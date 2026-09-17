# Home Assistant

Fælleskassen udstiller overblikket som JSON, så du kan bruge det i dashboards uden en custom component.

## REST-sensorer

Se `rest.yaml`. Peg `resource` på:

```
http://<host>:8080/api/v1/ha/sensors
```

Header: `X-API-Key: <nøgle fra Indstillinger>`.

Flade felter til templates:

- `denne_maaned_netto`
- `naeste_maaned_netto`
- `forventet_marts_udbetaling`
- `naeste_overfoersel_navn` / `_beloeb` / `_dato`
- `naeste_abonnement_navn` / `_beloeb`
- `markdown` — klar liste til Markdown-kort

`sensors[]` er den samme data i HA-lignende objekter.

## Kalender

`GET /api/v1/ha/calendar.ics?api_key=...` giver 18 måneder frem.

Brug HACS-integrationen **ICS Calendar** (eller tilsvarende) med den URL. Så lander abonnementer og overførsler på en kalender-enhed, du kan vise i Lovelace.

## Tips

- Sæt `scan_interval` til 300 sekunder. Planlægning ændrer sig ikke hvert minut.
- Kør containeren på samme Docker-netværk som Home Assistant, og brug tjenestenavnet `faelleskassen`.
- API-nøglen kan tvinges med miljøvariablen `API_KEY`.
