# 07 — Surface Bases & Exotic Habitats

Status: DRAFT v1.0 (2026-06-09) — domain: surface/aerostat base construction, habitat structures, pressure vessels, environmental simulation (thermal cycles, dust, radiation shielding), per-body engineering packages from the Moon to Enceladus.

---

## 1. Overview

This document specifies everything between "a body and its sites exist" (`03-solar-system.md`) and "crew live and work somewhere" (`08-life-support-crew.md`). It owns:

- The **surface grid** (2D top-down placement), the four connection networks (power, thermal, fluid, data), and the three-stage construction pipeline (Deploy → Outfit → Commission).
- The **habitat module catalog**: rigid (ISS-Destiny class), inflatable (TransHab/BEAM heritage), ISRU-built (sintered regolith vaults, basalt-fiber-wound shells, ice structures), and buried/bermed variants — each with mass, volume, berths, leak rate, and envelope thermal properties.
- **Pressure-vessel and structure rules** — simplified but physically honest. Internal-pressure vessels (everything from the Moon to Mars) fail in tension; external-pressure vessels (Venus surface at 9.2 MPa, deep Titan/Europa ocean access) fail by buckling, which is a different formula and a different material logic. Titan surface habitats are the special iso-baric case where the hull carries (almost) no pressure load at all.
- **Per-environment engineering packages** with hazard→response tables and real anchors: Moon (vacuum, 354-hour night, thermal cycling, PSR ice bases), Mars (dust storms, perchlorates, the classic ISRU base), Venus aerostats at 50–56 km (NASA HAVOC / Landis), Titan (cold is the enemy, ice as structure, shoreline bases, the ocean bore megaproject), Europa (5.4 Sv/day — burrow or die), Enceladus (plume stations), asteroid interiors (GCR-floor dose and total SPE immunity for zero imported shielding mass), and Mercury (terminator crawlers, polar bonanza bases).
- **Environmental simulation per base**: external temperature cycles, dust events and contamination loads, and the radiation-dose ledger with explicit areal-density shielding math (the canonical `f_GCR`/`f_SPE` response law owned by `08-life-support-crew.md`) plus per-material thickness conversions for regolith, water, and polyethylene.

Design intent: every environment must feel *different to engineer for*, because in reality it is. The Moon is a thermal-swing and dust problem; Mars is an energy-reliability and toxicology problem; Venus at altitude is shockingly benign except for acid and the absence of ground; Titan inverts everything — pressure is free, heat is precious; Europa is a radiation siege; asteroids reward digging. The player who copies their Mars base onto Titan should fail in instructive ways.

Simulation philosophy (shared with `04-resources-isru.md` and `13-architecture.md`): all environmental processes are piecewise-analytic so they integrate cleanly under time warp. Temperatures follow closed-form day/night curves; dose and dust accumulate linearly between discrete events (storms, SPEs); the scheduler pre-computes the next threshold crossing (shelter required, heater capacity exceeded, dust limit hit) and interrupts warp.

---

## 2. Real-World Grounding

Every environment package in §4.3 names its anchors inline; the headline sources are collected here.

**Moon.**
- *LRO Diviner*: equatorial surface temperatures ~390 K subsolar to ~95 K pre-dawn; PSR floors 25–40 K (Hermite crater ≈ 25 K, among the coldest measured surfaces in the solar system).
- *Apollo 15/17 Heat Flow Experiments*: regolith below ~0.5 m sits at a nearly constant ≈ 250–255 K; top centimeters are an extreme insulator (k ≈ 0.0015 W/m·K fluff over ≈ 0.01 W/m·K at depth) — burial is free thermal stabilization.
- *Chang'E-4 LND* (Zhang et al., Sci. Adv. 2020): measured lunar-surface dose equivalent **1,369 µSv/day** (≈ 1.37 mSv/day) — our canonical unshielded lunar rate.
- *Apollo* dust experience (abraded seals, "lunar hay fever" — Schmitt, Apollo 17); NASA **Electrodynamic Dust Shield** flight demo (Blue Ghost Mission 1, 2025) — our dust-mitigation anchor.
- Apollo passive seismometers: ~28 **shallow moonquakes** in 8 years, some ≈ magnitude 5 — flexible inter-module couplings are not optional flavor.
- Shackleton/de Gerlache rim sites: ~80–90% annual illumination with 10 m masts; longest continuous darkness still 2–5 days (Mazarico et al. 2011 illumination modeling).
- NASA TP-3079 (Simonsen & Nealy, 1991): regolith shielding transport results for GCR/SPE — cross-check anchor for the [SIMPLIFIED] exponential shielding-response fits (the canonical `f_GCR`/`f_SPE` law itself is owned by `08-life-support-crew.md`; reproduced in B-6b).

**Mars.**
- *MSL RAD* (Hassler et al., Science 2014): surface dose equivalent ≈ **0.64–0.71 mSv/day** — game canon **0.67 mSv/day** per `03-solar-system.md` S-8a; cruise (free space, 1–1.5 AU) ≈ **1.84 mSv/day** (Zeitlin et al. 2013).
- *Phoenix WCL*: **0.4–0.6 wt% perchlorate** (ClO4⁻) in Martian soil — thyroid toxin (iodide-uptake inhibitor); also decomposes at ~350–500 °C releasing O2.
- Global dust storms: 2018 event killed *Opportunity* (optical depth τ peaked ≈ 10.8); MER panels degraded ~0.2%/sol from deposition between cleaning events. Global storms recur irregularly every ~3–4 Mars years; regional storms every dust season (Ls 180–330).
- Atmospheric column at datum: 610 Pa / 3.71 m/s² = **16.4 g/cm²** CO2 overhead (≈ 33 g/cm² in Hellas at 1,240 Pa) — real but modest radiation shielding.
- NASA *Mars Ice Home* (Langley, 2016; NIA Big Idea ConOps, 2017): inflatable torus with **~400–650 m³ (≈ 370–600 t) of locally harvested water ice** as translucent shielding, filled at ~1 m³/day → a **400+ day fill**; the ConOps explicitly designs for partial-shielding occupancy while the fill proceeds. NASA Mars DRA 5.0 surface habitat for the rigid baseline.

**Venus.**
- Atmosphere profile (Venus Express / Magellan radio occultation; VIRA, Seiff et al. 1985): ≈ 1 atm at **~50 km** — but ~350 K there, too hot for shirtsleeves; the **293–310 K shirtsleeve band sits at ~55–56.5 km**; ~53 kPa / ~302 K at 55 km. Cloud droplets are 75–98% H2SO4.
- NASA **HAVOC** (High Altitude Venus Operational Concept, Langley 2015): 129 m crewed airship at ~50 km; established ops altitude band, slow-failure philosophy, solar viability including cloud-albedo bonus on down-facing arrays.
- G. Landis, "Colonization of Venus" (2003): **breathable air (M ≈ 29) is a lifting gas in CO2 (M ≈ 43.45)** — Landis gives **~0.5 kg of lift per m³ at the ~1 bar / 50 km level, about half the lift of helium-on-Earth** (helium-on-Earth ≈ 1 kg/m³). At our thinner canonical 54 km station the absolute lift falls to ~0.33 kg/m³ (B-8a; the 1/3 there is the lift *fraction* of ambient density, 1 − 29/43.45 = 0.333). The lifting gas is the living volume.
- *VEGA-1/2* balloons (1985): PTFE(Teflon)-based envelopes survived ~46 h at ~54 km in the acid clouds — our envelope material anchor (FEP/PTFE laminate).
- Surface: 9.2 MPa, 737 K (Venera/VEGA landers; Venera 13 survived 127 min). NASA GRC **GEER** chamber: SiC electronics operated for weeks at full Venus surface conditions; **LLISSE** long-lived lander concept targets 60+ days. Duplex-Stirling cooled lander studies (GRC) for crewed-adjacent long-duration pressure vessels.
- Super-rotation winds ~60–70 m/s at 50–55 km → an aerostat circumnavigates in ~6 Earth days regardless of the 117-day solar day at the surface.

**Titan.**
- *Cassini-Huygens*: surface **146.7 kPa, 93.7 K**, ~94–95% N2 / ~5% CH4 near-surface; weak surface winds (0.3–1 m/s); Ligeia Mare ~160–170 m deep, methane-dominated. Crust is water ice (bedrock IS the oxygen feedstock); ice shell to the internal water-ammonia ocean estimated **50–100 km**.
- *Dragonfly* (NASA New Frontiers, launch 2028) — flight operations and surface science anchor; *Titan Submarine* (NASA NIAC, Oleson et al.) — sea operations anchor.
- Cryogenic ice mechanics: polycrystalline water ice strengthens dramatically with cold — tens of MPa compressive at ~100 K, and creep is negligible at 94 K. Ice is a legitimate structural material on Titan in a way it never is on warm Mars.
- Surface sunlight ~0.1% of Earth-surface flux (noon ≈ 1.5 W/m², 03 S-6a) — solar power is useless; fission mandatory (`09-power-thermal.md`).

**Europa / Enceladus / Jupiter–Saturn context.**
- Europa surface ionizing dose ≈ **5.4 Sv/day** (540 rem/day, JPL; trailing-hemisphere apex worst). Paranicas et al.: MeV electrons deposit in the top tens of cm; **bremsstrahlung photons dominate dose below ~1 m of ice** — burrowing works but needs meters, not centimeters. *Europa Clipper* shields its electronics in a ~9 mm-wall metal vault — our robot-hardening anchor. Ice shell ~15–25 km.
- Classic JPL hemisphere-scale dose ladder for context: Io ~36, Europa ~5.4, Ganymede ~0.08, **Callisto ~0.0001 Sv/day** — Callisto is the human-staging pick (NASA RASC **HOPE** study, 2003).
- *Cassini* at Enceladus: south-polar tiger-stripe plume, ~150–300 kg/s water vapor + 5–50 kg/s ice grains, jets laced with CO2, CH4, NH3, H2, salts, organics; grain fallback blankets the south polar terrain (Southworth et al. 2019 deposition mapping, ~mm/yr near stripes). South-polar ice shell locally thin (~2–5 km) — the thinnest known ocean roof.
- Mercury: *MESSENGER* radar-bright polar deposits = water ice, likely purer than lunar PSR ice under a thin organic lag; total estimated 10^14–10^15 kg (10^11–10^12 t; 03 §4.4.1 canon). Solar day 176 d (= 4,224 h; 03 §4.1); equatorial terminator ground speed ≈ 3.6 km/h — a slow crawler outruns the dawn. Solar flux 6,270–14,450 W/m² (aphelion 0.467 AU – perihelion 0.307 AU; 03 S-4a).

**Habitat structures.**
- ISS *Destiny* lab: 14.5 t, ~106 m³ pressurized — rigid-module anchor. ISS nominal whole-station leakage ≈ 0.27 kg air/day on ~1,100 kg inventory (≈ 0.025%/day) — leak-rate anchor.
- NASA **TransHab**: 13.2 t, 339.8 m³, crew 6 — inflatable anchor; *BEAM* (1.4 t, 16 m³, on ISS since 2016) — flight-proven softgoods. Bigelow B330 for the scaled class.
- *Quest* airlock: ~34 m³ with depress pump recovering most cycle air — pumped-airlock anchor. Suitports: NASA Z-suit / SEV concept work.
- NASA-STD-3001 / NASA habitable-volume studies: ≈ **25 m³ net habitable volume per crew** minimum for long-duration missions.
- Sintered-regolith construction: microwave sintering studies (Taylor & Meek), ESA/ICON regolith-printing work (Project Olympus class). Basalt fiber: terrestrial industrial product, feed via `04-resources-isru.md` RX-17.

Honesty flags as in 04: **[SIMPLIFIED]** = real physics, deliberately coarse; **[LUMPED]** = several phenomena folded into one rule; **[SPECULATIVE]** = T4 only.

---

## 3. Game Model

Symbols: `P` pressure [kPa], `ΔP` differential pressure [kPa], `V` pressurized volume [m³], `A` hull area [m²], `T` temperature [K], `x` shield areal density [g/cm²], `ρ` density [kg/m³], `σ_a` design allowable stress [MPa], `E` Young's modulus [GPa]. 1 g/cm² = 10 kg/m².

### 3.1 Surface grid & sites (B-1)

- Every landable body region (site list owned by `03-solar-system.md`) exposes **sites**: contiguous build regions of up to **64 × 64 cells, cell = 10 m × 10 m** (640 × 640 m). Bases larger than one site are multiple linked sites (power/thermal conduit runs between them are priced by `09-power-thermal.md`; fluid lines by the line-cost rule below; heat-trace power per §3.5).
- Each placed structure occupies a rectangular footprint of cells, has a facing, and connects to networks along cell edges. Terrain per cell: flat / rough (+50% deploy time) / crater-wall (berm-ready: berm cost ×0.5) / PSR-shadow / sea-shore (Titan) / fissure-adjacent (Enceladus).
- Four **network layers** on cell edges:
  1. **Power bus** — model owned by `09-power-thermal.md`; this doc only places conduits.
  2. **Thermal loop** (pumped fluid) — model owned by `09-power-thermal.md`; habitat envelope loads (B-5) are nodes on it.
  3. **Fluid lines** — carry one canonical resource each (`04-resources-isru.md` taxonomy); throughput limit 20 t/day per standard line; freeze-protection heat-trace power per §3.5 table. **Line cost rule:** a standard fluid line = 0.3 t StructuralParts + 0.05 t MachineParts per km (= 0.0035 t per 10 m cell edge), heat-trace hardware included; the same per-km pricing applies to inter-site runs.
  4. **Data** — wireless site-wide by default; inter-site > 10 km needs relay masts (0.1 t, 0.05 kWe each); enables robotic construction and remote ops (`13-architecture.md` automation).
- **Tailings slots** (shared canon with `04-resources-isru.md` M-8): each site has **16 pile slots**, 1 slot per 10,000 t of tailings/Regolith stockpile. Full slots stall extractors.

### 3.2 Construction pipeline (B-2)

Every structure passes through three stages:

```
DEPLOY     robot-crane or crew places/inflates the unit.
           Time: rigid 6 h, inflatable 12 h. ISRU-built = local mass ÷ build-machine
           rate: sinter printer 2 t/day (HAB-07: 120 t → 60 days), filament winder
           0.5 t/day of wound fiber (HAB-18: 6 t BasaltFiber → 12 days; glass
           furnace runs in parallel), ice casting 5 m³/day (Titan Ice Vault: 80 t
           ≈ 87 m³ → 18 days), Ice Home water fill 1 m³/day (HAB-09: ~400 days,
           staged occupancy per catalog note), gallery excavation at the excavator-
           chain throughput owned by `05-industry-logistics.md` (energy per
           `04-resources-isru.md` e_dig). Build machines themselves are 05 content.
           Rough terrain ×1.5. Requires a rover-crane (`10-vehicles.md`) or 2 crew EVA.
OUTFIT     internal fit-out. Consumes StructuralParts + Electronics + MachineParts
           = 8% / 1.5% / 0.5% of module IMPORTED mass respectively, plus
           crew-hours = 4 h per tonne of imported mass (robots count at 0.5× rate,
           T2+). Basis rule: percentages and crew-hours apply to IMPORTED mass only;
           for ISRU-built modules use the imported (liner/hatch/fittings) mass,
           never the regolith/ice/excavation shell mass.
COMMISSION pressurize from site gas inventory: m_gas = V · 1.20 kg/m³ (101.3 kPa, 293 K)
           (×1.45 for Titan iso-baric at 146.7 kPa).
           24 h leak check: measured_leak = L_cat · m_lk with m_lk ~ LogNormal(μ = 0,
           σ = 0.5), drawn once at first check (≈ 8% of modules draw m_lk > 2;
           robot-built modules use the same σ). PASS if measured_leak < 2 × L_cat;
           else a find-and-fix loop (4 crew-hours + 0.1% mass MachineParts per
           attempt), each attempt halving m_lk before the next 24 h re-check.
           3 consecutive failures flag the module DEFECTIVE (F-14).
```

(B-2a) A module is habitable only after COMMISSION. Uncommissioned modules are vacuum-equivalent storage. Berthed crew capacity and leak/thermal simulation activate at commissioning.

(B-2b) **Berm/burial stage (optional, repeatable):** emplacing regolith cover costs the regolith (from tailings or excavation, `04-resources-isru.md` M-8), hauling (`05-industry-logistics.md`), and — above the frame threshold — an arched roof frame of **0.02 t StructuralParts per m² covered**. Frame thresholds: **rigid modules** — berm areal mass > 0.1 × ΔP/g_local in t/m²; **softgoods/inflatable modules** — berm areal mass > 1 t/m² regardless of the ΔP criterion (restraint-layer creep under dead load; violating this without a frame is the F-19 event). (Sanity: 3 t/m² of regolith on the Moon presses only 4.9 kPa onto a 101 kPa **rigid** module — rigid modules carry shallow berms directly; for them the frame rule only bites for many-meter burials or low-pressure greenhouses. Inflatables hit their 1 t/m² softgoods limit first.)

### 3.3 Pressure vessels & structure (B-3)

**(B-3a) Internal pressure (tension) — Moon, Mars, orbital, asteroid liners.** Thin-wall sizing with a minimum-gauge floor:

```
m_hull = max(  k_geom · ΔP·10³ · V · ρ / (σ_a·10⁶) ,   ρ_areal,min · A  )   [kg]
k_geom = 1.5 (sphere), 2.0 (cylinder, incl. heads), 2.5 (irregular/toroid)
ρ_areal,min = 8 kg/m² rigid (MMOD/handling floor), 6 kg/m² softgoods stack
```

**Minimum-gauge exception:** the ρ_areal,min floor is waived for tensile liners installed *inside* excavated galleries (HAB-13/HAB-14 — no MMOD or handling exposure); those liners use the tension term only, with an absolute minimum of 2 kg/m².

Design allowables (safety factor and weld/penetration knockdowns already inside σ_a; E feeds the B-3b buckling formula):

| Material | σ_a (MPa) | E (GPa) | ρ (kg/m³) | Notes |
|---|---|---|---|---|
| Aluminum (2219-class) | 120 | 72 | 2,840 | T0 default; from Aluminum + StructuralParts |
| Stainless steel | 110 | 195 | 7,900 | IronSteel feed; cryo-tough (Titan-rated) |
| Titanium (Ti-6Al-4V) | 300 | 114 (90 @ 737 K) | 4,430 | T2; Venus surface shells (hot allowable 180 MPa at 737 K) |
| BasaltFiber composite | 250 | n/a — forbidden for external pressure | 2,000 | T2 ISRU; winding machine required (§4.1) |
| Softgoods restraint (Vectran-class) | 600 (fiber-eff.) | n/a — forbidden for external pressure | 1,400 | inflatables & liners; no external-pressure capability |

(B-3b) **External pressure (buckling) — Venus surface, Titan/Europa ocean access.** Spherical shells only (cylinders pay ×1.6 mass). Classical buckling with imperfection knockdown 0.25 (NASA SP-8032 class):

```
P_allow = 0.30 · E·10⁶ · (t/r)²   [kPa]   →   t = r · sqrt( P_ext / (0.30 · E·10⁶) )
m_shell = 4π r² t ρ
```

Worked anchor (Venera-class): Venus surface, P_ext = 9,200 kPa, titanium at 737 K (E ≈ 90 GPa): t/r = 0.0185 → a 1.8 m-radius crew sphere needs t ≈ 33 mm, shell ≈ 6.0 t before insulation and cooling plant. Fabric, inflatables, and sintered masonry are **forbidden** as external-pressure hulls (no compressive/buckling integrity): the UI must refuse them.

(B-3c) **Iso-baric rule (Titan).** Habitats may run cabin pressure = ambient (146.7 kPa, pO2 21.2 kPa + N2 — `08-life-support-crew.md` owns the mix). Then ΔP ≈ 0 and hull mass = minimum gauge only; structure budget goes to insulation instead. A Titan hab pressurized to Earth-standard 101.3 kPa instead sees **45.4 kPa external crush** — a buckling case (B-3b) on what players assume is a normal hab. The build UI warns; the physics does not forgive.

(B-3d) **Pressurized ISRU masonry rule.** Compression structures (sintered regolith vaults, ice vaults) cannot hold internal pressure by weight: ballast needed is `ΔP/g_local` = **62.5 t/m² on the Moon, 27.3 t/m² on Mars** for 101.3 kPa — i.e. ~38 m / ~17 m of regolith. Therefore every pressurized ISRU structure requires an internal **tensile liner** sized by B-3a (softgoods or BasaltFiber), with the masonry shell providing only shielding, MMOD armor, thermal mass, and dead-load support. Liners anchor to a cast ring foundation: +0.5 t StructuralParts per airlock/hatch penetration.

(B-3e) **Asteroid voids.** In g < 0.01 m/s², overburden weight is negligible (10 m of rubble at ρ ≈ 1,500 kg/m³ under 1.4×10⁻⁴ m/s² presses ≈ 2 Pa): excavated pressurized galleries are **liner-only pressure vessels** (B-3a, k_geom 2.5) with the asteroid as pure shielding. Monolithic bodies (per `04-resources-isru.md` M-6 spin rule) may count rock tensile capacity only after a T3 bore-inspection task; rubble piles never.

### 3.4 Atmosphere inventory & leaks (B-4)

(B-4a) Each pressurized volume tracks gas mass by species (`08-life-support-crew.md` owns composition control). Baseline structural leak:

```
ṁ_leak = L_cat · m_gas · (ΔP / 101.3)        [kg/day]
```

`L_cat` = catalog leak rate per day (§4.1; rigid 0.02%/day, inflatable 0.04–0.05, ISRU+liner 0.06–0.10 — anchored on ISS ≈ 0.025%/day actual). **Units rule: L_cat is stored as percent/day — divide by 100 when evaluating the formula** (rigid 0.02%/day = 2×10⁻⁴/day fraction). Titan iso-baric habs use ΔP_eff = 5 kPa (diffusion/airlock-dominated): leaks are tiny but **composition drift** (O2 out, ambient N2/CH4 in at 0.02%/day of inventory) still forces makeup and CH4 monitoring (fire safety, `08-life-support-crew.md`).

(B-4b) **Airlock cycle losses** (per cycle, 4 m³ crew-lock reference):

| Airlock (§4.2) | Gas lost/cycle | Energy | Cycle time |
|---|---|---|---|
| AL-1 Vent | 4.8 kg | 0 | 10 min |
| AL-2 Pumped (Quest-class) | 0.5 kg | 1.0 kWh | 25 min |
| AL-3 Suitport pair | 0.2 kg | 0.1 kWh | 5 min |
| AL-4 Vehicle dock | 1.0 kg | 0.2 kWh | 15 min |

(B-4c) **Puncture events.** On airless bodies, unburied modules roll micrometeoroid punctures at MTBF = 20 yr per 100 m² exposed hull [order-of-magnitude from lunar meteoroid flux models; SIMPLIFIED]. A puncture multiplies leak by a per-event severity roll — **×10 (pinhole, 80% of events) or ×100 (tear, 20% of events)** — until patched (2 crew-hours + 5 kg MachineParts). Berm/burial or a 2 cm standoff Whipple wrap (+3 kg/m²) makes a module immune. Atmosphere-bearing bodies (Mars, Titan, Venus): no MMOD events at the surface.

### 3.5 Thermal envelope (B-5)

This doc supplies the **envelope load**; `09-power-thermal.md` owns generation, loops, and radiators.

(B-5a) Vacuum bodies (Moon, Mercury, Europa, Enceladus, asteroids) — radiative through MLI:

```
Q_env = ε_eff · σ_SB · A · (T_in⁴ − T_env,eff⁴)     ε_eff = 0.03 (MLI, game constant)
```

`T_env,eff` is derived from the §4.4 columns by the **half-sky rule** [LUMPED]: `T_env,eff⁴ = 0.5 · T_ground⁴ + 0.5 · T_sky⁴`, with `T_sky = 3 K` and `T_ground` = `T_day` or `T_night` from §4.4 (lunar day → T_env,eff ≈ 328 K; lunar night → ≈ 80 K). For a 294 K cabin this lands at roughly **−7 W/m² (gain) lunar day / +12.6 W/m² (loss) lunar night** — MLI makes vacuum thermals mild; glazing is the exception (below). Bermed-but-not-buried modules (partial cover per B-9a) stay on the surface T_env,eff; fully buried modules use this same formula with `T_env,eff = T_deep` (B-9a burial rule).

(B-5b) Atmosphere bodies — conductive/convective:

```
Q_env = U · A · (T_in − T_ext)
U = k_ins / t_ins    (external film resistance negligible [SIMPLIFIED])
```

Insulation classes: fiber batt k = 0.02 W/m·K (Mars CO2-filled, cheap), aerogel blanket k = 0.014 (T2, mandatory class for Titan), microporous high-temp k = 0.03 at 700+ K (Venus surface). Standard builds: Mars 10 cm fiber → U = 0.20; Titan 30 cm aerogel → U = 0.047 → **≈ 9.4 W/m² at ΔT = 201 K**; Venus aerostat 2 cm → U ≈ 1.0 (ΔT only 0–40 K).

(B-5c) **Glazing rule.** Greenhouse/viewport area radiates hard: night loss 150 W/m² of glazing on Moon/Mars unless auto-shutters fitted (+10% structure mass, close automatically). Glazed area also passes solar gain `0.7 × S_local × A_glaz` by day (S from §4.4).

(B-5d) **Heat-trace for exposed fluid lines** [W per m of line]: Moon day 0 / night 2; PSR 6; Mars 5 (night); Titan 16; Europa 8; Mercury night 2 (day: lines must be regolith-buried instead — surface hits 700 K); Venus aerostat 0. Unpowered heat trace on a cold body freezes the line in 2–12 h (event; line bursts at thaw if Water: +1 repair task).

(B-5e) **Loss-of-heating time constant.** Cabin thermal capacity C_th = 900 J/K per kg of module dry mass [LUMPED]. Cooling rate after total heat loss: `dT/dt = −(Q_env + Q_trace)/C_th`. Worked Titan example: 10 t longhouse losing 5 kW → 2.0 K/h → ~25 h from 294 K to the 244 K survival floor — Titan power failures are urgent but not instant death. On the Moon (12.6 W/m² night loss, ≈ 1.5 kW for the same hab) → 0.60 K/h → ~3.5 days from 294 K to the 244 K floor. These cooldown clocks are first-class scheduler events.

### 3.6 Radiation & shielding (B-6)

(B-6a) **Site baseline dose rates are data, not derived** — we use measured/model values per body (§4.4 master table; flagged [model] where no spacecraft has measured). Free-space GCR (canon: `03-solar-system.md` S-8a): `D_gcr = 1.8 · f_cycle(t)` mSv/day anywhere in the system — **flat with heliocentric distance at game fidelity** (anchor: MSL RAD cruise 1.84 mSv/day) — with solar-cycle modulation `f_cycle ∈ [0.65, 1.35]` (0.65 at solar maximum, 1.35 at minimum; event stream from `03-solar-system.md`) [SIMPLIFIED]. There is **no radial gradient**: belt and Mercury free space see the same 1.8·f_cycle as 1 AU; only atmospheres, magnetospheres, and body half-sky shadowing (already folded into the §4.4 surface values) change the ambient.

(B-6b) **Added shielding** — the dose-response law is **owned by `08-life-support-crew.md` §3.6** and reproduced here verbatim as canon. Shielding is accounted as areal density σ [g/cm²], summed over everything between crew and sky (hull + berm + water walls), **material-blind** [SIMPLIFIED — real polyethylene outperforms steel per kg via hydrogen content, and thin shields show a few-percent secondary-buildup bump below ~20 g/cm²; both deliberately not modeled, see §9 Q2 and 08 Q5]:

```
f_GCR(σ) = F(σ) + 0.70 · exp(−σ / 30)
F(σ) = 0.30                                for σ ≤ 1,000 g/cm²   (the familiar floor — binds for every habitat-scale stack; returns saturate past ~2 t/m²)
F(σ) = 0.30 · exp(−(σ − 1,000) / 1,000)    for σ > 1,000 g/cm²   (deep-shield extension, 08 §3.6 — decision log A3: the floor itself decays, e-fold 1,000 g/cm²)
f_SPE(σ) = exp(−σ / 12)                    (strong attenuation — ~20 g/cm² cuts an SPE ~80%)

D_in = D_site,GCR · [ f_open + Σ_i f_i · f_GCR(σ_i) ]  +  D_SPE(t) · [ f_open + Σ_i f_i · f_SPE(σ_i) ]      [mSv/day]
```

`f_i` = fraction of sky solid angle covered by shield stack i; `σ_i` = that stack's summed areal density. Canonical coverage fractions: **side berm ring only (HAB-08 "+1 ring") f_i = 0.5** (zenith open, f_open = 0.5); **roof slab only f_i = 0.5**; **berm + roof ⇒ f_open = 0**. The module hull always counts as an additional full-sky (f = 1) stack at its own areal density. Body self-shielding of the lower hemisphere is already inside `D_site` for surface values. `D_SPE(t)` is zero except during an active SPE event (B-6d).

**The 0.30 GCR floor is canon for every habitat-scale shield stack — and decays past 1,000 g/cm²** (08 §3.6 owns the law; deep-shield extension ratified, decision log A3): no berm, roof, or water wall below 1,000 g/cm² (10 t/m²) reduces GCR below `0.30 × D_site,GCR`, and a 2 t/m² berm (200 g/cm² ⇒ f_GCR = 0.301) already sits within 1% of the floor — at habitat scale, cover beyond that buys SPE blackout, thermal stability (B-9a), and MMOD immunity (B-4c), not GCR margin. **Past ~1,000 g/cm²** (≈ 6 m of regolith, ≈ 11 m of ice — burial columns only, never hull stacks) the secondary shower that creates the floor is itself absorbed and the floor decays with an e-fold of 1,000 g/cm², physically correct and consistent with 03's thick-atmosphere data: Titan reads 0.01 mSv/day under its ≈ 10,900 g/cm² column (the extension yields f_GCR ≈ 1.5×10⁻⁵ there, comfortably below the measured value), while Earth's 0.01 under 1,033 g/cm² adds geomagnetic shielding on top. Deep galleries and deep ice therefore keep improving — see HAB-13/HAB-14 and §4.3.7. (Thick-atmosphere ambients — Earth 0.01, Titan 0.01, Venus 54 km 0.03 mSv/day — remain 03-owned measured/model **overrides of D_site**, not outputs of this law.)

Material conversion table for the shielding planner (layer thickness that delivers 100 g/cm² = 1 t/m²):

| Material | ρ (kg/m³) | Layer per 100 g/cm² | Notes |
|---|---|---|---|
| Regolith (loose fill) | 1,650 | 0.61 m | berm/burial default; tailings-fed (04 M-8) |
| Water / ice | 1,000 / 917 | 1.00 m / 1.09 m | shelter jackets, Ice Home cells |
| Polyethylene / Polymers | 950 | 1.05 m | real-world best per kg (hydrogen) — modeled flat [SIMPLIFIED] |
| Steel hull | 7,900 | 0.013 m | hull plate counts toward σ |

(B-6c) Worked canon examples: lunar surface 1.37 mSv/day → under 2 m regolith (3.3 t/m² = 330 g/cm²): f_GCR = 0.30 (floor) → 1.37 × 0.30 = **0.41 mSv/day** (150 mSv/yr — a ~4-year stay against the 600 mSv career budget, 08). A 1 t/m² berm (100 g/cm²) already gives f_GCR = 0.325 → 0.45 mSv/day, and 2 t/m² is within 1% of the floor — which is why `04-resources-isru.md` budgets 2–3 t/m² of Regolith overhead per habitat: the tonnes past the first buy SPE blackout (f_SPE(200) ≈ 6×10⁻⁸), thermal stability, and MMOD immunity rather than GCR margin. Mars 0.67 (03 S-8a) → 1 m regolith (165 g/cm²): f_GCR = 0.303 → **0.20 mSv/day**.

(B-6d) **SPE events** (stream from `03-solar-system.md`; frequency up at solar max). Design envelope event = "Aug-1972 class": **1,000 mSv effective, free space, 1 AU, over 36 h**, scaling ×(1 AU/d)²; typical events are 10–100 mSv. Attenuated by f_SPE(σ) per B-6b. Physical warning time is **30–60 min game-time after the flare flag** (canon `03-solar-system.md` S-8b — real SEP onset physics); the player *receives* that warning **only if** a solar-monitor satellite with Sun line-of-sight and data link exists (player infrastructure, `06-ships-stations.md`) — otherwise the dose arrives unannounced.

(B-6e) **Storm-shelter rule**: a compliant shelter = ≥ **35 g/cm²** water-equivalent over 4π around ≥ 1.5 m³/crew (HAB-17, water-wall jackets, or any spot under ≥ 2 t/m² berm) — matching 08's worked σ = 35 g/cm² shelter exactly. Design event behind 35 g/cm²: 1,000 × f_SPE(35) = 1,000 × e^(−35/12) ≈ **54 mSv** — bad day, not a casualty. (A 25 g/cm² jacket only cuts the design event to ≈ 124 mSv under the canonical f_SPE; the spec was thickened to 35 g/cm² rather than weakening the ~55 mSv design guarantee.) In a 0.5 g/cm² suit the same event delivers ≈ 960 mSv — acute radiation syndrome territory (`08-life-support-crew.md` owns health effects; crew career framework references NASA's 600 mSv limit).

(B-6f) **Europa special case** — three-component attenuation in ice/regolith cover, with an explicit dose decomposition (x = ice depth, x_areal = areal density in g/cm²):

```
D(x) = D_site · [ f_e · 2^(−x / 1.5 cm)  +  f_b · 2^(−x / 30 cm) ]  +  D_GCR · f_GCR(x_areal)

f_e   = 0.9   trapped MeV electrons, HVT = 1.5 cm ice (top ~30 cm absorbs them)
f_b   = 0.1   bremsstrahlung photons, HVT = 30 cm ice (dominate 0.3–4 m, per Paranicas)
D_GCR ≈ 0.9·f_cycle mSv/day   half-sky of the flat 1.8·f_cycle free-space GCR (B-6a);
                              f_GCR per B-6b — floor 0.30 up to 1,000 g/cm² ⇒ shallow-gallery GCR remnant ≈ 0.27 mSv/day
                              at mean f_cycle; past 1,000 g/cm² the floor decays (A3 deep-shield extension)
```

The electron/bremsstrahlung halving thicknesses are a **Europa-specific belt-electron model** (Paranicas anchor), not the B-6b GCR/SPE law — magnetospheric MeV electrons and their photons really are absorbed nearly exponentially in ice; only the GCR term carries the secondaries floor. Rule of thumb the UI teaches: **4 m of ice overhead → ≈ 0.32 mSv/day anywhere on Europa** (trailing apex: 5,400 × 0.1 × 2^(−400/30) ≈ 0.05 bremsstrahlung + 0.27 GCR-floor remnant; electrons are long gone). The < 0.5 mSv/day habitability line is crossed at ≈ 3.4 m — 4 m is the taught value, with margin. Past ≈ 11 m of ice (1,000 g/cm²) the B-6b deep-shield extension (A3) takes over and the GCR remnant itself decays: a 30 m gallery roof (≈ 2,750 g/cm²) reads ≈ 0.05 mSv/day at mean f_cycle, and ocean-bore stations go lower still — deep Europa real estate keeps improving with depth. Surface EVA at the trailing apex (5,400 mSv/day = 225 mSv/h) is dose-budgeted in minutes; leading-hemisphere mid-latitudes (game value 200 mSv/day [model]) allow ~1 h sorties. Crewed presence is legal only after robots finish a buried habitat (Act 5 gating, §6).

### 3.7 Dust & contamination (B-7)

Each base tracks **Dust Load D ∈ [0, 100]** (dimensionless):

```
ΔD: +1.0 per AL-1/AL-2 EVA cycle; +0.1 per suitport cycle; +5 per unwashed vehicle
    docking; Mars storms (B-9b two-class model): +15 regional, +20 global;
    +0.1/day ambient (Mars), +0.05/day (Moon ops nearby), 0 (Venus aerostat,
    Titan — no dust, see acid/cryo instead)
−D: housekeeping 0.5/crew-hour; HEPA loop −1/day (0.2 kWe, filter cartridge
    = 5 kg MachineParts per 30 days); sintered landing/road pads halve all
    vehicle and ambient gains; EDS-coated surfaces halve EVA gains (T2, Blue Ghost anchor)
```

Effects: maintenance multiplier `×(1 + D/50)` on the whole base (stacks with the `05-industry-logistics.md` F-9 k_env environment multipliers — the canonical spares ledger, decision log A5); D > 40 → crew respiratory irritation condition (`08-life-support-crew.md`); D > 70 → seal-failure roll at **2%/day per module** while the condition holds (a failed module takes leak ×2 until serviced).

**Perchlorate sub-ledger (Mars only):** crew toxin exposure accrues at `0.01 · D` exposure-points/day; the wet-wipe station (0.5 kg Water per EVA cycle) and D < 30 hold it at zero; chronic exposure is a thyroid-medical event chain in 08. Perchlorate-laden regolith fed to greenhouses must pass a bake-out/wash step (+0.3 kWh/kg soil) — also yields trace Oxygen [flavor-accurate, yield negligible].

**Venus acid ledger:** replaces dust. External equipment takes M-9 upkeep ×2 (canon with 04 F-9); any envelope/gondola panel left unwashed > 30 days gains +50% leak/optical-degradation until refurbished. Condensed-acid drip after cloud transits: airlock AL-6 includes a neutralization rinse (0.2 kg Water + trace Na2CO3 from MachineParts ledger per cycle).

**Titan cryo-fouling:** suits and vehicles enter at 94 K; the warm-lock (AL-5) thaw cycle (30 min, 5 kWh) prevents ice fog and brittle-seal failures; skipping it (override) rolls a seal-crack event at 10%/cycle.

### 3.8 Aerostat statics (B-8) — Venus 50–56 km

(B-8a) Net specific lift of breathable air in Venus CO2 atmosphere:

```
L_net(h) = ρ_amb(h) · (1 − M_air/M_venus) = ρ_amb(h) × 0.333     [kg per m³ of envelope]
ρ_amb: 1.28 kg/m³ @ 52 km (81 kPa, 330 K) … 0.80 kg/m³ @ 56 km (45 kPa, 293 K)  [03 §4.4.2 V-Temperate band lookup; VIRA]
Canonical station altitude 54 km (≈ 60 kPa, ≈ 311 K, ρ ≈ 1.0 kg/m³): L_net = 0.33 kg/m³.
Helium option (imported): L_net = 0.84 kg/m³ @ 55 km (2.7× better, but inert volume).
```

(B-8b) Float condition and trim:

```
m_total ≤ 0.95 · L_net(h_f) · V_envelope          (5% reserve mandatory)
Δh response to mass/gas change: Δh ≈ −H · ln(m_new/m_old),  H = 6.5 km (local scale height)
```

Ballonet trim authority ±2 km without venting. Below 48 km (≈ 1.4 atm, 366 K) envelope over-temperature alarms; below 45 km, envelope failure. Above 62 km, UV/acid degradation doubles and lift thins — the operating band is honest to HAVOC.

(B-8c) **The double-jeopardy rule** (air-filled T3 habitats): cabin gas IS lifting gas. A leak of fraction φ of inventory sinks the base by `Δh ≈ H·ln(1/(1−φ))` ≈ 65 m per 1% — slow, hours-to-days to respond (HAVOC's "failures are graceful" finding, kept honestly). Makeup gas: N2 + O2 from the atmospheric intake chain (`04-resources-isru.md` Venus aerostat intake + RX-13 + RX-05-class O2). Helium cells (T2 starter aerostats) decouple lift from cabin at the cost of imported He.

(B-8d) Day/night: super-rotation carries the base around Venus in ≈ 6 Earth days → ~72 h of darkness per cycle; storage or RTG bridging sized by `09-power-thermal.md`. Daytime available solar in the aerostat bands: f_atm 0.30–0.70 of S ≈ 2,602 W/m² ≈ **780–1,820 W/m²** (canon `03-solar-system.md` S-6a + §4.4.2 band column; the 52–56 km V-Temperate band is f_atm 0.55 ≈ 1,430 W/m²), plus the **+0.15 f_atm (absolute) below-cloud albedo bonus** for two-sided/down-facing arrays — `09-power-thermal.md` §3.8 implements exactly this column.

### 3.9 Environmental event simulation (B-9)

(B-9a) **External temperature** per site is a closed-form day/night curve (no per-tick weather):

```
T_ext(t) = T_night + (T_day − T_night) · clamp( sin(π · t_frac_daylight), 0, 1 )^0.7
```

with `T_day, T_night, P_cycle` from §4.4 and `f_lit` = lit fraction of the cycle (from the §4.4 Solar-cycle column; default 0.5 where unstated; Moon polar rim 0.8–0.9). Define `t_cyc = t mod P_cycle`: while `t_cyc < f_lit · P_cycle` the site is lit and `t_frac_daylight = t_cyc / (f_lit · P_cycle)`; otherwise `T_ext = T_night`. **Buried** = full-coverage berm ≥ 0.5 m (Apollo HFE anchor): buried structures use constant `T_deep` instead, evaluated through the body's own envelope formula — B-5a with `T_env,eff = T_deep` on vacuum bodies, B-5b with `T_ext = T_deep` under atmospheres — burial deletes the thermal cycle entirely. Partial berms (< 0.5 m, or not full-coverage) stay on the surface curve. Bodies with negligible swing (Titan ±1 K, Venus aerostat band) use constants.

(B-9b) **Mars dust storms** (canon: `03-solar-system.md` S-9 owns the storm model and climate curves per DECISIONS C24; 04 F-4 and 09 P-9a restate it): **two storm classes only** — **regional** (dust season Ls 180–330: sector τ → 2.0–4.0, duration U(5, 40) sols, spreads to adjacent sectors at p = 0.15/sol) and **global** (p = 0.33 per Mars year at Ls = 200° ± 30°: all sectors τ → U(4, 9), duration U(60, 100) sols, decay e-fold 25 sols). Solar at the panel is `f_dust = max(0.04, exp(−0.45·τ))` — global-storm τ 4–9 ⇒ solar ×0.165 down to the ×0.04 floor (up to a 96% cut; diffuse skylight keeps non-concentrating PV barely alive [SIMPLIFIED; the 2018 τ ≈ 10.8 peak was briefly worse]). Panel soiling −0.2%/sol output (clear), −2%/sol (storm) until cleaned — crew/robot cleaning task, or the wind-cleaning event p = 0.005/sol (Spirit/Opportunity precedent). Concentrating solar gets the ×exp(−τ) direct-beam penalty instead — storms kill it dead; this is the deliberate PV-vs-fission architecture lesson.

(B-9c) **Quakes**: Moon — shallow moonquake event, mean interval 18 months per region; severity roll per event on `severity ∈ {1…5}` with `P = [0.40, 0.30, 0.15, 0.10, 0.05]`. Severity ≤ 3 events are cosmetic alerts only (no damage). Rigid inter-module connections without flex couplings (0.2 t MachineParts each) take leak ×5 damage on a severity-4+ event. Mars — marsquakes (InSight anchor) use the same event interval and table shifted down one step (`severity = max(1, roll − 1)`); same damage rule. [SIMPLIFIED to a damage-roll, no structural sim.]

(B-9d) **Dose ledger**: every crewed entity integrates `D_in` (B-6b) into per-crewmember cumulative mSv (handed to `08-life-support-crew.md`). The scheduler precomputes shelter-required intervals during SPE events and auto-drops time warp (amber alert) when any crew's projected event dose > 50 mSv.

(B-9e) **PSR thermal discipline** (canon with 04 F-5): waste heat > 110 K dumped inside a PSR site degrades local ice grade 1%/yr. Habitats in PSRs must radiate to a mast-mounted radiator aimed at sky (+15% radiator mass, `09-power-thermal.md`) or be sited on the crater rim with a cable run (2–8 km typical Shackleton geometry).

### 3.10 Maintenance & wear (B-10)

Structures consume MachineParts/spares per the canonical ledger in `05-industry-logistics.md` §3.10 F-9 (one wear model, decision log A5 — orthogonal to 02 wear and 11 maturity, no double counting): `M_spares = k_env × structure mass per year`, with k_env = 0.02 orbital / **0.04 dusty surface (Moon and Mars — equal)** / 0.03 clean surface & Titan — i.e. Moon ×2, Mars ×2, Titan ×1.5 vs the orbital baseline (05 §8.9: dusty-surface wear ×2 / MTBF ×0.6), plus preventive-maintenance and failure-repair draws (05). This doc's situational modifiers ride on top of k_env: ×0.75 buried/bermed (stable 250 K, no cycling), ×2 Venus aerostat external (acid, canon with 04 F-9), ×1.5 thermal-cycling exposed (Moon/Mercury surface modules); Titan external hardware is stainless/composite only — ordinary aluminum fittings forbidden below 120 K by the build rules (cryo-embrittlement is already inside Titan's ×1.5 k_env). Habitat structural condition = utilization analog: starved bases degrade leak rates +2%/day relative until serviced.

---

## 4. Content Catalog

### 4.1 Habitat module catalog

Leak = `L_cat` %/day of contained gas at 101.3 kPa ΔP (B-4a). The Berths column is **canonical** (see crew berth rule below). "Local" = ISRU mass from `04-resources-isru.md`/`05-industry-logistics.md` chains; ISRU build durations follow the B-2 DEPLOY machine rates.

| ID | Module (Tier) | Imported mass | Local mass | Press. volume | Berths | Leak %/day | Footprint (cells) | Anchor / notes |
|---|---|---|---|---|---|---|---|---|
| HAB-01 | Lander Cabin (T0) | 4 t | — | 20 m³ | 1 (sortie) | 0.05 | 1×1 | Apollo LM/HLS-class; doubles as ascent cabin |
| HAB-02 | Rigid Core Module (T1) | 15 t | — | 100 m³ | 3 | 0.02 | 2×1 | ISS Destiny (14.5 t, 106 m³) |
| HAB-03 | Inflatable Logistics Pod (T1) | 1.5 t | — | 16 m³ | 0 | 0.05 | 1×1 | BEAM (1.4 t, 16 m³) |
| HAB-04 | Inflatable Hab (T2) | 14 t | — | 340 m³ | 6 | 0.04 | 2×2 | TransHab (13.2 t, 339.8 m³, crew 6) |
| HAB-05 | Node / Tunnel segment (T1) | 3 t | — | 14 m³ | 0 | 0.02 | 1×1 | ISS node heritage; flex couplings optional (B-9c) |
| HAB-06 | Glazed Dome 10 m (T2) | 6 t | 12 t Glass + frame | 260 m³ | 2 (or greenhouse) | 0.06 | 2×2 | lunar/Mars greenhouse; glazing rule B-5c; crops dose-tolerant (08) |
| HAB-07 | Sintered Regolith Vault (T2) | 1.5 t (liner+hatch) | 120 t sinter + 0.6 t BasaltFiber | 200 m³ | 5 | 0.08 | 3×2 | Taylor/Meek microwave sinter + ICON-class printing; liner rule B-3d |
| HAB-08 | Berm Kit (T1, applies to any module) | — | 2–3 t/m² Regolith (04 M-8 canon; +frame per B-2b) | — | — | — | +1 ring | radiation per B-6, thermal per B-9a, MMOD immunity |
| HAB-09 | Ice Home (T2, Mars/icy bodies) | 6 t | 370 t Water (fill ≈ 1 m³/day → ~400 days, staged) | 240 m³ | 4 | 0.06 | 2×2 | NASA Langley Mars Ice Home (~400–650 m³ ice in the ConOps); translucent shielding ≈ 90 g/cm² water when full → 0.22 mSv/day on Mars (B-6b: 0.67 × f_GCR(90)); occupiable during fill at proportional shielding (ConOps-honest) |
| HAB-10 | Titan Iso-baric Longhouse (T3) | 8 t (frame+aerogel) | optional ice cladding | 500 m³ | 8 | 0.02 (drift, B-4a) | 4×2 | iso-baric rule B-3c; 30 cm aerogel; 5 kW heater node |
| HAB-11 | Aerostat Gondola Module (T3) | 6 t | — | 80 m³ | 2 | 0.04 | keel slot | HAVOC gondola; FEP-clad, acid ledger B-7 |
| HAB-12 | Envelope Unit 10,000 m³ (T3) | 1.3 t (FEP/Vectran laminate, 0.35 kg/m² + fittings) | — | (lifting/living volume) | — | 0.5 kg/day gas | — | VEGA balloon material heritage; lifts 3.3 t gross @ 54 km (B-8a) |
| HAB-13 | Asteroid Gallery, per 1,000 m³ (T3) | 1.5 t liner + 0.4 t collar | 2,500 t excavation (04 e_dig) | 1,000 m³ | 20 | 0.06 | interior | B-3e; interior dose under ≥ 10 m rock (≈ 1,500 g/cm²) is past the B-6b floor knee: f_GCR ≈ 0.18 → ≈ 0.33 mSv/day in the belt at mean f_cycle, improving with depth (A3 deep-shield extension); SPE-immune |
| HAB-14 | Europa Ice Gallery, per 500 m³ (T3/T4) | 2 t liner + heaters | melted-bore spoil | 500 m³ | 10 | 0.08 | interior, ≥ 6 m deep | cryobot-cut; B-6f cover rule; walls held < 200 K standoff |
| HAB-15 | Venus Surface Crucible (T4) | 25 t | — | 25 m³ | 2 (30-day sortie) | 0.10 | 2×2 | Venera + GEER/LLISSE lineage: Ti buckling sphere (B-3b, t≈33 mm), internal microporous insulation, 30 kWe duplex-Stirling cooling, 900 K glow radiator |
| HAB-16 | Mercury Crawler Platform (T3) | 30 t chassis | — | carries 2 modules (each ≤ 2×1 footprint, ≤ 16 t) | — | — | mobile 4×2 | terminator-pacing base, 0.5–5 km/h; sustained ≥ 3.63 km/h equatorial requirement (= 87.1 km/day), design cruise 4.0 km/h (10% margin); drive power from `10-vehicles.md` |
| HAB-17 | Storm Shelter Cell (T1) | 2 t + 14 t Water fill (or 56 t Regolith bags) | optional | 8 m³ | 5 (shelter only) | 0.02 | 1×1 | B-6e compliant (35 g/cm² water-eq, 4π) |
| HAB-18 | BasaltFiber Wound Hab (T3) | 1 t (bladder, hatches) | 6 t BasaltFiber + 2 t Glass | 300 m³ | 6 | 0.05 | 2×2 | filament-wound on-site (winder = 05 machine); the "grown locally" rigid hab |

**Crew berth rule:** the catalog **Berths column is canonical** for every catalog module — its values already fold in real-world anchor caps (TransHab crew 6 for HAB-04) and volume reserved for function-specific outfitting (HAB-06 reserves most volume for crops; HAB-09's ice annulus and HAB-10/13/14's plant/standoff space are not berth-able). The formula `berths = floor(V_press / 35 m³)` is a **fallback only**, for non-catalog or player-reconfigured hab-outfitted volumes; labs/workshops/greenhouses count 0 berths. Net habitable volume reported to `08-life-support-crew.md` as `0.5 × V_press` [SIMPLIFIED] against its 25 m³/crew comfort floor.

**Hotel load [LUMPED]:** every commissioned module draws `P_hotel = 0.05 kWe × berths + 0.005 kWe per m³ of V_press` (lighting, avionics, fans, hatch actuators), reported to `09-power-thermal.md` alongside Q_env (B-5). Airlock per-cycle energy is separate (B-4b); life-support equipment loads belong to `08-life-support-crew.md`.

### 4.2 Airlocks & interfaces

| ID | Unit (Tier) | Mass | Volume | Loss/cycle | Special |
|---|---|---|---|---|---|
| AL-1 | Vent Airlock (T0) | 0.3 t | 4 m³ | 4.8 kg | dust +1.0 D |
| AL-2 | Pumped Airlock (T1) | 1.2 t | 4 m³ | 0.5 kg + 1 kWh | Quest-class; dust +1.0 D |
| AL-3 | Suitport Pair (T2) | 0.8 t | — | 0.2 kg | dust +0.1 D; 5-min egress; SEV/Z-suit anchor |
| AL-4 | Vehicle Dock Collar (T1) | 0.6 t | — | 1.0 kg | +5 D if vehicle unwashed |
| AL-5 | Titan Warm-Lock (T3) | 2.0 t | 6 m³ | 0.3 kg + 5 kWh thaw | mandatory thaw cycle (B-7) |
| AL-6 | Venus Acid-Lock (T3) | 1.0 t | 4 m³ | 0.5 kg + rinse (0.2 kg Water) | neutralization rinse (B-7) |
| AL-7 | Dust-Lock Suite (T2) | 1.5 t | 8 m³ | 0.5 kg + 1.2 kWh | brush + EDS + bake; EVA dust gain ×0.25 total |

### 4.3 Environment engineering packages

Each package = the hazard→response table the build UI surfaces when the player first lands, plus package-specific structures.

#### 4.3.1 Moon (Acts 1–2, T1–T2)

| Hazard (real) | Engineering response (game) |
|---|---|
| Vacuum; 101 kPa ΔP everywhere | Standard tension hulls (B-3a); pumped airlocks; leak ledger (B-4) |
| 354-h night, 95 K; 390 K day; ±150 K thermal cycling | MLI (B-5a); night storage or fission sizing (09); buried modules sit at constant 250 K (Apollo HFE) — berming is thermal *and* radiation strategy; exposed modules take wear ×1.5 (B-10) |
| GCR 1.37 mSv/day (Chang'E-4 LND) + SPE | 1–3.3 t/m² regolith berms → 0.45–0.41 mSv/day (B-6b: 100 g/cm² → 0.45; 200 g/cm² → 0.41; 330 (the 2 m B-6c case) → 0.41 — the GCR floor, saturated past ~2 t/m²); shelter rule B-6e |
| Abrasive electrostatic dust (Apollo) | Dust ledger B-7; suitports + EDS (Blue Ghost anchor); sintered pads/roads |
| Micrometeoroids | Berm/burial immunity or Whipple wrap (B-4c) |
| Shallow moonquakes (Apollo seismometry, up to ~M5) | Flex couplings between modules (B-9c) |
| PSR ops at 25–40 K (Cabeus-class ice sites) | Rim-power + cable run or mast radiators (B-9e); PSR digging wear ×2 (04 M-3); crew EVA suits get 2-h cold limit in PSR [08] |

Package structures: polar **Rim Power Station** site tag (80–90% annual sun, 10 m masts, Mazarico anchor); **PSR Ice Plant** site pairing (the Act 2 flagship per 04 Chain B); sintered **Landing Pad** (200 t sinter, kills ejecta sandblasting of neighbors — without a pad, each landing within 2 km adds +5 D and a puncture roll on unbermed modules).

#### 4.3.2 Mars (Act 3, T2)

| Hazard | Engineering response |
|---|---|
| 0.61 kPa CO2; ΔP ≈ 101 kPa | Standard tension hulls; cheap fiber insulation works (CO2 gap, B-5b) |
| Dust storms (03 S-9): regional τ 2–4 for 5–40 sols, global τ 4–9 for 60–100 sols; solar f_dust = max(0.04, exp(−0.45·τ)) — down to the ×0.04 floor; soiling −2%/sol in storm | Storm model B-9b; PV oversizing + cleaning robots, or fission (the canonical 04 §3.7 architecture lesson); intakes unaffected (HEPA ×3, 04 F-4) |
| Perchlorates 0.4–0.6 wt% (Phoenix) | Perchlorate sub-ledger (B-7): wet-wipe stations, dust-locks, greenhouse soil bake-out |
| GCR/SPE 0.67 mSv/day (MSL RAD; 03 S-8a canon), 16 g/cm² atmosphere already counted | 1 m regolith (165 g/cm² → 0.20 mSv/day) or full Ice Home water cells (90 g/cm² → 0.22 mSv/day) per B-6b; storm shelter for SPE (the 16.4 g/cm² column alone, f_SPE ≈ 0.26, cuts the distance-scaled design event to ≈ 90–135 mSv outdoors) |
| −90 °C nights, 24.66 h sol | mild: U = 0.2 envelope, heater node per 250 m² (09) |
| Marsquakes (InSight) | low-severity B-9c rolls |

Package structures: **Classic ISRU Base** template (pairs with 04 Chain A: intake + Rodwell/ice mine + Sabatier stack + HAB-09); **Glazed Agri-Dome** (HAB-06; perchlorate-washed soil or hydroponics per 08).

#### 4.3.3 Venus aerostat, 50–56 km (Act 4, T3) — and surface (T4)

| Hazard | Engineering response |
|---|---|
| No surface access; everything floats | Aerostat statics B-8; envelope units HAB-12; 5% lift reserve enforced |
| H2SO4 aerosol (75–98% acid droplets) | FEP/PTFE laminate envelope (VEGA anchor); acid ledger B-7; upkeep ×2 (04 F-9) |
| Lift = cabin air (T3 air-filled design) | Double-jeopardy rule B-8c; ballonets ±2 km; makeup from atmospheric intake (04) |
| ~72 h darkness each ~6-day super-rotation lap | Storage/RTG bridging (09); winds 60–70 m/s are free circumnavigation, not a structural load (gondola moves with the air) |
| Altitude excursions | < 48 km = thermal kill band; > 62 km = UV/lift kill band (B-8b) |
| Radiation | ≈ 0.03 mSv/day [model] under ~600 g/cm² of CO2 — **among the most radiation-benign crewed sites off Earth** (only Titan's surface, under ~10× the shielding column, is lower per §4.4); no berm possible, none needed |
| Surface: 9.2 MPa, 737 K | T4 only: HAB-15 Crucible (B-3b buckling sphere, 30 kWe Stirling cooling, 30-day sorties); robotic SiC surface stations (GEER/LLISSE anchor) from T3 |

Package structures: **Cloud Base Keel** (mass-budget platform: modules occupy keel slots, build rule `Σ mass ≤ 0.95·L_net·V_env`); **Acid-Water Harvester** (the honestly-tiny 2 kg H2O/day unit, canon with 04). Aerostat deployment hardware (AR-ENV envelope kit, AR-GON gondola, AR-INF inflation set) is cataloged in §4.5 — migrated from `06-ships-stations.md` §4.9 per DECISIONS A10. Surface access is lander-class only — see `10-vehicles.md`; there is no tethered winch probe in v1.

**Tier split (decision log A6):** **robotic aerostat platforms are T2** — helium-cell starter aerostats and instrument balloons (B-8c; unlocked by 11's VH-09 Venus Atmospheric Platforms, retiered to T2) — while the **crewed** aerostat habitat (HAB-11/12 keel modules; 11's HB-05) stays **T3**. Both remain gated on Venus cloud-layer ground truth (11 DSC-08), so Act-4 timing is unchanged.

**Venus crewed surface sortie [SPECULATIVE] (T4 — decision log C17):** IN as the endgame trophy — a *single short-duration crewed sortie* in a cooled suit-vehicle (vehicle owned by `10-vehicles.md`), staged from and recovered to HAB-15; achievement-tier content, no permanent surface crew. This entry is a placeholder design item only: the 07/08/10 interface (cooling budget, suit physiology limits, dose/heat ledger hand-off) is designed at Pass 2, and the honest speculation tag is mandatory wherever the content surfaces.

#### 4.3.4 Titan (Act 5, T3–T4)

| Hazard | Engineering response |
|---|---|
| 94 K everywhere, forever | Insulation is the structure budget: 30 cm aerogel class (B-5b, ~9 W/m²); cooldown clocks (B-5e); heat-trace 16 W/m on all lines (B-5d) |
| 146.7 kPa ambient | Iso-baric rule B-3c: ΔP ≈ 0 → near-zero hull mass; Earth-pressure habs become buckling cases — UI warns |
| Cryo-embrittlement | Stainless/Ti/composite fittings only; wear ×1.5 external (B-10, k_env canon 05 F-9); warm-lock AL-5 mandatory |
| No useful sunlight (noon ≈ 1.5 W/m², 03 S-6a) | Fission only (09); Titan is the poster child for the kilopower→megawatt ladder |
| Methane lakes/seas | Shoreline sites: sea-shore cells host Sea Pumps (04) and the **Titan Submarine** dock (`10-vehicles.md`, NIAC anchor); structures float per ρ_sea ≈ 550 kg/m³ if hull mean density < that |
| CH4-rich atmosphere vs cabin O2 | Composition-drift monitoring (B-4a); CH4-in-cabin alarm at 1% (fire safety, 08) |
| Ice as ground and resource | Ice is rock here: cryo-ice allowable 5 MPa compressive [SIMPLIFIED from tens-of-MPa lab values at 100 K; creep negligible at 94 K]; **Ice Vault** variant of HAB-07 (80 t cast/cut ice + liner) costs no imported sinter mass; keep ice structure < 150 K (standoff insulation) or it weakens — F-15 |
| Radiation | 0.01 mSv/day under the ≈ 10,900 g/cm² atmosphere column (03 §4.1) — radiation-free in practice; the hazard budget all went to cold |

Megaproject: **Titan Ocean Bore** (T4): cryobot string toward the 50–100 km-deep internal ocean; descent rate `v = P_t/(A · E_melt)`, E_melt ≈ 700 MJ/m³ from 94 K; a 500 kWt fission cryobot at 0.8 m² bores ~3.2 m/h — **≈ 11 months of continuous boring per 25 km, plus 30 days per 5 km segment to emplace a refreeze-back relay/casing station (each: 5 t + 50 kWe) → ≈ 16 months total per 25 km**; the same 30-day-per-5-km casing overhead applies to all ocean bores (Europa, Enceladus). Multi-year, multi-launch endgame content; science payoff + [SPECULATIVE] ocean chemistry sampling.

#### 4.3.5 Europa (Act 5, T3–T4)

| Hazard | Engineering response |
|---|---|
| **5.4 Sv/day** surface (trailing apex; JPL/Paranicas), 200 mSv/day leading [model] | Crew may not land until robots bury a habitat: B-6f three-component shielding; ≥ 4 m ice → ≈ 0.32 mSv/day (< 0.5 mSv/day from ≈ 3.4 m; the residual is the B-6b GCR floor); EVA dose budgets in minutes (trailing) to ~1 h (leading) |
| Electronics death | Robots need Clipper-style vaults: +0.3 t per robot, electronics-lifetime ×20 (anchor: Europa Clipper ~9 mm vault) |
| Vacuum, 50–125 K | Lunar-style MLI + heat trace 8 W/m; ice galleries sit at ~100 K walls — heaters + liner standoff |
| Ice as overburden | HAB-14 galleries melted at 6–30 m depth by construction cryobots; spoil refreezes as closure plug |
| Jupiter system logistics | Callisto staging doctrine (HOPE anchor): crewed ops based at 0.14 mSv/day Callisto (03 §4.1; package below), commanding Europa surface robots via **supervised autonomy / task-level command at ≈ 4.0–8.5 s one-way light time** (Callisto–Europa separation 1.21–2.55 × 10⁶ km) — far too long for joystick teleoperation (`13-architecture.md` remote-ops model) |
| Ocean access | **Europa Ocean Bore** megaproject: same cryobot physics as Titan (E_melt ≈ 620 MJ/m³ from ~100 K); 20 km shell at 500 kWt / 0.8 m² ≈ 3.6 m/h ≈ **8 months boring + 4 casing stations × 30 days ≈ 12 months total** (Titan-bore casing rule) — shorter shell than Titan but every tonne arrives through Jupiter's radiation tax; planetary-protection protocol flavor event chain [no gameplay penalty v1] |

**Callisto staging package** (NASA RASC **HOPE** study, 2003 — the Act 5 crewed base of the Jupiter system; environment row in §4.4):

| Hazard | Engineering response |
|---|---|
| Vacuum; 101 kPa ΔP | Lunar-pattern tension hulls (B-3a), pumped airlocks (B-4b); MMOD rules B-4c |
| 0.14 mSv/day dose + GCR (03 §4.1/S-8c; JPL-ladder context §2) — outside Jupiter's hard belts | Long-stay capable with shallow ~1 t/m² berms (B-6b: 100 g/cm² regolith, f_GCR = 0.325 → 0.05 mSv/day belt-component); shelter rule B-6e still applies for SPE remnants |
| 165 K day / 80 K night, 400.5 h solar cycle | MLI per B-5a; burial to T_deep ≈ 120 K (B-9a) |
| Icy, low-abrasion regolith — no lunar-style electrostatic fines [model] | Dust ledger off; standard pads still required for landing ejecta |
| Jupiter logistics hub | Supervised-autonomy ops center for Europa/Io robotics (4.0–8.5 s one-way to Europa); propellant depot pairing with `06-ships-stations.md` |

#### 4.3.6 Enceladus (Act 5, T3)

| Hazard | Engineering response |
|---|---|
| g = 0.113 m/s² | Anchored foundations (04 M-6 lite: 4 microspine pads per module); wheeled vehicles marginal — hoppers preferred (10) |
| 75 K vacuum | Titan-grade insulation without the atmosphere's convection — MLI suffices (B-5a) |
| Plume fallout near stripes | Fissure-adjacent cells: panel fouling +0.1%/day; don't put PV there |
| Vent variability | Plume Collector output varies ±50% on a 1.37-day tidal cycle (real: plume brightness is diurnally modulated) |
| Radiation | ~1 mSv/day [model: GCR-dominated; Saturn's belts are mild and E-ring-quenched at 3.95 R_S]; standard berm rules |

Package structures: **Plume-Curtain Collector** (T3): mast-and-fence electrostatic grain catcher straddling a tiger-stripe fissure; yield 20–100 kg/day of pre-mixed ocean material (Water 0.93, NH3 0.01, CO2 0.03, organics/salts 0.03 [Cassini INMS/CDA-derived, SIMPLIFIED]) — valuable as drilling-free ocean sampling and Nitrogen/Ammonia source; bulk Water still comes cheaper from surface ice (grade 0.95+, 04). Flagged concept-level — open question #6. **South-Polar Shaft** (T4 option): the ~2–5 km thin shell makes Enceladus the *cheapest* ocean access in the game (8× shorter bore than Europa) at the price of 9.6 AU logistics.

#### 4.3.7 Asteroids — NEA & belt (Acts 3–4, T2–T3)

| Hazard | Engineering response |
|---|---|
| µg: nothing stays put | Anchoring per 04 M-6 (microspines 250 N, bolts 2,000 N); excavation debris rule (04 M-6.3) |
| No overburden weight | Liner-only galleries (B-3e); rock = shielding, never pressure containment on rubble piles |
| GCR 1.8·f_cycle mSv/day in the belt — same as everywhere in free space (flat with distance, B-6a; 1.17–2.43 over the solar cycle) | Interior galleries under ≥ 10 m rock (≈ 1,500 g/cm²) sit past the B-6b floor knee: **f_GCR ≈ 0.18 → ≈ 0.21–0.44 mSv/day over the solar cycle, with total SPE immunity** — and the A3 deep-shield extension keeps paying: 30 m of rock (≈ 4,500 g/cm²) reads ≈ 0.011–0.022 mSv/day, Earth-surface-class, for zero imported shielding mass; this is the belt's quiet selling point |
| Rotation (≤ 2.2 h rubble limit, 04 M-6.4) | Galleries aligned to spin axis; despin option per 04; centrifugal "gravity" off-axis is millis-g — not health-relevant (08 owns µg health) |
| Thermal: fast sun/shade cycles (hours) | Interior is thermally dead-stable; only surface kit takes cycling wear ×1.5 |

Package structures: **Gallery Network** (HAB-13 stacks; berths 20/1,000 m³ make excavated rock the cheapest big habitable volume in the game once a T3 excavation chain runs); **Surface Collar Station** (dock + airlock + comms, 8 t).

#### 4.3.8 Mercury (Act 4 optional / endgame, T3)

| Hazard | Engineering response |
|---|---|
| 176-day solar day; 700 K subsolar (perihelion), 100 K night | Either **polar/PSR siting** (Moon-pattern base; MESSENGER ice, purer than lunar: grade roll 0.5/0.8/0.95) or the **Terminator Crawler** (HAB-16): stay in the twilight band by moving ≥ 3.63 km/h at the equator (= 87.1 km/day; slower at latitude ×cos φ) |
| SPE ×(1 AU/d)²: ≈ ×6.7 at mean distance (orbit-averaged, 03 S-8b), up to ×10.6 at perihelion (0.307 AU) | Storm shelter non-negotiable, sized to the ×10.6 perihelion case; receiving the 30–60 min flare warning (03 S-8b) needs an inner-system monitor sat |
| GCR 1.8·f_cycle mSv/day (flat with distance, B-6a; 03 §4 table) + SPE | berm rules as Moon |
| Solar bonanza 6,270–14,450 W/m² (03 S-4a) | 10× Earth-orbit PV yield; drives the T3+ **Mass Driver Port** (launcher itself owned by `05-industry-logistics.md` §3.8/§4.5; we own its 20-cell site, pad, and 2 MWe substation footprint) |
| Day thermal siege on stationary kit | Surface lines buried (B-5d); radiators face poleward sky; crawler radiators trail in own shadow |

### 4.4 Environment master table (canonical inputs to B-5/B-6/B-9)

| Site | g (m/s²) | P_amb | T_day / T_night (K) | T_deep (K) | Solar cycle | Unshielded dose (mSv/day) | S_local solar (W/m²) | Notes |
|---|---|---|---|---|---|---|---|---|
| Moon equator | 1.62 | vacuum | 390 / 95 | 250 | 708.7 h | 1.37 (LND, measured) | 1,361 | dust ledger on |
| Moon polar rim | 1.62 | vacuum | 230 / 120 | 190 | 708.7 h, 80–90% lit | 1.37 | 1,361 grazing | mast PV |
| Moon PSR floor | 1.62 | vacuum | 40 / 25 | 38 | never lit | 1.37 | 0 | B-9e heat discipline |
| Mars datum | 3.71 | 0.61 kPa CO2 | 270 / 185 | 215 | 24.66 h | 0.67 (RAD, measured; 03 S-8a) | 490–715 | storms B-9b; perchlorate |
| Venus 54 km | 8.87 | ≈ 61 kPa CO2 (53–80 kPa over the 52–55 km band) | 310 / 295 | — | ≈ 6 d (super-rotation) | 0.03 [model] | 400–1,000 day | acid ledger; B-8 |
| Venus surface | 8.87 | 9,200 kPa | 737 / 737 | 737 | 116.8 d | ~0.001 [model] | ~15–20 (heavy overcast; Tomasko/Pioneer Venus net-flux) | T4 sorties only |
| Titan surface | 1.352 | 146.7 kPa N2 | 94 / 93.5 | 94 | 15.95 d (moot) | < 0.01 [model] | ~1 (useless) | iso-baric; fission |
| Europa trailing | 1.315 | vacuum | 125 / 85 | 100 | 85.2 h | 5,400 (JPL) | 50 | robot-only surface |
| Europa leading | 1.315 | vacuum | 125 / 85 | 100 | 85.2 h | 200 [model] | 50 | 1-h EVA budgets |
| Callisto | 1.235 | vacuum | 165 / 80 | 120 | 400.5 h | 0.1 (JPL ladder) | 50 | HOPE crew staging; dust ledger off |
| Enceladus (non-stripe) | 0.113 | vacuum | 80 / 65 | 75 | 32.9 h | ~1 [model] | 14.8 | anchoring lite |
| NEA @ 1 AU | ~10⁻⁴ | vacuum | 350 / 150 (fast cycle) | 230 | hours | 1.8·f_cyc (03 §4 table) | 1,361 | 04 M-6 rules |
| Belt C-type @ 2.7 AU | ~10⁻⁴–10⁻² | vacuum | 233 / 120 | 160 | hours | 1.8·f_cyc (flat GCR, B-6a) | 187 | gallery doctrine |
| Ceres | 0.28 | vacuum | 235 / 110 | 160 | 9.07 h | 1.8·f_cyc (03 §4 table) | 178 | ice crust (04) |
| Mercury equator | 3.70 | vacuum | 700 / 100 | 350 | 4,223 h | 1.8·f_cyc + SPE ×6.6 mean / ×10.6 perihelion | 6,270–14,450 | crawler or pole |
| Mercury PSR | 3.70 | vacuum | < 100 | 90 | never lit | 1.8·f_cyc | 0 | purest PSR ice |

(B-5a derives `T_env,eff` from the T_day/T_night columns via the half-sky rule `T_env,eff⁴ = 0.5·T_ground⁴ + 0.5·T_sky⁴`, T_sky = 3 K [LUMPED]; buried structures substitute T_deep per B-9a. `03-solar-system.md` owns orbital-season refinements.)

---

## 5. Player Interaction & UI

(Shared UI grammar in `12-gameplay-economy-ui.md`.)

- **Base designer** (top-down grid): drag-place footprints; network layers toggle (power / thermal / fluid / data) with per-edge capacity coloring; terrain overlay (rough, crater-wall berm-ready, PSR, shore, fissure). Invalid placements (B-3b fabric-under-crush, Titan Earth-pressure hab, unanchored µg module) show the violated rule by ID with one-line physics ("146.7 kPa outside > 101.3 kPa inside: hull would buckle — run iso-baric?").
- **Environment dashboard** per base: live T_ext curve with day/night marker, dose rate inside vs outside with shield breakdown (B-6b terms itemized), Dust Load gauge with source attribution, storm/SPE forecast strip (only if monitoring assets exist — otherwise shows "NO SOLAR MONITOR: no SPE warning").
- **Shielding planner**: paint berm thickness per module; readout in t/m², g/cm², resulting mSv/day, and crew-years-to-600-mSv at that rate. The teaching tool for B-6.
- **Commissioning checklist** (B-2): gas inventory sourcing (which tank/intake pays the 1.2 kg/m³), leak-check progress bar, pass/fail with measured vs catalog leak.
- **Aerostat trim panel** (Venus): lift margin %, float altitude, ballonet state, projected Δh for planned cargo transfers (B-8b), kill-band altimeter bands in red.
- **Cooldown clocks**: any base whose heating/cooling fails shows time-to-threshold (B-5e) in the alert bar; scheduler auto-drops warp at T−6 h.
- **EVA dose budgeting** (Europa/Mercury): suit sortie planner shows minutes-to-budget at local rate before egress confirm.
- **Megaproject view** (bores): depth vs time strip-chart, relay-station checklist, power continuity warnings (a bore stalls and refreezes after 72 h unpowered — resume costs 20% of segment time).

---

## 6. Progression Hooks

| Tier / Act | Unlocks (this domain) | Gameplay meaning |
|---|---|---|
| **T0 (Act 1)** | HAB-01, AL-1; LEO station modules live in `06-ships-stations.md` | Sortie camps only; first lunar landings are tents-with-leak-ledgers |
| **T1 (Acts 1–2)** | HAB-02/03/05/17, AL-2/AL-4, Berm Kit, flex couplings, storm-shelter doctrine | First permanent Moon base: berm it or bleed crew dose; night survival = storage sizing lesson (09) |
| **T2 (Acts 2–3)** | HAB-04/06/07/09, AL-3/AL-7, sinter printer + pads, EDS, Ice Home, Mars package | ISRU construction begins: imported mass per berth drops ~10× (HAB-07: 1.5 t imported / 5 berths vs HAB-02: 15 t / 3); classic Mars base; dust/perchlorate discipline |
| **T3 (Acts 4–5)** | HAB-10/11/12/13/16/18, AL-5/AL-6, Venus Cloud Base, Titan package, asteroid galleries, Mercury crawler, Europa robotic phase, Enceladus collectors | The exotic-habitat act: every new body is a new physics puzzle; belt galleries become the cheap habitable volume; Callisto-staging doctrine for the Jupiter system |
| **T4 (Endgame) [SPECULATIVE-adjacent]** | HAB-14 crewed Europa galleries, HAB-15 Venus Crucible, Titan/Europa/Enceladus ocean bores, Mercury mass-driver port city | Megaprojects: ocean access, surface-of-Venus sorties, self-sufficient off-Earth settlements (berth count × closed loops from 08 define the campaign-end "civilization" metric in 12) |

Research costs/prereqs live in `11-research-tech.md`. Act-gating teeth: Europa crew landing is hard-locked behind "buried habitat commissioned by robots" (B-6f); Venus surface crew behind HAB-15; nothing requires 3D orbital geometry — polar sites, terminator bands, and hemispheric dose asymmetries are site *tags* from `03-solar-system.md` (honest 2D simplification, stated in-UI).

---

## 7. Cross-System Interfaces

**Consumes:**
- `03-solar-system.md`: body/site catalogs with terrain tags (PSR, shore, fissure, crater-wall), environment columns of §4.4 (seasonal refinement), storm and SPE event streams, solar flux vs distance, asteroid spin/class data.
- `04-resources-isru.md`: Regolith for berms/sinter (2–3 t/m² canon), Water for ice structures and shelter fills, BasaltFiber/Glass for ISRU hulls, gas inventories for commissioning (N2/O2), site tailings-slot pressure (M-8), digging energy e_dig for excavation, environment maintenance multipliers (M-9 canon).
- `05-industry-logistics.md`: StructuralParts/Electronics/MachineParts for Outfit stage (B-2), HEPA/filter consumables, hauling for berm emplacement, the filament winder and sinter-printer build chains, mass-driver port industrial stats.
- `08-life-support-crew.md`: cabin atmosphere standards (101.3 kPa default; Titan 146.7 kPa iso-baric; 70.3 kPa/26.5% O2 outpost option), crew-hours for Outfit/repairs, health consequences of dose/dust/perchlorate ledgers we feed it.
- `09-power-thermal.md`: electric power and thermal-loop service for heater/cooler nodes, heat-trace loads (B-5d), PSR mast radiators, night storage, the 30 kWe Venus Crucible cooling plant, cryobot 500 kWt cores.
- `10-vehicles.md`: rover-cranes for Deploy, dust-washed vehicle docking, Mercury crawler drivetrain, Titan submarine + shore dock, Europa hardened robots (+0.3 t vaults).
- `11-research-tech.md`: tier unlocks per §6.
- `12-gameplay-economy-ui.md`: module purchase/launch costs, alert bus, settlement-metric scoring.
- `13-architecture.md`: event scheduler (cooldown clocks, SPE shelter windows, bore stalls), the supervised-autonomy remote-ops model for Europa robotics (task-level command at ≈ 4.0–8.5 s one-way Callisto–Europa light time — not real-time teleoperation), save-stable closed-form environment curves (B-9a).
- `06-ships-stations.md`: module commonality (HAB-02/03/04 are flight modules that land); solar-monitor satellites for SPE warning; orbital depots paired with surface propellant plants.

**Provides:**
- `08-life-support-crew.md`: berth counts and net habitable volume per base, interior dose rates (B-6b), Dust/perchlorate/acid exposure ledgers, shelter compliance state, cabin gas inventories and leak makeup demands.
- `09-power-thermal.md`: envelope thermal loads Q_env per module (B-5a/b), per-module electrical hotel loads (P_hotel rule, §4.1), heat-trace W/m totals, glazing night loads, heater/cooler node placement on its loops.
- `04-resources-isru.md` / `05-industry-logistics.md`: the surface grid, site definitions, and 16 tailings slots per site; sintered pads halving dust; construction demand for their products.
- `06-ships-stations.md`: shared pressure-vessel rules B-3a (it reuses σ_a table and leak model for hulls), storm-shelter rule B-6e for crewed vessels.
- `10-vehicles.md`: dock interfaces (AL-4/AL-5/AL-6), pad locations, Mercury crawler platform spec.
- `12-gameplay-economy-ui.md`: settlement metrics (berths, mSv/day, closure), base-level alert definitions.
- `13-architecture.md`: data schemas for sites/cells/networks, the closed-form environment functions, dose-ledger integration contract.

---

## 8. Failure Modes & Edge Cases

| ID | Failure / edge case | Rule |
|---|---|---|
| F-1 | **Depressurization** (puncture B-4c, seal wear D > 70, quake damage) | Leak ×10 (pinhole) or ×100 (tear) per the B-4c severity roll until patched; cabin reserve time = m_gas/ṁ; crew don suits at < 55 kPa alarm (08); module auto-isolates if hatches powered |
| F-2 | **Moonquake on rigid couplings** | Severity-4+ event without flex joints: leak ×5 on affected tunnel + 1 repair task (B-9c) |
| F-3 | **Mars storm power crisis** | B-9b solar ×0.2 floor for 30–100 sols; canon with 04 F-4; fission-less bases must shed load (08 triage order: shelter > LS > ISRU) |
| F-4 | **PSR thermal pollution** | Canon: 04 F-5 (1%/yr grade decay if > 110 K dumped in PSR); mast-radiator or rim-siting avoids |
| F-5 | **Aerostat envelope leak** | Lift loss per B-8c: 65 m sink per 1% gas; below 48 km = thermal kill band; repair = EVA patch task (acid suit, 2 crew-h per 10 m² hole-equivalent); double-jeopardy means cabin pressure alarms double as altitude alarms |
| F-6 | **Acid degradation neglected** | Unwashed external kit: leak/optical +50% after 30 days; upkeep ×2 baseline (canon 04 F-9) |
| F-7 | **Titan freeze-out** | Heating lost: cooldown clock (B-5e, ~25 h for HAB-10); at 244 K cabin = crew survival line (08 cold-injury chain); at < 150 K plumbing bursts (every Water line = repair task); restart needs 2× heater power for 12 h |
| F-8 | **Europa EVA dose overrun** | Suit sortie past budget: acute dose event (08); trailing-hemisphere surface work without vaulted robots burns electronics MTBF ×20 |
| F-9 | **Cryobot stall** | Bore unpowered > 72 h refreezes: resume costs 20% of segment time; stuck-probe event (5%/stall) loses the cryobot — relay-station casing prevents total-bore loss |
| F-10 | **Asteroid liner blowout** | Gallery vents through breach: thrust = ṁ·v_e on the *body* is negligible [honest], but debris cloud triggers 04 M-6.3 hazard; gallery refill = full commissioning gas cost — galleries should be compartmentalized (collar bulkheads every 1,000 m³) |
| F-11 | **Mercury crawler breakdown** | Stationary at equator: dawn terminator arrives at 87.1 km/day; time-to-700 K = buffer distance / 87.1 km/day; rescue tow or repair before sunrise — a literal race against dawn |
| F-12 | **Perchlorate exposure chronic** | Exposure points (B-7) > threshold → thyroid medical chain (08); root causes: D > 30, no wet-wipe water budget, broken HEPA |
| F-13 | **Dust load runaway** | D > 70: random seal failures (leak ×2 events); maintenance ×2.4; the death-spiral is intended — dust discipline is a core lunar skill |
| F-14 | **Commissioning failure** | Measured leak ≥ 2× catalog: find-and-fix loop (B-2); 3 consecutive failures flag the module DEFECTIVE (refund path in 12, or scrap to StructuralParts at 30%) |
| F-15 | **Ice-structure warm creep** | Titan/ice vault wall warmed > 150 K (insulation standoff failed): structure condition −1%/day until cooled; > 200 K: collapse event (non-pressurized only — pressurized ice builds were already liner-held per B-3d) |
| F-16 | **Glazing night freeze** | Shutters failed/absent: greenhouse loses 150 W/m²; crop cold-kill below 278 K (08); heater surge or crop loss |
| F-17 | **Iso-baric hab on pressure excursion** | Titan hab vented to < 120 kPa cabin (e.g. botched airlock): 26.7 kPa external crush on a minimum-gauge hull → buckling damage roll each hour until equalized; the UI's loudest klaxon |
| F-18 | **SPE with no warning network** | No monitor sat: dose arrives unshielded for crew outside; the cheap fix (one smallsat, 06) becomes obvious exactly once |
| F-19 | **Berm-on-inflatable error** | Berming softgoods modules beyond 1 t/m² without frame (B-2b): creep deformation event, leak +0.02%/day permanent per excess t/m² |
| F-20 | **Save/warp consistency** | All environment curves closed-form (B-9a); dose/dust integrate linearly between events; scheduler owns next-threshold computation (13 invariant test) |

---

## 9. Open Questions

1. **Grid scale vs body size**: 10 m cells × 64² site works for the Moon/Mars; is it right for aerostat keels (mass-slots, not cells) and asteroid interiors (3D-ish galleries flattened to 2D decks)? Current answer: keel = slot list, gallery = stacked 2D decks; needs a UI prototype.
2. **Deep-burial GCR floor (B-6b)**: 08's canonical f_GCR floor (0.30, secondaries) is adopted here as binding at every depth, so 10 m asteroid galleries and 4 m Europa ice bottom out at 0.30 × ambient GCR — yet 03's measured thick-atmosphere overrides (Earth 0.01 mSv/day under 1,033 g/cm², Titan < 0.01 under ~10,900 g/cm²) show the floor must physically break somewhere past ~1,000 g/cm². Escalated to 08: either confirm that habitat shield stacks never graduate past the floor (the current binding answer), or publish a deep-shield extension (e.g. the floor itself decaying with an e-fold of ~1,000 g/cm²) — that would restore "Earth-surface-class" deep galleries and materially buff belt and Europa endgame real estate. Related fidelity items deliberately left out of the material-blind model: polyethylene's hydrogen advantage and the thin-shield secondary-buildup bump below ~20 g/cm² (08 Q5).
3. **Leak-rate canon**: rigid 0.02%/day is anchored (ISS ≈ 0.025%); inflatable 0.04–0.05 and ISRU-liner 0.06–0.10 are extrapolations. Hostile reviewers will ask for BEAM leak data (NASA reports it performed *better* than rigid spec) — consider flipping inflatables to 0.02 and making ISRU liners the only leaky class.
4. **Venus 52–56 km solar flux band** (B-8d, 400–1,000 W/m² + 40% albedo bonus): verify against Pioneer Venus LSFR/Tomasko net-flux profiles before 09 locks its power curves (the surface value, ~15–20 W/m² in §4.4, is already anchored to the same Tomasko et al. 1980 dataset).
5. **Europa leading-hemisphere dose** (200 mSv/day game value): model-based; Paranicas maps suggest possibly lower at high latitude on the leading side. If much lower, leading-pole surface ops become too easy — re-check before tuning Act 5 difficulty.
6. **Enceladus Plume-Curtain Collector** (20–100 kg/day): no published engineering study at this fidelity; either find a NIAC-class anchor or down-scope to a science instrument and let bulk ice mining carry the resource role.
7. **Cryo-ice structural allowable** (5 MPa at < 150 K): literature gives tens of MPa short-term compressive at 100 K, but long-term data is thin; conservative factor chosen — needs a citation pass or an [ICE-SIMPLIFIED] tag in the final bible.
8. **Mercury crawler vs polar base balance**: the crawler is spectacular but the polar base is strictly cheaper; does the crawler need an exclusive economic hook (equatorial mass-driver alignment? subsolar solar-furnace metallurgy at 14 kW/m²?) to be more than flavor?
9. **Titan iso-baric hyperbaric physiology**: 146.7 kPa with pN2 ≈ 126 kPa is fine for steady-state but creates mild decompression bookkeeping when crew transfer to 101.3 kPa ships — does 08 want the full saturation/decompression model or a flat 2-h transfer-acclimation timer?
10. **Quake damage model**: severity-roll-only (B-9c) vs per-structure fragility curves — fragility is more sim-honest but likely over-engineering for the fun delivered; decide with 13's complexity budget.
11. **Shared-canon audit**: berm areal-mass guidance (2–3 t/m²), storm solar floor (×0.2), maintenance multipliers, and the §4.4 master table must match `03-solar-system.md`, `04-resources-isru.md`, `08-life-support-crew.md`, and `09-power-thermal.md` final drafts byte-for-byte — schedule the reconciliation pass.
