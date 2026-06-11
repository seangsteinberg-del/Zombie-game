"""Synthesized audio (91-15: pre-baked variants, no runtime DSP — we
pre-bake at startup from numpy; no asset files). Vacuum-silence realism is
honored by keeping cues UI-diegetic (cockpit sounds), never 'space noise'.

Depth update: STEREO out; a real event vocabulary (stage bang, docking
clunk, touchdown thud, explosion boom, ignition, soft warn vs hard
alarm, UI tick); a three-band engine rumble whose channel volumes ride
the live throttle every frame (zero runtime synthesis); and three
crossfading music moods — calm (Dm9 drift), tense (low-fifth pulse) and
warm (F-major lift) — picked by the active scene.
"""

from __future__ import annotations

import math

import numpy as np

_RATE = 22_050


def _stereo(wave: np.ndarray, vol: float) -> bytes:
    pcm = np.clip(wave * vol, -1.0, 1.0)
    pcm16 = (pcm * 32_767.0).astype(np.int16)
    return np.ascontiguousarray(
        np.column_stack((pcm16, pcm16))).tobytes()


class AudioCues:
    def __init__(self) -> None:
        self.ok = False
        self.muted = False
        self.master = 0.8
        self._music: dict = {}          # mood -> Channel
        self._music_target = "calm"
        self._music_vol: dict[str, float] = {}
        self._eng_ch: list = []
        self._eng_started = False
        try:
            import pygame
            pygame.mixer.init(frequency=_RATE, size=-16, channels=2)
            pygame.mixer.set_num_channels(20)
            self._snd = {
                "burn": self._tone([(90.0, 1.0)], 0.18, decay=14.0, vol=0.5),
                "blip": self._tone([(660.0, 1.0)], 0.06, decay=40.0, vol=0.25),
                "paid": self._tone([(440.0, 0.7), (880.0, 0.5)], 0.35,
                                   decay=6.0, vol=0.4),
                "soi": self._tone([(523.0, 0.6), (784.0, 0.6)], 0.5,
                                  decay=4.0, vol=0.4),
                "alarm": self._tone([(310.0, 1.0), (370.0, 0.8)], 0.4,
                                    decay=2.0, vol=0.4),
                # UI micro-feedback: cursor tick + soft refusal warn
                "tick": self._tone([(880.0, 1.0)], 0.03, decay=60.0,
                                   vol=0.08),
                "warn": self._tone([(600.0, 1.0)], 0.12, decay=18.0,
                                   vol=0.2),
                # event vocabulary (depth update)
                "ignition": self._noise_boom(1.2, 45.0, decay=2.6, vol=0.55),
                "stage": self._noise_boom(0.32, 110.0, decay=11.0, vol=0.45),
                "boom": self._noise_boom(0.95, 55.0, decay=3.2, vol=0.65),
                "thud": self._noise_boom(0.26, 70.0, decay=14.0, vol=0.5),
                "clunk": self._clunk(),
            }
            self.ok = True
        except Exception:
            self._snd = {}

    # -- synthesis helpers -----------------------------------------------

    @staticmethod
    def _tone(partials, seconds: float, decay: float, vol: float):
        import pygame
        t = np.linspace(0.0, seconds, int(_RATE * seconds), endpoint=False)
        wave = np.zeros_like(t)
        for freq, amp in partials:
            wave += amp * np.sin(2.0 * np.pi * freq * t)
        wave *= np.exp(-decay * t) / max(1.0, sum(a for _, a in partials))
        return pygame.mixer.Sound(buffer=_stereo(wave, vol))

    @staticmethod
    def _noise_boom(seconds: float, hz: float, decay: float, vol: float):
        """Brown-noise burst over a low sine — ignitions, staging, loss."""
        import pygame
        n = int(_RATE * seconds)
        rng = np.random.default_rng(int(hz * 1000) + n)
        brown = np.cumsum(rng.normal(0.0, 1.0, n))
        brown /= max(np.max(np.abs(brown)), 1e-9)
        t = np.linspace(0.0, seconds, n, endpoint=False)
        wave = (0.7 * brown + 0.5 * np.sin(2.0 * np.pi * hz * t))
        wave *= np.exp(-decay * t)
        return pygame.mixer.Sound(buffer=_stereo(wave, vol))

    @staticmethod
    def _clunk():
        """Docking capture: two low mechanical hits + a metallic ring."""
        import pygame
        seconds = 0.5
        n = int(_RATE * seconds)
        t = np.linspace(0.0, seconds, n, endpoint=False)
        wave = np.zeros(n)
        for t0, hz in ((0.0, 95.0), (0.09, 70.0)):
            env = np.exp(-26.0 * np.maximum(t - t0, 0.0))
            env[t < t0] = 0.0
            wave += env * np.sin(2.0 * np.pi * hz * (t - t0))
        wave += 0.25 * np.exp(-8.0 * t) * np.sin(2.0 * np.pi * 460.0 * t)
        return pygame.mixer.Sound(buffer=_stereo(wave, 0.5))

    @staticmethod
    def _rumble(center_hz: float, seed: int):
        """2 s looping band of amplitude-shaped brown noise. The |sin|
        window zeroes both ends, so the loop seam breathes instead of
        clicking."""
        import pygame
        seconds = 2.0
        n = int(_RATE * seconds)
        rng = np.random.default_rng(seed)
        brown = np.cumsum(rng.normal(0.0, 1.0, n))
        brown /= max(np.max(np.abs(brown)), 1e-9)
        t = np.linspace(0.0, seconds, n, endpoint=False)
        wave = brown * (0.55 + 0.45 * np.sin(2.0 * np.pi * center_hz * t))
        wave *= np.abs(np.sin(np.pi * t / seconds)) ** 0.5
        return pygame.mixer.Sound(buffer=_stereo(wave, 0.6))

    @staticmethod
    def _pad(voices, dur: float = 28.0):
        """Generative drone: detuned voices with breathing LFOs, windowed
        for a seamless loop."""
        import pygame
        t = np.linspace(0.0, dur, int(_RATE * dur), endpoint=False)
        wave = np.zeros_like(t)
        for f, amp, lfo in voices:
            env = 0.55 + 0.45 * np.sin(2.0 * np.pi * lfo * t + f)
            wave += amp * env * (np.sin(2.0 * np.pi * f * t)
                                 + 0.35 * np.sin(2.0 * np.pi * f * 1.005 * t))
        wave /= max(np.max(np.abs(wave)), 1e-9)
        wave *= 0.6 + 0.4 * np.sin(np.pi * t / dur)
        return pygame.mixer.Sound(buffer=_stereo(wave, 0.45))

    # -- engine rumble (volumes ride the throttle each frame) -------------

    def _ensure_engine(self) -> None:
        if not self.ok or self._eng_started:
            return
        try:
            import pygame
            bands = [self._rumble(50.0, 11), self._rumble(90.0, 23),
                     self._rumble(140.0, 37)]
            self._eng_ch = []
            for bi, snd in enumerate(bands):
                ch = pygame.mixer.Channel(bi)
                ch.play(snd, loops=-1)
                ch.set_volume(0.0)
                self._eng_ch.append(ch)
            self._eng_started = True
        except Exception:
            self._eng_ch = []

    def set_engine(self, throttle: float) -> None:
        """Per-frame: three noise bands keyed to the live throttle."""
        if not self.ok:
            return
        if throttle > 0.0:
            self._ensure_engine()
        if not self._eng_ch:
            return
        thr = max(0.0, min(1.0, throttle))
        g = 0.0 if self.muted else self.master
        vols = (thr, max(0.0, thr - 0.3) * 1.4, max(0.0, thr - 0.7) * 3.0)
        for ch, v in zip(self._eng_ch, vols):
            ch.set_volume(min(1.0, v) * 0.55 * g)

    # -- music moods -------------------------------------------------------

    _MOODS = {
        "calm": ((73.42, 0.9, 0.013), (110.0, 0.7, 0.021),
                 (174.61, 0.55, 0.017), (261.63, 0.35, 0.011),
                 (329.63, 0.22, 0.007)),
        "tense": ((36.71, 0.8, 0.05), (73.42, 0.9, 0.045),
                  (110.0, 0.6, 0.06), (220.0, 0.3, 0.05),
                  (293.66, 0.18, 0.04)),
        "warm": ((87.31, 0.85, 0.012), (130.81, 0.6, 0.018),
                 (174.61, 0.5, 0.015), (220.0, 0.4, 0.01),
                 (261.63, 0.3, 0.008)),
    }

    def start_music(self) -> None:
        """Bake the three pads, park each on its own looping channel, and
        let update() crossfade between them by scene mood."""
        if not self.ok or self._music:
            return
        try:
            import pygame
            for mi, (mood, voices) in enumerate(self._MOODS.items()):
                ch = pygame.mixer.Channel(4 + mi)
                ch.play(self._pad(voices), loops=-1)
                ch.set_volume(0.0)
                self._music[mood] = ch
                self._music_vol[mood] = 0.0
            self._music_vol["calm"] = 1.0
            self._apply_music_volume()
        except Exception:
            self._music = {}

    def set_mood(self, mood: str) -> None:
        if mood in self._MOODS:
            self._music_target = mood

    def update(self, dt: float) -> None:
        """Crossfade music toward the target mood (~2 s)."""
        if not self._music:
            return
        changed = False
        for mood in self._music:
            want = 1.0 if mood == self._music_target else 0.0
            cur = self._music_vol[mood]
            if abs(cur - want) > 1e-3:
                step = dt / 2.0
                self._music_vol[mood] = (min(cur + step, want) if want > cur
                                         else max(cur - step, want))
                changed = True
        if changed:
            self._apply_music_volume()

    def _apply_music_volume(self) -> None:
        g = 0.0 if self.muted else 0.45 * self.master
        for mood, ch in self._music.items():
            try:
                ch.set_volume(self._music_vol.get(mood, 0.0) * g)
            except Exception:
                pass

    # -- master ------------------------------------------------------------

    def set_master(self, v: float) -> float:
        self.master = max(0.0, min(1.0, v))
        self._apply_music_volume()
        return self.master

    def toggle_mute(self) -> bool:
        self.muted = not self.muted
        self._apply_music_volume()
        if self.muted:
            self.set_engine(0.0)
        return self.muted

    def play(self, name: str) -> None:
        if self.ok and not self.muted and name in self._snd:
            try:
                snd = self._snd[name]
                snd.set_volume(self.master)
                snd.play()
            except Exception:
                pass
