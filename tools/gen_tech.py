"""Generate the full 132-node tech tree + 18 Discoveries content pack from
the canon tables in design/extracts/11-research-buildspec.md.

Run:  python tools/gen_tech.py        (from the repo root)

Emits data/core/tech/<slug>.toml (one file per node, replacing the legacy
13-node pack) and data/core/discoveries/<slug>.toml. Deterministic output;
re-run after editing the tables below. Tier SCI sums are asserted against
the bible's economy targets (11 §3.3) so transcription drift fails loudly.
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TECH_DIR = ROOT / "data" / "core" / "tech"
DSC_DIR = ROOT / "data" / "core" / "discoveries"

# (slug, name, tier, branch, prereqs, sci, ed[(family,val)...], unlocks,
#  grants, discoveries, era, speculative, anchor)
# prereqs: str code = AND term; tuple of codes = OR group (any one).
N = []


def n(slug, name, tier, branch, prereqs, sci, ed, unlocks=(), grants=(),
      dsc=(), era=False, spec=False, anchor=""):
    N.append(dict(slug=slug, name=name, tier=tier, branch=branch,
                  prereqs=prereqs, sci=sci, ed=ed, unlocks=list(unlocks),
                  grants=list(grants), dsc=list(dsc), era=era, spec=spec,
                  anchor=anchor))


# ---- Propulsion (PR) — 23 -------------------------------------------------
n("pr00_flight_proven_stack", "Flight-Proven Stack", "T0", "PR", [], 0, [],
  grants=["part:SRM-2", "part:SRM-49", "part:OMS-27", "part:SPS-91",
          "part:K-845", "part:KV-981", "part:H-102", "part:RCS-N10",
          "part:RCS-D400", "part:ION-2", "part:HALL-1", "part:tanks_parametric"],
  anchor="2049 baseline: Falcon 9 / Centaur / Soyuz heritage; NSTAR; SPT-100")
n("pr01_deep_throttle_landers", "Deep-Throttle Landing Engines", "T1", "PR",
  ["pr00", "gn02"], 80, [("StorableEngines", 100)],
  grants=["part:LND-71"], anchor="Apollo LMDE 10:1 throttle; BE-7")
n("pr02_reusable_methalox", "Reusable Methalox Heavy Lift", "T1", "PR",
  ["pr00"], 220, [("KeroloxEngines", 200)],
  grants=["part:M-2256", "part:MV-2530", "part:RCS-M2K", "ops:reusable_booster"],
  era=True, anchor="$/kg to LEO collapses. SpaceX Raptor FFSC / Starship")
n("pr03_modern_hydrolox", "Modern Hydrolox Upper Stages", "T1", "PR",
  ["pr00"], 100, [("HydroloxEngines", 150)],
  grants=["part:HL-67", "part:H-2280"], anchor="RL10 family; Centaur V")
n("pr04_cryo_fluid_mgmt", "Cryogenic Fluid Management", "T1", "PR",
  ["pr00"], 150, [("CryoFluidMgmt", 200)],
  grants=["part:ZBO-90", "part:ZBO-20", "part:sunshield", "part:tank_pmd"],
  anchor="ULA IVF; NASA eCryo/CFM demos")
n("pr05_orbital_depot", "Orbital Propellant Depot", "T1", "PR",
  ["pr04", "gn01"], 250, [("CryoFluidMgmt", 400)],
  grants=["part:DEP-60", "part:PTC-200", "ops:propellant_transfer"],
  era=True, anchor="ULA depot studies; Starship HLS refueling")
n("pr06_gridded_ion", "Gridded Ion Propulsion", "T1", "PR",
  ["pr00"], 120, [("EPThrusters", 100)],
  grants=["part:ION-7"], anchor="NASA NEXT-C: 6.9 kW, 4190 s, 236 mN")
n("pr07_hall_clusters", "High-Power Hall Clusters", "T1", "PR",
  ["pr00"], 140, [("EPThrusters", 150)],
  grants=["part:HALL-12"], anchor="AEPS/HERMeS 12.5 kW (Gateway PPE)")
n("pr08_solar_sail_demo", "Solar Sail Demonstrator", "T1", "PR",
  ["pr00"], 90, [], grants=["part:SAIL-86"],
  anchor="NEA Scout; IKAROS, LightSail 2")
n("pr09_ntr", "Nuclear Thermal Rocket", "T2", "PR",
  ["pr04", "pw04"], 700, [("HydroloxEngines", 500), ("FissionSystems", 300)],
  unlocks=["core:engine_ntr_k2"], grants=["part:NTR-73"],
  era=True, anchor="Isp ~900 s. NERVA/SNRE; DARPA DRACO")
n("pr10_heavy_ntr", "Heavy NTR Core", "T2", "PR",
  ["pr09"], 500, [("NTRCores", 800)],
  grants=["part:NTR-246"], anchor="NERVA XE': 246 kN ground-tested 1969")
n("pr11_lantr", "LANTR Augmentation", "T2", "PR",
  ["pr09"], 350, [("NTRCores", 600)],
  grants=["ops:lantr"], anchor="Borowski LANTR studies")
n("pr12_ntr_alt_propellants", "NTR Alternate Propellants", "T2", "PR",
  ["pr09"], 300, [("NTRCores", 600)],
  grants=["ops:ntr_ammonia", "ops:ntr_water"],
  anchor="NERVA-era alternate-propellant studies")
n("pr13_isru_refuelable_landers", "ISRU-Refuelable Landers", "T2", "PR",
  ["pr02", "is04"], 400, [("MethaloxEngines", 300)],
  unlocks=["core:engine_ml111"], grants=["part:ML-24", "ops:field_refuel"],
  anchor="Project Morpheus; Mars Direct ERV")
n("pr14_large_solar_sails", "Large Solar Sails", "T2", "PR",
  ["pr08"], 350, [], grants=["part:SAIL-1650"],
  anchor="NASA Solar Cruiser (1653 m^2)")
n("pr15_heavy_depots", "Heavy Depot Infrastructure", "T2", "PR",
  ["pr05"], 450, [("CryoFluidMgmt", 700)],
  grants=["part:DEP-600", "ops:lh2_depot_insulation"],
  anchor="ULA/NASA cryo depot architectures")
n("pr16_nested_hall", "Nested-Channel Hall Thrusters", "T3", "PR",
  ["pr07", "pw08"], 1200, [("EPThrusters", 900)],
  grants=["part:HALL-100"], anchor="X3 nested Hall, 102 kW demo")
n("pr17_mpd", "MPD Thrusters", "T3", "PR",
  ["pr16"], 1800, [("EPThrusters", 1500)],
  grants=["part:MPD-200"], anchor="NASA Lewis / MAI applied-field MPD")
n("pr18_vasimr", "VASIMR", "T3", "PR",
  ["pr16"], 1600, [("EPThrusters", 1200)],
  grants=["part:VAS-200"], anchor="Ad Astra VX-200: 200 kW lab firings")
n("pr19_industrial_sails", "Industrial Solar Sails", "T3", "PR",
  ["pr14"], 1000, [], grants=["part:SAIL-10K"],
  anchor="scaled NIAC/JPL sail-cargo studies")
n("pr20_inspace_engine_refurb", "In-Space Engine Refurbishment", "T3", "PR",
  ["pr10", "in06"], 1400, [("NTRCores", 1200)],
  grants=["ops:ntr_refurb", "part:pmd_lad_coupler"],
  anchor="ISS ORU servicing; OSAM")
n("pr21_fission_fragment", "Fission-Fragment Drive", "T4", "PR",
  ["pr17", "pw08"], 6000, [("FissionSystems", 2500)],
  grants=["part:FFR-43"], spec=True,
  anchor="Werka dusty-plasma FF rocket, NIAC 2012")
n("pr22_fusion_torch", "Fusion Torch Drive", "T4", "PR",
  ["pw12"], 9000, [("FissionSystems", 3000)],
  unlocks=["core:engine_torch_d1"], grants=["part:DFD-5", "blueprint:PULSE-D"],
  era=True, spec=True, anchor="Princeton DFD; Project Daedalus 1978")

# ---- Guidance, Nav & Comms (GN) — 8 --------------------------------------
n("gn00_baseline_gnc", "Baseline GNC", "T0", "GN", [], 0, [],
  grants=["prog:node_execute", "prog:ascent_guidance", "prog:circularize",
          "prog:hohmann_planner"],
  anchor="Saturn V IGM; flown upper-stage guidance")
n("gn01_rendezvous_prox_ops", "Rendezvous & Proximity Ops", "T1", "GN",
  ["gn00"], 100, [("Avionics", 80)],
  grants=["prog:rendezvous_sequencer", "prog:autodock",
          "prog:stationkeeping", "prog:window_finder"],
  anchor="Kurs, ATV, Dragon autodock")
n("gn02_powered_descent", "Powered Descent Guidance", "T1", "GN",
  ["gn00"], 130, [("Avionics", 100)],
  grants=["prog:vacuum_landing"], anchor="Apollo P63-P66; Falcon 9 landing")
n("gn03_relay_constellations", "Relay Constellations", "T1", "GN",
  ["gn00"], 160, [],
  grants=["part:relay_sat", "ops:comms_relay"],
  anchor="TDRS; Mars relay network")
n("gn04_atmospheric_flight", "Atmospheric Flight Guidance", "T2", "GN",
  ["gn02"], 450, [("AeroFlight", 300)],
  grants=["prog:edl_guidance", "prog:aerocapture", "part:aeroshells"],
  anchor="Viking->Mars 2020 EDL; aerocapture studies")
n("gn05_low_thrust_planning", "Low-Thrust Mission Planning", "T2", "GN",
  [("pr06", "pr07")], 400, [("EPThrusters", 200)],
  grants=["prog:low_thrust_spiral"], anchor="Edelbaum; SMART-1, Dawn ops")
n("gn06_optical_comms", "Optical Deep-Space Comms", "T2", "GN",
  ["gn03"], 500, [("Avionics", 200)],
  grants=["part:laser_terminal", "ops:comms_x10"],
  anchor="NASA DSOC on Psyche")
n("gn07_tour_planning", "Multi-Flyby Tour Planning", "T3", "GN",
  ["gn05"], 1100, [("Avionics", 400)],
  grants=["prog:tour_planner"], anchor="Galileo/Cassini tour design")

# ---- Power & Thermal (PW) — 13 --------------------------------------------
n("pw00_baseline_power", "Baseline Power", "T0", "PW", [], 0, [],
  grants=["part:pv_rigid", "part:liion_pack", "part:mmrtg",
          "part:radiator_bodymount"],
  anchor="ISS arrays; MMRTG")
n("pw01_rollout_arrays", "Roll-Out Arrays & Concentrators", "T1", "PW",
  ["pw00"], 80, [("SolarPower", 100)],
  grants=["part:ROSA", "part:SOL-CONC"], anchor="ISS iROSA; CSP heliostats")
n("pw02_regen_fuel_cells", "Regenerative Fuel Cells", "T1", "PW",
  ["pw00"], 120, [("EnergyStorage", 100)],
  grants=["part:RFC"], anchor="Gemini/Shuttle fuel cells; lunar-night RFC")
n("pw03_high_cap_radiators", "High-Capacity Radiators", "T1", "PW",
  ["pw00"], 100, [("ThermalControl", 100)],
  grants=["part:radiator_deployable"], anchor="ISS EATCS ~70 kW")
n("pw04_kilopower", "Kilopower Fission", "T2", "PW",
  ["pw00"], 450, [("FissionSystems", 200)],
  grants=["part:NUK-KP1", "part:NUK-KP10"], anchor="KRUSTY test, March 2018")
n("pw05_fission_surface", "Fission Surface Power", "T2", "PW",
  ["pw04"], 800, [("FissionSystems", 500)],
  grants=["module:reactor_100"], era=True,
  anchor="NASA FSP program (40 kWe contracts 2022)")
n("pw06_adv_pv_dust", "Advanced PV & Dust Mitigation", "T2", "PW",
  ["pw01"], 350, [("SolarPower", 250)],
  grants=["part:SOL-BLK", "part:SOL-EDS"],
  anchor="NREL 39.2% cell; EDS on Blue Ghost M1 (2025)")
n("pw07_thermal_storage", "Thermal Energy Storage", "T2", "PW",
  ["pw03"], 300, [("ThermalControl", 200)],
  grants=["part:thermal_battery"], anchor="CSP storage; lunar TES studies")
n("pw08_megawatt_reactors", "Megawatt Space Reactors", "T3", "PW",
  ["pw05", "pw09"], 1800, [("FissionSystems", 1800)],
  grants=["part:NEP-core"], anchor="SP-100; Prometheus/JIMO")
n("pw09_brayton", "Closed Brayton Conversion", "T3", "PW",
  ["pw05"], 1200, [("ThermalControl", 900)],
  grants=["part:brayton_unit", "part:NUK-MSR"],
  anchor="NASA BRU tests; ORNL MSRE")
n("pw10_radioisotope_prod", "Radioisotope Production", "T3", "PW",
  ["pw05", "is09b"], 1000, [("FissionSystems", 1000)],
  grants=["recipe:RX-19"], anchor="Oak Ridge Pu-238 restart")
n("pw11_power_beaming", "Power Beaming", "T3", "PW",
  ["pw08", "gn06"], 1400, [("SolarPower", 600)],
  grants=["part:laser_power_link"], anchor="NASA Watts on the Moon")
n("pw12_fusion_plant", "Fusion Power Plant", "T4", "PW",
  ["pw08", "is20"], 10000, [("FissionSystems", 4000)],
  grants=["part:fusion_plant"], spec=True,
  anchor="Kulcinski D-He3 concepts; SPARC/ARC lineage")

# ---- ISRU & Resources (IS) — 23 -------------------------------------------
n("is00_orbital_prospecting", "Orbital Prospecting", "T0", "IS", [], 0, [],
  grants=["part:orbital_spectrometer", "recipe:RX-05-demo"],
  anchor="LRO/LCROSS/M3; MOXIE 122 g O2")
n("is01_surface_survey_coring", "Surface Survey & Coring", "T1", "IS",
  ["is00"], 90, [],
  grants=["part:core_drill", "part:thermal_ice_corer", "part:k2_survey"],
  anchor="Honeybee TRIDENT (PRIME-1)")
n("is02_regolith_excavation", "Regolith Excavation", "T1", "IS",
  ["is01"], 110, [],
  grants=["part:drum_excavator"], anchor="NASA KSC RASSOR")
n("is03_water_electrolysis", "Water Electrolysis Plant", "T1", "IS",
  ["is00"], 130, [("ECLSS-PhysChem", 100)],
  grants=["recipe:RX-01", "ops:lox_lh2_liquefaction"],
  anchor="ISS OGA; industrial PEM")
n("is04_sabatier", "Sabatier Methanation", "T1", "IS",
  ["is03"], 150, [("ECLSS-PhysChem", 120)],
  grants=["recipe:RX-03", "ops:lch4_liquefaction", "ops:vapor_return"],
  anchor="ISS Sabatier; Mars Direct ISPP")
n("is05_polar_ice_mining", "Polar Ice Mining", "T2", "IS",
  ["is02"], 550, [("MiningMachines", 300)], dsc=["dsc01"],
  grants=["part:bucket_wheel", "part:sublimation_tent", "part:rodwell"],
  era=True, anchor="LCROSS Cabeus: 5.6 +/- 2.9 wt% H2O")
n("is06_mars_atmo_processing", "Mars Atmosphere Processing", "T2", "IS",
  ["is04"], 600, [("ISRU-Chem", 250)], dsc=["dsc04"],
  grants=["part:mars_co2_intake", "recipe:RX-04", "recipe:RX-05"],
  anchor="MOXIE scale-up; DRA 5.0")
n("is07_beneficiation", "Beneficiation & Ore Dressing", "T2", "IS",
  ["is02"], 400, [("MiningMachines", 250)],
  grants=["part:beneficiation_separator"],
  anchor="lunar ilmenite concentration studies")
n("is08_ilmenite_reduction", "Ilmenite Hydrogen Reduction", "T2", "IS",
  ["is07"], 650, [("ISRU-Chem", 400)],
  grants=["recipe:RX-07"], anchor="Apollo/Artemis lunar-oxygen baseline")
n("is09a_gas_volatile_chem", "Gas & Volatile Chemistry", "T2", "IS",
  ["is04"], 500, [("ISRU-Chem", 300)],
  grants=["recipe:RX-13", "recipe:RX-14", "recipe:RX-15"],
  anchor="air-separation industry; Haber-Bosch")
n("is09b_materials_chem", "Materials Chemistry", "T2", "IS",
  ["is07"], 550, [("ISRU-Chem", 300)],
  grants=["recipe:RX-06", "recipe:RX-12", "recipe:RX-17"],
  anchor="HYBRIT H2-DRI; basalt fiber")
n("is10_nea_volatile_capture", "NEA Volatile Capture", "T2", "IS",
  ["is01"], 500, [("MiningMachines", 200)], dsc=["dsc15"],
  grants=["part:capture_bag", "part:volatile_oven"],
  anchor="NASA ARM; Hayabusa2/OSIRIS-REx")
n("is11_deep_core_drilling", "Deep Core Drilling", "T2", "IS",
  ["is01"], 450, [("MiningMachines", 300)],
  grants=["part:deep_core_rig"], anchor="wireline coring; Mars deep-drill")
n("is12_carbothermal", "Carbothermal Reduction", "T2", "IS",
  ["is08"], 700, [("ISRU-Chem", 500)],
  grants=["recipe:RX-08"], anchor="NASA/Sierra Space CaRD (2023)")
n("is13_molten_regolith", "Molten Regolith Electrolysis", "T3", "IS",
  ["is12", "pw05"], 1600, [("ISRU-Chem", 800)],
  grants=["recipe:RX-09"], anchor="MIT MRE (Sadoway/Schreiner)")
n("is14_carbonyl_refining", "Carbonyl Metal Refining", "T3", "IS",
  ["is10"], 1400, [("ISRU-Chem", 700)], dsc=["dsc16"],
  grants=["recipe:RX-10"], anchor="INCO Clydach process; Mining the Sky")
n("is15_light_metals", "Light-Metal Production", "T3", "IS",
  ["is13"], 1800, [("ISRU-Chem", 1000)],
  grants=["recipe:RX-11", "recipe:RX-18"],
  anchor="NASA SP-509; FFC Cambridge")
n("is16_solar_silicon", "Solar-Grade Silicon", "T3", "IS",
  ["is13"], 1500, [("ISRU-Chem", 800)],
  grants=["recipe:RX-16"], anchor="Siemens trichlorosilane process")
n("is17_strip_optical_mining", "Strip & Optical Mining", "T3", "IS",
  [("is05", "is10")], 1300, [("MiningMachines", 900)],
  grants=["part:strip_miner", "part:optical_miner"],
  anchor="TransAstra Apis NIAC")
n("is18_venus_aerostat_intake", "Venus Aerostat Intake", "T3", "IS",
  ["hb05"], 1700, [("ISRU-Chem", 600)], dsc=["dsc08"],
  grants=["part:venus_intake"], anchor="NASA HAVOC; 96.5% CO2 / 3.5% N2")
n("is19_titan_hydrocarbons", "Titan Hydrocarbon Processing", "T3", "IS",
  ["is09a"], 1600, [("ISRU-Chem", 600)], dsc=["dsc13"],
  grants=["part:titan_sea_pump", "part:titan_intake"],
  anchor="Cassini/Huygens lakes; TiME")
n("is20_he3_kiln", "He3 Volatile Kiln", "T4", "IS",
  ["is17"], 7000, [("MiningMachines", 2500)], dsc=["dsc02"],
  grants=["part:he3_kiln"], spec=True,
  anchor="Wittenberg/Kulcinski/Schmitt: 5-20 ppb He3")
n("is21_gas_giant_scoop", "Gas-Giant Atmospheric Scoop", "T4", "IS",
  ["pr22"], 8000, [("AeroFlight", 2000)], dsc=["dsc18"],
  grants=["part:atmo_scoop"], spec=True,
  anchor="Daedalus aerostat He3 concept")

# ---- Industry & Automation (IN) — 15 --------------------------------------
n("in00_earth_supply_chain", "Earth Supply Chain", "T0", "IN", [], 0, [],
  grants=["module:polymer_printer", "ops:auto_cargo_dock", "ops:eva_a0"],
  anchor="ISS commercial resupply lineage")
n("in01_workshop", "Pressurized Workshop & Machine Shop", "T1", "IN",
  ["sh01"], 100, [("FabricationMachines", 80)],
  grants=["module:machine_shop", "module:workshop"],
  anchor="ISS maintenance work area")
n("in02_foundry_chem_plant", "Foundry & Chemical Plant", "T1", "IN",
  ["in01"], 140, [],
  grants=["module:foundry", "module:chem_plant"],
  anchor="terrestrial small-batch industry")
n("in03_electronics_assembly", "Electronics Assembly", "T1", "IN",
  ["in01"], 180, [],
  grants=["module:electronics_line"], anchor="SMT lines; in-space mfg pilots")
n("in04_robotic_manipulation", "Robotic Manipulation (A1)", "T1", "IN",
  ["gn01"], 150, [("RoboticsAutonomy", 100)],
  grants=["part:berthing_arm", "part:dexterous_unit"],
  anchor="Canadarm2 / Dextre")
n("in05_orbital_assembly_waam", "Orbital Assembly & WAAM", "T2", "IN",
  ["in01", "sh01"], 500, [("FabricationMachines", 350)],
  grants=["module:waam_cell", "module:assembly_hall"],
  anchor="wire-arc additive; OSAM/Archinaut")
n("in06_orbital_dry_dock", "Orbital Dry Dock", "T2", "IN",
  ["in05"], 700, [("FabricationMachines", 500)],
  grants=["module:dry_dock"], anchor="ISS truss assembly, scaled")
n("in07_teleop_robots", "Teleoperated Worker Robots (A2)", "T2", "IN",
  ["in04", "gn03"], 550, [("RoboticsAutonomy", 400)],
  grants=["part:worker_robot", "ops:teleop_a2"],
  anchor="ESA Analog-1 / METERON")
n("in08_auto_haulage", "Automated Haulage Routes", "T2", "IN",
  ["vh02", "in07"], 400, [("SurfaceMobility", 250)],
  grants=["ops:auto_haul_routes"], anchor="Pilbara autonomous haul trucks")
n("in09_supervised_autonomy", "Supervised Autonomy (A3)", "T3", "IN",
  ["in07"], 1400, [("RoboticsAutonomy", 1000)],
  grants=["ops:autonomy_a3"], anchor="Mars rover AutoNav lineage")
n("in10_autonomous_factory", "Autonomous Factory Complex", "T3", "IN",
  ["in09"], 2200, [("RoboticsAutonomy", 1600), ("FabricationMachines", 800)],
  grants=["module:auto_factory"], era=True,
  anchor="NASA 1980 AASM study (CP-2255)")
n("in11_wafer_fab", "Wafer Fab", "T3", "IN",
  ["is16", "in09"], 2500, [("FabricationMachines", 1200)],
  grants=["module:wafer_fab"], era=True,
  anchor="trailing-edge rad-hard fab (90-180 nm)")
n("in12_mass_driver", "Mass Driver & Catcher", "T3", "IN",
  ["pw05", "in05"], 2000, [("FabricationMachines", 800)],
  grants=["module:mass_driver", "module:catcher", "module:pelletizer"],
  era=True, anchor="O'Neill & Kolm; NASA SP-428")
n("in13_truss_fabrication", "In-Space Truss Fabrication", "T3", "IN",
  ["in06"], 1200, [("FabricationMachines", 700)],
  grants=["part:trusselator"], anchor="SpiderFab / Trusselator (NIAC)")
n("in14_industry_seed", "Self-Expanding Industry Seed", "T4", "IN",
  ["in10", "in11"], 9000, [("RoboticsAutonomy", 3500)],
  grants=["module:industry_seed"], spec=True,
  anchor="AASM self-replicating factory; Freitas")

# ---- Ships, Stations & Logistics (SH) — 10 --------------------------------
n("sh00_crew_capsule_ops", "Crew Capsule Operations", "T0", "SH", [], 0, [],
  grants=["part:crew_capsule", "part:cargo_capsule", "part:PAD-1", "part:PAD-2"],
  anchor="Dragon 2 / Soyuz / Starliner")
n("sh01_station_modules", "Station Modules", "T1", "SH",
  ["gn01"], 120, [("PressureStructures", 100)],
  unlocks=["core:hab_castor"], grants=["part:docking_node", "part:PAD-3"],
  anchor="ISS USOS modules")
n("sh02_inflatable_modules", "Inflatable Modules", "T1", "SH",
  ["sh01"], 200, [("PressureStructures", 150)],
  unlocks=["core:hab_pollux"], grants=["ops:inflatable_x3"],
  anchor="BEAM; B330; Sierra LIFE")
n("sh03_pallet_tug", "Pallet Tug", "T1", "SH",
  ["gn01", "pr06"], 150, [],
  grants=["part:pallet_tug"], anchor="space-tug studies; MEV docking")
n("sh04_pelican_lift_loop", "Pelican Lander Lift Loop", "T2", "SH",
  ["pr13", "is05"], 600, [],
  grants=["ops:pelican_loop"], anchor="lunar single-stage lander studies")
n("sh05_drayage_sep", "Drayage SEP Freighter", "T2", "SH",
  ["pr07", "gn05"], 650, [("EPThrusters", 300)],
  grants=["class:drayage_freighter"], anchor="Gateway PPE-derived cargo SEP")
n("sh06_longhaul_ntr", "Longhaul NTR Freighter", "T2", "SH",
  ["pr09", "in05"], 900, [],
  grants=["class:longhaul_freighter"],
  anchor="Borowski NTR cargo architectures")
n("sh07_cycler", "Cycler Architecture", "T3", "SH",
  ["gn07", "hb06"], 1300, [],
  grants=["ops:cycler", "prog:cycler_planner"],
  anchor="Aldrin Earth-Mars cycler (1985)")
n("sh08_skyhook", "Momentum-Exchange Skyhook", "T4", "SH",
  ["in12", "in13"], 6500, [("FabricationMachines", 2000)],
  grants=["module:skyhook"], spec=True, anchor="HASTOL (2000); MXER tether")
n("sh09_interstellar_precursor", "Interstellar Precursor Program", "T4", "SH",
  [("pr21", "pr22"), "in14"], 12000, [],
  unlocks=["core:probe_longshot"], grants=["blueprint:precursor"],
  spec=True, anchor="TAU study 1987; JHU/APL Interstellar Probe 2021")

# ---- Habitats & Bases (HB) — 9 --------------------------------------------
n("hb01_surface_hab_landers", "Surface Habitat Landers", "T1", "HB",
  ["sh01", "gn02"], 300, [("PressureStructures", 200)],
  grants=["module:surface_hab", "module:airlock"],
  anchor="Artemis surface habitat studies")
n("hb02_regolith_shielding", "Regolith Shielding", "T2", "HB",
  ["hb01", "is02"], 350, [],
  grants=["ops:berm_shielding"], anchor="GCR/SPE regolith shielding studies")
n("hb03_regolith_printing", "Regolith Construction Printing", "T2", "HB",
  ["hb02", "in07"], 600, [("FabricationMachines", 350)],
  grants=["module:regolith_printer", "ops:landing_pads"],
  anchor="ICON Project Olympus; ESA D-Shape")
n("hb04_lava_tube_outfitting", "Lava-Tube Outfitting", "T3", "HB",
  ["hb03"], 1300, [], dsc=["dsc03"],
  grants=["site:lava_tube"], anchor="Marius Hills skylight; Horvath 2022")
n("hb05_venus_aerostat_hab", "Venus Aerostat Habitat", "T3", "HB",
  ["sh02", "gn04"], 2000,
  [("PressureStructures", 500), ("AeroFlight", 400)], dsc=["dsc08"],
  unlocks=["core:gondola_havoc"], grants=["ops:crewed_aerostat"],
  anchor="NASA Langley HAVOC (2015); crewed tier T3 per DECISIONS A6")
n("hb06_spin_centrifuge", "Spin-Gravity Centrifuge", "T3", "HB",
  ["sh01"], 900, [("PressureStructures", 400)],
  grants=["part:centrifuge_module"],
  anchor="Nautilus-X; Gemini 11 tether spin")
n("hb07_titan_outpost", "Titan Surface Outpost", "T3", "HB",
  ["pw04"], 1500, [], dsc=["dsc13"],
  grants=["module:titan_base_kit"],
  anchor="NASA Glenn Titan studies; Huygens")
n("hb09_mercury_terminator", "Mercury Terminator Operations", "T3", "HB",
  ["vh04", "pw04"], 1500, [("SurfaceMobility", 800)],
  grants=["module:mercury_crawler", "site:mercury_terminator"],
  anchor="JPL terminator-rover studies; MESSENGER polar ice")
n("hb08_rotating_settlement", "Rotating Settlement", "T4", "HB",
  ["hb06", "in12", "is15"], 4500, [("PressureStructures", 1500)],
  grants=["module:spin_settlement"], spec=True,
  anchor="NASA Ames/Stanford Torus (1975)")

# ---- Life Support & Crew (LS) — 12 -----------------------------------------
n("ls00_open_loop", "Open-Loop Life Support", "T0", "LS", [], 0, [],
  grants=["part:lioh_scrubber", "part:iva_suit", "part:VEG-1"],
  anchor="Apollo/Dragon ECLSS; ISS Veggie")
n("ls01_regen_eclss", "Regenerative ECLSS", "T1", "LS",
  ["ls00"], 200, [("ECLSS-PhysChem", 150)],
  grants=["part:co2_sorbent", "part:oga", "part:wpa", "part:sabatier_eclss"],
  anchor="ISS ECLSS 98% water recovery")
n("ls02_crop_modules", "Crop Production Modules", "T1", "LS",
  ["ls00"], 150, [("ECLSS-Bio", 80)],
  grants=["module:salad_rack"], anchor="ISS Veggie / Advanced Plant Habitat")
n("ls03_surface_eva_suits", "Surface EVA Suits", "T1", "LS",
  ["ls00"], 180, [("PressureStructures", 100)],
  grants=["part:surface_eva_suit"], anchor="NASA xEMU / Axiom AxEMU")
n("ls04_greenhouse", "Greenhouse Food Production", "T2", "LS",
  ["ls02"], 500, [("ECLSS-Bio", 300)],
  grants=["module:ls_garden"], anchor="EDEN ISS Antarctic greenhouse")
n("ls05_radiation_planning", "Radiation Protection Planning", "T2", "LS",
  ["ls01"], 400, [],
  grants=["part:storm_shelter", "prog:dose_planner"],
  anchor="NASA exposure limits; SPE shelters")
n("ls06_water_waste_loops", "Advanced Water & Waste Loops", "T2", "LS",
  ["ls01"], 450, [("ECLSS-PhysChem", 350)],
  grants=["part:brine_recovery", "part:waste_pyrolysis"],
  anchor="ISS Brine Processor Assembly")
n("ls07_closed_loop_eclss", "Closed-Loop Bioregenerative ECLSS", "T3", "LS",
  ["ls04", "ls06"], 2400, [("ECLSS-Bio", 1500)],
  grants=["module:ls_green", "module:hb_grn", "ops:eclss_closed"],
  era=True, anchor="MELiSSA; BIOS-3; Lunar Palace 365")
n("ls08_crew_health", "Long-Duration Crew Health", "T2", "LS",
  ["ls01"], 350, [],
  grants=["module:med_bay", "part:exercise_rig"],
  anchor="ISS medical ops; ARED")
n("ls09_gravity_biology_1", "Partial-Gravity Biology I", "T2", "LS",
  ["ls08"], 400, [("ECLSS-Bio", 200)],
  grants=["module:animal_centrifuge"],
  anchor="Bion/Foton; ISS Rodent Research (DECISIONS C19)")
n("ls10_gravity_biology_2", "Partial-Gravity Biology II", "T3", "LS",
  ["ls09", "hb06"], 1200, [("ECLSS-Bio", 600)],
  grants=["ops:mammalian_trials"],
  anchor="multi-generation spin studies (DECISIONS C19)")
n("ls11_reproduction_protocols", "Human Reproduction Protocols", "T4", "LS",
  ["ls10"], 5000, [],
  grants=["ops:demographic_pillar"], spec=True,
  anchor="honest speculation - no human off-Earth data exists (C19)")

# ---- Vehicles (VH) — 11 ----------------------------------------------------
n("vh00_teleop_rovers", "Teleoperated Rovers", "T0", "VH", [], 0, [],
  grants=["part:robotic_rover", "part:teleop_arm", "part:instrument_mount"],
  anchor="Curiosity / Perseverance class")
n("vh01_open_rover", "Crewed Unpressurized Rover", "T1", "VH",
  ["ls03"], 130, [("SurfaceMobility", 80)],
  grants=["part:open_rover"], anchor="Apollo LRV; Artemis LTV")
n("vh02_robotic_haulers", "Robotic Haulers", "T1", "VH",
  ["vh00"], 200, [("SurfaceMobility", 150)],
  grants=["part:hauler_chassis"], anchor="autonomous haul trucks")
n("vh03_ballistic_hoppers", "Ballistic Hoppers", "T1", "VH",
  ["gn02"], 250, [],
  grants=["part:hopper"], anchor="IM Micro-Nova hopper")
n("vh04_pressurized_rover", "Pressurized Rover", "T2", "VH",
  ["vh01", "ls01"], 550, [("SurfaceMobility", 350)],
  grants=["part:pressurized_rover"],
  anchor="JAXA/Toyota Lunar Cruiser; NASA SEV")
n("vh05_mars_rotorcraft", "Mars Rotorcraft", "T2", "VH",
  ["gn04"], 480, [("AeroFlight", 200)],
  grants=["part:mars_rotorcraft"], anchor="Ingenuity: 72 flights")
n("vh09_venus_platforms", "Venus Atmospheric Platforms", "T2", "VH",
  ["gn04"], 700, [("AeroFlight", 500)], dsc=["dsc08"],
  grants=["part:venus_balloon", "part:cloud_drone"],
  anchor="Soviet VEGA balloons (1985); robotic T2 per DECISIONS A6")
n("vh06_titan_rotorcraft", "Titan Rotorcraft", "T3", "VH",
  ["vh05", "sc03"], 1300, [("AeroFlight", 600)],
  grants=["part:titan_rotorcraft"], anchor="Dragonfly (launch 2028)")
n("vh07_titan_submarine", "Titan Submarine", "T3", "VH",
  [], 1800, [("AeroFlight", 800)], dsc=["dsc13"],
  grants=["part:titan_submarine"],
  anchor="NASA Glenn COMPASS Titan Sub (NIAC)")
n("vh08_cryobot", "Ice-Penetrating Cryobot", "T3", "VH",
  ["pw04"], 2200, [("AeroFlight", 800)], dsc=["dsc10"],
  grants=["part:cryobot"], anchor="NASA SESAME; Honeybee SLUSH")
n("vh10_venus_surface", "Venus Surface Systems", "T3", "VH",
  [], 1400, [("Avionics", 300)], dsc=["dsc08"],
  grants=["part:venus_surface_station"],
  anchor="NASA Glenn LLISSE; SiC electronics, 737 K")

# ---- Science Instruments & Labs (SC) — 8 -----------------------------------
n("sc00_survey_instruments_1", "Survey Instruments I", "T0", "SC", [], 0, [],
  grants=["part:survey_pkg_1"], anchor="LRO instrument suite")
n("sc01_sample_return_capsules", "Sample Return Capsules", "T1", "SC",
  ["gn00"], 120, [],
  grants=["part:SRC-46"], anchor="Stardust / OSIRIS-REx SRC")
n("sc02_field_laboratory", "Field Laboratory", "T1", "SC",
  ["ls00"], 200, [],
  grants=["part:GL-1", "module:FL-2"], anchor="ISS MSG; MSL SAM")
n("sc03_survey_instruments_2", "Survey Instruments II", "T2", "SC",
  ["sc00"], 350, [],
  grants=["part:survey_pkg_2"], anchor="RIMFAX; LRO LEND")
n("sc04_orbital_laboratory", "Orbital Laboratory", "T2", "SC",
  ["sh01", "sc02"], 600, [],
  grants=["module:OL-12"], anchor="ISS Destiny/Columbus; MSR facility")
n("sc05_observatories", "Deep-Space Observatories", "T2", "SC",
  ["sc00", "gn03"], 700, [],
  grants=["part:observatory_platform"], anchor="NEO Surveyor")
n("sc06_cryo_sample_chain", "Cryogenic Sample Chain", "T2", "SC",
  ["sc01"], 400, [],
  grants=["part:cryo_vault", "part:SRC-300"],
  anchor="MSR / lunar-PSR cryo-curation")
n("sc07_astrobiology_suite", "Astrobiology Suite", "T3", "SC",
  ["sc04"], 1500, [],
  grants=["part:astrobiology_pkg", "ops:organics_x1_5"],
  anchor="Europa Lander SDT; MOMA")

# ---- Discoveries (18) -------------------------------------------------------
# (slug, name, sci, staged, gates[codes], discounts[(code,frac)],
#  trigger_kind, body_hint, requirement text)
D = [
    ("dsc01_lunar_psr_ice", "Lunar PSR Ice Ground Truth", 300, False,
     ["is05"], [("is03", 0.20)], "ice_core_psr", "core:moon",
     "Take a >= 1 m ice core inside a permanently shadowed lunar crater "
     "(Thermal Ice Corer)."),
    ("dsc02_mare_volatile_assay", "Mare Volatile Assay", 400, False,
     ["is20"], [], "mare_assay_x3", "core:moon",
     "Deep cores + Volatile Oven assay at 3 distinct lunar mare sites."),
    ("dsc03_lava_tube_survey", "Lava-Tube Interior Survey", 350, False,
     ["hb04"], [("hb03", 0.15)], "skylight_descent", "core:moon",
     "Descend a skylight anomaly with a lidar-equipped hopper or rover."),
    ("dsc04_mars_environment", "Mars Environment Characterization", 300, False,
     ["is06"], [("vh05", 0.20)], "surface_met_90sol", "core:mars",
     "90 sols of surface meteorology and dust data from one Mars station."),
    ("dsc05_mars_subsurface_ice", "Mars Subsurface Ice & Brines", 500, False,
     [], [("hb03", 0.15)], "gpr_deep_core", "core:mars",
     "GPR survey plus a 10 m core at a mid-latitude Mars site."),
    ("dsc06_phobos_deimos_regolith", "Phobos/Deimos Regolith", 350, False,
     [], [("sh04", 0.20)], "moonlet_sample", "core:phobos",
     "Land on Phobos or Deimos and return or lab-analyze a sample."),
    ("dsc07_comet_nucleus_sample", "Comet Nucleus Sample", 600, False,
     [], [("is10", 0.30)], "comet_sample", "core:halley",
     "Rendezvous with an active comet and take a nucleus sample."),
    ("dsc08_venus_cloud_chemistry", "Venus Cloud-Layer Chemistry", 600, False,
     ["hb05", "vh09", "vh10", "is18"], [], "balloon_30d", "core:venus",
     "30 days of balloon or probe data in the 50-56 km Venus cloud layer."),
    ("dsc09_venus_surface_mineralogy", "Venus Surface Mineralogy", 700, False,
     [], [("vh10", 0.25)], "venus_surface_survive", "core:venus",
     "A surface station surviving >= 60 minutes (or an LLISSE-class 60 days)."),
    ("dsc10_europa_plume_volatiles", "Europa Plume & Exosphere Volatiles", 800,
     False, ["vh08"], [], "plume_flythrough", "core:europa",
     "Low-orbit plume flythrough capture at <= 3 km/s relative."),
    ("dsc11_europa_ocean_water", "Europa Ocean Water", 2500, True,
     [], [], "cryobot_ocean", "core:europa",
     "A cryobot reaches the sub-ice ocean; melt sample analyzed. "
     "Ambiguous-organics arc I: chemistry, never organisms."),
    ("dsc12_enceladus_plume", "Enceladus Plume Sampling", 900, False,
     [], [("vh08", 0.30)], "plume_flythrough", "core:enceladus",
     "South-polar plume flythrough capture."),
    ("dsc13_titan_lake_composition", "Titan Lake Composition", 800, True,
     ["vh07", "is19", "hb07"], [], "lake_sample", "core:titan",
     "A lake-surface sample by lander or rotorcraft."),
    ("dsc14_titan_sea_floor", "Titan Sea Floor Survey", 1200, True,
     [], [], "submarine_sonar", "core:titan",
     "Submarine sonar map plus a sediment sample. "
     "Ambiguous-organics arc II: chemistry, never organisms."),
    ("dsc15_c_type_nea_assay", "C-Type NEA Assay", 350, False,
     ["is10"], [], "nea_samples_x3", "core:bennu",
     "Rendezvous and take 3 samples from one C-type near-Earth asteroid."),
    ("dsc16_m_type_metal_assay", "M-Type Metal Assay", 450, False,
     ["is14"], [], "mtype_sample", "core:psyche",
     "Rendezvous and sample an M-type metallic body."),
    ("dsc17_jovian_radiation_survey", "Jovian Radiation Survey", 500, False,
     [], [("vh08", 0.20)], "dosimetry_4orbits", "core:jupiter",
     "Orbiter dosimetry across >= 4 Jupiter-system orbits; gates crewed "
     "Jupiter operations planning."),
    ("dsc18_saturn_atmosphere_probe", "Saturn Atmosphere Probe", 700, False,
     ["is21"], [], "entry_probe_10bar", "core:saturn",
     "Entry-probe telemetry to >= 1,000 kPa (10 bar) depth."),
]


def _full_id(code_or_slug: str) -> str:
    """pr09 -> core:tech_pr09_ntr (codes are unique node prefixes)."""
    for node in N:
        if node["slug"] == code_or_slug or node["slug"].split("_")[0] == code_or_slug:
            return "core:tech_" + node["slug"]
    raise KeyError(code_or_slug)


def _dsc_id(code: str) -> str:
    for slug, *_ in D:
        if slug.startswith(code):
            return "core:" + slug
    raise KeyError(code)


def _toml_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _emit_node(node: dict) -> str:
    lines = ["# generated by tools/gen_tech.py - edit the generator, not this file"]
    lines.append(f'id      = "core:tech_{node["slug"]}"')
    lines.append(f'tier    = "{node["tier"]}"')
    lines.append(f'name    = {_toml_str(node["name"])}')
    lines.append(f'category = "{node["branch"]}"')
    pres = []
    for p in node["prereqs"]:
        if isinstance(p, tuple):
            pres.append("[" + ", ".join(f'"{_full_id(c)}"' for c in p) + "]")
        else:
            pres.append(f'"{_full_id(p)}"')
    lines.append("prereqs = [" + ", ".join(pres) + "]")
    lines.append("unlocks = [" + ", ".join(f'"{u}"' for u in node["unlocks"]) + "]")
    if node["grants"]:
        lines.append("grants  = [" + ", ".join(f'"{g}"' for g in node["grants"]) + "]")
    lines.append(f'cost_sci = {float(node["sci"])}')
    if node["ed"]:
        ed = ", ".join("{ family = \"%s\", value = %s }" % (f, float(v))
                       for f, v in node["ed"])
        lines.append(f"ed_thresholds = [{ed}]")
    if node["dsc"]:
        lines.append("discovery_prereqs = ["
                     + ", ".join(f'"{_dsc_id(d)}"' for d in node["dsc"]) + "]")
    if node["era"]:
        lines.append("era = true")
    if node["spec"]:
        lines.append("speculative = true")
    if node["anchor"]:
        lines.append(f'anchor = {_toml_str(node["anchor"])}')
    return "\n".join(lines) + "\n"


def _emit_dsc(slug, name, sci, staged, gates, discounts, kind, body, req) -> str:
    lines = ["# generated by tools/gen_tech.py - edit the generator, not this file"]
    lines.append(f'id   = "core:{slug}"')
    lines.append(f"name = {_toml_str(name)}")
    lines.append(f"sci  = {float(sci)}")
    lines.append(f"staged = {'true' if staged else 'false'}")
    lines.append("gates = [" + ", ".join(f'"{_full_id(g)}"' for g in gates) + "]")
    if discounts:
        ds = ", ".join("{ node = \"%s\", frac = %s }" % (_full_id(c), float(f))
                       for c, f in discounts)
        lines.append(f"discounts = [{ds}]")
    lines.append(f'trigger_kind = "{kind}"')
    lines.append(f'body = "{body}"')
    lines.append(f"requirement = {_toml_str(req)}")
    return "\n".join(lines) + "\n"


def main() -> None:
    # --- integrity asserts against the bible's economy targets (11 §1) ---
    assert len(N) == 132, len(N)
    branch_counts: dict[str, int] = {}
    tier_counts: dict[str, int] = {}
    tier_sci: dict[str, float] = {}
    for node in N:
        branch_counts[node["branch"]] = branch_counts.get(node["branch"], 0) + 1
        tier_counts[node["tier"]] = tier_counts.get(node["tier"], 0) + 1
        tier_sci[node["tier"]] = tier_sci.get(node["tier"], 0.0) + node["sci"]
    assert branch_counts == {"PR": 23, "GN": 8, "PW": 13, "IS": 23, "IN": 15,
                             "SH": 10, "HB": 9, "LS": 12, "VH": 11, "SC": 8}, \
        branch_counts
    assert tier_counts == {"T0": 9, "T1": 34, "T2": 44, "T3": 35, "T4": 10}, \
        tier_counts
    assert tier_sci["T0"] == 0
    assert abs(tier_sci["T1"] - 5_100) <= 600, tier_sci["T1"]
    assert abs(tier_sci["T2"] - 22_300) <= 2_500, tier_sci["T2"]
    assert abs(tier_sci["T3"] - 54_000) <= 5_500, tier_sci["T3"]
    assert tier_sci["T4"] == 77_000, tier_sci["T4"]
    assert sum(1 for x in N if x["era"]) == 10
    assert all(x["spec"] for x in N if x["tier"] == "T4")
    slugs = [x["slug"] for x in N]
    assert len(set(slugs)) == 132
    codes = [s.split("_")[0] for s in slugs]
    assert len(set(codes)) == 132, "node code prefixes must be unique"

    if TECH_DIR.exists():
        shutil.rmtree(TECH_DIR)
    TECH_DIR.mkdir(parents=True)
    for node in N:
        (TECH_DIR / f"{node['slug']}.toml").write_text(
            _emit_node(node), encoding="utf-8", newline="\n")

    if DSC_DIR.exists():
        shutil.rmtree(DSC_DIR)
    DSC_DIR.mkdir(parents=True)
    for row in D:
        (DSC_DIR / f"{row[0]}.toml").write_text(
            _emit_dsc(*row), encoding="utf-8", newline="\n")

    print(f"wrote {len(N)} tech nodes -> {TECH_DIR}")
    print(f"wrote {len(D)} discoveries -> {DSC_DIR}")
    print("tier SCI sums:", {k: round(v) for k, v in sorted(tier_sci.items())})


if __name__ == "__main__":
    main()
