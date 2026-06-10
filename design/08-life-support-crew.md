# 08 — Life Support & Crew

## 1. Overview

This document specifies the biology layer of the game: how human beings stay alive, productive, and sane inside the machines designed in `06-ships-stations.md` and `07-bases-habitats.md`, and how they function as characters with skills, morale, health, and mortality.

It defines five tightly-coupled subsystems, each with explicit formulas a programmer can implement from §3 alone:

1. **Metabolic accounting** — the per-crew, per-day mass balance of Oxygen, Water, food, and CO2, with named NASA anchors.
2. **The ECLSS loop model** — Environmental Control & Life Support System as a graph of closure fractions, from open-loop stored consumables (T0) through ISS-grade physico-chemical regeneration (T1-T2) to bioregenerative crop/algae loops (T3) approaching ~98% closure. This is the central engineering puzzle of survival.
3. **Cabin atmosphere physics** — partial-pressure tracking (ppO2, ppCO2, ppN2), leaks, fire/toxicity bands, and the depressurization model.
4. **Food & agriculture** — stored rations vs Controlled-Environment Agriculture (CEA) greenhouses, with a crop catalog (growth days, kcal/m²/day, lighting kW/m²).
5. **Crew health & character** — radiation dose tracking (mSv), microgravity/spin-gravity deconditioning, morale, skills, EVA, medical events, recruitment, death, and the design of the player character.

**Design philosophy.** Life support is a *throughput problem layered on a storage problem*. Every crewed mission is a race between depletion of stored consumables and the closure of regenerative loops. The realism doctrine forbids handwaving: a crew of four on an open loop to Mars carries **~3.6 t of consumables per 180 days** — and that single number is what forces the player up the ECLSS tech ladder.

**Ownership boundaries.** Pressurized volume, spin-gravity geometry, hull leak areas, storm-shelter modules, and Whipple penetration events → `06-ships-stations.md`. Surface-base atmospheres, regolith shielding mass, and greenhouse module siting → `07-bases-habitats.md`. Resource production/storage of Oxygen, Water, CO2, Nitrogen, Ammonia, Hydrogen, Methane, Biomass → `04-resources-isru.md`. Manufacturing of FoodRations, MedSupplies, and ECLSS spares → `05-industry-logistics.md`. Electrical power and thermal rejection for ECLSS hardware and grow-lights → `09-power-thermal.md`. Radiation *environment* (flux levels per region, SPE timing) → `03-solar-system.md`. Tier gating and research → `11-research-tech.md`. Recruitment cost, contracts, event UI → `12-gameplay-economy-ui.md`. Sim tick/integration → `13-architecture.md`.

A new canonical resource, **MedSupplies**, is introduced here as a genuinely-needed extension (manufactured per §4.6, consumed by the medbay). It is the only new resource this document adds.

## 2. Real-World Grounding

Every number below names its anchor. Sources are NASA BVAD (Baseline Values and Assumptions Document, NASA/TP-2015-218570/REV2), ISS ECLSS flight data, NASA-STD-3001, and the BIOS-3 / MELiSSA bioregenerative programs.

**Metabolic baseline (NASA BVAD, per crew member per day).**
- **Oxygen consumed: 0.84 kg/day** nominal metabolic (BVAD); rises to ~0.89 kg/day for an 82 kg crew member doing ~90 min/day heavy exercise. We use **0.84 kg/day** as the design baseline, scaled by activity (§3.2).
- **CO2 produced: ~1.00 kg/day** (BVAD ~1.04 kg; respiratory quotient RQ ≈ 0.86 mol CO2 per mol O2).
- **Dry food (solid intake): 0.62 kg/day**; "as-packaged" shelf-stable food including water and packaging ≈ **1.83 kg/day** (BVAD food system).
- **Caloric demand: ~2,500 kcal/day** design (BVAD range 2,000-3,000 depending on mass/activity/sex; ISS crews average ~2,700 kcal).
- **Water: ~3.5 kg/day** for drink + food rehydration + minimal hygiene before recycling; BVAD totals run **3.6-4.35 kg/day** with fuller hygiene. Breakdown used here: 2.0 drink + 0.5 food prep + 1.0 hygiene = 3.5 kg/day.
- **Metabolic water produced: ~0.35 kg/day** (oxidation of food).
- **Output streams**: urine ~1.6 kg/day, respiration+perspiration water vapor ~2.3 kg/day, feces (≈75% water) ~0.09 kg/day, dry solid waste ~0.03 kg/day.

**ECLSS hardware anchors (ISS).**
- **CO2 removal**: CDRA (Carbon Dioxide Removal Assembly, zeolite molecular sieve, regenerable) and Amine Swingbed; keep cabin ppCO2 below ~0.4 kPa (3 mmHg) target.
- **O2 generation**: OGA (Oxygen Generation Assembly) electrolyzes Water → O2 + H2.
- **CO2 reduction**: Sabatier reactor, **CO2 + 4 H2 → CH4 + 2 H2O** (the CH4 is vented overboard — this is why physico-chemical O2 closure is partial). ISS achieves roughly **40-50% O2 loop closure** with Sabatier.
- **Water recovery**: WRS (UPA urine processor ~75-85% + WPA) achieved ~90-93% recovery historically; with the Brine Processor Assembly ISS now reports **~98% water recovery**.

**Bioregenerative anchors.**
- **BIOS-3** (Institute of Biophysics, Krasnoyarsk, operational 1972): a 315 m³ sealed facility, two 84 m³ phytotrons with 63 m² of hydroponic conveyor. **~13 m² of crop area per person supplied ~78% of dry-food demand and essentially 100% of atmospheric (O2) regeneration**; ~8 m² of illuminated *Chlorella* algae alone balances one person's O2/CO2. Applied to **this document's own metabolic baselines** (§3.1: 0.62 kg/day dry food, 0.84 kg/day O2), the same 13 m²/person closure cuts daily dry-food resupply from 0.62 → **~0.14 kg** (78% closed) and O2 resupply from 0.84 → **~0 kg** (full gas closure; only a small buffer residual ≤ 0.05 kg for system losses). The original BIOS-3 figures (0.924 kg food, 1.22 kg O2) were for a heavier Soviet metabolic reference and are reconciled here to this doc's baselines so the loop math is consistent.
- **MELiSSA** (ESA Micro-Ecological Life Support System Alternative): a 5-compartment loop (C1 anaerobic liquefaction → C2 photoheterotrophs → C3 nitrifiers → C4 *Arthrospira* algae + higher plants → C5 crew); the engineering reference for closed-loop closure ~95-98%.

**Radiation anchors.**
- **NASA career limit: 600 mSv** effective dose, single universal standard for all ages/sexes (NASA-STD-3001, adopted 2021; based on ≤3% risk of exposure-induced cancer death).
- **Dose rates**: ISS LEO **0.5-1.0 mSv/day** (avg ~0.7); deep-space interplanetary cruise **~1.8 mSv/day** (MSL/RAD instrument, Hassler et al. 2013, 1.84 mSv/day measured Nov 2011–Aug 2012 during the **rise toward solar maximum** of cycle 24 — the true **solar-minimum** cruise dose is somewhat *higher*, because GCR flux peaks at solar minimum, so 1.8 mSv/day is a near-solar-max value, not a worst case); Mars surface **~0.64 mSv/day** (RAD on Curiosity); Moon surface **~0.4-0.6 mSv/day**; **Europa surface ~5,400 mSv/day (5.4 Gy/day)** — lethal in hours, the most hostile crewed destination in the game.
- **Acute thresholds**: Acute Radiation Syndrome (ARS) onset ~**1,000 mSv (1 Gy)** delivered in hours; LD50/60 ≈ **4,000-4,500 mSv (4-4.5 Gy)** acute, whole-body, untreated; near-certain death ≥ 8 Gy.
- **Solar Particle Events (SPE)**: episodic; a large event (e.g. an August-1972-class flare) can deliver **hundreds-to-thousands of mSv in hours** to lightly-shielded crew — the reason a storm shelter (`06`/`07`) exists.

**Gravity anchors.**
- **Bone mineral density loss: 1-1.5%/month** (hip/spine) in microgravity without effective countermeasures.
- **Muscle loss: up to ~20% in 2 weeks**, ~30% over 3-6 months uncountered.
- **Countermeasure**: ~**2 hours/day** combined resistive (ARED) + aerobic (treadmill/cycle) exercise keeps modern ISS crews near baseline.
- **Spin-gravity comfort** thresholds owned by `06-ships-stations.md §3.10`: a ≥ 3.71 m/s² halts most deconditioning; ≥ 1.62 halves it; < 1.0 cosmetic.

**Atmosphere anchors.**
- Sea-level air: 101.325 kPa total, ppO2 21.2 kPa, ppN2 ~79 kPa.
- Hypoxia threshold ppO2 < ~16 kPa; **fire-risk / flammability** band above ppO2 ~23 kPa or O2 fraction > ~30% at elevated pressure. NB: 23 kPa is a flammability threshold, **not** an oxygen-toxicity threshold — pulmonary O2 toxicity requires sustained ppO2 > ~50 kPa and CNS toxicity > ~150 kPa. (Apollo crews breathed pure O2 at ppO2 ~34 kPa for entire missions without toxicity; this document's own Exploration atm runs ppO2 19.2 kPa and the Pure-O2 atm 34 kPa — both far below any toxicity onset, but the latter is a severe fire risk.)
- **Exploration atmosphere** (NASA EVA studies): **56.5 kPa (8.2 psia), 34% O2** → ppO2 ≈ 19.2 kPa; chosen to slash EVA prebreathe.
- EVA suit pressure ~**29.6 kPa (4.3 psia) pure O2** (NASA EMU); decompression-sickness ("bends") risk governed by the tissue-ratio R = ppN2_cabin / P_suit.

## 3. Game Model

### 3.0 Integration and state

Life support is integrated per **sim hour** (scaled by time warp; `13-architecture.md`). Each crewed vessel/base holds a **Life-Support Cell (LSC)** state:

- Atmosphere: masses (kg) of Oxygen, CO2, Nitrogen, H2O-vapor, plus trace contaminants pooled into one "Trace" scalar; volume `V_press` (m³, from `06`/`07`); temperature `T` (K, from `09`).
- **CO2 accumulator** (kg): scrubbed CO2 removed from cabin air by CDRA/amine and held pending reduction by Sabatier/Bosch (§3.2, §3.3) — a store separate from cabin-air CO2.
- Stores: Water (potable), Water (grey/condensate), Water (urine/brine), FoodRations (dry kg) and/or packaged kg, Biomass (greenhouse standing crop), MedSupplies, buffer-gas Nitrogen.
- Crew list: each crew member is an entity (§3.9-3.14).

All flows are mass flows in kg; the LSC is a closed mass ledger except for documented vents (Sabatier CH4, airlock losses, leaks) and documented inputs (resupply, ISRU from `04`).

### 3.1 Per-crew metabolic baseline

Per crew member, per day, at activity level A (dimensionless multiplier, default 1.0):

| Flow | Symbol | Baseline (kg/day) | Direction |
|---|---|---|---|
| Oxygen consumed | O2_in | 0.84 · A | atmosphere → crew |
| CO2 produced | CO2_out | 1.00 · A | crew → atmosphere |
| Water drunk + prep | H2O_in | 2.5 | store → crew |
| Hygiene water | H2O_hyg | 1.0 | store → grey water |
| Metabolic water made | H2O_met | 0.35 · A | internal (already leaves via U_out + V_out) |
| Urine | U_out | 1.6 | crew → urine store |
| Water vapor (resp+persp) | V_out | 2.3 · A | crew → atmosphere (humidity) |
| Dry food eaten | F_in | 0.62 | store → crew |
| Solid waste (wet) | W_out | 0.12 | crew → waste store |

**Activity multiplier A**: sleeping 0.75; nominal work 1.0; heavy labor / EVA 1.6. Per-crew A is the time-weighted average over the day from their task schedule (§3.10). O2, CO2, metabolic water, and respiratory vapor scale with A; food and drink water are taken as roughly constant per day (appetite lags).

**H2O_met is a bookkeeping term only**: metabolic water is generated *inside* the body (oxidation of food) and exits through the already-tabulated urine (U_out) and respiratory/perspiration vapor (V_out) streams. It is **not** an additional source of cabin humidity — do **not** add it to the `dm_H2O(vap)` equation in §3.2 (that would double-count V_out). It appears in the table and the mass-balance check below solely to close the food→CO2+H2O oxidation ledger.

**Ration-dependent prep water**: the 0.5 kg/day food-prep component of `H2O_in` is a default that depends on the ration type (§3.5). With packaged or greenhouse-fresh food, prep = 0 → `H2O_in = 2.0` (drink only). With dehydrated rations (FD-DEHY), prep = 1.2 → `H2O_in = 3.2`. The 2.0 kg/day drink component is fixed; only the prep component varies.

**Mass-conservation check** (kg/day, A=1): in = 0.84 O2 + 3.5 H2O + 0.62 food = 4.96; out = 1.00 CO2 + 1.6 urine + 2.3 vapor + 0.12 waste = 5.02; balance closes to within the 0.06 kg/day of metabolic-water bookkeeping. Good enough for the sim; rounding is absorbed into the "Trace" scalar.

Humidity: respiratory/perspiration vapor (V_out) raises cabin humidity; a **Condensing Heat Exchanger (CHX)** (part of every ECLSS unit) condenses it to grey/condensate water at the same rate it is produced, rejecting latent heat to `09`. If CHX capacity is exceeded (overcrowding, CHX fault), humidity rises → condensation on surfaces, electrical-fault risk, mold morale penalty (§8).

### 3.2 Cabin atmosphere physics (partial pressures)

Each gas species X in the cabin has partial pressure (ideal gas):

```
ppX = (m_X / M_X) · R · T / V_press      [kPa, with m in kg→g, M in g/mol, R = 8.314 J/mol·K, T in K, V in m³, result /1000 for kPa]
```

Molar masses M: O2 = 32, CO2 = 44, N2 = 28, H2O = 18 g/mol. Total cabin pressure `P = ppO2 + ppCO2 + ppN2 + ppH2O + ppTrace`.

**Worked sanity check**: Destiny-class module, V = 106 m³, T = 294 K, target ppO2 = 21.2 kPa → m_O2 = ppO2·V·M/(R·T·1000) = 21200·106·32/(8.314·294) → ≈ 29.4 kg O2 resident. A crew of 4 consumes 4·0.84 = 3.36 kg/day → ~9 days of breathing buffer in the air alone before generation. Realistic.

**Atmosphere dynamics**, per hour, for each species:
```
dm_O2  = +Gen_O2  − Σcrew(O2_in)  − Leak·(ppO2 /P)
dm_CO2 = +Σcrew(CO2_out) − Scrub_CO2 − Uptake_plant − Leak·(ppCO2/P)
dm_N2  = +Makeup_N2 − Leak·(ppN2/P)
dm_H2O(vap) = +Σcrew(V_out) − CHX_rate − Leak·(ppH2O/P)
```

**CO2 removal is single-counted.** Only the scrubber (`Scrub_CO2`, CDRA/amine) and direct plant uptake (`Uptake_plant`, bioregen) remove CO2 from cabin *air*. The scrubbed CO2 is not destroyed — it enters the **CO2 accumulator** store (§3.0), which evolves as:
```
dStore_CO2 = +Scrub_CO2 − Reduce_CO2
```
The Sabatier/Bosch reducer (`Reduce_CO2`, §3.3) draws from this accumulator, **not** from cabin air. Subtracting `Reduce_CO2` from the air ODE as well would remove the same CO2 twice.

**Leak**: `Leak = k_leak · P · A_hull` (kg/h), where `A_hull` is summed module hull area (`06`) and `k_leak` a per-module tightness constant. Default tuned so a well-built station loses ~0.2-0.3 kg air/day (ISS-class). A Whipple penetration (`06 §3.9`) opens a hole of area a_hole (cm²); the escaping air is **choked (sonic)** for any breach to vacuum, with mass flow `ṁ = Cd·A·P0·√(γ/(Rs·T0))·[2/(γ+1)]^((γ+1)/(2(γ−1)))`. For air (γ = 1.4, Rs = 287 J/kg·K, T0 ≈ 294 K, Cd ≈ 0.62) this reduces to `Leak_hole ≈ C · a_hole · P` (kg/h) with **C ≈ 0.5 kg/(h·cm²·kPa)** (equivalently `0.0404·Cd·a_hole[cm²]·P[kPa]·(100/√T)` → ≈ 0.51·a_hole·(P/101) at T ≈ 294 K). So a **1 cm² hole at 101 kPa → ~51 kg/h** (not the previously-stated 1.2 kg/h, which was ~44× too small). The 106 m³ module holds ~127 kg of air, giving a pressure time-constant **τ = m_air/Leak ≈ 2.5 h** for a 1 cm² hole — survivable but a tens-of-minutes-to-act situation; a **10 cm² breach → ~510 kg/h** (τ ≈ 15 min) empties the module in minutes — a drop-everything emergency (§8). Because the leak rate is proportional to pressure, cabin pressure decays exponentially: `P(t) = P0·exp(−t/τ)`, with τ = m_air/(C·a_hole·P0) recomputed as P falls (flow stays choked until P drops below ~1.9× ambient, i.e. essentially the whole event in vacuum).

**Safe bands** (alarms drive UI and crew autonomy, §8):

| Quantity | Nominal | Caution | Critical |
|---|---|---|---|
| ppO2 | 19-23 kPa | 16-19 (mild hypoxia) / 23-27 (fire watch) | < 16 hypoxia, > 27 / O2-frac > 30% fire |
| ppCO2 | < 0.4 kPa | 0.4-1.0 (headache, fatigue) | > 1.0 impairment, > 3.0 acute, > 7 unconscious |
| P total | 50-103 kPa | 40-50 / 103-110 | < 40 (hypoxia regardless of O2%) |
| Humidity (ppH2O) | 0.8-1.6 kPa (~25-70% RH) | > 1.6 (condensation) | saturation = fog/short risk |

**Hypoxia/hypercapnia health clock**: when ppO2 < 16 kPa or ppCO2 > 3 kPa, each crew accrues an **incapacitation timer**, `t_inc = 30 min · deficit_ratio`, with the deficit ratio defined explicitly per insult:
```
hypoxia:      deficit_ratio_O2  = clamp((ppO2 − 8) / (16 − 8), 0, 1)
hypercapnia:  deficit_ratio_CO2 = clamp((7 − ppCO2) / (7 − 3), 0, 1)
t_inc = 30 min · min(deficit_ratio_O2, deficit_ratio_CO2)   (use the worse insult if both apply)
```
Hypoxia gives 30 min at ppO2 = 16 kPa, **~7.5 min at 10 kPa**, and ~0 (near-immediate) at ≤ 8 kPa. Hypercapnia gives 30 min at ppCO2 = 3 kPa, falling linearly to ~0 (near-immediate) at ≥ 7 kPa — matching the ">7 kPa unconscious" band of the safe-bands table. Death follows incapacitation by `t_death ≈ 1.5 · t_inc` if not corrected. This is the asphyxiation death path (§8).

**Atmosphere choices** (player-selectable per habitat; affects fire risk, EVA prebreathe, structural pressure load in `06`):

| Atmosphere | P (kPa) | O2 frac | ppO2 (kPa) | ppN2 (kPa) | Notes |
|---|---|---|---|---|---|
| Sea-level | 101.3 | 21% | 21.3 | 80 | Earthlike, heaviest gas mass, longest prebreathe |
| Exploration | 56.5 | 34% | 19.2 | 37 | NASA EVA atm; short prebreathe; default for deep-space hab |
| Reduced N2 | 70 | 27% | 18.9 | 51 | compromise |
| Pure-O2 low-P | 34 | ~100% | 34 | 0 | suits/emergency only; severe fire risk (Apollo 1 anchor) |

Higher O2 fraction raises fire probability in the `08`/`13` fault model (a flammability multiplier `φ_fire = max(1, (O2_frac/0.21)^3 · (P/101)^0.5)`); pure-O2 environments are flagged W-FIRE and forbidden for nominal crewed operations except suits.

### 3.3 The ECLSS loop model

ECLSS is modeled as a set of **closure fractions** η ∈ [0,1] applied to the metabolic flows, plus the hardware that provides them and the power/spares they cost. Net resupply demand is what the player must store or produce.

**Subsystem closure fractions** (the core balance levers):

| Subsystem | Symbol | Open (T0) | ISS-grade (T1-T2) | Bioregen (T3) |
|---|---|---|---|---|
| CO2 removal from air | η_CO2rm | 0 (LiOH consumed) | ~1.0 (CDRA, regenerable) | ~1.0 (uptake by plants) |
| O2 loop closure | η_O2 | 0 | 0.42 (Sabatier) → 0.50 (Sabatier+) | 0.95-0.98 (photosynthesis) |
| Water recovery | η_H2O | 0 | 0.90 → 0.98 (brine proc.) | 0.98 |
| Food closure | η_food | 0 | 0 | 0.50 (BIOS-3 level) → 0.95 (full greenhouse) |

**Net daily resupply per crew** (kg/day), given selected closures:
```
O2_resupply   = (1 − η_O2)   · 0.84 · A        (or: regenerate O2 by electrolysis of recovered Water; see below)
H2O_resupply  = (1 − η_H2O)  · 3.5
Food_resupply = (1 − η_food) · 0.62  (dry)
N2_resupply   = Leak·(ppN2/P)  + airlock losses     (buffer gas makeup only)
```

**Physico-chemical O2 path (T1-T2, the ISS loop), explicit flows:**
1. CDRA scrubs CO2 from air (η_CO2rm ≈ 1.0) into a CO2 accumulator.
2. OGA electrolyzes Water: `2 H2O → 2 H2 + O2`. Per 1 kg O2, consumes 1.125 kg Water, yields 0.125 kg H2.
3. Sabatier reduces accumulated CO2: `CO2 + 4 H2 → CH4 + 2 H2O`. Per 1 kg CO2 reduced: needs 0.182 kg H2, makes 0.364 kg CH4 (**vented**, or captured to Methane store if T2 "Bosch-loop" upgrade), recovers 0.818 kg Water.
4. The vented CH4 carries away carbon and hydrogen; the unrecovered fraction of O2 (the oxygen atoms that leave as the part of CO2 not reduced, plus venting losses) sets η_O2 ≈ 0.42. Upgrading to a **Bosch reactor** (`CO2 + 2 H2 → C + 2 H2O`, deposits solid Carbon) pushes η_O2 → 0.50+ at the cost of carbon-soot maintenance (higher spares).

**Implementation rule**: the sim does NOT simulate every reactor; it applies η_O2 and η_H2O to compute net resupply, and separately debits **electrical power** and **MedSupplies/ECLSS-spares** (kg/day) per installed unit from §4.1, and debits the **Water → electrolysis → O2** conversion when an OGA is present so that a water-rich base can be O2-self-sufficient even at η_O2 = 0.42 (the "missing" oxygen comes from electrolyzing *imported or ISRU* Water, not from the loop). This is the key Act-2 gameplay: lunar/Mars Water from `04` feeds OGA to make breathing O2 locally.

**Bioregenerative path (T3), explicit:** crops and algae photosynthesize `6 CO2 + 6 H2O → C6H12O6 + 6 O2`, simultaneously closing O2, CO2, Water (transpiration → CHX → potable), and food. Closure approaches η = 0.98 but never 1.0 (inedible biomass, system losses, buffer for crop failure). Requires the greenhouse subsystem (§3.6), large power for lighting (§3.6, `09`), and an agronomist (§3.9). The remaining 2-5% is supplemented from stores — a bioregen base is resilient but not infinitely so; a crop blight (§8) drops η_food and forces ration draw.

**Worked closure comparison** — crew of 4, 180-day transfer:

| Loop | O2 (kg) | Water (kg) | Food dry (kg) | Total consumables (kg) |
|---|---|---|---|---|
| Open (T0) | 605 | 2,520 | 446 | **3,571** (+packaging/tankage) |
| ISS-grade, η_O2=0.42, η_H2O=0.93, water-fed OGA | electrolysis of recovered water → ~70 net | 176 | 446 | **~692** + ECLSS hardware ~1.5 t |
| Bioregen, η=0.98 all, η_food=0.95 | ~12 | ~50 | ~22 | **~84** + greenhouse ~16 t + 12 kW/crew |

The table is the whole motivation curve: open-loop is fine for an Act-1 week in LEO, ruinous for Mars; the greenhouse only pays for itself on multi-year or permanent settlements (Act 3+). Hardware mass and power are owned by `06`/`07`/`09`; consumable masses above are this document's.

### 3.4 Water loop detail

Three water pools: **Potable**, **Grey/condensate**, **Urine/brine**. Daily routing per crew:
```
Potable −2.5 (drink+prep) −1.0 (hygiene)
Grey   +1.0 (hygiene) +2.3 (vapor via CHX) +0.818·(CO2 reduced) (Sabatier water)
Urine  +1.6
WPA processes Grey → Potable at η_WPA = 0.93
UPA processes Urine → Grey at η_UPA = 0.85   (brine residue stored; BPA upgrade recovers brine → overall 0.98)
```
Net potable makeup = consumed − recovered = 3.5 − η_H2O·3.5. With η_H2O = 0.98, makeup = 0.07 kg/day/crew. A water-recovery fault (UPA/WPA down) drops η_H2O to 0 instantly — the crew runs on Potable stores while the player repairs; this is a common Act-2 emergency.

### 3.5 Food & agriculture

**Stored food** comes in two forms the player chooses per mission:
- **Dehydrated rations**: 0.62 kg dry/crew/day, but draws **1.2 kg Water/day/crew** from the loop for rehydration. This 1.2 kg **replaces** (does not add to) the 0.5 kg/day food-prep component of the §3.1 baseline → `H2O_in = 2.0 drink + 1.2 prep = 3.2 kg/day` when FD-DEHY is the ration (net +0.7 kg/day over baseline). Nearly all of it re-enters the loop as vapor/urine and is recovered at η_H2O, so the *makeup* cost is small even though the *draw* is large; size potable stores to the +0.7 kg/day during any UPA/WPA outage. Lightest to ship.
- **Packaged (wet/shelf-stable)**: 1.83 kg/crew/day, no water draw, no prep power (food-prep water = 0 → `H2O_in = 2.0 kg/day`, drink only). Best for short missions and emergency reserve.
- Both have a **shelf life** (T-dependent): dehydrated ~5 years, packaged ~1.5 years; expired food → spoilage (§8) and a morale penalty if eaten.

**Caloric model**: each crew needs **kcal_req = 2,500 · A_metabolic** kcal/day (A_metabolic from activity, range ~2,000-3,000). Food provides kcal by type; if daily kcal intake < kcal_req, the crew accrues a **starvation deficit** (§3.9 health). Survival without food: incapacitation begins after a cumulative deficit ≈ 3-4 weeks of zero intake (humans survive ~30-45 days without food, faster with cold/labor); the sim uses a body-energy reserve of **~90,000 kcal** that depletes/refills, with deconditioning and death when it hits zero.

**Greenhouse (CEA) model.** A greenhouse provides grow area `Area_grow` (m², from `06`/`07` greenhouse modules) split among crops. Each crop c has, per m² of its allocation:
```
yield_c (kcal/m²/day) , light_c (kW/m² average) , water_c (L/m²/day transpired) , cycle_c (days to first/again harvest)
```
Per day a greenhouse produces `Σ_c Area_c · yield_c` kcal of food (added to a fresh-food store; fresh food gives a morale bonus and full nutrition), consumes `Σ_c Area_c · light_c` kW electrical (from `09`), transpires `Σ_c Area_c · water_c` L/day (recovered via CHX at ~0.98), fixes CO2 and releases O2 stoichiometrically with the kcal fixed (photosynthesis), and consumes **Ammonia** fertilizer (`04`) at **~0.03 g N per gram of edible dry biomass** (crop dry matter is only ~1–5% nitrogen, ~0.01–0.05 g N/g; protein-rich crops at the high end) plus a trickle of micronutrients (pooled as MedSupplies-adjacent "AgriSupplies", folded into MedSupplies for v1). In a **closed** bioregen loop most of this nitrogen is recycled from crew urine/waste (the MELiSSA nitrifier stage), so the *imported* Ammonia-N makeup is only the ~2% loop leakage — roughly an order of magnitude smaller than the gross uptake.

**Crop establishment lag**: a freshly planted bed yields nothing until `cycle_c` days pass (staggered planting smooths this); a brand-new greenhouse therefore cannot feed crew for the first ~2-3 months — they must carry rations to bridge. This is a deliberate Act-3 logistics trap.

**Algae photobioreactor** (separate part): primarily an **O2/CO2 balancer and protein source**, not staple calories. Per BIOS-3, **~8 m² illuminated *Chlorella* per crew balances O2/CO2**; in-game an algae unit closes O2 at high efficiency in less volume than crops but provides limited palatable calories (protein paste; monotony morale penalty if relied on).

**Per-person area benchmarks** (design figures, anchored to BIOS-3 and NASA CELSS):
- O2/CO2 balance only: ~8 m² algae *or* ~10 m² leafy crops per crew.
- ~78% of dry food + O2 (BIOS-3 demonstrated): **~13 m² staple crops per crew**.
- Full balanced diet (calories + protein + vegetables + morale variety): **~40 m² per crew**, costing **~10-12 kW grow-light power per crew** (the dominant power load that ties greenhouses to nuclear power in `09`). **This 40 m² is deliberately over-sized.** Summing `Σ(Area_c · yield_c)` for the recommended layout (§4.2: ~22 m² staples + 10 m² protein + 8 m² veg/fruit) against the catalog yields gives **~6,300 kcal/day ≈ 2.5×** the 2,500 kcal/day requirement — an intentional margin for crop failure, dietary variety, staggered-planting gaps, and harvest/processing losses. *Pure staple-calorie closure* needs only **~16.7 m²/crew** (consistent with §2's BIOS-3 figure: 13 m² = 78% of dry food). The 40 m² figure and the catalog yields are therefore reconciled: 40 m² is the *resilient, palatable* full diet, ~16.7 m² is the *minimum* full-calorie diet. **Surplus disposition:** fresh output first fills a capped fresh-food store (the morale +12 source, capped at ~14 crew-days); overflow beyond the cap is dried and added to the **FoodRations** reserve (§4.3) — surplus is banked, not wasted, and a sustained shortfall draws this buffer down before triggering the §8 food-shortfall path.

### 3.6 Radiation health model

Each crew member carries two **distinct** dose accumulators (do **not** equate them):
- **Career effective dose** `D_career` (**mSv**, effective dose = absorbed × quality factor Q) — chronic, stochastic (cancer) risk. Uses the NASA 600 mSv anchor.
- **Acute absorbed dose** `D_acute` (**mGy**, absorbed dose) over a rolling **24-hour window** — deterministic (ARS) risk. ARS thresholds are physically defined in absorbed dose (Gy), so this accumulator is tracked in mGy, separate from the mSv career accumulator.

**Quality factor (effective vs absorbed).** Effective dose (mSv) = absorbed dose (mGy) × Q, where Q ≈ 1 for SPE protons and Q ≈ 3 for the GCR heavy-ion mix (a deliberate v1 simplification; real GCR Q spans ~3–20 — see Q5). The `Ḋ_env` table below is given as **effective** dose-rate (mSv/day) and feeds `D_career` directly; the **absorbed** rate feeding `D_acute` is `Ḋ_env / Q`. Consequence: an SPE (Q ≈ 1) contributes almost equally to both accumulators, whereas chronic GCR (Q ≈ 3) adds ~3× more to the career (mSv) total than to the acute (mGy) total — which is why GCR drives the cancer limit but rarely the ARS limit.

**Environmental dose rate** at the crew's current location (per `03-solar-system.md` region table), before shielding:

| Region | Ḋ_env (mSv/day) | Anchor |
|---|---|---|
| Earth surface / under atmosphere | ~0.01 | sea-level background |
| LEO (ISS, 400 km) | 0.5-1.0 | ISS dosimetry |
| Van Allen transit (brief) | ~2,400 peak (≈100 mSv/**h** at peak) | inner-belt protons; transient, crossed only briefly |
| Cislunar / interplanetary cruise | 1.8 | MSL/RAD |
| Moon surface | 0.4-0.6 | half-sky + RAD-analog |
| Mars surface | ~0.64 | Curiosity/RAD |
| Main belt / Ceres | ~1.8 | GCR-dominated |
| Jupiter system (outside Europa) | 10-100+ | magnetosphere |
| **Europa surface** | **~5,400** | 5.4 Gy/day, lethal in hours |
| SPE event (unshielded, peak) | +100 to +3,000 over hours | Aug-1972-class |

**Reading the table for the shielding formula.** Each region's tabulated `Ḋ_env` is its **GCR background** rate and is used as `Ḋ_GCR` (the quantity the GCR shielding factor multiplies). `Ḋ_SPE` is **zero except during an active SPE event**, which supplies the `+100…+3,000 mSv-over-hours` term (the last row) as `Ḋ_SPE` for the duration of the event. The Van Allen value is a transient peak crossed only briefly during transfer (mark it per-hour, not a sustained daily rate). Where a region is GCR-dominated, set `Ḋ_GCR = Ḋ_env` and `Ḋ_SPE = 0` between events.

**Shielding.** Habitat areal density `σ` (g/cm²) is the sum of hull, dedicated shielding, stored Water walls, regolith overburden (`07`), and any structure between the crew and the sky (owned/aggregated by `06 §3.9` and `07`). The dose multiplier differs for GCR vs SPE:
```
GCR:  f_GCR(σ) = 0.30 + 0.70 · exp(−σ / 30)      (floor 0.30 — secondaries prevent full blocking; thick shields give diminishing returns)
SPE:  f_SPE(σ) = exp(−σ / 12)                    (strong attenuation; ~20 g/cm² cuts an SPE ~80%)
```
Effective rate `Ḋ = f_GCR(σ)·Ḋ_GCR + f_SPE(σ)·Ḋ_SPE`. Worked: storm shelter with water walls σ = 35 g/cm² → f_GCR = 0.30+0.70·exp(−1.17) = 0.52; f_SPE = exp(−2.92) = 0.054. So GCR is only halved (live with it; minimize transit time and use time warp wisely), but an SPE is nearly eliminated — which is exactly why the design is "thin hull for cruise, thick shelter for storms." A 1 g/cm² bare hull gives f_GCR ≈ 0.98, f_SPE ≈ 0.92.

**Career consequences** (uses NASA 600 mSv anchor):
- D_career ≥ 400 mSv → crew flagged "radiation caution"; recruitment/medical UI warns.
- D_career ≥ 600 mSv → **career limit reached**: crew must rotate home / retire from field duty within the mission; staying raises a per-day **cancer-incidence roll** (REID model: each additional 100 mSv ≈ +0.5% lifetime fatal-cancer probability, rolled at end of career or on Earth return). A crew that develops cancer is permanently lost from the roster (treatment on Earth, narrative).
- This is a *soft* limit by default (player may override for a critical mission, accepting risk) and a *hard* limit on Ironman.

**Acute Radiation Syndrome (ARS)** from D_acute (rolling 24 h, after shielding):

| D_acute (mGy, absorbed) | Effect |
|---|---|
| < 250 | none |
| 250-1,000 | prodromal: nausea, −30% productivity for 1-3 days, morale hit |
| 1,000-2,000 | mild ARS: −60% productivity 1-2 weeks, medbay treatment shortens; immune suppression raises infection event odds |
| 2,000-4,000 | severe ARS: bedridden, requires continuous medbay + MedSupplies, ~30-50% death roll without treatment |
| 4,000-6,000 | LD50 band: ~50% death even with treatment over 1-2 months |
| > 6,000 | near-certain death within days |

**Europa rule** (Act 5 hook): an unshielded crew on Europa's surface accrues ~5,400 mGy/day → lethal in ~hours. Crewed Europa operations require either heavy shielding making EVA impractical or **robotic/teleoperated** surface work (`10`) with crew in a shielded orbital station — a deliberate design statement that some places are for machines, not people.

### 3.7 Gravity health model

Each crew member carries a **conditioning score** `C ∈ [0,100]` (100 = Earth-fit), affecting EVA capability, manual-task productivity, re-entry g-tolerance, and injury odds. Bone and muscle are tracked together via C for v1 (an Open Question proposes splitting them).

**Deconditioning rate** as a function of local effective gravity g_eff (m/s², from surface gravity, spin gravity `06 §3.10`, or 0 in free-fall) and daily exercise hours `h_ex`:
```
dC/dt = −k_decon · max(0, 1 − g_eff/g_full) · (1 − e_ex)              [deconditioning]
        + k_recover · (g_eff/g_full) · max(0, C_ceiling − C)/100        [reconditioning toward Earth-fit]
g_full    = 9.81 m/s²
k_decon   ≈ 0.44 points/day  at g_eff = 0 with no exercise
k_recover ≈ 0.30 points/day  at full g
C_ceiling = 100  (Earth-fit; the maximum C recovers toward at sustained ≥ 1 g)
exercise efficacy e_ex = min(0.85, 0.42 · h_ex)   (2 h/day → e_ex = 0.84, i.e. 84% of loss prevented — matches ISS "near baseline")
```
`k_decon ≈ 0.44 points/day` is tuned so **180 days free-fall with no exercise → ~80-point loss** (C ≈ 100 → ~20), the stated 6-month deconditioning endpoint. (This is a **points/day** rate; it is **not** "1.5 %/day" — a 1.5/day rate would clamp C to 0 in ~67 days and cannot produce C ≈ 20 at 6 months, so that label is dropped.) With 2 h/day exercise the same period loses only `0.44 · (1 − 0.84) · 180 ≈ 13 points` (near baseline, matching ISS). The recovery term gives slow reconditioning when gravity (and exercise) exceed the maintenance demand: at full g with C = 0 it adds +0.30 points/day, tapering to 0 as C → C_ceiling. Equivalently, this is `dC/dt = (C*(g_eff, h_ex) − C)/τ_C` driving C toward a gravity-and-exercise-dependent equilibrium `C*` with a time constant `τ_C`; the two rate constants above are that model's loss and recovery rates.

**Gravity benefit thresholds** (from `06 §3.10`, restated as the health curve):
- g_eff ≥ 3.71 m/s² (Mars-equiv): k_decon → ~0 (deconditioning halts; C recovers slowly).
- g_eff ≥ 1.62 m/s² (Lunar): deconditioning rate halved.
- g_eff < 1.0 m/s²: treated as free-fall for health (cosmetic gravity only).
- Spin-gravity adaptation/comfort penalties (rpm thresholds) are owned by `06 §3.10` and apply as productivity/morale modifiers here.

**Exercise** consumes `h_ex` hours/day of a crew's schedule (default prescription 2.0 h in free-fall, 0.5 h in low-g, 0 at ≥ Mars-g) and requires an **exercise device** (ARED/treadmill/cycle) part installed (§4); without the device, e_ex = 0. Exercise raises activity multiplier A during those hours (more O2/food/water).

**Re-adaptation & consequences:**
- A crew with low C returning to ≥1 g (Earth landing, high-g hab) suffers **orthostatic intolerance**: −50% productivity and elevated fall-injury odds for `t_readapt ≈ (100 − C)/10` days.
- EVA requires C ≥ 40 (suit work is strenuous); below that the crew cannot EVA.
- Re-entry g-load tolerance scales with C: at C < 30, a nominal 4 g entry causes a medical event (§8).

### 3.8 Morale model

Each crew member has **Morale M ∈ [0,100]** (start 70 for a recruit). Updated daily toward a target `M_target` set by living conditions, with a lag:
```
dM/dt = (M_target − M) / τ_M ,  τ_M = 7 days
M_target = 50 + Σ (modifiers, clamped to [0,100])
```

**Modifiers** (additive points to M_target):

| Factor | Modifier | Source / anchor |
|---|---|---|
| Habitable volume ≥ 25 m³/crew | +10 | NASA long-duration min (`06 §3.11`) |
| Volume 10-25 m³/crew | linear 0 → +10 | — |
| Volume < 10 m³/crew | −2 per m³ below 10 | crowding |
| Private sleep quarters | +10 | privacy is a top stressor in analog studies |
| Hot-bunking / shared | −5 | — |
| Fresh greenhouse food available | +12 | psychological value of fresh food (BIOS-3, Antarctic stations) |
| Monotonous ration-only diet > 30 d | −0.2/day (to −15 floor) | menu fatigue |
| Cupola / window / view | +6 | ISS crew reports |
| Live plants in living space | +4 | horticultural-therapy effect |
| Earth one-way light-time L_owl | −min(15, L_owl_minutes · 0.5) | isolation; real-time chat impossible beyond ~minutes |
| Comms blackout (solar conjunction, dish fault) | −10 while active | — |
| Recent crew death (≤ 30 d) | −25 decaying | grief, mortality salience |
| Near-miss incident (≤ 14 d) | −8 decaying | — |
| Microgravity discomfort (g<1.0) | −5 | — |
| Spin comfort penalty (rpm tier) | per `06 §3.10` | motion sickness |
| Overwork (scheduled > 12 h/day) | −0.5/day | — |
| Skill-matched fulfilling work | +5 | — |

**Light-lag (L_owl)**: one-way light time from Earth, computed from current distance (`01`/`03`): Moon ~1.3 s (negligible), Mars 3-22 min, Jupiter 33-53 min, Saturn 68-84 min. Beyond a few light-minutes, real-time conversation with Earth is impossible — a quantified loneliness penalty that grows with distance and is unique to this game's honest scale.

**Morale effects:**
- Productivity multiplier `P_morale = 0.5 + 0.5·(M/100)` (at M=100, full; at M=50, 0.75; at M=0, 0.5).
- Error/incident probability multiplier `φ_err = 2 − M/100` (low morale doubles human-error events feeding `13` reliability and §8 medical/accident rolls).
- **M ≤ 20**: "crisis" — chance/day of a breakdown event (refuses work, or a destructive incident). 
- **M ≤ 0**: the crew **quits** at the next return-to-Earth opportunity, or (if stranded) becomes non-functional. No mutiny/combat (doctrine: no combat); the failure is loss of a worker and a heavy morale contagion to the rest of the crew.

### 3.9 Crew as characters: skills

Each crew member has five **skill tracks**, level 0-5 each (a recruit typically has one primary at 2-3 and a secondary at 1-2):

| Skill | Drives | Consumed by |
|---|---|---|
| **Pilot** | precision of crewed maneuvers, landing, docking margins; reduces piloting-error events | `01`, `06`, `10` |
| **Engineer** | repair speed, manufacturing throughput bonus, ECLSS/reactor fault recovery | `05`, `09`, `13` |
| **Scientist** | research rate, sample analysis, anomaly resolution | `11` |
| **Medic** | medbay treatment efficacy, illness prevention, EVA injury response | this doc §3.12 |
| **Agronomist** | greenhouse yield bonus, crop-failure prevention, algae management | this doc §3.5 |

**Skill effect**: a task tagged with skill s and difficulty d completes at rate `rate = base · (0.5 + 0.25·level_s) · P_morale · P_health`. Level 0 in a required skill → task allowed at heavy penalty (0.5·) or blocked for gated tasks (e.g. only a Medic ≥ 2 can perform surgery; only an Agronomist ≥ 1 unlocks full greenhouse yield).

**Health factor `P_health`** (the multiplier that gates every skill task) is computed explicitly:
```
P_health = clamp(C/100, 0.3, 1.0) · (1 − med_penalty) · (1 − rad_penalty)
```
- **Conditioning factor** `clamp(C/100, 0.3, 1.0)`: a fully deconditioned crew still works at 30% (floor), full at C = 100.
- **`med_penalty`** = the productivity hit of the worst active medical condition (§3.12): minor illness 0.30, injury 0.50, dental abscess 0.30 (rising with time), kidney stone 0.60, DCS 0.50, psychological crisis 0.50; **bedridden** conditions (appendicitis, severe ARS) → 1.00 (cannot work).
- **`rad_penalty`** = the productivity hit of the active ARS band (§3.6): prodromal (250–1,000 mGy) 0.30, mild ARS (1,000–2,000) 0.60, severe ARS (≥ 2,000) 1.00 (bedridden); 0 below 250 mGy.
- **Combining concurrent conditions:** take the **maximum** penalty *within* each of `med_penalty` and `rad_penalty` (the worst active condition in each category dominates — penalties do not stack additively, avoiding implausible > 100% loss), then multiply the two factors as shown. ARS is counted only in `rad_penalty` (not double-counted in `med_penalty`). Example: C = 70, a minor illness (0.30), and prodromal ARS (0.30) → `P_health = 0.70 · 0.70 · 0.70 = 0.343`.

**Skill growth**: skills improve with use (XP per task-hour, slow), and via **training** (an Earth-side or station "training" action costing time and money, `12`). Cap depends on tier: T0-T1 caps at level 3, T2 unlocks level 4 (advanced training programs), T3+ level 5.

**Crew capacity** is the minimum of: life-support throughput available (O2/Water/food production ≥ crew demand), habitable volume (`06 §3.11`: crew_max = floor(V_hab/25)), and sleep slots. Exceeding any → morale collapse and/or consumable shortfall.

### 3.10 Daily schedule & time budget

Each crew member's 24 h is allocated (player sets policy, defaults shown), feeding activity multiplier A and which tasks progress:

| Block | Default hours | A | Notes |
|---|---|---|---|
| Sleep | 8.0 | 0.75 | < 6 h triggers fatigue penalty |
| Personal/hygiene/meals | 2.5 | 1.0 | uses hygiene water |
| Exercise | 2.0 (0 in ≥Mars-g) | 1.6 | conditioning (§3.7) |
| Work (skill tasks) | 10.0 | 1.0-1.6 | the productive block |
| Reserve/contingency | 1.5 | 1.0 | absorbs incidents |

Scheduling > 12 h work/day or < 6 h sleep accrues fatigue: −productivity and +error multiplier, recovering only with rest. EVA days replace a work block (§3.11) at A = 1.6.

### 3.11 EVA & suits, prebreathe

**EVA suit consumables** (per crew, per EVA hour), anchored to the NASA EMU:
- Oxygen ~**0.09 kg/h** (metabolic O2 at a high EVA workload ~0.072 kg/h plus small suit leakage at 29.6 kPa). Anchored to the NASA EMU PLSS, which supplies O2 at ~0.165 lb/hr ≈ **0.075 kg/h** at ~1000 BTU/hr; real EMU O2 use spans ~0.07–0.10 kg/h, so we use ~0.09 kg/h (the prior 0.15 kg/h was ~1.5–2× too high).
- Cooling water (sublimator, sublimated to space) ~**0.40 kg/h**.
- CO2 scrubbing: LiOH or regenerable metox cartridge (consumed per EVA; folded into MedSupplies/ECLSS-spares).
- Battery energy (from `09`).
- Suit endurance: **8 h nominal + 0.5 h reserve**; exceeding reserve → asphyxiation clock (§3.2) for that crew.

A suited crew runs its own mini-LSC (the suit) using the asphyxiation/thermal rules; a suit breach is a §8 emergency with minutes of consciousness.

**Prebreathe (decompression sickness):** moving from cabin to a lower-pressure suit risks the bends as dissolved N2 comes out of solution. Tissue ratio:
```
R = ppN2_cabin / P_suit
```
Prebreathe requirement (purge N2 by breathing high-O2 before EVA):

| R | Prebreathe protocol | t_prebreathe |
|---|---|---|
| ≤ 1.4 | none required | 0 |
| 1.4-1.65 | light | ~30 min |
| 1.65-2.2 | standard (ISS exercise/ISLE-class) | ~2 h |
| > 2.2 | extended / staged depress | 3-4 h |

Worked: sea-level cabin (ppN2 80) to EMU suit (29.6 kPa) → R = 2.70 → 3-4 h prebreathe per EVA (a big time tax — this is why bases use the **exploration atmosphere**). Exploration atm (ppN2 37) → R = 1.25 → **no prebreathe**, enabling frequent EVA. The choice of cabin atmosphere (§3.2) is therefore an EVA-cadence decision. Prebreathe consumes O2 and a work block; a botched/skipped prebreathe (player override or airlock fault) rolls a DCS medical event (§8).

**Airlock loss**: each EVA cycle vents the airlock volume's gas (or pumps most of it back if the airlock has a **scavenge pump** part, recovering ~80%). Mass lost is computed **per species** (recovering kg from partial pressure exactly as §3.2 does — `pp·V/(R·T)` alone yields *moles*, so the molar mass M is required):
```
loss_X = (1 − 0.8·has_pump) · ppX · M_X · V_airlock / (R·T)        [kg per cycle]
total airlock loss = Σ_X loss_X    over X ∈ {N2, O2, CO2, H2O, …}
```
with ppX in kPa, M_X in g/mol, V_airlock in m³, T in K, R = 8.314 J/mol·K (this kPa·(g/mol) combination yields kg directly — see the §3.2 worked sanity check). Worked: a 4 m³ airlock at exploration atm (ppN2 37, ppO2 19.2 kPa), no pump, 294 K → loss_N2 = 37·28·4/(8.314·294) ≈ 1.70 kg + loss_O2 = 19.2·32·4/(8.314·294) ≈ 1.01 kg ≈ **2.7 kg/cycle**; with the scavenge pump (×0.2) ≈ 0.54 kg/cycle. This is the steady N2/O2 makeup driver for an EVA-heavy program.

### 3.12 Medical events & the medbay

**Medbay** is a habitat subsystem (part in §4) that, staffed by a Medic, treats conditions and lowers event probability. It consumes **MedSupplies** (kg) per treatment. Telemedicine consult with Earth is available but delayed by L_owl (§3.8) — beyond a few light-minutes, the crew is on its own and Medic skill matters more.

**Event model**: each day, per crew, roll a base medical-event probability `p_med ≈ 0.0008/day` (≈ one event per ~3.4 crew-years), multiplied by modifiers: `φ_err` (morale, §3.8), radiation state, deconditioning (low C → injury), EVA exposure, age, and crowding/hygiene. A medbay + Medic lowers p_med (preventive care) by up to 40%.

**Condition table** (illustrative; `12` owns the event UI):

| Condition | Trigger / odds modifier | Untreated outcome | Treatment |
|---|---|---|---|
| Minor illness (cold, GI) | crowding, low morale | −30% productivity 3-7 d | MedSupplies + rest |
| Injury (sprain, laceration) | low C, EVA, accidents | −50% productivity, infection risk | medbay, Medic ≥ 1 |
| Dental abscess | random, time | escalating pain, sepsis risk | Medic ≥ 2 |
| Appendicitis | random (~1/crew-decade) | **fatal in days** without surgery | surgery: medbay + Medic ≥ 3 + MedSupplies; else evacuate |
| DCS (the bends) | skipped/failed prebreathe | pain, neuro damage, death | recompression (cabin repress) + medbay |
| ARS | radiation (§3.6) | per ARS table | medbay + MedSupplies, supportive |
| Kidney stone | dehydration, microgravity Ca loss | severe pain, blockage | hydration + Medic |
| Psychological crisis | M ≤ 20 (§3.8) | breakdown, incident | morale recovery, Medic, rotate home |
| SANS (ocular) | long microgravity | vision degradation, permanent | spin-g/return; partial only |

Untreated conditions escalate over days; an unstaffed or unsupplied medbay cannot treat surgical conditions → **medical death** path (§8). Evacuation to Earth/base is the fallback but costs a transfer window (`01`).

### 3.13 The player character & permadeath

**Design decision (do not relitigate):** the player is **the program, not a single body.** You begin in 2049 as a lone engineer-founder operating a *robotic* program from a ground control room on Earth — never physically at risk in Acts 1-2. The save game = the program's continuity (treasury, tech, assets, roster).

- The **founder** may optionally be instantiated as a *crew member avatar* once crewed flight begins (Act 1 late / Act 2), with their own skills, health, dose, and morale — and is then subject to **all** the death rules above.
- **Default (Career) mode — program continuity:** if the founder-avatar dies, it is a major setback — large one-time morale hit to all crew, loss of that avatar's skills, a "succession" event, and a reputation/economic penalty (`12`) — but the **program continues** under a successor director. This avoids a punishing full game-over from a single airlock mishap while preserving real stakes (you can lose your best operator forever).
- **Non-founder crew** are always permadeath: when they die they are gone, with morale contagion (§3.8) to survivors and a recruitment/economic cost to replace.
- **Ironman / Hardcore mode (optional toggle, `12`):** founder-avatar death = game over; single save slot. For players who want the full weight of mortality.
- **Total-loss failure** (Career mode): the program ends only if the treasury is bankrupt AND no income source remains AND all crew are dead/stranded — an economic/logistical death spiral, not a single accident. This aligns the antagonist with the doctrine: physics, distance, entropy, and budgets.

The biology is identical for founder and crew — there is no protagonist plot armor at the physics layer; the only difference is the meta-rule about whether their death ends the campaign.

## 4. Content Catalog

Masses in t, power in kW, all anchored. ECLSS hardware performance (throughput, power, spares) is canonical here; the *part* mass/size/cost also appears in `06`/`07` builder catalogs and must match.

### 4.1 ECLSS units (life-support hardware)

| ID | Name | Tier | Mass (t) | Power (kWe) | Capacity | Closure provided | Spares (kg/yr) | Anchor |
|---|---|---|---|---|---|---|---|---|
| LS-OPEN | Stored-consumables rack | T0 | 0.3 | 0.3 | regulates 4 crew from tanks; LiOH CO2 canisters | η=0 (open) | LiOH 0.55 kg/crew/day | Apollo/Shuttle LiOH |
| LS-CDRA | CO2 removal (CDRA) | T1 | 0.7 | 1.0 | 6 crew | η_CO2rm 1.0 | 8 | ISS CDRA |
| LS-OGA | O2 generation (electrolysis) | T1 | 0.7 | 3.6 | 6 crew (needs Water) | makes O2 from Water; 1.125 kg H2O/kg O2 | 10 | ISS OGA |
| LS-SAB | Sabatier CO2 reducer | T2 | 0.4 | 0.5 | 6 crew | η_O2 → 0.42; recovers 0.818 kg H2O/kg CO2 | 6 | ISS Sabatier |
| LS-BOSCH | Bosch CO2 reducer | T2 | 0.6 | 1.2 | 6 crew | η_O2 → 0.50; deposits Carbon | 12 (soot) | NASA Bosch studies |
| LS-WRS | Water recovery (UPA+WPA) | T1 | 1.5 | 1.3 | 6 crew | η_H2O 0.90 | 15 | ISS WRS |
| LS-BPA | Brine processor add-on | T2 | 0.3 | 0.4 | 6 crew | η_H2O → 0.98 | 4 | ISS BPA |
| LS-CHX | Condensing heat exchanger | T0 | 0.2 | 0.4 | 6 crew | humidity → grey water | 3 | ISS CHX |
| LS-ALGAE | Algae photobioreactor | T3 | 2.0 | 19 (light) | O2 balance 4 crew (32 m² illuminated) | η_O2 → 0.95 at 8 m²/crew | 5 | BIOS-3 Chlorella; MELiSSA C4a |
| LS-GREEN | Greenhouse rack (per 40 m²) | T3 | (module, `06/07`) | ~11 (light) | full diet 1 crew | η_food → 0.95, η_O2 0.98 | Ammonia + 8 MedSupplies | BIOS-3 / CELSS |
| LS-N2 | Buffer-gas regulator | T0 | 0.1 | 0.1 | meters Nitrogen makeup | — | — | standard |

**LS-ALGAE power note:** O2-balancing 4 crew requires 4 × 8 m² = **32 m²** of illuminated *Chlorella*; at the §4.2 Chlorella light load of **0.60 kW/m²** that is `32 · 0.60 ≈ 19 kW` of lighting (hence the 19 kW figure, corrected from a prior 6.0 kW that only supported ~10 m² ≈ 1.25 crew). The rule `power = illuminated_area × light_density` is reproducible for any rating; a 1-crew unit would be ~8 m² ≈ 5 kW. This load propagates to `09-power-thermal.md`.

### 4.2 Crops (CEA catalog)

Design figures, simplified, anchored to BIOS-3 and NASA CELSS. yield = edible kcal per m² of bed per day at full light; light = average grow-light power; water = transpiration recovered by CHX; role notes calories vs nutrition/morale.

| Crop | Tier | Cycle (days) | kcal/m²/day | Light (kW/m²) | Water (L/m²/day) | Role |
|---|---|---|---|---|---|---|
| Potato | T3 | 95 | 250 | 0.28 | 3.5 | top staple calories/area |
| Wheat (dwarf) | T3 | 70 | 200 | 0.30 | 3.0 | staple grain, bread (BIOS-3) |
| Sweet potato | T3 | 120 | 230 | 0.30 | 3.5 | staple, vitamin A |
| Rice | T3 | 85 | 160 | 0.32 | 5.0 | staple, high water |
| Soybean | T3 | 90 | 120 | 0.30 | 3.2 | protein + oil |
| Peanut | T3 | 110 | 130 | 0.30 | 3.0 | protein + fat |
| Lettuce | T2 | 30 | 25 | 0.18 | 2.0 | morale, vitamins, fast |
| Tomato | T2 | 80 | 40 | 0.25 | 4.0 | morale, vitamin C |
| Kale/Chard | T2 | 40 | 30 | 0.20 | 2.5 | vitamins, hardy |
| Strawberry | T3 | 90 | 35 | 0.22 | 3.0 | morale (fresh fruit) |
| Chlorella (algae) | T3 | continuous | ~60 (protein) | 0.60/m² illum | n/a (in medium) | O2 balance + protein paste |

A full balanced diet for 1 crew ≈ 40 m² mixed beds (≈ 22 m² staples + 10 m² protein + 8 m² veg/fruit), ≈ 11 kW lighting, ≈ 130 L/day transpiration (≈98% recovered), ≈ **0.02–0.03 kg/day Ammonia-N gross uptake** (in a closed loop most N is recycled; *imported* makeup is only the ~2% leakage, ~0.001 kg/day/crew — see §3.5). Note this layout's `Σ(Area·yield)` ≈ **6,300 kcal/day ≈ 2.5×** the 2,500 kcal requirement, a deliberate crop-failure/variety margin (surplus banked to the fresh-food store then dried to FoodRations, §3.5). Staple-only **calorie** closure needs only **~16.7 m²/crew**; the survival ration ≈ 13–20 m²/crew (BIOS-3 level, ~78% diet).

### 4.3 Food & rations (stored)

| ID | Name | Tier | Mass/crew/day | Water draw | Shelf life | Notes |
|---|---|---|---|---|---|---|
| FD-DEHY | Dehydrated rations | T0 | 0.62 kg dry | 1.2 kg/day from loop | ~5 yr | lightest to ship |
| FD-PKG | Packaged shelf-stable | T0 | 1.83 kg | 0 | ~1.5 yr | no prep; emergency reserve |
| FD-FRESH | Greenhouse fresh food | T3 | grown | 0 | days | full nutrition + morale +12 |
| FD-EMRG | Emergency bar cache | T0 | 0.5 kg (2,000 kcal) | 0 | ~7 yr | survival-only, morale −10 if sustained |

FoodRations (canonical resource) is shipped/produced as dry-equivalent mass; `05` owns production rates, `12` owns price.

### 4.4 Suits & EVA

| ID | Name | Tier | Mass (t) | O2 use | Cooling water | Endurance | Anchor |
|---|---|---|---|---|---|---|---|
| SU-IVA | Launch/entry pressure suit | T0 | 0.02 | n/a (cabin) | n/a | — | counted in `06` crew mass (80+20 kg) |
| SU-EMU | EVA suit (EMU-class) | T0 | 0.13 | 0.09 kg/h | 0.40 kg/h | 8 h + 0.5 h | NASA EMU/xEMU (PLSS ~0.075 kg/h at 1000 BTU/hr) |
| SU-MCP | Mech. counter-pressure suit | T3 | 0.07 | 0.08 kg/h | 0.30 kg/h | 8 h | MIT BioSuit studies (lower leakage) |
| SU-HARD | Hard-shell exploration suit | T2 | 0.20 | 0.09 kg/h | 0.40 kg/h | 10 h | NASA AX-5/Mark III |

MCP/hard suits lower prebreathe (higher operating pressure) and reduce DCS odds; `10-vehicles.md` owns rover suit-ports (suitport entry avoids airlock gas loss entirely).

### 4.5 Crew-support & medical hardware

| ID | Name | Tier | Mass (t) | Power | Function | Anchor |
|---|---|---|---|---|---|---|
| CS-EXER | Exercise device (ARED+treadmill+cycle) | T0 | 0.5 | 0.3 kW | enables e_ex (§3.7) | ISS ARED/T2/CEVIS |
| CS-MEDBAY | Medbay module | T1 | 1.2 | 0.5 kW | treats conditions; needs Medic + MedSupplies | ISS HMS / DRA medical |
| CS-GALLEY | Galley & food system | T0 | 0.3 | 1.0 kW | meal prep, rehydration, morale +2 | ISS galley |
| CS-QTRS | Private crew quarters (per crew) | T0 | 0.2 | 0.1 kW | privacy +10 morale | ISS crew quarters |
| CS-HYG | Hygiene/waste compartment | T0 | 0.4 | 0.5 kW | toilet (UWMS), hygiene water | ISS UWMS |

### 4.6 MedSupplies (new canonical resource)

**MedSupplies** — a consumable representing pharmaceuticals, medical disposables, ECLSS filters/cartridges (LiOH, metox, water filters), and agricultural micronutrients (pooled for v1). Manufactured per `05-industry-logistics.md` from `0.5 Polymers + 0.3 Electronics + 0.2 Biomass` per kg (placeholder recipe; `05` owns final), or imported from Earth. Consumed by: medbay treatments (0.2-5 kg/event), ECLSS spares (§4.1 columns), and greenhouse micronutrients (§3.5). A program that cannot make or import MedSupplies eventually loses both its life support (no filters) and its crew (no medicine) — a slow squeeze that rewards establishing `05` production off-Earth.

### 4.7 Crew archetypes (recruitment pool)

Generated candidates; `12` owns the recruitment market, salary, and signing cost. Illustrative archetypes (primary skill level / secondary):

| Archetype | Pilot | Engineer | Scientist | Medic | Agronomist | Typical cost |
|---|---|---|---|---|---|---|
| Test Pilot | 3 | 1 | 0 | 1 | 0 | high |
| Flight Engineer | 1 | 3 | 1 | 0 | 0 | mid |
| Mission Scientist | 0 | 1 | 3 | 1 | 1 | mid |
| Flight Surgeon | 0 | 0 | 1 | 3 | 0 | high |
| Space Agronomist | 0 | 1 | 1 | 0 | 3 | mid |
| Generalist (early hire) | 1 | 2 | 1 | 1 | 1 | low |

Each candidate also rolls hidden traits affecting morale/health: e.g. *Resilient* (slower morale decay), *Veteran* (starts with some career dose used, higher skills), *Claustrophobic* (volume penalties hit harder), *Iron Gut* (illness-resistant). Traits surface through play, not at hire (a recruitment gamble).

## 5. Player Interaction & UI

**The Life-Support panel** (per crewed vessel/base) is the primary screen, a *visible spreadsheet* in the project style:

1. **Atmosphere gauges**: dial readouts for ppO2, ppCO2, P_total, humidity, temperature, with the safe-band colors of §3.2. Trend arrows show whether each is rising/falling and time-to-limit at current rate ("ppCO2 → 1.0 kPa in 6 h").
2. **Loop diagram (Sankey)**: a live flow diagram of the ECLSS — boxes for crew, CDRA, OGA, Sabatier, WRS, greenhouse; arrows labeled with kg/day; closure fractions on each loop; vents (CH4, leaks, airlock) shown leaving the system in red. This makes "where is my oxygen going" legible.
3. **Consumable burn-down**: stacked timeline of Oxygen, Water, Food, MedSupplies, Nitrogen stores vs net daily draw, with a bold **"Days of life support remaining"** number (the headline survival stat) computed as `min over resources of (store / net_daily_draw)`.
4. **Crew roster cards**: per crew — portrait, skills, Morale, Conditioning C, Career dose D_career (with the 600 mSv bar), current activity, health/medical status, and assigned task. Hover shows the full modifier breakdown (every morale/health number traces to §3).
5. **Schedule editor**: drag work/sleep/exercise/EVA blocks per crew (§3.10); the panel previews resulting A, fatigue, and conditioning trajectory.
6. **EVA planner**: select crew + suit, shows prebreathe time (from cabin atmosphere), consumables needed, airlock gas loss, and a go/no-go (C ≥ 40, suit charged, prebreathe complete).
7. **Greenhouse manager**: allocate Area_grow among crops, preview kcal/day, power, water, and time-to-first-harvest; warns of monoculture/blight risk and lighting-power shortfalls.

**Alerts & automation**: caution/critical band crossings raise events (`12` event bus). The player sets **policies** (target ppO2, ppCO2 setpoint, exercise prescription, ration type, when to trigger storm-shelter) rather than micromanaging hourly; the sim runs those policies under time warp and pauses on emergencies (configurable). Under comms delay, a base runs autonomously on its policies — reinforcing the light-lag theme.

**Readout honesty**: every displayed number is the same number the sim integrates — no hidden "fudge." Hovering any value shows its formula and inputs (the §3 equation), so the UI is also the documentation.

## 6. Progression Hooks (tiers & acts)

| Tier | Capability unlocked | Anchor | Act |
|---|---|---|---|
| **T0** | Open-loop life support (stored O2/Water/Food, LiOH CO2, FD-DEHY/PKG), IVA + EVA suits, exercise device, basic medbay, sea-level/exploration atmospheres | Apollo/ISS-era stored consumables | Act 1 (Earth+LEO): days-to-weeks crewed missions, consumables dominate mass |
| **T1** | CDRA, OGA (water-fed O2), WRS (~90% water), private quarters, scavenge airlock, telemedicine | ISS ECLSS | Act 1-2: weeks-to-months stations; water recycling makes LEO stations sustainable |
| **T2** | Sabatier/Bosch (40-50% O2 closure), BPA (98% water), hard suits, lunar/Mars Water → OGA O2, fission power for ECLSS, storm shelters | ISS+ / Fission Surface Power | Act 2-3 (Moon, Mars): months-long surface bases; ISRU Water closes O2 locally |
| **T3** | Bioregenerative loops: greenhouses (full-diet CEA), algae bioreactors, ~95-98% closure, agronomist skill cap 5, MCP suits | BIOS-3, MELiSSA, CELSS | Act 3-4 (Mars, belt, Venus): permanent self-feeding settlements; food independence |
| **T4** | [SPECULATIVE] advanced closed ecologies for interstellar-precursor crews; multi-generation life support; not required for v1 win | speculative closed-loop | Endgame: self-sufficient off-Earth civilization |

**Cross-act survival curve**: Act 1 you fight the clock with stored consumables; Act 2 you close the *water* loop (the biggest mass) and feed O2 from ISRU Water; Act 3 you close *food* with greenhouses (the last and hardest loop, gated on power); Act 4-5 you operate where humans barely can (Venus aerostat habitable zone via `07`; Jupiter system where Europa is robots-only). The greenhouse's huge power appetite (~11 kW/crew) explicitly couples this ladder to the nuclear-power ladder in `09`.

## 7. Cross-System Interfaces

**Consumes (provided by siblings):**
- `06-ships-stations.md`: pressurized volume `V_press`, net habitable volume, crew capacity formula, hull leak area, spin-gravity g_eff and rpm comfort tier, storm-shelter module mass, Whipple penetration events (hole area → leak), crew mass convention (80 kg + 20 kg IVA suit).
- `07-bases-habitats.md`: surface-base pressurized volume, regolith/water shielding areal density σ, greenhouse module siting and grow area, base atmosphere selection.
- `04-resources-isru.md`: Oxygen, Water, CO2, Nitrogen, Ammonia (fertilizer), Hydrogen, Methane production and storage; Biomass; contaminant warnings on PSR-derived water (must be cleaned before potable).
- `05-industry-logistics.md`: FoodRations and MedSupplies manufacturing rates, ECLSS spares production, logistics containers for consumable resupply.
- `09-power-thermal.md`: electrical power for ECLSS units and grow-lights (~11 kW/crew greenhouse), thermal rejection of CHX latent heat and ECLSS waste heat, cabin temperature control (crew thermal survival band 18-27°C comfortable).
- `03-solar-system.md`: radiation environment Ḋ_env per region (LEO/cruise/Mars/Jupiter/Europa), SPE event timing and magnitude, atmosphere data for surface bases.
- `01-orbital-mechanics.md`: transfer windows and durations (set consumable demand), Earth one-way light time L_owl (morale), re-entry g-loads.
- `11-research-tech.md`: tier unlocks for ECLSS/greenhouse/suit tech; scientist research output mapping.
- `12-gameplay-economy-ui.md`: recruitment market, salaries, event presentation, contracts paying for crew safety, mode toggles (Career/Ironman).
- `10-vehicles.md`: rover cabins (mobile LSC), suitports, teleoperation for radiation-lethal sites (Europa).

**Provides (consumed by siblings):**
- To `04`/`05`: crew/greenhouse demand signals for Oxygen, Water, Food, Nitrogen, Ammonia, MedSupplies (drives ISRU/production planning); surplus CO2 from crew (minor) and grey-water streams.
- To `06`/`07`: crew capacity constraints (life-support throughput as a cap independent of volume), storm-shelter requirement beyond LEO, atmosphere choice (sets structural pressure load and fire policy).
- To `09`: ECLSS and grow-light electrical load profiles and CHX heat loads.
- To `12`: crew morale/health state for narrative events, death/casualty events, the "days of life support remaining" headline stat, founder permadeath/succession events.
- To `13`: per-crew entity state, error-probability multipliers feeding the reliability/fault model, integration cadence.
- To `10`: crew conditioning C and EVA-readiness gating surface operations.

## 8. Failure Modes & Edge Cases

| Mode | Trigger | Model / consequence | Mitigation |
|---|---|---|---|
| **Asphyxiation (hypoxia)** | ppO2 < 16 kPa | incapacitation timer (§3.2); death at ~1.5× | O2 reserve, OGA, alarms, suits |
| **Hypercapnia** | ppCO2 > 3 kPa (CDRA fault, overcrowding) | impairment → unconsciousness | redundant CO2 removal, LiOH backup |
| **Rapid depressurization** | hull breach / Whipple (`06`), seal failure | choked-flow leak (§3.2); 10 cm² breach = minutes; sub-40 kPa hypoxia even at 100% O2 | compartment isolation, patch kit, don suits, retreat to sealed module |
| **Slow leak** | seal wear, micro-puncture | gradual P drop; N2/O2 makeup drain | leak-check policy, makeup gas, find-and-seal task (Engineer) |
| **Water recovery failure** | UPA/WPA fault | η_H2O → 0; potable store depletes | repair (Engineer), water reserve, ration hygiene |
| **O2 generation failure** | OGA fault, power loss | air O2 depletes at crew rate; ~days of air buffer | O2 tank reserve, fix power/OGA |
| **Food shortfall** | ration depletion, crop blight, greenhouse lag | starvation deficit (§3.5); −productivity → death at reserve=0 | emergency cache, staggered planting, ration cut |
| **Crop blight / algae crash** | monoculture, contamination, light/power loss | η_food drops, standing crop lost; recovery = a full cycle | crop diversity, Agronomist, sterile procedures, ration buffer |
| **Power loss to ECLSS** | reactor/array fault (`09`) | cascade: no CDRA/OGA/CHX/lights; humidity + CO2 climb, food cold | battery buffer, load-shed policy (life support priority), backup power |
| **Thermal control loss** | radiator/loop fault (`09`) | cabin drifts out of 18-27°C; <0°C or >40°C → medical/death | redundant loops, retreat, repair |
| **Radiation: SPE** | solar flare (`03`) | acute dose spike; ARS if unsheltered (§3.6) | storm shelter (minutes warning); time-warp pause + alert |
| **Radiation: chronic** | long deep-space/belt exposure | D_career → 600 mSv; cancer roll; forced rotation | shielding, mission-duration limits, crew rotation |
| **Europa/Jupiter lethal field** | crew on/near Europa surface | ~5.4 Gy/day → death in hours | robotic/teleop ops only; shielded orbit |
| **Deconditioning** | long microgravity, no exercise | C falls; EVA blocked < 40; re-entry injury | exercise device, spin-g habitat, Mars/Moon surface g |
| **DCS (bends)** | skipped/failed prebreathe | medical event, possible death | correct prebreathe, exploration atmosphere, recompression |
| **Suit failure on EVA** | breach, consumable exhaustion | minutes of consciousness; rescue window | buddy EVA, suit reserve, nearby airlock/rover |
| **Medical: surgical** | appendicitis etc. | fatal in days without surgery | medbay + Medic ≥ 3 + MedSupplies, or evacuate |
| **MedSupplies exhaustion** | no production/import | no treatment, no ECLSS filters | establish `05` production off-Earth, stockpile |
| **Morale collapse** | crowding, isolation, deaths (§3.8) | productivity floor, breakdown, crew quits | volume, privacy, fresh food, views, rotation, lighter schedule |
| **Founder death** | any death rule applied to avatar | Career: succession + morale/economic hit; Ironman: game over | keep founder out of high-risk ops; shielding |
| **Stranding** | no return dv / window (`01`) | crew survives only as long as consumables/loops hold | closed loops, rescue mission, pre-positioned supplies |

**Edge cases & rules:**
- **Sleeping crew** still consume O2/Water/CO2 at A = 0.75 — life support never "pauses" under time warp.
- **Zero crew (robotic)** vessels run no LSC; this is the Act-1 default and the safest operating mode (doctrine: automation first).
- **Overcrowding** (crew > capacity) is allowed temporarily (rescue, evacuation) with stacking CO2/humidity/volume penalties — survivable for a short transfer, lethal long-term.
- **Children/birth** are out of scope for v1 (Open Question Q6).
- **Corpses**: a deceased crew's mass remains (recovery/burial is a narrative/morale event, `12`); no resource recovery (doctrine: no grim cannibalism mechanics).
- **Cold-soak food/water**: loss of thermal control can freeze water lines (burst → leak) and spoil fresh food; stored dehydrated food is freeze-tolerant.

## 9. Open Questions

- **Q1 — Bone/muscle split.** v1 folds bone and muscle into one conditioning score C. Should they be tracked separately (bone recovers far slower than muscle, with permanent fracture-risk consequences), and should SANS get its own permanent-vision track? Adds realism, adds UI.
- **Q2 — Per-crew metabolic variation.** Should mass/sex/age modify the 0.84 kg O2 / 2,500 kcal baselines per individual (BVAD supports this), or keep one baseline for simplicity? Variation makes crew selection meaningful but complicates the loop math.
- **Q3 — MedSupplies granularity.** v1 pools pharmaceuticals, ECLSS filters, and agri-micronutrients into one resource. Is that too coarse — should ECLSS spares (`05` reliability) be separated from medicine? Risk of resource sprawl vs fidelity.
- **Q4 — Psychology depth.** How deep should the morale/relationship sim go (inter-crew compatibility, leadership, factions)? Doctrine forbids combat/mutiny-as-violence; how is interpersonal conflict expressed without it?
- **Q5 — Radiation model fidelity.** Is the f_GCR/f_SPE exponential-with-floor sufficient, or do we need separate dose-equivalent quality factors for protons vs heavy ions, and depth-dose buildup (secondaries can *increase* dose at intermediate shielding)? Current model intentionally ignores the secondary-particle hump.
- **Q6 — Generational/closed-civilization scope.** The endgame "self-sufficient off-Earth civilization" implies birth, growth, and multi-decade closed ecology. Is reproduction modeled at all in v1, or is "self-sufficient" defined purely as resource/industrial closure with recruited (not born) crew?
- **Q7 — Greenhouse power realism.** ~11 kW/crew of grow light is enormous; should we model **sunlight-fed greenhouses** (transparent/concentrator designs) on bodies with usable insolation to cut electrical load, coordinating with `07`/`09`? This dramatically changes the Mars vs outer-system food economics.
- **Q8 — Suit/airlock fidelity.** Is the simplified prebreathe tissue-ratio table adequate, or do we need staged-decompression timelines and exercise-prebreathe protocols (ISLE) as explicit minigames? And should suitports (`10`) fully replace airlock gas-loss accounting?
- **Q9 — Closure never reaching 100%.** We cap bioregen at ~98%. Over a multi-year settlement even 2% leakage compounds. Does the game require a permanent trickle import (realistic) or a T4 "fully closed ecology" unlock — and would full closure violate the entropy-as-antagonist doctrine?
