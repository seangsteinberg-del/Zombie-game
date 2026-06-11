# BUILD SPEC — Doc 16: Communications & Light-Lag Networks

Source: `design/92-16-communications-networks.md` (doc 16). Conflicts resolved by `design/DECISIONS.md`.
DECISIONS that bind here: **C22** (comms system live from day one — no Act-2 stub path; 13 confirms
scheduler budget at Phase 4 gate), **A2** (doc 16 owns all link-rate numbers in any cross-doc diff),
**A7** (F3 opens the Planner — the network overlay lives there).

Doc 16 owns: the link-rate law, the antenna/relay/ground-station part catalog, bandwidth-as-resource,
the blackout catalog, operations link doctrine, DSN lease stats. It does NOT own: graph/LOS/occlusion/
Dijkstra/RTT (13 §3.11, consumed verbatim), η_teleop (05 F-2), control modes (10 §3.8), SCI/ED amounts
(11), money/alerts/difficulty (12), ephemerides/light-time (01/03).

All SI: distance m, power W (RF/optical emitted; electrical draw separate, kWe), rate bit/s, volume bit
(UI shows Mbit/Gbit/Tbit). `c = 299_792_458 m/s` (already `aphelion.core.units.C_LIGHT`).

---

## 1. THE RATE LAW

### 1.1 Antenna gain (L-2)

```python
LAMBDA_RF  = 0.0357     # m  (X-band class, 8.4 GHz — ALL game RF is modeled at this wavelength)
LAMBDA_OPT = 1.55e-6    # m
ETA_AP_RF  = 0.6        # parabolic aperture efficiency, RF dishes ONLY

def gain_rf_dish(d_m):  return 0.6 * (math.pi * d_m / LAMBDA_RF) ** 2
def gain_optical(d_m):  return (math.pi * d_m / LAMBDA_OPT) ** 2   # diffraction limit, eta = 1.0
```

- Optical implementation losses (pointing, photon-counting detection, sky background) live in
  `K_opt` ONLY — never in the gain. The DSOC calibration must reproduce from catalog gains as printed.
- Omnis: G = 1 (0 dBi) by definition. CM-PROX: G = 100 (20 dBi) quoted directly (UHF helix/patch
  array, not a parabola — do not aperture-derive it).
- Catalog G values (§2) are precomputed from these rules; store them as data, but a test must
  re-derive the dish rows from D.

### 1.2 Directed link rate (L-3) — THE formula

For transmitter part `t` on node a, receiver part `r` on node b, distance d (m), when the 13 §3.11
link exists:

```python
K_RF  = 3.0e15   # bit·m²/(s·W)  — calibrated MRO -> DSN-34
K_OPT = 3.2e3    # bit·m²/(s·W)  — calibrated DSOC -> Palomar 5 m

def link_rate(P_t, G_t, G_r, d, K, rmax_t, rmax_r):
    return min(rmax_t, rmax_r, K * P_t * G_t * G_r / d**2)   # bit/s
```

- `P_t` = transmit power in W of **emitted** RF/optical (not electrical draw).
- `R_max` = per-part modem/detector cap (hardware limit, catalog column).
- RF parts pair only with RF parts; optical only with optical. K absorbs noise temp, coding, margins.
- Rate and latency are independent (L-1): RTT stays 13's `2·path_length/c`. A Neptune link with 8 h
  RTT can still be a fat pipe.

**Mandatory calibration tests (programmer must reproduce):**

| Check | Inputs | Expected |
|---|---|---|
| MRO | P=100 W, G_t=4.2e4 (3 m), G_r=5.4e6 (DSN 34 m), d=1 AU=1.496e11 m | **3.0 Mbit/s**; over 0.37–2.68 AU spans 22→0.42 Mbit/s, R_max=6 Mbit/s clips close end |
| Voyager | P=23 W, G_t=6.4e4 (3.7 m), G_r=2.28e7 (DSN 70 m), d=160 AU | **175 bit/s** (real: ~160); 5.0 kbit/s at 30 AU |
| DSOC | P=4 W, G_t=1.99e11 (22 cm opt), G_r=1.03e14 (5 m), d=0.21 AU | **267 Mbit/s** exact; 5.2 Mbit/s at 1.5 AU |

### 1.3 Rated range / link existence (L-4) — derives 13's binary rule

```python
R_FLOOR_RF  = 8.0      # bit/s   (DSN 7.8125 bit/s min command rate)
R_FLOOR_OPT = 1000.0   # bit/s   (photon-counting acquisition floor — no optical "trickle mode")

def rated_range(P, G, K, r_floor):
    return math.sqrt(K * P * G**2 / r_floor)    # m, per part

# Link a<->b EXISTS iff LOS (13) and d <= sqrt(R_a * R_b)   — 13's rule, now derived:
# sqrt(R_a*R_b) is the geometric mean of the two directed floor distances.
```

- Any existing link carries ≥ its band's command floor (geometric-mean sense). Directed asymmetry
  is real and displayed (20 kW DSN uplink reaches an omni far beyond the omni's useful downlink).
- Worked rated ranges (test fixtures): CM-OMNI 4.3e7 m; CM-PROX 6.1e9 m; UT-DISH-M 8.1e12 m (54 AU);
  DSN-34 1.5e16 m. Mixed: omni↔DSN-34 closes at √(4.3e7·1.5e16) ≈ 8.0e11 m ≈ **5.3 AU**.
- Proximity legs are a *rate* story: rover omni → areo relay omni at 17,000 km EXISTS but carries
  ~52 bit/s (P0 only). CM-PROX↔CM-PROX at same range ≈ 1.0 Mbit/s, R_max-capped 2 Mbit/s inside
  ~12,000 km — the Electra envelope. CM-PROX is mandatory fit on every TELEOP/A2 vehicle and relay bus.

### 1.4 Band table (game model)

The game models **two physical bands**; UHF/S/Ka realism is folded into per-part `R_max` and K_RF
(doc 16 §2 note; Ka/arraying as separate tech is open question Q5 — NOT in v1).

| Band (model) | λ | K | Floor | Typical R_max | Penalties |
|---|---|---|---|---|---|
| RF (UHF/S/X/Ka folded) | 35.7 mm | 3.0e15 | 8 bit/s | omni 256 kbit/s · prox 2 Mbit/s · dishes 2–50 Mbit/s · DSN 150 Mbit/s | SPE ×0.5 outside magnetospheres (L-8); conjunction <2°/<5° (L-7); weather-immune |
| Optical | 1.55 µm | 3.2e3 | 1 kbit/s | 267 Mbit/s–1.2 Gbit/s | Earth ground availability ×0.5 (scheduled pre-rolled outages, L-15); Mars ground suspended in dust storms; SPE-immune; conjunction NOT bypassed (Sun-avoidance, L-7) |

### 1.5 Pointing / scheduling rules (L-5)

- One antenna part = **one directed link at a time** (scheduler assigns). Multi-antenna nodes run one
  link per antenna (relay pattern: prox omni + Earth trunk simultaneously is legal — two parts).
- P0 command floor is preemptively available on any existing link, never scheduled.
- Multi-hop path rate = min over hops of directed hop rate; RTT = sum of hop light times.
- Live classes (P0, P2 teleop) need the whole path up simultaneously. Bulk (P1/P3/P4) moves
  hop-by-hop via store-and-forward if the relay has recorder capacity; no recorder = bent-pipe only.

---

## 2. HARDWARE CATALOG

All parts build-class ELEC (recipe 0.40 Electronics + 0.30 Aluminum + 0.20 Copper + 0.10 MachineParts).
Prices are 2049 baselines, $M (12 owns evolution). RF draw from TWTA efficiency 0.3; optical heads ~5%.

### 2.1 Antennas & terminals (vessel/vehicle mounts, 06/10 by ID)

| ID | Name | Tier | Mass | Draw kWe | Band | P_tx W | G | R_max | Rated range | $M |
|---|---|---|---|---|---|---|---|---|---|---|
| CM-OMNI | Omni (integrated in UT-AV/UT-AVS; standalone for vehicles/relays) | T0 | 5 kg | 0.02 | RF | 5 | 1 | 256 kbit/s | 4.3e7 m | 0.05 |
| CM-PROX | Proximity medium-gain (UHF helix/patch) | T0 | 8 kg | 0.04 | RF | 10 | 100 | 2 Mbit/s | 6.1e9 m | 0.15 |
| UT-DISH-S | High-gain dish 0.5 m | T0 | 20 kg | 0.05 | RF | 10 | 1.16e3 | 2 Mbit/s | 7.1e10 m | 0.4 |
| UT-DISH-M | High-gain dish 3 m (MRO HGA class) | T0 | 90 kg | 0.35 | RF | 100 | 4.2e4 | 6 Mbit/s | 8.1e12 m | 2.0 |
| UT-DISH-L | Deployable mesh dish 10 m | T2 | 400 kg | 0.70 | RF | 200 | 4.6e5 | 50 Mbit/s | 1.3e14 m | 8.0 |
| OPT-1 | Optical terminal 22 cm (DSOC class) | T2 (GN-06) | 30 kg | 0.10 | opt | 4 | 1.99e11 | 267 Mbit/s | 7.1e11 m† | 12 |
| OPT-2 | Optical terminal 50 cm | T3 | 80 kg | 0.25 | opt | 10 | 1.03e12 | 1.2 Gbit/s | 5.8e12 m† | 25 |

† Optical rated ranges are self-pair values at the 1 kbit/s acquisition floor; real reach comes from
ground apertures: OPT-1↔GS-OPT-5 closes at ≈ 2.4e13 m ≈ **160 AU**, 5.2 Mbit/s at 1.5 AU.

- UT-AV avionics core integrates 1× CM-OMNI + **16 Gbit** buffer; UT-AVS integrates CM-OMNI + **4 Gbit**.
- CM-PROX is never integrated — explicit mount on rovers/landers/relay buses.
- UT-DISH-L carries a one-time deployment failure roll (F-2): jam → operates at G = 100 (Galileo
  mode); repair = 8 crew-h EVA or A2 robot task + 0.1 t MachineParts. Ship validator W-class warning
  for any deep-space design whose only Earth-class link is a single deployable HGA ("Galileo check").

### 2.2 Ground / base stations (07 surface-grid modules)

| ID | Name | Tier | Mass | Draw kWe | Band | P_tx | G | R_max | Rated range | $M |
|---|---|---|---|---|---|---|---|---|---|---|
| GS-12 | Ground station, 12 m dish | T1 | 25 t | 15 | RF | 2 kW | 6.7e5 | 200 Mbit/s | 5.8e14 m | 20 |
| GS-OPT-5 | Optical ground terminal, 5 m | T2 (GN-06) | 40 t | 25 | opt | 20 | 1.03e14 | 1.2 Gbit/s | 8.2e14 m | 45 |
| core:dsn 34 m | lease only | — | — | — | RF | 20 kW | 5.4e6 | 150 Mbit/s | 1.5e16 m | §2.5 |
| core:dsn 70 m | lease only | — | — | — | RF | 20 kW | 2.28e7 | 150 Mbit/s | 6.2e16 m | §2.5 |

- `core:dsn` = 13's always-on root node (three complexes 120° apart abstracted: never Earth-rotation
  occluded). The 70 m's edge is aperture, not power; its real 400 kW emergency uplink is modeled as a
  P0-floor-only state, never in scheduled rates. DSN optical tier appears T2+ once GN-06 exists anywhere.
- Player GS-12 / GS-OPT-5 sit on rotating Earth → 13's LOS occludes them ~50%/day (that is WHY DSN has
  three complexes; building 2–3 spaced player stations is the mid-game emancipation move).
- Same GS parts on other bodies serve base trunks; 07's site network (wireless ≤10 km, masts) is the
  layer below.

### 2.3 Data recorders (buffers)

| ID | Tier | Mass | Draw kWe | Capacity | $M |
|---|---|---|---|---|---|
| (integrated UT-AV / UT-AVS) | T0 | — | — | 16 / 4 Gbit | — |
| DR-1 solid-state recorder | T0 | 5 kg | 0.05 | 256 Gbit | 0.5 |
| DR-2 bulk archive recorder | T2 | 20 kg | 0.10 | 4 Tbit | 1.5 |

### 2.4 Reference relay blueprints (06 blueprint format)

| Blueprint | Tier | Parts | Wet mass | Role |
|---|---|---|---|---|
| "Heliograph" | T1 (GN-03) | UT-AVS + CM-OMNI + CM-PROX + UT-DISH-S + DR-1 + 1 kWe solar + RCS | 0.36 t | Lunar ring unit cell: 2 Mbit/s prox legs, UT-DISH-S Earth trunk (capped 2 Mbit/s in Earth SOI; only ~8.4 kbit/s at 1 AU — not interplanetary), DR-1 store-and-forward, omni P0 crosslinks |
| "Heliograph-A" | T1 (GN-03) | UT-AVS + CM-OMNI + CM-PROX + UT-DISH-M + DR-1 + 2 kWe solar + RCS | 0.50 t | Areostationary trio cell: ~1 Mbit/s prox legs; UT-DISH-M Earth trunk 0.42–6 Mbit/s by season |
| "Pharos" | T2 | UT-AV + UT-DISH-L ×2 + DR-2 + 3 kWe solar + RCS | 2.4 t | Conjunction-bypass deep relay: ~1.2 Mbit/s per leg at 2.2 AU, both directions simultaneously (two dishes) |
| "Lighthouse" | T3 (GN-06) | UT-AV + OPT-2 ×2 + UT-DISH-S (RF fallback — Galileo lesson) + DR-2 ×2 + 5 kWe solar | 2.0 t | 0.2–40 Mbit/s optical backbone legs between planets; always carries RF fallback |

All relays pay stationkeeping per 01 Table 4.8 (flat 2 m/s/yr class). All comms parts accrue
Avionics-family ED (11 family 22) and ride 06's part-event failure machinery.

### 2.5 DSN lease tiers (stats here; pricing evolution/contracts → 12)

| Service | Price (2049) | Notes |
|---|---|---|
| 34 m antenna-hour | $1,100/h | anchor: NASA aperture fee ≈ $1,057/h FY2015 |
| 70 m antenna-hour | $4,400/h | aperture weighting ×4 |
| Optical ground network hour | $2,500/h | T2+, after GN-06 researched |
| HQ allocation | **2 h/day on 34 m, FREE** | sponsored-mission status; covers Acts 1–2 |
| Standing lease | per 12 E-12 contract | auto-scheduled passes |

Leases buy antenna-hours via the Planner; the scheduler converts a lease into PASS_START/END events.

---

## 3. NETWORK MECHANICS

### 3.1 Graph (consumed from 13 §3.11 — do not redefine)

Nodes (≤ 300 cap), 2D LOS test, event-driven rebuild + 60 s cadence, Brent-predicted occlusion
windows, Dijkstra routing, `core:dsn` root, frame budget 0.2–0.3 ms. Doc 16 supplies: per-part `R_x`
(rated range) feeding 13's `d ≤ √(R_a·R_b)`; rate evaluation as one vectorized numpy pass over live
links piggybacked on the rebuild.

`CommsNode` component gains fields (save-schema versioned): `parts: [comm part uids]`, `buffer_bits`,
`buffer_cap_bits`, `queue: per-class volumes`. Buffers serialize as plain ledger floats.

New event types in 13's queue: `CONJ_IN/OUT`, `LINK_DEGRADED_IN/OUT` (SPE/weather), `PASS_START/END`,
`BUFFER_FULL/EMPTY`, `NODE_OPS_HOLD` (`OCCLUSION_IN/OUT` exists). Determinism: scheduler order =
(class, queue timestamp, uid); weather outages pre-rolled from `rng("comms")` substream — no rerolls
on reload.

### 3.2 Bandwidth as a resource (L-6, L-14, L-10)

**Buffer ledger (L-6).** `dB/dt = Σ generation − Σ scheduled drain`, piecewise-constant rates between
events (13 §3.9 analytic-ledger contract — nothing polls). BUFFER_FULL/EMPTY crossings predicted
analytically. At full: **generators pause** (instruments idle; data is never silently lost) + F-3 flag.

**Priority classes (L-14)** — drain strictly by class, FIFO within:

| Class | Traffic | Notes |
|---|---|---|
| P0 | command / safe-mode / go-no-go | fits the 8 bit/s floor; always on, never scheduled |
| P1 | housekeeping telemetry, failure bursts | feeds 11 ED rules |
| P2 | teleop / live-ops reservation | reserves L-13 rate during a shift; not buffered |
| P3 | science data, survey products | feeds 11 transmit-path awards |
| P4 | Chronicle media, low-value bulk | first to starve |

**Canonical data volumes (L-10)** — doc 16 owns these numbers:

| Source | Volume / rate | Class |
|---|---|---|
| Housekeeping telemetry | 200 bit/s per powered comms node, continuous | P1 |
| Failure burst (investigated failure, 11 §3.2) | 2 Gbit queued at failure; **must be delivered ≤ 30 days** for the ED bonus; counts on landing, not queueing; EDL bent-pipe tones count even if vehicle destroyed | P1 |
| Science, transmit path | **10 Gbit per SCI point**, queued at acquisition | P3 |
| Orbital/ground survey product | 10 Gbit per SCI of the one-shot (50-SCI Mars survey = 500 Gbit ≈ 17 days at 8 h/day leased 34 m at 1.7 AU) | P3 |
| A2 BATCH sol cycle | 20 Mbit up + 800 Mbit down per cycle | P2 |
| TELEOP session | live reservation only, no volume | P2 |
| Chronicle auto-shot | 50 Mbit each | P4 |

**Science crediting (the teeth, conforming edit to 11 §9):** transmit-path awards (M_analysis = 0.40
in-situ, survey one-shots, observation trickles) credit **only when the data volume lands at Earth or
any crewed Lab module**. Pool depletion S_n stays assigned at acquisition (11 untouched); only the
crediting moment moves. Sample return = mass carrier, no downlink.

### 3.3 Blackout catalog (all via 13's event queue)

| Rule | Blackout | Mechanic |
|---|---|---|
| **L-7 conjunction** | Endpoint is solar-blinded when angular separation (peer vs Sun, seen from that endpoint) **< 2° → link down; < 5° → rate ×0.1**. Applies to RF AND optical (optical does NOT bypass conjunction — only relay geometry does). Window edges via Brent on (separation − threshold); events CONJ_IN/OUT. Tested **per endpoint per direction** (uplink can be blinded while downlink is clear). |
| **L-8 SPE [GAME MODEL]** | During 03 S-8 SPE: every RF link with a segment outside a planetary magnetosphere runs ×0.5. Optical unaffected (deliberate tuning lever selling GN-06; honesty-tagged). |
| **L-9 EDL plasma** | While 01 §3.11 stagnation heat flux q̇ > 50 kW/m²: entering craft's direct links down; a relay overhead receives **P0 tones only** (8 bit/s) through the wake; full telemetry buffers and drains after blackout. Park-a-relay-before-you-land doctrine. |
| Body occlusion | 13 canon, unchanged (farside passes, terrain horizon, under-ice). |
| **L-15 optical weather** | Earth ground optical: availability 0.5 as scheduled pre-rolled outages (`rng("comms")`). Mars ground optical suspended entirely during dust storms (DUST_STORM_IN/OUT). RF immune. Airless bodies: full availability. |

**Conjunction season geometry (2D, derived not tuned).** Elongation sweep rate near conjunction:
`ω_syn · r/(r+1)` (superior) or `ω_syn · r/(1−r)` (inferior), ω_syn = 360°/synodic period, r = body
heliocentric AU. Hard window = 4°/rate; degraded total = 10°/rate.

| Body (vs Earth) | Synod | Sweep °/d | Hard blackout | Degraded total |
|---|---|---|---|---|
| Mars superior | 780 d | 0.28 | **~14 d / 26 mo** | ~36 d |
| Venus superior / inferior | 584 d | 0.26 / 1.61 | ~15.5 d / ~2.5 d | ~39 d / ~6 d |
| Mercury superior / inferior | 116 d | 0.87 / 1.96 | ~4.6 d / ~2.0 d (×3/yr) | ~11.5 d / ~5 d |
| Jupiter | 399 d | 0.76 | ~5.3 d | ~13 d |
| Saturn | 378 d | 0.86 | ~4.6 d | ~11.5 d |

2D coplanarity makes inferior conjunctions always hit 0° elongation (more blackouts than reality —
accepted artifact, 01 limitations table). Planner posts a **Class-3 alert at T−30 d** with the
pre-conjunction checklist (suspend teleop shifts / confirm A3 queues / top off uplinked plans).

### 3.4 Light-lag gameplay (consumed canon + this doc's additions)

- RTT = 2·path/c summed along relay path (13). Earth–Moon 2.56 s; Earth–Mars best 6.1 min.
- `η_teleop = 1/(1 + RTT/T_atom)` — 05 F-2, T_atom values from 05, refusal at η < 0.2. Already in
  code (`comms.py`, T_atom 26 s, canon rows 2.6 s → 0.91, 372 s → 0.063).
- **L-13 TELEOP requirement (new):** live path ≥ **0.5 Mbit/s** (P2 reservation; METERON anchor)
  AND η ≥ 0.2 AND relay legs CM-PROX-class or better (omni legs are P0-only). On loss: safe-halt
  per 10 §3.8; shift pauses on 13's window machinery, extended to unplanned losses (F-1: Class-2
  alert, remaining operator-hours forfeit on 05's labor ledger).
- **L-11 operations doctrine:** uncrewed T0–T1 node ops (dock/undock/burn/cargo-start) need a floor
  path **at event time** (go/no-go, light-lag irrelevant) — else auto-hold, retry next window, route
  replan, NODE_OPS_HOLD Class-3 escalating Class-2 if a burn window expires. T2+ avionics: no link
  needed. A2 BATCH: one 20 Mbit up + 800 Mbit down session per cycle (≈13 min/sol on a 1 Mbit/s areo
  prox leg); missed cycle = robot idles that sol. AUTONAV/A3: floor at dispatch/arrival; exceptions
  page humans only when a path exists, else queue (uncleared exceptions idle the robot). A4/crewed: none.
  EDL: autonomy mandatory during L-9.
- **D-2 difficulty toggle** bypasses RTT penalties ONLY (η ≡ 1, no input-delay ghost, no refusal).
  Link existence, rates, buffers, blackouts, node-ops requirements, DSN fees, A2's 0.35 km/sol cap
  (autonomy hardware, not light-lag) all stay on in every preset. RTT still displayed truthfully.

### 3.5 Relay constellation design loop (2D coverage math, binding worked examples)

Relays are ordinary 06 vessels on 01 conics; coverage falls out of 13's occlusion machinery — **no
new solver**. Surface visibility arc per relay at orbit radius r about body radius R:
`2·arccos(R/r)`; continuous ring coverage needs arc > 360°/N. Earth-occlusion fraction per orbit:
`arcsin(R/r)/π`.

1. **Lunar farside ring (Act 2).** No EML-2 halo in 2D (collinear point sits exactly behind the
   Moon). Honest solution: **3 Heliographs, 5,000 km circular lunar orbit, 120° phased** (8.8 h
   period). Visibility arc 2·arccos(1737/5000) = 139° > 120° → continuous farside coverage. Prox
   legs 14–28 Mbit/s computed, capped 2 Mbit/s ≥ teleop floor. Each bird Moon-occluded from Earth
   11.3%/orbit; omni crosslinks (8,660 km) carry ~200 bit/s = P0 continuity only; bulk rides DR-1
   store-and-forward (≤ 1 h occluded buffers ≤ 7.2 Gbit at 2 Mbit/s ingest ≪ 256 Gbit). ~1.1 t to LLO.
2. **Mars areostationary trio (Act 3).** r_areo = (μ_M·T²/4π²)^(1/3) = 20,430 km (T = 24.623 h,
   μ = 4.2828e13). 3 Heliograph-A at 120°; arc 2·arccos(3396/20430) = 161° > 120°. Prox legs ~1.0
   Mbit/s nadir (0.74 at horizon slant — above teleop floor). Omni crosslinks 35,400 km ≈ 12 bit/s
   = P0 only; Earth-occlusion ≤ 5.3% of sol rides DR-1. Each bird: UT-DISH-M Earth trunk 0.42–6
   Mbit/s by season.
3. **Conjunction-bypass Pharos (Act 3–4).** 1.0 AU heliocentric orbit phased ±60° from Earth (plain
   conic; it IS the Sun–Earth L4/L5 region). At Mars superior conjunction, Mars→relay→Earth clears
   the Sun by 0.6 AU. With UT-DISH-L on the Mars end into the Pharos dish: Mars→relay 2.20 AU ≈
   1.17 Mbit/s; relay→Earth 1.0 AU = 67 → capped 50 Mbit/s; **path ≈ 1.2 Mbit/s through the
   blackout** (each hop computed with its actual receiver, not DSN gain). Against stock UT-DISH-M
   only ~54 kbit/s. Two relays at ±60° cover every superior conjunction of every body forever.

### 3.6 Store-and-forward (L-5 bulk + F-10)

A relay with DR capacity ingests bulk (P1/P3/P4) on one hop, holds across occlusion/blackout, drains
on the next window. No recorder = bent-pipe (live rules). Failure-burst/contract deadlines: data
sitting on a relay whose next drain window misses the deadline counts undelivered — the scheduler's
analytic projection flags this **at queue time** (Class-3), not at the deadline.

### 3.7 UI (12 owns frames; F3 = Planner per DECISIONS A7)

- **S-02 network overlay** on the System Map: node health badges; links colored by rate (log scale:
  green ≥ 1 Mbit/s, yellow < 1, red = floor-only, grey dashed = occluded/scheduled-out); shaded 2°/5°
  conjunction sectors about the Sun; 03's light-lag isochrones reused.
- **Link inspector**: directed rate both ways with L-3 terms itemized (hover any number for its
  equation), RTT, 48 h occlusion/pass strip, binding constraint named (gain/cap/blinded).
- **Downlink scheduler panel** (vessel/site tab): buffer gauge + analytic time-to-full, per-class
  queues, assigned passes, drag-reprioritize within class, "lease more DSN time" shortcut.
- **Pre-conjunction checklist** (T−30 d Class-3); **teleop console** adds rate vs 0.5 Mbit/s and the
  shift occlusion timeline; buffer % on every vessel context panel.
- Alerts (12 A-1): Class 2 — UNPLANNED_RELAY_LOSS in live ops, burn-window expiry, science stall
  > 7 d; Class 3 — NODE_OPS_HOLD, BUFFER ≥ 80%, CONJ T−30 d, LINK_DEGRADED. No comms event is Class 1.

### 3.8 Anti-softlock invariants (F-3, F-7)

- The P0 floor exists on any link by construction → a commandable asset can always be told to point
  home / deorbit / rendezvous. Bandwidth can stall progress, never strand the campaign.
- No-link + no-autonomy assets enter SAFE (sun-pointed, beacon at floor when a path next exists);
  recovery = build the link or fly there. UI refuses dispatch plans whose required link windows don't
  exist at plan time; stranding requires a signed override.

---

## 4. PROGRESSION — "the network is free" → "you are the network"

**DECISIONS C22: the full system ships from day one.** No stubbed Act-1 code path. Invisibility in
Act 1 is *emergent*: inside Earth SOI nearly every link is R_max-capped (Moon UT-DISH-M → DSN-34
computes 4.6e11 bit/s → capped 6 Mbit/s), so the system reads as a green status light until
distances grow.

| Act / tier | Network state | Activates |
|---|---|---|
| Act 1 (T0, LEO) | Everything R_max-capped; HQ's free 2 h/day DSN covers all traffic; comms UI = status light | Whole system live but invisible; P0 floor; buffers exist but never fill |
| Act 2 (T1, Moon) | **GN-03 Relay Constellations** unlocks relay parts; farside ring = first constellation (Queqiao moment); PSR teleop over the ring at 2.56 s RTT, η 0.91–0.96 | Constellation loop; store-and-forward; teleop rate floor L-13 starts binding |
| Act 3 (T2, Mars) | **First conjunction blackout (~14 d) hits a live program**; areostationary trio; A2 BATCH cadence misery + downlink-limited surveys push IN-09 (A3) and GN-06 (optical); DSN fees sting → first player GS-12s | Conjunction seasons; DSN leasing economics; survey downlink gating; ground-station ownership |
| Act 4 (T2–T3, Belt/Venus) | Optical backbone (Lighthouse); Pharos pair at ±60°; multi-hop routing the norm | Optical band + weather availability; conjunction bypass; you are becoming your own DSN |
| Act 5 (T3–T4, outer system) | kbit/s physics even on 10 m dishes → A3/A4 doctrine total; solar relay ring retires conjunction forever; Triton ~8 h RTT runs entirely store-and-forward | Autonomy is the only signal that always arrives |

Research line (11): GN-00 baseline → **GN-03** Relay Constellations (T1: relay parts, comms-path
rules) → **GN-06** Optical Deep-Space Comms (T2: OPT parts, ×10 rate class) → IN-07/IN-09 autonomy
rungs that *reduce* link dependence. ED: Avionics family 22. DSN lease prices: 12 owns escalation;
recommended mild deflation + queue-contention flavor events (Q6). Chronicle beat: first conjunction
survived without data loss.

---

## 5. GAP vs CODE

Existing code (`aphelion/sim/comms.py`, 37 lines) implements exactly two things: `rtt_seconds`
(geometry/c) and `teleop_effectiveness` (η = 1/(1+RTT/26 s), tested in `test_phase6_endgame.py`).
**Everything else in this spec is unimplemented.** `aphelion/main.py` (4,494 lines) has zero comms
UI. No comms graph, no parts, no events, no scheduler exist anywhere in the codebase.

| Spec area | Code today | Gap |
|---|---|---|
| L-2/L-3/L-4 rate law, gains, K constants, calibration tests | none | entire §1; note 13's graph/LOS/Dijkstra/occlusion layer it sits on is ALSO unbuilt |
| Part catalog (7 antennas, 2 GS, 2 DR, 4 relay blueprints, DSN tiers) | none — `content/` has no comms parts | entire §2; needs content schema rows + ELEC recipes |
| CommsNode component, buffers, P0–P4 scheduler, analytic BUFFER events | none (`core/events.py` exists as a generic queue) | entire §3.2 |
| Blackout catalog (conjunction Brent windows, SPE, EDL plasma, optical weather) | none; `sim/flight/entry.py` computes heating but posts no comms blackout | §3.3; L-9 must read 01's q̇ > 50 kW/m² from the entry model |
| Operations doctrine L-11 hooks | `sim/industry/routes.py` FreighterRoute.run() withdraws/delivers with **no link check at node-ops time** (05 §3.6 rule unenforced); `sim/flight/node_exec.py` similarly ungated | wire floor-path checks + NODE_OPS_HOLD into both |
| L-13 teleop rate floor | only η refusal exists conceptually; no rate model to check 0.5 Mbit/s against | extend teleop gating once L-3 exists |
| Science delivery gating | `sim/research.py` `earn_science()` credits instantly | route transmit-path SCI through P3 delivery; 10 Gbit/SCI volumes |
| ED failure bursts (2 Gbit / 30 d window) | no ED telemetry concept in code | new |
| Constellation gameplay, store-and-forward | `sim/orbits/*` can place the conics; nothing models coverage/buffering | §3.5–3.6 |
| DSN leasing, PASS events, player ground stations | `sim/economy.py` has money but no lease product | §2.5 + 12 integration |
| UI (overlay, link inspector, scheduler panel, checklist, alerts) | nothing in `main.py` or `ui/` | entire §3.7 |
| D-2 toggle precise semantics | no difficulty toggles in code | §3.4 |

**Consumers to wire when the system lands:** science return (`sim/research.py`), teleop vehicles
(10's control modes — not yet in code beyond η), autonomous freighters (`sim/industry/routes.py`
node-ops gate), EDL telemetry (`sim/flight/entry.py`, `descent_live.py`), power draw of antenna
parts (`sim/power.py` 09 ledger — F-6 brownout = self-inflicted blackout), campaign alerts
(`game/campaign.py`).

**Build order suggestion (respecting C22 and 13's ownership):** (1) 13's graph/LOS/occlusion layer
with rated ranges from L-4; (2) L-3 rates + calibration tests; (3) parts into content DB; (4) buffer
ledger + scheduler + events; (5) blackout catalog; (6) L-11 gates into routes/node_exec; (7) science
delivery gating; (8) DSN leases; (9) UI overlay + inspector + scheduler panel; (10) constellation
content (blueprints) and the Act 2–3 beats.

**Open questions already ruled or pending:** C22 settles Q2 (full system day one). Q1 (Chronicle
gating), Q3 (morale link, 08), Q4 (uplink ledger — recommend downlink-only), Q5 (Ka/arraying nodes),
Q6 (DSN price evolution, 12), Q7 (SPE polarity, 03/09), Q8 (relay salvage) remain open; none block
implementation as specced.
