# BUILD SPEC — Visual Direction & Rendering

Extracted from `design/90-14-visual-direction-rendering.md` (doc 14, design-complete) + binding
rulings from `design/DECISIONS.md` (A7, C23, C24, D29, D30, G35a — DECISIONS wins conflicts).
Implement from this document without re-reading the original; VD-## rule IDs preserved.
Ownership: doc 14 owns *what the game looks like* and the GPU path. 13 §3.13 owns the SOFTWARE
render path internals (7.0 ms cap, unchanged). 12 §5.7 owns semantic color tokens (14 extends,
never overrides). Gap-check against v2.1 code in §4.

---

## 1. ART DIRECTION CANON

### 1.1 The four pillars (binding; every visual decision traces to one)

- **VD-P1 — Instrument first.** At gameplay zoom the screen is a readable engineering drawing.
  The HUD/UI layer composites *after* all post-processing and is **never** bloomed, blurred,
  graded, grained, or color-shifted. Beauty loses to legibility, always.
- **VD-P2 — The physics is the animator.** Nothing moves/glows/flashes/shakes unless a sim
  quantity drove it (02 thrust, 09 temperature, real acceleration, 09 eclipse events). No "juice"
  track. Filming the screen should let you reverse-engineer the physics.
- **VD-P3 — Painterly depth behind the glass.** Below the vector layer: real-catalog starfield,
  zodiacal light, atmosphere gradients, terminator shading, dust. Gorgeous is allowed because it
  never carries gameplay-critical meaning alone.
- **VD-P4 — Archival memory.** Chronicle cards, photo mode, endgame export render in a
  1960s–70s mission-print idiom (cyanotype, mission patches, warm archival paper). Played on a
  monitor, remembered as a document.

### 1.2 Layer stack — compositing order (binding, both paths)

Back to front (D = drawn on CPU pygame surface and streamed; G = generated on GPU):

| # | Layer | Source | Updates | Post applied |
|---|---|---|---|---|
| 1 | Starfield (Yale Bright Star Catalog 9,110 stars to V 6.5 + procedural fainter extension; magnitude→PSF, Hipparcos color tints) | G | on zoom-band / pointing change | grade |
| 2 | Zodiacal light / milky-way band | G | per frame (cheap quad) | grade |
| 3 | Atmosphere & sky gradient (world card) | G | per frame | grade |
| 4 | World vector layer (orbits, bodies, terrain, sprites) | D, 8.29 MB @1080p | per frame | grade |
| 5 | FX particles (instanced additive point sprites) **+ sun disc billboard** (assigned here so bloom never samples layer 4) | D (instance buffer ≤ 320 KB) + G | per frame | **bloom** + grade |
| 6 | Lighting multiply (terminator/eclipse/night) | G | per frame | — |
| 7 | HUD/UI (per-widget textures, dirty-upload) | D, dirty regions only | on change | **none — VD-P1** |

Post stack: bloom (threshold luma > 0.75, half-res 960×540, 2-pass separable Gaussian σ = 6 px,
additive recomposite, **layer 5 only**) → color grade (32³ 3D LUT from active world card + photo
filter; identity when off) → final blit + HUD on top, untouched.

**Starfield honesty (§2/VD-19):** stars are at parsec distances — they **never parallax** under
camera pan (fixed backdrop is both cheap and honest). The only layer allowed to parallax is
zodiacal light (dust physically at AU distances), SYSTEM layer only. Magnitude floor deepens with
zoom-in (longer-exposure metaphor) for continuous depth feedback.

### 1.3 Per-world visual identity cards

Shipped as **data** (TOML, pack-patchable, validated at load per 13 §3.4). Schema field names
binding:

```toml
[world.mars]
body = "core:mars"               # 03 body id (referential check)
space_or_sky = "sky"             # "space" = vacuum bodies
sky_zenith_day   = "#C28E5C"
sky_horizon_day  = "#E3B584"
sky_twilight     = "#8FA8C8"     # sun-centered halo color
sky_night        = "#0A0E14"     # converges to 12 §5.7 background
light_cct_k      = 4800          # display white-balance cast of sunlight
sun_disc_deg     = 0.35          # must match 2·atan(R_sun/d) from 03 within 10%
ambient_night    = 0.06          # lighting floor L_amb
terminator_soft  = 0.30          # 0 = knife edge (airless), 1 = full haze
dust             = "suspended"   # none | ballistic | suspended
weather          = ["dust_storm"]# 03-owned events only (DUST_STORM_IN/OUT)
grade_lut        = "core:lut/mars_day"   # GPU only
```

Complete initial card set (hexes are shipped defaults, data-patchable):

| Card | Sky/space day | Twilight/limb | cct K | amb_night | dust | Signature treatment (anchor) |
|---|---|---|---|---|---|---|
| earth | zenith `#3D6FB8`, horizon `#A8C8E8` | warm `#E8A05C` | 5900 | 0.18 | none | Rayleigh blue, thin limb line; city-glow specks night side (DMSP) |
| earth_orbit | space `#0A0E14` | airglow arc `#5C8A6E` | 5800 | 0.10 | none | ISS night-pass airglow band at the limb |
| moon_day | black `#05070A` | none | 5800 | 0.06 | ballistic | knife-edge terminator, terminator_soft = 0 (Apollo) |
| moon_psr | black `#05070A` | none | — (no sun) | 0.02 | ballistic | floodlight-only; rim sunlight as a distant white wall (LRO Diviner) |
| mercury | black `#05070A` | none | 5800 | 0.05 | ballistic | ×6.7 sun-disc brightness, darker regolith than lunar maria (MESSENGER) |
| venus_aerostat | diffuse `#E8DCAE` | `#C8A86E` | 5200 | 0.30 | suspended | shadowless yellow-white cloud glow at 50 km (HAVOC) |
| mars | zenith `#C28E5C`, horizon `#E3B584` | **blue halo `#8FA8C8`** | 4800 | 0.06 | suspended | butterscotch day / **blue sunset inversion** (Pathfinder; Curiosity Sol 956) |
| phobos_deimos | black `#05070A` | none | 5700 | 0.04 | ballistic | Mars fills the sky from the sub-Mars sector |
| asteroid_belt | black `#05070A` | none | 5800 | 0.03 | ballistic | dock-mode: slow body rotation is the only motion |
| ceres | black `#05070A` | none | 5800 | 0.03 | ballistic | bright crater faculae accents (Dawn, Occator) |
| europa | black `#05070A` | none | 5800 | 0.05 | ballistic | Jupiter disc dominates; cold blue-grey ice (Galileo) |
| titan | haze `#C87A32` zenith → `#A85E28` horizon | none — **no solar disc** | 3800 | 0.35 | suspended | shadowless orange gloom, 0.1% illuminance via VD-9 (Huygens DISR) |
| saturn_titan_orbit | space `#0A0E14` | ring-light fill `#D8C8A8` | 5700 | 0.08 | none | rings as the light source on night sides |
| pluto_kbo | black `#05070A` | none | 5800 | 0.02 | ballistic | "Pluto Time" twilight under True-Lux; N2-ice blue-white accents |
| deep_space | black `#05070A` | zodiacal wedge | 5800 | 0.0 | none | starfield + zodiacal only |

Act mood arc (progression delivers new light, never new fidelity): Act 1 blue-white familiar →
Act 2 monochrome severity (moon) → Act 3 warm Mars inversion → Act 4 Mercury glare vs Venus
gloom → Act 5 dim ring-lit Pluto twilight. Two skies in Act 1 grow to fifteen by Act 5.

**VD-7 (load-time validation — content load FAILS on violation).** Per card: all **ten** 12 §5.7
semantic tokens — player cyan `#57C7E3`, inert grey-white `#9AA7B0`, nominal green `#44CC77`,
caution amber `#E8C547`, warning orange `#E8893B`, emergency red `#E25555`, radiation magenta
`#C678DD`, cryo/water blue `#5398D9`, thermal deep-orange `#D97E4A`, money/Prestige gold
`#D9B354` — must hold contrast ratio ≥ 3.0 against *every* sky gradient stop (this enumerated
list is the validator's binding input). HUD text ≥ 4.5:1 vs HUD backplate (world-independent,
checked once). `sun_disc_deg` cross-checked vs 03 within 10%; `body` must exist. A modded pretty
sky that hides a red alert is a build error.

**VD-8/VD-28 (colorblind).** Colorblind modes swap *semantic tokens only* (data swap, zero
per-pixel cost, works on every degradation rung, never implemented inside a LUT). 12 defines the
deuteranopia set today; protan/tritan are proposed 12 extensions. World cards are decorative and
never swapped.

### 1.4 Typography & color tokens

- Semantic tokens + alert classes: owned by 12 §5.7 (the ten hexes above). World-card hexes are
  decorative and live in TOML, not code constants.
- SYSTEM map layer uses **only** the 12 §5.7 base palette — the map is an instrument, never
  world-graded (VD-21); world-card grading begins at LOCAL when the body disc subtends > 32 px,
  ramped over one zoom-band step.
- Any label drawn over the painterly stack gets a 70%-opacity `#0A0E14` auto-backplate (VD-27).
- Print idiom anchors: cyanotype (Herschel 1842), NASA Graphics Standards Manual 1976,
  embroidered crew patches.

### 1.5 UI density & motion rules

- **VD-25:** numeric readouts sample values at ≤ 10 Hz (rendered per-frame from the glyph
  atlas); final value exact on settle.
- **VD-18 (icon↔sprite band):** crossfade as rendered size moves 56 → 72 px (opacity sum = 1;
  icon scales 0.9→1.1 across the band so it reads as approach). < 56 px icon only; > 72 px
  sprite only.
- **VD-19 (scale honesty):** a powers-of-10 scale ruler (1 px ticks, m/km/AU) is visible during
  any zoom motion + 1 s after.
- **VD-20 (layer handoffs, on 13's 150 ms crossfade):** SYSTEM↔LOCAL icon blossoms into the lit
  disc (terminator already correct); LOCAL↔SITE landed craft stays screen-fixed, sky gradient
  fades in over 150 ms; SITE↔INTERIOR 150 ms iris wipe on the hatch, exterior light visible
  through windows.
- First-arrival vista: on each body's first SOI_ARRIVAL, a 2 s exposure-adaptation ramp (sim
  unpaused, camera untouched) + photo-mode toast. Skippable, never repeats.
- Encyclopedia: each world card gets a "Why does it look like this?" page citing its real anchor.

### 1.6 2D lighting model (billboards only — no 3D, no normal maps)

- **Sun direction.** LOCAL: `sun_dir = normalize(r_sun − r_body)` from 01/03 ephemeris. SITE:
  solar elevation from 03 S-6a sun-cosine `c_sun(t)`, `e(t) = asin(c_sun)`; poles/PSRs use S-6b
  insolation-flag overrides (no latitude field exists). 09's daylight flag `L` (120 s penumbra
  ramp) is the binding day/night truth — lighting consumes 09, never recomputes.
- **Illumination.** `L_v = clamp(L_amb + (1 − L_amb)·max(0, cos θ_sun)·L_ecl, 0, 1)`;
  `L_amb` = card `ambient_night` (airless ≤ 0.08; Titan 0.35).
- **Terminator (LOCAL discs).** Gradient band width = `terminator_soft × 0.25 × R_px`, min 1 px.
  Atmosphere bodies add a limb-glow annulus, thickness `min(8·H, 0.1·R)` (H = 03 scale height),
  tinted `sky_horizon_day`.
- **Shadows (SITE).** One sheared darkened silhouette per structure/vehicle along −sun_dir,
  length factor `min(cot e, 8)` with `cot e = √(1 − c_sun²)/c_sun`. PSR sectors: permanent
  L_amb-only; player floodlights (07 items) are the only local lights — additive radial
  gradients, 1/r² falloff, **cap 32 light billboards per site** (beyond: merged ambient lift).
- **Eclipse/night.** ECLIPSE_IN/OUT + TERMINATOR events (13 §4.4) drive whole-layer luminance
  ramps over the 120 s penumbra (instant at high warp per VD-16/17).
- **Hull specular.** 1–3 px rim highlight on the sun side, ∝ max(0, cos θ). SOFTWARE: sun
  quantized to 8 sectors, rim pre-baked into the vessel surface cache (cache ×8, no per-frame
  cost). GPU: trivial rim shader.
- **VD-9 (auto-exposure with a confession).** Display exposure normalizes mean world-layer luma
  to 0.45; mood is carried by CCT cast, contrast, `ambient_night` (real scale: 133 klx Earth →
  57 klx Mars → 5 klx Jupiter → 85 lx Pluto). Photo mode has a **True-Lux toggle** that disables
  normalization and stamps measured illuminance on the export.

---

## 2. FX CANON — physics in, photons out

Every emitter is keyed by sim state from the owning doc; **no FX exists without a driver**.
Particles: numpy SoA per 13 §3.13. Caps: **SOFTWARE 4,000 live** (13's binding cap) /
**GPU 20,000** (instanced). **VD-10 starvation priority** when a cap binds, culled in reverse
order: cosmetic dust < plumes < RCS < reentry < **venting/breach (never starved)** — anything
that is also an alarm gets photons first.

### 2.1 Plume optics per propellant (driver: 02 thrust/throttle/family, p_amb from 01/03)

Visible length `L_p ≈ k_f·√(F/kN)` m; throttle scales `L_p ∝ √(x·F)`. Ignition transient = 4-frame
overbright pop (within VD-22). Per-emitter caps SOFTWARE/GPU:

| FX | Color core→edge | k_f (m/√kN) | Cap S/G | Anchor |
|---|---|---|---|---|
| Kerolox SL (K-845) | `#FFD27A`→`#E8893B`, sooty orange | 2.2 | 600/3,000 per engine | Merlin/F9 |
| Methalox SL (M-2256) | `#9AB8FF`→`#6E7AE8`, crisp diamonds | 1.6 | 600/3,000 | Raptor |
| Hydrolox (H-2280) | near-transparent `#C8D8FF`, bright Mach disc | 1.0 | 400/2,000 | RS-25 |
| Solid (SRM-2/49) | white `#FFF4E0`→`#FFB36E`, opaque, smoky | 3.0 | 800/4,000 | APCP Al2O3 |
| Hypergolic (OMS-27, LND-71) | faint pink `#E8A8A0`, translucent | 1.2 | 300/1,500 | Shuttle OMS |
| Vacuum (any family) | family color, opacity ×0.15, 25° half-angle, core ×0.25 | — | same | Apollo LM ascent (invisible) |
| Ion/Hall beam | Xe `#7AB8E8`; Ar/Kr `#A89AE8`; thin additive beam 4–10 m, opacity ∝ P_in/P_max | — | 100/400 | NSTAR/Dawn, SPT-100 |
| RCS puff | white `#E6EDF3`, 40 particles, 0.3 s life, aligned to actual firing nozzle vector | — | 40/puff | Shuttle PRCS |
| NTR | **no visible exhaust** (hot H2 transparent); incandescent nozzle skirt ramps toward dull orange (Draper-consistent) + heat-shimmer billboard when p_amb > 1 kPa; LANTR O/F mode gains a real pale flame | — | 0 particles | NERVA |

**Shock diamonds:** render only in atmosphere when `p_e/p_amb ∉ [0.8, 1.25]`; cell spacing is
Prandtl–Pack `x_s = 1.31·D_e·√(M_j² − 1)` (≈ 4–5·D_e for booster-class M_j 3.4–4.0); brightness
∝ family soot/Al loading. 02 publishes no exit-plane data, so visual-domain defaults (photons
only, never thrust; proposed 02 columns):

| Engine | p_e (kPa) | M_j | D_e (m) | D_e source |
|---|---|---|---|---|
| K-845 "Mule" | 70 | 3.4 | 0.93 | derived: A_e = (F_vac−F_SL)/101.325 kPa = (914−845)/101.325 |
| M-2256 "Drayhorse" | 80 | 4.0 | 1.32 | derived: (2394−2256)/101.325 |
| H-2280 "Shire" | 13 | 3.8 | 2.29 | derived: (2279−1860)/101.325 |
| MV-2530 "Drayhorse-V" | 3 [est] | 4.6 [est] | 2.4 [est] | pinned (vacuum-rated) |
| SRM-2 / SRM-49 | 60 | 3.0 | 0.5 / 1.5 [est] | pinned |
| OMS-27 / LND-71 | 10 | 3.2 | 0.6 [est] | pinned |

p_e/M_j are per-engine constants (consistent with 02's fixed-exit-area model). EP/NTR/RCS never
render diamonds. EP at LOCAL zoom collapses to a 1 px tick — an ion burn is information (thrust
chevron), not spectacle (VD-P1).

**DECISIONS D29 (binding, supersedes doc 14 §9-Q6's v1 default):** plumes are a **parametric GPU
mesh** (length/diamond spacing analytic from the rules above) **with a sprite fallback toggle**;
gate Phase 2/3. Particle caps in the table drop where the mesh replaces particles.

### 2.2 Other emitters

- **Surface dust** (driver: 10 vehicles, 02 plumes; regime from card `dust`):
  `ballistic` (vacuum) = real parabolas under local g, **no billowing, no suspension** (LRV
  rooster-tails); landing plumes throw < 3° high-speed ejecta sheets out to 10 §3.6.3's 200 m
  sandblast radius — making C23's plume-scouring hazard *visible*. `suspended` (atmosphere) =
  billowing clouds, settling time ∝ 1/ρ_atm; Mars dust storms (03 events, C24 live from Act 3)
  are a whole-scene τ-based contrast/color wash on the lighting layer, **not** particles. Dust
  devils: statistical visual only (deterministic-seeded columns), never a 03/13 event. Caps
  1,200/6,000 each regime.
- **Reentry plasma** (driver: 01 Sutton–Graves q̇): onset q̇ ≥ 5 W/cm² faint glow; full sheath
  ≥ 50 W/cm² (rate ∝ q̇·A_ref). Color by atmosphere: N2/O2 warm pink-orange `#FF9A7A`; CO2
  (Mars/Venus) pale blue-white `#A8C8E8`. Sheath visually swallows the craft exactly during 01's
  comm-blackout window. Cap 800/4,000.
- **Venting/breach** (drivers: 07 breach, 08 rapid-depress, 02 boiloff): collimated white
  ice-crystal jets `#F0F4F8`, length = 10·√(ṁ/kg·s⁻¹) m, aligned to breach normal, imparting
  06's real reaction torque. Boiloff = same jet at low ṁ on relief-valve schedule. Cap 200/800,
  **never starved**.

### 2.3 Incandescence honesty (VD-13)

Diegetic glow only at T ≥ **798 K (Draper point)**: NEP radiators (800 K class) faint dull red;
reentry TPS; nozzle skirts. ISS-style 275 K / Kilopower 400 K radiators **do not glow, ever**.
Everything else is the explicit thermal overlay (engineering toggle, HUD layer, INSTRUMENT
watermark): 250 K deep blue → 400 K green → 800 K orange → 1,000 K white, from 09 node temps.
Endgame fusion (NUK-FUS, 900 K radiators per 09) honestly glows red.

### 2.4 Animation standards

- **VD-11:** deployables tween over the *sim's* deployment duration; if warp jumps the state,
  the sprite jumps. Defaults (proposed 06/09 amendments, owned here until ratified): solar wing
  **120 s**, radiator **90 s**, landing gear **6 s**.
- **VD-12:** nozzles rotate to the actual commanded gimbal angle at the actuator's real slew
  rate (02 §3.6) — you can watch a control loop hunt.
- **VD-14:** beacons/strobes 1 Hz default, hard ceiling 3 Hz, duty ≤ 20% (docking lights, pad
  perimeter, Master Alarm lamp).
- **VD-15:** v1 interior crew = status icons in cells (12 icon grammar), ≤ 1 Hz two-frame tick.
- **VD-16 (warp truth table):**

| Warp | Plumes/RCS | Strobes | Dust/weather | Day/night & eclipse |
|---|---|---|---|---|
| 1–10× | full FX | blink | full particles | 120 s penumbra ramps |
| 10–1,000× | steady-state plume, no flicker | steady glow | statistical wash | ramps compressed, min 2 frames |
| > 1,000× | thrust drawn as colored trajectory arc segments (Planner vocabulary), no particles | steady glow | suppressed | time-averaged (VD-17) |

- **VD-17 (eclipse-flicker clamp, photosensitivity-critical):** at warp w, period T, if apparent
  day/night frequency `f_app = w/T > 0.5 Hz`, replace per-event lighting with
  `L̄ = (1 − f_ecl)·L_day + f_ecl·L_night` (f_ecl from 09 P-10). Keys on the current rev's
  shadow-crossing interval so elliptical orbits don't flicker either.

### 2.5 Camera & alert grammar

- **VD-23 (no arcade shake):** camera offset only from physical acceleration:
  `offset_px = min(16, 24·|a|/g0)` opposite the accel vector, low-passed at 2 Hz. Contact:
  single critically damped (ζ = 1, 400 ms) kick of `min(20, 6·Δv_contact/(m/s))` px. **No
  random/Perlin camera noise exists in the codebase.** Engine roughness: blocked on a proposed
  02 σ_F output; until ratified the accelerometer needle is steady.
- **VD-24 (alert grammar, with 12 A-1):** Class 1 EMERGENCY = 0.8 Hz *sinusoidal* red vignette
  ≤ 8% screen area + 12's klaxon. Class 2 WARNING = steady orange HUD border, one 200 ms onset
  pulse. Class 3 CAUTION = amber badge on the owning gauge. Class 4 ADVISORY = toast. No alert
  ever moves the camera or blurs the screen.

### 2.6 Photo mode & Chronicle print filters (12 C-5 names; recipes owned here)

| Filter | Recipe | Anchor |
|---|---|---|
| Blueprint | luma → duotone ramp Prussian blue `#13294B` → paper `#E8EDF2`; all lines white; fills dropped; **2% paper-grain noise**; title block (craft name/date, 12 caption grammar) | cyanotype 1842 |
| Mission-Patch | posterize 6 levels; semantic colors → flat saturated fills; 3 px outlines; circular crop, gold ring `#D9B354`; mission-name arc text; procedural emblem seed (12 C-4) | crew patches |
| Archival-Print | invert to warm paper `#F4EFE6`, dark ink lines `#2A2E33`; **10% halftone dot on fills**; 0.3% chromatic offset; date/frame-number margin stamp | NASA press kits, 1976 GSM |
| True-Lux (modifier) | disables VD-9 exposure normalization; stamps measured lx on the export | "Pluto Time" |

Photo mode (S-19, 12 owns the screen): line-weight boost ×1.5 + these recipes.
**VD-26 (path-independent archive):** photo exports, Chronicle vector snapshots, endgame poster
always re-render through the **SOFTWARE vector rasterizer** at export resolution (up to 4×),
filter LUTs applied in that offline pass (numpy float64). Same platform + build ⇒ identical
pixels (D30: per-platform bit-exactness is the v1 promise; cross-machine exactness is §9-Q8, not
promised). Snapshots store world-card id + filter id at capture so re-renders survive mod
patches.

### 2.7 Accessibility budget (binding)

- **VD-22 (WCAG 2.1 §2.3.1, strict):** nothing flashes > 3 Hz; simultaneous flashing area < 10%
  of screen; no red square-wave flashes; ignition pops ≤ 4 frames and ≤ 10% screen. **Reduced
  Flash** setting: every strobe → steady +20% brightness; Class-1 vignette pulse → steady
  border. CI scene PERF-V3 runs an automated flash-frequency audit (frame-differencing, 600
  frames).
- **VD-27 (contrast floors):** HUD text ≥ 4.5:1 vs backplate; all vector chrome ≥ 3:1 vs any
  background — enforced at load (VD-7) and at runtime by the 70% `#0A0E14` auto-backplate.
- **VD-28:** colorblind sets are pure data swaps, available and identical on every degradation
  rung, never inside a LUT.
- **VD-29 (motion):** settings to disable camera accel offset, zoom crossfades (cut instead),
  zodiacal parallax. None change sim behavior.
- Visual fidelity is **never** a progression reward; no tech node gates rendering features.

---

## 3. PIPELINE — pygame-ce + moderngl hybrid

### 3.1 Two paths, prime contract

| Path | Stack | Status |
|---|---|---|
| **SOFTWARE** | pygame-ce/SDL2 software blits, exactly 13 §3.13 | **Canonical.** Always shipped, CI baseline, 7.0 ms render cap untouched. |
| **GPU-COMPOSITE** | pygame draws layers to CPU surfaces → streamed to moderngl textures → GPU composites + post | Enhancement. Auto-selected; degrades cleanly to SOFTWARE. |

- **VD-1 (meaning preservation, CI golden-image test):** with all post passes disabled, GPU
  composite of the same layer surfaces must match SOFTWARE within mean |Δ| ≤ 1/255 per channel;
  ≤ 0.5% of pixels may exceed 16/255. AA exemption is mechanical: the vector rasterizer emits a
  per-golden-frame mask of pixels within 1 px of any stroke; only masked pixels are exempt from
  the outlier count (they still count toward the mean bound); the mask ships in the artifact.
- **VD-2 (dependencies):** pygame-ce + numpy + *optional* moderngl ≥ 5.10, imported inside a
  guard in `render/gpu/`. ImportError, GL < 3.3 core, or blacklisted/llvmpipe renderer string ⇒
  SOFTWARE, logged once, surfaced in Settings. `sim/` still imports numpy only (CI import-graph
  test). **Shader target: GL 3.3 core, desktop-only v1 — DECISIONS G35a, resolved.** No ES 3.0
  hedge in v1.
- **VD-3 (CPU surfaces authoritative):** every dynamic layer exists as a pygame surface;
  GL context loss ⇒ next frame renders SOFTWARE losslessly (Class-4 advisory, one background
  re-init attempt — no frame is ever black). Screenshots/exports are path-independent. The GPU
  is a compositor, never the system of record.
- **VD-5 (bloom legibility):** bloom threshold pass samples **layer 5 only** (FX + sun-disc
  billboard). Semantic alert colors never bloom. An emergency is red because 12 says so, not
  because it glows.
- **VD-6 (grade by token):** SOFTWARE world mood comes from the card's pre-graded palette
  tokens; live LUT grading is GPU-only. SOFTWARE applies LUTs only in photo mode (paused; a
  50 ms numpy pass is fine).

### 3.2 Budgets (proposed; 13 ratifies — SOFTWARE column binding and unchanged)

**Targets:** GPU path 60 fps @1080p on Intel UHD 620-class with full post; 60 fps @4K on
GTX 1650/RX 6400-class. CPU render work on the GPU path fits the **same 7.0 ms cap**; GPU work
≤ 6.0 ms on baseline iGPU, overlapped with next frame's sim.

CPU render @1080p (ms): starfield+world vector 3.5 SW / 2.9 GPU-path · sprites/sites 2.0 / 1.5 ·
FX numpy update+instance pack — / 0.6 · text+HUD 1.5 / 1.4 · texture uploads — / 0.6 ·
**total 7.0 / 7.0 (hard cap both)**.

GPU passes @1080p UHD 620 (ms): starfield+zodiacal 0.4 · sky gradient+limb 0.1 · layer composite
0.5 · particles ≤20k 0.5 · lighting multiply 0.2 · bloom 0.8 · grade LUT+final 0.4 · HUD
composite 0.2 · **total 3.1 ≤ 6.0 budget**.

**VD-4 (upload budget):** streamed bytes ≤ 12 MB/frame @1080p (world 8.29 + FX 0.32 + HUD dirty
< 1) ≈ 0.5 ms at 25 GB/s, budgeted 0.6. At 4K the world layer renders 1080p and GPU-upscales ×2
integer; HUD renders/uploads native, dirty-only. Full-HUD 4K redraw (~33 MB) is a 1-frame spike,
legal on screen transitions only; > 3 consecutive frames ⇒ HUD streams at 1440p integer-scaled +
perf-HUD log.

### 3.3 Degradation ladder (auto when GPU frame > 12 ms sustained 120 frames; each step logged)

| Rung | Action | Lost |
|---|---|---|
| L0 | full GPU path | — |
| L1 | bloom off | glow |
| L2 | particle cap 20,000 → 8,000 | FX density |
| L3 | grading LUT → identity (tokens keep mood; colorblind unaffected) | continuous grade |
| L4 | SOFTWARE path (= 13 §3.13 exactly) | parallax/zodiacal, GPU particles |

### 3.4 CI & failure modes

- New perf scenes (into 13 §3.14/§3.16): **PERF-V1** Max-Q nine-engine kerolox ascent;
  **PERF-V2** Mars dust-storm EDL with plasma sheath (also asserts VD-10 priority under
  oversubscription); **PERF-V3** lunar-night base, 60 conics, beacons (doubles as VD-22 flash
  audit); **PERF-V4** 4K Planner HUD-heavy (VD-4 spike check). Headless CI: GPU scenes on
  llvmpipe assert correctness only (VD-1 goldens, SSIM ≥ 0.995); timing nightly on a reference
  UHD 620. SOFTWARE timings keep 13's ×3-slack rule.
- **sRGB double-gamma trap:** sample pygame surfaces as UNORM (no auto sRGB decode), apply LUT
  in encoded space — or whites clip and VD-1 fails (that's why it's a CI test).
- **llvmpipe masquerade:** GL_RENDERER containing `llvmpipe`/`softpipe` ⇒ no-GPU. Blacklist is
  data (13 §3.4 pack).
- **Mod LUT crushing alerts:** grade LUTs checked at pack load to keep ΔE between any two
  semantic tokens ≥ 50% of ungraded ΔE; VD-7 re-validates CR per pack.
- **Warp plume lies:** >1,000× burning craft renders thrust as trajectory arc segments (Planner
  vocabulary), never a realtime plume.

### 3.5 Settings & HUD

Settings → Graphics: render path Auto/Software/GPU · bloom · world grading · particle density ·
Reduced Flash · motion switches · colorblind set · exposure mode · integer UI scale. Every
toggle states its honest cost. Perf HUD on **Ctrl+F3** (DECISIONS A7 — F3 is the Planner):
adds GPU frame ms, upload MB/frame, active degradation rung + reason.

### 3.6 DECISIONS rulings binding this domain

A7 (Perf HUD Ctrl+F3) · C23 (plume–surface scouring IN — the 200 m ejecta visual is load-bearing)
· C24 (Mars density ±50% — dust-storm visuals live ops from Act 3) · D29 (plumes = parametric GPU
mesh + sprite fallback toggle, Phase 2/3 gate) · D30 (determinism per-platform only) · G35a
(GL 3.3 core, desktop-only v1).

---

## 4. GAP vs CODE (v2.1 "THE LOOK UPDATE" software pass)

What exists in `aphelion/` today vs this spec. v2.1 built a good *generic* software look; almost
none of doc 14's *specific* canon is implemented.

| Area | Code today | Spec requires | Gap |
|---|---|---|---|
| World identity cards | Three independent hard-coded palette systems: `render/surface_art.py` `SKY_PALS`/`GROUND_PALS` (5 skies: earth/mars/titan/venus/default — non-canon hexes, e.g. Mars zenith (86,58,44) vs `#C28E5C`), `render/base_art.py` `_KIND_PAL` (5 site kinds), `render/body_art.py` per-body palettes | One TOML card per environment, §1.3 schema + 15-card table, VD-7 load validator | **Total.** No TOML, no schema, no validator, no Mars blue-sunset inversion, no moon_psr/mercury/europa/pluto cards, no `terminator_soft`/`ambient_night`/`light_cct_k` fields |
| Semantic tokens | `ui/theme.py`/`render/vessel_art.py`: ACCENT `#8CEBFF`, GOOD `#78FFAA`, WARN `#FFC85A`, DANGER `#FF6E6E`, GOLD `#FFD782` (10 names, wrong hexes) | The ten 12 §5.7 tokens (§1.3): `#57C7E3` cyan … `#D9B354` gold; warning-orange ≠ emergency-red; radiation/cryo/thermal/inert tokens | Token set mismatch; single DANGER conflates Class 1/2; four tokens missing; no colorblind swap sets (VD-8/28) |
| Plumes | `vessel_art.plume()`: one orange/white triangle ramp for **all** propellants (per-family `_BELL_COLORS` exist but plume ignores family); `ui/effects.py` `emit_burn` default (255,200,90) | §2.1 per-family colors, k_f length law, Prandtl–Pack diamonds (§4.2b exit-plane table), vacuum ×0.25/25°/×0.15 behavior, NTR no-plume + skirt glow, EP beams, D29 parametric mesh | **Total** — plume colors generic, no diamonds, no vacuum honesty, no NTR/EP/RCS distinctions |
| Bloom | `render/postfx.py Bloom`: full-screen smoothscale bloom of the composited **world** (threshold 110 ≈ 0.43 luma); correctly applied before HUD (`main.py:3338`) | Bloom samples **layer 5 only** (FX + sun disc), threshold luma > 0.75 (VD-5); orbit lines/world vector must never bloom | Blooms the entire world vector layer — semantic colors and orbit chrome currently glow |
| Film grain / vignette | `main.py:805-821`: 4-frame grain blitted **over the entire frame including HUD** in `apply_fade()`; permanent decorative `vignette()` | VD-P1: HUD never post-processed; grain exists **only** in photo-mode filter recipes (2% Blueprint paper grain, 10% Archival halftone); only vignette in canon is the Class-1 alert vignette | Grain over HUD violates VD-P1; permanent vignette is non-canon |
| Starfield | `ui/effects.py Starfield`: 2 parallax layers (0.35/0.7); `postfx.py Nebula`: procedural indigo/teal/rust clouds + 0.05 parallax | YBC 9,110-star catalog, magnitude→PSF, Hipparcos tints; **stars never parallax**; zodiacal light is the only parallax layer; no nebula clouds in canon; magnitude floor deepens with zoom (VD-19) | Star parallax is a physics lie per §2; nebula clouds are invented art; no catalog |
| Lighting | `body_art.py`: Lambert disc shading, 16-sector sun, limb darkening, lit rim; `base_art.sky_strip` day/night lerp; `main.py` terminator phase | §1.6: `terminator_soft` band, limb-glow annulus `min(8H, 0.1R)`, 09-event eclipse ramps (120 s), SITE shadow billboards `min(cot e, 8)`, PSR floodlights (cap 32), VD-9 auto-exposure + True-Lux | Partial — disc shading good; no eclipse events, no shadows, no floodlights, no exposure model |
| Particles | `effects.Particles` cap 1,024, flame/smoke only; floor-billow on every body | 4,000 SW / 20,000 GPU; VD-10 priority culling; reentry plasma, vent/breach jets, ballistic-vs-suspended dust regimes | Cap low; no priority; billowing dust on airless bodies violates the ballistic rule; plasma/vent emitters absent |
| GPU path | None — no moderngl anywhere, no `render/gpu/` | §3 entire: GL 3.3 compositing, LUT grading, GPU bloom, 20k particles, degradation ladder, VD-1 goldens, PERF-V1..V4 | **Total** (acceptable: SOFTWARE is canonical; GPU is enhancement — but VD-2 guard scaffolding + budget tables should be built into the renderer's structure now) |
| Photo mode / Chronicle | None | S-19 screen, §2.6 filter recipes, VD-26 software-rasterizer export, True-Lux, snapshot card-id pinning | **Total** |
| Camera feedback | `render/camera.py`: transform choke point only | VD-23 accel offset + contact kick; VD-29 disable switches | Absent |
| Zoom continuity | 13's layers exist; no crossfade band logic found | VD-18 56→72 px icon↔sprite dissolve, VD-19 scale ruler during zoom, VD-20 handoff dressing, VD-21 SYSTEM never graded | Mostly absent (no ruler, no crossfade band) |
| Warp truth | `plume(phase01)` caller-driven (good, VD-P2-compliant flicker) | VD-16 table (steady plume 10–1,000×, arc segments >1,000×), VD-17 eclipse clamp | Absent above 10× |
| Alerts/strobes | ad-hoc flashes (`apply_flash`), base status lights | VD-24 class grammar (sinusoidal vignette, ≤ 8%), VD-14 strobe caps, VD-22 Reduced Flash setting, flash audit | Absent — no flash-rate governance |
| Accessibility | `draw_text` 1 px drop shadow | VD-27 70% backplate + CR floors, VD-7 validator, VD-28 token swaps, VD-29 motion settings | Absent |
| Animation timing | none of the §2.4 defaults | solar wing 120 s, radiator 90 s, gear 6 s, gimbal at real slew, VD-15 crew ticks | Absent (blocked partly on 06/09 state plumbing) |

**Salvageable from v2.1:** the layer ordering discipline (bloom before HUD), deterministic
seeded-procedural style, module-level caching, headless-safety, camera choke point, fBM toolkit,
SoA particle pool, and the Bahnschrift/mono type split are all spec-compatible foundations.
The work is mostly *re-pointing* them at canon data (cards, tokens, plume families) and adding
the missing systems (validator, photo mode, lighting events, GPU scaffold).

---

## 5. Open questions carried (doc 14 §9, minus resolved)

Q1 GL floor — **RESOLVED G35a** (3.3 core). Q6 plume mesh — **RESOLVED D29** (parametric mesh +
sprite fallback). Still open: Q2 star catalog depth (YBC ships; Hipparcos V 7.5 vs procedural
extension); Q3 interior brownout flicker (dim smoothly, never oscillate — needs playtest vs
VD-22 audit); Q4 HDR output (post-1.0; keep float intermediates in grade pipeline); Q5
SYSTEM-layer grading purity (needs mockups); Q7 snapshot full-card inlining (~1 KB/snapshot —
recommend yes, decide with 13 save-schema review); Q8 cross-machine archival exactness (only
with 13 §9-Q9 transcendental-free rasterizer; per D30, post-v1 at most).
