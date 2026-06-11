# BUILD SPEC — 07 Bases & Habitats (extract of design/07-bases-habitats.md DRAFT v1.0)

Engineering extract. Source of truth: `design/07-bases-habitats.md`; conflicts resolved by
`design/DECISIONS.md` (A3 deep-shield GCR floor, A5 one wear model, A6 aerostat tiers,
A10 AR-* ownership, C17 Venus surface sortie, D27 thermal-node cap, D28 grid-scale rulings).
All numbers below are canon as of v1.0 (post-A2 reconciliation pass).

Symbols: P pressure [kPa], ΔP differential [kPa], V pressurized volume [m³], A hull area [m²],
T [K], σ shield areal density [g/cm²] (1 g/cm² = 10 kg/m²), σ_a allowable stress [MPa],
E Young's modulus [GPa], ρ [kg/m³].

---

## 1. HABITAT CATALOG

### 1.1 Habitat modules (HAB-01 … HAB-18) — §4.1 verbatim numbers

Leak = L_cat, **stored as percent/day** of contained gas at 101.3 kPa ΔP (divide by 100 in the
formula — B-4a). Berths column is CANONICAL (do not derive). "Local" = ISRU-supplied mass.
Pressure rating: 101.3 kPa internal tension unless noted. The doc carries **no per-module $
cost** for HAB-* (module purchase/launch costs are owned by `12-gameplay-economy-ui.md`);
the AR-* rows in §1.4 are the only entries with a Cost column.

| ID | Name | Tier | Class | Footprint (10 m cells) | Imported mass | Local mass | V_press | Berths | Leak %/day | Pressure rating | Anchor / notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HAB-01 | Lander Cabin | T0 | rigid | 1×1 | 4 t | — | 20 m³ | 1 (sortie) | 0.05 | 101.3 kPa tension | Apollo LM/HLS; doubles as ascent cabin |
| HAB-02 | Rigid Core Module | T1 | rigid | 2×1 | 15 t | — | 100 m³ | 3 | 0.02 | 101.3 tension | ISS Destiny (14.5 t, 106 m³) |
| HAB-03 | Inflatable Logistics Pod | T1 | inflatable | 1×1 | 1.5 t | — | 16 m³ | 0 | 0.05 | 101.3 tension (softgoods) | BEAM (1.4 t, 16 m³) |
| HAB-04 | Inflatable Hab | T2 | inflatable | 2×2 | 14 t | — | 340 m³ | 6 | 0.04 | 101.3 tension (softgoods) | TransHab (13.2 t, 339.8 m³, crew 6) |
| HAB-05 | Node / Tunnel segment | T1 | rigid | 1×1 | 3 t | — | 14 m³ | 0 | 0.02 | 101.3 tension | ISS node; flex couplings optional (0.2 t MachineParts ea., quake rule) |
| HAB-06 | Glazed Dome 10 m | T2 | rigid+glazed | 2×2 | 6 t | 12 t Glass + frame | 260 m³ | 2 (or greenhouse=0) | 0.06 | 101.3 tension | glazing rule §2.7; crops dose-tolerant (08) |
| HAB-07 | Sintered Regolith Vault | T2 | ISRU-built (masonry+liner) | 3×2 | 1.5 t (liner+hatch) | 120 t sinter + 0.6 t BasaltFiber | 200 m³ | 5 | 0.08 | liner carries 101.3 (B-3d) | microwave sinter / ICON print; 60-day print at 2 t/day |
| HAB-08 | Berm Kit (applies to any module) | T1 | regolith cover | +1 ring | — | 2–3 t/m² Regolith (+frame per B-2b) | — | — | — | — | radiation §2.6, thermal §2.5, MMOD immunity |
| HAB-09 | Ice Home (Mars/icy) | T2 | inflatable + ice fill | 2×2 | 6 t | 370 t Water (1 m³/day fill ≈ 400 days, staged occupancy) | 240 m³ | 4 | 0.06 | 101.3 tension | NASA Langley Ice Home; full = 90 g/cm² water → 0.22 mSv/day on Mars |
| HAB-10 | Titan Iso-baric Longhouse | T3 | rigid frame, min-gauge | 4×2 | 8 t (frame+aerogel) | optional ice cladding | 500 m³ | 8 | 0.02 (composition drift) | iso-baric 146.7 kPa, ΔP≈0 (B-3c) | 30 cm aerogel; 5 kW heater node |
| HAB-11 | Aerostat Gondola Module | T3 | rigid (FEP-clad) | keel slot (not cells) | 6 t | — | 80 m³ | 2 | 0.04 | 101.3 vs ~60 kPa ambient | HAVOC gondola; acid ledger |
| HAB-12 | Envelope Unit 10,000 m³ | T3 | softgoods envelope | — (envelope) | 1.3 t (FEP/Vectran 0.35 kg/m² + fittings) | — | lifting/living volume | — | 0.5 kg/day gas (absolute) | inflation ~60 kPa | lifts 3.3 t gross @ 54 km (B-8a) |
| HAB-13 | Asteroid Gallery, per 1,000 m³ | T3 | excavated + liner | interior (stacked 2D decks, D28) | 1.5 t liner + 0.4 t collar | 2,500 t excavation (04 e_dig) | 1,000 m³ | 20 | 0.06 | liner-only 101.3, k_geom 2.5 (B-3e) | ≥10 m rock ≈1,500 g/cm² → f_GCR≈0.18 → ≈0.33 mSv/day belt mean; SPE-immune |
| HAB-14 | Europa Ice Gallery, per 500 m³ | T3/T4 | melted-bore + liner | interior, ≥ 6 m deep | 2 t liner + heaters | melted-bore spoil | 500 m³ | 10 | 0.08 | liner-only 101.3 | cryobot-cut; B-6f cover; walls < 200 K standoff |
| HAB-15 | Venus Surface Crucible | T4 | external-pressure Ti sphere | 2×2 | 25 t | — | 25 m³ | 2 (30-day sortie) | 0.10 | **external 9,200 kPa buckling** (t≈33 mm @ r=1.8 m) | Venera/GEER/LLISSE; 30 kWe duplex-Stirling cooling; 900 K glow radiator |
| HAB-16 | Mercury Crawler Platform | T3 | mobile chassis | mobile 4×2 | 30 t chassis | — | carries 2 modules (each ≤2×1, ≤16 t) | — | — | — | terminator pacing: ≥3.63 km/h equatorial (=87.1 km/day); design cruise 4.0 km/h |
| HAB-17 | Storm Shelter Cell | T1 | rigid + water jacket | 1×1 | 2 t + 14 t Water fill (or 56 t Regolith bags) | optional | 8 m³ | 5 (shelter only) | 0.02 | 101.3 tension | B-6e compliant: ≥35 g/cm² water-eq over 4π, ≥1.5 m³/crew |
| HAB-18 | BasaltFiber Wound Hab | T3 | ISRU-built (filament-wound) | 2×2 | 1 t (bladder, hatches) | 6 t BasaltFiber + 2 t Glass | 300 m³ | 6 | 0.05 | 101.3 tension | wound on-site at 0.5 t/day → 12 days |

**Berth rule (canon):** catalog Berths column is authoritative. Fallback for non-catalog /
reconfigured volumes only: `berths = floor(V_press / 35 m³)`; labs/workshops/greenhouses = 0.
Net habitable volume reported to 08 = `0.5 × V_press` [SIMPLIFIED] vs its 25 m³/crew floor.

**Hotel power load [LUMPED], every commissioned module:**
`P_hotel = 0.05 kWe × berths + 0.005 kWe × V_press[m³]` → reported to 09 alongside Q_env.
Precomputed: HAB-01 0.15 · HAB-02 0.65 · HAB-03 0.08 · HAB-04 2.00 · HAB-05 0.07 ·
HAB-06 1.40 · HAB-07 1.25 · HAB-09 1.40 · HAB-10 2.90 (+5 kW heater node) · HAB-11 0.50 ·
HAB-13 6.00 · HAB-14 3.00 · HAB-15 0.225 (+30 kWe cooling plant) · HAB-17 0.29 · HAB-18 1.80 kWe.
Airlock cycle energy is separate (§1.3); life-support equipment loads belong to 08.

**Heat kWt:** modules have no fixed heat rating — envelope load Q_env is computed per
environment by the formulas in §2.5 and handed to 09 as a thermal-loop node. Named constants:
HAB-10 carries a 5 kW heater node; HAB-15 a 30 kWe cooling plant; heater node density on
Mars = 1 per 250 m² (09).

### 1.2 Function rates / functional notes per module

| ID | Function rates & special mechanics |
|---|---|
| HAB-06 | Glazing: night loss 150 W/m² of glazed area (Moon/Mars) unless auto-shutters (+10% structure mass); solar gain 0.7 × S_local × A_glaz by day |
| HAB-07 | DEPLOY = 120 t ÷ sinter printer 2 t/day = 60 days; internal tensile liner mandatory (B-3d); +0.5 t StructuralParts per airlock/hatch penetration (ring foundation) |
| HAB-09 | Fill 1 m³/day → ~400 days; occupiable during fill at proportional shielding (shield σ scales with fill fraction) |
| HAB-10 | Commission gas ×1.45 (146.7 kPa); leak model uses ΔP_eff = 5 kPa; composition drift 0.02%/day of inventory (O2 out, N2/CH4 in) → CH4 alarm at 1% cabin |
| HAB-12 | Gas loss 0.5 kg/day absolute; envelope ≈2,500 m² class; lift per §3.3 |
| HAB-13 | Compartmentalize: collar bulkheads every 1,000 m³ (F-10); blowout refill = full commissioning gas cost |
| HAB-14 | Heaters keep walls < 200 K standoff; HAB-14/13 liners waive the min-gauge floor (interior, no MMOD): tension term only, abs. min 2 kg/m² |
| HAB-15 | 30-day sortie endurance; staging point for the C17 T4 crewed surface sortie (interface designed at Pass 2) |
| HAB-16 | Drive power from 10-vehicles; breakdown = race against dawn: time-to-700 K = buffer distance ÷ 87.1 km/day (F-11); speed requirement scales ×cos(latitude) |
| HAB-17 | Design SPE behind 35 g/cm²: 1,000 × e^(−35/12) ≈ 54 mSv (vs ≈960 mSv in a 0.5 g/cm² suit) |

### 1.3 Airlocks & interfaces (AL-1 … AL-7) — §4.2 verbatim

| ID | Unit | Tier | Mass | Volume | Gas lost/cycle | Energy/cycle | Cycle time | Dust ΔD | Special |
|---|---|---|---|---|---|---|---|---|---|
| AL-1 | Vent Airlock | T0 | 0.3 t | 4 m³ | 4.8 kg | 0 | 10 min | +1.0 | — |
| AL-2 | Pumped Airlock | T1 | 1.2 t | 4 m³ | 0.5 kg | 1.0 kWh | 25 min | +1.0 | Quest-class |
| AL-3 | Suitport Pair | T2 | 0.8 t | — | 0.2 kg | 0.1 kWh | 5 min | +0.1 | SEV/Z-suit |
| AL-4 | Vehicle Dock Collar | T1 | 0.6 t | — | 1.0 kg | 0.2 kWh | 15 min | +5 if vehicle unwashed | — |
| AL-5 | Titan Warm-Lock | T3 | 2.0 t | 6 m³ | 0.3 kg | 5 kWh thaw | 30 min thaw | — | mandatory thaw; skip ⇒ 10%/cycle seal-crack roll |
| AL-6 | Venus Acid-Lock | T3 | 1.0 t | 4 m³ | 0.5 kg | — | — | — | neutralization rinse 0.2 kg Water + trace Na2CO3/cycle |
| AL-7 | Dust-Lock Suite | T2 | 1.5 t | 8 m³ | 0.5 kg | 1.2 kWh | — | EVA dust gain ×0.25 total | brush + EDS + bake |

### 1.4 Aerostat deployment hardware (AR-*) — §4.5, owned here per DECISIONS A10

| ID | Name | Tier | Size | Mass | Cost | Class | Key stats | Anchor |
|---|---|---|---|---|---|---|---|---|
| AR-ENV | Aerostat envelope kit | T3 | 2×3 stowed | 1.3 t | 6 | HAB | ≈2,500 m² Vectran/PTFE laminate; 11,700 m³ inflated; DEPLOY event blocked while stowed | HAVOC envelope |
| AR-GON | Aerostat gondola | T3 | 2×2 | 4.6 t | 25 | ELEC | command source; 2 kWe solar; relay comms; atmosphere-ISRU sampler | HAVOC gondola |
| AR-INF | Aerostat inflation hardware | T3 | 1×2 | 0.7 t | 3 | MECH | inflates AR-ENV during parachute descent (≈20 min); feeds from any connected Hydrogen tank | HAVOC mid-air inflation |

Tier split (A6): robotic aerostat platforms (helium-cell starters, instrument balloons) = **T2**
(carried by 11's VH-09, not AR-*); crewed aerostat habitat (HAB-11/12, AR-* set) = **T3**.

### 1.5 §4.4 Environment master table (canonical inputs — verbatim)

| Site | g (m/s²) | P_amb | T_day / T_night (K) | T_deep (K) | Solar cycle | Unshielded dose (mSv/day) | S_local (W/m²) | Notes |
|---|---|---|---|---|---|---|---|---|
| Moon equator | 1.62 | vacuum | 390 / 95 | 250 | 708.7 h | 1.37 (LND, measured) | 1,361 | dust ledger on |
| Moon polar rim | 1.62 | vacuum | 230 / 120 | 190 | 708.7 h, 80–90% lit | 1.37 | 1,361 grazing | mast PV |
| Moon PSR floor | 1.62 | vacuum | 40 / 25 | 38 | never lit | 1.37 | 0 | PSR heat discipline (≤110 K dumping) |
| Mars datum | 3.71 | 0.61 kPa CO2 | 245 / 175 | 210 | 24.66 h | 0.67 (RAD; 03 S-8a) | 490–715 | storms; perchlorate; T = 210 ± 35 |
| Venus 54 km | 8.87 | ≈60 kPa CO2 (45–81 over 52–56 km band) | 310 / 295 | — | ≈6 d (super-rotation) | 0.03 [model] | ≈1,430 day (f_atm 0.55; band 780–1,820) | acid ledger; aerostat statics |
| Venus surface | 8.87 | 9,200 kPa | 737 / 737 | 737 | 116.8 d | ~0.001 [model] | ~15–20 | T4 sorties only |
| Titan surface | 1.35 | 146.7 kPa N2 | 94 / 93.5 | 94 | 15.95 d (moot) | 0.01 [model] | ≈1.5 noon (useless) | iso-baric; fission |
| Europa trailing | 1.31 | vacuum | 110 / 50 | 100 | 85.2 h | 5,400 (JPL) | 50 | robot-only surface |
| Europa leading | 1.31 | vacuum | 110 / 50 | 100 | 85.2 h | 200 [model] | 50 | 1-h EVA budgets |
| Callisto | 1.24 | vacuum | 165 / 80 | 120 | 400.5 h | 0.14 + GCR | 50 | HOPE crew staging; dust ledger off |
| Enceladus (non-stripe) | 0.113 | vacuum | 80 / 65 | 75 | 32.9 h | ~1 [model] | 14.8 | anchoring lite |
| NEA @ 1 AU | ~10⁻⁴ | vacuum | 330 / 200 (fast) | 230 | hours | 1.8·f_cyc | 1,361 | 04 M-6 anchoring |
| Belt C-type @ 2.7 AU | ~10⁻⁴–10⁻² | vacuum | 233 / 120 | 160 | hours | 1.8·f_cyc (flat GCR) | 187 | gallery doctrine |
| Ceres | 0.28 | vacuum | 235 / 110 | 160 | 9.07 h | 1.8·f_cyc | 178 | ice crust |
| Mercury equator | 3.70 | vacuum | 700 / 100 | 350 | 4,224 h | 1.8·f_cyc + SPE ×6.7 mean / ×10.6 perihelion | 6,270–14,450 | crawler or pole |
| Mercury PSR | 3.70 | vacuum | ~50 | 50 | never lit | 1.8·f_cyc | 0 | purest PSR ice |

Free-space GCR everywhere: `D_gcr = 1.8 · f_cycle(t)` mSv/day, f_cycle ∈ [0.65, 1.35]
(0.65 solar max, 1.35 min; event stream from 03). NO radial gradient [SIMPLIFIED].

### 1.6 Structural material allowables (B-3a table — feeds hull sizing)

| Material | σ_a (MPa) | E (GPa) | ρ (kg/m³) | Notes |
|---|---|---|---|---|
| Aluminum (2219-class) | 120 | 72 | 2,840 | T0 default; Aluminum + StructuralParts; FORBIDDEN below 120 K (Titan fittings rule) |
| Stainless steel | 110 | 195 | 7,900 | IronSteel feed; cryo-tough (Titan-rated) |
| Titanium (Ti-6Al-4V) | 300 | 114 (90 @ 737 K) | 4,430 | T2; Venus surface (hot allowable 180 MPa @ 737 K) |
| BasaltFiber composite | 250 | n/a — FORBIDDEN external pressure | 2,000 | T2 ISRU; winder machine required |
| Softgoods restraint (Vectran-class) | 600 (fiber-eff.) | n/a — FORBIDDEN external pressure | 1,400 | inflatables & liners |

### 1.7 Shielding material conversion (B-6b planner table)

| Material | ρ (kg/m³) | Thickness per 100 g/cm² (= 1 t/m²) | Notes |
|---|---|---|---|
| Regolith (loose fill) | 1,650 | 0.61 m | berm/burial default; tailings-fed |
| Water / ice | 1,000 / 917 | 1.00 m / 1.09 m | shelter jackets, Ice Home |
| Polyethylene / polymers | 950 | 1.05 m | modeled material-blind [SIMPLIFIED] |
| Steel hull | 7,900 | 0.013 m | hull plate counts toward σ |

---

## 2. CONSTRUCTION

### 2.1 Surface grid (B-1)

- Site = contiguous build region ≤ **64 × 64 cells, cell = 10 m × 10 m** (640 × 640 m).
  Bigger bases = multiple linked sites (inter-site conduit runs priced per network rules).
- Each structure: rectangular footprint in cells + facing; connects to networks along **cell edges**.
- Terrain classes per cell: `flat` / `rough` (+50% deploy time) / `crater-wall` (berm-ready:
  berm cost ×0.5) / `PSR-shadow` / `sea-shore` (Titan; hosts sea pumps, sub dock) /
  `fissure-adjacent` (Enceladus; PV fouling +0.1%/day).
- **Tailings slots**: 16 pile slots per site, 1 slot per 10,000 t stockpile; full slots stall extractors (04 M-8 canon).
- Grid exceptions (open question 1 + D28 "fit grid scale"): Venus aerostat = **keel slot list**,
  not cells (build rule = mass budget §3.3); asteroid/Europa galleries = **stacked 2D interior decks**.
- Invalid-placement UI rule: violations show rule ID + one-line physics (e.g. Titan
  Earth-pressure hab → "146.7 kPa outside > 101.3 inside: hull would buckle — run iso-baric?").

### 2.2 The FOUR utility networks (cell-edge layers)

| # | Network | Model owner | This doc's rules |
|---|---|---|---|
| 1 | **Power bus** | 09-power-thermal | 07 only places conduits; inter-site runs priced by 09 |
| 2 | **Thermal loop** (pumped fluid) | 09-power-thermal | habitat envelope loads Q_env (§2.5) are nodes on it; cap ≤40 thermal nodes/base (DECISIONS D27) |
| 3 | **Fluid lines** | 07 | one canonical resource per line; **throughput 20 t/day per standard line**; cost **0.3 t StructuralParts + 0.05 t MachineParts per km** (= 0.0035 t per 10 m cell edge), heat-trace hardware included; same per-km price for inter-site runs; freeze-protection heat-trace power per §2.5 table |
| 4 | **Data** | 07/13 | wireless site-wide free; inter-site > 10 km needs relay masts (0.1 t, 0.05 kWe each); enables robotic construction + remote ops |

UI: network layers toggle with per-edge capacity coloring.

### 2.3 Construction pipeline: DEPLOY → OUTFIT → COMMISSION (B-2)

**DEPLOY** — robot-crane or crew places/inflates. Requires a rover-crane (10-vehicles) or 2 crew EVA.
- Rigid: 6 h. Inflatable: 12 h. Rough terrain ×1.5.
- ISRU-built = local mass ÷ build-machine rate (machines are 05 content):
  | Machine | Rate | Worked example |
  |---|---|---|
  | Sinter printer | 2 t/day | HAB-07: 120 t → 60 days |
  | Filament winder | 0.5 t/day wound fiber | HAB-18: 6 t BasaltFiber → 12 days (glass furnace parallel) |
  | Ice casting | 5 m³/day | Titan Ice Vault: 80 t ≈ 87 m³ → 18 days |
  | Ice Home water fill | 1 m³/day | HAB-09: ~400 days, staged occupancy |
  | Gallery excavation | excavator-chain throughput (05) | energy = 04 e_dig |

**OUTFIT** — consumes StructuralParts / Electronics / MachineParts =
**8% / 1.5% / 0.5% of IMPORTED mass**, plus crew-hours = **4 h per tonne of imported mass**
(robots count at 0.5× rate, T2+). Basis rule: IMPORTED mass only — ISRU-built modules use the
liner/hatch/fittings mass, never the shell/excavation mass.

**COMMISSION** —
- Pressurize from site gas inventory: `m_gas = V · 1.20 kg/m³` (101.3 kPa, 293 K); **×1.45 Titan iso-baric** (146.7 kPa).
- 24 h leak check: `measured_leak = L_cat · m_lk`, `m_lk ~ LogNormal(μ=0, σ=0.5)` drawn ONCE
  at first check (≈8% of modules draw m_lk > 2; robot-built same σ).
- PASS if measured < 2 × L_cat. FAIL → find-and-fix loop: 4 crew-hours + 0.1% module-mass
  MachineParts per attempt; each attempt **halves m_lk**, then 24 h re-check.
- 3 consecutive failures → module **DEFECTIVE** (F-14: refund path in 12, or scrap to StructuralParts at 30%).
- (B-2a) Habitable ONLY after commission. Uncommissioned = vacuum-equivalent storage; berths,
  leak and thermal sim activate at commissioning.

### 2.4 Berm / regolith shielding stage (B-2b, optional, repeatable)

- Cost = regolith mass (tailings or excavation) + hauling (05) + above frame threshold an
  arched roof frame of **0.02 t StructuralParts per m² covered**.
- Frame thresholds: **rigid** modules — frame needed when berm areal mass > `0.1 × ΔP / g_local` [t/m²];
  **softgoods/inflatable** — frame needed above **1 t/m² regardless** (restraint-layer creep;
  violating = F-19: permanent leak +0.02%/day per excess t/m²).
- Canonical guidance: 2–3 t/m² regolith overhead per habitat (04 canon). Crater-wall cells halve berm cost.
- Coverage fractions for the dose law: side ring only f_i = 0.5 (zenith open); roof slab only
  f_i = 0.5; berm + roof ⇒ f_open = 0. Hull always counts as an extra full-sky (f=1) stack.
- **Buried** (thermal definition) = full-coverage ≥ 0.5 m: module switches to constant T_deep
  and gains MMOD immunity; maintenance ×0.75.

### 2.5 Thermal envelope & heat trace (B-5)

- Vacuum bodies (radiative through MLI): `Q_env = ε_eff · σ_SB · A · (T_in⁴ − T_env,eff⁴)`,
  ε_eff = 0.03 (game constant). Half-sky rule: `T_env,eff⁴ = 0.5·T_ground⁴ + 0.5·T_sky⁴`,
  T_sky = 3 K, T_ground = T_day/T_night from §1.5. Lunar 294 K cabin ≈ −7 W/m² gain (day) /
  +12.6 W/m² loss (night). Buried → same formula with T_env,eff = T_deep.
- Atmosphere bodies (conductive): `Q_env = U · A · (T_in − T_ext)`, `U = k_ins / t_ins`.
  Insulation classes: fiber batt k = 0.02 (Mars), aerogel k = 0.014 (T2, MANDATORY Titan),
  microporous k = 0.03 @ 700+ K (Venus surface). Standards: Mars 10 cm → U = 0.20;
  Titan 30 cm aerogel → U = 0.047 → ≈9.4 W/m² @ ΔT = 201 K; Venus aerostat 2 cm → U ≈ 1.0.
- Glazing: night loss 150 W/m² (Moon/Mars) sans shutters; day gain 0.7 × S_local × A_glaz.
- **Heat-trace, W per metre of exposed fluid line**: Moon day 0 / night 2; PSR 6; Mars 5 (night);
  Titan 16; Europa 8; Mercury night 2 (day: lines MUST be buried — 700 K surface); Venus aerostat 0.
  Unpowered trace on a cold body freezes the line in 2–12 h; Water line bursts at thaw (+1 repair task).
- **Cooldown clock**: C_th = 900 J/K per kg module dry mass [LUMPED];
  `dT/dt = −(Q_env + Q_trace)/C_th`. Worked: Titan 10 t longhouse @ 5 kW loss → 2.0 K/h →
  ~25 h from 294 K to the 244 K survival floor; Moon same hab ~3.5 days. First-class scheduler
  events; warp auto-drops at T−6 h.
- External temperature closed-form (B-9a, no per-tick weather):
  `T_ext(t) = T_night + (T_day − T_night) · clamp(sin(π · t_frac_daylight), 0, 1)^0.7`,
  with f_lit = lit fraction (default 0.5; Moon polar rim 0.8–0.9); lit while
  `t mod P_cycle < f_lit · P_cycle`, else T_ext = T_night. Titan/Venus-band: constants.

### 2.6 Radiation & shielding (B-6, canon law owned by 08 §3.6; A3 ratified)

```
f_GCR(σ) = F(σ) + 0.70 · exp(−σ/30)
  F(σ) = 0.30                              σ ≤ 1,000 g/cm²   (the floor)
  F(σ) = 0.30 · exp(−(σ−1,000)/1,000)      σ > 1,000 g/cm²   (A3 deep-shield decay)
f_SPE(σ) = exp(−σ/12)

D_in = D_site,GCR·[f_open + Σ f_i·f_GCR(σ_i)] + D_SPE(t)·[f_open + Σ f_i·f_SPE(σ_i)]  [mSv/day]
```
- Material-blind areal density, summed hull + berm + water walls [SIMPLIFIED].
- Worked canon: Moon 1.37 → 2 m regolith (330 g/cm²) → 0.41 mSv/day; 1 t/m² berm → 0.45.
  Mars 0.67 → 1 m regolith → 0.20. 2 t/m² is within 1% of the floor — tonnes beyond buy SPE
  blackout (f_SPE(200) ≈ 6×10⁻⁸), thermal stability, MMOD immunity, not GCR margin.
- **SPE events**: design envelope = Aug-1972 class, 1,000 mSv free-space @ 1 AU over 36 h,
  scaling ×(1 AU/d)²; typical 10–100 mSv. Warning exists 30–60 min after flare flag ONLY if a
  solar-monitor sat with Sun LOS + data link exists (else unannounced — F-18).
- **Shelter rule (B-6e)**: compliant = ≥35 g/cm² water-eq over 4π around ≥1.5 m³/crew.
  Design event behind 35 g/cm² ≈ 54 mSv; in a 0.5 g/cm² suit ≈ 960 mSv.
- Dose ledger: per-crew cumulative mSv integration; scheduler precomputes shelter windows;
  warp auto-drops when projected event dose > 50 mSv (amber).

### 2.7 Pressure vessels: tension vs buckling (B-3)

**(a) Internal pressure — tension (Moon, Mars, orbital, asteroid liners):**
```
m_hull = max( k_geom · ΔP·10³ · V · ρ / (σ_a·10⁶) ,  ρ_areal,min · A )   [kg]
k_geom = 1.5 sphere · 2.0 cylinder (incl. heads) · 2.5 irregular/toroid
ρ_areal,min = 8 kg/m² rigid · 6 kg/m² softgoods
```
Exception: liners inside excavated galleries (HAB-13/14) waive the floor — tension term only,
absolute min 2 kg/m².

**(b) External pressure — buckling (Venus surface, Titan/Europa ocean access):** spheres only
(cylinders ×1.6 mass); classical buckling with 0.25 imperfection knockdown (SP-8032 class):
```
P_allow = 0.30 · E·10⁶ · (t/r)²  [kPa]   ⇒   t = r·sqrt(P_ext / (0.30·E·10⁶));  m = 4π r² t ρ
```
Worked anchor: Venus surface 9,200 kPa, Ti @ 737 K (E≈90 GPa) → t/r = 0.0185 → r = 1.8 m
sphere needs t ≈ 33 mm, shell ≈ 6.0 t. **Fabric, inflatables, sintered masonry, BasaltFiber:
FORBIDDEN as external-pressure hulls — UI must refuse.**

**(c) Iso-baric (Titan):** cabin = ambient 146.7 kPa → ΔP ≈ 0 → minimum-gauge hull; budget
goes to insulation. A 101.3 kPa cabin on Titan = 45.4 kPa external crush = buckling case;
UI warns, physics doesn't forgive (F-17: vented below 120 kPa → 26.7 kPa crush → hourly
buckling-damage rolls until equalized).

**(d) Pressurized ISRU masonry:** compression structures can't hold internal pressure by weight
(ballast needed = ΔP/g: 62.5 t/m² Moon, 27.3 t/m² Mars). Every pressurized ISRU structure
needs an internal tensile liner sized by (a); masonry provides shielding/MMOD/thermal mass only.
Liner ring foundation: +0.5 t StructuralParts per airlock/hatch penetration.

**(e) Asteroid voids:** g < 0.01 m/s² → overburden negligible → galleries are liner-only
vessels (k_geom 2.5), rock = pure shielding. Monolithic bodies may count rock tensile capacity
only after a T3 bore-inspection; rubble piles NEVER.

### 2.8 Atmosphere inventory, leaks, punctures (B-4)

- Per-volume gas mass by species (08 owns composition). Leak:
  `ṁ_leak = (L_cat/100) · m_gas · (ΔP/101.3)` kg/day. Titan iso-baric: ΔP_eff = 5 kPa.
- Punctures (airless bodies, unburied): MTBF = 20 yr per 100 m² exposed hull. Severity:
  leak ×10 (pinhole, 80%) or ×100 (tear, 20%) until patched (2 crew-h + 5 kg MachineParts).
  Immunity: berm/burial or Whipple wrap (+3 kg/m², 2 cm standoff). No MMOD on Mars/Titan/Venus surfaces.
- Depress response (F-1): reserve time = m_gas/ṁ; suit alarm < 55 kPa; auto-isolate if hatches powered.

### 2.9 Maintenance & wear (B-10, canon A5 — 05 F-9 owns the ledger)

`M_spares = k_env × structure mass / yr`; k_env = 0.02 orbital / 0.04 Moon & Mars (equal) /
0.03 clean surface & Titan. Situational multipliers on top: ×0.75 buried/bermed; ×2 Venus
aerostat external (acid); ×1.5 thermal-cycling exposed (Moon/Mercury). Titan externals
stainless/composite only (Al forbidden < 120 K). Dust multiplier ×(1 + D/50) stacks.
Starved bases: leak rates +2%/day relative until serviced.

### 2.10 Dust / contamination ledger (B-7) — per base, D ∈ [0, 100]

Gains: +1.0 per AL-1/AL-2 EVA cycle; +0.1 per suitport cycle; +5 unwashed vehicle dock;
Mars storms +15 regional / +20 global; ambient +0.1/day Mars, +0.05/day Moon-ops, 0 Venus/Titan.
Reductions: housekeeping 0.5/crew-hour; HEPA −1/day (0.2 kWe + 5 kg MachineParts cartridge per
30 days); sintered pads/roads halve vehicle+ambient gains; EDS coatings halve EVA gains (T2).
Effects: maintenance ×(1 + D/50); D > 40 respiratory condition (08); D > 70 seal-failure roll
2%/day per module (failed module leak ×2). Mars perchlorate sub-ledger: exposure 0.01·D
points/day; wet-wipe (0.5 kg Water/EVA) + D < 30 holds zero; greenhouse soil bake-out
+0.3 kWh/kg. Venus acid ledger replaces dust (upkeep ×2; unwashed >30 days → +50%
leak/optical). Titan cryo-fouling: AL-5 thaw mandatory.

### 2.11 Quakes (B-9c, severity rolls per D28)

Moon: shallow moonquake mean interval 18 mo/region; severity 1–5 at P = [.40,.30,.15,.10,.05];
≤3 cosmetic. Severity 4+: rigid couplings without flex joints (0.2 t MachineParts each) take
leak ×5 + repair task. Mars: same table shifted down one (severity = max(1, roll−1)).

---

## 3. PER-BODY ENGINEERING PACKAGES (implementable constraint sets)

### 3.1 Moon (Acts 1–2, T1–T2)

| Constraint | Implementation |
|---|---|
| 101 kPa ΔP, vacuum | tension hulls §2.7a; pumped airlocks; leak ledger |
| 354-h night (708.7 h cycle), 390/95 K | MLI radiative model; night storage/fission sizing (09); exposed wear ×1.5 |
| Burial = free thermal stability | full berm ≥0.5 m ⇒ constant T_deep 250 K (Apollo HFE) |
| Dose 1.37 mSv/day + SPE | berm 1–3.3 t/m² → 0.45–0.41 mSv/day (floor); HAB-17 shelter |
| Electrostatic dust | dust ledger on; suitports + EDS; sintered pads/roads |
| MMOD | puncture rolls unless bermed/Whipple |
| Moonquakes ~M5 | flex couplings or leak ×5 on severity 4+ |
| PSR ops 25–40 K | waste heat >110 K in PSR degrades ice 1%/yr → mast radiators (+15% radiator mass) or rim siting + 2–8 km cable; PSR digging wear ×2; suit 2-h cold limit |
| Landing ejecta (C23) | sintered Landing Pad = 200 t sinter; without it each landing within 2 km adds +5 D + puncture roll on unbermed modules |
| Package structures | polar Rim Power Station site tag (80–90% lit, 10 m masts); PSR Ice Plant pairing |

### 3.2 Mars (Act 3, T2)

| Constraint | Implementation |
|---|---|
| 0.61 kPa CO2, ΔP ≈ 101 kPa | tension hulls; cheap fiber insulation (U = 0.20) |
| Dust storms (03 S-9 canon) | regional: τ→2.0–4.0, U(5,40) sols, spread p=0.15/sol to adjacent sectors, in season Ls 180–330; global: p=0.33/Mars-yr @ Ls 200°±30°, all sectors τ→U(4,9), U(60,100) sols, decay e-fold 25 sols. Solar `f_dust = max(0.04, exp(−0.45·τ))`. Soiling −0.2%/sol clear, −2%/sol storm; wind-cleaning event p=0.005/sol. Concentrating solar takes ×exp(−τ) direct-beam — storms kill it |
| Perchlorates 0.4–0.6 wt% | sub-ledger §2.10; wet-wipe stations; dust-locks; soil bake-out |
| Dose 0.67 mSv/day | 1 m regolith → 0.20 mSv/day; or full HAB-09 → 0.22; atmosphere column 16.4 g/cm² already in D_site (f_SPE ≈ 0.26 outdoors → scaled design event ≈ 90–135 mSv) |
| −90 °C nights, 24.66 h sol | mild: heater node per 250 m² |
| Marsquakes | severity table shifted −1 |
| Templates | Classic ISRU Base (intake + Rodwell + Sabatier + HAB-09); Glazed Agri-Dome (HAB-06) |

### 3.3 Venus aerostat 50–56 km (Act 4; robotic T2 / crewed T3) + surface T4

**Float rules (B-8) — implement exactly:**
```
L_net(h) = ρ_amb(h) · (1 − 29/43.45) = ρ_amb(h) × 0.333   [kg lift per m³ envelope]
ρ_amb: 1.28 kg/m³ @ 52 km (81 kPa, 330 K) … 0.80 kg/m³ @ 56 km (45 kPa, 293 K)
Canonical station 54 km: ≈60 kPa, ≈311 K, ρ ≈ 1.0 → L_net = 0.33 kg/m³
Helium option (imported): L_net = 0.84 kg/m³ @ 55 km (2.7× better; inert volume)

FLOAT CONDITION: m_total ≤ 0.95 · L_net(h_f) · V_envelope    (5% reserve MANDATORY)
Altitude response: Δh ≈ −H · ln(m_new/m_old),  H = 6.5 km scale height
Ballonet trim authority: ±2 km without venting
KILL BANDS: < 48 km (1.4 atm, 366 K) over-temp alarms; < 45 km envelope failure;
            > 62 km UV/acid degradation ×2 + lift thins
```
- **Double-jeopardy (air-filled T3)**: cabin gas IS lifting gas. Leak of fraction φ sinks
  `Δh ≈ H·ln(1/(1−φ))` ≈ 65 m per 1% — pressure alarms double as altitude alarms (F-5;
  repair = acid-suit EVA patch, 2 crew-h per 10 m² hole-equivalent). Makeup: N2+O2 from
  atmospheric intake chain (04). Helium cells (T2 starters) decouple lift from cabin.
- Envelope spec: HAB-12 = 10,000 m³ unit, 1.3 t FEP/Vectran laminate @ 0.35 kg/m², lifts
  3.3 t gross @ 54 km, gas loss 0.5 kg/day (VEGA anchor). AR-ENV deploy variant: 11,700 m³,
  inflates in ≈20 min during parachute descent.
- **Cloud Base Keel**: modules occupy keel SLOTS (not grid cells); build rule
  `Σ mass ≤ 0.95 · L_net · V_env`.
- Day/night: super-rotation lap ≈ 6 Earth days → ~72 h darkness/cycle; solar 780–1,820 W/m²
  by band (54 km ≈ 1,430), +0.15 f_atm absolute below-cloud albedo bonus for down-facing arrays.
- Acid: FEP/PTFE everything external; acid ledger; AL-6 rinse 0.2 kg Water/cycle; upkeep ×2.
- Dose 0.03 mSv/day [model] — no shielding needed or possible.
- Surface T4: HAB-15 buckling sphere only; robotic SiC stations from T3; crewed surface
  sortie = single C17 trophy, designed Pass 2. No tethered winch probe in v1.

### 3.4 Titan (Act 5, T3–T4)

| Constraint | Implementation |
|---|---|
| 94 K forever | 30 cm aerogel mandatory (≈9.4 W/m²); cooldown clocks (~25 h for HAB-10 @ 5 kW); heat-trace 16 W/m all lines; restart after freeze-out = 2× heater power for 12 h (F-7); cabin 244 K = survival line; <150 K = plumbing bursts |
| 146.7 kPa ambient | iso-baric rule: ΔP≈0 → min-gauge hulls; commission gas ×1.45; Earth-pressure habs = buckling case (UI warn, F-17) |
| Cryo-embrittlement | stainless/Ti/composite fittings ONLY (no Al < 120 K); AL-5 warm-lock mandatory (skip = 10%/cycle seal-crack) |
| No sun (1.5 W/m² noon) | fission only |
| Methane lakes | sea-shore cells: Sea Pumps + Titan Submarine dock; flotation if hull mean density < ρ_sea ≈ 550 kg/m³ |
| CH4 vs cabin O2 | composition drift 0.02%/day; CH4 cabin alarm at 1% |
| Ice as structure | cryo-ice allowable 5 MPa compressive [SIMPLIFIED]; Ice Vault = HAB-07 variant, 80 t cast ice, no imported sinter; keep ice < 150 K (else condition −1%/day; >200 K collapse for unpressurized — F-15) |
| Radiation | 0.01 mSv/day — free |
| Megaproject | **Titan Ocean Bore** (T4): v = P_t/(A·E_melt), E_melt ≈ 700 MJ/m³ from 94 K; 500 kWt cryobot @ 0.8 m² ≈ 3.2 m/h ≈ 11 mo boring per 25 km + 30 days per 5 km casing relay (5 t + 50 kWe each) ≈ 16 mo total per 25 km; stall >72 h unpowered = refreeze, resume +20% segment time, 5% stuck-probe loss per stall (F-9) |

### 3.5 Europa (Act 5, T3–T4) — radiation siege

**Three-component dose law (B-6f) — Europa only:**
```
D(x) = D_site · [0.9 · 2^(−x/1.5 cm) + 0.1 · 2^(−x/30 cm)] + 0.9·f_cycle · f_GCR(x_areal)
       (electrons HVT 1.5 cm ice; bremsstrahlung HVT 30 cm; GCR = half-sky 0.9·f_cycle with B-6b law)
```
- Taught rule: **4 m ice overhead → ≈0.32 mSv/day anywhere** (<0.5 mSv/day crossed at ≈3.4 m).
  30 m roof (≈2,750 g/cm²) → ≈0.05 mSv/day (A3 decay). Trailing-apex surface = 225 mSv/h →
  EVA budgets in minutes; leading hemisphere 200 mSv/day → ~1 h sorties.
- **Hard gate: crew may not land until robots commission a buried habitat** (Act 5 gating).
- Robots: Clipper-style vaults +0.3 t each, electronics lifetime ×20 (without: MTBF ×20 burn, F-8).
- HAB-14 galleries melted 6–30 m deep by construction cryobots; spoil refreezes as plug;
  walls ~100 K → heaters + liner standoff; MLI + heat trace 8 W/m.
- **Callisto staging package** (HOPE): crewed base at 0.14 mSv/day; lunar-pattern hulls;
  ~1 t/m² berms → 0.05 mSv/day belt-component; T_deep 120 K burial; dust ledger OFF;
  supervised autonomy to Europa robots at 4.0–8.5 s one-way light time (no joystick teleop).
- **Europa Ocean Bore**: E_melt ≈ 620 MJ/m³ from ~100 K; 20 km shell @ 500 kWt/0.8 m² ≈
  3.6 m/h ≈ 8 mo boring + 4 casing stations × 30 days ≈ 12 mo total.

### 3.6 Enceladus (Act 5, T3)

| Constraint | Implementation |
|---|---|
| g = 0.113 m/s² | anchored foundations: 4 microspine pads per module; hoppers > wheels |
| 75 K vacuum | MLI suffices (no convection) |
| Plume fallout | fissure-adjacent cells: PV fouling +0.1%/day — don't site PV there |
| Vent variability | Plume-Curtain Collector output ±50% on 1.37-day tidal cycle |
| Dose ~1 mSv/day [model] | standard berm rules |
| Structures | Plume-Curtain Collector (T3): 20–100 kg/day pre-mixed ocean material (Water .93 / NH3 .01 / CO2 .03 / organics+salts .03) — concept-level, open question 6; South-Polar Shaft (T4): 2–5 km shell = cheapest ocean access (8× shorter than Europa) |

### 3.7 Asteroids — NEA & belt (Acts 3–4, T2–T3)

| Constraint | Implementation |
|---|---|
| µg anchoring | 04 M-6: microspines 250 N, bolts 2,000 N; excavation debris rule M-6.3 |
| No overburden weight | liner-only galleries (§2.7e); rock = shielding never containment on rubble |
| GCR 1.8·f_cyc flat | ≥10 m rock (≈1,500 g/cm²): f_GCR ≈ 0.18 → 0.21–0.44 mSv/day over cycle, SPE-immune; 30 m (≈4,500 g/cm²) → 0.011–0.022 — Earth-surface-class for zero imported mass |
| Rotation | galleries aligned to spin axis (≤2.2 h rubble limit, 04 M-6.4); off-axis milli-g not health-relevant |
| Thermal | interior dead-stable; surface kit cycling wear ×1.5 |
| Structures | Gallery Network (HAB-13 stacks — cheapest big volume in game at T3); Surface Collar Station (dock + airlock + comms, 8 t) |

### 3.8 Mercury (Act 4 optional, T3)

| Constraint | Implementation |
|---|---|
| 176-day solar day; 700 K day / 100 K night | polar/PSR siting (Moon-pattern; ice grade roll 0.5/0.8/0.95) OR Terminator Crawler HAB-16 (≥3.63 km/h equatorial = 87.1 km/day; ×cos φ at latitude) |
| SPE ×6.7 mean, ×10.6 perihelion | shelter sized to ×10.6 case, non-negotiable; warning needs inner-system monitor sat |
| GCR 1.8·f_cyc + SPE | berm rules as Moon |
| Solar 6,270–14,450 W/m² | 10× Earth PV → Mass Driver Port (launcher = 05; 07 owns 20-cell site + pad + 2 MWe substation) |
| Day thermal siege | lines buried by day (700 K); radiators poleward; crawler radiators trail in own shadow |
| Failure | F-11 race against dawn: time-to-700 K = buffer distance ÷ 87.1 km/day |

---

## 4. GAP vs CODE

Current implementation (`aphelion/game/basebuild.py` + `aphelion/sim/ledger/network.py` +
`aphelion/render/base_art.py`): a **flat module list** per site. CATALOG has 12 entries
(ISRU/power/storage units, one generic 4-bed `hab_module`), each a ledger transformer with
price_m / power_kw / recipe / mtbf_d / site-kind gating. LedgerNetwork gives pooled buffers,
piecewise-constant rate solve, power coupling with battery, pre-rolled failures, boundary
events. base_art.py draws one sprite per CATALOG key on a 1D terrain strip with 5 site-kind
palettes. **None of the 07 spatial/structural/environmental machinery exists.** Gaps:

### 4.1 Catalog & data model
- No HAB-01…18 / AL-1…7 / AR-* entries; `hab_module` (4 beds, 25 $M) matches nothing in §1.1.
- Modules lack: class (rigid/inflatable/ISRU/buried), grid footprint, imported-vs-local mass
  split, V_press, canonical berths, L_cat leak %/day, pressure rating, tier gating per §6,
  hotel-load formula. No per-module $ cost source yet (12 owns; placeholder prices in code).
- Site model is a dict with `kind` + `solar`; no terrain cells, no §1.5 environment columns
  (g, P_amb, T_day/T_night, T_deep, P_cycle, f_lit, dose, S_local).

### 4.2 Grid & networks
- **No placement grid at all**: need 64×64 cells @ 10 m, rectangular footprints, facing,
  per-cell terrain classes (flat/rough/crater-wall/PSR/sea-shore/fissure), 16 tailings slots.
- **No network layers**: ledger pools every resource site-wide with zero topology. Need four
  cell-edge layers — power conduits, thermal loop nodes (≤40/base, D27), fluid lines (one
  resource each, 20 t/day cap, 0.0035 t parts per edge, freeze/heat-trace state), data
  (relay masts >10 km). The pooled-buffer rule can stay per 13, but edge existence/capacity
  must gate which modules join the pool, and line freezing must sever flows.
- Two grid exceptions need their own containers: aerostat keel slot list (mass-budget build
  rule) and gallery stacked-deck interiors.

### 4.3 Construction pipeline
- `add_module()` is instantaneous and free. Need the three-stage Deploy→Outfit→Commission
  state machine with durations (6 h/12 h/ISRU machine rates), rough-terrain ×1.5, crane/EVA
  prerequisite, Outfit consumption (8/1.5/0.5% of imported mass + 4 crew-h/t), commissioning
  gas draw (1.20 kg/m³, ×1.45 Titan), the LogNormal(0, 0.5) leak-check loop, DEFECTIVE flag,
  and the B-2a "uncommissioned = not habitable" rule.
- No berm stage: regolith mass per m², frame-threshold rules (rigid ΔP-based vs softgoods
  1 t/m²), crater-wall ×0.5, buried thermal/MMOD/dose state, F-19 creep failure.
- ISRU build machines (sinter printer, winder, ice caster, excavator chain) absent (05 scope,
  but DEPLOY durations depend on them).

### 4.4 Structures & atmosphere physics
- No pressure-vessel sizing (tension formula + material table; buckling formula + sphere
  rule; iso-baric ΔP≈0 path; masonry-liner mandate; UI refusal of fabric-under-crush).
- No gas inventory per volume, no leak integration `(L_cat/100)·m_gas·(ΔP/101.3)`, no
  puncture MTBF rolls / pinhole-vs-tear severity, no airlock cycle losses/energies, no
  composition-drift on Titan, no F-1 depress reserve-time events.

### 4.5 Environment simulation
- No T_ext closed-form curve, no half-sky T_env,eff, no Q_env (radiative MLI / conductive U·A),
  no glazing loads, no heat-trace W/m, no cooldown clocks (C_th = 900 J/K·kg) as scheduler
  events. Reactor heat_kw / radiator rejection exist as bare numbers but nothing computes
  habitat envelope loads.
- No radiation: f_GCR/f_SPE law with A3 deep-floor decay, coverage-fraction stacks, per-crew
  dose ledger, SPE event stream + monitor-sat-gated warning, shelter compliance, Europa B-6f
  three-component law, EVA dose budgeting.
- No dust ledger D (gains/reductions/effects), perchlorate/acid/cryo-fouling sub-ledgers,
  no Mars two-class storm model (only a static `solar` site scalar), no quake severity rolls,
  no PSR heat-discipline rule.
- Maintenance: code has flat mtbf_d pre-rolls; 07 needs k_env × situational multipliers
  (buried ×0.75, acid ×2, cycling ×1.5) and dust ×(1 + D/50) feeding MTBF/spares (A5 ledger).

### 4.6 Aerostats & exotic packages
- Venus aerostat exists only as a `kinds: ("aerostat",)` tag. Need: L_net(h) lookup, float
  condition with 5% reserve, Δh = −H·ln(m ratio) trim, ballonet ±2 km, kill bands 48/45/62 km,
  double-jeopardy leak→sink coupling, keel mass budget, helium-vs-air cell types (T2/T3 per A6),
  AR-* deployment sequence, 72 h darkness power bridging.
- Nothing for: Mercury crawler kinematics (87.1 km/day race), Europa robot vaults +0.3 t /
  crew hard-gate, ocean-bore megaprojects (rate law, casing stations, stall/refreeze, F-9),
  Enceladus collectors/anchoring, gallery excavation volumes, Callisto staging, HAB-15
  cooling-plant dependency (30 kWe or cook).
- Renderer has 5 site-kind palettes; §1.5 implies ~16 environments and the base scene has no
  concept of grid placement, berms, envelopes, or keels to draw.

### 4.7 Scheduler & cross-system contracts
- LedgerNetwork's boundary machinery is the right substrate, but 07 adds new boundary classes:
  cooldown thresholds, SPE shelter windows (warp drop at >50 mSv projected), storm onsets/decays,
  line-freeze timers, terminator arrival, leak-check completions, bore stalls — all must be
  precomputed next-threshold events per the closed-form doctrine (F-20).
- Interfaces not yet stubbed: berths/habitable-volume/dose/dust → 08; Q_env/P_hotel/heat-trace
  → 09; grid/sites/tailings → 04/05; AL-4/5/6 dock interfaces → 10; settlement metrics → 12.

---

*End of build spec. Source: design/07-bases-habitats.md v1.0 + DECISIONS.md (2026-06-10).*
