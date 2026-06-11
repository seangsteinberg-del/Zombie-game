# PROJECT "APHELION"

A single-player, 2D top-down, **hard-realism space survival/engineering sim** for PC,
built in Python 3.12 + pygame-ce.

> KSP's orbital flight × Oxygen Not Included's habitat engineering × Factorio's industry —
> played as one persistent engineer-founder campaign across a **real-scale solar system**,
> 2049 → ~2090+. No combat. No aliens. The antagonist is physics.

## The pitch

You found a cash-starved private space program in 2049 and spend four decades clawing it
off Earth: contracts and reusable boosters in LEO, ice mining at the lunar poles, the
nuclear-thermal push to Mars, metallic asteroids and Venus cloud cities, and finally the
outer planets — ending with a self-sufficient off-Earth civilization, an interstellar
precursor probe, or both.

Every number is real or honestly tagged. Engines are Merlins, RL10s, and NERVA derivatives
with published stats; Earth to LEO costs ~9,400 m/s; ISRU chemistry balances mass and
energy to the percent; heat must be radiated by the T⁴ law; cryogens boil off; crews take
real radiation dose. Anything beyond engineering-complete is labeled **[SPECULATIVE]** and
gated to the endgame tier. Tedium is defeated by exact million-fold time warp and
automation — never by shrinking the universe.

## Status

**PLAYABLE.** All six roadmap phases have their core systems built and
acceptance-tested (190+ pinned physics/sim tests, all green), and the campaign game
runs on top of them.

```
pip install pygame-ce numpy
python -m aphelion.main
```

**How to play:** you start in LEO with $150M and open contracts. `B` opens the
Builder — assemble a rocket from the 30-part canon catalog (live Δv/TWR), pay for it,
and it flies the real ascent sim to orbit; your design's remaining Δv is your mission
budget. `N` places a maneuver node (arrows shape it, `ENTER` arms, the burn
auto-executes). `X/Z/A/D` burn directly; `./,` run the warp ladder to 1,000,000×.
Ride an SOI handoff to the Moon, press `G` to found Peary Base, `F2` to watch its
ledger run — ice mining, electrolysis, equipment failures, repair bots. Contracts pay
out from Moon to Venus to Mars; crew accrue real radiation dose; `F1` is the tutorial.

Build for distribution: `pyinstaller aphelion.spec` → `dist/APHELION/`.

Sixteen domain design documents (~1.1 MB of canon) govern every number on screen; the
engine reproduces the bible's worked examples within 1% by test (Earth→Mars TMI,
ascent loss budgets, the Mars aerocapture corridor, lunar-night survival, the works).

## Where to start

- **[design/README.md](design/README.md)** — the master document: pitch and pillars,
  system map, reading order for all 16 docs, canonical glossary (tiers, acts, resources),
  the phase-by-phase build roadmap with definitions of done, the design risk register,
  and the bible-wide open-question list.
- `design/01-…13-*.md` — the core domain canon; `design/90-…92-*.md` — visual, audio,
  and comms direction.

*(Repository name "Zombie-game" is historical — there are no zombies here, only entropy.)*
