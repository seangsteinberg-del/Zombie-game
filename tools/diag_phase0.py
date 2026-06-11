import math
from aphelion.core.units import AU, SECONDS_PER_DAY as DAY
from aphelion.sim.orbits.ephemeris import load_solar_system
import aphelion.tests.test_phase0_acceptance as acc

db, tree = load_solar_system()
t_dep, vinf, dv_pred, t_tr_pred, r1, r2, phi_asym = acc._plan_window(tree, 0.0)
dv, legs = acc._fly_tmi(tree, t_dep, vinf, phi_asym)
helio = legs[1]
print(f"t_dep = {t_dep/DAY:.2f} d   vinf = {vinf:.1f}   dv = {dv:.1f}")
print(f"r1 = {r1/AU:.4f} AU   r2(target) = {r2/AU:.4f} AU")
print(f"helio peri = {helio.elements.periapsis/AU:.4f} AU  apo = {helio.elements.apoapsis/AU:.4f} AU")
print(f"apo/r2 = {helio.elements.apoapsis/r2:.4f}")
per = helio.elements.period
t_apo = helio.elements.tau + per / 2
while t_apo < helio.t_start:
    t_apo += per
print(f"transfer = {(t_apo - t_dep)/DAY:.2f} d  (pred {t_tr_pred/DAY:.2f})")
print("legs:", [(l.frame_id, l.end_reason) for l in legs])
