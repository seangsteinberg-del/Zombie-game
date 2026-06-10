# 10 — Surface & Atmospheric Vehicles

Domain: everything that moves across, above, or beneath a planetary surface **without achieving orbit** — rovers (robotic, crewed-unpressurized, pressurized), construction and utility vehicles, suborbital ballistic hoppers, atmospheric craft (rotorcraft, fixed-wing, balloons, dirigibles, gliders), marine craft (boats, barges, submarines, ice-penetrating cryobots, under-ice ROVs), and the garages, docks, and maintenance loops that keep them alive.

Sibling docs: 01-orbital-mechanics.md, 02-propulsion.md, 03-solar-system.md, 04-resources-isru.md, 05-industry-logistics.md, 06-ships-stations.md, 07-bases-habitats.md, 08-life-support-crew.md, 09-power-thermal.md, 11-research-tech.md, 12-gameplay-economy-ui.md, 13-architecture.md.

---

## 1. Overview

### 1.1 What this document owns

- The **vehicle part system**: chassis classes built in the same 1 m × 1 m part-grid editor as ships (06-ships-stations.md §3.1), with vehicle-specific parts (wheels, rotors, envelopes, ballast tanks) and vehicle-specific validation rules (tip-over, ground clearance, float check).
- The **ground locomotion model**: rolling resistance, traction, slope, terrain classes, rough-terrain speed limits, and the energy-per-km formula that drives every range readout in the game.
- The **atmospheric flight model**: lift, hover power, stall speed, buoyancy — one set of formulas evaluated against each body's real atmosphere, which is why Mars flight is heartbreak, Venus cloud flight is Earth-like, and Titan flight is a golden age.
- The **suborbital hop model**: ballistic Δv on airless bodies and the driving-vs-hopping trade.
- The **marine model**: buoyancy in cryogenic hydrocarbon seas, depth pressure, drag, the Titan submarine's nitrogen-effervescence problem, and the Europa cryobot/ROV endgame.
- **Autonomy and remote operation** of vehicles, consuming the comms model owned by 13-architecture.md §3.11 and the teleoperation-productivity formula F-2 owned by 05-industry-logistics.md.
- **Vehicle bays, garages, and maintenance**, using the same condition/MTBF/spares system as 05 (explicitly: 10 confirms 05's open question — vehicles do NOT invent a parallel wear system).

### 1.2 What this document does not own

- Orbit-capable craft, landers, ascent vehicles → 06-ships-stations.md (a "hopper" that can reach orbit is a lander and belongs to 06; the boundary rule is in §3.6).
- Engine physics and propellant chemistry → 02-propulsion.md. Hoppers pull engine rows from 02's catalog.
- Power sources and storage (batteries, RTGs, fuel cells, Kilopower) → 09-power-thermal.md. Vehicles mount 09's catalog items by ID.
- Extraction tool heads (excavator drums, drills, intakes) → 04-resources-isru.md. This doc supplies the *mobile chassis* those tools mount on.
- Bodies, atmospheres, terrain sectors → 03-solar-system.md (terrain_class, slope_sigma, rock_abundance per sector; ρ(h) profiles per S-5a).
- Habitat-side dock hardware (AL-4 vehicle dock, AL-5 Titan warm-lock, AL-6 Venus rinse lock) → 07-bases-habitats.md. This doc defines the vehicle-side requirements.

### 1.3 Design intent

Vehicles are the game's *texture of place*. Orbital mechanics makes every destination cost the same kind of math; surface vehicles make every destination **feel** different: the Moon punishes you with night and dust, Mars with thin air and storms, Mercury rewards you with the terminator chase, Venus floats you, Titan hands you the keys to an aviator's paradise, and Europa makes you melt your way down into the dark. Every one of those differences falls out of the same dozen formulas fed with real planetary numbers — no per-body special-casing beyond the data tables.

---

## 2. Real-World Grounding

Every vehicle archetype below is anchored to flown hardware or a named study. Hostile fact-checkers: the load-bearing numbers are listed with their anchors here and used consistently in §3–§4.

**Rovers (flown):**
- **Apollo Lunar Roving Vehicle** (1971–72): 210 kg dry, 490 kg payload, two 36 V / 121 Ah silver-zinc primary batteries (≈ 8.7 kWh total), four 190 W (¼ hp) DC hub motors, ~13 km/h nominal (18 km/h record, Apollo 17), design range ~92 km, longest mission total 35.7 km (Apollo 17), max excursion from the LM limited to ~7.6 km by suit **walkback** capability — the walkback rule survives into the game (§3.2.6).
- **Lunokhod 1/2** (1970–73): 756 / 840 kg, Earth-teleoperated (≈ 2.6 s light RTT — canon with 05's teleop table), polonium-210 radioisotope *heater* for the 354 h lunar night, Lunokhod 2 drove ~39–42 km — the robotic distance record for four decades.
- **Curiosity / Perseverance** (899 / 1,025 kg): MMRTG 110 We (09 catalog NUK-RTG-M), top speed 4 cm/s ≈ 0.14 km/h, drives in daily bursts buffered by battery; Perseverance AutoNav: record single-sol drive 347.7 m, and up to ~700 m driven autonomously without human review across multi-sol segments — the anchor for autonomy tier A3 driving.
- **Spirit** (2009): permanently embedded in soft sulfate soil at Troy — the anchor for the immobilization failure mode. **Opportunity** (2018): killed by the global dust storm — the anchor for solar-rover storm risk. **Curiosity's wheels**: holed by sharp rocks — the anchor for terrain-dependent wheel wear.

**Rovers (studied):**
- **NASA Space Exploration Vehicle / MMSEV**: ~3 t pressurized cabin, 2 crew (4 contingency), 14-day sorties, ~10 km/h, **suitports** (canon with 08-life-support-crew.md). **JAXA/Toyota Lunar Cruiser**: ~10 t class pressurized rover, regenerative-fuel-cell powered (canon with 09's RFC).
- **NASA Glenn superelastic NiTi spring tire**: shape-memory-alloy compliant wheel, demonstrated on Mars-rover testbeds — the T1 wheel upgrade.
- **JPL "Mercury rover at the terminator"** concept studies: equatorial dawn advances at ~3.6 km/h (canon with 03 S-6c) — a rover can outrun sunrise forever. Drives the HAB-16 Mercury Crawler (07).
- **NASA AREE** (Automaton Rover for Extreme Environments, JPL NIAC 2017) and **NASA Glenn LLISSE** (~10 kg Venus surface station, SiC electronics, 60-day design target; GEER chamber ran SiC circuits 60+ days at 737 K / 9.2 MPa) — anchors for T3 Venus surface vehicles (canon with 11's VH-10).

**Rotorcraft / aircraft:**
- **Ingenuity** (Mars, 2021–24): 1.8 kg, 1.21 m coaxial rotors at ~2,400–2,700 rpm (tip Mach ~0.7 — the hard limit thin air imposes), ~350 W in hover, 72 flights, longest ~170 s and ~0.7 km, max ground speed 10 m/s. Proof that Mars flight works *and* that it buys grams of payload for kilograms of rotor.
- **Mars Science Helicopter** study (Johnson et al., NASA/JPL 2020): ~31 kg hexacopter, 2–5 kg science payload, ~10 km per flight — our T2 Mars courier anchor.
- **ARES** (NASA Langley Mars airplane study): rocket-deployed fixed-wing; stall speeds in the 60+ m/s class at Mars datum — why Mars fixed-wing is niche.
- **Dragonfly** (NASA New Frontiers, launch 2028, Titan arrival 2034): ~875 kg as-built octocopter (the 2017–19 concept papers said ~450 kg), 3.85 m airframe, eight ~1.35 m rotors, MMRTG trickle-charging a ~10 kWh-class battery (134 Ah), ~10 m/s cruise, km-class hops, >175 km planned traverse. In our 2049+ timeline it is a derelict anomaly (03 AN-39) whose salvage discounts the Titan-flyer tech node.
- **Human-powered flight on Titan**: dense air (ρ ≈ 5.3 kg/m³) + 0.14 g means a ~120 kg flyer stalls at ~2 m/s and cruises on ~72 W (V-15 at the HPF-T's declared L/D 12, §3.5.6) — about a third of what a fit cyclist sustains. Discussed seriously in the Titan literature (R. Lorenz's Titan aviation analyses; popularized by R. Zubrin). We lean into it (§3.5.6).
- **Titan Montgolfière** (JPL/CNES studies for the Titan Saturn System Mission, 2008–09): a ~10 m double-wall hot-air balloon kept aloft by nothing but an MMRTG's ~2 kWt of waste heat at ΔT of only ~5–10 K — at 94 K every kelvin of warmth buys ~1% density change (vs 0.35%/K on Earth). Cryogenic air is absurdly easy to heat-float.

**Balloons (flown):**
- **Vega 1/2** (USSR/CNES, Venus 1985): 3.54 m helium superpressure balloons, ~7 kg gondolas, floated 53–54 km (~53.5 kPa, ~300–310 K), survived 46.5 h on battery, drifted ~11,600 km in the 60–70 m/s superrotation winds. The only extraterrestrial aerobots ever flown — T0 unlock by right.
- **JPL variable-altitude Venus aerobot prototype** (Nevada flights, 2022): two-envelope design, controlled altitude excursions — the T3 VH-09 anchor (canon with 11).
- **NASA HAVOC** (Langley 2015): the crewed-airship architecture; the *habitat* side is 07's, the flight side (envelope, props, station-keeping) is ours.
- **Northrop Grumman VAMP** concept: ~450 kg inflatable flying wing for Venus clouds — T3 glider anchor.

**Hoppers:**
- **Intuitive Machines Micro-Nova "Grace" hopper**: delivered to the Moon on IM-2 (2025) but never deployed after the Athena lander tipped over — design-complete, flight-attempted kg-class propulsive hopper for PSR access. T1 anchor weight is therefore shared with Apollo LM / SLIM-class hop heritage (canon with 11's VH-03).
- **Apollo LM**: the existence proof for crewed ballistic hops; **Apollo 12 vs Surveyor 3**: landing 163 m away sandblasted Surveyor — anchor for the plume-ejecta exclusion rule.

**Marine:**
- **NASA Glenn COMPASS Titan Submarine** (NIAC Phase I/II, Oleson, Lorenz et al., 2014–15): ~1,500 kg, ~6 m, ~1 m/s cruise, 90-day / 2,000 km Kraken Mare mission, kilowatt-class Stirling radioisotope power, dorsal phased-array fin for direct-to-Earth comms, and the identified **nitrogen effervescence** problem: waste heat makes dissolved N2 bubble out of the cryogenic sea, blinding sonar — modeled in §3.7.4.
- **Cassini bathymetry**: Ligeia Mare max measured depth ~170 m, radio-transparent → methane-rich; Kraken Mare deeper (≥300 m in places), likely more ethane-rich. Liquid densities at 90–94 K: CH4 ≈ 450 kg/m³, C2H6 ≈ 650 kg/m³; sea mixtures 450–660. Game canon mean ρ_sea = 550 kg/m³ (matches 07's float rule), per-sea values in §3.7.1.
- **Philberth probes** (Greenland 1968): thermal melt probes reached 1,005 m — flown-on-Earth anchor for cryobots. **Stone Aerospace VALKYRIE**, **NASA SESAME program**, **Honeybee SLUSH** (~25 cm diameter, ~tens-of-kWt nuclear melt/drill hybrid, ~15 km Europa shell in ~3 years): T3/T4 cryobot anchors (canon with 11's VH-08). Europa ice shell 15–25 km (canon 03/11).

**Utility:**
- **NASA KSC RASSOR / IPEx** excavators (04 owns the dig heads; e_dig = 1 kWh/t canon), **NASA Langley LSMS** crane (lightweight surface manipulation system), **Honeybee TRIDENT** drill (delivered to the Moon on IM-2, 2025; demonstrated actuation but never drilled regolith after the lander tip-over — design-complete, flight-attempted; 04 catalog), terrestrial **autonomous mining haul trucks** (Caterpillar/Komatsu fleets, operating driverless since the 2010s) — the T1 robotic hauler anchor (canon with 11's VH-02).

---

## 3. Game Model

All formulas SI: mass kg (tables in t), force N, power kW (kWe/kWt per convention), energy kWh, speed m/s (UI shows km/h), g in m/s², ρ in kg/m³, angles deg. Formula IDs **V-n** for cross-reference by sibling docs. g0 = 9.80665 m/s² appears only inside Isp (02 canon); all local weights use the body's g from 03 §4.1.

### 3.1 Shared part system, chassis classes, and the Motor Pool editor

**V-0 (shared grid).** Vehicles are built in the **Motor Pool**, a mode of 06's Drydock editor: same 1 m × 1 m side-cross-section grid, same footprint/attach-node/COM math (06 §3.1), same blueprint JSON. Differences:

1. The grid is oriented travel-axis-horizontal; "down" is the body's local gravity.
2. Locomotion parts (wheel sets, track sets, rotors, floats) attach only to `bottom` nodes of chassis-frame parts; envelopes only to `top` nodes.
3. Vehicle-specific validation (V-0a..d) replaces launch validation:
   - **V-0a ground clearance**: lowest non-locomotion cell ≥ clearance stat of the locomotion set; UI warns when sector `rock_abundance` (03 S-7) implies obstacles taller than clearance.
   - **V-0b tip-over**: static stability angle `θ_tip = atan(0.5·track_width / h_COM)` must satisfy `θ_tip ≥ 2.0 × slope_sigma` of the coarsest sector the route planner is allowed to enter. Loading cargo recomputes h_COM live.
   - **V-0c float check** (marine): mean density `m_gross / V_displacement ≤ 0.95·ρ_sea`, else the blueprint is flagged sink-on-launch.
   - **V-0d power closure**: Σ continuous drive + hotel ≤ Σ source output at the *destination body's* insolation (09 evaluates).
4. Vehicles below 100 kg (drones, micro-hoppers, Vega-class gondolas) are **integrated catalog items**, not grid-built — the 1 m cell is too coarse; they occupy 1 cell as cargo. One designated exception class: **zero-g assembly drones up to 300 kg** (UTL-CDRONE) are also integrated — in zero-g there is no locomotion, clearance, or tip-over validation for the grid to add.

**Chassis classes** (the "vehicle-class chassis" shared with 06 — a vehicle is a vessel whose root part is a chassis frame):

| Class | Grid envelope | Gross mass cap | Examples |
|---|---|---|---|
| VC-1 cart | 2×2 | 0.8 t | LRV-class, Mule, drill cart |
| VC-2 light | 4×2 | 3 t | robotic science rover, light hauler |
| VC-3 medium | 6×3 | 12 t | pressurized rover, excavator carrier |
| VC-4 heavy | 10×4 | 60 t | 20 t haulers, mobile cranes, Titan barge tug |
| VC-5 platform | 16×5 | 300 t | Mercury crawler (07 HAB-16 drivetrain), module transporter |

Vehicles ride as cargo in 06's CG-BAY or on 05's Pelican-class lander decks: a vehicle consumes its grid footprint + mass; unloading needs a ramp part, a rover-crane, or 2 crew-h EVA (canon with 07 §Deploy).

### 3.2 Ground locomotion

#### 3.2.1 Resistive forces

```
V-1   F_roll  = Crr · m · g                          [N]
V-1a  p_ground = (m · g / N_sets) / A_contact        [Pa]  (per locomotion set; A_contact per set from §4.2; embedding rule §8.2)
V-2   F_aero  = ½ · ρ · Cd · A_front · v²            [N]   (negligible for ρ < 0.1 kg/m³)
        ground vehicles: A_front = occupied frontal grid cells × 1 m² (Motor Pool grid); Cd = 0.8 boxy chassis, 0.5 with the T2 fairing part (marine Cd values: §3.7.3)
V-3   F_grade = m · g · sin θ                        [N]   (negative downhill; regen recovers η_regen = 0.5 of it)
V-4   P_drive = (F_roll + F_aero + F_grade) · v / η_drive   [W],  η_drive = 0.65 (T0–T1), 0.72 (T2+)
V-5   E_km    = (F_roll + F_aero + F_grade) / (3,600 · η_drive)  +  P_hotel / v_kmh      [kWh/km]
        (first term: N → kWh/km; second: hotel power [kW] over speed [km/h])
```

**V-5a hotel power (the P_hotel rule).** `P_hotel = Σ idle loads of mounted parts`, computable for any Motor Pool build: **avionics/comms idle — the single canonical rule, referenced by V-14 as P_fix without redefinition — is 60 W for grid-built vehicles (≥ 100 kg) and 25 W for integrated sub-100 kg catalog items** (25 W is also the electronics-off hibernation floor, §3.4); pressurized-cab ECLSS 1.5 kW per 2 crew (rates owned by 08); cabin/enclosure heater load per V-11 evaluated at the route's sector temperature (09 H-8 bands); plus per-part idle loads from the mounted 04 tool-head and 09 power-item rows (those docs own their numbers; this doc owns the summation rule).

**Rolling-resistance coefficient Crr by terrain class** (03's sector terrain_class; values include soil sinkage, calibrated so the LRV reproduces its real ~92 km design range — see worked example below):

| Terrain (03 S-7) | Crr | μ (traction) | Bearing capacity [kPa] | Notes |
|---|---|---|---|---|
| Loose regolith (MARE, HIGHLAND) | 0.15 | 0.6 | 25 | lunar/asteroid default; soil mechanics per Apollo data |
| Duricrust plains (Mars default) | 0.10 | 0.6 | 80 | 5%/km sand-trap roll in DUNE-adjacent cells **only when p_ground (V-1a) > the cell's bearing capacity** (one rule with §8.2) |
| DUNE | 0.20 | 0.4 | 7 | Spirit's killer (science-rover-class loading ≈ 15 kPa exceeds 7 kPa — fails by design); speed cap 0.5× |
| ICE_PLAIN (Europa, Ganymede, Pluto…) | 0.04 | 0.25 | 500 | hard cryo-ice ≈ rock; studded wheels raise μ to 0.45 |
| CHAOS / blocky | 0.25 | 0.6 | 200 | wheel-wear ×2 (Curiosity anchor); speed cap 0.3× |
| Titan damp shoreline / tholin sand | 0.12 | 0.5 | 40 | |
| Venus surface basalt plain | 0.12 | 0.5 | 300 | T3 refractory robots only (§3.9.3 lifetime clocks); AREE/LLISSE class |
| Compacted track (after 50 vehicle passes) | 0.06 | 0.7 | 150 | tracks persist per site map |
| **Sintered road** (05/07 build item) | 0.02 | 0.8 | 600 | roads are a real infrastructure investment: 5–7× range |

Wheel-type modifiers in §4.2 multiply Crr and wear; per-set contact areas for V-1a are in the §4.2 part rows.

#### 3.2.2 Traction, slope, braking

```
V-6  Slope limit:    sin θ_max = (μ − Crr) · cos θ_max   →  θ_max = atan(μ − Crr)   [deg]   (rolling resistance carries cos θ on a slope: Crr·m·g·cos θ)
V-7  Braking:        d_stop = v² / (2 · μ · g)                                    [m]
```

Low gravity means low traction at *equal inertia*: at 12.4 m/s (≈ 45 km/h) a hauler needs 79 m to stop on the Moon (μ 0.6) vs 13 m on Earth — mass cancels in V-7. The route planner caps speed so `d_stop ≤ 0.5 × sensor range` (50 m robotic, 120 m crewed daylight, 40 m night/PSR with lights).

#### 3.2.3 Rough-terrain speed limit (the √g rule)

Wheels leave the ground when terrain-induced vertical accelerations exceed local g (the LRV's "bucking bronco" ride at 13 km/h):

```
V-8  v_max = k_t · √g    [m/s];   k_t = 2.8 (raw terrain), 4.5 (compacted), 8.0 (sintered road)
```

Examples (raw / road, km/h): Moon (g 1.62) 12.8 / 36.6; Mars (3.71) 19.4 / 55.5; Titan (1.35) 11.7 / 33.5; Ceres (0.27) 5.2 / 15.0; Earth (9.81) 31.6 / 90.3. Below g = 0.3 m/s² wheels are nearly useless (canon with 07's "hoppers preferred" at Enceladus) — see §3.6.

#### 3.2.4 Power and range — canonical worked examples

- **LRV-class open rover, Moon, loose regolith**: m = 670 kg gross (210 dry + 2 suited crew + tools). F_roll = 0.15·670·1.62 = 163 N → 0.070 kWh/km; + hotel 0.15 kW (itemized per V-5a: 60 W avionics + 90 W per-part idle from the mounted nav/comm dish and instrument pallet) at 8 km/h = 0.019 → **0.089 kWh/km**. On 8.7 kWh (×0.9 usable — primary cells run deeper than the 0.85 rechargeable-pack standard, §4): **88 km** ≈ the real LRV's 92 km design range. Calibration anchor.
- **Pressurized rover (SEV-class), Moon**: 3.4 t gross, 100 kWh solid-state pack (09 STO-SS, 0.4 t), 0.85 usable. Loose regolith: 826 N → 0.353 + hotel 1.5 kW/10 km/h = 0.15 → **0.50 kWh/km → 170 km**. On compacted track (Crr 0.06): 0.141 + 0.15 = **0.29 kWh/km → 293 km**. On sintered road (Crr 0.02): 0.047 + 0.15 = **0.20 kWh/km → 425 km**. Compacted tracks ≈ 1.7× and sintered roads ≈ 2.5× pressurized-rover range; the Act-2 lesson.
- **RTG science rover, Mars**: 1.0 t, NUK-RTG-M (110 We). After 60 W avionics (V-5a), ~50 We continuous → battery-buffered drive bursts; sustainable speed `v̄ = P_net·η/F_roll` = 50·0.65/371 = 0.09 m/s ≈ **0.3 km/h**. Duty-cycle rule (explicit): **A2 ground-in-the-loop from Earth is batch-command supervised autonomy** (one uplinked sol-plan; exempt from F-2 because there is no joystick loop — §3.8), capped at **~0.1–0.35 km/sol** — the real Curiosity/Perseverance practice (their all-time single-sol record is 347.7 m, §2). A *local* operator (Mars base, η ≈ 1) driving the same ~6 h/sol supervised window (thermal + comms constraints) gets **~2 km/sol**; an A3 AutoNav rover may drive 24/7 up to the energy cap of **~7–8 km/sol**. Reproduces why real Mars rovers crawl: RTGs buy immortality, not speed — and light-lag caps the sol.
- **10 t-payload Mars hauler**: 18 t gross, duricrust: 6.68 kN → **2.9 kWh/km** (0.29 kWh per payload-t·km; 0.16 per gross-t·km). 100 km round trip = 290 kWh: a 1.2 t battery bank, or 350 kg of Methane+Oxygen through the combustion drive (§3.3.3).

**Freight energy intensity** (V-5 per **gross** tonne, η 0.65, full-load): Moon sintered road 0.014 kWh/t·km; Mars road 0.032; Titan road 0.012 (+aero); Moon raw regolith 0.10; Mars duricrust 0.16. Per *payload* tonne, divide by the payload fraction — canonical hauler 10 t payload / 18 t gross = 0.55: Moon road 0.025, Mars road 0.057, Titan road 0.021, Moon regolith 0.19, Mars duricrust 0.29 (matches the hauler worked example above). Earth-truck sanity check: Crr 0.008 (tires, pavement) gives 0.034 kWh per gross t·km — matches real electric-truck practice (~0.05 incl. hotel/terrain). 05's route planner consumes the gross-tonne figures as link costs and applies the route's load fraction.

#### 3.2.5 Wheels vs terrain per body

| Body | Environment driver | Locomotion verdict (catalog IDs §4.2) |
|---|---|---|
| Moon / Mercury / asteroids | vacuum thermal cycling + razor dust: elastomers forbidden (real LRV/Lunokhod practice) | WHL-MESH (T0), WHL-NITI (T1); dust wear ×1.5 (07 D-ledger canon) |
| Mars | −90 °C nights, sharp rocks, sand traps | WHL-NITI best; WHL-RIGID wears ×2 on CHAOS (Curiosity anchor); battery heaters P0 (09 canon) |
| Titan | 94 K: standard elastomers/lubricants embrittle; terrain gentle | WHL-CRYO (heated hubs, metal-bellows seals); skipping the AL-5 warm-lock thaw risks seal cracks (07 canon 10%/cycle) |
| Venus surface | 737 K / 9.2 MPa: no electronics below T3, no lubricant, no battery | WHL-REFRACTORY on AREE/LLISSE-class robots only; lifetime clock, not km wear (§3.9.3) |
| Europa / icy moons | hard ice, radiation (03 field) | WHL-STUD; electronics vaults +0.3 t (canon 07); A3+ autonomy mandatory (§3.8) |
| g < 0.3 m/s² (Ceres, Enceladus, comets) | traction ∝ g → wheels marginal | drive ≤ 5 km/h or hop (§3.6); anchored tools per 04 M-6 |

#### 3.2.6 Crew range rules (ties 08)

- **Walkback rule**: a crewed *unpressurized* vehicle may not plan routes farther from a pressurized refuge than the crew's suit endurance allows walking back at 2 km/h (Apollo practice). EMU-class 8 h suit → **10 km tether-free radius** (8 h minus 3 h reserve × 2 km/h). Pressurized rovers are their own refuge; their radius is consumables (08 rates) and the rescue asset's range.
- Suitports on pressurized cabs: 0.1 kg gas + 0.1 D dust per cycle vs 0.5 kg + 1.0 D for a full airlock (canon 07/08).

### 3.3 Vehicle power options (consumes 09 catalog)

#### 3.3.1 Storage and generators

Vehicles mount 09 items unmodified: STO-LI (150 Wh/kg pack, T0), STO-SS (250 Wh/kg, T1), STO-LS (350 Wh/kg surge, T2), STO-RFC + tanked H2/O2 (2.0 kWh_e per kg reactants — the Lunar Cruiser pattern), NUK-RTG-M/-S, and for VC-4/5 platforms NUK-KP1/KP10. Li-family packs cannot charge below 273 K — the heater is a P0 load (09 canon); a rover that runs its battery flat at lunar night *and* loses heater power bricks the pack (§8).

#### 3.3.2 Recharge interfaces

- **Base umbilical** (at 07 AL-4 dock or any pad): up to pack max charge rate, 09 grid ledger pays.
- **Onboard solar**: 09's per-body insolation f_atm applies; on Titan solar is decoration (1.5 W/m² noon, 03 canon).
- **Swap pallet** (T2): 1.2 t battery modules (STO-SS, 300 kWh installed) forklift-swapped in 10 min at a garage; the logistics of charged-pallet circulation is an 05 route.

#### 3.3.3 Combustion drives (chemical kWh where batteries are too heavy)

```
V-9  Methalox ICE/turbine (T2):  1 kg Methane + 4 kg Oxygen → 15 MJ/5 kg → 0.83 kWh_mech per kg reactants  (η 0.30; CH4 LHV 50 MJ/kg, stoich O/F = 4.0)
V-10 Titan oxidizer-breather (T4 [SPECULATIVE]): carry Oxygen only, ingest ambient CH4 (~5% of the 146.7 kPa atmosphere):
       1 kg Oxygen → 12.5 MJ → 1.04 kWh_mech per kg O2 carried   (η 0.30)
```

V-9 anchor: methane/O2 ISRU ground vehicles in Mars Direct-lineage studies (Zubrin); both reactants are the 04 Sabatier economy's products. V-10 is the inverse-Earth joke made real — on Titan the *atmosphere is the fuel tank* and you carry the air. Tier honesty: oxidizer-breathing Titan engines exist only as concept-level discussion in the exploration literature (Lorenz) — no methane-aspirating, O2-carried combustion engine has ever been built or lab-demonstrated, so per doctrine V-10 hardware is **T4 [SPECULATIVE]**, not T3. The thermochemistry itself (12.5 MJ and 1.04 kWh_mech per kg O2 at η 0.30 with ambient CH4) is standard and stands. Exhaust (CO2, H2O) vents as snow; not ledgered. T3 Titan craft burn V-9 methalox (carrying both reactants — CH4 is free at the lakeshore, O2 from water ice).

RFC vs combustion vs battery rule of thumb the UI surfaces: per kg carried — battery T1 0.25 kWh, RFC reactants 2.0 kWh, methalox 0.83 kWh, Titan O2-only 1.04 kWh. RFC wins when a recharge electrolyzer awaits at both ends; combustion wins for one-way freight where propellant is dirt-cheap ISRU.

### 3.4 Thermal survival (consumes 09 H-formulas)

```
V-11 Cabin/enclosure heat loss:  Q = U · A_surface · (T_in − T_out)   [W]
       U = 0.3 W/m²K  (MLI, vacuum bodies — MLI works only in vacuum)
       U = 1.0 W/m²K  (aerogel + gas-barrier, Titan/Mars — convection defeats MLI; Huygens/Dragonfly practice)
       U = 2.5 W/m²K  (uninsulated metal hull in atmosphere)
```

- **Titan**: ΔT ≈ 200 K. A pressurized cab (A ≈ 30 m²) loses ~15 kW uninsulated (U 2.5), ~6 kW aerogel-insulated (U 1.0) — worked example used in §4 stats; the 6 kW aerogel figure sizes pressurized-cab heater loads, which RTG/Stirling/combustion vehicles cover from waste kWt. On Titan **waste heat is life**: RTG/Stirling/combustion vehicles heat themselves; battery vehicles pay V-11 from the pack. Dragonfly anchor: its MMRTG's ~2 kWt waste heat warms the avionics vault.
- **Lunar night (354 h)**: parked vehicles choose a strategy: (a) survival heater from RTG (Lunokhod's Po-210 pattern — any NUK item's kWt suffices); (b) battery hibernation: P_surv = V-11 with electronics-off floor 25 W + heater; (c) park on a **thermal wadi** (09 STO-WADI: sintered thermal mass holds parked vehicles ≥ **~245 K** through the 354 h night on a ~2 kWt bleed — NASA Glenn/PNNL thermal-wadi studies (Balasubramaniam & Wegeng, NTRS 20100015637), which size wadis to keep rover hardware at ≈ 243 K against the ~95 K unaided night surface; 245 K clears the 233 K electrolyte-freeze damage line (§8.3), and the pack's own trickle heater bridges the last ~30 K to the 273 K charge threshold (§3.3.1)); (d) garage it (07 bay = grid node, no exposure).
- **Venus surface / Mercury noon**: endurance clocks per 09 H-5, not steady-state: pre-T3 vehicles get 2–8 h (Venera 13: 127 min anchor, canon 03); T3 SiC-electronics vehicles (VH-10) get LLISSE-class 60-day clocks between refurbishments. Mercury twilight-band ops avoid the clock entirely (terminator chase).
- Operating bands: every part inherits 09 H-8 `[T_min_op, T_max_op, T_survival]`; the route planner refuses routes whose sector T (03 S-6c) violates any mounted part's band unless an enclosure part covers it.

### 3.5 Atmospheric flight

The same four formulas, per-body data from 03 §4.1 / S-5a. No per-body hacks: feasibility differences are emergent.

#### 3.5.1 Core formulas

```
V-12 Lift:            L = ½ · ρ · v² · S · C_L                       [N]; level flight L = m·g
V-13 Stall speed:     v_stall = √( 2·m·g / (ρ · S · C_Lmax) )        [m/s]; C_Lmax = 1.4 (T0–T2), 1.8 (T3 high-lift)
V-14 Hover power:     P_hover = (m·g)^1.5 / ( η_h · √(2 · ρ · A_disk) )   [W]
       η_h = 0.29 T0–T1 (calibrated against Ingenuity, below — first-generation small rotors, low figure of merit × motor/ESC chain), 0.42 T2+ (MSH/Dragonfly-class design FoM ~0.6–0.7 × drive chain), + P_fix (avionics idle per V-5a: 25 W integrated sub-100 kg items, 60 W grid-built — V-5a owns the rule)
       calibrated: Ingenuity (1.8 kg, A_disk = π·0.605² = 1.15 m² for the 1.21 m rotors, ρ 0.016, g 3.71) → ideal induced (m·g)^1.5/√(2ρA) = 90 W; /0.29 ≈ 310 W induced + 25 W P_fix ≈ 335 W ✓ matches ~350 W-class telemetry
V-15 Cruise power:    P = m·g·v / ( (L/D) · η_prop )                 [W];  L/D 10 (T0–T1), 15 (T2), 20 (T3 clean); η_prop 0.75
V-16 Rotor tip-Mach cap: v_tip = ω·R ≤ 0.75 · a_sound (03 per-body a; Mars a ≈ 240 m/s → big slow-turning rotors; Titan a ≈ 195 m/s, irrelevant in practice)
```

#### 3.5.2 Per-body feasibility table (the doc's centerpiece)

Indices normalized to Earth sea level (ρ 1.225, g 9.81): hover-power index = (g^1.5/√ρ)ₙ — specific power to hover per kg; stall index = (√(g/ρ))ₙ — how fast you must fly to stay up.

| Body / station | ρ [kg/m³] | g [m/s²] | Hover index | Stall index | Verdict |
|---|---|---|---|---|---|
| Earth sea level | 1.225 | 9.81 | 1.00 | 1.00 | baseline |
| **Mars datum** | 0.016 (03/04 canon) | 3.71 | **2.0** | **5.4** | hover costs 2× Earth per kg *and* rotors hit tip-Mach; fixed-wing stalls at airliner speeds. Gram-payload scouts only; ceiling: ρ(h) falls by e per +11 km (scale height; halves per ~7.7 km) → no highland flight |
| Mars, −7 km basins (Hellas) | 0.028 | 3.71 | 1.5 | 4.1 | basin-hugging courier routes (scale-height rule: 0.016·e^(7/11) ≈ 0.030; measured Hellas-floor 0.027–0.030 — canon 0.028) |
| **Venus 54 km** | 1.05 | 8.87 | 0.93 | 1.03 | Earth-like flight, period. Balloons trivial, props efficient; the cloud layer is an aviation habitat |
| Venus surface | 64.8 | 8.87 | 0.12 | 0.13 | aerodynamically easy, thermally lethal: T3 robotic only |
| **Titan surface** | 5.3 (03 canon) | 1.35 | **0.025 (≈1/40)** | **0.18** | flight is ~40× cheaper per kg than Earth; stall speeds are jogging speeds. Planes & dirigibles are the *primary* logistics layer |
| Earth 10 km alt | 0.41 | 9.81 | 1.7 | 1.7 | (for Earth-ops completeness) |
| Moon / Mercury / vacuum | 0 | — | ∞ | ∞ | no flight; hoppers (§3.6) |

Titan in one line: **wings lift 4.3× more per m² at 1/7 the weight — never build a road on Titan when you can build a runway, and never a runway when a mooring mast will do.**

#### 3.5.3 Buoyant flight

```
V-17 Net lift:  m_payload = V_env · (ρ_atm − ρ_gas) − m_envelope ;  ρ_gas = P·M_gas/(R·T_gas), R = 8.314 J/mol·K
       envelope areal density: 0.20 kg/m² (T0 fabric), 0.10 (T2), 0.06 (T3 film), 0.02 (T2 Mars-only superpressure thin film — JPL Mars-aerobot Mylar-class film studies; fragile, instrument-class loads only)
```

Lifting-gas table (computed with V-17 at each station's P, T from 03):

| Site | ρ_atm | H2 lift [kg/m³] | He lift | Breathable-air lift | Hot-gas lift (ΔT +50 K ambient gas) |
|---|---|---|---|---|---|
| Titan surface (146.7 kPa, 94 K) | 5.3 | **4.9** | 4.6 | **warm (290 K) habitat air: ≈ 3.5** (ρ_air = 1.77 at 146.7 kPa/290 K — one of Titan's best lifting gases, a standard Titan-literature result; reconcile with 07. Cold air is irrelevant: O2 condenses at Titan ambient, and ambient-T air would sink anyway, M 29 > N2/CH4 mix M ≈ 27.4) | 1.8 (generic ΔT +50 K reference only; an MMRTG sustains just ΔT ≈ 5–10 K → 0.27–0.55 kg/m³ — see MGF-T §4.6) |
| Venus 54 km (≈60 kPa, 300 K — VIRA interpolation at 54.0 km, **canonical P per 03**; ideal-gas check: ρ = PM/RT = 60·43.5/(8.314·300) ≈ 1.05 ✓. Vega telemetry read ~53.5 kPa at its 53–54 km float, consistent within the band) | 1.05 | 1.00 | 0.95 | **0.35–0.42 across the band** (canon with 06: habitat sizing uses the conservative 0.35 ≈ ⅓ of H2 lift) | 0.15 |
| Mars datum (0.61 kPa, 210 K) | 0.016 | 0.015 | 0.014 | — | 0.003 |
| Earth SL | 1.225 | 1.14 | 1.06 | — | 0.18 |

Consequences the game leans on: a 10 t-payload Titan dirigible needs only ~2,050 m³ of Hydrogen — a slender 40 m × 10 m ellipsoid (DIR-T; for size-feel only, the same volume as a 16 m sphere: hangar-sized, not Hindenburg-sized; and H2 is *inert* in a methane atmosphere with no free O2 — the fire risk is reversed and absent). The same payload on Mars would need 670,000 m³ — Mars ballooning is science-instrument-only (superpressure, Vega-style, 04's intake band). On Venus, habitats are their own balloons (07's domain); our vehicles are the tugs, gliders, and instrument drops around them.

**Balloon altitude control & drift**: superpressure = fixed altitude band; Montgolfière/variable-altitude (VH-09) trade heat/ballast gas for ±5 km excursions at 0.5 m/s vertical. Horizontal motion = wind vector per altitude band (03 owns winds; canonical values: Venus 54 km zonal 65 m/s — Vega's 11,600 km in 46 h; Titan surface ≤ 1 m/s, low-altitude ~2–5 m/s prograde; Mars 5–30 m/s gusts). Powered dirigibles add airspeed from V-15 with the envelope's Cd ≈ 0.05 and frontal area (DIR-T's 40 × 10 m ellipsoid: ~78 m² frontal — the slender hull, not a sphere, is what makes the drag number work); the 10 t Titan dirigible cruises 8 m/s on **7.8 kW** (≈ 0.027 kWh/t·km — the cheapest bulk transport in the game short of 05's mass driver).

**Mars wind myth, dispelled in-game**: dynamic pressure q = ½ρv² at a 30 m/s Mars gale = 7 Pa (Earth equivalent: a 3.4 m/s breeze). Wind never tips a Mars vehicle; it *does* lift dust (03 storms) and kill solar output (09).

#### 3.5.4 Flight in the 2D top-down world (honest abstraction)

Altitude is a scalar band, not a rendered dimension: `ALT ∈ {0 surface, 1 low ≤ 200 m, 2 cruise, 3 high/float}`. Per-body band altitudes (ρ, T, and wind are sampled from 03 S-5a at the band midpoint):

| Body | ALT 1 low | ALT 2 cruise | ALT 3 high/float |
|---|---|---|---|
| Mars | ≤ 200 m AGL | 200 m – 1 km AGL | — (ρ too low; band does not exist) |
| Titan | ≤ 200 m | ~1 km | 3–8 km (balloons/dirigibles) |
| Venus | — (no flight below the 45 km planner clamp; 42–45 km is a warning band, §8.11) | 50–56 km | 56–62 km |
| Earth | ≤ 200 m | 1–3 km | 8–12 km |

Aircraft execute planned routes on the map at v_cruise with the V-14/V-15 energy ledger; takeoff/landing are events with terrain checks (landing cell must satisfy slope ≤ 5° and rock_abundance ≤ wheel clearance unless VTOL). Under time warp, flights integrate analytically like drives (13 contract). Direct control (§5) is available in real time only.

#### 3.5.5 Mars rotorcraft specifics

Battery-only flight profile (Ingenuity pattern): flight energy E = P_hover-equivalent × t; the T0 scout (2 kg) flies 3 min and recharges for a sol on 0.4 m² of panel. The T2 courier (31 kg, MSH anchor) hovers on ~6 kW (V-14: A_disk 7.7 m²), flies 8 min / 10 km hops carrying 4 kg — the canonical use: sample ferry, sensor drops, scouting routes for ground convoys through CHAOS terrain. **No Mars cargo aviation, ever** — V-14 at 200 kg payload demands >100 kW continuous and rotor disks beyond packaging; the tech tree deliberately offers nothing (hostile reviewers: this is the honest answer).

#### 3.5.6 Titan aviation (lean in)

- **Human-powered flyer** (T3 morale/utility item): 120 kg system (suited crew + 30 kg wing, S ≈ 8 m², C_Lmax 1.8), v_stall 2.1 m/s, cruise 4 m/s (14 km/h) on **~72 W** of pedaling (V-15 with a declared per-craft L/D override of 12 — strapped-on wings and a dangling suited human are draggier than the canon tier airframes; the override is a row stat, §4.5) — a fit human sustains 200 W. Mechanically: an EVA with a 14 km/h self-powered flight mode and a stall-crash roll only on exhaustion (08 fatigue) — the "you can fly on Titan with strapped-on wings" promise, kept, with the real numbers shown in the tooltip.
- **Cargo plane** (T3): 8 t gross / 5 t payload, S = 60 m²: v_stall 6.1 m/s (V-13, C_Lmax 1.8 T3), cruise 40 m/s on 28.8 kW shaft (V-15, L/D 20 T3 clean; installed 36 kW for climb/headwind margin — the catalog quotes both) → 0.04 kWh per payload-t·km; 600 m ice runways (compacted class).
- **Dirigible** (T2, before runways exist): §3.5.3 numbers; moors to a mast part at any base.
- Rotorcraft (Dragonfly-class, VH-06): the do-everything Titan utility aircraft; hover index 1/40 means a 450 kg craft hovers on ~3.2 kW (V-14: A 11.5 m², η_h 0.42; ideal induced power 1.36 kW — consistent with real Dragonfly hover estimates of ~2–2.5 kW shaft at FoM ~0.6–0.7) — battery + RTG trickle exactly as Dragonfly does it.

### 3.6 Suborbital hoppers (airless bodies)

#### 3.6.1 The hop Δv formula

Minimum-energy ballistic arc between surface points separated by ground distance d on an airless body (radius R_p, GM μ from 03; Ψ = d/R_p in radians):

```
V-18  v_launch = √( (μ/R_p) · 2·sin(Ψ/2) / (1 + sin(Ψ/2)) )      [m/s]
V-19  Δv_hop  = 2 · v_launch · 1.10        (boost + propulsive landing; 10% gravity/steering margin)
V-18a short-hop limit (d ≪ R_p):  v_launch → √(g·d) ;  Δv_hop ≈ 2.2·√(g·d)
```

(V-18 limits check: Ψ→π gives v = √(μ/R_p) = surface-circular velocity ✓; small Ψ reduces to the flat-ground 45° solution ✓.)

**Hop Δv table** (V-19, computed):

| d | Moon (g 1.62) | Mercury (3.70) | Ceres (0.27) | Europa (1.31) | Enceladus (0.113) |
|---|---|---|---|---|---|
| 1 km | 89 m/s | 134 | 36 | 80 | 23 |
| 10 km | 281 | 424 | 114 | 252 | 74 |
| 100 km | 873 | 1,318 | 339 | 781 | 218 |
| 500 km | 1,851 | 2,830 | 643* | 1,650 | — (>¼ circumf.; orbit instead) |
| 1,000 km | 2,458 | 3,830 | — (>¼ circumf.; orbit instead) | 2,177 | — (>¼ circumf.; orbit instead) |
| orbit-and-land (2× from 03) | ≈ 3,800 | ≈ 6,100 | ≈ 720 | ≈ 2,900 | ≈ 340 (2 × √(gR) = 2 × 169 m/s; ~370 with the 10% margin) |

*Asterisk: approaching the orbital-velocity asymptote — hop and orbit costs converge; UI suggests switching to a lander (06). Cells beyond ¼ circumference (d > πR_p/2) are struck uniformly — Ceres ≥ 1,000 km and Enceladus ≥ 500 km (πR/2 ≈ 396 km) — orbit instead.

**Boundary rule (10 vs 06)**: a craft whose flight plan exceeds Ψ = π/2 (¼ circumference — the same threshold as the table's struck cells) or reaches local orbital velocity is a *lander/ascent vehicle* — 06's domain, 01's conics. Hoppers never get orbit lines; they get a range ring.

#### 3.6.2 Propellant and the drive-vs-hop trade

Propellant per hop from 02's rocket equation with the mounted engine. Engines are 02 catalog rows cited by ID — never local stats (02 §7 provides exactly this set to 10: ML-24, LND-71, and the RCS blocks): **ML-24 "Gopher"** pressure-fed methalox lander, **Isp 320 s vac → v_e = 3,138 m/s** — the catalog ceiling for a lander engine (even pump-fed Raptor 2 is only 347 s vac; no 350 s-class pressure-fed methalox exists to cite) — or storable NTO/MMH for PSR cold: **RCS-D400** Draco blocks at 300 s (OMS-27's 316 s is the storable Isp ceiling, but its fixed-throttle 26.7 kN is an orbit-insertion engine, not a hop-landing one). Example: 5 t landed-mass cargo hopper on ML-24, Moon, 200 km hop: Δv 1,219 m/s → 5·(e^(1219/3138) − 1) ≈ 2.4 t methalox one way.

Energy honesty: that 2.4 t of ISRU methalox cost ≈ 7.1 kWh/kg (04 canon) ≈ **16,900 kWh**; driving the same 5 t *gross* 200 km on a road costs ≈ 14 kWh (§3.2.4; on a payload basis — 5 t of payload in a 0.55-payload-fraction hauler — ≈ 0.025 × 5 × 200 = 25 kWh). **Hopping is ~700–1,200× more energy-expensive than driving** — it buys *time* (200 km in 9 min vs 6 h) and *access*. Decision rules the planner surfaces:

1. **Terrain**: route crosses CHAOS/impassable sectors or PSR crater walls → hop.
2. **No road, low g**: g < 0.3 m/s² (wheels marginal, V-8) → hop by default (Ceres/Enceladus/comet ops; canon with 07).
3. **Distance**: one-way > 3× vehicle range → hop or build infrastructure.
4. **Tempo**: rescue, sample-return windows, anomaly events (11 DSC-03 skylight survey is hopper-gated).

#### 3.6.3 Plume ejecta rule

Propulsive landing/launch off-pad sandblasts the neighborhood (Apollo 12 → Surveyor 3 at 163 m anchor): within **200 m**, exposed equipment takes an abrasion event (condition −2%, solar −1% permanent per event, 09 dust ledger +1); within 50 m, each exposed unrated part rolls 30% for a −15% condition hit per launch/landing event. Landing pads (07 build item) suppress the rule. Hop-frequency gameplay therefore demands pad infrastructure — intentional.

### 3.7 Marine vehicles

#### 3.7.1 Buoyancy and seas

```
V-20  F_B = ρ_sea · V_disp · g    [N];   float ⇔ m_gross ≤ ρ_sea · V_hull · 0.95  (V-0c)
```

Titan sea table (canon mean ρ_sea = 550 kg/m³ per 07; per-sea values from Cassini composition evidence):

| Sea | ρ [kg/m³] | Max depth | Note |
|---|---|---|---|
| Ligeia Mare | 520 | 170 m (measured) | methane-rich (radio-transparent, Cassini) |
| Kraken Mare | 580 | ≥ 300 m (est.) | ethane-enriched; the charter's ~570 kg/m³ class |
| Ontario Lacus | 600 | ~50 m | ethane/evaporitic shallows |

Designing for ρ 520–600 (vs water's 1,000) means Titan hulls must be ~45% *less* dense than Earth boats: large displacement volumes, thin pressure-tolerant shells — the NASA Titan Sub's long thin 6 m form. Cargo rule: payload density above ρ_sea must be offset by hull volume; the barge catalog entry carries 100 t in a 350 m³ hull.

#### 3.7.2 Depth, pressure, hulls

```
V-21  P(d) = P_surf + ρ_sea · g · d     [Pa]   (Titan: 146.7 kPa + 0.74 kPa per m — 300 m ≈ 3.7 atm total: trivial)
```

Hull classes: H1 = 0.5 MPa (any Titan depth; the design driver is 94 K, not pressure), H2 = 5 MPa, H3 = 40 MPa (Europa under-ice: ice-shell base at 25 km ≈ ρ_ice·g·h = 920·1.315·25,000 ≈ **30 MPa**), H4 [out of v1 scope] = abyssal Europa. Exceeding rating: leak events at 1%/min per 10% overpressure.

#### 3.7.3 Drag and propulsion

V-2 with wetted-area Cd: streamlined sub 0.10, boat hull 0.15, barge 0.4. Marine propulsive efficiency (screws/thrusters — V-4's η_drive is ground-drivetrain-only): **η_prop,marine = 0.60 (T2), 0.65 (T3)**; `P_prop = F·v / η_prop,marine`. Worked: Titan Sub (frontal 1.1 m², Cd 0.10) at 1.0 m/s: F = 30 N → P_prop = 30/0.60 ≈ 50 W (T2 prop value, conservative) + hotel ≈ 280 W = 330 W, covered by the Stirling RIG bank (NUK-RTG-S ×3, ≈ 330 We — matches the SUB-T catalog row; the units' ~6 kWt rejection also holds the ~12 m² hull's ≈ 2.4 kW V-11 loss) — consistent with the NIAC design's kW-class budget and 90-day/2,000 km legs. Speed scales as P^⅓: tripling power buys 44% speed; submarines are patient.

#### 3.7.4 Cryogenic-sea special rules (the NASA-study problems, gamified)

1. **Nitrogen effervescence**: hull skin heat flux > 0.5 kW/m² wetted boils dissolved N2 out of the sea: sonar/survey instruments −50%, drag +20%, buoyancy control unstable (±2% V_disp noise). Mitigation: dorsal heat-rejection fin above the waterline (the real Titan Sub's solution — part SUB-FIN, also the comms mast). Direct anchor: COMPASS study's effervescence analysis.
2. **Cryo materials**: elastomer seals forbidden (94 K); metal bellows and dry bearings only (T3 parts) — else seal-crack events 10%/dive (mirrors 07's AL-5 rule).
3. **Methane weather**: sea state 0–2 normally (Cassini saw mirror-flat seas; mm–cm waves); seasonal storm events (03) raise to state 4: surface craft speed ×0.5, capsize roll for boats (10%/h for VC-1, 3%/h for VC-2), subs dive below 10 m and ignore it.
4. **Shore interface**: sea-shore site cells host the Submarine Dock (07 canon) and Sea Pumps (04); boats beach-launch from a ramp vehicle-part.

#### 3.7.5 Europa cryobot and under-ice ROV (endgame, VH-08)

Melt-probe descent (Philberth/SLUSH physics):

```
V-22  E_melt_vol = ρ_ice · (c̄_p·ΔT + L_f) · k_loss   [J/m³]
        ρ_ice 920, c̄_p ≈ 1.5 kJ/kg·K (100→273 K mean), ΔT ≈ 173 K, L_f 334 kJ/kg → 546 MJ/m³ ideal
        k_loss = 3.0 (lateral conduction + tether/refreeze overhead; Philberth-efficiency class)
V-23  v_descent = P_t / (A_probe · E_melt_vol)        [m/s]
```

Catalog cryobot (Ø 0.26 m, A 0.053 m², dedicated 100 kWt fission heat source per 09): v = 100,000/(0.053·1.64×10⁹) W/(m²·J/m³) ≈ **4.2 m/h ≈ 100 m/day → 15 km shell in ~150 days; 25 km in ~250 days**. Honesty note: SLUSH projects ~3 years for 15 km on ~40 kWt-class heat — our production T4 probe is simply hotter; the scaling, not the schedule, is the anchored part. Comms: no teleop through ice — the probe deploys frozen-in RF/acoustic repeater pucks every 500 m (SLUSH architecture); bandwidth tiny, **A3 autonomy mandatory** below the surface (§3.8). On breakthrough, the probe releases the **under-ice ROV** (H3 hull, 30 MPa interface, NUK-RTG-S power, 0.5 m/s): the endgame science vehicle (11's DSC ocean arcs). Planetary-protection sterilization is a build-cost multiplier (12 owns the contract/ethics flavor), not a mechanic.

### 3.8 Autonomy, comms, and control (consumes 13 §3.11 + 05 F-2)

Light-lag is physics: one-way `τ = path/c` along the 13-comms relay graph; RTT = 2τ. Vehicles add **no new comms model** — only control-mode consequences:

| Mode | Requires | Effective capability |
|---|---|---|
| CREWED | crew aboard (08) | full v_max, all tasks, no link needed |
| TELEOP (A2 joystick, 05 ladder) | comms link, operator (crew or Earth-hire per 05) | speed/work ×η_teleop = 1/(1 + RTT/60 s) (05 F-2, driving T_atom); UI refuses standing ops below η = 0.2 (canon 05) |
| A2 BATCH (ground-in-the-loop) | comms link at sol-plan uplink/downlink only; A2 kit | supervised autonomy on uplinked plans — **exempt from F-2** (no joystick loop) but drive capped at **0.35 km/sol** (Perseverance single-sol record anchor, §3.2.4); tool work per 05's batch rules |
| AUTONAV (A3, T3, 11 IN-09) | none while executing; link at dispatch/arrival | 0.5 × v_max, 24/7, handles known terrain; exceptions (stuck, breakdown, novel obstacle) halt and page (05 exception queue) |
| A4 (05 ladder, endgame) | 05 autonomous-complex node; no link needed | ledger-mode operation only (§8.15): no per-vehicle events, exceptions handled site-locally — endgame fleets (§6) are never simulated per-vehicle |
| CONVOY | leader (any mode) | followers at leader's effective speed; 1 leader per 5 followers |

Worked η_teleop (13's RTT checks): Moon from Earth RTT 2.56 s → 0.96 (Lunokhod proved it); Mars best 6.2 min → η 0.14, *below the 0.2 refusal line* — joystick TELEOP from Earth is never available at Mars; Earth-run Mars vehicles fall back to A2 BATCH (≤ 0.35 km/sol, §3.2.4), the misery that drives the Act-3 push to A3; Mars worst 44 min → even batch turnaround degrades toward one plan per sol; Saturn ~160 min → A3 or crewed, full stop. Relay occlusion (farside, sea-horizon, under-ice) pauses TELEOP exactly per 13's event windows; vehicles **safe-halt** on link loss (aircraft execute return-to-base; balloons keep drifting — they don't halt, see §8).

### 3.9 Wear, maintenance, garages

#### 3.9.1 Condition system — 05's, verbatim

Vehicles use 05's condition C ∈ [0,1], MTBF, and spares-split mechanics unchanged (this closes 05's open question #5-Q "vehicles must confirm"). Vehicle-specific *wear drivers* feed C:

```
V-24a wheels/tracks:   ΔC per 100 km     = base (wheels 0.4%, tracks 0.6%) × terrain_mult × dust_mult   (tracks: terrain_mult capped at 1.5)
V-24b rotors:          ΔC per 10 flight-h = 0.3% × dust_mult                 (no terrain term)
V-24c hulls:           ΔC per 10 dive-h   = 0.2% × sea_state_mult            (state 0–2: ×1.0; state 4: ×2.0; effervescence-active dives: ×1.2)
V-24d thermal cycling: ΔC += 0.1% per survival-band night cycle (Mars/Moon) — additive, applied independently of V-24a–c
        terrain_mult: road 0.5 · regolith 1.0 · DUNE 1.5 · CHAOS 2.0 (Curiosity anchor) · ICE 0.8 · all unlisted terrain classes (incl. Titan damp shoreline/tholin sand, Venus basalt) 1.0
        dust_mult: Moon 1.5 (glass-sharp fines) · Mercury 1.5 (lunar-like razor fines) · Mars 1.0 · Titan 0.7 · Venus-cloud 2.0 acid (07 acid-ledger canon) · icy moons 0.8 · all other bodies 1.0
```

Venus *surface* vehicles ignore V-24 and run 09 H-5 endurance clocks instead (§3.4).

#### 3.9.2 Service

Restoring C consumes spares per 05's recipes; rule of thumb surfaced in UI: full overhaul = MachineParts 3% + Electronics 0.5% of vehicle dry mass. **In a garage bay**: full rate. **Field repair** (crew EVA or A2 robot): ×3 spares, ×2 time, weather-gated. No garage on site → fleets decay; intentional infrastructure pull.

#### 3.9.3 Garage/bay modules (vehicle-side spec; 07 owns the habitat modules)

| Bay | Fits | Functions |
|---|---|---|
| VEH-PAD (T0, 0 t — marked regolith) | any | park, umbilical charge; full exposure (V-24 thermal term applies) |
| VEH-BAY-S (T1, pressurizable option) | VC-1/2 | service, dust wash (−5 D per 07 ledger), thermal shelter |
| VEH-BAY-L (T2) | VC-3/4 | + part swap (Motor Pool edits on-site), battery-pallet swap |
| SUB-DOCK (T3, shoreline) | boats/sub | hull thaw (AL-5 logic), O2 bunkering, sonar data offload |
| MAST (T2) | dirigibles | mooring, gas top-off, cargo crane |

Airlocks/dust/cryo/acid cycles between vehicle and habitat use 07's AL-4/AL-5/AL-6 rules — the vehicle just declares its dock-collar port (standard on pressurized cabs T2+).

---

## 4. Content Catalog

Stats at nominal load on the named body; E_km from V-5; range at 0.85 usable energy (the canonical rechargeable-pack fraction; primary-cell packs use 0.9 — the LRV exception). "Pwr" = mounted 09 item(s). Anchors abbreviated (full list §2). Tech node column = 11's VH/IN nodes.

### 4.1 Rovers & ground chassis

| ID | Name | Tier (node) | Class | Dry t | Pwr | Crew | Speed (raw/road) | E_km nominal | Range | Anchor |
|---|---|---|---|---|---|---|---|---|---|---|
| RVR-SCOUT | Robotic science rover | T0 (VH-00) | VC-2 | 1.0 | NUK-RTG-M + 2 kWh buf | 0 | 0.3 km/h avg (≤ 0.35 km/sol at A2 BATCH from Earth; ~2 km/sol local-operator A2; ~7 km/sol energy cap at A3 — §3.2.4 duty-cycle rule) | 0.37 kWh/km (Mars) | ∞ (RTG) | Curiosity/Perseverance |
| RVR-LRV | Open crew rover | T1 (VH-01) | VC-1 | 0.21 | 8.7 kWh primary AgZn (T0 cells) or STO-LI 0.06 t | 2 | 13/37 km/h (Moon) | 0.089 kWh/km | 88 km | Apollo LRV / Artemis LTV |
| RVR-MULE | Rover-manipulator | T2 | VC-1 | 0.45 | STO-LI 15 kWh | 0 | 8/24 km/h | 0.06 | 200 km | = 05's bot_mule (single shared stat row; 05 owns its labor math) |
| RVR-PRESS | Pressurized rover "sortie cab" | T2 (VH-04) | VC-3 | 3.0 | STO-SS 100 kWh; RFC option | 2 (4 cont.) | 10/30 km/h (Moon) | 0.50 raw / 0.29 track / 0.20 road | 170/293/425 km | NASA SEV; Lunar Cruiser (RFC) |
| RVR-HAUL10 | Hauler, 10 t bed | T1 (VH-02) | VC-4 | 8.0 | swap-pallet 300 kWh (1.2 t STO-SS) or V-9 combustion | 0 | 15/40 km/h (Mars) | 2.9 kWh/km full | ~90 km/pallet (0.85 usable) | autonomous mining trucks |
| RVR-HAUL40 | Hauler, 40 t bed | T2 (VH-02) | VC-4 | 22 | V-9 combustion (1.2 t reactants/100 km Mars) | 0/1 | 12/35 km/h | 9.6 full | by tankage | same |
| RVR-CRAWL | Mercury crawler drivetrain | T3 | VC-5 | 30 (chassis; = 07 HAB-16) | NUK-KP10 ×3 | (carries 2 modules) | 0.5–5 km/h | 25 kWe cont. @ 3.7 km/h, 60 t gross — **assumes the prepared/compacted terminator corridor, Crr 0.06** (raw regolith Crr 0.15 → ≈ 48 kWe, out of budget); 80 kWe peak = 3.7 km/h on a 10° grade on that corridor | ∞ (fission) | JPL terminator-rover studies; spec provided to 07 |
| RVR-VENUS | Venus surface crawler | T3 (VH-10) | VC-2 | 1.8 | wind turbine (AREE-class: ~40 W mean, 250 W gust, buffered in a mechanical spring/flywheel store — no battery survives 737 K) + SiC avionics | 0 | 0.3 km/h burst (V-4 closes: 222 W on Venus basalt, Crr 0.12) / ~0.05 km/h mission avg on the 40 W mean | clock-limited | 60-day clock | AREE + LLISSE/GEER |

### 4.2 Ground locomotion parts (multiply Crr / wear per §3.2; A_contact and clearance feed V-1a / V-0a)

| ID | Type | Tier | Crr mult | Wear mult | A_contact/set [m²] | Clearance [m] | Mass/set [kg] | Max load/set [t] | Where |
|---|---|---|---|---|---|---|---|---|---|
| WHL-MESH | wire-mesh wheel | T0 | 1.0 | 1.0 | 0.05 | 0.35 | 12 | 0.4 | vacuum bodies (LRV piano-wire anchor) |
| WHL-RIGID | machined metal wheel | T0 | 1.1 | 2.0 on CHAOS | 0.04 | 0.30 | 25 | 0.6 | Mars robotic (Curiosity anchor) |
| WHL-NITI | superelastic NiTi spring tire | T1 | 0.85 | 0.6 | 0.06 | 0.35 | 20 | 0.8 | everywhere vacuum/Mars (NASA Glenn) |
| TRK-STD | tracks | T1 | 0.8 soft / 1.3 hard | 1.5 | 0.50 | 0.25 | 90 | 5.0 | DUNE, soft regolith, VC-4/5 platforms; speed cap 15 km/h |
| WHL-CRYO | heated-hub cryo wheel | T2 | 1.0 | 1.0 (Titan) | 0.06 | 0.35 | 30 | 0.8 | Titan (94 K bearings, metal bellows) |
| WHL-STUD | studded ice wheel | T2 | 1.0 | 1.0 | 0.04 | 0.30 | 28 | 0.8 | ICE_PLAIN; μ 0.25→0.45 |
| WHL-REFR | refractory wheel, dry bearings | T3 | 1.3 | clock-based | 0.03 | 0.25 | 40 | 0.6 | Venus surface (AREE) |

V-1a worked checks (the numbers the §3.2.1 table quotes): the 1 t science rover on six WHL-RIGID sets → p_ground = 1,000·3.71/6/0.04 ≈ **15.5 kPa** — the "science-rover-class loading ≈ 15 kPa" of the DUNE row (exceeds DUNE's 7 kPa bearing, fails by design; clears duricrust's 80 kPa). The LRV on four WHL-MESH: 670·1.62/4/0.05 ≈ 5.4 kPa ≪ 25 kPa ✓. Heavy haulers on wheels exceed duricrust bearing (18 t gross on six NiTi sets ≈ 185 kPa): they mount TRK-STD (18 t on four track sets ≈ 33 kPa) or keep to compacted/sintered corridors — consistent with §3.2.4's hauler economics, which already assume roads. RVR-CRAWL: 60 t on twelve TRK-STD ≈ 37 kPa on the compacted corridor (150 kPa) ✓.

### 4.2b Aero & marine locomotion parts (feed V-13/V-14/V-15/V-17/V-20; the §5 hover- and float-margin readouts read these stats)

| ID | Type | Tier | Key stats | Mass | Used by |
|---|---|---|---|---|---|
| ROT-M | rotor set, multirotor (8 nacelles) | T2 | A_disk 11.5 m², P_max 8 kW | 50 kg | AIR-T1 Titan rotorcraft (hover margin 8/3.2 = 2.5) |
| ROT-L | tiltrotor set (VTOL + cruise tilt) | T3 | A_disk 30 m², P_max 70 kW | 300 kg | AIR-T2 (T4 [SPECULATIVE] build) |
| ENV-F0 | envelope, coated fabric | T0 | 0.20 kg/m² (V-17), max ΔP 5 kPa | per m² | BLN-V0 |
| ENV-F2 | envelope, laminate | T2 | 0.10 kg/m², max ΔP 10 kPa | per m² | DIR-T; MGF-T (double-wall ×2) |
| ENV-F3 | envelope, film | T3 | 0.06 kg/m², max ΔP 15 kPa | per m² | BLN-V2 |
| ENV-MSP | Mars superpressure thin film | T2 | 0.02 kg/m², max ΔP 1 kPa; instrument-class loads only (fragile) | per m² | BLN-M |
| FLT-1 | float / displacement hull cell | T2 | V_disp 4 m³ per part (V-0c/V-20) | 120 kg | BOAT-T, BARGE-T hull |
| BLST-1 | ballast tank | T3 | V 0.5 m³, pump 10 L/s (trim/dive rate) | 40 kg | SUB-T |
| FAIR-1 | fairing kit | T2 | Cd 0.8 → 0.5 on faired chassis (V-2) | 8 kg per faired cell | any ground vehicle |
| RAMP-1 | deployment ramp | T1 | vehicle load/unload without crane; refuses > 15° lander tilt (§8.14) | 150 kg | landers, hauler beds |
| SUB-FIN | dorsal heat-rejection fin + comms mast | T3 | rejects up to 6 kWt above the waterline (holds wetted skin flux ≤ 0.5 kW/m², §3.7.4); phased-array direct-to-Earth | 60 kg | SUB-T |

### 4.3 Utility & construction vehicles (mount 04 tool heads; rates are the tool's, canon 04)

| ID | Name | Tier | Class | Dry t | Pwr | Function / rate | Anchor |
|---|---|---|---|---|---|---|---|
| UTL-EXC1 | Excavator cart | T1 | VC-2 | 0.6 + 04 Drum Excavator (0.15 t) | STO-LI 15 kWh | 2.5 t regolith/day; e_dig 1 kWh/t (04 canon) | RASSOR/IPEx |
| UTL-EXC2 | Mobile bucket-wheel | T2 | VC-4 | 9 + 04 BWE (3 t) | NUK-KP1 or umbilical 15 kWe | 100 t/day (04 canon) | small terrestrial BWE |
| UTL-DOZE | Dozer/grader | T1 | VC-3 | 4.5 | STO-LI 60 kWh | grades 100 m of compacted track /h (8 kW); berms, pads | LANCE blade studies (NASA/Caterpillar) |
| UTL-CRANE | Rover-crane (LSMS arm) | T1 | VC-3 | 3.0 | STO-LI 30 kWh | lift m_max = 12 t·(1.62/g_local); 07 module Deploy enabler | NASA Langley LSMS |
| UTL-DRILL | Drill rig carrier | T1 | VC-3 | 4.0 + 04 drill | STO-LI 60 kWh / umbilical | carries TRIDENT-1 m (T1) or 10 m rig (T2); K3 cores per 04 | Honeybee TRIDENT/PRIME-1 |
| UTL-CDRONE | Construction drone "Spider" | T2 | (integrated, 0.25 t — zero-g drone exception, §3.1 V-0 item 4) | — | STO-LI 5 kWh + cold-gas | orbital/zero-g assembly, 1 joint/30 min (06 §canon); A2/A3 | Orbital Express + R2 lineage |

(Crane sanity: LSMS-class structures lift ~6× their Earth rating on the Moon — V-1 weight scaling; tipping uses V-0b with the load at boom tip.)

### 4.4 Hoppers (engines from 02 catalog; Δv from V-19)

| ID | Name | Tier (node) | Landed mass | Prop capacity (tank-full) | Engine (02) | Δv tank-full | Use | Anchor |
|---|---|---|---|---|---|---|---|---|
| HOP-S | Micro-hopper | T1 (VH-03) | 50 kg | 10.5 kg | RCS-D400 block (Draco, NTO/MMH, Isp 300 s) | 560 m/s = 2,942·ln(60.5/50) (→ 40 km Moon hops) | PSR peeks, skylight survey (11 DSC-03) | IM Micro-Nova "Grace" (flown 2025) |
| HOP-C5 | Cargo hopper | T2 | 5 t | 2.5 t | ML-24 (PF methalox, Isp 320 s vac) | 1,272 m/s = 3,138·ln(7.5/5) (→ 220 km Moon) | time-critical freight, no-road sites | lunar-lander derivatives (Morpheus-class engine) |
| HOP-P | Crewed hopper | T2 | 12 t | 8 t | ML-24 ×2 (PF methalox, Isp 320 s vac) | 1,600 m/s = 3,138·ln(20/12) (→ 360 km Moon) | crew sorties beyond rover range; abort-to-base reserve mandatory 20% | Apollo LM heritage |
| HOP-CERES | Low-g utility hopper | T2 | 2 t | 0.35 t biprop + cold-gas trim bottles | RCS-D400 ×2 blocks (Isp 300 s) + RCS-N10 cold-gas trim (70 s) | 475 m/s on the biprop (→ 210 km Ceres) | g<0.3 default mobility | Hayabusa/MASCOT hop lineage (uncontrolled→controlled) |

Propellant consumed per hop and hops-remaining follow from 02's rocket equation on the row's landed mass + remaining prop; the §3.6.2 worked example (5 t landed, 200 km Moon hop, Δv 1,219 m/s → ~2.4 t) is HOP-C5 at 95% tank.

Thrust closure against the 02 rows (Moon g 1.62): HOP-C5's single ML-24 gives 24 kN vac vs 12.2 kN gross weight (T/W 2.0; x_min 0.25 → 6 kN, hover-capable under the 8.1 kN landed weight ✓). HOP-P mounts ML-24 ×2 = 48 kN vs 32.4 kN at 20 t gross (T/W 1.5; 12 kN at min throttle vs 19.4 kN landed weight ✓). HOP-S and HOP-CERES land on Draco-class pulse modulation (400 N per nozzle; RCS-D400 is ullage-capable per 02 §4.7). Isp discipline: 320 s vac (ML-24) is the hard ceiling for hopper performance in this doc — if later content needs the 450 km-class crewed sortie, the path is a new engine row in 02, not a local Isp (§9 Q10).

### 4.5 Atmospheric craft

| ID | Name | Tier (node) | Body | Mass | Pwr | Aero: S [m²] / A_disk [m²] / C_Lmax / L/D | Performance | Payload | Anchor |
|---|---|---|---|---|---|---|---|---|---|
| AIR-M0 | Scout heli | T0→T2* (VH-05) | Mars | 2 kg | 40 Wh batt + panel | — / 1.15 / — / — | 3 min / 0.5 km per sol; ≈ 335 W hover (V-14: 310 W induced + 25 W avionics) | 50 g sensor | Ingenuity (*T0 hardware, fieldable at Mars from Act 3) |
| AIR-M1 | Courier heli | T2 (VH-05) | Mars | 31 kg | 2 kWh batt | — / 7.7 / — / — | 6 kW hover (V-14, η_h 0.42); 10 km hops; basins only ρ≥0.014 | 4 kg | Mars Science Helicopter study |
| AIR-T1 | Titan rotorcraft | T3 (VH-06) | Titan | 450 kg | MMRTG + 10 kWh batt; ROT-M (P_max 8 kW) | — / 11.5 / — / — | 3.2 kW hover (V-14, §3.5.6); 10 m/s; 30 km legs, daily (~2.7 kWh/leg on the 10 kWh pack ✓) | 80 kg | Dragonfly (+AN-39 salvage discount) |
| AIR-T2 | Titan tiltrotor utility | T4 [SPECULATIVE] (VH-06; tier set by the V-10 engine) | Titan | 2.5 t | V-10 O2-breather, 60 kW; ROT-L | 25 / 30 / 1.4 / 15 | VTOL (26 kW hover); 30 m/s cruise on ~9 kW (V-15); 500 km radius | 800 kg | Dragonfly-scaled; V-10 physics |
| AIR-T3 | Titan cargo plane | T3 | Titan | 8 t gross | V-9 methalox turbine, installed 36 kW (climb/headwind margin), cruise 28.8 kW shaft; V-10 is the T4 [SPECULATIVE] retrofit | 60 / — / 1.8 / 20 | stall 6.1 m/s; 144 km/h; 0.04 kWh/t·km; 600 m runway | 5 t | §3.5.6 math; Lorenz Titan-aviation analyses |
| HPF-T | Human-powered flyer | T3 | Titan | 30 kg wing | crew (≈72 W) | 8 / — / 1.8 / **12 (declared per-craft override, §3.5.6)** | stall 2.1 m/s, cruise 14 km/h, 2 h fatigue limit (08) | suited crew | Lorenz/Zubrin; V-13/V-15 shown in tooltip |
| GLD-V | Venus cloud glider | T3 (VH-09) | Venus 50–60 km | 450 kg | solar-electric 5 kW | 50 / — / 1.4 / 20 | soars the 65 m/s zonal superrotation — circumnavigates in ~5–7 days, roughly half of it in darkness (battery night ops; Vega's balloons flew at night); station-keeps vs the wind only at band edges; sun-synchronous flight would demand ~16 kW (V-15 at 61 m/s) and is deliberately not fitted | 100 kg | Northrop Grumman VAMP concept |

### 4.6 Balloons & dirigibles

| ID | Name | Tier (node) | Body/alt | Envelope (V_env / frontal / Cd) | Lift gas | Net payload | Notes / anchor |
|---|---|---|---|---|---|---|---|
| BLN-V0 | Superpressure aerobot | T0 (VH-09 free) | Venus 54 km | 3.5 m sphere, ENV-F0 (22 m³ / 9.6 m² / 0.45) | Hydrogen (carried; lift 1.00 — the 1985 Vega craft flew helium, which is not a ledgered resource; H2 is non-flammable in CO2 with no free O2) | 7 kg | Vega 1/2 (flown 1985, on He); drifts 65 m/s; 46 h battery unless solar T1 |
| BLN-V2 | Variable-altitude aerobot | T3 (VH-09) | Venus 48–60 km | 12 m dual-envelope, ENV-F3 (~900 m³ / ~110 m² / 0.5) | Hydrogen | 40 kg | JPL 2022 prototype (flew He; game item ships H2 per resource canon); ±5 km control; clamps to 03's 45–65 km safe envelope |
| MGF-T | Titan Montgolfière | T2 | Titan ≤ 8 km | 10 m double-wall, ENV-F2 ×2 (524 m³ / 79 m² / 0.5; ~630 m² wall area, ~65 kg) | RTG-heated ambient N2: waste heat sustains **ΔT ≈ 5–10 K → 0.27–0.55 kg/m³** (per §3.5.3 / TSSM double-wall design) | 120 kg (gross lift 141–288 kg − ~65 kg envelope; margin at the warm end of the band) | TSSM JPL/CNES study; MMRTG 2 kWt is the burner |
| DIR-T | Titan dirigible | T2 | Titan ≤ 3 km | 40×10 m ellipsoid, ENV-F2 (2,050 m³ / 78 m² / 0.05) | Hydrogen (inert here) | 10 t | §3.5.3: 8 m/s on 7.8 kW; 0.027 kWh/t·km — Titan's railroad |
| BLN-M | Mars science balloon | T2 | Mars < 6 km | ENV-MSP thin film (5,000 m³ / ~280 m² / 0.5) | Hydrogen | 60 kg | Mars aerobot studies; logistics-useless (honest table §3.5.3) |

### 4.7 Marine craft

| ID | Name | Tier (node) | Mass | Hull | Pwr | Performance | Anchor |
|---|---|---|---|---|---|---|---|
| BOAT-T | Shoreline skiff | T2 | 0.8 t + 1 t cargo | H1, V_hull 4 m³ | STO-SS 30 kWh | 4 m/s; 150 km; sea-state ≤ 2 | Titan Mare Explorer (TiME, proposed Discovery finalist) |
| SUB-T | Titan submarine | T3 (VH-07) | 1.5 t | H1, 6 m | Stirling RIG bank (NUK-RTG-S ×3, ≈ 330 We; ~6 kWt rejected via SUB-FIN) | 1 m/s, 90-day/2,000 km legs, 300 m depth; effervescence rules §3.7.4; power closure per §3.7.3 ✓ | NASA GRC COMPASS/NIAC |
| BARGE-T | Methane barge + tug | T4 [SPECULATIVE] (no direct study — the tag marks the missing anchor, not exotic physics) | 6 t tug + 350 m³ barge (30×5 m, 1.5 m draft, ~7.5 m² submerged frontal) | H1, FLT-1 cells | V-10, 30 kW installed; ~21.5 kW at cruise (V-2 marine: Cd 0.4, η_prop 0.60) + ~3.5 kW hotel = 25 kW | 100 t cargo at 2.5 m/s (9 km/h); **0.028 kWh/t·km** — bulk sea freight for indivisible 100 t loads | displacement-hull physics |
| CRYO-E | Ice-penetrating cryobot | T3 → T4 [SPECULATIVE] for the production 100 kWt config (VH-08; SLUSH-class ~40 kWt is the T3 anchor) | 2.2 t, Ø 0.26 m × 5 m | melt head | 100 kWt fission core (09) | 100 m/day; 15 km in ~150 d; repeater pucks; A3 only | SESAME / Honeybee SLUSH / Philberth (1,005 m flown 1968) |
| ROV-E | Europa under-ice ROV | T4 [SPECULATIVE] (VH-08) | 0.9 t | **H3 (40 MPa)** | NUK-RTG-S + 20 kWh | 0.5 m/s; deployed by CRYO-E at shell base (~30 MPa) | endgame; SWIM/Orpheus lineage |

### 4.8 Control & autonomy fit-kits (tie to 05 ladder / 11 nodes)

| ID | Kit | Tier (node) | Mass | Grants |
|---|---|---|---|---|
| CTL-A2 | Teleop package | T2 (05 A2) | 20 kg + comms part (06/07 catalogs) | TELEOP mode, η per 05 F-2 |
| CTL-A3 | AutoNav package | T3 (11 IN-09) | 35 kg | AUTONAV mode (0.5× v_max, 24/7); exception queue |
| CTL-CNV | Convoy follower | T2 | 8 kg | follow a leader, 5:1 |

---

## 5. Player Interaction & UI

- **Motor Pool editor**: the Drydock (06 §5) reskinned — same grid canvas, part palette filtered to vehicle categories; live readouts: gross mass, h_COM/θ_tip dial, ground clearance vs target-sector rocks, E_km and range *on the currently selected body/terrain* (V-5 evaluated live), float margin for marine (V_disp from §4.2b float parts), hover margin (P_max/P_hover, P_max from the §4.2b rotor rows) for rotorcraft.
- **Route planner** (the primary mobility verb): draw waypoints on the site/sector map (03 S-7c tiles); the planner shades cells by Crr/slope/clearance feasibility, quotes time, kWh or propellant, wear, and walkback/abort compliance; routes execute under time warp as analytic segments with scheduled events (arrival, recharge stop, breakdown roll, comm-occlusion pause, storm interrupt) per 13's event-queue contract.
- **Direct drive** (real-time only): WASD top-down control of any CREWED/TELEOP vehicle — deliberately fun, physically honest (V-6/V-7/V-8 enforced: brake distances balloon at low g; the LRV *will* leave the ground at 14 km/h). In TELEOP the control loop displays the RTT-delayed ghost: inputs apply after τ, the canonical "drive the Moon from Earth" experience (move-and-wait above 5 s RTT).
- **Flight UI**: altitude-band strip + energy/airspeed tape; planner mode identical to ground routes with wind-vector overlay per band; balloons show drift forecast cones (wind field from 03).
- **Dive UI**: depth tape, hull-margin bar (V-21), effervescence warning when skin flux > 0.5 kW/m², sonar swath painting the bathymetry layer (feeds 11 DSC-14).
- **Hop targeting**: range ring + Δv/propellant quote (V-19); landing-cell terrain check displayed before commit; plume-exclusion circles drawn around both endpoints.
- **Teleop console**: per 05 §UI canon — operator → vehicle assignment, RTT and η_teleop quoted before committing; sub-0.2 refused with the standard hint.
- **Fleet & maintenance dashboard**: per-vehicle C, MTBF forecast, spares stock (05 ledger), parked-thermal status (wadi/garage/exposed), battery-night margin alarm ("vehicle will not survive the night where it is parked" — fires *before* dusk via 09's analytic event prediction).
- **Tooltips teach the real math**: every range/stall/hover figure expands to show V-formula, inputs, and the real-world anchor — the design bible's pedagogy doctrine applied to vehicles.

---

## 6. Progression Hooks

Tech nodes are 11's VH ladder (this doc implements them; ED for SurfaceMobility/AeroFlight accrues from km driven and flight/dive events — 11 §canon).

| Tier / Act | Vehicle beats |
|---|---|
| **T0, Act 1 (Earth+LEO)** | RVR-SCOUT robotic rovers (VH-00) and BLN-V0-class aerobots exist as proven tech; Earth proving grounds let players learn the Motor Pool and farm early SurfaceMobility ED cheaply (12's test-contract economy). |
| **T1, Act 2 (Moon)** | VH-01 open rover (the LRV moment), VH-02 robotic haulers feeding 04/05 mining, VH-03 hoppers for PSR prospecting, dozers/cranes/drills enabling 07 base assembly. **The night-survival arc**: first night kills a careless rover fleet → wadis → RFC rovers → garages. Teleop from Earth at η 0.96 makes the Moon the automation sandbox. |
| **T2, Act 3 (Mars + NEAs)** | VH-04 pressurized rovers (14-day sorties), VH-05 Mars rotorcraft scouts, combustion-drive haulers burning ISRU methalox, swap-pallet logistics; Mars light-lag (η ≤ 0.14) forces the AUTONAV research push; dust storms teach fission-backed fleets. Low-g hoppers own the asteroid sites. |
| **T2–T3, Act 4 (Belt + Venus + Mercury)** | Venus: VH-09 balloons → variable-altitude aerobots → cloud gliders around 07's aerostats; VH-10 Venus surface crawler converts the Venera-13 trophy contract from suicide run to 60-day campaign. Mercury: RVR-CRAWL terminator-pacing platform (07 HAB-16) — the game's slowest, coolest vehicle. Ceres: hopper-first mobility doctrine. |
| **T3–T4, Act 5 (Jupiter/Saturn)** | **Titan is the vehicle act**: Dragonfly-class rotorcraft (discounted by AN-39 salvage), dirigible freight network, cargo planes on ice runways, shoreline boats → VH-07 submarine (DSC-13/14 science arcs) → methane barges as the colony's bulk haulers; the human-powered flyer as the morale crown jewel. Europa: VH-08 cryobot descent (~150-day melt campaign as a live event chain) → under-ice ROV → ocean science endgame. |
| **Endgame** | Vehicle fleets become fully A3/A4 background economy (A4 mode row, §3.8: ledger-mode only per §8.15 — 05's autonomous factory complexes extend to autonomous *mines with wheels*); the interstellar-precursor megaproject consumes the fleet's output, not new vehicle tech. He3/T4 content adds no new chassis — deliberately; mobility is a solved problem by then. |

---

## 7. Cross-System Interfaces

**Consumes:**
- `03-solar-system.md`: per-body g, R, GM (V-18); atmosphere ρ(h)/T/P/composition (S-5a) for all flight and V-10; sector terrain_class/slope_sigma/rock_abundance (S-7) for Crr/μ/clearance; winds and storm events; Mercury terminator speed 3.6 km/h; sea locations; Venus 45–65 km safe-envelope clamp.
- `09-power-thermal.md`: every power/storage item by ID (STO-*, NUK-*), battery-freeze and heater-P0 rules, RFC 2.0 kWh_e/kg, thermal wadi STO-WADI, H-5 endurance clocks (Venus/Mercury), H-8 operating bands, analytic event prediction for night-margin alarms.
- `02-propulsion.md`: hopper engine rows by catalog ID — ML-24 (PF methalox lander, 320 s vac), LND-71, RCS-D400/RCS-N10 blocks, per 02 §7's provides list — with their thrust, Isp, propellant, throttle, and ignition limits; rocket equation conventions. No engine stat is restated or extrapolated here (§3.6.2, §4.4).
- `04-resources-isru.md`: tool-head stats mounted on UTL chassis (excavators, drills, intakes), e_dig 1 kWh/t, anchoring rules (M-6) for low-g tool reaction, propellant kWh/kg (7.1 methalox) for the hop-vs-drive energy honesty.
- `05-industry-logistics.md`: autonomy ladder A0–A4, F-2 η_teleop with T_atom 60 s driving, condition/MTBF/spares system (adopted verbatim — closes 05's open question), route/exception queues, Earth teleoperator labor market, vehicle build recipes.
- `06-ships-stations.md`: the part-grid editor, footprint/COM/attach math, blueprint format; CG-BAY cargo carriage of vehicles; comms antenna part stats.
- `07-bases-habitats.md`: AL-4/AL-5/AL-6 dock cycles, dust D-ledger and acid ledger, garage habitat modules, landing pads, Deploy crane requirement, Titan submarine dock, sintered-road build items.
- `08-life-support-crew.md`: cabin consumable rates, suit endurance (walkback rule inputs), suitport gas/dust costs, fatigue for the human-powered flyer.
- `13-architecture.md`: comms graph and RTT (§3.11), occlusion windows, time-warp analytic route integration, entity caps (vehicles are entities; ≤ 2,000 global).
- `11-research-tech.md`: VH-00…VH-10 and IN-09 unlock gates; ED accrual rules.

**Provides:**
- To `04`/`05`: mobile platforms for every extraction tool; freight-link cost table (kWh/t·km per body/terrain/mode: road 0.012–0.034, dirigible 0.027, barge 0.028, plane 0.04, hop ~10³× road) for the route planner; survey-traverse mobility for K2/K3.
- To `06`: construction drone (UTL-CDRONE) for orbital assembly; the vehicle-class chassis validation rules (V-0a–d) as a Drydock mode.
- To `07`: RVR-CRAWL drivetrain spec for HAB-16 (25 kWe continuous / 80 kWe peak at 60 t gross, 3.7 km/h — **valid on the prepared/compacted terminator corridor, Crr 0.06; raw regolith ≈ 48 kWe**, §4.1); rover-crane for module Deploy; vehicle-side dock-collar standard.
- To `08`: pressurized-cab refuge definitions, suitport mounts, walkback-rule enforcement data.
- To `09`: vehicle load profiles (P_drive, hotel, heater) as grid consumers; night-survival strategy menu consuming wadi/RFC/RTG items.
- To `11`: km-driven / flight-hour / dive-hour event streams for ED; vehicle-gated discovery arcs (skylight hopper survey, sub sonar maps, cryobot ocean breach).
- To `12`: vehicle price/contract hooks (test contracts, the Venera-13 recovery trophy, Titan air-cargo contracts); tooltip-pedagogy content.
- To `13`: vehicle sim requirements (analytic route segments, breakdown/arrival/occlusion events, site-map traversal LOD).

---

## 8. Failure Modes & Edge Cases

1. **Tip-over** (V-0b violated by dynamic load or off-route slope): vehicle immobilized, 20% part-damage roll; recovery needs a crane or 4 crew-h — on Mars from Earth, that's an A3 task or a long wait. UI shows a live tilt icon past θ_tip − 5°.
2. **Embedding** (Spirit's death): DUNE/soft cells roll 5%/km when gross pressure per wheel > soil bearing stat; escape attempts ×3 energy and 30%/attempt success — or a second vehicle tows (tow rule: combined V-6 traction must exceed 1.5× embedded F_roll).
3. **Battery freeze-brick**: Li packs may not *charge* below 273 K (§3.3.1 — lithium plating); unpowered cold soak is tolerated down to electrolyte freeze at ≈ 233 K (−40 °C). Permanent damage triggers two ways: pack below **233 K** with heater unpowered for > 6 h, or any charge/discharge attempt below 273 K — either costs −30% capacity per event (09 chemistry canon, coordinated). The classic chain: flat battery at lunar dusk → no heater → ~100 K regolith pulls the pack under 233 K → bricked rover 300 km from base. The pre-dusk alarm (§5) exists because playtests will demand it.
4. **Night/storm strand**: solar vehicle caught by lunar night or Mars global storm (09's signature crisis) → hibernation roll each 24 h: survival = f(insulation, RTG presence, wadi). Opportunity's fate, player-preventable.
5. **Wheel destruction**: CHAOS sectors at speed > 0.3× v_max roll puncture events (Curiosity anchor); a wheel-dead vehicle limps at 0.3× with +50% E_km.
6. **Comm loss in TELEOP**: vehicle safe-halts (brakes, beacon). Aircraft: RTB autopilot at A2+; at A1 (no kit) the aircraft *crashes* — the UI refuses A1 flight dispatch beyond visual range, but the player can override once with a signed warning. Balloons cannot halt: link loss = drift continues; recovery becomes an intercept problem (Vega gondolas as drifting anomalies are the in-world precedent, 03 AN-18).
7. **Hop landing failure**: landing-cell slope > 10° or rock roll vs clearance → tip/crash cascade (50% cargo survival, crew abort engine rule: HOP-P always reserves 20% Δv to re-hop to flat). Plume rule violations damage third-party assets — including your own base; pads are not optional decor.
8. **Titan cryo-seal failure** (skipped warm-lock, elastomer parts in 94 K service): leak/seize events per 07's 10%/cycle; submarine variant: ballast-valve seize → emergency buoyancy drop (mission continues surfaced, dives locked until dock service).
9. **Effervescence blind-out**: sustained skin flux > 0.5 kW/m² (e.g., running the Stirling pair flat-out submerged in warm shallow ethane): sonar −50%, survey data quality halved (11 DSC-14 sabotaged), bubble-noise event chance. Throttle or surface.
10. **Cryobot stuck/refreeze**: descent halt > 48 h with heat < 20 kWt → refreeze entombment (probe lost; repeater string survives as a science consolation). Drives the "don't undersize the core" lesson; SLUSH's hybrid mechanical clearing is the T4 mitigation part.
11. **Venus clocks**: the route planner clamps flight at the **45 km floor** (03's safe envelope — the §3.5.4 band table points here); **42–45 km is an out-of-envelope warning band** — reachable only by failure or override, accruing condition damage (2%/min) with escalating thermal alarms; **below 42 km → destruction** (03's kill line, 380 K electronics). Surface vehicle past its H-5 clock → loss; acid ledger unwashed > 30 days → optics/envelope degradation (07 canon).
12. **Mercury crawler falls behind**: drivetrain failure that strands the platform in daylight starts the 09 H-5 noon clock (hours at 700 K subsolar) — the slowest catastrophe in the game; spare-drivetrain doctrine and twilight-margin routing are the counters.
13. **Walkback violations**: the planner hard-refuses unpressurized crew routes beyond the 10 km radius; EVA overrides (12's risk-acceptance flow) exist but suit failure outside walkback range is unsurvivable by design (08's failure table) — no miracle rescues.
14. **Vehicle-as-cargo edge**: a vehicle inside a crashing lander uses 06's crash rules (it is cargo); a vehicle *driving onto* a fueled hopper pad during launch triggers the plume rule both ways. Deployment ramps refuse > 15° lander tilt.
15. **Entity-cap pressure** (13): fleets > ~50 active vehicles per site degrade to ledger-mode (statistical wear/throughput, no per-vehicle events) — by design, invisible if garages and A3 routes are healthy.

---

## 9. Open Questions

1. **Direct-drive depth**: how much suspension/terrain feel does the real-time driving mode need (per-wheel raycast vs flat-kinematic) before it stops being worth the 13 §perf budget? Playtest gate after the Act-2 vertical slice.
2. **Wind-field fidelity**: balloon/dirigible gameplay quality hinges on wind variety; 03 currently specs band-mean vectors + storm events. Do we need stochastic gusting and altitude shear for Venus/Titan, or does that turn aerobots into babysitting? (Owners: 03 + 10.)
3. **Titan human-powered flight**: shipped as a true EVA-mobility mode (this doc's current spec) or demoted to a morale/wonder event to save UI surface? Realism is not in question — scope is.
4. **Venus crewed surface**: 03's open question — if the decision lands "robots only forever," VH-10 stays as-is; if crewed sorties are allowed at T4, this doc needs a crewed refractory crawler with an 08 interface nobody has designed. Recommend robots-only (matches realism reviewers).
5. **Europa ocean scope in v1**: ROV-E currently terminates at science arcs near the breach point. Full ocean-floor traversal (H4 hulls, 100+ MPa) is physically specifiable but content-empty — cut or keep as post-v1?
6. **Boats/waves**: is the sea-state 0–4 abstraction enough, or does Titan storm sailing deserve real wave mechanics? (Cassini evidence says seas are usually flat — realism argues for the abstraction.)
7. **Legged locomotion**: deliberately absent (no flown anchor beyond testbeds; tracked/wheeled covers v1 terrain). Revisit if CHAOS-sector content needs it; ATHLETE (JPL) would be the T3 anchor.
8. **Shared-stat row with 05's bot_mule**: one vehicle defined in two docs (05 labor math, 10 chassis stats) — confirm at integration that both docs point at a single data row to avoid divergence (action: 05+10 joint review).
9. **Terminator-chase automation**: is RVR-CRAWL's perpetual-twilight routing a standing A3 route (05's system) or a dedicated "pace the terminator" autopilot verb? UX call for 12.
10. **Crewed-hopper range vs 02's lander-engine ceiling**: with 02's best lander engine at Isp 320 s vac (ML-24), HOP-P closes at 1,600 m/s tank-full (~360 km Moon) — short of a 450 km sortie class. Options: accept it (more pads, staged hops — arguably better infrastructure gameplay), or request that 02 add a pump-fed methalox *lander* row (Raptor-derived lander class, ~345 s vac plausible within 02's own pump-fed ceiling) and re-quote HOP-P against its ID. Joint owners 02 + 10; this doc will not carry an Isp that 02's catalog cannot source.
