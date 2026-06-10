# 05 — Manufacturing, Industry & Logistics

Status: design-complete draft for review · Owner: Industry/Logistics domain · Depends on: 01, 02, 03, 04 · Feeds: 06, 07, 08, 09, 10, 11, 12, 13

---

## 1. Overview

This document specifies everything between **refined resources** (the output boundary of
04-resources-isru.md) and **finished hardware** (the input boundary of 06-ships-stations.md,
07-bases-habitats.md, and 10-vehicles.md): production chains, factory modules, the automation
ladder, orbital shipyards, the logistics network (routes, freighters, landers, depots, mass
drivers), and the maintenance/spares economy.

Design pillars:

1. **Industry is a chain, not a magic box.** Refined metals become stock shapes, stock becomes
   components, components become `MachineParts` / `StructuralParts` / `Electronics`. Every stage
   has mass balance, energy cost, labor cost, and a real-world anchor.
2. **Electronics are the honest long pole.** A real semiconductor fab is a $10–20 B facility with
   thousands of process steps and hundreds of suppliers. We do not pretend a colony prints CPUs in
   Act 1. Local wafer production is gated to **T3** (Minimal-Fab-derived line, micron-class
   devices); until then `Electronics` are **imported from Earth** and are the single most
   import-dependent resource in the game. This dependency is a deliberate campaign-shaping
   constraint.
3. **Automation is earned.** Manual EVA → fixed robotic arms → teleoperated robots (light-lag is a
   real mechanic) → supervised-autonomous factories. Each rung has explicit productivity math.
4. **Orbital construction is the payoff.** Ships assembled in orbit escape launch loads (≈6 g
   axial, ~30–35 kPa max-Q) and fairing diameters (5 m class), enabling vehicles that could never
   be launched whole and **can never land**.
5. **Logistics is rocket-equation-honest.** Every cargo trip burns propellant computed from
   Tsiolkovsky against the Δv map published by 01-orbital-mechanics.md. Tedium is killed by the
   route planner and time warp, never by cheating the physics.
6. **Entropy is an antagonist.** Hardware wears, fails, and eats spares. A base that stops
   manufacturing spare parts is a base that is already dying — it just doesn't know it yet.

Scope boundary notes:
- Refining chemistry (ore → metal, gas separation, propellant ISRU) belongs to 04. The **chemical
  plant** module appears here only for its parts-feedstock recipes (Polymers, process organics);
  04 owns the upstream feedstock chemistry.
- Engine performance numbers (Isp, thrust, mass) belong to 02; this doc consumes them for
  freighter/lander sizing and shows the worked examples.
- Power generation and heat rejection hardware belong to 09; this doc states each factory's
  electrical demand and waste-heat load as interface quantities.

---

## 2. Real-World Grounding

Every module, rate, and rule below names its anchor. Summary table of the load-bearing facts:

| Anchor | Real numbers used | Where used |
|---|---|---|
| Made In Space **Additive Manufacturing Facility** (ISS, 2016–) | Polymer FDM in micro-g, build volume 14×10×10 cm, EXPRESS-rack locker scale | T0 polymer printing exists in space today |
| **ESA/Airbus Metal 3D Printer** (ISS, 2024) | First metal (stainless wire + laser) parts printed on orbit | T1 metal printing in micro-g is flight-demonstrated |
| **Laser powder-bed fusion** (EOS/SLM class) | ~20–100 cm³/h per laser ≈ 0.16–0.8 kg/h steel; multi-laser machines ~2–4 t | T1 precision metal printer cell |
| **WAAM / directed energy deposition** (industry lit., Relativity Stargate) | 1–10 kg/h wire deposition; CMT ~2–3 kg/h steel | T2 large-format printer, shipyard fab |
| **CNC vertical machining center** (Haas VF-2 class) | ~3.2 t machine, 22.4 kW spindle | T1 machine shop sizing |
| **Induction melting of steel** (industry practice) | ~500–650 kWh/t melt energy; rolling/forming adds ~100 kWh/t | Foundry & mill energy: 700 kWh/t stock |
| **Semiconductor fab energy** (EPRI fab survey; Williams et al. 2002; Taiwan fab studies) | 0.7–1.8 kWh per cm² of processed wafer; ~56% of fab power is facility (HVAC/UPW) | Wafers at 8,000 kWh/kg; fab is the long pole |
| **AIST Minimal Fab** (Japan, operational R&D line) | Half-inch (12.5 mm) wafers, maskless DLP lithography (~5 µm features), standardized tools 0.30×0.45×1.44 m, cleanroom-free local clean environments | T3 space wafer fab concept; micron-class devices only |
| **Canadarm2 / SSRMS** | 17.6 m, ~1,800 kg, handles 116 t; tip speed 0.37 m/s unloaded, ~0.02 m/s loaded; avg ~0.44 kW, peak ~2 kW | T1 berthing arm stats |
| **Dextre / SPDM** | 1,560 kg, ORU handling to ~600 kg | T1 dexterous unit |
| **Robonaut 2 / Valkyrie** | ~150 kg dexterous humanoid torso/body class | T2 worker robot mass class |
| **Lunokhod 1/2** (1970–73) | Earth-teleoperated lunar rovers; ~2.6 s light RTT plus slow-scan TV frame delays; 10.5 km and 39 km driven | Teleoperation latency model |
| **NASA Surface Telerobotics (2013), ESA METERON/ANALOG-1 (2019)** | ISS crew teleoperated K10 rover (Ames) and Interact rover (Netherlands) with sub-second orbital RTT | "Crew-in-orbit teleoperates surface robots" mechanic |
| **NASA CP-2255, “Advanced Automation for Space Missions” (1980/82)** | Self-replicating lunar factory study; ~90–96% mass closure studied | T3–T4 autonomous factory & closure metric |
| **ISS assembly** | ~420 t over >30 flights, 1998–2011 ≈ 0.1 t/day average incl. all overhead | Floor/ceiling sanity for shipyard rates |
| **Kosmos 186/188 (1967), Progress/Kurs, ATV, Dragon; DARPA Orbital Express (2007); Northrop MEV-1 (2020)** | Automated rendezvous & docking and on-orbit servicing are flown technology | Autonomous freighters available from T0–T1 |
| **Tethers Unlimited SpiderFab / “Trusselator”** (NIAC); **Archinaut/OSAM-2** (flight project, cancelled 2023 — anchor used honestly as matured ground demo) | On-orbit fabrication of truss from spooled feedstock | T3 truss-fab robots |
| **Falcon 9 / Starship launch environment** | ~6 g axial design load factor, max-Q ~30–35 kPa, 5.2 m fairing (Starship 9 m); JWST's 6.5 m mirror had to fold into a 5.4 m fairing | Why orbital assembly matters |
| **O'Neill mass driver studies (Princeton/MIT/NASA Ames 1977)** | Lunar escape 2.38 km/s; KE = 2.83 MJ/kg; prototype accelerators built; studies up to 1,000 g | T3 mass-driver physics |
| **ULA/NASA cryogenic depot studies** | LH2 boiloff: legacy stages ~2%/day; advanced passive ~0.1–0.5%/day; MLI leak ~0.5–1.5 W/m²; cryocooler specific power ~15–20 W/W at 90 K, ≥100 W/W at 20 K | Depot boiloff & ZBO rules |
| **NASA Gateway PPE + AEPS Hall thrusters** | 60 kW-class SEP flown-config; AEPS: 12.5 kW, Isp ≈2,600 s, ≈590 mN, η≈0.57–0.6; 300 kW-class SEP cargo tugs studied by NASA GRC | T2 SEP freighter |
| **NERVA / DRA 5.0 Pewee-class NTR** | Isp ~900 s, 111 kN (25 klbf) engines, ~3.3 t each | T2–T3 NTR freighter (per 02) |
| **ISS maintenance & ORU practice** | Orbital Replacement Unit architecture; of order 1% of station mass per year flies as maintenance hardware in benign LEO; station-wide preventive+corrective maintenance ≈2–4 crew-h/day | Spares economy coefficients |
| **EMU spacesuit ops** | ~6.5 h sorties, ~3.9 kg feedwater sublimated per sortie, ~12 crew-h prep/post per 2-person EVA, ~25 sorties between depot-level overhauls (extended ISS interval) | Manual-EVA labor cost |
| **Wright/aerospace learning curve** | 80–85% learning curve typical | Blueprint learning-curve formula |

Deliberate abstractions (stated honestly):
- Alloy zoology is collapsed: one `MetalStock` resource with recipe-defined input baskets, instead
  of tracking 30 alloys. Conservation of each canonical metal is preserved at recipe boundaries.
- `Wafers` stands in for the entire semiconductor BEOL/FEOL + packaging chain. Locally produced
  (T3) wafers are micron-class devices; the game does not distinguish chip grades — instead the
  *fab tier gate* and brutal energy cost carry the realism.
- 2D patched conics (per project doctrine): no plane-change costs anywhere in the logistics model;
  windows are purely phase-angle/synodic driven. 01 owns this caveat; the route planner inherits it.

---

## 3. Game Model

### 3.0 New intermediate resources (extensions to the canonical list)

Three intermediates are genuinely needed to express the production chain demanded by design
(metals → stock → components → parts). Exact spellings:

| Resource | What it is | Why it must exist |
|---|---|---|
| `MetalStock` | Engineered stock shapes: plate, bar, tube, extrusion, wire, powder | The logistics-shippable midpoint between refining and parts-making; lets foundries and machine shops live at different sites |
| `Components` | Machined/printed mechanical elements: gears, housings, valves, fittings, fasteners, springs | Distinguishes precision machining capacity from bulk assembly capacity |
| `Wafers` | Finished, diced, packaged semiconductor devices (mass-accounted as kg of fab output) | The long-pole gate; tiny mass, enormous energy/infrastructure cost |

Spares are **not** a new resource: maintenance consumes `MachineParts` (mechanical),
`Electronics` (avionics/control), `StructuralParts` (structure), `Polymers` (seals/filters/soft goods).

### 3.1 The production chain

```
 (from 04-resources-isru.md)                      (this document)                    (to 06/07/10)
 IronSteel ─┐
 Aluminum  ─┤  FOUNDRY            MACHINE SHOP /          ASSEMBLY HALL
 Titanium  ─┼─► & MILL ─► MetalStock ─► PRINTERS ─► Components ─► MachineParts ──► ships, bases,
 Copper    ─┘                        │                          ▲                  vehicles, spares
                                     └────────► WAAM/MILL ──► StructuralParts ──►
 Methane+Oxygen ─► CHEMICAL PLANT ─► Polymers ──────────────────┤
 Silicon (semi-grade) ─► WAFER FAB [T3] ─► Wafers ─► ELECTRONICS ASSEMBLY ─► Electronics
 Glass, BasaltFiber, RareEarths ────────────────────────────────┘
                       (until T3: Wafers and/or finished Electronics IMPORTED FROM EARTH)
```

### 3.2 Recipe format (the sim's data structure)

All production is defined by recipes normalized **per tonne of primary output**. JSON schema:

```json
{
  "id": "machine_parts_std",
  "module": "assembly_hall",            // module type that can run it
  "tier": "T2",                          // research gate (11-research-tech.md)
  "inputs_t":  {"Components": 0.62, "MetalStock": 0.43},
  "outputs_t": {"MachineParts": 1.00},
  "byproducts_t": {},                    // e.g. recovered Water, CO2
  "loss_t": 0.05,                        // mass discarded (slag, fume, unrecyclable scrap)
  "energy_kWh_per_t": 300,               // electrical, from 09-power-thermal.md grid
  "heat_fraction": 0.95,                 // fraction of energy_kWh rejected as waste heat (to 09)
  "labor": [                             // ALL entries required simultaneously (see 3.4)
    {"type": "crew",  "h_per_t": 4.0,  "substitutable": false},
    {"type": "robot", "h_per_t": 16.0, "crew_may_substitute_at": 1.0}
  ],
  "min_automation": "A1",                // lowest automation rung that can run it (see 3.4)
  "wear_per_t": 1.0,                     // multiplier on utilization in F-7 (see 3.10); default 1.0
  "env": "pressurized"                   // "pressurized" | "vacuum" | "any"
}
```

Mass conservation rule (validated at load time): `sum(inputs_t) == sum(outputs_t) +
sum(byproducts_t) + loss_t` within 0.5%.

**Module operating state machine:** `OFF → STARTING(warmup) → RUNNING ↔ {STARVED, OUTPUT_BLOCKED,
DEGRADED} → FAILED → MAINTENANCE → OFF`. Warmup times: foundry 6 h at full power before first
output; wafer fab 72 h re-qualification after any power interruption; others 0.5 h.

**Effective throughput** of a module running recipe r:

```
R_eff = R_nom × f_power × f_labor × f_condition × Y          [t/day]      (F-1)

f_power     = clamp(P_supplied / P_required, 0, 1); process trips OFF below 0.3
              (foundry: f_power < 0.8 continuously for >1 h while RUNNING → freeze → FAILED, §8.2)
P_required  = P_hotel + energy_kWh_per_t × R_nom / 24   [kW]
              (P_hotel from §4.1; the §4.1 Power column is generated from this formula)
f_labor     = min over the recipe's labor entries of clamp(supplied / required, 0, 1)
              (crew AND robot entries are both required; substitution rules in §3.4)
f_condition = 1.0 while condition C ≥ 0.5, else C/0.5        (see §3.10)
Y           = yield (1.0 for most recipes; wafer fab ramps, see §3.3)
```

Each module has input and output buffers sized at 3 × daily nominal flow (override per module).
Under time warp, production integrates analytically (`output += R_eff × Δt`) with events posted
for buffer-full / feedstock-empty / failure boundaries (interface: 13-architecture.md).

### 3.3 Stage-by-stage rules

**Stock (foundry & mill).** Inputs are metal baskets; alternate baskets let local ISRU drive the
mix (lunar highlands are Al-rich; NEA metal is Fe/Ni). Melt+form energy 700 kWh/t (induction melt
≈560 + forming ≈140 — industry practice). 3% loss to slag/dross.

**Components (machine shop, printer cells).** Machining scrap is internally re-melted; net stock
consumption 1.04 t per t. Energy 1,500 kWh/t (shop-level CNC energy intensity ≈1–3 kWh/kg incl.
machine overhead; Haas-class anchor). Printers trade throughput for zero tooling: LPBF cell makes
*precision* `Components` at small scale at 30,000 kWh/t (published LPBF specific energy incl.
ancillaries spans ~30–330 kWh/kg; the recipe sits at the optimistic edge and matches the cell's
25 kWe process draw at 20 kg/day); polymer farm makes low-load `Components` from `Polymers`.

**StructuralParts (WAAM cell / mill).** 1.05 t `MetalStock` + 0.02 t `Polymers` (primers,
sealants) → 1.00 t, 6,000 kWh/t (WAAM ≈5–7 kWh/kg deposited incl. system overhead at 2–3 kg/h
CMT rates; the recipe uses 6 kWh/kg, mid-anchor).

**MachineParts (assembly hall).** 0.62 t `Components` + 0.43 t `MetalStock` → 1.00 t + 0.05 t
loss, 300 kWh/t. Represents fitted assemblies: pumps, actuators, drive units, valves, bearings-in-housings.

**Polymers (chemical plant).** Methane-to-olefins-to-polyolefin route (real industrial chemistry:
oxidative/methanol route, 2 CH4 + O2 → C2H4 + 2 H2O, polymerized). Balanced game recipe per 1.00 t
`Polymers` (95% carbon efficiency):

```
1.20 t Methane + 1.20 t Oxygen → 1.00 t Polymers + 1.22 t Water + 0.16 t CO2 + 0.02 t Hydrogen
energy 1,500 kWh/t (electric; net process exotherm dumped to 09 as low-grade heat)
```
Mass and C/H/O atom balance close exactly (checked: 2.40 t in = 2.40 t out). Water and CO2 return
to the 04/08 loops.

**Wafers (wafer fab, T3).** The long pole, modeled with real fab energy intensity:
≈1.5 kWh per cm² of processed wafer (EPRI fab survey 1.15, Taiwan fabs 1.43, LCA values to 1.8) →
a 300 mm-equivalent wafer area of 707 cm² costs ~1,060 kWh and masses ~128 g, i.e. **≈8,000 kWh
per kg of `Wafers`** (game value, total fab energy incl. the ~56% facility overhead). Recipe per
1.00 t `Wafers` (run in kg in practice):

```
1.60 t Silicon (semiconductor-grade, 04) + 2.0 t Polymers (resists/organics) + 0.10 t Copper
+ 30 t Nitrogen + 60 t Water  (gross draws)
→ 1.00 t Wafers + byproducts 24 t Nitrogen (80% recovered to storage) + 54 t Water (90% UPW-loop
recovery to storage) + 14.7 t loss (vented/waste)
energy 8,000,000 kWh/t ; env pressurized, vibration-isolated
(mass closes per the §3.2 validator: 93.7 t in = 1.0 + 78.0 + 14.7 t out)
```
Yield ramp after commissioning or any major fault: `Y(d) = 0.9 − 0.7·e^(−d/60)`   **(F-Y)**
(d = days since start; reaches 90% asymptotically — real fabs ramp for months). Local wafers are micron-class
devices (Minimal-Fab anchor: ~5 µm maskless litho): sensors, power electronics,
microcontrollers — sufficient for the game's `Electronics`, and the abstraction is declared.

**Electronics (electronics assembly line).** Per 1.00 t:

```
0.35 Copper + 0.30 Polymers + 0.19 Aluminum + 0.11 Glass + 0.07 IronSteel
+ 0.02 RareEarths + 0.01 Wafers  (total 1.05 t) → 1.00 t Electronics + 0.05 t loss
energy 3,000 kWh/t (SMT placement is cheap; environmental test & burn-in dominate)
```
The line itself is T1 (SMT pick-and-place is mature tech) — **but until T3 the `Wafers` input must
be imported from Earth**, and before any line exists, finished `Electronics` are imported. This is
the intended Act 1–3 umbilical to Earth (economy: 12-gameplay-economy-ui.md).

### 3.4 Automation ladder

| Rung | Name | Tier | What it is | Anchor |
|---|---|---|---|---|
| A0 | Manual EVA / shirt-sleeve | T0 | Crew with hand tools; pressurized workshop or suited EVA | ISS maintenance, EMU ops |
| A1 | Fixed robotic arms | T1 | Berthing arms + dexterous units on rails; crew supervises from console | Canadarm2, Dextre |
| A2 | Teleoperated mobile robots | T2 | Worker robots & rover-manipulators driven by an operator; light-lag applies | Lunokhod, Robonaut 2, Surface Telerobotics, ANALOG-1 |
| A3 | Supervised autonomy | T3 | Robots execute scripted task classes 24/7; humans handle exceptions | CP-2255 study, Orbital Express, modern AMRs |
| A4 | Autonomous factory complex | T3→T4 | Whole sites run with kit-closure χ ≥ 0.9; only exceptions page a human | NASA CP-2255 self-replicating factory study |

**Labor units & staffing rules (one convention, no exceptions):** crew-hour (crew-h) from
08-life-support-crew.md; robot-hour (robot-h) from robots in the catalog (§4.3). A recipe's
`labor` list (§3.2) is satisfied as follows:

- **All labor entries are required simultaneously.** "a crew-h + b robot-h" in any table means
  both must be staffed; `f_labor = min over entries of clamp(supplied / required, 0, 1)` (F-1).
  The "+" convention is normative everywhere — no catalog row means "either/or".
- **Crew may substitute for robot-h** at the entry's `crew_may_substitute_at` rate (default
  1.0 h per h). **Robots never cover a crew entry** (`substitutable: false`) — crew entries
  represent judgment/QA work. Some recipes add a floor (wafer fab: min 10% of total hours crew).
- **A1 supervision charge:** every robot-h worked at rung A1 consumes an additional 0.1 crew-h of
  console supervision, charged to the same job. At A2, the operator's shift time *is* the cost
  (one operator : one robot; output scaled by η_teleop per F-2 — no extra charge); at A3+ the
  exception-handling rule below replaces supervision.

**EVA cost rule (A0):** one EVA sortie = 2 crew × 6.5 h outside; +12 crew-h prep/post; consumes
per suit-sortie: 0.65 kg Oxygen, 3.9 kg Water (sublimator, lost). Net efficiency: 13 productive
hours per 25 crew-h spent → **η_EVA = 0.52**. Suits take 1 wear unit per sortie; overhaul at 25
sorties (50 kg MachineParts + 10 kg Polymers + 40 crew-h). EVA work rate on assembly tasks:
1.0× (humans are still the best field hands in 2049).

**Teleoperation productivity (A2):** round-trip light time RTT (s) from 03-solar-system.md
geometry via the comms model (13-architecture.md):

```
η_teleop = 1 / (1 + RTT / T_atom),  T_atom = 25 s (dexterous), 60 s (driving/hauling)   (F-2)
```

| Operator → robot | RTT | η (dexterous) | Verdict |
|---|---|---|---|
| Same site / orbit→surface below | <0.1 s | ≈1.0 | Full telepresence (ANALOG-1 anchor) |
| Earth → Moon | 2.6 s | 0.91 | Workable (Lunokhod precedent) |
| Earth → Mars (best) | 6.2 min | 0.063 | Useless — UI flags "switch to A3" |
| Earth → Mars (worst) | 44.6 min | 0.009 | Useless |
| Earth → Jupiter | 66–105 min | <0.007 | Useless |

One operator (crew or Earth-hired controller via 12) drives one robot for up to an 8 h shift.
Robot daily output = `8 h × η_teleop × rate_class`. Below η = 0.2 the UI refuses standing teleop
orders (one-off commands still allowed).

**Supervised autonomy (A3):** per-robot productivity 0.35× human rate but 24 h/day, latency-free,
restricted to *scripted task classes* (each unlocked by research: hauling → mating connectors →
welding → inspection → repair-swap). Exception rate: 0.5 exceptions/robot-day, each consuming
0.2 crew-h (or teleop time) to clear; uncleaned exceptions idle the robot.

**Crossover math (why the ladder matters):** a worker robot at Mars driven from Earth produces
8 × 0.063 ≈ 0.5 robot-h/day; the same robot under A3 produces 24 × 0.35 = 8.4 robot-h/day; a crew
member on-site costs ~5 kg/day of life-support logistics (08). The game's economics push you up
the ladder exactly as real programs argue.

**Kit closure χ (the A3/A4 mechanic):** an autonomous complex with closure χ internally satisfies
the fraction χ of (a) its own annual spares demand (F-9) and (b) any expansion parts bill charged
to it; the remaining (1 − χ) must arrive as imports (Electronics-dominated), or repairs stall and
the complex degrades per §3.10. UI readout: import dependency [t/yr] = (1 − χ) × (M_spares +
expansion bill). Worked checks: at χ = 0.90 a 120 t complex on a dusty surface needs
(1 − 0.90) × 0.04 × 120 = 0.48 t/yr of imported spares; the χ = 0.98 replicator seed needs
0.02 × (0.04 × 250) = 0.2 t/yr plus its doubling-period Electronics imports (§4.1).

### 3.5 Orbital shipyards

**Why orbit:** launch imposes ~6 g axial quasi-static loads, ~30–35 kPa max-Q, acoustic loads, and
a 5 m (Starship-era: 9 m) fairing. Structures assembled in orbit are sized for milli-g handling
and thrust loads of their own (typically ≤0.5 g for NTR/SEP stages per 02), so trusses, tanks,
and radiators can be a factor ~2–4 lighter than launch-qualified equivalents and arbitrarily
large (JWST's fold-up agony is the cautionary anchor). Game rule: blueprints flagged
`orbital_only: true` get a **0.65× structural mass multiplier** on `StructuralParts` (06 owns the
ship mass model; this multiplier is the interface) and ignore fairing dimension checks — but the
resulting vehicle has no aero/landing rating and **can never enter an atmosphere or land**.

**Dry dock module** (catalog §4.2): open truss cage with rails, lighting, jigs, two Canadarm2-class
arms, and robot charging. Pressurized workshop module handles items <2 m in shirt sleeves.

**Assembly jobs and rates:**

```
BERTH       prefab module ≤25 t: 1 event/day per arm pair; 4 robot-h + 2 crew-h each
INTEGRATE   connect berthed module (power/fluid/data): 0.5 day per interface, 8 robot-h
FABWELD     erect structure from StructuralParts: 1.0 t/day per gang
            (gang = 2 worker robots + 1 dexterous unit, A2+; A3 gangs 0.7 t/day but 24/7-stable)
TRUSS-FAB   extrude truss from MetalStock spool (T3 trusselator robot): 120 kg/day per robot
OUTFIT      install MachineParts/Electronics into structure: 0.8 t/day per gang; quality
            gate: crew-h ≥ 0.25 × robot-h charged to the job
COMMISSION  checkout: 0.5 day + 8 crew-h + 16 robot-h per 10 t of new dry mass; skipping
            multiplies failure hazard ×3 for the first 90 days (infant mortality / bathtub curve)
```

Sanity anchor: ISS averaged ~0.1 t/day including all programmatic overhead with ~zero dedicated
robots; a T2 dock with 3 gangs sustains ~3 t/day fab + up to 50 t/day berthing of prefabs with
both arm pairs on BERTH (plan ~25 t/day in practice: one pair is normally reserved to support
INTEGRATE/FABWELD) — aggressive but defensible for a purpose-built yard, and the player pays for
it in robots, spares, and power.

**The loop the player experiences:** design blueprint → parts manufactured/imported → logistics
delivers to dock → assembly schedule (Gantt) runs under time warp → commissioning → a 600 t NTR
freighter exists that no launch vehicle could ever have lofted whole. That moment — *“this ship
has never touched a planet and never will”* — is the Act 3 emotional beat.

### 3.6 Logistics network model

The solar system is a **node graph**: nodes = surface sites, parking orbits, depots; edges =
transfer legs. 01-orbital-mechanics.md publishes, per edge: impulsive Δv(t) (porkchop lookup),
low-thrust Δv (spiral, no Oberth — substantially higher; e.g. LEO→lunar vicinity ≈8 km/s
low-thrust vs ≈4.0 km/s impulsive), transfer time, and window phasing (synodic periods: Earth–Mars
779.9 d, Earth–Venus 583.9 d, Earth–Jupiter 398.9 d; Moon: continuous).

**Propellant per trip (the only fuel formula in the game):** for each leg i, burned in sequence,

```
m_prop,i = (m_dry + m_cargo + m_prop,later_legs) × (e^(Δv_i / v_e) − 1)        (F-3)
v_e = Isp × g0,  g0 = 9.80665 m/s²;  Δv_i = map value × 1.05 margin; tank loads additionally
hold back 2% of capacity as unusable residuals
```

**Gear ratio** (UI-surfaced figure of merit): `G = cargo delivered / propellant consumed`.

Worked examples (engine values per 02; Δv per 01's example map):

| Trip | Freighter | v_e (m/s) | Δv used (m/s) | Propellant | Cargo | G | Time |
|---|---|---|---|---|---|---|---|
| LEO→LLO one-way | Pallet chem tug (dry 4.5 t) | 3,530 (Isp 360) | 4,200 | 24.0 t (full tanks) | 6.0 t | 0.25 | 4 d |
| LEO→LLO one-way | Drayage SEP (dry 8 t) | 25,497 (Isp 2,600) | 8,400 (low-thrust) | 10.9 t Xenon | 20 t | 1.83 | ~230 d |
| LEO→LMO (propulsive capture) | Longhaul NTR (dry 22 t) | 8,826 (Isp 900) | 5,720 | 56.5 t Hydrogen | 40 t | 0.71 | 259 d |

(Drayage check, shown so a programmer can validate the implementation: thrust 24×0.59 N = 14.2 N,
ṁ = F/v_e = 48 kg/day; 8,400 m/s at average 33 t → ~230 days, 10.9–12 t Xenon. Consistent with
F = 2ηP/v_e at η = 0.6, P = 300 kWe.)

Worked-example conventions (so the table validates against F-3 exactly): the Δv column already
includes the ×1.05 margin; the 2% residual hold-back is **excluded** from the propellant figures
shown — the planner adds it when sizing tank loads, so flyable cargo runs ~2% under these values.
Pallet check: m_prop = (4.5 + 6.0) × (e^(4200/3530) − 1) = 24.0 t — the tug arrives at LLO with
dry tanks and cannot return without the LLO depot (§3.9). Longhaul check: the row closes only
because of its ZBO cryocooler (§3.9, §4.4); at the passive F-6 rate (0.10%/day) the 259-day leg
would lose 1 − 0.999²⁵⁹ ≈ 23% of stored Hydrogen and the mission would not close.

**Route planner algorithm** (player-facing autopilot; runs at order time and each window):

```
input: origin, destination, cargo manifest, freighter class, earliest departure, weights w
1. enumerate paths through node graph (depth ≤ 4) with optional refuel stops at depots
2. for each path, for each candidate departure t in 01's window table:
     compute per-leg propellant by F-3 backwards from final leg
     reject if any leg exceeds tank capacity at that point (after scheduled refuels)
3. score = w_prop × propellant_cost(origin prices, 12) + w_time × trip_days
           + w_wait × days_until_departure
4. emit lowest-score schedule as events (load → depart → coast on-rails → capture → unload
   → refuel → return/hold) into the sim event queue (13-architecture.md)
```
Standing routes repeat every window with auto-replanning; search over (node, fuel-state) is a
label-correcting shortest path with refuel-reset, ~10² states — trivially fast in Python.

**Autonomy & comms:** automated rendezvous/docking is T0 (Kosmos 186/188 1967, Progress/Kurs, ATV,
Dragon, Orbital Express 2007). T0–T1 freighters require a comm link at node-ops time (light-lag
irrelevant: ops are autonomous, link is for go/no-go); T2+ freighters are fully independent.
Ops rates: cargo handling 20 t/day at any node whose catalog row carries `cargo_equipped: true`
(yard_drydock, both depot classes in §4.5, and any 07 base module with a cargo crane); 5 t/day at
all other nodes; propellant transfer 5 t/h settled (small ullage thrust or pump-fed, per ULA
settled-transfer studies).

### 3.7 Surface-to-orbit lift loops

Reusable single-stage landers shuttle between a surface base and orbit, refueled by ISRU
propellant (04). Per-sortie propellant from F-3 applied per leg. **The refuel node is stated per
lander and changes the cycle math:** lunar Pelicans top up at the LLO depot before each descent
(so descent carries ascent propellant; the depot is stocked by dedicated propellant-lift sorties
— the "6 t up only" tanker run below); the Mars Pelican-M refuels on the surface (Sabatier ISRU,
04), so ascent carries the next descent's propellant. Worked example, **Pelican** lunar lander
(dry 9 t, methalox Isp 360, tanks 31 t,
Δv: descent 2,000 m/s, ascent 1,900 m/s incl. margins on the 1.87 km/s ideal):

```
6 t down + 6 t up:  ascent prop 10.7 t, descent prop 19.6 t → 30.3 t/cycle, G = 12/30.3 = 0.40
12 t down only:     ascent prop  6.4 t, descent prop 20.9 t → 27.3 t/cycle
6 t up only:        25.7 t/cycle → 4.3 t propellant per t lifted to LLO
```
Cycle time 1.5 days (load 0.5 + hops 0.2 + unload 0.5 + refuel 0.3) → ~4 t/day net down-mass per
lander. Variant **Pelican-H** (hydrolox Isp 450, dry 9.0 t, PSR-water ISRU): 21.3 t/cycle for 6/6 — better
gear ratio, worse boiloff logistics. Honest chemistry note: lunar methalox needs carbon, which the
Moon mostly lacks outside cold-trap CO/CO2 (LCROSS detections, per 03/04) — early lunar loops run
hydrolox or import Methane.

Mars (**Pelican-M**, dry 10 t incl. heatshield, tanks 38 t, **surface refuel**): descent is mostly
aerodynamic (powered terminal ~700 m/s), ascent 4,100 m/s; because refueling happens on the
surface, the ascent also carries the next descent's propellant → 6 t down + 2 t up costs
37.6 t/cycle (F-3: descent 3.51 t + ascent 34.04 t; the tanks hold the full load at liftoff).
Mars ascent is brutal; the asymmetry (easy down, hard up) is real and shapes base economics.

### 3.8 Mass drivers (T3) — bulk cargo without propellant

Electromagnetic launch of payload slugs (O'Neill anchor). Physics rules:

```
track length L = v² / (2a)                 [m]                                    (F-4)
energy per kg  E = v² / (2η)               [J/kg], η = 0.6 end-to-end electrical  (F-5)
```
Lunar baseline (v = 2,500 m/s ≈ escape 2,380 + trim): a = 100 g → L = 3.2 km;
E = 5.2 MJ/kg = **1.45 kWh/kg**. Honest comparison with the lander loop: **zero propellant per kg
thrown**; 1.45 kWh/kg of electricity versus 4.3 t of methalox per delivered tonne by lander
(≈43 GJ of chemical energy per tonne delivered, plus the ISRU energy to make that propellant —
itself ~10 kWh/kg-class) — paid in 850 t of track mass and grid power. Baseline throughput:
10 kg slugs, 1 per 20 s → 43.2 t/day. Pulse power (interface to 09): energy per shot 52 MJ
delivered over t = v/a = 2.55 s → shot-average 20.4 MW; because power rises linearly with
velocity at constant acceleration, the instantaneous electrical peak at the muzzle is
F·v/η = 9.81 kN × 2,500 m/s / 0.6 ≈ **41 MW**; duty-cycle average 2.6 MW. Size the
flywheel/capacitor bank for 52 MJ per 20 s cycle. Payload forms: sintered Regolith slugs or
canisters of refined bulk; 2% miss rate at the orbital **catcher** (a crewless funnel-and-bag
craft + retrieval tug); misses are lost mass.

**Cargo rating (per-resource manifest validation):** mass-driver-safe — `Regolith`, `IronSteel`,
`Aluminum`, `Titanium`, `Copper`, `MetalStock`, `Glass`, `BasaltFiber`, and `Water` (in sealed
canisters); forbidden — `Components`, `MachineParts`, `Electronics`, `Wafers`, `FoodRations`;
resources not listed default to forbidden until assigned a g-rating. The honest rationale: it is
**not** the 100 g launch acceleration (hardened electronics routinely survive 10,000–15,500 g gun
launches — Excalibur-class guided-artillery fuzes are the anchor); it is the catcher intercept
(funnel-and-bag capture at tens of m/s closing speed) and unpadded slug packaging that preclude
delicate assemblies. Canisterized finished goods with padding/deceleration overhead are
deliberately out of v1 scope — finished goods fly on landers.

### 3.9 Propellant depots (T1 storable/methalox, T3 LH2 ZBO)

Depot = node module with storage, transfer gear, thermal control. Boiloff rule per commodity:

```
boiloff %/day: storable (Ammonia, etc.) 0.0 ; Oxygen/Methane shielded 0.03 ;
Oxygen/Methane + 90 K cryocooler 0.0 (ZBO, 4.5 kW per 200 t store: ~300 W leak × 15 W/W) ;
Hydrogen passive (advanced MLI + sunshield) 0.10 ; Hydrogen ZBO 0.0 (12 kW per 200 t: 20 K
cryocooler ≥100 W/W + 90 K shield)                                              (F-6)
```
Anchors: legacy cryo stages ~2%/day LH2; ULA/NASA advanced passive studies 0.1–0.5%/day; MLI leak
0.5–1.5 W/m².

**Vehicle tanks in flight obey the same F-6 rates** (passive rows) unless the vehicle's §4.4 row
lists ZBO hardware. Route-planner integration: for each leg i the planner adds
`m_boiloff,i = m_prop_on_board,i × rate × leg_days` to the leg's propellant requirement before
applying F-3, and rejects schedules whose tanks cannot cover burn + boiloff + the 2% residual
hold-back. The Longhaul NTR mounts a 4 kW 20 K-class ZBO cryocooler (F-6 scaling: 12 kW per
200 t → ~3.6 kW for its 60 t store), fed by a 6 kWe deployable array carried in its 22 t dry mass
→ 0%/day Hydrogen loss in flight. Pelican-H is passive (0.10%/day, loitering or in flight).

Depots make the chemical-tug economy work (the LEO→LLO Pallet example in §3.6 arrives at LLO
with dry tanks — its return leg is infeasible without a refuel stop at the LLO depot) and are
the natural first "infrastructure" purchase of Act 2.

### 3.10 Maintenance economy

**Wear & condition.** Each module/robot/vehicle has condition C ∈ [0,1], starting 1.0:

```
dC/dt = − (u × wear_per_t) / L_wear                                                     (F-7)
u = utilization (0–1); wear_per_t = the running recipe's multiplier (default 1.0, >1 marks
abusive recipes, §3.2); L_wear from catalog [operating h]
```
(Stated exception: EVA suits wear per *sortie*, not per operating hour — §3.4.)
Preventive maintenance (PM) at the catalog interval restores C by 0.25 (cap 1.0) and costs the PM
parts/labor row. Throughput penalty per F-1 below C = 0.5.

**Random failures.** Poisson with catalog MTBF, hazard scaled by condition:

```
P_fail per operating hour = (1 / MTBF) × (2 − C)                                        (F-8)
```
On failure: state FAILED; severity is rolled once, at failure time: **minor** (95% of failures)
or **major** (5%). Repair job = labor + parts by severity: minor = uniform(4, 12) h labor + 0.1%
of module mass in parts; major = uniform(24, 40) h labor + 1.0% — drawn from `MachineParts` /
`Electronics` / `StructuralParts` / `Polymers` per the module's spares-split row (§4.6). No
stocked spares → module stays down; the UI shows projected ETA from manufacturing or import.
Failures are sampled under time warp by Poisson thinning over the warp interval (13).

**Annual spares budget (planning figure surfaced in UI):**

```
M_spares = k_env × M_module   per year;  k_env = 0.02 (orbital), 0.04 (dusty surface:
Moon/Mars regolith abrasion — Apollo dust experience), 0.03 (clean surface/Titan)       (F-9)
```
Anchored to ISS practice (~1%/yr of station mass as maintenance hardware in benign LEO *with*
on-site humans and full Earth logistics; remote/dusty sites are charged 2–4×). Crew maintenance
labor baseline: ISS-anchored 2–4 crew-h/day per ~400 t of habitat-class hardware; industrial
modules instead use their catalog labor rows plus failure repairs.

### 3.11 Blueprints — design once, manufacture many

A **blueprint** = parts list (resources + parts), labor recipe, required modules/automation, mass
properties, version. Creating one costs engineering-hours (player character early; engineering
staff or purchased Earth designs later, prices per 12):

```
E_design = 40 × (M_dry in t)^0.6   [engineering-h]   (100 t ship ≈ 630 eng-h)          (F-10)
first article: ×1.5 labor and ×1.1 materials
learning curve: labor(N) = labor(1) × N^log2(0.85) = labor(1) × N^(−0.234), floor 0.4× (F-11)
```
(85% aerospace learning curve, Wright). A **subsystem** is a tagged group of parts-list lines
(tags: structure, propulsion, power, avionics, ECLSS, …); revising a blueprint resets F-11
learning only on the changed tags. Revision also reduces **spares commonality**:

```
C_bp(a, b) = (mass of identical parts-list entries shared by versions a and b)
             / (total parts mass)                                                      (F-12a)

Fleet spares pool for N hulls:
S(N) = S_1 × N × [(1 − C_bp) + C_bp / √N]                                              (F-12)
```

S_1 = one hull's annual spares stock per F-9; the common fraction pools with √N statistics, the
unique fraction does not pool at all. Worked check: 5 identical hulls (C_bp = 1) need
√5 ≈ 2.24 × S_1; 5 one-off hulls (C_bp = 0) need 5 × S_1 — a ~2.2× penalty for fleet
fragmentation (§8.10). The UI shows C_bp and ΔS(N) at design-revision time; standardization is a
real strategy lever.

### 3.12 Where the heat and power go

Interface rule (09-power-thermal.md): every factory's electrical demand is a grid load equal to
P_required (F-1: hotel + process — identically the §4.1 Power column); `heat_fraction` (default
0.95) of **total consumed electrical energy** (P_required × operating hours) must be rejected by
radiators at the site. A 700 kW wafer fab is also a ~665 kW radiator problem. Heat cascade rule:
if a foundry is co-sited with a 04 thermal-ISRU module and flagged `heat_cascade: true`, the
receiving module's electrical demand is reduced by `min(0.20 × foundry heat output, 0.15 ×
receiving module's demand)`, and the site radiator load drops by the same amount.

---

## 4. Content Catalog

### 4.1 Factory modules

Mass = installed dry mass. **Power (kWe) = P_hotel + recipe energy_kWh_per_t × nominal rate / 24**
— the Power column is *generated* from that formula (peak in parens where it matters), so §4.1
and §4.2 cannot disagree; F-1's f_power and §3.12's heat rejection both use this total.
Labor /day = recipe labor × nominal rate; "a + b" means both required (§3.4).
Env: P = pressurized, V = vacuum-rated, S = surface only.

**Construction parts bill (applies to every item in §4.1/§4.3/§4.5):** unless a row notes an
override, building any catalog item consumes its installed mass split **55% StructuralParts /
30% MachineParts / 8% Electronics / 7% Polymers** (e.g. fab_foundry_mill, 25 t = 13.75 t
StructuralParts + 7.5 t MachineParts + 2.0 t Electronics + 1.75 t Polymers). Overrides:
fab_wafer_fab 25/25/40/10; robots (§4.3) 25/45/25/5; depots 70/20/5/5; log_massdriver 60/30/8/2.
Erection labor is owned by this document: orbital items assemble at the dry dock under the §3.5
job classes and rates; surface items run the same job classes (FABWELD/OUTFIT/COMMISSION) from
07's construction pad at the same rates (07 owns the pad building itself).

| ID | Module | Tier | Env | Mass (t) | P_hotel (kWe) | Power (kWe) | Throughput | Labor /day | Anchor |
|---|---|---|---|---|---|---|---|---|---|
| fab_printer_poly | Polymer printer farm | T0 | P | 0.8 | 2.6 | 3 | 25 kg/day Components(poly) | 0.1 crew-h | ISS AMF (2016) |
| fab_printer_lpbf | Metal printer cell (LPBF) | T1 | P | 3.0 | 2 | 27 | 20 kg/day Components (precision) | 0.05 crew-h + 0.25 robot-h | EOS/SLM class; ESA ISS metal printer 2024 |
| fab_machine_shop | Machine shop | T1 | P | 8.0 | 3.75 | 35 | 0.5 t/day Components | 8 crew-h + 16 robot-h (A1+) | Haas VF-2 class CNC |
| fab_foundry_mill | Foundry & mill | T1 | S | 25.0 | 14 | 160 (300 pk) | 5 t/day MetalStock | 2 crew-h + 12 robot-h | Induction melt 560 kWh/t + rolling |
| fab_chem_plant | Chemical plant (parts feedstock) | T1 | S/V | 15.0 | 15 | 140 | 2 t/day Polymers | 1 crew-h + 6 robot-h | Methane-to-olefins industrial route (04 co-owns) |
| fab_elec_assy | Electronics assembly line | T1 | P | 10.0 | 7.5 | 20 | 100 kg/day Electronics | 4 crew-h + 8 robot-h | SMT pick-and-place lines |
| fab_workshop | Pressurized workshop module | T1 | P | 13.0 | 12 | 12 | hosts 2 small fab modules + repair bay (+25% repair speed) | — | ISS Destiny lab (14.5 t) |
| fab_waam | Large-format WAAM/DED cell | T2 | P/V | 12.0 | 2.5 | 40 | 150 kg/day StructuralParts or Components(large) | 0.15 crew-h + 1.8 robot-h (A2+) | WAAM 1–10 kg/h, CMT 2–3 kg/h |
| fab_assembly_hall | Parts assembly hall | T2 | P | 20.0 | 10 | 35 | 2 t/day MachineParts or StructuralParts finishing | 8 crew-h + 32 robot-h | Industrial assembly practice |
| yard_drydock | Orbital dry dock | T2 | V | 85.0 | 30 | 30 (180 pk, job-driven) | §3.5 job rates; 2 arm pairs, 3 gang slots; cargo_equipped | per job (§3.5) | ISS truss assembly, Canadarm2 |
| fab_wafer_fab | Wafer fab (Minimal-Fab line) | T3 | P | 45.0 | 33 | 700 (900 pk) | 2 kg/day Wafers | 4 crew-h + 40 robot-h (min 10% crew) | AIST Minimal Fab; fab energy surveys |
| fab_auto_complex | Autonomous factory complex | T3 | S | 120.0 | 398 (handling, robot charging, 04 pre-processing) | 600 | bundled at A3/A4: 5 t/day MetalStock + 0.5 t/day Components + 2 t/day MachineParts; kit closure χ = 0.90 (§3.4) | 1 crew-h (exceptions) | NASA CP-2255 (1980) |
| fab_replicator_seed | Self-expanding industry seed | T4 [SPECULATIVE] | S | 250.0 | — (coarse, [SPECULATIVE]) | 1,500 | χ = 0.98 (§3.4); consumes 10 t/day Regolith (integrated 04 chain) + imports 0.02 × installed mass (= 5 t) of Electronics per doubling period; output = a second 250 t seed (or equivalent module mass) every 2 yr | exceptions only | CP-2255 extrapolation |

Size-class rule: "small" = installed mass ≤ 3 t (fab_printer_poly and fab_printer_lpbf qualify);
anything larger needs its own pressurized volume from 07. The autonomous complex's 600 kWe =
398 P_hotel (materials handling, robot-fleet charging, 04 pre-processing) + 202 kWe of bundled
§4.2 recipe process power (foundry 146 + machine shop 31 + assembly hall 25).

### 4.2 Recipes (normalized per 1.00 t primary output; energy in kWh/t)

| ID | Module | Tier | Inputs (t) | Outputs (t) | Loss (t) | kWh/t | Labor h/t (crew / robot, both required §3.4) |
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
| polymers_mto | fab_chem_plant | T1 | Methane 1.20, Oxygen 1.20 | Polymers 1.00; byp: Water 1.22, CO2 0.16, Hydrogen 0.02 | 0.00 | 1,500 | 0.5 / 3 |
| wafers_min | fab_wafer_fab | T3 | Silicon 1.60, Polymers 2.0, Copper 0.10, Nitrogen 30, Water 60 (gross draws) | Wafers 1.00; byp: Nitrogen 24 (recovered to storage), Water 54 (UPW loop, recovered to storage) | 14.7 | 8,000,000 | 2,000 / 20,000 |
| electronics_std | fab_elec_assy | T1 | Copper 0.35, Polymers 0.30, Aluminum 0.19, Glass 0.11, IronSteel 0.07, RareEarths 0.02, Wafers 0.01 | Electronics 1.00 | 0.05 | 3,000 | 40 / 80 |

(Recipes for habitats' pressure vessels, tanks, radiators etc. are 06/07 blueprints *composed of*
these parts — they do not get separate factory recipes. Factory and logistics modules themselves
are built per the §4.1 construction parts bill.)

Schema fields not shown as columns take these defaults: `min_automation` = the rung noted in the
module's Labor column (A1+/A2+ …; A0 otherwise), `env` = the module's Env column, `wear_per_t` =
1.0, `heat_fraction` = 0.95. Per-recipe overrides would be listed here; none currently exist.

### 4.3 Robots & manipulators

| ID | Robot | Tier | Mass | Power (avg) | Capability | Rate class | Anchor |
|---|---|---|---|---|---|---|---|
| bot_arm_berth | Berthing arm | T1 | 1.8 t | 0.44 kW (2 pk) | Handles to 116 t docked; 17.6 m reach; tip 0.37 m/s unloaded / 0.02 loaded | BERTH jobs | Canadarm2 |
| bot_arm_dex | Dexterous unit | T1 | 1.6 t | 0.6 kW | ORU swap to 600 kg; rides arm or rail | 0.5× human | Dextre |
| bot_worker | GP worker robot "Wrench" | T2 | 160 kg | 0.4 kW | Tools, welding, mating; EVA-rated | 1.0× human teleop-local (×η_teleop); 0.35× at A3 | Robonaut 2 / Valkyrie class |
| bot_mule | Rover-manipulator "Mule" | T2 | 450 kg | 1.2 kW | Hauls 1 t; regolith ops; charges worker bots | 60 s T_atom class | Lunokhod heritage + modern AMR |
| bot_trusselator | Truss-fab robot | T3 | 350 kg | 2 kW | Extrudes structural truss from MetalStock spool, 120 kg/day | TRUSS-FAB | Tethers Unlimited SpiderFab (NIAC) |

Robot upkeep: L_wear 2,000 h (×0.6 in dust), spares split 70% MachineParts / 30% Electronics.

### 4.4 Freighters & landers (logistics roles; engines and full vehicle sheets in 02/06/10)

| ID | Vehicle | Tier | Dry (t) | Propellant | Isp (s) | Payload | Notes |
|---|---|---|---|---|---|---|---|
| frt_capsule | "Carrack" cargo capsule | T0 | 6.0 | 2 t storable biprop (per 02) | 300 | 3–6 t | Kosmos-186/188→ATV→Dragon lineage; Earth-launched to the LEO node via purchased launches (12); automated docking; Δv 0.45 km/s at 6 t cargo — LEO-vicinity legs only. Act 1's import carrier |
| frt_pallet | "Pallet" chemical tug | T1 | 4.5 | 24 t Methane+Oxygen | 360 | to 14 t (short legs) | Δv by load (F-3): 2.9 km/s at 14 t → 4.2 km/s at 6 t → 6.5 km/s empty; needs depots for lunar runs |
| frt_drayage | "Drayage" SEP freighter | T2 | 8.0 (incl. 300 kWe array) | 12 t Xenon | 2,600 | 20 t | 24× AEPS-class Hall (12.5 kW, 0.59 N); slow, superb gear ratio; Argon variant (T3): +15% Isp but −25% thrust at the same power (η ≈ 0.45, higher ionization cost — longer trips); Argon is cheap and ISRU-available |
| frt_longhaul | "Longhaul" NTR freighter | T2/T3 | 22 (incl. 4 kW 20 K ZBO cryocooler + 6 kWe array) | 60 t Hydrogen | 900 | 40 t | 3× Pewee-class 111 kN (per 02); zero Hydrogen boiloff in flight (§3.9); orbital-only, never lands |
| lndr_pelican | "Pelican" lunar lander | T2 | 9 | 31 t Methane+Oxygen | 360 | 6 t down + 6 t up | §3.7 cycle math (refuels at the LLO depot); 100 sortie airframe life |
| lndr_pelican_h | "Pelican-H" hydrolox variant | T2 | 9.0 | 28 t Hydrogen+Oxygen | 450 | 6 t + 6 t at 21.3 t/cycle | PSR-water ISRU; passive boiloff per F-6 (0.10 %/day, no ZBO) |
| lndr_pelican_m | "Pelican-M" Mars lander | T2 | 10 (incl. TPS) | 38 t Methane+Oxygen | 360 | 6 t down + 2 t up | Aero descent, 4.1 km/s ascent; surface refuel — ascent carries the next descent's propellant: 37.6 t/cycle (§3.7) |
| frt_torch | Fusion-torch bulk freighter | T4 [SPECULATIVE] | per 02 | per 02 | per 02 | 500 t class | Endgame only; obeys F-3 like everything else |

### 4.5 Logistics infrastructure

| ID | Item | Tier | Mass | Power | Function / numbers |
|---|---|---|---|---|---|
| log_depot_s | Depot, storable/methalox | T1 | 20 t dry | 6 kW | 200 t storage; boiloff per F-6; transfer 5 t/h; cargo_equipped |
| log_depot_h | Depot, LH2 ZBO | T3 | 28 t dry | 14 kW | 200 t LH2, zero boiloff; 12 kW cryocoolers (20 K, ≥100 W/W); cargo_equipped |
| log_massdriver | Mass driver "Slinger" | T3 | 850 t installed (track 3.2 km, 100 g) | 2.6 MW avg (41 MW pk at muzzle; 52 MJ/shot from flywheel/capacitor bank, §3.8) | 43.2 t/day rough cargo at 1.45 kWh/kg; cargo whitelist per §3.8; surface-built: 510 t StructuralParts + 255 t MachineParts + 68 t Electronics + 17 t Polymers (override split 60/30/8/2) |
| log_catcher | Orbital catcher | T3 | 60 t | 40 kW | Catches slugs, 2% loss; feeds orbital foundry or depot; station-keeping: 0.5 t Xenon SEP budget = ~60 m/s/yr + 0.2 kg Xenon per caught slug-tonne (momentum cancellation), refuelable per §3.6; miss rate 10% when Xenon is empty (§8.7) |
| log_skyhook | Momentum-exchange tether | T4 [SPECULATIVE] | 1,200 t | 200 kW | Boeing HASTOL-class concept; tip Δv 2.4 km/s per catch, max catch mass 20 t; momentum ledger unit = t·(km/s): each up-boost debits catch mass × 2.4, repaid 1:1 by down-mass catches (equal credit) or electrodynamic/SEP reboost (SEP propellant via F-3 against the 1,200 t tether; orbit bookkeeping via 01) |

### 4.6 Maintenance data (per module class)

| Module class | MTBF (op. h) | L_wear (h) | PM interval (h) | PM cost | Spares split (Mach/Elec/Struct/Poly) |
|---|---|---|---|---|---|
| Printer farms | 1,500 | 6,000 | 500 | 5 kg MachineParts, 2 crew-h | 60/25/5/10 |
| LPBF cell | 1,200 | 5,000 | 400 | 8 kg MachineParts, 3 crew-h | 55/35/0/10 |
| Machine shop | 1,800 | 8,000 | 500 | 15 kg MachineParts, 4 crew-h | 70/20/5/5 |
| Foundry & mill | 2,500 | 12,000 | 750 | 40 kg MachineParts + 10 kg Polymers, 8 robot-h | 60/15/20/5 |
| Chemical plant | 3,500 | 15,000 | 1,000 | 25 kg MachineParts + 15 kg Polymers, 6 robot-h | 50/20/10/20 |
| Electronics assembly | 2,000 | 10,000 | 500 | 5 kg MachineParts + 5 kg Electronics, 3 crew-h | 30/60/0/10 |
| Wafer fab | 400 (!) | 20,000 | 168 | 2 kg Electronics + 5 kg Polymers, 12 crew-h | 15/65/0/20 |
| Dry dock & arms | 5,000 | 25,000 | 2,000 | 30 kg MachineParts, 12 robot-h | 65/25/10/0 |
| Robots (all) | 2,000 (×0.6 dust) | 2,000 | 250 | 3 kg MachineParts, 1 crew-h | 70/30/0/0 |
| Depots | 8,000 | 30,000 | 2,000 | 10 kg MachineParts + 5 kg Polymers | 50/30/5/15 |
| Mass driver | 900 | 10,000 | 168 | 50 kg MachineParts + 10 kg Electronics | 55/30/10/5 |
| Assembly hall | 2,000 | 10,000 | 500 | 10 kg MachineParts, 4 crew-h | 60/20/10/10 |
| Workshop | 5,000 | 20,000 | 1,000 | 5 kg MachineParts, 2 crew-h | 50/20/10/20 |
| Orbital catcher | 4,000 | 20,000 | 1,000 | 10 kg MachineParts, 8 robot-h | 60/30/10/0 |
| Skyhook [SPECULATIVE] | 10,000 | 50,000 | 2,000 | 50 kg StructuralParts, 20 robot-h | 30/20/50/0 |

fab_auto_complex and fab_replicator_seed inherit the bundled modules' rows (foundry & mill,
machine shop, assembly hall) pro-rata by bundled-module mass, scaled to the complex's installed
mass — no separate rows needed.

The wafer fab's 400 h MTBF is deliberate realism: real fabs live with constant tool-down events
and large maintenance staffs — owning one is a commitment, not a checkbox.

---

## 5. Player Interaction & UI

- **Industry dashboard:** site-level Sankey diagram of mass flows (t/day) from refined inputs to
  parts; bottleneck stage highlighted red; click-through to module panels. Stockline graphs with
  30/90/365-day projections at current rates.
- **Module panel:** state machine status, condition C bar, current recipe, buffers, power/heat
  draw, labor allocation sliders (crew vs robots), PM countdown, MTBF-derived risk readout.
- **Recipe browser:** the full §4.2 table in-game, filterable by site capability; shows *effective*
  cost at this site (energy price, labor availability, import alternative from 12).
- **Logistics map:** node-graph overlay on the 2D system map (03); standing routes drawn as arcs
  with next-window countdowns; per-route gear ratio and propellant bill. Order dialog = §3.6
  planner with weight sliders (cheapest / fastest / soonest) and a porkchop heat-map (data from 01)
  for manual departure picking.
- **Shipyard view:** 2D schematic of the hull on the dock truss; Gantt of BERTH/FABWELD/OUTFIT/
  COMMISSION jobs; gang and arm assignment; parts shortfall list with "order via logistics"
  one-click. Skipping commissioning requires an explicit confirm (shows the ×3 hazard).
- **Teleoperation console:** pick operator → robot; UI shows RTT and η_teleop before committing;
  sub-0.2 efficiency is refused with the hint "relocate operator closer or research autonomy".
- **Maintenance queue:** all open repair jobs sorted by production impact; spares stock vs 12-month
  projected burn (F-9); "spares death spiral" warning when projected burn exceeds stock +
  manufacturing + manifest imports.
- **Blueprint studio:** parts-list editor with live mass/cost/learning-curve readout; version diff
  showing spares-commonality impact.
- **Time warp:** all of the above runs analytically under warp; warp auto-drops on failure events,
  window openings, and arrival events (13).

---

## 6. Progression Hooks

| Tier | Act | Industry & logistics unlocks |
|---|---|---|
| **T0** (2049 baseline) | Act 1 | Polymer printer farm; manual EVA (A0); automated docking cargo capsules ("Carrack" frt_capsule, §4.4 — Kosmos-186/188→Dragon lineage); everything else imported from Earth at launch prices (12). The player learns that `Electronics` and `MachineParts` come from Earth, full stop. |
| **T1** | Act 1→2 | Machine shop, foundry & mill, chemical plant, electronics assembly (imported `Wafers`), pressurized workshop; berthing arm + dexterous unit (A1); Pallet tug; storable/methalox depot. First closed loop: lunar `MetalStock` → `Components` → repairs without Earth. |
| **T2** | Act 2→3 | WAAM cell, assembly hall, **orbital dry dock**; worker robots + teleoperation (A2 — and the crew-in-orbit-drives-surface-robots trick); Pelican lander lift loops; Drayage SEP freighter; Longhaul NTR freighter; first never-lands ship built in lunar orbit. |
| **T3** | Act 3→4 | **Wafer fab** (the umbilical to Earth is finally cut — campaign milestone "Silicon Independence"); supervised autonomy (A3) and autonomous factory complexes (χ = 0.90); mass driver + catcher; trusselator robots; LH2 ZBO depots; belt logistics with multi-year SEP routes. |
| **T4** [SPECULATIVE] | Act 5→Endgame | Self-expanding industry seed (χ = 0.98); skyhook logistics; fusion-torch bulk freighters (02); He3 handling chains (04). Endgame megaprojects (interstellar precursor) are blueprints whose parts lists only a T4 industrial base can satisfy. |

Pacing rule of thumb the numbers enforce: each tier of industry cuts the Earth-import mass
fraction of new construction roughly from 100% (T0) → 60% (T1) → 25% (T2) → 5% (T3, electronics
only at the margin) → ~0% (T4).

---

## 7. Cross-System Interfaces

**Consumes:**
- 01-orbital-mechanics.md — Δv node-graph (impulsive + low-thrust variants), porkchop/window
  tables, transfer times; on-rails coast states for freighters.
- 02-propulsion.md — engine stats (Isp, thrust, mass, propellant types) for Pallet/Drayage/
  Longhaul/Pelican classes; boiloff-relevant propellant properties.
- 03-solar-system.md — body/site properties, distances → light-time for teleoperation, dust
  environment flags (k_env), resource availability context.
- 04-resources-isru.md — all refined inputs: IronSteel, Aluminum, Titanium, Copper, Silicon
  (semiconductor grade), Glass, BasaltFiber, RareEarths, Polymers feedstocks (Methane, Oxygen),
  propellants for the logistics network.
- 08-life-support-crew.md — crew-hours supply, EVA consumables accounting, crew transport demand
  on logistics routes.
- 09-power-thermal.md — electrical supply (kWe) and heat-rejection capacity per site; pulse-power
  storage for mass drivers.
- 11-research-tech.md — tier gates for every module/robot/route capability named here.
- 12-gameplay-economy-ui.md — Earth import prices (esp. Electronics/Wafers), launch costs,
  contractor engineering purchases, money layer of route planning.
- 13-architecture.md — event queue, time-warp analytic integration contract, comms-link model.

**Provides:**
- 06-ships-stations.md — MachineParts/StructuralParts/Electronics supply; dry-dock assembly jobs
  and rates; the 0.65× orbital-structure mass multiplier; commissioning rules.
- 07-bases-habitats.md — same parts supply for surface construction; factory modules as base
  buildings (mass/power/heat/labor rows); maintenance economy for all base hardware.
- 10-vehicles.md — parts + spares for rovers/landers; lander lift-loop scheduling.
- 08-life-support-crew.md — spares for ECLSS hardware (drawn via §4.6 splits); workshop repair-bay
  bonus.
- 09-power-thermal.md — factory demand/heat-load table (§4.1) as grid sizing input.
- 12-gameplay-economy-ui.md — gear ratios, route costs, and production costs as the physical basis
  of the price model.

---

## 8. Failure Modes & Edge Cases

1. **Spares death spiral** (the marquee failure): no `MachineParts` stock → repairs stall → the
   machine shop itself fails → nothing can make MachineParts. Detection: maintenance queue
   projects burn > supply. Recovery: emergency Earth import (slow, expensive) or cannibalization
   (player may strip C from one module to repair another: transfers 1% mass as parts, donor C −0.3).
2. **Foundry freeze (deterministic, with grace window):** if f_power < 0.8 continuously for >1 h
   while the foundry is RUNNING, the melt solidifies in the crucible (real induction-foundry
   hazard): module FAILED with a *major* repair (1% mass parts, 40 robot-h). UI warns at brownout
   onset; during the 1 h window the player may order an emergency dump — the input-buffer
   contents (the batch) are lost and the module returns to OFF undamaged.
3. **Wafer fab excursion:** any power interruption or pressure/vibration event → 72 h
   re-qualification + yield ramp restart (F-Y). Co-locating a fab with a mass driver (vibration)
   is flagged invalid at placement.
4. **Logistics deadlock:** freighter arrives at a node with insufficient propellant to leave and
   no depot stock. The planner refuses schedules that project this, but stochastic events
   (boiloff after cryocooler failure, missed window) can strand ships. Recovery: tanker mission or
   wait for ISRU production. Stranded-ship alerts escalate.
5. **Missed launch window:** cargo not staged by departure → planner replans to next synodic
   window (e.g. +780 d for Mars). The UI makes this loud *before* it happens (staging deadline on
   every route card).
6. **Teleop mishap:** operating below η = 0.2 via manual override carries a 5%/h chance of a
   robot-damaging error (Lunokhod-style crater encounter): robot FAILED on site, repair requires
   another robot or EVA.
7. **Mass-driver dispersion:** catcher misses (2% nominal) rise to 10% if the catcher's
   station-keeping Xenon (0.5 t budget, consumption per §4.5) is empty or its condition C < 0.5;
   persistent misses also create a (cosmetic in v1)
   debris-cloud warning at the catch orbit per 01.
8. **Infant mortality:** uncommissioned ships/modules run a ×3 failure hazard for 90 days (F-8
   multiplier). Stacks miserably with deep-space distances to the nearest spares stock.
9. **Dust abrasion:** Moon/Mars surface modules and robots wear ×2 / fail ×1.67 (k_env, MTBF×0.6)
   — Apollo dust experience. Mitigation: T2 dust-lock building (07) restores ×1 indoors-serviced
   robots.
10. **Blueprint drift:** revising a fielded design fragments the spares pool (commonality C_bp,
    F-12). A fleet of 5 one-off ships needs ~2.2× the spares stock of 5 identical hulls
    (F-12: 5·S_1 at C_bp = 0 vs √5·S_1 ≈ 2.24·S_1 at C_bp = 1); the UI shows this at
    design-revision time, not after.
11. **Buffer deadlock in closed chains:** A feeds B feeds A (e.g. machine shop needs MachineParts
    spares it produces). Rule: repair-parts draws come from *storage*, never inline from buffers,
    and the UI nags below a 90-day reserve, preventing the cycle from silently consuming itself.
12. **Time-warp consistency:** all production, wear, failures, and route events must integrate
    identically at 1× and 10⁶× warp (analytic integration + Poisson thinning; no per-frame
    accumulation). This is a hard correctness requirement on 13's implementation, called out here
    because industry is the system most likely to expose drift.

---

## 9. Open Questions

1. **Granularity of `Components`:** one generic resource (current design) vs. splitting precision
   vs. bulk components into two SKUs. Current recipes encode precision via *which module* made
   them; is that legible enough to players?
2. **Should locally-made (T3, micron-class) `Electronics` carry a mass penalty** (e.g. ×1.3 per
   function) versus Earth-imported high-density electronics, or is the single-resource abstraction
   cleaner? Realism argues for the penalty; UI simplicity argues against. Needs a playtest call
   with 12.
3. **Mass-driver debris consequences:** v1 treats catcher misses as pure loss + cosmetic warning.
   Do we want a real debris-risk mechanic at busy orbits (coordination with 01/06)?
4. **Skyhook momentum ledger ownership:** the bookkeeping (boost debt repaid by down-mass) sits
   here, but the orbital state belongs to 01. Confirm 01 is willing to model tether tip
   rendezvous as a standard "node" with a Δv discount, or whether skyhooks become 01-owned.
5. **Labor market for Earth-based teleoperators:** hiring ground controllers (cash → robot-h at
   Earth-RTT) is implied by 12's economy. Confirm 12 wants this lever; it strongly shapes early
   lunar automation.
6. **Recycling depth:** scrap/loss fractions are currently destroyed. A T2 "recycler" module
   (shredder + induction re-melt) reclaiming 80% of `loss_t` and decommissioned hardware would
   tighten closure — worth a module slot? (Leaning yes; needs 04 sign-off on resource flows.)
7. **Wear of *ships* vs *modules*:** this doc defines the maintenance model generically; 06/10
   must confirm vehicles use the same C / MTBF / spares-split system rather than inventing a
   parallel one (strong recommendation: one system).
8. **Pelican-H vs Pelican-M commonality:** are landers per-body variants of one blueprint family
   (sharing learning curve and spares at C_bp ≈ 0.7) or distinct designs? Affects Act 2→3 economy
   noticeably.
9. **Tuning the spares coefficients:** k_env values (F-9) are anchored but coarse. Flagging for
   economy balancing once 12's price model exists — these coefficients are the single biggest
   knob on long-range mission difficulty.
