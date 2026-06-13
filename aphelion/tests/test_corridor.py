"""Chunk O: aerocapture/entry corridor advisor pinned against 01 §1.6
(EDL/aerocapture corridor rules) and the fly_entry band already pinned in
test_phase5_environments (Mars 5.6 km/s, beta 300: 7 deg skips, 9 captures,
11 lands). Every headline number from the spec's worked examples is pinned
here with pytest.approx."""

import math

import pytest

from aphelion.sim.flight.corridor import (
    BARE_HEAT_W_M2,
    CAPSULE_HEAT_W_M2,
    advise,
    ballistic_range,
    corridor,
    local_scale_height,
    tps_required,
    vacuum_periapsis_alt_m,
)
from aphelion.sim.flight.entry import (
    allen_eggers_peak_g,
    fly_entry,
    radiative_factor,
    stagnation_heating_w_m2,
)

MU_MARS = 4.282_837e13
R_MARS = 3.3895e6
MU_EARTH = 3.986_004_418e14
R_EARTH = 6.371e6


@pytest.fixture(scope="module")
def mars_rep():
    """Canon Mars arrival: 5.6 km/s at the 125 km interface, beta 300."""
    return corridor("core:mars", MU_MARS, R_MARS, 5_600.0, 300.0)


@pytest.fixture(scope="module")
def earth_rep():
    """Canon LEO return: 7.8 km/s at the 140 km interface, beta 300."""
    return corridor("core:earth", MU_EARTH, R_EARTH, 7_800.0, 300.0)


# ---- (a) the pinned Mars corridor, rediscovered by bisection -----------------

def test_mars_corridor_reproduces_pinned_band(mars_rep):
    """test_phase5_environments pins outcomes at 7 (skip) / 9 (capture) /
    11 (land); bisection must land the edges inside those pins, within
    0.3 deg of the sim's true boundaries (8.83 / 9.42)."""
    assert mars_rep.gamma_skip_limit == pytest.approx(8.83, abs=0.3)
    assert mars_rep.gamma_land_limit == pytest.approx(9.42, abs=0.3)
    # consistency with the phase-5 outcome pins
    assert mars_rep.gamma_skip_limit > 7.0
    assert mars_rep.gamma_capture_lo < 9.0 < mars_rep.gamma_capture_hi
    assert mars_rep.gamma_land_limit < 11.0
    # edges are the same boundaries seen from the capture side
    assert mars_rep.gamma_capture_lo == mars_rep.gamma_skip_limit
    assert mars_rep.gamma_capture_hi == mars_rep.gamma_land_limit


def test_mars_corridor_width_headline(mars_rep):
    """(b) The spec's headline fact: the Mars corridor at 5.6 km/s is about
    a degree wide (phase-5 docstring: '~1 degree', quoted 8->10 at integer
    sampling, i.e. <= 2 deg). The hard bisected capture band is 0.59 deg."""
    assert mars_rep.width_deg == pytest.approx(0.59, abs=0.3)
    assert 0.3 < mars_rep.width_deg < 2.0


def test_mars_center_pass_quality(mars_rep):
    """Corridor-center pass: gentle (~1 g, crew-survivable per phase-5's
    < 6 g pin) and exits to a workable bound orbit (< 12 R apoapsis)."""
    assert mars_rep.gamma_center == pytest.approx(9.12, abs=0.3)
    assert mars_rep.peak_g == pytest.approx(1.0, abs=0.4)
    assert mars_rep.peak_g < 6.0
    assert mars_rep.exit_apoapsis_m == pytest.approx(4.4 * R_MARS,
                                                     rel=0.35)
    assert mars_rep.exit_apoapsis_m < 12.0 * R_MARS
    # heating at the center is mild — far below even the bare rating
    assert mars_rep.peak_heating_w_m2 == pytest.approx(0.28e6, rel=0.2)
    assert mars_rep.peak_heating_w_m2 < BARE_HEAT_W_M2


def test_mars_hp_window_spec_rule(mars_rep):
    """(e) §1.6: 'periapsis-altitude window h_p* ± Δh, Δh ≈ 0.5-1.0 ×
    H_local (a few km)'. The gamma band maps through the vacuum conic to
    h_p 47.8-57.0 km; half-width 4.6 km ≈ 0.53 × H_local(52 km)."""
    assert mars_rep.hp_window_lo_m == pytest.approx(47.8e3, abs=3e3)
    assert mars_rep.hp_window_hi_m == pytest.approx(57.0e3, abs=3e3)
    half = 0.5 * (mars_rep.hp_window_hi_m - mars_rep.hp_window_lo_m)
    h_center = 0.5 * (mars_rep.hp_window_hi_m + mars_rep.hp_window_lo_m)
    ratio = half / local_scale_height("core:mars", h_center)
    assert 0.25 < ratio < 1.0
    # vacuum-conic helper sanity: steeper gamma -> lower periapsis
    r0 = R_MARS + 125e3
    assert (vacuum_periapsis_alt_m(MU_MARS, R_MARS, r0, 5_600.0,
                                   math.radians(10.0))
            < vacuum_periapsis_alt_m(MU_MARS, R_MARS, r0, 5_600.0,
                                     math.radians(8.0)))


# ---- the advisor one-liner ----------------------------------------------------

def test_advise_one_liner_formats(mars_rep):
    lo, hi = mars_rep.gamma_capture_lo, mars_rep.gamma_capture_hi
    band = f"CAPTURE corridor {lo:.1f}-{hi:.1f} deg"

    line, margin = advise(mars_rep, 8.5)          # 0.33 deg shallow of lo
    assert line == f"{band}, you are 0.3 deg shallow"
    assert margin == pytest.approx(-(lo - 8.5), abs=1e-9)
    assert margin == pytest.approx(-0.33, abs=0.05)

    line, margin = advise(mars_rep, 10.0)         # steep of hi: will land
    assert line == f"{band}, you are 0.6 deg steep"
    assert margin == pytest.approx(-(10.0 - hi), abs=1e-9)

    line, margin = advise(mars_rep, mars_rep.gamma_center)
    assert line.startswith(f"{band}, you are GO")
    assert margin == pytest.approx(0.5 * mars_rep.width_deg, abs=1e-9)
    assert margin > 0.0


# ---- (c) Earth LEO return ------------------------------------------------------

def test_earth_leo_return_everything_lands(earth_rep):
    """7.8 km/s is bound (≈ v_circ at 140 km): drag only removes energy, so
    skip-out is impossible — and at beta 300 every gamma from the 0.5 deg
    search floor through 7 deg lands in one pass (land limit <= 1.5 deg)."""
    assert math.isnan(earth_rep.gamma_skip_limit)         # no skip-out, ever
    assert not earth_rep.has_capture_band                 # no exit either
    assert earth_rep.gamma_land_limit <= 1.5
    r0 = R_EARTH + 140e3
    for g_deg in (1.5, 2.0, 4.0, 7.0):
        res = fly_entry("core:earth", MU_EARTH, R_EARTH, r0=r0, v0=7_800.0,
                        gamma0_rad=math.radians(g_deg), beta_kg_m2=300.0)
        assert res.outcome == "landed", g_deg

    line, margin = advise(earth_rep, 2.0)
    assert line.startswith("LAND corridor")
    assert "GO" in line
    assert margin == pytest.approx(2.0 - earth_rep.gamma_land_limit,
                                   abs=1e-9)
    line, margin = advise(earth_rep, 0.2)
    assert "shallow" in line and margin < 0.0


def test_earth_allen_eggers_pin():
    """(e) §1.6 worked example: LEO entry 7.8 km/s @ gamma 2 deg, H 8.5 km
    -> ≈ 4.7 g (the planner sanity model, pinned as in phase 5)."""
    g = allen_eggers_peak_g(7_800.0, math.radians(2.0), 8_500.0)
    assert g == pytest.approx(4.7, abs=0.3)


# ---- (d) beta monotonicity ----------------------------------------------------

def test_higher_beta_shifts_corridor_monotonically(mars_rep):
    """A higher ballistic coefficient sheds less energy per pass
    (decel = rho v^2 / 2beta), so the corridor must dig monotonically
    deeper/steeper in gamma as beta rises — equivalently, the §1.6
    periapsis-altitude window walks lower into the atmosphere. Measured:
    skip 8.44 / 8.83 / 9.21 deg at beta 150 / 300 / 600."""
    light = corridor("core:mars", MU_MARS, R_MARS, 5_600.0, 150.0)
    heavy = corridor("core:mars", MU_MARS, R_MARS, 5_600.0, 600.0)
    assert (light.gamma_skip_limit < mars_rep.gamma_skip_limit
            < heavy.gamma_skip_limit)
    assert (light.gamma_land_limit < mars_rep.gamma_land_limit
            < heavy.gamma_land_limit)
    assert light.gamma_skip_limit == pytest.approx(8.44, abs=0.3)
    assert heavy.gamma_skip_limit == pytest.approx(9.21, abs=0.3)
    # h_p window walks DOWN with beta (deeper periapsis needed)
    assert heavy.hp_window_lo_m < mars_rep.hp_window_lo_m


# ---- TPS sizing ----------------------------------------------------------------

def test_tps_classes_match_spec_speed_table():
    """(e) §1.6 'entry-interface speed -> TPS class' table, mapped onto the
    shipped main.py ratings (2.5e6 ablative / 0.9e6 bare, main.py:70-71):
    Mars 5.5-7 km/s is mild; LEO return needs the ablative-protected stack;
    Venus 10-11 km/s direct (and 11 km/s lunar return at the steep default)
    is PICA-class — beyond anything the game ships."""
    mars = tps_required("core:mars", 5_600.0, 300.0)
    assert mars.tps_class == "bare"
    assert mars.peak_heating_w_m2 == pytest.approx(0.558e6, rel=0.02)
    assert mars.rating_w_m2 == BARE_HEAT_W_M2

    leo = tps_required("core:earth", 7_800.0, 300.0)
    assert leo.tps_class == "ablator"
    assert leo.peak_heating_w_m2 == pytest.approx(1.787e6, rel=0.02)
    assert leo.rating_w_m2 == CAPSULE_HEAT_W_M2

    lunar = tps_required("core:earth", 11_000.0, 300.0)
    assert lunar.tps_class == "beyond"
    assert math.isinf(lunar.rating_w_m2)

    venus = tps_required("core:venus", 10_600.0, 300.0)   # V3 direct entry
    assert venus.tps_class == "beyond"

    titan = tps_required("core:titan", 7_000.0, 300.0)    # teaching case
    assert titan.tps_class != "beyond"                    # huge H = gentle


def test_tps_closed_form_tracks_integrator():
    """The Allen-Eggers-point estimate must track fly_entry's integrated
    peak heating at the same gamma: near-exact for the shallow Earth case,
    conservative (never optimistic by > 30%) for the curved Mars case."""
    res_e = fly_entry("core:earth", MU_EARTH, R_EARTH, r0=R_EARTH + 140e3,
                      v0=7_800.0, gamma0_rad=math.radians(7.0),
                      beta_kg_m2=300.0)
    est_e = tps_required("core:earth", 7_800.0, 300.0, gamma_deg=7.0)
    assert 0.7 < est_e.peak_heating_w_m2 / res_e.peak_heating_w_m2 < 2.0

    res_m = fly_entry("core:mars", MU_MARS, R_MARS, r0=R_MARS + 125e3,
                      v0=5_600.0, gamma0_rad=math.radians(10.0),
                      beta_kg_m2=300.0)
    est_m = tps_required("core:mars", 5_600.0, 300.0, gamma_deg=10.0)
    assert 0.7 < est_m.peak_heating_w_m2 / res_m.peak_heating_w_m2 < 2.0


def test_stardust_validation_anchor():
    """(e) §1.6 anchor: Stardust v=12.9 km/s, r_n=0.229 m, rho≈2e-4 kg/m3
    -> q_conv ≈ 1,100 W/cm2 (flown ~1,200). stagnation_heating_w_m2 is
    f_rad-augmented, so divide it back out for the convective-only pin."""
    q_conv = (stagnation_heating_w_m2("core:earth", 2e-4, 12_900.0, 0.229)
              / radiative_factor(12_900.0))
    assert q_conv == pytest.approx(1.1e7, rel=0.05)       # W/m2 = 1,100 W/cm2


# ---- downrange -----------------------------------------------------------------

def test_ballistic_range_mars_pins():
    """Landing-site prediction: monotone — steeper entries stop shorter.
    Values pinned from the deterministic integrator (km-scale)."""
    r0 = R_MARS + 125e3
    d = {g: ballistic_range("core:mars", MU_MARS, R_MARS, r0, 5_600.0,
                            math.radians(g), 300.0)
         for g in (9.5, 11.0, 15.0, 25.0)}
    assert d[9.5] == pytest.approx(2_377e3, rel=0.05)
    assert d[11.0] == pytest.approx(974e3, rel=0.05)
    assert d[15.0] == pytest.approx(557e3, rel=0.05)
    assert d[25.0] == pytest.approx(281e3, rel=0.05)
    assert d[9.5] > d[11.0] > d[15.0] > d[25.0]
    # a skip pass has no landing site
    assert math.isinf(ballistic_range("core:mars", MU_MARS, R_MARS, r0,
                                      5_600.0, math.radians(7.0), 300.0))


def test_ballistic_range_earth_leo():
    """LEO return at gamma 2 deg glides ~2,700 km downrange (ballistic)."""
    d = ballistic_range("core:earth", MU_EARTH, R_EARTH, R_EARTH + 140e3,
                        7_800.0, math.radians(2.0), 300.0)
    assert d == pytest.approx(2_659e3, rel=0.05)


# ---- guards --------------------------------------------------------------------

def test_airless_body_has_no_corridor():
    with pytest.raises(ValueError):
        corridor("core:moon", 4.9048695e12, 1.7374e6, 2_400.0, 300.0)
    with pytest.raises(ValueError):
        tps_required("core:moon", 2_400.0, 300.0)
    with pytest.raises(ValueError):
        local_scale_height("core:moon", 10e3)
