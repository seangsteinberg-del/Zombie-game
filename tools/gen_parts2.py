"""Chunk D1: extend the part catalog to the 06 buildspec's 110 rows.

Layers on top of tools/gen_parts.py (which authors the original 37
engine/tank rows): (1) PATCHES those files additively — catalog_id /
class / size / cost_musd inserted before the first [section], so the 1D
builder and saves keep working; (2) EMITS ~73 brand-new parts with the
06 §5.1 extended schema (structure, solids, NTRs, EP strings, RCS,
power/thermal, habs, spin/dock/assembly, cargo/utility/entry/landing,
Whipple). Idempotent. If gen_parts.py is ever re-run, re-run this after.

Numbers are canon from design/extracts/06-ships-buildspec.md. Run:
    python tools/gen_parts2.py
"""

from __future__ import annotations

import glob
import os

OUT = os.path.join("data", "core", "parts")

# ---- 1. patches for the existing 37 (by part id) ---------------------------
# id: (catalog_id, class, w, h, cost $M)
PATCH = {
    "core:engine_k845":   ("EN-K1",    "ENGINE", 1, 2, 1.5),
    "core:engine_kv981":  ("EN-K1V",   "ENGINE", 1, 3, 2.0),
    "core:engine_h102":   ("EN-H1",    "ENGINE", 2, 4, 12.0),
    "core:engine_oms27":  ("EN-HYP",   "ENGINE", 1, 1, 2.5),
    "core:engine_sps91":  ("EN-HYP-L", "ENGINE", 1, 2, 4.0),
    "core:engine_lnd71":  ("EN-LND",   "ENGINE", 1, 1, 2.0),
    "core:engine_h2280":  ("EN-H2",    "ENGINE", 2, 4, 40.0),
    "core:engine_m2256":  ("EN-M2",    "ENGINE", 2, 3, 2.5),
    "core:engine_mv2530": ("EN-M2V",   "ENGINE", 2, 4, 3.0),
    "core:engine_ml24":   ("EN-ML",    "ENGINE", 1, 1, 1.5),
    "core:engine_m733":   ("EN-M0",    "ENGINE", 2, 3, 2.0),   # A8 Bantam
    "core:engine_mv815":  ("EN-M0V",   "ENGINE", 2, 3, 2.2),   # A8 Bantam vac
    "core:engine_ml111":  ("EN-ML1",   "ENGINE", 1, 2, 1.8),   # A8 lander
    "core:engine_hl67":   ("EN-HL",    "ENGINE", 1, 2, 2.0),
    "core:engine_ntr_k2": ("EN-NTR-S", "ENGINE", 2, 5, 60.0),
    "core:engine_torch_d1": ("EN-FT",  "ENGINE", 3, 8, 2_000.0),
    "core:tank_ml_s":     ("TK-ML-S",  "TANK", 2, 2, 0.4),
    "core:tank_ml_m":     ("TK-ML-M",  "TANK", 2, 4, 0.9),
    "core:tank_ml_l":     ("TK-ML-L",  "TANK", 3, 6, 2.2),
    "core:tank_ml_xl":    ("TK-ML-XL", "TANK", 4, 8, 4.5),
    "core:tank_kl_m":     ("TK-KL-M",  "TANK", 2, 4, 0.8),
    "core:tank_lh2_m":    ("TK-LH2-M", "TANK", 2, 5, 1.5),
    "core:tank_lh2_l":    ("TK-LH2-L", "TANK", 4, 9, 5.0),
    "core:tank_lox_m":    ("TK-LOX-M", "TANK", 2, 3, 0.5),
    "core:tank_ch4_m":    ("TK-CH4-M", "TANK", 2, 3, 0.5),
    "core:tank_hyp_s":    ("TK-HYP-S", "TANK", 1, 2, 0.4),
    "core:tank_xe_s":     ("TK-XE-S",  "TANK", 1, 1, 0.6),
    "core:tank_xe_l":     ("TK-XE-L",  "TANK", 2, 2, 2.0),
    "core:tank_h2o":      ("TK-H2O",   "TANK", 1, 2, 0.2),
    "core:tank_n2":       ("TK-N2",    "TANK", 1, 1, 0.2),
    "core:tank_depot":    ("TK-DEPOT", "TANK", 5, 12, 25.0),
    "core:capsule_vela":  ("HB-CAP2",  "HAB", 2, 3, 25.0),
    "core:hab_castor":    ("HB-RIG-S", "HAB", 3, 5, 70.0),
    "core:hab_pollux":    ("HB-RIG-L", "HAB", 4, 9, 120.0),
    "core:gondola_havoc": ("AR-GON",   "STRUCT", 3, 3, 30.0),
    "core:payload_2t":    ("CG-PAY",   "STRUCT", 2, 2, 0.5),
    "core:probe_longshot": ("UT-PROBE", "ELEC", 1, 1, 8.0),
}
COMMAND_SOURCES = {"core:capsule_vela", "core:probe_longshot"}

# ---- 2. the new rows --------------------------------------------------------
# (file, catalog, name, tier, type, class, w, h, dry_t, cost|"res", extras)


def T(s):
    return s.strip("\n")


NEW = [
    # -- structure (1.1) ------------------------------------------------------
    ("st_g1", "ST-G1", "Girder segment", "T0", "structure", "STRUCT",
     1, 1, 0.08, 0.05, ""),
    ("st_g4", "ST-G4", "Girder beam", "T0", "structure", "STRUCT",
     1, 4, 0.30, 0.15, ""),
    ("st_tr8", "ST-TR8", "Ship spine truss", "T0", "structure", "STRUCT",
     2, 8, 1.4, 0.8, 'axial_kn = 2500\nnodes = "interior"'),
    ("st_keel", "ST-KEEL", "Station keel truss", "T1", "structure",
     "STRUCT", 2, 10, 9.0, 6.0, "axial_kn = 4000\nutility_runs = true"),
    ("st_is3", "ST-IS3", "Interstage 3 m", "T0", "structure", "STRUCT",
     3, 2, 0.40, 0.3, "fairing_interior = [3, 2]"),
    ("st_is_v", "ST-IS-V", "Vented interstage", "T1", "structure",
     "STRUCT", 3, 2, 0.55, 0.5,
     "hot_stage = true\nfairing_interior = [3, 2]"),
    ("st_dc2", "ST-DC2", "Stack decoupler 2 m", "T0", "structure",
     "STRUCT", 2, 1, 0.05, 0.2, "decoupler = true\nsep_ms = 0.3"),
    ("st_dc3", "ST-DC3", "Stack decoupler 3.7 m", "T0", "structure",
     "STRUCT", 3, 1, 0.12, 0.3, "decoupler = true\nsep_ms = 0.3"),
    ("st_rd", "ST-RD", "Radial decoupler", "T0", "structure", "STRUCT",
     1, 1, 0.03, 0.15, "decoupler = true\nradial = true\nsep_ms = 1.0"),
    ("st_fr3", "ST-FR3", "Fairing 3.7 m", "T0", "structure", "STRUCT",
     3, 9, 0.9, 1.2, 'fairing_interior = [3, 8]\nnodes = "interior"'),
    ("st_fr5", "ST-FR5", "Fairing 5 m", "T0", "structure", "STRUCT",
     4, 13, 2.0, 2.5, 'fairing_interior = [4, 12]\nnodes = "interior"'),
    ("st_fin", "ST-FIN", "Grid fin / strake", "T0", "structure", "STRUCT",
     1, 2, 0.15, 0.4, "qalpha_bonus_kpadeg = 40"),
    ("fd_1", "FD-1", "Crossfeed fuel duct", "T1", "structure", "STRUCT",
     1, 2, 0.08, 0.3,
     "crossfeed = true\nflow_cryo_tpm = 1.0\nflow_storable_tpm = 5.0"),
    ("st_bf_g4", "ST-BF-G4", "BasaltFiber beam", "T2", "structure",
     "STRUCT", 1, 4, 0.22, "res", "axial_kn = 1100"),
    ("st_bf_keel", "ST-BF-KEEL", "BasaltFiber keel", "T2", "structure",
     "STRUCT", 2, 10, 6.8, "res", "axial_kn = 3600"),
    # -- solids (1.3) ----------------------------------------------------------
    ("engine_srb", "EN-SRB", "SRM-49 solid booster (GEM 63)", "T0",
     "engine", "ENGINE", 2, 12, 5.2, 6.0, T("""
[engine]
thrust_kN  = 1265.0
isp_s      = 275.0
isp_sl_s   = 245.0
throttle   = [1.0, 1.0]
gimbal_deg = 0.0
solid      = true
solid_prop_t = 44.1
burn_s     = 94.0""")),
    ("engine_kick", "EN-KICK", "SRM-2 kick stage (Star 48B)", "T0",
     "engine", "ENGINE", 1, 2, 0.126, 1.5, T("""
[engine]
thrust_kN  = 66.0
isp_s      = 286.0
isp_sl_s   = 250.0
throttle   = [1.0, 1.0]
gimbal_deg = 0.0
solid      = true
solid_prop_t = 2.011
burn_s     = 87.0""")),
    # -- NTRs (1.4) -------------------------------------------------------------
    ("engine_ntr_l", "EN-NTR-L", "NTR-246 heavy tug core (NERVA XE')",
     "T2", "engine", "ENGINE", 3, 6, 12.5, 90.0, T("""
[engine]
thrust_kN  = 247.0
isp_s      = 850.0
isp_sl_s   = 850.0
throttle   = [0.3, 1.0]
gimbal_deg = 2.0
propellant = { Hydrogen = 1.0 }
ntr = true
restart_lockout_s = 2700""")),
    ("engine_ntr_b", "EN-NTR-B", "NTR-111B bimodal (Borowski)", "T3",
     "engine", "ENGINE", 2, 5, 4.6, 120.0, T("""
[engine]
thrust_kN  = 111.0
isp_s      = 900.0
isp_sl_s   = 900.0
throttle   = [0.3, 1.0]
gimbal_deg = 2.0
propellant = { Hydrogen = 1.0 }
ntr = true
restart_lockout_s = 2700
idle_export_kwe = 25.0""")),
    # -- EP strings + RCS (1.5) ---------------------------------------------------
    ("ep_ion_2", "EN-ION-2", "ION-2 string (NSTAR)", "T0", "engine",
     "ENGINE", 1, 1, 0.030, 2.0, T("""
[engine]
thrust_kN  = 0.000092
isp_s      = 3120.0
isp_sl_s   = 0.0
throttle   = [0.0, 1.0]
gimbal_deg = 10.0
propellant = { Xenon = 1.0 }
ep_power_kwe = 2.3
ep_eta = 0.61""")),
    ("ep_hall_1", "EN-HALL-1", "HALL-1 string (SPT-100)", "T0", "engine",
     "ENGINE", 1, 1, 0.012, 1.0, T("""
[engine]
thrust_kN  = 0.000083
isp_s      = 1600.0
isp_sl_s   = 0.0
throttle   = [0.0, 1.0]
gimbal_deg = 10.0
propellant = { Xenon = 1.0 }
ep_power_kwe = 1.35
ep_eta = 0.48""")),
    ("ep_ion_n", "EN-ION-N", "ION-7 string (NEXT-C)", "T1", "engine",
     "ENGINE", 1, 1, 0.058, 5.0, T("""
[engine]
thrust_kN  = 0.000236
isp_s      = 4190.0
isp_sl_s   = 0.0
throttle   = [0.0, 1.0]
gimbal_deg = 10.0
propellant = { Xenon = 1.0 }
ep_power_kwe = 6.9
ep_eta = 0.70""")),
    ("ep_hall", "EN-HALL", "HALL-12 string (AEPS)", "T1", "engine",
     "ENGINE", 1, 1, 0.115, 3.0, T("""
[engine]
thrust_kN  = 0.00059
isp_s      = 2800.0
isp_sl_s   = 0.0
throttle   = [0.0, 1.0]
gimbal_deg = 10.0
propellant = { Xenon = 1.0 }
ep_power_kwe = 12.5
ep_eta = 0.65""")),
    ("ep_hall_x", "EN-HALL-X", "HALL-100 nested string (X3)", "T3",
     "engine", "ENGINE", 2, 2, 0.46, 12.0, T("""
[engine]
thrust_kN  = 0.0054
isp_s      = 2000.0
isp_sl_s   = 0.0
throttle   = [0.0, 1.0]
gimbal_deg = 10.0
propellant = { Xenon = 1.0 }
ep_power_kwe = 100.0
ep_eta = 0.52""")),
    ("ep_mpd", "EN-MPD", "MPD-200 applied-field string", "T3", "engine",
     "ENGINE", 2, 2, 0.90, 15.0, T("""
[engine]
thrust_kN  = 0.0046
isp_s      = 4000.0
isp_sl_s   = 0.0
throttle   = [0.0, 1.0]
gimbal_deg = 10.0
propellant = { Argon = 1.0 }
ep_power_kwe = 200.0
ep_eta = 0.45""")),
    ("ep_vasimr", "EN-VAS", "VAS-200 VASIMR string", "T3", "engine",
     "ENGINE", 2, 3, 0.65, 20.0, T("""
[engine]
thrust_kN  = 0.0057
isp_s      = 4900.0
isp_sl_s   = 0.0
throttle   = [0.0, 1.0]
gimbal_deg = 10.0
propellant = { Argon = 1.0 }
ep_power_kwe = 200.0
ep_eta = 0.69""")),
    ("rcs_n2", "RCS-N2", "RCS-N10 cold-gas quad", "T0", "engine",
     "ENGINE", 1, 1, 0.008, 0.1, T("""
[engine]
thrust_kN  = 0.04
isp_s      = 70.0
isp_sl_s   = 70.0
throttle   = [0.0, 1.0]
gimbal_deg = 0.0
propellant = { Nitrogen = 1.0 }
rcs = true""")),
    ("rcs_hyp", "RCS-HYP", "RCS-D400 quad (Draco)", "T0", "engine",
     "ENGINE", 1, 1, 0.022, 0.4, T("""
[engine]
thrust_kN  = 1.6
isp_s      = 300.0
isp_sl_s   = 280.0
throttle   = [0.0, 1.0]
gimbal_deg = 0.0
propellant = { NTO = 0.623, MMH = 0.377 }
rcs = true
ullage = true""")),
    ("rcs_ch4", "RCS-CH4", "RCS-M2K hot-gas quad", "T1", "engine",
     "ENGINE", 1, 1, 0.060, 0.6, T("""
[engine]
thrust_kN  = 8.0
isp_s      = 270.0
isp_sl_s   = 250.0
throttle   = [0.0, 1.0]
gimbal_deg = 0.0
propellant = { Oxygen = 0.783, Methane = 0.217 }
rcs = true""")),
    # -- power & thermal (1.6) ------------------------------------------------------
    ("pw_sa_r", "PW-SA-R", "Rigid solar wing", "T0", "structure", "ELEC",
     1, 4, 0.16, 0.8,
     "deployed_area_m2 = 12.5\n[power]\noutput_kwe = 5.0\nsolar = true"),
    ("pw_sa_ro", "PW-SA-RO", "Roll-out array (ROSA)", "T0", "structure",
     "ELEC", 1, 3, 0.25, 2.0,
     "deployed_area_m2 = 46.0\n[power]\noutput_kwe = 20.0\nsolar = true"),
    ("pw_bat", "PW-BAT", "Battery bank", "T0", "structure", "ELEC",
     1, 1, 0.20, 0.5, "[power]\nstorage_kwh = 30.0"),
    ("pw_fc", "PW-FC", "Fuel cell", "T0", "structure", "ELEC",
     1, 1, 0.12, 1.0, "[power]\noutput_kwe = 7.0\nfuel_cell = true"),
    ("pw_rtg", "PW-RTG", "RTG (MMRTG)", "T0", "structure", "ELEC",
     1, 1, 0.045, 15.0, "[power]\noutput_kwe = 0.11"),
    ("pw_kp1", "PW-KP1", "Fission unit 1 kWe (Kilopower)", "T2",
     "structure", "ELEC", 1, 2, 0.40, 20.0,
     "[power]\noutput_kwe = 1.0\nreactor = true"),
    ("pw_kp10", "PW-KP10", "Fission unit 10 kWe", "T2", "structure",
     "ELEC", 2, 3, 1.5, 60.0, "[power]\noutput_kwe = 10.0\nreactor = true"),
    ("pw_fsp", "PW-FSP", "Surface fission 100 kWe", "T2", "structure",
     "ELEC", 3, 4, 9.0, 150.0,
     "[power]\noutput_kwe = 100.0\nreactor = true"),
    ("pw_nep", "PW-NEP", "NEP reactor 2 MWe", "T3", "structure", "ELEC",
     5, 8, 35.0, 600.0, "deployed_area_m2 = 144.0\n"
     "[power]\noutput_kwe = 2000.0\nreactor = true"),
    ("th_rad", "TH-RAD", "Deployable radiator", "T0", "structure", "ELEC",
     1, 3, 1.2, 1.5,
     "deployed_area_m2 = 12.0\n[power]\nreject_kwt = 50.0"),
    # -- habs (1.7) --------------------------------------------------------------------
    ("hb_cap4", "HB-CAP4", "4-crew capsule", "T0", "crew", "HAB",
     3, 4, 9.5, 60.0, T("""
command_source = true
[crew]
capacity = 4
endurance_days = 30
[hab]
v_press_m3 = 20.0
sleeps = 4
[shield]
tps_qdot_max = 12.0
ablator_t = 0.11""")),
    ("hb_rig_s", "HB-RIG-S", "Rigid module S", "T0", "crew", "HAB",
     3, 5, 9.0, 70.0,
     "[crew]\ncapacity = 2\nendurance_days = 900\n"
     "[hab]\nv_press_m3 = 60.0\nsleeps = 2"),
    ("hb_inf_s", "HB-INF-S", "Inflatable module S (BEAM)", "T0",
     "structure", "HAB", 2, 2, 1.4, 8.0,
     "deployed_size = [3, 4]\n[hab]\nv_press_m3 = 16.0\nsleeps = 0"),
    ("hb_inf_m", "HB-INF-M", "Inflatable hab M (TransHab)", "T1", "crew",
     "HAB", 3, 5, 13.2, 80.0, T("""
deployed_size = [8, 11]
[crew]
capacity = 6
endurance_days = 900
[hab]
v_press_m3 = 340.0
sleeps = 6
surge = 6""")),
    ("hb_inf_l", "HB-INF-L", "Inflatable hab L (B330)", "T1", "crew",
     "HAB", 4, 6, 20.0, 150.0, T("""
deployed_size = [8, 11]
[crew]
capacity = 6
endurance_days = 1800
[hab]
v_press_m3 = 330.0
sleeps = 6
surge = 6""")),
    ("hb_cup", "HB-CUP", "Cupola", "T0", "structure", "HAB",
     2, 1, 1.9, 15.0, "[hab]\nv_press_m3 = 3.0\nsleeps = 0\nmorale = 6"),
    ("hb_air", "HB-AIR", "Airlock", "T0", "structure", "HAB",
     2, 3, 6.1, 30.0,
     "[hab]\nv_press_m3 = 34.0\nsleeps = 0\nairlock = true"),
    ("hb_lab", "HB-LAB", "Science lab (Destiny-class)", "T1", "structure",
     "HAB", 4, 9, 12.0, 100.0,
     "[hab]\nv_press_m3 = 100.0\nsleeps = 0\nlab = true"),
    ("hb_grn_s", "HB-GRN-S", "Greenhouse S", "T2", "structure", "HAB",
     3, 5, 6.0, 40.0,
     "[hab]\nv_press_m3 = 80.0\nsleeps = 0\ngrow_m2 = 50.0"),
    ("hb_grn", "HB-GRN", "Greenhouse (full diet)", "T3", "structure",
     "HAB", 4, 9, 16.0, 90.0,
     "[hab]\nv_press_m3 = 280.0\nsleeps = 0\ngrow_m2 = 200.0"),
    ("hb_storm", "HB-STORM", "Storm shelter core", "T1", "structure",
     "HAB", 2, 2, 3.0, 12.0,
     "[hab]\nv_press_m3 = 8.0\nsleeps = 0\nshelter = true\n"
     "water_fill_t = 5.0"),
    # -- spin, docking & assembly (1.8) --------------------------------------------------
    ("sp_hub", "SP-HUB", "Despun hub w/ rotary seal", "T2", "structure",
     "MECH", 3, 3, 8.0, 90.0,
     "spin_hub = true\nmotor_knm = 10.0\n"
     "[port]\nsize = \"B\"\nrating_kn = 150\ncount = 2"),
    ("sp_arm", "SP-ARM", "Spin truss arm 10 m", "T2", "structure",
     "STRUCT", 1, 10, 1.2, 2.0, "axial_kn = 800\nspin_arm = true"),
    ("sp_tether", "SP-TETHER", "Bolo tether 200 m", "T2", "structure",
     "MECH", 1, 2, 0.8, 3.0, "tether_kn = 300\ntether_m = 200"),
    ("sp_hab", "SP-HAB", "Ring hab pod", "T2", "crew", "HAB",
     3, 4, 8.0, 60.0,
     "spin_r_min_m = 20.0\n[crew]\ncapacity = 2\nendurance_days = 1800\n"
     "[hab]\nv_press_m3 = 60.0\nsleeps = 2"),
    ("sp_ring", "SP-RING", "Ring segment 30 deg", "T3", "crew", "HAB",
     29, 4, 22.0, 120.0,
     "ring_segment = true\n[crew]\ncapacity = 4\nendurance_days = 3600\n"
     "[hab]\nv_press_m3 = 180.0\nsleeps = 4"),
    ("dk_s", "DK-S", "Docking port S (IDSS)", "T0", "structure", "MECH",
     1, 1, 0.34, 2.0, "[port]\nsize = \"S\"\nrating_kn = 60"),
    ("dk_b", "DK-B", "Berthing port B (CBM)", "T0", "structure", "MECH",
     2, 1, 0.25, 2.0,
     "[port]\nsize = \"B\"\nrating_kn = 150\nneeds_arm = true"),
    ("dk_l", "DK-L", "Structural berth L", "T1", "structure", "MECH",
     3, 1, 1.2, 5.0,
     "[port]\nsize = \"L\"\nrating_kn = 800\nfluid = true"),
    ("dk_gr", "DK-GR", "Grapple fixture", "T0", "structure", "MECH",
     1, 1, 0.05, 0.3, "grapple = true"),
    ("dk_arm", "DK-ARM", "Robot arm (17 m)", "T1", "structure", "MECH",
     1, 2, 1.8, 40.0, "robot_arm = true\nreach_m = 17\nmoves_t = 116"),
    ("hb_dockyard", "HB-DOCKYARD", "Dry Dock module", "T2", "structure",
     "STRUCT", 6, 12, 24.0, 200.0,
     "dockyard = true\n[hab]\nv_press_m3 = 20.0\nsleeps = 0\n"
     "[port]\nsize = \"B\"\nrating_kn = 150"),
    ("ut_cmg", "UT-CMG", "Control moment gyro", "T0", "structure", "MECH",
     1, 1, 0.3, 8.0, "cmg_nms = 4760\ncmg_torque_knm = 0.26"),
    # -- cargo, utility, entry & landing (1.9) ---------------------------------------------
    ("cg_bay", "CG-BAY", "Unpressurized cargo bay", "T0", "structure",
     "STRUCT", 2, 3, 0.6, 0.8, "cargo_t = 8.0\ncargo_cells = 12"),
    ("cg_hop", "CG-HOP", "Ore hopper", "T1", "structure", "STRUCT",
     3, 3, 1.5, 1.0, "cargo_t = 12.0\nbulk = true"),
    ("cg_con", "CG-CON", "Container berth", "T1", "structure", "STRUCT",
     2, 1, 0.15, 0.3, "container_berth = true"),
    ("cg_rb", "CG-RB", "Regolith ballast box", "T2", "structure",
     "STRUCT", 2, 2, 0.4, 0.2, "ballast_fill_t = 10.0"),
    ("ut_av", "UT-AV", "Avionics core", "T0", "structure", "ELEC",
     1, 1, 0.15, 5.0,
     "command_source = true\n[power]\ndraw_kwe = 0.3"),
    ("ut_avs", "UT-AVS", "Probe core S", "T0", "structure", "ELEC",
     1, 1, 0.04, 2.0,
     "command_source = true\n[power]\ndraw_kwe = 0.1"),
    ("ut_dish_s", "UT-DISH-S", "High-gain dish 0.5 m", "T0", "structure",
     "ELEC", 1, 1, 0.02, 1.0, "dish_m = 0.5"),
    ("ut_dish_m", "UT-DISH-M", "High-gain dish 3 m", "T0", "structure",
     "ELEC", 1, 2, 0.09, 3.0, "dish_m = 3.0\ndeployed_area_m2 = 7.0"),
    ("ut_dish_l", "UT-DISH-L", "Deployable dish 10 m", "T2", "structure",
     "ELEC", 2, 2, 0.4, 10.0, "dish_m = 10.0\ndeployed_area_m2 = 80.0"),
    ("ut_hs3", "UT-HS3", "Heat shield 3.7 m (PICA)", "T0", "structure",
     "SHIELD", 3, 1, 0.5, 2.0,
     "nodes = \"no_bottom\"\n[shield]\ntps_qdot_max = 12.0\n"
     "ablator_t = 0.17\ncolumn_w = 3"),
    ("ut_hs5", "UT-HS5", "Heat shield 5 m (PICA)", "T1", "structure",
     "SHIELD", 4, 1, 0.9, 4.0,
     "nodes = \"no_bottom\"\n[shield]\ntps_qdot_max = 12.0\n"
     "ablator_t = 0.31\ncolumn_w = 4"),
    ("ut_chute", "UT-CHUTE", "Parachute cluster", "T0", "structure",
     "MECH", 1, 1, 0.24, 0.5,
     "chute_recover_t = 6.0\nchute_q_max_kpa = 20.0\nchute_a_max_g = 7.0"),
    ("st_ll", "ST-LL", "Landing leg", "T0", "structure", "MECH",
     1, 2, 0.15, 0.4, "leg_rating_t = 8.0\nleg_td_ms = 3.0"),
    ("st_llh", "ST-LLH", "Heavy landing leg", "T1", "structure", "MECH",
     1, 3, 0.6, 1.0, "leg_rating_t = 40.0\nleg_td_ms = 3.0"),
    ("ar_shell", "AR-SHELL", "Entry aeroshell 5 m", "T3", "structure",
     "SHIELD", 4, 2, 2.5, 8.0,
     "nodes = \"no_bottom\"\n[shield]\ntps_qdot_max = 12.0\n"
     "ablator_t = 0.63\ncolumn_w = 4\nvenus_rated = true"),
    ("ar_chute", "AR-CHUTE", "Supersonic extraction chute", "T3",
     "structure", "MECH", 1, 1, 0.6, 1.5,
     "chute_recover_t = 10.0\nchute_q_max_kpa = 4.0\nchute_mach_max = 2.2"),
    # -- Whipple (1.10) ---------------------------------------------------------------------
    ("ws_b", "WS-B", "Whipple panel 10 m2", "T0", "structure", "SHIELD",
     1, 2, 0.10, 0.3, "[shield]\nwhipple_eta = 0.90\ncovers_m2 = 10.0"),
    ("ws_s", "WS-S", "Stuffed Whipple 10 m2", "T1", "structure",
     "SHIELD", 1, 2, 0.22, 0.8,
     "[shield]\nwhipple_eta = 0.98\ncovers_m2 = 10.0"),
    ("ws_bf", "WS-BF", "BasaltFiber stuffed panel", "T2", "structure",
     "SHIELD", 1, 2, 0.22, "res",
     "[shield]\nwhipple_eta = 0.97\ncovers_m2 = 10.0"),
]


def emit_new() -> int:
    n = 0
    for (fn, cat, name, tier, ptype, cls, w, h, dry, cost, extra) in NEW:
        lines = [
            f'id     = "core:{fn}"',
            f'type   = "{ptype}"',
            f'tier   = "{tier}"',
            f'name   = "{name}"',
            f"mass_t = {dry}",
            f'catalog_id = "{cat}"',
            f'class = "{cls}"',
            f"size = [{w}, {h}]",
        ]
        if cost == "res":
            lines.append("printable = true")
        else:
            lines.append(f"cost_musd = {cost}")
        body = "\n".join(lines)
        if extra:
            body += "\n" + extra
        with open(os.path.join(OUT, fn + ".toml"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(body + "\n")
        n += 1
    return n


def patch_existing() -> int:
    n = 0
    for path in glob.glob(os.path.join(OUT, "*.toml")):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        pid = None
        for line in text.splitlines():
            if line.replace(" ", "").startswith("id="):
                pid = line.split("=", 1)[1].strip().strip('"')
                break
        spec = PATCH.get(pid)
        if spec is None or "catalog_id" in text:
            continue
        cat, cls, w, h, cost = spec
        ins = (f'catalog_id = "{cat}"\nclass = "{cls}"\n'
               f"size = [{w}, {h}]\ncost_musd = {cost}\n")
        if pid in COMMAND_SOURCES:
            ins += "command_source = true\n"
        i = text.find("\n[")
        text = (text + "\n" + ins) if i < 0 else \
            text[:i + 1] + ins + text[i + 1:]
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        n += 1
    return n


if __name__ == "__main__":
    patched = patch_existing()
    new = emit_new()
    total = len(glob.glob(os.path.join(OUT, "*.toml")))
    print(f"patched {patched} existing, wrote {new} new, "
          f"{total} part files total")
