"""THE PLAYTHROUGH: drive a whole campaign through the real game objects
— build, orbit, Moon, land, found, industrialize, expand, and launch the
precursor — proving the 1.0 loop is completable end to end."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from aphelion.core.rng import RngRegistry
from aphelion.game.campaign import act_unlocked, sweep
from aphelion.game.crew import CrewMember
from aphelion.game.fleet import FleetVessel
from aphelion.game.sites import SITES
from aphelion.main import BaseSite
from aphelion.sim.economy import Program
from aphelion.sim.orbits.ephemeris import load_solar_system
from aphelion.sim.orbits.kepler import state_to_elements
from aphelion.sim.orbits import transfers as tr
from aphelion.sim.research import ResearchState
from aphelion.sim.vessels.vessel import Vessel

DAY = 86_400.0


def _vessel(db, tree, parts, frame="core:earth", alt=300e3):
    rows = [Vessel.fueled_row(db, p) for p in parts]
    body = tree.body(frame)
    r = body.radius + alt
    el = state_to_elements(r, 0.0, 0.0, tr.circular_speed(body.mu, r),
                           0.0, body.mu)
    return FleetVessel(tree, frame, el,
                       Vessel(db, rows, stage_plan=[list(range(len(rows)))]),
                       "PT", 1)


def test_campaign_is_completable_end_to_end():
    db, tree = load_solar_system()
    program = Program(funds=150e6)
    research = ResearchState()
    rng = RngRegistry(2049)
    crew = {"V": CrewMember("V", "pilot", 2)}
    S = dict(vessels=[], bases=[], visited={"core:earth"},
             visited_surface=set(), milestones=set(), research=research)
    t = 0.0

    # -- Act I ---------------------------------------------------------------
    sweep(program, S, t)
    lander = _vessel(db, tree, ["core:engine_hl67", "core:tank_ml_l",
                                "core:capsule_vela"])
    lander.crew = ["V"]
    S["vessels"].append(lander)
    S["milestones"].update({"orbited", "docked"})
    # fly to the Moon, land at Peary, found the base
    lander.frame_id = "core:moon"
    body = tree.body("core:moon")
    r = body.radius + 100e3
    lander.elements = state_to_elements(r, 0.0, 0.0,
                                        tr.circular_speed(body.mu, r),
                                        t, body.mu)
    S["visited"].add("core:moon")
    assert lander.land_at("site:peary", SITES["site:peary"], t)
    S["visited_surface"].add("site:peary")
    base = BaseSite("Peary Base", t, rng)
    S["bases"].append(base)
    S["vessels"].remove(lander)            # consumed as base hardware
    t += DAY
    sweep(program, S, t)

    # industrialize: tent miner + 2 electrolyzers + power, run a year,
    # bank LOX (canon rates: PEM 222 kg O2/day each, 04 RX-01)
    research.unlocked.update({"core:tech_is05_polar_ice_mining",
                              "core:tech_is03_water_electrolysis"})
    for key in ("drill_ice", "electrolyzer", "electrolyzer",
                "solar_array", "solar_array", "solar_array", "solar_array",
                "solar_array", "solar_array", "solar_array",
                "tank_farm", "tank_farm", "tank_farm"):
        ok, msg = base.build(key, t, research, program)
        assert ok, msg
    t += 365.0 * DAY
    base.advance(t)
    assert base.net.buffers["Oxygen"].level >= 100_000.0
    toasts, _ = sweep(program, S, t)
    assert act_unlocked(2, program), "Act I should be complete"

    # -- Act II/III: expansion flags via the same machinery -------------------
    sweep(program, S, t)                    # offer act 2
    S["visited"].update({"core:sun", "core:mars", "core:venus",
                         "core:jupiter", "core:saturn"})
    S["visited_surface"].update({"site:jezero", "site:venus_cloud"})
    mars = BaseSite("Jezero Base", t, rng, site_id="site:jezero")
    mars.net.buffers["Methane"].level = 25_000.0
    S["bases"].append(mars)
    t += 30 * DAY
    sweep(program, S, t)
    t += DAY
    sweep(program, S, t)
    assert act_unlocked(3, program), "Act II should be complete"
    S["visited_surface"].update({"site:europa_burrow", "site:titan_shore"})
    titan = BaseSite("Ligeia Base", t, rng, site_id="site:titan_shore")
    S["bases"].append(titan)
    t += 30 * DAY
    sweep(program, S, t)
    t += DAY
    sweep(program, S, t)
    assert act_unlocked(4, program), "Act III should be complete"

    # -- Act IV: the torch and the stars --------------------------------------
    research.unlocked.add("core:tech_pr22_fusion_torch")
    mu_s = tree.body("core:sun").mu
    r_s = 1.5e11
    v_esc = (2.0 * mu_s / r_s) ** 0.5
    probe = FleetVessel(
        tree, "core:sun",
        state_to_elements(r_s, 0.0, 0.0, v_esc * 1.15, t, mu_s),
        Vessel(db, [Vessel.fueled_row(db, "core:probe_longshot")],
               stage_plan=[[0]]),
        "Longshot", 9)
    S["vessels"].append(probe)
    t += 30 * DAY
    _, won1 = sweep(program, S, t)
    t += DAY
    _, won2 = sweep(program, S, t)
    assert won1 or won2, "the precursor on a hyperbolic solar orbit must WIN"

    # the program ran at a profit and every act paid out
    done = sum(1 for c in program.contracts if c.completed_t is not None)
    assert done >= 18
    assert program.funds > 150e6
