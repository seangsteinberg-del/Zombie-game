"""Zoom-layer camera and THE world->screen transform choke point (13 §3.7,
§3.13, §4.8 — binding).

The floating-origin rule: screen = (p_frame - cam_frame) * zoom * flip +
center, with the subtraction performed FIRST, in float64, in the camera's
SOI frame; only the resulting camera-local values may be narrowed to
float32. Done in the wrong order the error at Neptune is ~524 km * zoom —
the classic shaking-spacecraft bug. Layers are forbidden to roll their own
transform; this module is the single choke point (enforced by unit test).
"""

from __future__ import annotations

from enum import Enum

import numpy as np

ZOOM_STEP = 1.25                  # mouse-wheel step (13 §3.13)


class ZoomLayer(Enum):
    SYSTEM = "system"             # heliocentric schematic
    LOCAL = "local"               # focus-body SOI frame
    SITE = "site"                 # tile map (Phase 2)
    INTERIOR = "interior"         # habitat cells (Phase 3)


# z ranges in px/m (13 §4.8; SYSTEM floor lowered 2026-06-13 by user
# request — 1.6e-10 clipped Neptune's orbit at 1280 px, 6e-11 fits the
# whole system in ~45% of the frame)
LAYER_Z_RANGE: dict[ZoomLayer, tuple[float, float]] = {
    ZoomLayer.SYSTEM: (6.0e-11, 1e-6),
    ZoomLayer.LOCAL: (1e-7, 0.05),
    ZoomLayer.SITE: (0.5, 50.0),
    ZoomLayer.INTERIOR: (16.0, 128.0),
}

# SYSTEM <-> LOCAL hysteretic handoff (13 §4.8): -> LOCAL when the focus SOI
# subtends > 60 % of the screen; <- SYSTEM when < 40 %.
HANDOFF_TO_LOCAL_FRACTION = 0.60
HANDOFF_TO_SYSTEM_FRACTION = 0.40


class Camera:
    """Owns (frame_id, center in frame, zoom, layer). All values float64."""

    def __init__(self, width: int, height: int, frame_id: str,
                 zoom: float, layer: ZoomLayer = ZoomLayer.SYSTEM) -> None:
        self.width = int(width)
        self.height = int(height)
        self.frame_id = frame_id
        self.layer = layer
        self.zoom = float(zoom)
        self.cx = 0.0
        self.cy = 0.0
        self._clamp_zoom()

    # -- the choke point -------------------------------------------------

    def world_to_screen(self, x: float, y: float) -> tuple[float, float]:
        """Subtract first (float64, camera frame), then scale. +y world is up;
        screen y grows down."""
        sx = (x - self.cx) * self.zoom + 0.5 * self.width
        sy = 0.5 * self.height - (y - self.cy) * self.zoom
        return (sx, sy)

    def world_to_screen_np(self, points: np.ndarray) -> np.ndarray:
        """(N, 2) float64 frame positions -> (N, 2) float64 screen px. The
        subtraction happens here in float64; callers may narrow the RESULT."""
        pts = np.asarray(points, dtype=np.float64)
        out = np.empty_like(pts)
        out[:, 0] = (pts[:, 0] - self.cx) * self.zoom + 0.5 * self.width
        out[:, 1] = 0.5 * self.height - (pts[:, 1] - self.cy) * self.zoom
        return out

    def screen_to_world(self, sx: float, sy: float) -> tuple[float, float]:
        x = (sx - 0.5 * self.width) / self.zoom + self.cx
        y = (0.5 * self.height - sy) / self.zoom + self.cy
        return (x, y)

    # -- zoom & layers -----------------------------------------------------

    def _clamp_zoom(self) -> None:
        lo, hi = LAYER_Z_RANGE[self.layer]
        self.zoom = min(max(self.zoom, lo), hi)

    def zoom_in(self, steps: int = 1) -> None:
        self.zoom *= ZOOM_STEP ** steps
        self._clamp_zoom()

    def zoom_out(self, steps: int = 1) -> None:
        self.zoom /= ZOOM_STEP ** steps
        self._clamp_zoom()

    def follow(self, x: float, y: float) -> None:
        self.cx = float(x)
        self.cy = float(y)

    def reanchor(self, new_frame_id: str, cx: float, cy: float) -> None:
        """SOI/focus change: swap frames in one render frame (13 §3.7) —
        no visual pop because the subtraction is exact at the crossing."""
        self.frame_id = new_frame_id
        self.cx = float(cx)
        self.cy = float(cy)

    def update_system_local_handoff(self, focus_soi_radius_m: float,
                                    local_frame_id: str,
                                    system_frame_id: str) -> bool:
        """Hysteretic SYSTEM<->LOCAL handoff; z carries continuously (the
        ranges overlap). Returns True when the layer changed; the caller owns
        re-expressing the camera center into the new frame."""
        soi_px = 2.0 * focus_soi_radius_m * self.zoom
        frac = soi_px / min(self.width, self.height)
        if self.layer is ZoomLayer.SYSTEM and frac > HANDOFF_TO_LOCAL_FRACTION:
            self.layer = ZoomLayer.LOCAL
            self.frame_id = local_frame_id
            self._clamp_zoom()
            return True
        if self.layer is ZoomLayer.LOCAL and frac < HANDOFF_TO_SYSTEM_FRACTION:
            self.layer = ZoomLayer.SYSTEM
            self.frame_id = system_frame_id
            self._clamp_zoom()
            return True
        return False
