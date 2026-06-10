# 15 — Audio Direction & Sound Architecture

Status: DRAFT v1 for design-bible integration. Owner: audio domain.
Sibling docs: 01-orbital-mechanics.md … 13-architecture.md, plus 90-14-visual-direction-rendering.md.
**This document resolves 13 §9 open question 1** ("Audio architecture is unspecified bible-wide") by becoming the canonical audio owner. 12 §5.10's four rules are adopted verbatim as founding canon and expanded here; 12 §5.10 becomes a pointer to this doc.

---

## 1. Overview

Aphelion's audio answers one question the visuals cannot: *is the machine that keeps you alive still running?* The direction follows from the bible's realism doctrine and from the ~170-hour campaign shape (12 G-12: Act 5 ends ≈ 170 h; credits ~150–220 h):

1. **Vacuum silence is canon.** Space makes no sound (12 §5.10: "no space roar"). Sound exists only inside pressurized volumes (07 B-4a / 08 §3.2 atmosphere state), as filtered structure-borne transmission through docked/landed mechanical assemblies, and in real planetary atmospheres at honestly attenuated levels. The camera is the microphone (§3.3).
2. **Ambience is instrumentation** (ONI lineage). The habitat hum is keyed to 09's live grid load; every scrubber, fan, and pump loop is keyed to 08/05 equipment state. The player *hears the scrubber spin down before the Class 3 alert fires hours later at the ppCO2 threshold*. Sound is telemetry you don't have to read.
3. **Alerts own their sound.** Exactly three alarm voices exist — Class 1 klaxon, Class 2 tone, Class 3 chime (ISS Caution & Warning anchor, 12 A-1) — and almost no event gets a bespoke sound on top of its class. Discrimination comes from captions and toasts, not from forty competing jingles.
4. **Silence-first mixing.** Over a 170-hour campaign, every repeated sound is a tax. Music plays in episodes, not wallpaper; advisories are silent by default; cooldowns are law (§3.7). The mix's resting state is a quiet room with a hum in it.
5. **Audio is downstream of the sim, always.** Audio code never mutates `World`, never feeds the deterministic core, and runs inside 13's threading rules (§3.2). A campaign played muted is bit-identical to one played loud.

Scope: music direction, the diegetic propagation model, the alarm grammar, adaptive mixing, the event-to-sound map against 13 §4.4's 40-type catalog, the pygame.mixer channel/thread architecture, asset and loudness standards, accessibility, and budgets. Out of scope for v1: voice acting, radio chatter dialogue, HRTF/binaural rendering, runtime DSP beyond gain/pan (all §9).

---

## 2. Real-World Grounding

- **ISS Caution & Warning system** — four alarm classes (Emergency, Warning, Caution, Advisory), with the first three annunciated by distinct tones from the C&W panel — advisories are visual/log-only — and a single MASTER ALARM pushbutton that silences the tone while the condition persists. (The silent-advisory detail is exactly what 12 A-1 and AU-10 adopt.) Adopted structurally by 12 A-1/A-6; this doc binds the tone designs (§4.2).
- **Auditory danger-signal standards** — ISO 7731 (auditory danger signals: signal level ≥ 65 dBA and ≥ 15 dB above ambient noise); R. D. Patterson's 1982 CAA guidelines for civil-aircraft auditory warnings (pulse bursts of 4–5 pulses with shaped onsets, distinct inter-burst gaps, against continuous sirens that block speech and thought); IEC 60601-1-8 melodic alarm coding in medical devices. These drive the alarm-floor law (AU-14) and the pulse-burst Class 2 design.
- **ISS acoustic environment** — NASA acoustics requirements (NASA-STD-3001 lineage): continuous noise limit ~NC-50 in work areas, NC-40 in crew quarters; measured US Lab levels ~58–62 dBA; ISS crews historically used earplugs. The habitat hum bed is mixed to *feel* like NC-50, i.e., present but speech-transparent (§4.4).
- **Sound in thin atmospheres** — NASA InSight sensed Martian wind via its seismometer and APSS pressure sensor (2018; the released "audio" was derived from that data — the lander carried no microphone); Perseverance's SuperCam and EDL microphones (2021) directly recorded Martian wind, laser-zap impacts, and the Ingenuity rotorcraft: heavily attenuated, bass-dominated, short carry distances at 0.61 kPa mean surface pressure. Anchors the pressure-attenuation law (AU-6) and the pre-baked "thin-atmosphere" asset variants.
- **Structure-borne sound in spacecraft** — Apollo and ISS crews report hearing docking latches, thruster firings, and MMOD strikes conducted through structure; vibration transmits through a rigid hull where airborne paths don't exist. Anchors the structure-borne path (AU-7).
- **Quindar tones** — Apollo air-to-ground keying tones (2,525 Hz intro / 2,475 Hz outro, 250 ms): the cultural anchor for the telemetry-blip bed (12 §5.10) and radio squelch grammar.
- **Vacuum-silence media precedent** — *2001: A Space Odyssey* (breathing-only EVA scenes) and *Gravity* (2013; structure-conducted-only exterior mix): proof that silence and contact-conducted sound read as dread and scale, not as a missing feature.
- **Score precedent** — Brian Eno, *Apollo: Atmospheres and Soundtracks* (1983, composed for Apollo footage): sparse, patient, awe-without-bombast — the tonal north star. Game-side: Oxygen Not Included's reactive instrumentation (machines and score share a palette), Factorio's restrained ambient-over-machine mix, KSP's silence-heavy map view. All are proofs that quiet scores survive 170-hour exposure.
- **Loudness measurement** — ITU-R BS.1770-4 / EBU R 128 (LUFS, true peak); Sony ASWG-R001 game-loudness recommendation (-24 LUFS console, -18 portable). We treat **-16 LUFS** as the program-loudness ceiling and normalization reference for desktop-speaker/headphone play (§3.8 — a ceiling, not a band: the mix is silence-first), peaks ≤ -1 dBTP.
- **pygame-ce / SDL2 audio** — SDL mixes N channels in a C-side callback thread (no GIL contention during mixing); output latency ≈ `buffer_samples / sample_rate`; pygame-ce 2.5 exposes `mixer.pre_init`, per-channel stereo volume, one streamed `mixer.music` voice, and `Sound` objects decoded resident. The arithmetic behind §3.2's latency budget.

---

## 3. Game Model

Rules are numbered **AU-1 … AU-30**. A programmer implements from these. All dB figures are gain offsets relative to an asset's mastered loudness (§3.8); all times are real-time seconds unless marked sim.

### 3.1 Ownership and boundary (AU-1…AU-3)

- **AU-1 (canon ownership).** This doc owns: alarm sound design and audio behavior (12 A-1/A-3/A-6 audio semantics), the diegetic model, ambience, music, UI sound grammar, the event-to-sound map, asset/loudness standards, and the audio engine architecture. 12 keeps the alert *taxonomy* and UI semantics; 13 keeps the threading and budget law this doc complies with.
- **AU-2 (sim boundary; binding).** Audio lives in `audio/` (new top-level package in 13 §3.2's layout, peer of `render/`). It imports pygame + numpy, **never `sim/`** mutation paths; it reads the same per-frame world snapshot and alert/toast stream the UI reads, plus a read-only cue feed (§3.2). Audio never emits intents, never posts events, never touches the RNG registry. Enforced by the 13 §3.1 import-graph CI test (extended: `sim/` never imports `audio/`; `audio/` never imports `sim/` internals beyond the read API).
- **AU-3 (determinism).** Audio variation (take selection, micro-delays) uses `random.Random(time.monotonic_ns())` — explicitly *outside* 13 §3.10's seeded registry, because audio must be free to vary without ever influencing campaign state. Muted, dummy-driver (CI), and loud runs are bit-identical campaigns.

### 3.2 Engine architecture: mixer, threads, latency (AU-4…AU-5)

- **AU-4 (mixer configuration; binding).**
  ```
  pygame.mixer.pre_init(frequency=48000, size=-16, channels=2, buffer=512)
  pygame.mixer.set_num_channels(32)
  ```
  Output latency = 512 / 48,000 = **10.7 ms**. The 32 channels are partitioned into buses (§4.1). One additional streamed voice (`pygame.mixer.music`) carries the current music BED. **Latency budget (binding):** UI cue dispatched the same frame as the input intent (≤ 16.7 ms) + mixer buffer (10.7 ms) + OS/driver (≈ 10 ms) → **click-to-sound ≤ 40 ms typical, ≤ 60 ms worst-case**; alarm cues dispatch on the render pass of the frame whose event handler raised the alert (same bound). If profiling shows underruns on low-end devices, buffer may rise to 1024 (21.3 ms) — a settings option, not a silent change.
- **AU-5 (thread layout; per 13 §3.10).** Three execution contexts:
  1. **Main thread — AudioDirector** (`audio/director.py`), called once per render frame *after* `render.frame()`: drains the cue queue, computes the listener context (§3.3), selects the top audible emitters to fill the 5 emitter channels (§4.1; the other 3 AMBIENCE channels carry the hum layers), steps gain/duck ramps, issues `play/stop/set_volume`. **Budget ≤ 0.3 ms/frame**, accounted inside 13 §4.6's headroom line; a perf-HUD bar shows it (perf HUD per 13 §3.14; keybinding collision flagged in §9-Q9).
  2. **SDL callback thread** — C-side mixing of the 32 channels; no Python code runs here; CPU cost is not on any Python budget.
  3. **Audio worker thread** — the "audio" worker 13 §3.10 already authorizes: disk I/O and Vorbis decode of act music banks and ambience loops (lazy, at act transitions and scene loads), so the main thread never blocks on audio disk reads. Communicates with the director by a thread-safe queue of `(bank_id, decoded Sound)` results; touches no game state.
- **Cue feed (the one new interface):** `core/events.py` gains a non-authoritative **tap**: after an event handler runs, a frozen `AudioCue(type, class, source_eid, payload_summary)` record is appended to a ring buffer (length 256) that the director drains each frame. Alerts (12 §3.11) and UI interactions append cues the same way. The tap is fire-and-forget: a full ring drops oldest cues silently (audio is never load-bearing).

### 3.3 Diegetic doctrine: the camera is the microphone (AU-6…AU-9)

The listener is the camera (13 §4.8 zoom layers), with one POV override. **Listener contexts (binding):**

| Context | When | Hears (diegetic) | Hears (non-diegetic) |
|---|---|---|---|
| **DEEP** | SYSTEM layer; LOCAL layer with no focus craft | nothing | music, telemetry-blip bed, UI, alarms |
| **EXTERIOR-VAC** | LOCAL exterior view of any craft above the atmosphere interface | **nothing** — a full burn at 2 m camera distance is silent (doctrine; the signature exterior-burn shot this doc treats as its charter) | music, blips, UI, alarms |
| **EXTERIOR-ATM** | LOCAL view of a craft below the atmosphere interface; SITE layer on a body with atmosphere | engine/aero/weather foley attenuated by AU-6 with local ambient pressure | UI, alarms, music |
| **CABIN** | Pilot mode with a **crewed, pressurized** helm craft; INTERIOR layer camera | full interior soundscape at cabin pressure: hum, equipment loops, structure-borne own-vehicle foley (AU-7) | UI, alarms, music |
| **TELEMETRY** | Pilot mode with an uncrewed/unpressurized helm | nothing diegetic — the craft is a data product: blips, radio squelch on command acts | UI, alarms, music |
| **SUIT** | EVA crew selected (08 EVA state) | own breathing + suit fan loop; contact-conducted tool/ground thumps only (AU-7 filtered) | radio squelch, UI, alarms |

- **AU-6 (pressure attenuation law [GAME MODEL]).** For a source in ambient (or cabin) pressure `P` [kPa]:
  `G_atm(P) = clamp( 10 · log10(P / 101.325), −40, +3 ) dB`, with **hard vacuum cutoff: P < 1 kPa → silent for ordinary point emitters**, *except* two source classes that use the law without cutoff: **LOUD** (rocket plumes, explosions, ≥ 140 dB SPL source analog) and **WEATHER** (listener-context wind/weather ambience beds, §4.4 — exempt because the §2 anchor is precisely that wind was recorded at Mars's 0.61 kPa; the doc's own Mars beds must survive the law, not the cutoff). Worked values: exploration atmosphere 56.5 kPa → −2.5 dB (barely thinner); Mars 0.61 kPa → −22 dB on LOUD and WEATHER sources, all ordinary emitters silent — a landing burn is a distant bass thump, the wind a bass-only gust (Perseverance/InSight anchor); Titan 146.7 kPa → +1.6 dB (sound carries *better*; capped +3). Physically this is the density term of radiated intensity at constant T, honestly simplified; tagged [GAME MODEL].
- **AU-7 (structure-borne path).** A structure-borne path exists iff source and listener volume share a **rigid mechanical graph**: a docked stack (06 physics-body merge) or structures connected on a site's networks (07 §3.1). Implementation: every foley family ships a pre-baked `_struct` variant (500 Hz low-pass, 12 dB/oct, −12 dB, 80 ms decay tail) — **no runtime filtering** (dependency policy: pygame + numpy only; runtime DSP is a §9 question). The CABIN listener hears its own vehicle's engines/RCS/docking exclusively via `_struct` variants: a burn from inside is a low rumble in the hull, never a roar.
- **AU-8 (distance and pan).** Within SITE/INTERIOR layers: `G_dist(d) = −20 · log10( max(d, 10) / 10 ) dB` (spherical spreading, d in m, reference 10 m); cull emitters below −36 dB net (carry ≈ 630 m at full pressure; on Mars only LOUD/WEATHER sources survive AU-6's cutoff at all, and at −22 dB their carry is realistically short). Stereo pan by screen position: `pan = clamp(0.5 + 0.35 · (x_screen − cx)/(w/2), 0, 1)`, applied via per-channel L/R volumes. No pan in DEEP/EXTERIOR-VAC (nothing diegetic to pan).
- **AU-9 (the ascent fade; signature moment).** During ascent, engine foley gain follows AU-6 with ambient pressure at current altitude (03/01 atmosphere model): a launch is deafening at the pad, thins through Max-Q, and **fades to total silence as the sky blackens** — physics as drama, no scripting. The reverse plays on entry: silence → thin shriek → full roar. CI-adjacent QA checklist item: the fade must complete by the atmosphere interface altitude, exactly when rails warp unlocks (01 §3.6).

### 3.4 Alarm audio canon (AU-10…AU-14)

Three alarm voices, total (12 §5.10 adopted). Binding asset specs in §4.2.

- **AU-10 (class voices).** Class 1 EMERGENCY = klaxon, continuous; Class 2 WARNING = Patterson-style 4-pulse burst, repeating; Class 3 CAUTION = two-note chime, finite; Class 4 ADVISORY = **silent** (12 A-1). Alarms are non-diegetic (the program's C&W system follows the founder, not the camera) and play regardless of listener context — the one legal violation of vacuum silence, because the alarm is *in your headset*, not in space.
- **AU-11 (repeat & latch law).** Class 1: loops continuously until the condition resolves, the player Accept-Risks (12 A-2), or Master Alarm silences it — silence lasts **120 s**, then the klaxon re-arms if the condition persists (ISS master-alarm behavior). Class 2: burst at t=0, then every **10 s** until acknowledged (toast click / `Enter` / Master Alarm). Class 3: chime at t=0 and t=30 s, then audio ends (visual cap persists per 12 A-2).
- **AU-12 (Master Alarm, `Delete`).** Implements 12 A-6: one press kills all Class 2–3 alarm audio instantly (caps remain) and silences Class 1 audio per AU-11's 120 s rule. The button itself has a heavy electromechanical *clack* (the one deliberately physical UI sound; covered-switch grammar per 12 §5.9).
- **AU-13 (dedup & storm collapse).** Per 12 A-3 dedup, a merged (source, type) toast re-triggers its alarm sound at most **once per 60 s**. **Storm rule:** if > 3 alarms of the same class arrive within 5 s (cascade failures, 13 §8-2 event storms), play **one** class voice plus a distinct "multiple alarms" double-pulse marker; the Alert Center badge carries the count. **Precedence with 12 §8-3:** when 12's CASCADE collapse fires (> 10 Class-2/3 alerts within 60 s → one "CASCADE at site" Class-2 card), it presents to audio as exactly one Class-2 voice plus the storm marker — the card, not the underlying alerts, is what audio voices. The two thresholds are deliberately nested, not in conflict: AU-13's fast local rule (5 s / > 3, same class) de-spams bursts below 12's collapse threshold; 12 §8-3 (60 s / > 10) replaces the stream entirely above it. Audio never plays two copies of the same class voice concurrently — alarm channels are per-class singletons (§4.1).
- **AU-14 (alarm floor; ISO 7731).** Whenever any Class 1–2 alarm is sounding, the ducking law (AU-21) guarantees the alarm bus sits ≥ **12 dB** above the sum of all other buses, at any master-volume setting. This is a deliberate 3 dB deviation from ISO 7731's ≥ 15 dB ambient clearance: with every asset capped at −1 dBTP and alarms mastered at −16 LUFS (§4.2), a full 15 dB floor would force AU-21's ducks to crush the rest of the mix below usefulness during long Class 1 episodes; 12 dB preserves the §4.2 discriminability QA bar within the available headroom, and the AU-21 ducks (−18 dB music, −12 dB ambience) typically deliver well above the floor in practice. In **Ironman** (12 D-2), the alarm bus slider has a floor of **40%** and cannot be muted — you may not difficulty-select your way out of hearing the fire alarm.

### 3.5 Ambience as instrumentation (AU-15…AU-18)

- **AU-15 (habitat hum keyed to 09).** The interior bed is three loop layers crossfaded by grid load fraction `f = P_dem / max(P_gen, ε)` (09 P-1 terms): IDLE (f < 0.5), LOAD (0.5 ≤ f ≤ 0.9), STRAINED (f > 0.9, adds a 50 Hz electrical flutter layer; also forced whenever batteries are discharging on the night side). Layer weights are linear in f within each band, updated at ≤ 2 Hz (no zipper noise; `set_volume` steps of ≤ 0.05). The player learns the pitch of trouble before reading a single gauge.
- **AU-16 (equipment loops keyed to 08/05 state).** Each running module of an audible family (scrubber/CDRA, fans, pumps, electrolyzer, Sabatier, foundry, machine shop — catalog §4.4) is an emitter looping while its ledger state is RUNNING. On FAILURE (pre-rolled, 13 §4.4) or shutdown, **the loop stops within 1 s real** — typically *hours of sim time before* the consequent Class 3 threshold alert (08 §3.2 bands). This gap is the design point: diegetic early warning for attentive players, alarm safety net for everyone (the alert system never assumes the player heard anything — accessibility AU-26).
- **AU-17 (emitter budget).** ≤ **8 concurrent ambience channels** (§4.1). Emitters ranked by net gain at the listener (AU-6/AU-8); ties broken by criticality class (life support > industry > comfort). Rank updates at 2 Hz with 1 s crossfades on swap — no popping when panning across a base.
- **AU-18 (telemetry-blip bed; 12 §5.10).** In DEEP/EXTERIOR-VAC/TELEMETRY contexts, a sparse Quindar-flavored blip bed plays at −30 dB, density scaled by warp: `f_blip = 0.2 Hz × 1.5^tier` for rails tiers 0–7 → 0.2 Hz at 1×, ≈ 3.4 Hz at tier 7 — deep time audibly *rushes*. Physics warp (P2–P4) uses tier-0 density. Blips pause during alarms (they share no attention budget).

### 3.6 Music direction (AU-19…AU-22)

- **AU-19 (identity).** One composer-voice across the campaign, per-act palettes (§4.6): Act 1 warm analog optimism → Act 5 outer-system austerity where music is nearly weather. North star: Eno's *Apollo* — patient, diatonic-to-modal drift, zero bombast. Per-world color: each major body adds one "color instrument" overlay stem (Moon = glass armonica family, Mars = hammered dulcimer, Venus = breath-noise brass, Titan = low woodwind, Jupiter/Saturn system = bowed metal), so arrivals are *heard* as places.
- **AU-20 (adaptive layer model).** Each act bank = **BED** (streamed via `mixer.music`) + **PULSE** + **AWE** stems (resident Sounds on the MUSIC bus, timer-aligned to BED's loop grid within ±80 ms per §8-6 — pygame cannot sample-lock a `Sound` to the `mixer.music` stream, so the drift-corrected timer is the mechanism, not sample alignment; loop lengths 60–90 s). Bar-quantized stem starts at 4-bar boundaries apply **only to acts whose BED has a fixed BPM** (§4.6: Acts 1, 3, 4); rubato/static banks (Acts 2, 5) have no grid — their stems start under a 1 s crossfade without quantization. Keying (mode per 12 G-2, warp per 01 §3.6):

| State | Layers |
|---|---|
| Pilot, 1× / physics warp, engines live | BED + PULSE (rhythmic, low) |
| Engineer / Planner / Base, 1×–tier 4 | BED only |
| HQ overlay | BED at −6 dB (the office) |
| Rails tier 5–7 | BED-THIN variant (sparser mix of the same cue) + blip bed |
| Ceremony (stingers, §4.3b) | exclusive — stingers interrupt and suppress BED |

- **AU-21 (ducking law; 12 §5.10 "music ducks under Class 1–2").** Class 1 active: music −18 dB, ambience −12 dB, attack 0.2 s. Class 2 active: music −9 dB, attack 0.5 s. Release: +6 dB/s starting 5 s after the last audible alarm ends. Class 3+4: no duck. Implemented as per-bus gain ramps stepped each frame by the director.
- **AU-22 (silence budget; binding).** Music is episodic: at 1×, episodes ≤ 6 min followed by ≥ 6 min of scored silence (hum and world remain) — a **structural hard cap of 50% duty**; under rails tier ≥ 5, episodes ≤ 3 min per 15 min real. Episode *starts* prefer hooks: mode dwell > 2 min, window-open, SOI arrival, act ceremony. The episode scheduler *aims* for ≤ 40% of real playtime at 1× on average (the 6/6 structure is the worst-case ceiling, not the operating point — scheduled episodes are usually shorter than 6 min and gaps longer than 6 min), ≤ 20% under long warp. Rationale: 170 h × 40% is already 68 h of score exposure; monotony is the enemy the whole section is built against.

### 3.7 Event-to-sound mapping (AU-23…AU-24)

- **AU-23 (alerts own their sound).** Any queue event whose handler raises a Class 1–3 alert produces **only** the class voice (+ caption + toast). No bespoke per-event alarm sounds exist. Bespoke audio is reserved for: (a) diegetic consequences (a FAILURE stops its loop, AU-16; fire adds a diegetic crackle in the burning volume), (b) non-alert feedback foley (docking clunk, staging, touchdown — sim-state foley, §4.4b), (c) ceremony (§4.3b), (d) the player's own ALARM_CLOCK. Full 40-type map: §4.3.
- **AU-24 (cooldown law).** Every audible non-alarm cue type carries a per-type cooldown (§4.3 tables; default 10 s) keyed (type, source); a global governor caps **≤ 6 non-alarm cues per real second** — overflow is dropped silently (the toast/log remains; audio is never load-bearing). UI sounds are exempt below 50 ms spacing per family (§4.5).

### 3.8 Asset, loudness, and mix standards (AU-25)

- **AU-25 (binding standards).**
  - **Format:** OGG Vorbis q5 on disk for all assets; 48 kHz source masters; SFX ≤ 2 s decode-resident at load (mono unless inherently stereo — note mono saves disk and decode time only: pygame/SDL_mixer converts every `Sound` to the AU-4 device format at load, so RAM residency is stereo-size regardless, AU-27), ambience loops decode-resident per scene, music BED streamed, stems decode-resident per act bank.
  - **Loudness (ITU-R BS.1770-4):** per-asset mastering targets — alarms −16 LUFS, UI −20, event foley −18, ambience loops −28, music stems −23 (EBU R 128 reference). True peak ≤ −1.0 dBTP on every asset. **Program loudness ceiling: −16 LUFS** integrated over any 20-min play window — never exceeded (alarm passages may exceed momentarily; nothing else may). There is deliberately **no loudness floor**: the mix is silence-first (AU-22), and a mandated quiet window legitimately integrates near the −28 LUFS hum bed. A −16 LUFS ± 2 band is enforced only over *active program material* — measured with BS.1770 relative gating, so scored silence and the resting hum are excluded from the integration. Asset CI: a dev-only `ffmpeg ebur128` lint pass rejects out-of-spec files (dev dependency only — the 13 §3.1 runtime rule of pygame+numpy is untouched).
  - **Naming:** `data/core/audio/<bus>/<family>_<take>.ogg`; `_struct` and `_thin` suffixes for pre-baked variants; loudness metadata in a `manifest.toml` validated by 13 §3.4's content pipeline.
  - **Variation pools:** every repeating cue family ships 3–5 takes; selection is non-repeating random (AU-3 RNG). No runtime pitch-shift exists (mixer limitation); variation is takes, not transposition.

### 3.9 Accessibility (AU-26)

- **AU-26 (binding; extends 12 §8 ¶13 color+shape+sound+text redundancy).**
  1. **Full captioning:** every audible cue type carries a caption string (`[source] description`, e.g., `[NODE A] CO2 scrubber spun down`); captions render in the alert strip's caption line (12 §5.1) when "Captions" is on. Alarms are always also visual (toast + cap + screen-edge pulse for Class 1) — already canon, restated as audio's contract.
  2. **Hearing-accessibility mode:** promotes audio-only information to visible advisories — equipment loop stops (AU-16) emit a Class 4 toast; the hum's STRAINED transition emits one advisory.
  3. **Mono downmix** toggle (sums L/R; pan information preserved in caption text "left/right" omitted — pan is never meaning-bearing, rule).
  4. **Per-bus volume sliders** (master, alarms, UI, ambience, foley, music) in settings (13 core.config); **alarm floor** per AU-14; "reduce repetition" toggle doubles all cooldowns.
  5. No information is *only* audible; no information is *only* a color; alarm identity is always (color + shape + sound + text) — QA checklist item, not an afterthought.

### 3.10 Performance and memory budget (AU-27)

- **AU-27 (binding; lives inside 13 §4.6's frame law).**

| Item | Budget | Notes |
|---|---|---|
| AudioDirector main-thread update | ≤ 0.3 ms/frame | inside 13's headroom line; perf-HUD bar |
| Cue ring drain | ≤ 256 cues/frame, O(1) each | ring overflow drops oldest |
| Emitter ranking | 2 Hz, ≤ 200 candidate emitters | reuses ledger module lists; no scans at 60 Hz |
| SDL mixing | C callback thread | not on any Python budget |
| Worker decode | act bank ≤ 1.5 s off-thread | at ACT_CHAPTER / scene load; never blocks |
| Resident audio RAM | ≤ **128 MB** | pygame/SDL_mixer converts every `Sound` to the opened device format at load (48 kHz, s16, **stereo** per AU-4), so a mono-on-disk asset occupies stereo size in RAM: 48,000 × 2 B × 2 ch = 192 KB per second per asset (mono saves disk + decode time, not residency). Resident SFX ≈ 250 assets (≈ 230 always-resident per §4.7 + headroom) × ~1 s ≈ 48 MB; 1 act bank (2 stereo stems + THIN + scene ambience set) ≈ 50 MB; streamed BED ≈ 0 — total ≈ 98 MB typical against the 128 MB cap |
| Channels | 32 + 1 stream | §4.1; voice stealing per priority |

Voice stealing: if a bus is full, steal the lowest-priority, oldest channel *within that bus*; alarms steal from any bus except ALARM. Priorities: ALARM 100 > UI 80 > EVENT 60 > AMBIENCE 40 > MUSIC 20.

---

## 4. Content Catalog

### 4.1 Bus and channel allocation (binding)

| Bus | Channels | Content | Steal policy |
|---|---|---|---|
| ALARM | 4 | one singleton per class voice (1/2/3) + storm marker | never stolen |
| UI | 6 | clicks, confirms, refusals, warp ticks, Master Alarm clack | steals within bus |
| EVENT | 8 | foley + event cues (§4.3, §4.4b) | steals within bus, then MUSIC |
| AMBIENCE | 8 | hum layers (3) + top-emitter loops (5) | steals within bus |
| MUSIC | 4 | PULSE, AWE, color stem, stinger | stolen by EVENT under pressure |
| RESERVE | 2 | crossfade headroom (layer swaps) | scratch |
| `mixer.music` | 1 stream | music BED / BED-THIN | n/a |

### 4.2 Alarm assets (binding specs; ISS C&W + ISO 7731 + Patterson anchors)

| Class | Voice | Spec | Cadence | Loudness | Repeat (AU-11) |
|---|---|---|---|---|---|
| 1 EMERGENCY | Klaxon | alternating 800/1,000 Hz, rich-harmonic saw, 2.5 Hz alternation, 10 ms onset ramps | continuous loop | −16 LUFS | loops; Master Alarm silences 120 s |
| 2 WARNING | Burst tone | 600 Hz fundamental, 4 pulses × 0.2 s, 0.1 s gaps, shaped onsets (Patterson) | burst / 10 s | −16 LUFS | until ack |
| 3 CAUTION | Chime | two struck tones 880 → 660 Hz, 0.6 s total, soft mallet timbre | t = 0 and t = 30 s | −18 LUFS | 2 plays max |
| 4 ADVISORY | — | silent (12 A-1) | — | — | — |
| Storm marker | Double-pulse | 1,200 Hz × 2 × 80 ms | once per storm (AU-13) | −16 LUFS | — |
| Master Alarm | Clack | electromechanical switch foley | on `Delete` | −18 LUFS | — |

All three class voices must remain mutually discriminable under mono downmix and 4 kHz-bandwidth laptop speakers (QA test).

### 4.3 Event-to-sound map — 13 §4.4 full catalog (40 types)

Class column = default alert class raised by the owning system. 12 keeps the taxonomy (AU-1); siblings register their event types into classes per 12 §4.7, and only some rows below are already registered in 12's own tables (IMPACT_PREDICTED → 1, PP_THRESHOLD → 2/3 via the 08 LS bands, CONTRACT_DEADLINE → 3/2 per 12 §8-2). Classes marked **\*** are **proposed defaults** — this doc's suggestion for the owning system (03/05/08/09) to register per 12 §4.7, not yet alert canon. "—" = no alert. Per AU-23, rows whose audio is "class voice" play nothing else. CD = cooldown, real seconds, keyed (type, source).

| Event | Class | Audible result | Bus | CD | Caption |
|---|---|---|---|---|---|
| SOI_CROSS | 4 | soft transition swell (non-diegetic, 1.5 s) | EVENT | 10 | `[craft] Entered X's sphere of influence` |
| ATMO_ENTRY | 4 | starts AU-9 entry foley ramp (diegetic) | AMB | — | `[craft] Atmosphere interface` |
| IMPACT_PREDICTED | 1 | class voice | ALARM | — | `[craft] IMPACT PREDICTED — T−n s` |
| PERIAPSIS_MARK | 4 | tick only if player-flagged | EVENT | 5 | `[craft] Periapsis` |
| NODE_IGNITION | 4 | T−10 s count ticks (1 Hz) + ignition foley (diegetic, context rules §3.3) | EVENT | — | `[craft] Ignition` |
| BURN_END | 4 | cutoff thunk (`_struct` in CABIN) + confirm blip | EVENT | — | `[craft] Burn complete — Δv as planned` |
| CLOSEST_APPROACH | 4 | tick | EVENT | 5 | `[craft] Closest approach: r km` |
| ESCAPE_SUN | 4 | one-shot stinger (rare, ceremonial) | MUSIC | once | `[craft] On solar escape trajectory` |
| BUFFER_FULL | 4 | silent | — | — | `[site] X storage full` |
| BUFFER_EMPTY | 3\* (if critical chain) | class voice | ALARM | — | `[site] X buffer empty` |
| DEPOSIT_EXHAUSTED | 3\* | class voice | ALARM | — | `[site] Deposit exhausted` |
| GRID_DEFICIT | 2\* | class voice; hum forced STRAINED (AU-15) | ALARM | — | `[site] Power deficit — load shed` |
| WARMUP_DONE | 4 | silent (loop starts, AU-16) | — | — | `[module] Online` |
| BATCH_DONE | 4 | silent | — | — | `[module] Batch complete` |
| BUILD_DONE | 4 | soft confirm | EVENT | 10 | `[site] Construction complete: X` |
| FAILURE | per owner | **emitter loop stops (AU-16)**; alert follows per class | AMB/ALARM | — | `[module] FAILURE — x` |
| MAINTENANCE_DONE | 4 | silent (loop restarts) | — | — | `[module] Restored` |
| SHIFT_CHANGE | 4 | silent | — | — | — |
| TRANSFER_ARRIVAL | 4 | arrival tick | EVENT | 10 | `[route] Arrival: manifest` |
| HARVEST | 4 | soft confirm | EVENT | 30 | `[site] Harvest: n kg` |
| ECLIPSE_IN / OUT | 4 | none — hum dips as PV drops (diegetic consequence only) | — | — | `[site] Eclipse entry/exit` |
| TERMINATOR | 4 | silent | — | — | — |
| SPE_ONSET | 2\* | class voice + dosimeter click bed starts (instrumentation, −28 dB, rate ∝ dose rate) | ALARM/AMB | — | `[program] Solar particle event in progress` |
| SPE_PEAK | 4 | dosimeter bed density peaks | AMB | — | `[program] SPE peak flux` |
| SPE_END | 4 | bed stops + soft all-clear chime (single, distinct from Class 3) | EVENT | — | `[program] SPE ended` |
| DUST_STORM_IN / OUT | 3\* / 4 | class voice; exterior wind bed starts/stops (AU-6 WEATHER class at Mars P — bass-only; Perseverance/InSight anchor, §2) | ALARM/AMB | — | `[site] Dust storm` |
| OCCLUSION_IN / OUT | 4 | link-lost / link-restored squelch (Quindar grammar) | EVENT | 10 | `[net] Link lost/restored: route` |
| PP_THRESHOLD | 2/3 per 08 band | class voice | ALARM | — | `[volume] ppCO2 1.0 kPa rising` |
| DOSE_LIMIT | 2\* | class voice | ALARM | — | `[crew] Dose limit reached` |
| MEAL / SLEEP | 4 | silent | — | — | — |
| MEDICAL | 2\* | class voice | ALARM | — | `[crew] Medical event: x` |
| ALARM_CLOCK | 4 (stops warp) | player alarm: triple-beep, distinct from all C&W voices | EVENT | — | `[alarm] label` |
| AUTOSAVE_POINT | 4 | silent (optional tick, default off) | — | — | — |
| CONTRACT_DEADLINE | 3 at T−30 d / 2 at T−7 d (12 §8-2) | class voice at each firing (chime at T−30 d, burst tone at T−7 d) | ALARM | — | `[contract] Due in 30 d` / `[contract] Due in 7 d` |
| WINDOW_OPEN | 4 | **the window bell** — signature two-tone, campaign heartbeat | EVENT | once/window | `[planner] X→Y window open, closes t` |
| RESEARCH_DONE | 4 | confirm motif (short, major-third) | EVENT | — | `[research] X complete` |

\* Proposed default — this event type is not among 12 A-1's registered examples; the owning system registers it into a class per 12 §4.7. Until registered there (or in the owner's own doc), the class shown is this doc's proposal for the owner to confirm, not alert canon.

### 4.3b Chronicle & ceremony audio (12 C-1…C-5)

| Chronicle type | Treatment |
|---|---|
| FIRST_* (12 §4.2 ladder) | **first-time long-tail rule:** the first occurrence per campaign plays the full act-flavored stinger (8–12 s); repeats of the underlying action use the short confirm only |
| ACT_CHAPTER (C-3, G-13) | chapter stinger 8–12 s in the *incoming* act's palette; BED crossfades to the new act bank over 10 s; the only place music is loud (−14 LUFS momentary permitted) |
| DEATH (C-4 epitaph) | **memorial treatment:** all buses fade −12 dB over 2 s; single low bell (once); music suppressed for 120 s real; hum returns first — the station keeps running |
| DISASTER | aftermath silence: 10 s full duck after the Class 1 resolves, then world audio returns before music |
| RESCUE (F-2) | resolution stinger (the campaign's warmest cue) on the rescued-crew dock event |
| RISK_ACCEPTED (A-2) | covered-switch foley + low sustained tone 2 s (the weight of the signature) |
| WONDER | wonder stinger + permanent new color stem unlocked for that body's bank |
| AUDIT_PASS / FAIL | confirm motif / dissonant suspension (no alarm voice — it's bookkeeping) |
| EPILOGUE / export (C-3) | end-titles suite (the one through-composed piece); the HTML/PNG Chronicle export itself is silent by design — a paper trophy |
| PHOTO (C-5) | shutter foley; in photo mode all buses mute except music at −6 dB + shutter |

### 4.4 Ambience emitter catalog (loops; mono; −28 LUFS masters)

| Family | Source state (owner) | Character | Variants |
|---|---|---|---|
| Hum IDLE/LOAD/STRAINED | grid f (09, AU-15) | broadband HVAC wash, NC-50 feel | per habitat class (06 can / 07 ISRU-built differ subtly) |
| Scrubber (CDRA/amine) | LS-CDRA RUNNING (08 §4) | cyclic sorbent-bed sigh, 6 s period | `_struct` |
| Cabin fans | ventilation on (08) | steady mid whir | `_struct` |
| Water/coolant pumps | loops active (08/09) | low pulse | `_struct` |
| Electrolyzer / Sabatier | module RUNNING (04/05) | bubbling hiss / soft burner | `_struct` |
| Foundry / machine shop | module RUNNING (05) | rumble + intermittent strikes | `_thin`, `_struct` |
| Airlock cycle | pump-down/up (08 §3.11 EVA & airlock model) | descending/ascending pump whine, ~30 s [GAME MODEL — duration is this doc's choice; 08 §3.11 specifies prebreathe and per-species gas loss, not cycle time] | — |
| EVA suit | SUIT context (08) | breathing + PLSS fan + faint regulator | exertion variant |
| Mars wind / dust storm | site weather (03/07) | bass-only gusts (AU-6 WEATHER class at 0.61 kPa; Perseverance mic / InSight sensor anchor, §2) | storm intensity ×3 |
| Titan wind / methane rain | site weather (03/07) | dense, carried (146.7 kPa, +1.6 dB) | shoreline lap |
| Venus aerostat | 07 §B-8 | constant stratified wind + envelope creak | leak-hiss event foley |
| Dosimeter bed | SPE active (03 S-8) | Geiger-style clicks, rate ∝ dose rate | — |
| Telemetry blips | DEEP/VAC/TELEMETRY contexts | Quindar-flavored, AU-18 density | — |

### 4.4b Sim-state foley (not queue events; EVENT bus; context rules §3.3)

Staging separation (pyro thump; `_struct` in CABIN), docking capture + hard-dock latch sequence (the Gemini/ISS clunk — always `_struct`), touchdown (gear crunch scaled by vertical speed, body regolith variant), RCS puffs (CABIN `_struct` ticks only; silent exterior in vacuum), parachute deploy/disreef (EXTERIOR-ATM), engine loops per 02 class: methalox/H2 roar families, ion = **near-silent coil whine `_struct` only** (honest: EP makes no airborne sound in vacuum and little anywhere), NTR = deep turbopump rumble; wheels-on-regolith per 10 vehicle class on focused sites; construction (07 tasks on focused sites): ratchet/weld/regolith-pour loops.

### 4.5 UI sound grammar (UI bus; −20 LUFS; ≥ 3 takes per family — warp-tick ladder exempt, 1 take per pitch; 50 ms family spacing)

| Family | Sound | Rule |
|---|---|---|
| click | 2 ms dry tick | every mouse-down on an interactive widget |
| confirm | two-tone up (60 ms) | action accepted / committed |
| refuse | dull wooden thud | invalid action — **never a harsh buzzer** (you'll hear it 5,000 times) |
| toggle | snap | toggles, tabs |
| warp tick | pitched tick, **11 pre-rendered pitches** stepping up the 01 §3.6 ladder (0, P2–P4, 1–7) | on every tier change; the player learns warp state by ear. 11 assets total, 1 take per pitch — the ladder itself is the variation pool, so the multi-take rule does not apply |
| modal open/close | soft whoosh in/out | 13 §3.17 modal stack |
| covered switch | guard-flip + heavy click | abort arm, Accept-Risk, Master Alarm |
| typing | paper-soft key ticks | text fields, optional (default on) |

### 4.6 Music: per-act banks (AU-19/AU-20)

| Act (12 §6) | Identity | Palette | Tempo/feel | Stems |
|---|---|---|---|---|
| 1 — Earth+LEO | garage-startup optimism | warm analog synth, piano, acoustic guitar, tape texture | 80–100 BPM pulse available | BED, PULSE (motorik), AWE |
| 2 — Moon | glassy awe, first otherworld | glass armonica color, choir pads, long decays | rubato | BED, PULSE (soft), AWE |
| 3 — Mars & NEAs | the hinge: industry + distance | dulcimer color, modal strings, work-rhythm percussion | 60–80 BPM | BED, PULSE (industrial), AWE |
| 4 — Belt & Venus | vastness, money fading | metallic bowed drones, breath-brass (Venus), sub pulses | sparse | BED, PULSE (low), AWE |
| 5 — Jupiter/Saturn | austerity; music as weather | near-static cold pads, bowed metal, sub-bass swells | none | BED(-THIN ≈ BED), AWE only |
| Endgame/megaprojects | restrained grandeur | organ + choir, very slow | — | BED, AWE, end-titles suite |

Bank sizes: ~12–18 min unique music per act + stingers; total score ~90–110 min (cost note §9-Q1).

### 4.7 Asset budget (v1 targets)

| Category | Count | Resident |
|---|---|---|
| Alarm voices + markers | 6 | always |
| UI families | 7 families × 3–5 takes + 11 warp-tick pitches (1 take each, §4.5) ≈ 32–46 | always |
| Event cues + ceremony stingers | ~60 | always |
| Foley families (+`_struct`/`_thin` variants) | ~120 | always |
| Ambience loops | ~40 | per scene |
| Music stems | ~30 across 6 banks | per act |
| **Total unique assets** | **~290–310** (always-resident subset ≈ 220–230) | RAM ≤ 128 MB (AU-27) |

---

## 5. Player Interaction & UI

- **Settings (13 core.config TOML):** master + 5 bus sliders (alarm floor per AU-14/Ironman); captions on/off (+ size); hearing-accessibility mode; mono downmix; "reduce repetition" (×2 cooldowns); music duty-cycle (Off / Sparse(default) / Standard); buffer size 512/1024; output device follows OS default.
- **Captions** render in the alert strip line (12 §5.1), max 2 concurrent, 4 s persistence, newest replaces oldest; alarm captions persist while the alarm sounds.
- **Master Alarm** (`Delete`): AU-12. **`Enter`** toast acknowledge stops that alert's repeats (AU-11). Both are 12-canon keys; audio adds no new bindings except none — audio is fully mouse/settings-driven (12 §5.9 philosophy).
- **Readout honesty extends to audio:** hovering the hum/status icon in Base mode shows *why* the soundscape is what it is ("STRAINED: P_dem/P_gen = 0.94; battery discharging"), same as every number's formula hover (08 §5).
- **Perf HUD (per 13 §3.14; this doc asserts no key — see §9-Q9):** audio line — director ms, live channels by bus, cue ring depth, dropped-cue counter, current LUFS estimate (dev builds).
- **Photo mode (C-5):** world muted, music −6 dB, shutter only. **Pause:** diegetic world freezes (loops fade −6 dB and hold), UI/music continue — pause is the office, not the void.

---

## 6. Progression Hooks

- **Act banks unlock on ACT_CHAPTER** (12 G-13): the chapter stinger is the player's audible promotion; act state is monotonic, so the score never regresses (a returning Act-1 launch under Act 4 plays Act 4's palette — the program has changed, and it sounds like it).
- **First-time long-tail rule** (§4.3b) makes the Firsts ladder (12 §4.2) audible exactly once at full weight — the 40th docking is a clunk and a tick, the first is a ceremony.
- **Tech tiers change the machine voice:** T0–T1 equipment loops are rougher (compressor rattle, relay clicks); T2+ variants of the same families are smoother and quieter (automation reads as calm; 05's labor → automation arc becomes audible). Implemented as per-tier loop variants, not runtime processing.
- **World-color stems** accumulate: each new body's first landing (FIRST_*) unlocks its color instrument permanently for that body's scenes — by Act 5 the system is an orchestra you assembled.
- **SSI / money fade (12 E-19):** when the HQ ledger flips to mass, the HQ overlay BED variant swaps from "office with money" (Act-1 piano voicing) to the austere late-campaign voicing — the economy's biggest invisible transition gets a sound.
- **Memorial wall (C-4):** opening it suppresses music and plays room tone + the low bell once per visit. The Chronicle export stays silent (§4.3b) — the trophy is paper.

---

## 7. Cross-System Interfaces

- **01-orbital-mechanics** — *consumes:* warp ladder tier for blip density (AU-18) and warp ticks (§4.5); event-guard timing (alarm cues land before/at warp drops); atmosphere interface altitude for AU-9. *Provides:* nothing upstream (audio is terminal).
- **02-propulsion** — *consumes:* engine class + throttle state for foley families (§4.4b); ion/NTR/chemical distinctions are audible doctrine.
- **03-solar-system** — *consumes:* per-body ambient pressure (AU-6), weather events (dust storms, SPE schedule S-8) for beds and dosimeter clicks.
- **04/05-resources/industry** — *consumes:* module RUNNING/FAILURE states for emitter loops (AU-16); foundry/mass-driver foley on focused sites.
- **06-ships-stations** — *consumes:* docked-stack mechanical graph for the structure-borne path (AU-7); crewed/pressurized flags for CABIN vs TELEMETRY context.
- **07-bases-habitats** — *consumes:* pressurized-volume inventory and cabin P (B-4a) for AU-6 interior gain; site networks as the surface mechanical graph (AU-7); INTERIOR layer cell positions for emitter placement.
- **08-life-support-crew** — *consumes:* equipment run state (CDRA, fans, pumps), cabin composition/pressure, EVA state for SUIT context, alert-band crossings (audio follows class only, AU-23).
- **09-power-thermal** — *consumes:* `P_dem/P_gen` and battery discharge state at ≤ 2 Hz for AU-15; GRID_DEFICIT class mapping.
- **10-vehicles** — *consumes:* vehicle class + motion state on focused sites for surface foley.
- **11-research-tech** — *consumes:* tier tags for loop variants (§6); RESEARCH_DONE confirm.
- **12-gameplay-economy-ui** — *consumes (binding):* A-1 classes, A-2 ack semantics, A-3 dedup, A-6 Master Alarm, C-1…C-5 Chronicle types, modes G-2, keybindings §5.9. *Provides:* the caption stream rendered in 12's alert strip; the audio settings panel contents. 12 §5.10 is superseded-by-expansion (its four rules all survive verbatim: three alarm voices → AU-10; warp-scaled blip ambience → AU-18; vacuum silence in exterior shots → §3.3/AU-6; music ducks under Class 1–2 → AU-21).
- **13-architecture** — *consumes (binding):* worker-thread law §3.10, cue tap on `core/events.py` (§3.2), frame budget §4.6 headroom (AU-27), zoom layers §4.8 as listener contexts, settings/core.config, content pipeline validation §3.4, `SDL_AUDIODRIVER=dummy` CI mode. *Provides:* the resolution of 13 §9-Q1 (vacuum-silence realism is **in scope**, implemented by listener contexts + pre-baked variants, no runtime DSP).
- **90-14-visual-direction-rendering** — *consumes:* photo-mode state and flow (12 C-5 owns the screen; 14 supplies the filter/export recipes) so the §4.3b/§5 photo-mode audio treatment (world muted, music −6 dB, shutter foley) tracks the same mode; the perf-HUD layout (13 §3.14 plus 14's GPU additions) that hosts this doc's audio line (§5). *Provides:* the photo-mode mute/shutter audio spec and the shutter foley asset; the perf-HUD audio-line contents (§5).

---

## 8. Failure Modes & Edge Cases

1. **No audio device / init failure.** `pygame.mixer.init()` failure is non-fatal: the game runs in silent mode, captions auto-enable with a one-time notice. CI's dummy driver exercises this path on every run (13 §3.16-8).
2. **Channel exhaustion.** Voice stealing per AU-27 priorities; alarms can always play (ALARM bus never stolen, class voices are singletons). A perf-HUD counter tracks steals; > 10/s logs a sim-warning (mix design bug).
3. **Cue storms** (event-queue storms, 13 §8-2). The AU-24 global governor (≤ 6 cues/s) and AU-13 alarm collapse bound audio load and annoyance; dropped cues are counted, never queued late (a 4-second-stale dock clunk is worse than none).
4. **Stale cues across load/scene change.** The cue ring is cleared on load, mode of death, and scene transitions; loops are rebuilt from current state (AU-16 reads state, not history) — audio state is **never serialized** except user settings.
5. **Loudness creep.** The asset-lint CI (AU-25) plus the dev-build LUFS meter prevent the classic ratchet; any asset replacing an old one must match its mastered loudness ± 1 LU.
6. **Music/stem desync.** In fixed-BPM act banks (Acts 1, 3, 4 per §4.6), stems start only on BED's 4-bar boundaries — a timer-based grid built from the BED's known BPM, since pygame offers no sample-accurate sync between a `Sound` and the `mixer.music` stream; `mixer.music.get_pos()` drift > 80 ms triggers a stem restart at the next boundary, inaudible under crossfade. Rubato/static banks (Acts 2, 5) have no BPM and therefore no grid: their stems enter under a 1 s crossfade at any time (AU-20), so grid desync is impossible there by construction.
7. **Underruns / buffer stutter on weak hardware.** Settings buffer 1024 fallback (AU-4); the director's work is constant-time so audio never amplifies a sim-side spike; during the ≤ 200 ms autosave hitch (13 §1) loops simply continue from the callback thread — audio is the one subsystem a hitch *cannot* stutter.
8. **Missing/corrupt asset.** Loader substitutes a −30 dB neutral tick + logs a content-validation warning at load (13 §3.4 pipeline); never a crash, never silence-without-log.
9. **Alarm fatigue (human failure mode).** Bounded by design: 3 voices total, AU-11 finite repeats for Class 3, AU-13 collapse, AU-24 cooldowns, Class 4 silent. If playtests still show Master-Alarm-spam behavior, the fix is fewer audible types (tighten §4.3), never quieter alarms (AU-14 is law).
10. **Determinism regression risk.** The only audio→sim surface is none (AU-2); the import-graph test and the AU-3 RNG rule are the tripwires. A challenge-run muted and unmuted must serialize bit-identically (add to 13 §3.16-5's scripted determinism test).

---

## 9. Open Questions

1. **Original vs licensed score.** §4.6 assumes ~90–110 min of original commissioned music (single composer voice). Licensing (e.g., existing ambient catalog) halves cost but breaks per-act/per-world stem keying (AU-20) and the color-stem progression (§6). Recommendation: original; decide at Phase 2 budgeting.
2. **Hand-rolled adaptive mixer vs middleware.** FMOD/Wwise would give runtime filters, real sidechains, and authoring tools, but violates 13 §3.1's pygame+numpy-only runtime law. This doc's design (pre-baked variants, gain-only runtime) deliberately fits the law. Standing question: if pre-baked `_struct`/`_thin` variants bloat the asset count past ~400, revisit a numpy-based offline bake tool first, middleware last.
3. **Runtime DSP via numpy.** A small block-processing path (one-pole low-pass on int16 arrays via `sndarray`) could replace `_struct` variants and enable continuous pressure-filtering (AU-6 currently quantizes to full/thin/struct). Feasible within the dependency law; costs latency (+1 block) and complexity. Prototype at Phase 1; adopt only if the variant library proves unwieldy.
4. **Cell-level occlusion (07).** v1 treats each pressurized volume as one acoustic space (AU-6 cabin P, no per-wall occlusion). Does INTERIOR play need door/bulkhead muffling from 07's cell graph (hear the fire behind the hatch)? Depends on 13 §9-Q3's crew-agents decision; recommend: defer with the same v1-icons logic, revisit post-1.0.
5. **Radio chatter / crew voice.** Wordless radio grammar (squelch, Quindar) is in (§4.3); actual voice (Flight Director T-3 readouts, crew callouts) is a large localization/casting cost and risks 170-hour repetition. Recommend: v1 ships wordless; revisit with playtest data.
6. **Caption localization pipeline.** Captions (AU-26) are strings in content packs — confirm 12/13's localization story covers them (likely yes via the content pipeline); flag so audio isn't the doc that breaks i18n.
7. **Per-body alarm flavor.** Should alarms differ by habitat class or stay program-wide identical? Current ruling: identical everywhere (alarms are trained reflexes, ISS anchor); revisit only if playtests show context confusion.
8. **Endgame megaproject soundscapes.** Mass drivers, Europa bore, Venus aerostat city (07 WONDERs) deserve bespoke sound identities beyond §4.4's families — scope after 07's final megaproject list freezes.
9. **Perf-HUD keybinding collision (12 vs 13).** 12 G-2/§5.9 binds `F3` to Planner mode; 13 §3.14 and 90-14 bind `F3` to the perf HUD. Both are binding consumed canon for this doc, so the audio sections reference the perf HUD by section (13 §3.14) and assert no key (§3.2 AU-5, §5). 12/13 own the resolution; this doc adopts whatever key survives.
