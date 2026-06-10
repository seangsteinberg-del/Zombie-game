# APHELION — Design Decision Log

Rulings on the 35 bible-wide open questions (design/README.md §7). Ratified by the Director, 2026-06-10.
Status legend: **DECIDED** (binding now — docs must conform) · **DEFAULTED** (binding unless profiling/playtest overturns at the named gate) · **DEFERRED** (explicitly out of v1; revisit note attached).

## A. Canon reconciliation — all DECIDED, apply in one pre-code cleanup pass

| # | Ruling | Affected docs |
|---|---|---|
| A1 | Canonical spelling is **`RP1`** (no punctuation in resource IDs). 12 §4.3 gains the missing NTO/MMH price rows. | 06, 12 |
| A2 | **Byte-identical shared-numbers audit**: one cleanup pass; on any diff the owning doc wins (01 Δv · 03 bodies · 02 engines · 08 crew · 09 power/thermal curves · 16 link rates). | 02,03,04,07,08,09 |
| A3 | **GCR floor decays** past ~1,000 g/cm²: 08 publishes the decaying-floor extension (physically correct; thick-atmosphere/deep-ice sites keep improving). Materially upgrades belt/Europa endgame habitability. | 08, 07, 03 |
| A4 | Radiation model uses **piecewise-exact anchors**, not a smooth fudge. Honesty doctrine outranks elegance. | 03 |
| A5 | **One wear model**: 02 per-ignition/wear base × 11 maturity factor × 05 spares/MTBF consumption — orthogonal multipliers, no double counting. Ship as an interface test in Phase 1. | 02,05,06,10,11 |
| A6 | Aerostats: **robotic platforms T2, crewed habitat (HB-05) T3**. 11 §3.3 sums rebalanced accordingly. | 07, 11 |
| A7 | **F3 = Planner** (player-facing binding wins). Perf HUD → **Ctrl+F3**. | 12, 13, 90-14 |
| A8 | Engine catalog: **accept all three registrations** — Bantam-class methalox pair, argon Hall string, pump-fed methalox lander row. 02 to publish stats. | 02, 06, 10 |
| A9 | **Skyhook tip = standard orbital node with Δv discount**; momentum ledger owned by 05; 01 provides state only. `bot_mule` single data row confirmed (05 owns). | 01, 05, 10 |
| A10 | Aerostat envelope/gondola hardware **migrates from 06 §4.9 to 07's catalog** (07 owns habitats). 06 keeps a pointer. | 06, 07 |

## B. Resource taxonomy — DECIDED

| # | Ruling |
|---|---|
| B11 | Hypergolics get **T3 ISRU synthesis routes** (Ammonia→MMH; Nitrogen+Oxygen→NTO) as chem-plant recipes (04 owns). They never age out; storables keep their niche. |
| B12 | **Single `Components` SKU** stays. Locally-fabbed micron-class Electronics carry a **×1.3 mass penalty** vs Earth imports until T3+ fab maturity. |
| B13 | `MedSupplies` **stays pooled** in v1. |
| B14 | Ethane **stays [LUMPED]** into Methane (0.93×) until a consumer system demands C2H6. |
| B15 | **Copper stays realistically near-Earth-scarce.** No invented asteroid Cu deposits. Late-game pressure relieved via B16 recycling, not fake geology. |
| B16 | **T2 recycler module approved**: reclaims 80% of process losses; 04 to add the recipe row. |

## C. Scope — Director ratified

| # | Ruling | Status |
|---|---|---|
| C17 | **Venus crewed surface sortie: IN as T4 [SPECULATIVE] trophy** — a single short-duration crewed sortie in a cooled suit-vehicle, endgame achievement tier. 07/08/10 design the interface at Pass 2; honest speculation tag mandatory. | DECIDED |
| C18 | Sun–Earth **L1/L2 anchor slots in v1** (cheap on-rails slots; enables early science-station contracts). | DECIDED |
| C19 | **Births & generations: MODELED.** Self-sufficiency includes biological continuity, not just industrial closure. Partial-gravity reproduction is unknown science → the game models the *uncertainty itself*: research arc (centrifuge studies, mammalian trials → human protocols), gravity-threshold discoveries, spin-habitat prescriptions. Foundation Audit gains a demographic pillar. Major 08 expansion — design in Pass 2; implementation lands Phase 6+. | DECIDED |
| C20 | **Entire exotic-vehicle bundle stays in v1**: Titan human-powered flight, Europa ocean-floor traversal, legged locomotion, boats with wave model. Phase 5 scope grows accordingly — accepted knowingly. | DECIDED |
| C21 | **Replay/flight-recorder logging hook built into the Phase 1 integrator** (feature ships later). | DECIDED |
| C22 | **Comms system live from day one** (naturally invisible inside Earth SOI; becomes load-bearing at the Moon). 13 confirms scheduler budget at Phase 4 gate. | DECIDED |
| C23 | **Plume–surface scouring IN** as a simple landing-site hazard (drives landing-pad construction gameplay). Simple cone/threshold model only. | DECIDED |
| C24 | **Mars atmospheric density varies ±50%** with season/dust — aerobraking corridors are live operations from Act 3. 03 owns climate curves. | DECIDED |
| C25 | Transfer planning: **1D window bar default + full 2-axis porkchop behind an "Advanced" toggle**. EP mega-clusters: **per-bank bookkeeping** (not per-string). | DECIDED |

## D. Fidelity vs performance — DEFAULTED (overturn only with profiling data, at the named gate)

| # | Default | Gate |
|---|---|---|
| D26 | Low-thrust elliptical spirals: **numeric ≤1,000× warp fallback**; averaged-elements propagator only if Phase 4 profiling demands. | Phase 4 |
| D27 | Thermal: **≤40 nodes/base**; hierarchical aggregation deferred until a real Act 5 megabase exceeds budget. | Phase 5 |
| D28 | Driving: **terrain-class/slope model, not per-wheel**. Aerostat keels & asteroid galleries: **fit grid scale**. Quakes: **severity rolls**, not fragility curves. | Phase 5 |
| D29 | Audio: **pre-baked variants** (no runtime DSP). Plumes: **parametric GPU mesh** with sprite fallback toggle. | Phase 2/3 |
| D30 | Determinism: **per-platform bit-exactness is the v1 promise**; cross-platform polynomial transcendentals only if community challenge-runs demand. | post-v1 |

## E. Balance placeholders — all stay as written, tagged [PLAYTEST], owners per README §7.31
Polar surcharge +500 m/s · PSR decay 1%/yr · mature-engine 25 ignitions · k_env spares coefficients (primary difficulty knob) · contract SCI ≤25% · hour targets · He3/fusion pacing (revisit at Phase 6 gate with 09 Q10 fusion specific mass).

## F. Narrative & world canon

| # | Ruling |
|---|---|
| F32 | **2049 future-history timeline: commissioned** — one canonical page (03 appendix): which 2026–2049 missions exist as derelicts/anomalies (Artemis assets on Luna, stranded MSR sample cache at Jezero, Dragonfly silent at Selk, etc.). Blocks 03 anomaly list + 12 narrative; write before Pass 2. |
| F33 | **Money endgame reads as triumph**: $ ledger persists but fades per 12; investor board becomes advisory post-self-sufficiency; cosmetic rival program IN; crew pensions IN (flavor-cost). |
| F34 | **Doctrine reaffirmed**: ambiguous organics only — the biology question is never answered, no aliens, ever. Content writers hold the line per 11 §4.11. |

## G. Platform & distribution

| # | Ruling |
|---|---|
| G35a | Shaders target **GL 3.3 core** (desktop-only v1). |
| G35b | Score: **original minimal-ambient**, budget decision confirmed at Phase 2. |
| G35c | **Folder mods v1**; Steam Workshop deferred. |
| G35d | **Crash-triage save-bundle button: yes**, Phase 2. |
| G35e | **n-body "Principia mode" headroom: yes** — one reserved save-schema version field, Phase 1. |

---

**Consequences register (from the Director's three maximalist calls):**
- C17 adds a T4 design item to 07/08/10 (Pass 2).
- C19 is the largest scope addition since the bible was written: 08 gains demographics/reproduction-research systems; 11 gains the gravity-biology research arc; 12's Foundation Audit gains a demographic pillar.
- C20 commits Phase 5 to four extra vehicle systems; the wave model and ocean-floor traversal are the heavy items.

*Next actions: (1) canon cleanup pass applying A1–A10 + B16 recipe + the F32 timeline page; (2) Pass 2 expansion incorporating C17/C19/C20 scope.*
