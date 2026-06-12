"""F0 GPU post-processing (16 §presentation, bar raised 2026-06-12).

The game keeps rendering every scene to a plain 1280x720 pygame Surface
exactly as before; when a GL 3.3 context is available that surface is
uploaded once per frame and a shader chain runs over it:

    frame -> bright-pass (quarter res) -> separable gaussian x2
          -> composite: split-tone world grade, true additive bloom,
             subtle chromatic aberration, GPU dither (anti-banding)

`GLPost.try_create()` returns None on ANY failure (headless dummy
driver, missing moderngl, ancient GPU, remote desktop) and the caller
falls back to the classic CPU path — the GL pass is presentation only,
never load-bearing. Shaders target #version 330 core (2010 baseline;
effectively 100% of the Steam hardware survey).
"""

from __future__ import annotations

import struct

import pygame

try:
    import moderngl
except Exception:                                   # pragma: no cover
    moderngl = None

_VERT = """#version 330 core
in vec2 in_pos;
out vec2 v_uv;
void main() {
    v_uv = in_pos * 0.5 + 0.5;
    gl_Position = vec4(in_pos, 0.0, 1.0);
}
"""

_BRIGHT_FRAG = """#version 330 core
uniform sampler2D u_tex;
uniform float u_thresh;
in vec2 v_uv;
out vec4 f_color;
void main() {
    vec3 c = texture(u_tex, v_uv).rgb;
    float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
    f_color = vec4(c * smoothstep(u_thresh, u_thresh + 0.18, l), 1.0);
}
"""

_BLUR_FRAG = """#version 330 core
uniform sampler2D u_tex;
uniform vec2 u_dir;            // (1/w, 0) or (0, 1/h)
in vec2 v_uv;
out vec4 f_color;
void main() {
    vec3 a = texture(u_tex, v_uv).rgb * 0.2270270270;
    vec2 o1 = u_dir * 1.3846153846;
    vec2 o2 = u_dir * 3.2307692308;
    a += (texture(u_tex, v_uv + o1).rgb + texture(u_tex, v_uv - o1).rgb)
         * 0.3162162162;
    a += (texture(u_tex, v_uv + o2).rgb + texture(u_tex, v_uv - o2).rgb)
         * 0.0702702703;
    f_color = vec4(a, 1.0);
}
"""

_COMPOSITE_FRAG = """#version 330 core
uniform sampler2D u_tex;
uniform sampler2D u_bloom;
uniform float u_bloom_str;
uniform vec3 u_tint_lo;        // shadows multiplier (split-tone)
uniform vec3 u_tint_hi;        // highlights multiplier
uniform float u_sat;
uniform float u_gamma;
uniform float u_ca;            // chromatic aberration strength
uniform float u_curve;         // filmic curve blend
uniform float u_time;
in vec2 v_uv;
out vec4 f_color;
void main() {
    vec2 c2 = v_uv - 0.5;
    vec2 off = c2 * dot(c2, c2) * u_ca;
    vec3 c;
    c.r = texture(u_tex, v_uv - off).r;
    c.g = texture(u_tex, v_uv).g;
    c.b = texture(u_tex, v_uv + off).b;
    c += texture(u_bloom, v_uv).rgb * u_bloom_str;
    // filmic S-curve (ACES approx), blended: deep blacks + creamy
    // highlights without crushing the UI text
    vec3 flm = (c * (2.51 * c + 0.03)) / (c * (2.43 * c + 0.59) + 0.14);
    c = mix(c, clamp(flm, 0.0, 1.0), u_curve);
    c = pow(max(c, 0.0), vec3(u_gamma));
    float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
    c = mix(vec3(l), c, u_sat);
    c *= mix(u_tint_lo, u_tint_hi, clamp(l, 0.0, 1.0));
    // hash dither, +-0.75/255: kills the banding the CPU path needed
    // int16 tricks for (see surface_art lesson)
    float n = fract(sin(dot(v_uv * vec2(12.9898, 78.233)
                            + vec2(u_time * 0.37), vec2(1.0, 1.0)))
                    * 43758.5453) - 0.5;
    c += n * (1.5 / 255.0);
    f_color = vec4(c, 1.0);
}
"""

# Per-world split-tone grades:
# (tint_lo, tint_hi, sat, gamma, bloom, ca, curve).
# Multipliers stay within ~10% — identity is mood, not Instagram.
_DEFAULT = ((1.00, 1.00, 1.02), (1.00, 1.00, 1.00),
            1.04, 1.00, 0.55, 0.006, 0.35)
GRADES: dict[str, tuple] = {
    "default": _DEFAULT,
    "menu":    ((0.98, 0.99, 1.04), (1.00, 1.00, 1.02),
                1.03, 1.00, 0.70, 0.008, 0.45),
    "earth":   ((0.99, 1.00, 1.03), (1.02, 1.01, 0.99),
                1.06, 0.99, 0.55, 0.006, 0.35),
    "moon":    ((0.96, 0.99, 1.06), (1.03, 1.02, 0.99),
                0.95, 1.02, 0.60, 0.006, 0.40),
    "mars":    ((1.05, 0.97, 0.92), (1.06, 1.00, 0.92),
                1.08, 0.99, 0.50, 0.006, 0.35),
    "venus":   ((1.04, 1.00, 0.90), (1.07, 1.04, 0.90),
                1.02, 1.00, 0.60, 0.007, 0.35),
    "mercury": ((0.98, 0.98, 1.00), (1.05, 1.04, 1.00),
                0.92, 1.05, 0.65, 0.006, 0.45),
    "titan":   ((1.06, 0.95, 0.82), (1.10, 1.01, 0.85),
                1.05, 1.03, 0.65, 0.007, 0.40),
    "europa":  ((0.94, 0.99, 1.10), (1.00, 1.02, 1.06),
                0.98, 1.01, 0.60, 0.006, 0.40),
    "ceres":   ((0.97, 0.99, 1.04), (1.02, 1.01, 1.00),
                0.96, 1.02, 0.55, 0.006, 0.35),
    "interior": ((1.03, 1.00, 0.96), (1.04, 1.02, 0.97),
                 1.04, 0.98, 0.50, 0.005, 0.30),
}
BLOOM_THRESH = 0.62


def grade_for(key: str) -> tuple:
    """Body ids arrive as "core:mars" — grade by the suffix."""
    return GRADES.get(key.rsplit(":", 1)[-1], _DEFAULT)


class GLPost:
    """Owns the OPENGL window + the post chain. Construct via try_create."""

    @staticmethod
    def try_create(logical_size: tuple[int, int],
                   vsync: bool = True) -> "GLPost | None":
        if moderngl is None:
            return None
        try:
            # Integer-upscale the window on HiDPI desktops (SCALED is
            # incompatible with OPENGL); the composite pass does the
            # filtering, which beats SDL's scaler anyway.
            try:
                dw, dh = pygame.display.get_desktop_sizes()[0]
                scale = max(1, min((dw - 80) // logical_size[0],
                                   (dh - 120) // logical_size[1]))
            except Exception:
                scale = 1
            win = (logical_size[0] * scale, logical_size[1] * scale)
            pygame.display.set_mode(
                win, pygame.OPENGL | pygame.DOUBLEBUF,
                vsync=1 if vsync else 0)
            ctx = moderngl.create_context(require=330)
            return GLPost(ctx, logical_size, win)
        except Exception:
            return None

    def __init__(self, ctx, logical_size: tuple[int, int],
                 window_size: tuple[int, int]) -> None:
        self.ctx = ctx
        self.size = logical_size
        self.window_size = window_size
        quad = struct.pack("8f", -1, -1, 1, -1, -1, 1, 1, 1)
        vbo = ctx.buffer(quad)

        self._p_bright = ctx.program(vertex_shader=_VERT,
                                     fragment_shader=_BRIGHT_FRAG)
        self._p_blur = ctx.program(vertex_shader=_VERT,
                                   fragment_shader=_BLUR_FRAG)
        self._p_comp = ctx.program(vertex_shader=_VERT,
                                   fragment_shader=_COMPOSITE_FRAG)
        self._va_bright = ctx.vertex_array(
            self._p_bright, [(vbo, "2f", "in_pos")])
        self._va_blur = ctx.vertex_array(
            self._p_blur, [(vbo, "2f", "in_pos")])
        self._va_comp = ctx.vertex_array(
            self._p_comp, [(vbo, "2f", "in_pos")])

        w, h = logical_size
        self._tex_frame = ctx.texture((w, h), 3)
        self._small = (max(1, w // 4), max(1, h // 4))
        self._tex_a = ctx.texture(self._small, 3)
        self._tex_b = ctx.texture(self._small, 3)
        for tex in (self._tex_frame, self._tex_a, self._tex_b):
            tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
            tex.repeat_x = tex.repeat_y = False
        self._fbo_a = ctx.framebuffer(color_attachments=[self._tex_a])
        self._fbo_b = ctx.framebuffer(color_attachments=[self._tex_b])

        self._p_bright["u_tex"].value = 0
        self._p_bright["u_thresh"].value = BLOOM_THRESH
        self._p_blur["u_tex"].value = 0
        self._p_comp["u_tex"].value = 0
        self._p_comp["u_bloom"].value = 1

    def present(self, frame: pygame.Surface, world_key: str = "default",
                frame_idx: int = 0) -> None:
        """Upload the finished software frame, run the chain, swap."""
        self._tex_frame.write(pygame.image.tobytes(frame, "RGB", True))

        self._fbo_a.use()
        self._tex_frame.use(0)
        self._va_bright.render(moderngl.TRIANGLE_STRIP)

        sw, sh = self._small
        for _ in range(2):
            self._fbo_b.use()
            self._tex_a.use(0)
            self._p_blur["u_dir"].value = (1.0 / sw, 0.0)
            self._va_blur.render(moderngl.TRIANGLE_STRIP)
            self._fbo_a.use()
            self._tex_b.use(0)
            self._p_blur["u_dir"].value = (0.0, 1.0 / sh)
            self._va_blur.render(moderngl.TRIANGLE_STRIP)

        tint_lo, tint_hi, sat, gamma, bloom, ca, curve = grade_for(world_key)
        self.ctx.screen.use()
        # window may have been resized (F11 desktop-fullscreen toggle)
        win = pygame.display.get_window_size()
        self.window_size = win
        self.ctx.viewport = (0, 0, win[0], win[1])
        self._tex_frame.use(0)
        self._tex_a.use(1)
        self._p_comp["u_bloom_str"].value = bloom
        self._p_comp["u_tint_lo"].value = tint_lo
        self._p_comp["u_tint_hi"].value = tint_hi
        self._p_comp["u_sat"].value = sat
        self._p_comp["u_gamma"].value = gamma
        self._p_comp["u_ca"].value = ca
        self._p_comp["u_curve"].value = curve
        self._p_comp["u_time"].value = float(frame_idx % 4096)
        self._va_comp.render(moderngl.TRIANGLE_STRIP)
        pygame.display.flip()

    def read_screen(self) -> pygame.Surface:
        """Back-buffer readback for --screenshot in GL mode."""
        w, h = self.window_size
        data = self.ctx.screen.read(viewport=(0, 0, w, h), components=3)
        return pygame.image.frombytes(data, (w, h), "RGB", True)
