# Business Trips · Frontend · RefCard03–04

Tim Held, M324. Eigenes React/Vite-Repository aus dem Unterrichtsstarter `v1-start`.

## Start und Tests

```bash
npm ci
npm test
npm run lint
npm run build
npm run dev
```

Vite leitet `/v1` in der Entwicklung auf `http://localhost:8080` weiter. Die Produktions-App verwendet denselben Origin wie die API. Im nginx-Container kann `BACKEND_ORIGIN` beim Start gesetzt werden, standardmässig `http://backend:8080`.

Das gemeinsame lokale Setup liegt im Backend-Repo. Beide Repos nebeneinander als `backend` und `frontend` auschecken und dort `docker compose up -d --build --wait` ausführen. Danach ist die App unter http://localhost:3000 erreichbar.

## Pipeline

Eigene Test- und Build-Jobs mit npm-Cache. Der Build wird als Artefakt gespeichert. Auf `main` folgen nach Einrichtung optional EC2-Transfer, Docker-Hub-Push und ECS-Deployment. Images werden mit `prod01`, `latest` und vollständigem Commit-SHA veröffentlicht. Docker-Publishing baut für amd64 und arm64; ECS verwendet amd64.

Die Secrets und Freischaltvariablen entsprechen der [Backend-Konfiguration](https://github.com/AdminGodZ/bbw-m324-biztrips-fullstack-actions-aws-backend). EC2-Secrets liegen im Environment `production`; AWS-Lab-Zugang und Docker-Hub-Zugang liegen als verschlüsselte Repository-Secrets vor. `AWS_CREDENTIALS` enthält den vollständigen `[default]`-Block aus AWS Details und muss nach Session-Ablauf erneuert werden.

## Abgenommene Anwendung

EC2: http://13.220.4.150

ECS: http://bbw-m324-Alb-BD6YtmTDd85r-713603972.us-east-1.elb.amazonaws.com

Der [abgenommene Run](https://github.com/AdminGodZ/bbw-m324-biztrips-fullstack-actions-aws-frontend/actions/runs/42182874967) ist für Test, Build, EC2, Docker Hub und ECS erfolgreich. `task-definition.json` dokumentiert die registrierte Task-Konfiguration. Screenshots und der gemeinsame Nachweis sind im Backend-Repo verlinkt.

## Nachweis

Der gemeinsame [Nachweis](https://github.com/AdminGodZ/bbw-m324-biztrips-fullstack-actions-aws-backend/blob/main/docs/NACHWEIS.md) trennt lokale Tests, CI und Live-Deployments. Die ursprüngliche README ist unter `docs/UPSTREAM-README.md` erhalten; die Aufgaben stehen unter `docs/exercises`.
