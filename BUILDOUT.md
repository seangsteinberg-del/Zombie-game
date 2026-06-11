# APHELION v3 — THE FULL BUILD-OUT

**Directive (2026-06-11):** build every system in the 16-doc design bible in full — plus
walkable environments (surface EVA, base and station interiors), pilotable vehicles
(rovers, submarines, aircraft), land-anywhere planetary surfaces, full station building,
factories, farms, shipyards. Not a text skeleton: fully playable, "most in-depth space
game of all time." Quality bar: actually really good, not 1990s, not text-based.

**Method:** vertical chunks, each shippable — sim + data + UI + art + tests + screenshots,
committed and pushed per chunk. Specs live in `design/extracts/*-buildspec.md` (one per
bible doc, implementable without re-reading the bible). DECISIONS.md wins conflicts.

## Status board

| # | Chunk | Status | Delivers |
|---|-------|--------|----------|
| R | Research & tech | **DONE** (c3ae6b6, 5bab011) | 132-node tree (T0–T4, 10 branches), ED per-family high-water thresholds, prototyping ×3/×2 + maturation m(D), fog of research, 18 Discoveries scaffold, milestone/observation SCI sources, board UI v2 (pan/zoom branches) |
| S | Solar system v2 | **DONE** (1bc349a; deferred: ~218 procedural bodies + K0–K4 deposit prospecting → B/O chunks, h_atm reconciliation → O, site tile maps → W) | body JSON growth (atmo/thermal/radiation/sectors), ~176 curated sectors, land-anywhere sector targeting, anomaly catalog AN-01..50 + procedural, radiation v2 (f_cycle, SPE events, belts), Mars climate/dust, prospecting K0–K4 + survey instruments, SurveyData→SCI |
| B | Bases v2 | **DONE** (b77e7b7, ca8da74; deferred: placement grid + 4 utility networks → W chunk with walkable layouts, deposits/K-ladder → I, aerostat float sim → V) | placement grid, Deploy→Outfit→Commission, four utility networks, HAB-01..18/AL/AR catalog, pressure-vessel + berm rules, per-body packages (Moon night, Mars dust, Venus aerostat float, Titan cold, Europa siege), deposits + RX-01..22 ISRU recipes + extraction machines |
| G | Power & thermal v2 | **DONE** (54d45c6; deferred: full H-6 per-node T network → W layouts, reactor burnup/decay heat → Z balance) | thermal node network (H-6), grid dispatch/shedding (P-1), generation/storage/radiator catalogs, sink temps per body, failure modes |
| W | EVA & interiors | **DONE** (part 1 2425746: eva walk scene; part 2 91efb17: walkable hab interiors; part 3a 757a172: tile site-worlds core per the **Terraria directive 2026-06-11** — each landing site = persistent side-view tile world 2 km × 160 m deep, 0.5 m tiles, strata/ice lenses/ore veins/caves, canon dig rates, construction stays MODULAR, planets stay real-scale (bible S-7c); part 3b: eva scene renders cached tile chunks, walker tile collision incl. 2-tile step-up/shaft drops/roof-stopped jumps, X digs ahead / C digs down with per-type dig clocks, dug tiles + first-strike deposits persist in explore (saved), spoil credits colony Water/Regolith buffers, suit-lamp darkness underground, `--scene mine` QA) | walk the surface at any landed site/colony, dig the cross-section (veins feed the I-chunk extraction ladder), enter modules → walkable interiors, flags/samples; THE marquee feature |
| H | Humans v2 | PENDING | cabin atmosphere physics (pp gases, leaks), ECLSS ladder + LS hardware, food & agriculture (crops, greenhouses, rations), dose v2 (acute/ARS/REID), morale/medical/5 skill tracks, EVA suit loop |
| D | Drydock 2.0 | PENDING | 2D grid builder, ~110-part catalog (EP strings, solids, RCS, structure, Whipple, legs, chutes, TPS), O/F plumbing + feed groups, structural validation E1–E11 + W warns, pre-flight ascent sim panel, 4 worked-build acceptance tests, wear/ignition gates |
| T | Stations | PENDING | port-based assembly, spin-gravity rings (comfort bands), station interiors (walkable), depots + boiloff economy + transfer ops, stationkeeping fees, MMOD |
| I | Industry | PENDING | production chains (Electronics long pole), fab modules, labor ledger + automation ladder A0–A4 + robots, shipyards (BERTH→COMMISSION, learning curve), mass drivers, freighter-route planner UI, spares/wear economy (F-7/F-9) |
| V | Vehicles | PENDING | rovers/hoppers/rotorcraft/aerobots/Titan submarine/Europa cryobot: V-0..24 physics, pilotable scenes (drive/fly/dive), traverse science, calibration fixtures (LRV 88 km, Ingenuity 335 W, SUB-T 330 W) |
| C | Comms | PENDING | Friis rate law + calibration (MRO/Voyager/DSOC), comms graph + routing, antenna/relay catalog, bandwidth buffers + downlink scheduler, conjunction/EDL blackouts, teleop gating, science-delivery gate, network overlay |
| O | Orbital v2 | PENDING | Lambert windows + porkchop (advanced toggle), finite burns + thrust warp (RKF45), aerocapture/EDL corridor advisor + TPS consumption, gravity-assist planner, L-point anchors, multi-node chains, polar surcharge |
| E | Campaign v2 | PENDING | 5 acts + endgame, 25 contract templates + 38-row Firsts ladder + charters, Prestige, investors/insurance/stand-downs/rescues, rate-based money ledger, SSI + Foundation Audit + Precursor (10 AU/yr), alert bus (4 classes, warp caps), Chronicle + export, births (C19) |
| F | Presentation v2 | PENDING | per-world identity cards, per-propellant plume optics, bloom/grain canon fixes, star catalog, photo mode + Chronicle print filters, 3-voice alarm grammar, ambience-as-instrumentation, per-world beds, act-based score, accessibility |
| Z | Hardening | PENDING | perf scenes P1–P5, save header + migration harness, autosave rotation + crash bundle, determinism CI, golden saves, exe rebuild, README v3 |

Statuses: PENDING → IN PROGRESS → DONE (commit hash). Update this table every chunk.

## Build order rationale

R first (user's #1 complaint: "nothing to research"). S unlocks land-anywhere + the
sector substrate every later chunk needs (vehicles, prospecting, anomalies). B gives
bases real layouts; W then walks them (walk mode needs module positions, so B before W).
G is B's power/thermal half, split for size. H deepens the people inside what W shows.
D rebuilds the builder around the full catalog; T assembles those parts into stations;
I industrializes (its wear/spares model is shared with D's engines and V's vehicles);
V rides on S's terrain + I's wear; C gates V's teleop and S's science return; O finishes
flight; E re-frames everything into the five-act campaign; F makes it look/sound like
the bible; Z hardens for release.

## Standing rules

- Every chunk: pytest suite green (no skips), `--scene` QA hooks + screenshots for new
  scenes, deterministic (seeded rng, no wall clock), headless-safe, commit + push.
- Numbers come from the extract, which carries the bible's canon. Cite formula IDs
  (V-7, P-4, H-6, F-9, RX-04…) in code comments so canon stays traceable.
- Content is data (`data/core/...`), not code. Schema-validate at load; validation
  failure = boot failure.
- main.py integration is done solo (no parallel agents editing main.py). Fan-out is for
  audits/extractions/art only.
- Update BUILDOUT.md status + memory after each chunk lands.
