"""PHASE 5: entry/aerocapture physics, radiation doses, Venus aerostat and
Titan statics — every number pinned against the canon tables."""

import math

import pytest

from aphelion.sim.environment.buoyancy import (
    titan_air_density,
    titan_dirigible_lift_kg_m3,
    titan_submarine_net_buoyancy_n,
    titan_wing_lift_n,
    venus_envelope_volume_m3,
    venus_lift_kg_m3,
)
from aphelion.sim.flight.entry import (
    allen_eggers_peak_g,
    fly_entry,
    radiative_factor,
    stagnation_heating_w_m2,
)
from aphelion.sim.habitat.dose import (
    CrewDose,
    attenuation,
    dose_rate_msv_day,
)

MU_MARS = 4.282_837e13
R_MARS = 3.3895e6
MU_EARTH = 3.986_004_418e14
R_EARTH = 6.371e6


# ---- entry physics (01 §3.11 pinned) -----------------------------------------

def test_allen_eggers_canon_example():
    """LEO entry v=7.8 km/s, gamma=2 deg, H=8.5 km -> ~4.7 g."""
    g = allen_eggers_peak_g(7_800.0, math.radians(2.0), 8_500.0)
    assert g == pytest.approx(4.7, abs=0.3)


def test_radiative_factor_anchors():
    """Calibrated: lunar return (~11 km/s) ~1.45x; Stardust (~12.8 km/s)
    ~2.7x; hard cap 8."""
    assert radiative_factor(7_800.0) == 1.0
    assert radiative_factor(11_000.0) == pytest.approx(1.44, abs=0.05)
    assert radiative_factor(12_800.0) == pytest.approx(2.6, abs=0.2)
    assert radiative_factor(20_000.0) == 8.0


def test_mars_aerocapture_canon_band():
    """Mars arrival at the canon 5.6 km/s entry-interface speed: the
    aerocapture corridor the sim discovered is ~1 degree wide (8 deg skips
    out, 9 captures, 10 lands) — exactly why 01 §3.11 specs corridor rules."""
    r0 = R_MARS + 125e3
    res = fly_entry("core:mars", MU_MARS, R_MARS,
                    r0=r0, v0=5_600.0, gamma0_rad=math.radians(9.0),
                    beta_kg_m2=300.0)
    assert res.outcome == "captured", res.log
    assert res.exit_apoapsis_m < 12.0 * R_MARS    # bound orbit, workable
    assert res.peak_g < 6.0                        # crew-survivable pass
    # corridor edges
    skip = fly_entry("core:mars", MU_MARS, R_MARS, r0=r0, v0=5_600.0,
                     gamma0_rad=math.radians(7.0), beta_kg_m2=300.0)
    assert skip.outcome == "escaped"
    dig = fly_entry("core:mars", MU_MARS, R_MARS, r0=r0, v0=5_600.0,
                    gamma0_rad=math.radians(11.0), beta_kg_m2=300.0)
    assert dig.outcome == "landed"


def test_mars_steep_entry_lands():
    res = fly_entry("core:mars", MU_MARS, R_MARS,
                    r0=R_MARS + 125e3, v0=5_600.0,
                    gamma0_rad=math.radians(25.0), beta_kg_m2=120.0)
    assert res.outcome == "landed"
    assert res.peak_g > 4.0                        # steep = punishing


def test_heating_scales_with_v_cubed():
    q1 = stagnation_heating_w_m2("core:earth", 1e-4, 6_000.0, 2.0)
    q2 = stagnation_heating_w_m2("core:earth", 1e-4, 3_000.0, 2.0)
    assert q1 / q2 == pytest.approx(8.0, rel=1e-9)


# ---- radiation (03/08 pinned) --------------------------------------------------

def test_dose_rates_canon():
    assert dose_rate_msv_day("core:moon") == pytest.approx(1.37)
    assert dose_rate_msv_day("core:europa") == pytest.approx(5_400.0)
    assert dose_rate_msv_day("deep_space") == pytest.approx(1.8)


def test_shielding_two_channel_law():
    # GCR law (08 §4.2): f_GCR = 0.30 + 0.70·exp(−σ/30)
    assert attenuation(22.0) == pytest.approx(
        0.30 + 0.70 * 2.718281828 ** (-22.0 / 30.0), rel=1e-6)
    # heavy shielding approaches the 0.30 secondary floor
    assert attenuation(200.0) == pytest.approx(0.30, abs=2e-3)
    # ...and the floor itself decays past 1,000 g/cm2, e-fold 1,000
    # (DECISIONS A3): Titan's 10,900 g/cm2 column reads near-zero
    assert attenuation(10_900.0) < 1e-4
    # storm-shelter worked example (08 §4.2): σ=35 water walls
    assert attenuation(35.0) == pytest.approx(0.52, abs=0.01)
    assert attenuation(35.0, channel="spe") == pytest.approx(0.054,
                                                             abs=0.005)


def test_europa_surface_is_lethal_fast():
    """5.4 Sv/day unshielded: a career dose (600 mSv) in under 3 hours."""
    crew = CrewDose()
    crew.accrue("core:europa", days=0.2)
    assert crew.over_limit


def test_europa_ice_burrow_works():
    """Europa's field is trapped electrons/protons — SPE-channel physics:
    a metre-plus of ice overburden ends it (the GCR share underneath is
    Earth-orbit-class). Burrow or die, but burrowing WORKS."""
    raw = dose_rate_msv_day("core:europa")
    assert raw == pytest.approx(5_400.0)
    burrow = dose_rate_msv_day("core:europa", areal_g_cm2=140.0,
                               material="water")
    assert burrow < 1.0               # ~1.5 m of ice: storm over


# ---- Venus aerostat (07 B-8 / HAVOC) -------------------------------------------

def test_venus_breathable_air_floats():
    lift = venus_lift_kg_m3(52_500.0)
    assert lift > 0.25                # the HAVOC trick is real
    # a 60 t gondola floats on a feasible envelope (tens of thousands m3,
    # Hindenburg was 200,000 m3)
    vol = venus_envelope_volume_m3(60_000.0, 52_500.0)
    assert 50_000.0 < vol < 350_000.0


def test_venus_lift_dies_with_altitude():
    assert venus_lift_kg_m3(52_500.0) > venus_lift_kg_m3(62_000.0)


# ---- Titan (10 / NASA Titan Sub) ------------------------------------------------

def test_titan_air_is_dense():
    assert titan_air_density() == pytest.approx(5.28, rel=0.06)   # canon 5.28


def test_titan_human_powered_flight_is_real():
    """DECISIONS C20: a fit human (~120 kg with wings) at 8 m/s on 12 m2 of
    wing generates more lift than Titan weight."""
    weight_n = 120.0 * 1.35
    lift_n = titan_wing_lift_n(12.0, 8.0, cl=1.0)
    assert lift_n > weight_n * 1.5


def test_titan_dirigible_lift():
    """Canon 4.9 kg/m³: AMBIENT-temperature H2 in cold dense N2 (warm
    gas is the Montgolfière mechanic, 10 §4.2 reconciliation)."""
    assert titan_dirigible_lift_kg_m3("h2") == pytest.approx(4.9,
                                                             abs=0.1)


def test_titan_submarine_must_be_dense():
    """Canon mean sea 550 kg/m3 (per-sea 520/580/600, 10 §2.7): a 10 m3
    hull massing 6 t SINKS — the NASA study's central design problem."""
    assert titan_submarine_net_buoyancy_n(10.0, 6_000.0) < 0.0
    # neutral trim needs mass ~ 5.5 t for 10 m3 at the canon mean
    assert abs(titan_submarine_net_buoyancy_n(10.0, 5_500.0)) < 1.0
    # ethane-rich Kraken carries more than methane-rich Ligeia
    assert titan_submarine_net_buoyancy_n(10.0, 5_500.0, sea="kraken") \
        > titan_submarine_net_buoyancy_n(10.0, 5_500.0, sea="ligeia")
