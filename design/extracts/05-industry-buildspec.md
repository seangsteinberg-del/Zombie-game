# BUILD SPEC — 05 Industry & Logistics

Extracted from `design/05-industry-logistics.md` (design-complete draft) + `design/DECISIONS.md`
(DECISIONS wins conflicts). Target: implementable without re-reading the source doc.
Conventions: all recipes normalized **per 1.00 t of primary output**; mass balance must close
within 0.5% at load time (`sum(inputs) == sum(outputs) + sum(byproducts) + loss`); "a crew-h +
b robot-h" means **both required simultaneously** (never either/or).

---

## 1. PRODUCTION CHAINS

### 1.1 New intermediate resources (extend canonical list — exact spellings)

| Resource | Definition |
|---|---|
| `MetalStock` | Stock shapes (plate/bar/tube/extrusion/wire/powder); shippable midpoint refining→parts |
| `Components` | Machined/printed mechanical elements (gears, housings, valves, fasteners) — single SKU per DECISIONS B12 |
| `Wafers` | Finished, diced, packaged semiconductor devices, mass-accounted in kg of fab output |

Spares are NOT a resource — maintenance consumes `MachineParts` / `Electronics` /
`StructuralParts` / `Polymers` per module spares-split (§3.6 below). `FoodRations` and
`MedSupplies` are made here too (consumables line) but are canonical/08-declared resources.

### 1.2 Chain topology

```
IronSteel/Aluminum/Titanium/Copper → FOUNDRY&MILL → MetalStock
MetalStock → MACHINE SHOP / LPBF PRINTER → Components
MetalStock (+Polymers) → WAAM CELL → StructuralParts
Components + MetalStock → ASSEMBLY HALL → MachineParts
Methane + Oxygen → CHEM PLANT → Polymers (+Water, CO2, H2 byproducts)
Silicon → WAFER FAB [T3] → Wafers ;  Wafers + metals/Polymers/Glass → ELEC ASSY → Electronics
Until T3: Wafers (and pre-line, finished Electronics) IMPORTED FROM EARTH — the campaign umbilical.
```

### 1.3 Recipe schema (sim data structure, JSON)

```json
{
  "id": "machine_parts_std", "module": "assembly_hall", "tier": "T2",
  "inputs_t": {"Components": 0.62, "MetalStock": 0.43},
  "outputs_t": {"MachineParts": 1.00}, "byproducts_t": {}, "loss_t": 0.05,
  "energy_kWh_per_t": 300, "heat_fraction": 0.95,
  "labor": [{"type":"crew","h_per_t":4.0,"substitutable":false},
            {"type":"robot","h_per_t":16.0,"crew_may_substitute_at":1.0}],
  "min_automation": "A1", "wear_per_t": 1.0, "env": "pressurized"
}
```

Defaults when not listed: `min_automation` = rung in module Labor column (else A0), `env` =
module Env, `wear_per_t` = 1.0, `heat_fraction` = 0.95. No per-recipe overrides currently exist.

### 1.4 Module state machine & throughput

`OFF → STARTING(warmup) → RUNNING ↔ {STARVED, OUTPUT_BLOCKED, DEGRADED} → FAILED → MAINTENANCE → OFF`.
Warmup: foundry 6 h at full power; wafer fab 72 h re-qualification after ANY power interruption;
all others 0.5 h.

```
R_eff = R_nom × f_power × f_labor × f_condition × Y      [t/day]            (F-1)
f_power     = clamp(P_supplied / P_required, 0, 1); module trips OFF below 0.3
              foundry special: f_power < 0.8 continuously >1 h while RUNNING → freeze → FAILED
P_required  = P_hotel + energy_kWh_per_t × R_nom / 24    [kW]  (generates the §1.6 Power column)
f_labor     = min over labor entries of clamp(supplied/required, 0, 1)
f_condition = 1.0 while C ≥ 0.5, else C/0.5
Y           = 1.0 except wafer fab ramp: Y(d) = 0.9 − 0.7·e^(−d/60)         (F-Y)
```

Buffers: input + output, each sized 3 × daily nominal flow (per-module override allowed).
Time warp: analytic integration with events at buffer-full / feedstock-empty / failure boundaries.

### 1.5 Recipes (complete §4.2 table)

| ID | Module | Tier | Inputs (t) | Outputs (t) | Loss (t) | kWh/t | Labor h/t crew/robot |
|---|---|---|---|---|---|---|---|
| stock_std | fab_foundry_mill | T1 | IronSteel 0.68, Aluminum 0.22, Titanium 0.05, Copper 0.05 | MetalStock 0.97 | 0.03 | 700 | 0.4 / 2.4 |
| stock_lunar | fab_foundry_mill | T2 | Aluminum 0.55, IronSteel 0.35, Titanium 0.10 | MetalStock 0.96 | 0.04 | 780 | 0.4 / 2.4 |
| stock_nea | fab_foundry_mill | T2 | IronSteel 0.92, Copper 0.08 | MetalStock 0.97 | 0.03 | 650 | 0.4 / 2.4 |
| comp_machined | fab_machine_shop | T1 | MetalStock 1.04 | Components 1.00 | 0.04 | 1,500 | 16 / 32 |
| comp_printed | fab_printer_lpbf | T1 | MetalStock 1.06 | Components 1.00 (precision) | 0.06 | 30,000 | 2 / 12 |
| comp_poly | fab_printer_poly | T0 | Polymers 1.05 | Components 1.00 (low-load) | 0.05 | 400 | 4 / 0 |
| struct_waam | fab_waam | T2 | MetalStock 1.05, Polymers 0.02 | StructuralParts 1.00 | 0.07 | 6,000 | 1 / 12 |
| struct_basalt | fab_waam | T2 | BasaltFiber 0.60, Polymers 0.25, MetalStock 0.22 | StructuralParts 1.00 (surface-only rating) | 0.07 | 900 | 1 / 12 |
| machparts_std | fab_assembly_hall | T2 | Components 0.62, MetalStock 0.43 | MachineParts 1.00 | 0.05 | 300 | 4 / 16 |
| machparts_shop | fab_machine_shop | T1 | Components 0.65, MetalStock 0.42 | MachineParts 1.00 | 0.07 | 350 | 12 / 12 (slow path, ×0.25 module rate) |
| polymers_mto | fab_chem_plant | T1 | Methane 1.20, Oxygen 1.20 | Polymers 1.00; byp Water 1.22, CO2 0.16, Hydrogen 0.02 | 0.00 | 1,500 | 0.5 / 3 |
| wafers_min | fab_wafer_fab | T3 | Silicon 1.60, Polymers 2.0, Copper 0.10, Nitrogen 30, Water 60 (gross) | Wafers 1.00; byp Nitrogen 24 (recovered), Water 54 (UPW loop, recovered) | 14.7 | 8,000,000 | 2,000 / 20,000 (min 10% of total hours crew) |
| electronics_std | fab_elec_assy | T1 | Copper 0.35, Polymers 0.30, Aluminum 0.19, Glass 0.11, IronSteel 0.07, RareEarths 0.02, Wafers 0.01 | Electronics 1.00 | 0.05 | 3,000 | 40 / 80 |
| ration_pack | fab_consumables | T1 | Biomass 2.10, Polymers 0.05 | FoodRations 1.00; byp Water 1.10 (recovered to 08 loop) | 0.05 | 1,800 | 2 / 6 |
| medsupplies_std | fab_consumables | T2 | Polymers 0.50, Electronics 0.30, Biomass 0.20 | MedSupplies 1.00 | 0.00 | 2,500 | 30 / 30 |

Notes:
- **Electronics long pole:** elec line itself is T1 (SMT mature), but the `Wafers` input is
  Earth-imported until T3 wafer fab; before a line exists, finished `Electronics` are imported.
- **Local-electronics ×1.3 mass penalty (DECISIONS B12):** Electronics built from local
  (micron-class) Wafers charge 1.3 t per 1.0 t specified at *installation time* (recipe
  unchanged; stacks with the in-situ derate). Retires at T3+ fab maturity (11's ladder);
  Earth-imported Electronics never pay it.
- **Wafer fab realism:** 8,000,000 kWh/t (≈8,000 kWh/kg, EPRI/Taiwan fab anchor at ~1.5 kWh/cm²
  incl. ~56% facility overhead); yield ramp F-Y restarts after commissioning or any major fault;
  output is micron-class devices (AIST Minimal Fab anchor, ~5 µm maskless litho).
- Pressure vessels, tanks, radiators etc. are 06/07 blueprints composed of these parts —
  no separate factory recipes.

### 1.6 Factory modules (complete §4.1 catalog)

Power (kWe) = P_hotel + recipe kWh/t × nominal rate / 24 (column is generated from formula —
§4.1/§4.2 cannot disagree). Env: P = pressurized, V = vacuum-rated, S = surface only.

| ID | Module | Tier | Env | Mass t | P_hotel kWe | Power kWe | Throughput | Labor /day |
|---|---|---|---|---|---|---|---|---|
| fab_printer_poly | Polymer printer farm | T0 | P | 0.8 | 2.6 | 3 | 25 kg/day Components(poly) | 0.1 crew-h |
| fab_printer_lpbf | Metal printer cell (LPBF) | T1 | P | 3.0 | 2 | 27 | 20 kg/day Components (precision) | 0.05 crew-h + 0.25 robot-h |
| fab_machine_shop | Machine shop | T1 | P | 8.0 | 3.75 | 35 | 0.5 t/day Components | 8 crew-h + 16 robot-h (A1+) |
| fab_foundry_mill | Foundry & mill | T1 | S | 25.0 | 14 | 160 (300 pk) | 5 t/day MetalStock | 2 crew-h + 12 robot-h |
| fab_chem_plant | Chemical plant | T1 | S/V | 15.0 | 15 | 140 | 2 t/day Polymers | 1 crew-h + 6 robot-h |
| fab_elec_assy | Electronics assembly line | T1 | P | 10.0 | 7.5 | 20 | 100 kg/day Electronics | 4 crew-h + 8 robot-h |
| fab_consumables | Consumables line | T1 | P | 6.0 | 4 | 42 (rations) / 9 (med) | 0.5 t/day FoodRations or 50 kg/day MedSupplies | 1+3 (rations); 1.5+1.5 (med) |
| fab_workshop | Pressurized workshop | T1 | P | 13.0 | 12 | 12 | hosts 2 small fab modules + repair bay (+25% repair speed) | — |
| fab_waam | Large-format WAAM/DED cell | T2 | P/V | 12.0 | 2.5 | 40 | 150 kg/day StructuralParts or Components(large) | 0.15 crew-h + 1.8 robot-h (A2+) |
| fab_assembly_hall | Parts assembly hall | T2 | P | 20.0 | 10 | 35 | 2 t/day MachineParts or StructuralParts finishing | 8 crew-h + 32 robot-h |
| fab_sinter_printer | Regolith sinter printer | T2 | S | 12.0 | 5 | 47 | 2 t/day in-place sintered structure (07 B-2 DEPLOY) | 0.5 crew-h + 8 robot-h (A2+) |
| fab_filament_winder | Basalt filament winder | T2 | S | 4.0 | 2 | 6 | 0.5 t/day wound shell in place | 0.2 crew-h + 4 robot-h (A2+) |
| fab_ice_caster | Ice casting rig | T2 | S | 3.0 | 2 | 8 | 5 m³/day ≈ 4.6 t/day cast ice in place | 0.1 crew-h + 4 robot-h (A2+) |
| yard_drydock | Orbital dry dock | T2 | V | 85.0 | 30 | 30 (180 pk, job-driven) | §3 job rates; 2 arm pairs, 3 gang slots; cargo_equipped | per job |
| fab_wafer_fab | Wafer fab (Minimal-Fab line) | T3 | P | 45.0 | 33 | 700 (900 pk) | 2 kg/day Wafers | 4 crew-h + 40 robot-h (min 10% crew) |
| fab_auto_complex | Autonomous factory complex | T3 | S | 120.0 | 398 | 600 | bundled A3/A4: 5 t/day MetalStock + 0.5 t/day Components + 2 t/day MachineParts; χ = 0.90 | 1 crew-h (exceptions) |
| fab_replicator_seed | Self-expanding industry seed | T4 [SPEC] | S | 250.0 | — | 1,500 | χ = 0.98; eats 10 t/day Regolith + imports 5 t Electronics per doubling; outputs a second 250 t seed every 2 yr | exceptions only |

- Size rule: "small" = ≤3 t (printer_poly, printer_lpbf) fits in a workshop; larger needs its own
  07 pressurized volume.
- Auto complex 600 kWe = 398 hotel + 202 bundled recipe power (foundry 146 + shop 31 + hall 25).
- The three surface-construction machines output *in-place structure*, not resources — 07 owns
  the build recipes (process energies: 500 kWh/t sinter, 150 kWh/t winding, 30 kWh/m³ ice).
- **Construction parts bill** (every §1.6/§2/§3 catalog item): installed mass splits
  **55% StructuralParts / 30% MachineParts / 8% Electronics / 7% Polymers**. Overrides:
  fab_wafer_fab 25/25/40/10; robots 25/45/25/5; depots 70/20/5/5; log_massdriver 60/30/8/2.
  Orbital items erect at the dry dock under §3.1 jobs; surface items run FABWELD/OUTFIT/
  COMMISSION from 07's construction pad at the same rates.

### 1.7 Recycling (DECISIONS B16)

T2 Recycler = **04 RX-22** (04 owns machine + recipe): 2 t, 19 kWe, 500 kg/day, 0.9 kWh/kg.
Reclaims **80%** of recipe `loss_t` streams, decommissioned-hardware mass, and worn-out parts
back to canonical resources; the 20% residue converts to Regolith (04 M-8); Electronics scrap
reclaims only as metal/RareEarths fractions. Does NOT reduce M_spares (F-9) — it cuts net
resource draw for making spares and tightens kit closure χ. This (not invented ore — DECISIONS
B15) is the sanctioned relief for scarce Copper. Without a co-sited Recycler, loss is destroyed.

### 1.8 Heat/power interface & in-situ derate

- Every factory's grid load = P_required (F-1). `heat_fraction` (0.95 default) of **total
  consumed electrical energy** must be radiator-rejected at the site (700 kW fab ⇒ ~665 kW heat).
- Heat cascade: foundry co-sited with 04 thermal-ISRU + `heat_cascade: true` reduces receiver
  demand by `min(0.20 × foundry heat, 0.15 × receiver demand)`; radiator load drops same amount.
- **In-situ derate (F-13):** locally built stand-ins for imported precision hardware (esp. 09
  arrays/radiators/power electronics) install at `m = k_insitu × m_catalog`; k = **4 (T2),
  3 (T3), 2 (T4)**. Derated mass goes through the construction parts bill; Electronics content
  stays imported until T3. Does NOT apply to already-ISRU-specified hardware (struct_basalt,
  07 sintered habs).

---

## 2. AUTOMATION LADDER

| Rung | Name | Tier | What it is |
|---|---|---|---|
| A0 | Manual EVA / shirt-sleeve | T0 | Crew + hand tools; pressurized workshop or suited EVA |
| A1 | Fixed robotic arms | T1 | Berthing arms + dexterous units on rails; crew console-supervised |
| A2 | Teleoperated mobile robots | T2 | Worker robots/rover-manipulators; light-lag is live |
| A3 | Supervised autonomy | T3 | Scripted task classes 24/7; humans clear exceptions |
| A4 | Autonomous factory complex | T3→T4 | Whole sites with kit closure χ ≥ 0.9; exceptions page a human |

**Labor rules (one convention):**
- All recipe labor entries required simultaneously; `f_labor = min(clamp(supplied/required))`.
- Crew may substitute for robot-h at `crew_may_substitute_at` (default 1.0 h/h). Robots NEVER
  cover crew entries (judgment/QA). Wafer fab floor: min 10% of total hours crew.
- **A1 supervision charge:** +0.1 crew-h per robot-h worked, same job. A2: operator shift IS the
  cost (1 operator : 1 robot, output × η_teleop, no extra charge). A3+: exception rule instead.

**A0 EVA cost rule:** 1 sortie = 2 crew × 6.5 h outside + 12 crew-h prep/post; per suit-sortie
0.59 kg Oxygen + 2.6 kg Water lost (08 §3.11 rates: 0.09 kg O2/h, 0.40 kg water/h × 6.5 h;
airlock gas/prebreathe stays on 08's ledger). **η_EVA = 0.52** (13 productive h / 25 crew-h).
Suits: 1 wear unit/sortie; overhaul at 25 sorties = 50 kg MachineParts + 10 kg Polymers +
40 crew-h. EVA assembly work rate 1.0× human.

**A2 teleop (F-2):** `η_teleop = 1 / (1 + RTT / T_atom)`, T_atom = 25 s dexterous, 60 s
driving/hauling. RTT from 03 geometry via 13 comms model.

| Operator → robot | RTT | η (dexterous) | Verdict |
|---|---|---|---|
| Same site / orbit→surface | <0.1 s | ≈1.0 | Full telepresence |
| Earth → Moon | 2.6 s | 0.91 | Workable |
| Earth → Mars (best) | 6.2 min | 0.063 | Useless — UI flags "switch to A3" |
| Earth → Mars (worst) | 44.6 min | 0.009 | Useless |
| Earth → Jupiter | 66–105 min | <0.007 | Useless |

One operator drives one robot up to 8 h/shift; daily output = `8 × η_teleop × rate_class`.
**Below η = 0.2 the UI refuses standing teleop orders** (one-off commands allowed; manual
override below 0.2 carries 5%/h robot-damaging-error chance — robot FAILED on site).

**A3 supervised autonomy:** 0.35× human rate, 24 h/day, latency-free, restricted to scripted
task classes unlocked by research (hauling → mating connectors → welding → inspection →
repair-swap). Exceptions: 0.5/robot-day, each 0.2 crew-h (or teleop) to clear; uncleared
exceptions idle the robot. Crossover: Mars-from-Earth teleop = 8×0.063 ≈ 0.5 robot-h/day vs
A3 = 24×0.35 = 8.4 robot-h/day.

**A4 kit closure χ:** complex internally satisfies fraction χ of (a) its own annual spares
demand (F-9) and (b) expansion parts bills; remainder (1−χ) arrives as imports
(Electronics-dominated) or repairs stall and the site degrades. UI: import dependency [t/yr] =
(1−χ) × (M_spares + expansion bill). Checks: χ=0.90, 120 t dusty-surface complex →
0.1 × 0.04 × 120 = 0.48 t/yr; χ=0.98, 250 t seed → 0.02 × (0.04 × 250) = 0.2 t/yr + doubling
Electronics imports.

**Robot catalog (§4.3):**

| ID | Robot | Tier | Mass | Power avg | Capability | Rate class |
|---|---|---|---|---|---|---|
| bot_arm_berth | Berthing arm (Canadarm2) | T1 | 1.8 t | 0.44 kW (2 pk) | handles to 116 t; 17.6 m reach; tip 0.37/0.02 m/s | BERTH jobs |
| bot_arm_dex | Dexterous unit (Dextre) | T1 | 1.6 t | 0.6 kW | ORU swap to 600 kg; rides arm/rail | 0.5× human |
| bot_worker | GP worker "Wrench" | T2 | 160 kg | 0.4 kW | tools/welding/mating; EVA-rated | 1.0× human teleop-local (×η); 0.35× A3 |
| bot_mule | Rover-manipulator "Mule" | T2 | 450 kg | 1.2 kW | hauls 1 t; regolith ops; charges workers | 60 s T_atom class (single canonical row, DECISIONS A9 — 05 owns, 10 references) |
| bot_trusselator | Truss-fab robot | T3 | 350 kg | 2 kW | extrudes truss from MetalStock spool | TRUSS-FAB 120 kg/day |

Robot upkeep: L_wear 2,000 h (×0.6 in dust), spares split 70% MachineParts / 30% Electronics.

---

## 3. SHIPYARDS, MASS DRIVERS, FREIGHTERS, SPARES

### 3.1 Orbital shipyards

**Why orbit:** launch imposes ~6 g axial, ~30–35 kPa max-Q, 5 m (–9 m) fairings; orbital
structures size for milli-g + own thrust (≤0.5 g NTR/SEP). Game rule: blueprints flagged
`orbital_only: true` get **0.65× structural mass multiplier on StructuralParts** (06 owns ship
mass model; this multiplier is the interface) and skip fairing checks — but the vehicle has no
aero/landing rating and **can never enter an atmosphere or land**.

**Dry dock** (yard_drydock, §1.6): 85 t, T2, open truss cage + rails/lighting/jigs, two
Canadarm2-class arm pairs, robot charging, 3 gang slots, cargo_equipped. Pressurized workshop
handles <2 m items in shirt sleeves.

**Assembly job classes & rates:**

| Job | Rate | Labor |
|---|---|---|
| BERTH | prefab module ≤25 t: 1 event/day per arm pair | 4 robot-h + 2 crew-h each |
| INTEGRATE | 0.5 day per interface (power/fluid/data) | 8 robot-h |
| FABWELD | 1.0 t/day per gang (gang = 2 worker robots + 1 dexterous unit, A2+); A3 gangs 0.7 t/day but 24/7-stable | gang time |
| TRUSS-FAB | 120 kg/day per trusselator robot (T3), from MetalStock spool | robot |
| OUTFIT | 0.8 t/day per gang installing MachineParts/Electronics | quality gate: crew-h ≥ 0.25 × robot-h on the job |
| COMMISSION | 0.5 day + 8 crew-h + 16 robot-h per 10 t new dry mass | skipping ⇒ ×3 failure hazard for first 90 days |

Sanity: ISS ≈ 0.1 t/day all-in; a T2 dock with 3 gangs sustains ~3 t/day fab + up to 50 t/day
berthing with both arm pairs on BERTH (plan ~25 t/day — one pair normally reserved for
INTEGRATE/FABWELD). Surface "shipyard" = same job classes run from 07's construction pad at the
same rates (07 owns the pad building; 05 owns erection labor).

### 3.2 Mass drivers (T3)

Physics: `L = v²/(2a)` (F-4); `E = v²/(2η)`, η = 0.6 end-to-end (F-5).
Lunar baseline: v = 2,500 m/s, a = 100 g → **L = 3.2 km**, **E = 1.45 kWh/kg** (5.2 MJ/kg),
zero propellant. Throughput baseline: 10 kg slugs every 20 s = **43.2 t/day**.
Pulse power (09 interface): 52 MJ/shot over 2.55 s → 20.4 MW shot-average; instantaneous muzzle
peak F·v/η ≈ **41 MW**; duty-cycle average **2.6 MW**; flywheel/capacitor bank sized 52 MJ/20 s.

| ID | Item | Tier | Mass | Power | Numbers |
|---|---|---|---|---|---|
| log_massdriver "Slinger" | mass driver | T3 | 850 t installed (3.2 km track) | 2.6 MW avg / 41 MW pk | 43.2 t/day @ 1.45 kWh/kg; parts bill 510 t Struct + 255 t Mach + 68 t Elec + 17 t Poly (60/30/8/2) |
| log_pelletizer | regolith pelletizer | T3 | 10 t | 100 kW | 50 t/day @ ~45 kWh/t into 10 kg slugs; feed = 04 M-8 tailings or canisterized safe bulk; unlocked with driver by 11 IN-12 |
| log_catcher | orbital catcher | T3 | 60 t | 40 kW | 2% miss (lost mass); station-keeping 0.5 t Xenon SEP = ~60 m/s/yr + 0.2 kg Xenon per caught slug-tonne; miss → 10% when Xenon empty or C < 0.5; cosmetic debris warning |

**Cargo rating:** mass-driver-safe = Regolith, IronSteel, Aluminum, Titanium, Copper,
MetalStock, Glass, BasaltFiber, Water (sealed canisters). Forbidden = Components, MachineParts,
Electronics, Wafers, FoodRations. Unlisted resources default FORBIDDEN until g-rated. (Rationale
is catcher intercept + packaging, not the 100 g launch.) Finished goods fly on landers.
Co-locating wafer fab with a mass driver = invalid at placement (vibration).

### 3.3 Freighters & landers (§4.4)

| ID | Vehicle | Tier | Dry t | Propellant | Isp s | Payload | Notes |
|---|---|---|---|---|---|---|---|
| frt_capsule "Carrack" | cargo capsule | T0 | 6.0 | 2 t storable | 300 | 3–6 t | Earth-launched to LEO node (12 buys launches); Δv 0.45 km/s @ 6 t; LEO-vicinity only; Act 1 import carrier |
| frt_pallet "Pallet" | chem tug | T1 | 4.5 | 24 t methalox | 380 (MV-2530) | to 14 t short legs | Δv by load: 3.1 km/s @14 t, 4.4 @6 t, 6.9 empty; needs depots for lunar runs |
| frt_drayage "Drayage" | SEP freighter | T2 | 8.0 (incl 300 kWe array) | 12 t Xenon | 2,800 (24× HALL-12) | 20 t | slow, superb G; Argon variant Isp 2,400 s, 0.48 N/string @12.5 kW (η≈0.45) |
| frt_longhaul "Longhaul" | NTR freighter | T2/T3 | 22 (incl 4 kW 20 K ZBO cryocooler + 6 kWe array) | 60 t Hydrogen | 900 (3× Pewee 111 kN) | 40 t | zero H2 boiloff in flight; orbital-only, never lands |
| lndr_pelican "Pelican" | lunar lander | T2 | 9 | 39 t methalox | 320 (ML-24) | 6 t down + 6 t up | refuels at LLO depot; 37.6 t/cycle; 100-sortie airframe |
| lndr_pelican_h "Pelican-H" | hydrolox variant | T2 | 9.0 | 28 t H2+O2 | 445 (HL-67) | 6+6 @ 22.0 t/cycle | PSR-water ISRU; passive bare boiloff 0.15%/day |
| lndr_pelican_m "Pelican-M" | Mars lander | T2 | 10 (incl TPS) | 52 t methalox | 320 (ML-24) | 6 t down + 2 t up | aero descent; surface refuel; 49.9 t/cycle |
| frt_torch | fusion-torch bulk | T4 [SPEC] | per 02 | per 02 | per 02 | 500 t class | endgame; obeys F-3 |

**Propellant formula (the ONLY fuel formula, F-3)** — per leg i, burned in sequence:

```
m_prop,i = (m_dry + m_cargo + m_prop,later_legs) × (e^(Δv_i / v_e) − 1)
v_e = Isp × g0 (g0 = 9.80665); Δv_i = map value × 1.05 margin
tanks additionally hold back 2% capacity as unusable residuals
Gear ratio G = cargo delivered / propellant consumed (UI figure of merit)
```

**Worked examples (validation targets — implementation must reproduce):**

| Trip | Freighter | v_e m/s | Δv used m/s (incl ×1.05) | Propellant | Cargo | G | Time |
|---|---|---|---|---|---|---|---|
| LEO→LLO one-way | Pallet (dry 4.5 t) | 3,727 (Isp 380) | 4,200 | 21.9 t | 6.0 t | 0.27 | 4 d |
| LEO→LLO one-way | Drayage SEP (dry 8 t) | 27,459 (Isp 2,800) | 8,400 (low-thrust) | 10.0 t Xenon | 20 t | 2.0 | ~227 d |
| LEO→LMO propulsive capture | Longhaul NTR (dry 22 t) | 8,826 (Isp 900) | 5,720 | 56.5 t H2 | 40 t | 0.71 | 259 d |

- Δv column already includes ×1.05; 2% residual excluded from propellant figures (planner adds
  it when sizing tank loads — flyable cargo runs ~2% under).
- Pallet check: (4.5+6.0) × (e^(4200/3726.5) − 1) = 21.9 t; arrives LLO with ≈1.6 t usable
  (24×0.98 − 21.9) ≈ 1,100 m/s empty — cannot return without LLO depot.
- Drayage check: thrust 24 × 0.59 N = 14.2 N; ṁ = F/v_e = 44.6 kg/day; 8,400 m/s at avg 33 t →
  ~227 d, 10.0–10.2 t Xenon. F = 2ηP/v_e, η 0.65, P 300 kWe.
- Longhaul closes only because of ZBO: at bare passive 0.15%/day the 259-d leg loses
  1 − 0.9985²⁵⁹ ≈ 32% of H2 (even depot-grade 0.01%/day leaks ≈2.6% ≈ 1.5 t).

**Lander lift-loop cycles (§3.7) — refuel node changes the math:**

Pelican (lunar, dry 9 t, tanks 39 t, Isp 320; refuels at LLO depot so descent carries ascent
prop). Δv with ×1.05: descent 1,995 m/s (M3 1,900), ascent 1,943 m/s (M4 1,850):

```
6 t down + 6 t up: ascent 12.86 t + descent 24.75 t = 37.6 t/cycle, G = 12/37.6 = 0.32
12 t down only:    ascent 7.72 t + descent 25.51 t = 33.2 t/cycle
6 t up only:       32.3 t/cycle → 5.4 t propellant per t lifted to LLO (the depot-stocking run)
Cycle time 1.5 d (load 0.5 + hops 0.2 + unload 0.5 + refuel 0.3) → ~4 t/day net down-mass/lander
```

Pelican-H (hydrolox, Isp 445, tanks 28 t): 22.0 t/cycle for 6/6. Lunar methalox needs carbon the
Moon mostly lacks — early lunar loops run hydrolox or import Methane.

Pelican-M (Mars, dry 10 t incl TPS, tanks 52 t, **surface refuel** so ascent carries next
descent's prop): descent powered-terminal 735 m/s (700 × 1.05); ascent 4,200 m/s (R4 4,000 ×
1.05). 6 t down + 2 t up = **49.9 t/cycle** (descent 4.22 t + ascent 45.63 t; tanks hold full
49.9 t at liftoff).

**Route planner (player-facing autopilot; runs at order time + each window):**

```
input: origin, destination, manifest, freighter class, earliest departure, weights w
1. enumerate node-graph paths (depth ≤ 4) with optional depot refuel stops
2. per path × candidate departure (01 window table): compute per-leg propellant by F-3
   BACKWARDS from the final leg; reject if any leg exceeds tank capacity (after refuels)
3. score = w_prop × propellant_cost (origin prices, 12) + w_time × trip_days
         + w_wait × days_until_departure
4. emit lowest-score schedule as events: load → depart → coast on-rails → capture → unload
   → refuel → return/hold (13 event queue)
```

Standing routes auto-replan each window. Search = label-correcting shortest path over
(node, fuel-state) with refuel-reset, ~10² states. Boiloff integration: per leg add
`m_boiloff,i = m_prop_on_board,i × rate × leg_days` before F-3; reject schedules whose tanks
cannot cover burn + boiloff + 2% residual. Planner refuses schedules projecting a stranding
(arrive with insufficient prop and no depot); stochastic events can still strand → alerts.

**Ops:** automated RDV/docking is T0. T0–T1 freighters need a comm link at node-ops time
(go/no-go only); T2+ fully independent. Cargo handling 20 t/day at `cargo_equipped` nodes
(yard_drydock, both depots, 07 modules with cranes), 5 t/day elsewhere. Propellant transfer
(02 §3.13, per docked coupler): PTC-200 cryo 18 t/h (settled, ullage ≥0.0005 m/s²), storables
72 t/h, gases 1.8 t/h; PTC-300L LAD = 60% of PTC-200 cryo (10.8 t/h). Node throughput = rate ×
installed coupler count. Missed window → replan to next synodic (Mars +780 d); UI shows staging
deadline on every route card.

**Depots (§3.9) & boiloff (F-6, byte-identical with 02 §3.12 which owns the rates):**

```
%/day: storables 0.0 ; O2/CH4 shielded 0.03 ; O2/CH4 + 90 K cryocooler 0.0 (ZBO,
4.5 kW per 200 t) ; H2 passive depot-grade (adv MLI + sunshield) 0.01 ; H2 passive bare
(standard MLI, no sunshield) 0.15 ; H2 ZBO 0.0 (12 kW per 200 t, 20 K ≥100 W/W + 90 K shield)
```

Vehicle tanks in flight obey passive F-6 rates unless the §3.3 row lists ZBO (Longhaul: 4 kW
cryocooler scaled from 12 kW/200 t for its 60 t store, 6 kWe array → 0%/day; Pelican-H bare).

| ID | Depot | Tier | Mass | Power | Numbers |
|---|---|---|---|---|---|
| log_depot_s | storable/methalox | T1 | 20 t dry | 6 kW | 200 t storage; F-6; 2× PTC-200; cargo_equipped |
| log_depot_h | LH2 ZBO | T2 | 28 t dry | 14 kW | 200 t LH2 zero boiloff; 12 kW 20 K cryocoolers; 2× PTC-200; per 02 DEP-600, unlock 11 PR-15; cargo_equipped |
| log_skyhook | momentum tether | T4 [SPEC] | 1,200 t | 200 kW | tip Δv 2.4 km/s/catch, max 20 t; ledger unit t·(km/s): up-boost debits mass×2.4, repaid 1:1 by down-catches or SEP/electrodynamic reboost; **momentum ledger owned by 05** (DECISIONS A9); 01 provides orbital state only |

### 3.4 Spares/maintenance economy

**Wear (F-7):** condition C ∈ [0,1] starts 1.0; `dC/dt = −(u × wear_per_t) / L_wear`
(u = utilization 0–1; L_wear catalog op-hours). EVA suits wear per sortie, not per hour.
PM at catalog interval restores C +0.25 (cap 1.0), costs PM row. Throughput penalty below
C = 0.5 per F-1 (f_condition = C/0.5).

**Failures (F-8):** Poisson, `P_fail/op-h = (1/MTBF) × (2 − C)`. Severity rolled at failure:
**minor 95%** = uniform(4,12) h labor + 0.1% module mass in parts; **major 5%** = uniform(24,40)
h + 1.0% — parts drawn per spares-split. No spares → down, UI shows ETA. Time warp: Poisson
thinning. Uncommissioned hardware: ×3 hazard for first 90 days. Repair-parts draws come from
*storage*, never inline from production buffers (prevents closed-chain self-consumption); UI
nags below 90-day reserve.

**Annual spares budget (F-9, UI planning figure):** `M_spares = k_env × M_module` per year;
**k_env = 0.02 orbital, 0.04 dusty surface (Moon/Mars), 0.03 clean surface/Titan**. (ISS anchor
~1%/yr in benign LEO; k_env is [PLAYTEST]-tagged — the primary difficulty knob, DECISIONS E.)
Dust: surface modules/robots wear ×2, MTBF ×0.6; T2 dust-lock building (07) restores ×1 for
indoors-serviced robots. Crew maintenance baseline: 2–4 crew-h/day per ~400 t habitat-class;
industrial modules use catalog labor rows + repairs.

**Maintenance data (§4.6, complete):**

| Module class | MTBF op-h | L_wear h | PM interval h | PM cost | Spares split Mach/Elec/Struct/Poly |
|---|---|---|---|---|---|
| Printer farms | 1,500 | 6,000 | 500 | 5 kg MachParts, 2 crew-h | 60/25/5/10 |
| LPBF cell | 1,200 | 5,000 | 400 | 8 kg MachParts, 3 crew-h | 55/35/0/10 |
| Machine shop | 1,800 | 8,000 | 500 | 15 kg MachParts, 4 crew-h | 70/20/5/5 |
| Foundry & mill | 2,500 | 12,000 | 750 | 40 kg MachParts + 10 kg Poly, 8 robot-h | 60/15/20/5 |
| Chemical plant | 3,500 | 15,000 | 1,000 | 25 kg MachParts + 15 kg Poly, 6 robot-h | 50/20/10/20 |
| Electronics assembly | 2,000 | 10,000 | 500 | 5 kg MachParts + 5 kg Elec, 3 crew-h | 30/60/0/10 |
| Consumables line | 2,500 | 12,000 | 750 | 10 kg MachParts + 5 kg Poly, 3 crew-h | 50/20/10/20 |
| Surface build machines | 1,800 (×0.6 dust) | 8,000 | 500 | 10 kg MachParts, 4 robot-h | 60/25/10/5 |
| Wafer fab | **400** | 20,000 | 168 | 2 kg Elec + 5 kg Poly, 12 crew-h | 15/65/0/20 |
| Dry dock & arms | 5,000 | 25,000 | 2,000 | 30 kg MachParts, 12 robot-h | 65/25/10/0 |
| Robots (all) | 2,000 (×0.6 dust) | 2,000 | 250 | 3 kg MachParts, 1 crew-h | 70/30/0/0 |
| Depots | 8,000 | 30,000 | 2,000 | 10 kg MachParts + 5 kg Poly | 50/30/5/15 |
| Mass driver & pelletizer | 900 | 10,000 | 168 | 50 kg MachParts + 10 kg Elec | 55/30/10/5 |
| Assembly hall | 2,000 | 10,000 | 500 | 10 kg MachParts, 4 crew-h | 60/20/10/10 |
| Workshop | 5,000 | 20,000 | 1,000 | 5 kg MachParts, 2 crew-h | 50/20/10/20 |
| Orbital catcher | 4,000 | 20,000 | 1,000 | 10 kg MachParts, 8 robot-h | 60/30/10/0 |
| Skyhook [SPEC] | 10,000 | 50,000 | 2,000 | 50 kg StructParts, 20 robot-h | 30/20/50/0 |

auto_complex / replicator_seed inherit bundled-module rows pro-rata by mass. Wafer fab 400 h
MTBF is deliberate (real fabs live with constant tool-downs).

**Failure-mode rules to implement (§8):** spares death spiral (detection: projected burn >
stock + manufacturing + imports; recovery: emergency import or cannibalization — strip 1% mass
as parts from donor, donor C −0.3); foundry freeze (f_power <0.8 >1 h RUNNING → major FAILED;
1 h grace window allows emergency dump losing the input-buffer batch, module OFF undamaged);
wafer fab excursion (any power/pressure/vibration event → 72 h requal + F-Y restart); wear
model is one system per DECISIONS A5 (02 per-ignition base × 11 maturity × 05 spares/MTBF —
orthogonal multipliers, no double counting); 06/10 vehicles use this same C/MTBF/split system.

**Blueprints (§3.11):**

```
E_design = 40 × (M_dry t)^0.6 engineering-h (100 t ship ≈ 630 eng-h)        (F-10)
first article ×1.5 labor, ×1.1 materials
learning: labor(N) = labor(1) × N^(−0.234) (85% Wright curve), floor 0.4×    (F-11)
commonality C_bp(a,b) = shared identical parts-mass / total parts mass       (F-12a)
fleet spares pool: S(N) = S_1 × N × [(1 − C_bp) + C_bp/√N]                   (F-12)
```

Subsystem tags (structure/propulsion/power/avionics/ECLSS…); revision resets F-11 only on
changed tags and fragments spares (5 one-offs need 5·S_1 vs √5 ≈ 2.24·S_1 identical). UI shows
C_bp and ΔS(N) at revision time.

### 3.5 Progression pacing (tier → Earth-import fraction of new construction)

T0 100% → T1 60% → T2 25% → T3 5% (Electronics margin only; "Silicon Independence" = 12's Act 4
exit) → T4 ~0%. Unlock order per §6: T0 poly printer/A0/Carrack; T1 shop+foundry+chem+elec-assy+
workshop/A1/Pallet/storable depot; T2 WAAM+hall+**drydock**/A2/Pelicans/Drayage/Longhaul/LH2 ZBO
depot/surface builders; T3 wafer fab/A3/auto complex/mass driver+pelletizer+catcher/trusselator;
T4 seed/skyhook/torch.

---

## 4. GAP vs CODE

| System | Spec section | Code today | Gap |
|---|---|---|---|
| Freighter route sim | §3.3 | `aphelion/sim/industry/routes.py` — LEO↔LLO legs from live patched-conics (incl. aerobrake return), F-3 propellant, deterministic standing-route cycles between two LedgerNetworks | **No UI** (no logistics map/route cards/planner dialog). No node graph or path enumeration (single hardcoded leg pair), no window/porkchop phasing, no ×1.05 margin or 2% residual, no boiloff term, no depot refuel stops, no cargo-handling rates, single propellant resource ("Oxygen"), no gear-ratio readout, no Carrack/Pallet/Drayage/Longhaul/Pelican classes as data |
| Ledger network | §1.4 | `aphelion/sim/ledger/network.py` — analytic piecewise rates, OFF/RUNNING/STARVED/BLOCKED/FAILED subset, f_power/f_labor/f_condition/Y hooks, MTBF pre-rolls, battery | Missing states STARTING(warmup)/DEGRADED/MAINTENANCE; no warmup times (foundry 6 h, fab 72 h requal); no f_power 0.3 trip-off or foundry 0.8/1 h freeze; no wear integration (F-7), PM, severity rolls, spares-split parts draws; condition is a static field nobody decays |
| Production chains | §1.5–1.6 | **Missing.** `aphelion/game/basebuild.py` catalog is 04-style ISRU (ice drill, electrolyzer, Sabatier, CO2 intake) + power/hab — zero 05 modules | All 15 recipes, all 17 fab modules, MetalStock/Components/Wafers resources, labor model (crew+robot simultaneity, substitution, A1 supervision charge), construction parts bill, heat_fraction/cascade, in-situ derate F-13, ×1.3 local-electronics penalty, recycling hook (04 RX-22) |
| Automation ladder | §2 | **Missing entirely** — no robots, no crew/robot-h ledger, no teleop, no η formulas | A0–A4, EVA cost rule, F-2 light-lag, A3 exceptions, kit closure χ, robot catalog |
| Shipyards | §3.1 | **Missing entirely** | Dry dock module, 6 job classes + rates, gangs, Gantt, 0.65× orbital multiplier, commissioning ×3 hazard, blueprint system F-10/11/12 |
| Mass drivers | §3.2 | **Missing entirely** | Slinger/pelletizer/catcher, F-4/F-5, pulse-power interface, cargo whitelist, miss model |
| Depots/boiloff | §3.3 | **Missing** (routes.py has no boiloff; basebuild tank_farm is unrelated) | F-6 rates, ZBO power, PTC coupler transfer rates, depot catalog rows |
| Spares economy | §3.4 | **Missing** (network.py has bare MTBF exponential pre-roll, no parts cost, basebuild uses ad-hoc mtbf_d values not §4.6) | F-7/8/9 full model, §4.6 table, k_env, dust multipliers, cannibalization, death-spiral detection, F-12 fleet pooling |
| Economy hooks | 12 interface | `aphelion/sim/economy.py` — cash/contracts/part-cost only | No import prices for Electronics/Wafers, no route propellant costing into planner score |
