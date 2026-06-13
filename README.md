# PROJECT "APHELION" — v3 · THE FULL BUILD-OUT

A single-player, 2D top-down, **hard-realism space program sim** for PC,
built in Python 3.12 + pygame-ce. Every pixel procedural — no asset files.

> KSP's orbital flight × Oxygen Not Included's habitat engineering × Factorio's
> industry — one persistent engineer-founder campaign across a **real-scale
> solar system**, 2049 onward. No combat. No aliens. The antagonist is physics.

v3 builds out the entire 16-document design bible into a playable whole: a
**cinematic "MISSION FILM" art direction** (a moderngl GPU post pass —
HDR bloom on emitters only, per-world color grades, film grain), a real
**launch campaign** (countdown holds, weather, radio chatter, anomaly
chains, swing-arm retract, deluge steam, a plume with mach diamonds that
feathers with altitude), **walkable everything** (surface EVA over diggable
tile worlds, living ship/station interiors where the crew sleep, eat, and
work at real stations, a colony command view that is just that same world
pulled back), **pilotable vehicles** (rovers across the V-law terrain
table, a submarine under Titan's living methane seas), a full **comms
network** with light-lag teleop, **aerocapture corridor advice** and
Lambert transfer windows, and a campaign meta-layer of Firsts, Prestige,
a Chronicle that remembers every milestone, and a four-class alarm grammar
that caps time-warp until you answer it.

## Install & run

```
pip install pygame-ce numpy
python -m aphelion.main
```

Build for distribution: `pip install pyinstaller && pyinstaller aphelion.spec`
→ `dist/APHELION/APHELION.exe`.

## The campaign

Pick a difficulty (CADET / DIRECTOR / HARDCORE — start funds, sponsor
patience, and a real monthly payroll all change), then take a cash-starved
2049 program from first orbit to an **interstellar precursor on a hyperbolic
solar orbit** across 21 contracts in four Acts. Blown deadlines get
re-negotiated at a haircut — setbacks, never dead saves. Early delivery pays
a bonus. The ledger (`O`) shows every payout and countdown.

- **Build in a real VAB** (`B`): categorized catalog with stats cards and per
  part pricing, mid-stack editing, stage splitting, blueprint slots, crew
  assignment before launch — and your rocket's real silhouette sets its real
  drag. Then **fly the launch**: engine rumble rides your throttle, clouds
  sweep past, max-q rattles the camera, staging bangs, and ESC only refunds
  inside a 20-second pad-scrub window.
- **Fly the map, not the dark**: right-click targets show encounters and
  closest approach; Ap/Pe markers, SOI crossing flags and per-frame leg
  colors make predictions readable; the node editor snaps to apsides and
  warps to the burn; the transfer planner (`P`) quotes every planet's next
  window from *your* parking orbit.
- **Land it yourself**: a low parking orbit, a deorbit burn, and a flown
  suicide-burn descent with a BURN-NOW ladder. Hit at over 3 m/s and the
  vehicle — and everyone aboard — is gone. Aero worlds adjudicate real entry
  heating against your stack first. Relaunches are flown off every body too.
- **Dock by hand**: pay the rendezvous match, then fly the
  Clohessy-Wiltshire approach on an LVLH radar — RCS pulses against a real
  budget, soft capture under 2 m/s, hot contact bounces. Pilots make it
  visibly cheaper, and can fly it for you.
- **One world, two cameras**: a landing site is a persistent side-view
  **tile cross-section** — strata, ore veins, ice lenses, the tunnels you
  dig. Walk it on foot (EVA, `G`), drive a rover across it, or pull the
  camera back (`F2`) for the colony command view — *the same world*, with
  modules on the real ground and a tunnel dug on foot visible from orbit.
  Founding pours your lander's tanks into the buffers and its crew become
  colonists. Solar dies at night — batteries bridge, reactors don't care.
- **Living interiors**: step inside a hab or board a stack and the crew are
  really living there — asleep in the bunks, on the exercise rack, at the
  science bench. `E` at a station cooks a morale-lifting shared meal, runs a
  medical scan, services a module, works a sample for science, or takes in a
  planet through the cupola. Needs (sleep, exercise in free-fall, hygiene,
  food) drive their condition for real.
- **The seas are alive**: take the submarine down through Titan's methane or
  Europa's ocean. Sonar paints the bathymetry; vent fields, fluorescing
  microbial mats (UV lamp), and — once per campaign, in the deep — a contact
  that paces the boat at the edge of the headlights and never quite resolves.
- **The network**: every vessel and base is a comms node. Watch your link
  rate and round-trip light-time home (`J` for the map), and learn why a
  rover on Mars *crawls* under teleop while one on the Moon does not.
- **Spend people carefully**: hire, train, watch dose careers end
  permanently. Every First — first orbit, first crewed landing, the Titan
  sub — pays out, earns Prestige, and is written into the **Chronicle** you
  can photograph (`F12`) and one day export as a mission-log.
- **Research that grants**: a 132-node tree including a flyable NTR engine,
  the fusion torch the precursor rides, and closed-loop ECLSS. Science labs
  make the win provably affordable — a pinned test does the budget.

## Controls (F1 in-game for the full table)

| | |
|---|---|
| `B` | builder — TAB stack focus, ◄► filters, ⇧S split, 1-6 blueprints, L launch |
| Launch | SPACE ignite/stage · SHIFT/CTRL throttle · X/Z max/cut · arrows pitch · P autopilot · C circularize · ESC revert (T+20s) |
| `X/Z` `A/D` | prograde/retrograde, radial burns (SHIFT = 100 m/s) |
| `N` | node — arrows dv (CTRL fine), [/] time (SHIFT hr, CTRL day), P/A snap, O +1 orbit, ENTER arm, `W` warp to burn |
| `P` / `O` | transfer-window planner · contract ledger |
| right-click | set navigation TARGET (encounter + closest approach on NAV) |
| `V` / click | switch command · `E` fly the docking approach · `U` undock · `T` crossfeed |
| Descent | SHIFT/CTRL throttle · A autoland (pilot) · watch the BURN ladder |
| `G` / `F2` | surface ops (land/relaunch/found/refuel/board) · colony scene |
| `R` / `K` | research · crew roster (ENTER trains) & hiring |
| `TAB`/click/wheel | camera focus & zoom · `.` `,` warp · SPACE pause |
| `F5` `F9` | quicksave / quickload (autosaves every 5 min) |
| `H` `F1` `M` `F11` | tutorial rail · help · mute · fullscreen |

## Engineering

Sixteen design documents (~1.1 MB of canon) govern every number on screen;
the engine reproduces the bible's worked examples by test — Earth→Mars
transfers within 1%, the 44° phase window, ascent loss budgets, entry
corridors, 14-day lunar nights survived on stored watt-hours. **355 pinned
tests**, including a scripted end-to-end campaign playthrough that wins the
game and a budget proof that the win is always affordable. Start at
[design/README.md](design/README.md).
