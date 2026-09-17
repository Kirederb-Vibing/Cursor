from __future__ import annotations

from app.formatting import format_dkk
from app.planning import Occurrence


def to_ics(occurrences: list[Occurrence], calendar_name: str = "Fælleskassen") -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Faelleskassen//DA",
        f"X-WR-CALNAME:{calendar_name}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    for occ in occurrences:
        summary = f"{occ.name} ({format_dkk(occ.amount_ore)})".replace("\n", " ")
        desc = f"Type: {occ.kind}\\nKategori: {occ.category or '-'}"
        stamp = occ.date.strftime("%Y%m%d")
        uid = f"{occ.item_id}-{stamp}@faelleskassen"
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{stamp}T080000Z",
                f"DTSTART;VALUE=DATE:{stamp}",
                f"SUMMARY:{summary}",
                f"DESCRIPTION:{desc}",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
