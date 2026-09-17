from app.tax import interest_tax_value, march_payout_estimate


def test_single_interest_under_threshold():
    value = interest_tax_value(3_000_000, municipal_tax_pct=25.05, church_tax_pct=0, is_couple=False)
    # 30.000 * 33.05% = 9.915 kr. = 991_500 øre
    assert value == 991_500


def test_couple_interest_over_threshold():
    value = interest_tax_value(12_000_000, municipal_tax_pct=25.05, church_tax_pct=0, is_couple=True)
    # 100.000 * 33.05% + 20.000 * 25.05% = 33.050 + 5.010 = 38.060
    assert value == 3_806_000


def test_march_payout_is_difference_versus_forskud():
    estimate = march_payout_estimate(
        tax_year=2026,
        remaining_principal_ore=0,
        interest_rate_pct=0,
        contribution_rate_pct=0,
        annual_interest_override_ore=3_000_000,
        forskud_interest_ore=3_000_000,
        property_value_ore=None,
        municipal_tax_pct=25.05,
        church_tax_pct=0,
        is_couple=False,
    )
    assert estimate.payout_month == "marts 2027"
    assert estimate.estimated_march_payout_ore == 0
    assert estimate.rentefradrag_value_ore == estimate.forskud_value_ore


def test_march_payout_full_when_nothing_in_forskud():
    estimate = march_payout_estimate(
        tax_year=2026,
        remaining_principal_ore=248_000_000,
        interest_rate_pct=4.0,
        contribution_rate_pct=0.4,
        annual_interest_override_ore=None,
        forskud_interest_ore=0,
        property_value_ore=None,
        municipal_tax_pct=25.05,
        church_tax_pct=0,
        is_couple=True,
    )
    assert estimate.annual_interest_ore == 10_912_000  # 2.480.000 * 4.4%
    assert estimate.estimated_march_payout_ore == estimate.rentefradrag_value_ore
    assert estimate.estimated_march_payout_ore > 0
