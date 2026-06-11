"""Cabin atmosphere physics (08 §1.4–1.9): ideal-gas partial pressures per
species, per-hour ODEs for O2/CO2/N2/H2O(vap), baseline + choked-breach
leaks, CHX humidity control, the safe-band table, the fire multiplier,
the hypoxia/hypercapnia incapacitation clock, airlock losses and the
prebreathe (DCS) table. Pure sim — callers own stores and hardware sizing.
"""

from __future__ import annotations

import math

R_GAS = 8.314                    # J/(mol·K)
M_GMOL = {"O2": 32.0, "CO2": 44.0, "N2": 28.0, "H2O": 18.0}

# metabolic canon per crew per day (08 §1.1; A = activity multiplier)
O2_IN_KG_DAY = 0.84              # × A
CO2_OUT_KG_DAY = 1.00            # × A
VAPOR_OUT_KG_DAY = 2.3           # × A (respiration + perspiration)

# baseline leak constant: tuned so a well-built ~400 m² hull at 101 kPa
# loses ~0.25 kg air/day (ISS-class)
K_LEAK = 2.6e-7                  # kg/(h · kPa · m²)
CHOKED_KGPH_PER_CM2_KPA = 0.5    # choked-flow constant (08 §1.7)

# player-selectable cabin presets (08 §1.5): total P kPa, O2 mole fraction
ATMOSPHERES = {
    "sea_level":   {"P": 101.3, "o2_frac": 0.21},
    "exploration": {"P": 56.5,  "o2_frac": 0.34},   # DEFAULT deep-space hab
    "reduced_n2":  {"P": 70.0,  "o2_frac": 0.27},
}

PP_H2O_TARGET_KPA = 1.2          # CHX setpoint, mid nominal band


def prebreathe_hours(pp_n2_kpa: float, p_suit_kpa: float = 29.6) -> float:
    """DCS prebreathe time from the tissue ratio R = ppN2 / P_suit
    (08 §4.7). Exploration atm → 0; sea-level cabin → 3.5 h."""
    r = pp_n2_kpa / p_suit_kpa
    if r <= 1.4:
        return 0.0
    if r <= 1.65:
        return 0.5
    if r <= 2.2:
        return 2.0
    return 3.5


class CabinAtm:
    """One pressurized volume. Species tracked as resident masses (kg);
    pressures derive. step_hours() integrates one interval and returns the
    boundary flows so the caller can debit/credit its stores."""

    def __init__(self, v_m3: float, t_k: float = 294.0,
                 preset: str = "exploration") -> None:
        self.v_m3 = v_m3
        self.t_k = t_k
        self.preset = preset
        p = ATMOSPHERES[preset]
        self.m = {"O2": self._m_at(p["P"] * p["o2_frac"], "O2"),
                  "CO2": self._m_at(0.04, "CO2"),
                  "N2": self._m_at(p["P"] * (1.0 - p["o2_frac"]), "N2"),
                  "H2O": self._m_at(1.0, "H2O")}
        self.co2_store_kg = 0.0          # scrubbed accumulator (NOT air)
        self.exposure_min = 0.0          # hypoxia/hypercapnia clock
        self.hole_cm2 = 0.0              # open breach area

    # -- gas state ------------------------------------------------------------
    def _m_at(self, pp_kpa: float, sp: str) -> float:
        return pp_kpa * self.v_m3 * M_GMOL[sp] / (R_GAS * self.t_k)

    def pp(self, sp: str) -> float:
        return self.m[sp] / M_GMOL[sp] * R_GAS * self.t_k / self.v_m3

    @property
    def p_total(self) -> float:
        return sum(self.pp(s) for s in self.m)

    @property
    def o2_frac(self) -> float:
        p = self.p_total
        return self.pp("O2") / p if p > 0 else 0.0

    def fire_multiplier(self) -> float:
        """φ_fire = max(1, (O2_frac/0.21)³ · (P/101)^0.5) (08 §1.5)."""
        p = self.p_total
        if p <= 0:
            return 1.0
        return max(1.0, (self.o2_frac / 0.21) ** 3 * (p / 101.0) ** 0.5)

    # -- safe bands (08 §1.6) --------------------------------------------------
    def bands(self) -> dict[str, str]:
        out = {}
        po2 = self.pp("O2")
        # fire-watch keys on φ_fire, not raw O2 fraction: the canonical
        # Exploration atm IS 34% O2 at 56.5 kPa (φ≈3.2, accepted)
        out["ppO2"] = ("critical" if po2 < 16.0 or po2 > 27.0
                       or self.fire_multiplier() > 4.0
                       else "caution" if po2 < 19.0 or po2 > 23.0
                       else "nominal")
        pco2 = self.pp("CO2")
        out["ppCO2"] = ("critical" if pco2 > 1.0
                        else "caution" if pco2 > 0.4 else "nominal")
        pt = self.p_total
        out["P"] = ("critical" if pt < 40.0
                    else "caution" if pt < 50.0 or pt > 103.0
                    else "nominal")
        ph = self.pp("H2O")
        out["humidity"] = ("caution" if ph > 1.6 or ph < 0.8
                           else "nominal")
        return out

    # -- the per-hour ODE step --------------------------------------------------
    def step_hours(self, hours: float, crew_n: int = 0, activity: float = 1.0,
                   scrub_kgph: float = 0.0, o2_avail_kg: float = 0.0,
                   n2_avail_kg: float = 0.0, chx_kgph: float = 1.0,
                   hull_m2: float = 120.0,
                   plant_uptake_kgph: float = 0.0) -> dict:
        """Integrate. Returns boundary flows (all kg, positive):
        o2_used (debit O2 store), n2_used (debit N2), condensate (credit
        grey water), co2_scrubbed (into the accumulator), air_lost."""
        a = activity
        o2_burn = O2_IN_KG_DAY * a * crew_n / 24.0 * hours
        co2_made = CO2_OUT_KG_DAY * a * crew_n / 24.0 * hours
        vap_made = VAPOR_OUT_KG_DAY * a * crew_n / 24.0 * hours

        # leak: baseline tightness + choked breach flow (08 §1.7)
        p = self.p_total
        leak_kg = (K_LEAK * p * hull_m2
                   + CHOKED_KGPH_PER_CM2_KPA * self.hole_cm2 * p) * hours
        air_lost = 0.0
        if p > 0 and leak_kg > 0:
            for sp in self.m:
                share = min(self.m[sp], leak_kg * self.pp(sp) / p)
                self.m[sp] -= share
                air_lost += share

        # crew gas exchange
        self.m["O2"] = max(0.0, self.m["O2"] - o2_burn)
        self.m["CO2"] += co2_made
        self.m["H2O"] += vap_made

        # CO2 removal: scrubbers to the accumulator + plant uptake; ONLY
        # these touch cabin air (Sabatier draws the accumulator, never air)
        scrubbed = min(self.m["CO2"] - self._m_at(0.02, "CO2"),
                       scrub_kgph * hours)
        scrubbed = max(0.0, scrubbed)
        self.m["CO2"] -= scrubbed
        self.co2_store_kg += scrubbed
        eaten = max(0.0, min(self.m["CO2"] - self._m_at(0.02, "CO2"),
                             plant_uptake_kgph * hours))
        self.m["CO2"] -= eaten

        # O2 setpoint controller: inject from the store toward the preset
        target_o2 = self._m_at(
            ATMOSPHERES[self.preset]["P"]
            * ATMOSPHERES[self.preset]["o2_frac"], "O2")
        o2_used = max(0.0, min(target_o2 - self.m["O2"], o2_avail_kg))
        self.m["O2"] += o2_used

        # N2 makeup toward the preset buffer pressure
        target_n2 = self._m_at(
            ATMOSPHERES[self.preset]["P"]
            * (1.0 - ATMOSPHERES[self.preset]["o2_frac"]), "N2")
        n2_used = max(0.0, min(target_n2 - self.m["N2"], n2_avail_kg))
        self.m["N2"] += n2_used

        # CHX condenses humidity above the setpoint → grey water
        excess = self.m["H2O"] - self._m_at(PP_H2O_TARGET_KPA, "H2O")
        condensate = max(0.0, min(excess, chx_kgph * hours))
        self.m["H2O"] -= condensate

        self._tick_health_clock(hours * 60.0)
        return {"o2_used": o2_used, "n2_used": n2_used,
                "condensate": condensate, "co2_scrubbed": scrubbed,
                "co2_plants": eaten, "air_lost": air_lost}

    # -- hypoxia / hypercapnia clock (08 §1.8) -----------------------------------
    def hazard_t_inc_min(self) -> float | None:
        """Minutes to incapacitation at CURRENT atmosphere, None if safe."""
        po2, pco2 = self.pp("O2"), self.pp("CO2")
        if po2 >= 16.0 and pco2 <= 3.0:
            return None
        r_o2 = min(1.0, max(0.0, (po2 - 8.0) / 8.0))
        r_co2 = min(1.0, max(0.0, (7.0 - pco2) / 4.0))
        return 30.0 * min(r_o2, r_co2)

    def _tick_health_clock(self, minutes: float) -> None:
        if self.hazard_t_inc_min() is None:
            self.exposure_min = max(0.0, self.exposure_min - 2.0 * minutes)
        else:
            self.exposure_min += minutes

    def crew_status(self) -> str:
        """ok | incapacitated | dead, from accumulated exposure vs the
        current insult severity (death ≈ 1.5×t_inc past incapacitation)."""
        t_inc = self.hazard_t_inc_min()
        if t_inc is None:
            return "ok"
        if self.exposure_min >= 2.5 * t_inc + 1.0:
            return "dead"
        if self.exposure_min >= t_inc:
            return "incapacitated"
        return "ok"

    # -- airlock loss (08 §4.7) ---------------------------------------------------
    def airlock_loss_kg(self, v_airlock_m3: float = 4.0,
                        has_pump: bool = False) -> dict:
        """Per EVA cycle, per species: the airlock volume's gas at cabin
        pps, 80% scavenged with a pump. Caller debits stores."""
        fac = (1.0 - 0.8) if has_pump else 1.0
        out = {}
        for sp in ("O2", "N2"):
            out[sp] = (fac * self.pp(sp) * M_GMOL[sp] * v_airlock_m3
                       / (R_GAS * self.t_k))
        return out

    # -- persistence ---------------------------------------------------------------
    def to_dict(self) -> dict:
        return {"v": self.v_m3, "t": self.t_k, "preset": self.preset,
                "m": dict(self.m), "co2_store": self.co2_store_kg,
                "exposure": self.exposure_min, "hole": self.hole_cm2}

    @classmethod
    def from_dict(cls, d: dict) -> "CabinAtm":
        c = cls(d["v"], d.get("t", 294.0), d.get("preset", "exploration"))
        c.m = {k: float(v) for k, v in d["m"].items()}
        c.co2_store_kg = d.get("co2_store", 0.0)
        c.exposure_min = d.get("exposure", 0.0)
        c.hole_cm2 = d.get("hole", 0.0)
        return c
