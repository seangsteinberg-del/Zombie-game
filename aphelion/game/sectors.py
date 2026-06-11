"""Sector runtime (03 S-7): land ANYWHERE — every body's surface is
partitioned into named sectors loaded from the content pack, and any
landable sector synthesizes a site dict compatible with the descent /
base-founding flows that the original five hand-picked SITES used.

Landing classes (S-7b): A airless dock/anchor · B airless rockets-only ·
C thin atmo (shield + retropropulsion) · D thick benign (chutes) ·
E extreme (Venus surface, pre-T3 probes only) · F no surface.
"""

from __future__ import annotations

import math

from aphelion.content.loader import ContentDB

# per-body surface ops: ascent dv to low parking orbit [m/s] (§1.1 column),
# propulsive landing dv (aero worlds pay only the terminal phase), solar
# distance d [AU] and solar-day length [s]. None day_s = use PEL/PSR rules.
DAY = 86_400.0
BODY_OPS: dict[str, dict] = {
    "core:mercury": {"asc": 3_200.0, "land": 3_200.0, "d": 0.387,
                     "day_s": 176.0 * DAY},
    "core:venus": {"asc": 8_000.0, "land": 300.0, "d": 0.723,
                   "day_s": 4.0 * DAY},      # cloud deck super-rotation
    "core:earth": {"asc": 9_400.0, "land": 500.0, "d": 1.0, "day_s": DAY},
    "core:moon": {"asc": 1_900.0, "land": 1_900.0, "d": 1.0,
                  "day_s": 29.53 * DAY},
    "core:mars": {"asc": 4_100.0, "land": 1_000.0, "d": 1.524,
                  "day_s": 88_775.0},
    "core:phobos": {"asc": 10.0, "land": 10.0, "d": 1.524,
                    "day_s": 7.654 * 3_600.0},
    "core:deimos": {"asc": 8.0, "land": 8.0, "d": 1.524,
                    "day_s": 30.31 * 3_600.0},
    "core:ceres": {"asc": 370.0, "land": 370.0, "d": 2.766,
                   "day_s": 9.07 * 3_600.0},
    "core:vesta": {"asc": 270.0, "land": 270.0, "d": 2.362,
                   "day_s": 5.342 * 3_600.0},
    "core:psyche": {"asc": 140.0, "land": 140.0, "d": 2.924,
                    "day_s": 4.196 * 3_600.0},
    "core:hygiea": {"asc": 180.0, "land": 180.0, "d": 3.139,
                    "day_s": 13.83 * 3_600.0},
    "core:io": {"asc": 2_000.0, "land": 2_000.0, "d": 5.204,
                "day_s": 1.769 * DAY},
    "core:europa": {"asc": 1_450.0, "land": 1_500.0, "d": 5.204,
                    "day_s": 3.551 * DAY},
    "core:ganymede": {"asc": 2_000.0, "land": 2_000.0, "d": 5.204,
                      "day_s": 7.155 * DAY},
    "core:callisto": {"asc": 1_800.0, "land": 1_800.0, "d": 5.204,
                      "day_s": 16.689 * DAY},
    "core:titan": {"asc": 2_400.0, "land": 350.0, "d": 9.583,
                   "day_s": 15.945 * DAY},
    "core:enceladus": {"asc": 180.0, "land": 180.0, "d": 9.583,
                       "day_s": 1.370 * DAY},
    "core:miranda": {"asc": 150.0, "land": 150.0, "d": 19.19,
                     "day_s": 1.413 * DAY},
    "core:titania": {"asc": 550.0, "land": 550.0, "d": 19.19,
                     "day_s": 8.706 * DAY},
    "core:oberon": {"asc": 550.0, "land": 550.0, "d": 19.19,
                    "day_s": 13.46 * DAY},
    "core:triton": {"asc": 1_000.0, "land": 1_000.0, "d": 30.07,
                    "day_s": 5.877 * DAY},
    "core:pluto": {"asc": 850.0, "land": 850.0, "d": 39.48,
                   "day_s": 6.387 * DAY},
    "core:charon": {"asc": 420.0, "land": 420.0, "d": 39.48,
                    "day_s": 6.387 * DAY},
    "core:eris": {"asc": 950.0, "land": 950.0, "d": 67.9,
                  "day_s": 15.8 * DAY},
    "core:bennu": {"asc": 5.0, "land": 5.0, "d": 1.126,
                   "day_s": 4.296 * 3_600.0},
    "core:ryugu": {"asc": 5.0, "land": 5.0, "d": 1.190,
                   "day_s": 7.63 * 3_600.0},
    "core:itokawa": {"asc": 5.0, "land": 5.0, "d": 1.324,
                     "day_s": 12.13 * 3_600.0},
    "core:eros": {"asc": 10.0, "land": 10.0, "d": 1.458,
                  "day_s": 5.27 * 3_600.0},
    "core:apophis": {"asc": 5.0, "land": 5.0, "d": 1.10,
                     "day_s": 30.6 * 3_600.0},
    "core:67p": {"asc": 5.0, "land": 5.0, "d": 3.463,
                 "day_s": 12.40 * 3_600.0},
    "core:halley": {"asc": 5.0, "land": 5.0, "d": 17.83,
                    "day_s": 52.8 * 3_600.0},
    "core:arrokoth": {"asc": 5.0, "land": 5.0, "d": 44.58,
                      "day_s": 15.9 * 3_600.0},
}

# EDL touchdown dispersion sigma by landing class [km] (S-7b)
EDL_SIGMA_KM = {"A": 0.05, "B": 0.2, "C": 5.0, "D": 20.0, "E": 25.0}

# legacy hand-picked sites -> canonical sector ids (saves/contracts keep
# the site:* ids; the sector layer is the superset)
LEGACY_SITE_SECTOR = {
    "site:peary": "core:sec_moon_10",
    "site:jezero": "core:sec_mars_07",
    "site:venus_cloud": "core:sec_venus_10",
    "site:titan_shore": "core:sec_titan_02",
    "site:europa_burrow": "core:sec_europa_01",
}


def sectors_of(db: ContentDB, body_id: str) -> list[dict]:
    rows = [s for s in db.by_type("sectors").values()
            if s["body"] == body_id]
    return sorted(rows, key=lambda s: s["idx"])


def landable(sector: dict) -> bool:
    return sector["landing_class"] in ("A", "B", "C", "D")


def anomalies_at(db: ContentDB, sector_id: str) -> list[dict]:
    return [a for a in db.by_type("anomalies").values()
            if a["sector"] == sector_id]


def sector_site(db: ContentDB, sector_id: str) -> dict:
    """Synthesize a SITES-shaped dict for any landable sector, so descent,
    base founding and surface ops work on the whole solar system."""
    sec = db.by_type("sectors")[sector_id]
    body = sec["body"]
    ops = BODY_OPS.get(body)
    if ops is None or not landable(sec):
        raise ValueError(f"{sector_id}: not a landable surface")
    region = db.by_type("regions")[sec["region"]]
    flags = sec.get("flags", [])
    # solar factor bundles distance^2 and the local sky (PSR dark, PEL
    # near-eternal rim light, atmosphere f_atm)
    inv_d2 = 1.0 / (ops["d"] ** 2)
    if "PSR" in flags:
        solar = 0.0
    elif "PEL" in flags:
        solar = 0.85 * inv_d2
    else:
        solar = sec.get("f_atm", 1.0) * inv_d2
    aero = sec["landing_class"] in ("C", "D")
    anoms = anomalies_at(db, sector_id)
    out = {
        "body": body,
        "name": f"{sec['name']} ({body.split(':')[1].title()})",
        "kind": sec["site_kind"],
        "land_dv": ops["land"] if aero else ops["asc"],
        "ascent_dv": ops["asc"],
        # small per-sector exploration lump; the big money is the one-shot
        # region ground survey (10·X via research.award_survey) + milestones
        "science": 2.0 * region["x"],
        "aero": aero,
        "solar": round(solar, 4),
        "day_s": (None if ("PEL" in flags or "PSR" in flags)
                  else ops["day_s"]),
        "region_code": region["code"],
        "x": region["x"],
        "sector_id": sector_id,
        "terrain": sec["terrain"],
        "landing_class": sec["landing_class"],
        "edl_sigma_km": EDL_SIGMA_KM[sec["landing_class"]],
        "anomalies": [a["id"] for a in anoms],
        "heritage": "HERITAGE" in flags,
        "blurb": (f"{sec['terrain'].replace('_', ' ').lower()} · "
                  f"region {region['code']} (X={region['x']:g})"
                  + (f" · {len(anoms)} anomaly site(s)" if anoms else "")),
    }
    if body == "core:venus" and sec["terrain"] == "CLOUD_BAND":
        out["requires_part"] = "core:gondola_havoc"   # aerostat envelope
    return out


def landing_offset_km(sector: dict, u: float) -> float:
    """Touchdown offset draw (S-7b): N(0, sigma) via inverse-ish transform
    of a uniform u in (0,1) — caller supplies the deterministic roll."""
    sigma = EDL_SIGMA_KM[sector["landing_class"]]
    # Box-Muller-lite using two halves of u keeps it deterministic & cheap
    z = math.sqrt(-2.0 * math.log(max(1e-9, u))) * math.cos(2 * math.pi * u)
    return sigma * z
