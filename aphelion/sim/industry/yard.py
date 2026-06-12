"""Orbital shipyards (05 §3.1): the six job classes at canon rates, the
build schedule for erecting a drydock DESIGN in orbit, the 0.65×
orbital structural multiplier, and the F-11 learning curve applied to
the labor-driven phases. Surface pads run the same job classes at the
same rates (07 owns the pad building; 05 owns erection labor)."""

from __future__ import annotations

from dataclasses import dataclass

from aphelion.sim.industry.chains import PARTS_KEYS, parts_bill
from aphelion.sim.industry.wear import labor_mult

# job rates (§3.1)
BERTH_PER_DAY_PER_ARM_PAIR = 1.0      # prefab module ≤ 25 t
BERTH_MAX_T = 25.0
BERTH_LABOR = (2.0, 4.0)              # crew-h, robot-h per event
INTEGRATE_DAYS_PER_INTERFACE = 0.5
INTEGRATE_ROBOT_H = 8.0
FABWELD_T_DAY_PER_GANG = 1.0          # A2 gangs; A3 gangs run 24/7
FABWELD_T_DAY_PER_GANG_A3 = 0.7
OUTFIT_T_DAY_PER_GANG = 0.8
OUTFIT_CREW_MIN_FRAC = 0.25           # quality gate: crew ≥ 0.25 × robot
COMMISSION_DAYS_PER_10T = 0.5
COMMISSION_LABOR_PER_10T = (8.0, 16.0)
TRUSS_FAB_KG_DAY = 120.0

ORBITAL_STRUCT_MULT = 0.65            # orbital_only blueprints; the hull
                                      # can never enter an atmosphere


@dataclass(slots=True)
class YardPlan:
    """The priced schedule for one orbital build."""
    days: float
    phase_days: dict            # phase -> days
    bill_kg: dict               # parts draw (kg)
    crew_h: float
    robot_h: float
    learning: float             # F-11 multiplier applied


def plan_build(dry_t: float, n_parts: int, gangs: int = 3,
               arm_pairs: int = 2, a3: bool = False,
               orbital_only: bool = True, n_built_before: int = 0,
               prefab_t: float = 0.0) -> YardPlan:
    """Erect a design at a dry dock. Mass beyond `prefab_t` (berthed
    whole, ≤25 t modules) is FABWELDed from the parts bill; interfaces
    integrate at 0.5 d each; the MachineParts+Electronics share outfits
    at 0.8 t/day/gang; commissioning is never skipped here (×3 hazard
    isn't worth it). F-11: labor phases shrink as the design repeats."""
    gangs = max(1, gangs)
    arm_pairs = max(1, arm_pairs)
    learn = labor_mult(max(1, n_built_before + 1))

    fab_t = max(0.0, dry_t - prefab_t)
    bill = parts_bill(fab_t)
    if orbital_only:
        bill["StructuralParts"] *= ORBITAL_STRUCT_MULT
    bill_kg = {k: v * 1_000.0 for k, v in bill.items() if v > 0.0}

    rate = (FABWELD_T_DAY_PER_GANG_A3 if a3 else FABWELD_T_DAY_PER_GANG)
    d_berth = (prefab_t / BERTH_MAX_T) / arm_pairs if prefab_t else 0.0
    d_fabweld = fab_t / (rate * gangs) * learn
    d_integrate = n_parts * INTEGRATE_DAYS_PER_INTERFACE * learn
    outfit_t = (bill.get("MachineParts", 0.0)
                + bill.get("Electronics", 0.0))
    d_outfit = outfit_t / (OUTFIT_T_DAY_PER_GANG * gangs) * learn
    d_comm = COMMISSION_DAYS_PER_10T * dry_t / 10.0

    crew_h = (BERTH_LABOR[0] * (prefab_t / BERTH_MAX_T)
              + COMMISSION_LABOR_PER_10T[0] * dry_t / 10.0) * learn
    robot_h = (BERTH_LABOR[1] * (prefab_t / BERTH_MAX_T)
               + INTEGRATE_ROBOT_H * n_parts
               + COMMISSION_LABOR_PER_10T[1] * dry_t / 10.0) * learn

    phases = {"BERTH": d_berth, "FABWELD": d_fabweld,
              "INTEGRATE": d_integrate, "OUTFIT": d_outfit,
              "COMMISSION": d_comm}
    return YardPlan(days=sum(phases.values()), phase_days=phases,
                    bill_kg=bill_kg, crew_h=crew_h, robot_h=robot_h,
                    learning=learn)


def sanity_t_per_day(gangs: int = 3, a3: bool = False) -> float:
    """§3.1 sanity row: a T2 dock with 3 gangs sustains ~3 t/day fab."""
    return gangs * (FABWELD_T_DAY_PER_GANG_A3 if a3
                    else FABWELD_T_DAY_PER_GANG)


def cargo_capacity_kg(vessel) -> float:
    """Cargo cells aboard a stack (CG-BAY rows etc.)."""
    return sum(float(vessel.part(r).get("cargo_t", 0.0)) * 1_000.0
               for r in vessel.rows)


def has_dockyard(vessel) -> bool:
    return any(vessel.part(r).get("dockyard") for r in vessel.rows)


PARTS_CARGO = tuple(PARTS_KEYS)
