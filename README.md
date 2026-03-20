# les577.fr

Visualisation des données publiques de l'Assemblée Nationale française.

Chaque député, chaque vote, chaque amendement — présentés clairement, à partir des données officielles.

🌐 [les577.fr](https://les577.fr)

---

## Fonctionnalités

- **Hémicycle interactif** — visualisation des 577 sièges avec les vraies positions, colorisés par groupe parlementaire
- **Fiches député** — activité par jour sur toute la législature (votes, prises de parole, amendements), style calendrier de contributions
- **Scrutins** — liste et détail de chaque vote avec résultat par siège dans l'hémicycle
- **Amendements** — liste par député

---

## Stack technique

| Couche | Technologie |
|---|---|
| Back-end | Python 3.12 + FastAPI |
| Front-end | Svelte 5 |
| Animations | Rive |
| Base de données | Scaleway Managed PostgreSQL |
| Ingestion open data | Scaleway Serverless Functions + CRON |
| Infra | Terraform (provider Scaleway) |
| CI/CD | GitHub Actions |
| Hébergement | Scaleway 🇫🇷 (Paris) |

---

## Sources de données

- [data.assemblee-nationale.fr](https://data.assemblee-nationale.fr) — API officielle de l'Assemblée Nationale
- [data.gouv.fr](https://www.data.gouv.fr/organizations/assemblee-nationale/datasets) — jeux de données ouverts
- [NosDéputés.fr](https://www.nosdeputes.fr) par [Regards Citoyens](https://www.regardscitoyens.org) — données complémentaires (réseaux sociaux, positions hémicycle)

> Les données issues de NosDéputés.fr sont publiées sous licence [ODbL](https://opendatacommons.org/licenses/odbl/).
> Attribution : *"NosDéputés.fr par Regards Citoyens à partir de l'Assemblée nationale"*

---

## Développement local

### Prérequis

- Python 3.12+
- Node.js 20+
- Docker (pour PostgreSQL en local)
- Terraform CLI
- Claude Code (`npm install -g @anthropic-ai/claude-code`)

### Installation

```bash
git clone git@github.com:caronicolas/577.git
cd 577
```

**Back-end**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # remplir les variables
alembic upgrade head         # créer les tables
uvicorn api.main:app --reload
```

**Front-end**
```bash
cd frontend
npm install
npm run dev
```

L'API est disponible sur `http://localhost:8000`
Le front est disponible sur `http://localhost:5173`

### Variables d'environnement

Copier `.env.example` en `.env` et remplir :

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/les577
ASSEMBLEE_API_BASE_URL=https://data.assemblee-nationale.fr/api
GOUV_API_BASE_URL=https://www.data.gouv.fr/api/1
NOSDEPUTES_API_BASE_URL=https://www.nosdeputes.fr
```

---

## Infra

L'infrastructure est définie dans `/infra` avec Terraform (provider Scaleway).

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars   # remplir les credentials Scaleway
terraform init
terraform plan
terraform apply
```

---

## Déploiement

Le déploiement est automatisé via GitHub Actions sur chaque push sur `main` :

- `deploy-backend.yml` — build et déploie l'API FastAPI sur Scaleway Serverless Containers
- `deploy-frontend.yml` — build et déploie le front Svelte
- `deploy-infra.yml` — applique les changements Terraform

---

## Contribuer

Les contributions sont les bienvenues. Quelques règles :

- Commits en français au format conventionnel (`feat:`, `fix:`, `chore:`, `infra:`)
- PR obligatoire pour merger sur `main`
- Lancer `ruff` et `black` avant de soumettre du code Python
- Lancer `npm run check` avant de soumettre du code Svelte

---

## Licence

Code source : [AGPL](LICENSE)

Données affichées : soumises aux licences de leurs sources respectives (voir section Sources).
