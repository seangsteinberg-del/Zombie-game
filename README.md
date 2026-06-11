# PROJECT "APHELION" — v2.0 · THE DEPTH UPDATE

A single-player, 2D top-down, **hard-realism space program sim** for PC,
built in Python 3.12 + pygame-ce. Every pixel procedural — no asset files.

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
- **Found drawn colonies** (`F2`): seeded terrain and day/night skies, one
  drawn structure per module with live status lights, residents walking
  between them. Founding pours your lander's tanks into the buffers and its
  crew become colonists; engineers speed repairs and raise output; banked
  ISRU propellant **refuels landers kg-for-kg**. Solar dies at night —
  batteries bridge, reactors don't care, radiators shed the heat.
- **Spend people carefully**: hire, train (+1 skill, 90 days grounded),
  watch dose careers end permanently, pay the casualty review when they do.
- **Research that grants**: 13 nodes including a flyable NTR engine, the
  fusion torch the precursor actually rides, and closed-loop ECLSS that
  stretches life support 2.5×. Science labs make the win provably affordable
  — a pinned test does the budget.

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
