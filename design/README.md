# PROJECT "APHELION" — Design Bible Master Document

Status: design bible complete (16 domain documents), pre-code · This file: index, canon summary, build roadmap, risk register, and the bible-wide open-question harvest.
Owner: lead designer · Conventions doc governs; where this summary and a domain doc disagree, the domain doc wins inside its ownership boundary.

---

## 1. Elevator Pitch & Design Pillars

**APHELION** is a single-player, 2D top-down, hard-realism space survival/engineering sim (Python 3.12 + pygame-ce): KSP's orbital flight × Oxygen Not Included's habitat engineering × Factorio's industry, played as **one persistent engineer-founder campaign across a REAL-SCALE solar system, 2049 → ~2090+**. You claw a cash-starved private program off Earth, learn logistics at the Moon, colonize Mars, industrialize the Belt and the clouds of Venus, settle the outer system, and end the game with one or both megaprojects: a **self-sufficient off-Earth civilization** (the Foundation Audit) and the **first interstellar precursor probe**. There is no combat and there are no aliens. The antagonist is physics — distance, gravity, entropy, radiation, heat, and the rocket equation, all charged at real prices.

### The seven pillars

1. **Real numbers, named anchors.** Existing tech uses real published figures (Merlin, RL10, MOXIE, KRUSTY, ISS ECLSS…). Future tech must be a seriously-studied concept (NASA/ESA/peer-reviewed). Anything beyond engineering-complete is tagged **[SPECULATIVE]** and lives in tier T4 only. Forbidden forever: FTL, reactionless drives, non-spin artificial gravity, handwaved resources.
2. **Real scale, real delta-v.** 1 AU = 149,600,000 km. Earth surface → LEO costs ~9,400 m/s. Saturn is a six-year Hohmann. Tedium is defeated by 1,000,000× time warp and automation — never by shrinking the universe or discounting the physics.
3. **Everything is a ledger.** Mass and energy are conserved everywhere: ISRU recipes balance to ±1%, every watt consumed becomes a watt of heat that must be radiated (the T⁴ radiator doctrine), every kg of propellant is bought with the raw Tsiolkovsky logarithm shown in the UI. No magic balance layer between design-time numbers and flight-time physics.
4. **Entropy is an antagonist.** Cryogens boil off, engines wear out, spares run out, crews take dose, closure never reaches 100%. Failure is content, not a fail state: aborts, rescues, stand-downs, and dead crew become entries in the Chronicle — the auto-generated program history that is itself the endgame artifact.
5. **Tiered honesty (T0–T4).** The tech tree is a coarse TRL ladder from "flying in 2049" to "[SPECULATIVE] fusion torch", and every part says which rung it stands on. You learn where you go (Science from exploration) and you learn by flying (Engineering Data from operating hours).
6. **From money to mass.** Acts 1–2 are about dollars (contracts, milestones, investors). Act 3 is the hinge. Acts 4–5 are about mass and the Self-Sufficiency Index, as ISRU and industry replace the Earth market. The economic arc *is* the campaign arc.
7. **Instrument first, place behind the glass.** At gameplay zoom the screen is a readable engineering drawing; the painterly layer (butterscotch Mars sky, Titan's orange haze) lives behind it and never carries gameplay meaning alone. Audio and visuals are strictly downstream of the sim: the physics is the animator, the camera is the microphone, vacuum is silent.

---

## 2. System Map

How the major systems feed each other (doc numbers in boxes; arrows are the load-bearing data flows):

```
            ┌────────────────────────────────────────────────────────────────────┐
            │ 12 GAMEPLAY / ECONOMY / UI — four lenses (Pilot·Engineer·Planner·  │
            │ Base), contracts & money (Acts 1–3) → mass & SSI (Acts 4–5),      │
            │ alerts, Chronicle. Frames every screen below.                      │
            └─────────▲─────────────────────▲──────────────────────▲─────────────┘
                      │ payouts, prestige   │ SCI/ED, unlocks      │ alarms, telemetry
            ┌─────────┴─────────┐   ┌───────┴────────────┐  ┌──────┴───────────────┐
            │ 11 RESEARCH &     │   │ 16 COMMS & LIGHT-  │  │ 91-15 AUDIO          │
            │ TECH (T0–T4 gates │◀──│ LAG NETWORKS (a    │  │ 90-14 VISUALS        │
            │ on ALL content)   │   │ bit is cargo)      │  │ (read-only views of  │
            └───────▲───────────┘   └──────▲─────────────┘  │ the sim state)       │
        SCI from    │       ED from        │ links gate     └──────────────────────┘
        exploration │       flight hours   │ teleop/science
                    │                      │
   ENVIRONMENT      │     TRANSPORT        │           PRODUCTION & HABITATION
  ┌──────────────┐  │   ┌──────────────┐ Δv map,     ┌──────────────────┐
  │ 03 SOLAR     │──┴──▶│ 01 ORBITAL   │ windows,    │ 05 INDUSTRY &    │
  │ SYSTEM       │      │ MECHANICS    │ transport ─▶│ LOGISTICS        │
  │ bodies, sites│ eph- │ patched      │ costs       │ chains, routes,  │
  │ radiation,   │ emer-│ conics, EDL, │             │ shipyards, spares│
  │ atmospheres  │ ides │ rendezvous   │             └───▲──────┬───────┘
  └──────┬───────┘      └──────▲───────┘    refined goods │      │ parts, spares
         │ deposits, grades    │ thrust, Isp, boiloff     │      ▼
         ▼                     │                          │  ┌────────────────────┐
  ┌──────────────┐ propellant ┌┴───────────────┐          │  │ 06 SHIPS & STATIONS│
  │ 04 RESOURCES │───────────▶│ 02 PROPULSION  │          │  │ 07 BASES & HABITATS│
  │ & ISRU       │            │ engines, tanks,│          │  │ 10 SURFACE/ATMO    │
  │ mining,      │────────────│ depots, sails  │          │  │    VEHICLES        │
  │ chemistry    │  refined resources ─────────┴──────────┘  └─────────┬──────────┘
  └──────────────┘                                                     │ hulls, berths
         ▲                                                             ▼
         │ crew labor, EVA                                  ┌────────────────────┐
         └──────────────────────────────────────────────────│ 08 LIFE SUPPORT &  │
                                                            │ CREW — O2/H2O/food │
   09 POWER & THERMAL: every box above draws kWe and must   │ loops, dose, morale│
   reject kWt — radiators are as binding as delta-v.        └────────────────────┘
   13 ARCHITECTURE: the substrate under everything — one event queue, analytic
   warp-exact ledgers, body-centric float64, determinism by construction.
```

The core gameplay loop in one sentence: **03 tells you where things are, 11 makes you go look, 04 digs them up, 05 turns them into hardware, 06/07/10 are the hardware, 08 keeps people alive inside it, 02 + 01 move it all around, 09 powers and cools every step, 16 connects it, 12 prices it and tells the story, 13 makes it run at 60 fps.**

---

## 3. Reading Order & Document Index

Recommended order (not numeric): understand the game, then the engine, then movement and the world, then the production stack, then the cross-cutting layers.

| # | File | What it owns (2–3 lines) |
|---|---|---|
| 1 | `12-gameplay-economy-ui.md` | The game itself: four play modes (Pilot/Engineer/Planner/Base), five-act campaign, all money (contracts, milestones, investors, insurance), Prestige, the SSI and the money→mass transition, alerts, every major screen, the Chronicle. Read first — everything else serves this. |
| 2 | `13-architecture.md` | The engine: analytic-first simulation, the single global event queue, body-centric float64, data-driven content, determinism, performance contract (60 fps, ≤ 8 ms sim/frame), save system, and the phase-by-phase build roadmap this README adopts. |
| 3 | `01-orbital-mechanics.md` | How things move: 2D planar patched conics, on-rails universal-variable Kepler, finite burns, EDL/aerocapture, rendezvous/docking, time-warp machinery, and **THE CANONICAL DELTA-V MAP** (§4.2) every other doc must cite. |
| 4 | `03-solar-system.md` | The canonical environment database: every body's real elements, gravity, atmospheres, temperatures, radiation fields, surface sectors, and the anomaly/discovery layer (real derelicts, lava tubes, cold traps). The solar system as antagonist. |
| 5 | `02-propulsion.md` | Every thrust-producing device: chemical (solid→methalox), NTR/LANTR, electric, sails, RCS, tanks, boiloff, depots, propellant transfer, engine reliability/wear. Owns all engine stats. The power–thrust–Isp triangle. |
| 6 | `04-resources-isru.md` | Rock/ice/gas → tank of product: resource taxonomy, the prospecting chain (orbital survey → core sample → proven grade), extraction hardware, real ISRU chemistry with kWh/kg energy balances, microgravity mining, cryo conditioning. |
| 7 | `05-industry-logistics.md` | Refined resources → finished hardware: production chains (Electronics are the honest long pole — imported until T3), the automation ladder (EVA → teleop → autonomous), shipyards, freighters/routes, mass drivers, and the spares/maintenance economy. |
| 8 | `06-ships-stations.md` | The Drydock: 2D grid vessel editor, builder math (live Tsiolkovsky, COM, TWR), structural checks, spin-gravity stations, docking, 113-part catalog, four fully worked example builds. |
| 9 | `07-bases-habitats.md` | Surface and aerostat bases: placement grid, four utility networks, habitat catalog (rigid/inflatable/ISRU/buried), tension-vs-buckling pressure-vessel rules, and per-body engineering packages (Moon night, Mars dust, Venus aerostats, Titan cold, Europa siege). |
| 10 | `08-life-support-crew.md` | The biology layer: BVAD metabolic mass balance, the ECLSS closure ladder (open loop → ISS-grade → ~98% bioregenerative), cabin atmospheres, food/agriculture, radiation dose, deconditioning, morale, skills, death. Owns crew consumption canon. |
| 11 | `09-power-thermal.md` | Watts in, watts out: solar/RTG/fission/[SPECULATIVE] fusion generation, storage, the grid sim, and the thermal network under the radiator doctrine (T⁴). Power is capability, heat is the universal tax. |
| 12 | `10-vehicles.md` | Everything that moves without reaching orbit: rovers, hoppers, Mars rotorcraft, Venus aerobots, Titan aviation and submarines, Europa cryobots; locomotion/flight/marine physics from one formula set fed real planetary data. |
| 13 | `11-research-tech.md` | The campaign skeleton: Science (exploration) + Engineering Data (operations) currencies, 129 tech nodes across T0–T4, prototyping pain, reliability maturation, 18 location-gated Discoveries, sample-return mechanics. |
| 14 | `92-16-communications-networks.md` | (Doc 16) Link budgets as gameplay: Friis-style rate law, antenna/relay catalog, bandwidth as a resource, conjunction/EDL blackouts, DSN leasing, the constellation design loop. From "the network is free" (Act 1) to "you are the network" (Act 4+). |
| 15 | `90-14-visual-direction-rendering.md` | (Doc 14) Art direction canon and the pygame-ce + moderngl hybrid pipeline with mandatory software fallback: instrument-first compositing, per-world identity cards, physically honest FX (plume optics, Draper point), photo/Chronicle print idiom, accessibility budgets. |
| 16 | `91-15-audio-direction.md` | (Doc 15) Audio owner (resolves 13 §9-Q1): vacuum silence canon, ambience-as-instrumentation keyed to live sim state, the three-voice alarm grammar (ISS C&W anchor), silence-first mixing for a 170-hour campaign, pygame.mixer architecture. |

Note on numbering: files `90/91/92` are presentation/late-canon docs whose internal titles are 14, 15, 16; the prefix just sorts them after the 13 core docs.

Canon ownership (binding, from conventions): **01 owns the delta-v map · 03 owns body data · 02 owns engine stats · 08 owns crew consumption.** Additionally established in the docs: 09 owns power/thermal performance curves, 06 owns the part grid/builder math (stubs republish 02/09 verbatim), 11 owns the tree layout and tier placement, 12 owns money and alert classes, 13 owns implementation contracts, 16 owns link rates, 90-14 owns look, 91-15 owns sound.

---

## 4. Canonical Glossary

### Technology tiers (≈ coarse NASA TRL ladder)

| Tier | Meaning | Examples |
|---|---|---|
| **T0** | Flown today; the 2049 baseline (TRL 9) | Merlin, RL10, ISS ECLSS, MOXIE, MMRTG, Vega balloons |
| **T1** | Flight-proven derivatives (TRL 6–8) | Large methalox reuse, cryo depots, metal printing on orbit, ROSA arrays |
| **T2** | Studied-and-credible (TRL 4–6) | NTR (NERVA/DRACO), Kilopower/FSP, large ISRU plants, SEP freighters, aerocapture |
| **T3** | Lab-demonstrated (TRL 2–4) | 100 kW Hall (X3), VASIMR, MPD, bioregenerative closure (MELiSSA), mass drivers, Titan submarine, minimal-fab wafers |
| **T4** | **[SPECULATIVE]** — physics-sound, beyond engineering-complete, tagged on the tin | Fusion torch (DFD), fission-fragment, He3 economy, skyhook, interstellar precursor |

Honesty flags used bible-wide: **[SPECULATIVE]** (T4 only), **[SIMPLIFIED]** (real process, deliberately coarse), **[LUMPED]** (several real species folded into one resource), **[est]** (real but still-evolving number).

### Campaign acts

| Act | Theater | Economic mode |
|---|---|---|
| **1** | Earth + LEO | Money: contracts, reuse, depots (T0–T1) |
| **2** | The Moon | Money→logistics school: polar ice, lunar LOX, first base (T1–T2) |
| **3** | Mars + NEAs | The hinge: NTR era, ISRU methalox, first colony (T2) |
| **4** | Main Belt + Venus | Mass: metallic asteroids, aerostats, Silicon Independence (T2–T3) |
| **5** | Outer planets | Mass: Callisto staging, Titan, Enceladus (T3–T4) |
| **End** | Megaprojects | Foundation Audit (self-sufficient civilization) and/or Interstellar Precursor (≥ 10 AU/yr) |

Build-phase alignment: Phases 0–1 = Act 1 · 2–3 = Act 2 · 4 = Act 3 · 5 = Acts 4–5 · 6 = Endgame · 7 = release polish.

### Canonical resources (exact spellings — these strings appear in code and data)

Base list (conventions, 29 entries):
`Water, Oxygen, Hydrogen, Methane, Nitrogen, CO2, Ammonia, Argon, Xenon, Regolith, IronSteel, Aluminum, Titanium, Copper, Silicon, RareEarths, Uranium, Thorium, Pu238, Carbon, Polymers, BasaltFiber, Glass, Electronics, MachineParts, StructuralParts, FoodRations, Biomass, He3` (He3 is **[SPECULATIVE]**/T4 only).

Registered extensions ("only when genuinely needed" rule):
- **RP-1 / RP1** — kerolox fuel, Earth-import (declared by 02). ⚠ Spelling conflict on record: 06 §9 says "no hyphen in RP1", 12 §4.3 registers `RP-1`. Must be reconciled before code (see §7-A below).
- **NTO, MMH** — hypergolic pair, Earth-import (02; price rows still missing from 12 §4.3).
- **Wafers** — semiconductor stand-in (05).
- **MedSupplies** — pharma/filters/micronutrients (08).
- **SurveyData** — intangible, tracked in GB, 2 SCI/GB anomaly conversion (03; 05 transports it).

### Key terms

- **SOI / patched conics / on-rails** — Laplace sphere-of-influence frames; coasting craft ride exact analytic Kepler conics (drift-free, warp-safe); numeric integration (RK4 @ 50 Hz) only under thrust or in atmosphere.
- **The Δv map** — 01 §4.2, the single source of truth for transfer costs (E1 Earth→LEO 9,400 m/s; M1 LEO→TLI 3,110; R1 LEO→Mars 3,590; J1 Jupiter 6,300; S1 Saturn 7,280…). No sibling doc may invent its own numbers.
- **SCI / ED** — Science (spendable, from exploration & sample return) and Engineering Data (per-part-family experience from operating hours; drives reliability maturation and gates higher tiers).
- **SSI** — Self-Sufficiency Index, the Act 4–5 victory metric: fraction of program demand met without Earth imports, per category (propellant, structure, food, electronics…).
- **ECLSS / closure** — life-support loop regeneration fraction; T0 open loop → ISS-grade ~40–50% O2 / ~98% water → T3 bioregenerative ~98% cap. 100% closure deliberately does not exist.
- **ZBO / boiloff** — cryogen loss modeled as analytic linear drains; zero-boiloff cryocoolers cost power; depots are gameplay.
- **PSR** — permanently shadowed region (lunar/Mercury polar cold traps; the Act 2 ice keystone).
- **EDL** — entry, descent, landing; Sutton–Graves heating, corridor rules, TPS catalog (01).
- **The Chronicle** — the auto-generated history log (Dwarf Fortress lineage); FIRSTs, failures, and dead crew all land here; exported as the endgame document.
- **Four lenses** — F1 Pilot (seconds), F2 Engineer (minutes), F3 Planner (hours–years), F4 Base (days): four views of one persistent world.
- **Golden save** — recorded end-of-phase campaign save kept forever as a regression fixture.
- **Event queue** — the single global priority queue of predicted discontinuities (SOI crossings, tank-empty, SPE onset, harvest…); nothing polls, nothing tunnels through warp.

Units: SI everywhere in sim code (m, kg, N, W, Pa, K); UI displays kg/t, m/s, kN, kWe/kWt, kPa, K, km/AU. Money is constant-2049 USD. Epoch t = 0 is 2049-01-01 00:00 UTC.

---

## 5. Build Roadmap (Phases 0–7)

Adopted from 13 §6 (binding there for Phases 0–6) and extended with a release phase. Every phase is shippable to testers, ends with all CI green and a recorded golden save. **DoD = the concrete vertical slice that proves the phase.**

### Phase 0 — Orbital sandbox (Act 1 skeleton)
- **Goal:** the physics kernel is true. Fly the real solar system with nothing to build yet.
- **Implements:** 13 kernel (event queue, warp ladder, determinism, SYSTEM+LOCAL layers), 01 core (Kepler/universal variables, SOI frames, maneuver nodes, Lambert window scan), 03 subset (Sun/Earth/Moon/Mars elements + pinned-test bodies).
- **DoD slice:** a node-planned Earth→Mars transfer reproduces 01 §3.8 within 1% (TMI 3,591 ± 36 m/s, 259 ± 3 d); 60 fps with 2,000 on-rails objects; bit-exact determinism test green; warp to 1,000,000× clamps exactly to predicted events.

### Phase 1 — Builder + launch (Act 1 playable)
- **Goal:** design a rocket, fly it to orbit, with the same numbers in the editor and in flight.
- **Implements:** 13 content pipeline + schema validator, 06 Drydock (grid editor, staging, live Δv/TWR), 02 T0 chemical catalog + tanks, 01 §3.10 ascent (RK4 atmosphere, ascent program), physics warp.
- **DoD slice:** a 2-stage TWR-1.3 methalox vehicle reaches LEO-300 for 9,300–9,500 m/s; builder fuzz suite green; the pre-flight ascent simulation and the flight integrator are one code path (06 §5).

### Phase 2 — Survival + landing + mining (Act 2 opens)
- **Goal:** people can live, land, and dig. Saves exist.
- **Implements:** 08 life-support core (metabolic ledger, cabin atmosphere, dose), vacuum landing + landed state, 03 site/sector maps, 04 first ISRU chain (PSR water-ice → electrolysis → LOX/LH2), save system v1 + autosave + migration harness.
- **DoD slice:** crewed Moon landing; the crew survives a 14-day lunar night on stored power/water per 08/09 numbers; the ice→LOX/LH2 chain runs under warp with exact tank-event prediction; golden save #1 recorded.

### Phase 3 — Bases (Act 2 complete)
- **Goal:** persistent unattended infrastructure under deep warp.
- **Implements:** 13 ledger v1 (full analytic rate solver), 07 habitat construction (Deploy→Outfit→Commission, four networks), 09 power grid + thermal network + load shedding, failure pre-rolls, INTERIOR render layer.
- **DoD slice:** an unattended lunar propellant base runs 6 warped months; ledger-vs-tick equivalence < 0.1%; tier-7 warp holds 60 fps with 5 bases (perf scene P3).

### Phase 4 — Orbital industry (Act 3)
- **Goal:** the logistics economy: routes, depots, money, and the network.
- **Implements:** 06 docking/merge, 02 depots + propellant transfer + boiloff economy, 05 freighters + route planner + maintenance/spares, 12 economy (contracts, milestones, investors, alerts), 16 comms graph + link rates.
- **DoD slice:** a standing LEO→LLO methalox route self-runs for 1 sim-year including refuel/replan events; 05's Pelican/Drayage worked examples reproduce within 2%; a Career campaign can earn its way through the Act 1 milestone ladder.

### Phase 5 — Full system + exotic environments (Acts 4–5)
- **Goal:** the whole solar system is a destination, and every body engineers differently.
- **Implements:** all 03 bodies/sectors/anomalies, 01 §3.11 aerocapture/EDL + gravity assists UI, radiation + SPE events (03/08), 07 Venus aerostat + Titan packages, 10 vehicles (rovers, aerobots, hoppers, submarine), 05 teleoperation light-lag, 16 conjunction/relay constellations.
- **DoD slice:** Jupiter arrival via gravity assist matching 01 §3.9 (δ = 144° case); the Callisto-staging teleop scenario (07) is playable; Mars EDL passes 01's corridor acceptance; a Venus aerostat deploys and floats at 54–55 km per 06 Build D / 07.

### Phase 6 — Automation + endgame
- **Goal:** the game can be *finished*.
- **Implements:** 05 A3/A4 autonomy, 11 complete tree incl. T4 [SPECULATIVE] content, megaprojects (Foundation Audit E-28, Interstellar Precursor E-29, Europa bore, mass drivers), perf hardening, save-migration tooling, mod docs.
- **DoD slice:** a "no Earth imports for 2 sim-years" self-sufficiency run at a Mars complex stays at 60 fps; the interstellar-precursor launch sequence is playable end-to-end; every golden save from Phases 2–6 still loads and passes.

### Phase 7 — Presentation, accessibility & release hardening
- **Goal:** it looks, sounds, and reads like the bible promises, on the weakest contract hardware.
- **Implements:** 90-14 GPU compositing path + software-fallback parity, photo mode + Chronicle print filters, 91-15 full audio (score episodes, alarm grammar, diegetic propagation), 12 onboarding/tutorialization (01 §3.8 as the canonical tutorial), balancing/calibration pass against 12 §4.2 hour targets (G-12), accessibility audits.
- **DoD slice:** Acts 1–2 playtest lands within ±50% of target hours; WCAG flash/contrast audits pass on every alert and FX; the pure-SDL2 fallback renders identical gameplay semantics on an Intel UHD 620-class machine at 60 fps; mix verifies at ≤ −16 LUFS / ≤ −1 dBTP; full golden-save regression suite green.

---

## 6. Top-10 Design Risk Register

| # | Risk | Likelihood / Impact | Mitigation |
|---|---|---|---|
| 1 | **Python/pygame can't hold 60 fps** with a populated solar system, multi-base ledgers, and deep warp. | Med / Critical | Analytic-first doctrine (nothing ticks that can be solved closed-form); single event queue; numpy-vectorized batch propagation; binding CI perf budgets with named scenes (13 §3.14) from Phase 0; hierarchical thermal aggregation and float32 render caches held in reserve. |
| 2 | **Real-scale realism reads as tedium** — 9.4 km/s to orbit, 6-year Saturn transfers, month-long spirals. | Med / Critical | 1,000,000× warp that is *exact*, warp-to-event automation, route planner, four-lens time horizons, alarm clock + analytic "state at arrival" previews; the Phase 0/2 DoD slices exist precisely to test this feel early. |
| 3 | **Cross-doc canon drift** — 16 documents share hundreds of numbers (boiloff, dose, leak rates, prices); several §9s already flag byte-identical-audit debts and one live spelling conflict (RP1/RP-1). | High / High | Single-owner rule per number (this doc §3); republish-verbatim stubs; a scheduled pre-code reconciliation pass (§7-A); load-time schema validation so a divergent constant is a build failure, not a bug. |
| 4 | **Scope** — 113 parts, 129 tech nodes, ~40 bodies, 10 vehicle families, megaprojects: a multi-year content mountain for a small team. | High / High | Phased vertical slices each independently shippable; content is data, not code; acts gate content authoring order; pre-identified cut lists in §9s (mission-patch generator, Europa ocean floor, Titan HPF, droplet radiators). |
| 5 | **The 2D flattening breaks somewhere expensive** — no inclination means no plane changes, polar orbits, or real eclipse geometry; hostile realism reviewers will probe it. | Med / Med | Honesty doctrine: documented casualties (01 §3.14, 03 S-2), no fake compensation taxes, honesty tooltips in UI; eclipse over-prediction accepted and stated; retrograde `dir` flag preserves real difficulty by other means. |
| 6 | **Economy/pacing numbers are anchored but untested** — hour targets, spares coefficients, prices, polar surcharge are designer estimates with zero playtest data. | High / Med | Tuning knobs isolated from physics (11 Q6 doctrine: never touch λ/realism, only costs and incomes); G-12 calibration rule + opt-in telemetry plan; balance passes scheduled at Phases 4 and 7. |
| 7 | **UI complexity overwhelms** — four modes, dozens of screens, Sankey diagrams, link budgets, thermal networks. | Med / High | Instrument-first pillar; ISS four-class alert taxonomy with silence-first audio; progressive disclosure by act (Act 1 needs no comms/thermal UI); the Drydock as "a spreadsheet you can see" — one formula doctrine end to end. |
| 8 | **Determinism guarantee fails in practice** (float divergence, RNG misuse, threading leaks) and with it golden saves, Simulation-mode trust, and challenge runs. | Med / High | Single-threaded sim core; named PCG64 substreams; pre-rolled stochastic outcomes; bit-exact CI determinism test from Phase 0; cross-platform exactness explicitly deferred (13 Q9) rather than half-promised. |
| 9 | **Save-format longevity** across 7 phases of schema evolution; a broken migration invalidates the regression corpus and player campaigns. | Med / High | Schema version field from save v1 (incl. n-body headroom per 01 Q8); migration harness built in Phase 2, exercised every phase; golden saves double as migration tests. |
| 10 | **Late-canon integration debt** — docs 14–16 (visual/audio/comms) landed after the core 13 and already carry collisions (F3 keybinding; 16's scheduler vs 13's Phase-4 budget; 90's budget amendments awaiting 13 ratification). | Med / Med | Treat §7-A reconciliation as a blocking milestone before Phase 1 content authoring; 13 explicitly ratifies or rejects each amendment; keybinding and budget tables get single canonical homes. |

---

## 7. Bible-Wide Open Questions (harvested from every doc §9, deduplicated, grouped)

> **STATUS (2026-06-11): ALL 35 QUESTIONS RULED.** Every item below was decided by the Director and recorded in [DECISIONS.md](DECISIONS.md), then applied to the docs by the canon-cleanup pass. This section is preserved as the historical register; where it conflicts with DECISIONS.md, DECISIONS.md wins.

The items below are the ones worth deciding **before coding starts** or at the named phase gate. Source docs in parentheses. Recommendations recorded in the source docs are noted where they exist.

### A. Canon reconciliation — blocking, schedule as one pre-code pass

1. **Resource-extension spellings**: `RP1` (06 §9) vs `RP-1` (12 §4.3) must converge to one string; verify `Wafers`, `MedSupplies`, `SurveyData`, `NTO`, `MMH` are defined identically in their owning docs; add the missing NTO/MMH price rows to 12 §4.3. (02, 06, 12)
2. **Byte-identical shared numbers audit**: liquefaction/ZBO energies (02/04/09), berm areal mass, storm solar floor, maintenance multipliers and the 07 §4.4 master table (03/04/07/08/09). One audit pass, diffs resolved by the owning doc. (04 Q10, 07 Q11)
3. **Deep-shield GCR floor**: 08's f_GCR floor of 0.30 is binding at every depth, yet 03's measured thick-atmosphere overrides show the floor must break past ~1,000 g/cm². 08 must either confirm the floor or publish a decaying-floor extension — it materially changes belt/Europa endgame real estate. (07 Q2 → 08, 08 Q5)
4. **Radiation model honesty band**: S-8c reproduces Ganymede at ~2× literature before the B-field factor; choose smooth-fudge vs piecewise-exact-anchors before implementation freeze. (03 Q10)
5. **One wear model**: confirm 02 (per-ignition + wear) × 11 (maturity) × 05 (MTBF/spares) multiply without double counting; vehicles (10) and ships (06) already pledge to use it — make it an interface test. (11 Q3, 06 Q7, 05 Q7)
6. **Aerostat tier**: conventions say T2, 11 gates crewed HB-05 at T3 — resolve with 07's module tiering and rebalance §3.3 sums. (11 Q11)
7. **F3 keybinding collision**: 12 binds F3 = Planner; 13/90-14 bind F3 = perf HUD. Trivial, but three docs consume the answer. (91-15 Q9)
8. **Engine catalog registrations**: 02 to accept/reject the Bantam-class methalox pair and the argon Hall string (06 Q1), and the pump-fed methalox *lander* row that HOP-P range targets need (10 Q10).
9. **Skyhook ledger ownership** (05 bookkeeping vs 01 orbital state — is a tether tip a standard node with a Δv discount?) and the 05/10 `bot_mule` single-data-row check. (05 Q4, Q8; 10 Q8)
10. **Aerostat hardware home**: do 06 §4.9's envelope/gondola entries migrate to 07's catalog? (06 Q8)

### B. Resource taxonomy & SKU granularity (decide before content authoring)

11. **Hypergolics endgame**: NTO/MMH stay separate (resolved); open: do T3 ISRU synthesis routes for them exist, or do hypergolics age out? (02 Q1–Q2, 04 owns)
12. **Components / Electronics granularity**: one generic `Components` vs precision/bulk split; mass penalty for local micron-class Electronics vs imported. (05 Q1–Q2)
13. **MedSupplies scope**: keep pooled, or split ECLSS spares from medicine? (08 Q3)
14. **Ethane promotion** from [LUMPED]-into-Methane if 02/05 ever want distinct C2H6. (04 Q3)
15. **Copper scarcity**: near-Earth-monopoly realism vs late-game frustration; would need a defensible anchor for asteroidal Cu micro-deposits. (04 Q2)
16. **Recycling depth**: T2 recycler module reclaiming 80% of process losses — leaning yes; needs 04 sign-off. (05 Q6)

### C. v1 scope cuts — recommend deciding "no for v1, revisit" explicitly in writing

17. **Venus crewed surface**: robots-only forever (recommended by 03/10 realism reviewers) vs T4 trophy sorties — settles VH-10, 07's packages, and an 08 interface nobody has designed. (03 Q2, 10 Q4)
18. **Sun–Earth L1/L2 anchor slots**: v1 or v1.1 — only 12 can say whether an early science-station contract line wants them. (01 Q1)
19. **Reproduction/generational scope**: is "self-sufficient civilization" purely industrial closure with recruited crew (v1 recommendation), or are births modeled? Defines the Foundation Audit. (08 Q6)
20. **Europa ocean-floor traversal, Titan human-powered flight, legged locomotion, boats/waves fidelity**: all physically specifiable, all content-thin — cut/defer candidates. (10 Q3, Q5, Q6, Q7)
21. **Replay/flight-recorder**: cheap only if the logging hook exists in the integrator from Phase 1 — decide *before* Phase 1 even though the feature ships later. (13 Q5)
22. **Comms from day one** vs stubbed until Act 2: recommend full system (naturally invisible in Earth SOI); 13 to confirm the scheduler fits the Phase-4 budget. (92-16 Q2)
23. **Plume–surface interaction** (regolith scouring) as landing-site hazard vs ignored in v1. (02 Q3)
24. **Mars atmospheric variability** (±50% seasonal/dust-coupled density): high flavor for Act 3+ aerobraking; moderate sim cost — leaning yes. (01 Q4, 03 owns climate)
25. **Lambert porkchop depth** (1D window bar vs 2-axis heatmap behind an "advanced" toggle) and EP mega-cluster (50+ strings) UI/bookkeeping. (01 Q2, 02 Q6)

### D. Simulation fidelity vs performance (decide with profiling data, not taste)

26. **Averaged-elements low-thrust propagator** for elliptical ion spirals vs ≤1,000× numeric warp fallback. (01 Q5)
27. **Thermal node budget** (≤40/base) vs Act 5 megabases — hierarchical aggregation if profiling demands. (09 Q9)
28. **Per-wheel terrain sim depth** for direct driving; **grid-scale fit** for aerostat keels and asteroid galleries; **quake fragility curves** vs severity rolls. (10 Q1, 07 Q1, Q10)
29. **Runtime numpy DSP vs pre-baked audio variants**; **parametric GPU plume mesh vs sprites**. (91-15 Q2–Q3, 90-14 Q6)
30. **Cross-platform determinism**: per-platform bit-exactness is the v1 promise; upgrading to cross-platform requires polynomial transcendentals (~2 weeks) — only if community challenge runs demand it. (13 Q9, 90-14 Q8)

### E. Balance placeholders — flagged for playtest, owners assigned

31. **Polar-site surcharge** (+500 m/s, 01 Q7 — must keep lunar polar ice attractive), **PSR thermal-pollution decay** (1%/yr gameplay number, 04 Q4), **mature-engine threshold** (25 ignitions, 02 Q10), **spares coefficients k_env** (the single biggest difficulty knob, 05 Q9), **contract SCI share** (≤25% proposal, 11 Q4), **hour targets** (zero playtest data, 12 Q5), **He3 logistics timescales** (does a fusion economy fit fun timescales at 10⁵ t regolith/kg? 11 Q9, 04 Q9), **fusion specific mass** (the endgame pacing knob, 09 Q10).

### F. Narrative & world canon

32. **The 2049 future-history timeline**: one canonical page deciding which 2026–2049 missions exist as derelicts/anomalies (Artemis assets, MSR state, Dragonfly at Selk) — blocks 03's anomaly list and 12's narrative. (03 Q5)
33. **Money endgame**: the $ ledger persisting-but-irrelevant must read as triumph, not bug; plus investor board teeth, cosmetic rival program, Chronicle text-variant budget, crew pensions. (12 Q1–Q2, Q6–Q8)
34. **Biology-question presentation**: ambiguous organics with no discovery-of-life storyline is locked doctrine; per-act presentation already specified (11 §4.11) — keep it from drifting toward aliens in content writing. (11, 12)

### G. Platform & distribution

35. **GL 3.3 core vs ES 3.0-compatible shaders** (decide before shader authoring, 90-14 Q1); **original vs licensed score** (Phase 2 budgeting, 91-15 Q1); **Steam Workshop vs folder mods** (defer, 13 Q6); **crash-triage save bundle button** (recommend yes at Phase 2, 13 Q10); **n-body "Principia mode" save-schema headroom** (recommend yes — one version field, 01 Q8).

---

*Master document ends. The sixteen domain documents are the canon; this file is the map.*
