"""Chunk E (Campaign v2): the rate-based money ledger and its
consumers, pinned to 12 §2.8 G-9 (analytic finance, zero drift), §2.2
E-4 overhead, §2.4 salaries, §1.3 E-9…E-11 contract money, §1.7
E-17/E-18 investors + bridge loan, §1.8 E-20…E-23 insurance and
stand-downs, §1.10 F-2…F-4 rescues/agency assist/death economics —
including the equivalence proof that main.py's discrete 30-day
overhead burn reproduces as one stream (no balance jump on swap-over)
and the persisted Program contract shape survives the v2 round-trip.
"""

import json
import math

import pytest

from aphelion.game.finance import (
    ADVANCE_FRAC, AGENCY_ASSIST_PREP_D, BRIDGE_APR, BRIDGE_INTEREST_PER_MO,
    BRIDGE_REVENUE_FRAC, BRIDGE_TERM_MO, CT19_CAP_KG_Y, CT19_PU238_PER_KG,
    CashLedger, DAY, DEATH_BENEFIT, FADE_SSI, FADE_SUSTAIN_D,
    FinanceState, InsuranceBook, Investors, MONTH, MONTH_30D,
    NUCLEAR_LICENSE_LEAD_D, OVERHEAD_FIXED_M, OVERHEAD_PER_BASE_M,
    OVERHEAD_PER_CREW_M, PENSION_Y, QUARTER, RATE_DECLINE_PER_Y,
    RESCUE_DELIVERY_WAIVER_D, ROUNDS, RescueObligation, SELL_FRACTION,
    SIGNING_BONUS, StandDown, TRAINING_COST, TRAINING_DAYS, YEAR,
    accept_contract, agency_assist_cost, contract_save_shape, contract_v2,
    data_payment, declined, default_deadline_s, e4_overhead_per_day,
    e4_overhead_rate, f_history, failure_cost, game_over, harbor_reachable,
    insured_value, is_stranded, launch_allowed, legacy_overhead_rate,
    liquidation_value, next_month_s, offtake_stream, pause_crewed_deadlines,
    pay_tranche, premium, prestige_floor, runway_alert_class, salary_per_year,
    salary_rate, service_rate, service_unlocked, ServiceLine,
    stand_down_duration_s, tranche_amounts, trailing_revenue, urgent_terms,
)
from aphelion.sim.economy import Contract, Program


# =============================================================================
# G-9: the analytic ledger
# =============================================================================

def test_legacy_overhead_stream_matches_main_burn():
    """The main.py burn — (1.5 + 0.4/crew + 1.0/base) $M per 30 d ×
    difficulty — must reproduce as ONE stream (swap-over without a
    balance jump)."""
    assert OVERHEAD_FIXED_M == pytest.approx(1.5)
    assert OVERHEAD_PER_CREW_M == pytest.approx(0.4)
    assert OVERHEAD_PER_BASE_M == pytest.approx(1.0)
    # DIRECTOR (×1.0), 2 crew, 1 base: $3.3M / 30 d
    r = legacy_overhead_rate(2, 1, 1.0)
    assert r * MONTH_30D == pytest.approx(-3.3e6, rel=1e-12)
    lg = CashLedger(cash0=150e6)
    lg.start("overhead", r, 0.0)
    burn_90d = 3.3e6 * 90.0 / 30.0          # the discrete formula
    assert lg.balance(90 * DAY) == pytest.approx(150e6 - burn_90d,
                                                 rel=1e-12)
    # HARDCORE doubles, CADET zeroes (mults owned by main)
    assert legacy_overhead_rate(2, 1, 2.0) == pytest.approx(2 * r)
    assert legacy_overhead_rate(2, 1, 0.0) == 0.0


def test_settle_into_program_no_balance_jump():
    """Wrapped mode: uneven settles over 90 d land the exact discrete
    total on the live Program (same history label, same clamp)."""
    program = Program(funds=150e6)
    lg = CashLedger(cash0=program.funds)
    lg.start("overhead", legacy_overhead_rate(2, 1, 1.0), 0.0)
    for d in (0.7, 3.3, 10.0, 40.0, 61.25, 90.0):
        lg.settle_into(program, d * DAY)
    assert program.funds == pytest.approx(150e6 - 9.9e6, rel=1e-12)
    assert all(h[1] == "program overhead" for h in program.history)
    # clamp at zero exactly like main's min(burn, funds)
    poor = Program(funds=1e5)
    lg2 = CashLedger(cash0=poor.funds)
    lg2.start("overhead", legacy_overhead_rate(0, 0, 1.0), 0.0)
    lg2.settle_into(poor, 300 * DAY)        # 10 months × $1.5M ≫ funds
    assert poor.funds == pytest.approx(0.0)


def test_two_year_ledger_walk_no_drift():
    """G-9: streams switching on/off over 2 years; a naive daily
    integrator must agree with the closed form (no per-tick drift),
    and the closed form must equal hand arithmetic."""
    lg = CashLedger(cash0=300e6)                       # E-1 seed
    lg.start("overhead", legacy_overhead_rate(0, 0, 1.0), 0.0)
    lg.start("salaries", salary_rate(2, 1), 90 * DAY)  # crew on payroll
    lg.stop("salaries", 455 * DAY)                     # flight ends
    lg.start("lease:dsn", -0.5e6 / QUARTER, 180 * DAY)  # E-4 tracking
    lg.start("svc:leo_constellation", service_rate("leo_constellation"),
             365 * DAY)                                # E-12 $5M/mo
    lg.post(10 * DAY, "contract:ct02:advance", 15e6)
    lg.post(20 * DAY, "premium:lv1#0", -12e6)
    lg.post(100 * DAY, "milestone:first_orbit", 30e6)
    lg.post(400 * DAY, "contract:ct17:tranche1", 450e6)

    t_end = 730 * DAY
    expected = (300e6
                - 1.5e6 * 730.0 / 30.0                 # overhead
                - 1.5e6 * (455 - 90) / 365.0           # salaries $1.5M/yr
                - 0.5e6 * (730 - 180) * DAY / QUARTER  # DSN lease
                + 5e6 * (730 - 365) * DAY / MONTH      # service income
                + 15e6 - 12e6 + 30e6 + 450e6)
    assert lg.balance(t_end) == pytest.approx(expected, rel=1e-12)

    # naive daily walk (what a per-tick accumulator would do)
    cash, ev = 300e6, sorted(lg.events)
    for d in range(730):
        a, b = d * DAY, (d + 1) * DAY
        cash += lg.rate(a) * DAY
        cash += sum(amount for te, _, amount in ev if a < te <= b)
    assert cash == pytest.approx(lg.balance(t_end), rel=1e-9)


def test_runway_and_alert_classes():
    """E-4 runway = Cash / max(ε, −net rate), ∞ at net ≥ 0; G-9 death
    spiral: < 60 d Class-3, < 14 d Class-2."""
    lg = CashLedger(cash0=100e6)
    lg.start("overhead", -1e6 / DAY, 0.0)
    assert lg.runway_days(0.0) == pytest.approx(100.0)
    assert runway_alert_class(lg.runway_days(0.0)) is None
    assert lg.runway_days(41 * DAY) == pytest.approx(59.0)
    assert runway_alert_class(59.0) == 3
    assert lg.runway_days(87 * DAY) == pytest.approx(13.0)
    assert runway_alert_class(13.0) == 2
    lg.start("income", 2e6 / DAY, 50 * DAY)     # net rate flips positive
    assert lg.runway_days(50 * DAY) == math.inf
    assert runway_alert_class(math.inf) is None


def test_zero_crossing_forces_warp_drop():
    """G-9: a Cash sign change inside a warp step is found at the
    exact crossing time (stream + queued discrete event)."""
    lg = CashLedger(cash0=10e6)
    lg.start("overhead", -1e6 / DAY, 0.0)
    lg.post(5 * DAY, "premium", -2e6)
    # 10 − t − 2·[t≥5] = 0 → t = 8 d
    assert lg.zero_crossing(0.0, 30 * DAY) == pytest.approx(8 * DAY)
    # an event alone can cross: drop lands exactly on its timestamp
    lg2 = CashLedger(cash0=1e6)
    lg2.post(3 * DAY, "fine", -2e6)
    assert lg2.zero_crossing(0.0, 10 * DAY) == pytest.approx(3 * DAY)
    # income covering the burn → no crossing
    lg3 = CashLedger(cash0=10e6)
    lg3.start("overhead", -1e6 / DAY, 0.0)
    lg3.start("svc", 2e6 / DAY, 0.0)
    assert lg3.zero_crossing(0.0, 365 * DAY) is None


# =============================================================================
# E-4 overhead, §2.4 salaries, E-12 services, offtake
# =============================================================================

def test_e4_daily_overhead_components():
    """E-4: $40k HQ + $10k/pad + $5k/uncrewed + $30k/crewed vessel +
    leases ($0.3M launch site + $0.5M tracking per quarter) +
    salaries."""
    assert e4_overhead_per_day() == pytest.approx(
        40e3 + 10e3 + 0.3e6 / (QUARTER / DAY))
    sal = salary_per_year(2, 1, 1)
    per_day = e4_overhead_per_day(n_pads=1, n_uncrewed=2,
                                  n_crewed_vessels=1, launch_site_leases=1,
                                  tracking=True, salaries_per_year=sal)
    assert per_day == pytest.approx(
        40e3 + 10e3 + 2 * 5e3 + 30e3
        + 0.8e6 / (QUARTER / DAY) + 1.6e6 / 365.0)
    assert e4_overhead_rate(tracking=True) == pytest.approx(
        -e4_overhead_per_day(tracking=True) / DAY)


def test_salaries_and_staffing_table():
    """§2.4: $0.25M/yr reserve, $1.0M/yr flight, pension $0.1M/yr
    (DECISIONS F33), signing 2/5/12 $M, training $2M + 90 d."""
    assert salary_per_year(2, 1, 1) == pytest.approx(1.6e6)
    assert salary_rate(0, 1) * YEAR == pytest.approx(-1.0e6)
    assert PENSION_Y == pytest.approx(0.1e6)
    assert SIGNING_BONUS == {"low": 2e6, "mid": 5e6, "high": 12e6}
    assert TRAINING_COST == pytest.approx(2e6)
    assert TRAINING_DAYS == pytest.approx(90.0)


def test_standing_service_lines_e12():
    """E-12: $5M/mo and $2M/mo lines unlock after 2 qualifying
    completions; the data line pays $0.2M/GB capped at 50 GB/yr."""
    assert service_rate("leo_constellation") * MONTH == pytest.approx(5e6)
    assert service_rate("stationkeeping") * MONTH == pytest.approx(2e6)
    assert service_unlocked("leo_constellation", {"CT-03": 2})
    assert not service_unlocked("leo_constellation",
                                {"CT-03": 1, "CT-05": 1})
    assert data_payment(10.0, 0.0) == pytest.approx(2e6)
    assert data_payment(10.0, 45.0) == pytest.approx(1e6)   # cap bites
    assert data_payment(10.0, 50.0) == 0.0


def test_service_suspension_machine():
    """E-12: failed quarterly check suspends from the next month;
    a satisfied quarter resumes the month after it."""
    lg = CashLedger(cash0=0.0)
    rate = service_rate("leo_constellation")
    lg.start("svc:leo_constellation", rate, 0.0)
    sl = ServiceLine("leo_constellation")
    assert sl.quarterly_check(lg, 200 * DAY, satisfied=False) == "suspend"
    t_stop = next_month_s(200 * DAY)
    assert sl.suspended
    assert sl.quarterly_check(lg, 290 * DAY, satisfied=True) == "resume"
    t_resume = next_month_s(290 * DAY)
    assert not sl.suspended
    earned_days = (t_stop / DAY) + (400.0 - t_resume / DAY)
    assert lg.balance(400 * DAY) == pytest.approx(rate * earned_days * DAY)


def test_offtake_stream_ct19():
    """CT-19: Pu238 at $10M/kg, ≤ 5 kg/yr → a $50M/yr income rate."""
    lg = CashLedger(cash0=0.0)
    offtake_stream(lg, "offtake:pu238", CT19_PU238_PER_KG, CT19_CAP_KG_Y, 0.0)
    assert lg.balance(YEAR) == pytest.approx(50e6, rel=1e-12)


# =============================================================================
# Contract v2 (E-9…E-11) over the persisted Program shape
# =============================================================================

def test_contract_v2_roundtrip_preserves_save_shape():
    """The v2 dict accepts a live Contract, adds defaulted new fields,
    and projects back to EXACTLY the persisted keys."""
    c = Contract("c_orbit", "Put a vessel in orbit", 100e6, 0.5 * YEAR)
    d = contract_v2(c)
    assert d["payout"] == pytest.approx(100e6)
    assert d["advance_frac"] == pytest.approx(ADVANCE_FRAC)
    assert d["tranches"] == 1 and d["crewed"] is False
    saved = contract_save_shape(d)
    assert set(saved) == {"contract_id", "description", "payout",
                          "deadline_s", "completed_t", "failed"}
    c2 = Contract(**saved)                      # restore path still valid
    assert c2.contract_id == "c_orbit" and not c2.failed


def test_e9_advance_and_ct17_tranches():
    """E-9: accept → 10% advance; CT-17 $1.5B in 3 tranches →
    $150M + 3 × $450M (sums to face value)."""
    adv, parts = tranche_amounts(1.5e9, 3)
    assert adv == pytest.approx(150e6)
    assert parts == [pytest.approx(450e6)] * 3
    assert adv + sum(parts) == pytest.approx(1.5e9)
    lg = CashLedger(cash0=0.0)
    c = contract_v2({"contract_id": "ct17", "description": "Mars sample",
                     "payout": 1.5e9, "deadline_s": 4 * YEAR, "tranches": 3})
    assert accept_contract(lg, c, 0.0) == pytest.approx(150e6)
    assert c["advance_paid_t"] == 0.0
    for _ in range(3):
        pay_tranche(lg, c, 1 * YEAR)
    assert pay_tranche(lg, c, 2 * YEAR) == 0.0      # nothing left
    assert lg.balance(2 * YEAR) == pytest.approx(1.5e9)


def test_e10_failure_economics():
    """E-10: repay advance + 20% of value + Prestige −10 + 1-yr
    customer lockout; destroyed payload adds $10M/t (mass delivery)
    or 2 × value (customer hardware)."""
    c = contract_v2({"contract_id": "ct05", "description": "LEO cargo",
                     "payout": 40e6, "deadline_s": YEAR})
    lg = CashLedger(cash0=0.0)
    accept_contract(lg, c, 0.0)
    fx = failure_cost(c, payload_destroyed_t=3.0)
    assert fx["cash"] == pytest.approx(-(4e6 + 8e6 + 30e6))
    assert fx["prestige"] == pytest.approx(-10.0)
    assert fx["customer_lockout_y"] == pytest.approx(1.0)
    fx2 = failure_cost(c, customer_hardware=True)   # CT-04/CT-22 class
    assert fx2["cash"] == pytest.approx(-(4e6 + 8e6 + 80e6))
    # no advance accepted yet → nothing to repay
    fresh = contract_v2({"contract_id": "x", "description": "x",
                         "payout": 40e6, "deadline_s": YEAR})
    assert failure_cost(fresh)["cash"] == pytest.approx(-8e6)


def test_e9_deadline_and_e11_urgency_decline():
    """E-9: deadline = accept + max(2×t_transfer, 90 d). E-11: urgent
    = ×1.5 pay on ×0.5 deadline; all rates decline 8%/yr."""
    assert default_deadline_s(0.0, 10 * DAY) == pytest.approx(90 * DAY)
    assert default_deadline_s(0.0, 100 * DAY) == pytest.approx(200 * DAY)
    pay, window = urgent_terms(8_000.0, 120 * DAY)
    assert pay == pytest.approx(12_000.0)
    assert window == pytest.approx(60 * DAY)
    assert RATE_DECLINE_PER_Y == pytest.approx(0.92)
    assert declined(8_000.0, 1.0) == pytest.approx(7_360.0)
    assert declined(8_000.0, 2.0) == pytest.approx(8_000.0 * 0.92 ** 2)


# =============================================================================
# Insurance (E-20…E-22)
# =============================================================================

def test_e21_premium_formula_and_bounds():
    """E-21: Premium = V × 6% × f_history × f_payload; bounds 3.6–12%
    before the nuclear rider; nuclear ×1.5 + 60-d licensing lead."""
    assert f_history(0, 0) == pytest.approx(2.0)        # <3 flights
    assert f_history(3, 3) == pytest.approx(1.0)        # 3–10 flights
    assert f_history(20, 11) == pytest.approx(0.6)      # >10 consecutive
    assert f_history(20, 2) == pytest.approx(1.0)       # streak reset
    assert premium(100e6, 0, 0) == pytest.approx(12e6)          # 12%
    assert premium(100e6, 20, 11) == pytest.approx(3.6e6)       # 3.6%
    assert premium(100e6, 0, 0, nuclear=True) == pytest.approx(18e6)
    assert NUCLEAR_LICENSE_LEAD_D == pytest.approx(60.0)
    # E-20: insurable value caps at $2B per risk
    assert insured_value(1.5e9, 1.0e9) == pytest.approx(2.0e9)
    assert insured_value(0.4e9, 0.1e9) == pytest.approx(0.5e9)


def test_e22_claims_total_crippled_and_envelope():
    """E-22: total loss pays insured value now; crippled pays 50%
    after the 7-d assessor; deep space (outside Earth SOI) denied."""
    lg = CashLedger(cash0=0.0)
    book = InsuranceBook()
    pol = book.underwrite(lg, 0.0, "lv1", 80e6, 20e6, flights=5,
                          consecutive_successes=5, amortize=False)
    assert pol.insured_value == pytest.approx(100e6)
    assert lg.balance(0.0) == pytest.approx(-6e6)       # 6% premium
    res = book.claim(lg, pol, 100 * DAY, total_loss=True)
    assert res["payout"] == pytest.approx(100e6)
    assert lg.balance(100 * DAY) == pytest.approx(94e6)
    # crippled: 50% lands only after the assessor event (7 d)
    lg2 = CashLedger(cash0=0.0)
    pol2 = book.underwrite(lg2, 0.0, "lv1", 100e6, amortize=False)
    res2 = book.claim(lg2, pol2, 30 * DAY, total_loss=False)
    assert res2["payout"] == pytest.approx(50e6)
    assert res2["payable_s"] == pytest.approx(37 * DAY)
    assert lg2.balance(36 * DAY) == pytest.approx(-12e6)
    assert lg2.balance(37 * DAY) == pytest.approx(38e6)
    # E-20 envelope: outside Earth SOI / after term / double-claim → denied
    pol3 = book.underwrite(lg2, 0.0, "lv1", 100e6, amortize=False)
    assert book.claim(lg2, pol3, 10 * DAY,
                      in_earth_soi=False)["status"] == "denied"
    assert book.claim(lg2, pol3, 2 * YEAR)["status"] == "denied"
    assert book.claim(lg2, pol2, 40 * DAY)["status"] == "denied"


def test_e22_fraud_guard_and_amortized_premium():
    """E-22: scuttling voids (claims need a failure event); engineered
    failures pay but reprice; the third strike in 10 yr ends offers
    for the line. Amortized premium totals the quoted premium."""
    lg = CashLedger(cash0=0.0)
    book = InsuranceBook()
    p1 = book.underwrite(lg, 0.0, "lv2", 100e6, amortize=False)
    assert book.claim(lg, p1, 1 * DAY,
                      player_commanded=True)["status"] == "voided"
    p2 = book.underwrite(lg, 2 * DAY, "lv2", 100e6, amortize=False)
    assert book.claim(lg, p2, 3 * DAY,
                      failure_event=False)["status"] == "voided"
    p3 = book.underwrite(lg, 4 * DAY, "lv2", 100e6, amortize=False)
    res = book.claim(lg, p3, 5 * DAY, engineered=True)
    assert res["status"] == "paid" and res["f_history_reset"]
    assert not book.offers_available("lv2", 6 * DAY)        # 3rd strike
    assert book.underwrite(lg, 6 * DAY, "lv2", 100e6) is None
    assert book.offers_available("lv3", 6 * DAY)            # per-line
    # amortized: stream over the 1-yr term integrates to the premium
    lg4 = CashLedger(cash0=0.0)
    p4 = book.underwrite(lg4, 0.0, "lv3", 100e6, amortize=True)
    assert lg4.balance(YEAR) == pytest.approx(-p4.premium, rel=1e-12)
    assert lg4.balance(2 * YEAR) == pytest.approx(-p4.premium, rel=1e-12)


# =============================================================================
# Stand-downs (E-23)
# =============================================================================

def test_e23_standdown_durations_and_freeze():
    """E-23: 30 d (ground fatality) · 90 d (in-flight) · 180 d
    (founder or multiple deaths) · Ironman ×2; crewed launches freeze,
    uncrewed continue; Prestige −5/month while active."""
    assert stand_down_duration_s(in_flight=False) == pytest.approx(30 * DAY)
    assert stand_down_duration_s(in_flight=True) == pytest.approx(90 * DAY)
    assert stand_down_duration_s(in_flight=True,
                                 founder=True) == pytest.approx(180 * DAY)
    assert stand_down_duration_s(in_flight=True,
                                 fatalities=2) == pytest.approx(180 * DAY)
    assert stand_down_duration_s(in_flight=False,
                                 ironman=True) == pytest.approx(60 * DAY)
    sd = StandDown(100 * DAY, 90 * DAY)
    assert not launch_allowed(sd, 150 * DAY, crewed=True)
    assert launch_allowed(sd, 150 * DAY, crewed=False)
    assert launch_allowed(sd, 190 * DAY, crewed=True)
    assert launch_allowed(None, 0.0, crewed=True)
    drift = sd.prestige_drift(100 * DAY, 190 * DAY)
    assert drift == pytest.approx(-5.0 * 90 * DAY / MONTH)


def test_e23_crewed_deadlines_pause():
    """Force majeure: crewed contract deadlines extend by the
    stand-down; uncrewed, completed, and unflagged ones don't."""
    sd = StandDown(0.0, 90 * DAY)
    crewed = contract_v2({"contract_id": "ct06", "description": "seats",
                          "payout": 30e6, "deadline_s": 200 * DAY,
                          "crewed": True})
    cargo = contract_v2({"contract_id": "ct05", "description": "cargo",
                         "payout": 16e6, "deadline_s": 200 * DAY})
    done = contract_v2({"contract_id": "ct13", "description": "done",
                        "payout": 100e6, "deadline_s": 200 * DAY,
                        "crewed": True, "completed_t": 10.0})
    legacy = Contract("c_orbit", "orbit", 100e6, 200 * DAY)  # no flag
    assert pause_crewed_deadlines([crewed, cargo, done, legacy], sd) == 1
    assert crewed["deadline_s"] == pytest.approx(290 * DAY)
    assert cargo["deadline_s"] == pytest.approx(200 * DAY)
    assert done["deadline_s"] == pytest.approx(200 * DAY)
    assert legacy.deadline_s == pytest.approx(200 * DAY)


# =============================================================================
# Investors & debt (E-17/E-18, DECISIONS F33)
# =============================================================================

def test_e17_round_table_pinned():
    """E-17: Seed $300M (pre-banked) · A 50→$250M/36mo · B 150→$600M/
    36mo · C 300→$1.5B/36mo · D 500→$4.0B/48mo."""
    assert ROUNDS["seed"].cash == pytest.approx(300e6)
    assert (ROUNDS["series_a"].gate, ROUNDS["series_a"].cash,
            ROUNDS["series_a"].promise_mo) == (50.0, 250e6, 36.0)
    assert (ROUNDS["series_b"].gate, ROUNDS["series_b"].cash) == (150.0,
                                                                  600e6)
    assert (ROUNDS["series_c"].gate, ROUNDS["series_c"].cash) == (300.0,
                                                                  1.5e9)
    assert (ROUNDS["series_d"].gate, ROUNDS["series_d"].cash,
            ROUNDS["series_d"].promise_mo) == (500.0, 4.0e9, 48.0)
    assert prestige_floor(500.0) == pytest.approx(400.0)    # E-14 floor
    assert prestige_floor(50.0) == pytest.approx(0.0)


def test_e17_promise_mechanics():
    """Raise needs Prestige ≥ gate + ladder order; deliver vests (no
    clawback); fail → Prestige −100, no rounds 5 yr, overhead +10%
    for 2 yr; post-fade (E-19) penalties are void."""
    lg = CashLedger(cash0=300e6)
    inv = Investors()
    assert not inv.can_raise("series_a", 49.0, 0.0)         # gate
    assert not inv.can_raise("series_b", 999.0, 0.0)        # ladder order
    cash = inv.raise_round(lg, "series_a", 50.0, 0.0, "first_docking")
    assert cash == pytest.approx(250e6)
    assert lg.balance(0.0) == pytest.approx(550e6)
    assert inv.promise["deadline_s"] == pytest.approx(36 * MONTH)
    assert not inv.can_raise("series_b", 999.0, 0.0)        # promise open
    assert inv.deliver_promise(35 * MONTH)                  # vests
    assert inv.promise is None
    inv.raise_round(lg, "series_b", 150.0, 2 * YEAR, "crewed_lunar")
    assert inv.promise_overdue(2 * YEAR + 37 * MONTH)
    fx = inv.fail_promise(5 * YEAR)
    assert fx["prestige"] == pytest.approx(-100.0)
    assert not inv.can_raise("series_c", 999.0, 9.9 * YEAR)  # 5-yr lockout
    assert inv.can_raise("series_c", 300.0, 10.1 * YEAR)
    assert inv.overhead_mult(6 * YEAR) == pytest.approx(1.10)
    assert inv.overhead_mult(7.1 * YEAR) == pytest.approx(1.0)
    inv.set_advisory()                                      # E-19 fade
    inv.promise = {"round_id": "series_c", "milestone": "x",
                   "deadline_s": 0.0}
    assert inv.fail_promise(11 * YEAR)["prestige"] == 0.0
    assert not inv.can_raise("series_c", 999.0, 11 * YEAR)  # no more rounds


def test_e18_bridge_loan():
    """E-18: one revolving loan ≤ 25% trailing-12-mo revenue, 1%/month
    interest as a G-9 cost rate (12% APR), bullet at 24 months,
    auto-repaid at Cash > 2 × principal."""
    assert BRIDGE_APR == pytest.approx(12 * BRIDGE_INTEREST_PER_MO)
    lg = CashLedger(cash0=10e6)
    lg.post(-100 * DAY + YEAR, "contract:ct03", 200e6)  # inside window
    lg.post(0.5 * YEAR, "round:series_a", 250e6)        # NOT revenue
    fs = FinanceState(ledger=lg)
    t = YEAR
    assert trailing_revenue(lg, t) == pytest.approx(200e6)
    loan = fs.draw_bridge(t)
    assert loan.principal == pytest.approx(BRIDGE_REVENUE_FRAC * 200e6)
    assert fs.draw_bridge(t) is None                # one at a time
    # 1%/month of principal accrues as a rate
    accrued = lg.balance(t + 5 * MONTH) - lg.balance(t)
    assert accrued == pytest.approx(-0.05 * 50e6, rel=1e-12)
    assert fs.service_bridge(t + 5 * MONTH,
                             cash=40e6) == "accruing"
    # rich → early bullet repay, then re-borrowable
    assert fs.service_bridge(t + 6 * MONTH, cash=150e6) == "repaid"
    assert fs.loan is None
    loan2 = fs.draw_bridge(t + 7 * MONTH, trailing=100e6)
    assert loan2.principal == pytest.approx(25e6)
    # term default with thin cash → Liquidation flow
    assert fs.service_bridge(loan2.drawn_s + BRIDGE_TERM_MO * MONTH,
                             cash=1e6) == "liquidation"


def test_e18_auto_draw_below_zero():
    lg = CashLedger(cash0=10e6)
    lg.start("overhead", -1e6 / DAY, 0.0)           # burns to negative
    lg.post(50 * DAY, "contract:x", 80e6)           # trailing revenue
    fs = FinanceState(ledger=lg)
    assert fs.auto_bridge(50 * DAY) is None         # still solvent
    assert fs.auto_bridge(364 * DAY) is not None    # cash < 0 → auto-draw
    assert fs.loan.principal == pytest.approx(20e6)


# =============================================================================
# Rescues, agency assist, death economics (F-2…F-4)
# =============================================================================

def test_f2_stranded_predicate_and_rescue():
    """F-2: stranded iff every harbor fails Δv (+5% margin) or
    transfer-time AND no other craft can reach; rescue purchases get
    7-d delivery; success pays Prestige +50."""
    assert harbor_reachable(105.0, 100.0, 10.0, 20.0)   # exactly 5% margin
    assert not harbor_reachable(104.9, 100.0, 10.0, 20.0)
    assert not harbor_reachable(200.0, 100.0, 25.0, 20.0)  # too slow
    assert is_stranded(20.0, [(100.0, 100.0, 10.0), (50.0, 200.0, 5.0)])
    assert not is_stranded(20.0, [(110.0, 100.0, 10.0)])
    assert not is_stranded(20.0, [(100.0, 100.0, 10.0)],
                           other_craft_can_reach=True)
    assert RESCUE_DELIVERY_WAIVER_D == pytest.approx(7.0)
    fs = FinanceState(ledger=CashLedger(cash0=0.0))
    r = fs.add_rescue(0.0, ls_days=40.0, subject="PELICAN-3")
    assert r.deadline_s == pytest.approx(40 * DAY)
    assert r.expired(41 * DAY) and not r.expired(39 * DAY)
    assert fs.resolve_rescue(r, success=True) == pytest.approx(50.0)
    assert fs.rescues == []


def test_f3_agency_assist_once():
    """F-3: once per campaign, max($500M, 50% of treasury), Prestige
    −100, min 30 d prep."""
    assert agency_assist_cost(600e6) == pytest.approx(500e6)
    assert agency_assist_cost(2e9) == pytest.approx(1e9)
    fs = FinanceState(ledger=CashLedger(cash0=600e6))
    fx = fs.agency_assist(0.0)
    assert fx["cost"] == pytest.approx(500e6)
    assert fx["prestige"] == pytest.approx(-100.0)
    assert fx["ready_s"] == pytest.approx(AGENCY_ASSIST_PREP_D * DAY)
    assert fs.ledger.balance(0.0) == pytest.approx(100e6)
    assert fs.agency_assist(1.0) is None                # spent


def test_f4_death_economics():
    """F-4: $10M/fatality death benefit; founder death = succession
    (Prestige −150, morale −25, overhead +10% for 1 yr; Ironman =
    game over); offers −50% for 6 months; stand-down per E-23."""
    fs = FinanceState(ledger=CashLedger(cash0=100e6))
    fx = fs.crew_fatality(10 * DAY, fatalities=2, in_flight=True)
    assert fs.ledger.balance(10 * DAY) == pytest.approx(100e6 - 2
                                                        * DEATH_BENEFIT)
    assert fx["prestige"] == pytest.approx(-200.0)
    assert fx["stand_down_d"] == pytest.approx(180.0)   # multiple deaths
    assert not fs.crewed_launch_allowed(100 * DAY)
    assert fs.offer_payout_mult(10 * DAY + 5 * MONTH) == pytest.approx(0.5)
    assert fs.offer_payout_mult(10 * DAY + 7 * MONTH) == pytest.approx(1.0)
    # founder, Ironman
    fs2 = FinanceState(ledger=CashLedger(cash0=100e6))
    fx2 = fs2.crew_fatality(0.0, in_flight=True, founder=True, ironman=True)
    assert fx2["prestige"] == pytest.approx(-150.0)
    assert fx2["morale_all_crew"] == pytest.approx(-25.0)
    assert fx2["stand_down_d"] == pytest.approx(360.0)  # 180 × Ironman 2
    assert fx2["game_over"] and not fx2["succession"]
    assert fs2.investors.overhead_mult(0.5 * YEAR) == pytest.approx(1.10)
    assert fs2.investors.overhead_mult(1.5 * YEAR) == pytest.approx(1.0)


# =============================================================================
# Endgame plumbing + save round-trip
# =============================================================================

def test_e19_fade_and_g9_liquidation_constants():
    """E-19: SSI ≥ 0.8 sustained 730 d; E-6 liquidation at 40%; G-9
    game-over needs bankrupt + no income + no crew."""
    assert FADE_SSI == pytest.approx(0.8)
    assert FADE_SUSTAIN_D == pytest.approx(730.0)
    assert SELL_FRACTION == pytest.approx(0.40)
    assert liquidation_value(100e6) == pytest.approx(40e6)
    assert not game_over(True, True, False)
    assert not game_over(True, False, True)
    assert game_over(True, False, False)


def test_finance_state_save_roundtrip_json_safe():
    """The whole FinanceState survives dict → JSON → dict with
    balances, policies, loans, stand-downs and rescues intact
    (additive save section; the Program section is untouched)."""
    lg = CashLedger(cash0=300e6)
    lg.start("overhead", legacy_overhead_rate(2, 1, 1.0), 0.0)
    lg.start("salaries", salary_rate(2, 1), 30 * DAY)
    lg.stop("salaries", 200 * DAY)
    lg.post(10 * DAY, "milestone:first_launch", 5e6)
    fs = FinanceState(ledger=lg)
    fs.insurance.underwrite(lg, 0.0, "lv1", 100e6, amortize=True)
    fs.insurance.strikes.append((5 * DAY, "lv1"))
    fs.investors.raise_round(lg, "series_a", 60.0, 0.0, "first_orbit")
    fs.crew_fatality(50 * DAY, in_flight=False)
    fs.add_rescue(60 * DAY, 25.0, "ROC-2")
    fs.draw_bridge(70 * DAY, trailing=80e6)

    blob = json.dumps(fs.to_dict())                 # must be JSON-safe
    fs2 = FinanceState.from_dict(json.loads(blob))
    for t in (0.0, 45 * DAY, 100 * DAY, 2 * YEAR):
        assert fs2.ledger.balance(t) == pytest.approx(fs.ledger.balance(t),
                                                      rel=1e-12)
    assert fs2.ledger.rate(100 * DAY) == pytest.approx(
        fs.ledger.rate(100 * DAY), rel=1e-12)
    assert fs2.stand_down.end_s == pytest.approx(80 * DAY)
    assert fs2.loan.principal == pytest.approx(20e6)
    assert fs2.investors.promise["milestone"] == "first_orbit"
    assert not fs2.agency_assist_used
    assert fs2.rescues[0].subject == "ROC-2"
    assert fs2.insurance.policies[0].insured_value == pytest.approx(100e6)
    assert len(fs2.insurance.strikes) == 1
    # monthly lines (S-13 HQ rows) survive too
    assert fs2.ledger.monthly_lines(100 * DAY) == pytest.approx(
        fs.ledger.monthly_lines(100 * DAY))
