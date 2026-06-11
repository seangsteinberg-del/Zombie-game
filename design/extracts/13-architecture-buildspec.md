# 13 — Technical Architecture: BUILD SPEC

Extracted from design/13-architecture.md (DRAFT v1) + design/DECISIONS.md (DECISIONS wins conflicts).
Target: Python 3.12 + pygame-ce 2.5 + numpy 1.26. Runtime deps are pygame-ce and numpy ONLY —
no scipy, no ECS lib, no JSON-schema lib, no UI toolkit. `sim/` imports numpy only, never pygame
(CI import-graph test). Optional GPU path (90-14) targets GL 3.3 core, desktop-only (DECISIONS G35a).

---

## 1. ENGINE CONTRACTS

### 1.1 The single global event queue (§3.8, §4.4) — THE doctrine

- ONE `heapq` of `(t_due: float64, seq: int, EventRecord)`. `seq` is a monotonic tiebreaker →
  total deterministic order. The warp controller, autosave, and ledger all read the SAME queue.
- **Cancellation is lazy**: records carry a `generation` int captured at post time; on pop, compare
  to the source's current generation; stale → silently discarded. One generation bump = O(1)
  invalidation of every prediction that source ever posted (e.g., a burn changes the orbit → bump).
- **Three binding contracts every system obeys:**
  1. **Predict, don't poll.** Any system that knows its next discontinuity (tank empty at current
     rates, SOI crossing on current conic, SPE end) posts it when the prediction becomes valid and
     bumps its generation when inputs change. No polling code path exists anywhere.
  2. **Events are exact clamps.** The rails warp loop never advances past `events.peek_time()`.
     There is no "check if we missed it" path — nothing tunnels through a warp step, by construction.
  3. **Handlers are bounded.** A handler may mutate state, post new events, request a warp change;
     it may NOT advance time. Budget 0.5 ms typical (long work like a ledger re-solve OK — events
     are rare, tens per sim-day).
- **Record shape:** `(t_due f64, seq u64, type, source_eid, generation u32, payload dict)`.
  Payload keys snake_case; values are JSON scalars, entity ids, or content ids only — never live
  object references (so persistent records serialize without special cases).
- **Event catalog (~40 types, §4.4):**
  - Orbital: SOI_CROSS, ATMO_ENTRY, IMPACT_PREDICTED, PERIAPSIS_MARK, NODE_IGNITION, BURN_END,
    CLOSEST_APPROACH, ESCAPE_SUN.
  - Ledger a/b (predictions, recomputed on load): BUFFER_FULL, BUFFER_EMPTY, DEPOSIT_EXHAUSTED,
    GRID_DEFICIT.
  - Ledger c (scheduled): WARMUP_DONE, BATCH_DONE, BUILD_DONE, FAILURE (pre-rolled), 
    MAINTENANCE_DONE, SHIFT_CHANGE, TRANSFER_ARRIVAL, HARVEST.
  - Environment: ECLIPSE_IN/OUT, TERMINATOR, SPE_ONSET/PEAK/END, DUST_STORM_IN/OUT,
    OCCLUSION_IN/OUT (comms).
  - Crew/LS: PP_THRESHOLD, DOSE_LIMIT, MEAL/SLEEP (batched daily), MEDICAL.
  - Meta: ALARM_CLOCK (player-created, first-class queue citizens, serialized), AUTOSAVE_POINT,
    CONTRACT_DEADLINE, WINDOW_OPEN, RESEARCH_DONE.
  - **Persistence split:** pre-rolled fate + alarms + deadlines + WINDOW_OPEN + RESEARCH_DONE +
    TRANSFER_ARRIVAL SERIALIZE into saves; predictions (class a/b, SOI) recompute on load.
  - Binding payload schemas for orbital + persistent types are tabled in 13 §4.4 (save-format law).

### 1.2 Warp ladder + main loop (§3.5; ladder owned by 01 §3.6)

- `SIM_DT = 0.02 s` (50 Hz, binding). Render paced by vsync 60 Hz (fallback `Clock.tick(60)`).
  `REAL_DT_CLAMP = 0.25 s` spiral-of-death guard; accumulator saturated 60 frames → auto-pause
  with "simulation overloaded" + perf HUD hint (never slow-motion mush).
- **Two warp modes:**
  - NUMERIC (1× + physics warp P2–P4 = 2–4 RK4 substeps): Fiedler accumulator;
    `alpha = accumulator/SIM_DT` render interpolation (two stored states per NUMERIC craft).
  - RAILS (tiers 1–7: 5× / 25× / 100× / 1,000× / 10,000× / 100,000× / 1,000,000×):
    `t_clamp = min(t + rate*real_dt, events.peek_time())` → `advance_analytic(t, t_clamp)`;
    if clamped, handle event + step down per 01 §3.6. `alpha = 0` (rails positions exact at t).
- **`advance_analytic` does NO per-tick work**: rails elements are time-parametric (positions
  evaluated lazily by whoever asks); ledger advances piecewise-linearly; environment/dose/boiloff
  are closed-form evals at t1−t0. Cost is INDEPENDENT of warp rate — tier 7 costs the same per
  frame as tier 1. This is the single most important performance property.
- **`step_numeric` fixed order:** (1) flight programs set throttle/gimbal; (2) RK4 all NUMERIC
  craft; (3) contact/landing; (4) resource ticks due (engine propellant inside RK4 mass flow);
  (5) hourly boundary work (LSC, thermal, dose, ledger micro-advance); (6) pop due events.
- **Mode transitions:** NUMERIC→RAILS requires thrust=0, outside atmosphere, not landed → refit
  conic elements, drop Cartesian state. RAILS→NUMERIC at event boundaries only (node ignition
  −10 s, atmosphere interface). The warp controller OWNS transitions; gameplay requests, never forces.
- **Time:** float64 s from epoch 2049-01-01 00:00 UTC. During numeric flight, drift-free time:
  `t = t_anchor + n_steps*SIM_DT` (int64 counter); re-base on every mode switch.
- Rails warp forbidden under thrust / below atmosphere interface; physics warp blocked when
  q > 20 kPa or |a_thrust| > 30 m/s². Pause is a real mode (planning UI fully live).

### 1.3 Analytic-first / LEDGER doctrine (§3.9) — the warp workhorse

- **The ledger is NOT a warp mode — it is the ONLY model** for production, life-support stores,
  and power balance at every time rate. 1× advances in ≤1 h segments at hourly boundaries; tier 7
  in one ~4.63 h span per frame. One code path = no 1×-vs-warp divergence, by construction.
- **Model per site (`LedgerNetwork`):** Buffers (level L, capacity C; kg / kWh / crew-h), recipe
  Transformers (state machine OFF/STARTING/RUNNING/STARVED/BLOCKED/DEGRADED/FAILED/MAINTENANCE;
  modifiers f_power·f_labor·f_condition·Y per 05 F-1), Sources/sinks (deposits, crew metabolism,
  power, documented vents). All flows piecewise-constant between events → the ledger is EXACT.
- **Pooling rule (binding):** one logical buffer per resource per network (L=Σ levels,
  C=Σ capacities); links are module↔resource recipe adjacency, not pipes.
- **`ledger_advance(t0,t1)` loop:** solve_rates → next boundary = min(buffer hit Δt, deposit
  exhaustion, scheduled class-c: warmup/batch/build/shift/pre-rolled failure/maintenance/eclipse/
  terminator/transfer arrival) → exact linear update (clamp |L−bound|<1e-9 to bound) → apply
  boundary, bump generations, re-solve only the affected subgraph → loop. After t1, post the next
  boundary to the GLOBAL queue so the warp guard sees it.
- **`solve_rates`:** module rate = R_nom·f_power·f_labor·f_condition·Y, throttled by empty inputs
  (run at inflow rate) and full outputs (run at drain rate). Power couples globally
  (f_power = clamp(P_supplied/P_required) from the 09 grid solve). Spec'd solution: Tarjan SCC
  condensation + topological order; within an SCC, monotone fixed-point (non-increasing from
  unthrottled start ⇒ converges; cap 32 iters, tol 1e-9 kg/s; non-convergence → freeze at last
  iterate + sim-warning, NEVER an infinite loop). Typical base <60 modules, solve <0.3 ms.
- **Failure pre-rolls (warp-fairness law):** on entering RUNNING, pre-sample time-to-failure from
  Exponential(MTBF) (wear-unit based per 05 §3.10; re-sample on >10% throughput change) using the
  module's named substream. Failure lands at the same sim time at 1× or tier 7 — warp can never
  dodge or farm risk. Pre-rolls are FATE: they serialize into saves; reload does not reroll.
- **Equivalence law:** `ledger_advance(t0, t0+30 d)` vs a test-only brute-force 1 s ticker on
  randomized bases — every buffer within **max(0.1 %, 1 kg)**. This test IS the warp-correctness
  guarantee (§3.16-3). Plus property test: Σ(buffers + deposits + vented) conserved within 1e-9 kg.
- **LSC coupling:** gas masses are ordinary ledger buffers; threshold crossings (ppO2 < 16 kPa)
  predicted analytically and posted; hourly class-c boundaries only when nonlinear effects armed.
  A stable 6-year cruise costs ~zero CPU; a degrading loop wakes the sim exactly when it should.

### 1.4 SYSTEM + LOCAL layer split & body-centric float64 frames (§3.7, §4.8)

- **Storage:** every dynamic state body-centric float64 in its SOI frame; rails objects store
  elements `(μ, a or α, e, ϖ, τ, s)` — zero secular drift (time-parametric, no accumulated adds).
  SOI tree (Sun→planets→moons) is the only path to absolute positions; ≤3 hops compose on demand.
- **Floating-origin rule (binding):** `screen = (p_frame − cam_frame) · zoom · flip + center`,
  subtraction performed FIRST, in float64, in the camera's SOI frame; only camera-local smalls may
  narrow to float32/int. Enforced by ONE choke point `camera.world_to_screen()`; layers are
  forbidden to roll their own transform (code-review rule + Neptune-orbit fixture unit test
  asserting residual < 0.5 px; correct ordering yields 0.13 px worst case).
- **SDL int safety:** clip every primitive in float64 camera space to viewport + 8,192 px guard
  band BEFORE int conversion (Cohen–Sutherland in `render/draw_conics.py`).
- **Zoom layers (§4.8, binding):** SYSTEM (heliocentric, 1.6e-10–1e-6 px/m) ↔ LOCAL (SOI frame,
  1e-7–0.05) ↔ SITE (tile map, 0.5–50; opens at 16 px/m regardless of LOCAL z; reverse reopens
  LOCAL at 0.01) ↔ INTERIOR (16–128). Hysteretic handoffs (SOI >60% screen → LOCAL; <40% back);
  150 ms crossfade anchored on the focus craft's screen position. Camera re-anchors frames in the
  same render frame on focus SOI change (no visual pop — subtraction exact at crossing).

### 1.5 Determinism rules (§3.10) — binding

- **Single-threaded sim.** All mutation on the main thread. Workers ONLY for: zlib save
  compression, terrain chunk gen (pure seed→array), audio. None touch `World`.
- **Fixed iteration order** everywhere: sorted ids or insertion-ordered dicts; queue `seq`
  tiebreaker for same-timestamp events.
- **RNG:** campaign seed (uint64, player-visible) → `numpy SeedSequence` → named PCG64 substreams
  per domain+entity: `rng("failures", module_uid)`, `rng("terrain", body, sector, slot)`,
  `rng("solar")`, `rng("contracts")`. Streams independent — burning one never shifts another.
  Stream states serialize into saves.
- **`hash()` is FORBIDDEN in `sim/`** (per-process SipHash salt) — stable hashing via `hashlib`
  only; enforced by lint rule alongside the import-graph test. Terrain seed derivation is pinned:
  sha256 of `"{body}:{sector}:{slot}"` first 8 bytes LE, XOR campaign_seed.
- **Pre-rolled outcomes** (failure times, SPE Poisson schedule) are drawn at defined trigger
  points and saved — reload + different route does not reroll fate.
- **Promise (DECISIONS D30):** per-platform bit-exactness is the v1 promise (CI-tested: same save
  + scripted intents, twice, in-process and cross-process ⇒ bit-identical end serialization).
  Cross-platform divergence at 1e-15 accepted; saves are state snapshots, never input replays.
- The sim never reads wall-clock, locale, or filesystem order. Autosave timing is the only
  wall-clock consumer and lives outside `sim/`.

### 1.6 The 50 Hz RK4 LOCAL integration contract (§3.6)

- **Under force:** RK4, fixed dt = SIM_DT = 0.02 s at 1×; 5-state (x, y, vx, vy, m); gravity from
  current SOI body only + thrust + atmo drag/lift below interface; mass flow inside the state.
- **Thrust warp** (≤1,000× while burning): RKF4(5) adaptive, rel tol 1e-9, dt additionally capped
  so `a_thrust·dt ≤ 1 m/s`. Budget **2 ms/frame TOTAL across all NUMERIC craft**; warp controller
  lowers rate when measured >2.0 ms for 30 consecutive frames.
- **Concurrent NUMERIC craft cap: 8.** A 9th is queued; burn slips seconds; player notified.
- **Prediction = same code path:** node planner / pre-flight ascent sim run the same RKF4(5) in a
  scratch world at tol 1e-7; prediction never mutates live state (06 §5 "same code path" law).
- **Replay/flight-recorder hook (DECISIONS C21, Phase 1, binding):** the integrator emits state
  samples at event boundaries from Phase 1 onward; player-facing replay ships later. Must exist
  in the integrator before Phase 1 closes (smoke test: hook emits samples, no UI).
- SOI checks for NUMERIC craft: per-step distance test vs candidate set (parent + children of
  parent within 2× SOI). Rails crossings: coarse sample (elliptic: min(T_craft,T_body)/64;
  hyperbolic: analytic time-to-boundary span/64, capped T_body/64) + Brent refine to ±1 s;
  hysteresis 1.01/0.99·r_SOI + 60 s re-entry lockout live in the predictor, not the queue.
- **NaN containment:** debug asserts finiteness after every RK4 step + element fit; release checks
  at mode transitions/handlers → restore last-good snapshot, drop to 1×, sim-warning. Serializer
  refuses NaN.

---

## 2. PERFORMANCE CONTRACT (§3.14, §4.6 — binding, CI-enforced)

- **Frame split @60 fps (16.7 ms): sim ≤ 8.0 ms hard cap, render ≤ 7.0 ms hard cap,
  input/UI ≤ 1.0 ms, headroom ≥ 0.7 ms.** Worst-case frame (warp landing + autosave) ≤ 200 ms
  hitch (≤150 ms main-thread serialize + frame work), never a freeze.
- **Budget lines (ms/frame @1× / @tier 7):** RK4 craft 2.0/—; batch rails eval (≤2,000 obj)
  0.5/0.8; SOI prediction 0.3/0.6; ledger all sites 0.5/3.0; LSC/env/dose 0.5/1.0; comms 0.2/0.3
  (confirmed at Phase 4 gate per C22); events+warp 0.2/0.5 → sim total 4.2/6.2. Render: starfield
  + world vector 3.5; sprites/sites/particles 2.0; text+HUD 1.5 → 7.0.
- **Scale caps are design LAW, not hopes:** ≤2,000 entities; ≤600 parts/vessel; ≤8 NUMERIC craft;
  ≤200 ledger modules/site; ≤50 ledgered sites; ≤16 resident site maps; ≤300 comms nodes;
  ≤4,000 particles; ≤256 cached chunks.
- **Named perf scenes (pytest-benchmark; CI asserts budgets ×3 slack; regression >1.5× median
  fails the build).** The doc defines FIVE scenes — there is no P2:
  - **P0** "2,000 rails objects" (one vectorized Kepler solve < 0.5 ms)
  - **P1** "600-part launch"
  - **P3** "200-module base at tier 7" (5 bases hold 60 fps — Phase 3 DoD)
  - **P4** "8 simultaneous burns" (2 ms total line)
  - **P5** "Jupiter system, 60 conics + comms"
- **numpy batch propagation rules:** `propagate_batch(elements_soa, t)` structure-of-arrays over
  ALL rails objects in a frame, vectorized Newton with convergence mask (3–5 iters typical);
  consumed by renderer, comms, SOI predictor — all reading the per-frame ephemeris cache (body
  positions computed once per render frame, nothing recomputes). Review rule: any per-frame Python
  loop over >100 items needs a numpy justification comment or gets vectorized.
- **Render cache rules (§3.13):** full redraw of the world layer every frame (dirty rects only in
  the HUD/widget layer, where they pay). Starfield regenerated only on camera move > threshold.
  Conics: ≤256-point batched true-anomaly sampling, LOD (<8 px → 2-point tick, <2 px → cull;
  200 visible worst case 5 ms, typical 30–60 ≈ 1.5 ms). Text: glyph atlas per (font,size) + LRU
  4,096 rendered strings; NO `render()` call for a string already on screen last frame; per-frame
  numerics draw glyph-by-glyph. Sprites: whole-vessel cached surfaces re-rasterized per ×1.6 zoom
  band; <64 px → icons. Site chunks pre-rasterized 64×64-tile per zoom band, LRU 256. Particles:
  SoA numpy, cap 4,000, zero per-frame allocation.
- **Governors degrade gracefully, VISIBLY:** thrust-warp rate cut, ledger tier step-down (7→6),
  particle cap, conic LOD. Every governor logs to the perf HUD; the UI states the reason ("warp
  limited by base simulation load") — never silent slowdowns.
- **Perf HUD on Ctrl+F3** (DECISIONS A7 — F3 is the Planner; this overrides 13's original F3),
  ships in release builds: per-subsystem ms bars, 240-frame history, entity/event/cache counters,
  governor status. `--profile` flag wraps loop in cProfile. PR policy: no optimization without an
  attached profile capture.
- **GC:** minimize churn, `gc.freeze()` after content load, explicit `gc.collect()` at scene
  transitions/autosaves where a hitch is already accepted.
- **Event-storm guard:** per-source rate limiter (≥1 s sim between same-type boundaries from one
  source); HUD counter + sim-warning past 100 events/sim-day from one source.

---

## 3. CONTENT PIPELINE (§3.4, §4.2, §3.15)

### 3.1 Data-driven content rules

- Code knows mechanics; data knows content. Every part, recipe, body, sector, tech node, contract
  template, program is a TOML (hand-authored) or JSON (bulk/machine-generated) file; both
  normalize to the same dataclasses. Saves are always JSON.
- Ids are `"<pack>:<name>"` globally unique. Packs are directories under `data/`; load order
  `core` first, then mods alphabetically. Later packs ADD ids or PATCH existing ones (shallow key
  override, explicit `"patch": true`); silent collisions are a hard load error.
- No engine feature is tier-gated; tiers (T0–T4 on every item) gate DATA. `sim.research` exposes
  `unlocked(id)`; the loader never hides items (locked parts render greyed in the builder).
- Schema examples with binding field names: 13 §4.2 (part/body/tech/recipe); 05 §3.2 recipe JSON
  is normative for recipes.

### 3.2 Schema validation = build failure

- `content/validate.py` runs on EVERY launch (<200 ms core; results cached keyed by content-hash):
  1. Schema: required keys, types, unit ranges (`isp_s ∈ (0,20000]`, `tier ∈ {T0..T4}`).
  2. Referential integrity: every referenced id exists (recipe modules, tech prereqs, body parents).
  3. Physics invariants: recipe mass balance within 0.5 %; republished SOI values match 01 canon;
     part mass > 0; engine `thrust/(g0·isp·mdot) ≈ 1`.
  4. Tier-gating sanity: no T0 part needs a T3 input chain (graph reachability — WARNS, not errors).
- Failure prints file, key, expected/got and REFUSES to start. CI validates `data/core` as a job;
  tech-tree acyclicity + reachability validated.

### 3.3 Modding folder format (DECISIONS G35c: folder mods v1; Workshop deferred)

- Drop a pack directory beside `data/core/`: `data/<pack>/{bodies,parts,recipes,tech,sectors,
  contracts,programs}/*.toml|*.json`. Mods validate IDENTICALLY to core — the validator IS the
  modding API contract; errors surface in a launcher-style content report (file/key listed).
- Conflict law: duplicate id without `patch:true` = hard error naming both files. A mod removed
  out from under a save → loader substitutes a tagged placeholder part (mass, no function) and
  warns, instead of refusing the save.
- Public API = content schemas + validator ONLY; internal modules documented unstable pre-1.0 (R9).

### 3.4 Save schema versioning & migration harness (§3.15, §4.5)

- **File format `<name>.aph`:** line 1 = UNCOMPRESSED UTF-8 JSON header + `\n`
  (`{"magic":"APHSAVE","schema":N,"game_version":...,"t_sim":...,"label":...,"playtime_s":...,
  "focus":...,"body_sha256":...,"body_len":...}`); rest = zlib(level 6) of the body JSON.
  Header readable without decompression (instant save-browser listing). `body_sha256` detects
  truncation/bit-rot → auto-fallback to next-newest autosave with a notice.
- Body: `{campaign_meta, rng_streams, entities:{id:{Component:{...}}}, ledger_networks,
  event_queue_persistent, site_diffs, research, economy, ui_prefs}`. **Derived state never saved**
  (caches, class-a/b predictions recompute); pre-rolled outcomes ARE saved (fate, not derivation).
  JSON shortest-round-trip floats round-trip float64 exactly.
- Serialize ≤150 ms main thread; compress + atomic write (`tmp` + `os.replace`) in a worker.
  Migration operates on the parsed dict, never in place on disk.
- **Migration harness:** integer `schema`; `save/migrate.py` holds pure
  `migrate_N_to_N+1(body_dict) -> body_dict`, applied in sequence. Policy: migrations maintained
  for every schema shipped in a public release in the current major; newer-schema loads refuse
  with a clear message; dev saves best-effort. Reserved `"propagator":"patched_conics"` field
  from the first shipped schema (DECISIONS G35e — n-body headroom).
- **Autosave:** every 600 s wall-clock AND event-armed before node ignition / crewed SOI crossing /
  atmosphere entry / landing / undock. Rotation `auto_0..auto_9`; `milestone_*` at act
  transitions; F5/F9 quicksave/load; `crash_recovery.aph` on unhandled exception (World always
  serializable mid-frame because render never mutates).

### 3.5 Golden-save regression doctrine (§3.16-4, §6)

- Each phase ends with a recorded golden save → permanent fixture in `tests/fixtures/saves/`.
  CI loads each, advances 30 sim-days at max allowed warp, compares ~200 scalar probes
  (positions, buffer levels, crew health, money) against recorded values with per-field
  tolerances. Every public release adds a fixture and CI proves the whole migration chain loads +
  passes goldens. Phase 6 DoD: all golden saves from Phases 2–6 still load and pass.

### 3.6 Crash-triage bundle (DECISIONS G35d — Phase 2, binding)

- Crash dialog: traceback + "copy report" + **"bundle save + log + sysinfo to zip"** button for
  forum reports. No telemetry, no network — single-player offline doctrine.

### 3.7 Surface-site content contract (§3.12 — save/determinism relevant)

- Site key `(body, sector, slot)`; pinned seed derivation (sha256, NOT `hash()`); 1024×1024 tiles
  @1 m; 64×64 lazy chunks in a worker (~2 ms/chunk); binding generator: 4-octave value noise,
  λ₀=64 m, lacunarity 2.0, persistence 0.5, counter-based lattice draws (chunk-order independent),
  normalize by 1.875; obstacle iff n > 1−0.5·slope_sigma; rock p = 0.15·rock_abundance·n;
  deposit center uniform in central 512×512, grade g(d) per 04 M-1a. Persistence: sparse diffs
  only (~10–100 KB built site); pristine chunks regenerate from seed forever. ≤16 resident sites
  (LRU evict serializes diffs). Unfocused sites are pure ledger entities — a hauling rover is a
  scheduled TRANSFER_ARRIVAL, not a simulated drive.

---

## 4. BUILD ROADMAP (§6 — DoD slices are acceptance gates; all CI green implied)

| Phase | Scope | Definition of Done |
|---|---|---|
| **0 — Orbital sandbox** | Kepler/frames/SOI/event queue, SYSTEM+LOCAL layers, warp ladder, maneuver nodes, pinned tests | Fly node-planned Earth→Mars transfer reproducing 01 §3.8 within 1 % (TMI 3,591±36 m/s, 259±3 d); 60 fps with 2,000 rails objects (scene P0); determinism test green |
| **1 — Builder + launch** | Content pipeline + validator, T0 part catalog, vessel builder, staging, RK4 ascent + ascent program, physics warp, **replay/flight-recorder hook in the integrator (C21)** | 2-stage TWR-1.3 methalox reaches LEO-300 for 9,300–9,500 m/s (01 §3.10); builder fuzz suite green; pre-flight ascent sim = flight code path; recorder hook emits samples in a smoke test |
| **2 — Survival + landing + mining** | LSC (08), vacuum landing, landed state, site maps, first ISRU chain (04), **save v1 + autosave**, **crash-triage bundle button (G35d)** | Crewed Moon landing; crew survives 14-day lunar night on stored power/water; water-ice → LOX/LH2 chain runs; **golden save #1 recorded; save-migration harness in place** |
| **3 — Bases** | Ledger v1 (full §3.9), habitat construction (07), power grid (09), failure pre-rolls, INTERIOR layer | Unattended lunar propellant base runs 6 warped months; **ledger-vs-ticker equivalence < 0.1 %**; tier-7 warp holds 60 fps with 5 bases (scene P3) |
| **4 — Orbital industry** | Docking/merge (06), depots, freighters + route planner (05 §3.6), economy/contracts (12), comms graph (live from day one, C22) | LEO→LLO methalox route self-runs 1 sim-year incl. refuel/replan; 05 Pelican/Drayage examples within 2 %; comms budget confirmed vs §4.6 line (the C22 gate) |
| **5 — Full system + exotic environments** | All 03 bodies/sectors, aerocapture/EDL, radiation + SPE, Venus aerostat + Titan content, teleop latency, gravity-assist UI | Jupiter arrival via assist matching 01 §3.9 (δ=144°); Callisto-staging teleop scenario playable; Mars EDL per 01 corridor rules |
| **6 — Automation + endgame** | A3/A4 autonomy, T4 [SPECULATIVE] content, megaprojects, perf hardening, save-migration tooling, **mod docs** | "No Earth imports for 2 sim-years" Mars complex at 60 fps; interstellar-precursor launch playable; all Phase 2–6 golden saves still load and pass |

Phase↔Act: P0–P1 = Act 1; P2–P3 = Act 2; P4 = Act 3; P5 = Acts 4–5; P6 = Endgame.
DECISIONS scope notes: D26 (low-thrust spirals numeric ≤1,000× fallback; revisit Phase 4),
D27 (≤40 thermal nodes/base until Phase 5 data), C19 (demographics lands Phase 6+),
C20 (Phase 5 grows by four exotic vehicle systems — accepted knowingly).

---

## 5. GAP vs CODE (repo state, 2026-06)

### Honored by current code

- **Event queue** (`aphelion/core/events.py`): single heapq, `(t_due, seq)` total order, lazy
  generation invalidation with O(1) `bump()`, `peek_time()` clamp, deterministic `pop_due`. Solid.
- **Warp ladder** (`aphelion/core/clock.py`): rails tiers 1–7 at the binding rates, P2–P4
  substeps, event guard (`max_guarded_tier`, 5 s real margin), q/a_thrust physics-warp blocks,
  drift-free `t_anchor + n*SIM_DT` time, request-never-force API. Solid.
- **RNG** (`aphelion/core/rng.py`): PCG64 named substreams via SeedSequence + blake2b stable key
  hash (built-in `hash()` correctly avoided), stream-state save/restore. Solid.
- **ECS-lite** (`aphelion/core/ecs.py`): int ids, id 0 reserved, monotonic never-reused counter,
  insertion-ordered stores. Solid.
- **Ledger** (`aphelion/sim/ledger/network.py`): pooled buffers, monotone fixed-point solve
  (32/1e-9), exact linear advance, class-c scheduled boundaries, pre-rolled failures from named
  substream, `next_boundary_after` for the global queue, boundary-storm guard.
- **The binding ledger-vs-ticker test EXISTS** (`aphelion/tests/test_ledger.py` — <0.1 % vs 1 s
  brute force) plus ledger determinism test. P0-style perf check exists
  (`test_pinned_physics.py::test_batch_2000_objects_perf_budget`, ×3 slack). Phase-0 determinism
  (bit-identical trajectory twice) exists. Pinned-physics table largely implemented.
- **Camera choke point** (`aphelion/render/camera.py`): `world_to_screen` float64-subtract-first,
  layer z-ranges and hysteresis constants per §4.8.
- **Content pipeline** (`aphelion/content/`): pack order core-then-mods, patch-flag collision law,
  TOML+JSON, schema field checks, referential integrity, mass balance 0.5 %, SOI-vs-Laplace check.
- **Save v1**: reserved `"propagator":"patched_conics"` (G35e) committed at schema 1; rng state,
  module failure fates (`failure_t`) serialized via campaign extras — fate survives reload;
  golden1.sav fixture + load test; autosave (5 min) + quicksave/F9 in main.py.

### Violations / missing (ranked)

1. **Save file format violates §3.15**: `write_save` emits raw zlib with NO uncompressed header
   line (no magic, schema, label, playtime, `body_sha256`/`body_len`) → no fast save-browser
   listing, no corruption detection/auto-fallback, no atomic `tmp`+`os.replace`, serialize not
   split main-thread/worker.
2. **No migration harness**: `save/migrate.py` absent; `read_save` REFUSES any schema ≠ 1, and
   campaign v2 refuses v1 ("pre-fleet saves are not migratable") — directly against the §3.15
   policy and the Phase 2 DoD ("save migration harness in place"). No `tests/fixtures/saves/`
   migration-chain CI.
3. **Perf scenes P1/P3/P4/P5 missing**: only the P0 batch budget exists. No pytest-benchmark
   harness, no ×3-slack budget assertions for 600-part launch, 200-module tier-7 base, 8 burns,
   Jupiter scene; no >1.5×-median regression gate in CI.
4. **Replay/flight-recorder hook (DECISIONS C21) missing**: `sim/flight/` has no recorder/sample
   emission at event boundaries — this is a binding Phase 1 DoD item and is cheap now, expensive
   later.
5. **RKF4(5) adaptive integrator missing** (`core/math2d.py` has RK4 only): no thrust-warp
   ≤1,000× path, no 2 ms-total governor, no tol-1e-7 scratch-world prediction sharing the flight
   code path; no 8-craft NUMERIC cap machinery.
6. **solve_rates skips the SCC decomposition**: whole-network fixed point instead of Tarjan SCC
   condensation + topo order (§3.9). Converges for current sizes but unproven at 200-module
   recycling-loop bases — revisit at Phase 3 gate with scene P3.
7. **Ledger events don't flow into THE global queue**: `advance()` returns `LedgerEvent` lists
   and `next_boundary_after()` exists, but no code posts ledger boundaries as global EventRecords
   with generations — the "one queue" doctrine is only half-wired (warp guard can't see
   buffer-full events).
8. **Autosave policy partial**: single `autosave.aph` at 5 min (spec: 600 s + event-armed before
   risk events, rotation auto_0..auto_9, milestone saves, `crash_recovery.aph` crash handler).
   Crash-triage zip bundle (G35d, Phase 2) not present.
9. **Validator gaps**: no engine `thrust/(g0·isp·mdot)≈1` check, no tier-reachability warning, no
   content-hash result cache; `data/core/` has only bodies/parts/tech (no recipes/sectors/
   contracts/programs as data — recipes currently constructed in code); no mod docs; no
   launcher-style content report; no missing-id placeholder-part fallback on load.
10. **Determinism enforcement partial**: no CI import-graph test (`sim/` imports numpy only), no
    `hash()`-ban lint rule, no two-process scripted-intent bit-identical save test, no
    Neptune-fixture sub-pixel render test wired as the §3.7 tripwire.
