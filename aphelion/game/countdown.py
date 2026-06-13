"""The launch campaign state machine: a real countdown (T-hh:mm:ss)
with named timeline events, built-in hold points, deterministic weather,
a generated voice-loop script, and low-probability anomaly chains that
escalate through readable telemetry BEFORE anyone calls them out.

Canon honored:
- 03 §6 (#8): Earth spaceport weather scrub probability ~= 0.02 per
  attempt at the KSC-analog coastal site; high-latitude sites are
  differentiated by a worse scrub probability. The per-criterion
  violation odds below sum to that target.
- 02 §2.4: cryo engines chill before start; a chill out of family is a
  hold/abort, not flavor text. The He-pressurant floor gates ignition.
- 12 F-1: the machine always knows its current abort posture (pad abort
  / Max-Q region / press-to-MECO) and recommends, never commands.
- 12 §3.5: every event carries an alert class (1 EMERGENCY … 4
  ADVISORY) so the orchestrator can post straight to the AlertBus.
- 13 determinism: every roll is zlib.crc32 of a stable string key —
  never Python hash(); state is a JSON-safe plain dict throughout.

The depth contract: each anomaly surfaces as telemetry trending wrong
(an engine chill temp diverging from its siblings, bottle pressure
bleeding down, a nav delta creeping) minutes before the comm-loop
callout — the attentive player sees it coming.

API: Countdown(vessel_summary, site, t0, seed_key) with .step(dt) ->
[event dicts], .state, .telemetry, .chatter / .pop_chatter(),
.request_resume() / .commit() / .scrub() / .recycle() / .feed_flight(),
JSON-safe .to_dict() / .from_dict(). Renderer hooks: .arm_frac(),
.clamp_frac(), .deluge_on(), .vent_strength() drive
aphelion/render/launch_art.py with no extra bookkeeping.
"""

from __future__ import annotations

import math
import zlib

DAY_S = 86_400.0

# ---- the count --------------------------------------------------------------

START_CLOCK_S = -2_400.0          # T-40:00 — power-up is already underway
RECYCLE_CLOCK_S = -1_200.0        # recycle returns the count to T-20:00

# built-in hold points (clock_s, id). The commit point ALWAYS holds and
# waits for the player's explicit commit() — the forecast is on screen
# before the irreversible part begins.
HOLD_POINTS: tuple[tuple[float, str], ...] = (
    (-1_200.0, "poll_topping"),   # T-20:00 go/no-go poll
    (-120.0, "poll_terminal"),    # T-02:00 final range/weather/vehicle
    (-10.0, "commit"),            # T-00:10 player commits the auto sequence
)

# renderer cue windows (clock_s)
ARMS_T0, ARMS_T1 = -300.0, -210.0     # swing/crew arm retract window
DELUGE_T = -18.0                      # deluge water on
IGNITION_T = -3.0                     # ignition sequence start
CLAMP_RELEASE_S = 0.45                # hold-down release sweep after T0

# ---- engine chill (02 §2.4) -------------------------------------------------

CHILL_START_T = -420.0            # T-07:00
CHILL_AMBIENT_K = 295.0
CHILL_TARGET_K = 110.0
CHILL_TAU_S = 110.0               # nominal pump-inlet cooldown constant
CHILL_GO_K = 135.0                # at/below this the engine may start
CHILL_RISK_K = 150.0              # starting hotter = start-transient abort

# ---- helium pressurant ------------------------------------------------------

HE_NOMINAL_PSI = 5_200.0
HE_FLOOR_PSI = 3_800.0            # ignition inhibit floor
HE_FLIGHT_FLOOR_PSI = 3_000.0     # in-flight depletion recommendation
HE_SCRUB_RATE_PSI_S = 1.2         # leak rate above this is a scrub call

# ---- weather (03 §6 #8) -----------------------------------------------------

WIND_LIMIT_KT = 30.0              # ground winds at the pad
SHEAR_LIMIT_KT = 40.0             # upper-level shear
CELL_LIMIT_NMI = 10.0             # the lightning rule: no cell inside 10
# per-criterion violation odds (wind, shear, lightning); default coastal
# equatorial site sums to ~0.024 ~= the canon 0.02 scrub probability.
SITE_WX_P: dict[str, tuple[float, float, float]] = {
    "default": (0.010, 0.008, 0.006),
    "polar": (0.030, 0.022, 0.012),     # high-latitude surcharge
}
WX_DRIFT_PERIOD_S = 2_700.0       # gust-front period — holds can clear it
WX_DRIFT_FRAC = 0.22

# ---- anomaly fault trees ----------------------------------------------------
# p = roll-under probability per attempt; all rolls crc32-derived.

ANOMALY_P: dict[str, float] = {
    "chill_lag": 0.07,            # one engine chills slow -> hold chain
    "he_leak": 0.05,              # pressurant bleed -> caution or scrub
    "range_foul": 0.05,           # boat in the box -> pure delay
    "engine_out": 0.04,           # post-liftoff shutdown
    "sensor_disagree": 0.04,      # post-liftoff IMU split
}
NAV_CALLOUT_DEG = 1.5
NAV_ABORT_DEG = 4.0

# telemetry keys whose values are currently out of family land in
# .cautions — the HUD marks them, the player who watches gets the story
# early. Bands for the steady-state keys:
TELEMETRY_BANDS: dict[str, tuple[float, float]] = {
    "he_psi": (4_800.0, 5_400.0),
    "tank_psi": (44.0, 56.0),
    "gnd_wind_kt": (0.0, WIND_LIMIT_KT),
    "shear_kt": (0.0, SHEAR_LIMIT_KT),
    "nav_delta_deg": (0.0, 1.0),
}

MAX_ENGINE_CHANNELS = 9


# ---- determinism ------------------------------------------------------------

def _roll(key: str) -> float:
    """Uniform [0, 1) from zlib.crc32 of a stable key (13: no hash())."""
    return (zlib.crc32(key.encode("utf-8")) & 0xFFFFFFFF) / 4294967296.0


def _pick(key: str, seq):
    return seq[zlib.crc32(key.encode("utf-8")) % len(seq)]


def fmt_clock(clock_s: float) -> str:
    """T-hh:mm:ss / T+hh:mm:ss caption-bar formatting."""
    sign = "-" if clock_s < 0 else "+"
    s = int(round(abs(clock_s)))
    return f"T{sign}{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


# ---- vessel summary ---------------------------------------------------------

def summarize_vessel(vessel, name: str = "", crew=()) -> dict:
    """JSON-safe pad summary of a sim.vessels Vessel: tank masses by
    resource (drives load timelines), first-stage engine count (drives
    chill channels + engine-out math), crew (drives CAPCOM)."""
    prop: dict[str, float] = {}
    for row in vessel.rows:
        for res, kg in row.fill.items():
            prop[res] = prop.get(res, 0.0) + float(kg)
    return {
        "name": name or "the vehicle",
        "crewed": bool(crew),
        "crew": [str(c) for c in crew],
        "engines": max(1, len(vessel.active_engines())),
        "stages": max(1, len(vessel.stage_plan)),
        "mass_t": vessel.total_mass_kg() / 1_000.0,
        "prop_kg": prop,
    }


# resource-ID aliases (04 canon ids like "Oxygen"/"Methane" and the
# colloquial pad names both work)
_OX_KEYS = ("LOX", "Oxygen", "NTO")
_FUEL_KEYS = ("CH4", "Methane", "LH2", "Hydrogen", "RP1", "MMH")
_DISPLAY = {"Oxygen": "LOX", "Methane": "CH4", "Hydrogen": "LH2"}


def _ox_key(prop_kg: dict) -> str | None:
    for res in _OX_KEYS:
        if prop_kg.get(res, 0.0) > 0.0:
            return res
    return None


def _fuel_key(prop_kg: dict) -> str | None:
    for res in _FUEL_KEYS:
        if prop_kg.get(res, 0.0) > 0.0:
            return res
    ox = _ox_key(prop_kg)
    others = [r for r in prop_kg if r != ox and prop_kg[r] > 0.0]
    return others[0] if others else None


def _fuel_name(prop_kg: dict) -> str:
    key = _fuel_key(prop_kg)
    if key is None:
        return "FUEL"
    return _DISPLAY.get(key, key)


# ---- weather model ----------------------------------------------------------

def _site_p(site: str) -> tuple[float, float, float]:
    s = site.lower()
    if "polar" in s or "high_lat" in s or "high-lat" in s:
        return SITE_WX_P["polar"]
    return SITE_WX_P["default"]


def _wx_base(site: str, day: int, kind: str, p: float,
             limit: float) -> float:
    """Base magnitude for the day: monotone in the roll with
    P(value > limit) == p exactly, and calm typical days."""
    u = _roll(f"wx|{site}|{day}|{kind}")
    return min(limit * 1.45, limit * (u / (1.0 - p)) ** 3)


def weather_at(site: str, abs_t: float) -> dict:
    """Deterministic weather at one absolute sim time: per-(site, day)
    crc32 anchor rolls + slow intra-day drift, so a marginal violation
    can clear inside a 10-25 minute hold. JSON-safe dict."""
    day = int(abs_t // DAY_S)
    p_wind, p_shear, p_ltg = _site_p(site)
    out: dict = {"day": day}
    tod = abs_t % DAY_S
    for kind, p, limit in (("wind", p_wind, WIND_LIMIT_KT),
                           ("shear", p_shear, SHEAR_LIMIT_KT)):
        base = _wx_base(site, day, kind, p, limit)
        ph = _roll(f"wxph|{site}|{day}|{kind}") * 2.0 * math.pi
        drift = 1.0 + WX_DRIFT_FRAC * math.sin(
            2.0 * math.pi * tod / WX_DRIFT_PERIOD_S + ph)
        out[kind + "_kt"] = round(base * drift, 1)
    # lightning rule: distance of the nearest convective cell; the day
    # roll places it, drift walks it — no-go inside CELL_LIMIT_NMI.
    u = _roll(f"wx|{site}|{day}|ltg")
    base_nmi = min(50.0, CELL_LIMIT_NMI * math.sqrt((1.0 - u) / p_ltg))
    ph = _roll(f"wxph|{site}|{day}|ltg") * 2.0 * math.pi
    cell = base_nmi + 6.0 * math.sin(
        2.0 * math.pi * tod / (WX_DRIFT_PERIOD_S * 1.7) + ph)
    out["cell_nmi"] = round(max(0.0, cell), 1)
    out["violations"] = violations = []
    if out["wind_kt"] > WIND_LIMIT_KT:
        violations.append("weather:wind")
    if out["shear_kt"] > SHEAR_LIMIT_KT:
        violations.append("weather:shear")
    if out["cell_nmi"] < CELL_LIMIT_NMI:
        violations.append("weather:lightning")
    out["go"] = not violations
    return out


def weather_forecast(site: str, t0: float) -> dict:
    """The honest pre-commit forecast: criteria valued AT the scheduled
    T0 (same function the live check reads — the forecast never lies)."""
    wx = weather_at(site, t0)
    criteria = [
        {"name": "ground winds", "value": wx["wind_kt"],
         "limit": WIND_LIMIT_KT, "unit": "kt",
         "go": wx["wind_kt"] <= WIND_LIMIT_KT},
        {"name": "upper-level shear", "value": wx["shear_kt"],
         "limit": SHEAR_LIMIT_KT, "unit": "kt",
         "go": wx["shear_kt"] <= SHEAR_LIMIT_KT},
        {"name": "nearest cell", "value": wx["cell_nmi"],
         "limit": CELL_LIMIT_NMI, "unit": "nmi",
         "go": wx["cell_nmi"] >= CELL_LIMIT_NMI},
    ]
    return {"site": site, "t0": t0, "day": wx["day"],
            "criteria": criteria, "go": all(c["go"] for c in criteria)}


def next_window(site: str, t0: float, days: int = 14) -> float | None:
    """First future daily slot (same time of day) with a GO forecast."""
    for n in range(1, days + 1):
        if weather_forecast(site, t0 + n * DAY_S)["go"]:
            return t0 + n * DAY_S
    return None


# ---- the comm loop ----------------------------------------------------------
# Stations with per-station personality: variant pools picked by crc32
# of (seed, line id) — alive between launches, identical on replay.

POLL_ORDER = ("PROP", "TM", "GUID", "FTS", "RANGE", "WX", "GC", "CAPCOM")

STATION_GO: dict[str, tuple[str, ...]] = {
    "PROP": ("PROP is go, flight.", "PROP — we are go.",
             "Tanks are stable, PROP is go."),
    "TM": ("TM, go.", "Telemetry is solid — TM is go.",
           "TM — good data on all strings, go."),
    "GUID": ("Guidance is go.", "GUID — nav is tight, go.",
             "Guidance — platform aligned, we are go."),
    "FTS": ("FTS, go.", "FTS is green.", "FTS — go."),
    "RANGE": ("Range is green.", "Range is clear — go.",
              "RANGE — surveillance shows a clean box, go."),
    "WX": ("Weather is go.", "WX is go — all criteria observed green.",
           "Weather — go at this time."),
    "GC": ("GC, go.", "Ground is configured — GC is go.",
           "GC — pad is buttoned up, go."),
    "CAPCOM": ("Crew is go.", "CAPCOM — crew reports go.",
               "Crew is strapped in and go."),
}
LD_POLL_OPEN = (
    "All stations, this is LD — go/no-go for launch.",
    "All consoles, LD here: stand by for status check.",
    "LD to all stations — verify go for terminal count.",
)
LD_POLL_CLOSE = (
    "LD copies all stations go. We are continuing the count.",
    "All green across the board — the count continues.",
    "LD — we are go, picking up the count.",
)
LD_HOLD = (
    "LD — hold, hold, hold. All stations safe your consoles.",
    "LD — we are going into a hold. Stations, hold your items.",
)
LD_RESUME = (
    "LD — the constraint is cleared, we are go to resume the count.",
    "LD — picking up the count where we left it.",
)
LD_SCRUB = (
    "LD — we are scrubbed for today. Stations, proceed to securing.",
    "LD — that's a scrub. Begin detanking and safing procedures.",
)


def _line(seed_key: str, attempt: int, line_id: str, who: str,
          pool) -> str:
    return _pick(f"{seed_key}|a{attempt}|{line_id}|{who}", tuple(pool))


# Named timeline: (clock_s, id, class, event text, [(who, pool), ...]).
# Pools may contain {fuel}/{name}/{lox_t}/{fuel_t} format slots.
def _timeline(vs: dict) -> tuple:
    prop = vs.get("prop_kg", {})
    fuel = _fuel_name(prop)
    ox = _ox_key(prop)
    lox_t = (prop.get(ox, 0.0) if ox else 0.0) / 1_000.0
    fk = _fuel_key(prop)
    fuel_t = (prop.get(fk, 0.0) if fk else 0.0) / 1_000.0
    nm = vs.get("name", "the vehicle")
    f = {"fuel": fuel, "name": nm, "lox_t": f"{lox_t:,.0f}",
         "fuel_t": f"{fuel_t:,.0f}"}
    rows = [
        (-2_400.0, "power_up", 4, "vehicle power-up and checkout",
         (("GC", ("Vehicle is on external power, avionics are up.",
                  "GC — bus voltages nominal, checkout is running.")),)),
        (-2_100.0, "lox_load", 4, "LOX load start",
         (("PROP", ("LD, PROP — LOX load has started, "
                    "{lox_t} tonnes to go aboard.",
                    "PROP — oxidizer flow is established, "
                    "{lox_t} tonnes on the manifest.")),)),
        (-1_920.0, "fuel_load", 4, "{fuel} load start",
         (("PROP", ("PROP — {fuel} load underway, {fuel_t} tonnes.",
                    "PROP — fuel side is flowing, {fuel_t} tonnes "
                    "to load.")),)),
        (-960.0, "load_topping", 4, "propellant topping",
         (("PROP", ("PROP — tanks are at flight load, going to "
                    "topping.",
                    "PROP — we are in stable replenish.")),)),
        (CHILL_START_T, "engine_chill", 4, "engine chill-in begins",
         (("PROP", ("PROP — engine chill-in has started.",
                    "PROP — chilldown flow to all engines.")),)),
        (-300.0, "arms_retract", 4, "access arms retracting",
         (("GC", ("GC — swing arms coming back.",
                  "GC — retracting the access arms now.")),)),
        (-60.0, "internal_power", 4, "vehicle on internal power",
         (("GC", ("Vehicle is on internal power.",
                  "GC — transferred to internal power, levels are "
                  "good.")),)),
        (-45.0, "fts_arm", 4, "flight termination system armed",
         (("FTS", ("FTS is armed.", "FTS — system is armed and "
                   "green.")),)),
        (DELUGE_T, "deluge", 4, "deluge water flowing",
         (("GC", ("Deluge is flowing.", "GC — water on the deck.")),)),
        (IGNITION_T, "ignition", 3, "ignition sequence start",
         (("GC", ("Ignition sequence start.",
                  "GC — engine start command.")),)),
        (0.0, "liftoff", 3, "LIFTOFF",
         (("GC", ("Liftoff — we have liftoff of {name}.",
                  "And liftoff — {name} has cleared the hold-downs.")),)),
        (6.0, "tower_clear", 4, "tower cleared",
         (("GC", ("Tower is clear.", "{name} has cleared the "
                  "tower.")),)),
        (18.0, "pitch_program", 4, "pitch program",
         (("GUID", ("Vehicle is pitching downrange.",
                    "GUID — pitch and roll program nominal.")),)),
    ]
    out = []
    for t, eid, cls, text, chat in rows:
        chat2 = tuple((who, tuple(p.format(**f) for p in pool))
                      for who, pool in chat)
        out.append((t, eid, cls, text.format(**f), chat2))
    return tuple(out)


# ---- the machine ------------------------------------------------------------

class Countdown:
    """One launch attempt as a deterministic state machine.

    Phases: count -> (hold <-> count) -> terminal -> flight, with
    scrub / abort exits. Clock freezes in holds; weather and the cryo
    state keep evolving on absolute time — the hold IS the gameplay.
    """

    def __init__(self, vessel_summary: dict, site: str, t0: float,
                 seed_key: str, clock_s: float = START_CLOCK_S):
        self.vs = dict(vessel_summary)
        self.site = str(site)
        self.t0 = float(t0)
        self.seed_key = str(seed_key)
        self.clock_s = float(clock_s)
        self.abs_t = float(t0) + float(clock_s)
        self.phase = "count"
        self.attempt = 1
        self.holds: list[dict] = []
        self.passed: list[str] = []          # hold-point ids cleared
        self.fired: list[str] = []           # timeline event ids fired
        self.accepted_risks: list[str] = []
        self.chatter: list[dict] = []
        self.log: list[dict] = []
        self.telemetry: dict[str, float] = {}
        self.cautions: list[str] = []
        self.abort_recommended: str | None = None
        self.abort_posture = "pad abort"     # 12 F-1: always present
        self.anomalies: dict[str, dict] = {}
        self._flight: dict[str, float] = {}  # feed_flight mirrors
        self._q_max = 0.0
        self._count_said: list[int] = []
        self._roll_attempt()
        self._update_telemetry()

    # -- deterministic per-attempt rolls --------------------------------------

    def _r(self, key: str) -> float:
        return _roll(f"{self.seed_key}|a{self.attempt}|{key}")

    def _roll_attempt(self) -> None:
        n_eng = min(int(self.vs.get("engines", 1)), MAX_ENGINE_CHANNELS)
        a: dict[str, dict] = {}
        if self._r("p|chill_lag") < ANOMALY_P["chill_lag"]:
            sev = self._r("sev|chill_lag")
            a["chill_lag"] = {
                "engine": 1 + int(self._r("eng|chill_lag") * n_eng),
                "sev": round(sev, 4), "tau_s":
                    round(CHILL_TAU_S * (2.0 + 2.5 * sev), 1),
                "called": False}
        if self._r("p|he_leak") < ANOMALY_P["he_leak"]:
            sev = self._r("sev|he_leak")
            a["he_leak"] = {
                "onset_clock": round(-2_000.0 + 1_600.0
                                     * self._r("on|he_leak"), 1),
                "rate_psi_s": round(0.3 + 2.2 * sev, 3),
                "t_abs_start": None, "called": False}
        if self._r("p|range_foul") < ANOMALY_P["range_foul"]:
            off = 600.0 + 1_500.0 * self._r("on|range_foul")
            dur = 240.0 + 900.0 * self._r("dur|range_foul")
            a["range_foul"] = {
                "t_abs_in": round(self.t0 - off, 1),
                "t_abs_out": round(self.t0 - off + dur, 1),
                "called": False}
        if self._r("p|engine_out") < ANOMALY_P["engine_out"]:
            a["engine_out"] = {
                "engine": 1 + int(self._r("eng|engine_out") * n_eng),
                "t_clock": round(20.0 + 70.0 * self._r("on|engine_out"),
                                 1),
                "called": False}
        if self._r("p|sensor_disagree") < ANOMALY_P["sensor_disagree"]:
            a["sensor_disagree"] = {
                "t_clock": round(15.0 + 45.0
                                 * self._r("on|sensor_disagree"), 1),
                "rate_deg_s": round(0.02 + 0.08
                                    * self._r("sev|sensor_disagree"), 4),
                "called": False}
        self.anomalies = a
        self.timeline = _timeline(self.vs)

    # -- public queries -------------------------------------------------------

    @property
    def state(self) -> dict:
        return {
            "phase": self.phase, "clock_s": self.clock_s,
            "clock": fmt_clock(self.clock_s), "abs_t": self.abs_t,
            "attempt": self.attempt, "holds": [dict(h) for h in
                                               self.holds],
            "hold_reasons": self._blocking_reasons()
            if self.phase == "hold" else [],
            "abort_recommended": self.abort_recommended,
            "abort_posture": self.abort_posture,
            "weather": weather_at(self.site, self.abs_t),
            "accepted_risks": list(self.accepted_risks),
        }

    def forecast(self) -> dict:
        return weather_forecast(self.site, self.t0)

    def pop_chatter(self, n: int | None = None) -> list[dict]:
        """Drain (up to n) pending comm-loop lines, oldest first."""
        if n is None:
            n = len(self.chatter)
        out, self.chatter = self.chatter[:n], self.chatter[n:]
        return out

    # renderer hooks (launch_art consumes these directly) ----------------

    def arm_frac(self) -> float:
        """0 = arms on the vehicle, 1 = fully retracted (eased)."""
        u = (self.clock_s - ARMS_T0) / (ARMS_T1 - ARMS_T0)
        u = max(0.0, min(1.0, u))
        return u * u * (3.0 - 2.0 * u)

    def clamp_frac(self) -> float:
        """Hold-down release sweep just after T0."""
        if self.phase != "flight":
            return 0.0
        return max(0.0, min(1.0, self.clock_s / CLAMP_RELEASE_S))

    def deluge_on(self) -> bool:
        return (self.phase in ("terminal", "flight")
                and DELUGE_T <= self.clock_s <= 20.0)

    def vent_strength(self) -> float:
        """Cryo vent wisps: full while tanking with cryo aboard, gone
        once the vehicle is pressurized for flight."""
        if self.phase in ("flight", "scrub"):
            return 0.0
        if self.telemetry.get("lox_pct", 0.0) < 5.0:
            return 0.0
        if self.clock_s >= DELUGE_T:
            return 0.0
        return min(1.0, self.telemetry.get("lox_pct", 0.0) / 60.0)

    # -- player verbs ---------------------------------------------------------

    def request_hold(self) -> bool:
        """Player-initiated hold (only while counting, before commit)."""
        if self.phase != "count":
            return False
        self._enter_hold("player hold", ["player"])
        return True

    def request_resume(self, accept_risk: bool = False) -> bool:
        """Resume from a hold. Blocked while constraints stand unless
        the player explicitly accepts the risk (logged; consequences
        follow at ignition/ascent)."""
        if self.phase != "hold":
            return False
        reasons = self._blocking_reasons()
        if reasons and not accept_risk:
            return False
        if reasons:
            for r in reasons:
                if r not in self.accepted_risks:
                    self.accepted_risks.append(r)
        if self.holds:
            self.holds[-1]["released"] = True
        if self._at_commit_point():
            # resuming the commit hold IS committing
            self.phase = "terminal"
            self.abort_posture = "pad abort"
        else:
            self.phase = "count"
        self._say("resume", "LD",
                  _line(self.seed_key, self.attempt,
                        f"resume{len(self.holds)}", "LD", LD_RESUME))
        self._event("resume", 4, "count resumed"
                    + (" (risk accepted: " + ", ".join(reasons) + ")"
                       if reasons else ""))
        return True

    def commit(self, accept_risk: bool = False) -> bool:
        """Commit the terminal auto-sequence at the T-10 s hold."""
        if not (self.phase == "hold" and self._at_commit_point()):
            return False
        return self.request_resume(accept_risk=accept_risk)

    def scrub(self) -> dict:
        """Stand down for the day. Returns {'next_t0': ...} from the
        forecast scan so the scene can offer the next attempt."""
        if self.phase in ("flight", "scrub"):
            return {"next_t0": None}
        self.phase = "scrub"
        self._say("scrub", "LD",
                  _line(self.seed_key, self.attempt, "scrub", "LD",
                        LD_SCRUB))
        self._event("scrub", 3, "SCRUB — launch attempt stood down")
        nxt = next_window(self.site, self.t0)
        return {"next_t0": nxt}

    def recycle(self) -> bool:
        """After a pad abort (or from a hold): recycle to T-20:00 with
        fresh per-attempt rolls. Time already burned stays burned."""
        if self.phase not in ("abort", "hold"):
            return False
        self.attempt += 1
        self.clock_s = RECYCLE_CLOCK_S
        self.t0 = self.abs_t - RECYCLE_CLOCK_S
        self.phase = "count"
        self.passed = []
        # release any parked hold so it doesn't persist (unreleased) into
        # the new attempt and keep growing the hold list / line-id numbering
        for _h in self.holds:
            _h["released"] = True
        self.fired = [e for e in self.fired
                      if e in ("power_up", "lox_load", "fuel_load")]
        self.accepted_risks = []
        self.abort_recommended = None
        self._count_said = []
        self._anom_marks = {}
        self._q_max = 0.0
        self._roll_attempt()
        self._event("recycle", 4,
                    f"count recycled to {fmt_clock(RECYCLE_CLOCK_S)} "
                    f"(attempt {self.attempt})")
        return True

    def feed_flight(self, h_m: float | None = None,
                    v_ms: float | None = None,
                    q_pa: float | None = None,
                    engines_out: int | None = None) -> None:
        """Optional live-ascent mirror: enables Mach-1 / Max-Q callouts
        and ties real flameouts into the loop."""
        for k, v in (("h_m", h_m), ("v_ms", v_ms), ("q_pa", q_pa),
                     ("engines_out", engines_out)):
            if v is not None:
                self._flight[k] = float(v)

    # -- the step -------------------------------------------------------------

    def step(self, dt: float) -> list[dict]:
        """Advance dt seconds; returns the new event dicts (each with
        id/kind/cls/text/t_clock). Chatter accumulates separately."""
        out: list[dict] = []
        if dt <= 0.0 or self.phase == "scrub":
            return out
        self._events_out = out
        self.abs_t += dt
        if self.phase == "hold":
            if self.holds:
                self.holds[-1]["t_held_s"] = round(
                    self.holds[-1]["t_held_s"] + dt, 3)
            self._tick_anomalies()
            self._update_telemetry()
            self._hold_watch()
            self._events_out = None
            return out
        if self.phase == "abort":
            self._update_telemetry()
            self._events_out = None
            return out
        remaining = dt
        while remaining > 1e-9 and self.phase in ("count", "terminal",
                                                  "flight"):
            target = self.clock_s + remaining
            hp = self._next_hold_point()
            step_to = min(target, hp[0]) if hp else target
            advanced = step_to - self.clock_s
            self.clock_s = step_to
            remaining -= advanced
            self._fire_due()
            if self.phase in ("abort", "scrub"):
                break
            if hp and abs(self.clock_s - hp[0]) < 1e-9:
                self.passed.append(hp[1])
                self._hold_point(hp[1])
                if self.phase == "hold":
                    break
        self._tick_anomalies()
        self._update_telemetry()
        self._events_out = None
        return out

    # -- internals ------------------------------------------------------------

    def _say(self, line_id: str, who: str, text: str,
             kind: str = "loop", t_at: float | None = None) -> None:
        t = self.clock_s if t_at is None else t_at
        self.chatter.append({"t_clock": round(t, 2),
                             "clock": fmt_clock(t),
                             "who": who, "text": text, "kind": kind})

    def _event(self, eid: str, cls: int, text: str,
               kind: str = "event", t_at: float | None = None) -> dict:
        t = self.clock_s if t_at is None else t_at
        ev = {"id": eid, "kind": kind, "cls": int(cls), "text": text,
              "t_clock": round(t, 2), "clock": fmt_clock(t)}
        self.log.append(ev)
        if getattr(self, "_events_out", None) is not None:
            self._events_out.append(ev)
        return ev

    def _next_hold_point(self):
        if self.phase != "count":
            return None
        for t, hid in HOLD_POINTS:
            if hid not in self.passed and t > self.clock_s - 1e-9:
                return (t, hid)
        return None

    def _at_commit_point(self) -> bool:
        return abs(self.clock_s - HOLD_POINTS[-1][0]) < 1e-6

    # blocking constraints (range/weather/vehicle), evaluated live ------

    def _blocking_reasons(self) -> list[str]:
        reasons = list(weather_at(self.site, self.abs_t)["violations"])
        rf = self.anomalies.get("range_foul")
        if rf and rf["t_abs_in"] <= self.abs_t <= rf["t_abs_out"]:
            reasons.append("range:fouled")
        cl = self.anomalies.get("chill_lag")
        if cl and self.clock_s >= CHILL_START_T:
            if self._chill_k(cl["engine"]) > CHILL_GO_K:
                reasons.append("vehicle:chill_lag")
        hl = self.anomalies.get("he_leak")
        if hl and hl["t_abs_start"] is not None:
            if hl["rate_psi_s"] > HE_SCRUB_RATE_PSI_S:
                reasons.append("vehicle:he_leak")
        reasons = [r for r in reasons if r not in self.accepted_risks]
        return reasons

    def _enter_hold(self, label: str, reasons: list[str]) -> None:
        self.phase = "hold"
        self.holds.append({"t_clock": round(self.clock_s, 2),
                           "label": label, "reasons": list(reasons),
                           "t_held_s": 0.0, "released": False})
        self._say(f"hold{len(self.holds)}", "LD",
                  _line(self.seed_key, self.attempt,
                        f"hold{len(self.holds)}", "LD", LD_HOLD))
        self._event("hold", 3,
                    f"HOLD at {fmt_clock(self.clock_s)} — "
                    + ", ".join(reasons), kind="hold")

    def _hold_watch(self) -> None:
        """Announce (once) when every constraint has cleared."""
        if not self.holds or self.holds[-1].get("clear_called"):
            return
        if not self._blocking_reasons():
            self.holds[-1]["clear_called"] = True
            self._event("hold_clear", 4,
                        "all constraints clear — go for resume")
            self._say("hold_clear", "GC",
                      _line(self.seed_key, self.attempt, "hold_clear",
                            "GC",
                            ("GC — the constraint has cleared, standing "
                             "by for LD.",
                             "GC — board is green again, ready to pick "
                             "up the count.")))

    def _hold_point(self, hid: str) -> None:
        """Arriving at a built-in hold point: run the poll, then either
        continue through or park in a hold."""
        reasons = self._blocking_reasons()
        if hid in ("poll_topping", "poll_terminal"):
            self._poll(hid, reasons)
            if reasons:
                self._enter_hold(hid, reasons)
        elif hid == "commit":
            self._event("commit_point", 4,
                        "T-10 s — auto-sequence awaits launch commit")
            self._say("commit", "LD",
                      _line(self.seed_key, self.attempt, "commit", "LD",
                            ("LD — auto-sequence is configured; on your "
                             "call we commit.",
                             "LD — holding at ten seconds for the "
                             "commit.")))
            self._enter_hold("commit", reasons or ["awaiting commit"])

    def _poll(self, hid: str, reasons: list[str]) -> None:
        self._say(f"{hid}|open", "LD",
                  _line(self.seed_key, self.attempt, f"{hid}|open",
                        "LD", LD_POLL_OPEN), kind="poll")
        wx = weather_at(self.site, self.abs_t)
        for who in POLL_ORDER:
            if who == "CAPCOM" and not self.vs.get("crewed"):
                continue
            nogo = None
            if who == "WX" and any(r.startswith("weather")
                                   for r in reasons):
                nogo = (f"Weather is NO-GO — winds {wx['wind_kt']:.0f}"
                        f" kt, shear {wx['shear_kt']:.0f} kt, nearest "
                        f"cell {wx['cell_nmi']:.0f} nautical miles.")
            elif who == "RANGE" and "range:fouled" in reasons:
                nogo = ("Range is RED — surface contact inside the "
                        "hazard area, surveillance is on it.")
            elif who == "PROP" and "vehicle:chill_lag" in reasons:
                cl = self.anomalies["chill_lag"]
                nogo = (f"PROP is NO-GO — engine {cl['engine']} chill "
                        f"is out of family, reading "
                        f"{self._chill_k(cl['engine']):.0f} kelvin "
                        f"against {CHILL_GO_K:.0f} required.")
            elif who == "PROP" and "vehicle:he_leak" in reasons:
                hl = self.anomalies["he_leak"]
                nogo = (f"PROP is NO-GO — helium decay at "
                        f"{hl['rate_psi_s'] * 60.0:.0f} psi a minute, "
                        f"that is over the scrub line.")
            if nogo:
                self._say(f"{hid}|{who}", who, nogo, kind="poll")
            elif who == "WX":
                self._say(f"{hid}|{who}", who,
                          _line(self.seed_key, self.attempt,
                                f"{hid}|{who}", who, STATION_GO[who])
                          + (f" Winds {wx['wind_kt']:.0f} knots, "
                             f"cell at {wx['cell_nmi']:.0f} miles."),
                          kind="poll")
            else:
                self._say(f"{hid}|{who}", who,
                          _line(self.seed_key, self.attempt,
                                f"{hid}|{who}", who, STATION_GO[who]),
                          kind="poll")
        if not reasons:
            self._say(f"{hid}|close", "LD",
                      _line(self.seed_key, self.attempt, f"{hid}|close",
                            "LD", LD_POLL_CLOSE), kind="poll")
            self._event(hid, 4, "go/no-go poll: all stations GO",
                        kind="poll")
        else:
            self._event(hid, 3, "go/no-go poll: NO-GO — "
                        + ", ".join(reasons), kind="poll")

    # timeline + terminal sequence ----------------------------------------

    def _fire_due(self) -> None:
        # terminal count digits for the caption bar FIRST (the liftoff
        # row below flips phase to flight; backfilled so a warped step
        # still logs the whole sequence in order)
        if self.phase == "terminal":
            n = int(math.ceil(-self.clock_s - 1e-9))
            for k in range(10, max(n, 1) - 1, -1):
                if k not in self._count_said:
                    self._count_said.append(k)
                    self._say(f"count{k}", "GC", f"T-minus {k}",
                              kind="count", t_at=-float(k))
        for t, eid, cls, text, chat in self.timeline:
            if eid in self.fired or t > self.clock_s + 1e-9:
                continue
            if eid == "ignition" and not self._ignition_check():
                return
            if eid == "liftoff":
                self.phase = "flight"
                self.abort_posture = "Max-Q region"
            self.fired.append(eid)
            if eid == "engine_chill":
                marks = self._anom_marks = getattr(
                    self, "_anom_marks", {})
                marks["chill_abs"] = self.abs_t - (self.clock_s - t)
            self._event(eid, cls, text, t_at=t,
                        kind="milestone" if t >= 0.0 else "event")
            for who, pool in chat:
                self._say(eid, who,
                          _line(self.seed_key, self.attempt, eid, who,
                                pool), t_at=t)
        if self.phase == "flight":
            self._flight_milestones()

    def _ignition_check(self) -> bool:
        """02 §2.4 gates at engine start. A failed gate is a pad abort
        (phase 'abort'), recyclable — the consequence of accepted risk."""
        cl = self.anomalies.get("chill_lag")
        if (cl and "vehicle:chill_lag" in self.accepted_risks
                and self._chill_k(cl["engine"]) > CHILL_RISK_K):
            self.phase = "abort"
            self.fired.append("ignition")
            self._event("pad_abort", 2,
                        f"PAD ABORT — engine {cl['engine']} start "
                        f"transient out of family; shutdown", kind="abort")
            self._say("pad_abort", "GC",
                      "Hold-down — we have an abort, engine "
                      f"{cl['engine']} did not make start box. "
                      "Vehicle is safe.", kind="anomaly")
            self.abort_posture = "pad abort"
            return False
        if self.telemetry.get("he_psi", HE_NOMINAL_PSI) < HE_FLOOR_PSI:
            self.phase = "abort"
            self.fired.append("ignition")
            self._event("pad_abort", 2,
                        "PAD ABORT — pressurant below ignition floor "
                        f"({HE_FLOOR_PSI:.0f} psi)", kind="abort")
            self._say("pad_abort", "PROP",
                      "PROP — cutoff, helium is below the floor. "
                      "Safing the vehicle.", kind="anomaly")
            return False
        return True

    def _flight_milestones(self) -> None:
        v = self._flight.get("v_ms")
        if v is not None and v >= 340.0 and "mach1" not in self.fired:
            self.fired.append("mach1")
            self._event("mach1", 4, "vehicle is supersonic",
                        kind="milestone")
            self._say("mach1", "TM", "Vehicle is supersonic.")
        q = self._flight.get("q_pa")
        if q is not None:
            self._q_max = max(self._q_max, q)
            if (self._q_max > 15_000.0 and q < 0.92 * self._q_max
                    and "maxq" not in self.fired):
                self.fired.append("maxq")
                self.abort_posture = "press to MECO"
                self._event("maxq", 4, "through Max-Q", kind="milestone")
                self._say("maxq", "TM",
                          f"And we are through Max-Q, "
                          f"{self._q_max / 1000.0:.0f} kilopascals "
                          "peak. Vehicle is looking good.")
        if ("weather:shear" in self.accepted_risks
                and "shear_kick" not in self.fired
                and self.clock_s >= 40.0):
            self.fired.append("shear_kick")
            wx = weather_at(self.site, self.abs_t)
            cls = 2 if wx["shear_kt"] > SHEAR_LIMIT_KT * 1.1 else 3
            self._event("shear_kick", cls,
                        f"wind-shear exceedance — {wx['shear_kt']:.0f} "
                        "kt layer", kind="anomaly")
            self._say("shear_kick", "GUID",
                      "GUID — we took a shear kick in the upper levels,"
                      " attitude error is recovering.", kind="anomaly")
            if cls == 2:
                self.abort_recommended = "structural margins (shear)"

    # anomaly evolution -----------------------------------------------------

    def _chill_k(self, engine: int) -> float:
        """Pump-inlet temperature for one engine channel (1-based).
        Chill keeps running on ABSOLUTE time through holds — holding
        for a lagging engine genuinely cools it down."""
        if "engine_chill" not in self.fired:
            return CHILL_AMBIENT_K
        dt = max(0.0, self.abs_t - self._chill_abs_start())
        tau = CHILL_TAU_S
        cl = self.anomalies.get("chill_lag")
        if cl and cl["engine"] == engine:
            tau = cl["tau_s"]
        return (CHILL_TARGET_K + (CHILL_AMBIENT_K - CHILL_TARGET_K)
                * math.exp(-dt / tau))

    def _chill_abs_start(self) -> float:
        marks = self._anom_marks = getattr(self, "_anom_marks", {})
        if "chill_abs" not in marks:
            # back-date to the clock instant chill actually started
            marks["chill_abs"] = self.abs_t - max(
                0.0, self.clock_s - CHILL_START_T)
        return marks["chill_abs"]

    def _tick_anomalies(self) -> None:
        cl = self.anomalies.get("chill_lag")
        if (cl and not cl["called"] and "engine_chill" in self.fired):
            nominal = (CHILL_TARGET_K
                       + (CHILL_AMBIENT_K - CHILL_TARGET_K)
                       * math.exp(-(self.abs_t
                                    - self._chill_abs_start())
                                  / CHILL_TAU_S))
            if self._chill_k(cl["engine"]) - nominal > 40.0:
                cl["called"] = True
                self._event("chill_lag", 3,
                            f"engine {cl['engine']} chill lagging",
                            kind="anomaly")
                self._say("chill_lag", "PROP",
                          f"LD, be advised — engine {cl['engine']} "
                          "chill is lagging the others, watching the "
                          "trend.", kind="anomaly")
        hl = self.anomalies.get("he_leak")
        if hl:
            if (hl["t_abs_start"] is None
                    and self.clock_s >= hl["onset_clock"]):
                hl["t_abs_start"] = self.abs_t
            if hl["t_abs_start"] is not None and not hl["called"]:
                drop = (self.abs_t - hl["t_abs_start"]) \
                    * hl["rate_psi_s"]
                if drop > 150.0:
                    hl["called"] = True
                    over = hl["rate_psi_s"] > HE_SCRUB_RATE_PSI_S
                    self._event(
                        "he_leak", 2 if over else 3,
                        f"helium decay {hl['rate_psi_s'] * 60.0:.0f} "
                        f"psi/min"
                        + (" — exceeds scrub threshold" if over else ""),
                        kind="anomaly")
                    self._say("he_leak", "PROP",
                              "PROP — I'm seeing helium bottle decay at "
                              f"{hl['rate_psi_s'] * 60.0:.0f} psi a "
                              "minute"
                              + (", that's over our scrub line."
                                 if over else ", inside limits for "
                                 "now."), kind="anomaly")
        if self.phase != "flight":
            return
        eo = self.anomalies.get("engine_out")
        if eo and not eo["called"] and self.clock_s >= eo["t_clock"]:
            eo["called"] = True
            n_eng = int(self.vs.get("engines", 1))
            self._event("engine_out", 2,
                        f"engine {eo['engine']} shutdown — "
                        f"{n_eng - 1} running", kind="anomaly")
            self._say("engine_out", "TM",
                      f"TM — we've lost engine {eo['engine']}. Vehicle "
                      "is holding attitude, performance is degraded.",
                      kind="anomaly")
            if n_eng <= 2:
                self.abort_recommended = "thrust deficit (engine out)"
                self._say("engine_out2", "LD",
                          "LD — performance will not close. Recommend "
                          "abort.", kind="anomaly")
            else:
                self._say("engine_out2", "GUID",
                          "GUID — trajectory still converges, we are "
                          "press to MECO.", kind="anomaly")
        sd = self.anomalies.get("sensor_disagree")
        if sd and self.clock_s >= sd["t_clock"]:
            delta = (self.clock_s - sd["t_clock"]) * sd["rate_deg_s"]
            if delta >= NAV_CALLOUT_DEG and not sd["called"]:
                sd["called"] = True
                self._event("sensor_disagree", 3,
                            "IMU disagree — nav delta "
                            f"{delta:.1f} deg and growing",
                            kind="anomaly")
                self._say("sensor_disagree", "GUID",
                          "GUID — I have a platform split, strings A "
                          "and B disagree. Watching the voter.",
                          kind="anomaly")
            if (delta >= NAV_ABORT_DEG
                    and "sensor_abort" not in self.fired):
                self.fired.append("sensor_abort")
                self.abort_recommended = "guidance integrity (IMU)"
                self._event("sensor_abort", 2,
                            "nav disagree beyond limit — abort "
                            "recommended", kind="anomaly")
                self._say("sensor_abort", "LD",
                          "LD — guidance is no longer trustworthy. "
                          "Recommend manual takeover or abort.",
                          kind="anomaly")
        if (self.anomalies.get("he_leak")
                and self.anomalies["he_leak"]["t_abs_start"] is not None
                and self.telemetry.get("he_psi", HE_NOMINAL_PSI)
                < HE_FLIGHT_FLOOR_PSI
                and "he_depletion" not in self.fired):
            self.fired.append("he_depletion")
            self.abort_recommended = "pressurant depletion"
            self._event("he_depletion", 2,
                        "helium below flight floor — abort recommended",
                        kind="anomaly")

    # telemetry -------------------------------------------------------------

    def _update_telemetry(self) -> None:
        tm = self.telemetry
        prop = self.vs.get("prop_kg", {})
        # propellant load: clock-driven ramps from load start to T-4:00
        for key, start, res in (("lox_pct", -2_100.0, _ox_key(prop)),
                                ("fuel_pct", -1_920.0,
                                 _fuel_key(prop))):
            if res is None or prop.get(res, 0.0) <= 0.0:
                tm[key] = 0.0
                continue
            u = (self.clock_s - start) / (-240.0 - start)
            tm[key] = round(max(0.0, min(1.0, u)) * 100.0, 1)
        # helium bottle: nominal wiggle, leak decline on top
        psi = HE_NOMINAL_PSI + 18.0 * math.sin(self.abs_t / 53.0)
        hl = self.anomalies.get("he_leak")
        if hl and hl["t_abs_start"] is not None:
            psi -= (self.abs_t - hl["t_abs_start"]) * hl["rate_psi_s"]
        tm["he_psi"] = round(max(0.0, psi), 1)
        tm["tank_psi"] = round(50.0 + 2.0
                               * math.sin(self.abs_t / 37.0), 1)
        wx = weather_at(self.site, self.abs_t)
        tm["gnd_wind_kt"] = wx["wind_kt"]
        tm["shear_kt"] = wx["shear_kt"]
        tm["cell_nmi"] = wx["cell_nmi"]
        n_eng = min(int(self.vs.get("engines", 1)), MAX_ENGINE_CHANNELS)
        for i in range(1, n_eng + 1):
            tm[f"chill_k_{i}"] = round(self._chill_k(i), 1)
        if self.phase == "flight":
            eo = self.anomalies.get("engine_out")
            for i in range(1, n_eng + 1):
                pc = 96.0 + 2.0 * math.sin(self.abs_t / 3.1 + i)
                if eo and eo["engine"] == i:
                    # chamber pressure decays for ~4 s BEFORE the
                    # shutdown callout — the readable precursor
                    ramp = (self.clock_s - (eo["t_clock"] - 4.0)) / 4.0
                    pc *= max(0.0, 1.0 - max(0.0, min(1.0, ramp)))
                tm[f"pc_bar_{i}"] = round(pc, 1)
            sd = self.anomalies.get("sensor_disagree")
            delta = 0.05 + 0.03 * math.sin(self.abs_t / 7.0)
            if sd and self.clock_s >= sd["t_clock"]:
                delta += (self.clock_s - sd["t_clock"]) \
                    * sd["rate_deg_s"]
            tm["nav_delta_deg"] = round(delta, 2)
        self._refresh_cautions()

    def _refresh_cautions(self) -> None:
        tm = self.telemetry
        cautions: list[str] = []
        for key, (lo, hi) in TELEMETRY_BANDS.items():
            v = tm.get(key)
            if v is not None and not (lo <= v <= hi):
                cautions.append(key)
        if tm.get("cell_nmi", 99.0) < CELL_LIMIT_NMI:
            cautions.append("cell_nmi")
        chans = [v for k, v in tm.items() if k.startswith("chill_k_")]
        if chans and "engine_chill" in self.fired:
            med = sorted(chans)[len(chans) // 2]
            for k, v in tm.items():
                if k.startswith("chill_k_") and v - med > 25.0:
                    cautions.append(k)
        pcs = [v for k, v in tm.items() if k.startswith("pc_bar_")]
        if pcs:
            top = max(pcs)
            for k, v in tm.items():
                if k.startswith("pc_bar_") and top > 0 and v < 0.85 * top:
                    cautions.append(k)
        self.cautions = cautions

    # -- persistence ----------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "vs": dict(self.vs), "site": self.site, "t0": self.t0,
            "seed_key": self.seed_key, "clock_s": self.clock_s,
            "abs_t": self.abs_t, "phase": self.phase,
            "attempt": self.attempt,
            "holds": [dict(h) for h in self.holds],
            "passed": list(self.passed), "fired": list(self.fired),
            "accepted_risks": list(self.accepted_risks),
            "chatter": [dict(c) for c in self.chatter],
            "log": [dict(e) for e in self.log],
            "anomalies": {k: dict(v) for k, v in self.anomalies.items()},
            "flight": dict(self._flight), "q_max": self._q_max,
            "count_said": list(self._count_said),
            "abort_recommended": self.abort_recommended,
            "abort_posture": self.abort_posture,
            "anom_marks": dict(getattr(self, "_anom_marks", {})),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Countdown":
        cd = cls(d["vs"], d["site"], d["t0"], d["seed_key"],
                 clock_s=d["clock_s"])
        cd.abs_t = d["abs_t"]
        cd.phase = d["phase"]
        cd.attempt = d["attempt"]
        cd.holds = [dict(h) for h in d.get("holds", [])]
        cd.passed = list(d.get("passed", []))
        cd.fired = list(d.get("fired", []))
        cd.accepted_risks = list(d.get("accepted_risks", []))
        cd.chatter = [dict(c) for c in d.get("chatter", [])]
        cd.log = [dict(e) for e in d.get("log", [])]
        cd._flight = dict(d.get("flight", {}))
        cd._q_max = d.get("q_max", 0.0)
        cd._count_said = list(d.get("count_said", []))
        cd.abort_recommended = d.get("abort_recommended")
        cd.abort_posture = d.get("abort_posture", "pad abort")
        cd._roll_attempt()
        # restore mutable anomaly progress over the fresh rolls
        for k, v in d.get("anomalies", {}).items():
            cd.anomalies[k] = dict(v)
        cd._anom_marks = dict(d.get("anom_marks", {}))
        cd._update_telemetry()
        return cd
