# 03 — The Solar System & Celestial Bodies

Status: DRAFT v1 for design-bible integration. Owner: solar-system domain. Siblings referenced: `01-orbital-mechanics.md` (delta-v map, patched conics), `02-propulsion.md`, `04-resources-isru.md` (deposits, grades), `05-industry-logistics.md`, `06-ships-stations.md`, `07-bases-habitats.md`, `08-life-support-crew.md` (dose effects), `09-power-thermal.md` (solar/nuclear sizing), `10-vehicles.md`, `11-research-tech.md`, `12-gameplay-economy-ui.md`, `13-architecture.md`.

## 1. Overview

This document is the canonical environment database of the game: every celestial body the player can orbit, land on, mine, or die at, with REAL physical numbers. It owns:

- The **body roster** and master data table: radii, GM, gravity, rotation, atmospheres, temperatures, radiation environments.
- The **2D orbital parameter set** (semi-major axis, eccentricity, period) used by the on-rails Kepler propagator in `01-orbital-mechanics.md`.
- The **environment field models**: solar flux vs distance, atmosphere density profiles, diurnal temperature cycles, radiation dose-rate fields (GCR, solar particle events, planetary belts), Mars dust seasons, comet activity.
- The **surface representation**: how each landable body decomposes into 2D top-down regions (sectors), what differentiates regions, and how many each body gets.
- The **discovery layer**: anomaly sites — real derelict probes, lava tubes, polar cold traps, geological wonders. No aliens, no artifacts; the wonder budget is spent on real places and real human hardware.

Design intent: the solar system is the antagonist. Each body is a boss fight against a different combination of gravity, distance, temperature, pressure, radiation, and dust — and each body's *reward* is a different resource column in `04-resources-isru.md`. Mercury is a thermal puzzle with near-free energy (6.7× Earth solar flux orbit-averaged, 10.6× at perihelion) and an iron-poor crust — the forge that imports its ore. Venus is a floating city in acid. The Moon is logistics school. Mars is the first true colony. Jupiter is a radiation maze with one safe corner (Callisto). Titan is a cryogenic paradise where everything burns except the air.

Out of scope here: transfer delta-v values and SOI-transition math (owned by `01`), deposit tonnage/grade rolls (owned by `04`, with region hooks defined here), thermal/power hardware (owned by `09`), dose biology (owned by `08`).

## 2. Real-World Grounding

Every number in §4 traces to a published source family. Primary anchors:

- **Bulk and orbital data**: NASA/JPL planetary fact sheets and JPL Horizons (J2000 mean elements). IAU 2015 nominal solar values (solar constant 1361 W/m² at 1 AU; GM_sun = 1.32712×10^11 km³/s²).
- **Mercury**: MESSENGER (2011–2015) — polar radar-bright water ice (Prokofiev, Kandinsky craters; 10^14–10^15 kg estimated), hollows, Caloris basin, exosphere ~10^-14 bar. Surface chemistry: XRS/GRS measured crustal Fe of only ~1.5–2 wt% (Weider et al. 2014, Icarus; Evans et al. 2012, JGR) — one of the most iron-poor rocky surfaces known (the planet's metal is in the inaccessible core); the crust is Mg-rich silicate, S-rich (~4 wt%) and volatile-bearing (Na, K).
- **Venus**: Venera 7–14 and Vega landers/balloons (surface 9.2 MPa, 737 K; Venera 13 survived 127 min), Pioneer Venus and Magellan, VIRA reference atmosphere (Seiff et al. 1985) for the 48–62 km aerostat band, NASA HAVOC study (Jones et al. 2015) for 50 km crewed aerostats; Herrick & Hensley 2023 (Science) for active Maat Mons venting.
- **Moon**: Apollo samples, LRO Diviner (equatorial 95–390 K; Hermite crater ~25 K, coldest measured surface in the solar system), LCROSS Cabeus impact (5.6±2.9 wt% water), Lunar Prospector GRS (KREEP thorium), Kaguya/LRO pit discoveries (Marius Hills, Mare Tranquillitatis pits).
- **Mars**: Viking lander pressure series (6.8–9.0 hPa seasonal at VL1), MSL SAM atmospheric composition, MSL RAD dosimetry (cruise 1.84 mSv/day; surface ~0.67 mSv/day, Hassler et al. 2014), MRO SHARAD + SWIM project mid-latitude ice mapping, global dust storm record (2001, 2007, 2018 — the 2018 storm killed Opportunity at optical depth τ > 10).
- **Asteroids/comets**: Hayabusa/Itokawa, Hayabusa2/Ryugu, OSIRIS-REx/Bennu (returned-sample volatile contents), NEAR/Eros, Dawn at Vesta and Ceres (GRaND ice, Occator carbonates, Ahuna Mons), Rosetta/Philae at 67P (density 533 kg/m³, anchoring failure precedent).
- **Jupiter system**: Galileo and Juno; radiation surface-dose anchors widely used in mission literature — Io ~36 Gy/day, Europa ~5.4 Sv/day, Ganymede ~0.08 Sv/day, Callisto ~0.0001 Sv/day (the basis of NASA's HOPE human-outer-planets study choosing Callisto).
- **Saturn system**: Cassini-Huygens — Titan surface 146.7 kPa / 93.7 K (Huygens DISR/HASI), seas by Cassini radar (Kraken Mare ≈ 400,000 km², Ligeia Mare ≈ 126,000 km²), Enceladus south-polar plume ~200 kg/s (Cassini INMS/UVIS), ring composition > 95% water ice.
- **Ice giants / KBOs**: Voyager 2 (Triton geysers, 38 K, 1.4 Pa N2 atmosphere; Miranda's Verona Rupes), New Horizons (Pluto 1.0–1.3 Pa atmosphere, Sputnik Planitia N2 glacier; Arrokoth contact binary).
- **Radiation physics**: MSL RAD and Chang'e-4 LND (lunar surface ≈ 1.37 mSv/day dose equivalent, Zhang et al. 2020); AP8/AE8 Van Allen belt models (qualitatively); CREME/Badhwar-O'Neill GCR solar-cycle modulation.

Honest simplifications (stated once, tagged where used): the world is **2D planar**. All inclinations are flattened to the ecliptic (§3.1 S-2 lists the casualties — Pallas i=34.8°, Pluto i=17.2°, Halley i=162° survive only as eccentricity + direction). Latitude does not exist in the orbit view; polar regions are represented as reserved surface sectors with overridden insolation (§3.6). Axial-tilt seasons are replaced by calendar-driven forcing functions (Mars dust season, §3.8).

## 3. Game Model

All rules carry codes S-1…S-14 for cross-referencing. Units SI. `d` = heliocentric distance in AU unless noted. Time uses game epoch t=0 at 2049-01-01 00:00 UTC.

### 3.1 Two-body elements and the 2D flattening rule (S-1, S-2)

**S-1 (state).** Every body is on-rails on a fixed Kepler ellipse about its primary (planets/asteroids/comets → Sun; moons → planet). Elements per body: semi-major axis `a` [km], eccentricity `e`, period `P` [s] (redundant, P = 2π√(a³/GM_primary), stored for cache), longitude of perihelion `ϖ` [rad], mean anomaly at epoch `M0` [rad], and direction flag `dir ∈ {+1 prograde/CCW, −1 retrograde/CW}`. Position via Kepler's equation `M = E − e·sin E` solved by Newton iteration (tolerance 10^-12 rad, ≤ 8 iterations); radius `r = a(1 − e·cos E)`. Propagator implementation and SOI handoff are owned by `01-orbital-mechanics.md`; this file owns the element *values* (§4.2, §4.3).

**S-2 (flattening).** Real inclinations are set to 0; everything orbits in one plane. Consequences handled explicitly:
- Retrograde real orbits (Triton i≈157°, Halley i≈162°) keep `dir = −1`: they orbit clockwise in-plane. Rendezvous with them is honestly brutal (≈ 2× orbital velocity relative speed), preserving the real difficulty by a different mechanism.
- High-inclination bodies that would otherwise become trivially reachable (Pallas) get NO compensation — we accept the 2D discount and say so in flavor text.
- Pluto's perihelion (29.66 AU) lies inside Neptune's orbit. Reality avoids collision via the 3:2 resonance + inclination; we keep the **resonance phasing**: canonical Pluto M0 = 86.0° / ϖ = 224.1° vs Neptune M0 = 7.0° / ϖ = 45.0° (§4.2) gives a verified minimum separation of 18.3 AU over the full 495-yr synodic cycle (≥ 12 AU guarantee, validated per §8) — and we document the abstraction.
- `ϖ` and `M0` are taken from J2000/Horizons osculating elements propagated to epoch 2049-01-01, then frozen. Real planetary positions in 2049 are approximated within a few degrees — good enough that Halley's 2061-07 perihelion occurs on schedule as a campaign event (S-14).

### 3.2 Gravity, SOI, and surface (S-3)

**S-3.** Each body stores `GM` [km³/s²], mean radius `R` [km], surface gravity `g = GM/R²` (precomputed, m/s²), escape velocity `v_esc = √(2GM/R)` [km/s] (GM and R are the source of truth — see §4.1 note 4 for the fast-rotator equatorial-value caveat), rotation period `T_rot` [s] (negative = retrograde spin), and SOI radius `r_SOI = a·(m/M_primary)^(2/5)` [km] (values in §4.1; formula owned by `01`). Bodies are perfect circles of radius R in the orbit view; terrain exists only in the surface layer (§3.6). Equatorial launch rotation bonus: `v_rot = 2πR/T_rot` is added prograde to any ascent (2D: every launch is "equatorial"; latitude-dependent azimuth penalties are dropped — stated honestly).

### 3.3 Solar flux and light lag (S-4)

**S-4a (flux).** `S(d) = 1361 / d²` W/m², d in AU, evaluated at the body's *current* orbital radius (Mercury's flux therefore swings 6,270–14,450 W/m² over its eccentric orbit — a real gameplay season). Consumed by `09-power-thermal.md` (arrays, radiator sink temps) and §3.5 insolation.

**S-4b (light lag).** One-way comms delay `t = r_line/c`, c = 299,792.458 km/s, r_line = current Euclidean distance between endpoints. Earth–Mars 3.0–22.3 min; Earth–Jupiter 32.7–53.7 min; Earth–Saturn 66.5–90.6 min; Earth–Neptune ≈ 3.9–4.3 h. Consumed by `05-industry-logistics.md` (remote command latency) and `12` (UI). **Solar conjunction blackout**: blackout iff the angular separation between the Sun and the target, *as seen from the observer*, is < 1.0° AND distance(observer→target) > distance(observer→Sun) — superior-conjunction geometry only (a target passing between observer and Sun at small elongation, e.g. Venus inferior conjunction, does NOT occult). Comms drop for the duration (real Mars conjunctions: ~2 weeks every 26 months).

### 3.4 Atmosphere model (S-5)

**S-5a (profile).** Each atmosphere-bearing body stores surface (or datum) pressure `P0` [kPa], temperature `T0` [K], mean molecular mass `μ` [g/mol], scale height `H` [km], and composition (mole fractions, canonical resource names). Above datum:

```
P(h) = P0 · exp(−h/H)        ρ(h) = (P(h)·μ) / (R_gas·T(h))      R_gas = 8.314 J/(mol·K)
T(h) = max(T_min_strat, T0 − L·h)    with lapse L [K/km] per body   [SIMPLIFIED single-layer]
```

The isothermal-H exponential is a deliberate compression of real multilayer atmospheres; H values are fit to the flight-relevant band of each body, and all per-body inputs (μ, H layers, L, T_min_strat, h_atm override, canonical winds) are tabulated in **§4.1b** — a programmer needs no values beyond that table. Two structural fixes keep the model honest:

1. **Venus is two-layer**: H = 15.9 km below the 30-km break, H = 5.5 km above it (anchored to a 60-km datum). The surface-fit 15.9 km alone would be ~4× too dense in the 50–52 km aerostat band and ~5 orders of magnitude too dense at 100 km — fatal for the aerocapture sims `01` builds on ρ(h). Venus additionally stores the §4.4.2 lookup table, extended at data-entry to cover the full entry corridor (45 km → entry interface), which overrides the exponential wherever defined.
2. **Hot extended thermospheres**: above the single-H cutoff `H·ln(P0/P_cut)` (P_cut = 10^-7 kPa) but below the stored per-body **h_atm override** (§4.1b), ρ(h) follows a second exospheric scale height H_upper. This is what makes the real drag environments exist: Earth h_atm = 600 km (so 400-km LEO stations DO decay and must station-keep), Titan h_atm = 1,400 km (Cassini-measured extended thermosphere whose scale height grows to 50+ km aloft). The bare exponential alone would give Earth ≈ 176 km and Titan ≈ 422 km — no LEO decay, no Titan parking-orbit drag, contradicting the realism doctrine.

Drag and aerocapture consume ρ(h) (owned by `01`); intake mining consumes ρ and composition (owned by `04`, M-3e — datum values there MUST match §4.1).

**S-5b (winds).** Single **canonical** scalar per body/band (tabulated in §4.1b; the gust model needs one deterministic w): mean horizontal wind `w` [m/s] for drift of balloons/parachutes, plus gust model `w_gust = w·(1 + 0.5·sin(2πt/τ_g))`, τ_g = 600 s. Canonical values: Venus aerostat band w = 66 (super-rotation; Vega balloons measured ~66 m/s — full circumnavigation ≈ 6 Earth days, which moves an aerostat between day and night sides on that cycle); Mars surface w = 7 clear / 25 in storm-flagged sectors (real range 2–10 / 30+, kept as flavor — at ρ ≈ 0.016 kg/m³ the dynamic pressure is tiny; dust storms threaten power, not structures); Titan surface w = 0.5; Earth w = 8; Triton w = 5.

### 3.5 Insolation, day/night, and surface temperature (S-6)

**S-6a (solar elevation).** A surface site at body-fixed angle φ (sector center) has sun-cosine `c_sun(t) = max(0, cos(φ + 2πt/T_rot − θ_sun(t)))` where θ_sun is the direction to the Sun. Site insolation:

```
I(t) = S(d) · c_sun(t) · f_atm     [W/m²]
f_atm: vacuum 1.0
       · Mars f_atm := f_dust(τ) = max(0.04, exp(−0.45·τ)) (τ from S-9 — this IS the dust attenuation, the direct+diffuse
         panel fit `09` actually needs; it is defined once in S-9 and counted exactly ONCE here; panel soiling is a separate
         multiplier owned by S-9; no /c_sun term anywhere, so there is no c_sun = 0 divide-by-zero to guard)
       · Venus per cloud band (f_atm column in the §4.4.2 band table: 0.30–0.70, +0.15 below-cloud albedo for two-sided arrays)
       · Titan surface 0.10 (≈0.1% of Earth-surface flux: 14.8 W/m² × 0.10 ≈ 1.5 W/m² noon — solar is decoration on Titan)
```

**S-6b (PSR override).** Sectors flagged `PSR` have I = 0 always (permanently shadowed craters). Sectors flagged `PEL` ("peak of eternal light", e.g. Shackleton rim) have I = S(d)·duty with canonical duty = 0.85, world-gen jitter ±0.05, and no T_rot dependence (real LRO illumination mapping; the 2D engine treats them as a special duty-cycle, documented abstraction). **Eclipse rule (single source of truth)**: the moon eclipse fraction f_ecl (§4.3) multiplies into solar availability for ALL assets inside a moon's SOI — orbiting AND landed (an Io solar farm sits in Jupiter's shadow 5.4% of the time; a Phobos surface array 12%) — EXCEPT sectors flagged PSR/PEL, whose insolation override replaces it entirely (mutual exclusion asserted in §8).

**S-6c (surface temperature).** Per sector, diurnal temperature for hardware/habitat loads (`07`, `09`):

```
T_surf(t) = T_night + (T_day − T_night) · c_sun(t)^0.25        (airless bodies; Stefan-Boltzmann day side)
T_surf(t) = T_mean ± ΔT_diurnal/2 · sin(2πt/T_solarday)        (atmosphere bodies; ΔT per §4 tables)
```

T_day/T_night per sector in §4. Venus surface and Titan surface use ΔT ≈ 0 (massive thermal inertia). Special: Io hotspot sectors add stochastic lava events (S-11); Mercury sectors use the 176-Earth-day solar day, enabling the **terminator-chase mechanic**: dawn moves at `v_term = 2πR/T_solarday` = 15,329 km / 176 d ≈ 3.6 km/h at the equator — a rover can outrun sunrise indefinitely (terminator-following rover concept — G. Landis, NASA Glenn Research Center).

### 3.6 Surface representation: sectors and site maps (S-7)

**S-7a (sectors).** Each landable body's surface is partitioned into `N_reg` named **sectors** — angular spans of the body's circumference in the orbit view (the natural 2D mapping). Latitude-flavored regions (poles, PSRs, mid-latitude ice bands) occupy *reserved sectors* with overridden insolation flags (S-6b) — a stated 2D abstraction. Sector record:

```
Sector { id, body, φ_center [deg], arc_deg, terrain_class ∈ {MARE, HIGHLAND, DUNE, ICE_PLAIN, CHAOS, VOLCANIC, PSR, SEA(liquid), CLOUD_BAND(Venus only), REGOLITH_PILE(rubble asteroids)},
         slope_sigma [deg], rock_abundance [0..1], T_day/T_night [K], dust_index [0..1],
         deposit_rolls → 04 §4.2 row references, anomaly_slots [0..3], landing_class ∈ {A..F} }
```

**Layout rule (angular position)**: sectors are laid out CCW from the body's prime meridian in §4.4 list order; unless a §4.4 entry overrides, sector i (0-based) of N_reg has `arc_deg = 360/N_reg` and `φ_center = 360·(i + 0.5)/N_reg`. S-6a consumes φ_center directly — no per-sector angle table is needed.

**Field defaults by terrain_class** — a sector takes these values unless its §4.4 entry states an exception inline (PSR/PEL flags, SEA assignments, hotspots, Medusae Fossae dust_index 1.0, etc.). This defaults-plus-overrides scheme is how all ~176 curated sectors are fully specified without 176 rows:

| terrain_class | slope_sigma [deg] | rock_abundance | dust_index | anomaly_slots | T_day / T_night default [K] |
|---|---|---|---|---|---|
| MARE | 2 | 0.10 | 0.4 | 1 | body §4.1 T-range max / min |
| HIGHLAND | 6 | 0.25 | 0.3 | 1 | (max − 10) / min |
| DUNE | 4 | 0.05 | 0.9 | 1 | max / min |
| ICE_PLAIN | 3 | 0.10 | 0.1 | 1 | max / min |
| CHAOS | 12 | 0.45 | 0.1 | 2 | max / min |
| VOLCANIC | 8 | 0.35 | 0.2 | 2 | max / min (hotspot events S-11 on top) |
| PSR | 8 | 0.20 | 0.1 | 1 | PSR floor / PSR floor (§4.1 PSR value; I = 0) |
| SEA | 0 | 0.00 | 0.0 | 1 | body mean / body mean (liquid thermal inertia) |
| CLOUD_BAND | — | — | 0.0 | 1 | band T from §4.4.2 table |
| REGOLITH_PILE | 15 | 0.60 | 0.8 | 1 | max / min |

Atmosphere-bearing bodies ignore the T_day/T_night columns and use S-6c's `T_mean ± ΔT_diurnal/2` with ΔT_diurnal from §4.1b (Mars 70 K default, modulated 60–100 K by sector dust_index; Venus/Titan/Triton ≈ 0; Earth 10 K).

Counts (sector NAME lists in §4.4; all other fields from the defaults table + inline overrides): Mercury 10, Venus 8 surface + 4 cloud bands, Earth 12, Moon 14, Mars 18, Phobos 3, Deimos 2, Ceres 8, Vesta 6, Psyche 5, generic belt/NEA 1–3, Io 8, Europa 8, Ganymede 10, Callisto 10, Titan 12, Enceladus 6, Miranda 4, Titania 4, Oberon 3, Triton 6, Pluto 6, Charon 4, comets 2–3. Total curated sectors ≈ 176.

**S-7b (landing class).** A = airless, g < 0.05 m/s² (dock, don't land; anchoring rule S-12); B = airless, landable with rockets only; C = thin atmosphere (Mars: too thick to ignore, too thin to land on chutes alone — EDL needs heat shield + retropropulsion); D = thick benign atmosphere (Titan: chutes alone suffice, Huygens precedent); E = extreme (Venus surface: survivable minutes-to-hours without T3 refractory tech); F = no surface (gas/ice giants: atmosphere-skim and probe drops only). **EDL dispersion (base mechanic)**: touchdown offset from the targeted point is drawn N(0, σ) along the sector arc, with σ_base per landing class: B 0.2 km, C 5 km, D 20 km. S-9 storms multiply σ ×2; S-13 comet activity ×(1 + 0.2·A). `01-orbital-mechanics.md` consumes σ in its EDL model; this file owns the base values and multipliers.

**S-7c (site maps).** Landing in a sector instantiates a procedural local top-down tile map (engine details in `13-architecture.md`) seeded by `(body, sector, slot)` with terrain parameters from the sector record: slope obstacles ∝ slope_sigma, rock density ∝ rock_abundance, deposit overlay g(d) from `04` M-1a, and anomaly site tiles if discovered. Sites are persistent once instantiated.

### 3.7 Radiation environment (S-8)

This file owns the **environmental field**; biological/shielding response is owned by `08-life-support-crew.md`. All values are unshielded ambient dose-equivalent rates in mSv/day (one labeled exception: the Earth belt field in S-8c is behind-hull effective dose).

**S-8a (GCR).** `D_gcr(d, t) = 1.8 · f_cycle(t)` mSv/day in free space anywhere in the system (GCR is nearly flat with heliocentric distance at game fidelity; anchor: MSL RAD cruise 1.84 mSv/day). Solar-cycle modulation `f_cycle = 1.0 − 0.35·cos(2π(t − t_max)/11 yr)` — equals 0.65 AT solar maximum t_max and 1.35 at minimum (range 0.65–1.35; GCR anti-correlates with solar activity; the real ~6–12-month GCR lag after maximum is below game fidelity). Bodies with thick atmospheres or magnetospheres override: Earth surface 0.01, Venus 52 km 0.03, Titan surface 0.01 (column mass P/g ≈ 109 t/m² ≈ 10,900 g/cm² — ten times Earth sea level's 1,033 g/cm²), Mars surface 0.67 (MSL RAD), Moon surface 1.37 (Chang'e-4 LND). Half of the sky is rock on any surface; the listed surface values already include that.

**S-8b (SPE — solar particle events).** Poisson process, rate `λ = 0.5 + 3.5·max(0, cos(2π(t−t_max)/11 yr))` events/year (4.0/yr AT solar max t_max, 0.5/yr at min). Event unshielded free-space dose at 1 AU: lognormal, median 100 mSv, σ_ln = 1.2, capped 2,000 mSv (Carrington-class tail), delivered over 6–48 h. Scales as `1/d²`. Mercury ops take ≈6.7× Earth SPE dose; Jupiter takes 0.037×. Warning time: 30–60 min game-time after flare flag (real SEP onset physics) — the "run to the storm shelter" mechanic for `07`/`08`.

**S-8c (planetary belts).** Earth: Van Allen dose field, expressed as **effective dose behind a nominal 5 g/cm² hull [SIMPLIFIED from AP8/AE8]** — truly unshielded skin dose at the inner-belt peak is Gy/day-class, one to two orders higher; `08` applies habitat shielding on top of this hull baseline. Piecewise in geocentric radius r [R_E]: 0 below 1.1; linear rise to **150 mSv/day peak at 1.6 R_E** (inner proton belt); fall to 10 at 2.5; second hump **50 mSv/day at 4.5 R_E** (outer electron belt); → 0 at 8 R_E. A chemical transit spends hours in the belts (~1–5 mSv/pass); an electric-propulsion spiral spends weeks (Sv-class — the real reason SEP cargo tugs fly uncrewed; gameplay teeth for `02`/`08`).

Jupiter: anchored exponential in jovicentric radius r [R_J = 71,492 km]:

```
D_jup(r) = 5,400 · exp(−(r − 9.4)/1.6)  mSv/day   for 6 ≤ r ≤ 30, clamped to ≤ 36,000 at r ≤ 6; D_jup := 0 for r > 30
Total jovicentric ambient anywhere in the SOI: D = D_gcr (S-8a) + (r ≤ 30 R_J ? D_jup(r) : 0)
Anchors reproduced: Io (5.9 R_J) ≈ 36,000 (≈36 Gy/day) · Europa (9.4 R_J) = 5,400 (5.4 Sv/day)
                    Ganymede (15.0 R_J) ≈ 160 vs cited ~80 (within model honesty band) · Callisto (26.3 R_J) ≈ 0.14
```

Ganymede's intrinsic magnetic field (the only moon with one) halves its ambient value → use 80 mSv/day at Ganymede's surface, matching literature. Saturn's belts are mild and absorbed by the rings: 1.0 mSv/day inside 8 R_S, 0 beyond; Titan (21.0 R_S) is outside entirely. Time-integrated dose bookkeeping is `08`'s job; this field function is evaluated per simulation tick.

### 3.8 Mars dust seasons (S-9)

Solar longitude `Ls ∈ [0°, 360°)` is computed from world state as **`Ls = (ν + 251°) mod 360°`**, where ν is Mars's true anomaly [deg] from the on-rails propagator (S-1) and 251° is the real perihelion-to-Ls offset (Mars perihelion occurs at Ls ≈ 251°); Ls(t=0) follows from Mars's §4.2 M0. It advances over the 668.6-sol Mars year (sol = 88,775 s) *non-uniformly*, as it should — e = 0.0934 makes southern spring/summer shorter and hotter (real). Optical depth τ per sector:

```
τ_base = 0.3 (Ls 0–180, northern spring/summer) · 0.5 (Ls 180–360)
Regional storms: in Ls 180–330, each sector rolls p = 0.004/sol to spawn a storm: τ → 2.0–4.0 over 2 sols,
   duration U(5, 40) sols, spreads to adjacent sectors with p = 0.15/sol.
Global storm: once per Mars year at Ls = 200°±30°, p = 0.33 (≈1 per 3 Mars years; anchor: 2001/2007/2018):
   ALL sectors τ → U(4, 9) over 10 sols, duration U(60, 100) sols, decay e-fold 25 sols.
Solar panel factor (direct+diffuse, game fit to Appelbaum & Flood / Opportunity 2018): f_dust = max(0.04, exp(−0.45·τ))
   — this IS Mars's f_atm in S-6a: defined once here, applied exactly once (global-storm τ = 4–9 → f_dust ≈ 0.165–0.04).
Panel soiling: −0.2%/sol output (clear), −2%/sol (storm); restored by crew/rover cleaning task or wind cleaning event p = 0.005/sol (Spirit/Opportunity precedent).
```

Storms also raise EDL dispersion (σ ×2 on the S-7b base landing dispersion) and block surface↔orbit optical scans (survey S-10 paused). Pressure seasonal swing: `P_site(t) = P_datum·(1 + 0.15·sin(2π(Ls−250°)/360°))` [SIMPLIFIED two-term real cycle; anchor VL1 6.8–9.0 hPa] — affects intake mining rate (`04` M-3e) and EDL.

### 3.9 Survey & discovery (S-10)

Three knowledge layers per body, integrating with `04` M-2's deposit K-ladder:

```
L0 ephemeris-only (everything starts here except Earth/Moon/Mars = L1 from real data)
L1 mapped: orbital survey complete → sector list + terrain classes + anomaly *pings* visible
L2 prospected: per-sector rover/lander work → deposits to K2, anomaly pings resolved to sites
Orbital survey progress: C(t) += (w_swath · v_orb)/(4πR²) per s while alt < h_scan and instrument powered
   (w_swath and h_scan per instrument, 04 §4.3; full map at C = 1 → typ. 5–30 orbits)
Anomaly slots: each sector has 0–3; curated anomalies (real probes/wonders, fixed) fill listed slots; remaining
   slots roll procedural finds at world-gen: P(lava tube)=0.06, P(ice lens)=0.10, P(geode/ore vug)=0.08, P(empty)=rest.
Rewards: SurveyData [GB] per anomaly class (§4.6); anomaly investigation additionally awards Science at the
   canonical 2 SCI/GB conversion (§4.6, co-signed 11 §3.5); some yield salvage
   (e.g. Pu238 from derelict RTGs — masses in §4.5 table, ledger in 04).
Science regions: the survey/sample region partition and per-region exoticism X consumed by 11 (§3.1, §3.5, §3.7)
   are owned here and cataloged in §4.7 — sectors carry a region_id; 11 keys its Science pools to those IDs.
```

### 3.10 Small-body surface ops (S-11, S-12)

**S-11 (spin barrier & hazards).** Rubble-pile asteroids cannot spin faster than the ~2.2 h cohesionless limit; world-gen enforces `T_rot ≥ 2.2 h` for D > 300 m rubble piles; monolith fragments below 300 m may spin to 0.1 h (flagged DANGER: docking relative speeds). Io volcanic sectors: eruption events Poisson 1/(30 d) per volcanic sector; plume reaches 300–400 km altitude (Tvashtar/Pele class); ballistic ejecta strike chance for surface assets within the sector p = 0.02 per event (damage roll to `07` structures). Enceladus plume sectors: continuous vapor+ice jet, total source ≈ 200 kg/s (Cassini); flying through the plume below 100 km yields free SurveyData and hull erosion 0 (benign), landing astride a tiger stripe grants direct vent-water capture ≤ 5 kg/s per collector (cap before it outpaces just melting the ice everywhere else).

**S-12 (anchoring).** If local `g < 0.01 m/s²` (Phobos-class and below) every surface structure/vehicle requires anchor hardpoints (harpoon/auger, MachineParts cost in `05`); unanchored objects drift off on any actuation impulse > m·v_esc_local. Philae's bounce is the canonical cautionary tale. Comet surfaces additionally roll anchor failure p = 0.1 per anchor in low-cohesion ice (re-anchor task).

### 3.11 Comet activity (S-13)

Active comets inside 3 AU emit gas/dust. Activity index `A(d) = clamp((3.0/d)² − 1, 0, 8)` (zero outside 3 AU, ~8 near 1 AU). Effects: optics/array abrasion −0.5%·A per day on surface or within 50 km; landing dispersion ×(1+0.2A); free volatile capture: a coma scoop within 10 km of the nucleus collects `0.2·A` kg/h of Water-equivalent ice (flavor-scale, not industrial). Non-gravitational orbit drift is NOT modeled (on-rails) — stated simplification.

### 3.12 Scheduled celestial events (S-14)

World-clock events (campaign texture, fixed at world-gen): Halley's perihelion 2061-07-28 (comet becomes reachable showpiece; unique SurveyData jackpot); Mars global storm rolls (S-9); solar cycle maxima ≈ 2057 and 2068, ±2 yr world-gen jitter (S-8; phased from the observed Solar Cycle 25 maximum of October 2024 on an 11-yr ladder — 2035, 2046, 2057, 2068; the 2046 maximum just pre-dates the 2049 start, so the campaign opens in a maximum's declining phase); Mars/Venus/Jupiter launch windows recur per synodic periods 779.9 d / 583.9 d / 398.9 d (computed, surfaced by `01`'s porkchop UI; listed here because the calendar is world state).

## 4. Content Catalog

### 4.1 Master body data table

Mean radius R; g and v_esc at R; T_rot negative = retrograde spin; radiation = unshielded ambient surface/ambient value from S-8 (mSv/day) before habitat shielding (`08`). "Δv ref" values are owned by `01-orbital-mechanics.md` — indicative numbers here are for sanity only. PSR = permanently shadowed regions.

| Body | R [km] | GM [km³/s²] | g [m/s²] | v_esc [km/s] | T_rot | Atmosphere (surface P, main gases, H) | T range [K] | Radiation [mSv/d] | r_SOI [km] | Key resources (04) | Indicative surface↔low-orbit Δv |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Sun | 695,700 | 1.32712×10^11 | 274 | 617.5 | 25.4 d | — | — | — | — | — | not landable |
| Mercury | 2,439.7 | 22,032 | 3.70 | 4.25 | 58.646 d (solar day 176 d) | exosphere ~10^-12 kPa (~10^-14 bar) | 100–700 (PSR ~50) | 1.8·f_cyc + 6.7× SPE | 1.12×10^5 | polar Water; Mg-silicate Regolith → Silicon, Oxygen, Glass; sulfide volatiles (S ~4 wt%); crustal Fe only 1.5–2 wt% (MESSENGER) | ≈ 3.2 km/s |
| Venus | 6,051.8 | 324,859 | 8.87 | 10.36 | −243.02 d (solar day 116.8 d) | 9,200 kPa CO2 96.5/N2 3.5, H=15.9 km below 30 km / 5.5 km above (§4.1b; §4.4.2 band lookup overrides) | 737 surface (uniform); ~293–350 at 50–56 km | 0.03 (52 km) | 6.16×10^5 | CO2, N2 (atm); surface basalt | aerostat→orbit ≈ 8.3 km/s; surface ascent unsupported pre-T3 |
| Earth | 6,371.0 | 398,600 | 9.81 | 11.19 | 23.934 h | 101.325 kPa N2 78.1/O2 20.9/Ar 0.9, H=8.5 km | 184–330 (mean 288) | 0.01 surf; belts S-8c | 9.24×10^5 | everything, at a price (12) | 9.4 km/s incl. losses (canon) |
| Moon | 1,737.4 | 4,902.8 | 1.62 | 2.38 | 27.322 d sync (solar day 29.53 d) | none | 95–390 eq; PSR 25–40 | 1.37 | 66,200 (of Earth) | PSR Water, ilmenite O2/Ti/Fe, anorthite Al/Si, KREEP Th/U, He3 [SPECULATIVE] | ≈ 1.9 km/s |
| Mars | 3,389.5 | 42,828 | 3.71 | 5.03 | 24.623 h (sol 88,775 s) | 0.61 kPa datum CO2 96.0/Ar 1.93/N2 1.89 (MSL SAM molar), H=11.1 km | 130–308 (mean 210) | 0.67 | 5.77×10^5 | atm CO2, mid-lat Water ice, Fe-oxides, hydrated minerals | ≈ 4.0 km/s up (EDL down ≈ 1 km/s propulsive after aero) |
| Phobos | 11.1 (27×22×18) | 7.11×10^-4 | 0.0057 | 0.011 | 7.66 h sync | none | 130–300 | 0.7 (Mars shadowing) | ≈7.3 — BELOW the 11.1 km mean radius: no orbits exist, dock mode only | Regolith; Water 0–5 wt% (unresolved — survey!) | dock; ≈ 5 m/s touch/go |
| Deimos | 6.2 | 9.8×10^-5 | 0.003 | 0.0056 | 30.3 h sync | none | 130–290 | 0.9 | ~9 | as Phobos | dock |
| Ceres | 469.7 | 62.6 | 0.28 | 0.51 | 9.07 h | transient H2O exosphere ~0 | 110–235 | 1.8·f_cyc | 77,000 | Water ice 20–45 wt% crust, ammoniated clays, carbonates | ≈ 0.37 km/s |
| Vesta | 262.7 | 17.3 | 0.25 | 0.36 | 5.342 h | none | 85–270 | 1.8·f_cyc | ~40,000 | basaltic crust: Silicon, Aluminum, IronSteel | ≈ 0.27 km/s |
| Psyche | 111 (mean D 222) | 1.53 | 0.12 | 0.16 | 4.196 h | none | 80–280 | 1.8·f_cyc | ≈18,400 | metal-rich mixed body, ~30–60 vol% metal (bulk density 3,980 kg/m³ rules out solid NiFe; orbiter survey resolves grade): IronSteel, RareEarths (PGM residue) | ≈ 0.14 km/s |
| Hygiea | 217 | 5.83 | 0.124 | 0.232 | 13.83 h | none | 100–250 | 1.8·f_cyc | ≈33,800 | C-type outer belt: Water-bearing clays, Carbon | ≈ 0.18 km/s |
| Jupiter | 69,911 | 1.26687×10^8 | 24.8 | 59.5 | 9.925 h | gas giant, H2 89/He 11 (1-bar T = 165 K) | — | belt field S-8c | 4.82×10^7 | Hydrogen, He3 [SPECULATIVE T4 scoop] | class F — no surface |
| Io | 1,821.6 | 5,959.9 | 1.80 | 2.56 | 1.769 d sync | SO2 traces ~10^-9 kPa | 90–130 bg; hotspots to 1,900 | ≈ 36,000 | 7,840 | sulfur, silicates [mostly a hazard showcase] | ≈ 2.0 km/s (v_orb 1.76 + margin, consistent with the other Galileans) |
| Europa | 1,560.8 | 3,202.7 | 1.31 | 2.02 | 3.551 d sync | O2 trace ~10^-9 kPa | 50–110 | 5,400 | 9,730 | Water (ice shell 15–25 km over 60–150 km ocean) | ≈ 1.6 km/s |
| Ganymede | 2,634.1 | 9,887.8 | 1.43 | 2.74 | 7.155 d sync | O2 trace | 70–152 | 80 (own B-field) | 24,350 | Water ice + rock; largest moon | ≈ 2.0 km/s |
| Callisto | 2,410.3 | 7,179.3 | 1.24 | 2.44 | 16.689 d sync | CO2 trace | 80–165 (mean 134) | 0.14 + GCR | 37,700 | Water ice, rock; THE jovian base site (NASA HOPE) | ≈ 1.8 km/s |
| Saturn | 58,232 | 3.79312×10^7 | 10.4 | 35.5 | 10.66 h (System III; interior fits ~10.56) | gas giant H2/He (1-bar T = 134 K) | — | 1.0 inside 8 R_S | 5.48×10^7 | Hydrogen, He3 [SPECULATIVE] | class F |
| Titan | 2,574.7 | 8,978.1 | 1.35 | 2.64 | 15.945 d sync | 146.7 kPa (1.45 atm) N2 94.5/CH4 5 near-surface, H≈20 km | 90–94 (93.7 Huygens) | 0.01 (atm column ≈10,900 g/cm² — 10× Earth's 1,033) | ≈43,300 | Methane seas (+[LUMPED] ethane), N2 atm, Water bedrock | ≈ 2.4 km/s up (drag-heavy); chute descent ~free |
| Enceladus | 252.1 | 7.21 | 0.113 | 0.239 | 1.370 d sync | plume-fed vapor ~0 | 33–145 (stripes to ~197) | 1.0 | ≈490 | Water (plume + crust), south-polar vents | ≈ 0.18 km/s |
| Uranus | 25,362 | 5.7939×10^6 | 8.87 | 21.3 | −17.24 h | ice giant H2/He/CH4 (1-bar T = 76 K) | — | mild belts 0.5 | 5.18×10^7 | Hydrogen, He3 [SPECULATIVE — lowest-v_esc giant, classic He3 target] | class F |
| Titania | 788.9 | 228.3 | 0.37 | 0.76 | 8.706 d sync | none | 60–89 | 0.5 | ≈7,540 | Water ice, rock | ≈ 0.55 km/s |
| Oberon | 761.4 | 192.4 | 0.33 | 0.71 | 13.46 d sync | none | 60–89 | 0.5 | ≈9,430 | Water ice, rock | ≈ 0.55 km/s |
| Miranda | 235.8 | 4.4 | 0.079 | 0.193 | 1.413 d sync | none | 60–86 | 0.5 | ~500 | ice; Verona Rupes wonder | ≈ 0.15 km/s |
| Neptune | 24,622 | 6.8365×10^6 | 11.15 | 23.5 | 16.11 h | ice giant (1-bar T = 72 K) | — | mild belts 0.5 | 8.66×10^7 | Hydrogen, He3 [SPECULATIVE] | class F |
| Triton | 1,353.4 | 1,428 | 0.78 | 1.46 | 5.877 d sync RETROGRADE | 0.0014–0.0019 kPa N2 | 38 | GCR 1.8·f_cyc | 12,000 | N2 ice, Water ice, CH4 frost; geysers | ≈ 1.0 km/s |
| Pluto | 1,188.3 | 869.6 | 0.62 | 1.21 | 6.387 d sync w/ Charon | 0.0010–0.0013 kPa N2 | 33–55 (mean ~44) | GCR | 3.1×10^6 (heliocentric) | N2/CH4/CO ices, Water-ice bedrock | ≈ 0.85 km/s |
| Charon | 606.0 | 105.9 | 0.288 | 0.59 | 6.387 d sync | none | 53 max | GCR | ≈8,440 | Water ice | ≈ 0.42 km/s |
| Bennu (NEA, B/C) | 0.245 | 4.9×10^-9 | 6×10^-5 | 2×10^-4 | 4.296 h | none | 240–330 | 1.8·f_cyc | ~0.1 (dock) | Water ~8 wt% phyllosilicates, Carbon, Nitrogen | dock (S-12 anchors) |
| Ryugu (NEA, C) | 0.448 | 3.0×10^-8 | 1.5×10^-4 | 3.7×10^-4 | 7.63 h | none | 230–330 | 1.8·f_cyc | dock | as Bennu | dock |
| Eros (NEA, S) | 8.4 (34×11×11) | 4.46×10^-4 | 0.0059 | 0.0103 | 5.27 h | none | 170–310 | 1.8·f_cyc | dock | NiFe grains, Silicon | dock |
| Itokawa (NEA, S rubble) | 0.165 | 2.1×10^-9 | ~10^-4 | 1.7×10^-4 | 12.13 h | none | 200–330 | 1.8·f_cyc | dock | rubble regolith | dock |
| Apophis (NEA, S) | 0.17 | 4.0×10^-9 | 1.4×10^-4 | 2.2×10^-4 | 30.6 h (tumbler, simplified) | none | 230–340 | 1.8·f_cyc | dock | S-type silicates; 2029-flyby celebrity (Prestige) | dock |
| 67P (comet) | ~2.0 bilobed | 6.7×10^-7 | ~2×10^-4 | ~0.001 | 12.40 h | coma when active (S-13) | 130–230 active | 1.8·f_cyc | dock | Water/CO2/CO ice, Carbon organics, dust | dock; anchor p_fail 0.1 |
| Halley (comet) | ~5.5 (15×8×8) | ~1.5×10^-5 | ~4×10^-4 | ~0.002 | 52.8 h (complex spin simplified) | strong coma near perihelion | 130–350 active | 1.8·f_cyc | dock | as 67P; prestige target 2061 | dock; retrograde rendezvous! |
| Arrokoth (KBO) | ~9 (36 km contact binary) | ~3×10^-5 | ~10^-3 | ~0.003 | 15.9 h | none | 30–60 | GCR | dock | primordial ices, organics | dock |
| Eris (KBO dwarf) | 1,163 | 1,108 | 0.82 | 1.38 | 15.8 d sync w/ Dysnomia | collapsed N2/CH4 frost | 30–55 | GCR | large | N2/CH4 ice | ≈ 0.95 km/s |

Notes: (1) Asteroid/comet GM below ~10^-3 km³/s² means orbital speeds slower than a walk; the engine treats g < 0.01 m/s² bodies in "dock mode" (`01`/`06`) — you station-keep, you don't orbit-and-land. (2) Saturn's ring particles and minor moons are not individually simulated; rings are a zone object (§4.4.10). (3) Galilean radiation values are the standard mission-literature surface anchors; Io's is an absorbed-dose figure (~36 Gy/day) used as Sv-equivalent ceiling [SIMPLIFIED]. (4) **Column convention**: GM and mean R are the source of truth. For the fast-rotating giants and Bennu, the g and v_esc columns are *published equatorial values* (including rotational reduction) shown for reference; the engine MUST derive g = GM/R² and v_esc = √(2GM/R) from the stored columns per S-3 — which yields Jupiter 25.9 m/s² / 60.2 km/s, Saturn 11.2 / 36.1, Uranus 9.0 / 21.4, Neptune 11.3 / 23.6, Bennu 8.2×10^-5 m/s² — and unit tests must assert against the derived values, not this column.

### 4.1b Atmosphere profile & wind parameters (complete S-5a/S-5b input set — no values beyond this table are needed)

| Body | P0 [kPa] (datum) | T0 [K] | μ [g/mol] | H [km] (lower layer) | layer break h_break [km] | H_upper [km] | L [K/km] | T_min_strat [K] | h_atm stored override [km] | ΔT_diurnal [K] | canonical w [m/s] |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Venus | 9,200 (surface) | 737 | 43.45 | 15.9 | 30 | 5.5 (60-km datum anchor; §4.4.2 lookup overrides 45–65 km+corridor) | 7.7 (below 60 km) | 230 (band top) | 350 | ≈0 (massive thermal inertia; band-level day/night handled by super-rotation drift S-5b) | 66 (aerostat band) |
| Earth | 101.325 | 288 | 28.97 | 8.5 | 120 | 60 (hot thermosphere) | 6.5 | 217 | 600 — LEO decay/station-keeping exists | 10 | 8 |
| Mars | 0.61 | 210 | 43.34 | 11.1 | 100 | 25 | 2.5 | 130 | 250 | 70 default (60–100 by sector: ΔT = 100 − 40·dust_index) | 7 clear / 25 storm |
| Titan | 146.7 | 93.7 | 28.0 | 20 | 300 | 65 (Cassini hot extended thermosphere) | 1.0 (lowest 10 km) | 70 | 1,400 | ≈2 | 0.5 |
| Triton | 0.0014–0.0019 | 38 | 28.0 | 14.5 | — | — | 0 [near-isothermal approx] | 38 | 800 | ≈0 | 5 |
| Pluto | 0.0010–0.0013 | 44 | 28.0 | 21 | — | — | 0 [real inversion ignored, SIMPLIFIED] | 44 | 1,600 | ≈0 | 1 |

μ values follow from the §4.1 composition fractions (CO2-dominated 43.3–43.5; N2-dominated ≈28); ρ(h) = P(h)·μ/(R_gas·T(h)) per S-5a. Above h_break, P(h) continues from the layer-break pressure with H_upper until the stored h_atm override (drag cutoff). Gas/ice giants are class F and use entry-interface tables owned by `01`/`02` (skim/probe only).

### 4.1c Procedural small-body physical generation (world-gen rules — the physical half of the ~218 procedural bodies)

| Property | Rule |
|---|---|
| Diameter D | truncated power law N(>D) ∝ D^−2; belt D ∈ [0.3, 30] km; NEA D ∈ [0.1, 2] km; trojans [1, 20] km; comets [0.5, 5] km; KBOs [10, 200] km |
| Spectral class | belt: C 60% / S 30% / M 10% (§4.4.7); NEA: C 40% / S 55% / M 5%; trojans: C/D-like (treat as C); comets and KBOs: volatile class fixed |
| Bulk density ρ | by class: C 1.3, S 2.4, M 4.5, comet 0.53 (67P anchor), KBO 1.5 t/m³ |
| GM | GM = G·(4/3)·π·(D/2)³·ρ, G = 6.674×10^-20 km³/(kg·s²); g and v_esc derived per S-3 from GM and R = D/2 |
| Rotation T_rot | U(2.2 h, 40 h), subject to the S-11 spin barrier (rubble piles D > 300 m never < 2.2 h; monolith fragments < 300 m may roll down to 0.1 h, flagged DANGER) |
| Dock-mode flag | fixed at world-gen if g < 0.01 m/s² (S-12; never recomputed live, per §8) |
| Sectors | 1–3, terrain by class: C → REGOLITH_PILE / ICE_PLAIN; S/M → REGOLITH_PILE / HIGHLAND; comet → REGOLITH_PILE with active neck/lobe split (§4.4.14); KBO → ICE_PLAIN |
| Deposits / anomalies | deposit_rolls per `04` §4.2 class tables; anomaly slots roll per S-10 procedural probabilities |

### 4.2 Heliocentric orbital elements (2D map; J2000-derived, propagated to epoch 2049-01-01, then frozen; inclination → 0 per S-2)

| Body | a [AU] | a [10^6 km] | e | P | ϖ [deg] | M0 @ epoch [deg] | Real i (dropped) | dir | Notes |
|---|---|---|---|---|---|---|---|---|---|
| Mercury | 0.3871 | 57.91 | 0.2056 | 87.97 d | 77.5 | 337.4 | 7.00° | + | big e: flux and Δv vary per window |
| Venus | 0.7233 | 108.21 | 0.0068 | 224.70 d | 131.5 | 284.6 | 3.39° | + | nearly circular |
| Earth | 1.0000 | 149.60 | 0.0167 | 365.26 d | 102.9 | 357.5 | 0.00° | + | reference plane |
| Mars | 1.5237 | 227.94 | 0.0934 | 686.98 d | 336.0 | 38.1 | 1.85° | + | e drives good/bad windows (real effect); feeds Ls (S-9) |
| Vesta | 2.3615 | 353.3 | 0.089 | 3.63 yr | 255.0 | 169 [P] | 7.14° | + | |
| Ceres | 2.766 | 413.8 | 0.076 | 4.60 yr | 153.9 | 264 [P] | 10.59° | + | belt anchor body |
| Psyche | 2.924 | 437.4 | 0.134 | 4.99 yr | 19.3 | 302 [P] | 3.10° | + | M-type flagship |
| Hygiea | 3.139 | 469.6 | 0.112 | 5.57 yr | 235.5 | 47 [P] | 3.83° | + | C-type outer belt |
| Jupiter | 5.2044 | 778.6 | 0.0489 | 11.862 yr | 14.8 | 66.7 | 1.30° | + | trojan phasing reference |
| Saturn | 9.5826 | 1,433.5 | 0.0565 | 29.447 yr | 92.4 | 196.4 | 2.49° | + | |
| Uranus | 19.191 | 2,870.7 | 0.0472 | 84.02 yr | 171.0 | 352.2 | 0.77° | + | |
| Neptune | 30.07 | 4,498.4 | 0.0086 | 164.79 yr | 45.0 | 7.0 | 1.77° | + | resonance pair with Pluto |
| Pluto | 39.482 | 5,906.4 | 0.2488 | 247.94 yr | 224.1 | 86.0 | 17.16° | + | 3:2 resonance phasing enforced (S-2): with these ϖ/M0 the verified Pluto–Neptune minimum separation is 18.3 AU over the 495-yr synodic cycle (≥ 12 AU guarantee, §8) |
| Eris | 67.9 | 10,157 | 0.44 | ~559 yr | 187.6 | 205 [P] | 44.0° | + | endgame; i-discount acknowledged |
| Arrokoth | 44.58 | 6,669 | 0.042 | ~298 yr | 333.3 | 316 [P] | 2.45° | + | cold classical KBO |
| Eros | 1.458 | 218.1 | 0.223 | 1.76 yr | 123.1 | 110 [P] | 10.83° | + | Amor NEA |
| Bennu | 1.1264 | 168.5 | 0.2037 | 1.20 yr | 68.3 | 102 [P] | 6.03° | + | Apollo NEA; sample-site anomaly |
| Ryugu | 1.1896 | 178.0 | 0.1902 | 1.30 yr | 103.0 | 21 [P] | 5.88° | + | |
| Itokawa | 1.324 | 198.1 | 0.280 | 1.52 yr | 231.9 | 297 [P] | 1.62° | + | |
| Apophis | ~1.10 | 164.6 | ~0.19 | ~1.15 yr | 330.8 | 213 [P] | 2.2° | + | post-2029-flyby Apollo-class elements |
| 67P/C-G | 3.463 | 518.0 | 0.641 | 6.45 yr | 62.9 | 84 | 7.04° | + | q = 1.24 AU; M0 anchored to the ~2047-07 perihelion (1.5 yr before epoch) |
| 1P/Halley | 17.83 | 2,667 | 0.967 | ~75 yr | 169.8 | 299.9 | 162.3° | − | RETROGRADE in 2D; M0 anchored so perihelion lands 2061-07-28 (S-14): M0 = −(12.57 yr / 75.32 yr)·360° |
| + procedural | belt 2.1–3.3 / NEA 0.8–1.9 / trojans := 5.2044 | — | belt U(0, 0.25) / NEA U(0.05, 0.45) | — | ϖ ~ U(0°, 360°) | M0 ~ U(0°, 360°) | — | + | world-gen: ~120 belt, ~60 NEA, ~20 Jupiter trojans, ~10 comets, ~8 KBOs; **trojan exception**: a := a_Jupiter (hence P := P_Jupiter), ϖ := ϖ_Jupiter, M0 := M0_Jupiter ± 60° + U(−15°, +15°) — locked to the L4/L5 longitudes (random phase would NOT be a trojan) |

ϖ/M0 sourcing: planet rows are computed from J2000 mean elements propagated 17,897.5 days to epoch (consistent with S-2's "within a few degrees" promise); Halley and 67P are anchored to their known perihelion dates; rows tagged **[P]** are provisional placeholders at ±15° (body phase there is unobservable in play and affects only transfer-window timing) to be replaced verbatim by a scripted JPL Horizons pull at data-entry — the schema, conventions, and anchored rows are canonical now.

### 4.3 Satellite orbital elements (about their primaries)

| Moon | Primary | a [km] | e | P | ϖ [deg] | M0 @ epoch [deg] | dir | Eclipse fraction f_ecl = asin(R_p/a)/π |
|---|---|---|---|---|---|---|---|---|
| Moon | Earth | 384,400 | 0.0549 | 27.322 d | 318.2 [P] | 135.0 [P] | + | 0.005 (lunar eclipses; ignorable for power) |
| Phobos | Mars | 9,376 | 0.0151 | 7.654 h | 150.1 [P] | 40.0 [P] | + | 0.12 — long Mars-shadow pass each orbit |
| Deimos | Mars | 23,463 | 0.0003 | 30.31 h | 0 | 200.0 | + | 0.046 |
| Io | Jupiter | 421,800 | 0.0041 | 1.769 d | 0 | 310.0 | + | 0.054 |
| Europa | Jupiter | 671,100 | 0.0094 | 3.551 d | 0 | 120.0 | + | 0.034 |
| Ganymede | Jupiter | 1,070,400 | 0.0013 | 7.155 d | 0 | 250.0 | + | 0.021 |
| Callisto | Jupiter | 1,882,700 | 0.0074 | 16.689 d | 0 | 85.0 | + | 0.012 |
| Enceladus | Saturn | 237,948 | 0.0047 | 1.370 d | 0 | 15.0 | + | 0.079 |
| Titan | Saturn | 1,221,870 | 0.0288 | 15.945 d | 185.7 [P] | 160.0 [P] | + | 0.015 |
| Miranda | Uranus | 129,390 | 0.0013 | 1.413 d | 0 | 295.0 | + | 0.063 |
| Titania | Uranus | 435,910 | 0.0011 | 8.706 d | 0 | 70.0 | + | 0.019 |
| Oberon | Uranus | 583,520 | 0.0014 | 13.46 d | 0 | 225.0 | + | 0.014 |
| Triton | Neptune | 354,759 | 0.000016 | 5.877 d | 0 | 330.0 | − | RETROGRADE (real); 0.022 |
| Charon | Pluto | 19,596 | 0.0002 | 6.387 d | 0 | 0.0 | + | mutual tidal lock — Charon hangs fixed in Pluto's sky |

ϖ/M0 convention for moons: rows with e < 0.01 store ϖ := 0 (perihelion direction unobservable at game fidelity) and a fixed canonical M0 chosen for determinism; the three e ≥ 0.01 moons carry [P] placeholders like §4.2, replaceable by the Horizons data-entry pull — nothing downstream depends on real 2049 moon phase. **f_ecl rule (single source, S-6b)**: f_ecl multiplies into solar availability for ALL assets inside the moon's SOI — orbiting AND landed — except PSR/PEL-flagged sectors, whose insolation override replaces it (`09` consumes). Synchronous rotation means each moon's solar day equals its orbital period (S-6).
### 4.4 Per-body design

Each entry: identity (what the body is *for*), unique mechanics, hazards, landing/ascent, base opportunities, sectors, survey content. Anomaly details in §4.5.

#### 4.4.1 Mercury — the forge at the terminator

- **Identity**: Act 4–5 industrial outpost built on ENERGY, not ore. 6.7× Earth solar flux orbit-averaged (~9,100 W/m²; 10.6× at perihelion) makes it the system's best place for energy-hungry processing (mass drivers, smelting, refining); polar ice for life support. The crust is NOT metal-rich: MESSENGER XRS/GRS measured surface Fe of only ~1.5–2 wt% (Weider et al. 2014, Icarus; Evans et al. 2012, JGR — among the most iron-poor rocky surfaces known, below even lunar maria). Mercury's iron is in the inaccessible core; the crust is Mg-silicate, sulfur-rich (~4 wt% S) and volatile-bearing (Na, K). High-grade inner-system IronSteel lives in the Moon's ilmenite mare and the NEAs — Mercury *imports* feedstock and exports refined product plus native Silicon/Oxygen/Glass. Anchor: MESSENGER; mass-driver export per O'Neill-era and recent solar-electric studies.
- **Unique mechanics**: (1) Terminator chase (S-6c): dawn advances at ≈3.6 km/h equatorial; mobile bases (`10`) can stay in the perpetual twilight band where T ≈ 250–350 K instead of enduring 700 K noon / 100 K night. (2) Solar flux seasonality from e = 0.2056 (S-4a): perihelion smelting campaigns. (3) Mass-driver export (T3, `05`): v_esc only 4.25 km/s and no atmosphere — electromagnetic launch of refined billets (smelted NEA/lunar feedstock plus native Silicon/Glass/StructuralParts) is the intended endgame logistics: cheap energy in, finished mass out.
- **Hazards**: 700 K subsolar surface (equipment thermal limit checks, `09`); SPE dose ×6.7 with no atmosphere and only 30–60 min warning (storm shelter mandatory, `07`/`08`); deep gravity well for inbound Δv (see `01` — getting *to* Mercury is expensive; being there is cheap energy).
- **Landing/ascent**: class B; ≈3.2 km/s each way, no aero assist. Land at terminator or in polar PSR shadow to avoid thermal soak.
- **Base sites**: PSR rim sites (Prokofiev/Kandinsky-class) combine permanent shade, nearby water ice (10^14–10^15 kg deposits, MESSENGER radar), and near-continuous solar on rim masts — the lunar-south-pole playbook at 6.7× the wattage (10.6× at perihelion).
- **Sectors (10)**: Caloris Basin (VOLCANIC flood lava — Mg-silicate; Silicon/Glass feed) · Pantheon Fossae "the Spider" (anomaly) · Borealis PSR-N (PSR, Water) · Kandinsky PSR-N (PSR, Water, anomaly slot) · South PSR (PSR, Water) · Hollows Terrain (volatile-loss pits, sulfide/volatile lag deposits — MESSENGER hollows chemistry, anomaly) · Intercrater Plains ×2 (HIGHLAND, Silicon/Regolith) · Smooth Plains (MARE-analog Mg-silicate; crustal Fe 1.5–2 wt%, low-grade only) · Discovery Rupes (thermal-contraction scarp, wonder).
- **Survey**: MESSENGER impact site (2015, Suisei Planitia area); BepiColombo MPO derelict orbiter (post-2049 disposal orbit); hollows close-up science (unique to Mercury).

#### 4.4.2 Venus — the cloud colony

- **Identity**: Act 4 set-piece: the only place where the *atmosphere* is the habitat. At 50–55 km altitude Venus is the most Earth-like environment off Earth (NASA HAVOC): ~1 atm, 273–350 K, Earth-like gravity 8.87 m/s², and breathable air is a *lifting gas* (O2/N2 floats in CO2 — habitats are their own balloons).
- **Aerostat band table (VIRA / Seiff et al. 1985)**, the four CLOUD_BAND "sectors" of the upper layer:

| Band | Altitude | P [kPa] | T [K] | f_atm (S-6a) | Notes |
|---|---|---|---|---|---|
| V-Cloud-Low | 48–50 km | 107–135 | 348–366 | 0.30 | hot but max lift; acid aerosol heavy |
| V-HAVOC | 50–52 km | 81–107 | 330–348 | 0.45 | HAVOC design point; best compromise |
| V-Temperate | 52–56 km | 45–81 | 293–330 | 0.55 | "shirt-sleeve" T; thinner air, bigger envelopes |
| V-Cloud-Top | 56–62 km | 17–45 | 263–293 | 0.70 | best solar, strongest UV + acid exposure |

All bands additionally take the +0.15 below-cloud-albedo bonus for two-sided arrays (S-6a); `09` sizes arrays per band from this column.

- **Unique mechanics**: (1) Buoyancy station-keeping (`07` owns the balloon model; this file owns ρ(h)). (2) Super-rotation drift: aerostats circumnavigate every ≈6 Earth days (Vega balloon anchor, w ≈ 66 m/s) — day/night power cycle is 3 days light / 3 days dark regardless of the 116.8-day solar day; batteries or H2 fuel cells required (`09`). (3) Atmospheric ISRU: infinite CO2/N2 intake (`04` M-3e); acid-droplet water harvesting at ~5 g Water per t of processed cloud air [generous end of measured cloud mass loading: ~1–50 mg aerosol/m³ in ~1.4 kg/m³ air at 50–52 km, of which only ~15–25% is H2O in the H2SO4·xH2O droplets] — bulk Water therefore comes from cracking the ~30 ppm trace H2O vapor in processed CO2 throughput and from imported ice (`04` chain balanced accordingly). (4) Solar factor per band (f_atm column 0.30–0.70, table above) + 0.15 below-cloud albedo bonus for double-sided arrays (S-6a).
- **Hazards**: H2SO4 aerosol — exposed Polymers/seals degrade 1%/day unless acid-rated (T2 coating, `05`); envelope tear → altitude loss; below 45 km T > 380 K kills standard electronics; the surface (737 K, 9.2 MPa) is a one-way trip before T3.
- **Landing/ascent**: class E (surface) / D (cloud entry). Aerocapture into the cloud deck is gentle (dense atmosphere, generous corridor, `01`). Aerostat→orbit: rocket drop-launched from 52 km, Δv ≈ 8.3 km/s (`01` V4 = ~8,300 m/s canon; a near-Earth-class problem at altitude — the canonical "Venus is easy to visit, hard to leave" lesson). Surface sorties pre-T3: armored probe drops only, survival timer 2–8 h (Venera 13 anchor: 127 min).
- **Base sites**: aerostat clusters in V-HAVOC band; surface T3 refractory mining stations (basalt → BasaltFiber, `04`) at Maxwell Montes foothills and Beta Regio once high-temperature electronics (SiC, real NASA HOTTech line) unlock.
- **Surface sectors (8)**: Maxwell Montes (11 km peak, wonder; radar-bright "metal frost" snowline anomaly) · Maat Mons (ACTIVE volcano — eruption events reuse S-11 Io logic at 1/(180 d); Herrick 2023 anchor) · Beta Regio (Venera 9/10 derelicts) · Phoebe Regio (Venera 13/14) · Baltis Vallis (6,800 km lava channel, longest in the solar system, wonder) · Lakshmi Planum (plateau) · Aphrodite Terra (tessera highlands — oldest crust, survey jackpot) · Lowland Plains (Vega 1/2 landers).
- **Survey**: Venera 7–14 lander derelicts (first soft landings on another planet's surface), Vega balloon gondolas (still adrift? recovered as drifting anomalies in cloud bands), Pioneer Venus probe wreckage; tessera geology; Maat Mons live vent.

#### 4.4.3 Earth — home, market, gravity tax

- **Identity**: starting body, permanent economic anchor (`12` owns launch costs/contracts). Everything is available here; the 9.4 km/s surface→LEO tax (canon, `01`) is the reason the rest of the game exists.
- **Unique mechanics**: (1) Launch windows to everywhere (S-14 synodics). (2) Van Allen belts (S-8c) punish slow SEP spirals with crew. (3) Re-entry: free aerobraking/EDL for returning cargo (`01`); splashdown recovery vs propulsive reuse (`02`/`12`). (4) Orbital debris zones: LEO 400–1,200 km and GEO graveyard flagged as debris fields — collision roll p = 0.0005 per asset-year in flagged bands [SIMPLIFIED Kessler bookkeeping], salvage opportunities (§4.5).
- **Hazards**: budgets (`12`); range-safety launch licensing delays as event timers; hurricanes closing the equatorial spaceport (flavor event, p = 0.02/launch-window).
- **Sectors (12)**: KSC-analog equatorial spaceport · high-latitude spaceport — rotation bonus is global in 2D (S-3); differentiated by weather scrub probability and logistics cost (`12` owns values) · Atacama observatory (SurveyData bonus) · Iceland geothermal industrial park · Australian mass-driver site (T3) · 7 scenery/market regions (`12` owns their economy stats).
- **Survey**: Earth orbit is the museum — Vanguard 1 (oldest object in orbit, 1958), Hubble (derelict by 2049 unless player boosts it — prestige contract), ISS debris/graveyard remnants (deorbited ~2030), Envisat (8-t collision hazard and salvage prize), GEO graveyard ring.

#### 4.4.4 Moon — logistics school

- **Identity**: Act 2 core. Three days away; teaches ISRU, night survival, and export economics (LCROSS/LRO/Artemis data foundation). The Moon's job is to make the player build their first non-Earth supply chain (oxygen, then metals, then propellant to LLO/EML depots — `05`).
- **Unique mechanics**: (1) 14.77-day night (solar day 29.53 d): power storage or Kilopower fission (`09`) or PEL sites (S-6b canonical duty 0.85 ± 0.05). (2) PSR mining: Cabeus-class floors at 25–40 K hold 5.6±2.9 wt% water ice (LCROSS) but machines need full cryo-rated drivetrains (`04` M-9 dust/cold wear ×2). (3) Dust: electrostatic regolith fines degrade seals/radiators — maintenance tax ×1.5 vs Mars (Apollo anchor; `04` M-9). (4) Mass driver (T3): v_esc 2.38 km/s, the original O'Neill scenario; ships Oxygen/metal to EML depots (`05`).
- **Hazards**: thermal swing 95–390 K (equipment cycling fatigue, `09`); micrometeoroids (p = 0.001/asset-year damage roll); no SPE warning shelter excuse — 1.37 mSv/day ambient (Chang'e-4 LND) plus events.
- **Landing/ascent**: class B; ≈1.9 km/s with margins each way; no atmosphere → suicide-burn profiles (`01`), terrain slope checks vs sector slope_sigma.
- **Base sites**: South-pole rim (PEL power + PSR water 2 km apart — the Artemis logic); Marius Hills lava tube (Kaguya/LRO ~60 m skylight; intact tube = free radiation/thermal/micrometeoroid shelter for a buried base, `07` cost −40%); high-Ti mare for ilmenite O2 plants (`04` RX chain).
- **Sectors (14)**: Mare Tranquillitatis (high-Ti, Apollo 11 + Surveyor 5, pit anomaly) · Oceanus Procellarum (KREEP fringe Th/U, Luna 9/13) · Mare Imbrium (Lunokhod 1, Chang'e 3) · Taurus-Littrow (Apollo 17, pyroclastic He3-rich [SPECULATIVE]) · Aristarchus Plateau (pyroclastic glass, wonder) · Marius Hills (lava tubes) · Highlands Near N / Near S (anorthite Al/Si) · Tycho (young crater, central-peak wonder) · South Pole Shackleton (PEL + PSR cluster, Chandrayaan/Artemis derelicts) · Cabeus PSR (LCROSS impact site anomaly, Water) · North Pole PSR (Hermite ~25 K — coldest measured surface in the solar system) · Far-side Highlands (radio-quiet zone: SurveyData ×1.5 for astronomy contracts, Chang'e 4) · South Pole–Aitken Basin (deep-crust exposures, survey jackpot).
- **Survey**: richest derelict catalog in the game (§4.5): Apollo descent stages and ALSEPs, Luna sample-return stages, both Lunokhods (Lunokhod 1's laser retroreflector still functional — real), Surveyor 3 (Apollo 12 already salvaged parts from it — precedent for the game's salvage mechanic), LCROSS/Ranger impact scars, Chang'e series.

#### 4.4.5 Mars — the first colony

- **Identity**: Act 3 centerpiece. The only body where full ISRU closure (propellant + plastics + food + steel) is plausible with T2 tech: CO2 atmosphere + mid-latitude ice + iron oxides (Zubrin/Mars Direct + MOXIE anchors). Designed to host the player's first self-sustaining base.
- **Unique mechanics**: (1) Dust season state machine (S-9) — the defining rhythm: stockpile power before Ls 180. (2) Sabatier economy: intake CO2 + ice Water → Methane/Oxygen (`04` chains, MOXIE/Mars Direct anchors). (3) EDL minigame: aerocapture corridor → chute (only slows to ~Mach 2) → mandatory retropropulsion ≈ 1 km/s (class C teeth; `01`). (4) Seasonal pressure swing ±15% (S-9) modulates intake mining and EDL margins. (5) Hellas depth bonus: P ≈ 1.16 kPa at −7.1 km — best aerobraking/chute margin, worst dust.
- **Hazards**: global storms (60–100 sols of f_dust ≈ 0.04–0.17 for τ = 9–4 — solar-only bases die; the 2018-storm/Opportunity lesson is the tutorial text); dust soiling −0.2%/sol; perchlorates in regolith (greenhouse feedstock must be washed, `04`/`08` toxicity rule); 0.67 mSv/day chronic dose (bury habs, `07`).
- **Landing/ascent**: class C; ascent ≈ 4.0 km/s incl. losses (`01` R4 = 4,000 m/s canon; anchor: MAV studies 4.0–4.3 km/s); descent mostly aero with ≈ 1 km/s propulsive.
- **Base sites**: Arcadia/Deuteronilus mid-lat ice (SWIM: excess ice 30–90 wt% under <1 m overburden — water without PSR cryo pain); Jezero/Isidis (Perseverance sample cache salvage contract); Valles Marineris floor (pressure +20% vs datum, wind-sheltered, wonder); polar cap edge (seasonal CO2 frost cycle = free dry-ice cold sink, `09`).
- **Sectors (18)**: Chryse (Viking 1, Pathfinder) · Utopia (Viking 2, Zhurong) · Elysium (InSight) · Gale (Curiosity) · Gusev (Spirit) · Meridiani (Opportunity, Schiaparelli crash, hematite Fe) · Jezero/Isidis (Perseverance + Ingenuity + sample depot, Beagle 2) · Arabia (hydrated minerals) · Tharsis Rise (young lava, geothermal residual-heat anomaly candidates) · Olympus Mons (21.9 km summit above most dust — PEL-like solar bonus f_dust exponent halved; wonder) · Valles Marineris (wonder, deep-canyon pressure bonus) · Hellas (−7.1 km, P 1.16 kPa) · Argyre · Arcadia mid-lat ice N (SWIM) · Deuteronilus ice N · Mid-lat ice S · Polar Cap N (layered H2O ice + seasonal CO2) · Medusae Fossae (fine ash — worst dust_index 1.0, BasaltFiber feed).
- **Survey**: nine real derelict/active-heritage sites (by 2049 all are derelicts/museums), Mars 3 (first soft landing, 1971, Terra Sirenum), sample-cache retrieval, RSL brine-streak science sites, SHARAD-confirmed buried glaciers.

#### 4.4.6 Phobos & Deimos — the free depots

- **Identity**: Act 3 logistics keystones. Moonlets in Mars orbit = natural propellant depots and staging platforms; Δv from Phobos to trans-Earth injection is tiny (see `01`). Composition genuinely unresolved (captured C-type vs impact debris) — the game makes that uncertainty *content*: water content rolls 0–5 wt% at world-gen (`04` table) and the survey answer changes Act 3 strategy.
- **Unique mechanics**: dock mode (S-12, g = 0.0057 m/s²); Phobos eclipse fraction 0.12 (S-7c table) — solar arrays need 12% margin; Stickney crater (9 km) provides radiation shadowing from half the sky +0.35 shielding factor (`08`).
- **Hazards**: anchoring failures; ejecta self-rain after blasting ops (mining charges prohibited — drill-only rule, `04` M-6 microgravity mining).
- **Sectors**: Phobos 3 (Stickney interior · grooved terrain · sub-Mars point — Mars hangs fixed in sky, comms relay site) ; Deimos 2 (smooth saddle · cratered north).
- **Survey**: Phobos 2 Soviet derelict (lost 1989, drifting nearby — recoverable anomaly); MMX mission hardware (JAXA, 2020s) on Phobos; future-history sample canister.

#### 4.4.7 Ceres & the Main Belt — the water tower

- **Identity**: Act 4 hub. Ceres is the belt's logistics capital: 0.51 km/s escape velocity, 20–45 wt% water-ice crust (Dawn GRaND), ammoniated clays (Nitrogen feed — rare off Earth!), carbonates. The belt itself is a procedural field of ~120 bodies in three spectral classes (`04` grades):

| Class | Fraction (game) | Composition anchor | Game resources | Identity |
|---|---|---|---|---|
| C-type | 60% | CI/CM chondrite; Ryugu/Bennu samples | Water 5–20 wt%, Carbon, Nitrogen | volatile tankers' targets |
| S-type | 30% | ordinary chondrite; Itokawa/Eros | Silicon, IronSteel grains 5–20 wt% | structural feedstock |
| M-type | 10% | Psyche-class; iron meteorites | IronSteel 30–70 wt%, high variance (Psyche's bulk density 3,980 kg/m³ implies ~30–60 vol% metal mixed with silicates — survey to K2 resolves the actual grade), RareEarths (PGM 10–100 ppm) | the metal motherlode |

- **Unique mechanics**: (1) Belt transit is *empty* — mean spacing ~10^6 km; collision risk 0 (honest; movie asteroid fields are forbidden). (2) Spin-state gating (S-11): fast rotators need despin tugs (`06`) before industrial anchoring. (3) Ceres brine cryovolcanism: Dawn gravity data place the deep brine reservoir under Occator at **~40 km depth** (Raymond et al. 2020 — "25 miles deep, hundreds of miles wide"), with km-scale impact-melt remnant pockets that fed Cerealia Facula; there is NO shallow liquid — at drill depths Ceres is ~155 K cryogenic ice/clay. Gameplay split: shallow ICE mining at Occator/Kerwan is routine Act 4 industry; **deep-brine access is a T3 drilling megaproject** (km-class boreholes, `11` gate) — the belt's analogue of the Europa melt probe.
- **Hazards**: distance (light lag 13–30 min; full autonomy rules, `05`); solar flux 130–180 W/m² (solar still viable but arrays ×8 Earth area, pushing fission, `09`); months-long transfer windows (`01`).
- **Landing/ascent**: Ceres class B ≈ 0.37 km/s; everything smaller is dock mode.
- **Ceres sectors (8)**: Occator faculae (carbonate domes over the ~40 km brine reservoir, wonder) · Ahuna Mons (cryovolcano, wonder) · Kerwan basin (ice-rich) · Equatorial dark plains (clays, Nitrogen) · N polar PSR-analog craters (cold-trap ice, S-6b) · S highlands · Urvara basin · Juling crater (seasonal ice patch — Dawn VIR observed change).
- **Vesta sectors (6)**: Rheasilvia basin + 22-km central peak (wonder) · Marcia crater (young, pitted volatile terrain) · Divalia Fossae trough belt · Cratered highlands N · Cratered highlands S · Dark-material unit (carbonaceous infall, Carbon).
- **Psyche sectors (5)**: Metal-rich plains W (wonder — radar-bright, ~30–60 vol% metal) · Metal-rich plains E (wonder) · Meteorite-breccia mixed terrain · Crater Panthia (depth profile = grade ground truth) · Regolith-covered south (silicate cover, lower grade).
- **Survey**: Dawn derelict orbiter (still circling Ceres — real disposal orbit, stable >50 yr); procedural geode vugs (S-10); the metal-rich-plains wonder on Psyche, whose orbiter-survey grade roll (30–70 wt% IronSteel) is the Act 4 economic reveal (4.4.8-adjacent: Psyche orbiter derelict).

#### 4.4.8 Near-Earth Asteroids — the first mines

- **Identity**: Act 3 parallel track to Mars: lowest-Δv resources in the system (some NEAs are < 0.5 km/s from escape-adjacent staging — `01` owns the map; anchor: NHATS accessibility studies). Teach microgravity mining (`04` M-6) before the belt.
- **Mechanics/hazards**: dock mode + anchoring (S-12); spin barrier (S-11); thermal cycling 200–330 K per rotation (hardware fatigue ×1.2); curated roster (Bennu, Ryugu, Itokawa, Eros, Apophis) + ~60 procedural NHATS-like rolls; C-types yield Water for the first orbital propellant economy.
- **Survey**: OSIRIS-REx Nightingale sampling scar on Bennu (TAG event ground truth — the TAGSAM head returned to Earth in the 2023 sample capsule; what remains is the disturbed, gas-blasted surface); Hayabusa target markers + MINERVA/MASCOT hoppers on Itokawa/Ryugu; NEAR Shoemaker resting on Eros (first asteroid landing, 2001); heliocentric drifters between NEA orbits: the Tesla Roadster (a ≈ 1.33 AU — real), Apollo 10's "Snoopy" LM ascent stage (real heliocentric derelict), ISEE-3 (real).

#### 4.4.9 Jupiter system — the radiation maze

- **Identity**: Act 5 opening. Four worlds arranged by dose rate (S-8c): the game's cleanest "difficulty rings". Solar flux is 50 W/m² — fission or bust (`09`). Jupiter itself is class F: gravity assist pivot (`01`) and [SPECULATIVE T4] He3/Hydrogen scoop target.
- **Radiation belt model is S-8c**; the gameplay consequence table:

| Moon | r [R_J] | Surface dose [mSv/day] | Unshielded crew survival | Gameplay verdict |
|---|---|---|---|---|
| Io | 5.9 | ≈ 36,000 (36 Gy/day absorbed) | hours | robots only, brief sorties, T4 |
| Europa | 9.4 | 5,400 | ~1 day | teleops from orbit/subsurface only; burial mandatory (≥ 3 m ice, `08`) |
| Ganymede | 15.0 | 80 (own magnetic field) | weeks | shielded surface base viable T3 |
| Callisto | 26.3 | 0.14 + GCR | indefinite | THE crewed base (NASA HOPE anchor) |

- **Io**: 400+ active volcanoes (Galileo/Juno); eruption events per S-11, plumes 300–400 km; background 90–130 K with 1,900 K lava lakes (Loki Patera ≈ 200 km across, wonder). Tidal-heating geothermal taps [SPECULATIVE T4 flavor, capped 100 kWt]. Sectors (8): Loki Patera · Pele · Tvashtar · Prometheus plume field · 2× sulfur plains · 2× polar mountains (Boösaule ~17 km, wonder).
- **Europa**: 15–25 km ice shell over a 60–150 km liquid ocean (Galileo magnetometry). The melt-probe campaign (T3 megaproject, `11`): reach the ocean, return biology-negative-but-chemistry-rich SurveyData jackpot (no aliens — the find is abiotic organic chemistry and hydrothermal minerals). Chaos terrain (Conamara) = shallow brine lenses at 1–3 km (drillable precursor goal). Sectors (8): Conamara Chaos · Thera/Thrace Macula · 2× ridge plains · lineae band · impact site Pwyll · 2× polar plains. Hazard: 5.4 Sv/day — all surface assets accrue electronics damage 1 component-fault roll/(30 d) unless buried (`05` maintenance).
- **Ganymede**: largest moon (R 2,634 km), intrinsic magnetosphere (real: only moon with one) halves ambient dose to ~80 mSv/day. Grooved/dark terrain dichotomy; subsurface ocean (deep, not gameplay-reachable). The "mid-difficulty" jovian base. Sectors (10): Galileo Regio (dark, ancient) · Uruk Sulcus (grooved) · 4× terrain-pair repeats · polar caps ×2 (frost) · Enki Catena (crater chain wonder) · Tros (bright ray).
- **Callisto**: outside the main belts (0.14 mSv/day + GCR), 40% ice by mass, ancient cratered surface — the staging capital for the outer system (HOPE study had it exactly right). Valhalla multi-ring basin (wonder). Sectors (10): Valhalla center + 2 ring arcs · Asgard basin · 4× cratered plains (ice 20–40 wt%) · 2× knobby erosion terrain.
- **Survey**: Galileo probe entry point (atmosphere, unreachable — log entry only); Juno disposal entry (same); on Europa, the crashed-by-design Juice/Clipper-era hardware [future-history: Clipper disposal impact site on Ganymede per current plan]; Pioneer/Voyager flyby trajectories as "heritage corridor" map overlays (flavor).

#### 4.4.10 Saturn system — the cryogenic harbor

- **Identity**: Act 5 second half. Saturn's belts are mild (S-8c: 1.0 mSv/day inside 8 R_S) — the hazard here is *cold and distance* (flux 14.8 W/m², light lag ~80 min). Titan is the richest single body in the outer system; Enceladus is the easiest water tap; the rings are a T3+ ice quarry.
- **Titan — the gas station with weather**:
  - Surface 146.7 kPa (1.45 atm), 93.7 K (Huygens HASI); N2 ~94.5%/CH4 ~5% near-surface. Atmosphere column P/g ≈ 109 t/m² ≈ 10,900 g/cm² — ten times Earth sea level's 1,033 g/cm² → radiation ≈ 0.01 mSv/day: Titan is the most radiation-safe surface in the game including Earth.
  - **Unique mechanics**: (1) Flight paradise: ρ 5.3 kg/m³ + g 1.35 m/s² → human-powered/electric flight trivial; Dragonfly-class rotorcraft are the default vehicle (`10`). (2) Methane hydrology: Kraken Mare (≈400,000 km²), Ligeia Mare (≈126,000 km²) — Sea Pump intake per `04` M-3f; methane rain events (decadal storms, Cassini-observed) refill polar lakes — modeled as sector weather flag, optics obscured f = 0.5 for U(5,20) d. (3) Inverted combustion: O2 is the scarce/explosive commodity; Methane is ambient. Burn anything = bring oxygen (Water-ice bedrock electrolysis). (4) Chute-only landing (class D, Huygens anchor): descent is free; ascent ≈ 2.4 km/s with severe drag losses (`01` S4 = 2,400 m/s canon; `01`/`02` own the split).
  - **Hazards**: 94 K cryo-embrittlement (all surface hardware needs T3 cryo rating, `05` maintenance ×1.5 otherwise); solar 1.5 W/m² noon (S-6a f_atm 0.10) — fission mandatory (`09`); CH4/O2 leak combinations (habitat explosion roll, `07`).
  - **Sectors (12)**: Kraken Mare (SEA, Ligeia-class roll alt: ethane-richer Kraken-class per `04`) · Ligeia Mare (SEA) · Punga Mare · Shangri-La dune field (organics: Carbon/Polymers feed) · Adiri (Huygens derelict — the most distant human artifact landing, prestige anomaly) · Selk crater (Dragonfly derelict/active heritage ~2034+, anomaly) · Xanadu (water-ice bedrock outcrop) · Sotra Patera (cryovolcano candidate, wonder) · 2× polar lake districts (seasonal) · equatorial plains ×2.
- **Enceladus — the water fountain**: R 252 km, g 0.113 m/s²; south-polar tiger stripes (Damascus/Baghdad/Cairo/Alexandria sulci) vent ≈ 200 kg/s total (Cassini); stripe-adjacent T up to ~197 K vs 75 K mean. Mechanics: S-11 vent capture ≤ 5 kg/s/collector; lowest-Δv water export in the outer system (0.18 km/s ascent + Saturn-system transfers, `01`). E-ring transit = free hull "snow" accretion (cosmetic). Sectors (6): 4 tiger-stripe vents (each an anomaly wonder) · cratered north · sub-Saturn plains.
- **Rings**: zone object, not particles: annular fields C (74,658–92,000 km), B (92,000–117,580 km), Cassini Division, A (122,170–136,775 km), >95% Water ice, particle sizes cm–10 m. **Ring mining (T3)**: a harvester ship inside the zone collects Water at `ṁ = 2.0 t/h · ρ_zone` (ρ_zone: B = 1.0, A = 0.6, C = 0.3) with collision micro-damage 0.1%/h hull wear. Honest tag: engineering-extrapolated, no published study mines rings at scale [SPECULATIVE-adjacent but physics-trivial]; B-ring optical depth supports the density ranking (real).
- **Survey**: Huygens lander (Adiri); Cassini's atmosphere-entry "grave" (log entry); ring-embedded moonlet discovery chain (procedural, real propeller-feature anchor).

#### 4.4.11 Uranus — the quiet giant

- **Identity**: Act 5/endgame waypoint; lowest escape-velocity-to-radius ratio of the giants, the coldest measured tropopause in the solar system (~49 K), and negligible internal heat flux (note: at the 1-bar level Neptune, 72 K, is colder than Uranus, 76 K — §4.1). The classic He3 atmospheric-mining target [SPECULATIVE T4] (anchor: Bussard/Wittenberg He3 literature choosing Uranus for low v_esc 21.3 km/s and mild winds).
- **Mechanics**: class F — atmospheric scoop craft only (T4, `02`/`06`); 98° real axial tilt is flattened by S-2 (stated; the famous sideways seasons are lost — flavor text mourns this). Moons are standard icy-B bodies; Miranda hosts Verona Rupes (scarp 5–10 km, possibly up to 20 km — imaging uncertainty stated; lowest-gravity BASE-jump wonder, 0.079 m/s²: a dropped object falls ~8 min).
- **Sectors**: Miranda 4 (Verona Rupes · chevron coronae ×2 · cratered plains) · Titania 4 (Messina Chasmata rift (wonder) · Gertrude crater · cratered plains ×2) · Oberon 3 (Hamlet crater (dark-floor) · S limb mountain ~11 km (Voyager 2, wonder) · cratered plains). Catalog-level depth only — no curated anomalies beyond the listed wonders.
- **Survey**: Voyager 2 flyby corridor (heritage overlay); procedural ice-moon geysers (Miranda candidate plumes — flagged speculative-real).

#### 4.4.12 Neptune & Triton — the captured world

- **Identity**: endgame. Triton is a captured KBO in a RETROGRADE orbit (S-2 dir = −1) — rendezvous costs ~2× normal jovian-style moon capture (`01` owns numbers; the 2D mechanic preserves the real penalty). Surface 38 K, thin 1.4–1.9 Pa N2 atmosphere, active N2 geysers (Voyager 2, dark plume streaks).
- **Mechanics**: geysers = sector events (S-11 logic, benign: 8 km plumes, SurveyData); N2 frost mining = direct cold-trap Nitrogen export (the system's last big Nitrogen reservoir after Earth/Titan/Ceres); cantaloupe terrain wonder. Charon-style mutual-lock does not apply; Triton's orbit decays in ~3.6 Gyr (flavor only).
- **Sectors (6)**: S polar cap (geysers, N2 ice) · cantaloupe terrain (wonder) · 2× equatorial plains · N plains · Mahilani plume site.
- **Survey**: Voyager 2 corridor; procedural cryolava lakes.

#### 4.4.13 Pluto & the Kuiper Belt — the frontier museum

- **Identity**: endgame prestige + interstellar-precursor staging (the campaign's final megaproject launches from high-solar-system orbit; KBO ices fuel it). Pluto: 1.0–1.3 Pa N2 atmosphere (New Horizons) that partially collapses as Pluto recedes from perihelion (real prediction): atmosphere pressure scales `P = P_2015 · exp((r_2015 − r)/2.5 AU)` [SIMPLIFIED] — by the 2060s–80s game era it is thinning on schedule.
- **Mechanics**: Sputnik Planitia — a 1,000-km convecting N2-ice glacier (wonder + infinite-class Nitrogen deposit, slow extraction: volatile handling at 38 K, `04` cryo rules); Charon mutual tidal lock = natural skyhook-anchor geometry [T4 SPECULATIVE project hook]; KBOs (Arrokoth-class contact binaries, Eris) are dock-mode primordial-ice archives (SurveyData ×2 "pristine" multiplier).
- **Sectors**: Pluto 6 (Sputnik Planitia · al-Idrisi mountains (water-ice bergs, wonder) · Cthulhu Macula (tholin dark terrain, Carbon) · Wright Mons (cryovolcano) · N polar · far-side plains), Charon 4 (Mordor Macula N pole · Serenity Chasma (wonder rift) · 2× plains).
- **Survey**: New Horizons flyby corridor (it left the system — log entry); procedural KBO contact binaries; Eris/Dysnomia long-haul expedition chain.

#### 4.4.14 Comets — the moving targets

- **Identity**: periodic volatile bonanzas with built-in deadlines. A comet near perihelion is simultaneously the best science target and the worst parking spot (S-13 activity). Curated: 67P (e = 0.641, q = 1.24 AU, the Rosetta museum piece), Halley (retrograde showpiece, 2061 event). ~10 procedural Jupiter-family comets (a 3–4 AU, e 0.5–0.7).
- **Mechanics**: S-13 activity index drives abrasion/dispersion/free-coma-capture; S-12 anchoring with p_fail = 0.1 (Philae's bounce is in the tutorial text); density ~533 kg/m³ (67P anchor) — drills sink, anchors pull out, mass-budget cheap to deflect [no impact-threat gameplay in v1 — flavor only].
- **Sectors**: 2–3 per comet (active neck/lobe terrain split, 67P-style).
- **Survey**: Philae (Abydos, found-after-loss precedent — real), Rosetta (crashed on Ma'at, 2016), Giotto/Vega flyby heritage at Halley; surface organics (Carbon, Polymers feed) and primordial D/H water chemistry SurveyData.

### 4.5 Anomaly & discovery catalog (curated)

Classes: DERELICT (real human hardware, fixed location), WONDER (real geological feature), COLDTRAP (PSR/ice lens), TUBE (lava tube/cave), EVENT (timed celestial). Procedural anomalies (S-10) reuse these classes. Rewards: SurveyData [GB] (Science lump = 2 SCI per GB, the canonical §4.6 conversion co-signed with `11` §3.5), salvage mass (→ `04`/`05` ledgers), Prestige (→ `12` reputation economy). No aliens anywhere; the emotional payload is real history and real geology.

| ID | Body/Sector | Class | What it really is | Reward |
|---|---|---|---|---|
| AN-01 | Moon / Mare Tranquillitatis | DERELICT | Apollo 11 descent stage, flag, EASEP (Early Apollo Scientific Experiments Package — full ALSEPs flew on Apollo 12–17) | 50 GB, Prestige ×3, heritage-zone rule (no mining within 10 km, `12` fine) |
| AN-02 | Moon / Taurus-Littrow | DERELICT | Apollo 17 site + LRV rover | 50 GB, LRV museum salvage (Prestige choice: preserve or recover) |
| AN-03 | Moon / Mare Imbrium | DERELICT | Lunokhod 1 (laser retroreflector still works — real) | 30 GB, working retroreflector = free nav-beacon upgrade |
| AN-04 | Moon / Oceanus Procellarum | DERELICT | Luna 9 (first soft landing, 1966) | 30 GB, Prestige |
| AN-05 | Moon / Cabeus PSR | COLDTRAP | LCROSS impact scar + 5.6 wt% ice ground truth | instant K2 on sector Water deposit (`04` M-2) |
| AN-06 | Moon / Marius Hills | TUBE | Kaguya/LRO skylight, intact tube ≥ 60 m bore | buried-base site: `07` build cost −40%, radiation 0.05× |
| AN-07 | Moon / South Pole | DERELICT | Chandrayaan-3 + Artemis-era hardware (future-history) | 20 GB, MachineParts salvage 2 t |
| AN-08 | Mars / Chryse | DERELICT | Viking 1 (1976) | 40 GB; RTG casings: 0.5 kg Pu238 (decayed — half-life 87.7 yr, ~55% activity left from 1975 fueling) |
| AN-09 | Mars / Utopia | DERELICT | Viking 2 + Zhurong | 40 GB, Pu238 as AN-08 |
| AN-10 | Mars / Meridiani | DERELICT | Opportunity, dust-dead at Perseverance Valley (2018) | 35 GB; the in-game plaque text is its last data packet (real: "my battery is low and it's getting dark" paraphrase-folklore — use the real τ telemetry instead) |
| AN-11 | Mars / Jezero | DERELICT | Perseverance + Ingenuity + sample-tube depot | 60 GB; sample-cache retrieval contract (`12` payout) |
| AN-12 | Mars / Gale | DERELICT | Curiosity (MMRTG: 4.8 kg PuO2 — ~3.5 kg Pu-238 at 2012 fueling, ~2.6 kg Pu-238 remaining by 2049 at the 87.7-yr half-life; decay products stay in the clads) | 40 GB, Pu238 salvage (`09` RTG refurb chain applies recovery efficiency) |
| AN-13 | Mars / Terra Sirenum* | DERELICT | Mars 3 (first Mars soft landing, 1971; ~20 s of signal, ending 110 s after touchdown) | 30 GB (* folded into Argyre sector for count) |
| AN-14 | Mars / Olympus Mons | WONDER | 21.9 km summit caldera above most of the dust column | summit solar bonus (f_dust exponent ×0.5), Prestige |
| AN-15 | Mars / Valles Marineris | WONDER | 4,000 km canyon, 7 km deep | canyon-floor pressure +20%, wind-sheltered base flag |
| AN-16 | Mars / Arcadia | COLDTRAP | SWIM excess-ice lens < 1 m overburden | instant K2 Water; landing-site recommendation event |
| AN-17 | Venus / Phoebe Regio | DERELICT | Venera 13 (127 min survivor, 1982) | 40 GB; recovering its capsule from 737 K is a T3 trophy contract |
| AN-18 | Venus / cloud bands | DERELICT | Vega 1/2 balloon gondolas (1985) | 25 GB drifting-intercept minigame |
| AN-19 | Venus / Maxwell Montes | WONDER | 11 km peak; radar-bright semiconductor "frost" snowline | 30 GB; RareEarths trace-deposit unlock |
| AN-20 | Venus / Maat Mons | WONDER+EVENT | active volcano (Herrick & Hensley 2023) | live-vent SurveyData 40 GB; eruption events |
| AN-21 | Mercury / Pantheon Fossae | WONDER | "the Spider" radial graben system, Caloris center | 30 GB |
| AN-22 | Mercury / Hollows | WONDER | volatile-sublimation pits (MESSENGER discovery; formed by volatile loss, likely sulfides) | 25 GB; sulfide/volatile lag-deposit unlock |
| AN-23 | Mercury / Suisei Planitia | DERELICT | MESSENGER impact scar (2015) | 15 GB |
| AN-24 | Phobos / sub-Mars point | DERELICT | Phobos 2 (lost 1989) + MMX hardware | 30 GB; comms-relay site flag |
| AN-25 | Ceres / Occator | WONDER | Cerealia Facula carbonate dome over the ~40 km-deep brine reservoir (Dawn gravity, Raymond et al. 2020) | 40 GB; T3 deep-brine drilling megaproject unlock + shallow-ice mining ground truth |
| AN-26 | Ceres / orbit | DERELICT | Dawn orbiter (stable disposal orbit, real) | 20 GB, Xenon residuals 10 kg salvage |
| AN-27 | Bennu | WONDER | Nightingale sampling scar (TAG event ground truth; no hardware remains — the TAGSAM head returned to Earth in 2023) | 25 GB; ground-truth: sector deposits to K2 |
| AN-28 | Eros | DERELICT | NEAR Shoemaker (first asteroid landing, 2001) | 25 GB |
| AN-29 | Heliocentric ~1.3 AU | DERELICT | Tesla Roadster + Starman (real, launched 2018) | 15 GB, Prestige meme bonus; Polymers 1 t |
| AN-30 | Heliocentric | DERELICT | Apollo 10 LM "Snoopy" ascent stage (real) | 35 GB, museum-grade Prestige ×2 |
| AN-31 | Earth orbit | DERELICT | Vanguard 1 (1958, oldest artifact in orbit) | 20 GB; retrieval = Prestige ×2 or leave-in-situ heritage bonus |
| AN-32 | Earth orbit | DERELICT | Envisat (8 t debris hazard) | salvage 6 t StructuralParts/Electronics; removes debris-zone penalty tick |
| AN-33 | Europa / Conamara | WONDER | chaos terrain brine lens 1–3 km deep | melt-probe precursor site; 60 GB |
| AN-34 | Europa / ocean | WONDER | T3 melt-probe ocean contact (abiotic chemistry, hydrothermal minerals — explicitly no life) | 200 GB campaign jackpot |
| AN-35 | Io / Loki Patera | WONDER | 200-km recurrently-overturning lava lake | 50 GB at 1/(30 d) eruption risk |
| AN-36 | Ganymede / Enki Catena | WONDER | 13-crater chain (split-comet impact) | 25 GB |
| AN-37 | Callisto / Valhalla | WONDER | 3,800-km multi-ring basin | 30 GB; base-site flag (HOPE homage) |
| AN-38 | Titan / Adiri | DERELICT | Huygens (2005; most distant landing) | 50 GB, Prestige ×2 |
| AN-39 | Titan / Selk | DERELICT | Dragonfly rotorcraft (arrived 2034; derelict by Act 5) | 40 GB; rotor hardware salvage → `10` Titan-flyer blueprint discount |
| AN-40 | Titan / Sotra Patera | WONDER | cryovolcano candidate | 35 GB |
| AN-41 | Enceladus / 4 sulci | WONDER | tiger-stripe vent fields (each) | 4 × 30 GB; vent-capture sites (S-11) |
| AN-42 | 67P / Abydos | DERELICT | Philae (bounced 2014, found 2016 — real) | 35 GB; anchoring-failure tutorial codex |
| AN-43 | 67P / Ma'at | DERELICT | Rosetta (soft-crashed 2016) | 30 GB |
| AN-44 | Halley | EVENT | 2061-07-28 perihelion apparition | 100 GB once; retrograde-rendezvous achievement |
| AN-45 | Miranda / Verona Rupes | WONDER | 5–10 km fault scarp (possibly 20 km; tallest cliff known) | 40 GB; lowest-g cliff descent stunt (Prestige) |
| AN-46 | Triton / S polar cap | WONDER | active N2 geysers (Voyager 2, 1989) | 40 GB |
| AN-47 | Pluto / Sputnik Planitia | WONDER | convecting N2-ice glacier, 1,000 km | 60 GB; Nitrogen mega-deposit unlock |
| AN-48 | Pluto / al-Idrisi | WONDER | floating water-ice mountain rafts | 30 GB |
| AN-49 | Arrokoth | WONDER | pristine contact binary (New Horizons 2019) | 50 GB ×2 pristine multiplier |
| AN-50 | Moon / far side | DERELICT | Chang'e 4 + Yutu 2 (first far-side landing, 2019) | 30 GB |

Procedural anomaly generator fills remaining slots: lava tubes (Moon/Mars: P = 0.06/slot; volcanic-class sectors ×2), subsurface ice lenses (COLDTRAP, P = 0.10, mid-latitude bands), ore vugs/geodes (P = 0.08, grants +1 grade tier to one deposit), empty otherwise. Curated count: 50+; target total anomalies per campaign ≈ 110.

### 4.6 SurveyData yield classes

| Class | Yield [GB] | Examples |
|---|---|---|
| Flyby first (per body) | 10 | first SOI entry |
| Orbit survey complete (L1) | 20 × √(R/1,000 km), min 5 | full sector map |
| Sector prospect (L2) | 8 per sector | rover traverse |
| DERELICT | 15–60 (table) | hardware archaeology |
| WONDER | 25–60 (table) | geology |
| Jackpots | 100–200 | Europa ocean, Halley 2061 |

**Canonical GB→SCI conversion (co-signed with `11` §3.5 — the ONLY SurveyData→Science bridge).** Investigating an anomaly on-site converts its SurveyData yield to Science at a flat **2 SCI per GB**, one-shot per anomaly. The curated §4.5 catalog therefore lumps **30–400 SCI** (floor: AN-23's 15 GB → 30 SCI; ceiling: AN-34's 200 GB Europa-ocean jackpot → 400 SCI). The GB themselves remain a tradeable data resource (registered in `12` §4.3; the E-12 planetary-data subscription pays $0.2M/GB) — selling the data does NOT forfeit the Science lump. Non-anomaly rows above (flyby first, L1 orbit survey, L2 sector prospect, the Halley EVENT excepted as an anomaly) carry **no implicit SCI**: Science for surveys and traverses comes from `11` §3.5's own one-shot awards (orbital survey per instrument class × region; ground survey 10·X per region over the §4.7 partition), so no double-counting path exists. Diminishing-returns pooling for repeated sampling is owned by `11` §3.1/§3.6, keyed to the §4.7 region IDs.

### 4.7 Science-region partition & exoticism X (canonical per-region assignment, consumed by `11` §3.1/§3.5/§3.7)

`11-research-tech.md`'s Science accrual — survey one-shots, sample pools `P = V_base·X`, milestone lumps `k·X` — is keyed to *science regions*, which this file owns. Partition rule (S-10 extension):

- **Orbit regions**: every body with an SOI gets one `ORB` region (scope of orbital/remote one-shot surveys). Earth alone splits into `EAR-ORB-LEO` (≤ 2,000 km altitude) and `EAR-ORB-HIGH` (above, incl. cislunar) — the only orbit split in `11` §3.7's class table; no other body's orbital classes differ enough to justify one.
- **Atmosphere regions**: class-F giants get one `ATM` probe-band region (so the k = 40 "first atmosphere probe" milestone always resolves to a single X); Venus's four CLOUD_BAND sectors form one `VEN-CLOUD` region.
- **Surface regions**: S-7a sectors group into the named regions below; every sector record carries its `region_id`. IDs are stable across saves (`11` F-12 keys depletion pools to them; a rebalanced sector list keeps orphaned IDs' depleted state).
- **Vertical special regions**: Europa's sub-ice ocean and Titan's sea floor are distinct regions reachable only via their megaproject content (AN-33/34 chain; `04` M-3f sea ops).

Each region carries exactly ONE exoticism value X — never a range (`11` §3.7 requirement). Values follow `11` §3.7's class table verbatim; rows marked ⁺ are 03-assigned extensions of that ladder (bodies the representative table omits), placed on the same Act/hostility gradient and capped below the X = 14 ocean class.

| Body | region_id : member sectors / span | X |
|---|---|---|
| Earth | EAR-ORB-LEO : ≤ 2,000 km · EAR-ORB-HIGH : high orbit + cislunar · EAR-SURF : all 12 sectors | 1 · 1.5 · 1 |
| Moon | MOO-ORB : orbit · MOO-NEAR : Tranquillitatis, Procellarum, Imbrium, Taurus-Littrow, Aristarchus, Marius Hills, Highlands Near N/S, Tycho · MOO-FARPOLE : Shackleton, Cabeus PSR, N-Pole PSR, Far-side Highlands, SPA Basin | 2 · 2 · 4 |
| Mercury⁺ | MER-ORB : orbit · MER-SURF : 7 non-PSR sectors · MER-PSR : Borealis-N, Kandinsky-N, South PSR | 6 · 7 · 8 |
| Venus | VEN-ORB : orbit · VEN-CLOUD : 4 cloud bands · VEN-SURF : all 8 surface sectors | 6 · 6 · 8 |
| Mars | MAR-ORB : orbit · MAR-SURF : all 18 sectors | 5 · 5 |
| Phobos / Deimos | PHO-SURF : 3 sectors · DEI-SURF : 2 sectors (dock space included) | 5 · 5 |
| NEAs (C/S-type) | one SURF region per body: Bennu, Ryugu, Itokawa, Eros, Apophis + procedural C/S rolls | 4 |
| NEAs (M-type) | one SURF region per procedural M-type | 5 |
| Main belt | CER-ORB · CER-SURF (8 sectors) · VES-SURF (6) · PSY-SURF (5) · HYG-SURF · one region per procedural belt body | 6 (all) |
| Comets | one NUC region per nucleus: 67P, Halley, ~10 procedural | 7 |
| Jupiter | JUP-ATM : probe band (k = 40 milestone key) | 9 |
| Io / Europa | IO-SURF (8 sectors) · EUR-SURF (8); each moon's ORB inherits its X | 10 |
| Europa ocean | EUR-OCEAN : sub-ice (melt-probe megaproject, AN-34) | 14 |
| Ganymede / Callisto | GAN-SURF (10) · CAL-SURF (10); ORBs inherit | 8 |
| Saturn | SAT-ATM : probe band · SAT-RINGS : ring zones A/B/C (§4.4.10) | 10 · 10 |
| Titan | TIT-ORB · TIT-SURF : land sectors · TIT-SEAS : Kraken/Ligeia/Punga + 2 polar lake districts | 10 · 11 · 11 |
| Titan sea floor | TIT-SEAFLOOR : beneath the SEA sectors (submersible content) | 14 |
| Enceladus | ENC-SPT : 4 tiger-stripe sectors · ENC-NORTH : cratered north + sub-Saturn plains | 12 · 10 |
| Uranus system⁺ | URA-ATM : probe band · MIR-SURF (4) · TIA-SURF (4) · OBE-SURF (3) | 11 · 12 · 12 · 12 |
| Neptune system⁺ | NEP-ATM : probe band · TRI-SURF : 6 sectors | 12 · 13 |
| Pluto system⁺ | PLU-SURF : 6 sectors · CHA-SURF : 4 sectors | 13 · 13 |
| KBOs⁺ | one SURF region per body (Arrokoth, Eris, ~8 procedural) — the ×2 "pristine" multiplier (§4.4.13) applies to SurveyData GB, never to X | 13 |

Totals cross-check against `11` §6's act income bands: Act 1 X = 1–1.5 (Earth), Act 2 X = 2–4 (Moon), Act 3 X = 4–5 (Mars/NEAs), Act 4 X = 6–8 (belt, Venus, Mercury⁺), Act 5 X = 8–14 (Jupiter→Saturn ladder, oceans at the 14 cap) — the ⁺ rows extend, but never reorder, that gradient.

## 5. Player Interaction & UI

- **System map** (`12` owns chrome; this file owns content): true-scale 2D map, log-zoom from 0.3 AU framing to 70 AU. Bodies render as discs with exaggeration floor (min 4 px) plus true-scale toggle ("honesty mode" renders the Moon 1.7 px at Earth-frame zoom — the tutorial uses this once, deliberately, to teach scale).
- **Body inspector**: clicking a body opens the §4.1 row as a live panel: g, atmosphere profile plot P(h)/ρ(h), current solar flux, radiation field readout at cursor altitude (S-8 evaluated live), rotation phase, sector ring with day/night shading (S-6a), PSR/PEL badges, comm light-lag to Earth and to player assets.
- **Sector ring UI**: a body's circumference is its sector list (S-7a); hovering shows terrain class, T_day/T_night, dust_index, known deposits (K-state from `04`), anomaly pings (undiscovered = "?" with class-blind ping radius). Landing-target selection = click sector + the orbit-phase indicator shows when your trajectory crosses it (rotation matters).
- **Environment overlays** (toggle layers on the system map): radiation heatmap (S-8c belts drawn as shaded annuli around Earth/Jupiter), solar flux contours, light-lag isochrones, dust-season status icon on Mars (Ls dial with storm warnings), comet activity halos (S-13).
- **Survey workflow**: instrument on ship + orbit inside h_scan → progress bar per S-10; completion fanfare reveals sector ring; anomaly pings then drive expedition planning. All survey states persist per body in the save (schema → `13`).
- **Event feed**: S-14 calendar (launch windows, Halley countdown, solar-cycle phase, Mars Ls), SPE warnings (30–60 min timer, big red banner — the player's cue to shelter crews, `08`), global-storm onset alerts.
- **Time-warp interaction**: warp caps owned by `01`/`13`; this file flags warp-blocking events: SPE in progress with unsheltered crew, eruption events in occupied sectors, comet perihelion ops with anchored assets.

## 6. Progression Hooks

| Act / Tier | Solar-system content unlocked | Gate |
|---|---|---|
| Act 1 (T0–T1) | Earth sectors, LEO/GEO debris salvage (AN-31/32), Moon flybys + L1 lunar survey | starting tech; survey instruments T0 |
| Act 2 (T1–T2) | Moon landings: PSR water (AN-05), lava-tube base (AN-06), mass-driver site survey; NEA flyby missions (Bennu/Ryugu ground-truth) | lunar-rated landers `06`; cryo mining `04` |
| Act 3 (T2) | Mars EDL + dust-season ops, Phobos/Deimos depots, NEA mining; Apollo/Viking heritage tourism contracts (`12`) | NTR or large methalox (`02`); fission surface power (`09`) |
| Act 4 (T2–T3) | Venus aerostats (cloud bands), Mercury terminator ops, Ceres hub, belt C/S/M industry, Psyche metal export | aerostat habs `07`; autonomy ≥ light-lag tier (`05`) |
| Act 5 (T3–T4) | Jupiter ladder (Callisto → Ganymede → Europa melt-probe → Io robotics), Saturn (Titan colony, Enceladus water, ring mining), Uranus/Neptune expeditions | 100 kWe-class fission + MPD/VASIMR-class (`02`/`09`) |
| Endgame (T4) | Pluto/KBO archive runs, He3 scoops [SPECULATIVE], Halley 2061 if window kept, interstellar-precursor staging at 40+ AU | fusion-torch tier [SPECULATIVE] (`02`/`11`) |

Design rule: each Act's flagship body teaches the mechanic the next Act assumes — Moon night→power storage, Mars storms→resilience design, Venus/Mercury→environment-specific engineering, Jupiter→radiation logistics, Saturn→cryogenics; the endgame assumes all five.

## 7. Cross-System Interfaces

**Provides →**
- `01-orbital-mechanics.md`: all GM, R, r_SOI, orbital elements (§4.1–4.3), dir flags, atmosphere ρ(h)/h_atm for drag-aerocapture (S-5a), rotation v_rot launch bonus (S-3), synodic/event calendar (S-14).
- `02-propulsion.md`: ambient pressure for nozzle/back-pressure models (S-5a), atmosphere composition for intake propulsion concepts, dust/abrasion environment flags.
- `04-resources-isru.md`: per-body sector lists with deposit-roll hooks (§4.4 ↔ 04 §4.2 rows MUST stay 1:1), atmosphere/sea datum compositions (§4.1, must equal 04 M-3e/M-3f tables), PSR site tags, asteroid spectral classes & spin states (S-11), solar flux S-4a.
- `05-industry-logistics.md`: light-lag t(r) for autonomy tiers (S-4b), conjunction blackouts, mass-driver site flags (Mercury/Moon), debris-zone salvage.
- `06-ships-stations.md`: dock-mode threshold g < 0.01 m/s² (S-12), eclipse fractions f_ecl (§4.3), landing classes A–F (S-7b).
- `07-bases-habitats.md`: sector environment records (T_day/T_night, P, wind, dust_index, slope), PSR/PEL/TUBE site modifiers, Venus band table (4.4.2), eruption/storm event hooks.
- `08-life-support-crew.md`: radiation field functions S-8a/b/c (ambient values; 08 owns shielding & biology), SPE warning timers, perchlorate toxicity flag (Mars).
- `09-power-thermal.md`: I(t) insolation per S-6a — on Mars f_atm IS f_dust(τ), one attenuation path counted exactly once — plus f_ecl and PSR/PEL overrides per the S-6b single rule; panel soiling is a separate S-9 multiplier. Sky/sink temperatures (T_surf S-6c; deep-space 4 K; Venus surface 737 K radiator wall).
- `10-vehicles.md`: terrain class/slope_sigma/rock_abundance per sector, atmosphere ρ for flight (Titan/Venus/Mars flyers), terminator-chase speed bound (Mercury 3.6 km/h).
- `11-research-tech.md`: science-region partition + per-region exoticism X (§4.7 — 11 §3.1/§3.7 consume; stable region_ids for its Science pools), the canonical anomaly GB→SCI conversion 2 SCI/GB (§4.6, co-signed 11 §3.5), SurveyData yields (§4.6), anomaly unlock effects (§4.5), Europa-ocean and He3 gated content tags.
- `12-gameplay-economy-ui.md`: heritage-zone rules, Prestige rewards, contract seeds (sample return, Hubble boost, Venera recovery), map-UI content (§5).
- `13-architecture.md`: entity schemas implied by S-1/S-7a records, anomaly persistence, event calendar serialization.

**Consumes ←**
- `01`: patched-conic propagator, SOI transition logic, canonical Δv map (this file's Δv column is indicative only).
- `04`: deposit object model (M-1), K-ladder (M-2) that S-10 layers wrap.
- `09`: power availability feedback for survey instruments (powered flag in S-10).
- `11`: tier gates consumed by §6 table.
- `12`: time-warp UI, notification framework for S-14 events.

## 8. Failure Modes & Edge Cases

- **Kepler solver near e → 1** (Halley e = 0.967, procedural comets): Newton iteration on E diverges from M seed near perihelion; use Markley/Danby starter or bisection fallback; unit test at e = 0.99, M = 0.001 rad. (Implementation note for `01`/`13`; listed here because this file ships the offending elements.)
- **Pluto–Neptune phasing**: if a modder/world-gen edit changes M0, the 12-AU separation guarantee breaks silently. Canonical values (Pluto M0 = 86.0°, ϖ = 224.1°; Neptune M0 = 7.0°, ϖ = 45.0°, §4.2) give a verified minimum separation of 18.3 AU. Validate at world-gen: min distance over one 495-yr synodic cycle ≥ 12 AU, else re-seed Pluto M0.
- **Retrograde rendezvous UX**: players will burn prograde at Halley/Triton out of habit and produce 60+ km/s flyby disasters; UI must show closing speed in red when dir mismatch (hook for `12`).
- **PSR contradiction**: PSR sectors with I = 0 must never receive S-6c day-side temperatures; enforce PSR flag overrides T_day := T_night. (Bug class: sector flag forgotten after deposit instantiation.)
- **Mercury terminator drift vs warp**: at 10^6× warp the 3.6 km/h terminator crosses a parked rover in seconds of real time; thermal damage must integrate analytically across warp steps, not per-frame, or warp kills rovers unfairly (rule: clamp T_surf change per real-frame, apply energy integral).
- **Venus aerostat altitude excursions**: ρ(h) exponential + balloon model can oscillate; band table (4.4.2) is the truth source — clamp simulation to 45–65 km envelope, destructive below 42 km (T > 380 K electronics kill line).
- **Mars storm during EDL**: if global storm spawns while a ship is mid-transfer, EDL dispersion ×2 applies on arrival; guarantee the warning fired at storm onset (S-9) so the player could divert to Phobos — never spring it silently.
- **Eclipse vs PSR double-counting**: single rule per S-6b — f_ecl applies to ALL assets inside a moon's SOI, orbiting AND landed (an Io solar farm is in Jupiter's shadow 5.4% of the time; a Phobos surface array 12%); PSR/PEL-flagged sectors override insolation entirely and take no f_ecl. Assert mutual exclusion of (PSR/PEL override path) vs (f_ecl path) — NOT surface vs orbit.
- **Dock-mode boundary**: bodies near g = 0.01 m/s² (Phobos 0.0057) must not flip modes with radius refinements; mode is a fixed per-body flag at world-gen, not computed live.
- **Anomaly heritage-zone griefing**: mining inside 10 km of AN-01-class sites triggers `12` penalties; ensure procedural deposit rolls never place a K2-mandatory deposit *only* inside a heritage zone (re-roll rule).
- **Atmosphere drag cutoff popping**: the bare exponential H·ln(P0/P_cut) gives Titan only ≈ 422 km — it is the stored §4.1b h_atm override (1,400 km, hot extended thermosphere) that makes 1,000–1,400 km Titan parking orbits decay. Real anchor: Cassini's low Titan flybys (~950–1,200 km) met measurably higher atmospheric drag than predicted, forcing the project to manage flyby altitudes and fight aerodynamic torque (Cassini never actually aerobraked at Titan). Same mechanism at Earth: the 600 km override is what makes 400-km LEO stations decay and station-keep. Ships parked below h_atm decay; UI must warn rather than silently decay during warp.
- **Solar-cycle extremes**: f_cycle 0.65–1.35 must clamp; SPE lognormal cap 2,000 mSv prevents RNG one-shot kills of sheltered crews (shelter math in `08` assumes this cap).
- **Procedural overlap**: world-gen must reject procedural NEA elements that duplicate curated bodies within Δa < 0.01 AU ∧ Δe < 0.02 (map clutter + lore conflicts).
- **Comet exhaustion**: S-13 coma capture is flavor-scale; assert total capture per perihelion < 10 t so comets never out-compete Enceladus/Ceres industrial water (balance guard).

## 9. Open Questions

1. **Procedural belt density**: 120 belt objects is a map-readability guess; does the Act 4 economy need more M-types, or does Psyche alone carry the metal endgame? (Blocks `05` freighter sizing.)
2. **Venus surface tier**: is T3 high-temperature electronics (NASA HOTTech SiC anchor) enough for *crewed* surface sorties, or should crewed Venus surface remain impossible forever (robots only)? Realism reviewers lean "robots only"; gameplay wants the trophy. Decide with `07`/`08`.
3. **Io geothermal taps**: flagged [SPECULATIVE T4 flavor, 100 kWt cap] here — keep, or cut as too handwavy despite tidal-heating physics being sound? (`09` to rule.)
4. **Ring mining tag**: currently T3 with an honesty note; should it move to T4 [SPECULATIVE] since no engineering study exists at scale? (`11` tier owner to rule; physics is trivial, optics are gamey.)
5. **2049 future-history canon**: which 2026–2049 missions exist as derelicts (Artemis surface assets, Mars Sample Return state, Dragonfly end-of-mission location at Selk)? Needs a one-page canonical timeline shared with `12` narrative; current §4.5 assumes conservative versions.
6. **Pluto atmosphere collapse rate**: the exp(Δr/2.5 AU) freeze-out is a placeholder; New Horizons-era models disagree on full-collapse timing. Does any mechanic actually depend on it, or demote to flavor? 
7. **Procedural KBO count (8)**: enough for the interstellar-precursor staging gameplay, or does the endgame need a Centaur population (Chiron) between Saturn and Uranus as stepping stones?
8. **Earth weather/spaceport events**: kept minimal here (p = 0.02 scrub); `12` may want a richer launch-cadence economy — if so, that system should own the model and this file just hosts the sector list.
9. **Saturn ring zone vs moonlet mining**: would harvesting Saturn's small inner moonlets (Pan, Daphnis-class, not yet rostered) be cleaner than the ring-zone abstraction? Adds bodies but removes the zone-object special case (`13` complexity trade).
10. **Radiation model honesty band**: S-8c reproduces Ganymede at 160 vs literature ~80 mSv/day before the B-field factor; hostile reviewers may flag the fudge. Alternative: piecewise-linear through all four anchors (uglier code, exact anchors). Decide before implementation freeze.
