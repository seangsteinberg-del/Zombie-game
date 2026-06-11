# PROJECT "APHELION" — v1.0

A single-player, 2D top-down, **hard-realism space program sim** for PC,
built in Python 3.12 + pygame-ce.

> KSP's orbital flight × Oxygen Not Included's habitat engineering × Factorio's
> industry — one persistent engineer-founder campaign across a **real-scale
> solar system**, 2049 onward. No combat. No aliens. The antagonist is physics.

## Install & run

```
pip install pygame-ce numpy
python -m aphelion.main
```

Build for distribution: `pip install pyinstaller && pyinstaller aphelion.spec`
→ `dist/APHELION/APHELION.exe`.

## The campaign

You found a cash-starved space program in 2049 with $150M, two astronauts, and
an empty launch pad. **Twenty-one contracts across four Acts** take you from
first orbit to the outer planets; the campaign is won by putting an
interstellar precursor probe on a hyperbolic solar orbit. Every step is paid
for in real propellant, real power, and real crew careers:

- **Build rockets** from a 35-part catalog of real engines (Merlins, RL10s,
  Raptors, NERVA derivatives) with live Tsiolkovsky/TWR readouts — then **fly
  the launch yourself**, KSP-style: ignition, max-q, staging, MECO,
  circularization. The autopilot flies the canon guidance program; the arrows
  hand you the stick. Losses are itemized in the post-flight report.
- **Run a fleet.** Every vessel persists with its actual tanks, stages, and
  crew. Burns drain propellant Tsiolkovsky-exact; staging happens mid-burn
  when a stage runs dry. Dock vessels (pilots cut the prox-ops cost),
  crossfeed a tanker into a depot, undock and fly on.
- **Land and build.** Five surveyed sites — the Peary crater rim, Jezero
  delta, the 55 km Venus cloud deck (gondola required), Ligeia Mare on Titan,
  the Conamara chaos on Europa — each with real descent/ascent Δv. Found
  bases and construct them module by module: ice drills, electrolysis,
  Sabatier methanation, solar wings scaled by real site sunlight, fission
  reactors. Production runs through an exact resource ledger with equipment
  failures and repairs, warp-invariant to 1,000,000×.
- **Spend crew careers.** Hire pilots, engineers, and scientists (skills have
  real mechanical effects). Radiation dose accrues by real location rates —
  Europa's surface ends a career in days. Life support is finite. People die
  if you get it wrong.
- **Research** thirteen tech nodes with Science (exploration) and Engineering
  Data (operations), unlocking habs, depots, reactors, the Venus gondola, and
  finally the fusion torch and the LONGSHOT probe.

## Controls

| | |
|---|---|
| `B` | vessel builder (UP/DOWN, ENTER add, S stage, L launch) |
| Launch | SPACE ignite/stage · SHIFT/CTRL throttle · Z/X max/cut · arrows pitch · P autopilot · C circularize · ESC revert |
| `X/Z` `A/D` | prograde/retrograde, radial burns (SHIFT = 100 m/s) |
| `N` | maneuver node (arrows shape, [/] time, ENTER arm) |
| `V` / click | switch command between vessels |
| `E` `U` `T` | dock · undock · crossfeed propellant |
| `G` | surface operations: land / relaunch / found base |
| `F2` | base operations + construction |
| `R` / `K` | research tree · crew roster & hiring |
| `TAB` / click | camera focus · `C` your craft · wheel zoom |
| `.` `,` | time warp to 1,000,000× · SPACE pause |
| `F5` `F9` | quicksave / quickload (autosaves every 5 min) |
| `F1` `F11` `M` | tutorial · fullscreen · mute |
| `ESC` | pause menu (save/load/volume/quit) |

## Engineering

Sixteen design documents (~1.1 MB of canon) govern every number on screen;
the engine reproduces the bible's worked examples by test — Earth→Mars
transfers within 1%, ascent loss budgets, the 1°-wide Mars aerocapture
corridor, 14-day lunar nights survived on stored oxygen, two-year
self-sufficiency audits. **311 pinned tests**, including a scripted
end-to-end campaign playthrough that wins the game. Start at
[design/README.md](design/README.md).
