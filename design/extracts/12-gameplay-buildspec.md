# BUILD SPEC — Gameplay Loop, Campaign, Economy & UI
Extracted from `design/12-gameplay-economy-ui.md` (v1 design-complete) + binding rulings from
`design/DECISIONS.md` (A1, A7, C18, C19, C25, F33 — DECISIONS wins conflicts). Implement from this
document without re-reading the original; rule IDs (G/E/D/A/F/C/T-x) preserved for traceability.
All money = constant-2049 USD. Campaign epoch t₀ = 2049-01-01 00:00 UTC.

---

## 1. THE FIVE-ACT CAMPAIGN

### 1.1 Act structure (§6 + G-12/G-13)

| Act | Theater | Tiers | Economic regime | Gameplay center | Exit milestone (act-transition trigger) | Target hours (cum.) |
|---|---|---|---|---|---|---|
| 1 | Earth + LEO | T0–T1 | Pure $: contracts CT-01…CT-10, Firsts, Seed→Series A; insurance matters; every kg lifted hurts ($1,500/kg) | Pilot + Engineer: launcher design, reuse, depots | First cryo depot transfer demo | 0–12 h |
| 2 | Moon | T1–T2 | $ still king; CLPS-style rates; Series B; first SSI pixels (lunar Water/LOX) | + Base mode; first ISRU chain, surface ops | Lunar LOX at depot; 4-crew × 90-d base | 12–35 h |
| 3 | Mars & NEAs | T2 | **The hinge**: CT-16/17 money big but logistics dominates; standing services (E-12) automate cash | Planner ascendant; NTR logistics, windows, Mars ISRU closure | Mars methalox + first food harvest | 35–75 h |
| 4 | Belt & Venus | T2–T3 | Money fades (E-19 usually fires); Earth manifests = Electronics/Pu238/HALEU only; mass driver changes gear ratios | Base + Planner; multi-site industry, aerostat ops | Silicon Independence (wafer fab online) | 75–120 h |
| 5 | Jupiter/Saturn | T3–T4 | Mass economy; $ ledger a side-tab; Prestige + Chronicle are the score | Megaproject staging, MW-class EP fleets, Titan/Enceladus volatiles | Saturn permanent base (12 crew × 2 yr) | 120–170 h |
| End | — | T4 [SPECULATIVE] | None — audits | Foundation Audit (E-28) and/or Interstellar Precursor (E-29) | Credits | 170–220 h |

- **G-13 (act transitions).** Act N+1 begins — and the Chronicle `ACT_CHAPTER` entry fires — when
  Act N's exit milestone completes. Act state is **monotonic** (never reverts). Contract `[A#]`
  availability = act unlocked AND capability demonstrated (E-8). One "reach" teaser contract per
  act is always visible as a stretch goal.
- **G-12 (pacing).** Credits ~150–220 h Baseline; completionist ~300 h. Calibration: if median
  playtesters exceed a target by >40%, cut *frictions* (UI steps, warp interrupts) — never physics.
- Per-act money envelope: cumulative spend capacity ≈ **$0.45B end Act 1, ≈ $1.6B Act 2, ≈ $4B
  Act 3** (then money decouples).

### 1.2 Starting state (E-1)

$300M cash (seed round, pre-banked) · one leased coastal launch site (pad + integration hangar +
mission control) · T0 catalog access · 2 generated crew candidates on file · Prestige 0.

### 1.3 Contract system mechanics (E-8…E-12)

- **E-8 (offer board).** Refreshes weekly (sim). Simultaneous offers `N = 3 + floor(Prestige/100)`,
  max 12, filtered by demonstrated capability (lunar contracts only after any player craft reaches
  lunar SOI, etc.). Post-completion same-template cooldown: **90 d default**; recurring (CT-05/14/19)
  immediate; tourism (CT-07/15) 30 d; flagship science (CT-17/20) 180 d; uniques (CT-09/21) never.
- **E-9 (payment).** Accept → **10% advance**. Completion → remainder. Multi-part contracts pay
  per-unit fractions. Default deadline `T_deadline = T_accept + max(2 × t_min_transfer, 90 d)`
  (t_min_transfer from transfer/window tables, incl. synodic wait). Explicit per-template deadline
  bases in §1.4 **override** the formula. Deadline alerts at T−90/30/7 d.
- **E-10 (failure).** Miss/abandon → repay advance + **20% of total value** penalty + **Prestige
  −10** + that customer's templates locked 1 yr. If a customer payload was destroyed, add insured
  value: customer-supplied hardware (CT-04, CT-22) → **2 × total contract value**; mass-delivery
  (CT-02/05/11/14/16) → **$10M/tonne** of customer payload aboard; crewed (CT-06/07/13/15) add no
  payload penalty (fatalities handled by E-23 stand-downs + F-4 death economics).
- **E-11 (delivery payout).** Mass-delivery: `Payout = m_payload(kg) × rate_dest($/kg) × k_urgency`.
  **25% of generated offers are urgent**: deadline ×0.5 (still feasibility-validated) and
  `k_urgency = 1.5`; otherwise 1.0. All rates decline **8%/yr** (standing still = shrinking margins).
- **E-12 (standing service lines).** Unlock after qualifying contracts completed **twice**;
  quarterly obligation check; failing a check auto-suspends (no penalty, lost income only) from the
  next month, resumes the month after the next satisfied quarter:

| Line | Income | Unlock | Quarterly obligation |
|---|---|---|---|
| LEO constellation maintenance | $5M/month | 2× CT-03 or CT-05 | ≥1 player flight rendezvousing with a customer satellite |
| Station-keeping boost services | $2M/month | 2× CT-04, CT-08, or CT-09 | ≥1 docking-or-boost op on a customer asset |
| Planetary-data subscription | $0.2M/GB fresh SurveyData, cap 50 GB/yr | 2× CT-18 or CT-22 | pays per GB delivered; lapses after 2 consecutive zero-delivery quarters |

### 1.4 Contract templates — full ladder (§4.1, Career)

Values = 2049–2052 openings; rates decline 8%/yr per E-11. `[A#]` = act availability.

| ID | Template | Act | Payout | Deadline basis |
|---|---|---|---|---|
| CT-01 | Sounding payload, 100 km | A1 | $2M flat | 60 d |
| CT-02 | Smallsat to LEO | A1 | m × **$8,000/kg** (0.2–2 t) | 120 d |
| CT-03 | Constellation batch deploy | A1–2 | $5M/sat × 20–60 sats, per-unit pay | 2 yr |
| CT-04 | GEO-slot comsat delivery (sat supplied) | A1–2 | $50M | 1 yr |
| CT-05 | Agency LEO cargo (CRS-style, recurring) | A1–2 | m × $8,000/kg, 2–6 t | per window |
| CT-06 | Crew seat to agency LEO station | A1–2 | **$30M/seat** | per window |
| CT-07 | Orbital tourism, LEO, 2–4 pax | A1–3 | $40M/seat × (1 + P/1000) | flexible |
| CT-08 | Debris remediation (large object) | A1–2 | $90M/object | 2 yr |
| CT-09 | Hubble reboost (**unique**) | A1–2 | $150M + Prestige +25 | 3 yr |
| CT-10 | In-flight abort demo | A1 | $25M | 1 yr |
| CT-11 | Lunar surface delivery (CLPS-style) | A2 | m × **$400k/kg** (50–500 kg); steps to $100k/kg at world T2; 8%/yr on top | window + 90 d |
| CT-12 | Lunar sample return, 5 kg | A2 | $120M | 2 yr |
| CT-13 | Lunar crew seat (agency astronaut) | A2 | $100M/seat | per window |
| CT-14 | Propellant to depot (LOX/CH4/LH2, recurring) | A2–4 | m × 1.5 × `L(orbit)` (E-2 destination scaling) | 1 yr |
| CT-15 | Lunar flyby tourism, 2 pax | A2 | $100M/seat | flexible |
| CT-16 | Mars surface delivery | A3 | m × **$2M/kg** (100–500 kg; payout cap $1.0B) | window-locked |
| CT-17 | Mars sample return | A3 | **$1.5B**, 3 tranches | 2 windows |
| CT-18 | NEA characterization survey | A3 | $40M + $0.2M/GB SurveyData | 3 yr |
| CT-19 | Pu238 supply to agency (standing) | A3–5 | **$10M/kg**, ≤ 5 kg/yr | standing |
| CT-20 | Venus cloud-sample return | A4 | $600M | 2 windows |
| CT-21 | Venera 13 capsule recovery (**unique**) | A4–5 | $500M + Prestige +50 | none |
| CT-22 | Outer-planet science package hosting | A5 | $80M + $0.1M/GB | window-locked |
| CT-23 | Heritage documentation (Apollo sites etc.; no-touch per E-16) | A2+ | $20M/site | 1 yr |
| CT-24 | Stranded-asset salvage for owner | A2+ | 30% of asset value | 2 yr |
| CT-25 | Sun–Earth L1/L2 science station (DECISIONS C18 anchor slots) | A1–2 | $60M deploy + $0.1M/GB while hosted | 2 yr |

**Certification wall (E-2, anti-arbitrage):** contract payloads must fly on player-operated craft.
Third-party commercial lift can deliver only player-owned cargo/parts/crew to player-owned
facilities and can **never satisfy a contract delivery**.

### 1.5 Milestones — the "Firsts" ladder (§4.2, E-13)

One-time payments (COTS tranche model), paid automatically, ×funding multiplier (D-2). Repeats pay
nothing. Each fires a Chronicle FIRST entry. Cumulative target hours per G-12.

| Act | Milestone | Payout | Prestige | Target h |
|---|---|---|---|---|
| 1 | First launch (any) | $5M | +5 | 1 |
| 1 | **First orbit** | $30M | +10 | 3 |
| 1 | First stage recovered & reflown | $20M | +5 | 5 |
| 1 | **First docking** | $25M | +10 | 7 |
| 1 | First crewed orbit | $60M | +20 | 9 |
| 1 | In-flight abort demonstrated (pairs CT-10) | — (contract) | +5 | 10 |
| 1 | LEO station core operational (4 crew, 30 d) | $40M | +10 | 11 |
| 1 | First cryo depot transfer demo (T1) — **Act 1 exit** | $50M | +10 | 12 |
| 2 | First lunar flyby / orbit | $40M | +10 | 14 |
| 2 | First robotic lunar landing | $80M | +20 | 16 |
| 2 | Polar ice confirmed by drill | $60M | +10 | 19 |
| 2 | **First crewed lunar landing** | $300M | +50 | 22 |
| 2 | **Lunar ice mine online** (first 10 t Water extracted) | $150M | +30 | 28 |
| 2 | Lunar LOX delivered to orbital depot | $100M | +20 | 32 |
| 2 | Surface base: 4 crew × 90 d continuous — **Act 2 exit** (with LOX-at-depot) | $120M | +20 | 35 |
| 3 | **First NTR burn in orbit** (cold-launch rule) | $100M | +25 | 38 |
| 3 | First robotic Mars EDL | $150M | +30 | 44 |
| 3 | **First crewed Mars landing** | $500M | +75 | 50 |
| 3 | First kg of Mars-made methalox | $80M | +30 | 55 |
| 3 | NEA rendezvous + 100 t volatiles extracted | $120M | +25 | 60 |
| 3 | Mars sample return delivered (pairs CT-17) | — (contract) | +40 | 65 |
| 3 | First off-Earth food harvest — **Act 3 exit** (with methalox) | $50M | +15 | 70 |
| 4 | Main-belt arrival (Ceres-class rendezvous) | $100M | +25 | 80 |
| 4 | Metallic-asteroid mine online (100 t IronSteel refined) | $120M | +25 | 86 |
| 4 | **Venus aerostat deployed** (crewed 30 d) | $250M | +75 | 92 |
| 4 | **Silicon Independence** (wafer fab online) — **Act 4 exit** | $200M | +50 | 100 |
| 4 | Mass driver first throw | $100M | +25 | 105 |
| 4 | Food independence at one site (SSI_food = 1.0, 365 d) | $100M | +25 | 112 |
| 4 | First never-Earth ship (built, fueled, crewed off-Earth) | $150M | +40 | 118 |
| 5 | Jupiter system arrival; Callisto base seed | $200M | +50 | 128 |
| 5 | Europa ocean bore relay online (robotic megaproject) | $150M | +40 | 135 |
| 5 | **Titan landing** (crewed = +75 instead) | $200M | +50 | 140 |
| 5 | **Titan submarine deployed** | $150M | +50 | 150 |
| 5 | Enceladus plume-water harvest (100 t) | $100M | +25 | 158 |
| 5 | Saturn-system permanent base (12 crew × 2 yr) — **Act 5 exit** | $250M | +50 | 168 |
| End | **Foundation Audit passed** ("Foundation Day") | — | +100 | 180–220 |
| End | **Interstellar Precursor launched** | — | +100 | 190–220 |
| End | Precursor crosses 100 AU (≤ 10 yr) | — | +100 | (warped decades) |

Per DECISIONS C19 the ladder **gains demographic entries** (births/generations) with 08's Pass-2
expansion (Phase 6+).

### 1.6 Prestige system (E-13…E-16)

- **E-14.** Scalar P, 0–1,000. **Sources:** milestones (table above); contract bonuses (CT-09 +25,
  CT-21 +50); anomaly visits (+5 × listed multiplier); rescues +50; safety record +5 per consecutive
  year with crewed flights and zero fatalities. **Losses:** crew fatality −100 (founder −150);
  contract failure −10; heritage-zone violation −50; agency-assist bailout −100; stand-down decay
  −5/month; failed investor promise −100.
- **Prestige tiers** = investor gates (P = 50/150/300/500). **Floor** = `max(0, highest gate ever
  crossed − 100)` — history can't be fully erased.
- **E-15 (effects).** Gates investor rounds; contract board size (E-8); recruitment pool quality
  (archetype quality roll +1 per 200 P); tourism pricing ×(1 + P/1000).
- **E-16 (heritage zones).** No mining/industrial **placement** within **10 km** of DERELICT
  heritage anomalies (Apollo sites, Luna 9, Huygens…). Violation: one-time **$100M fine +
  Prestige −50** + agency-contract lockout 1 yr. Debris falling into a zone from a failed landing
  is NOT a violation (placed industry only) — but logs an embarrassing Chronicle entry.

### 1.7 Investors & debt (E-17…E-19, §4.5; teeth per DECISIONS F33 / §9-Q1)

Rounds are **milestone-gated grants with a promise** (equity abstracted away). Raising requires
Prestige ≥ gate + a chosen **promise**: one Firsts milestone delivered within the deadline. Deliver
→ vests (cash paid up front, no clawback). Fail → **Prestige −100, no rounds 5 yr, overhead +10%
for 2 yr** (board oversight).

| Round | Prestige gate | Cash | Promise deadline |
|---|---|---|---|
| Seed | start | $300M (pre-banked, E-1) | tutorial charter |
| Series A | 50 | $250M | 36 mo |
| Series B | 150 | $600M | 36 mo |
| Series C | 300 | $1.5B | 36 mo |
| Series D | 500 | $4.0B | 48 mo |
| Bridge loan | any | ≤ 25% trailing-12-mo revenue | 24 mo @ 12% APR |

- **E-18 (bridge loan).** One revolving instrument; auto-drawn at Cash < 0. Interest accrues as a
  G-9 cost rate (1% of outstanding principal/month); principal is a **bullet at 24 months**,
  auto-repaid earlier when `Cash > 2 × principal`; failure to repay at term → Liquidation flow.
  One loan outstanding at a time (re-borrowable only after full repayment).
- **Teeth ruling (DECISIONS F33 + §9-Q1):** pre-fade rounds get **no board mechanics** beyond the
  promise penalty (v1 leaning-no stands: the antagonist is physics, not shareholders). **Post-fade**
  (E-19): board converts to **advisory** — outstanding promises lose penalty clauses (delivering
  still pays Prestige + Chronicle entry), oversight riders end, no further rounds offered. Board
  commentary persists as news/Chronicle flavor.
- **E-19 (money fade trigger).** When `SSI_program ≥ 0.8` sustained **730 d**: HQ default tab flips
  $ Ledger → Mass Ledger (player-reversible); money never turns off, it stops binding. Staged to
  read as **triumph** (advisory board + rival ticker + crew pensions).

### 1.8 Insurance & accidents (E-20…E-23)

- **E-20 (envelope).** Commercial insurance covers **launch + 1 yr of operations inside Earth's SOI
  only** (deep space uninsurable). Insurable value = hardware catalog value + declared cargo value,
  **cap $2B per risk**.
- **E-21 (premium).** `Premium = V_insured × 6% × f_history × f_payload`.
  `f_history`: 2.0 (design with <3 flights) · 1.0 (3–10 flights) · 0.6 (>10 consecutive successes;
  resets to 1.0 after any failure). `f_payload = 1.5` if nuclear material aboard (also adds a 60-d
  licensing lead time per nuclear launch). Bounds 3.6–12% before the nuclear rider.
- **E-22 (claims).** Total loss → insured value; recoverable-but-crippled → 50% (assessor event,
  7 d). **Player-commanded destruction/scuttling voids coverage**; claims require a failure event
  from the reliability systems. Fraud guard: "engineered" failures accepted but premiums reprice
  (f_history resets); a third voided/edge claim in 10 yr ends coverage offers for that vehicle line.
- **E-23 (stand-downs).** Any crewed fatality freezes crewed launches: **30 d** (uncrewed-vehicle
  fatality, e.g. pad worker) · **90 d** (in-flight, cause found quickly) · **180 d** (in-flight,
  founder or multiple deaths). Ironman ×2. During stand-down: crewed contract deadlines pause
  (force majeure — the only force-majeure source), Prestige −5/month. Uncrewed flights continue.

### 1.9 The rival program (E-30 — cosmetic per DECISIONS F33)

One named rival (procedurally named at campaign start; working example *OrbitalX*) exists as **pure
news texture**: a ticker/Chronicle-ambient feed of rival milestones, paced off the world tier and
the E-2 cost-decline curve. **Strictly cosmetic**: no market share, no contract competition, no
window contention. Surfaces as Class-4 Advisories + optional `RIVAL_NEWS` Chronicle entries; never
gates, devalues, or pays Firsts (Firsts are *program* firsts).

### 1.10 Failure-as-content (F-1…F-5)

- **F-1 (aborts).** Pilot HUD always shows the current abort plan per flight phase (pad abort /
  Max-Q / abort-to-orbit / ballistic-return; stations/bases show evacuation plans + lifeboat
  capacity). Trigger: `Backspace` ×2 within 1 s (covered). Abort demo is paid (CT-10 + milestone).
- **F-2 (rescues).** Stranded detection on every trajectory change + once per sim-day under warp.
  STRANDED iff crew alive AND for every safe harbor {player bases/stations with free berths +
  functioning LS, Earth}: `Δv_available < Δv_required` (+5% margin) OR `t_transfer >
  LS_days_remaining` — AND no other player craft can reach + dock within LS_days_remaining.
  Auto-creates a RESCUE objective: countdown = days-of-LS; planner pre-computes windows; all
  rescue purchases get 7-day delivery (E-5 waiver). Success: **Prestige +50** + Chronicle RESCUE +
  morale arc. A rescue that itself strands chains a second RESCUE objective.
- **F-3 (agency assist).** **Once per campaign**: costs `max($500M, 50% of treasury)` + **Prestige
  −100**; flies a real trajectory (min 30 d prep) — can still fail if LS runs out.
- **F-4 (death economics).** Non-founder crew permadeath; founder death = succession event
  (Prestige −150, all-crew morale −25, overhead +10% for 1 yr); Ironman = game over. Death benefit
  **$10M/fatality** to estate; stand-down per E-23; new contract offers −50% for 6 months
  (deadlines on active contracts unchanged).
- **F-5 (wreckage & salvage).** Failed hardware persists; debris is a conjunction hazard and a
  salvage resource: scrap mass = **0.50 × wreck dry mass**; processing yields **30% of scrap** as
  resources split by source parts' bill-of-materials, remainder = Regolith-class waste.

### 1.11 Tutorial: the Program Charter chain (T-1, §5.8)

Tutorials are **contracts** from a patient seed investor — deadline-free, penalty-free (E-9/E-10 do
not apply; failed charter re-offers). Veteran skip checkbox grants the summed payouts (**$50M**) as
extra starting capital + full UI unlock. Physics never faked (honest margins).

| Clock | Beat | Teaches | Unlocks | Pays |
|---|---|---|---|---|
| 0:00–0:08 | Cold open: sounding rocket on pad, 3 actions to fly | Pilot HUD, staging, warp `,`/`.` | — | — |
| 0:08–0:20 | Charter 1: recover the capsule | aborts, recovery value | Finance tab | $5M |
| 0:20–0:40 | Charter 2: assemble provided orbital launcher; paid Simulation of ascent | Engineer mode, Δv/TWR, sims (D-5) | Designer full palette | $10M |
| 0:40–1:00 | Charter 3: **first orbit** (guided ascent, circularize node, deorbit, reenter) | Planner basics, nodes, event-guard warp | Transfer dialog (C25) | $20M |
| 1:00–1:20 | CT-02 smallsat contract (first real money), fairings | contracts, payload integration, insurance quote | Contract board full | per CT-02 |
| 1:20–1:45 | Charter 4: rendezvous + **first docking**; autodock unlock at end | phasing, target markers, RCS IJKL+HN | station assembly | $15M |
| 1:45–2:00 | Vista beat: station core docked; Flight Director points at Moon; Series A pitch (promise selection) | investors, Prestige, campaign map | Act 2 teasers | — |

Flight Director advisor (T-3): optional, max 1 hint/5 min, never repeats acknowledged hints,
hard-off toggle; hints link Encyclopedia articles (T-4: every UI number hover-links its page).

---

## 2. MONEY → MASS

### 2.1 Launch-cost economics (E-2, E-3)

- **E-2 (commercial LEO lift).** Price per kg to 300 km LEO:
  `L(y, T) = max($100/kg, $1,500/kg × 0.92^(y−2049) × s(T))` with tier steps `s(T0)=1.0,
  s(T1)=0.75, s(T2)=0.55, s(T3)=0.40, s(T4)=0.30`; **"world tier" = player's highest unlocked
  research tier** (no scripted tech calendar). **Destination scaling:** `L(orbit) = L_LEO × (1 +
  2 × Δv_LEO→orbit / 9,400 m/s)` → ≈ ×1.0 LEO, ×1.5 GTO (2.4 km/s), ×1.8 low lunar orbit
  (3.9 km/s), ×2.3 lunar surface (5.9 km/s). Crew seats: `$30M × 0.92^(y−2049)` each, LEO only.
  Certification wall per §1.4 (commercial lift never satisfies a contract delivery).
- **E-3 (own-launch marginal cost).** Propellant (mass × §2.3 prices) + range/licensing **$1M per
  Earth launch** + expended hardware (catalog value of discarded stages) + refurbishment **2% of
  recovered-stage hardware value per reflight** + integration labor **$0.5M/launch at T0–T1,
  $0.1M at T2+**. This is why reuse and depots win Act 1.

### 2.2 Overhead, purchases, sales (E-4…E-7)

- **E-4 (daily overhead).** `OH = $40k (HQ) + $10k×N_pads + $5k×N_active_uncrewed_missions +
  $30k×N_active_crewed_vessels + Σ facility leases + Σ salaries`. Leases: launch site
  $0.3M/quarter; second pad build $20M; tracking-network subscription (needed beyond lunar
  distance) $0.5M/quarter — **auto-cancels** once the player's relay network covers every active
  beyond-lunar mission, **auto-resubscribes** (Class-3 alert) if coverage lapses. **Runway:**
  `runway_d = Cash / max(ε, −(Σincome − Σcost rates))` over recurring G-9 rates only (discrete
  events excluded); displayed **∞** while net rate ≥ 0.
- **E-5 (purchases).** Parts at catalog $M; raw resources at §2.3 Earth prices + E-2 lift if
  delivered to orbit. Lead time to pad: **30 d parts, 7 d resources** (Earth surface only;
  rescue waiver per F-2 = 7 d for everything).
- **E-6 (selling).** Assets/resources sell on Earth at **40% of catalog/list**; saturation (E-25)
  applies to high-value commodities. Selling requires asset on Earth or in LEO.
- **E-7 (no money printer off-Earth).** Money is created only by contracts, milestones, investors,
  and Earth sales. No funds-per-science faucet. Off-Earth value is mass, energy, crew-time.

### 2.3 Earth market — complete price table (§4.3; sell = 40% of buy per E-6)

Includes NTO/MMH rows per DECISIONS A1. `Q_sat "—"` = unsaturable at player scale (`Q_sat = ∞`,
saturation multiplier ≡ 1; the >10×Q_sat refusal rule does not apply).

| Resource | Buy $/kg | Q_sat (sell), t/yr | Note |
|---|---|---|---|
| Water | 0.001 | — | municipal |
| Oxygen (LOX) | 0.20 | — | industrial bulk |
| Hydrogen (LH2) | 6 | — | KSC procurement class |
| Methane (LCH4) | 1 | — | LNG + launch-grade liquefaction |
| RP1 | 3 | — | spelling `RP1` per DECISIONS A1 (no punctuation in resource IDs) |
| Nitrogen | 0.3 | — | industrial LN2 |
| CO2 | 0.1 | — | industrial |
| Ammonia | 0.6 | — | anhydrous |
| **NTO** | **12** | — | storable oxidizer; T3 ISRU route (DECISIONS B11: N2+O2→NTO) |
| **MMH** | **100** | — | storable fuel; T3 ISRU route (B11: Ammonia→MMH) |
| Argon | 1.5 | — | liquid argon |
| Xenon | 1,200 | 60 | shock event ×3 (E-24) |
| Regolith | n/a | — | not traded |
| IronSteel | 0.8 | — | |
| Aluminum | 2.5 | — | |
| Titanium | 25 | — | aerospace mill products |
| Copper | 9 | — | stays near-Earth-scarce (B15) |
| Silicon (solar-grade) | 15 | — | |
| RareEarths | 80 | 20 | |
| Uranium (HALEU) | 30,000 | — | shock ×2 (E-24) |
| Thorium | 100 | — | [game value] |
| Pu238 | 10,000,000 | 0.005 | shock: unavailable 1 yr (E-24) |
| Carbon (graphite) | 1.5 | — | |
| Polymers | 3 | — | |
| BasaltFiber | 4 | — | |
| Glass | 1 | — | |
| Electronics | 20,000 | 50 | falls 5%/yr (E-24 scripted decline) |
| Wafers | 200,000 | 5 | falls 5%/yr |
| MachineParts | 1,000 | — | |
| StructuralParts | 50 | — | = $0.05M/t commodity-structure canon |
| FoodRations | 150 | — | |
| MedSupplies | 2,000 | — | pooled SKU (B13) |
| Biomass | not traded | — | |
| He3 [SPECULATIVE] | sell-only 15,000,000 | 0.1 | T4 only |

Delivered-to-orbit = buy + E-2 lift (destination-scaled). Canonical resource-ID extensions: `RP1`,
`Wafers`, `MedSupplies`, `SurveyData` (intangible, GB) — all code must use these exact spellings.

- **E-24 (shocks).** Prices constant except Electronics/Wafers −5%/yr and supply shocks: each
  listed shock is independent Poisson, mean **one per 15 sim-years**, max one active per commodity,
  duration uniform in range — Xenon ×3 for 1–2 yr; Pu238 unavailable 1 yr; HALEU ×2 for 1 yr.
  Each shock = Chronicle event + ISRU nudge.
- **E-25 (sell saturation).** Marginal pricing: each kg sold at trailing-12-month volume `q` gets
  multiplier `exp(−q/Q_sat)`; a block of Q from q₀ averages `(Q_sat/Q) × (e^(−q₀/Q_sat) −
  e^(−(q₀+Q)/Q_sat))`. Example: He3, Q_sat=100 kg/yr — selling 100 kg from q₀=0 averages `0.4 ×
  $15M × (1−e⁻¹) ≈ $3.8M/kg` (0.4 = E-6). Orders > 10 × Q_sat per transaction refused ("no buyer").

### 2.4 Salaries & staffing (§4.4)

| Item | Value |
|---|---|
| Crew salary, Earth-side reserve | $0.25M/yr |
| Crew salary, flight status | $1.0M/yr |
| Signing bonus (archetype low/mid/high) | $2M / $5M / $12M |
| Training, per skill-level attempt | $2M + 90 d |
| Death benefit (F-4) | $10M |
| Pension, retired crew (DECISIONS F33) | $0.1M/yr per retiree, enters E-4 Σsalaries as a G-9 rate |
| Recruitment pool refresh | 4 candidates/quarter; quality per E-15 |
| Mission-control ops staff | inside E-4 overhead |

### 2.5 The Self-Sufficiency Index (E-26, E-27)

Over a trailing **365 d** window, for every off-Earth site and vessel, classify consumed mass into
category c ∈ {Propellant, LifeSupport, Structure, Parts, Electronics, Nuclear} **by consuming
subsystem, not resource species** (dual-use species — Oxygen, Water, Hydrogen, Methane — would
otherwise misclassify):

| Consuming subsystem | Category |
|---|---|
| Engine / RCS / pressurant | **Propellant** (regardless of species — LOX burned as oxidizer is Propellant) |
| ECLSS / crew systems | **LifeSupport** |
| Construction | **Structure** |
| Maintenance / spares | **Parts** |
| Avionics / fab installation | **Electronics** |
| Reactor / RTG fueling | **Nuclear** |

Fallback species mapping **only** for ambiguous/unmetered sinks (subsystem attribution wins):
LifeSupport (Water, Oxygen, Nitrogen, FoodRations, MedSupplies) · Structure (StructuralParts,
IronSteel, Aluminum, Titanium, BasaltFiber, Glass, Regolith-derived) · Parts (MachineParts) ·
Electronics (Electronics, Wafers) · Nuclear (Uranium, Thorium, Pu238). **Propellant has no
species list** — always subsystem-attributed.

**Formulas:** `SSI_c = 1 − m_imported_from_Earth,c / m_consumed,c` ·
`SSI_program = 1 − Σ_c m_imported,c / Σ_c m_consumed,c` (mass-weighted). Per-site SSI identical per
site. Displayed as the **Umbilical gauge** (Earth with a cord; per-category bars).

**E-27 expected trajectory:** T0 ≈ 0 → T1 ≈ 0.4 → T2 ≈ 0.75 → T3 ≈ 0.95 → T4 ≈ 1.0. Electronics is
the designed long pole (wafer fab at T3 = Silicon Independence).

### 2.6 Foundation Audit — civilization win (E-28)

Passed when **ALL** hold simultaneously for **24 consecutive months**:

| # | Criterion | Threshold |
|---|---|---|
| a | Permanent off-Earth residents | ≥ **50 crew** across ≥ **2 bodies** |
| b | Self-sufficiency | `SSI_program ≥ 0.98` AND every `SSI_c ≥ 0.95` AND FoodRations ≥ **0.99** |
| c | Earth cargo | **zero** Earth cargo manifests (crew transfers permitted) |
| d | Kit closure | χ ≥ **0.90 at ≥ 2 industrial sites** |
| e | Medical + morale | every crewed site has medbay + Medic ≥ 2; mean morale ≥ 60 |
| f | Settlement score | `Σ_sites (occupied_berths × SSI_site) ≥ 50` |
| g | **Demographic pillar (DECISIONS C19)** | biological continuity: births/generations modeled; partial-gravity reproduction researched as uncertainty (centrifuge → mammalian trials → human protocols; gravity thresholds; spin-habitat prescriptions). Criteria (birth count, generational health, gravity-prescription compliance) are **08-owned**, land Phase 6+ — this clause binds the audit to include them |

Passing fires the **Foundation Day** Chronicle chapter + credits; sandbox continues.

### 2.7 Interstellar Precursor — probe win (E-29)

- Research gate: 11's **SH-09 Interstellar Precursor Program** megaproject (T4 [SPECULATIVE],
  12,000 SCI, prereqs `(PR-21 | PR-22) + IN-14`). Researching SH-09 unlocks the project screen —
  the T4 investment (one T4 propulsion node + IN-14 industry seed) is **mandatory regardless of
  which propulsion architecture flies**.
- Flight requirement: uncrewed probe **crosses 100 AU within 10 years of departure** (sustained
  **≥ 10 AU/yr ≈ 47.4 km/s**). Honesty ladder shown in the project screen: Voyager 1 = 3.6 AU/yr;
  best studied chemical/Oberth (APL Interstellar Probe) ≈ 7 AU/yr; ≥10 AU/yr honestly demands T4.
- Two valid architectures: (1) the 02 fusion stage [SPECULATIVE] (PR-22 hardware); (2) staged
  solar-Oberth + multi-MW EP stack from T3 parts (PR-17/PR-18 thrusters on PW-08 reactor cores) —
  there the T4 propulsion node is researched but never flown; it does **not** waive the SH-09 gate.
- Payload: science kit = **Electronics 2 t + 50 kWe-class power**.
- Optional stretch flag at **550 AU** (solar-gravity-lens focal region) → post-credits Chronicle
  epilogue.

### 2.8 Ledger mechanics & insolvency (G-9, §8)

- **G-9 (analytic finance).** Ledger integrates analytically per warp step:
  `Cash(t_now) = Cash(t_prev) + Δt·(Σincome_rates − Σcost_rates) + Σ(discrete events in step)`.
  Discrete events queued with timestamps, processed in order; a Cash sign change inside a step
  forces warp-drop at the zero-crossing time.
- **Death spiral (designed).** Runway < 60 d → Class-3; < 14 d → Class-2 + auto bridge-loan offer.
  True game-over only at: bankrupt AND no income source AND all crew dead/stranded. Before that,
  the **Liquidation flow** (sell at 40%, cancel leases) is always offered; crewed assets are
  liquidation-exempt until crew are home/dead.

---

## 3. UI CANON

### 3.1 The four lenses (G-1…G-6)

Four modes = camera+UI configurations over **one live world**. Switching ≤ 1 frame; sim runs in
all modes, pausable in all; each mode keeps its own camera/selection/scroll (G-3). Exactly one
craft is the *helm* (receives key input); all others fly queued programs; taking the helm
mid-program confirms ("Disengage Node-Execute?") (G-4).

| Key | Lens | Decision timescale | Core loop (~10 s–5 min repeat unit) |
|---|---|---|---|
| **F1** | **Pilot** | 0.1 s–minutes | orient (A/D, hold modes) → throttle (Shift/Ctrl/Z/X) → execute node/manual burn → monitor tapes (alt/vel/AP/PE, prop, Δv) → stage (Space) → set alarm → warp (`.`) |
| **F2** | **Engineer** | minutes | read requirement → place/edit parts on cell grid → live Δv/TWR/cost/mass readouts → validation checks → optional paid Simulation → commit to build queue. Two tabs: **Designer** (free, instant edits) and **Works** (maintenance/EVA/inspections; consumes sim time + resources) (G-5) |
| **F3** | **Planner** (alias `M`) | hours–years | scan Next-Events rail + demand list → transfer dialog (window-bar default, C25) → drop nodes / standing routes → set alarms → contract board pass → warp. **DECISIONS A7: F3 = Planner; the developer perf HUD relocates to `Ctrl+F3`** |
| **F4** | **Base** | days | read dashboards (stocklines, Sankeys, power margin) → adjust policies/recipes/priorities/build orders → resolve maintenance queue → review site alerts → warp. Tab bar over sibling panels: Build, Industry, Life Support, Power/Thermal, Crew, Vehicles, Site Map — with alert badges per tab (G-6) |

Plus: `` ` `` = Program HQ overlay · `Esc` = pause menu · double-click any owned object anywhere
jumps to its native mode (ship→Pilot, blueprint→Engineer, route→Planner, base→Base) ·
`Tab`/`Shift+Tab` cycles owned craft in Pilot (G-2).

### 3.2 Time & session (G-7…G-11)

- **G-7.** Epoch 2049-01-01 00:00 UTC; UI shows sim date UTC + mission-elapsed times.
- **G-8.** Warp ladder verbatim from 01: 1x, physics 2–4x, rails 5x→1,000,000x, with 01's event
  guard; alert interrupts (A-2) layer on top.
- **G-10 (session template).** Designed 30–90 min session = **Review → Plan → Execute → Warp**.
  Load screen = *Captain's Log* card (last 5 Chronicle entries + next 3 events + cash/SSI headline).
  **Next-Events rail** (top of every mode) lists next 5 queued events. Autosave on quit and at
  every launch/landing/docking/SOI change (rolling 10 slots).
- **G-11 (alarms).** Player alarms (absolute / relative / event-linked "window −7 d") enter the
  event queue, stop warp at tier 0, carry a note + jump-link.

### 3.3 Screen inventory (§4.8) — every major screen

| ID | Screen | Mode/access | Required elements (this doc owns) |
|---|---|---|---|
| S-01 | Flight HUD | Pilot | layout, tapes (auto-switch by regime: ascent/orbit/approach/landed), alert strip, abort-plan line always present on crewed flights, burn UI (t_b countdown, split-burn) |
| S-02 | System Map / Planner | Planner | frame, filters (craft/stations/bases/routes/contracts/anomalies/debris), Next-Events rail |
| S-03 | Transfer dialog | Planner | **1D window bar default** (Δv color + trip time vs departure date, next windows flagged/countdown); full 2-axis porkchop behind **Advanced** toggle, sticky per save (DECISIONS C25) |
| S-04 | Logistics routes | Planner | frame; 05's node-graph overlay w/ gear ratios + propellant bills |
| S-05 | Contract board | Planner/HQ | cards: payout, deadline, feasibility hint ("no current capability" flagged honestly vs fleet Δv/windows) |
| S-06 | Vehicle Designer | Engineer | frame, cost-ledger strip (full E-3 marginal cost of next flight + E-21 insurance quote inline), SIMULATE button w/ price |
| S-07 | Works (maintenance/EVA) | Engineer | frame |
| S-08 | Base Build | Base | frame |
| S-09 | Industry dashboard | Base | frame |
| S-10 | Life Support panel | Base/vessel | frame (08 Sankey content) |
| S-11 | Power/Thermal grid | Base | frame |
| S-12 | Crew roster & schedule | Base/HQ | frame, recruitment market (§2.4 prices) |
| S-13 | Program HQ | `` ` `` overlay | **$ Ledger** (cash, runway, in/out $M/mo by line, insurance in force, next-round progress) and **Mass Ledger** (Umbilical SSI gauge + per-category bars, t/day flows by site/route, Earth manifest queue); default tab flips at E-19 |
| S-14 | Research | HQ tab | frame (11 content) |
| S-15 | Alert Center | HQ tab | filterable table of active + historical alerts; jump-links; owning system; formula-grade detail (hover any number → its defining equation + inputs) |
| S-16 | Chronicle | HQ tab | the generated-history browser (Dwarf Fortress legends-mode ancestry) |
| S-17 | Encyclopedia | `F11` / hover-links | every mechanic page carries its real-world-anchor paragraph |
| S-18 | Settings/Difficulty | Esc | presets + per-toggle UI, integrity-asterisk notice (D-3) |
| S-19 | Photo mode | F10 | C-5 spec (§4.5 below) |
| S-20 | Save/Load + Captain's Log card | Esc | G-10 card |

### 3.4 Global layout grammar (§5.1, §5.7)

Every mode shares: **top** status bar (date/warp widget, cash or mass headline, Prestige,
Next-Events rail) · **right** context panel (selection properties) · **bottom** alert strip
(toasts + Master Alarm) · **left** mode palette. One window; no modal stacking deeper than 2; UI
render ≤ 4 ms/frame at 1080p; vector chrome; monospace numerals.

**The Altimeter Rule:** the 1–3 numbers that can kill you in this mode are the largest on screen
(Pilot: altitude/velocity/propellant · Base: days-of-LS/power margin · HQ: runway-days). Every
number hover-expands to its formula ("readout honesty").

**Palette:** background `#0A0E14`, grid `#18202B`, text `#E6EDF3`. Semantic: player **cyan
#57C7E3** · inert/derelict **grey-white #9AA7B0** · nominal **green #44CC77** · Caution **amber
#E8C547** · Warning **orange #E8893B** · Emergency/loss **red #E25555** · radiation **magenta
#C678DD** · cryo/water **blue #5398D9** · thermal **deep orange #D97E4A** · money/Prestige **gold
#D9B354**. Rules: semantic colors never decorative; **shape carries meaning redundantly** (bodies
= circles, craft = triangles, stations = squares, bases = pentagons, debris = ×, anomalies =
diamonds, contracts = ring-badges) so the deuteranopia palette swap never changes meaning; line
weight 2 px player / 1 px others; solid = current, dashed = planned, dotted = history; fills mean
"selected" or "alarmed" only.

**UI ancestry (binding §5.0):** copy proven idioms verbatim — KSP flight scene (navball, staging
stack w/ per-stage Δv, `M` to map; KSP player at home in <60 s), KSP map + Factorio overlays
(Planner), KSP VAB + Factorio blueprints (Engineer), ONI overlay lenses/priorities 1–9 (Base),
RimWorld time cluster + alert chips, Factorio production graphs (HQ), Dwarf Fortress legends
(Chronicle). Novel interactions require written justification.

### 3.5 Alert taxonomy (A-1…A-6 — ISS C&W, four classes)

| Class | Name | Color / sound | Warp effect (Baseline) | Example sources |
|---|---|---|---|---|
| 1 | **EMERGENCY** | red, klaxon | **pause** (tier 0 + pause) | fire, rapid depress, toxic atmosphere; reactor casualty; collision < 60 s; crew incapacitation |
| 2 | **WARNING** | orange, alarm tone | drop to **1x** | engine failure in burn; LS critical band; conjunction < 1 h; insufficient Δv after burn; foundry freeze risk; habitat breach; runway < 14 d; deadline T−7 d |
| 3 | **CAUTION** | amber, chime | cap warp at **1,000x** | caution-band crossings; spares < 90 d projection; boiloff margin; contract T−30 d; runway < 60 d |
| 4 | **ADVISORY** | white, silent | none (log + toast) | arrivals, completed builds, harvest, window-opened, ledger receipts, rival news |

- **A-2 (warp law).** `warp_max_effective = min(warp_player, min over active unacknowledged alerts
  of warp_cap(class))`. Acknowledge (click / `Enter` on focused toast) releases the cap — **except
  Class 1 (latching)**: requires resolution or explicit **Accept-Risk** (covered switch; logged to
  Chronicle forever, optional one-line justification). 01's event guard stays independent.
- **A-3 (toast budget).** Max 3 toasts (top-right, newest on top); overflow → Alert Center badge
  silently. Dedup: identical (source, type) within 24 h sim merge with a ×N counter.
- **A-4 (overrides).** Any event type remappable one class up/down (never out of Class 1), with
  per-type pause/no-pause; stored per save.
- **A-6 (Master Alarm).** Physical-feeling HUD button; key **`Delete`**: acknowledges all Class
  2–3 **audio** at once, leaves warp caps until individually acknowledged. (`Backspace×2` is
  reserved for abort.)
- **Storm rule (§8.3).** >10 Class-2/3 alerts within 60 s collapse into one "CASCADE at <site>"
  Class-2 card with a tree view showing root cause first.
- **Audio (§5.10).** Exactly three alarm sounds (klaxon/tone/chime); telemetry-blip ambience
  scales with warp; silence in vacuum exterior shots; music ducks under Class 1–2.

### 3.6 Keybindings (§5.9 — defaults; full remap; presets "Default", "KSP-émigré", "Left-hand mirror")

Philosophy: mouse-complete (keys accelerate); one home cluster per hand per mode, no required
chords (modifiers = fine/coarse only); identical keys never change meaning across modes;
destructive actions are double-press or covered-switch.

| Key | Action |
|---|---|
| `F1–F4` | modes Pilot/Engineer/Planner/Base |
| `Ctrl+F3` | developer perf HUD (DECISIONS A7) |
| `M` | Planner alias |
| `` ` `` | HQ overlay |
| `,` / `.` | warp down/up; `Alt+,/.` physics warp |
| `Space` | stage (Pilot) / confirm (dialogs) |
| `A` / `D` | rotate CCW/CW |
| `Shift` / `Ctrl` | throttle up/down; `Z` full, `X` cut |
| `CapsLock` | fine-control toggle |
| `R` | RCS toggle; `T` attitude-hold cycle |
| `I/K/J/L` | translate (screen axes); `H/N` fore/aft |
| `Backspace` ×2 (within 1 s) | ABORT (covered) |
| `Delete` | Master Alarm |
| `Tab` / `Shift+Tab` | cycle craft |
| `Enter` | acknowledge focused toast |
| `F5` / `F9` | quicksave/quickload (disabled in Ironman) |
| `F10` | photo mode; `F12` screenshot |
| `F11` | Encyclopedia |
| `Ctrl+P` | command palette (search ships/screens/contracts) |
| `+/-` / wheel | zoom; `V` camera mode |
| `1–9` | action groups |
| `Esc` | pause menu |

### 3.7 Progressive disclosure (T-2) & difficulty (D-1…D-6, §4.6)

UI modules unlock on first relevance — locked modules visible but greyed with a one-line "unlocks
when…" (no hidden screens): Finance tab after first contract · transfer dialog after first orbit
(Advanced porkchop ships with it) · Base mode at first surface/station asset · Industry dashboards
at first fab module · SSI gauge at first off-Earth production.

| Preset | Funding | Boiloff | Radiation | Failures | Light-lag | Ironman | Sims/Reverts |
|---|---|---|---|---|---|---|---|
| Training | ×1.5 | simplified (×0.25) | no-death | reduced (×0.25) | off | off | sims free; reverts loose (any flight ≤15 min, fee refunded); asterisked |
| **Baseline** | ×1.0 | full | full | full | on | off | sims paid; D-6 reverts — **the designed game** |
| Veteran | ×0.6 | full | full | full | on | off | sims paid, no reverts; asterisk-free |
| Ironman | ×0.6 | full | full | full | on | **on** | sims paid, none; single rotating save; founder death = game over; stand-downs ×2 |
| Sandbox | off | any | any | any | any | off | free; separate save class; Chronicle still records |

- **D-3 (integrity marker).** Any toggle below Baseline permanently asterisks the save + Chronicle
  with the settings list; mid-campaign changes apply forward-only and are themselves Chronicle
  entries. Life-support consumption is always ON in Career.
- **D-5 (Simulation — the diegetic revert).** Run any planned segment as a sandboxed
  SIM-watermarked copy, no consequences. `C_sim = $0.1M + 0.5% × hardware value of simulated
  vehicles`, cap $2M, once per sim session. Available in Ironman (engineering tool, not a cheat).
- **D-6 (revert-to-pad).** Baseline: only ≤ 5 min after liftoff AND pre-declared **Test Flight**
  (no contract payload, no crew XP, range fee still paid). Ironman: never.

---

## 4. THE CHRONICLE

### 4.1 Record schema (C-1)

Append-only log. Entry = `(t_sim, type, class, subjects[], location, numbers{}, autoshot_id, seed)`.
Target volume **200–800 entries per campaign**. Auto-written on: every FIRST, death, disaster,
rescue, contract landmark, audit, anomaly visit, accepted Class-1 risk, act transition.

### 4.2 Entry types (§4.9 — complete list)

`FIRST_*` (one per Firsts-ladder row, §1.5) · `LAUNCH` · `LANDING` · `DOCKING` · `SOI_ARRIVAL` ·
`CONTRACT_WON` / `CONTRACT_DONE` / `CONTRACT_FAILED` · `ROUND_RAISED` · `DEATH` (epitaph card) ·
`RESCUE` · `DISASTER` (Class-1 with loss) · `RISK_ACCEPTED` · `STANDDOWN` · `ANOMALY` · `WONDER`
(completion of a flagged megaproject — Europa ocean bore relay, first mass driver, Venus aerostat —
or the E-29 precursor vehicle) · `HERITAGE_VIOLATION` · `BANKRUPTCY_NEAR` · `AUDIT_PASS` /
`AUDIT_FAIL` · `ACT_CHAPTER` · `SETTINGS_CHANGED` (D-3) · `PHOTO` (pinned) · `RIVAL_NEWS` (E-30,
cosmetic, optional) · `EPILOGUE`.

### 4.3 Generation rules (C-2…C-4)

- **C-2 (auto-shot).** Each entry captures a **vector scene snapshot** (scene graph, not pixels —
  re-renderable at any resolution; 13 owns the buffer format). Entries render as cards with
  deterministic **template-grammar** text in dry mission-report tone: *"2053-08-14 — PELICAN-3 set
  down at Shackleton Rim. First crewed lunar landing of the program. Crew: Vasquez, Okafor. Margin
  at touchdown: 4.1% propellant."* Variant budget: **~8 templates × 25 types** (§9-Q7).
- **C-3 (chapters).** Act transitions and audits generate **chapter cards** with auto-computed
  stats (launches, tonnage to orbit, fatalities, $ and t flows, firsts).
- **C-4 (epitaphs & patches).** Dead crew get permanent memorial entries (name, role, hours,
  missions, cause) + a Memorial wall in HQ. Retired crew keep roster cards and appear in the
  epilogue (pension $0.1M/yr per F33). Every named mission auto-generates a **vector mission
  patch** (procedural emblem seeded by name/body/vehicle) used on its cards; the patch generator
  is first cut if art budget tightens (§9-Q10).
- **Memory cap (§8.12).** Snapshots ≤ 64 kB each, ≤ 2,000 entries; beyond cap, oldest
  non-FIRST/DEATH entries degrade to text-only.

### 4.4 Export format (C-3)

Endgame export — **"The Program, 2049–20XX"** — a scrollable **HTML file + PNG poster timeline**
rendered from the vector snapshots. This export is the intended trophy of a campaign.

### 4.5 Photo mode (C-5)

`F10`: pauses (sim-safe in Ironman), free camera, UI hide, line-weight boost, palette filters
(Blueprint, Mission-Patch, Archival-Print), annotation stamps (date, craft name, velocity vector),
PNG export up to 4× window resolution via vector re-render. Any photo pinnable to the Chronicle as
a manual `PHOTO` entry.

---

## 5. GAP vs CODE

Code audited: `aphelion/game/campaign.py` (181 lines), `aphelion/sim/economy.py` (100 lines),
`aphelion/main.py` scene/overlay structure.

### 5.1 Campaign / contracts

| Design | Code today | Gap |
|---|---|---|
| 25 procedural templates (CT-01…25) + ~10 hand-authored uniques + 38-row Firsts ladder + 4-charter tutorial chain | **21 bespoke one-shot contracts** in `CONTRACTS` tuple — a fused contract/milestone hybrid | Split into (a) repeatable templates w/ weekly board, capability filters, cooldowns, urgency variants, $/kg payout formulas; (b) the Firsts ladder as auto-paying milestones; (c) charters |
| 5 acts + endgame, theaters Earth/Moon/Mars+NEA/Belt+Venus/Jup+Sat; act advance = **exit milestone** (G-13) | 4 acts (LEO+Luna / inner / outer / way-out); advance at **≥60% of previous act** | Re-theater acts; replace 60% gate with exit-milestone trigger; add `ACT_CHAPTER` events |
| E-9 10% advance; E-10 repay+20%+P−10+lockout; E-11 urgency; deadlines from transfer tables | flat payout on completion; fail → re-offer ×0.6 haircut (max 2 retries); +25% early bonus | Advance/penalty/insured-value model replaces haircut/bonus (or keep haircut as the renegotiation UX for charters only) |
| Investors (5 rounds w/ promises), bridge loan, standing services, insurance, stand-downs, Prestige, heritage zones, rival ticker, agency assist, rescues | **none of these exist** | All new systems; Prestige gates the board size and rounds so it's load-bearing early |

### 5.2 Economy

| Design | Code today | Gap |
|---|---|---|
| §4.3 per-resource Earth prices (34 rows incl. NTO/MMH), E-2 lift formula w/ tier steps + destination scaling, E-3 marginal launch cost, E-6 40% sales, E-24 shocks, E-25 saturation | `part_cost_usd`/`vessel_cost_usd` (tier-multiplier hardware pricing) + flat `$120k/t` propellant | Resource price table, lift pricing, range fee/refurb/integration line items, sell-side, shocks, saturation all missing |
| E-4 overhead (HQ/pads/missions/leases/salaries) + runway readout + G-9 analytic ledger w/ mid-step insolvency warp-drop | `Program.funds` + history list; no recurring rates at all | Rate-based ledger is prerequisite for runway, overhead, salaries, pensions, loan interest |
| SSI (E-26 subsystem attribution, Umbilical gauge), E-19 money fade, E-28 Foundation Audit (7 criteria), E-29 precursor (100 AU ≤ 10 yr, SH-09 gate) | win = `c_precursor` check: hyperbolic solar orbit while carrying `core:probe_longshot` | SSI accounting, audit engine, and the 10 AU/yr sustained-speed requirement (current check has **no speed/time requirement**) |

### 5.3 UI

| Design | Code today | Gap |
|---|---|---|
| Four lenses F1–F4 + `` ` `` HQ + G-2 jump/cycle semantics | scenes: menu/flight/ascent/descent/proxops/victory; overlays on letters (base F2-ish, research R, crew K, contracts O, planner P, help F1) | Key map conflicts with canon (F1 = Pilot, not help; R = RCS toggle, not research); modes are scene-switches, not persistent lenses w/ preserved camera/selection |
| A-1 four alert classes w/ warp caps, latching Class 1, Accept-Risk, Master Alarm, toast budget, Alert Center, storm rule | toast lines only | Entire alert bus + warp-interrupt law missing |
| S-01…S-20 screen inventory; HQ two-ledger screen; transfer dialog (window bar + Advanced porkchop per C25); contract board w/ feasibility hints | flight map, builder, base/research/crew/contracts/planner overlays exist in some form | Missing: HQ ledgers, Alert Center, Chronicle, Encyclopedia, Settings/Difficulty, Photo mode, Captain's Log, Works tab, recruitment market |
| §5.7 semantic palette + shape redundancy + deuteranopia swap; Altimeter Rule; Next-Events rail; D presets; D-5 paid Simulation; T-1 charter onboarding | THE LOOK update visual layer exists; none of the semantic-token/disclosure/difficulty systems | Token-ize colors; add rail, presets, sims, charters |

### 5.4 Chronicle

Nothing exists in code. Needs: append-only store w/ C-1 schema, 25 entry types, template grammar,
vector-snapshot hook, chapter cards, Memorial wall, HTML+PNG export, photo pinning, memory caps.

---

## Build-order suggestion (dependency-driven)

1. **Rate-based ledger (G-9)** — all finance (overhead, runway, salaries, loans, services) hangs
   off it.
2. **Alert bus (A-1/A-2)** — every system registers events into it; the warp law depends on it.
3. **Contract board rewrite** (templates + Firsts split + Prestige) — replaces campaign.py's fused
   model.
4. **Investors/insurance/stand-downs/rescues** — pure consumers of 1–3.
5. **SSI accounting + E-19 fade + HQ two-ledger screen.**
6. **Chronicle** (consumes events from 2–5), then audits/wins (E-28/E-29). Per DECISIONS C19,
   E-28(g) demographics land with 08's Phase 6+ expansion — stub that criterion behind a flag.
