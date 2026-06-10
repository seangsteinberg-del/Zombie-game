# 01 — Orbital Mechanics & Flight

Status: design-complete draft for review · Owner: Orbital Mechanics & Flight domain
Sibling docs: 02-propulsion.md, 03-solar-system.md, 04-resources-isru.md, 05-industry-logistics.md, 06-ships-stations.md, 07-bases-habitats.md, 08-life-support-crew.md, 09-power-thermal.md, 10-vehicles.md, 11-research-tech.md, 12-gameplay-economy-ui.md, 13-architecture.md

---

## 1. Overview

This document is the single source of truth for how things move in PROJECT APHELION: orbits, transfers, launches, reentries, rendezvous, flybys, and the time-warp machinery that makes a real-scale solar system playable. It also contains **THE CANONICAL DELTA-V MAP** (Section 4.2) that every sibling document must cite instead of inventing its own numbers.

Core commitments (locked by project charter, not relitigated here):

- **Real scale, real delta-v.** 1 AU = 149,600,000 km in-game. Reaching a 300 km LEO costs ~9,400 m/s off the pad. Tedium is defeated by time warp (up to 1,000,000x), never by shrinking the universe.
- **2D planar patched conics.** All bodies and craft live in a single ecliptic plane. While coasting, craft are "on rails" on analytic Kepler conics (exact, drift-free, warp-safe). Numerical integration runs only under thrust or inside an atmosphere.
- **Honesty about the 2D cut.** Inclination, plane changes, and polar orbits do not exist in this game. Section 3.14 lists exactly what that drops and the design compensations. We do not add fake delta-v taxes to "make up" for missing plane changes.
- **Implementability.** Section 3 is written so a programmer can build the flight model from this document alone: every rule has a formula with SI units. The recommended Kepler solver is the universal-variable formulation (one code path for ellipse/parabola/hyperbola).

What this document does NOT own: engine performance (02-propulsion.md), body physical/orbital constants beyond what is needed here (03-solar-system.md is canonical for ephemerides), ship mass/drag properties (06-ships-stations.md), and the economic meaning of a launch window (12-gameplay-economy-ui.md).

---

## 2. Real-World Grounding

Every mechanic below is anchored to flown practice or standard astrodynamics literature:

- **Patched conics & sphere of influence.** The Laplace sphere of influence, r_SOI = a·(m/M)^(2/5), and patched-conic mission design are the method used for Apollo-era trajectory planning and still taught as the first-order tool (Bate, Mueller & White, *Fundamentals of Astrodynamics*; Vallado, *Fundamentals of Astrodynamics and Applications*; Curtis, *Orbital Mechanics for Engineering Students*). Typical patched-conic errors vs. full n-body are a few percent in delta-v — acceptable for a game that charges real prices.
- **Universal-variable Kepler propagation.** The χ/Stumpff-function formulation (BMW ch. 4; Vallado ch. 2) solves time-of-flight for all conic types with one Newton iteration loop; it is the standard robust propagator and is what we specify.
- **Delta-v map values.** All values in Section 4.2 are computed from vis-viva/Hohmann with published μ values (JPL/NASA planetary fact sheets) and cross-checked against community-standard solar-system delta-v maps and flown missions (Apollo TLI ≈ 3.1 km/s from LEO; Mars injection ≈ 3.6 km/s; MAVEN Mars orbit insertion ≈ 1.2 km/s into ellipse).
- **Launch losses.** Real launchers spend ~1.3–1.7 km/s on gravity, drag, and steering losses on top of the ~7.7 km/s orbital speed (Saturn V gravity loss ≈ 1.5 km/s; typical drag loss 40–150 m/s). Total surface→LEO ≈ 9.3–9.5 km/s is the accepted figure.
- **Atmosphere models.** Earth: US Standard Atmosphere 1976. Mars: Viking/Mars Climate Database-class profiles. Venus: Venus International Reference Atmosphere (VIRA). Titan: Huygens HASI descent data. Gas giants: NASA fact-sheet scale heights (Jupiter 27 km, Saturn 59.5 km at the 1-bar datum).
- **Entry heating.** Sutton–Graves stagnation-point convective heating (k_Earth = 1.7415e-4 SI), validated here against Stardust (12.9 km/s, ~1,200 W/cm² peak — the fastest Earth reentry ever flown) and Apollo lunar return (~11 km/s, ~400–500 W/cm²). Ballistic-entry peak deceleration uses the classic Allen–Eggers result.
- **Heat shields.** Shuttle HRSI tiles (reusable, ~1,260 °C surface limit), Apollo AVCOAT ablator, Stardust/Mars-2020 PICA, Galileo-probe carbon phenolic (survived heat fluxes in the tens of kW/cm² and ~230 g peak deceleration entering Jupiter).
- **Aerobraking / aerocapture.** Aerobraking is flown technology (Magellan 1993, Mars Global Surveyor 1997–99, MAVEN). Aerocapture has never been flown but is engineering-complete per NASA aerocapture systems analysis studies (2002–2016, covering Mars, Venus, Titan, and Neptune — incl. Titan Explorer) — hence a T2 unlock. Jupiter/Saturn aerocapture was NOT covered by those studies and is excluded from the game model (3.11).
- **Rendezvous & docking.** Gemini/Apollo phasing techniques; ISS approach gates and ~0.1 m/s contact velocities; Soyuz/Progress Kurs automated docking (operational since the 1980s) anchors the autodock program.
- **Low-thrust spirals.** Edelbaum's 1961 result: coplanar circular-to-circular low-thrust transfer costs Δv = |v_c1 − v_c2|, and low-thrust escape from a circular orbit costs ≈ v_c. Anchors: SMART-1, Dawn, ion-propelled GEO stationkeeping.
- **Lagrange-point reality check.** Patched conics cannot produce Lagrange points (they are a three-body phenomenon). Real L4/L5 are dynamically stable (Jupiter trojans persist for Gyr); Sun–Earth L1/L2 are unstable, with flown stationkeeping budgets of 2–4 m/s/yr (SOHO ≈ 2.4 m/s/yr, JWST ≤ 4 m/s/yr). Our anchor-slot model (3.13) encodes these facts.

---

## 3. Game Model

### 3.1 Frames, epoch, units, state

- Epoch t = 0 is **2049-01-01 00:00 UTC**. Simulation time `t` is float64 seconds from epoch. 03-solar-system.md supplies all body elements at this epoch.
- The world is a tree of **SOI frames**: Sun (root) → planets → moons. Each craft/body state is stored **body-centric** in its current SOI frame, never in global coordinates (precision rule, see 8.4).
- A 2D state is `(x, y, vx, vy)` float64, meters and m/s, in a non-rotating frame whose +x axis is the shared reference direction (the J2000 vernal-equinox direction projected to the plane). Angles are radians, counterclockwise positive. Both prograde (CCW) and retrograde (CW) orbits exist; sign convention below.
- SI units everywhere in code: m, m/s, kg, N, W, Pa, K. UI may display km, t, kN, kPa per project conventions.

### 3.2 2D Keplerian elements

Element set per on-rails object: `(μ_frame, a, e, ϖ, τ, s)`:

| Symbol | Meaning | Units |
|---|---|---|
| μ_frame | Gravitational parameter of SOI body | m³/s² |
| a | Semi-major axis (negative for hyperbolic; store α = 1/a to handle near-parabolic) | m |
| e | Eccentricity ≥ 0 | — |
| ϖ | Longitude of periapsis (angle of periapsis direction from +x) | rad |
| τ | Time of periapsis passage | s |
| s | Rotation sense: +1 prograde (CCW), −1 retrograde (CW) | — |

Conversions (standard, 2D-specialized):

```
p   = a(1 − e²)                      (semi-latus rectum, m)
h   = s·sqrt(μ p)                    (signed specific angular momentum, m²/s; h = x·vy − y·vx)
r(ν)= p / (1 + e cos ν)              (ν = true anomaly)
θ   = ϖ + s·ν                        (position angle of craft from +x axis)
v_r = (μ/|h|) e sin ν                (radial speed)
v_t = (μ/|h|)(1 + e cos ν)           (transverse speed, in direction s·(θ + 90°))
vis-viva:  v² = μ (2/r − 1/a)
energy:    ε = v²/2 − μ/r = −μ/(2a)
period:    T = 2π sqrt(a³/μ)         (elliptic only)
```

State → elements: `ε → a`; `e_vec = ((v²−μ/r)·r_vec − (r_vec·v_vec)·v_vec)/μ → e, ϖ`; `s = sign(x·vy − y·vx)`; τ from current anomaly. Elements → state via Kepler solve (3.3). Degenerate radial orbits (h = 0) are clamped to e = 0.999999 or 1.000001 (8.6).

### 3.3 Kepler propagation — universal variables (mandatory)

One propagator handles all conics. Given `r0_vec, v0_vec, Δt, μ`, find `r_vec, v_vec`:

```
r0 = |r0_vec|;  vr0 = (r0_vec·v0_vec)/r0
α  = 2/r0 − v0²/μ            # = 1/a; >0 ellipse, ≈0 parabola, <0 hyperbola

Stumpff functions of z = α χ²:
  C(z) = (1 − cos√z)/z            z > 0
       = (cosh√(−z) − 1)/(−z)     z < 0
       = 1/2 − z/24 + z²/720 …    |z| < 1e-6  (series, avoids cancellation)
  S(z) = (√z − sin√z)/√(z³)       z > 0
       = (sinh√(−z) − √(−z))/√((−z)³)  z < 0
       = 1/6 − z/120 + z²/5040 …  |z| < 1e-6

Initial guess:
  elliptic:   χ = √μ · α · Δt
  hyperbolic: χ = sign(Δt)·√(−a)·ln( −2μαΔt / (r0_vec·v0_vec + sign(Δt)·√(−μa)(1 − r0 α)) )
  parabolic:  Barker-equation seed (Vallado Alg. 8)

Newton iteration on F(χ) = (r0 vr0/√μ) χ² C + (1 − α r0) χ³ S + r0 χ − √μ Δt:
  F'(χ) = (r0 vr0/√μ) χ (1 − z S) + (1 − α r0) χ² C + r0
  χ ← χ − F/F'
  converge when |F/√μ| < 1e-8 s; max 100 iterations; on failure fall back to
  bisection on F (F is monotonic in χ) — guaranteed convergence.

Lagrange f and g:
  f  = 1 − (χ²/r0) C        g  = Δt − (χ³/√μ) S
  r_vec = f·r0_vec + g·v0_vec ;  r = |r_vec|
  fdot = (√μ/(r r0)) χ (z S − 1)   gdot = 1 − (χ²/r) C
  v_vec = fdot·r0_vec + gdot·v0_vec
```

This is exact to float64 for any Δt — it is what makes 1,000,000x warp free of integration error. Bodies themselves are propagated the same way from their 03-solar-system.md elements (planets/moons are on rails forever; their orbits never change).

### 3.4 Spheres of influence

```
r_SOI = a_body · (m_body / M_parent)^(2/5)        [Laplace SOI; a = body's orbit semi-major axis]
```

Computed canonical values are in Table 4.1. Rules:

- **SOI floor rule:** if `r_SOI < 1.5 × R_body` (mean radius), the body gets **no SOI** and exerts no gravity; it is a "rendezvous object" — you dock with its surface (applies to Phobos, Deimos; their gravity, ~6 mm/s² on Phobos, is below gameplay relevance). Landing = velocity match + contact at < 2 m/s.
- **Transition:** when a craft's distance from a body crosses that body's r_SOI, re-express the state in the new frame by subtracting/adding the body's position and velocity at the crossing instant, then refit elements. Energy is not exactly conserved across the patch — that is inherent to patched conics; accept it (errors ≲ 1–2 % of leg Δv).
- **Hysteresis:** to prevent thrashing at the boundary (8.2), exit requires r > 1.01·r_SOI and entry requires r < 0.99·r_SOI.
- **Detection on rails:** find crossings analytically before they happen — coarse-sample candidate intervals. For bound craft (e < 1): step = min(T_craft, T_body)/64. For unbound craft (e ≥ 1, i.e. α ≤ 0 — every escape trajectory and every arrival hyperbola; T_craft does not exist): step = min(T_body, t_exit)/64, where t_exit is the universal-Kepler time of flight from the current state to r = r_SOI of the current frame (or to 2× the current radius if already outbound past periapsis). Then refine the root of `|r_craft(t) − r_body(t)| − r_SOI = 0` with Brent's method to ±1 s. All predicted crossings go into the **event queue** (used by warp guards, 3.6).

### 3.5 Flight regimes

| Regime | Condition | Propagation |
|---|---|---|
| On rails | No thrust, outside atmosphere, not landed | Analytic universal-Kepler (3.3). Exact at any warp. |
| Powered flight | Engine thrust ≠ 0 or RCS translating | Numerical integration, RK4 |
| Atmospheric flight | Altitude < atmosphere interface (Table 4.4) | Numerical integration, RK4, drag+lift+gravity+thrust |
| Landed | Contact with surface, v_rel ≈ 0 | State = (body, surface longitude angle); position follows body rotation analytically |

Integrator spec (binding for 13-architecture.md): fixed-timestep **RK4 at dt = 0.02 s** (50 Hz) at 1x for powered/atmospheric flight; gravity term uses only the current SOI body (patched conics, no n-body). Trajectory *prediction* under thrust (node planner, ascent guidance) may use larger adaptive steps (RKF4(5), relative tolerance 1e-9). When thrust ends and the craft is outside atmosphere, immediately refit conic elements and return to rails.

### 3.6 Time warp

**The ladder.** Eight on-rails tiers plus physics warp:

| Tier | Rate | 1 real second = | Mode | Allowed when |
|---|---|---|---|---|
| 0 | 1x | 1 s | numeric or rails | always |
| P2–P4 | 2x, 3x, 4x | 2–4 s | **physics warp**: RK4 with 2–4 substeps of dt = 0.02 s per tick | under thrust / in atmosphere; blocked if `q > 20 kPa` or `|a_thrust| > 30 m/s²` (control fidelity) |
| 1 | 5x | 5 s | rails | coasting, outside atmosphere |
| 2 | 25x | 25 s | rails | " |
| 3 | 100x | 100 s | rails | " |
| 4 | 1,000x | ~16.7 min | rails | " |
| 5 | 10,000x | ~2.8 h | rails | " |
| 6 | 100,000x | ~1.16 d | rails | " |
| 7 | 1,000,000x | ~11.6 d | rails | " |

A full Hohmann flight to Saturn (6.05 yr) takes ~3.2 minutes of real time at tier 7. There are no per-altitude warp caps (rails propagation is exact); instead:

- **Event guard:** the warp controller looks at the event queue (SOI crossings, maneuver node start times, atmosphere interface crossings, predicted periapsis < surface + 5 km, closest-approach markers, alarm clock entries). Warp auto-steps down so that **no event occurs within 5 real-time seconds** at the current rate; it lands at 1x exactly 10 s (sim) before maneuver-node ignition and at the moment of SOI/atmosphere crossing.
- **Rails warp is forbidden** below the atmosphere interface altitude and while landed launch clamps are released with engines lit. Landed craft may use any tier (state is analytic).
- **Background simulation:** all colony/industry/life-support systems (05, 07, 08, 09) must integrate analytically per warp step — they receive `(t_prev, t_now)` and may not assume small dt. This is a binding interface.

**Thrust warp (low-thrust support, with 02-propulsion.md):**

- Numeric thrust warp up to **1,000x** for any burning craft: RKF4(5) with per-step relative tolerance 1e-9 and dt capped so `a_thrust·dt ≤ 1 m/s`. CPU budget interface to 13-architecture.md: ≤ 2 ms/frame/craft; the warp controller reduces rate if the budget is exceeded.
- **Spiral mode [Edelbaum]:** if `a_thrust < 0.01·g_local` — where `g_local = μ_frame/r²`, the local gravitational acceleration evaluated at the craft's **current orbital radius** (NOT the body's surface gravity; this is the standard low-thrust criterion and matches the Edelbaum assumptions) — and current e < 0.05 and target is a coplanar circular orbit in the same SOI, the game may execute the burn analytically at up to 100,000x: `Δv = |v_c1 − v_c2|`, duration `t = Δv/a_thrust` (constant-thrust approximation with mass update via rocket equation), trajectory rendered as a spiral. Low-thrust **escape** from a circular orbit costs `Δv ≈ v_c1` (Edelbaum/standard result). This deliberately teaches the Oberth penalty of low thrust: ion escape from LEO costs ~7.7 km/s of Δv versus 3.2 km/s impulsive — but at 10–30x better Isp (02-propulsion.md owns the engines).

### 3.7 Maneuver nodes & delta-v accounting

- A node is `(t_node, Δv_prograde, Δv_radial)` — **no normal component exists in 2D**. The node's frame is the craft's prograde/radial directions at t_node on the predicted trajectory.
- Node planner draws the resulting patched-conic trajectory across up to **5 SOI transitions** ahead, with encounter and closest-approach markers. Multiple chained nodes allowed (max 12).
- **Delta-v readout** uses Tsiolkovsky with stage awareness (stage data from 06-ships-stations.md):
  `Δv = v_e · ln(m0/m1)`, `v_e = Isp · g0`, `g0 = 9.80665 m/s²` exactly.
- **Burn time:** `t_b = (m0·v_e/F)·(1 − e^(−Δv/v_e))`. Execution splits the burn **centered on the node**: ignition at `t_node − t_b/2`. The UI shows t_b and warns when `t_b > 1/6` of the current orbit period ("impulsive approximation breaking down — consider splitting the burn"); the player can split a node into N periapsis-kick burns with one click.
- Burns are always executed as finite burns by the integrator; the node is the *plan*, reality is integrated. Residuals after a guided burn: the executor (autopilot program "Node Execute", Table 4.7) trims to within 0.1 m/s of the planned Δv vector or propellant exhaustion (8.9).

### 3.8 Transfer planning

**Hohmann (the workhorse).** Between coplanar circular orbits r1 → r2 about μ:

```
Δv1 = sqrt(μ/r1)·(sqrt(2 r2/(r1+r2)) − 1)
Δv2 = sqrt(μ/r2)·(1 − sqrt(2 r1/(r1+r2)))
t_transfer = π·sqrt(((r1+r2)/2)³ / μ)
```

**Bi-elliptic:** offered by the planner when `r2/r1 > 11.94` (classical threshold where bi-elliptic beats Hohmann); three-burn sequence via intermediate apoapsis r_b chosen by a slider (cost vs. time trade shown live).

**Phasing.** To shift phase angle by Δθ (rad) relative to a co-orbital target in N revolutions, burn into a phasing orbit of period

```
T_phase = T_target · (1 − Δθ/(2πN))     (Δθ > 0: target ahead → use a lower/faster orbit)
```

then return. The rendezvous planner (3.12) automates this.

**Synodic periods & launch windows.** For orbit periods T1, T2: `S = 1/|1/T1 − 1/T2|`. Required departure **phase angle** (target lead over chaser, heliocentric):

```
φ_dep = 180° − n_target · t_transfer ,   n_target = 360°/T_target   (deg/day)
```

Windows repeat every synodic period. Canonical values: Table 4.3. The first windows after campaign start follow from the 2049 epoch ephemerides in 03-solar-system.md (the window finder computes them; this doc does not hardcode dates).

**Worked example — Earth → Mars Hohmann (canonical, cited by 12-gameplay-economy-ui.md tutorials):**

- r1 = 1.000 AU, r2 = 1.524 AU, μ_sun = 1.32712e11 km³/s².
- Transfer ellipse a_t = 1.262 AU. Perihelion speed 32.73 km/s vs Earth's 29.78 → **v∞ departure = 2.95 km/s**.
- From 300 km LEO (v = 7,726 m/s, v_esc = 10,926 m/s): `Δv_TMI = sqrt(v∞² + v_esc²) − v_circ = sqrt(2.95² + 10.93²) − 7.73 =` **3,590 m/s**.
- Transfer time **259 days**. Mars sweeps 0.524°/day × 259 d = 135.7°; arrival point is 180° from departure → **departure phase angle = 44.3°** (Mars leads Earth).
- Arrival: transfer aphelion speed 21.48 km/s vs Mars's 24.13 → **v∞ arrival = 2.65 km/s**. Entry interface speed at Mars (125 km): `sqrt(2.65² + 2μ_M/r) =` **5.6 km/s**. Propulsive capture to 250 km circular: **2,100 m/s**; minimum capture to a just-bound ellipse: **680 m/s** (theoretical floor — MAVEN's flown MOI was ~1,230 m/s into a working 35-h science ellipse); aerocapture (T2): **~50 m/s** of trim.
- Windows repeat every **780 days**.

**Lambert solver (window scan).** The "Window Finder" sweeps departure/arrival date pairs and solves the 2D Lambert problem (universal-variable Lambert, BMW ch. 5, iterating on z with the same Stumpff functions as 3.3) for total Δv; result is displayed as a 1D-per-departure-date "window bar" (a porkchop collapses to clean curves in 2D). Prograde short-way solutions by default; long-way available behind an "advanced" toggle. Note: the classic 180°-transfer singularity of 3D Lambert (undefined transfer plane) **does not exist in 2D** — the plane is fixed; the solver is well-conditioned at all transfer angles except exact 0°/360°.

### 3.9 Gravity assists (patched-conic flybys)

Inside the flyby body's SOI the craft follows a hyperbola with the same |v∞| in and out; the assist rotates v∞ by the **turning angle**:

```
e_hyp = 1 + r_p · v∞² / μ_body        (r_p = periapsis radius, m; v∞ m/s; μ m³/s²)
δ     = 2·arcsin(1/e_hyp)             (turning angle)
|Δv_heliocentric| = 2 · v∞ · sin(δ/2) (free Δv imparted in the Sun frame)
```

Constraint: `r_p ≥ R_body + h_min` (h_min = atmosphere interface + 10 km, or 50 km for airless bodies; radiation belts may impose larger h_min per 03-solar-system.md).

In 2D the flyby targeting parameter ("B-plane") collapses to **one signed number**: the periapsis radius and which side you pass. **Pass behind the body → gain heliocentric energy; pass in front → lose it.** This is wonderfully teachable and is surfaced directly in the UI (3.9-UI in Section 5).

Worked examples (verify the formula):
- Jupiter arrival, v∞ = 5.64 km/s, r_p = 200,000 km: e = 1.050, δ = 144°, free heliocentric Δv up to **10.7 km/s** — this is why Act 5 tour design revolves around Jupiter.
- Earth flyby, v∞ = 3.0 km/s, r_p = 6,578 km: δ = 121°, up to **5.2 km/s** — enables Mercury/outer-planet routes (MESSENGER, Galileo, Cassini all used Earth/Venus assists).
- Moon assists from TLI-class v∞ (~0.8–1 km/s) give ~1.5 km/s — free Earth-escape boosts (real anchor: every outer-planet "lunar gravity assist" study; STEREO used lunar swingbys).

Moon-tour assists inside the Jovian/Saturnian systems use the same mechanic and cut capture-to-moon-orbit chains by 50–80 % (Galileo/Cassini tours); the Tour Planner program (T3, Table 4.7) automates multi-flyby sequencing.

### 3.10 Launch & ascent

**Initial state.** A craft on a pad moves with the body surface: position angle = pad longitude (rotating with the body at sidereal rate ω_body), velocity = `ω_body × r` tangential. Earth equatorial credit = **465 m/s** prograde (sidereal day 86,164 s); Mars 241 m/s; Moon 4.6 m/s; Venus 1.8 m/s retrograde (ignored, < 2 m/s). In 2D every site is effectively equatorial; player chooses prograde or retrograde launch (retrograde to LEO costs ~930 m/s extra — allowed, pointless, honest).

**Forces during ascent** (numeric integration per 3.5):

```
a_vec = thrust/m · û_attitude  −  μ/r² · r̂  −  (D/m) · v̂_air  (+ lift, 3.11)
D = ½ ρ v_air² C_d A          (v_air = velocity relative to rotating atmosphere)
```

Atmosphere co-rotates rigidly with the body (wind = 0 in v1; weather is out of scope).

**Loss accounting (HUD + post-flight report):**

```
Δv_gravity  = ∫ g·sin γ dt          (γ = flight-path angle above local horizon)
Δv_drag     = ∫ (D/m) dt
Δv_steering = ∫ (F/m)(1 − cos α) dt (α = angle between thrust and velocity)
Δv_total    = Δv_orbit_speed + Δv_gravity + Δv_drag + Δv_steering − rotation credit
nominal Earth ascent: 7,726 + 1,350 + 100 + 250 − 465 ≈ 8,960 m/s integrated
```

The catalog (row E1) quotes a deliberately conservative **9,400 m/s** — the commonly cited 9.3–9.5 km/s industry figure, which embeds non-equatorial launch sites and dispersion margins that our 2D equatorial sim does not pay. Design targets the sim must reproduce (tuning acceptance test for 13-architecture.md): a TWR-1.3 liftoff, 2-stage methalox vehicle reaches 300 km LEO for **8,900–9,300 m/s integrated Δv**, with gravity loss 1,100–1,500 m/s, drag loss 50–150 m/s, and steering loss 100–400 m/s; the identity above must close to < 50 m/s residual in the post-flight report. (Anchors: Saturn V ≈ 1.5 km/s gravity loss; typical drag 40–150 m/s; flown steering losses ~100–400 m/s.)

**Ascent guidance program (player-programmable autopilot, T0).** Parameters with defaults (Earth):

| Parameter | Default | Meaning |
|---|---|---|
| v_pitch_start | 50 m/s | fly vertical until this airspeed |
| h_curve | 60 km | gravity-turn shaping altitude |
| pitch law | `γ_cmd = 90°·(1 − sqrt(min(1, h/h_curve)))` | then follow prograde when α would exceed 5° |
| q_limit | 35 kPa | auto-throttle to hold q ≤ limit (max-Q rule) |
| a_limit | 40 m/s² (~4 g) | throttle cap (crew comfort per 08) |
| target_apo | 300 km | MECO when predicted apoapsis reached |
| auto-circ | on | creates+executes circularization node at apoapsis |

The same program with body-specific defaults handles Mars ascent (no q_limit issue, h_curve 25 km) and vacuum ascents (immediate pitch-over, h_curve 8 km on the Moon). Players can edit parameters per vehicle; later autopilot tiers add closed-loop guidance (Table 4.7).

### 3.11 Atmospheric flight, reentry, aerobraking, aerocapture

**Density model.** Piecewise-exponential (log-linear between breakpoints): per body, a table of `(h_i, ρ_i)` anchors (Table 4.4b); between anchors `ρ(h) = ρ_i · exp(−(h−h_i)/H_i)` with `H_i = (h_{i+1}−h_i)/ln(ρ_i/ρ_{i+1})`. Above the last anchor, ρ = 0: this altitude is the **atmosphere interface** — rails warp allowed above, forbidden below. Single-scale-height summaries (Table 4.4a) are for player-facing display; the breakpoints are the sim truth. Real upper atmospheres vary ±50 % with solar activity/season — we model the mean and note the variance only as flavor text.

**Drag & ballistic coefficient.**

```
D = ½ ρ v² C_d A ;     β = m/(C_d A)   [kg/m², the ballistic coefficient]
deceleration a = ½ ρ v² / β
terminal velocity v_t = sqrt(2 β g / ρ)
```

C_d·A per craft comes from 06-ships-stations.md part data (fixed C_d per assembly; no Mach dependence in v1 — an acknowledged simplification). Deployed parachutes simply add huge C_d·A. Opening constraints are **per-chute part stats `(q_max, v_max)` owned by 06/10**; binding class defaults: supersonic DGB-class chutes q_max ≈ 1 kPa, v_max ≈ 600 m/s (real Mars EDL practice — MSL/Mars 2020 deployed at ~750 Pa and Mach ~2.3, qualified to ~850 Pa); subsonic drogues q_max ≈ 15–20 kPa (Earth practice); mains q_max ≈ 3–5 kPa (subsonic deploy). A chute opened outside its limits is shredded (chute part destroyed, alarm; no damage to the rest of the craft).

**Lift (2D).** Optional per-craft L/D ratio (capsule with offset CG: L/D = 0.30, Apollo anchor; spaceplane: L/D = 1.0+). Lift force `L = (L/D)·D`, directed perpendicular to airspeed; the player/autopilot selects **lift-up or lift-down** (the 2D remnant of bank-angle modulation). Lift-up stretches the entry (lower g, lower peak q̇, more total heat load); lift-down steepens it. This one-bit control plus periapsis targeting is the entire entry-corridor game, and it is faithful to how real entry guidance modulates g-load.

**Ballistic-entry sanity model (design check, also used for the planner's prediction when the player has no integrator preview).** Allen–Eggers closed form for constant γ:

```
a_max = v_E² · sin γ_E / (2 e H)        (e = 2.71828; H = local scale height)
h(a_max) = H · ln( ρ_0 H / (β sin γ_E) )
```

Example: LEO entry v_E = 7.8 km/s, γ_E = 2°, H = 8.5 km → a_max ≈ 4.7 g. Matches Soyuz-class entries (4–5 g nominal; their ballistic backup mode at steeper γ reaches 8–9 g).

**Heating model.** Stagnation-point convective heating, Sutton–Graves:

```
q̇ = k · sqrt(ρ / r_n) · v³        [W/m²; ρ kg/m³; r_n = nose radius m; v m/s]
k_air (Earth, N2 bodies incl. Titan) = 1.7415e-4
k_CO2 (Mars, Venus)                  = 1.90e-4
k_H2He (Jupiter, Saturn)             = 1.7415e-4 × 2.0  [GAME MODEL — H2/He entry is
                                       brutally radiative; factor stands in for it]
Radiative augmentation (all bodies): q̇_total = q̇ · f_rad,
  f_rad = 1                              for v ≤ 9,000 m/s
  f_rad = min(1 + ((v − 9000)/3000)², 8) for v > 9,000 m/s   [GAME MODEL stand-in for
                                    shock-layer radiation; calibrated so lunar return
                                    ≈ 1.45x and Stardust-speed ≈ 2.7x convective.
                                    The quadratic is calibrated ONLY on 9–13 km/s Earth
                                    entries and has no validity above that range — hence
                                    the hard cap at 8, reached near 17 km/s]
```

Validation anchor: Stardust (v = 12.9 km/s, r_n = 0.229 m, ρ ≈ 2e-4 kg/m³ at peak) → q̇_conv ≈ 1,100 W/cm², matching the flown ~1,200 W/cm².

**Heat-shield rule.** Every part stack exposed to airflow has a thermal protection entry (Table 4.5):

- Flux-limited (reusable) shields: fail (part destroyed) if `q̇_total > q̇_max` for > 2 s.
- Ablative shields: the destruction check compares **q̇_conv only (convective, no f_rad) against q̇_max** — ablators are flux-tolerant, and the Table 4.5 limits are anchored to flown *convective* values. (This convention keeps the model consistent with its own anchors: Stardust's q̇_conv ≈ 1,100 W/cm² passes PICA's 1,200 W/cm² limit, whereas checking the f_rad-augmented q̇_total ≈ 2,970 W/cm² would destroy the shield on its own anchor mission.) The augmented `q̇_total` feeds only the consumption and heat-load integrals: ablator mass is consumed at `ṁ_abl = q̇_total / E_abl` per m² of loaded area, with `E_abl = 50 MJ/kg` [GAME TUNING — real effective heats of ablation including blockage are higher and messier; 50 MJ/kg makes Stardust-class entries consume ≈ 45 % of a PICA shield, which is good gameplay]. **Loaded area** = the shield part's frontal projected area A_shield, supplied by 06-ships-stations.md (the same A used in C_d·A); the stagnation-point q̇ is applied uniformly over it — a deliberate conservative simplification. Shield depleted → structure takes flux → destroyed at bare-structure limit.
- Unshielded structure limit: radiative-equilibrium derived, 0.007 MW/m² aluminum (T_eq ≈ 600 K — aluminum loses most of its strength well below its 933 K melting point) / 0.10 MW/m² steel hot structure (T_eq ≈ 1,150 K).
- Heat *load* (∫q̇ dt, MJ/m²) is tracked and displayed; it is what sizes ablators.

**g-load rule.** `n = |a_nongrav|/9.80665`. Crew (defaults only — 08-life-support-crew.md owns and finalizes crew tolerance): warning at n > 7 sustained 5 s; injury at n > 12 sustained 5 s; death at n > 25 sustained > 10 s, or at n > 45 at any duration. (Anchors: John Stapp survived 46.2 g for ~1 s on the rocket sled; the Soyuz 18a crew survived a ~21.3 g ballistic abort — an instant-death threshold at 25 g would be indefensible.) Cargo/structure limits per part (06), default 12 g axial / 6 g lateral.

**Aerobraking (manual at T0; corridor advisor: T1).** Repeated atmospheric periapsis passes from a capture ellipse, each lowering apoapsis. The physics emerges from the integrator and is available from T0 with manual periapsis control (matching Section 6); the T1 unlock is the advisor tooling only. Rules of play: choose periapsis altitude ("walk it in" 2–5 km at a time, exactly like Magellan/MGS operations); per-pass constraints are the same q̇/g/heat-load rules; rails warp is allowed between passes, auto-dropping at each interface crossing. The T1 "corridor advisor" overlay shows per-pass predicted Δapoapsis, peak q̇, and peak g.

**Aerocapture (T2 unlock — never yet flown, NASA systems-analysis studies: Mars, Venus, Titan, Neptune).** Single-pass hyperbolic → bound orbit. The **corridor** is the periapsis-altitude window where post-pass apoapsis lands between the target and escape:

```
corridor: h_p* ± Δh,  Δh ≈ 0.5–1.0 × H_local  (a few km — honest and tense)
```

The Aerocapture Guidance program (T2) holds lift-up/lift-down to steer within corridor; without it, manual aerocapture is possible but demands a generous β and nerve. Typical trim burn after a successful pass: 30–100 m/s (raise periapsis out of atmosphere). Entry-interface speeds set the TPS class per body: Titan ≈ 6.5–8 km/s (the gentle teaching case — huge scale height, standard ablators suffice; anchor: Titan Explorer aerocapture study); Mars ≈ 5.5–7 km/s and Venus ≈ 10–11 km/s (PICA-class); ice giants (Uranus/Neptune) ≈ 22–25 km/s — carbon-phenolic-class TPS required (Table 4.5). **Jupiter (interface ≥ 60 km/s) and Saturn (≥ 36 km/s) offer NO aerocapture option:** shock-layer radiation at those speeds is far beyond any modeled TPS and outside the scope of the NASA studies; capture at the gas giants is propulsive — and cheap anyway thanks to Oberth (J2: 450 m/s; S2: 670 m/s, or ~100 m/s via the Titan-aerocapture alternative).

**Skip-out and partial passes** arise naturally from integration: exit with v > v_esc(local) → still hyperbolic, you skipped. No special rule needed; the planner warns when predicted exit is unbound.

**Orbital decay (abstraction).** Below the interface the integrator handles drag honestly. Real thermosphere drag above our interface (e.g., ISS at 400 km) is abstracted as a station-keeping fee (Table 4.8): LEO assets in band 200–500 km pay 2–25 m/s/yr of RCS Δv per the altitude curve in Table 4.8 (ISS anchor ≈ 20 m/s/yr at 400 km); above 500 km, the flat 2 m/s/yr background fee of Table 4.8 applies. Fee auto-deducts from station RCS propellant (06/05 logistics restock).

### 3.12 Rendezvous & docking

2D makes rendezvous honestly easier than reality (no plane matching, no RAAN launch windows) — we keep the real *phasing* problem and the real *terminal* discipline.

**Phasing strategy (the taught loop):**
1. Launch into a lower coplanar orbit (every launch is in-plane in 2D — acknowledged gift).
2. Compute phase angle φ to target; coast `t_wait = φ / (n_chaser − n_target)` or burn into a phasing orbit (3.8) for an N-rev catch-up.
3. Hohmann up to the target altitude timed so arrival apoapsis is within 2 km / 5 m/s of target.
4. **Match velocity** at closest approach (kill relative velocity), then translate in on RCS.

Typical budget after a competent phasing setup: **25–100 m/s** (matches real LEO rendezvous budgets); the map shows closest-approach markers (next two approaches, distance + relative speed) exactly KSP-style — patched-conic closest approach is found by golden-section minimization of |Δr(t)| on rails.

**Approach gates (soft rule — exceeding them triggers proximity alarms; collisions are real):**

| Range to target | Max closing speed |
|---|---|
| 10 km | 30 m/s |
| 2 km | 10 m/s |
| 500 m | 5 m/s |
| 100 m | 2 m/s |
| 30 m | 1 m/s |
| Contact (port) | 0.05–0.30 m/s (port class dependent, 06) |

**Docking mini-loop (manual).** Camera-aligned close view; controls: RCS translate (±x, ±y), rotate, fine mode (10 % thrust). HUD: relative velocity vector, port alignment error, range, closing rate. **Capture condition:** |v_rel| ≤ 0.3 m/s AND axial alignment ≤ 5° AND lateral offset ≤ 0.5 m AND relative rotation rate |ω_rel| ≤ 1°/s, within the port's 15° approach cone → soft capture (magnetic/probe), then automatic hard dock over 10 s. (Angular-rate anchor: ISS docking systems specify ~0.1–0.5°/s; 1°/s is the forgiving game value — without this term a tumbling craft could "capture" mid-spin.) Contact outside limits at < 2 m/s: bounce (no damage, alarm). Contact > 2 m/s: collision damage per 06 structural rules.

**Autodock program (T1; anchor: Soyuz/Progress Kurs, ATV).** Executes gates table automatically; requires both vehicles to carry a docking transponder part (Electronics cost, 06). Rendezvous Sequencer (T1) chains phasing→Hohmann→match→approach.

**Direction discipline:** prograde and retrograde orbits cannot dock (closing speeds ~2×v_orbit ≈ 15 km/s in LEO). The planner refuses to target a rendezvous between opposite-sense orbits and shows a "WRONG WAY" banner; reversing sense costs 2×v_orbit propulsively — effectively a rebuild-your-trajectory decision (8.10).

### 3.13 L4/L5 — and why we must cheat honestly

**Patched conics cannot produce Lagrange points** (they exist only in the three-body problem). Rather than fake the dynamics, we model **anchor slots**: designated on-rails parking orbits that the game treats as stable storage locations. Design note shown to players in-game (honesty pledge): *"Lagrange dynamics are not simulated; these slots stand in for orbits that are genuinely stable in reality."*

| Slot | Where | Capture rule | Stationkeeping fee | Real anchor |
|---|---|---|---|---|
| Sun–X L4/L5 | X's orbit, ±60° mean longitude | within 0.01·a_X of slot center AND v_rel < 100 m/s → snap to rails co-orbit | **0 m/s/yr** (L4/L5 are dynamically stable) | Jupiter trojans (real asteroids populate the Sun–Jupiter slots — Act 4/5 mining content per 03/04) |
| Earth–Moon L4/L5 | Moon's orbit ±60° | within 20,000 km AND v_rel < 50 m/s | 0 m/s/yr | classic O'Neill/space-settlement siting |
| Sun–Earth L1/L2 [optional v1.1] | 1.5e6 km sun/anti-sun | within 100,000 km AND v_rel < 50 m/s | **4 m/s/yr** auto-deducted RCS (unstable in reality) | SOHO 2.4 m/s/yr, JWST ≤ 4 m/s/yr |

Slots hold unlimited stations/depots (they are bookkeeping anchors, not physical points). Reaching them costs real Δv (map rows in Table 4.2). A craft nudged out of a slot (undock, burn) reverts to ordinary rails in the parent SOI.

### 3.14 What 2D drops — the honesty section

| Dropped | Reality | Consequence in game | Compensation |
|---|---|---|---|
| Inclination & plane changes | Plane changes cost up to 2·v·sin(Δi/2); a 28.5°-launch GTO→GEO mission pays ~1.8 km/s combined vs our coplanar 1,470 m/s | Everything is cheaper by the plane-change tax (0–30 % on some real missions) | **None — deliberately.** We refuse fake Δv taxes. Difficulty is preserved by real scale, real synodic waits, and real budgets. The doc and UI say so plainly. |
| Polar & sun-synchronous orbits | Mapping, ice-prospecting, comms coverage need them | Cannot exist | Survey/mapping is abstracted: any circular orbit below a body-specific altitude grants survey coverage at a rate (12-gameplay owns rates). |
| Polar landing sites (lunar PSR ice!) | Reaching ±90° latitude from an equatorial orbit is impossible without a plane change | Critical Act 2 resource (04-resources-isru.md polar volatiles) would be free to reach | **Polar-site surcharge [GAME MODEL]:** surface sites tagged `Polar` charge a flat **+500 m/s** on every descent AND ascent leg, representing out-of-plane geometry. Mechanism below. Binding on 03 (site tags), 04, 07, 10. |
| RAAN/launch-window-to-plane timing | Real ISS launches wait for the plane to pass overhead | Every launch is in-plane | Keep honest phasing waits; nothing else needed. |
| 3D gravity-assist geometry (Tisserand plane targeting) | B-plane is 2D | Flyby targeting is a 1-DOF choice (periapsis radius + leading/trailing side) | Presented as a feature: the cleanest possible teaching of assists. |
| Retrograde-inclined orbit phenomena (SSO precession, Molniya) | J2 not modeled either | No frozen/Molniya orbits | Out of scope; stationkeeping fees stand in for perturbations (Table 4.8). |
| Eclipse/occultation geometry in 3D | A 2D orbit passes behind its body every rev | MORE comm blackouts and eclipses than reality | Accepted: drives relay-constellation gameplay (05/09 interfaces — eclipse fraction formula below). |

**Polar-surcharge mechanism (binding — descents/ascents are physically integrated, so the charge needs an executable rule):** when the active vehicle crosses 10 km altitude descending toward a `Polar`-tagged site, or at ascent-guidance ignition lifting off from one, the active stage's propellant is debited the rocket-equation mass for 500 m/s at the craft's current total mass and the current stage's vacuum Isp: `Δm = m·(1 − e^(−500/v_e))`. The debit is applied linearly over 60 s of sim time (so life-support/power ticks see a finite burn, not a teleporting mass change), exactly once per leg. The landing/ascent planner adds +500 m/s to the displayed budget pre-commitment and refuses to initiate powered descent or ascent guidance if remaining stage Δv < (required + 500) m/s; if a manually flown leg exhausts propellant mid-debit anyway, normal propellant-exhaustion rules apply (8.9).

Eclipse rule (binding for 09-power-thermal.md solar arrays and 05 comms): a craft is in shadow/comm-occlusion when the body disk (radius R) blocks the line to the Sun/target: for a circular orbit of radius r, shadow fraction per orbit `f = (1/π)·arcsin(R/r)` ×2/2 = `arcsin(R/r)/π`. (LEO 300 km: f ≈ 0.40 — slightly above the real ~0.36; honest 2D artifact, noted.)

---

## 4. Content Catalog

### 4.1 Canonical SOI table (computed from r_SOI = a·(m/M)^(2/5); orbit semi-major axes a are 03-solar-system.md §4.2/§4.3 canonical ephemerides verbatim — 03 owns body data — masses per NASA fact sheets; the r_SOI column is computed here in one pass from those inputs and 03 republishes it verbatim, never recomputing independently)

| Body | Parent | a (km) | Mass (kg) | r_SOI (km) | Notes |
|---|---|---|---|---|---|
| Mercury | Sun | 57.91e6 | 3.301e23 | **112,400** | |
| Venus | Sun | 108.21e6 | 4.867e24 | **616,200** | |
| Earth | Sun | 149.60e6 | 5.972e24 | **924,500** | often quoted 924,000–929,000 (distance-dependent); we fix the a-based value |
| Moon | Earth | 384,400 | 7.342e22 | **66,200** | commonly quoted 66,100 |
| Mars | Sun | 227.94e6 | 6.417e23 | **577,200** | |
| Phobos | Mars | 9,376 | 1.066e16 | (7) → **none** | SOI floor rule: 7 km < 1.5×11 km radius — rendezvous object |
| Deimos | Mars | 23,463 | 1.476e15 | (8) → **none** | rendezvous object |
| Vesta | Sun | 353.3e6 | 2.59e20 | **39,300** | |
| Ceres | Sun | 413.8e6 | 9.38e20 | **77,000** | |
| Psyche | Sun | 437.4e6 | 2.29e19 | **18,400** | metal-asteroid content per 04 |
| Jupiter | Sun | 778.57e6 | 1.898e27 | **48,200,000** | |
| Io | Jupiter | 421,800 | 8.932e22 | **7,840** | |
| Europa | Jupiter | 671,100 | 4.800e22 | **9,730** | |
| Ganymede | Jupiter | 1,070,400 | 1.4819e23 | **24,350** | |
| Callisto | Jupiter | 1,882,700 | 1.0759e23 | **37,700** | preferred crew staging (radiation, per 03/08) |
| Saturn | Sun | 1,433.5e6 | 5.683e26 | **54,800,000** | |
| Enceladus | Saturn | 237,948 | 1.080e20 | **490** | passes floor rule (1.5×252 = 378 km) — barely; periapsis ops are tight and fun |
| Titan | Saturn | 1,221,870 | 1.3452e23 | **43,300** | |
| Uranus | Sun | 2,870.7e6 | 8.681e25 | **51,800,000** | |
| Neptune | Sun | 4,498.4e6 | 1.024e26 | **86,600,000** | |
| Triton | Neptune | 354,759 | 2.139e22 | **12,000** | retrograde around Neptune — representable in 2D (s = −1), kept |
| Pluto | Sun | 5,906.4e6 | 1.303e22 | **3,150,000** | flavor/endgame probe target |

### 4.2 THE CANONICAL DELTA-V MAP (single source of truth — all sibling docs cite these numbers)

Conventions: impulsive burns, coplanar (2D), from/to circular orbits; canonical parking orbits: **LEO = 300 km**, **LLO = 100 km**, **LMO = 250 km**, **LVO = 250 km**. "Aero" = cost with aerobrake/aerocapture/EDL where an atmosphere allows it (trim burns only). Values computed from vis-viva with fact-sheet μ; rounded to 10 m/s. Hohmann v∞ values in Table 4.3.

| # | From → To | Δv (m/s) | Aero option | Notes / anchor |
|---|---|---|---|---|
| E1 | Earth surface → LEO | **9,400** | — | conservative catalog quote (industry figure 9.3–9.5 km/s); honest equatorial sims integrate 8,900–9,300 per identity 3.10 (gravity 1,100–1,500 + drag 50–150 + steering 100–400 − 465 rotation credit) |
| E2 | LEO → GTO (300×35,786 km) | **2,430** | — | |
| E3 | GTO → GEO | **1,470** | — | coplanar value; real 28.5°-launches pay ~1,800 (see 3.14) |
| E4 | LEO → GEO (direct total) | **3,900** | — | E2+E3 |
| E5 | LEO → Earth escape (C3 = 0) | **3,200** | — | |
| E6 | LEO → deorbit (entry interface) | **100** | entry 7.8 km/s | Soyuz deorbit ≈ 120 m/s |
| M1 | LEO → TLI (trans-lunar injection) | **3,110** | — | Apollo ≈ 3,150 from ~185 km |
| M2 | TLI → LLO (lunar orbit insertion) | **830** | — | Apollo LOI ≈ 850–900 |
| M3 | LLO → Moon surface | **1,900** | — | v_circ 1,630 + ~270 gravity/hover losses; Apollo LM descent budget ≈ 2,000 |
| M4 | Moon surface → LLO | **1,850** | — | Apollo ascent ≈ 1,850 |
| M5 | LLO → Earth return (TEI) | **830** | entry 11.0 km/s | aero all the way to surface |
| M6 | LEO → Earth–Moon L4/L5 slot | **3,950** | — | TLI + full velocity match (no Oberth at slot) |
| L1 | LEO → Sun–Earth L1/L2 slot | **3,250** | — | escape-class + small insertion; SOHO/JWST class |
| L2 | LEO → Sun–Earth L4/L5 slot | **3,900** | — | escape + slow heliocentric drift (months–years); patience trades for Δv |
| V1 | LEO → Venus transfer | **3,480** | — | v∞ 2.50 km/s |
| V2 | Venus arrival → LVO (propulsive) | **3,330** | **50** (aerocapture, T2) | min elliptical capture 360 |
| V3 | Venus arrival → aerostat (50 km) | — | **0** (direct entry, 10.6 km/s) | NASA HAVOC profile; 10-vehicles owns EDL |
| V4 | Venus aerostat (50 km) → LVO | **~8,300** | — | full rocket ascent from 50 km [est.; 10-vehicles owns]; v_circ = 7,180 |
| R1 | LEO → Mars transfer (TMI) | **3,590** | — | worked example 3.8; v∞ 2.95 |
| R2 | Mars arrival → LMO (propulsive) | **2,100** | **50** (aerocapture, T2) | min capture to a just-bound ellipse: 680 (theoretical floor; MAVEN flew ~1,230 m/s into a working 35-h science ellipse) |
| R3 | LMO → Mars surface (EDL) | **600** | mostly aero | entry ~3.5 km/s from LMO (5.6 km/s applies only to direct entry from hyperbolic arrival — worked example 3.8); terminal retropropulsion (anchor: Mars EDL studies, ~0.4–0.7 km/s for large landers) |
| R4 | Mars surface → LMO | **4,000** | — | v_circ 3,430 + losses; MAV studies 4.0–4.3 km/s |
| R5 | LMO → Earth return (TEI) | **2,100** | entry 11.5 km/s | symmetric with R2 |
| R6 | LMO → Phobos rendezvous | **1,230** | — | then dock-with-surface (no SOI) |
| R7 | LMO → Deimos rendezvous | **1,730** | — | |
| H1 | LEO → Mercury transfer (Hohmann) | **5,540** | — | v∞ arr 9.61 km/s — capture below is why nobody flies this direct |
| H2 | Mercury arrival → low orbit 200 km | **7,550** (direct Hohmann) | — | with 2–3 Venus/Mercury flybys: **≈ 2,000** [route-dependent]. Anchor: MESSENGER, BepiColombo |
| A1 | LEO → NEA rendezvous (class Easy/Typical/Hard) | **4,200 / 5,000 / 6,000** | — | total incl. arrival match; 03 owns the NEA list; return to Earth 200–1,000 + aerocapture |
| A2 | LEO → Vesta transfer | **4,520** | — | v∞ arr 4.43 |
| A3 | Vesta arrival → low orbit 40 km | **4,200** | — | tiny well: capture ≈ v∞. Low-thrust strongly favored (Dawn anchor) |
| A4 | Vesta orbit ↔ surface | **270** | — | v_circ 240 |
| A5 | LEO → Ceres transfer | **4,890** | — | v∞ arr 4.86 |
| A6 | Ceres arrival → low orbit 50 km | **4,550** | — | low-thrust strongly favored (Dawn) |
| A7 | Ceres orbit ↔ surface | **380** | — | v_circ 350 |
| J1 | LEO → Jupiter transfer (Hohmann) | **6,300** | — | 2.73 yr; v∞ arr 5.64 |
| J2 | Jupiter arrival → capture ellipse (r_p 200,000 km) | **450** | — (no aerocapture: entry interface ≥ 60 km/s, beyond any modeled TPS — see 3.11) | Oberth at 36 km/s perijove makes propulsive capture cheap |
| J3 | Capture ellipse → Callisto orbit | **1,700** propulsive / **≈600** with moon-assist tour (T3 Tour Planner) | — | Galileo-style tour |
| S1 | LEO → Saturn transfer (Hohmann) | **7,280** | — | 6.05 yr; v∞ arr 5.44 |
| S2 | Saturn arrival → capture ellipse (r_p 160,000 km) | **670** | **Titan aerocapture: ~100** (T2 — Aerocapture Guidance; carbon-phenolic NOT required at Titan's 6.5–8 km/s entry; Titan Explorer study) | periapsis outside main rings; no Saturn-atmosphere aerocapture (interface ≥ 36 km/s, 3.11) |
| S3 | Capture ellipse → Titan orbit | **1,200** propulsive / **≈100** via Titan aerocapture | — | |
| S4 | Titan orbit (1,500 km) ↔ surface | down: **~150** (chutes; Huygens) · up: **2,400** | — | v_circ 1,480 at 1,500 km (sqrt(8,978 km³/s² / 4,075 km)) + ~900 gravity/drag losses through the 850-km-deep atmosphere, dense lower layers dominating [est.; 10 owns ascent vehicle] |
| S5 | Saturn ellipse → Enceladus orbit | **2,100** (propulsive; moon assists reduce) | — | Cassini-tour style |
| U1 | LEO → Uranus transfer (Hohmann) | **7,980** | — | 16.0 yr — Jupiter assist in practice |
| U2 | Uranus arrival → capture ellipse | **550** | — | r_p 30,000 km |
| N1 | LEO → Neptune transfer (Hohmann) | **8,250** | — | 30.6 yr — assists or T4 propulsion in practice |
| N2 | Neptune arrival → capture ellipse | **380** | — | r_p 30,000 km |
| G1 | Gravity-assist credit (per flyby, typical) | Venus/Earth: up to **3,000–5,200** · Jupiter: up to **10,700** | — | formula 3.9; free but window-constrained |
| X1 | Polar-site surcharge (any body) | **+500 per descent or ascent leg** | — | [GAME MODEL] 2D compensation, see 3.14 |

Reading rules: legs chain additively (e.g., LEO→Moon surface = M1+M2+M3 = 5,840 m/s). Lambert/non-Hohmann transfers and gravity-assist routes will beat or miss these numbers; this table is the **Hohmann reference baseline**, and contracts/UI quote it as "catalog Δv".

### 4.3 Synodic periods, transfer times, windows (Earth ↔ X, Hohmann)

| Target | Transfer time | Synodic period | v∞ depart (km/s) | v∞ arrive (km/s) | Departure phase angle |
|---|---|---|---|---|---|
| Mercury | 105 d | 115.9 d | 7.53 | 9.61 | 108° |
| Venus | 146 d | 583.9 d | 2.50 | 2.71 | −54.0° (Venus trails) |
| Mars | 259 d | 779.9 d | 2.95 | 2.65 | +44.3° |
| Vesta | 398 d | 504.1 d | 5.52 | 4.43 | +71.9° |
| Ceres | 472 d | 466.6 d | 6.31 | 4.86 | +79.0° |
| Jupiter | 2.73 yr | 398.9 d | 8.79 | 5.64 | +97.1° |
| Saturn | 6.05 yr | 378.1 d | 10.29 | 5.44 | +106.1° |
| Uranus | 16.0 yr | 369.7 d | 11.28 | 4.66 | +111.3° |
| Neptune | 30.6 yr | 367.5 d | 11.65 | 4.05 | +113.1° |

(Phase angle = target's lead over Earth at departure, heliocentric, from φ = 180° − n_target·t_transfer.)

### 4.4a Atmospheres — summary parameters (display values)

| Body | Surface P (kPa) | Surface ρ (kg/m³) | Scale height H (km) | Interface altitude (km) | Main gas | Anchor |
|---|---|---|---|---|---|---|
| Earth | 101.3 | 1.225 | 8.5 | **140** | N2/O2 | US Std 1976 |
| Mars | 0.61 | 0.016 | 11.1 | **125** | CO2 | Viking / MCD; ρ0 follows the ideal gas law from 03's canonical datum (P0 = 0.61 kPa, T0 = 210 K, μ = 43.34 g/mol → ρ = P·μ/(R·T) ≈ 0.0151 kg/m³), displayed as 0.016 to match 03 S-5b and 04 M-3e verbatim |
| Venus | 9,200 | 65.0 | 15.9 | **180** | CO2 | VIRA; 50-km level is ~1 atm (1.066 atm), ~348 K (75 °C) — aerostat country (HAVOC itself quotes 75 °C at 50 km); the temperate 293–310 K band sits higher, at 52.5–54 km and ~0.6–0.8 atm |
| Titan | 146.7 | 5.28 | 21 (lower) / ~50 (upper) | **850** | N2/CH4 | Huygens HASI |
| Jupiter | 100 (1-bar datum) | 0.16 at datum | 27 | **1,000 above datum** | H2/He | NASA fact sheet |
| Saturn | 100 (datum) | 0.19 | 59.5 | **1,500 above datum** | H2/He | NASA fact sheet |
| Uranus | 100 (datum) | 0.42 | 27.7 | **1,200 above datum** | H2/He | fact sheet; v1.1 content |
| Neptune | 100 (datum) | 0.45 | ~20 | **1,000 above datum** | H2/He | fact sheet; v1.1 content |

### 4.4b Atmosphere breakpoints (sim truth; ρ in kg/m³ at altitude km; log-linear between; [GAME MODEL] fitted to the anchors above — 03-solar-system.md republishes these verbatim)

| Body | Breakpoints (h km : ρ) |
|---|---|
| Earth | 0:1.225 · 25:4.0e-2 · 50:1.03e-3 · 75:4.0e-5 · 100:5.6e-7 · 120:2.2e-8 · 140:3.9e-9 (interface) |
| Mars | 0:1.5e-2 · 25:2.5e-3 · 50:2.8e-4 · 75:1.6e-5 · 100:1.0e-7 · 125:6e-9 (interface; 0-km anchor 1.5e-2 = the gas-law value from 03's canonical P0/T0/μ — consistent with 03 S-5b and 04 M-3e, NOT the older fact-sheet 2.0e-2) |
| Venus | 0:65 · 50:1.6 · 70:9.2e-2 · 100:5e-5 · 130:1e-7 · 180:2e-9 (interface) |
| Titan | 0:5.28 · 75:1.5e-1 · 300:1.7e-3 · 600:4e-6 · 850:7e-8 (interface) |
| Jupiter | −100:0.6 · 0:0.16 · 200:9e-5 · 500:1.3e-9 · 1000:1e-13 (interface; datum = 1 bar) |
| Saturn | −150:0.5 · 0:0.19 · 300:1.2e-3 · 800:2e-8 · 1500:1e-13 (interface) |

Last anchors must be finite (the piecewise-exponential rule H_i = (h_{i+1}−h_i)/ln(ρ_i/ρ_{i+1}) is undefined against ρ = 0); ρ = 0 applies strictly *above* the interface anchor per 3.11. **Uranus/Neptune (v1 rule):** no breakpoints ship in v1 — the 4.4a interface altitudes still generate atmosphere-entry events and the rails-warp lockout, but any craft crossing the interface is **lost (destruction zone)**, with a planner warning at trajectory-plot time; density breakpoints ship with the v1.1 ice-giant content.

### 4.5 Thermal-protection catalog (binding for 06-ships-stations.md part stats)

| TPS type | Tier | Max flux (MW/m²) | (W/cm²) | Areal mass (kg/m²) | Capacity (MJ/m² = mass × 50) | Reusable | Anchor |
|---|---|---|---|---|---|---|---|
| BareStructure (Al) | — | 0.007 | 0.7 | 0 | — | — | radiative equilibrium ≈ 600 K at 0.007 MW/m² — the structural limit of aluminum (loses most strength well below its 933 K melt) |
| SteelHotStructure | T1 | 0.10 | 10 | +15 % dry mass | — | yes | stainless reentry vehicles (Starship-class studies) |
| ReusableTile (HRSI/TUFROC-class) | T1 | 0.30 | 30 | 12 | flux-limited | yes | Shuttle tiles, 1,260 °C |
| ReinforcedCarbonCarbon | T2 | 0.75 | 75 | 35 | flux-limited | yes | Shuttle RCC leading edges ~1,650 °C |
| AVCOAT-class ablator | T0 | 6.0 | 600 | 40 | 2,000 | no | Apollo lunar return (~400–500 W/cm² flown) |
| PICA-class ablator | T1 | 12.0 | 1,200 | 16 | 800 | no | Stardust 12.9 km/s, ~1,200 W/cm²; MSL/Mars 2020 |
| Carbon-phenolic (HEEET-class) | T3 | 30 | 3,000 | 60 | 3,000 | no | stat anchor: HEEET arc-jet qualification (~3,600 W/cm² demonstrated) — Venus deep entry, ice-giant aerocapture. (Heritage fully-dense carbon phenolic flew Galileo into Jupiter at ~30 kW/cm² and 230 g; that environment is deliberately NOT a part stat here — Jupiter/Saturn entry is out of scope, 3.11) |

Rules of use in 3.11. For ablative rows, the max-flux limit is checked against q̇_conv (convective only); ablator consumption uses the augmented value: ṁ = q̇_total/(50 MJ/kg) per m² of loaded area [GAME TUNING] (3.11).

### 4.6 Time-warp ladder

(Normative table in 3.6; repeated here for catalog completeness: 1x · physics 2–4x · rails 5x / 25x / 100x / 1,000x / 10,000x / 100,000x / 1,000,000x; event-guard 5 s; thrust warp ≤ 1,000x numeric; Edelbaum spiral mode ≤ 100,000x.)

### 4.7 Flight-computer program catalog (autopilots the player unlocks & parameterizes)

| Program | Tier | Function | Real anchor |
|---|---|---|---|
| Node Execute | T0 | warp-to-node, finite-burn execution, ±0.1 m/s trim | every flown upper stage |
| Ascent Guidance | T0 | parameterized gravity turn (3.10), max-Q hold, auto-circularize | Saturn V IGM / open-loop+PEG ascent |
| Circularize / Apsis Burn | T0 | node generation at apo/peri | — |
| Hohmann Planner | T0 | 3.8 formulas + phase-window wait | Apollo-era hand methods |
| Window Finder (Lambert scan) | T1 | departure-date sweep, window bars UI | porkchop plots, JPL |
| Rendezvous Sequencer | T1 | phasing → transfer → match velocity | Gemini/Apollo CSM |
| Autodock | T1 | gates table 3.12 to capture | Soyuz/Progress Kurs (1980s), ATV |
| Vacuum Landing (suicide-burn + hover) | T1 | gravity-loss-minimizing descent, terminal hover | Apollo LM P63–P66; Falcon-style guidance |
| EDL Guidance | T2 | entry corridor hold, chute trigger, terminal retropropulsion | Viking → Mars 2020 |
| Aerocapture Guidance | T2 | lift-up/down corridor control (3.11) | NASA aerocapture systems studies |
| Low-Thrust Spiral | T2 | Edelbaum spiral mode planner (3.6) | SMART-1, Dawn |
| Tour Planner (multi-flyby) | T3 | chained gravity-assist search inside a planetary system | Galileo/Cassini tours |
| Stationkeeping Manager | T1 | auto-deduct fees (4.8), alarm on propellant low | ISS/GEO ops |

Programs consume Electronics + MachineParts to install (05-industry-logistics.md) and are unlocked via 11-research-tech.md.

### 4.8 Stationkeeping fees (abstraction of unmodeled perturbations; auto-deducted RCS Δv)

| Location | Fee (m/s per year) | Real anchor |
|---|---|---|
| LEO 200–300 km | 25 | rapid decay band |
| LEO 300–500 km | fee(h): piecewise log-linear (linear in ln fee vs h) through the anchor pairs (300 km: 25) · (400 km: 20) · (500 km: 2) | fee(400) = 20 matches the ISS anchor (≈ 20 m/s/yr at ~400 km); continuous with the 25 m/s/yr row above and the 2 m/s/yr row below |
| LEO > 500 km, MEO, GEO | 2 | GEO E-W only ≈ 2 (N-S doesn't exist in 2D) |
| Sun–Earth L1/L2 slot | 4 | SOHO 2.4, JWST ≤ 4 |
| L4/L5 slots (any) | 0 | dynamically stable |
| Low orbits at Moon/asteroids | 5 | lumpy-gravity stand-in (real lunar frozen-orbit issue) |

---

## 5. Player Interaction & UI

- **Map view** (the main strategic screen): zoomable 2D solar system, true scale with logarithmic zoom assist; conic trajectory lines color-coded per SOI segment; apoapsis/periapsis/AN-free (no nodes in 2D!) markers; encounter entry/exit chevrons; the two next closest-approach markers to a selected target with distance and relative speed.
- **Maneuver-node editor:** click trajectory → place node; drag two handles (prograde/retrograde and radial-in/out); scroll-wheel fine adjust; readouts: Δv, burn time, time-to-node, post-burn periapsis/apoapsis, encounter outcomes. Warning badges: "burn > 1/6 orbit", "insufficient Δv", "node in different SOI".
- **Warp HUD:** ladder bar with current tier, the auto-cap reason shown as a tooltip ("capped: Moon SOI in 00:00:42"), warp-to-event buttons (next node / SOI / periapsis / window).
- **Window Finder:** timeline of departure windows per target with bar height = total Δv from catalog (Table 4.2 baseline) and exact next-window countdown; clicking a window auto-creates the transfer node chain. Alarm clock integration (alarms pause warp).
- **Flyby planner:** when a trajectory enters a body SOI, a periapsis-radius slider + "pass ahead/behind" toggle appears; outbound conic updates live with the turning-angle formula; readout: v∞, δ, heliocentric Δv gained/lost, new apoapsis/periapsis.
- **Ascent HUD:** pitch/γ indicator, q gauge with max-Q band, loss accounting live (gravity/drag/steering), apoapsis target tape. Post-flight report grades the ascent against the loss-accounting identity (3.10; target 8,900–9,300 m/s integrated), with the conservative 9,400 m/s catalog quote shown as the contract baseline.
- **Entry/EDL HUD:** predicted corridor gauge (periapsis altitude vs green band), live q̇ vs TPS limit bar, heat-load integral bar (ablator % remaining), g meter with crew limit bands, predicted post-pass apoapsis during aerobraking/aerocapture. Lift-up/lift-down indicator.
- **Docking HUD:** target-relative velocity vector, port alignment cross, range/range-rate, gates table compliance lamps (green/amber/red per Table in 3.12), fine-RCS mode toggle.
- **Δv budget panel:** stage-by-stage Tsiolkovsky readout (with current Isp from 02), side-by-side with the catalog cost of the planned route; deficit highlighted red before launch, not after.
- **Honesty tooltips:** every abstraction flagged in this doc ([GAME MODEL], L4/L5 note, 2D-drops note, polar surcharge) has an in-UI info card stating what reality does instead. The game teaches real astrodynamics and admits its cuts.

Default controls (keyboard+mouse; pad optional per 12): time warp `,`/`.`, node editor mouse-driven, RCS translate IJKL+HN, rotate AD, throttle shift/ctrl, fine mode CapsLock toggle.

---

## 6. Progression Hooks

| Tier | Unlocks (this domain) | Act usage |
|---|---|---|
| **T0** (2049 baseline) | Manual flight, maneuver nodes, Node Execute, Ascent Guidance, Circularize, Hohmann Planner, AVCOAT ablators, aerobraking *passes* with manual periapsis control | **Act 1:** reach LEO for 9,400 m/s, GTO/GEO commercial contracts, first rendezvous (manual docking), deorbit/recovery |
| **T1** | Window Finder, Rendezvous Sequencer, Autodock, Vacuum Landing, PICA/tiles/steel TPS, Stationkeeping Manager, aerobraking advisor | **Act 1→2:** TLI (3,110), LOI (830), first Moon landing (1,900), reusable boosters change launch economics (12) |
| **T2** | EDL Guidance, **Aerocapture Guidance** (the Act-3 keystone: Mars capture for 50 m/s instead of 2,100), Low-Thrust Spiral, RCC | **Act 3:** Mars windows every 780 d become the campaign heartbeat; NEA prospecting (A1 rows); Phobos/Deimos depots (04/05) |
| **T3** | Tour Planner (multi-flyby), carbon-phenolic TPS (Venus deep entry; ice-giant aerocapture — Jupiter/Saturn entry remains out of scope, 3.11), advanced low-thrust trajectory ops with MPD/VASIMR-class drives (02) | **Act 4:** main-belt logistics on ion spirals; Venus aerostat entries (HAVOC); Jupiter-window assists. **Act 5:** Jupiter capture 450 m/s + moon tours; Titan aerocapture ~100 m/s; Enceladus ops inside a 490 km SOI |
| **T4 [SPECULATIVE]** | Fusion-torch trajectories (02) make non-Hohmann fast transits routine: the planner gains a "constant-acceleration brachistochrone" mode `t = 2·sqrt(d/a)`, Δv = 2·sqrt(d·a) — physics-sound, hardware speculative. Solar-Oberth perihelion maneuver planning for the **interstellar precursor probe** (endgame megaproject: solar Oberth at 0.05–0.1 AU, v∞ > 70–100 km/s; anchor: JHU Interstellar Probe study) | **Endgame** |

Campaign pacing note (for 12): synodic periods are the natural mission cadence — Venus 584 d, Mars 780 d, Jupiter 399 d, Saturn 378 d. Acts 3+ should schedule contract beats against Table 4.3, not arbitrary timers.

---

## 7. Cross-System Interfaces

**02-propulsion.md**
- Consumes from 02: per-engine thrust (kN), Isp (s), throttle range, ullage/restart rules, gimbal authority, RCS thrust; per-propellant densities for tank mass flow.
- Provides to 02: Δv map (4.2) for engine sizing targets; finite-burn/node mechanics (3.7); thrust-warp and Edelbaum spiral-mode rules (3.6) that electric propulsion must satisfy; Oberth/low-thrust cost doctrine (escape ≈ v_c).

**03-solar-system.md**
- Consumes from 03: canonical 2049-epoch elements (a, e, ϖ, τ, s) for every body, μ, radii, rotation periods, surface-site tags (incl. `Polar`), radiation-belt keep-out altitudes, NEA class list.
- Provides to 03: SOI formula and the exact computed values (Table 4.1 — 03 republishes, must not recompute differently); SOI floor rule; atmosphere breakpoint tables 4.4 (03 republishes verbatim); L4/L5 anchor-slot spec (3.13) including trojan-asteroid slot population.

**04-resources-isru.md / 05-industry-logistics.md**
- Consume: Δv map edges as transport-cost inputs; synodic windows (4.3) as logistics cadence; stationkeeping fees (4.8) as recurring RCS-propellant demand; eclipse fraction rule (3.14) for relay/depot siting.
- Provide to me: cargo-vessel mass statements (affects burn times only).

**06-ships-stations.md**
- Consumes from me: g-load and heating loads imposed on structure (3.11), docking capture rules and port approach cones (3.12), TPS catalog (4.5) as part stats, collision rules at contact > 2 m/s.
- Provides to me: per-craft m, C_d·A, L/D, r_n (nose radius), port classes and capture-velocity windows, RCS layouts, structural g-limits.

**07-bases-habitats.md / 10-vehicles.md**
- Consume: landing/ascent Δv rows (M3/M4, R3/R4, A4/A7, S4), polar-site surcharge (X1), descent-profile rules (vacuum suicide-burn vs EDL), Venus aerostat entry profile (V3/V4).
- Provide: lander/ascent-vehicle performance and chute stats.

**08-life-support-crew.md**
- Consumes: g-load exposure events (3.11 defaults; 08 owns final crew tolerance numbers), mission-duration implications of Table 4.3 (a Saturn Hohmann is a 6-year life-support problem), warp-safe analytic consumption requirement (3.6).

**09-power-thermal.md**
- Consumes: eclipse fraction formula (3.14) for solar sizing; reentry heat flux as an external thermal load case; stationkeeping fees imply RCS power draws.
- Provides: power availability for flight computers (programs disabled when unpowered — failure mode 8.11 hook).

**11-research-tech.md**
- Consumes: the program/TPS tier assignments in 4.5/4.7 and the T0–T4 mapping in Section 6 (11 owns the tree layout; these placements are binding).

**12-gameplay-economy-ui.md**
- Consumes: catalog Δv quotes for contract generation; window timeline (4.3) for mission cadence; the worked Earth→Mars example (3.8) as the canonical tutorial; honesty-tooltip content (Section 5).

**13-architecture.md**
- Consumes (binding specs): universal-variable propagator (3.3) incl. tolerances; RK4 50 Hz powered-flight integrator and RKF4(5) prediction (3.5); event-queue + Brent SOI detection (3.4); float64 body-centric frames (3.1, 8.4); warp event-guard semantics and CPU budgets (3.6); numpy-vectorized conic sampling for trajectory rendering (~256 points/conic suggested).

---

## 8. Failure Modes & Edge Cases

1. **Kepler-solver non-convergence (near-parabolic, e ≈ 1).** Universal variables with series-expanded Stumpff functions for |z| < 1e-6 handle this by construction; if Newton stalls (> 100 iters), bisection fallback on the monotonic F(χ) is guaranteed. Never represent orbits as (E, M) classical anomalies internally.
2. **SOI boundary thrashing.** A craft drifting near r_SOI could oscillate frames every tick. Fixed by the 1 %-hysteresis band (3.4) plus a 60 s re-entry lockout (after leaving an SOI, re-entry within 60 s keeps the old frame until clear).
3. **Event tunneling at high warp.** At 1,000,000x a tick spans ~4.6 h sim (at 60 fps render, 10⁶/60 ≈ 16,667 s): a craft could skip an entire SOI or atmosphere. Fixed by *predictive* event detection on rails (3.4) — events are found analytically before warp steps over them; the warp controller clamps the step to the next event time exactly. Numeric (thrust-warp) mode instead caps dt and checks altitude/SOI each substep.
4. **Floating-point precision.** Heliocentric positions reach 4.5e12 m; float64 ULP there is ~0.5 mm — fine — but only because **all dynamic states are body-centric** (3.1) and rails states are stored as elements (a, e, ϖ, τ), which do not accumulate error. Forbidden: storing global Cartesian sums, single-precision anywhere in dynamics, accumulating `t += dt` in float32 (keep t float64 seconds).
5. **Burns spanning SOI changes.** The executor splits the burn at the crossing and re-frames mid-burn; the planner warns ("burn crosses Moon SOI — Δv prediction degraded") because patched-conic impulse math is least accurate there.
6. **Degenerate orbits.** h ≈ 0 (radial plunge), e exactly 1, a → ∞: clamp e to avoid the parabolic razor edge (3.2); radial trajectories propagate fine under universal variables (they are conics with p → 0) but the elements cache stores state vectors directly when e > 0.9999 and |h| below threshold.
7. **Collision during warp.** Rails periapsis < R_body + terrain margin enqueues an impact event (Brent root on r(t) = R_body); warp clamps to it; at 1x, surface impact above 2 m/s destroys parts per 06 rules. No craft ever "warps through" a planet.
8. **Atmosphere skip with warp lockout.** A craft on rails whose periapsis dips below the interface gets an atmosphere-entry event; if the player warps anyway, warp drops at the interface and integration takes over — possibly for many passes (aerobraking). The advisor shows pass count to circularization so the player isn't trapped baby-sitting; "warp-to-next-periapsis" automates multi-pass campaigns.
9. **Propellant exhaustion mid-burn.** Node Execute aborts, flags the node red with achieved-Δv fraction, recomputes the resulting (off-plan) trajectory, and pauses at 1x with an alarm. No silent failures.
10. **Wrong-direction rendezvous.** Opposite-sense (prograde vs retrograde) targets: planner refuses docking solutions, shows closing speed (~15 km/s LEO) and the 2×v_orbit reversal cost. Collisions between counter-rotating constellations are possible and are the player's fault — proximity alarms fire at < 10 km with |v_rel| > 1 km/s.
11. **Unpowered flight computer.** If 09-power says the avionics bus is dead, all programs (incl. Node Execute and warp-to-event autonomy for that craft) are offline; the craft still propagates on rails. Crewed craft retain manual control; uncrewed become derelicts (recoverable — salvage gameplay per 05).
12. **Leaving the Sun's SOI.** Hyperbolic solar escape is allowed (interstellar precursor endgame). Beyond 200 AU the craft enters a "deep space" bookkeeping state (no rendering of further trajectory, telemetry-only); returning is possible if Δv permits. No other star exists; the map simply ends — stated honestly.
13. **Landed-state edge cases.** Landing on a rotating body stores (body, longitude); body rotation rate changes nothing dynamically until launch (analytic). Landing exactly at an SOI-less object (Phobos) is a dock: undocking imparts 0.5 m/s separation, not a ballistic launch.
14. **Patched-conic energy discontinuities.** Frame patches change Jacobi-like invariants slightly; over hundreds of Moon flybys a craft could pump energy unphysically. Mitigation: SOI patch conserves the craft's *velocity relative to the new frame* exactly as sampled at crossing (standard patched conics) and we accept the known few-percent error — documented, not hidden. No invariant-enforcement hacks.

---

## 9. Open Questions

1. **L1/L2 slots in v1 or v1.1?** The spec (3.13) is ready, but Sun–Earth L1/L2 mainly serve telescope/relay flavor; recommend v1.1 unless 12-gameplay wants an early-game science-station contract line. — Needs 12 decision.
2. **Lambert-scan UX depth:** is the 1D window-bar enough, or do players want a full 2-axis (depart × arrive) porkchop heatmap behind an "advanced" toggle? Cheap to add (same solver); UI clutter question for 12.
3. **Mach-dependent C_d and supersonic-retropropulsion penalties** (currently fixed C_d, no SRP penalty): adds realism to Mars EDL sizing; is it worth the part-data burden on 06/10? My recommendation: v1 no, revisit if EDL feels gamey.
4. **Atmospheric variability:** should Mars density vary ±50 % seasonally/dust-storm-coupled (03 owns climate)? It would make aerobraking corridors live operations rather than lookup. Moderate sim cost, high flavor. Leaning yes for Act 3+.
5. **Spiral-mode fidelity:** Edelbaum handles circular↔circular; elliptical low-thrust transfers currently fall back to ≤1,000x numeric warp. Is an averaged-elements propagator (orbit-averaged Gauss equations) worth implementing for big ion freighters? Performance question for 13.
6. **Gravity-assist credit in contracts:** should 12's contract Δv quotes assume Hohmann-only (Table 4.2) or include canonical assist routes (e.g., Mercury via Venus ≈ 2,000 capture)? Recommend quoting Hohmann with an "expert route" bonus payout.
7. **Polar-surcharge value (+500 m/s):** placeholder pending playtest; must be high enough that equatorial sites matter, low enough that lunar polar ice (Act 2 keystone per 04) stays attractive. Tuning owner: 04 + 12 jointly.
8. **N-body flag for a future "Principia mode":** the architecture (body-centric states, event queue) does not preclude swapping the rails propagator for numerical n-body later. Do we reserve save-format headroom for it (13)? Recommend yes — one schema version field.
9. **Eclipse fraction artifact:** 2D over-predicts eclipse time (~0.40 vs ~0.36 real in LEO 300 km). Accept, or apply a 0.9 correction factor in 09's solar sizing? Recommend accept (honesty > polish).
