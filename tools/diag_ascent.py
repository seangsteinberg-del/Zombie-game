from aphelion.content.loader import default_data_dir, load_packs
from aphelion.content.validate import validate
from aphelion.sim.flight.ascent import AscentParams, fly_ascent
from aphelion.tests.test_phase1_ascent import build_two_stage, MU_EARTH, R_EARTH, EARTH_DAY

db = load_packs(default_data_dir())
validate(db)
v = build_two_stage(db)
r = fly_ascent(v, "core:earth", MU_EARTH, R_EARTH, EARTH_DAY, AscentParams())
print("reached:", r.reached_orbit)
print(f"dv_int {r.dv_integrated:.0f}  grav {r.dv_gravity:.0f}  drag {r.dv_drag:.0f}"
      f"  steer {r.dv_steering:.0f}  circ {r.dv_circ:.0f}")
print(f"orbit_speed {r.orbit_speed:.0f}  rot_credit {r.rotation_credit:.0f}"
      f"  residual {r.identity_residual:.0f}")
print(f"peri {r.periapsis_m/1e3:.1f} km  apo {r.apoapsis_m/1e3:.1f} km  t_meco {r.t_meco:.1f} s")
for line in r.log:
    print(" ", line)
