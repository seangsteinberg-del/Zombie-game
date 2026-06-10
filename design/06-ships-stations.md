# 06 — Ships & Stations: Modular Construction

## 1. Overview

This document specifies how the player designs, validates, assembles, and operates every vessel in the game: launch vehicles, transfer ships, tugs, landers, and orbital stations. It defines:

- The **2D side-cross-section grid editor** (the "Drydock") and its part-attachment rules.
- The **builder math**: total mass, wet/dry mass, center of mass (COM), 2D thrust-vector alignment, live Tsiolkovsky delta-v readout, per-stage TWR, and burn times. Every formula a programmer needs is in §3.
- A **simplified structural-integrity model**: joint-graph axial load checks, g-limits, a max-Q rule, and a q-alpha rule for atmospheric ascent.
- **Station mechanics**: spin-gravity sections with real comfort limits, pressurized volume per crew, docking topology, and station-keeping budgets.
- A **catalog of 110 parts** (§4) with mass, cost, tier, and stats, including inflatable habitats (TransHab anchor) and ISRU-manufactured variants (BasaltFiber/IronSteel printed structure).
- **Four fully worked example builds** with complete mass budgets and computed delta-v (§4.11).
- **Three construction flows**: Earth launch (pad and fairing constraints), orbital assembly, and ISRU manufacture (interfacing 05-industry-logistics.md).

Design philosophy: the editor is a *spreadsheet you can see*. Nothing is hidden — every readout traces to a formula in this document, and the same formulas drive the flight simulation. There is no "magic balance layer" between design-time numbers and flight-time physics.

Ownership boundaries: engine physics and propellant chemistry beyond catalog stats → 02-propulsion.md; power/thermal performance curves → 09-power-thermal.md; life-support consumption → 08-life-support-crew.md; surface vehicles → 10-vehicles.md; manufacturing rates and logistics containers → 05-industry-logistics.md; prices and contracts → 12-gameplay-economy-ui.md; physics engine implementation → 13-architecture.md.

## 2. Real-World Grounding

Every part and rule below names its anchor. Key anchors:

- **Chemical engines**: SpaceX Merlin 1D (845 kN SL, Isp 282 s SL / 311 s vac, ~470 kg); Merlin Vacuum (981 kN, 348 s); SpaceX Raptor 2 (~2,256 kN SL, Isp ~327 s SL / ~350 s vac, ~1.6 t); Raptor Vacuum (Isp ~378 s); Aerojet RL10B-2 (110.1 kN, Isp 465.5 s, 277 kg); RS-25 (1,860 kN SL / 2,279 kN vac, Isp 366/452.3 s, 3,177 kg); AJ10-118K storable (43.4 kN, Isp ~320 s); Aerojet R-4D RCS (490 N, Isp ~312 s, 3.76 kg); Star 48B solid kick stage (2,141 kg gross / 2,010 kg propellant, Isp 292.1 s, 84.1 s burn → ~68 kN mean thrust); GEM 63 SRB (~49 t gross / ~44 t propellant, Isp ~279 s vac).
- **Nuclear-thermal**: NERVA program (XE' ground-tested 1969 at ~246 kN; delivered Isp ~710 s — 841 s was the ideal vacuum Isp excluding turbine-bleed and cooling losses; ~900 s is the modern NTP design goal); NASA Mars Design Reference Architecture 5.0 (three 111 kN / 25 klbf NTR engines, Isp ~900 s, LH2 propellant); modern BWXT/NASA NTP studies target engine T/W ≈ 3-3.5.
- **Electric propulsion**: NSTAR (2.3 kW, 92 mN, Isp 3,120 s — flew on Deep Space 1, Dawn); NEXT-C (6.9 kW, 236 mN, Isp 4,190 s — flew on DART); AEPS Hall thruster (12.5 kW, ~589 mN, Isp ~2,800 s — Gateway PPE); X3 nested Hall (5.4 N at 102 kW, lab-demonstrated 2017); VASIMR VX-200 (~5.7 N at 200 kW, Isp ~5,000 s, lab) [T3]; lithium MPD thrusters (100-500 kW lab demos, Princeton LiLFA / MAI; the MAI 500 kW Li-MPD produced ~12.5 N at ~45-60% efficiency) [T3].
- **Habitats**: NASA TransHab (8.2 m inflated diameter, ~340 m³, ~13.2 t); Bigelow BEAM (1.4 t, 16 m³, flown on ISS); Bigelow B330 (~20 t, 330 m³, engineering-complete design); ISS Destiny lab (14.5 t, ~106 m³); Quest airlock (6.1 t); ISS Cupola (1.8 t).
- **Habitable volume**: NASA long-duration habitability studies converge on ≈25 m³ net habitable volume per crewmember as the long-duration minimum; ISS provides ~64 m³/crew at 6 crew.
- **Spin gravity comfort**: classic NASA-era criteria (Hill & Schnitzer 1962; 1970s Stanford/NASA Ames summer studies): spin rate ≤ 4 rpm for adapted crews (≤ 2 rpm without adaptation), head-to-foot gravity gradient ≤ 8%, rim speed ≥ 6 m/s to keep Coriolis effects tolerable. Later research (Globus & Hall, 2017) argues higher rates are trainable; we keep the conservative limits and hard-cap at 6 rpm.
- **MMOD protection**: ISS Whipple shields — thin sacrificial aluminum bumper (≈2 mm = 5.4 kg/m²) at 10-30 cm standoff, vaporizing impactors before the pressure wall; "stuffed" Whipple adds Nextel ceramic-fabric/Kevlar layers (ISS US Lab shielding ≈ 20-30 kg/m² total). In-game BasaltFiber cloth is the ISRU analog of Nextel ceramic fabric.
- **Docking**: International Docking System Standard / NASA Docking System (androgynous, 800 mm passage, ~330 kg); ISS Common Berthing Mechanism (1.27 m square hatch, ~0.2-0.3 t); Canadarm2 (17.6 m reach, ~1.8 t, handles up to 116 t).
- **Ascent loads**: Space Shuttle throttled down to hold max-Q near ~33 kPa (~700 psf); modern launchers see 25-40 kPa. Typical structural q·α (dynamic pressure × angle of attack) envelopes are ~3,000-4,500 psf·deg ≈ 145-215 kPa·deg.
- **Station keeping**: ISS at ~400 km expends roughly 5-25 m/s/yr of reboost delta-v depending on solar activity.
- **Tankage fractions**: Falcon 9 stages achieve propellant mass fractions ≈ 0.95+ (≈ 5-6% structure per unit propellant for kerolox/methalox); Centaur III (hydrolox) dry/propellant ≈ 0.11 including engines; dedicated LH2-only tanks with MLI and zero-boiloff cryocoolers run ~13-15% (NASA cryogenic fluid management studies). LH2 bulk density 70.85 kg/m³ is the driver. Dawn stored 425 kg Xenon in a 21.6 kg COPV (≈5%).
- **Power hardware** (stats canonical in 09-power-thermal.md): Kilopower/KRUSTY fission (1 kWe ≈ 0.4 t; 10 kWe ≈ 1.5 t); MMRTG (110 We, 45 kg); ISS legacy rigid arrays ≈ 30-35 W/kg; Roll-Out Solar Array (ROSA, flight-demonstrated) ≈ 80-100+ W/kg; Shuttle PC17C fuel cell (12 kW peak / 7 kW continuous, ~118 kg).
- **Venus aerostat**: NASA HAVOC study (Langley, 2014) — entry vehicle deploys a buoyant vehicle at ~50-55 km where Venus pressure and temperature are Earth-like; in 96.5% CO2 atmosphere (mean molecular weight ≈ 43.45 g/mol) even breathable air is a lifting gas (net lift ≈ 35% of H2's per m³; equivalently, ≈33% of the displaced CO2 mass).
- **Speculative tier anchor**: NASA GRC "Discovery II" fusion-vehicle study (TM-2005-213559): spherical-torus fusion, thrust ≈ 18 kN, Isp ≈ 35,000 s. [SPECULATIVE], T4 only.

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
- Worked example (Build A): two EN-M0 engines at x = ±1 m, 800 kN each, symmetric → τ_net = 0. One engine out: τ = 800 kN × 1 m = 800 kN·m; remaining engine authority = 800 × sin 5° × 14 m = 976 kN·m → flyable, since 800 ≤ 976 — full stop. Note that both the disturbance torque and the gimbal authority scale linearly with throttle, so throttling alone never changes the verdict; what throttling buys is margin against the throttle-independent RCS term. The full engine-out check is `|τ_fail(throttle)| ≤ τ_ctl_remaining(throttle) + τ_rcs`, displayed as the "engine-out" badge.
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
  `Isp(p) = Isp_vac − (Isp_vac − Isp_SL) · (p / 101.325 kPa)` , clamped at p = 101.325 kPa. Example: EN-M0 (298 s SL / 348 s vac) at 50 kPa ambient → 323 s.
- For first stages the editor also shows a **trajectory-averaged Isp** = `Isp_SL + 0.44 · (Isp_vac − Isp_SL)` (empirical fit to the ascent profile in 01-orbital-mechanics.md; for EN-M0 this gives 320 s). The worked builds in §4.11 use this average and also print the SL/vac bounds.
- **Electric propulsion**: thrust is power-limited: `F = 2 · η · P_in / (Isp · g0)` (N, with P in W). Catalog η: gridded ion 0.70, Hall 0.65 (nested X3 cluster 0.69), MPD 0.55, VASIMR 0.70 (VX-200 measured thruster efficiency at Isp 5,000 s). **Catalog thrust is authoritative**: the sim back-derives each entry's η = F · Isp · g0 / (2 · P_rated) and holds it constant when power-scaling. If available electrical power (09-power-thermal.md, including 1/d² solar falloff) is below rated, thrust scales proportionally at constant Isp. The dv readout is unchanged (dv is power-independent); the *burn time* readout is what grows.
- **Burn time**: `t_burn = m_prop / ṁ`, `ṁ = Σ F_i / (Isp_eff · g0)` (kg/s). **ṁ is a per-engine constant**, derived from any *consistent* catalog pair: `ṁ = F_vac / (Isp_vac · g0) = F_SL / (Isp_SL · g0)` (the paired thrust/Isp columns are consistent by construction). Thrust at ambient pressure then follows: **`F(p) = ṁ · g0 · Isp(p)`** — this is the formula the ascent sim and the TWR readout use between the SL and vac columns. Never mix one pressure condition's F with another's Isp (e.g. Build A's 128 s stage-1 burn is 70,000 kg / 547 kg/s with both numbers from the same engine constant; mixing trajectory-average Isp with SL thrust would wrongly give 137 s).

### 3.5 Thrust-to-weight ratio

`TWR = Σ F_i / (m · g_ref)` — displayed per stage at ignition (m = m0) and burnout (m = m1), against a player-selectable reference gravity:

| Body | g_ref (m/s²) |
|---|---|
| Earth | 9.80665 |
| Moon | 1.62 |
| Mars | 3.71 |
| (others) | from 03-solar-system.md body table |

Earth's g_ref equals the g0 constant of §3.4 so the TWR and dv readouts share one constant (no third-decimal QA discrepancies); all other bodies use the surface-gravity values canonical in 03-solar-system.md.

Rules of thumb surfaced in UI: surface launch requires TWR > 1.2 at ignition (warning below 1.3); upper stages ≥ 0.5 recommended; NTR/EP stages may be < 1 (the maneuver planner in 01-orbital-mechanics.md splits low-TWR burns into multiple periapsis passes when `t_burn > 0.1 · T_orbit`).

### 3.6 Staging editor rules

KSP-style ordered stage list S0 (first to fire) … Sn, edited by dragging part icons:

1. Stage events: `IGNITE(engine)`, `SEPARATE(decoupler)`, `JETTISON(fairing)`, `DEPLOY(chute/panel/radiator/inflatable)`.
2. A decoupler's separation must split G into exactly two connected components; otherwise validation error E3 ("separation would not detach anything / would orphan parts").
3. dv/TWR are computed bottom-up: stage k's `m0` includes all stages > k; jettisoned mass (fairings, spent boosters) leaves the ledger at its event.
4. An engine may not fire if its exhaust column (the grid cells in a `w_engine`-wide column below its nozzle, out to 6 m, where `w_engine` = the engine part's footprint width w from its §4.3-4.5 Size column) intersects a same-vessel part that has not yet separated — error E5 "plume impingement". RCS quads are exempt (per-nozzle thrust < 1 kN; see §4.5). Exception: the **vented interstage** part (ST-IS-V, anchor: Starship hot-staging ring) permits firing through it.
5. Solid motors cannot throttle or shut down; once lit they burn to depletion (warning W4 if a solid is staged above a liquid stage that ignites later).
6. **Acceleration limiter**: autopilot throttles to keep `a ≤ 4 g` with crew aboard, `a ≤ 6 g` uncrewed (player-overridable down to part limits, §3.8). The selected limiter is saved with the design, and the §3.8(a) joint check (validation E6) always evaluates at it. Solids ignore the limiter (their thrust curve is fixed).

### 3.7 Propellant flow and crossfeed

- **Mixture ratio (O/F) is an engine property** (catalog column, §4.3): methalox 3.6:1 Oxygen:Methane (Raptor), kerolox 2.36:1 Oxygen:RP-1* (Merlin), hydrolox 6.0:1 Oxygen:Hydrogen (RL10). Bipropellant *tanks* (TK-ML-*) are merely a packaging convenience pre-loaded at the matching ratio; engines do not require them. (*RP-1 is represented as the canonical resource Carbon-derived `Polymers`? No — see Open Question Q2; v1 ships kerolox as a sealed "Kerolox" tank filled only at Earth, avoiding a new resource.)
- **Drain rule**: an engine draws each of its propellant resources — at its O/F mass split, for bipropellants — from **all tanks within its own stage holding that resource** that are graph-connected through structural joints, proportionally across those tanks (keeps COM drift gentle). A hydrolox engine fed by separate TK-LOX-M and TK-LH2-M tanks therefore draws 6 kg Oxygen per 1 kg Hydrogen from them, exactly as it would from one combined tank. If either resource of the pair exhausts first, the engine **flames out** (§8.16); the editor's dv readout counts only *burnable* propellant (limited by the scarcer resource at the engine's O/F).
- **Crossfeed** between stages or across docking ports requires the **FD-1 fuel duct** (T1) or a fluid-transfer docking port (DK-L); this enables asparagus staging and depot refueling. Tanks connected through ducts/fluid berths form one **feed group**. Within a feed group, tanks drain in **descending stage number** — the soonest-separated stage's tanks empty first (this ordering is what makes asparagus staging work) — proportionally among tanks of the same stage. The editor exposes a per-tank **priority integer** that overrides the default order (higher priority drains first). Duct flow caps (FD-1: 1 t/min cryogenic, 5 t/min storable; 05-industry-logistics.md owns depot transfer rates) are enforced in flight: if connected engines demand more than the ducts can deliver, those engines throttle down to the deliverable flow — surfaced at design time as warning W9.
- **Solid motors** (EN-SRB, EN-KICK) are sealed single-use parts: their propellant is internal part mass, not a tracked canonical resource. They cannot be refilled, drained, or crossfed, and cannot be ISRU-printed below the ENGINE-class tier (§3.13). (Kerolox is the other sealed case — Q2.)
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

Example (Build A — uncrewed, limiter deliberately set to 5 g; full walkthrough in §4.11a): m_above at the interstage = 21.61 t. Unclamped burnout acceleration would be 1,868 kN / 29.11 t = 6.5 g, so the limiter clamps a at 49.03 m/s² → L = 21.61 × 49.03 = 1,060 kN ≤ 1,200 kN, PASS (12% margin). At the 6 g uncrewed default the same joint would see 1,272 kN → E6: the limiter setting is part of the design, and E6 always evaluates at the selected limiter. On-pad: 21.61 × 9.80665 = 212 kN, PASS.

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
- **Spin-up propellant** (RCS at radius r_t): `m_prop = I · ω / (r_t · Isp · g0)`, with `I = Σ m_i · r_i²` about the hub. Worked example: 200 t of ring mass at r = 56 m → I = 6.27×10⁸ kg·m²; ω(4 rpm) = 0.419 rad/s; a pair of R-4D quads (980 N total) at the rim: torque 54.9 kN·m, spin-up time 4,790 s (1.3 h), propellant 1,533 kg Hypergols. The SP-HUB's electric counter-torque motor can instead spin up against a counter-rotating section or flywheel for zero propellant (slower: motor torque 10 kN·m).

### 3.11 Pressurized volume, crew capacity, docking topology

- Each habitat part lists pressurized volume `V_press` (m³). Net habitable volume `V_hab = 0.7 · V_press` (fittings/equipment).
- **Crew capacity**: each habitat lists `sleeps` (permanent crew berths; surge berths noted separately). `V_hab_total` sums net habitable volume over **all pressurized modules** — labs, greenhouses, and cupolas count toward volume but contribute 0 sleeps. The binding boarding limits (displayed in §5 as "crew capacity vs. sleeps") are:
  - **Long-duration (> 30 days)**: `crew_max = min( Σ sleeps, floor(V_hab_total / 25 m³) )` per NASA habitable-volume guidance.
  - **Short-duration (≤ 30 days)**: `crew_max = min( Σ sleeps + surge berths, floor(V_hab_total / 10 m³) )`.
  - Exceeding the applicable limit is emergency-only and triggers the 08-life-support-crew.md morale-penalty tiers (heaviest below 10 m³/crew).
- Stations/ships with crew additionally require (validation warnings, not errors): ≥ 1 airlock for EVA capability; ≥ 1 docking port per 4 crew for logistics; a radiation storm shelter beyond LEO (W3; 08 owns dose math). **Shelter rule (implementable W3 check)**: HB-STORM qualifies outright; any other module qualifies iff **every footprint edge cell is adjacent to (or covered by radial shield panels) parts whose summed areal densities reach ≥ 500 kg/m² across that edge**, where a part's areal density = part mass including contents / part hull area. Water counts. Worked example: a full TK-H2O is 2.1 t over hull area 2·(1+2) = 6 m² → 350 kg/m², so a single water-tank layer is *not* enough — two stacked layers (700 kg/m²) qualify.
- **Docking topology**: docking edges join vessel graphs. Ports are androgynous within a size class (IDSS anchor); sizes must match: S (0.8 m passage), B (1.27 m), L (3.0 m structural berth). Closed loops are allowed only through L-class berths (rigidized into one physics body; 13-architecture.md merges bodies on dock).
- **Port load ratings**: burns while docked check the §3.8(a) joint formula across the docking joint with `L_rated`: DK-S 60 kN, DK-B 150 kN, DK-L 800 kN. Example: Build B's NTR stage pushing its 30 t payload through a DK-L at burnout (a = 5.32 m/s²) → 160 kN ≤ 800 kN, PASS. Pushing the same payload through a DK-S would fail (160 > 60) — tugs must pull gently or berth structurally.
- **Docking capture limits** (else bounce-off): closing speed ≤ 0.1 m/s (S/B) or ≤ 0.05 m/s (L), lateral offset ≤ 0.1 m, approach angle ≤ 5°. Magnetic soft-capture (T1 port upgrade) doubles these.

### 3.12 Station keeping

Drag makeup for stations in low orbits (atmosphere model from 03-solar-system.md):

```
a_drag = Cd · A_drag · ρ · v² / (2 m)      Cd = 2.2
dv_year = a_drag · 3.156×10⁷ s
```

`A_drag` = Σ exposed-part frontal areas + deployed areas of arrays/radiators/dishes (catalog "deployed area" stats, §4.6/§4.9 — arrays dominate). **Frontal-area default**: `w × 1 m²` per exposed stack part (the 2D grid's unit depth convention), with catalog overrides where listed; Cd = 2.2 for everything (free-molecular, tumbling-average). The same per-part Cd·A table is exported to 01-orbital-mechanics.md for the ascent-drag integration (§7). Representative table for a 200 t station with A_drag = 1,000 m² at Earth (mean solar activity):

| Altitude | ρ (kg/m³) | dv/year |
|---|---|---|
| 300 km | 2×10⁻¹¹ | 204 m/s |
| 350 km | 7×10⁻¹² | 72 m/s |
| 400 km | 3×10⁻¹² | 31 m/s |
| 450 km | 1.5×10⁻¹² | 15 m/s |
| 500 km | 6×10⁻¹³ | 6 m/s |

(Cross-check: ISS, 420 t and larger area, uses 5-25 m/s/yr — same order.) Above ~600 km Earth, drag is negligible at game timescales. Low lunar orbits are perturbed by mascons — 01-orbital-mechanics.md owns that budget (placeholder 5-30 m/s/yr depending on altitude; frozen orbits exempt). Reboost can come from any docked engine or station thrusters; the resupply burden is the real gameplay cost (05-industry-logistics.md).

### 3.13 Construction flows

**(1) Earth launch.** Vessels built at a pad must pass: liftoff TWR > 1.2, max-Q/q·α checks, and pad class limits:

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

Entry/aerocapture trajectory integration and corridor planning are owned by 01-orbital-mechanics.md; this section owns what heating does to parts, and the catalog supplies the stats 01 needs (shield diameter, q̇_max, ablator mass, protected column — see §7 Provides).

- **Stagnation heat flux** (Sutton-Graves, SI units): `q̇ = k · sqrt(ρ / r_n) · v³` [W/m²], with `k = 1.7415×10⁻⁴` (kg^0.5/m), ρ(h) from 03-solar-system.md, v = speed relative to the rotating atmosphere, and `r_n` = effective nose radius = half the footprint width (w/2, m) of the foremost part along the velocity vector. Sanity anchor: LEO entry at 7,800 m/s, ρ = 3×10⁻⁴ kg/m³, r_n = 1.85 m → q̇ ≈ 1.0 MW/m².
- **Per-part rating `q̇_max`**: default **0.5 MW/m²** for every exposed part (survives high-altitude skip heating, not entry). Heat shields and aeroshells (UT-HS3/5, AR-SHELL; integral capsule shields on HB-CAP2/CAP4) are rated **10 MW/m²** while ablator remains (PICA-class; Stardust saw ~12).
- **Protection geometry** (the mirror image of the E5 plume rule): a shield **protects every part whose footprint lies within the shield's w-cell-wide column behind it** (away from the velocity vector). The vessel must hold the shield within ±10° of the velocity vector; outside that cone, trailing parts are treated as exposed (in-flight warning). Parts inside an intact fairing or cargo bay are protected by it up to the *fairing's* 0.5 MW/m² rating (fairings are not entry shields).
- **Ablator budget**: a shield loses ablator mass at `ṁ_abl = q̇ · A_shield / h_abl`, with `h_abl = 150 MJ/kg` effective heat of ablation (PICA-class; re-radiated fraction included). Catalog ablator masses: UT-HS3 0.30 t, UT-HS5 0.55 t, AR-SHELL 0.90 t, HB-CAP2 0.20 t, HB-CAP4 0.35 t. A depleted shield reverts to the 0.5 MW/m² default — multi-pass aerocapture draws down the same budget as entry.
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
| TK-KL-M | Kerolox tank M (sealed) | T0 | 2×4 | 0.70 | 14 | 0.8 | Earth-fill only (see Q2) | F9 S1 PMF ≈ 0.95 |
| TK-LH2-M | LH2 tank M (ZBO) | T1 | 2×5 | 0.60 | 4.0 | 1.5 | Hydrogen; needs 0.4 kWe ZBO | LH2 70.85 kg/m³; CFM studies |
| TK-LH2-L | LH2 tank L (ZBO) | T2 | 4×9 | 3.0 | 20 | 5 | Hydrogen; needs 1.7 kWe ZBO | DRA 5.0 LH2 tanks |
| TK-LOX-M | LOX tank M | T0 | 2×3 | 0.40 | 8.0 | 0.5 | Oxygen | ISRU product storage |
| TK-CH4-M | Methane tank M | T0 | 2×3 | 0.35 | 7.0 | 0.5 | Methane | — |
| TK-HYP-S | Storable-prop tank S | T0 | 1×2 | 0.10 | 1.6 | 0.4 | Hypergols (MMH/NTO pair; see Q1) | Apollo SM tankage |
| TK-XE-S | Xenon COPV S | T0 | 1×1 | 0.025 | 0.42 | 0.6 | Xenon | Dawn: 425 kg Xe / 21.6 kg tank |
| TK-XE-L | Xenon COPV L | T1 | 2×2 | 0.24 | 4.0 | 2.0 | Xenon | — |
| TK-H2O | Water tank | T0 | 1×2 | 0.10 | 2.0 | 0.2 | Water; counts as shelter shielding | ISS water bags |
| TK-N2 | Gas bottle (N2/Ar) | T0 | 1×1 | 0.05 | 0.25 | 0.2 | Nitrogen or Argon @ 30 MPa | COPV |
| TK-DEPOT | Cryo depot tank | T1 | 5×12 | 14.0 | 200 | 25 | any cryo pair; ZBO 6 kWe; 2× DK-L fluid ports | ULA/NASA depot studies |

### 4.3 Engines — chemical & solid (11)

Size = grid footprint w×h; the §3.6 plume rule's `w_engine` is the part's w, and the nozzle face exposes no attach node (§3.1). O/F = oxidizer:fuel mass ratio the engine draws (§3.7). All §4.3-4.5 entries are material class **ENGINE** (§3.13); engine stack nodes are rated `max(1,200 kN, 1.25 × rated vacuum thrust)` (§3.8a).

| ID | Name | Tier | Size | Mass (t) | Thrust SL/vac (kN) | Isp SL/vac (s) | Prop | O/F | Gimbal | Cost | Anchor |
|---|---|---|---|---|---|---|---|---|---|---|---|
| EN-K1 | "Mule" kerolox SL | T0 | 1×2 | 0.47 | 845 / 914 | 282 / 311 | kerolox | 2.36 | ±5° | 1.5 | Merlin 1D |
| EN-K1V | "Mule-Vac" kerolox | T0 | 1×3 | 0.60 | — / 981 | — / 348 | kerolox | 2.36 | ±5° | 2.0 | Merlin Vacuum |
| EN-M2 | "Drayhorse" methalox SL | T0 | 2×3 | 1.6 | 2,256 / 2,530 | 327 / 350 | methalox | 3.6 | ±5° | 2.5 | Raptor 2 |
| EN-M2V | "Drayhorse-Vac" | T0 | 2×4 | 1.8 | — / 2,300 | — / 378 | methalox | 3.6 | ±3° | 3.0 | Raptor Vacuum |
| EN-M0 | "Bantam" methalox SL | T0 | 1×2 | 0.9 | 800 / 934 | 298 / 348 | methalox | 3.6 | ±5° | 1.2 | Archimedes-class (Neutron) |
| EN-M1V | "Bantam-Vac" | T0 | 1×2 | 0.4 | — / 120 | — / 360 | methalox | 3.6 | ±4° | 0.8 | small GG vac methalox (conservative vs RVac 378 s) |
| EN-H1 | Hydrolox vac engine | T0 | 2×4 | 0.28 | — / 110 | — / 465.5 | hydrolox | 6.0 | ±4° | 12 | RL10B-2 (2.2 m extendible nozzle) |
| EN-H2 | Reusable hydrolox SL | T1 | 2×4 | 3.18 | 1,860 / 2,279 | 366 / 452.3 | hydrolox | 6.0 | ±8° | 40 | RS-25 |
| EN-HYP | Storable apogee engine | T0 | 1×1 | 0.10 | — / 43.4 | — / 319 | Hypergols | — (paired commodity, Q1) | ±4° | 3 | AJ10-118K |
| EN-SRB | Strap-on solid booster | T0 | 2×12 | 5.1 + 44.2 prop | ~1,290 mean (vac) | 252 / 279 | solid (integral, §3.7) | — | fixed | 6 | GEM 63 (≈49 t gross, 94 s burn) |
| EN-KICK | Solid kick stage | T0 | 1×2 | 0.13 + 2.01 prop | — / ~68 mean | — / 292 | solid (integral, §3.7) | — | spin-stab | 1.5 | Star 48B |

### 4.4 Engines — nuclear thermal (3)

Class **ENGINE** (§3.13); monopropellant Hydrogen (no O/F). Sizes include the integral shadow shield.

| ID | Name | Tier | Size | Mass (t) | Thrust vac (kN) | Isp (s) | Prop | Notes | Anchor |
|---|---|---|---|---|---|---|---|---|---|
| EN-NTR-S | NTR, 111 kN | T2 | 2×5 | 3.4 | 111 | 900 | Hydrogen | shadow shield incl.; no Earth ops where ambient pressure exceeds 50 kPa, i.e. below ~5.5 km altitude (policy: exhaust is clean H2 but reactor-overflight rules apply, 12 owns; see Q3); T/W ≈ 3.3 | DRA 5.0 25-klbf class; NERVA heritage (XE' 246 kN, ~710 s delivered Isp; 841 s ideal vac) |
| EN-NTR-L | NTR, 250 kN | T2 | 3×6 | 8.5 | 250 | 900 | Hydrogen | T/W ≈ 3.0 (modern composite fuel; historical NERVA XE was far heavier) | NERVA XE-class thrust |
| EN-NTR-B | Bimodal NTR | T3 | 2×5 | 4.6 | 111 | 900 | Hydrogen | + 25 kWe electrical in idle mode (09) | bimodal NTR studies (Borowski et al.) |

### 4.5 Engines — electric & RCS (10)

EP thrust scales with available power (§3.4); per-string masses include PPU and gimbal. Class **ENGINE** (§3.13). EP propellants are single-resource (no O/F). RCS quads are 1×1 **surface-mount** parts: they attach radially to any hull edge cell and are exempt from the E5 plume rule (per-nozzle thrust < 1 kN).

| ID | Name | Tier | Size | Mass (t) | Thrust | Isp (s) | Power | Prop | Cost | Anchor |
|---|---|---|---|---|---|---|---|---|---|---|
| EN-ION-N | Ion thruster string | T0 | 1×1 | 0.06 | 236 mN | 4,190 | 6.9 kWe | Xenon | 5 | NEXT-C (flew on DART) |
| EN-HALL | Hall thruster string | T0 | 1×1 | 0.08 | 589 mN | 2,800 | 12.5 kWe | Xenon | 3 | AEPS (Gateway PPE) |
| EN-HALL-AR | Argon Hall string | T2 | 1×1 | 0.09 | 480 mN | 2,400 | 12.5 kWe | Argon | 3 | krypton/argon Hall research (Starlink krypton heritage) |
| EN-HALL-X | Nested Hall cluster | T3 | 2×2 | 0.50 | 5.4 N | 2,650 | 102 kWe | Xenon/Argon | 12 | X3 (lab, 2017) |
| EN-VAS | Plasma rocket | T3 | 2×3 | 1.2 | 5.7 N | 5,000 | 200 kWe | Argon | 20 | VASIMR VX-200 (lab) |
| EN-MPD | Lithium MPD thruster | T3 | 2×2 | 0.8 | 12 N | 4,000 | 430 kWe | Xenon (game-simplified; real demos used lithium) | 15 | MAI/Energiya 500 kW Li-MPD (~12.5 N demo); Princeton LiLFA (η ≈ 0.55 per §3.4) |
| EN-FT | Fusion torch [SPECULATIVE] | T4 | 8×20 | 180 | 18 kN | 35,000 | self-powered (3 GW jet) | Hydrogen (+He3 catalyst, [SPECULATIVE]) | 2,000 | NASA GRC Discovery II study |
| RCS-N2 | Cold-gas quad | T0 | 1×1 surface-mount | 0.01 | 4×50 N | 68 | — | Nitrogen | 0.1 | industry standard |
| RCS-HYP | Storable RCS quad | T0 | 1×1 surface-mount | 0.015 | 4×490 N | 312 | — | Hypergols | 0.4 | R-4D |
| RCS-CH4 | Hot-gas methalox quad | T1 | 1×1 surface-mount | 0.03 | 4×400 N | 280 | — | Methane+Oxygen (gas, O/F 3.6) | 0.6 | Starship hot-gas RCS |

### 4.6 Power & thermal (builder entries; performance canonical in 09-power-thermal.md) (10)

All §4.6 entries are material class **ELEC** (§3.13). "Depl. area" = deployed face area in m², feeding the §3.12 drag model (— = not a deployable; negligible beyond the frontal-area default).

| ID | Name | Tier | Size | Mass (t) | Output | Depl. area (m²) | Cost | Anchor |
|---|---|---|---|---|---|---|---|---|
| PW-SA-R | Rigid solar wing | T0 | 1×4 stowed | 0.16 | 5 kWe @1 AU BOL (≈31 W/kg) | 60 (≈80 W/m²) | 0.8 | ISS legacy wings |
| PW-SA-RO | Roll-out array | T0 | 1×3 stowed | 0.25 | 20 kWe @1 AU (80 W/kg) | 100 (≈200 W/m²) | 2 | ROSA / iROSA |
| PW-BAT | Battery bank | T0 | 1×1 | 0.20 | 40 kWh (200 Wh/kg) | — | 0.5 | Li-ion pack, 2040s |
| PW-FC | Fuel cell | T0 | 1×1 | 0.12 | 7 kWe cont. (Hydrogen+Oxygen→Water) | — | 1 | Shuttle PC17C |
| PW-RTG | RTG | T0 | 1×1 | 0.045 | 0.11 kWe (Pu238) | — | 15 | MMRTG |
| PW-KP1 | Fission unit 1 kWe | T1 | 1×2 | 0.40 | 1 kWe (Uranium) | — | 20 | Kilopower/KRUSTY |
| PW-KP10 | Fission unit 10 kWe | T2 | 2×3 | 1.5 | 10 kWe | — | 60 | Kilopower 10 kWe design |
| PW-FSP | Surface fission 100 kWe | T2 | 3×4 | 9.0 | 100 kWe | — | 150 | NASA Fission Surface Power studies |
| PW-NEP | NEP reactor 2 MWe | T3 | 5×8 | 40 | 2,000 kWe (20 kg/kWe incl. conversion + radiators; optimistic end of the 20-40 kg/kWe MW-class study range) | ≈1,200 (integral radiator wings) | 600 | MW-class NEP concept studies (NASA human-Mars NEP / Copernicus-class; Prometheus/JIMO was ~200 kWe) |
| TH-RAD | Deployable radiator | T0 | 1×3 stowed | 1.2 | rejects 50 kWt @ 500 K | 8 (two-sided panel) | 1.5 | ISS HRS-derived; 09 owns curve |

### 4.7 Habitat modules (12)

All §4.7 entries are material class **HAB** (§3.13). "Crew sleeps" = permanent berths; §3.11 defines how sleeps and volume jointly gate boarding.

| ID | Name | Tier | Size | Mass (t) | V_press (m³) | Crew sleeps | Cost | Anchor |
|---|---|---|---|---|---|---|---|---|
| HB-CAP2 | 2-crew capsule | T0 | 2×3 | 4.2 | 9 | 2 (≤7 d) | 25 | Gemini (3.85 t) + modern materials; integral heat shield (q̇_max 10 MW/m², 0.20 t ablator, §3.15) & chutes (deploy q ≤ 20 kPa, a ≤ 7 g; UT-CHUTE scaling rule, §4.9) |
| HB-CAP4 | 4-crew capsule | T0 | 3×4 | 9.5 | 20 | 4 (≤30 d) | 60 | Crew Dragon class; integral heat shield (q̇_max 10 MW/m², 0.35 t ablator, §3.15) & chutes (deploy q ≤ 20 kPa, a ≤ 7 g; UT-CHUTE scaling rule, §4.9) |
| HB-RIG-S | Rigid module S | T0 | 3×5 | 9.0 | 60 | 2 | 70 | ISS-module density ≈0.14 t/m³ |
| HB-RIG-L | Rigid lab/hab module | T0 | 4×9 | 14.5 | 106 | 4 | 120 | ISS Destiny |
| HB-INF-S | Inflatable module S | T0 | 2×2 (3×4 deployed) | 1.4 | 16 | 0 (storage) | 8 | BEAM (flown) |
| HB-INF-M | Inflatable hab M | T1 | 3×5 (8×11 deployed) | 13.2 | 340 | 6 (+6 short-duration surge, §3.11) | 80 | TransHab (6-crew design; shell + basic outfitting) |
| HB-INF-L | Inflatable hab L (outfitted) | T1 | 4×6 (8×11 deployed) | 20.0 | 330 | 6 (+6 short-duration surge, §3.11) | 150 | B330 (nominal 6 crew; incl. integral ECLSS; 08) |
| HB-CUP | Cupola | T0 | 2×1 | 1.9 | 3 | 0; +morale | 15 | ISS Cupola 1.8 t |
| HB-AIR | Airlock | T0 | 2×3 | 6.1 | 34 | 0; 2-person EVA | 30 | ISS Quest |
| HB-LAB | Science lab | T1 | 4×9 | 12.0 | 100 | 0; research slots (11) | 100 | Destiny-derived |
| HB-GRN | Greenhouse module | T3 | 4×9 (inflatable) | 16.0 | 280 | 0; 200 m² grow area (08) | 90 | bioregenerative LSS studies (BIOS-3, NASA) |
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

### 4.9 Cargo, utility, entry & landing (19)

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
| UT-HS3 | Heat shield 3.7 m | T0 | 3×1 | 0.5 | 2 | SHIELD | ablative, ≈45 kg/m² incl. carrier; q̇_max 10 MW/m², ablator 0.30 t, protects the 3-wide column behind it (§3.15); bottom face = TPS, no attach node | PICA-X |
| UT-HS5 | Heat shield 5 m | T1 | 4×1 | 0.9 | 4 | SHIELD | as UT-HS3 at 4-wide: q̇_max 10 MW/m², ablator 0.55 t, protects the 4-wide column (§3.15) | — |
| UT-CHUTE | Parachute cluster | T0 | 1×1 | 0.24 | 0.5 | MECH | recovers 6 t at ≤ 8 m/s (Earth SL); scaling `v_td = 8 m/s · sqrt(m / 6 t) · sqrt(ρ_Earth,SL / ρ_local)`; deploy limits q ≤ 20 kPa, a ≤ 7 g (exceed = chute destroyed); mass rule ≈ 4% of recovered | Apollo ELS ≈ 250 kg / 5.8 t |
| ST-LL | Landing leg | T0 | 1×2 | 0.15 | 0.4 | MECH | 8 t per leg @ ≤3 m/s touchdown | — |
| ST-LLH | Heavy landing leg | T1 | 1×3 | 0.6 | 1 | MECH | 40 t per leg @ ≤3 m/s | F9 leg class |
| AR-SHELL | Entry aeroshell 5 m | T2 | 4×2 | 2.5 | 8 | SHIELD | PICA-class TPS + backshell; q̇_max 10 MW/m², ablator 0.90 t, protects the 4-wide column behind it (§3.15); jettisonable (SEPARATE event); no bottom attach node | HAVOC entry vehicle / MSL aeroshell class |
| AR-CHUTE | Supersonic extraction chute | T2 | 1×1 | 0.6 | 1.5 | MECH | deploys ≤ Mach 2.2 and q ≤ 4 kPa; extracts ≤ 10 t payload from an aeroshell; single-use | MSL/HAVOC disk-gap-band chute |
| AR-ENV | Aerostat envelope kit | T2 | 2×3 stowed | 1.3 | 6 | HAB | ≈2,500 m² Vectran/PTFE laminate; 11,700 m³ inflated; lift math per §4.11(d); DEPLOY event (blocked while stowed in bay/fairing, §8.15) | HAVOC envelope |
| AR-GON | Aerostat gondola | T2 | 2×2 | 4.6 | 25 | ELEC | command source; 2 kWe solar, relay comms, atmosphere-ISRU sampler (07 operates) | HAVOC gondola |
| AR-INF | Aerostat inflation hardware | T2 | 1×2 | 0.7 | 3 | MECH | inflates AR-ENV during parachute descent (≈20 min); feeds from any connected Hydrogen tank | HAVOC mid-air inflation system |

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

#### (a) "Anvil-1" — T0 two-stage methalox launcher (2 t to LEO, uncrewed)

Built entirely from integer catalog parts; the design's acceleration limiter is set to **5 g** (player-selected, below the 6 g uncrewed default — see the joint check below for why).

| Item | Mass (t) |
|---|---|
| Payload | 2.00 |
| **Stage 2**: 1× TK-ML-M + 1× TK-ML-S (16.5 t prop; dry 0.72 + 0.27) | 17.49 |
| EN-M1V engine | 0.40 |
| UT-AV + structure | 0.30 |
| **Stage 2 total (m0₂, incl. payload)** | **20.19** |
| ST-FR3 fairing (jettisoned with stage 1) | 0.90 |
| ST-IS3 interstage + ST-DC3 decoupler (0.40 + 0.12) | 0.52 |
| **Stage 1**: 2× TK-ML-L (70 t prop; dry 4.2) | 74.20 |
| 2× EN-M0 | 1.80 |
| Structure, ST-FIN ×2, avionics | 1.50 |
| **Liftoff mass (m0₁)** | **99.11** |

- Stage 2: m0 = 20.19 t, m1 = 3.69 t → dv = 360 × 9.80665 × ln(20.19/3.69) = 3,530 × 1.700 = **6,000 m/s**. TWR(ignition, Earth) = 120/(20.19×9.80665) = 0.61. Burn 485 s (ṁ = 34.0 kg/s).
- Stage 1: m0 = 99.11 t, m1 = 29.11 t. Trajectory-avg Isp 320 s (bounds: 3,580 m/s at SL 298 s; 4,181 m/s at vac 348 s) → dv = 320 × 9.80665 × ln(99.11/29.11) = 3,138 × 1.225 = **3,845 m/s**. Liftoff TWR = 1,600/(99.11×9.80665) = **1.65**. Burn 128 s (ṁ = 547 kg/s, from either consistent F/Isp pair — §3.4).
- **Total ideal dv = 9,845 m/s ≥ 9,400 m/s LEO requirement** (01-orbital-mechanics.md) → ~445 m/s designer margin. Payload fraction 2.0% (typical for a small launcher).
- Joint check (§3.8a, evaluated at the selected 5 g limiter): m_above the interstage = 20.19 + 0.90 + 0.52 = 21.61 t. Unclamped stage-1 burnout acceleration would be 1,868/29.11 = 64.2 m/s² (6.5 g), so the limiter clamps a at 49.03 m/s² → L = 21.61 × 49.03 = **1,060 kN ≤ 1,200 kN PASS** (12% margin). At the 6 g uncrewed default the joint would see 1,272 kN → E6, which is exactly why this design selects 5 g (the gravity-loss cost of the lower clamp is negligible — it engages only in the final seconds). On-pad: 21.61 × 9.80665 = 212 kN PASS. Engine mounts: EN-M0 stack node rated max(1,200, 1.25×934) = 1,200 kN ≥ per-engine peak thrust 934 kN — pass by construction (§3.8a). Stage-2 burnout is 120/3.69 = 32.5 m/s² (3.3 g), under the limiter, all stage-2 joints trivially pass. Hardware cost ≈ $16M + propellant.

#### (b) "Charon" — T2 NTR Mars transfer vehicle (orbital-assembled)

| Item | Mass (t) |
|---|---|
| 3× EN-NTR-S (111 kN, Isp 900 s, shadow shields) | 10.2 |
| 3× TK-LH2-L (60 t Hydrogen; tanks 15% = 9.0) | 69.0 |
| ST-KEEL truss | 9.0 |
| PW-KP10 (ZBO power 5 kWe + ship bus) | 1.5 |
| TH-RAD | 1.2 |
| UT-AV, dishes | 0.5 |
| DK-L berth (payload) | 1.2 |
| **Payload**: HB-INF-M hab 13.2 + consumables 6.0 (08) + HB-CAP2 return capsule 4.2 + storm-shelter Water 5.0 + science 1.6 | 30.0 |
| **m0** | **122.6** |

- m1 = 122.6 − 60 = 62.6 t → **dv = 900 × 9.80665 × ln(122.6/62.6) = 8,826 × 0.6722 = 5,933 m/s**.
- TWR in LEO = 333/(122.6×9.80665) = 0.28 → TMI split into 3 periapsis burns (§3.5; TMI burn time ≈ 18.3 min at ṁ = 37.7 kg/s; the full 60 t load would take 26.5 min).
- Mission ledger (01-orbital-mechanics.md budgets): TMI 3,650 m/s burns 41.5 t H2 → 81.1 t; Mars capture to 1-sol elliptic 1,100 m/s burns 9.5 t → 71.6 t; **reserve 9.0 t ≈ 1,180 m/s** for trans-Earth injection after a Phobos/ISRU LH2 top-up, or as partial cover toward an outbound abort.
- Berth load at burnout: a = 333/62.6 = 5.32 m/s²; 30 t payload → 160 kN ≤ 800 kN (DK-L) PASS.

#### (c) "Packmule" — Hall-thruster cargo tug (LEO → low lunar orbit)

| Item | Mass (t) |
|---|---|
| 4× EN-HALL (AEPS strings: 50 kWe rated, 2.356 N total) | 0.32 |
| 3× PW-SA-RO roll-out arrays: 60 kWe @1 AU (20% power margin; deployed area 300 m²) | 0.75 |
| 1× TK-XE-L (4.0 t Xenon; 0.24 dry) | 4.24 |
| Structure 0.45, UT-AV 0.15, DK-B 0.25, radiator stub 0.15 (09 small class) | 1.00 |
| **Payload (container rack)** | 8.00 |
| **m0** | **14.31** |

- m1 = 10.31 t → **dv = 2,800 × 9.80665 × ln(14.31/10.31) = 27,459 × 0.32784 = 9,002 m/s** — covers the ≈8,000 m/s low-thrust LEO→LLO spiral (01-orbital-mechanics.md) with ~1,000 m/s margin.
- Acceleration 1.65×10⁻⁴ m/s²; ṁ = 2.356/(2,800×9.80665) = 8.58×10⁻⁵ kg/s; thrust-on time 4.66×10⁷ s ≈ **540 days** (this is the honest physics of 50 kWe; time warp and uncrewed patience are the gameplay answer — crewed transfers use chemical/NTR).
- At Mars distance (1.52 AU) arrays deliver 60/1.52² = 26.0 kWe → thrust drops to 26.0/50 = **~52% of rated** (the §3.4 rule divides available power by *rated thruster power*, here 50 kWe — not by array output at 1 AU); the editor's transfer planner shows power-limited thrust along the trajectory.

#### (d) "Cyclops" — Venus aerostat deployment ship (T2, HAVOC-class robotic)

Deploys a robotic aerostat at 55 km in Venus's atmosphere (07-bases-habitats.md operates it).

| Item | Mass (t) |
|---|---|
| **Entry assembly (payload, §4.9 aerostat parts)**: AR-SHELL 2.5; AR-CHUTE 0.6; AR-ENV 1.3; AR-GON 4.6; TK-LH2-M 0.60 dry, part-filled with 0.5 Hydrogen lifting gas; AR-INF 0.7; mass margin 1.2 | 12.00 |
| Carrier bus (UT-AV, PW-SA-RO, UT-DISH-M, RCS-HYP + Hypergols) | 1.50 |
| **Departure stage**: EN-H1 (RL10B-2, O/F 6.0) 0.30; propellant 28.0 = 24.0 Oxygen in 3× TK-LOX-M + 4.0 Hydrogen in 1× TK-LH2-M (tank dry 3×0.40 + 0.60 = 1.80, per §4.2 fractions); structure 0.80; avionics 0.20 | 31.10 |
| **m0 (assembled in LEO)** | **44.60** |

- m1 = 16.60 t → **dv = 465.5 × 9.80665 × ln(44.60/16.60) = 4,565 × 0.9883 = 4,512 m/s**; trans-Venus injection from LEO needs ≈3,500 m/s (01) → ~1,012 m/s for midcourse + carrier divert to relay flyby. TWR 0.25 (two perigee burns, 1,162 s total at ṁ = 24.1 kg/s). The hydrolox engine draws 6 kg Oxygen per kg Hydrogen across the four separate tanks per the §3.7 drain rule; ZBO power for the LH2 tanks comes from the carrier's PW-SA-RO. Peak proper acceleration 110/16.6 = 6.6 m/s² (0.68 g) — joint loads trivial (the payload stack joint sees 13.5 t × 6.63 = 90 kN).
- Buoyancy check at 55 km (ρ ≈ 0.9 kg/m³, T ≈ 300 K, p ≈ 0.5 atm — 03-solar-system.md): envelope volume 11,700 m³ of Hydrogen → net lift = 11,700 × 0.9 × (1 − 2.016/43.45) ≈ **10,050 kg** vs. floated mass 8.9 t (12.0 minus jettisoned AR-SHELL 2.5 and AR-CHUTE 0.6) → buoyancy margin 13%. (Design note surfaced in-game: in CO2, breathable air lifts 0.30 kg/m³ — crewed aerostats at T3 keep their habitat *inside* the envelope, per HAVOC.)

## 5. Player Interaction & UI

- **Drydock screen** (vector/schematic art): grid canvas; part palette filtered by category/tier; mirror-symmetry toggle (x-axis); sub-assembly save/load; blueprint export (JSON, shareable).
- **Live readout panel** (always visible, recomputed per edit, all from §3 formulas): wet/dry mass; per-stage dv (with SL/vac/trajectory-avg toggle and g_ref selector), TWR at ignition/burnout, burn time; COM markers (wet/dry) + thrust-line overlay with GREEN/YELLOW/RED stability badge and engine-out badge; part count /600; cost total; crew capacity vs. sleeps; pressurized volume; power balance preview (generation vs. draw, at selected solar distance — 09); radiator margin (09); MMOD coverage % and P_pen/yr at selected orbit; q_max worst part; spin section: rpm slider with live a_spin, comfort verdict, balance offset.
- **Validation list** with stable codes (clicking zooms to the offender): E1 no command source; E2 disconnected parts; E3 invalid decoupler; E4 overlapping footprints; E5 plume impingement; E6 joint overload at the design-selected limiter accel (§3.8a); E7 q_max exceeded in pre-flight ascent sim; E8 port size mismatch; E9 crewed spin > 6 rpm; E10 negative dry mass from cargo-manifest misconfiguration; E11 q̇_max exceeded in pre-flight entry sim (§3.15); W1 liftoff TWR < 1.3; W2 no airlock with crew; W3 no storm shelter beyond LEO (§3.11 shelter rule); W4 solid above liquid stage; W5 dv below mission planner target; W6 spin imbalance > 0.02·r; W7 uncovered hull in high-flux orbit; W8 insufficient docking ports for crew logistics; W9 crossfeed duct flow cap throttles engines (§3.7).
- **Pre-flight ascent sim**: one-click 2D ascent integration (same code path as flight, 13-architecture.md) plotting q, q·α, accel, and throttle vs. time with limit lines.
- **Station view**: docking topology graph overlay; per-port load/rating; station-keeping dv/yr forecast; spin-up/spin-down buttons with propellant quote (§3.10 formula).
- Engineer-founder fantasy: every readout has a "show the math" hover expanding the formula with the current numbers plugged in.

## 6. Progression Hooks

| Tier | Act | Unlocks (this document) |
|---|---|---|
| T0 (2049 baseline) | Act 1 | Full chemical engine line (EN-K1/K1V/M0/M1V/M2/M2V/H1, EN-HYP, solids, all RCS), basic tanks, PAD-1/2, fairings, capsules, rigid modules, BEAM-class inflatable, IDSS/CBM ports, basic Whipple, NEXT-C ion & AEPS Hall strings (smallsat-scale EP), legacy + ROSA arrays |
| T1 | Acts 1-2 | PAD-3, EN-H2 reusable hydrolox, ZBO LH2 tanks, TK-DEPOT cryo depot, FD-1 crossfeed, DK-L fluid berth, DK-ARM orbital assembly, TransHab/B330-class inflatables, stuffed Whipple, storm shelter, Kilopower-1 |
| T2 | Acts 2-4 | EN-NTR-S/L, LH2-L tanks, SP-HUB/ARM/TETHER/HAB spin sections, Kilopower-10 / FSP-100, Argon Hall, Dry Dock module (assemble beyond fairing limits), ISRU printing of STRUCT/TANK/MECH/SHIELD (BasaltFiber & IronSteel variants), HAVOC-class aerostat deployment hardware (AR-SHELL/AR-CHUTE/AR-ENV/AR-GON/AR-INF, §4.9) |
| T3 | Acts 4-5 | X3-class Hall clusters, VASIMR, MPD, NEP 2 MWe, bimodal NTR, SP-RING 1 g ring segments, greenhouse modules, orbital ENGINE/HAB/ELEC printing |
| T4 [SPECULATIVE] | Act 5 / Endgame | EN-FT fusion torch, He3-augmented variants, interstellar-precursor bus structures, reactor printing |

Act gating in practice: Act 1 is launcher design under pad/fairing/budget constraints; Act 2 adds orbital assembly and depots (Moon); Act 3 is the NTR + ISRU-printing inflection (Mars builds get cheap); Act 4 is spin-gravity stations and aerostats; Act 5 is MW-class electric ships; Endgame is the fusion torch and self-sufficient off-Earth shipyards (no Earth imports in any recipe).

## 7. Cross-System Interfaces

**Consumes:**
- 01-orbital-mechanics.md: mission dv targets for the planner (LEO 9,400; TMI 3,650; Venus TVI 3,500; LEO→LLO low-thrust ≈8,000 m/s); low-TWR burn-splitting rule; ascent guidance (α profile); lunar station-keeping budgets.
- 02-propulsion.md: authoritative engine performance curves, throttle ranges, ullage/restart rules, boiloff rates; this doc's engine tables must match 02's master list.
- 03-solar-system.md: atmosphere ρ(h) profiles (max-Q, drag, aerostat deployment), MMOD flux Φ by region, body g and radiation environments.
- 04-resources-isru.md: canonical resource properties/densities; the Hypergols extension decision (Q1).
- 05-industry-logistics.md: fabrication rates, machine-shop/printer buildings, standard container spec (CG-CON mounts it), propellant transfer rates, launch logistics.
- 08-life-support-crew.md: crew mass (100 kg w/ suit), consumable rates, habitable-volume morale curve, radiation dose model, spin-adaptation effects.
- 09-power-thermal.md: array/reactor/radiator performance (parts §4.6 are builder stubs of 09's systems), ZBO power draws.
- 10-vehicles.md: construction drones (orbital assembly), landers/rovers reuse this part system and builder math.
- 11-research-tech.md: tier unlock placement of every part.
- 12-gameplay-economy-ui.md: prices, commercial launch market, contracts, event system (MMOD conjunctions, part reliability rolls).
- 13-architecture.md: physics body merging on dock, 600-part cap rationale, ascent-sim code path, blueprint serialization.

**Provides:**
- To 01/02: vessel mass properties (m, COM, I), thrust/torque tables, per-stage dv — the flight model's inputs.
- To 01: the per-part Cd·A drag table (frontal-area default §3.12, deployed areas §4.6/§4.9; Cd = 2.2 default) for ascent and orbital drag integration, plus entry-vehicle stats — shield diameter, q̇_max, ablator budget, protected column (§3.15). 01 owns the entry/aerocapture trajectory integration; this doc owns what heating does to parts.
- To 05: part material classes + masses (manufacturing demand), depot/berth fluid-transfer interfaces.
- To 07: station modules, spin sections, aerostat deployment hardware (07 owns surface/atmosphere base operation; the boundary is "if it can free-fly, it's mine").
- To 08: pressurized volumes, crew capacities, shelter shielding mass per module.
- To 09: per-part power draws and radiator mounts; reactor placement rules (shadow-shield cone covers parts within ±10° aft).
- To 11: research-able part list with tiers.
- To 12: cost ledger per design; failure-event hooks.
- To 13: the complete builder data model (grid, graph, stages) and validation rule list (E1-E11, W1-W9).

## 8. Failure Modes & Edge Cases

1. **Joint overload** (§3.8a violated in flight, e.g. player overrides the g-limiter): joint breaks; vessel splits into two physics bodies; downstream parts uncontrolled. Deterministic, no RNG.
2. **Max-Q part loss**: exposed part exceeding q_max is destroyed; if it was structural, cascades to joint check.
3. **q·α stack break**: snap at the highest-load joint; the dramatic "rocket folds at max Q" failure for hand-flown pitch-overs.
4. **Engine-out**: baseline ignition-failure and burn-failure probabilities owned by 12 (T0 baseline 0.5%/ignition, halves each tier); the §3.3 engine-out badge tells the player at design time whether it's survivable.
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

1. **Hypergols as a resource extension.** RCS and storable apogee engines need MMH/NTO. Proposal: single paired commodity `Hypergols` (fixed 1.6:1 NTO:MMH), Earth-sourced at T0, ISRU-producible from Ammonia + Water electrolysis chains at T3. Needs sign-off from 04-resources-isru.md (it extends the canonical resource list).
2. **Kerolox representation.** RP-1 is not a canonical resource. Current design: kerolox tanks are sealed Earth-fill-only units (no ISRU path, engines retired by mid-game). Alternative: model RP-1 as a `Polymers`-class refined product. Decision with 04.
3. **NTR overflight policy.** Real NTR exhaust is clean hydrogen, but ground launch of an operating reactor is politically forbidden; we currently hard-ban NTR thrust on Earth wherever ambient pressure exceeds 50 kPa (i.e., below ~5.5 km altitude); high-altitude and vacuum operation is permitted. Mars has a thin atmosphere — allow NTR landers there? Needs 12 (politics/events) input.
4. **Propellant-shift COM realism.** We freeze propellant at tank centroids (§3.2). Is the resulting error acceptable for long LH2 stages (real COM moves meters as tanks drain)? Option: linear COM interpolation per tank between full/empty centroids — cheap, worth it?
5. **Stuffed-Whipple ISRU parity.** WS-BF at η = 0.97 vs imported 0.98 — is a 1-point difference worth the UI complexity, or should they be identical?
6. **Spin-section rendering.** 2D side view of a rotating ring is visually ambiguous; current plan is a schematic "ring inset" panel. Needs UI prototype (12/13).
7. **Reliability model granularity.** Per-ignition engine failure (12) vs. per-part wear with maintenance hours (05/08 crew tasks)? Affects how much spare-parts logistics matter.
8. **Aerostat hand-off boundary.** This doc delivers the aerostat to float-positive at 55 km; 07-bases-habitats.md takes over. The deployment hardware is statted here (§4.9 AR-SHELL/AR-CHUTE/AR-ENV/AR-GON/AR-INF); confirm 07 does not want the envelope/gondola entries migrated to its own catalog (if migrated, §4.9 keeps AR-SHELL/AR-CHUTE and Build D references 07's IDs).
