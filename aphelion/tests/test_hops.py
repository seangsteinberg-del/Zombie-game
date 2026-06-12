"""10 §2.6 anchors: the Δv table rows for Moon/Mercury/Ceres/Europa,
the lander-domain boundary, the catalog hop quotes, and C23 plume."""

import pytest

from aphelion.core.units import G0
from aphelion.sim.vehicles.hops import (
    dv_hop_ms, dv_hop_short_ms, is_lander_domain, plume_effects,
    v_launch_ms)

MU_MOON, R_MOON = 4.9048695e12, 1.7374e6
MU_MERCURY, R_MERCURY = 2.2032e13, 2.4397e6
MU_CERES, R_CERES = 6.26325e10, 4.73e5
MU_EUROPA, R_EUROPA = 3.2027e12, 1.5608e6


def test_dv_table_anchors():
    """§2.6 table: 10 km — Moon 281 / Mercury 424 / Ceres 114 /
    Europa 252; 100 km — 873/1318/339/781; 500 km Moon 1851."""
    assert dv_hop_ms(MU_MOON, R_MOON, 10e3) == pytest.approx(281, abs=4)
    assert dv_hop_ms(MU_MERCURY, R_MERCURY, 10e3) == pytest.approx(
        424, abs=6)
    assert dv_hop_ms(MU_CERES, R_CERES, 10e3) == pytest.approx(114,
                                                               abs=3)
    assert dv_hop_ms(MU_EUROPA, R_EUROPA, 10e3) == pytest.approx(252,
                                                                 abs=4)
    assert dv_hop_ms(MU_MOON, R_MOON, 100e3) == pytest.approx(873,
                                                              abs=10)
    assert dv_hop_ms(MU_MERCURY, R_MERCURY, 100e3) == pytest.approx(
        1_318, abs=15)
    assert dv_hop_ms(MU_MOON, R_MOON, 500e3) == pytest.approx(1_851,
                                                              abs=20)
    # short-hop shortcut agrees at 1 km on the Moon (89 m/s)
    assert dv_hop_short_ms(1.62, 1e3) == pytest.approx(89, abs=2)


def test_lander_boundary():
    """Past a quarter circumference it's a lander, not a hop."""
    assert not is_lander_domain(R_MOON, 1_000e3)
    assert is_lander_domain(R_MOON, 3_000e3)
    assert is_lander_domain(R_CERES, 800e3)


def test_catalog_hop_quotes():
    """§1.5: HOP-S 560 m/s tank-full -> 40 km Moon; HOP-P (ML-111,
    DECISIONS A8) 1,778 m/s -> ~445 km with the 20% abort reserve
    leaving ~1,422 usable."""
    import math
    dv_hop_s = 300.0 * G0 * math.log(60.5 / 50.0)
    assert dv_hop_s == pytest.approx(560.0, abs=3.0)
    assert dv_hop_ms(MU_MOON, R_MOON, 40e3) < dv_hop_s
    dv_hop_p = 355.0 * G0 * math.log(20.0 / 12.0)
    assert dv_hop_p == pytest.approx(1_778.0, abs=5.0)
    assert dv_hop_ms(MU_MOON, R_MOON, 445e3) < dv_hop_p
    usable = dv_hop_p * 0.8                  # mandatory abort reserve
    assert dv_hop_ms(MU_MOON, R_MOON, 280e3) < usable
    assert dv_hop_ms(MU_MOON, R_MOON, 320e3) > usable


def test_plume_rule_c23():
    assert plume_effects(120.0, on_pad=True) == {}
    far = plume_effects(150.0, on_pad=False)
    assert far["condition"] == pytest.approx(0.02)
    assert "close_roll_p" not in far
    near = plume_effects(30.0, on_pad=False)
    assert near["close_roll_p"] == pytest.approx(0.30)
    assert plume_effects(250.0, on_pad=False) == {}
