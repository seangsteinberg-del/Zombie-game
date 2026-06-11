# BUILD SPEC — Research & Technology Tree (extracted from design/11-research-tech.md)

Source of truth: `design/11-research-tech.md` (post-DECISIONS rebalance). Conflicts resolved per `design/DECISIONS.md` (A5 one-wear-model, A6 aerostat split, C19 gravity-biology arc, E balance placeholders).
Implementation targets: `data/core/tech/*.toml` content pack + `aphelion/sim/research.py`.

**Node count note:** the tree is **132 nodes** as written (the older "129" count predates DECISIONS C19, which added LS-09/10/11). 132 is canonical.

**ID convention used here:** canonical node id = snake_case slug prefixed with the doc code (e.g. `pr09_ntr`). Prereq columns reference the code prefix only (`pr09`); the prefix uniquely identifies a node. Content-pack ids should be `core:tech_<id>`. Node ids are stable strings forever (save schema, doc §8 F-12).

**Prereq grammar:** `+` and `,` = AND (all required); `|` = OR and **binds tighter than AND** — `(a | b) + c` means c AND at least one of a/b. `dscNN` = Discovery prerequisite (§4 below). T0 nodes are start-unlocked: cost 0, no prereqs.

**Tags:** `(era)` = era-defining node (changes the shape of the game). `[SPEC]` = `[SPECULATIVE]`, rendered with watermark + honesty tooltip.

---

## 1. Tree shape & global rules

### 1.1 Node counts

| Branch | Code | T0 | T1 | T2 | T3 | T4 | Total |
|---|---|---|---|---|---|---|---|
| Propulsion | PR | 1 | 8 | 7 | 5 | 2 | 23 |
| Guidance, Nav & Comms | GN | 1 | 3 | 3 | 1 | 0 | 8 |
| Power & Thermal | PW | 1 | 3 | 4 | 4 | 1 | 13 |
| ISRU & Resources | IS | 1 | 4 | 9 | 7 | 2 | 23 |
| Industry & Automation | IN | 1 | 4 | 4 | 5 | 1 | 15 |
| Ships, Stations & Logistics | SH | 1 | 3 | 3 | 1 | 2 | 10 |
| Habitats & Bases | HB | 0 | 1 | 2 | 5 | 1 | 9 |
| Life Support & Crew | LS | 1 | 3 | 5 | 2 | 1 | 12 |
| Vehicles | VH | 1 | 3 | 3 | 4 | 0 | 11 |
| Science Instruments & Labs | SC | 1 | 2 | 4 | 1 | 0 | 8 |
| **Total** | | **9** | **34** | **44** | **35** | **10** | **132** |

### 1.2 Cost bands (design targets; individual nodes may move ±30% in balancing)

| Tier | SCI cost band | ED threshold band | TRL meaning |
|---|---|---|---|
| T0 | 0 (start-unlocked) | — | TRL 9, flown by 2049 |
| T1 | 60–300 | 80–400 | TRL 6–8 flight-proven derivatives |
| T2 | 300–900 | 200–1,200 | TRL 4–6 studied-and-credible |
| T3 | 900–2,500 | 400–2,000 | TRL 2–4 lab-demonstrated |
| T4 `[SPECULATIVE]` | 4,000–12,000 | 2,000–4,000 | physics-sound, engineering-incomplete |

### 1.3 Economy totals (post A6/C19 rebalance — must reproduce)

- Tier SCI sums: **T1 ≈ 5,100 / T2 ≈ 22,300 / T3 ≈ 54,000 / T4 ≈ 77,000 → ≈ 158,400 SCI** for the whole tree (T4 ≈ 49%).
- Total recoverable Science in the system with thorough Earth-return play ≈ **210,000 SCI** = sample pools at ×1.25 Earth-return + Discoveries (≈ 12,300) + milestones + observation campaigns at the program-wide cap (15,000). Excludes the unbounded-but-small contract trickle.
- Per-act income targets: Act 1 ≈ 1,500–2,500; Act 2 ≈ 8,000; Act 3 ≈ 15,000; Act 4 ≈ 25,000; Act 5 ≈ 40,000+.
- Act-1 spine to the Moon: GN-01/02/03 + PR-01/02/04/05 + SH-01 + LS-03 = **1,390 SCI**.

### 1.4 Node unlock rule (all five must hold)

1. Node is **visible** (fog of research, §1.5) — hidden "???" nodes cannot be researched, hard gate.
2. Every prerequisite node researched.
3. Every prerequisite **Discovery** acquired (§4).
4. Global Science ≥ SCI cost (cost is **spent/destroyed** on confirm; no decay, no refund).
5. For each listed ED threshold, the named family's `D_f ≥ threshold` (**checked, never spent**).

Unlock is instantaneous on payment — the time cost of new tech lives in prototyping (§3) and fabrication hours (doc 05).

**Discounts:** Discovery discounts multiply the SCI cost before payment. Earth R&D campus (doc 12) adds up to a further −20%. Stacking is multiplicative with a floor: `cost = base · Π(1−d_i)`, clamped `≥ 0.4·base` (F-13). UI shows post-discount cost with struck-through original.

### 1.5 Tree visibility (fog of research)

- All T0 and T1 nodes: always visible.
- A T(n≥2) node is visible when (a) any node within **distance 1 in its prerequisite graph** is researched, OR (b) its gating Discovery is acquired.
- T4 nodes additionally hidden until **at least one T3 node in the same category** is researched. `[SPECULATIVE]` watermark on all T4 UI.
- Hidden nodes render as "???" silhouettes showing tier + category only.

### 1.6 The 10 era-defining nodes

PR-02 (Act 1, $/kg collapse) · PR-05 (Act 1→2, depots/logistics map) · IS-05 (Act 2, Moon becomes gas station) · PR-09 (Act 2→3, NTR opens belt) · PW-05 (Act 2→3, survive lunar night) · LS-07 (Act 3→4, crew stop being resupply liability) · IN-10 (Act 4, exponential base growth) · IN-11 (Act 4, "Silicon Independence" — last Earth umbilical cut) · IN-12 (Act 4→5, propellantless bulk export) · PR-22 `[SPEC]` (Act 5→End, outer system commute).

### 1.7 Victory-path guarantee (audit invariant)

SH-09 must be reachable via PR-21 (fission-fragment) without any fusion/He3 content; its discovery prerequisites touch only the Moon (DSC-02 applies only on the PR-22/PW-12 branch). Because T4 visibility requires a researched in-category T3 node, the audited chain includes **SH-07** (the SH category's only T3 node) and its prereqs **GN-07 + HB-06** (≈ 3,300 SCI extra, no Discoveries). Venus/Titan/Europa content is optional but carries discounts and ~40% of total recoverable Science.

### 1.8 Edge-formula summary (implementation checklist, verbatim from doc §3.9)

```
SCI pool:        P = V_base·X;  S_n = 0.6·R_(n-1);  R_n = R_(n-1)−S_n   (S_n = 0.6·0.4^(n−1)·P)
Award:           S_n·M_analysis·max(0.2, 1−0.02·days_above_150K)   [decay term cryo-only]
ED accrual:      dD/dt = Σ_g R_f·√N_g·M_env(f, class(g))  (+ event terms; g = part type × env class)
Cap:             C_f = max(1.5·max visible threshold (0 if none), 6·D_half)
Maturity:        m(D) = 1 + 3·2^(−D/D_half);   λ_live = λ_min·m(D)·m_state·m_unit·(wear terms 02/05)
Prototype:       cost ×3, fab time ×2, m_state = 4 until 1 full-duration success
Infant unit:     m_unit = 2.5 first 50 h / 3 ignitions, else 1
Unlock:          visible ∧ prereqs ∧ discoveries ∧ SCI ≥ cost (spend) ∧ ∀f: D_f ≥ threshold_f (check)
```

All RNG from the deterministic mission seed (doc 13). ED accrual, observation trickle, and sample decay must integrate **analytically under time warp** (closed-form linear segments, events scheduled at threshold crossings: cap hit, milestone, 200-h M_env expiry). No per-tick iteration in the warp path.

---

## 2. FULL NODE CATALOG — all 132 nodes

### 2.1 Propulsion (PR) — 23 nodes (parts in doc 02)

| ID | Name | Tier | Prereqs | SCI | ED (family) | Unlocks | Description / anchor |
|---|---|---|---|---|---|---|---|
| pr00_flight_proven_stack | Flight-Proven Stack | T0 | — | 0 | — | SRM-2, SRM-49, OMS-27, SPS-91, K-845, KV-981, H-102, RCS-N10, RCS-D400, ION-2 "Mayfly" ion + HALL-1 "Wren" Hall (EPThrusters T0 donors), parametric tanks (CryoFluidMgmt T0 donor) | 2049 baseline: everything that has actually flown. Falcon 9 / Centaur / Soyuz heritage; NSTAR; SPT-100 |
| pr01_deep_throttle_landers | Deep-Throttle Landing Engines | T1 | pr00 + gn02 | 80 | 100 (StorableEngines) | LND-71 lander engine | Apollo LMDE 10:1 throttle; BE-7 |
| pr02_reusable_methalox **(era)** | Reusable Methalox Heavy Lift | T1 | pr00 | 220 | 200 (KeroloxEngines) | M-2256, MV-2530, RCS-M2K; reusable booster ops (06/12) | $/kg to LEO collapses. SpaceX Raptor FFSC / Starship |
| pr03_modern_hydrolox | Modern Hydrolox Upper Stages | T1 | pr00 | 100 | 150 (HydroloxEngines) | HL-67, H-2280 | RL10 family (since 1963), Centaur V |
| pr04_cryo_fluid_mgmt | Cryogenic Fluid Management | T1 | pr00 | 150 | 200 (CryoFluidMgmt) | ZBO-90/ZBO-20 cryocoolers, sunshields, PMD tanks | ULA IVF; NASA eCryo/CFM demos |
| pr05_orbital_depot **(era)** | Orbital Propellant Depot | T1 | pr04 + gn01 | 250 | 400 (CryoFluidMgmt) | DEP-60, PTC-200 coupler, propellant-transfer ops (02 §3.13) | ULA depot studies; Starship HLS refueling |
| pr06_gridded_ion | Gridded Ion Propulsion | T1 | pr00 | 120 | 100 (EPThrusters) | ION-7 | NASA NEXT-C: 6.9 kW, 4,190 s, 236 mN |
| pr07_hall_clusters | High-Power Hall Clusters | T1 | pr00 | 140 | 150 (EPThrusters) | HALL-12 | AEPS/HERMeS 12.5 kW (Gateway PPE) |
| pr08_solar_sail_demo | Solar Sail Demonstrator | T1 | pr00 | 90 | — | SAIL-86 | NEA Scout; IKAROS, LightSail 2 |
| pr09_ntr **(era)** | Nuclear Thermal Rocket | T2 | pr04 + pw04 | 700 | 500 (HydroloxEngines) + 300 (FissionSystems) | NTR-73 "Prometheus" | Isp ~900 s. NERVA/SNRE; DARPA DRACO |
| pr10_heavy_ntr | Heavy NTR Core | T2 | pr09 | 500 | 800 (NTRCores) | NTR-246 "Prometheus-H" | NERVA XE': 246 kN ground-tested 1969 |
| pr11_lantr | LANTR Augmentation | T2 | pr09 | 350 | 600 (NTRCores) | LANTR option (O/H MR 3.0: thrust ×2.75 @ Isp 645 s per 02 §3.10) | Borowski LANTR studies |
| pr12_ntr_alt_propellants | NTR Alternate Propellants | T2 | pr09 | 300 | 600 (NTRCores) | Ammonia/Water NTR modes (02 §3.10) | NERVA-era alternate-propellant studies |
| pr13_isru_refuelable_landers | ISRU-Refuelable Landers | T2 | pr02 + is04 | 400 | 300 (MethaloxEngines) | ML-24 "Gopher", field-refueling ops | Project Morpheus; Mars Direct ERV |
| pr14_large_solar_sails | Large Solar Sails | T2 | pr08 | 350 | — | SAIL-1650 | NASA Solar Cruiser (1,653 m²) |
| pr15_heavy_depots | Heavy Depot Infrastructure | T2 | pr05 | 450 | 700 (CryoFluidMgmt) | DEP-600 "Reservoir", LH2 depot-grade insulation | ULA/NASA cryo depot architectures |
| pr16_nested_hall | Nested-Channel Hall Thrusters | T3 | pr07 + pw08 | 1,200 | 900 (EPThrusters) | HALL-100 "Condor" | X3 nested Hall, 102 kW demo |
| pr17_mpd | MPD Thrusters | T3 | pr16 | 1,800 | 1,500 (EPThrusters) | MPD-200 "Albatross" | NASA Lewis / MAI applied-field MPD |
| pr18_vasimr | VASIMR | T3 | pr16 | 1,600 | 1,200 (EPThrusters) | VAS-200 "Petrel" | Ad Astra VX-200: 200 kW lab firings |
| pr19_industrial_sails | Industrial Solar Sails | T3 | pr14 | 1,000 | — | SAIL-10K | scaled NIAC/JPL sail-cargo studies |
| pr20_inspace_engine_refurb | In-Space Engine Refurbishment | T3 | pr10 + in06 | 1,400 | 1,200 (NTRCores) | NTR refurbishment-in-space, advanced PMD/LAD couplers | ISS ORU servicing; OSAM |
| pr21_fission_fragment `[SPEC]` | Fission-Fragment Drive | T4 | pr17 + pw08 | 6,000 | 2,500 (FissionSystems) | FFR-43 "Phoenix" | Werka dusty-plasma FF rocket, NIAC 2012 |
| pr22_fusion_torch `[SPEC]` **(era)** | Fusion Torch Drive | T4 | pw12 | 9,000 | 3,000 (FissionSystems) | DFD-5 "Helios"; PULSE-D blueprint access (endgame chain) | Princeton DFD; Project Daedalus 1978 |

### 2.2 Guidance, Navigation & Comms (GN) — 8 nodes (programs in doc 01 §4.7)

| ID | Name | Tier | Prereqs | SCI | ED (family) | Unlocks | Description / anchor |
|---|---|---|---|---|---|---|---|
| gn00_baseline_gnc | Baseline GNC | T0 | — | 0 | — | Node Execute, Ascent Guidance, Circularize, Hohmann Planner | Saturn V IGM; flown upper-stage guidance |
| gn01_rendezvous_prox_ops | Rendezvous & Proximity Ops | T1 | gn00 | 100 | 80 (Avionics) | Rendezvous Sequencer, Autodock, Stationkeeping Manager, Window Finder | Kurs, ATV, Dragon autodock |
| gn02_powered_descent | Powered Descent Guidance | T1 | gn00 | 130 | 100 (Avionics) | Vacuum Landing program | Apollo P63–P66; Falcon 9 landing |
| gn03_relay_constellations | Relay Constellations | T1 | gn00 | 160 | — | relay satellite parts; comms-path rules for teleop & telemetry | TDRS; Mars relay network |
| gn04_atmospheric_flight | Atmospheric Flight Guidance | T2 | gn02 | 450 | 300 (AeroFlight) | EDL Guidance + Aerocapture Guidance programs; aeroshell parts (06) | Viking→Mars 2020 EDL; aerocapture studies |
| gn05_low_thrust_planning | Low-Thrust Mission Planning | T2 | pr06 \| pr07 | 400 | 200 (EPThrusters) | Low-Thrust Spiral planner | Edelbaum; SMART-1, Dawn ops |
| gn06_optical_comms | Optical Deep-Space Comms | T2 | gn03 | 500 | 200 (Avionics) | laser comm terminals: telemetry/teleop range ×10 | NASA DSOC on Psyche |
| gn07_tour_planning | Multi-Flyby Tour Planning | T3 | gn05 | 1,100 | 400 (Avionics) | Tour Planner (gravity-assist chains within planetary systems) | Galileo/Cassini tour design |

### 2.3 Power & Thermal (PW) — 13 nodes (parts in doc 09)

| ID | Name | Tier | Prereqs | SCI | ED (family) | Unlocks | Description / anchor |
|---|---|---|---|---|---|---|---|
| pw00_baseline_power | Baseline Power | T0 | — | 0 | — | rigid PV arrays, Li-ion packs, MMRTG (110 We), baseline body-mounted radiators (ThermalControl T0 donor) | ISS arrays; MMRTG |
| pw01_rollout_arrays | Roll-Out Arrays & Concentrator Mirrors | T1 | pw00 | 80 | 100 (SolarPower) | ROSA-class wings (20+ kW), drop-in array upgrades; SOL-CONC heat-only concentrators (116 kWt @ 1 AU, process heat for 04) | ISS iROSA; CSP heliostats |
| pw02_regen_fuel_cells | Regenerative Fuel Cells | T1 | pw00 | 120 | 100 (EnergyStorage) | RFC night-survival storage (H2/O2 loop) | Gemini/Shuttle fuel cells; lunar-night RFC studies |
| pw03_high_cap_radiators | High-Capacity Radiators | T1 | pw00 | 100 | 100 (ThermalControl) | deployable two-phase radiator wings | ISS EATCS ~70 kW |
| pw04_kilopower | Kilopower Fission | T2 | pw00 | 450 | 200 (FissionSystems) | NUK-KP1 + NUK-KP10 units, 1–10 kWe | KRUSTY test, March 2018 |
| pw05_fission_surface **(era)** | Fission Surface Power | T2 | pw04 | 800 | 500 (FissionSystems) | 40–100 kWe-class surface reactors | NASA FSP program (40 kWe contracts 2022) |
| pw06_adv_pv_dust | Advanced PV & Dust Mitigation | T2 | pw01 | 350 | 250 (SolarPower) | 36%-cell array retrofits, SOL-BLK thin-film blankets; SOL-EDS electrodynamic dust shields | NREL 39.2% cell; EDS on Blue Ghost M1 (2025) |
| pw07_thermal_storage | Thermal Energy Storage | T2 | pw03 | 300 | 200 (ThermalControl) | molten-salt / regolith thermal batteries for lunar night | CSP storage; lunar TES studies |
| pw08_megawatt_reactors | Megawatt Space Reactors | T3 | pw05 + pw09 | 1,800 | 1,800 (FissionSystems) | 0.5–2 MWe NEP cores (powers pr16/17/18 tugs) | SP-100; Prometheus/JIMO |
| pw09_brayton | Closed Brayton Conversion | T3 | pw05 | 1,200 | 900 (ThermalControl) | Brayton conversion units (η ≈ 25–30%); NUK-MSR 500 kWe thorium molten-salt surface plant (Th from lunar KREEP, 04) | NASA BRU tests; ORNL MSRE |
| pw10_radioisotope_prod | Radioisotope Production | T3 | pw05 + is09b | 1,000 | 1,000 (FissionSystems) | RX-19 Pu-238 line: 20 g Pu238/yr per 100 kWe core | Oak Ridge Pu-238 restart |
| pw11_power_beaming | Power Beaming | T3 | pw08 + gn06 | 1,400 | 600 (SolarPower) | laser power links: kW-class over 10s of km (PSR rim→crater floor) | NASA Watts on the Moon |
| pw12_fusion_plant `[SPEC]` | Fusion Power Plant | T4 | pw08 + is20 | 10,000 | 4,000 (FissionSystems) | D-He3 fusion plants (MWe-class, 09); enables pr22 | Kulcinski D-He3 concepts; SPARC/ARC lineage |

### 2.4 ISRU & Resource Processing (IS) — 23 nodes (machines/recipes in doc 04)

| ID | Name | Tier | Prereqs | SCI | ED (family) | Unlocks | Description / anchor |
|---|---|---|---|---|---|---|---|
| is00_orbital_prospecting | Orbital Prospecting | T0 | — | 0 | — | orbital spectrometer instruments; RX-05 SOXE demo (0.29 kg O2/day) | LRO/LCROSS/M3; MOXIE 122 g O2 |
| is01_surface_survey_coring | Surface Survey & Coring | T1 | is00 | 90 | — | Core Drill, Thermal Ice Corer, K2 ground-survey package | Honeybee TRIDENT (PRIME-1) |
| is02_regolith_excavation | Regolith Excavation | T1 | is01 | 110 | — | Drum Excavator | NASA KSC RASSOR |
| is03_water_electrolysis | Water Electrolysis Plant | T1 | is00 | 130 | 100 (ECLSS-PhysChem) | RX-01 PEM electrolyzer (250 kg H2O/day), LOX/LH2 liquefaction chain | ISS OGA; industrial PEM |
| is04_sabatier | Sabatier Methanation | T1 | is03 | 150 | 120 (ECLSS-PhysChem) | RX-03 Sabatier (91 kg CH4/day), LCH4 liquefaction, vapor-return cryo transfer | ISS Sabatier; Mars Direct ISPP |
| is05_polar_ice_mining **(era)** | Polar Ice Mining | T2 | is02 + dsc01 | 550 | 300 (MiningMachines) | Bucket-Wheel excavator, Sublimation Tent, Rodwell | LCROSS Cabeus: 5.6±2.9 wt% H2O |
| is06_mars_atmo_processing | Mars Atmosphere Processing | T2 | is04 + dsc04 | 600 | 250 (ISRU-Chem) | Mars CO2 intakes, RX-04 RWGS, RX-05 plant scale (100 kg O2/day) | MOXIE scale-up; DRA 5.0 |
| is07_beneficiation | Beneficiation & Ore Dressing | T2 | is02 | 400 | 250 (MiningMachines) | Beneficiation Separator (magnetic/electrostatic) | lunar ilmenite concentration studies |
| is08_ilmenite_reduction | Ilmenite Hydrogen Reduction | T2 | is07 | 650 | 400 (ISRU-Chem) | RX-07 line (100 kg O2/day + IronSteel + TiO2 slag) | Apollo/Artemis lunar-oxygen baseline |
| is09a_gas_volatile_chem | Gas & Volatile Chemistry | T2 | is04 | 500 | 300 (ISRU-Chem) | RX-13 Cryo Fractionator, RX-14 Haber loop, RX-15 Polymer plant | air-separation industry; Haber-Bosch |
| is09b_materials_chem | Materials Chemistry | T2 | is07 | 550 | 300 (ISRU-Chem) | RX-06 Bosch, RX-12 H2-DRI steel, RX-17 Basalt/Glass furnace | HYBRIT H2-DRI; basalt fiber |
| is10_nea_volatile_capture | NEA Volatile Capture | T2 | is01 + dsc15 | 500 | 200 (MiningMachines) | Capture Bag, Volatile Oven (C-type baking) | NASA ARM; Hayabusa2/OSIRIS-REx |
| is11_deep_core_drilling | Deep Core Drilling | T2 | is01 | 450 | 300 (MiningMachines) | Deep Core Rig (>10 m), deep-core sample type | wireline coring; Mars deep-drill studies |
| is12_carbothermal | Carbothermal Reduction | T2 | is08 | 700 | 500 (ISRU-Chem) | RX-08 carbothermal O2 (any regolith, 50 kg O2/day) | NASA/Sierra Space CaRD (2023) |
| is13_molten_regolith | Molten Regolith Electrolysis | T3 | is12 + pw05 | 1,600 | 800 (ISRU-Chem) | RX-09 MRE cell (250 kg O2/day + Fe-Si) | MIT MRE (Sadoway/Schreiner) |
| is14_carbonyl_refining | Carbonyl Metal Refining | T3 | is10 + dsc16 | 1,400 | 700 (ISRU-Chem) | RX-10 Mond refinery (500 kg metal/day, PGM residue) | INCO Clydach process; *Mining the Sky* |
| is15_light_metals | Light-Metal Production | T3 | is13 | 1,800 | 1,000 (ISRU-Chem) | RX-11 anorthite Al line, RX-18 FFC titanium cell | NASA SP-509; FFC Cambridge |
| is16_solar_silicon | Solar-Grade Silicon | T3 | is13 | 1,500 | 800 (ISRU-Chem) | RX-16 Siemens refiner (20 kg/day solar-grade Si) | Siemens trichlorosilane process |
| is17_strip_optical_mining | Strip & Optical Mining | T3 | is05 \| is10 | 1,300 | 900 (MiningMachines) | strip miners; Optical Mining (concentrated-sunlight spalling) | TransAstra Apis NIAC |
| is18_venus_aerostat_intake | Venus Aerostat Intake | T3 | hb05 + dsc08 | 1,700 | 600 (ISRU-Chem) | Venus Aerostat Intake (CO2/N2 capture at 52 km) | NASA HAVOC; 96.5% CO2 / 3.5% N2 |
| is19_titan_hydrocarbons | Titan Hydrocarbon Processing | T3 | dsc13 + is09a | 1,600 | 600 (ISRU-Chem) | Titan Sea Pump, Titan atmosphere intake (CH4/N2) | Cassini/Huygens lakes; TiME |
| is20_he3_kiln `[SPEC]` | He3 Volatile Kiln | T4 | is17 + dsc02 | 7,000 | 2,500 (MiningMachines) | He3 Volatile Kiln (g/t-level H2/H2O/N2/C byproducts + ppb He3) | Wittenberg/Kulcinski/Schmitt: 5–20 ppb He3 |
| is21_gas_giant_scoop `[SPEC]` | Gas-Giant Atmospheric Scoop | T4 | pr22 + dsc18 | 8,000 | 2,000 (AeroFlight) | atmospheric scoop craft (H2/He/He3 skimming) | Daedalus aerostat He3 concept |

### 2.5 Industry & Automation (IN) — 15 nodes (modules/robots in doc 05)

| ID | Name | Tier | Prereqs | SCI | ED (family) | Unlocks | Description / anchor |
|---|---|---|---|---|---|---|---|
| in00_earth_supply_chain | Earth Supply Chain | T0 | — | 0 | — | polymer printer farm, automated cargo docking, manual EVA ops (A0) | ISS commercial resupply lineage |
| in01_workshop | Pressurized Workshop & Machine Shop | T1 | sh01 | 100 | 80 (FabricationMachines) | machine shop, pressurized workshop (05) | ISS maintenance work area |
| in02_foundry_chem_plant | Foundry & Chemical Plant | T1 | in01 | 140 | — | foundry & mill, chemical plant (05) | terrestrial small-batch industry |
| in03_electronics_assembly | Electronics Assembly | T1 | in01 | 180 | — | electronics assembly line (imported Wafers) | SMT lines; in-space mfg pilots |
| in04_robotic_manipulation | Robotic Manipulation (A1) | T1 | gn01 | 150 | 100 (RoboticsAutonomy) | berthing arm, dexterous unit | Canadarm2 / Dextre |
| in05_orbital_assembly_waam | Orbital Assembly & WAAM | T2 | in01 + sh01 | 500 | 350 (FabricationMachines) | WAAM cell, assembly hall | wire-arc additive; OSAM/Archinaut |
| in06_orbital_dry_dock | Orbital Dry Dock | T2 | in05 | 700 | 500 (FabricationMachines) | orbital dry dock (06: never-lands ships) | ISS truss assembly, scaled |
| in07_teleop_robots | Teleoperated Worker Robots (A2) | T2 | in04 + gn03 | 550 | 400 (RoboticsAutonomy) | worker robots, surface teleoperation (incl. orbit→surface) | ESA Analog-1 / METERON |
| in08_auto_haulage | Automated Haulage Routes | T2 | vh02 + in07 | 400 | 250 (SurfaceMobility) | automated surface logistics routes (05) | Pilbara autonomous haul trucks |
| in09_supervised_autonomy | Supervised Autonomy (A3) | T3 | in07 | 1,400 | 1,000 (RoboticsAutonomy) | A3 autonomy: task queues without comms link | Mars rover AutoNav lineage |
| in10_autonomous_factory **(era)** | Autonomous Factory Complex | T3 | in09 | 2,200 | 1,600 (RoboticsAutonomy) + 800 (FabricationMachines) | autonomous factory complexes (χ = 0.90, 05) | NASA 1980 AASM study (CP-2255) |
| in11_wafer_fab **(era)** | Wafer Fab | T3 | is16 + in09 | 2,500 | 1,200 (FabricationMachines) | off-Earth wafer fab — "Silicon Independence" milestone (05) | trailing-edge rad-hard fab (90–180 nm) |
| in12_mass_driver **(era)** | Mass Driver & Catcher | T3 | pw05 + in05 | 2,000 | 800 (FabricationMachines) | lunar mass driver (2.5 km/s muzzle; 1.45 kWh/kg per 05 §3.8), orbital catcher, regolith pelletizer | O'Neill & Kolm; NASA SP-428 |
| in13_truss_fabrication | In-Space Truss Fabrication | T3 | in06 | 1,200 | 700 (FabricationMachines) | trusselator robots (05): print structure on orbit | SpiderFab / Trusselator (NIAC) |
| in14_industry_seed `[SPEC]` | Self-Expanding Industry Seed | T4 | in10 + in11 | 9,000 | 3,500 (RoboticsAutonomy) | self-expanding industry seed (χ = 0.98, 05) | AASM self-replicating factory; Freitas |

### 2.6 Ships, Stations & Logistics (SH) — 10 nodes (hulls/ops in doc 06, freighters in 05)

| ID | Name | Tier | Prereqs | SCI | ED (family) | Unlocks | Description / anchor |
|---|---|---|---|---|---|---|---|
| sh00_crew_capsule_ops | Crew Capsule Operations | T0 | — | 0 | — | crew capsule, cargo capsule, PAD-1/PAD-2 | Dragon 2 / Soyuz / Starliner |
| sh01_station_modules | Station Modules | T1 | gn01 | 120 | 100 (PressureStructures) | rigid hab modules, docking nodes, PAD-3 | ISS USOS modules |
| sh02_inflatable_modules | Inflatable Modules | T1 | sh01 | 200 | 150 (PressureStructures) | inflatable habs (volume/mass ×3 vs rigid, 06) | BEAM; B330; Sierra LIFE |
| sh03_pallet_tug | Pallet Tug | T1 | gn01 + pr06 | 150 | — | Pallet tug (05 short-haul logistics) | space-tug studies; MEV docking |
| sh04_pelican_lift_loop | Pelican Lander Lift Loop | T2 | pr13 + is05 | 600 | — | Pelican reusable surface↔orbit lift loop (05) | lunar single-stage lander studies |
| sh05_drayage_sep | Drayage SEP Freighter | T2 | pr07 + gn05 | 650 | 300 (EPThrusters) | Drayage SEP freighter class (05) | Gateway PPE-derived cargo SEP |
| sh06_longhaul_ntr | Longhaul NTR Freighter | T2 | pr09 + in05 | 900 | — | Longhaul NTR freighter class (05) | Borowski NTR cargo architectures |
| sh07_cycler | Cycler Architecture | T3 | gn07 + hb06 | 1,300 | — | cycler habitats & schedule planner (01/06) | Aldrin Earth–Mars cycler (1985) |
| sh08_skyhook `[SPEC]` | Momentum-Exchange Skyhook | T4 | in12 + in13 | 6,500 | 2,000 (FabricationMachines) | rotating tether logistics nodes (suborbital catch, 05/06) | HASTOL (2000); MXER tether |
| sh09_interstellar_precursor `[SPEC]` | Interstellar Precursor Program | T4 | (pr21 \| pr22) + in14 | 12,000 | — | endgame megaproject blueprint: 500+ AU probe (12 victory chain) | TAU study 1987; JHU/APL Interstellar Probe 2021 |

### 2.7 Habitats & Bases (HB) — 9 nodes (modules in doc 07)

| ID | Name | Tier | Prereqs | SCI | ED (family) | Unlocks | Description / anchor |
|---|---|---|---|---|---|---|---|
| hb01_surface_hab_landers | Surface Habitat Landers | T1 | sh01 + gn02 | 300 | 200 (PressureStructures) | delivered surface hab modules, airlocks | Artemis surface habitat studies |
| hb02_regolith_shielding | Regolith Shielding | T2 | hb01 + is02 | 350 | — | berms, 2–3 t/m² overburden shielding (07/08 dose model) | GCR/SPE regolith shielding studies |
| hb03_regolith_printing | Regolith Construction Printing | T2 | hb02 + in07 | 600 | 350 (FabricationMachines) | printed/sintered structures, landing pads | ICON Project Olympus; ESA D-Shape |
| hb04_lava_tube_outfitting | Lava-Tube Outfitting | T3 | dsc03 + hb03 | 1,300 | — | lava-tube base sites: near-zero radiation, 290 K-stable interiors | Marius Hills skylight; Horvath 2022 |
| hb05_venus_aerostat_hab | Venus Aerostat Habitat | T3 | sh02 + gn04 + dsc08 | 2,000 | 500 (PressureStructures) + 400 (AeroFlight) | **crewed** aerostats at 50–54 km (60–107 kPa, 315–350 K; breathable-air lifting gas). Crewed tier stays T3 per DECISIONS A6 | NASA Langley HAVOC (2015) |
| hb06_spin_centrifuge | Spin-Gravity Centrifuge | T3 | sh01 | 900 | 400 (PressureStructures) | centrifuge sleep modules (partial-g countermeasure, 08) | Nautilus-X; Gemini 11 tether spin |
| hb07_titan_outpost | Titan Surface Outpost | T3 | pw04 + dsc13 | 1,500 | — | Titan base kit: 94 K / 146.7 kPa N2 environment systems (07) | NASA Glenn Titan studies; Huygens |
| hb09_mercury_terminator | Mercury Terminator Operations | T3 | vh04 + pw04 | 1,500 | 800 (SurfaceMobility) | HAB-16 Mercury Crawler Platform (07 §4.3.8), RVR-CRAWL drivetrain (NUK-KP10 ×3), Mercury Mass Driver Port site class — Act 4 optional | JPL terminator-rover studies; MESSENGER polar ice |
| hb08_rotating_settlement `[SPEC]` | Rotating Settlement | T4 | hb06 + in12 + is15 | 4,500 | 1,500 (PressureStructures) | large spin habitat (1 g rim, 100+ crew) — endgame megaproject | NASA Ames/Stanford Torus (1975) |

### 2.8 Life Support & Crew (LS) — 12 nodes (systems in doc 08)

| ID | Name | Tier | Prereqs | SCI | ED (family) | Unlocks | Description / anchor |
|---|---|---|---|---|---|---|---|
| ls00_open_loop | Open-Loop Life Support | T0 | — | 0 | — | LiOH scrubbers, stored O2/Water/FoodRations, basic IVA suits, VEG-1 salad rack (ECLSS-Bio T0 donor; morale only) | Apollo/Dragon ECLSS; ISS Veggie |
| ls01_regen_eclss | Regenerative ECLSS | T1 | ls00 | 200 | 150 (ECLSS-PhysChem) | CO2 sorbent beds, O2 electrolysis, Sabatier loop, water processor | ISS ECLSS 98% water recovery |
| ls02_crop_modules | Crop Production Modules | T1 | ls00 | 150 | 80 (ECLSS-Bio) | salad-crop racks (morale + trace food, 08) | ISS Veggie / Advanced Plant Habitat |
| ls03_surface_eva_suits | Surface EVA Suits | T1 | ls00 | 180 | 100 (PressureStructures) | dust-tolerant surface EVA suits | NASA xEMU / Axiom AxEMU |
| ls04_greenhouse | Greenhouse Food Production | T2 | ls02 | 500 | 300 (ECLSS-Bio) | LS-GARDEN EDEN-class racks: partial diet, η_food 0.25–0.50 (08 §3.3/§4.1) | EDEN ISS Antarctic greenhouse |
| ls05_radiation_planning | Radiation Protection Planning | T2 | ls01 | 400 | — | water-wall storm shelters, dosimetry & career-dose planner (08) | NASA exposure limits; SPE shelters |
| ls06_water_waste_loops | Advanced Water & Waste Loops | T2 | ls01 | 450 | 350 (ECLSS-PhysChem) | brine recovery, waste pyrolysis (08) | ISS Brine Processor Assembly |
| ls07_closed_loop_eclss **(era)** | Closed-Loop Bioregenerative ECLSS | T3 | ls04 + ls06 | 2,400 | 1,500 (ECLSS-Bio) | algae/bacteria/plant loop (LS-GREEN full-diet racks; HB-GRN module): ≥95% air/water, η_food 0.80→0.95 | MELiSSA; BIOS-3; Lunar Palace 365 |
| ls08_crew_health | Long-Duration Crew Health | T2 | ls01 | 350 | — | med bay, exercise countermeasures, psych-support systems (08) | ISS medical ops; ARED |
| ls09_gravity_biology_1 | Partial-Gravity Biology I — Centrifuge Studies | T2 | ls08 | 400 | 200 (ECLSS-Bio) | gravity-biology arc opener (08 §3.14 GENERATIONS, C19): small-animal centrifuge studies; first gravity-threshold data layer | Bion/Foton; ISS Rodent Research |
| ls10_gravity_biology_2 | Partial-Gravity Biology II — Mammalian Trials | T3 | ls09 + hb06 | 1,200 | 600 (ECLSS-Bio) | multi-generation mammalian reproduction trials in spin habitats; narrows g_repro threshold brackets (08 §3.14) | rodent multi-generation spin studies |
| ls11_reproduction_protocols `[SPEC]` | Human Reproduction Protocols | T4 | ls10 | 5,000 | — | [SPECULATIVE] human partial-g gestation/development protocols + spin-habitat prescriptions; satisfies Foundation Audit demographic pillar (12) | honest speculation — no human off-Earth data exists (C19) |

### 2.9 Vehicles (VH) — 11 nodes (chassis/craft in doc 10)

| ID | Name | Tier | Prereqs | SCI | ED (family) | Unlocks | Description / anchor |
|---|---|---|---|---|---|---|---|
| vh00_teleop_rovers | Teleoperated Rovers | T0 | — | 0 | — | robotic rover chassis, teleoperated sampling arm (task orders feed RoboticsAutonomy ED — T0 donor), instrument mounts | Curiosity / Perseverance class |
| vh01_open_rover | Crewed Unpressurized Rover | T1 | ls03 | 130 | 80 (SurfaceMobility) | open rover (2 crew + cargo) | Apollo LRV; Artemis LTV |
| vh02_robotic_haulers | Robotic Haulers | T1 | vh00 | 200 | 150 (SurfaceMobility) | dump/haul chassis for 04/05 logistics | autonomous haul trucks |
| vh03_ballistic_hoppers | Ballistic Hoppers | T1 | gn02 | 250 | — | propulsive hop vehicles (PSR access, anomaly reach) | IM Micro-Nova hopper |
| vh04_pressurized_rover | Pressurized Rover | T2 | vh01 + ls01 | 550 | 350 (SurfaceMobility) | pressurized rover (2–4 crew, 14-day sorties) | JAXA/Toyota Lunar Cruiser; NASA SEV |
| vh05_mars_rotorcraft | Mars Rotorcraft | T2 | gn04 | 480 | 200 (AeroFlight) | scout/courier rotorcraft for thin CO2 atmospheres | Ingenuity: 72 flights |
| vh09_venus_platforms | Venus Atmospheric Platforms | T2 | dsc08 + gn04 | 700 | 500 (AeroFlight) | **robotic** variable-altitude balloons, cloud-layer drones, helium-cell starter aerostats (07 §4.3.3) — T2 robotic tier per DECISIONS A6 (crewed hb05 stays T3); Act-4 timing held by dsc08 gate | Soviet VEGA balloons (1985); JPL VAB studies |
| vh06_titan_rotorcraft | Titan Rotorcraft | T3 | vh05 + sc03 | 1,300 | 600 (AeroFlight) | heavy Titan rotorcraft (dense N2, low g) | Dragonfly (launch 2028) |
| vh07_titan_submarine | Titan Submarine | T3 | dsc13 | 1,800 | 800 (AeroFlight) | submarine for Kraken/Ligeia Mare; sea-floor sampling | NASA Glenn COMPASS Titan Sub (NIAC) |
| vh08_cryobot | Ice-Penetrating Cryobot | T3 | dsc10 + pw04 | 2,200 | 800 (AeroFlight) | fission-heated melt probe (km-class ice shells) + ocean sampler | NASA SESAME; Honeybee SLUSH |
| vh10_venus_surface | Venus Surface Systems | T3 | dsc08 | 1,400 | 300 (Avionics) | long-duration surface stations (SiC electronics, 737 K / 9,200 kPa) | NASA Glenn LLISSE |

### 2.10 Science Instruments & Labs (SC) — 8 nodes (this system's own parts)

| ID | Name | Tier | Prereqs | SCI | ED (family) | Unlocks | Description / anchor |
|---|---|---|---|---|---|---|---|
| sc00_survey_instruments_1 | Survey Instruments I | T0 | — | 0 | — | camera, vis/IR spectrometer, magnetometer, radio science (50 kg pkg) | LRO instrument suite |
| sc01_sample_return_capsules | Sample Return Capsules | T1 | gn00 | 120 | — | SRC-46 (46 kg, 5 kg sample capacity, ballistic reentry) | Stardust / OSIRIS-REx SRC |
| sc02_field_laboratory | Field Laboratory | T1 | ls00 | 200 | — | GL-1 glovebox (0.4 t, ×0.55); FL-2 field lab (3.5 t, 2 kWe, ×0.70) | ISS MSG; MSL SAM |
| sc03_survey_instruments_2 | Survey Instruments II | T2 | sc00 | 350 | — | GPR, neutron spectrometer, gravimeter, lidar (120 kg pkg; feeds 04 K2 resource layer) | RIMFAX; LRO LEND |
| sc04_orbital_laboratory | Orbital Laboratory | T2 | sh01 + sc02 | 600 | — | OL-12 lab module (12 t, 6 kWe, ×0.90) | ISS Destiny/Columbus; MSR facility studies |
| sc05_observatories | Deep-Space Observatories | T2 | sc00 + gn03 | 700 | — | telescope platforms (0.2 SCI/day trickle; NEA/comet target catalog for 03) | NEO Surveyor |
| sc06_cryo_sample_chain | Cryogenic Sample Chain | T2 | sc01 | 400 | — | Cryo Sample Vault (0.8 t, 50 kg @ <150 K); SRC-300 (300 kg, 30 kg sample, lifting reentry) | MSR / lunar-PSR cryo-curation |
| sc07_astrobiology_suite | Astrobiology Suite | T3 | sc04 | 1,500 | — | life-detection instrument package; ×1.5 analysis value on dsc11/13/14 organics tranches (tranches 2–3 only) | Europa Lander SDT; MOMA |

**Survey package stats** (simulation-facing; the one-shot survey award key is the package-level class ID — exactly three classes; individual instruments never award separately):

| Class ID (award key) | Package | Mass | Power | Survey ceiling (periapsis must be below) |
|---|---|---|---|---|
| SC-00 | Survey Package I (camera, vis/IR spec, magnetometer, radio science) | 50 kg | 0.3 kWe | 5,000 km (global mapper) |
| SC-03 | Survey Package II (GPR, neutron spec, gravimeter, lidar) | 120 kg | 0.6 kWe | 200 km (high-res mapper) |
| SC-05 | Observatory Platform (telescope bus) | 1,500 kg | 2.0 kWe | 50,000 km (remote survey) + 0.2 SCI/day trickle |

---

## 3. CURRENCY MECHANICS

### 3.1 Science (SCI) — global spendable scalar

Sources (complete list):

| Source | Mechanic |
|---|---|
| Orbital/remote surveys | one-shot per (instrument class, region): `15 · X` SCI; 30 days instrument-on time below the class's survey ceiling (warpable). Upgraded classes re-survey the same regions once more at full value |
| Ground surveys | rover/crew traverse with survey package: one-shot `10 · X` SCI per region + resource-prospecting layer for 04 (K2) |
| Physical samples | pooled, diminishing returns, analysis-path multiplier (§3.3) |
| Anomalies | hand-placed POIs revealed by surveys; on-site investigation pays lump SCI at **2 SCI per GB** of the anomaly's SurveyData yield (30–400 SCI each, one-shot; the GB remain tradeable data — selling does not forfeit the SCI). Anomaly budget placeholder: 4–10 per major body |
| Discoveries | 18 hand-placed lump sums, often node-gating (§5) |
| Program milestones ("firsts") | formula lumps `k · X(body)` (§3.4) |
| Observation campaigns | 0.2 SCI/day per SC-05 platform, ×2 outside 1.1 AU or dust-free vantage; cap 4,000 SCI lifetime per platform AND **15,000 SCI program-wide** |
| Contracts (doc 12) | repeatable trickle, guaranteed ≥ 30 SCI/quarter equivalent (anti-softlock F-2); design cap **≤ 25% of act income** (open question Q4 proposal, DECISIONS E placeholder) |

**Regions:** doc 03 partitions every body into science regions (orbit-high, orbit-low, atmosphere bands, surface site classes). Each region has an exoticism factor X.

**Diminishing returns** — each (activity type, region) pair has a finite pool:

```
P = V_base(activity) · X(region)
S_n = 0.6 · R_(n-1),  R_0 = P,  R_n = R_(n-1) − S_n     closed form: S_n = 0.6 · 0.4^(n−1) · P
S_1 = 0.60P, S_2 = 0.24P, S_3 = 0.096P, ...  Σ → P
```

Award credited = `S_n · M_analysis`. Pool depletion counted at `S_n` (pre-multiplier) — so a thorough Earth-return program extracts up to `1.25·P` per region (deliberate). The seven sample activities in §3.3 are the **complete** set of pooled activity types; surveys/anomalies are one-shot; milestones are formula lumps.

**Spending:** SCI is destroyed on node unlock. No decay, no refund.

### 3.2 Exoticism table X (representative values; 03 owns per-region assignment — every milestone key must resolve to one number, never a range)

| Region class | X | Region class | X |
|---|---|---|---|
| Earth surface / LEO | 1 | Venus cloud layer (50–56 km) | 6 |
| Earth high orbit, cislunar | 1.5 | Comet nuclei | 7 |
| Moon nearside mare/highlands | 2 | Venus surface | 8 |
| Moon farside / polar / PSR | 4 | Jupiter system (Callisto/Ganymede) | 8 |
| NEAs (C/S-type) | 4 | Jupiter atmosphere (probe band) | 9 |
| Mars orbit / surface | 5 | Io, Europa | 10 |
| Phobos, Deimos, M-type NEA | 5 | Saturn atmosphere (probe band) | 10 |
| Main belt (Ceres, Vesta, M-types) | 6 | Saturn system (rings, icy moons) | 10 |
| | | Titan surface | 11 |
| | | Enceladus (south-polar terrain) | 12 |
| | | Europa sub-ice ocean, Titan sea floor | 14 |

### 3.3 Samples — types, analysis paths, sample return

**Sample types** (one item = one pool draw `S_n`; `V_base` is per-(activity, region) pool base, pre-X):

| Sample type | V_base (SCI) | Mass | Special handling | Acquired by |
|---|---|---|---|---|
| Atmosphere grab | 25 | 0.2 kg | gas bottle | any vehicle in atmosphere band |
| Regolith scoop | 40 | 0.5 kg | none | rover arm, crew EVA |
| Drill core | 60 | 2 kg/m, max 3 m | none | Core Drill (04) |
| Ice core | 90 | 5 kg | **cryo < 150 K** or decays | Thermal Ice Corer (04) |
| Deep core | 140 | 25 kg | none | Deep Core Rig (04, 10+ m) |
| Liquid grab (Titan seas, Europa melt) | 120 | 1 kg | **cryo < 150 K** or decays | Sea Pump, cryobot (10) |
| Plume flythrough capture | 70 | 0.05 kg | aerogel cassette | orbital flythrough ≤ 3 km/s relative |

**Cryo decay (exact):** `award = S_n · M_analysis · max(0.2, 1 − 0.02 · days_above_150K)` — linear, floored at 20% (mineralogy survives, F-4).

**Analysis paths** (sample consumed by analysis; one path per sample; pool depleted at `S_n` regardless of path):

| Path | M_analysis | Throughput / requirement |
|---|---|---|
| In-situ robotic instrument (transmit only) | 0.40 | instant on acquisition; needs comms path |
| Glovebox GL-1 (any crewed module) | 0.55 | 0.2 kg/day, 1 crew-h/kg |
| Field Lab FL-2 (surface module) | 0.70 | 1 kg/day, 2.0 kWe, 1 crew or A2 robot |
| Orbital Lab OL-12 (station module) | 0.90 | 3 kg/day, 6.0 kWe, 2 crew |
| Earth Receiving Laboratory | 1.25 | instant on recovery; unlimited |

**Sample return logistics:** Earth return needs physical transport — SRC-46 (46 kg, holds 5 kg, ballistic reentry), SRC-300 (T2: 300 kg, 30 kg capacity, lifting reentry), or any vehicle landing intact on Earth. Cryo samples additionally need a **Cryo Sample Vault** (0.8 t, 0.4 kWe, 50 kg @ <150 K) in the whole transport chain or they decay en route.

**Pool-depletion rule (load-bearing):** pool is depleted **on analysis award, not on acquisition**. Samples destroyed in transit return their `S_n` to the pool — no science silently lost to a failed reentry, only time (F-3). Consequence: `S_n` is assigned **at the moment of analysis, in analysis order**; the sample-manifest UI shows *projections* (value if analyzed next from its pool), not fixed tags.

### 3.4 Milestones ("firsts", per body) — lump `k · X(body surface class)`

| Milestone | k |
|---|---|
| First flyby | 10 |
| First orbit | 20 |
| First uncrewed landing (or atmosphere probe for gas giants/Venus deep) | 40 |
| First sample return to Earth | 60 |
| First crewed landing | 80 |
| First 30-day continuously crewed presence | 100 |

### 3.5 Engineering Data (ED) — per-family cumulative high-water mark

`D_f ≥ 0` per part family. **Never spent**; node ED costs are thresholds (`D_f ≥ cost`), and reliability curves read `D_f` directly.

**The 22 part families** (with T0 donors closing every first-of-family chain — audit rule F-15):

| # | Family | Accrues from (owning doc) |
|---|---|---|
| 1 | SolidMotors | SRM-2/49 burns (02) |
| 2 | StorableEngines | OMS-27, SPS-91, RCS-D400 (02) |
| 3 | KeroloxEngines | K-845, KV-981 (02) |
| 4 | HydroloxEngines | H-102, HL-67, H-2280 (02) |
| 5 | MethaloxEngines | M-2256, MV-2530, ML-24, RCS-M2K (02) |
| 6 | NTRCores | NTR-73, NTR-246, LANTR (02) |
| 7 | EPThrusters | ION/HALL/MPD/VAS strings; T0 donors ION-2 + HALL-1 (pr00) |
| 8 | CryoFluidMgmt | ZBO coolers, depots, couplers, cryo tanks incl. pr00's parametric tanks (T0 donor) |
| 9 | SolarPower | PV arrays, sails' power share (09) |
| 10 | EnergyStorage | batteries, fuel cells (09) |
| 11 | FissionSystems | RTGs, Kilopower, FSP, NEP reactors (09) |
| 12 | ThermalControl | radiators incl. pw00 baseline radiators (T0 donor), heat pumps, TES (09) |
| 13 | ECLSS-PhysChem | scrubbers, OGA, WPA, Sabatier-ECLSS (08) |
| 14 | ECLSS-Bio | crop modules, bioreactors; T0 donor VEG-1 salad rack (ls00) |
| 15 | PressureStructures | hab modules, inflatables, EVA suits (06/07) |
| 16 | ISRU-Chem | RX-01…RX-19 reactors (04) |
| 17 | MiningMachines | excavators, corers, beneficiation (04) |
| 18 | FabricationMachines | machine shop, WAAM, dry dock, wafer fab (05) |
| 19 | RoboticsAutonomy | arms, worker robots, autonomy levels (05); T0 donor vh00 teleop-arm task orders |
| 20 | SurfaceMobility | rover chassis, haulers, hoppers (10) |
| 21 | AeroFlight | aeroshells, chutes, rotorcraft, balloons, submarines/cryobots (10) |
| 22 | Avionics | GNC programs, comms, sensors (01/06) |

**Accrual rates** (`u` = duty fraction 0–1):

| Family class | Rate |
|---|---|
| Chemical/NTR engines (families 1–6) | 5 ED per successful ignition + 0.05 ED per second of burn |
| EPThrusters | 0.04 ED/h thrusting |
| Continuous machines (families 8–18 except 15) | 0.05 ED/h at u ≥ 0.5 (pro-rated `u·0.05` below) |
| PressureStructures | 0.01 ED/h while crewed and pressurized |
| RoboticsAutonomy | 0.03 ED/h active + 1 ED per completed task order |
| SurfaceMobility | 0.5 ED per km driven + 0.02 ED/h powered |
| AeroFlight | 25 ED per completed atmospheric-flight/EDL/dive event |
| Avionics | 2 ED per autopilot program execution, max 10 ED per vessel per SOI leg (cap resets at SOI transition) |

`u` for passive cryo hardware (tanks, depots) = 1 while containing cryogenic fluid, else 0 (this is how T0 parametric tanks feed CryoFluidMgmt before dedicated CFM hardware).

**Concurrency damping (anti-farm):** accrual aggregates per group `g = (part type, environment class)`:

```
dD_f/dt = Σ_g R_f · √N_g · M_env(f, class(g))      [continuous families]
N_g = active units of one part type in one environment class
```

For event-based accrual every event counts, but within each group units are ranked by commission timestamp and events from units ranked **5th or later pay ×0.5**.

**Novel-environment multiplier M_env:** first **200 operating hours** of a family in each new environment class accrue at **×3**; the same ×3 applies to event-based ED for events inside that 200-h window (e.g. EDL event during AeroFlight's first 200 h in a new class = 25×3 = 75 ED). Seven environment classes (tags from 03): LEO/microgravity, deep-space radiation, vacuum dusty surface, cryogenic surface (<120 K), dense atmosphere (>50 kPa), high-radiation (Jupiter belts), liquid immersion (Titan seas). Bound: ~4,200 bonus-hours per family max (F-10).

**Event bonuses:**
- **Investigated failure:** +25 ED (machines) / +40 ED (engines) per failure event, ONLY if telemetry was downlinked (comms path existed) or the unit is physically inspected by crew/robot within 30 days. Uninvestigated failures yield 0 (and still count against reliability). Creates the relay-coverage incentive (F-11).
- **Teardown:** physically returning a flown unit to a workshop or Earth: one-time +10% of that unit's lifetime ED contribution.
- **Test stand / burn-in:** ground/base test facilities (Earth pad has one free) accrue ED at full rate while consuming real propellant/power/funds.

**Cap formula** (per family; "DATA SATURATED" in UI when hit):

```
C_f = max( 1.5 · max(ED thresholds among VISIBLE nodes naming family f; 0 if none),
           6 · D_half(f) )
```

Researching/revealing new nodes raises `C_f` and accrual resumes. The `6·D_half` floor guarantees every family — including ones named by no threshold anywhere (SolidMotors) — can mature to `m ≈ 1.047 ≤ 1.05` (F-7). Reliability curves keep reading the capped `D_f`.

---

## 4. PROTOTYPING & RELIABILITY MATURATION

### 4.1 Part-type states

`PROTOTYPE → FLIGHT → MATURE` (per part **type**, program-wide).

**Prototype (first article) rules:**
- Resource build cost **×3**, fabrication hours **×2** (applied in 05's fab model / 06's build pipeline).
- Reliability state multiplier `m_state = 4` until the type completes one **full-duration success**:

| Part category | Full-duration success (clears PROTOTYPE) |
|---|---|
| Engines (families 1–7) | one rated-duration burn (test stand or flight) |
| Continuous machines (families 8–18) | 500 h at ≥ 50% duty |
| Pressure structures | 30 d pressurized hold |
| Rovers / haulers | 10 km traverse |
| Hoppers | one complete hop cycle (ascent–translation–landing) |
| Rotorcraft | one flight ≥ 30 min |
| Balloons / aerostats | 72 h afloat |
| Submarines / cryobots | one complete dive/descent-and-return cycle |
| Landers / aeroshells | one EDL event |

- Categories with no meaningful operating duration — science instruments, solar sails, SRCs, GNC software — **skip PROTOTYPE** and enter FLIGHT on unlock (still pay ×3/×2 first-article build costs where physical).
- After success: FLIGHT state (`m_state = 1`), subsequent units at normal cost.
- A prototype that fails catastrophically must be replaced (another ×3-cost article), but the investigated-failure ED bonus applies.
- **Parallel prototypes (F-6):** only the first article pays ×3; units 2..n built before type success pay **×1.5** and all carry `m_state = 4` until the type's first full-duration success.

### 4.2 Maturation curve

Catalog failure rates in 02/05/08/09 are **mature floors** (λ_min, p_min). Live rate for a type in family f:

```
λ(D_f) = λ_min · m(D_f) · m_state · m_unit
m(D_f) = 1 + 3 · 2^(−D_f / D_half)        [type-maturity multiplier, 4 → 1]
```

- `m_unit` = per-individual-unit infant mortality: **×2.5 for a unit's first 50 operating hours or first 3 ignitions** (test-stand burn-in clears it safely), else 1.
- **One wear model (DECISIONS A5, binding):** 02's per-ignition/wear base (`1 + 9w²`) × this system's maturity stack `m(D_f)·m_state·m_unit` × 05's spares/MTBF consumption are **orthogonal multipliers — no double counting anywhere**. Ships as an interface test in Phase 1.

**D_half per family (ED):**

| Families | D_half |
|---|---|
| Avionics | 100 |
| SolidMotors, StorableEngines, SurfaceMobility, PressureStructures, SolarPower, EnergyStorage | 150 |
| Kerolox/Hydrolox/Methalox engines, MiningMachines, ThermalControl | 200 |
| EPThrusters, CryoFluidMgmt, ECLSS-PhysChem, FabricationMachines | 250 |
| NTRCores, ISRU-Chem, RoboticsAutonomy, AeroFlight | 300 |
| FissionSystems, ECLSS-Bio | 400 |

**Worked examples (acceptance tests — a programmer must reproduce these numbers):**

1. *Pump-fed engine* (mature p_ign = 0.0005). FLIGHT-state type, `D_f = 0`, unit past burn-in: `p = 0.0005·m(0) = 0.0005·4 = 0.002` (matches 02 §3.14 "new type" row). After ≈ 25 program ignitions (≈ 25·(5 + 0.05·400 s) ≈ **625 ED**, D_half 200): `m = 1 + 3·2^(−3.1) = 1.35`, `p = 0.00068`. **"Mature" badge at D_f ≥ 600** — 02's "mature after 25 ignitions" rule is formally this badge (DECISIONS E placeholder, [PLAYTEST]).
2. *ECLSS-PhysChem unit*, catalog MTBF 5,000 h (λ_min = 0.2/1000 h): first article in PROTOTYPE past unit burn-in: `0.2·4·4 = 3.2 failures/1000 h` (early-CDRA experience); at `D_f = 500` (D_half 250): `m = 1.75`, λ = 0.35/1000 h in FLIGHT.
3. *NTR core* (p_base = 0.003 mature): first-article rated ignition in PROTOTYPE after test-stand burn-in: `0.003·4·4 = 4.8%`/ignition. Skipping burn-in adds `m_unit = 2.5`: `0.003·4·4·2.5 = 12%`.

**Maturity perks (per family at D_f milestones):**

| Milestone | Perk |
|---|---|
| `D_f ≥ 600` "Mature" | refurbishment cost −25% (02/05); badge in builder |
| `D_f ≥ 2,000` "Refined" | MachineParts upkeep −20% (05); ISRU/ECLSS throughput +2% |
| `D_f ≥ 5,000` "Optimized" | newly built units: dry mass −5% (build-time flag to 02/06, **never retroactive**) |

### 4.3 Test & UI workflow (prototyping UX)

- Builder flags first articles with amber PROTOTYPE badge + projected first-failure probability for the planned mission profile (integrate `λ_min·m·m_state·m_unit` over profile).
- Test Stand UI: select part type → run rated-duration test → consumes propellant/power/funds, accrues ED, clears `m_state` on success, clears `m_unit` burn-in for that unit. "Qualification campaign" macro queues N tests and reports resulting `m(D_f)`.
- ED dashboard per family: `D_f / C_f` bar, current `m(D_f)` ("×1.35 failure rate"), accrual breakdown (√N damping, M_env active), DATA SATURATED flag, failure ledger (investigated vs lost, forfeited ED in red).
- Part-type cards show state badges: PROTOTYPE (amber, ×3 cost / ×4 failure) / FLIGHT / MATURE (≥600) / REFINED / OPTIMIZED.
- Transparency rule: every node tooltip shows actual formula values — current `m(D_f)`, exact discount arithmetic, gating Discovery. No hidden math.
- Alerts owned by this system: DATA SATURATED, PROTOTYPE FAILURE, FAILURE NOT INVESTIGATED (30-day timer), SAMPLE THERMAL DECAY, DISCOVERY ACQUIRED, MILESTONE ACHIEVED, NODE AFFORDABLE (opt-in).

---

## 5. THE 18 DISCOVERIES (DSC) — location-gated, one-time

Discoveries are tied to physical presence. Each grants its lump SCI immediately (no analysis multiplier) and permanently satisfies prerequisites / applies discounts. Discoveries have **no tier locks** — sequence-breaking is legal and rewarded (F-8); T4 visibility still requires an in-category T3 node.

**Staged biology payouts (exception):** dsc11, dsc13, dsc14 pay in three tranches keyed to their analysis chain: **40% on acquisition** (node gates release immediately here), **30% on SC-07 suite analysis** of retained material, **30% on Earth-return verdict** (SRC-300 + Cryo Sample Vault chain). SC-07's ×1.5 organics bonus applies to **tranches 2–3 only** → max total = listed × (0.4 + 1.5·0.6) = **listed × 1.3** (e.g. dsc11 up to 3,250 SCI).

| ID | Discovery | Where / trigger | SCI | Gates / discounts |
|---|---|---|---|---|
| dsc01 | Lunar PSR Ice Ground Truth | ≥ 1 m ice core inside a PSR site (Thermal Ice Corer) | 300 | gates is05; −20% is03 |
| dsc02 | Mare Volatile Assay | deep cores + Volatile Oven assay at **3 distinct mare sites** | 400 | gates is20; reveals He3/volatile ppb map layer (03) |
| dsc03 | Lava-Tube Interior Survey | hopper/rover descends a skylight anomaly with lidar | 350 | gates hb04; −15% hb03 |
| dsc04 | Mars Environment Characterization | 90 sols of surface meteorology + dust data from one station | 300 | gates is06; −20% vh05 |
| dsc05 | Mars Subsurface Ice & Brines | GPR survey + 10 m core, mid-latitude site | 500 | gates Mars water chain sites (04); −15% hb03 at Mars |
| dsc06 | Phobos/Deimos Regolith | lander + returned or lab-analyzed sample | 350 | −20% sh04; Phobos depot site survey (06) |
| dsc07 | Comet Nucleus Sample | rendezvous + sample from an active comet | 600 | −30% is10 |
| dsc08 | Venus Cloud-Layer Chemistry | 30 days of balloon/probe data at 50–56 km | 600 | gates hb05, vh09, vh10, is18 |
| dsc09 | Venus Surface Mineralogy | surface station surviving ≥ 60 min (or LLISSE-class 60 d) | 700 | −25% vh10 |
| dsc10 | Europa Plume & Exosphere Volatiles | low-orbit flythrough capture ≤ 3 km/s | 800 | gates vh08 |
| dsc11 | Europa Ocean Water | cryobot reaches sub-ice ocean; melt sample analyzed | 2,500 (staged 40/30/30) | "ambiguous organics" arc I; campaign codex |
| dsc12 | Enceladus Plume Sampling | south-polar plume flythrough capture | 900 | −30% vh08; hydrothermal H2/silica codex |
| dsc13 | Titan Lake Composition | lake-surface sample (lander or vh06 rotorcraft) | 800 (staged 40/30/30) | gates vh07, is19, hb07 |
| dsc14 | Titan Sea Floor Survey | vh07 submarine sonar map + sediment sample | 1,200 (staged 40/30/30) | "ambiguous organics" arc II |
| dsc15 | C-Type NEA Assay | rendezvous + **3 samples** from one C-type NEA | 350 | gates is10 |
| dsc16 | M-Type Metal Assay | rendezvous + sample from an M-type body | 450 | gates is14 |
| dsc17 | Jovian Radiation Survey | orbiter dosimetry across ≥ 4 Jupiter-system orbits | 500 | gates crewed Jupiter-system ops (08 dose planner); −20% vh08 |
| dsc18 | Saturn Atmosphere Probe | entry probe telemetry to ≥ 1,000 kPa (10 bar) depth | 700 | gates is21 |

Total Discovery SCI ≈ 12,300 (at listed values).

**Hard content rules:** dsc11/13/14 return *chemistry, never organisms* — chiral excess at 2σ, methane disequilibria with viable abiotic pathways, lipid-like vesicles of uncertain origin. Earth verdict stays scientifically open. Every organics codex entry ships with the abiotic counter-hypothesis (F-14; DECISIONS F34 reaffirms: no aliens, ever). Discovery codex UI: acquired entries get real-science write-ups; pending ones show "what would it take" requirement text.

**Open question (Q5):** dsc02 needs 3 mare sites — proposal is 25% SCI per site, gate releases at 3 (not yet ratified).

---

## 6. FAILURE MODES & EDGE CASES (implementation-binding)

| # | Case | Rule |
|---|---|---|
| F-1 | ED grinding (pad-fire forever) | √N damping + real test-stand propellant/funds cost + per-family cap C_f; UI says DATA SATURATED |
| F-2 | Science soft-lock | pools never expire; contracts guarantee ≥ 30 SCI/quarter; milestones on any new body always available; no node refundable but no node load-bearing AND missable |
| F-3 | Samples lost in transit | pool depletes at analysis award, not acquisition; destroyed samples return `S_n` to pool |
| F-4 | Cryo decay to zero | floor at 20% of `S_n` |
| F-5 | Prototype death spiral | investigated failures pay +25/+40 ED → lowers `m(D_f)` for next article; spiral converges by construction |
| F-6 | Parallel prototypes | first article ×3; units 2..n before type success ×1.5; all carry `m_state = 4` until first success |
| F-7 | Family cap after tree completion | unconditional `6·D_half` floor in C_f; every family matures to `m ≤ 1.05` |
| F-8 | Sequence breaking | legal — Discoveries have no tier locks; T4 visibility still needs in-category T3 |
| F-9 | Skipping optional worlds | victory path needs only Earth–Moon–Mars–belt; optional gates lock only nodes useless without being there |
| F-10 | M_env hopping | bonus per (family, env class), 200 h each, 7 classes — bounded ~4,200 bonus-hours/family |
| F-11 | Failure with no comms | no ED bonus; wreck inspection within 30 days recovers it (relay incentive) |
| F-12 | Region redefinition across saves | pools keyed by stable region IDs; orphans keep depleted state; node IDs stable strings |
| F-13 | Discount stacking | multiplicative, `cost = base·Π(1−d_i)`, clamp ≥ 0.4·base |
| F-14 | Biology misread as aliens | abiotic counter-hypothesis in same codex entry; marketing may not promise life |
| F-15 | ED threshold orphan | lint rule: every threshold's family must be accruable from parts unlocked by a T0 start node or by one of the node's own prereqs (donor-family pattern: pr09 names HydroloxEngines not NTRCores; pr10/11/12's NTRCores accrue from NTR-73 via common prereq pr09). Build-time content lint |

**Open questions still unratified (doc §9):** research calendar time at R&D facility for T3/T4 (Q1); scientist crew multiplying M_analysis capped +0.1 (Q2, owned by 08); contract share ≤25% (Q4); partial discovery credit (Q5); difficulty scales SCI costs ×0.7/×1.0/×1.3, never λ floors (Q6); anomaly density 4–10/body (Q7); Optimized −5% dry-mass serialization round-trip (Q8); He3 logistics reality check (Q9); era-node pacing, candidate promote pw04 (Q10).

---

## 7. GAP ANALYSIS — design vs current code

### 7.1 Tree content: 13 nodes exist, 132 specified

Current `data/core/tech/*.toml` (13 files) vs this spec:

| Existing node id | Closest spec node | Conflicts |
|---|---|---|
| `core:tech_cryo_depots` (NOTE: lives in **era_defining.toml** — filename/content mismatch) | pr04 (150 SCI matches) / pr05 | spec splits CFM (pr04) from depot ops (pr05, era); ED must become CryoFluidMgmt threshold |
| `core:tech_fission_100kwe` (400/250) | pw04 Kilopower (450/200) by cost; **name says 100 kWe = pw05** (800/500) | split into pw04 + pw05 (era) |
| `core:tech_ntr` (1200/600, prereqs cryo+fission) | pr09 (700 SCI; 500 HydroloxEngines + 300 FissionSystems; prereqs pr04+pw04) | cost too high; ED must be two family thresholds; unlock id `engine_ntr_k2` vs spec NTR-73 |
| `core:tech_isru_large` (500/400) | is05 Polar Ice Mining (550/300, era) | missing dsc01 gate and the entire is00–is04 chain below it |
| `core:tech_closed_loop_eclss` (2400/1500) | ls07 (2,400 / 1,500 ECLSS-Bio) — **costs match exactly** | prereq wrong: spec ls04+ls06, code says isru_large; era flag missing |
| `core:tech_wafer_fab` (2000/1500) | in11 (2,500 / 1,200 FabricationMachines) | prereqs should be is16+in09 |
| `core:tech_autonomous_factories` (1500/1800, prereq wafer_fab) | in10 (2,200 / 1,600 RA + 800 FM, prereq in09) | dependency inverted vs spec (in10 and in11 are siblings under in09) |
| `core:tech_aerostat_ops` (T2, 1100/800) | must become **two nodes** per DECISIONS A6: vh09 robotic T2 (700) + hb05 crewed T3 (2,000) | both gated by dsc08 |
| `core:tech_titan_ops` (1200/900) | hb07 Titan Surface Outpost (1,500, no ED, gated dsc13+pw04) | |
| `core:tech_transit_habs` (350/250) | no direct spec node — nearest sh01/sh02/hb06 | non-canonical; retire or remap |
| `core:tech_deep_habs` (900/700) | no direct spec node — nearest sh07/hb08 | non-canonical; retire or remap |
| `core:tech_fusion_torch` (6000/5000) | pr22 (9,000 / 3,000 FissionSystems, prereq pw12) | cost/prereqs wrong; era flag missing |
| `core:tech_precursor` (6000/5000) | sh09 (12,000, **no ED**, prereq (pr21\|pr22)+in14) | cost/prereqs wrong |

**Whole branches with zero coverage:** GN (8 nodes), PW T0–T1/T3 (pw00–pw03, pw06–pw11), IS T0–T2/T3 (21 of 23), SC (all 8), VH (all 11), LS (10 of 12), HB (7 of 9), SH (8 of 10), most of PR (20 of 23), most of IN (12 of 15). All 9 T0 start nodes missing.

### 7.2 Mechanics gaps in `aphelion/sim/research.py`

1. **ED is wrong in kind:** code holds one global `eng_data` scalar and **spends** it (`self.eng_data -= cost_ed`). Spec: ED is a **per-family (22 families) cumulative high-water mark, threshold-checked and never spent**. This changes `ResearchState` shape, `can_unlock`, `unlock`, and the save schema.
2. **No ED accrual sources:** no per-family rates, no ignition/burn-second events, no √N concurrency damping, no M_env ×3 novel-environment bonus, no investigated-failure/teardown/test-stand bonuses, no cap `C_f` / DATA SATURATED.
3. **No SCI sources:** no surveys (15·X / 10·X), no sample pools with `S_n = 0.6·0.4^(n−1)·P` diminishing returns, no analysis paths (M_analysis 0.40–1.25), no cryo decay, no milestones (k·X), no anomaly 2 SCI/GB conversion, no observation-campaign trickle/caps, no contract share cap.
4. **No Discoveries:** no DSC entities, no discovery prereqs on nodes, no discounts (multiplicative, ≥0.4·base floor), no staged 40/30/30 biology tranches.
5. **No sample-return chain:** no sample items, SRC-46/SRC-300 parts, Cryo Sample Vault, pool-refund-on-loss rule, analysis-order S_n assignment.
6. **No prototyping/maturation:** no part-type states (PROTOTYPE/FLIGHT/MATURE), no ×3/×2 first-article costs, no `m(D_f) = 1 + 3·2^(−D/D_half)` curve, no `m_state`/`m_unit`, no D_half table, no maturity perks (−25% refurb / −20% upkeep / −5% dry mass), no A5 interface test.
7. **No prereq grammar:** code requires ALL prereqs; spec needs OR groups (`pr21 | pr22`, `is05 | is10`, `pr06 | pr07`) with `|` binding tighter than `+`.
8. **No visibility/fog:** all nodes visible; spec needs distance-1 reveal, discovery reveal, T4-behind-in-category-T3, "???" silhouettes, [SPECULATIVE] watermark + honesty notes.
9. **Node schema too thin:** TOML needs added fields: `category`, `era` flag, `speculative` flag, `ed_thresholds = [{family, value}, ...]` (replacing scalar `cost_ed`), `discovery_prereqs`, `discounts = [{source, frac}]`, anchor/tooltip text, OR-group prereq encoding.
10. **No warp integration:** ED accrual / trickle / sample decay must integrate analytically under time warp with threshold-crossing events (no per-tick iteration).
11. **Unlock-id drift:** existing `unlocks` ids (`core:engine_ntr_k2`, `core:engine_ml111`, `core:engine_torch_d1`, `core:hab_castor`, `core:hab_pollux`, `core:gondola_havoc`, `core:probe_longshot`) do not match the 02/04/05-doc part ids the spec references (NTR-73, ML-24, DFD-5, …) — needs a reconciliation pass when 02's catalog extract lands.
12. **No milestone/region/exoticism data:** needs 03's region partition + X assignments as content-pack data before SCI sources can be computed.

### 7.3 Suggested build order

1. Content: regenerate `data/core/tech/` from §2 (132 TOML files or one tech.toml per branch), with the new schema; keep a save-migration map from the 13 legacy ids.
2. `ResearchState` rework: per-family ED dict, threshold checks, visibility, OR-prereqs, discoveries, discounts.
3. ED accrual pipeline (telemetry events from sim systems → family accrual with damping/M_env/caps).
4. Prototyping/maturation stack + A5 orthogonality interface test (Phase 1 requirement).
5. SCI sources: surveys/milestones first (cheap, immediately makes research *playable*), then sample pools + analysis paths + SRCs, then Discoveries + anomalies.
6. R&D screen (10 columns × 5 tier rows, fog, tooltips with real numbers) + ED dashboard + sample manifest + codex.
