"""Generate data/core/bodies/*.json from the 03-solar-system.md canon tables
(§4.1 master data, §4.2 heliocentric elements, §4.3 satellite elements).

Run: python tools/gen_bodies.py
Regenerates the whole pack deterministically; t_peri is machine-computed
from M0 (tau = -M0_rad / n, epoch 2049-01-01) so no hand-derived numbers
can drift. SOI is Laplace-computed with the 01 §3.4 floor rule; bodies with
surface gravity < 0.01 m/s^2 are dock-mode (soi = 0, table 4.1 note 1).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

DAY = 86_400.0
HOUR = 3_600.0

# name, parent, GM [m^3/s^2], R [m], rotation [s] (negative = retrograde,
# None = synchronous: use orbital period), a [m], e, varpi [deg], M0 [deg], sense
ROWS = [
    ("sun",      None,      1.32712440018e20, 6.957e8,  25.4 * DAY,   None,       None,   None,  None,  1),
    # -- heliocentric (03 §4.2) --
    ("mercury",  "sun",     2.2032e13,   2.4397e6,  58.646 * DAY, 5.791e10,   0.2056, 77.5,  337.4, 1),
    ("venus",    "sun",     3.24859e14,  6.0518e6, -243.02 * DAY, 1.0821e11,  0.0068, 131.5, 284.6, 1),
    ("earth",    "sun",     3.986004418e14, 6.371e6, 23.934 * HOUR, 1.495978707e11, 0.0167, 102.9, 357.5, 1),
    ("mars",     "sun",     4.282837e13, 3.3895e6,  24.623 * HOUR, 2.2794e11,  0.0934, 336.0, 38.1,  1),
    ("vesta",    "sun",     1.73e10,     2.627e5,   5.342 * HOUR,  3.533e11,   0.089,  255.0, 169.0, 1),
    ("ceres",    "sun",     6.26e10,     4.697e5,   9.07 * HOUR,   4.138e11,   0.076,  153.9, 264.0, 1),
    ("psyche",   "sun",     1.53e9,      1.11e5,    4.196 * HOUR,  4.374e11,   0.134,  19.3,  302.0, 1),
    ("hygiea",   "sun",     5.83e9,      2.17e5,    13.83 * HOUR,  4.696e11,   0.112,  235.5, 47.0,  1),
    ("jupiter",  "sun",     1.26686534e17, 6.9911e7, 9.925 * HOUR, 7.786e11,   0.0489, 14.8,  66.7,  1),
    ("saturn",   "sun",     3.79312e16,  5.8232e7,  10.66 * HOUR,  1.4335e12,  0.0565, 92.4,  196.4, 1),
    ("uranus",   "sun",     5.7939e15,   2.5362e7, -17.24 * HOUR,  2.8707e12,  0.0472, 171.0, 352.2, 1),
    ("neptune",  "sun",     6.8365e15,   2.4622e7,  16.11 * HOUR,  4.4984e12,  0.0086, 45.0,  7.0,   1),
    ("pluto",    "sun",     8.696e11,    1.1883e6,  6.387 * DAY,   5.9064e12,  0.2488, 224.1, 86.0,  1),
    ("eris",     "sun",     1.108e12,    1.163e6,   15.8 * DAY,    1.0157e13,  0.44,   187.6, 205.0, 1),
    ("arrokoth", "sun",     3.0e4,       9.0e3,     15.9 * HOUR,   6.669e12,   0.042,  333.3, 316.0, 1),
    ("eros",     "sun",     4.46e5,      8.4e3,     5.27 * HOUR,   2.181e11,   0.223,  123.1, 110.0, 1),
    ("bennu",    "sun",     4.9,         2.45e2,    4.296 * HOUR,  1.685e11,   0.2037, 68.3,  102.0, 1),
    ("ryugu",    "sun",     3.0e1,       4.48e2,    7.63 * HOUR,   1.780e11,   0.1902, 103.0, 21.0,  1),
    ("itokawa",  "sun",     2.1,         1.65e2,    12.13 * HOUR,  1.981e11,   0.280,  231.9, 297.0, 1),
    ("apophis",  "sun",     4.0,         1.70e2,    30.6 * HOUR,   1.646e11,   0.19,   330.8, 213.0, 1),
    ("67p",      "sun",     6.7e2,       2.0e3,     12.40 * HOUR,  5.180e11,   0.641,  62.9,  84.0,  1),
    ("halley",   "sun",     1.5e4,       5.5e3,     52.8 * HOUR,   2.667e12,   0.967,  169.8, 299.9, -1),
    # -- satellites (03 §4.3); rotation None = synchronous --
    ("moon",     "earth",   4.9028e12,   1.7374e6,  None, 3.844e8,    0.0549, 318.2, 135.0, 1),
    ("phobos",   "mars",    7.11e5,      1.11e4,    None, 9.376e6,    0.0151, 150.1, 40.0,  1),
    ("deimos",   "mars",    9.8e4,       6.2e3,     None, 2.3463e7,   0.0003, 0.0,   200.0, 1),
    ("io",       "jupiter", 5.9599e12,   1.8216e6,  None, 4.218e8,    0.0041, 0.0,   310.0, 1),
    ("europa",   "jupiter", 3.2027e12,   1.5608e6,  None, 6.711e8,    0.0094, 0.0,   120.0, 1),
    ("ganymede", "jupiter", 9.8878e12,   2.6341e6,  None, 1.0704e9,   0.0013, 0.0,   250.0, 1),
    ("callisto", "jupiter", 7.1793e12,   2.4103e6,  None, 1.8827e9,   0.0074, 0.0,   85.0,  1),
    ("enceladus","saturn",  7.21e9,      2.521e5,   None, 2.37948e8,  0.0047, 0.0,   15.0,  1),
    ("titan",    "saturn",  8.9781e12,   2.5747e6,  None, 1.22187e9,  0.0288, 185.7, 160.0, 1),
    ("miranda",  "uranus",  4.4e9,       2.358e5,   None, 1.2939e8,   0.0013, 0.0,   295.0, 1),
    ("titania",  "uranus",  2.283e11,    7.889e5,   None, 4.3591e8,   0.0011, 0.0,   70.0,  1),
    ("oberon",   "uranus",  1.924e11,    7.614e5,   None, 5.8352e8,   0.0014, 0.0,   225.0, 1),
    ("triton",   "neptune", 1.428e12,    1.3534e6,  None, 3.54759e8,  0.000016, 0.0, 330.0, -1),
    ("charon",   "pluto",   1.059e11,    6.06e5,    None, 1.9596e7,   0.0002, 0.0,   0.0,   1),
]

SOI_FLOOR_FACTOR = 1.5
DOCK_GRAVITY = 0.01     # m/s^2 (03 §4.1 note 1)


def main() -> None:
    out_dir = Path(__file__).resolve().parent.parent / "data" / "core" / "bodies"
    out_dir.mkdir(parents=True, exist_ok=True)
    mu_by_name = {row[0]: row[2] for row in ROWS}

    count = 0
    for name, parent, mu, radius, rot, a, e, varpi_deg, m0_deg, sense in ROWS:
        body: dict = {
            "id": f"core:{name}",
            "parent": f"core:{parent}" if parent else None,
            "mu_m3s2": mu,
            "radius_m": radius,
        }
        if parent is None:
            body["rotation_period_s"] = rot
            body["soi_m"] = None       # infinite (root)
            body["elements"] = None
        else:
            mu_parent = mu_by_name[parent]
            n = math.sqrt(mu_parent / a ** 3)
            period = 2.0 * math.pi / n
            body["rotation_period_s"] = rot if rot is not None else period
            body["elements"] = {
                "a_m": a,
                "e": e,
                "lon_peri_rad": round(math.radians(varpi_deg), 10),
                "t_peri_s": round(-math.radians(m0_deg) / n, 6),
                "sense": sense,
            }
            g_surface = mu / radius ** 2
            soi = a * (mu / mu_parent) ** 0.4
            if g_surface < DOCK_GRAVITY or soi < SOI_FLOOR_FACTOR * radius:
                soi = 0.0   # dock mode / floor rule
            body["soi_m"] = soi
        path = out_dir / f"{name}.json"
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(body, fh, indent=1)
            fh.write("\n")
        count += 1
    print(f"wrote {count} bodies to {out_dir}")


if __name__ == "__main__":
    main()
