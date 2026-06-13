"""12 §1: the five-act spine (G-12/G-13), the 38-row Firsts ladder
(§1.5/E-13), Prestige (§1.6/E-14…E-16), investor rounds (§1.7/E-17…E-19)
and the charter chain (§1.11/T-1) — every stated numeric pinned."""

import math

import pytest

from aphelion.game.acts import (
    ACT_BY_NO, ACTS, BRIDGE_LOAN, CHARTER_BY_ID, CHARTER_DEADLINE_S,
    CHARTERS, CONTENT_GATES, END_ACT, FIRST_BY_ID, FIRSTS, HERITAGE_FINE,
    HERITAGE_LOCKOUT_YR, HERITAGE_RADIUS_KM, LEGACY_ACT_GATE, MONEY_FADE,
    P_MAX, PRESTIGE_EVENTS, PRESTIGE_GATES, PROMISE_FAIL, ROUND_BY_ID,
    ROUNDS, SPEND_ENVELOPE_B, VETERAN_SKIP_M, Prestige, act_entered,
    award_firsts, charter_contract, check_firsts, content_available,
    current_act, first_payout, first_prestige, is_charter, legacy_act,
    legacy_act_unlocked, money_faded, rounds_available, snapshot,
    validate_acts,
)
from aphelion.sim.economy import Contract, Program


def test_validate_and_ladder_shape():
    """§1.5: 38 rows; per-act 8/7/7/7/6/3; unique ids."""
    validate_acts()
    assert len(FIRSTS) == 38
    per_act = {a: sum(1 for f in FIRSTS if f.act == a)
               for a in (1, 2, 3, 4, 5, END_ACT)}
    assert per_act == {1: 8, 2: 7, 3: 7, 4: 7, 5: 6, END_ACT: 3}


# every (payout $M, prestige) pair from the §1.5 table, in ladder order
LADDER = [
    ("f_first_launch", 5.0, 5), ("f_first_orbit", 30.0, 10),
    ("f_first_reflight", 20.0, 5), ("f_first_docking", 25.0, 10),
    ("f_first_crewed_orbit", 60.0, 20), ("f_abort_demo", 0.0, 5),
    ("f_leo_station_core", 40.0, 10), ("f_cryo_depot_transfer", 50.0, 10),
    ("f_lunar_flyby", 40.0, 10), ("f_robotic_moon_landing", 80.0, 20),
    ("f_polar_ice", 60.0, 10), ("f_crewed_moon_landing", 300.0, 50),
    ("f_lunar_ice_mine", 150.0, 30), ("f_lunar_lox_at_depot", 100.0, 20),
    ("f_lunar_base_90d", 120.0, 20), ("f_ntr_burn", 100.0, 25),
    ("f_robotic_mars_edl", 150.0, 30), ("f_crewed_mars_landing", 500.0, 75),
    ("f_mars_methalox", 80.0, 30), ("f_nea_volatiles", 120.0, 25),
    ("f_mars_sample_return", 0.0, 40), ("f_food_harvest", 50.0, 15),
    ("f_belt_arrival", 100.0, 25), ("f_metal_mine", 120.0, 25),
    ("f_venus_aerostat", 250.0, 75), ("f_silicon_independence", 200.0, 50),
    ("f_mass_driver", 100.0, 25), ("f_food_independence", 100.0, 25),
    ("f_never_earth_ship", 150.0, 40), ("f_jupiter_arrival", 200.0, 50),
    ("f_europa_bore", 150.0, 40), ("f_titan_landing", 200.0, 50),
    ("f_titan_submarine", 150.0, 50), ("f_enceladus_plume", 100.0, 25),
    ("f_saturn_base", 250.0, 50), ("f_foundation_audit", 0.0, 100),
    ("f_precursor_launched", 0.0, 100), ("f_precursor_100au", 0.0, 100),
]


def test_ladder_values_pinned():
    """E-13: every payout and Prestige award from the table is LAW."""
    assert [f.fid for f in FIRSTS] == [row[0] for row in LADDER]
    for fid, payout_m, prestige in LADDER:
        f = FIRST_BY_ID[fid]
        assert f.payout_m == pytest.approx(payout_m), fid
        assert f.prestige == prestige, fid
    assert sum(f.payout_m for f in FIRSTS) == pytest.approx(4_150.0)
    assert sum(f.prestige for f in FIRSTS) == 1_305


def test_first_payout_funding_multiplier():
    """E-13: paid x funding multiplier (D-2); '—' rows pay nothing."""
    assert first_payout("f_first_orbit") == pytest.approx(30e6)
    assert first_payout("f_first_orbit", 1.5) == pytest.approx(45e6)
    assert first_payout("f_abort_demo") == pytest.approx(0.0)        # CT-10
    assert first_payout("f_mars_sample_return") == pytest.approx(0.0)
    assert first_payout("f_foundation_audit") == pytest.approx(0.0)


def test_act_table_pinned():
    """§1.1: theaters, tiers, exit milestones, target hours, envelopes."""
    assert [a.act for a in ACTS] == [1, 2, 3, 4, 5, END_ACT]
    assert ACT_BY_NO[1].theater == "Earth + LEO"
    assert ACT_BY_NO[2].theater == "Moon"
    assert ACT_BY_NO[3].theater == "Mars & NEAs"
    assert ACT_BY_NO[4].theater == "Belt & Venus"
    assert ACT_BY_NO[5].theater == "Jupiter/Saturn"
    assert ACT_BY_NO[1].tiers == "T0-T1" and ACT_BY_NO[5].tiers == "T3-T4"
    # exit milestones (G-13 act-transition triggers)
    assert ACT_BY_NO[1].exit_fids == ("f_cryo_depot_transfer",)
    assert set(ACT_BY_NO[2].exit_fids) == {"f_lunar_base_90d",
                                           "f_lunar_lox_at_depot"}
    assert set(ACT_BY_NO[3].exit_fids) == {"f_food_harvest",
                                           "f_mars_methalox"}
    assert ACT_BY_NO[4].exit_fids == ("f_silicon_independence",)
    assert ACT_BY_NO[5].exit_fids == ("f_saturn_base",)
    assert ACT_BY_NO[END_ACT].exit_fids == ()
    # target cumulative hours (G-12 pacing)
    assert ACT_BY_NO[1].hours == (0.0, 12.0)
    assert ACT_BY_NO[2].hours == (12.0, 35.0)
    assert ACT_BY_NO[3].hours == (35.0, 75.0)
    assert ACT_BY_NO[4].hours == (75.0, 120.0)
    assert ACT_BY_NO[5].hours == (120.0, 170.0)
    assert ACT_BY_NO[END_ACT].hours == (170.0, 220.0)
    # per-act money envelope: $0.45B / $1.6B / $4B, then money decouples
    assert SPEND_ENVELOPE_B[1] == pytest.approx(0.45)
    assert SPEND_ENVELOPE_B[2] == pytest.approx(1.6)
    assert SPEND_ENVELOPE_B[3] == pytest.approx(4.0)
    assert 4 not in SPEND_ENVELOPE_B and 5 not in SPEND_ENVELOPE_B


def test_campaign_walkthrough_in_order():
    """G-13: walk a campaign through every act transition in order,
    earning Firsts from minimal snapshots along the way."""
    earned: set[str] = set()
    S = snapshot()
    assert current_act(S, earned) == 1
    assert check_firsts(S, earned) == []

    # Act 1: launch -> orbit -> docking -> crewed -> station -> depot demo
    S["milestones"] |= {"launched", "orbited", "stage_reflown", "docked",
                        "crewed_orbit", "abort_demo", "station_core_4x30"}
    new = check_firsts(S, earned)
    assert new == ["f_first_launch", "f_first_orbit", "f_first_reflight",
                   "f_first_docking", "f_first_crewed_orbit",
                   "f_abort_demo", "f_leo_station_core"]
    earned |= set(new)
    # the depot demo needs T1 too — flag alone is not enough
    S["milestones"].add("depot_cryo_transfer")
    assert "f_cryo_depot_transfer" not in check_firsts(S, earned)
    assert current_act(S, earned) == 1
    S["tech_tier"] = 1
    assert check_firsts(S, earned) == ["f_cryo_depot_transfer"]
    earned.add("f_cryo_depot_transfer")
    assert current_act(S, earned) == 2          # Act 1 exit fired

    # Act 2: the exit needs BOTH the 4x90 base AND LOX-at-depot
    S["visited"].add("core:moon")
    S["landed"].add("core:moon")
    S["crewed_landed"].add("core:moon")
    S["milestones"] |= {"polar_ice_drilled", "base_4crew_90d"}
    S["extracted_t"]["Water"] = 10.0
    earned |= set(check_firsts(S, earned))
    assert current_act(S, earned) == 2          # no LOX at depot yet
    S["milestones"].add("lunar_lox_at_depot")
    earned |= set(check_firsts(S, earned))
    assert current_act(S, earned) == 3

    # Act 3: exit = food harvest WITH methalox
    S["milestones"] |= {"ntr_burn_orbit", "food_harvest"}
    earned |= set(check_firsts(S, earned))
    assert current_act(S, earned) == 3          # methalox still missing
    S["milestones"].add("mars_methalox")
    earned |= set(check_firsts(S, earned))
    assert current_act(S, earned) == 4

    # Act 4: exit = Silicon Independence (wafer fab online)
    S["industry_online"].add("fab_wafer_fab")
    assert "f_silicon_independence" in check_firsts(S, earned)
    earned |= set(check_firsts(S, earned))
    assert current_act(S, earned) == 5

    # Act 5: exit = Saturn permanent base (12 crew x 2 yr)
    S["milestones"].add("saturn_base_12crew_2yr")
    earned |= set(check_firsts(S, earned))
    assert current_act(S, earned) == END_ACT

    # monotonic (G-13): a gutted snapshot can never demote the act
    assert current_act(snapshot(), earned) == END_ACT
    assert act_entered(END_ACT, snapshot(), earned)


def test_one_shot_and_remaining_triggers():
    """E-13: repeats pay nothing; spot-check the remaining predicates."""
    S = snapshot(milestones={"orbited"})
    assert check_firsts(S, set()) == ["f_first_orbit"]
    assert check_firsts(S, {"f_first_orbit"}) == []        # one-shot
    # Mars rows ride landed/crewed_landed body sets
    S = snapshot(landed={"core:mars"}, crewed_landed={"core:mars"})
    assert set(check_firsts(S, set())) == {"f_robotic_mars_edl",
                                           "f_crewed_mars_landing"}
    # NEA row needs the rendezvous AND 100 t of volatiles
    S = snapshot(milestones={"nea_rendezvous"},
                 extracted_t={"Volatiles": 99.9})
    assert check_firsts(S, set()) == []
    S["extracted_t"]["Volatiles"] = 100.0
    assert check_firsts(S, set()) == ["f_nea_volatiles"]
    # belt arrival = Ceres-class rendezvous; metal mine = 100 t IronSteel
    assert check_firsts(snapshot(visited={"core:ceres"}), set()) \
        == ["f_belt_arrival"]
    assert check_firsts(snapshot(refined_t={"IronSteel": 100.0}), set()) \
        == ["f_metal_mine"]
    # Jupiter arrival pairs the SOI with the Callisto base seed
    assert check_firsts(snapshot(visited={"core:jupiter"}), set()) == []
    assert check_firsts(snapshot(visited={"core:jupiter"},
                                 colonized={"core:callisto"}), set()) \
        == ["f_jupiter_arrival"]
    # Titan submarine is a vehicle-class first
    assert check_firsts(snapshot(vehicles_operated={"submarine"}),
                        set()) == ["f_titan_submarine"]


def test_titan_crewed_prestige_variant():
    """§1.5: Titan landing +50; crewed = +75 instead."""
    robotic = snapshot(landed={"core:titan"})
    crewed = snapshot(landed={"core:titan"}, crewed_landed={"core:titan"})
    assert first_prestige("f_titan_landing", robotic) == 50
    assert first_prestige("f_titan_landing", crewed) == 75
    assert first_prestige("f_first_orbit", crewed) == 10  # others fixed


def test_award_firsts_wraps_existing_program():
    """Firsts pay through the EXISTING Program ledger (save shape kept)."""
    program = Program(funds=0.0)
    prestige = Prestige()
    earned: set[str] = set()
    S = snapshot(milestones={"launched", "orbited"})
    toasts = award_firsts(program, prestige, 100.0, S, earned)
    assert len(toasts) == 2
    assert program.funds == pytest.approx(35e6)          # $5M + $30M
    assert prestige.value == pytest.approx(15.0)         # +5 +10
    assert earned == {"f_first_launch", "f_first_orbit"}
    assert ("first:f_first_orbit"
            in {h[1] for h in program.history})          # ledger idiom
    # re-sweep: one-shot, nothing double-pays
    assert award_firsts(program, prestige, 200.0, S, earned) == []
    assert program.funds == pytest.approx(35e6)
    # funding multiplier (D-2) scales the payment
    p2, e2 = Program(funds=0.0), set()
    award_firsts(p2, Prestige(), 0.0, S, e2, funding_mult=0.5)
    assert p2.funds == pytest.approx(17.5e6)


def test_legacy_act_gate_mapping():
    """The v1 contract table keeps acts 1..4 (LEO+Luna / inner / outer /
    way-out); the five-act spine maps onto that numbering."""
    assert LEGACY_ACT_GATE == {1: 1, 2: 1, 3: 2, 4: 2, 5: 3, END_ACT: 4}
    assert legacy_act(2) == 1 and legacy_act(5) == 3
    earned = {"f_cryo_depot_transfer"}                   # v2 act 2
    assert legacy_act_unlocked(1, snapshot(), earned)
    assert not legacy_act_unlocked(2, snapshot(), earned)
    earned |= {"f_lunar_base_90d", "f_lunar_lox_at_depot"}   # v2 act 3
    assert legacy_act_unlocked(2, snapshot(), earned)
    assert not legacy_act_unlocked(3, snapshot(), earned)


def test_content_gates():
    """§1.4 act column: 25 templates, [A#] availability honored."""
    assert len(CONTENT_GATES) == 25
    assert content_available("CT-01", 1) and not content_available("CT-01", 2)
    assert content_available("CT-07", 3) and not content_available("CT-07", 4)
    assert content_available("CT-14", 2) and content_available("CT-14", 4)
    assert not content_available("CT-14", 5)
    assert content_available("CT-19", 3) and content_available("CT-19", 5)
    assert content_available("CT-19", END_ACT)      # A3-5 lives on at End
    assert not content_available("CT-22", 4) and content_available("CT-22", 5)
    assert content_available("CT-23", 2) and content_available("CT-23", 5)
    assert not content_available("CT-23", 1)        # A2+
    assert not content_available("CT-16", 4)        # A3 only, window-locked


def test_prestige_scalar_and_events():
    """E-14: P in 0..1,000; every named delta pinned."""
    assert (P_MAX, PRESTIGE_GATES) == (1000, (50, 150, 300, 500))
    assert PRESTIGE_EVENTS["contract_bonus_ct09"] == 25
    assert PRESTIGE_EVENTS["contract_bonus_ct21"] == 50
    assert PRESTIGE_EVENTS["anomaly_visit"] == 5    # x listed multiplier
    assert PRESTIGE_EVENTS["rescue"] == 50
    assert PRESTIGE_EVENTS["safety_year"] == 5
    assert PRESTIGE_EVENTS["crew_fatality"] == -100
    assert PRESTIGE_EVENTS["founder_fatality"] == -150
    assert PRESTIGE_EVENTS["contract_failure"] == -10
    assert PRESTIGE_EVENTS["heritage_violation"] == -50
    assert PRESTIGE_EVENTS["agency_assist"] == -100
    assert PRESTIGE_EVENTS["stand_down_month"] == -5
    assert PRESTIGE_EVENTS["failed_promise"] == -100
    p = Prestige()                                  # E-1: start P 0
    assert p.value == pytest.approx(0.0)
    p.event("crew_fatality")
    assert p.value == pytest.approx(0.0)            # clamped at 0
    p.event("anomaly_visit", mult=3.0)
    assert p.value == pytest.approx(15.0)           # +5 x multiplier
    p.add(2000.0)
    assert p.value == pytest.approx(1000.0)         # cap


def test_prestige_floor_history():
    """E-14 floor = max(0, highest gate ever crossed - 100)."""
    p = Prestige()
    p.add(160.0)                            # crosses 50 and 150
    assert p.highest_gate == 150
    p.add(-1000.0)
    assert p.value == pytest.approx(50.0)   # floor 150 - 100
    p.add(500.0)                            # 550: crosses 300 and 500
    assert p.highest_gate == 500
    p.event("founder_fatality")
    assert p.value == pytest.approx(400.0)
    p.add(-1000.0)
    assert p.value == pytest.approx(400.0)  # floor 500 - 100
    # round-trips through the additive save dict
    q = Prestige.from_dict(p.to_dict())
    assert (q.value, q.highest_gate) == (p.value, p.highest_gate)
    assert Prestige.from_dict(None).value == pytest.approx(0.0)


def test_prestige_effects():
    """E-15/E-8: board N = 3 + floor(P/100) max 12; recruit +1/200 P;
    tourism x (1 + P/1000)."""
    assert Prestige(0.0).board_slots == 3
    assert Prestige(99.0).board_slots == 3
    assert Prestige(100.0).board_slots == 4
    assert Prestige(850.0).board_slots == 11
    assert Prestige(900.0).board_slots == 12
    assert Prestige(1000.0).board_slots == 12       # capped
    assert Prestige(199.0).recruit_bonus == 0
    assert Prestige(200.0).recruit_bonus == 1
    assert Prestige(450.0).recruit_bonus == 2
    assert Prestige(250.0).tourism_mult == pytest.approx(1.25)
    assert Prestige(0.0).tourism_mult == pytest.approx(1.0)


def test_heritage_zone_constants():
    """E-16: 10 km no-placement radius, $100M fine, 1 yr lockout."""
    assert HERITAGE_RADIUS_KM == pytest.approx(10.0)
    assert HERITAGE_FINE == pytest.approx(100e6)
    assert HERITAGE_LOCKOUT_YR == 1


def test_investor_rounds_pinned():
    """E-17 table: gates start/50/150/300/500; cash $300M/$250M/$600M/
    $1.5B/$4.0B; promises 36/36/36/48 mo (Seed = tutorial charter)."""
    assert [r.rid for r in ROUNDS] == ["seed", "series_a", "series_b",
                                       "series_c", "series_d"]
    assert [r.gate for r in ROUNDS] == [0, 50, 150, 300, 500]
    assert [r.cash_m for r in ROUNDS] == [pytest.approx(300.0),
                                          pytest.approx(250.0),
                                          pytest.approx(600.0),
                                          pytest.approx(1500.0),
                                          pytest.approx(4000.0)]
    assert ROUND_BY_ID["seed"].promise_mo is None   # tutorial charter
    assert [r.promise_mo for r in ROUNDS[1:]] == [36, 36, 36, 48]
    avail = rounds_available(160.0)
    assert [r.rid for r in avail] == ["series_a", "series_b"]
    avail = rounds_available(160.0, raised={"series_a"})
    assert [r.rid for r in avail] == ["series_b"]
    assert rounds_available(49.0) == []
    # promise failure: Prestige -100, no rounds 5 yr, overhead +10% 2 yr
    assert PROMISE_FAIL == {"prestige": -100, "round_lockout_yr": 5,
                            "overhead_add": 0.10, "overhead_yr": 2}


def test_bridge_loan_and_money_fade():
    """E-18: <= 25% trailing revenue, 24 mo @ 12% APR (1%/mo), bullet,
    auto-repaid when Cash > 2 x principal. E-19: SSI >= 0.8 for 730 d."""
    assert BRIDGE_LOAN["revenue_frac"] == pytest.approx(0.25)
    assert BRIDGE_LOAN["term_mo"] == 24
    assert BRIDGE_LOAN["apr"] == pytest.approx(0.12)
    assert BRIDGE_LOAN["monthly_rate"] == pytest.approx(0.01)
    assert BRIDGE_LOAN["repay_cash_mult"] == pytest.approx(2.0)
    assert MONEY_FADE == {"ssi_program": 0.8, "sustain_days": 730.0}
    assert money_faded(0.8, 730.0)
    assert not money_faded(0.79, 10_000.0)
    assert not money_faded(0.95, 729.0)


def test_charter_chain():
    """T-1/§1.11: four charters paying $5M/$10M/$20M/$15M; veteran skip
    grants the $50M sum; charters are deadline-free Contracts that drop
    into the existing Program and save shape."""
    assert [c.payout_m for c in CHARTERS] == [5.0, 10.0, 20.0, 15.0]
    assert VETERAN_SKIP_M == pytest.approx(50.0)
    assert VETERAN_SKIP_M == pytest.approx(
        sum(c.payout_m for c in CHARTERS))
    assert CHARTER_BY_ID["charter_orbit"].unlocks == "Transfer dialog"
    assert is_charter("charter_recovery")
    assert not is_charter("c_orbit") and not is_charter("CT-02")

    program = Program(funds=0.0)
    for ch in CHARTERS:
        program.offer(charter_contract(ch))
    # deadline-free: completing DECADES later still pays (E-9/E-10 off)
    t = 80.0 * 365.0 * 86_400.0
    assert program.complete(t, "charter_recovery")
    assert program.funds == pytest.approx(5e6)
    assert program.expire_overdue(t) == []      # nothing ever expires
    # the contract dict shape used by save/campaign.py round-trips
    c = next(c for c in program.contracts
             if c.contract_id == "charter_orbit")
    cd = {"contract_id": c.contract_id, "description": c.description,
          "payout": c.payout, "deadline_s": c.deadline_s,
          "completed_t": c.completed_t, "failed": c.failed}
    c2 = Contract(**cd)
    assert c2.payout == pytest.approx(20e6)
    assert c2.deadline_s == pytest.approx(CHARTER_DEADLINE_S)
    assert math.isfinite(c2.deadline_s)         # JSON-safe sentinel


def test_v1_snapshot_flags_shared():
    """The v2 ladder reads the SAME milestone flags the v1 sweep saves
    ("orbited", "docked") — no migration needed for old campaigns."""
    S = snapshot(milestones={"orbited", "docked"})
    new = check_firsts(S, set())
    assert new == ["f_first_orbit", "f_first_docking"]
