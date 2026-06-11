"""Propellant flow & crossfeed (06 §2.7). The drain rule: an engine
draws each resource at its O/F split from all graph-connected
same-feed-group tanks holding it, proportionally. Crossfeed (FD-1 /
DK-L) forms a feed group draining in DESCENDING stage number
(asparagus), proportional within a stage, per-tank priority integers
overriding. Either resource exhausting = flameout (deterministic).
"""

from __future__ import annotations

from dataclasses import dataclass, field

KGPS_PER_TPM = 1_000.0 / 60.0    # duct flow caps are quoted t/min


@dataclass
class TankState:
    """One tank's live loads (t per resource) + its drain ordering."""
    loads: dict = field(default_factory=dict)
    stage: int = 0
    priority: int | None = None   # higher drains first; beats stage

    def total_t(self) -> float:
        return sum(self.loads.values())


def _groups(tanks: list[TankState], crossfeed: bool) -> list[list[TankState]]:
    if not crossfeed:
        return [list(tanks)]
    def key(t: TankState):
        return (t.priority if t.priority is not None else -1, t.stage)
    order = sorted({key(t) for t in tanks}, reverse=True)
    return [[t for t in tanks if key(t) == k] for k in order]


def drain(tanks: list[TankState], mix: dict, dm_t: float,
          crossfeed: bool = False) -> float:
    """Draw up to dm_t of propellant at the O/F mass split. Returns the
    mass actually drawn; short = the engine flames out this step. The
    draw is all-or-nothing per the mix (a stranded surplus of the rich
    resource never burns alone)."""
    if dm_t <= 0.0:
        return 0.0
    # the limiting resource caps the WHOLE draw (06 §2.4/§2.7)
    avail = {r: sum(t.loads.get(r, 0.0) for t in tanks) for r in mix}
    burnable = min((avail[r] / f for r, f in mix.items() if f > 0),
                   default=0.0)
    take = min(dm_t, burnable)
    if take <= 0.0:
        return 0.0
    for res, frac in mix.items():
        need = take * frac
        for grp in _groups(tanks, crossfeed):
            if need <= 1e-12:
                break
            have = sum(t.loads.get(res, 0.0) for t in grp)
            if have <= 0.0:
                continue
            pull = min(need, have)
            for t in grp:                  # proportional within a group
                share = pull * t.loads.get(res, 0.0) / have
                t.loads[res] = t.loads.get(res, 0.0) - share
            need -= pull
    return take


def flameout(tanks: list[TankState], mix: dict) -> bool:
    """True when the scarcer O/F resource is dry (deterministic)."""
    return any(sum(t.loads.get(r, 0.0) for t in tanks) <= 1e-9
               for r, f in mix.items() if f > 0)


def w9_flow_capped(mdot_kgps: float, ducts: list[dict],
                   cryogenic: bool = True) -> bool:
    """Design-time W9: the crossfeed ducts can't feed the engines at
    full throttle (flight throttles to the cap)."""
    if not ducts:
        return False
    cap = sum(float(d.get("flow_cryo_tpm" if cryogenic
                          else "flow_storable_tpm", 0.0)) * KGPS_PER_TPM
              for d in ducts)
    return mdot_kgps > cap
