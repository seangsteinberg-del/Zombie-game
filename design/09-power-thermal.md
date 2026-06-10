# 09 — Power & Thermal

**Owner:** Power & Thermal domain. **Status:** design-complete draft for implementation.
**Scope:** electrical generation (solar, radioisotope, fission, [SPECULATIVE] fusion), energy storage, the electrical grid simulation, and the **thermal network** — heat generation, transport, and rejection — for every vessel, station, base, and vehicle in the game.
**Canonical rule:** this file owns all power/thermal *performance curves*. Builder part stubs in `06-ships-stations.md` §4.6 (PW-*, TH-RAD) and factory demand tables in `05-industry-logistics.md` §4.1 reference the models here.

---

## 1. Overview

Power is the game's universal currency of capability and **heat is its universal tax**. Every machine in Aphelion — electrolyzer, Hall thruster, habitat scrubber, smelter, cryocooler — consumes watts from a simulated grid and emits watts of heat into a simulated thermal network. Neither watt is free and neither disappears.

Three design pillars:

1. **The power problem changes shape across the solar system, it never goes away.** At Mercury you drown in sunlight and die of heat. At Mars you fight dust and night. On the Moon you fight a 354-hour night. At Saturn the Sun is a bright star (14.8 W/m²) and you are nuclear or you are dead — but Titan's dense cold atmosphere makes heat *rejection* free and heat *retention* the fight. Each act of the campaign (per the campaign-act mapping in §6) is a new power-thermal puzzle made of the same parts.

2. **THE RADIATOR DOCTRINE.** Heat rejection is a first-class constraint, equal in stature to delta-v and life support. In vacuum, the only exit for waste heat is radiation, governed by Stefan-Boltzmann's T⁴ law: a radiator at 900 K rejects **81×** more heat per square meter than one at 300 K. Consequence, enforced everywhere in the design: *habitats* (which must reject heat near 290 K) carry huge gossamer radiator wings; *reactors* (which may reject at 400–900 K) carry small dense ones. A base that doubles its smelter line without doubling its radiator field cooks itself. Players who internalize T⁴ have learned real spacecraft engineering.

3. **No magic batteries, no magic reactors.** Every generator and store is anchored to flown hardware (ISS arrays, MMRTG, KRUSTY) or a named study (Kilopower 10 kWe, NASA Fission Surface Power, SP-100, JIMO), with honest flags where the game extrapolates. Fusion exists only at T4 and is tagged [SPECULATIVE].

The simulation is deliberately simple per-node — a power ledger in kW and a lumped-temperature ledger in K — but networked, prioritized, and failure-capable, so brownouts cascade, coolant freezes, and dust storms become campaign events rather than scripted drama.

---

## 2. Real-World Grounding

Named anchors used throughout (hostile fact-checkers start here):

**Solar.**
- Solar constant **1361 W/m² at 1 AU** (SORCE/TIM measured total solar irradiance); flux scales 1/d².
- Cell efficiencies: flown triple-junction GaAs ~29.5% (Spectrolab XTJ class); best flown ~32% (IMM); 39.2% 6-junction demonstrated at 1-sun (NREL, 2020; 47.1% under 143-sun concentration) → our T2 production cells at 36% are credible.
- Array specific power: ISS legacy rigid Si wings ≈ 31 W/kg (14% cells, 1990s); **ROSA/iROSA** roll-out arrays (flown: ISS upgrades 2021–23, each iROSA ~18.3 × 6 m, >20 kWe) ≈ 80–100 W/kg wing-level; blanket-array study targets 150–300 W/kg.
- Degradation: GEO comsat arrays lose ~2% the first year, then ~0.5–1%/yr; Jupiter's radiation belts are far harsher (Juno's 60 m² of cells, optimized and annealed, produce only ~500 We at Jupiter — LILT + radiation).
- Mars dust: Spirit/Opportunity measured ~0.2%/sol output loss from dust deposition between cleaning events; the 2018 global storm (optical depth τ ≈ 10.8) killed Opportunity by starving it below survival heater power.
- MESSENGER at Mercury: solar panels were 2/3 optical solar reflector (OSR) mirrors and were tilted off-Sun to keep below qualification temperature — overheating, not supply, is Mercury's problem.
- NASA "Light Bender" (STMD/LuSTR 2021): heliostat mirror relays to redirect sunlight into lunar shadowed regions — our T2 mirror-relay anchor.

**Radioisotope.**
- **GPHS-RTG** (Galileo, Ulysses, Cassini, New Horizons): ~300 We BOL from ~4.4 kWt, ~57 kg, 18 GPHS modules (~10.9 kg PuO2, ~7.8 kg Pu-238 metal), SiGe thermoelectrics ~6.8% efficient. Flight-observed electrical decay ~1.6%/yr (New Horizons: 246 We launch → ~190 We after 17 yr).
- **MMRTG** (Curiosity, Perseverance): 110 We BOL from ~2.0 kWt, 45 kg, 8 GPHS modules (~4.8 kg PuO2), PbTe/TAGS; flight-observed decay ~3.8%/yr (Curiosity ~110 We → ~80 We over 8 yr).
- **ASRG** (NASA/Lockheed, built and ground-tested, canceled 2013): ~130 We from ~500 Wt (2 GPHS modules), 32 kg, free-piston Stirling ~26% — our T1 Stirling-RTG anchor.
- Pu-238: half-life **87.74 yr**; specific power 0.567 W/g metal, ≈ 0.415 W/g as fresh flight-grade PuO2 (83% isotopic enrichment, oxide dilution) — this reconciles 10.9 kg PuO2 → 4.4 kWt and 4.8 kg → 2.0 kWt. Produced by Np-237 irradiation (Oak Ridge restart line, ~kg/yr scale), not mined — see `04-resources-isru.md` (Pu238 resource).

**Fission.**
- **KRUSTY** (NASA/NNSA, March 2018, Nevada National Security Site): full ground test of a Kilopower reactor — cast U-235/Mo core, sodium heat pipes, Stirling convertors; demonstrated passive load-following and benign failure modes. The only new-design space-class fission reactor tested in the US since the 1960s.
- **Kilopower** flight designs (Gibson/Mason et al., NASA GRC): 1 kWe ≈ 400 kg; 10 kWe ≈ 1,500 kg (43 kWt core ~44 kg U-Mo, ~23% Stirling conversion, titanium-water heat-pipe radiator ~400 K, LiH/DU shadow shield).
- **NASA/DOE Fission Surface Power** reference (2008–2010; Mason et al., "Fission Surface Power System Initial Concept Definition", NASA/TM-2010): 40 kWe, ~5.7 t, **8-yr design life**, regolith-augmented shielding — anchor for our T2 100 kWe surface unit (scaled at ~90 kg/kWe, conservative; NUK-FSP's 10 FPY core life is a deliberate mild extrapolation of the 8-yr anchor).
- **SP-100** (1980s US program, detailed design): 100 kWe from ~2.4 MWt (thermoelectric ~4.2%), lithium-cooled, 1,350 K core, ~4.6 t → 46 kg/kWe paper value for space (instrument-shielded) systems.
- **JIMO/Prometheus** (2003–05): ~200 kWe Brayton NEP design. Our T3 2 MWe unit at 17.5 kg/kWe (set in `06-ships-stations.md` PW-NEP) is an **extrapolation beyond any completed design** — flagged honestly; MWe-class NEP studies project 5–25 kg/kWe depending on radiator temperature.
- Decay heat after shutdown: Way-Wigner correlation (≈6% of full power at 1 s, ~1.2% at 1 h).
- Molten-salt thorium breeder (T3): ORNL MSRE operated 1965–69; thorium-cycle plant studies (ORNL-4541) — lab/pilot-demonstrated, never flown, surface-only in game.

**[SPECULATIVE] Fusion (T4).** Princeton Field-Reversed Configuration / Direct Fusion Drive studies (D-He3, 1–10 MW class, claimed ~1 kWe/kg); we use a conservative 6 kg/kWe and it **still needs radiators**.

**Thermal.**
- Stefan-Boltzmann constant σ = 5.670×10⁻⁸ W/(m²·K⁴).
- ISS External Active Thermal Control System: two pumped ammonia loops, six deployable radiator ORUs (~23 m × 3.4 m, ≈1.1 t each), rejecting up to ~70 kW total near 275 K → ~13 kg/m². Two kg/kW numbers, both stated so the catalog basis is traceable: **~95 kg/kW at flight operating conditions** (Earth-view sink, as flown) and **~24 kg/kW under the 0 K-sink rating convention** used by H-9 and the §4.5 catalog.
- Ammonia coolant freezes at 195.4 K (why ISS uses it externally); water freezes at 273 K (internal loops only); NaK and sodium heat pipes serve 500–900+ K (SP-100, Kilopower heritage).
- Liquid droplet radiators: 1980s NASA Lewis/AFRL ground and reduced-gravity demonstrations, projected <2 kg/m² — T3.
- Lunar thermal environment: equatorial noon regolith ~390 K, night ~95 K; permanently shadowed craters ~40 K (Diviner). Mercury: noon ~700 K, night ~100 K, solar day 176 Earth days. Titan: 93.7 K, 146.7 kPa N2 — convection works. Venus: 737 K / 9,200 kPa at the surface (Venera probes survived ~2 h); 293–330 K / 45–81 kPa at the 52–56 km aerostat band (NASA HAVOC; canonical lookup in `03-solar-system.md` §4.4.2).
- Li-ion: modern NCA/NMC cells 250–300 Wh/kg cell-level; integrated EV/automotive packs (with BMS/thermal) ~130–180 Wh/kg — the anchor for our 150 Wh/kg T0 pack. (The ISS Li-ion ORUs are far heavier: 30 GS Yuasa LSE134 cells, ~14.9 kWh in a ~197 kg unit ≈ 75–80 Wh/kg — structural/EVA-handling overhead, not cell chemistry.) Li-ion cannot be charged below 0 °C (lithium plating) — battery heaters are real and modeled.
- H2/O2 regenerative fuel cells: Shuttle PC17C alkaline stack 12 kWe peak / 7 kWe continuous at 118 kg; PEM electrolysis ~50 kWh/kg H2 (per `04-resources-isru.md` canon); round-trip ~36–45% — NASA Glenn RFC studies for lunar night.
- Flywheels: NASA G2 / Beacon Power class, ~25–50 Wh/kg system, >10⁵ cycles, high self-discharge — LEO cycling niche.

---

## 3. Game Model

All power in **kW** (kWe electric, kWt thermal), energy in **kWh**, temperature in **K**, area in **m²**. Formulas are numbered P-n (power), H-n (heat) for cross-reference from sibling docs.

### 3.1 The electrical grid model

A **grid** is a set of devices joined by physical connection: structural attachment within one vessel/base module cluster, surface **cables** between base structures, or (T2+) mirror/laser links. Grids are merged by **switchboards** (§4.6); a vessel has an implicit built-in 30 kW bus.

Each device declares per tick:
- `P_gen` (kWe available this tick — generators),
- `P_dem` (kWe wanted this tick — consumers) and a **priority tier**,
- storage devices declare capacity `E` (kWh), state-of-charge `SoC`, max charge/discharge rates (kW), efficiencies.

**Priority tiers** (consumer default assignments; player may re-pin any device):

| Tier | Name | Default members | Shed order |
|---|---|---|---|
| P0 | Life-critical | ECLSS fans/scrubbers (08), avionics, battery heaters, thermal-control pumps | never auto-shed; failure ⇒ emergency event |
| P1 | Survival-adjacent | ZBO cryocoolers (02/06), comms, habitat heaters, reactor coolant pumps | last |
| P2 | Production | ISRU plants (04), factories (05), drills, survey instruments | third |
| P3 | Storage & drives | battery/RFC charging, EP thruster strings (02) | second |
| P4 | Opportunistic | shunt-fed smelting top-up, science bonus loads | first |

**Tick resolution (P-1), executed per grid per simulation tick `dt` (s):**

```
1. P_avail   = Σ P_gen (after env. factors §3.2–3.3)
2. for tier in [P0, P1, P2, P3, P4]:
       serve tier from P_avail, then from storage discharge
       (respecting per-device discharge limits, η_d, and the
        storage reserve floor: SoC < reserve% serves only P0/P1;
        default reserve 20%)
3. surplus = P_avail − Σ served
   surplus → storage charge (η_c, rate-limited)
            → shunt resistor (becomes heat node load, §3.5)
            → generator curtailment (solar/fission throttle; free)
   RTG output is non-curtailable electrically; unused RTG kWe
   becomes heat in its own node (it was heat anyway).
4. unserved devices in a shed tier turn OFF and latch off for
   ≥300 s game time, then retry staggered by hash(device_id) mod 60 s
   (prevents brownout flapping). Production devices may instead
   scale `utilization` continuously per 04 (M-4a) if flagged
   `throttleable`.
5. Storage update: SoC += (P_chg·η_c − P_dis/η_d)·dt/3600   [kWh]
```

**P-1 clarifications (deterministic dispatch):**
- *Storage charging* sits at P3 priority but is served **from generation surplus only** — never from another store's discharge (step 2's "then from storage" skips charge-type demands; no battery-to-battery round trips).
- *Partially served tiers:* devices flagged `throttleable` scale `utilization` pro-rata first; remaining binary devices are served in ascending `device_id` order until power runs out (deterministic, save-stable).
- *Multiple storage units* act as a merged pool: discharge is drawn pro-rata by each unit's available discharge rate; charge is distributed pro-rata by each unit's remaining headroom (per-unit rate limits and reserve floors respected).

No voltage/frequency simulation: the grid is a kW ledger. **Multi-segment flow (P-2):** segments (switchboard-bounded islands) are graph **nodes**; cables, switchboard ports, and mirror/laser links are capacity-limited **edges**. The P-1 tier loop runs *globally* over each connected graph:

```
for tier in [P0..P4]:
  1. each segment first serves its tier demand from local generation
     (and storage, per P-1 step 2)
  2. remaining deficits import over links in ascending path-loss order
     (path loss = Σ edge loss%·(P/P_rated)² along the path); each edge
     caps at its rating minus flow already committed this tick
  3. parallel paths split a deficit pro-rata by remaining edge capacity
  4. each edge's resistive loss is deposited as heat on that cable's
     thermal node (H-6)
```

Edges carry **net flow only**: circular flow around a ring is forbidden — the allocator nets opposing flows to zero before applying ratings. A failed/severed edge is removed; segments left without a path island and run P-1 locally on their own storage (§8.9). Cable resistive loss (catalog %/km at rated load) scales with `(P/P_rated)²`.

**Event prediction under warp** (interface to `13-architecture.md`): between state changes the ledger is piecewise-constant, so battery-empty/full, dawn/dusk terminator crossings, and eclipse entry/exit are computed analytically and scheduled as events; the grid is not ticked at 1 Hz during 10,000× warp.

### 3.2 Solar power

**Flux (P-3):** `S(d) = 1361 / d²  W/m²`, `d` in AU (true distance from the Sun, including the body's orbit eccentricity — read from `03-solar-system.md` ephemeris, not a constant).

**Per-body solar flux table** (mean-distance values; the sim uses live `d`):

| Body / region | d (AU) | S multiplier | S (W/m²) | Notes |
|---|---|---|---|---|
| Mercury | 0.387 (0.307–0.467) | ≈6.7× | 9,119 (6,270–14,450) | flux is not the problem; heat is (§3.8); range per 03 §3.3 S-4a |
| Venus (aerostat band) | 0.723 | 1.91× | 2,604 top-of-atmosphere | §3.8 cloud rules |
| Earth / Moon / LEO | 1.000 | 1.00× | 1,361 | baseline |
| Mars | 1.524 (1.381–1.666) | 0.431× | 586 (490–715) | + atmosphere & dust factors |
| Vesta | 2.36 | 0.179× | 244 | |
| Ceres | 2.77 | 0.131× | 178 | solar still viable with big arrays |
| Jupiter / Europa | 5.204 | 0.0369× | 50 | Juno proved solar *possible*; rarely *wise* (§3.8); 03 §4.4.9 canon |
| Saturn / Titan | 9.583 | 0.0109× | 14.8 | top-of-atmosphere; Titan surface §3.8 |
| Uranus | 19.19 | 0.0027× | 3.7 | nuclear only |
| Neptune | 30.07 | 0.0011× | 1.5 | nuclear only |

**Panel output (P-4):**

```
P_e = S(d) · A · η_cell · f_temp · f_dust · f_degr · f_atm · cosθ · L
```
- `A` panel area (m²); `η_cell` per tier: **T0 0.295, T1 0.32, T2 0.36** (rigid/ROSA); T2 thin-film blanket 0.25 at 1.7 kg/m².
- `cosθ`: incidence factor. Coasting vessels with sun-tracking enabled: 1.0. Under thrust: computed from actual 2D thrust-attitude vs Sun geometry (the transfer planner in 06 displays it). Surface farms: tracking mounts 0.95 daytime average; fixed mounts 0.637 (⟨cos⟩ over a half-day arc).
- `L` daylight flag (0 in eclipse/night, with 120 s linear penumbra ramp).

**Panel equilibrium temperature (P-5)** (flat plate, radiating both faces):

```
T_p = [ S_abs · (α − η_cell) / (2 ε_p σ) ]^0.25      S_abs = S·cosθ
```
with absorptance α = 0.90, panel emissivity ε_p = 0.85. At 1 AU: T_p ≈ 303 K. At Mars: ≈ 246 K. At Mercury normal-incidence: ≈ 488 K — **above the 425 K damage limit of standard panels** (panel takes 1% condition damage per hour per 10 K over limit). Mercury-rated OSR panels (T1, MESSENGER anchor) devote 2/3 of panel area to OSR mirrors — only 1/3 active cells, so ~1/3 of a standard wing's output per m² of panel — but tolerate 575 K and run sun-normal at Mercury (SOL-OSR catalog row). Standard panels survive by tilting; the rule is the **condition, not a fixed angle**: auto-tilt to hold `S_abs = S(d)·cosθ ≤ 5,240 W/m²` (→ T_p ≤ 425 K), which is θ ≈ 55° at Mercury mean distance and θ ≈ 69° at perihelion (S = 14,450 W/m²) — solved continuously from P-5.

**Temperature derate (P-6):** `f_temp = 1 − 0.0022·(T_p − 298 K)` (triple-junction coefficient ≈ −0.06%/°C absolute ≈ −0.22%/°C relative). Cold panels over-perform: at Mars f_temp ≈ 1.11; at Jupiter ≈ 1.3 but a LILT penalty ×0.85 applies beyond 4 AU (low-intensity low-temperature flat-band losses, Juno-informed).

**Degradation (P-7):** `f_degr = (1 − r)^(t/yr)`, environment-dependent annual rate `r`:

| Environment | r (per year) |
|---|---|
| LEO (atomic oxygen + trapped protons) | 2.0% |
| Deep space / lunar / GEO | 1.0% (plus one-time 2% first-year burn-in) |
| Mars surface (atmosphere stops protons) | 0.5% |
| Jupiter system, standard glass | 8% |
| Jupiter system, rad-hard thick cover glass (T2, +25% panel mass) | 3% |

Floor at 0.55; panels are replaceable (MachineParts + Silicon per 05 recipes).

**Mars dust soiling (P-8):** deposition factor `f_dust` on surface panels only (this is `03-solar-system.md` S-9's "panel soiling" multiplier — rates owned by S-9, applied here; distinct from the atmospheric `f_atm` of P-9):
```
f_dust(t+1sol) = f_dust − 0.002·k_storm ;  k_storm = 1 clear sky, 10 in a storm-flagged sector
                                            (S-9 canon: −0.2%/sol clear, −2%/sol storm)
```
`f_dust` initializes at **1.0** on deployment (and on wiper service) and clamps to **[0, 1]**. Natural cleaning events: per sol, probability 0.005 of a wind event (S-9) restoring `f_dust → max(f_dust, 0.85)` (Spirit/Opportunity behavior). Parts mitigation: **Electrodynamic Dust Shield** add-on (T2, NASA KSC EDS anchor, flown on the 2025 Blue Ghost lunar lander; tier matched to 11's PW-06 node and 07): holds `f_dust ≥ 0.95` for 0.1 kWe per 100 m²; rover wiper service (a `10-vehicles.md` task) restores 1.0.

**Atmospheric attenuation (P-9):** `f_atm` = 1 in vacuum. Mars: `f_atm := f_dust(τ) = max(0.04, exp(−0.45·τ))` — `03-solar-system.md` S-9's canonical direct+diffuse panel fit (Appelbaum & Flood / Opportunity 2018), defined once in 03 and counted exactly once here (note the naming map: 03's "f_dust(τ)" is this *atmospheric* factor; 09's P-8 soiling multiplier is 03's separate "panel soiling" term). τ per sector from S-9: 0.3–0.5 seasonal baseline (f ≈ 0.87–0.80), 2.0–4.0 regional storm (f ≈ 0.41–0.165), 4–9 global storm (f ≈ 0.165 down to the 0.04 floor; the real 2018 storm hit τ ≈ 10.8 — Opportunity's end). Venus and Titan: special rules in §3.8.

**Eclipse & night (P-10).** In our 2D planar world every orbit crosses the body's shadow once per revolution. Circular orbit of radius `r` about body of radius `R`:
```
eclipse fraction  f_ecl = asin(R/r) / π
```
LEO 400 km: f = 0.39 → 36 min of a 92.6 min orbit (matches reality). Elliptical orbits get exact entry/exit anomalies from the shadow-cylinder intersection (computed in `01-orbital-mechanics.md` geometry, scheduled as events). Surface night durations (solar day / 2): Moon **354.4 h**; Mars 12.33 h (sol = 24.66 h); Ceres 4.5 h; Mercury **2,112 h** (88 days — give up); Venus aerostat ≈72 h (super-rotation cycle, §3.8); Titan ~191 h (moot — no usable sun).

**Solar concentrators for process heat (P-11):** mirror of area A delivers `0.85·S(d)·A` W (S in W/m², A in m²; ÷1000 for kWt) directly to a thermally-coupled process (no electric conversion), at up to 1,100 K (re-radiation limited at concentration ratio ~200). This is how the Sublimation Tent Miner's 80 kWt (04, RX catalog) is cheaply fed on the Moon: one 100 m² mirror at 1 AU = 116 kWt.

### 3.3 Nuclear power

**RTGs (P-12).** Thermal output decays with the fuel; electrical output decays faster (thermocouple degradation, flight-calibrated):
```
Q_t(t)  = Q_t(0) · 2^(−t / 87.74 yr)
P_e(t)  = P_e(0) · 2^(−t / 87.74 yr) · (1 − k_TE)^(t/yr)
   k_TE = 0.008 (SiGe, GPHS-RTG → net ≈ −1.6%/yr)
        = 0.030 (PbTe, MMRTG  → net ≈ −3.8%/yr, matches Curiosity)
        = 0.005 (Stirling, ASRG class → net ≈ −1.3%/yr)
```
RTGs are always-on: `Q_t` flows into the thermal network whether or not `P_e` is used. Stand-alone RTGs include fins sized for their own heat; an RTG enclosed in a bay adds its `Q_t` to that node. Fuel ledger: building an RTG consumes `Pu238` resource equal to its PuO2 mass (we ledger oxide mass under the Pu238 name; 0.415 W/g fresh).

**Fission reactors (P-13).** A reactor is defined by: `P_e,max` (kWe), conversion efficiency η_cv, core thermal `P_t,max = P_e,max/η_cv`, design radiator temperature `T_rej`, core life `L_core` (full-power-years, FPY), shield class, and Uranium (or Thorium) core mass.

- **Load following:** Kilopower-class cores self-regulate (KRUSTY demonstrated). Reactor thermal output tracks demand: `P_t = clamp(P_e,dem/η_cv, 0.05·P_t,max, P_t,max)` — a 5% idle simmer at zero demand, rated output (never above `P_t,max`) at full demand. Throttle range 5–100%, slew 1%/s.
- **Conversion efficiencies:** thermoelectric 0.065 (RTG/SP-100 class), Stirling 0.23 (Kilopower), Brayton 0.30 (FSP/MSR), Brayton-HT 0.25 at 800 K rejection (NEP — lower η bought deliberately for hot, small radiators: the T⁴ trade in action).
- **Waste heat:** `Q_rej = P_t − P_e` flows to the reactor's coolant node and **must** be radiated at `T_rej` (§3.5). A reactor whose coolant node exceeds `T_rej + 150 K` SCRAMs automatically. **Restart rule:** a SCRAMed core may be restarted on player command once its coolant node has cooled below `T_rej` *and* the coolant pump is powered (the §8.3 frozen-loop trap); it ramps up from the 5% simmer at the 1%/s slew limit. A core with `CORE_DAMAGE` cannot restart until core swap.
- **Core burnup:** core life ledger decrements at `P_t/P_t,max` rate; at end of `L_core` (10 FPY default, 12 for Kilopower) output capability ramps down 2%/month. Core swap = scheduled maintenance consuming a fresh core (Uranium + MachineParts recipe in 05). Actual fissioned mass is honest but tiny (10 kWe·10 yr ≈ 0.17 kg fissioned); the core is replaced for materials/poisoning reasons, as in real designs.
- **Decay heat after shutdown (P-14)** — Way-Wigner, table form (fraction of pre-shutdown `P_t`):

| t after SCRAM | 1 s | 1 min | 1 h | 1 day | 1 week | 1 month |
|---|---|---|---|---|---|---|
| Q_decay/P_t | 6.2% | 2.7% | 1.2% | 0.64% | 0.43% | 0.32% |

Kilopower-class (≤50 kWt) cores shed decay heat passively — no action needed (KRUSTY's demonstrated benignity). Reactors ≥ 1 MWt must keep radiator capacity ≥ 2% of `P_t` available for 30 days post-shutdown or suffer a `CORE_DAMAGE` event (permanent −50% `P_e,max`, no restart until core swap).

**Shadow shielding (P-15).** Reactors irradiate a cone. The **dose-rate source term** is a power-system property and is emitted by this file: outside the shielded half-angle (default 15°),
```
D(r) = 17,000 · P_t / r²      [mSv/h]   (P_t in kWt, r in m)
```
calibrated to `02-propulsion.md` §3.10's canonical unshielded-core anchor — 1×10⁴ Sv/h at 25 m for a 367 MWt core at full power (check: 17,000 × 367,000 / 25² ≈ 1.0×10⁷ mSv/h) — so an operating unshielded fission core produces the *same* field whether it drives a thruster (02) or a grid (09). An unshielded 100 kWt surface core gives ≈170 mSv/h at 100 m. This is 02's ~3%-prompt-n/γ-leakage derivation inherited as-is, not an independent transport calculation; per 02's rule, any gameplay softening must be bought as shield mass, never by editing the unshielded constant. Inside the shielded cone the field is attenuated ×10⁻⁴. `08-life-support-crew.md` integrates this field against its crew dose model and limits; electronics additionally take an MTBF penalty ×0.2 within 50 m unshielded line-of-sight of a ≥100 kWt core. Shield mass rule:
```
m_shield = m_ref · (P_t / P_t,ref)^0.6 · k_class
  instrument-rated (25 m separation): m_ref = 150 kg at P_t,ref = 4.3 kWt   (Kilopower-1 anchor)
  crew-rated (100 m, habitat dose floor): k_class = 4
  4π full shield (mobile reactor, `10-vehicles.md`): k_class = 20
```
**Burial substitution:** ≥ 2 m of Regolith over/around a surface reactor = free crew-rating (FSP reference design practice). Sanity anchors: Kilopower-10 instrument shield ≈ 150·10^0.6 ≈ 600 kg (published ~550 kg); PW-FSP's 9 t includes its crew-rated shield.

**Thorium molten-salt breeder (T3, P-16):** surface-only plant; burns ~1 kg Thorium per 1.43 MWt-year, i.e. **0.70 kg Thorium per MWt-FPY** (≈0.56 kg of that actually fissioned, the rest breeding/processing losses; mass-conservation floor: 1 MWt-yr ÷ 8.2×10¹³ J/kg ≈ 0.39 kg fissioned — every fissioned U-233 nucleus came from a fed Th-232 nucleus, so feed ≥ fissioned mass always). Online refueling: no core swap, continuous feed **equal to the burn, 0.70 kg Thorium/MWt-FPY** (≈1.0 kg/yr for the 500 kWe / 1.43 MWt NUK-MSR at full power); η_cv 0.35.

**[SPECULATIVE] Fusion (T4, P-17):** D-He3 PFRC-derived units; consume **1 kg He3 + 0.67 kg Hydrogen per ~5.3 MW-year of gross power**. Ledger simplification: the fuel is physically *deuterium* (protium does not participate in the D-He3 reaction); we ledger it under the canonical Hydrogen resource at the stoichiometric 2.014:3.016 mass ratio (0.67 kg D per kg He3). Energy bookkeeping: the fuel mix is 354 TJ/kg, but only ~28% of injected fuel fuses before exhaust/recirculation losses — 354 TJ/kg × 1.67 kg × 0.28 ≈ 167 TJ ≈ 5.3 MW-yr (full burnup would give ~18.7 MW-yr per 1.67 kg). 60% direct conversion; reject 40% of gross as 900 K heat. The DFD-5 drive in `02-propulsion.md` additionally exports 1 MWe bus power when idle-burning. Fusion does not abolish the Radiator Doctrine; it monetizes it at 900 K.

### 3.4 Energy storage

| Type (part §4.4) | Tier | Pack-level specific energy | η round-trip | Self-discharge | Cycle life (100% DoD-equiv) | Notes |
|---|---|---|---|---|---|---|
| Li-ion pack | T0 | 150 Wh/kg | 95% | 0.1%/day | 4,000 | cannot charge below 273 K (heater = P0 load); anchor: 21700 NCA cells ~260 Wh/kg derated to pack |
| Solid-state pack | T1 | 250 Wh/kg | 95% | 0.05%/day | 6,000 | charges to 253 K |
| Li-S pack | T2 | 350 Wh/kg | 92% | 0.3%/day | 800 | cheap mass, short life — surge & abort reserves; charges ≥263 K |
| Flywheel | T1 | 50 Wh/kg | 92% | 2%/h | effectively ∞ | LEO eclipse cycling; useless for lunar night (self-discharge); no charge-temperature limit |
| Regenerative fuel cell (RFC) | T1 | see P-18 | ≈36% | none (tanked H2/O2) | stack 10,000 h | the long-night solution before fission |
| Thermal store (molten salt) | T2 | 100 Wh_t/kg (heat only, 550→800 K) | 95% thermal | 1%/day | ∞ | buffers process heat for 04 recipes |
| Thermal wadi (sintered Regolith) | T1 | 60 Wh_t/kg over 95→380 K | — | sized by H-1 losses | ∞ | ISRU-built night-survival heat for rovers (NASA thermal wadi concept) |

**Battery wear (P-19):** equivalent-cycle counting, no rainflow needed. The sim tracks each discharge excursion's depth `DoD` = peak-to-trough SoC since the last charge reversal; **on each charge reversal** the capacity multiplier decrements `Δ = (cycle_life)⁻¹ · (DoD)^1.1` (partial cycles accrue as their own excursions; continuous micro-cycling thus wears packs sub-linearly, as in reality). Replace packs via 05 recipes. Discharge floor: packs damaged below 5% SoC (1% capacity loss per event).

**RFC chain (P-18)** — uses canonical resources, consistent with `04-resources-isru.md` electrolysis canon (50 kWh/kg H2):
```
Charge:    Water + 50 kWh_e → 1 kg Hydrogen + 7.94 kg Oxygen   (+10.6 kWh_t waste heat per kg H2)
Discharge: 1 kg Hydrogen + 7.94 kg Oxygen → 8.94 kg Water + 18 kWh_e + 21.4 kWh_t heat per kg H2
Round trip: 18/50 = 36%.  Reactant-mass figure of merit: ~2.0 kWh_e per kg reactants.
```
Fuel-cell stack hardware = PW-FC (Shuttle PC17C: 7 kWe continuous, 118 kg, §4.4); electrolyzer per 04; tanks per 06.

**WORKED DESIGN PROBLEM — surviving the lunar night (354.4 h), 10 kWe continuous habitat load.**
Energy required: 10 × 354.4 = **3,544 kWh**.

| Option | Mass | Extra daytime power | Verdict |
|---|---|---|---|
| A. Li-ion (T0): 3,544,000 Wh ÷ (150 Wh/kg × 0.8 DoD × 0.975 η_d) | **30.3 t** of batteries | +10.5 kWe to recharge | absurd to land, plausible to *manufacture* later (05 in-situ packs) |
| B. RFC (T1): 197 kg Hydrogen + 1,563 kg Oxygen reactants; 2× PW-FC (0.24 t); 30 kWe electrolyzer (0.45 t); ZBO H2 + O2 tankage (~1.1 t); plumbing/radiators (~0.4 t) | **≈ 3.9 t** | +27.8 kWe daytime (197 kg × 50 kWh/kg ÷ 354 h) ≈ 0.35 t ROSA | the bridge solution; RT 36% is the price |
| C. Kilopower-10 (T2): one PW-KP10 | **1.5 t** | none; night-indifferent | endgame of the Act-2 power arc |

This trade *is* Act 2's tech ladder: players land batteries, build RFC infrastructure from ISRU water, and research fission to escape the night entirely (§6).

**Mars cross-check (canon with 04 §"Worked sizing example"):** 59 kWe continuous for the 100 t/500-day methalox plant via solar: continuous-equivalent surface solar yield ≈ 586 W/m² × η 0.30 × 0.5 day-fraction × ⟨cos⟩ 0.64 × f_atm 0.80 (τ 0.5 per P-9/03 S-9) × f_dust 0.9 ≈ **40 We/m² continuous** → ~1,460 m² of panel, ~0.4 ha of land at 50% packing with storm margin — matching 04's "~0.4 ha" — plus a 726 kWh (6.5 t Li-ion) night bank, *and the whole farm dies for months in a global storm*. The one-line alternative: a single 100 kWe fission unit (PW-FSP, 9 t). This is the intended Act-3 lesson.

### 3.5 THE RADIATOR DOCTRINE — the thermal network

**Every watt is accounted (H-0, conservation rule):** electrical energy consumed by a device becomes, each tick: (a) chemical/potential energy in products (e.g., electrolysis stores 39.4/50 = 79% in bonds; ledgered per 04 recipe), (b) transmitted energy leaving the system (laser links, radio, thrust beam — EP jet power is `η_total·P_in`, anchored on flown total efficiencies: NSTAR ~61%, NEXT ~71%, Hall ~55–60%; of the non-jet balance, only the fraction deposited in the PPU and thruster body is a ship radiator load — **10% of P_in for gridded ion and Hall strings, 15% for VASIMR, 30% for MPD** (anode-fall losses land in the thruster body), per `02-propulsion.md` §3.9, which owns these fractions — the rest of the non-jet power leaves in the plume as divergence/ionization losses; PPU heat rejects at low temperature, the real radiator driver, thruster-body heat at high temperature), or (c) **heat in the device's thermal node — the default 100%**. Factories: `heat_fraction` 0.95 per `05-industry-logistics.md` canon. Crew add 100 Wt each (08). There is no fourth option.

**Radiation (H-1):** a radiator surface rejects
```
Q = ε · σ · A · N_sides · (T_r⁴ − T_sink⁴)        [W]
```
ε = 0.88–0.92 (catalog), N_sides = 2 for deployed wings, 1 for body-mount/surface-laid panels.

**The T⁴ table every player will learn** (ε = 0.90, per side, T_sink ≈ 0):

| T_r | 280 K | 300 K | 400 K | 500 K | 600 K | 800 K | 900 K | 1000 K |
|---|---|---|---|---|---|---|---|---|
| kW/m² per side | 0.31 | 0.41 | 1.31 | 3.19 | 6.61 | 20.9 | **33.5** | 51.0 |

Worked contrast (the doctrine in one line): rejecting **25 kWt of habitat heat at 290 K** needs ~35 m² of double-sided wing; rejecting **33 kWt of Kilopower-10 reactor heat at 400 K** needs ~13 m². Same order of heat, 2.7× less area at +110 K; at 900 K the same panel area does **81×** the 300 K duty. Habitats get sails; reactors get fins.

**Effective sink temperatures (H-2)** (precomputed per body/situation in `03-solar-system.md` data tables; radiator Q uses them):

| Situation | T_sink |
|---|---|
| Deep space / shadowed orbit | 4 K (treat as 0) |
| LEO, mixed Earth view | 210 K |
| Moon surface, day (vertical panel) | 330 K |
| Moon surface, night | 95 K |
| Lunar PSR crater floor | 40 K |
| Mars surface day / night | 240 K / 180 K |
| Mercury surface, day / night | 590 K / 85 K |
| Europa surface | 100 K |
| Venus aerostat 55 km / Titan surface | convection-dominated, §H-4 |

Note the lunar-noon trap: a 290 K habitat radiator **cannot reject into a 330 K sink**. Options: heat-pump the loop to ≥400 K (H-5 — a shallow 360 K lift barely clears the 330 K sink and needs *more* area than the deep-space baseline; see the H-5 worked example), the Radiator Shade kit (§4.5: parabolic shade, sink −100 K, +20% radiator mass — real lunar radiator-study practice), or schedule heat-heavy industry into the night. This is deliberate gameplay.

**Convection (H-3/H-4):** in atmosphere, surfaces also exchange
```
Q_conv = h · A · (T_surf − T_atm)        [W]
```

| Atmosphere | h, calm (W/m²·K) | h, forced/wind | T_atm |
|---|---|---|---|
| Mars (0.61 kPa CO2) | 0.5 | 1.5 | ~210 K |
| Titan (146.7 kPa N2, 5.3 kg/m³) | 5 | 15 | 93.7 K |
| Venus aerostat 52–56 km | 8 | 25 | 293–330 K |
| Venus surface (9.2 MPa CO2) | 30 | 60 | 737 K — heats *you* |
| Earth (reference) | 10 | 30 | 288 K |

On Titan a bare 1 m² fin at 290 K dumps `5×(290−94)` ≈ 1 kWt — radiator mass nearly vanishes, but the same physics drains habitats: insulation rules in §3.8. Convectors (§4.5) are cheap dumb fins usable only where an `h` row exists.

**Heat pumps (H-5):** move Q_c from T_c up to T_h at electrical cost
```
P_e = Q_c / COP,   COP = 0.4 · T_c / (T_h − T_c)      (40% of Carnot, real HVAC/cryocooler practice)
Q_h = Q_c + P_e   (rejected at T_h)
```
Example (lunar noon, **T_sink = 330 K** — the lift must be computed against the sink, not against 0 K): lift 25 kWt from 290 K to 420 K: COP = 0.4·290/130 = 0.89 → 28 kWe input, 53 kWt rejected at 420 K; net flux vs the 330 K sink is `0.9σ(420⁴ − 330⁴)` ≈ 0.98 kW/m² per side → **~27 m² double-sided**, versus *zero* possible rejection at 290 K. Beware shallow lifts: at 360 K the net flux against 330 K is only ≈0.25 kW/m² per side (the 0 K-sink value would be 0.86), so 40 kWt would need ~79 m² — *more* than the 35 m² deep-space baseline. Lift well above the sink (400–450 K), or lower the sink with RAD-SHADE. Example (why Venus surface kills): hold a rover interior at 300 K against 737 K with 1 kWt leaking in: reject at 800 K, COP = 0.4·300/500 = 0.24 → **4.2 kWe per kWt of leak**, before the pump's own heat. Venera lasted ~2 h; our Venus surface ops are likewise phase-limited (`10-vehicles.md`).

**The lumped-node thermal network (H-6)** — the implementable core. **Node partitioning rule:** one node per placed base structure/module (07) and one per attachment cluster of parts on a vessel (06 builder), with these always split into their **own** node regardless of clustering: radiator assemblies, battery banks, reactor cores + their coolant loops, and habitat cabins (the §8.5 runaway-cascade and §8.3 freeze gameplay depend on this separation — "separate your banks" must be physically expressible). Structural attachment between two nodes auto-creates a rigid 50 W/K link; every attachment carries a builder toggle **insulated mount** (2 W/K). Docking two vessels joins their networks through a 10 W/K docking-port link (removed on undock). If a network exceeds its node budget (≤40/base, ≤15/vessel, per H-7), the adjacent pair with smallest combined `C` auto-merges until within budget. Each node `i` has heat capacity `C_i` (kJ/K) = `0.9 kJ/(kg·K) × dry mass` (+ contents: water 4.2, atmosphere per 08). Per tick:

```
C_i · dT_i/dt = Q_int,i                                  (H-0 loads, reactors, RTGs, crew, sunlight α·A_s·S_abs)
              + Σ_j G_ij · (T_j − T_i)                   (conductive/coolant links, W/K)
              + h_i · A_c,i · (T_atm − T_i)              (convection if in atmosphere)
              − ε_i σ A_r,i N_s (T_i⁴ − T_sink⁴)         (radiators attached to node)
```
Link conductances `G`: rigid structural joint 50 W/K; insulated mount 2 W/K; pumped fluid loop = catalog kWt rating treated as `G = Q_rated/ΔT_design` with hard cap; MLI-wrapped node: external ε → 0.03 and conductive leak 0.05 W/m²·K (≈1 W/m² in LEO — flight-typical); aerogel surface insulation (Titan/Mars): U = 0.2 W/m²·K per 10 cm.

**Surface-property defaults (H-6a):** unless a catalog row states otherwise, generic external surfaces use **α = 0.25, ε = 0.85** (white thermal paint); solar panels α = 0.90 (P-5); radiators ε = 0.88–0.92 (H-1); MLI as above. `A_s` (sun-projected area) and `A_c` (convective wetted area) are read from the part's `footprint_area` field in the 06/07 part definitions (projected and total wetted values respectively). Deployed sun-tracking radiator wings are assumed flown **edge-on to the Sun — no `α·A_s·S_abs` solar term on radiators**; environmental loading on radiators is already folded into the precomputed H-2 `T_sink` rows, so adding a direct solar term to them would double-count.

**Integration (H-7):** explicit Euler with adaptive substeps,
```
dt_sub ≤ 0.25 · C_i / (Σ_j G_ij + h A_c + 4 ε σ A_r N_s T_i³)     for the stiffest node
```
(linearized-radiation stability bound). Above 1,000× warp the integrator is replaced by a damped-Newton steady-state solve per network (≤10 iterations), with transitions event-scheduled — same architecture as the flow solver in 04/13. Typical base ≤ 40 nodes; vessel ≤ 15 (budget agreed with `13-architecture.md`).

**Operating bands (H-8):** every part declares `[T_min_op, T_max_op, T_survival]`. Outside op band: device offline (electronics 230–320 K op typical; batteries charge ≥273 K T0; crew cabin 292–300 K per 08). Beyond survival: condition damage 1%/h per 10 K excess. Coolant freeze: an unpowered ammonia loop node below 195 K latches `FROZEN` (thaw = 0.5 kWh per kWt of loop rating, heater time).

**Radiator rating convention (H-9):** catalog parts quote `Q_rated` at `T_design` into 0 K sink. In play: `Q = Q_rated · (T_loop⁴ − T_sink⁴)/T_design⁴`, capped at `1.3 × Q_rated` (pump/heat-pipe transport limit). TH-RAD in 06 ("rejects 50 kWt @ 500 K") is this convention.

### 3.6 Heat as a resource

Process-heat consumers in 04 (ovens at 900–1300 K, Sabatier exotherm at 600 K, habitat warmth) may take heat directly from: solar concentrators (P-11), reactor coolant taps (up to 30% of `Q_rej` at `T_rej`), RTG `Q_t`, fuel-cell discharge heat, or thermal stores — saving electric heating watt-for-watt when temperature class suffices (heat at T can serve any process needing ≤ T − 50 K). The Sabatier reaction's gross exotherm is **2.86 kWh_t per kg CH4** (ΔH = −165 kJ/mol CH4, CO2 + 4H2 → CH4 + 2H2O(g)); net of non-recuperated feed-gas preheat to ~600 K (~0.8 kWh_t/kg debit) the plant dumps **~1.8–2.0 kWh_t per kg CH4** into the thermal network — a *load* like any other. (`04-resources-isru.md` owns the recipe and publishes both figures in RX-03: gross exotherm 2.86 kWh_t/kg and **canonical net P_t = −1.8 kWh_t/kg CH4** — the H-0 ledger consumes the net value, never the gross.)

### 3.7 Beamed & relayed power

- **Mirror relay (T2, GRD-HELIO):** Light Bender anchor. Line-of-sight only, lunar surface masts; each mast carries a **40 m² steerable mirror aperture**. Delivery rule: `P_delivered = S(d) · 40 m² · 0.8ⁿ` after `n` bounces (at 1 AU, one bounce: 1361 × 40 × 0.8 ≈ **43.6 kW of beam flux** per mast chain). The delivered beam is deposited as flux onto receiving panels — it enters P-4 as `S` with **cosθ = 1** (the mast steers the beam normal to the receiver) — or onto concentrators/process-heat receivers via P-11. Range ≤ 5 km per mast hop. This is PSR mining without nuclear (§3.8 Moon, §6).
- **Laser link (T3, GRD-LASER):** 100 kWe in → 25 kWe out at receiver (25% end-to-end, studied laser-power-beaming efficiency class), range ≤ 2,000 km (orbit-to-surface). The 75 kW balance is heat at both ends (60/15 split). Niche by design; honest inefficiency.

### 3.8 Per-environment quirk rules

**Mercury.** S = 6.27–14.45 kW/m²; energy is free, survival is thermal. Standard panels auto-tilt per P-5's `S_abs ≤ 5,240 W/m²` condition (≈55° at mean distance, ≈69° at perihelion); OSR panels (T1) run flat. Dayside radiators see T_sink 590 K → industry runs on heat-pump lifts or at night (88 Earth days each). The intended colony pattern: **polar/PSR-rim sites** — perpetual low-angle sun on vertical panels, ~50 K crater sinks next door (radiator paradise; Mercury PSR floor per 03 §4.1), water ice in the PSRs (04). Equatorial bases are a self-imposed hard mode.

**Venus aerostat (48–62 km cloud bands; V-HAVOC design band 50–52 km).** T_atm ≈ 263–366 K, ~17–135 kPa across the bands — Earthlike thermal engineering, convection available. Solar: per-band attenuation from `03-solar-system.md` §4.4.2's canonical f_atm column — **V-Cloud-Low (48–50 km) 0.30, V-HAVOC (50–52 km) 0.45, V-Temperate (52–56 km) 0.55, V-Cloud-Top (56–62 km) 0.70** — entering P-4 as `f_atm` against S = 2,604 W/m² top-of-atmosphere; **two-sided arrays add the canonical +0.15 below-cloud albedo bonus** (S-6a; the cloud deck below bounces flux onto down-facing cells — Venus Bond albedo 0.75 — so a two-sided array flies at `f_atm + 0.15`, e.g. 0.60 effective in V-HAVOC). Super-rotation (S-5b canon: w = 66 m/s, Vega balloon anchor) circumnavigates in ≈6 Earth days → day/night ≈ **3 days light / 3 days dark (≈72 h / 72 h)** regardless of the 116.8-day solar day; batteries/RFC size to ≈72 h of night, not ~1,400 h. Acid film: f_dust analog 0.1%/h on exposed panels, washed by station-keeping pitch maneuver (free, 1/day).

**Mars.** Quirks already in P-8/P-9; plus: convection h 0.5–1.5 helps electronics but frosts radiators at night (no penalty modeled beyond T_sink). Battery heaters are a P0 load 16:00–10:00 local. **Storm input (P-9a — a consumption rule, not a generator):** `03-solar-system.md` S-9 is the **single owner** of the Mars dust-storm generator and dust-season state machine; 09 consumes S-9's per-sector optical depth `τ(t)` and feeds it to P-9. For the reader's convenience, S-9's canonical parameters (any change happens in 03, never here): baseline τ 0.3 (Ls 0°–180°) / 0.5 (Ls 180°–360°); *regional* storms — within Ls 180°–330°, each sector rolls p = 0.004/sol to spawn, τ → 2.0–4.0 over 2 sols, duration U(5, 40) sols, spreading to adjacent sectors at p = 0.15/sol; *global* storm — rolled once per Mars year at Ls = 200°±30° with p = 0.33 (≈1 per 3 Mars years; 2001/2007/2018 anchor), all sectors τ → U(4, 9) over 10 sols, duration U(60, 100) sols, e-fold decay 25 sols. Storms are pre-scheduled events at roll time — onset, peak, and clearing are warp-interrupting events per the §3.1/13 contract. Global storm = the campaign's signature power crisis: τ 4–9 for 60–100 sols, f_atm 0.165 down to the 0.04 floor (P-9; solar never quite dies — diffuse skylight holds the floor — but solar-only bases do). Doctrine: fission baseload + solar surge.

**Moon.** The 354 h night (§3.4 worked problem); lunar-noon sink trap (H-2); PSR mining powered by rim solar + GRD-HELIO or buried Kilopower; thermal wadis keep night rovers alive (§4.4).

**Europa (Jupiter system).** S = 50 W/m² (03 §4.4.9): solar *works* (Juno proof) at 27× the array area per kWe vs 1 AU — viable for probes, not bases. **Radiation tax:** unhardened Electronics-bearing parts take MTBF ×0.05 on Europa's surface; rad-hard build flag costs ×3 Electronics + 15% mass (cross-ref 05 recipes, 11 unlock). Solar degrades per P-7 Jupiter rates. Crewed ops need ≥3 m ice/Regolith burial (dose model in 08). Eclipse: Europa passes through Jupiter's shadow ~2.9 h per 85.2 h orbit (f_ecl = 0.034, 03 canon). Practical doctrine: Kilopower under ice berms.

**Titan.** TOA flux 14.8 W/m² (1.09% of Earth); the haze passes only ~10% to the surface → ≤1.5 W/m² diffuse, ~0.1% of Earth-surface noon sun (Huygens-confirmed gloom). Solar is dead; nuclear is mandatory. The flip side: 5.3 kg/m³ of 94 K nitrogen makes every fin a superb radiator (H-3) — *and every habitat wall a 1 kW/m² leak if uninsulated* (h=5 × ΔT≈200 K). Insulation rule: habitats/vehicles declare aerogel thickness; U = 0.2 W/m²·K per 10 cm; waste heat becomes the heating budget (an 8-crew hab's 26 kWt of internal waste heat comfortably heats 300 m² of 10 cm-aerogel shell losing 12 kWt). RTG/reactor waste heat is Titan's most valuable byproduct. Wind turbines are NOT modeled v1 (near-surface winds ~0.3 m/s, too weak — honest omission; see §9).

**Deep space / belt (Ceres 178 W/m²).** Solar farms get big but stay viable through the main belt (Dawn flew solar at Ceres); beyond ~6 AU fission/RTG only. EP freighters (05's Drayage, 300 kWe array) thrust-derate with 1/d² per 06's planner.

---

## 4. Content Catalog

All masses are launch-qualified hardware; ISRU-manufactured equivalents may be 2–4× heavier per 05 §"in-situ derate" but cost local resources. IDs marked (=PW-xx) are the canonical stats behind `06-ships-stations.md` builder stubs.

### 4.1 Solar generators

| ID | Name | Tier | Mass | Area | η_cell | P_e BOL @1 AU | W/kg @1 AU | Notes / anchor |
|---|---|---|---|---|---|---|---|---|
| SOL-RW (=PW-SA-R) | Rigid solar wing | T0 | 0.16 t | 12.5 m² | 0.295 | 5.0 kWe | 31 | ISS legacy class; 0.8 kWe stowed-safe |
| SOL-RO (=PW-SA-RO) | Roll-out array | T1 | 0.25 t | 46 m² | 0.32 | 20 kWe | 80 | ROSA/iROSA; needs 0.02 kWe deploy motor; T1 per 11's PW-01 node (and η 0.32 is the T1 cell tier, §3.2) |
| SOL-OSR | Mercury-rated wing | T1 | 0.20 t | 12.5 m² | 0.295 (on the 1/3 active-cell area) | 1.7 kWe | 8.5 | 2/3 OSR mirror area (only 1/3 cells), 575 K limit; the payoff: runs sun-normal at Mercury — ~11 kWe at mean distance before the P-6 temperature derate; MESSENGER |
| SOL-BLK | Thin-film blanket | T2 | 0.10 t | 59 m² | 0.25 | 20 kWe | 200 | studied 200–300 W/kg class; fragile (½ MMOD tolerance) |
| SOL-FARM | Surface farm unit, tracking | T1 | 1.2 t | 100 m² | 0.30 | 40.8 kWe noon @1 AU (≈15.6 kWe @Mars mean-distance noon: τ 0.5 → f_atm 0.80 per P-9/03 S-9, f_temp 1.11, ex-dust — reproducible from P-4) | — | 12 kg/m² ground mount incl. tracker (0.1 kWe) |
| SOL-FARM-F | Surface farm unit, fixed | T0 | 0.8 t | 100 m² | 0.30 | ⟨cos⟩=0.637 applies | — | the cheap hectare-filler |
| SOL-CONC | Concentrator mirror | T1 | 0.15 t | 100 m² | — | **116 kWt** @1 AU (heat only) | — | P-11; feeds 04 thermal recipes, ≤1,100 K |
| SOL-EDS | Electrodynamic dust shield add-on | T2 | +2 kg/100 m² | — | — | holds f_dust ≥ 0.95 @ 0.1 kWe/100 m² | — | NASA KSC EDS, flown (Blue Ghost 2025); T2 per 11's PW-06 node and 07's EDS surfaces |

Output everywhere = P-4 with the body's live `S(d)` and environment factors. Efficiency tier upgrades (T1 0.32, T2 0.36 cells) are research-gated retrofits (Silicon + Electronics per 05).

### 4.2 Radioisotope generators

| ID | Name | Tier | Mass | P_e BOL | Q_t BOL | Pu238 (PuO2 kg) | Decay (net %/yr) | Anchor |
|---|---|---|---|---|---|---|---|---|
| NUK-RTG-M (=PW-RTG) | MMRTG | T0 | 45 kg | 110 We | 2.0 kWt | 4.8 | 3.8 | Curiosity/Perseverance |
| NUK-RTG-G | GPHS-RTG | T0 | 57 kg | 300 We | 4.4 kWt | 10.9 | 1.6 | Cassini/New Horizons; production-limited (12 owns Pu238 market) |
| NUK-RTG-S | Stirling RIG | T1 | 32 kg | 130 We | 0.5 kWt | 1.2 | 1.3 | ASRG (built, canceled 2013) |
| NUK-RHU | Radioisotope heater unit | T0 | 0.04 kg | — | 1 Wt | 0.0027 | 0.79 | flown RHUs; rover/instrument warmth |

### 4.3 Fission & fusion

| ID | Name | Tier | Mass (incl. shield+radiators as noted) | P_e | η_cv | Q_rej @ T_rej | Core (resource) | Life | Anchor |
|---|---|---|---|---|---|---|---|---|---|
| NUK-KP1 (=PW-KP1) | Kilopower-1 | T2 | 0.40 t (instr. shield, radiator incl.) | 1 kWe | 0.23 | 3.3 kWt @ 400 K | 30 kg Uranium | 12 FPY | Kilopower/KRUSTY (ground-tested 2018, never flown → T2 per tier doctrine; unlocked by 11's PW-04 node) |
| NUK-KP10 (=PW-KP10) | Kilopower-10 | T2 | 1.5 t (instr. shield, 25 m² radiator incl.) | 10 kWe | 0.23 | 33 kWt @ 400 K | 45 kg Uranium | 12 FPY | Kilopower 10 kWe design (Gibson/Mason) |
| NUK-FSP (=PW-FSP) | Surface fission unit | T2 | 9.0 t (crew shield + radiators incl.; −1.5 t if Regolith-buried instead) | 100 kWe | 0.30 | 233 kWt @ 450 K | 200 kg Uranium | 10 FPY | NASA/DOE FSP 40 kWe ref, scaled ~90 kg/kWe (conservative vs SP-100's 46) |
| NUK-MSR | Thorium molten-salt plant | T3 | 28 t (surface only, building per 07) | 500 kWe | 0.35 | 0.93 MWt @ 500 K | Thorium feed 0.70 kg/MWt-FPY (≈1.0 kg/yr at full power; P-16) | online refuel | MSRE (ran 1965–69) + ORNL Th-cycle studies |
| NUK-NEP (=PW-NEP) | NEP reactor module | T3 | 35 t (incl. 144 m² 800 K radiator + instr. shield) | 2,000 kWe | 0.25 | 6 MWt @ 800 K | 1.2 t Uranium | 10 FPY | JIMO/Prometheus class — **game-extrapolated 10× beyond the 200 kWe design**, 17.5 kg/kWe within study range |
| NUK-FUS | Fusion power unit [SPECULATIVE] | T4 | 60 t | 10,000 kWe | 0.60 direct | 6.7 MWt @ 900 K (100 m²) | 1 kg He3 + 0.67 kg Hydrogen (physically deuterium) per 5.3 MW-yr gross (≈28% burnup; P-17) | 20 FPY | PFRC/DFD studies; we use 6 kg/kWe vs claimed ~1 |

All reactors obey P-13–P-15 (load-following, decay heat, shields/burial).

### 4.4 Storage

| ID | Name | Tier | Mass | Capacity | Max chg/dis | Notes |
|---|---|---|---|---|---|---|
| STO-LI-1 | Li-ion pack | T0 | 100 kg | 15 kWh | 15/30 kW | stats per §3.4 row; heater 50 W below 273 K (P0) |
| STO-LI-10 | Li-ion bank | T0 | 1.0 t | 150 kWh | 150/300 kW | base-scale unit; heater 500 W below 273 K (P0); min charge T 273 K |
| STO-SS-10 | Solid-state bank | T1 | 1.0 t | 250 kWh | 250/375 kW | heater 250 W below 253 K (P0); min charge T 253 K |
| STO-LS-10 | Li-S bank | T2 | 1.0 t | 350 kWh | 200/350 kW | 800-cycle life; heater 500 W below 263 K (P0); min charge T 263 K |
| STO-FW | Flywheel set | T1 | 0.5 t | 25 kWh | 100/100 kW | LEO eclipse cycler; 2%/h self-drain; no charge-temperature limit (no heater) |
| PW-FC | Fuel-cell stack | T0 | 118 kg | — | 7 kWe cont. / 12 peak | Shuttle PC17C; consumes Hydrogen+Oxygen → Water per P-18 |
| STO-RFC | RFC skid (stack+electrolyzer+plumbing, ex-tankage) | T1 | 1.1 t | sized by tanked reactants (2.0 kWh_e/kg) | 14 kWe out / 30 kWe in | lunar-night workhorse (§3.4 worked problem) |
| STO-TS | Molten-salt heat store | T2 | 2.0 t | 200 kWh_t (550→800 K) | 100 kWt | buffers SOL-CONC for night-running ovens |
| STO-WADI | Thermal wadi | T1 | 20 t sintered Regolith (ISRU-built, ~0 launched) | 1,200 kWh_t (95→380 K; = 20 t × 60 Wh_t/kg per §3.4) | 2 kWt bleed | parks a rover warm through lunar night; NASA thermal-wadi concept |

### 4.5 Radiators, convectors & thermal transport

| ID | Name | Tier | T_design | Mass | Area | Q_rated (0 K sink) | kg/kW | Notes |
|---|---|---|---|---|---|---|---|---|
| RAD-BM | Body-mount panel | T0 | 300 K | 8 kg/m² | per m² | 0.37 kWt/m² (1-sided; effective ε 0.81 after structure view-factor blockage — clear-field H-1 at ε 0.90 would give 0.41) | 22 | no deploy risk; doubles as MMOD skin |
| RAD-HAB | Habitat wing | T1 | 290 K | 0.60 t | 50 m² (2-sided) | 36 kWt | 17 | the big sail; pumped water loop |
| TH-RAD | Deployable mid-temp radiator | T0/T1 | 500 K | 1.2 t | 12 m² (2-sided) | 50 kWt (loop-capped; 76 radiative) | 24 | =06 stub; ISS-HRS-derived mechanism, pumped water |
| RAD-KP | Heat-pipe radiator panel | T2 | 400 K | 5 kg/m² | per m² | 2.6 kWt/m² (2-sided) | 1.9 | Ti-H2O heat pipes, Kilopower style |
| RAD-HT | Refractory radiator | T3 | 800 K | 10 kg/m² | per m² | 41.8 kWt/m² (2-sided) | 0.24 | C-C/Na heat pipes; NEP class |
| RAD-LDR | Liquid-droplet radiator | T3 | 500 K | 2 kg/m²-equiv | per m² | 6.4 kWt/m² | 0.31 | 1980s demos; droplet loss 0.01%/h of fluid (Polymers ledger) |
| RAD-SHADE | Radiator shade kit | T1 | — | +20% of host radiator | — | lowers surface T_sink by 100 K | — | lunar-noon fix (H-2) |
| RAD-CONV | Atmospheric convector | T2 | any | 0.3 t | 20 m² fin | h·A·ΔT per H-3 (Titan calm: 20 kWt @ ΔT 200 K) | — | atmosphere-only |
| THX-HP | Heat-pipe strap | T0 | ≤320 K | 0.5 kg/m | — | 1 kWt per line, ≤10 m | — | ammonia axial-groove |
| THX-PL | Pumped loop | T1 | class: NH3 200–320 K / H2O 280–500 K / NaK 500–900 K (T3) | 50 kg + 0.3 kg/m | — | 25 kWt, 0.15 kWe pump | — | freeze rule H-8 |
| THX-HPMP | Heat pump | T1 | — | 0.2 t | — | lifts 10 kWt per H-5 COP | — | lunar noon, Venus, Mercury |

### 4.6 Grid hardware

| ID | Name | Tier | Mass | Rating | Loss | Notes |
|---|---|---|---|---|---|---|
| GRD-SB-S | Switchboard S | T0 | 80 kg | 30 kW | 1% → heat | 4 ports; vessel bus built-in equivalent |
| GRD-SB-M | Switchboard M | T1 | 0.4 t | 300 kW | 1% | 8 ports, remote-switchable |
| GRD-SB-L | Switchboard L | T2 | 2.0 t | 3 MW | 0.8% | base backbone |
| GRD-CAB-LV | Cable, 600 V | T0 | 0.5 kg/m | 20 kW | 2.2%/km @ rated | Aluminum conductor; loss ∝ (P/P_r)² |
| GRD-CAB-MV | Cable, 3 kV | T2 | 1.0 kg/m | 200 kW | 0.45%/km | |
| GRD-CAB-HV | Line, 10 kV | T3 | 2.5 kg/m | 2 MW | 0.16%/km | belt/megabase backbone |
| GRD-SHUNT | Shunt resistor bank | T0 | 0.25 t | dumps 100 kW @ 600 K | — | 7.6 m² integral radiator; the surplus sink of last resort |
| GRD-HELIO | Mirror relay mast | T2 | 0.3 t | 40 m² aperture; delivers S(d)·40·0.8ⁿ W after n bounces (≈43.6 kW @1 AU, 1 bounce), ≤5 km hop | 20%/bounce scattered (not a local heat load) | Light Bender anchor; lunar LOS only; delivery rule §3.7 (cosθ = 1, mast-steered) |
| GRD-LASER | Laser power link (pair) | T3 | 1.5 t TX + 0.8 t RX | 100 kWe in → 25 kWe out, ≤2,000 km | 75 kW as heat (60 TX / 15 RX) | studied beaming class |

### 4.7 Conversion reference (used by P-13 and 04 recipes)

| Converter | η | Reject temp | Anchor |
|---|---|---|---|
| Thermoelectric (SiGe/PbTe) | 0.065 | 500–600 K | GPHS-RTG/MMRTG |
| Stirling, free-piston | 0.23–0.26 | 400 K | KRUSTY/ASRG |
| Brayton, recuperated | 0.30–0.35 | 450–500 K | FSP/JIMO studies |
| Brayton, high-reject | 0.25 | 800 K | NEP trade (small radiators) |
| PV cell tiers | 0.295/0.32/0.36 | — | XTJ/IMM/6J-lab |
| Fusion direct conversion [SPECULATIVE] | 0.60 | 900 K | PFRC papers |

---

## 5. Player Interaction & UI

- **Power ledger panel** (per grid): stacked bar of generation by source vs consumption by tier; storage SoC strip with **time-to-empty / time-to-full** computed analytically (the same prediction the warp scheduler uses — UI never lies relative to sim). A Sankey view shows kWe flows source→tier and the mandatory heat column (H-0 makes every Sankey end in radiators — the doctrine made visible).
- **Thermal overlay** (base/vessel view): nodes tinted by temperature on a 90–1000 K color ramp; radiators show % utilization; links show flow direction. A "heat debt" badge appears on any node trending above `T_max_op` with ETA — the thermal equivalent of a delta-v readout.
- **Night/eclipse planner**: for the selected site/orbit, plots S(d)·daylight over the next N days (drawing eclipse events from 01), overlays storage depletion under current loads, and flags the first brownout tier and time. This is the tool the §3.4 lunar worked problem is played through.
- **Brownout console**: when shedding occurs, an ordered list shows what dropped and why; players can re-pin tiers, set storage reserve floors, and define **load-shed scripts** ("storm mode": P2 off, electrolysis off, heaters max).
- **Radiator sizing helper** in the builder (06 editor): select parts → live Q_total at design temps vs installed rejection at the destination body's worst-case `T_sink`; red/green margin bar. Same helper in base-building (07).
- **Reactor console**: throttle, SCRAM button, decay-heat gauge post-shutdown, core-life bar, shield-cone visualization (parts/crew inside the unshielded zone are flagged with dose/MTBF warnings).
- **Alarms**: advisory (storage < 40%), warning (< reserve floor, node within 20 K of limit), master (P0 at risk, coolant freeze, reactor over-temp). Alarms generate warp-stop events per player settings (13).
- **Warp behavior**: all curves (decay P-12, degradation P-7, dust P-8, burnup P-13) integrate analytically; the player can warp a year and the ledgers are exact, with scheduled events (storm onset, battery-empty, core end-of-life) interrupting warp.

---

## 6. Progression Hooks

| Tier | Act | Power/thermal unlocks (research tree details in `11-research-tech.md`) |
|---|---|---|
| T0 | Act 1 (Earth+LEO) | SOL-RW, SOL-FARM-F, STO-LI, PW-FC, NUK-RTG-M/G (Pu238 purchase-limited per 12), RAD-BM, TH-RAD, GRD-SB-S, GRD-CAB-LV, GRD-SHUNT. Lessons: eclipse cycling (P-10), the first Sankey, EP power-limited thrust. |
| T1 | Act 1–2 (Moon) | SOL-RO (11's PW-01), NUK-RTG-S, STO-SS, STO-RFC, STO-FW, STO-WADI, SOL-OSR, SOL-CONC, RAD-HAB, RAD-SHADE, THX-PL, THX-HPMP, GRD-SB-M. **The lunar night arc (§3.4) is the Act-2 spine: batteries → RFC from ISRU water → first fission (the T2 Kilopower research finishing the act).** |
| T2 | Act 2–4 (Mars, belt, Venus) | NUK-KP1 (11's PW-04), NUK-KP10, NUK-FSP, SOL-BLK, SOL-EDS (11's PW-06), STO-LS, STO-TS, RAD-KP, RAD-CONV, GRD-SB-L, GRD-CAB-MV, GRD-HELIO, T2 cells (0.36), rad-hard build flag. Mars storm doctrine; Venus aerostat power; PSR mirror mining. |
| T3 | Act 4–5 (outer planets) | NUK-MSR (Thorium economy), NUK-NEP (2 MWe — enables MPD/VASIMR freighters in 02), RAD-HT, RAD-LDR, NaK loops, GRD-LASER, GRD-CAB-HV, Pu238 breeding line (04/05). Titan insulation engineering; Europa rad-tax management. |
| T4 | Endgame | [SPECULATIVE] NUK-FUS; He3 logistics (03/04); fusion-powered megaprojects (mass drivers in 05, interstellar precursor in 12). Radiator Doctrine persists at 900 K. |

Milestone beats: first night survived (Act 1 tutorial, LEO eclipse); first lunar night survived (Act 2 capstone); first fission start-up (Act 2/3 gate — regulatory/cost gates owned by 12); first MW grid (Act 4); first fusion ignition (endgame).

---

## 7. Cross-System Interfaces

**Consumes:**
- `03-solar-system.md`: body ephemerides `d(t)` (AU), rotation/solar-day periods, atmosphere tables (P, T, density → h values H-3), surface temperatures and T_sink table (H-2), Jupiter radiation-zone map (Europa tax), PSR locations, the Venus §4.4.2 per-band f_atm column and +0.15 albedo bonus (§3.8), and the complete Mars dust system S-9 — storm generator, per-sector τ(t), the f_dust attenuation fit `max(0.04, exp(−0.45·τ))`, and panel-soiling rates — **all owned by 03**; §3.8 P-9a and P-8/P-9 only consume it.
- `01-orbital-mechanics.md`: shadow entry/exit anomalies for eclipse events (P-10), orbit geometry for sun-pointing/cosθ.
- `02-propulsion.md`: EP electrical demands per string (6.9–250 kWe) and their radiator-rejected waste-heat fractions (02 §3.9 canon: **gridded ion and Hall 10% of P_in, VASIMR 15%, MPD 30%** — PPU + thruster-body heat per the H-0 accounting; the rest of the non-jet power leaves in the plume); ZBO cryocooler draws (0.75/2.0 kWe) and reject loads; bimodal NTR idle export (+25 kWe); DFD-5 1 MWe export; tank heaters 50 W/t.
- `04-resources-isru.md`: Uranium/Thorium/Pu238/He3 resource chains; recipe `P_e`/`P_t` demands and exotherms (the canonical kWh/kg cross-checks: Mars methalox 7.1 kWh/kg → 59 kWe example reproduced in §3.4); electrolysis 50 kWh/kg H2 (RFC charge leg).
- `05-industry-logistics.md`: factory demand tables and `heat_fraction = 0.95`; manufacturing recipes for all §4 parts; in-situ mass derates for locally-built radiators/arrays.
- `06-ships-stations.md`: part slotting, deployment states, MMOD penetration rolls against radiators/arrays; builder stubs PW-*/TH-RAD (stats canonical here).
- `08-life-support-crew.md`: crew metabolic heat (100 Wt each), cabin temperature band, ECLSS loads as P0 consumers, crew dose limits for shield rule P-15.

**Provides:**
- To `04`/`05`/`07`/`10`: delivered grid power by tier and process heat by temperature class at every site (their `utilization` inputs); brownout signals that scale plant throughput.
- To `06`/`07`: radiator/array/reactor performance curves (H-1, H-9, P-4, P-13), thermal node parameters, operating bands H-8 for every part.
- To `08`: habitat thermal balance (cabin node temperature), heater capacity, survival-time-to-freeze in failures, and the reactor dose-rate field `D(r)` (P-15) that 08 integrates against its crew dose model and limits.
- To `10`: vehicle battery/RTG/wadi night-survival model; Venus/Mercury thermal endurance clocks (H-5).
- To `11`: the tier unlock list in §6.
- To `12`: capital/operating cost drivers (Pu238 scarcity, reactor licensing beats, power as a sellable station service).
- To `13`: the two network solvers (P-1 ledger, H-6/H-7 lumped thermal), analytic-integration + event-scheduling contracts, node-count budgets.

---

## 8. Failure Modes & Edge Cases

1. **Brownout cascade (the designed failure).** Deficit sheds P4→P2 per P-1 with 300 s latch + staggered retry. If P1 sheds: ZBO cryocoolers stop → boiloff begins (02 owns rates) — a *resource* leak, not an instant disaster. If P0 cannot be served: `EMERGENCY_POWER` event — 13 stops warp; ECLSS battery-backup grace period (08 owns asphyxiation clock). Design intent: a Mars global storm produces a week of escalating, survivable decisions, not a cut to black.
2. **Radiator loss.** MMOD penetration (06 roll) on a pumped-loop radiator: coolant leak, −10% rating per cm² hole per hour until isolated (auto-isolation valves T1+); heat-pipe panels degrade gracefully (lose only struck pipes, −5% per hit). Lost rejection → node temps climb per H-6 → devices hit `T_max_op` and shut down in physics order, not script order.
3. **Coolant freeze.** Unpowered/shaded ammonia loop < 195 K latches FROZEN (H-8); thaw costs heater energy and time. Classic trap: SCRAMing a reactor at lunar night and losing pump power freezes the very loop needed to restart — players learn to keep a battery on the P1 pump bus.
4. **Reactor faults.** Over-temp auto-SCRAM (coolant node > T_rej + 150 K); decay heat per P-14 must still be rejected (small cores: passive; ≥1 MWt: 2% radiator reserve or CORE_DAMAGE). No civilian-killing meltdowns — Kilopower-class physics is genuinely benign and we model that honestly; the punishment is capability loss and core-swap logistics, plus dose zones if shields are damaged (08). Restart after a SCRAM follows the P-13 restart rule: player command, coolant node back below `T_rej`, coolant pump powered, ramp from 5% at the 1%/s slew limit.
5. **Battery thermal runaway.** Li-family node > 400 K: pack destroyed, releases stored kWh + 0.3 kWh/kg chemical as a heat spike into its node over 10 min (can cascade to neighbors via G links — separate your banks). Li-S is the touchiest (×1.5 spike). Flywheels instead shed rotor: instant loss of stored kWh, 1% chance of structural damage to the host module.
6. **Cold batteries.** Charging below 273 K (T0 chemistry) is refused by the BMS; if heaters are shed (they're P0 for a reason), the bank is bricked at −1% capacity per cold-charge attempt.
7. **Dust death spiral (Mars).** Storm cuts solar (P-8/P-9) → shedding hits EDS and heaters → dust accumulates faster and batteries freeze. The storm-mode load script (§5) and fission baseload are the designed outs. This spiral is intentional and survivable with preparation — it is the Act-3 boss fight.
8. **Lunar-noon overheat.** Players who size habitat radiators for deep-space sinks meet H-2's 330 K lunar noon: rejection hits zero, cabin climbs ~1–3 K/h (26 kWt into ~30 MJ/K of habitat). Fixes: RAD-SHADE, heat pump lift, or pre-noon industrial curfew. The night/eclipse planner forecasts it.
9. **Single-point grid failures.** A failed switchboard (MTBF per 05 maintenance model; Europa tax applies) isolates its segment: islands run on local storage per P-1. Cables can be severed by rover collisions/landing debris (10/06 events). Ring topologies and spare switchboards are pure player skill expression.
10. **Surplus with nowhere to go.** Curtailable sources throttle free; RTG heat is always-on by physics; a grid that loses its shunt AND storage while running non-curtailable surplus pushes the excess into the source nodes as heat (overheat path) — build shunts.
11. **Beamed-power edge cases.** GRD-LASER TX without RX lock auto-inhibits (no death rays in v1 — see §9); GRD-HELIO bounces require LOS recheck on terrain edits (07).
12. **Degenerate warp.** All §3 curves are closed-form in t; the steady-state thermal solve (H-7) prevents stiff-node explosions at 100,000×. Events (storm onset, eclipse, SoC zero-crossing, core EOL) are pre-scheduled so nothing is missed between frames — contract with 13.

---

## 9. Open Questions

1. **Within-tier shedding granularity:** binary shed with latch (current P-1) vs continuous `utilization` scaling for *all* devices (04 already supports it for plants). Continuous is smoother but hides crises; binary is legible. Playtest call.
2. **Should cables/switchboards carry an AC/DC or voltage-class distinction beyond mass/loss?** Current model says no (kW ledger only); 05's "pulse-power" note for mass drivers may force a capacitor-bank part and a surge-rating axis in v1.1.
3. **Titan wind power:** near-surface winds (~0.3–1 m/s, Huygens) make turbines marginal but the dense atmosphere (5.3 kg/m³) partially compensates (P ∝ ρv³). Excluded from v1; revisit if Titan acts need a non-nuclear flavor option.
4. **Lunar noon sink values:** the H-2 single-number sinks are deliberate simplifications of view-factor geometry. Is one `T_sink` per (body, day/night, shaded-flag) sufficient, or do vertical vs horizontal radiator orientations need separate rows? (Cost: one more parameter per part placement.)
5. **Liquid droplet radiator art/feel** in clean 2D vector style — droplet sheets may read as "magic"; if unconvincing visually, slide RAD-LDR to T4 or cut.
6. **Pu238 economy depth:** is the Oak Ridge-style purchase trickle (12) + T3 breeding line (04/05) enough of an arc, or does Pu238 scarcity need a dedicated contract storyline? Coordinate with 12.
7. **Mercury polar sites** may trivialize the "overheating planet" identity (perpetual terminator sun + 40 K sinks). Possible friction: PSR-rim real estate as a scarce site resource (03 owns site definitions).
8. **Laser-link griefing/exploits:** can players beam power to dodge the cable-mass cost everywhere? Current 25% efficiency + range cap seems sufficient tax; verify in economy balance (12).
9. **RESOLVED (DECISIONS D27 — DEFAULTED).** The ≤40 nodes/base budget stands; hierarchical thermal aggregation is deferred until a real Act 5 megabase exceeds the budget — overturn only with profiling data, with 13, at the Phase 5 gate.
10. **RESOLVED (DECISIONS E).** Stays 6 kg/kWe as written ([PLAYTEST] balance placeholder); He3/fusion pacing is revisited at the Phase 6 gate together with this knob — any change documented as [SPECULATIVE] tuning, not physics.
