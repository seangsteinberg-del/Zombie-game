"""Food & agriculture (08 §3): ration forms, the caloric/starvation model
(90,000 kcal body reserve), the canon crop catalog, and the greenhouse
(CEA) model with establishment lag, light/water/ammonia draws, the capped
fresh-food store with dry overflow, and blight.
"""

from __future__ import annotations

KCAL_BASE_DAY = 2_500.0          # × activity multiplier A
BODY_RESERVE_KCAL = 90_000.0     # depletes to deconditioning + death

# stored food forms (08 §3.1): kg/crew/day, prep water kg/day, shelf-life
# years, morale modifier while the staple diet
RATIONS = {
    "FD-DEHY":  {"kg_day": 0.62, "prep_water": 1.2, "shelf_yr": 5.0,
                 "morale": 0.0,  "tier": 0},
    "FD-PKG":   {"kg_day": 1.83, "prep_water": 0.0, "shelf_yr": 1.5,
                 "morale": 0.0,  "tier": 0},
    "FD-FRESH": {"kg_day": 0.0,  "prep_water": 0.0, "shelf_yr": 0.02,
                 "morale": 12.0, "tier": 2},
    "FD-EMRG":  {"kg_day": 0.5,  "prep_water": 0.0, "shelf_yr": 7.0,
                 "morale": -10.0, "tier": 0},
}

# crop catalog (08 §3.4) — yields at full light
# (tier, cycle days, kcal/m²/day, light kW/m², water L/m²/day)
CROPS = {
    "potato":       (2, 95,  250.0, 0.28, 3.5),
    "wheat":        (3, 70,  200.0, 0.30, 3.0),
    "sweet_potato": (3, 120, 230.0, 0.30, 3.5),
    "rice":         (3, 85,  160.0, 0.32, 5.0),
    "soybean":      (3, 90,  120.0, 0.30, 3.2),
    "peanut":       (3, 110, 130.0, 0.30, 3.0),
    "lettuce":      (1, 30,  25.0,  0.18, 2.0),
    "tomato":       (1, 80,  40.0,  0.25, 4.0),
    "kale":         (1, 40,  30.0,  0.20, 2.5),
    "strawberry":   (3, 90,  35.0,  0.22, 3.0),
    "chlorella":    (3, 1,   60.0,  0.60, 0.0),
}

KCAL_PER_KG_DRY = 4_000.0        # dry-equivalent food energy density
AMMONIA_PER_DRY_KG = 0.03        # kg N (as Ammonia) per kg edible dry mass
FRESH_CAP_CREW_DAYS = 14.0       # fresh store cap (then dried → rations)
TRANSPIRE_RECOVERY = 0.98        # via CHX

# per-person closure area anchors (08 §3.5)
AREA_FULL_DIET_M2 = 40.0
AREA_STAPLE_ONLY_M2 = 16.7
AREA_O2_BALANCE_M2 = 8.0         # algae


class CrewEnergy:
    """One crew member's caloric ledger: reserve depletes on shortfall,
    refills on surplus; zero = death (08 §3.2)."""

    def __init__(self, reserve_kcal: float = BODY_RESERVE_KCAL) -> None:
        self.reserve = reserve_kcal

    def step_day(self, kcal_eaten: float, activity: float = 1.0,
                 days: float = 1.0) -> None:
        need = KCAL_BASE_DAY * activity * days
        self.reserve = min(BODY_RESERVE_KCAL,
                           self.reserve + kcal_eaten - need)

    @property
    def starving(self) -> bool:
        return self.reserve < 0.5 * BODY_RESERVE_KCAL

    @property
    def dead(self) -> bool:
        return self.reserve <= 0.0

    @property
    def productivity_penalty(self) -> float:
        """0 fed → 0.7 near death (folds into P_health as starvation)."""
        frac = max(0.0, self.reserve / BODY_RESERVE_KCAL)
        return 0.0 if frac > 0.5 else 0.7 * (1.0 - frac / 0.5)


class Greenhouse:
    """One greenhouse's planted beds. Beds carry an age; nothing yields
    until the crop's cycle completes (the Act-3 logistics trap — carry
    rations to bridge). Yields scale with light availability and the
    Agronomist bonus; blight zeroes a bed and forces a full re-cycle."""

    def __init__(self, area_m2: float) -> None:
        self.area_m2 = area_m2
        # crop -> [allocated m², bed age days]
        self.beds: dict[str, list] = {}
        self.fresh_kcal = 0.0            # capped fresh store
        self.dry_overflow_kg = 0.0       # dried surplus → FoodRations

    def plant(self, crop: str, area_m2: float) -> bool:
        used = sum(b[0] for b in self.beds.values())
        if crop not in CROPS or used + area_m2 > self.area_m2 + 1e-9:
            return False
        bed = self.beds.setdefault(crop, [0.0, 0.0])
        if bed[0] > 0.0:
            # expanding an established bed restarts the clock pro-rata
            bed[1] = bed[1] * bed[0] / (bed[0] + area_m2)
        bed[0] += area_m2
        return True

    def blight(self, crop: str) -> None:
        """Crop failure: the bed restarts its full cycle (08 §3.3)."""
        if crop in self.beds:
            self.beds[crop][1] = 0.0

    # -- daily run ----------------------------------------------------------
    def step_day(self, crew_n: int, light_frac: float = 1.0,
                 agronomist_level: int = 0, days: float = 1.0) -> dict:
        """Returns the day's flows: kcal produced, power kW needed, water
        transpired (L, ~98% back via CHX), ammonia kg consumed."""
        kcal = 0.0
        power = 0.0
        water = 0.0
        agro = min(1.25, 1.0 + 0.08 * agronomist_level)
        for crop, bed in self.beds.items():
            area, age = bed
            tier, cycle, y_kcal, light, w_l = CROPS[crop]
            bed[1] = age + days
            power += area * light
            water += area * w_l * days
            if bed[1] >= cycle:
                kcal += area * y_kcal * light_frac * agro * days
        ammonia = (kcal / KCAL_PER_KG_DRY) * AMMONIA_PER_DRY_KG
        # fresh store fills to the cap; overflow dries to rations
        cap = FRESH_CAP_CREW_DAYS * KCAL_BASE_DAY * max(1, crew_n)
        self.fresh_kcal += kcal
        if self.fresh_kcal > cap:
            self.dry_overflow_kg += (self.fresh_kcal - cap) / KCAL_PER_KG_DRY
            self.fresh_kcal = cap
        return {"kcal": kcal, "power_kw": power,
                "water_l": water, "ammonia_kg": ammonia}

    def eat_fresh(self, kcal_wanted: float) -> float:
        got = min(self.fresh_kcal, kcal_wanted)
        self.fresh_kcal -= got
        return got

    def take_dry_kg(self) -> float:
        kg, self.dry_overflow_kg = self.dry_overflow_kg, 0.0
        return kg

    def eta_food(self, crew_n: int) -> float:
        """Closure fraction this greenhouse could sustain at steady state
        (mature beds, full light) — the §2.1 ladder readout."""
        if crew_n <= 0:
            return 0.0
        steady = sum(b[0] * CROPS[c][2] for c, b in self.beds.items())
        return min(0.95, steady / (KCAL_BASE_DAY * crew_n))

    # -- persistence ----------------------------------------------------------
    def to_dict(self) -> dict:
        return {"area": self.area_m2,
                "beds": {c: list(b) for c, b in self.beds.items()},
                "fresh": self.fresh_kcal, "dry": self.dry_overflow_kg}

    @classmethod
    def from_dict(cls, d: dict) -> "Greenhouse":
        g = cls(d["area"])
        g.beds = {c: [float(b[0]), float(b[1])]
                  for c, b in d.get("beds", {}).items()}
        g.fresh_kcal = d.get("fresh", 0.0)
        g.dry_overflow_kg = d.get("dry", 0.0)
        return g


def full_diet_layout(crew_n: int) -> dict[str, float]:
    """The 40 m²/crew balanced template (08 §3.5): ~22 staples + 10
    protein + 8 veg/fruit. Deliberately ~2.5× margin over 2,500 kcal."""
    return {"potato": 14.0 * crew_n, "wheat": 8.0 * crew_n,
            "soybean": 6.0 * crew_n, "peanut": 4.0 * crew_n,
            "lettuce": 3.0 * crew_n, "tomato": 3.0 * crew_n,
            "strawberry": 2.0 * crew_n}
