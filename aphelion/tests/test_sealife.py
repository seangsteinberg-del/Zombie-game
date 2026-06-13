"""THE LIVING SEAS — ecology sim + renderer tests (10 §2.7 DIVE,
11 §5 dsc11/13/14, DECISIONS F34). Covers: determinism (zlib.crc32, no
hash()), the tiered astrobiology ladder per ocean/band, the
sonar-vs-identification split, Tier-2 swarm steering (scatter from
lights / seek RTG warmth), the once-per-campaign Tier-3 contact, and a
headless render pass of every sprite kind."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import math

import pygame
import pytest

from aphelion.game import sealife as sl
from aphelion.render import marine_art


# ---- determinism -------------------------------------------------------------

def test_populate_is_deterministic():
    a = sl.populate("core:europa", "site:x|sea", 200.0, 1000.0)
    b = sl.populate("core:europa", "site:x|sea", 200.0, 1000.0)
    assert [(e["kind"], round(e["x"], 4), round(e["z"], 4)) for e in a] == \
           [(e["kind"], round(e["x"], 4), round(e["z"], 4)) for e in b]
    # fresh dict objects each call (mutating one must not poison the next)
    if a:
        a[0]["x"] = -9999.0
        c = sl.populate("core:europa", "site:x|sea", 200.0, 1000.0)
        assert c[0]["x"] != -9999.0


def test_no_python_hash_in_source():
    """13 §1.1: randomness must derive from zlib.crc32, never hash()."""
    import inspect
    src = inspect.getsource(sl)
    assert "hash(" not in src
    assert "zlib.crc32" in src


def test_different_cells_differ():
    here = sl.populate("core:europa", "site:x|sea", 200.0, 100.0)
    far = sl.populate("core:europa", "site:x|sea", 200.0, 5000.0)
    assert ([e["kind"] for e in here], len(here)) != \
           ([e["kind"] for e in far], len(far)) or here != far


# ---- ocean / ladder gating ---------------------------------------------------

def test_no_sea_no_entities():
    assert sl.populate("core:mars", "site:jezero", 50.0, 10.0) == []
    assert sl.ocean_of("core:moon") is None


def test_titan_is_methane_no_motile_life():
    """Hard realism: liquid methane at 94 K hosts NO motile animals — a
    Titan dive can yield Tier 0/1 only, never a Tier-2 swarm."""
    assert sl.ocean_of("core:titan") == "methane"
    tiers = set()
    for cell in range(0, 400):
        ents = sl.populate("core:titan", "site:titan_shore|sea",
                           260.0, cell * sl.CELL_W_M + 5.0)
        tiers.update(e["tier"] for e in ents)
    assert 2 not in tiers
    assert 1 in tiers                       # biosignatures DO occur


def test_water_oceans_can_have_motile_life():
    found = False
    for cell in range(0, 400):
        ents = sl.populate("core:europa", "site:europa|sea",
                           240.0, cell * sl.CELL_W_M + 5.0)
        if any(e["kind"] == "filter_swarm" for e in ents):
            found = True
            break
    assert found


def test_depth_bands_gate_tiers():
    assert sl.depth_band(10.0) == "shallow"
    assert sl.depth_band(100.0) == "mid"
    assert sl.depth_band(220.0) == "deep"
    # vents/swarms only appear deep
    shallow_kinds = set()
    for cell in range(0, 200):
        for e in sl.populate("core:europa", "site:e|sea", 30.0,
                             cell * sl.CELL_W_M + 5.0):
            shallow_kinds.add(e["kind"])
    assert "filter_swarm" not in shallow_kinds
    assert "vent_chimney" not in shallow_kinds


def test_discovery_dsc_mapping():
    assert sl.DSC_BY_BODY["core:titan"] == "dsc14"
    assert sl.DSC_BY_BODY["core:europa"] == "dsc11"
    assert sl.DSC_BY_BODY["core:enceladus"] == "dsc12"


# ---- sonar vs. identification ------------------------------------------------

def _find(body, site, depth, kind, cells=600):
    for cell in range(cells):
        for e in sl.populate(body, site, depth, cell * sl.CELL_W_M + 5.0):
            if e["kind"] == kind:
                return e
    raise AssertionError(f"no {kind} spawned")


def test_tier0_vent_is_sonar_only_no_science():
    """Abiotic vents are gorgeous and sonar-paintable but pay no
    science (they are Tier 0 spectacle, not a biosignature)."""
    chim = _find("core:europa", "site:e|sea", 240.0, "vent_chimney")
    assert chim["tier"] == 0 and chim["sci"] == 0.0
    ev = sl.step([chim], 0.1, chim["x"] - 8.0, chim["z"],
                 lights_on=True, rtg_we=0.0)
    assert any(e[0] == "sonar_contact" for e in ev)
    assert not any(e[0] == "discovery" for e in ev)


def test_sonar_fires_before_visual_id():
    """A sonar blip (acoustic, long range) precedes the visual ID of a
    Tier-2 school (needs the headlights and a close approach)."""
    sw = _find("core:europa", "site:e|sea", 240.0, "filter_swarm")
    # park the sub 100 m away: inside sonar range, outside ID range
    sx, sz = sw["x"] - 100.0, sw["z"]
    ev = sl.step([sw], 0.1, sx, sz, lights_on=True, rtg_we=330.0)
    kinds = [e[0] for e in ev]
    assert "sonar_contact" in kinds
    assert "discovery" not in kinds
    # close to ID range -> discovery fires once
    sx2 = sw["x"] - 10.0
    ev2 = sl.step([sw], 0.1, sx2, sw["z"], lights_on=True, rtg_we=330.0)
    assert any(e[0] == "discovery" for e in ev2)
    ev3 = sl.step([sw], 0.1, sw["x"] - 10.0, sw["z"], lights_on=True,
                  rtg_we=330.0)
    assert not any(e[0] == "discovery" for e in ev3)   # once only


def test_visual_id_requires_lights():
    sw = _find("core:europa", "site:e|sea", 240.0, "filter_swarm")
    sx = sw["x"] - 8.0
    dark = sl.step([sw], 0.1, sx, sw["z"], lights_on=False, rtg_we=0.0)
    assert not any(e[0] == "discovery" for e in dark)
    lit = sl.step([sw], 0.1, sw["x"] - 8.0, sw["z"], lights_on=True,
                  rtg_we=0.0)
    assert any(e[0] == "discovery" for e in lit)


def test_microbial_mat_needs_uv():
    mat = _find("core:europa", "site:e|sea", 240.0, "microbial_mat")
    sx = mat["x"] - 8.0
    no_uv = sl.step([mat], 0.1, sx, mat["z"], lights_on=True,
                    rtg_we=0.0, uv_on=False)
    assert not any(e[0] == "discovery" for e in no_uv)
    assert mat["glow"] is False
    uv = sl.step([mat], 0.1, sx, mat["z"], lights_on=True,
                 rtg_we=0.0, uv_on=True)
    assert mat["glow"] is True
    assert any(e[0] == "discovery" and e[1] == 1 for e in uv)


def test_chem_gradient_is_sensor_no_light():
    cg = _find("core:europa", "site:e|sea", 200.0, "chem_gradient")
    sx = cg["x"] - 5.0
    ev = sl.step([cg], 0.1, sx, cg["z"], lights_on=False, rtg_we=0.0)
    disc = [e for e in ev if e[0] == "discovery"]
    assert disc and disc[0][1] == 1 and disc[0][3] == "dsc11"


def test_discovery_pays_science_by_tier():
    assert sl.SCI_BY_TIER[1] < sl.SCI_BY_TIER[2] < sl.SCI_BY_TIER[3]
    swarm = _find("core:europa", "site:e|sea", 240.0, "filter_swarm")
    sx = swarm["x"] - 5.0
    ev = sl.step([swarm], 0.1, sx, swarm["z"], lights_on=True,
                 rtg_we=0.0)
    disc = [e for e in ev if e[0] == "discovery"]
    assert disc and disc[0][1] == 2 and disc[0][2] == sl.SCI_BY_TIER[2]


# ---- Tier-2 swarm behaviour --------------------------------------------------

def test_swarm_scatters_from_headlights():
    swarm = _find("core:europa", "site:e|sea", 240.0, "filter_swarm")
    cx0, cz0 = swarm["x"], swarm["z"]
    # sub sits right on the school with lights blazing
    for _ in range(40):
        sl.step([swarm], 0.1, cx0, cz0, lights_on=True, rtg_we=0.0)
    spread = max(math.hypot(m["x"] - cx0, m["z"] - cz0)
                 for m in swarm["members"])
    assert spread > 1.0          # the school fled the cone


def test_swarm_creeps_toward_rtg_warmth_in_dark():
    swarm = _find("core:europa", "site:e|sea", 240.0, "filter_swarm")
    # sub off to one side, lights OFF, hot RTG: school should drift in
    sub_x = swarm["x"] + 25.0
    sub_z = swarm["z"]
    d0 = abs(swarm["x"] - sub_x)
    for _ in range(120):
        sl.step([swarm], 0.1, sub_x, sub_z, lights_on=False,
                rtg_we=330.0)
    d1 = abs(swarm["x"] - sub_x)
    assert d1 < d0               # warmth drew them closer


def test_swarm_members_stay_finite():
    swarm = _find("core:europa", "site:e|sea", 240.0, "filter_swarm")
    for _ in range(200):
        sl.step([swarm], 0.2, swarm["x"] + 10, swarm["z"],
                lights_on=True, rtg_we=330.0)
    for m in swarm["members"]:
        assert math.isfinite(m["x"]) and math.isfinite(m["z"])
        assert math.hypot(m["vx"], m["vz"]) <= sl.SWARM_SPEED + 1e-6


# ---- Tier-3 THE CONTACT ------------------------------------------------------

def test_contact_only_deep_water_once():
    # not in shallow water
    assert sl.maybe_contact("core:europa", "site:e|sea", 50.0, 0.0, 1,
                            "seed-1", seen=False) is None
    # not in methane (Titan)
    assert sl.maybe_contact("core:titan", "site:t|sea", 250.0, 0.0, 1,
                            "seed-1", seen=False) is None
    # not if already seen
    assert sl.maybe_contact("core:europa", "site:e|sea", 250.0, 0.0, 1,
                            "seed-1", seen=True) is None
    # find a seed/cell where it does spawn
    got = None
    for cx in range(0, 4000, 80):
        got = sl.maybe_contact("core:europa", "site:e|sea", 250.0,
                               float(cx), 1, "seed-1", seen=False)
        if got is not None:
            break
    assert got is not None and got["tier"] == 3
    assert got["detect"] == "sonar" and got["id_range"] == 0.0
    assert sl.is_first(got)


def test_contact_paces_then_reveals_first():
    c = None
    for cx in range(0, 4000, 80):
        c = sl.maybe_contact("core:europa", "site:e|sea", 250.0,
                             float(cx), 1, "seed-7", seen=False)
        if c is not None:
            sub_x = float(cx)
            break
    assert c is not None
    # first sonar blip but NO reveal yet
    ev0 = sl.step([c], 0.1, sub_x, 250.0, lights_on=True, rtg_we=330.0)
    assert any(e[0] == "sonar_contact" and e[1] == "moving" for e in ev0)
    assert not any(e[0] == "discovery" for e in ev0)
    # keep the sub deep & near: dwell accrues, then the FIRST fires once
    fired = []
    for _ in range(int(sl.CONTACT_REVEAL_DWELL_S / 0.1) + 20):
        ev = sl.step([c], 0.1, sub_x, 250.0, lights_on=True,
                     rtg_we=330.0)
        fired += [e for e in ev if e[0] == "discovery"]
    assert len(fired) == 1
    assert fired[0][1] == 3 and fired[0][2] == sl.SCI_BY_TIER[3]
    # it never closed to visual ID range — stays a silhouette
    assert sl._dist(c, sub_x, 250.0) > sl.ID_RANGE_M


def test_contact_dwell_resets_if_sub_leaves():
    c = None
    for cx in range(0, 4000, 80):
        c = sl.maybe_contact("core:europa", "site:e|sea", 250.0,
                             float(cx), 1, "seed-7", seen=False)
        if c is not None:
            sub_x = float(cx)
            break
    # surface the sub (shallow) — dwell must not accumulate to a reveal
    for _ in range(int(sl.CONTACT_REVEAL_DWELL_S / 0.1) + 40):
        sl.step([c], 0.1, sub_x, 40.0, lights_on=True, rtg_we=330.0)
    assert not c["reveal"]


# ---- doctrine: ambiguous organics only (F34) ---------------------------------

def test_chronicle_text_holds_the_line():
    swarm = _find("core:europa", "site:e|sea", 240.0, "filter_swarm")
    txt = sl.chronicle_text(swarm).lower()
    assert "alien" not in txt
    # every tier 1-3 readout carries an abiotic / unconfirmed caveat
    for tier in (1, 2, 3):
        e = {"kind": "contact" if tier == 3 else "chem_gradient",
             "tier": tier}
        low = sl.chronicle_text(e).lower()
        assert any(w in low for w in ("abiotic", "unconfirmed",
                                      "uncertain", "not excluded",
                                      "artefact"))


# ---- renderer (headless) -----------------------------------------------------

def test_every_sprite_kind_renders_headless():
    pygame.init()
    surf = pygame.Surface((640, 360))
    cam = {"x0": 1000.0, "depth": 240.0, "ppm": 6.0,
           "cx": 320.0, "cy": 150.0}
    beam = {"x": 320.0, "y": 150.0, "dir": 1, "reach": 180.0,
            "half": 60.0}
    ents = []
    for cell in range(80):
        ents += sl.populate("core:europa", "site:e|sea", 240.0,
                            1000.0 + cell)
    c = None
    for cx in range(0, 4000, 80):
        c = sl.maybe_contact("core:europa", "site:e|sea", 250.0,
                             float(cx), 1, "seed-7", seen=False)
        if c is not None:
            break
    if c is not None:
        c["x"], c["z"] = 1000.0 + 30.0, 244.0
        ents.append(c)
    # turn the UV on so mats glow, and step once so state settles
    sl.step(ents, 0.1, 1000.0, 240.0, lights_on=True, rtg_we=330.0,
            uv_on=True)
    marine_art.draw_backscatter(surf, beam, 1.0)
    marine_art.draw_entities(surf, ents, cam, beam, 1.0)
    # something was actually painted (not an all-black frame)
    arr = pygame.surfarray.array3d(surf)
    assert arr.sum() > 0


def test_glow_sprite_cached():
    a = marine_art._glow(8, (80, 200, 160))
    b = marine_art._glow(8, (80, 200, 160))
    assert a is b
    assert a.get_flags() & pygame.SRCALPHA


def test_beam_lit_zero_behind_sub():
    beam = {"x": 100.0, "y": 100.0, "dir": 1, "reach": 120.0,
            "half": 40.0}
    assert marine_art._beam_lit(beam, 50.0, 100.0) == 0.0    # behind
    assert marine_art._beam_lit(beam, 130.0, 100.0) > 0.0    # in cone
    assert marine_art._beam_lit(beam, 130.0, 400.0) == 0.0   # off-axis
