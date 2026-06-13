"""12 §3.5 alert bus (A-1…A-6 + §8.3 storm rule + E-9/G-9 sweeps),
12 §4 Chronicle (C-1…C-4, §8.12 caps), and DECISIONS C19 births: warp
caps per class pinned, overlapping-alert law, latching Class 1 +
Accept-Risk logging, dedup/toast budgets, deadline alerts at T−90/30/7,
the mission-log export, and the save-shape newborn roster record."""

import json
import math

import pytest

from aphelion.game.alerts import (
    ADULT_AGE_YR, ALERT_CLASSES, CHILD_ENERGY_KCAL, CHRONICLE_TARGET_VOLUME,
    DEADLINE_ALERT_DAYS, DEDUP_WINDOW_S, ENTRY_CAP, ENTRY_KINDS,
    G_REPRO_BOUNDS, GESTATION_D, MASTER_ALARM_KEY, MIN_PARENT_CREW,
    RUNWAY_ALERT_DAYS, SNAPSHOT_CAP_BYTES, STORM_THRESHOLD, STORM_WINDOW_S,
    TOAST_BUDGET, WARP_CAPS, YEAR, Alert, AlertBus, Chronicle, birth_count,
    births_eligible, chapter_stats, chronicle_contract, deadline_sweep,
    draw_g_repro, export_text, g_repro_bracket, generations_reached,
    make_birth, new_crew_dict, record_birth, runway_sweep, sim_date,
)
from aphelion.game.crew import ROLES, CrewMember
from aphelion.sim.economy import Contract
from aphelion.sim.habitat.dose import CrewDose

DAY = 86_400.0


# ---- A-1: the four classes are LAW ------------------------------------------

def test_alert_classes_pinned():
    """§3.5 table: EMERGENCY pause / WARNING 1x / CAUTION 1,000x /
    ADVISORY none; colors per §3.4; exactly three alarm sounds."""
    assert sorted(ALERT_CLASSES) == [1, 2, 3, 4]
    assert ALERT_CLASSES[1]["name"] == "EMERGENCY"
    assert ALERT_CLASSES[2]["name"] == "WARNING"
    assert ALERT_CLASSES[3]["name"] == "CAUTION"
    assert ALERT_CLASSES[4]["name"] == "ADVISORY"
    assert WARP_CAPS[1] == pytest.approx(0.0)          # tier 0 + pause
    assert WARP_CAPS[2] == pytest.approx(1.0)
    assert WARP_CAPS[3] == pytest.approx(1_000.0)
    assert WARP_CAPS[4] == math.inf
    assert ALERT_CLASSES[1]["color"] == "#E25555"      # Emergency red
    assert ALERT_CLASSES[2]["color"] == "#E8893B"      # Warning orange
    assert ALERT_CLASSES[3]["color"] == "#E8C547"      # Caution amber
    assert ALERT_CLASSES[1]["pause"] and ALERT_CLASSES[1]["latching"]
    for c in (2, 3, 4):
        assert not ALERT_CLASSES[c]["pause"]
        assert not ALERT_CLASSES[c]["latching"]
    # §5.10: exactly three alarm sounds + silent advisories
    sounds = [ALERT_CLASSES[c]["sound"] for c in (1, 2, 3)]
    assert sounds == ["klaxon", "tone", "chime"]
    assert ALERT_CLASSES[4]["sound"] == "silent"
    assert MASTER_ALARM_KEY == "Delete"


def test_warp_law_overlapping_alerts():
    """A-2: min over active unacknowledged alerts; ack releases."""
    bus = AlertBus()
    t = 1_000.0
    a3 = bus.post(t, 3, "base:peary", "spares < 90 d", kind="spares")
    assert bus.highest_warp_cap(t) == pytest.approx(1_000.0)
    a2 = bus.post(t, 2, "ship:pelican", "LS critical band", kind="ls")
    assert bus.highest_warp_cap(t) == pytest.approx(1.0)   # lowest wins
    assert bus.warp_max_effective(100_000.0, t) == pytest.approx(1.0)
    assert bus.warp_max_effective(0.5, t) == pytest.approx(0.5)
    assert bus.acknowledge(a2.aid, t)                       # released
    assert bus.highest_warp_cap(t) == pytest.approx(1_000.0)
    assert bus.acknowledge(a3.aid, t)
    assert bus.highest_warp_cap(t) == math.inf
    # class 4 never caps, even unacknowledged
    bus.post(t, 4, "hq", "window opened", kind="window")
    assert bus.highest_warp_cap(t) == math.inf
    assert not bus.should_pause(t)


def test_class1_latching_accept_risk():
    """A-2: Class 1 latches — ack never lifts it; Accept-Risk does and
    logs RISK_ACCEPTED to the Chronicle forever."""
    chron = Chronicle()
    bus = AlertBus(chron)
    t = 500.0
    a1 = bus.post(t, 1, "base:peary", "rapid depress, hab ring",
                  kind="depress")
    assert bus.should_pause(t)
    assert bus.highest_warp_cap(t) == pytest.approx(0.0)
    assert not bus.acknowledge(a1.aid, t)        # latching: NOT released
    assert bus.highest_warp_cap(t) == pytest.approx(0.0)
    assert bus.should_pause(t)
    assert bus.accept_risk(a1.aid, t, "crew already in suits")
    assert bus.highest_warp_cap(t) == math.inf
    assert not bus.should_pause(t)
    logged = chron.by_kind("RISK_ACCEPTED")
    assert len(logged) == 1 and logged[0].cls == 1
    assert "base:peary" in logged[0].subjects
    # accept_risk is the Class-1 covered switch only
    a2 = bus.post(t, 2, "x", "warning", kind="w")
    assert not bus.accept_risk(a2.aid, t)
    # resolution also releases a Class 1
    b1 = bus.post(t, 1, "ship:k", "fire", kind="fire")
    assert bus.highest_warp_cap(t) == pytest.approx(0.0)
    bus.resolve(b1.aid)
    assert b1.released()


def test_expiry_and_resolution():
    bus = AlertBus()
    a = bus.post(0.0, 3, "site:x", "conjunction watch",
                 kind="conj", expires_s=3_600.0)
    assert a in bus.active(1_000.0)
    assert bus.highest_warp_cap(1_000.0) == pytest.approx(1_000.0)
    assert a not in bus.active(3_600.0)          # lapsed
    assert bus.highest_warp_cap(3_600.0) == math.inf


def test_dedup_24h_merge():
    """A-3: identical (source, type) within 24 h merge with ×N."""
    bus = AlertBus()
    a = bus.post(0.0, 3, "base:m", "boiloff margin", kind="boiloff")
    b = bus.post(10.0 * 3_600.0, 3, "base:m", "boiloff margin",
                 kind="boiloff")
    assert b is a and a.count == 2
    assert len(bus.active(10.0 * 3_600.0)) == 1
    assert DEDUP_WINDOW_S == pytest.approx(24.0 * 3_600.0)
    # outside the window: a fresh card
    c = bus.post(a.t_last + DEDUP_WINDOW_S + 1.0, 3, "base:m",
                 "boiloff margin", kind="boiloff")
    assert c is not a
    # a re-raise re-arms the warp cap
    bus.acknowledge(c.aid)
    assert c.released()
    bus.post(c.t_last + 60.0, 3, "base:m", "boiloff margin",
             kind="boiloff")
    assert not c.released()


def test_toast_budget_and_overflow():
    """A-3: max 3 toasts, newest on top; overflow counts silently."""
    bus = AlertBus()
    for i in range(5):
        bus.post(float(i), 4, f"src{i}", f"advisory {i}", kind=f"k{i}")
    toasts = bus.toasts(10.0)
    assert TOAST_BUDGET == 3 and len(toasts) == 3
    assert [a.text for a in toasts] == ["advisory 4", "advisory 3",
                                        "advisory 2"]
    assert bus.overflow(10.0) == 2


def test_master_alarm_audio_only():
    """A-6: hushes Class 2–3 audio at once; warp caps remain."""
    bus = AlertBus()
    t = 0.0
    bus.post(t, 2, "a", "warn", kind="w")
    bus.post(t, 3, "b", "caution", kind="c")
    e = bus.post(t, 1, "c", "emergency", kind="e")
    assert bus.master_alarm(t) == 2              # 2–3 only, not Class 1
    assert all(a.audio_acked for a in bus.active(t) if a.cls in (2, 3))
    assert not e.audio_acked
    assert bus.highest_warp_cap(t) == pytest.approx(0.0)   # caps stay
    bus2 = AlertBus()
    bus2.post(t, 2, "a", "warn", kind="w")
    bus2.master_alarm(t)
    assert bus2.highest_warp_cap(t) == pytest.approx(1.0)  # still capped


def test_storm_rule_cascade():
    """§8.3: >10 Class-2/3 alerts within 60 s collapse into one
    'CASCADE at <site>' Class-2 card, root cause first."""
    bus = AlertBus()
    assert STORM_THRESHOLD == 10 and STORM_WINDOW_S == pytest.approx(60.0)
    first = None
    for i in range(11):
        a = bus.post(100.0 + i * 2.0, 3 if i % 2 else 2, f"mod{i}",
                     f"fault {i}", kind=f"fault{i}", site="base:peary")
        first = first or a
    live = bus.active(130.0)
    assert len(live) == 1
    cascade = live[0]
    assert cascade.kind == "CASCADE" and cascade.cls == 2
    assert cascade.text == "CASCADE at base:peary"
    assert len(cascade.children) == 11
    assert cascade.children[0] == first.aid      # root cause first
    assert bus.highest_warp_cap(130.0) == pytest.approx(1.0)
    # 10 within the window does NOT collapse
    bus2 = AlertBus()
    for i in range(10):
        bus2.post(float(i), 2, f"m{i}", f"f {i}", kind=f"f{i}",
                  site="base:x")
    assert all(a.kind != "CASCADE" for a in bus2.active(20.0))


def test_override_remap_one_class():
    """A-4: per-type remap one class up/down, never out of Class 1;
    per-type pause override."""
    bus = AlertBus()
    bus.set_override("foundry_freeze", delta=+1)         # demote 2 → 3
    a = bus.post(0.0, 2, "base:m", "foundry freeze risk",
                 kind="foundry_freeze")
    assert a.cls == 3
    bus.set_override("conjunction", delta=-1)            # promote 3 → 2
    b = bus.post(0.0, 3, "ship:p", "conjunction < 1 h",
                 kind="conjunction")
    assert b.cls == 2
    bus.set_override("fire", delta=+1)                   # never out of 1
    c = bus.post(0.0, 1, "base:m", "fire", kind="fire")
    assert c.cls == 1 and c.pause
    bus.set_override("depress", pause=False)             # pause override
    d = bus.post(0.0, 1, "base:m", "slow leak", kind="depress")
    assert d.cls == 1 and not d.pause


# ---- E-9 / G-9 sweeps over the EXISTING contract shape ------------------------

def test_deadline_alerts_pinned():
    """E-9: alerts at T−90 (Advisory) / T−30 (Caution) / T−7 d
    (Warning), once each, against the Program contract dict shape."""
    assert DEADLINE_ALERT_DAYS == ((90.0, 4), (30.0, 3), (7.0, 2))
    bus = AlertBus()
    deadline = 200.0 * DAY
    c = {"contract_id": "ct02_smallsat", "description": "Smallsat to LEO",
         "payout": 8.0e6, "deadline_s": deadline}
    assert deadline_sweep(bus, [c], deadline - 95.0 * DAY) == []
    p = deadline_sweep(bus, [c], deadline - 89.0 * DAY)
    assert len(p) == 1 and p[0].cls == 4
    assert deadline_sweep(bus, [c], deadline - 88.0 * DAY) == []  # once
    p = deadline_sweep(bus, [c], deadline - 29.0 * DAY)
    assert len(p) == 1 and p[0].cls == 3
    p = deadline_sweep(bus, [c], deadline - 6.0 * DAY)
    assert len(p) == 1 and p[0].cls == 2
    assert p[0].expires_s == pytest.approx(deadline)
    # completed/failed contracts never alert; Contract objects accepted
    done = Contract("c_orbit", "Orbit", 1e8, deadline, completed_t=1.0)
    assert deadline_sweep(bus, [done], deadline - 6.0 * DAY) == []
    live = Contract("c_moon", "Moon SOI", 8e7, deadline)
    p = deadline_sweep(bus, [live], deadline - 6.0 * DAY)
    assert {a.cls for a in p} == {4, 3, 2}       # warped past all three


def test_runway_alerts_pinned():
    """G-9 death spiral: < 60 d → Class 3; < 14 d → Class 2."""
    assert RUNWAY_ALERT_DAYS == ((60.0, 3), (14.0, 2))
    bus = AlertBus()
    assert runway_sweep(bus, 0.0, 75.0) == []
    p = runway_sweep(bus, 0.0, 59.0)
    assert [a.cls for a in p] == [3]
    p = runway_sweep(bus, 1.0 + DEDUP_WINDOW_S, 13.0)
    assert sorted(a.cls for a in p) == [2, 3]


def test_alertbus_save_roundtrip():
    bus = AlertBus()
    a = bus.post(5.0, 2, "x", "warn", kind="w", expires_s=99.0)
    bus.post(6.0, 1, "y", "fire", kind="fire")
    bus.acknowledge(a.aid)
    bus.set_override("w", delta=+1)
    blob = json.dumps(bus.to_dict())             # JSON-safe (13 §1.1)
    bus2 = AlertBus.from_dict(json.loads(blob))
    assert bus2.highest_warp_cap(7.0) == pytest.approx(0.0)
    assert bus2.get(a.aid).acked
    assert bus2.overrides["w"]["delta"] == 1
    a3 = bus2.post(8.0, 3, "z", "c", kind="c")
    assert a3.aid not in {a.aid for a in bus.alerts}   # seq continues


# ---- THE CHRONICLE (12 §4) -----------------------------------------------------

def test_entry_kinds_and_schema():
    """§4.2 complete list (FIRST_* counts as one) + C19 BIRTH; C-1
    record fields; §8.12 caps pinned."""
    for k in ("FIRST_*", "LAUNCH", "LANDING", "DOCKING", "SOI_ARRIVAL",
              "CONTRACT_WON", "CONTRACT_DONE", "CONTRACT_FAILED",
              "ROUND_RAISED", "DEATH", "RESCUE", "DISASTER",
              "RISK_ACCEPTED", "STANDDOWN", "ANOMALY", "WONDER",
              "HERITAGE_VIOLATION", "BANKRUPTCY_NEAR", "AUDIT_PASS",
              "AUDIT_FAIL", "ACT_CHAPTER", "SETTINGS_CHANGED", "PHOTO",
              "RIVAL_NEWS", "EPILOGUE", "BIRTH"):
        assert k in ENTRY_KINDS
    assert len(ENTRY_KINDS) == 26
    assert CHRONICLE_TARGET_VOLUME == (200, 800)
    assert ENTRY_CAP == 2_000
    assert SNAPSHOT_CAP_BYTES == 64 * 1024
    ch = Chronicle()
    e = ch.add(100.0, "LANDING", "Set down.", subjects=("PELICAN-3",),
               location="site:peary", numbers={"margin_pct": 4.1},
               autoshot_id="shot:1", seed=7, cls=4)
    assert (e.t, e.kind, e.cls) == (100.0, "LANDING", 4)
    assert e.refs == e.subjects == ("PELICAN-3",)
    assert e.numbers["margin_pct"] == pytest.approx(4.1)
    ch.add(101.0, "FIRST_CREWED_LUNAR_LANDING", "First.")   # prefix OK
    with pytest.raises(ValueError):
        ch.add(102.0, "NOT_A_KIND", "nope")
    # append-only: seq strictly increases
    assert [x.seq for x in ch.entries] == sorted(x.seq for x in ch.entries)


def test_chronicle_queries():
    ch = Chronicle()
    ch.add(0.0, "LAUNCH", "L1")
    ch.add(50.0, "LAUNCH", "L2")
    ch.add(100.0, "DEATH", "D1")
    assert [e.text for e in ch.by_kind("LAUNCH")] == ["L1", "L2"]
    assert [e.text for e in ch.in_range(40.0, 100.0)] == ["L2", "D1"]
    assert [e.text for e in ch.query(kind="LAUNCH", t0=40.0)] == ["L2"]
    assert len(ch.query()) == 3


def test_chapter_cards_auto_stats():
    """C-3: act/audit chapters carry auto-computed stats."""
    ch = Chronicle()
    for i in range(3):
        ch.add(float(i), "LAUNCH", f"L{i}", numbers={"tonnage_t": 20.0})
    ch.add(5.0, "DEATH", "Lost Okafor.")
    ch.add(6.0, "FIRST_ORBIT", "First orbit.", numbers={"usd": 30.0e6})
    stats = chapter_stats(ch.entries)
    assert stats["launches"] == 3
    assert stats["fatalities"] == 1
    assert stats["firsts"] == 1
    assert stats["tonnage_to_orbit_t"] == pytest.approx(60.0)
    assert stats["usd_flow"] == pytest.approx(30.0e6)
    card = ch.chapter(10.0, "ACT II — THE MOON")
    assert card.kind == "ACT_CHAPTER" and card.numbers == stats
    with pytest.raises(ValueError):
        ch.chapter(11.0, "x", kind="LAUNCH")


def test_contract_entries_wrap_program_shape():
    ch = Chronicle()
    c = {"contract_id": "ct04_geo", "description": "GEO comsat",
         "payout": 50.0e6, "deadline_s": 1e8}
    chronicle_contract(ch, 1.0, c, "won")
    e = chronicle_contract(ch, 2.0, c, "done")
    chronicle_contract(ch, 3.0, Contract("c_x", "X", 1e6, 1e8), "failed")
    assert [x.kind for x in ch.entries] == [
        "CONTRACT_WON", "CONTRACT_DONE", "CONTRACT_FAILED"]
    assert e.numbers["payout_usd"] == pytest.approx(50.0e6)
    assert e.numbers["usd"] == pytest.approx(50.0e6)   # paid on DONE only
    assert ch.entries[0].numbers["usd"] == pytest.approx(0.0)


def test_export_text_mission_log():
    """C-2 tone + epoch math: 2049-01-01 + 1686 d = 2053-08-14."""
    t_landing = 1_686.0 * DAY
    assert sim_date(t_landing) == "2053-08-14"
    assert sim_date(0.0) == "2049-01-01"
    ch = Chronicle()
    ch.add(0.0, "LAUNCH", "First flight of the program.")
    ch.add(t_landing, "LANDING",
           "PELICAN-3 set down at Shackleton Rim. First crewed lunar "
           "landing of the program. Crew: Vasquez, Okafor. Margin at "
           "touchdown: 4.1% propellant.")
    ch.chapter(t_landing + DAY, "ACT III BEGINS",
               stats={"launches": 1, "fatalities": 0})
    doc = export_text(ch.entries)
    lines = doc.splitlines()
    assert lines[0] == "The Program, 2049–2053"       # C-4 trophy title
    assert lines[1] == "=" * len(lines[0])
    assert "2049-01-01 — First flight of the program." in lines
    assert ("2053-08-14 — PELICAN-3 set down at Shackleton Rim. First "
            "crewed lunar landing of the program. Crew: Vasquez, Okafor."
            " Margin at touchdown: 4.1% propellant.") in lines
    assert "==== 2053-08-15 — ACT III BEGINS ====" in lines
    assert "  launches: 1" in lines
    assert export_text([]).startswith("The Program, 2049–20XX")


def test_memory_cap_degrades_text_only():
    """§8.12: past 2,000 entries the oldest non-FIRST/DEATH degrade to
    text-only; FIRST/DEATH keep snapshots; nothing is deleted."""
    ch = Chronicle()
    ch.add(0.0, "FIRST_LAUNCH", "first", autoshot_id="s0")
    ch.add(1.0, "DEATH", "epitaph", autoshot_id="s1")
    for i in range(ENTRY_CAP + 8):
        ch.add(2.0 + i, "LAUNCH", f"L{i}", autoshot_id=f"s{i + 2}")
    assert len(ch.entries) == ENTRY_CAP + 10          # append-only
    assert not ch.entries[0].degraded                 # FIRST_ kept
    assert ch.entries[0].autoshot_id == "s0"
    assert not ch.entries[1].degraded                 # DEATH kept
    degraded = [e for e in ch.entries if e.degraded]
    assert len(degraded) == 10
    assert all(e.autoshot_id is None for e in degraded)
    assert degraded[0] is ch.entries[2]               # oldest first
    assert degraded[0].text == "L0"                   # prose survives


def test_chronicle_save_roundtrip():
    ch = Chronicle()
    ch.add(5.0, "RESCUE", "Got them home.", subjects=("KESTREL",),
           numbers={"prestige": 50})
    blob = json.dumps(ch.to_dict())
    ch2 = Chronicle.from_dict(json.loads(blob))
    assert ch2.entries[0].subjects == ("KESTREL",)
    assert ch2.entries[0].numbers["prestige"] == 50
    e = ch2.add(6.0, "LAUNCH", "next")
    assert e.seq == 2                                 # seq continues


# ---- BIRTHS (DECISIONS C19, 08 §4.9) ---------------------------------------------

def test_birth_eligibility_gates():
    """Policy ON, g_repro discovered & met, ≥2 adults, occupation ≥
    one gestation (270 d) — in that order."""
    assert GESTATION_D == pytest.approx(270.0)
    assert MIN_PARENT_CREW == 2
    ok = dict(policy_on=True, g_local_g=0.9, g_repro_g=0.38,
              adults=4, occupied_d=400.0)
    assert births_eligible(**ok) == (True, "eligible")
    assert births_eligible(**{**ok, "policy_on": False}) == \
        (False, "policy_off")
    assert births_eligible(**{**ok, "g_repro_g": None}) == \
        (False, "g_repro_undiscovered")
    assert births_eligible(**{**ok, "g_local_g": 0.30}) == \
        (False, "gravity_below_threshold")
    assert births_eligible(**{**ok, "adults": 1}) == \
        (False, "needs_two_adults")
    assert births_eligible(**{**ok, "occupied_d": 269.0}) == \
        (False, "occupation_below_gestation")


def test_g_repro_deterministic_brackets():
    """08 §4.9: threshold drawn per save within defensible bounds;
    LS-10 narrows the bracket; LS-11 reveals it exactly."""
    lo, hi = G_REPRO_BOUNDS
    assert (lo, hi) == (0.30, 0.90)
    g = draw_g_repro("campaign:42")
    assert g == draw_g_repro("campaign:42")           # deterministic
    assert lo <= g <= hi
    assert draw_g_repro("campaign:43") != g           # seed matters
    b0 = g_repro_bracket("campaign:42", 0)
    b2 = g_repro_bracket("campaign:42", 2)
    b3 = g_repro_bracket("campaign:42", 3)
    assert b0 == G_REPRO_BOUNDS
    assert b0[0] <= b2[0] <= g <= b2[1] <= b0[1]
    assert b2[1] - b2[0] <= 0.1 + 1e-9                # LS-10 narrowed
    assert b3 == (g, g)                               # LS-11 exact


def test_birth_naming_and_crew_save_shape():
    """The newborn record matches the save crew section EXACTLY and
    reconstructs through the restore_campaign code path."""
    parents = ["Vasquez", "Okafor"]
    b = make_birth("site:titan_shore", 100.0 * YEAR, parents, 0)
    b2 = make_birth("site:titan_shore", 100.0 * YEAR, parents, 0)
    assert b["name"] == b2["name"]                    # deterministic
    assert b["name"].split()[-1] in {"Vasquez", "Okafor"}
    assert b["generation"] == 1                       # first spaceborn
    nxt = make_birth("site:titan_shore", 101.0 * YEAR, parents, 1,
                     parent_generations=(1, 0))
    assert nxt["generation"] == 2
    # collision handling
    clash = make_birth("site:titan_shore", 102.0 * YEAR, parents, 0,
                       existing_names=(b["name"],))
    assert clash["name"] == b["name"] + " II"
    # the save shape, key for key (aphelion/save/campaign.py crew dict)
    cd = b["crew"]
    assert set(cd) == {"msv", "role", "skill", "acute", "busy", "skills",
                       "morale", "cond", "energy", "traits", "conditions",
                       "xp"}
    assert cd["msv"] == 0.0 and cd["skill"] == 0
    assert cd["role"] in ROLES
    assert cd["skills"] == {r: 0 for r in ROLES}      # non-working child
    assert cd["busy"] == pytest.approx(100.0 * YEAR + ADULT_AGE_YR * YEAR)
    assert cd["energy"] == pytest.approx(CHILD_ENERGY_KCAL)
    assert CHILD_ENERGY_KCAL == pytest.approx(45_000.0)   # 0.5 × baseline
    json.dumps(cd)                                    # serializes clean
    # exactly how restore_campaign rebuilds a CrewMember:
    m = CrewMember(b["name"], cd["role"], cd["skill"],
                   CrewDose(cd["msv"], cd.get("acute", [])),
                   busy_until=cd.get("busy", 0.0),
                   skills=dict(cd["skills"]) if cd.get("skills") else None,
                   morale=cd.get("morale", 70.0),
                   cond=cd.get("cond", 100.0),
                   energy_kcal=cd.get("energy", 90_000.0),
                   traits=(tuple(cd["traits"])
                           if cd.get("traits") is not None else None),
                   conditions=[dict(c) for c in cd.get("conditions", [])],
                   xp=dict(cd.get("xp", {})))
    assert not m.available(100.0 * YEAR + 1.0)        # child: non-working
    assert m.available(100.0 * YEAR + ADULT_AGE_YR * YEAR)
    assert m.skills == {r: 0 for r in ROLES}


def test_birth_chronicle_and_audit_inputs():
    """BIRTH entries feed the E-28(g) demographic pillar."""
    ch = Chronicle()
    parents = ["Vasquez", "Okafor"]
    b1 = make_birth("site:peary", 50.0 * YEAR, parents, 0)
    e = record_birth(ch, b1)
    assert e.kind == "BIRTH" and e.location == "site:peary"
    assert b1["name"] in e.subjects and "Vasquez" in e.subjects
    assert e.numbers["generation"] == 1
    assert b1["name"] in e.text and "Generation 1" in e.text
    b2 = make_birth("site:peary", 70.0 * YEAR, [b1["name"], "Okafor"], 1,
                    parent_generations=(1, 0))
    record_birth(ch, b2)
    assert birth_count(ch) == 2
    assert generations_reached(ch) == 2
