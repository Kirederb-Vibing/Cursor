from __future__ import annotations

from datetime import date

MONTHS_DA = [
    "",
    "januar",
    "februar",
    "marts",
    "april",
    "maj",
    "juni",
    "juli",
    "august",
    "september",
    "oktober",
    "november",
    "december",
]

WEEKDAYS_DA = ["man", "tir", "ons", "tor", "fre", "lør", "søn"]

CADENCE_DA = {
    "monthly": "Månedligt",
    "quarterly": "Kvartalsvist",
    "semiannual": "Halvårligt",
    "yearly": "Årligt",
}

KIND_DA = {
    "income": "Indkomst",
    "expense": "Abonnement / betaling",
    "internal_transfer": "Intern overførsel",
    "external_transfer": "Ekstern overførsel",
}

CHARGE_RULE_DA = {
    "first": "Første dag i måneden",
    "last": "Sidste dag i måneden",
    "day_of_month": "Fast dag i måneden",
}


def format_dkk(ore: int, with_kr: bool = True) -> str:
    sign = "-" if ore < 0 else ""
    kr = abs(ore) / 100
    whole = int(kr)
    frac = int(round((kr - whole) * 100))
    if frac == 100:
        whole += 1
        frac = 0
    grouped = f"{whole:,}".replace(",", ".")
    text = f"{sign}{grouped},{frac:02d}"
    return f"{text} kr." if with_kr else text


def parse_dkk(raw: str) -> int:
    text = (raw or "").strip().lower().replace("kr.", "").replace("kr", "").replace(" ", "")
    if not text:
        return 0
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")
    return int(round(float(text) * 100))


def format_date(value: date) -> str:
    return f"{value.day}. {MONTHS_DA[value.month]} {value.year}"


def format_short_date(value: date) -> str:
    return f"{value.day}/{value.month}"


def month_label(year: int, month: int) -> str:
    return f"{MONTHS_DA[month][:3]} {year}"
