# 02 — Propulsion Systems

Domain spec for every device that produces thrust or stores/moves propellant: chemical rockets (solid, hypergolic, kerolox, hydrolox, methalox), nuclear-thermal rockets, electric propulsion, solar sails, RCS, tanks, boiloff, orbital depots and propellant transfer, plus the reliability/wear model and the builder math (rocket equation, TWR rules). Trajectory integration itself is owned by `01-orbital-mechanics.md`; this document provides the thrust, mass-flow, and Isp inputs that integrator consumes.

## 1. Overview

Propulsion is the game's primary economy sink and the player's primary lever against distance. The design pillars:

1. **Real numbers, real anchors.** Every engine in the catalog is a named real engine or a named real design study, with published thrust/Isp/mass. Where SpaceX-style numbers are still evolving in the real world, values are tagged `[est]`.
2. **Propellant logistics IS the gameplay.** Delta-v is bought with propellant mass; propellant mass is bought with ISRU chains (`04-resources-isru.md`), boiloff management, depots, and transfer infrastructure. The rocket equation is shown raw in the UI — the game never hides the logarithm.
3. **The power–thrust–Isp triangle.** Chemical engines are power-rich and Isp-poor; electric engines invert that. The single coupling formula `T = 2·η·P / (g0·Isp)` governs all electric propulsion and forces the player into `09-power-thermal.md`'s domain for every high-Isp ship.
4. **Tiered honesty.** T0 is flying hardware (2049 baseline). T1 is engineering-complete derivatives (methalox reuse, cryo depots). T2 is studied-and-credible (NTR, LANTR, large ISRU landers). T3 is lab-demonstrated (100 kW Hall, MPD, VASIMR, big sails). T4 is `[SPECULATIVE]` physics-sound endgame (fusion torch, fission-fragment) and says so on the tin.
5. **Entropy is an antagonist.** Cryogens boil, engines wear out, igniters fail, NTO freezes. Each of these is a explicit modeled rule, not flavor text.

Act mapping at a glance: Act 1 flies kerolox/hydrolox/solids and learns reuse + depots (T0–T1). Act 2 runs methalox and lunar-LOX LANTR logistics (T1–T2). Act 3 is the NTR + ISRU methalox era (T2). Act 4 belt/Venus runs high-power Hall and sails (T2–T3). Act 5 runs MPD/VASIMR megafreighters (T3–T4). Endgame builds the Daedalus-class interstellar precursor (T4).

## 2. Real-World Grounding

### 2.1 Chemical rockets

- **Solids**: Star 48B kick motor (Thiokol/Northrop Grumman; 66 kN, Isp 286 s vac, 2,137 kg gross / 126 kg burnout, 87 s burn) and GEM 63 strap-on (Atlas V; 1,663 kN max thrust, 44,087 kg propellant, 94 s burn; the stretched, higher-thrust GEM 63XL is the Vulcan Centaur variant). APCP (ammonium perchlorate composite propellant) chemistry. Simple, dense, storable for years, cannot be throttled or shut down.
- **Hypergolics (NTO/MMH)**: Space Shuttle OMS engine AJ10-190 (26.7 kN, Isp 316 s, 118 kg), Apollo Service Propulsion System AJ10-137 (91 kN, Isp 314 s, 293 kg; real SPS burned NTO/Aerozine-50 — the game simplifies all hypergolics to the NTO/MMH pair at O/F 1.65, the OMS ratio). SpaceX Draco (400 N, Isp 300 s) and SuperDraco (71 kN, deep throttle) for RCS and landers. Hypergolics ignite on contact: no igniter, near-unlimited restarts, storable at room temperature — but NTO freezes at 262 K and the pair is toxic and lower-Isp.
- **Kerolox**: SpaceX Merlin 1D (845 kN SL / 914 kN vac, Isp 282 s SL / 311 s vac, ~470 kg, gas-generator cycle, T/W ≈ 180) and Merlin Vacuum (981 kN, Isp 348 s). O/F ≈ 2.36. RP-1 is dense and storable but cokes engines and cannot be made off-Earth cheaply (no convenient ISRU route) — which is exactly why the game pushes players off kerolox after Act 1.
- **Hydrolox**: the RL10 family — best flying vacuum Isp of any chemical engine (RL10B-2 reached 465.5 s on Delta IV; current C-variants fly ≈450–454 s); the game's H-102 uses RL10C-1 numbers (101.8 kN, Isp 449.7 s, 190 kg, expander cycle); CECE (RL10-derivative Common Extensible Cryogenic Engine, deep throttle demonstrated to 5.9% of rated thrust); RS-25/SSME (1,860 kN SL / 2,279 kN vac, Isp 366/452 s, 3,177 kg, staged combustion, T/W ≈ 73, originally certified for 7.5 h / 55 starts). O/F game-standard 6.0 (real RL10 5.5–5.88, RS-25 6.03). LH2 at 70.8 kg/m³ makes tanks enormous and boiloff brutal — modeled.
- **Methalox**: SpaceX Raptor 2 (full-flow staged combustion; 230 tf = 2,256 kN SL, Isp 327 s SL / 347 s vac, 1,630 kg — figures from SpaceX's published Raptor comparison), Raptor Vacuum (≈2,530 kN, Isp ≈380 s `[est]`). O/F game-standard 3.6 (Raptor flies ≈3.5–3.8). Methane is the ISRU propellant: Sabatier from CO2 + H2 (Mars, anywhere with carbon and water) — see `04-resources-isru.md`. NASA Project Morpheus flew a 24 kN pressure-fed methalox deep-throttle lander engine — our small-lander anchor.

**Pressure-fed vs pump-fed** (this tradeoff is a real game mechanic, §3.16):

| Property | Pressure-fed | Pump-fed |
|---|---|---|
| Real anchors | AJ10, Draco, SuperDraco, Morpheus HD | Merlin, RL10, RS-25, Raptor |
| Chamber pressure | ≈0.7–2.4 MPa typical (AJ10, Draco, Morpheus); SuperDraco is an outlier at ~6.9 MPa | ≈2.4–30 MPa (RL10 2.4–4.4, Merlin 1D 9.7, RS-25 20.6, Raptor ~30) |
| Isp | 10–25 s lower per propellant pair | best achievable |
| Tank mass | heavy (tanks hold 1.5–3 MPa): tankage ×1.6 | light, low-pressure tanks |
| Restart | effectively unlimited, instant | igniter + ullage settling + (cryo) chilldown |
| Throttle | deep (to ~20% or lower) | typically limited (40–67%) unless special (CECE) |
| Reliability | highest (fewest moving parts) | lower; turbopumps dominate failure stats |
| Cost class | low | high |

### 2.2 Nuclear-thermal rockets (NTR)

A solid-core fission reactor heats a working fluid (ideally hydrogen, lowest molar mass) to ~2,700–2,900 K and expands it through a nozzle. Isp scales as √(T_chamber / M_molar): hydrogen gives ~850–950 s, double the best chemical. Anchors:

- **NERVA XE'** (1969 ground test): 246.7 kN, Isp 841 s ideal vacuum (710 s at rated test conditions), 18,144 kg, demonstrated **24 start/restart cycles** and 28 min accumulated burn. Engineering-complete in 1972; cancelled for budget, not physics.
- **SNRE** (Small Nuclear Rocket Engine, LANL/NASA Glenn Schnitzler & Borowski design studies): 16.5 klbf ≈ 73 kN, Isp ~900 s, 367 MWt reactor, engine ≈2,400 kg with internal shield — the modern reference design.
- **DRACO** (NASA/DARPA Demonstration Rocket for Agile Cislunar Operations, 2023–2025 program; HALEU fuel): our T2 unlock narrative assumes a DRACO-like flight demo happened before 2049.
- **LANTR** (LOX-Augmented NTR, Borowski/NASA studies): inject LOX into the nozzle as an afterburner. At LOX/H2 mixture ratio 3.0 the 1994 LANTR/LUNOX study tables give Isp ≈ 647 s (down from 941 s at MR 0; the ≈607–610 s figure belongs to MR ≈ 4) and ≈2.7× thrust (engine T/W rises 3.0 → 8.2) — a perfect lunar-LOX synergy, modeled as a mode switch (game values 645 s, ×2.75; §3.10).
- Shadow shield: the reactor is shielded only in a cone toward the crew; mass outside the cone gets a promptly lethal dose (~10⁴ Sv/h class at 25 m for an SNRE-class core at full power — §3.10 derivation). Post-shutdown decay heat requires continued propellant flow (real mission studies budget 1–3% extra H2 for cooldown).

### 2.3 Electric propulsion

Thrust is power-starved by physics: jet power P_jet = T·g0·Isp/2, so at fixed power, thrust falls as Isp rises. Anchors with flight/lab data:

- **NSTAR** (Deep Space 1, Dawn): gridded ion, 2.3 kW, 92 mN, Isp 3,120 s, total efficiency ≈0.61; Extended Life Test ran 30,352 h and processed 235 kg xenon.
- **NEXT** (NASA, flown on DART): 6.9 kW, 236 mN, Isp 4,190 s, η ≈ 0.70; life test 51,000+ h, 918 kg throughput.
- **SPT-100** (Fakel, hundreds flown): Hall thruster, 1.35 kW, 83 mN, Isp 1,600 s, η ≈ 0.48.
- **AEPS/HERMeS** (NASA/Aerojet, Gateway PPE): 12.5 kW Hall, ~590 mN, Isp 2,600–2,800 s, thruster efficiency ~67% (game uses η = 0.65 system incl. PPU).
- **X3** (Univ. of Michigan/AFRL nested-channel Hall): demonstrated 5.4 N at 102 kW in 2017 — lab-demonstrated, hence T3.
- **MPD** (magnetoplasmadynamic): lab-demonstrated at 100s of kW (NASA Lewis, Moscow Aviation Institute lithium thrusters, η ~45%); game versions run Argon/Ammonia/Hydrogen to stay inside the canonical resource list. T3.
- **VASIMR VX-200** (Ad Astra): 200 kW RF plasma, 5.7 N at Isp ~4,900 s, η ≈ 0.70 at high Isp; variable specific impulse is its signature. Lab-demonstrated; flight-scale radiators unsolved → T3.

### 2.4 Solar sails

Flight-proven: IKAROS (JAXA 2010, 196 m²), LightSail 2 (2019, 32 m²), NEA Scout (2022, 86 m² design). NASA Solar Cruiser matured a 1,653 m² design. Solar radiation pressure on a perfect reflector at 1 AU normal incidence: **9.08 µN/m²** (2 × 1,361 W/m² / c). Real sails achieve ~85% of ideal. Thrust is tiny but free and eternal — in-game niche: cargo tugs, station-keeping, sunward logistics.

### 2.5 `[SPECULATIVE]` T4 anchors

- **Direct Fusion Drive** (Princeton PFRC concept studies): 1–10 MW class, Isp ~10,000–12,000 s, ~2.5–5 N per MW, D-He3 fueled, doubles as a power plant. Physics-sound, not engineering-complete.
- **Fission-fragment rocket** (Werka NIAC Phase I FFRE study, 2012; NASA NTRS 20160010095): dusty-plasma fission fragments exhausted directly from a ~1 GWt core; Isp ≈ 527,000 s (exhaust ≈1.7% c), thrust 43 N (≈111 MW of jet power, ≈11% of core thermal — consistent with the report), vehicle-class mass ~113 t. At 43 N the 113 t study vehicle accelerates at 3.8×10⁻⁴ m/s² ≈ 12 km/s of Δv per year — the probe drive, not a freighter drive.
- **Project Daedalus** (British Interplanetary Society, 1978): inertial-confinement D-He3 pulse drive, exhaust velocity ~10,000 km/s (Isp ≈ 1.0×10⁶ s), first-stage thrust ≈7,500 kN. The endgame interstellar-precursor megaproject. Requires the [SPECULATIVE] He3 economy.

### 2.6 Cryogenic storage and transfer

- Passive LH2 storage in LEO with flight-grade MLI loses ~3–5%/month (NASA CPST/eCryo studies); LOX/LCH4 lose ~0.5–1%/month. Sunshields cut heat leak by ~4×; deep space with a shield is ~10× better than LEO.
- Zero-boiloff (ZBO) cryocoolers are flight-class hardware (reverse turbo-Brayton, Creare-class): lifting heat at 90 K costs ≈15 We per Wt; at 20 K (LH2) ≈100 We per Wt. ZBO is a power bill, which is the game hook into `09-power-thermal.md`.
- Storable-propellant transfer is routine (Progress→Salyut since 1978, Orbital Express 2007). Cryogenic transfer was demonstrated intra-vehicle by SpaceX in 2024 and is the keystone of HLS-style architectures — T1 in 2049 is defensible.

### 2.7 Honesty notes

- The 2D planar patched-conic world (locked decision) does not change any propulsion math; it only deletes plane-change Δv from mission budgets. Stated here once.
- Solid motors really have shaped thrust curves; the game burns them at constant rated average thrust (simplification, §4.2 note).
- All hypergolic engines are normalized to NTO/MMH at O/F 1.65 even where the historic engine burned Aerozine-50 — one fuel resource instead of two.
- Helium pressurant is abstracted into tank dry mass; methalox/hydrolox stages T1+ are autogenously pressurized (real Raptor practice). No Helium resource exists.

## 3. Game Model

All formulas SI. `g0 = 9.80665 m/s²` everywhere, on every body — Isp is defined against standard gravity, period.

### 3.1 Symbols

| Symbol | Meaning | Unit |
|---|---|---|
| F | thrust | N (catalog in kN) |
| Isp | specific impulse | s |
| ve | effective exhaust velocity = g0·Isp | m/s |
| ṁ | total propellant mass flow | kg/s |
| P | electrical input power (EP) | W |
| η | system efficiency (EP), jet power / input power | – |
| p_amb | ambient static pressure | kPa |
| x | throttle fraction | – |
| w | wear fraction | – |
| O/F | oxidizer:fuel mass ratio | – |

### 3.2 The rocket equation as the builder uses it

Per stage *s* (modules grouped by the player's staging list, `06-ships-stations.md`):

```
Δv_s = g0 · Isp_eff · ln(m_start / m_end)            [m/s]
m_start = wet mass of this stage + all upper stages
m_end   = m_start − usable propellant burned this stage
```

Mixed engines burning simultaneously use thrust-weighted effective Isp:

```
Isp_eff = ΣF_i / Σ(F_i / Isp_i)                      [s]
```

Mass flow and burn time:

```
ṁ_i = F_vac,i / (g0 · Isp_vac,i)                     [kg/s]   (constant; throttle scales it)
t_burn = m_prop / Σ(x_i · ṁ_i)                       [s]
```

Propellant split by mixture ratio (per engine, both flows drawn from feed-connected tanks):

```
ṁ_ox   = ṁ · O/F ÷ (1 + O/F)
ṁ_fuel = ṁ · 1   ÷ (1 + O/F)
```

Engine cuts off when EITHER commodity in its pair is exhausted; the UI flags the limiting propellant.

Worked example (shown as an in-game tooltip): NTR tug, dry 28.0 t (engine 2.4 t + shadow shield 1.5 t + structure/tank), 42.0 t LH2. Δv = 9.80665 · 900 · ln(70/28) = **8,090 m/s**. ṁ = 73,000/(9.80665·900) = 8.27 kg/s → 5,080 s of full-thrust burn.

Game O/F constants (locked, must match `04-resources-isru.md` chains):

| Pair | O/F by mass | Note |
|---|---|---|
| LOX : RP1 | 2.36 | Merlin ratio |
| LOX : LH2 | 6.00 | RL10/RS-25 envelope (real 5.5–6.03) |
| LOX : LCH4 | 3.60 | inside Raptor's 3.5–3.8; ISRU must deliver 3.6 kg O2 per kg CH4 |
| NTO : MMH | 1.65 | Shuttle OMS ratio |

### 3.3 Thrust and Isp vs ambient pressure

Each engine tabulates `F_vac`, `Isp_vac`, `Isp_SL`. Mass flow is pressure-independent. Linear back-pressure model (exact for fixed nozzle exit area):

```
ṁ      = F_vac / (g0 · Isp_vac)
Isp(p) = Isp_vac − (Isp_vac − Isp_SL) · (p_amb / 101.325)      [s, p_amb in kPa]
F(p)   = ṁ · g0 · Isp(p)                                        [N]
```

- Valid for p_amb ≤ 101.325 kPa. For p_amb above 1 atm (Venus below ~50 km altitude) the formula keeps extrapolating; an engine whose F(p) ≤ 0.3·F_vac **cannot ignite** (flow separation / backflow). Practically: no chemical ascent from the Venus surface; aerostat altitude (~50–55 km, p ≈ 50–100 kPa) is flyable. Cross-ref `03-solar-system.md` atmosphere tables.
- **Vacuum-rated engines** (catalog column `p_max`): firing at p_amb > p_max is inhibited by default. Player override allowed: while overridden, wear accrues at 20× rate and each second rolls 2% chance of immediate engine-out (flow-separation side loads).
- Every catalog row — including vacuum-rated engines and the NTRs of §4.3 — tabulates an Isp_SL. For vacuum-rated engines it is a **synthetic** value (marked † in the catalogs) that encodes the nozzle back-pressure slope, so Isp(p), F(p), and the 0.3·F_vac ignition check are computable at any ambient pressure (off-design firing up to p_max, and override flights above it). It is not a claim that the engine operates at sea level — p_max remains the default inhibit. NTR Isp_SL scales by the same k factor as Isp_vac when burning alternate propellants (§3.10).

### 3.4 Throttle

Throttle x ∈ [x_min, 1.0] scales ṁ linearly. Small Isp penalty below 60% (film-cooling/injector off-design):

```
Isp(x) = Isp · (1 − 0.08 · max(0, 0.6 − x) / 0.6)
```

(At CECE-style x = 0.06: Isp × 0.928.) Solids: x fixed = 1, no shutdown, no restart. EP throttles 0.2–1.0 continuously with no Isp penalty (power scales instead, §3.9).

### 3.5 Ignition, ullage, chilldown

An ignition attempt succeeds only if ALL hold:

1. **Engine serviceable**: wear w < 2.0 (§3.14). Rated ignition counts (catalog `rated ign`) are wear normalizers, never a hard inhibit — ignition is always permitted while w < 2.0, but p_ignition_fail grows without bound as wear accrues (§3.14).
2. **Ullage settled** (pump-fed liquid engines only): vehicle longitudinal acceleration ≥ 0.005 m/s² sustained 3 s before ignition (RCS ullage burn, another engine, or surface gravity), OR every feeding tank has a PMD (propellant management device option: +2% tank dry mass, only available on tanks ≤ 20 t capacity). Pressure-fed, solid, cold-gas, and EP are exempt.
3. **Chilldown** (cryo pump-fed engines after > 1 h since last burn): ignition consumes 5 s of rated ṁ as vented chill propellant before thrust ramps.
4. **Propellant unfrozen and tank pressure NOMINAL** — every feeding tank holds m_gas < 0.005 × capacity per the §3.12 overpressure surrogate (§8).
5. Reliability roll passes (§3.14).

### 3.6 Gimbal and control authority

Engines gimbal ±δ (catalog). Control torque per engine about the stack center of mass:

```
τ = F · sin(δ_cmd) · L          [N·m, L = lever arm from CoM, |δ_cmd| ≤ δ_max]
```

The flight computer (13-architecture owns the controller) auto-allocates gimbal + differential throttle + RCS. Builder check: a stage whose total pitch authority τ_max < 1.5× worst-case thrust-offset torque (one engine out at max thrust) gets a red "CONTROL AUTHORITY" warning.

### 3.7 TWR rules per context

```
TWR_local = ΣF(p_amb) / (m · g_local)        g_local from 03-solar-system.md
```

| Context | Rule |
|---|---|
| Surface launch, atmosphere (Earth, Mars, Titan) | Liftoff requires TWR > 1.0; builder warns < 1.2; recommended 1.3–1.5 (Earth). Gravity/drag losses emerge from the 01 integrator; the locked budget figure for Earth pad→LEO is **9,400 m/s**. |
| Surface launch, airless (Moon, asteroids) | TWR > 1.0 strictly; recommended ≥ 1.8 to limit gravity loss. |
| Powered landing | At ignition of final descent: TWR_local must be > 1.0 at touchdown body or the lander is unrecoverable; UI suicide-burn planner enforces. |
| Orbital tug / deep space | No minimum. Maneuver planner warns when t_burn > T_orbit/20 at the burn's orbit (impulsive approximation degrading) and offers burn-splitting across periapsis passes (mechanic owned by 01). |
| Low-thrust (EP, sail) | Planner uses the circular-spiral estimate `Δv ≈ |v_c,start − v_c,end|` (circular orbit speeds); truth is the 01 integrator under warp. |

### 3.8 Solid motors

Constant rated average thrust for `t_burn`s; cannot stop, throttle, or restart; cannot be refueled (the motor is a sealed part). Jettison while burning is forbidden. After 10 years from manufacture, ignition failure probability ×5 (propellant aging).

### 3.9 Electric propulsion model

The locked coupling formula:

```
T  = 2 · η · P / (g0 · Isp)                  [N]
ṁ  = T / (g0 · Isp) = 2 · η · P / (g0·Isp)²  [kg/s]
P/T = g0 · Isp / (2 · η)                     [W per N]   e.g. NSTAR: 25 kW/N
```

- `P` is electrical input drawn from the bus (`09-power-thermal.md`). If available power < demand, thrust scales with delivered P; below 20% of rated P the thruster drops out (discharge unsustainable).
- **Waste heat** (interface to 09) scales with thruster family, not a flat fraction: gridded ion and Hall reject 10% of P_in through ship radiators (PPU + thruster body), VASIMR 15%, MPD 30% (anode-fall losses are deposited in the thruster body and must be radiated, not carried off in the plume). The rest of the non-jet power leaves in the plume.
- **Atmosphere inhibit**: EP thrusters require p_amb < 0.01 kPa. Above that they cannot start, and a running thruster shuts down benignly (no failure roll consumed). Sails have their own atmosphere rule (§3.11).
- **Propellant**: gridded ion and small Hall require Xenon. HALL-100, MPD, VASIMR accept Argon (catalog η); MPD may also run Ammonia (η −0.05) or Hydrogen (η −0.05, Isp +25%).
- **VASIMR variable Isp** at constant power — player slider, linear-interpolated η:

| Isp setting | 3,000 s | 4,900 s | 12,000 s |
|---|---|---|---|
| η | 0.45 | 0.69 | 0.76 |
| Thrust at 200 kW | 6.1 N | 5.7 N | 2.6 N |

- **Wear** is throughput-based: w = kg propellant processed / rated throughput (catalog). No ignition count.

### 3.10 Nuclear-thermal model

- Reactor thermal power implied: `P_t ≈ F · ve / (2 · 0.85)` (85% thermal→jet). SNRE check: 73 kN × 8,826 m/s / 1.7 = 379 ≈ its real 367 MWt. Displayed, not player-managed. The catalog `Reactor (MWt)` values are **canonical** — they feed the UI and the dose law below; the formula is the design-time derivation only. Where they differ (NTR-246: formula 1,211 MWt vs catalog anchor 1,140 MWt), the catalog wins — same treatment as EP thrust in §4.4.
- **Propellant flexibility** (any single fluid; Isp = k × Isp_H2 of that engine):

| Propellant | k | Isp on NTR-73 (s) | Wear mult | Anchor / note |
|---|---|---|---|---|
| Hydrogen | 1.00 | 900 | ×1 | NERVA/SNRE baseline |
| Methane | 0.67 | 600 | ×4 | NERVA-era studies; carbon coking |
| Ammonia | 0.50 | 450 | ×1.5 | NERVA-era alternate-propellant studies |
| Water | 0.38 | 340 | ×1.2 | "steamer" concept studies |
| CO2 | 0.295 | 265 | ×2 | Zubrin NIMF Mars-hopper studies (264 s) |

  Thrust scales with ṁ·ve at constant reactor power: `F_alt = F_H2 / k`, ṁ_alt = ṁ_H2 / k². (Denser propellant → more thrust, less Isp.)
- **LANTR mode** (T2 upgrade module, +250 kg per engine): injects LOX at O/F 3.0 → Isp = 645 s, thrust ×2.75, draws LOX from tanks (ISRU demand: 3 kg LOX per kg H2). Toggle in flight. (Borowski LANTR/LUNOX study values, §2.2.)
- **Shadow shield**: optional module (catalog). Defines a safe cone, half-angle 12°, axis along the stack, apex at the reactor. During burns, any crew/electronics module outside the cone receives dose rate `D = 1×10⁴ Sv/h × (P_t / 367 MWt) × x × (25 m / r)²` (r = distance to reactor; P_t = catalog reactor power, so NTR-246 scales up by 1,140/367; x = throttle). Derivation kept in-doc: ~3% of core thermal power escapes the pressure vessel as prompt n/γ leakage → 11 MW at 367 MWt → 11 MW / (4π·625 m²) ≈ 1.4 kW/m² at 25 m ≈ 5×10³ Gy/h to tissue, ~1×10⁴ Sv/h after neutron quality factors. An operating, unshielded NTR is promptly lethal within tens of meters in seconds-to-minutes — exactly why real NTR crew studies carry tonnes of shadow shield. Inside the cone: 0.1 mSv/h at full power, scaling with the same `(P_t / 367 MWt) × x` factor. Any gameplay softening must be bought as additional 4π secondary shield mass, never by editing the unshielded constant. Dose bookkeeping and limits live in `08-life-support-crew.md`; electronics degradation in `06-ships-stations.md`. Uncrewed tugs may skip the shield (save 1.5 t) at the cost of irradiating any docked payload.
- **Cooldown rule**: after each burn the engine automatically trickle-flows 1.5% of the propellant mass just burned over the following 2 h (decay heat), producing thrust at Isp 350 s (auto-applied by the integrator as a small acceleration). If feed propellant is unavailable, reactor takes damage: wear +0.25.
- **Restart**: 45 min minimum between shutdown and re-ignition (thermal). Rated ignition counts per catalog (NERVA XE' demonstrated 24).
- No NTR operation below 60 km altitude on Earth (regulatory, hard rule; other bodies unrestricted). Launch NTRs cold; first criticality only in orbit.

### 3.11 Solar sail model

```
F_sail = 9.08e-6 N/m² · η_s · A · cos²θ · (1 AU / r)²      [N]
```

- η_s = 0.85 (film reflectivity/billow); A = deployed area (m²); θ = angle between sail normal and sunline, player-commanded, |θ| ≤ 60°; thrust vector along sail normal (away from Sun). r = heliocentric distance.
- Sails degrade: η_s loses 0.01/year (UV/micrometeoroids).
- Thermal limit: inside r = 0.25 AU standard aluminized film overheats — sail takes 1% area damage per hour inside the limit.
- Deployed sails cannot survive atmosphere or thrust > 0.2 m/s² from other engines (auto-retract or tear; retract takes 1 h). 2D makes sail steering a single scalar θ — clean fit.

### 3.12 Cryogenic storage and boiloff

Physically-derived, cheap to compute. Per cryo tank:

```
Q_leak  = q_env · k_ins · k_T · A_tank            [W]
ṁ_boil  = Q_leak / h_vap                          [kg/s]  (vented automatically as gas, lost)
A_tank  = sphere-equivalent area of capacity volume (precomputed per tank part)
k_T     = 1.0 for 20 K cryogens (LH2);  0.5 for ≥ 77 K cryogens (LOX, LCH4, LN2, LAr)
```

`k_T` reflects MLI heat leak scaling roughly with the cold-side ΔT: 90–111 K cryogens leak materially less through the same blanket than 20 K LH2. The 0.5 value is calibrated so standard-MLI methalox in LEO lands inside the published 0.5–1%/month band (§2.6).

Environment factor `q_env` (W/m², game-calibrated to CPST-class studies). Evaluated as a decision tree, top-down, once per tank per tick; the FIRST matching rule applies and **exactly one rule always matches**:

1. **Landed on a listed surface** (others fall through to the heliocentric rules; each row lists ambient temperature T_amb for the clamp rule below):

| Surface | q_env | T_amb |
|---|---|---|
| Lunar surface, day | 2.0 | 390 K |
| Lunar surface, night / permanently shadowed crater | 0.05 | 100 K (PSR ~40 K) |
| Mars surface (diurnal avg) | 0.6 | 210 K |
| Titan surface | 0.3 | 94 K |

2. **Else, heliocentric r < 1.5 AU** (any orbit or atmospheric flight): `q_env = (1 AU / r)²`, capped at 3.0 — sunlit LEO = 1.0, Venus transfer/orbit at 0.72 AU = 1.93, Mercury capped at 3.0. Multiply by ×0.25 if a sunshield is deployed (§4.8 SUN series).
3. **Else, 1.5 AU ≤ r < 3 AU**: q_env = 0.4; or 0.10 if a sunshield is deployed or the tank is permanently shadowed.
4. **Else (r ≥ 3 AU)**: q_env = 0.03.

**Cold-ambient clamp**: on a surface whose T_amb is at or below the cryogen's storage temperature, that tank's Q_leak = 0 (no boiloff). Titan at 94 K: LCH4 (111 K) is free, LOX (90 K) nearly free, LH2 still leaks.

Insulation factor `k_ins`: bare ascent tank ×20; standard MLI ×1.0; depot-grade (60-layer MLI + vapor-cooled shield, +0.03 tankage fraction) ×0.25.

**Sunshield (deployable part — §4.8 SUN-1 / SUN-4)**: a multilayer deployable shade anchored to the eCryo/CPST depot-study sunshields. While deployed it applies the ×0.25 factor of rules 2–3 to every tank of its host stack, up to its rated shaded area (tank area beyond that is unshaded). Deploy and retract each take 1 h. A deployed sunshield is destroyed by atmospheric flight or stack acceleration > 0.2 m/s² (same rule as sails, §3.11); EP, sail, and NTR-cooldown accelerations are safe.

Propellant thermal constants:

| Cryogen | Storage T (K) | h_vap (kJ/kg) |
|---|---|---|
| LH2 | 20 | 446 |
| LCH4 | 111 | 511 |
| LOX | 90 | 213 |
| LN2 | 77 | 199 |
| LAr | 87 | 161 |

Worked check (matches published %/month): 50 t LH2 sphere → V = 706 m³, A = 383 m². LEO, standard MLI (k_T = 1.0): Q = 383 W → 74 kg/day → **4.4%/month**. Same tank, sunshield + depot insulation: 0.28%/month. Methalox stack of equal mass (50 t at O/F 3.6, two sphere-equivalent tanks, k_T = 0.5): ≈**0.85%/month** LEO passive — inside §2.6's published 0.5–1%/month band. (%/month scales as m^(−1/3): bigger stacks boil proportionally slower.)

**Active ZBO (cryocoolers)**: modules lift Q_lift watts at their stage temperature for electrical input (interface to 09; they also reject `P_in + Q_lift` as waste heat):

```
P_elec = SP · Q_lift        SP = 15 We/Wt @ 90 K (LOX/LCH4/LAr),  100 We/Wt @ 20 K (LH2)
Net boiloff = max(0, Q_leak,eff − Σ Q_lift | T_stage ≤ T_store) / h_vap
```

Only coolers whose cold-head stage temperature is **at or below the tank's storage temperature** count toward the lift sum — a 90 K cold head cannot absorb heat from a 20 K tank (second law; this also closes the exploit of cheap ZBO-90s substituting for the 5×-more-power-hungry ZBO-20). **Staged cooling** (the real depot architecture): a powered ZBO-90 mounted on an LH2 tank instead acts as a heat interceptor at that tank's vapor-cooled shield, multiplying the tank's Q_leak by ×0.25 before the 20 K stage (`Q_leak,eff`). At most one interceptor multiplier applies per tank — additional ZBO-90s on the same LH2 tank add nothing. This is how DEP-600 reaches net zero (§4.8).

**Storables in the cold**: NTO freezes < 262 K, MMH < 221 K, RP1 gels < 226 K, Water freezes < 273 K. Tanks holding storables (or Water propellant) in environments with equilibrium temp below threshold need heater power 50 W per t of propellant (09 interface) or the propellant freezes (engines inoperable; thawing takes 6 h of double heater power).

**Tank overpressure (surrogate model — deliberately not real thermodynamics)**: venting is on by default (boiloff gas is dumped and lost). If the player disables venting, boiloff gas accumulates in a per-tank counter `m_gas` at the ṁ_boil rate above. States: pressure **NOMINAL** (ignition permitted, §3.5) while m_gas < 0.005 × tank propellant capacity; **TANK OVERPRESSURE** alarm (ignition blocked) at m_gas ≥ 0.005 × capacity; tank **bursts** at m_gas ≥ 0.02 × capacity (the "150% rating" event — module destroyed, 06 damage model). Re-enabling venting dumps m_gas over 60 s, after which the tank is NOMINAL again.

Boiloff integrates analytically under time warp (13 interface): closed-form linear drain, event scheduled at tank-empty.

### 3.13 Propellant transfer and depots

- Transfer requires a docked **PTC-200 coupler** path (catalog) or base plumbing (`07-bases-habitats.md`).
- Rates per coupler: storable liquids 20 kg/s; cryogens 5 kg/s; gases (Xenon/Nitrogen/Argon gas) 0.5 kg/s.
- **Cryo settling**: liquid cryo transfer requires ullage acceleration ≥ 0.0005 m/s² (settling thrust, ~50 N per 100 t stack — RCS trickle) for the duration, OR a PTC-300L LAD coupler (internal liquid-acquisition devices, catalog §4.8) at 60% rate.
- **Chilldown loss**: transferring cryogen into a warm tank (empty > 24 h) vents 1.5% of the transferred mass.
- Solids and sealed items: not transferable.
- Depots are tank modules + ZBO + sunshield + couplers sold as parts (catalog §4.8). A depot with powered ZBO sized ≥ Q_leak holds cryogens indefinitely; on power loss it reverts to passive boiloff (alarm).
- Depot economics (locked intent for `12-gameplay-economy-ui.md`): propellant at the right depot is the game's standard tradable good; price = production + logistics, no magic markets.

### 3.14 Reliability and wear

Per engine instance, wear fraction:

```
Chemical/NTR:  w = 0.6·(t_burned / t_rated) + 0.4·(n_ign / n_rated)
EP:            w = m_throughput / m_rated
```

Failure probabilities (multiplier applies to both):

```
p_ignition_fail = p_base · (1 + 9·w²)
λ_inflight      = λ0 · (1 + 9·w²)        [probability per second of burn]
```

| Engine class | p_base (per ignition) | λ0 (per s) |
|---|---|---|
| Solid | 0.001 | 2×10⁻⁶ |
| Pressure-fed liquid | 0.0005 | 5×10⁻⁷ |
| Pump-fed liquid (new type) | 0.002 | 2×10⁻⁶ |
| Pump-fed liquid (Mature: after 25 program-wide successful ignitions of the type) | 0.0005 | 5×10⁻⁷ |
| NTR | 0.003 | 1×10⁻⁶ |
| Electric | 0.0002 | 1×10⁻⁸ |

`t_rated` and `n_rated` (catalog `burn` / `rated ign`) are **wear normalizers only, never hard inhibits**: an engine may exceed its rated counts. Ignition is always permitted while w < 2.0; p_ignition_fail and λ_inflight simply keep growing without bound through the (1 + 9·w²) multiplier, and the only hard stop is the w = 2.0 no-refurbish line below. Hypergolic and EP catalog counts are wear data like any other — not ignition limiters. **Mature status** (25 program-wide successful ignitions of the type, §6) divides BOTH p_base and λ0 by 4 for EVERY engine class — solid, pressure-fed, pump-fed, NTR, EP; the table's pump-fed pair is the worked example.

**RCS blocks** are exempt from per-ignition rolls (no RNG draw per pulse — flight computers fire thousands). They wear on total impulse delivered: `w = (N·s delivered) / (rated total impulse)` (§4.7 column). A λ-style failure check, using the Electric-class λ0 and the (1 + 9·w²) multiplier, runs once per maneuver, not per pulse. RCS failures are always benign (block dead).

Failure outcome roll (chemical/NTR): 70% benign shutdown (one restart attempt allowed at 25% success, else engine dead), 25% engine permanently dead, 5% energetic failure — engine destroyed, each adjacent module 50% chance of damage (damage model in `06-ships-stations.md`). Solids: 60% thrust-anomaly (±20% thrust for rest of burn), 40% energetic. EP failures are always benign (thruster dead).

**Maintenance**: a workshop (`05-industry-logistics.md` module) with crew or robot arm can refurbish an engine for 20% of its MachineParts build cost: resets counters to 20% of rated (w → 0.2). An engine past w = 2.0 cannot be refurbished — scrap for 50% material recovery. All RNG draws come from the deterministic mission seed (13 interface).

### 3.15 RCS

RCS blocks are modules with 4 nozzles in a cross; the flight computer fires them for torque/translation (13 owns allocation). Propellant draw `ṁ = F/(g0·Isp)` per firing nozzle; pulses < 0.1 s pay Isp ×0.9. RCS provides ullage and settling thrust (§3.5, §3.13). Sizing rule shown in builder: angular acceleration `α = Σ(F_nozzle · L_i) / I_stack ≥ 0.02 rad/s²` about the worst axis for a "responsive" rating, where L_i is each nozzle's lever arm and I_stack is the stack moment of inertia (provided by `06-ships-stations.md`, §7).

### 3.16 Mass and cost model

**Tankage fractions** (dry tank mass / propellant capacity; includes abstracted pressurant, plumbing, MLI class as listed):

| Tank type | f_tank | Note |
|---|---|---|
| RP1 / storables, pump-fed feed | 0.06 | |
| Storables, pressure-fed feed | 0.10 | the pressure-fed tax |
| Kerolox/methalox launch tank | 0.05 | thin-wall booster grade, bare (k_ins ×20) |
| Methalox / LOX in-space tank, standard MLI | 0.065 | |
| LH2 in-space tank, standard MLI | 0.12 | LH2 density tax |
| LH2/hydrolox launch tank, bare (k_ins ×20) | 0.085 | thin-wall booster grade for H-2280 first stages |
| Water tank | 0.02 | ambient; freezes < 273 K — heater rule §3.12 |
| Ammonia tank | 0.06 | chilled ~240 K or pressurized ambient |
| CO2 tank, pressurized | 0.10 | liquid CO2 at 220 K / ≈600 kPa saturation (§4.1) |
| LN2 cryo tank | 0.08 | |
| Depot-grade option (any cryo) | +0.03 | k_ins ×0.25 |
| Xenon COPV | 0.05 | Dawn-class: 21.6 kg tank / 425 kg Xe |
| Argon cryo tank | 0.08 | |
| Nitrogen cold-gas COPV (300 bar) | 0.80 | why cold gas is for small craft only |
| PMD option (tanks ≤ 20 t) | f_tank × 1.02 | zero-g start without ullage (§3.5); real PMDs (vanes/sponges/galleries) are light |

**Build recipes** (interface offer to `05-industry-logistics.md`; per kg of part dry mass):

| Part family | Recipe (kg per kg) |
|---|---|
| Pump-fed chemical engine | 0.45 MachineParts, 0.25 IronSteel, 0.10 Copper, 0.10 Titanium, 0.10 Electronics |
| Pressure-fed engine | 0.30 MachineParts, 0.30 IronSteel, 0.20 Titanium, 0.10 Polymers, 0.05 Copper, 0.05 Electronics |
| Solid motor (gross mass incl. propellant) | 0.20 MachineParts, 0.30 Aluminum, 0.50 Polymers — propellant abstracted; Earth/T3 chem plant only |
| NTR | 0.30 MachineParts, 0.25 IronSteel, 0.10 Titanium, 0.10 Carbon, 0.10 Electronics, 0.05 Copper, 0.05 Uranium (HALEU), 0.05 StructuralParts |
| EP thruster + PPU | 0.35 Electronics, 0.20 Copper, 0.20 MachineParts, 0.10 Titanium, 0.10 RareEarths, 0.05 Silicon |
| Tanks | 0.70 Aluminum, 0.15 MachineParts, 0.15 Polymers (COPV: 0.35 Carbon, 0.25 Titanium, 0.20 Polymers, 0.20 MachineParts) |
| Solar sail | 0.50 Polymers, 0.20 Aluminum, 0.20 MachineParts, 0.10 Electronics |
| RCS block | 0.30 MachineParts, 0.30 IronSteel, 0.20 Titanium, 0.10 Polymers, 0.05 Copper, 0.05 Electronics (mirrors pressure-fed engine) |
| PTC coupler / ZBO cryocooler | 0.30 MachineParts, 0.25 IronSteel, 0.20 Copper, 0.15 Electronics, 0.10 Titanium |
| Sunshield (SUN series) | 0.55 Polymers, 0.30 Aluminum, 0.10 StructuralParts, 0.05 MachineParts |

Depots (DEP-60/DEP-600) have no recipe of their own: they are assembled from their constituent parts — tanks + ZBO units + couplers + sunshield (§4.8).

**Cost classes** (monetary mapping owned by `12-gameplay-economy-ui.md`): **A** consumable/cheap; **B** mass-produced engine (T1 factory); **C** precision aerospace (Earth import or T2 orbital fab); **D** nuclear/exotic (Earth import + regulatory event, or T3 fab; consumes Uranium license); **E** megaproject (Endgame chain only).

## 4. Content Catalog

### 4.1 Propellant properties (resource extensions declared here)

This document extends the canonical resource list with three genuinely-needed propellants: **RP1**, **NTO**, **MMH** (Earth-import at T0–T1; possible late synthesis routes are an open question for `04-resources-isru.md`). Solid propellant is NOT a resource (sealed parts).

| Resource | State as stored | Density (kg/m³) | Store T (K) | Cryo? | Notes |
|---|---|---|---|---|---|
| LOX (Oxygen) | liquid | 1,141 | 90 | yes | ISRU everywhere (water, regolith, CO2) |
| LH2 (Hydrogen) | liquid | 70.8 | 20 | deep | worst boiloff, biggest tanks |
| LCH4 (Methane) | liquid | 423 | 111 | yes | Sabatier ISRU; Titan native |
| RP1 | liquid | 815 | ambient | no | gels < 226 K; Earth-only |
| NTO | liquid | 1,442 | ambient | no | freezes < 262 K (heaters!) |
| MMH | liquid | 875 | ambient | no | freezes < 221 K |
| Xenon | supercritical gas | 1,580 | ambient | no | COPV ~86 bar; rare, expensive |
| Argon | liquid | 1,395 | 87 | yes | cheap EP propellant (atmospheres, regolith) |
| Nitrogen | gas 300 bar | 300 | ambient | no | cold gas RCS; ≈300 kg/m³ at 300 bar / 293 K (Z ≈ 1.13) |
| Water | liquid | 1,000 | ambient | no | NTR alternate propellant (§3.10); freezes < 273 K — heater rule §3.12 |
| Ammonia | liquid | 682 | 240 | no | NTR alternate (§3.10) and MPD propellant; chilled ~240 K or pressurized ambient |
| CO2 | liquid (saturated) | 1,166 | 220 | no | NIMF hopper propellant (§3.10); ≈600 kPa saturation pressure at 220 K, tank f 0.10 (§3.16) |

### 4.2 Chemical engines

Columns: dry mass; thrust SL/vac; Isp SL/vac; min throttle x_min; gimbal; rated ignitions; rated burn (s); p_max = max ambient pressure for ignition (kPa); cost class. Isp_SL values marked † are synthetic back-pressure slopes for vacuum-rated engines (§3.3) — model data, not a sea-level operating claim. "—" thrust-SL entries are computed from Isp_SL per §3.3 when needed.

| ID / game name | Anchor | Tier | Cycle / feed | Propellants (O/F) | Dry mass (kg) | Thrust SL/vac (kN) | Isp SL/vac (s) | x_min | Gimbal | Ign | Burn (s) | p_max | Cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SRM-2 "Kestrel" | Star 48B | T0 | solid | APCP (sealed; 2,011 kg prop, gross 2,137) | 126 burnout | — / 66 | 250 / 286 | 1.0 | none | 1 | 87 | 101 | A |
| SRM-49 "Aurochs" | GEM 63 | T0 | solid strap-on | APCP (sealed; 44,087 kg prop, gross ≈49,300 `[est]`) | ≈5,200 `[est]` | 1,265 avg (1,663 max) | 245 / 275 `[est]` | 1.0 | none | 1 | 94 | 101 | A |
| OMS-27 "Vireo" | Shuttle OMS AJ10-190 | T0 | pressure-fed | NTO/MMH (1.65) | 118 | — / 26.7 | 100† / 316 | 1.0 (fixed) | ±6° | 500 | 15,000 | 30 | B |
| SPS-91 "Pelican" | Apollo SPS AJ10-137 | T0 | pressure-fed | NTO/MMH (1.65; real SPS used A-50) | 293 | — / 91 | 60† / 314 | 1.0 (fixed) | ±6° | 200 | 750 | 30 | B |
| LND-71 "Ibex" | SuperDraco | T1 | pressure-fed lander | NTO/MMH (1.65) | 120 `[est]` | 71 / 73 | 235 / 243 `[est]` | 0.20 | fixed (cluster diff-throttle) | 300 | 600 | 101 | B |
| K-845 "Mule" | Merlin 1D | T0 | GG pump-fed kerolox | LOX/RP1 (2.36) | 470 | 845 / 914 | 282 / 311 | 0.40 (landing variant) | ±5° | 20 | 2,500 | 101 | B |
| KV-981 "Mule-V" | Merlin Vacuum | T0 | GG pump-fed kerolox | LOX/RP1 (2.36) | 630 `[est]` | — / 981 | 90† / 348 | 0.60 | ±3° | 10 | 1,500 | 20 | B |
| H-102 "Crane" | RL10C-1 | T0 | expander hydrolox | LOX/LH2 (6.0) | 190 | — / 101.8 | 110† / 449.7 | 1.0 (fixed) | ±4° | 15 | 2,000 | 25 | C |
| HL-67 "Heron" | CECE (RL10 deriv.) | T1 | expander hydrolox lander | LOX/LH2 (6.0) | 230 `[est]` | — / 67 | 120† / 445 | 0.06 | ±4° | 50 | 2,000 | 60 | C |
| H-2280 "Shire" | RS-25 | T1 | staged-comb. hydrolox | LOX/LH2 (6.0) | 3,177 | 1,860 / 2,279 | 366 / 452 | 0.67 | ±10.5° | 55 | 27,000 | 101 | C |
| M-2256 "Drayhorse" | Raptor 2 | T1 | FFSC methalox | LOX/LCH4 (3.6) | 1,630 | 2,256 / 2,394 | 327 / 347 | 0.40 | ±15° | 50 | 5,000 | 101 | B |
| MV-2530 "Drayhorse-V" | Raptor Vacuum | T1 | FFSC methalox | LOX/LCH4 (3.6) | 2,100 `[est]` | — / 2,530 `[est]` | 100† / 380 `[est]` | 0.40 | ±3° | 50 | 5,000 | 40 | B |
| ML-24 "Gopher" | NASA Project Morpheus HD | T2 | pressure-fed methalox lander | LOX/LCH4 (3.6) | 80 `[est]` | 22 / 24 | 295 / 320 `[est]` | 0.25 | ±5° | 500 | 3,000 | 101 | B |

Notes: Merlin SL/vac thrust pair implies ṁ = 914,000/(9.80665·311) = 299.7 kg/s; the model derives F_SL from Isp_SL per §3.3 (small rounding vs the listed real figure is accepted). T/W sanity anchors: Merlin ≈183, Raptor 2 ≈141, RS-25 ≈73, RL10C ≈55 — all match published values.

### 4.3 Nuclear-thermal engines (T2; cost class D; H2 baseline, alternates per §3.10)

| ID / name | Anchor | Dry mass (kg) | Thrust vac (kN) | Isp vac (s) | Isp SL (s) | Reactor (MWt) | x_min | Gimbal | Ign | Burn rated (s) | p_max (kPa) | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NTR-73 "Prometheus" | SNRE (Schnitzler/Borowski), DRACO-class | 2,400 (+1,500 shadow shield option) | 73 | 900 | 750† | 367 | 0.25 | ±3° | 30 | 16,200 | 30 | LANTR option +250 kg: Isp 645 s, thrust ×2.75 (LOX O/F 3.0) |
| NTR-246 "Prometheus-H" | NERVA XE' (modernized) | 12,500 game (historic 18,144 incl. test hardware; modern composites) | 247 | 850 (historic 841 ideal) | 700† | 1,140 | 0.25 | ±3° | 30 (XE' demoed 24) | 10,800 | 30 | heavy tug core, Act 3–4 |

† synthetic Isp_SL per §3.3; scales by the same k as Isp_vac on alternate propellants (§3.10). p_max 30 kPa permits Mars-ambient NIMF hops (0.6–1 kPa) but not Titan surface ignition (147 kPa).

NTR T/W: 3.1 and 2.0 — deliberately, honestly poor; NTRs are space-only tugs.

### 4.4 Electric thrusters (per-string = thruster + PPU + feed; gimbal ±10° mount included)

| ID / name | Anchor | Tier | Propellant | P_in (kW) | Thrust | Isp (s) | η | String mass (kg) | Rated throughput (kg) | Cost |
|---|---|---|---|---|---|---|---|---|---|---|
| ION-2 "Mayfly" | NSTAR (DS1/Dawn) | T0 | Xenon | 2.3 | 92 mN | 3,120 | 0.61 | 30 | 235 (ELT-demonstrated) | C |
| ION-7 "Dragonfly" | NEXT | T1 | Xenon | 6.9 | 236 mN | 4,190 | 0.70 | 58 `[est]` | 918 (LDT-demonstrated) | C |
| HALL-1 "Wren" | SPT-100 | T0 | Xenon | 1.35 | 83 mN | 1,600 | 0.48 | 12 | 170 | B |
| HALL-12 "Harrier" | AEPS/HERMeS | T1 | Xenon | 12.5 | 590 mN | 2,800 | 0.65 | 115 `[est]` | 1,700 `[design target]` | C |
| HALL-100 "Condor" | X3 nested Hall (UM/AFRL) | T3 | Xenon or Argon (η −0.06) | 100 | 5.4 N | 2,000 | 0.52 | 460 `[est]` | 5,000 `[est]` | D |
| MPD-200 "Albatross" | NASA Lewis / MAI applied-field MPD | T3 | Argon (Ammonia η −0.05; Hydrogen η −0.05, Isp +25%) | 200 | 4.6 N | 4,000 | 0.45 | 900 `[est]` | 20,000 `[est]` | D |
| VAS-200 "Petrel" | VASIMR VX-200 | T3 | Argon | 200 | 5.7 N @4,900 s (variable 3,000–12,000 s, §3.9) | 4,900 | 0.69 | 650 `[est]` | 30,000 `[est]` | D |

Sanity row: every row satisfies T = 2ηP/(g0·Isp) within rounding — the sim computes thrust from that formula, the table is display data.

### 4.5 Solar sails (module = film + booms + actuators)

| ID | Anchor | Tier | Area (m²) | Module mass (kg) | F at 1 AU, θ=0 (mN) | Cost | Note |
|---|---|---|---|---|---|---|---|
| SAIL-86 | NEA Scout | T1 | 86 | 12 | 0.66 | B | smallsat scouting |
| SAIL-1650 | NASA Solar Cruiser | T2 | 1,653 | 90 | 12.8 | C | station-keeping, sunward cargo |
| SAIL-10K | scaled NIAC/JPL study class | T3 | 10,000 | 250 `[est]` | 77 | C | slow bulk tug; a = 0.1 mm/s² on a 750 kg craft ≈ 8.9 m/s per day |

### 4.6 T4 endgame drives — all `[SPECULATIVE]`, research tier T4 only

| ID | Anchor | Thrust | Isp (s) | Power / fuel | Mass | Role |
|---|---|---|---|---|---|---|
| DFD-5 "Helios" | Princeton Direct Fusion Drive concept | 20 N | 10,500 | 5 MW fusion; He3 + Hydrogen (deuterium folded into Hydrogen); also exports 1 MWe bus power | 10 t `[concept]` | crewed outer-system clipper |
| FFR-43 "Phoenix" | Werka NIAC FFRE study (2012) | 43 N | 527,000 | ≈1 GWt dusty-plasma fission core; Uranium | 113 t `[concept]` (study vehicle mass) | interstellar-precursor probe drive: 43 N / 113 t = 3.8×10⁻⁴ m/s² ≈ 12 km/s Δv per year |
| PULSE-D "Daedalus" | BIS Project Daedalus (1978) | 7,500 kN | ≈1,000,000 | He3/D ICF pellets, 250 Hz | ≈1,700 t assembly | Endgame megaproject only (12-gameplay economy chain); not a buildable ship part |

These exist to end the campaign, not to balance against T2 hardware. He3 supply chain per `04-resources-isru.md` [SPECULATIVE] tier.

### 4.7 RCS blocks (4-nozzle cross modules)

| ID | Anchor | Tier | Propellant | Thrust per nozzle (N) | Isp (s) | Block mass (kg) | Rated total impulse (N·s) | Cost | Notes |
|---|---|---|---|---|---|---|---|---|---|
| RCS-N10 | industry cold-gas | T0 | Nitrogen | 10 | 70 | 8 | 2×10⁵ | A | smallsats; COPV tankage 0.80 |
| RCS-D400 | SpaceX Draco | T0 | NTO/MMH (1.65) | 400 | 300 | 22 | 5×10⁶ | B | workhorse; ullage-capable |
| RCS-M2K | Starship hot-gas methalox | T1 | gaseous LOX/LCH4 from main tanks | 2,000 | 270 `[est]` | 60 | 2×10⁷ | B | no separate RCS propellant — the depot-era choice |

RCS wear is total-impulse-based and failure is checked once per maneuver, never per pulse (§3.14).

### 4.8 Tanks, depots, transfer hardware, cryocoolers, sunshields

Catalog part masses are **canonical** and override the §3.16 parametric fractions where they differ. Depots are assemblies of their constituent parts (tanks + ZBO units + couplers + sunshield); they have no recipe or cost class of their own.

| ID | Tier | Capacity | Dry mass | Power draw | Cost | Notes |
|---|---|---|---|---|---|---|
| Tank parts (parametric) | T0+ | player-sized | per §3.16 fractions | heaters per §3.12 | A | every propellant |
| PTC-200 coupler | T1 | n/a | 150 kg | 0.1 kWe while pumping | B | 5 kg/s cryo / 20 kg/s storable / 0.5 kg/s gas |
| PTC-300L LAD coupler | T3 | n/a | 250 kg | 0.2 kWe while pumping | C | internal liquid-acquisition devices: cryo transfer without settling at 3 kg/s (60% of PTC-200 cryo rate); storable/gas rates as PTC-200 (§3.13) |
| ZBO-90 cryocooler | T1 | lifts 50 Wt @ 90 K | 25 kg | 0.75 kWe; rejects 0.8 kWt | C | LOX/LCH4/LAr; on an LH2 tank acts as shield-stage interceptor, Q_leak ×0.25 (§3.12) |
| ZBO-20 cryocooler | T1 | lifts 20 Wt @ 20 K | 90 kg | 2.0 kWe; rejects 2.0 kWt | C | LH2 |
| SUN-1 sunshield | T1 | shades ≤ 120 m² tank area | 500 kg | none (passive) | B | q_env ×0.25 while deployed (§3.12); deploy/retract 1 h; destroyed by atmosphere or stack accel > 0.2 m/s² |
| SUN-4 sunshield | T2 | shades ≤ 900 m² tank area | 2,500 kg | none (passive) | B | DEP-600-class stacks; same deployment rules as SUN-1 |
| DEP-60 "Cache" | T1 | 60 t methalox (13 t CH4 + 47 t LOX at 3.6) | 6.5 t (incl. SUN-1, 2× ZBO-90, 2× PTC-200) | 1.6 kWe | n/a (assembly) | LEO/LLO logistics node |
| DEP-600 "Reservoir" | T2 | 600 t methalox or 150 t LH2 | 62 t (incl. SUN-4, 4× ZBO-90 + 2× ZBO-20, 4× PTC-200; the 600 t methalox configuration alone carries 57 t of §3.16 tankage) | 3.0–5.5 kWe | n/a (assembly) | net-zero boiloff ≤ 1 AU when powered — LH2 mode works via §3.12 staged cooling: ZBO-90 shield interception cuts the ≈50 W leak to ≈12.5 W, under the 40 Wt of 20 K lift |

### 4.9 Cost class legend

A consumable · B mass-produced · C precision aerospace · D nuclear/exotic (regulatory event + Uranium handling) · E megaproject. Monetary values in `12-gameplay-economy-ui.md`.

## 5. Player Interaction & UI

### 5.1 Builder (VAB) Δv panel

- Per-stage readout computed exactly per §3.2: `Δv`, `Isp_eff`, wet/dry mass, t_burn, limiting propellant.
- **TWR selector**: dropdown of bodies (g_local from 03); panel shows TWR at stage start and burnout; red below context minimum (§3.7).
- Pressure context toggle: "vacuum / body sea level / custom kPa" — re-evaluates F and Isp per §3.3, so a player sees their vacuum stage die at Titan's 147 kPa before flying it.
- Boiloff forecast line per cryo tank: "%/month in [selected environment]" using §3.12 with the tank's insulation and any ZBO aboard, including the ZBO power bill cross-checked against the ship's power budget (09 panel integration).
- Warnings (hard list): LOW TWR, CONTROL AUTHORITY, NO ULLAGE PATH (pump-fed cryo stage with no RCS and no PMD), VACUUM ENGINE IN ATMOSPHERE PROFILE, SHADOW SHIELD VIOLATION (crew module outside NTR cone), EP POWER SHORTFALL (ΣP_thruster > bus power), HYPERGOL FREEZE RISK (storables + outer-system route, no heaters).

### 5.2 Flight

- Maneuver planner (owned by 01) displays burn duration from §3.2 and splits burns when t_burn > T_orbit/20.
- Engine panel per engine: throttle, gimbal lock, wear bar (w), ignition count vs rated (a wear input, not a remaining-shots counter — §3.14), health state (OK / SHUTDOWN / DEAD / DESTROYED), restart button (greyed during NTR 45-min lockout).
- NTR overlay: shadow-shield cone drawn over the ship schematic; modules outside flash during burns; cumulative dose meter (08).
- Sail control: single θ dial + auto modes "spiral out / spiral in / hold" (sets θ = ∓35° / 0°, the near-optimal tangential-thrust angles).
- Time-warp interaction: chemical burns limit warp to 4×; EP/sail/NTR-trickle integrate analytically under high warp (13 owns thresholds).

### 5.3 Logistics

- Transfer UI: dock view with drag-arrow flows, rate slider, predicted chilldown loss and transfer time; settling status indicator (SETTLED / LADs / NOT SETTLED — transfer paused).
- Depot dashboard: fill levels, Q_leak vs ΣQ_lift, net boiloff kg/day, power draw, alarm history.
- Alarm types this doc owns: BOILOFF VENTING, TANK OVERPRESSURE, PROPELLANT FROZEN, ZBO POWER LOST, ENGINE WEAR CRITICAL (w > 0.8), IGNITION FAILURE, ENERGETIC ENGINE FAILURE, SAIL THERMAL LIMIT.

## 6. Progression Hooks

| Tier | Unlocks (this doc) | Act usage |
|---|---|---|
| T0 (2049 baseline) | SRM-2, SRM-49, OMS-27, SPS-91, K-845, KV-981, H-102, ION-2, HALL-1, RCS-N10, RCS-D400, basic tanks | Act 1: expendable launch, LEO ops, first GEO/lunar probes |
| T1 | M-2256 + MV-2530 (methalox reuse — the cost-curve breaker), LND-71, HL-67, H-2280, depots DEP-60/600 + PTC-200 + ZBO line + SUN-series sunshields + PMD, ION-7, HALL-12, RCS-M2K, SAIL-86, "Mature engine" reliability upgrades | Act 1→2: reusable lift, LEO depot, lunar landings |
| T2 | NTR-73, NTR-246, LANTR option, ML-24 ISRU landers, NTR alternate propellants, SAIL-1650, depot-grade insulation everywhere | Act 2–3: lunar LOX economy, Mars cyclers, NEA mining tugs |
| T3 | HALL-100, MPD-200, VAS-200, SAIL-10K, NTR refurbishment-in-space, PTC-300L LAD couplers | Act 4–5: belt freighters, Venus aerostat support, Jupiter/Saturn tugs |
| T4 `[SPECULATIVE]` | DFD-5, FFR-43, PULSE-D megaproject | Act 5 + Endgame: outer-system clippers, interstellar precursor |

Research costs/prereq graph lives in `11-research-tech.md`; the intended spine is: methalox reuse → cryo depots → ISRU methalox (with 04) → NTR → high-power EP (gated by 09's reactors) → T4.

Reliability progression: each engine *type*, in every engine class, graduates to "Mature" (p_base and λ0 ÷4, §3.14) after 25 program-wide successful ignitions — flying cheap uncrewed missions first is mechanically rewarded.

## 7. Cross-System Interfaces

- **01-orbital-mechanics.md** — *provides to 01*: per-engine F(p_amb), ṁ, Isp(x), sail force vector law, NTR cooldown trickle accel, EP thrust under warp. *Consumes*: p_amb at vehicle, heliocentric r, g_local, T_orbit, finite-burn integration, burn-splitting planner, Earth pad→LEO budget 9,400 m/s (locked).
- **03-solar-system.md** — *consumes*: body g, atmosphere pressure profiles (Venus 50–55 km aerostat band, Titan 147 kPa), solar flux vs r, surface thermal environments for q_env calibration, Titan ambient 94 K.
- **04-resources-isru.md** — *consumes*: production of LOX, LCH4, LH2, Water, Ammonia, CO2, Xenon, Argon, Nitrogen, Uranium/HALEU, He3 [SPECULATIVE]. *Provides*: locked O/F ratios (3.6 methalox / 6.0 hydrolox / 2.36 kerolox / 1.65 hypergol), demand: ISRU must supply 3.6 kg O2 per kg CH4 (Sabatier alone yields 2.0 — remainder via water or CO2 electrolysis, MOXIE/SOEC anchor); declares new resources RP1, NTO, MMH (Earth-import).
- **05-industry-logistics.md** — *provides*: build recipes (§3.16), refurbishment costs (20% MachineParts, workshop required), solid-motor fab restriction (Earth/T3 chem plant). *Consumes*: fabrication, workshops, scrap recovery (50%).
- **06-ships-stations.md** — *provides*: all engine/tank/RCS/depot module stats, gimbal authority, energetic-failure adjacency damage trigger, shadow-shield cone geometry. *Consumes*: stack structure, CoM/lever arms, stack moment of inertia I_stack (RCS responsiveness check §3.15), docking couplers, module damage model, staging.
- **07-bases-habitats.md** — *provides*: surface refueling plumbing specs (PTC rates apply), pad boiloff environments (lunar day/night, Mars). *Consumes*: base power for heaters/ZBO/pumping.
- **08-life-support-crew.md** — *provides*: NTR dose rate law (D = 1×10⁴ Sv/h × (P_t/367 MWt) × throttle × (25 m/r)² off-cone; 0.1 mSv/h in-cone at full power, same P_t/throttle scaling — §3.10). *Consumes*: crew dose limits, crew availability for maintenance.
- **09-power-thermal.md** — *consumes*: bus electrical power for EP (P_in per string), ZBO (0.75/2.0 kWe units), tank heaters (50 W/t), pumping (0.1 kWe). *Provides*: waste heat loads — EP per family (ion/Hall 10%, VASIMR 15%, MPD 30% of P_in — §3.9), cryocoolers P_in + Q_lift, DFD-5 exports 1 MWe.
- **10-vehicles.md** — *provides*: small engines for hoppers/landers (ML-24, LND-71, RCS blocks), NIMF-style CO2-fed NTR hopper option (§3.10 table).
- **11-research-tech.md** — *provides*: unlock list per tier (§6), Mature-engine usage-based upgrade rule. *Consumes*: research gating, T4 [SPECULATIVE] placement.
- **12-gameplay-economy-ui.md** — *provides*: cost classes A–E, depot propellant as standard tradable good, regulatory event hooks (NTR class D, no NTR < 60 km Earth). *Consumes*: prices, contracts, Δv-map presentation.
- **13-architecture.md** — *consumes/provides*: analytic boiloff under warp (linear drain + empty events), deterministic RNG seed for failure rolls, flight-computer control allocation (gimbal/diff-throttle/RCS), warp limits during burns.

## 8. Failure Modes & Edge Cases

1. **Vacuum engine in atmosphere**: ignition inhibited above p_max; override → 20× wear + 2%/s engine-out roll (§3.3).
2. **Venus deep atmosphere**: F(p) ≤ 0.3·F_vac → no ignition. Surface ascent impossible by design; aerostat altitude operations only (HAVOC alignment with 07).
3. **Propellant freeze**: NTO < 262 K, MMH < 221 K, RP1 < 226 K without heater power → engines inoperable; thaw = 6 h at 100 W/t. Outer-system hypergol ships are a design error the UI warns about.
4. **Tank overpressure**: if venting is disabled (player action) boiloff gas accumulates per the §3.12 surrogate: ignition-blocking alarm at m_gas = 0.5% of tank capacity, burst at 2% of capacity — the "150% rating" event (module destroyed, 06 damage model). Default: auto-vent (propellant loss, alarm).
5. **Boiloff to empty during warp**: analytic drain schedules a TANK EMPTY event; mission planner shows "propellant at arrival" so the player sees the LH2 evaporate before launch, not after.
6. **Either-commodity depletion**: bipropellant engine shuts down benignly when one side runs dry; no damage; restart allowed if stocks restored.
7. **Ullage collapse**: settling lost mid-transfer or pre-ignition → transfer pauses / ignition aborts (no failure roll consumed).
8. **Engine-out asymmetry**: thrust-offset torque vs control authority check each tick; uncontrollable → tumble (01 integrator), player must shut down opposing engine.
9. **Energetic failure adjacency**: 5% outcome destroys engine, 50% damage roll per adjacent module; solids 40% energetic — clustering big solids next to crew is punished by math, not fiat.
10. **NTR specific**: burn with crew outside shadow cone → acute, promptly lethal dose (~10⁴ Sv/h at 25 m at full power, §3.10; 08 consequences); cooldown propellant unavailable → wear +0.25; restart inside 45-min lockout → inhibited; NTR fired < 60 km over Earth → mission-ending regulatory event (12).
11. **EP brownout**: bus power < 20% of rated string demand → thruster drop-out (alarm), thrust gap mid-spiral; planner re-plots.
12. **EP wear-out**: throughput exceeds rated → λ multiplier grows; dead thrusters on a 30-string freighter are expected attrition — carry spares (05 logistics).
13. **Sail limits**: < 0.25 AU → 1%/h area damage; atmosphere or > 0.2 m/s² acceleration with sail deployed → sail destroyed; retraction takes 1 h (plan ahead of aerobrakes).
14. **Stale solids**: > 10 years old → p_ign ×5; the failure outcome table's 40% energetic share makes old solids genuinely scary.
15. **Cold-soak restart**: cryo pump-fed engine idle > 1 h pays 5 s ṁ chilldown; players who forget see slightly less Δv than the planner promised — planner includes it when the coast is known.
16. **Depot power loss**: ZBO offline → passive boiloff resumes per §3.12 (the sunshield is passive and keeps working); a dead DEP-600 in its 150 t LH2 configuration reverts to ≈0.2%/month (≈290 kg/month: 0.25 shield × 0.25 depot MLI × 798 m² ≈ 50 W at 20 K) — slow leak, loud alarm.
17. **Transfer into warm tank**: 1.5% chilldown vent loss; repeated small transfers into warm tanks are punished vs one big settled transfer (correct incentive).
18. **Numerical edge**: throttle commands below x_min clamp to 0 (engine off) — no sub-idle hover cheese; thrust during the 5 s chilldown is exactly 0.

## 9. Open Questions

1. Should NTO/MMH be merged into a single "Hypergols" resource at fixed 1.65 ratio to cut tank micro-management, or kept separate for realism? (Lean: merge; 04 to decide.)
2. Late-game ISRU synthesis of MMH (from Ammonia + Methane) and NTO (from Nitrogen + Oxygen) — real chemistry exists (Raschig-type routes, HNO3 oxidation); is it worth a T3 chem-plant recipe or do hypergolics simply age out of the meta?
3. Plume–surface interaction (regolith scouring during lunar landings, pad damage): model as a landing-site hazard (07/10) or ignore in v1?
4. Spin-stabilization for solid kick stages (no gimbal): do we model spin-up RCS cost or hand-wave guidance for SRM-2 class motors?
5. Depot station-keeping budget: LEO drag makeup for DEP-600 (interface with 01 drag model) — included in depot power/propellant overhead or a separate Hall-thruster module requirement?
6. EP mega-clusters (Act 5 freighters may want 50+ strings): UI grouping and a per-string vs per-bank failure bookkeeping decision for 13's performance budget.
7. LANTR-style augmentation for NTR-246, and an open-cycle "afterburning" mode tradespace — worth a second mode or is one augmented engine enough?
8. Aerospike/SSTO-flavored engines were excluded (no strong flight anchor); revisit if Act 1 launch gameplay needs more variety?
9. Does H-2280 (RS-25-class) earn its slot once methalox unlocks, or should it become a premium "hydrolox sustainer" contract-unlock only? (Balance question for 11/12.)
10. Exact Mature-engine threshold (25 program-wide ignitions) needs playtest tuning against Act 1 mission cadence.
