# BUILD SPEC EXTRACT — 01 Orbital Mechanics & Flight

Source: design/01-orbital-mechanics.md (design-complete draft) + design/DECISIONS.md (overrides).
Purpose: implement without re-reading the original. All units SI in code (m, m/s, kg, N, W, Pa, K); UI may display km/t/kN/kPa.
Epoch t=0 = **2049-01-01 00:00 UTC**, float64 seconds. 2D planar patched conics, body-centric SOI frames only.

DECISIONS overrides in force: C18 (Sun–Earth L1/L2 slots IN v1), C24 (Mars density ±50% seasonal/dust — 03 owns curves),
C25 (1D window bar default + 2-axis porkchop behind "Advanced" toggle), D26 (elliptical low-thrust = numeric ≤1,000x warp,
no averaged-elements propagator unless Phase-4 profiling demands), G35e (reserved save-schema `propagator` field),
A9 (skyhook tip = standard orbital node w/ Δv discount; 01 provides state only), E (polar surcharge +500 m/s stays, tagged [PLAYTEST]).

---

## 1. CANON TABLES

### 1.1 Canonical SOI table (r_SOI = a·(m/M)^(2/5); 03 republishes verbatim, never recomputes)

| Body | Parent | a (km) | Mass (kg) | r_SOI (km) | Notes |
|---|---|---|---|---|---|
| Mercury | Sun | 57.91e6 | 3.301e23 | 112,400 | |
| Venus | Sun | 108.21e6 | 4.867e24 | 616,200 | |
| Earth | Sun | 149.60e6 | 5.972e24 | 924,500 | a-based value fixed |
| Moon | Earth | 384,400 | 7.342e22 | 66,200 | |
| Mars | Sun | 227.94e6 | 6.417e23 | 577,200 | |
| Phobos | Mars | 9,376 | 1.066e16 | (7) → **none** | floor rule: rendezvous object |
| Deimos | Mars | 23,463 | 1.476e15 | (8) → **none** | rendezvous object |
| Vesta | Sun | 353.3e6 | 2.59e20 | 39,300 | |
| Ceres | Sun | 413.8e6 | 9.38e20 | 77,000 | |
| Psyche | Sun | 437.4e6 | 2.29e19 | 18,400 | |
| Jupiter | Sun | 778.57e6 | 1.898e27 | 48,200,000 | |
| Io | Jupiter | 421,800 | 8.932e22 | 7,840 | |
| Europa | Jupiter | 671,100 | 4.800e22 | 9,730 | |
| Ganymede | Jupiter | 1,070,400 | 1.4819e23 | 24,350 | |
| Callisto | Jupiter | 1,882,700 | 1.0759e23 | 37,700 | crew staging (radiation) |
| Saturn | Sun | 1,433.5e6 | 5.683e26 | 54,800,000 | |
| Enceladus | Saturn | 237,948 | 1.080e20 | 490 | passes floor barely (1.5×252=378) |
| Titan | Saturn | 1,221,870 | 1.3452e23 | 43,300 | |
| Uranus | Sun | 2,870.7e6 | 8.681e25 | 51,800,000 | |
| Neptune | Sun | 4,498.4e6 | 1.024e26 | 86,600,000 | |
| Triton | Neptune | 354,759 | 2.139e22 | 12,000 | retrograde: s = −1 |
| Pluto | Sun | 5,906.4e6 | 1.303e22 | 3,150,000 | |

SOI rules: **floor** — if r_SOI < 1.5×R_body → no SOI, no gravity, "rendezvous object" (dock with surface at < 2 m/s).
**Hysteresis** — exit at r > 1.01·r_SOI, entry at r < 0.99·r_SOI, plus **60 s re-entry lockout** after leaving an SOI.
**Detection** — analytic pre-detection on rails: coarse step = min(T_craft, T_body)/64 (bound) or min(T_body, t_exit)/64 (unbound,
t_exit = universal-Kepler TOF to r = r_SOI, or to 2× current radius if outbound past periapsis); refine root of
|r_craft(t) − r_body(t)| − r_SOI = 0 with Brent to ±1 s; post to event queue.

### 1.2 THE CANONICAL DELTA-V MAP (Hohmann reference baseline; impulsive, coplanar, circular↔circular; rounded to 10 m/s)

Canonical parking orbits: **LEO = 300 km, LLO = 100 km, LMO = 250 km, LVO = 250 km**. Legs chain additively
(LEO→Moon surface = M1+M2+M3 = 5,840). Contracts/UI quote these as "catalog Δv".

| # | From → To | Δv (m/s) | Aero option | Notes / anchor |
|---|---|---|---|---|
| E1 | Earth surface → LEO | **9,400** | — | catalog quote; honest sim integrates 8,700–9,300 (see ascent acceptance test §2.10) |
| E2 | LEO → GTO (300×35,786 km) | **2,430** | — | |
| E3 | GTO → GEO | **1,470** | — | coplanar; real 28.5° launches pay ~1,800 (honesty tooltip) |
| E4 | LEO → GEO direct total | **3,900** | — | E2+E3 |
| E5 | LEO → Earth escape (C3=0) | **3,200** | — | |
| E6 | LEO → deorbit | **100** | entry 7.8 km/s | Soyuz ≈ 120 |
| M1 | LEO → TLI | **3,110** | — | Apollo ≈ 3,150 |
| M2 | TLI → LLO (LOI) | **830** | — | Apollo 850–900 |
| M3 | LLO → Moon surface | **1,900** | — | v_circ 1,630 + ~270 losses |
| M4 | Moon surface → LLO | **1,850** | — | Apollo ascent |
| M5 | LLO → Earth return (TEI) | **830** | entry 11.0 km/s | aero to surface |
| M6 | LEO → Earth–Moon L4/L5 slot | **3,950** | — | TLI + full match (no Oberth at slot) |
| L1 | LEO → Sun–Earth L1/L2 slot | **3,250** | — | escape-class + small insertion |
| L2 | LEO → Sun–Earth L4/L5 slot | **3,900** | — | escape + slow heliocentric drift |
| V1 | LEO → Venus transfer | **3,480** | — | v∞ 2.50 |
| V2 | Venus arrival → LVO | **3,330** | **50** (aerocapture T2) | min elliptical capture 360 |
| V3 | Venus arrival → aerostat 50 km | — | **0** (direct entry 10.6 km/s) | HAVOC profile |
| V4 | Venus aerostat 50 km → LVO | **~8,300** | — | [est., 10 owns]; v_circ 7,180 |
| R1 | LEO → Mars transfer (TMI) | **3,590** | — | v∞ 2.95; worked example §2.6 |
| R2 | Mars arrival → LMO | **2,100** | **50** (aerocapture T2) | min just-bound capture 680 (floor); MAVEN flew ~1,230 |
| R3 | LMO → Mars surface (EDL) | **600** | mostly aero | entry ~3.5 km/s from LMO; 5.6 km/s only on direct hyperbolic entry |
| R4 | Mars surface → LMO | **4,000** | — | v_circ 3,430 + losses; MAV 4.0–4.3 |
| R5 | LMO → Earth return (TEI) | **2,100** | entry 11.5 km/s | |
| R6 | LMO → Phobos rendezvous | **1,230** | — | dock-with-surface |
| R7 | LMO → Deimos rendezvous | **1,730** | — | |
| H1 | LEO → Mercury transfer | **5,540** | — | v∞ arr 9.61 |
| H2 | Mercury arrival → 200 km orbit | **7,550** direct | — | with 2–3 Venus/Mercury flybys ≈ **2,000** [route-dependent] |
| A1 | LEO → NEA rendezvous Easy/Typical/Hard | **4,200 / 5,000 / 6,000** | — | total incl. match; return 200–1,000 + aerocapture |
| A2 | LEO → Vesta transfer | **4,520** | — | v∞ arr 4.43 |
| A3 | Vesta arrival → 40 km orbit | **4,200** | — | capture ≈ v∞; low-thrust favored |
| A4 | Vesta orbit ↔ surface | **270** | — | v_circ 240 |
| A5 | LEO → Ceres transfer | **4,890** | — | v∞ arr 4.86 |
| A6 | Ceres arrival → 50 km orbit | **4,550** | — | low-thrust favored |
| A7 | Ceres orbit ↔ surface | **380** | — | v_circ 350 |
| J1 | LEO → Jupiter transfer | **6,300** | — | 2.73 yr; v∞ arr 5.64 |
| J2 | Jupiter arrival → capture ellipse (r_p 200,000 km) | **450** | NO aerocapture (interface ≥ 60 km/s) | Oberth at 36 km/s perijove |
| S1 | LEO → Saturn transfer | **7,280** | — | 6.05 yr; v∞ arr 5.44 |
| S2 | Saturn arrival → capture ellipse (r_p 160,000 km) | **670** | **Titan aerocapture ~100** (T2) | no Saturn-atmo aerocapture (≥ 36 km/s) |
| J3 | Jupiter capture ellipse → Callisto orbit | **1,700** prop / **≈600** moon-assist tour (T3) | — | Galileo-style |
| S3 | Saturn capture ellipse → Titan orbit | **1,200** prop / **≈100** via Titan aerocapture | — | |
| S4 | Titan orbit 1,500 km ↔ surface | down **~150** (chutes) · up **2,400** | — | v_circ 1,480 + ~900 atmo losses [est., 10 owns] |
| S5 | Saturn ellipse → Enceladus orbit | **2,100** (moon assists reduce) | — | |
| U1 | LEO → Uranus transfer | **7,980** | — | 16.0 yr |
| U2 | Uranus arrival → capture ellipse | **550** | — | r_p 30,000 km |
| N1 | LEO → Neptune transfer | **8,250** | — | 30.6 yr |
| N2 | Neptune arrival → capture ellipse | **380** | — | r_p 30,000 km |
| G1 | Gravity-assist credit per flyby | Venus/Earth up to **3,000–5,200** · Jupiter up to **10,700** | — | formula §2.7 |
| X1 | Polar-site surcharge | **+500 per descent AND ascent leg** | — | [GAME MODEL][PLAYTEST]; mechanism §1.12 |

### 1.3 Synodic periods / transfer times / windows (Earth ↔ X, Hohmann)

| Target | Transfer time | Synodic period | v∞ dep (km/s) | v∞ arr (km/s) | Departure phase angle |
|---|---|---|---|---|---|
| Mercury | 105 d | 115.9 d | 7.53 | 9.61 | 108° |
| Venus | 146 d | 583.9 d | 2.50 | 2.71 | −54.0° (trails) |
| Mars | 259 d | 779.9 d | 2.95 | 2.65 | +44.3° |
| Vesta | 398 d | 504.1 d | 5.52 | 4.43 | +71.9° |
| Ceres | 472 d | 466.6 d | 6.31 | 4.86 | +79.0° |
| Jupiter | 2.73 yr | 398.9 d | 8.79 | 5.64 | +97.1° |
| Saturn | 6.05 yr | 378.1 d | 10.29 | 5.44 | +106.1° |
| Uranus | 16.0 yr | 369.7 d | 11.28 | 4.66 | +111.3° |
| Neptune | 30.6 yr | 367.5 d | 11.65 | 4.05 | +113.1° |

### 1.4a Atmospheres — display summary

| Body | Surf P (kPa) | Surf ρ (kg/m³) | H (km) | Interface (km) | Gas |
|---|---|---|---|---|---|
| Earth | 101.3 | 1.225 | 8.5 | **140** | N2/O2 |
| Mars | 0.61 | 0.016 (gas-law 0.0151) | 11.1 | **125** | CO2 |
| Venus | 9,200 | 65.0 | 15.9 | **180** | CO2 (50 km ≈ 1.07 atm, 348 K) |
| Titan | 146.7 | 5.28 | 21 lower / ~50 upper | **850** | N2/CH4 |
| Jupiter | 100 (1-bar datum) | 0.16 | 27 | **1,000 above datum** | H2/He |
| Saturn | 100 (datum) | 0.19 | 59.5 | **1,500 above datum** | H2/He |
| Uranus | 100 (datum) | 0.42 | 27.7 | **1,200** | H2/He; v1.1 |
| Neptune | 100 (datum) | 0.45 | ~20 | **1,000** | H2/He; v1.1 |

### 1.4b Atmosphere breakpoints (SIM TRUTH; ρ kg/m³ at h km; log-linear between; ρ=0 strictly above last anchor)

| Body | Breakpoints |
|---|---|
| Earth | 0:1.225 · 25:4.0e-2 · 50:1.03e-3 · 75:4.0e-5 · 100:5.6e-7 · 120:2.2e-8 · 140:3.9e-9 |
| Mars | 0:1.5e-2 · 25:2.5e-3 · 50:2.8e-4 · 75:1.6e-5 · 100:1.0e-7 · 125:6e-9 |
| Venus | 0:65 · 50:1.6 · 70:9.2e-2 · 100:5e-5 · 130:1e-7 · 180:2e-9 |
| Titan | 0:5.28 · 75:1.5e-1 · 300:1.7e-3 · 600:4e-6 · 850:7e-8 |
| Jupiter | −100:0.6 · 0:0.16 · 200:9e-5 · 500:1.3e-9 · 1000:1e-13 (datum = 1 bar) |
| Saturn | −150:0.5 · 0:0.19 · 300:1.2e-3 · 800:2e-8 · 1500:1e-13 |

**Uranus/Neptune v1 rule:** NO breakpoints ship; the 4.4a interface altitudes still generate atmosphere-entry events and
rails-warp lockout, but any craft crossing the interface is **LOST (destruction zone)** with a planner warning at plot time.
Mars density varies **±50%** with season/dust (DECISIONS C24; 03 owns climate curves) — corridors are live ops from Act 3.

### 1.5 TPS catalog (binding part stats for 06)

| TPS type | Tier | Max flux (MW/m²) | (W/cm²) | Areal mass (kg/m²) | Capacity (MJ/m²) | Reusable | Anchor |
|---|---|---|---|---|---|---|---|
| BareStructure (Al) | — | 0.007 | 0.7 | 0 | — | — | T_eq ≈ 600 K |
| SteelHotStructure | T1 | 0.10 | 10 | +15% dry mass | — | yes | T_eq ≈ 1,150 K |
| ReusableTile (HRSI/TUFROC) | T1 | 0.30 | 30 | 12 | flux-limited | yes | Shuttle tiles 1,260 °C |
| ReinforcedCarbonCarbon | T2 | 0.75 | 75 | 35 | flux-limited | yes | Shuttle RCC ~1,650 °C |
| AVCOAT-class ablator | T0 | 6.0 | 600 | 40 | 2,000 | no | Apollo lunar return |
| PICA-class ablator | T1 | 12.0 | 1,200 | 16 | 800 | no | Stardust 12.9 km/s |
| Carbon-phenolic (HEEET) | T3 | 30 | 3,000 | 60 | 3,000 | no | Venus deep entry, ice-giant aerocapture; Jupiter/Saturn entry OUT OF SCOPE |

Rules: flux-limited shields **fail (destroyed) if q̇_total > q̇_max for > 2 s**. Ablative shields: destruction check uses
**q̇_conv only** vs q̇_max; the f_rad-augmented q̇_total feeds only consumption: ṁ_abl = q̇_total / E_abl per m² of loaded
area, **E_abl = 50 MJ/kg [GAME TUNING]** (Stardust-class entry eats ≈45% of a PICA shield). Loaded area = shield frontal
projected area A_shield (same A as C_d·A); stagnation q̇ applied uniformly (conservative). Shield depleted → structure
takes flux → destroyed at bare-structure limit. Heat load ∫q̇dt (MJ/m²) tracked and displayed (sizes ablators).

### 1.6 EDL / aerocapture corridor rules

- Sutton–Graves constants (q̇ = k·sqrt(ρ/r_n)·v³, W/m²): **k_air = 1.7415e-4** (Earth, N2 bodies incl. Titan);
  **k_CO2 = 1.90e-4** (Mars, Venus); **k_H2He = 3.483e-4** (= 1.7415e-4 × 2.0, gas giants [GAME MODEL]).
- Radiative augmentation: f_rad = 1 for v ≤ 9,000 m/s; f_rad = min(1 + ((v−9000)/3000)², 8) above. Calibration: lunar
  return ≈ 1.45x, Stardust-speed ≈ 2.7x; quadratic valid only 9–13 km/s, hard cap 8 reached near 17 km/s.
- Validation anchor: Stardust v=12.9 km/s, r_n=0.229 m, ρ≈2e-4 kg/m³ → q̇_conv ≈ 1,100 W/cm² (flown ~1,200).
- **g-limits** (defaults; 08 owns final): n = |a_nongrav|/9.80665. Warning n > 7 sustained 5 s; injury n > 12 / 5 s;
  death n > 25 / > 10 s, or n > 45 at any duration. Cargo/structure default 12 g axial / 6 g lateral (06 per-part).
- Allen–Eggers sanity: a_max = v_E²·sin γ_E/(2eH); h(a_max) = H·ln(ρ₀H/(β sin γ_E)). LEO entry 7.8 km/s @ γ 2°, H 8.5 km → ≈ 4.7 g.
- **Aerocapture corridor (T2):** periapsis-altitude window **h_p* ± Δh, Δh ≈ 0.5–1.0 × H_local** (a few km). Post-pass
  apoapsis must land between target and escape. Trim burn after success: **30–100 m/s** (raise periapsis out of atmo).
- Entry-interface speed → TPS class: Titan 6.5–8 km/s (standard ablators, the teaching case); Mars 5.5–7; Venus 10–11
  (PICA-class); Uranus/Neptune 22–25 (carbon-phenolic). **Jupiter ≥ 60 km/s, Saturn ≥ 36 km/s: NO aerocapture, ever**
  (propulsive capture is cheap anyway: J2 = 450, S2 = 670 or ~100 via Titan).
- **Aerobraking** (manual T0; advisor T1): walk periapsis in 2–5 km at a time; per-pass q̇/g/heat-load rules apply; rails
  warp allowed between passes, auto-drop at each interface crossing. T1 advisor overlay: per-pass predicted Δapoapsis,
  peak q̇, peak g, pass count to circularization. "Warp-to-next-periapsis" automates campaigns.
- Skip-out: exit with v > v_esc(local) emerges from integration; planner warns when predicted exit unbound.
- Chute class defaults (per-part (q_max, v_max) owned by 06/10): supersonic DGB q_max ≈ 1 kPa, v_max ≈ 600 m/s;
  subsonic drogues q_max ≈ 15–20 kPa; mains q_max ≈ 3–5 kPa. Opened outside limits → chute part shredded (alarm, no
  other damage). Deployed chutes just add huge C_d·A.
- Lift: per-craft L/D (capsule offset-CG 0.30; spaceplane 1.0+); L = (L/D)·D perpendicular to airspeed; player/autopilot
  selects **lift-up or lift-down** (the whole corridor control). Lift-up stretches (lower g, lower peak q̇, more ∫q̇dt).
- Orbital decay abstraction: LEO 200–500 km pays 2–25 m/s/yr RCS per Table 1.10 curve; above 500 km flat 2 m/s/yr.

### 1.7 Gravity-assist worked cases (formula §2.7)

| Case | v∞ (km/s) | r_p | e_hyp | δ | Max heliocentric Δv |
|---|---|---|---|---|---|
| **Jupiter arrival** | 5.64 | 200,000 km | 1.050 | **144°** | **10.7 km/s** (Act 5 keystone) |
| Earth flyby | 3.0 | 6,578 km | — | 121° | 5.2 km/s |
| Moon (TLI-class) | 0.8–1.0 | — | — | — | ~1.5 km/s free escape boost |

Constraint: r_p ≥ R_body + h_min; **h_min = atmosphere interface + 10 km** (or **50 km** airless); radiation belts may
raise h_min per 03. 2D B-plane = one signed number: periapsis radius + side. **Pass behind body → gain heliocentric
energy; in front → lose.** Moon-tour assists inside Jovian/Saturnian systems cut capture chains 50–80% (T3 Tour Planner).

### 1.8 Rendezvous & docking budgets

Typical post-phasing rendezvous budget: **25–100 m/s**. Approach gates (soft rule; alarms; collisions real):

| Range | Max closing speed |
|---|---|
| 10 km | 30 m/s |
| 2 km | 10 m/s |
| 500 m | 5 m/s |
| 100 m | 2 m/s |
| 30 m | 1 m/s |
| Contact (port) | 0.05–0.30 m/s (port class, 06) |

**Capture condition:** |v_rel| ≤ 0.3 m/s AND axial alignment ≤ 5° AND lateral offset ≤ 0.5 m AND |ω_rel| ≤ 1°/s, inside
the port's 15° approach cone → soft capture, hard dock auto over 10 s. Contact outside limits < 2 m/s: bounce (alarm,
no damage). Contact > 2 m/s: collision damage (06). Rendezvous arrival tolerance: apoapsis within 2 km / 5 m/s of target.
**Direction discipline:** prograde↔retrograde docking refused ("WRONG WAY" banner; closing ~2×v_orbit ≈ 15 km/s LEO);
reversal costs 2×v_orbit. Proximity alarm at < 10 km with |v_rel| > 1 km/s. Autodock (T1) needs docking transponder
part on both vehicles.

### 1.9 Time-warp ladder

| Tier | Rate | Mode | Allowed |
|---|---|---|---|
| 0 | 1x | numeric or rails | always |
| P2–P4 | 2x/3x/4x | physics warp (RK4, 2–4 substeps of dt=0.02) | under thrust/in atmo; **blocked if q > 20 kPa or a_thrust > 30 m/s²** |
| 1–7 | 5x · 25x · 100x · 1,000x · 10,000x · 100,000x · 1,000,000x | rails | coasting, outside atmosphere |

Event guard: no event within **5 real seconds** at current rate; land at 1x exactly **10 s (sim) before node ignition**
and at the moment of SOI/atmo crossing. Rails warp forbidden below atmosphere interface and with clamps released +
engines lit. No per-altitude caps. Background systems integrate analytically per (t_prev, t_now) — binding interface.
**Thrust warp:** numeric up to **1,000x** for burning craft, RKF4(5) rel tol 1e-9, dt capped so a_thrust·dt ≤ 1 m/s;
CPU ≤ 2 ms/frame/craft. **Edelbaum spiral mode** up to **100,000x** when a_thrust < 0.01·g_local (g_local = μ/r² at
current radius), e < 0.05, target coplanar circular same SOI: Δv = |v_c1 − v_c2|, t = Δv/a_thrust; low-thrust escape
≈ v_c1 (ion escape from LEO ~7.7 km/s vs 3.2 impulsive — taught deliberately).

### 1.10 Stationkeeping fees (auto-deducted RCS Δv; Stationkeeping Manager T1)

| Location | Fee (m/s/yr) |
|---|---|
| LEO 200–300 km | 25 |
| LEO 300–500 km | piecewise log-linear through (300:25) · (400:20) · (500:2) |
| LEO > 500 km, MEO, GEO | 2 |
| Sun–Earth L1/L2 slot | 4 |
| L4/L5 slots (any) | 0 |
| Low orbits at Moon/asteroids | 5 |

### 1.11 L4/L5 + L1/L2 anchor slots (patched conics can't do Lagrange — honest cheat, in-UI honesty card)

| Slot | Where | Capture rule | Fee |
|---|---|---|---|
| Sun–X L4/L5 | X's orbit ±60° mean longitude | within 0.01·a_X of center AND v_rel < 100 m/s → snap to rails co-orbit | 0 |
| Earth–Moon L4/L5 | Moon's orbit ±60° | within 20,000 km AND v_rel < 50 m/s | 0 |
| Sun–Earth L1/L2 (v1, C18) | 1.5e6 km sun/anti-sun | within 100,000 km AND v_rel < 50 m/s | 4 m/s/yr |

Slots hold unlimited stations (bookkeeping anchors). Nudge out → ordinary rails. Skyhook (T4 [SPECULATIVE], A9): hub =
ordinary on-rails conic; tip = analytic offset (rotation phase × tether length); catch = standard rendezvous vs tip
state; tip Δv discount 2.4 km/s (05 owns ledger); 01 provides hub elements, tip state, catch-window events only.

### 1.12 Polar-site surcharge mechanism (binding, [GAME MODEL][PLAYTEST])

Trigger: active vehicle crosses 10 km altitude descending toward a `Polar`-tagged site, OR ascent-guidance ignition
lifting off from one. Debit the active stage's propellant: **Δm = m·(1 − e^(−500/v_e))** at current total mass and the
stage's vacuum Isp, applied **linearly over 60 s sim**, exactly once per leg. Planner adds +500 m/s to displayed budget
pre-commitment and **refuses** to initiate the leg if remaining stage Δv < required + 500. Exhaustion mid-debit → normal
propellant-exhaustion rules.

### 1.13 Flight-computer program catalog (unlock via 11; install costs Electronics + MachineParts via 05)

| Program | Tier | Function |
|---|---|---|
| Node Execute | T0 | warp-to-node, finite burn, ±0.1 m/s trim |
| Ascent Guidance | T0 | parameterized gravity turn, max-Q hold, auto-circ |
| Circularize / Apsis Burn | T0 | node generation at apo/peri |
| Hohmann Planner | T0 | Hohmann formulas + phase-window wait |
| Window Finder (Lambert scan) | T1 | departure-date sweep, window bars UI |
| Rendezvous Sequencer | T1 | phasing → transfer → match velocity |
| Autodock | T1 | gates table to capture |
| Vacuum Landing | T1 | suicide-burn + terminal hover |
| EDL Guidance | T2 | corridor hold, chute trigger, terminal retro |
| Aerocapture Guidance | T2 | lift-up/down corridor control |
| Low-Thrust Spiral | T2 | Edelbaum spiral planner |
| Tour Planner | T3 | chained gravity-assist search in a planetary system |
| Stationkeeping Manager | T1 | auto-deduct fees, low-prop alarm |

Unpowered avionics bus (09) → ALL programs offline; rails propagation continues; crewed keeps manual; uncrewed = derelict.

### 1.14 Ascent guidance defaults (Earth; Mars: h_curve 25 km, no q issue; Moon vacuum: immediate pitch-over, h_curve 8 km)

| Param | Default |
|---|---|
| v_pitch_start | 50 m/s |
| h_curve | 60 km |
| pitch law | γ_cmd = 90°·(1 − sqrt(min(1,(h−h₀)/h_curve))), h₀ = pitch-start altitude [ERRATUM: anchored form] |
| q_limit | 35 kPa |
| a_limit | 40 m/s² (~4 g) |
| target_apo | 300 km |
| auto-circ | on |

Rotation credits: Earth **465 m/s** (sidereal 86,164 s); Mars 241; Moon 4.6; Venus 1.8 retrograde (ignored). Retrograde
launch allowed (costs ~930 m/s extra — honest, pointless). Atmosphere co-rotates rigidly; wind = 0 in v1.

### 1.15 Finite-burn / node rules

- Node = (t_node, Δv_prograde, Δv_radial); NO normal component in 2D. Frame = prograde/radial at t_node on predicted trajectory.
- Planner draws trajectory across **up to 5 SOI transitions**; **max 12 chained nodes**.
- Δv readout: Tsiolkovsky with stage awareness; g0 = **9.80665** exactly.
- Burn time t_b = (m0·v_e/F)(1 − e^(−Δv/v_e)); execution **centered on node** (ignite at t_node − t_b/2).
- Warn when t_b > T_orbit/6 ("impulsive approx breaking down"); one-click split into N periapsis-kick burns.
- Always executed as finite burns by the integrator; executor trims to **±0.1 m/s** of planned vector or exhaustion.
- Burn spanning SOI crossing: executor splits at crossing and re-frames mid-burn; planner warns "Δv prediction degraded".
- Exhaustion mid-burn: abort, node flagged red with achieved-Δv fraction, recompute trajectory, pause 1x + alarm.

### 1.16 Integrator & precision rules (binding)

- Powered/atmospheric: fixed RK4 **dt = 0.02 s** (50 Hz) at 1x; gravity = current SOI body only.
- Prediction (node planner, ascent guidance): RKF4(5) adaptive, rel tol 1e-9.
- Thrust ends outside atmo → immediately refit conic, return to rails.
- All dynamic states body-centric float64; rails state stored as elements (a→α=1/a, e, ϖ, τ, s). Forbidden: global
  Cartesian sums, float32 anywhere in dynamics, t accumulation in float32.
- Kepler tolerance |F/√μ| < 1e-8 s, max 100 Newton iters, bisection fallback (F monotonic in χ). Stumpff series |z| < 1e-6.
- Degenerate: clamp e to 0.999999/1.000001 when h ≈ 0; store raw state vectors when e > 0.9999 and |h| below threshold.
- Trajectory rendering: numpy-vectorized conic sampling, ~256 points/conic.
- Collision during warp: rails periapsis < R_body + 5 km margin → impact event (Brent root r(t) = R_body); warp clamps; never tunnel.
- Beyond 200 AU: "deep space" bookkeeping state (telemetry only); return possible; no other star.
- Landed = (body, surface longitude), analytic with rotation. Landing on SOI-less object = dock; undock imparts 0.5 m/s.
- Eclipse/occlusion (binding for 09/05): circular orbit shadow fraction **f = arcsin(R/r)/π** (LEO 300 km: f ≈ 0.40; honest artifact).

---

## 2. FORMULAS (code-ready, SI)

### 2.1 Elements & conversions (element set: μ, a (store α = 1/a), e, ϖ, τ, s = ±1)

```
p = a(1 − e²)                        h = s·sqrt(μp) = x·vy − y·vx
r(ν) = p/(1 + e cos ν)               θ = ϖ + s·ν
v_r = (μ/|h|) e sin ν                v_t = (μ/|h|)(1 + e cos ν)
vis-viva: v² = μ(2/r − 1/a)          ε = v²/2 − μ/r = −μ/(2a)
T = 2π·sqrt(a³/μ)                    state→elements: ε→a; e_vec = ((v²−μ/r)r_vec − (r_vec·v_vec)v_vec)/μ; s = sign(x·vy − y·vx)
```

### 2.2 Universal-variable Kepler (mandatory single propagator; exact at any Δt)

```
r0 = |r0_vec|; vr0 = (r0_vec·v0_vec)/r0; α = 2/r0 − v0²/μ
Stumpff: C(z) = (1−cos√z)/z [z>0] | (cosh√−z −1)/(−z) [z<0] | 1/2 − z/24 + z²/720 [|z|<1e-6]
         S(z) = (√z−sin√z)/√z³ [z>0] | (sinh√−z −√−z)/√(−z)³ [z<0] | 1/6 − z/120 + z²/5040 [|z|<1e-6]
Seeds: elliptic χ = √μ·α·Δt; hyperbolic χ = sign(Δt)√(−a)·ln(−2μαΔt / (r0_vec·v0_vec + sign(Δt)√(−μa)(1 − r0α)));
       parabolic: Barker (Vallado Alg. 8)
Newton on F(χ) = (r0·vr0/√μ)χ²C + (1 − αr0)χ³S + r0χ − √μΔt;  F' = (r0·vr0/√μ)χ(1 − zS) + (1 − αr0)χ²C + r0
converge |F/√μ| < 1e-8 s; ≤100 iters; else bisection (guaranteed). z = αχ².
f = 1 − (χ²/r0)C;  g = Δt − (χ³/√μ)S;  fdot = (√μ/(r·r0))χ(zS − 1);  gdot = 1 − (χ²/r)C
r_vec = f·r0_vec + g·v0_vec;  v_vec = fdot·r0_vec + gdot·v0_vec
```

### 2.3 Hohmann / bi-elliptic / phasing / windows

```
Δv1 = sqrt(μ/r1)(sqrt(2r2/(r1+r2)) − 1);  Δv2 = sqrt(μ/r2)(1 − sqrt(2r1/(r1+r2)));  t = π·sqrt(((r1+r2)/2)³/μ)
Bi-elliptic offered when r2/r1 > 11.94 (slider on intermediate apoapsis r_b; live cost/time trade)
Phasing: T_phase = T_target(1 − Δθ/(2πN))  (Δθ > 0 target ahead → lower/faster orbit), or coast t_wait = φ/(n_chaser − n_target)
Synodic: S = 1/|1/T1 − 1/T2|;  departure phase φ_dep = 180° − n_target·t_transfer  (n = 360°/T, deg/day)
Departure injection (Oberth): Δv = sqrt(v∞² + v_esc²) − v_circ = sqrt(v∞² + 2μ/r_park) − sqrt(μ/r_park)
```

### 2.4 Lambert (Window Finder, T1)

Universal-variable Lambert (BMW ch. 5): iterate on z with the same Stumpff C(z), S(z); 2D — no 180° singularity (plane
fixed); well-conditioned at all transfer angles except exactly 0°/360°. Sweep departure (× arrival) date pairs for total
Δv. Default UI: 1D per-departure-date window bar; full 2-axis porkchop heatmap behind "Advanced" toggle (C25). Prograde
short-way default; long-way behind same toggle. Clicking a window auto-creates the transfer node chain.

### 2.5 Edelbaum / brachistochrone

```
Low-thrust circ→circ (coplanar, same SOI): Δv = |v_c1 − v_c2|;  t = Δv/a_thrust (const-thrust, rocket-eq mass update)
Low-thrust escape from circular: Δv ≈ v_c1
T4 brachistochrone (const accel): t = 2·sqrt(d/a);  Δv = 2·sqrt(d·a)
```

### 2.6 Worked Earth→Mars canon (tutorial; must reproduce)

r1 = 1.000 AU, r2 = 1.524 AU, μ_sun = 1.32712e11 km³/s² (= 1.32712e20 m³/s²). a_t = 1.262 AU; perihelion 32.73 vs Earth
29.78 → v∞ dep 2.95 km/s. From LEO 300 km (v 7,726, v_esc 10,926): Δv_TMI = sqrt(2.95² + 10.93²) − 7.73 = **3,590 m/s**.
Transfer 259 d; Mars sweeps 0.524°/d × 259 = 135.7°; phase angle **44.3°**. Arrival: 21.48 vs 24.13 → v∞ arr 2.65 km/s;
entry interface (125 km) speed sqrt(2.65² + 2μ_M/r) = **5.6 km/s**; propulsive capture to 250 km circ **2,100**; min
just-bound **680**; aerocapture trim **~50**. Windows every **780 d**.

### 2.7 Gravity assist (patched-conic flyby)

```
e_hyp = 1 + r_p·v∞²/μ_body;  δ = 2·arcsin(1/e_hyp);  |Δv_helio| = 2·v∞·sin(δ/2)
constraint r_p ≥ R_body + h_min (interface + 10 km, or 50 km airless; belts per 03)
```

### 2.8 Atmosphere / drag / lift / heating

```
ρ(h) = ρ_i·exp(−(h−h_i)/H_i), H_i = (h_{i+1}−h_i)/ln(ρ_i/ρ_{i+1});  ρ = 0 above interface anchor
D = ½ρv_air²·C_d·A  (v_air relative to co-rotating atmosphere);  β = m/(C_d·A);  a = ½ρv²/β;  v_term = sqrt(2βg/ρ)
L = (L/D)·D ⊥ airspeed, sign = lift-up/lift-down
q̇_conv = k·sqrt(ρ/r_n)·v³;  q̇_total = q̇_conv·f_rad  (k and f_rad per §1.6)
Allen–Eggers: a_max = v_E²·sinγ_E/(2eH);  h(a_max) = H·ln(ρ₀H/(β·sinγ_E))
ablator: ṁ_abl = q̇_total/E_abl per m², E_abl = 50 MJ/kg;  heat load = ∫q̇dt
```

### 2.9 Tsiolkovsky / burns

```
Δv = v_e·ln(m0/m1);  v_e = Isp·g0;  g0 = 9.80665 m/s² exactly
t_b = (m0·v_e/F)(1 − e^(−Δv/v_e));  ignition at t_node − t_b/2;  m_prop = m0(1 − e^(−Δv/v_e))
```

### 2.10 Ascent forces & loss identity (acceptance test)

```
a_vec = (F/m)û_att − (μ/r²)r̂ − (D/m)v̂_air (+ lift)
Δv_gravity = ∫g·sinγ dt;  Δv_drag = ∫(D/m)dt;  Δv_steering = ∫(F/m)(1 − cosα)dt
Δv_total = Δv_orbit_speed + Δv_gravity + Δv_drag + Δv_steering − rotation_credit;  residual must close < 50 m/s
Acceptance: TWR-1.3, 2-stage methalox → 300 km LEO in 8,700–9,300 m/s integrated; gravity 1,100–1,500; drag 50–150;
steering ≤ 100 (2D forced-profile). Catalog quotes 9,400 (contract baseline).
```

### 2.11 SOI / misc

```
r_SOI = a_body·(m_body/M_parent)^(2/5);  floor: none if r_SOI < 1.5·R_body
eclipse fraction (circular): f = arcsin(R/r)/π
closest approach on rails: golden-section minimization of |Δr(t)|; show next two approaches (distance + rel speed)
```

---

## 3. GAP vs CODE

### Implemented and matching spec (verified)

- **Universal-variable Kepler** — `aphelion/sim/orbits/kepler.py`: scalar + vectorized batch, Stumpff series guard,
  Newton + bisection fallback, Barker seed, radial-orbit clamp (0.999999/1.000001), Elements(μ, α, e, ϖ, τ, s),
  state↔elements with elliptic/hyperbolic/parabolic τ. Matches §2.2 fully.
- **SOI machinery** — `aphelion/sim/orbits/soi.py`: Laplace radius, floor rule (1.5×), hysteresis constants
  (1.01/0.99), binding /64 sampling step rules incl. unbound t_exit span, Brent refinement ±1 s, entry/exit predictors.
- **Frames** — `aphelion/sim/orbits/frames.py`: body-centric FrameTree, memoized per-t body states, exact
  subtract/add re-expression at crossings. `ephemeris.py` builds from content packs (with a two-body μ refinement).
- **Trajectory chaining** — `aphelion/sim/orbits/trajectory.py`: patched-conic prediction across ≤ 5 SOI transitions,
  same math as live sim. Drawn in map view with per-frame colors + SOI markers (`main.py`).
- **Transfers** — `aphelion/sim/orbits/transfers.py`: vis-viva, Hohmann, synodic, Oberth departure_dv,
  flyby_deflection (formula only). Earth→Mars canon pinned in `tests/test_pinned_physics.py` / `test_map_intel.py`.
- **Maneuver node** — `aphelion/sim/flight/node_exec.py`: (t, Δv_p, Δv_r), impulsive apply, burn time, centered
  ignition, T/6 impulsive warning, propellant. Node editor UI (N key) with post-burn leg preview in `main.py`.
- **Warp** — `aphelion/core/clock.py`: exact ladder (5x→1e6x), physics substeps 2–4 with q > 20 kPa / a > 30 m/s²
  block, 5-real-second event guard, rails forbidden under thrust/in atmosphere, drift-free int64-step clock.
  Event queue with exact clamps — `aphelion/core/events.py`.
- **Atmospheres** — `aphelion/sim/environment/atmosphere.py`: breakpoint tables byte-identical to §1.4b for
  Earth/Mars/Venus/Titan/Jupiter/Saturn; piecewise-exponential; interface = rails lockout boundary.
- **Entry core** — `aphelion/sim/flight/entry.py`: Sutton–Graves k's (incl. ×2 H2/He), f_rad with cap 8, Allen–Eggers,
  ballistic aeropass integrator with landed/captured/escaped verdict + peak q̇/g. Aerocapture corridor band pinned
  empirically in `tests/test_phase5_environments.py`.
- **Ascent** — `aphelion/sim/flight/ascent.py` + `ascent_live.py`: §1.14 defaults, anchored pitch law (erratum applied),
  q-hold, a-limit, liftoff TWR cap, staging, MECO on predicted apo, auto-circ at true apoapsis, full loss bookkeeping
  with rotation credit, flown live with manual/PROG modes.
- **Descent/landing** — `landing.py` + `descent_live.py`: impulsive deorbit → rails coast → suicide-burn +
  LM-style terminal phase, flown live with autoland; touchdown limit 3 m/s.
- **Docking (flown)** — `proxops_live.py`: Clohessy–Wiltshire LVLH mini-scene, real RCS Δv budget, capture < 2 m/s
  inside 50 m, bounce on hot contact, approach autopilot. (CW dynamics is an extension beyond the doc.)
- **Hohmann window planner** — `main.py` `_transfer_window` + planner UI (P): phase-angle wait, synodic wrap,
  auto-place departure node at window; closest-approach readout (`closest_approach`, line ~873).
- **Freighter route legs price Δv-map edges live** — `aphelion/sim/industry/routes.py` (TLI/LOI, TEI + 50 m/s aero trim).

### MISSING or simplified (the build list)

- **Lambert solver + Window Finder**: no Lambert anywhere; planner is Hohmann-circular-only (`_transfer_window`).
  No 1D Δv window bar, no 2-axis porkchop "Advanced" toggle (C25), no short/long-way, no auto node chain from a scan.
- **Gravity assists as gameplay**: only `flyby_deflection()` exists. No flyby planner UI (periapsis slider,
  ahead/behind toggle, live outbound conic, v∞/δ/Δv readout), no h_min constraint enforcement, no leading/trailing
  sign handling, no Tour Planner (T3), no moon-tour sequencing. The δ=144° Jupiter case is only a test pin.
- **Aerocapture/EDL tooling**: `fly_entry` adjudicates a pass, but there is no corridor computation (h_p* ± 0.5–1.0·H),
  no corridor advisor overlay (per-pass Δapo / peak q̇ / peak g / pass count), no Aerocapture Guidance or EDL Guidance
  programs, no lift (L/D, lift-up/down) — v1 entries are ballistic-only, no skip-out warning in the planner,
  no entry-corridor HUD gauge.
- **TPS system**: Table 1.5 catalog absent. No part-level TPS stats, no flux-limited 2-s failure rule, no
  q̇_conv-vs-q̇_max ablative convention, no ablator consumption (E_abl = 50 MJ/kg) or heat-load integral, no
  bare-structure limits. `main.py` uses a single flat `_CAPSULE_HEAT_W_M2 = 2.5e6` survive/destroy threshold.
- **Chutes**: no parachute parts, no (q_max, v_max) opening constraints, no shred rule; `descent_live.from_entry`
  just starts the powered phase subsonic at 8 km.
- **g-load rules**: peak g is recorded but the crew warning/injury/death thresholds (7/12/25/45 g) and cargo
  12 g axial / 6 g lateral limits are not adjudicated anywhere.
- **Low-thrust support**: no thrust warp (numeric ≤ 1,000x RKF4(5), a·dt ≤ 1 m/s cap), no Edelbaum spiral mode
  (≤ 100,000x), no Low-Thrust Spiral planner, no RKF4(5) adaptive predictor at all (integrator is fixed RK4 only).
- **Node depth**: single node only — no chained nodes (max 12), no node splitting into N periapsis kicks, no
  Node Execute finite-burn executor with ±0.1 m/s trim / mid-burn SOI split / red-flag abort flow (node is applied
  impulsively in `main.py`), no "burn crosses SOI" warning, no warp-stop 10 s before ignition wired to real nodes.
- **Bi-elliptic + phasing planner**: no r2/r1 > 11.94 offer, no r_b slider, no T_phase phasing-orbit tool,
  no Rendezvous Sequencer program.
- **Docking fidelity**: gates table (10 km/30 … 30 m/1, contact 0.05–0.3 m/s), alignment/lateral/ω_rel capture
  condition, 15° approach cone, port classes, transponder requirement, wrong-way (prograde vs retrograde) refusal
  banner — all simplified to range < 50 m AND speed < 2 m/s in `proxops_live.py`.
- **L4/L5 + L1/L2 anchor slots (C18: v1)**: not implemented — no slot entities, capture rules, snap-to-rails,
  honesty card, or trojan content hooks. Skyhook tip-state provider (A9) also absent (T4, can wait).
- **Stationkeeping fees + orbital decay band** (Table 1.10) and Stationkeeping Manager: absent (no auto RCS deduction).
- **Polar-site surcharge X1**: no +500 m/s debit mechanism, no planner refusal, no `Polar` site-tag handling
  (sites exist in `game/sites.py` but carry no surcharge).
- **Uranus/Neptune v1 rule**: no interface altitudes registered (airless in `atmosphere.py`) → no entry events,
  no rails lockout, no destruction zone, no planner warning.
- **Mars ±50% density variation (C24)**: atmosphere is static; no season/dust coupling hook for 03 climate curves.
- **SOI 60 s re-entry lockout** (§8.2): hysteresis constants exist but the lockout timer is not implemented.
- **Eclipse fraction rule** f = arcsin(R/r)/π: not implemented for 09 solar/05 comms (only prose references).
- **Honesty tooltips**: no [GAME MODEL]/2D-drops/L4L5/plane-change info cards in UI (e.g. GTO→GEO 1,470 vs real
  ~1,800 note); spec requires every abstraction to carry an in-UI card.
- **Program catalog as content**: autopilot assists are hardcoded (PROG, autoland, approach AP); they are not
  tiered unlockable programs costing Electronics + MachineParts with the unpowered-avionics failure mode.
- **Misc**: no retrograde-launch choice from pad; no warp-to-event buttons per spec ("warp-to-next-periapsis" for
  aerobraking campaigns); no deep-space > 200 AU bookkeeping state; no brachistochrone/solar-Oberth T4 planner mode;
  no replay/flight-recorder hook in the integrator (DECISIONS C21).
