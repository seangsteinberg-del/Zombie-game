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

**Design bible complete · pre-code.**

Sixteen domain design documents (~1.1 MB of canon) cover orbital mechanics, propulsion,
the solar system database, ISRU, industry and logistics, ship and base construction, life
support, power and thermal, vehicles, research, gameplay/economy/UI, technical
architecture, visuals, audio, and communications. Implementation has not started; the
build roadmap runs Phase 0 (orbital sandbox) through Phase 7 (release hardening).

## Where to start

- **[design/README.md](design/README.md)** — the master document: pitch and pillars,
  system map, reading order for all 16 docs, canonical glossary (tiers, acts, resources),
  the phase-by-phase build roadmap with definitions of done, the design risk register,
  and the bible-wide open-question list.
- `design/01-…13-*.md` — the core domain canon; `design/90-…92-*.md` — visual, audio,
  and comms direction.

*(Repository name "Zombie-game" is historical — there are no zombies here, only entropy.)*
