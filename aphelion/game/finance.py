"""Program finance v2 (12 §2.8 G-9, §2.2 E-4, §2.4, §1.3 E-9…E-11,
§1.7 E-17…E-19, §1.8 E-20…E-23, §1.10 F-2…F-4; DECISIONS F33): the
rate-based money ledger and its consumers — investors, the bridge loan,
insurance, stand-downs, rescues, and death economics.

The CashLedger is G-9's analytic integrator: money is income/expense
STREAMS (USD/s) with start/stop times plus timestamped discrete events;
`balance(t)` is closed-form, so a 2-year warp accrues zero drift versus
stepping daily. It is a DEPTH layer over the existing
`aphelion.sim.economy.Program`: `settle_into()` applies stream accruals
to a live Program (same funds/history/save shape — main.py's discrete
30-day overhead burn reproduces exactly as one stream, so the swap-over
causes no balance jump), and the contract-v2 helpers accept/produce the
persisted contract dict shape (contract_id/description/payout/
deadline_s/completed_t/failed) with all new fields defaulted.

Money is constant-2049 USD throughout. No wall clock, no rng.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

DAY = 86_400.0
YEAR = 365.0 * DAY
MONTH = YEAR / 12.0          # finance month (loans, promises, services)
QUARTER = YEAR / 4.0         # lease billing period (E-4)
MONTH_30D = 30.0 * DAY       # legacy main.py overhead period


# =============================================================================
# G-9: the rate-based cash ledger
# =============================================================================

@dataclass(slots=True)
class Stream:
    """One recurring money rate: income > 0, cost < 0, in USD/s,
    active on [start_s, stop_s)."""
    stream_id: str
    rate: float
    start_s: float
    stop_s: float = math.inf

    def overlap_s(self, a: float, b: float) -> float:
        return max(0.0, min(b, self.stop_s) - max(a, self.start_s))


@dataclass
class CashLedger:
    """G-9 analytic finance: `Cash(t) = cash0 + Σ rate·overlap + Σ events`.
    Streams are piecewise-constant rates; events are queued with
    timestamps — both integrate exactly, never per-tick."""
    cash0: float
    t0: float = 0.0
    streams: list[Stream] = field(default_factory=list)
    events: list[tuple[float, str, float]] = field(default_factory=list)
    settled_s: float | None = None        # wrapped-mode bookmark

    # -- streams ------------------------------------------------------------
    def start(self, stream_id: str, rate: float, t: float) -> Stream:
        """Open a stream; an already-open stream with the same id is
        stopped at t first (a rate CHANGE is stop+start, so the
        integral stays piecewise-exact)."""
        self.stop(stream_id, t)
        s = Stream(stream_id, rate, t)
        self.streams.append(s)
        return s

    def stop(self, stream_id: str, t: float) -> None:
        for s in self.streams:
            if s.stream_id == stream_id and s.stop_s == math.inf:
                s.stop_s = max(s.start_s, t)

    def rate(self, t: float) -> float:
        return sum(s.rate for s in self.streams
                   if s.start_s <= t < s.stop_s)

    def monthly_lines(self, t: float) -> dict[str, float]:
        """S-13 HQ $ Ledger rows: active in/out $/month by stream id."""
        out: dict[str, float] = {}
        for s in self.streams:
            if s.start_s <= t < s.stop_s:
                out[s.stream_id] = out.get(s.stream_id, 0.0) + s.rate * MONTH
        return out

    # -- discrete events ------------------------------------------------------
    def post(self, t: float, what: str, amount: float) -> None:
        self.events.append((t, what, amount))

    # -- the closed form ------------------------------------------------------
    def balance(self, t: float) -> float:
        b = self.cash0
        for s in self.streams:
            b += s.rate * s.overlap_s(self.t0, t)
        for te, _, amount in self.events:
            if te <= t:
                b += amount
        return b

    def runway_days(self, t: float, cash: float | None = None) -> float:
        """E-4: `runway_d = Cash / max(ε, −net rate)` over recurring
        rates only (discrete events excluded); ∞ while net rate ≥ 0."""
        c = self.balance(t) if cash is None else cash
        r = self.rate(t)
        if r >= 0.0:
            return math.inf
        return max(0.0, c) / (-r) / DAY

    def zero_crossing(self, t_a: float, t_b: float,
                      cash_a: float | None = None) -> float | None:
        """G-9: first time in (t_a, t_b] where Cash changes sign — the
        forced warp-drop time. None if the sign never changes."""
        cash = self.balance(t_a) if cash_a is None else cash_a
        cuts = {t_b}
        for s in self.streams:
            for x in (s.start_s, s.stop_s):
                if t_a < x < t_b:
                    cuts.add(x)
        ev: dict[float, float] = {}
        for te, _, amount in self.events:
            if t_a < te <= t_b:
                ev[te] = ev.get(te, 0.0) + amount
                cuts.add(te)
        cur = t_a
        for bp in sorted(cuts):
            r = self.rate(cur)
            nxt = cash + r * (bp - cur)
            if (cash > 0.0) != (nxt > 0.0):
                return cur - cash / r       # r != 0 whenever the sign flips
            cash = nxt
            if bp in ev:
                bumped = cash + ev[bp]
                if (cash > 0.0) != (bumped > 0.0):
                    return bp
                cash = bumped
            cur = bp
        return None

    # -- the Program bridge ----------------------------------------------------
    def settle_into(self, program, t: float) -> float:
        """Apply stream accruals since the last settle to a live
        sim.economy.Program (funds/history/save shape untouched).
        Expense clamps at available funds exactly like main.py's
        discrete burn; ledger events are NOT applied (in wrapped mode
        discrete cash keeps flowing through the Program itself)."""
        a = self.t0 if self.settled_s is None else self.settled_s
        if t <= a:
            return 0.0
        self.settled_s = t
        inc = sum(s.rate * s.overlap_s(a, t)
                  for s in self.streams if s.rate > 0.0)
        exp = -sum(s.rate * s.overlap_s(a, t)
                   for s in self.streams if s.rate < 0.0)
        if inc > 0.0:
            program.earn(t, inc, "streams")
        applied = 0.0
        if exp > 0.0:
            applied = min(exp, program.funds)
            program.spend(t, applied, "program overhead")
        return inc - applied

    # -- save (additive section; JSON-safe: inf encodes as None) ---------------
    def to_dict(self) -> dict:
        return {
            "cash0": self.cash0, "t0": self.t0, "settled_s": self.settled_s,
            "streams": [{"id": s.stream_id, "rate": s.rate,
                         "start_s": s.start_s,
                         "stop_s": (None if s.stop_s == math.inf
                                    else s.stop_s)}
                        for s in self.streams],
            "events": [list(e) for e in self.events],
        }

    @classmethod
    def from_dict(cls, d: dict) -> CashLedger:
        lg = cls(cash0=d["cash0"], t0=d.get("t0", 0.0),
                 settled_s=d.get("settled_s"))
        for sd in d.get("streams", []):
            lg.streams.append(Stream(
                sd["id"], sd["rate"], sd["start_s"],
                math.inf if sd.get("stop_s") is None else sd["stop_s"]))
        lg.events = [(e[0], e[1], e[2]) for e in d.get("events", [])]
        return lg


# G-9 death spiral: runway alert thresholds
RUNWAY_CLASS3_D = 60.0
RUNWAY_CLASS2_D = 14.0


def runway_alert_class(runway_d: float) -> int | None:
    """G-9: runway < 60 d → Class-3; < 14 d → Class-2 (+ auto bridge
    offer, see `bridge_offer`). None when comfortable."""
    if runway_d < RUNWAY_CLASS2_D:
        return 2
    if runway_d < RUNWAY_CLASS3_D:
        return 3
    return None


def bridge_offer(runway_d: float) -> bool:
    return runway_d < RUNWAY_CLASS2_D


# =============================================================================
# Overhead & salary stream builders (legacy main.py + E-4 + §2.4)
# =============================================================================

# legacy main.py monthly overhead ($M per 30 d, scaled by difficulty)
OVERHEAD_FIXED_M = 1.5
OVERHEAD_PER_CREW_M = 0.4
OVERHEAD_PER_BASE_M = 1.0


def legacy_overhead_rate(n_crew: int, n_bases: int,
                         difficulty_mult: float = 1.0) -> float:
    """main.py's burn — (1.5 + 0.4/crew + 1.0/base) $M per 30 d ×
    difficulty — as one G-9 cost rate (USD/s, negative). Integrating
    this stream reproduces the discrete burn exactly, so main can swap
    over with no balance jump."""
    m_usd = (OVERHEAD_FIXED_M + OVERHEAD_PER_CREW_M * n_crew
             + OVERHEAD_PER_BASE_M * n_bases) * 1e6 * difficulty_mult
    return -m_usd / MONTH_30D


# E-4 daily overhead
E4_DAILY_HQ = 40_000.0
E4_DAILY_PER_PAD = 10_000.0
E4_DAILY_PER_UNCREWED = 5_000.0
E4_DAILY_PER_CREWED_VESSEL = 30_000.0
LEASE_LAUNCH_SITE_Q = 0.3e6          # $/quarter
LEASE_TRACKING_Q = 0.5e6             # $/quarter (DSN; auto-cancel rule)
PAD_BUILD_COST = 20e6                # second pad, one-time


def e4_overhead_per_day(n_pads: int = 1, n_uncrewed: int = 0,
                        n_crewed_vessels: int = 0,
                        launch_site_leases: int = 1,
                        tracking: bool = False,
                        salaries_per_year: float = 0.0) -> float:
    """E-4: `OH = $40k (HQ) + $10k×pads + $5k×uncrewed missions +
    $30k×crewed vessels + Σ leases + Σ salaries`, in USD/day."""
    leases_q = (launch_site_leases * LEASE_LAUNCH_SITE_Q
                + (LEASE_TRACKING_Q if tracking else 0.0))
    return (E4_DAILY_HQ + E4_DAILY_PER_PAD * n_pads
            + E4_DAILY_PER_UNCREWED * n_uncrewed
            + E4_DAILY_PER_CREWED_VESSEL * n_crewed_vessels
            + leases_q / (QUARTER / DAY)
            + salaries_per_year / (YEAR / DAY))


def e4_overhead_rate(**kw) -> float:
    """The E-4 overhead as a G-9 cost rate (USD/s, negative)."""
    return -e4_overhead_per_day(**kw) / DAY


# §2.4 salaries & staffing
SALARY_RESERVE_Y = 0.25e6        # Earth-side reserve, $/yr
SALARY_FLIGHT_Y = 1.0e6          # flight status, $/yr
PENSION_Y = 0.1e6                # retired crew (DECISIONS F33), $/yr
SIGNING_BONUS = {"low": 2e6, "mid": 5e6, "high": 12e6}
TRAINING_COST = 2e6
TRAINING_DAYS = 90.0
RECRUIT_POOL_PER_QUARTER = 4


def salary_per_year(n_reserve: int, n_flight: int,
                    n_retired: int = 0) -> float:
    return (SALARY_RESERVE_Y * n_reserve + SALARY_FLIGHT_Y * n_flight
            + PENSION_Y * n_retired)


def salary_rate(n_reserve: int, n_flight: int, n_retired: int = 0) -> float:
    """Crew payroll as a G-9 cost rate (USD/s, negative); enters E-4
    Σsalaries."""
    return -salary_per_year(n_reserve, n_flight, n_retired) / YEAR


# E-12 standing service lines
STANDING_SERVICES: dict[str, dict] = {
    "leo_constellation": {
        "name": "LEO constellation maintenance",
        "income_per_month": 5.0e6, "unlock_contracts": ("CT-03", "CT-05")},
    "stationkeeping": {
        "name": "Station-keeping boost services",
        "income_per_month": 2.0e6,
        "unlock_contracts": ("CT-04", "CT-08", "CT-09")},
    "planetary_data": {
        "name": "Planetary-data subscription",
        "per_gb": 0.2e6, "cap_gb_per_year": 50.0,
        "unlock_contracts": ("CT-18", "CT-22")},
}
SERVICE_UNLOCK_COMPLETIONS = 2


def service_unlocked(line: str, completions: dict[str, int]) -> bool:
    """E-12: unlocks after any qualifying template completed twice."""
    return any(completions.get(cid, 0) >= SERVICE_UNLOCK_COMPLETIONS
               for cid in STANDING_SERVICES[line]["unlock_contracts"])


def service_rate(line: str) -> float:
    """Monthly service income as a G-9 rate (USD/s, positive)."""
    return STANDING_SERVICES[line]["income_per_month"] / MONTH


def data_payment(gb: float, sold_this_year_gb: float) -> float:
    """E-12 planetary-data line: $0.2M/GB, capped 50 GB/yr."""
    svc = STANDING_SERVICES["planetary_data"]
    room = max(0.0, svc["cap_gb_per_year"] - sold_this_year_gb)
    return svc["per_gb"] * min(gb, room)


def next_month_s(t: float) -> float:
    return (math.floor(t / MONTH) + 1.0) * MONTH


@dataclass(slots=True)
class ServiceLine:
    """E-12 suspension machine: a failed quarterly check suspends from
    the next month (no penalty, lost income only); a satisfied quarter
    while suspended resumes the month after it."""
    line: str
    suspended: bool = False

    def quarterly_check(self, ledger: CashLedger, t: float,
                        satisfied: bool) -> str:
        sid = f"svc:{self.line}"
        if not satisfied and not self.suspended:
            ledger.stop(sid, next_month_s(t))
            self.suspended = True
            return "suspend"
        if satisfied and self.suspended:
            ledger.start(sid, service_rate(self.line), next_month_s(t))
            self.suspended = False
            return "resume"
        return "none"


# ISRU offtake (e.g. CT-19: Pu238 to agency at $10M/kg, ≤ 5 kg/yr)
CT19_PU238_PER_KG = 10e6
CT19_CAP_KG_Y = 5.0


def offtake_stream(ledger: CashLedger, stream_id: str, price_per_kg: float,
                   kg_per_year: float, t: float) -> Stream:
    """A standing offtake agreement as a G-9 income rate."""
    return ledger.start(stream_id, price_per_kg * kg_per_year / YEAR, t)


# =============================================================================
# Contract v2 (E-9…E-11) — wraps the persisted Program contract shape
# =============================================================================

PERSISTED_KEYS = ("contract_id", "description", "payout", "deadline_s",
                  "completed_t", "failed")
ADVANCE_FRAC = 0.10              # E-9: accept → 10% advance
FAIL_PENALTY_FRAC = 0.20         # E-10: + 20% of total value
FAIL_PRESTIGE = -10.0
CUSTOMER_LOCKOUT_Y = 1.0
PAYLOAD_PENALTY_PER_T = 10e6     # E-10 mass-delivery insured value
CUSTOMER_HARDWARE_MULT = 2.0     # E-10 customer-supplied hardware
URGENT_K = 1.5                   # E-11
URGENT_DEADLINE_MULT = 0.5
URGENT_OFFER_FRAC = 0.25
RATE_DECLINE_PER_Y = 0.92        # E-11: all rates decline 8%/yr
DEADLINE_MIN_D = 90.0            # E-9 default deadline floor

V2_DEFAULTS = {"advance_frac": ADVANCE_FRAC, "tranches": 1,
               "paid_tranches": 0, "advance_paid_t": None,
               "crewed": False, "urgent": False, "customer": "agency"}


def _cget(c, key: str, default=None):
    if isinstance(c, dict):
        return c.get(key, default)
    return getattr(c, key, default)


def _cset(c, key: str, value) -> None:
    if isinstance(c, dict):
        c[key] = value
    else:
        setattr(c, key, value)


def contract_v2(c) -> dict:
    """Lift a persisted contract dict OR a sim.economy.Contract into
    the v2 dict shape: the six persisted keys plus every new field at
    its default. Non-destructive; extras already present win."""
    base = (dict(c) if isinstance(c, dict)
            else {k: getattr(c, k) for k in PERSISTED_KEYS if hasattr(c, k)})
    out = dict(V2_DEFAULTS)
    out.update(base)
    out.setdefault("completed_t", None)
    out.setdefault("failed", False)
    return out


def contract_save_shape(c) -> dict:
    """Project back to EXACTLY the keys aphelion/save/campaign.py
    persists today — `Contract(**contract_save_shape(d))` stays valid."""
    d = contract_v2(c)
    return {k: d[k] for k in PERSISTED_KEYS}


def tranche_amounts(payout: float, n_tranches: int,
                    advance_frac: float = ADVANCE_FRAC
                    ) -> tuple[float, list[float]]:
    """E-9: 10% advance at accept, remainder in equal per-unit
    tranches (CT-17: $1.5B in 3 → $150M advance + 3 × $450M)."""
    adv = advance_frac * payout
    per = (payout - adv) / n_tranches
    return adv, [per] * n_tranches


def accept_contract(ledger: CashLedger, c, t: float) -> float:
    """E-9 accept: post the 10% advance; marks advance_paid_t."""
    adv = _cget(c, "advance_frac", ADVANCE_FRAC) * _cget(c, "payout")
    ledger.post(t, f"contract:{_cget(c, 'contract_id')}:advance", adv)
    _cset(c, "advance_paid_t", t)
    return adv


def pay_tranche(ledger: CashLedger, c, t: float) -> float:
    """E-9 multi-part completion: pay the next per-unit tranche."""
    n = _cget(c, "tranches", 1)
    paid = _cget(c, "paid_tranches", 0)
    if paid >= n:
        return 0.0
    _, per = tranche_amounts(_cget(c, "payout"), n,
                             _cget(c, "advance_frac", ADVANCE_FRAC))
    amount = per[paid]
    ledger.post(t, f"contract:{_cget(c, 'contract_id')}:tranche{paid + 1}",
                amount)
    _cset(c, "paid_tranches", paid + 1)
    return amount


def failure_cost(c, *, payload_destroyed_t: float = 0.0,
                 customer_hardware: bool = False) -> dict:
    """E-10: repay the advance + 20% of total value + Prestige −10 +
    customer templates locked 1 yr; destroyed customer payload adds
    insured value (2 × value for supplied hardware, $10M/t for mass
    delivery)."""
    payout = _cget(c, "payout")
    repay = (0.0 if _cget(c, "advance_paid_t") is None
             else _cget(c, "advance_frac", ADVANCE_FRAC) * payout)
    addendum = (CUSTOMER_HARDWARE_MULT * payout if customer_hardware
                else PAYLOAD_PENALTY_PER_T * payload_destroyed_t)
    return {"cash": -(repay + FAIL_PENALTY_FRAC * payout + addendum),
            "prestige": FAIL_PRESTIGE,
            "customer_lockout_y": CUSTOMER_LOCKOUT_Y}


def default_deadline_s(accept_t: float, t_min_transfer_s: float) -> float:
    """E-9: `T_accept + max(2 × t_min_transfer, 90 d)`."""
    return accept_t + max(2.0 * t_min_transfer_s, DEADLINE_MIN_D * DAY)


def declined(value0: float, years_since_2049: float) -> float:
    """E-11: all rates decline 8%/yr — standing still shrinks margins."""
    return value0 * RATE_DECLINE_PER_Y ** years_since_2049


def urgent_terms(payout: float, window_s: float) -> tuple[float, float]:
    """E-11: urgent offers pay ×1.5 on half the deadline."""
    return payout * URGENT_K, window_s * URGENT_DEADLINE_MULT


# =============================================================================
# Insurance (E-20…E-22)
# =============================================================================

INSURE_CAP = 2.0e9               # E-20: cap $2B per risk
COVER_TERM_S = YEAR              # launch + 1 yr ops, Earth SOI only
PREMIUM_RATE = 0.06              # E-21
F_PAYLOAD_NUCLEAR = 1.5
NUCLEAR_LICENSE_LEAD_D = 60.0
CLAIM_CRIPPLED_FRAC = 0.50       # E-22
ASSESSOR_D = 7.0
FRAUD_STRIKES = 3                # third voided/edge claim in 10 yr …
FRAUD_WINDOW_Y = 10.0            # … ends offers for the vehicle line


def f_history(flights: int, consecutive_successes: int) -> float:
    """E-21: 2.0 (<3 flights) · 0.6 (>10 consecutive successes; any
    failure resets the streak, hence to 1.0) · else 1.0."""
    if flights < 3:
        return 2.0
    if consecutive_successes > 10:
        return 0.6
    return 1.0


def insured_value(hardware_value: float, cargo_value: float = 0.0) -> float:
    """E-20: hardware catalog value + declared cargo, cap $2B."""
    return min(hardware_value + cargo_value, INSURE_CAP)


def premium(v_insured: float, flights: int, consecutive_successes: int,
            nuclear: bool = False) -> float:
    """E-21: `V × 6% × f_history × f_payload` (bounds 3.6–12% of V
    before the ×1.5 nuclear rider)."""
    f_pay = F_PAYLOAD_NUCLEAR if nuclear else 1.0
    return (v_insured * PREMIUM_RATE
            * f_history(flights, consecutive_successes) * f_pay)


@dataclass(slots=True)
class Policy:
    policy_id: str
    line: str                    # vehicle line (fraud guard granularity)
    insured_value: float
    premium: float
    start_s: float
    nuclear: bool = False
    claimed: bool = False

    @property
    def end_s(self) -> float:
        return self.start_s + COVER_TERM_S

    def covered(self, t: float, in_earth_soi: bool = True) -> bool:
        """E-20 envelope: in force, inside Earth's SOI, not yet
        claimed (deep space is uninsurable)."""
        return (in_earth_soi and not self.claimed
                and self.start_s <= t <= self.end_s)


@dataclass
class InsuranceBook:
    policies: list[Policy] = field(default_factory=list)
    strikes: list[tuple[float, str]] = field(default_factory=list)

    def offers_available(self, line: str, t: float) -> bool:
        """E-22 fraud guard: a third voided/edge claim within 10 yr
        ends coverage offers for that vehicle line."""
        n = sum(1 for ts, ln in self.strikes
                if ln == line and t - ts <= FRAUD_WINDOW_Y * YEAR)
        return n < FRAUD_STRIKES

    def underwrite(self, ledger: CashLedger, t: float, line: str,
                   hardware_value: float, cargo_value: float = 0.0, *,
                   flights: int = 0, consecutive_successes: int = 0,
                   nuclear: bool = False,
                   amortize: bool = True) -> Policy | None:
        """Bind a policy; the premium lands either amortized as a G-9
        cost stream over the term or as one discrete event (equal
        totals). Nuclear payloads also need a 60-d licensing lead."""
        if not self.offers_available(line, t):
            return None
        v = insured_value(hardware_value, cargo_value)
        p = premium(v, flights, consecutive_successes, nuclear)
        pol = Policy(f"{line}#{len(self.policies)}", line, v, p, t, nuclear)
        sid = f"premium:{pol.policy_id}"
        if amortize:
            ledger.start(sid, -p / COVER_TERM_S, t)
            ledger.stop(sid, t + COVER_TERM_S)
        else:
            ledger.post(t, sid, -p)
        self.policies.append(pol)
        return pol

    def claim(self, ledger: CashLedger, policy: Policy, t: float, *,
              total_loss: bool = True, in_earth_soi: bool = True,
              player_commanded: bool = False, failure_event: bool = True,
              engineered: bool = False) -> dict:
        """E-22: total loss pays insured value now; recoverable-but-
        crippled pays 50% after the 7-d assessor event. Scuttling or
        any claim without a reliability-system failure event is VOIDED
        (and counts a fraud strike); 'engineered' failures pay but
        reprice (f_history resets — caller zeroes its success streak)
        and also count a strike."""
        if not policy.covered(t, in_earth_soi):
            return {"payout": 0.0, "status": "denied",
                    "f_history_reset": False}
        if player_commanded or not failure_event:
            policy.claimed = True
            self.strikes.append((t, policy.line))
            return {"payout": 0.0, "status": "voided",
                    "f_history_reset": False}
        payout = (policy.insured_value if total_loss
                  else CLAIM_CRIPPLED_FRAC * policy.insured_value)
        payable_s = t if total_loss else t + ASSESSOR_D * DAY
        ledger.post(payable_s, f"claim:{policy.policy_id}", payout)
        policy.claimed = True
        if engineered:
            self.strikes.append((t, policy.line))
        return {"payout": payout, "payable_s": payable_s,
                "status": "paid", "f_history_reset": engineered}

    def to_dict(self) -> dict:
        return {"policies": [{
                    "policy_id": p.policy_id, "line": p.line,
                    "insured_value": p.insured_value, "premium": p.premium,
                    "start_s": p.start_s, "nuclear": p.nuclear,
                    "claimed": p.claimed} for p in self.policies],
                "strikes": [list(s) for s in self.strikes]}

    @classmethod
    def from_dict(cls, d: dict) -> InsuranceBook:
        book = cls()
        for pd in d.get("policies", []):
            book.policies.append(Policy(**pd))
        book.strikes = [(s[0], s[1]) for s in d.get("strikes", [])]
        return book


# =============================================================================
# Stand-downs (E-23)
# =============================================================================

STANDDOWN_GROUND_D = 30.0        # uncrewed-vehicle fatality (pad worker)
STANDDOWN_FLIGHT_D = 90.0        # in-flight, cause found quickly
STANDDOWN_MAJOR_D = 180.0        # in-flight, founder or multiple deaths
IRONMAN_STANDDOWN_MULT = 2.0
STANDDOWN_PRESTIGE_PER_MO = -5.0


def stand_down_duration_s(*, in_flight: bool, founder: bool = False,
                          fatalities: int = 1,
                          ironman: bool = False) -> float:
    if not in_flight:
        d = STANDDOWN_GROUND_D
    elif founder or fatalities >= 2:
        d = STANDDOWN_MAJOR_D
    else:
        d = STANDDOWN_FLIGHT_D
    return d * DAY * (IRONMAN_STANDDOWN_MULT if ironman else 1.0)


@dataclass(slots=True)
class StandDown:
    """E-23: crewed launches freeze; uncrewed flights continue; crewed
    contract deadlines pause (the only force-majeure source); Prestige
    bleeds −5/month while it lasts."""
    start_s: float
    duration_s: float
    cause: str = ""

    @property
    def end_s(self) -> float:
        return self.start_s + self.duration_s

    def active(self, t: float) -> bool:
        return self.start_s <= t < self.end_s

    def prestige_drift(self, t_a: float, t_b: float) -> float:
        overlap = max(0.0, min(t_b, self.end_s) - max(t_a, self.start_s))
        return STANDDOWN_PRESTIGE_PER_MO * overlap / MONTH


def launch_allowed(sd: StandDown | None, t: float, crewed: bool) -> bool:
    if sd is None or not crewed:
        return True
    return not sd.active(t)


def pause_crewed_deadlines(contracts, sd: StandDown) -> int:
    """Force majeure: extend every open CREWED contract's deadline by
    the stand-down duration (accepts v2 dicts or Contract objects; a
    contract without a crewed flag defaults uncrewed). Returns the
    count paused."""
    n = 0
    for c in contracts:
        if (_cget(c, "crewed", False) and _cget(c, "completed_t") is None
                and not _cget(c, "failed", False)):
            _cset(c, "deadline_s", _cget(c, "deadline_s") + sd.duration_s)
            n += 1
    return n


# =============================================================================
# Investors & debt (E-17…E-19; DECISIONS F33)
# =============================================================================

@dataclass(frozen=True)
class Round:
    round_id: str
    gate: float                  # Prestige gate (E-14 tiers 50/150/300/500)
    cash: float
    promise_mo: float            # promise deadline, months


ROUNDS: dict[str, Round] = {
    "seed": Round("seed", 0.0, 300e6, 0.0),         # pre-banked (E-1)
    "series_a": Round("series_a", 50.0, 250e6, 36.0),
    "series_b": Round("series_b", 150.0, 600e6, 36.0),
    "series_c": Round("series_c", 300.0, 1.5e9, 36.0),
    "series_d": Round("series_d", 500.0, 4.0e9, 48.0),
}
ROUND_ORDER = ("seed", "series_a", "series_b", "series_c", "series_d")

PROMISE_FAIL_PRESTIGE = -100.0
PROMISE_LOCKOUT_Y = 5.0
OVERHEAD_SURCHARGE = 1.10        # +10% board-oversight overhead
PROMISE_OVERHEAD_Y = 2.0

# E-19 money fade trigger
FADE_SSI = 0.8
FADE_SUSTAIN_D = 730.0

# E-18 bridge loan
BRIDGE_APR = 0.12
BRIDGE_INTEREST_PER_MO = 0.01    # 1% of outstanding principal/month
BRIDGE_TERM_MO = 24.0            # bullet at 24 months
BRIDGE_REVENUE_FRAC = 0.25       # ≤ 25% trailing-12-mo revenue


def prestige_floor(highest_gate_crossed: float) -> float:
    """E-14: `max(0, highest gate ever crossed − 100)` — history can't
    be fully erased."""
    return max(0.0, highest_gate_crossed - 100.0)


@dataclass
class Investors:
    """E-17 rounds are milestone-gated grants with a promise: cash up
    front (no clawback), one Firsts milestone owed by the deadline.
    Post-fade (E-19) the board is advisory: promises lose their
    penalty clauses and no further rounds are offered."""
    raised: list[str] = field(default_factory=lambda: ["seed"])
    promise: dict | None = None
    lockout_until_s: float = 0.0
    surcharges: list[tuple[float, float, float]] = field(
        default_factory=list)              # (start_s, end_s, mult)
    advisory: bool = False

    def can_raise(self, round_id: str, prestige: float, t: float) -> bool:
        r = ROUNDS.get(round_id)
        if (r is None or self.advisory or round_id in self.raised
                or self.promise is not None or t < self.lockout_until_s
                or prestige < r.gate):
            return False
        prev = ROUND_ORDER[ROUND_ORDER.index(round_id) - 1]
        return prev in self.raised

    def raise_round(self, ledger: CashLedger, round_id: str,
                    prestige: float, t: float,
                    promise_milestone: str) -> float:
        if not self.can_raise(round_id, prestige, t):
            return 0.0
        r = ROUNDS[round_id]
        ledger.post(t, f"round:{round_id}", r.cash)
        self.raised.append(round_id)
        self.promise = {"round_id": round_id,
                        "milestone": promise_milestone,
                        "deadline_s": t + r.promise_mo * MONTH}
        return r.cash

    def promise_overdue(self, t: float) -> bool:
        return self.promise is not None and t > self.promise["deadline_s"]

    def deliver_promise(self, t: float) -> bool:
        """Vests (cash was paid up front, no clawback)."""
        if self.promise is None or t > self.promise["deadline_s"]:
            return False
        self.promise = None
        return True

    def fail_promise(self, t: float) -> dict:
        """E-17 teeth: Prestige −100, no rounds 5 yr, overhead +10%
        for 2 yr — unless advisory (E-19), where penalty clauses are
        void."""
        self.promise = None
        if self.advisory:
            return {"prestige": 0.0}
        self.lockout_until_s = max(self.lockout_until_s,
                                   t + PROMISE_LOCKOUT_Y * YEAR)
        self.surcharges.append((t, t + PROMISE_OVERHEAD_Y * YEAR,
                                OVERHEAD_SURCHARGE))
        return {"prestige": PROMISE_FAIL_PRESTIGE}

    def overhead_mult(self, t: float) -> float:
        m = 1.0
        for a, b, mult in self.surcharges:
            if a <= t < b:
                m *= mult
        return m

    def set_advisory(self) -> None:
        """E-19 fade: board converts to advisory."""
        self.advisory = True

    def to_dict(self) -> dict:
        return {"raised": list(self.raised), "promise": self.promise,
                "lockout_until_s": self.lockout_until_s,
                "surcharges": [list(s) for s in self.surcharges],
                "advisory": self.advisory}

    @classmethod
    def from_dict(cls, d: dict) -> Investors:
        return cls(raised=list(d.get("raised", ["seed"])),
                   promise=d.get("promise"),
                   lockout_until_s=d.get("lockout_until_s", 0.0),
                   surcharges=[(s[0], s[1], s[2])
                               for s in d.get("surcharges", [])],
                   advisory=d.get("advisory", False))


@dataclass(slots=True)
class BridgeLoan:
    principal: float
    drawn_s: float

    @property
    def due_s(self) -> float:
        return self.drawn_s + BRIDGE_TERM_MO * MONTH


def trailing_revenue(ledger: CashLedger, t: float) -> float:
    """E-18 sizing basis: positive cash over the trailing 12 months —
    discrete receipts (contracts, milestones, sales) plus income
    streams; loan draws, round grants and insurance claims are not
    revenue."""
    a = t - YEAR
    rev = sum(amount for te, what, amount in ledger.events
              if a < te <= t and amount > 0.0
              and not what.startswith(("loan", "round", "claim")))
    rev += sum(s.rate * s.overlap_s(a, t)
               for s in ledger.streams if s.rate > 0.0)
    return rev


# =============================================================================
# Rescues, agency assist, death economics (F-2…F-4)
# =============================================================================

STRANDED_DV_MARGIN = 1.05        # F-2: Δv_required + 5%
RESCUE_DELIVERY_WAIVER_D = 7.0   # all rescue purchases: 7-d delivery
RESCUE_PRESTIGE = 50.0

AGENCY_ASSIST_MIN_COST = 500e6   # F-3: max($500M, 50% of treasury)
AGENCY_ASSIST_TREASURY_FRAC = 0.50
AGENCY_ASSIST_PRESTIGE = -100.0
AGENCY_ASSIST_PREP_D = 30.0

DEATH_BENEFIT = 10e6             # F-4, $ per fatality, to estate
FATALITY_PRESTIGE = -100.0       # E-14
FOUNDER_DEATH_PRESTIGE = -150.0
FOUNDER_DEATH_MORALE = -25.0
FOUNDER_OVERHEAD_Y = 1.0         # overhead +10% for 1 yr
OFFER_HAIRCUT = 0.50             # new contract offers −50% …
OFFER_HAIRCUT_MO = 6.0           # … for 6 months


def harbor_reachable(dv_available: float, dv_required: float,
                     transfer_days: float, ls_days: float) -> bool:
    return (dv_available >= STRANDED_DV_MARGIN * dv_required
            and transfer_days <= ls_days)


def is_stranded(ls_days: float,
                harbors: list[tuple[float, float, float]],
                other_craft_can_reach: bool = False) -> bool:
    """F-2: stranded iff (crew alive and) EVERY safe harbor — player
    bases/stations with berths+LS, plus Earth — fails the Δv (+5%) or
    transfer-time test, AND no other player craft can reach + dock in
    time. harbors: (Δv_available, Δv_required, transfer_days)."""
    if other_craft_can_reach:
        return False
    return all(not harbor_reachable(a, r, td, ls_days)
               for a, r, td in harbors)


@dataclass(slots=True)
class RescueObligation:
    """F-2 RESCUE objective: countdown = days of life support left."""
    created_s: float
    ls_days: float
    subject: str = ""

    @property
    def deadline_s(self) -> float:
        return self.created_s + self.ls_days * DAY

    def expired(self, t: float) -> bool:
        return t > self.deadline_s


def agency_assist_cost(treasury: float) -> float:
    return max(AGENCY_ASSIST_MIN_COST,
               AGENCY_ASSIST_TREASURY_FRAC * treasury)


# =============================================================================
# E-19 / G-9 endgame plumbing
# =============================================================================

SELL_FRACTION = 0.40             # E-6: Earth sales at 40% of list


def liquidation_value(catalog_value: float) -> float:
    """G-9 Liquidation flow: sell at 40%, cancel leases (crewed assets
    exempt until crew are home or dead)."""
    return SELL_FRACTION * catalog_value


def game_over(bankrupt: bool, has_income_source: bool,
              any_crew_alive: bool) -> bool:
    """G-9: true game-over ONLY at bankrupt AND no income source AND
    all crew dead/stranded."""
    return bankrupt and not has_income_source and not any_crew_alive


# =============================================================================
# The orchestrator
# =============================================================================

@dataclass
class FinanceState:
    """One bag main can own: the ledger plus every E-17…E-23/F-2…F-4
    consumer, with an additive JSON-safe save section."""
    ledger: CashLedger
    insurance: InsuranceBook = field(default_factory=InsuranceBook)
    investors: Investors = field(default_factory=Investors)
    stand_down: StandDown | None = None
    rescues: list[RescueObligation] = field(default_factory=list)
    loan: BridgeLoan | None = None
    agency_assist_used: bool = False
    offer_haircut_until_s: float = 0.0

    # -- stand-down face ------------------------------------------------------
    def crewed_launch_allowed(self, t: float) -> bool:
        return launch_allowed(self.stand_down, t, crewed=True)

    def offer_payout_mult(self, t: float) -> float:
        """F-4: new contract offers −50% for 6 months after a death."""
        return OFFER_HAIRCUT if t < self.offer_haircut_until_s else 1.0

    # -- death economics (F-4 + E-23) -------------------------------------------
    def crew_fatality(self, t: float, *, fatalities: int = 1,
                      in_flight: bool = True, founder: bool = False,
                      ironman: bool = False) -> dict:
        self.ledger.post(t, "death:benefit", -DEATH_BENEFIT * fatalities)
        dur = stand_down_duration_s(in_flight=in_flight, founder=founder,
                                    fatalities=fatalities, ironman=ironman)
        self.stand_down = StandDown(t, dur, cause="fatality")
        self.offer_haircut_until_s = t + OFFER_HAIRCUT_MO * MONTH
        if founder:
            self.investors.surcharges.append(
                (t, t + FOUNDER_OVERHEAD_Y * YEAR, OVERHEAD_SURCHARGE))
        return {"prestige": (FOUNDER_DEATH_PRESTIGE if founder
                             else FATALITY_PRESTIGE * fatalities),
                "morale_all_crew": FOUNDER_DEATH_MORALE if founder else 0.0,
                "death_benefit": DEATH_BENEFIT * fatalities,
                "stand_down_d": dur / DAY,
                "succession": founder and not ironman,
                "game_over": founder and ironman}

    # -- rescues (F-2) -----------------------------------------------------------
    def add_rescue(self, t: float, ls_days: float,
                   subject: str = "") -> RescueObligation:
        r = RescueObligation(t, ls_days, subject)
        self.rescues.append(r)
        return r

    def resolve_rescue(self, r: RescueObligation, success: bool) -> float:
        """Returns the Prestige delta (+50 on success)."""
        if r in self.rescues:
            self.rescues.remove(r)
        return RESCUE_PRESTIGE if success else 0.0

    # -- agency assist (F-3) ------------------------------------------------------
    def agency_assist(self, t: float,
                      treasury: float | None = None) -> dict | None:
        """Once per campaign: max($500M, 50% of treasury), Prestige
        −100, min 30 d prep (and the flight can still fail)."""
        if self.agency_assist_used:
            return None
        c = agency_assist_cost(self.ledger.balance(t)
                               if treasury is None else treasury)
        self.ledger.post(t, "agency:assist", -c)
        self.agency_assist_used = True
        return {"cost": c, "prestige": AGENCY_ASSIST_PRESTIGE,
                "ready_s": t + AGENCY_ASSIST_PREP_D * DAY}

    # -- bridge loan (E-18) --------------------------------------------------------
    def draw_bridge(self, t: float,
                    trailing: float | None = None) -> BridgeLoan | None:
        """One revolving instrument, ≤ 25% trailing-12-mo revenue;
        interest accrues as a G-9 cost rate (1%/month of principal)."""
        if self.loan is not None:
            return None
        rev = (trailing_revenue(self.ledger, t) if trailing is None
               else trailing)
        principal = BRIDGE_REVENUE_FRAC * rev
        if principal <= 0.0:
            return None
        self.loan = BridgeLoan(principal, t)
        self.ledger.post(t, "loan:draw", principal)
        self.ledger.start("loan:interest",
                          -principal * BRIDGE_INTEREST_PER_MO / MONTH, t)
        return self.loan

    def auto_bridge(self, t: float) -> BridgeLoan | None:
        """E-18: auto-drawn at Cash < 0."""
        if self.ledger.balance(t) < 0.0:
            return self.draw_bridge(t)
        return None

    def service_bridge(self, t: float,
                       cash: float | None = None) -> str | None:
        """Bullet at 24 months; auto-repaid earlier once
        Cash > 2 × principal; failure to repay at term → the
        Liquidation flow. Re-borrowable only after full repayment."""
        ln = self.loan
        if ln is None:
            return None
        c = self.ledger.balance(t) if cash is None else cash
        if c > 2.0 * ln.principal:
            self._repay(t)
            return "repaid"
        if t >= ln.due_s:
            if c >= ln.principal:
                self._repay(t)
                return "repaid"
            return "liquidation"
        return "accruing"

    def _repay(self, t: float) -> None:
        self.ledger.post(t, "loan:repay", -self.loan.principal)
        self.ledger.stop("loan:interest", t)
        self.loan = None

    # -- save -------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "ledger": self.ledger.to_dict(),
            "insurance": self.insurance.to_dict(),
            "investors": self.investors.to_dict(),
            "stand_down": (None if self.stand_down is None else
                           {"start_s": self.stand_down.start_s,
                            "duration_s": self.stand_down.duration_s,
                            "cause": self.stand_down.cause}),
            "rescues": [{"created_s": r.created_s, "ls_days": r.ls_days,
                         "subject": r.subject} for r in self.rescues],
            "loan": (None if self.loan is None else
                     {"principal": self.loan.principal,
                      "drawn_s": self.loan.drawn_s}),
            "agency_assist_used": self.agency_assist_used,
            "offer_haircut_until_s": self.offer_haircut_until_s,
        }

    @classmethod
    def from_dict(cls, d: dict) -> FinanceState:
        sd = d.get("stand_down")
        ln = d.get("loan")
        return cls(
            ledger=CashLedger.from_dict(d["ledger"]),
            insurance=InsuranceBook.from_dict(d.get("insurance", {})),
            investors=Investors.from_dict(d.get("investors", {})),
            stand_down=None if sd is None else StandDown(**sd),
            rescues=[RescueObligation(**r) for r in d.get("rescues", [])],
            loan=None if ln is None else BridgeLoan(**ln),
            agency_assist_used=d.get("agency_assist_used", False),
            offer_haircut_until_s=d.get("offer_haircut_until_s", 0.0),
        )
