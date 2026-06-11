import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import time

import numpy as np
import pygame

pygame.init()
w, h = 1280, 720
sw, sh = 320, 180
tw, th = 160, 90
screen = pygame.Surface((w, h), pygame.SRCALPHA)
screen.fill((8, 10, 14, 255))
pygame.draw.circle(screen, (255, 255, 255), (640, 360), 40)
small = pygame.Surface((sw, sh), pygame.SRCALPHA)
tiny = pygame.Surface((tw, th), pygame.SRCALPHA)
half = pygame.Surface((w // 2, h // 2), pygame.SRCALPHA)
full = pygame.Surface((w, h), pygame.SRCALPHA)
lut = np.clip((np.arange(256) - 110) * 1.4069, 0, 255).astype(np.uint8)
sm = pygame.transform.smoothscale


def t(f, n=100):
    t0 = time.perf_counter()
    for _ in range(n):
        f()
    return (time.perf_counter() - t0) / n * 1e3


def thresh_lut():
    arr = pygame.surfarray.pixels3d(small)
    arr[...] = lut[arr]
    del arr


def thresh_buf():
    view = small.get_view("1")
    b = np.frombuffer(view, dtype=np.uint8)
    np.take(lut, b, out=b)
    del b, view


print("thresh LUT        %.2f" % t(thresh_lut))
print("thresh buf take   %.2f" % t(thresh_buf))


def full_apply_buf():
    sm(screen, (sw, sh), small)
    view = small.get_view("1")
    b = np.frombuffer(view, dtype=np.uint8)
    np.take(lut, b, out=b)
    del b, view
    sm(small, (tw, th), tiny)
    sm(tiny, (sw, sh), small)
    sm(small, (tw, th), tiny)
    sm(tiny, (sw, sh), small)
    sm(small, (w, h), full)
    screen.blit(full, (0, 0), special_flags=pygame.BLEND_ADD)


print("FULL apply buf    %.2f" % t(full_apply_buf))
print("small->half sm    %.2f" % t(lambda: sm(small, (w // 2, h // 2), half)))
print("half->full scale  %.2f" % t(lambda: pygame.transform.scale(half, (w, h), full)))
print("small->full sm    %.2f" % t(lambda: sm(small, (w, h), full)))


def full_apply():
    sm(screen, (sw, sh), small)
    arr = pygame.surfarray.pixels3d(small)
    arr[...] = lut[arr]
    del arr
    sm(small, (tw, th), tiny)
    sm(tiny, (sw, sh), small)
    sm(small, (tw, th), tiny)
    sm(tiny, (sw, sh), small)
    sm(small, (w // 2, h // 2), half)
    pygame.transform.scale(half, (w, h), full)
    screen.blit(full, (0, 0), special_flags=pygame.BLEND_ADD)


print("FULL apply        %.2f" % t(full_apply))


def full_apply_smooth_up():
    sm(screen, (sw, sh), small)
    arr = pygame.surfarray.pixels3d(small)
    arr[...] = lut[arr]
    del arr
    sm(small, (tw, th), tiny)
    sm(tiny, (sw, sh), small)
    sm(small, (tw, th), tiny)
    sm(tiny, (sw, sh), small)
    sm(small, (w, h), full)
    screen.blit(full, (0, 0), special_flags=pygame.BLEND_ADD)


print("FULL apply smooth %.2f" % t(full_apply_smooth_up))
