# BUILD SPEC — 06 Ships & Stations (Drydock 2D grid builder, full part catalog, stations)

Extracted from `design/06-ships-stations.md` (v2 catalog) with `design/DECISIONS.md` applied (A1 RP1 spelling, A8 engine registrations accepted, A10 aerostat envelope rows migrated to doc 07).
Engineer-facing: every formula, every part, every validation rule, plus the four worked builds as acceptance tests, plus the gap against current code.

Catalog count note: the doc's nominal "113 parts" is **110 buildable rows here + 3 aerostat rows (AR-ENV, AR-GON, AR-INF) migrated to doc 07's catalog per DECISIONS A10**. This doc keeps AR-SHELL/AR-CHUTE and a pointer.

Global constants: `g0 = 9.80665 m/s²` (exact, used for dv, TWR-Earth, ṁ — one constant everywhere). Masses stored in kg, displayed in t. 1 grid cell = 1 m × 1 m.

---

## 1. THE PART CATALOG (110 parts)

Column defaults (apply unless a row overrides):
- **Hull area** (MMOD §2.9): `2·(w+h)` m². **Frontal area** (drag): `w × 1` m², Cd = 2.2 for everything.
- **Attach nodes**: one `top`, one `bottom`, one radial node per edge cell (h-tall part has h `left[i]` + h `right[i]`). Overrides: engines/heat shields/aeroshells expose **no bottom node**; fairings expose interior payload nodes instead of exterior radial nodes; docking-port outward face mates only to a matching port; ST-TR8 exposes interior nodes (engines may fire through it).
- **Axial joint rating** by material class: STRUCT/TANK/HAB/ENGINE stack nodes **1,200 kN**; ELEC/SHIELD/MECH and all deployables **300 kN**; radial joints **25% of the smaller part's rating**. Explicit `axial` stats override. Engine stack node = `max(1,200 kN, 1.25 × rated vac thrust)`, and the engine-to-stack joint uses the engine's rating.
- **q_max**: streamlined stack part 50 kPa; radial pod/leg/stowed deployable 35 kPa; deployed wing/radiator/dish 0.5 kPa; deployed inflatable 1 kPa; chutes per catalog. **a_max**: 8 g axial / 3 g lateral default; inflatables 4 g axial deployed; chute deploy limits per part.
- **Cost** = baseline 2049 $M (12 owns final pricing). "resources" = ISRU-printed, costs inputs + shop time only.
- Wet mass = dry + listed capacity/fill where a Cap/fill column exists; otherwise wet = dry.

### 1.1 Structure (15) — class STRUCT

| ID | Name | Tier | Size w×h | Dry (t) | Cost $M | Key stats / special functions |
|---|---|---|---|---|---|---|
| ST-G1 | Girder segment | T0 | 1×1 | 0.08 | 0.05 | axial 1,200 kN |
| ST-G4 | Girder beam | T0 | 1×4 | 0.30 | 0.15 | axial 1,200 kN |
| ST-TR8 | Ship spine truss | T0 | 2×8 | 1.4 | 0.8 | axial 2,500 kN; OPEN: interior nodes, engines may fire through |
| ST-KEEL | Station keel truss | T1 | 2×10 | 9.0 | 6 | axial 4,000 kN; utility runs (power/fluid) |
| ST-IS3 | Interstage 3 m | T0 | 3×2 | 0.40 | 0.3 | axial 1,200 kN |
| ST-IS-V | Vented interstage | T1 | 3×2 | 0.55 | 0.5 | hot-staging permitted (E5 plume exemption through it) |
| ST-DC2 | Stack decoupler 2 m | T0 | 2×1 | 0.05 | 0.2 | SEPARATE event: 0.3 m/s relative along stack axis, inverse-mass split |
| ST-DC3 | Stack decoupler 3.7 m | T0 | 3×1 | 0.12 | 0.3 | same sep rule, 0.3 m/s relative axial |
| ST-RD | Radial decoupler | T0 | 1×1 | 0.03 | 0.15 | jettison booster outward: 1 m/s relative lateral, inverse-mass split |
| ST-FR3 | Fairing 3.7 m | T0 | 3×9 | 0.9 | 1.2 | interior 3×8 m usable; JETTISON event; interior payload nodes |
| ST-FR5 | Fairing 5 m | T0 | 4×13 | 2.0 | 2.5 | interior 4×12 m usable; JETTISON event |
| ST-FIN | Grid fin / strake | T0 | 1×2 | 0.15 | 0.4 | +40 kPa·deg to q·α limit (max 2 counted); aero control torque +30% in atmo |
| FD-1 | Crossfeed fuel duct | T1 | 1×2 | 0.08 | 0.3 | stage-to-stage/port crossfeed; flow cap 1 t/min cryo, 5 t/min storable (W9) |
| ST-BF-G4 | BasaltFiber beam | T2 | 1×4 | 0.22 | resources | axial 1,100 kN; ISRU print, no Earth imports on basalt bodies |
| ST-BF-KEEL | BasaltFiber keel | T2 | 2×10 | 6.8 | resources | axial 3,600 kN; ISRU print |

### 1.2 Tanks (15) — class TANK

Dry-mass fractions encoded: 6% of prop (methalox, storables, Xe COPV), 5% (kerolox, water), 15% (LH2 incl. MLI+ZBO cryocooler), ~20% (30 MPa gas bottles). Bipropellant tanks pre-loaded at the engine-standard O/F (the ratio is an *engine* property — tanks are packaging convenience). Wet = Dry + Cap.

| ID | Name | Tier | Size | Dry (t) | Cap (t) | Cost $M | Contents (canonical resources) / notes |
|---|---|---|---|---|---|---|---|
| TK-ML-S | Methalox tank S | T0 | 2×2 | 0.27 | 4.5 | 0.4 | 3.52 Oxygen + 0.98 Methane (3.6:1); cryogenic |
| TK-ML-M | Methalox tank M | T0 | 2×4 | 0.72 | 12 | 0.9 | 9.39 Oxygen + 2.61 Methane; cryogenic |
| TK-ML-L | Methalox tank L | T0 | 3×6 | 2.1 | 35 | 2.2 | 27.4 Oxygen + 7.6 Methane; cryogenic |
| TK-ML-XL | Methalox tank XL | T1 | 4×8 | 4.8 | 80 | 4.5 | 62.6 Oxygen + 17.4 Methane; cryogenic |
| TK-KL-M | Kerolox tank M | T0 | 2×4 | 0.70 | 14 | 0.8 | 9.83 Oxygen + 4.17 RP1 (2.36:1); RP1 Earth-import only |
| TK-LH2-M | LH2 tank M (ZBO) | T1 | 2×5 | 0.60 | 4.0 | 1.5 | Hydrogen; ZBO draw 0.4 kWe |
| TK-LH2-L | LH2 tank L (ZBO) | T2 | 4×9 | 3.0 | 20 | 5 | Hydrogen; ZBO draw 1.7 kWe |
| TK-LOX-M | LOX tank M | T0 | 2×3 | 0.40 | 8.0 | 0.5 | Oxygen; cryogenic |
| TK-CH4-M | Methane tank M | T0 | 2×3 | 0.35 | 7.0 | 0.5 | Methane; cryogenic |
| TK-HYP-S | Storable-prop tank S | T0 | 1×2 | 0.10 | 1.6 | 0.4 | 1.00 NTO + 0.60 MMH (1.65:1); heaters below 262 K |
| TK-XE-S | Xenon COPV S | T0 | 1×1 | 0.025 | 0.42 | 0.6 | Xenon; not cryogenic |
| TK-XE-L | Xenon COPV L | T1 | 2×2 | 0.24 | 4.0 | 2.0 | Xenon |
| TK-H2O | Water tank | T0 | 1×2 | 0.10 | 2.0 | 0.2 | Water; counts toward storm-shelter areal density |
| TK-N2 | Gas bottle (N2/Ar) | T0 | 1×1 | 0.05 | 0.25 | 0.2 | Nitrogen or Argon @ 30 MPa (RCS feed); no boiloff |
| TK-DEPOT | Cryo depot tank | T1 | 5×12 | 14.0 | 200 | 25 | any cryo pair; ZBO 6 kWe; **2× DK-L fluid ports** built in |

### 1.3 Engines — chemical & solid (12) — class ENGINE

Stats canonical in 02 §4.2 (republished verbatim, may not diverge). Isp_SL marked † = synthetic back-pressure slope for vacuum engines, not a SL operating claim. Wet mass = dry + internal solid prop where listed. The full 02 catalog is buildable; these are the preset rows.

| ID (=02 ID) | Anchor | Tier | Size | Mass (t) | Thrust SL/vac kN | Isp SL/vac s | Prop (O/F) | Gimbal | Cost $M |
|---|---|---|---|---|---|---|---|---|---|
| EN-K1 (=K-845) | Merlin 1D | T0 | 1×2 | 0.47 | 845 / 914 | 282 / 311 | Oxygen+RP1 (2.36) | ±5° | 1.5 |
| EN-K1V (=KV-981) | Merlin Vacuum | T0 | 1×3 | 0.63 | — / 981 | 90† / 348 | Oxygen+RP1 (2.36) | ±3° | 2.0 |
| EN-H1 (=H-102) | RL10C-1 | T0 | 2×4 | 0.19 | — / 101.8 | 110† / 449.7 | Oxygen+Hydrogen (6.0) | ±4° | 12 |
| EN-HYP (=OMS-27) | Shuttle OMS | T0 | 1×1 | 0.12 | — / 26.7 | 100† / 316 | NTO+MMH (1.65) | ±6° | 2.5 |
| EN-HYP-L (=SPS-91) | Apollo SPS | T0 | 1×2 | 0.29 | — / 91 | 60† / 314 | NTO+MMH (1.65) | ±6° | 4 |
| EN-SRB (=SRM-49) | GEM 63 | T0 | 2×12 | 5.2 + 44.1 prop | 1,265 avg (1,663 max) | 245 / 275 | solid, sealed; 94 s burn; no throttle/shutdown | fixed | 6 |
| EN-KICK (=SRM-2) | Star 48B | T0 | 1×2 | 0.126 + 2.011 prop | — / 66 mean | 250 / 286 | solid, sealed; 87 s burn | spin-stab | 1.5 |
| EN-LND (=LND-71) | SuperDraco | T1 | 1×1 | 0.12 | 71 / 73 | 235 / 243 | NTO+MMH (1.65) | fixed (cluster diff-throttle) | 2 |
| EN-H2 (=H-2280) | RS-25 | T1 | 2×4 | 3.18 | 1,860 / 2,279 | 366 / 452 | Oxygen+Hydrogen (6.0) | ±10.5° | 40 |
| EN-M2 (=M-2256) | Raptor 2 | T1 | 2×3 | 1.63 | 2,256 / 2,394 | 327 / 347 | Oxygen+Methane (3.6) | ±15° | 2.5 |
| EN-M2V (=MV-2530) | Raptor Vacuum | T1 | 2×4 | 2.10 | — / 2,530 | 100† / 380 | Oxygen+Methane (3.6) | ±3° | 3.0 |
| EN-ML (=ML-24) | Morpheus lander | T2 | 1×1 | 0.08 | 22 / 24 | 295 / 320 | Oxygen+Methane (3.6) | ±5° | 1.5 |

Raptor pair (EN-M2/M2V) is T1 gated by era node PR-02. DECISIONS A8 accepted three more 02 registrations (Bantam-class methalox SL/vac pair, argon AEPS Hall derivative, pump-fed methalox lander) — builder stubs land when 02 publishes; the code's `engine_m733`/`engine_mv815`/`engine_ml111` rows appear to be these.

### 1.4 Engines — nuclear thermal (3) — class ENGINE

Canonical 02 §4.3. Monoprop Hydrogen (no O/F). Binding ops rules: **no NTR firing below 60 km on Earth** (mission-ending regulatory event); 45-min restart lockout; crew outside shadow cone during ops = promptly lethal dose; p_max 30 kPa (Mars-ambient OK, Titan surface not).

| ID (=02 ID) | Anchor | Tier | Size | Mass (t) | Thrust vac kN | Isp s | Notes |
|---|---|---|---|---|---|---|---|
| EN-NTR-S (=NTR-73) | SNRE/DRACO | T2 | 2×5 | 2.4 (+1.5 shadow shield opt = 3.9) | 73 | 900 | T/W 3.1 bare; LANTR option: +0.25 t, Isp 645 s, thrust ×2.75 (LOX O/F 3.0) |
| EN-NTR-L (=NTR-246) | NERVA XE' | T2 | 3×6 | 12.5 | 247 | 850 | T/W 2.0; heavy tug core |
| EN-NTR-B (=NTR-111B) | Borowski BNTR | T3 | 2×5 | 3.1 (+1.5 shield = 4.6) | 111 | 900 | bimodal: +25 kWe idle export, none while thrusting; no LANTR |

### 1.5 Engines — electric & RCS (11) — class ENGINE

Canonical 02 §4.4/§4.7. EP = full string (thruster+PPU+feed, ±10° gimbal mount). Catalog thrust authoritative; sim back-derives η = F·Isp·g0/(2·P_rated) and holds it constant under power scaling. RCS quads: 1×1 **surface-mount** (radial to any hull edge cell), exempt from E5 plume rule, per-nozzle ≤ 2 kN; wear is total-impulse-based per maneuver.

| ID (=02 ID) | Anchor | Tier | Size | Mass (t) | Thrust | Isp s | Power | Prop | Cost $M |
|---|---|---|---|---|---|---|---|---|---|
| EN-ION-2 (=ION-2) | NSTAR | T0 | 1×1 | 0.030 | 92 mN | 3,120 | 2.3 kWe | Xenon | 2 |
| EN-HALL-1 (=HALL-1) | SPT-100 | T0 | 1×1 | 0.012 | 83 mN | 1,600 | 1.35 kWe | Xenon | 1 |
| EN-ION-N (=ION-7) | NEXT-C | T1 | 1×1 | 0.058 | 236 mN | 4,190 | 6.9 kWe | Xenon | 5 |
| EN-HALL (=HALL-12) | AEPS | T1 | 1×1 | 0.115 | 590 mN | 2,800 | 12.5 kWe | Xenon | 3 |
| EN-HALL-X (=HALL-100) | X3 nested Hall | T3 | 2×2 | 0.46 | 5.4 N | 2,000 | 100 kWe | Xenon or Argon (η −0.06) | 12 |
| EN-MPD (=MPD-200) | applied-field MPD | T3 | 2×2 | 0.90 | 4.6 N | 4,000 | 200 kWe | Argon (NH3 η −0.05; H2 η −0.05, Isp +25%) | 15 |
| EN-VAS (=VAS-200) | VASIMR VX-200 | T3 | 2×3 | 0.65 | 5.7 N | 4,900 (var 3,000–12,000) | 200 kWe | Argon | 20 |
| EN-FT (=DFD-5) [SPECULATIVE] | Princeton DFD | T4 | 3×8 | 10 | 20 N | 10,500 | self-powered (5 MW fusion; exports 1 MWe) | He3+Hydrogen | 2,000 |
| RCS-N2 (=RCS-N10) | cold-gas | T0 | 1×1 surf | 0.008 | 4×10 N | 70 | — | Nitrogen (TK-N2 feed) | 0.1 |
| RCS-HYP (=RCS-D400) | Draco | T0 | 1×1 surf | 0.022 | 4×400 N | 300 | — | NTO+MMH (1.65); ullage-capable | 0.4 |
| RCS-CH4 (=RCS-M2K) | Starship hot-gas | T1 | 1×1 surf | 0.060 | 4×2,000 N | 270 | — | gaseous O2+CH4 from main tanks | 0.6 |

EP catalog η (02): NSTAR 0.61, NEXT 0.70, SPT-100 0.48, AEPS 0.65, X3 0.52, MPD 0.45, VASIMR 0.69. 02's FFR-43 and PULSE-D get **no** builder stub.

### 1.6 Power & thermal (10) — class ELEC (performance canonical in 09)

| ID (=09 ID) | Name | Tier | Size | Mass (t) | Output | Deployed area m² | Cost $M | Notes |
|---|---|---|---|---|---|---|---|---|
| PW-SA-R (=SOL-RW) | Rigid solar wing | T0 | 1×4 stowed | 0.16 | 5 kWe @1 AU BOL | 12.5 | 0.8 | ISS legacy, 31 W/kg |
| PW-SA-RO (=SOL-RO) | Roll-out array | T0 | 1×3 stowed | 0.25 | 20 kWe @1 AU | 46 | 2 | ROSA, 80 W/kg; 1/d² falloff |
| PW-BAT (=STO-LI) | Battery bank | T0 | 1×1 | 0.20 | 30 kWh | — | 0.5 | 150 Wh/kg; heater 50 W per 0.1 t below 273 K |
| PW-FC | Fuel cell | T0 | 1×1 | 0.12 | 7 kWe cont. | — | 1 | Hydrogen+Oxygen→Water |
| PW-RTG | RTG | T0 | 1×1 | 0.045 | 0.11 kWe | — | 15 | Pu238 (MMRTG) |
| PW-KP1 | Fission unit 1 kWe | T2 | 1×2 | 0.40 | 1 kWe | — | 20 | Kilopower; unlock 11 PW-04 |
| PW-KP10 | Fission unit 10 kWe | T2 | 2×3 | 1.5 | 10 kWe | — | 60 | Kilopower 10 |
| PW-FSP | Surface fission 100 kWe | T2 | 3×4 | 9.0 | 100 kWe | — | 150 | FSP studies |
| PW-NEP (=NUK-NEP) | NEP reactor 2 MWe | T3 | 5×8 | 35 | 2,000 kWe | 144 (integral radiators) | 600 | 17.5 kg/kWe incl. conversion+shield+800 K radiators |
| TH-RAD | Deployable radiator | T0 | 1×3 stowed | 1.2 | rejects 50 kWt @500 K | 12 (two-sided) | 1.5 | 09 owns curve |

Reactor shadow-shield cone covers parts within ±10° aft (09 placement rule).

### 1.7 Habitat modules (13) — class HAB

V_hab = 0.7 · V_press. Sleeps = permanent berths; labs/greenhouses/cupolas = 0 sleeps but count toward volume.

| ID | Name | Tier | Size | Mass (t) | V_press m³ | Sleeps | Cost $M | Special |
|---|---|---|---|---|---|---|---|---|
| HB-CAP2 | 2-crew capsule | T0 | 2×3 | 4.2 | 9 | 2 (≤7 d) | 25 | command source; integral PICA shield (q̇_max 12 MW/m² vs q̇_conv, 0.05 t ablator / 3.1 m²) + chutes (deploy q ≤ 20 kPa, a ≤ 7 g) |
| HB-CAP4 | 4-crew capsule | T0 | 3×4 | 9.5 | 20 | 4 (≤30 d) | 60 | command source; integral PICA shield (0.11 t ablator / 7.1 m²) + chutes (same limits) |
| HB-RIG-S | Rigid module S | T0 | 3×5 | 9.0 | 60 | 2 | 70 | — |
| HB-RIG-L | Rigid lab/hab module | T0 | 4×9 | 14.5 | 106 | 4 | 120 | ISS Destiny |
| HB-INF-S | Inflatable module S | T0 | 2×2 (3×4 deployed) | 1.4 | 16 | 0 (storage) | 8 | DEPLOY event; BEAM |
| HB-INF-M | Inflatable hab M | T1 | 3×5 (8×11 depl.) | 13.2 | 340 | 6 (+6 surge) | 80 | TransHab; DEPLOY |
| HB-INF-L | Inflatable hab L | T1 | 4×6 (8×11 depl.) | 20.0 | 330 | 6 (+6 surge) | 150 | B330 incl. integral ECLSS |
| HB-CUP | Cupola | T0 | 2×1 | 1.9 | 3 | 0 | 15 | +morale |
| HB-AIR | Airlock | T0 | 2×3 | 6.1 | 34 | 0 | 30 | 2-person EVA (clears W2) |
| HB-LAB | Science lab | T1 | 4×9 | 12.0 | 100 | 0 | 100 | research slots (11) |
| HB-GRN-S | Greenhouse S | T2 | 3×5 (inflatable) | 6.0 | 80 | 0 | 40 | 50 m² grow, 25–50% food closure ~4 crew |
| HB-GRN | Greenhouse | T3 | 4×9 (inflatable) | 16.0 | 280 | 0 | 90 | 200 m² grow, full-diet tier |
| HB-STORM | Storm shelter core | T1 | 2×2 | 3.0 (+5 Water fill) | 8 | refuge 8 | 12 | clears W3 outright |

### 1.8 Spin-gravity, docking & assembly (12)

| ID | Name | Tier | Size | Mass (t) | Cost $M | Class | Key stats / ports |
|---|---|---|---|---|---|---|---|
| SP-HUB | Despun hub w/ rotary seal | T2 | 3×3 | 8.0 | 90 | MECH | **2× DK-B despun ports**; motor torque 10 kN·m; pressurized rotating joint |
| SP-ARM | Spin truss arm 10 m | T2 | 1×10 | 1.2 | 2 | STRUCT | radial-load axial 800 kN → max ring mass/arm = 800/a_spin |
| SP-TETHER | Bolo tether 200 m | T2 | 1×2 reel | 0.8 | 3 | MECH | 2-mass bolo; rated 300 kN |
| SP-HAB | Ring hab pod | T2 | 3×4 | 8.0 | 60 | HAB | V_press 60 m³; pre-curved r ≥ 20 m |
| SP-RING | Ring segment 30° | T3 | 29×4 (chord) | 22.0 | 120 | HAB | V_press 180 m³ @ r=56 m; ends attach only to SP-RING ends / SP-ARM tips; 12 segments close a 1 g ring (cycle → canonical-joint rule) |
| DK-S | Docking port S | T0 | 1×1 | 0.34 | 2 | MECH | 0.8 m passage; rated 60 kN; androgynous IDSS |
| DK-B | Berthing port B | T0 | 2×1 | 0.25 | 2 | MECH | 1.27 m passage; 150 kN; needs robot arm to mate (CBM) |
| DK-L | Structural berth L | T1 | 3×1 | 1.2 | 5 | MECH | 3 m; 800 kN; fluid transfer built in; loops allowed only via L |
| DK-GR | Grapple fixture | T0 | 1×1 | 0.05 | 0.3 | MECH | arm grab point |
| DK-ARM | Robot arm | T1 | 1×2 stowed | 1.8 | 40 | MECH | 17 m reach; moves ≤ 116 t; enables orbital assembly |
| HB-DOCKYARD | Dry Dock module | T2 | 6×12 | 24.0 | 200 | STRUCT | open frame fits sub-assemblies ≤ 6×12 m; 2× assembly rate in-frame; assembles beyond fairing limits; pressurized cab 20 m³ (0 sleeps); 2 kWe; 1× DK-B |
| UT-CMG | Control moment gyro | T0 | 1×1 | 0.3 | 8 | MECH | momentum 4,760 N·m·s; torque 0.26 kN·m |

### 1.9 Cargo, utility, entry & landing (16)

| ID | Name | Tier | Size | Mass (t) | Cost $M | Class | Key stats / special |
|---|---|---|---|---|---|---|---|
| CG-BAY | Unpressurized cargo bay | T0 | 2×3 | 0.6 | 0.8 | STRUCT | holds 8 t / 12 stowed-cell-equivalents as **off-grid manifest** (2 cell-eq per bay cell); contents mass at bay centroid, count vs 600-part cap, aero/MMOD-protected while intact, no DEPLOY while stowed |
| CG-HOP | Ore hopper | T1 | 3×3 | 1.5 | 1 | STRUCT | 12 t bulk (Regolith etc.) |
| CG-CON | Container berth | T1 | 2×1 | 0.15 | 0.3 | STRUCT | mounts 1 standard container (05 spec) |
| CG-RB | Regolith ballast box | T2 | 2×2 | 0.4 (+10 fill) | 0.2 | STRUCT | spin counterweight / rad shielding |
| UT-AV | Avionics core | T0 | 1×1 | 0.15 | 5 | ELEC | **command source**; low-gain comms; 0.3 kWe draw |
| UT-AVS | Probe core S | T0 | 1×1 | 0.04 | 2 | ELEC | **command source**; 0.1 kWe |
| UT-DISH-S | High-gain dish 0.5 m | T0 | 1×1 | 0.02 | 1 | ELEC | link budget per 12/13 |
| UT-DISH-M | High-gain dish 3 m | T0 | 1×2 stowed | 0.09 | 3 | ELEC | deployed area 7 m² |
| UT-DISH-L | Deployable dish 10 m | T2 | 2×2 stowed | 0.4 | 10 | ELEC | outer-system relay; deployed area 80 m² |
| UT-HS3 | Heat shield 3.7 m | T0 | 3×1 | 0.5 | 2 | SHIELD | PICA: q̇_max 12 MW/m² vs q̇_conv; ablator 0.17 t (16 kg/m² over 10.8 m²); protects 3-wide column behind; no bottom node |
| UT-HS5 | Heat shield 5 m | T1 | 4×1 | 0.9 | 4 | SHIELD | as HS3 at 4-wide: ablator 0.31 t over 19.6 m² |
| UT-CHUTE | Parachute cluster | T0 | 1×1 | 0.24 | 0.5 | MECH | recovers 6 t @ ≤8 m/s Earth SL; `v_td = 8 · sqrt(m/6t) · sqrt(ρ_E,SL/ρ_local)`; deploy q ≤ 20 kPa, a ≤ 7 g else destroyed; mass ≈ 4% of recovered |
| ST-LL | Landing leg | T0 | 1×2 | 0.15 | 0.4 | MECH | 8 t per leg @ ≤3 m/s touchdown |
| ST-LLH | Heavy landing leg | T1 | 1×3 | 0.6 | 1 | MECH | 40 t per leg @ ≤3 m/s |
| AR-SHELL | Entry aeroshell 5 m | T3 | 4×2 | 2.5 | 8 | SHIELD | PICA + backshell; q̇_max 12 vs q̇_conv; ablator 0.63 t (32 kg/m² double layup / 19.6 m², Venus-rated); protects 4-wide column; jettisonable; no bottom node |
| AR-CHUTE | Supersonic extraction chute | T3 | 1×1 | 0.6 | 1.5 | MECH | deploy ≤ Mach 2.2 and q ≤ 4 kPa; extracts ≤ 10 t from aeroshell; single-use |

AR-ENV / AR-GON / AR-INF (aerostat envelope/gondola/inflation) → **doc 07's catalog** (DECISIONS A10); Build D references them by 07's IDs. The AR-* set is T3 (Act 4).
Landed tip-over rule: stable iff `tan(θ_slope) < (b/2)/h_COM` (b = leg-base width). Legs 7 m apart, COM at 4 m → stable to 41°.

### 1.10 Whipple shielding (3) — class SHIELD

| ID | Name | Tier | Size | Mass (t) | Cost $M | Stats |
|---|---|---|---|---|---|---|
| WS-B | Whipple panel 10 m² | T0 | 1×2 | 0.10 | 0.3 | η = 0.90; 10 kg/m²; covers 10 m² hull |
| WS-S | Stuffed Whipple 10 m² | T1 | 1×2 | 0.22 | 0.8 | η = 0.98; 22 kg/m² |
| WS-BF | BasaltFiber stuffed panel | T2 | 1×2 | 0.22 | resources | η = 0.97; ISRU print |

### 1.11 Tier progression (unlock placement)

| Tier | Act | Unlocks |
|---|---|---|
| T0 | 1 | EN-K1/K1V, EN-H1, EN-HYP/HYP-L, EN-SRB/KICK, RCS-N2/HYP, EN-ION-2, EN-HALL-1; basic tanks; PAD-1/2; fairings, capsules, rigid modules, HB-INF-S, DK-S/B, WS-B, PW-SA-R/RO |
| T1 | 1–2 | PAD-3; EN-M2/M2V (behind PR-02) + RCS-CH4; EN-LND, EN-H2; EN-ION-N (PR-06), EN-HALL (PR-07); ZBO LH2 tanks, TK-DEPOT, FD-1, DK-L, DK-ARM, HB-INF-M/L, WS-S, HB-STORM, PW-KP1 |
| T2 | 2–4 | EN-NTR-S/L, EN-ML, TK-LH2-L, SP-HUB/ARM/TETHER/HAB, PW-KP10/FSP, HB-GRN-S, HB-DOCKYARD, ISRU printing STRUCT/TANK/MECH/SHIELD |
| T3 | 4–5 | EN-HALL-X, EN-VAS, EN-MPD, PW-NEP, EN-NTR-B, SP-RING, HB-GRN, AR-SHELL/AR-CHUTE, orbital ENGINE/HAB/ELEC printing |
| T4 [SPEC] | 5 | EN-FT, He3 chain, reactor printing |

---

## 2. BUILDER MATH & STRUCTURE (the Drydock)

### 2.1 Grid & attachment
- Side cross-section 2D grid, **1 cell = 1 m × 1 m**, +y = nose, −y = engines, x lateral. Parts occupy w×h footprints at integer positions; **no overlap** (E4).
- Attach nodes per §1 defaults/overrides. Stack nodes carry full rating; radial nodes 25% of the smaller part's axial rating.
- Vessel = connected graph G(parts, joints) (E2 if disconnected). ≥ 1 **command source** (UT-AV/UT-AVS or crewed module with controls) else E1. Control follows the **active core**: player-designated, default highest-tier avionics, ties broken by proximity to wet COM; re-run per fragment on SEPARATE/undock; fragment with zero sources → debris.
- Part cap **600 per vessel**, including docked merges (refuse dock past cap with UI explanation — no silent failure).

### 2.2 Mass properties
- `m_dry = Σ part dry + Σ cargo + Σ crew·(80 kg + 20 kg suit)`; `m_wet = m_dry + Σ propellant + Σ consumables`.
- COM (live, wet AND dry): `x_COM = Σ(m_i·x_i)/Σm_i` (same y) using footprint centroids; propellant fixed at tank centroid while draining (stated simplification — COM shifts only *between* tanks). Display wet COM (yellow), dry COM (orange), swept line.

### 2.3 Thrust vector / control authority
- `F_net = Σ F_i·(u_i, v_i)`; torque `τ_net = Σ[(x_i − x_COM)·F_y,i − (y_i − y_COM)·F_x,i]` (kN·m, CCW+).
- Gimbal authority `τ_ctl = Σ F_i·sin(δ_i)·L_i` (L_i = engine→COM distance).
- Badges, evaluated at BOTH wet and dry COM: GREEN `|τ_net| ≤ 0.5·τ_ctl`; YELLOW ≤ 0.9·τ_ctl; RED above.
- **Engine-out badge**: `|τ_fail(throttle)| ≤ τ_ctl_remaining(throttle) + τ_rcs` (both engine terms scale with throttle; RCS term doesn't). `τ_rcs = Σ F_rcs·L_rcs`; CMGs add catalog torque/momentum.

### 2.4 Delta-v (live, per stage)
- `dv = Isp·g0·ln(m0/m1)`; m0 = stage full mass + everything above; m1 = m0 − propellant burned by this stage.
- Mixed engines: `Isp_eff = ΣF_i / Σ(F_i/Isp_i)` (thrust-weighted).
- Ambient: `Isp(p) = Isp_vac − (Isp_vac − Isp_SL)·(p/101.325 kPa)`, clamped at 101.325. First-stage **trajectory-averaged Isp = Isp_SL + 0.44·(Isp_vac − Isp_SL)** (worked builds use this; also print SL/vac bounds).
- **ṁ is a per-engine constant from the vacuum pair**: `ṁ = F_vac/(Isp_vac·g0)`; then `F(p) = ṁ·g0·Isp(p)`. NEVER mix one pressure's F with another's Isp (Build A stage 1: 70,000 kg / 599.4 kg/s = 117 s, not 126 s).
- Burn time `t_burn = m_prop/ṁ`, `ṁ = ΣF_i/(Isp_eff·g0)`.
- EP: `F = 2·η·P_in/(Isp·g0)`; catalog thrust authoritative (η back-derived and held constant); under-power → thrust scales proportionally at constant Isp (dv unchanged, burn time grows). Solar P scales 1/d²; the §3.4 scaling divides available power by **rated thruster power**, not array output.
- dv readout counts only **burnable** propellant (min-limited by the scarcer resource at the engine's O/F).

### 2.5 TWR
- `TWR = ΣF_i/(m·g_ref)` at ignition AND burnout, per stage; g_ref selectable: Earth 9.80665 (= g0), Moon 1.62, Mars 3.71, others from 03.
- Thresholds (canonical 02 §3.7): atmo launch hard floor TWR > 1.0; **W1 below 1.2**; recommended 1.3–1.5 Earth; airless liftoff > 1.0 strict, ≥ 1.8 recommended; powered landing TWR_local > 1.0; upper stages ≥ 0.5 recommended; NTR/EP < 1 OK — planner warns and offers burn-split when `t_burn > T_orbit/6`.

### 2.6 Staging
- Ordered stage list S0…Sn; events: IGNITE(engine), SEPARATE(decoupler), JETTISON(fairing), DEPLOY(chute/panel/radiator/inflatable).
- Decoupler must split G into exactly two connected components, else E3.
- dv/TWR bottom-up; jettisoned mass leaves the ledger at its event.
- **E5 plume rule**: engine may not fire if its exhaust column (w_engine wide, 6 m below nozzle) hits a not-yet-separated same-vessel part. RCS exempt; ST-IS-V (hot staging) exempt. Mirror rule for fairing-enclosed DEPLOY (blocked, E5-class — edge case 15).
- Solids: no throttle/shutdown, burn to depletion; W4 if a solid stages above a later-igniting liquid stage.
- **Acceleration limiter**: autopilot clamps a ≤ 4 g crewed / 6 g uncrewed; player-overridable down to part limits; the selected value is SAVED WITH THE DESIGN and E6 always evaluates at it. Solids ignore the limiter.

### 2.7 Propellant flow & crossfeed
- O/F is an engine property: methalox 3.6, kerolox 2.36, hydrolox 6.0, storables 1.65 (resources RP1/NTO/MMH per 02 §4.1, exact spellings — DECISIONS A1).
- Drain rule: engine draws each resource at its O/F split from **all graph-connected same-stage tanks holding it, proportionally**. Either resource exhausts → flameout (deterministic; restart per 02 ullage rules).
- Crossfeed via FD-1 or DK-L only → **feed group**: drains in descending stage number (asparagus), proportional within a stage; per-tank priority integer overrides. Flow caps (FD-1: 1 t/min cryo, 5 t/min storable) throttle engines in flight; design-time warning W9.
- Solids sealed (prop = part mass, not a resource). Cryo flag is on the tank, not the resource; cryo tanks boil off without ZBO (rates 02/09; ZBO ≈ 5 kWe per 60 t LH2 class).

### 2.8 Structural integrity (no FEA — three live checks + g-limits)
**(a) Joint axial loads.** `a` = proper acceleration (thrust/m, limiter-clamped; on pad/landed a = g_local). Per joint: `L_j(t) = m_above,j(t)·a(t)` — PASS iff ≤ L_rated,j for every joint, evaluated at each stage's **burnout** (+ limiter-engage instant + on-pad case); no full integration needed. Load graph is a **spanning tree**: every cycle (rings, L-berth loops, dock-formed) designates the most-recently-closed joint as non-load-bearing (canonical joint, recomputed on graph change); one DFS from root engine cluster computes all m_above — O(parts). L_rated = min of the two parts' ratings (defaults §1; engine stack nodes pass at any throttle by construction; radially-mounted engines get no waiver and are flagged). Violation in flight = joint breaks, vessel splits (deterministic).
**(b) Max-Q.** `q = ½·ρ(h)·v²`; per-part q_max table in §1 defaults. Exceed → part destroyed (flight) / E7 (pre-flight sim). Autopilot flies a throttle bucket targeting q ≤ 35 kPa.
**(c) q·α bending.** `q·|α| ≤ 170 kPa·deg` vessel-wide (+40 per ST-FIN, max 2). Violation snaps the stack at the joint with max `m_above·q·α/L_rated`. Ascent guidance flies α ≤ 3° below 30 km.
**(d) g-limits.** default 8 g axial / 3 g lateral; exceed → part damage event.

### 2.9 MMOD (design-relevant)
- Daily roll per vessel: `P_pen = 1 − exp(−Φ·A_exposed·t·(1−η))`, t in YEARS (1/365.25 daily; batch under warp). Φ from 03 (placeholder 1e-4 /m²/yr > 1 mm at 400 km).
- A_exposed = Σ hull areas not covered by shield panels (1 panel covers 10 m²). η: bare 0, WS-B 0.90, WS-S 0.98, WS-BF 0.97. Hit location weighted by share of uncovered hull area: module→leak, tank→0.1%/h per cm² leak, radiator/array→capacity loss, avionics→fault. >10 cm objects tracked in LEO → conjunction events (0.5–2 m/s avoidance).

### 2.10 Entry heating (builder-relevant; constants owned by 01)
- `q̇_conv = k·sqrt(ρ/r_n)·v³`, r_n = w/2 of foremost part; `q̇_total = q̇_conv·f_rad`, f_rad = min(1 + ((v−9000)/3000)², 8) above 9 km/s.
- q̇_max: bare aluminum **0.007 MW/m²**; SteelHotStructure option (+15% dry mass) 0.10; tiles 0.30; RCC 0.75 (reusables fail if exceeded > 2 s); PICA 12 and carbon-phenolic 30 **checked vs q̇_conv only** (q̇_total drives ablator consumption).
- Shield protects its w-wide column behind it while held within ±10° of velocity vector. Fairings/bays protect contents only to fairing's own 0.007 limit.
- Ablator: `ṁ_abl = q̇_total·A_loaded/E_abl`, E_abl = 50 MJ/kg, A_loaded = frontal disc area, stagnation q̇ uniform (conservative). Depleted shield → bare structure. Multi-pass aerocapture draws the same budget. Exceed q̇_max → destroyed / E11 pre-flight.

### 2.11 Crew capacity & shelter
- `V_hab = 0.7·V_press`, summed over ALL pressurized modules.
- Long-duration (>30 d): `crew_max = min(Σ sleeps, floor(V_hab_total/25))`. Short (≤30 d): `min(Σ sleeps + surge, floor(V_hab_total/10))`. Exceeding = emergency-only (08 morale tiers).
- Warnings with crew: ≥1 airlock (W2); ≥1 docking port per 4 crew (W8); storm shelter beyond LEO (W3). **Shelter check**: HB-STORM qualifies outright; any module qualifies iff every footprint edge cell is adjacent to / covered by parts whose summed areal densities (mass incl. contents / hull area) ≥ 500 kg/m². Full TK-H2O = 350 kg/m² → one layer fails, two layers (700) pass.

### 2.12 Construction flows, pads, fairings, cost
- **Earth launch**: liftoff TWR > 1.0 hard floor, max-Q/q·α pass, pad limits: PAD-1 150 t / 30 m (Act 1 start); PAD-2 1,000 t / 60 m (Act 1 upgrade); PAD-3 5,000 t / 120 m (T1). Fairing interiors: ST-FR3 3×8 m, ST-FR5 4×12 m (payloads inside exempt from aero checks). Commercial lift alternative: $1,500/kg to LEO baseline (12 owns).
- **Orbital assembly**: parts arrive as cargo; needs DK-ARM or drone within 50 m; 1 structural joint / 30 min / arm; HB-DOCKYARD doubles rate and assembles beyond fairing limits. Port-docking assembly needs no arm.
- **ISRU manufacture** by material class (recipe per kg): STRUCT 0.95 IronSteel|Aluminum|BasaltFiber + 0.05 MachineParts (T2); TANK 0.80 Al + 0.15 MP + 0.05 Electronics (T2); MECH 0.55 IS + 0.25 MP + 0.10 Ti + 0.10 El (T2); ENGINE 0.50 IS + 0.20 Ti + 0.20 MP + 0.10 El (T3 orbital foundry); HAB 0.50 Al + 0.20 Poly + 0.15 MP + 0.10 El + 0.05 Glass (T3); ELEC 0.40 El + 0.30 Al + 0.20 Cu + 0.10 MP (T3; reactors Earth-only until T4); SHIELD 0.60 Al + 0.40 BF (T2). BasaltFiber STRUCT prints 25% lighter than IronSteel.
- Cost ledger: catalog $M; printed parts = inputs + shop time.

### 2.13 Required UI readouts (live, recompute per edit; every readout has "show the math" hover)
Wet/dry mass · per-stage dv (SL/vac/traj-avg toggle, g_ref selector) · TWR ignition/burnout · burn time · COM markers + thrust line + GREEN/YELLOW/RED + engine-out badge · part count /600 · cost · crew capacity vs sleeps · V_press · power balance at selected solar distance · radiator margin · MMOD coverage % + P_pen/yr at selected orbit · q_max worst part · spin rpm slider with a_spin/comfort/balance. Plus: one-click **pre-flight ascent sim** (same code path as flight) plotting q, q·α, accel, throttle vs t with limit lines; mirror-symmetry toggle; sub-assembly save/load; blueprint JSON export.

### 2.14 Validation codes (stable IDs; clicking zooms to offender)
| Code | Meaning |
|---|---|
| E1 | no command source |
| E2 | disconnected parts |
| E3 | decoupler would not split into exactly two components |
| E4 | overlapping footprints |
| E5 | plume impingement (incl. deploy-inside-fairing) |
| E6 | joint overload at design-selected limiter accel |
| E7 | q_max exceeded in pre-flight ascent sim |
| E8 | docking port size mismatch |
| E9 | crewed spin > 6 rpm |
| E10 | negative dry mass from cargo-manifest misconfig |
| E11 | q̇_max exceeded in pre-flight entry sim |
| W1 | liftoff TWR < 1.2 |
| W2 | no airlock with crew |
| W3 | no storm shelter beyond LEO |
| W4 | solid above liquid stage |
| W5 | dv below mission-planner target |
| W6 | spin imbalance > 0.02·r |
| W7 | uncovered hull in high-flux orbit |
| W8 | < 1 docking port per 4 crew |
| W9 | crossfeed duct flow cap throttles engines |

---

## 3. STATIONS

### 3.1 Spin gravity math
```
ω = rpm·2π/60;  a_spin = ω²·r;  v_rim = ω·r;  gradient Δa/a = h/r
```
Comfort rules (08 consumes): (1) ω ≤ 2 rpm comfortable immediately; (2) 2–4 rpm needs 7-day adaptation; (3) 4–6 rpm permanent −15% productivity; (4) **ω > 6 rpm crewed = E9**; (5) full comfort needs r ≥ 25 m (≤8% gradient over 2 m); (6) full comfort needs v_rim ≥ 6 m/s, else −5% productivity (stacks); (7) health: a ≥ 3.71 m/s² halts most deconditioning, ≥ 1.62 halves it, < 1.0 cosmetic.

Worked r = a/ω² (v_rim):
| rpm | 1.00 g | 0.38 g | 0.17 g |
|---|---|---|---|
| 1 | 894.6 m (93.7) | 338.3 m (35.4) | 147.7 m (15.5) |
| 2 | 223.6 m (46.8) | 84.6 m (17.7) | 36.9 m (7.7) |
| 3 | 99.4 m (31.2) | 37.6 m (11.8) | 16.4 m (5.2) |
| 4 | 55.9 m (23.4) | 21.1 m (8.9) | 9.2 m (3.9) |
| 6 | 24.8 m (15.6) | 9.4 m (5.9) | 4.1 m (2.6) |

Design anchors: 1 g ring @4 rpm → r ≈ 56 m (Act 4+, 12× SP-RING closes it); Mars-g @3 rpm → r ≈ 38 m; Lunar-g @4 rpm → r ≈ 9 m bolo (accepts rule-6 penalty).

### 3.2 Spin mechanics
- Spin sections attach via **SP-HUB** (rotary coupling). Docking to a spinning station only at despun hub ports; **EVA forbidden at ω > 2 rpm**.
- **Balance**: rotating subassembly COM within `0.02·r` of hub axis, else W6 / in-flight wobble (oscillating stress, −50% docking-port ratings, comfort penalty). > 0.10·r → forced emergency despin. Counterweights: any mass (water, cargo, CG-RB).
- **Spin-up propellant**: `m_prop = I·ω/(r_t·Isp·g0)`, `I = Σ m_i·r_i²`. Worked: 200 t ring at r = 56 m → I = 6.27e8 kg·m²; ω(4 rpm) = 0.419 rad/s; 2 RCS-HYP at rim (800 N) → torque 44.8 kN·m, spin-up 5,864 s, 1,595 kg storables (993 NTO + 602 MMH). SP-HUB motor (10 kN·m) does it propellant-free against counter-mass (slower).
- Mass change on a spinning station (undock, drain) re-evaluates balance. SP-HUB seal failure event: 0.1 kg/h leak, hub ports locked.

### 3.3 Docking topology & merge rules
- Ports androgynous within size class; sizes must match (E8): **S** 0.8 m / 60 kN; **B** 1.27 m / 150 kN (arm-mated); **L** 3.0 m / 800 kN + fluid transfer.
- Capture limits (else bounce at 0.5× closing speed; damage above 0.5 m/s): close ≤ 0.1 m/s (S/B), ≤ 0.05 m/s (L); lateral ≤ 0.1 m; angle ≤ 5°. Magnetic soft-capture (T1 upgrade) doubles all.
- Dock merges vessel graphs into ONE physics body (13); merged assembly respects the 600-part cap (refuse + explain). Closed loops only through L-berths; loops resolved by the canonical-joint spanning-tree rule.
- Burns while docked: §2.8(a) across the docking joint with the port's L_rated. (Build B: 30 t payload at a = 3.42 m/s² → 103 kN ≤ 800 OK through DK-L; would FAIL through DK-S.)
- Station view UI: docking topology graph, per-port load/rating, station-keeping dv/yr forecast, spin-up/down buttons with propellant quote.

### 3.4 Station keeping (no drag integration above the atmosphere interface)
Fee auto-deducted as RCS dv (01 Table 4.8, canonical): LEO 200–300 km **25 m/s/yr**; 300–500 km piecewise log-linear through (300:25)·(400:20)·(500:2); >500 km/MEO/GEO **2**; Sun-Earth L1/L2 **4**; L4/L5 **0**; low lunar/asteroid orbits **5**. Reboost from any docked engine; low fee propellant → alarm. Below-interface drag uses the per-part Cd·A export (frontal default w×1 m², Cd 2.2, + deployed areas).

---

## 4. THE FOUR WORKED BUILDS (acceptance tests — machine-checked numbers)

All dv via `dv = Isp·g0·ln(m0/m1)`, g0 = 9.80665. Implement each as an integration test: assemble the exact part list, assert every "Expected" number (tolerances: dv ±1 m/s, TWR ±0.01, burn time ±1 s, loads ±1 kN).

### 4.1 Build A "Anvil-1" — T0 two-stage kerolox/hydrolox launcher, 2 t to LEO, uncrewed
T0 engines only (Raptor line is T1 behind PR-02). Acceleration limiter player-set to **5 g** (saved with design; E6 evaluates at it).

| Item | Mass (t) |
|---|---|
| Payload | 2.00 |
| Stage 2 tanks: 1× TK-LH2-M part-filled 2.0 Hydrogen (dry 0.60) + 2× TK-LOX-M with 12.0 Oxygen (dry 0.80) — 14.0 t hydrolox @ O/F 6.0 | 15.40 |
| EN-H1 (=H-102) | 0.19 |
| UT-AV + structure | 0.30 |
| **Stage 2 total m0₂ (incl. payload)** | **17.89** |
| ST-FR3 fairing (jettisoned with stage 1) | 0.90 |
| ST-IS3 interstage + ST-DC3 decoupler | 0.52 |
| Stage 1: 5× TK-KL-M (70 t prop = 49.2 Oxygen + 20.8 RP1; dry 3.50) | 73.50 |
| 2× EN-K1 (at x = ±1 m) | 0.94 |
| Structure, 2× ST-FIN, avionics | 1.50 |
| **Liftoff mass m0₁** | **95.25** |

Expected:
- S2: dv = 449.7·g0·ln(17.89/3.89) = **6,729 m/s**; TWR_Earth at ignition **0.58**; burn **607 s** (ṁ = 23.08 kg/s). TK-LH2-M's 0.4 kWe ZBO rides the avionics bus battery for the short coast.
- S1: trajectory-avg Isp 295 s → dv = **3,841 m/s** (bounds: 3,672 at SL 282 s / 4,049 at vac 311 s); liftoff TWR = 1,690/(95.25·g0) = **1.81**; burn **117 s** (ṁ = 2×299.7 = 599.4 kg/s, both from the vacuum pair — mixing listed SL thrust with vac Isp wrongly gives 126 s).
- Total ideal **10,570 m/s** ≥ 9,400 m/s LEO target → ~1,170 m/s margin; payload fraction 2.1%.
- Joint check @5 g limiter: m_above the interstage = 17.89 + 0.90 + 0.52 = 19.31 t; unclamped burnout a = 1,828/25.25 = 72.4 m/s² (7.4 g) → limiter clamps at 49.03 m/s² → L = **947 kN ≤ 1,200 kN PASS** (21% margin). At the 6 g uncrewed default: 1,136 kN (legal, 5% margin). On-pad: 19.31·g0 = **189 kN PASS**. Engine mounts pass by construction (EN-K1 node = max(1,200, 1.25·914) = 1,200 ≥ 914).
- Engine-out (one EN-K1 dies): τ_fail = 845 kN·m ≤ remaining authority 845·sin5°·14 m = 1,031 kN·m → **flyable badge**. Hardware cost ≈ $30M + propellant.

### 4.2 Build B "Charon" — T2 NTR Mars transfer vehicle (orbital-assembled)

| Item | Mass (t) |
|---|---|
| 3× EN-NTR-S (73 kN, Isp 900 s; incl. shadow shields → 3.9 each) | 11.7 |
| 3× TK-LH2-L (60 t Hydrogen; tanks 15% = 9.0 dry) | 69.0 |
| ST-KEEL truss | 9.0 |
| PW-KP10 (ZBO 5 kWe + ship bus) | 1.5 |
| TH-RAD | 1.2 |
| UT-AV, dishes | 0.5 |
| DK-L berth (payload) | 1.2 |
| Payload: HB-INF-M 13.2 + consumables 6.0 + HB-CAP2 return capsule 4.2 + storm-shelter Water 5.0 + science 1.6 | 30.0 |
| **m0** | **124.1** |

Expected:
- dv = 900·g0·ln(124.1/64.1) = 8,826·0.6606 = **5,830 m/s**.
- TWR(LEO, Earth ref) = 219/(124.1·g0) = **0.18** → planner splits TMI into 3 periapsis passes (TMI burn ≈ 27.9 min at ṁ = 24.8 kg/s; full 60 t would take 40.3 min).
- Mission ledger (01 Table 4.2): TMI 3,590 m/s burns 41.5 t H2 → 82.6 t; Mars capture to 1-sol elliptic 1,100 m/s burns 9.7 t → 72.9 t; reserve **8.8 t ≈ 1,136 m/s**.
- DK-L berth load at burnout: a = 219/64.1 = 3.42 m/s²; 30 t payload → **103 kN ≤ 800 kN PASS** (a DK-S at 60 kN would FAIL — tugs pull gently or berth structurally).
- NTR ops: launched cold, first criticality in orbit (60 km Earth rule); 45-min restart lockout between the periapsis passes.

### 4.3 Build C "Packmule" — T1 Hall-thruster cargo tug, LEO → low lunar orbit

| Item | Mass (t) |
|---|---|
| 4× EN-HALL (AEPS strings: 50 kWe rated total, 2.36 N) | 0.46 |
| 3× PW-SA-RO roll-out arrays: 60 kWe @1 AU (20% power margin; 138 m² deployed) | 0.75 |
| 1× TK-XE-L (4.0 t Xenon; 0.24 dry) | 4.24 |
| Structure 0.45 + UT-AV 0.15 + DK-B 0.25 + radiator stub 0.15 | 1.00 |
| Payload (container rack) | 8.00 |
| **m0** | **14.45** |

Expected:
- dv = 2,800·g0·ln(14.45/10.45) = 27,459·0.32409 = **8,900 m/s** — covers the ≈8,000 m/s low-thrust LEO→LLO spiral with ~900 m/s margin.
- a = **1.63e-4 m/s²**; ṁ = 2.36/(2,800·g0) = **8.59e-5 kg/s**; thrust-on time 4.65e7 s ≈ **540 days** (honest 50 kWe physics; time warp is the answer).
- At Mars distance (1.52 AU): arrays give 60/1.52² = 26.0 kWe → thrust = 26.0/50 = **52% of rated** (available power ÷ RATED thruster power, constant Isp; dv unchanged, burn time grows). Transfer planner must show power-limited thrust along the trajectory.

### 4.4 Build D "Cyclops" — T3 Venus aerostat deployment ship (HAVOC-class robotic)
Deploys a robotic aerostat at 55 km in Venus's atmosphere; 07 operates it after float-positive (hand-off boundary).

| Item | Mass (t) |
|---|---|
| Entry assembly (payload): AR-SHELL 2.5 + AR-CHUTE 0.6 + 07:AR-ENV 1.3 + 07:AR-GON 4.6 + TK-LH2-M (0.60 dry, part-filled 0.5 Hydrogen lifting gas) + 07:AR-INF 0.7 + margin 1.2 | 12.00 |
| Carrier bus (UT-AV, PW-SA-RO, UT-DISH-M, RCS-HYP + NTO/MMH) | 1.50 |
| Departure stage: EN-H1 0.19 + 28.0 t prop (24.0 Oxygen in 3× TK-LOX-M + 4.0 Hydrogen in 1× TK-LH2-M; tank dry 1.80) + structure 0.80 + avionics 0.20 + trim ballast 0.11 | 31.10 |
| **m0 (assembled in LEO)** | **44.60** |

Expected:
- dv = 449.7·g0·ln(44.60/16.60) = 4,410·0.9883 = **4,358 m/s** vs trans-Venus injection 3,480 (01 V1) → ~878 m/s for midcourse + carrier divert. TWR **0.23** → 2 perigee burns, **1,213 s** total at ṁ = 23.1 kg/s.
- Drain-rule test: the hydrolox engine draws 6 kg Oxygen per 1 kg Hydrogen across the four SEPARATE tanks exactly as from one combined tank. ZBO power from carrier's PW-SA-RO.
- Peak proper accel 101.8/16.6 = 6.13 m/s² (0.63 g); payload stack joint 13.5 t × 6.13 = **83 kN**, trivial.
- Buoyancy at 55 km (ρ ≈ 0.9 kg/m³): envelope 11,700 m³ Hydrogen → net lift = 11,700·0.9·(1 − 2.016/43.45) ≈ **10,050 kg** vs floated mass **8.9 t** (12.0 minus jettisoned shell 2.5 + chute 0.6) → **13% buoyancy margin**.

---

## 4b. FAILURE MODES & EDGE CASES (flight-side contract the builder data feeds)

| # | Mode | Rule |
|---|---|---|
| 1 | Joint overload in flight (limiter overridden) | joint breaks; vessel splits into two physics bodies; deterministic, no RNG |
| 2 | Max-Q part loss | exposed part over q_max destroyed; structural part → cascade re-check |
| 3 | q·α stack break | snap at joint with max `m_above·q·α/L_rated` ("rocket folds at max Q") |
| 4 | Engine-out | probabilities owned by 02 §3.14: p_base per ignition (solid 0.001, pressure-fed 0.0005, pump-fed 0.002 new / 0.0005 Mature, NTR 0.003, EP 0.0002) and λ0 per burn-second, × wear (1 + 9w²); Mature = ÷4 after 25 program-wide ignitions; × 11 maturity × 05 spares (DECISIONS A5 — orthogonal, no double count). Outcomes 70% benign / 25% dead / 5% energetic |
| 5 | Landing failure | touchdown > 3 m/s or leg over rating → collapse; tip-over per tan rule; plume on > 20° slope → slide |
| 6 | Docking bounce | capture limits missed → elastic bounce at 0.5× closing speed; damage above 0.5 m/s |
| 7 | MMOD penetration | per §2.9; leaks to 08; tank leaks drain to vacuum; repair = EVA/drone + MachineParts |
| 8 | Spin imbalance | mass change re-evaluates; > 0.02·r → wobble (comfort penalty, port ratings halved); > 0.10·r → forced despin |
| 9 | SP-HUB seal failure | MTBF event: 0.1 kg/h air leak until repaired; hub ports locked |
| 10 | Boiloff exhaustion | ZBO power lost → cryo vents at 02's rates (visible on resource timeline) |
| 11 | CMG saturation | accumulated torque > momentum → degrade to RCS; desat burn m = H_total/(r_t·Isp·g0) |
| 12 | Stranded stage | decouple with no command source on one side → tracked debris (LEO conjunction source) |
| 13 | Numerical guards | dv shows 0 (never NaN) when m_prop = 0 / no engine; guard m1 ≤ 0 (E10); cycles always rigidized through one canonical joint |
| 14 | Part-cap griefing | dock exceeding 600 parts refused with UI explanation |
| 15 | Fairing deploy | DEPLOY inside intact fairing/bay blocked (E5-class) |
| 16 | Bipropellant flameout | either O/F resource out → engine shuts down (deterministic); dv readout already excluded the stranded surplus |

Deliberate simplifications (stated, binding): propellant frozen at tank centroid while draining (open question: linear full/empty interpolation); no slosh; no plane changes; 2D grid abstracts depth (parts carry real volumes/areas as scalars); no drag integration above the atmosphere interface (fee instead).

---

## 5. GAP vs CODE (current: 1D stack builder, 37 parts)

Current state (`aphelion/main.py` builder scene; `data/core/parts/*.toml`; `aphelion/sim/vessels/vessel.py`, `docking.py`):
- Builder = ordered **1D list of stages, each a list of part IDs** (`self.stack: list[list[str]]`) — no positions at all. Catalog filter over 4 types (engine/tank/crew/structure), research-lock check, stage split/new, 6 blueprint slots (designs.json).
- Parts TOML schema: `id, type, tier, name, mass_t`, `[engine] thrust_kN/isp_s/isp_sl_s/throttle/gimbal_deg/propellant`, `[tank] capacity_t/mixture`, `[crew] capacity/endurance_days`. 37 files: 16 engines, 15 tanks (the §1.2 set, complete), 6 misc (capsule_vela, gondola_havoc, hab_castor/pollux, payload_2t, probe_longshot).
- Vessel = rows + stage_plan; active stage drains active-stage tanks proportionally ("v1 plumbing rule" docstring); ambient Isp/thrust interpolation present and matches 02 §3.3 in spirit. Docking = row-merge/undock row-split + resource transfer with mixture-aware capacity.

What the spec requires that does not exist:

| Area | Gap |
|---|---|
| Grid editor | Entire 2D system: w×h footprints at integer (x,y); overlap check E4; attach-node model (stack/radial/interior/docking/no-bottom overrides); connected-graph + command-source + active-core rules; 600-part cap; mirror symmetry; sub-assemblies |
| Part data | Per-part: grid size, cost $M, material class, hull area, frontal/deployed area, axial rating, q_max/a_max, V_press/sleeps/surge, power output/draw, port size/class, command-source flag, special flags (open truss, hot-stage, surface-mount, ablator stats, sep impulse). None of these fields exist in TOML |
| Catalog | 37 → 110 parts. Whole categories absent: structure (15), power/thermal (10), spin/docking/assembly (12), cargo/utility/entry/landing (16), Whipple (3), EP strings + RCS (11), solids (EN-SRB/EN-KICK), spec NTRs (NTR-73/246/111B — code has only `engine_ntr_k2`). Code-only parts (m733, mv815, ml111, hl67, torch_d1, vela, castor/pollux, longshot, havoc gondola) need reconciliation against 02/A8 or retirement |
| Builder math | COM (wet/dry) needs positions; thrust-line/torque/τ_ctl + GREEN/YELLOW/RED + engine-out badge; traj-avg Isp toggle; g_ref selector; per-stage ignition/burnout TWR vs thresholds; EP power-limited thrust with 1/d²; burnable-prop min-limit at O/F (current code drains a pooled sum, no O/F split, no flameout) |
| Structure | Everything in §2.8: joint-load spanning tree + canonical-joint cycle rule, burnout-point evaluation, limiter saved with design (E6), max-Q per part (E7), q·α 170 kPa·deg + ST-FIN bonus, g-limits; in-flight break/split |
| Validation | None of E1–E11 / W1–W9 exists; no pre-flight ascent sim with q/q·α/accel/throttle plots |
| Crossfeed | No feed groups, no FD-1/DK-L ducting, no descending-stage drain order, no priority ints, no flow caps (W9) |
| Crew/hab | No V_press/V_hab, sleeps vs volume crew_max (long/short), airlock/port-per-4-crew/storm-shelter (500 kg/m² areal) checks |
| Stations | No spin model at all: a_spin/v_rim/gradient, comfort rules + E9, SP-HUB despun ports, 0.02·r balance + wobble, spin-up propellant quote, ring-closure cycle handling; no station-keeping fee deduction; no MMOD P_pen/coverage; docking has no ports/size match (E8), no capture limits/bounce, no per-port load check, no cap-refusal |
| Entry/landing | No q̇/TPS/ablator model (E11), no protected-column geometry, no chute scaling rule, no leg ratings/tip-over rule |
| Flows/economy | No pads (PAD-1/2/3 limits), no fairing interiors, no orbital assembly (arm rate, dockyard), no ISRU material-class recipes, no cost ledger |

### 5.1 TOML schema extension (concrete; current fields kept, new fields additive)

```toml
id = "core:tk_ml_m"            # keep
type = "tank"                   # keep (engine|tank|crew|structure today; grows)
tier = "T0"                     # keep
name = "Methalox tank M"        # keep
mass_t = 0.72                   # keep (dry)
# --- new, required for the 2D builder ---
size = [2, 4]                   # w, h cells; deployed_size = [8, 11] optional
class = "TANK"                  # STRUCT|TANK|MECH|ENGINE|HAB|ELEC|SHIELD (ISRU recipe key)
cost_musd = 0.9                 # "resources" -> cost_musd omitted + printable = true
axial_kN = 1200                 # optional override; else class default
hull_area_m2 = 12               # optional; default 2*(w+h)
frontal_area_m2 = 2             # optional; default w*1; deployed_area_m2 for arrays/dishes
q_max_kPa = 50                  # optional; default by part state table
nodes = "default"               # or override list: no_bottom|interior|surface_mount|dock_only
command_source = false          # UT-AV/UT-AVS/capsules = true
[tank]                          # keep capacity_t/mixture; add:
cryogenic = true
zbo_kWe = 0.0
[engine]                        # keep; add: of_ratio, plume exempt flag (rcs), solid = true,
                                #   p_max_kPa, restart_lockout_s (NTR), power_kWe (EP), eta
[hab]                           # new: v_press_m3, sleeps, surge, airlock = true, shelter = true
[port]                          # new: size = "S"|"B"|"L", rating_kN, fluid = true, needs_arm
[power]                         # new: output_kWe / draw_kWe / storage_kWh / reject_kWt
[shield]                        # new: eta (whipple) | tps: q_dot_max, ablator_t, areal, column_w
```

### 5.2 Reconciliation list (code parts vs catalog)
- Matching and keepable as-is (rename to catalog IDs): 15 tanks; engines k845→EN-K1, kv981→EN-K1V, h102→EN-H1, oms27→EN-HYP, sps91→EN-HYP-L, lnd71→EN-LND, h2280→EN-H2, m2256→EN-M2, mv2530→EN-M2V, ml24→EN-ML.
- Code-only engines needing a ruling: `m733`/`mv815` (likely the A8 Bantam-class pair — stub when 02 publishes), `ml111` (A8 pump-fed lander), `hl67` (no catalog row), `ntr_k2` (replace with EN-NTR-S/L/B per spec), `torch_d1` (DFD — map to EN-FT, T4).
- Code-only others: `capsule_vela` → reconcile with HB-CAP2/CAP4; `hab_castor`/`hab_pollux` → HB-RIG-S/L or retire; `gondola_havoc` → doc 07's AR-GON (A10); `payload_2t`, `probe_longshot` → keep as scenario payloads outside the catalog.
- Net authoring work: **~73 brand-new parts** (15 structure + 2 solids + 3 NTR + 11 EP/RCS + 10 power + ~10 habs + 12 spin/dock + 16 cargo/utility + 3 Whipple, minus overlaps).

### 5.3 Suggested implementation order
1. Extend TOML schema (§5.1) + author all 110 parts (data-only PR; existing 1D builder keeps working off the kept fields).
2. 2D grid + attach-node graph + E1–E5 validation.
3. COM/torque/τ_ctl/dv/TWR live readouts; **Build A as the first acceptance test** (every number in §4.1).
4. Joint-load spanning tree + max-Q + q·α (E6/E7) + pre-flight ascent sim.
5. O/F drain split + flameout + crossfeed feed groups (FD-1/DK-L, W9).
6. Docking ports/capture/merge + port load checks; **Builds B and C tests**.
7. Spin gravity + balance + station-keeping fees + MMOD rolls.
8. Entry heating/ablator (E11) + chutes/legs; **Build D test**.
