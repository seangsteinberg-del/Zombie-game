"""Propellant flow & crossfeed (06 §2.7): proportional drain, the
Build-D four-tank split, asparagus ordering, flameout, W9 caps."""

import pytest

from aphelion.sim.vessels.plumbing import (
    TankState, drain, flameout, w9_flow_capped)

HYDROLOX = {"Oxygen": 6.0 / 7.0, "Hydrogen": 1.0 / 7.0}


def test_build_d_four_tank_drain():
    """06 §4.4: the hydrolox engine draws 6 kg O2 per 1 kg H2 across
    four SEPARATE tanks exactly as from one combined tank."""
    tanks = [TankState({"Oxygen": 8.0}), TankState({"Oxygen": 8.0}),
             TankState({"Oxygen": 8.0}), TankState({"Hydrogen": 4.0})]
    got = drain(tanks, HYDROLOX, 7.0)
    assert got == pytest.approx(7.0)
    for t in tanks[:3]:                      # 6 t O2, proportionally
        assert t.loads["Oxygen"] == pytest.approx(6.0, abs=1e-9)
    assert tanks[3].loads["Hydrogen"] == pytest.approx(3.0)


def test_asparagus_descending_stage_order():
    side = TankState({"Oxygen": 6.0, "Hydrogen": 1.0}, stage=2)
    core = TankState({"Oxygen": 6.0, "Hydrogen": 1.0}, stage=1)
    drain([side, core], HYDROLOX, 3.5, crossfeed=True)
    assert side.total_t() == pytest.approx(3.5)   # boosters drain first
    assert core.total_t() == pytest.approx(7.0)
    # a priority integer beats the stage number
    pri = TankState({"Oxygen": 6.0, "Hydrogen": 1.0}, stage=0, priority=9)
    drain([side, core, pri], HYDROLOX, 3.5, crossfeed=True)
    assert pri.total_t() == pytest.approx(3.5)
    assert core.total_t() == pytest.approx(7.0)


def test_flameout_is_deterministic_and_surplus_strands():
    tanks = [TankState({"Oxygen": 12.0, "Hydrogen": 0.5})]
    got = drain(tanks, HYDROLOX, 10.0)
    assert got == pytest.approx(3.5)         # 0.5 H2 caps the draw
    assert flameout(tanks, HYDROLOX)
    assert tanks[0].loads["Oxygen"] == pytest.approx(9.0)  # stranded
    assert drain(tanks, HYDROLOX, 1.0) == 0.0


def test_w9_duct_flow_caps():
    duct = {"flow_cryo_tpm": 1.0, "flow_storable_tpm": 5.0}
    # a Raptor-class 700 kg/s through one cryo duct (16.7 kg/s) -> W9
    assert w9_flow_capped(700.0, [duct], cryogenic=True)
    assert not w9_flow_capped(10.0, [duct], cryogenic=True)
    assert not w9_flow_capped(70.0, [duct] * 2, cryogenic=False)
    assert not w9_flow_capped(700.0, [], cryogenic=True)
