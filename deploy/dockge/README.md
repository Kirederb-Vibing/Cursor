# Dockge

Kopiér `compose.yaml` og `.env` ind i en ny Dockge-stack ved navn **faelleskassen**.

1. Dockge → **Compose** → **+ New Stack**
2. Navn: `faelleskassen`
3. Paste `compose.yaml`
4. Fanen **Env** → paste `.env`
5. **Deploy**
6. Åbn `http://<din-server>:8080`

Første start bygger image fra GitHub-branchen (tager et par minutter). Testhusstanden indlæses automatisk (`SEED_DEMO=true`).

API-nøgle til n8n / Home Assistant i test: `fk_test_n8n_ha_local`.

`APP_PASSWORD` er tom, så UI ikke kræver login. Sæt en værdi, hvis den skal bag basic auth.

Hvis GitHub-repoet er privat, kan Docker ikke hente `build.context`. Klon så repoet ind i stack-mappen og skift `build.context` til `.`.
