"""Drydock 2.0 grid datamodel (06 §2.1): parts occupy w×h footprints at
integer cells (+y = nose, −y = engines), joints derive from face
adjacency under the attach-node rules, and the E1–E5 validation codes
fall out of the graph. Pure sim — the editor scene renders this.

Coordinates: a part at (x, y) fills cells [x, x+w) × [y, y+h); y grows
toward the nose. Stack joints form where one part's bottom row meets
another's top row with ≥1 cell of x-overlap; radial joints where sides
touch with ≥1 cell of y-overlap. Rules honored here:
- engines / heat shields / aeroshells expose NO bottom node (nothing
  hangs beneath them; they can still hang from what's above),
- nodes="interior" (fairings, open trusses): parts fully inside the
  fairing_interior region attach to the container and are exempt from
  E4 overlap with it,
- RCS quads are surface-mount: radial joints only, E5-exempt,
- ST-IS-V hot-staging vents the plume column (E5 exemption through it).
"""

from __future__ import annotations

from dataclasses import dataclass, field

PART_CAP = 600                   # per vessel, docked merges included
PLUME_LEN_M = 6                  # exhaust column below the nozzle

# axial joint ratings by material class, kN (06 §1 defaults)
CLASS_AXIAL_KN = {"STRUCT": 1_200.0, "TANK": 1_200.0, "HAB": 1_200.0,
                  "ENGINE": 1_200.0, "ELEC": 300.0, "SHIELD": 300.0,
                  "MECH": 300.0}
RADIAL_FRACTION = 0.25           # radial joints: 25% of the smaller rating


def _size(spec: dict) -> tuple[int, int]:
    w, h = spec.get("size", [1, 1])
    return int(w), int(h)


def axial_rating_kn(spec: dict) -> float:
    """Part's stack-node rating; engines rate max(1200, 1.25·F_vac)."""
    if "axial_kn" in spec:
        return float(spec["axial_kn"])
    base = CLASS_AXIAL_KN.get(spec.get("class", "STRUCT"), 1_200.0)
    eng = spec.get("engine")
    if eng and not eng.get("rcs"):
        return max(base, 1.25 * float(eng.get("thrust_kN", 0.0)))
    return base


def _no_bottom(spec: dict) -> bool:
    if spec.get("nodes") == "no_bottom":
        return True
    eng = spec.get("engine")
    return bool(eng and not eng.get("rcs"))


def _surface_mount(spec: dict) -> bool:
    eng = spec.get("engine")
    return bool(eng and eng.get("rcs"))


def _interior(spec: dict) -> bool:
    return spec.get("nodes") == "interior"


@dataclass
class GridPart:
    pid: str                     # content id, e.g. core:tank_ml_m
    spec: dict
    x: int
    y: int

    @property
    def w(self) -> int:
        return _size(self.spec)[0]

    @property
    def h(self) -> int:
        return _size(self.spec)[1]

    @property
    def cells(self) -> set[tuple[int, int]]:
        return {(cx, cy) for cx in range(self.x, self.x + self.w)
                for cy in range(self.y, self.y + self.h)}

    def centroid(self) -> tuple[float, float]:
        return self.x + self.w / 2.0, self.y + self.h / 2.0


@dataclass
class Joint:
    a: int                       # part indices
    b: int
    kind: str                    # "stack" | "radial" | "interior"
    rating_kn: float = 0.0


class GridVessel:
    """The editable craft: placed parts + derived joints + validation."""

    def __init__(self) -> None:
        self.parts: list[GridPart] = []

    # -- editing ---------------------------------------------------------------
    def add(self, pid: str, spec: dict, x: int, y: int) -> int | None:
        """Place a part; refuses past the 600 cap. Overlap is allowed at
        placement (E4 reports it) so the editor can show the conflict."""
        if len(self.parts) >= PART_CAP:
            return None
        self.parts.append(GridPart(pid, spec, int(x), int(y)))
        return len(self.parts) - 1

    def remove(self, idx: int) -> None:
        self.parts.pop(idx)

    def move(self, idx: int, x: int, y: int) -> None:
        self.parts[idx].x = int(x)
        self.parts[idx].y = int(y)

    # -- fairing interiors --------------------------------------------------------
    def _interior_rect(self, p: GridPart) -> tuple | None:
        fi = p.spec.get("fairing_interior")
        if not fi and _interior(p.spec):
            fi = [p.w, p.h]          # open truss: whole footprint usable
        if not fi:
            return None
        iw, ih = int(fi[0]), int(fi[1])
        return (p.x + (p.w - iw) // 2, p.y + (p.h - ih) // 2, iw, ih)

    def container_of(self, idx: int) -> int | None:
        """The fairing/truss whose interior fully holds part idx."""
        p = self.parts[idx]
        for j, c in enumerate(self.parts):
            if j == idx:
                continue
            r = self._interior_rect(c)
            if r is None:
                continue
            rx, ry, rw, rh = r
            if (rx <= p.x and p.x + p.w <= rx + rw
                    and ry <= p.y and p.y + p.h <= ry + rh):
                return j
        return None

    # -- joints (derived, O(n²) on edit — n ≤ 600) ---------------------------------
    def joints(self) -> list[Joint]:
        out = []
        inside = {i: self.container_of(i) for i in range(len(self.parts))}
        for i, a in enumerate(self.parts):
            for j in range(i + 1, len(self.parts)):
                b = self.parts[j]
                if inside.get(i) == j or inside.get(j) == i:
                    out.append(Joint(i, j, "interior", min(
                        axial_rating_kn(a.spec), axial_rating_kn(b.spec))))
                    continue
                xo = min(a.x + a.w, b.x + b.w) - max(a.x, b.x)
                yo = min(a.y + a.h, b.y + b.h) - max(a.y, b.y)
                # stack: faces meet vertically with x overlap
                if xo >= 1 and not _surface_mount(a.spec) \
                        and not _surface_mount(b.spec):
                    lo, hi = (a, b) if a.y < b.y else (b, a)
                    if lo.y + lo.h == hi.y and not _no_bottom(hi.spec):
                        out.append(Joint(i, j, "stack", min(
                            axial_rating_kn(a.spec),
                            axial_rating_kn(b.spec))))
                        continue
                # radial: sides touch with y overlap
                if yo >= 1 and (a.x + a.w == b.x or b.x + b.w == a.x):
                    rating = RADIAL_FRACTION * min(
                        axial_rating_kn(a.spec), axial_rating_kn(b.spec))
                    out.append(Joint(i, j, "radial", rating))
        return out

    def _components(self, skip: set[int] | None = None) -> list[set[int]]:
        skip = skip or set()
        adj: dict[int, set[int]] = {i: set() for i in
                                    range(len(self.parts)) if i not in skip}
        for jt in self.joints():
            if jt.a in skip or jt.b in skip:
                continue
            adj[jt.a].add(jt.b)
            adj[jt.b].add(jt.a)
        seen: set[int] = set()
        comps = []
        for i in adj:
            if i in seen:
                continue
            stack, comp = [i], set()
            while stack:
                k = stack.pop()
                if k in comp:
                    continue
                comp.add(k)
                stack.extend(adj[k] - comp)
            seen |= comp
            comps.append(comp)
        return comps

    # -- validation E1–E5 (06 §2.14) --------------------------------------------------
    def validate(self) -> list[tuple[str, int | None]]:
        """[(code, offending part index or None)]; empty = clean."""
        errs: list[tuple[str, int | None]] = []
        if not any(p.spec.get("command_source") for p in self.parts):
            errs.append(("E1", None))
        comps = self._components()
        if len(comps) > 1:
            small = min(comps, key=len)
            errs.append(("E2", min(small)))
        # E3: every decoupler must split the graph into exactly two
        for i, p in enumerate(self.parts):
            if p.spec.get("decoupler"):
                if len(self._components(skip={i})) != 2:
                    errs.append(("E3", i))
        # E4: overlapping footprints (fairing interiors exempt)
        for i, a in enumerate(self.parts):
            for j in range(i + 1, len(self.parts)):
                b = self.parts[j]
                if not (a.cells & b.cells):
                    continue
                if self.container_of(i) == j or self.container_of(j) == i:
                    continue
                errs.append(("E4", j))
        # E5: plume impingement — exhaust column w wide, 6 m below the
        # nozzle; RCS exempt; vented interstage in the column vents it;
        # a part that SEPARATES before ignition (a decoupler sits in the
        # column between it and the engine) is no impingement
        for i, p in enumerate(self.parts):
            eng = p.spec.get("engine")
            if not eng or eng.get("rcs"):
                continue
            col = {(cx, cy) for cx in range(p.x, p.x + p.w)
                   for cy in range(p.y - PLUME_LEN_M, p.y)}
            vented = any(o.spec.get("hot_stage")
                         and (o.cells & col) for o in self.parts)
            if vented:
                continue
            for j, o in enumerate(self.parts):
                if j == i or _surface_mount(o.spec):
                    continue
                if not (o.cells & col):
                    continue
                if o.spec.get("decoupler") and o.y + o.h <= p.y:
                    continue             # the staging plane itself
                staged = any(
                    d.spec.get("decoupler") and (d.cells & col)
                    and o.y + o.h <= d.y and d.y < p.y
                    for d in self.parts)
                if staged:
                    continue             # gone before this engine lights
                errs.append(("E5", j))
                break
        return errs

    # -- mass & geometry readouts (D3 builds on these) -----------------------------------
    def dry_mass_t(self) -> float:
        return sum(float(p.spec.get("mass_t", 0.0)) for p in self.parts)

    def com(self) -> tuple[float, float]:
        """Dry COM in cell units (wet COM lands with D3 plumbing)."""
        m = 0.0
        sx = sy = 0.0
        for p in self.parts:
            pm = float(p.spec.get("mass_t", 0.0))
            cx, cy = p.centroid()
            m += pm
            sx += pm * cx
            sy += pm * cy
        if m <= 0.0:
            return 0.0, 0.0
        return sx / m, sy / m

    # -- persistence ------------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {"parts": [[p.pid, p.x, p.y] for p in self.parts]}

    @classmethod
    def from_dict(cls, d: dict, db) -> "GridVessel":
        v = cls()
        specs = db.by_type("parts")
        for pid, x, y in d.get("parts", []):
            v.add(pid, specs[pid], x, y)
        return v
