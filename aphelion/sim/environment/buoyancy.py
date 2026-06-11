"""Buoyancy statics for the exotic habitats (07 B-8 / 10): Venus aerostats
(breathable air as lifting gas — the HAVOC trick) and Titan submarines/
dirigibles (liquid methane seas, dense cold N2 air).
"""

from __future__ import annotations

from aphelion.sim.environment.atmosphere import density

R_GAS = 8.314462618          # J/(mol K)

MOLAR_KG_MOL = {
    "venus_atmo": 0.04345,   # CO2 96.5 / N2 3.5
    "air": 0.02897,          # habitable 21/79 O2/N2
    "titan_atmo": 0.02795,   # N2 94.5 / CH4 5
    "h2": 0.002016,
}

TITAN_SURFACE = {"pressure_pa": 146_700.0, "temperature_k": 93.7,
                 "g": 1.35}
LCH4_DENSITY = 570.0         # kg/m^3, liquid methane ~94 K (NASA Titan Sub)
VENUS_G = 8.87


def gas_density(gas: str, pressure_pa: float, temperature_k: float) -> float:
    """Ideal gas: rho = P mu / (R T)."""
    return pressure_pa * MOLAR_KG_MOL[gas] / (R_GAS * temperature_k)


def venus_lift_kg_m3(altitude_m: float, cabin_temperature_k: float = 300.0,
                     band_pressure_pa: float = 70_000.0) -> float:
    """Net lift per m^3 of BREATHABLE AIR envelope at the aerostat band
    (HAVOC). The envelope flies at AMBIENT pressure — at the temperate
    52.5-54 km band that is ~0.6-0.8 atm (03 §4.4a) — with cabin-warm air;
    the lift is the CO2-vs-air molar-mass gap at equal P and T-ish."""
    rho_ambient = density("core:venus", altitude_m)
    rho_air = gas_density("air", band_pressure_pa, cabin_temperature_k)
    return rho_ambient - rho_air


def venus_envelope_volume_m3(gondola_kg: float, altitude_m: float = 52_500.0,
                             margin: float = 1.2) -> float:
    """Envelope volume to float a gondola at the band (statics, 07 B-8)."""
    lift = venus_lift_kg_m3(altitude_m)
    if lift <= 0.0:
        raise ValueError("no positive lift at this altitude")
    return gondola_kg * margin / lift


def titan_air_density() -> float:
    return gas_density("titan_atmo", TITAN_SURFACE["pressure_pa"],
                       TITAN_SURFACE["temperature_k"])


def titan_dirigible_lift_kg_m3(lifting_gas: str = "h2") -> float:
    """Titan airships: dense cold N2 vs warm light gas."""
    rho_atm = titan_air_density()
    rho_gas = gas_density(lifting_gas, TITAN_SURFACE["pressure_pa"], 200.0)
    return rho_atm - rho_gas


def titan_submarine_net_buoyancy_n(displacement_m3: float,
                                   mass_kg: float) -> float:
    """Archimedes in Kraken Mare: liquid methane ~570 kg/m^3 — barely half
    of water; Titan subs must be LEAD-DENSE compared to Earth boats (the
    NASA Titan Submarine study's central mass problem)."""
    g = TITAN_SURFACE["g"]
    return (LCH4_DENSITY * displacement_m3 - mass_kg) * g


def titan_wing_lift_n(wing_area_m2: float, v_ms: float, cl: float = 1.0) -> float:
    """L = 0.5 rho v^2 Cl A — at rho 5.3 and g 1.35, human-powered flight is
    genuinely possible (DECISIONS C20 keeps it)."""
    return 0.5 * titan_air_density() * v_ms ** 2 * cl * wing_area_m2
