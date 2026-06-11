"""Synthesized audio cues (91-15: pre-baked variants, no runtime DSP — we
pre-bake at startup from numpy; no asset files). Vacuum-silence realism is
honored by keeping cues UI-diegetic (cockpit sounds), never 'space noise'.
"""

from __future__ import annotations

import numpy as np

_RATE = 22_050


class AudioCues:
    def __init__(self) -> None:
        self.ok = False
        self.muted = False
        self.master = 0.8
        self._music_chan = None
        try:
            import pygame
            pygame.mixer.init(frequency=_RATE, size=-16, channels=1)
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
            }
            self.ok = True
        except Exception:
            self._snd = {}

    def start_music(self) -> None:
        """Generative deep-space pad (91-15: synthesized, no assets): a
        slow Dm9 drone with detune shimmer and breathing LFOs, looped with
        matched endpoints so the seam is inaudible."""
        if not self.ok or self._music_chan is not None:
            return
        try:
            import pygame
            dur = 28.0
            t = np.linspace(0.0, dur, int(_RATE * dur), endpoint=False)
            wave = np.zeros_like(t)
            voices = ((73.42, 0.9, 0.013), (110.0, 0.7, 0.021),
                      (174.61, 0.55, 0.017), (261.63, 0.35, 0.011),
                      (329.63, 0.22, 0.007))
            for f, amp, lfo in voices:
                env = 0.55 + 0.45 * np.sin(2.0 * np.pi * lfo * t + f)
                wave += amp * env * (np.sin(2.0 * np.pi * f * t)
                                     + 0.35 * np.sin(2.0 * np.pi * f * 1.005 * t))
            wave /= np.max(np.abs(wave))
            wave *= 0.6 + 0.4 * np.sin(np.pi * t / dur)   # seamless seam
            pcm = (wave * 0.45 * 32_767.0).astype(np.int16)
            snd = pygame.mixer.Sound(buffer=pcm.tobytes())
            self._music_chan = snd.play(loops=-1)
            self._apply_music_volume()
        except Exception:
            self._music_chan = None

    def _apply_music_volume(self) -> None:
        if self._music_chan is not None:
            self._music_chan.set_volume(
                0.0 if self.muted else 0.45 * self.master)

    def set_master(self, v: float) -> float:
        self.master = max(0.0, min(1.0, v))
        self._apply_music_volume()
        return self.master

    def toggle_mute(self) -> bool:
        self.muted = not self.muted
        self._apply_music_volume()
        return self.muted

    @staticmethod
    def _tone(partials, seconds: float, decay: float, vol: float):
        import pygame
        t = np.linspace(0.0, seconds, int(_RATE * seconds), endpoint=False)
        wave = np.zeros_like(t)
        for freq, amp in partials:
            wave += amp * np.sin(2.0 * np.pi * freq * t)
        wave *= np.exp(-decay * t) * vol / max(1.0, sum(a for _, a in partials))
        pcm = (wave * 32_767.0).astype(np.int16)
        return pygame.mixer.Sound(buffer=pcm.tobytes())

    def play(self, name: str) -> None:
        if self.ok and not self.muted and name in self._snd:
            try:
                snd = self._snd[name]
                snd.set_volume(self.master)
                snd.play()
            except Exception:
                pass
