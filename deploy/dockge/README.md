# Dockge

Kopiér `compose.yaml` og `.env` ind i en ny Dockge-stack ved navn **faelleskassen**.

1. Dockge → **Compose** → **+ New Stack**
2. Navn: `faelleskassen`
3. Paste `compose.yaml`
4. Fanen **Env** → paste `.env`
5. **Deploy**
6. Åbn `http://<din-server>:8080`

Stacken trækker `ghcr.io/kirederb-vibing/cursor:latest`. Testhusstanden indlæses automatisk (`SEED_DEMO=true`).

API-nøgle til n8n / Home Assistant i test: `fk_test_n8n_ha_local`.

`APP_PASSWORD` er tom, så UI ikke kræver login. Sæt en værdi, hvis den skal bag basic auth.

Hvis Dockge ikke kan trække imaget, log ind på GHCR (`docker login ghcr.io`) eller gør pakken public under GitHub → Packages.
