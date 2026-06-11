"""Ledger tests (13 §3.9): the binding ledger-vs-brute-force-ticker
equivalence (< 0.1 %), warp-span invariance, throttling state machine,
power coupling, and the Sabatier chain on canonical RX-03 stoichiometry.
"""

import math

import pytest

from aphelion.sim.ledger.network import (
    BATTERY,
    BLOCKED,
    Buffer,
    LedgerNetwork,
    Module,
    RUNNING,
    Source,
    STARVED,
)


def sabatier_net(h2_kg: float = 100.0) -> LedgerNetwork:
    """CO2 + H2 -> CH4 + H2O on RX-03 canon (2.75 CO2 + 0.50 H2 -> 1.00 CH4
    + 2.25 H2O), 0.01 kg/s CH4 nominal, 200 kWh/t = 2 kW at this rate."""
    net = LedgerNetwork()
    net.add_buffer("CO2", 5_000.0, 10_000.0)
    net.add_buffer("Hydrogen", h2_kg, 1_000.0)
    net.add_buffer("Methane", 0.0, 1_000.0)
    net.add_buffer("Water", 0.0, 10_000.0)
    net.add_module(Module(
        module_id="sabatier_1",
        inputs={"CO2": 2.75, "Hydrogen": 0.50},
        outputs={"Methane": 1.00, "Water": 2.25},
        rate_kgps=0.01,
        power_kw=2.0,
    ))
    net.add_module(Module(
        module_id="solar_1", inputs={}, outputs={}, rate_kgps=0.0,
        power_kw=-10.0))
    return net


def brute_force_tick(net: LedgerNetwork, t0: float, t1: float,
                     dt: float = 1.0) -> None:
    """The independent reference integrator (13 §3.16): re-solve every
    second, integrate naively."""
    t = t0
    while t < t1:
        step = min(dt, t1 - t)
        _, rates, _ = net.solve_rates()
        for res, buf in net.buffers.items():
            buf.level += rates.get(res, 0.0) * step
            buf.clamp()
        for s in net.sources:
            if s.remaining is not math.inf and s.remaining > 0.0:
                s.remaining = max(0.0, s.remaining - abs(s.rate_kgps) * step)
        # ticker applies the same boundary transitions
        for kind, res_list in (("buffer_empty",
                                [r for r, b in net.buffers.items() if b.level <= 0.0]),
                               ("buffer_full",
                                [r for r, b in net.buffers.items()
                                 if b.level >= b.capacity])):
            for res in res_list:
                net._apply_boundary(kind, res)
        t += step


def test_ledger_matches_brute_force_ticker():
    """THE binding equivalence test: ledger advance vs 1 s ticker < 0.1 %."""
    a = sabatier_net()
    b = sabatier_net()
    span = 6.0 * 3_600.0          # six hours crosses the H2-empty boundary
    a.advance(0.0, span)
    brute_force_tick(b, 0.0, span)
    for res in a.buffers:
        la, lb = a.buffers[res].level, b.buffers[res].level
        scale = max(abs(lb), 1.0)
        assert abs(la - lb) / scale < 1e-3, (res, la, lb)


def test_ledger_warp_span_invariance():
    """advance(t0, t1) must equal any split of the same span — exactness is
    what makes tier-7 warp safe."""
    a = sabatier_net()
    b = sabatier_net()
    a.advance(0.0, 20_000.0)
    b.advance(0.0, 137.0)
    b.advance(137.0, 6_000.5)
    b.advance(6_000.5, 20_000.0)
    for res in a.buffers:
        assert a.buffers[res].level == pytest.approx(b.buffers[res].level,
                                                     rel=1e-12, abs=1e-9)


def test_h2_exhaustion_boundary_exact():
    net = sabatier_net(h2_kg=100.0)
    # H2 consumption rate = 0.5 * 0.01 = 0.005 kg/s -> empty at t = 20,000 s
    events = net.advance(0.0, 30_000.0)
    empties = [e for e in events if e.kind == "buffer_empty" and e.subject == "Hydrogen"]
    assert len(empties) == 1
    assert empties[0].t == pytest.approx(20_000.0, abs=1e-6)
    # production stopped exactly there: CH4 = 0.01 * 20,000 = 200 kg
    assert net.buffers["Methane"].level == pytest.approx(200.0, rel=1e-9)
    assert net.buffers["Water"].level == pytest.approx(450.0, rel=1e-9)
    sab = net.modules[0]
    assert sab.state == STARVED


def test_starved_module_recovers_on_resupply():
    net = sabatier_net(h2_kg=10.0)
    net.advance(0.0, 3_000.0)         # H2 empty at t=2,000
    assert net.modules[0].state == STARVED
    net.buffers["Hydrogen"].level = 50.0
    net._apply_boundary("noop", "")   # recovery check runs on boundaries
    assert net.modules[0].state == RUNNING


def test_blocked_on_full_output():
    net = sabatier_net()
    net.buffers["Water"] = Buffer(9_999.99, 10_000.0)
    events = net.advance(0.0, 10_000.0)
    assert any(e.kind == "buffer_full" and e.subject == "Water" for e in events)
    assert net.modules[0].state == BLOCKED


def test_power_deficit_throttles_rates():
    net = sabatier_net()
    net.modules[1].power_kw = -1.0    # solar now supplies 1 kW vs 2 kW demand
    _, rates, f_power = net.solve_rates()
    assert f_power == pytest.approx(0.5)
    assert rates["Methane"] == pytest.approx(0.005)   # half rate


def test_battery_bridges_power_deficit_until_empty():
    net = sabatier_net()
    net.modules[1].power_kw = -1.0
    net.add_buffer(BATTERY, 1.0, 10.0)    # 1 kWh stored
    _, rates, f_power = net.solve_rates()
    assert f_power == 1.0                  # battery covers the 1 kW deficit
    assert rates[BATTERY] == pytest.approx(-1.0 / 3_600.0)
    events = net.advance(0.0, 7_200.0)
    assert any(e.kind == "buffer_empty" and e.subject == BATTERY for e in events)
    _, _, f_after = net.solve_rates()
    assert f_after == pytest.approx(0.5)


def test_deposit_exhaustion():
    net = LedgerNetwork()
    net.add_buffer("Water", 0.0, 1_000.0)
    net.add_source(Source("ice_patch", "Water", 0.1, remaining=360.0))
    events = net.advance(0.0, 10_000.0)
    assert any(e.kind == "deposit_exhausted" for e in events)
    assert net.buffers["Water"].level == pytest.approx(360.0, rel=1e-9)


def test_ledger_determinism():
    a = sabatier_net()
    b = sabatier_net()
    ea = a.advance(0.0, 50_000.0)
    eb = b.advance(0.0, 50_000.0)
    assert [(e.t, e.kind, e.subject) for e in ea] == \
           [(e.t, e.kind, e.subject) for e in eb]
    for res in a.buffers:
        assert a.buffers[res].level == b.buffers[res].level
