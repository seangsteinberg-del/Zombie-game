"""Engine-core tests: event queue (13 §3.8), RNG discipline (13 §3.10),
clock/warp ladder (13 §3.5, 01 §3.6), ECS-lite (13 §3.3)."""

import math

import pytest

from aphelion.core.clock import (
    EVENT_GUARD_REAL_S,
    RAILS_RATES,
    SimClock,
    WarpController,
    WarpMode,
)
from aphelion.core.ecs import EntityRegistry
from aphelion.core.events import EventQueue, EventRecord
from aphelion.core.rng import RngRegistry
from aphelion.core.units import SIM_DT


# ---- event queue --------------------------------------------------------

def test_events_order_by_time_then_seq():
    q = EventQueue()
    q.post(EventRecord(kind="b", t_due=100.0))
    q.post(EventRecord(kind="a", t_due=50.0))
    q.post(EventRecord(kind="c", t_due=100.0))
    kinds = [r.kind for r in q.pop_due(200.0)]
    assert kinds == ["a", "b", "c"]   # same-time ties resolved by post order


def test_events_peek_and_clamp_contract():
    q = EventQueue()
    assert q.peek_time() == math.inf
    q.post(EventRecord(kind="soi_cross", t_due=1_000.0))
    assert q.peek_time() == 1_000.0
    assert q.pop_due(999.999) == []
    assert [r.kind for r in q.pop_due(1_000.0)] == ["soi_cross"]


def test_events_lazy_generation_invalidation():
    q = EventQueue()
    src = ("craft", 7)
    q.post(EventRecord(kind="soi_cross", t_due=500.0, source=src))
    q.post(EventRecord(kind="periapsis", t_due=600.0, source=src))
    q.post(EventRecord(kind="alarm", t_due=550.0, source=None))
    q.bump(src)   # burn changed the orbit: every prediction from src is stale
    q.post(EventRecord(kind="soi_cross_new", t_due=700.0, source=src))
    assert q.peek_time() == 550.0
    kinds = [r.kind for r in q.pop_due(1_000.0)]
    assert kinds == ["alarm", "soi_cross_new"]


# ---- rng registry --------------------------------------------------------

def test_rng_deterministic_across_registries():
    a = RngRegistry(123456789)
    b = RngRegistry(123456789)
    assert a.stream("failures", 42).random(8).tolist() == \
           b.stream("failures", 42).random(8).tolist()


def test_rng_streams_independent():
    a = RngRegistry(99)
    ref = RngRegistry(99).stream("failures", 1).random(4).tolist()
    a.stream("terrain", "moon", 3, 7).random(1000)   # burn another stream
    assert a.stream("failures", 1).random(4).tolist() == ref


def test_rng_different_seeds_differ():
    assert RngRegistry(1).stream("solar").random(4).tolist() != \
           RngRegistry(2).stream("solar").random(4).tolist()


def test_rng_state_roundtrip():
    a = RngRegistry(7)
    a.stream("failures", 5).random(13)
    state = a.state()
    b = RngRegistry.from_state(state)
    assert a.stream("failures", 5).random(6).tolist() == \
           b.stream("failures", 5).random(6).tolist()


def test_rng_rejects_unstable_keys():
    with pytest.raises(TypeError):
        RngRegistry(1).stream("bad", 3.14)   # floats are not stable key parts


# ---- clock ---------------------------------------------------------------

def test_clock_drift_free_numeric_time():
    c = SimClock(t0=1_000.0)
    for _ in range(1_000_000):
        c.step_numeric()
    # int64 counter: exactly anchor + n*SIM_DT, no float accumulation drift
    assert c.t == 1_000.0 + 1_000_000 * SIM_DT


def test_clock_rebase_and_analytic_advance():
    c = SimClock()
    c.step_numeric(50)            # 1.0 s
    c.advance_analytic(16_667.0)  # one tier-7 frame span
    assert c.t == 16_667.0
    with pytest.raises(ValueError):
        c.advance_analytic(0.0)


# ---- warp controller -----------------------------------------------------

def test_warp_ladder_rates():
    assert RAILS_RATES == (5.0, 25.0, 100.0, 1_000.0, 10_000.0, 100_000.0, 1_000_000.0)


def test_event_guard_tier_selection():
    # Event 10 sim-minutes out: tier must keep >= 5 real seconds of margin.
    t_event = 600.0
    tier = WarpController.max_guarded_tier(0.0, t_event)
    assert RAILS_RATES[tier - 1] == 100.0     # 600/100 = 6 s ok; 600/1000 < 5 s
    assert WarpController.max_guarded_tier(0.0, math.inf) == len(RAILS_RATES)
    assert WarpController.max_guarded_tier(0.0, -1.0) == 0


def test_warp_guard_steps_down_and_lands_at_numeric():
    w = WarpController()
    granted = w.request_rails(7, coasting=True, in_atmosphere=False,
                              t_now=0.0, t_next_event=math.inf)
    assert granted and w.mode is WarpMode.RAILS and w.rails_tier == 7
    w.apply_guard(t_now=0.0, t_next_event=2_000_000.0)
    assert w.rails_tier < 7
    w.apply_guard(t_now=0.0, t_next_event=1.0)   # event imminent -> 1x
    assert w.mode is WarpMode.NUMERIC and w.rate == 1.0


def test_rails_forbidden_under_thrust_or_in_atmosphere():
    w = WarpController()
    assert not w.request_rails(3, coasting=False, in_atmosphere=False,
                               t_now=0.0, t_next_event=math.inf)
    assert not w.request_rails(3, coasting=True, in_atmosphere=True,
                               t_now=0.0, t_next_event=math.inf)


def test_physics_warp_blocked_by_q_and_acceleration():
    w = WarpController()
    assert not w.request_physics_warp(2, q_pa=25_000.0, a_thrust=5.0)
    assert not w.request_physics_warp(2, q_pa=1_000.0, a_thrust=35.0)
    assert w.request_physics_warp(2, q_pa=1_000.0, a_thrust=5.0)
    assert w.substeps == 3 and w.rate == 3.0    # P3


# ---- ecs-lite ------------------------------------------------------------

def test_ecs_ids_monotonic_never_reused_zero_reserved():
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class Tag:
        name: str

    reg = EntityRegistry()
    a = reg.new_entity()
    b = reg.new_entity()
    assert a == 1 and b == 2
    reg.add(a, Tag("x"))
    reg.destroy(a)
    c = reg.new_entity()
    assert c == 3                      # never reused
    assert reg.get(a, Tag) is None     # destroy cleared stores
    assert not reg.is_alive(a)


def test_ecs_store_iteration_is_insertion_ordered():
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class Orbit:
        a: float

    @dataclass(frozen=True)
    class Vessel:
        name: str

    reg = EntityRegistry()
    ids = [reg.new_entity() for _ in range(5)]
    for eid in [ids[3], ids[0], ids[4]]:
        reg.add(eid, Orbit(a=float(eid)))
    reg.add(ids[3], Vessel(name="K"))
    reg.add(ids[4], Vessel(name="L"))
    assert list(reg.store(Orbit)) == [ids[3], ids[0], ids[4]]
    assert list(reg.entities_with(Orbit, Vessel)) == [ids[3], ids[4]]
