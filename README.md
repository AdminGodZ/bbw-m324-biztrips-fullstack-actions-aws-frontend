# Business Trips · Frontend · RefCard05 (Full Stack auf AWS)

Tim Held, M324. React 19 + Vite · nginx · ECR · ECS Fargate · GitHub Actions.

**→ Dokumentation RefCard05: [docs/REFCARD05.md](docs/REFCARD05.md)**

| | |
|---|---|
| Backend-Repo (inkl. Infrastruktur und ausführlicher Doku) | <https://github.com/AdminGodZ/bbw-m324-biztrips-fullstack-actions-aws-backend> |
| Lokale Entwicklung (Compose) | <https://github.com/AdminGodZ/bbw-m324-biztrips-fullstack-compose> |
| Pipeline | [`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml): lint → test → build → Image → ECR → ECS + Verifikation |

## Entwicklung

```bash
npm ci
npm run lint && npm test && npm run build
npm run dev        # Vite leitet /v1 an http://localhost:8080 weiter
```

| Variable | Zeitpunkt | Bedeutung |
|---|---|---|
| `VITE_API_BASE_URL` | Build (GitHub-Variable) | URL des Backend-Service, auf ECS die ALB-URL |
| `APP_VERSION` | Build-Arg | Release-Version → Footer und `/version.json` |
| `API_BASE_URL` | Container-Start (optional) | übersteuert die Backend-URL zur Laufzeit, Compose: `/` |
| `BACKEND_ORIGIN` | Container-Start | Ziel des nginx-Proxys für `/v1` und `/actuator`, Compose: `http://backend:8080` |

Ältere Stände (RefCard03/04): [docs/CR-01-review.md](docs/CR-01-review.md), [docs/exercises](docs/exercises), ursprüngliche README unter [docs/UPSTREAM-README.md](docs/UPSTREAM-README.md).
