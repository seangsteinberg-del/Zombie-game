# 04 — Resources, Mining & ISRU

Status: DRAFT v1.0 (2026-06-09) — domain: resource taxonomy, prospecting, extraction, ISRU chemistry, propellant production, microgravity mining, tailings, cryo product conditioning.

---

## 1. Overview

This document specifies everything between "rock/ice/gas exists somewhere" (owned by `03-solar-system.md`) and "a tank of usable product exists" (consumed by `02-propulsion.md`, `05-industry-logistics.md`, `06-ships-stations.md`, `07-bases-habitats.md`, `08-life-support-crew.md`). It covers:

- The canonical resource taxonomy: what each resource physically is, how it is stored, and where it genuinely occurs in the solar system.
- The **prospecting chain**: orbital spectrometry → surface survey → core samples → proven ore-grade map. Knowledge quality is a first-class game state; building plants on poorly-surveyed deposits is a real financial gamble, exactly as in terrestrial mining.
- The **extraction catalog**: excavators, ice miners, atmospheric intakes, sea pumps — each with mass / power / throughput a programmer can drop into the simulation.
- **ISRU chemistry** with real reactions and honest simplified mass balances: electrolysis, Sabatier, RWGS, solid-oxide CO2 electrolysis (MOXIE), ilmenite reduction, carbothermal reduction, molten regolith electrolysis, Mond-process carbonyl refining, anorthite-to-Aluminum, Bosch, Haber-Bosch, direct-reduced iron.
- **End-to-end propellant chains** with kWh/kg figures that `09-power-thermal.md` must be able to satisfy.
- **Microgravity mining** (anchoring, bag-and-grind, optical mining), tailings handling, and conditioning/liquefaction of cryogenic products consistent with the boiloff model in `02-propulsion.md`.

Design intent: ISRU is the economic engine of the whole campaign. Earth launch costs (see `12-gameplay-economy-ui.md`) make every kilogram lifted from Earth painful; the player wins by replacing Earth-sourced mass with local mass, in the historically-argued order: **propellant → bulk structure/shielding → metals → chemicals → food → electronics**. Electronics and precision goods stay Earth-dominated until late Act 4 (see `05-industry-logistics.md`).

Simulation philosophy: all production is modeled as **continuous linear flows (kg/s) with explicit mass and energy balance**. No free mass, no free energy. Every recipe in §4 conserves mass to within ±1% (rounding) and states its electric and thermal power demand. Flows integrate analytically under time warp; tank-full / deposit-exhausted / feedstock-starved events are predicted ahead of time and handed to the event scheduler in `13-architecture.md`.

---

## 2. Real-World Grounding

Every mechanic below is anchored to a flown mission, an operating industrial process, or a published engineering study. Key anchors, by domain:

**Prospecting.**
- *Lunar Prospector* Neutron/Gamma-Ray Spectrometers (1998–99): mapped epithermal-neutron suppression (hydrogen in top ~1 m) and thorium (KREEP terrane, up to ~12 ppm Th around Oceanus Procellarum). Footprint of an orbital neutron spectrometer ≈ 1.5× orbital altitude — this drives our survey-resolution rule.
- *LRO LEND*, *Chandrayaan-1 M3* (OH/H2O 3 µm absorption), *MRO CRISM* (hydrated minerals on Mars), *Dawn GRaND* at Ceres, *OSIRIS-REx OVIRS/OTES* at Bennu.
- *LCROSS* (2009): impact plume at Cabeus crater measured **5.6 ± 2.9 wt% water** in PSR regolith, plus CO, H2S, NH3, SO2, light hydrocarbons — our canonical "dirty polar ice" composition.
- *Perseverance RIMFAX* ground-penetrating radar (~10 m depth class) — our surface-survey instrument anchor.
- *TRIDENT* 1-m drill (Honeybee Robotics), flown on the PRIME-1 payload (IM-2 "Athena", 2025) — our core-sampling anchor.
- Resource-confidence ladder borrowed from terrestrial mining codes (JORC / NI 43-101): Inferred → Indicated → Measured → Proven.

**Extraction.**
- NASA KSC Swamp Works *RASSOR* counter-rotating bucket-drum excavator (~66 kg class, ~100 W drive power, design duty around 2.7 t regolith/day) and the follow-on *ISRU Pilot Excavator (IPEx)* — Tier I/II excavator anchors. Specific digging energy ≈ 1 kWh/t follows directly from RASSOR's numbers.
- *Thermal mining* of PSR ice (G. Sowers et al., Colorado School of Mines): capture tent over icy regolith, sublime ice with redirected sunlight, cold-trap the vapor. Our Tier II ice miner.
- Honeybee *PVEx / Planetary Volatiles Extractor* corer (heated coring drill that sublimes ice downhole) — Tier I ice extractor.
- *MOXIE* on Perseverance (2021–23): 17.1 kg, ~300 W, produced O2 from Mars CO2 at 6–12 g/hr, 122 g total — the single most important ISRU flight demo; Tier 0 in our tree, and the anchor for scaled solid-oxide electrolysis (SOXE).
- Mars atmospheric acquisition (cryo-freezing or scroll compression of 610 Pa CO2): D. Rapp, *Use of Extraterrestrial Resources for Human Space Missions* — ~0.4–0.9 kWh/kg CO2.
- NASA *HAVOC* study (Venus aerostats at ~50 km, ~1 atm, ~75 °C) — Venus atmospheric intake context.
- *Cassini-Huygens*: Titan surface 146.7 kPa, 93.7 K, ~94–95% N2 / ~5% CH4 near-surface; Ligeia Mare radar sounding consistent with a methane-dominated sea (~70% CH4, ~12% C2H6, ~17% dissolved N2, Le Gall et al. 2016).
- *ARM* (Asteroid Redirect Mission, cancelled 2017) capture-bag and boulder-grapple studies; JPL **microspine grippers** (100–300 N class on natural rock); TransAstra *Apis* **optical mining** NIAC studies (concentrated sunlight spalling volatiles into a containment bag).

**Chemistry.**
- Water electrolysis: ΔH°(HHV) = 285.8 kJ/mol → theoretical 39.4 kWh/kg H2 = 4.41 kWh/kg H2O; modern PEM stacks run ~50 kWh/kg H2 (~79% HHV efficiency). ISS OGA is the flight anchor.
- Sabatier: CO2 + 4H2 → CH4 + 2H2O, ΔH = −165 kJ/mol, Ni/Ru catalyst, 300–400 °C — flown on ISS (CDRA/Sabatier assembly).
- RWGS: CO2 + H2 → CO + H2O, ΔH = +41 kJ/mol, ~700–900 °C.
- Solid-oxide CO2 electrolysis: 2CO2 → 2CO + O2, ΔH = +283 kJ/mol CO2 (theoretical ≈ 4.9 kWh/kg O2; MOXIE's gram-scale unit ran ~25–50 kWh/kg; scaled-plant studies ~7–12 kWh/kg O2).
- Bosch reaction: CO2 + 2H2 → C(s) + 2H2O, mildly exothermic (≈ −90 kJ/mol), 530–730 °C — studied for ISS CO2 loop closure; our graphite/Carbon source.
- Ilmenite hydrogen reduction: FeTiO3 + H2 → Fe + TiO2 + H2O at 900–1000 °C; releases 1/3 of ilmenite's oxygen (10.5 wt% of ilmenite mass as O2 after electrolysis) — Apollo-era through Artemis-era lunar O2 baseline.
- Carbothermal reduction of regolith with methane (~1600–1800 °C): NASA/Sierra Space *CaRD* vacuum demonstration (JSC, 2023); O2 yields up to ~15+ wt% of regolith.
- Molten Regolith Electrolysis (MRE): MIT (Sadoway; Schreiner & Hoffman system models), ~1600 °C, oxygen evolved on inert anodes, Fe-Si metal at the cathode; modeled specific energies ~25–50 kWh/kg O2.
- Mond / carbonyl metallurgy: Ni + 4CO ⇌ Ni(CO)4 (40–80 °C, ~100 kPa; decomposes 180–250 °C); Fe + 5CO ⇌ Fe(CO)5 (~150–200 °C, 6–20 MPa). Industrial since 1902 (INCO Clydach refinery). Proposed for M-type asteroid NiFe by J. S. Lewis (*Mining the Sky*) — gas-phase, gravity-insensitive, leaves a PGM-rich residue.
- Lunar anorthite (CaAl2Si2O8, 19.4 wt% Al) → Aluminum: carbochlorination / molten-salt electrolysis concepts in NASA SP-509 *Space Resources*; Earth Hall-Héroult reference 12.5–15 kWh/kg Al (we charge more on the Moon).
- H2 direct-reduced iron: Fe2O3 + 3H2 → 2Fe + 3H2O (HYBRIT pilot, ~3.5 MWh/t crude steel including H2 production).
- Solar-grade Silicon: Siemens process, order 100+ kWh/kg polysilicon.
- Cryogenic conditioning: industrial LH2 liquefaction 10–13 kWh/kg (theoretical minimum 3.92); LOX ≈ 0.4–0.6 kWh/kg; LNG ≈ 0.3–0.4 kWh/kg at scale (we charge small-plant penalties).
- He3 in lunar regolith: ~4–20 ppb in mare soils (highest in high-Ti, ilmenite-rich soils; Wittenberg/Kulcinski/Schmitt literature) → ≥100,000 t regolith processed per kg He3. Strictly **[SPECULATIVE]** T4 content.

Honesty flags used throughout: **[SIMPLIFIED]** = real process, deliberately coarse mass balance; **[LUMPED]** = several real species folded into one canonical resource; **[SPECULATIVE]** = T4 physics-sound but far beyond engineering-complete.

---

## 3. Game Model

All formulas use SI. Symbols: `g` = ore grade (mass fraction, 0–1), `Q` = feed throughput (kg/s internally; tables quote t/day or kg/day for readability; 1 t/day = 0.01157 kg/s), `R` = recovery fraction, `P` = power (kW; kWe electric, kWt thermal), `E` = specific energy (kWh/kg).

### 3.1 Deposits (M-1)

Resource occurrences are discrete **Deposit** objects created at world-gen on each body (site list per body in `03-solar-system.md`):

```
Deposit {
  body, site_id            # surface cell / region (07-bases-habitats.md owns surface grid)
  resource                 # canonical resource name (raw form, §4.1)
  tonnage_T  [t]           # remaining extractable mass of the RESOURCE (not of ore)
  grade_g0   [-]           # core mass fraction of resource in feedstock
  r_core     [m]           # radius of peak-grade zone
  depth_class              # SURFACE (0–0.5 m) | SHALLOW (0.5–3 m) | DEEP (3–30 m)
  knowledge_K              # K0..K4 (see M-2)
}
```

Local grade falls off from the deposit center (this *is* the ore-grade map the player ultimately reveals):

```
g(d) = g0 · exp( −(d / r_core)² )            (M-1a)
```

where `d` [m] is extractor distance from deposit center. Extractors sample `g(d)` at their placement point; placement therefore matters even after a deposit is found. Tonnage is decremented by extracted resource mass; when `tonnage_T ≤ 0` the deposit is exhausted (machines idle with an alert). Grade is constant over a deposit's life **[SIMPLIFIED]** — real mines see declining grade; we trade that for predictability.

World-gen rolls per body class (full per-body site lists in `03-solar-system.md`):

```
tonnage_T = 10^U(a,b) t,  grade_g0 ~ triangular(lo, mode, hi) from §4.2 table   (M-1b)
r_core    = 10^U(1.5, 3.0) m   (log-uniform, 30 m – 1 km; independent roll
            per deposit; applies to every §4.2 row — no per-row override)       (M-1c)
```

**Deposit placement.** The deposit center is placed uniformly at random within the site cell (`07-bases-habitats.md` owns the surface grid); `d` in M-1a is the extractor's distance from that center, measured in the same surface grid. **Bulk-body deposits** (rows marked "bulk" in §4.2 — whole asteroids, Phobos/Deimos) have no center: `g(d) = g0` everywhere on the body, and the whole body counts as a single site.

Atmospheres and Titan seas are **infinite deposits** (`tonnage_T = ∞`, fixed composition) — honest at campaign scales (Mars' atmosphere holds ~2.5×10^16 kg ≈ 2.4×10^13 t of CO2 at 95% CO2 by mass). Atmosphere and sea "deposits" are **born at K4** (compositions are telescopically known); intake/sea-pump placement has **no K-gate** — the K-ladder below applies to solid deposits only.

### 3.2 Prospecting / knowledge ladder (M-2)

Knowledge states per deposit, named after terrestrial resource codes (JORC / NI 43-101):

| K | Name | How obtained | Grade error σ_K | Tonnage error | Unlocks |
|---|------|--------------|------------------|---------------|---------|
| K0 | Unknown | — | hidden | hidden | nothing shown |
| K1 | Inferred | orbital spectrometry pass (M-2a) | 0.50 | order-of-magnitude band | deposit icon + rough grade |
| K2 | Indicated | surface rover traverse w/ neutron spec + GPR (microgravity: station-keeping survey, see below) | 0.25 | ±50% | Tier I extractors placeable |
| K3 | Measured | ≥5 core samples (drill, 6 h each; microgravity: anchored corer, see below) | 0.10 | ±20% | Tier II plants placeable; ore-grade map revealed (M-1a contours) |
| K4 | Proven | 30 days of pilot extraction on-site | 0.02 | ±5% | Tier III plants placeable; deposit bankable as loan collateral (`12-gameplay-economy-ui.md`) |

Displayed estimate at state K (rolled once per state transition, *not* re-rolled — players can't savescum-by-staring):

```
ĝ_K = g0 · exp(ε),  ε ~ N(0, σ_K²)          (M-2b)
UI shows ĝ_K with a ±1σ band.

T̂_K = tonnage_T · exp(ε_T),  ε_T ~ N(0, σ_T,K²)          (M-2c)
σ_T,K = {1.15, 0.41, 0.18, 0.05} for K1..K4
(≈ ×10 order-of-magnitude band, ±50%, ±20%, ±5%)
```

Both estimates are rolled once per state transition, never re-rolled. The K4 tonnage estimate T̂_K4 is the "bankable collateral" value used by `12-gameplay-economy-ui.md`. Production always uses **true** `g`. A player who builds a methalox plant on an Indicated (K2) ice deposit may discover the field runs 40% lean. This is intended.

**Orbital survey (K0→K1).** Requires a powered survey instrument (§4.3) on a vessel orbiting below `h_max`. Neutron/gamma instruments need long signal integration (Lunar Prospector mapped for months); footprint ≈ 1.5 × altitude:

```
T_K1 = max( 6 h,  10 d · sqrt(R_body / 1738 km) ),  valid while h ≤ h_max   (M-2a)
h_max = max( 25 km,  150 km · R_body / 1738 km )
```

For small bodies (`R_body < 50 km`) closed orbits inside `h_max` may not exist or are impractically slow; powered station-keeping within `h_max` of the body counts as "orbiting" for M-2a purposes. (2D note: in our planar world an orbiter overflies every longitude each body rotation, so coverage is purely an integration-time gate. We state this honestly rather than faking swath geometry.) Progress accrues only while the instrument is powered (0.1–0.45 kWe per §4.3) and the vessel is below `h_max`. All orbital instruments use the same `T_K1`; each instrument accrues progress independently for its own resource classes (§4.3), and two copies of the same instrument do **not** stack. Completing K1 reveals **all** deposits on the body whose resource class the instrument can see (table §4.3) at K1 confidence.

**Surface survey (K1→K2).** A rover (`10-vehicles.md`) carrying the Surface Survey Package drives to the site: 2 days on-site + 1 day per 10 km traverse from landing point. GPR resolves `depth_class`.

**Core sampling (K2→K3).** Core Drill (TRIDENT-class, §4.3) takes 5 samples × 6 h, each ≥ depth_class floor (DEEP deposits need the Tier II 10-m drill). Reveals the M-1a grade contour map.

**Microgravity equivalents (asteroids, Phobos/Deimos, comets).** Rovers cannot traverse milligravity rubble piles, so the surface steps map onto ship/robot operations:
- **K1→K2:** any ship or robotic vehicle (`06-ships-stations.md` / `10-vehicles.md`) station-keeping ≤ 1 km from the body with a powered Surface Survey Package for 2 cumulative days (no traverse term).
- **K2→K3:** 5 core samples × 6 h by a Core Drill mounted on an anchored platform; the drill's 100 N tool reaction force must satisfy the M-6.1 anchor rule (one microspine pad suffices: 100 N ≤ 0.5 × 250 N).
- The whole body counts as a **single site**, consistent with the §4.2 "bulk body" deposit rows; K-states apply body-wide.

**Pilot extraction (K3→K4).** Any Tier I extractor running on the deposit for 30 cumulative days (microgravity included — a bagged or anchored extractor qualifies).

### 3.3 Extraction (M-3)

Every extractor has feed throughput `Q_feed` (raw regolith/ice-bearing material, gas, or liquid), recovery `R_tier`, and produces:

```
ṁ_product = Q_feed · g(d) · R_tier                  (M-3a)
ṁ_tailings = Q_feed − ṁ_product                     (M-3b)   # mass conserved, see M-8
P_draw = P_fixed + e_dig · Q_feed                   (M-3c)
```

Canonical recoveries: **R = 0.60 (Tier I), 0.75 (Tier II), 0.90 (Tier III)**. Tier I/II/III here ≡ the machine tech tiers T1/T2/T3 used in the catalogs and `11-research-tech.md`; **T4 machines use R = 0.90 unless their catalog entry overrides it** (the He3 Volatile Kiln's R = 0.70 is a deliberate override, §4.4). Specific digging energy `e_dig` = 1.0 kWh/t loose regolith (RASSOR anchor), ×3 for ice-cemented PSR regolith (cryogenic icy soil has concrete-like strength), ×2 wear multiplier on maintenance (see M-9).

**Bulk Regolith rule.** Plain Regolith (unprocessed mineral mass) is extractable at **any** surface site without a Deposit object: treat `g = 1.0`, `R` = tier recovery, tonnage unlimited at site scale. The Deposit/K-ladder machinery applies only to resources that are *concentrated* somewhere.

**Thermal water extraction energy is grade-dependent** (this is the main way grade bites). Heating gangue is wasted energy; subliming ice at ~0 °C costs 2.83 MJ/kg, warming regolith (cp ≈ 0.8 kJ/kg·K) through ΔT ≈ 200 K costs 0.044 kWh/kg gangue:

```
E_water(g) = [0.79 + 0.044 · (1/g − 1)] / η_th   kWh per kg H2O      (M-3d)
η_th = 0.5 (Tier I), 0.7 (Tier II), 0.85 (Tier III, heat recuperation)
```

Examples: g = 5% → 2.3 kWh/kg (Tier II); g = 1% → 7.4 kWh/kg; g = 50% (Mars massive ice) → 1.2 kWh/kg. Add **0.1 kWh/kg water-cleanup** (deionization/distillation) because PSR ice is dirty (LCROSS: CO, H2S, NH3, SO2 contaminants) — contaminants exit as a fraction `f_c` of water mass into a vent/sour-gas stream, with **f_c ~ U(0.02, 0.08) rolled once per Water deposit at world-gen** (stored on the Deposit). Sour-gas composition is fixed **[SIMPLIFIED, LCROSS-derived]**: CO2 0.45 / NH3 0.20 / H2S 0.15 / SO2 0.10 / light hydrocarbons 0.10 by mass; a Fractionator (RX-13) recovers the CO2 and Ammonia fractions, the remaining 0.35 is flared (M-8, F-11).

**Atmospheric intake (M-3e).** Intake mass flow is displacement × ambient density × species fraction:

```
ṁ_i = V̇ · ρ_atm · x_i ;   ideal compression work W = R_s T ln(P_out/P_in), real ×4
P_out = 100 kPa (canonical tank delivery pressure, all sites)
```

Canonical ambient densities (datum values; `03-solar-system.md` owns site/season variation):

| Location | P | T | ρ_atm | Composition (mass-relevant) | Intake energy (game) |
|---|---|---|---|---|---|
| Mars surface (datum) | 0.61 kPa | 210 K | 0.016 kg/m³ | CO2 96.0%, Ar 1.93%, N2 1.89% (MSL SAM, molar) **[SIMPLIFIED — molar fractions applied as mass fractions]** | 0.6 kWh/kg gas (Intake I), 0.4 (Intake II) — both T2 cryo-freezers (Rapp; IS-06 unlock, `11-research-tech.md`) |
| Venus aerostat, 52–56 km | ~50–100 kPa | 290–340 K | ~0.9–1.5 kg/m³ | CO2 96.5%, N2 3.5% **[SIMPLIFIED — molar fractions applied as mass fractions]** | 0.07 kWh/kg |
| Titan surface | 146.7 kPa | 93.7 K | 5.3 kg/m³ | N2 ~94.5%, CH4 ~5% (near-surface, Huygens) | 0.01 kWh/kg (already cold & dense) |

Delivery state depends on intake type: **Mars cryo-freezer intakes (I & II, both T2 — gated by IS-06 behind discovery DSC-04, `11-research-tech.md`) deliver pure CO2 directly** (CO2 desublimes at 145 K; the other species don't) **plus a residual Ar/N2 mixed-gas stream (4% of throughput)** that requires a Fractionator to split; **Venus and Titan ram intakes deliver mixed gas** requiring fractionation. Separation of any mixed-gas stream into canonical resources requires a Fractionator (§4.5, RX-13) at 0.25 kWh/kg processed. Mars intakes consume 1 HEPA filter cartridge (MachineParts ledger, `05-industry-logistics.md`) per 100 t gas due to dust (MOXIE precedent).

**Liquid intake (Titan seas) (M-3f).** Sea Pump draws bulk liquid at fixed Q; composition (Ligeia-class): CH4 0.71, C2H6 0.12, N2 0.17 by mass **[SIMPLIFIED — molar estimates applied as mass fractions]**. Fractionation splits N2 out; ethane is **[LUMPED]** into Methane at 0.93 kg CH4-equivalent per kg C2H6 (similar C/H energy content; engines in `02-propulsion.md` see one "Methane" propellant). Kraken-class seas roll ethane-richer (CH4 0.45/C2H6 0.40/N2 0.15).

### 3.4 Chemical plants (M-4)

Every plant runs one **recipe** (RX-nn, §4.5) defined by: input rates, output rates (mass-balanced), electric power `P_e`, thermal power `P_t` (positive = needs process heat; negative = waste heat to radiators — `09-power-thermal.md` owns rejection), operating temperature, and tier. Plants scale linearly with a `utilization` ∈ [0,1] set by feedstock/storage/power availability:

```
actual_rate = nominal_rate · utilization                                     (M-4a)
utilization = min( P_avail / P_req,
                   min over inputs i  ( feed_rate_avail_i / feed_rate_req_i ),
                   min over outputs j ( storage_drain_capacity_j / output_rate_j ) )
```

Each of the three terms is clamped to [0,1] before the min; `i` ranges over **all** input streams and `j` over **all** output streams (a full output tank with zero drain stalls the whole plant — no selective venting unless the recipe says so). Evaluated once per scheduler tick (`13-architecture.md`).

Plants below 30% utilization for >24 h flag an efficiency alert (real chemical plants hate throttling; we model it only as the alert + 2× maintenance below 30% **[SIMPLIFIED]**).

### 3.5 Conditioning & cryo handoff (M-5)

Gaseous products must be liquefied before they enter `02-propulsion.md` tankage. Canonical liquefaction energies and storage states (these numbers are shared canon with 02 and 09):

| Product | Stored as | T_store | ρ_liquid | E_liquefy (kWh/kg) |
|---|---|---|---|---|
| Hydrogen | LH2 | 20 K | 70.8 kg/m³ | 12.0 (industrial 10–13; theoretical 3.9) |
| Oxygen | LOX | 90 K | 1141 kg/m³ | 0.7 |
| Methane | LCH4 | 112 K | 423 kg/m³ | 0.8 |
| Nitrogen | LN2 | 77 K | 808 kg/m³ | 0.8 |
| CO2 | liquid, 2 MPa | 220 K | 1170 kg/m³ | 0.15 |
| Ammonia | liquid, 1.2 MPa | 300 K | 600 kg/m³ | 0.05 |
| Argon | liquid | 87 K | 1395 kg/m³ | 0.6 |
| Xenon | supercritical, 12 MPa | ambient | ~1100 kg/m³ | 0.3 |
| Water | liquid/ice | any | 1000 kg/m³ | 0 |

(NH3 stored at 1.2 MPa because P_sat(300 K) ≈ 1.06 MPa — 1 MPa at 300 K would be on the gas side of the vapor curve.)

**Liquefaction hardware:** liquefaction is performed by the buildable **Cryo Liquefaction Skid** (§4.4), at the E_liquefy values above. The 0.1 kWh/kg water-cleanup step (M-3d) needs **no** separate machine — it is integrated into the ice extractors and already charged in the M-3d examples and §4.6 chains.

**Zero-boiloff (ZBO) cryocooler rule (shared with 02-propulsion.md):** to hold a tank with environmental heat leak `Q_leak` [W] at temperature T, input power is

```
P_ZBO = Q_leak · k(T) ;  k(20 K) = 80 We/Wt, k(77–90 K) = 12, k(112 K) = 10    (M-5a)
```

(reverse turbo-Brayton state of the art). Without ZBO, boiloff %/day comes from 02-propulsion's tank table; vented boiloff is *destroyed mass* unless routed to a use (cold-gas RCS, habitat O2). **Transfer ullage loss: 1.5% of transferred cryogen per transfer, 0.3% with a vapor-return line** (depot equipment, T1 tech).

### 3.6 Microgravity mining (M-6)

Surface gravity of a small body: `g_ast = (4/3)π G ρ r` — for a 500 m diameter, ρ = 2000 kg/m³ rubble pile: g = 1.4×10⁻⁴ m/s², v_esc ≈ 0.26 m/s. Consequences modeled:

1. **Anchoring requirement.** Any surface tool must react its forces. Anchor capacities: microspine pad 250 N (JPL anchor), drilled rock-bolt 2000 N (1 h install, monolithic bodies only), full capture bag — unlimited (internal reaction). Tool reaction forces: corer 100 N, enclosed grinder head 500 N, bucket excavator 2000 N. Rule: Σ(tool force) ≤ 0.5 × Σ(anchor capacity), else tool refuses to run.
2. **Bag-and-grind.** Bodies ≤ 20 m diameter (≈ 10⁴ t at ρ 2000) can be fully enclosed by a Capture Bag (ARM Option A heritage) and ground up inside it: recovery R +0.10, zero debris. Larger bodies use anchored, shrouded grinder heads.
3. **Debris rule.** Unenclosed regolith handling in g < 0.01 m/s² loses 15% of throughput as escaping debris and increments a local debris-hazard counter (micrometeoroid-equivalent damage rate ×3 for ships within 1 km; `06-ships-stations.md` damage model).
4. **Spin barrier.** Real rubble piles cannot spin faster than ~2.2 h period. Bodies generated with P_rot < 2.2 h are monolithic (rock-bolt anchors allowed, microspines at half capacity). Optional despin: angular momentum L = I·ω must be removed by thrusters at lever arm r: `m_prop = I·ω / (v_e · r)` — for a 10 m, 1000 t monolith at P_rot = 4 h, despun via thruster at r = 5 m with v_e = 3000 m/s: I ≈ 10⁷ kg·m², ω = 4.4×10⁻⁴ s⁻¹ → m_prop ≈ 0.3 kg (cheap — the rule exists for realism flavor, the cost is the EVA/robot time: 8 h setup).
5. **Optical mining (T3).** Concentrated sunlight (inflatable reflector) spalls and devolatilizes bagged C-type material directly: replaces excavator+oven with one machine; thermal power is free sunlight scaled by `1/d_AU²` (TransAstra Apis anchor).

### 3.7 Propellant chain headline energies (M-7)

End-to-end specific energies the power system must budget for (derivations in §4.6; **these are the canonical cross-check numbers for `09-power-thermal.md`**). Basis: **all figures below include liquefaction to the M-5 storage state** (Water needs none):

```
Mars methalox (CO2 + buried ice → LCH4 + LOX, O/F 3.6):   ≈ 7.1 kWh per kg propellant
Moon hydrolox (5%-grade PSR ice → LH2 + LOX, O/F 6.0):    ≈ 12.6 kWh per kg propellant
LOX alone via molten regolith electrolysis (anywhere):     ≈ 35.7 kWh per kg LOX (35 MRE + 0.7 liquefaction)
LOX alone via SOXE from Mars CO2 (scaled MOXIE):           ≈ 9.8 kWh per kg LOX (8 SOXE + 1.1 acquisition + 0.7 liquefaction)
Water from C-type rubble (8% grade, bake-out):             ≈ 2.3 kWh per kg H2O
```

Worked sizing example (canon, quoted in 09 and 12): **fueling a 100 t methalox ascent vehicle in 500 days requires 200 kg/day × 7.1 kWh/kg ≈ 59 kWe continuous** — one 100 kWe-class fission unit (T2) or ~0.4 ha of Mars solar with dust margin.

### 3.8 Tailings & waste (M-8)

`ṁ_tailings` (M-3b) accumulates as a **Tailings pile** entity at the site (or bagged mass in microgravity). Rules:

- Tailings convert 1:1 to the canonical resource **Regolith** for downstream use: radiation shielding fill (`07-bases-habitats.md` wants 2–3 t/m² overhead), sintered roads/pads, basalt feed (RX-17), or mass-driver slugs (`05-industry-logistics.md` T3 mass driver §3.8 and its pelletizer §4.5 — 05 owns both).
- Piles occupy site capacity: 1 pile slot per 10,000 t; a site has finite slots (per `07-bases-habitats.md` grid). Full slots stall extractors — the player must plan waste logistics like a real mine.
- In microgravity, unbagged tailings jettison is allowed but triggers the debris rule (M-6.3). Bagged tailings are legitimate cargo (shielding mass for `06-ships-stations.md` crew vessels).
- Sour-gas streams (ice cleanup contaminants, carbonyl purge) are flared (destroyed) unless a Fractionator captures them.

### 3.9 Maintenance & dust (M-9)

Every machine consumes **MachineParts at 0.0008 × machine_mass per day** (≈ 0.08%/day; a 3 t plant eats 2.4 kg/day) — the ledger lives in `05-industry-logistics.md`. Multipliers: ×2 lunar surface (abrasive, electrostatically-charged dust — Apollo anchor), ×2 PSR ice digging (M-3), ×2 Venus aerostat external equipment (H2SO4 aerosol corrosion), ×0.5 inside pressurized workshops. A machine starved of MachineParts degrades: utilization cap falls 2%/day until serviced (floor 20%).

---

## 4. Content Catalog

### 4.1 Resource taxonomy

Canonical names only. "Form" = how the sim stores/moves it. Occurrence ties to `03-solar-system.md` body data.

| Resource | Form / storage | Physical-chemical notes | Real occurrence (primary → secondary) |
|---|---|---|---|
| Water | liquid/ice tank | universal feedstock; 0.888 kg O2 + 0.112 kg H2 by electrolysis | Earth; Moon PSRs (LCROSS 5.6±2.9 wt%); Mercury PSRs (MESSENGER radar-bright ice, purer than lunar — §4.2); Mars mid-latitude buried ice (SWIM, 30–90 vol% ≈ 0.17–0.81 by mass, see §4.2) & poles; C-type asteroids (5–20 wt% bound in phyllosilicates); Ceres crust; icy moons (Europa, Enceladus, Titan's bedrock IS water ice; Ganymede/Callisto dirty ice-rock crusts — §4.2 icy-crust class rows) |
| Oxygen | LOX 90 K | 86% of hydrolox mass, 78% of methalox — the bulk prize | electrolyzed Water; Mars CO2 (MOXIE); 43–45 wt% of any silicate regolith (MRE/carbothermal) |
| Hydrogen | LH2 20 K | hardest cryogen (20 K, ρ 70.8); leaks, embrittles | Water electrolysis; solar-wind H in regolith (~50–150 ppm, byproduct only); gas giants [T4] |
| Methane | LCH4 112 K | space-storable-ish; Raptor-class fuel | Sabatier product (Mars); Titan atmosphere ~5% / seas ~70%; traces in comets/C-types |
| Nitrogen | LN2 / GN2 | buffer gas (habitats need ~78 kPa-equivalent inventories), fertilizer | Earth; **Titan (94.5% of the 146.7 kPa (1.45 atm) atmosphere — the system's N reservoir)**; Venus 3.5% (huge absolute column); Mars 1.9%; NH3 ices/salts on Ceres & comets; Triton N2 ice & Pluto's Sputnik Planitia glacier (endgame N2-ice reservoirs, §4.2) |
| CO2 | liquid 220 K / gas | Mars & Venus atmospheres are infinite deposits | Mars 96%, Venus 96.5%; Ceres/comet ices; combustion/respiration loops (`08-life-support-crew.md`) |
| Ammonia | liquid 300 K/1.2 MPa | N-carrier, fertilizer, coolant, NTR propellant option | Haber synthesis; Ceres ammoniated phyllosilicates (Dawn); comet/KBO ices; LCROSS plume trace |
| Argon | liquid 87 K | Hall/MPD thruster propellant (cheaper than Xenon) | Mars atmosphere 1.93% (byproduct of CO2 acquisition); Titan trace |
| Xenon | supercritical 12 MPa | premium EP propellant, 0.087 ppm in Earth air — always scarce | Earth air separation (import); Mars atmosphere 0.08 ppm molar ≈ 0.24 ppm by mass (Viking GCMS, Owen et al. 1976) — same mixing ratio as Earth air but throughput-uneconomic (F-15) |
| Regolith | bulk pile | unprocessed mineral mass; shielding 2–3 t/m²; sinter feed | every solid body; also = tailings (M-8) |
| IronSteel | ingot | **[LUMPED]**: Fe + Ni + Co alloys incl. carbonyl-pure Fe/Ni | M-type asteroids (Fe 85–92%, Ni 5–10%, Co ~0.5% — Psyche-class); ilmenite-reduction byproduct (Moon); Mars hematite/magnetite via H2-DRI |
| Aluminum | ingot | light structure; lunar highlands specialty | anorthite CaAl2Si2O8 = 19.4 wt% Al, highlands 75–95% plagioclase; Earth |
| Titanium | ingot | from ilmenite TiO2 slag; FFC-Cambridge reduction (T3) | high-Ti lunar mare (soil TiO2 up to ~8–10 wt%); Earth |
| Copper | ingot | conductors; **genuinely rare off Earth** (hydrothermal concentration is an Earth/Mars luxury) | Earth; rare Mars hydrothermal deposits (Act 3, low tonnage); trace sulfides in M-types |
| Silicon | ingot (met./solar grade) | MRE & carbothermal byproduct; solar-grade costs ~120 kWh/kg (Siemens anchor) | any silicate regolith (~21 wt% Si) |
| RareEarths | ingot/oxide | **[LUMPED]**: REE + PGM + other scarce metals (honest lump, flagged in UI) | Earth; lunar KREEP terrane (Th-tracked); M-type carbonyl residue (PGM 10–100 ppm) |
| Uranium | oxide/fuel rod | fission fuel; space grades are *bad* (KREEP ~2–3 ppm U vs Earth ores 1000+ ppm) | Earth import until T3; lunar KREEP; Mars trace |
| Thorium | oxide | breeder fuel (T3 molten-salt path, `09-power-thermal.md`) | lunar KREEP (up to ~12 ppm, Lunar Prospector); Earth |
| Pu238 | RTG pellet | 0.57 W/g decay heat; made from Np-237 irradiation, not mined | Earth (Oak Ridge line, ~kg/yr scale); T3 player production in fission reactors |
| Carbon | graphite/powder | Bosch product; reductant, electrodes, carbonyl makeup | C-type asteroids (2–5 wt% organic C); CO2 atmospheres; Titan hydrocarbons |
| Polymers | pellets | PE-class **[LUMPED]** plastics from CH4 + O2 | synthesized in `05-industry-logistics.md` (`polymers_mto`, RX-15 alias — 04 supplies the Methane/Oxygen feedstocks); Titan hydrocarbons feedstock paradise |
| BasaltFiber | spool | melt-spun regolith/basalt, 1400 °C; rebar/fabric (terrestrial industry anchor) | any basaltic regolith (mare, Mars plains) |
| Glass | sheet/stock | sintered/melted silica-rich regolith; habitat glazing w/ metal frames | any silicate regolith |
| Electronics | crate | NOT ISRU-producible until late game; see `05-industry-logistics.md` fab chain | Earth import → T3 fab (needs Silicon solar-grade, Copper, RareEarths, Polymers) |
| MachineParts | crate | bearings, seals, motors; the maintenance currency (M-9) | Earth import → machined locally from IronSteel/Aluminum (05) |
| StructuralParts | beam/panel | extruded/printed structure | from IronSteel/Aluminum/BasaltFiber (05) |
| FoodRations | crate | `08-life-support-crew.md` owns diet; we supply inputs | Earth import → greenhouse Biomass chain |
| Biomass | wet mass | crops/algae; needs Water, CO2, Nitrogen (as NH3-fertilizer), light | grown (08); C-type organics are NOT food (kerogen-like) |
| He3 | gas bottle | **[SPECULATIVE]** fusion fuel; ~4–20 ppb in mare regolith; ≥10⁵ t regolith per kg | lunar high-Ti mare (solar-wind implanted); gas-giant atmospheres (T4 endgame) |

### 4.2 Regional ore-grade table (world-gen inputs to M-1b)

Grades are mass fractions of the named resource in raw feed. lo/mode/hi for triangular roll. `r_core` for every row is rolled per M-1c (no per-row override); rows marked "bulk" are bulk-body deposits with uniform grade (no center, no `r_core`).

**Coverage note (binds 03 §7's 1:1 mandate):** this table is the canonical world-gen input (M-1b); `03-solar-system.md` §4.4's per-body deposit-roll hooks MUST resolve 1:1 to rows here. Outer-system and Mercury assignments in 03's key-resource column resolve as follows: Mercury polar Water → the Mercury PSR row; Europa, Enceladus, Titania/Oberon/Miranda, Charon, and Pluto/Triton water-ice bedrock → the *clean icy-crust class* row; Ganymede and Callisto → the *dirty icy-crust class* row; Triton N2 ice and Pluto's Sputnik Planitia → their named N2-ice rows. Class rows roll one deposit set per body exactly as named-body rows do.

| Body / region (03-solar-system.md) | Resource (raw form) | lo / mode / hi grade | Tonnage 10^(a..b) t | Depth | Anchor |
|---|---|---|---|---|---|
| Moon — PSR floors (Cabeus-class) | Water (ice-cemented regolith) | 0.01 / 0.055 / 0.10 | 4..7 | SHALLOW | LCROSS 5.6±2.9 wt% |
| Moon — high-Ti mare | Ilmenite→(Oxygen, IronSteel, Titanium) | 0.05 / 0.10 / 0.15 (ilmenite in soil) | 6..8 | SURFACE | Apollo 11/17 soils |
| Moon — highlands | Anorthite→(Aluminum, Silicon, Oxygen) | 0.75 / 0.85 / 0.95 (plagioclase) | 7..9 | SURFACE | anorthositic crust |
| Moon — KREEP (Procellarum fringe) | Thorium / Uranium ore | 6/9/12 ppm Th; U = 0.27×Th | 5..6 | SURFACE | Lunar Prospector GRS |
| Moon — high-Ti mare | He3 [SPECULATIVE] | 4 / 10 / 20 **ppb** | 6..8 | SURFACE | Wittenberg/Kulcinski |
| Mercury — PSR floors (Prokofiev/Kandinsky-class) | Water (radar-bright ice under thin organic lag) | 0.50 / 0.80 / 0.95 | 7..10 | SURFACE (lag ≤ 0.3 m) | MESSENGER radar-bright polar deposits, 10^10–10^12 t system total — purer than lunar PSR ice; grade roll quoted by `07-bases-habitats.md` §4.3.8 |
| Mars — mid-latitude ice (SWIM zones) | Water (excess ice) | 0.17 / 0.45 / 0.81 | 5..8 | SHALLOW–DEEP | SWIM, SHARAD report 30–90 **vol%** excess ice; converted to mass fraction at ρ_ice 0.92 t/m³ in a ~1.7–2.0 t/m³ regolith matrix |
| Mars — hydrated minerals (equatorial) | Water (gypsum/smectite) | 0.03 / 0.06 / 0.10 | 6..8 | SURFACE | CRISM |
| Mars — hematite/magnetite plains | IronSteel ore (Fe-oxides) | 0.10 / 0.18 / 0.30 (as Fe) | 6..8 | SURFACE | Meridiani hematite |
| Mars — rare hydrothermal sites | Copper ore | 0.002 / 0.005 / 0.02 | 4..5 | SHALLOW | Jezero-class paleo-hydrothermal (sparse by design) |
| Mars/Venus/Titan atmospheres | CO2/N2/Ar; CO2/N2; N2/CH4 | fixed composition (M-3e) | ∞ | — | Viking/MSL, Venera, Huygens |
| Titan — seas (Ligeia-class) | Methane (+[LUMPED] ethane) | fixed: CH4 .71/C2H6 .12/N2 .17 | ∞ | LIQUID | Cassini radar |
| Icy-crust class, clean — Titan bedrock, Europa, Enceladus, Titania/Oberon/Miranda, Charon, Pluto/Triton water-ice bedrock | Water (ice crust) | 0.85 / 0.95 / 1.0 | ∞-ish (8..10) | SURFACE | bulk ice crusts (Cassini, Galileo, Voyager 2, New Horizons); the Enceladus surface-ice "grade 0.95+" quoted by `07-bases-habitats.md` §4.3.6 is this row |
| Icy-crust class, dirty — Ganymede, Callisto | Water (ice-rock mixed crust) | 0.40 / 0.60 / 0.80 | ∞-ish (8..10) | SURFACE | Galileo bulk densities (~half ice, half rock); Callisto is the HOPE crew-staging site (07 §4.3.5) |
| Triton — N2 ice plains & polar cap | Nitrogen (N2 ice; CH4/CO frost traces) | 0.70 / 0.85 / 0.95 | ∞-ish (9..12) | SURFACE | Voyager 2; 38 K cold-trap sublimation mining, product conditioned per M-5 cryo rules; the system's last big N reservoir after Earth/Titan/Ceres (03 §4.4.12) |
| Pluto — Sputnik Planitia | Nitrogen (convecting N2-ice glacier; CH4/CO traces) | 0.85 / 0.93 / 0.98 | ∞ (infinite-class per 03 §4.4.13) | SURFACE | New Horizons; volatile handling at 38 K per M-5 — slow extraction by design (endgame logistics, not chemistry) |
| NEA / belt — C-type | Water (phyllosilicate-bound) | 0.05 / 0.08 / 0.20 | 3..7 | bulk body | CI/CM chondrites; Ryugu/Bennu samples |
| NEA / belt — C-type | Carbon (organics) | 0.02 / 0.03 / 0.05 | same body | bulk | CI chondrite C content |
| NEA / belt — C-type | Nitrogen (NH3-salts/organics) | 0.001 / 0.003 / 0.005 | same body | bulk | Bennu ammonia-bearing samples |
| NEA / belt — S-type | IronSteel (NiFe grains) | 0.05 / 0.10 / 0.20 | 4..7 | bulk | ordinary chondrites |
| NEA / belt — M-type | IronSteel (massive NiFe) | 0.50 / 0.80 / 0.95 | 5..9 | bulk | Psyche-class (density-inferred metal fraction 30–60%+; we roll high-metal members honestly rare) |
| M-type — carbonyl residue | RareEarths [LUMPED PGM] | 10 / 40 / 100 ppm of metal mass | from metal | — | Kargel 1994 PGM estimates |
| Ceres — crust | Water ice | 0.20 / 0.30 / 0.45 | 8..10 | SHALLOW | Dawn GRaND H map |
| Ceres — clays | Ammonia (ammoniated phyllosilicates) | 0.005 / 0.01 / 0.02 | 6..8 | SURFACE | Dawn VIR |
| Phobos/Deimos | Water (uncertain!) | 0.00 / 0.02 / 0.05 (may roll ZERO — survey before committing) | 5..7 | SHALLOW | composition genuinely unresolved |

### 4.3 Survey instrument catalog

| Instrument | Tier | Mass | Power | Detects (→K state) | Notes / anchor |
|---|---|---|---|---|---|
| Orbital Neutron+Gamma Spectrometer | T0 | 30 kg | 0.10 kWe | H (Water/ice), Th/U/KREEP, Fe → K1 | Lunar Prospector NS/GRS, LEND; needs h ≤ h_max; T_K1 per M-2a |
| Orbital IR/Vis Spectral Mapper | T0 | 25 kg | 0.10 kWe | hydrated minerals, ilmenite, organics, CO2/NH3 ices → K1 | M3, CRISM, OVIRS; surface-composition class only (no depth) |
| Orbital Radar Sounder | T2 | 90 kg | 0.45 kWe | buried ice sheets (DEEP), metal richness of asteroids → K1+depth | SHARAD/MARSIS heritage |
| Surface Survey Package (rover-mounted) | T1 | 40 kg | 0.15 kWe | neutron spec + GPR (10 m) + XRF → K2 | RIMFAX + MSL APXS heritage |
| Core Drill, 1 m | T1 | 30 kg | 0.40 kWe peak | K3 on SURFACE/SHALLOW | TRIDENT / PRIME-1 (IM-2, 2025) |
| Deep Core Rig, 10 m | T2 | 400 kg | 3.0 kWe | K3 on DEEP; prerequisite for Mars Rodwell | terrestrial geotech class |

### 4.4 Extraction machine catalog

"Feed" = raw material moved. Product = feed × g × R (M-3a). Masses include local handling conveyors.

**Catalog power convention (binds M-3c):** the Power column is **total `P_draw` at 100% utilization at the quoted reference grade**; `P_fixed` = 20% of that value, with the remainder covering `e_dig·Q_feed` plus process energy. For grade-dependent water extractors (Thermal Ice Corer, Sublimation Tent Miner, Ice Strip Miner), **power is held fixed and rated output is recomputed from M-3d at the actual sampled grade `g(d)`**; all other machines hold throughput fixed and scale `P_draw` per M-3c.

| Machine | Tier | Mass | Power | Feed throughput | Feed type | Notes / anchor |
|---|---|---|---|---|---|---|
| Drum Excavator | T1 | 0.15 t | 0.4 kWe | 2.5 t/day | loose regolith | RASSOR-class; e_dig 1 kWh/t |
| Bucket-Wheel Excavator | T2 | 3 t | 12 kWe | 100 t/day | regolith, ×3 power on icy | IPEx → small terrestrial BWE lineage |
| Strip Miner | T3 | 25 t | 200 kWe | 1,500 t/day | regolith | autonomous fleet-scale |
| Thermal Ice Corer | T1 | 0.25 t | 3.0 kWe (heat) | → 20 kg H2O/day @ g=5% | downhole sublimation | Honeybee PVEx; output scales w/ M-3d |
| Sublimation Tent Miner | T2 | 6 t | 80 kWt + 6 kWe | → 800 kg H2O/day @ g=5% | tented surface patch | Sowers/CSM thermal mining; kWt can come from solar concentrator (09) |
| Ice Strip Miner | T3 | 30 t | 870 kWe | → 10 t H2O/day @ g=5% | excavate+oven integrated | scaled CSM concept; 870 kWe = M-3d (Tier III, g=5%, +0.1 cleanup) + digging 222 t feed/day × 3 kWh/t |
| Mars Rodwell Rig | T2 | 2 t | 25 kWt + 2 kWe | → 1.2 t H2O/day | massive buried ice (g ≥ 0.5) only | Rodriguez well, Antarctic practice; needs Deep Core Rig survey. **M-3d exempt**: Rodwells melt rather than sublime (no vacuum exposure, ~0.13 kWh/kg theoretical) — use the catalog figure of 0.54 kWh/kg H2O, valid only at g ≥ 0.5 |
| Atmospheric Intake (Mars) I | T2 | 0.3 t | 5 kWe | 200 kg/day mixed gas | Mars atmo | cryo-freezer CO2 acquisition (Rapp), 0.6 kWh/kg small-unit penalty; HEPA consumable. T2 — unlocked alongside Intake II at `11-research-tech.md` IS-06 "Mars Atmosphere Processing" (DSC-04 discovery gate); no T1 Mars intake exists |
| Atmospheric Intake (Mars) II | T2 | 1.0 t | 18 kWe | 1,000 kg/day | Mars atmo | 0.4 kWh/kg + Ar/N2 byproduct via Fractionator; same IS-06 unlock |
| Aerostat Intake (Venus) | T3 | 0.5 t | 6 kWe | 2,000 kg/day | Venus 52–56 km | HAVOC platform mount (`07-bases-habitats.md` aerostat); + trace cloud-water harvester 2 kg H2O/day from H2SO4 aerosol (honestly tiny) |
| Atmospheric Intake (Titan) | T3 | 0.3 t | 2 kWe | 5,000 kg/day | Titan atmo | dense cold gas; near-free liquefaction |
| Sea Pump (Titan) | T3 | 0.8 t | 4 kWe | 20 t/day liquid | Titan sea (shore/sub, `10-vehicles.md`) | heated inlet vs icing (F-8) |
| Volatile Bake Oven | T2 | 2 t | 40 kWe-or-kWt | 10 t/day crushed feed | C-type rubble, icy regolith | 500 °C bake; releases Water/CO2/NH3/N2 per grade; pairs w/ Fractionator |
| Capture Bag + Grinder | T2 | 1.5 t | 8 kWe | 15 t/day | whole bodies ≤ 20 m (M-6.2) | ARM Option A heritage; R +0.10 |
| Anchored Grinder Head | T2 | 0.6 t | 5 kWe | 6 t/day | anchored asteroid surface | microspine anchors ×4 included |
| Optical Mining Rig | T3 | 4 t | 1 kWe (+free solar kWt × 1/d_AU²) | 30 t/day @ 1 AU | bagged C-type | TransAstra Apis NIAC; thermal only — no O2 yield from silicates |
| Beneficiation Separator | T2 | 1.5 t | 10 kWe | 50 t/day feed | regolith → concentrate | magnetic/electrostatic, 0.02 kWh/kg feed. Balance: concentrate grade g_c = min(k·g_feed, 0.90) with k = 8 (ilmenite), 10 (NiFe grains); mineral recovery 0.80; concentrate mass = feed·g_feed·0.80/g_c; remainder → tailings (Regolith, M-8). Mare soil at g_feed = 0.10: 50 t/day feed → 5.0 t/day concentrate @ g_c 0.80 (4.0 t contained ilmenite) + 45 t/day tailings |
| Cryo Liquefaction Skid | T1 | 1.2 t | 25 kWe | any gaseous M-5 product | gas → liquid per M-5 | rate = nameplate / E_liquefy: ≈ 50 kg/day LH2, ≈ 860 kg/day LOX, ≈ 750 kg/day LCH4; ZBO cryocoolers are separate (M-5a) |
| Cryo Liquefaction Skid II | T2 | 4.8 t | 113 kWe | any gaseous M-5 product | gas → liquid per M-5 | ×5 throughput at −10% specific energy (plant scaling rule, §4.5) |
| He3 Volatile Kiln [SPECULATIVE] | T4 | 50 t | 400 kWe + 1,600 kWt | 2,000 t/day | high-Ti mare regolith, 700 °C | → 14 g He3/day @10 ppb (R = 0.70, volatile release efficiency at 700 °C — deliberate override of M-3 tier recovery) + byproducts/t: 50 g H2, 20 g He4, 100 g N2, 150 g C (as CO2/CO), 30 g H2O. Budget assumes **~85% counterflow thermal recuperation** (UW Mark-series He3 miner studies) — raw 23 kg/s × ΔT 670 K × cp 0.8 kJ/kg·K would otherwise need ~12.4 MWt |

### 4.5 Chemical plant & recipe catalog

All mass balances conserve mass. `P_t < 0` means exothermic waste heat that `09-power-thermal.md` must radiate (or can credit to habitat heating). Catalysts/electrodes are MachineParts upkeep (M-9), not consumed reagents, except where noted.

**Authority rule (binds M-4a):** the **Energy column (kWh per kg of bold product) is canonical** for the simulation; nameplate kWe = Energy × nominal rate / 24 h, and is display-only. Where a recipe also has `P_t`, thermal demand scales the same way.

| RX | Plant (Tier) | Reaction (real) | Game mass balance (per kg of primary product, **bold**) | Energy | Op temp | Anchor |
|---|---|---|---|---|---|---|
| RX-01 | PEM Electrolyzer (T1) — 1.0 t, 58 kWe, 250 kg H2O/day | H2O → H2 + ½O2, ΔH 285.8 kJ/mol | 1 kg H2O → **0.112 kg H2** + 0.888 kg O2 | 5.6 kWh/kg H2O (79% HHV) | 350 K | ISS OGA / industrial PEM (~50 kWh/kg H2) |
| RX-02 | SOEC Electrolyzer (T2) — 2.5 t, 200 kWe, 1,000 kg H2O/day | high-T steam electrolysis | same balance | 4.8 kWh/kg H2O | 1100 K | SOEC industry; co-electrolysis variant RX-05 |
| RX-03 | Sabatier Reactor (T1) — 0.8 t, 0.8 kWe, 91 kg CH4/day | CO2 + 4H2 → CH4 + 2H2O, ΔH −165 kJ/mol | 2.75 kg CO2 + 0.50 kg H2 → **1 kg CH4** + 2.25 kg H2O | 0.2 kWh/kg e⁻. Thermal: gross exotherm 2.86 kWh_t/kg CH4 (ΔH −165 kJ/mol); net of non-recuperated feed-gas preheat to 600 K the radiator load is **P_t = −1.8 kWh_t/kg CH4 — the canonical value, and the one `09-power-thermal.md` §3.6's H-0 thermal ledger consumes** (honest band 1.8–2.0 as the recuperator wears; 09 quotes the same pair). Waste heat ≈ 6.8 kWt net at full rate (10.8 kWt gross) | 600 K, Ni/Ru cat. | ISS Sabatier; Mars ISRU baseline |
| RX-04 | RWGS Reactor (T2) — 1.0 t, 6 kWe, 240 kg H2O/day | CO2 + H2 → CO + H2O, ΔH +41 kJ/mol | 2.44 kg CO2 + 0.111 kg H2 → 1.556 kg CO + **1 kg H2O** | 0.6 kWh/kg H2O (incl. 1070 K heat) | 1070 K | Mars ISRU studies |
| RX-05 | SOXE CO2 Electrolyzer (T0 demo / T2 plant) — demo: 17 kg, 0.36 kWe, 0.29 kg O2/day; plant: 1.5 t, 35 kWe, 100 kg O2/day | 2CO2 → 2CO + O2, ΔH +283 kJ/mol CO2 | 2.75 kg CO2 → **1 kg O2** + 1.75 kg CO | demo 30 kWh/kg O2; plant 8 kWh/kg O2 (theoretical 4.9) | 1070 K | **MOXIE** (6–12 g/hr, 122 g total, 2021–23) |
| RX-06 | Bosch Reactor (T2) — 0.5 t, 3 kWe, 50 kg C/day | CO2 + 2H2 → C(s) + 2H2O, ΔH ≈ −90 kJ/mol | 3.67 kg CO2 + 0.333 kg H2 → **1 kg Carbon** + 3.0 kg H2O | 1.5 kWh/kg C (reactor heat mgmt) | 800–1000 K | ISS CO2-reduction studies |
| RX-07 | Ilmenite H2-Reduction Line (T2) — 4 t, 58 kWe, 100 kg O2/day | FeTiO3 + H2 → Fe + TiO2 + H2O (≈950 °C), then RX-01 | 9.5 kg **contained ilmenite** (≈ 11.9 kg concentrate @ g_c = 0.80; the 2.4 kg gangue passes through unreacted → tailings/Regolith) → **1 kg O2** + 3.5 kg IronSteel + 5.0 kg TiO2 slag (→Titanium feed); H2 recycled, 2% makeup | 14 kWh/kg O2 (incl. beneficiated feed, electrolysis) | 1250 K | Apollo/Artemis lunar O2 baseline; needs Beneficiation Separator upstream |
| RX-08 | Carbothermal Reactor (T2/T3) — 3 t, 20 kWe + 45 kWt, 50 kg O2/day | silicates + CH4 → CO + H2 + Si/Fe (1900 K); CO+H2 remethanated; H2O electrolyzed | 6.7 kg regolith → **1 kg O2** + 0.35 kg Si-Fe metal mix + 5.37 kg slag; CH4 makeup 0.02 kg | 30 kWh/kg O2 (kWt can be concentrated solar) | 1900 K | NASA/Sierra Space **CaRD** demo 2023; ~15% O2 yield |
| RX-09 | Molten Regolith Electrolysis Cell (T3) — 12 t, 365 kWe, 250 kg O2/day | direct oxide-melt electrolysis, inert anode | 4.0 kg any regolith → **1 kg O2** + 0.7 kg IronSteel-grade Fe-Si + 2.3 kg slag | 35 kWh/kg O2 | 1900 K | MIT MRE (Sadoway/Schreiner models, 25–50 kWh/kg); anode life = heavy MachineParts upkeep ×3 |
| RX-10 | Mond Carbonyl Refinery (T3) — 3 t, 42 kWe, 500 kg metal/day | Ni+4CO⇌Ni(CO)4 (330 K, ~100 kPa); Fe+5CO⇌Fe(CO)5 (450 K, 10 MPa); decompose 500 K | 1.04 kg crushed NiFe → **1 kg IronSteel** (carbonyl-pure Fe/Ni/Co) + 0.04 kg PGM-rich residue → RareEarths at deposit ppm; CO loop, 0.05 kg Carbon makeup/kg | 2 kWh/kg metal | 330–500 K | INCO Clydach (since 1902); Lewis *Mining the Sky*; gravity-insensitive — the M-type asteroid workhorse |
| RX-11 | Anorthite Aluminum Line (T3) — 8 t, 125 kWe + 20 kWt, 100 kg Al/day | CaAl2Si2O8 via carbochlorination / molten-salt electrolysis **[SIMPLIFIED]** | 6.4 kg highland regolith → **1 kg Aluminum** + 0.6 kg Silicon + 1.5 kg O2 + 3.3 kg Ca-silicate slag (→Glass feed) | 30 kWh/kg Al total (Earth Hall-Héroult 13–15; lunar penalty honest) | 1300 K | NASA SP-509 *Space Resources*; Cl2 loop is MachineParts-hungry |
| RX-12 | H2-DRI Steel Plant (T2) — 3.5 t, 39 kWe, 250 kg Fe/day | Fe2O3 + 3H2 → 2Fe + 3H2O (1200 K), H2O re-electrolyzed | 1.43 kg Fe2O3 conc. → **1 kg IronSteel** + (0.48 kg H2O internal loop, 3% makeup H2) | 3.7 kWh/kg Fe | 1200 K | HYBRIT pilot (~3.5 MWh/t) |
| RX-13 | Cryo Fractionator (T2) — 1.2 t, 21 kWe, 2,000 kg/day mixed fluid | staged cryogenic distillation | mixed gas/liquid → pure canonical streams per input composition | 0.25 kWh/kg processed | 80–250 K | air-separation industry |
| RX-14 | Haber Ammonia Loop (T2) — 0.6 t, 2.1 kWe, 50 kg NH3/day | N2 + 3H2 → 2NH3, ΔH −46 kJ/mol NH3, 20 MPa Fe cat. | 0.824 kg N2 + 0.176 kg H2 → **1 kg Ammonia** | 1.0 kWh/kg NH3 (synthesis loop only; H2 priced upstream) | 700 K | Haber-Bosch |
| RX-15 | Polymers — **canonical recipe lives in `05-industry-logistics.md`**: `polymers_mto` at the fab_chem_plant (05 §4.2; build tier T1 per 05, unlock node IS-09a per `11-research-tech.md`). RX-15 is retained as an alias ID only; 04 defines **no** competing recipe — 04 owns the upstream feedstock chemistry (Methane, Oxygen), 05 owns the conversion | CH4 partial oxidation → methanol → olefins → polyolefin (MTO) **[SIMPLIFIED]** | quoted verbatim from 05 (canonical there): 1.20 kg Methane + 1.20 kg Oxygen → **1 kg Polymers** + 1.22 kg Water + 0.16 kg CO2 + 0.02 kg Hydrogen | 1.5 kWh/kg (05 canon) | varies | methanol/MTO industrial route (95% carbon efficiency, 05 §4.2) |
| RX-16 | Siemens Silicon Refiner (T3) — 5 t, 100 kWe, 20 kg/day | metallurgical Si → trichlorosilane → solar-grade | 1.4 kg Si (met.) → **1 kg Silicon (solar-grade)** + 0.4 kg recycle loss | 120 kWh/kg | 1400 K | Siemens process (order 10²) |
| RX-17 | Basalt/Glass Furnace (T2) — 2 t, 31 kWe, 500 kg/day | melt 1650 K, spin or cast | 1.05 kg Regolith/tailings → **1 kg BasaltFiber or Glass** | 1.5 kWh/kg | 1650 K | terrestrial basalt-fiber industry |
| RX-18 | FFC Titanium Cell (T3) — 3 t, 47 kWe, 25 kg/day | TiO2 electro-deoxidation in CaCl2 melt | 1.67 kg TiO2 slag → **1 kg Titanium** + 0.67 kg O2-bearing offgas | 45 kWh/kg Ti | 1200 K | FFC Cambridge (vs Kroll ~100 kWh/kg) |
| RX-19 | Pu-238 Line (T3) — reactor add-on, 2 t | Np-237(n,γ)→Pu-238 in fission flux | per `09-power-thermal.md` reactor: **20 g Pu238/year** per 100 kWe-class core + Uranium chain upkeep | — | — | Oak Ridge production line (~kg/yr national scale; player gets grams) |

**Plant scaling rule:** Tier-up versions of any RX plant cost ×4 mass, deliver ×5 throughput at −10% specific energy (economies of scale, honest but mild). `05-industry-logistics.md` owns build costs.

**Intermediate streams.** The following non-canonical process streams flow between machines. They are real inventory objects (`05-industry-logistics.md` / `13-architecture.md` schema: name, form, bulk density for storage volume, composition vector where noted). **Disposal rule: any intermediate solid stream not routed to a consumer converts 1:1 to Regolith (M-8); mixed gas held in a full tank vents (destroyed mass); sour gas is flared unless fractionated.**

| Stream | Form | Bulk ρ (storage) | Producer | Consumer | If unconsumed |
|---|---|---|---|---|---|
| Ilmenite concentrate (grade g_c) | bulk granular | ~2,500 kg/m³ | Beneficiation Separator | RX-07 | → Regolith |
| NiFe concentrate (grade g_c) | bulk granular | ~4,000 kg/m³ | Beneficiation Separator | RX-10 | → Regolith |
| Fe2O3 concentrate | bulk granular | ~2,800 kg/m³ | Beneficiation Separator (magnetic, Mars Fe-oxide plains) | RX-12 | → Regolith |
| TiO2 slag | bulk granular | ~2,400 kg/m³ | RX-07 | RX-18 | → Regolith |
| Si-Fe metal mix | ingot | ~5,000 kg/m³ | RX-08 | auto-splits on output: 0.5 kg IronSteel + 0.5 kg Silicon (met.) per kg **[SIMPLIFIED]** | n/a (splits immediately) |
| Generic / Ca-silicate slag | bulk | ~2,900 kg/m³ | RX-08, RX-09, RX-11 | RX-17 (counts as Regolith feed → Glass/BasaltFiber) | → Regolith |
| Mixed gas | tank + composition vector | per composition | intakes (M-3e), Volatile Bake Oven | RX-13 Fractionator | held; vents if tank full |
| Sour gas | tank, fixed composition (M-3d) | per composition | ice cleanup (M-3d), RX-10 purge | RX-13 (recovers CO2 + Ammonia fractions) | flared (M-8, F-11) |

**Silicon grade attribute:** the canonical resource Silicon carries a grade flag {met, solar}. RX-08/09/11 produce Silicon (met.); RX-16 upgrades met → solar; the Electronics fab chain (`05-industry-logistics.md`) requires solar grade. One canonical name, one extra byte of state — no canon-list extension needed.

### 4.6 End-to-end propellant chains (canon derivations)

**Chain A — Mars methalox (Act 3 flagship).** Engine O/F = 3.6 (Raptor-class, `02-propulsion.md`). Basis: 1 kg CH4 + 3.96 kg O2 (electrolysis output slightly exceeds 3.6 O/F; surplus 0.36 kg O2 → life support credit).

| Step | Recipe | Mass flow | Energy |
|---|---|---|---|
| Mine buried ice (g≈0.6) | M-3d | net 2.21 kg H2O (4.46 needed − 2.25 returned by Sabatier) | 2.21 × 1.2 ≈ 2.7 kWh |
| Acquire CO2 | Intake II | 2.75 kg CO2 (+Ar/N2 bonus) | 2.75 × 0.4 = 1.1 kWh |
| Electrolyze | RX-01 | 4.46 kg H2O → 0.50 kg H2 + 3.96 kg O2 | 4.46 × 5.6 = 25.0 kWh |
| Sabatier | RX-03 | → 1 kg CH4 + 2.25 kg H2O (recycled) | 0.2 kWh e⁻ (−1.8 kWh_t net heat credit per RX-03 canon; 2.86 gross) |
| Liquefy | M-5 | 1 kg LCH4 + 3.96 kg LOX | 0.8 + 2.8 = 3.6 kWh |
| **Total** | | **4.6 kg propellant** (1 kg LCH4 + 3.6 kg LOX at O/F 3.6) **+ 0.36 kg surplus O2** (life-support credit, excluded from the propellant basis) | **32.6 kWh → 7.1 kWh/kg propellant** (heat credit excluded) |

(Note: the liquefaction line includes liquefying all 3.96 kg O2, surplus included (~0.25 kWh); delivering the surplus to `08-life-support-crew.md` as gas would strictly give ~7.0 kWh/kg — **7.1 is the conservative canon figure**.)

**Chain B — Lunar hydrolox from PSR ice (Act 2 flagship).** O/F = 6.0 (RL10-class). Basis: 1 kg propellant = 0.143 kg H2 + 0.857 kg O2. Stoichiometric water yields O2:H2 = 7.93:1, so H2 limits; 1.28 kg H2O needed, 0.27 kg surplus O2 per kg propellant (sell to `08-life-support-crew.md`).

| Step | Mass flow | Energy |
|---|---|---|
| PSR ice extraction @ g=5%, Tier II (M-3d) | 1.28 kg H2O (+cleanup 0.1 kWh/kg) | 1.28 × (2.3+0.1) = 3.1 kWh |
| Electrolysis (RX-01) | → 0.143 kg H2 + 1.137 kg O2 | 1.28 × 5.6 = 7.2 kWh |
| LH2 liquefaction | 0.143 kg | 0.143 × 12 = 1.7 kWh |
| LOX liquefaction | 0.857 kg (0.27 kg surplus vented to LS) | 0.857 × 0.7 = 0.6 kWh |
| **Total** | **1 kg propellant** | **≈ 12.6 kWh/kg** (drops to ~11.8 at g=10%, rises to ~16.4 at g=1.5%; all sensitivities at Tier II per M-3d — only the extraction line moves) |

**Chain C — "LOX is 86% of the rocket" (Act 2 alternative).** Ship LH2 from Earth (or skip H2 entirely with methalox tankers), make only LOX locally via RX-07/08/09. Hauling 0.143 kg H2 instead of 1 kg propellant cuts imported mass 7×. MRE LOX at ≈ 35.7 kWh/kg (incl. liquefaction, §3.7) is power-hungry but works on *any* regolith with zero prospecting risk — the deliberate tradeoff vs PSR ice (cheap energy, risky deposit, hostile 40 K site).

**Chain D — C-type water depot (Act 3–4).** Bag-and-grind (15 t/day) + Volatile Bake Oven @ g=8%, R = 0.85 (Capture Bag: Tier II 0.75 + 0.10 enclosure bonus, M-6.2): 1 kg H2O per ~14.7 kg rubble; oven 2.0 kWh/kg H2O + grind 0.2 (Capture Bag+Grinder, 8 kWe at 15 t/day feed → 0.0128 kWh/kg feed × 14.7) + cleanup 0.1 ≈ **2.3 kWh/kg H2O**; electrolyze+liquefy at the depot per Chain B economics minus mining. Byproducts per kg H2O: 0.37 kg CO2, 0.04 kg N2/NH3 mix via Fractionator.

**Chain E — Titan methalox (Act 5).** CH4 near-free from sea/atmosphere (≈ 0.005–0.01 kWh/kg acquisition + fractionation); **all O2 must come from water-ice bedrock**: per kg methalox at O/F 3.6, 0.78 kg O2 ← 0.88 kg H2O; ice extraction 0.8 kWh (g≈0.95: ~0.9 kWh/kg H2O) + electrolysis 4.9 kWh (0.88 × 5.6) + LOX liquefaction 0.55 kWh (0.78 × 0.7) ≈ **6.3 kWh/kg propellant** (LCH4 liquefaction ~free at 94 K ambient). The 0.099 kg H2 electrolysis byproduct per kg propellant is stored as Haber feed (RX-14 Ammonia, with the N2 fractionation byproduct) or vented if no Haber loop is on site. At 9.5 AU solar is ~1% of Earth's — fission power mandatory (`09-power-thermal.md`).

---

## 5. Player Interaction & UI

(Shared UI grammar in `12-gameplay-economy-ui.md`; this section lists what this domain needs.)

- **Survey overlay** (map mode): per-body toggle showing deposit icons colored by resource class, badge for K-state, grade shown as `ĝ ± σ` band (M-2b). K3+ deposits render the radial grade-contour map (M-1a) as a heat ring. Un-surveyed bodies show "?" with the instrument(s) required.
- **Deposit panel**: resource, K-state with "next step" button (e.g. "Send rover: 2d + travel"), estimated tonnage band, grade band, depth class, list of machines on site with their sampled `g(d)`.
- **Plant/flow panel** (Factorio-style but mass-true): every machine shows input rate → output rate, utilization bar (M-4a), bottleneck cause (POWER / FEED / STORAGE / PARTS), specific energy, waste-heat line to the thermal bus (09). A site-level **Sankey view** aggregates mass flows from excavator to tank so leaks (vented boiloff, flared sour gas, debris losses) are visually obvious — entropy made legible.
- **Production planner**: player sets a target ("100 t methalox by day X"); tool back-computes required continuous kWe and feed rates from §4.6 chains and flags shortfalls against installed power (09) and deposit tonnage. This is the core "engineering sim" loop.
- **Alerts** (to the global alert bus, 12): deposit < 90 days at current draw; tank full (production stalling); ZBO power lost (boiloff venting started, mass-loss rate shown); survey estimate revised (on K-upgrade, show old vs new grade — the "assay day" moment); MachineParts starvation.
- **Time-warp behavior**: all flows are linear; the scheduler (13) pre-computes the earliest of {tank full, tank empty, deposit exhausted, parts depleted} and auto-drops warp on alert severity ≥ amber, per the global warp-interrupt rule.

---

## 6. Progression Hooks

| Tier / Act | Unlock (this domain) | Gameplay meaning |
|---|---|---|
| **T0 (Act 1, Earth+LEO)** | Orbital spectrometers; SOXE demo (MOXIE-scale, RX-05 demo); all resources Earth-purchased (12) | ISRU is a science demo; player learns the survey loop on the Moon from orbit while flying LEO ops |
| **T1 (Act 1–2)** | Drum Excavator, Thermal Ice Corer, PEM Electrolyzer (RX-01), Sabatier (RX-03), Core Drill, Cryo Liquefaction Skid (LOX/LCH4/LH2, §4.4), vapor-return cryo transfer | First lunar polar water pilot plant; first locally-fueled hop; "Proven reserve" loans unlock (12) |
| **T2 (Act 2–3)** | Bucket-Wheel, Sublimation Tent, Beneficiation, RX-02/04/05-plant/06/07/08/12/13/14/17, Mars Intakes I & II (both T2, IS-06 gate in `11-research-tech.md`), Rodwell, Capture Bag, Volatile Oven, Deep Core Rig | Industrial Moon (ilmenite O2 + Fe + Ti slag); Mars methalox chain closes (Chain A); first C-type NEA bagged; steel & polymers go local (Polymers via 05's `polymers_mto` chem plant — RX-15 alias, not an 04 recipe) |
| **T3 (Act 3–5)** | Strip miners, MRE (RX-09), Mond (RX-10), Anorthite Al (RX-11), FFC Ti (RX-18), Siemens Si (RX-16), Pu238 line (RX-19), Optical Mining, Venus Aerostat Intake, Titan Sea Pump/Intake | Heavy industry anywhere; M-type metal economy with PGM (RareEarths) export to Earth (12); Venus/Titan volatiles; KREEP Th/U ends fuel imports |
| **T4 (Endgame) [SPECULATIVE]** | He3 Volatile Kiln; gas-giant atmospheric scoop (with `02-propulsion.md` fusion tier) | He3 economy feeds fusion torch; kiln byproducts (H2/N2/C/H2O at g/t levels) finally make mare regolith a volatile source — closing the loop the hard way |

Research costs/prereq graph lives in `11-research-tech.md`; this table is the content mapping. Act-gating note: nothing here requires plane changes or 3D geometry; PSR access in 2D is modeled as polar *sites* with permanent-shadow tags (03 owns site definitions) — honest about the 2D simplification.

---

## 7. Cross-System Interfaces

**Consumes:**
- `03-solar-system.md`: body/site lists, atmosphere composition & density profiles, PSR site tags, asteroid spectral classes & spin states, solar flux vs distance.
- `09-power-thermal.md`: electric power (kWe) and process heat (kWt) supply; radiator capacity for exothermic recipes (Sabatier: canonical **net −1.8 kWh_t/kg CH4** to radiators per RX-03 — the figure 09 §3.6's H-0 ledger consumes; the 2.86 kWh_t/kg gross exotherm is the pre-preheat-debit value, never a radiator load) and cryocooler heat rejection.
- `05-industry-logistics.md`: MachineParts (M-9 upkeep), machine construction, surface haulage of feed/tailings, HEPA consumables, pelletizer for mass-driver Regolith.
- `10-vehicles.md`: rovers for K2 surveys, haulers, Titan submarine/shore platform for Sea Pump.
- `06-ships-stations.md`: survey-instrument mounting, anchoring ops, debris-hazard damage model, depot tankage.
- `11-research-tech.md`: tier unlocks for every machine/recipe above.
- `12-gameplay-economy-ui.md`: Earth purchase prices (Xenon, Electronics, Uranium, Pu238 early game), reserve-collateral finance, alert/UI framework.

**Provides:**
- `02-propulsion.md`: propellant mass flows (LCH4/LOX/LH2/LN2/Argon/Xenon/Water/NH3), liquefaction-state handoff table (M-5), shared ZBO power rule (M-5a), transfer ullage losses.
- `09-power-thermal.md`: canonical load figures — 7.1 kWh/kg methalox, 12.6 kWh/kg hydrolox, 35.7 kWh/kg MRE LOX (all incl. liquefaction, §3.7), 59 kWe for the 100 t/500 d Mars plant; waste-heat credits.
- `07-bases-habitats.md`: Regolith/tailings for shielding (2–3 t/m²), Glass/BasaltFiber/StructuralParts feedstocks, site-slot pressure from tailings piles (M-8).
- `08-life-support-crew.md`: surplus O2 streams (Chains A/B), Water, N2 buffer gas, Ammonia fertilizer, CO2; contaminant warnings on PSR-derived water (cleanup step mandatory before potable use).
- `05-industry-logistics.md`: refined metals (IronSteel/Aluminum/Titanium/Copper/Silicon/RareEarths), Carbon, Glass, BasaltFiber as manufacturing inputs, plus the Polymers feedstocks Methane + Oxygen (the Polymers conversion itself is 05's `polymers_mto`, RX-15 alias); Regolith/tailings feed for its mass-driver pelletizer (M-8); recipe IDs RX-01..19 referenced by its factory UI.
- `13-architecture.md`: linear-flow production model, predicted-event list (tank full/empty, deposit exhaustion, parts-out), deposit/knowledge data schema (M-1, M-2).

---

## 8. Failure Modes & Edge Cases

| ID | Failure / edge case | Rule |
|---|---|---|
| F-1 | **Assay shock**: true grade ≪ K2 estimate (M-2b tail) | Production shortfall discovered only via pilot ops; mitigation is paying for K3/K4 first. No rescue mechanic — this is the designed gamble. |
| F-2 | **Deposit exhaustion mid-campaign** | 90-day warning alert; machines idle at exhaustion; site keeps tailings (Regolith) value. Planner (§5) shows tonnage vs committed launch schedule. |
| F-3 | **ZBO power loss** | Tank reverts to passive boiloff per 02's table; vented mass is destroyed; alert severity scales with %/day. LH2 depots without backup power are a deliberate trap. |
| F-4 | **Mars dust storm** (03 weather) | Solar input cut up to 80% for 30–100 days (09); intakes keep working (HEPA ×3 consumption); chain A stalls unless fission-backed — the classic architecture lesson. |
| F-5 | **PSR cold-trap thermal pollution** | If total radiator heat rejection within a PSR site cell exceeds **10 kWt at radiator temperature > 110 K for > 30 consecutive days**, every Water deposit in that cell loses 1% of `g0` per year of continued violation (slow, honest: you can cook your own deposit). Encourages tent capture & heat discipline. |
| F-6 | **Anchor failure / debris cascade** | If tool force exceeds anchor rule (M-6.1) due to damage, tool auto-stops; override = 5%/h chance of anchor rip-out → machine becomes free-floating debris hazard (06 must recapture). |
| F-7 | **Carbonyl leak** (RX-10): Ni(CO)4 is violently toxic | In crewed modules, a Mond plant leak event (MTBF-driven, 05 reliability model) forces module evacuation + 10 crew-hours decontamination (08). Robotic-only siting avoids the risk entirely — intended design pressure. |
| F-8 | **Titan inlet icing** | Sea Pump throughput −50% if inlet heater unpowered (2 kWe of its 4 kWe budget is heating). |
| F-9 | **Venus aerosol corrosion** | External machines on aerostats take M-9 upkeep ×2; ignoring parts starvation here degrades to 20% utilization fastest. |
| F-10 | **Tailings lockout** | Site slots full (M-8) → extractors stall; player must sinter, export, or bag tailings. No magic disposal. |
| F-11 | **Sour-gas venting near habitats** | Flared sour gas within a habitat site adds **(flared kg/day × non-recovered fraction)** — 0.35 with a Fractionator capturing the CO2/NH3 fractions, 1.0 without (composition per M-3d) — as trace-contaminant input (kg/day) to 08's air-quality ledger for habitat cells adjacent to the flare **[SIMPLIFIED to adjacency]**. |
| F-12 | **Mining the whole asteroid** | Allowed: deposit tonnage = body mass × grade. Body mass loss has no orbital effect (honest: negligible); ship mass growth does affect 06's CoM/thrust. Bagged bodies < 20 m can be fully consumed, leaving the bag (reusable). |
| F-13 | **Phobos gamble** | Phobos/Deimos water may roll ~0 (genuinely unknown today). Orbital survey before commitment is the lesson; the K-system exists exactly for this. |
| F-14 | **Throttled-plant wear** | <30% utilization >24 h → maintenance ×2 (M-4a note). Prevents "build 10× oversized plant" being free. |
| F-15 | **Xenon trap** | Mars-atmosphere Xe is 0.08 ppm molar ≈ 0.24 ppm by mass (Viking GCMS, Owen et al. 1976) — the **same mixing ratio as Earth air**, but throughput kills it: ~4,000 t of Mars gas per kg Xe, so an Intake II (1 t/day) needs ~11 years per kg vs industrial Earth ASUs processing >10^5 t air/day. The Fractionator UI explicitly marks it NOT RECOVERABLE (throughput-uneconomic, not concentration-poor), blocking a plausible-sounding but wrong player plan. Argon is the intended EP propellant pivot (1.93% — genuinely recoverable). |
| F-16 | **Save/load & warp consistency** | All flows linear ⇒ state at t+Δt is closed-form; no drift between warp rates (13 owns the invariant test). |

---

## 9. Open Questions

1. **Grade-field fidelity**: is the radial Gaussian (M-1a) enough, or do we want 2–3 overlapping lobes per deposit for richer extractor-placement gameplay? (Cost: survey UI complexity.)
2. **Copper scarcity tuning**: making Cu a near-Earth-monopoly is realistic and creates good logistics tension, but may frustrate late-game off-Earth electronics; option: M-type sulfide micro-deposits at 0.1–0.5% Cu — need a defensible literature anchor before adding (cosmochemistry on asteroidal Cu is thin).
3. **Ethane as a first-class resource?** Currently [LUMPED] into Methane at 0.93×. If `02-propulsion.md` wants distinct C2H6 performance or `05-industry` wants an ethylene shortcut, we should promote it (canon-list extension request).
4. **PSR thermal-pollution rate (F-5)**: 1%/year grade decay is a gameplay number, not literature-derived; needs a heat-diffusion sanity model or removal.
5. **Pu238 production rate** (RX-19, 20 g/yr per 100 kWe core): plausible order for a small Np-237 target loop but weakly anchored; coordinate with `09-power-thermal.md` on whether RTGs matter enough to keep the chain.
6. **Venus cloud-water harvesting**: 2 kg/day per intake is a placeholder for very thin aerosol mass loading (~mg/m³); verify against Venus cloud LWC literature or cut the feature.
7. **Beneficiation depth**: one generic separator vs per-mineral concentration ratios (ilmenite ×8, NiFe ×10 currently). More fidelity helps the Moon ilmenite chain feel real but adds a machine class.
8. **Does K1 reveal *all* deposits or per-instrument subsets only?** Current rule: per-instrument resource classes (neutron→H, IR→minerals, radar→deep ice/metal). Confirm the survey-completionist loop isn't tedious with 3 instruments × N bodies; possible merge into one T2 "survey suite".
9. **He3 kiln byproduct economy** [SPECULATIVE]: at 10 ppb He3, byproduct volatiles (g/t) dwarf the He3 by mass — should T4 mare volatile mining become a legitimate *water* source (≈30 g/t means 300× worse than PSR ice; probably never competitive — verify the kiln doesn't accidentally trivialize volatile logistics).
10. **Shared-canon audit**: M-5 liquefaction/ZBO numbers and §3.7 headline energies must be byte-identical in `02-propulsion.md` and `09-power-thermal.md` final drafts — schedule a cross-doc reconciliation pass.
