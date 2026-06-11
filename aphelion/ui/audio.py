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
            }
            self.ok = True
        except Exception:
            self._snd = {}

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
                self._snd[name].play()
            except Exception:
                pass
