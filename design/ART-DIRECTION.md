# APHELION ART DIRECTION — "MISSION FILM"

**Binding for every visual in the game** (decided 2026-06-13 with the user after
the "pick an art style and keep to it" directive). Every scene, sprite, palette,
and UI element is checked against this document. When in doubt: *would this
frame pass as documentary footage from a space program that actually exists?*

The emotional target: **mesmerising authenticity.** The player should feel like
they are THERE — Apollo Hasselblad photographs, ISS cupola timelapses,
*For All Mankind* title cards, *Gravity* (2013). Not a toy, not a hologram,
not pixel-art retro.

---

## 1. The three layers

### 1.1 WORLD layer (space, planets, terrain, atmospheres) — photographic
- **Space is near-black.** The drama is CONTRAST: a brilliant subject against
  void. Sparse pinpoint stars (power-law brightness), a faint structured galaxy
  band, nebulae barely-there. Never a "Christmas tree" sky.
- **Planets are the jewel of any frame they appear in**: swirling white cloud
  systems (domain-warped, cyclone vortices), deep saturated surface hues, a
  RAZOR-THIN brilliant atmosphere limb (not a wide soft halo), golden sunset
  terminator, city lights and earthshine on the night side, sun glint on seas.
- **The sun is a camera artifact**: white diffraction star, anamorphic streak,
  lens ghosts. It is the light source of every exterior frame.
- **Terrain (tile worlds, surfaces)** reads as geological cross-section
  photography: material gradients, strata, ambient-occlusion shadows in
  cavities, sun-direction shading on ridges. Tiles are a SIMULATION grid, not
  a visual style — render them with smooth material shading, never chunky.

### 1.2 MACHINE layer (rockets, modules, vehicles, interiors) — precision engineering
- **Shape language**: clean engineered geometry — cylinders, trusses, gimbals,
  quilted MLI padding. Greebles are structured (bolt rows, weld seams, panel
  lines), never random noise.
- **Materials by gradient + shadow, not flat fill**: every surface gets a
  vertical light gradient, an occlusion shadow where it meets another surface,
  and a 1-2 px darker outline only where silhouette needs it.
- **Palette**: NASA-white / bare-aluminium / graphite hulls; INTERNATIONAL
  ORANGE accents (handles, stripes, suits); gold MLI foil; dark glass visors
  and screens. Stenciled typography (vessel names, NO STEP marks) where scale
  allows.
- **Nothing floats**: every prop casts a contact shadow on the surface that
  holds it; recessed things (alcoves, hatches) get inner shadow + lip
  highlight; mounted things get a visible mount.

### 1.3 INSTRUMENT layer (HUD, overlays, menus) — mission-control glass
- Dark translucent glass panels, thin rules, generous spacing.
- **ONE accent family**: amber (#FFB000-ish) for interactive/attention, with
  desaturated cyan reserved for orbital/nav geometry. KILL the 4-color chip
  salad. Status semantics live in ICONS + brightness, not rainbow text.
- Monospace telemetry for numbers (it IS instrumentation); Bahnschrift for
  titles. Text is never pure white (#E8E4DA max) and never glows.
- The HUD whispers; the world speaks. If an overlay competes with the planet,
  the overlay loses.

---

## 2. Light rules (all layers)
1. One sun outside; light has a DIRECTION in every frame, and shading agrees
   with it (sprites take a sun_angle; terrain shades ridges accordingly).
2. Interior light comes from fixtures with falloff pools; dark corners are
   allowed and good. Console screens are local color accents (cyan/green/amber)
   that cast glow on their surroundings.
3. Bloom (GL) only on genuine emitters: sun, engine plumes, screens, fixtures,
   city lights. If everything blooms, nothing does.
4. Film grade is the glue: the GL chain (filmic curve faded in shadows,
   per-world split-tone grades, subtle grain, gentle chromatic aberration at
   edges) runs over EVERY scene so the whole game feels shot on one camera.
5. Shadows anchor: contact shadow under every standing object, drop shadow
   behind every wall-mounted object, AO in every recess. This is rule zero of
   "depth" — its absence is why scenes read flat.

## 3. Color discipline
- Global: shadows lean cool, highlights lean warm (the grade enforces it).
- Saturation lives in the WORLD (planet hues, biome palettes, nebula whispers)
  and in small machine accents (orange), never in large machine surfaces or UI.
- Per-world identity grades (already in glpost.GRADES): Mars butterscotch,
  Titan amber gloom, Europa blue-white glare, Moon steel — keep multipliers
  within ~10%; identity is mood, not Instagram.
- Forbidden: candy colors on machines/UI, pure #000 surfaces (space only),
  pure #FFF (sun core/specular only), flat single-color fills larger than
  ~40 px without gradient/grain, neon outlines.

## 4. Motion & feel (when animating)
- Everything eases; nothing teleports. Drift, inertia, slow parallax.
- Idle life: floating crew bob, dust motes in light pools, star twinkle is
  SUBTLE (camera exposure, not fairy lights), cloth/foliage micro-sway.
- Camera: scene transitions fade through black like film cuts (exists);
  screen-shake only for physical violence (ignition, staging, impacts).

## 5. Per-scene application contract
| Scene | World layer | Machine layer | Notes |
|---|---|---|---|
| Map/flight | black space, jewel planets, luminous fading conics | vessel icons crisp | conics = cyan family; sun streak when in frame |
| Ascent/descent | photographic sky gradients, real pad | engineering rocket w/ panel lines, volumetric-feel plume | plume is the bloom hero |
| EVA/mine | geological strata, suit-lamp falloff | orange-accent suit, real tools | darkness underground is REAL darkness + lamp pool |
| Interiors | stars out the portholes | quilted padding, fixtures, consoles w/ glow, contact shadows everywhere | benchmark: the user's Dragon screenshot must look like a real capsule |
| Base/colony | per-world sky + terrain shading | modules as engineered objects w/ AO, utility runs visible | day/night light direction sweeps |
| Drydock | dark hangar w/ work lights | blueprint-on-glass UI + real-material parts | the one place schematic style is allowed (it IS an instrument) |
| Menus | one hero image (planet limb) | — | typography + restraint |

## 6. Production technique (how we hit this procedurally)
- numpy fields for anything organic (clouds, strata, nebula, noise) — domain
  warping for flow; never raw white noise.
- Geometry + vertical gradients + baked AO for anything engineered.
- Additive glow sprites for emitters (GL bloom amplifies them).
- Palette constants live per-module but obey §3; new art reads its world's
  identity from glpost.GRADES keys.
- EVERY art change is verified by screenshot + 2-3 full-size crops, with an
  explicit flaw list, iterated until the list is empty (see visual-standard
  memory). "Runs" is not "done"; "done" means it passes §1-§3 by eye.
