"""PHASE 2: crewed Moon landing acceptance + the first ISRU chain
(PSR water ice -> extractor -> electrolysis -> O2/H2 propellant)."""

import pytest

from aphelion.content.loader import default_data_dir, load_packs
from aphelion.content.validate import validate
from aphelion.sim.flight.landing import TOUCHDOWN_LIMIT, fly_landing
from aphelion.sim.habitat.lsc import DAY, oga_electrolysis
from aphelion.sim.ledger.network import LedgerNetwork, Module, Source
from aphelion.sim.vessels.vessel import Vessel

MU_MOON = 4.9028e12
R_MOON = 1.7374e6


@pytest.fixture(scope="module")
def db():
    d = load_packs(default_data_dir())
    validate(d)
    return d


def build_lander(db) -> Vessel:
    rows = [
        Vessel.fueled_row(db, "core:engine_ml111"),
        Vessel.fueled_row(db, "core:tank_ml_s"),
        Vessel.fueled_row(db, "core:payload_2t"),
    ]
    return Vessel(db, rows, stage_plan=[[0, 1, 2]], cd_a_m2=0.0)


def test_phase2_moon_landing_acceptance(db):
    """LLO-100 to the surface under the touchdown limit with margin left."""
    lander = build_lander(db)
    result = fly_landing(lander, MU_MOON, R_MOON, orbit_alt=100e3)
    assert result.landed, "\n".join(result.log)
    assert result.touchdown_speed <= TOUCHDOWN_LIMIT
    # canon indicative surface<->LLO dv ~1.9 km/s incl. margin (03 table);
    # a clean autopilot descent should spend well under that ceiling
    assert result.dv_used < 2_300.0
    assert result.propellant_left_kg > 200.0     # abort margin survives


def test_isru_chain_ice_to_propellant():
    """PSR ice -> Water -> electrolysis -> Oxygen + Hydrogen, end to end on
    the ledger: the first link of the lunar LOX economy (04)."""
    net = LedgerNetwork()
    net.add_buffer("Water", 0.0, 5_000.0)
    net.add_buffer("Oxygen", 0.0, 8_000.0)
    net.add_buffer("Hydrogen", 0.0, 1_000.0)
    net.add_buffer("Regolith", 0.0, 100_000.0)
    # icy regolith deposit: extractor pulls 0.02 kg/s of water equivalent
    net.add_source(Source("psr_ice", "Water", 0.02, remaining=20_000.0))
    net.add_module(oga_electrolysis(rate_o2_kgps=0.015, power_kw=60.0))
    net.add_module(Module("reactor", inputs={}, outputs={}, rate_kgps=0.0,
                          power_kw=-100.0))

    events = net.advance(0.0, 7.0 * DAY)

    o2 = net.buffers["Oxygen"].level
    h2 = net.buffers["Hydrogen"].level
    assert o2 > 5_000.0                      # tonnes-scale propellant week
    assert h2 == pytest.approx(o2 * 0.111 / 0.889, rel=1e-6)   # stoichiometry
    # mass conservation: extracted water == stored water + electrolyzed mass
    extracted = 20_000.0 - [s for s in net.sources][0].remaining
    accounted = net.buffers["Water"].level + (o2 + h2) * (1.0 / 0.889) * 0.889
    assert extracted == pytest.approx(net.buffers["Water"].level + o2 + h2,
                                      rel=1e-6)


def test_isru_chain_throttles_on_power_deficit():
    net = LedgerNetwork()
    net.add_buffer("Water", 1_000.0, 5_000.0)
    net.add_buffer("Oxygen", 0.0, 8_000.0)
    net.add_buffer("Hydrogen", 0.0, 1_000.0)
    net.add_module(oga_electrolysis(rate_o2_kgps=0.015, power_kw=60.0))
    net.add_module(Module("small_panel", inputs={}, outputs={}, rate_kgps=0.0,
                          power_kw=-15.0))
    _, rates, f_power = net.solve_rates()
    assert f_power == pytest.approx(0.25)
    assert rates["Oxygen"] == pytest.approx(0.015 * 0.25)
