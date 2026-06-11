"""Generate the surface-sector, science-region and anomaly content packs
from design/extracts/03-solar-system-buildspec.md (§1.7-1.8, §2.1-2.4).

Run:  python tools/gen_system.py

Emits data/core/sectors/*.toml (one per sector, ~190), data/core/regions/
*.toml and data/core/anomalies/*.toml (AN-01..50). Deterministic; re-run
after editing the tables. Sector ids are stable strings forever (F-12).
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEC_DIR = ROOT / "data" / "core" / "sectors"
REG_DIR = ROOT / "data" / "core" / "regions"
AN_DIR = ROOT / "data" / "core" / "anomalies"

# terrain_class -> (slope_sigma, rock_abundance, dust_index, anomaly_slots)
TERRAIN = {
    "MARE": (2, 0.10, 0.4, 1), "HIGHLAND": (6, 0.25, 0.3, 1),
    "DUNE": (4, 0.05, 0.9, 1), "ICE_PLAIN": (3, 0.10, 0.1, 1),
    "CHAOS": (12, 0.45, 0.1, 2), "VOLCANIC": (8, 0.35, 0.2, 2),
    "PSR": (8, 0.20, 0.1, 1), "SEA": (0, 0.0, 0.0, 1),
    "CLOUD_BAND": (0, 0.0, 0.0, 1), "REGOLITH_PILE": (15, 0.60, 0.8, 1),
}

# science regions (§2.4): id -> (body, X, kind)  kind: orbit|surface|special
REGIONS = {
    "EAR-ORB-LEO": ("core:earth", 1.0, "orbit"),
    "EAR-ORB-HIGH": ("core:earth", 1.5, "orbit"),
    "EAR-SURF": ("core:earth", 1.0, "surface"),
    "MOO-ORB": ("core:moon", 2.0, "orbit"),
    "MOO-NEAR": ("core:moon", 2.0, "surface"),
    "MOO-FARPOLE": ("core:moon", 4.0, "surface"),
    "MER-ORB": ("core:mercury", 6.0, "orbit"),
    "MER-SURF": ("core:mercury", 7.0, "surface"),
    "MER-PSR": ("core:mercury", 8.0, "surface"),
    "VEN-ORB": ("core:venus", 6.0, "orbit"),
    "VEN-CLOUD": ("core:venus", 6.0, "surface"),
    "VEN-SURF": ("core:venus", 8.0, "surface"),
    "MAR-ORB": ("core:mars", 5.0, "orbit"),
    "MAR-SURF": ("core:mars", 5.0, "surface"),
    "PHO-SURF": ("core:phobos", 5.0, "surface"),
    "DEI-SURF": ("core:deimos", 5.0, "surface"),
    "BEN-SURF": ("core:bennu", 4.0, "surface"),
    "RYU-SURF": ("core:ryugu", 4.0, "surface"),
    "ITO-SURF": ("core:itokawa", 4.0, "surface"),
    "ERO-SURF": ("core:eros", 4.0, "surface"),
    "APO-SURF": ("core:apophis", 4.0, "surface"),
    "CER-ORB": ("core:ceres", 6.0, "orbit"),
    "CER-SURF": ("core:ceres", 6.0, "surface"),
    "VES-SURF": ("core:vesta", 6.0, "surface"),
    "PSY-SURF": ("core:psyche", 6.0, "surface"),
    "HYG-SURF": ("core:hygiea", 6.0, "surface"),
    "67P-NUC": ("core:67p", 7.0, "surface"),
    "HAL-NUC": ("core:halley", 7.0, "surface"),
    "JUP-ATM": ("core:jupiter", 9.0, "surface"),
    "IO-SURF": ("core:io", 10.0, "surface"),
    "EUR-SURF": ("core:europa", 10.0, "surface"),
    "EUR-OCEAN": ("core:europa", 14.0, "special"),
    "GAN-SURF": ("core:ganymede", 8.0, "surface"),
    "CAL-SURF": ("core:callisto", 8.0, "surface"),
    "SAT-ATM": ("core:saturn", 10.0, "surface"),
    "SAT-RINGS": ("core:saturn", 10.0, "special"),
    "TIT-ORB": ("core:titan", 10.0, "orbit"),
    "TIT-SURF": ("core:titan", 11.0, "surface"),
    "TIT-SEAS": ("core:titan", 11.0, "surface"),
    "TIT-SEAFLOOR": ("core:titan", 14.0, "special"),
    "ENC-SPT": ("core:enceladus", 12.0, "surface"),
    "ENC-NORTH": ("core:enceladus", 10.0, "surface"),
    "URA-ATM": ("core:uranus", 11.0, "surface"),
    "MIR-SURF": ("core:miranda", 12.0, "surface"),
    "TIA-SURF": ("core:titania", 12.0, "surface"),
    "OBE-SURF": ("core:oberon", 12.0, "surface"),
    "NEP-ATM": ("core:neptune", 12.0, "surface"),
    "TRI-SURF": ("core:triton", 13.0, "surface"),
    "PLU-SURF": ("core:pluto", 13.0, "surface"),
    "CHA-SURF": ("core:charon", 13.0, "surface"),
    "ARR-SURF": ("core:arrokoth", 13.0, "surface"),
    "ERI-SURF": ("core:eris", 13.0, "surface"),
}

# per-body sector lists (§1.8): body -> landing_class, [(name, terrain,
# region, flags, overrides), ...]   flags: PSR PEL SEA HERITAGE HOTSPOT
# overrides: dict of record fields (dust_index, kind, slots...)
S = {}

S["core:mercury"] = ("B", [
    ("Caloris Basin", "VOLCANIC", "MER-SURF", "", {}),
    ("Pantheon Fossae", "HIGHLAND", "MER-SURF", "", {}),
    ("Borealis PSR-N", "PSR", "MER-PSR", "PSR", {"kind": "psr_ice"}),
    ("Kandinsky PSR-N", "PSR", "MER-PSR", "PSR", {"kind": "psr_ice"}),
    ("South PSR", "PSR", "MER-PSR", "PSR", {"kind": "psr_ice"}),
    ("Hollows Terrain", "CHAOS", "MER-SURF", "", {}),
    ("Intercrater Plains W", "HIGHLAND", "MER-SURF", "", {}),
    ("Intercrater Plains E", "HIGHLAND", "MER-SURF", "", {}),
    ("Smooth Plains", "MARE", "MER-SURF", "", {}),
    ("Discovery Rupes", "HIGHLAND", "MER-SURF", "", {}),
])

S["core:venus"] = ("E", [
    ("Maxwell Montes", "HIGHLAND", "VEN-SURF", "", {}),
    ("Maat Mons", "VOLCANIC", "VEN-SURF", "HOTSPOT", {}),
    ("Beta Regio", "VOLCANIC", "VEN-SURF", "", {}),
    ("Phoebe Regio", "HIGHLAND", "VEN-SURF", "", {}),
    ("Baltis Vallis", "MARE", "VEN-SURF", "", {}),
    ("Lakshmi Planum", "MARE", "VEN-SURF", "", {}),
    ("Aphrodite Terra", "CHAOS", "VEN-SURF", "", {}),
    ("Lowland Plains", "MARE", "VEN-SURF", "", {}),
    ("V-Cloud-Low 48-50 km", "CLOUD_BAND", "VEN-CLOUD", "",
     {"kind": "aerostat", "landing_class": "D", "f_atm": 0.30}),
    ("V-HAVOC 50-52 km", "CLOUD_BAND", "VEN-CLOUD", "",
     {"kind": "aerostat", "landing_class": "D", "f_atm": 0.45}),
    ("V-Temperate 52-56 km", "CLOUD_BAND", "VEN-CLOUD", "",
     {"kind": "aerostat", "landing_class": "D", "f_atm": 0.55}),
    ("V-Cloud-Top 56-62 km", "CLOUD_BAND", "VEN-CLOUD", "",
     {"kind": "aerostat", "landing_class": "D", "f_atm": 0.70}),
])

S["core:earth"] = ("C", [
    ("Equatorial Spaceport", "MARE", "EAR-SURF", "", {}),
    ("High-Latitude Spaceport", "HIGHLAND", "EAR-SURF", "", {}),
    ("Atacama Observatory", "HIGHLAND", "EAR-SURF", "", {}),
    ("Iceland Geothermal Park", "VOLCANIC", "EAR-SURF", "", {}),
    ("Mass-Driver Site", "DUNE", "EAR-SURF", "", {}),
    ("Pacific Recovery Zone", "SEA", "EAR-SURF", "SEA", {}),
    ("Atlantic Recovery Zone", "SEA", "EAR-SURF", "SEA", {}),
    ("Boreal Market Region", "HIGHLAND", "EAR-SURF", "", {}),
    ("Monsoon Market Region", "MARE", "EAR-SURF", "", {}),
    ("Steppe Market Region", "HIGHLAND", "EAR-SURF", "", {}),
    ("Megacity Coast", "MARE", "EAR-SURF", "", {}),
    ("Polar Research Zone", "ICE_PLAIN", "EAR-SURF", "", {}),
])

S["core:moon"] = ("B", [
    ("Mare Tranquillitatis", "MARE", "MOO-NEAR", "HERITAGE", {}),
    ("Oceanus Procellarum", "MARE", "MOO-NEAR", "", {}),
    ("Mare Imbrium", "MARE", "MOO-NEAR", "HERITAGE", {}),
    ("Taurus-Littrow", "HIGHLAND", "MOO-NEAR", "HERITAGE", {}),
    ("Aristarchus Plateau", "VOLCANIC", "MOO-NEAR", "", {}),
    ("Marius Hills", "VOLCANIC", "MOO-NEAR", "", {}),
    ("Highlands Near N", "HIGHLAND", "MOO-NEAR", "", {}),
    ("Highlands Near S", "HIGHLAND", "MOO-NEAR", "", {}),
    ("Tycho", "HIGHLAND", "MOO-NEAR", "", {}),
    ("South Pole Shackleton", "PSR", "MOO-FARPOLE", "PEL",
     {"kind": "psr_ice"}),
    ("Cabeus PSR", "PSR", "MOO-FARPOLE", "PSR", {"kind": "psr_ice"}),
    ("North Pole PSR", "PSR", "MOO-FARPOLE", "PSR", {"kind": "psr_ice"}),
    ("Far-side Highlands", "HIGHLAND", "MOO-FARPOLE", "", {}),
    ("South Pole-Aitken Basin", "HIGHLAND", "MOO-FARPOLE", "", {}),
])

S["core:mars"] = ("C", [
    ("Chryse Planitia", "MARE", "MAR-SURF", "HERITAGE", {}),
    ("Utopia Planitia", "MARE", "MAR-SURF", "HERITAGE", {}),
    ("Elysium Planitia", "MARE", "MAR-SURF", "", {}),
    ("Gale Crater", "HIGHLAND", "MAR-SURF", "HERITAGE", {}),
    ("Gusev Crater", "MARE", "MAR-SURF", "", {}),
    ("Meridiani Planum", "MARE", "MAR-SURF", "", {}),
    ("Jezero / Isidis", "HIGHLAND", "MAR-SURF", "HERITAGE",
     {"kind": "mars_ice"}),
    ("Arabia Terra", "HIGHLAND", "MAR-SURF", "", {}),
    ("Tharsis Rise", "VOLCANIC", "MAR-SURF", "", {}),
    ("Olympus Mons", "VOLCANIC", "MAR-SURF", "", {"dust_index": 0.1}),
    ("Valles Marineris", "CHAOS", "MAR-SURF", "", {}),
    ("Hellas Basin", "DUNE", "MAR-SURF", "", {"dust_index": 1.0}),
    ("Argyre Planitia", "HIGHLAND", "MAR-SURF", "", {}),
    ("Arcadia Ice N", "ICE_PLAIN", "MAR-SURF", "", {"kind": "mars_ice"}),
    ("Deuteronilus Ice N", "ICE_PLAIN", "MAR-SURF", "", {"kind": "mars_ice"}),
    ("Mid-Latitude Ice S", "ICE_PLAIN", "MAR-SURF", "", {"kind": "mars_ice"}),
    ("Polar Cap N", "ICE_PLAIN", "MAR-SURF", "", {"kind": "mars_ice"}),
    ("Medusae Fossae", "DUNE", "MAR-SURF", "", {"dust_index": 1.0}),
])

S["core:phobos"] = ("A", [
    ("Stickney Interior", "REGOLITH_PILE", "PHO-SURF", "", {}),
    ("Grooved Terrain", "REGOLITH_PILE", "PHO-SURF", "", {}),
    ("Sub-Mars Point", "REGOLITH_PILE", "PHO-SURF", "", {}),
])
S["core:deimos"] = ("A", [
    ("Smooth Saddle", "REGOLITH_PILE", "DEI-SURF", "", {}),
    ("Cratered North", "REGOLITH_PILE", "DEI-SURF", "", {}),
])

S["core:ceres"] = ("B", [
    ("Occator Faculae", "CHAOS", "CER-SURF", "", {}),
    ("Ahuna Mons", "VOLCANIC", "CER-SURF", "", {}),
    ("Kerwan Basin", "ICE_PLAIN", "CER-SURF", "", {"kind": "psr_ice"}),
    ("Equatorial Dark Plains", "MARE", "CER-SURF", "", {}),
    ("North Polar Craters", "PSR", "CER-SURF", "PSR", {"kind": "psr_ice"}),
    ("South Highlands", "HIGHLAND", "CER-SURF", "", {}),
    ("Urvara Basin", "HIGHLAND", "CER-SURF", "", {}),
    ("Juling Crater", "ICE_PLAIN", "CER-SURF", "", {"kind": "psr_ice"}),
])

S["core:vesta"] = ("B", [
    ("Rheasilvia Basin", "HIGHLAND", "VES-SURF", "", {}),
    ("Marcia Crater", "CHAOS", "VES-SURF", "", {}),
    ("Divalia Fossae", "HIGHLAND", "VES-SURF", "", {}),
    ("Cratered Highlands N", "HIGHLAND", "VES-SURF", "", {}),
    ("Cratered Highlands S", "HIGHLAND", "VES-SURF", "", {}),
    ("Dark-Material Unit", "MARE", "VES-SURF", "", {}),
])

S["core:psyche"] = ("B", [
    ("Metal Plains W", "HIGHLAND", "PSY-SURF", "", {}),
    ("Metal Plains E", "HIGHLAND", "PSY-SURF", "", {}),
    ("Meteorite Breccia", "REGOLITH_PILE", "PSY-SURF", "", {}),
    ("Crater Panthia", "CHAOS", "PSY-SURF", "", {}),
    ("Regolith South", "REGOLITH_PILE", "PSY-SURF", "", {}),
])

S["core:hygiea"] = ("B", [
    ("Carbonaceous Plains N", "MARE", "HYG-SURF", "", {}),
    ("Carbonaceous Plains S", "MARE", "HYG-SURF", "", {}),
    ("Hydrated Clay Basin", "ICE_PLAIN", "HYG-SURF", "", {"kind": "psr_ice"}),
    ("Cratered Terrain", "HIGHLAND", "HYG-SURF", "", {}),
])

S["core:io"] = ("B", [
    ("Loki Patera", "VOLCANIC", "IO-SURF", "HOTSPOT", {}),
    ("Pele", "VOLCANIC", "IO-SURF", "HOTSPOT", {}),
    ("Tvashtar Paterae", "VOLCANIC", "IO-SURF", "HOTSPOT", {}),
    ("Prometheus Plume Field", "VOLCANIC", "IO-SURF", "HOTSPOT", {}),
    ("Sulfur Plains W", "MARE", "IO-SURF", "", {}),
    ("Sulfur Plains E", "MARE", "IO-SURF", "", {}),
    ("Boosaule Montes", "HIGHLAND", "IO-SURF", "", {}),
    ("Polar Mountains S", "HIGHLAND", "IO-SURF", "", {}),
])

S["core:europa"] = ("B", [
    ("Conamara Chaos", "CHAOS", "EUR-SURF", "", {"kind": "ice_burrow"}),
    ("Thera Macula", "CHAOS", "EUR-SURF", "", {"kind": "ice_burrow"}),
    ("Ridge Plains N", "ICE_PLAIN", "EUR-SURF", "", {"kind": "ice_burrow"}),
    ("Ridge Plains S", "ICE_PLAIN", "EUR-SURF", "", {"kind": "ice_burrow"}),
    ("Lineae Band", "ICE_PLAIN", "EUR-SURF", "", {"kind": "ice_burrow"}),
    ("Pwyll Impact", "CHAOS", "EUR-SURF", "", {"kind": "ice_burrow"}),
    ("Polar Plains N", "ICE_PLAIN", "EUR-SURF", "", {"kind": "ice_burrow"}),
    ("Polar Plains S", "ICE_PLAIN", "EUR-SURF", "", {"kind": "ice_burrow"}),
])

S["core:ganymede"] = ("B", [
    ("Galileo Regio", "MARE", "GAN-SURF", "", {}),
    ("Uruk Sulcus", "HIGHLAND", "GAN-SURF", "", {}),
    ("Grooved Terrain W", "HIGHLAND", "GAN-SURF", "", {}),
    ("Grooved Terrain E", "HIGHLAND", "GAN-SURF", "", {}),
    ("Dark Terrain N", "MARE", "GAN-SURF", "", {}),
    ("Dark Terrain S", "MARE", "GAN-SURF", "", {}),
    ("Polar Cap N", "ICE_PLAIN", "GAN-SURF", "", {"kind": "psr_ice"}),
    ("Polar Cap S", "ICE_PLAIN", "GAN-SURF", "", {"kind": "psr_ice"}),
    ("Enki Catena", "CHAOS", "GAN-SURF", "", {}),
    ("Tros Ray Crater", "HIGHLAND", "GAN-SURF", "", {}),
])

S["core:callisto"] = ("B", [
    ("Valhalla Center", "CHAOS", "CAL-SURF", "", {}),
    ("Valhalla Ring Arc W", "HIGHLAND", "CAL-SURF", "", {}),
    ("Valhalla Ring Arc E", "HIGHLAND", "CAL-SURF", "", {}),
    ("Asgard Basin", "HIGHLAND", "CAL-SURF", "", {}),
    ("Cratered Plains N", "ICE_PLAIN", "CAL-SURF", "", {"kind": "psr_ice"}),
    ("Cratered Plains S", "ICE_PLAIN", "CAL-SURF", "", {"kind": "psr_ice"}),
    ("Cratered Plains W", "ICE_PLAIN", "CAL-SURF", "", {"kind": "psr_ice"}),
    ("Cratered Plains E", "ICE_PLAIN", "CAL-SURF", "", {"kind": "psr_ice"}),
    ("Knobby Terrain N", "CHAOS", "CAL-SURF", "", {}),
    ("Knobby Terrain S", "CHAOS", "CAL-SURF", "", {}),
])

S["core:titan"] = ("D", [
    ("Kraken Mare", "SEA", "TIT-SEAS", "SEA", {"kind": "methane_lake"}),
    ("Ligeia Mare", "SEA", "TIT-SEAS", "SEA", {"kind": "methane_lake"}),
    ("Punga Mare", "SEA", "TIT-SEAS", "SEA", {"kind": "methane_lake"}),
    ("Shangri-La Dunes", "DUNE", "TIT-SURF", "", {}),
    ("Adiri", "HIGHLAND", "TIT-SURF", "HERITAGE", {}),
    ("Selk Crater", "HIGHLAND", "TIT-SURF", "", {}),
    ("Xanadu", "HIGHLAND", "TIT-SURF", "", {}),
    ("Sotra Patera", "VOLCANIC", "TIT-SURF", "", {}),
    ("Polar Lake District N", "SEA", "TIT-SEAS", "SEA",
     {"kind": "methane_lake"}),
    ("Polar Lake District S", "SEA", "TIT-SEAS", "SEA",
     {"kind": "methane_lake"}),
    ("Equatorial Plains W", "MARE", "TIT-SURF", "", {}),
    ("Equatorial Plains E", "MARE", "TIT-SURF", "", {}),
])

S["core:enceladus"] = ("B", [
    ("Damascus Sulcus", "CHAOS", "ENC-SPT", "HOTSPOT", {}),
    ("Baghdad Sulcus", "CHAOS", "ENC-SPT", "HOTSPOT", {}),
    ("Cairo Sulcus", "CHAOS", "ENC-SPT", "HOTSPOT", {}),
    ("Alexandria Sulcus", "CHAOS", "ENC-SPT", "HOTSPOT", {}),
    ("Cratered North", "ICE_PLAIN", "ENC-NORTH", "", {"kind": "psr_ice"}),
    ("Sub-Saturn Plains", "ICE_PLAIN", "ENC-NORTH", "", {"kind": "psr_ice"}),
])

S["core:miranda"] = ("B", [
    ("Verona Rupes", "CHAOS", "MIR-SURF", "", {}),
    ("Chevron Corona W", "CHAOS", "MIR-SURF", "", {}),
    ("Chevron Corona E", "CHAOS", "MIR-SURF", "", {}),
    ("Cratered Plains", "ICE_PLAIN", "MIR-SURF", "", {"kind": "psr_ice"}),
])
S["core:titania"] = ("B", [
    ("Messina Chasmata", "CHAOS", "TIA-SURF", "", {}),
    ("Gertrude Crater", "HIGHLAND", "TIA-SURF", "", {}),
    ("Cratered Plains N", "ICE_PLAIN", "TIA-SURF", "", {"kind": "psr_ice"}),
    ("Cratered Plains S", "ICE_PLAIN", "TIA-SURF", "", {"kind": "psr_ice"}),
])
S["core:oberon"] = ("B", [
    ("Hamlet Crater", "HIGHLAND", "OBE-SURF", "", {}),
    ("South Limb Mountain", "HIGHLAND", "OBE-SURF", "", {}),
    ("Cratered Plains", "ICE_PLAIN", "OBE-SURF", "", {"kind": "psr_ice"}),
])

S["core:triton"] = ("B", [
    ("South Polar Cap", "ICE_PLAIN", "TRI-SURF", "HOTSPOT",
     {"kind": "psr_ice"}),
    ("Cantaloupe Terrain", "CHAOS", "TRI-SURF", "", {}),
    ("Equatorial Plains W", "ICE_PLAIN", "TRI-SURF", "", {"kind": "psr_ice"}),
    ("Equatorial Plains E", "ICE_PLAIN", "TRI-SURF", "", {"kind": "psr_ice"}),
    ("Northern Plains", "ICE_PLAIN", "TRI-SURF", "", {"kind": "psr_ice"}),
    ("Mahilani Plume Site", "ICE_PLAIN", "TRI-SURF", "HOTSPOT",
     {"kind": "psr_ice"}),
])

S["core:pluto"] = ("B", [
    ("Sputnik Planitia", "ICE_PLAIN", "PLU-SURF", "", {"kind": "psr_ice"}),
    ("al-Idrisi Montes", "CHAOS", "PLU-SURF", "", {}),
    ("Cthulhu Macula", "MARE", "PLU-SURF", "", {}),
    ("Wright Mons", "VOLCANIC", "PLU-SURF", "", {}),
    ("North Polar Terrain", "ICE_PLAIN", "PLU-SURF", "", {"kind": "psr_ice"}),
    ("Far-Side Plains", "ICE_PLAIN", "PLU-SURF", "", {"kind": "psr_ice"}),
])
S["core:charon"] = ("B", [
    ("Mordor Macula", "MARE", "CHA-SURF", "", {}),
    ("Serenity Chasma", "CHAOS", "CHA-SURF", "", {}),
    ("Vulcan Planum", "ICE_PLAIN", "CHA-SURF", "", {"kind": "psr_ice"}),
    ("Oz Terra", "HIGHLAND", "CHA-SURF", "", {}),
])

for _nea, _reg in (("bennu", "BEN-SURF"), ("ryugu", "RYU-SURF"),
                   ("itokawa", "ITO-SURF"), ("apophis", "APO-SURF")):
    S[f"core:{_nea}"] = ("A", [
        ("Sample Site", "REGOLITH_PILE", _reg, "", {}),
        ("Boulder Field", "REGOLITH_PILE", _reg, "", {}),
    ])
S["core:eros"] = ("A", [
    ("Himeros Saddle", "REGOLITH_PILE", "ERO-SURF", "", {}),
    ("Psyche Crater", "REGOLITH_PILE", "ERO-SURF", "", {}),
])
S["core:67p"] = ("A", [
    ("Abydos (small lobe)", "REGOLITH_PILE", "67P-NUC", "HERITAGE", {}),
    ("Ma'at (large lobe)", "REGOLITH_PILE", "67P-NUC", "", {}),
])
S["core:halley"] = ("A", [
    ("Sunward Active Neck", "REGOLITH_PILE", "HAL-NUC", "", {}),
    ("Dark Lobe", "REGOLITH_PILE", "HAL-NUC", "", {}),
])
S["core:arrokoth"] = ("A", [
    ("Contact Neck", "REGOLITH_PILE", "ARR-SURF", "", {}),
])
S["core:eris"] = ("B", [
    ("Collapsed-Frost Plains", "ICE_PLAIN", "ERI-SURF", "",
     {"kind": "psr_ice"}),
    ("Highland Terrain", "HIGHLAND", "ERI-SURF", "", {}),
])

for _gg, _reg in (("jupiter", "JUP-ATM"), ("saturn", "SAT-ATM"),
                  ("uranus", "URA-ATM"), ("neptune", "NEP-ATM")):
    S[f"core:{_gg}"] = ("F", [
        ("Atmosphere Probe Band", "CLOUD_BAND", _reg, "",
         {"landing_class": "F"}),
    ])

# ---- anomalies (§2.1, AN-01..50) -------------------------------------------
# (num, body, sector_idx (1-based, 0 = orbit/heliocentric), class, name,
#  gb, reward_note, heritage)
AN = [
    (1, "core:moon", 1, "DERELICT", "Apollo 11 descent stage", 50,
     "Prestige x3; heritage zone", True),
    (2, "core:moon", 4, "DERELICT", "Apollo 17 + LRV", 50,
     "preserve-or-salvage Prestige choice", True),
    (3, "core:moon", 3, "DERELICT", "Lunokhod 1 (retroreflector live)", 30,
     "free nav-beacon upgrade", False),
    (4, "core:moon", 2, "DERELICT", "Luna 9 (first soft landing)", 30,
     "Prestige", False),
    (5, "core:moon", 11, "COLDTRAP", "LCROSS scar + 5.6 wt% ice truth", 20,
     "instant K2 on sector Water deposit", False),
    (6, "core:moon", 6, "TUBE", "Marius Hills skylight (tube >= 60 m)", 30,
     "buried base: cost -40%, radiation x0.05", False),
    (7, "core:moon", 10, "DERELICT", "Chandrayaan-3 + Artemis hardware", 20,
     "2 t MachineParts salvage", False),
    (8, "core:mars", 1, "DERELICT", "Viking 1", 40,
     "0.5 kg Pu238 (decayed)", False),
    (9, "core:mars", 2, "DERELICT", "Viking 2 + Zhurong", 40,
     "Pu238 salvage", False),
    (10, "core:mars", 6, "DERELICT", "Opportunity rover", 35,
     "dust-death telemetry codex", False),
    (11, "core:mars", 7, "DERELICT", "Perseverance + MSR sample depot", 60,
     "sample-retrieval contract jackpot", True),
    (12, "core:mars", 4, "DERELICT", "Curiosity (MMRTG warm)", 40,
     "2.6 kg Pu238 salvage", False),
    (13, "core:mars", 13, "DERELICT", "Mars 3 (first Mars soft landing)", 30,
     "", False),
    (14, "core:mars", 10, "WONDER", "Olympus summit above the dust", 30,
     "f_dust exponent x0.5; Prestige", False),
    (15, "core:mars", 11, "WONDER", "Valles Marineris canyon floor", 30,
     "floor pressure +20%; wind shelter", False),
    (16, "core:mars", 14, "COLDTRAP", "SWIM ice lens under 1 m", 25,
     "instant K2 Water", False),
    (17, "core:venus", 4, "DERELICT", "Venera 13", 40,
     "capsule-recovery trophy contract", False),
    (18, "core:venus", 10, "DERELICT", "Vega balloon gondolas adrift", 25,
     "drifting-intercept", False),
    (19, "core:venus", 1, "WONDER", "Maxwell metal-frost snowline", 30,
     "RareEarths trace unlock", False),
    (20, "core:venus", 2, "WONDER", "Maat Mons live vents", 40,
     "eruption events", False),
    (21, "core:mercury", 2, "WONDER", "Pantheon Fossae 'the Spider'", 30,
     "", False),
    (22, "core:mercury", 6, "WONDER", "Volatile sublimation hollows", 25,
     "sulfide lag-deposit unlock", False),
    (23, "core:mercury", 9, "DERELICT", "MESSENGER impact scar", 15,
     "", False),
    (24, "core:phobos", 3, "DERELICT", "Phobos 2 + MMX hardware", 30,
     "comms-relay flag; sample canister", False),
    (25, "core:ceres", 1, "WONDER", "Cerealia Facula brine reservoir", 40,
     "deep-brine T3 megaproject unlock", False),
    (26, "core:ceres", 0, "DERELICT", "Dawn orbiter", 20,
     "10 kg Xenon", False),
    (27, "core:bennu", 1, "WONDER", "Nightingale TAG scar", 25,
     "sector deposits to K2", False),
    (28, "core:eros", 2, "DERELICT", "NEAR Shoemaker", 25, "", False),
    (29, "core:earth", 0, "DERELICT", "Tesla Roadster + Starman", 15,
     "1 t Polymers; meme Prestige", False),
    (30, "core:earth", 0, "DERELICT", "Apollo 10 LM 'Snoopy'", 35,
     "Prestige x2", False),
    (31, "core:earth", 0, "DERELICT", "Vanguard 1 (1958)", 20,
     "retrieve = Prestige x2", False),
    (32, "core:earth", 0, "DERELICT", "Envisat hulk (8 t)", 20,
     "6 t StructuralParts/Electronics", False),
    (33, "core:europa", 1, "WONDER", "Conamara brine lens 1-3 km", 60,
     "melt-probe precursor", False),
    (34, "core:europa", 0, "WONDER", "Sub-ice ocean contact", 200,
     "campaign jackpot; abiotic chemistry", False),
    (35, "core:io", 1, "WONDER", "Loki overturning lava lake", 50,
     "1/(30 d) eruption risk", False),
    (36, "core:ganymede", 9, "WONDER", "Enki Catena crater chain", 25,
     "", False),
    (37, "core:callisto", 1, "WONDER", "Valhalla multi-ring basin", 30,
     "base-site flag", False),
    (38, "core:titan", 5, "DERELICT", "Huygens probe", 50,
     "Prestige x2", True),
    (39, "core:titan", 6, "DERELICT", "Dragonfly (silent since 2039)", 40,
     "rotor salvage: Titan-flyer discount", False),
    (40, "core:titan", 8, "WONDER", "Sotra cryovolcano", 35, "", False),
    (41, "core:enceladus", 1, "WONDER", "Tiger-stripe vent field", 30,
     "vent-capture sites", False),
    (42, "core:67p", 1, "DERELICT", "Philae", 35,
     "anchoring-failure codex", True),
    (43, "core:67p", 2, "DERELICT", "Rosetta", 30, "", False),
    (44, "core:halley", 0, "EVENT", "2061 perihelion passage", 100,
     "retrograde-rendezvous achievement", False),
    (45, "core:miranda", 1, "WONDER", "Verona Rupes 5-10 km cliff", 40,
     "lowest-g descent stunt Prestige", False),
    (46, "core:triton", 1, "WONDER", "Active nitrogen geysers", 40,
     "", False),
    (47, "core:pluto", 1, "WONDER", "Convecting nitrogen glacier", 60,
     "Nitrogen mega-deposit unlock", False),
    (48, "core:pluto", 2, "WONDER", "Floating water-ice rafts", 30,
     "", False),
    (49, "core:arrokoth", 1, "WONDER", "Pristine contact binary", 50,
     "x2 pristine GB", False),
    (50, "core:moon", 13, "DERELICT", "Chang'e 4 + Yutu 2", 30,
     "", False),
]


def _toml_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main() -> None:
    n_sectors = sum(len(rows) for _, rows in S.values())
    for d in (SEC_DIR, REG_DIR, AN_DIR):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)

    for rid, (body, x, kind) in REGIONS.items():
        slug = rid.lower().replace("-", "_")
        lines = ["# generated by tools/gen_system.py"]
        lines.append(f'id   = "core:reg_{slug}"')
        lines.append(f'code = "{rid}"')
        lines.append(f'body = "{body}"')
        lines.append(f"x = {float(x)}")
        lines.append(f'kind = "{kind}"')
        (REG_DIR / f"{slug}.toml").write_text("\n".join(lines) + "\n",
                                              encoding="utf-8", newline="\n")

    sec_ids: dict[tuple[str, int], str] = {}
    for body, (lc_default, rows) in S.items():
        bslug = body.split(":")[1]
        n = len(rows)
        for i, (name, terrain, region, flags, over) in enumerate(rows):
            sid = f"core:sec_{bslug}_{i + 1:02d}"
            sec_ids[(body, i + 1)] = sid
            slope, rock, dust, slots = TERRAIN[terrain]
            lines = ["# generated by tools/gen_system.py"]
            lines.append(f'id     = "{sid}"')
            lines.append(f'body   = "{body}"')
            lines.append(f"idx    = {i + 1}")
            lines.append(f"name   = {_toml_str(name)}")
            lines.append(f'terrain = "{terrain}"')
            lines.append(f"arc_deg = {round(360.0 / n, 4)}")
            lines.append(f"phi_center_deg = {round(360.0 * (i + 0.5) / n, 4)}")
            lines.append(f"slope_sigma = {float(over.get('slope_sigma', slope))}")
            lines.append(f"rock_abundance = {float(over.get('rock_abundance', rock))}")
            lines.append(f"dust_index = {float(over.get('dust_index', dust))}")
            lines.append(f"anomaly_slots = {int(over.get('slots', slots))}")
            lines.append(f'landing_class = "{over.get("landing_class", lc_default)}"')
            lines.append(f'region = "core:reg_{region.lower().replace("-", "_")}"')
            lines.append(f'site_kind = "{over.get("kind", "regolith")}"')
            if "f_atm" in over:
                lines.append(f"f_atm = {float(over['f_atm'])}")
            fl = [f for f in flags.split() if f]
            lines.append("flags = [" + ", ".join(f'"{f}"' for f in fl) + "]")
            (SEC_DIR / f"{bslug}_{i + 1:02d}.toml").write_text(
                "\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    for num, body, sec_idx, klass, name, gb, reward, heritage in AN:
        sid = sec_ids.get((body, sec_idx)) if sec_idx else None
        lines = ["# generated by tools/gen_system.py"]
        lines.append(f'id    = "core:an{num:02d}"')
        lines.append(f'body  = "{body}"')
        lines.append("sector = " + (f'"{sid}"' if sid else '"orbit"'))
        lines.append(f'class = "{klass}"')
        lines.append(f"name  = {_toml_str(name)}")
        lines.append(f"gb = {float(gb)}")
        lines.append(f"reward = {_toml_str(reward)}")
        lines.append(f"heritage = {'true' if heritage else 'false'}")
        (AN_DIR / f"an{num:02d}.toml").write_text(
            "\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    print(f"wrote {n_sectors} sectors, {len(REGIONS)} regions, "
          f"{len(AN)} anomalies")


if __name__ == "__main__":
    main()
