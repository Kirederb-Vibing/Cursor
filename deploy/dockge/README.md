# Dockge + Pangolin

Kopiér `compose.yaml` og `.env` ind i en ny Dockge-stack ved navn **faelleskassen**.

1. Dockge → **Compose** → **+ New Stack**
2. Navn: `faelleskassen`
3. Paste `compose.yaml`
4. Fanen **Env** → paste `.env`
5. Ret `PUBLIC_URL` til dit Pangolin-domæne
6. **Deploy**

Stacken åbner **ingen porte** på værten. Den slutter sig til det eksisterende Docker-netværk `proxy` (sæt `PROXY_NETWORK` hvis det hedder noget andet).

I Pangolin:

- Type: HTTP
- Destinationshost: `faelleskassen`
- Destinationsport: `8080`
- URL: `http://faelleskassen:8080`

Testhusstanden indlæses automatisk (`SEED_DEMO=true`). API-nøgle til n8n / Home Assistant i test: `fk_test_n8n_ha_local`.
