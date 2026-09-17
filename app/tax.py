from __future__ import annotations

from dataclasses import dataclass

# 2026-satser. Kilder: Skatteministeriet (personskatteloven) og gængs praksis for
# skatteværdi af negativ nettokapitalindkomst. Estimat — ikke en årsopgørelse.
AM_CONTRIBUTION_PCT = 8.0
BOTTOM_TAX_PCT = 12.01
PERSONAL_ALLOWANCE_ORE = 5_410_000  # 54.100 kr.
EMPLOYMENT_DEDUCTION_PCT = 12.75
EMPLOYMENT_DEDUCTION_MAX_ORE = 6_330_000  # 63.300 kr.
JOB_DEDUCTION_PCT = 4.5
JOB_DEDUCTION_MAX_ORE = 310_000  # 3.100 kr.
MIDDLE_TAX_PCT = 7.5
MIDDLE_TAX_THRESHOLD_AFTER_AM_ORE = 64_120_000  # 641.200 kr.
TOP_TAX_PCT = 7.5
TOP_TAX_THRESHOLD_AFTER_AM_ORE = 77_790_000  # 777.900 kr.
TOP_TOP_TAX_PCT = 5.0
TOP_TOP_TAX_THRESHOLD_AFTER_AM_ORE = 259_270_000  # 2.592.700 kr.

DEFAULT_MUNICIPAL_TAX_PCT = 25.05
INTEREST_EXTRA_PCT = 8.0
INTEREST_LOW_THRESHOLD_SINGLE_ORE = 5_000_000  # 50.000 kr.
INTEREST_LOW_THRESHOLD_COUPLE_ORE = 10_000_000  # 100.000 kr.

# Forenklet ejendomsværdiskat (ejerbolig). Grundskyld medtages ikke.
PROPERTY_TAX_LOW_PCT = 0.51
PROPERTY_TAX_HIGH_PCT = 1.40
PROPERTY_TAX_THRESHOLD_ORE = 920_000_000  # 9,2 mio. kr.


def _pct(ore: int, rate: float) -> int:
    return int(round(ore * rate / 100.0))


def interest_tax_value(
    negative_capital_income_ore: int,
    *,
    municipal_tax_pct: float = DEFAULT_MUNICIPAL_TAX_PCT,
    church_tax_pct: float = 0.0,
    extra_pct: float = INTEREST_EXTRA_PCT,
    is_couple: bool = False,
) -> int:
    """Skatteværdi af negativ nettokapitalindkomst (rentefradrag)."""
    amount = max(0, negative_capital_income_ore)
    low_limit = INTEREST_LOW_THRESHOLD_COUPLE_ORE if is_couple else INTEREST_LOW_THRESHOLD_SINGLE_ORE
    low = min(amount, low_limit)
    high = max(0, amount - low_limit)
    low_rate = municipal_tax_pct + church_tax_pct + extra_pct
    high_rate = municipal_tax_pct + church_tax_pct
    return _pct(low, low_rate) + _pct(high, high_rate)


def estimated_annual_interest(
    remaining_principal_ore: int,
    interest_rate_pct: float,
    contribution_rate_pct: float,
    override_ore: int | None = None,
) -> int:
    if override_ore is not None:
        return max(0, override_ore)
    return _pct(max(0, remaining_principal_ore), interest_rate_pct + contribution_rate_pct)


def property_value_tax(property_value_ore: int | None) -> int:
    if not property_value_ore:
        return 0
    value = max(0, property_value_ore)
    low = min(value, PROPERTY_TAX_THRESHOLD_ORE)
    high = max(0, value - PROPERTY_TAX_THRESHOLD_ORE)
    return _pct(low, PROPERTY_TAX_LOW_PCT) + _pct(high, PROPERTY_TAX_HIGH_PCT)


@dataclass
class MortgageMarchEstimate:
    tax_year: int
    payout_month: str
    annual_interest_ore: int
    rentefradrag_value_ore: int
    forskud_interest_ore: int
    forskud_value_ore: int
    property_tax_ore: int
    estimated_march_payout_ore: int
    low_rate_pct: float
    high_rate_pct: float
    low_threshold_ore: int
    disclaimer: str


def march_payout_estimate(
    *,
    tax_year: int,
    remaining_principal_ore: int,
    interest_rate_pct: float,
    contribution_rate_pct: float,
    annual_interest_override_ore: int | None,
    forskud_interest_ore: int,
    property_value_ore: int | None,
    municipal_tax_pct: float,
    church_tax_pct: float,
    is_couple: bool,
) -> MortgageMarchEstimate:
    annual_interest = estimated_annual_interest(
        remaining_principal_ore,
        interest_rate_pct,
        contribution_rate_pct,
        annual_interest_override_ore,
    )
    extra = INTEREST_EXTRA_PCT
    rentefradrag = interest_tax_value(
        annual_interest,
        municipal_tax_pct=municipal_tax_pct,
        church_tax_pct=church_tax_pct,
        extra_pct=extra,
        is_couple=is_couple,
    )
    forskud_value = interest_tax_value(
        max(0, forskud_interest_ore),
        municipal_tax_pct=municipal_tax_pct,
        church_tax_pct=church_tax_pct,
        extra_pct=extra,
        is_couple=is_couple,
    )
    evs = property_value_tax(property_value_ore)
    # Marts-udbetalingen her er forskellen på rentefradragets skatteværdi og det,
    # der allerede er indregnet i forskud. Ejendomsværdiskat vises separat.
    payout = rentefradrag - forskud_value
    return MortgageMarchEstimate(
        tax_year=tax_year,
        payout_month=f"marts {tax_year + 1}",
        annual_interest_ore=annual_interest,
        rentefradrag_value_ore=rentefradrag,
        forskud_interest_ore=max(0, forskud_interest_ore),
        forskud_value_ore=forskud_value,
        property_tax_ore=evs,
        estimated_march_payout_ore=payout,
        low_rate_pct=municipal_tax_pct + church_tax_pct + extra,
        high_rate_pct=municipal_tax_pct + church_tax_pct,
        low_threshold_ore=(
            INTEREST_LOW_THRESHOLD_COUPLE_ORE if is_couple else INTEREST_LOW_THRESHOLD_SINGLE_ORE
        ),
        disclaimer=(
            "Estimat til planlægning. Årsopgørelsen afhænger af hele årets indkomst, "
            "andre fradrag, indberetninger fra realkredit/bank og din forskudsopgørelse."
        ),
    )


@dataclass
class SimpleIncomeTax:
    gross_ore: int
    am_ore: int
    employment_deduction_ore: int
    job_deduction_ore: int
    municipal_ore: int
    bottom_tax_ore: int
    middle_tax_ore: int
    top_tax_ore: int
    church_ore: int
    total_tax_ore: int
    net_ore: int


def rough_income_tax(
    gross_ore: int,
    *,
    municipal_tax_pct: float,
    church_tax_pct: float,
) -> SimpleIncomeTax:
    """Meget forenklet indkomstskat af A-indkomst. Bruges kun som pejlemærke."""
    gross = max(0, gross_ore)
    am = _pct(gross, AM_CONTRIBUTION_PCT)
    personal = gross - am
    employment = min(_pct(gross, EMPLOYMENT_DEDUCTION_PCT), EMPLOYMENT_DEDUCTION_MAX_ORE)
    job = min(_pct(gross, JOB_DEDUCTION_PCT), JOB_DEDUCTION_MAX_ORE)
    taxable = max(0, personal - PERSONAL_ALLOWANCE_ORE - employment - job)
    municipal = _pct(taxable, municipal_tax_pct)
    church = _pct(taxable, church_tax_pct)
    bottom = _pct(max(0, personal - PERSONAL_ALLOWANCE_ORE), BOTTOM_TAX_PCT)
    after_am = personal
    middle = _pct(max(0, after_am - MIDDLE_TAX_THRESHOLD_AFTER_AM_ORE), MIDDLE_TAX_PCT)
    top = _pct(max(0, after_am - TOP_TAX_THRESHOLD_AFTER_AM_ORE), TOP_TAX_PCT)
    top_top = _pct(max(0, after_am - TOP_TOP_TAX_THRESHOLD_AFTER_AM_ORE), TOP_TOP_TAX_PCT)
    income_taxes = municipal + church + bottom + middle + top + top_top
    total = am + income_taxes
    return SimpleIncomeTax(
        gross_ore=gross,
        am_ore=am,
        employment_deduction_ore=employment,
        job_deduction_ore=job,
        municipal_ore=municipal,
        bottom_tax_ore=bottom,
        middle_tax_ore=middle,
        top_tax_ore=top + top_top,
        church_ore=church,
        total_tax_ore=total,
        net_ore=gross - total,
    )
