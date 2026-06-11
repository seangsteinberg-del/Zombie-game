"""Builder math vs the 06 worked builds — machine-checked acceptance
numbers (§4.1 Build A, §4.2 Build B dv/TWR, §4.3 Build C)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from aphelion.content.loader import default_data_dir, load_packs
from aphelion.sim.vessels.buildermath import (
    G0, StageDef, burnable_prop_t, ep_thrust_fraction, isp_traj_avg,
    mdot_kgps, mixed_isp, solar_kwe, stage_report, thrust_kn_at)


@pytest.fixture(scope="module")
def parts():
    return load_packs(default_data_dir()).by_type("parts")


def test_build_a_anvil1(parts):
    """06 §4.1 — T0 two-stage launcher, every Expected number."""
    h1 = parts["core:engine_h102"]["engine"]      # RL10C-1
    k1 = parts["core:engine_k845"]["engine"]      # Merlin 1D
    stages = [
        # S1: 5× TK-KL-M dry 3.50 + 2× EN-K1 0.94 + structure/fins 1.50
        #     + fairing 0.90 + interstage+decoupler 0.52 (ride down)
        StageDef(engines=[k1, k1], inert_t=3.50 + 0.94 + 1.50 + 0.90
                 + 0.52, prop_t=70.0),
        # S2: tanks dry 1.40 + EN-H1 0.19 + avionics 0.30 + payload 2.0
        StageDef(engines=[h1], inert_t=1.40 + 0.19 + 0.30 + 2.00,
                 prop_t=14.0),
    ]
    vac = stage_report(stages, mode="vac")
    s1, s2 = vac
    assert s1["m0_t"] == pytest.approx(95.25, abs=0.01)   # liftoff mass
    assert s2["m0_t"] == pytest.approx(17.89, abs=0.01)
    # S2 vacuum: dv 6,729; TWR 0.58 at ignition; burn 607 s @ 23.08 kg/s
    assert s2["dv_ms"] == pytest.approx(6_729.0, abs=1.0)
    assert s2["twr_ignition"] == pytest.approx(0.58, abs=0.01)
    assert s2["mdot_kgps"] == pytest.approx(23.08, abs=0.02)
    assert s2["burn_s"] == pytest.approx(607.0, abs=1.0)
    # S1 burn 117 s — ṁ from the VACUUM pair (599.4 kg/s), the spec's
    # named trap (mixing SL thrust with vac Isp wrongly gives 126 s)
    assert s1["mdot_kgps"] == pytest.approx(599.4, abs=0.5)
    assert s1["burn_s"] == pytest.approx(117.0, abs=1.0)
    # S1 dv bounds: 3,672 SL / 4,049 vac; traj-avg lands between
    assert s1["dv_ms"] == pytest.approx(4_049.0, abs=1.0)
    sl = stage_report(stages, mode="sl")[0]
    assert sl["dv_ms"] == pytest.approx(3_672.0, abs=1.0)
    traj = stage_report(stages, mode="traj")[0]
    assert isp_traj_avg(k1) == pytest.approx(294.76, abs=0.01)
    # spec quotes 3,841 after rounding Isp to 295; exact law gives 3,838
    assert traj["dv_ms"] == pytest.approx(3_841.0, abs=5.0)
    # total ideal ≈ 10,570 ≥ 9,400 LEO target
    assert traj["dv_ms"] + s2["dv_ms"] == pytest.approx(10_570.0, abs=8.0)
    # liftoff TWR: ṁ-constant model (binding 06 §2.4) gives F_SL =
    # 2×829 kN → 1.78; the catalog's measured-Merlin 845 row would give
    # the spec's quoted 1.81 — the ṁ rule wins, both clear the 1.2 floor
    assert sl["twr_ignition"] == pytest.approx(1.78, abs=0.01)
    assert thrust_kn_at(k1, 101.325) == pytest.approx(828.8, abs=1.0)


def test_build_b_charon_dv_twr(parts):
    """06 §4.2 — NTR Mars transfer: dv 5,830, TWR 0.18."""
    ntr = parts["core:engine_ntr_k2"]["engine"]   # EN-NTR-S class
    eng = dict(ntr, thrust_kN=73.0, isp_s=900.0, isp_sl_s=900.0)
    stages = [StageDef(engines=[eng] * 3,
                       inert_t=11.7 + 9.0 + 9.0 + 1.5 + 1.2 + 0.5 + 1.2
                       + 30.0, prop_t=60.0)]
    r = stage_report(stages, mode="vac")[0]
    assert r["m0_t"] == pytest.approx(124.1, abs=0.01)
    assert r["dv_ms"] == pytest.approx(5_830.0, abs=2.0)
    assert r["twr_ignition"] == pytest.approx(0.18, abs=0.005)


def test_build_c_packmule_ep(parts):
    """06 §4.3 — Hall tug: dv 8,900, ṁ 8.59e-5 kg/s, 52% thrust at
    Mars distance (available power ÷ RATED power, constant Isp)."""
    aeps = parts["core:ep_hall"]["engine"]
    stages = [StageDef(engines=[aeps] * 4,
                       inert_t=0.46 + 0.75 + 0.24 + 1.00 + 8.00,
                       prop_t=4.0)]
    r = stage_report(stages, mode="vac")[0]
    assert r["m0_t"] == pytest.approx(14.45, abs=0.01)
    assert r["dv_ms"] == pytest.approx(8_900.0, abs=10.0)
    assert r["mdot_kgps"] == pytest.approx(8.59e-5, rel=0.01)
    # at 1.52 AU the 60 kWe arrays give 26 kWe → 52% of the 50 kWe rated
    avail = solar_kwe(60.0, 1.52)
    assert avail == pytest.approx(26.0, abs=0.05)
    assert ep_thrust_fraction(aeps, avail / 4) == pytest.approx(
        0.52, abs=0.005)
    powered = stage_report(stages, mode="vac", ep_power_kwe=avail)[0]
    assert powered["dv_ms"] == pytest.approx(r["dv_ms"])   # dv unchanged
    assert powered["burn_s"] == pytest.approx(r["burn_s"] / 0.52,
                                              rel=0.01)


def test_of_min_limit_and_mixed_isp(parts):
    """Burnable prop is min-limited by the scarcer resource (§2.4); a
    stranded surplus never counts toward dv."""
    mix = {"Oxygen": 6.0 / 7.0, "Hydrogen": 1.0 / 7.0}   # hydrolox 6:1
    assert burnable_prop_t({"Oxygen": 12.0, "Hydrogen": 2.0},
                           mix) == pytest.approx(14.0, abs=0.01)
    # hydrogen-starved: 0.7 t H2 caps the burn at 4.9 t total
    assert burnable_prop_t({"Oxygen": 12.0, "Hydrogen": 0.7},
                           mix) == pytest.approx(4.9, abs=0.01)
    assert burnable_prop_t({}, mix) == 0.0
    # mixed engines: thrust-weighted ΣF/Σ(F/Isp)
    a = {"thrust_kN": 1000.0, "isp_s": 300.0}
    b = {"thrust_kN": 1000.0, "isp_s": 450.0}
    assert mixed_isp([a, b], lambda e: e["isp_s"]) == pytest.approx(
        2000.0 / (1000.0 / 300.0 + 1000.0 / 450.0))
    assert mdot_kgps(a) == pytest.approx(1000e3 / (300 * G0))
