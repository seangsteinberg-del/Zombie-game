# 11 — Research & Technology Tree

Domain doc for PROJECT "APHELION". Owns: research currencies (Science, Engineering Data), the T0–T4 tech tree (all node definitions, costs, prerequisites), the prototyping / reliability-maturation model, location-gated Discoveries, and sample-return science mechanics.

Sibling docs: 01-orbital-mechanics.md, 02-propulsion.md, 03-solar-system.md, 04-resources-isru.md, 05-industry-logistics.md, 06-ships-stations.md, 07-bases-habitats.md, 08-life-support-crew.md, 09-power-thermal.md, 10-vehicles.md, 12-gameplay-economy-ui.md, 13-architecture.md.

---

## 1. Overview

Research in APHELION is not a meter you fill by waiting. It is the formalization of two real engineering truths:

1. **You learn where you go.** Knowledge of the solar system — where the ice is, what Venus's clouds are made of, whether Europa's ocean is habitable — only comes from sending instruments and bringing samples home. This produces **Science (SCI)**, the spendable currency that unlocks tree nodes.
2. **You learn by flying.** Hardware gets reliable by accumulating operating hours, ignitions, and investigated failures — the way the RL10 became trustworthy over six decades and the way SpaceX matured Falcon 9 through flight rate. This produces **Engineering Data (ED)**, a per-part-family experience track that (a) drives reliability maturation curves and (b) gates higher-tier nodes as thresholds.

The tree itself is the campaign's skeleton. Tiers T0–T4 (locked by conventions) map onto Acts 1–5: T0 is the 2049 baseline (everything that has actually flown), T1 is flight-proven derivatives (large methalox reuse, cryo depots), T2 is studied-and-credible (NTR, fission surface power, large ISRU), T3 is lab-demonstrated concepts (closed bioregenerative loops, MW-class electric propulsion, mass drivers, the Titan submarine), and T4 is the honestly-tagged `[SPECULATIVE]` endgame (fusion torch, He3, skyhook, interstellar precursor).

Design pillars of this document:

- **132 named nodes** across 10 categories, each with explicit Science cost, ED threshold (naming the donor part family), prerequisites, unlock list, and a real-world anchor.
- **No stat-bump filler.** Roughly one node in twelve is *era-defining*: it changes what kind of game you are playing (§4.12). The rest unlock concrete parts and processes defined in sibling docs.
- **Prototyping hurts.** The first article of any new part type costs ×3 resources, builds at half speed, and fails 4× more often until it survives one full-duration operation. Maturity is earned, not bought.
- **Exploration is mandatory, not flavor.** Eighteen location-gated Discoveries (§4.11) are hard prerequisites or large discounts for key nodes. You cannot research polar ice mining from an armchair in LEO.
- **No combat tech, no aliens.** The Titan and Europa "biology question" content resolves to chemically ambiguous organics — scientifically honest, narratively open (§4.11, §8).

---

## 2. Real-World Grounding

**Tier ladder = TRL discipline.** The T0–T4 ladder is a coarse-grained NASA Technology Readiness Level scale (TRL 1–9, NASA NPR 7123.1): T0 ≈ TRL 9 (flown, operational), T1 ≈ TRL 6–8 (flight-proven derivatives; e.g. large methalox reuse — SpaceX Raptor/Starship; cryogenic depots — ULA depot studies, NASA eCryo/CFM flight experiments), T2 ≈ TRL 4–6 (NTR — NERVA XE' ground-tested 1969 at 246 kN, DARPA/NASA DRACO program; Kilopower — KRUSTY 1-kWe nuclear test, March 2018), T3 ≈ TRL 2–4 (VASIMR VX-200 200 kW lab firings; MELiSSA closed-loop pilot; Titan Submarine NASA Glenn COMPASS/NIAC study), T4 = physics-sound but beyond engineering-complete, tagged `[SPECULATIVE]` (Princeton Direct Fusion Drive, Project Daedalus 1978, lunar He3 per Wittenberg/Kulcinski/Schmitt, HASTOL skyhook study 2000).

**Science from exploration.** The currency models the real information economics of planetary science. In-situ instruments return a fraction of what Earth laboratories extract: MSL's SAM instrument (~40 kg) performs a subset of the analyses a terrestrial lab runs on returned material, which is why Mars Sample Return was planned at all, and why 382 kg of Apollo samples and OSIRIS-REx's 121.6 g are still producing papers decades later. Hence the analysis-path multipliers in §3.6 (in-situ transmit 0.40 → Earth-return 1.25). Diminishing returns per repeated activity model real survey saturation: the 10th scoop from the same mare teaches less than the 1st.

**Engineering Data from operations.** Reliability growth through accumulated test/operating time is standard aerospace practice, formalized in the Duane postulate (1964) and the Crow-AMSAA model (MIL-HDBK-189): cumulative failure rate falls as a power law of cumulative operating time, with growth driven by *investigated and corrected* failures. The game's exponential-decay maturation curve (§3.4) is a save-file-friendly approximation of Crow-AMSAA with the same qualitative shape: steep early learning, long tail. Historical anchors: the F-1 engine's combustion-instability campaign consumed years of full-scale hot-fire testing before Saturn V flew; RL10 (in service since 1963, hundreds of flight units) is the canonical "mature engine"; Falcon 9 Block 5 demonstrated reliability-through-flight-rate; conversely every *first article* — N1, early Ariane 5, Starship prototypes — shows the infant-mortality spike the prototype rules model.

**Location-gated knowledge.** Every Discovery in §4.11 corresponds to a real measurement gap that real missions exist(ed) to close: LCROSS measured 5.6 ± 2.9 wt% water in the Cabeus PSR ejecta plume (2009) — ground truth from orbit only, hence the ice-coring requirement; MOXIE made 122 g of O2 on Mars (2021–23) before anyone would commit to ISRU-dependent architectures; Cassini flew through Enceladus's plume and found H2 (2017, hydrothermal indicator); Huygens and Cassini radar established Titan's methane/ethane lakes; Europa Clipper (launched 2024) exists because ocean composition is unknown. The "ambiguous organics" narrative thread follows the real epistemics of biosignature science (Viking LR ambiguity, ALH84001): detection of complex organics is *never* self-evidently biology.

**Sample-return scale.** Capsule and sample masses anchor to flown hardware: Stardust SRC 46 kg, OSIRIS-REx SRC 46 kg / 121.6 g of regolith, Hayabusa2 5.4 g, Apollo 382 kg total across six landings, planned MSR ~30 tubes at ~10–15 g each. Cryogenic sample integrity (ice cores must stay < 150 K) reflects real MSR/lunar-PSR curation studies.

**Honest 2D caveat.** Nothing in this tree models inclination or plane-change technology — the 2D planar patched-conic decision (01) removes that entire real-world problem class. Survey coverage that in reality depends on orbital inclination (polar mapping orbits) is abstracted as instrument-time in any orbit below the survey altitude ceiling (§3.5).

---

## 3. Game Model

All formulas use SI units; time in hours (h) or days (d) as marked. All RNG draws come from the deterministic mission seed (13-architecture.md).

### 3.1 Science (SCI) — definition and accrual

Science is a single global spendable scalar (unit: points, displayed "SCI"). Sources:

| Source | Mechanic | Section |
|---|---|---|
| Orbital/remote surveys | one-shot per (instrument class, region) | §3.5 |
| Physical samples | pooled, diminishing returns, analysis-path multiplier | §3.6 |
| Anomalies & Discoveries | hand-placed lump sums, often node-gating | §4.11 |
| Program milestones ("firsts") | formula-driven lump sums | §3.7 |
| Long-term observation campaigns | trickle from telescope/monitoring platforms | §3.5 |

**Regions.** 03-solar-system.md partitions every body into *science regions* (orbit-high, orbit-low, atmosphere bands, and surface site classes: mare, highlands, polar PSR, etc.). Each region carries an **exoticism factor X** (§3.7 table) scaling all Science earned there.

**Diminishing returns (samples and repeatable surface activities).** Each (activity type, region) pair has a finite pool:

```
P = V_base(activity) · X(region)          [SCI, the pool; V_base per activity type — table in §3.6]
yield of n-th performance:  S_n = 0.6 · R_(n-1)        R_0 = P
remaining pool:             R_n = R_(n-1) − S_n        (closed form: S_n = 0.6 · 0.4^(n−1) · P)
⇒ S_1 = 0.60·P,  S_2 = 0.24·P,  S_3 = 0.096·P, ...   Σ S_n → P
```

The closed form is what §5.5's analytic-warp requirement integrates. The seven sample activities in §3.6 are the **complete** set of pooled (diminishing-returns) activity types; surveys and anomalies (§3.5) are one-shot awards, milestones are formula lumps (§3.7).

The award actually credited is `S_n · M_analysis` (analysis-path multiplier, §3.6). Pool depletion is counted at `S_n` (pre-multiplier), so a thorough Earth-return program can extract up to `1.25·P` from a region — deliberate reward for doing science properly.

**Spending.** Science is spent (destroyed) on node unlocks. There is no Science decay and no refund.

### 3.2 Engineering Data (ED) — definition, accrual, caps

ED is tracked **per part family** as a cumulative high-water mark `D_f ≥ 0` (unit: ED points). It is never spent; node "ED costs" are *thresholds* (`D_f ≥ cost` required), and reliability curves read `D_f` directly. The 22 part families:

| # | Family | Accrues from (examples; owning doc) |
|---|---|---|
| 1 | SolidMotors | SRM-2/49 burns (02) |
| 2 | StorableEngines | OMS-27, SPS-91, RCS-D400 (02) |
| 3 | KeroloxEngines | K-845, KV-981 (02) |
| 4 | HydroloxEngines | H-102, HL-67, H-2280 (02) |
| 5 | MethaloxEngines | M-2256, MV-2530, ML-24, RCS-M2K (02) |
| 6 | NTRCores | NTR-73, NTR-246, LANTR (02) |
| 7 | EPThrusters | ION/HALL/MPD/VAS strings; T0 donors: ION-2 + HALL-1 stationkeeping thrusters (PR-00, 02) |
| 8 | CryoFluidMgmt | ZBO coolers, depots, couplers, cryo tanks incl. PR-00's T0 parametric tanks (02) |
| 9 | SolarPower | PV arrays, sails' power share (09) |
| 10 | EnergyStorage | batteries, fuel cells (09) |
| 11 | FissionSystems | RTGs, Kilopower, FSP, NEP reactors (09) |
| 12 | ThermalControl | radiators incl. PW-00's T0 baseline body-mounted radiators, heat pumps, TES (09) |
| 13 | ECLSS-PhysChem | scrubbers, OGA, WPA, Sabatier-ECLSS (08) |
| 14 | ECLSS-Bio | crop modules, bioreactors; T0 donor: VEG-1 salad rack (LS-00, 08) |
| 15 | PressureStructures | hab modules, inflatables, EVA suits (06/07) |
| 16 | ISRU-Chem | RX-01…RX-19 reactors (04) |
| 17 | MiningMachines | excavators, corers, beneficiation (04) |
| 18 | FabricationMachines | machine shop, WAAM, dry dock, wafer fab (05) |
| 19 | RoboticsAutonomy | arms, worker robots, autonomy levels (05); T0 donor: VH-00 teleoperated-rover arm task orders (10) |
| 20 | SurfaceMobility | rover chassis, haulers, hoppers (10) |
| 21 | AeroFlight | aeroshells, chutes, rotorcraft, balloons, submarines/cryobots (10) |
| 22 | Avionics | GNC programs, comms, sensors (01/06) |

**Accrual rates** (per operating unit; `u` = duty fraction 0–1):

| Family class | Rate |
|---|---|
| Chemical/NTR engines (1–6) | 5 ED per successful ignition + 0.05 ED per second of burn |
| EPThrusters | 0.04 ED/h thrusting |
| Continuous machines (8–18 except 15) | 0.05 ED/h at u ≥ 0.5 (pro-rated `u·0.05` below) |
| PressureStructures | 0.01 ED/h while crewed and pressurized |
| RoboticsAutonomy | 0.03 ED/h active + 1 ED per completed task order (05 task queue) |
| SurfaceMobility | 0.5 ED per km driven + 0.02 ED/h powered |
| AeroFlight | 25 ED per completed atmospheric-flight/EDL/dive event |
| Avionics | 2 ED per autopilot program execution, max 10 ED per vessel per SOI leg (cap resets at each SOI transition; SOI events owned by 01-orbital-mechanics.md) |

`u` for passive cryo hardware (tanks, depots) is defined as 1 while the unit contains cryogenic fluid, 0 otherwise — this is how PR-00's T0 parametric tanks feed CryoFluidMgmt ED before any dedicated CFM hardware exists.

**Concurrency damping (anti-farm).** Accrual aggregates per group `g = (part type, environment class)`: "identical units" means *same part type*, and each environment class is damped and multiplied separately:

```
dD_f/dt = Σ_g R_f · √N_g · M_env(f, class(g))        [continuous families]
N_g = number of active units of one part type in one environment class
```

(For event-based accrual, every event still counts, but within each group `g` units are ranked by commission timestamp, and events from units ranked 5th or later pay ×0.5.)

**Novel-environment multiplier `M_env`.** The first 200 operating hours of a family in each new *environment class* accrue at ×3. The same ×3 applies to **event-based ED** for events occurring while the family's 200-h clock for that class is still running (e.g. an EDL event within AeroFlight's first 200 h in a new class pays 25 × 3 = 75 ED). Environment classes (tags from 03): LEO/microgravity, deep-space radiation, vacuum dusty surface, cryogenic surface (< 120 K ambient), dense atmosphere (> 50 kPa), high-radiation (Jupiter belts), liquid immersion (Titan seas). Operating your proven excavator on Mars after the Moon is genuinely informative — the game says so.

**Event bonuses:**

- **Investigated failure:** +25 ED (machines) / +40 ED (engines) per failure event, *only if* telemetry was downlinked (comms path existed, 01 §4.8) or the unit is physically inspected by crew/robot within 30 days. Uninvestigated failures yield 0 — and still count against you. This is Crow-AMSAA's "corrective action" term.
- **Teardown:** physically returning a flown/used unit to a workshop (05) or Earth: one-time +10% of that unit's lifetime ED contribution.
- **Test stand / burn-in:** ground or base test facilities (05 module; Earth pad has one free) accrue ED at full rate while consuming real propellant/power/funds (12). This is how you mature an engine before risking crew, exactly as real programs do.

**Cap formula.** Per family:

```
C_f = max( 1.5 · max(ED thresholds among VISIBLE nodes naming family f; 0 if none),
           6 · D_half(f) )
D_f accrual halts at C_f  ("DATA SATURATED" in UI)
```

Visibility is defined in §3.8; researching or revealing new nodes raises `C_f` and accrual resumes. The unconditional `6 · D_half` floor guarantees every family — including families named by **no** node threshold anywhere (e.g. SolidMotors) — can mature to `m(C_f) = 1 + 3·2^(−6) ≈ 1.047 ≤ 1.05` (see F-7). Reliability curves keep reading the capped `D_f`.

### 3.3 Node unlock rule

A node may be researched when ALL hold:

1. The node is **visible** per §3.8 (hidden "???" nodes cannot be researched — the fog of research is a hard gate, not cosmetic; this is what makes the T4-behind-T3 rule in §3.8/F-8 binding).
2. Every prerequisite node is researched.
3. Every prerequisite Discovery (§4.11) is acquired.
4. Global Science ≥ Science cost (spent on confirm).
5. For each listed ED threshold, `D_family ≥ threshold` (checked, not spent).

Unlock is instantaneous on payment (the *time* cost of new tech lives in prototyping, §3.4, and fabrication hours, 05). Discovery-linked discounts (§4.11) multiply the Science cost before payment. Earth R&D campus upgrades (12-gameplay-economy-ui.md) may apply up to a further −20%; that knob is owned by 12.

**Cost bands (design targets; balancing may move individual nodes ±30%):**

| Tier | Science cost band (SCI) | ED threshold band (ED) |
|---|---|---|
| T0 | 0 (start-unlocked) | — |
| T1 | 60–300 | 80–400 |
| T2 | 300–900 | 200–1,200 |
| T3 | 900–2,500 | 400–2,000 |
| T4 `[SPECULATIVE]` | 4,000–12,000 | 2,000–4,000 |

Whole-tree totals (sums of §4 as written, after the DECISIONS A6/C19 rebalance — VH-09 retiered to T2 at 700 SCI; gravity-biology arc LS-09/10/11 added): T1 ≈ 5,100 / T2 ≈ 22,300 / T3 ≈ 54,000 / T4 ≈ 77,000 → ≈ **158,400 SCI** to research everything (T4 ≈ 49%). Total recoverable Science in the solar system with thorough Earth-return play ≈ **210,000 SCI**, derived from: the §3.6 `V_base` table × 03's region catalog (pools extracted at ×1.25 Earth-return), Discoveries ≈ 12,300, milestones (§3.7), and observation campaigns counted at their **program-wide cap of 15,000 SCI** (§3.5). The figure deliberately **excludes** the repeatable contract trickle (F-2, owned by 12), which is unbounded over infinite time but small by design (≤ 25% of act income, §9 Q4). Finishing the tree therefore requires exploring most of the system; finishing the *campaign* requires roughly half of it.

### 3.4 Prototyping and reliability maturation

**Part-type states:** `PROTOTYPE → FLIGHT → MATURE` (per part *type*, program-wide).

**Prototype (first article) rules.** The first unit of any newly unlocked part type:

- Resource build cost ×3 and fabrication hours ×2 (05 fab model).
- Reliability state multiplier `m_state = 4` until the type completes one **full-duration success**, defined per part category:

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

  Part categories with no meaningful operating duration — science instruments, solar sails, SRCs, and GNC software programs — **skip PROTOTYPE entirely** and enter FLIGHT state on unlock (they still pay the ×3/×2 first-article build costs where physical).
- After that success, the type enters FLIGHT state (`m_state = 1`) and subsequent units build at normal cost.
- A prototype that fails catastrophically must be replaced (another ×3-cost article), but the investigated-failure ED bonus applies — failure is literally progress, if you can see the wreckage.

**Maturation curve.** Catalog failure rates in 02/05/08/09 are *mature floors* (λ_min, p_min). The live rate for a type in family f:

```
λ(D_f) = λ_min · m(D_f) · m_state · m_unit
m(D_f) = 1 + 3 · 2^(−D_f / D_half)            [type-maturity multiplier, 4 → 1]
```

- `m_unit` = per-individual-unit infant mortality: ×2.5 for a unit's first 50 operating hours or first 3 ignitions (burn-in on a test stand clears it safely).
- Wear multipliers from 02 §3.14 (engines, `1 + 9w²`) and machine wear/MTBF models (05) stack multiplicatively on top — this doc owns only `m(D_f)`, `m_state`, `m_unit`. **One wear model, confirmed (DECISIONS A5):** 02's per-ignition/wear base × this doc's maturity stack `m(D_f)·m_state·m_unit` × 05's spares/MTBF consumption are **orthogonal multipliers** — no double counting anywhere in the chain — and the contract ships as an interface test in Phase 1.

**`D_half` per family (ED):**

| Families | D_half |
|---|---|
| Avionics | 100 |
| SolidMotors, StorableEngines, SurfaceMobility, PressureStructures, SolarPower, EnergyStorage | 150 |
| Kerolox/Hydrolox/Methalox engines, MiningMachines, ThermalControl | 200 |
| EPThrusters, CryoFluidMgmt, ECLSS-PhysChem, FabricationMachines | 250 |
| NTRCores, ISRU-Chem, RoboticsAutonomy, AeroFlight | 300 |
| FissionSystems, ECLSS-Bio | 400 |

**Worked examples (the numbers a programmer should reproduce):**

- *Pump-fed engine* (02 catalog: mature p_ign = 0.0005). FLIGHT-state type at `D_f = 0`, unit past burn-in (`m_state = 1`, `m_unit = 1`): `p = 0.0005 · m(0) = 0.0005·4 = 0.002` — matches 02 §3.14's "new type" row exactly (that row means a *post-prototype* type with zero family ED). After ≈ 25 program ignitions (≈ 25·(5 + 0.05·400 s) ≈ 625 ED, D_half 200): `m = 1 + 3·2^(−3.1) = 1.35`, `p = 0.00068`. The "Mature" badge displays at `D_f ≥ 600`; 02's two-row table is the displayed simplification of this curve.
- *ECLSS-PhysChem unit* with catalog MTBF 5,000 h (λ_min = 0.2 failures/1000 h): first article in PROTOTYPE state, past unit burn-in (`m(0) = 4`, `m_state = 4`, `m_unit = 1`), runs at `0.2·4·4 = 3.2 failures/1000 h` (one fault a fortnight — the real early CDRA experience on ISS); at `D_f = 500` (D_half 250): `m = 1.75`, λ = 0.35/1000 h in FLIGHT state.
- *NTR core* (02 lists NTR p_base = 0.003 as the mature flying value; m(D) approaches 1 from 4). First-article rated ignition in PROTOTYPE state **after test-stand burn-in** (`m(0) = 4`, `m_state = 4`, `m_unit = 1`): `0.003·4·4 = 4.8%`/ignition. Skip the burn-in and the very first ignition carries `m_unit = 2.5` too: `0.003·4·4·2.5 = 12%`. Test your reactor on the stand at Jackass Flats like it's 1969.

**Maturity perks (per family, at `D_f` milestones):**

| Milestone | Perk |
|---|---|
| `D_f ≥ 600` "Mature" | refurbishment cost −25% (02 §3.14 / 05 maintenance); badge in builder |
| `D_f ≥ 2,000` "Refined" | MachineParts upkeep −20% (05); ISRU/ECLSS throughput +2% |
| `D_f ≥ 5,000` "Optimized" | newly built units of the family: dry mass −5% (interface flag to 02/06 — applied at build time, never retroactively) |

### 3.5 Surveys, observation campaigns, anomalies

- **Orbital survey:** carry the instrument package (SC nodes) in any orbit with periapsis below the package's survey ceiling (per-class values in §4.10: SC-00 5,000 km global mapper, SC-03 200 km high-res mapper, SC-05 50,000 km remote survey) around the target body, accumulate 30 days of instrument-on time (warpable). One-shot award per (instrument class, region), where **instrument class = the package-level class ID (SC-00, SC-03, SC-05 — exactly three classes; individual instruments inside a package do not award separately)**: `15 · X` SCI. Upgraded classes re-survey the same regions once more at full value — new instruments see new things (anchor: Lunar Prospector → LRO → ShadowCam).
- **Ground survey:** rover/crew traverse with survey package: per region, one-shot `10 · X` SCI plus the resource-prospecting data layer consumed by 04 (K2 survey mechanics).
- **Observation campaign:** telescope platforms (SC-05) generate a trickle: `0.2 SCI/day` per platform, ×2 if outside 1.1 AU or in a dust-free vantage (03 tags), capped at 4,000 SCI lifetime per platform **and 15,000 SCI program-wide across all observation campaigns** (a telescope farm under time warp must not substitute for exploration; §3.3's recoverable-Science total counts this source at the program-wide cap). Models NEO Surveyor-class population science.
- **Anomalies:** hand-placed points of interest revealed by surveys (lava-tube skylights, fresh craters, exposed ice scarps, derelict-hardware historical sites like the Apollo 11 descent stage — real heritage objects only). Investigating on-site: lump SCI at the canonical conversion co-signed in 03 §4.6 — **2 SCI per GB** of the anomaly's SurveyData yield (03 §4.5 table; 30–400 SCI across the curated catalog, one-shot per anomaly; the GB remain a tradeable 12-§4.3 data resource and selling them does not forfeit the SCI). Some anomalies *are* Discoveries (§4.11).

### 3.6 Samples, labs, and sample return

**Sample types** (mass per sample item; one item = one pool draw `S_n`). `V_base` is the per-(activity, region) pool base of §3.1 (`P = V_base · X`, SCI, pre-exoticism); these seven rows are the complete set of pooled activity types. The §3.3 system-wide total (≈ 210,000 SCI) and §6's per-act income bands are *derived* from this column × 03's region catalog (×1.25 Earth-return), plus Discoveries, milestones, and capped observation campaigns:

| Sample type | V_base (SCI, pre-X) | Mass | Special handling | Acquired by |
|---|---|---|---|---|
| Atmosphere grab | 25 | 0.2 kg | gas bottle | any vehicle in atmosphere band |
| Regolith scoop | 40 | 0.5 kg | none | rover arm, crew EVA |
| Drill core | 60 | 2 kg per metre, max 3 m | none | Core Drill (04) |
| Ice core | 90 | 5 kg | **cryo: < 150 K** or value decays | Thermal Ice Corer (04) |
| Deep core | 140 | 25 kg | none | Deep Core Rig (04, 10+ m) |
| Liquid grab (Titan seas, Europa melt) | 120 | 1 kg | **cryo: < 150 K** or value decays | Sea Pump, cryobot (10) |
| Plume flythrough capture | 70 | 0.05 kg | aerogel cassette | orbital flythrough ≤ 3 km/s relative |

**Cryo decay (exact rule):** `award = S_n · M_analysis · max(0.2, 1 − 0.02 · days_above_150K)` — linear on `S_n`, floored at 20% (F-4: mineralogy survives even if volatiles bake out).

**Analysis paths.** A sample yields `S_n · M_analysis` when processed (pool depleted at `S_n` regardless of path):

| Path | `M_analysis` | Throughput / requirement | Anchor |
|---|---|---|---|
| In-situ robotic instrument (transmit only) | 0.40 | instant on acquisition; needs comms path | MSL SAM, MOMA-class instruments |
| Glovebox GL-1 (any crewed module) | 0.55 | 0.2 kg/day, 1 crew-h/kg | ISS MSG |
| Field Lab FL-2 (surface module) | 0.70 | 1 kg/day, 2.0 kWe, 1 crew or A2 robot | Apollo LM science + EDEN-class analog labs |
| Orbital Lab OL-12 (station module) | 0.90 | 3 kg/day, 6.0 kWe, 2 crew | ISS Destiny/Columbus; MSR receiving-facility studies |
| Earth Receiving Laboratory | 1.25 | instant on recovery; unlimited | Apollo LRL; Johnson curation; 382 kg Apollo legacy |

A sample is consumed by analysis (no double-dipping paths; choose where it gets processed). Earth return requires physical transport: a Sample Return Capsule part (SRC-46: 46 kg, holds 5 kg of samples, ballistic Earth reentry — anchor Stardust/OSIRIS-REx SRC; SRC-300 at T2: 300 kg, 30 kg capacity, lifting reentry) or any crewed/cargo vehicle that lands on Earth intact. Cryo samples additionally need a **Cryo Sample Vault** (0.8 t, 0.4 kWe, 50 kg capacity at < 150 K) in the transport chain or they decay en route. Losing the vehicle loses the samples — pools stay depleted only for the extracted `S_n` values actually awarded... correction, rule: **pool is depleted on analysis award, not on acquisition**; samples destroyed in transit return their `S_n` to the pool. No science is silently lost to a failed reentry, but the time is. Consequence: `S_n` is **assigned at the moment of analysis, in analysis order** — two held samples from the same pool take whichever S-values correspond to the order they reach a lab. The §5.4 manifest therefore displays *projections* (the value assuming that sample is analyzed next from its pool), not fixed tags.

### 3.7 Milestones and exoticism table

Program "firsts" (lump SCI, formula `k · X(body)`, X of the body's surface class):

| Milestone (per body) | k |
|---|---|
| First flyby | 10 |
| First orbit | 20 |
| First uncrewed landing (or atmosphere probe for gas giants/Venus deep) | 40 |
| First sample return to Earth | 60 |
| First crewed landing | 80 |
| First 30-day continuously crewed presence | 100 |

**Exoticism X by region class** (03 owns the per-region assignment; representative values):

| Region class | X |
|---|---|
| Earth surface / LEO | 1 |
| Earth high orbit, cislunar space | 1.5 |
| Moon nearside mare / highlands | 2 |
| Moon farside / polar / PSR | 4 |
| NEAs (C/S-type) | 4 |
| Mars orbit / surface | 5 |
| Phobos, Deimos, M-type NEA | 5 |
| Main belt (Ceres, Vesta, M-types) | 6 |
| Venus cloud layer (50–56 km) | 6 |
| Comet nuclei | 7 |
| Venus surface | 8 |
| Jupiter system (Callisto/Ganymede) | 8 |
| Jupiter atmosphere (probe band) | 9 |
| Io, Europa | 10 |
| Saturn atmosphere (probe band) | 10 |
| Saturn system (rings, icy moons) | 10 |
| Titan surface | 11 |
| Enceladus (south-polar terrain) | 12 |
| Europa sub-ice ocean, Titan sea floor | 14 |

(The atmosphere-probe rows exist so the gas-giant "first uncrewed landing (or atmosphere probe)" milestone, k = 40, always has a defined X; 03 owns final per-region assignment but every milestone key above must resolve to a single number, never a range.)

### 3.8 Tree visibility (fog of research)

- All T0 and T1 nodes: always visible.
- A T(n≥2) node is visible when (a) any node within distance 1 in its prerequisite graph is researched, OR (b) its gating Discovery is acquired.
- T4 nodes are additionally hidden until at least one T3 node in the same category is researched. `[SPECULATIVE]` watermark rendered on all T4 UI.
- Hidden nodes show as "???" silhouettes with tier and category only — the player can see the *shape* of the future, not its contents.

### 3.9 Edge formulas summary (implementation checklist)

```
SCI pool:        P = V_base·X (V_base table §3.6);  S_n = 0.6·R_(n-1);  R_n = R_(n-1)−S_n
Award:           S_n·M_analysis·max(0.2, 1−0.02·days_above_150K)   [decay term cryo-only]
ED accrual:      dD/dt = Σ_g R_f·√N_g·M_env(f, class(g))  (+ event terms; g = part type × env class)
Cap:             C_f = max(1.5·max visible threshold (0 if none), 6·D_half)
Maturity:        m(D) = 1 + 3·2^(−D/D_half);   λ_live = λ_min·m(D)·m_state·m_unit·(wear terms 02/05)
Prototype:       cost ×3, fab time ×2, m_state = 4 until 1 full-duration success (table §3.4)
Infant unit:     m_unit = 2.5 first 50 h / 3 ignitions, else 1
Unlock:          visible(§3.8) ∧ prereqs ∧ discoveries ∧ SCI ≥ cost (spend) ∧ ∀f: D_f ≥ threshold_f (check)
```

---

## 4. Content Catalog

The tree: **132 nodes** in 10 categories. Columns: Science cost (SCI, spent), ED threshold (checked against named family), prerequisites — grammar: `+` and `,` both mean AND (all required); `|` means OR and **binds tighter than AND**, so `(A | B) + C` requires C plus at least one of A/B; `DSC-xx` = Discovery §4.11 — unlocks (part/process IDs from sibling docs), real-world anchor. Tier `T4*` = `[SPECULATIVE]`. Start-unlocked T0 nodes cost 0 and have no prerequisites. **(era)** marks era-defining nodes (§4.12).

### 4.1 Propulsion (PR) — parts in 02-propulsion.md

| ID | Node | Tier | Prereqs | SCI | ED (family) | Unlocks | Anchor |
|---|---|---|---|---|---|---|---|
| PR-00 | Flight-Proven Stack | T0 | — | 0 | — | SRM-2, SRM-49, OMS-27, SPS-91, K-845, KV-981, H-102, RCS-N10, RCS-D400, ION-2 "Mayfly" gridded ion + HALL-1 "Wren" stationkeeping Hall thruster (EPThrusters T0 donors, IDs per 02 §4.4), parametric tanks (CryoFluidMgmt T0 donor) | Falcon 9 / Centaur / Soyuz heritage; NSTAR gridded ion (DS1/Dawn); SPT-100 Hall stationkeeping (flown since 1994) |
| PR-01 | Deep-Throttle Landing Engines | T1 | PR-00, GN-02 | 80 | 100 (StorableEngines) | LND-71 lander engine | Apollo LMDE (10:1 throttle); Blue Origin BE-7 |
| PR-02 | Reusable Methalox Heavy Lift **(era)** | T1 | PR-00 | 220 | 200 (KeroloxEngines) | M-2256, MV-2530, RCS-M2K; reusable booster ops (06/12) | SpaceX Raptor FFSC, Starship flight program |
| PR-03 | Modern Hydrolox Upper Stages | T1 | PR-00 | 100 | 150 (HydroloxEngines) | HL-67, H-2280 | RL10 family (since 1963), Centaur V |
| PR-04 | Cryogenic Fluid Management | T1 | PR-00 | 150 | 200 (CryoFluidMgmt) | ZBO-90/ZBO-20 cryocoolers, sunshields, PMD tanks | ULA IVF; NASA eCryo / CFM flight demos |
| PR-05 | Orbital Propellant Depot **(era)** | T1 | PR-04, GN-01 | 250 | 400 (CryoFluidMgmt) | DEP-60, PTC-200 coupler, propellant-transfer ops (02 §3.13) | ULA depot studies; Starship HLS refueling architecture |
| PR-06 | Gridded Ion Propulsion | T1 | PR-00 | 120 | 100 (EPThrusters) | ION-7 | NASA NEXT-C: 6.9 kW, 4,190 s, 236 mN (flies on DART) |
| PR-07 | High-Power Hall Clusters | T1 | PR-00 | 140 | 150 (EPThrusters) | HALL-12 | AEPS/HERMeS 12.5 kW (Gateway PPE) |
| PR-08 | Solar Sail Demonstrator | T1 | PR-00 | 90 | — | SAIL-86 | NEA Scout; IKAROS, LightSail 2 |
| PR-09 | Nuclear Thermal Rocket **(era)** | T2 | PR-04, PW-04 | 700 | 500 (HydroloxEngines) + 300 (FissionSystems) | NTR-73 "Prometheus" | NERVA-derived, Isp ~900 s; SNRE (Borowski); DARPA/NASA DRACO |
| PR-10 | Heavy NTR Core | T2 | PR-09 | 500 | 800 (NTRCores) | NTR-246 "Prometheus-H" | NERVA XE': 246 kN ground-tested 1969 |
| PR-11 | LANTR Augmentation | T2 | PR-09 | 350 | 600 (NTRCores) | LANTR option (O/H MR 3.0: thrust ×2.75 @ Isp 645 s — game value per 02 §3.10) | Borowski LANTR studies (NASA Glenn; 1994 study tables ≈ 647 s at MR 3.0) |
| PR-12 | NTR Alternate Propellants | T2 | PR-09 | 300 | 600 (NTRCores) | Ammonia/Water NTR modes (02 §3.10) | NERVA-era alternate-propellant studies |
| PR-13 | ISRU-Refuelable Landers | T2 | PR-02, IS-04 | 400 | 300 (MethaloxEngines) | ML-24 "Gopher", field-refueling ops | NASA Project Morpheus; Mars Direct ERV (Zubrin 1990) |
| PR-14 | Large Solar Sails | T2 | PR-08 | 350 | — | SAIL-1650 | NASA Solar Cruiser (1,653 m²) |
| PR-15 | Heavy Depot Infrastructure | T2 | PR-05 | 450 | 700 (CryoFluidMgmt) | DEP-600 "Reservoir", LH2 depot-grade insulation | ULA/NASA cryo depot architecture studies |
| PR-16 | Nested-Channel Hall Thrusters | T3 | PR-07, PW-08 | 1,200 | 900 (EPThrusters) | HALL-100 "Condor" | X3 nested Hall, 102 kW demo (U. Michigan/AFRL) |
| PR-17 | MPD Thrusters | T3 | PR-16 | 1,800 | 1,500 (EPThrusters) | MPD-200 "Albatross" | NASA Lewis / MAI applied-field MPD lab programs |
| PR-18 | VASIMR | T3 | PR-16 | 1,600 | 1,200 (EPThrusters) | VAS-200 "Petrel" | Ad Astra VX-200: 200 kW lab firings 2009–13 |
| PR-19 | Industrial Solar Sails | T3 | PR-14 | 1,000 | — | SAIL-10K | scaled NIAC/JPL sail-cargo studies |
| PR-20 | In-Space Engine Refurbishment | T3 | PR-10, IN-06 | 1,400 | 1,200 (NTRCores) | NTR refurbishment-in-space, advanced PMD/LAD couplers | ISS ORU servicing heritage, OSAM studies |
| PR-21 | Fission-Fragment Drive `[SPECULATIVE]` | T4* | PR-17, PW-08 | 6,000 | 2,500 (FissionSystems) | FFR-43 "Phoenix" | Werka dusty-plasma FF rocket, NIAC 2012 |
| PR-22 | Fusion Torch Drive `[SPECULATIVE]` **(era)** | T4* | PW-12 | 9,000 | 3,000 (FissionSystems) | DFD-5 "Helios"; PULSE-D blueprint access (endgame chain) | Princeton Direct Fusion Drive; BIS Project Daedalus (1978) |

### 4.2 Guidance, Navigation & Comms (GN) — programs in 01-orbital-mechanics.md §4.7

| ID | Node | Tier | Prereqs | SCI | ED (family) | Unlocks | Anchor |
|---|---|---|---|---|---|---|---|
| GN-00 | Baseline GNC | T0 | — | 0 | — | Node Execute, Ascent Guidance, Circularize, Hohmann Planner | Saturn V IGM; flown upper-stage guidance |
| GN-01 | Rendezvous & Proximity Ops | T1 | GN-00 | 100 | 80 (Avionics) | Rendezvous Sequencer, Autodock, Stationkeeping Manager, Window Finder | Kurs (1980s), ATV, Dragon autodock |
| GN-02 | Powered Descent Guidance | T1 | GN-00 | 130 | 100 (Avionics) | Vacuum Landing program | Apollo P63–P66; Falcon 9 landing guidance |
| GN-03 | Relay Constellations | T1 | GN-00 | 160 | — | relay satellite parts; comms-path rules for teleop & telemetry (05/§3.2) | TDRS; Mars relay network (MRO/Odyssey) |
| GN-04 | Atmospheric Flight Guidance | T2 | GN-02 | 450 | 300 (AeroFlight) | EDL Guidance + Aerocapture Guidance programs; aeroshell parts (06) | Viking→Mars 2020 EDL; NASA aerocapture systems analysis |
| GN-05 | Low-Thrust Mission Planning | T2 | PR-06 \| PR-07 | 400 | 200 (EPThrusters) | Low-Thrust Spiral planner | Edelbaum; SMART-1, Dawn ops |
| GN-06 | Optical Deep-Space Comms | T2 | GN-03 | 500 | 200 (Avionics) | laser comm terminals: telemetry/teleop range extension ×10 | NASA DSOC on Psyche (2023–24, > 1 AU optical downlink) |
| GN-07 | Multi-Flyby Tour Planning | T3 | GN-05 | 1,100 | 400 (Avionics) | Tour Planner (gravity-assist chains within planetary systems) | Galileo/Cassini tour design |

### 4.3 Power & Thermal (PW) — parts in 09-power-thermal.md

| ID | Node | Tier | Prereqs | SCI | ED (family) | Unlocks | Anchor |
|---|---|---|---|---|---|---|---|
| PW-00 | Baseline Power | T0 | — | 0 | — | rigid PV arrays, Li-ion packs, MMRTG (110 We, 4.8 kg PuO2), baseline body-mounted radiators (ThermalControl T0 donor) | ISS arrays; MMRTG (Curiosity/Perseverance) |
| PW-01 | Roll-Out Arrays & Concentrator Mirrors | T1 | PW-00 | 80 | 100 (SolarPower) | ROSA-class wings (20+ kW each), drop-in array upgrades; SOL-CONC concentrator mirrors (heat-only, 116 kWt @ 1 AU — process heat for 04 recipes; T1 per 09 §4.1) | ISS iROSA (2021–); terrestrial CSP heliostat practice |
| PW-02 | Regenerative Fuel Cells | T1 | PW-00 | 120 | 100 (EnergyStorage) | RFC night-survival storage (H2/O2 loop) | Gemini PEM fuel cells / Shuttle alkaline fuel cells + NASA lunar-night regenerative-PEM RFC studies |
| PW-03 | High-Capacity Radiators | T1 | PW-00 | 100 | 100 (ThermalControl) | deployable two-phase radiator wings | ISS EATCS (~70 kW heat rejection) |
| PW-04 | Kilopower Fission | T2 | PW-00 | 450 | 200 (FissionSystems) | NUK-KP1 + NUK-KP10 Kilopower units, 1–10 kWe (09 §4.3; = 06's PW-KP1/PW-KP10 — T2 in all three registries: ground-tested, never flown) | KRUSTY test, NNSS, March 2018 (1 kWe) |
| PW-05 | Fission Surface Power **(era)** | T2 | PW-04 | 800 | 500 (FissionSystems) | 40–100 kWe-class surface reactors | NASA FSP program (40 kWe contracts, 2022) |
| PW-06 | Advanced PV & Dust Mitigation | T2 | PW-01 | 350 | 250 (SolarPower) | T2 36%-cell array retrofits (09 §3.2 efficiency tier), SOL-BLK thin-film blanket arrays; SOL-EDS electrodynamic dust shields (Mars/Moon derating relief; T2 per 09 §4.1) | NREL 39.2% six-junction cell (2020); NASA EDS, demonstrated on the lunar surface by Firefly Blue Ghost Mission 1 (CLPS, 2025); prior ISS MISSE exposure tests |
| PW-07 | Thermal Energy Storage | T2 | PW-03 | 300 | 200 (ThermalControl) | molten-salt / regolith thermal batteries for lunar night | terrestrial CSP storage; lunar TES studies |
| PW-08 | Megawatt Space Reactors | T3 | PW-05, PW-09 | 1,800 | 1,800 (FissionSystems) | 0.5–2 MWe NEP reactor cores (powers PR-16/17/18 tugs) | SP-100; Project Prometheus/JIMO (200 kWe design) |
| PW-09 | Closed Brayton Conversion | T3 | PW-05 | 1,200 | 900 (ThermalControl) | Brayton power-conversion units (η ≈ 25–30%), big radiator economy; NUK-MSR 500 kWe thorium molten-salt surface plant (09 §4.3 — Thorium feed from lunar KREEP, 04) | NASA Brayton Rotating Unit tests (1960s–70s, 10 kWe class); ORNL MSRE (ran 1965–69) + Th-cycle studies |
| PW-10 | Radioisotope Production | T3 | PW-05, IS-09b | 1,000 | 1,000 (FissionSystems) | RX-19 Pu-238 line (04): 20 g Pu238/yr per 100 kWe core | Oak Ridge Pu-238 production restart (2015–) |
| PW-11 | Power Beaming | T3 | PW-08, GN-06 | 1,400 | 600 (SolarPower) | laser power links: kW-class over 10s of km (PSR rim→crater floor) | NASA Watts on the Moon; kW-class beaming demos |
| PW-12 | Fusion Power Plant `[SPECULATIVE]` | T4* | PW-08, IS-20 | 10,000 | 4,000 (FissionSystems) | D-He3 fusion plants (MWe-class, 09); enables PR-22 | D-He3 fusion concepts (Kulcinski, UW-Madison); SPARC/ARC lineage for confinement |

### 4.4 ISRU & Resource Processing (IS) — machines/recipes in 04-resources-isru.md

| ID | Node | Tier | Prereqs | SCI | ED (family) | Unlocks | Anchor |
|---|---|---|---|---|---|---|---|
| IS-00 | Orbital Prospecting | T0 | — | 0 | — | orbital spectrometer instruments; RX-05 SOXE demo (0.29 kg O2/day) | LRO/LCROSS/M3; **MOXIE**: 6–12 g O2/h, 122 g total (2021–23) |
| IS-01 | Surface Survey & Coring | T1 | IS-00 | 90 | — | Core Drill, Thermal Ice Corer, K2 ground-survey package | Honeybee TRIDENT drill (PRIME-1) |
| IS-02 | Regolith Excavation | T1 | IS-01 | 110 | — | Drum Excavator | NASA KSC RASSOR counter-rotating drum excavator |
| IS-03 | Water Electrolysis Plant | T1 | IS-00 | 130 | 100 (ECLSS-PhysChem) | RX-01 PEM electrolyzer (250 kg H2O/day), LOX/LH2 liquefaction chain | ISS OGA; industrial PEM (~50 kWh/kg H2) |
| IS-04 | Sabatier Methanation | T1 | IS-03 | 150 | 120 (ECLSS-PhysChem) | RX-03 Sabatier (91 kg CH4/day), LCH4 liquefaction, vapor-return cryo transfer | ISS Sabatier; Mars Direct/DRA 5.0 ISPP baseline |
| IS-05 | Polar Ice Mining **(era)** | T2 | IS-02 + DSC-01 | 550 | 300 (MiningMachines) | Bucket-Wheel excavator, Sublimation Tent, Rodwell | LCROSS Cabeus plume: 5.6 ± 2.9 wt% H2O (2009); RASSOR/IPEx lineage |
| IS-06 | Mars Atmosphere Processing | T2 | IS-04 + DSC-04 | 600 | 250 (ISRU-Chem) | Mars CO2 intakes, RX-04 RWGS, RX-05 plant scale (100 kg O2/day) | MOXIE scale-up studies; DRA 5.0 ISRU |
| IS-07 | Beneficiation & Ore Dressing | T2 | IS-02 | 400 | 250 (MiningMachines) | Beneficiation Separator (magnetic/electrostatic) | terrestrial mineral processing; lunar ilmenite concentration studies |
| IS-08 | Ilmenite Hydrogen Reduction | T2 | IS-07 | 650 | 400 (ISRU-Chem) | RX-07 line (100 kg O2/day + IronSteel + TiO2 slag) | Apollo-era + Artemis lunar-oxygen baseline chemistry |
| IS-09a | Gas & Volatile Chemistry | T2 | IS-04 | 500 | 300 (ISRU-Chem) | RX-13 Cryo Fractionator, RX-14 Haber loop, RX-15 Polymer plant | air-separation industry; Haber-Bosch |
| IS-09b | Materials Chemistry | T2 | IS-07 | 550 | 300 (ISRU-Chem) | RX-06 Bosch, RX-12 H2-DRI steel, RX-17 Basalt/Glass furnace | HYBRIT H2-DRI pilot; basalt-fiber industry |
| IS-10 | NEA Volatile Capture | T2 | IS-01 + DSC-15 | 500 | 200 (MiningMachines) | Capture Bag, Volatile Oven (C-type baking) | NASA ARM capture studies; Hayabusa2/OSIRIS-REx regolith mechanics |
| IS-11 | Deep Core Drilling | T2 | IS-01 | 450 | 300 (MiningMachines) | Deep Core Rig (> 10 m), deep-core sample type | terrestrial wireline coring; Mars deep-drill studies |
| IS-12 | Carbothermal Reduction | T2 | IS-08 | 700 | 500 (ISRU-Chem) | RX-08 carbothermal O2 (any regolith, 50 kg O2/day) | NASA/Sierra Space CaRD demo (2023) |
| IS-13 | Molten Regolith Electrolysis | T3 | IS-12, PW-05 | 1,600 | 800 (ISRU-Chem) | RX-09 MRE cell (250 kg O2/day + Fe-Si) | MIT MRE (Sadoway/Schreiner models) |
| IS-14 | Carbonyl Metal Refining | T3 | IS-10 + DSC-16 | 1,400 | 700 (ISRU-Chem) | RX-10 Mond refinery (500 kg metal/day, PGM residue) | INCO Clydach carbonyl process (since 1902); Lewis, *Mining the Sky* |
| IS-15 | Light-Metal Production | T3 | IS-13 | 1,800 | 1,000 (ISRU-Chem) | RX-11 anorthite Al line, RX-18 FFC titanium cell | NASA SP-509; FFC Cambridge process |
| IS-16 | Solar-Grade Silicon | T3 | IS-13 | 1,500 | 800 (ISRU-Chem) | RX-16 Siemens refiner (20 kg/day solar-grade Si) | Siemens process (trichlorosilane) |
| IS-17 | Strip & Optical Mining | T3 | IS-05 \| IS-10 | 1,300 | 900 (MiningMachines) | strip miners; Optical Mining (concentrated-sunlight spalling) | TransAstra Apis NIAC optical mining |
| IS-18 | Venus Aerostat Intake | T3 | HB-05 + DSC-08 | 1,700 | 600 (ISRU-Chem) | Venus Aerostat Intake (CO2/N2 capture at 52 km) | NASA HAVOC; Venus atmosphere 96.5% CO2 / 3.5% N2 |
| IS-19 | Titan Hydrocarbon Processing | T3 | DSC-13, IS-09a | 1,600 | 600 (ISRU-Chem) | Titan Sea Pump, Titan atmosphere intake (CH4/N2) | Cassini/Huygens lake composition; TiME proposal (2011) |
| IS-20 | He3 Volatile Kiln `[SPECULATIVE]` | T4* | IS-17 + DSC-02 | 7,000 | 2,500 (MiningMachines) | He3 Volatile Kiln (g/t-level H2/H2O/N2/C byproducts + ppb He3) | Wittenberg/Kulcinski/Schmitt (UW-Madison): 5–20 ppb He3 in ilmenite-rich mare |
| IS-21 | Gas-Giant Atmospheric Scoop `[SPECULATIVE]` | T4* | PR-22 + DSC-18 | 8,000 | 2,000 (AeroFlight) | atmospheric scoop craft (H2/He/He3 skimming) | Daedalus aerostat He3 acquisition concept (BIS) |

### 4.5 Industry & Automation (IN) — modules/robots in 05-industry-logistics.md

| ID | Node | Tier | Prereqs | SCI | ED (family) | Unlocks | Anchor |
|---|---|---|---|---|---|---|---|
| IN-00 | Earth Supply Chain | T0 | — | 0 | — | polymer printer farm, automated cargo docking, manual EVA ops (A0) | ISS commercial resupply (Kosmos-186/188 → Dragon lineage) |
| IN-01 | Pressurized Workshop & Machine Shop | T1 | SH-01 | 100 | 80 (FabricationMachines) | machine shop, pressurized workshop (05) | ISS maintenance work area heritage |
| IN-02 | Foundry & Chemical Plant | T1 | IN-01 | 140 | — | foundry & mill, chemical plant (05) | terrestrial small-batch industry |
| IN-03 | Electronics Assembly | T1 | IN-01 | 180 | — | electronics assembly line (imported Wafers) | terrestrial SMT lines; ISS in-space manufacturing pilots |
| IN-04 | Robotic Manipulation (A1) | T1 | GN-01 | 150 | 100 (RoboticsAutonomy) | berthing arm, dexterous unit | Canadarm2 / Dextre |
| IN-05 | Orbital Assembly & WAAM | T2 | IN-01, SH-01 | 500 | 350 (FabricationMachines) | WAAM cell, assembly hall | wire-arc additive industry; NASA OSAM/Archinaut studies |
| IN-06 | Orbital Dry Dock | T2 | IN-05 | 700 | 500 (FabricationMachines) | orbital dry dock (06: never-lands ships) | ISS truss assembly heritage, scaled |
| IN-07 | Teleoperated Worker Robots (A2) | T2 | IN-04, GN-03 | 550 | 400 (RoboticsAutonomy) | worker robots, surface teleoperation (incl. orbit→surface) | ESA Analog-1 / METERON teleop experiments |
| IN-08 | Automated Haulage Routes | T2 | VH-02, IN-07 | 400 | 250 (SurfaceMobility) | automated surface logistics routes (05) | autonomous haul-truck fleets (Pilbara mining) |
| IN-09 | Supervised Autonomy (A3) | T3 | IN-07 | 1,400 | 1,000 (RoboticsAutonomy) | A3 autonomy: task queues without comms link | Mars rover AutoNav lineage; NASA autonomy roadmaps |
| IN-10 | Autonomous Factory Complex **(era)** | T3 | IN-09 | 2,200 | 1,600 (RoboticsAutonomy) + 800 (FabricationMachines) | autonomous factory complexes (χ = 0.90, 05) | NASA 1980 summer study, *Advanced Automation for Space Missions* (CP-2255) |
| IN-11 | Wafer Fab **(era)** | T3 | IS-16, IN-09 | 2,500 | 1,200 (FabricationMachines) | off-Earth wafer fab — "Silicon Independence" milestone (05) | trailing-edge rad-hard fab (90–180 nm class) |
| IN-12 | Mass Driver & Catcher **(era)** | T3 | PW-05, IN-05 | 2,000 | 800 (FabricationMachines) | lunar mass driver (2.5 km/s muzzle ≈ escape 2,380 m/s + trim; 1.45 kWh/kg per 05 §3.8), orbital catcher, regolith pelletizer | O'Neill & Kolm mass-driver work; NASA Ames 1977 summer study, *Space Resources and Space Settlements* (SP-428) |
| IN-13 | In-Space Truss Fabrication | T3 | IN-06 | 1,200 | 700 (FabricationMachines) | trusselator robots (05): print structure on orbit | Tethers Unlimited SpiderFab / Trusselator (NIAC) |
| IN-14 | Self-Expanding Industry Seed `[SPECULATIVE]` | T4* | IN-10, IN-11 | 9,000 | 3,500 (RoboticsAutonomy) | self-expanding industry seed (χ = 0.98, 05) | AASM self-replicating lunar factory chapter (1980); Freitas |

### 4.6 Ships, Stations & Logistics (SH) — hulls/ops in 06-ships-stations.md, freighters in 05

| ID | Node | Tier | Prereqs | SCI | ED (family) | Unlocks | Anchor |
|---|---|---|---|---|---|---|---|
| SH-00 | Crew Capsule Operations | T0 | — | 0 | — | crew capsule, cargo capsule, PAD-1/PAD-2 | Dragon 2 / Soyuz / Starliner |
| SH-01 | Station Modules | T1 | GN-01 | 120 | 100 (PressureStructures) | rigid hab modules, docking nodes, PAD-3 | ISS USOS modules |
| SH-02 | Inflatable Modules | T1 | SH-01 | 200 | 150 (PressureStructures) | inflatable habs (volume/mass ×3 vs rigid, 06) | BEAM (on ISS since 2016); Bigelow B330; Sierra LIFE |
| SH-03 | Pallet Tug | T1 | GN-01, PR-06 | 150 | — | Pallet tug (05 short-haul logistics) | space-tug studies; MEV docking heritage |
| SH-04 | Pelican Lander Lift Loop | T2 | PR-13, IS-05 | 600 | — | Pelican reusable surface↔orbit lift loop (05) | lunar single-stage methalox/LOX-H2 lander studies |
| SH-05 | Drayage SEP Freighter | T2 | PR-07, GN-05 | 650 | 300 (EPThrusters) | Drayage SEP freighter class (05) | Gateway PPE-derived cargo SEP |
| SH-06 | Longhaul NTR Freighter | T2 | PR-09, IN-05 | 900 | — | Longhaul NTR freighter class (05) | Borowski NTR cargo architectures (NASA Glenn) |
| SH-07 | Cycler Architecture | T3 | GN-07, HB-06 | 1,300 | — | cycler habitats & schedule planner (01/06) | Aldrin Earth–Mars cycler (1985) |
| SH-08 | Momentum-Exchange Skyhook `[SPECULATIVE]` | T4* | IN-12, IN-13 | 6,500 | 2,000 (FabricationMachines) | rotating tether logistics nodes (suborbital catch, 05/06) | HASTOL study (Boeing/Tethers Unlimited, 2000); MXER tether (NIAC) |
| SH-09 | Interstellar Precursor Program `[SPECULATIVE]` | T4* | (PR-21 \| PR-22) + IN-14 | 12,000 | — | endgame megaproject blueprint: 500+ AU probe (12 victory chain) | JPL TAU study (1987, 1000 AU NEP); JHU/APL Interstellar Probe study (2021) |

### 4.7 Habitats & Bases (HB) — modules in 07-bases-habitats.md

| ID | Node | Tier | Prereqs | SCI | ED (family) | Unlocks | Anchor |
|---|---|---|---|---|---|---|---|
| HB-01 | Surface Habitat Landers | T1 | SH-01, GN-02 | 300 | 200 (PressureStructures) | delivered surface hab modules, airlocks | Artemis surface habitat studies |
| HB-02 | Regolith Shielding | T2 | HB-01, IS-02 | 350 | — | berms, 2–3 t/m² overburden shielding (07/08 dose model) | NASA GCR/SPE regolith shielding studies |
| HB-03 | Regolith Construction Printing | T2 | HB-02, IN-07 | 600 | 350 (FabricationMachines) | printed/sintered structures, landing pads | ICON Project Olympus (NASA MMPACT); ESA D-Shape |
| HB-04 | Lava-Tube Outfitting | T3 | DSC-03, HB-03 | 1,300 | — | lava-tube base sites: near-zero radiation, 290 K-stable interiors | Marius Hills skylight (Kaguya 2009); Mare Tranquillitatis pit thermal stability (Horvath et al. 2022) |
| HB-05 | Venus Aerostat Habitat | T3 | SH-02, GN-04, DSC-08 | 2,000 | 500 (PressureStructures) + 400 (AeroFlight) | crewed aerostats at 50–54 km (60–107 kPa [≈0.6–1.05 atm], 315–350 K; ≈100 kPa only at the 50 km HAVOC altitude; breathable-air lifting gas) | NASA Langley HAVOC (2015) |
| HB-06 | Spin-Gravity Centrifuge | T3 | SH-01 | 900 | 400 (PressureStructures) | centrifuge sleep modules (partial-g countermeasure, 08) | Nautilus-X centrifuge demo concept; Gemini 11 tether spin (1966) |
| HB-07 | Titan Surface Outpost | T3 | PW-04, DSC-13 | 1,500 | — | Titan base kit: 94 K / 146.7 kPa N2 environment systems (07) | NASA Glenn Titan exploration studies; Huygens (2005) |
| HB-09 | Mercury Terminator Operations | T3 | VH-04, PW-04 | 1,500 | 800 (SurfaceMobility) | HAB-16 Mercury Crawler Platform (07 §4.3.8), RVR-CRAWL crawler drivetrain (10 §4.1; NUK-KP10 ×3 powered), Mercury Mass Driver Port site class (07; launcher itself per IN-12) — Act 4 optional content (03 §6) | JPL Mercury terminator-rover studies (equatorial dawn ≈ 3.6 km/h — a slow crawler outruns sunrise); MESSENGER radar-bright polar ice |
| HB-08 | Rotating Settlement `[SPECULATIVE]` | T4* | HB-06, IN-12, IS-15 | 4,500 | 1,500 (PressureStructures) | large spin habitat (1 g rim, 100+ crew) — endgame megaproject | NASA Ames/Stanford Torus summer study (1975) |

### 4.8 Life Support & Crew (LS) — systems in 08-life-support-crew.md

| ID | Node | Tier | Prereqs | SCI | ED (family) | Unlocks | Anchor |
|---|---|---|---|---|---|---|---|
| LS-00 | Open-Loop Life Support | T0 | — | 0 | — | LiOH scrubbers, stored O2/Water/FoodRations, basic IVA suits, VEG-1 salad rack (ECLSS-Bio T0 donor; morale only) | Apollo / Dragon ECLSS; ISS Veggie (flown since 2014) |
| LS-01 | Regenerative ECLSS | T1 | LS-00 | 200 | 150 (ECLSS-PhysChem) | CO2 sorbent beds, O2 electrolysis, Sabatier loop, water processor | ISS ECLSS: 98% water recovery (2023); OGA/CDRA |
| LS-02 | Crop Production Modules | T1 | LS-00 | 150 | 80 (ECLSS-Bio) | salad-crop racks (morale + trace food, 08) | ISS Veggie / Advanced Plant Habitat |
| LS-03 | Surface EVA Suits | T1 | LS-00 | 180 | 100 (PressureStructures) | dust-tolerant surface EVA suits | NASA xEMU / Axiom AxEMU |
| LS-04 | Greenhouse Food Production | T2 | LS-02 | 500 | 300 (ECLSS-Bio) | LS-GARDEN EDEN-class greenhouse racks: partial diet, η_food 0.25–0.50 (08 §3.3/§4.1; full-diet closure starts at T3 via LS-07) | EDEN ISS Antarctic greenhouse (~270 kg vegetables/yr from 12.5 m²) |
| LS-05 | Radiation Protection Planning | T2 | LS-01 | 400 | — | water-wall storm shelters, dosimetry & career-dose planner (08) | NASA permissible exposure limits; SPE shelter studies |
| LS-06 | Advanced Water & Waste Loops | T2 | LS-01 | 450 | 350 (ECLSS-PhysChem) | brine recovery, waste pyrolysis (08) | ISS Brine Processor Assembly (2021–) |
| LS-07 | Closed-Loop Bioregenerative ECLSS **(era)** | T3 | LS-04, LS-06 | 2,400 | 1,500 (ECLSS-Bio) | algae/bacteria/plant loop (LS-GREEN full-diet racks, 08 §4.1; HB-GRN module, 06): ≥ 95% air/water, η_food 0.80→0.95 (08 §3.3) | ESA MELiSSA; BIOS-3 (Krasnoyarsk, 6-month closures); Lunar Palace 365 (Beihang, 370 d, 2017–18) |
| LS-08 | Long-Duration Crew Health | T2 | LS-01 | 350 | — | med bay, exercise countermeasures, psych-support systems (08) | ISS medical ops; ARED countermeasure heritage |
| LS-09 | Partial-Gravity Biology I — Centrifuge Studies | T2 | LS-08 | 400 | 200 (ECLSS-Bio) | the gravity-biology research arc opener (08 §3.14 GENERATIONS — decision log C19): small-animal onboard-centrifuge studies on partial-g development; first gravity-threshold data layer (08 demographic pillar) | NASA rodent centrifuge studies; Bion/Foton biosat program; ISS Rodent Research |
| LS-10 | Partial-Gravity Biology II — Mammalian Trials | T3 | LS-09, HB-06 | 1,200 | 600 (ECLSS-Bio) | multi-generation mammalian reproduction trials in spin habitats (HB-06/06); narrows the g_repro threshold brackets (08 §3.14); demographic-pillar maturation | rodent multi-generation spin studies; analog-habitat reproduction research |
| LS-11 | Human Reproduction Protocols `[SPECULATIVE]` | T4* | LS-10 | 5,000 | — | [SPECULATIVE] human partial-gravity gestation/development protocols and spin-habitat prescriptions (08 §3.14 GENERATIONS, Pass 2 / Phase 6+); satisfies the Foundation Audit demographic pillar's biological-continuity requirement (12) | honest speculation — no human off-Earth pregnancy data exists; arc models the uncertainty per C19 |

### 4.9 Vehicles (VH) — chassis/craft in 10-vehicles.md

| ID | Node | Tier | Prereqs | SCI | ED (family) | Unlocks | Anchor |
|---|---|---|---|---|---|---|---|
| VH-00 | Teleoperated Rovers | T0 | — | 0 | — | robotic rover chassis, teleoperated sampling arm (task orders feed RoboticsAutonomy ED — T0 donor), instrument mounts | Curiosity / Perseverance class |
| VH-01 | Crewed Unpressurized Rover | T1 | LS-03 | 130 | 80 (SurfaceMobility) | open rover (2 crew + cargo) | Apollo LRV; Artemis LTV |
| VH-02 | Robotic Haulers | T1 | VH-00 | 200 | 150 (SurfaceMobility) | dump/haul chassis for 04/05 logistics | autonomous haul trucks (terrestrial mining) |
| VH-03 | Ballistic Hoppers | T1 | GN-02 | 250 | — | propulsive hop vehicles (PSR access, anomaly reach) | Intuitive Machines Micro-Nova hopper |
| VH-04 | Pressurized Rover | T2 | VH-01, LS-01 | 550 | 350 (SurfaceMobility) | pressurized rover (2–4 crew, 14-day sorties) | JAXA/Toyota Lunar Cruiser; NASA Space Exploration Vehicle |
| VH-05 | Mars Rotorcraft | T2 | GN-04 | 480 | 200 (AeroFlight) | scout/courier rotorcraft for thin CO2 atmospheres | Ingenuity: 72 flights (2021–24); Mars Science Helicopter study |
| VH-06 | Titan Rotorcraft | T3 | VH-05, SC-03 | 1,300 | 600 (AeroFlight) | heavy Titan rotorcraft (dense N2, low g) | Dragonfly (NASA New Frontiers, launch 2028) |
| VH-07 | Titan Submarine | T3 | DSC-13 | 1,800 | 800 (AeroFlight) | submarine for Kraken/Ligeia Mare; sea-floor sampling | NASA Glenn COMPASS Titan Submarine (NIAC, 90-day cruise design) |
| VH-08 | Ice-Penetrating Cryobot | T3 | DSC-10, PW-04 | 2,200 | 800 (AeroFlight) | fission-heated melt probe (km-class ice shells) + ocean sampler | NASA SESAME program; Honeybee SLUSH; Europa shell 15–25 km |
| VH-09 | Venus Atmospheric Platforms | T2 | DSC-08, GN-04 | 700 | 500 (AeroFlight) | **robotic** variable-altitude balloons, cloud-layer drones, helium-cell starter aerostats (07 §4.3.3) — the **T2 robotic aerostat tier** per DECISIONS A6 (crewed HB-05 stays T3); Act-4 timing preserved by the DSC-08 gate | Soviet VEGA balloons (1985, ~46 h at ~54 km); JPL variable-altitude balloon studies |
| VH-10 | Venus Surface Systems | T3 | DSC-08 | 1,400 | 300 (Avionics) | long-duration surface stations (SiC electronics, 737 K / 9,200 kPa [≈91 atm]) | NASA Glenn LLISSE (60-day design target) |

### 4.10 Science Instruments & Labs (SC) — this doc's own parts

| ID | Node | Tier | Prereqs | SCI | ED (family) | Unlocks | Anchor |
|---|---|---|---|---|---|---|---|
| SC-00 | Survey Instruments I | T0 | — | 0 | — | camera, vis/IR spectrometer, magnetometer, radio science (50 kg pkg) | LRO instrument suite |
| SC-01 | Sample Return Capsules | T1 | GN-00 | 120 | — | SRC-46 (46 kg, 5 kg sample, ballistic reentry) | Stardust / OSIRIS-REx SRC (46 kg, 121.6 g returned) |
| SC-02 | Field Laboratory | T1 | LS-00 | 200 | — | GL-1 glovebox (0.4 t, ×0.55); FL-2 field lab (3.5 t, 2 kWe, ×0.70) | ISS Microgravity Science Glovebox; MSL SAM (~40 kg in-situ lab) |
| SC-03 | Survey Instruments II | T2 | SC-00 | 350 | — | ground-penetrating radar, neutron spectrometer, gravimeter, lidar (120 kg pkg; feeds 04 K2 resource layer) | RIMFAX (Perseverance); LRO LEND |
| SC-04 | Orbital Laboratory | T2 | SH-01, SC-02 | 600 | — | OL-12 lab module (12 t, 6 kWe, ×0.90) | ISS Destiny/Columbus; MSR receiving-facility studies |
| SC-05 | Deep-Space Observatories | T2 | SC-00, GN-03 | 700 | — | telescope platforms (0.2 SCI/day trickle; NEA/comet target catalog for 03) | NEO Surveyor |
| SC-06 | Cryogenic Sample Chain | T2 | SC-01 | 400 | — | Cryo Sample Vault (0.8 t, 50 kg @ <150 K); SRC-300 (300 kg, 30 kg sample, lifting reentry) | MSR / lunar-PSR cryo-curation studies |
| SC-07 | Astrobiology Suite | T3 | SC-04 | 1,500 | — | life-detection instrument package; ×1.5 analysis value on DSC-11/13/14 organics tranches (§4.11) | Europa Lander SDT report (2016); MOMA (Rosalind Franklin) |

**Survey package stats** (the simulation-facing numbers for §3.5; the one-shot survey award key is the **package-level class ID** — exactly these three classes; the 4+ instruments inside a package never award separately):

| Class ID (award key) | Package | Mass | Power | Survey ceiling (periapsis must be below) |
|---|---|---|---|---|
| SC-00 | Survey Package I (camera, vis/IR spectrometer, magnetometer, radio science) | 50 kg | 0.3 kWe | 5,000 km (global mapper) |
| SC-03 | Survey Package II (GPR, neutron spectrometer, gravimeter, lidar) | 120 kg | 0.6 kWe | 200 km (high-res mapper) |
| SC-05 | Observatory Platform (telescope bus) | 1,500 kg | 2.0 kWe | 50,000 km (remote survey) — plus the 0.2 SCI/day campaign trickle, caps per §3.5 |

### 4.11 Location-gated Discoveries (DSC)

Discoveries are one-time acquisitions tied to physical presence. Each grants its lump SCI immediately (no analysis multiplier — the listed acquisition already defines the path) and permanently satisfies prerequisites / applies discounts. **Exception — staged biology payouts.** The three biology-arc Discoveries DSC-11, DSC-13, DSC-14 pay in three tranches keyed to their analysis chain: **40%** of listed SCI on acquisition (any node gates they satisfy release immediately at this point), **30%** on SC-07 suite analysis of the retained material, **30%** on the Earth-return verdict (SRC-300 + Cryo Sample Vault chain). SC-07's ×1.5 organics bonus applies to the **second and third tranches only** (max total = listed × (0.4 + 1.5·0.6) = listed × 1.3; e.g. DSC-11 up to 3,250 SCI). All other Discoveries are immediate lump sums. No aliens anywhere: organics content is chemically real and deliberately ambiguous.

| ID | Discovery | Where / how acquired | SCI | Gates / discounts |
|---|---|---|---|---|
| DSC-01 | Lunar PSR Ice Ground Truth | ≥ 1 m ice core inside a PSR site (Thermal Ice Corer) | 300 | gates IS-05; −20% IS-03 |
| DSC-02 | Mare Volatile Assay | deep cores + Volatile Oven assay at 3 distinct mare sites | 400 | gates IS-20; reveals He3/volatile ppb map layer (03) |
| DSC-03 | Lava-Tube Interior Survey | hopper/rover descends a skylight anomaly with lidar | 350 | gates HB-04; −15% HB-03 |
| DSC-04 | Mars Environment Characterization | 90 sols of surface meteorology + dust data from one station | 300 | gates IS-06; −20% VH-05 |
| DSC-05 | Mars Subsurface Ice & Brines | GPR survey + 10 m core, mid-latitude site | 500 | gates Mars water chain sites (04); −15% HB-03 at Mars |
| DSC-06 | Phobos/Deimos Regolith | lander + returned or lab-analyzed sample | 350 | −20% SH-04; Phobos depot site survey (06) |
| DSC-07 | Comet Nucleus Sample | rendezvous + sample from an active comet | 600 | −30% IS-10 |
| DSC-08 | Venus Cloud-Layer Chemistry | 30 days of balloon/probe data at 50–56 km | 600 | gates HB-05, VH-09, VH-10, IS-18 |
| DSC-09 | Venus Surface Mineralogy | surface station surviving ≥ 60 min (or LLISSE-class 60 d) | 700 | −25% VH-10 |
| DSC-10 | Europa Plume & Exosphere Volatiles | low-orbit flythrough capture ≤ 3 km/s | 800 | gates VH-08 |
| DSC-11 | Europa Ocean Water | cryobot reaches the sub-ice ocean; melt sample analyzed | 2,500 | "ambiguous organics" arc I (staged 40/30/30; ×1.5 with SC-07 on tranches 2–3); campaign codex |
| DSC-12 | Enceladus Plume Sampling | south-polar plume flythrough capture | 900 | −30% VH-08; hydrothermal H2/silica codex (Cassini 2017 anchor) |
| DSC-13 | Titan Lake Composition | lake-surface sample (lander or VH-06 rotorcraft) | 800 | gates VH-07, IS-19, HB-07 |
| DSC-14 | Titan Sea Floor Survey | VH-07 submarine sonar map + sediment sample | 1,200 | "ambiguous organics" arc II |
| DSC-15 | C-Type NEA Assay | rendezvous + 3 samples from one C-type NEA | 350 | gates IS-10 |
| DSC-16 | M-Type Metal Assay | rendezvous + sample from an M-type body | 450 | gates IS-14 |
| DSC-17 | Jovian Radiation Survey | orbiter dosimetry across ≥ 4 Jupiter-system orbits | 500 | gates crewed Jupiter-system ops (08 dose planner); −20% VH-08 |
| DSC-18 | Saturn Atmosphere Probe | entry probe telemetry to ≥ 1,000 kPa (10 bar) depth | 700 | gates IS-21 |

**The biology question (narrative spec).** DSC-11 and DSC-13/14 return *chemistry*, never organisms: chiral-excess measurements that sit at 2σ, methane disequilibria with viable abiotic pathways, lipid-like vesicle structures of uncertain origin. Each has a three-stage analysis chain (in-situ → SC-07 suite → Earth-return with SRC-300 + cryo vault) paying the 40/30/30 tranches defined in this section's intro, and the final Earth verdict is written to remain scientifically open. The payoff is Science, prestige (12), and codex text — not a creature. This is a hard content rule.

### 4.12 Era-defining nodes (the 10 that change the game's shape)

| Node | Act | What changes strategically |
|---|---|---|
| PR-02 Reusable Methalox Heavy Lift | 1 | $/kg to LEO collapses (12 price table); mass stops being the binding constraint on LEO ambition; flight *rate* becomes the new currency of ED accrual |
| PR-05 Orbital Propellant Depot | 1→2 | missions stop being single-launch puzzles; the map grows logistics nodes; "where is my propellant" becomes the campaign's standing question |
| IS-05 Polar Ice Mining (+ IS-03/04 chain) | 2 | first off-Earth propellant: the Moon flips from destination to gas station; Earth-launch demand per mission drops ~70% for cislunar ops |
| PR-09 Nuclear Thermal Rocket | 2→3 | Isp ~900 s halves Mars transit propellant or trip time; NEAs and the belt enter realistic Δv reach; nuclear regulatory events (12) begin |
| PW-05 Fission Surface Power | 2→3 | bases survive the 354-h lunar night and Mars dust storms without heroics; industry siting decouples from sunlight; PSR mining becomes routine |
| LS-07 Closed-Loop Bioregenerative ECLSS | 3→4 | crew stop being a resupply liability; outposts beyond Mars become permanent; FoodRations logistics shrink ~90% (08) |
| IN-10 Autonomous Factory Complex | 4 | industry scales without crew or comms babysitting; the player's role shifts from operator to architect; exponential (not linear) base growth |
| IN-11 Wafer Fab ("Silicon Independence") | 4 | the last Earth umbilical (Electronics) is cut; true off-Earth self-sufficiency becomes possible; Earth budget pressure (12) loses its teeth |
| IN-12 Mass Driver & Catcher | 4→5 | lunar/asteroid bulk mass to orbit at electricity prices; megaproject construction streams open; propellantless export reshapes 05's network |
| PR-22 Fusion Torch Drive `[SPECULATIVE]` | 5→End | transit times stop dictating life-support sizing; the outer system becomes a place you *commute*; enables the interstellar precursor |

### 4.13 T4 endgame summary — all `[SPECULATIVE]`, honestly

Ten nodes: PR-21 (fission-fragment), PR-22 (fusion torch), PW-12 (fusion plant), IS-20 (He3 kiln), IS-21 (gas-giant scoop), IN-14 (self-expanding seed), SH-08 (skyhook), SH-09 (interstellar precursor), HB-08 (rotating settlement), LS-11 (human reproduction protocols). Honesty notes, rendered in-game on each node tooltip:

- **Fusion (PR-22, PW-12):** no net-energy D-He3 device exists; confinement physics is sound, engineering is not done. Anchors are concept studies (Princeton DFD, Daedalus), not hardware.
- **He3 economy (IS-20, IS-21):** abundances (5–20 ppb in mare regolith) are measured and honest — which is precisely why the kiln must move ~100,000 t of regolith per kg of He3. The game does not inflate the ore grade; it gives you T3 strip miners instead.
- **Skyhook (SH-08):** momentum-exchange tethers are dynamically modeled in real studies (HASTOL, MXER) but never flown at scale; material requirements (Spectra/Zylon-class, *not* unobtainium) are respected in 06's tether part spec.
- **Self-expanding seed (IN-14):** 98% closure, never 100% — the 1980 AASM study's own conclusion; Electronics closure still requires IN-11 fab capacity.
- **Rotating settlement (HB-08):** spin gravity is plain Newton; the speculation is economic scale, hence its placement behind mass driver + light-metal ISRU.
- **Interstellar precursor (SH-09):** a 500+ AU probe in decades needs T4 propulsion; this is the campaign's victory monument, anchored to real mission studies (TAU 1987, Interstellar Probe 2021).
- **Human reproduction protocols (LS-11):** no human off-Earth pregnancy or partial-g development data exists — the node is the *end* of the §3.14 GENERATIONS arc (decision log C19), and it ships the uncertainty honestly: gravity thresholds are discovered per save within defensible bounds, never asserted as fact. Anchors are rodent centrifuge/spin studies, not human outcomes.

---

## 5. Player Interaction & UI

### 5.1 R&D screen

- **Layout:** 10 category columns (Propulsion, GNC, Power, ISRU, Industry, Ships, Habitats, Life Support, Vehicles, Science) × 5 tier rows (T0 bottom → T4 top). Nodes are cards with: name, SCI cost (post-discount, struck-through original if discounted), ED threshold chips colored green/red per family status, prerequisite edges drawn as vector splines.
- **Fog:** hidden nodes render as "???" silhouettes (§3.8). T4 row carries a persistent `[SPECULATIVE]` watermark and a one-line honesty note on hover (§4.13 text).
- **Transparency rule (project-wide):** every node tooltip shows the *actual* formula values: current `m(D_f)` per family, exact discount arithmetic, which Discovery gated it. No hidden math — this is an engineering sim.

### 5.2 Engineering Data dashboard

- Per-family panel: progress bar `D_f / C_f`, current maturity multiplier `m(D_f)` (e.g. "×1.35 failure rate"), accrual rate breakdown (units operating, √N damping, M_env bonuses active), DATA SATURATED flag, and a failure ledger (investigated vs. lost — with the ED forfeited by uninvestigated failures shown in red; teaching tool).
- Part-type cards show state badge: **PROTOTYPE** (amber, ×3 cost / ×4 failure note), **FLIGHT**, **MATURE** (≥ 600 ED), **REFINED**, **OPTIMIZED**.

### 5.3 Prototyping & test workflow

- Builder (06 VAB) flags first articles with the amber badge and a projected first-failure probability for the planned mission profile (computed from §3.4 stack: `λ_min·m·m_state·m_unit` integrated over profile).
- Test Stand UI (Earth pad free; base workshops per 05): select part type → run rated-duration test → consumes propellant/power/funds (12), accrues ED, clears `m_state` on success, clears `m_unit` burn-in for that unit. A "qualification campaign" macro queues N tests and reports the resulting `m(D_f)`.

### 5.4 Science operations

- **Sample manifest:** per-vessel list of carried samples (type, origin region, *projected* `S_n` — the draw this sample would take if analyzed next from its pool, since `S_n` is assigned at analysis time in analysis order (§3.6), decay timer for cryo items, projected award per analysis path). Drag to lab queue or SRC.
- **Region atlas (03 map layer):** per region, completion bars per activity type (pool remaining), survey status per instrument class, anomaly markers.
- **Discovery codex:** acquired DSC entries with real-science write-ups; pending ones show "what would it take" requirement text (e.g. "return a ≥ 1 m ice core from a permanently shadowed crater").
- **Alerts owned by this doc:** DATA SATURATED, PROTOTYPE FAILURE, FAILURE NOT INVESTIGATED (30-day timer running), SAMPLE THERMAL DECAY, DISCOVERY ACQUIRED, MILESTONE ACHIEVED, NODE AFFORDABLE (opt-in).

### 5.5 Time-warp behavior (13 interface)

ED accrual and observation-campaign trickle integrate analytically under warp (closed-form linear segments; events scheduled at threshold crossings: cap hit, milestone reached, 200-h M_env expiry). Sample decay likewise. No per-tick iteration is permitted in the warp path.

---

## 6. Progression Hooks

The intended research spine (mirrors 02 §6): methalox reuse → cryo depots → lunar ISRU propellant → NTR + fission power → high-power EP + closed-loop ECLSS + autonomy → T4 endgame.

| Act | Tier focus | Science income (typical sources) | Spend targets | ED focus / Discoveries |
|---|---|---|---|---|
| **Act 1 — Earth + LEO** | T0→T1 | LEO/Earth surveys (X=1–1.5), first-milestones, 12's contracts; ≈ 1,500–2,500 SCI | the ~1,400-SCI spine to the Moon: GN-01/02/03, PR-01/02/04/05, SH-01, LS-03 (Σ = 1,390) | KeroloxEngines + CryoFluidMgmt hours from flight rate; first depot ops |
| **Act 2 — Moon** | T1→T2 | lunar regions X=2–4, PSR anomalies, first sample returns (×1.25 path); ≈ 8,000 SCI on a thorough Moon | finish T1 (Σ ≈ 5,100), enter T2: IS-05 chain, PW-04/05, PR-09 | **DSC-01, DSC-02, DSC-03**; MiningMachines + ISRU-Chem hours; NTR test-stand campaign |
| **Act 3 — Mars + NEAs** | T2 | Mars X=5, Phobos/Deimos, C/S-type NEAs, comet option; ≈ 15,000 SCI | bulk of T2 (Σ ≈ 22,300): IS-06, SH-04/05/06, LS-04/05/06/09, VH-04/05 | **DSC-04, DSC-05, DSC-06, DSC-15**; AeroFlight EDL events; Methalox field ops |
| **Act 4 — Belt + Venus** | T2→T3 | belt X=6, M-types, Venus clouds X=6 / surface X=8; ≈ 25,000 SCI | T3 industry/ISRU (IS-13..18, IN-09..13), HB-05, HB-09 (optional Mercury crawler), PW-08/09; **robotic** VH-09 aerostats land at T2 (A6) | **DSC-07, DSC-08, DSC-09, DSC-16**; RoboticsAutonomy + FissionSystems hours |
| **Act 5 — Jupiter/Saturn** | T3→T4 | Europa/Io X=10, Titan/Enceladus X=10–12, oceans X=14; ≈ 40,000+ SCI | finish T3 (Σ ≈ 54,000; incl. LS-10 gravity-biology); open T4 (Σ ≈ 77,000) | **DSC-10..14, DSC-17, DSC-18**; EPThrusters throughput on long hauls |
| **Endgame** | T4* | megaproject milestones, remaining pools | SH-09 victory chain (PR-21/22, IN-14, PW-12) | He3 chain validation; `[SPECULATIVE]` honesty maintained |

**Victory-path guarantee:** SH-09 is reachable via PR-21 (fission-fragment) without any fusion/He3 content, and its discovery prerequisites (DSC-02 chain via IS-20 only applies on the PR-22/PW-12 branch) touch only the Moon. Because researching requires visibility (§3.3 condition 1) and a T4 node is hidden until a T3 node in the same category is researched (§3.8), the audited chain also includes **SH-07 Cycler Architecture** — the SH category's only T3 node — and its prerequisites **GN-07 + HB-06** (≈ 3,300 SCI extra, no Discoveries required, so the geographic claim is unchanged); SH-08 is likewise visibility-gated behind SH-07. Venus, Titan, and Europa content is *optional but lucrative* — discounts and ~40% of total recoverable Science.

**Pacing note:** tier Science sums (T1 ≈ 5,100 / T2 ≈ 22,300 / T3 ≈ 54,000 / T4 ≈ 77,000, after the A6/C19 rebalance) deliberately exceed per-act income until the player pushes outward — the tree *pulls* exploration. ED thresholds independently pull *operations*: you cannot Science your way to an NTR without 500 ED of hydrolox engine hours and 300 ED of reactor time.

---

## 7. Cross-System Interfaces

**Consumes:**
- **01-orbital-mechanics.md** — autopilot program executions (Avionics ED events); mission-event stream (burns, dockings, landings) for milestone detection.
- **02-propulsion.md** — catalog failure-rate floors (p_base/λ0 mature values, §3.14 there); ignition/burn-second events per engine family; wear multipliers (stack under §3.4 here).
- **03-solar-system.md** — science-region partition + exoticism X per region; environment-class tags (M_env); anomaly placement and PSR/lava-tube site definitions; comet/NEA catalogs (with SC-05 reveals).
- **04-resources-isru.md** — sampling hardware behavior (corers, drills, Volatile Oven assay); machine operating-hours telemetry for ISRU-Chem/MiningMachines ED.
- **05-industry-logistics.md** — fabrication hours (prototype ×2 rule applies there); workshop teardown + Test Stand modules; robot task-completion events (RoboticsAutonomy ED).
- **06-ships-stations.md** — part build pipeline (prototype ×3 cost applied at build); vessel-loss events (sample pool refund); per-part operating telemetry routing.
- **07-bases-habitats.md** — surface-module operating telemetry (PressureStructures ED); base-site definitions consumed by HB-02/03/04/07 unlock placement.
- **08-life-support-crew.md** — crew hours for lab throughput (GL-1/FL-2/OL-12); crewed-pressurized hours (PressureStructures ED).
- **09-power-thermal.md** — power/thermal part catalogs and operating hours for SolarPower/EnergyStorage/FissionSystems/ThermalControl ED.
- **10-vehicles.md** — km-driven and flight/dive events for SurfaceMobility/AeroFlight ED.
- **12-gameplay-economy-ui.md** — funds for prototypes and test campaigns; contract-based SCI income; R&D campus discount (≤ 20%); difficulty multipliers.
- **13-architecture.md** — deterministic mission-seed RNG; analytic warp integration of accrual/decay.

**Provides:**
- **All sibling docs** — tier/node gating for every part, process, program, module, and autonomy level they define (the master unlock registry, §4.1–4.10).
- **02/05/08/09/10** — the type-maturity multiplier `m(D_f)`, prototype state `m_state`, infant `m_unit` (§3.4) to stack on their failure models; 02's "Mature after 25 ignitions" rule is formally the `D_f ≥ 600` badge of this model.
- **02/06** — Optimized perk flag (−5% dry mass at build time, never retroactive); Mature refurb −25%.
- **03** — Discovery list + acquisition conditions for world placement; survey instrument classes/ceilings.
- **04** — resource-map data layers produced by SC-03 surveys (K2 interplay).
- **05** — maturity upkeep perk (−20% MachineParts at Refined); Silicon Independence event trigger (IN-11).
- **12** — milestone/prestige events, Discovery codex content, victory chain definition (SH-09), Science/ED UI state.

---

## 8. Failure Modes & Edge Cases

| # | Case | Rule |
|---|---|---|
| F-1 | **ED grinding** (fire an engine forever on the pad) | Triple defense: √N concurrency damping, real propellant/funds cost of test stands (12), and the per-family cap `C_f`. Past saturation the UI says so explicitly. |
| F-2 | **Science soft-lock** (player spends all SCI on dead-end nodes, can't afford the spine) | Pools never expire; 12's repeatable survey/delivery contracts provide a guaranteed SCI trickle (≥ 30 SCI/quarter equivalent); milestones on any new body are always available. No node is refundable — but no node is load-bearing *and* missable. |
| F-3 | **Samples lost in transit** (reentry failure, vessel loss) | Pool depletion happens at analysis award, not acquisition (§3.6): destroyed samples return their `S_n` to the pool. Time and hardware are the only losses. |
| F-4 | **Cryo sample decay to zero** | Value floor at 20% of `S_n` (mineralogy survives even if volatiles bake out) — mirrors real degraded-sample science. |
| F-5 | **Prototype death spiral** (first articles keep exploding, budget drains) | Investigated failures pay +25/+40 ED, directly lowering `m(D_f)` for the next article; test-stand qualification is always cheaper than flight failure; 12's insurance/contract systems cushion Act 1. The spiral converges by construction (Crow-AMSAA learning). |
| F-6 | **Parallel prototypes** (build 5 units before any has succeeded) | Only the first article pays ×3; units 2..n built before type success pay ×1.5 and all carry `m_state = 4` until the type's first full-duration success. |
| F-7 | **Family cap after tree completion** (all nodes naming family f researched → C_f frozen) | No special case needed: the §3.2 cap is unconditionally `C_f = max(1.5 · max visible threshold (0 if none), 6 · D_half)`, so every family — including ones named by no threshold anywhere (SolidMotors) — can mature to `m ≤ 1.05` (`m(6·D_half) = 1 + 3·2^(−6) ≈ 1.047`; note 4.5·D_half would only reach m ≈ 1.13). |
| F-8 | **Sequence breaking** (T1 probe attempts an Enceladus flythrough) | Legal and rewarded — Discoveries have no tier locks. T4 visibility still requires a researched T3 node in-category, so lucky discoveries inform but don't skip the ladder. |
| F-9 | **Skipping optional worlds** (no Venus/Titan/Europa ever) | Victory path audited to need only Earth–Moon–Mars–belt content (§6). Optional discovery gates lock only nodes whose *use* requires being there anyway (IS-18 without Venus presence is pointless). |
| F-10 | **M_env hopping** (drag one excavator through every environment for ×3s) | Bonus is per (family, environment class), 200 h each, 7 classes — bounded ~4,200 bonus-hours per family; transport cost self-balances. |
| F-11 | **Failure with no comms** (telemetry-less loss in deep space) | No ED bonus; wreck inspection within 30 days recovers it. Creates a real incentive for relay coverage (GN-03) — intended coupling. |
| F-12 | **Region redefinition across saves** (03 rebalances biomes) | Pools keyed by stable region IDs; orphaned IDs keep their depleted state; new regions spawn fresh pools. Node IDs are stable strings (13 save schema). |
| F-13 | **Discount stacking** | Multiplicative, floor at 40% of base cost: `cost = base · Π(1−d_i)`, clamped ≥ 0.4·base. |
| F-14 | **"Biology question" misread as aliens** | Hard content rule (§4.11): every organics result ships with the abiotic counter-hypothesis in the same codex entry. Marketing copy may not promise life. Fact-checkers welcome. |
| F-15 | **ED threshold orphan** (node requires ED from a family the player owns no parts of) | Audit rule: every ED threshold's family must be accruable from parts unlocked **by a T0 start node or by one of the node's own prerequisite nodes (same tier or lower)**. Two sanctioned patterns: *donor family* — PR-09 draws on HydroloxEngines, not NTRCores; *prerequisite donor* — PR-10/11/12's NTRCores thresholds accrue from NTR-73, unlocked by their common prerequisite PR-09. T0 donors close every first-of-family chain: ION-2/HALL-1 (PR-00) → EPThrusters; PR-00 parametric tanks → CryoFluidMgmt; PW-00 baseline radiators → ThermalControl; VEG-1 (LS-00) → ECLSS-Bio; VH-00 arm task orders → RoboticsAutonomy (§3.2 family table). Enforced by a build-time content lint (13). |

---

## 9. Open Questions

1. **Research time:** unlocks are currently instantaneous on payment (§3.3); prototyping carries the time cost. Should T3/T4 nodes additionally take calendar time at an R&D facility (queue management), or is that tedium the depots already solved?
2. **Crew scientist skill (08):** do scientist crew multiply lab throughput (kg/day) only, or also `M_analysis` (capped at +0.1)? Owned by 08; this doc reserves the hook.
3. **Reliability granularity reconciliation — RESOLVED (DECISIONS A5):** one wear model with **orthogonal, multiplicative** factors and **no double counting** — 02's per-ignition/wear base × this doc's `m(D)·m_state·m_unit` maturity stack × 05's spares/MTBF consumption. The confirmation is recorded in §3.2; A5 mandates it ship as an interface test in Phase 1, which subsumes the joint 02/05/06 pass this question asked for.
4. **Contract science share (12):** what fraction of act-by-act SCI income should contracts provide? Proposal: ≤ 25%, so exploration stays the primary engine.
5. **Partial Discovery credit:** DSC-02 needs 3 mare sites — award 0/partial SCI at 1–2 sites, or all-or-nothing? Proposal: 25% per site, gate releases at 3.
6. **Difficulty knobs:** scale SCI costs (×0.7 / ×1.0 / ×1.3) or scale λ floors? Proposal: never touch λ (realism doctrine); scale costs and contract income only.
7. **Anomaly density:** how many hand-placed anomalies per body before they feel like checklist litter? Needs 03 coordination and playtesting; placeholder budget: 4–10 per major body.
8. **Optimized perk (−5% dry mass):** confirm with 02/06 that build-time-only application survives ship serialization round-trips (13 schema).
9. **He3 kiln logistics reality check:** at 5–20 ppb, 1 kg He3 ≈ 10^5 t regolith moved — does 05's T4 logistics throughput actually support a fusion economy at fun timescales, or does the He3 chain need to lean harder on IS-21 gas-giant scooping?
10. **Era-defining node count per act:** Acts 4–5 currently carry 5 of the 10 era nodes; consider promoting one Act-2 node (candidate: PW-04 Kilopower) to era status for mid-game rhythm.
11. **HB-05 tier vs. conventions (joint with 07) — RESOLVED (DECISIONS A6):** the split the conventions hinted at is now canon — **robotic aerostat platforms are T2** (VH-09, retiered here to T2 / 700 SCI; 07 §4.3.3 helium-cell starters) while the **crewed aerostat habitat HB-05 stays T3** (HAVOC's crewed-phase engineering genuinely exceeds the uncrewed tech). §3.3 and §6 tier sums were rebalanced accordingly (T2 ≈ 22,300 / T3 ≈ 54,000); Act-4 timing is preserved by the DSC-08 gate on both.



