"""Buoyancy statics for the exotic habitats (07 B-8 / 10): Venus aerostats
(breathable air as lifting gas — the HAVOC trick) and Titan submarines/
dirigibles (liquid methane seas, dense cold N2 air).
"""

from __future__ import annotations

R_GAS = 8.314462618          # J/(mol K)

MOLAR_KG_MOL = {
    "venus_atmo": 0.04345,   # CO2 96.5 / N2 3.5
    "air": 0.02897,          # habitable 21/79 O2/N2
    "titan_atmo": 0.02795,   # N2 94.5 / CH4 5
    "h2": 0.002016,
}

TITAN_SURFACE = {"pressure_pa": 146_700.0, "temperature_k": 93.7,
                 "g": 1.35}
# canon mean sea density 550 with per-sea values (10 §2.7; ethane-rich
# Kraken is denser than methane-rich Ligeia)
SEA_DENSITY = {"ligeia": 520.0, "kraken": 580.0, "ontario": 600.0}
LCH4_DENSITY = 550.0         # kg/m^3 mean — use SEA_DENSITY per sea
VENUS_G = 8.87


def gas_density(gas: str, pressure_pa: float, temperature_k: float) -> float:
    """Ideal gas: rho = P mu / (R T)."""
    return pressure_pa * MOLAR_KG_MOL[gas] / (R_GAS * temperature_k)


# canon Venus cloud-band rows (03 §4.4a): altitude -> (P Pa, T_amb K)
_VENUS_BANDS = ((45_000.0, 135_000.0, 385.0), (48_000.0, 100_000.0, 350.0),
                (52_500.0, 70_000.0, 315.0), (54_000.0, 60_000.0, 300.0),
                (58_000.0, 35_000.0, 270.0), (62_000.0, 20_000.0, 245.0))


def _venus_band(altitude_m: float) -> tuple[float, float]:
    bands = _VENUS_BANDS
    if altitude_m <= bands[0][0]:
        return bands[0][1], bands[0][2]
    for (a0, p0, t0), (a1, p1, t1) in zip(bands, bands[1:]):
        if a0 <= altitude_m <= a1:
            u = (altitude_m - a0) / (a1 - a0)
            return p0 + u * (p1 - p0), t0 + u * (t1 - t0)
    return bands[-1][1], bands[-1][2]


def venus_lift_kg_m3(altitude_m: float = 54_000.0,
                     cabin_temperature_k: float = 300.0) -> float:
    """Net lift per m^3 of BREATHABLE AIR envelope at the aerostat band
    (HAVOC). Canon station: 54 km / 60 kPa / 300 K → 0.35 kg/m³ sizing
    lift (10 §2.5). The envelope flies at AMBIENT pressure with
    cabin-warm air; the lift is the CO2-vs-air molar gap at the canon
    band P/T (the generic ρ(h) exponential under-reads this band)."""
    p_band, t_amb = _venus_band(altitude_m)
    rho_ambient = gas_density("venus_atmo", p_band, t_amb)
    rho_air = gas_density("air", p_band, cabin_temperature_k)
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


def titan_dirigible_lift_kg_m3(lifting_gas: str = "h2",
                               gas_temperature_k: float | None = None) -> float:
    """Titan airships: AMBIENT-temperature light gas (canon 4.9 kg/m³
    for H2 at 94 K — warm gas is the Montgolfière's mechanic, not the
    dirigible default)."""
    rho_atm = titan_air_density()
    t_gas = (gas_temperature_k if gas_temperature_k is not None
             else TITAN_SURFACE["temperature_k"])
    rho_gas = gas_density(lifting_gas, TITAN_SURFACE["pressure_pa"], t_gas)
    return rho_atm - rho_gas


def titan_submarine_net_buoyancy_n(displacement_m3: float,
                                   mass_kg: float,
                                   sea: str = "") -> float:
    """Archimedes in a Titan sea: ~550 kg/m^3 mean (per-sea 520/580/600)
    — barely half of water; Titan subs must be LEAD-DENSE compared to
    Earth boats (the NASA Titan Submarine study's central mass problem)."""
    g = TITAN_SURFACE["g"]
    rho = SEA_DENSITY.get(sea, LCH4_DENSITY)
    return (rho * displacement_m3 - mass_kg) * g


def titan_wing_lift_n(wing_area_m2: float, v_ms: float, cl: float = 1.0) -> float:
    """L = 0.5 rho v^2 Cl A — at rho 5.3 and g 1.35, human-powered flight is
    genuinely possible (DECISIONS C20 keeps it)."""
    return 0.5 * titan_air_density() * v_ms ** 2 * cl * wing_area_m2
