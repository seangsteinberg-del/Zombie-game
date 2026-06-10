# 16 — Communications & Light-Lag Networks

Domain doc for PROJECT "APHELION". Owns: the **link-rate model** (data rate from transmit power,
antenna gain, and distance) layered on top of the connectivity geometry that 13-architecture.md
§3.11 already owns; the **canonical antenna / relay / ground-station part catalog** (06/07/10
consume these parts by ID); **bandwidth as a resource** (data buffers, downlink scheduling,
rate-limited science and telemetry return); the **blackout catalog** (solar conjunction, reentry
plasma, SPE degradation — occlusion windows themselves stay canon in 13); the **operations
doctrine** (link requirements per operation class); and **DSN leasing** stats (12 owns the money).

Sibling docs: 01-orbital-mechanics.md, 02-propulsion.md, 03-solar-system.md, 04-resources-isru.md,
05-industry-logistics.md, 06-ships-stations.md, 07-bases-habitats.md, 08-life-support-crew.md,
09-power-thermal.md, 10-vehicles.md, 11-research-tech.md, 12-gameplay-economy-ui.md,
13-architecture.md.

---

## 1. Overview

### 1.1 What this document owns

- **The link-rate law (L-3)**: a simplified Friis-style model, `R ∝ P·G_t·G_r / d²`, SI units
  throughout, calibrated against DSN/MRO/Voyager/DSOC published numbers. 13 §3.11's binary
  link-existence rule is *derived* from it (§3.3), not replaced.
- **The comms part catalog** (§4): omnis, medium-gain proximity antennas, high-gain dishes,
  deployable mesh antennas, optical terminals, data recorders, surface ground stations, and
  reference relay-satellite blueprints.
  06 §4.7 already lists UT-DISH-S/M/L placeholders pointing at "the 12/13 comms model" — the
  stats now live here; 06/07/10 mount these parts by ID.
- **Bandwidth as a resource**: onboard buffers, the downlink scheduler, priority classes, and the
  data volumes attached to science, telemetry, and operations (§3.5). Science transmit-path
  awards (11 §3.6) and investigated-failure ED bonuses (11 §3.2) now consume real link capacity.
- **The blackout catalog** (§3.6): superior/inferior solar conjunction, EDL plasma blackout, SPE
  link degradation, optical weather/dust availability — all posted through 13's event queue.
- **Operations doctrine** (§3.7): which operations require what link, formalizing 05 §3.6's
  "T0–T1 freighters require a comm link at node-ops time" into a general rule with failure
  consequences.
- **Earth segment**: DSN service tiers and the aperture-fee leasing anchor (§3.8); 12 owns
  pricing evolution and the Finance UI.
- **The constellation design loop** (§3.9): lunar farside rings, Mars areostationary trios,
  conjunction-bypass heliocentric relays — coverage windows computed by 13's existing occlusion
  machinery over 01/03 conics.

### 1.2 What this document does not own

- **Graph, geometry, latency, occlusion windows** → 13 §3.11, adopted verbatim: nodes, the 2D
  line-of-sight test, event-driven rebuilds, Brent-predicted occlusion windows, Dijkstra routing,
  the ≤ 300-node cap, `core:dsn` root. This doc only supplies the per-part numbers `R_x` that
  13's `d ≤ √(R_a·R_b)` rule consumes, plus new scalar event functions (conjunction, §3.6).
- **Teleoperation productivity** → 05 F-2 (`η_teleop = 1/(1 + RTT/T_atom)`), consumed unchanged.
- **Control modes** → 10 §3.8's table (CREWED / TELEOP / A2 BATCH / AUTONAV / A4 / CONVOY),
  consumed unchanged; this doc adds only the link-rate requirement column (§3.7).
- **Science amounts and ED accounting** → 11. This doc owns the *data volume* of returning them.
- **Money, alerts, difficulty toggles** → 12. This doc registers event types into 12's A-1
  classes and defines precisely what the D-2 light-lag toggle bypasses (§3.10).
- **Light-time geometry** → 01/03 (ephemerides, distances); 03 §5's body-inspector light-lag
  readout and light-lag isochrone overlay are canon and reused.

### 1.3 Design intent

Light-lag is already physics in this game (13/05/10). What is missing is the other half of real
deep-space operations: **a bit is a logistics object**. Every real mission lives and dies by its
link budget — MRO alone has returned more data than every other interplanetary mission combined
(300+ Tbit and counting, the actual NASA claim); Voyager 2
whispers home at bit-per-second rates; Galileo lost its main antenna and salvaged a mission
through heroic squeezing of a low-gain trickle. No other survival/engineering game models this
honestly, and it is pure gameplay: antennas are a design trade (mass/power/aperture), relays are
infrastructure you place with the same conic tools you fly with, conjunction is a scheduled
season you prepare for like lunar night, and the DSN is a service you outgrow. The arc of the
campaign is the arc of real spaceflight: from "the network is free" (LEO, Act 1) to "you *are*
the network" (Act 4+).

---

## 2. Real-World Grounding

| Anchor | Published numbers | Used for |
|---|---|---|
| **NASA Deep Space Network** | 34 m BWG and 70 m apertures at Goldstone/Madrid/Canberra, 120° apart so deep-space targets are always visible from one complex; 20 kW standard uplink (70 m: up to 400 kW emergency); minimum command rate 7.8125 bit/s | `core:dsn` root node stats; the 8 bit/s command floor (L-4); three-complex always-on abstraction |
| **NASA DSN Aperture Fee schedule** | published cost-recovery formula for non-NASA users; rate base ≈ $1,057 per antenna-hour (34 m, FY2015), weighted by aperture and contact type | DSN leasing prices (§4.5; 12 owns escalation) |
| **Mars Reconnaissance Orbiter** | 3 m X-band HGA, 100 W TWTA, 0.5–4 Mbit/s (peaks ~6) to DSN depending on range; 160 Gbit solid-state recorder; Electra UHF proximity relay 256 kbit/s–2 Mbit/s for surface assets | UT-DISH-M calibration point for K_RF (§3.2); DR-1 recorder; CM-PROX medium-gain proximity antenna (§4.1) and the proximity-leg worked check (§3.3) |
| **Voyager 1/2** | 3.7 m HGA, ~23 W X-band; 21.6 kbit/s at Neptune (30 AU, with arrayed 70 m + VLA); ~160 bit/s engineering telemetry at ≥ 150 AU today | Far-range sanity check of L-3 (§3.2 worked check) |
| **Galileo HGA failure (1991)** | 4.8 m deployable mesh HGA never opened; mission flew on the low-gain antenna at 8–16 bit/s, recovered to ~1 kbit/s via compression + DSN arraying vs 134 kbit/s planned | Deployable-antenna failure roll F-2; single-point-HGA design warning (§8) |
| **LCRD (2021)** | GEO optical relay demo, 1.2 Gbit/s downlink | OPT-2 rate cap; T1→T2 optical branch |
| **DSOC on Psyche (2023–24)** | 22 cm flight terminal, ~4 W laser: 267 Mbit/s at 0.21 AU to the 5 m Palomar Hale receiver; Mbit/s-class at 1.5+ AU | K_opt calibration (§3.2); OPT-1 part; GS-OPT-5 ground terminal |
| **Mars solar conjunction moratorium** | NASA stands down Mars commanding when Sun–Earth–Mars angle < ~2°, roughly 2 weeks every 26-month synod (e.g., Oct 2–16, 2021) | Conjunction blackout L-7; the 26-month "comms season" |
| **Queqiao (2018) / Chang'e-4** | first lunar-farside relay (EML-2 halo); farside surface ops impossible without it | Farside relay gameplay (§3.9; 2D honesty note there) |
| **MSL EDL "bent pipe" (2012)** | direct-to-Earth X-band dropped during entry; Odyssey overhead relayed real-time UHF tones through plasma/wake | EDL blackout rule L-9 and the park-a-relay-first doctrine |
| **Apollo reentry blackout** | ~3–4 min S-band loss during peak heating | L-9 plasma threshold |
| **Lunokhod 1/2 (1970–73)** | Earth-driven lunar rovers over ~2.6 s RTT; slow-scan TV at one frame per 3.2–21.1 s (tens-of-kbit/s class) | proof that teleop over 2.6 s RTT works (the η_teleop regime, 05 F-2) — deliberately *not* the L-13 rate floor, which its link sat ~100× below |
| **ESA METERON / ANALOG-1 (2019)** | ISS astronaut teleoperated a surface rover (live video + force-feedback haptics) over a relayed ~0.8 s RTT; Mbit/s-class video link | TELEOP minimum-rate requirement L-13 (0.5 Mbit/s live floor, canon with 05's table) |
| **TDRS / NASA Near Space Network** | LEO assets enjoy near-continuous multi-hundred-Mbit/s relay coverage | Act-1 "links are effectively free" design (§3.11, §6) |
| **Solar corona scintillation** | charged-particle scintillation, not the solar disc, causes conjunction outages; optical links additionally need several degrees of Sun-avoidance at the receiver | L-7's 2°/5° thresholds; "optical does not bypass conjunction" honesty rule |

Antenna gain physics: `G = η_ap·(πD/λ)²` for a parabolic aperture of diameter D at wavelength λ,
with aperture efficiency η_ap ≈ 0.6 — standard antenna-engineering practice (e.g., JPL DSN
Telecommunications Link Design Handbook 810-005). That is the RF convention; optical terminal
gains are conventionally quoted at the diffraction limit `(πD/λ)²` with implementation losses
carried in the link budget — L-2 mirrors both conventions, one per band. All RF in the game is
modeled as X-band-class
(λ = 35.7 mm, 8.4 GHz); Ka-band and UHF differences are folded into per-part rate caps `R_max`.

---

## 3. Game Model

All formulas SI: distance m, power W (RF or optical emitted; electrical draw quoted separately in
kWe per 09 convention), data rate bit/s, data volume bit (UI shows Mbit/Gbit/Tbit), time s.
Rules are numbered **L-x**. `c = 299,792,458 m/s` (13 canon).

### 3.1 Adopted canon (consumed unchanged — listed so nobody redefines it)

1. **Nodes, LOS, occlusion, routing, latency** — 13 §3.11 verbatim. RTT = 2·(path length)/c
   summed along the relay path. Earth–Moon RTT 2.56 s; Earth–Mars best 6.1 min (13's checks).
2. **η_teleop = 1/(1 + RTT/T_atom)** — 05 F-2, with 05's T_atom values and the η < 0.2 refusal.
3. **Control modes and link-loss safe-halt** — 10 §3.8 table, including A2 BATCH's 0.35 km/sol
   cap (that cap is autonomy hardware, *not* light-lag — see §3.10).
4. **Eclipse/occlusion fraction** `arcsin(R/r)/π` per orbit — 01 §3.14's binding rule.
5. **2D honesty**: 01's limitations table already accepts that 2D produces MORE comm blackouts
   than reality and names relay-constellation gameplay as the payoff. This doc is that payoff.

### 3.2 The link-rate law

**(L-2) Antenna gain.** Every comms part carries a gain `G` (dimensionless; UI shows dBi):

```
G_RF  = 0.6 · (π·D / λ_RF)²        λ_RF  = 0.0357 m (X-band class); η_ap = 0.6, RF only
G_opt =       (π·D / λ_opt)²       λ_opt = 1.55e-6 m; diffraction-limited convention (η = 1.0)
```

The η_ap = 0.6 dish efficiency applies to **RF apertures only**. Optical terminal gains are
quoted at the diffraction limit; every real optical implementation loss (pointing, photon-
counting detection, sky background) is folded into `K_opt` — one place only, so the §3.2 DSOC
calibration check reproduces from the catalog gains exactly as printed. Omnis have G = 1
(0 dBi) by definition; CM-PROX quotes G = 100 (20 dBi) directly (UHF helix/patch array, not a
parabola). Catalog values in §4 are precomputed from these rules.

**(L-3) Directed link rate.** For transmitter part t on node a and receiver part r on node b at
distance d (m), when the 13 §3.11 link exists:

```
R(a→b) = min( R_max(t), R_max(r), K_band · P_t · G_t · G_r / d² )   [bit/s]

K_RF  = 3.0e15  bit·m²/(s·W)     (calibrated: MRO→DSN-34, below)
K_opt = 3.2e3   bit·m²/(s·W)     (calibrated: DSOC→Palomar, below)
```

`P_t` = transmit power in W (RF or optical output, not electrical draw). `R_max` is the part's
modem/detector cap (hardware limit; §4 tables). RF and optical parts only pair with their own
band. K absorbs every real constant we refuse to simulate (system noise temperature, coding,
margins); K_opt ≪ K_RF because optical "gains" via L-2 are enormous while photon-counting
detection, pointing loss, and sky background eat most of it — one honest constant per band.

**Calibration checks (a programmer must reproduce these):**

- *MRO*: P = 100 W, G_t = 4.2e4 (3 m), G_r = 5.4e6 (DSN 34 m), d = 1 AU = 1.496e11 m →
  R = 3.0e15·100·4.2e4·5.4e6 / 2.238e22 = **3.0 Mbit/s**. Over Mars's 0.37–2.68 AU range the
  formula spans 22→0.42 Mbit/s; the UT-DISH-M cap R_max = 6 Mbit/s clips the close end —
  reproducing MRO's published 0.5–4 (peak ~6) Mbit/s envelope.
- *Voyager-class*: P = 23 W, G_t = 6.4e4 (3.7 m), to DSN 70 m (G_r = 2.28e7): at 160 AU
  (2.394e13 m) → **175 bit/s** (Voyager 1 today: ~160 bit/s). At Neptune (30 AU) → 5.0 kbit/s
  single-aperture; the real 21.6 kbit/s used a 4–5× arrayed ground complex — model is honest and
  conservative.
- *DSOC*: P = 4 W, G_t = 1.99e11 (22 cm optical), G_r = 1.03e14 (5 m Palomar-class), d = 0.21 AU
  → **267 Mbit/s** (exact calibration point). At 1.5 AU the same pair gives 5.2 Mbit/s —
  matching DSOC's demonstrated Mbit/s-class at Mars-like range.

**(L-1) Latency is unchanged** (13 §3.11). Rate and latency are independent: a Neptune link with
its ~8-hour RTT (≈ 4 h one-way light time at ~30 AU; RTT = 2τ per 13) can still be a fat pipe if
you built one.

### 3.3 Rated range — deriving 13's binary rule

**(L-4)** Define the **command floor** per band: `R_floor,RF = 8 bit/s` (anchor: DSN
7.8125 bit/s minimum command rate) and `R_floor,opt = 1 kbit/s` (photon-counting acquisition
floor: an optical receiver needs a minimum photon flux to acquire and hold pointing lock, so
there is no optical analog of the bit-per-second RF emergency mode — one more reason every deep
relay carries an RF fallback, §4.4). Each part's rated range — the number 13 §3.11's
`d ≤ √(R_a·R_b)` consumes — is:

```
R_x = sqrt( K_band · P_x · G_x² / R_floor,band )        [m]
```

With this definition, 13's root-product pairing rule `d_max = √(R_a·R_b)` is exactly the
**geometric mean of the two directed floor distances** of L-3 — i.e., the existing rule is now
*derived* from the rate model instead of being a free-standing abstraction. 13's formula, code,
and event machinery change not at all; this doc just supplies physically-derived `R_x` values.
(13's KSP-CommNet honesty tag can be retired: the abstraction now has a basis.)

Any link that exists therefore carries **at least its band's command floor** (8 bit/s RF /
1 kbit/s optical) in the geometric-
mean sense; directed asymmetry is real and displayed (a 20 kW DSN uplink reaches an omni at
ranges where the omni's downlink is a trickle — the Galileo predicament, by construction).

Worked rated ranges (from §4 stats): CM-OMNI 4.3e7 m (43,000 km — LEO/proximity class);
CM-PROX 6.1e9 m; UT-DISH-M 8.1e12 m (54 AU); `core:dsn` 34 m 1.5e16 m (never binding alone).
Mixed pairs:
omni↔DSN-34 closes at √(4.3e7·1.5e16) ≈ 8.0e11 m ≈ **5.3 AU** — a bare omni can phone home from
Jupiter at floor rates, exactly like real low-gain emergency links.

Proximity legs are a rate story, not just an existence story. A rover omni → areostationary
relay omni link at 17,000 km altitude *exists* (well inside both rated ranges) but L-3 gives it
only 3.0e15·5/(1.7e7)² ≈ **52 bit/s** — command and safe-mode, nothing more. Reproducing the
Electra envelope the §2 anchor quotes (256 kbit/s–2 Mbit/s) takes the **CM-PROX medium-gain
(G = 100) on both ends**: 3.0e15·10·100·100/(1.7e7)² ≈ **1.0 Mbit/s** at areostationary slant
range, R_max-capped at 2 Mbit/s inside ~12,000 km — the Electra UHF reality, by parts. CM-PROX
is therefore standard fit on every surface vehicle with a relay-dependent control mode
(TELEOP / A2, 10 §3.8) and on every relay bus (§4.4); omni-only proximity legs are P0-only.

### 3.4 Paths, directionality, live vs bulk traffic

**(L-5)**
- A multi-hop path's rate = **min over hops** of the directed hop rate; RTT = sum of hop light
  times (13).
- **Live classes** (P0 command, P2 teleop — see L-14) require the whole path up simultaneously.
- **Bulk classes** (P1/P3/P4) move hop-by-hop: a relay with data-recorder capacity (§4.3) stores
  and forwards across occlusion windows. A relay with no recorder is bent-pipe only (live rules).
- One antenna part services **one directed link at a time** (the scheduler assigns it); the P0
  command floor is always preemptively available on any existing link. Multi-antenna nodes
  (relay buses, §4.4) run one link per antenna.

### 3.5 Bandwidth as a resource: buffers, scheduler, data volumes

**(L-6) Buffer ledger.** Every command-source part has an integrated buffer; DR parts add more
(§4.3). Buffer level B(t) evolves piecewise-linearly: `dB/dt = Σ generation − Σ scheduled
drain`, with all rates piecewise-constant between events — exactly 13 §3.9's analytic-ledger
contract. BUFFER_FULL / BUFFER_EMPTY crossings are predicted analytically and posted to the
event queue; nothing polls. When a buffer is full, **generators pause** (instruments idle, no
data is ever silently lost) and the source is flagged (§8 F-3).

**(L-14) Priority classes.** The downlink scheduler drains buffers strictly by class, then FIFO
within class (deterministic order: class, queue timestamp, uid — 13 §3.10):

| Class | Traffic | Notes |
|---|---|---|
| P0 | command / safe-mode / go-no-go | fits in the 8 bit/s floor; never scheduled, always on |
| P1 | housekeeping telemetry, failure bursts | feeds 11's ED rules |
| P2 | teleop / live ops reservation | reserves L-13 rate while a shift runs; not buffered |
| P3 | science data, survey products | feeds 11's transmit-path awards |
| P4 | Chronicle media, low-value bulk | first to starve (12 C-x; §9 Q1) |

**(L-10) Canonical data volumes** (this doc owns these numbers; 11 owns the SCI/ED amounts):

| Source | Volume / rate | Anchor / note |
|---|---|---|
| Housekeeping telemetry | 200 bit/s per powered comms node, continuous, P1 | deep-space engineering telemetry class |
| Failure burst (11 §3.2 investigated failure) | 2 Gbit, queued P1 at failure | high-rate diagnostic dump |
| Science, transmit path | **10 Gbit per SCI point** queued P3 at acquisition | MSL-class sols return ~0.5–1 Gbit for fractional SCI |
| Orbital/ground survey product (11 §3.5) | 10 Gbit per SCI of the one-shot award | a 50-SCI Mars survey = 500 Gbit ≈ 17 days at ~8 h/day of leased 34 m passes at 1.7 AU (UT-DISH-M→34 m = 1.05 Mbit/s; 5.5 d continuous) — the real cadence |
| A2 BATCH sol cycle (10 §3.8) | 20 Mbit uplink + 800 Mbit downlink per cycle, P2 | MSL daily plan/return volumes |
| TELEOP session | L-13 live reservation, no volume | — |
| Chronicle auto-shot (12 C-2) | 50 Mbit each, P4 | §9 Q1 |

**Integration with 11 (the teeth):**
- **Science**: transmit-path awards (`M_analysis = 0.40` in-situ instruments, survey one-shots,
  observation-campaign trickles from remote platforms) are **credited only when their data
  volume is delivered to Earth or to any crewed Lab module** (OL-12/FL-2 class). Pool depletion
  S_n stays assigned per 11 §3.6 at acquisition/analysis order (11's rule untouched); only the
  *crediting moment* moves. Sample-return paths involve no downlink (mass is the carrier).
- **ED**: 11's investigated-failure bonus ("only if telemetry was downlinked") is formalized:
  the 2 Gbit failure burst must be **delivered within 30 days** of the failure event (matching
  11's inspection window). A burst stored on a relay counts when it lands, not when it's queued.
  EDL bent-pipe tones (L-9) count even if the vehicle is destroyed — the MSL doctrine, and the
  in-game reason to park a relay before you land. 11 F-11 ("failure with no comms") stands.

### 3.6 The blackout catalog (all posted via 13's event queue)

| # | Blackout | Rule | Anchor |
|---|---|---|---|
| L-7 | **Solar conjunction** | A link endpoint is *solar-blinded* when the angular separation between its peer and the Sun, seen from that endpoint, is **< 2° (link down)** or **< 5° (rate ×0.1)**. Applies to RF (corona scintillation) and optical (receiver Sun-avoidance) — **optical does not bypass conjunction; only relay geometry does.** Window edges found by the same Brent root machinery as 13's occlusions (event function: angular separation − threshold), posted as CONJ_IN/OUT. | NASA Mars command moratorium; DSOC Sun-avoidance limits |
| L-8 | **SPE degradation [GAME MODEL]** | During a 03 §S-8 SPE event, every RF link with a segment outside a planetary magnetosphere runs at ×0.5 rate; optical unaffected. LINK_DEGRADED event for the duration. | none — honesty tag, 13-CommNet style: published deep-space X-band experience shows no material rate loss from proton events (solar radio bursts matter only near solar boresight, which L-7 already covers), and real photon-counting optical receivers are if anything *more* radiation-noise-sensitive (a known DSOC design concern). The polarity here is a deliberate tuning lever that sells GN-06; revisit per §9 Q7. |
| L-9 | **EDL plasma blackout** | While 01 §3.11's heating model reports stagnation heat flux q̇ > 50 kW/m², the entering craft's direct links are down. A relay overhead receives **P0 tones only** (8 bit/s floor) through the wake; full telemetry is buffered and drains after blackout. | Apollo 3–4 min S-band loss; MSL/Odyssey bent pipe |
| — | **Body occlusion** (farside passes, terrain horizon, under-ice) | already canon — 13 §3.11 occlusion windows, unchanged | Queqiao; 10 §3.7 cryobot pucks |
| L-15 | **Atmosphere availability (optical only)** | Ground optical terminals: Earth weather availability factor 0.5 applied as scheduled random outages (13 §3.10 pre-rolled, `rng("comms")` substream); Mars ground optical suspended entirely during 03 dust storms (DUST_STORM_IN/OUT events). RF immune. | LCRD/DSOC ground-site weather diversity |

**Conjunction season table** (2D geometry: near a conjunction the Sun–Earth–body elongation
sweeps at `ω_syn · r/(r+1)` for superior conjunctions and `ω_syn · r/(1−r)` for inferior ones,
where `ω_syn = 360°/synodic period` and r is the body's heliocentric distance in AU — the
relative-longitude rate scaled by the parallax factor; 360°/synod alone is the *longitude* rate,
not the elongation rate. Hard window = 4°/sweep rate; degraded < 5° total = 10°/sweep rate —
derived, not tuned):

| Body / conjunction (vs Earth) | Synodic period (03 S-14) | Elongation sweep rate | Hard blackout | Degraded (×0.1) total |
|---|---|---|---|---|
| Mars (superior) | 780 d | 0.28°/d | **~14 d every 26 months** | ~36 d |
| Venus (superior) | 584 d | 0.26°/d | ~15.5 d | ~39 d |
| Venus (inferior) | 584 d | 1.61°/d | ~2.5 d | ~6 d |
| Mercury (superior) | 116 d | 0.87°/d | ~4.6 d, ~3×/yr | ~11.5 d |
| Mercury (inferior) | 116 d | 1.96°/d | ~2.0 d, ~3×/yr | ~5 d |
| Jupiter | 399 d | 0.76°/d | ~5.3 d per 399 d | ~13 d |
| Saturn | 378 d | 0.86°/d | ~4.6 d per 378 d | ~11.5 d |

(The real Oct 2–16, 2021 Mars moratorium ran 15 days — the derived 14-day hard window plus
shoulders reproduces the anchor directly, no tuning. The inferior-conjunction rows exist because
in coplanar 2D every inferior conjunction of Venus/Mercury passes exactly through 0° elongation
with the planet crossing the Sun's disc as seen from Earth, so L-7 triggers there too; real
passes usually miss in ecliptic latitude — this is the more-blackouts-than-reality artifact
01's limitations table already accepts.) Planner surfaces these like launch windows: a
**Class-3 alert at T−30 d** with a pre-conjunction checklist (§5.4).

### 3.7 Operations doctrine — link requirements per operation class

**(L-11)** Adopts 05's autonomy ladder A0–A4 and 10 §3.8's control modes verbatim; adds the
required link and the failure consequence. "Floor" = any existing path (≥ 8 bit/s, P0).

| Operation class | Link requirement | On loss / unavailability |
|---|---|---|
| Crewed ops (CREWED mode, A0 EVA, crewed docking) | none | — |
| **Uncrewed node ops, T0–T1 avionics** (dock/undock, burn execute, cargo-handling start — generalizes 05 §3.6's freighter rule) | floor path **at event time** (light-lag irrelevant: execution is autonomous, the link is go/no-go) | op auto-holds; retry at next link window; route replans (05); Class-3 NODE_OPS_HOLD, escalating Class-2 if a burn window expires |
| Uncrewed node ops, T2+ avionics | none (fully independent — 05 canon) | — |
| TELEOP (A2 joystick) | **(L-13)** live path ≥ 0.5 Mbit/s (P2 reservation; anchor: METERON/ANALOG-1-class video+haptics, §2) AND η_teleop ≥ 0.2 (05). Relay legs must be CM-PROX-class or better (§3.3 — omni legs are P0-only) | safe-halt per 10 §3.8 (aircraft RTB, balloons drift); shift pauses exactly per 13's windows — extended to unplanned losses (§8 F-1) |
| A2 BATCH | one 20 Mbit up + 800 Mbit down session per cycle (L-10) — ≈ 13 min/sol on a 1 Mbit/s CM-PROX areostationary leg (§3.9.2) | robot idles that sol; missed cycles accumulate no penalty beyond lost time |
| AUTONAV / A3 dispatch & arrival | floor path at dispatch and arrival events; exceptions page a human only when a path exists, else they queue | exception queue grows; uncleared exceptions idle the robot (05 canon) |
| A4 complex | none (05 canon) | — |
| EDL | autonomy mandatory during L-9 blackout (01 EDL Guidance); relay overhead optional but feeds ED (§3.5) | — |
| Science downlink, ED telemetry | scheduled P3/P1 capacity (L-6) | credits defer; F-3 alerts on starvation |

### 3.8 The Earth segment: DSN root and player ground stations

- **`core:dsn`** (13's always-on root) represents the three-complex 120° DSN: never occluded by
  Earth's rotation. Stats: 34 m tier G = 5.4e6, P_tx = 20 kW; 70 m tier G = 2.28e7, P_tx =
  20 kW (the standard uplink, anchored — the 70 m's advantage is its aperture, not its power;
  the published 400 kW emergency-command mode is modeled as a P0-floor-only state and never
  enters scheduled rates); both R_max = 150 Mbit/s (Ka-class folded in). Optical tier (T2+, after GN-06 exists
  anywhere): GS-OPT-5-class receive, leased like an aperture.
- **Leasing (L-12)**: DSN time is bought in antenna-hours via the Planner; the scheduler turns a
  lease into PASS_START/END events. Prices in §4.5 anchor to NASA's aperture-fee schedule; 12
  owns escalation, contracts, and standing-service automation (E-12 style). **Program HQ
  includes 2 h/day of 34 m time free** (the "NASA-sponsored mission" status; tutorial-friendly).
- **Player Earth ground stations** (GS-12, §4.2) are nodes on rotating Earth: 13's LOS test
  occludes them ~50% of each day naturally — which is *why* the DSN has three complexes and why
  leasing matters. Building 2–3 of your own spaced stations is the mid-game emancipation move.
- Surface ground stations on other bodies (same GS parts) serve base trunks; 07's data network
  (wireless ≤ 10 km, relay masts beyond) handles intra-site distribution — unchanged.

### 3.9 The network design loop: constellations (worked examples, binding)

Relays are ordinary vessels (06 blueprints) on 01 conics; coverage windows fall out of 13's
existing occlusion machinery. No new solver. Three canonical projects:

1. **Lunar farside ring (Act 2).** 2D honesty: a Queqiao-style EML-2 halo cannot exist in this
   game (collinear point sits exactly behind the Moon; no out-of-plane halos — 01's accepted
   artifact). The honest 2D solution: **3 relays in 5,000 km circular lunar orbit, 120° phased**
   (period 8.8 h). Surface visibility arc per sat = 2·arccos(1737/5000) = 139° > 120° spacing →
   continuous farside coverage. Surface legs are CM-PROX↔CM-PROX: slant range 3,263–4,688 km →
   L-3 computes 14–28 Mbit/s, R_max-capped at 2 Mbit/s — comfortably above the L-13 teleop
   floor. Each sat is Moon-occluded from Earth arcsin(1737/5000)/π = 11.3% of its orbit; the
   omni crosslinks across the r√3 = 8,660 km inter-sat spacing carry only ~200 bit/s (L-3) —
   **P0 command continuity for the occluded bird, nothing more**. Bulk traffic across the
   occlusion window rides the DR-1 store-and-forward (the primary mechanism: ≤ 1 h occluded per
   8.8 h orbit buffers ≤ 7.2 Gbit at full 2 Mbit/s ingest, well inside 256 Gbit). Live relay
   *through* a neighbor would need a second dish-class antenna per bird (one antenna, one link —
   L-5) — deliberately not in this blueprint. Cost: 3 × "Heliograph" buses (§4.4) ≈ 1.1 t to
   LLO.
2. **Mars areostationary trio (Act 3).** r_areo = (μ_M·T²/4π²)^(1/3) = 20,430 km (T = 24.623 h,
   μ = 4.2828e13 m³/s²): 3 "Heliograph-A" relays (§4.4) at 120° give continuous coverage of
   every surface site (visibility arc 2·arccos(3396/20430) = 161° > 120°). Surface legs are
   CM-PROX↔CM-PROX: ~1.0 Mbit/s at the 17,000 km nadir range (0.74 Mbit/s at the 20,100 km
   horizon-edge slant — still above the L-13 floor; 2 Mbit/s cap inside ~12,000 km) — the
   Electra envelope, enough for TELEOP reservations and a ~13 min A2 BATCH session per sol. The
   omni crosslinks at 35,400 km inter-sat spacing exist (just inside the 43,000 km omni rated
   range) but carry ~12 bit/s, barely above floor — **P0 continuity only**; bulk traffic across
   any relay's Earth-occlusion arc (≤ 5.3% of the sol) rides its DR-1 store-and-forward. Each
   carries a UT-DISH-M Earth trunk: 0.42–6 Mbit/s by season.
   Anchor: real proposed Mars areostationary relay constellations (MOSAIC-class studies).
3. **Conjunction-bypass solar relay (Act 3–4).** A "Pharos" bus in a **1.0 AU heliocentric orbit
   phased ±60° from Earth** (plain on-rails conic — no L-point machinery needed; it *is* the
   Sun–Earth L4/L5 region). At Mars superior conjunction the path Mars→relay→Earth clears the
   Sun by 0.6 AU. Rates (L-3, each hop computed with its *actual* receiver — the Mars→relay
   hop terminates on the Pharos's own dish, not on DSN gain): with a UT-DISH-L on the
   Mars end (the trio's trunk bird upgraded, or a dedicated Mars-orbit twin) into the Pharos's
   UT-DISH-L, Mars→relay at 2.20 AU = 3.0e15·200·(4.6e5)²/(3.291e11)² ≈ 1.17 Mbit/s; relay→Earth
   at 1.0 AU computes 67 Mbit/s into DSN-34 → R_max-capped at 50 Mbit/s; path rate =
   min(1.17, 50) ≈ **1.2 Mbit/s through the blackout** — science keeps flowing while everyone
   else's Mars program goes dark for two weeks. (Against the trio's stock UT-DISH-M transmit the
   bypass carries only ~54 kbit/s — P0/P1 continuity and a science trickle; the L-class
   Mars-side dish is part of the project's price.) RTT via relay ≈ 53 min (irrelevant: nothing
   live runs at Mars anyway). Two relays at ±60° cover every superior conjunction of every body
   forever — a quiet, deeply in-genre megaproject.

Stationkeeping fees per 01 Table 4.8 apply to all relays (flat 2 m/s/yr background class).

### 3.10 Difficulty integration (12 D-2, precise semantics)

The D-2 toggle **"Comms light-lag & teleop penalty: off"** bypasses **RTT penalties only**:
- η_teleop ≡ 1 (F-2 bypassed); the TELEOP input-delay ghost (10 §5) renders without delay;
  the η < 0.2 refusal never triggers.
- **Everything else stays on in every preset**: link existence and occlusion windows (13),
  rates and caps (L-3), buffers and scheduling (L-6), the blackout catalog (§3.6), node-ops
  link requirements (L-11), DSN fees (L-12), and the A2 BATCH 0.35 km/sol cap (autonomy
  hardware, not light-lag). Links never stop existing because of a toggle.
- RTT continues to be *displayed* truthfully (the toggle waives consequences, not physics
  readouts). **Baseline keeps all of it on** (12 D-1); Training preset ships with the toggle
  off per 12 §4.6, and the save is asterisked per D-3.

### 3.11 Architecture & performance contract (13)

- Node cap ≤ 300, event-driven rebuild + 60 s cadence, Dijkstra routing, frame budget 0.2–0.3 ms
  — all 13 §3.11/§4.6 numbers unchanged. Rate evaluation is one vectorized numpy pass over live
  links piggybacked on the existing rebuild; the scheduler is pure event bookkeeping (L-6).
- New event types registered with 13's queue: CONJ_IN/OUT, LINK_DEGRADED_IN/OUT (SPE/weather),
  PASS_START/END (leases), BUFFER_FULL/EMPTY, NODE_OPS_HOLD. OCCLUSION_IN/OUT already exists.
- `CommsNode` component (13 §schema) gains fields: `parts: [comm part uids]`, `buffer_bits`,
  `buffer_cap_bits`, `queue: per-class volumes` — dataclass extension, save-schema versioned.
- Determinism: scheduler ordering is (class, timestamp, uid); weather outages pre-rolled from
  `rng("comms")` (13 §3.10 — no rerolls on reload).
- **Act-1 cost honesty**: in Earth SOI nearly every link is R_max-capped (e.g., Moon UT-DISH-M →
  DSN-34 computes 4.6e11 bit/s → capped at 6 Mbit/s), so the whole system is invisible until
  distances grow — the complexity ramp is emergent, not special-cased (see §9 Q2).

---

## 4. Content Catalog

Recipes: all parts below are build-class ELEC (06 §3.x: 0.40 Electronics + 0.30 Aluminum +
0.20 Copper + 0.10 MachineParts). Prices are 2049 baselines in $M (12 owns evolution). Gain
values follow L-2 exactly (RF dish rows include η_ap = 0.6; optical rows are diffraction-limited
per L-2's optical branch); CM-OMNI (G = 1) and CM-PROX (G = 100, helix/patch array) are quoted
directly, not aperture-derived. "Draw" is electrical (kWe, 09 ledger); TWTA efficiency 0.3 sets
RF draw, optical heads ~5%.

### 4.1 Antennas and terminals (vessel/vehicle parts; 06/10 mount by ID)

| ID | Name | Tier | Mass | Draw kWe | Band | P_tx W | G (dBi) | R_max | Rated range L-4 | $M | Anchor |
|---|---|---|---|---|---|---|---|---|---|---|---|
| CM-OMNI | Omni antenna (integrated in UT-AV/UT-AVS cores; standalone for vehicles/relays) | T0 | 5 kg | 0.02 | RF | 5 | 1 (0) | 256 kbit/s | 4.3e7 m | 0.05 | flight LGAs |
| CM-PROX | Proximity medium-gain antenna (UHF helix/patch array) | T0 | 8 kg | 0.04 | RF | 10 | 100 (20) | 2 Mbit/s | 6.1e9 m | 0.15 | **Electra UHF proximity payload (MRO/MAVEN/TGO)** |
| UT-DISH-S | High-gain dish 0.5 m | T0 | 20 kg | 0.05 | RF | 10 | 1.16e3 (30.7) | 2 Mbit/s | 7.1e10 m | 0.4 | smallsat HGAs |
| UT-DISH-M | High-gain dish 3 m | T0 | 90 kg | 0.35 | RF | 100 | 4.2e4 (46.2) | 6 Mbit/s | 8.1e12 m | 2.0 | **MRO HGA + 100 W TWTA** |
| UT-DISH-L | Deployable mesh dish 10 m | T2 | 400 kg | 0.70 | RF | 200 | 4.6e5 (56.7) | 50 Mbit/s | 1.3e14 m | 8.0 | large deployable mesh; **Galileo deploy-roll, §8 F-2** |
| OPT-1 | Optical terminal 22 cm | T2 (GN-06) | 30 kg | 0.10 | opt | 4 | 1.99e11 | 267 Mbit/s | 7.1e11 m† | 12 | **DSOC flight terminal** |
| OPT-2 | Optical terminal 50 cm | T3 | 80 kg | 0.25 | opt | 10 | 1.03e12 | 1.2 Gbit/s | 5.8e12 m† | 25 | LCRD-derived deep terminal |

† Optical rated ranges use the optical acquisition floor R_floor,opt = 1 kbit/s (L-4) and are
self-pair values; real reach comes from pairing with big ground apertures (§4.2): OPT-1 ↔
GS-OPT-5 closes at √(7.1e11 · 8.2e14) ≈ 2.4e13 m ≈ **160 AU**; rate at 1.5 AU = 5.2 Mbit/s.

06 §4.7's UT-DISH rows now defer here (same IDs, masses unchanged); UT-AV's "low-gain comms"
is canonically one integrated CM-OMNI + 16 Gbit buffer; UT-AVS integrates CM-OMNI + 4 Gbit.
CM-PROX is never integrated — it is an explicit mount on rovers and landers (10) and on relay
buses (§4.4); the §3.3 proximity-leg worked check is its sizing rationale.

### 4.2 Ground / base stations (07 surface-grid modules)

| ID | Name | Tier | Mass | Draw kWe | Band | P_tx | G (dBi) | R_max | Rated range L-4 | $M | Anchor |
|---|---|---|---|---|---|---|---|---|---|---|---|
| GS-12 | Ground station, 12 m dish | T1 | 25 t | 15 | RF | 2 kW | 6.7e5 (58.3) | 200 Mbit/s | 5.8e14 m | 20 | commercial 12 m class + site infra |
| GS-OPT-5 | Optical ground terminal, 5 m | T2 (GN-06) | 40 t | 25 | opt | 20 | 1.03e14 | 1.2 Gbit/s | 8.2e14 m | 45 | Palomar/DSOC receive chain |
| — | `core:dsn` 34 m (lease only) | — | — | — | RF | 20 kW | 5.4e6 (67.3) | 150 Mbit/s | 1.5e16 m | §4.5 | DSN 34 m BWG |
| — | `core:dsn` 70 m (lease only) | — | — | — | RF | 20 kW | 2.28e7 (73.6) | 150 Mbit/s | 6.2e16 m | §4.5 | DSN 70 m (standard uplink; 400 kW emergency mode is P0-only, §3.8) |

GS-12 on Earth is subject to rotation occlusion (~50% duty, §3.8); GS-OPT availability ×0.5
weather on Earth (L-15). On airless bodies optical ground terminals run at full availability.

### 4.3 Data recorders (buffers)

| ID | Name | Tier | Mass | Draw kWe | Capacity | $M | Anchor |
|---|---|---|---|---|---|---|---|
| (integrated) | in UT-AV / UT-AVS | T0 | — | — | 16 / 4 Gbit | — | flight SSRs |
| DR-1 | Solid-state recorder | T0 | 5 kg | 0.05 | 256 Gbit | 0.5 | MRO 160 Gbit SSR class |
| DR-2 | Bulk archive recorder | T2 | 20 kg | 0.10 | 4 Tbit | 1.5 | modern flash arrays, rad-hard derated |

### 4.4 Reference relay blueprints (assemblies of the above; 06 blueprint format)

| Blueprint | Tier (node) | Parts | Wet mass | Role / quoted performance |
|---|---|---|---|---|
| "Heliograph" relay smallsat | T1 (GN-03) | UT-AVS + CM-OMNI + CM-PROX + UT-DISH-S + DR-1 + 1 kWe solar + RCS | 0.36 t | **lunar ring unit cell** (§3.9.1): CM-PROX proximity legs (2 Mbit/s capped inside ~12,000 km), UT-DISH-S Earth trunk (2 Mbit/s R_max-capped inside Earth SOI; only ~8.4 kbit/s at 1 AU — not an interplanetary trunk), DR-1 store-and-forward across occlusions, omni P0 crosslinks |
| "Heliograph-A" areo relay | T1 (GN-03) | UT-AVS + CM-OMNI + CM-PROX + UT-DISH-M + DR-1 + 2 kWe solar + RCS | 0.50 t | **areostationary trio unit cell** (§3.9.2): CM-PROX proximity legs ~1 Mbit/s at areostationary slant; UT-DISH-M Earth trunk 0.42–6 Mbit/s by season; DR-1 store-and-forward |
| "Pharos" deep relay | T2 | UT-AV + UT-DISH-L ×2 + DR-2 + 3 kWe solar + RCS | 2.4 t | trunk relay: ~1.2 Mbit/s per leg at 2.2 AU, both directions simultaneously (the 50 Mbit/s modem cap binds only inside ~1.15 AU against DSN-class apertures); conjunction-bypass unit (§3.9.3) |
| "Lighthouse" optical trunk | T3 (GN-06) | UT-AV + OPT-2 ×2 + UT-DISH-S (RF backup — the Galileo lesson) + DR-2 ×2 + 5 kWe solar | 2.0 t | 0.2–40 Mbit/s optical backbone legs between planets; always carries an RF fallback |

### 4.5 DSN lease tiers (stats here; money mechanics and escalation → 12)

| Service | Price (2049 $) | Notes |
|---|---|---|
| 34 m antenna-hour | $1,100/h | anchor: NASA aperture fee RB ≈ $1,057/h (FY2015) |
| 70 m antenna-hour | $4,400/h | aperture weighting ×4 |
| Optical ground network hour | $2,500/h | available T2+ once GN-06 researched |
| HQ allocation | 2 h/day on 34 m, free | sponsored-mission status; covers Act 1–2 comfortably |
| Standing lease | contract per 12 E-12 | auto-scheduled passes; the set-and-forget option |

### 4.6 ED and reliability hooks

All §4.1–4.3 parts accrue **Avionics-family ED** (11 family 22, event/hour rules per 11 §3.2).
Failure rates ride 06's part-event machinery; UT-DISH-L additionally carries the one-time
deployment roll (§8 F-2) using 11's prototype/reliability state multipliers.

---

## 5. Player Interaction and UI

- **S-02 network overlay (Planner).** Toggle layer on 12's System Map: nodes with health badges;
  link lines colored by current rate (log scale: green ≥ 1 Mbit/s, yellow < 1 Mbit/s, red =
  floor-only, grey dashed = occluded/scheduled-out); conjunction zones drawn as shaded 2°/5°
  sectors about the Sun; 03 §5's light-lag isochrones reused unchanged. 12 owns the frame.
- **Link inspector.** Click any link: directed rate both ways with the L-3 terms itemized
  (readout honesty per 08 §5 / 12 A-5 — hover any number for its equation), RTT, the next 48 h
  occlusion/pass timeline as a horizontal strip (the "when does my relay set" answer at a
  glance), and the binding constraint named (gain-limited / cap-limited / blinded).
- **Downlink scheduler panel** (vessel/site context tab): buffer gauge with analytic
  time-to-full, per-class queue volumes, assigned passes; drag to reprioritize within class
  rules; "lease more DSN time" shortcut into 12's Finance.
- **Pre-conjunction checklist** (Class-3 alert at T−30 d): affected assets list, projected
  buffer growth during blackout, one-click "suspend standing teleop shifts / confirm A3 task
  queues / top off uplinked plans" — the NASA moratorium ritual as UX.
- **Teleop console additions** (extends 05/10 canon unchanged): alongside RTT and η_teleop, show
  link rate vs the 0.5 Mbit/s L-13 requirement and the shift's occlusion timeline before
  committing. Store-and-forward status appears on every vessel context panel (buffer %, next
  drain window).
- **Alert registrations** (12 A-1): Class 2 — UNPLANNED_RELAY_LOSS during live ops, NODE_OPS
  burn-window expiry, science stall > 7 d; Class 3 — NODE_OPS_HOLD, BUFFER ≥ 80%, CONJ_IN
  T−30 d notice, LINK_DEGRADED. (No comms event is Class 1: nothing here kills crew directly.)

---

## 6. Progression Hooks

| Act / tier | Network state | The lesson |
|---|---|---|
| Act 1 (T0, Earth/LEO) | everything R_max-capped; HQ's free DSN hours cover all traffic; comms UI is a status light | links feel free — as in real LEO ops (TDRS reality) |
| Act 2 (T1, Moon) | GN-03 unlocks relay parts; **farside ring is the first constellation** (the Queqiao moment); PSR teleop from orbit or Earth rides the ring's CM-PROX proximity legs (2 Mbit/s capped ≥ the 0.5 Mbit/s L-13 floor) while bulk science drains by DR-1 store-and-forward; 2.56 s RTT teleop at η 0.91–0.96 | coverage is built, not given |
| Act 3 (T2, Mars) | first conjunction blackout (~14 d) hits a live program; areostationary trio; A2 BATCH misery + downlink-limited surveys push IN-09 (A3) and GN-06 (optical); DSN fees start to sting → first GS-12s | bandwidth and seasons are logistics |
| Act 4 (T2–T3, Belt/Venus) | optical backbone legs (Lighthouse); conjunction-bypass Pharos pair at ±60°; multi-hop routing the norm | you are becoming your own DSN |
| Act 5 / endgame (T3–T4) | outer-system kbit/s physics even on 10 m dishes → A3/A4 doctrine total; solar relay ring retires conjunction forever; Triton at ~8 h RTT (4 h one-way) runs entirely on store-and-forward | autonomy is the only signal that always arrives |

Research tie-ins (11 canon, consumed): GN-00 baseline avionics → GN-03 Relay Constellations
(T1: relay parts + comms-path rules) → GN-06 Optical Deep-Space Comms (T2: OPT parts, ×10-class
rate jump) → IN-07/IN-09 autonomy rungs that *reduce* link dependence. ED: Avionics family.
Era-defining beat: the first conjunction survived without data loss is a Chronicle chapter.

---

## 7. Cross-System Interfaces

- **13-architecture.md** — *consumes from 13*: graph, LOS, occlusion windows, Dijkstra, RTT,
  ≤ 300-node cap, event queue, analytic-ledger contract, RNG discipline. *Provides to 13*:
  per-part `R_x` values (L-4) so §3.11's root-product rule is derived; new event types (§3.11
  list); CommsNode field extensions; the conjunction scalar event function.
- **05-industry-logistics.md** — F-2 consumed unchanged; L-11 formalizes 05 §3.6's freighter
  comm rule and its hold/replan consequence; teleop labor market unchanged; relay buses are 05
  fabrication jobs.
- **10-vehicles.md** — control-mode table consumed verbatim; L-11 adds rate requirements; L-13's
  0.5 Mbit/s TELEOP floor; CM-PROX is the standard rover/lander-side proximity antenna for
  TELEOP/A2 vehicles (§3.3, §4.1); safe-halt and occlusion-pause semantics unchanged, extended
  to unplanned losses (§8 F-1).
- **11-research-tech.md** — SCI/ED amounts unchanged; this doc adds delivery gating (L-10) and
  the 30-day failure-burst window. **Conforming edit requested in 11 §9**: transmit-path awards
  credit on delivery, not acquisition (pool accounting untouched).
- **12-gameplay-economy-ui.md** — DSN lease stats (§4.5; 12 owns pricing/contracts/E-12), alert
  registrations (§5), D-2 semantics (§3.10), S-02 overlay content, Chronicle hooks (§9 Q1).
- **01/03** — geometry, light-time, synodic periods, eclipse rule, EDL heating (L-9 threshold
  reads 01 §3.11's q̇), SPE fields (03 S-8), dust storms (03), stationkeeping fees (01 4.8).
- **06/07** — part grid mounting, blueprint format, ELEC recipes; 06's UT-DISH rows defer here;
  07's site data network (relay masts) is the last-100-m layer below this doc's trunks; 09
  supplies power per Draw columns.
- **08** — nothing consumed yet; crew-morale link (family comms) offered as §9 Q3, 08 to rule.

## 8. Failure Modes and Edge Cases

| # | Failure | Rule / consequence |
|---|---|---|
| F-1 | **Relay loss mid-teleop-shift** (part failure, power loss, MMOD — unplanned, unlike 13's predicted windows) | identical machinery to 13's exact occlusion pause, triggered by the failure event instead of a predicted window: shift pauses, robot/vehicle safe-halts (10 §3.8), Class-2 UNPLANNED_RELAY_LOSS. Operator-hours for the rest of the shift are forfeit (05 labor ledger) — redundancy has a payroll argument. |
| F-2 | **Deployable-antenna jam** (UT-DISH-L only) | one-time deploy roll via 11's reliability state (prototype ×4 etc.). Jam → part operates at G = 100 (20 dBi partial mesh; Galileo's mission-on-a-trickle, by the numbers). Repairable: 8 crew-h EVA or A2 robot task + 0.1 t MachineParts — *unlike* Galileo, you can fly a serviceing mission; routing one is the intended lesson. 06 validator emits a W-class warning for any deep-space design whose only Earth-class link is a single deployable HGA ("Galileo check"). |
| F-3 | **Bandwidth starvation / softlock** | BUFFER ≥ 80% Class-3; generators pause at 100% (no data loss, science stalls); science stall > 7 d Class-2. Hard anti-softlock: the P0 floor exists on any link by construction (L-4), so a commandable asset can always be told to point home, deorbit, or rendezvous — bandwidth can stall progress, never strand the campaign. |
| F-4 | **Conjunction with no bypass** | scheduled, never a surprise: Class-3 at T−30 d with checklist (§5). During hard window: standing TELEOP suspended, A2 BATCH cycles skip, T0–T1 node ops auto-held (route planner refuses to schedule them inside a known window at plan time), A3+ continues. Buffers ride it out per L-6. |
| F-5 | **SPE storm** | L-8 ×0.5 on exposed RF links for event duration; stacks with everything else; optical unaffected per L-8's [GAME MODEL] tuning — a quiet T2 argument for GN-06. |
| F-6 | **Node unpowered** | 13 canon: drops from graph. Comms parts' Draw is on 09's ledger; a brownout that sheds the antenna bus is a self-inflicted blackout (09 load-shedding priorities apply). |
| F-7 | **Stranded asset: no link, no autonomy** | e.g., T0 freighter drifting past its hold limit, or a farside crash site with no ring yet. Asset enters SAFE (sun-pointed, beacon at floor *when* a path next exists); recovery = build the link or fly to it. UI refuses dispatch plans whose required link windows don't exist at plan time — stranding takes deliberate overrides (signed warning, 10 §8 precedent). |
| F-8 | **Earth station weather/dust** (optical) | L-15 pre-rolled outages; the scheduler simply books around them — visible in the pass timeline, no alert unless it breaks a deadline (then 12's contract machinery owns it). |
| F-9 | **EDL telemetry loss** | no relay overhead during L-9 blackout + vehicle lost = no failure burst = no investigated-failure ED (11 F-11 stands). The bent-pipe relay turns "we'll never know" into engineering data — exactly why MSL flew it. |
| F-10 | **Edge: store-and-forward deadlines** | bulk data on a relay whose next drain window misses a contract/ED deadline counts as undelivered; the scheduler's analytic projection flags this at queue time (Class-3), not at the deadline. |

Edge cases: (a) multi-hop live paths break if *any* hop occludes — the planner quotes the
**intersection** of hop windows for teleop shifts; (b) two antennas on one vessel can run
simultaneous links (e.g., proximity omni + Earth trunk — the standard relay pattern); (c) a
link's two directions can be in different states (uplink blinded, downlink clear) — L-7 tests
per endpoint; (d) buffers serialize as plain ledger floats (13 §3.15), pristine-cheap in saves.

## 9. Open Questions

1. **Chronicle auto-shots from remote sites** (12 C-2): gate the 50 Mbit P4 uploads behind real
   bandwidth (delicious — your Neptune montage arrives four hours late and starved), or exempt
   media as non-diegetic? Recommend: gate beyond Mars, exempt inside; 12 to rule.
2. **Act-1 minimum viable model**: ship the full system from day one (current design — it is
   naturally invisible in Earth SOI per §3.11) or stub rates entirely until Act 2 and save a
   sprint? Recommend full system; the emergent ramp is cheaper than two code paths. 13 to
   confirm the scheduler fits the Phase-4 milestone.
3. **Crew morale link** (08): private family video uplink as a morale modifier (analog-mission
   literature supports it) — e.g., +5 morale band when ≥ 1 Mbit/s to Earth exists weekly.
   Offered to 08; not canon until 08 prices it into its morale economy.
4. **Uplink ledger**: currently only downlink is scheduled (uplink is free except A2 BATCH and
   node-ops go/no-go). Model uplink capacity symmetrically, or is that fidelity without
   gameplay? Recommend: downlink-only until playtests complain.
5. **Ka-band / arraying as content**: both are folded into R_max and K_RF today. Worth a T1–T2
   node each (×3 R_max upgrade; DSN arraying lease tier ×4 G_r) for tech-tree texture? 11 owns
   node budget (129 named nodes is a hard count).
6. **DSN price evolution**: does commercialization deflate $/h over the campaign decades (the
   way commercial lift deflates $1,500/kg, 06 §3.x)? 12 owns; recommend mild deflation + queue
   contention events for flavor.
7. **SPE vs proximity links**: L-8 currently exempts links inside magnetospheres; should Jovian
   belt links (03 S-8c) instead be *permanently* degraded ×0.5 as a radiation-noise tax? 03/09
   realism reviewers to rule.
8. **Relay salvage/refit**: when a Heliograph ring is obsoleted by an optical backbone, are the
   old birds salvage (05 scrap chain) or heritage monuments (Chronicle flavor)? Pure content
   question; no system blocks on it.
