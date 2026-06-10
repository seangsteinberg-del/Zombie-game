# 12 — Gameplay Loop, Campaign, Economy & UI

**Owner:** Gameplay/Economy/UI domain. **Status:** v1 design-complete draft.
**This document owns:** the four play modes and mode-switching, the session loop and campaign arc, all money (prices, contracts, milestones, investors, insurance, salaries), the Prestige/reputation economy, the self-sufficiency metric and the money→mass transition, difficulty/realism toggles, failure-as-content (rescues, aborts, stand-downs), the alert/notification bus and its time-warp interrupt rules, every major screen, the color/iconography language, keybindings, onboarding, the Chronicle, and photo mode.
**This document does NOT own:** physics (01), engines (02), bodies (03), ISRU chemistry (04), production rates (05), part stats (06/07), crew biology (08), power (09), vehicles (10), research-tree costs (11), engine architecture (13). Where a sibling exposes a screen's *content* (e.g., the Life-Support Sankey, 08 §5), this document owns the *frame* it appears in.

All money figures are **constant-2049 US dollars** ($k / $M / $B); no inflation is simulated. All other units SI per project convention.

---

## 1. Overview

Aphelion is played as one continuous program, 2049 → ~2090+, through four *lenses* on the same persistent world:

- **Pilot (F1)** — fly one craft in real time under time control. Seconds-to-minutes decisions.
- **Engineer (F2)** — design vehicles, modify blueprints, queue repairs and EVA work orders. Minutes decisions.
- **Planner (F3)** — the system map: transfers, logistics routes, contracts, alarms. Hours-to-years decisions.
- **Base (F4)** — colony management: construction, industry, life support, power, crew. Days decisions.

The macro-structure is the five-act campaign fixed by project conventions (Act 1 Earth+LEO … Act 5 outer planets, then megaproject endgame). The economic arc is the game's signature: **Acts 1–2 are about money** (contracts, milestones, investors — a cash-starved private program clawing off Earth), **Act 3 is the hinge**, and **Acts 4–5 are about mass** — money fades into a side-tab as logistics becomes the economy, measured by the **Self-Sufficiency Index (SSI)**. The campaign ends in one or both megaprojects: the **Interstellar Precursor probe** and the **Foundation Audit** (self-sufficient off-Earth civilization).

Failure is content, not a fail state: aborts, rescues, insurance claims, accident stand-downs, and dead crew all become entries in **the Chronicle**, the auto-generated history of the program that is itself the endgame artifact.

### Out of scope for v1 (explicit)

- **Multiplayer** of any kind (including async/ghost programs).
- **Combat**, weapons, piracy, military contracts.
- **Aliens / extant extraterrestrial life** as actors. Biosignature science (e.g., Enceladus organics) is flavor text and SurveyData only; no discovery-of-life storyline.
- **Terraforming** (planetary-scale engineering beyond single bases/aerostats).
- AI competitor space programs with simulated market share (the market is a static-curve abstraction, §3.8).
- Earth-side politics simulation (elections, wars). The Earth economy is a stable backdrop with scripted price curves and rare supply-shock events.
- Modding API, localization beyond English, VR, controller-first UI (keyboard+mouse primary; pad mappings best-effort).
- Procedural narrative characters beyond the Flight Director advisor and crew trait system (08).

---

## 2. Real-World Grounding

Every economy and pacing number below is anchored. The hostile-fact-checker list:

**Program economics**
- **NASA COTS** (2006–2013): $396M to SpaceX, $288M to Orbital, paid in ~20–40 discrete milestone tranches of order $10M each → our "Firsts" milestone payments (§3.5).
- **Ansari X Prize** (2004): $10M for first private crewed suborbital reflight → milestone scale sanity check.
- **NASA CRS** ISS resupply (NASA OIG reports): effective delivered-cargo prices of roughly **$60,000–90,000/kg** across CRS-1/CRS-2 → our agency LEO cargo rates ($8,000/kg in 2049) are conservative extrapolations down the cost curve.
- **NASA Commercial Crew** (OIG, 2019): ≈ **$55M/seat** (Crew Dragon), ≈ $90M/seat (Starliner); Soyuz seats $86M (2019 contract era), peaking at **$90.25M** (final purchased seat, Oct 2020) → our 2049 crew-seat contract $30M.
- **CLPS** lunar task orders (2019–2024): $77M–$323M orders implying ≈ **$0.8–1.2M per kg** delivered to the lunar surface → Act 2 lunar delivery rates.
- **Falcon 9**: 2020s list price ≈ $67–70M, ≈ $3,000–4,000/kg to LEO → 06's canon **$1,500/kg commercial LEO lift in 2049** (this doc owns its evolution, §3.3). The observed commercial decline is ≈ **3–5× in $/kg over 2006–2026** (Atlas V / Ariane 5 class ≈ $8,000–14,000/kg in 2006 vs Falcon 9 ≈ $3,000–4,000/kg), i.e. ≈ **6–8%/yr**; an order-of-magnitude drop holds only vs the Shuttle era (≈ $54,000/kg, 1981–2011). The $1,500/kg 2049 anchor assumes that curve **flattened to ≈ 3%/yr over 2026–2049** ($3,000 × 0.97²³ ≈ $1,500); in-game, E-2's 8%/yr plus tier steps then resume the historical pace from 2049.
- **Space insurance market**: launch+first-year premiums historically **4–12%** of insured value, higher for unproven vehicles; deep-space missions are effectively uninsurable commercially → §3.7, including the "no coverage beyond Earth SOI" rule.
- **Accident stand-downs**: Apollo 1 ~21 months, Challenger 32 months, Columbia 29 months, CRS-7 ~6 months, AMOS-6 ~4.5 months → our investigation stand-down durations (30–180 days, game-compressed).
- **ClearSpace-1** (ESA, 2020): €86M for one large-debris removal → debris-remediation contract $90M.
- **Iridium NEXT** (~$3B / 75 satellites incl. build) → constellation-deployment contract scale.
- **NASA astronaut salary**: ≈ **$152k/yr** (2023 single-rate GS scale) → crew salaries $0.5–1.0M/yr as private hazard-pay multiples (×3–6).

**Commodity anchors (Earth market, §4.3)** — industrial LOX ≈ $0.2/kg; LH2 ≈ $4–6/kg (KSC procurement history); LNG/methane ≈ $0.6/kg; Xenon ≈ $1,200/kg with documented 2022 supply-shock spikes >×3; aluminum ≈ $2.5/kg and copper ≈ $9/kg (LME); steel ≈ $0.7/kg; solar/semi-grade polysilicon ≈ $10–30/kg; mixed rare-earth-oxide basket ≈ $50–200/kg (2010s–20s volatility); He-3 post-2009-shortage ≈ $2,000+/L STP ≈ **$15M/kg**; Pu-238: the DOE/NASA Supply Project restart was estimated at **$75–90M total over ~5 yr** (NASA's RPS program line, ≈$150M/yr, funds far more than Pu production — RTG hardware, iridium clads, infrastructure), and independent production-cost estimates cluster near **≈$8M/kg** (GAO-17-673) — we use $10M/kg and say so; HALEU projected mature price ≈ $20–30k/kg (DOE/Centrus demo lots cost far more).

**Operations & UI anchors**
- **ISS Caution & Warning system**: exactly four classes — Emergency, Warning, Caution, Advisory — with distinct annunciation → our alert taxonomy (§3.11) is a direct adoption.
- **Shuttle abort modes** (RTLS/TAL/ATO/AOA; STS-51-F flew a real Abort-To-Orbit, 1985) and **Apollo ascent abort modes I–IV** → per-phase abort-plan UI (§3.13).
- **Mission simulation practice** (hardware-in-the-loop sims, Monte Carlo mission design) → the diegetic paid "Simulation" feature that replaces save-scumming (§3.10).
- **Voyager 1 escape speed ≈ 17 km/s ≈ 3.6 AU/yr**; **JHU/APL Interstellar Probe study ≈ 7 AU/yr**; solar-gravity-lens focal region begins ≈ **550 AU** → endgame probe requirement of ≥10 AU/yr is deliberately beyond every studied chemical architecture, i.e., honestly T4 (§3.9).
- Design lineage (games): KSP (map/flight split, maneuver nodes), Oxygen Not Included (legible flow dashboards), Factorio (logistics-as-economy), Dwarf Fortress (history log → Chronicle), RimWorld (failure-as-story).

---

## 3. Game Model

Rules are numbered **G-x** (modes/time), **E-x** (economy), **D-x** (difficulty), **A-x** (alerts), **F-x** (failure-as-content), **C-x** (Chronicle), **T-x** (tutorial). A programmer implements from these.

### 3.1 Modes and switching (G-1…G-6)

- **G-1 (lenses, not rooms).** The four modes are camera+UI configurations over one live world. Switching is instant (≤ 1 frame; perf contract with 13). Sim time runs in all modes and is pausable in all modes.
- **G-2 (switch inputs).** `F1` Pilot, `F2` Engineer, `F3` Planner (alias `M`), `F4` Base, `` ` `` Program HQ overlay, `Esc` pause menu. Double-clicking any owned object anywhere jumps to its native mode (ship → Pilot, blueprint/dock job → Engineer, route/transfer → Planner, base → Base). `Tab`/`Shift+Tab` cycles owned controllable craft within Pilot.
- **G-3 (context preservation).** Each mode keeps its own camera, selection, and scroll state; returning restores it exactly.
- **G-4 (control focus).** Exactly one craft is "under the player's hand" (receives key input) at a time — the *helm*. All other craft fly their queued programs (01 autopilot programs, 05 routes). Taking the helm of a craft mid-program shows a confirm ("Disengage Node-Execute?").
- **G-5 (Engineer contexts).** Engineer mode has two tabs: **Designer** (vehicle/blueprint editing; content rules from 06 §3 and 05 blueprint studio) and **Works** (maintenance queue, EVA work orders, inspections; content from 05 §5, 08 EVA planner). Design *editing* is free and instant; construction/repair consumes sim time and resources per 05/06.
- **G-6 (Base mode container).** Base mode is a tab bar over sibling-owned panels for the selected site: Build (07), Industry (05), Life Support (08), Power/Thermal (09), Crew (08), Vehicles (10), Site Map (07). This doc owns the frame, tab order, and alert badges on tabs.

**Moment-to-moment loops** (what the player's hands do):

| Mode | Timescale of decisions | Core loop (repeat unit ~10 s – 5 min) |
|---|---|---|
| Pilot | 0.1 s – minutes | orient (A/D, hold modes) → throttle (Shift/Ctrl/Z/X) → execute node or manual burn → monitor tapes (alt/vel/AP/PE, prop, dv) → stage (`Space`) → set next alarm → warp (`.`) |
| Engineer | minutes | read requirement (contract payload, failure report) → place/edit parts on the 06 cell grid → watch live Δv/TWR/cost/mass readouts → run validation checks (06) → optionally pay for a Simulation run (§3.10) → commit to build queue |
| Planner | hours–years | scan Next-Events rail and demand list → open transfer dialog (01 Hohmann/porkchop data) → drop nodes / create standing route (05) → set alarms → contract board pass (accept/decline) → warp to next event |
| Base | days | read dashboards (stocklines, Sankeys, power margin) → adjust policies (08), recipes/priorities (05), build orders (07) → resolve maintenance queue → review site alerts → warp |

### 3.2 Time, the ledger tick, and the session loop (G-7…G-11)

- **G-7 (clock).** Campaign epoch **t₀ = 2049-01-01 00:00 UTC** (ephemeris alignment per 01). All UI shows sim date UTC + mission-elapsed times.
- **G-8 (warp).** Time control is 01's ladder verbatim: 1x, physics warp 2–4x, rails 5x→1,000,000x, with 01's event guard. This doc adds the *alert* interrupts (§3.11) on top of 01's *event* guard.
- **G-9 (analytic finance).** The money/Prestige ledger integrates analytically per warp step (binding, per 01 §3.6 background-simulation rule): `Cash(t_now) = Cash(t_prev) + (t_now − t_prev)·(Σincome_rates − Σcost_rates) + Σ(discrete events in [t_prev, t_now])`. Discrete events (contract payouts, purchases, claims) are queued with timestamps and processed in order; a sign change of Cash inside a step forces warp-drop to handle insolvency events at the correct time (§8.4).
- **G-10 (session template).** The designed 30–90 min session is **Review → Plan → Execute → Warp**: the load screen shows a *Captain's Log* card (last 5 Chronicle entries + next 3 upcoming events + cash/SSI headline); the **Next-Events rail** (top of every mode) lists the next 5 queued events (nodes, windows, arrivals, deadlines, ledger events, alarms) so there is always a visible hook. Autosave on quit and at every launch, landing, docking, and SOI change (rolling 10 slots).
- **G-11 (alarm clock).** Player-set alarms (absolute date, relative offset, or event-linked "window minus 7 d") enter 01's event queue and stop warp at tier 0. Alarms can carry a note and a jump-link to an object/screen.

### 3.3 Money: prices, launch costs, overhead (E-1…E-7)

- **E-1 (starting state).** Career start: **$300M cash** (seed round, already raised), one leased coastal launch site (pad + integration hangar + mission control), T0 catalog access (06/02), 2 generated crew candidates on file, Prestige 0. Anchor: SpaceX's ~$100M founding capitalization (2002, ≈$170M in 2020s dollars) plus seed-era CLPS/COTS environment — a plausible 2049 Series-seed for a deep-space startup.
- **E-2 (commercial LEO lift).** Buying third-party launch (no design fun, per 06 §3.13): price per kg to 300 km LEO
  `L(y, T) = max( $100/kg , $1,500/kg × 0.92^(y−2049) × s(T) )`, with tier step `s(T0)=1.0, s(T1)=0.75, s(T2)=0.55, s(T3)=0.40, s(T4)=0.30` applied when the world reaches that tier — **"world tier" = the player's highest unlocked research tier per 11** (the player's program is the era's pacing actor; there is no separate scripted world-tech calendar). The 8%/yr decline resumes the observed 2006–2026 pace (≈6–8%/yr; per §2 the historical curve is assumed to have flattened to ≈3%/yr over 2026–2049, which is what makes the $1,500/kg 2049 anchor consistent with ≈$3,000/kg in 2026). **Destination scaling** (used by CT-14, E-5, and any non-LEO commercial delivery): `L(orbit) = L_LEO × (1 + 2 × Δv_LEO→orbit / 9,400 m/s)` with Δv from 01's transfer tables (≈ ×1.0 LEO, ×1.5 GTO at Δv ≈ 2.4 km/s, ×1.8 low lunar orbit at ≈ 3.9 km/s, ×2.3 lunar surface at ≈ 5.9 km/s). Crew seats on commercial lift: `$30M × 0.92^(y−2049)` each, only to LEO. **Certification wall (no arbitrage):** contract payloads must be flown on player-operated craft; commercial lift can deliver only player-owned cargo/parts/crew to player-owned facilities and can **never satisfy a contract delivery** — in-fiction, agency and customer contracts buy *operator certification*, which third-party lift cannot provide. This closes the CT-02/CT-05/CT-14 money pump against E-2 prices (E-7).
- **E-3 (own-launch marginal cost).** Flying your own vehicle costs: propellant (mass × §4.3 prices) + range/licensing fee **$1M per Earth launch** (FAA/range anchor, order-of-magnitude) + expended hardware (catalog value of discarded stages, 06) + refurbishment **2% of recovered-stage hardware value per reflight** (game value; consistent with SpaceX-claimed low refurb costs) + integration labor **$0.5M per launch** at T0–T1, $0.1M at T2+ (automation). This is why reuse and depots win Act 1.
- **E-4 (overhead).** Daily program overhead: `OH = $40k (HQ base) + $10k×N_pads + $5k×N_active_uncrewed_missions + $30k×N_active_crewed_vessels + Σ facility leases + Σ salaries`. Facility leases: launch site $0.3M/quarter; second pad build $20M; tracking-network subscription (needed beyond lunar distance, DSN-analog) $0.5M/quarter — **auto-cancels** once the player's relay network (05/09 hardware, per 05's comms model) provides link coverage to *every active mission beyond lunar distance*, and **auto-resubscribes** (with a Class-3 alert) if that coverage lapses. Salaries per §4.4. **Runway readout** (HQ headline per §5.1; Class-3 trigger per §8 ¶1): `runway_d = Cash / max(ε, −(Σincome_rates − Σcost_rates))` over G-9's recurring rates (discrete events such as contract payouts and purchases are excluded from the rate sums); displayed as **∞** while the net rate ≥ 0.
- **E-5 (purchases).** Parts at 06/07 catalog prices ($M); raw resources at §4.3 Earth prices, plus E-2 lift (destination-scaled per E-2) if delivered to orbit. Delivery lead time to pad: 30 d for catalog parts, 7 d for resources (logistics handwave on Earth's surface only — everything off-Earth moves through 05's real logistics).
- **E-6 (selling).** Assets and resources sell on Earth at **40% of catalog/list** (market spread); §3.8 saturation applies to high-value commodities. Selling requires the asset to be on Earth or in LEO (recovery costs are real).
- **E-7 (no money printer off-Earth).** Money is only created by contracts, milestones, investors, and Earth sales. There is no abstract "funds per science" faucet. Off-Earth value is mass, energy, and crew-time — the point of the whole game.

### 3.4 Contracts (E-8…E-12)

- **E-8 (offer board).** The contract board refreshes weekly (sim). Simultaneous offers: `N = 3 + floor(Prestige/100)`, max 12, drawn from §4.1 templates filtered by demonstrated capability (you see lunar-delivery contracts only after any craft of yours reaches lunar SOI, etc. — one "reach" teaser per act is always visible as a stretch goal). Same-template cooldown after completion: **90 d default**; exceptions — recurring/standing templates (CT-05, CT-14, CT-19) re-offer immediately, tourism (CT-07, CT-15) 30 d, flagship science (CT-17, CT-20) 180 d, unique contracts (CT-09, CT-21) never re-offer.
- **E-9 (payment structure).** Accept → **10% advance**. Completion → remainder. Multi-part contracts (e.g., constellation deploys) pay per-unit fractions. Deadline: `T_deadline = T_accept + max(2 × t_min_transfer, 90 d)` where `t_min_transfer` comes from 01's window/transfer tables (includes synodic wait). **Precedence:** where §4.1 lists an explicit deadline basis (e.g., CT-01's 60 d, CT-03's 2 yr), the table value overrides this formula; the E-9 formula is the default for window-locked and per-window templates. Deadline alerts at T−90/30/7 d (§3.11).
- **E-10 (failure).** Miss/abandon → repay advance + **20% of total value penalty** + **Prestige −10** + that customer's templates locked for 1 yr. If failure destroyed a customer payload, add the payload's **insured value**: customer-supplied-hardware templates (CT-04 comsat, CT-22 hosted package) → insured value = **2 × total contract value**; mass-delivery templates (CT-02, CT-05, CT-11, CT-14, CT-16) → **$10M per tonne** of customer payload aboard; crewed templates (CT-06, CT-07, CT-13, CT-15) add no payload penalty — fatalities are covered by E-23 stand-downs and F-4 death economics instead.
- **E-11 (delivery payout formula).** For mass-delivery templates: `Payout = m_payload(kg) × rate_dest($/kg, §4.1) × k_urgency`. **Urgent variants:** 25% of generated offers are urgent — deadline ×0.5 (still feasibility-validated per §8 ¶5) and `k_urgency = 1.5`; all other offers use `k_urgency = 1.0`. Rates decline 8%/yr like E-2 (the world's costs fall — standing still means shrinking margins; the game pushes you outward).
- **E-12 (recurring service lines).** **Standing services** are steady income with light obligations; each line unlocks after its qualifying contracts have been completed twice and carries a quarterly obligation check:
  - **LEO constellation maintenance** — $5M/month. Unlock: 2 completed CT-03 or CT-05. Obligation: ≥ 1 player flight per quarter that rendezvouses (01 gate) with a customer satellite.
  - **Station-keeping boost services** — $2M/month. Unlock: 2 completed CT-04, CT-08, or CT-09. Obligation: ≥ 1 docking-or-boost operation on a customer asset per quarter.
  - **Planetary-data subscription** — $0.2M/GB of fresh SurveyData, cap 50 GB/yr. Unlock: 2 completed CT-18 or CT-22. Pays per GB actually delivered; counts as lapsed after 2 consecutive quarters with zero delivery.
  A line whose quarterly check fails **auto-suspends** (no penalty beyond lost income) from the start of the next month and resumes the month after the next satisfied quarter. These keep mid-game cash unattended so the player's attention can move to mass logistics.

### 3.5 Milestones & Prestige (E-13…E-16)

- **E-13 (Firsts).** One-time milestone payments (§4.2) on the COTS model: investor/agency tranches for demonstrated capability, paid automatically, each generating a Chronicle FIRST entry. Repeat performances pay nothing — incentive to push outward.
- **E-14 (Prestige P).** Scalar 0–1,000. Sources: milestones (§4.2), contract Prestige bonuses (§4.1, where listed: CT-09 +25, CT-21 +50), anomaly visits (03 §4.4: base **+5 × listed multiplier**), rescues (+50), standing safety record (+5 per consecutive year with crewed flights and zero fatalities). Losses: crew fatality −100 (founder −150), contract failure −10, heritage-zone violation −50, agency-assist bailout −100. **Prestige tiers** = the §4.5 investor gates (P = 50/150/300/500); floor = `max(0, highest gate ever crossed − 100)` (history can't be fully erased).
- **E-15 (Prestige effects).** Gates investor rounds (§3.6), contract board size (E-8), recruitment pool quality (08 archetype quality roll `+1 per 200 P`), and tourism pricing (`×(1 + P/1000)`).
- **E-16 (heritage zones).** Per 03's anomaly table: no mining/industrial placement within **10 km** of DERELICT heritage anomalies (Apollo sites, Luna 9, Huygens…). Violation: one-time **$100M fine + Prestige −50** + agency contract lockout 1 yr (framing: OST Art. VIII retained jurisdiction over hardware + the One Small Step to Protect Human Heritage in Space Act (2020) + Artemis Accords §9-descended heritage protocols). Preserve-vs-salvage choices on museum-grade derelicts (03) trade salvage mass against Prestige.

### 3.6 Investors & debt (E-17…E-19)

- **E-17 (rounds).** Funding rounds are milestone-gated grants with a promise attached (equity is abstracted away; see §9-Q1). Table §4.5. Raising requires Prestige ≥ gate and a chosen **promise**: one §4.2 milestone to deliver within 36 months. Deliver → round fully vests (cash was paid up front; no clawback). Fail → **Prestige −100**, no further rounds for 5 years, and overhead +10% for 2 years (board oversight).
- **E-18 (bridge loan).** One revolving instrument: borrow up to `25% × trailing-12-month revenue`, **APR 12%** (venture-debt anchor 8–15%), term 24 months, auto-drawn at Cash < 0 (§8.4). Mechanics: interest accrues monthly as a G-9 cost rate (1% of outstanding principal per month); principal is a **bullet due at 24 months**, auto-repaid earlier whenever `Cash > 2 × principal`; failure to repay at term triggers the §8 ¶1 Liquidation flow; **one loan outstanding at a time** (revolving = re-borrowable only after full repayment).
- **E-19 (money fade trigger).** When `SSI_program ≥ 0.8` sustained 730 d (§3.9), the HQ default tab switches from the **$ Ledger** to the **Mass Ledger** (t/day by category, SSI bars); money collapses to a side-tab (player-reversible). Mechanically money never turns off — it just stops being the binding constraint, by design.

### 3.7 Insurance & accidents (E-20…E-23)

- **E-20 (coverage envelope).** Commercial insurance covers **launch + 1 year of operations inside Earth's SOI only** (real market practice; deep space is uninsurable). Insurable value = hardware catalog value + declared cargo value, cap $2B per risk.
- **E-21 (premium).** `Premium = V_insured × 6% × f_history × f_payload` with `f_history = 2.0` (vehicle design with <3 flights), `1.0` (3–10 flights), `0.6` (>10 consecutive successes; resets to 1.0 after any failure); `f_payload = 1.5` if nuclear material aboard (launch-approval regime anchor: US INSRP/Price-Anderson-style nuclear launch review — also adds a 60 d licensing lead time per nuclear launch). Bounds **3.6–12%** before the nuclear rider (the historical market's 4–12%, with the floor undercut only by a >10-flight perfect safety record).
- **E-22 (claims).** Payout = insured value on total loss; 50% on recoverable-but-crippled (assessor event, 7 d). **Player-commanded destruction or scuttling voids coverage** (fraud guard, §8.6): claims require a failure event originating in the reliability systems (02 §engine failures, 05 MTBF, 06 damage model).
- **E-23 (stand-downs).** Any crewed fatality: mandatory investigation freezing crewed launches — **30 d** (uncrewed-vehicle fatality, e.g., pad worker), **90 d** (in-flight, cause found quickly), **180 d** (in-flight, founder or multiple deaths). Anchored to real stand-downs (≈4.5–32 months, §2) but game-compressed; Ironman uses 2× durations. During stand-down: crewed contracts pause deadlines (force majeure), Prestige decays −5/month. Uncrewed flights continue.

### 3.8 Earth market & saturation (E-24…E-25)

- **E-24 (price model).** Earth buy prices per §4.3, constant except scripted tier declines (Electronics/Wafers fall 5%/yr as Earth's industry advances) and **supply-shock events**. Shock generator: each listed shock is an independent Poisson event with mean one occurrence per **15 sim-years**, at most one active per commodity at a time, duration drawn uniformly from its listed range — Xenon ×3 for 1–2 yr (2022 anchor); Pu238 unavailable for 1 yr; HALEU ×2 for 1 yr. Each shock is a Chronicle event and an ISRU nudge.
- **E-25 (sell saturation).** Pricing is **marginal**: each kg sold while the trailing-12-month sold volume stands at `q` receives price multiplier `exp(−q/Q_sat)` (per-commodity Q_sat, §4.3); a block sale of quantity Q starting from trailing volume q₀ therefore averages multiplier `(Q_sat/Q) × (e^(−q₀/Q_sat) − e^(−(q₀+Q)/Q_sat))`. This kills "dump asteroid platinum, retire" exploits honestly: markets saturate. Worked example: He3 Q_sat = 100 kg/yr; selling 100 kg in a year from q₀ = 0 earns `0.4 × $15M × (1−e⁻¹) ≈ $3.8M/kg` average, not $6M/kg.

### 3.9 The material economy, SSI, and endgame audits (E-26…E-29)

- **E-26 (SSI definition).** Over a trailing 365 d window, for every off-Earth site and vessel, classify consumed mass into category c ∈ {**Propellant**, **LifeSupport**, **Structure**, **Parts**, **Electronics**, **Nuclear**} by **consuming subsystem, not by resource species** (dual-use species — Oxygen, Water, Hydrogen, Methane — would otherwise be misclassified): mass drawn by engine/RCS/pressurant systems (02/06) → **Propellant** regardless of species (LOX burned as oxidizer is Propellant, not LifeSupport); mass drawn by ECLSS/crew systems (08) → **LifeSupport**; consumed by construction (07) → **Structure**; by maintenance/spares (05) → **Parts**; by avionics/fab installation (05) → **Electronics**; by reactor/RTG fueling (09) → **Nuclear**. Only for ambiguous or unmetered sinks, fall back to the default species mapping (subsystem attribution always takes precedence): LifeSupport (Water, Oxygen, Nitrogen, FoodRations, MedSupplies), Structure (StructuralParts, IronSteel, Aluminum, Titanium, BasaltFiber, Glass, Regolith-derived), Parts (MachineParts), Electronics (Electronics, Wafers), Nuclear (Uranium, Thorium, Pu238); Propellant deliberately has **no** species list — it is always subsystem-attributed. Then
  `SSI_c = 1 − m_imported_from_Earth,c / m_consumed,c` and `SSI_program = 1 − Σ_c m_imported,c / Σ_c m_consumed,c` (mass-weighted). Displayed as the **Umbilical gauge** (Earth with a cord; per-category bars). Per-site SSI computed identically per site.
- **E-27 (expected trajectory).** Mirrors 05 §6's import-fraction ladder: T0 ≈ 0 → T1 ≈ 0.4 → T2 ≈ 0.75 → T3 ≈ 0.95 → T4 ≈ 1.0. Electronics is the designed long pole (05 wafer fab at T3 = "Silicon Independence").
- **E-28 (Foundation Audit — civilization win).** Passed when ALL hold simultaneously for **24 consecutive months**: (a) ≥ **50 crew** permanently resident off-Earth across ≥ 2 bodies; (b) `SSI_program ≥ 0.98` AND every category `SSI_c ≥ 0.95` (FoodRations ≥ 0.99); (c) **zero Earth cargo manifests** (crew transfers permitted); (d) kit-closure **χ ≥ 0.90 at ≥ 2 industrial sites** (05 A3/A4 metric); (e) every crewed site medically covered (medbay + Medic ≥ 2, 08) and mean morale ≥ 60; (f) settlement score `Σ_sites (occupied_berths × SSI_site) ≥ 50` (07's berths-×-closure metric; since `SSI_site ≤ 1` and an occupied berth = one resident crew, this is (a)'s 50-crew count discounted by site closure — (a) additionally enforces the ≥ 2-body spread). Passing fires the **Foundation Day** Chronicle chapter and the credits; the sandbox continues.
- **E-29 (Interstellar Precursor — probe win).** Build and launch an uncrewed probe that **crosses 100 AU within 10 years of departure** (sustained ≥ 10 AU/yr ≈ 47.4 km/s). Honesty ladder shown in the project screen: Voyager 1 managed 3.6 AU/yr; the best studied chemical/Oberth architecture (APL Interstellar Probe) ~7 AU/yr; ≥10 AU/yr therefore requires the T4 path (02 fusion stage [SPECULATIVE], or a staged solar-Oberth + multi-MW EP architecture assembled from T3 parts — both satisfiable). Optional stretch flag at 550 AU (solar-gravity-lens focal region) for the post-credits Chronicle epilogue. Probe must carry the science payload kit (Electronics 2 t + 50 kWe-class power, 09) — a fitting final demand on the T4 industrial base.

### 3.10 Difficulty & realism toggles (D-1…D-6)

- **D-1 (the designed experience).** **Baseline** preset = every realism system ON, Ironman OFF, paid Simulations ON, funding ×1.0. All balancing, tutorials, and milestone hour-targets assume Baseline. Stated in the new-game screen: *"Baseline is how Aphelion is meant to be played."*
- **D-2 (toggles).** Each toggle is independent; presets in §4.6:
  - Funding multiplier: ×1.5 / **×1.0** / ×0.6 (applies to contracts, milestones, rounds).
  - Boiloff (02): full / simplified (rates ×0.25) / off.
  - Radiation (08): full / no-death (morale & career-limit only) / off.
  - Part failures (02 engine wear, 05 MTBF, 06 events): full / reduced (rates ×0.25) / off.
  - Comms light-lag & teleop penalty (05): on / off.
  - Life-support consumption (08): always ON in Career (it is the soul of the game); toggleable only in Sandbox.
  - Ironman: single rotating save, quicksave/load disabled, founder death = game over (08 §3.13 rule adopted verbatim), stand-downs ×2.
  - Event-pause policy per alert class (§3.11) — player-tunable in all modes.
- **D-3 (integrity marker).** Any toggle below Baseline permanently marks the save and its Chronicle with an asterisk and the settings list (the baseball-records rule). Toggles may be changed mid-campaign; changes are themselves Chronicle entries.
- **D-4 (Sandbox).** Money off, optional all-tech unlock, all toggles free, separate save class, Chronicle still records. For builders and for reproducing historical missions.
- **D-5 (Simulation — the diegetic revert).** Anywhere, the player may run any planned mission segment as a **Simulation** (hardware-in-the-loop / Monte Carlo framing): a sandboxed copy of the world, watermarked SIM, no consequences. Cost `C_sim = $0.1M + 0.5% × hardware value of simulated vehicles`, cap $2M, charged once per sim session. Available in Ironman (it's an engineering tool, not a cheat). Quicksave (F5) / quickload (F9) exist outside Ironman for players who want them; the designed loop is Simulate-then-commit.
- **D-6 (revert-to-pad).** In Baseline, a flight may be reverted **only** within 5 min after liftoff *and* only if it was declared a **Test Flight** before launch (no contract payload, no crew XP, range fee still paid). Everything else is forever. **Training preset ("reverts loose," §4.6):** any flight is revertible to pad within 15 min of liftoff, no Test-Flight declaration required, range fee refunded. Ironman: no reverts.

### 3.11 Alerts, notifications, and warp interrupts (A-1…A-6)

- **A-1 (taxonomy = ISS C&W).** Four classes, adopted from the ISS Caution & Warning system:

| Class | Name | Color/sound | Warp effect (Baseline default) | Examples (owner) |
|---|---|---|---|---|
| 1 | **EMERGENCY** | red, klaxon | **pause** (tier 0 + pause) | fire, rapid depress, toxic atmosphere (08); reactor casualty (09); collision < 60 s (01/06); crew incapacitation (08) |
| 2 | **WARNING** | orange, alarm tone | drop to **1x** | engine failure in burn (02); LS critical band (08); conjunction < 1 h (01); insufficient Δv after burn (01); foundry freeze risk (05); habitat breach (07) |
| 3 | **CAUTION** | amber, chime | cap warp at **1,000x** | caution-band crossings (08); spares < 90 d projection (05); boiloff margin (02); contract T−30 d; cash < 60 d runway |
| 4 | **ADVISORY** | white, silent | none (log + toast) | arrivals, completed builds, harvest, window-opened notices, ledger receipts |

- **A-2 (warp law).** `warp_max_effective = min(warp_player, min over active un-acknowledged alerts of warp_cap(class))`. Acknowledging (click or `Enter` on focused toast) releases the cap — **except Class 1**, which requires either resolution or an explicit **Accept-Risk** action (covered-switch UI; logged to the Chronicle forever with the player's one-line justification, optional). 01's event guard remains independently active for trajectory events.
- **A-3 (toast budget).** Max 3 toasts on screen (top-right, newest on top); overflow goes silently to the Alert Center badge. Dedup: identical (source, type) within 24 h sim-time merge into one toast with a ×N counter.
- **A-4 (per-type overrides).** Power users may remap any *event type* one class up/down (never out of Class 1) and set per-type pause/no-pause. Stored per save; defaults are A-1.
- **A-5 (Alert Center).** Full screen (in HQ overlay): filterable table of all active + historical alerts, each with jump-link, owning system, formula-grade detail ("readout honesty" per 08 §5: hovering any number shows its defining equation and inputs).
- **A-6 (Master Alarm).** A physical-feeling MASTER ALARM button (ISS anchor) on the HUD acknowledges all Class 2–3 audio at once but leaves caps until individually acknowledged. Muscle-memory key: `Backspace+Backspace` is reserved for abort (§3.13), so Master Alarm is `Delete`.

### 3.12 Pacing model & act transitions (G-12…G-13)

- **G-12 (hour targets).** Designed pacing for a focused Baseline player (tutorials on, no wiki): the table in §4.2 carries a cumulative target hour per milestone. Acts: **Act 1 ≈ 0–12 h, Act 2 ≈ 12–35 h, Act 3 ≈ 35–75 h, Act 4 ≈ 75–120 h, Act 5 ≈ 120–170 h, Endgame ≈ 170–220 h.** Credits achievable ~150–220 h; completionist (all anomalies, both wins) ~300 h. Calibration rule for playtests: if median testers exceed a target by >40%, the *frictions* (UI steps, warp interrupts) get cut first, never the physics.
- **G-13 (act transitions).** Act N+1 begins — and the Chronicle `ACT_CHAPTER` entry fires — when Act N's **exit milestone** in the §6 table completes. Act state is **monotonic** (never reverts). Contract `[A#]` availability = act unlocked AND capability demonstrated per E-8; §6's economic-regime descriptions and the "one reach teaser per act" rule (E-8) read this same act state.

### 3.13 Failure-as-content (F-1…F-5)

- **F-1 (aborts).** Pilot HUD always shows the current **abort plan** for the flight phase (Shuttle RTLS/TAL/ATO and Apollo Mode I–IV anchors): pad abort (LES part, 06), Max-Q abort, abort-to-orbit, ballistic-return windows; for stations/bases, evacuation plans (lifeboat capacity from 06/07). Abort trigger: `Backspace` double-press within 1 s (covered switch). An in-flight abort demonstration is a paid milestone (§4.2) — failure systems are revenue.
- **F-2 (rescue generation).** Stranded detection is evaluated on every trajectory change and once per sim-day under warp. A crewed craft is **STRANDED** iff its crew are alive and, for every safe harbor in the set {player bases/stations with free berths and functioning life support, Earth}, either `Δv_available < Δv_required` (01 transfer tables, +5% margin) or `t_transfer > LS_days_remaining` (08 headline) — AND no other player craft can reach and dock with it within `LS_days_remaining`. On the STRANDED transition, the game auto-creates a RESCUE objective: countdown = 08's days-of-life-support headline; planner pre-computes candidate windows; all rescue-related purchases get 7-day delivery (E-5 waiver, "emergency procurement"). Success: **Prestige +50**, Chronicle RESCUE entry, crew morale arc (08). This is the game deliberately turning a failure into its best content (Apollo 13 anchor).
- **F-3 (agency assist).** Once per campaign, the player may request a national-agency rescue/bailout: costs `max($500M, 50% of treasury)` and **Prestige −100**, takes a realistic transfer time anyway (no teleporting — agency flies a real trajectory, min 30 d prep). It can therefore *fail* if life support runs out first. The existence of exactly one humiliating lifeline is a design valve, not a safety net.
- **F-4 (death economics).** Per 08 §3.13 (adopted verbatim): non-founder crew are permadeath; founder death in Career = succession event (Prestige −150, all-crew morale −25, overhead +10% for 1 yr); Ironman = game over. Additional economic effects owned here: death benefit **$10M per fatality** to estate, stand-down per E-23, customer-confidence dip (active contract deadlines unchanged but new offers −50% for 6 months).
- **F-5 (wreckage & salvage).** Failed hardware persists (01 rails / 03 surfaces): debris is a conjunction hazard (06) and a salvage resource: scrap mass = **0.50 × wreck dry mass**; processing yields **30% of scrap mass** as resources, split by the source parts' bill-of-materials composition (06 part data), remainder discarded as Regolith-class waste → 04/05 ledgers. Your own disasters literally become mines. Famous-wreck Chronicle entries name the vehicle and cause.

### 3.14 The Chronicle (C-1…C-5)

- **C-1 (record schema).** Append-only log; entry = `(t_sim, type, class, subjects[], location, numbers{}, autoshot_id, seed)`. Types in §4.9. Every FIRST, death, disaster, rescue, contract landmark, audit, anomaly visit, accepted Class-1 risk, and act transition writes an entry. Target volume: 200–800 entries per campaign.
- **C-2 (auto-shot).** Each entry captures a **vector scene snapshot** (scene graph, not pixels — re-renderable at any resolution later; cheap for the CPU renderer, 13 owns the buffer format). Entries render as cards with deterministic text from a template grammar (dry mission-report tone: *"2053-08-14 — PELICAN-3 set down at Shackleton Rim. First crewed lunar landing of the program. Crew: Vasquez, Okafor. Margin at touchdown: 4.1% propellant."*).
- **C-3 (chapters).** Act transitions and audits generate **chapter cards** with auto-computed statistics (launches, t to orbit, fatalities, $ and t flows, firsts). The endgame export — **"The Program, 2049–20XX"** — is a scrollable HTML file + PNG poster timeline rendered from vector snapshots. This export is the intended trophy of a campaign.
- **C-4 (epitaphs & patches).** Dead crew get permanent memorial entries (name, role, hours, missions, cause) and appear on a Memorial wall in HQ. Every named mission auto-generates a small **vector mission patch** (procedural emblem seeded by mission name/body/vehicle) used on its Chronicle cards.
- **C-5 (photo mode).** `F10`: pauses (sim-safe in Ironman), free camera, UI hide, line-weight boost, palette filters (Blueprint, Mission-Patch, Archival-Print), annotation stamps (date, craft name, velocity vector), export PNG at up to 4× window resolution via vector re-render. Any photo can be pinned to the Chronicle as a manual entry.

### 3.15 Onboarding & tutorial gating (T-1…T-4)

- **T-1 (diegetic tutorials).** Tutorials are **contracts** from the "Program Charter" chain (a patient seed investor), not modal popups. Each charter contract constrains scope, pre-supplies a blueprint where needed, and pays per the §5.8 table (charters are **deadline-free and penalty-free** — E-9/E-10 do not apply; a failed charter simply re-offers). Skippable wholesale for veterans: a single checkbox grants the four charters' summed payouts — **$50M** — as additional starting capital and unlocks the full UI.
- **T-2 (progressive disclosure).** UI modules unlock on first relevance: Finance tab after first contract; Planner porkchop after first orbit; Base mode at first surface/station asset; Industry dashboards at first fab module; SSI gauge at first off-Earth production. Locked modules are visible but greyed with a one-line "unlocks when…" (no hidden screens — depth is visible from hour zero).
- **T-3 (Flight Director).** An optional advisor persona delivering context hints (max 1 per 5 min, never repeats an acknowledged hint, hard-off toggle). All hints reference the Encyclopedia article they summarize.
- **T-4 (Encyclopedia).** In-game manual where every mechanic page carries its real-world anchor paragraph (the design bible's §2 sections, abridged). Every UI number hover-links to its page ("readout honesty" extends to teaching: the UI is the documentation, per 08 §5).
- The scripted first two hours: §5.8 beat sheet.

---

## 4. Content Catalog

### 4.1 Contract templates (Career)

Rates decline 8%/yr per E-11; values below are 2049–2052 openings. `[A#]` = act availability.

| ID | Template | Act | Payout formula / value | Deadline basis | Anchor |
|---|---|---|---|---|---|
| CT-01 | Sounding payload, 100 km | A1 | $2M flat | 60 d | commercial suborbital market |
| CT-02 | Smallsat to LEO | A1 | m × **$8,000/kg** (0.2–2 t) | 120 d | CRS $/kg history, scaled down-curve |
| CT-03 | Constellation batch deploy | A1–2 | $5M/sat × 20–60 sats, per-unit pay | 2 yr | Iridium NEXT economics |
| CT-04 | GEO-slot comsat delivery | A1–2 | $50M (sat supplied) | 1 yr | commercial GEO launch services |
| CT-05 | Agency LEO cargo (CRS-style) | A1–2 | m × $8,000/kg, 2–6 t, recurring | per window | NASA CRS |
| CT-06 | Crew seat to agency LEO station | A1–2 | **$30M/seat** | per window | Commercial Crew $55M (2020) |
| CT-07 | Orbital tourism, LEO, 2–4 pax | A1–3 | $40M/seat × (1+P/1000) | flexible | Axiom ~$55M/seat |
| CT-08 | Debris remediation (large object) | A1–2 | $90M/object (e.g., Envisat, 03) | 2 yr | ClearSpace-1 €86M |
| CT-09 | Hubble reboost (unique) | A1–2 | $150M + P+25 | 3 yr | 2022 NASA/SpaceX study; seed from 03 |
| CT-10 | In-flight abort demo | A1 | $25M | 1 yr | Commercial Crew abort tests |
| CT-11 | Lunar surface delivery (CLPS-style) | A2 | m × **$400k/kg** (50–500 kg); steps to $100k/kg when the world reaches T2 (E-2 tier-step pattern), E-11's 8%/yr on top | window+90 d | CLPS $0.8–1.2M/kg (2020s) |
| CT-12 | Lunar sample return, 5 kg | A2 | $120M | 2 yr | CNSA Chang'e-5 class missions |
| CT-13 | Lunar crew seat (agency astronaut) | A2 | $100M/seat | per window | Artemis-era seat economics, extrapolated |
| CT-14 | Propellant to depot (LOX/CH4/LH2) | A2–4 | m × 1.5 × `L(orbit)` (E-2 destination scaling) | 1 yr | cryo-depot studies; margin over self-delivery |
| CT-15 | Lunar flyby tourism, 2 pax | A2 | $100M/seat | flexible | dearMoon-class private missions |
| CT-16 | Mars surface delivery | A3 | m × **$2M/kg** (100–500 kg; max payout $1.0B, kept below CT-17) | window-locked | derived: CLPS × Δv/duration scaling [game value] |
| CT-17 | Mars sample return | A3 | **$1.5B**, 3 tranches | 2 windows | MSR program budgets ($5–11B agency-run); seed from 03 (Perseverance cache) |
| CT-18 | NEA characterization survey | A3 | $40M + $0.2M/GB SurveyData | 3 yr | planetary defense + CSDA data-buy programs |
| CT-19 | Pu238 supply to agency | A3–5 | **$10M/kg**, ≤ 5 kg/yr | standing | DOE restart economics (§2); demand ≈ NASA RPS needs |
| CT-20 | Venus cloud-sample return | A4 | $600M | 2 windows | flagship-class New Frontiers/flagship scale |
| CT-21 | Venera 13 capsule recovery (unique) | A4–5 | $500M museum purchase + P+50 | none | seed from 03 AN-17 (T3 trophy) |
| CT-22 | Outer-planet science package hosting | A5 | $80M + $0.1M/GB | window-locked | hosted-payload market, extrapolated |
| CT-23 | Heritage documentation (Apollo sites etc.) | A2+ | $20M/site, no-touch rules (E-16) | 1 yr | heritage-protection protocols |
| CT-24 | Stranded-asset salvage for owner | A2+ | 30% of asset value | 2 yr | commercial salvage practice, GEO servicing |

### 4.2 Milestones — the "Firsts" ladder (payout, Prestige, target hours)

Cumulative target hours per G-12; payouts ×funding multiplier (D-2); each is a Chronicle FIRST.

| Act | Milestone | Payout | Prestige | Target h (cum.) |
|---|---|---|---|---|
| 1 | First launch (any) | $5M | +5 | 1 |
| 1 | **First orbit** | $30M | +10 | 3 |
| 1 | First stage recovered & reflown | $20M | +5 | 5 |
| 1 | **First docking** (01 gates) | $25M | +10 | 7 |
| 1 | First crewed orbit | $60M | +20 | 9 |
| 1 | In-flight abort demonstrated (CT-10 pairs) | — (contract) | +5 | 10 |
| 1 | LEO station core operational (4 crew, 30 d) | $40M | +10 | 11 |
| 1 | First cryo depot transfer demo (T1) | $50M | +10 | 12 |
| 2 | First lunar flyby / orbit | $40M | +10 | 14 |
| 2 | First robotic lunar landing | $80M | +20 | 16 |
| 2 | Polar ice confirmed by drill (04 survey chain) | $60M | +10 | 19 |
| 2 | **First crewed lunar landing** | $300M | +50 | 22 |
| 2 | **Lunar ice mine online** (first 10 t Water extracted) | $150M | +30 | 28 |
| 2 | Lunar LOX delivered to orbital depot (02 LANTR synergy) | $100M | +20 | 32 |
| 2 | Surface base: 4 crew × 90 d continuous | $120M | +20 | 35 |
| 3 | **First NTR burn in orbit** (02 SNRE-class, cold-launch rule) | $100M | +25 | 38 |
| 3 | First robotic Mars EDL | $150M | +30 | 44 |
| 3 | **First crewed Mars landing** | $500M | +75 | 50 |
| 3 | First kg of Mars-made methalox (04 RX chain) | $80M | +30 | 55 |
| 3 | NEA rendezvous + 100 t volatiles extracted | $120M | +25 | 60 |
| 3 | Mars sample return delivered (CT-17 pairs) | — (contract) | +40 | 65 |
| 3 | First off-Earth food harvest (08 greenhouse) | $50M | +15 | 70 |
| 4 | Main-belt arrival (Ceres-class rendezvous) | $100M | +25 | 80 |
| 4 | Metallic-asteroid mine online (100 t IronSteel refined) | $120M | +25 | 86 |
| 4 | **Venus aerostat deployed** (07 HAVOC-anchored, crewed 30 d) | $250M | +75 | 92 |
| 4 | **Silicon Independence** (05 wafer fab online) | $200M | +50 | 100 |
| 4 | Mass driver first throw (05) | $100M | +25 | 105 |
| 4 | Food independence at one site (SSI_food = 1.0, 365 d) | $100M | +25 | 112 |
| 4 | First never-Earth ship (built, fueled, crewed off-Earth) | $150M | +40 | 118 |
| 5 | Jupiter system arrival; Callisto base seed (08 radiation logic) | $200M | +50 | 128 |
| 5 | Europa ocean bore relay online (07 megaproject, robotic) | $150M | +40 | 135 |
| 5 | **Titan landing** (Huygens anchor; crewed = +75) | $200M | +50 | 140 |
| 5 | **Titan submarine deployed** (NASA COMPASS study anchor) | $150M | +50 | 150 |
| 5 | Enceladus plume-water harvest (100 t) | $100M | +25 | 158 |
| 5 | Saturn-system permanent base (12 crew × 2 yr) | $250M | +50 | 168 |
| End | **Foundation Audit passed** (E-28, "Foundation Day") | — | +100 | 180–220 |
| End | **Interstellar Precursor launched** (E-29) | — | +100 | 190–220 |
| End | Precursor crosses 100 AU (≤ 10 yr) | — | +100 | (warped decades) |

Money values stop mattering before Act 5 by design (E-19); late payouts exist mostly as Chronicle fanfare and Prestige.

### 4.3 Earth market — buy prices (sell = 40%, E-6; saturation Q_sat per E-25)

| Resource | Buy $/kg | Q_sat (sell), t/yr | Anchor / note |
|---|---|---|---|
| Water | 0.001 | — | municipal supply |
| Oxygen (LOX) | 0.20 | — | industrial bulk LOX ≈ $0.15–0.3/kg |
| Hydrogen (LH2) | 6 | — | KSC LH2 procurement ≈ $4–6/kg |
| Methane (LCH4) | 1 | — | LNG ≈ $0.6/kg + launch-grade liquefaction |
| RP-1 (propellant, 02 list) | 3 | — | RP-1 ≈ $2–3/kg historical |
| Nitrogen | 0.3 | — | industrial LN2 |
| CO2 | 0.1 | — | industrial |
| Ammonia | 0.6 | — | anhydrous NH3 ≈ $400–800/t |
| Argon | 1.5 | — | liquid argon industrial |
| Xenon | 1,200 | 60 | ≈$1,200/kg baseline; 2022 shock ×3+ (E-24 event); world prod. ~50–70 t/yr |
| Regolith | n/a | — | not traded |
| IronSteel | 0.8 | — | steel ≈ $0.5–1/kg |
| Aluminum | 2.5 | — | LME |
| Titanium | 25 | — | aerospace mill products (sponge ~$8/kg) |
| Copper | 9 | — | LME |
| Silicon (semi-grade) | 15 | — | polysilicon $10–30/kg |
| RareEarths | 80 | 20 | mixed REO basket, 2010s–20s range |
| Uranium (HALEU) | 30,000 | — | DOE/Centrus projection; demo lots cost far more [est.] |
| Thorium | 100 | — | thin market [game value] |
| Pu238 | 10,000,000 | 0.005 | production-cost estimates ≈$8M/kg (GAO-17-673; §2); we fix $10M/kg |
| Carbon (graphite) | 1.5 | — | industrial graphite |
| Polymers | 3 | — | commodity-to-engineering resin mix |
| BasaltFiber | 4 | — | basalt fiber $3–6/kg |
| Glass | 1 | — | float/borosilicate mix |
| Electronics | 20,000 | 50 | space-grade avionics; satellite $/kg anchor |
| Wafers (05 resource) | 200,000 | 5 | packaged high-end semiconductors (value density conservative) |
| MachineParts | 1,000 | — | precision aerospace components |
| StructuralParts | 50 | — | = 06's $0.05M/t commodity-structure canon |
| FoodRations | 150 | — | NASA space-food production cost class |
| MedSupplies | 2,000 | — | pharma/filters mix (08 §4.6) |
| Biomass | not traded | — | — |
| He3 [SPECULATIVE] | sell-only 15,000,000 | 0.1 | post-2009 shortage ≈ $2,000+/L ≈ $15M/kg; T4 only |

Delivered-to-orbit price = buy + E-2 lift (destination-scaled). Propellant catalog beyond this list is 02's; prices follow the closest entry here. **Q_sat "—"** = effectively unsaturable at player scales: treat as `Q_sat = ∞` (E-25 multiplier ≡ 1; §8 ¶7's transaction-size refusal does not apply). **Canonical-resource extensions registered by this doc:** `RP-1` (owned by 02), `Wafers` (05), `MedSupplies` (08), `SurveyData` (03/05; intangible, tracked in GB not kg) — extensions per the project convention ("only when genuinely needed"); all 13 docs must use exactly these spellings (verification: §9-Q11).

### 4.4 Salaries, staffing, crew market (owns 08's pointers)

| Item | Value | Anchor / note |
|---|---|---|
| Crew salary, Earth-side reserve | $0.25M/yr | NASA $152k/yr × private multiple |
| Crew salary, flight status | $1.0M/yr | hazard pay ×4–6 |
| Signing bonus (08 archetype cost low/mid/high) | $2M / $5M / $12M | test-pilot & flight-surgeon markets |
| Training, per skill-level attempt (08 mechanics) | $2M + 90 d | astronaut training pipeline scale |
| Death benefit (F-4) | $10M | program liability [game value] |
| Recruitment pool refresh | 4 candidates/quarter; quality per E-15 | — |
| Mission-control ops staff | inside E-4 overhead | small-sat ops team costs $2–5M/yr |

### 4.5 Investor rounds (E-17)

| Round | Prestige gate | Cash | Promise deadline | Anchor |
|---|---|---|---|---|
| Seed | start | $300M (pre-banked, E-1) | tutorial charter | SpaceX founding capital, scaled to 2049 |
| Series A | 50 | $250M | 36 mo | COTS-era private raises |
| Series B | 150 | $600M | 36 mo | mid-2010s SpaceX rounds |
| Series C | 300 | $1.5B | 36 mo | constellation-era raises |
| Series D | 500 | $4.0B | 48 mo | cumulative SpaceX ~$10B+ by 2020s |
| Bridge loan | any | ≤ 25% trailing revenue | 24 mo @ 12% APR | venture debt 8–15% |

### 4.6 Difficulty presets (D-2 toggles)

| Preset | Funding | Boiloff | Radiation | Failures | Light-lag | Ironman | Sims/Reverts | Notes |
|---|---|---|---|---|---|---|---|---|
| Training | ×1.5 | simplified | no-death | reduced | off | off | sims free, reverts loose | asterisked |
| **Baseline** | ×1.0 | full | full | full | on | off | sims paid, D-6 reverts | **the designed game** |
| Veteran | ×0.6 | full | full | full | on | off | sims paid, no reverts | asterisk-free, harder wallet |
| Ironman | ×0.6 | full | full | full | on | **on** | sims paid, none | single save; founder death = game over (08) |
| Sandbox | off | any | any | any | any | off | free | separate save class |

### 4.7 Alert taxonomy defaults — see §3.11 A-1 table (canonical; siblings register event types into these classes via 13's event bus).

### 4.8 Screen inventory

| ID | Screen | Mode/access | Content owner | This doc owns |
|---|---|---|---|---|
| S-01 | Flight HUD | Pilot | 01/02/06 data | layout, tapes, alert strip |
| S-02 | System Map / Planner | Planner | 01/03 | frame, filters, Next-Events rail |
| S-03 | Transfer dialog + porkchop | Planner | 01 | dialog UX |
| S-04 | Logistics routes | Planner | 05 | frame |
| S-05 | Contract board | Planner/HQ | this doc | all |
| S-06 | Vehicle Designer | Engineer | 06 (rules), 02 (engines) | frame, ledger strip, sim button |
| S-07 | Works (maintenance/EVA orders) | Engineer | 05/08 | frame |
| S-08 | Base Build | Base | 07 | frame |
| S-09 | Industry dashboard | Base | 05 | frame |
| S-10 | Life Support panel | Base/vessel | 08 §5 | frame |
| S-11 | Power/Thermal grid | Base | 09 | frame |
| S-12 | Crew roster & schedule | Base/HQ | 08 | frame, recruitment market |
| S-13 | Program HQ ($ Ledger / Mass Ledger / SSI) | overlay `` ` `` | this doc | all |
| S-14 | Research | HQ tab | 11 | frame |
| S-15 | Alert Center | HQ tab | this doc | all |
| S-16 | Chronicle | HQ tab | this doc | all |
| S-17 | Encyclopedia | `F11` / hover-links | this doc | all |
| S-18 | Settings/Difficulty | Esc | this doc | all |
| S-19 | Photo mode | F10 | this doc | all |
| S-20 | Save/Load + Captain's Log card | Esc | this doc + 13 | all |

### 4.9 Chronicle event types (C-1)

`FIRST_*` (one per §4.2 row) · `LAUNCH` · `LANDING` · `DOCKING` · `SOI_ARRIVAL` · `CONTRACT_WON/DONE/FAILED` · `ROUND_RAISED` · `DEATH` (epitaph card) · `RESCUE` · `DISASTER` (Class-1 with loss) · `RISK_ACCEPTED` (A-2) · `STANDDOWN` · `ANOMALY` (03 visits) · `WONDER` (fires on completion of an 07-flagged megaproject — e.g., Europa ocean bore relay, first mass driver, Venus aerostat — or of the E-29 precursor vehicle) · `HERITAGE_VIOLATION` · `BANKRUPTCY_NEAR` · `AUDIT_PASS/FAIL` · `ACT_CHAPTER` · `SETTINGS_CHANGED` (D-3) · `PHOTO` (pinned) · `EPILOGUE`.

---

## 5. Player Interaction & UI

### 5.1 Global layout grammar

Every mode shares: (top) **status bar** — date/warp widget, cash or mass-ledger headline, Prestige, Next-Events rail; (right) **context panel** — properties of current selection; (bottom) **alert strip** — active toasts + Master Alarm; (left) mode-specific palette. One window, no modal stacking deeper than 2. UI render budget ≤ 4 ms/frame at 1080p (13 contract); all chrome is vector-drawn, numerals monospace.

**The Altimeter Rule (info hierarchy):** at any moment, the 1–3 numbers that can kill you in this mode are the largest on screen (Pilot: altitude/velocity/propellant; Base: days-of-LS/power margin; HQ: runway-days). Everything else shrinks one step per priority level; every number hover-expands to its formula (readout honesty, 08).

### 5.2 Pilot HUD (S-01)

```
+--------------------------------------------------------------------------+
| 2053-08-14 03:12 UTC  WARP [|| 1x . . . . 1M]   $1,284M  P:312           |
| NEXT: NODE 00:06:12 | LUNAR SOI 04:11:08 | CTR-114 due 19d | ALARM 2d    |
+--------------------------------+-----------------------------------------+
|                                | PELICAN-3            [stage 2/3]        |
|                                | dv 3,412 m/s   TWR 0.86   prop 64%      |
|      WORLD VIEW                | heading dial  [PRO][RET][TGT][NODE]     |
|  (vector conics, body limb,    | throttle |||||||...  72%   RCS[ ] FINE[ ]|
|   target marker, predicted     | ALT 14.2 km   VS -38 m/s   AP/PE 102/-8 |
|   impact/landing point)        | LS 41 d | PWR +2.1 kW | DOSE 0.3 mSv/d  |
|                                | ABORT PLAN: ballistic return (covered)  |
+--------------------------------+-----------------------------------------+
| [C] LH2 boiloff 0.4%/d   [A] Harvest complete, Site CER-1    [MASTER ALM]|
+--------------------------------------------------------------------------+
```

Tapes/dials switch automatically by regime (ascent / orbit / approach / landed); the abort-plan line (F-1) is always present on crewed flights. Burn UI per 01 §3.7 (t_b countdown centered on node, split-burn button).

### 5.3 Planner (S-02/S-03/S-04/S-05)

```
+--------------------------------------------------------------------------+
| filters:[craft][stations][bases][routes][contracts][anomalies][debris]   |
+--------------------------------------------+-----------------------------+
|                                            | TRANSFER  LEO -> Moon       |
|        SYSTEM MAP                          | window 2053-09-02 (18d)     |
|  (sun- or body-centered; SOI circles,      | dv 3,930 m/s  t 4.3 d       |
|   conics, route arcs with window           | [porkchop heatmap]          |
|   countdowns, closest-approach flags,      | [create nodes][set alarm]   |
|   contract destination badges)             +-----------------------------+
|                                            | NEXT EVENTS                 |
|   zoom: mouse wheel; focus: click body     |  09-02 window LUNA          |
|                                            |  09-04 node PELICAN-3       |
|                                            |  09-19 deadline CT-114      |
|                                            |  10-01 ledger: lease due    |
+--------------------------------------------+-----------------------------+
```

Contract board is a Planner tab: cards with payout, deadline, feasibility hint (planner cross-checks Δv/window against your fleet and flags "no current capability" honestly). Logistics tab = 05's node-graph overlay with gear-ratio and propellant bills.

### 5.4 Engineer (S-06/S-07)

```
+--------------------------------------------------------------------------+
| DESIGNER | WORKS          vehicle: GOSHAWK-2 rev7        [SIMULATE $0.16M]|
+---------------------+----------------------------------------------------+
| PART PALETTE        |        CELL GRID (06 rules)        | STATS          |
|  engines (02)       |        [vector cross-section,      |  wet 412 t     |
|  tanks              |         stage coloring, CoM/CoT    |  dv 9,746 m/s  |
|  crew modules       |         markers]                   |  TWR 1.31      |
|  power (09)         |                                    |  cost $11.2M   |
|  payload/fairings   |                                    |  checks: 2 WARN|
+---------------------+------------------------------------+----------------+
| ledger: hardware $11.2M + prop $0.3M + range $1M + ins. $0.9M = $13.4M   |
+--------------------------------------------------------------------------+
```

Validation list mirrors 06's builder checks (control authority per 02 §, aero per 06, fairing fit). The cost-ledger strip is this doc's: full marginal cost of the next flight (E-3) with insurance quote (E-21) inline.

### 5.5 Base (S-08…S-12)

```
+--------------------------------------------------------------------------+
| SITE: SHACKLETON-1   [BUILD][INDUSTRY][LIFE SUPPORT][POWER][CREW][VEH]   |
+----------------------------------------+---------------------------------+
|   SITE GRID (07 cells, networks        |  HEADLINES                      |
|   overlay toggles: power/pipes/        |   LS remaining   214 d          |
|   thermal/roads)                       |   power margin   +18 kWe        |
|                                        |   SSI(site)      0.61           |
|                                        |   crew 8  morale 71  dose ok    |
|                                        |  ALERT BADGES per tab           |
+----------------------------------------+---------------------------------+
```

Tab contents are sibling-owned (G-6). The headline block obeys the Altimeter Rule: days-of-LS is the largest number on any crewed site.

### 5.6 Program HQ (S-13) — the two ledgers

```
$ LEDGER (Acts 1-3)                       MASS LEDGER (post E-19 switch)
+-----------------------------------+    +-----------------------------------+
| cash $1,284M  runway ∞ (+14.3/mo) |    | UMBILICAL: SSI 0.93 ███████████░  |
| in:  contracts 18.2  services 5.0 |    |  Propellant 1.00 | LifeSup 0.99   |
| out: overhead 6.1  salaries 2.4   |    |  Structure 0.98  | Parts 0.95     |
|      leases 0.4  loan 0.0  ($M/mo)|    |  Electronics 0.78| Nuclear 0.40   |
| insurance in force: 2 policies    |    | flows t/day by site/route table   |
| next round: Series C (P 300: 288) |    | Earth manifest queue: 2 (14 t)    |
+-----------------------------------+    +-----------------------------------+
```

### 5.7 Color, iconography, line language

Palette (vector style, near-black field): background `#0A0E14`, grid `#18202B`, neutral text `#E6EDF3`. **Semantic colors:** player/controllable **cyan `#57C7E3`**; other/inert/derelict **grey-white `#9AA7B0`**; nominal/positive **green `#44CC77`**; Caution **amber `#E8C547`**; Warning **orange `#E8893B`**; Emergency/loss **red `#E25555`**; radiation **magenta `#C678DD`**; cryo/water **blue `#5398D9`**; thermal **deep orange `#D97E4A`**; money/Prestige **gold `#D9B354`**. Rules: (1) semantic colors are never reused decoratively; (2) **shape carries meaning redundantly with color** — bodies = circles, craft = triangles, stations = squares, bases = pentagons, debris = ×, anomalies = diamonds, contracts = ring-badges — so the colorblind palette swap (deuteranopia-safe alternates for green/amber/red) never changes meaning; (3) line weight: 2 px player trajectories, 1 px others; solid = current path, dashed = predicted/planned, dotted = history trail; (4) fills are rare — Aphelion is a line-drawing; filled shapes mean "selected" or "alarmed."

### 5.8 Onboarding — the first 120 minutes (T-1 charter chain, Baseline)

| Clock | Beat | Teaches | Unlocks | Pays |
|---|---|---|---|---|
| 0:00–0:08 | Cold open: sounding rocket fueled on pad; 3 actions to fly (throttle, launch, stage) | Pilot HUD, staging, warp `,`/`.` | — | — |
| 0:08–0:20 | Charter 1: recover the capsule (parachute, landing marker) | aborts, recovery value (E-3) | Finance tab | **$5M** |
| 0:20–0:40 | Charter 2: assemble provided orbital launcher in Designer; pay-and-learn Simulation of ascent | Engineer mode, Δv/TWR readouts, sim (D-5) | Designer full palette | **$10M** |
| 0:40–1:00 | Charter 3: **first orbit** (guided ascent, node to circularize, deorbit, reenter) | Planner basics, nodes, event-guard warp | Planner porkchop | **$20M** |
| 1:00–1:20 | CT-02 smallsat contract (first real money), fairings | contracts, payload integration, insurance quote | Contract board full | per CT-02 (standard E-9…E-11 terms) |
| 1:20–1:45 | Charter 4: rendezvous + **first docking** with autodock unlock at the end (01 T1) | phasing, target markers, RCS IJKL+HN | station assembly | **$15M** |
| 1:45–2:00 | Vista beat: station core docked; Flight Director points at the Moon; Series A pitch screen (promise selection) | investors, Prestige, the campaign map | Act 2 contract teasers | — |

Scripted-ish, not on rails: every charter can be failed and retried (deadline-free, penalty-free per T-1); the four charter payouts sum to **$50M** — exactly the T-1 skip grant. Physics is never faked for the tutorial (the tutorial launcher has honest 06 margins). Veterans: T-1 skip.

### 5.9 Keybindings (defaults; full remap; presets "Default", "KSP-émigré", "Left-hand mirror")

Philosophy: (1) **mouse-complete** — every action is reachable by pointer; keys accelerate; (2) one home cluster per hand per mode, no required chords; modifiers mean fine/coarse only; (3) identical keys never change meaning across modes; (4) destructive actions are double-press or covered-switch.

| Key | Action | Note |
|---|---|---|
| `F1–F4` | modes | G-2 |
| `M` | Planner (alias) | KSP muscle memory |
| `` ` `` | HQ overlay | |
| `,` / `.` | warp down/up; `Alt+,/.` physics warp | 01 canon |
| `Space` | stage (Pilot) / confirm (dialogs) | |
| `A` / `D` | rotate CCW/CW | 01 canon (2D) |
| `Shift` / `Ctrl` | throttle up/down; `Z` full, `X` cut | |
| `CapsLock` | fine-control toggle | 01 canon |
| `R` | RCS toggle; `T` attitude-hold cycle | |
| `I/K/J/L` | translate (screen axes); `H/N` fore/aft | 01 canon |
| `Backspace` ×2 | ABORT (covered) | F-1 |
| `Delete` | Master Alarm acknowledge | A-6 |
| `Tab` / `Shift+Tab` | cycle craft | G-2 |
| `Enter` | acknowledge focused toast | A-2 |
| `F5` / `F9` | quicksave/quickload (not Ironman) | D-5 |
| `F10` | photo mode; `F12` screenshot | C-5 |
| `F11` | Encyclopedia | T-4 / S-17 (F1 stays Pilot mode, G-2) |
| `Ctrl+P` | command palette (search ships/screens/contracts) | power users |
| `+/-` or wheel | zoom; `V` camera mode | |
| `1–9` | action groups (06) | |
| `Esc` | pause menu | |

### 5.10 Audio note

Three alarm sounds only (Class 1 klaxon, Class 2 tone, Class 3 chime — ISS C&W style), telemetry-blip ambience scaled by warp, silence in vacuum exterior shots (doctrine: no space roar). Music ducks under Class 1–2.

---

## 6. Progression Hooks

| Act | Tiers | Economic regime | Gameplay center of mass | Exit milestone |
|---|---|---|---|---|
| Act 1 — Earth+LEO | T0–T1 | pure $: contracts CT-01…CT-10, Firsts, Seed→Series A; insurance matters; every kg lifted hurts ($1,500/kg E-2) | Pilot+Engineer; launcher design, reuse, depots | cryo depot demo (h≈12) |
| Act 2 — Moon | T1–T2 | $ still king; CLPS-style rates; Series B; **first SSI pixels** (lunar Water/LOX) | +Base mode; first ISRU chain (04), surface ops | lunar LOX at depot; 90-d base (h≈35) |
| Act 3 — Mars & NEAs | T2 | **the hinge**: CT-16/17 money is big but logistics begins to dominate; standing services (E-12) automate cash | Planner ascendant; NTR logistics (02), windows, Mars ISRU closure (03/04) | Mars methalox + food harvest (h≈70) |
| Act 4 — Belt & Venus | T2–T3 | money fades (E-19 usually triggers); Earth manifests = Electronics/Pu238/HALEU only; mass driver changes gear ratios (05) | Base+Planner; multi-site industry, aerostat ops (07) | Silicon Independence (h≈100) |
| Act 5 — Jupiter/Saturn | T3–T4 | mass economy; $ ledger is a side-tab; Prestige and the Chronicle are the score | megaproject staging, MW-class EP fleets (02/09), Titan/Enceladus volatiles | Saturn permanent base (h≈168) |
| Endgame | T4 [SPECULATIVE tier] | none — audits | Foundation Audit (E-28) and/or Precursor (E-29) | credits (h≈180–220) |

Research costs and the tech tree are 11's; this doc supplies 11 with the **per-act money envelope** (what a Baseline player can afford): cumulative spend capacity ≈ $0.45B by end Act 1, ≈ $1.6B Act 2, ≈ $4B Act 3 (then money decouples). UI/feature unlock cadence per T-2. Difficulty presets never gate content, only friction.

---

## 7. Cross-System Interfaces

**Consumes:**
- `01-orbital-mechanics.md` — warp ladder + event guard (A-2 layers on it); transfer/window/porkchop data for contract deadlines (E-9) and Planner; canonical keybindings (§5.9); rendezvous/docking gates for tutorial; 9.4 km/s LEO canon.
- `02-propulsion.md` — engine catalog stats for Designer readouts; failure events → insurance claims (E-22) and Chronicle; NTR cold-launch rule (nuclear rider E-21); propellant list for §4.3 pricing.
- `03-solar-system.md` — anomaly/Prestige seeds (E-14, E-16 heritage zones, contract seeds CT-09/17/21); site/sector data for map content; Earth market regions flavor.
- `04-resources-isru.md` — production/consumption mass flows feeding SSI (E-26); survey chain for ice-confirmation milestones; reserve-collateral question (§9-Q3).
- `05-industry-logistics.md` — route costs/gear ratios as the physical basis of the mass economy; kit-closure χ for E-28; maintenance/spares projections feeding Class-3 alerts; production costs anchoring §4.3 sanity.
- `06-ships-stations.md` — part catalog prices ($M) and the $1,500/kg 2049 lift canon (this doc owns its evolution, E-2); designer rules behind S-06; damage model for claims.
- `07-bases-habitats.md` — base builder content (S-08); settlement berths × closure for E-28(f); base alert definitions registered into A-1 classes.
- `08-life-support-crew.md` — days-of-LS headline stat; death/morale events (F-4 adopts 08 §3.13 verbatim); crew archetypes for the recruitment market (§4.4); LS panel content (S-10).
- `09-power-thermal.md` — power-margin headline for Base mode; reactor casualty events (Class 1/2); Pu238/HALEU demand context for §4.3.
- `10-vehicles.md` — vehicle panels under the Base/VEH tab; teleoperation UX constraints (light-lag toggle D-2).
- `11-research-tech.md` — tier unlock events (drive E-2 price steps, contract pools, T-2 disclosures); research spend rates drawn from the $ ledger.
- `13-architecture.md` — event bus (alert classes A-1 are bus priorities), analytic-integration contract for the ledger (G-9), save journaling for Ironman, vector-snapshot buffer for the Chronicle (C-2), UI frame budget (§5.1).

**Provides:**
- To **all sibling docs** — the alert taxonomy and warp-interrupt law (A-1/A-2; siblings register event types into classes); the color/iconography tokens (§5.7); screen frames (§4.8); difficulty-toggle flags their systems must respect (D-2).
- To `01` — alarm-clock entries (G-11) into the event queue; pause/warp policy.
- To `04`/`05`/`06`/`07` — all Earth-side prices (§4.3), launch/lift pricing (E-2/E-3), purchase lead times (E-5), build-budget envelopes (§6).
- To `08` — recruitment market, salaries, signing bonuses, training costs (§4.4); Career/Ironman mode semantics; death economics (F-4).
- To `11` — money envelope per act; Prestige as an optional research-event reward channel.
- To `13` — Chronicle schema (C-1), ledger tick spec (G-9), session autosave points (G-10).

---

## 8. Failure Modes & Edge Cases

1. **Economic death spiral (designed).** Runway < 60 d fires Class-3; < 14 d Class-2 with auto bridge-loan offer (E-18). True game-over only per 08's total-loss rule: bankrupt AND no income source AND all crew dead/stranded. Before that: **Liquidation** flow (sell assets at 40%, cancel leases) is always offered.
2. **Warp-blindness on deadlines.** At 1,000,000x a 90-day deadline passes in ~8 s. Mitigation: deadline alerts are Class-3 (cap 1,000x) at T−30 d, Class-2 at T−7 d; G-9 processes ledger events in-order inside warp steps so penalties land at correct sim times.
3. **Alert storms.** Cascading failures (power → thermal → LS) can fire dozens of events. A-3 dedup + a storm rule: >10 Class-2/3 alerts within 60 s collapse into one "CASCADE at <site>" Class-2 card with a tree view, so the player sees the root cause first (input from 09/05 dependency graphs).
4. **Mid-step insolvency.** Cash sign change inside a warp step: G-9 forces warp-drop at the zero-crossing time, auto-draws bridge loan if available, else fires insolvency event. No retroactive debt spirals from a single long step.
5. **Contract feasibility lies.** The board must not offer windows the player cannot possibly meet: generator validates `T_deadline` against 01's next two windows; if a supply-shock or stand-down later makes a contract impossible through no player fault (force majeure list: E-23 stand-downs only), the contract suspends instead of failing.
6. **Insurance fraud.** E-22: player-commanded destruction voids coverage; "engineered" failures (disabling cooling and waiting) are still legitimate sim outcomes — accepted, but premiums reprice (f_history resets) and a third voided/edge claim in 10 yr ends coverage offers for that vehicle line. We police with incentives, not detective AI.
7. **Market dumping.** E-25 saturation handles wealth exploits; additionally sell orders > 10 × Q_sat in one transaction are refused ("no buyer") to avoid exp() underflow silliness.
8. **Stranded rescue chains.** A rescue mission that itself strands generates a second RESCUE objective; F-3 agency assist remains exactly once per campaign — if it is spent and a chain fails, the deaths are content (Chronicle DISASTER chapter), not a softlock: the program continues per 08.
9. **Founder edge cases.** Founder on a vessel at bankruptcy-liquidation: liquidation cannot sell life support out from under crew (crewed assets are liquidation-exempt until crew are home/dead — prevents the UI selling the ship around them).
10. **Tutorial skips & mid-game toggles.** T-1 skip grants charter cash equivalent; toggles changed mid-campaign apply from now on only (no retroactive dose/boiloff recompute) and asterisk the save (D-3).
11. **Ironman crash safety.** Single-save integrity via 13's journaled writes; on crash, recover to last journal checkpoint (≤ 5 min loss), never a corrupt file.
12. **Photo/Chronicle memory.** Vector snapshots are capped (≤ 64 kB each, ≤ 2,000 entries); beyond cap, oldest non-FIRST/DEATH entries degrade to text-only (C-2 buffer contract with 13).
13. **Colorblind + alarm redundancy.** All alarm states are color+shape+sound+text; the deuteranopia palette is a strict token swap (§5.7) — QA checklist item, not an afterthought.
14. **Heritage-zone griefing by physics.** Debris from a failed landing falling inside a 10-km heritage zone is not a violation (E-16 triggers on *placed* mining/industry only); the wreck still logs an embarrassing Chronicle entry.

---

## 9. Open Questions

1. **Investor equity teeth.** Rounds are grants-with-promises (E-17). Should later rounds carry board mechanics (forced milestone choices, veto on Ironman-risk launches)? Leaning no for v1 — antagonist is physics, not shareholders — but the Series-D promise feels light for $4B.
2. **Money endgame.** After E-19, should the $ ledger eventually freeze entirely (Earth economy becomes scenery), or persist for Earth-side flavor purchases forever? Current design: persists, irrelevant. Needs playtest confirmation that irrelevance reads as *triumph*, not as a broken system.
3. **Reserve-collateral finance (04's pointer).** 04 suggests borrowing against proven ISRU reserves. Adds simulationist depth in Acts 3–4 exactly when money is fading — include as a Series-C alternative, or cut? Leaning cut for v1.
4. **Contract authorship ratio.** Current plan: ~24 procedural templates + ~10 hand-authored uniques (CT-09/17/21 class). Is that enough texture for 80 h of Acts 1–3? May need a second pass of authored "campaign" contracts with light narrative.
5. **Hour-target confidence.** §4.2 hour targets are designer estimates with zero playtest data; the G-12 calibration rule needs a telemetry plan (opt-in) in 13.
6. **Second program presence.** A purely cosmetic rival (news ticker: "OrbitalX lands crew at Nobile") would make the cost-decline curve (E-2) feel inhabited without simulating competition. Cheap win or scope creep?
7. **Chronicle text generation depth.** Template grammar (C-2) vs. richer procedural prose. How many templates per event type before repetition shows in a 600-entry campaign? Budget: ~8 variants × 25 types.
8. **Crew retirement & pensions.** 08 models career dose retirement; do retired crew cost pensions ($0.1M/yr?) and appear in the Chronicle epilogue? Flavorful, trivial cost — leaning yes.
9. **Pause-anywhere vs. Ironman purism.** Should Ironman forbid pausing during Class-1 emergencies (forcing real-time response)? Current answer: no — 2D schematic clarity, not reflexes, is the game's skill. Revisit after playtests.
10. **Mission-patch generator scope.** Procedural vector emblems (C-4) are pure charm; if art budget tightens, first thing cut. Decide at vertical-slice review.
11. **Resource-name extensions (registration).** §4.3 registers `RP-1` (02), `Wafers` (05), `MedSupplies` (08), and `SurveyData` (03/05) as canonical-resource-list extensions. The integration pass must verify the owning docs define and spell them identically (or fold `MedSupplies` into an existing 08 consumable) before these names become load-bearing in code — they already bind E-12, E-26's SSI fallback mapping, and the §4.3 price table.
