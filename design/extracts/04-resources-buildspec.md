# BUILD SPEC — 04 Resources, Mining & ISRU

Extracted from `design/04-resources-isru.md` (DRAFT v1.0, 2026-06-09) + `design/DECISIONS.md` (B11/B14/B15/B16 already folded into 04; A1 spelling `RP1`; A2 owner-doc-wins).
Engineer-facing: implement from this file. Cross-doc owners noted inline. All units SI; `1 t/day = 0.01157 kg/s`.

Global simulation rules (binding):

- All production = **continuous linear flows (kg/s)**, explicit mass + energy balance. Every recipe conserves mass to ±1%. No free mass/energy. (Code: `validate.py` already enforces 0.5% — stricter is fine.)
- Flows integrate analytically under warp; tank-full / deposit-exhausted / feedstock-starved are **predicted boundaries** handed to the scheduler (matches existing `LedgerNetwork.advance`).
- Plant utilization (M-4a): `util = min(P_avail/P_req, min_i(feed_avail_i/feed_req_i), min_j(drain_cap_j/out_rate_j))`, each term clamped [0,1], evaluated per scheduler tick. Full output tank with zero drain stalls the **whole** plant — no selective venting unless the recipe says so.
- Plants <30% utilization for >24 h → efficiency alert + **2× maintenance** [SIMPLIFIED] (F-14).
- **Plant scaling rule:** tier-up version of any RX plant = ×4 mass, ×5 throughput, −10% specific energy.
- **Energy-column authority:** in §3 recipe tables the kWh-per-kg-of-bold-product figure is canonical; nameplate kWe = Energy × nominal rate / 24 h (display only). Thermal `P_t` scales identically.

---

## 1. RESOURCE TAXONOMY

### 1.1 Canonical resources (29) — exact spellings

Exact spellings below are canon (already in `aphelion/content/validate.py::CANONICAL_RESOURCES`). Storage class legend: **CRYO** (needs liquefaction + boiloff/ZBO model), **PRESS** (pressurized or ambient liquid tank), **BULK** (pile/ingot/crate — no tank physics).
Densities: cryo/liquid densities are canon from M-5 (shared byte-identical with 02 §4.1, which owns them). 04 assigns no ledger density to solids (form only) — see §3.6 intermediate-stream densities for bulk granular streams.

| # | Resource | Storage class | Stored as | T_store | ρ (kg/m³) | Earth buy anchor (12 §4.3, $/kg) | Notes |
|---|---|---|---|---|---|---|---|
| 1 | Water | PRESS (liquid/ice) | liquid/ice tank | any | 1000 | 0.001 | universal feedstock; electrolyzes to 0.888 O2 + 0.112 H2 |
| 2 | Oxygen | CRYO | LOX | 90 K | 1141 | 0.20 | 86% of hydrolox mass, 78% of methalox — the bulk prize |
| 3 | Hydrogen | CRYO | LH2 | 20 K | 70.8 | 6 | hardest cryogen; ZBO k = 100 We/Wt |
| 4 | Methane | CRYO | LCH4 | 111 K | 423 | 1 | Sabatier product; Titan native; ethane lumped in at 0.93× (B14) |
| 5 | Nitrogen | CRYO | LN2 / GN2 | 77 K | 808 | 0.3 | buffer gas + fertilizer; Titan = system N reservoir |
| 6 | CO2 | CRYO (mild) | sat. liquid ≈600 kPa | 220 K | 1166 | 0.1 | Mars/Venus atmospheres = infinite deposits |
| 7 | Ammonia | PRESS | chilled liq ~240 K (or pressurized ambient, same ρ) | ~240 K | 682 | 0.6 | N-carrier, fertilizer, coolant, NTR option, MMH feed |
| 8 | MMH | PRESS (ambient storable) | liquid | ambient | (02 owns tank state) | 100 | hypergolic fuel; never ages out (B11); RX-20 |
| 9 | NTO | PRESS (ambient storable) | liquid | ambient | (02 owns tank state) | 12 | hypergolic oxidizer; never ages out (B11); RX-21 |
| 10 | Argon | CRYO | liquid | 87 K | 1395 | 1.5 | EP propellant pivot (Mars 1.93%) |
| 11 | Xenon | PRESS | supercritical gas 8.6 MPa | ambient | 1580 | 1,200 | always scarce; Mars recovery blocked by F-15 |
| 12 | Regolith | BULK | pile | — | — | n/a (not traded) | = tailings; shielding 2–3 t/m²; sinter/fiber feed; minable anywhere at g=1.0 with no Deposit |
| 13 | IronSteel | BULK | ingot | — | — | 0.8 | [LUMPED] Fe+Ni+Co alloys incl. carbonyl-pure |
| 14 | Aluminum | BULK | ingot | — | — | 2.5 | from anorthite (19.4 wt% Al) |
| 15 | Titanium | BULK | ingot | — | — | 25 | from ilmenite TiO2 slag via FFC |
| 16 | Copper | BULK | ingot | — | — | 9 | genuinely Earth-scarce (B15 — no invented asteroid Cu); relief via Recycler (B16) |
| 17 | Silicon | BULK | ingot, **grade flag {met, solar}** | — | — | 15 (solar-grade) | one canonical name + 1 byte of grade state; fab needs solar |
| 18 | RareEarths | BULK | ingot/oxide | — | — | 80 | [LUMPED] REE+PGM+scarce metals (flagged in UI) |
| 19 | Uranium | BULK | oxide/fuel rod | — | — | 30,000 (HALEU) | KREEP grades are bad (2–3 ppm) — import until T3 |
| 20 | Thorium | BULK | oxide | — | — | 100 | KREEP up to ~12 ppm; T3 molten-salt path (09) |
| 21 | Pu238 | BULK | RTG pellet | — | — | 10,000,000 | 0.57 W/g; made (RX-19), never mined |
| 22 | Carbon | BULK | graphite/powder | — | — | 1.5 | Bosch product; reductant/electrodes/carbonyl makeup |
| 23 | Polymers | BULK | pellets | — | — | 3 | [LUMPED] PE-class; recipe OWNED BY 05 (`polymers_mto`, alias RX-15) |
| 24 | BasaltFiber | BULK | spool | — | — | 4 | melt-spun regolith, 1650 K (RX-17) |
| 25 | Glass | BULK | sheet/stock | — | — | 1 | sintered silica regolith (RX-17) |
| 26 | Electronics | BULK | crate | — | — | 20,000 | Earth import until T3 fab (05); ×1.3 mass penalty local until T3+ (B12) |
| 27 | MachineParts | BULK | crate | — | — | 1,000 | THE maintenance currency (M-9; 05 §3.10 owns rates) |
| 28 | StructuralParts | BULK | beam/panel | — | — | 50 | from IronSteel/Aluminum/BasaltFiber (05) |
| 29 | FoodRations | BULK | crate | — | — | 150 | 08 owns diet |
| 30 | Biomass | BULK | wet mass | — | — | not traded | grown (08); C-type organics are NOT food |
| 31 | He3 | PRESS | gas bottle | — | — | sell-only 15,000,000 | [SPECULATIVE] T4; 4–20 ppb in high-Ti mare |

(Table is the 04 §4.1 taxonomy = 29 canon + MMH/NTO already in 04's table. Registered extensions used elsewhere: `RP1` (02, spelling per DECISIONS A1), `Wafers` (05), `MedSupplies` (08), `SurveyData` (03/05, GB not kg) — all already in `validate.py`.)

### 1.2 Liquefaction / conditioning energies (M-5, canon shared w/ 02 & 09)

| Product | E_liquefy (kWh/kg) | Real anchor |
|---|---|---|
| Hydrogen → LH2 | 12.0 | industrial 10–13 (theoretical 3.92) |
| Oxygen → LOX | 0.7 | industrial 0.4–0.6 + small-plant penalty |
| Methane → LCH4 | 0.8 | LNG 0.3–0.4 at scale + penalty |
| Nitrogen → LN2 | 0.8 | — |
| CO2 → sat. liquid | 0.15 | — |
| Ammonia → chilled liq | 0.05 | — |
| Argon → liquid | 0.6 | — |
| Xenon → supercritical | 0.3 | — |
| Water | 0 | — |

- Liquefaction is performed by the buildable **Cryo Liquefaction Skid** (§3.4) — not free, not implicit.
- **ZBO rule (M-5a):** `P_ZBO = Q_leak × k(T)`; k(20 K) = 100 We/Wt (LH2); k(77–111 K) = 15 We/Wt (LN2/LOX/LAr/LCH4). Without ZBO, boiloff %/day per 02's tank table; vented boiloff is destroyed mass unless routed to a use.
- **Transfer ullage loss:** 1.5% of transferred cryogen per transfer; 0.3% with vapor-return line (T1 depot equipment).
- MMH/NTO are ambient-storable: **no** M-5 liquefaction step.

---

## 2. DEPOSIT & PROSPECTING

### 2.1 Deposit object (M-1)

```
Deposit {
  body, site_id        # 07 owns the surface grid
  resource             # canonical name (raw form)
  tonnage_T [t]        # remaining extractable RESOURCE mass (not ore mass)
  grade_g0  [-]        # core mass fraction of resource in feedstock
  r_core    [m]        # radius of peak-grade zone
  depth_class          # SURFACE (0–0.5 m) | SHALLOW (0.5–3 m) | DEEP (3–30 m)
  knowledge_K          # K0..K4
  f_c                  # Water deposits only: contaminant fraction ~U(0.02,0.08), rolled at world-gen
}
```

- Grade falloff: `g(d) = g0 · exp(−(d/r_core)²)` (M-1a); `d` = extractor distance from deposit center in the surface grid. Extractors sample g at placement — placement matters post-discovery.
- World-gen rolls (M-1b/c): `tonnage_T = 10^U(a,b) t` and `grade_g0 ~ triangular(lo, mode, hi)` from §2.4 table; `r_core = 10^U(1.5, 3.0) m` (log-uniform 30 m–1 km, independent per deposit, no per-row override).
- Deposit center placed uniformly at random within the site cell. **Bulk-body rows** (asteroids, Phobos/Deimos): no center, `g(d) = g0` everywhere, whole body = one site.
- Grade constant over deposit life [SIMPLIFIED]; tonnage decrements by extracted resource mass; at `tonnage_T ≤ 0` machines idle with an alert.
- **Atmospheres & Titan seas:** infinite deposits (`tonnage_T = ∞`, fixed composition), **born at K4**, no K-gate on intake/pump placement. K-ladder applies to solid deposits only.

### 2.2 Knowledge ladder (M-2) — JORC/NI 43-101 naming

| K | Name | How obtained | Grade σ_K | Tonnage σ_T,K | Unlocks |
|---|---|---|---|---|---|
| K0 | Unknown | — | hidden | hidden | nothing |
| K1 | Inferred | orbital spectrometry pass (M-2a) | 0.50 | 1.15 (≈×10 OOM band) | deposit icon + rough grade |
| K2 | Indicated | rover traverse w/ neutron spec + GPR (µg: station-keeping survey) | 0.25 | 0.41 (±50%) | Tier I extractors placeable |
| K3 | Measured | ≥5 core samples × 6 h (µg: anchored corer) | 0.10 | 0.18 (±20%) | Tier II plants; ore-grade contour map revealed |
| K4 | Proven | 30 cumulative days of pilot extraction (any Tier I extractor) | 0.02 | 0.05 (±5%) | Tier III plants; deposit bankable as loan collateral (12) |

- Displayed estimates: `ĝ_K = g0·exp(ε), ε~N(0,σ_K²)`; `T̂_K = tonnage_T·exp(ε_T), ε_T~N(0,σ_T,K²)`. **Rolled ONCE per state transition, never re-rolled** (no savescum-by-staring). UI shows ±1σ band. Production always uses TRUE g — building on K2 and finding the field 40% lean is intended (F-1 "assay shock", no rescue mechanic).
- T̂_K4 is the bankable-collateral value (12).

**Orbital survey (K0→K1), M-2a:** powered survey instrument on a vessel below `h_max`:
```
T_K1 = max(6 h, 10 d · sqrt(R_body / 1738 km)),  valid while h ≤ h_max
h_max = max(25 km, 150 km · R_body / 1738 km)
```
Small bodies (R < 50 km): powered station-keeping within h_max counts as orbiting. Progress accrues only while powered and below h_max. All instruments share T_K1; each accrues independently for its own resource classes; duplicate instruments do NOT stack. Completing K1 reveals ALL deposits on the body that the instrument's resource class can see (§2.3). (2D world: coverage is purely an integration-time gate — stated honestly, no fake swath geometry.)

**Surface survey (K1→K2):** rover carrying Surface Survey Package: 2 days on-site + 1 day per 10 km traverse from landing point. GPR resolves depth_class.

**Core sampling (K2→K3):** Core Drill, 5 samples × 6 h each, depth ≥ depth_class floor (DEEP needs the T2 10-m rig). Reveals M-1a grade contours.

**Microgravity equivalents** (asteroids, Phobos/Deimos, comets — rovers can't traverse milligravity rubble):
- K1→K2: ship/robot station-keeping ≤1 km with powered Surface Survey Package, 2 cumulative days (no traverse term).
- K2→K3: 5 cores × 6 h from an **anchored** platform; corer's 100 N reaction must satisfy the M-6 anchor rule (1 microspine pad suffices: 100 ≤ 0.5×250).
- Whole body = single site; K-states body-wide.

**Pilot extraction (K3→K4):** any Tier I extractor, 30 cumulative days on the deposit (bagged/anchored qualifies).

### 2.3 Survey instrument catalog (§4.3)

| Instrument | Tier | Mass | Power | Detects (→K) | Anchor |
|---|---|---|---|---|---|
| Orbital Neutron+Gamma Spectrometer | T0 | 30 kg | 0.10 kWe | H (Water/ice), Th/U/KREEP, Fe → K1 | Lunar Prospector NS/GRS, LEND |
| Orbital IR/Vis Spectral Mapper | T0 | 25 kg | 0.10 kWe | hydrated minerals, ilmenite, organics, CO2/NH3 ices → K1 (no depth) | M3, CRISM, OVIRS |
| Orbital Radar Sounder | T2 | 90 kg | 0.45 kWe | buried ice sheets (DEEP), asteroid metal richness → K1+depth | SHARAD/MARSIS |
| Surface Survey Package (rover-mount) | T1 | 40 kg | 0.15 kWe | neutron spec + GPR (10 m) + XRF → K2 | RIMFAX + APXS |
| Core Drill, 1 m | T1 | 30 kg | 0.40 kWe peak | K3 on SURFACE/SHALLOW | TRIDENT / PRIME-1 (IM-2, 2025) |
| Deep Core Rig, 10 m | T2 | 400 kg | 3.0 kWe | K3 on DEEP; prereq for Mars Rodwell | terrestrial geotech |

### 2.4 World-gen ore-grade table (M-1b inputs; binds 1:1 to 03 §4.4 body hooks)

Grades = mass fraction of resource in raw feed, triangular(lo/mode/hi). Tonnage = 10^(a..b) t. "bulk" = bulk-body (uniform grade, no r_core).

| Body / region | Resource (raw form) | lo / mode / hi | Tonnage 10^(a..b) t | Depth | Anchor |
|---|---|---|---|---|---|
| Moon — PSR floors (Cabeus-class) | Water (ice-cemented regolith) | 0.01 / 0.055 / 0.10 | 4..7 | SHALLOW | LCROSS 5.6±2.9 wt% |
| Moon — high-Ti mare | Ilmenite → (Oxygen, IronSteel, Titanium) | 0.05 / 0.10 / 0.15 (ilmenite in soil) | 6..8 | SURFACE | Apollo 11/17 |
| Moon — highlands | Anorthite → (Aluminum, Silicon, Oxygen) | 0.75 / 0.85 / 0.95 (plagioclase) | 7..9 | SURFACE | anorthositic crust |
| Moon — KREEP (Procellarum fringe) | Thorium / Uranium ore | 6 / 9 / 12 ppm Th; U = 0.27×Th | 5..6 | SURFACE | Lunar Prospector GRS |
| Moon — high-Ti mare | He3 [SPECULATIVE] | 4 / 10 / 20 **ppb** | 6..8 | SURFACE | Wittenberg/Kulcinski |
| Mercury — PSR floors | Water (radar-bright ice, thin organic lag) | 0.50 / 0.80 / 0.95 | 7..10 | SURFACE (lag ≤0.3 m) | MESSENGER; purer than lunar |
| Mars — mid-latitude ice (SWIM zones) | Water (excess ice) | 0.17 / 0.45 / 0.81 | 5..8 | SHALLOW–DEEP | SWIM/SHARAD 30–90 vol% → mass frac |
| Mars — hydrated minerals (equatorial) | Water (gypsum/smectite) | 0.03 / 0.06 / 0.10 | 6..8 | SURFACE | CRISM |
| Mars — hematite/magnetite plains | IronSteel ore (Fe-oxides) | 0.10 / 0.18 / 0.30 (as Fe) | 6..8 | SURFACE | Meridiani hematite |
| Mars — rare hydrothermal sites | Copper ore | 0.002 / 0.005 / 0.02 | 4..5 | SHALLOW | Jezero-class; sparse by design (B15) |
| Mars / Venus / Titan atmospheres | CO2/N2/Ar; CO2/N2; N2/CH4 | fixed comp. (§3.2) | ∞ | — | Viking/MSL, Venera, Huygens |
| Titan — seas (Ligeia-class) | Methane (+lumped ethane) | fixed: CH4 .71 / C2H6 .12 / N2 .17 | ∞ | LIQUID | Cassini radar (Kraken-class rolls .45/.40/.15) |
| Icy-crust clean — Titan bedrock, Europa, Enceladus, Titania/Oberon/Miranda, Charon, Pluto/Triton bedrock | Water (ice crust) | 0.85 / 0.95 / 1.0 | 8..10 (∞-ish) | SURFACE | Cassini/Galileo/Voyager 2/New Horizons |
| Icy-crust dirty — Ganymede, Callisto | Water (ice-rock crust) | 0.40 / 0.60 / 0.80 | 8..10 (∞-ish) | SURFACE | Galileo bulk densities |
| Triton — N2 ice plains & polar cap | Nitrogen (N2 ice, CH4/CO traces) | 0.70 / 0.85 / 0.95 | 9..12 (∞-ish) | SURFACE | Voyager 2; 38 K sublimation mining |
| Pluto — Sputnik Planitia | Nitrogen (N2-ice glacier) | 0.85 / 0.93 / 0.98 | ∞ | SURFACE | New Horizons |
| NEA/belt — C-type | Water (phyllosilicate-bound) | 0.05 / 0.08 / 0.20 | 3..7 | bulk | CI/CM chondrites; Ryugu/Bennu |
| NEA/belt — C-type | Carbon (organics) | 0.02 / 0.03 / 0.05 | same body | bulk | CI chondrite C |
| NEA/belt — C-type | Nitrogen (NH3-salts/organics) | 0.001 / 0.003 / 0.005 | same body | bulk | Bennu NH3-bearing samples |
| NEA/belt — S-type | IronSteel (NiFe grains) | 0.05 / 0.10 / 0.20 | 4..7 | bulk | ordinary chondrites |
| NEA/belt — M-type | IronSteel (massive NiFe) | 0.50 / 0.80 / 0.95 | 5..9 | bulk | Psyche-class; high-metal members honestly rare |
| M-type — carbonyl residue | RareEarths [LUMPED PGM] | 10 / 40 / 100 ppm of metal mass | from metal | — | Kargel 1994 |
| Ceres — crust | Water ice | 0.20 / 0.30 / 0.45 | 8..10 | SHALLOW | Dawn GRaND |
| Ceres — clays | Ammonia (ammoniated phyllosilicates) | 0.005 / 0.01 / 0.02 | 6..8 | SURFACE | Dawn VIR |
| Phobos/Deimos | Water (uncertain!) | 0.00 / 0.02 / 0.05 — **may roll ZERO** | 5..7 | SHALLOW | genuinely unresolved (F-13: survey first) |

---

## 3. ISRU CHEMISTRY & HARDWARE

### 3.1 Extraction model (M-3)

```
ṁ_product  = Q_feed · g(d) · R_tier        (M-3a)
ṁ_tailings = Q_feed − ṁ_product            (M-3b)  → Tailings pile (→ Regolith 1:1)
P_draw     = P_fixed + e_dig · Q_feed      (M-3c)
```

- Recoveries: **R = 0.60 (T1), 0.75 (T2), 0.90 (T3)**; T4 uses 0.90 unless overridden (He3 Kiln R = 0.70 is a deliberate override). Capture Bag adds +0.10.
- `e_dig` = 1.0 kWh/t loose regolith (RASSOR anchor); **×3** for ice-cemented PSR regolith; ×2 wear multiplier on maintenance for PSR digging.
- **Bulk Regolith rule:** plain Regolith extractable at ANY surface site without a Deposit: g = 1.0, R = tier recovery, unlimited tonnage at site scale.
- **Catalog power convention (binds M-3c):** Power column = total P_draw at 100% util at reference grade; **P_fixed = 20%** of that. Grade-dependent water extractors (Thermal Ice Corer, Sublimation Tent, Ice Strip Miner) hold power fixed and recompute output from M-3d at sampled g(d); all other machines hold throughput fixed and scale P_draw.

**Thermal water extraction energy (M-3d)** — the main way grade bites:
```
E_water(g) = [0.79 + 0.044 · (1/g − 1)] / η_th   kWh per kg H2O
η_th = 0.5 (T1), 0.7 (T2), 0.85 (T3 heat recuperation)
```
Examples (T2): g=5% → 2.3 kWh/kg; g=1% → 7.4; g=50% (Mars massive ice) → 1.2. Add **+0.1 kWh/kg water-cleanup** (integrated into the extractors — no separate machine). Contaminants exit as fraction `f_c ~ U(0.02, 0.08)` of water mass (rolled per Water deposit at world-gen) into a **sour-gas** stream, fixed composition [SIMPLIFIED, LCROSS]: CO2 0.45 / NH3 0.20 / H2S 0.15 / SO2 0.10 / light HC 0.10 by mass. Fractionator (RX-13) recovers CO2 + Ammonia fractions (0.65); the remaining 0.35 is flared (F-11 habitat air-quality input if adjacent).

### 3.2 Atmospheric & liquid intake (M-3e/f)

`ṁ_i = V̇ · ρ_atm · x_i`; ideal compression `W = R_s·T·ln(P_out/P_in)`, real ×4; P_out = 100 kPa canonical delivery.

| Location | P | T | ρ_atm | Composition (mass) [SIMPLIFIED: molar applied as mass] | Intake energy |
|---|---|---|---|---|---|
| Mars surface (datum) | 0.61 kPa | 210 K | 0.016 kg/m³ | CO2 96.0 / Ar 1.93 / N2 1.89 % | 0.6 kWh/kg (Intake I), 0.4 (Intake II) — cryo-freezers |
| Venus aerostat 52–56 km | 45–81 kPa | 293–330 K | 0.8–1.3 kg/m³ | CO2 96.5 / N2 3.5 % | 0.07 kWh/kg |
| Titan surface | 146.7 kPa | 93.7 K | 5.3 kg/m³ | N2 ~94.5 / CH4 ~5 % | 0.01 kWh/kg |

- Mars cryo-freezer intakes (both T2, IS-06 unlock behind discovery DSC-04 in 11) deliver **pure CO2** + a residual **Ar/N2 mixed-gas stream (4% of throughput)** needing a Fractionator. Venus/Titan ram intakes deliver **mixed gas** (always fractionate). Fractionation = 0.25 kWh/kg processed (RX-13).
- Mars intakes consume **1 HEPA filter cartridge (MachineParts) per 100 t gas** (MOXIE dust precedent). Mars dust storms (F-4, 03 owns curve): intakes keep working at HEPA ×3 consumption; solar power collapses to as low as ×0.04.
- **Titan seas (M-3f):** Sea Pump draws bulk liquid at fixed Q; Ligeia-class CH4 0.71/C2H6 0.12/N2 0.17 by mass; Kraken-class 0.45/0.40/0.15. Fractionation splits out N2; ethane lumps into Methane at **0.93 kg CH4-equivalent per kg C2H6** (B14). Sea Pump inlet heater: 2 kWe of its 4 kWe budget; unpowered heater → throughput −50% (F-8).
- **Xenon trap (F-15):** Mars Xe = 0.24 ppm by mass — same mixing ratio as Earth air but ~4,000 t gas/kg Xe; Fractionator UI marks it NOT RECOVERABLE (throughput-uneconomic). Argon is the intended pivot.

### 3.3 Extraction machine catalog (§4.4)

| Machine | Tier | Mass | Power | Feed throughput | Feed type | Notes / anchor |
|---|---|---|---|---|---|---|
| Drum Excavator | T1 | 0.15 t | 0.4 kWe | 2.5 t/day | loose regolith | RASSOR-class; e_dig 1 kWh/t |
| Bucket-Wheel Excavator | T2 | 3 t | 12 kWe | 100 t/day | regolith (×3 power on icy) | IPEx → small BWE lineage |
| Strip Miner | T3 | 25 t | 200 kWe | 1,500 t/day | regolith | autonomous fleet-scale |
| Thermal Ice Corer | T1 | 0.25 t | 3.0 kWe (heat) | → 20 kg H2O/day @ g=5% | downhole sublimation | Honeybee PVEx; output scales per M-3d |
| Sublimation Tent Miner | T2 | 6 t | 80 kWt + 6 kWe | → 800 kg H2O/day @ g=5% | tented surface patch | Sowers/CSM thermal mining; kWt can be solar concentrator |
| Ice Strip Miner | T3 | 30 t | 870 kWe | → 10 t H2O/day @ g=5% | excavate+oven integrated | 870 kWe = M-3d(T3, g=5%, +0.1) + 222 t/day feed × 3 kWh/t |
| Mars Rodwell Rig | T2 | 2 t | 25 kWt + 2 kWe | → 1.2 t H2O/day | massive buried ice, **g ≥ 0.5 only** | **M-3d exempt** (melts, no vacuum): 0.54 kWh/kg H2O; needs Deep Core Rig survey |
| Atmospheric Intake (Mars) I | T2 | 0.3 t | 5 kWe | 200 kg/day | Mars atmo | cryo-freezer, 0.6 kWh/kg; HEPA consumable; IS-06 gate; **no T1 Mars intake exists** |
| Atmospheric Intake (Mars) II | T2 | 1.0 t | 18 kWe | 1,000 kg/day | Mars atmo | 0.4 kWh/kg + Ar/N2 byproduct via Fractionator |
| Aerostat Intake (Venus) | T3 | 0.5 t | 6 kWe | 2,000 kg/day | Venus 52–56 km | + cloud-water harvester 2 kg H2O/day (honestly tiny); upkeep ×2 (F-9 H2SO4) |
| Atmospheric Intake (Titan) | T3 | 0.3 t | 2 kWe | 5,000 kg/day | Titan atmo | dense cold gas; near-free liquefaction |
| Sea Pump (Titan) | T3 | 0.8 t | 4 kWe | 20 t/day liquid | Titan sea (shore/sub per 10) | heated inlet vs icing (F-8) |
| Volatile Bake Oven | T2 | 2 t | 40 kWe-or-kWt | 10 t/day crushed feed | C-type rubble, icy regolith | 500 °C; releases Water/CO2/NH3/N2 per grade; pairs w/ Fractionator |
| Capture Bag + Grinder | T2 | 1.5 t | 8 kWe | 15 t/day | whole bodies ≤ 20 m | ARM Option A; **R +0.10**, zero debris |
| Anchored Grinder Head | T2 | 0.6 t | 5 kWe | 6 t/day | anchored asteroid surface | 4 microspine anchors included |
| Optical Mining Rig | T3 | 4 t | 1 kWe (+free solar kWt ×1/d_AU²) | 30 t/day @ 1 AU | bagged C-type | TransAstra Apis; thermal only — **no O2 from silicates** |
| Beneficiation Separator | T2 | 1.5 t | 10 kWe | 50 t/day feed | regolith → concentrate | 0.02 kWh/kg feed; g_c = min(k·g_feed, 0.90), k = 8 ilmenite / 10 NiFe; mineral recovery 0.80; concentrate mass = feed·g_feed·0.80/g_c; rest → tailings |
| Cryo Liquefaction Skid | T1 | 1.2 t | 25 kWe | any gaseous M-5 product | gas → liquid | rate = nameplate/E_liquefy: ≈50 kg/day LH2, ≈860 LOX, ≈750 LCH4; ZBO coolers separate |
| Cryo Liquefaction Skid II | T2 | 4.8 t | 113 kWe | any gaseous M-5 product | gas → liquid | ×5 throughput, −10% specific energy |
| He3 Volatile Kiln [SPECULATIVE] | T4 | 50 t | 400 kWe + 1,600 kWt | 2,000 t/day | high-Ti mare regolith, 700 °C | → 14 g He3/day @ 10 ppb (R = 0.70 override) + per tonne feed: 50 g H2, 20 g He4, 100 g N2, 150 g C (as CO2/CO), 30 g H2O; ~85% thermal recuperation assumed |

### 3.4 Chemical recipe catalog (RX-01..22) — complete

All balances conserve mass ±1%. Energy column (kWh per kg of **bold** product) is canonical; nameplate kWe is derived. `P_t < 0` = waste heat to radiators (09); catalysts/electrodes = MachineParts upkeep, not reagents.

| RX | Plant (Tier) — mass, kWe, nominal rate | Inputs (kg) → Outputs (kg), per kg primary | Energy (kWh/kg) | Thermal | Op temp | Anchor |
|---|---|---|---|---|---|---|
| RX-01 | PEM Electrolyzer (T1) — 1.0 t, 58 kWe, 250 kg H2O/day | 1 H2O → **0.112 H2** + 0.888 O2 | 5.6 /kg H2O | — | 350 K | ISS OGA; PEM ~50 kWh/kg H2 (79% HHV) |
| RX-02 | SOEC Electrolyzer (T2) — 2.5 t, 200 kWe, 1,000 kg H2O/day | same balance | 4.8 /kg H2O | — | 1100 K | SOEC industry |
| RX-03 | Sabatier Reactor (T1) — 0.8 t, 0.8 kWe, 91 kg CH4/day | 2.75 CO2 + 0.50 H2 → **1 CH4** + 2.25 H2O | 0.2 /kg CH4 (electric) | **P_t = −1.8 kWh_t/kg CH4 net (canonical, 09 H-0 ledger)**; gross exotherm 2.86; ≈6.8 kWt net at full rate | 600 K, Ni/Ru | ISS Sabatier; ΔH −165 kJ/mol |
| RX-04 | RWGS Reactor (T2) — 1.0 t, 6 kWe, 240 kg H2O/day | 2.44 CO2 + 0.111 H2 → 1.556 CO + **1 H2O** | 0.6 /kg H2O (incl. 1070 K heat) | — | 1070 K | Mars ISRU studies; ΔH +41 kJ/mol |
| RX-05 | SOXE CO2 Electrolyzer (T0 demo / T2 plant) — demo 17 kg, 0.36 kWe, 0.29 kg O2/day; plant 1.5 t, 35 kWe, 100 kg O2/day | 2.75 CO2 → **1 O2** + 1.75 CO | demo 30; plant 8 /kg O2 (theor. 4.9) | — | 1070 K | **MOXIE** (17.1 kg, ~300 W, 6–12 g/hr, 122 g total) |
| RX-06 | Bosch Reactor (T2) — 0.5 t, 3 kWe, 50 kg C/day | 3.67 CO2 + 0.333 H2 → **1 Carbon** + 3.0 H2O | 1.5 /kg C | mildly exothermic (≈−90 kJ/mol; folded into Energy) | 800–1000 K | ISS CO2-reduction studies |
| RX-07 | Ilmenite H2-Reduction Line (T2) — 4 t, 58 kWe, 100 kg O2/day | 9.5 contained ilmenite (≈11.9 concentrate @ g_c 0.80; 2.4 gangue → tailings) → **1 O2** + 3.5 IronSteel + 5.0 TiO2 slag; H2 recycled, 2% makeup | 14 /kg O2 (incl. beneficiated feed + electrolysis) | — | 1250 K | Apollo/Artemis lunar O2 baseline; needs Beneficiation upstream |
| RX-08 | Carbothermal Reactor (T2/T3) — 3 t, 20 kWe + 45 kWt, 50 kg O2/day | 6.7 regolith → **1 O2** + 0.35 Si-Fe mix + 5.37 slag; CH4 makeup 0.02 | 30 /kg O2 | +45 kWt process heat (can be concentrated solar) | 1900 K | NASA/Sierra **CaRD** 2023; ~15% O2 yield |
| RX-09 | Molten Regolith Electrolysis Cell (T3) — 12 t, 365 kWe, 250 kg O2/day | 4.0 any regolith → **1 O2** + 0.7 Fe-Si (IronSteel-grade) + 2.3 slag | 35 /kg O2 | — | 1900 K | MIT MRE (25–50 kWh/kg); anode = MachineParts upkeep ×3 |
| RX-10 | Mond Carbonyl Refinery (T3) — 3 t, 42 kWe, 500 kg metal/day | 1.04 crushed NiFe → **1 IronSteel** (carbonyl-pure) + 0.04 PGM residue → RareEarths at deposit ppm; CO loop, 0.05 Carbon makeup/kg | 2 /kg metal | — | 330–500 K (Fe(CO)5 at 10 MPa) | INCO Clydach 1902; Lewis; gravity-insensitive; F-7 toxic-leak event in crewed modules |
| RX-11 | Anorthite Aluminum Line (T3) — 8 t, 125 kWe + 20 kWt, 100 kg Al/day | 6.4 highland regolith → **1 Aluminum** + 0.6 Silicon + 1.5 O2 + 3.3 Ca-silicate slag | 30 /kg Al (Earth H-H 13–15; lunar penalty honest) | +20 kWt | 1300 K | NASA SP-509 [SIMPLIFIED]; Cl2 loop MachineParts-hungry |
| RX-12 | H2-DRI Steel Plant (T2) — 3.5 t, 39 kWe, 250 kg Fe/day | 1.43 Fe2O3 concentrate → **1 IronSteel** (+0.48 H2O internal loop, 3% H2 makeup) | 3.7 /kg Fe | — | 1200 K | HYBRIT pilot (~3.5 MWh/t) |
| RX-13 | Cryo Fractionator (T2) — 1.2 t, 21 kWe, 2,000 kg/day | mixed gas/liquid → pure canonical streams per input composition vector | 0.25 /kg processed | — | 80–250 K | air-separation industry |
| RX-14 | Haber Ammonia Loop (T2) — 0.6 t, 2.1 kWe, 50 kg NH3/day | 0.824 N2 + 0.176 H2 → **1 Ammonia** | 1.0 /kg NH3 (loop only; H2 priced upstream) | exothermic −46 kJ/mol (folded) | 700 K, 20 MPa Fe cat. | Haber-Bosch |
| RX-15 | Polymers — **alias only; canonical recipe = 05's `polymers_mto`** (fab_chem_plant, T1 build, IS-09a unlock) | (verbatim from 05) 1.20 Methane + 1.20 Oxygen → **1 Polymers** + 1.22 Water + 0.16 CO2 + 0.02 Hydrogen | 1.5 (05 canon) | — | varies | methanol/MTO route, 95% C efficiency |
| RX-16 | Siemens Silicon Refiner (T3) — 5 t, 100 kWe, 20 kg/day | 1.4 Silicon(met) → **1 Silicon(solar)** + 0.4 recycle loss | 120 /kg | — | 1400 K | Siemens process |
| RX-17 | Basalt/Glass Furnace (T2) — 2 t, 31 kWe, 500 kg/day | 1.05 Regolith/tailings → **1 BasaltFiber or Glass** | 1.5 /kg | — | 1650 K | terrestrial basalt-fiber industry |
| RX-18 | FFC Titanium Cell (T3) — 3 t, 47 kWe, 25 kg/day | 1.67 TiO2 slag → **1 Titanium** + 0.67 O2-bearing offgas | 45 /kg Ti | — | 1200 K, CaCl2 melt | FFC Cambridge (vs Kroll ~100) |
| RX-19 | Pu-238 Line (T3) — reactor add-on, 2 t | Np-237(n,γ) in fission flux → **20 g Pu238/year per 100 kWe-class core** + Uranium chain upkeep | — | — | — | Oak Ridge line (player gets grams) |
| RX-20 | MMH Synthesis Loop (T3, B11) — 1.2 t, 8.3 kWe, 25 kg MMH/day | 0.74 Ammonia + 0.35 Methane → **1 MMH** + 0.09 Hydrogen (recycle to RX-14/RX-03 or vent) | 8 /kg MMH | — | 320–400 K | Raschig/ketazine routes [SIMPLIFIED net: 2NH3+CH4→CH6N2+2H2]; ambient-storable, no M-5 step |
| RX-21 | NTO Arc Synthesis Plant (T3, B11) — 2 t, 31 kWe, 50 kg NTO/day | 0.30 Nitrogen + 0.70 Oxygen → **1 NTO** | 15 /kg NTO | — | 3000 K arc / 294 K condenser | Birkeland–Eyde; ambient-storable, no M-5 step |
| RX-22 | Recycler (T2, B16) — 2 t, 19 kWe, 500 kg/day reclaimed | 1.25 scrap (05 `loss_t` streams, decommissioned hardware, worn parts) → **1 reclaimed canonical resources** (split per source composition vector; Electronics scrap → metal/RareEarths fractions, never Electronics) + 0.25 unrecoverable → Regolith | 0.9 /kg reclaimed | — | 1700 K melt / 600 K pyrolysis | terrestrial scrap; **reclaims 80% of process losses** |

### 3.5 End-to-end propellant chains (M-7 / §4.6 — canonical cross-checks for 09)

All figures include liquefaction to M-5 state:

| Chain | Route | Headline energy |
|---|---|---|
| A — Mars methalox (Act 3 flagship) | buried ice (g≈0.6) + Intake II CO2 → RX-01 → RX-03 → liquefy; O/F 3.6; per kg propellant basis: 32.6 kWh / 4.6 kg | **≈7.1 kWh/kg propellant** (+0.36 kg surplus O2/4.6 kg → life support) |
| B — Lunar hydrolox from PSR ice (Act 2) | g=5% T2 ice (3.1) + RX-01 (7.2) + LH2 liq (1.7) + LOX liq (0.6); O/F 6.0, H2-limited, 1.28 kg H2O/kg | **≈12.6 kWh/kg** (11.8 @ g=10%, 16.4 @ g=1.5%) + 0.27 kg surplus O2 |
| C — LOX-only (Act 2 alt) | MRE (RX-09) on any regolith, zero prospecting risk | **≈35.7 kWh/kg LOX** (35 + 0.7 liq); SOXE from Mars CO2: **≈9.8** (8 + 1.1 acquisition + 0.7 liq) |
| D — C-type water depot (Act 3–4) | Bag-and-grind @ g=8%, R=0.85 (0.75+0.10): oven 2.0 + grind 0.2 + cleanup 0.1 | **≈2.3 kWh/kg H2O**; byproducts/kg H2O: 0.37 CO2, 0.04 N2/NH3 via Fractionator |
| E — Titan methalox (Act 5) | CH4 near-free (0.005–0.01); ALL O2 from ice bedrock: 0.88 kg H2O → ice 0.8 + RX-01 4.9 + LOX liq 0.55 | **≈6.3 kWh/kg propellant**; LCH4 liq ~free at 94 K; fission mandatory at 9.5 AU |

Worked sizing canon (quoted by 09 & 12): **100 t methalox in 500 days = 200 kg/day × 7.1 = ≈59 kWe continuous** — one 100 kWe fission unit or ~0.4 ha Mars solar w/ dust margin.

### 3.6 Intermediate streams (non-canonical inventory objects)

Schema (05/13): name, form, bulk density, composition vector where noted. **Disposal rule: unconsumed intermediate solids → Regolith 1:1; mixed gas in a full tank vents (destroyed); sour gas flared unless fractionated.**

| Stream | Form | Bulk ρ kg/m³ | Producer | Consumer | If unconsumed |
|---|---|---|---|---|---|
| Ilmenite concentrate (g_c) | bulk granular | ~2,500 | Beneficiation Separator | RX-07 | → Regolith |
| NiFe concentrate (g_c) | bulk granular | ~4,000 | Beneficiation Separator | RX-10 | → Regolith |
| Fe2O3 concentrate | bulk granular | ~2,800 | Beneficiation (magnetic, Mars) | RX-12 | → Regolith |
| TiO2 slag | bulk granular | ~2,400 | RX-07 | RX-18 | → Regolith |
| Si-Fe metal mix | ingot | ~5,000 | RX-08 | auto-splits: 0.5 IronSteel + 0.5 Silicon(met) per kg [SIMPLIFIED] | n/a (splits) |
| Generic / Ca-silicate slag | bulk | ~2,900 | RX-08/09/11 | RX-17 (counts as Regolith feed) | → Regolith |
| Mixed gas | tank + composition vector | per comp. | intakes, Volatile Bake Oven | RX-13 | held; vents if full |
| Sour gas | tank, fixed comp. (§3.1) | per comp. | ice cleanup, RX-10 purge | RX-13 (recovers CO2+NH3) | flared (F-11) |

### 3.7 Microgravity mining (M-6)

1. **Anchoring:** Σ(tool force) ≤ 0.5 × Σ(anchor capacity), else tool refuses to run. Capacities: microspine pad 250 N (half on monoliths→ no, see 4), rock-bolt 2,000 N (1 h install, monolithic only), capture bag unlimited. Tool forces: corer 100 N, enclosed grinder 500 N, bucket excavator 2,000 N. Override after damage = 5%/h anchor rip-out → free-floating debris hazard (F-6).
2. **Bag-and-grind:** bodies ≤ 20 m dia (~10⁴ t @ ρ2000) fully enclosed: R +0.10, zero debris. Larger: anchored shrouded grinders.
3. **Debris rule:** unenclosed handling at g < 0.01 m/s² loses 15% throughput as escaping debris + local hazard counter (damage ×3 within 1 km, 06 model).
4. **Spin barrier:** P_rot < 2.2 h ⇒ monolithic (rock-bolts allowed, microspines at HALF capacity). Optional despin: `m_prop = I·ω/(v_e·r)`, 8 h setup.
5. **Optical mining (T3):** replaces excavator+oven for bagged C-types; thermal power = free sunlight × 1/d_AU².
6. F-12: mining the whole body allowed (tonnage = body mass × grade); no orbital effect, ship CoM/thrust effect real; bag reusable.

### 3.8 Tailings & maintenance (M-8/M-9)

- Tailings → **Regolith** 1:1; pile slots: 1 per 10,000 t, finite per site (07 grid); full slots stall extractors (F-10 — sinter, export, or bag).
- Spares (05 owns): `M_spares = k_env × machine_mass / year`; k_env = 0.02 orbital / 0.04 dusty surface (Moon, Mars) / 0.03 clean surface & Titan. Process multipliers stack: ×2 PSR ice digging, ×2 Venus aerostat external, ×0.5 in pressurized workshops; lunar-dust ×2 is ALREADY the 0.04 — don't double-apply. Parts-starved machine: utilization cap −2%/day, floor 20%.
- F-5 PSR thermal pollution: >10 kWt rejected at >110 K in a PSR cell for >30 consecutive days → every Water deposit in cell loses 1%/yr of g0 while violated.

### 3.9 Tier / Act progression mapping (unlock graph lives in 11)

| Tier (Act) | Unlocks in this domain |
|---|---|
| T0 (Act 1) | Orbital spectrometers; SOXE demo (MOXIE-scale RX-05 demo); everything else Earth-purchased |
| T1 (Act 1–2) | Drum Excavator, Thermal Ice Corer, RX-01 PEM, RX-03 Sabatier, Core Drill, Cryo Liquefaction Skid, vapor-return cryo transfer |
| T2 (Act 2–3) | Bucket-Wheel, Sublimation Tent, Beneficiation, RX-02/04/05-plant/06/07/08/12/13/14/17, RX-22 Recycler, Mars Intakes I & II (IS-06 gate), Rodwell, Capture Bag, Volatile Oven, Deep Core Rig |
| T3 (Act 3–5) | Strip Miners, RX-09 MRE, RX-10 Mond, RX-11 Al, RX-18 FFC Ti, RX-16 Siemens, RX-19 Pu238, RX-20 MMH + RX-21 NTO (B11), Optical Mining, Venus Aerostat Intake, Titan Sea Pump/Intake |
| T4 (Endgame) [SPECULATIVE] | He3 Volatile Kiln; gas-giant scoop (02 fusion tier) |

2D note: PSR access modeled as polar *sites* with permanent-shadow tags (03 owns) — no plane changes needed anywhere in this domain.

### 3.10 UI surfaces & alert requirements (grammar owned by 12)

- **Survey overlay** (map): deposit icons by resource class, K-state badge, `ĝ ± σ` band; K3+ renders the radial grade-contour heat ring; un-surveyed bodies show "?" + required instrument.
- **Deposit panel:** resource, K-state with "next step" action (e.g. "Send rover: 2d + travel"), tonnage band, grade band, depth class, machines on site with their sampled g(d).
- **Plant/flow panel** (mass-true Factorio-style): per machine input→output rates, utilization bar, bottleneck cause (POWER / FEED / STORAGE / PARTS), specific energy, waste-heat line. Site-level **Sankey view** so losses (boiloff, flared sour gas, debris) are visible.
- **Production planner:** target ("100 t methalox by day X") → back-computed continuous kWe + feed rates from §3.5 chains, flagged against installed power and deposit tonnage. Core engineering-sim loop.
- **Alerts** (global bus, 12): deposit <90 days at current draw; tank full; ZBO power lost (boiloff venting + mass-loss rate); survey estimate revised on K-upgrade ("assay day" — show old vs new); MachineParts starvation.
- **Warp:** all flows linear; scheduler pre-computes earliest of {tank full, tank empty, deposit exhausted, parts depleted}; auto-drop warp at severity ≥ amber. State at t+Δt is closed-form — no drift between warp rates (F-16; 13 owns the invariant test; matches existing `next_boundary_after`).

---

## 4. GAP vs CODE

### 4.1 What exists today

- `aphelion/sim/ledger/network.py` — LedgerNetwork: pooled per-resource Buffers, Module (inputs/outputs **already in kg-per-kg-of-primary form — recipes map 1:1**), Source (flat-rate deposit with finite `remaining`), analytic boundary advance, power throttle fixed-point, Battery, MTBF pre-rolls, heat_kw slot. Solid foundation; matches M-4a shape.
- `aphelion/game/basebuild.py` — CATALOG of 12 modules: `drill_ice`, `electrolyzer`, `sabatier`, `co2_intake`, `lake_pump`, `solar_array`, `reactor_100`, `battery_pack`, `radiator_wing`, `science_lab`, `hab_module`, `tank_farm`.
- `aphelion/content/validate.py` — full canonical resource list (29 + RP1/NTO/MMH/Wafers/MedSupplies/SurveyData) and recipe mass-balance check (0.5%).

### 4.2 Numeric divergences in existing modules (energy is OFF by 3–10×)

| Code module | Code implies | Canon | Fix |
|---|---|---|---|
| `drill_ice` (25 kW, 0.03 kg/s) | 0.23 kWh/kg H2O, grade-free, placeable flat-rate | M-3d: 2.3 kWh/kg @ g=5% T2; output must recompute from sampled g(d) | replace with Thermal Ice Corer / Sublimation Tent / Ice Strip Miner / Rodwell rows |
| `electrolyzer` (80 kW, 0.02 kg/s O2) | ≈0.99 kWh/kg H2O | RX-01: 5.6 kWh/kg H2O (58 kWe @ 250 kg/day) | stoich is right (1.125 H2O → 1 O2 + 0.125 H2 ≡ RX-01); fix power/rate |
| `sabatier` (30 kW, 0.01 kg/s CH4) | 0.83 kWh/kg CH4, no heat credit | RX-03: 0.2 kWh/kg e⁻, **P_t −1.8 kWh_t/kg** to radiators | stoich exact match; fix power, add thermal credit |
| `co2_intake` (12 kW, 0.05 kg/s) | 0.067 kWh/kg, free pure CO2 anywhere | Intake I/II: 0.4–0.6 kWh/kg, T2/IS-06 gate, +4% Ar/N2 mixed stream, HEPA/100 t | rescale; add byproduct stream + consumable |
| `lake_pump` | pure Methane out | M-3f: mixed CH4/C2H6/N2 liquid → Fractionator; ethane ×0.93 lump; inlet-heater F-8 | add composition + RX-13 dependency |
| `tank_farm` / `starter_network` | 5 resources only (Water/Oxygen/Hydrogen/Methane/CO2) | 29+ resources, per-class tankage (cryo vs press vs bulk) | extend buffers + storage classes |

### 4.3 Missing systems (entire subsystems, not tweaks)

1. **Deposit model (M-1):** no Deposit object — `Source.remaining` is the only stub. Missing: grade g0, Gaussian falloff g(d) by extractor placement, r_core, depth_class, tonnage rolls, bulk-body deposits, infinite atmosphere/sea deposits born K4, per-deposit f_c contaminant roll.
2. **Prospecting/K-ladder (M-2):** nothing exists. K0–K4 states, one-shot lognormal estimate rolls, orbital survey timer (M-2a) tied to vessel altitude + instrument power, surface survey, core sampling, microgravity variants, pilot-extraction K4, tier-gating of machine placement by K-state, collateral hook to 12.
3. **Survey instruments (§2.3):** none of the 6 exist as parts/modules.
4. **Extraction tiers & recovery (M-3):** no R_tier (0.60/0.75/0.90), no e_dig term, no icy ×3, no bulk-Regolith free-mining rule, no grade-dependent M-3d water energy.
5. **Extraction hardware:** 17 of 19 catalog machines missing (only crude `drill_ice`/`co2_intake`/`lake_pump` analogs exist). Notably: all excavators, all three ice-miner tiers, Rodwell, Venus/Titan intakes, Volatile Bake Oven, Capture Bag, Anchored Grinder, Optical Mining, **Beneficiation Separator**, **Cryo Liquefaction Skids**, He3 Kiln.
6. **Recipes:** 3 of 22 RX recipes exist (RX-01/03 approximately, RX-05-ish nothing). Missing entirely: RX-02 SOEC, RX-04 RWGS, RX-05 SOXE (MOXIE), RX-06 Bosch, RX-07 ilmenite, RX-08 carbothermal, RX-09 MRE, RX-10 Mond, RX-11 anorthite Al, RX-12 H2-DRI, RX-13 Fractionator, RX-14 Haber, RX-16 Siemens, RX-17 basalt/glass, RX-18 FFC Ti, RX-19 Pu238, RX-20 MMH, RX-21 NTO, RX-22 Recycler. Plus plant scaling rule (×4 mass/×5 rate/−10% energy).
7. **Composition-vector streams:** ledger buffers are scalars; **mixed gas / sour gas / scrap need composition vectors** (§3.6) plus the Fractionator that splits them and the disposal rules (slag→Regolith, vent, flare). This is the biggest architectural delta to `LedgerNetwork` (pooled one-buffer-per-resource rule vs per-stream composition).
8. **Liquefaction & cryo handoff (M-5):** products today appear in buffers with no gas/liquid state. Missing: Liquefaction Skid machines, E_liquefy charges, ZBO power rule (M-5a), passive boiloff venting as destroyed mass, transfer ullage 1.5%/0.3%.
9. **Silicon grade flag** {met, solar} — needs a resource attribute or paired buffer.
10. **Tailings (M-8):** no tailings entity, pile slots, site-slot stall, or 1:1 Regolith conversion.
11. **Maintenance (M-9):** Modules have MTBF only; no MachineParts consumption (k_env × mass/yr), process multipliers, −2%/day starvation degradation, <30%-utilization ×2 wear (F-14), HEPA consumable.
12. **Microgravity mining (M-6):** anchoring force ledger, bag-and-grind R bonus, 15% debris loss + hazard counter, spin barrier/despin, optical mining solar scaling — all absent.
13. **Thermal accounting:** `heat_kw` exists but recipe-level P_t (Sabatier −1.8 kWh_t/kg credit, RX-08 +45 kWt demand, kWt-from-solar-concentrator option) is not modeled; 09's H-0 ledger consumes these numbers.
14. **Failure/edge rules F-1..F-16:** assay shock (free — falls out of M-2), 90-day exhaustion warning, ZBO-loss venting, dust-storm HEPA ×3, PSR thermal pollution, anchor rip-out, carbonyl leak, Titan icing, Venus corrosion, tailings lockout, sour-gas habitat input, whole-asteroid consumption, Xenon NOT-RECOVERABLE flag.

### 4.4 Implementation notes

- The Module recipe format (kg per kg primary) means §3.4 tables paste directly into CATALOG-style dicts; add fields: `tier`, `mass_t`, `p_thermal_kwh_per_kg`, `op_temp`, `feed_grade_dependent`, `k_state_required`, `consumables` (HEPA/MachineParts), `intermediate_streams`.
- Mixed-gas handling could ship v1 as N parallel buffers per intake site (one per species at fixed composition ratios enforced by the Fractionator module's stoichiometry) — avoids breaking the pooled-buffer invariant while honoring composition; true composition vectors only needed for variable-comp scrap (RX-22).
- Validation: extend `validate.py` recipe check to ±1% canon and assert nameplate kWe ≈ Energy × rate / 24 h for every RX row.
