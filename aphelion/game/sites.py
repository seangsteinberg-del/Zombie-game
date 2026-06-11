"""Surface sites (03 §4.4 + 01 Δv map): named landing targets with real
propulsive costs. land_dv is what the lander's tanks actually pay to get
down (aero-assisted entries pay only the propulsive terminal phase);
ascent_dv returns you to a 100 km parking orbit. Science is the
first-landing award (bigger than first SOI entry — boots beat flybys).

kind drives base gameplay: what a base founded here can extract, and
which special hardware the site demands (07/02 exotic-environment rows).
"""

from __future__ import annotations

SITES: dict[str, dict] = {
    "site:peary": {
        "body": "core:moon", "name": "Peary crater rim (lunar pole)",
        "kind": "psr_ice", "land_dv": 1_900.0, "ascent_dv": 1_900.0,
        "science": 600.0, "aero": False, "solar": 0.85,
        "day_s": None,                  # near-eternal rim sun
        "blurb": "PSR ice 200 m away; near-eternal solar on the rim",
    },
    "site:jezero": {
        "body": "core:mars", "name": "Jezero delta (Mars)",
        "kind": "mars_ice", "land_dv": 1_000.0, "ascent_dv": 4_100.0,
        "science": 1_200.0, "aero": True, "solar": 0.40,
        "day_s": 88_775.0,
        "blurb": "entry burns the atmosphere, not your tanks; CO2 + ice",
    },
    "site:venus_cloud": {
        "body": "core:venus", "name": "55 km cloud deck (Venus)",
        "kind": "aerostat", "land_dv": 300.0, "ascent_dv": 8_000.0,
        "science": 2_000.0, "aero": True, "solar": 1.30,
        "requires_part": "core:gondola_havoc",
        "day_s": 4.0 * 86_400.0,        # super-rotating cloud deck
        "blurb": "HAVOC altitude: 1 bar, 27 C — the only shirt-sleeve sky",
    },
    "site:titan_shore": {
        "body": "core:titan", "name": "Ligeia Mare shoreline (Titan)",
        "kind": "methane_lake", "land_dv": 350.0, "ascent_dv": 2_400.0,
        "science": 2_500.0, "aero": True, "solar": 0.04,
        "day_s": 1.38e6,
        "blurb": "thick air, soft gravity; LCH4 to drink for your engines",
    },
    "site:europa_burrow": {
        "body": "core:europa", "name": "Conamara chaos (Europa)",
        "kind": "ice_burrow", "land_dv": 1_500.0, "ascent_dv": 1_450.0,
        "science": 2_500.0, "aero": False, "solar": 0.03,
        "day_s": 3.07e5,
        "blurb": "5.4 Sv/day on the surface — dig 14 m or die",
    },
}


def sites_for_body(body_id: str) -> list[tuple[str, dict]]:
    return [(sid, s) for sid, s in SITES.items() if s["body"] == body_id]
