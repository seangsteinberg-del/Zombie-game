# 15 — AUDIO BUILD SPEC (extracted from design/91-15-audio-direction.md)

Source: doc 15 "Audio Direction & Sound Architecture" (canonical audio owner; supersedes-by-expansion 12 §5.10).
DECISIONS overrides applied: **D29** (pre-baked variants, NO runtime DSP — Phase 2/3 gate), **G35b** (original
minimal-ambient score; budget deferred to Phase 2), **A7** (F3 = Planner; perf HUD = **Ctrl+F3** — resolves doc §9-Q9).
Rule IDs AU-1…AU-30 are binding. All dB figures are gain offsets vs the asset's mastered loudness; times are
real seconds unless marked sim.

---

## 1. CANON RULES

### 1.1 The five doctrines
1. **Vacuum silence is canon.** Space makes no sound. Sound exists only: (a) inside pressurized volumes,
   (b) as filtered structure-borne transmission through docked/landed rigid assemblies, (c) in real planetary
   atmospheres at honestly attenuated levels. The camera is the microphone.
2. **Ambience is instrumentation.** Habitat hum keys to live grid load (09); every scrubber/fan/pump loop keys
   to equipment RUNNING state (08/05). The player hears the scrubber spin down *hours of sim time before* the
   Class 3 ppCO2 alert. Sound is telemetry you don't have to read.
3. **Alerts own their sound.** Exactly THREE alarm voices exist (ISS C&W anchor). Almost no event gets a
   bespoke sound on top of its class voice. Discrimination = captions + toasts, not forty jingles.
4. **Silence-first mixing.** Music is episodic, never wallpaper; advisories silent by default; cooldowns are law.
   The mix's resting state is a quiet room with a hum in it. 170-hour campaign: every repeated sound is a tax.
5. **Audio is downstream of the sim, always.** Audio never mutates `World`, never posts events/intents, never
   touches the seeded RNG registry. A muted campaign is bit-identical to a loud one.

### 1.2 Ownership & engine architecture (AU-1…AU-5)
- **AU-2:** audio lives in `audio/` (top-level package, peer of `render/`). Imports pygame + numpy ONLY; never
  `sim/` mutation paths. Reads the per-frame world snapshot + alert/toast stream + a read-only cue feed.
  Import-graph CI test: `sim/` never imports `audio/`; `audio/` never imports `sim/` internals beyond read API.
- **AU-3 (determinism):** audio variation RNG = `random.Random(time.monotonic_ns())` — deliberately OUTSIDE the
  seeded registry. Muted / dummy-driver (CI) / loud runs are bit-identical campaigns.
- **AU-4 (mixer config, binding):** `pre_init(frequency=48000, size=-16, channels=2, buffer=512)`;
  `set_num_channels(32)` + 1 streamed `mixer.music` voice. Latency 512/48000 = 10.7 ms.
  **Click-to-sound ≤ 40 ms typical, ≤ 60 ms worst-case.** Buffer 1024 allowed only as a user setting.
- **AU-5 (threads):** (1) main-thread `AudioDirector` (`audio/director.py`) runs once per render frame after
  `render.frame()`: drains cue ring, computes listener context, ranks emitters, steps gain/duck ramps —
  **budget ≤ 0.3 ms/frame**, perf-HUD line (under **Ctrl+F3** per DECISIONS A7). (2) SDL C callback thread mixes
  (no Python). (3) Audio worker thread: disk I/O / decode of act banks + ambience at act transitions & scene
  loads, returns `(bank_id, Sound)` via thread-safe queue.
- **Cue feed:** `core/events.py` gains a non-authoritative tap — after an event handler runs, append frozen
  `AudioCue(type, class, source_eid, payload_summary)` to a 256-slot ring buffer; director drains per frame;
  full ring drops oldest silently (audio never load-bearing). Alerts + UI interactions append the same way.

### 1.3 Diegetic propagation: listener contexts (binding table)

| Context | When | Hears (diegetic) | Hears (non-diegetic) |
|---|---|---|---|
| DEEP | SYSTEM layer; LOCAL with no focus craft | nothing | music, blip bed, UI, alarms |
| EXTERIOR-VAC | LOCAL exterior view above atmosphere interface | **nothing** — full burn at 2 m camera distance is SILENT (charter shot) | music, blips, UI, alarms |
| EXTERIOR-ATM | LOCAL below atmosphere interface; SITE on body w/ atmosphere | engine/aero/weather foley attenuated by AU-6 | UI, alarms, music |
| CABIN | Pilot mode, crewed+pressurized helm; INTERIOR camera | full interior soundscape at cabin P: hum, equipment loops, own-vehicle foley via `_struct` ONLY | UI, alarms, music |
| TELEMETRY | Pilot mode, uncrewed/unpressurized helm | nothing diegetic — blips, radio squelch on command acts | UI, alarms, music |
| SUIT | EVA crew selected (08 EVA state) | own breathing + suit fan loop; contact-conducted tool/ground thumps (`_struct`-filtered) only | radio squelch, UI, alarms |

- **AU-6 (pressure attenuation law [GAME MODEL]):** for source at ambient/cabin pressure P [kPa]:
  `G_atm(P) = clamp(10·log10(P/101.325), −40, +3) dB`.
  **Hard vacuum cutoff: P < 1 kPa → silent** for ordinary point emitters. Two exempt source classes use the
  law WITHOUT cutoff: **LOUD** (rocket plumes, explosions, ≥140 dB SPL analog) and **WEATHER** (wind/weather
  ambience beds). Worked values: 56.5 kPa exploration atmo → −2.5 dB; Mars 0.61 kPa → −22 dB on LOUD/WEATHER,
  everything else silent (landing burn = distant bass thump; wind = bass-only gust — Perseverance/InSight
  anchor); Titan 146.7 kPa → +1.6 dB (carries BETTER; capped +3).
- **AU-7 (structure-borne path):** exists iff source and listener share a rigid mechanical graph — docked stack
  (06 physics-body merge) or site networks (07 §3.1). Implementation: every foley family ships a pre-baked
  `_struct` variant (**500 Hz low-pass 12 dB/oct, −12 dB, 80 ms decay tail**) — NO runtime filtering (D29).
  CABIN hears its own engines/RCS/docking exclusively via `_struct`: a burn from inside is a hull rumble, never a roar.
- **AU-8 (distance & pan):** within SITE/INTERIOR: `G_dist(d) = −20·log10(max(d,10)/10) dB` (ref 10 m); cull
  emitters below −36 dB net (≈630 m carry at full pressure). Stereo pan by screen position:
  `pan = clamp(0.5 + 0.35·(x_screen − cx)/(w/2), 0, 1)` via per-channel L/R volumes. No pan in DEEP/EXTERIOR-VAC.
- **AU-9 (the ascent fade; signature moment):** engine foley gain follows AU-6 with ambient pressure at current
  altitude — deafening at pad → thins through Max-Q → **total silence as the sky blackens**. Reverse on entry:
  silence → thin shriek → full roar. QA: fade must complete exactly at the atmosphere-interface altitude
  (= rails-warp unlock, 01 §3.6). No scripting; physics drives it.

### 1.4 Ambience-as-instrumentation: sim-state → sound mapping (AU-15…AU-18)

| Sim state (owner) | Sound behavior |
|---|---|
| Grid load f = P_dem/max(P_gen,ε) (09) | Hum = 3 crossfaded loop layers: **IDLE** (f<0.5), **LOAD** (0.5≤f≤0.9), **STRAINED** (f>0.9, adds 50 Hz electrical flutter; also forced while batteries discharge on night side). Linear weights within band; update ≤ 2 Hz; `set_volume` steps ≤ 0.05 (no zipper) |
| Module RUNNING (08/05/04): scrubber, fans, pumps, electrolyzer, Sabatier, foundry, machine shop | Looping emitter while RUNNING. On FAILURE or shutdown, **loop stops within 1 s real** — the diegetic early warning, hours of sim time before the threshold alert |
| FAILURE / MAINTENANCE_DONE | loop stop / loop restart; alert follows per class separately |
| Eclipse (ECLIPSE_IN/OUT) | NO cue — hum dips as PV drops (diegetic consequence only) |
| GRID_DEFICIT | Class 2 voice; hum forced STRAINED |
| SPE active (03 S-8) | dosimeter Geiger-click bed at −28 dB, click rate ∝ dose rate; density peaks at SPE_PEAK; stops at SPE_END + single all-clear chime (distinct from Class 3) |
| Site weather (03/07) | Mars wind/dust beds (WEATHER class, bass-only at 0.61 kPa, ×3 storm intensities); Titan wind/methane-rain (dense, +1.6 dB) |
| Warp tier (01 §3.6) | blip bed density `f_blip = 0.2 Hz × 1.5^tier` (tiers 0–7): 0.2 Hz at 1× → ≈3.4 Hz at tier 7. Physics warp (P2–P4) uses tier-0 density. Blips pause during alarms |
| Tech tier (11) | T0–T1 loops rougher (compressor rattle, relay clicks); T2+ same families smoother/quieter — per-tier loop VARIANTS, not processing |
- **AU-17 (emitter budget):** ≤ 8 concurrent AMBIENCE channels (3 hum layers + 5 top emitters). Rank by net
  gain at listener (AU-6/AU-8), ties by criticality (life support > industry > comfort). Rank at 2 Hz with
  1 s crossfades on swap. ≤ 200 candidate emitters per ranking pass (reuse ledger lists; no 60 Hz scans).
- Honesty hover: hum/status icon hover in Base mode shows WHY ("STRAINED: P_dem/P_gen = 0.94; battery discharging").

### 1.5 Silence-first mixing & loudness law (AU-21, AU-22, AU-25)
- **Loudness targets (ITU-R BS.1770-4), per-asset masters:** alarms **−16 LUFS**, UI **−20**, event foley
  **−18**, ambience loops **−28**, music stems **−23**. True peak ≤ **−1.0 dBTP** every asset.
  **Program ceiling −16 LUFS** integrated over any 20-min window (only alarm passages may exceed momentarily;
  ACT_CHAPTER stinger may hit −14 LUFS momentary). **No loudness floor** — −16±2 band enforced only over
  active program material with BS.1770 relative gating (scored silence + hum excluded). Replacement assets
  must match old mastered loudness ±1 LU. Dev-only `ffmpeg ebur128` lint in CI (dev dep; runtime stays pygame+numpy).
- **AU-21 (ducking law):** Class 1 active → music −18 dB, ambience −12 dB, attack 0.2 s. Class 2 active →
  music −9 dB, attack 0.5 s. Release +6 dB/s starting 5 s after last audible alarm ends. Class 3/4: no duck.
  Per-bus gain ramps stepped per frame by the director.
- **AU-22 (silence budget, binding):** music episodic — at 1×: episodes ≤ 6 min then ≥ 6 min scored silence
  (**hard 50% duty cap**); rails tier ≥ 5: episodes ≤ 3 min per 15 min real. Scheduler AIMS for ≤ 40% of real
  playtime scored at 1×, ≤ 20% under long warp. Episode starts prefer hooks: mode dwell > 2 min, window-open,
  SOI arrival, act ceremony.
- **AU-24 (cooldown law):** every audible non-alarm cue type has a per-(type,source) cooldown (default 10 s);
  global governor **≤ 6 non-alarm cues/s**, overflow dropped silently (toast/log remains). UI exempt above
  50 ms family spacing. "Reduce repetition" setting doubles all cooldowns.
- **Pause:** diegetic loops fade −6 dB and hold; UI/music continue ("pause is the office, not the void").
  **Photo mode:** world muted, music −6 dB, shutter foley only.

---

## 2. ALARM GRAMMAR (AU-10…AU-14; ISS C&W anchor)

Three alarm voices TOTAL, program-wide identical everywhere (trained reflexes; §9-Q7 ruling). Alarms are
**non-diegetic** — they play in every listener context, the one legal violation of vacuum silence ("the alarm
is in your headset, not in space"). Alarm channels are per-class **singletons** — never two copies of one
class voice concurrently. ALARM bus (4 ch) is never stolen.

### 2.1 Voice specs (binding; §4.2)

| Class | Voice | Tone spec | Cadence | Master | Repeat/latch (AU-11) |
|---|---|---|---|---|---|
| 1 EMERGENCY | Klaxon | alternating **800/1000 Hz**, rich-harmonic saw, **2.5 Hz alternation**, 10 ms onset ramps | continuous loop | −16 LUFS | loops until condition resolves / Accept-Risk / Master Alarm; Master Alarm silences **120 s**, then re-arms if condition persists |
| 2 WARNING | Burst tone | **600 Hz** fundamental, **4 pulses × 0.2 s, 0.1 s gaps**, shaped onsets (Patterson) | burst at t=0, then **every 10 s** | −16 LUFS | until acknowledged (toast click / `Enter` / Master Alarm) |
| 3 CAUTION | Chime | two struck tones **880 → 660 Hz**, **0.6 s total**, soft mallet timbre | t=0 and t=30 s | −18 LUFS | 2 plays max; visual cap persists |
| 4 ADVISORY | — | **silent** (visual/log only) | — | — | — |
| Storm marker | Double-pulse | **1200 Hz × 2 × 80 ms** | once per storm | −16 LUFS | — |
| Master Alarm | Clack | electromechanical switch foley (the ONE deliberately physical UI sound; covered-switch grammar) | on `Delete` | −18 LUFS | — |

QA bar: all three class voices mutually discriminable under mono downmix AND 4 kHz-bandwidth laptop speakers.

### 2.2 Master Alarm & dedup
- **AU-12:** `Delete` = Master Alarm: one press kills all Class 2–3 alarm audio instantly (visual caps remain)
  and silences Class 1 for 120 s per AU-11. `Enter` = acknowledge focused toast (stops its repeats).
  Audio adds NO new keybindings.
- **AU-13 (dedup & storm collapse):** merged (source,type) toast re-triggers its alarm sound **≤ once per 60 s**.
  Storm rule: > 3 same-class alarms within 5 s → play ONE class voice + the storm double-pulse marker; Alert
  Center badge carries the count. Nesting with 12 §8-3 CASCADE (> 10 Class-2/3 in 60 s → one Class-2 card):
  the card presents to audio as exactly one Class-2 voice + storm marker. AU-13 de-spams below the collapse
  threshold; 12 §8-3 replaces the stream above it.
- **AU-23:** any event raising a Class 1–3 alert produces ONLY the class voice (+ caption + toast). Bespoke
  audio reserved for: (a) diegetic consequences (loop stop; fire crackle in the burning volume), (b) non-alert
  sim-state foley (dock clunk, staging, touchdown), (c) ceremony stingers, (d) player ALARM_CLOCK
  (triple-beep, deliberately distinct from all C&W voices).

### 2.3 Alarm floor (AU-14; ISO 7731-derived)
While any Class 1–2 alarm sounds, the ducking law guarantees the ALARM bus sits **≥ 12 dB above the sum of
all other buses at ANY master-volume setting** (deliberate 3 dB deviation from ISO 7731's 15 dB — headroom
math vs −1 dBTP caps; AU-21's −18/−12 ducks usually deliver more in practice). **Ironman:** alarm bus slider
floor **40%**, cannot be muted.

---

## 3. SOUND CATALOG

Doc 15 specifies OGG assets (`data/core/audio/<bus>/<family>_<take>.ogg`, `_struct`/`_thin` suffixes,
manifest.toml loudness metadata, 3–5 takes per family, non-repeating random take selection, NO runtime
pitch-shift — variation is takes). **Repo reality:** audio.py pre-bakes everything procedurally from numpy at
startup; that satisfies D29 ("pre-baked variants, no runtime DSP") as long as variants (`_struct` = offline
500 Hz LP/−12 dB/80 ms tail; `_thin` = thin-atmosphere bake) are baked at startup, not filtered at runtime.

### 3.1 Buses & channels (binding; §4.1)

| Bus | Ch | Content | Steal policy / priority |
|---|---|---|---|
| ALARM | 4 | class-voice singletons 1/2/3 + storm marker | never stolen (prio 100) |
| UI | 6 | clicks, confirms, refusals, warp ticks, Master Alarm clack | within bus (80) |
| EVENT | 8 | foley + event cues | within bus, then MUSIC (60) |
| AMBIENCE | 8 | hum layers (3) + top-5 emitter loops | within bus (40) |
| MUSIC | 4 | PULSE, AWE, color stem, stinger | stolen by EVENT under pressure (20) |
| RESERVE | 2 | crossfade headroom | scratch |
| `mixer.music` | 1 stream | music BED / BED-THIN | n/a |

Voice stealing: lowest-priority oldest channel within the bus; alarms steal from any bus except ALARM.
Perf counter: > 10 steals/s logs a sim-warning.

### 3.2 Engines & flight foley (§4.4b; EVENT bus, −18 LUFS, context rules §1.3)
| Cue | Spec / synthesis hint |
|---|---|
| Chemical engines (methalox / H2 roar families) | per-02-class loop families; full roar in EXTERIOR-ATM per AU-6; `_struct` rumble in CABIN; SILENT in EXTERIOR-VAC. (Existing 3-band brown-noise throttle rumble is the right skeleton) |
| NTR | deep turbopump rumble (lower center frequency than chemical) |
| EP / ion | **near-silent coil whine, `_struct` only** — honest: EP makes no airborne sound in vacuum and little anywhere |
| RCS puffs | CABIN `_struct` ticks only; silent exterior in vacuum |
| Staging separation | pyro thump; `_struct` in CABIN |
| Docking | capture + hard-dock latch sequence (Gemini/ISS clunk) — **always `_struct`** |
| Touchdown | gear crunch scaled by vertical speed; per-body regolith variant |
| Parachute deploy / disreef | EXTERIOR-ATM only |
| Ignition countdown | NODE_IGNITION: T−10 s ticks at 1 Hz + ignition foley (diegetic, context-gated) |
| Burn end | cutoff thunk (`_struct` in CABIN) + confirm blip |
| Wheels / construction | wheels-on-regolith per 10 vehicle class; ratchet/weld/regolith-pour loops on focused sites (07 tasks) |

### 3.3 Machinery & habitat loops (§4.4; AMBIENCE bus, mono masters, −28 LUFS)
| Family | Keyed to | Character | Variants |
|---|---|---|---|
| Hum IDLE/LOAD/STRAINED | grid f (09) | broadband HVAC wash, NC-50 feel (present but speech-transparent; ISS US-Lab ~58–62 dBA anchor) | per habitat class (06 can vs 07 ISRU-built differ subtly) |
| Scrubber (CDRA/amine) | LS RUNNING (08 §4) | cyclic sorbent-bed sigh, **6 s period** | `_struct` |
| Cabin fans | ventilation on (08) | steady mid whir | `_struct` |
| Water/coolant pumps | loops active (08/09) | low pulse | `_struct` |
| Electrolyzer / Sabatier | RUNNING (04/05) | bubbling hiss / soft burner | `_struct` |
| Foundry / machine shop | RUNNING (05) | rumble + intermittent strikes | `_thin`, `_struct` |
| Airlock cycle | pump-down/up (08 §3.11) | descending/ascending pump whine, **~30 s** [GAME MODEL duration] | — |
| EVA suit | SUIT context (08) | **breathing + PLSS fan + faint regulator**; exertion variant | — |
| Mars wind / dust storm | site weather | bass-only gusts (WEATHER class at 0.61 kPa) | ×3 storm intensities |
| Titan wind / methane rain | site weather | dense, carried (+1.6 dB cap) | shoreline lap |
| Venus aerostat | 07 §B-8 | constant stratified wind + envelope creak | leak-hiss event foley |
| Dosimeter bed | SPE active | Geiger clicks, rate ∝ dose rate, −28 dB | — |
| Telemetry blips | DEEP/VAC/TELEMETRY | Quindar-flavored (2525/2475 Hz cultural anchor, 250 ms), −30 dB, warp-scaled density | — |
| Fire | volume on fire | diegetic crackle in the burning volume | — |

### 3.4 UI grammar (§4.5; UI bus, −20 LUFS, ≥3 takes/family, 50 ms family spacing)
| Family | Sound | Rule |
|---|---|---|
| click | 2 ms dry tick | every mouse-down on interactive widget |
| confirm | two-tone up (60 ms) | action accepted/committed |
| refuse | dull wooden thud | invalid action — **never a harsh buzzer** (heard 5,000 times) |
| toggle | snap | toggles, tabs |
| warp tick | pitched tick, **11 pre-rendered pitches** up the warp ladder (0, P2–P4, 1–7); 1 take per pitch (ladder IS the variation pool) | every tier change — warp state by ear |
| modal open/close | soft whoosh in/out | modal stack |
| covered switch | guard-flip + heavy click | abort arm, Accept-Risk, Master Alarm |
| typing | paper-soft key ticks | text fields (default on) |

### 3.5 Event cues (§4.3 — 40-type map; non-class-voice rows only)
Class-voice-only rows (play NOTHING but the class voice): IMPACT_PREDICTED(1), BUFFER_EMPTY(3*),
DEPOSIT_EXHAUSTED(3*), GRID_DEFICIT(2*), PP_THRESHOLD(2/3 per 08 band), DOSE_LIMIT(2*), MEDICAL(2*),
SPE_ONSET(2* + dosimeter bed start), DUST_STORM_IN(3* + wind bed), CONTRACT_DEADLINE (chime T−30 d, burst T−7 d).
Silent (Class 4, toast/log only): BUFFER_FULL, WARMUP_DONE, BATCH_DONE, MAINTENANCE_DONE, SHIFT_CHANGE,
TERMINATOR, MEAL/SLEEP, AUTOSAVE_POINT (optional tick default off), ECLIPSE_IN/OUT (hum dips instead).
(* = proposed default class, owner must register per 12 §4.7.)

| Event | Audible cue | Bus / CD |
|---|---|---|
| SOI_CROSS | soft non-diegetic transition swell, 1.5 s | EVENT / 10 s |
| ATMO_ENTRY | starts AU-9 entry foley ramp | AMB |
| PERIAPSIS_MARK / CLOSEST_APPROACH | tick (periapsis only if player-flagged) | EVENT / 5 s |
| BURN_END | cutoff thunk + confirm blip | EVENT |
| ESCAPE_SUN | one-shot ceremonial stinger | MUSIC / once |
| BUILD_DONE | soft confirm | EVENT / 10 s |
| TRANSFER_ARRIVAL | arrival tick | EVENT / 10 s |
| HARVEST | soft confirm | EVENT / 30 s |
| SPE_END | bed stops + single all-clear chime (≠ Class 3 chime) | EVENT |
| OCCLUSION_IN/OUT | link-lost / link-restored squelch (Quindar grammar) | EVENT / 10 s |
| ALARM_CLOCK | player triple-beep, distinct from all C&W voices | EVENT |
| WINDOW_OPEN | **the window bell** — signature two-tone, campaign heartbeat | EVENT / once per window |
| RESEARCH_DONE | confirm motif (short, major-third) | EVENT |
| FAILURE | emitter loop STOPS (the sound is the absence); alert per class | AMB/ALARM |

### 3.6 Ceremony & Chronicle audio (§4.3b)
| Type | Treatment |
|---|---|
| FIRST_* | **first-time long-tail rule:** first occurrence per campaign = full act-flavored stinger (8–12 s); every repeat = short confirm only (40th docking is a clunk and a tick) |
| ACT_CHAPTER | chapter stinger 8–12 s in the INCOMING act's palette; BED crossfades to new bank over 10 s; the only loud music (−14 LUFS momentary allowed) |
| DEATH | memorial: all buses fade −12 dB over 2 s; single low bell once; music suppressed 120 s; **hum returns first — the station keeps running** |
| DISASTER | aftermath silence: 10 s full duck after the Class 1 resolves; world audio returns before music |
| RESCUE | resolution stinger (the campaign's warmest cue) on rescued-crew dock |
| RISK_ACCEPTED | covered-switch foley + low sustained 2 s tone |
| WONDER | wonder stinger + permanently unlocks that body's color stem |
| AUDIT_PASS/FAIL | confirm motif / dissonant suspension (no alarm voice — bookkeeping) |
| EPILOGUE | end-titles suite (the one through-composed piece); Chronicle HTML/PNG export itself silent by design |
| PHOTO | shutter foley; all buses mute except music −6 dB |
| Memorial wall open | music suppressed; room tone + low bell once per visit |

### 3.7 Asset budget (§4.7) — v1 targets
Alarms+markers 6 · UI ≈32–46 · event cues+stingers ~60 · foley families (+variants) ~120 · ambience loops ~40
(per scene) · music stems ~30 (per act). **Total ~290–310 unique; always-resident ≈220–230; RAM ≤ 128 MB**
(SDL converts everything to 48 kHz s16 stereo at load: 192 KB/s per asset regardless of mono-on-disk).
If `_struct`/`_thin` variants push past ~400 assets → numpy offline bake tool first, middleware never (§9-Q2).
Missing/corrupt asset → −30 dB neutral tick + validation warning, never a crash, never silence-without-log.

---

## 4. SCORE

- **Ruling (DECISIONS G35b, binding):** **original minimal-ambient score confirmed** — single composer voice,
  ~90–110 min total (~12–18 min/act + stingers). Only the budget figure deferred to Phase 2. Licensed catalog
  is dead: it would break per-act/per-world stem keying and the color-stem progression.
- **AU-19 (identity):** Eno *Apollo* north star — patient, diatonic-to-modal drift, zero bombast. Per-act
  palettes; per-world **color instrument** overlay stems: Moon = glass armonica, Mars = hammered dulcimer,
  Venus = breath-noise brass, Titan = low woodwind, Jupiter/Saturn = bowed metal. Arrivals are heard as places.
- **AU-20 (adaptive layers):** act bank = **BED** (streamed `mixer.music`) + **PULSE** + **AWE** stems
  (resident Sounds, MUSIC bus), timer-aligned to BED's loop grid within ±80 ms (pygame can't sample-lock —
  drift-corrected timer; `get_pos()` drift > 80 ms → stem restart at next boundary under crossfade). Loop
  lengths 60–90 s. 4-bar quantized stem starts ONLY for fixed-BPM banks (Acts 1, 3, 4); rubato/static banks
  (Acts 2, 5) start stems under 1 s crossfade, no grid.

| State | Layers |
|---|---|
| Pilot, 1×/physics warp, engines live | BED + PULSE |
| Engineer / Planner / Base, 1×–tier 4 | BED only |
| HQ overlay | BED at −6 dB |
| Rails tier 5–7 | BED-THIN (sparser mix of same cue) + blip bed |
| Ceremony stingers | exclusive — interrupt and suppress BED |

| Act | Identity | Palette | Tempo | Stems |
|---|---|---|---|---|
| 1 Earth+LEO | garage-startup optimism | warm analog synth, piano, acoustic guitar, tape | 80–100 BPM | BED, PULSE (motorik), AWE |
| 2 Moon | glassy awe | glass armonica, choir pads, long decays | rubato | BED, PULSE (soft), AWE |
| 3 Mars & NEAs | industry + distance | dulcimer, modal strings, work percussion | 60–80 BPM | BED, PULSE (industrial), AWE |
| 4 Belt & Venus | vastness, money fading | bowed metal drones, breath-brass, sub pulses | sparse | BED, PULSE (low), AWE |
| 5 Jupiter/Saturn | austerity; music as weather | near-static cold pads, bowed metal, sub-bass | none | BED(≈THIN), AWE only |
| Endgame | restrained grandeur | organ + choir, very slow | — | BED, AWE, end-titles suite |

- **When music plays vs silence:** AU-22 episodes (≤6 min on / ≥6 min off at 1×; ≤3 min per 15 min at tier ≥5;
  aim ≤40% scored at 1×, ≤20% warp). Ducks per AU-21. Suppressed: 120 s after DEATH, 10 s after DISASTER
  Class 1 resolve, memorial wall, during ceremony stingers. Music stem master −23 LUFS.
- **Progression hooks:** act banks unlock on ACT_CHAPTER, monotonic (an Act-1-style launch in Act 4 plays
  Act 4's palette). Color stems accumulate per first landing — by Act 5 the system is an orchestra you
  assembled. SSI money-fade (12 E-19): HQ BED swaps Act-1 piano "office with money" voicing → austere voicing.
- v1 ships wordless radio grammar (squelch/Quindar) — NO voice acting (§9-Q5).

---

## 5. GAP vs CODE (aphelion/ui/audio.py today)

Existing: 22.05 kHz stereo mixer (20 ch), 13 one-shot cues (burn/blip/paid/soi/alarm/tick/warn/ignition/
stage/boom/thud/clunk), 3-band throttle-keyed brown-noise engine rumble, 3 crossfading generative pads
(calm/tense/warm), master volume + mute. All procedural numpy pre-bake — that PART matches D29.

| # | Gap | Spec ref |
|---|---|---|
| 1 | **Alarm grammar absent.** One generic "alarm" tone vs the binding 3-voice system: 800/1000 Hz klaxon loop, 600 Hz Patterson 4-pulse, 880→660 chime — plus latching (120 s Master-Alarm re-arm, 10 s Class-2 repeat, 2-play Class-3), `Delete` Master Alarm + clack, storm marker, dedup/collapse, 12 dB alarm floor, Ironman 40% floor | §2 |
| 2 | **No diegetic model.** No listener contexts, no AU-6 pressure law (no ascent fade — the charter shot), no `_struct` path, no distance/pan, no vacuum cutoff. Cues play identically everywhere | §1.3 |
| 3 | **No ambience instrumentation.** No grid-keyed hum (IDLE/LOAD/STRAINED), no equipment RUNNING loops with the stop-on-FAILURE early-warning, no emitter ranking/budget | §1.4 |
| 4 | **No per-world ambience or EVA layer.** Missing Mars/Titan/Venus weather beds, dosimeter bed, airlock cycle, SUIT breathing+PLSS fan, telemetry-blip bed with warp-scaled density | §3.3 |
| 5 | **Engine voice undifferentiated.** One rumble for all engines vs chemical-roar / NTR-turbopump / EP-coil-whine-`_struct`-only doctrine; no RCS ticks, no countdown/cutoff pair | §3.2 |
| 6 | **Music model is moods, not the act system.** 3 ambient pads vs 6 act banks with BED+PULSE+AWE stems, BED-THIN, color-stem unlocks, episode scheduler (50% duty cap), AU-21 ducking, ceremony stingers, first-time long-tail | §4 |
| 7 | **No bus architecture.** Flat 20 channels vs 32-ch partition (ALARM 4 / UI 6 / EVENT 8 / AMBIENCE 8 / MUSIC 4 / RESERVE 2) + priorities + voice stealing + per-bus settings sliders | §3.1 |
| 8 | **Mixer config off-spec.** 22.05 kHz / mixer.init vs binding `pre_init(48000, -16, 2, 512)` + 32 ch; no latency accounting, no 0.3 ms director budget, no cue-ring tap on core/events.py | §1.2 |
| 9 | **No mix/loudness law.** No per-bus LUFS targets, ducking ramps, cooldowns/global governor, captions, hearing-accessibility mode, mono downmix, pause/photo treatments | §1.5, AU-26 |
| 10 | **UI grammar partial.** tick/warn exist; missing confirm/refuse(wood-thud)/toggle/covered-switch/modal whoosh/typing and the 11-pitch warp-tick ladder; no take pools (every cue is 1 take) | §3.4 |
| 11 | **Event map coverage thin.** ~13 of ~40 event types + ceremonies; no window bell, no SPE/dust-storm/occlusion-squelch/contract-deadline/research-motif/ALARM_CLOCK | §3.5–3.6 |
| 12 | Code lives in `ui/audio.py`; spec demands top-level `audio/` package with director, import-graph CI, AU-3 RNG rule, dummy-driver CI path, settings (buffer 512/1024, music duty cycle, reduce-repetition) | §1.2 |

Porting note: the procedural-synthesis approach is compatible with the spec (D29 wants pre-baked, not files
per se), but every bake must hit the §1.5 mastering targets and ship variant bakes (`_struct`, `_thin`,
per-tier, takes) generated offline/at-startup — runtime stays gain+pan only.

### 5.1 Failure modes & QA checklist (doc §8; ship as tests)
1. `mixer.init()` failure is non-fatal: silent mode + captions auto-enable + one-time notice; CI runs
   `SDL_AUDIODRIVER=dummy` every build.
2. Cue ring cleared on load / death / scene transition; loops rebuilt from CURRENT state (AU-16 reads state,
   not history). Audio state is never serialized except user settings.
3. Dropped cues are counted, never queued late ("a 4-second-stale dock clunk is worse than none").
4. Autosave hitch (≤ 200 ms) cannot stutter loops — the SDL callback thread keeps mixing; director work is
   constant-time.
5. Determinism tripwires: import-graph test (sim ↛ audio, audio ↛ sim internals) + muted-vs-loud scripted
   challenge run serializes bit-identically.
6. Alarm-fatigue ruling: if playtests show Master-Alarm spam, the fix is FEWER audible types (tighten the
   event map), never quieter alarms — AU-14 is law.
7. QA items: ascent fade completes exactly at atmosphere-interface altitude; 3 alarm voices discriminable in
   mono on 4 kHz laptop speakers; no information only-audible or only-color (identity = color+shape+sound+text).
