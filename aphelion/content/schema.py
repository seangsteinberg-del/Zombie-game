"""Declarative content schemas (13 §3.4/§4.2 — field names binding).

Each content type maps to a spec: {field: (required, check)} where check is
a predicate over the raw value. The validator reports file/key/expected/got
and the game refuses to start on failure (fail loudly, fail early).
"""

from __future__ import annotations

from typing import Any, Callable

Check = Callable[[Any], bool]


def _is_id(v: Any) -> bool:
    return isinstance(v, str) and ":" in v and all(part for part in v.split(":", 1))


def _num(lo: float | None = None, hi: float | None = None,
         allow_none: bool = False) -> Check:
    def check(v: Any) -> bool:
        if v is None:
            return allow_none
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            return False
        if lo is not None and v < lo:
            return False
        if hi is not None and v > hi:
            return False
        return True
    return check


def _string(v: Any) -> bool:
    return isinstance(v, str) and len(v) > 0


TIERS = {"T0", "T1", "T2", "T3", "T4"}

# (required, check) per field. Unknown keys are allowed (forward compat /
# pack patches) — validation only asserts what the engine relies on.
BODY_SCHEMA: dict[str, tuple[bool, Check]] = {
    "id": (True, _is_id),
    "parent": (True, lambda v: v is None or _is_id(v)),
    "mu_m3s2": (True, _num(lo=1e-3)),
    "radius_m": (True, _num(lo=1.0)),
    "rotation_period_s": (True, _num()),            # negative = retrograde spin
    "soi_m": (True, _num(lo=0.0, allow_none=True)),  # None = infinite (root)
    # elements: None for the root; checked structurally in validate.py
}

ELEMENTS_SCHEMA: dict[str, tuple[bool, Check]] = {
    "a_m": (True, _num(lo=1.0)),
    "e": (True, _num(lo=0.0, hi=1.999)),
    "lon_peri_rad": (True, _num()),
    "t_peri_s": (True, _num()),
    "sense": (True, lambda v: v in (1, -1)),
}

ENGINE_SCHEMA: dict[str, tuple[bool, Check]] = {
    "thrust_kN": (True, _num(lo=1e-6)),
    "isp_s": (True, _num(lo=1e-3, hi=20_000.0)),     # 13 §3.4 range rule
    "isp_sl_s": (False, _num(lo=0.0, hi=20_000.0)),
    "gimbal_deg": (False, _num(lo=0.0, hi=45.0)),
}

PART_SCHEMA: dict[str, tuple[bool, Check]] = {
    "id": (True, _is_id),
    "type": (True, _string),
    "tier": (True, lambda v: v in TIERS),
    "name": (True, _string),
    "mass_t": (True, _num(lo=1e-9)),
}

RECIPE_SCHEMA: dict[str, tuple[bool, Check]] = {
    "id": (True, _is_id),
    "module": (True, _is_id),
    "tier": (True, lambda v: v in TIERS),
    "inputs_t": (True, lambda v: isinstance(v, dict)),
    "outputs_t": (True, lambda v: isinstance(v, dict)),
    "energy_kWh_per_t": (True, _num(lo=0.0)),
}

def _prereq_list(v: Any) -> bool:
    """Prereq grammar (11 §1): list of AND terms; a nested list is an OR
    group. Every leaf is an id string."""
    if not isinstance(v, list):
        return False
    for term in v:
        if isinstance(term, list):
            if not term or not all(_is_id(x) for x in term):
                return False
        elif not _is_id(term):
            return False
    return True


def _ed_thresholds(v: Any) -> bool:
    if not isinstance(v, list):
        return False
    return all(isinstance(t, dict) and isinstance(t.get("family"), str)
               and isinstance(t.get("value"), (int, float)) for t in v)


TECH_SCHEMA: dict[str, tuple[bool, Check]] = {
    "id": (True, _is_id),
    "tier": (True, lambda v: v in TIERS),
    "name": (True, _string),
    "category": (False, _string),
    "prereqs": (True, _prereq_list),
    "unlocks": (True, lambda v: isinstance(v, list)),
    "grants": (False, lambda v: isinstance(v, list)),
    "cost_sci": (False, _num(lo=0.0)),
    "ed_thresholds": (False, _ed_thresholds),
    "discovery_prereqs": (False, lambda v: isinstance(v, list)),
    "era": (False, lambda v: isinstance(v, bool)),
    "speculative": (False, lambda v: isinstance(v, bool)),
    "anchor": (False, _string),
}

DISCOVERY_SCHEMA: dict[str, tuple[bool, Check]] = {
    "id": (True, _is_id),
    "name": (True, _string),
    "sci": (True, _num(lo=0.0)),
    "staged": (True, lambda v: isinstance(v, bool)),
    "gates": (True, lambda v: isinstance(v, list)),
    "discounts": (False, lambda v: isinstance(v, list)),
    "trigger_kind": (True, _string),
    "body": (True, _is_id),
    "requirement": (True, _string),
}

# content-type directory name -> schema
TYPE_SCHEMAS: dict[str, dict[str, tuple[bool, Check]]] = {
    "bodies": BODY_SCHEMA,
    "parts": PART_SCHEMA,
    "recipes": RECIPE_SCHEMA,
    "tech": TECH_SCHEMA,
    "discoveries": DISCOVERY_SCHEMA,
}

RECIPE_MASS_BALANCE_TOL = 0.005     # 0.5 % (05 §3.2 rule)
SOI_REPUBLISH_TOL = 0.05            # republished SOI vs Laplace-computed
