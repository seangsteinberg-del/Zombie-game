"""Structural checks (06 §2.8) — Build A's joint worked example, the
spanning-tree loads on a grid stack, and the pre-flight q-sim."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from aphelion.content.loader import default_data_dir, load_packs
from aphelion.sim.vessels.buildermath import G0
from aphelion.sim.vessels.grid import GridVessel
from aphelion.sim.vessels.structure import (
    ascent_qsim, joint_load_kn, limiter_clamped_accel, part_q_max_kpa,
    qalpha_limit_kpadeg, stack_joint_loads, validate_e7)


@pytest.fixture(scope="module")
def parts():
    return load_packs(default_data_dir()).by_type("parts")


def test_build_a_joint_worked_example():
    """06 §4.1: m_above the interstage 19.31 t. Unclamped burnout would
    pull 7.4 g; the saved 5 g limiter clamps to 49.03 m/s² → 947 kN ≤
    1,200 PASS. At the 6 g uncrewed default: 1,136 kN (5% margin).
    On-pad: 189 kN."""
    a5 = limiter_clamped_accel(1_828.0, 25.25, 5.0)
    assert a5 == pytest.approx(49.03, abs=0.01)
    assert 1_828.0 / 25.25 == pytest.approx(72.4, abs=0.1)   # unclamped
    assert joint_load_kn(19.31, a5) == pytest.approx(947.0, abs=1.0)
    a6 = limiter_clamped_accel(1_828.0, 25.25, 6.0)
    assert joint_load_kn(19.31, a6) == pytest.approx(1_136.0, abs=1.0)
    assert joint_load_kn(19.31, G0) == pytest.approx(189.0, abs=1.0)


def test_grid_stack_loads_heaviest_at_the_bottom(parts):
    v = GridVessel()
    v.add("core:engine_m2256", parts["core:engine_m2256"], 0, 0)
    v.add("core:tank_ml_m", parts["core:tank_ml_m"], 0, 3)
    v.add("core:capsule_vela", parts["core:capsule_vela"], 0, 7)
    rows = stack_joint_loads(v, 3.0 * G0)
    assert len(rows) == 2
    by_load = sorted(rows, key=lambda r: -r["load_kn"])
    # the engine-tank joint carries tank+capsule; tank-capsule only the
    # capsule — and a 3 g stack is nowhere near the 1,200 kN ratings
    assert by_load[0]["m_above_t"] > by_load[1]["m_above_t"]
    assert all(r["ok"] for r in rows)
    # a brutal 40 g hammer overloads the bottom joint
    hard = stack_joint_loads(v, 40.0 * G0)
    assert any(not r["ok"] for r in hard)


def test_ascent_qsim_throttle_bucket():
    """Build-A-class first stage: the bucket holds peak q in the real
    max-Q band (~35 kPa target, never the unthrottled ~80), q·α stays
    inside the 170 kPa·deg envelope, and the stage makes altitude."""
    out = ascent_qsim(thrust_kn=1_828.0, mdot_kgps=599.4, m0_t=95.25,
                      prop_t=70.0, frontal_m2=2.0)
    assert 20.0 < out["peak_q_kpa"] < 45.0
    assert out["peak_qalpha"] < 170.0
    assert out["burnout_h_m"] > 30_000.0
    # throttling through max-Q stretches the burn past the unthrottled
    # 117 s — the propellant doesn't care about the clock
    assert 117.0 <= out["trace"][-1][0] < 132.0


def test_e7_and_qalpha_bonus(parts):
    v = GridVessel()
    v.add("core:capsule_vela", parts["core:capsule_vela"], 0, 2)
    v.add("core:rcs_hyp", parts["core:rcs_hyp"], 2, 3)
    assert part_q_max_kpa(parts["core:capsule_vela"]) == 50.0
    assert part_q_max_kpa(parts["core:rcs_hyp"]) == 35.0
    assert validate_e7(v, 30.0) == []
    assert validate_e7(v, 40.0) == [1]          # the radial quad dies
    assert qalpha_limit_kpadeg(v) == 170.0
    v.add("core:st_fin", parts["core:st_fin"], 0, 0)
    v.add("core:st_fin", parts["core:st_fin"], 3, 0)
    v.add("core:st_fin", parts["core:st_fin"], 5, 0)
    assert qalpha_limit_kpadeg(v) == 250.0      # max 2 fins counted