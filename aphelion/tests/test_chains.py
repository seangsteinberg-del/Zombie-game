"""Production chains (05 §1): every recipe closes mass balance within
0.5%, the §4.1 power column is GENERATED from §4.2 recipes (the spec's
own consistency rule), F-Y wafer ramp, parts bill, F-13 derate, RX-22
recycling."""

import pytest

from aphelion.sim.industry.chains import (
    FAB_MODULES, RECIPES, alt_power_kwe, f_condition, f_power,
    heat_cascade_credit, heat_kw, insitu_mass_t, parts_bill, power_kwe,
    r_eff, recycle, validate_chains, warmup_h, y_wafer)


def test_chains_validate_clean():
    assert validate_chains() == []
    assert len(RECIPES) == 15
    assert len(FAB_MODULES) == 17


def test_generated_power_column_matches_catalog():
    """§1.6: Power = P_hotel + kWh/t × rate / 24. Catalog anchors."""
    assert power_kwe("fab_machine_shop") == pytest.approx(35.0)
    assert power_kwe("fab_foundry_mill") == pytest.approx(160.0, abs=0.5)
    assert power_kwe("fab_chem_plant") == pytest.approx(140.0)
    assert power_kwe("fab_elec_assy") == pytest.approx(20.0)
    assert power_kwe("fab_printer_lpbf") == pytest.approx(27.0)
    assert power_kwe("fab_printer_poly") == pytest.approx(3.0, abs=0.2)
    assert power_kwe("fab_waam") == pytest.approx(40.0)
    assert power_kwe("fab_assembly_hall") == pytest.approx(35.0)
    assert power_kwe("fab_consumables") == pytest.approx(42.0, abs=0.6)
    assert alt_power_kwe("fab_consumables") == pytest.approx(9.0, abs=0.3)
    assert power_kwe("fab_wafer_fab") == pytest.approx(700.0, abs=0.5)
    assert power_kwe("fab_auto_complex") == pytest.approx(600.0)
    assert power_kwe("fab_sinter_printer") == pytest.approx(47.0, abs=0.4)
    assert power_kwe("fab_ice_caster") == pytest.approx(8.25, abs=0.1)
    # CANON NOTE: winder computes 5.1 from its own formula; the catalog
    # row says 6 (rounded up). The formula wins per §1.6's rule.
    assert power_kwe("fab_filament_winder") == pytest.approx(5.1, abs=0.1)


def test_wafer_ramp_and_warmups():
    assert y_wafer(0.0) == pytest.approx(0.2)
    assert y_wafer(60.0) == pytest.approx(0.9 - 0.7 / 2.718281828, rel=1e-6)
    assert y_wafer(1e6) == pytest.approx(0.9)
    assert warmup_h("fab_foundry_mill") == 6.0
    assert warmup_h("fab_wafer_fab") == 72.0
    assert warmup_h("fab_machine_shop") == 0.5


def test_f1_throughput_law():
    assert f_power(50.0, 100.0) == 0.5
    assert f_condition(0.7) == 1.0
    assert f_condition(0.25) == pytest.approx(0.5)
    assert r_eff(5.0, 0.8, 0.5, 1.0, 0.9) == pytest.approx(1.8)


def test_parts_bill_and_massdriver_anchor():
    """§3.2 row: 850 t Slinger = 510 Struct + 255 Mach + 68 Elec + 17
    Poly (60/30/8/2)."""
    bill = parts_bill(850.0, "log_massdriver")
    assert bill["StructuralParts"] == pytest.approx(510.0)
    assert bill["MachineParts"] == pytest.approx(255.0)
    assert bill["Electronics"] == pytest.approx(68.0)
    assert bill["Polymers"] == pytest.approx(17.0)
    default = parts_bill(100.0)
    assert default["StructuralParts"] == pytest.approx(55.0)
    assert sum(default.values()) == pytest.approx(100.0)


def test_derates_heat_recycle():
    assert insitu_mass_t(10.0, "T2") == 40.0
    assert insitu_mass_t(10.0, "T3") == 30.0
    assert insitu_mass_t(10.0, "T4") == 20.0
    # "a 700 kW fab => ~665 kW heat" (§1.8)
    assert heat_kw("fab_wafer_fab") == pytest.approx(665.0, abs=1.0)
    assert heat_cascade_credit(150.0, 100.0) == pytest.approx(15.0)
    assert heat_cascade_credit(50.0, 200.0) == pytest.approx(10.0)
    reclaimed, residue = recycle(1.0)
    assert reclaimed == pytest.approx(0.8) and residue == pytest.approx(0.2)
