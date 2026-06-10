# 06 — Ships & Stations: Modular Construction

## 1. Overview

This document specifies how the player designs, validates, assembles, and operates every vessel in the game: launch vehicles, transfer ships, tugs, landers, and orbital stations. It defines:

- The **2D side-cross-section grid editor** (the "Drydock") and its part-attachment rules.
- The **builder math**: total mass, wet/dry mass, center of mass (COM), 2D thrust-vector alignment, live Tsiolkovsky delta-v readout, per-stage TWR, and burn times. Every formula a programmer needs is in §3.
- A **simplified structural-integrity model**: joint-graph axial load checks, g-limits, a max-Q rule, and a q-alpha rule for atmospheric ascent.
- **Station mechanics**: spin-gravity sections with real comfort limits, pressurized volume per crew, docking topology, and station-keeping budgets.
- A **catalog of 110 parts** (§4; the three aerostat envelope/gondola/inflation rows migrated to 07's catalog per DECISIONS A10) with mass, cost, tier, and stats, including inflatable habitats (TransHab anchor) and ISRU-manufactured variants (BasaltFiber/IronSteel printed structure). Engine, power and thermal entries are **builder stubs**: their performance stats are republished verbatim from the owning documents (02-propulsion.md, 09-power-thermal.md) and may not diverge.
- **Four fully worked example builds** with complete mass budgets and computed delta-v (§4.11).
- **Three construction flows**: Earth launch (pad and fairing constraints), orbital assembly, and ISRU manufacture (interfacing 05-industry-logistics.md).

Design philosophy: the editor is a *spreadsheet you can see*. Nothing is hidden — every readout traces to a formula in this document, and the same formulas drive the flight simulation. There is no "magic balance layer" between design-time numbers and flight-time physics.

Ownership boundaries: engine physics and propellant chemistry beyond catalog stats → 02-propulsion.md; power/thermal performance curves → 09-power-thermal.md; life-support consumption → 08-life-support-crew.md; surface vehicles → 10-vehicles.md; manufacturing rates and logistics containers → 05-industry-logistics.md; prices and contracts → 12-gameplay-economy-ui.md; physics engine implementation → 13-architecture.md.

## 2. Real-World Grounding

Every part and rule below names its anchor. Key anchors:

- **Chemical engines** (catalog stats canonical in 02-propulsion.md §4.2): SpaceX Merlin 1D (845 kN SL / 914 kN vac, Isp 282/311 s, 470 kg); Merlin Vacuum (981 kN, 348 s); SpaceX Raptor 2 (2,256 kN SL / 2,394 kN vac, Isp 327/347 s, 1.63 t); Raptor Vacuum (2,530 kN, 380 s [est]); Aerojet RL10C-1 (101.8 kN, Isp 449.7 s, 190 kg); RS-25 (1,860 kN SL / 2,279 kN vac, Isp 366/452 s, 3,177 kg); Shuttle OMS AJ10-190 (26.7 kN, Isp 316 s); Apollo SPS AJ10-137 (91 kN, Isp 314 s); SuperDraco (73 kN vac, 243 s [est]); SpaceX Draco RCS (400 N, Isp 300 s, 22 kg block); Star 48B solid kick stage (2,137 kg gross / 2,011 kg propellant, 87 s burn → 66 kN mean thrust; catalog Isp 286 s vac vs the published 292.1 — 02's conservative derate); GEM 63 SRB (≈49.3 t gross / 44.1 t propellant, Isp 245/275 s, 94 s burn, 1,265 kN average).
- **Nuclear-thermal** (canonical in 02 §4.3): NERVA program (XE' ground-tested 1969 at ~246 kN; delivered Isp ~710 s — 841 s was the ideal vacuum Isp excluding turbine-bleed and cooling losses; 02's NTR-246 ships 247 kN / 850 s at 12.5 t with modern composite fuel); SNRE (Schnitzler/Borowski Small Nuclear Rocket Engine, ~73 kN / ~900 s, the DRACO-class baseline behind 02's NTR-73); modern BWXT/NASA NTP studies target engine T/W ≈ 3 (NTR-73 hits 3.1, NTR-246 an honest 2.0).
- **Electric propulsion** (canonical in 02 §4.4): NSTAR (2.3 kW, 92 mN, Isp 3,120 s — flew on Deep Space 1, Dawn); SPT-100 Hall (1.35 kW, 83 mN, Isp 1,600 s — flown since 1994); NEXT-C (6.9 kW, 236 mN, Isp 4,190 s — flew on DART); AEPS Hall thruster (12.5 kW, 590 mN, Isp 2,800 s — Gateway PPE); X3 nested Hall (5.4 N at ~102 kW, lab-demonstrated 2017; catalog 100 kWe, Isp 2,000 s, η 0.52) [T3]; VASIMR VX-200 (~5.7 N at 200 kW, Isp 4,900 s, lab) [T3]; applied-field MPD thrusters (100-500 kW lab demos, NASA Lewis / Princeton LiLFA / MAI; catalog MPD-200 conservatively ships 4.6 N at 200 kWe on Argon, η 0.45) [T3].
- **Habitats**: NASA TransHab (8.2 m inflated diameter, ~340 m³, ~13.2 t); Bigelow BEAM (1.4 t, 16 m³, flown on ISS); Bigelow B330 (~20 t, 330 m³, engineering-complete design); ISS Destiny lab (14.5 t, ~106 m³); Quest airlock (6.1 t); ISS Cupola (1.8 t).
- **Habitable volume**: NASA long-duration habitability studies converge on ≈25 m³ net habitable volume per crewmember as the long-duration minimum; ISS provides ~64 m³/crew at 6 crew.
- **Spin gravity comfort**: classic NASA-era criteria (Hill & Schnitzer 1962; 1970s Stanford/NASA Ames summer studies): spin rate ≤ 4 rpm for adapted crews (≤ 2 rpm without adaptation), head-to-foot gravity gradient ≤ 8%, rim speed ≥ 6 m/s to keep Coriolis effects tolerable. Later research (Globus & Hall, 2017) argues higher rates are trainable; we keep the conservative limits and hard-cap at 6 rpm.
- **MMOD protection**: ISS Whipple shields — thin sacrificial aluminum bumper (≈2 mm = 5.4 kg/m²) at 10-30 cm standoff, vaporizing impactors before the pressure wall; "stuffed" Whipple adds Nextel ceramic-fabric/Kevlar layers (ISS US Lab shielding ≈ 20-30 kg/m² total). In-game BasaltFiber cloth is the ISRU analog of Nextel ceramic fabric.
- **Docking**: International Docking System Standard / NASA Docking System (androgynous, 800 mm passage, ~330 kg); ISS Common Berthing Mechanism (1.27 m square hatch, ~0.2-0.3 t); Canadarm2 (17.6 m reach, ~1.8 t, handles up to 116 t).
- **Ascent loads**: Space Shuttle throttled down to hold max-Q near ~33 kPa (~700 psf); modern launchers see 25-40 kPa. Typical structural q·α (dynamic pressure × angle of attack) envelopes are ~3,000-4,500 psf·deg ≈ 145-215 kPa·deg.
- **Station keeping**: ISS at ~400 km expends roughly 5-25 m/s/yr of reboost delta-v depending on solar activity; 01-orbital-mechanics.md Table 4.8 charges the canonical fee of 20 m/s/yr at 400 km, inside that bracket.
- **Tankage fractions**: Falcon 9 stages achieve propellant mass fractions ≈ 0.95+ (≈ 5-6% structure per unit propellant for kerolox/methalox); Centaur III (hydrolox) dry/propellant ≈ 0.11 including engines; dedicated LH2-only tanks with MLI and zero-boiloff cryocoolers run ~13-15% (NASA cryogenic fluid management studies). LH2 bulk density 70.8 kg/m³ is the driver. Dawn stored 425 kg Xenon in a 21.6 kg COPV (≈5%).
- **Power hardware** (stats canonical in 09-power-thermal.md): Kilopower/KRUSTY fission (1 kWe ≈ 0.4 t; 10 kWe ≈ 1.5 t); MMRTG (110 We, 45 kg); ISS legacy rigid arrays ≈ 30-35 W/kg; Roll-Out Solar Array (ROSA, flight-demonstrated) ≈ 80-100+ W/kg; Shuttle PC17C fuel cell (12 kW peak / 7 kW continuous, ~118 kg).
- **Venus aerostat**: NASA HAVOC study (Langley, 2014) — entry vehicle deploys a buoyant vehicle at ~50-55 km where Venus pressure and temperature are Earth-like; in 96.5% CO2 atmosphere (mean molecular weight ≈ 43.45 g/mol) even breathable air is a lifting gas (net lift ≈ 35% of H2's per m³; equivalently, ≈33% of the displaced CO2 mass).
- **Speculative tier anchor**: Princeton Direct Fusion Drive concept studies (PPPL/Princeton Satellite Systems): ~5 MW field-reversed-configuration fusion, thrust ≈ 20 N, Isp ≈ 10,500 s, ~1 MWe exported bus power. [SPECULATIVE], T4 only — republished from 02 §4.6 (DFD-5).

Honest 2D simplifications, stated once here: the vessel cross-section grid abstracts the third dimension (parts carry real volumes/areas as scalar stats); propellant is assumed centered in its tank (no slosh, no COM shift within a tank as it drains — but COM *does* shift between tanks); plane-change maneuvers do not exist (see 01-orbital-mechanics.md).

## 3. Game Model

### 3.1 The construction grid

- The Drydock editor is a **side cross-section 2D grid**; 1 cell = 1 m × 1 m. +y is "up" (nose), −y is "down" (engines), x is lateral.
- Each part occupies a `w × h` cell footprint (catalog column "Size") at integer position; footprints may not overlap (no clipping).
- Parts expose **attach nodes** on footprint edges: `top`, `bottom`, `left[i]`, `right[i]`. Stack nodes (top/bottom) carry full structural rating; radial nodes (left/right) carry 25% of the smaller part's axial rating (see §3.8). **Default node set**: every part exposes one `top` node, one `bottom` node, and one radial node per edge cell (an h-cell-tall part has h `left[i]` and h `right[i]` nodes) unless the catalog notes an override. Standing overrides: engines expose no `bottom` attach node (the nozzle face is exhaust-only — nothing stacks below a nozzle); heat shields and aeroshells expose no `bottom` attach node (TPS face); fairings expose interior payload nodes on their enclosed cells instead of exterior radial nodes; a docking port's outward face is a docking node only (mates to a matching port, never to structure); ST-TR8 open truss exposes interior nodes and engines may fire through it.
- A vessel is a **connected graph** G = (parts, joints). **At least one** part must be a command source (avionics core or crewed module with controls); zero command sources is validation error E1. Merged assemblies routinely carry several command sources: control authority follows the **active core** — player-designated, defaulting to the highest-tier avionics part (ties broken by proximity to the wet COM). SEPARATE and undock events re-run the rule per fragment; a fragment left with zero sources becomes debris (§8.12).
- Per-vessel part cap: **600 parts** (performance budget; see 13-architecture.md). Docking two vessels merges their graphs; the merged assembly must also respect the cap.

### 3.2 Mass properties

All masses in tonnes (t) internally stored as kg.

- **Dry mass**: `m_dry = Σ m_part_dry + Σ m_cargo + Σ m_crew_and_suits` (80 kg + 20 kg suit per crew; 08-life-support-crew.md).
- **Wet mass**: `m_wet = m_dry + Σ m_propellant + Σ m_consumables`.
- **Center of mass** (2D, computed live, wet and dry):
  `x_COM = Σ(m_i · x_i) / Σ m_i` , `y_COM = Σ(m_i · y_i) / Σ m_i`
  where `(x_i, y_i)` is each part's footprint centroid in meters. Propellant mass sits at its tank's centroid (constant while draining — stated simplification). The editor displays the wet COM (yellow), dry COM (orange), and the swept line between them.

### 3.3 Thrust vector and control authority (2D)

Each engine i has thrust magnitude `F_i` (kN), mount position `(x_i, y_i)`, thrust direction unit vector `(u_i, v_i)` (normally (0, −1) exhaust down → thrust up), and gimbal range `δ_i` (deg).

- **Net thrust**: `F_net = Σ F_i · (u_i, v_i)` (kN, vector).
- **Net torque about COM** (2D cross product, kN·m, positive = counterclockwise):
  `τ_net = Σ [ (x_i − x_COM) · F_y,i − (y_i − y_COM) · F_x,i ]`
- **Gimbal control authority**: `τ_ctl = Σ F_i · sin(δ_i) · L_i` where `L_i` = distance (m) from engine i to COM.
- **Builder flags**:
  - GREEN (stable): `|τ_net| ≤ 0.5 · τ_ctl` evaluated at both wet COM and dry COM.
  - YELLOW (marginal): `0.5 · τ_ctl < |τ_net| ≤ 0.9 · τ_ctl`.
  - RED (uncontrollable): `|τ_net| > 0.9 · τ_ctl`.
- Worked example (Build A): two EN-K1 engines at x = ±1 m, 845 kN each (SL), symmetric → τ_net = 0. One engine out: τ = 845 kN × 1 m = 845 kN·m; remaining engine authority = 845 × sin 5° × 14 m = 1,031 kN·m → flyable, since 845 ≤ 1,031 — full stop. Note that both the disturbance torque and the gimbal authority scale linearly with throttle, so throttling alone never changes the verdict; what throttling buys is margin against the throttle-independent RCS term. The full engine-out check is `|τ_fail(throttle)| ≤ τ_ctl_remaining(throttle) + τ_rcs`, displayed as the "engine-out" badge.
- RCS pods add torque authority `τ_rcs = Σ F_rcs · L_rcs` independent of main-engine gimbal; CMGs add the values in §4.8.

### 3.4 Delta-v readout (Tsiolkovsky)

The headline readout, computed live per stage:

```
dv = Isp · g0 · ln(m0 / m1)        [m/s]
g0 = 9.80665 m/s² (exact constant, used everywhere)
```

- `m0` = full mass of this stage *plus everything above it*; `m1` = m0 − propellant burned by this stage.
- **Mixed engines in one stage** use the thrust-weighted effective Isp: `Isp_eff = Σ F_i / Σ (F_i / Isp_i)`.
- **Ambient-pressure Isp** (drives both the sim and the editor's "SL / vac / trajectory-avg" toggle):
  `Isp(p) = Isp_vac − (Isp_vac − Isp_SL) · (p / 101.325 kPa)` , clamped at p = 101.325 kPa. Example: EN-K1 (282 s SL / 311 s vac) at 50 kPa ambient → 297 s. (This is 02 §3.3's back-pressure model; Isp_SL entries marked † in 02's catalog are synthetic slopes for vacuum engines, not sea-level operating claims.)
- For first stages the editor also shows a **trajectory-averaged Isp** = `Isp_SL + 0.44 · (Isp_vac − Isp_SL)` (empirical fit to the ascent profile in 01-orbital-mechanics.md; for EN-K1 this gives 295 s). The worked builds in §4.11 use this average and also print the SL/vac bounds.
- **Electric propulsion**: thrust is power-limited: `F = 2 · η · P_in / (Isp · g0)` (N, with P in W). Catalog η (02 §4.4, republished): NSTAR 0.61, NEXT 0.70, SPT-100 0.48, AEPS 0.65, X3 0.52 (−0.06 on Argon), MPD 0.45 (Ammonia or Hydrogen −0.05), VASIMR 0.69 (VX-200 at Isp 4,900 s). **Catalog thrust is authoritative**: the sim back-derives each entry's η = F · Isp · g0 / (2 · P_rated) and holds it constant when power-scaling. If available electrical power (09-power-thermal.md, including 1/d² solar falloff) is below rated, thrust scales proportionally at constant Isp. The dv readout is unchanged (dv is power-independent); the *burn time* readout is what grows.
- **Burn time**: `t_burn = m_prop / ṁ`, `ṁ = Σ F_i / (Isp_eff · g0)` (kg/s). **ṁ is a per-engine constant derived from the vacuum pair** (02 §3.3): `ṁ = F_vac / (Isp_vac · g0)` — e.g. EN-K1: 914,000 / (311 × 9.80665) = 299.7 kg/s. Thrust at ambient pressure then follows: **`F(p) = ṁ · g0 · Isp(p)`** — this is the formula the ascent sim and the TWR readout use between the SL and vac columns; small rounding versus a published SL thrust figure is accepted (02 §4.2 note). Never mix one pressure condition's F with another's Isp (e.g. Build A's 117 s stage-1 burn is 70,000 kg / 599.4 kg/s with both numbers from the same engine constant; mixing the listed SL thrust with the vacuum Isp would wrongly give 126 s).

### 3.5 Thrust-to-weight ratio

`TWR = Σ F_i / (m · g_ref)` — displayed per stage at ignition (m = m0) and burnout (m = m1), against a player-selectable reference gravity:

| Body | g_ref (m/s²) |
|---|---|
| Earth | 9.80665 |
| Moon | 1.62 |
| Mars | 3.71 |
| (others) | from 03-solar-system.md body table |

Earth's g_ref equals the g0 constant of §3.4 so the TWR and dv readouts share one constant (no third-decimal QA discrepancies); all other bodies use the surface-gravity values canonical in 03-solar-system.md.

Thresholds surfaced in UI (canonical in 02 §3.7 — one threshold set across both builder docs): atmospheric surface launch requires TWR > 1.0 at ignition (hard floor; builder warning W1 below 1.2; recommended 1.3-1.5 on Earth); airless-body liftoff TWR > 1.0 strictly, recommended ≥ 1.8 to limit gravity loss; powered landing requires TWR_local > 1.0 at the touchdown body; upper stages ≥ 0.5 recommended; NTR/EP stages may be < 1 (the maneuver planner in 01-orbital-mechanics.md warns and offers a one-click split into multiple periapsis passes when `t_burn > T_orbit/6` — threshold canonical in 01 §3.7).

### 3.6 Staging editor rules

KSP-style ordered stage list S0 (first to fire) … Sn, edited by dragging part icons:

1. Stage events: `IGNITE(engine)`, `SEPARATE(decoupler)`, `JETTISON(fairing)`, `DEPLOY(chute/panel/radiator/inflatable)`.
2. A decoupler's separation must split G into exactly two connected components; otherwise validation error E3 ("separation would not detach anything / would orphan parts").
3. dv/TWR are computed bottom-up: stage k's `m0` includes all stages > k; jettisoned mass (fairings, spent boosters) leaves the ledger at its event.
4. An engine may not fire if its exhaust column (the grid cells in a `w_engine`-wide column below its nozzle, out to 6 m, where `w_engine` = the engine part's footprint width w from its §4.3-4.5 Size column) intersects a same-vessel part that has not yet separated — error E5 "plume impingement". RCS quads are exempt (surface-mount attitude blocks, per-nozzle thrust ≤ 2 kN; see §4.5). Exception: the **vented interstage** part (ST-IS-V, anchor: Starship hot-staging ring) permits firing through it.
5. Solid motors cannot throttle or shut down; once lit they burn to depletion (warning W4 if a solid is staged above a liquid stage that ignites later).
6. **Acceleration limiter**: autopilot throttles to keep `a ≤ 4 g` with crew aboard, `a ≤ 6 g` uncrewed (player-overridable down to part limits, §3.8). The selected limiter is saved with the design, and the §3.8(a) joint check (validation E6) always evaluates at it. Solids ignore the limiter (their thrust curve is fixed).

### 3.7 Propellant flow and crossfeed

- **Mixture ratio (O/F) is an engine property** (catalog column, §4.3): methalox 3.6:1 Oxygen:Methane (Raptor), kerolox 2.36:1 Oxygen:RP1 (Merlin), hydrolox 6.0:1 Oxygen:Hydrogen (RL10), storables 1.65:1 NTO:MMH (AJ10/Draco). **RP1, NTO and MMH are canonical-resource extensions declared by 02 §4.1** (exact spellings; separate tracked resources, Earth-import at T0-T1; late ISRU synthesis routes are 04's open question; 12 must carry price rows for all three). Bipropellant *tanks* (TK-ML-*, TK-KL-*, TK-HYP-*) are merely a packaging convenience pre-loaded at the matching ratio; engines do not require them.
- **Drain rule**: an engine draws each of its propellant resources — at its O/F mass split, for bipropellants — from **all tanks within its own stage holding that resource** that are graph-connected through structural joints, proportionally across those tanks (keeps COM drift gentle). A hydrolox engine fed by separate TK-LOX-M and TK-LH2-M tanks therefore draws 6 kg Oxygen per 1 kg Hydrogen from them, exactly as it would from one combined tank. If either resource of the pair exhausts first, the engine **flames out** (§8.16); the editor's dv readout counts only *burnable* propellant (limited by the scarcer resource at the engine's O/F).
- **Crossfeed** between stages or across docking ports requires the **FD-1 fuel duct** (T1) or a fluid-transfer docking port (DK-L); this enables asparagus staging and depot refueling. Tanks connected through ducts/fluid berths form one **feed group**. Within a feed group, tanks drain in **descending stage number** — the soonest-separated stage's tanks empty first (this ordering is what makes asparagus staging work) — proportionally among tanks of the same stage. The editor exposes a per-tank **priority integer** that overrides the default order (higher priority drains first). Duct flow caps (FD-1: 1 t/min cryogenic, 5 t/min storable; depot/coupler transfer rates are owned by 02-propulsion.md §3.13 — PTC-200/300L — and adopted by 05-industry-logistics.md's ops model) are enforced in flight: if connected engines demand more than the ducts can deliver, those engines throttle down to the deliverable flow — surfaced at design time as warning W9.
- **Solid motors** (EN-SRB, EN-KICK) are sealed single-use parts: their propellant is internal part mass, not a tracked canonical resource (02 §4.1: solid propellant is NOT a resource). They cannot be refilled, drained, or crossfed, and cannot be ISRU-printed below the ENGINE-class tier (§3.13).
- **Cryogenic storage**: phase state is a property of the containing tank, not the resource — the canonical resource names are simply Hydrogen, Oxygen, Methane. Any of them stored in a tank flagged *cryogenic* boils off unless the tank has zero-boiloff (ZBO) hardware; boiloff rates and ZBO power draw (≈5 kWe per 60 t LH2 class tank) are owned by 02-propulsion.md / 09-power-thermal.md. Tanks flagged "ZBO" in the catalog include the cryocooler mass but need the power. High-pressure gas bottles (TK-N2, RCS feed gas) are not cryogenic: no boiloff, lower stored density.

### 3.8 Structural integrity (simplified, deterministic)

No finite-element analysis; three cheap checks that run live in the editor and continuously in flight.

**(a) Joint axial-load graph check.** `a` is the vessel's **proper acceleration** — what an accelerometer reads. In free flight `a(t) = Σ F_thrust(t) / m_total(t)`, clamped by the §3.6 limiter; gravity loads no joints in free fall, so there is no "thrust plus gravity" term. When ground-supported (on the pad, landed) `a = g_local`, and the same formula gives each joint's hanging/compression weight. Every joint j carries the inertial load of all parts on the far side of it (toward the nose):

```
L_j(t) = m_above,j(t) · a(t)                            [kN, with m in t and a in m/s²]
PASS iff max over the mission of L_j(t) ≤ L_rated,j     for every joint
```

The editor evaluates L_j(t) across each stage's burn using the §3.7 propellant-drain timeline, plus the on-pad case (a = g_local). Because m_total falls while thrust holds, **the worst flight case is at each stage's burnout** (or at the instant the limiter clamp engages); the check needs only those discrete points, not a full integration.

**Topology**: the load graph is a **spanning tree**. Every cycle — editor-built (closed rings, §4.8; L-berth loops, §3.11) or dock-formed — designates one **canonical joint**, the most recently closed joint in the cycle (recomputed on any graph change), as non-load-bearing: it remains a physical and fluid connection but is attributed zero structural load, and every other joint is checked against the resulting tree. With the tree fixed, a single DFS from the root engine cluster computes every `m_above` — O(parts).

`L_rated` = min of the two parts' axial ratings. Explicit catalog load ratings (`axial` stats in §4.1, port ratings in §3.11/§4.8, spin-arm and tether ratings in §4.8) override; every other part defaults **by material class (§3.13)**: STRUCT, TANK, HAB, and ENGINE stack nodes 1,200 kN; ELEC, SHIELD, MECH, and all deployables (arrays, radiators, dishes, chutes) 300 kN; radial joints 25% of the smaller part's rating. **Engine mounts**: an ENGINE-class part's stack node is rated `max(1,200 kN, 1.25 × rated vacuum thrust)`, and the engine-to-stack joint uses the *engine's* node rating (the thrust-takeout structure ships with the engine), so stack-mounted engines pass at any throttle by construction; radially-mounted engines get no such waiver (the 25% rule applies, and the editor flags them).

Example (Build A — uncrewed, limiter deliberately set to 5 g; full walkthrough in §4.11a): m_above at the interstage = 19.31 t. Unclamped burnout acceleration would be 1,828 kN / 25.25 t = 72.4 m/s² (7.4 g), so the limiter clamps a at 49.03 m/s² → L = 19.31 × 49.03 = 947 kN ≤ 1,200 kN, PASS (21% margin). At the 6 g uncrewed default the same joint would see 19.31 × 58.84 = 1,136 kN — legal, but only a 5% margin; the limiter setting is part of the design, and E6 always evaluates at the selected limiter. On-pad: 19.31 × 9.80665 = 189 kN, PASS.

**(b) Max-Q rule (atmospheric flight).** Dynamic pressure `q = ½ · ρ(h) · v²` (kPa; ρ from the atmosphere model in 03-solar-system.md). Every *exposed* part (not enclosed by an intact fairing or cargo bay) has a rating `q_max`:

| Part state | q_max |
|---|---|
| Streamlined stack part (tank, engine, fairing, capsule) | 50 kPa |
| Radially-attached pod / leg / stowed deployable | 35 kPa |
| Deployed solar wing, radiator, dish | 0.5 kPa |
| Deployed inflatable module | 1 kPa |
| Deployed parachute | per-chute rating (catalog) |

Exceeding `q_max` destroys the part (flight) / raises error E7 (editor pre-flight sim). Anchor: Shuttle held max-Q ≈ 33 kPa; a sample ascent point — 432 m/s at 11 km (US Standard Atmosphere ρ ≈ 0.364 kg/m³) — gives q = ½ × 0.364 × 432² ≈ 34 kPa, comfortably inside the 50 kPa rating; the autopilot flies a throttle bucket targeting q ≤ 35 kPa.

**(c) q·α bending rule.** Aerodynamic bending is abstracted as a stack-level limit on dynamic pressure × angle of attack:

```
q · |α| ≤ 170 kPa·deg      (≈ 3,550 psf·deg, typical LV envelope)
```

Violation breaks the stack at the highest-load joint (the joint with max `m_above · q·α / L_rated`). Strakes/fins (ST-FIN) raise the vessel limit by +40 kPa·deg each (max 2 counted). The ascent guidance in 01-orbital-mechanics.md flies α ≤ 3° below 30 km by default, so a clean design never sees this; it exists to punish hand-flown pitch-overs at max Q.

**(d) Part g-limits.** Every part has `a_max` (default 8 g axial, 3 g lateral; inflatables 4 g axial deployed-stowed, capsule chute deployment per catalog). `a > a_max` → part damage event (§8).

### 3.9 Whipple shielding and MMOD

Micrometeoroid/orbital-debris flux Φ(d > d_crit) [impacts/m²/yr] by region is owned by 03-solar-system.md (placeholder: Φ(>1 mm) ≈ 1×10⁻⁴ /m²/yr at 400 km LEO; lower in deep space, higher near the ring planes). The sim rolls penetration once per vessel per game-day:

```
P_pen = 1 − exp( − Φ · A_exposed · t · (1 − η) )      [t in years; t = 1/365.25 per daily roll]
```

(Φ is an annual flux, so `t` is in **years**; the daily roll uses t = 1/365.25. Longer time-warp steps may batch rolls with the corresponding larger t.)

- `A_exposed` = Σ part hull areas (catalog stat) not covered by shield panels.
- Shield effectiveness η: bare wall η = 0 (stops < 1 mm intrinsically); **WS-B basic Whipple** η = 0.90 (2 mm Al bumper + standoff + wall ≈ 10 kg/m², stops < 5 mm); **WS-S stuffed Whipple** η = 0.98 (bumper + BasaltFiber/Nextel + Kevlar ≈ 22 kg/m², stops < 10 mm; ISS US Lab anchor).
- A penetration event rolls location **weighted by each part's share of the uncovered hull area** (a part contributing 30% of A_exposed takes the hit 30% of the time): pressurized module → leak (hole area 0.5-5 cm², atmosphere loss handled by 08-life-support-crew.md), tank → propellant leak 0.1%/h per cm², radiator/array → capacity loss, avionics → component fault.
- Objects > 10 cm are tracked (LEO only): conjunction events demand an avoidance burn of 0.5-2 m/s (12-gameplay-economy-ui.md event system).
- Shield panels (§4.10) mount radially over modules; one 10 m² panel covers 10 m² of hull area. Mass is the cost; there is no power draw. **This is armor, not a force field** — η < 1 always.

### 3.10 Spin gravity

Artificial gravity comes only from rotation (realism doctrine #4).

```
a_spin = ω² · r        [m/s²],  ω = rpm · 2π/60  [rad/s]
v_rim  = ω · r         [m/s]
gradient over height h: Δa/a = h / r
```

**Comfort rules** (consumed by 08-life-support-crew.md morale/health):
1. ω ≤ 2 rpm: comfortable for all crew immediately.
2. 2 < ω ≤ 4 rpm: crew need 7-day adaptation (reduced productivity during); thereafter comfortable.
3. 4 < ω ≤ 6 rpm: permanent −15% productivity, chronic motion-sickness risk.
4. ω > 6 rpm: forbidden for crewed sections (validation error E9).
5. Gravity gradient: full comfort requires r ≥ 25 m (8% head-to-foot over 2 m); below that, minor penalty.
6. Rim speed: full comfort requires v_rim ≥ 6 m/s (classic Hill & Schnitzer Coriolis criterion, §2); below 6 m/s, minor Coriolis comfort penalty (−5% productivity, stacks with rules 1-5).
7. Health benefit thresholds (08 owns the curve): a ≥ 3.71 m/s² (Mars-equivalent) halts most deconditioning; a ≥ 1.62 m/s² (Lunar) halves it; a < 1.0 m/s² is cosmetic.

**Worked radius/rpm table** (r = a/ω²; v_rim in parens, m/s):

| Spin rate | 1.00 g (9.81 m/s²) | 0.38 g (3.71 m/s²) | 0.17 g (1.62 m/s²) |
|---|---|---|---|
| 1 rpm | 894.6 m (93.7) | 338.3 m (35.4) | 147.7 m (15.5) |
| 2 rpm | 223.6 m (46.8) | 84.6 m (17.7) | 36.9 m (7.7) |
| 3 rpm | 99.4 m (31.2) | 37.6 m (11.8) | 16.4 m (5.2) |
| 4 rpm | 55.9 m (23.4) | 21.1 m (8.9) | 9.2 m (3.9) |
| 6 rpm | 24.8 m (15.6) | 9.4 m (5.9) | 4.1 m (2.6) |

Design consequence baked into the catalog: a 1 g ring needs r ≈ 56 m even at the aggressive 4 rpm — a 112 m diameter megastructure (Act 4+); Mars-g at 3 rpm needs only r ≈ 38 m (Act 3-4); Lunar-g at 4 rpm fits in r ≈ 9 m (a tethered-counterweight bolo or small centrifuge, Act 2-3 — its v_rim of 3.9 m/s deliberately accepts the rule-6 minor Coriolis penalty as the cost of compactness).

**Mechanics:**
- Spin sections attach through the **SP-HUB despun hub** (rotary coupling, anchor: ISS Solar Alpha Rotary Joint ≈ 1.16 t per joint, plus pressurized rotating seal). Docking to a spinning station is only allowed at despun hub ports; EVA is forbidden at ω > 2 rpm.
- **Balance rule**: the rotating subassembly's COM must lie within `0.02 · r` of the hub axis, else wobble (warning W6; in flight: oscillating stress, −50% docking-port ratings, crew comfort penalty). Counterweights: any mass works — water tanks, cargo, regolith ballast (CG-RB).
- **Spin-up propellant** (RCS at radius r_t): `m_prop = I · ω / (r_t · Isp · g0)`, with `I = Σ m_i · r_i²` about the hub. Worked example: 200 t of ring mass at r = 56 m → I = 6.27×10⁸ kg·m²; ω(4 rpm) = 0.419 rad/s; a pair of RCS-HYP quads (=RCS-D400 Draco, one tangential nozzle each, 800 N total) at the rim: torque 44.8 kN·m, spin-up time 5,864 s (1.6 h), propellant 1,595 kg of storables (993 kg NTO + 602 kg MMH at O/F 1.65, Isp 300 s). The SP-HUB's electric counter-torque motor can instead spin up against a counter-rotating section or flywheel for zero propellant (slower: motor torque 10 kN·m).

### 3.11 Pressurized volume, crew capacity, docking topology

- Each habitat part lists pressurized volume `V_press` (m³). Net habitable volume `V_hab = 0.7 · V_press` (fittings/equipment).
- **Crew capacity**: each habitat lists `sleeps` (permanent crew berths; surge berths noted separately). `V_hab_total` sums net habitable volume over **all pressurized modules** — labs, greenhouses, and cupolas count toward volume but contribute 0 sleeps. The binding boarding limits (displayed in §5 as "crew capacity vs. sleeps") are:
  - **Long-duration (> 30 days)**: `crew_max = min( Σ sleeps, floor(V_hab_total / 25 m³) )` per NASA habitable-volume guidance.
  - **Short-duration (≤ 30 days)**: `crew_max = min( Σ sleeps + surge berths, floor(V_hab_total / 10 m³) )`.
  - Exceeding the applicable limit is emergency-only and triggers the 08-life-support-crew.md morale-penalty tiers (heaviest below 10 m³/crew).
- Stations/ships with crew additionally require (validation warnings, not errors): ≥ 1 airlock for EVA capability; ≥ 1 docking port per 4 crew for logistics; a radiation storm shelter beyond LEO (W3; 08 owns dose math). **Shelter rule (implementable W3 check)**: HB-STORM qualifies outright; any other module qualifies iff **every footprint edge cell is adjacent to (or covered by radial shield panels) parts whose summed areal densities reach ≥ 500 kg/m² across that edge**, where a part's areal density = part mass including contents / part hull area. Water counts. Worked example: a full TK-H2O is 2.1 t over hull area 2·(1+2) = 6 m² → 350 kg/m², so a single water-tank layer is *not* enough — two stacked layers (700 kg/m²) qualify.
- **Docking topology**: docking edges join vessel graphs. Ports are androgynous within a size class (IDSS anchor); sizes must match: S (0.8 m passage), B (1.27 m), L (3.0 m structural berth). Closed loops are allowed only through L-class berths (rigidized into one physics body; 13-architecture.md merges bodies on dock).
- **Port load ratings**: burns while docked check the §3.8(a) joint formula across the docking joint with `L_rated`: DK-S 60 kN, DK-B 150 kN, DK-L 800 kN. Example: Build B's NTR stage pushing its 30 t payload through a DK-L at burnout (a = 3.42 m/s²) → 103 kN ≤ 800 kN, PASS. Pushing the same payload through a DK-S would fail (103 > 60) — tugs must pull gently or berth structurally.
- **Docking capture limits** (else bounce-off): closing speed ≤ 0.1 m/s (S/B) or ≤ 0.05 m/s (L), lateral offset ≤ 0.1 m, approach angle ≤ 5°. Magnetic soft-capture (T1 port upgrade) doubles these.

### 3.12 Station keeping

Above each body's atmosphere interface (01 §3.11), drag is **not** integrated: stations and other parked assets pay 01-orbital-mechanics.md's **station-keeping fee** (Table 4.8 — the single canonical curve; 01 owns it), auto-deducted as RCS delta-v by the Stationkeeping Manager program (01 §4.7):

| Location | Fee (m/s per year, 01 Table 4.8) |
|---|---|
| LEO 200-300 km | 25 |
| LEO 300-500 km | piecewise log-linear through (300 km: 25) · (400 km: 20 — ISS anchor) · (500 km: 2) |
| LEO > 500 km, MEO, GEO | 2 (flat background fee) |
| Sun-Earth L1/L2 slot | 4 |
| L4/L5 slots | 0 |
| Low orbits at Moon/asteroids | 5 (mascon / lumpy-gravity stand-in) |

The §2 ISS anchor (5-25 m/s/yr observed, solar-cycle dependent) brackets the canonical 20 m/s/yr at 400 km. There is deliberately **no separate ρ·v² station-keeping integration in this doc** — one owner, one curve; honest drag integration happens only below the interface (ascent, entry, aerobraking), where it uses this doc's per-part drag table:

`A_drag` = Σ exposed-part frontal areas + deployed areas of arrays/radiators/dishes (catalog "deployed area" stats, §4.6/§4.9 — arrays dominate). **Frontal-area default**: `w × 1 m²` per exposed stack part (the 2D grid's unit depth convention), with catalog overrides where listed; Cd = 2.2 for everything (free-molecular, tumbling-average). The per-part Cd·A table is exported to 01-orbital-mechanics.md for its drag integration (§7). Deployed areas are therefore still design-relevant: they size the below-interface drag and the §3.9 MMOD exposure, and 01 may re-anchor Table 4.8 against them in a future pass.

Reboost can come from any docked engine or station thrusters; the resupply burden is the real gameplay cost (05-industry-logistics.md). Fee propellant low → alarm (01 §4.7).

### 3.13 Construction flows

**(1) Earth launch.** Vessels built at a pad must pass: liftoff TWR > 1.0 (02 §3.7 hard floor; W1 warns below 1.2, recommended 1.3-1.5), max-Q/q·α checks, and pad class limits:

| Pad | Max liftoff mass | Max stack height | Availability |
|---|---|---|---|
| PAD-1 | 150 t | 30 m | Act 1 start |
| PAD-2 | 1,000 t | 60 m | Act 1, after upgrade |
| PAD-3 | 5,000 t | 120 m | T1 |

Payloads under a fairing are exempt from aero checks but must fit the fairing's interior cells (ST-FR3: 3 × 8 m usable; ST-FR5: 4 × 12 m). Alternatively the player **buys commercial lift** (no design fun, pure cash): baseline 2049 price $1,500/kg to LEO falling with tier — final pricing owned by 12-gameplay-economy-ui.md.

**(2) Orbital assembly.** Parts or sub-assemblies arrive as cargo (in fairings or CG-BAY); assembly requires a robot arm (DK-ARM) or construction drone (10-vehicles.md) within 50 m. Assembly rate: 1 structural joint per 30 min per arm (time-warped). The T2 **Dry Dock** station module (HB-DOCKYARD) doubles rate and permits assembling parts larger than any fairing (girders, ring segments shipped as rolled stock). Docking-based assembly (modules with ports) needs no arm — fly them together.

**(3) ISRU manufacture.** Machine shops and printers (05-industry-logistics.md) fabricate parts from canonical resources by part *material class* (every catalog entry has one):

| Class | Recipe per kg of part | First printable |
|---|---|---|
| STRUCT | 0.95 IronSteel *or* Aluminum *or* BasaltFiber + 0.05 MachineParts | T2 (surface), T2 (orbital w/ Dry Dock) |
| TANK | 0.80 Aluminum + 0.15 MachineParts + 0.05 Electronics | T2 |
| MECH (legs, arms, drills) | 0.55 IronSteel + 0.25 MachineParts + 0.10 Titanium + 0.10 Electronics | T2 |
| ENGINE | 0.50 IronSteel + 0.20 Titanium + 0.20 MachineParts + 0.10 Electronics | T3 (orbital foundry); until then Earth-only |
| HAB | 0.50 Aluminum + 0.20 Polymers + 0.15 MachineParts + 0.10 Electronics + 0.05 Glass | T3 |
| ELEC (avionics, dishes, PPUs, reactors) | 0.40 Electronics + 0.30 Aluminum + 0.20 Copper + 0.10 MachineParts | T3; reactors Earth-only until T4 |
| SHIELD | 0.60 Aluminum + 0.40 BasaltFiber | T2 |

BasaltFiber STRUCT variants are 25% lighter than IronSteel prints and need no Earth imports on basalt-rich bodies (Moon mare, Mars) — see catalog §4.1. Fabrication hours/tonne and shop throughput are owned by 05-industry-logistics.md.

### 3.14 Cost

Catalog prices are baseline 2049 hardware costs in $M; 12-gameplay-economy-ui.md owns currency, contracts, and price evolution. Rule of thumb encoded in the catalog: commodity structure ≈ $0.05M/t-class; engines $1.5-40M; nuclear hardware $60-300M; crewed modules $40-150M. ISRU-printed parts cost only their resource inputs plus shop time.

### 3.15 Atmospheric entry heating

Entry/aerocapture trajectory integration, corridor planning, **the heating-model constants, and the TPS class table are owned by 01-orbital-mechanics.md** (§3.11 and Table 4.5, which 01 declares binding for this doc's part stats); this section owns what heating does to parts, and the catalog supplies the stats 01 needs (shield diameter, TPS class, ablator mass, protected column — see §7 Provides).

- **Stagnation heat flux** (Sutton-Graves, 01 §3.11): `q̇_conv = k · sqrt(ρ / r_n) · v³` [W/m²], with k per atmosphere (01 owns: k_air = 1.7415×10⁻⁴ for Earth and N2 bodies incl. Titan; k_CO2 = 1.90×10⁻⁴ for Mars/Venus; H2/He bodies ×2.0 [GAME MODEL]), ρ(h) from 03-solar-system.md, v = speed relative to the rotating atmosphere, and `r_n` = effective nose radius = half the footprint width (w/2, m) of the foremost part along the velocity vector. **Radiative augmentation** (01 §3.11): `q̇_total = q̇_conv · f_rad`, with f_rad = 1 for v ≤ 9,000 m/s and f_rad = min(1 + ((v − 9000)/3000)², 8) above. Sanity anchor: LEO entry at 7,800 m/s, ρ = 3×10⁻⁴ kg/m³, r_n = 1.85 m → q̇_conv ≈ 1.0 MW/m², f_rad = 1.
- **Per-part flux rating `q̇_max`** (01 Table 4.5): default for every exposed part — bare aluminum structure — is **0.007 MW/m²** (radiative equilibrium ≈ 600 K; aluminum loses most of its strength well below its 933 K melt). Parts built with the T1 **SteelHotStructure** option (+15% dry mass, reusable) rate **0.10 MW/m²**. There is no generous default: skip heating is survivable only when brief and shallow, and any real entry needs TPS. Reusable TPS classes (tiles 0.30, RCC 0.75 MW/m²) fail when `q̇_total > q̇_max` for > 2 s; **ablative classes are checked against q̇_conv only** (convective — Table 4.5's ablative limits are anchored to flown convective values), while q̇_total drives consumption.
- The catalog's ablative parts (UT-HS3/HS5, AR-SHELL; integral capsule shields on HB-CAP2/CAP4) are **PICA-class** (01 Table 4.5): `q̇_max = 12 MW/m²` checked against q̇_conv, ablator areal density 16 kg/m², capacity 800 MJ/m² (= 16 × 50). Carbon-phenolic (HEEET-class, 30 MW/m²) is the T3 class for Venus deep entry / ice-giant aerocapture parts.
- **Protection geometry** (the mirror image of the E5 plume rule): a shield **protects every part whose footprint lies within the shield's w-cell-wide column behind it** (away from the velocity vector). The vessel must hold the shield within ±10° of the velocity vector; outside that cone, trailing parts are treated as exposed (in-flight warning). Parts inside an intact fairing or cargo bay are protected by it only up to the *fairing's own* bare-structure limit (0.007 MW/m² — fairings are not entry shields).
- **Ablator budget** (01 §3.11): a shield loses ablator mass at `ṁ_abl = q̇_total · A_loaded / E_abl`, with **`E_abl = 50 MJ/kg` [GAME TUNING, 01]** (calibrated so Stardust-class entries consume ≈45% of a PICA shield). `A_loaded` = the shield's frontal projected disc area — the same A used in the Cd·A export — with the stagnation-point q̇ applied uniformly over it (deliberately conservative, per 01). Catalog ablator masses are sized at the PICA-class 16 kg/m² (AR-SHELL carries a 32 kg/m² double layup for Venus-entry heat loads): UT-HS3 0.17 t (10.8 m²), UT-HS5 0.31 t (19.6 m²), AR-SHELL 0.63 t (19.6 m²), HB-CAP2 0.05 t (3.1 m²), HB-CAP4 0.11 t (7.1 m²). A depleted shield exposes bare structure (0.007 MW/m²) — multi-pass aerocapture draws down the same budget as entry; the tracked heat-load integral ∫q̇_total dt is the EDL HUD's ablator-% bar (01 §5).
- Exceeding `q̇_max` destroys the part in flight; the pre-flight entry sim raises **E11**.

## 4. Content Catalog

Columns: ID, Name, Tier, Size (w×h cells = m), Dry mass (t), Cost ($M), Class, Key stats, Real-world anchor. Hull area (for §3.9) defaults to `2·(w+h)` m² per part unless listed; frontal area for drag defaults to `w × 1` m² (§3.12). Material class (§3.13) appears as a Class column in mixed tables and as a one-line note above single-class tables — every entry has exactly one class.

### 4.1 Structure (15)

| ID | Name | Tier | Size | Mass (t) | Cost | Class | Key stats | Anchor |
|---|---|---|---|---|---|---|---|---|
| ST-G1 | Girder segment | T0 | 1×1 | 0.08 | 0.05 | STRUCT | axial 1,200 kN | Al truss, ~80 kg/m |
| ST-G4 | Girder beam | T0 | 1×4 | 0.30 | 0.15 | STRUCT | axial 1,200 kN | — |
| ST-TR8 | Ship spine truss | T0 | 2×8 | 1.4 | 0.8 | STRUCT | axial 2,500 kN, open (engines may fire through) | — |
| ST-KEEL | Station keel truss | T1 | 2×10 | 9.0 | 6 | STRUCT | axial 4,000 kN, utility runs (power/fluid) | ISS S0: 13.97 t / 13.4 m |
| ST-IS3 | Interstage 3 m | T0 | 3×2 | 0.40 | 0.3 | STRUCT | axial 1,200 kN | F9 interstage |
| ST-IS-V | Vented interstage | T1 | 3×2 | 0.55 | 0.5 | STRUCT | hot-staging permitted | Starship hot-stage ring |
| ST-DC2 | Stack decoupler 2 m | T0 | 2×1 | 0.05 | 0.2 | STRUCT | separation imparts 0.3 m/s *relative* velocity along the stack axis, split between the two bodies in inverse proportion to their masses | pyro sep ring |
| ST-DC3 | Stack decoupler 3.7 m | T0 | 3×1 | 0.12 | 0.3 | STRUCT | same sep rule, 0.3 m/s relative along stack axis (inverse-mass split) | — |
| ST-RD | Radial decoupler | T0 | 1×1 | 0.03 | 0.15 | STRUCT | jettisons booster outward: 1 m/s relative, lateral (inverse-mass split) | — |
| ST-FR3 | Fairing 3.7 m | T0 | 3×9 | 0.9 | 1.2 | STRUCT | interior 3×8 m; jettison event | F9-class scaled |
| ST-FR5 | Fairing 5 m | T0 | 4×13 | 2.0 | 2.5 | STRUCT | interior 4×12 m | F9 fairing 1.9 t / 5.2 m |
| ST-FIN | Grid fin / strake | T0 | 1×2 | 0.15 | 0.4 | STRUCT | +40 kPa·deg q·α; aero control torque +30% in atmo | F9 grid fins |
| FD-1 | Crossfeed fuel duct | T1 | 1×2 | 0.08 | 0.3 | STRUCT | enables stage-to-stage / port crossfeed (§3.7); flow 1 t/min cryo, 5 t/min storable (05) | proposed Falcon Heavy crossfeed; standard LV feedline hardware |
| ST-BF-G4 | BasaltFiber beam | T2 | 1×4 | 0.22 | resources | STRUCT | axial 1,100 kN; ISRU-printed | basalt-fiber composites (lunar/Mars studies) |
| ST-BF-KEEL | BasaltFiber keel | T2 | 2×10 | 6.8 | resources | STRUCT | axial 3,600 kN; ISRU-printed | — |

### 4.2 Tanks (15)

Dry-mass fractions: 6% of propellant for methalox and storables, 5% for kerolox (Falcon-class PMF ≈ 0.95), 15% for LH2 (MLI + ZBO cryocooler included), 6% for Xenon COPV (Dawn achieved 5%), 5% for water tanks (ambient-pressure bags), and ~20% for 30 MPa gas bottles (COPV reality — high-pressure gas is heavy to bottle). Bipropellant tanks come pre-loaded at the engine-standard O/F ratio (§3.7 — the ratio itself is an engine property). "Cap" = propellant capacity. All §4.2 entries are material class **TANK** (§3.13).

| ID | Name | Tier | Size | Dry (t) | Cap (t) | Cost | Contents (canonical resources) | Anchor |
|---|---|---|---|---|---|---|---|---|
| TK-ML-S | Methalox tank S | T0 | 2×2 | 0.27 | 4.5 | 0.4 | 3.52 Oxygen + 0.98 Methane (3.6:1) | LOX 1,141 / LCH4 423 kg/m³ |
| TK-ML-M | Methalox tank M | T0 | 2×4 | 0.72 | 12 | 0.9 | 9.39 Oxygen + 2.61 Methane | — |
| TK-ML-L | Methalox tank L | T0 | 3×6 | 2.1 | 35 | 2.2 | 27.4 Oxygen + 7.6 Methane | — |
| TK-ML-XL | Methalox tank XL | T1 | 4×8 | 4.8 | 80 | 4.5 | 62.6 Oxygen + 17.4 Methane | Starship-class tankage |
| TK-KL-M | Kerolox tank M | T0 | 2×4 | 0.70 | 14 | 0.8 | 9.83 Oxygen + 4.17 RP1 (2.36:1; RP1 is Earth-import only, 02 §4.1) | F9 S1 PMF ≈ 0.95 |
| TK-LH2-M | LH2 tank M (ZBO) | T1 | 2×5 | 0.60 | 4.0 | 1.5 | Hydrogen; needs 0.4 kWe ZBO | LH2 70.8 kg/m³; CFM studies |
| TK-LH2-L | LH2 tank L (ZBO) | T2 | 4×9 | 3.0 | 20 | 5 | Hydrogen; needs 1.7 kWe ZBO | DRA 5.0 LH2 tanks |
| TK-LOX-M | LOX tank M | T0 | 2×3 | 0.40 | 8.0 | 0.5 | Oxygen | ISRU product storage |
| TK-CH4-M | Methane tank M | T0 | 2×3 | 0.35 | 7.0 | 0.5 | Methane | — |
| TK-HYP-S | Storable-prop tank S | T0 | 1×2 | 0.10 | 1.6 | 0.4 | 1.00 NTO + 0.60 MMH (1.65:1, 02 §4.1; freeze risk below 262 K — heaters per 02) | Apollo SM tankage |
| TK-XE-S | Xenon COPV S | T0 | 1×1 | 0.025 | 0.42 | 0.6 | Xenon | Dawn: 425 kg Xe / 21.6 kg tank |
| TK-XE-L | Xenon COPV L | T1 | 2×2 | 0.24 | 4.0 | 2.0 | Xenon | — |
| TK-H2O | Water tank | T0 | 1×2 | 0.10 | 2.0 | 0.2 | Water; counts as shelter shielding | ISS water bags |
| TK-N2 | Gas bottle (N2/Ar) | T0 | 1×1 | 0.05 | 0.25 | 0.2 | Nitrogen or Argon @ 30 MPa | COPV |
| TK-DEPOT | Cryo depot tank | T1 | 5×12 | 14.0 | 200 | 25 | any cryo pair; ZBO 6 kWe; 2× DK-L fluid ports | ULA/NASA depot studies |

### 4.3 Engines — chemical & solid (12)

**Stats canonical in 02-propulsion.md §4.2** — the rows below are builder stubs republishing 02's master list verbatim, with `(=02-ID)` aliases (the same pattern §4.6 uses for 09's power parts). This doc adds only grid footprints, attach-node behavior, and baseline $M price tags (12 owns final pricing); thrust, Isp, mass, O/F, gimbal, tier, min-throttle, rated ignitions/burn, ambient-ignition p_max, and reliability all come from 02 (§3.3, §3.6, §3.14) and **may not diverge here**. The full 02 §4.2 catalog is buildable; the rows below are the entries this doc's worked builds and UI presets use. Isp_SL values marked † are 02's synthetic back-pressure slopes for vacuum engines — model data, not a sea-level operating claim.

Size = grid footprint w×h; the §3.6 plume rule's `w_engine` is the part's w, and the nozzle face exposes no attach node (§3.1). O/F = oxidizer:fuel mass ratio the engine draws (§3.7), in canonical resources. All §4.3-4.5 entries are material class **ENGINE** (§3.13); engine stack nodes are rated `max(1,200 kN, 1.25 × rated vacuum thrust)` (§3.8a).

| ID (=02 ID) | Anchor | Tier | Size | Mass (t) | Thrust SL/vac (kN) | Isp SL/vac (s) | Prop (O/F) | Gimbal | Cost |
|---|---|---|---|---|---|---|---|---|---|
| EN-K1 (=K-845 "Mule") | Merlin 1D | T0 | 1×2 | 0.47 | 845 / 914 | 282 / 311 | Oxygen+RP1 (2.36) | ±5° | 1.5 |
| EN-K1V (=KV-981 "Mule-V") | Merlin Vacuum | T0 | 1×3 | 0.63 | — / 981 | 90† / 348 | Oxygen+RP1 (2.36) | ±3° | 2.0 |
| EN-H1 (=H-102 "Crane") | RL10C-1 | T0 | 2×4 | 0.19 | — / 101.8 | 110† / 449.7 | Oxygen+Hydrogen (6.0) | ±4° | 12 |
| EN-HYP (=OMS-27 "Vireo") | Shuttle OMS AJ10-190 | T0 | 1×1 | 0.12 | — / 26.7 | 100† / 316 | NTO+MMH (1.65) | ±6° | 2.5 |
| EN-HYP-L (=SPS-91 "Pelican") | Apollo SPS AJ10-137 | T0 | 1×2 | 0.29 | — / 91 | 60† / 314 | NTO+MMH (1.65) | ±6° | 4 |
| EN-SRB (=SRM-49 "Aurochs") | GEM 63 strap-on | T0 | 2×12 | 5.2 + 44.1 prop | 1,265 avg (1,663 max) | 245 / 275 | solid (sealed, §3.7); 94 s burn | fixed | 6 |
| EN-KICK (=SRM-2 "Kestrel") | Star 48B | T0 | 1×2 | 0.126 + 2.011 prop | — / 66 mean | 250 / 286 | solid (sealed, §3.7); 87 s burn | spin-stab | 1.5 |
| EN-LND (=LND-71 "Ibex") | SuperDraco lander | T1 | 1×1 | 0.12 | 71 / 73 | 235 / 243 | NTO+MMH (1.65) | fixed (cluster diff-throttle) | 2 |
| EN-H2 (=H-2280 "Shire") | RS-25 | T1 | 2×4 | 3.18 | 1,860 / 2,279 | 366 / 452 | Oxygen+Hydrogen (6.0) | ±10.5° | 40 |
| EN-M2 (=M-2256 "Drayhorse") | Raptor 2 | T1 | 2×3 | 1.63 | 2,256 / 2,394 | 327 / 347 | Oxygen+Methane (3.6) | ±15° | 2.5 |
| EN-M2V (=MV-2530 "Drayhorse-V") | Raptor Vacuum | T1 | 2×4 | 2.10 | — / 2,530 | 100† / 380 | Oxygen+Methane (3.6) | ±3° | 3.0 |
| EN-ML (=ML-24 "Gopher") | Project Morpheus lander | T2 | 1×1 | 0.08 | 22 / 24 | 295 / 320 | Oxygen+Methane (3.6) | ±5° | 1.5 |

The Raptor-class pair (EN-M2/M2V) is **T1, gated by 11's era node PR-02 "Reusable Methalox Heavy Lift"** — Act 1 starts on the T0 kerolox/hydrolox/storable/solid line above (02 §6); the $/kg collapse when PR-02 lands is the designed Act 1 economic arc (11 §4.12, 12 E-2). Any engine this doc needs that 02's master list lacks must be **added to 02's catalog by 02 first, then stubbed here** (precedent: the bimodal NTR-111B, §4.4); see §9 Q1 — the registration requests (small "Bantam"-class methalox pair, argon AEPS derivative, plus 10's pump-fed methalox lander row) were **ACCEPTED per DECISIONS A8**; 02 is publishing the stats, and the new rows get builder stubs here when they land.

### 4.4 Engines — nuclear thermal (3)

**Stats canonical in 02 §4.3.** Class **ENGINE** (§3.13); monopropellant Hydrogen baseline (no O/F; alternate propellants — Water, Ammonia, CO2 — per 02 §3.10). Masses below include the +1.5 t shadow-shield option where noted. Operating rules from 02 §3.10, binding here: **no NTR operation below 60 km altitude on Earth** (hard regulatory rule — launch NTRs cold, first criticality only in orbit; firing below 60 km over Earth is a mission-ending regulatory event, 02 §8.10 / 12 event system; other bodies unrestricted, p_max 30 kPa permits Mars-ambient ignition but not Titan surface); 45-min restart lockout; crew outside the shadow cone during operation receive a promptly lethal dose (02 §3.10, 08).

| ID (=02 ID) | Anchor | Tier | Size | Mass (t) | Thrust vac (kN) | Isp (s) | Prop | Notes |
|---|---|---|---|---|---|---|---|---|
| EN-NTR-S (=NTR-73 "Prometheus") | SNRE (Schnitzler/Borowski), DRACO-class | T2 | 2×5 | 2.4 (+1.5 shadow shield option; Charon flies 3.9) | 73 | 900 | Hydrogen | T/W ≈ 3.1 bare; LANTR option (02): +0.25 t, Isp 645 s, thrust ×2.75 (LOX O/F 3.0) |
| EN-NTR-L (=NTR-246 "Prometheus-H") | NERVA XE' (modernized) | T2 | 3×6 | 12.5 | 247 | 850 | Hydrogen | T/W ≈ 2.0 (12.5 t game mass with modern composites; historic XE' 18.1 t incl. test hardware); heavy tug core, Act 3-4 |
| EN-NTR-B (=NTR-111B "Prometheus-B") | Borowski BNTR studies, DRA 5.0 25-klbf class | T3 | 2×5 | 3.1 (+1.5 shadow shield option = 4.6 shielded) | 111 | 900 | Hydrogen | bimodal: +25 kWe idle export (09 ledger), no export while thrusting; mode rules 02 §3.10; no LANTR option |

### 4.5 Engines — electric & RCS (11)

**Stats canonical in 02 §4.4 (EP strings: thruster + PPU + feed, ±10° gimbal mount included) and 02 §4.7 (RCS blocks).** EP thrust scales with available power (§3.4); catalog η republished in §3.4. Class **ENGINE** (§3.13). EP propellants are single-resource (no O/F). RCS quads are 1×1 **surface-mount** parts: they attach radially to any hull edge cell and are exempt from the E5 plume rule (attitude blocks, per-nozzle thrust ≤ 2 kN); RCS wear is total-impulse-based, checked once per maneuver (02 §3.14).

| ID (=02 ID) | Anchor | Tier | Size | Mass (t) | Thrust | Isp (s) | Power | Prop | Cost |
|---|---|---|---|---|---|---|---|---|---|
| EN-ION-2 (=ION-2 "Mayfly") | NSTAR (DS1, Dawn) | T0 | 1×1 | 0.030 | 92 mN | 3,120 | 2.3 kWe | Xenon | 2 |
| EN-HALL-1 (=HALL-1 "Wren") | SPT-100 (flown since 1994) | T0 | 1×1 | 0.012 | 83 mN | 1,600 | 1.35 kWe | Xenon | 1 |
| EN-ION-N (=ION-7 "Dragonfly") | NEXT (flew on DART) | T1 | 1×1 | 0.058 | 236 mN | 4,190 | 6.9 kWe | Xenon | 5 |
| EN-HALL (=HALL-12 "Harrier") | AEPS/HERMeS (Gateway PPE) | T1 | 1×1 | 0.115 | 590 mN | 2,800 | 12.5 kWe | Xenon | 3 |
| EN-HALL-X (=HALL-100 "Condor") | X3 nested Hall (UM/AFRL lab, 2017) | T3 | 2×2 | 0.46 | 5.4 N | 2,000 | 100 kWe | Xenon or Argon (η −0.06) | 12 |
| EN-MPD (=MPD-200 "Albatross") | NASA Lewis / MAI applied-field MPD | T3 | 2×2 | 0.90 | 4.6 N | 4,000 | 200 kWe | Argon (Ammonia η −0.05; Hydrogen η −0.05, Isp +25%) | 15 |
| EN-VAS (=VAS-200 "Petrel") | VASIMR VX-200 (lab) | T3 | 2×3 | 0.65 | 5.7 N | 4,900 (variable 3,000-12,000, 02 §3.9) | 200 kWe | Argon | 20 |
| EN-FT (=DFD-5 "Helios") [SPECULATIVE] | Princeton Direct Fusion Drive concept | T4 | 3×8 | 10 | 20 N | 10,500 | self-powered (5 MW fusion; exports 1 MWe bus power, 09) | He3 + Hydrogen [SPECULATIVE] | 2,000 |
| RCS-N2 (=RCS-N10) | industry cold-gas | T0 | 1×1 surface-mount | 0.008 | 4×10 N | 70 | — | Nitrogen (COPV feed, TK-N2) | 0.1 |
| RCS-HYP (=RCS-D400) | SpaceX Draco | T0 | 1×1 surface-mount | 0.022 | 4×400 N | 300 | — | NTO+MMH (1.65); ullage-capable | 0.4 |
| RCS-CH4 (=RCS-M2K) | Starship hot-gas methalox | T1 | 1×1 surface-mount | 0.060 | 4×2,000 N | 270 | — | gaseous Oxygen+Methane from main tanks (no separate RCS propellant) | 0.6 |

Note: 02's T4 catalog also lists FFR-43 (fission-fragment probe drive) and the PULSE-D Daedalus megaproject; FFR-43 is probe-scale (10-vehicles.md territory) and PULSE-D is an economy-chain megaproject (12), not a buildable ship part — neither gets a builder stub here.

### 4.6 Power & thermal (builder entries; performance canonical in 09-power-thermal.md) (10)

All §4.6 entries are material class **ELEC** (§3.13). "Depl. area" = deployed face area in m², feeding the §3.12 drag model (— = not a deployable; negligible beyond the frontal-area default).

| ID | Name | Tier | Size | Mass (t) | Output | Depl. area (m²) | Cost | Anchor |
|---|---|---|---|---|---|---|---|---|
| PW-SA-R (=SOL-RW) | Rigid solar wing | T0 | 1×4 stowed | 0.16 | 5 kWe @1 AU BOL (≈31 W/kg, η 0.295 — 09 §4) | 12.5 | 0.8 | ISS legacy wings |
| PW-SA-RO (=SOL-RO) | Roll-out array | T0 | 1×3 stowed | 0.25 | 20 kWe @1 AU (80 W/kg, η 0.32 — 09 §4) | 46 | 2 | ROSA / iROSA |
| PW-BAT (=STO-LI) | Battery bank | T0 | 1×1 | 0.20 | 30 kWh (150 Wh/kg Li-ion canon, 09 §3.4/§4; heater 50 W per 0.1 t below 273 K) | — | 0.5 | Li-ion pack, 2040s |
| PW-FC | Fuel cell | T0 | 1×1 | 0.12 | 7 kWe cont. (Hydrogen+Oxygen→Water) | — | 1 | Shuttle PC17C |
| PW-RTG | RTG | T0 | 1×1 | 0.045 | 0.11 kWe (Pu238) | — | 15 | MMRTG |
| PW-KP1 | Fission unit 1 kWe | T2 | 1×2 | 0.40 | 1 kWe (Uranium) | — | 20 | Kilopower/KRUSTY (ground-tested 2018, never flown → T2 per 09 §4.3; unlocked by 11's PW-04) |
| PW-KP10 | Fission unit 10 kWe | T2 | 2×3 | 1.5 | 10 kWe | — | 60 | Kilopower 10 kWe design |
| PW-FSP | Surface fission 100 kWe | T2 | 3×4 | 9.0 | 100 kWe | — | 150 | NASA Fission Surface Power studies |
| PW-NEP (=NUK-NEP) | NEP reactor 2 MWe | T3 | 5×8 | 35 | 2,000 kWe (17.5 kg/kWe incl. conversion, instrument shield and integral 800 K radiators — 09 flags this honestly as a 10× extrapolation beyond JIMO/Prometheus's 200 kWe, within the 5-25 kg/kWe MW-class study range) | 144 (integral radiator wings) | 600 | JIMO/Prometheus-class, game-extrapolated (09 §4) |
| TH-RAD | Deployable radiator | T0 | 1×3 stowed | 1.2 | rejects 50 kWt @ 500 K (loop-capped; 76 radiative — 09 H-9 convention) | 12 (two-sided panel) | 1.5 | ISS HRS-derived; 09 owns curve |

### 4.7 Habitat modules (13)

All §4.7 entries are material class **HAB** (§3.13). "Crew sleeps" = permanent berths; §3.11 defines how sleeps and volume jointly gate boarding.

| ID | Name | Tier | Size | Mass (t) | V_press (m³) | Crew sleeps | Cost | Anchor |
|---|---|---|---|---|---|---|---|---|
| HB-CAP2 | 2-crew capsule | T0 | 2×3 | 4.2 | 9 | 2 (≤7 d) | 25 | Gemini (3.85 t) + modern materials; integral PICA-class heat shield (q̇_max 12 MW/m² vs q̇_conv, 0.05 t ablator over 3.1 m², §3.15 / 01 Table 4.5) & chutes (deploy q ≤ 20 kPa, a ≤ 7 g; UT-CHUTE scaling rule, §4.9) |
| HB-CAP4 | 4-crew capsule | T0 | 3×4 | 9.5 | 20 | 4 (≤30 d) | 60 | Crew Dragon class (PICA-X heritage); integral PICA-class heat shield (q̇_max 12 MW/m² vs q̇_conv, 0.11 t ablator over 7.1 m², §3.15 / 01 Table 4.5) & chutes (deploy q ≤ 20 kPa, a ≤ 7 g; UT-CHUTE scaling rule, §4.9) |
| HB-RIG-S | Rigid module S | T0 | 3×5 | 9.0 | 60 | 2 | 70 | ISS-module density ≈0.14 t/m³ |
| HB-RIG-L | Rigid lab/hab module | T0 | 4×9 | 14.5 | 106 | 4 | 120 | ISS Destiny |
| HB-INF-S | Inflatable module S | T0 | 2×2 (3×4 deployed) | 1.4 | 16 | 0 (storage) | 8 | BEAM (flown) |
| HB-INF-M | Inflatable hab M | T1 | 3×5 (8×11 deployed) | 13.2 | 340 | 6 (+6 short-duration surge, §3.11) | 80 | TransHab (6-crew design; shell + basic outfitting) |
| HB-INF-L | Inflatable hab L (outfitted) | T1 | 4×6 (8×11 deployed) | 20.0 | 330 | 6 (+6 short-duration surge, §3.11) | 150 | B330 (nominal 6 crew; incl. integral ECLSS; 08) |
| HB-CUP | Cupola | T0 | 2×1 | 1.9 | 3 | 0; +morale | 15 | ISS Cupola 1.8 t |
| HB-AIR | Airlock | T0 | 2×3 | 6.1 | 34 | 0; 2-person EVA | 30 | ISS Quest |
| HB-LAB | Science lab | T1 | 4×9 | 12.0 | 100 | 0; research slots (11) | 100 | Destiny-derived |
| HB-GRN-S | Greenhouse module S | T2 | 3×5 (inflatable) | 6.0 | 80 | 0; 50 m² grow area — 25-50% food closure for ~4 crew (08; unlocked by 11 LS-04, feeds 12's Act 3 food-harvest milestones) | 40 | EDEN ISS Antarctic greenhouse, scaled (~270 kg vegetables/yr from 12.5 m²) |
| HB-GRN | Greenhouse module | T3 | 4×9 (inflatable) | 16.0 | 280 | 0; 200 m² grow area — full-diet closure tier (08; 11 LS-07 era) | 90 | bioregenerative LSS studies (BIOS-3, NASA) |
| HB-STORM | Storm shelter core | T1 | 2×2 | 3.0 (+5 Water fill) | 8 | refuge 8 crew | 12 | water-wall shielding concepts (08 owns dose) |

### 4.8 Spin-gravity, docking & assembly (12)

| ID | Name | Tier | Size | Mass (t) | Cost | Class | Key stats | Anchor |
|---|---|---|---|---|---|---|---|---|
| SP-HUB | Despun hub w/ rotary seal | T2 | 3×3 | 8.0 | 90 | MECH | 2× DK-B despun ports; motor torque 10 kN·m; pressurized rotating joint | ISS SARJ (1.16 t, unpressurized) + seal engineering margin |
| SP-ARM | Spin truss arm 10 m | T2 | 1×10 | 1.2 | 2 | STRUCT | axial (radial-load) 800 kN → max ring mass per arm = 800/a_spin kN/(m/s²) | — |
| SP-TETHER | Bolo tether 200 m | T2 | 1×2 reel | 0.8 | 3 | MECH | 2-mass bolo; rated 300 kN | tethered artificial-g studies (Gemini XI demo) |
| SP-HAB | Ring hab pod | T2 | 3×4 | 8.0 | 60 | HAB | V_press 60 m³; pre-curved for r ≥ 20 m | — |
| SP-RING | Ring segment 30° | T3 | 29×4 (chord approximation of a 30° arc at r = 56 m) | 22.0 | 120 | HAB | V_press 180 m³ at r = 56 m; **ring group rule**: ends attach only to other SP-RING ends or SP-ARM tips; exactly 12 segments close a 1 g ring, and closure forms a cycle resolved by the §3.8(a) canonical-joint rule; schematic ring-inset rendering per Q6 | Stanford-torus-style construction, scaled down |
| DK-S | Docking port S | T0 | 1×1 | 0.34 | 2 | MECH | 0.8 m passage; axial 60 kN | IDSS/NDS |
| DK-B | Berthing port B | T0 | 2×1 | 0.25 | 2 | MECH | 1.27 m passage; 150 kN; needs arm to mate | ISS CBM |
| DK-L | Structural berth L | T1 | 3×1 | 1.2 | 5 | MECH | 3 m; 800 kN; fluid transfer built in | depot-study couplers |
| DK-GR | Grapple fixture | T0 | 1×1 | 0.05 | 0.3 | MECH | arm grab point | ISS FRGF |
| DK-ARM | Robot arm | T1 | 1×2 stowed | 1.8 | 40 | MECH | 17 m reach; moves ≤116 t; enables assembly §3.13 | Canadarm2 |
| HB-DOCKYARD | Dry Dock module | T2 | 6×12 | 24.0 | 200 | STRUCT | open assembly frame fits sub-assemblies up to 6×12 m; doubles §3.13 assembly rate for arms working in-frame; assembles parts beyond any fairing limit; pressurized control cab 20 m³ (0 sleeps); 2 kWe draw; 1× DK-B port | NASA OSAM in-space assembly studies; ISS truss-assembly heritage |
| UT-CMG | Control moment gyro | T0 | 1×1 | 0.3 | 8 | MECH | momentum 4,760 N·m·s; torque 0.26 kN·m | ISS CMG |

### 4.9 Cargo, utility, entry & landing (16)

| ID | Name | Tier | Size | Mass (t) | Cost | Class | Key stats | Anchor |
|---|---|---|---|---|---|---|---|---|
| CG-BAY | Unpressurized cargo bay | T0 | 2×3 | 0.6 | 0.8 | STRUCT | holds 8 t / 12 stowed-cell-equivalents of parts as an **off-grid manifest** (racked 2 cell-equivalents per bay cell; no grid placement): contents contribute mass at the bay centroid (§3.2), count against the 600-part cap, are aero/MMOD-protected while the bay is intact, and cannot be DEPLOYed while stowed (§8.15) | — |
| CG-HOP | Ore hopper | T1 | 3×3 | 1.5 | 1 | STRUCT | 12 t bulk (Regolith etc.) | — |
| CG-CON | Container berth | T1 | 2×1 | 0.15 | 0.3 | STRUCT | mounts 1 standard container (defined in 05) | — |
| CG-RB | Regolith ballast box | T2 | 2×2 | 0.4 (+10 fill) | 0.2 | STRUCT | spin counterweight / rad shielding | — |
| UT-AV | Avionics core | T0 | 1×1 | 0.15 | 5 | ELEC | command source; low-gain comms; 0.3 kWe draw | — |
| UT-AVS | Probe core S | T0 | 1×1 | 0.04 | 2 | ELEC | command source; 0.1 kWe | cubesat-derived |
| UT-DISH-S | High-gain dish 0.5 m | T0 | 1×1 | 0.02 | 1 | ELEC | link budget per 12/13 comms model | — |
| UT-DISH-M | High-gain dish 3 m | T0 | 1×2 stowed | 0.09 | 3 | ELEC | deployed area 7 m² (§3.12) | MRO 3 m HGA |
| UT-DISH-L | Deployable dish 10 m | T2 | 2×2 stowed | 0.4 | 10 | ELEC | outer-system relay; deployed area 80 m² (§3.12) | large deployable mesh antennas |
| UT-HS3 | Heat shield 3.7 m | T0 | 3×1 | 0.5 | 2 | SHIELD | ablative PICA-class (01 Table 4.5): q̇_max 12 MW/m² vs q̇_conv, ablator 0.17 t (16 kg/m² over the 10.8 m² loaded disc; ≈46 kg/m² total incl. carrier), protects the 3-wide column behind it (§3.15); bottom face = TPS, no attach node | PICA-X |
| UT-HS5 | Heat shield 5 m | T1 | 4×1 | 0.9 | 4 | SHIELD | as UT-HS3 at 4-wide / 5 m: q̇_max 12 MW/m² vs q̇_conv, ablator 0.31 t (16 kg/m² over 19.6 m²), protects the 4-wide column (§3.15) | — |
| UT-CHUTE | Parachute cluster | T0 | 1×1 | 0.24 | 0.5 | MECH | recovers 6 t at ≤ 8 m/s (Earth SL); scaling `v_td = 8 m/s · sqrt(m / 6 t) · sqrt(ρ_Earth,SL / ρ_local)`; deploy limits q ≤ 20 kPa, a ≤ 7 g (exceed = chute destroyed); mass rule ≈ 4% of recovered | Apollo ELS ≈ 250 kg / 5.8 t |
| ST-LL | Landing leg | T0 | 1×2 | 0.15 | 0.4 | MECH | 8 t per leg @ ≤3 m/s touchdown | — |
| ST-LLH | Heavy landing leg | T1 | 1×3 | 0.6 | 1 | MECH | 40 t per leg @ ≤3 m/s | F9 leg class |
| AR-SHELL | Entry aeroshell 5 m | T3 | 4×2 | 2.5 | 8 | SHIELD | PICA-class TPS + backshell (01 Table 4.5): q̇_max 12 MW/m² vs q̇_conv, ablator 0.63 t (32 kg/m² double layup over 19.6 m² — sized for Venus 10-11 km/s entry heat loads), protects the 4-wide column behind it (§3.15); jettisonable (SEPARATE event); no bottom attach node | HAVOC entry vehicle / MSL aeroshell class |
| AR-CHUTE | Supersonic extraction chute | T3 | 1×1 | 0.6 | 1.5 | MECH | deploys ≤ Mach 2.2 and q ≤ 4 kPa; extracts ≤ 10 t payload from an aeroshell; single-use | MSL/HAVOC disk-gap-band chute |

Aerostat envelope/gondola/inflation hardware (AR-ENV envelope kit, AR-GON gondola, AR-INF inflation hardware) **migrated to 07-bases-habitats.md's catalog per DECISIONS A10** (07 owns habitats) — this doc keeps the entry hardware (AR-SHELL, AR-CHUTE) and this pointer; Build D (§4.11d) references 07's entries.

The AR-* aerostat deployment set (entry hardware above; envelope/gondola/inflation in 07's catalog) is **T3**, matching 07 §4.3.3 (Venus aerostat = Act 4, T3; HAB-11/12 at T3) and 11's gating of crewed aerostats/Venus platforms (HB-05, VH-09 behind DSC-08).

Static tip-over rule for landed vessels: stable iff `tan(θ_slope) < (b/2) / h_COM` with b = leg-base width, h_COM = COM height. Example: legs spanning 7 m, COM at 4 m → stable to 41° slope.

### 4.10 Whipple shielding (3)

All §4.10 entries are material class **SHIELD** (§3.13).

| ID | Name | Tier | Size | Mass (t) | Cost | Stats | Anchor |
|---|---|---|---|---|---|---|---|
| WS-B | Whipple panel 10 m² | T0 | 1×2 | 0.10 | 0.3 | η = 0.90; 10 kg/m² (2 mm Al bumper + standoff + wall) | ISS basic Whipple |
| WS-S | Stuffed Whipple 10 m² | T1 | 1×2 | 0.22 | 0.8 | η = 0.98; 22 kg/m² (adds ceramic fabric + Kevlar) | ISS US Lab stuffed shields (Nextel/Kevlar) |
| WS-BF | BasaltFiber stuffed panel | T2 | 1×2 | 0.22 | resources | η = 0.97; ISRU print (SHIELD class) | basalt fiber as Nextel analog |

### 4.11 Worked example builds

All delta-v via `dv = Isp · g0 · ln(m0/m1)`, g0 = 9.80665. Arithmetic shown; all figures machine-checked.

#### (a) "Anvil-1" — T0 two-stage kerolox/hydrolox launcher (2 t to LEO, uncrewed)

Built entirely from integer catalog parts and **T0 engines only** (the Raptor-class methalox line is T1 behind PR-02 — §4.3); the design's acceleration limiter is set to **5 g** (player-selected, below the 6 g uncrewed default — see the joint check below for why).

| Item | Mass (t) |
|---|---|
| Payload | 2.00 |
| **Stage 2**: 1× TK-LH2-M part-filled 2.0 Hydrogen (dry 0.60) + 2× TK-LOX-M, 12.0 Oxygen (dry 0.80) — 14.0 t hydrolox at O/F 6.0 | 15.40 |
| EN-H1 engine (=H-102) | 0.19 |
| UT-AV + structure | 0.30 |
| **Stage 2 total (m0₂, incl. payload)** | **17.89** |
| ST-FR3 fairing (jettisoned with stage 1) | 0.90 |
| ST-IS3 interstage + ST-DC3 decoupler (0.40 + 0.12) | 0.52 |
| **Stage 1**: 5× TK-KL-M (70 t prop = 49.2 Oxygen + 20.8 RP1; dry 3.50) | 73.50 |
| 2× EN-K1 | 0.94 |
| Structure, ST-FIN ×2, avionics | 1.50 |
| **Liftoff mass (m0₁)** | **95.25** |

- Stage 2: m0 = 17.89 t, m1 = 3.89 t → dv = 449.7 × 9.80665 × ln(17.89/3.89) = 4,410 × 1.5258 = **6,729 m/s**. TWR(ignition, Earth) = 101.8/(17.89×9.80665) = 0.58. Burn 607 s (ṁ = 23.08 kg/s; well inside H-102's 2,000 s rating). The TK-LH2-M's 0.4 kWe ZBO draw rides the avionics bus battery for the short coast.
- Stage 1: m0 = 95.25 t, m1 = 25.25 t. Trajectory-avg Isp 295 s (bounds: 3,672 m/s at SL 282 s; 4,049 m/s at vac 311 s) → dv = 295 × 9.80665 × ln(95.25/25.25) = 2,893 × 1.3277 = **3,841 m/s**. Liftoff TWR = 1,690/(95.25×9.80665) = **1.81** (hard floor 1.0, recommended 1.3-1.5 — 02 §3.7; the surplus buys single-engine-out controllability, §3.3, at the price of an earlier max-Q throttle bucket). Burn 117 s (ṁ = 2 × 299.7 = 599.4 kg/s from the vacuum pair — §3.4).
- **Total ideal dv = 10,570 m/s ≥ 9,400 m/s LEO requirement** (01-orbital-mechanics.md) → ~1,170 m/s designer margin (hydrolox upper stages are generous; the price is the $12M engine and cryo-handling logistics). Payload fraction 2.1% (typical for a small launcher).
- Joint check (§3.8a, evaluated at the selected 5 g limiter): m_above the interstage = 17.89 + 0.90 + 0.52 = 19.31 t. Unclamped stage-1 burnout acceleration would be 1,828/25.25 = 72.4 m/s² (7.4 g), so the limiter clamps a at 49.03 m/s² → L = 19.31 × 49.03 = **947 kN ≤ 1,200 kN PASS** (21% margin). At the 6 g uncrewed default the joint would see 1,136 kN — legal, but only a 5% margin; the design selects 5 g because the clamp engages only in the final seconds (negligible gravity-loss cost) and buys real structural margin. E6 always evaluates at the selected limiter. On-pad: 19.31 × 9.80665 = 189 kN PASS. Engine mounts: EN-K1 stack node rated max(1,200, 1.25×914) = 1,200 kN ≥ per-engine peak thrust 914 kN — pass by construction (§3.8a). Stage-2 burnout is 101.8/3.89 = 26.2 m/s² (2.7 g), under the limiter, all stage-2 joints trivially pass. Hardware cost ≈ $30M + propellant.

#### (b) "Charon" — T2 NTR Mars transfer vehicle (orbital-assembled)

| Item | Mass (t) |
|---|---|
| 3× EN-NTR-S (=NTR-73: 73 kN, Isp 900 s; incl. 1.5 t shadow shields → 3.9 t each) | 11.7 |
| 3× TK-LH2-L (60 t Hydrogen; tanks 15% = 9.0) | 69.0 |
| ST-KEEL truss | 9.0 |
| PW-KP10 (ZBO power 5 kWe + ship bus) | 1.5 |
| TH-RAD | 1.2 |
| UT-AV, dishes | 0.5 |
| DK-L berth (payload) | 1.2 |
| **Payload**: HB-INF-M hab 13.2 + consumables 6.0 (08) + HB-CAP2 return capsule 4.2 + storm-shelter Water 5.0 + science 1.6 | 30.0 |
| **m0** | **124.1** |

- m1 = 124.1 − 60 = 64.1 t → **dv = 900 × 9.80665 × ln(124.1/64.1) = 8,826 × 0.6606 = 5,830 m/s**.
- TWR in LEO = 219/(124.1×9.80665) = 0.18 → TMI split into 3 periapsis burns (§3.5; TMI burn time ≈ 27.9 min at ṁ = 24.8 kg/s; the full 60 t load would take 40.3 min).
- Mission ledger (01-orbital-mechanics.md Table 4.2): TMI (R1) 3,590 m/s burns 41.5 t H2 → 82.6 t; Mars capture to 1-sol elliptic 1,100 m/s burns 9.7 t → 72.9 t; **reserve 8.8 t ≈ 1,136 m/s** for trans-Earth injection after a Phobos/ISRU LH2 top-up, or as partial cover toward an outbound abort.
- Berth load at burnout: a = 219/64.1 = 3.42 m/s²; 30 t payload → 103 kN ≤ 800 kN (DK-L) PASS.

#### (c) "Packmule" — T1 Hall-thruster cargo tug (LEO → low lunar orbit)

| Item | Mass (t) |
|---|---|
| 4× EN-HALL (=HALL-12 AEPS strings: 50 kWe rated, 2.36 N total) | 0.46 |
| 3× PW-SA-RO roll-out arrays: 60 kWe @1 AU (20% power margin; deployed area 138 m²) | 0.75 |
| 1× TK-XE-L (4.0 t Xenon; 0.24 dry) | 4.24 |
| Structure 0.45, UT-AV 0.15, DK-B 0.25, radiator stub 0.15 (09 small class) | 1.00 |
| **Payload (container rack)** | 8.00 |
| **m0** | **14.45** |

- m1 = 10.45 t → **dv = 2,800 × 9.80665 × ln(14.45/10.45) = 27,459 × 0.32409 = 8,900 m/s** — covers the ≈8,000 m/s low-thrust LEO→LLO spiral (01-orbital-mechanics.md) with ~900 m/s margin.
- Acceleration 1.63×10⁻⁴ m/s²; ṁ = 2.36/(2,800×9.80665) = 8.59×10⁻⁵ kg/s; thrust-on time 4.65×10⁷ s ≈ **540 days** (this is the honest physics of 50 kWe; time warp and uncrewed patience are the gameplay answer — crewed transfers use chemical/NTR).
- At Mars distance (1.52 AU) arrays deliver 60/1.52² = 26.0 kWe → thrust drops to 26.0/50 = **~52% of rated** (the §3.4 rule divides available power by *rated thruster power*, here 50 kWe — not by array output at 1 AU); the editor's transfer planner shows power-limited thrust along the trajectory.

#### (d) "Cyclops" — Venus aerostat deployment ship (T3, HAVOC-class robotic)

Deploys a robotic aerostat at 55 km in Venus's atmosphere (07-bases-habitats.md operates it; the AR-* deployment set is T3, §4.9, matching 07/11's Act 4 gating).

| Item | Mass (t) |
|---|---|
| **Entry assembly (payload: AR-SHELL/AR-CHUTE per §4.9; AR-ENV/AR-GON/AR-INF per 07's catalog — DECISIONS A10, stats unchanged)**: AR-SHELL 2.5; AR-CHUTE 0.6; AR-ENV 1.3; AR-GON 4.6; TK-LH2-M 0.60 dry, part-filled with 0.5 Hydrogen lifting gas; AR-INF 0.7; mass margin 1.2 | 12.00 |
| Carrier bus (UT-AV, PW-SA-RO, UT-DISH-M, RCS-HYP + NTO/MMH) | 1.50 |
| **Departure stage**: EN-H1 (=H-102 RL10C-1, O/F 6.0) 0.19; propellant 28.0 = 24.0 Oxygen in 3× TK-LOX-M + 4.0 Hydrogen in 1× TK-LH2-M (tank dry 3×0.40 + 0.60 = 1.80, per §4.2 fractions); structure 0.80; avionics 0.20; trim ballast 0.11 | 31.10 |
| **m0 (assembled in LEO)** | **44.60** |

- m1 = 16.60 t → **dv = 449.7 × 9.80665 × ln(44.60/16.60) = 4,410 × 0.9883 = 4,358 m/s**; trans-Venus injection from LEO needs 3,480 m/s (01 Table 4.2, V1) → ~878 m/s for midcourse + carrier divert to relay flyby. TWR 0.23 (two perigee burns, 1,213 s total at ṁ = 23.1 kg/s). The hydrolox engine draws 6 kg Oxygen per kg Hydrogen across the four separate tanks per the §3.7 drain rule; ZBO power for the LH2 tanks comes from the carrier's PW-SA-RO. Peak proper acceleration 101.8/16.6 = 6.1 m/s² (0.63 g) — joint loads trivial (the payload stack joint sees 13.5 t × 6.13 = 83 kN).
- Buoyancy check at 55 km (ρ ≈ 0.9 kg/m³, T ≈ 300 K, p ≈ 0.5 atm — 03-solar-system.md): envelope volume 11,700 m³ of Hydrogen → net lift = 11,700 × 0.9 × (1 − 2.016/43.45) ≈ **10,050 kg** vs. floated mass 8.9 t (12.0 minus jettisoned AR-SHELL 2.5 and AR-CHUTE 0.6) → buoyancy margin 13%. (Design note surfaced in-game: in CO2, breathable air lifts 0.30 kg/m³ — crewed aerostats at T3 keep their habitat *inside* the envelope, per HAVOC.)

## 5. Player Interaction & UI

- **Drydock screen** (vector/schematic art): grid canvas; part palette filtered by category/tier; mirror-symmetry toggle (x-axis); sub-assembly save/load; blueprint export (JSON, shareable).
- **Live readout panel** (always visible, recomputed per edit, all from §3 formulas): wet/dry mass; per-stage dv (with SL/vac/trajectory-avg toggle and g_ref selector), TWR at ignition/burnout, burn time; COM markers (wet/dry) + thrust-line overlay with GREEN/YELLOW/RED stability badge and engine-out badge; part count /600; cost total; crew capacity vs. sleeps; pressurized volume; power balance preview (generation vs. draw, at selected solar distance — 09); radiator margin (09); MMOD coverage % and P_pen/yr at selected orbit; q_max worst part; spin section: rpm slider with live a_spin, comfort verdict, balance offset.
- **Validation list** with stable codes (clicking zooms to the offender): E1 no command source; E2 disconnected parts; E3 invalid decoupler; E4 overlapping footprints; E5 plume impingement; E6 joint overload at the design-selected limiter accel (§3.8a); E7 q_max exceeded in pre-flight ascent sim; E8 port size mismatch; E9 crewed spin > 6 rpm; E10 negative dry mass from cargo-manifest misconfiguration; E11 q̇_max exceeded in pre-flight entry sim (§3.15); W1 liftoff TWR < 1.2 (02 §3.7; recommended 1.3-1.5); W2 no airlock with crew; W3 no storm shelter beyond LEO (§3.11 shelter rule); W4 solid above liquid stage; W5 dv below mission planner target; W6 spin imbalance > 0.02·r; W7 uncovered hull in high-flux orbit; W8 insufficient docking ports for crew logistics; W9 crossfeed duct flow cap throttles engines (§3.7).
- **Pre-flight ascent sim**: one-click 2D ascent integration (same code path as flight, 13-architecture.md) plotting q, q·α, accel, and throttle vs. time with limit lines.
- **Station view**: docking topology graph overlay; per-port load/rating; station-keeping dv/yr forecast; spin-up/spin-down buttons with propellant quote (§3.10 formula).
- Engineer-founder fantasy: every readout has a "show the math" hover expanding the formula with the current numbers plugged in.

## 6. Progression Hooks

| Tier | Act | Unlocks (this document) |
|---|---|---|
| T0 (2049 baseline) | Act 1 | Flight-proven chemical line per 02 §6 / 11 PR-00: EN-K1/K1V kerolox, EN-H1 hydrolox, EN-HYP/EN-HYP-L storables, EN-SRB/EN-KICK solids, RCS-N2 + RCS-HYP; smallsat-scale EP strings EN-ION-2 (NSTAR) + EN-HALL-1 (SPT-100); basic tanks, PAD-1/2, fairings, capsules, rigid modules, BEAM-class inflatable, IDSS/CBM ports, basic Whipple, legacy + ROSA arrays |
| T1 | Acts 1-2 | PAD-3; EN-M2/M2V Raptor-class methalox reuse (=M-2256/MV-2530, behind 11's era node PR-02) + RCS-CH4 hot-gas quads; EN-LND lander engine; EN-H2 reusable hydrolox; EN-ION-N (NEXT, PR-06) + EN-HALL (AEPS, PR-07) EP strings; ZBO LH2 tanks, TK-DEPOT cryo depot, FD-1 crossfeed, DK-L fluid berth, DK-ARM orbital assembly, TransHab/B330-class inflatables, stuffed Whipple, storm shelter, Kilopower-1 |
| T2 | Acts 2-4 | EN-NTR-S/L (=NTR-73/246), EN-ML methalox lander, LH2-L tanks, SP-HUB/ARM/TETHER/HAB spin sections, Kilopower-10 / FSP-100, HB-GRN-S partial-closure greenhouse (11 LS-04), Dry Dock module (assemble beyond fairing limits), ISRU printing of STRUCT/TANK/MECH/SHIELD (BasaltFiber & IronSteel variants) |
| T3 | Acts 4-5 | X3-class Hall clusters, VASIMR, MPD, NEP 2 MWe, EN-NTR-B bimodal NTR (=NTR-111B), SP-RING 1 g ring segments, HB-GRN full-diet greenhouse (11 LS-07 era), HAVOC-class aerostat deployment hardware (AR-SHELL/AR-CHUTE §4.9; AR-ENV/AR-GON/AR-INF in 07's catalog per DECISIONS A10 — matches 07 §4.3.3 / 11), orbital ENGINE/HAB/ELEC printing |
| T4 [SPECULATIVE] | Act 5 / Endgame | EN-FT fusion drive (=DFD-5), He3 supply chain [SPECULATIVE], interstellar-precursor bus structures, reactor printing |

Act gating in practice: Act 1 is launcher design under pad/fairing/budget constraints on the T0 flight-proven line, broken open by PR-02's reusable methalox $/kg collapse; Act 2 adds orbital assembly and depots (Moon); Act 3 is the NTR + ISRU-printing inflection (Mars builds get cheap); Act 4 is spin-gravity stations and aerostats; Act 5 is MW-class electric ships; Endgame is the fusion drive and self-sufficient off-Earth shipyards (no Earth imports in any recipe).

## 7. Cross-System Interfaces

**Consumes:**
- 01-orbital-mechanics.md: mission dv targets for the planner from the Table 4.2 catalog (LEO 9,400; TMI = R1 3,590; Venus transfer = V1 3,480; LEO→LLO low-thrust ≈8,000 m/s — any design margin is stated separately, never folded into the catalog quote); low-TWR burn-splitting rule; ascent guidance (α profile); the station-keeping fee curve (Table 4.8, §3.12); the entry-heating constants and TPS class table (§3.11 / Table 4.5: Sutton-Graves k per atmosphere, f_rad, E_abl = 50 MJ/kg — binding for §3.15 and the §4.7/§4.9 TPS stats).
- 02-propulsion.md: authoritative engine performance stats and tiers (§4.2-4.7 — §4.3-4.5 here republish them verbatim and must match 02's master list), throttle ranges, ullage/restart rules, boiloff rates, TWR thresholds (§3.7), the NTR 60 km Earth rule (§3.10), the engine reliability model (§3.14), and the RP1/NTO/MMH resource extensions (§4.1).
- 03-solar-system.md: atmosphere ρ(h) profiles (max-Q, drag, aerostat deployment), MMOD flux Φ by region, body g and radiation environments.
- 04-resources-isru.md: canonical resource properties/densities; sign-off on any late ISRU synthesis routes for 02's RP1/NTO/MMH extensions (Q1).
- 05-industry-logistics.md: fabrication rates, machine-shop/printer buildings, standard container spec (CG-CON mounts it), propellant transfer rates, launch logistics.
- 08-life-support-crew.md: crew mass (100 kg w/ suit), consumable rates, habitable-volume morale curve, radiation dose model, spin-adaptation effects.
- 09-power-thermal.md: array/reactor/radiator performance (parts §4.6 are builder stubs of 09's systems), ZBO power draws.
- 10-vehicles.md: construction drones (orbital assembly), landers/rovers reuse this part system and builder math.
- 11-research-tech.md: tier unlock placement of every part.
- 12-gameplay-economy-ui.md: prices (including the RP1/NTO/MMH rows 02 §4.1 requires), commercial launch market, contracts, event system (MMOD conjunctions; reliability events are *rolled* by 02 §3.14's model and surfaced through 12).
- 13-architecture.md: physics body merging on dock, 600-part cap rationale, ascent-sim code path, blueprint serialization.

**Provides:**
- To 01/02: vessel mass properties (m, COM, I), thrust/torque tables, per-stage dv — the flight model's inputs.
- To 01: the per-part Cd·A drag table (frontal-area default §3.12, deployed areas §4.6/§4.9; Cd = 2.2 default) for below-interface drag integration (ascent, entry, aerobraking — above the interface 01 charges its Table 4.8 fee instead, §3.12), plus entry-vehicle stats — shield diameter, TPS class and q̇_max per 01 Table 4.5, ablator budget, loaded area, protected column (§3.15). 01 owns the entry/aerocapture trajectory integration and the heating constants; this doc owns what heating does to parts.
- To 05: part material classes + masses (manufacturing demand), depot/berth fluid-transfer interfaces.
- To 07: station modules, spin sections, aerostat entry hardware — AR-SHELL/AR-CHUTE; the envelope/gondola/inflation rows live in 07's own catalog per DECISIONS A10 (07 owns surface/atmosphere base operation; the boundary is "if it can free-fly, it's mine").
- To 08: pressurized volumes, crew capacities, shelter shielding mass per module.
- To 09: per-part power draws and radiator mounts; reactor placement rules (shadow-shield cone covers parts within ±10° aft).
- To 11: research-able part list with tiers.
- To 12: cost ledger per design; failure-event hooks.
- To 13: the complete builder data model (grid, graph, stages) and validation rule list (E1-E11, W1-W9).

## 8. Failure Modes & Edge Cases

1. **Joint overload** (§3.8a violated in flight, e.g. player overrides the g-limiter): joint breaks; vessel splits into two physics bodies; downstream parts uncontrolled. Deterministic, no RNG.
2. **Max-Q part loss**: exposed part exceeding q_max is destroyed; if it was structural, cascades to joint check.
3. **q·α stack break**: snap at the highest-load joint; the dramatic "rocket folds at max Q" failure for hand-flown pitch-overs.
4. **Engine-out**: ignition and in-flight failure probabilities are owned by **02 §3.14** — per-class `p_base` per ignition (solid 0.001; pressure-fed liquid 0.0005; pump-fed liquid 0.002 new type, 0.0005 once Mature; NTR 0.003; electric 0.0002) and `λ0` per burn-second, both multiplied by the wear factor (1 + 9·w²); a type goes **Mature** (p_base and λ0 ÷4, every class) after 25 program-wide successful ignitions, with 11 §3.4's maturity stack layered on top — there is no per-tier halving and no separate model in 12. DECISIONS A5 ratifies the unified wear model: **02's per-ignition/wear base × 11's maturity factor × 05's spares/MTBF consumption** — orthogonal multipliers, no double counting; ships as an interface test in Phase 1. Failure outcomes (70% benign shutdown / 25% dead / 5% energetic, solids and EP per their own splits) follow 02 §3.14's outcome roll; the adjacent-module damage from an energetic failure resolves in this doc's damage model. The §3.3 engine-out badge tells the player at design time whether a single failure is survivable.
5. **Landing failures**: touchdown v > 3 m/s or leg load > rating → leg collapse; tip-over per §4.9 rule; engine plume on > 20° slope triggers slide.
6. **Docking bounce**: §3.11 capture limits missed → elastic bounce at 0.5× closing speed, possible part damage above 0.5 m/s.
7. **MMOD penetration**: per §3.9; leaks interface to 08; unrepaired tank leaks drain to vacuum. Repair: EVA crew or drone + MachineParts (rate in 05).
8. **Spin imbalance**: mass change on a spinning station (undocking, tank drain) re-evaluates balance; > 0.02·r offset starts wobble (comfort penalty, port-rating halving); > 0.10·r forces emergency despin.
9. **Rotating-seal failure** (SP-HUB, MTBF event from 12): hub leaks 0.1 kg/h air until repaired; ports on the hub locked.
10. **Boiloff exhaustion**: ZBO power loss → cryo propellant vents (rates from 02); the Mars ship that loses its reactor slowly loses its return ticket — visible on the resource timeline.
11. **CMG saturation**: accumulated torque > momentum capacity → attitude control degrades to RCS; desaturation burn consumes RCS propellant (`m = H_total / (r_t · Isp · g0)`).
12. **Stranded-stage edge case**: decoupling with no command source on one side creates debris (tracked, becomes MMOD conjunction source in LEO).
13. **Numerical edge cases**: dv readout shows 0 (not NaN) when m_prop = 0 or no engine in stage; ratio guards for m1 ≤ 0 (validation E10 catches negative dry mass from cargo misconfig); docking loops always rigidized through one canonical joint — the §3.8(a) cycle rule — to prevent solver explosions (13).
14. **Part-cap griefing**: docking that would exceed 600 parts is refused with a UI explanation (no silent failure).
15. **Fairing edge case**: deploying inflatables/arrays inside an intact fairing or bay is blocked (E5-class error), preventing the classic "exploded my own fairing" bug.
16. **Bipropellant flameout**: if either resource of an engine's O/F pair runs out, the engine shuts down — deterministic, no RNG (§3.7); restart per 02's ullage/restart rules once both resources flow again. The dv readout already excludes the stranded surplus of the other resource (burnable propellant is min-limited at the engine's O/F).

## 9. Open Questions

1. **Engine registration requests to 02 — ACCEPTED per DECISIONS A8** (catalog owner — nothing ships here until 02 lists it; precedent: NTR-111B). All three registrations were accepted; 02 to publish the stats, builder stubs land here when 02's rows do. (a) A small "Bantam"-class methalox SL/vac pair (Archimedes/Neutron anchor, ~800 kN class) for compact T1 launchers under PR-02. (b) An argon-fueled AEPS derivative for a cheap mid-tier Argon Hall string (currently argon capability starts at HALL-100/MPD/VAS, T3). (c) The pump-fed methalox lander row requested by 10 §9 (HOP-P's sortie class). Resolved and withdrawn: the storable apogee niche (covered by OMS-27/SPS-91), the RL10B-2 variant (H-102/RL10C-1 is the hydrolox master), the bimodal NTR (NTR-111B, now stubbed as EN-NTR-B), and the Discovery II torch (02's T4 catalog DFD-5 replaces it as EN-FT).
2. **Storable/kerolox resources — RESOLVED.** 02 §4.1 declares **RP1, NTO and MMH** as canonical-resource extensions (exact spellings, no hyphen in RP1); this doc's tanks, engines and RCS use them directly (no merged "Hypergols" commodity, no sealed Earth-only kerolox tank). Remaining actions elsewhere: 12 §4.3 must add RP1/NTO/MMH price rows; 04 owns whether late ISRU synthesis routes (e.g. Ammonia-chain MMH at T3) ever exist.
3. **NTR overflight policy — RESOLVED per 02 §3.10.** Hard rule: no NTR operation below 60 km altitude on Earth (regulatory; launch cold, first criticality in orbit; violation = mission-ending regulatory event via 12); other bodies unrestricted within the engine's p_max 30 kPa (Mars-ambient ignition legal, Titan surface not). This doc carries no separate 50 kPa rule.
4. **Propellant-shift COM realism.** We freeze propellant at tank centroids (§3.2). Is the resulting error acceptable for long LH2 stages (real COM moves meters as tanks drain)? Option: linear COM interpolation per tank between full/empty centroids — cheap, worth it?
5. **Stuffed-Whipple ISRU parity.** WS-BF at η = 0.97 vs imported 0.98 — is a 1-point difference worth the UI complexity, or should they be identical?
6. **Spin-section rendering.** 2D side view of a rotating ring is visually ambiguous; current plan is a schematic "ring inset" panel. Needs UI prototype (12/13).
7. **Reliability model granularity — RESOLVED.** Both layers already exist in canon: 02 §3.14 owns per-ignition/per-second engine failure *and* wear-based growth (refurbish via 05's workshops at 20% MachineParts cost), and 11 §3.4 layers type maturity on top. Spare-parts logistics matter exactly as much as 02's wear curve makes them; no separate model in 12 or here. DECISIONS A5 ratifies this as the one wear model — 02 per-ignition/wear base × 11 maturity factor × 05 spares/MTBF consumption, orthogonal multipliers with no double counting — shipping as a Phase 1 interface test.
8. **Aerostat hand-off boundary.** This doc delivers the aerostat to float-positive at 55 km; 07-bases-habitats.md takes over. The deployment hardware is statted here (§4.9 AR-SHELL/AR-CHUTE/AR-ENV/AR-GON/AR-INF); confirm 07 does not want the envelope/gondola entries migrated to its own catalog (if migrated, §4.9 keeps AR-SHELL/AR-CHUTE and Build D references 07's IDs). **RESOLVED per DECISIONS A10: migrated.** AR-ENV/AR-GON/AR-INF now live in 07's catalog; §4.9 keeps AR-SHELL/AR-CHUTE plus a one-line pointer, and Build D references 07's entries.
