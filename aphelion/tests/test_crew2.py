"""Crew v2 (08 §4): five tracks, P_health composition, morale dynamics,
conditioning ODE, medical events, XP growth, archetypes."""

import random

import pytest

from aphelion.game.crew import (
    CrewMember, ROLES, best_skill, candidates, derive_skills,
    morale_target)
from aphelion.sim.habitat.dose import CrewDose


def member(role="engineer", skill=3, **kw) -> CrewMember:
    return CrewMember("Test Subject", role, skill, CrewDose(), **kw)


def test_five_tracks_derive_from_archetype():
    assert ROLES == ("pilot", "engineer", "scientist", "medic",
                     "agronomist")
    m = member("scientist", 3)
    assert m.skills["scientist"] == 3
    assert m.skills["medic"] == 1 and m.skills["agronomist"] == 1
    rookie = derive_skills("pilot", 1)
    assert rookie["pilot"] == 1 and rookie["engineer"] == 0


def test_p_health_worked_example():
    """C=70, minor illness 0.30, prodromal ARS 0.30 → 0.343 (08 §4.1)."""
    m = member(cond=70.0)
    m.conditions.append({"kind": "minor_illness", "age": 0.0,
                         "treated": False})
    m.dose.accrue_event_msv(400.0, t=0.0)        # prodromal band
    assert m.p_health(0.0) == pytest.approx(0.343, abs=0.01)
    # conditioning floors at 0.3 even fully deconditioned
    wreck = member(cond=0.0)
    assert wreck.p_health() == pytest.approx(0.3)


def test_task_rate_law():
    m = member("engineer", 4, morale=100.0)
    assert m.task_rate("engineer") == pytest.approx(1.5)
    assert m.task_rate("agronomist") == pytest.approx(0.5)
    m.morale = 0.0
    assert m.task_rate("engineer") == pytest.approx(0.75)
    assert m.phi_err == pytest.approx(2.0)


def test_morale_lags_toward_target():
    m = member(morale=70.0)
    good = morale_target({"vol_m3": 30.0, "private_quarters": True,
                          "fresh_food": True, "window": True,
                          "g_eff": 9.81})
    assert good == pytest.approx(88.0)
    for _ in range(60):
        m.step_morale(good, 1.0)
    assert m.morale == pytest.approx(good, abs=1.0)
    cramped = morale_target({"vol_m3": 5.0, "private_quarters": False,
                             "ration_days": 90.0, "light_min": 20.0,
                             "g_eff": 0.0, "blackout": True})
    assert cramped < 15.0
    for _ in range(40):
        m.step_morale(cramped, 1.0)
    assert m.crisis


def test_conditioning_ode_tuning():
    """180 d free-fall no exercise ≈ 80-point loss; 2 h/day exercise cuts
    it to ~13; Mars-g recovers (08 §4.3)."""
    m = member()
    for _ in range(180):
        m.step_conditioning(0.0, 0.0, 1.0)
    assert m.cond == pytest.approx(100.0 - 79.2, abs=1.0)
    assert not m.eva_ok()                        # C < 40 gates EVA
    m2 = member()
    for _ in range(180):
        m2.step_conditioning(0.0, 2.0, 1.0)
    assert 100.0 - m2.cond == pytest.approx(12.7, abs=1.0)
    assert m2.eva_ok()
    hurt = member(cond=50.0)
    for _ in range(200):
        hurt.step_conditioning(3.71, 0.0, 1.0)
    assert hurt.cond > 55.0                      # Mars-g recovery zone
    assert member(cond=20.0).readapt_days() == pytest.approx(8.0)


def test_medical_treat_or_die():
    m = member()
    m.conditions.append({"kind": "appendicitis", "age": 0.0,
                         "treated": False})
    assert m.bedridden
    rng = random.Random(7)
    # no medic aboard: fatal inside the window
    out = None
    for _ in range(5):
        out = m.step_medical(1.0, medic_level=0, medsupplies_kg=10.0,
                             rng=rng)
        if out["died_of"]:
            break
    assert out["died_of"] == "appendicitis"
    # a level-3 surgeon with supplies saves the next case
    m2 = member()
    m2.conditions.append({"kind": "appendicitis", "age": 0.0,
                          "treated": False})
    out2 = m2.step_medical(1.0, medic_level=3, medsupplies_kg=10.0,
                           rng=rng)
    assert out2["supplies_used"] == pytest.approx(5.0)
    assert out2["died_of"] is None
    for _ in range(14):
        m2.step_medical(1.0, 3, 10.0, rng)
    assert m2.conditions == []                   # recovered


def test_medical_event_rate_is_rare():
    """~0.0008/day: a 4-crew year sees roughly one event."""
    rng = random.Random(3)
    m = member(morale=100.0)
    events = sum(1 for _ in range(10_000)
                 if m.roll_medical(rng) is not None)
    m.conditions.clear()
    assert 2 <= events <= 25                     # ~8 expected


def test_xp_growth_and_tier_cap():
    m = member("pilot", 2)
    for _ in range(1_200):
        if m.accrue_xp("pilot", 1.0, cap=3):
            break
    assert m.skills["pilot"] == 3 and m.skill == 3
    # capped at tier ceiling: no growth past 3 until T2
    assert not any(m.accrue_xp("pilot", 100.0, cap=3) for _ in range(50))
    assert m.skills["pilot"] == 3
    assert m.accrue_xp("pilot", 1_600.0, cap=4)
    assert m.skills["pilot"] == 4


def test_archetype_pool_has_surgeons_and_agronomists():
    cands = candidates({}, count=22)
    roles = {c.role for c in cands}
    assert "medic" in roles and "agronomist" in roles
    doc = next(c for c in cands if c.role == "medic" and c.skill == 3)
    assert doc.skills["medic"] == 3


def test_best_skill_reads_tracks_not_roles():
    class FV:
        crew = ["A", "B"]
    crew = {"A": CrewMember("A", "scientist", 3),
            "B": CrewMember("B", "pilot", 2)}
    # the scientist archetype carries medic 1 — tracks, not job titles
    assert best_skill(FV, crew, "medic") == 1
    assert best_skill(FV, crew, "pilot") == 2
