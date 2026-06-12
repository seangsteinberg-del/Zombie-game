"""Frame-budget gates (Z pulled forward, per the pygame-playability
commitment): the heavy scenes must keep per-frame WORK inside a 30 fps
budget at 720p headless, measured between ticks so the frame cap's sleep
never counts. Bounds carry CI slack — re-run before believing a failure
under parallel CPU load."""

import re
import subprocess
import sys

import pytest

BUDGET_AVG_MS = 33.0      # 30 fps floor
BUDGET_P95_MS = 60.0      # spikes (chunk regen, cache rebuild) get slack


def _perf(scene: str, frames: int = 150) -> tuple[float, float]:
    out = subprocess.run(
        [sys.executable, "-m", "aphelion.main", "--headless",
         "--scene", scene, "--frames", str(frames), "--perf"],
        capture_output=True, text=True, timeout=300)
    m = re.search(r"PERF avg=([\d.]+) p95=([\d.]+)", out.stdout)
    assert m, f"no PERF line from --scene {scene}:\n{out.stdout}\n{out.stderr}"
    return float(m.group(1)), float(m.group(2))


@pytest.mark.parametrize("scene", ["flight", "mine", "drydock", "aboard"])
def test_scene_frame_budget(scene):
    avg, p95 = _perf(scene)
    assert avg < BUDGET_AVG_MS, f"{scene}: avg {avg:.1f} ms over budget"
    assert p95 < BUDGET_P95_MS, f"{scene}: p95 {p95:.1f} ms over budget"
