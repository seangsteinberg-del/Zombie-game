"""Post-FX tests (90-14 §1, §3.3): nebula backdrop determinism and
coverage, bloom brighten/no-op behavior with zero size change, vignette
radial falloff and caching, SOI ring cache identity and radius cap."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from types import SimpleNamespace

import numpy as np
import pygame

from aphelion.render.postfx import (
    SOI_RING_MAX_RADIUS_PX,
    Bloom,
    Nebula,
    soi_ring,
    vignette,
)

pygame.init()

SIZE = (320, 180)


def _frame(neb: Nebula, cam=None) -> bytes:
    screen = pygame.Surface(SIZE, pygame.SRCALPHA)
    neb.draw(screen, cam)
    return pygame.image.tobytes(screen, "RGBA")


# ---- Nebula -----------------------------------------------------------------

def test_nebula_deterministic_same_seed():
    a = Nebula(SIZE, seed=7)
    b = Nebula(SIZE, seed=7)
    assert _frame(a) == _frame(b)


def test_nebula_different_seed_differs():
    assert _frame(Nebula(SIZE, seed=1)) != _frame(Nebula(SIZE, seed=2))


def test_nebula_covers_screen_and_parallax_shifts():
    neb = Nebula(SIZE, seed=2049)
    screen = pygame.Surface(SIZE, pygame.SRCALPHA)
    screen.fill((255, 0, 255, 255))                 # sentinel
    neb.draw(screen)
    arr = pygame.surfarray.array3d(screen)
    assert not np.any((arr[..., 0] == 255) & (arr[..., 1] == 0)
                      & (arr[..., 2] == 255))       # backdrop covers all
    assert int(arr[..., 2].min()) >= 10             # never pure black
    cam = SimpleNamespace(cx=3.0e8, cy=1.0e8, zoom=2.0e-5)
    assert _frame(neb, cam) != _frame(neb)          # parallax moved clouds
    assert _frame(neb, cam) == _frame(neb, cam)     # but deterministically


# ---- Bloom ------------------------------------------------------------------

def test_bloom_brightens_neighborhood_keeps_size():
    screen = pygame.Surface(SIZE, pygame.SRCALPHA)
    screen.fill((8, 10, 14, 255))
    pygame.draw.rect(screen, (255, 255, 255), pygame.Rect(156, 86, 8, 8))
    before = pygame.surfarray.array3d(screen).astype(np.int64)
    Bloom(SIZE).apply(screen)
    after = pygame.surfarray.array3d(screen).astype(np.int64)
    assert screen.get_size() == SIZE
    # the dark strip left of the bright rect picks up glow
    assert after[136:152, 82:98].sum() > before[136:152, 82:98].sum()


def test_bloom_dark_field_unchanged():
    screen = pygame.Surface(SIZE, pygame.SRCALPHA)
    screen.fill((20, 25, 30, 255))                  # all below threshold
    before = pygame.surfarray.array3d(screen).copy()
    Bloom(SIZE).apply(screen)
    assert np.array_equal(before, pygame.surfarray.array3d(screen))


def test_bloom_reuse_is_stateless_and_deterministic():
    bloom = Bloom(SIZE)

    def scene() -> pygame.Surface:
        s = pygame.Surface(SIZE, pygame.SRCALPHA)
        s.fill((8, 10, 14, 255))
        pygame.draw.circle(s, (200, 240, 255), (100, 90), 12)
        return s

    s1, s2 = scene(), scene()
    bloom.apply(s1)
    bloom.apply(s2)                                 # reused buffers
    assert (pygame.image.tobytes(s1, "RGBA")
            == pygame.image.tobytes(s2, "RGBA"))


# ---- vignette ---------------------------------------------------------------

def test_vignette_cached_radial_alpha():
    v1 = vignette(SIZE)
    assert vignette(SIZE) is v1                     # cache hit, same object
    assert v1.get_size() == SIZE
    assert v1.get_flags() & pygame.SRCALPHA
    alpha = pygame.surfarray.array_alpha(v1)
    cx, cy = SIZE[0] // 2, SIZE[1] // 2
    assert int(alpha[cx, cy]) <= 4                  # transparent center
    assert int(alpha[0, 0]) >= 40                   # dark corners
    assert int(alpha[0, 0]) > int(alpha[cx, cy])
    assert int(alpha.max()) <= 90                   # ~70-alpha, never opaque


# ---- soi_ring ---------------------------------------------------------------

def test_soi_ring_cached_faint_and_capped():
    ring = soi_ring(150)
    assert ring is not None
    assert soi_ring(150) is ring                    # cache hit, same object
    assert ring.get_flags() & pygame.SRCALPHA
    assert ring.get_size() == (308, 308)            # 2 * (r + 4px glow pad)
    alpha = pygame.surfarray.array_alpha(ring)
    assert 40 <= int(alpha.max()) <= 60             # faint (~50 peak)
    assert soi_ring(SOI_RING_MAX_RADIUS_PX + 1) is None
