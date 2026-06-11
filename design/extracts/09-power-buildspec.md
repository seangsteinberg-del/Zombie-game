# 09 — Power & Thermal: BUILD SPEC (extract)

Source: `design/09-power-thermal.md` (design-complete). Conflicts resolved per `design/DECISIONS.md`
(A2: 09 owns all power/thermal curves byte-identically; D27: ≤40 thermal nodes/base, no hierarchical
aggregation in v1; E: fusion 6 kg/kWe stays as [PLAYTEST] knob, revisit Phase 6 gate with He3 pacing).
Units: power kW (kWe electric / kWt thermal), energy kWh, temperature K, area m². Formula IDs P-n / H-n
match the source doc. Constants: solar constant **1361 W/m² @ 1 AU**; σ = **5.670e-8 W/m²K⁴**;
Pu-238 half-life **87.74 yr** (0.415 W/g as fresh PuO2); ammonia freezes **195.4 K**; Draper point **798 K**.

---

## 1. GENERATION CATALOG

### 1.1 Solar — flux and output model

**P-3 flux:** `S(d) = 1361 / d² W/m²`, d = live heliocentric distance in AU from 03's ephemeris
(includes eccentricity — NOT a per-body constant).

Per-body mean-distance reference (sim uses live d):

| Body / region | d (AU) | S (W/m²) | Note |
|---|---|---|---|
| Mercury | 0.387 (0.307–0.467) | 9,119 (6,270–14,450) | heat is the problem, not supply |
| Venus aerostat | 0.723 | 2,604 TOA | per-band f_atm, §1.1 quirks |
| Earth/Moon/LEO | 1.000 | 1,361 | baseline |
| Mars | 1.524 (1.381–1.666) | 586 (490–715) | + f_atm, f_dust |
| Vesta | 2.36 | 244 | |
| Ceres | 2.77 | 178 | solar viable, big arrays |
| Jupiter/Europa | 5.204 | 50 | possible, rarely wise |
| Saturn/Titan | 9.583 | 14.8 | TOA; Titan surface ≤1.5 W/m² (haze ×0.1) — solar dead |
| Uranus | 19.19 | 3.7 | nuclear only |
| Neptune | 30.07 | 1.5 | nuclear only |

**P-4 panel output:** `P_e = S(d) · A · η_cell · f_temp · f_dust · f_degr · f_atm · cosθ · L`
- η_cell tiers: **T0 0.295, T1 0.32, T2 0.36**; T2 thin-film blanket 0.25 @ 1.7 kg/m².
- cosθ: coasting sun-tracking = 1.0; under thrust = actual 2D thrust-attitude vs Sun geometry;
  surface tracking mount 0.95 day-avg; fixed mount 0.637 (⟨cos⟩ over half-day arc).
- L: daylight flag 0/1 with **120 s linear penumbra ramp** at eclipse/terminator.

**P-5 panel equilibrium temp** (flat plate, both faces): `T_p = [S_abs·(α − η_cell)/(2·ε_p·σ)]^0.25`,
S_abs = S·cosθ, α = 0.90, ε_p = 0.85. → 1 AU ≈ 303 K; Mars ≈ 246 K; Mercury normal ≈ 488 K.
Standard panel damage limit **425 K** (1% condition damage /h per 10 K over). Auto-tilt rule: hold
`S_abs ≤ 5,240 W/m²` (solves to θ≈55° at Mercury mean, ≈69° at perihelion) — a continuous condition,
not a fixed angle. SOL-OSR panels tolerate 575 K and run sun-normal.

**P-6 temperature derate:** `f_temp = 1 − 0.0022·(T_p − 298)`. Cold panels over-perform (Mars ≈1.11,
Jupiter ≈1.3) but apply **LILT penalty ×0.85 beyond 4 AU**.

**P-7 degradation:** `f_degr = (1 − r)^(t/yr)`, floor 0.55, panels replaceable (05 recipes):

| Environment | r/yr |
|---|---|
| LEO | 2.0% |
| Deep space / lunar / GEO | 1.0% + one-time 2% first-year burn-in |
| Mars surface | 0.5% |
| Jupiter system, standard glass | 8% |
| Jupiter system, rad-hard cover glass (T2, +25% panel mass) | 3% |

**P-8 Mars dust soiling** (surface panels only; rates owned by 03 S-9):
`f_dust −= 0.002·k_storm per sol` (k=1 clear, 10 in storm sector); init 1.0, clamp [0,1].
Natural cleaning: p = 0.005/sol wind event → `f_dust = max(f_dust, 0.85)`. SOL-EDS add-on holds
`f_dust ≥ 0.95` for 0.1 kWe/100 m². Rover wiper service restores 1.0.

**P-9 atmospheric attenuation:** vacuum f_atm = 1. Mars: `f_atm = max(0.04, exp(−0.45·τ))`,
τ per sector from 03 S-9 (baseline 0.3–0.5 → f≈0.87–0.80; regional storm τ 2–4 → 0.41–0.165;
global τ 4–9 → down to floor 0.04). Distinct from P-8 soiling — apply both, count each once.
**P-9a:** 03 S-9 owns the storm generator/state machine (regional: p=0.004/sol/sector in Ls 180–330°,
τ→2–4 over 2 sols, U(5,40) sols, spread p=0.15/sol; global: p=0.33/Mars-yr at Ls 200°±30°,
all sectors τ→U(4,9) over 10 sols, U(60,100) sols, e-fold 25 sols). Storms pre-scheduled as
warp-interrupting events at roll time.

**P-10 eclipse & night:** circular orbit `f_ecl = asin(R/r)/π` (LEO 400 km → 0.39, 36 min of 92.6 min).
Elliptical: exact shadow-cylinder entry/exit anomalies from 01, event-scheduled. Surface nights:
Moon **354.4 h**; Mars 12.33 h; Ceres 4.5 h; Mercury 2,112 h; Venus aerostat ≈72 h (super-rotation,
not the 116.8-day solar day); Titan ~191 h (moot).

**P-11 solar concentrator (process heat):** delivers `0.85·S(d)·A` W directly to a thermally-coupled
process, max 1,100 K (concentration ~200). 100 m² @ 1 AU = 116 kWt.

**Solar part catalog (§4.1)** — masses are launch-qualified; ISRU-built 2–4× heavier per 05:

| ID | Name | Tier | Mass | Area | η_cell | P_e BOL @1 AU | W/kg | Notes |
|---|---|---|---|---|---|---|---|---|
| SOL-RW (=PW-SA-R) | Rigid solar wing | T0 | 0.16 t | 12.5 m² | 0.295 | 5.0 kWe | 31 | 0.8 kWe stowed-safe |
| SOL-RO (=PW-SA-RO) | Roll-out array | T1 | 0.25 t | 46 m² | 0.32 | 20 kWe | 80 | ROSA; 0.02 kWe deploy motor |
| SOL-OSR | Mercury-rated wing | T1 | 0.20 t | 12.5 m² | 0.295 on 1/3 cell area | 1.7 kWe | 8.5 | 2/3 OSR mirror; 575 K limit; ~11 kWe sun-normal @ Mercury pre-derate |
| SOL-BLK | Thin-film blanket | T2 | 0.10 t | 59 m² | 0.25 | 20 kWe | 200 | ½ MMOD tolerance |
| SOL-FARM | Surface farm, tracking | T1 | 1.2 t | 100 m² | 0.30 | 40.8 kWe noon @1 AU (≈15.6 @Mars noon) | — | 12 kg/m² incl. tracker (0.1 kWe) |
| SOL-FARM-F | Surface farm, fixed | T0 | 0.8 t | 100 m² | 0.30 | ⟨cos⟩ 0.637 applies | — | cheap hectare-filler |
| SOL-CONC | Concentrator mirror | T1 | 0.15 t | 100 m² | — | **116 kWt** heat only | — | P-11; ≤1,100 K |
| SOL-EDS | Dust shield add-on | T2 | +2 kg/100 m² | — | — | f_dust ≥ 0.95 @ 0.1 kWe/100 m² | — | flown (Blue Ghost 2025) |

### 1.2 Radioisotope (RTG)

**P-12 decay:** `Q_t(t) = Q_t(0)·2^(−t/87.74yr)`; `P_e(t) = P_e(0)·2^(−t/87.74yr)·(1−k_TE)^(t/yr)`
with k_TE = 0.008 SiGe (net −1.6%/yr), 0.030 PbTe (net −3.8%/yr), 0.005 Stirling (net −1.3%/yr).
RTGs are **always-on**: Q_t flows to the thermal network regardless of electrical use; unused kWe is
heat in its own node; electrically **non-curtailable**. Build consumes `Pu238` resource = PuO2 mass.

| ID | Name | Tier | Mass | P_e BOL | Q_t BOL | PuO2 kg | Net decay %/yr | Anchor |
|---|---|---|---|---|---|---|---|---|
| NUK-RTG-M (=PW-RTG) | MMRTG | T0 | 45 kg | 110 We | 2.0 kWt | 4.8 | 3.8 | Curiosity |
| NUK-RTG-G | GPHS-RTG | T0 | 57 kg | 300 We | 4.4 kWt | 10.9 | 1.6 | Cassini/New Horizons; Pu238 purchase-limited (12) |
| NUK-RTG-S | Stirling RIG | T1 | 32 kg | 130 We | 0.5 kWt | 1.2 | 1.3 | ASRG |
| NUK-RHU | Heater unit | T0 | 0.04 kg | — | 1 Wt | 0.0027 | 0.79 | rover warmth |

### 1.3 Fission

**P-13 reactor model.** Defined by P_e,max, η_cv, P_t,max = P_e,max/η_cv, T_rej, core life L_core (FPY),
shield class, core mass.
- **Load following:** `P_t = clamp(P_e,dem/η_cv, 0.05·P_t,max, P_t,max)` — 5% idle simmer,
  throttle 5–100%, slew **1%/s**. Curtailment is free.
- **Waste heat:** `Q_rej = P_t − P_e` → reactor coolant node, must radiate at T_rej.
- **Auto-SCRAM** when coolant node > `T_rej + 150 K`. **Restart:** player command + coolant node
  < T_rej + coolant pump powered; ramps from 5% at 1%/s. CORE_DAMAGE blocks restart until core swap.
- **Burnup:** life ledger decrements at `P_t/P_t,max` rate; past L_core (10 FPY default, 12 Kilopower)
  output ramps down 2%/month. Core swap = Uranium + MachineParts recipe (05).

**P-14 decay heat after SCRAM** (fraction of pre-shutdown P_t, Way-Wigner):

| t | 1 s | 1 min | 1 h | 1 day | 1 week | 1 month |
|---|---|---|---|---|---|---|
| Q_decay/P_t | 6.2% | 2.7% | 1.2% | 0.64% | 0.43% | 0.32% |

Cores ≤50 kWt shed decay heat passively. Reactors **≥1 MWt** must keep radiator capacity ≥2% of P_t
for 30 days post-shutdown or take `CORE_DAMAGE` (permanent −50% P_e,max, no restart until swap).

**P-15 shadow shield & dose.** Outside the shielded half-angle (default 15°):
`D(r) = 17,000·P_t/r² [mSv/h]` (P_t kWt, r m) — same constant as 02 §3.10; never edit it, buy shield
mass instead. Inside cone: ×10⁻⁴. Electronics MTBF ×0.2 within 50 m unshielded LOS of ≥100 kWt core.
Shield mass: `m = 150 kg · (P_t/4.3 kWt)^0.6 · k_class`; k = 1 instrument (25 m), 4 crew-rated
(100 m), 20 full 4π (mobile). **≥2 m regolith burial = free crew-rating.**

**P-16 thorium MSR (T3, surface-only):** feed 0.70 kg Thorium per MWt-FPY, online refuel (no core
swap), η_cv 0.35.

**Fission/fusion part catalog (§4.3):**

| ID | Name | Tier | Mass (shield+rad incl. as noted) | P_e | η_cv | Q_rej @ T_rej | Core | Life |
|---|---|---|---|---|---|---|---|---|
| NUK-KP1 (=PW-KP1) | Kilopower-1 | T2 | 0.40 t (instr shield+rad) | 1 kWe | 0.23 | 3.3 kWt @ 400 K | 30 kg Uranium | 12 FPY |
| NUK-KP10 (=PW-KP10) | Kilopower-10 | T2 | 1.5 t (instr shield, 25 m² rad) | 10 kWe | 0.23 | 33 kWt @ 400 K | 45 kg Uranium | 12 FPY |
| NUK-FSP (=PW-FSP) | Surface fission unit | T2 | 9.0 t crew shield (−1.5 t if regolith-buried) | 100 kWe | 0.30 | 233 kWt @ 450 K | 200 kg Uranium | 10 FPY |
| NUK-MSR | Thorium molten-salt plant | T3 | 28 t (surface bldg per 07) | 500 kWe | 0.35 | 0.93 MWt @ 500 K | Th feed 0.70 kg/MWt-FPY | online |
| NUK-NEP (=PW-NEP) | NEP reactor module | T3 | 35 t (144 m² 800 K rad + instr shield) | 2,000 kWe | 0.25 | 6 MWt @ 800 K | 1.2 t Uranium | 10 FPY |
| NUK-FUS | Fusion unit [SPECULATIVE] | T4 | 60 t | 10,000 kWe | 0.60 direct | 6.7 MWt @ 900 K (100 m²) | 1 kg He3 + 0.67 kg Hydrogen per 5.3 MW-yr gross | 20 FPY |

### 1.4 [SPECULATIVE] Fusion (T4) — P-17

D-He3 PFRC-derived. Fuel: **1 kg He3 + 0.67 kg Hydrogen (ledgered; physically deuterium) per
5.3 MW-yr gross** (≈28% burnup of 354 TJ/kg mix). 60% direct conversion; **40% of gross rejected as
900 K heat** — fusion monetizes the Radiator Doctrine, never abolishes it. Specific mass **6 kg/kWe**
is THE endgame balance knob (DECISIONS E: stays as written, [PLAYTEST], revisit only at Phase 6 gate
with He3 pacing; any change is [SPECULATIVE] tuning, not physics). At 900 K (> 798 K Draper point)
fusion radiators honestly glow dull red (90-14 VD-13).

### 1.5 Conversion reference (§4.7)

| Converter | η | Reject T | Anchor |
|---|---|---|---|
| Thermoelectric (SiGe/PbTe) | 0.065 | 500–600 K | GPHS-RTG/MMRTG |
| Stirling free-piston | 0.23–0.26 | 400 K | KRUSTY/ASRG |
| Brayton recuperated | 0.30–0.35 | 450–500 K | FSP/JIMO |
| Brayton high-reject | 0.25 | 800 K | NEP (small hot radiators — T⁴ trade) |
| PV tiers | 0.295/0.32/0.36 | — | XTJ/IMM/6J |
| Fusion direct [SPECULATIVE] | 0.60 | 900 K | PFRC |

### 1.6 Beamed & relayed power (§3.7)

- **GRD-HELIO mirror relay (T2):** 40 m² steerable aperture/mast; `P = S(d)·40·0.8ⁿ` after n bounces
  (≈43.6 kW @1 AU, 1 bounce); ≤5 km/hop, lunar LOS only; enters P-4 as S with cosθ=1, or P-11 heat.
  Scatter loss is not a local heat load. LOS recheck on terrain edits.
- **GRD-LASER (T3):** 100 kWe in → 25 kWe out, ≤2,000 km; 75 kW heat split 60 TX / 15 RX.
  TX auto-inhibits without RX lock (no death rays v1).

---

## 2. STORAGE

### 2.1 Technology table (§3.4)

| Type | Tier | Pack Wh/kg | η round-trip | Self-discharge | Cycle life (100% DoD-eq) | Charge-temp floor / notes |
|---|---|---|---|---|---|---|
| Li-ion | T0 | 150 | 95% | 0.1%/day | 4,000 | no charge < 273 K; heater is P0 load |
| Solid-state | T1 | 250 | 95% | 0.05%/day | 6,000 | charges to 253 K |
| Li-S | T2 | 350 | 92% | 0.3%/day | 800 | ≥263 K; cheap mass, short life (surge/abort reserve) |
| Flywheel | T1 | 50 | 92% | **2%/h** | ∞ | no temp limit; LEO eclipse niche, useless lunar night |
| RFC (H2/O2) | T1 | per P-18 | ≈36% | none (tanked) | stack 10,000 h | the long-night bridge before fission |
| Molten-salt thermal store | T2 | 100 Wh_t/kg (550→800 K) | 95% thermal | 1%/day | ∞ | heat only, buffers 04 process heat |
| Thermal wadi (sintered regolith) | T1 | 60 Wh_t/kg (95→380 K) | — | H-1 losses | ∞ | ISRU-built rover night survival |

### 2.2 Part catalog (§4.4)

| ID | Name | Tier | Mass | Capacity | Max chg/dis | Notes |
|---|---|---|---|---|---|---|
| STO-LI-1 | Li-ion pack | T0 | 100 kg | 15 kWh | 15/30 kW | heater 50 W < 273 K (P0) |
| STO-LI-10 | Li-ion bank | T0 | 1.0 t | 150 kWh | 150/300 kW | heater 500 W < 273 K |
| STO-SS-10 | Solid-state bank | T1 | 1.0 t | 250 kWh | 250/375 kW | heater 250 W < 253 K |
| STO-LS-10 | Li-S bank | T2 | 1.0 t | 350 kWh | 200/350 kW | 800-cycle; heater 500 W < 263 K |
| STO-FW | Flywheel set | T1 | 0.5 t | 25 kWh | 100/100 kW | 2%/h drain; no heater |
| PW-FC | Fuel-cell stack | T0 | 118 kg | — | 7 kWe cont / 12 peak | Shuttle PC17C; H2+O2 → Water per P-18 |
| STO-RFC | RFC skid (ex-tankage) | T1 | 1.1 t | sized by reactants (2.0 kWh_e/kg) | 14 out / 30 in kWe | lunar-night workhorse |
| STO-TS | Molten-salt heat store | T2 | 2.0 t | 200 kWh_t (550→800 K) | 100 kWt | night-running ovens |
| STO-WADI | Thermal wadi | T1 | 20 t regolith (~0 launched) | 1,200 kWh_t (95→380 K) | 2 kWt bleed | rover lunar night |

### 2.3 Rules

- **SoC update (P-1 step 5):** `SoC += (P_chg·η_c − P_dis/η_d)·dt/3600` kWh.
- **Reserve floor:** below reserve% (default 20%) storage serves only P0/P1.
- **P-19 wear:** track each discharge excursion's DoD (peak-to-trough since last charge reversal);
  on each charge reversal decrement capacity multiplier `Δ = (1/cycle_life)·DoD^1.1`. Discharge below
  5% SoC = 1% capacity loss per event. Replace packs via 05 recipes.
- **P-18 RFC chain** (consistent with 04's 50 kWh/kg H2 electrolysis):
  Charge: Water + 50 kWh_e → 1 kg Hydrogen + 7.94 kg Oxygen (+10.6 kWh_t heat).
  Discharge: 1 kg H2 + 7.94 kg O2 → 8.94 kg Water + **18 kWh_e** + 21.4 kWh_t heat.
  Round trip 36%; ~2.0 kWh_e per kg reactants.
- **Thermal runaway (§8.5):** Li-family node > 400 K → pack destroyed; releases stored kWh +
  0.3 kWh/kg chemical as 10-min heat spike into its node (cascades via G links; Li-S ×1.5).
  Flywheel: instant kWh loss, 1% chance structural damage to host.
- **Cold charge (§8.6):** BMS refuses below chemistry floor; each cold-charge attempt −1% capacity.
- Charging sits at tier P3 but is served **from generation surplus only** — never storage-to-storage.
- Multiple units = merged pool: discharge pro-rata by available rate, charge pro-rata by headroom.

**Canonical worked problem (lunar night, 354.4 h × 10 kWe = 3,544 kWh):** Li-ion 30.3 t vs RFC ≈3.9 t
(+27.8 kWe daytime electrolysis) vs one Kilopower-10 at 1.5 t. This trade is the Act-2 ladder — use as
the balance acceptance test. Mars cross-check: 59 kWe continuous solar ≈ 1,460 m² panels + 6.5 t night
bank and dies in a global storm, vs one 9 t NUK-FSP.

---

## 3. THERMAL — THE RADIATOR DOCTRINE (code-ready)

### 3.1 Conservation H-0

Every consumed electrical watt becomes, each tick, exactly one of: (a) chemical/potential energy in
products (per 04 recipe, e.g. electrolysis 79% into bonds), (b) transmitted energy leaving the system
(EP jet power = η_total·P_in; ship radiator load is **10% of P_in for ion/Hall, 15% VASIMR, 30% MPD**
per 02 §3.9 — PPU heat rejects cold, thruster-body hot; laser/radio beams), or (c) **heat in the
device's thermal node — the default 100%**. Factories: heat_fraction 0.95 (05). Crew: 100 Wt each (08).
There is no fourth option — every Sankey ends in radiators.

### 3.2 Radiation H-1 and the T⁴ table

`Q = ε·σ·A·N_sides·(T_r⁴ − T_sink⁴)` W; ε 0.88–0.92 catalog; N_sides 2 deployed wings, 1 body-mount.

| T_r | 280 K | 300 K | 400 K | 500 K | 600 K | 800 K | 900 K | 1000 K |
|---|---|---|---|---|---|---|---|---|
| kW/m²/side (ε 0.90, sink 0) | 0.31 | 0.41 | 1.31 | 3.19 | 6.61 | 20.9 | 33.5 | 51.0 |

Doctrine: 25 kWt of 290 K habitat heat ≈ 35 m² double-sided sail; 33 kWt of 400 K reactor heat ≈ 13 m²
fins. 900 K does 81× the 300 K duty per m².

### 3.3 Environment sink temperatures H-2 (per body/situation, precomputed in 03)

| Situation | T_sink |
|---|---|
| Deep space / shadowed orbit | 4 K (treat as 0) |
| LEO mixed Earth view | 210 K |
| Moon surface day (vertical panel) | **330 K** (the lunar-noon trap) |
| Moon surface night | 95 K |
| Lunar PSR crater floor | 40 K |
| Mars surface day / night | 240 K / 180 K |
| Mercury surface day / night | 590 K / 85 K |
| Europa surface | 100 K |
| Venus aerostat / Titan surface | convection-dominated (H-3/H-4) |

Lunar-noon trap: a 290 K radiator cannot reject into a 330 K sink. Outs: heat-pump lift to ≥400 K
(H-5), RAD-SHADE (sink −100 K, +20% radiator mass), or night-schedule heavy industry.

### 3.4 Convection H-3/H-4 (atmosphere only)

`Q_conv = h·A·(T_surf − T_atm)` W:

| Atmosphere | h calm | h forced (W/m²K) | T_atm |
|---|---|---|---|
| Mars (0.61 kPa CO2) | 0.5 | 1.5 | ~210 K |
| Titan (146.7 kPa N2) | 5 | 15 | 93.7 K |
| Venus aerostat 52–56 km | 8 | 25 | 293–330 K |
| Venus surface (9.2 MPa) | 30 | 60 | 737 K — heats YOU |
| Earth (reference) | 10 | 30 | 288 K |

Titan: a bare 1 m² fin at 290 K dumps ≈1 kWt free — but uninsulated habitat walls leak ~1 kW/m².
Insulation: aerogel U = 0.2 W/m²K per 10 cm; waste heat becomes the heating budget.

### 3.5 Heat pumps H-5

`P_e = Q_c/COP`, `COP = 0.4·T_c/(T_h − T_c)` (40% Carnot), `Q_h = Q_c + P_e` rejected at T_h.
Compute net flux **against the sink, not 0 K**. Worked: lunar noon, 25 kWt from 290→420 K: COP 0.89,
28 kWe in, 53 kWt out, net 0.98 kW/m²/side vs 330 K sink → ~27 m². Shallow-lift trap: 360 K vs 330 K
sink nets only 0.25 kW/m²/side — worse than deep-space baseline; lift to 400–450 K or shade the sink.
Venus surface: 300 K interior vs 737 K, reject at 800 K → COP 0.24 → **4.2 kWe per kWt of leak**
(phase-limited ops only).

### 3.6 Lumped-node thermal network H-6 (the implementable core)

**Node partitioning:** one node per placed base structure (07) and per attachment cluster on a vessel
(06), with these ALWAYS split into their own node: radiator assemblies, battery banks, reactor cores +
coolant loops, habitat cabins (freeze/runaway gameplay depends on the separation). Budgets: **≤40
nodes/base, ≤15/vessel** (DECISIONS D27 — firm; over budget, auto-merge adjacent pair with smallest
combined C until within).

**Node ODE per tick:**
```
C_i·dT_i/dt = Q_int,i                                (H-0 loads, reactor/RTG Q, crew, sun α·A_s·S_abs)
            + Σ_j G_ij·(T_j − T_i)                   (links, W/K)
            + h_i·A_c,i·(T_atm − T_i)                (convection if atmosphere)
            − ε_i·σ·A_r,i·N_s·(T_i⁴ − T_sink⁴)       (attached radiators)
```
- `C_i = 0.9 kJ/(kg·K) × dry mass` + contents (water 4.2, atmosphere per 08).
- Link conductances G: rigid structural joint **50 W/K**; insulated-mount toggle **2 W/K**; docking
  port **10 W/K** (removed on undock); pumped loop = `Q_rated/ΔT_design` with hard cap; MLI wrap:
  ε→0.03 + 0.05 W/m²K leak; aerogel U = 0.2 W/m²K per 10 cm.
- **H-6a surface defaults:** generic external α 0.25 / ε 0.85 (white paint); panels α 0.90; radiators
  ε 0.88–0.92. A_s/A_c from part `footprint_area` (projected/wetted). Deployed sun-tracking radiator
  wings fly edge-on — **no solar term on radiators** (environmental load already in T_sink; adding it
  double-counts).

**H-7 integration:** explicit Euler, adaptive substeps,
`dt_sub ≤ 0.25·C_i/(Σ G_ij + h·A_c + 4εσA_r·N_s·T_i³)` for the stiffest node. Above 1,000× warp:
replace with damped-Newton steady-state solve (≤10 iterations), transitions event-scheduled.

**H-8 operating bands:** every part declares `[T_min_op, T_max_op, T_survival]`. Outside op band:
device offline (electronics 230–320 K typical; cabin 292–300 K). Beyond survival: 1%/h condition
damage per 10 K excess. Unpowered ammonia loop < 195 K latches `FROZEN`; thaw = 0.5 kWh per kWt of
loop rating.

**H-9 rating convention:** catalog parts quote Q_rated at T_design into 0 K sink. In play:
`Q = Q_rated·(T_loop⁴ − T_sink⁴)/T_design⁴`, capped at **1.3×Q_rated** (transport limit).

**Draper-point glow rule (90-14 VD-13, render hook):** below **798 K** radiators emit no visible glow
— 275 K ISS-class and 400 K Kilopower radiators do NOT glow, ever. Only 800 K NEP radiators earn a
faint dull red; 900 K fusion radiators glow honestly. Radiator color is driven by sim temperature.

### 3.7 Radiator / transport part catalog (§4.5)

| ID | Name | Tier | T_design | Mass | Area | Q_rated (0 K sink) | kg/kW | Notes |
|---|---|---|---|---|---|---|---|---|
| RAD-BM | Body-mount panel | T0 | 300 K | 8 kg/m² | per m² | 0.37 kWt/m² (1-side, eff ε 0.81) | 22 | MMOD skin, no deploy risk |
| RAD-HAB | Habitat wing | T1 | 290 K | 0.60 t | 50 m² (2-side) | 36 kWt | 17 | the big sail; pumped water |
| TH-RAD | Deployable mid-temp | T0/T1 | 500 K | 1.2 t | 12 m² (2-side) | 50 kWt (loop-capped; 76 radiative) | 24 | =06 stub |
| RAD-KP | Heat-pipe panel | T2 | 400 K | 5 kg/m² | per m² | 2.6 kWt/m² (2-side) | 1.9 | Ti-H2O, Kilopower style |
| RAD-HT | Refractory radiator | T3 | 800 K | 10 kg/m² | per m² | 41.8 kWt/m² (2-side) | 0.24 | C-C/Na pipes; NEP |
| RAD-LDR | Liquid-droplet radiator | T3 | 500 K | 2 kg/m²-eq | per m² | 6.4 kWt/m² | 0.31 | droplet loss 0.01%/h fluid (Polymers) |
| RAD-SHADE | Radiator shade kit | T1 | — | +20% host mass | — | T_sink −100 K | — | lunar-noon fix |
| RAD-CONV | Atmospheric convector | T2 | any | 0.3 t | 20 m² fin | h·A·ΔT (Titan calm: 20 kWt @ ΔT 200 K) | — | atmosphere only |
| THX-HP | Heat-pipe strap | T0 | ≤320 K | 0.5 kg/m | — | 1 kWt/line, ≤10 m | — | ammonia |
| THX-PL | Pumped loop | T1 | NH3 200–320 / H2O 280–500 / NaK 500–900 K (T3) | 50 kg + 0.3 kg/m | — | 25 kWt, 0.15 kWe pump | — | freeze rule H-8 |
| THX-HPMP | Heat pump | T1 | — | 0.2 t | — | lifts 10 kWt per H-5 | — | lunar noon / Venus / Mercury |

### 3.8 Heat as a resource (§3.6)

Process-heat consumers (04: ovens 900–1300 K, Sabatier 600 K, habitat warmth) may draw directly from:
solar concentrators (P-11), reactor coolant taps (≤30% of Q_rej at T_rej), RTG Q_t, fuel-cell
discharge heat, thermal stores. Heat at T serves any process needing ≤ T − 50 K, saving electric
heat watt-for-watt. Sabatier net dump: **−1.8 kWh_t/kg CH4 canonical** (gross 2.86; H-0 uses net).

---

## 4. GRID SIM

### 4.1 Topology

A **grid** = devices joined by structural attachment, surface cables, or (T2+) mirror/laser links;
merged by switchboards; every vessel has an implicit 30 kW bus. kW ledger only — no volts/Hz.
Devices declare per tick: P_gen, P_dem + priority tier, or storage (E, SoC, rates, η_c/η_d).

### 4.2 Priority tiers (player may re-pin any device)

| Tier | Name | Default members | Shed order |
|---|---|---|---|
| P0 | Life-critical | ECLSS fans/scrubbers, avionics, battery heaters, thermal pumps | never auto-shed; failure ⇒ EMERGENCY_POWER event |
| P1 | Survival-adjacent | ZBO cryocoolers, comms, hab heaters, reactor coolant pumps | last |
| P2 | Production | ISRU plants, factories, drills, survey instruments | third |
| P3 | Storage & drives | battery/RFC charging, EP thruster strings | second |
| P4 | Opportunistic | shunt-fed smelt top-up, science bonus loads | first |

### 4.3 Dispatch P-1 (per grid per tick dt)

```
1. P_avail = Σ P_gen (after env factors)
2. for tier in [P0..P4]: serve from P_avail, then storage discharge
   (per-device limits, η_d; SoC < reserve(20%) ⇒ only P0/P1 from storage;
    charging demands are NEVER served from another store's discharge)
3. surplus → storage charge (η_c, rate-limited) → shunt resistor (heat node load)
   → curtailment (solar/fission, free). RTG kWe non-curtailable → own node heat.
4. unserved shed devices latch OFF ≥300 s, retry staggered hash(device_id) mod 60 s
   (anti-flapping). `throttleable` devices scale utilization continuously (04 M-4a).
5. SoC += (P_chg·η_c − P_dis/η_d)·dt/3600
```
Determinism: throttleable devices scale pro-rata first; remaining binary devices served in ascending
device_id order (save-stable). Storage pools merge pro-rata.

### 4.4 Multi-segment flow P-2

Segments (switchboard-bounded islands) = graph nodes; cables/ports/beam links = capacity-limited
edges. Tier loop runs globally: each segment serves locally first; deficits import over links in
ascending path-loss order (path loss = Σ edge loss%·(P/P_rated)²); parallel paths split pro-rata by
remaining capacity; each edge's resistive loss deposits as heat on the cable's thermal node. Edges
carry **net flow only** (ring circulation netted to zero). Severed edge → islanded segment runs P-1
locally on its own storage.

### 4.5 Grid hardware catalog (§4.6)

| ID | Name | Tier | Mass | Rating | Loss | Notes |
|---|---|---|---|---|---|---|
| GRD-SB-S | Switchboard S | T0 | 80 kg | 30 kW | 1% → heat | 4 ports; = vessel bus |
| GRD-SB-M | Switchboard M | T1 | 0.4 t | 300 kW | 1% | 8 ports, remote-switchable |
| GRD-SB-L | Switchboard L | T2 | 2.0 t | 3 MW | 0.8% | base backbone |
| GRD-CAB-LV | Cable 600 V | T0 | 0.5 kg/m | 20 kW | 2.2%/km @ rated | loss ∝ (P/P_r)² |
| GRD-CAB-MV | Cable 3 kV | T2 | 1.0 kg/m | 200 kW | 0.45%/km | |
| GRD-CAB-HV | Line 10 kV | T3 | 2.5 kg/m | 2 MW | 0.16%/km | megabase backbone |
| GRD-SHUNT | Shunt resistor bank | T0 | 0.25 t | dumps 100 kW @ 600 K | — | 7.6 m² integral radiator; surplus sink of last resort |
| GRD-HELIO | Mirror relay mast | T2 | 0.3 t | 40 m²; S(d)·40·0.8ⁿ; ≤5 km hop | 20%/bounce scattered | lunar LOS |
| GRD-LASER | Laser link pair | T3 | 1.5 t TX + 0.8 t RX | 100→25 kWe, ≤2,000 km | 75 kW heat (60/15) | |

### 4.6 Warp contract (13)

Ledger is piecewise-constant between state changes → battery-empty/full, dawn/dusk, eclipse
entry/exit computed analytically and event-scheduled; the grid is NOT ticked at 1 Hz under 10,000×.
All curves (P-7 degradation, P-8 dust, P-12 decay, P-13 burnup) integrate closed-form in t.

### 4.7 Grid events & failure modes (§8 — all required behaviors)

1. **Brownout cascade:** shed P4→P2 with latch+stagger; P1 shed → ZBO stops → boiloff (resource leak);
   P0 unservable → `EMERGENCY_POWER`, warp stop, ECLSS battery grace (08 owns the clock).
2. **Radiator loss:** MMOD hit on pumped loop → −10% rating per cm² hole per hour until isolated
   (auto-isolation T1+); heat-pipe panels lose only struck pipes (−5%/hit). Devices then shut down in
   physics order via H-6 temps, not script order.
3. **Coolant freeze:** unpowered NH3 loop < 195 K → FROZEN; the SCRAM-at-night pump trap is intended.
4. **Reactor faults:** auto-SCRAM > T_rej+150 K; P-14 decay heat must still be rejected; no meltdowns
   (Kilopower physics is benign) — punishment is capability loss, core-swap logistics, dose zones.
5. **Battery runaway / 6. cold-charge bricking:** per §2.3 rules above.
7. **Mars dust death spiral:** storm → shedding hits EDS+heaters → faster dust + frozen banks;
   storm-mode load script + fission baseload are the designed outs (Act-3 boss fight).
8. **Lunar-noon overheat:** rejection → 0 vs 330 K sink; cabin climbs ~1–3 K/h (26 kWt / ~30 MJ/K).
9. **Switchboard failure:** isolates segment → island on local storage; cables severable by
   rover/landing debris; ring topology is player skill.
10. **Surplus nowhere to go:** lose shunt AND storage with non-curtailable surplus → excess heats the
    source nodes (overheat path).
11. **Beam edge cases:** laser TX inhibit without lock; HELIO LOS recheck on terrain edits.
12. **Degenerate warp:** steady-state H-7 solve above 1,000×; all events pre-scheduled.

### 4.8 UI hooks (build later, sim must expose the data)

Power ledger panel (per-grid stacked gen-vs-tier bars, SoC with analytic time-to-empty/full, Sankey
ending in radiators); thermal overlay (90–1000 K ramp, radiator % utilization, heat-debt ETA badge);
night/eclipse planner; brownout console with re-pinnable tiers + load-shed scripts ("storm mode");
reactor console (throttle/SCRAM/decay gauge/core-life/shield cone); alarms advisory <40% / warning
<reserve or within 20 K of limit / master (P0 risk, freeze, over-temp) generating warp-stop events.

---

## 5. GAP vs CODE

**What exists — `aphelion/sim/power.py` (~89 lines):**
- `solar_flux()` — correct P-3 inverse-square, 1361 W/m².
- `radiator_rejection_kw()` — correct H-1 (ε, N_sides, T_sink⁴ term).
- `solar_array_module()` — area × η only; **flux frozen at build time**; no env factors.
- `schedule_day_night()` — square-wave day/night toggle for synchronous rotators only.
- `thermal_balance_kw()` — single global heat pool: Σ emitted vs Σ capacity (H-0 default applied).

**What exists — `aphelion/game/basebuild.py`:** `solar_array` (40 kWe flat, `solar_scaled` site flag),
`reactor_100` (100 kWe, heat_kw 250 — **canon NUK-FSP is 233 kWt @ 450 K**), `battery_pack`
(400 kWh — no canon part matches; catalog banks are 150/250/350 kWh), `radiator_wing` (−160 kWt flat,
no temperature, no sink, no area).

**Missing entirely (by section):**

| Area | Missing |
|---|---|
| Solar model | P-4 factor chain (f_temp, f_dust, f_degr, f_atm, cosθ, L w/ penumbra ramp); live-distance re-derive; P-5 panel temp + 425 K damage + Mercury auto-tilt; P-6 derate + LILT; P-7 degradation envs + burn-in + 0.55 floor; P-8 soiling/cleaning/EDS; P-9 τ attenuation; P-10 orbital eclipse fraction (only surface day/night exists); P-11 concentrators |
| Generation catalog | All 8 solar parts, all 4 RTG parts (P-12 decay, always-on Q_t, Pu238 ledger), 6 fission/fusion parts; only one ad-hoc 100 kWe reactor exists |
| Reactor physics | P-13 load-following/simmer/slew, SCRAM + restart rule, core burnup/FPY/EOL ramp, core swap; P-14 decay heat + CORE_DAMAGE; P-15 dose field D(r), shield mass, regolith burial; P-16 MSR feed; P-17 fusion fuel ledger |
| Storage | Everything: SoC integration, η_c/η_d, rates, reserve floor, self-discharge, P-19 wear, P-18 RFC chain, charge-temp floors + heaters, thermal stores/wadis, runaway/cold-charge failures (current battery is a bare capacity number in a cap dict) |
| Thermal network | The entire H-6 lumped-node model (nodes, C_i, G links, insulated mounts, docking links, MLI/aerogel), H-2 sink table, H-3/H-4 convection, H-5 heat pumps, H-6a surface defaults, H-7 substepped Euler + steady-state warp solve, H-8 operating bands + FROZEN latch, H-9 rating convention + 1.3× cap, node budgets (D27). Current code has zero temperatures — heat is one scalar pool |
| Grid sim | P-1 priority tiers, shedding with 300 s latch + staggered retry, throttleable scaling, deterministic device order, reserve-floor policy; P-2 segments/edges/path-loss/islanding; all §4.6 hardware (switchboards, cables w/ (P/P_r)² loss, shunt, HELIO, LASER) |
| Events | Analytic SoC zero-crossing prediction, storm/eclipse/EOL event scheduling, EMERGENCY_POWER, all §8 failure modes |
| Heat-as-resource | Temperature-classed process heat, reactor coolant taps, concentrator feed |

**Numeric drift to fix when porting basebuild:** reactor_100 heat 250 → 233 kWt; battery_pack 400 kWh
→ catalog units; radiator_wing −160 kWt flat → H-9 temperature-dependent rating against site T_sink.
