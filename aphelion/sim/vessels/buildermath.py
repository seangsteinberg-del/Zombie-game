"""Drydock builder math (06 §2.2–2.5): the live readouts. One constant
g0 everywhere; ṁ is a per-engine constant derived from the VACUUM pair —
F(p) = ṁ·g0·Isp(p). Never mix one pressure's thrust with another's Isp
(the spec's Build-A trap: 70,000 kg / 599.4 kg/s = 117 s, not 126).

Note on canon: catalogs list real engines' measured SL thrust (Merlin
845 kN), which disagrees by a few % with the ṁ-constant model
(914·282/311 = 829). The ṁ rule is the binding one (06 §2.4) — every
number here derives from it, including sea-level TWR.
"""

from __future__ import annotations

from dataclasses import dataclass, field

G0 = 9.80665
P_SL_KPA = 101.325


# ---- per-engine laws --------------------------------------------------------
def mdot_kgps(eng: dict) -> float:
    """Constant mass flow from the vacuum pair (06 §2.4)."""
    return float(eng["thrust_kN"]) * 1e3 / (float(eng["isp_s"]) * G0)


def isp_at(eng: dict, p_kpa: float) -> float:
    """Ambient Isp: vac − (vac − SL)·(p/101.325), p clamped at SL."""
    p = min(max(p_kpa, 0.0), P_SL_KPA)
    vac = float(eng["isp_s"])
    sl = float(eng.get("isp_sl_s", vac))
    return vac - (vac - sl) * (p / P_SL_KPA)


def thrust_kn_at(eng: dict, p_kpa: float) -> float:
    return mdot_kgps(eng) * G0 * isp_at(eng, p_kpa) / 1e3


def isp_traj_avg(eng: dict) -> float:
    """First-stage trajectory-averaged Isp = SL + 0.44·(vac − SL)."""
    vac = float(eng["isp_s"])
    sl = float(eng.get("isp_sl_s", vac))
    return sl + 0.44 * (vac - sl)


def mixed_isp(engines: list[dict], isp_of) -> float:
    """Thrust-weighted effective Isp: ΣF / Σ(F/Isp), vac thrusts."""
    if not engines:
        return 0.0
    f_tot = sum(float(e["thrust_kN"]) for e in engines)
    denom = sum(float(e["thrust_kN"]) / isp_of(e) for e in engines)
    return f_tot / denom if denom > 0 else 0.0


def ep_thrust_fraction(eng: dict, avail_kwe: float) -> float:
    """Under-powered EP throttles at constant Isp: available power ÷
    RATED thruster power (06 §2.4), capped at 1."""
    rated = float(eng.get("ep_power_kwe", 0.0))
    if rated <= 0.0:
        return 1.0
    return min(1.0, max(0.0, avail_kwe / rated))


def solar_kwe(rated_kwe: float, d_au: float) -> float:
    """Array output falls 1/d²."""
    return rated_kwe / max(0.01, d_au) ** 2


# ---- O/F burnable limit (06 §2.4/§2.7) ---------------------------------------
def burnable_prop_t(loaded_t: dict, mix: dict) -> float:
    """Total prop the engine can actually burn from these loads: the
    scarcer resource at the O/F mass split limits everything."""
    lim = float("inf")
    for res, frac in mix.items():
        if frac <= 0.0:
            continue
        lim = min(lim, loaded_t.get(res, 0.0) / frac)
    return 0.0 if lim == float("inf") else lim


# ---- per-stage report ----------------------------------------------------------
@dataclass
class StageDef:
    """One stage, bottom-up: its engines, its inert mass (structure +
    engine dry + tank dry + anything jettisoned with it), and its
    burnable propellant. Payload rides in the TOP stage's inert."""
    engines: list = field(default_factory=list)
    inert_t: float = 0.0
    prop_t: float = 0.0


def stage_report(stages: list[StageDef], g_ref: float = G0,
                 mode: str = "vac", ep_power_kwe: float | None = None
                 ) -> list[dict]:
    """Bottom-up dv/TWR/burn per stage (06 §2.4/§2.5). mode picks the
    Isp law: "vac" | "sl" | "traj". EP stages may pass available power
    for the thrust fraction (Isp and dv unchanged; burns stretch)."""
    def isp_of(e):
        if mode == "sl":
            return isp_at(e, P_SL_KPA)
        if mode == "traj":
            return isp_traj_avg(e)
        return float(e["isp_s"])

    out = []
    for k, st in enumerate(stages):
        above = sum(s.inert_t + s.prop_t for s in stages[k + 1:])
        m0 = st.inert_t + st.prop_t + above
        m1 = m0 - st.prop_t
        isp = mixed_isp(st.engines, isp_of)
        dv = 0.0
        if st.prop_t > 0 and m1 > 0 and isp > 0:
            import math
            dv = isp * G0 * math.log(m0 / m1)
        f_kn = sum(float(e["thrust_kN"]) for e in st.engines)
        if mode in ("sl", "traj"):
            f_kn = sum(thrust_kn_at(e, P_SL_KPA) for e in st.engines)
        frac = 1.0
        if ep_power_kwe is not None and st.engines:
            frac = min(ep_thrust_fraction(e, ep_power_kwe / len(st.engines))
                       for e in st.engines)
        md = sum(mdot_kgps(e) for e in st.engines) * frac
        out.append({
            "m0_t": m0, "m1_t": m1, "dv_ms": dv, "isp_s": isp,
            "thrust_kn": f_kn * frac,
            "twr_ignition": f_kn * frac * 1e3 / (m0 * 1e3 * g_ref)
            if m0 > 0 else 0.0,
            "twr_burnout": f_kn * frac * 1e3 / (m1 * 1e3 * g_ref)
            if m1 > 0 else 0.0,
            "burn_s": st.prop_t * 1e3 / md if md > 0 else 0.0,
            "mdot_kgps": md,
        })
    return out
