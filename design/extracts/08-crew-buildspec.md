# 08 — Life Support & Crew — BUILD SPEC

Engineer-facing extract of `design/08-life-support-crew.md`, reconciled with `design/DECISIONS.md`
(DECISIONS wins all conflicts). APHELION, Python 3.12 + pygame-ce, hard-realism 2D space sim.
All masses kg, power kW(e), pressure kPa, dose mSv (effective) / mGy (absorbed), area m², time days unless noted.
Integration cadence: **per sim-hour** (scaled by time warp), LSC is a closed mass ledger with documented vents.

New canonical resource introduced here: **MedSupplies** (only new resource this doc adds; pooled per DECISIONS B13).

---

## 1. METABOLIC CANON (BVAD mass balance)

### 1.1 Per-crew daily mass balance (NASA BVAD; activity multiplier A, default 1.0)

| Flow | Symbol | Baseline kg/day | Scales w/ A? | Direction |
|---|---|---|---|---|
| Oxygen consumed | O2_in | 0.84 · A | yes | atmosphere → crew |
| CO2 produced | CO2_out | 1.00 · A | yes | crew → atmosphere |
| Water drunk + prep | H2O_in | 2.5 (see ration note) | no | store → crew |
| Hygiene water | H2O_hyg | 1.0 | no | store → grey water |
| Metabolic water made | H2O_met | 0.35 · A | yes | internal bookkeeping ONLY |
| Urine | U_out | 1.6 | no | crew → urine store |
| Water vapor (resp+persp) | V_out | 2.3 · A | yes | crew → atmosphere (humidity) |
| Dry food eaten | F_in | 0.62 | no | store → crew |
| Solid waste (wet) | W_out | 0.12 | no | crew → waste store |

Total water demand = 2.5 + 1.0 = **3.5 kg/day** (2.0 drink + 0.5 prep + 1.0 hygiene).
**CRITICAL:** `H2O_met` is bookkeeping only — it exits via U_out + V_out already. Do NOT add it to the
`dm_H2O(vap)` cabin-humidity equation (double-counts V_out). It exists solely to close the food→CO2+H2O ledger.

**Activity multiplier A** (time-weighted daily avg from task schedule, §4.7):
sleep 0.75 · nominal work 1.0 · heavy labor / EVA 1.6.
O2, CO2, H2O_met, V_out scale with A; food and drink water are constant per day (appetite lags).

**Mass-conservation check (A=1):** in = 0.84 + 3.5 + 0.62 = 4.96; out = 1.00 + 1.6 + 2.3 + 0.12 = 5.02;
closes within 0.06 kg/day of metabolic-water bookkeeping (absorbed into "Trace" scalar).

### 1.2 Ration-dependent prep water (the H2O_in variable component)

The 0.5 kg/day food-prep part of `H2O_in` depends on ration type (§3). 2.0 drink is fixed; only prep varies:

| Ration | Prep water | H2O_in total | Notes |
|---|---|---|---|
| Packaged / greenhouse-fresh | 0.0 | 2.0 | drink only |
| Default (baseline) | 0.5 | 2.5 | — |
| Dehydrated (FD-DEHY) | 1.2 | 3.2 | net +0.7/day vs baseline; nearly all recovered at η_H2O |

### 1.3 Output streams (for waste routing)
urine ~1.6 kg/day · resp+persp vapor ~2.3 kg/day · feces (~75% water) ~0.09 · dry solid waste ~0.03.

### 1.4 Cabin atmosphere physics

Ideal-gas partial pressure per species X:
```
ppX = (m_X / M_X) · R · T / V_press      [kPa; m kg→g, R=8.314 J/mol·K, T K, V m³, /1000 → kPa]
```
Molar masses M (g/mol): **O2=32, CO2=44, N2=28, H2O=18.** Total P = ppO2 + ppCO2 + ppN2 + ppH2O + ppTrace.
Sanity: V=106 m³, T=294 K, ppO2=21.2 kPa → ~29.4 kg O2 resident; crew-4 burns 3.36 kg/day → ~9 days air buffer.

**Per-hour atmosphere ODEs:**
```
dm_O2  = +Gen_O2  − Σcrew(O2_in)  − Leak·(ppO2 /P)
dm_CO2 = +Σcrew(CO2_out) − Scrub_CO2 − Uptake_plant − Leak·(ppCO2/P)
dm_N2  = +Makeup_N2 − Leak·(ppN2/P)
dm_H2O(vap) = +Σcrew(V_out) − CHX_rate − Leak·(ppH2O/P)
```
**CO2 single-counting rule:** only `Scrub_CO2` (CDRA/amine) and `Uptake_plant` (bioregen) remove CO2 from *air*.
Scrubbed CO2 goes to a separate **CO2 accumulator** store: `dStore_CO2 = +Scrub_CO2 − Reduce_CO2`.
Sabatier/Bosch (`Reduce_CO2`) draws from the accumulator, NOT cabin air. Never subtract Reduce_CO2 from the air ODE.

### 1.5 Cabin atmosphere options (player-selectable per habitat)

| Atmosphere | P (kPa) | O2 frac | ppO2 | ppN2 | Notes |
|---|---|---|---|---|---|
| Sea-level | 101.3 | 21% | 21.3 | 80 | Earthlike, heaviest gas mass, longest prebreathe |
| Exploration | 56.5 | 34% | 19.2 | 37 | NASA EVA atm; short prebreathe; DEFAULT deep-space hab |
| Reduced N2 | 70 | 27% | 18.9 | 51 | compromise |
| Pure-O2 low-P | 34 | ~100% | 34 | 0 | suits/emergency only; W-FIRE; forbidden for nominal crewed ops |

Fire multiplier: `φ_fire = max(1, (O2_frac/0.21)^3 · (P/101)^0.5)`. Pure-O2 environments flagged **W-FIRE**.
NB: 23 kPa is a *flammability* threshold, not O2-toxicity (pulmonary toxicity needs sustained ppO2 > ~50 kPa).

### 1.6 Safe bands (drive alarms / crew autonomy)

| Quantity | Nominal | Caution | Critical |
|---|---|---|---|
| ppO2 | 19-23 kPa | 16-19 (mild hypoxia) / 23-27 (fire watch) | < 16 hypoxia, > 27 / O2-frac>30% fire |
| ppCO2 | < 0.4 kPa | 0.4-1.0 (headache) | > 1.0 impair, > 3.0 acute, > 7 unconscious |
| P total | 50-103 kPa | 40-50 / 103-110 | < 40 (hypoxia regardless of O2%) |
| Humidity ppH2O | 0.8-1.6 kPa (~25-70% RH) | > 1.6 (condensation) | saturation = fog/short risk |

### 1.7 Leak & breach model

Baseline leak: `Leak = k_leak · P · A_hull` (kg/h). `A_hull` summed module hull area (`06`),
`k_leak` per-module tightness constant; tuned so well-built station loses ~0.2-0.3 kg air/day (ISS-class).

**Whipple/hull breach to vacuum — choked (sonic) flow:**
```
ṁ = Cd·A·P0·√(γ/(Rs·T0))·[2/(γ+1)]^((γ+1)/(2(γ−1)))
For air (γ=1.4, Rs=287, T0≈294 K, Cd≈0.62): Leak_hole ≈ C · a_hole · P  [kg/h], C ≈ 0.5 kg/(h·cm²·kPa)
```
- 1 cm² hole @ 101 kPa → **~51 kg/h** (NOT 1.2 kg/h — that legacy value was ~44× too small).
- 106 m³ module holds ~127 kg air → τ = m_air/Leak ≈ **2.5 h** for 1 cm² hole (tens-of-minutes to act).
- 10 cm² breach → **~510 kg/h**, τ ≈ 15 min — drop-everything emergency.
- Pressure decays exponentially: `P(t) = P0·exp(−t/τ)`, τ recomputed as P falls; flow stays choked until P < ~1.9× ambient.

### 1.8 Hypoxia / hypercapnia health clock
When ppO2 < 16 kPa OR ppCO2 > 3 kPa, accrue an incapacitation timer:
```
deficit_ratio_O2  = clamp((ppO2 − 8) / (16 − 8), 0, 1)
deficit_ratio_CO2 = clamp((7 − ppCO2) / (7 − 3), 0, 1)
t_inc  = 30 min · min(deficit_ratio_O2, deficit_ratio_CO2)   (worse insult dominates)
t_death ≈ 1.5 · t_inc   (after incapacitation, if uncorrected)
```
Hypoxia: 30 min @ 16 kPa, ~7.5 min @ 10 kPa, ~0 @ ≤8 kPa. Hypercapnia: 30 min @ 3 kPa → ~0 @ ≥7 kPa.

### 1.9 Humidity / CHX
V_out raises humidity; a **Condensing Heat Exchanger (CHX)** (in every ECLSS unit) condenses vapor to
grey/condensate water at production rate, latent heat → `09`. CHX overrun (overcrowding/fault) → condensation,
electrical-fault risk, mold morale penalty.

---

## 2. ECLSS LADDER (closure stages)

### 2.1 Subsystem closure fractions η ∈ [0,1] — the core balance levers

| Subsystem | Symbol | Open (T0) | ISS-grade (T1-T2) | Bioregen (T3) |
|---|---|---|---|---|
| CO2 removal from air | η_CO2rm | 0 (LiOH consumed) | ~1.0 (CDRA regenerable) | ~1.0 (plant uptake) |
| O2 loop closure | η_O2 | 0 | 0.42 (Sabatier) → 0.50 (Bosch) | 0.95–0.98 (photosynthesis) |
| Water recovery | η_H2O | 0 | 0.90 → 0.98 (brine proc.) | 0.98 |
| Food closure | η_food | 0 | 0 phys-chem; **0.25–0.50** (T2 LS-GARDEN) | 0.80 → 0.95 (T3 LS-GREEN) |

**Food is the only fraction with a meaningful T2 step.** Air/water close physico-chemically; food's partial
bioregen loop (LS-GARDEN salad/veg rack, η_food 0.25–0.50) arrives a tier before full-diet closure (T3, 0.80–0.95).

### 2.2 Net daily resupply per crew (kg/day)
```
O2_resupply   = (1 − η_O2)   · 0.84 · A     (OR regenerate O2 via electrolysis of recovered/ISRU water)
H2O_resupply  = (1 − η_H2O)  · 3.5
Food_resupply = (1 − η_food) · 0.62  (dry)
N2_resupply   = Leak·(ppN2/P) + airlock losses   (buffer gas makeup only)
```

### 2.3 Physico-chemical O2 path (T1-T2 ISS loop) — explicit stoichiometry
1. **CDRA** scrubs CO2 from air (η_CO2rm ≈ 1.0) → CO2 accumulator.
2. **OGA** electrolysis `2 H2O → 2 H2 + O2`: per 1 kg O2 consumes **1.125 kg H2O**, yields **0.125 kg H2**.
3. **Sabatier** `CO2 + 4 H2 → CH4 + 2 H2O`: per 1 kg CO2 reduced needs **0.182 kg H2**, makes **0.364 kg CH4**
   (vented, or to Methane store with Bosch-loop T2 upgrade), recovers **0.818 kg H2O**.
4. Vented CH4 carries away C+H → η_O2 ≈ 0.42. **Bosch** `CO2 + 2 H2 → C + 2 H2O` (deposits solid Carbon)
   pushes η_O2 → 0.50+ at cost of carbon-soot maintenance (higher spares).

**Implementation rule:** sim does NOT simulate each reactor — apply η_O2 / η_H2O to compute net resupply, separately
debit electrical power and MedSupplies/ECLSS-spares per installed unit, and debit Water→electrolysis→O2 when an OGA
is present (so a water-rich base is O2-self-sufficient at η_O2=0.42 — the "missing" O2 comes from electrolyzing
imported/ISRU water). **This is the key Act-2 gameplay: lunar/Mars water → OGA → local breathing O2.**

### 2.4 Bioregenerative path (T3)
Crops/algae photosynthesize `6 CO2 + 6 H2O → C6H12O6 + 6 O2`, simultaneously closing O2, CO2, Water
(transpiration→CHX→potable) and food. Closure → η ≈ 0.98, **never 1.0** (inedible biomass, losses, crop-failure
buffer). Requires greenhouse subsystem, large lighting power, an Agronomist. Remaining 2–5% from stores; a crop
blight drops η_food and forces ration draw.

### 2.5 Water loop detail (three pools: Potable, Grey/condensate, Urine/brine)
```
Potable −2.5 (drink+prep) −1.0 (hygiene)
Grey   +1.0 (hygiene) +2.3 (vapor via CHX) +0.818·(CO2 reduced)
Urine  +1.6
WPA: Grey → Potable at η_WPA = 0.93
UPA: Urine → Grey at η_UPA = 0.85   (brine stored; BPA upgrade recovers brine → overall 0.98)
```
Net potable makeup = 3.5 · (1 − η_H2O). At η_H2O=0.98 → **0.07 kg/day/crew**. UPA/WPA fault drops η_H2O→0
instantly; crew runs on Potable stores while repaired (common Act-2 emergency).

### 2.6 ECLSS hardware catalog (§4.1) — mass/power/closure/spares (CANONICAL here)

| ID | Name | Tier | Mass t | Power kWe | Capacity | Closure | Spares kg/yr | Anchor |
|---|---|---|---|---|---|---|---|---|
| LS-OPEN | Stored-consumables rack | T0 | 0.3 | 0.3 | 4 crew from tanks; LiOH | η=0 open | LiOH 0.55 kg/crew/day | Apollo/Shuttle |
| LS-CDRA | CO2 removal (CDRA) | T1 | 0.7 | 1.0 | 6 crew | η_CO2rm 1.0 | 8 | ISS CDRA |
| LS-OGA | O2 generation (electrolysis) | T1 | 0.7 | 3.6 | 6 crew (needs Water) | O2 from Water; 1.125 kg H2O/kg O2 | 10 | ISS OGA |
| LS-SAB | Sabatier CO2 reducer | T2 | 0.4 | 0.5 | 6 crew | η_O2 → 0.42; +0.818 kg H2O/kg CO2 | 6 | ISS Sabatier |
| LS-BOSCH | Bosch CO2 reducer | T2 | 0.6 | 1.2 | 6 crew | η_O2 → 0.50; deposits Carbon | 12 (soot) | NASA Bosch |
| LS-WRS | Water recovery (UPA+WPA) | T1 | 1.5 | 1.3 | 6 crew | η_H2O 0.90 | 15 | ISS WRS |
| LS-BPA | Brine processor add-on | T2 | 0.3 | 0.4 | 6 crew | η_H2O → 0.98 | 4 | ISS BPA |
| LS-CHX | Condensing heat exchanger | T0 | 0.2 | 0.4 | 6 crew | humidity → grey water | 3 | ISS CHX |
| LS-ALGAE | Algae photobioreactor | T3 | 2.0 | 19 (light) | O2 balance 4 crew (32 m² illum) | η_O2 → 0.95 @ 8 m²/crew | 5 | BIOS-3 Chlorella |
| LS-GARDEN | Salad/veg greenhouse (per ~14 m²) | T2 | module (06/07) | ~4 (light) | partial diet 1 crew (~14 m²) | η_food 0.25–0.50, η_O2 partial | Ammonia + 4 MedSupplies | EDEN ISS; `11` LS-04 |
| LS-GREEN | Greenhouse full-diet (per 40 m²) | T3 | module (06/07) | ~11 (light) | full diet 1 crew | η_food 0.80→0.95, η_O2 0.98 | Ammonia + 8 MedSupplies | BIOS-3/CELSS; `11` LS-07 |
| LS-N2 | Buffer-gas regulator | T0 | 0.1 | 0.1 | meters Nitrogen makeup | — | — | standard |

**LS-ALGAE power:** O2-balancing 4 crew = 4×8 m² = 32 m² illuminated Chlorella × 0.60 kW/m² = **~19 kW**.
Rule `power = illuminated_area × light_density` reproducible for any rating (1-crew unit ≈ 8 m² ≈ 5 kW). Load → `09`.

### 2.7 Worked closure comparison — crew of 4, 180-day transfer

| Loop | O2 kg | Water kg | Food dry kg | Total consumables kg |
|---|---|---|---|---|
| Open (T0) | 605 | 2,520 | 446 | **3,571** (+packaging/tankage) |
| ISS-grade η_O2=0.42, η_H2O=0.93, water-fed OGA | ~70 net (electrolysis) | 176 | 446 | **~692** + ECLSS ~1.5 t |
| Bioregen η=0.98 all, η_food=0.95 | ~12 | ~50 | ~22 | **~84** + greenhouse ~16 t + 12 kW/crew |

The whole motivation curve: open-loop fine for Act-1 LEO week, ruinous for Mars; greenhouse only pays off on
multi-year/permanent settlements (Act 3+). Hardware mass/power owned by `06`/`07`/`09`; consumables owned here.

---

## 3. FOOD & AGRICULTURE

### 3.1 Stored food forms (player chooses per mission)

| ID | Name | Tier | Mass/crew/day | Water draw | Shelf life | Notes |
|---|---|---|---|---|---|---|
| FD-DEHY | Dehydrated rations | T0 | 0.62 kg dry | 1.2 kg/day from loop | ~5 yr | lightest to ship; prep water REPLACES 0.5 baseline → H2O_in=3.2 |
| FD-PKG | Packaged shelf-stable | T0 | 1.83 kg | 0 | ~1.5 yr | no prep; H2O_in=2.0; emergency reserve |
| FD-FRESH | Greenhouse fresh food | T2 | grown | 0 | days | partial diet + morale +12; full nutrition at T3 |
| FD-EMRG | Emergency bar cache | T0 | 0.5 kg (2,000 kcal) | 0 | ~7 yr | survival-only; morale −10 if sustained |

Expired food → spoilage (§5) + morale penalty if eaten. FoodRations (canonical resource) shipped/produced as
dry-equivalent mass (`05` owns production rates, `12` owns price).

### 3.2 Caloric / starvation model
`kcal_req = 2,500 · A_metabolic` kcal/day (range ~2,000–3,000). If intake < req, accrue **starvation deficit**.
Body-energy reserve **~90,000 kcal** depletes/refills; deconditioning + death when it hits zero. Humans survive
~30–45 days zero-intake (faster with cold/labor).

### 3.3 Greenhouse (CEA) model
Greenhouse provides `Area_grow` (m², from `06`/`07`), split among crops. Per m² of crop c's allocation:
```
yield_c (kcal/m²/day) , light_c (kW/m² avg) , water_c (L/m²/day transpired) , cycle_c (days to harvest)
```
Per day a greenhouse:
- produces `Σ_c Area_c · yield_c` kcal → fresh-food store (morale bonus + full nutrition)
- consumes `Σ_c Area_c · light_c` kW electrical (`09`)
- transpires `Σ_c Area_c · water_c` L/day (recovered via CHX at ~0.98)
- fixes CO2 / releases O2 stoichiometric with kcal fixed
- consumes **Ammonia** fertilizer (`04`) at **~0.03 g N per g edible dry biomass** (crop dry matter ~1–5% N)
  + micronutrient trickle (pooled into MedSupplies for v1 as "AgriSupplies").
  In a closed loop most N is recycled from crew urine/waste (MELiSSA nitrifier) → imported makeup only ~2% leakage.

**Crop establishment lag:** a freshly planted bed yields nothing until `cycle_c` days pass. A brand-new greenhouse
cannot feed crew for ~2–3 months — they must carry rations to bridge (deliberate Act-3 logistics trap; staggered
planting smooths it).

### 3.4 Crop catalog (§4.2) — yields at full light

| Crop | Tier | Cycle days | kcal/m²/day | Light kW/m² | Water L/m²/day | Role |
|---|---|---|---|---|---|---|
| Potato | T2 | 95 | 250 | 0.28 | 3.5 | top staple cal/area; T2 LS-GARDEN caloric anchor |
| Wheat (dwarf) | T3 | 70 | 200 | 0.30 | 3.0 | staple grain, bread |
| Sweet potato | T3 | 120 | 230 | 0.30 | 3.5 | staple, vitamin A |
| Rice | T3 | 85 | 160 | 0.32 | 5.0 | staple, high water |
| Soybean | T3 | 90 | 120 | 0.30 | 3.2 | protein + oil |
| Peanut | T3 | 110 | 130 | 0.30 | 3.0 | protein + fat |
| Lettuce | T1 | 30 | 25 | 0.18 | 2.0 | morale, vitamins, fast (`11` LS-02) |
| Tomato | T1 | 80 | 40 | 0.25 | 4.0 | morale, vitamin C |
| Kale/Chard | T1 | 40 | 30 | 0.20 | 2.5 | vitamins, hardy |
| Strawberry | T3 | 90 | 35 | 0.22 | 3.0 | morale (fresh fruit) |
| Chlorella (algae) | T3 | continuous | ~60 (protein) | 0.60/m² illum | n/a (in medium) | O2 balance + protein paste |

**Crop tier staging:** T1 = salad/leaf (lettuce/tomato/kale — morale + trace food). T2 adds **potato** (LS-GARDEN
η_food 0.25–0.50 partial diet, Acts 2–3). T3 unlocks full-diet staples (wheat/sweet potato/rice/soybean/peanut),
fruit (strawberry), algae (η_food 0.80–0.95, `11` LS-07). Grow greens from T1, partial calories T2, food-independent only at T3.

### 3.5 Per-person area benchmarks (BIOS-3 / NASA CELSS anchors)
- O2/CO2 balance only: **~8 m² algae** OR **~10 m² leafy crops** per crew.
- ~78% dry food + full O2 (BIOS-3): **~13 m² staple crops** per crew.
- Full balanced diet: **~40 m²/crew** (~22 m² staples + 10 m² protein + 8 m² veg/fruit), **~10–12 kW grow-light/crew**,
  ~130 L/day transpiration (~98% recovered), **~0.02–0.03 kg/day Ammonia-N gross** (imported makeup ~0.001 kg/day/crew).
- **40 m² is deliberately over-sized:** `Σ(Area_c·yield_c)` ≈ **6,300 kcal/day ≈ 2.5×** the 2,500 req — margin for crop
  failure, variety, staggered-planting gaps, harvest losses. *Pure staple-calorie* closure needs only **~16.7 m²/crew**
  (consistent with BIOS-3's 13 m² = 78%). Survival ration ≈ 13–20 m²/crew.

**Surplus disposition:** fresh output first fills a capped **fresh-food store** (morale +12 source, capped ~14 crew-days);
overflow is dried → **FoodRations** reserve (banked not wasted). Sustained shortfall draws this buffer before §5 food-shortfall path.

### 3.6 Algae photobioreactor
Primarily an **O2/CO2 balancer + protein source**, not staple calories. ~8 m² illuminated Chlorella per crew balances
O2/CO2 (BIOS-3). Closes O2 at high efficiency in less volume than crops; limited palatable calories (protein paste;
monotony morale penalty if relied on).

### 3.7 Crew-support hardware (§4.5)

| ID | Name | Tier | Mass t | Power | Function | Anchor |
|---|---|---|---|---|---|---|
| CS-EXER | Exercise device (ARED+treadmill+cycle) | T0 | 0.5 | 0.3 kW | enables e_ex (§4.4) | ISS ARED/T2/CEVIS |
| CS-MEDBAY | Medbay module | T1 | 1.2 | 0.5 kW | treats conditions; needs Medic + MedSupplies | ISS HMS |
| CS-GALLEY | Galley & food system | T0 | 0.3 | 1.0 kW | meal prep, rehydration, morale +2 | ISS galley |
| CS-QTRS | Private crew quarters (per crew) | T0 | 0.2 | 0.1 kW | privacy +10 morale | ISS crew quarters |
| CS-HYG | Hygiene/waste compartment | T0 | 0.4 | 0.5 kW | toilet (UWMS), hygiene water | ISS UWMS |

### 3.8 MedSupplies (§4.6) — new canonical resource (pooled, DECISIONS B13)
Represents pharmaceuticals, medical disposables, ECLSS filters/cartridges (LiOH/metox/water filters), and agri
micronutrients (pooled for v1). Manufactured per `05` from `0.5 Polymers + 0.3 Electronics + 0.2 Biomass` per kg
(placeholder; `05` owns final), or imported from Earth. Consumed by: medbay treatments (0.2–5 kg/event), ECLSS spares
(§2.6 columns), greenhouse micronutrients. No production/import → slow squeeze loses both life support and crew.

---

## 4. CREW MODEL

### 4.1 Skills — FIVE tracks, level 0-5 each (recruit: one primary 2-3, secondary 1-2)

| Skill | Drives | Consumed by |
|---|---|---|
| **Pilot** | crewed-maneuver precision, landing, docking margins; cuts piloting-error events | `01`,`06`,`10` |
| **Engineer** | repair speed, manufacturing throughput, ECLSS/reactor fault recovery | `05`,`09`,`13` |
| **Scientist** | research rate, sample analysis, anomaly resolution | `11` |
| **Medic** | medbay treatment efficacy, illness prevention, EVA injury response | §4.6 |
| **Agronomist** | greenhouse yield bonus, crop-failure prevention, algae mgmt | §3 |

**Skill effect on a task** (skill s, difficulty d): `rate = base · (0.5 + 0.25·level_s) · P_morale · P_health`.
Level 0 in a required skill → heavy penalty (0.5·) or blocked for gated tasks (surgery needs Medic ≥ 2; full
greenhouse yield needs Agronomist ≥ 1; appendix surgery needs Medic ≥ 3).

**Skill growth:** XP per task-hour (slow) + **training** action (Earth/station, costs time+money, `12`).
**Tier-gated cap:** T0-T1 cap level 3, T2 unlocks level 4, T3+ level 5.

**Health factor `P_health`** (gates every skill task):
```
P_health = clamp(C/100, 0.3, 1.0) · (1 − med_penalty) · (1 − rad_penalty)
```
- Conditioning factor `clamp(C/100, 0.3, 1.0)`: fully deconditioned still 30% floor.
- `med_penalty` = worst active medical condition (max within category, NOT additive): minor illness 0.30, injury 0.50,
  dental abscess 0.30, kidney stone 0.60, DCS 0.50, psych crisis 0.50; bedridden (appendicitis, severe ARS) → 1.00.
- `rad_penalty` = active ARS band: prodromal 0.30, mild 0.60, severe ≥2,000 mGy → 1.00. ARS counted ONLY here.
- Combine: max within each category, then multiply the two factors. Example: C=70, minor illness 0.30, prodromal ARS 0.30
  → P_health = 0.70·0.70·0.70 = **0.343**.

**Crew capacity** = min(life-support throughput ≥ demand, habitable volume `crew_max=floor(V_hab/25)`, sleep slots).

### 4.2 Radiation dose model — TWO distinct accumulators (do not equate)
- **Career effective dose `D_career`** (mSv = absorbed × Q) — chronic stochastic cancer risk; NASA **600 mSv** anchor.
- **Acute absorbed dose `D_acute`** (mGy) over rolling **24-h window** — deterministic ARS risk (Gy-defined).

**Quality factor Q:** effective(mSv) = absorbed(mGy) × Q. Q ≈ **1 for SPE protons**, Q ≈ **3 for GCR heavy-ion mix**
(v1 simplification; real GCR Q ~3–20, see Q5). The `Ḋ_env` table is **effective** (mSv/day) and feeds `D_career`
directly; the **absorbed** rate feeding `D_acute` is `Ḋ_env / Q`. Consequence: SPE (Q≈1) adds ~equally to both;
GCR (Q≈3) adds ~3× more to career (mSv) than acute (mGy) — GCR drives cancer limit, rarely ARS.

**Environmental dose rate `Ḋ_env`** (mSv/day; `03` S-8a/b/c is CANONICAL field; 08 consumes verbatim):

| Region | Ḋ_env mSv/day | Anchor |
|---|---|---|
| Earth surface / under atmosphere | ~0.01 | sea-level background |
| LEO (ISS, 400 km) | 0.5–1.0 (avg ~0.7) | ISS dosimetry |
| Van Allen belts (behind 5 g/cm² hull) | piecewise: peak **150 @ 1.6 R_E** → 10 @ 2.5 → **50 @ 4.5 R_E** → 0 @ 8 R_E; chemical transit ~1–5 mSv/pass; EP spiral Sv-class | S-8c AP8/AE8 |
| Cislunar / interplanetary cruise | 1.8 · f_cycle (f_cycle 0.65–1.35) | MSL/RAD |
| Moon surface | **1.37** | Chang'e-4 LND |
| Mars surface | **0.67** | MSL RAD Curiosity |
| Main belt / Ceres | 1.8 · f_cycle | GCR-dominated |
| Jupiter system (outside Europa) | 10–100+ (D_jup(r)) | magnetosphere |
| **Europa surface** | **~5,400** | 5.4 Gy/day, lethal in hours |
| SPE event (unshielded, 1 AU) | lognormal: median +100, σ_ln=1.2, **capped +2,000**, over 6–48 h (×1/d²) | Aug-1972-class |

Each region's tabulated `Ḋ_env` = its **GCR background** = `Ḋ_GCR`. `Ḋ_SPE` = **0 except during an active SPE**.
Van Allen field is proton/electron (not GCR), already behind 5 g/cm² hull; integrate along trajectory by geocentric
radius r [R_E]; reproduce ~1–5 mSv/chemical-pass (EP spiral lingers weeks → Sv-class — why SEP tugs fly uncrewed).

**Shielding** — areal density σ (g/cm²) summed from hull + dedicated shield + water walls + regolith overburden (`07`):
```
GCR:  f_GCR(σ) = F(σ) + 0.70 · exp(−σ / 30)
      F(σ) = 0.30                              for σ ≤ 1,000 g/cm²   (0.30 floor — secondaries)
      F(σ) = 0.30 · exp(−(σ − 1,000) / 1,000)  for σ > 1,000 g/cm²   (DECISIONS A3 decaying floor, e-fold 1,000)
SPE:  f_SPE(σ) = exp(−σ / 12)                  (~20 g/cm² cuts SPE ~80%)
Ḋ = f_GCR(σ)·Ḋ_GCR + f_SPE(σ)·Ḋ_SPE
```
Worked: storm shelter water walls σ=35 → f_GCR = 0.30+0.70·exp(−1.17) = **0.52** (GCR only halved); f_SPE = exp(−2.92) = **0.054**
(SPE nearly eliminated) → "thin hull for cruise, thick shelter for storms." 1 g/cm² bare hull: f_GCR≈0.98, f_SPE≈0.92.
**Deep-shield (A3):** past σ≈1,000 g/cm² (≈6 m regolith, ≈11 m ice — burial columns only) floor decays e-fold 1,000;
30 m belt rock ≈4,500 g/cm² → f_GCR ≈ 0.009 (Earth-surface class). `03` measured ambients remain *overrides of site
dose*, not outputs of this law. **DECISIONS A3 binding now.**

**Career consequences (600 mSv NASA anchor):**
- D_career ≥ **400 mSv** → "radiation caution" flag; recruitment/medical UI warns.
- D_career ≥ **600 mSv** → career limit; crew must rotate home / retire from field duty. Staying raises per-day
  **cancer-incidence roll** (REID: each +100 mSv ≈ +0.5% lifetime fatal-cancer prob, rolled at career end / Earth return).
  Cancer = permanently lost from roster (narrative).
- **Soft limit by default** (player may override accepting risk); **hard limit on Ironman.**

**ARS from D_acute (rolling 24 h, after shielding):**

| D_acute (mGy absorbed) | Effect |
|---|---|
| < 250 | none |
| 250–1,000 | prodromal: nausea, −30% productivity 1–3 d, morale hit |
| 1,000–2,000 | mild ARS: −60% productivity 1–2 wk; immune suppression raises infection odds |
| 2,000–4,000 | severe ARS: bedridden, continuous medbay + MedSupplies, ~30–50% death roll untreated |
| 4,000–6,000 | LD50 band: ~50% death even treated over 1–2 mo |
| > 6,000 | near-certain death within days |

**Europa rule (Act 5):** unshielded crew ~5,400 mGy/day → lethal in hours. Crewed Europa = robotic/teleop surface
work (`10`) with crew in shielded orbital station (some places are for machines, not people).

### 4.3 Gravity / deconditioning model
Each crew carries **conditioning score `C ∈ [0,100]`** (100 = Earth-fit; bone+muscle folded together v1).
```
dC/dt = −k_decon · max(0, 1 − g_eff/g_full) · (1 − e_ex)          [deconditioning]
        + k_recover · (g_eff/g_full) · max(0, C_ceiling − C)/100    [reconditioning]
g_full=9.81 ; k_decon≈0.44 points/day @ g_eff=0 no exercise ; k_recover≈0.30 points/day @ full g
C_ceiling=100 ; e_ex = min(0.85, 0.42·h_ex)   (2 h/day → e_ex=0.84, "near ISS baseline")
```
Tuning: 180 d free-fall no exercise → ~80-point loss (C: 100→~20). With 2 h/day: `0.44·(1−0.84)·180 ≈ 13 pts`.
(This is **points/day**, NOT %/day.) Equivalent form: `dC/dt = (C*(g_eff,h_ex) − C)/τ_C` toward equilibrium C*.

**Gravity thresholds** (from `06 §3.10`):
- g_eff ≥ 3.71 m/s² (Mars): k_decon → ~0, C recovers slowly.
- g_eff ≥ 1.62 m/s² (Lunar): deconditioning rate halved.
- g_eff < 1.0 m/s²: treated as free-fall (cosmetic gravity only).
- Spin-gravity rpm comfort penalties owned by `06 §3.10` → productivity/morale modifiers.

**Exercise** consumes `h_ex` of schedule (default 2.0 h free-fall, 0.5 h low-g, 0 at ≥Mars-g), requires
**CS-EXER** device (else e_ex=0). Raises A=1.6 during those hours.

**Re-adaptation & consequences:**
- Low-C crew returning to ≥1 g → orthostatic intolerance: −50% productivity + fall-injury odds for
  `t_readapt ≈ (100 − C)/10` days.
- **EVA requires C ≥ 40** (else cannot EVA).
- Re-entry: at C < 30 a nominal 4 g entry causes a medical event.

### 4.4 Morale model — `M ∈ [0,100]` (recruit starts 70)
```
dM/dt = (M_target − M) / τ_M ,  τ_M = 7 days
M_target = 50 + Σ(modifiers, clamped [0,100])
```

| Factor | Modifier | Source |
|---|---|---|
| Habitable volume ≥ 25 m³/crew | +10 | NASA long-duration min |
| Volume 10–25 m³/crew | linear 0 → +10 | — |
| Volume < 10 m³/crew | −2 per m³ below 10 | crowding |
| Private sleep quarters | +10 | privacy |
| Hot-bunking / shared | −5 | — |
| Fresh greenhouse food available | +12 | BIOS-3 / Antarctic |
| Monotonous ration-only diet > 30 d | −0.2/day (to −15 floor) | menu fatigue |
| Cupola / window / view | +6 | ISS crew |
| Live plants in living space | +4 | horticultural therapy |
| Earth one-way light-time L_owl | −min(15, L_owl_minutes · 0.5) | isolation |
| Comms blackout (conjunction/dish fault) | −10 while active | — |
| Recent crew death (≤ 30 d) | −25 decaying | grief |
| Near-miss incident (≤ 14 d) | −8 decaying | — |
| Microgravity discomfort (g < 1.0) | −5 | — |
| Spin comfort penalty (rpm tier) | per `06 §3.10` | motion sickness |
| Overwork (scheduled > 12 h/day) | −0.5/day | — |
| Skill-matched fulfilling work | +5 | — |

**L_owl** one-way light time: Moon ~1.3 s (negligible), Mars 3.0–22.3 min, Jupiter 32.7–53.7 min, Saturn ~67–91 min.

**Morale effects:**
- Productivity mult `P_morale = 0.5 + 0.5·(M/100)` (M=100 full; M=50 → 0.75; M=0 → 0.5).
- Error/incident mult `φ_err = 2 − M/100` (low morale doubles human-error events feeding `13` + §5 rolls).
- **M ≤ 20** "crisis": chance/day of breakdown event (refuses work / destructive incident).
- **M ≤ 0**: crew **quits** at next Earth-return (or non-functional if stranded). No mutiny/combat (doctrine).
  Loss of worker + heavy morale contagion to crew.

### 4.5 Daily schedule & time budget (player policy; defaults; feeds A and task progress)

| Block | Default hours | A | Notes |
|---|---|---|---|
| Sleep | 8.0 | 0.75 | < 6 h → fatigue penalty |
| Personal/hygiene/meals | 2.5 | 1.0 | uses hygiene water |
| Exercise | 2.0 (0 in ≥Mars-g) | 1.6 | conditioning |
| Work (skill tasks) | 10.0 | 1.0–1.6 | productive block |
| Reserve/contingency | 1.5 | 1.0 | absorbs incidents |

Scheduling > 12 h work or < 6 h sleep accrues fatigue (−productivity, +error mult; recovers with rest).
EVA day replaces a work block at A = 1.6.

### 4.6 Medical events & medbay
**Medbay** (CS-MEDBAY) staffed by Medic treats conditions + lowers event prob (up to 40% preventive). Consumes
MedSupplies (kg)/treatment. Telemedicine consult delayed by L_owl — beyond a few light-min crew is on its own,
Medic skill matters more.

**Event model:** per crew per day roll `p_med ≈ 0.0008/day` (~1 event/3.4 crew-years) × modifiers
(`φ_err` morale, radiation state, low-C injury, EVA exposure, age, crowding/hygiene).

| Condition | Trigger | Untreated outcome | Treatment |
|---|---|---|---|
| Minor illness (cold, GI) | crowding, low morale | −30% prod 3–7 d | MedSupplies + rest |
| Injury (sprain, laceration) | low C, EVA, accident | −50% prod, infection risk | medbay, Medic ≥ 1 |
| Dental abscess | random, time | escalating pain, sepsis | Medic ≥ 2 |
| Appendicitis | random ~1/crew-decade | **fatal in days** w/o surgery | surgery: medbay + Medic ≥ 3 + MedSupplies; else evacuate |
| DCS (bends) | skipped/failed prebreathe | pain, neuro damage, death | recompression + medbay |
| ARS | radiation (§4.2) | per ARS table | medbay + MedSupplies, supportive |
| Kidney stone | dehydration, microgravity Ca loss | severe pain, blockage | hydration + Medic |
| Psychological crisis | M ≤ 20 | breakdown, incident | morale recovery, Medic, rotate home |
| SANS (ocular) | long microgravity | vision degradation, permanent | spin-g/return; partial only |

Untreated conditions escalate over days; unstaffed/unsupplied medbay can't treat surgical → **medical death** path (§5).
Evacuation to Earth/base is fallback but costs a transfer window (`01`).

### 4.7 EVA & suits, prebreathe
**Suit consumables** (per crew per EVA hour, NASA EMU anchor):
- O2 ~**0.09 kg/h** (metabolic ~0.072 + suit leak at 29.6 kPa). EMU PLSS ~0.075 kg/h @ 1000 BTU/hr.
- Cooling water (sublimator, lost to space) ~**0.40 kg/h**.
- CO2 scrubbing: LiOH/metox cartridge (folded into MedSupplies/ECLSS-spares).
- Battery energy from `09`.
- Suit endurance: **8 h nominal + 0.5 h reserve**; exceeding reserve → asphyxiation clock for that crew.
  Suited crew runs its own mini-LSC; a suit breach = §5 emergency, minutes of consciousness.

**Suit catalog (§4.4):**

| ID | Name | Tier | Mass t | O2 use | Cooling | Endurance | Anchor |
|---|---|---|---|---|---|---|---|
| SU-IVA | Launch/entry pressure suit | T0 | 0.02 | n/a (cabin) | n/a | — | in `06` crew mass (80+20 kg) |
| SU-EMU | EVA suit (EMU-class) | T0 | 0.13 | 0.09 kg/h | 0.40 kg/h | 8 h + 0.5 h | NASA EMU/xEMU |
| SU-MCP | Mech. counter-pressure | T3 | 0.07 | 0.08 kg/h | 0.30 kg/h | 8 h | MIT BioSuit (lower leakage) |
| SU-HARD | Hard-shell exploration | T2 | 0.20 | 0.09 kg/h | 0.40 kg/h | 10 h | NASA AX-5/Mark III |

**Prebreathe (DCS):** tissue ratio `R = ppN2_cabin / P_suit`:

| R | Protocol | t_prebreathe |
|---|---|---|
| ≤ 1.4 | none | 0 |
| 1.4–1.65 | light | ~30 min |
| 1.65–2.2 | standard (ISLE-class) | ~2 h |
| > 2.2 | extended / staged | 3–4 h |

Worked: sea-level (ppN2 80) → EMU (29.6) → R=2.70 → 3–4 h prebreathe (big tax → why bases use Exploration atm).
Exploration (ppN2 37) → R=1.25 → **no prebreathe** (frequent EVA). Botched/skipped prebreathe rolls a DCS event.

**Airlock loss** (per EVA cycle), per species (recover kg from pp via molar mass M):
```
loss_X = (1 − 0.8·has_pump) · ppX · M_X · V_airlock / (R·T)   [kg per cycle]
```
Worked: 4 m³ airlock @ exploration atm, no pump, 294 K → loss_N2 ≈ 1.70 + loss_O2 ≈ 1.01 = **~2.7 kg/cycle**;
with scavenge pump (×0.2) ≈ 0.54 kg/cycle. Steady N2/O2 makeup driver for EVA-heavy programs.
(`10` suitports avoid airlock gas loss entirely.)

### 4.8 Player character & permadeath (DECISION — do not relitigate)
Player = **the program, not a single body.** Begin 2049 as lone engineer-founder running a *robotic* program from
Earth ground control — never at risk in Acts 1–2. Save = program continuity (treasury, tech, assets, roster).
- **Founder** may optionally be instantiated as a crew-member avatar once crewed flight begins (Act 1 late / Act 2),
  with own skills/health/dose/morale — then subject to ALL death rules.
- **Career mode (default):** founder-avatar death = major setback (large one-time morale hit all crew, lost skills,
  "succession" event, reputation/economic penalty) but **program continues** under a successor director.
- **Non-founder crew: always permadeath** — gone, morale contagion to survivors, recruitment/economic replace cost.
- **Ironman/Hardcore (toggle, `12`):** founder-avatar death = game over; single save slot.
- **Total-loss failure (Career):** ends only if treasury bankrupt AND no income AND all crew dead/stranded.

### 4.9 GENERATIONS — births & demographics (DECISIONS C19: **MODELED**, binding now; full design Pass 2, impl Phase 6+)
Self-sufficiency includes *biological continuity*, not just industrial closure. Partial-gravity reproduction is
genuinely unknown science → game **models the uncertainty itself** as a research arc (centrifuge studies → mammalian
trials → human protocols; `11` LS-09 → LS-10 → LS-11) with payoffs:
- **Gravity-threshold discoveries** (g_repro brackets for safe gestation/development, drawn per save from deterministic
  seed within defensible bounds).
- **Spin-habitat prescriptions** (g_repro feeds `06 §3.10` spin design + `07` settlement berthing).
- Human-protocol content is **T4 [SPECULATIVE]**, tagged wherever surfaced.

Skeleton contracts (Pass 2 fills; nothing ships before Phase 6+ except `11` research hooks):
- Demographic ledger per settlement: age structure, conceptions/births/deaths, dependency ratio; children are
  non-working crew entities with scaled metabolic baselines (§1) + education/skill-growth tracks.
- Reproduction policy framing: player sets settlement-level policy; sim never forces outcomes on named characters.
- Gravity gating: conception-to-birth + early development legal only in habitats meeting *discovered* g_repro threshold.
- Foundation Audit (`12`) gains a demographic pillar (births, cohort survival, generational skill transfer).
- Failure modes (Pass 2): obstetric medical events, developmental risk outside threshold, demographic collapse of aging settlement.

**Until that system ships, rosters grow by recruitment only (Q6 RESOLVED).**

### 4.10 Crew archetypes (recruitment pool; `12` owns market/salary/cost)

| Archetype | Pilot | Engineer | Scientist | Medic | Agronomist | Cost |
|---|---|---|---|---|---|---|
| Test Pilot | 3 | 1 | 0 | 1 | 0 | high |
| Flight Engineer | 1 | 3 | 1 | 0 | 0 | mid |
| Mission Scientist | 0 | 1 | 3 | 1 | 1 | mid |
| Flight Surgeon | 0 | 0 | 1 | 3 | 0 | high |
| Space Agronomist | 0 | 1 | 1 | 0 | 3 | mid |
| Generalist (early hire) | 1 | 2 | 1 | 1 | 1 | low |

Hidden traits (surface through play, not at hire): *Resilient* (slower morale decay), *Veteran* (starts with some
career dose used, higher skills), *Claustrophobic* (volume penalties hit harder), *Iron Gut* (illness-resistant).

### 4.11 Pension / death economics (DECISIONS F33)
$ ledger persists but fades post-self-sufficiency; investor board becomes advisory; **crew pensions IN (flavor-cost)**.
Corpses: deceased crew's mass remains (recovery/burial = narrative/morale event, `12`); no resource recovery (doctrine).

---

## 5. FAILURE MODES (condensed; §8)

| Mode | Trigger | Consequence | Mitigation |
|---|---|---|---|
| Asphyxiation (hypoxia) | ppO2 < 16 kPa | incapacitation timer; death ~1.5× | O2 reserve, OGA, alarms, suits |
| Hypercapnia | ppCO2 > 3 kPa | impairment → unconscious | redundant CO2 removal, LiOH backup |
| Rapid depressurization | hull breach/Whipple | choked-flow leak; 10 cm² = minutes | isolation, patch kit, don suits |
| Slow leak | seal wear, micro-puncture | gradual P drop; N2/O2 makeup drain | leak-check, makeup gas, Engineer seal task |
| Water recovery failure | UPA/WPA fault | η_H2O → 0; potable depletes | repair (Engineer), water reserve |
| O2 generation failure | OGA fault / power loss | air O2 depletes; ~days buffer | O2 tank reserve, fix power/OGA |
| Food shortfall | depletion, blight, greenhouse lag | starvation deficit; death at reserve=0 | emergency cache, staggered planting, ration cut |
| Crop blight / algae crash | monoculture, contamination, power loss | η_food drops, crop lost; recovery = full cycle | diversity, Agronomist, sterile proc, buffer |
| Power loss to ECLSS | reactor/array fault | cascade: no CDRA/OGA/CHX/lights | battery buffer, life-support-priority load-shed |
| Thermal control loss | radiator/loop fault | cabin out of 18–27°C; <0/>40 → medical/death | redundant loops, retreat, repair |
| Radiation SPE | solar flare | acute spike; ARS if unsheltered | storm shelter, time-warp pause + alert |
| Radiation chronic | long deep-space/belt | D_career → 600 mSv; cancer roll; forced rotation | shielding, duration limits, rotation |
| Europa/Jupiter lethal field | crew on/near Europa | ~5.4 Gy/day → death in hours | robotic/teleop only; shielded orbit |
| Deconditioning | long microgravity, no exercise | C falls; EVA blocked < 40; re-entry injury | exercise device, spin-g, surface g |
| DCS (bends) | skipped/failed prebreathe | medical event, possible death | correct prebreathe, exploration atm, recompression |
| Suit failure on EVA | breach, consumable exhaustion | minutes of consciousness | buddy EVA, suit reserve, nearby airlock |
| Medical surgical | appendicitis etc. | fatal in days w/o surgery | medbay + Medic ≥ 3 + MedSupplies, or evacuate |
| MedSupplies exhaustion | no production/import | no treatment, no ECLSS filters | establish `05` off-Earth, stockpile |
| Morale collapse | crowding, isolation, deaths | productivity floor, breakdown, quit | volume, privacy, fresh food, views, rotation |
| Founder death | death rule on avatar | Career: succession + morale/econ hit; Ironman: game over | keep founder out of high-risk ops |
| Stranding | no return dv/window (`01`) | survive only while consumables/loops hold | closed loops, rescue, pre-positioned supplies |

**Edge rules:** sleeping crew still consume at A=0.75 (LSC never pauses under time warp). Zero-crew vessels run no LSC.
Overcrowding allowed temporarily (rescue) with stacking CO2/humidity/volume penalties (lethal long-term). Cold-soak
can freeze water lines (burst→leak) and spoil fresh food; dehydrated food is freeze-tolerant.

---

## 6. UI / INTEGRATION CONTRACT
Per crewed vessel/base **Life-Support panel** (visible spreadsheet):
1. Atmosphere gauges (ppO2/ppCO2/P/humidity/T) w/ §1.6 band colors + trend arrows + time-to-limit.
2. Loop diagram (Sankey): crew/CDRA/OGA/Sabatier/WRS/greenhouse boxes; kg/day arrows; closure fractions; vents in red.
3. Consumable burn-down: O2/Water/Food/MedSupplies/N2 stores vs net draw; headline **"Days of life support remaining"**
   = `min over resources of (store / net_daily_draw)`.
4. Crew roster cards: portrait, 5 skills, M, C, D_career (600 mSv bar), activity, health status, task; hover = full breakdown.
5. Schedule editor (drag work/sleep/exercise/EVA per crew; previews A, fatigue, C trajectory).
6. EVA planner (crew+suit → prebreathe time, consumables, airlock loss, go/no-go: C ≥ 40, suit charged, prebreathe done).
7. Greenhouse manager (allocate Area among crops; preview kcal/power/water/time-to-harvest; monoculture/blight/power warnings).

**Policies not micromanagement:** player sets target ppO2/ppCO2 setpoint, exercise prescription, ration type,
storm-shelter trigger; sim runs policies under time warp, pauses on emergencies. Under comms delay base runs autonomously.
**Readout honesty:** every displayed number = the number the sim integrates; hovering shows its §3 formula.

---

## 7. GAP vs CODE (current implementation)

Files inspected: `aphelion/sim/habitat/lsc.py`, `aphelion/sim/habitat/dose.py`, `aphelion/game/crew.py`.
Current state = **one lumped consumption rate + ECLSS multiplier; crew have 3 skills + a single career-dose accumulator.**

### 7.1 `lsc.py` — life-support consumption ledger
**Present:** crew metabolism transformer (O2+Food+Water → CO2+WasteWater); water processor (recovery frac);
OGA electrolysis (Water→O2+H2); ISS-grade hab builder with buffer stores + power supply; ledger emerges closure %.
**Missing / wrong:**
- **Water baseline = 3.0 kg/day in code (`WATER_KG_DAY=3.0`); spec is 3.5** (2.5 drink+prep + 1.0 hygiene). **Conflict — fix to 3.5.**
- No activity multiplier A (sleep 0.75 / work 1.0 / EVA 1.6); consumption is flat.
- No partial-pressure atmosphere physics: no ppO2/ppCO2/ppN2/ppH2O, no V_press, no T, no safe-bands/alarms.
- No CO2 accumulator store; no Sabatier/Bosch reduction stoichiometry (CH4 vent, 0.818 H2O recovery, η_O2 0.42/0.50).
- No CDRA scrub-vs-air single-counting; CO2 just flows to a generic store.
- No leak model (k_leak·P·A_hull) and no choked-flow breach (C·a_hole·P, τ, exponential decay).
- No CHX humidity loop; no hypoxia/hypercapnia incapacitation clock.
- No ration types (FD-DEHY/PKG/FRESH/EMRG): no variable prep water, shelf life, spoilage.
- No caloric/starvation model (kcal_req, 90,000 kcal reserve).
- No greenhouse/CEA model at all: no crops, cycle lag, yields, light/water/Ammonia, fresh-food store + cap + dry-overflow.
- No algae photobioreactor.
- No N2 buffer-gas makeup; no airlock per-species loss; no EVA suit mini-LSC / prebreathe / DCS.
- No explicit per-subsystem closure-fraction ladder (η_CO2rm/η_O2/η_H2O/η_food) or hardware catalog (LS-* IDs,
  mass/power/spares); current OGA power (~1.5 kW placeholder) and processor recovery (0.90) are hardcoded, not catalog-driven.
- No MedSupplies/ECLSS-spares consumption per unit.

### 7.2 `dose.py` — radiation dose
**Present:** ambient mSv/day table, exponential attenuation w/ decaying GCR floor, single `CrewDose` career accumulator.
**Missing / wrong:**
- **`CAREER_LIMIT_MSV = 1_000.0` — spec & NASA-STD-3001 anchor is 600 mSv. Conflict — fix to 600.** No 400 mSv caution flag.
- **Shielding formula differs from spec.** Code uses material halving thicknesses (water 18 / regolith 22 / poly 15 g/cm²)
  and `max(direct, floor)`. Spec mandates GCR `f_GCR = 0.30 + 0.70·exp(−σ/30)` and SPE `f_SPE = exp(−σ/12)` — distinct
  per-channel laws (not a single material-halving). **Reimplement to the spec's f_GCR/f_SPE pair.**
- **Floor-decay constant differs:** code `FLOOR_DECAY_HALVING = 120 g/cm²` (0.5^((σ−1000)/120)); spec A3 is
  `0.30·exp(−(σ−1000)/1000)` (e-fold 1,000 g/cm²). **Conflict — fix e-fold to 1,000.**
- No GCR-vs-SPE channel split / quality factor Q (GCR Q≈3, SPE Q≈1); no separate **D_acute (mGy, rolling 24 h)**.
- No ARS bands / death rolls; no REID cancer-incidence roll; no `f_cycle` solar modulation (1.8·f_cycle, 0.65–1.35).
- No SPE event model (lognormal median 100, σ_ln 1.2, cap 2,000, 6–48 h, ×1/d²); no Van Allen piecewise belt field.
- Ambient table lacks LEO, deep-space cruise (has `deep_space` flat 1.8 without f_cycle), Jupiter D_jup(r), SPE row.

### 7.3 `crew.py` — crew characters
**Present:** 3 roles (pilot/engineer/scientist), single int skill 1-3, CrewDose, training (busy_until, 90 d/$12M),
deterministic candidate pool, vessel bonuses (prox_ops dv, lss_bonus, science_mult), reap-over-limit.
**Missing / wrong:**
- **Only 3 skill ROLES; spec needs 5 SKILL TRACKS per crew** (add Medic, Agronomist), each level **0-5** (code is single
  role + skill 1-3). Need per-crew 5-tuple, not one role+level.
- **Skill cap not tier-gated** (T0-1 → 3, T2 → 4, T3+ → 5); XP-per-task-hour growth absent (only the training action).
- No **morale M** (target/lag, modifier table, P_morale, φ_err, crisis/quit thresholds).
- No **conditioning C** / deconditioning ODE / exercise e_ex / EVA C≥40 gate / re-entry & orthostatic effects.
- No **P_health** composition (C floor × med_penalty × rad_penalty).
- No medical-event system (p_med roll, condition table, medbay+Medic gating, MedSupplies consumption, medical-death path).
- No daily schedule/activity → A feedback; no fatigue (>12 h / <6 h sleep).
- No hidden traits (Resilient/Veteran/Claustrophobic/Iron Gut).
- No founder avatar / succession / Ironman / permadeath meta-rules.
- No GENERATIONS demographic skeleton (C19) — even the `11` research hooks (LS-09/10/11) are absent.
- `reap_over_limit` uses `dose.over_limit` against the wrong 1,000 mSv limit; should be soft (override) in Career, hard in Ironman.

### 7.4 Net assessment
Code implements ~15% of §3: the **mass-ledger spine** (metabolic transformer + water recovery + OGA + career dose).
The atmosphere physics, ECLSS closure ladder + hardware catalog, food/agriculture, acute-dose/ARS/SPE, gravity/morale/
medical/schedule character systems, EVA/prebreathe, and the founder/generations meta-layers are all unbuilt.
Two **direct numeric conflicts to reconcile first** (DECISIONS A2 byte-identical audit): water 3.0→3.5 kg/day,
career limit 1,000→600 mSv, plus the f_GCR/f_SPE shielding law + floor e-fold 120→1,000 g/cm².
