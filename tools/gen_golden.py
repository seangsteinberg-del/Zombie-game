"""Generate golden save #1 (Phase 2 DoD fixture). Run ONLY when a schema
migration intentionally changes the format: python tools/gen_golden.py
"""

from pathlib import Path

from aphelion.content.loader import default_data_dir, load_packs
from aphelion.content.validate import validate
from aphelion.core.rng import RngRegistry
from aphelion.sim.habitat.lsc import build_iss_grade_hab
from aphelion.sim.orbits.kepler import Elements
from aphelion.sim.vessels.vessel import Vessel
from aphelion.save.serialize import build_save, write_save


def main() -> None:
    db = load_packs(default_data_dir())
    validate(db)
    el = Elements(mu=4.9028e12, alpha=1.0 / 1.8374e6, e=0.0007,
                  varpi=1.1, tau=-321.5, s=1.0)
    lander = Vessel(db, [
        Vessel.fueled_row(db, "core:engine_ml111"),
        Vessel.fueled_row(db, "core:tank_ml_s"),
        Vessel.fueled_row(db, "core:payload_2t"),
    ], stage_plan=[[0, 1, 2]], cd_a_m2=0.0)
    hab = build_iss_grade_hab(crew=2, water_store=120.0, o2_store=40.0,
                              food_store=25.0, battery_kwh=60.0,
                              supply_kw=2.5)
    rng = RngRegistry(20490101)
    save = build_save(t=86_400.0, vessels={"lander": lander},
                      orbits={"lander": el}, ledgers={"hab": hab}, rng=rng)
    out = Path(__file__).resolve().parent.parent / "aphelion" / "tests" / "golden" / "golden1.sav"
    out.parent.mkdir(parents=True, exist_ok=True)
    write_save(out, save)
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
