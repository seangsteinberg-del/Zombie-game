# BUILD SPEC — 02 Propulsion (extracted from design/02-propulsion.md, DECISIONS.md applied)

Source of truth: `design/02-propulsion.md` (649 lines). Conflicts resolved per `design/DECISIONS.md`
(A1 RP1 spelling, A5 unified wear, A8 three engine registrations accepted, B11 hypergolic ISRU at T3,
C23 plume scour IN, C25 per-bank EP bookkeeping, E playtest placeholders stay).
Conventions: SI everywhere; `g0 = 9.80665 m/s²` on every body. Catalog thrust in kN, formulas in N.
`[est]` = evolving real-world figure; `†` = synthetic Isp_SL (back-pressure slope datum for vacuum
engines, not an operating claim — §3.3 model needs it). `[SPECULATIVE]` = T4 honesty tag.

---

## 1. FULL ENGINE CATALOG

### 1.1 Chemical engines (doc §4.2)

Columns: x_min = min throttle fraction; Ign = rated ignitions (wear normalizer, NOT a hard limit);
Burn = rated burn seconds (wear normalizer); p_max = max ambient pressure for ignition (kPa);
Cost class per §1.9 legend.

| ID / name | Anchor | Tier | Cycle / feed | Prop (O/F) | Dry kg | Thrust SL/vac kN | Isp SL/vac s | x_min | Gimbal | Ign | Burn s | p_max | Cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SRM-2 "Kestrel" | Star 48B | T0 | solid | APCP sealed; 2,011 kg prop, 2,137 gross | 126 burnout | — / 66 | 250 / 286 | 1.0 | none | 1 | 87 | 101 | A |
| SRM-49 "Aurochs" | GEM 63 | T0 | solid strap-on | APCP sealed; 44,087 kg prop, ≈49,300 gross `[est]` | ≈5,200 `[est]` | 1,265 avg (1,663 max) | 245 / 275 `[est]` | 1.0 | none | 1 | 94 | 101 | A |
| OMS-27 "Vireo" | Shuttle OMS AJ10-190 | T0 | pressure-fed | NTO/MMH 1.65 | 118 | — / 26.7 | 100† / 316 | 1.0 fixed | ±6° | 500 | 15,000 | 30 | B |
| SPS-91 "Pelican" | Apollo SPS AJ10-137 | T0 | pressure-fed | NTO/MMH 1.65 | 293 | — / 91 | 60† / 314 | 1.0 fixed | ±6° | 200 | 750 | 30 | B |
| LND-71 "Ibex" | SuperDraco | T1 | pressure-fed lander | NTO/MMH 1.65 | 120 `[est]` | 71 / 73 | 235 / 243 `[est]` | 0.20 | fixed (cluster diff-throttle) | 300 | 600 | 101 | B |
| K-845 "Mule" | Merlin 1D | T0 | GG pump-fed kerolox | LOX/RP1 2.36 | 470 | 845 / 914 | 282 / 311 | 0.40 (landing variant) | ±5° | 20 | 2,500 | 101 | B |
| KV-981 "Mule-V" | Merlin Vacuum | T0 | GG pump-fed kerolox | LOX/RP1 2.36 | 630 `[est]` | — / 981 | 90† / 348 | 0.60 | ±3° | 10 | 1,500 | 20 | B |
| H-102 "Crane" | RL10C-1 | T0 | expander hydrolox | LOX/LH2 6.0 | 190 | — / 101.8 | 110† / 449.7 | 1.0 fixed | ±4° | 15 | 2,000 | 25 | C |
| HL-67 "Heron" | CECE (RL10 deriv.) | T1 | expander hydrolox lander | LOX/LH2 6.0 | 230 `[est]` | — / 67 | 120† / 445 | 0.06 | ±4° | 50 | 2,000 | 60 | C |
| H-2280 "Shire" | RS-25 | T1 | staged-comb hydrolox | LOX/LH2 6.0 | 3,177 | 1,860 / 2,279 | 366 / 452 | 0.67 | ±10.5° | 55 | 27,000 | 101 | C |
| M-2256 "Drayhorse" | Raptor 2 | T1 | FFSC methalox | LOX/LCH4 3.6 | 1,630 | 2,256 / 2,394 | 327 / 347 | 0.40 | ±15° | 50 | 5,000 | 101 | B |
| MV-2530 "Drayhorse-V" | Raptor Vacuum | T1 | FFSC methalox | LOX/LCH4 3.6 | 2,100 `[est]` | — / 2,530 `[est]` | 100† / 380 `[est]` | 0.40 | ±3° | 50 | 5,000 | 40 | B |
| M-733 "Bantam" | Rocket Lab Archimedes | T1 | ORSC pump-fed methalox | LOX/LCH4 3.6 | 750 `[est]` | 733 / 765 `[est]` | 315 / 329 `[est]` | 0.40 | ±5° | 20 | 2,500 | 101 | B |
| MV-815 "Bantam-V" | Archimedes vac variant | T1 | ORSC pump-fed methalox | LOX/LCH4 3.6 | 900 `[est]` | — / 815 `[est]` | 95† / 367 `[est]` | 0.50 | ±3° | 10 | 1,500 | 30 | B |
| ML-24 "Gopher" | NASA Morpheus HD | T2 | pressure-fed methalox lander | LOX/LCH4 3.6 | 80 `[est]` | 22 / 24 | 295 / 320 `[est]` | 0.25 | ±5° | 500 | 3,000 | 101 | B |
| ML-111 "Badger" | Masten Broadsword 25K deriv. | T2 | GG pump-fed methalox lander | LOX/LCH4 3.6 | 240 `[est]` | 95 / 111 | 300 / 355 `[est]` | 0.15 | ±8° | 250 | 4,000 | 101 | B |

"—" thrust-SL entries: compute F_SL = ṁ·g0·Isp_SL per §2.2. T/W sanity anchors: Merlin ≈183,
Raptor 2 ≈141, RS-25 ≈73, RL10C ≈55, Bantam ≈100, ML-111 ≈47.

### 1.2 Nuclear-thermal engines (doc §4.3 — T2 unless noted, cost class D, H2 baseline)

| ID / name | Anchor | Dry kg | F vac kN | Isp vac s | Isp SL s | Reactor MWt (canonical) | x_min | Gimbal | Ign | Burn s | p_max kPa | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NTR-73 "Prometheus" | SNRE / DRACO-class | 2,400 (+1,500 shadow-shield option) | 73 | 900 | 750† | 367 | 0.25 | ±3° | 30 | 16,200 | 30 | LANTR option +250 kg: Isp 645 s, thrust ×2.75, LOX O/F 3.0 |
| NTR-246 "Prometheus-H" | NERVA XE' modernized | 12,500 | 247 | 850 | 700† | 1,140 (catalog wins over formula's 1,211) | 0.25 | ±3° | 30 | 10,800 | 30 | heavy tug core, Act 3–4 |
| NTR-111B "Prometheus-B" | Borowski BNTR @ DRA 5.0 25-klbf | 3,100 incl. Brayton+radiator (+1,500 shield; 4.6 t shielded) | 111 | 900 | 750† | 575 | 0.25 | ±3° | 30 | 16,200 | 30 | **T3.** Bimodal +25 kWe idle; no export while thrusting; no LANTR option |

NTR T/W: 3.1 / 2.0 / 3.7 (2.5 shielded) — deliberately poor; space-only tugs. No NTR < 60 km
altitude on Earth (hard regulatory rule → mission-ending event, doc 12). Launch cold; first
criticality in orbit. p_max 30 kPa allows Mars NIMF hops, not Titan surface (147 kPa).

NTR alternate propellants (any single fluid; Isp = k × that engine's Isp_H2; Isp_SL scales by same k):

| Propellant | k | Isp on NTR-73 (s) | Wear mult | Anchor |
|---|---|---|---|---|
| Hydrogen | 1.00 | 900 | ×1 | NERVA/SNRE baseline |
| Methane | 0.67 | 600 | ×4 | NERVA-era studies (coking) |
| Ammonia | 0.50 | 450 | ×1.5 | NERVA alternate-prop studies |
| Water | 0.38 | 340 | ×1.2 | "steamer" studies |
| CO2 | 0.295 | 265 | ×2 | Zubrin NIMF hopper |

Constant reactor power: `F_alt = F_H2 / k`, `ṁ_alt = ṁ_H2 / k²` (denser prop → more thrust, less Isp).

### 1.3 Electric thrusters (doc §4.4 — per string = thruster + PPU + feed; ±10° gimbal mount included)

Sim computes thrust from `T = 2ηP/(g0·Isp)`; the table is display data (every row consistent within rounding).

| ID / name | Anchor | Tier | Propellant | P_in kW | Thrust | Isp s | η | String kg | Rated throughput kg | Cost |
|---|---|---|---|---|---|---|---|---|---|---|
| ION-2 "Mayfly" | NSTAR (DS1/Dawn) | T0 | Xenon | 2.3 | 92 mN | 3,120 | 0.61 | 30 | 235 | C |
| ION-7 "Dragonfly" | NEXT (DART) | T1 | Xenon | 6.9 | 236 mN | 4,190 | 0.70 | 58 `[est]` | 918 | C |
| HALL-1 "Wren" | SPT-100 | T0 | Xenon | 1.35 | 83 mN | 1,600 | 0.48 | 12 | 170 | B |
| HALL-12 "Harrier" | AEPS/HERMeS | T1 | Xenon | 12.5 | 590 mN | 2,800 | 0.65 | 115 `[est]` | 1,700 | C |
| HALL-12A "Harrier-A" | krypton-Hall heritage (A8 registration) | T2 | Argon | 12.5 | 480 mN | 2,400 | 0.45 | 115 `[est]` | 1,500 `[est]` | C |
| HALL-100 "Condor" | X3 nested Hall | T3 | Xenon or Argon (η −0.06) | 100 | 5.4 N | 2,000 | 0.52 | 460 `[est]` | 5,000 `[est]` | D |
| MPD-200 "Albatross" | NASA Lewis / MAI MPD | T3 | Argon (NH3 η −0.05; H2 η −0.05 & Isp +25%) | 200 | 4.6 N | 4,000 | 0.45 | 900 `[est]` | 20,000 `[est]` | D |
| VAS-200 "Petrel" | VASIMR VX-200 | T3 | Argon | 200 | 5.7 N @4,900 s | 3,000–12,000 variable | 0.69 @4,900 | 650 `[est]` | 30,000 `[est]` | D |

VASIMR Isp slider (constant power, η linear-interpolated between set points):

| Isp setting | 3,000 s | 4,900 s | 12,000 s |
|---|---|---|---|
| η | 0.45 | 0.69 | 0.76 |
| Thrust @200 kW | 6.1 N | 5.7 N | 2.6 N |

Waste-heat split to ship radiators (09 interface): ion/Hall 10% of P_in, VASIMR 15%, MPD 30%.
EP mega-clusters: per-BANK failure/wear bookkeeping, not per-string (DECISIONS C25).

### 1.4 Solar sails (doc §4.5 — module = film + booms + actuators)

| ID | Anchor | Tier | Area m² | Mass kg | F @1 AU, θ=0 | Cost | Role |
|---|---|---|---|---|---|---|---|
| SAIL-86 | NEA Scout | T1 | 86 | 12 | 0.66 mN | B | smallsat scouting |
| SAIL-1650 | NASA Solar Cruiser | T2 | 1,653 | 90 | 12.8 mN | C | station-keeping, sunward cargo |
| SAIL-10K | scaled NIAC/JPL class | T3 | 10,000 | 250 `[est]` | 77 mN | C | slow bulk tug (0.1 mm/s² on 750 kg ≈ 8.9 m/s per day) |

### 1.5 T4 endgame drives — all `[SPECULATIVE]`

| ID | Anchor | Thrust | Isp s | Power / fuel | Mass | Role |
|---|---|---|---|---|---|---|
| DFD-5 "Helios" | Princeton DFD | 20 N | 10,500 | 5 MW fusion, He3+Hydrogen; exports 1 MWe to bus | 10 t `[concept]` | crewed outer-system clipper |
| FFR-43 "Phoenix" | Werka NIAC FFRE 2012 | 43 N | 527,000 | ≈1 GWt fission core; Uranium | 113 t `[concept]` | precursor probe drive (≈12 km/s Δv per year) |
| PULSE-D "Daedalus" | BIS Daedalus 1978 | 7,500 kN | ≈1,000,000 | He3/D ICF pellets, 250 Hz | ≈1,700 t assembly | Endgame megaproject ONLY — not a buildable ship part |

### 1.6 RCS blocks (doc §4.7 — 4-nozzle cross modules)

| ID | Anchor | Tier | Propellant | F per nozzle N | Isp s | Block kg | Rated total impulse N·s | Cost | Notes |
|---|---|---|---|---|---|---|---|---|---|
| RCS-N10 | industry cold-gas | T0 | Nitrogen (COPV, f_tank 0.80) | 10 | 70 | 8 | 2×10⁵ | A | smallsats |
| RCS-D400 | SpaceX Draco | T0 | NTO/MMH 1.65 | 400 | 300 | 22 | 5×10⁶ | B | workhorse; ullage-capable |
| RCS-M2K | Starship hot-gas | T1 | gaseous LOX/LCH4 from main tanks | 2,000 | 270 `[est]` | 60 | 2×10⁷ | B | no separate RCS propellant |

### 1.7 Tanks, depots, transfer hardware, cryocoolers, sunshields (doc §4.8)

Catalog masses are canonical and override §2.13 parametric fractions where they differ.
Depots are ASSEMBLIES of constituent parts (no own recipe/cost class).

| ID | Tier | Capacity | Dry mass | Power | Cost | Notes |
|---|---|---|---|---|---|---|
| Tank parts (parametric) | T0+ | player-sized | per §2.13 f_tank | heaters per §2.10 | A | every propellant |
| PTC-200 coupler | T1 | n/a | 150 kg | 0.1 kWe pumping | B | 5 kg/s cryo / 20 kg/s storable / 0.5 kg/s gas |
| PTC-300L LAD coupler | T3 | n/a | 250 kg | 0.2 kWe pumping | C | cryo transfer WITHOUT settling at 3 kg/s (60% rate); storable/gas as PTC-200 |
| ZBO-90 cryocooler | T1 | lifts 50 Wt @90 K | 25 kg | 0.75 kWe; rejects 0.8 kWt | C | LOX/LCH4/LAr; on LH2 tank = shield-stage interceptor: Q_leak ×0.25 (max one per tank) |
| ZBO-20 cryocooler | T1 | lifts 20 Wt @20 K | 90 kg | 2.0 kWe; rejects 2.0 kWt | C | LH2 only |
| SUN-1 sunshield | T1 | shades ≤120 m² | 500 kg | passive | B | q_env ×0.25; deploy/retract 1 h; destroyed by atmosphere or accel >0.2 m/s² |
| SUN-4 sunshield | T2 | shades ≤900 m² | 2,500 kg | passive | B | DEP-600-class; same rules |
| DEP-60 "Cache" | T1 | 60 t methalox (13 t CH4 + 47 t LOX) | 6.5 t (incl. SUN-1, 2×ZBO-90, 2×PTC-200) | 1.6 kWe | assembly | LEO/LLO node |
| DEP-600 "Reservoir" | T2 | 600 t methalox or 150 t LH2 | 62 t (incl. SUN-4, 4×ZBO-90 + 2×ZBO-20, 4×PTC-200) | 3.0–5.5 kWe | assembly | net-zero boiloff ≤1 AU powered; LH2 mode via staged cooling |

### 1.8 Propellant properties (doc §4.1 — extends canonical resource list with RP1, NTO, MMH)

RP1 Earth-only forever. NTO/MMH Earth-import until T3 ISRU routes (B11: Ammonia→MMH;
N2+O2→NTO; recipes owned by doc 04). Solid propellant is NOT a resource (sealed parts).

| Resource | Stored as | Density kg/m³ | Store T K | Cryo? | Notes |
|---|---|---|---|---|---|
| LOX (Oxygen) | liquid | 1,141 | 90 | yes | ISRU everywhere |
| LH2 (Hydrogen) | liquid | 70.8 | 20 | deep | worst boiloff, biggest tanks |
| LCH4 (Methane) | liquid | 423 | 111 | yes | Sabatier ISRU; Titan native |
| RP1 | liquid | 815 | ambient | no | gels < 226 K; Earth-only |
| NTO | liquid | 1,442 | ambient | no | freezes < 262 K (heaters) |
| MMH | liquid | 875 | ambient | no | freezes < 221 K |
| Xenon | supercritical gas | 1,580 | ambient | no | COPV ~86 bar; rare |
| Argon | liquid | 1,395 | 87 | yes | cheap EP propellant |
| Nitrogen | gas 300 bar | 300 | ambient | no | cold-gas RCS |
| Water | liquid | 1,000 | ambient | no | NTR alternate; freezes < 273 K |
| Ammonia | liquid | 682 | 240 | no | NTR alternate + MPD prop |
| CO2 | liquid sat. | 1,166 | 220 | no | NIMF hopper prop; ≈600 kPa @220 K |

Locked O/F mass ratios (must match doc 04 ISRU chains): LOX:RP1 = 2.36 · LOX:LH2 = 6.00 ·
LOX:LCH4 = 3.60 · NTO:MMH = 1.65. (Tank mixture mass fractions: ox/(1+O/F)·O/F, fuel/(1+O/F):
methalox 0.783/0.217, kerolox 0.702/0.298, hydrolox 0.857/0.143, hypergol 0.623/0.377.)

### 1.9 Cost classes
A consumable · B mass-produced (T1 factory) · C precision aerospace (Earth import / T2 orbital fab)
· D nuclear/exotic (regulatory event + Uranium license, or T3 fab) · E megaproject. Money in doc 12.

### 1.10 Tier unlocks (doc §6)

| Tier | Unlocks |
|---|---|
| T0 | SRM-2, SRM-49, OMS-27, SPS-91, K-845, KV-981, H-102, ION-2, HALL-1, RCS-N10, RCS-D400, basic tanks |
| T1 | M-2256, MV-2530, M-733, MV-815, LND-71, HL-67, H-2280, DEP-60/600, PTC-200, ZBO-90/20, SUN-1/4, PMD, ION-7, HALL-12, RCS-M2K, SAIL-86, Mature-engine upgrades |
| T2 | NTR-73, NTR-246, LANTR option, ML-24, ML-111, NTR alternate props, HALL-12A, SAIL-1650, depot-grade insulation |
| T3 | HALL-100, MPD-200, VAS-200, NTR-111B, SAIL-10K, NTR space refurbishment, PTC-300L |
| T4 | DFD-5, FFR-43, PULSE-D megaproject |

---

## 2. MECHANICS — code-ready formulas

### 2.1 Rocket equation / staging (doc §3.2)
```
Δv_s     = g0 · Isp_eff · ln(m_start / m_end)                 [m/s]
Isp_eff  = ΣF_i / Σ(F_i / Isp_i)                              [s]    (thrust-weighted, mixed engines)
ṁ_i      = F_vac,i / (g0 · Isp_vac,i)                         [kg/s] (constant; throttle scales)
t_burn   = m_prop / Σ(x_i · ṁ_i)                              [s]
ṁ_ox     = ṁ · O/F / (1 + O/F);   ṁ_fuel = ṁ / (1 + O/F)      [kg/s]
```
Engine cuts off when EITHER commodity is exhausted; UI flags limiting propellant.
Worked anchor: NTR tug 28 t dry + 42 t LH2 @ Isp 900 → Δv 8,090 m/s; ṁ 8.27 kg/s; 5,080 s burn.

### 2.2 Thrust/Isp vs ambient pressure (doc §3.3 — linear back-pressure model)
```
ṁ      = F_vac / (g0 · Isp_vac)                               (pressure-independent)
Isp(p) = Isp_vac − (Isp_vac − Isp_SL) · (p_amb / 101.325)     [s; p_amb in kPa]
F(p)   = ṁ · g0 · Isp(p)                                      [N]
```
- Extrapolates above 1 atm (Venus). If `F(p) ≤ 0.3·F_vac` → CANNOT IGNITE (flow separation).
  Consequence: no chemical ascent from Venus surface; aerostat band ~50–55 km flyable.
- Vacuum-rated engines: ignition inhibited above catalog `p_max`. Player override: wear ×20
  while overridden + 2% per second chance of immediate engine-out.
- Every row (incl. NTRs) carries Isp_SL — synthetic (†) for vac engines so Isp(p)/F(p)/0.3-check
  compute at any pressure.

### 2.3 Throttle (doc §3.4)
```
x ∈ [x_min, 1.0] scales ṁ linearly.
Isp(x) = Isp · (1 − 0.08 · max(0, 0.6 − x) / 0.6)             (off-design penalty below 60%)
```
Throttle command < x_min clamps to 0 (engine off — no sub-idle hover). Solids: x=1 fixed, no
shutdown/restart. EP throttles 0.2–1.0 continuously, NO Isp penalty (power scales instead).

### 2.4 Ignition gates (doc §3.5 — ALL must hold)
1. Wear w < 2.0 (rated ignition counts are wear normalizers, never hard inhibits).
2. Ullage (pump-fed liquids only): longitudinal accel ≥ 0.005 m/s² sustained 3 s, OR every feeding
   tank has PMD (+2% tank dry mass; only tanks ≤ 20 t). Pressure-fed/solid/cold-gas/EP exempt.
3. Chilldown (cryo pump-fed, > 1 h since last burn): consume 5 s of rated ṁ as vented propellant
   before thrust ramps (thrust exactly 0 during those 5 s).
4. Propellant unfrozen AND every feeding tank pressure NOMINAL (m_gas < 0.005 × capacity, §2.10).
5. Reliability roll passes (§2.12).

### 2.5 Gimbal / control authority (doc §3.6) and TWR rules (doc §3.7)
```
τ = F · sin(δ_cmd) · L          [N·m]   |δ_cmd| ≤ δ_max (catalog)
TWR_local = ΣF(p_amb) / (m · g_local)
```
Builder red warning when stage pitch authority τ_max < 1.5× worst-case one-engine-out torque.
TWR rules: Earth/Mars/Titan launch TWR > 1.0 (warn < 1.2, recommend 1.3–1.5 Earth); airless
launch > 1.0 strict, recommend ≥ 1.8; powered landing TWR_local > 1.0 at touchdown body; deep
space no minimum (planner warns t_burn > T_orbit/6, owned by doc 01); low-thrust planner uses
spiral estimate Δv ≈ |v_c,start − v_c,end|. Earth pad→LEO locked budget: 9,400 m/s.

### 2.6 Solids (doc §3.8)
Constant rated average thrust for t_burn; no stop/throttle/restart/refuel; jettison-while-burning
forbidden. Age > 10 years → ignition failure probability ×5.

### 2.7 Electric propulsion triangle (doc §3.9 — locked coupling)
```
T   = 2 · η · P / (g0 · Isp)                  [N]
ṁ   = 2 · η · P / (g0 · Isp)²                 [kg/s]
P/T = g0 · Isp / (2 · η)                      [W/N]    (NSTAR ≈ 25 kW/N)
```
- P = delivered bus power; thrust scales with delivered P; below 20% of rated P → thruster drop-out.
- Atmosphere inhibit: requires p_amb < 0.01 kPa; running thruster shuts down benignly above.
- Propellants: gridded ion + small Hall = Xenon only. HALL-100/MPD/VASIMR accept Argon; MPD also
  Ammonia (η −0.05) or Hydrogen (η −0.05, Isp +25%).
- Wear: w = kg processed / rated throughput. No ignition count, no per-ignition roll.

### 2.8 NTR model (doc §3.10)
- Reactor thermal: `P_t ≈ F·ve/(2·0.85)` is design-time only; catalog MWt is CANONICAL for UI + dose.
- LANTR mode (T2 module, +250 kg): LOX injection O/F 3.0 → Isp 645 s, thrust ×2.75; in-flight toggle;
  draws LOX (3 kg per kg H2).
- Bimodal (NTR-111B only): idle 115 kWt → +25 kWe bus export, no propellant use, no wear accrual;
  no export while thrusting; idle→thrust = 15-min ramp (replaces 45-min lockout); thrust→idle only
  after 2-h cooldown completes. Idling dose factor: (0.115/367) in place of (P_t/367)·x.
- Shadow shield (optional 1,500 kg): safe cone half-angle 12°, apex at reactor. Off-cone dose:
  `D = 1e4 Sv/h · (P_t / 367 MWt) · x · (25 m / r)²`; in-cone 0.1 mSv/h at full power, same scaling.
  Constant is locked — soften only by buying 4π secondary shield mass.
- Cooldown: after each burn, auto trickle-flow 1.5% of mass-just-burned over 2 h at Isp 350 s
  (integrator applies the small accel). No feed propellant available → wear +0.25.
- Restart: 45-min minimum lockout (thermal). No operation < 60 km Earth altitude.

### 2.9 Solar sail law (doc §3.11)
```
F_sail = 9.08e-6 N/m² · η_s · A · cos²θ · (1 AU / r)²         [N]   along sail normal, anti-sun
```
η_s = 0.85 new; degrades 0.01/year. |θ| ≤ 60° (player scalar). Inside 0.25 AU: 1% area damage/h.
Deployed sail destroyed by atmosphere or stack accel > 0.2 m/s²; retract takes 1 h.
Auto modes: spiral out/in = θ ∓35°, hold = 0°.

### 2.10 Boiloff (doc §3.12)
```
Q_leak = q_env · k_ins · k_T · A_tank          [W]      A_tank = sphere-equivalent area of capacity
ṁ_boil = Q_leak / h_vap                        [kg/s]   auto-vented (lost) by default
k_T    = 1.0 for 20 K cryogens (LH2); 0.5 for ≥77 K (LOX, LCH4, LN2, LAr)
k_ins  = 20 bare ascent tank · 1.0 standard MLI · 0.25 depot-grade (+0.03 tankage fraction)
```
q_env decision tree (first match wins, exactly one always matches):
1. Landed on listed surface: Lunar day 2.0 (T_amb 390 K) · Lunar night/PSR 0.05 (95 K, PSR ~40 K) ·
   Mars 0.6 (210 K) · Titan 0.3 (94 K).
2. Else r < 1.5 AU: `q_env = (1 AU/r)²` capped at 3.0; ×0.25 if sunshield deployed.
3. Else 1.5 ≤ r < 3 AU: 0.4 (0.10 with sunshield or permanent shadow).
4. Else r ≥ 3 AU: 0.03.
Cold-ambient clamp: surface T_amb ≤ cryogen storage T → Q_leak = 0 (Titan: LCH4 free, LOX nearly).

| Cryogen | Store T K | h_vap kJ/kg |
|---|---|---|
| LH2 | 20 | 446 |
| LCH4 | 111 | 511 |
| LOX | 90 | 213 |
| LN2 | 77 | 199 |
| LAr | 87 | 161 |

Verified anchors: 50 t LH2 sphere in LEO, std MLI → 383 W → 74 kg/day → 4.4%/month (with shield +
depot insulation 0.28%/month). 50 t methalox same → ≈0.85%/month. %/month scales as m^(−1/3).

Active ZBO:
```
P_elec = SP · Q_lift          SP = 15 We/Wt @90 K, 100 We/Wt @20 K
Net boiloff = max(0, Q_leak,eff − Σ Q_lift where T_stage ≤ T_store) / h_vap
```
Only coolers with cold-head T ≤ tank storage T count (second law). Staged cooling: one powered
ZBO-90 on an LH2 tank = interceptor, Q_leak ×0.25 before the 20 K stage (max one multiplier/tank).
ZBO rejects P_in + Q_lift as waste heat (09 ledger).

Storables freeze: NTO < 262 K, MMH < 221 K, RP1 gels < 226 K, Water < 273 K. Heater demand
50 W per tonne of propellant; frozen → engines inoperable; thaw = 6 h at double heater power.

Tank overpressure surrogate (venting disabled by player): accumulate m_gas at ṁ_boil.
NOMINAL m_gas < 0.005·capacity → OVERPRESSURE alarm (ignition blocked) ≥ 0.005 → BURST ≥ 0.02
(module destroyed, 06 damage). Re-enable venting: dumps m_gas over 60 s → NOMINAL.
Warp: boiloff integrates analytically (closed-form linear drain, tank-empty event scheduled).

### 2.11 Propellant transfer & depots (doc §3.13)
- Requires docked PTC-200 coupler path or base plumbing (07).
- Rates per coupler: storables 20 kg/s · cryogens 5 kg/s · gases (Xe/N2/Ar gas) 0.5 kg/s.
- Cryo settling: ullage accel ≥ 0.0005 m/s² for the duration (≈50 N per 100 t stack RCS trickle),
  OR PTC-300L LAD coupler at 60% rate (3 kg/s). Settling lost mid-transfer → transfer pauses.
- Chilldown loss: into a warm tank (empty > 24 h) vents 1.5% of transferred mass.
- Solids and sealed items not transferable.
- Depot = tanks + ZBO + sunshield + couplers assembly. Powered ZBO ≥ Q_leak → holds cryogen
  indefinitely; power loss → passive boiloff + alarm. Depot propellant is the standard tradable
  good (price = production + logistics, doc 12).

### 2.12 Reliability & wear (doc §3.14)
```
Chemical/NTR:  w = 0.6·(t_burned / t_rated) + 0.4·(n_ign / n_rated)
EP:            w = m_throughput / m_rated
RCS:           w = (N·s delivered) / (rated total impulse)

p_ignition_fail = p_base · (1 + 9·w²)
λ_inflight      = λ0    · (1 + 9·w²)        [per second of burn]
```

| Engine class | p_base /ignition | λ0 /s |
|---|---|---|
| Solid | 0.001 | 2×10⁻⁶ |
| Pressure-fed liquid | 0.0005 | 5×10⁻⁷ |
| Pump-fed liquid (new type) | 0.002 | 2×10⁻⁶ |
| Pump-fed liquid (Mature) | 0.0005 | 5×10⁻⁷ |
| NTR | 0.003 | 1×10⁻⁶ |
| Electric | 0.0002 | 1×10⁻⁸ |

- Mature = 25 program-wide successful ignitions of the TYPE ([PLAYTEST] per DECISIONS E) →
  p_base AND λ0 ÷4, for EVERY class.
- Rated burn/ignition counts are normalizers only; ignition always permitted while w < 2.0;
  multiplier grows unbounded.
- RCS: no per-pulse roll; one λ-check per maneuver (Electric-class λ0); failures always benign.
  Pulses < 0.1 s pay Isp ×0.9 (§3.15). Sizing: α = Σ(F·L_i)/I_stack ≥ 0.02 rad/s² for "responsive".
- Failure outcome (chemical/NTR): 70% benign shutdown (one restart attempt @25% success, else dead),
  25% permanently dead, 5% energetic (engine destroyed; each adjacent module 50% damage roll).
  Solids: 60% thrust anomaly (±20% rest of burn), 40% energetic. EP: always benign.
- Maintenance: workshop + crew/robot arm refurbishes at 20% of MachineParts build cost → w = 0.2.
  Past w = 2.0: scrap only (50% material recovery). RNG from deterministic mission seed (13).
- DECISIONS A5 composition (Phase-1 interface test): total reliability = (02 wear base) ×
  (11 maturity ÷4 factor) × (05 spares/MTBF k_env). Multiplicative, never restated cross-doc.

### 2.13 Mass & cost model (doc §3.16)

Tankage fractions f_tank (dry/capacity; pressurant+plumbing+MLI abstracted in):

| Tank type | f_tank |
|---|---|
| RP1/storables pump-fed feed | 0.06 |
| Storables pressure-fed feed | 0.10 |
| Kerolox/methalox launch tank (bare, k_ins 20) | 0.05 |
| Methalox/LOX in-space, std MLI | 0.065 |
| LH2 in-space, std MLI | 0.12 |
| LH2 launch tank bare | 0.085 |
| Water | 0.02 |
| Ammonia | 0.06 |
| CO2 pressurized | 0.10 |
| LN2 cryo | 0.08 |
| Depot-grade option (any cryo) | +0.03 (k_ins ×0.25) |
| Xenon COPV | 0.05 |
| Argon cryo | 0.08 |
| Nitrogen cold-gas COPV 300 bar | 0.80 |
| PMD option (tanks ≤ 20 t) | f_tank × 1.02 |

Build recipes (kg per kg dry mass, → doc 05): pump-fed engine 0.45 MachineParts/0.25 IronSteel/
0.10 Cu/0.10 Ti/0.10 Electronics · pressure-fed 0.30 MP/0.30 Fe/0.20 Ti/0.10 Poly/0.05 Cu/0.05 El ·
solid (gross mass) 0.20 MP/0.30 Al/0.50 Poly, Earth or T3 chem plant only · NTR 0.30 MP/0.25 Fe/
0.10 Ti/0.10 C/0.10 El/0.05 Cu/0.05 Uranium(HALEU)/0.05 SP · EP string 0.35 El/0.20 Cu/0.20 MP/
0.10 Ti/0.10 RareEarths/0.05 Si · tanks 0.70 Al/0.15 MP/0.15 Poly (COPV 0.35 C/0.25 Ti/0.20 Poly/
0.20 MP) · sail 0.50 Poly/0.20 Al/0.20 MP/0.10 El · RCS = pressure-fed mix · PTC/ZBO 0.30 MP/
0.25 Fe/0.20 Cu/0.15 El/0.10 Ti · sunshield 0.55 Poly/0.30 Al/0.10 SP/0.05 MP.

### 2.14 Plume–surface scouring (doc §3.17, DECISIONS C23 — cone/threshold ONLY)
```
p_plume = F(p_amb) · x / (π · (h · tan 15°)²)        [Pa]   h = nozzle height above terrain
h_scour = sqrt(F·x / (π · p_crit)) / tan 15°         [m]    scour-onset height
```
p_crit: loose regolith/dust 1 kPa · compacted site 10 kPa · bare rock/ice 30 kPa · sintered pad
300 kPa. While scouring: burning engine wear ×2 (FOD); ejecta consequences owned by docs 10/07
(radius scale ×1 airless, ×0.5 Mars, ×0.1 Titan). One height test per burning engine per tick.

### 2.15 Failure modes checklist (doc §8 — each must be implemented/tested)
1 vac engine in atmo (inhibit/override 20× wear + 2%/s) · 2 Venus deep-atmo no-ignite ·
3 propellant freeze/thaw · 4 overpressure→burst · 5 boiloff-to-empty under warp (analytic event) ·
6 either-commodity depletion benign shutdown · 7 ullage collapse pauses/aborts (no roll consumed) ·
8 engine-out asymmetry → tumble · 9 energetic adjacency damage · 10 NTR dose/cooldown/lockout/
regulatory · 11 EP brownout drop-out · 12 EP throughput wear-out · 13 sail thermal+accel limits ·
14 stale solids p_ign ×5 · 15 cold-soak chilldown Δv tax · 16 depot power loss → passive + alarm ·
17 warm-tank transfer 1.5% loss · 18 sub-x_min clamps to 0; zero thrust during chilldown ·
19 plume scour below h_scour.

### 2.16 UI obligations (doc §5 — builder/flight/logistics surfaces this spec implies)
- Builder Δv panel: per-stage Δv/Isp_eff/wet-dry/t_burn/limiting-propellant; TWR per body dropdown;
  pressure context toggle (vac / SL / custom kPa); boiloff %/month forecast per cryo tank incl.
  ZBO power cross-check. Hard warnings: LOW TWR, CONTROL AUTHORITY, NO ULLAGE PATH, VACUUM ENGINE
  IN ATMOSPHERE PROFILE, SHADOW SHIELD VIOLATION, EP POWER SHORTFALL, HYPERGOL FREEZE RISK.
- Flight: per-engine throttle/gimbal-lock/wear bar/ign count/health (OK·SHUTDOWN·DEAD·DESTROYED)/
  restart (greyed in NTR lockout); NTR-111B THRUST/POWER/OFF selector with 15-min ramp countdown;
  NTR cone overlay + dose meter; sail θ dial + auto modes; chemical burns cap warp at 4×,
  EP/sail/NTR-trickle integrate analytically under warp.
- Logistics: transfer UI (rates, chilldown loss, settling status SETTLED/LADs/NOT SETTLED);
  depot dashboard (fill, Q_leak vs ΣQ_lift, net kg/day, alarms). Alarms owned: BOILOFF VENTING,
  TANK OVERPRESSURE, PROPELLANT FROZEN, ZBO POWER LOST, ENGINE WEAR CRITICAL (w>0.8),
  IGNITION FAILURE, ENERGETIC ENGINE FAILURE, SAIL THERMAL LIMIT.

### 2.17 Open questions still unresolved (doc §9)
Q4 solid kick-stage spin-up cost · Q5 DEP-600 LEO drag-makeup budget · Q7 LANTR for NTR-246 ·
Q8 aerospike (excluded) · Q9 H-2280 relevance post-methalox.

---

## 3. GAP vs CODE

### 3.1 What exists (verified in repo)

| Area | File(s) | State |
|---|---|---|
| 16 chemical-engine parts | `data/core/parts/engine_{oms27,sps91,lnd71,k845,kv981,h102,hl67,h2280,m2256,mv2530,m733,mv815,ml24,ml111}.toml` | All 14 liquid chemical rows present with correct thrust/Isp/Isp_SL/x_min/gimbal/O/F mass fractions matching the doc |
| NTR part | `data/core/parts/engine_ntr_k2.toml` | "K-2 Kingfisher (NERVA-D)" 245 kN / 900 s / 2.3 t — NOT a doc engine. Closest is NTR-246 (247 kN / 850 s / 12,500 kg); K-2's 2.3 t mass and Isp_SL 380 contradict the catalog |
| T4 part | `data/core/parts/engine_torch_d1.toml` | "D-1 Daystar fusion torch" 120 kN / 8,000 s — NOT in doc; doc's DFD-5 is 20 N / 10,500 s. Off by ~6,000× on thrust |
| Tanks (16) | `tank_{ml_s,ml_m,ml_l,ml_xl,kl_m,lh2_m,lh2_l,lox_m,ch4_m,hyp_s,h2o,n2,xe_s,xe_l,depot}.toml` | Fixed-size tanks, correct mixture fractions; `tank_depot` = 200 t methalox / 14 t dry (doc has DEP-60 60 t / DEP-600 600 t assemblies instead) |
| Stage math | `aphelion/sim/vessels/vessel.py` `stage_stats()` | Thrust-weighted Isp_eff, Δv vac/SL, TWR vac/SL, burn_s — matches §2.1; linear atmosphere interpolation via `atmosphere_frac` matches §2.2 with frac = p/101.325 |
| Min throttle | `vessel.py` `min_throttle()` | Reads `throttle[0]`; no Isp penalty curve, no clamp-to-zero semantics |
| Propellant drain | `vessel.py` `drain_propellant()` | Proportional across active-stage tanks; NO per-engine O/F split, no either-commodity cutoff/limiting-propellant flag |
| Transfer | `aphelion/sim/vessels/docking.py` `transfer_resource()` | Instantaneous, capacity/mixture-aware; NO coupler requirement, rate limits, settling, chilldown loss, gas-vs-cryo rates |
| Live ascent | `aphelion/sim/flight/ascent_live.py` | Flies §2.2 pressure model + staging; ignition is a bare flag — no ignition gates, failure rolls, or chilldown |
| Costs | `aphelion/sim/economy.py` | Heuristic part pricing from thrust/Isp; no A–E cost classes, no §2.13 build recipes |
| Power bus | `aphelion/sim/power.py` | Exists (09 domain) — EP/ZBO/heater loads not wired to propulsion |
| Condition field | `vessel.py` `PartRow.condition` | String "OK" placeholder; nothing sets SHUTDOWN/DEAD/DESTROYED from a reliability model |

### 3.2 What is missing entirely (no code, no parts)

| Missing system | Spec section | Notes |
|---|---|---|
| Solid motors (SRM-2, SRM-49) | §1.1, §2.6 | No solid parts; no sealed-propellant part semantics, no no-restart/no-jettison rules, no aging ×5 |
| Electric propulsion — ALL of it | §1.3, §2.7 | No ION/HALL/MPD/VASIMR parts; no T=2ηP/(g0·Isp) coupling, power-throttled thrust, brownout, waste-heat split, VASIMR slider, per-bank bookkeeping (C25) |
| Solar sails | §1.4, §2.9 | No parts, no force law, no θ control, degradation, thermal/accel limits |
| RCS blocks | §1.6, §2.12 | No RCS parts, ullage/settling provider, total-impulse wear, per-maneuver check, responsiveness sizing |
| Real T4 drives (DFD-5/FFR-43/PULSE-D) | §1.5 | Placeholder torch_d1 contradicts catalog; replace or rename |
| Doc-conformant NTRs + NTR mechanics | §1.2, §2.8 | NTR-73/246/111B rows; alternate-propellant k-table, LANTR, bimodal, shadow shield + dose law, cooldown trickle, 45-min lockout, <60 km Earth rule |
| Boiloff economy | §2.10 | No Q_leak/q_env/k_ins/k_T/h_vap anywhere; no venting, overpressure surrogate, freeze/heaters, analytic warp drain. Tank TOMLs have no insulation/area fields ("ZBO" appears only in tank names) |
| Depot hardware & mechanics | §1.7, §2.11 | No PTC-200/300L, ZBO-90/20, SUN-1/4, DEP-60/600 assemblies; no transfer rates/settling/chilldown-loss; `tank_depot` is a lone oversized tank |
| Reliability & wear model | §2.12 | No w, p_base/λ0 tables, (1+9w²), outcome rolls, Mature ÷4, refurbishment, A5 composition test |
| Ignition gating | §2.4 | No ullage/PMD, chilldown, frozen-prop, overpressure, or reliability-roll gates; no p_max field or vac-engine inhibit/override |
| Throttle Isp penalty + pulse rules | §2.3 | `Isp(x)` off-design curve and <0.1 s pulse ×0.9 absent |
| Plume scouring | §2.14 | No p_plume/h_scour test, p_crit classes, ×2 FOD wear |
| Propellant variety | §1.8 | No Argon/Ammonia/CO2/LAr/LN2 tanks or resources in parts; PMD/depot-grade/parametric tank options absent |
| Engine data schema gaps | §1.1 | TOMLs lack: rated ignitions, rated burn, p_max, cost class, feed type (pressure/pump/solid/EP/NTR), cycle, ullage-exemption flag, ignition-count, wear fields |
| Catalog/economy hooks | §1.9, §2.13 | Cost classes A–E, build recipes, tankage fractions, scrap/refurb economics |

### 3.3 Schema migration implied (engine TOML, additive)
`feed = "pump"|"pressure"|"solid"|"ntr"|"ep"`, `rated_ign`, `rated_burn_s`, `p_max_kPa`,
`cost_class`, `ep = {power_kW, eta, throughput_kg, family}`, `ntr = {reactor_MWt, lantr?, bimodal?}`,
`tank += {insulation = "bare"|"mli"|"depot", pmd = bool}`, `rcs = {nozzle_N, total_impulse_Ns}`,
`sail = {area_m2}`. Catalog masses canonical over parametric fractions (doc §4.8 rule).
