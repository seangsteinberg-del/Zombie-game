# 13 — Technical Architecture (Python 3.12 + pygame-ce)

Status: DRAFT v1 for design-bible integration. Owner: architecture domain.
Sibling docs: 01-orbital-mechanics.md, 02-propulsion.md, 03-solar-system.md, 04-resources-isru.md, 05-industry-logistics.md, 06-ships-stations.md, 07-bases-habitats.md, 08-life-support-crew.md, 09-power-thermal.md, 10-vehicles.md, 11-research-tech.md, 12-gameplay-economy-ui.md.

---

## 1. Overview

This document is the build specification for the engine: how a hard-realism solar-system sim with month-long transfer arcs, kilometer-scale bases, and meter-scale habitat interiors runs at 60 fps on a CPU in Python. It binds every implementation contract the sibling documents reference ("interface: 13-architecture.md") into one place.

Five architectural pillars, each elaborated in §3:

1. **Analytic-first simulation.** Anything that can be solved in closed form over an arbitrary time span *is*: orbits via universal-variable Kepler (01 §3.3), production via piecewise-linear ledgers (§3.9), environment via closed-form curves (07 §3). Numerical integration is the exception (thrust, atmosphere), never the default. This is what makes 1,000,000× time warp exact and cheap.
2. **One event queue.** Every future discontinuity — SOI crossing, buffer-full, reactor failure, SPE onset, node ignition, crop harvest — is *predicted* and posted to a single global priority queue. The warp controller, the autosave system, and the ledger all read the same queue. Nothing is discovered by polling; nothing tunnels through a warp step.
3. **Body-centric float64 everywhere; floating origin at render time.** Dynamic states live in per-SOI frames as float64; on-rails objects are stored as orbital elements (zero secular drift). The renderer subtracts the camera origin in float64 *before* any scaling or narrowing. §3.7 shows the precision numbers honestly.
4. **Data-driven content.** Every part, recipe, body, sector, tech node, and contract template is a JSON/TOML file validated against an explicit schema at load. Code knows mechanics; data knows content. Modding falls out for free.
5. **Determinism by construction.** Single-threaded sim core, fixed iteration order, named RNG substreams, pre-rolled stochastic outcomes. Same save + same inputs = same campaign, bit-exact on the same platform (§3.10).

Performance contract (binding, enforced by CI budget tests, §3.14): render target 60 fps at 1920×1080; simulation work ≤ 8 ms per frame at any warp tier; worst-case frame (warp landing + autosave) ≤ 200 ms hitch (the ≤ 150 ms main-thread autosave serialize of §3.15 plus the frame's own work), never a freeze.

---

## 2. Real-World Grounding

The realism doctrine applies to engineering decisions too — every architectural choice below has a named precedent or published basis:

- **Universal-variable Kepler propagation** — Bate/Mueller/White *Fundamentals of Astrodynamics* ch. 4, Vallado *Fundamentals of Astrodynamics and Applications* Alg. 8; the standard one-solver-for-all-conics formulation, exact to machine precision for any Δt. Specified in 01 §3.3; this doc owns the implementation and tests.
- **Fixed-timestep simulation decoupled from rendering with interpolation** — the canonical pattern (Glenn Fiedler, "Fix Your Timestep", 2004); used by essentially every physics-stable game engine.
- **Floating origin / camera-relative rendering** — Kerbal Space Program's "Krakensbane" (origin shifting at > 750 m/s) and floating-origin literature (Thorne, *Using a Floating Origin to Improve Fidelity and Performance of Large, Distributed Virtual Worlds*, 2005). Orbiter (Schweiger, 2000–2016) likewise propagates elements analytically and renders camera-relative.
- **IEEE-754 double precision** — 52-bit mantissa ⇒ relative ULP 2.22e-16. All precision claims in §3.7 are computed from this, not asserted.
- **Discrete-event simulation (DES)** — the ledger (§3.9) is a textbook event-driven piecewise-linear DES (Banks et al., *Discrete-Event System Simulation*): advance state analytically between events, process events in time order. Factorio's belt/bot optimizations and Dwarf Fortress's job scheduler are game-side precedents for "don't tick what you can solve."
- **PCG64 random generator** — O'Neill 2014, the numpy default `Generator` bit stream; statistically sound, splittable via `SeedSequence.spawn` (the named-substream determinism discipline in §3.10).
- **pygame-ce / SDL2** — pygame Community Edition ≥ 2.5 on SDL ≥ 2.30: software blitting, `Surface.convert()`, `pygame.freetype` glyph rendering. A 1920×1080×32-bit surface is 8.29 MB; one full-screen copy at ~25 GB/s memory bandwidth ≈ 0.33 ms — the arithmetic behind the layer-compositing budget in §3.13.
- **Python 3.12** — `tomllib` (stdlib, read-only TOML), `json` float serialization is shortest-round-trip (exact float64 round-trip, CPython ≥ 3.1), `zlib` releases the GIL during compression (background-thread save compression, §3.15).
- **Testing pins** — published values: Earth surface escape velocity 11,186 m/s; ISS-altitude orbital period ~92.4 min at 400 km; Earth→Mars Hohmann ~259 days / TMI ~3.59 km/s from LEO-300; Earth–Mars synodic period 779.9 d (NASA fact sheets / Vallado). Full table §4.7.

---

## 3. Game Model

### 3.1 Runtime stack and dependency policy

| Layer | Choice | Version floor | Why |
|---|---|---|---|
| Language | Python | 3.12 | project mandate; tomllib, perf improvements |
| Rendering/input/audio | pygame-ce | 2.5 | project mandate; SDL2 software rendering |
| Numerics | numpy | 1.26 | float64 batch math, PCG64, surfarray interop |
| Tests | pytest + hypothesis | any current | unit/property/fuzz testing (dev-only dep) |
| Lint/type | ruff + mypy | any current | dev-only |

**Hard rule: runtime dependencies are pygame-ce and numpy only.** No scipy (we implement the ~6 numerical routines we need: Newton, Brent, RK4, RKF4(5), Stumpff series, Lambert iteration — all specified in 01), no ECS framework, no JSON-schema library (hand-rolled validator, §3.4), no UI toolkit (custom widget framework over pygame, specified in §3.17). Rationale: install footprint, auditability of every numerical routine against the design bible, and zero dependency-rot risk for a long-lived project.

The sim core (`sim/` package) imports **numpy only** — never pygame. This is enforced by a CI import-graph test. Benefits: headless simulation for tests and the dedicated server-less "background campaign check," and a clean port path if the renderer ever changes.

### 3.2 Package / module layout

Top-level layout (full module table in §4.1):

```
aphelion/
├─ main.py                  # entry: arg parsing, profile flags, crash handler
├─ core/                    # engine-agnostic plumbing
│   ├─ clock.py             #   sim time, warp controller, accumulator loop
│   ├─ events.py            #   THE global event queue (heapq, lazy invalidation)
│   ├─ rng.py               #   seeded substream registry (PCG64)
│   ├─ ecs.py               #   entity ids, component stores, system scheduler
│   ├─ math2d.py            #   vec2 float64 ops, root finders, Stumpff, RK4/RKF45
│   ├─ units.py             #   SI constants (g0 = 9.80665, c = 299_792_458, AU)
│   └─ config.py            #   settings load/save, keybinds
├─ content/                 # data pipeline (no game logic)
│   ├─ loader.py            #   pack discovery, TOML/JSON parse, id registry
│   ├─ schema.py            #   declarative schema defs for every content type
│   └─ validate.py          #   load-time validation incl. cross-doc invariants
├─ sim/                     # ALL game state + rules; imports numpy only
│   ├─ orbits/              #   kepler.py lambert.py soi.py frames.py ephemeris.py
│   ├─ flight/              #   integrator.py forces.py ascent.py node_exec.py programs.py
│   ├─ vessels/             #   parts.py assembly.py staging.py docking.py tanks.py
│   ├─ ledger/              #   network.py rates.py predict.py  (THE warp workhorse, §3.9)
│   ├─ habitat/             #   lsc.py crew.py thermal_env.py dose.py     (07/08 models)
│   ├─ industry/            #   recipes.py modules.py mining.py routes.py (04/05 models)
│   ├─ power.py             #   grid solve (09 model)
│   ├─ sites/               #   terrain.py tiles.py construction.py       (03 §S-7c, 07)
│   ├─ comms.py             #   link graph, RTT, occlusion windows (§3.11)
│   ├─ research.py economy.py contracts.py   (11/12 models)
│   └─ world.py             #   the World aggregate: entities + queue + rng + t
├─ render/                  # pygame-facing; reads sim, never mutates it
│   ├─ camera.py            #   zoom layers, floating origin (§3.7, §3.13)
│   ├─ layers/              #   system.py local.py site.py interior.py starfield.py
│   ├─ draw_conics.py       #   numpy-sampled trajectory polylines
│   ├─ sprites.py text.py fx.py surfcache.py
├─ ui/                      # widgets, screens, builder, map UI, HUD (12 owns semantics)
├─ save/                    # serialize.py migrate.py autosave.py
├─ data/                    # content packs (core/ is the base game; mods alongside)
│   └─ core/{bodies,parts,recipes,tech,sectors,contracts,programs}/*.toml|*.json
└─ tests/                   # unit, property, golden/, perf/, fixtures/
```

Dataflow per frame: `input → ui intents → sim.step(...) → render(world, camera, alpha)`. Render and UI hold **no authoritative state** except camera and widget state; everything gameplay-visible lives in `sim.world` so saving is "serialize the World" (§3.15).

### 3.3 Entity model: ECS-lite (decision and rationale)

**Decision: ECS-lite.** Entities are opaque `int64` ids. Components are frozen-field `@dataclass` instances held in per-type stores `dict[EntityId, Component]`. Systems are plain functions run in a fixed, explicit order list (no dependency solver). There are no archetypes, no query DSL, no component bitmasks.

```python
eid = world.new_entity()
world.add(eid, OrbitState(frame=EARTH, a=6.778e6, e=0.0007, lon_peri=1.31, t_peri=...))
world.add(eid, Vessel(parts=blueprint, dry_mass_kg=..., tanks={...}))
for eid, orb in world.store(OrbitState).items():   # systems iterate stores directly
    ...
```

Rationale against the alternatives:

- **vs. deep OOP inheritance (KSP `PartModule` style):** save serialization becomes "walk the component stores and emit dataclass fields" — symmetric, schema-versionable, no `__reduce__` magic. Behavior composition (a vessel that is also a comms relay and a lab) needs no diamond inheritance.
- **vs. a real ECS library (esper, etc.):** archetype/query optimizations pay off at 10⁵–10⁶ entities with dynamic composition churn. Our entity count is **~10³** (see budget below) and composition is nearly static after creation. A library adds a dependency and an abstraction tax for zero measurable win in CPython, where `dict` iteration is already the fast path.
- **Aggregation rule (the critical scaling decision):** *parts are not entities.* A vessel is **one** entity; its ≤ 600 parts (cap per 06 §3) are rows in a plain parts list inside the `Vessel` component, with cached aggregates (wet/dry mass, per-stage Δv, thrust, tank levels, CoM offset) recomputed only on structural change (stage, dock, part failure, build). Likewise a base is one entity; its modules are rows in its ledger network (§3.9). Without this rule, 200 vessels × 600 parts = 120,000 entities would drown CPython; with it, the whole campaign is ≤ ~2,000 entities (budget table §4.6).
  - **Part-row shape (binding, save-format-relevant):** `(part_id: content id, fill: {resource: kg} — present only on tank/container parts, condition: enum OK/DEGRADED/FAILED, attach: list of (other_row_index, port_class) links)`. Part condition/failure state lives here, on the row — not in separate entities.
  - **`stage_plan`** is an ordered list of part-row-index sets (index 0 fires first); staging pops the leading set and triggers an aggregate recompute.
  - The vessel-level `tanks{resource: kg}` field (§4.3) is a **derived cache** — Σ of part fills — never independently authoritative. Per-stage Δv is computed from the tanks *reachable* by each stage's engines under 06 §3's plumbing/staging rules (06 owns reachability; this doc only caches its result).

Entity id 0 is reserved/invalid. Ids are never reused within a campaign (monotonic counter, serialized). Iteration order in every system is `sorted(store)` or insertion-ordered dict (CPython guarantees insertion order) — fixed order is a determinism requirement (§3.10).

### 3.4 Data-driven content pipeline

**Formats.** Hand-authored content is **TOML** (comments, multiline, merge-friendly diffs; parsed by stdlib `tomllib`). Machine-generated or bulk tabular content (e.g., the 165 sector records from 03, atmosphere breakpoint tables) is **JSON**. The loader accepts both extensions for every content type and normalizes to the same internal dataclasses; sibling docs that show JSON schemas (05 §3.2 recipes) are normative for field names and units. Saves are always JSON (§3.15).

**Identity and packs.** Every content item has a globally unique id `"<pack>:<name>"` (e.g. `core:raptor_vac`, `core:recipe/machine_parts_std`). Packs are directories under `data/`; load order is `core` first, then mods alphabetically; a later pack may **add** ids or **patch** existing ones (shallow key override with an explicit `"patch": true` flag — silent collisions are a load error).

**Load-time validation (fail loudly, fail early).** `content/validate.py` runs on every launch (< 200 ms for core content; results cached keyed by content-hash):

1. Schema check: required keys, types, units ranges (e.g., `isp_s ∈ (0, 20000]`, `tier ∈ {T0..T4}`).
2. Referential integrity: every id referenced (recipe module types, tech prerequisites, body parents) exists.
3. **Physics invariants from sibling docs**: recipe mass balance within 0.5 % (05 §3.2 rule); SOI table values match 01 Table 4.1 (republished data must not drift); part mass > 0; engine `thrust/(g0·isp·mdot) ≈ 1` consistency.
4. Tier/act gating sanity: no T0 part requires a T3 resource input chain (graph reachability check; warns, not errors).

A failed validation prints the file, key, expected/got, and refuses to start. Modded packs validate identically — the validator *is* the modding API contract.

Schema examples for the major content types are in §4.2.

### 3.5 Simulation core: fixed timestep, decoupled render, mode machine

The main loop is the Fiedler accumulator pattern with a warp-aware twist. Definitions: `SIM_DT = 0.02 s` (50 Hz, binding per 01 §3.5); render paced by vsync at 60 Hz (fallback `Clock.tick(60)`).

```python
REAL_DT_CLAMP = 0.25          # spiral-of-death guard, s
while running:
    real_dt = min(clock.tick_seconds(), REAL_DT_CLAMP)
    intents = ui.gather_input()

    if warp.mode == NUMERIC:                       # 1x and physics warp P2–P4
        accumulator += real_dt
        while accumulator >= SIM_DT:
            for _ in range(warp.substeps):         # 1 at 1x; 2–4 at P2–P4 (01 §3.6)
                sim.step_numeric(SIM_DT)           # RK4 craft, contact, hourly ticks due
            accumulator -= SIM_DT
        alpha = accumulator / SIM_DT               # render interpolation factor

    elif warp.mode == RAILS:                       # tiers 1–7, 5x .. 1,000,000x
        span = warp.rate * real_dt                 # desired sim seconds this frame
        t_target = world.t + span
        t_clamp  = min(t_target, events.peek_time())   # never step over an event
        sim.advance_analytic(world.t, t_clamp)     # rails eval + ledger + env curves
        if t_clamp < t_target: warp.handle_event() # event guard: step down per 01 §3.6
        alpha = 0.0                                # rails positions are exact at t

    render.frame(world, camera, alpha)
```

Rules a programmer must implement exactly:

- **Sim time `t`** is float64 seconds from epoch 2049-01-01 00:00 UTC (01 §3.1). ULP at the 50-year campaign horizon (1.58e9 s) is 2.4e-7 s — event ordering at microsecond resolution is safe. During numeric flight, drift-free time is maintained as `t = t_anchor + n_steps * SIM_DT` with an int64 step counter; `t_anchor` re-bases on every mode switch.
- **`step_numeric`** order (fixed): (1) flight programs/autopilots set throttle and gimbal commands; (2) RK4 integrate every craft in NUMERIC regime (01 §3.5 forces); (3) contact/landing resolution; (4) resource flow ticks due this step (engine propellant is integrated inside RK4 mass flow; everything else is event/hourly); (5) hourly boundary work: LSC life-support step (08 §3.0), thermal env, dose, ledger micro-advance; (6) event queue pops due events.
- **`advance_analytic(t0, t1)`** does *no per-tick work at all*: on-rails orbits are not "updated" (elements are time-parametric; positions are evaluated lazily by whoever asks — renderer, comms, SOI predictor); the ledger advances piecewise-linearly (§3.9); environment/dose/boiloff curves are closed-form evaluations at t1 minus t0 (07 §3, 02 boiloff). Cost is therefore **independent of the warp rate** — tier 7 costs the same per frame as tier 1. This is the single most important performance property of the architecture.
- **Mode transitions**: NUMERIC→RAILS requires thrust = 0, outside atmosphere, not landed → refit conic elements (01 §3.5) and drop the Cartesian state. RAILS→NUMERIC at event boundaries only (node ignition −10 s, atmosphere interface, SOI crossing handled in-rails). The warp controller owns transitions; gameplay code requests, never forces.
- **Interpolated rendering**: only NUMERIC-regime craft need `alpha` interpolation (two stored states); rails objects are evaluated exactly at render time `t` — no interpolation, no extrapolation artifacts.
- **Pause** is a real mode: sim time frozen, UI/planning fully live (node editing while paused is a core UX per 12).

### 3.6 Propagators: batched Kepler on rails; RK4 under force

**On rails (the default).** Implementation of 01 §3.3 universal-variable propagator, float64, with the series-expanded Stumpff guard at |z| < 1e-6 and bisection fallback. Two call shapes:

1. `propagate(elements, t) -> (r_vec, v_vec)` — scalar, used by gameplay queries.
2. `propagate_batch(elements_soa, t) -> (N,4) float64 array` — numpy structure-of-arrays over **all** rails objects in a frame; the Newton iteration runs vectorized with a convergence mask (typ. 3–5 iterations). Budget: 2,000 objects in < 0.5 ms (§4.6). Used by the renderer, the comms graph, and the SOI predictor each frame.

Planets and moons are permanently on rails from their 03 epoch elements (`ephemeris.py` caches per-frame body positions once per render frame — every consumer reads the cache, nothing recomputes).

**Under force.** RK4, fixed `dt = SIM_DT = 0.02 s` at 1×, per 01 §3.5: gravity from the current SOI body only + thrust + atmospheric drag/lift below the interface altitude. Mass flow integrated inside the state vector (5-state: x, y, vx, vy, m). Thrust warp (≤ 1,000× while burning, 01 §3.6) uses RKF4(5) adaptive steps, relative tolerance 1e-9, dt additionally capped so `a_thrust·dt ≤ 1 m/s`, with a CPU budget of **2 ms/frame TOTAL across all NUMERIC craft** (the binding §4.6 line; per-craft share = 2.0/N ms when N craft burn simultaneously) — the warp controller lowers the rate when the *total* `measured_ms > 2.0` for 30 consecutive frames.

**Trajectory prediction** (node planner, ascent sim per 06 §5): same RKF4(5) code path with coarser tolerance (1e-7) running in a *scratch world* — prediction never mutates live state, and the builder's pre-flight ascent sim is literally `sim.flight` invoked headless (06's "same code path" requirement).

**Concurrent numeric craft cap: 8.** A 9th craft requesting NUMERIC (e.g., station-keeping burns scheduled together) is queued; its burn slips by seconds and the player is notified. Keeps worst-case physics cost bounded: 8 craft × ~0.06 ms/step × (50/60) steps/frame ≈ **0.4 ms/frame at 1×**, ≈ **1.6 ms/frame at P4 physics warp** (4 substeps) — consistent with the 2.0 ms line in §4.6 (measured target).

### 3.7 Coordinate frames, precision analysis, floating origin

**Storage (per 01 §3.1/8.4, restated as the implementation contract):** every dynamic state is body-centric float64 in its SOI frame; rails objects store elements `(μ, a or α, e, ϖ, τ, s)`; the SOI tree (Sun → planets → moons) is the only path to "absolute" positions, composed on demand.

**The honest precision numbers** (float64: 52-bit mantissa; float32: 23-bit):

| Quantity | Magnitude | float64 ULP | float32 ULP | Verdict |
|---|---|---|---|---|
| Heliocentric position at 1 AU | 1.496e11 m | 3.1e-5 m (31 µm) | 16,384 m | f64 fine; f32 fails by 4 orders |
| Heliocentric position at Neptune (30 AU) | 4.5e12 m | 9.8e-4 m (~1 mm) | 524,288 m | f64 fine for *position*; f32 catastrophic |
| Heliocentric position at Pluto (39.5 AU) | 5.9e12 m | ~1 mm | 524 km | same |
| Neptune-centric position at SOI edge | 8.66e10 m | 1.6e-5 m | 8,192 m | body-centric f64: micron-class |
| Sim time at year 50 | 1.58e9 s | 2.4e-7 s | 128 s | f64 time mandatory (f32 would skip frames) |

So: **float64 heliocentric positions are sufficient for simulation** — ~1 mm representational error at Neptune is far below gameplay relevance. Why we *still* mandate body-centric frames + floating origin, honestly argued:

1. **Zero-drift storage.** Elements `(a, e, ϖ, τ)` are time-parametric — a craft parked for 30 game-years has *exactly* the same orbit, no accumulated rounding from repeated adds. Cartesian storage, even f64, random-walks at the ULP scale per operation (√N growth; ~10⁶ ops → meter-class wander at 30 AU). Elements make the question moot.
2. **Patched conics is body-centric math anyway.** Gravity, SOI tests, and element fits all need body-relative vectors; storing them body-centric avoids a large-minus-large subtraction (4.5e12 − 4.5e12 to get a 1e7 m local offset) in the hottest code.
3. **The render pipeline narrows.** numpy batch vertex arrays for polylines/starfields use float32 for speed (half the memory bandwidth), and SDL's internal geometry is C `int`/`float` (32-bit). Any world-scale value entering those paths jitters by *hundreds of kilometers* at Neptune (table above). Therefore the **floating-origin rule**: `screen = (p_frame − cam_frame) · zoom · flip + center`, with the subtraction performed **first, in float64, in the camera's SOI frame**; only the resulting camera-local values (small numbers) may be narrowed.
   - Residual error after correct ordering: ~1 mm relative position error × 128 px/m max interior zoom (§4.8 INTERIOR ceiling) = **0.13 px** worst case at Neptune — still sub-pixel, invisible. Done in the wrong order (scale-then-subtract in float32), the error is 524 km × 128 px/m — the classic "shaking spacecraft" bug. The ordering is enforced by a single choke-point function `camera.world_to_screen()`; layers are forbidden to roll their own transform (code-review rule + unit test that feeds a Neptune-orbit fixture and asserts residual < 0.5 px).
4. **SDL integer coordinates.** pygame draw calls truncate to C int (±2.1e9). A polyline endpoint at solar zoom can be 1e14 px away → overflow/wrap. Rule: clip every primitive in float64 camera space to the viewport + 8,192 px guard band *before* int conversion (`render/draw_conics.py` owns the Cohen–Sutherland clip).

**Frame composition:** `abs_pos(entity, t) = Σ body_pos(frame_chain, t) + local_pos` — at most 3 hops (Sun→planet→moon→craft). The camera stores `(frame_id, focus_entity | fixed_point)`; when the focused craft changes SOI, the camera re-anchors in the same render frame (one-frame transform swap, no visual pop because the subtraction is exact at the crossing point by construction).

### 3.8 SOI transitions and the global event queue

**Event queue.** One `heapq` of `(t_due: float64, seq: int, EventRecord)`. `seq` is a monotonically increasing tiebreaker → total deterministic order. Cancellation is **lazy**: records carry a `generation` int checked against their source's current generation on pop; stale events are discarded silently. Sources re-post on invalidation (e.g., a burn changes the orbit → all of that craft's predicted events are stale via one generation bump — O(1) invalidation).

Event taxonomy and the full catalog (≈ 40 types) are in §4.4. The three contracts every system obeys:

1. **Predict, don't poll.** A system that knows its next discontinuity (tank empty at current rates; SOI crossing on current conic; SPE end) must post it when the prediction becomes valid, and bump its generation when inputs change.
2. **Events are exact clamps.** The warp loop never advances past `peek_time()` (§3.5). There is no "check if we missed it" code path anywhere — by construction nothing is missed (01 §8.3 tunneling fix).
3. **Handlers are bounded.** An event handler may mutate state, post new events, and request a warp change; it may not advance time. Cost budget 0.5 ms typical; long work (e.g., ledger rate re-solve) is allowed because events are rare (tens per sim-day).

**SOI transition (implementation of 01 §3.4):** on-rails crossings are predicted by coarse sampling + Brent refinement to ±1 s, posted as `SOI_CROSS` events. Sampling span: for elliptic craft conics (e < 1), step = `min(T_craft, T_body)/64`. For e ≥ 1 (hyperbolic/parabolic — the common case for escapes and flybys, where `T_craft` does not exist), the span is the analytic time-to-SOI-boundary on the current conic: solve `r(ν) = r_SOI` for the true anomaly, convert to time via the hyperbolic Kepler equation, and sample that span at span/64 (step additionally capped at `T_body/64`); if the conic never reaches `r_SOI`, no event is posted. The handler: sample both states at `t_cross`, subtract body position/velocity (entering) or add (exiting), refit elements in the new frame, bump the craft's prediction generation, re-anchor the camera if focused. Hysteresis (exit > 1.01·r_SOI, entry < 0.99·r_SOI) and the 60 s re-entry lockout (01 §8.2) live in the predictor, so the queue never sees thrash. NUMERIC-regime craft instead check the SOI radius each RK4 step (cheap: one distance per body in the candidate set — parent, children of parent within 2× SOI).

### 3.9 The time-warp ladder and the LEDGER (the critical subsystem)

The warp ladder itself (tiers, rates, guards) is owned by 01 §3.6/4.6; this section specifies **what executes** at each rung and the ledger algorithm precisely.

| Rung | Craft | Bases/factories/life support | Environment |
|---|---|---|---|
| 1× / physics warp | RK4 (§3.6) | LEDGER, advanced in ≤ 1 h segments at hourly boundaries | closed-form eval |
| Rails tiers 1–7 | analytic Kepler eval, no per-tick work | LEDGER, advanced in one call per frame over the frame's sim span | closed-form eval |

**Design decision: the ledger is not a "warp mode" — it is the *only* model for production, life support stores, and power balance at every time rate.** At 1× it advances in small spans; at tier 7 in ~4.6 h spans per frame (1,000,000× / 60 fps = 16,667 s ≈ 4.63 h). One code path = no 1×-vs-warp divergence bugs by construction (the classic colony-sim failure). The independent reference for testing is a brute-force 1 s ticker that exists *only* in the test suite (§3.16).

**Ledger model.** Per site (base, station, or vessel interior) a `LedgerNetwork`:

- **Buffers** `b_i`: level `L_i` (kg, or kWh for batteries, or crew-h for labor pools), capacity `C_i ≥ L_i ≥ 0`. Tanks, hoppers, LSC gas masses (08), battery banks (09).
  - **Topology rule (binding):** all storage of one resource within a LedgerNetwork pools into **one logical buffer per resource** — `L = Σ levels`, `C = Σ capacities` of the contributing tanks/hoppers; physical placement within the site is 07's layout concern and does not affect flow rates. The network's "links" (§4.3 `LedgerHost`) are therefore *not* pipes: they are the module↔resource adjacency derived mechanically from each module's recipe inputs/outputs. Every `solve_rates` empty/full test below refers to the pooled buffer. (If 05's network schema ever introduces explicit buffer-to-module pipes, that section becomes normative and replaces this pooling rule; until then, pooling is the rule.)
- **Transformers** `m_j`: recipe-driven modules (05 §3.2): nominal rate `R_j` (kg/s of primary output), input/output stoichiometry vectors, state machine `OFF/STARTING/RUNNING/STARVED/BLOCKED/DEGRADED/FAILED/MAINTENANCE` (05 §3.2), modifiers `f_power, f_labor, f_condition, Y` (05 F-1).
- **Sources/sinks**: deposits with remaining mass (04), crew metabolic flows (08 §3.1), solar/reactor power vs. demand (09), documented vents.

All flows are **piecewise-constant rates** between events — guaranteed by the sibling docs' "analytic integration" contracts (04 §1, 05 §3.2, 07 §3, 08 §3.0). The ledger is therefore exact, not approximate.

**Algorithm `ledger_advance(net, t0, t1)`:**

```
t ← t0
while t < t1:
    # 1. RATE SOLVE: piecewise-constant rates valid until the next boundary
    rates ← solve_rates(net, t)            # see below
    # 2. NEXT BOUNDARY: earliest of
    #    a. buffer hit:   for each buffer, Δt_i = (C_i − L_i)/ṅ_i if ṅ_i>0,
    #                                       L_i/(−ṅ_i) if ṅ_i<0   (ṅ = net rate)
    #    b. deposit exhaustion: remaining / extraction_rate
    #    c. scheduled: warmup complete, batch/build complete, crew shift change,
    #       pre-rolled failure time (§3.10), maintenance done, eclipse entry/exit (09),
    #       day/night terminator (07), arrival of a logistics transfer (05)
    t_next ← min(t1, t + min over a/b/c)
    # 3. INTEGRATE: exact linear update
    for each buffer: L_i += ṅ_i · (t_next − t)         # clamp |L−bound|<1e-9 to bound
    deposit.remaining −= rate · (t_next − t)
    t ← t_next
    # 4. EVENT: if t < t1, apply the boundary (state machine transition, vent, alarm),
    #    bump generations, and loop (rates re-solved only for the affected subgraph)
post_to_global_queue(next boundary after t1)            # so the warp guard sees it
```

**`solve_rates` (the only subtle part).** Module rate = `R_nom·f_power·f_labor·f_condition·Y`, *throttled* by supply: if an input buffer is empty, the module runs at the rate its input arrives: `R_j ← min(R_j, inflow_i / stoich_ij)` over empty inputs `i`; if an output buffer is full, `R_j ← min(R_j, drain_o / stoich_oj)` (05's STARVED/BLOCKED states). Power couples globally: `f_power = clamp(P_supplied/P_required)` with `P_supplied` from the 09 grid solve, which itself depends on module duty — a monotone coupled system. Solution: Tarjan SCC condensation of the flow graph; topological order between SCCs; within an SCC, fixed-point iteration of the throttle map (monotone non-increasing from the unthrottled point ⇒ converges; cap 32 iterations, tolerance 1e-9 kg/s; non-convergence → freeze rates at last iterate + log a sim-warning — never an infinite loop). Typical base: < 60 modules, 1–3 small SCCs (recycling loops), solve < 0.3 ms.

**Complexity & budget:** O(events × affected-subgraph). A 200-module base generates ~20–80 boundaries/sim-day. Worst case (tier 7 ≈ 4.6 h sim per frame at 60 fps, i.e. 0.193 sim-day/frame): ~4–15 boundaries/frame/base (80 × 4.63/24 ≈ 15.4 at the busy end) — which still fits ⇒ budget **3 ms/frame for all ledgers combined** (§4.6); the warp controller degrades tier 7→6 if exceeded (same pattern as thrust-warp budget). A "catch-up" call after loading a save mid-transfer (advance 100 days for 10 sites) completes in < 250 ms behind a loading spinner.

**Failure rolls under warp** (02's binding "deterministic RNG" requirement): when a module enters RUNNING, pre-sample its time-to-failure from `Exponential(MTBF)` (MTBF from 05 §3.10 wear model — sampled against *wear units*, converted to time at current throughput; re-sampled when throughput changes by > 10 %, consuming from the module's named substream §3.10). The sampled failure instant is a class-c scheduled boundary. Result: failures land at the same sim time whether the player warps through the month or plays it at 1× — warp is never a way to dodge (or farm) risk.

**LSC coupling:** 08's "per sim hour" integration is implemented as class-c boundaries at hour marks *only when nonlinear effects are armed* (partial-pressure threshold crossings, CO2 curves); otherwise LSC gas masses are ordinary ledger buffers with crew metabolic rates and the next threshold crossing (e.g., ppO2 < 16 kPa) predicted analytically and posted — so a 6-year Saturn cruise with a stable loop costs ~zero CPU, but a degrading loop wakes the sim exactly when it should.

### 3.10 Determinism and RNG discipline

- **Single-threaded sim.** All mutation on the main thread. Worker threads exist only for: zlib save compression, terrain chunk generation (pure function of seed → handed back whole), and audio. None touch `World`.
- **Fixed iteration order** everywhere (sorted ids / insertion order); the event queue's `seq` tiebreaker makes same-timestamp processing deterministic.
- **RNG registry** (`core/rng.py`): campaign seed (uint64, shown to player) → `numpy.random.SeedSequence` → named substreams spawned per domain and entity: `rng("failures", module_uid)`, `rng("terrain", body, sector, slot)`, `rng("solar", )`, `rng("contracts", )`… Streams are independent: burning terrain randomness never shifts failure outcomes. Stream states serialize into saves. **Python's built-in `hash()` is forbidden in `sim/` code** (per-process SipHash salting makes it non-deterministic across runs); any stable key→seed hashing uses `hashlib` (e.g., the §3.12 terrain seed) — enforced by a lint rule alongside the import-graph test.
- **Pre-rolled outcomes** (failure times §3.9, SPE schedule per 03 §S-8b Poisson process — next-event times stored): reloading a save and taking a different route does not reroll fate that was already drawn; drawing happens at well-defined trigger points.
- **Cross-platform honesty:** PCG64 streams are bit-identical everywhere; float64 arithmetic is IEEE-deterministic for + − × ÷ √, but `sin/cos/exp` last-ULP results can differ across libm versions. Therefore: **same platform ⇒ bit-exact reproducibility** (CI-tested); across platforms a loaded save is valid but trajectories may diverge at the 1e-15 relative level over time. Saves are **state snapshots, never input replays**, so this costs nothing gameplay-visible. We do not chase cross-platform bit-exactness (that would require a fixed-point or software-float core — not worth it for a single-player game).
- **The sim never reads wall-clock time, locale, or filesystem order.** Autosave timing is the only wall-clock consumer and lives outside `sim/`.

### 3.11 Comms and remote-ops model (owned here; consumed by 05 F-2, 07)

- **Nodes:** every entity with a powered comms part (antenna stats — range class, power draw — owned by 06/07 part catalogs) plus the Earth Deep Space Network root node (always on, id `core:dsn`).
- **Link rule [GAME MODEL]:** nodes a, b link if (1) 2D line-of-sight — segment vs. body discs (radius + atmosphere interface) for all bodies in the SOI chain between them; and (2) `d ≤ √(R_a · R_b)` where `R_x` is the antenna's rated range (root-product pairing rule; anchor: KSP CommNet's published model — an honest game abstraction standing in for real link budgets, tagged as such).
- **Latency:** one-way light time `τ = path_length / c`, `c = 299,792,458 m/s`; RTT = 2τ summed along the relay path (relays are store-and-forward with negligible processing delay at game fidelity). RTT feeds 05's teleoperation productivity F-2 and 07's remote-ops gating. Checks: Earth–Moon RTT 2.56 s; Earth–Mars best RTT 6.1 min at 0.37 AU closest approach — matches 05's table.
- **Connectivity solve:** graph rebuild is event-driven — on topology change (new node, node unpowered, SOI change) and otherwise every 60 s sim; per-route **occlusion windows** (body eclipses a link, e.g., farside passes) are predicted from the conics by the same Brent machinery as SOI crossings and posted to the event queue, so a teleoperated mining shift pauses *exactly* when the relay sets, even at tier 6 warp.
- **Routing:** shortest-RTT path by Dijkstra over ≤ 300 nodes — microseconds, rebuilt with the graph.

### 3.12 Surface site maps (procedural tile engine — 03 §S-7c contract)

- **Instantiation:** landing in a sector creates a persistent site keyed `(body, sector, slot)`; seed derivation (binding): `seed = int.from_bytes(hashlib.sha256(f"{body}:{sector}:{slot}".encode("utf-8")).digest()[:8], "little") ^ campaign_seed`, fed to `numpy.random.SeedSequence(seed)` as the `rng("terrain", body, sector, slot)` substream. Python's built-in `hash()` is **forbidden** here and everywhere in `sim/`: it is SipHash keyed randomly per process (`PYTHONHASHSEED`), so pristine chunks would regenerate differently on every run — a silent violation of §3.10 and of the persistence model below.
- **Geometry:** square tile grid, **1 m/tile, 1024×1024 tiles** (1.02 × 1.02 km) per site. Generation is chunked (64×64 tiles), lazy, in a worker thread (pure seed → array function), ~2 ms/chunk.
- **Generator (binding — two implementations of this paragraph must produce identical sites):** layered value noise (numpy), 4 octaves, base wavelength λ₀ = 64 m, lacunarity 2.0 (octave *i* wavelength = 64/2^i m), persistence 0.5 (octave *i* amplitude = 0.5^i). Lattice values are drawn from the site substream indexed by `(octave, lattice_i, lattice_j)` (counter-based draws, so any chunk is generable independently of generation order); bilinear interpolation between lattice points; the octave sum is normalized to `n(x,y) ∈ [0,1]` by dividing by Σ amplitudes = 1.875.
  - **Obstacle classification:** a tile is OBSTACLE (untraversable/unbuildable until graded, 07/10) iff `n(x,y) > 1 − k·slope_sigma`, with **k = 0.5** and `slope_sigma ∈ [0,1]` from the 03 §S-7a sector record — expected obstacle fraction ≈ k·slope_sigma.
  - **Rock spawn:** per-tile Bernoulli on non-obstacle tiles in fixed row-major order, `p_rock = c·rock_abundance·n(x,y)` with **c = 0.15** and `rock_abundance ∈ [0,1]` from the sector record.
  - **Deposit overlay:** each deposit rolled for the sector (04 M-1) gets a center tile drawn uniformly from the site's central 512×512 region; every tile's ore grade = `g(d)` evaluated at d = Euclidean distance (m) from that center per 04 M-1a, stored as a lazily-sampled float32 grade field per chunk. Mining (04) reads grade at the miner's tile.
  - Anomaly tiles if rolled (03). The constants k and c are tuning values pinned here; 03 §S-7c may override them per body class, in which case 03's table is normative.
- **Persistence:** only diffs are saved — sparse `{(x,y): tile_state}` for mined/graded/built tiles, plus placed-structure records (07 schemas). Pristine chunks regenerate from seed forever; a heavily built site costs ~10–100 KB in the save.
- **Sim on sites:** vehicles (10) and construction (07) run only at 1×/physics warp while the site is *focused*; unfocused sites are pure ledger entities (§3.9) — a rover ordered to haul ore becomes a scheduled transfer event, not a simulated drive (05's logistics abstraction).
- **Cap:** ≤ 16 instantiated sites resident in memory (LRU; eviction serializes diffs); no gameplay limit on total sites.

### 3.13 Rendering architecture: zoom layers, caching, the dirty-rect decision

**Zoom-layer cameras.** Continuous exponential zoom `z` (px/m), mouse-wheel steps ×1.25, spanning ~12 orders of magnitude in four layers with hysteretic handoffs (table §4.8): SYSTEM (heliocentric schematic; 1.6e-10 px/m shows 80 AU across 1920 px), LOCAL (SOI frame; bodies, orbits, vessels), SITE (tile map), INTERIOR (habitat cells from 07/08). Layers share the §3.7 transform choke point; handoff is a frame-anchored crossfade over 150 ms.

**Full redraw, not dirty rects — the analysis.** Dirty-rect rendering wins when most pixels are static. Our world view pans/zooms or has moving orbit lines virtually every frame, so the world layer would be 100 % dirty anyway. Decision: **full redraw every frame of the world layer; per-element caching above it**:

- **Layer surfaces** composited per frame: starfield (regenerated only on camera move > threshold; else blitted, 0.33 ms) → world vector layer (orbits, bodies, sprites; drawn fresh) → HUD/UI layer (widgets cached as sub-surfaces, redrawn only on state change — *here* dirty-rect logic lives, where it pays; widget model in §3.17).
- **Conic polylines:** each visible orbit sampled at ≤ 256 points (01 §7 contract) by *batched* true-anomaly sampling in numpy (one vectorized eval per conic), clipped (§3.7), drawn with `pygame.draw.aalines`. Budget 200 visible conics × ~25 µs = 5 ms worst case → LOD rule: orbits subtending < 8 px render as 2-point ticks; < 2 px cull. Typical scene: 30–60 conics, ~1.5 ms.
- **Text:** `pygame.freetype` with two caches — glyph atlas per (font, size), and an LRU of 4,096 rendered strings keyed `(text, font, size, color)`. Numeric readouts (altimeter, Δv) change every frame ⇒ rendered glyph-by-glyph from the atlas (no per-frame `Font.render` allocations). Rule: **no `render()` call for a string already on screen last frame.**
- **Sprites/parts:** vessels beyond 64 px render as cached whole-vessel surfaces (re-rasterized on zoom band change — zoom bands quantized ×1.6 so cache churn is bounded); under 64 px, as icons. Site chunks pre-rasterized to 64×64-tile chunk surfaces per zoom band, LRU 256.
- **Particles/FX** (engine plumes, dust, RCS puffs): numpy position/velocity/age arrays (SoA), vectorized update, rendered as additive-blended micro-sprite blits; cap 4,000 live particles; FX never allocate per frame.
- **Display:** `set_mode((1920,1080), SCALED | DOUBLEBUF, vsync=1)`; if vsync unavailable, `Clock.tick(60)`. UI scales by integer factors for other resolutions (vector art tolerates this cleanly).

**Render budget: ≤ 7 ms/frame** at 1080p (breakdown §4.6) — pessimistic software-blit arithmetic: ~4 full-frame-equivalent composites ≈ 1.3 ms + vector/text/sprite work.

### 3.14 Performance budget and strategy

Frame budget at 60 fps = 16.7 ms; the binding split is **sim ≤ 8 ms, render ≤ 7 ms, input/UI ≤ 1 ms, headroom ≥ 0.7 ms** (full table with per-subsystem lines: §4.6). Strategy, in priority order:

1. **Don't compute** — analytic-first (§3.5/§3.9): cost independent of warp rate; lazily evaluated rails positions; event-driven everything.
2. **Vectorize what remains** — numpy batch Kepler (§3.6), conic sampling, particles, terrain gen, dose/thermal curve evaluation over entity arrays. Rule of thumb enforced in review: any per-frame Python loop over > 100 items must have a numpy justification comment or be vectorized.
3. **Cache aggressively** — body ephemeris per frame; vessel aggregates on structural change; rendered text/sprites/chunks (§3.13); comms graph (§3.11).
4. **Partition space** — the SOI tree *is* the broad phase for orbit-space queries (proximity alarms, docking: only craft sharing a frame are compared, sorted-by-x sweep within 100 km bands). Site maps use the tile grid itself (uniform hash) for vehicle/structure queries. No quadtrees needed at our densities.
5. **Degrade gracefully, visibly** — soft-budget governors: thrust-warp rate reduction (01's 2 ms rule), ledger tier step-down (§3.9), particle cap, conic LOD. Every governor logs to the perf HUD; nothing silently stutters.

**Profiling plan (a process, not a wish):**
- Perf HUD (F3): per-subsystem ms bars (sim/ledger/render/UI), 240-frame history graph, entity/event/cache counters, governor status.
- `--profile` flag wraps the loop in `cProfile` and dumps on exit; pyinstrument for sampled flame graphs in dev; py-spy for attaching to live/shipped builds (no code change needed).
- CI perf tests (pytest-benchmark): 5 reference scenes (§3.16) asserting budgets ×3 slack for CI-runner noise; a regression > 1.5× median fails the build.
- Optimization is forbidden without a profile capture attached to the PR (repo policy) — CPython hot spots are reliably surprising.

### 3.15 Save system

**Format — one file `<name>.aph`:**
```
line 1 (uncompressed UTF-8 JSON + '\n'):
  {"magic":"APHSAVE","schema":7,"game_version":"0.4.2","t_sim":1.6213e8,
   "label":"Mars window 3","playtime_s":214511,"focus":"vessel:412",
   "body_sha256":"...","body_len":31415926}
rest: zlib(level 6) of the body JSON
```
Header is readable without decompression (save-browser UI lists metadata fast). Body: `{campaign_meta, rng_streams, entities:{id:{ComponentName:{...}}}, ledger_networks, event_queue_persistent, site_diffs, research, economy, ui_prefs}`. **Derived state is never saved** (caches, predicted events — the prediction classes a/b in §3.9 and SOI predictions are recomputed on load; *pre-rolled outcomes* — failure times, SPE schedule — ARE saved because they are fate, not derivation).

- **Floats:** Python `json` emits shortest-round-trip representations ⇒ float64 state round-trips exactly. No binary float hacks needed.
- **Size & speed targets:** late-game body ~10–40 MB raw JSON, ~1–5 MB compressed; serialize ≤ 150 ms on the main thread (hitch acceptable at autosave points, which are chosen at calm moments; together with the frame's own work this fits the §1 ≤ 200 ms worst-case-frame contract, and the CI perf assertion tests the combined autosave frame against 200 ms), compress + atomic write (`tmp` + `os.replace`) in a worker thread.
- **Autosave:** every 600 s wall-clock *and* event-armed before: node ignition, SOI crossing of a crewed craft, atmosphere entry, landing/undock. Rotation: `auto_0..auto_9`; separate `milestone_*` saves at campaign-act transitions; quicksave/quickload on F5/F9. Crash handler writes `crash_recovery.aph` on unhandled exception (the World is always serializable mid-frame because render never mutates it).
- **Versioning & migration policy:** integer `schema`, bumped on any breaking shape change. `save/migrate.py` holds pure functions `migrate_6_to_7(body_dict) -> body_dict`, applied in sequence. Policy: migrations are maintained for **every save schema that shipped in a public release within the current major version**; loading a newer schema than the engine refuses with a clear message; loading pre-release dev saves is best-effort. Every public release adds a fixture save to `tests/fixtures/saves/` and CI proves the whole migration chain still loads and passes the golden checks (§3.16). Headroom per 01 §9-Q8: schema reserves a `"propagator":"patched_conics"` field so a hypothetical future n-body mode is a schema evolution, not a format break.

### 3.16 Testing strategy and CI

1. **Pinned-value physics tests** (`tests/physics/`): the §4.7 table, each row one test, asserting against published/derived values to the stated tolerance. These are the project's realism contract in executable form.
2. **Property tests** (hypothesis): Kepler `propagate(Δt)` then `propagate(−Δt)` returns within 1e-6 m over random conics (e ∈ [0, 5], all quadrants); elements↔state round-trip; propagator self-consistency `propagate(t1+t2) == propagate(t1) ∘ propagate(t2)` within 1e-6 m; RK4 coast (thrust 0, no atmosphere) vs. Kepler < 1 m drift over one orbit; ledger conservation — Σ(mass in buffers + deposits + vented) constant within 1e-9 kg over random networks and spans.
3. **Ledger equivalence**: `ledger_advance(t0, t0+30 d)` vs. the test-only 1 s brute-force ticker on randomized bases — every buffer within max(0.1 %, 1 kg). This test *is* the warp-correctness guarantee.
4. **Golden-save regression**: canonical saves (one per campaign act) loaded, advanced 30 sim-days at max allowed warp, then ~200 scalar probes (positions, buffer levels, crew health, money) compared to recorded values with per-field tolerances. Catches "refactor changed the campaign" bugs that unit tests cannot.
5. **Determinism test**: same save + scripted input sequence run twice in one process and across two processes ⇒ bit-identical end-state serialization (same platform).
6. **Builder fuzzing** (hypothesis): random part graphs within builder rules (06) ⇒ loader/assembly never raises; aggregates finite and non-negative; staging order valid; Δv readout matches hand Tsiolkovsky; save→load→save byte-identical.
7. **Perf scenes** (pytest-benchmark, §3.14): P0 "2,000 rails objects", P1 "600-part launch", P3 "200-module base at tier 7", P4 "8 simultaneous burns", P5 "Jupiter system, 60 conics + comms".
8. **CI** (GitHub Actions): Ubuntu + Windows, Python 3.12, `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy` for headless pygame; jobs: ruff → mypy (strict on `sim/`, `core/`, `save/`) → pytest (coverage gate 80 % on `sim/`) → perf scenes (×3 slack) → content validation of `data/core`. The import-graph test (§3.1: `sim/` imports numpy only) runs here.

### 3.17 UI widget framework (the contract 12 builds against)

"No UI toolkit" (§3.1) obliges this doc to specify the one we hand-roll — 12-gameplay-economy-ui.md's every screen is built against this section. Binding decisions for `ui/`:

- **Retained-mode widget tree.** One root per screen; widgets are plain Python objects with `children[]`, persisting across frames. Immediate-mode is rejected: it re-does layout and text every frame, fighting the §3.13 caching strategy and the "no `render()` for an unchanged string" rule.
- **Layout: single top-down pass per dirty subtree.** Each widget declares `anchor` (parent-relative: one of 9 anchor points or fractional offsets), a `size` rule (`fixed px | fit-content | fill-fraction`), and `padding`/`gap` on the two container types (VBox, HBox). No constraint solver — nested boxes cover every screen in 12's designs. Layout reruns only on a layout-dirty mark (resize, content change, child add/remove).
- **Event routing.** Mouse: hit-test from root downward (capture); the deepest hit widget handles first; unhandled events bubble back toward the root. Keyboard: an explicit focus chain (Tab order = tree order; focused widget draws a focus ring). **Modal stack:** a pushed modal (dialog, builder overlay, save browser) owns all input until popped; global hotkeys (warp ladder, F3, F5/F9) bypass widgets only when no modal is up and no text field holds focus.
- **Drawing = the §3.13 HUD dirty-rect layer.** Each widget owns a cached sub-surface and a render-dirty flag: state change → mark dirty → re-render the sub-surface once → parent composites. Per-frame numeric readouts (altimeter, Δv) bypass widget dirtying entirely and draw via the §3.13 glyph-atlas fast path.
- **Minimum widget set (v1):** Label, Button, Toggle, Slider, TextField, List (virtualized — only visible rows instantiate), Table, TabBar, Window (draggable, z-ordered within the non-modal band), Tooltip (hover-delayed, follows the §3.13 text cache), ProgressBar, Graph (numpy polyline; perf HUD and ledger plots). New widget types require an update to this list.
- **Sim boundary: intents, never calls.** Widgets never import or mutate `sim/`. Interaction emits **intent objects** — frozen dataclasses such as `SetThrottle(craft_eid, 0.7)`, `CreateNode(craft_eid, t, dv_vec)`, `QueueResearch(tech_id)`, `PlaceModule(site_key, tile, part_id)` — collected by `ui.gather_input()` and applied at the next sim step boundary (the §3.5 dataflow). This keeps render-never-mutates airtight and makes the scripted-input determinism test (§3.16-5) a matter of replaying an intent list.

---

## 4. Content Catalog

### 4.1 Module table (binding layout)

| Package.module | Owns | Key sibling contract |
|---|---|---|
| core.clock | sim time, accumulator, warp controller + governors | 01 §3.6 ladder & guards |
| core.events | global heap, generations, event taxonomy | 01 §3.4; 04/05/07 schedulers |
| core.rng | seed registry, named substreams | 02 deterministic failures |
| core.ecs | entity ids, stores, system order | — |
| core.math2d | vec2, Stumpff, Newton/Brent, RK4/RKF45 | 01 §3.3/3.5 |
| content.* | pack loading, schemas, validation | 05 §3.2 recipe schema, etc. |
| sim.orbits.kepler | universal-variable propagator, scalar + batch | 01 §3.3 (binding) |
| sim.orbits.lambert | 2D Lambert, window scan | 01 §3.8 |
| sim.orbits.soi | SOI tree, crossing prediction, hysteresis | 01 §3.4 |
| sim.orbits.ephemeris | per-frame body position cache | 03 elements |
| sim.flight.integrator | RK4/RKF45 powered & atmospheric flight | 01 §3.5 |
| sim.flight.programs | flight computer programs | 01 Table 4.7; 02 control alloc |
| sim.vessels.* | parts, aggregates, staging, docking merge | 06 §3 (600-part cap, port rules) |
| sim.ledger.* | LedgerNetwork, rate solve, boundary prediction | 04/05/07/08/09 analytic contracts |
| sim.habitat.* | LSC, crew, dose, environment curves | 08 §3.0, 07 §3, 03 §S-8 |
| sim.industry.* | recipes, mining, route planner events | 05 §3.6 route algorithm |
| sim.power | grid solve feeding f_power | 09 |
| sim.sites.* | tile terrain, diffs, construction | 03 §S-7c, 07 |
| sim.comms | link graph, RTT, occlusion windows | 05 F-2, 07 remote ops |
| sim.research / economy / contracts | tech tree state, money, contracts | 11, 12 |
| sim.world | World aggregate, step orchestration | — |
| render.camera | zoom layers, world_to_screen choke point | §3.7 |
| render.layers.* | system/local/site/interior drawing | §3.13 |
| save.* | serialize, migrate, autosave | §3.15 |

### 4.2 Content file schemas (examples; field names binding)

**Part** (`data/core/parts/engine_methalox_vac.toml`) — stat ownership per 02/06:
```toml
id          = "core:engine_methalox_vac_120"
type        = "engine"
tier        = "T1"
name        = "VR-120 vacuum methalox engine"
mass_t      = 1.30
cost        = 9_000_000          # 2049 USD, 12 owns pricing
[engine]
thrust_kN   = 120.0
isp_s       = 363.0              # vac; 02 catalog is the source of truth
isp_sl_s    = 0.0                # vacuum-only (no sea-level bell)
throttle    = [0.4, 1.0]
propellant  = { Methane = 0.222, Oxygen = 0.778 }   # mass fractions, O/F = 3.5
restarts    = 12
gimbal_deg  = 6.0
[attach]
size_class  = "B"
stack_top   = true
stack_bottom= true
```

**Body** (`data/core/bodies/mars.json`) — elements/SOI republished from 01/03 canon, validated equal:
```json
{"id":"core:mars","parent":"core:sun","mu_m3s2":4.282837e13,
 "radius_m":3.3895e6,"rotation_period_s":88642.66,
 "elements":{"a_m":2.27939e11,"e":0.0934,"lon_peri_rad":5.8650,
             "t_peri_s":-1.4543e7,"sense":1},
 "soi_m":5.76e8,
 "atmosphere":{"interface_m":125000,"breakpoints":"core:atmo_mars"},
 "sectors":"core:sectors_mars","landing_class":"C"}
```

**Tech node** (`data/core/tech/ntr.toml`):
```toml
id        = "core:tech_ntr"
tier      = "T2"
act_hint  = 3
name      = "Nuclear-thermal propulsion"
prereqs   = ["core:tech_cryo_depots", "core:tech_fission_100kwe"]
cost_rp   = 1200                         # research points, 11 owns the economy
unlocks   = ["core:engine_ntr_25k", "core:part_h2_zbo_tank_l"]
```

**Recipe** (`data/core/recipes/sabatier_ch4.json`) — 05 §3.2's JSON schema verbatim; mass balance is 04's RX-03 canon (2.75 kg CO2 + 0.50 kg H2 → 1 kg CH4 + 2.25 kg H2O; ISS Sabatier / Mars ISRU baseline), normalized per tonne of primary output:
```json
{
  "id": "core:recipe/sabatier_ch4",
  "module": "core:module/sabatier_reactor",
  "tier": "T1",
  "inputs_t":  {"CO2": 2.75, "Hydrogen": 0.50},
  "outputs_t": {"Methane": 1.00},
  "byproducts_t": {"Water": 2.25},
  "loss_t": 0.0,
  "energy_kWh_per_t": 200,
  "heat_fraction": 1.0,
  "labor_h_per_t": {"crew": 0.0, "robot": 0.2},
  "min_automation": "A1",
  "wear_per_t": 1.0,
  "env": "any"
}
```
Validator checks fire here: Σinputs 3.25 t = Σoutputs 1.00 + byproducts 2.25 + loss 0.0 (exact; rule allows 0.5 %); all resource keys are canonical names; `energy_kWh_per_t` = 04 RX-03's 0.2 kWh/kg electrical (the −2.86 kWh/kg exothermic reaction heat is 04/09's thermal credit, not double-counted here). Sector records follow 03 §S-7a. Contract templates and program (autopilot) defs are analogous TOML; all validated per §3.4.

### 4.3 Component catalog (ECS components; serialized field-for-field)

| Component | Fields (units) | On |
|---|---|---|
| OrbitState | frame_id, a_m (or α), e, lon_peri_rad, t_peri_s, sense | rails entities |
| CartState | frame_id, x,y,vx,vy (m, m/s), m_kg, regime | NUMERIC craft |
| LandedState | body, longitude_rad, site_key? | landed craft/bases |
| Vessel | parts[] (rows: part_id, fill{resource: kg}, condition, attach links — §3.3), stage_plan (ordered part-set list), aggregates (cached), tanks{resource: kg} (derived cache = Σ part fills) | vessels |
| LedgerHost | network (pooled per-resource buffers, modules, links = module↔resource recipe adjacency, §3.9 topology rule) | bases, stations, vessels w/ industry |
| LSC | gas masses kg, V_press m3, T_K, stores, crew_ids | crewed cells (08) |
| CrewMember | name, skills, health, dose_Sv, task, A-multiplier | crew (08 §3.9) |
| CommsNode | antenna_range_m, powered, relay_flag | comm-capable entities |
| DepositLink | deposit_id, remaining_t, grade | miners (04) |
| Program | program_id, params, state | flight computers |
| SiteRef | (body, sector, slot), diff_handle | instantiated sites |
| Ownership | money flows, contract refs | program-level (12) |

### 4.4 Event-type catalog (queue records; full set for v1)

| Class | Types |
|---|---|
| Orbital | SOI_CROSS, ATMO_ENTRY, IMPACT_PREDICTED, PERIAPSIS_MARK, NODE_IGNITION, BURN_END, CLOSEST_APPROACH, ESCAPE_SUN |
| Ledger a/b | BUFFER_FULL, BUFFER_EMPTY, DEPOSIT_EXHAUSTED, GRID_DEFICIT |
| Ledger c | WARMUP_DONE, BATCH_DONE, BUILD_DONE, FAILURE (pre-rolled), MAINTENANCE_DONE, SHIFT_CHANGE, TRANSFER_ARRIVAL, HARVEST |
| Environment | ECLIPSE_IN/OUT, TERMINATOR, SPE_ONSET/PEAK/END, DUST_STORM_IN/OUT, OCCLUSION_IN/OUT (comms) |
| Crew/LS | PP_THRESHOLD (gas partial pressure), DOSE_LIMIT, MEAL/SLEEP boundaries (batched daily), MEDICAL |
| Meta | ALARM_CLOCK (player), AUTOSAVE_POINT, CONTRACT_DEADLINE, WINDOW_OPEN (launch windows), RESEARCH_DONE |

Record shape: `(t_due f64, seq u64, type, source_eid, generation u32, payload dict)`. Persistent classes (pre-rolled fate, alarms, deadlines) serialize; predictions recompute on load (§3.15).

**Payload schemas (binding for the orbital and persistent types — these are save-format-relevant):**

| Type | Payload |
|---|---|
| SOI_CROSS | `{craft_eid, from_frame, to_frame}` |
| ATMO_ENTRY | `{craft_eid, body_id, interface_alt_m}` |
| IMPACT_PREDICTED | `{craft_eid, body_id}` |
| PERIAPSIS_MARK / CLOSEST_APPROACH | `{craft_eid, other_eid?, r_m}` |
| NODE_IGNITION | `{craft_eid, node_id, dv_mps, est_duration_s}` |
| BURN_END | `{craft_eid, node_id}` |
| ESCAPE_SUN | `{craft_eid}` |
| FAILURE (pre-rolled, persists) | `{network_id, module_id, failure_class}` |
| TRANSFER_ARRIVAL (persists) | `{route_id, dest_network_id, manifest {resource: kg}}` |
| ALARM_CLOCK (persists) | `{label, owner_eid?}` |
| CONTRACT_DEADLINE (persists) | `{contract_id}` |
| WINDOW_OPEN (persists) | `{origin_body, dest_body, t_close_s}` |
| RESEARCH_DONE (persists) | `{tech_id}` |
| AUTOSAVE_POINT | `{reason}` |

All remaining types are **handler-internal**: the payload is consumed only by the posting system's own handler, under one convention — keys are snake_case; values are JSON scalars, entity ids, or content ids only (no live object references) — so any payload that ends up in a persistent record serializes without special cases.

### 4.5 Save schema versions (policy table)

| Schema | Ships with | Migration kept until |
|---|---|---|
| 1..N-dev | pre-release phases | best effort only |
| N (1.0) | release 1.0 | end of 1.x line |
| N+k | each later 1.x | end of 1.x line |

(Concrete numbers assigned at Phase 2 when the save system lands; the *policy* above is binding.)

### 4.6 Performance budget (binding; CI scenes assert ×3 slack)

| Subsystem | @1× (ms/frame) | @tier 7 (ms/frame) | Notes |
|---|---|---|---|
| RK4 craft physics (≤ 8 craft) | 2.0 | — | TOTAL across all NUMERIC craft (§3.6); physics warp ≤ 4× substeps included |
| Batch rails eval (≤ 2,000 obj) | 0.5 | 0.8 | one vectorized Kepler solve |
| SOI/encounter prediction | 0.3 | 0.6 | amortized; Brent refinements rare |
| Ledger (all sites) | 0.5 | 3.0 | §3.9 budget + governor |
| LSC/env/dose closed-form | 0.5 | 1.0 | hourly boundaries batched |
| Comms graph + occlusion | 0.2 | 0.3 | event-driven rebuilds |
| Event queue + warp control | 0.2 | 0.5 | |
| **Sim total** | **4.2** | **6.2** | **hard cap 8.0** (§3.14) |
| Input + UI logic | 0.8 | 0.8 | outside the sim cap; ≤ 1.0 per §3.14 |
| Starfield + world vector layer | 3.5 | 3.5 | conic LOD governs |
| Sprites/sites/particles | 2.0 | 2.0 | caches §3.13 |
| Text + HUD/UI composite | 1.5 | 1.5 | string LRU |
| **Render total** | **7.0** | **7.0** | **hard cap 7.0** (§3.14) |
| Headroom | 4.7 | 2.7 | 16.7 − sim − input/UI − render; GC, OS jitter. Worst legal case per the §3.14 caps: 16.7 − 8.0 − 1.0 − 7.0 = 0.7 |

Entity/scale caps (binding): ≤ 2,000 entities; ≤ 600 parts/vessel (06); ≤ 8 NUMERIC craft; ≤ 200 ledger modules/site, ≤ 50 sites with ledgers; ≤ 16 resident site maps; ≤ 300 comms nodes; ≤ 4,000 particles; ≤ 256 cached chunks.

### 4.7 Pinned physics test values (each row = one CI test)

| Test | Pinned value | Tolerance | Anchor |
|---|---|---|---|
| Earth surface escape velocity (R = 6,371 km) | 11,186 m/s | 1 m/s | √(2μ/R), NASA Earth fact sheet |
| Moon surface escape velocity (R = 1,737.4 km, volumetric mean) | 2,376 m/s | 1 m/s | √(2μ/R), NASA Moon fact sheet |
| Mars surface escape velocity (R = 3,389.5 km) | 5,027 m/s | 1 m/s | √(2μ/R), NASA Mars fact sheet |
| Circular speed, 300 km LEO (r = 6,678 km) | 7,726 m/s | 1 m/s | vis-viva; 01 §3.8 |
| Period, 300 km LEO | 5,431 s (90.5 min) | 1 s | 2π√(a³/μ) |
| Period, 400 km (ISS-class) | 5,545 s (92.4 min) | 5 s | ISS ≈ 92.5–93 min |
| GEO semi-major axis (T = 86,164.1 s) | 42,164 km | 1 km | published GEO radius |
| Hohmann LEO-300 → GEO total Δv | 3,893 m/s | 5 m/s | 2,426 + 1,467; standard result |
| Hohmann LEO-300 → GEO transfer time | 5h 16m (18,986 s) | 30 s | π√(a_t³/μ) |
| TLI Δv from LEO-300 (Hohmann to 384,400 km) | 3,107 m/s | 10 m/s | ≈ real TLI 3.1–3.2 km/s |
| Earth→Mars transfer time (1.000→1.5237 AU) | 258.9 d | 0.5 d | 01 §3.8 worked example |
| Earth→Mars departure v∞ | 2,945 m/s | 10 m/s | 01 §3.8 |
| TMI Δv from LEO-300 | 3,591 m/s | 10 m/s | 01 §3.8 (3,590) |
| Earth–Mars synodic period | 779.9 d | 0.5 d | 1/|1/T₁−1/T₂| |
| Kepler propagate 100 periods, e=0.9 ellipse | return to start | < 1e-3 m | closed-form: error must not grow with Δt |
| Hyperbolic flyby δ (Jupiter, v∞=5.64 km/s, r_p=2e5 km) | 144° | 1° | 01 §3.9 worked example |
| RK4 circular-orbit energy drift @ dt=0.02 s | < 1e-10 rel/orbit | — | rounding-dominated regime |
| Ascent acceptance: TWR-1.3 methalox 2-stage to LEO-300 | 9,300–9,500 m/s | band | 01 §3.10 tuning target |

### 4.8 Zoom layers

| Layer | Frame | z range (px/m) | Content | Handoff (hysteretic) |
|---|---|---|---|---|
| SYSTEM | heliocentric | 1.6e-10 – 1e-6 | schematic orbits, bodies as icons | → LOCAL when focus SOI > 60 % screen; ← when < 40 % |
| LOCAL | focus-body SOI | 1e-7 – 0.05 | bodies to scale, conics, vessels | → SITE on landed focus & z > 0.02; ← z < 0.01 |
| SITE | site tile map | 0.5 – 50 (16 px/tile nominal) | terrain, structures, vehicles | → INTERIOR on enter command |
| INTERIOR | habitat cells | 16 – 128 | cells, crew, machines (07/08) | ← exit command |

**Handoff zoom remap (LOCAL ↔ SITE):** the trigger value z > 0.02 px/m lies below SITE's 0.5 px/m floor, so z does **not** carry continuously across this handoff. Rule: SITE opens at its nominal 16 px/m (16 px/tile) regardless of the LOCAL z at the trigger; the reverse handoff (zooming out through SITE's 0.5 px/m floor) reopens LOCAL at z = 0.01 px/m (the hysteretic re-entry value). The 150 ms crossfade (§3.13) anchors both layers on the landed craft's screen position — the craft stays fixed on screen while the scales swap. All other handoffs (SYSTEM↔LOCAL, SITE↔INTERIOR) carry z continuously within overlapping ranges.

---

## 5. Player Interaction & UI

Architecture-owned player-facing surfaces (semantics of game UI belong to 12):

- **Widget framework** (§3.17): the retained-mode tree, layout pass, focus/modal routing, and intent-object sim boundary that every 12 screen composes — the architecture owns the framework, 12 owns what is built with it.
- **Time controls**: warp ladder UI states come straight from `core.clock` (current tier, why warp is blocked — "q = 24 kPa", "event in 4 s: Moon SOI", governor active). The honesty rule: when a budget governor lowers warp, the UI says so explicitly ("warp limited by base simulation load") — never silent slowdowns.
- **Alarm clock**: player-created ALARM_CLOCK events (next window per 01 Table 4.3, "wake me at periapsis", "30 d before contract deadline") — first-class queue citizens, listed in a sidebar, serialized.
- **Save UX**: save browser reads uncompressed headers (§3.15) for instant listing with act/playtime/version; incompatible-version saves shown greyed with the reason; autosave/quicksave per §3.15; "campaign seed" visible and copyable at new-game for community challenge runs (determinism §3.10).
- **Settings** (`core.config`, TOML in the user dir): resolution/integer scale, vsync, autosave cadence, UI scale, colorblind palettes (vector art makes this cheap — palettes are data), key rebinding, perf HUD toggle, governor thresholds (advanced).
- **Perf HUD (F3)** ships in release builds (§3.14) — players reporting "it stutters at my 40-base endgame" can screenshot the actual subsystem bars; bug reports become actionable.
- **Crash handling**: unhandled exception → `crash_recovery.aph` + a crash dialog with the traceback and a "copy report" button (no telemetry, no network — single-player offline doctrine).
- **Mod surface**: `data/<pack>/` drop-in; validator errors shown in a launcher-style content report listing each failing file/key — the same validator developers use (§3.4).

---

## 6. Progression Hooks

**How architecture gates content tiers:** every content item carries `tier` (T0–T4); `sim.research` exposes `unlocked(id)`; the loader never hides items — locked parts render greyed with their tech node, so the tree *is* discoverable in the builder (12's design). No engine feature is tier-gated; tiers gate *data*. The ledger, comms, and site systems are tier-agnostic — a T0 LEO station and a T4 Titan complex run identical code paths, which is what makes the endgame computationally safe.

**Vertical-slice roadmap** (build order; each phase is shippable to testers; DoD = definition of done, all CI green is implied):

| Phase | Scope (maps to Acts) | Definition of done |
|---|---|---|
| **0 — Orbital sandbox** | Kepler/frames/SOI/event queue, SYSTEM+LOCAL layers, warp ladder, maneuver nodes, pinned tests (Act 1 skeleton) | Fly a node-planned Earth→Mars transfer reproducing 01 §3.8 within 1 % (TMI 3,591 ± 36 m/s, 259 ± 3 d); 60 fps with 2,000 rails objects (perf scene P0); determinism test green |
| **1 — Builder + launch** | content pipeline + validator, part catalog (T0), vessel builder, staging, RK4 ascent + ascent program, physics warp | 2-stage TWR-1.3 methalox vehicle reaches LEO-300 for 9,300–9,500 m/s (01 §3.10 acceptance); builder fuzz suite green; pre-flight ascent sim = flight code path (06 §5) |
| **2 — Survival + landing + mining** | LSC life support (08), vacuum landing, landed state, site maps, first ISRU chain (04), save system v1 + autosave | Crewed Moon landing; crew survives a 14-day lunar night on stored power/water per 08/09 numbers; water-ice → LOX/LH2 chain runs; golden save #1 recorded; save migration harness in place |
| **3 — Bases** | ledger v1 (full §3.9), habitat construction (07), power grid (09), failure pre-rolls, INTERIOR layer | Unattended lunar propellant base runs 6 warped months; ledger-vs-ticker equivalence < 0.1 %; tier-7 warp holds 60 fps with 5 bases (scene P3) |
| **4 — Orbital industry** | docking/merge (06), depots, freighters + route planner (05 §3.6), economy/contracts (12), comms graph | Standing LEO→LLO methalox route self-runs for 1 sim-year incl. refuel/replan events; 05's Pelican/Drayage worked examples reproduce within 2 % |
| **5 — Full system + exotic environments** | all 03 bodies/sectors, aerocapture/EDL (01 §3.11), radiation + SPE events, Venus aerostat + Titan content, teleop latency, gravity assists UI | Jupiter arrival via gravity assist matching 01 §3.9 (δ = 144° case); Callisto-staging teleop scenario (07) playable; Mars EDL acceptance per 01 corridor rules |
| **6 — Automation + endgame** | A3/A4 autonomy (05 §3.4), T4 [SPECULATIVE] content, megaprojects, perf hardening, save-migration tooling, mod docs | "No Earth imports for 2 sim-years" self-sufficiency run at a Mars complex stays 60 fps; interstellar-precursor launch sequence playable; all golden saves from Phases 2–6 still load and pass |

Phase↔Act alignment: P0–P1 = Act 1; P2–P3 = Act 2; P4 = Act 3; P5 = Acts 4–5; P6 = Endgame. Each phase ends with a recorded golden save that becomes a permanent regression fixture — the campaign's history is the test corpus.

---

## 7. Cross-System Interfaces

- **01-orbital-mechanics.md** — *consumes (binding)*: universal-variable propagator spec + tolerances (3.3), RK4 50 Hz + RKF4(5) prediction (3.5), Brent SOI detection + hysteresis (3.4), warp ladder/guards + thrust-warp 2 ms budget (3.6), body-centric float64 rule (3.1, 8.4), 256-point conic sampling (§7). *Provides*: the event queue, batch propagation, warp governors, the ascent-acceptance CI test (01 §3.10), schema headroom for n-body (01 §9-Q8).
- **02-propulsion.md** — *consumes*: engine/tank stats schema fields, boiloff-as-linear-drain contract, control-allocation rules. *Provides*: deterministic failure-roll substreams (§3.10), RK4 mass-flow integration, warp-during-burn governor.
- **03-solar-system.md** — *consumes*: 2049 epoch elements, radii, rotation, sector records (S-7a), radiation fields (S-8), event-calendar entries (SPEs, storms). *Provides*: ephemeris cache, site-map engine + seeding (S-7c), anomaly/site persistence, event-calendar serialization.
- **04-resources-isru.md** — *consumes*: linear-flow recipes, deposit model g(d), predicted-event list (tank full/empty, exhaustion). *Provides*: ledger buffers/boundaries, deposit/knowledge schema storage (M-1/M-2), warp-exact integration.
- **05-industry-logistics.md** — *consumes*: recipe JSON schema (3.2 — normative), module state machine, F-1 throughput, F-2 teleop, route-planner emissions (3.6). *Provides*: rate solver, event queue for route schedules, comms RTT (§3.11), labor-pool buffers.
- **06-ships-stations.md** — *consumes*: part schemas, 600-part cap, port classes/merge rules, blueprint format needs. *Provides*: vessel-as-single-entity aggregation (§3.3), physics-body merge on dock, ascent-sim shared code path, blueprint serialization (a `Vessel` parts list is save-format JSON, exportable standalone).
- **07-bases-habitats.md** — *consumes*: closed-form environment curves, construction tasks, site/cell/network schemas, remote-ops gating. *Provides*: event scheduler (cooldowns, SPE shelter windows), dose-ledger integration, INTERIOR layer renderer, site diffs persistence.
- **08-life-support-crew.md** — *consumes*: LSC state shape, per-crew flow rates, hourly-integration contract (3.0). *Provides*: LSC-as-ledger-buffers with predicted partial-pressure threshold events (§3.9), crew entities, dose accumulation under warp.
- **09-power-thermal.md** — *consumes*: source/sink curves, battery capacities, eclipse geometry needs. *Provides*: grid solve inside `solve_rates` (f_power coupling), ECLIPSE_IN/OUT events from conic geometry.
- **10-vehicles.md** — *consumes*: vehicle stats and drive rules on tile maps. *Provides*: site tile engine, focused-vs-ledgered site simulation rule (§3.12), path queries on the tile grid.
- **11-research-tech.md** — *consumes*: tech-node schema, tier tags on all content. *Provides*: `unlocked()` gating API, RESEARCH_DONE events, validation that the tree is acyclic and reachable.
- **12-gameplay-economy-ui.md** — *consumes*: UI semantics, contract templates, tutorial flows (01 §3.8 worked example as data). *Provides*: widget framework (§3.17 — retained tree, layout, event routing, intent objects), save browser, alarm clock, perf HUD, settings, deterministic campaign seeds for challenge runs.

---

## 8. Failure Modes & Edge Cases

1. **NaN/Inf escape.** Any NaN in a craft state corrupts downstream silently. Containment: debug builds assert finiteness after every RK4 step and element fit; release builds check at mode transitions and event handlers — on detection, restore the entity's last-good snapshot (kept per mode switch), pause at 1×, raise a sim-warning. Never write NaN into a save (serializer validates).
2. **Event-queue storms.** A pathological base (oscillating buffer at its bound) could emit thousands of boundaries per sim-hour. Guard: per-source event-rate limiter (≥ 1 s sim between same-type boundaries from one source; the rate solver's clamp-to-bound at 1e-9 kg prevents the oscillation in the first place); perf HUD counter + sim-warning if any source exceeds 100 events/sim-day.
3. **Ledger fixed-point non-convergence** (§3.9): freeze at last iterate, log, continue — a 1e-9 kg/s rate error for one segment is harmless; an infinite loop is not. Counter visible in HUD; CI fuzz hunts for generating networks.
4. **Warp landing on stacked events** (SOI crossing + node + autosave within ms): total order via `seq` resolves deterministically; handlers are re-entrant-safe because each only bumps generations and posts — the loop processes until `peek_time() > t`.
5. **Spiral of death** (sim step slower than real time at 1×): `REAL_DT_CLAMP = 0.25 s` bounds catch-up; if the accumulator stays saturated 60 frames, the game auto-pauses with "simulation overloaded" + perf HUD hint, rather than slow-motion mush.
6. **Save corruption / power loss mid-write**: atomic temp+`os.replace` means the previous file survives; `body_sha256` in the header detects truncation/bit-rot at load → fall back to next-newest autosave automatically (with a notice).
7. **Migration bug ships**: golden saves + fixture chain in CI make this a build-breaker before release; if one escapes, the loader keeps the original file untouched (migration operates on the parsed dict, never in place on disk).
8. **Float precision regressions** (someone adds a heliocentric Cartesian cache "for speed"): the Neptune-fixture sub-pixel render test (§3.7) and the import-review rule are the tripwires; `camera.world_to_screen` choke point is the structural defense.
9. **Long-pause clock jumps** (laptop sleep, debugger): `real_dt` clamp handles it; wall-clock autosave timer uses monotonic clock.
10. **GC pauses**: CPython GC gen-2 collections can cost ~10 ms with large heaps. Mitigation: object churn minimized (SoA numpy, caches, no per-frame allocations in hot paths), `gc.freeze()` after content load, and explicit `gc.collect()` scheduled at scene transitions/autosaves where a hitch is already accepted.
11. **Cross-platform divergence** (§3.10): accepted and documented — saves are snapshots; the determinism guarantee is per-platform. Challenge-run leaderboards (12) must compare outcomes, not trajectories.
12. **Mod conflicts**: duplicate id without `patch:true` = hard load error listing both files; a mod removing an id referenced by a save → loader substitutes a tagged placeholder part (mass/no-function) and warns, instead of refusing the save.

**Risk register (top technical risks):**

| # | Risk | L×I | Mitigation |
|---|---|---|---|
| R1 | CPython too slow for endgame scale (40+ bases, tier 7) | M×H | analytic-first ledger (§3.9) makes cost ∝ events not time; budgets + governors + CI perf scenes from Phase 0; numpy batch paths; scale caps (§4.6) are design law, not hopes |
| R2 | Ledger diverges from "what 1× would do" → trust collapse | M×H | single code path at all rates; ledger-vs-ticker equivalence test (§3.16-3); conservation property tests |
| R3 | Event-prediction bugs (missed SOI/buffer events at warp) | M×H | predict-don't-poll contract, no polling code path exists; property tests over random orbits/networks; warp clamps to `peek_time()` structurally |
| R4 | Save-format churn during development burns trust | H×M | schema versioning from Phase 2, migration fixtures per release, golden saves; pre-1.0 saves explicitly best-effort |
| R5 | Render cost of text/vector UI in software | M×M | string LRU + glyph atlas, layer caches, conic LOD; perf scene P5; fallback: drop AA lines at low zoom |
| R6 | Precision bug class (jitter, drift) discovered late | L×H | §3.7 numbers verified up front; choke-point transform; Neptune fixture test from Phase 0 |
| R7 | Sibling-doc numeric drift (constants diverge between docs/data) | M×M | content validator cross-checks republished canon (SOI table, atmosphere breakpoints) at load; single-source data files |
| R8 | Scope creep in engine features (n-body, 3D, multithread sim) | M×M | "hard decisions" doctrine; schema headroom reserved (01 §9-Q8) but implementation explicitly out of v1 |
| R9 | Modding API promises constrain refactors | L×M | only the content schemas + validator are public API; internal modules documented as unstable pre-1.0 |
| R10 | Test suite slower than developers' patience → skipped | M×M | unit+property suite target < 90 s; golden/perf in separate CI job; pytest -x fast path documented |

---

## 9. Open Questions

1. **Audio architecture** is unspecified bible-wide (no sibling owns it). pygame.mixer suffices technically; need a decision on whether vacuum-silence realism (sound only inside pressurized frames / through structure) is in scope — flavor-vs-effort call for 12.
2. **Lambert window-scan vectorization**: scanning 200 departure dates × 100 TOFs per frame for the window bar is ~2e4 Lambert solves; batched numpy makes it ~5 ms but the UX may want it asynchronous (coroutine budget slicer) — decide at Phase 0 implementation.
3. **Interior layer fidelity**: are crew rendered as moving agents (pathfinding on cell tiles) or as status icons in cells? 07/08 read either way; agent rendering adds an A*-on-tiles cost and animation art budget. Recommend icons for v1, agents post-1.0.
4. **Ledger power solve vs. 09's final grid model**: §3.9 assumes 09's grid reduces to per-segment linear supply/demand with battery buffers. If 09 introduces nonlinear curves (e.g., reactor ramp limits), the rate solver needs a piecewise-linearization pass — confirm with 09 (doc pending).
5. **Replay/flight-recorder feature** (ghost trajectories, post-mission analysis per 12?): cheap if we log sampled states at event boundaries, expensive if full-rate. Decide before Phase 1 so the logging hook exists in the integrator from the start.
6. **Workshop/mod distribution**: folder drop-in is v1; any platform-workshop integration (Steam) changes packaging and validation UX — business decision, defer.
7. **32-bit float render fast path**: if profiling shows the float64 camera math hot (unlikely — it is O(visible entities)), a float32 camera-local cache per frame is safe *after* the §3.7 subtraction; keep as a known optimization, do not pre-build.
8. **Pause-the-world vs. background Earth economy** during menus/builder (12 owns the call): architecture supports both (builder runs in scratch world); default assumption is hard pause.
9. **Determinism scope for challenge runs** (12): is per-platform bit-exactness enough for community races, or do we need cross-platform? If the latter ever becomes a hard requirement, the only honest path is replacing libm transcendentals in the sim core with our own polynomial implementations (~2 ULP, deterministic) — feasible, ~2 weeks, but not v1.
10. **Telemetry-free crash triage**: with no network reporting (privacy doctrine), do we ship a "bundle save+log+sysinfo to zip" button for forum reports? Recommend yes at Phase 2.
