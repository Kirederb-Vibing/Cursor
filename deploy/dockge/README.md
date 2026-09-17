# Dockge + Pangolin

Kopiér `compose.yaml` og `.env` ind i en ny Dockge-stack ved navn **faelleskassen**.

1. Dockge → **Compose** → **+ New Stack**
2. Navn: `faelleskassen`
3. Paste `compose.yaml`
4. Fanen **Env** → paste `.env`
5. Ret `PUBLIC_URL` til dit Pangolin-domæne
6. **Deploy**

SQLite ligger i stack-mappen som `data/` (bind-mount `./data:/data`), ved siden af `compose.yaml` — ikke i Docker-volumes. Slet `data/` i stacken for en frisk start.

Stacken åbner **ingen porte** på værten. Den slutter sig til det eksisterende Docker-netværk `proxy` (sæt `PROXY_NETWORK` hvis det hedder noget andet).

I Pangolin:

- Type: HTTP
- Destinationshost: `faelleskassen`
- Destinationsport: `8080`
- URL: `http://faelleskassen:8080`

Testhusstanden indlæses **ikke** automatisk. Første åbning viser opsætningsguiden, hvor den første person bliver administrator med kode. Andre kan tilføjes uden login.

API-nøgle til n8n / Home Assistant sættes under Indstillinger efter login. `API_KEY` i `.env` kan stadig tvinge nøglen.

UI-adgang styres af person-login fra opsætningen. Der er ikke et særskilt app-kodeord.
