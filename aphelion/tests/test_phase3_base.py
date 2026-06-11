"""PHASE 3 acceptance (13 §6): an UNATTENDED lunar propellant base runs six
warped months — failures pre-rolled and deterministic, repairs by a
maintenance bot with a fixed turnaround, production within ledger-exact
expectations regardless of how the warp spans are split."""

import math

import pytest

from aphelion.core.rng import RngRegistry
from aphelion.sim.habitat.lsc import DAY, oga_electrolysis
from aphelion.sim.ledger.network import (
    FAILED,
    LedgerNetwork,
    Module,
    RUNNING,
    Source,
)

MONTH = 30.0 * DAY
REPAIR_TURNAROUND = 48.0 * 3_600.0      # maintenance bot, 48 h


def build_propellant_base(seed: int = 777) -> LedgerNetwork:
    net = LedgerNetwork(rng=RngRegistry(seed))
    net.add_buffer("Water", 100.0, 50_000.0)
    net.add_buffer("Oxygen", 0.0, 200_000.0)
    net.add_buffer("Hydrogen", 0.0, 30_000.0)
    net.add_source(Source("psr_ice", "Water", 0.03, remaining=1.0e6))
    oga = oga_electrolysis(rate_o2_kgps=0.02, power_kw=80.0)
    oga.mtbf_s = 45.0 * DAY              # 05 wear-model class placeholder
    net.add_module(oga)
    net.add_module(Module("reactor", inputs={}, outputs={}, rate_kgps=0.0,
                          power_kw=-120.0))
    return net


def run_unattended(net: LedgerNetwork, t0: float, t1: float,
                   spans: int = 1) -> list:
    """Advance in N spans; an unattended maintenance bot repairs each
    failure exactly REPAIR_TURNAROUND after it lands. Failure instants are
    PRE-ROLLED and knowable, so the harness clamps each advance to the
    next failure/repair — exactly what the global event queue does in the
    live sim loop (events are exact clamps)."""
    all_events = []
    pending_repairs: list[tuple[float, str]] = []
    cuts = [t0 + (t1 - t0) * i / spans for i in range(spans + 1)]
    for a, b in zip(cuts, cuts[1:]):
        t = a
        guard = 0
        while t < b - 1e-9 and guard < 1_000:
            guard += 1
            net.roll_failures(t)
            t_fail = min((m.failure_t for m in net.modules
                          if m.failure_t is not None and m.state == RUNNING
                          and m.failure_t > t), default=math.inf)
            t_rep = min((r[0] for r in pending_repairs), default=math.inf)
            t_stop = min(b, t_rep, t_fail + 1.0)
            events = net.advance(t, t_stop)
            all_events.extend(events)
            for e in events:
                if e.kind == "module_failed":
                    pending_repairs.append((e.t + REPAIR_TURNAROUND, e.subject))
            if t_rep <= t_stop + 1e-6:
                due = min(pending_repairs)
                pending_repairs.remove(due)
                t_repair, mid = due
                mod = [m for m in net.modules if m.module_id == mid][0]
                net.repair(mod, t_repair)
            t = t_stop
    return all_events


def test_phase3_unattended_base_six_months():
    net = build_propellant_base()
    events = run_unattended(net, 0.0, 6.0 * MONTH)

    failures = [e for e in events if e.kind == "module_failed"]
    assert len(failures) >= 2          # MTBF 45 d over 180 d: failures happen
    # base survived and produced at scale: > 150 t of LOX over six months
    # (0.02 kg/s * 180 d ~ 311 t ceiling, minus downtime from failures)
    assert net.buffers["Oxygen"].level > 150_000.0
    # stoichiometry holds across failures/repairs
    o2 = net.buffers["Oxygen"].level
    h2 = net.buffers["Hydrogen"].level
    assert h2 == pytest.approx(o2 * 0.111 / 0.889, rel=1e-9)


def test_phase3_failures_deterministic_and_warp_invariant():
    """The binding property: identical failure instants and final stores no
    matter how the six months are split into warp spans."""
    a = build_propellant_base()
    b = build_propellant_base()
    ev_a = run_unattended(a, 0.0, 6.0 * MONTH, spans=1)
    ev_b = run_unattended(b, 0.0, 6.0 * MONTH, spans=37)

    fa = [(round(e.t, 6), e.subject) for e in ev_a if e.kind == "module_failed"]
    fb = [(round(e.t, 6), e.subject) for e in ev_b if e.kind == "module_failed"]
    assert fa == fb
    for res in a.buffers:
        assert a.buffers[res].level == pytest.approx(b.buffers[res].level,
                                                     rel=1e-9, abs=1e-6)


def test_failure_lands_module_in_failed_state():
    net = build_propellant_base(seed=3)
    oga = net.modules[0]
    net.advance(0.0, 0.0 + 1.0)         # trigger the pre-roll
    assert oga.failure_t is not None
    t_fail = oga.failure_t
    events = net.advance(1.0, t_fail + 10.0)
    assert any(e.kind == "module_failed" for e in events)
    assert oga.state == FAILED
    net.repair(oga, t_fail + 10.0)
    assert oga.state == RUNNING
    assert oga.failure_t is not None and oga.failure_t > t_fail


def test_different_seeds_different_fates():
    a = build_propellant_base(seed=1)
    b = build_propellant_base(seed=2)
    a.advance(0.0, 1.0)
    b.advance(0.0, 1.0)
    assert a.modules[0].failure_t != b.modules[0].failure_t
