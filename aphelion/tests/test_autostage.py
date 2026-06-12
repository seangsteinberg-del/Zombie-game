"""Auto-staging + drydock readout math (06 §2.2/§2.3/§2.6)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from aphelion.content.loader import default_data_dir, load_packs
from aphelion.sim.vessels.autostage import (
    cost_musd, flyable_stack, stage_components, to_stage_defs,
    torque_badge, wet_com)
from aphelion.sim.vessels.buildermath import stage_report
from aphelion.sim.vessels.grid import GridVessel


@pytest.fixture(scope="module")
def parts():
    return load_packs(default_data_dir()).by_type("parts")


def two_stage(parts) -> GridVessel:
    """Methalox booster under a decoupler, lander stage above."""
    v = GridVessel()
    v.add("core:engine_m2256", parts["core:engine_m2256"], 0, 0)   # 2×3
    v.add("core:tank_ml_m", parts["core:tank_ml_m"], 0, 3)         # 2×4
    v.add("core:st_dc2", parts["core:st_dc2"], 0, 7)               # 2×1
    v.add("core:engine_ml24", parts["core:engine_ml24"], 0, 8)     # 1×1
    v.add("core:tank_ml_s", parts["core:tank_ml_s"], 0, 9)         # 2×2
    v.add("core:capsule_vela", parts["core:capsule_vela"], 0, 11)  # 2×3
    return v


def test_stage_split_at_decoupler(parts):
    v = two_stage(parts)
    comps = stage_components(v)
    assert len(comps) == 2
    assert 0 in comps[0] and 1 in comps[0]      # booster is the bottom
    assert 2 in comps[0]                        # decoupler rides down
    assert {3, 4, 5} <= set(comps[1])
    # no decouplers -> one stage
    solo = GridVessel()
    solo.add("core:capsule_vela", parts["core:capsule_vela"], 0, 0)
    assert len(stage_components(solo)) == 1


def test_stage_defs_and_dv_chain(parts):
    v = two_stage(parts)
    s1, s2 = to_stage_defs(v)
    assert len(s1.engines) == 1 and len(s2.engines) == 1
    assert s1.prop_t == pytest.approx(12.0, abs=0.05)   # full ML-M
    assert s2.prop_t == pytest.approx(4.5, abs=0.05)    # full ML-S
    rep = stage_report([s1, s2], mode="vac")
    assert rep[0]["m0_t"] > rep[1]["m0_t"]
    assert rep[0]["dv_ms"] > 0 and rep[1]["dv_ms"] > 0
    # an upper stage with no oxidizer strands its methane as inert
    dry = GridVessel()
    dry.add("core:engine_ml24", parts["core:engine_ml24"], 0, 0)
    dry.add("core:tank_ch4_m", parts["core:tank_ch4_m"], 0, 1)
    sd = to_stage_defs(dry)[0]
    assert sd.prop_t == 0.0
    assert sd.inert_t == pytest.approx(0.08 + 0.35 + 7.0, abs=0.01)


def test_torque_badge_symmetry(parts):
    v = GridVessel()
    v.add("core:tank_ml_m", parts["core:tank_ml_m"], 0, 3)
    v.add("core:engine_m2256", parts["core:engine_m2256"], 0, 0)
    assert torque_badge(v)["badge"] == "GREEN"   # engine under the COM
    # bolt the engine far off-axis: thrust line misses the COM, RED
    off = GridVessel()
    off.add("core:tank_ml_m", parts["core:tank_ml_m"], 0, 3)
    off.add("core:engine_m2256", parts["core:engine_m2256"], 6, 0)
    assert torque_badge(off)["badge"] == "RED"


def test_wet_com_cost_and_flyable_bridge(parts):
    v = two_stage(parts)
    dry_cx, dry_cy = v.com()
    wet_cx, wet_cy = wet_com(v)
    assert wet_cx == pytest.approx(dry_cx, abs=0.2)
    assert wet_cy < dry_cy            # 12 t of prop sits low in the stack
    assert cost_musd(v) == pytest.approx(
        2.5 + 0.9 + 0.2 + 1.5 + 0.4 + 25.0, abs=0.01)
    plan = flyable_stack(v)
    assert plan == [["core:engine_m2256", "core:tank_ml_m"],
                    ["core:engine_ml24", "core:tank_ml_s",
                     "core:capsule_vela"]]
