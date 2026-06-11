# BUILD SPEC — 03 Solar System & Celestial Bodies

Extracted from `design/03-solar-system.md` (DRAFT v1, 730 lines). Conflicts resolved per `design/DECISIONS.md`
(binding rulings referenced inline: A2 owning-doc-wins, A3 decaying GCR floor, A4 piecewise-exact radiation,
C17 Venus crewed surface T4 trophy, C24 Mars ±50% density, F32 Appendix-A timeline canon, F34 no aliens ever).
Game epoch t = 0 is **2049-01-01 00:00 UTC**. Units SI; `d` = heliocentric distance in AU. Rule codes S-1…S-14.

---

## 1. BODY DATABASE

### 1.1 Master physical table (§4.1 — 37 curated bodies)

g and v_esc shown are published reference values; **engine MUST derive g = GM/R², v_esc = √(2GM/R) from stored GM+R**
(derived values for fast rotators: Jupiter 25.9 m/s² / 60.2 km/s, Saturn 11.2/36.1, Uranus 9.0/21.4, Neptune 11.3/23.6,
Bennu 8.2e-5 m/s²; unit tests assert against derived, not the column). T_rot negative = retrograde spin.
Radiation = unshielded ambient mSv/day (S-8); LC = landing class (S-7b).

| Body | R [km] | GM [km³/s²] | g [m/s²] | v_esc [km/s] | T_rot | Atmosphere (P0, gases, H) | T range [K] | Radiation [mSv/d] | r_SOI [km] | LC | Key resources | Δv surf↔LO (indicative; 01 owns) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Sun | 695,700 | 1.32712e11 | 274 | 617.5 | 25.4 d | — | — | — | — | — | — | not landable |
| Mercury | 2,439.7 | 22,032 | 3.70 | 4.25 | 58.646 d (solar day 176 d) | exosphere ~1e-12 kPa | 100–700 (PSR ~50) | 1.8·f_cyc + 6.7× SPE | 1.12e5 | B | polar Water; Mg-silicate→Si/O2/Glass; S ~4 wt%; crustal Fe only 1.5–2 wt% | ≈3.2 |
| Venus | 6,051.8 | 324,859 | 8.87 | 10.36 | −243.02 d (solar day 116.8 d) | 9,200 kPa CO2 96.5/N2 3.5; H 15.9 km <30 km / 5.5 above | 737 surf; 293–350 @50–56 km | 0.03 (52 km) | 6.16e5 | E surf / D cloud | CO2, N2 atm; basalt | aerostat→orbit ≈8.3 |
| Earth | 6,371.0 | 398,600 | 9.81 | 11.19 | 23.934 h | 101.325 kPa N2 78.1/O2 20.9/Ar 0.9; H 8.5 km | 184–330 (mean 288) | 0.01 surf; belts S-8c | 9.24e5 | — | everything, at a price | 9.4 incl losses (canon) |
| Moon | 1,737.4 | 4,902.8 | 1.62 | 2.38 | 27.322 d sync (solar day 29.53 d) | none | 95–390 eq; PSR 25–40 | 1.37 | 66,200 | B | PSR Water, ilmenite O2/Ti/Fe, anorthite Al/Si, KREEP Th/U, He3 [SPEC] | ≈1.9 |
| Mars | 3,389.5 | 42,828 | 3.71 | 5.03 | 24.623 h (sol 88,775 s) | 0.61 kPa datum CO2 96.0/Ar 1.93/N2 1.89; H 11.1 km | 130–308 (mean 210) | 0.67 | 5.77e5 | C | atm CO2, mid-lat ice, Fe-oxides, hydrates | ≈4.0 up / ~1 propulsive down |
| Phobos | 11.1 (27×22×18) | 7.11e-4 | 0.0057 | 0.011 | 7.66 h sync | none | 130–300 | 0.7 (Mars shadow) | ≈7.3 < R: dock only | A | Regolith; Water 0–5 wt% (world-gen roll) | dock, ≈5 m/s |
| Deimos | 6.2 | 9.8e-5 | 0.003 | 0.0056 | 30.3 h sync | none | 130–290 | 0.9 | ~9 | A | as Phobos | dock |
| Ceres | 469.7 | 62.6 | 0.28 | 0.51 | 9.07 h | transient H2O exosphere ~0 | 110–235 | 1.8·f_cyc | 77,000 | B | Water ice 20–45 wt%, ammoniated clays (Nitrogen), carbonates | ≈0.37 |
| Vesta | 262.7 | 17.3 | 0.25 | 0.36 | 5.342 h | none | 85–270 | 1.8·f_cyc | ~40,000 | B | basaltic Si/Al/IronSteel | ≈0.27 |
| Psyche | 111 | 1.53 | 0.12 | 0.16 | 4.196 h | none | 80–280 | 1.8·f_cyc | ≈18,400 | B | ~30–60 vol% metal: IronSteel, RareEarths (PGM) | ≈0.14 |
| Hygiea | 217 | 5.83 | 0.124 | 0.232 | 13.83 h | none | 100–250 | 1.8·f_cyc | ≈33,800 | B | C-type clays Water, Carbon | ≈0.18 |
| Jupiter | 69,911 | 1.26687e8 | 24.8* | 59.5* | 9.925 h | H2 89/He 11 (1-bar 165 K) | — | belts S-8c | 4.82e7 | F | Hydrogen, He3 [SPEC T4] | no surface |
| Io | 1,821.6 | 5,959.9 | 1.80 | 2.56 | 1.769 d sync | SO2 trace ~1e-9 kPa | 90–130 bg; hotspots 1,900 | ≈36,000 | 7,840 | B | sulfur, silicates (hazard showcase) | ≈2.0 |
| Europa | 1,560.8 | 3,202.7 | 1.31 | 2.02 | 3.551 d sync | O2 trace | 50–110 | 5,400 | 9,730 | B | Water (15–25 km shell / 60–150 km ocean) | ≈1.6 |
| Ganymede | 2,634.1 | 9,887.8 | 1.43 | 2.74 | 7.155 d sync | O2 trace | 70–152 | 80 (own B-field) | 24,350 | B | Water ice + rock | ≈2.0 |
| Callisto | 2,410.3 | 7,179.3 | 1.24 | 2.44 | 16.689 d sync | CO2 trace | 80–165 (mean 134) | 0.14 + GCR | 37,700 | B | Water ice 20–40 wt%; THE jovian base | ≈1.8 |
| Saturn | 58,232 | 3.79312e7 | 10.4* | 35.5* | 10.66 h | H2/He (1-bar 134 K) | — | 1.0 inside 8 R_S | 5.48e7 | F | Hydrogen, He3 [SPEC] | no surface |
| Titan | 2,574.7 | 8,978.1 | 1.35 | 2.64 | 15.945 d sync | 146.7 kPa N2 94.5/CH4 5; H≈20 km | 90–94 (93.7) | 0.01 (column 10,900 g/cm²) | ≈43,300 | D | Methane seas (+ethane [LUMPED]), N2, Water bedrock | ≈2.4 up; chute down ~free |
| Enceladus | 252.1 | 7.21 | 0.113 | 0.239 | 1.370 d sync | plume vapor ~0 | 33–145 (stripes ~197) | 1.0 | ≈490 | B | Water (plume + crust) | ≈0.18 |
| Uranus | 25,362 | 5.7939e6 | 8.87* | 21.3* | −17.24 h | H2/He/CH4 (1-bar 76 K) | — | 0.5 mild belts | 5.18e7 | F | Hydrogen, He3 [SPEC — classic target] | no surface |
| Titania | 788.9 | 228.3 | 0.37 | 0.76 | 8.706 d sync | none | 60–89 | 0.5 | ≈7,540 | B | Water ice, rock | ≈0.55 |
| Oberon | 761.4 | 192.4 | 0.33 | 0.71 | 13.46 d sync | none | 60–89 | 0.5 | ≈9,430 | B | Water ice, rock | ≈0.55 |
| Miranda | 235.8 | 4.4 | 0.079 | 0.193 | 1.413 d sync | none | 60–86 | 0.5 | ~500 | B | ice; Verona Rupes wonder | ≈0.15 |
| Neptune | 24,622 | 6.8365e6 | 11.15* | 23.5* | 16.11 h | ice giant (1-bar 72 K) | — | 0.5 mild belts | 8.66e7 | F | Hydrogen, He3 [SPEC] | no surface |
| Triton | 1,353.4 | 1,428 | 0.78 | 1.46 | 5.877 d sync **RETRO** | 0.0014–0.0019 kPa N2 | 38 | GCR | 12,000 | B | N2 ice, Water ice, CH4 frost; geysers | ≈1.0 |
| Pluto | 1,188.3 | 869.6 | 0.62 | 1.21 | 6.387 d sync w/ Charon | 0.0010–0.0013 kPa N2 | 33–55 (mean ~44) | GCR | 3.1e6 | B | N2/CH4/CO ices, Water bedrock | ≈0.85 |
| Charon | 606.0 | 105.9 | 0.288 | 0.59 | 6.387 d sync | none | 53 max | GCR | ≈8,440 | B | Water ice | ≈0.42 |
| Bennu | 0.245 | 4.9e-9 | 6e-5* | 2e-4* | 4.296 h | none | 240–330 | 1.8·f_cyc | dock | A | Water ~8 wt% phyllosilicates, Carbon, Nitrogen | dock + anchors |
| Ryugu | 0.448 | 3.0e-8 | 1.5e-4 | 3.7e-4 | 7.63 h | none | 230–330 | 1.8·f_cyc | dock | A | as Bennu | dock |
| Eros | 8.4 (34×11×11) | 4.46e-4 | 0.0059 | 0.0103 | 5.27 h | none | 170–310 | 1.8·f_cyc | dock | A | NiFe grains, Silicon | dock |
| Itokawa | 0.165 | 2.1e-9 | ~1e-4 | 1.7e-4 | 12.13 h | none | 200–330 | 1.8·f_cyc | dock | A | rubble regolith | dock |
| Apophis | 0.17 | 4.0e-9 | 1.4e-4 | 2.2e-4 | 30.6 h | none | 230–340 | 1.8·f_cyc | dock | A | S-type silicates; 2029 celebrity (Prestige) | dock |
| 67P | ~2.0 bilobed | 6.7e-7 | ~2e-4 | ~0.001 | 12.40 h | coma when active (S-13) | 130–230 | 1.8·f_cyc | dock | A | Water/CO2/CO ice, organics | dock; anchor p_fail 0.1 |
| Halley | ~5.5 (15×8×8) | ~1.5e-5 | ~4e-4 | ~0.002 | 52.8 h | strong coma near q | 130–350 | 1.8·f_cyc | dock | A | as 67P; 2061 prestige | dock; **retrograde rendezvous** |
| Arrokoth | ~9 (36 km binary) | ~3e-5 | ~1e-3 | ~0.003 | 15.9 h | none | 30–60 | GCR | dock | A | primordial ices, organics | dock |
| Eris | 1,163 | 1,108 | 0.82 | 1.38 | 15.8 d sync w/ Dysnomia | collapsed N2/CH4 frost | 30–55 | GCR | large | B | N2/CH4 ice | ≈0.95 |

\* published equatorial value incl. rotation — derive from GM/R per S-3.
Notes: g < 0.01 m/s² ⇒ permanent **dock mode** flag at world-gen (never recomputed live). Saturn rings = zone object (§1.8.16),
not particles. Io's 36,000 is absorbed-dose 36 Gy/day used as Sv ceiling [SIMPLIFIED].

### 1.2 Heliocentric orbital elements (§4.2 — J2000 propagated to 2049-01-01, frozen; i := 0 per S-2)

| Body | a [AU] | e | P | ϖ [deg] | M0 [deg] | dir | Notes |
|---|---|---|---|---|---|---|---|
| Mercury | 0.3871 | 0.2056 | 87.97 d | 77.5 | 337.4 | + | big e: flux/Δv vary per window |
| Venus | 0.7233 | 0.0068 | 224.70 d | 131.5 | 284.6 | + | |
| Earth | 1.0000 | 0.0167 | 365.26 d | 102.9 | 357.5 | + | reference |
| Mars | 1.5237 | 0.0934 | 686.98 d | 336.0 | 38.1 | + | e feeds Ls (S-9) |
| Vesta | 2.3615 | 0.089 | 3.63 yr | 255.0 | 169 [P] | + | |
| Ceres | 2.766 | 0.076 | 4.60 yr | 153.9 | 264 [P] | + | belt anchor |
| Psyche | 2.924 | 0.134 | 4.99 yr | 19.3 | 302 [P] | + | |
| Hygiea | 3.139 | 0.112 | 5.57 yr | 235.5 | 47 [P] | + | |
| Jupiter | 5.2044 | 0.0489 | 11.862 yr | 14.8 | 66.7 | + | trojan phasing ref |
| Saturn | 9.5826 | 0.0565 | 29.447 yr | 92.4 | 196.4 | + | |
| Uranus | 19.191 | 0.0472 | 84.02 yr | 171.0 | 352.2 | + | |
| Neptune | 30.07 | 0.0086 | 164.79 yr | 45.0 | 7.0 | + | resonance pair w/ Pluto |
| Pluto | 39.482 | 0.2488 | 247.94 yr | 224.1 | 86.0 | + | **canonical M0/ϖ give verified 18.3 AU min separation from Neptune over 495-yr cycle; world-gen must validate ≥ 12 AU or re-seed Pluto M0** |
| Eris | 67.9 | 0.44 | ~559 yr | 187.6 | 205 [P] | + | endgame |
| Arrokoth | 44.58 | 0.042 | ~298 yr | 333.3 | 316 [P] | + | |
| Eros | 1.458 | 0.223 | 1.76 yr | 123.1 | 110 [P] | + | |
| Bennu | 1.1264 | 0.2037 | 1.20 yr | 68.3 | 102 [P] | + | |
| Ryugu | 1.1896 | 0.1902 | 1.30 yr | 103.0 | 21 [P] | + | |
| Itokawa | 1.324 | 0.280 | 1.52 yr | 231.9 | 297 [P] | + | |
| Apophis | ~1.10 | ~0.19 | ~1.15 yr | 330.8 | 213 [P] | + | |
| 67P | 3.463 | 0.641 | 6.45 yr | 62.9 | 84 | + | q = 1.24 AU; M0 anchored to ~2047-07 perihelion |
| Halley | 17.83 | 0.967 | ~75 yr | 169.8 | 299.9 | **−** | retrograde; M0 = −(12.57/75.32)·360° so perihelion = 2061-07-28 |

[P] = provisional ±15°, replace via scripted Horizons pull at data entry.
**Procedural** (~218 bodies): belt a 2.1–3.3 AU e U(0,0.25) ×120 · NEA a 0.8–1.9 e U(0.05,0.45) ×60 · Jupiter trojans ×20
with **a := a_Jup, ϖ := ϖ_Jup, M0 := M0_Jup ± 60° + U(−15°,+15°)** (L4/L5 lock — random phase is NOT a trojan) ·
comets ×10 (a 3–4 AU, e 0.5–0.7) · KBOs ×8. ϖ, M0 ~ U(0°,360°) otherwise. Reject duplicates of curated bodies
within Δa < 0.01 AU ∧ Δe < 0.02.

### 1.3 Satellite elements (§4.3 — about primaries)

| Moon | Primary | a [km] | e | P | ϖ [deg] | M0 [deg] | dir | f_ecl = asin(R_p/a)/π |
|---|---|---|---|---|---|---|---|---|
| Moon | Earth | 384,400 | 0.0549 | 27.322 d | 318.2 [P] | 135.0 [P] | + | 0.005 (ignorable) |
| Phobos | Mars | 9,376 | 0.0151 | 7.654 h | 150.1 [P] | 40.0 [P] | + | **0.12** |
| Deimos | Mars | 23,463 | 0.0003 | 30.31 h | 0 | 200.0 | + | 0.046 |
| Io | Jupiter | 421,800 | 0.0041 | 1.769 d | 0 | 310.0 | + | 0.054 |
| Europa | Jupiter | 671,100 | 0.0094 | 3.551 d | 0 | 120.0 | + | 0.034 |
| Ganymede | Jupiter | 1,070,400 | 0.0013 | 7.155 d | 0 | 250.0 | + | 0.021 |
| Callisto | Jupiter | 1,882,700 | 0.0074 | 16.689 d | 0 | 85.0 | + | 0.012 |
| Enceladus | Saturn | 237,948 | 0.0047 | 1.370 d | 0 | 15.0 | + | 0.079 |
| Titan | Saturn | 1,221,870 | 0.0288 | 15.945 d | 185.7 [P] | 160.0 [P] | + | 0.015 |
| Miranda | Uranus | 129,390 | 0.0013 | 1.413 d | 0 | 295.0 | + | 0.063 |
| Titania | Uranus | 435,910 | 0.0011 | 8.706 d | 0 | 70.0 | + | 0.019 |
| Oberon | Uranus | 583,520 | 0.0014 | 13.46 d | 0 | 225.0 | + | 0.014 |
| Triton | Neptune | 354,759 | 0.000016 | 5.877 d | 0 | 330.0 | **−** | 0.022 (RETROGRADE, real) |
| Charon | Pluto | 19,596 | 0.0002 | 6.387 d | 0 | 0.0 | + | mutual tidal lock |

Convention: e < 0.01 ⇒ ϖ := 0, fixed canonical M0. **f_ecl rule (S-6b single source)**: multiplies solar availability
for ALL assets in the moon's SOI — orbiting AND landed — EXCEPT PSR/PEL sectors whose override replaces it (assert
mutual exclusion). Synchronous rotation ⇒ solar day = orbital period.

### 1.4 Atmosphere model (S-5a/b)

```
P(h) = P0·exp(−h/H)      ρ(h) = P(h)·μ/(R_gas·T(h))      R_gas = 8.314 J/(mol·K)
T(h) = max(T_min_strat, T0 − L·h)                          [single-layer SIMPLIFIED]
Above h_break: P continues from break pressure with H_upper until stored h_atm (drag cutoff; ρ = 0 above).
Winds: w_gust = w·(1 + 0.5·sin(2πt/τ_g)), τ_g = 600 s.
```

Complete per-body input set (§4.1b — a programmer needs nothing beyond this table):

| Body | P0 [kPa] | T0 [K] | μ [g/mol] | H [km] | h_break [km] | H_upper [km] | L [K/km] | T_min_strat [K] | **h_atm [km]** | ΔT_diurnal [K] | w [m/s] |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Venus | 9,200 | 737 | 43.45 | 15.9 | 30 | 5.5 (60-km anchor; band lookup overrides 45–65 km) | 7.7 | 230 | **350** | ≈0 | 66 (aerostat band) |
| Earth | 101.325 | 288 | 28.97 | 8.5 | 120 | 60 | 6.5 | 217 | **600** (LEO decay exists) | 10 | 8 |
| Mars | 0.61 | 210 | 43.34 | 11.1 | 100 | 25 | 2.5 | 130 | **250** | 70 default; ΔT = 100 − 40·dust_index | 7 clear / 25 storm |
| Titan | 146.7 | 93.7 | 28.0 | 20 | 300 | 65 | 1.0 (lowest 10 km) | 70 | **1,400** (Cassini thermosphere) | ≈2 | 0.5 |
| Triton | 0.0014–0.0019 | 38 | 28.0 | 14.5 | — | — | 0 | 38 | **800** | ≈0 | 5 |
| Pluto | 0.0010–0.0013 | 44 | 28.0 | 21 | — | — | 0 | 44 | **1,600** | ≈0 | 1 |

- **Venus band lookup overrides the exponential wherever defined** (45 km → entry interface). Aerostat bands (§1.8.2 table).
- Gas/ice giants: class F, entry-interface tables owned by 01/02.
- **Mars only**: ρ_Mars(h,t) = ρ_S5a(h) · f_climate(h,t), clamp [0.50, 1.50] (S-9a, §3.5 below — C24 contract).
- Pluto atmosphere collapse: P = P_2015 · exp((r_2015 − r)/2.5 AU) [SIMPLIFIED placeholder].
- Drag cutoff popping: ships parked below h_atm decay; UI must warn rather than silently decay in warp.

### 1.5 Radiation environment (S-8) — field model, evaluated per sim tick

**S-8a GCR**: `D_gcr = 1.8 · f_cycle(t)` mSv/day everywhere in free space (flat with distance at game fidelity).
`f_cycle = 1.0 − 0.35·cos(2π(t − t_max)/11 yr)` — 0.65 AT solar max, 1.35 at min; clamp to [0.65, 1.35].
Solar maxima ≈ 2057 and 2068 (±2 yr world-gen jitter); campaign opens in 2046-max declining phase.
Surface overrides (half-sky-is-rock already included): Earth 0.01 · Venus@52 km 0.03 · Titan 0.01 ·
Mars 0.67 · Moon 1.37. Shielding/biology owned by 08 (with DECISIONS A3 decaying floor past ~1,000 g/cm²).

**S-8b SPE**: Poisson, `λ = 0.5 + 3.5·max(0, cos(2π(t−t_max)/11 yr))` events/yr (4.0 at max, 0.5 at min).
Event dose at 1 AU free space: lognormal median 100 mSv, σ_ln = 1.2, **cap 2,000 mSv**, delivered over 6–48 h.
Scales 1/d² (Mercury ≈6.7×, Jupiter 0.037×). **Warning 30–60 min** game-time after flare flag → storm-shelter
mechanic (07/08); warp-block while SPE in progress with unsheltered crew.

**S-8c Earth belts** [SIMPLIFIED AP8/AE8; effective dose behind 5 g/cm² hull — labeled exception]:
piecewise in geocentric r [R_E]: 0 below 1.1 → linear to **150 mSv/day @ 1.6** (inner proton) → 10 @ 2.5 →
**50 @ 4.5** (outer electron) → 0 @ 8. Chem transit ~1–5 mSv/pass; SEP spiral = Sv-class (weeks).

**S-8c Jupiter** (DECISIONS A4: piecewise-exact log-linear through mission-literature anchors), r in R_J = 71,492 km:

```
D_jup(r) [mSv/day] = 36,000                          r ≤ 5.9      (Io clamp)
                     36,000·exp(−(r−5.9)/1.845)      5.9 < r ≤ 9.4
                      5,400·exp(−(r−9.4)/1.591)      9.4 < r ≤ 15.0
                        160·exp(−(r−15.0)/1.605)     15.0 < r ≤ 30
                          0                          r > 30
Total in SOI: D = D_gcr + D_jup(r).  Anchors EXACT: Io 36,000 · Europa 5,400 · Ganymede 160 ambient
(intrinsic B-field halves to 80 surface — only moon with one) · Callisto 0.14.
```

| Moon | r [R_J] | Surface dose | Unshielded survival | Verdict |
|---|---|---|---|---|
| Io | 5.9 | ≈36,000 (36 Gy/d) | hours | robots only, T4 sorties |
| Europa | 9.4 | 5,400 | ~1 day | bury ≥ 3 m ice; electronics fault roll 1/(30 d) unburied |
| Ganymede | 15.0 | 80 | weeks | shielded base viable T3 |
| Callisto | 26.3 | 0.14 + GCR | indefinite | THE crewed base (HOPE) |

**Saturn**: 1.0 mSv/day inside 8 R_S, 0 beyond (rings absorb); Titan at 21.0 R_S is outside entirely.
Uranus/Neptune mild belts 0.5. Mercury/Moon/asteroids: GCR + SPE only.

### 1.6 Procedural small-body physical generation (§4.1c — the ~218 procedural bodies)

| Property | Rule |
|---|---|
| Diameter D | N(>D) ∝ D^−2 truncated; belt [0.3, 30] km; NEA [0.1, 2]; trojans [1, 20]; comets [0.5, 5]; KBOs [10, 200] |
| Spectral class | belt C 60/S 30/M 10%; NEA C 40/S 55/M 5%; trojans → C; comets/KBOs fixed volatile class |
| Bulk density | C 1.3, S 2.4, M 4.5, comet 0.53, KBO 1.5 t/m³ |
| GM | G·(4/3)π(D/2)³·ρ, G = 6.674e-20 km³/(kg·s²); g, v_esc derived per S-3 |
| T_rot | U(2.2 h, 40 h); rubble D > 300 m never < 2.2 h (spin barrier S-11); monoliths < 300 m may roll to 0.1 h (DANGER flag) |
| Dock-mode | fixed flag at world-gen if g < 0.01 m/s² |
| Sectors | 1–3: C → REGOLITH_PILE/ICE_PLAIN; S/M → REGOLITH_PILE/HIGHLAND; comet → REGOLITH_PILE neck/lobe split; KBO → ICE_PLAIN |
| Deposits/anomalies | per 04 §4.2 class tables; anomaly slots per S-10 probabilities |

### 1.7 Sector model (S-7) — record schema, defaults, landing classes

```
Sector { id, body, φ_center [deg], arc_deg,
         terrain_class ∈ {MARE, HIGHLAND, DUNE, ICE_PLAIN, CHAOS, VOLCANIC, PSR, SEA, CLOUD_BAND, REGOLITH_PILE},
         slope_sigma [deg], rock_abundance [0..1], T_day/T_night [K], dust_index [0..1],
         deposit_rolls → 04 §4.2 refs, anomaly_slots [0..3], landing_class ∈ {A..F}, region_id (§2.4),
         flags: PSR | PEL | SEA-assignment | hotspot | storm-flagged | heritage-zone }
```

**Layout**: sectors laid CCW from prime meridian in §1.8 list order; sector i of N: arc_deg = 360/N,
φ_center = 360·(i + 0.5)/N unless overridden. ~176 curated sectors total, specified as defaults + inline overrides:

| terrain_class | slope_sigma | rock_abund | dust_index | anomaly_slots | T_day/T_night default |
|---|---|---|---|---|---|
| MARE | 2 | 0.10 | 0.4 | 1 | body T-max / T-min |
| HIGHLAND | 6 | 0.25 | 0.3 | 1 | (max − 10) / min |
| DUNE | 4 | 0.05 | 0.9 | 1 | max / min |
| ICE_PLAIN | 3 | 0.10 | 0.1 | 1 | max / min |
| CHAOS | 12 | 0.45 | 0.1 | 2 | max / min |
| VOLCANIC | 8 | 0.35 | 0.2 | 2 | max / min (+S-11 hotspot events) |
| PSR | 8 | 0.20 | 0.1 | 1 | PSR floor both (I = 0 always) |
| SEA | 0 | 0.00 | 0.0 | 1 | body mean both |
| CLOUD_BAND | — | — | 0.0 | 1 | band T from §1.8.2 |
| REGOLITH_PILE | 15 | 0.60 | 0.8 | 1 | max / min |

Atmosphere bodies ignore T_day/T_night columns: use T_mean ± ΔT_diurnal/2 (§1.4 table; Mars ΔT = 100 − 40·dust_index).

**S-7b landing classes + EDL dispersion**: A airless g < 0.05 (dock, anchor) · B airless rockets-only ·
C thin atmo (Mars: shield + retropropulsion) · D thick benign (Titan: chutes suffice) · E extreme (Venus surface) ·
F no surface. Touchdown offset ~ N(0, σ) along sector arc, σ_base: **B 0.2 km, C 5 km, D 20 km**;
storms ×2 (S-9); comet activity ×(1 + 0.2·A) (S-13). 01 consumes σ.

**S-7c site maps**: landing instantiates a procedural top-down tile map seeded by (body, sector, slot);
slope obstacles ∝ slope_sigma, rocks ∝ rock_abundance, deposit overlay from 04 M-1a, anomaly tiles if discovered.
Persistent once instantiated.

### 1.8 Per-body surface sector maps (§4.4 — names in canonical CCW order; defaults per §1.7 + listed overrides)

**1.8.1 Mercury (10)** — Act 4–5 energy forge; imports ore, exports refined mass (mass driver T3).
1 Caloris Basin (VOLCANIC, Si/Glass feed) · 2 Pantheon Fossae "the Spider" (anomaly AN-21) · 3 Borealis PSR-N (PSR, Water) ·
4 Kandinsky PSR-N (PSR, Water, anomaly slot) · 5 South PSR (PSR, Water) · 6 Hollows Terrain (sulfide/volatile lag, AN-22) ·
7–8 Intercrater Plains ×2 (HIGHLAND, Si/Regolith) · 9 Smooth Plains (MARE analog; Fe 1.5–2 wt% low-grade only) ·
10 Discovery Rupes (wonder scarp). PSR ice 1e14–1e15 kg (Prokofiev/Kandinsky class); terminator chase 3.6 km/h (§3.4).

**1.8.2 Venus (8 surface + 4 cloud bands)** — cloud colony; surface class E (pre-T3 probe drops, 2–8 h survival).
Surface: 1 Maxwell Montes (wonder, "metal frost" snowline, AN-19) · 2 Maat Mons (ACTIVE volcano — S-11 logic at 1/(180 d), AN-20) ·
3 Beta Regio (Venera 9/10) · 4 Phoebe Regio (Venera 13/14, AN-17) · 5 Baltis Vallis (6,800 km lava channel wonder) ·
6 Lakshmi Planum · 7 Aphrodite Terra (tessera, survey jackpot) · 8 Lowland Plains (Vega 1/2).
Cloud bands (CLOUD_BAND sectors; VIRA anchored; +0.15 below-cloud albedo bonus for 2-sided arrays):

| Band | Alt [km] | P [kPa] | T [K] | f_atm | Notes |
|---|---|---|---|---|---|
| V-Cloud-Low | 48–50 | 107–135 | 348–366 | 0.30 | max lift, heavy acid |
| V-HAVOC | 50–52 | 81–107 | 330–348 | 0.45 | design point |
| V-Temperate | 52–56 | 45–81 | 293–330 | 0.55 | shirt-sleeve T |
| V-Cloud-Top | 56–62 | 17–45 | 263–293 | 0.70 | best solar, worst UV/acid |

Hazards: H2SO4 degrades exposed Polymers 1%/day unless acid-rated (T2); < 45 km T > 380 K electronics kill;
clamp aerostat sim 45–65 km, destructive < 42 km. Super-rotation: circumnavigation ≈ 6 d ⇒ 3 d light / 3 d dark.
Water: ~5 g/t processed cloud air (aerosol) + ~30 ppm vapor cracking — bulk water imported.

**1.8.3 Earth (12)** — KSC-analog equatorial spaceport · high-latitude spaceport (differ by weather-scrub p and logistics
cost; rotation bonus global in 2D) · Atacama observatory (SurveyData bonus) · Iceland geothermal park ·
Australian mass-driver site (T3) · 7 scenery/market regions (12 owns economy stats). Debris bands LEO 400–1,200 km +
GEO graveyard: collision p = 0.0005/asset-yr [SIMPLIFIED Kessler]; hurricane scrub p = 0.02/launch-window.

**1.8.4 Moon (14)** — 1 Mare Tranquillitatis (high-Ti; AN-01 Apollo 11 + Surveyor 5; pit anomaly) · 2 Oceanus Procellarum
(KREEP Th/U; Luna 9/13, AN-04) · 3 Mare Imbrium (Lunokhod 1 AN-03, Chang'e 3) · 4 Taurus-Littrow (Apollo 17 AN-02;
pyroclastic He3 [SPEC]) · 5 Aristarchus Plateau (pyroclastic glass, wonder) · 6 Marius Hills (lava tube AN-06) ·
7 Highlands Near N (anorthite Al/Si) · 8 Highlands Near S · 9 Tycho (wonder) · 10 South Pole Shackleton (**PEL** + PSR
cluster; AN-07) · 11 Cabeus PSR (**PSR**; AN-05 LCROSS, 5.6±2.9 wt% water) · 12 North Pole PSR (**PSR**; Hermite ~25 K) ·
13 Far-side Highlands (radio-quiet: SurveyData ×1.5; Chang'e 4 AN-50) · 14 South Pole–Aitken Basin (survey jackpot).
Night 14.77 d; dust k_env = 0.04 (same class as Mars); micrometeoroid p = 0.001/asset-yr.

**1.8.5 Mars (18)** — 1 Chryse (Viking 1 AN-08, Pathfinder) · 2 Utopia (Viking 2 + Zhurong AN-09) · 3 Elysium (InSight) ·
4 Gale (Curiosity AN-12) · 5 Gusev (Spirit) · 6 Meridiani (Opportunity AN-10, Schiaparelli, hematite Fe) ·
7 Jezero/Isidis (Perseverance + Ingenuity + MSR cache AN-11; Beagle 2) · 8 Arabia (hydrated minerals) ·
9 Tharsis Rise (geothermal anomaly candidates) · 10 Olympus Mons (**f_dust exponent ×0.5** above dust; wonder AN-14) ·
11 Valles Marineris (wonder AN-15; floor **pressure +20%**, wind-sheltered flag) · 12 Hellas (−7.1 km, **P 1.16 kPa** —
best aero margin, worst dust) · 13 Argyre (hosts AN-13 Mars 3, folded from Terra Sirenum) · 14 Arcadia mid-lat ice N
(SWIM 30–90 wt% ice < 1 m overburden; AN-16) · 15 Deuteronilus ice N · 16 Mid-lat ice S · 17 Polar Cap N (layered H2O +
seasonal CO2 frost) · 18 Medusae Fossae (**dust_index 1.0**, BasaltFiber feed). Perchlorate toxicity flag (04/08).

**1.8.6 Phobos (3)** — Stickney interior (radiation shadow +0.35 shielding factor) · grooved terrain · sub-Mars point
(comms relay flag; AN-24 Phobos 2 + MMX). **Deimos (2)** — smooth saddle · cratered north. Both dock-mode;
Phobos f_ecl 0.12; blasting prohibited (drill-only, 04 M-6); Water 0–5 wt% world-gen roll (survey reveals).

**1.8.7 Ceres (8)** — Occator faculae (wonder AN-25; brine reservoir at ~40 km depth — **deep brine = T3 drilling
megaproject**, shallow ice routine) · Ahuna Mons (wonder) · Kerwan basin (ice-rich) · Equatorial dark plains (clays,
Nitrogen) · N polar PSR-analog craters (cold-trap ice, S-6b) · S highlands · Urvara basin · Juling crater (seasonal ice).
Light lag 13–30 min ⇒ autonomy rules; solar 130–180 W/m² (arrays ×8 Earth area).

**1.8.8 Vesta (6)** — Rheasilvia basin + 22 km peak (wonder) · Marcia (pitted volatile terrain) · Divalia Fossae ·
Cratered highlands N · Cratered highlands S · Dark-material unit (Carbon).

**1.8.9 Psyche (5)** — Metal-rich plains W (wonder) · Metal-rich plains E (wonder) · Meteorite-breccia terrain ·
Crater Panthia (grade ground truth) · Regolith-covered south (lower grade). Orbiter survey resolves 30–70 wt% IronSteel
grade — the Act 4 economic reveal.

**1.8.10 Belt classes** (procedural ×120): C 60% (Water 5–20 wt%, Carbon, Nitrogen) · S 30% (Si, IronSteel grains
5–20 wt%) · M 10% (IronSteel 30–70 wt% high variance, RareEarths PGM 10–100 ppm). Belt transit empty — collision risk 0.

**1.8.11 Io (8)** — Loki Patera (AN-35, 200-km lava lake) · Pele · Tvashtar · Prometheus plume field ·
2× sulfur plains · 2× polar mountains (Boösaule ~17 km, wonder). All VOLCANIC sectors: eruption Poisson 1/(30 d),
plumes 300–400 km, ejecta strike p = 0.02/event on assets in sector. Geothermal taps [SPEC T4, 100 kWt cap].

**1.8.12 Europa (8)** — Conamara Chaos (AN-33, brine lenses 1–3 km) · Thera/Thrace Macula · 2× ridge plains ·
lineae band · Pwyll impact · 2× polar plains. Melt-probe megaproject → EUR-OCEAN region (AN-34, 200 GB).
Surface: electronics fault roll 1/(30 d) unless buried.

**1.8.13 Ganymede (10)** — Galileo Regio (dark ancient) · Uruk Sulcus (grooved) · 4× terrain-pair repeats ·
2× polar caps (frost) · Enki Catena (AN-36) · Tros (bright ray).

**1.8.14 Callisto (10)** — Valhalla center + 2 ring arcs (AN-37) · Asgard basin · 4× cratered plains (ice 20–40 wt%) ·
2× knobby erosion terrain. Staging capital of the outer system.

**1.8.15 Titan (12)** — Kraken Mare (SEA, ≈400,000 km²) · Ligeia Mare (SEA, ≈126,000 km²) · Punga Mare (SEA) ·
Shangri-La dune field (DUNE, Carbon/Polymers) · Adiri (AN-38 Huygens) · Selk crater (AN-39 Dragonfly) ·
Xanadu (Water-ice bedrock) · Sotra Patera (AN-40 cryovolcano) · 2× polar lake districts (seasonal) ·
2× equatorial plains. Methane rain events: sector weather flag, optics f = 0.5 for U(5,20) d. Flight trivial
(ρ 5.3 kg/m³, g 1.35). O2 is the scarce commodity. k_env = 0.03, maintenance ×1.5. Solar f_atm 0.10 (~1.5 W/m² noon).

**1.8.16 Enceladus (6)** — 4× tiger-stripe vents Damascus/Baghdad/Cairo/Alexandria (each wonder AN-41; vent capture
≤ 5 kg/s/collector; stripe T ~197 K) · cratered north · sub-Saturn plains. Plume total 200 kg/s; sub-100 km plume fly-through
= free SurveyData, no erosion. **Saturn rings (zone object, not sectors)**: C 74,658–92,000 km · B 92,000–117,580 ·
Cassini Division · A 122,170–136,775; >95% Water ice, cm–10 m. Ring mining T3: ṁ = 2.0 t/h · ρ_zone
(B 1.0, A 0.6, C 0.3), hull wear 0.1%/h.

**1.8.17 Miranda (4)** — Verona Rupes (AN-45, 5–10 km scarp) · 2× chevron coronae · cratered plains.
**Titania (4)** — Messina Chasmata (wonder) · Gertrude crater · 2× cratered plains.
**Oberon (3)** — Hamlet crater · S limb mountain ~11 km (wonder) · cratered plains. Catalog depth only.

**1.8.18 Triton (6)** — S polar cap (AN-46 geysers, N2 ice) · cantaloupe terrain (wonder) · 2× equatorial plains ·
N plains · Mahilani plume site. Geysers = benign S-11 events (8 km plumes, SurveyData). N2 frost = last big
Nitrogen reservoir after Earth/Titan/Ceres. Retrograde rendezvous penalty applies.

**1.8.19 Pluto (6)** — Sputnik Planitia (AN-47, N2 glacier mega-deposit) · al-Idrisi mountains (AN-48) ·
Cthulhu Macula (tholins, Carbon) · Wright Mons (cryovolcano) · N polar · far-side plains.
**Charon (4)** — Mordor Macula · Serenity Chasma (wonder) · 2× plains.

**1.8.20 Comets (2–3 each)** — active neck/lobe REGOLITH_PILE split (67P-style). 67P: Abydos (AN-42 Philae) +
Ma'at (AN-43 Rosetta). Halley: AN-44 2061 event. Density ~533 kg/m³: anchor p_fail 0.1.

**1.8.21 KBOs** — Arrokoth (AN-49) and Eris: dock-mode primordial archives, SurveyData ×2 "pristine" multiplier (GB only, never X).

---

## 2. ANOMALIES & DISCOVERIES

Classes: DERELICT (real hardware, fixed) · WONDER (real geology) · COLDTRAP · TUBE · EVENT.
No aliens (F34). Rewards: SurveyData GB (+2 SCI/GB on-site investigation, one-shot), salvage mass, Prestige.

### 2.1 Curated catalog (§4.5 — 50 entries)

| ID | Body / Sector | Class | Find | Reward |
|---|---|---|---|---|
| AN-01 | Moon / Mare Tranquillitatis | DERELICT | Apollo 11 descent stage, flag, EASEP | 50 GB, Prestige ×3, heritage zone (no mining < 10 km) |
| AN-02 | Moon / Taurus-Littrow | DERELICT | Apollo 17 + LRV | 50 GB; preserve-or-salvage Prestige choice |
| AN-03 | Moon / Mare Imbrium | DERELICT | Lunokhod 1 (retroreflector still works) | 30 GB; free nav-beacon upgrade |
| AN-04 | Moon / Oceanus Procellarum | DERELICT | Luna 9 (first soft landing) | 30 GB, Prestige |
| AN-05 | Moon / Cabeus PSR | COLDTRAP | LCROSS scar + 5.6 wt% ice truth | instant K2 on sector Water deposit |
| AN-06 | Moon / Marius Hills | TUBE | skylight, intact tube ≥ 60 m | buried base: 07 cost −40%, radiation ×0.05 |
| AN-07 | Moon / South Pole | DERELICT | Chandrayaan-3 + Artemis hardware | 20 GB, 2 t MachineParts |
| AN-08 | Mars / Chryse | DERELICT | Viking 1 | 40 GB; 0.5 kg Pu238 (decayed ~55%) |
| AN-09 | Mars / Utopia | DERELICT | Viking 2 + Zhurong | 40 GB, Pu238 as AN-08 |
| AN-10 | Mars / Meridiani | DERELICT | Opportunity (2018 dust death) | 35 GB; real τ telemetry plaque |
| AN-11 | Mars / Jezero | DERELICT | Perseverance + Ingenuity + sample depot | 60 GB; sample-retrieval contract (Act 3 jackpot) |
| AN-12 | Mars / Gale | DERELICT | Curiosity (MMRTG ~2.6 kg Pu-238 left by 2049) | 40 GB, Pu238 salvage (09 refurb efficiency) |
| AN-13 | Mars / Argyre (Terra Sirenum) | DERELICT | Mars 3 (first Mars soft landing) | 30 GB |
| AN-14 | Mars / Olympus Mons | WONDER | 21.9 km summit above dust | f_dust exponent ×0.5, Prestige |
| AN-15 | Mars / Valles Marineris | WONDER | 4,000 km canyon | floor pressure +20%, wind-sheltered flag |
| AN-16 | Mars / Arcadia | COLDTRAP | SWIM ice lens < 1 m | instant K2 Water; site-recommendation event |
| AN-17 | Venus / Phoebe Regio | DERELICT | Venera 13 | 40 GB; T3 capsule-recovery trophy contract |
| AN-18 | Venus / cloud bands | DERELICT | Vega 1/2 balloon gondolas | 25 GB drifting-intercept minigame |
| AN-19 | Venus / Maxwell Montes | WONDER | semiconductor "frost" snowline | 30 GB; RareEarths trace unlock |
| AN-20 | Venus / Maat Mons | WONDER+EVENT | active volcano | 40 GB live-vent; eruption events |
| AN-21 | Mercury / Pantheon Fossae | WONDER | "the Spider" graben | 30 GB |
| AN-22 | Mercury / Hollows | WONDER | volatile-sublimation pits | 25 GB; sulfide lag-deposit unlock |
| AN-23 | Mercury / Suisei Planitia | DERELICT | MESSENGER impact scar | 15 GB |
| AN-24 | Phobos / sub-Mars point | DERELICT | Phobos 2 + MMX hardware | 30 GB; comms-relay flag |
| AN-25 | Ceres / Occator | WONDER | Cerealia Facula over 40-km brine | 40 GB; T3 deep-brine megaproject unlock |
| AN-26 | Ceres / orbit | DERELICT | Dawn orbiter | 20 GB, 10 kg Xenon |
| AN-27 | Bennu | WONDER | Nightingale TAG scar (no hardware) | 25 GB; sector deposits → K2 |
| AN-28 | Eros | DERELICT | NEAR Shoemaker | 25 GB |
| AN-29 | Heliocentric ~1.3 AU | DERELICT | Tesla Roadster + Starman | 15 GB, meme Prestige; 1 t Polymers |
| AN-30 | Heliocentric | DERELICT | Apollo 10 LM "Snoopy" | 35 GB, Prestige ×2 |
| AN-31 | Earth orbit | DERELICT | Vanguard 1 (1958) | 20 GB; retrieve = Prestige ×2 or in-situ heritage bonus |
| AN-32 | Earth orbit | DERELICT | Envisat (8 t) | 6 t StructuralParts/Electronics; removes debris penalty tick |
| AN-33 | Europa / Conamara | WONDER | brine lens 1–3 km | melt-probe precursor; 60 GB |
| AN-34 | Europa / ocean | WONDER | melt-probe ocean contact (abiotic chemistry) | **200 GB campaign jackpot** |
| AN-35 | Io / Loki Patera | WONDER | overturning lava lake | 50 GB at 1/(30 d) eruption risk |
| AN-36 | Ganymede / Enki Catena | WONDER | 13-crater chain | 25 GB |
| AN-37 | Callisto / Valhalla | WONDER | 3,800-km multi-ring basin | 30 GB; base-site flag |
| AN-38 | Titan / Adiri | DERELICT | Huygens | 50 GB, Prestige ×2 |
| AN-39 | Titan / Selk | DERELICT | Dragonfly (silent since 2039) | 40 GB; rotor salvage → 10 Titan-flyer blueprint discount |
| AN-40 | Titan / Sotra Patera | WONDER | cryovolcano candidate | 35 GB |
| AN-41 | Enceladus / 4 sulci | WONDER | tiger-stripe vents (each) | 4 × 30 GB; vent-capture sites |
| AN-42 | 67P / Abydos | DERELICT | Philae | 35 GB; anchoring-failure codex |
| AN-43 | 67P / Ma'at | DERELICT | Rosetta | 30 GB |
| AN-44 | Halley | EVENT | 2061-07-28 perihelion | 100 GB once; retrograde-rendezvous achievement |
| AN-45 | Miranda / Verona Rupes | WONDER | 5–10 km cliff | 40 GB; lowest-g descent stunt Prestige |
| AN-46 | Triton / S polar cap | WONDER | active N2 geysers | 40 GB |
| AN-47 | Pluto / Sputnik Planitia | WONDER | convecting N2 glacier | 60 GB; Nitrogen mega-deposit unlock |
| AN-48 | Pluto / al-Idrisi | WONDER | floating water-ice rafts | 30 GB |
| AN-49 | Arrokoth | WONDER | pristine contact binary | 50 GB ×2 pristine |
| AN-50 | Moon / far side | DERELICT | Chang'e 4 + Yutu 2 | 30 GB |

### 2.2 Procedural anomaly generator (S-10)

Each sector has 0–3 anomaly slots; curated entries fill listed slots; remaining roll at world-gen:
P(lava tube) = 0.06 (Moon/Mars; ×2 in VOLCANIC sectors) · P(ice lens COLDTRAP) = 0.10 (mid-lat bands) ·
P(geode/ore vug) = 0.08 (grants +1 grade tier to one deposit) · else empty.
Curated 50+; **target ≈ 110 anomalies per campaign**. Heritage-zone re-roll rule: procedural deposits never place
a K2-mandatory deposit only inside a heritage zone.

### 2.3 SurveyData yields (§4.6) & SCI conversion

| Class | Yield [GB] |
|---|---|
| Flyby first (per body) | 10 |
| Orbit survey complete (L1) | 20·√(R/1,000 km), min 5 |
| Sector prospect (L2) | 8 per sector |
| DERELICT | 15–60 (table) |
| WONDER | 25–60 (table) |
| Jackpots | 100–200 (Europa ocean, Halley 2061) |

**2 SCI per GB** on-site anomaly investigation, one-shot per anomaly (canonical, co-signed 11 §3.5) — range 30–400 SCI.
GB remain tradeable (12 §4.3: E-12 subscription $0.2M/GB); selling does NOT forfeit the SCI lump.
Non-anomaly rows carry NO implicit SCI (11 §3.5 owns survey/traverse Science — no double count).

### 2.4 Science regions & exoticism X (§4.7 — sectors carry region_id; IDs stable across saves)

| Body | Regions : members | X |
|---|---|---|
| Earth | EAR-ORB-LEO ≤ 2,000 km · EAR-ORB-HIGH · EAR-SURF (12) | 1 · 1.5 · 1 |
| Moon | MOO-ORB · MOO-NEAR (9 near sectors) · MOO-FARPOLE (Shackleton, Cabeus, N-Pole PSR, Far-side, SPA) | 2 · 2 · 4 |
| Mercury | MER-ORB · MER-SURF (7 non-PSR) · MER-PSR (3 PSR) | 6 · 7 · 8 |
| Venus | VEN-ORB · VEN-CLOUD (4 bands) · VEN-SURF (8) | 6 · 6 · 8 |
| Mars | MAR-ORB · MAR-SURF (18) | 5 · 5 |
| Phobos/Deimos | PHO-SURF (3) · DEI-SURF (2) | 5 · 5 |
| NEAs | one SURF per body (C/S 4; procedural M-type 5) | 4–5 |
| Main belt | CER-ORB · CER-SURF · VES-SURF · PSY-SURF · HYG-SURF · per procedural body | 6 all |
| Comets | one NUC per nucleus | 7 |
| Jupiter | JUP-ATM probe band | 9 |
| Io/Europa | IO-SURF · EUR-SURF (ORB inherits) | 10 |
| Europa ocean | EUR-OCEAN (melt-probe megaproject) | **14** |
| Ganymede/Callisto | GAN-SURF · CAL-SURF | 8 |
| Saturn | SAT-ATM · SAT-RINGS | 10 · 10 |
| Titan | TIT-ORB · TIT-SURF · TIT-SEAS (3 maria + 2 lake districts) | 10 · 11 · 11 |
| Titan sea floor | TIT-SEAFLOOR (submersible) | **14** |
| Enceladus | ENC-SPT (4 stripes) · ENC-NORTH | 12 · 10 |
| Uranus system | URA-ATM · MIR-SURF · TIA-SURF · OBE-SURF | 11 · 12 · 12 · 12 |
| Neptune system | NEP-ATM · TRI-SURF | 12 · 13 |
| Pluto system | PLU-SURF · CHA-SURF | 13 · 13 |
| KBOs | one SURF per body | 13 |

One X per region, never a range. Act gradient: 1–1.5 → 2–4 → 4–5 → 6–8 → 8–14 (ocean cap 14).

### 2.5 Future-history canon (Appendix A; DECISIONS F32 — every entry is world STATE at t=0, no timed events)

Eras: Crowded Decade 2024–35 (everything funded flew) → Retrenchment 2036–45 (2037 LEO collision-cascade scare at
800 km + fiscal crisis; programs orphaned) → Reopening 2046–49 (commercial heavy lift; player chartered 2049).
Entries without an AN row receive one at data entry:

| What / where | State 2049 | Hook |
|---|---|---|
| LEO/GEO derelicts + 3 megaconstellation generations | 700–900 km dirtiest band | debris zones, AN-31/32, clearance contracts |
| ISS (deorbited 2030) | jettisoned remnants decaying | graveyard remnants, museum Prestige |
| Hubble | derelict since 2032, reentry 2050s | Act 1 reboost prestige contract |
| Lunar Gateway (NRHO) | mothballed 2038, station-keeping on residual Xe | **largest cislunar salvage**: reactivation = instant station core |
| First commercial LEO station | stripped hulk @ 800 km | StructuralParts; docking practice |
| CLPS scatter (~15 landers, several tipped) | dead | first-salvage tutorial targets, Electronics scrap |
| VIPER (flown commercially 2028) | died first PSR night, Nobile rim | cryo drivetrain salvage; cold-wear codex |
| Artemis III–V assets (Shackleton/de Gerlache) | 2 HLS stages, dead LTV, masts, EVA cache | AN-07; LTV refurb = free rover chassis |
| China crewed lunar (2030–31, 2 sorties) | descent stages, pallets | heritage zone, tourism contract |
| Chang'e 6/7/8 + ILRS core | ILRS silent since 2041 relay failure | largest single lunar salvage; regolith-brick ground truth |
| Lunar relay constellation | all dark by 2043 | reactivate one = far-side relay head start |
| Mars relay fleet (5 orbiters, dead 2025–38) | silent, stable orbits | refurbish one = day-one Mars relay |
| Mars surface fleet (InSight, Ingenuity, Perseverance †2029, Curiosity †2031, Zhurong) | dust-covered; RTG rovers still warm | AN-08…13, Pu-238 chain |
| **NASA–ESA MSR cache, stranded** | Three Forks 10 tubes + 20+ aboard dead Perseverance; program cancelled 2028 | AN-11 = Act 3 prestige jackpot |
| Tianwen-3 (China MSR, worked 2035) | descent stage + launch mount, Utopia | pilgrimage zone, feasibility codex |
| MMX (Phobos) | lander + IDEFIX derelict; backup sample canister clamped on deck | AN-24, canister mini-contract, water ground truth |
| OSIRIS-APEX at Apophis | derelict escort | free K2 on Apophis; flyby-anniversary event |
| Hera + cubesats at Didymos | derelict at DART site | deflection codex |
| Tianwen-2 bus | silent near comet 311P | drifting intercept |
| Lucy bus | derelict on trojan cycler | ground-truth pings for ~20 procedural trojans |
| JWST | propellant out 2041, tumbling at drifted L2 | optics salvage = one-shot telescope boost; expert rendezvous |
| BepiColombo MPO/Mio | MPO decaying low Mercury orbit | partial L1 head start at Mercury |
| Europa Clipper | Ganymede disposal impact 2034 | impact scar + debris field |
| JUICE | Ganymede surface impact 2035 | "the two graves" survey chain |
| **Dragonfly, silent at Selk** | 47 sorties; comm loss 2039; on dune crest, MMRTG ~⅔ output | AN-39; locating it = Act 5 detective quest (last fix + wind drift) |

---

## 3. MECHANICS

### 3.1 Orbits & 2D flattening (S-1, S-2)
On-rails Kepler ellipses; elements a, e, P (cached), ϖ, M0, dir ∈ {+1, −1}. Kepler solved by Newton, tol 1e-12 rad,
≤ 8 iter; **near e→1 (Halley 0.967) use Markley/Danby starter or bisection fallback; unit test e = 0.99, M = 0.001 rad**.
All inclinations → 0. Retrograde bodies (Triton, Halley) keep dir = −1 ⇒ ~2× rendezvous closing speed (UI: red closing
speed on dir mismatch). Pluto–Neptune separation guarantee per §1.2.

### 3.2 Gravity, SOI, launch bonus (S-3)
g = GM/R², v_esc = √(2GM/R) derived; r_SOI = a·(m/M)^(2/5). Bodies are circles of radius R in orbit view.
Equatorial launch bonus v_rot = 2πR/T_rot added prograde to every ascent (all launches "equatorial" in 2D).

### 3.3 Solar flux, light lag, conjunction (S-4)
S(d) = 1361/d² W/m² at current orbital radius (Mercury swings 6,270–14,450 W/m²). Light lag t = r_line/c.
**Conjunction blackout** iff Sun–target angular separation seen from observer < 1.0° AND dist(obs→target) >
dist(obs→Sun) — superior conjunction only (Venus inferior conjunction does NOT occult). Mars: ~2 weeks/26 months.

### 3.4 Insolation, day/night, temperature (S-6)
- `I(t) = S(d) · c_sun(t) · f_atm`, c_sun = max(0, cos(φ_center + 2πt/T_rot − θ_sun)).
- f_atm: vacuum 1.0 · Mars f_dust(τ) = max(0.04, exp(−0.45·τ)) (defined once in S-9, applied exactly once) ·
  Venus per band column (0.30–0.70, +0.15 albedo bonus) · Titan 0.10.
- **PSR**: I = 0 always. **PEL** (Shackleton rim): I = S(d)·duty, duty 0.85 ± 0.05 jitter, no T_rot dependence.
- **Eclipse**: f_ecl multiplies solar availability for ALL assets in moon SOI except PSR/PEL (mutual exclusion assert).
- Airless T: `T_surf = T_night + (T_day − T_night)·c_sun^0.25`. Atmosphere: `T_mean ± ΔT_diurnal/2 · sin(2πt/T_solarday)`.
- **Mercury terminator chase**: v_term = 2πR/T_solarday ≈ 3.6 km/h equatorial — rovers outrun sunrise; twilight band
  T ≈ 250–350 K. Warp edge case: integrate thermal damage analytically across warp steps, never per-frame.
- PSR assert: PSR flag overrides T_day := T_night (bug class: flag forgotten after deposit instantiation).

### 3.5 Mars dust seasons & climate (S-9, S-9a — DECISIONS C24)
`Ls = (ν + 251°) mod 360°` from true anomaly; Mars year 668.6 sols (sol = 88,775 s); advances non-uniformly (e = 0.0934).
- τ_base = 0.3 (Ls 0–180) / 0.5 (Ls 180–360).
- Regional storms (Ls 180–330): p = 0.004/sol per sector; τ → 2.0–4.0 over 2 sols; duration U(5,40) sols;
  spread to adjacent sectors p = 0.15/sol.
- Global storm: once per Mars year roll at Ls = 200°±30°, p = 0.33; ALL sectors τ → U(4,9) over 10 sols,
  duration U(60,100) sols, e-fold decay 25 sols. f_dust = 0.165–0.04 → solar-only bases die.
- Panel soiling: −0.2%/sol clear, −2%/sol storm; cleaning task or wind event p = 0.005/sol restores.
- Storms: EDL σ ×2, orbital scans paused, **warning always fires at onset** (player may divert; never silent).
- Pressure: P_site = P_datum·(1 + 0.15·sin(2π(Ls − 250°)/360°)) — affects intake mining + EDL.
- **Climate multiplier** (every consumer of ρ_Mars(h)): `f_climate = clamp(f_season·f_dustheat·f_diurnal, 0.50, 1.50)`
  with f_season = 1 + 0.15·sin(2π(Ls−250°)/360°) · f_dustheat = 1 + 0.05·τ·(0.5 + h/100 km) ·
  f_diurnal = 1 − 0.20·(1 − c_sun)·min(1, h/100 km). Clamp band [0.50, 1.50] is the published interface for 01
  corridor planning, consumed at plan time AND execution.

### 3.6 Survey & prospecting (S-10)
Knowledge ladder: **L0** ephemeris-only (all start here except Earth/Moon/Mars = L1) → **L1** mapped (orbital survey:
sector list + terrain + anomaly pings) → **L2** prospected (per-sector rover/lander work: deposits to K2, pings → sites).
Orbital progress: `C += (w_swath·v_orb)/(4πR²)` per s while alt < h_scan and instrument powered (instrument params
04 §4.3; full map ≈ 5–30 orbits). Anomaly pings show class-blind "?" with ping radius until visited.
Survey states persist per body in save (13 schema).

### 3.7 Small-body ops (S-11, S-12)
- Spin barrier: rubble piles D > 300 m enforce T_rot ≥ 2.2 h; monolith fragments < 300 m may spin to 0.1 h (DANGER).
- Io eruptions: Poisson 1/(30 d) per volcanic sector; plume 300–400 km; ejecta p = 0.02/event (damage roll to 07).
- Enceladus: continuous plume 200 kg/s; sub-100 km fly-through free SurveyData, zero erosion; tiger-stripe landing:
  vent capture ≤ 5 kg/s per collector.
- Anchoring: g < 0.01 m/s² ⇒ anchor hardpoints mandatory (harpoon/auger, MachineParts via 05); unanchored objects
  drift on any impulse > m·v_esc_local. Comet ice: anchor p_fail = 0.1 per anchor (re-anchor task).
- Dock-mode flag fixed at world-gen; never flips with radius refinement.

### 3.8 Comet activity (S-13)
A(d) = clamp((3.0/d)² − 1, 0, 8). Effects: optics/array abrasion −0.5%·A/day on surface or within 50 km;
landing dispersion ×(1 + 0.2A); coma scoop within 10 km collects 0.2·A kg/h Water (flavor-scale;
**assert total < 10 t per perihelion** — never out-competes Enceladus/Ceres). Non-grav drift NOT modeled.

### 3.9 Scheduled events (S-14)
Halley perihelion 2061-07-28 (AN-44) · Mars global-storm rolls (S-9) · solar maxima ≈ 2057, 2068 ± 2 yr jitter ·
synodic launch windows Mars 779.9 d / Venus 583.9 d / Jupiter 398.9 d. Warp-blocking flags: SPE with unsheltered
crew, eruptions in occupied sectors, comet-perihelion ops with anchored assets.

### 3.10 Body-special mechanics (quick index)
Mercury terminator chase + perihelion smelting + mass-driver export (T3) · Venus buoyancy/super-rotation
3 d light/3 d dark + acid degradation 1%/day + crewed surface = single T4 [SPEC] trophy (C17) · Earth debris bands +
hurricane scrubs · Moon 14.77 d night + PEL duty 0.85 + lava-tube −40% base cost · Mars Sabatier economy + Hellas/
Olympus/Valles modifiers · Phobos Stickney +0.35 shielding · Ceres deep-brine T3 megaproject · Io geothermal
[SPEC T4 100 kWt cap] · Europa melt probe (T3 megaproject → X=14 region) · Titan flight paradise + inverted combustion
+ methane rain flags · Enceladus vent capture · Ring mining T3 (ṁ = 2 t/h·ρ_zone) · Triton retrograde + geysers ·
Pluto atmosphere collapse + Charon skyhook hook [T4 SPEC] · KBO ×2 pristine GB.

### 3.11 World-gen / runtime asserts (§8)
1. Pluto–Neptune min separation ≥ 12 AU over 495-yr cycle, else re-seed M0.
2. PSR/PEL override XOR f_ecl path (never both).
3. PSR sectors never receive day-side temperatures.
4. f_cycle clamp [0.65, 1.35]; SPE cap 2,000 mSv.
5. Procedural body rejection: Δa < 0.01 AU ∧ Δe < 0.02 vs curated.
6. Heritage-zone deposit re-roll.
7. Dock-mode flag immutable post world-gen.
8. Venus aerostat clamp 45–65 km; destructive < 42 km.
9. Comet capture < 10 t/perihelion.
10. Below-h_atm orbit decay must warn, not silently decay in warp.

---

## 4. GAP vs CODE

### 4.1 `data/core/bodies/*.json` (37 files, ~300 bytes each)
**Has**: id, parent, mu_m3s2, radius_m, rotation_period_s, elements {a_m, e, lon_peri_rad, t_peri_s, sense}, soi_m.
All 37 curated bodies present (roster complete vs §1.1). Note: code stores t_peri_s where design gives M0 @ epoch —
equivalent, but data entry must convert M0/ϖ canon (incl. Pluto/Neptune resonance values and Halley's anchored M0).
**Each body file needs to grow** (or sibling files keyed by body id):
- `atmosphere`: P0, T0, μ, H, h_break, H_upper, L, T_min_strat, **h_atm**, ΔT_diurnal, w, composition mole fractions
  (canonical resource names), Venus band lookup table, Mars f_climate hook, Pluto collapse term.
- `thermal`: T_day/T_night range, PSR floor, T_mean, solar-day length (≠ rotation for Mercury/Venus).
- `radiation`: ambient override OR field-function tag (earth_belts | jupiter_belts | saturn_belts | gcr_only),
  SPE distance factor.
- `surface`: landing_class A–F, dock_mode flag, **sector list** (per §1.8: name, terrain_class, flags, overrides,
  anomaly slots, region_id), spin-barrier/rubble class for small bodies.
- `science`: region_ids + X values, flyby/L1 GB yields.
- `resources`: key-resource hooks → 04 deposit tables (1:1 with sector lists).
- Missing entities entirely: **~218 procedural bodies** (world-gen §1.6 + §1.2 rules), Saturn **ring zone object**
  (A/B/C/Cassini radii + ρ_zone), Earth **debris band zones**, heliocentric derelict objects (AN-29/30, JWST,
  Lucy, Tianwen-2), Sun–Earth L1/L2 anchor slots (C18).

### 4.2 `aphelion/sim/environment/atmosphere.py`
Piecewise-exponential ρ(h) breakpoints for Earth/Mars/Venus/Titan/Jupiter/Saturn only.
Gaps: (a) **interface altitudes far below canon h_atm** — Earth 140 km vs 600, Mars 125 vs 250, Venus 180 vs 350,
Titan 850 vs 1,400 (no LEO station decay, no Titan parking-orbit drag — contradicts realism doctrine; note doc 01
owns the breakpoints per its header, so reconcile under DECISIONS A2 before extending); (b) no Triton/Pluto
atmospheres; (c) no composition/μ (intake mining 04 M-3e), no T(h), no winds/gusts, no Venus band table override,
(d) no Mars f_climate(h, t) multiplier (C24 — the ±50% corridor contract), no seasonal P_site, (e) no Pluto collapse.

### 4.3 `aphelion/sim/habitat/dose.py`
Has 8-entry static ambient table + A3 decaying-floor shielding + career accounting.
Gaps: no f_cycle(t) solar-cycle modulation (deep_space fixed 1.8); no SPE event system (Poisson λ(t), lognormal dose,
1/d² scaling, 30–60 min warning, shelter/warp-block hooks); no Earth belt piecewise field D(r); no Jupiter
piecewise-exact field function D_jup(r) (only the four fixed moon-surface values); no Saturn 8 R_S field; missing
bodies: Mercury (6.7× SPE), Venus cloud 0.03, Io 36,000, Phobos 0.7, Deimos 0.9, Uranus/Neptune moons 0.5, Moon-PSR;
Callisto hard-codes `0.14 + 1.8*0.5` — canon is 0.14 + GCR·f_cycle(t), time-varying.

### 4.4 `aphelion/game/sites.py`
5 hand-picked sites (Peary, Jezero, Venus cloud, Ligeia, Conamara) with land/ascent Δv, science lump, solar factor,
day length. This is a placeholder for the entire S-7 sector system: **~176 curated sectors** (§1.8), the sector
record schema, terrain-class defaults, φ_center layout, landing classes + EDL dispersion σ, PSR/PEL flags,
dust_index, anomaly slots, region_ids, deposit hooks, and procedural site-map seeds (S-7c) are all absent.
No anomaly catalog (AN-01…AN-50 + procedural generator + ≈110/campaign target), no SurveyData yield classes,
no 2 SCI/GB conversion, no L0/L1/L2 survey ladder, no heritage zones.

### 4.5 `aphelion/render/body_art.py`
Map-view sprites for all 37 bodies with palette table + unknown-id fallback — adequate for orbit view.
No surface-layer rendering: sector ring UI (§5), body inspector live panels (P(h) plot, radiation-at-cursor,
day/night shading, PSR/PEL badges), environment overlays (belt annuli, flux contours, light-lag isochrones,
Mars Ls dial, comet halos), anomaly pings.

### 4.6 Supporting systems (exist, need extension)
`sim/power.py`: 1361/d² flux + synchronous day/night boundaries exist; missing f_atm (Mars f_dust, Venus bands,
Titan 0.10), f_ecl eclipse fractions, PSR/PEL duty overrides, dust soiling. `sim/comms.py`: light lag exists;
missing conjunction blackout geometry. Nothing anywhere implements: Mars Ls/dust state machine, S-11 eruptions/vents,
S-12 anchoring, S-13 comet activity, S-14 event calendar (Halley 2061, solar maxima, storm warnings),
science regions/X, future-history world state (Appendix A — Gateway, MSR cache, Dragonfly, etc.).
