# n8n

Fælleskassen er bygget til HTTP Request-noder. Ingen speciel n8n-node er påkrævet.

## Autentificering

```
X-API-Key: <nøgle>
```

eller

```
Authorization: Bearer <nøgle>
```

Nøglen vises under **Indstillinger**. OpenAPI/Swagger ligger på `/docs` og `/openapi.json`.

## Typiske kald

Opret eller opdatér et abonnement (idempotent via `external_id`):

```http
POST /api/v1/subscriptions
Content-Type: application/json

{
  "name": "Netflix",
  "amount_dkk": 149,
  "cadence": "monthly",
  "charge_rule": "last",
  "starts_on": "2026-09-17",
  "from_account_id": 3,
  "external_id": "netflix-hovedkonto"
}
```

Samme `external_id` igen opdaterer posten i stedet for at oprette en ny.

Andre endpoints:

| Metode | Sti | Brug |
| --- | --- | --- |
| POST | `/api/v1/items` | Indkomst, udgift, intern/ekstern overførsel |
| GET | `/api/v1/overview` | 12-måneders plan + forventede overførsler |
| GET | `/api/v1/overview/upcoming` | Næste poster |
| POST | `/api/v1/people` | Ny person |
| POST | `/api/v1/accounts` | Ny konto |
| POST | `/api/v1/mortgages` | Huslån til marts-estimat |

`cadence`: `monthly` · `quarterly` · `semiannual` · `yearly`  
`charge_rule`: `first` · `last` · `day_of_month` (+ `charge_day`)

Tom `ends_on` betyder, at posten kører, indtil n8n eller UI sletter den.

## Udgående webhook

Sæt n8n webhook-URL under Indstillinger. Fælleskassen poster så events:

- `item.created` / `item.updated` / `item.deleted`
- `person.created`
- `account.created`
- `mortgage.updated`

Hvis n8n er nede, gemmes posten alligevel.

Importer `create-subscription.json` som udgangspunkt.
