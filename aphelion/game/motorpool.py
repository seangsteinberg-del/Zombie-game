"""V5: the vehicle entity layer — ground vehicles as first-class campaign
objects (10 §1/§3). A GroundVehicle lives at a surface site, is built at a
base's Motor Pool from real parts (MachineParts/Electronics debited off the
shelves), drains real energy when driven (V-5), wears per V-24, bricks its
battery on cold nights, and can hop/dive when its class allows.

Pure game-logic module: the pilot SCENES live in main; the physics live in
sim/vehicles/*; this file glues catalog rows to a playable entity with
deterministic, save-friendly state.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from aphelion.sim.vehicles import locomotion, wear as vwear
from aphelion.sim.vehicles.powerplant import usable_kwh

# parts bill per dry tonne for field-assembling a vehicle at a Motor Pool
# (mirrors the 10 §1 cost note's overhaul fractions x a build multiple: a
# full build is ~10x an overhaul's wear parts)
BUILD_MACHINEPARTS_FRAC = 0.30      # t per dry t
BUILD_ELECTRONICS_FRAC = 0.05       # t per dry t
SERVICE_COND_FLOOR = 0.999          # full service restores to ~new


@dataclass
class GroundVehicle:
    """One vehicle at (or moving between) surface sites."""
    vid: int
    catalog_id: str                  # "core:rvr_lrv" etc.
    name: str
    body: str                        # "core:moon"
    site_id: str                     # site it is parked at
    pack_kwh: float                  # installed storage (catalog row)
    energy_kwh: float                # current charge
    cond: float = 1.0                # 05 condition C in [0,1]
    odo_km: float = 0.0
    cargo_t: float = 0.0
    rtg_we: float = 0.0              # 0 = battery vehicle
    tracks: bool = False
    crewed: bool = False
    bricked_events: int = 0

    # -- driving (called by the drive scene per sim step) -----------------

    def e_km(self, g: float, terrain: str = "regolith",
             v_kmh: float = 10.0, hotel_kw: float = 0.0,
             mass_t: float | None = None, slope_deg: float = 0.0) -> float:
        """kWh per km at current load on this terrain (V-1+V-3 → V-5)."""
        m = (mass_t if mass_t is not None else self.mass_t) * 1000.0
        terr = locomotion.TERRAIN.get(terrain, locomotion.TERRAIN["regolith"])
        f = (locomotion.f_roll_n(terr.crr, m, g, slope_deg)
             + locomotion.f_grade_n(m, g, slope_deg))
        return locomotion.e_km_kwh(max(f, 0.0), hotel_kw * 1000.0, v_kmh)

    def drive(self, dist_km: float, g: float, terrain: str = "regolith",
              v_kmh: float = 10.0, hotel_kw: float = 0.06,
              dust_body: str = "other") -> bool:
        """Spend energy + wear for a leg; False = battery dead first.
        RTG vehicles recharge continuously and never strand (range inf,
        speed-bound per 10 §3.1)."""
        need = self.e_km(g, terrain, v_kmh, hotel_kw) * dist_km
        if self.rtg_we <= 0.0:
            if need > self.energy_kwh:
                return False
            self.energy_kwh -= need
        self.odo_km += dist_km
        self.cond = max(0.0, self.cond - vwear.dc_wheels(
            dist_km, terrain=terrain, body=dust_body, tracks=self.tracks))
        return True

    def night_cycle(self, sheltered: bool) -> None:
        """V-24d thermal cycling + brick risk when exposed unpowered."""
        if sheltered:
            return
        self.cond = max(0.0, self.cond - vwear.dc_thermal_cycles(1))

    def brick(self) -> None:
        """-30% capacity event (10 failure row 3)."""
        self.bricked_events += 1
        self.pack_kwh *= 0.70
        self.energy_kwh = min(self.energy_kwh, usable_kwh(self.pack_kwh))

    @property
    def mass_t(self) -> float:
        return self.dry_t + self.cargo_t

    # populated from the catalog row at construction/restore
    dry_t: float = 1.0

    def to_dict(self) -> dict:
        return {"vid": self.vid, "catalog_id": self.catalog_id,
                "name": self.name, "body": self.body,
                "site_id": self.site_id, "pack_kwh": self.pack_kwh,
                "energy_kwh": self.energy_kwh, "cond": self.cond,
                "odo_km": self.odo_km, "cargo_t": self.cargo_t,
                "rtg_we": self.rtg_we, "tracks": self.tracks,
                "crewed": self.crewed, "dry_t": self.dry_t,
                "bricked_events": self.bricked_events}

    @staticmethod
    def from_dict(d: dict) -> "GroundVehicle":
        gv = GroundVehicle(
            vid=int(d["vid"]), catalog_id=d["catalog_id"], name=d["name"],
            body=d["body"], site_id=d["site_id"],
            pack_kwh=float(d["pack_kwh"]),
            energy_kwh=float(d["energy_kwh"]), cond=float(d.get("cond", 1.0)),
            odo_km=float(d.get("odo_km", 0.0)),
            cargo_t=float(d.get("cargo_t", 0.0)),
            rtg_we=float(d.get("rtg_we", 0.0)),
            tracks=bool(d.get("tracks", False)),
            crewed=bool(d.get("crewed", False)),
            bricked_events=int(d.get("bricked_events", 0)))
        gv.dry_t = float(d.get("dry_t", 1.0))
        return gv


def row_stats(row: dict) -> dict:
    """Normalize a data/core/vehicles rover row into build stats."""
    dry_t = float(row.get("dry_t", 1.0))
    power = str(row.get("power", ""))
    rtg = 110.0 if "RTG" in power.upper() else 0.0
    pack = float(row.get("pack_kwh", 0.0) or 0.0)
    if pack <= 0.0:                       # parse "STO-SS 100 kWh" idiom
        for tok in power.replace("(", " ").split():
            try:
                val = float(tok)
            except ValueError:
                continue
            if 1.0 <= val <= 600.0:
                pack = val
                break
    return {"dry_t": dry_t, "pack_kwh": pack or 8.7, "rtg_we": rtg,
            "tracks": "TRK" in str(row.get("locomotion", "")).upper(),
            "crewed": int(row.get("crew", 0) or 0) > 0}


def build_bill_t(dry_t: float) -> dict[str, float]:
    """Motor Pool parts bill (tonnes) to assemble a vehicle."""
    return {"MachineParts": dry_t * BUILD_MACHINEPARTS_FRAC,
            "Electronics": dry_t * BUILD_ELECTRONICS_FRAC}


def can_build(base, dry_t: float) -> tuple[bool, str]:
    """Shelf check against the base's buffers (I4 parts economy)."""
    bill = build_bill_t(dry_t)
    for res, t in bill.items():
        buf = base.net.buffers.get(res)
        have = buf.level if buf is not None else 0.0
        if have < t * 1000.0:
            return False, (f"needs {t:.2f} t {res} "
                           f"(shelf {have / 1000.0:.2f} t)")
    return True, ""


def debit_build(base, dry_t: float) -> None:
    for res, t in build_bill_t(dry_t).items():
        base.net.buffers[res].level -= t * 1000.0


def service_bill_t(dry_t: float, cond: float) -> dict[str, float]:
    """Full overhaul per 10 §1 cost note, scaled by missing condition."""
    miss = max(0.0, 1.0 - cond)
    return {"MachineParts": dry_t * 0.03 * miss * 10.0,
            "Electronics": dry_t * 0.005 * miss * 10.0}
