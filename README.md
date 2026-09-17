# Fælleskassen

Lille self-hosted tjeneste til **økonomisk planlægning** i en husstand: indkomster, abonnementer, interne flytninger, andre faste overførsler og et estimat af rentefradrag til årsopgørelsen i marts.

Én Docker-container. SQLite på et volume. Dansk UI. REST-API til **n8n** og **Home Assistant**.

Det er et overblik over *det du har sagt vil ske* — ikke en bankforbindelse og ikke Skattestyrelsen.

## Kør den

### Byg lokalt

```bash
docker compose up --build
```

Åbn [http://localhost:8080](http://localhost:8080).

### Dockge

Kopiér [`deploy/dockge/compose.yaml`](deploy/dockge/compose.yaml) og [`deploy/dockge/.env`](deploy/dockge/.env) ind i en ny stack. Se [`deploy/dockge/README.md`](deploy/dockge/README.md).

### Image fra GitHub

Hvert push til `main` (og tags `v*`) bygger og lægger et image i GitHub Container Registry. CI kører tests først.

```bash
docker pull ghcr.io/kirederb-vibing/cursor:latest
docker compose up
```

`docker-compose.yml` peger på det image og kan stadig bygge fra kilden med `--build`.

Første gang skal pakken i GHCR være tilgængelig for den maskine, der trækker (public, eller `docker login ghcr.io`).

Valgfrie miljøvariabler:

| Variabel | Betydning |
| --- | --- |
| `API_KEY` | Fast API-nøgle (ellers oprettes en og vises under Indstillinger) |
| `APP_PASSWORD` | Sætter HTTP basic på UI |
| `SEED_DEMO` | `true` indlæser eksempelhusstand første gang |
| `DATA_DIR` | Standard `/data` i containeren |

## Hvad v1 kan

- Husstand med personer og interne konti
- Poster med kadence: måned, kvartal, halvår, år
- Hævedag: første i måneden, sidste i måneden, eller fast dato (31. bliver 28. i februar)
- Poster **uden slutdato kører videre**, indtil de slettes eller sættes på pause
- Overblik for husstand eller person, forventede overførsler, 12-måneders tabel
- Huslån → estimeret rente/bidrag → skatteværdi af rentefradrag → forskel mod forskud → **marts næste år**
- 2026-satser (bundskat, AM, personfradrag, beskæftigelsesfradrag, kommuneskat, 33/25 % rentefradrag). Estimat, ikke årsopgørelse

## Home Assistant

Overblikket er JSON, så det kan ligge på et dashboard:

- `GET /api/v1/ha/sensors` — tal + markdown-liste
- `GET /api/v1/ha/calendar.ics` — kalender 18 måneder frem

Eksempler: [`integrations/homeassistant/`](integrations/homeassistant/).

## n8n

- Header `X-API-Key` eller `Authorization: Bearer`
- `POST /api/v1/subscriptions` opretter et abonnement; `external_id` gør kaldet idempotent
- `POST /api/v1/items` til indkomst og overførsler
- Valgfri udgående webhook ved ændringer

Eksempler: [`integrations/n8n/`](integrations/n8n/). Interaktiv API: `/docs`.

## Skat

Marts-tallet er:

1. Årlig rente + bidrag (eller din override)
2. Skatteværdi ~33 % af de første 50.000 kr. negativ nettokapitalindkomst (100.000 for par), ~25 % af resten, justeret med din kommune- og kirkeskat
3. Minus den skatteværdi, der allerede sidder i forskud
4. Minus forenklet ejendomsværdiskat, hvis du angiver offentlig værdi

Satser kan rettes under Indstillinger. Kilder: Skatteministeriets beløbsgrænser 2026 og gængs praksis for rentefradragets skatteværdi.

## Udvikling

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
uvicorn app.main:app --reload --port 8080
```
