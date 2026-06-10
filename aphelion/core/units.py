"""SI constants (13 §3.2 core/units.py). All sim math is SI float64."""

G0 = 9.80665                  # standard gravity, m/s^2 (Isp <-> exhaust velocity)
C_LIGHT = 299_792_458.0       # m/s (comms RTT, 92-16)
AU = 1.495_978_707e11         # m (IAU 2012 exact)

SECONDS_PER_DAY = 86_400.0
SECONDS_PER_YEAR = 365.25 * SECONDS_PER_DAY   # Julian year

SIM_DT = 0.02                 # s, fixed timestep at 1x for powered/atmospheric flight (01 §3.5, binding)
