"""Load-time validation (13 §3.4: fail loudly, fail early).

1. Schema: required keys, types, unit ranges.
2. Referential integrity: every referenced id exists.
3. Physics invariants: recipe mass balance within 0.5 %; republished SOI
   values match the Laplace computation; engine consistency.
4. Exactly one root body; element sanity.

A failed validation raises ContentError naming file, key, expected/got.
"""

from __future__ import annotations

from aphelion.content.loader import ContentDB, ContentError
from aphelion.content.schema import (
    ELEMENTS_SCHEMA,
    RECIPE_MASS_BALANCE_TOL,
    SOI_REPUBLISH_TOL,
    TYPE_SCHEMAS,
)

CANONICAL_RESOURCES = {
    "Water", "Oxygen", "Hydrogen", "Methane", "Nitrogen", "CO2", "Ammonia",
    "Argon", "Xenon", "Regolith", "IronSteel", "Aluminum", "Titanium",
    "Copper", "Silicon", "RareEarths", "Uranium", "Thorium", "Pu238",
    "Carbon", "Polymers", "BasaltFiber", "Glass", "Electronics",
    "MachineParts", "StructuralParts", "FoodRations", "Biomass", "He3",
    # registered extensions (design/README.md glossary)
    "RP1", "NTO", "MMH", "Wafers", "MedSupplies", "SurveyData",
}


def _check_fields(type_name: str, item_id: str, raw: dict, src: str) -> None:
    schema = TYPE_SCHEMAS[type_name]
    for key, (required, check) in schema.items():
        if key not in raw:
            if required:
                raise ContentError(f"{src}: {item_id}: missing required key {key!r}")
            continue
        if not check(raw[key]):
            raise ContentError(
                f"{src}: {item_id}: key {key!r} failed validation (got {raw[key]!r})")


def _validate_bodies(db: ContentDB) -> None:
    bodies = db.bodies
    roots = []
    for item_id, raw in bodies.items():
        src = db.sources[item_id]
        _check_fields("bodies", item_id, raw, src)
        parent = raw["parent"]
        if parent is None:
            roots.append(item_id)
            if raw.get("elements") is not None:
                raise ContentError(f"{src}: {item_id}: root body must have no elements")
            continue
        if parent not in bodies:
            raise ContentError(f"{src}: {item_id}: parent {parent!r} does not exist")
        el = raw.get("elements")
        if not isinstance(el, dict):
            raise ContentError(f"{src}: {item_id}: non-root body needs 'elements'")
        for key, (required, check) in ELEMENTS_SCHEMA.items():
            if key not in el:
                if required:
                    raise ContentError(f"{src}: {item_id}: elements missing {key!r}")
                continue
            if not check(el[key]):
                raise ContentError(
                    f"{src}: {item_id}: elements.{key} failed validation "
                    f"(got {el[key]!r})")
    # Recipes/parts-only packs are legitimate; the root requirement applies
    # only when bodies exist at all (ephemeris build still fails loudly if a
    # campaign launches without a system).
    if bodies and len(roots) != 1:
        raise ContentError(f"bodies: expected exactly one root, got {roots!r}")

    # Physics invariant: republished SOI must match the Laplace computation
    # r_SOI = a (mu_b/mu_p)^(2/5) (mass ratio == mu ratio). 0 (dock mode,
    # floor rule) and None (infinite, root) are exempt.
    for item_id, raw in bodies.items():
        parent = raw["parent"]
        soi = raw["soi_m"]
        if parent is None or soi is None or soi == 0.0:
            continue
        a = raw["elements"]["a_m"]
        computed = a * (raw["mu_m3s2"] / bodies[parent]["mu_m3s2"]) ** 0.4
        rel = abs(soi - computed) / computed
        if rel > SOI_REPUBLISH_TOL:
            raise ContentError(
                f"{db.sources[item_id]}: {item_id}: republished soi_m {soi:.4g} "
                f"deviates {rel:.1%} from Laplace value {computed:.4g}")


def _validate_recipes(db: ContentDB) -> None:
    for item_id, raw in db.recipes.items():
        src = db.sources[item_id]
        _check_fields("recipes", item_id, raw, src)
        flows = [raw["inputs_t"], raw["outputs_t"],
                 raw.get("byproducts_t", {})]
        for flow in flows:
            for res in flow:
                if res not in CANONICAL_RESOURCES:
                    raise ContentError(
                        f"{src}: {item_id}: non-canonical resource {res!r}")
        mass_in = sum(raw["inputs_t"].values())
        mass_out = (sum(raw["outputs_t"].values())
                    + sum(raw.get("byproducts_t", {}).values())
                    + raw.get("loss_t", 0.0))
        if mass_in > 0 and abs(mass_in - mass_out) / mass_in > RECIPE_MASS_BALANCE_TOL:
            raise ContentError(
                f"{src}: {item_id}: mass balance violated: in {mass_in} t, "
                f"out {mass_out} t (> {RECIPE_MASS_BALANCE_TOL:.1%})")


def _validate_parts(db: ContentDB) -> None:
    for item_id, raw in db.parts.items():
        _check_fields("parts", item_id, raw, db.sources[item_id])


def _validate_tech(db: ContentDB) -> None:
    from aphelion.sim.research import FAMILIES   # canonical family list

    tech = db.tech
    discoveries = db.by_type("discoveries")
    known_ids = set(db.parts) | set(db.recipes) | set(tech)
    for item_id, raw in tech.items():
        src = db.sources[item_id]
        _check_fields("tech", item_id, raw, src)
        for term in raw["prereqs"]:
            refs = term if isinstance(term, list) else [term]
            for ref in refs:
                if ref not in tech:
                    raise ContentError(f"{src}: {item_id}: unknown prereq {ref!r}")
        for ref in raw["unlocks"]:
            if ref not in known_ids:
                raise ContentError(f"{src}: {item_id}: unlocks unknown id {ref!r}")
        for th in raw.get("ed_thresholds", []):
            if th["family"] not in FAMILIES:
                raise ContentError(
                    f"{src}: {item_id}: unknown ED family {th['family']!r}")
        for ref in raw.get("discovery_prereqs", []):
            if ref not in discoveries:
                raise ContentError(
                    f"{src}: {item_id}: unknown discovery {ref!r}")


def _validate_discoveries(db: ContentDB) -> None:
    tech = db.tech
    for item_id, raw in db.by_type("discoveries").items():
        src = db.sources[item_id]
        _check_fields("discoveries", item_id, raw, src)
        for ref in raw["gates"]:
            if ref not in tech:
                raise ContentError(f"{src}: {item_id}: gates unknown node {ref!r}")
        for d in raw.get("discounts", []):
            if not isinstance(d, dict) or d.get("node") not in tech \
                    or not isinstance(d.get("frac"), (int, float)):
                raise ContentError(f"{src}: {item_id}: bad discount {d!r}")


def validate(db: ContentDB) -> None:
    _validate_bodies(db)
    _validate_parts(db)
    _validate_recipes(db)
    _validate_tech(db)
    _validate_discoveries(db)
