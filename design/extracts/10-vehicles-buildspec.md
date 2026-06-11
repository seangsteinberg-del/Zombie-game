# BUILD SPEC — 10 Vehicles (Surface, Atmospheric, Marine)

Extracted from `design/10-vehicles.md` (649 lines), reconciled against `design/DECISIONS.md`
(which wins all conflicts). Target: implementable without re-reading the source doc.
Units: SI throughout — mass kg (tables t), force N, power W/kW, energy kWh, speed m/s
(UI km/h), g m/s², ρ kg/m³, angles deg. Formula IDs `V-n` are canon and must appear in
code comments/tooltips. g0 = 9.80665 only inside Isp; all local weight uses body g.

## 0. Binding DECISIONS overlay (apply before anything below)

| Ruling | Effect on this spec |
|---|---|
| C20 | Exotic bundle **IN v1**: Titan human-powered flyer (HPF-T) as a true EVA-mobility mode; Europa **ocean-floor traversal** (H4 hull, 100+ MPa, T4 [SPECULATIVE]); **legged locomotion** (ATHLETE anchor, T3, chassis design Pass 2); **boats with a real wave model**. All Phase 5; the wave model and ocean floor are the two acknowledged heavy items. |
| C17 | Venus **crewed** surface sortie IN as T4 [SPECULATIVE] trophy — single short sortie in a cooled suit-vehicle. Robotic RVR-VENUS line unchanged. Interface design (07/08/10) at Pass 2 — no stats yet. |
| A8 | 02 published **ML-111** pump-fed methalox lander (Isp 355 s vac). HOP-P quotes against it: Δv 1,778 m/s tank-full. ML-24's 320 s ceiling is superseded for this row only. |
| A9 | `bot_mule` is a **single data row owned by 05**; RVR-MULE in §1.1 is a pointer, not a copy. |
| A5 | One wear model: 02 per-ignition wear × 11 maturity factor × 05 spares/MTBF — orthogonal multipliers, no double counting. V-24 feeds only the 05 layer. |
| C23 | Plume–surface scouring IN, simple cone/threshold model (§2.6.3). |
| D28 | Driving sim is **terrain-class/slope**, NOT per-wheel physics (per-wheel raycast is an open playtest question, not v1 baseline). |
| C24 | Mars ρ varies ±50% season/dust (03 owns curves) — vehicle flight/range readouts must sample live ρ, not a constant. |

---

## 1. VEHICLE CATALOG

### 1.0 Build system

- Vehicles are built in the **Motor Pool**, a mode of 06's Drydock: same 1 m × 1 m grid,
  footprint/COM/attach math, blueprint JSON. Grid is travel-axis-horizontal; "down" = local g.
- Locomotion parts attach only to `bottom` nodes; envelopes only to `top` nodes.
- **Sub-100 kg vehicles are integrated catalog items** (no grid build; occupy 1 cell as cargo).
  Exception: zero-g assembly drones to 300 kg (UTL-CDRONE) are also integrated.
- Validation (replaces launch validation):
  - **V-0a clearance**: lowest non-locomotion cell ≥ locomotion set's clearance stat; warn vs sector rock_abundance.
  - **V-0b tip-over**: `θ_tip = atan(0.5·track_width / h_COM) ≥ 2.0 × slope_sigma` of coarsest allowed sector. Recompute h_COM live on cargo load.
  - **V-0c float**: `m_gross / V_displacement ≤ 0.95 · ρ_sea`.
  - **V-0d power closure**: Σ continuous drive + hotel ≤ Σ source output at destination-body insolation.

**Chassis classes** (root part of a vehicle = chassis frame):

| Class | Grid | Gross cap | Examples |
|---|---|---|---|
| VC-1 cart | 2×2 | 0.8 t | LRV, mule, drill cart |
| VC-2 light | 4×2 | 3 t | science rover, light hauler |
| VC-3 medium | 6×3 | 12 t | pressurized rover, excavator carrier |
| VC-4 heavy | 10×4 | 60 t | 20 t haulers, cranes, Titan barge tug |
| VC-5 platform | 16×5 | 300 t | Mercury crawler (07 HAB-16), module transporter |

Vehicles ride as cargo (06 CG-BAY / 05 Pelican decks); unloading needs RAMP-1, a rover-crane, or 2 crew-h EVA.

**Cost note**: 10-vehicles.md carries **no $ prices** — prices/contracts are 12 §4.3, build
recipes are 05. The only cost rule owned here: **full overhaul = MachineParts 3% +
Electronics 0.5% of dry mass**; field repair ×3 spares, ×2 time.

### 1.1 Rovers & ground chassis

| ID | Name | Tier (node) | Class | Dry t | Power | Crew | Speed raw/road | E_km | Range | Anchor |
|---|---|---|---|---|---|---|---|---|---|---|
| RVR-SCOUT | Robotic science rover | T0 (VH-00) | VC-2 | 1.0 | NUK-RTG-M + 2 kWh buffer | 0 | 0.3 km/h avg; 0.35 km/sol A2-batch / ~2 km/sol local A2 / ~7 km/sol A3 cap | 0.37 kWh/km (Mars) | ∞ (RTG) | Curiosity/Perseverance |
| RVR-LRV | Open crew rover | T1 (VH-01) | VC-1 | 0.21 | 8.7 kWh AgZn primary (0.9 usable) or STO-LI 60 kg | 2 | 13/37 km/h (Moon) | 0.089 kWh/km | 88 km | Apollo LRV |
| RVR-MULE | Rover-manipulator | T2 | VC-1 | 0.45 | STO-LI 15 kWh | 0 | 8/24 | 0.06 | 200 km | = 05 `bot_mule` (A9: 05 owns the row) |
| RVR-PRESS | Pressurized rover | T2 (VH-04) | VC-3 | 3.0 | STO-SS 100 kWh (0.4 t); RFC option | 2 (4 cont.) | 10/30 (Moon) | 0.50 raw / 0.29 track / 0.20 road | 170/293/425 km | NASA SEV; Lunar Cruiser |
| RVR-HAUL10 | Hauler, 10 t bed | T1 (VH-02) | VC-4 | 8.0 | swap pallet 300 kWh (1.2 t STO-SS) or V-9 combustion | 0 | 15/40 (Mars) | 2.9 full | ~90 km/pallet | autonomous mining trucks |
| RVR-HAUL40 | Hauler, 40 t bed | T2 (VH-02) | VC-4 | 22 | V-9 combustion (1.2 t reactants/100 km Mars) | 0/1 | 12/35 | 9.6 full | by tankage | same |
| RVR-CRAWL | Mercury crawler | T3 | VC-5 | 30 (chassis = 07 HAB-16) | NUK-KP10 ×3 | carries 2 modules | 0.5–5 km/h | 25 kWe cont. @ 3.7 km/h, 60 t gross — **requires compacted terminator corridor Crr 0.06** (raw regolith ≈ 48 kWe, out of budget); 80 kWe peak = 3.7 km/h on 10° grade | ∞ (fission) | JPL terminator studies |
| RVR-VENUS | Venus surface crawler | T3 (VH-10) | VC-2 | 1.8 | wind turbine ~40 W mean / 250 W gust → mechanical spring/flywheel store (no battery at 737 K) + SiC avionics | 0 | 0.3 km/h burst / ~0.05 km/h mission avg | clock-limited | 60-day clock | AREE + LLISSE/GEER |

### 1.2 Ground locomotion parts (multiply Crr/wear; A_contact feeds V-1a, clearance feeds V-0a)

| ID | Type | Tier | Crr mult | Wear mult | A_contact/set m² | Clearance m | kg/set | Max load/set t | Where |
|---|---|---|---|---|---|---|---|---|---|
| WHL-MESH | wire-mesh wheel | T0 | 1.0 | 1.0 | 0.05 | 0.35 | 12 | 0.4 | vacuum bodies (LRV) |
| WHL-RIGID | machined metal | T0 | 1.1 | 2.0 on CHAOS | 0.04 | 0.30 | 25 | 0.6 | Mars robotic (Curiosity) |
| WHL-NITI | NiTi spring tire | T1 | 0.85 | 0.6 | 0.06 | 0.35 | 20 | 0.8 | vacuum/Mars (NASA Glenn) |
| TRK-STD | tracks | T1 | 0.8 soft / 1.3 hard | 1.5 (terrain_mult cap 1.5) | 0.50 | 0.25 | 90 | 5.0 | DUNE/soft, VC-4/5; speed cap 15 km/h |
| WHL-CRYO | heated-hub cryo | T2 | 1.0 | 1.0 (Titan) | 0.06 | 0.35 | 30 | 0.8 | Titan (94 K bearings, metal bellows) |
| WHL-STUD | studded ice | T2 | 1.0 | 1.0 | 0.04 | 0.30 | 28 | 0.8 | ICE_PLAIN; μ 0.25→0.45 |
| WHL-REFR | refractory, dry bearings | T3 | 1.3 | clock-based | 0.03 | 0.25 | 40 | 0.6 | Venus surface |
| (LEG-ATH) | legged set, ATHLETE anchor | T3 | TBD Pass 2 | — | — | — | — | — | DECISIONS C20: IN v1, stats land Pass 2/Phase 5 |

Worked ground-pressure checks (V-1a): 1 t science rover ÷6 WHL-RIGID ≈ 15.5 kPa (fails DUNE's
7 kPa by design, clears duricrust 80); LRV ÷4 WHL-MESH ≈ 5.4 kPa ≪ 25 ✓; 18 t hauler on 6 NiTi
≈ 185 kPa (exceeds duricrust → mount TRK-STD: ÷4 tracks ≈ 33 kPa, or stay on roads);
RVR-CRAWL 60 t ÷12 TRK-STD ≈ 37 kPa vs corridor 150 ✓.

### 1.3 Aero & marine locomotion parts

| ID | Type | Tier | Key stats | Mass | Used by |
|---|---|---|---|---|---|
| ROT-M | multirotor set, 8 nacelles | T2 | A_disk 11.5 m², P_max 8 kW | 50 kg | AIR-T1 (hover margin 8/3.2 = 2.5) |
| ROT-L | tiltrotor set | T3 | A_disk 30 m², P_max 70 kW | 300 kg | AIR-T2 |
| ENV-F0 | envelope, coated fabric | T0 | 0.20 kg/m², max ΔP 5 kPa | per m² | BLN-V0 |
| ENV-F2 | envelope, laminate | T2 | 0.10 kg/m², max ΔP 10 kPa | per m² | DIR-T; MGF-T (double wall ×2) |
| ENV-F3 | envelope, film | T3 | 0.06 kg/m², max ΔP 15 kPa | per m² | BLN-V2 |
| ENV-MSP | Mars superpressure film | T2 | 0.02 kg/m², max ΔP 1 kPa; instrument loads only | per m² | BLN-M |
| FLT-1 | float/displacement hull cell | T2 | V_disp 4 m³ per part | 120 kg | BOAT-T, BARGE-T |
| BLST-1 | ballast tank | T3 | V 0.5 m³, pump 10 L/s (trim/dive rate) | 40 kg | SUB-T |
| FAIR-1 | fairing kit | T2 | Cd 0.8 → 0.5 | 8 kg per faired cell | ground vehicles |
| RAMP-1 | deployment ramp | T1 | load/unload w/o crane; refuses >15° lander tilt | 150 kg | landers, hauler beds |
| SUB-FIN | dorsal heat-rejection fin + comms mast | T3 | rejects ≤6 kWt above waterline (keeps wetted flux ≤0.5 kW/m²); phased-array DTE | 60 kg | SUB-T |

### 1.4 Utility & construction (tool heads + rates owned by 04)

| ID | Name | Tier | Class | Dry t | Power | Function | Anchor |
|---|---|---|---|---|---|---|---|
| UTL-EXC1 | Excavator cart | T1 | VC-2 | 0.6 + 0.15 (04 drum) | STO-LI 15 kWh | 2.5 t regolith/day; e_dig 1 kWh/t | RASSOR/IPEx |
| UTL-EXC2 | Mobile bucket-wheel | T2 | VC-4 | 9 + 3 (04 BWE) | NUK-KP1 or 15 kWe umbilical | 100 t/day | terrestrial BWE |
| UTL-DOZE | Dozer/grader | T1 | VC-3 | 4.5 | STO-LI 60 kWh | 100 m compacted track/h @ 8 kW; berms, pads | LANCE blade |
| UTL-CRANE | Rover-crane (LSMS) | T1 | VC-3 | 3.0 | STO-LI 30 kWh | lift m_max = 12 t·(1.62/g_local); tip check = V-0b with load at boom tip | NASA LSMS |
| UTL-DRILL | Drill rig carrier | T1 | VC-3 | 4.0 + drill | STO-LI 60 kWh / umbilical | TRIDENT 1 m (T1) or 10 m rig (T2) | Honeybee TRIDENT |
| UTL-CDRONE | Construction drone | T2 | integrated 0.25 t (zero-g exception) | — | STO-LI 5 kWh + cold gas | zero-g assembly, 1 joint/30 min; A2/A3 | Orbital Express |

### 1.5 Hoppers (engines by 02 catalog ID only — never restate engine stats)

| ID | Name | Tier (node) | Landed mass | Prop cap | Engine (02) | Δv tank-full | Use |
|---|---|---|---|---|---|---|---|
| HOP-S | Micro-hopper | T1 (VH-03) | 50 kg | 10.5 kg | RCS-D400 (NTO/MMH, 300 s) | 560 m/s = 2942·ln(60.5/50) → 40 km Moon | PSR peeks, skylight survey (11 DSC-03) |
| HOP-C5 | Cargo hopper | T2 | 5 t | 2.5 t | ML-24 (PF methalox, 320 s vac) | 1,272 m/s = 3138·ln(7.5/5) → 220 km Moon | time-critical freight |
| HOP-P | Crewed hopper | T2 | 12 t | 8 t | **ML-111 ×1** (pump-fed methalox, 355 s vac — DECISIONS A8) | 1,778 m/s = 3481·ln(20/12) → ~445 km Moon | crew sorties; **mandatory 20% Δv abort reserve** |
| HOP-CERES | Low-g utility hopper | T2 | 2 t | 0.35 t biprop + cold-gas trim | RCS-D400 ×2 + RCS-N10 (70 s) trim | 475 m/s biprop → 210 km Ceres | default mobility at g < 0.3 |

Thrust closure (Moon): HOP-C5 ML-24 24 kN vs 12.2 kN gross weight (T/W 2.0; min throttle 6 kN
< 8.1 kN landed weight → hover ✓). HOP-P ML-111 111 kN (T/W 3.4 @ 20 t; 16.7 kN min throttle
< 19.4 kN landed ✓). HOP-S/HOP-CERES land on Draco pulse modulation.

### 1.6 Atmospheric craft

| ID | Name | Tier (node) | Body | Mass | Power | S m² / A_disk m² / C_Lmax / L/D | Performance | Payload |
|---|---|---|---|---|---|---|---|---|
| AIR-M0 | Scout heli | T0 hw, fieldable T2 (VH-05) | Mars | 2 kg | 40 Wh batt + panel | —/1.15/—/— | ~335 W hover (310 induced + 25 fix); 3 min, 0.5 km per sol | 50 g sensor |
| AIR-M1 | Courier heli | T2 (VH-05) | Mars | 31 kg | 2 kWh batt | —/7.7/—/— | 6 kW hover (η_h 0.42); 8 min / 10 km hops; basins only (ρ ≥ 0.014) | 4 kg |
| AIR-T1 | Titan rotorcraft | T3 (VH-06) | Titan | 450 kg | MMRTG + 10 kWh batt; ROT-M | —/11.5/—/— | 3.2 kW hover; 10 m/s; 30 km legs daily (~2.7 kWh/leg) | 80 kg |
| AIR-T2 | Titan tiltrotor | T4 [SPEC] (engine sets tier) | Titan | 2.5 t | V-10 O2-breather 60 kW; ROT-L | 25/30/1.4/15 | 26 kW hover; 30 m/s cruise on ~9 kW; 500 km radius | 800 kg |
| AIR-T3 | Titan cargo plane | T3 | Titan | 8 t gross | V-9 methalox turbine: 36 kW installed, 28.8 kW cruise (V-10 = T4 retrofit) | 60/—/1.8/20 | stall 6.1 m/s; 40 m/s (144 km/h); 0.04 kWh/t·km; 600 m runway | 5 t |
| HPF-T | Human-powered flyer | T3 (C20: IN v1 as EVA mode) | Titan | 30 kg wing | crew ≈72 W (fit human sustains 200 W) | 8/—/1.8/**12 declared per-craft override** | stall 2.1 m/s; cruise 14 km/h; 2 h fatigue limit (08) | suited crew |
| GLD-V | Venus cloud glider | T3 (VH-09) | Venus 50–60 km | 450 kg | solar-electric 5 kW | 50/—/1.4/20 | rides 65 m/s superrotation, circumnavigates 5–7 days; station-keeps only at band edges (sun-sync would need ~16 kW — not fitted) | 100 kg |

### 1.7 Balloons & dirigibles

| ID | Name | Tier | Body/alt | Envelope (V_env / frontal / Cd) | Gas | Net payload | Notes |
|---|---|---|---|---|---|---|---|
| BLN-V0 | Superpressure aerobot | T0 (VH-09 free) | Venus 54 km | 3.5 m sphere ENV-F0 (22 m³ / 9.6 m² / 0.45) | H2 (lift 1.00; inert in CO2) | 7 kg | Vega anchor; drifts 65 m/s; 46 h battery unless solar T1 |
| BLN-V2 | Variable-altitude aerobot | T3 (VH-09) | Venus 48–60 km | 12 m dual ENV-F3 (~900 m³ / ~110 m² / 0.5) | H2 | 40 kg | ±5 km control @ 0.5 m/s vertical; clamps 45–65 km envelope |
| MGF-T | Titan Montgolfière | T2 | Titan ≤ 8 km | 10 m double-wall ENV-F2 ×2 (524 m³ / 79 m² / 0.5; ~65 kg wall) | RTG-heated ambient N2, ΔT 5–10 K → 0.27–0.55 kg/m³ | 120 kg | MMRTG 2 kWt is the burner (TSSM) |
| DIR-T | Titan dirigible | T2 | Titan ≤ 3 km | 40×10 m ellipsoid ENV-F2 (2,050 m³ / 78 m² / **0.05**) | H2 (inert: no free O2 on Titan) | **10 t** | 8 m/s on 7.8 kW; **0.027 kWh/t·km** — Titan's railroad; moors to MAST |
| BLN-M | Mars science balloon | T2 | Mars < 6 km | ENV-MSP (5,000 m³ / ~280 m² / 0.5) | H2 | 60 kg | logistics-useless by design (10 t payload would need 670,000 m³) |

### 1.8 Marine craft

| ID | Name | Tier (node) | Mass | Hull | Power | Performance | Anchor |
|---|---|---|---|---|---|---|---|
| BOAT-T | Shoreline skiff | T2 | 0.8 t + 1 t cargo | H1, V_hull 4 m³ | STO-SS 30 kWh | 4 m/s; 150 km; sea-state ≤ 2 | TiME |
| SUB-T | Titan submarine | T3 (VH-07) | 1.5 t, 6 m | H1 | NUK-RTG-S ×3 ≈ 330 We; ~6 kWt rejected via SUB-FIN | 1 m/s; 90-day / 2,000 km legs; 300 m depth | NASA GRC COMPASS |
| BARGE-T | Methane barge + tug | T4 [SPEC: missing anchor, not exotic physics] | 6 t tug + 350 m³ barge (30×5 m, 1.5 m draft, 7.5 m² submerged frontal) | H1, FLT-1 cells | V-10, 30 kW installed; ~21.5 kW cruise + 3.5 kW hotel | 100 t @ 2.5 m/s; **0.028 kWh/t·km** | displacement physics |
| CRYO-E | Ice-penetrating cryobot | T3 (≈40 kWt SLUSH) → T4 [SPEC] @ 100 kWt (VH-08) | 2.2 t, Ø 0.26 m × 5 m | melt head | 100 kWt fission core (09) | 100 m/day; 15 km/~150 d, 25 km/~250 d; repeater pucks every 500 m; **A3 only** | Philberth/SLUSH |
| ROV-E | Europa under-ice ROV | T4 [SPEC] (VH-08) | 0.9 t | **H3 (40 MPa)** | NUK-RTG-S + 20 kWh | 0.5 m/s; deployed by CRYO-E at shell base (~30 MPa) | SWIM/Orpheus |
| (ROV-E-ABYSS) | Ocean-floor variant | T4 [SPEC] (C20: IN v1) | TBD Pass 2 | **H4 (100+ MPa)** | TBD | full ocean-floor traversal; content design Pass 2/Phase 5 | — |

### 1.9 Control & autonomy fit-kits

| ID | Kit | Tier | Mass | Grants |
|---|---|---|---|---|
| CTL-A2 | Teleop package | T2 (05 A2) | 20 kg + comms part | TELEOP mode, η per 05 F-2 |
| CTL-A3 | AutoNav package | T3 (11 IN-09) | 35 kg | AUTONAV: 0.5× v_max, 24/7, exception queue |
| CTL-CNV | Convoy follower | T2 | 8 kg | follow leader, 5:1 |

### 1.10 Garage/bay modules (vehicle-side spec; 07 owns the habitat module)

| Bay | Fits | Functions |
|---|---|---|
| VEH-PAD (T0, 0 t) | any | park, umbilical charge; full exposure (V-24d applies) |
| VEH-BAY-S (T1, pressurizable) | VC-1/2 | service, dust wash (−5 D), thermal shelter |
| VEH-BAY-L (T2) | VC-3/4 | + on-site Motor Pool edits, battery-pallet swap (10 min) |
| SUB-DOCK (T3, shoreline) | boats/sub | hull thaw (AL-5 logic), O2 bunkering, sonar offload |
| MAST (T2) | dirigibles | mooring, gas top-off, cargo crane |

---

## 2. PHYSICS — the one formula set

All formulas are body-agnostic; differences emerge from data (g, ρ(h), T, terrain).
Inputs: g = μ/R² from ephemeris bodies; ρ(h) from `atmosphere.density()`; sector
`terrain_class / slope_sigma / rock_abundance` from 03 (NOT yet in code).

### 2.1 Ground locomotion

```
V-1   F_roll  = Crr · m · g                              [N]   (on slope: Crr·m·g·cosθ)
V-1a  p_ground = (m·g / N_sets) / A_contact              [Pa]  per locomotion set
V-2   F_aero  = 0.5 · ρ · Cd · A_front · v²              [N]   skip when ρ < 0.1
        A_front = frontal grid cells × 1 m²; Cd 0.8 boxy, 0.5 faired (FAIR-1)
V-3   F_grade = m · g · sinθ                             [N]   downhill negative; regen η = 0.5
V-4   P_drive = (F_roll + F_aero + F_grade) · v / η_drive    η_drive = 0.65 (T0–T1), 0.72 (T2+)
V-5   E_km    = (F_roll + F_aero + F_grade)/(3600·η_drive) + P_hotel/v_kmh   [kWh/km]
V-5a  P_hotel = Σ idle loads: avionics 60 W grid-built / 25 W integrated (<100 kg; also the
        hibernation floor) + cab ECLSS 1.5 kW per 2 crew + V-11 heater at sector T + part idles
V-6   θ_max  = atan(μ − Crr)                             [deg] traction slope limit
V-7   d_stop = v² / (2·μ·g)                              [m]   mass cancels; low g = long stops
V-8   v_max  = k_t·√g   k_t = 2.8 raw / 4.5 compacted / 8.0 sintered road    [m/s]
```

**Terrain table** (the data half of the model; calibrated so LRV reproduces ~92 km):

| terrain_class | Crr | μ | Bearing kPa | Special |
|---|---|---|---|---|
| Loose regolith (MARE/HIGHLAND) | 0.15 | 0.6 | 25 | lunar/asteroid default |
| Duricrust plains (Mars default) | 0.10 | 0.6 | 80 | sand-trap roll 5%/km near DUNE only when p_ground > bearing |
| DUNE | 0.20 | 0.4 | 7 | speed cap 0.5×; Spirit's killer (15 kPa rover > 7 kPa) |
| ICE_PLAIN | 0.04 | 0.25 (0.45 studded) | 500 | hard cryo-ice ≈ rock |
| CHAOS/blocky | 0.25 | 0.6 | 200 | wear ×2; speed cap 0.3×; puncture rolls above 0.3× v_max |
| Titan shoreline/tholin sand | 0.12 | 0.5 | 40 | |
| Venus basalt plain | 0.12 | 0.5 | 300 | T3 refractory only; lifetime clocks not km wear |
| Compacted track (50 passes) | 0.06 | 0.7 | 150 | persists per site map |
| Sintered road (05/07 build) | 0.02 | 0.8 | 600 | 5–7× range; the infrastructure pull |

Speed governance: route planner caps v so `d_stop ≤ 0.5 × sensor_range`
(50 m robotic / 120 m crewed daylight / 40 m night-PSR). √g examples raw/road km/h:
Moon 12.8/36.6 · Mars 19.4/55.5 · Titan 11.7/33.5 · Ceres 5.2/15.0 · Earth 31.6/90.3.
Below g = 0.3 m/s² wheels are marginal: drive ≤ 5 km/h or hop.

Calibration anchors (must hold in tests):
- LRV, Moon: 670 kg gross → 163 N → 0.089 kWh/km incl. 0.15 kW hotel @ 8 km/h → **88 km** on 8.7 kWh × 0.9.
- RVR-PRESS, Moon: 0.50/0.29/0.20 kWh/km → 170/293/425 km on 100 kWh × 0.85.
- Mars RTG rover: 110 We − 60 W avionics → v̄ = 50·0.65/371 ≈ 0.09 m/s ≈ 0.3 km/h.
- 18 t Mars hauler, duricrust: 6.68 kN → 2.9 kWh/km.
- Earth sanity: Crr 0.008 → 0.034 kWh/gross-t·km ≈ real e-trucks.

### 2.2 Vehicle power (09 catalog, mounted unmodified)

Storage: STO-LI 150 Wh/kg (T0) · STO-SS 250 (T1) · STO-LS 350 surge (T2) · STO-RFC 2.0 kWh_e/kg
reactants · NUK-RTG-M/-S · NUK-KP1/KP10 (VC-4/5 only). Li packs **cannot charge < 273 K**
(heater is P0). Usable fraction: 0.85 rechargeable, 0.9 primary cells.

```
V-9   Methalox ICE/turbine (T2): 1 kg CH4 + 4 kg O2 → 0.83 kWh_mech per kg reactants (η 0.30)
V-10  Titan O2-breather (T4 [SPECULATIVE]): carry O2 only, ingest ambient CH4:
        1 kg O2 → 1.04 kWh_mech (η 0.30). Exhaust vents as snow, not ledgered.
```
Per-kg-carried comparison the UI surfaces: battery T1 0.25 · RFC 2.0 · methalox 0.83 · Titan O2 1.04 kWh/kg.
Recharge: base umbilical (pack max rate) · onboard solar (09 f_atm; Titan ≈ decoration) ·
swap pallet T2 (300 kWh STO-SS module, 10 min at a garage; pallet circulation is an 05 route).

### 2.3 Thermal survival

```
V-11  Q = U · A_surface · (T_in − T_out)   [W]
      U = 0.3 (MLI, vacuum only) · 1.0 (aerogel+gas barrier, Titan/Mars) · 2.5 (bare metal in atmo)
```
- Titan ΔT ≈ 200 K: 30 m² cab loses ~6 kW aerogel / ~15 kW bare. RTG/Stirling/combustion vehicles self-heat from waste kWt; battery vehicles pay V-11 from the pack.
- Lunar night (354 h) strategies: (a) RTG kWt; (b) hibernation P_surv = V-11 + 25 W floor; (c) **thermal wadi** STO-WADI holds ≥ ~245 K on ~2 kWt bleed (clears 233 K damage line; pack trickle-heats last 30 K to the 273 K charge threshold); (d) garage (no exposure).
- Venus surface / Mercury noon: **09 H-5 endurance clocks**, not steady state — pre-T3: 2–8 h (Venera-13 127 min anchor); T3 SiC: 60-day clocks. Mercury twilight band avoids the clock (terminator advances 3.6 km/h at the equator — a crawler outruns sunrise forever).
- Every part inherits 09 H-8 `[T_min_op, T_max_op, T_survival]`; planner refuses violating routes unless an enclosure covers the part.
- Battery brick rules: damage (−30% capacity/event) if pack < 233 K with heater unpowered > 6 h, OR any charge/discharge attempt < 273 K.

### 2.4 Atmospheric flight (one formula set, all bodies)

```
V-12  L = 0.5·ρ·v²·S·C_L                  level flight: L = m·g
V-13  v_stall = sqrt(2·m·g / (ρ·S·C_Lmax))            C_Lmax = 1.4 (T0–T2), 1.8 (T3)
V-14  P_hover = (m·g)^1.5 / (η_h·sqrt(2·ρ·A_disk)) + P_fix
        η_h = 0.29 (T0–T1) / 0.42 (T2+);  P_fix = V-5a avionics (25 W integrated / 60 W grid)
V-15  P_cruise = m·g·v / ((L/D)·η_prop)                L/D 10/15/20 by tier T0–T1/T2/T3; η_prop 0.75
V-16  v_tip = ω·R ≤ 0.75·a_sound(body)                 Mars a ≈ 240 m/s → big slow rotors
```
Calibration: Ingenuity (1.8 kg, A 1.15 m², ρ 0.016, g 3.71) → 90 W ideal / 0.29 + 25 W ≈ **335 W** ✓.

**Per-body feasibility (indices vs Earth SL; hover = (g^1.5/√ρ)ₙ, stall = (√(g/ρ))ₙ):**

| Body/station | ρ | g | Hover idx | Stall idx | Verdict |
|---|---|---|---|---|---|
| Earth SL | 1.225 | 9.81 | 1.00 | 1.00 | baseline |
| Mars datum | 0.016 | 3.71 | 2.0 | 5.4 | gram-payload scouts only; ρ falls e× per +11 km — no highland flight; **no Mars cargo aviation, ever** (deliberate tech-tree hole) |
| Mars −7 km basins | 0.028 | 3.71 | 1.5 | 4.1 | basin-hugging courier routes |
| Venus 54 km | 1.05 | 8.87 | 0.93 | 1.03 | Earth-like aviation habitat |
| Venus surface | 64.8 | 8.87 | 0.12 | 0.13 | aero-easy, thermally lethal (T3 robotic) |
| Titan surface | 5.3 | 1.35 | **0.025** | 0.18 | flight ~40× cheaper/kg than Earth; primary logistics layer |
| Moon/Mercury/vacuum | 0 | — | ∞ | ∞ | hoppers only |

### 2.5 Buoyant flight

```
V-17  m_payload = V_env·(ρ_atm − ρ_gas) − m_envelope ;  ρ_gas = P·M_gas/(R·T_gas), R = 8.314
```
Lifting-gas lift (kg/m³, at station P,T):

| Site | ρ_atm | H2 | He | Breathable air | Hot ambient gas ΔT+50 K |
|---|---|---|---|---|---|
| Titan surface (146.7 kPa, 94 K) | 5.3 | **4.9** | 4.6 | warm 290 K habitat air ≈ **3.5** | 1.8 (MMRTG real ΔT 5–10 K → 0.27–0.55) |
| Venus 54 km (60 kPa, 300 K — canon P) | 1.05 | 1.00 | 0.95 | **0.35–0.42** (size with 0.35) | 0.15 |
| Mars datum (0.61 kPa, 210 K) | 0.016 | 0.015 | 0.014 | — | 0.003 |
| Earth SL | 1.225 | 1.14 | 1.06 | — | 0.18 |

Altitude control: superpressure = fixed band; variable-altitude/Montgolfière = ±5 km @ 0.5 m/s.
Drift = wind vector per band (03 owns): Venus 54 km zonal 65 m/s · Titan surface ≤ 1 m/s,
low-alt 2–5 m/s prograde · Mars 5–30 m/s gusts. Powered dirigibles add V-15 airspeed with
envelope Cd ≈ 0.05. Mars wind myth: q at 30 m/s gale = 7 Pa — never tips vehicles, only lifts dust.

### 2.6 Suborbital hops (airless bodies)

```
V-18   v_launch = sqrt( (μ/R_p) · 2·sin(Ψ/2) / (1 + sin(Ψ/2)) ),  Ψ = d/R_p   [m/s]
V-18a  short hop (d ≪ R_p): v_launch ≈ sqrt(g·d);  Δv_hop ≈ 2.2·sqrt(g·d)
V-19   Δv_hop = 2 · v_launch · 1.10      (boost + propulsive landing + 10% margin)
```
Δv table (m/s): 1 km — Moon 89 / Mercury 134 / Ceres 36 / Europa 80 / Enceladus 23;
10 km — 281/424/114/252/74; 100 km — 873/1318/339/781/218; 500 km — 1851/2830/643*/1650/—;
1000 km — 2458/3830/—/2177/—. (— = beyond ¼ circumference: orbit instead; * near-orbital, UI
suggests a lander.) Orbit-and-land ≈ Moon 3800 / Mercury 6100 / Ceres 720 / Europa 2900 / Enceladus ~370.

**Boundary rule**: flight plan past Ψ = π/2 or local orbital velocity → it's a lander (06's
domain). Hoppers get a range ring, never orbit lines.

Propellant per hop: 02 rocket equation on landed mass + remaining prop. Energy honesty for the
planner: hopping ≈ **700–1,200× the energy of driving** (5 t × 200 km Moon: 2.4 t methalox
≈ 16,900 kWh vs ~14 kWh on road) — buys time (9 min vs 6 h) and access. Hop triggers:
CHAOS/PSR-wall crossing · g < 0.3 · one-way > 3× vehicle range · tempo (rescue/windows).

**2.6.3 Plume ejecta (C23)**: off-pad launch/landing — within 200 m: abrasion event on exposed
equipment (condition −2%, solar −1% permanent, dust ledger +1); within 50 m: exposed unrated
parts roll 30% for −15% condition per event. Landing pads suppress entirely.

### 2.7 Marine

```
V-20  F_B = ρ_sea · V_disp · g    float ⇔ m_gross ≤ 0.95·ρ_sea·V_hull (V-0c)
V-21  P(d) = P_surf + ρ_sea·g·d   (Titan: 146.7 kPa + 0.74 kPa/m; 300 m ≈ 3.7 atm — trivial)
Drag:  V-2 with marine Cd — streamlined sub 0.10, boat hull 0.15, barge 0.4
Prop:  P_prop = F·v / η_prop_marine ;  η_prop_marine = 0.60 (T2), 0.65 (T3)  [NOT η_drive]
```
Titan seas (canon mean ρ_sea = 550): Ligeia 520 / 170 m · Kraken 580 / ≥300 m · Ontario 600 / ~50 m.
Hull classes: H1 0.5 MPa (any Titan depth — the driver is 94 K, not pressure) · H2 5 MPa ·
H3 40 MPa (Europa shell base ≈ 30 MPa) · H4 100+ MPa (ocean floor, **IN v1 per C20**, T4 [SPEC]).
Overpressure: leak events 1%/min per 10% over rating.

SUB-T closure check: 1.1 m² frontal, Cd 0.10, 1 m/s → 30 N → 50 W prop + 280 W hotel = 330 W
= NUK-RTG-S ×3; the units' ~6 kWt also covers the ~12 m² hull's ≈2.4 kW V-11 loss. Speed ∝ P^⅓.

Cryo-sea special rules (gamified NIAC findings):
1. **N2 effervescence**: wetted skin flux > 0.5 kW/m² → sonar/survey −50%, drag +20%, buoyancy ±2% V_disp noise. Mitigation: SUB-FIN above waterline.
2. **Cryo materials**: elastomer seals forbidden at 94 K — metal bellows/dry bearings (T3) or 10%/dive seal-crack events.
3. **Sea states**: 0–2 normal (mirror-flat per Cassini); storm events → state 4: surface speed ×0.5, capsize roll 10%/h VC-1 / 3%/h VC-2; subs dive > 10 m and ignore. (C20: a real wave model ships v1 — Phase 5 heavy item; sea-state numbers remain the planner abstraction.)
4. Shore interface: Submarine Dock (07) + Sea Pumps (04); boats beach-launch via ramp part.

### 2.8 Cryobot melt descent

```
V-22  E_melt_vol = ρ_ice·(c̄_p·ΔT + L_f)·k_loss   [J/m³]
        ρ_ice 920 · c̄_p 1.5 kJ/kgK (100→273 K mean) · ΔT 173 K · L_f 334 kJ/kg → 546 MJ/m³ ideal
        k_loss = 3.0 (lateral conduction + tether/refreeze) → 1.64e9 J/m³ effective
V-23  v_descent = P_t / (A_probe · E_melt_vol)    [m/s]
```
Catalog CRYO-E: Ø 0.26 m (A 0.053 m²), 100 kWt → 4.2 m/h ≈ **100 m/day → 15 km in ~150 d,
25 km in ~250 d**. No teleop through ice: frozen-in repeater pucks every 500 m, A3 mandatory.
Refreeze entombment if descent halts > 48 h with heat < 20 kWt. On breakthrough: releases
ROV-E. Planetary-protection sterilization = build-cost multiplier (12), not a mechanic.

### 2.9 Wear (feeds 05 condition C ∈ [0,1], MTBF, spares — adopted verbatim; A5 layering)

```
V-24a wheels/tracks: ΔC/100 km   = 0.4% wheels / 0.6% tracks × terrain_mult × dust_mult  (tracks: terrain_mult cap 1.5)
V-24b rotors:        ΔC/10 fl-h  = 0.3% × dust_mult
V-24c hulls:         ΔC/10 dive-h= 0.2% × sea_state_mult (states 0–2 ×1.0; state 4 ×2.0; effervescence-active ×1.2)
V-24d thermal cycle: ΔC += 0.1% per survival-band night cycle (additive, independent)
terrain_mult: road 0.5 · regolith 1.0 · DUNE 1.5 · CHAOS 2.0 · ICE 0.8 · unlisted 1.0
dust_mult: Moon 1.5 · Mercury 1.5 · Mars 1.0 · Titan 0.7 · Venus-cloud 2.0 (acid) · icy moons 0.8 · other 1.0
```
Venus *surface* vehicles skip V-24 → 09 H-5 clocks. Garage = full repair rate; field = ×3 spares ×2 time, weather-gated.

---

## 3. OPERATIONS

### 3.1 Range & endurance

Range = usable energy / E_km (V-5), usable = 0.85 pack (0.9 primary). RTG vehicles: range ∞,
speed bounded by `v̄ = P_net·η/F_roll` with battery-buffered bursts. Combustion: range by tankage
via V-9/V-10. Hoppers: hops-remaining via rocket equation. Aircraft: leg energy = P_hover·t_hover
+ P_cruise·t_cruise vs pack; balloons: endurance = battery/solar vs hotel only.

Duty-cycle caps (Mars RTG rover, canonical): A2 batch from Earth **0.1–0.35 km/sol** ·
local A2 (η≈1, 6 h window) **~2 km/sol** · A3 AutoNav 24/7 **~7–8 km/sol** (energy cap).

### 3.2 Control modes (consumes 13 comms graph; vehicles add NO new comms model)

| Mode | Requires | Capability |
|---|---|---|
| CREWED | crew aboard | full v_max, all tasks, no link |
| TELEOP (A2 joystick) | link + operator | speed/work × η = 1/(1 + RTT/60 s) (05 F-2, T_atom 60 s driving); **refuse standing ops below η 0.2** |
| A2 BATCH | link at uplink/downlink only | sol-plan supervised autonomy; exempt from F-2; drive cap 0.35 km/sol |
| AUTONAV (A3, CTL-A3) | link at dispatch/arrival | 0.5× v_max, 24/7; exceptions halt and page (05 queue) |
| A4 (endgame) | 05 autonomous-complex node | ledger-mode only; no per-vehicle events |
| CONVOY | leader any mode | followers at leader's speed, 1:5 |

Worked η: Moon RTT 2.56 s → 0.96 (Lunokhod) · Mars best 6.2 min → 0.14 (**below refusal — Earth
joystick at Mars never works**; A2 batch is the misery driving the Act-3 A3 push) · Saturn ~160 min
→ A3/crewed only. Link loss: ground safe-halts (brake + beacon); aircraft RTB at A2+ (A1 crashes —
UI refuses BVR dispatch, one signed override allowed); **balloons keep drifting** — recovery
becomes an intercept problem.

### 3.3 Crew rules

- **Walkback** (unpressurized crewed): max radius from pressurized refuge = (suit endurance − 3 h reserve) × 2 km/h → EMU 8 h = **10 km**. Planner hard-refuses; EVA override exists but suit failure beyond walkback is unsurvivable by design.
- Pressurized rovers are their own refuge (radius = 08 consumables + rescue-asset range; 14-day sorties).
- Suitports: 0.1 kg gas + 0.1 D dust per cycle (vs 0.5 kg + 1.0 D airlock).
- Direct drive (real-time only): WASD with V-6/V-7/V-8 enforced; TELEOP shows the RTT-delayed ghost (move-and-wait above 5 s RTT).

### 3.4 Traverse & route mechanics (the planner is the primary verb)

- Ground: waypoint routes on 03 S-7c sector tiles; cells shaded by Crr/slope/clearance feasibility; quote time, kWh/propellant, wear, walkback/abort compliance. Execute under warp as analytic segments with scheduled events: arrival, recharge, breakdown roll, comm-occlusion pause, storm interrupt (13 event-queue contract).
- Flight: altitude is a scalar band `ALT ∈ {0,1,2,3}`; ρ/T/wind sampled at band midpoint. Mars: ≤200 m / 200 m–1 km / — (no ALT 3). Titan: ≤200 m / ~1 km / 3–8 km. Venus: — / 50–56 km / 56–62 km (planner clamps at 45 km floor; 42–45 km warning band 2%/min condition; <42 km destruction). Landing cell: slope ≤ 5° and rocks ≤ clearance unless VTOL.
- Hops: range ring + Δv/propellant quote; landing-cell check pre-commit; plume circles at both endpoints. Hop landing failure (slope >10° or rock roll): tip/crash cascade, 50% cargo survival; HOP-P always re-hops on its 20% reserve.
- Dive: depth tape, hull-margin bar (V-21), effervescence warning, sonar swath painting bathymetry (feeds 11 DSC-14).
- Science traverse: ED for SurfaceMobility/AeroFlight accrues from km driven / flight & dive events (11); vehicle-gated arcs: skylight hopper survey (DSC-03), sub sonar maps (DSC-13/14), cryobot ocean breach.
- Freight link costs published to 05 (kWh per gross t·km): road 0.012–0.034 · dirigible 0.027 · barge 0.028 · plane 0.04 (payload) · hop ~10³× road. Payload-basis at 0.55 fraction: Moon road 0.025 / Mars road 0.057 / Titan road 0.021 / Moon regolith 0.19 / Mars duricrust 0.29.

### 3.5 Hazards & failure modes (event implementations)

| # | Failure | Trigger → effect |
|---|---|---|
| 1 | Tip-over | V-0b violated → immobilized, 20% part-damage roll; recovery = crane or 4 crew-h; live tilt icon past θ_tip − 5° |
| 2 | Embedding | DUNE/soft, p_ground > bearing: 5%/km roll; escape ×3 energy, 30%/attempt; tow needs 1.5× embedded F_roll traction |
| 3 | Battery brick | <233 K unpowered >6 h, or charge attempt <273 K → −30% capacity/event; pre-dusk alarm mandatory UI |
| 4 | Night/storm strand | solar vehicle in night/global storm → hibernation roll/24 h = f(insulation, RTG, wadi) |
| 5 | Wheel destruction | CHAOS above 0.3× v_max → puncture; wheel-dead limps 0.3× at +50% E_km |
| 6 | TELEOP link loss | safe-halt; aircraft RTB (A2+) or crash (A1); balloons drift on |
| 7 | Hop landing failure | see §3.4; plume violations damage own base — pads not optional |
| 8 | Titan cryo-seal | skipped warm-lock/elastomers at 94 K → 10%/cycle leak/seize; sub ballast seize → surfaced, dives locked |
| 9 | Effervescence blind-out | flux >0.5 kW/m² sustained → sonar −50%, survey halved, bubble noise; throttle or surface |
| 10 | Cryobot refreeze | halt >48 h, heat <20 kWt → probe lost (repeater string survives) |
| 11 | Venus clocks | flight floor 45 km; 42–45 km 2%/min damage; <42 km destroyed; surface past H-5 clock → loss; acid unwashed >30 d → optics degradation |
| 12 | Mercury crawler strand | drivetrain failure in daylight starts H-5 noon clock — slowest catastrophe in the game |
| 13 | Walkback violation | hard refusal; override → unsurvivable suit failure beyond radius |
| 14 | Vehicle-as-cargo | crashes per 06 cargo rules; driving onto a fueled pad triggers plume both ways; ramps refuse >15° tilt |
| 15 | Entity cap | >~50 active vehicles/site → ledger mode (statistical wear/throughput); global entity cap ≤2,000 (13) |

### 3.6 Progression beats (for content sequencing)

T0 Act 1: RVR-SCOUT + BLN-V0 proven tech, Earth proving grounds farm ED. T1 Act 2 Moon: LRV
moment, haulers, hoppers for PSR, dozer/crane/drill; **night-survival arc** (dead fleet → wadis
→ RFC → garages); Earth teleop η 0.96 sandbox. T2 Act 3 Mars: pressurized sorties, rotorcraft
scouts, methalox haulers, swap pallets; light-lag forces A3; storms teach fission. T2–T3 Act 4:
Venus balloon ladder + VH-10 crawler (Venera-13 trophy), Mercury crawler, Ceres hopper doctrine.
T3–T4 Act 5: **Titan is the vehicle act** (rotorcraft → dirigible network → cargo planes →
boats → submarine → barges; HPF-T crown jewel); Europa cryobot ~150-day live event chain → ROV.
Endgame: A3/A4 ledger fleets; no new chassis at He3 tier — deliberate.

---

## 4. GAP vs CODE

### 4.1 What exists today (everything else is unbuilt)

| File | Has | Usable for |
|---|---|---|
| `aphelion/sim/environment/buoyancy.py` | ideal-gas ρ, Venus air-lift, Titan dirigible lift, Titan sub Archimedes, Titan wing lift | V-17 and V-20 **statics** seeds only — no V_env sizing vs envelope mass tiers, no ballast/trim dynamics, no V-0c validation, no per-sea ρ |
| `aphelion/sim/environment/atmosphere.py` | piecewise-exponential ρ(h), 6 bodies, interface altitudes | feeds V-2/V-12/V-13/V-14/V-17 directly (needs T(h) and P(h) added for ρ_gas and band ops; only ρ exists) |
| `aphelion/sim/comms.py` | RTT + η = 1/(1+RTT/τ), τ = 26 s | TELEOP needs the **driving T_atom = 60 s** variant (parameterize τ); 0.2 refusal line not implemented |
| `aphelion/sim/orbits/ephemeris.py` + content pack | per-body μ, R | surface g = μ/R² for every V formula; V-18 inputs |
| `aphelion/sim/power.py` | solar flux, radiator rejection, ledger Modules | V-0d closure + recharge ledger hooks exist in spirit; no STO-*/NUK-* vehicle-mountable catalog |
| `aphelion/sim/industry/routes.py` | orbital freighter legs | pattern/precedent for surface route legs; shares the ledger-arrival event idiom |
| `aphelion/sim/research.py` | tech tree from content pack | VH-00…VH-10 / IN-09 nodes plug in as data |

**No vehicle gameplay exists**: no chassis/Motor Pool, no ground locomotion, no terrain sectors
(03's terrain_class/slope_sigma/rock_abundance are nowhere in code), no hoppers, no rotorcraft,
no marine dynamics, no cryobot, no wear/condition system (05's C/MTBF also unbuilt), no garages,
no control-mode ladder, no route planner for surfaces.

### 4.2 Discrepancies in existing code (reconcile before reuse — design canon wins)

1. `buoyancy.py LCH4_DENSITY = 570` — canon is **mean ρ_sea = 550** with per-sea 520/580/600 (Ligeia/Kraken/Ontario). Replace constant with a per-sea table + 550 default. Test `test_phase5_environments.py` asserts neutral at 570 — update with the canon change.
2. `titan_dirigible_lift_kg_m3` evaluates H2 at **200 K** → lift ≈ 5.08; canon table says **4.9** (ambient ~94 K gas). Default T_gas to ambient; warm-gas is a Montgolfière (MGF-T) mechanic with ΔT 5–10 K, not the dirigible default.
3. `venus_lift_kg_m3` defaults 52.5 km / 70 kPa; canon station is **54 km / 60 kPa / 300 K**, sizing lift **0.35** conservative. Align defaults; keep the function form.
4. `atmosphere.py` anchors: Mars ρ0 1.5e-2 vs canon **0.016**; Venus 65.0 vs **64.8**; Titan 5.28 vs **5.3**. Sub-% nits, but DECISIONS A2 (byte-identical shared numbers) requires one reconciliation pass; also add Mars ±50% seasonal ρ scaling hook (C24).
5. `comms.py TELEOP_TAU_S = 26` is the general work atom; driving uses **60 s** (05 F-2 T_atom driving). Parameterize, don't fork the formula.

### 4.3 Where each formula slots (proposed module map, mirrors existing layout)

| New module | Implements | Consumes |
|---|---|---|
| `sim/vehicles/chassis.py` | V-0, V-0a–d, chassis classes, blueprint integration | 06 grid math (vessels), content pack part rows |
| `sim/vehicles/locomotion.py` | V-1…V-8, terrain table, embedding/puncture rolls | terrain sectors (new, 03), ephemeris g |
| `sim/vehicles/terrain.py` (or `environment/`) | terrain_class/slope_sigma/rock_abundance/bearing per sector; compacted-track persistence | 03 data pack (new) |
| `sim/vehicles/powerplant.py` | V-9/V-10, pack usable fractions, recharge/swap, V-0d | `sim/power.py`, 09 catalog rows (new content) |
| `sim/vehicles/thermal.py` | V-11, night strategies, battery 273/233 K rules, H-5 clocks | `sim/power.py` radiators, 09 bands |
| `sim/vehicles/flight.py` | V-12…V-16, ALT bands, feasibility readouts | `environment/atmosphere.py` (+T/P extension) |
| `sim/vehicles/buoyant.py` | V-17, drift, altitude control | extend `environment/buoyancy.py` (keep, fix §4.2) |
| `sim/vehicles/hops.py` | V-18/18a/V-19, plume rule (C23), boundary rule | ephemeris μ/R, 02 engine rows |
| `sim/vehicles/marine.py` | V-20/V-21, marine drag/prop, effervescence, sea states, ballast | `buoyancy.py` statics, sea table (03) |
| `sim/vehicles/cryobot.py` | V-22/V-23, descent campaign events, repeater pucks | 09 heat sources |
| `sim/vehicles/wear.py` | V-24a–d, service costs | 05 condition/MTBF (also unbuilt — build the 05 layer first or together; A5 interface test is a Phase-1 deliverable) |
| `sim/vehicles/control.py` | mode table, η_teleop(τ=60), refusal line, safe-halt/RTB/drift | `sim/comms.py` (parameterized), 05 ladder |
| `sim/vehicles/traverse.py` | route segments, analytic warp integration, event scheduling, freight link costs | 13 event queue, `industry/routes.py` idiom |
| content pack `vehicles.json` etc. | every §1 catalog row as data | `content/loader.py` + `schema.py` extension |

### 4.4 Build-order recommendation

1. Terrain sectors + `locomotion.py` + LRV/SEV calibration tests (anchors in §2.1 are the test fixtures).
2. Catalog/content rows + chassis validation (V-0) — enables Motor Pool UI later.
3. Hops (small, self-contained, reuses ephemeris + 02 rows) + plume rule.
4. Flight + buoyancy reconciliation (fix §4.2 first; Ingenuity 335 W is the test fixture).
5. Wear/condition (with 05's layer), control modes, thermal survival.
6. Marine + cryobot (Phase 5 with C20 heavy items: waves, H4, legged parts).
