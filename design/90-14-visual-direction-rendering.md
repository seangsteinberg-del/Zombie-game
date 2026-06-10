# 90-14 — Visual Direction & Rendering

**Owner:** Visual domain. **Status:** design-complete draft for implementation.
**Scope:** the art-direction canon (pillars, per-world visual identity, FX vocabulary, animation language, 2D lighting), the photo-mode/Chronicle aesthetic recipes, accessibility limits for everything that glows or flashes, and the **pygame-ce + moderngl hybrid render pipeline** — the GPU compositing path, its mandatory pure-SDL2 software fallback, and the proposed GPU-path budget.
**Canonical rule:** this file owns *what the game looks like* and *how the GPU path is built*. `13-architecture.md` §3.13 remains the binding spec for the software render path and ratifies the budget amendments proposed in §3.2/§4.4 here. `12-gameplay-economy-ui.md` §5.7 remains the binding source of semantic UI color tokens; this doc extends them, never overrides them.
Sibling docs: 01-orbital-mechanics.md, 02-propulsion.md, 03-solar-system.md, 04-resources-isru.md, 05-industry-logistics.md, 06-ships-stations.md, 07-bases-habitats.md, 08-life-support-crew.md, 09-power-thermal.md, 10-vehicles.md, 11-research-tech.md, 12-gameplay-economy-ui.md, 13-architecture.md.

---

## 1. Overview

Aphelion's visual promise is a contradiction that must be engineered, not hand-waved: **an instrument** — the vector clarity of a mission-control plot, every line a number you can trust — **laid over a place** — the butterscotch haze of a Martian afternoon, the knife-edge shadows of a lunar polar rim, an ion drive's faint blue breath against ten thousand catalog stars. The instrument layer is owned by 12 (semantics) and 13 (machinery). The *place* has had no owner. This document is that owner.

Four pillars (binding; every visual decision below traces to one):

1. **VD-P1 — Instrument first.** At gameplay zoom the screen is a readable engineering drawing. Nothing painterly may reduce the legibility of a trajectory, a gauge, or an alert. Concretely: the HUD/UI layer is composited *after* all post-processing and is never bloomed, blurred, graded, or color-shifted (§3.3). When beauty and legibility collide, beauty loses, every time.
2. **VD-P2 — The physics is the animator.** Nothing on screen moves, glows, flashes, or shakes unless a sim quantity moved it: plumes from 02 thrust state, radiator color from 09 temperature, camera offset from real acceleration, eclipse darkness from 09's events. There is no "juice" track separate from the simulation. A player who films the screen can reverse-engineer the physics — that *is* the aesthetic.
3. **VD-P3 — Painterly depth behind the glass.** Below the vector layer lives the immersion stack: real-catalog starfields, zodiacal light, atmosphere gradients, terminator shading, dust. It is allowed to be gorgeous because pillar 1 guarantees it never carries gameplay-critical meaning alone.
4. **VD-P4 — Archival memory.** The campaign's visual afterlife (Chronicle cards, photo mode, the endgame export) renders in a 1960s–70s mission-print idiom: blueprint cyanotypes, flat-color mission patches, warm archival paper. The game is played on a monitor and remembered as a document.

What this doc owns: the GPU compositing pipeline and its budget proposal (§3.2–§3.3, §4.4), per-world identity cards (§3.4, §4.1), the 2D lighting model (§3.5), the FX catalog (§3.6, §4.2), animation and warp-truth rules (§3.7), zoom-transition language (§3.8), camera/feedback doctrine (§3.9), accessibility budgets (§3.10), photo-filter recipes (§4.5).
What it does not own: semantic color tokens and alert classes (12 §5.7, §3.11 A-1), the software render path internals and the final ratified budget table (13 §3.13, §4.6), body physical data (03), engine data (02), thermal state (09).

---

## 2. Real-World Grounding

Per the realism doctrine, every aesthetic claim below has a named source; the palette is observed, not invented.

- **Mars sky.** Viking, Pathfinder (Tomasko et al. 1999, JGR), and MER sky-imaging (Lemmon et al. 2004, *Science*) establish the daytime **butterscotch** sky — ~1.5 µm suspended dust absorbs blue and scatters red — and the inverted **blue sunset**: forward-scattering through dust makes the sky *around the solar disc* blue at twilight (Curiosity Sol 956 sunset sequence, NASA/JPL-Caltech, April 2015). Our Mars card (§4.1) encodes exactly this inversion.
- **Titan.** Huygens DISR (Tomasko et al. 2005, *Nature*): deep orange haze, no visible solar disc, surface illumination ~0.1% of Earth daylight — "late twilight" light levels at noon. Haze optical depth means soft, near-shadowless lighting.
- **The Moon.** Apollo surface photography: black sky at noon, zero atmospheric scattering, terminator shadows of effectively infinite contrast; secondary fill comes only from regolith-reflected sunlight (albedo ≈ 0.12). LRO Diviner measured 25–40 K in polar PSRs — the harshest light/dark boundary in the playable system.
- **Engine plume optics.** Kerolox: sooty, brilliant orange (RP-1 carbon incandescence; Merlin/F-9 footage). Hydrolox: nearly transparent pale blue with a bright Mach disc (RS-25/SSME). Methalox: translucent blue-violet with crisp shock diamonds (Raptor static fires). Solids: blinding white-orange from incandescent Al2O3 (APCP is ~16–18% aluminum). Hypergolics: faint translucent pink (Shuttle OMS). Vacuum: plumes expand to wide angles and effectively vanish — Apollo 17 LM ascent footage shows *no visible plume*. Shock-cell spacing follows the Prandtl–Pack relation x_s ≈ 1.31·D_e·√(M_j² − 1) (Pack 1950), M_j = fully-expanded jet Mach number — about 4–5 exit diameters per cell for booster-class M_j ≈ 3.4–4.0. (The often-quoted 0.67·D·√(p_0/p_amb) form is a different relation — distance from nozzle to the *first* diamond, using stagnation pressure p_0 — and is not used here.)
- **Electric propulsion glow.** NSTAR/Dawn xenon ion beams photograph as soft blue (Xe II emission); Hall thrusters show a cyan annulus; krypton/argon shift toward violet-white. NTR exhaust (hot H2) is essentially invisible — the honest visual is the radiatively cooled nozzle skirt's incandescence, not a flame.
- **Reentry plasma.** Sutton–Graves heating (already canon in 01 §2) sets onset and intensity; the Stardust reentry observation campaign (12.9 km/s, ~1,200 W/cm²) recorded the color evolution. N2/O2 atmospheres emit warm pink-orange: the N2 **first positive** system (B³Πg→A³Σu⁺, red-orange) plus the N2⁺ **first negative** system (blue-violet). CO2 atmospheres (Mars, Venus) emit paler blue-white from CN violet and C2 Swan bands — the CO Cameron bands lie in the ultraviolet (~190–270 nm) and contribute no visible color, so they do not justify any on-screen tint.
- **Incandescence honesty.** The **Draper point, 798 K**: below it, hot objects emit no visible glow. ISS radiators run ~275 K, Kilopower ~400 K — *they do not glow*, and Aphelion will not pretend they do (§3.7). Only 800 K-class NEP radiators (09 §3) earn a faint dull red.
- **Starfield.** The Yale Bright Star Catalog (9,110 stars to V ≈ 6.5) is small enough to ship verbatim; Hipparcos magnitudes/colors for tinting. Stars are at parsec distances: a 1 pc star shifts ~0.04% of the field across an 80 AU pan, i.e. **stars do not parallax**, and rendering them fixed under camera pan is both the cheap and the honest choice. The depth cue that *may* parallax is zodiacal light — interplanetary dust physically located at AU distances (observed brightness models: Leinert et al. 1998).
- **Illuminance scale.** Solar illuminance falls as 1/d²: ~133 klx at Earth, ~57 klx at Mars, ~5 klx at Jupiter, ~85 lx at Pluto — NASA's "Pluto Time" outreach (noon on Pluto ≈ Earth civil twilight) anchors the outer-system mood (§3.5).
- **Print idiom.** Cyanotype blueprint chemistry (Herschel 1842) for the Blueprint filter; the NASA Graphics Standards Manual (Danne & Blackburn, 1976) and Apollo-era press kits for Archival-Print; embroidered crew patches (Gemini–ISS) for Mission-Patch.
- **GPU pipeline precedent.** moderngl (OpenGL 3.3 core via Python) compositing pygame-authored surfaces is an established community pattern; the engineering numbers (8.29 MB per 1080p RGBA layer; ~0.3–1.0 ms upload on shared-memory iGPUs; separable Gaussian blur cost ∝ pixels × taps) are arithmetic, not vendor claims. Baseline GPU: Intel UHD 620-class (≈ 4.7 Gpix/s fill), the weakest hardware in the 60 fps@1080p contract (§4.4).
- **Photosensitivity.** WCAG 2.1 §2.3.1 "Three Flashes or Below Threshold" and ISO 9241; we adopt the strict reading (§3.10).
- **Accessibility contrast.** WCAG 2.1 contrast ratio CR = (L1+0.05)/(L2+0.05) on sRGB relative luminance; thresholds 4.5:1 (text) and 3:1 (graphical objects).

---

## 3. Game Model

### 3.1 The two render paths and the prime contract

| Path | Stack | Status |
|---|---|---|
| **SOFTWARE** | pygame-ce/SDL2 software blitting, exactly as specified in 13 §3.13 | **Canonical.** Always shipped, always working, CI baseline. Nothing in this document modifies its behavior or its 7.0 ms budget. |
| **GPU-COMPOSITE** | pygame-ce draws layers to CPU surfaces → surfaces stream to moderngl textures → GPU composites + post-processes | **Enhancement.** Auto-selected when available; every feature it adds degrades cleanly back to SOFTWARE. |

**VD-1 (the meaning-preservation contract).** The GPU path may only *add* (parallax depth, bloom, grading, more particles, smoother gradients); it may never change what a pixel *means*. Formally: with all post passes disabled, the GPU composite of the same layer surfaces must match the SOFTWARE composite within tolerance (mean |Δ| ≤ 1/255 per channel; ≤ 0.5% of pixels may exceed 16/255). Edge antialiasing is exempted **mechanically, not by judgment**: the vector rasterizer emits, per golden frame, the mask of pixels within 1 px of any stroke it drew (it knows every stroke's geometry); only mask pixels are exempt from the 16/255 outlier count, the mask ships as part of the golden-image artifact, and masked pixels still count toward the mean-|Δ| bound — so the exemption cannot swallow a compositing error that shifts whole lines. This is a CI golden-image test (§3.11).

**VD-2 (dependency amendment, proposed to 13 §3.1).** Runtime dependencies become **pygame-ce + numpy + (optional) moderngl ≥ 5.10**. moderngl is imported inside a guard in `render/gpu/`; ImportError, GL < 3.3 core, or a blacklisted/llvmpipe renderer string ⇒ SOFTWARE path, logged once, surfaced in Settings. The `sim/` package still imports numpy only — the CI import-graph test gains `sim/ imports no render.*` unchanged. 13 ratifies this amendment; until ratified, GPU path is a non-default experimental flag. The shader target is settled: **GL 3.3 core, desktop-only v1 (DECISIONS G35a — §9 Q1 resolved)**.

**VD-3 (CPU surfaces stay authoritative).** Every dynamic layer continues to exist as a pygame surface on the CPU. Consequences: (a) fallback mid-session is instant and lossless (GL context loss → next frame renders SOFTWARE); (b) screenshots, Chronicle vector snapshots, and photo-mode exports are path-independent (§3.9, VD-26); (c) the GPU is a *compositor*, never the system of record.

### 3.2 GPU-COMPOSITE pipeline

Layer stack, back to front (D = drawn on CPU and streamed; G = generated on GPU):

| # | Layer | Source | Updates | Post applied |
|---|---|---|---|---|
| 1 | Starfield (YBC stars + procedural V > 6.5 fainter extension, magnitude-to-PSF) | G | on zoom-band / pointing change | grade |
| 2 | Zodiacal light / milky-way band | G | per frame (cheap quad) | grade |
| 3 | Atmosphere & sky gradient (world card §3.4) | G | per frame | grade |
| 4 | World vector layer (orbits, bodies, terrain, sprites) | D, 8.29 MB | per frame | grade |
| 5 | FX particles (instanced point sprites, additive) **+ sun disc (GPU billboard, G)** — the disc is assigned here, *not* to layer 4, precisely so bloom never samples the world vector layer; both paths draw it additively above layer 4, so stacking matches under VD-1 | D (instance buffer ≤ 320 KB) + G | per frame | bloom + grade |
| 6 | Lighting multiply (terminator/eclipse/night, §3.5) | G | per frame | — |
| 7 | HUD/UI (per-widget textures, dirty-upload) | D, dirty regions only | on change | **none — VD-P1** |

Post stack: **bloom** (threshold luma > 0.75, half-res 960×540, 2-pass separable Gaussian σ = 6 px, additive re-composite, layer 5 only — which by the table above contains both FX particles and the sun-disc billboard) → **color grade** (32³ 3D LUT from the active world card + photo filter; identity LUT when grading off) → final blit + HUD.

**VD-4 (upload budget).** Streamed bytes per frame ≤ 12 MB at 1080p (world 8.29 + FX 0.32 + HUD dirty, typically < 1). At 25 GB/s shared-memory bandwidth ≈ 0.5 ms; budgeted 0.6 ms (§4.4). At 4K the world layer still renders at 1920×1080 and is GPU-upscaled ×2 integer (vector line art upscales acceptably; VD-P1 chrome does not) while **HUD widgets render and upload at native resolution, dirty-only** — steady-state flight dirties only numeric readouts (< 1 MB/frame). A full-HUD 4K redraw (~33 MB) is a 1-frame spike, legal during screen transitions only.

**VD-5 (bloom legibility rule).** Semantic alert colors (12 §5.7) never bloom: the bloom threshold pass samples layer 5 only (FX particles + the sun-disc billboard, which lives on layer 5 by construction — §3.2 table), never the world vector or HUD layers. An emergency is red because 12 says so, not because it glows.

### 3.3 Where the painterly budget lives

SOFTWARE path cannot afford per-pixel grading at 60 fps and is not asked to. **VD-6 (grade by token, not by pass):** world mood in SOFTWARE comes from the palette tokens in the world card itself (the TOML ships *pre-graded* colors); the GPU LUT only adds the continuous refinements (sky gradients banding-free, bloom, twilight ramps). Live LUT grading is GPU-only; SOFTWARE applies LUT filters solely in photo mode, where the game is paused and a 50 ms numpy per-pixel pass is irrelevant.

### 3.4 Per-world visual identity cards

One card per landable/orbitable body environment, shipped as data per 13 §3.4 (TOML, pack-patchable, validated at load). Schema (field names binding):

```toml
[world.mars]
body = "core:mars"                 # 03 body id (referential check)
space_or_sky = "sky"               # "space" = vacuum bodies
sky_zenith_day   = "#C28E5C"       # butterscotch (Pathfinder/MER)
sky_horizon_day  = "#E3B584"
sky_twilight     = "#8FA8C8"       # blue forward-scatter halo, sun-centered
sky_night        = "#0A0E14"       # converges to 12 §5.7 background
light_cct_k      = 4800            # display white-balance cast of sunlight
sun_disc_deg     = 0.35            # true angular size at body's a (01/03)
ambient_night    = 0.06            # lighting floor L_amb, §3.5
terminator_soft  = 0.30            # 0 = knife edge (airless), 1 = full haze
dust             = "suspended"     # none | ballistic | suspended
weather          = ["dust_storm"]  # 03-owned events only; must map to the 13 §4.4 v1
                                   # catalog (DUST_STORM_IN/OUT). Dust devils are NOT an
                                   # event — they render as a statistical visual within the
                                   # suspended-dust regime (§3.6, MER anchor), no 03/13 hook.
grade_lut        = "core:lut/mars_day"            # GPU only, VD-6
```

**VD-7 (load-time visual validation, registered into 13 §3.4 step list).** For every card: all **ten** 12 §5.7 semantic color tokens — player cyan `#57C7E3`, inert grey-white `#9AA7B0`, nominal green `#44CC77`, caution amber `#E8C547`, warning orange `#E8893B`, emergency red `#E25555`, radiation magenta `#C678DD`, cryo/water blue `#5398D9`, thermal deep-orange `#D97E4A`, money/Prestige gold `#D9B354` — must hold CR ≥ 3.0 against *every* sky gradient stop (this enumerated list, not a count, is the validator's binding input; if 12 §5.7 adds a token, VD-7 inherits it); HUD text token CR ≥ 4.5 against the HUD backplate (which is world-independent, so this is checked once); `sun_disc_deg` must match 2·atan(R_sun/d) from 03 data within 10%; `body` must exist. Violations fail content load — a modded "pretty" sky that hides a red alert is a build error, not a taste dispute.

**VD-8 (colorblind interaction).** Colorblind modes swap *semantic tokens only* (12 §5.7 rule 2 — shape already carries meaning). 12 §5.7 currently defines **one** swap set (deuteranopia-safe alternates for green/amber/red); protan and tritan sets do not yet exist in 12 and are proposed as a 12 §5.7 extension via §7. World cards are decorative and never swapped; VD-7 re-validates contrast against the deuteranopia set today and against each further set as 12 ratifies it. Because the swap is token-level, it costs zero per-pixel work on either path and survives every rung of the degradation ladder (§3.11).

### 3.5 2D lighting model (billboards only — no 3D, no normal maps)

All lighting is a small set of multiplies and gradients driven by sim state:

- **Sun direction.** LOCAL layer: `sun_dir = normalize(r_sun − r_body)` from the 01/03 ephemeris, per frame. SITE layer: solar elevation comes from 03's existing S-6 insolation machinery, not from latitude (which does not exist in 03's 2D model): S-6a's sun-cosine `c_sun(t) = max(0, cos(φ_center + 2πt/T_rot − θ_sun(t)))`, with `φ_center` read from the sector's 03 **S-7a** record, gives `e(t) = asin(c_sun(t))`. Latitude-flavored regions (poles, PSRs) are reserved sectors carrying S-6b insolation-flag overrides, and those flags — not a latitude field — drive their lighting (Shadows bullet below). The 09 daylight flag `L` (with its 120 s penumbra ramp) is the binding day/night truth — lighting *consumes* 09, never recomputes it.
- **Sprite/terrain illumination.** `L_v = clamp(L_amb + (1 − L_amb) · max(0, cos θ_sun) · L_ecl, 0, 1)` where `L_amb` = world card `ambient_night`, `θ_sun` = angle between surface-facing proxy and sun_dir, and `L_ecl` ∈ [0,1] is 09's flag including the 120 s penumbra ramp on ECLIPSE_IN/OUT events (13 §4.4 event catalog). Airless `L_amb` ≤ 0.08 (regolith backscatter only); thick-atmosphere bodies higher (Titan 0.35 — haze never goes fully dark by day).
- **Terminator on body discs (LOCAL).** Lit fraction from sun_dir; gradient band width = `terminator_soft × 0.25 × R_px`, minimum 1 px (airless = visually hard edge). Atmosphere-bearing bodies additionally draw a limb-glow annulus of thickness `min(8·H, 0.1·R)` (H = scale height from 03) tinted `sky_horizon_day` — Earth's 8.5 km H on a 6,371 km body reads as the familiar thin blue line.
- **Shadows (SITE).** One shadow billboard per structure/vehicle: a sheared, darkened silhouette along −sun_dir with length factor `min(cot e, 8)`, computable directly from S-6a's output as `cot e = √(1 − c_sun²)/c_sun` (the cap at 8 also absorbs the c_sun → 0 divergence at grazing sun). PSR sectors key on their 03 S-6b override (`terrain_class = PSR`, I = 0 always) — not on an elevation test — ⇒ permanent `L_amb`-only lighting; the player's floodlights (07 build items) are the *only* local light sources, drawn as additive radial gradients with 1/r² falloff over their rated radius.
- **Eclipse/night events.** ECLIPSE_IN/OUT and TERMINATOR events (13 §4.4) drive a whole-layer luminance ramp over the 120 s penumbra (instant at high warp per VD-16). LEO eclipse fraction is honest by construction: 09 P-10's `f_ecl = asin(R/r)/π` drives the events that drive us.
- **Hull specular hint.** A 1–3 px rim highlight on the vessel sprite edge nearest the sun, intensity ∝ max(0, cos θ). GPU: a trivial rim shader on the sprite pass. SOFTWARE: sun direction quantized to 8 sectors; rim variants pre-baked into the whole-vessel surface cache (13 §3.13), so cache size ×8 within the existing zoom-band LRU — bounded, no per-frame cost.
- **Exposure honesty.** Scene illuminance scales as (1 AU/d)²; raw rendering would make Saturn unplayable. **VD-9 (auto-exposure with a confession):** display exposure normalizes mean world-layer luma to 0.45 (the eye adapts; cameras meter), but mood is carried by CCT cast, contrast, and `ambient_night` — Pluto noon *feels* like twilight without being black. Photo mode offers a **True-Lux toggle** that disables normalization and shows the honest 85 lx gloom, with the measured illuminance stamped on the export.

### 3.6 FX vocabulary — physics in, photons out

Every emitter is keyed by sim state from the owning sibling; no FX exists without a driver. Particle simulation stays numpy SoA per 13 §3.13. Caps: **SOFTWARE 4,000 live particles (13's binding cap, restated, unchanged); GPU-COMPOSITE 20,000** (instanced point sprites; proposed here, 13 ratifies). Per-emitter sub-caps in §4.2.

- **Main-engine plumes (driver: 02 thrust state, throttle, propellant family, p_amb from 01/03 atmosphere).**
  Visible plume length `L_p ≈ k_f · √(F/kN)` m, family constant k_f and color in §4.2. Shock diamonds render only when burning in atmosphere with mismatch ratio `p_e/p_amb ∉ [0.8, 1.25]`, where `p_e` is the per-engine **visual-domain exit-pressure default pinned in §4.2b** (02 publishes no exit-plane data — see §7); cell spacing follows Prandtl–Pack, `x_s = 1.31 · D_e · √(M_j² − 1)` (≈ 4–5·D_e for booster-class M_j ≈ 3.4–4.0), with M_j and D_e per §4.2b, brightness ∝ family soot/Al loading. In vacuum: core length ×0.25, half-angle widens to ~25°, opacity ×0.15 — a Drayhorse-V burn at Mars-transfer is a faint violet whisper, exactly as the LM ascent taught us. Throttle scales L_p ∝ √(x·F); ignition transient = 4-frame overbright pop (within VD-22 flash rules).
- **NTR (02 §3.10).** No visible exhaust (hot H2 is transparent). Render: incandescent nozzle skirt ramped by burn time toward dull orange (Draper-consistent), plus atmospheric heat-shimmer refraction billboard when p_amb > 1 kPa. LANTR mode (O/F injection) gains a real pale flame.
- **Electric (02 §4.4).** A thin additive beam, length 4–10 m, opacity ∝ P_in/P_max: xenon soft blue, argon violet-white, per §4.2. Visible at SITE/INTERIOR-adjacent zooms; at LOCAL it collapses to a 1 px tick — an ion burn is *information* (the thrust vector chevron), not spectacle, per VD-P1.
- **RCS (02 §3.15).** 40-particle white puffs, 0.3 s life, aligned to the firing nozzle's actual thrust vector from the control solution. Puffs are the player's attitude-control debugger: asymmetric RCS firing patterns must be visibly asymmetric.
- **Surface dust (driver: 10 vehicles, 02 plumes; regime from world card `dust`).**
  `ballistic` (vacuum): particles follow real parabolas under local g, **no billowing, no suspension** — LRV rooster-tail arcs (Apollo 16 anchor); landing plumes throw low-angle (< 3°) high-speed ejecta sheets to the 10 §3.6.3 200 m sandblast radius, making that damage rule *visible*. `suspended` (atmosphere): billowing clouds with settling time ∝ 1/ρ_atm; Mars dust storms (03 events, 13 §4.4 DUST_STORM_IN/OUT) drive a whole-scene τ-based contrast/color wash on the lighting layer, not particles. Dust devils are a purely statistical visual within this regime (deterministic-seeded transient columns, MER anchor §4.2) — they are *not* a 03 event and post nothing to the 13 §4.4 catalog; if they ever gain gameplay effects, a DUST_DEVIL event must first be ratified by 03/13.
- **Reentry plasma (driver: 01 §3 Sutton–Graves q̇).** Onset at q̇_stag ≥ 5 W/cm² (faint glow), full sheath ≥ 50 W/cm² (enveloping bow + trail, particle rate ∝ q̇·A_ref). Color by atmosphere: N2/O2 warm pink-orange; CO2 pale blue-white (§2 anchors). The sheath visually swallows the craft sprite exactly during 01's comm-blackout window — the player *sees* why the radio died.
- **Venting and breach (drivers: 07 habitat breach, 08 rapid-depress, 02 §3.12 boiloff, 13 event types).** Collimated white jets of ice crystals (gas flashes to fog in vacuum — Apollo 13 anchor), length ∝ √(ṁ/kg·s⁻¹) × 10 m, aligned to the breach normal, imparting the (tiny, honest) reaction torque 06 computes. Boiloff venting is the same jet at low ṁ on a relief-valve schedule — a depot quietly bleeding Hydrogen *looks* like money leaking.
- **VD-10 (FX starvation priority).** When a cap binds, particles are culled in reverse priority: cosmetic dust < plumes < RCS < reentry < **venting/breach (never starved)** — anything that is also an alarm gets photons first.

### 3.7 Animation standards — what moves, and when it may not

- **VD-11 (state animation, not canned animation).** Deployables (solar wings, radiators, antennas, gear) tween between sprite states over the *sim's* deployment duration. 06 currently publishes **no** deploy durations (its catalogs carry deployed areas/masses only; 07 has only a structure-deploy terrain modifier), so this doc pins per-class default durations in §4.6, flagged as proposed 06 (and 09, for radiators) amendments per §7 — the sim consumes those same defaults, so sprite and state share one clock either way. If warp jumps the state, the sprite jumps — no animation debt is ever paid back in player time.
- **VD-12 (gimbal).** Engine nozzle sprites rotate to the actual commanded gimbal angle (02 §3.6 limits), slewed at the actuator's real rate. The player can *see* a control loop hunting.
- **VD-13 (thermal color).** Diegetic glow obeys the Draper point: surfaces render incandescent color only at T ≥ 798 K (NEP radiators: faint dull red at 800 K; reentry TPS; nozzle skirts). All other "heat vision" is the explicit **thermal overlay** (engineering view toggle): false-color 250 K → deep blue, 400 K → green, 800 K → orange, 1,000 K → white, driven by 09 node temperatures, drawn in the HUD layer with an INSTRUMENT watermark. We do not paint ISS-style 275 K radiators orange. Ever.
- **VD-14 (strobes and beacons).** Default beacon/strobe rate 1 Hz, hard ceiling 3 Hz (VD-22), duty ≤ 20%. Docking approach lights, pad perimeter, and the Master Alarm lamp all inherit this.
- **VD-15 (crew).** Per 13 §9-Q3 resolution adopted here: v1 interiors render crew as **status icons in cells** (idle/task/sleep/EVA/medical glyphs from 12's icon grammar) with at most a 1 Hz two-frame activity tick. Pathfinding agents are post-1.0 and would land in this doc's §9 first.
- **VD-16 (warp truth table).** What may animate at each warp band without lying about time:

| Warp | Plumes/RCS | Strobes | Dust/weather | Day/night & eclipse | Orbital motion |
|---|---|---|---|---|---|
| 1–10× | full FX | blink | full particles | 120 s penumbra ramps | honest |
| 10–1,000× | steady-state plume (no flicker) if thrusting | steady glow | statistical wash (no particles) | ramps compressed, min 2 frames | honest |
| > 1,000× | thrust arcs drawn as colored trajectory segments, no particles | steady glow | suppressed | **time-averaged lighting (VD-17)** | honest — watching orbits spin *is* the warp UI |

- **VD-17 (eclipse-flicker clamp — photosensitivity-critical).** At warp w on an orbit of period T, the apparent day/night frequency is `f_app = w/T`. If `f_app > 0.5 Hz`, per-event lighting is replaced by the time-averaged level `L̄ = (1 − f_ecl) · L_day + f_ecl · L_night` (f_ecl from 09 P-10). Example: LEO-300, T = 5,431 s ⇒ the clamp engages above w ≈ 2,716, comfortably before the 10,000× tier would strobe the screen at ~2 Hz.

### 3.8 Zoom-layer continuity (extends 13 §3.13/§4.8)

The four layers must feel like one camera. Rules layered onto 13's 150 ms frame-anchored crossfade:

- **VD-18 (icon-to-sprite band).** 13's 64 px threshold becomes a crossfade band: icon and sprite cross-dissolve as the rendered size moves 56 → 72 px with zoom (opacity sum = 1, never both fully opaque); the icon scales 0.9→1.1 across the band so the dissolve reads as approach, not a swap. Below 56 px: icon only (12 §5.7 shape grammar). Above 72 px: sprite only.
- **VD-19 (scale honesty cues).** A scale ruler (1 px tick bar, powers-of-10 in m/km/AU) is always visible during any zoom motion and for 1 s after; the starfield magnitude floor deepens with zoom-in (narrower field = longer exposure metaphor — more faint stars), giving continuous depth feedback without star parallax (which would be a lie, §2). Zodiacal light alone may parallax at SYSTEM layer, because that dust truly lives at AU distances.
- **VD-20 (handoff dressing).** SYSTEM↔LOCAL: the focus body's icon blossoms into its lit disc (terminator already correct on arrival). LOCAL↔SITE: per 13 §4.8 the landed craft stays screen-fixed; the sky gradient fades in over the same 150 ms from the world card. SITE↔INTERIOR: a 150 ms iris wipe centered on the entered hatch; exterior lighting state remains visible through window cells.
- **VD-21 (palette continuity).** SYSTEM layer is schematic and uses only the 12 §5.7 base palette (no world grading — the map is an instrument); world-card grading begins at LOCAL when a body's disc subtends > 32 px, ramped over one zoom-band step.

### 3.9 Camera & feedback doctrine — and the archival pipeline

- **VD-22 is in §3.10; camera rules here. VD-23 (no arcade shake).** Camera offset comes only from physical acceleration: `offset_px = min(16, 24 · |a_specific|/g0)` opposite the acceleration vector, low-pass filtered at 2 Hz. Touchdown/docking contact: a single critically damped (ζ = 1, 400 ms) displacement of `min(20, 6 · Δv_contact/(m/s))` px. **No random/Perlin camera noise exists in the codebase.** Engine roughness is conveyed honestly — on the instrument, never the world — but 02 currently publishes **no** thrust-oscillation/roughness output, and VD-P2 forbids FX without a sim driver. So: §7 proposes a 02 amendment adding a per-family thrust-roughness figure σ_F (RMS % of commanded thrust); once 02 ratifies it, the HUD accelerometer needle carries 1 px jitter scaled to σ_F. **Until then the needle is steady** — a steady needle is honest; an invented wobble is not.
- **VD-24 (alert grammar, shared with 12 A-1).** Class 1 EMERGENCY: 0.8 Hz sinusoidal red vignette (≤ 8% screen area, smooth — not a square-wave flash) + the 12-owned klaxon. Class 2 WARNING: steady orange HUD border, single 200 ms onset pulse. Class 3 CAUTION: amber badge on the owning gauge only. Class 4 ADVISORY: toast only. No alert class ever moves the camera or blurs the screen.
- **VD-25 (readout motion).** Numeric readouts refresh at ≤ 10 Hz (rendering still per-frame from the 13 glyph atlas; the *value* is sampled at 10 Hz) so digits are readable, with the final value always exact on settle.
- **VD-26 (archival pipeline is path-independent).** Photo-mode exports, Chronicle vector snapshots (12 C-2), and the endgame poster always re-render through the SOFTWARE vector rasterizer at export resolution (up to 4× per 12 C-5), applying filter LUTs in that offline pass. One campaign archived twice **on the same platform and build** produces identical pixels — exactly the scope of the determinism doctrine (13 §3.10 is per-platform bit-exact and explicitly disclaims cross-platform last-ULP libm variance; 13 §9-Q9) extended to memory itself. Cross-*machine* pixel exactness is not promised: it would additionally require a transcendental-free export rasterizer, a pinned freetype version, and integer/fixed-point LUT math — tracked as §9 Q8 and proposable to 13, not assumed here. Chronicle snapshots store the active world-card id + filter id at capture time so later re-renders reproduce the moment's look even if mods later patch the card.

### 3.10 Accessibility budget (binding)

- **VD-22 (photosensitivity).** Adopting WCAG 2.1 §2.3.1 strictly: no element flashes > 3 Hz; total simultaneously flashing area < 10% of the screen; no red square-wave flashes (Class-1 vignette is sinusoidal, VD-24); eclipse/day-night flicker clamped by VD-17; ignition pops ≤ 4 frames and ≤ 10% screen. A **Reduced Flash** setting converts every strobe to steady +20% brightness and disables the Class-1 vignette pulse (border becomes steady). CI scene PERF-V3 (§3.11) includes an automated flash-frequency audit (frame-differencing over 600 frames).
- **VD-27 (contrast floors).** HUD text ≥ 4.5:1 vs its backplate; all vector chrome (orbits, icons, scale ruler) ≥ 3:1 vs any background it can appear over — enforced at load by VD-7, and at runtime by the auto-backplate rule: any label drawn over the painterly stack gets a 70%-opacity `#0A0E14` backplate.
- **VD-28 (colorblind cost ceiling).** Colorblind palettes (12 §5.7's deuteranopia set today; protan/tritan sets proposed to 12 via §7, per VD-8) are pure data swaps (VD-8): they must remain available and identical in effect on every degradation rung including pure SOFTWARE, and may never be implemented inside a grading LUT (which degradation can drop).
- **VD-29 (motion sensitivity).** Setting to disable camera acceleration offset (VD-23) and zoom crossfades (cut instead); parallax (zodiacal) off switch. None of these change sim behavior.

### 3.11 Performance contract & degradation ladder

Targets (proposed; 13 §3.14/§4.6 ratifies): **GPU path: 60 fps at 1080p on Intel UHD 620-class iGPUs with the full post stack; 60 fps at 4K on ≥ GTX 1650/RX 6400-class with identical settings.** CPU render work on the GPU path must fit the **same 7.0 ms cap** as SOFTWARE (no cap arithmetic changes for 13 — see table §4.4); GPU work ≤ 6.0 ms on the baseline iGPU, overlapped with the CPU sim of the next frame.

**Degradation ladder (auto-steps when GPU frame > 12 ms sustained over 120 frames; each step logs to the perf HUD per 13's "nothing silently stutters"):**

| Rung | Action | Lost |
|---|---|---|
| L0 | full GPU path | — |
| L1 | bloom off | glow |
| L2 | particle cap 20,000 → 8,000 | FX density |
| L3 | grading LUT → identity (VD-6 tokens keep world mood; VD-28 colorblind unaffected) | continuous grade |
| L4 | **SOFTWARE path** (= 13 §3.13 exactly) | parallax/zodiacal, GPU particles |

New CI perf scenes registered into 13 §3.14/§3.16's suite: **PERF-V1** Max-Q nine-engine kerolox ascent, 1080p, full FX; **PERF-V2** Mars dust-storm EDL with plasma sheath; **PERF-V3** lunar-night base, 60 conics, beacons (doubles as the VD-22 flash audit); **PERF-V4** 4K Planner with HUD-heavy layout (VD-4 upload spike check). Headless CI lacks GPUs: GPU scenes run on llvmpipe asserting **correctness only** (VD-1 golden images, SSIM ≥ 0.995); timing asserts run nightly on a reference UHD 620 machine. SOFTWARE-path timings keep 13's ×3-slack CI rule unchanged.

---

## 4. Content Catalog

### 4.1 World identity cards (initial set; hexes are the shipped defaults, data-patchable)

| Card | Sky/space day | Twilight/limb | light_cct_k | ambient_night | dust | Signature treatment (anchor) |
|---|---|---|---|---|---|---|
| earth | zenith `#3D6FB8`, horizon `#A8C8E8` | warm `#E8A05C` | 5900 | 0.18 | none | Rayleigh blue, thin limb line; city-glow specks on night side (DMSP imagery) |
| earth_orbit | space `#0A0E14` | airglow arc `#5C8A6E` | 5800 | 0.10 | none | ISS night-pass airglow band at the limb |
| moon_day | black `#05070A` | none | 5800 | 0.06 | ballistic | knife-edge terminator, terminator_soft = 0 (Apollo) |
| moon_psr | black `#05070A` | none | — (no direct sun) | 0.02 | ballistic | floodlight-only lighting; rim sunlight as a distant white wall (LRO Diviner) |
| mercury | black `#05070A` | none | 5800 | 0.05 | ballistic | ×6.7 sun disc brightness, darker regolith than lunar maria (MESSENGER) |
| venus_aerostat | diffuse `#E8DCAE` | `#C8A86E` | 5200 | 0.30 | suspended | shadowless yellow-white cloud glow at 50 km (HAVOC) |
| mars | zenith `#C28E5C`, horizon `#E3B584` | **blue halo `#8FA8C8`** | 4800 | 0.06 | suspended | butterscotch day / blue sunset inversion (Pathfinder, Curiosity Sol 956) |
| phobos_deimos | black `#05070A` | none | 5700 | 0.04 | ballistic | Mars fills the sky from the sub-Mars sector (03) |
| asteroid_belt | black `#05070A` | none | 5800 | 0.03 | ballistic | dock-mode: slow body rotation is the only motion |
| ceres | black `#05070A` | none | 5800 | 0.03 | ballistic | bright crater faculae accents (Dawn, Occator) |
| europa | black `#05070A` | none | 5800 | 0.05 | ballistic | Jupiter disc dominates; cold blue-grey ice palette (Galileo) |
| titan | haze `#C87A32` zenith→`#A85E28` horizon | none — no solar disc | 3800 | 0.35 | suspended | shadowless orange gloom, 0.1% illuminance via VD-9 (Huygens DISR) |
| saturn_titan_orbit | space `#0A0E14` | ring-light fill `#D8C8A8` | 5700 | 0.08 | none | rings as the light source on night sides |
| pluto_kbo | black `#05070A` | none | 5800 | 0.02 | ballistic | "Pluto Time" twilight under True-Lux; N2-ice blue-white accents (New Horizons) |
| deep_space | black `#05070A` | zodiacal wedge | 5800 | 0.0 | none | starfield + zodiacal only; the loneliest card |

### 4.2 Plume & FX catalog (drivers per §3.6; per-emitter caps SOFTWARE / GPU)

| FX | Driver (owner) | Color core→edge | k_f (m/√kN) | Cap S/G | Anchor |
|---|---|---|---|---|---|
| Kerolox SL plume (K-845) | 02 thrust, p_amb | `#FFD27A`→`#E8893B`, sooty | 2.2 | 600/3,000 per engine | Merlin/F9 footage |
| Methalox SL plume (M-2256) | 02 | `#9AB8FF`→`#6E7AE8`, crisp diamonds | 1.6 | 600/3,000 | Raptor static fire |
| Hydrolox plume (H-2280) | 02 | near-transparent `#C8D8FF`, bright Mach disc | 1.0 | 400/2,000 | RS-25 |
| Solid plume (SRM-2/49) | 02 | white `#FFF4E0`→`#FFB36E`, opaque, smoky | 3.0 | 800/4,000 | APCP Al2O3 incandescence |
| Hypergolic (OMS-27, LND-71) | 02 | faint pink `#E8A8A0`, translucent | 1.2 | 300/1,500 | Shuttle OMS |
| Vacuum any | 02 thrust; p_amb < 0.8·p_e (p_e from §4.2b) | family color, opacity ×0.15, 25° half-angle | ×0.25 | same | Apollo LM ascent (invisible) |
| NTR "plume" | 02 §3.10 | none; nozzle skirt incandescence VD-13 | — | 0 particles | NERVA exhaust transparency |
| Ion/Hall beam | 02 §4.4 P_in | Xe `#7AB8E8`; Ar/Kr `#A89AE8` | fixed 4–10 m | 100/400 | NSTAR/Dawn, SPT-100 |
| RCS puff | 02 §3.15 firing solution | white `#E6EDF3` | 0.3 s life | 40/puff | Shuttle PRCS footage |
| Ballistic dust | 10 wheels / 02 plume ejecta | world regolith tint | parabolas, local g | 1,200/6,000 | Apollo 16 LRV; Apollo 12→Surveyor 3 |
| Suspended dust | 10 / 03 weather | world dust tint | settling ∝ 1/ρ_atm | 1,200/6,000 | MER dust devils |
| Reentry plasma | 01 q̇ Sutton–Graves | N2/O2 `#FF9A7A`; CO2 `#A8C8E8` | rate ∝ q̇·A | 800/4,000 | Stardust observation campaign |
| Vent/breach jet | 07/08/02 events, ṁ | ice-fog white `#F0F4F8` | L = 10·√(ṁ) m | 200/800, **never starved (VD-10)** | Apollo 13; Shuttle water dumps |

#### 4.2b Exit-plane data for diamond rendering (visual-domain defaults)

02 publishes no nozzle exit pressure, exit diameter, or expansion ratio (its §3.3 model needs only F_vac/Isp_vac/Isp_SL), so the §3.6 diamond gate and Prandtl–Pack spacing take their inputs from this table. These numbers feed **photons only, never thrust** — they are proposed to 02 for ratification as catalog columns (§7); until ratified they are owned here and tagged visual-domain. Where an engine has both thrust ratings, D_e is *derived*, not invented: `A_e = (F_vac − F_SL)/101.325 kPa` (the exact slope of 02 §3.3's linear back-pressure model), `D_e = 2·√(A_e/π)` — which reproduces the published Merlin 1D (0.92 m), Raptor 2 (~1.3 m), and RS-25 (2.30 m) exit diameters, validating the derivation against its own anchors.

| Engine (02 §4.2) | p_e (kPa) | M_j (fully-expanded jet Mach) | D_e (m) | Source of D_e |
|---|---|---|---|---|
| K-845 "Mule" | 70 | 3.4 | 0.93 | derived: (914−845)/101.325 → A_e 0.68 m² |
| M-2256 "Drayhorse" | 80 | 4.0 | 1.32 | derived: (2394−2256)/101.325 → A_e 1.36 m² |
| H-2280 "Shire" | 13 | 3.8 | 2.29 | derived: (2279−1860)/101.325 → A_e 4.14 m² |
| MV-2530 "Drayhorse-V" | 3 `[est]` | 4.6 `[est]` | 2.4 `[est]` | pinned (vacuum-rated, no F_SL to derive from) |
| SRM-2 / SRM-49 | 60 | 3.0 | 0.5 / 1.5 `[est]` | pinned |
| OMS-27 / LND-71 | 10 | 3.2 | 0.6 `[est]` | pinned |

p_e and M_j are per-engine constants (visual defaults), not throttle-dependent — an accepted simplification consistent with 02's own fixed-exit-area model. EP, NTR, and RCS emitters never render diamonds and take no row.

### 4.3 GPU post-pass table (1080p, baseline UHD 620-class estimates)

| Pass | Resolution | Est. cost (ms) |
|---|---|---|
| Starfield + zodiacal | native | 0.4 |
| Sky gradient + limb | native quad | 0.1 |
| Layer composite (4 streamed/generated layers) | native | 0.5 |
| Particles (≤ 20,000 instanced) | native, additive | 0.5 |
| Lighting multiply | native | 0.2 |
| Bloom (threshold + 2× Gaussian σ=6 + add) | 960×540 | 0.8 |
| Grade (32³ LUT) + final | native | 0.4 |
| HUD composite (no post) | native | 0.2 |
| **GPU total** | | **3.1 ≤ 6.0 budget** |

### 4.4 Proposed GPU-path CPU render budget (13 §4.6 ratifies; SOFTWARE column unchanged and binding)

| CPU item @1080p | SOFTWARE (13 §4.6) | GPU-COMPOSITE (proposed) |
|---|---|---|
| Starfield + world vector layer | 3.5 | 2.9 (starfield → GPU; no software full-frame composites) |
| Sprites/sites | 2.0 (incl. particles) | 1.5 |
| FX numpy update + instance pack | — (in above) | 0.6 (20,000 SoA) |
| Text + HUD | 1.5 | 1.4 (dirty-widget uploads) |
| Texture uploads (≤ 12 MB, VD-4) | — | 0.6 |
| **Render total** | **7.0 (hard cap)** | **7.0 (same hard cap)** |

Entity/scale caps restated from 13 §4.6, with the single proposed change: particles ≤ 4,000 (SOFTWARE, unchanged) / **≤ 20,000 (GPU path, new)**. All other caps untouched.

### 4.5 Photo-mode filter recipes (12 C-5 names; recipes owned here; applied per VD-26)

| Filter | Recipe | Anchor |
|---|---|---|
| Blueprint | luma → duotone ramp `#13294B` (Prussian blue) → paper `#E8EDF2`; all lines white; fills dropped; 2% paper-grain noise; title block with craft name/date in the 12 caption grammar | cyanotype (Herschel 1842) |
| Mission-Patch | posterize 6 levels; semantic colors to flat saturated fills; 3 px outlines; circular crop with gold ring `#D9B354`; mission name arc text; procedural emblem seed per 12 C-4 | embroidered crew patches |
| Archival-Print | invert to warm paper `#F4EFE6` with dark ink lines `#2A2E33`; 10% halftone dot on fills; 0.3% chromatic offset; date/frame-number stamp in the margin | NASA press kits; 1976 Graphics Standards Manual |
| True-Lux (modifier) | disables VD-9 exposure normalization; stamps measured illuminance (lx) on the export | "Pluto Time" |

### 4.6 Animation timing table

| Element | Duration / rate | Driver |
|---|---|---|
| Solar wing deploy | sim deployment time; **default 120 s** (06 publishes no duration — proposed 06 amendment, §7; ISS SAW motorized deploy runs minutes) | 06 DEPLOY state; duration default owned here until 06 ratifies |
| Radiator deploy | sim deployment time; **default 90 s** (proposed 06/09 amendment, §7; ISS HRS anchor) | 06/09 DEPLOY state; duration default owned here until ratified |
| Landing gear | sim deployment time; **default 6 s** (proposed 06 amendment, §7) | 06 DEPLOY state; duration default owned here until 06 ratifies |
| Gimbal slew | actuator rate (02 §3.6) | 02 command |
| Beacon strobe | 1 Hz default, ≤ 3 Hz, duty ≤ 20% | VD-14/VD-22 |
| Crew activity tick | ≤ 1 Hz, 2 frames | 08 task state |
| Zoom crossfade | 150 ms (13 §3.13) | camera |
| Eclipse ramp | 120 s penumbra (09), VD-17 clamp under warp | 09 events |
| Class-1 vignette | 0.8 Hz sinusoid | 12 A-1 |
| Contact camera kick | 400 ms, ζ = 1 | VD-23 |

---

## 5. Player Interaction & UI

- **Settings → Graphics** (extends 13 §5 settings list): render path Auto/Software/GPU; bloom on/off; world grading on/off; particle density (GPU rungs); Reduced Flash (VD-22); motion-sensitivity switches (VD-29); colorblind token set (VD-28); exposure mode; integer UI scale (13). Every toggle states its honest cost ("Software path: parallax and bloom unavailable").
- **Perf HUD (Ctrl+F3) additions** to 13 §3.14's bars (rebound from F3 per DECISIONS A7 — F3 stays the Planner): GPU frame ms, upload MB/frame, active degradation rung with reason — the same no-silent-stutter doctrine.
- **Photo mode (S-19, 12 owns the screen):** this doc supplies the filter recipes (§4.5), line-weight boost ×1.5, and the VD-26 export pipeline; any photo pins to the Chronicle per 12 C-5.
- **Thermal overlay toggle** (VD-13) lives with the other engineering overlays on S-11's frame; watermarked INSTRUMENT.
- **Encyclopedia (S-17):** each world card gets a "Why does it look like this?" page citing its §2 anchor (Pathfinder sky, Huygens gloom) — readout honesty extended to aesthetics: the sky is a citation.
- **First-arrival vista:** on each body's first SOI_ARRIVAL Chronicle event, a 2 s exposure-adaptation ramp plays (sim unpaused, nothing moves the camera) and a toast offers photo mode. Cosmetic, skippable, never repeats.

---

## 6. Progression Hooks

- **Visual fidelity is never a progression reward.** No tech node, act, or purchase gates rendering features (accessibility doctrine: a colorblind Act-1 player gets the same legibility as an endgame one). What progression *delivers* is new light: each act's new bodies bring new world cards — Act 1's two skies (Earth, LEO) grow to fifteen by Act 5.
- **Act mood arc (within the fixed grammar):** Act 1 is blue-white and familiar; Act 2 monochrome severity (moon_day/moon_psr); Act 3 the warm Mars inversion; Act 4 sun-drenched Mercury vs the yellow Venus gloom; Act 5 dim, ring-lit, and finally the Pluto twilight — the palette itself tells the story of leaving home.
- **Chronicle/endgame:** every FIRST_* card uses the era's world card + Mission-Patch emblem (12 C-4); the "The Program, 2049–20XX" HTML export re-renders all snapshots through VD-26 — the trophy is printable.
- **Research hooks:** none required; [SPECULATIVE] T4 drives get their FX entries (e.g., NUK-FUS rejects its 6.7 MWt at **900 K** per 09 §4.3 — comfortably above the 798 K Draper point, so its radiators run hot enough to *honestly* glow per VD-13: the endgame literally lights up red. The 6 kg/kWe figure 09 pins is the whole fusion unit's specific mass, not a radiator property).

---

## 7. Cross-System Interfaces

- **13-architecture.md** — *consumes:* layer/zoom architecture (§3.13, §4.8), caches, event catalog (§4.4 ECLIPSE_IN/OUT, TERMINATOR, DUST_STORM_IN/OUT), widget framework (§3.17), content pipeline + validator (§3.4, gains VD-7 checks), CI suite (§3.16, gains PERF-V1..V4). *Provides for ratification:* VD-2 dependency amendment, §4.4 GPU-path CPU budget, 20,000 GPU particle cap, VD-1 equivalence test. SOFTWARE path and its 7.0 ms cap pass through unmodified.
- **12-gameplay-economy-ui.md** — *consumes:* §5.7 tokens and shape grammar (binding), A-1 alert classes, C-2/C-4/C-5 Chronicle/photo specs, S-19 screen ownership. *Provides:* VD-24 alert visual grammar, §4.5 filter recipes, VD-26 export pipeline, world-card hexes for Encyclopedia pages. *Provides for ratification:* protan and tritan token sets as a proposed 12 §5.7 extension (12 currently defines deuteranopia only — VD-8/VD-28).
- **02-propulsion.md** — *consumes:* thrust/throttle/gimbal state, propellant family, EP power fraction, NTR mode (02 publishes no exit-plane data — §4.2b covers that gap with visual-domain defaults). *Provides for ratification:* (a) the §4.2b exit-plane columns (p_e, M_j, D_e) as a proposed 02 catalog amendment; (b) a per-family thrust-roughness output σ_F (RMS % of commanded thrust) for VD-23's accelerometer jitter. Neither feeds back into 02's performance numbers; plume visuals remain pure consumers (02's numbers are never tuned for looks).
- **03-solar-system.md** — *consumes:* body data (R, H scale height, rotation T_rot, albedo), S-7a sector records (φ_center, terrain_class, dust_index), the S-6a/S-6b insolation machinery (sun-cosine, PSR/PEL flags — §3.5 derives solar elevation from these; 03 has no latitude field and none is requested), weather events (DUST_STORM only; dust devils are visual-only per §3.6). *Provides:* world-card `body` references validated against 03; sun_disc_deg cross-check (VD-7).
- **01-orbital-mechanics.md** — *consumes:* ephemeris sun vectors, Sutton–Graves q̇, blackout window, EDL profiles.
- **09-power-thermal.md** — *consumes:* ECLIPSE_IN/OUT + 120 s penumbra L flag (binding day/night truth), node temperatures for VD-13, f_ecl for VD-17.
- **10-vehicles.md / 07 / 08 / 06** — *consumes:* dust generation events and the 200 m plume-ejecta rule (10 §3.6.3) made visible; breach/depress events (07/08); DEPLOY state and contact Δv (06). *Provides for ratification:* per-class default deployment durations (§4.6 — solar wing 120 s, radiator 90 s, gear 6 s) proposed as a 06 amendment (09 co-signs the radiator value), since 06 currently publishes deployed areas/masses but no deploy times.
- **05/04/11** — incidental: industry stack emissions reuse the vent-jet vocabulary; no special interface.

---

## 8. Failure Modes & Edge Cases

1. **GL context loss / driver crash mid-session.** VD-3: CPU surfaces are authoritative; next frame renders SOFTWARE, a Class-4 advisory fires, GPU re-init is attempted once in the background. No frame is ever black.
2. **llvmpipe masquerading as a GPU** (VMs, remote desktops). GL_RENDERER string containing `llvmpipe`/`softpipe` ⇒ treat as no-GPU (software GL is slower than pygame blits for this workload). Blacklist is data (13 §3.4 pack), updatable without code.
3. **sRGB double-gamma.** Classic hybrid-pipeline bug: pygame surfaces are sRGB-encoded; the GPU path must sample them as UNORM (no automatic sRGB decode) and apply the LUT in encoded space, or whites clip and the VD-1 golden test fails — which is exactly why VD-1 is a CI test and not a code review hope.
4. **Bloom bleeding into the HUD.** Structurally impossible (HUD composites after post, VD-P1/VD-5); the failure mode to guard is a *mod* LUT crushing alert hues — VD-7 re-validates CR on every pack load, and grade LUTs are checked to keep ΔE between any two semantic tokens ≥ 50% of their ungraded ΔE.
5. **Eclipse strobing at warp.** VD-17 clamps; edge case is *elliptical* orbits where f_ecl varies per rev — the clamp keys on instantaneous f_app using the current rev's shadow-crossing interval from 09's scheduled events, so a 10,000× Molniya doesn't flicker either.
6. **Particle cap exhaustion during a disaster** (nine-engine ascent + breach + dust). VD-10 priority guarantees the breach jet renders; cosmetic dust dies first. CI scene PERF-V2 asserts the priority order under deliberate over-subscription.
7. **4K HUD upload spike.** A full-screen UI rebuild at 4K (~33 MB) blows VD-4 for one frame. The arithmetic: ~1.3 ms upload (33 MB at 25 GB/s) + a full-HUD CPU re-render at 4× the 1080p pixel count ≈ 4 × the 1.4 ms HUD budget ≈ 5.6 ms — together roughly doubling that frame's CPU render cost, i.e. **one over-budget frame**, no more. Legal only on mode/screen transitions, where a single missed frame is invisible; sustained violation (> 3 consecutive frames) drops HUD streaming to 1440p with integer-scale and logs to the perf HUD.
8. **Colorblind × grading interaction.** Token swap happens before any LUT (VD-28); degradation rung L3 drops the LUT entirely — accessibility is therefore *more* robust under load, never less.
9. **Photo export mismatch between render paths or between re-renders.** Prevented by construction within 13 §3.10's scope: VD-26 exports always run the software rasterizer with deterministic LUT math (numpy float64, 13 §3.10 discipline), so any two exports of one snapshot on the same platform and build are identical, GPU session or not. Cross-platform exports may differ at the last ULP (libm; 13 §9-Q9) — see §9 Q8 before promising more.
10. **World card modded to break mood vs. meaning.** A pack can make Mars green (decorative freedom) but cannot make it *illegible*: VD-7 contrast validation fails the load. The validator is the modding contract, same doctrine as 13 §3.4.
11. **Warp-tier plume lies.** At > 1,000× a "burning" craft must not show a real-time plume (it would imply seconds while days pass): VD-16 renders thrust as colored trajectory arc segments — the same visual language the Planner already uses for planned burns, so the lie is avoided with a vocabulary the player knows.
12. **PSR floodlight abuse.** Dozens of player floodlights in one PSR site each cost an additive gradient draw; cap 32 visible light billboards per site (beyond that, merged into one ambient lift) — a visual cap, no sim effect.

---

## 9. Open Questions

1. **GL floor: 3.3 core vs ES 3.0.** 3.3 core is assumed (desktop-only doctrine); choosing ES 3.0-compatible shaders would keep a future handheld port open at little shader-level cost — ES 3.0 *does* support texelFetch and sampler3D, so the 32³ LUT path and texel-fetch tricks are unaffected. The real deltas are geometry shaders (unused here), some texture-format/blit rules, and the fact that moderngl creates desktop-GL contexts — making this mostly a context/loader question, not a shader rewrite. Decide before shader authoring starts. **RESOLVED (DECISIONS G35a):** shaders target **GL 3.3 core** (desktop-only v1); the ES 3.0 handheld hedge is not pursued for v1 (VD-2 updated).
2. **Star catalog depth.** YBC (9,110 stars) ships; do we add Hipparcos to V 7.5 (~25k stars — counts roughly triple per magnitude from 9.1k at V 6.5; ~50k is V ≈ 8) for the deepened zoom floor (VD-19), or extend procedurally with a deterministic seed? Memory is trivial either way; the question is whether community astronomers will check us (they will).
3. **Interior brownout flicker.** Dimming interior cells with 09 grid brownouts is mood gold, but sub-Hz luminance oscillation across a large screen area sits close to VD-22's limits. Proposal: dim smoothly, never oscillate; needs a playtest against the photosensitivity audit before canonization.
4. **HDR output.** scRGB/HDR10 swapchains would let the sun disc and plumes carry real highlights on capable displays. Post-1.0; tracked here so the grade pipeline keeps float intermediates.
5. **SYSTEM-layer grading purity (VD-21).** Current rule: the system map is never graded. Counter-argument: a faint act-mood tint on the map would carry the §6 palette arc into the most-viewed screen. Taste call; needs side-by-side mockups.
6. **Per-engine plume sprites vs. analytic plume mesh on GPU.** v1 uses particle + billboard composition; a parametric plume mesh (length/diamond spacing analytic from §3.6) would be cheaper at high engine counts and *more* physically legible. Prototype during Phase 1; if adopted, §4.2 caps drop.
7. **Chronicle snapshot world-card pinning (VD-26)** stores card *id*; should it store the full resolved card (hexes inline) so exports survive mod removal? Costs ~1 KB per snapshot; recommend yes — decide with 13's save-schema review.
8. **Cross-platform archival exactness.** VD-26 promises identical pixels per platform+build only (matching 13 §3.10). Earning a true cross-machine guarantee requires a 13 amendment: transcendental-free export rasterizer (polynomial sin/cos/exp, ~2 ULP — 13 §9-Q9 sizes the sim-core version at ~2 weeks), pinned freetype version for text, integer/fixed-point LUT math. Worth it only if community archives become a shared artifact (challenge-run galleries); decide with 13's Q9.
