"""Generate the full data/core/parts catalog from the canon tables
(02 §4.1 engine master list; 06 §4.2 tanks). Run: python tools/gen_parts.py
Overwrites existing generated part files (payload_2t.toml is hand-kept).

O/F mass fractions: methalox 3.6 -> 0.783/0.217; kerolox 2.36 ->
0.702/0.298; hydrolox 6.0 -> 0.857/0.143; NTO/MMH 1.65 -> 0.623/0.377.
"""

from __future__ import annotations

from pathlib import Path

METHALOX = '{ Oxygen = 0.783, Methane = 0.217 }'
KEROLOX = '{ Oxygen = 0.702, RP1 = 0.298 }'
HYDROLOX = '{ Oxygen = 0.857, Hydrogen = 0.143 }'
HYPERGOL = '{ NTO = 0.623, MMH = 0.377 }'

# slug, id-suffix, tier, name, mass_t, thrust_vac_kN, isp_vac, isp_sl,
# min_throttle, gimbal_deg, propellant-mix
ENGINES = [
    ("oms27",  "T0", "OMS-27 Vireo storable OMS (Shuttle OMS)",        0.118, 26.7,  316.0, 100.0, 1.00, 6.0,  HYPERGOL),
    ("sps91",  "T0", "SPS-91 Pelican storable service engine (Apollo)", 0.293, 91.0,  314.0, 60.0,  1.00, 6.0,  HYPERGOL),
    ("lnd71",  "T1", "LND-71 Ibex storable lander (SuperDraco)",        0.120, 73.0,  243.0, 235.0, 0.20, 0.0,  HYPERGOL),
    ("k845",   "T0", "K-845 Mule kerolox booster (Merlin 1D)",          0.470, 914.0, 311.0, 282.0, 0.40, 5.0,  KEROLOX),
    ("kv981",  "T0", "KV-981 Mule-V kerolox vacuum (Merlin Vacuum)",    0.630, 981.0, 348.0, 90.0,  0.60, 3.0,  KEROLOX),
    ("h102",   "T0", "H-102 Crane hydrolox upper (RL10C-1)",            0.190, 101.8, 449.7, 110.0, 1.00, 4.0,  HYDROLOX),
    ("hl67",   "T1", "HL-67 Heron hydrolox lander (CECE)",              0.230, 67.0,  445.0, 120.0, 0.06, 4.0,  HYDROLOX),
    ("h2280",  "T1", "H-2280 Shire hydrolox sustainer (RS-25)",         3.177, 2279.0, 452.0, 366.0, 0.67, 10.5, HYDROLOX),
    ("m2256",  "T1", "M-2256 Drayhorse methalox (Raptor 2)",            1.630, 2394.0, 347.0, 327.0, 0.40, 15.0, METHALOX),
    ("mv2530", "T1", "MV-2530 Drayhorse-V methalox vacuum (Raptor V)",  2.100, 2530.0, 380.0, 100.0, 0.40, 3.0,  METHALOX),
    ("m733",   "T1", "M-733 Bantam methalox booster engine",            0.750, 765.0, 329.0, 315.0, 0.40, 5.0,  METHALOX),
    ("mv815",  "T1", "MV-815 Bantam-V vacuum methalox engine",          0.900, 815.0, 367.0, 95.0,  0.50, 3.0,  METHALOX),
    ("ml24",   "T2", "ML-24 Gopher methalox lander (Morpheus HD)",      0.080, 24.0,  320.0, 295.0, 0.25, 5.0,  METHALOX),
    ("ml111",  "T2", "ML-111 Badger pump-fed methalox lander engine",   0.240, 111.0, 355.0, 300.0, 0.15, 8.0,  METHALOX),
]

# slug, tier, name, dry_t, cap_t, mixture
TANKS = [
    ("ml_s",   "T0", "Methalox tank S",        0.27, 4.5,   METHALOX),
    ("ml_m",   "T0", "Methalox tank M",        0.72, 12.0,  METHALOX),
    ("ml_l",   "T0", "Methalox tank L",        2.1,  35.0,  METHALOX),
    ("ml_xl",  "T1", "Methalox tank XL",       4.8,  80.0,  METHALOX),
    ("kl_m",   "T0", "Kerolox tank M",         0.70, 14.0,  KEROLOX),
    ("lh2_m",  "T1", "LH2 tank M (ZBO)",       0.60, 4.0,   '{ Hydrogen = 1.0 }'),
    ("lh2_l",  "T2", "LH2 tank L (ZBO)",       3.0,  20.0,  '{ Hydrogen = 1.0 }'),
    ("lox_m",  "T0", "LOX tank M",             0.40, 8.0,   '{ Oxygen = 1.0 }'),
    ("ch4_m",  "T0", "Methane tank M",         0.35, 7.0,   '{ Methane = 1.0 }'),
    ("hyp_s",  "T0", "Storable-prop tank S",   0.10, 1.6,   HYPERGOL),
    ("xe_s",   "T0", "Xenon COPV S",           0.025, 0.42, '{ Xenon = 1.0 }'),
    ("xe_l",   "T1", "Xenon COPV L",           0.24, 4.0,   '{ Xenon = 1.0 }'),
    ("h2o",    "T0", "Water tank",             0.10, 2.0,   '{ Water = 1.0 }'),
    ("n2",     "T0", "Gas bottle (N2)",        0.05, 0.25,  '{ Nitrogen = 1.0 }'),
    ("depot",  "T1", "Cryo depot tank",        14.0, 200.0, METHALOX),
]


def main() -> None:
    out = Path(__file__).resolve().parent.parent / "data" / "core" / "parts"
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    for slug, tier, name, mass, thrust, isp, isp_sl, throttle_min, gimbal, mix in ENGINES:
        text = (
            f'id        = "core:engine_{slug}"\n'
            f'type      = "engine"\n'
            f'tier      = "{tier}"\n'
            f'name      = "{name}"\n'
            f'mass_t    = {mass}\n'
            f'[engine]\n'
            f'thrust_kN  = {thrust}\n'
            f'isp_s      = {isp}\n'
            f'isp_sl_s   = {isp_sl}\n'
            f'throttle   = [{throttle_min}, 1.0]\n'
            f'gimbal_deg = {gimbal}\n'
            f'propellant = {mix}\n')
        (out / f"engine_{slug}.toml").write_text(text, encoding="utf-8", newline="\n")
        n += 1
    for slug, tier, name, dry, cap, mix in TANKS:
        text = (
            f'id     = "core:tank_{slug}"\n'
            f'type   = "tank"\n'
            f'tier   = "{tier}"\n'
            f'name   = "{name}"\n'
            f'mass_t = {dry}\n'
            f'[tank]\n'
            f'capacity_t = {cap}\n'
            f'mixture    = {mix}\n')
        (out / f"tank_{slug}.toml").write_text(text, encoding="utf-8", newline="\n")
        n += 1
    print(f"wrote {n} parts to {out}")


if __name__ == "__main__":
    main()
