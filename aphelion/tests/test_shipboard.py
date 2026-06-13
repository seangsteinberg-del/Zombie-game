"""Shipboard life (08 §4.3/§4.4/§4.5, 12 §3.5): stations registry,
continuous needs, the auto-scheduler, player verbs with real effects,
kcal conservation, deterministic events, save round-trip."""

import json

import pytest

from aphelion.game.crew import CrewMember
from aphelion.game.shipboard import (
    DAY_S, HOUR_S, ROOM_M, Shipboard, exercise_need_h)
from aphelion.sim.habitat.food import BODY_RESERVE_KCAL, KCAL_PER_KG_DRY

MODULES = (("flight_deck", "FD-1"), ("hab_module", "HAB-1"),
           ("machine_shop", "SHOP-1"), ("science_lab", "LAB-1"),
           ("med_bay", "MED-1"))


def crew4() -> dict:
    out = {}
    for name, role, lvl in (("A. Sharma", "pilot", 3),
                            ("T. Eze", "engineer", 2),
                            ("K. Sato", "scientist", 2),
                            ("Dr. I. Whitfield", "medic", 3)):
        out[name] = CrewMember(name, role, lvl)
    return out


def ship(spin_g=0.0, crew=None, modules=MODULES, **kw) -> Shipboard:
    return Shipboard(modules, crew if crew is not None else crew4(),
                     spin_g=spin_g, t0=0.0, **kw)


# ---- stations registry ------------------------------------------------------

def test_station_registry_positions_and_capacity():
    sb = ship()
    types = {st["type"] for st in sb.stations}
    assert {"bunk", "galley", "hygiene", "exercise", "maint_panel",
            "science_bench", "med_bay", "comms_desk",
            "cupola"} <= types
    for st in sb.stations:
        assert 0.0 <= st["x_m"] <= ROOM_M       # module-local metres
        i = st["module_index"]
        # strip mapping: airlock is room 0, module i is room i+1
        assert st["strip_x_m"] == pytest.approx(
            (i + 1) * ROOM_M + st["x_m"])
        assert st["capacity"] >= 1
    panel = next(s for s in sb.stations if s["id"] == "maint_panel.0")
    assert panel["module_id"] == "SHOP-1"
    assert "repair" in panel["verbs"]


def test_nearest_station_for_highlight():
    sb = ship()
    galley = next(s for s in sb.stations if s["type"] == "galley")
    hit = sb.nearest_station(galley["strip_x_m"] + 0.6)
    assert hit is not None and hit["id"] == galley["id"]
    assert sb.nearest_station(0.2) is None      # airlock: nothing near


# ---- scheduler --------------------------------------------------------------

def test_schedule_tiles_a_full_day():
    sb = ship()
    for name in sb.crew:
        plan = sb.plan(name)
        assert sum(b["dur"] for b in plan) == pytest.approx(24.0)
        acts = {b["act"]: sum(x["dur"] for x in plan
                              if x["act"] == b["act"]) for b in plan}
        assert acts["sleep"] == pytest.approx(8.0)
        assert acts["exercise"] == pytest.approx(2.5)   # 0 g prescription
        assert acts["meal"] == pytest.approx(1.5)       # three meals
        assert acts["work"] == pytest.approx(10.0)
    # work block sits at the role's station
    eng_plan = sb.plan("T. Eze")
    work = next(b for b in eng_plan if b["act"] == "work")
    assert work["station"].startswith("maint_panel")


def test_schedule_obeys_gravity_prescription():
    assert exercise_need_h(0.0) == 2.5
    assert exercise_need_h(2.0) == 1.0
    assert exercise_need_h(9.81) == 0.0
    sb = ship(spin_g=9.81)
    plan = sb.plan("A. Sharma")
    assert sum(b["dur"] for b in plan
               if b["act"] == "exercise") == pytest.approx(0.0)
    assert sum(b["dur"] for b in plan) == pytest.approx(24.0)


def test_player_override_replaces_plan():
    sb = ship()
    blocks = [{"h0": 0.0, "dur": 16.0, "act": "work",
               "station": "science_bench.0"},
              {"h0": 16.0, "dur": 8.0, "act": "sleep",
               "station": "bunk.0"}]
    assert sb.override("K. Sato", blocks)
    assert sb.plan("K. Sato")[0]["act"] == "work"
    assert not sb.override("K. Sato", blocks[:1])   # must tile 24 h
    sb.clear_override("K. Sato")
    assert sum(b["dur"] for b in sb.plan("K. Sato")
               if b["act"] == "work") == pytest.approx(10.0)


# ---- needs integration ------------------------------------------------------

def test_sleep_debt_accrues_awake_and_clears_asleep():
    sb = ship()
    name = sorted(sb.crew)[0]
    sb.override(name, [{"h0": 0.0, "dur": 16.0, "act": "work",
                        "station": None},
                       {"h0": 16.0, "dur": 8.0, "act": "sleep",
                        "station": "bunk.0"}])
    sb.step(0.0, 16.0 * HOUR_S)
    assert sb.need(name)["sleep_debt_h"] == pytest.approx(8.0, abs=0.3)
    sb.step(16.0 * HOUR_S, 8.0 * HOUR_S)
    assert sb.need(name)["sleep_debt_h"] < 1.0


def test_exercise_debt_faster_at_zero_g_than_spin():
    free = ship(spin_g=0.0)
    spun = ship(spin_g=2.0)
    for sb in (free, spun):
        for n in sb.crew:                      # nobody exercises
            sb.override(n, [{"h0": 0.0, "dur": 24.0, "act": "free",
                             "station": None}])
        sb.step(0.0, 2.0 * DAY_S)
    n = sorted(free.crew)[0]
    assert free.need(n)["ex_debt_h"] == pytest.approx(5.0, abs=0.3)
    assert spun.need(n)["ex_debt_h"] == pytest.approx(2.0, abs=0.3)
    assert free.need(n)["ex_debt_h"] > 2.0 * spun.need(n)["ex_debt_h"]
    # and the deconditioning caution fired only in free fall
    assert free.need(n)["flags"].get("decon")


def test_conditioning_decays_without_rack_in_free_fall():
    nogym = ship(modules=(("hab_module", "HAB-1"),))   # no exercise rack
    c0 = {n: m.cond for n, m in nogym.crew.items()}
    nogym.step(0.0, 10.0 * DAY_S)
    assert all(nogym.crew[n].cond < c0[n] - 2.0 for n in nogym.crew)


def test_kcal_conservation_galley_stores_to_crew():
    sb = ship()
    food0 = sb.stores["food_kg"]
    e0 = sum(m.energy_kcal for m in sb.crew.values())
    sb.step(0.0, 3.0 * DAY_S)
    e1 = sum(m.energy_kcal for m in sb.crew.values())
    drawn = (food0 - sb.stores["food_kg"]) * KCAL_PER_KG_DRY
    assert drawn == pytest.approx(sb.kcal_served, rel=1e-9)
    assert e1 - e0 == pytest.approx(sb.kcal_served - sb.kcal_burned,
                                    rel=1e-9)
    assert sb.kcal_served > 0.0 and sb.kcal_burned > 0.0


def test_empty_galley_posts_alert_and_crew_starve():
    sb = ship(stores={"food_kg": 0.0, "medsupplies_kg": 0.0,
                      "samples": 0.0})
    events = sb.step(0.0, 8.0 * DAY_S)
    kinds = {e["kind"] for e in events}
    assert "no_food" in kinds
    # ~2,450 kcal/day burn against the 90,000 kcal body reserve
    assert all(m.energy_kcal < BODY_RESERVE_KCAL * 0.85
               for m in sb.crew.values())


# ---- crew AI / occupancy ----------------------------------------------------

def test_capacity_claim_and_whereabouts():
    crew = crew4()
    crew["S. Novak"] = CrewMember("S. Novak", "pilot", 1)
    crew["J. Mbeki"] = CrewMember("J. Mbeki", "engineer", 3)
    sb = ship(crew=crew)
    sb.step(0.0, 600.0)
    for st in sb.stations:                      # never over capacity
        assert len(st["occupants"]) <= st["capacity"]
    w = sb.whereabouts(sorted(crew)[0])
    assert w["pose"] in ("sleep_bag", "exercise", "seated", "stand")
    assert w["eta_s"] == pytest.approx(
        abs(w["target_x_m"] - w["x_m"]) / 0.9)
    # crew x positions actually converge on their targets
    sb.step(600.0, 2.0 * HOUR_S)
    ws = [sb.whereabouts(n) for n in crew]
    assert any(not w["moving"] for w in ws)


# ---- verbs ------------------------------------------------------------------

def test_cook_feeds_diners_boosts_morale_and_cools_down():
    sb = ship()
    sb.step(0.0, 600.0)
    galley = next(s for s in sb.stations if s["type"] == "galley")
    m0 = {n: m.morale for n, m in sb.crew.items()}
    food0 = sb.stores["food_kg"]
    noon = 12.0 * HOUR_S                        # everyone is awake
    midnight = sb.verb("cook", galley["id"], 100.0)
    assert not midnight["ok"]                   # all asleep at 00:00
    out = sb.verb("cook", galley["id"], noon)
    assert out["ok"]
    assert out["effects"][0] == "meal"
    assert sb.stores["food_kg"] < food0
    assert all(sb.crew[n].morale > m0[n] for n in sb.crew)
    again = sb.verb("cook", galley["id"], noon + 600.0)
    assert not again["ok"] and again["reason"] == "cooldown"
    later = sb.verb("cook", galley["id"], noon + 6.5 * HOUR_S)
    assert later["ok"]


def test_repair_returns_wire_friendly_effect():
    sb = ship()
    out = sb.verb("repair", "maint_panel.0", 50.0)
    assert out["ok"]
    kind, module_id, amount = out["effects"]
    assert kind == "repair" and module_id == "SHOP-1"
    assert 5.0 <= amount <= 20.0
    # better engineers fix more
    aces = {"J. Mbeki": CrewMember("J. Mbeki", "engineer", 3)}
    rooks = {"F. Gutierrez": CrewMember("F. Gutierrez", "engineer", 0)}
    hi = ship(crew=aces).verb("repair", "maint_panel.0", 0.0)
    lo = ship(crew=rooks).verb("repair", "maint_panel.0", 0.0)
    assert hi["effects"][2] > lo["effects"][2]


def test_research_consumes_sample_with_skill_multiplier():
    sb = ship(stores={"food_kg": 50.0, "medsupplies_kg": 5.0,
                      "samples": 2.0})
    out = sb.verb("research", "science_bench.0", 10.0)
    assert out["ok"] and out["effects"][0] == "science"
    assert sb.stores["samples"] == pytest.approx(1.0)
    dry = ship(stores={"food_kg": 50.0, "medsupplies_kg": 5.0,
                       "samples": 0.0})
    assert not dry.verb("research", "science_bench.0", 10.0)["ok"]
    rook = {"W. Achebe": CrewMember("W. Achebe", "scientist", 0)}
    lo = ship(crew=rook, stores={"food_kg": 9.0, "medsupplies_kg": 0.0,
                                 "samples": 1.0})
    assert out["effects"][1] > lo.verb(
        "research", "science_bench.0", 10.0)["effects"][1]


def test_cupola_diminishing_returns_and_flyby_bonus():
    sb = ship()
    name = "A. Sharma"
    sb.crew[name].morale = 50.0
    g1 = sb.verb("gaze", "cupola.0", 0.0, actor=name)["effects"][1]
    g2 = sb.verb("gaze", "cupola.0", 3.0 * HOUR_S,
                 actor=name)["effects"][1]
    g3 = sb.verb("gaze", "cupola.0", 6.0 * HOUR_S,
                 actor=name)["effects"][1]
    assert g1 > g2 > g3                          # diminishing returns
    fly = ship()
    fb = fly.verb("gaze", "cupola.0", 0.0, context={"flyby": True},
                  actor="A. Sharma")
    assert fb["effects"][1] > g1                 # flyby is the big one
    assert fb["events"][0]["chronicle"]


def test_med_scan_reveals_and_treats_with_supplies():
    sb = ship()
    sick = sb.crew["K. Sato"]
    sick.conditions.append({"kind": "dcs", "age": 1.0,
                            "treated": False})
    out = sb.verb("scan", "med_bay.0", 100.0)
    assert out["ok"]
    _, findings, treated = out["effects"]
    assert ("K. Sato", "dcs", False) in findings
    assert ("K. Sato", "dcs") in treated         # medic 3 + supplies
    assert sick.conditions[0]["treated"]
    assert sb.stores["medsupplies_kg"] < 6.0
    # without supplies the scan only diagnoses
    bare = ship(stores={"food_kg": 50.0, "medsupplies_kg": 0.0,
                        "samples": 0.0})
    bare.crew["K. Sato"].conditions.append(
        {"kind": "dcs", "age": 1.0, "treated": False})
    out2 = bare.verb("scan", "med_bay.0", 100.0)
    assert out2["effects"][2] == []
    assert not bare.crew["K. Sato"].conditions[0]["treated"]


def test_verbs_gate_on_capacity():
    crew = {f"C{i}": CrewMember(f"C{i}", "pilot", 1) for i in range(4)}
    sb = ship(crew=crew)
    for n in crew:                              # park everyone in cupola
        sb.override(n, [{"h0": 0.0, "dur": 24.0, "act": "free",
                         "station": None}])
        sb.needs[n] = sb.need(n)
        sb.needs[n]["social"] = 1.0
    sb.step(0.0, 600.0)
    cupola = next(s for s in sb.stations if s["type"] == "cupola")
    assert len(cupola["occupants"]) == cupola["capacity"]
    out = sb.verb("gaze", cupola["id"], 700.0, actor="C3")
    if "C3" not in cupola["occupants"]:
        assert not out["ok"]                    # full: outsiders blocked
    ok = sb.verb("gaze", cupola["id"], 700.0,
                 actor=cupola["occupants"][0])
    assert ok["ok"]                             # occupants may use it


# ---- emergent events --------------------------------------------------------

def test_events_deterministic_across_runs():
    a, b = ship(), ship()
    ev_a, ev_b = [], []
    for day in range(6):
        ev_a += a.step(day * DAY_S, DAY_S)
        ev_b += b.step(day * DAY_S, DAY_S)
    assert [e["text"] for e in ev_a] == [e["text"] for e in ev_b]
    assert json.dumps(a.to_dict(), sort_keys=True) == \
        json.dumps(b.to_dict(), sort_keys=True)


def test_birthday_fires_and_party_pays_out():
    sb = ship()
    found = None
    for day in range(1, 400):
        evs = sb.step((day - 1) * DAY_S + 0.0, DAY_S)
        bd = [e for e in evs if e["kind"] == "birthday"]
        if bd:
            found = (day, bd[0]["who"][0])
            break
    assert found is not None, "a birthday must occur within a year"
    day, name = found
    assert sb.birthdays_today == [name]
    galley = next(s for s in sb.stations if s["type"] == "galley")
    sb.crew[name].morale = 40.0
    out = sb.verb("cook", galley["id"],
                  day * DAY_S + 12.0 * HOUR_S)   # midday, same day
    kinds = [e["kind"] for e in out["events"]]
    assert "birthday_party" in kinds
    assert name in sb.celebrated
    assert sb.crew[name].morale >= 40.0 + 10.0   # +5 meal +10 party


def test_arguments_dip_morale_and_a_meal_fixes_them():
    sb = ship()
    for day in range(60):
        sb.step(day * DAY_S, DAY_S)
        if sb.arguments:
            break
    assert sb.arguments, "an argument should occur within 60 days"
    pair = sb.arguments[0]
    galley = next(s for s in sb.stations if s["type"] == "galley")
    t = sb.t + 12.0 * HOUR_S                    # midday: both awake
    out = sb.verb("cook", galley["id"], t)
    assert out["ok"]
    assert any(e["kind"] == "made_up" for e in out["events"])
    assert not any(a["a"] == pair["a"] and a["b"] == pair["b"]
                   for a in sb.arguments)


# ---- persistence ------------------------------------------------------------

def test_save_round_trip_behaves_identically():
    a = ship()
    a.step(0.0, 2.0 * DAY_S)
    blob = json.loads(json.dumps(a.to_dict()))   # via real JSON
    crew_b = crew4()
    for n in crew_b:                             # mirror crew state
        crew_b[n].morale = a.crew[n].morale
        crew_b[n].cond = a.crew[n].cond
        crew_b[n].energy_kcal = a.crew[n].energy_kcal
    b = Shipboard.from_dict(blob, crew_b)
    ev_a = a.step(2.0 * DAY_S, DAY_S)
    ev_b = b.step(2.0 * DAY_S, DAY_S)
    assert [e["text"] for e in ev_a] == [e["text"] for e in ev_b]
    assert a.need("T. Eze") == b.need("T. Eze")
    assert a.stores == pytest.approx(b.stores)
    assert json.dumps(a.to_dict(), sort_keys=True) == \
        json.dumps(b.to_dict(), sort_keys=True)


def test_attention_markers_follow_context():
    sb = ship()
    sb.step(0.0, 600.0, context={"module_cond": {"SHOP-1": 50.0}})
    panel = next(s for s in sb.stations if s["id"] == "maint_panel.0")
    assert panel["attention"]
    sb.crew["T. Eze"].conditions.append(
        {"kind": "minor_illness", "age": 0.0, "treated": False})
    sb.step(600.0, 600.0, context={"module_cond": {"SHOP-1": 95.0}})
    med = next(s for s in sb.stations if s["type"] == "med_bay")
    panel = next(s for s in sb.stations if s["id"] == "maint_panel.0")
    assert med["attention"] and not panel["attention"]
