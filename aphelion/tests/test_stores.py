"""Ship's-stores rollup: provisioned crew-days, volume, greenhouse closure
and cargo summed straight from the part catalog."""

from aphelion.sim.habitat.stores import manifest

# canonical part shapes mirroring the live catalog
CAP_VELA = {"crew": {"capacity": 2, "endurance_days": 40.0}}
RIG_S = {"crew": {"capacity": 2, "endurance_days": 900.0},
         "hab": {"v_press_m3": 60.0, "sleeps": 2}}
GRN_S = {"hab": {"v_press_m3": 80.0, "sleeps": 0, "grow_m2": 50.0}}
LAB = {"hab": {"v_press_m3": 100.0, "lab": True}}
CG_BAY = {"cargo_t": 8.0, "cargo_cells": 12}


def test_crew_days_and_endurance():
    m = manifest([CAP_VELA], crew_n=2)
    assert m["crew_days"] == 80.0          # 2 seats × 40 d
    assert m["days"] == 40.0               # 80 crew-days / 2 crew
    assert m["seats"] == 2
    # the long-duration rig stretches endurance hugely
    m2 = manifest([RIG_S], crew_n=2)
    assert m2["days"] == 900.0
    assert m2["berths"] == 2


def test_daily_draw_is_canon():
    m = manifest([RIG_S], crew_n=2)
    assert m["daily_kg"]["O2"] == 0.84 * 2
    assert m["daily_kg"]["Water"] == 3.5 * 2


def test_greenhouse_closes_part_of_the_diet():
    # 50 m² for 2 crew vs 40 m²/crew full diet → ~0.625 capped diet share
    m = manifest([GRN_S, RIG_S], crew_n=2)
    assert 0.6 < m["food_closure"] <= 0.95
    # the closed share stops drawing stocked food → less daily food
    assert m["daily_kg"]["Food"] < 0.62 * 2
    assert m["food_days"] > m["days"]      # farm stretches the food line
    assert m["grow_m2"] == 50.0


def test_volume_berths_cargo_and_labs():
    m = manifest([RIG_S, GRN_S, LAB, CG_BAY], crew_n=4)
    assert m["volume_m3"] == 240.0
    assert m["vol_per_crew"] == 60.0
    assert m["labs"] == 1
    assert m["cargo_t"] == 8.0 and m["cargo_cells"] == 12


def test_empty_is_safe():
    m = manifest([], crew_n=0)
    assert m["crew_days"] == 0.0 and m["days"] == 0.0
    assert m["food_closure"] == 0.0
