# CLAUDE.md — Données Assemblée Nationale

## Vue d'ensemble du projet

Application web citoyenne affichant les données publiques de l'Assemblée Nationale française.
Lecture seule, pas d'authentification utilisateur, pas de temps réel (données batch).

**Sources de données officielles**
- API open data AN : https://data.assemblee-nationale.fr
- Data.gouv.fr (AN) : https://www.data.gouv.fr/organizations/assemblee-nationale/datasets

**Source complémentaire**
- Regards Citoyens / NosDéputés.fr : SVG hémicycle + données sociales
  Licence ODbL — attribution obligatoire : "NosDéputés.fr par Regards Citoyens à partir de l'Assemblée nationale"
  SVG hémicycle : https://github.com/regardscitoyens/mapHemicycle/blob/gh-pages/img/hemicycle-an.svg

---

## Stack technique

| Couche              | Technologie                                              |
|---------------------|----------------------------------------------------------|
| Back-end API        | Python 3.12 + FastAPI                                    |
| Front-end           | Svelte 5 (SPA)                                           |
| Animations          | Rive (runtime JS)                                        |
| Base de données     | Scaleway Managed PostgreSQL                              |
| Ingestion open data | Scaleway Serverless Functions (Python) + CRON triggers   |
| Infra               | Terraform (provider Scaleway officiel)                   |
| CI/CD               | GitHub Actions                                           |
| Cloud provider      | Scaleway 🇫🇷 (région fr-par)                             |

---

## Structure du projet

```
/
├── CLAUDE.md
├── backend/
│   ├── api/
│   │   ├── main.py            # App FastAPI, CORS, lifespan
│   │   └── routers/
│   │       ├── deputes.py
│   │       ├── votes.py
│   │       └── amendements.py
│   ├── ingestion/
│   │   ├── assemblee/         # Parsers data.assemblee-nationale.fr
│   │   └── gouv/              # Parsers data.gouv.fr
│   ├── db/
│   │   ├── models.py          # Modèles SQLAlchemy 2.0
│   │   └── migrations/        # Alembic
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── routes/
│   │   │   ├── +page.svelte              # /
│   │   │   ├── deputes/
│   │   │   │   ├── +page.svelte          # /deputes
│   │   │   │   └── [id]/+page.svelte     # /depute/:id
│   │   │   └── votes/
│   │   │       ├── +page.svelte          # /votes
│   │   │       └── [id]/+page.svelte     # /votes/:id
│   │   ├── lib/
│   │   │   ├── components/
│   │   │   │   ├── Hemicycle.svelte          # Réutilisé sur / et /votes/:id
│   │   │   │   ├── HemicycleTooltip.svelte   # Popup survol siège
│   │   │   │   └── ActivityCalendar.svelte   # Calendrier style GitHub contributions
│   │   │   ├── animations/               # Fichiers .riv Rive
│   │   │   └── data/
│   │   │       └── hemicycle-seats.json  # Coordonnées x/y des 577 sièges (extrait du SVG Regards Citoyens)
│   │   └── app.css
│   └── static/
├── infra/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── modules/
│       ├── database/          # Managed PostgreSQL
│       ├── containers/        # Serverless Containers (API FastAPI)
│       └── functions/         # Serverless Functions (ingestion CRON)
└── .github/
    └── workflows/
        ├── deploy-backend.yml
        ├── deploy-frontend.yml
        └── deploy-infra.yml
```

---

## Pages & Fonctionnalités

### `/` — Hémicycle interactif
Visualisation des 577 sièges disposés en arc courbe reflétant les vraies positions dans l'hémicycle.
Données de positionnement : `hemicycle-seats.json` extrait du SVG open data de Regards Citoyens.
Chaque carré SVG = un siège, colorisé par groupe parlementaire.
- Survol → tooltip (photo député, nom, groupe parlementaire, circonscription)
- Clic → navigation vers `/depute/:id`
- Animation d'entrée Rive : apparition progressive des sièges au chargement

### `/deputes` — Liste des députés
- Filtres : groupe parlementaire, département
- Recherche par nom

### `/depute/:id` — Fiche individuelle
- **Calendrier d'activité** style GitHub contributions
  - Période : 17e législature en cours (depuis juin 2024)
  - Phase 2 : accès aux législatures précédentes si le député était déjà en poste
  - Palette :
    - Rouge      : absent
    - Vert clair : présent (sans vote ni intervention)
    - Vert       : a voté
    - Vert foncé : a voté + prise de parole ou amendement déposé
  - Tooltip au survol : détail de l'activité du jour
- Liste des votes auxquels le député a participé
- Liste des amendements déposés
- Liens réseaux sociaux si disponibles dans les données (source : Regards Citoyens)

### `/votes` — Liste des scrutins
- Classement chronologique décroissant
- Recherche par intitulé
- Clic → navigation vers `/votes/:id`

### `/votes/:id` — Détail d'un scrutin
- Intitulé du vote, auteur (personne ou groupe ayant déposé l'amendement/proposition)
- Lien vers le document source officiel sur assemblee-nationale.fr
- Hémicycle (même composant `Hemicycle.svelte` que `/`) avec colorisation par résultat :
  - Vert : pour / Rouge : contre / Gris : abstention / Noir : absent
  - Tooltip au survol : identique à la page d'accueil
  - Animation d'entrée Rive : identique à `/`

### Composants Svelte réutilisés

| Composant                  | Utilisé sur           | Props principales                   |
|----------------------------|-----------------------|-------------------------------------|
| `Hemicycle.svelte`         | `/` et `/votes/:id`   | `mode: 'groupe' \| 'vote'`, `data`  |
| `HemicycleTooltip.svelte`  | via Hemicycle         | `depute`, `position`                |
| `ActivityCalendar.svelte`  | `/depute/:id`         | `activites`, `dateDebut`, `dateFin` |

### Animations Rive
- Apparition progressive de l'hémicycle au chargement de `/` et `/votes/:id`
- Animation ouverture/fermeture des tooltips de survol
- Pas de transitions de page

### Ce que le site ne fait PAS (hors scope)
- Pas de compte utilisateur ni d'authentification
- Pas de commentaires ni d'interaction sociale
- Pas de temps réel (données ingérées par batch CRON)
- Pas de données antérieures à la 11e législature (limite de l'open data AN)

---

## Commandes essentielles

### Back-end
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --reload           # Dev local (port 8000)
pytest                                   # Tests
alembic upgrade head                     # Appliquer migrations DB
alembic revision --autogenerate -m ""   # Créer une migration
```

### Front-end
```bash
cd frontend
npm install
npm run dev        # Dev local (port 5173)
npm run build      # Build production
npm run check      # Vérification TypeScript + Svelte
```

### Infra
```bash
cd infra
terraform init
terraform plan     # Toujours valider avant apply
terraform apply
```

---

## Conventions de code

### Python (back-end)
- Python 3.12+, type hints obligatoires sur toutes les fonctions
- Formatter : `black` + `isort`
- Linter : `ruff`
- Async partout : `async def` pour tous les endpoints FastAPI
- ORM : SQLAlchemy 2.0 (`select()`, `AsyncSession`, `async with session.begin()`)
- Variables d'environnement via `pydantic-settings` — jamais de secrets en dur

### Svelte (front-end)
- Svelte 5 avec runes : `$state`, `$derived`, `$effect`
- Ne pas mélanger avec la syntaxe Svelte 4 (`writable`, `onMount`)
- TypeScript strict activé
- CSS : vanilla CSS avec custom properties — pas de framework CSS
- Composants maison uniquement — pas de bibliothèque UI tierce
- Design sobre : palette neutre, typographie lisible, animations légères via Rive

### Terraform
- Un module par type de ressource Scaleway
- Tous les secrets via variables Terraform (`.tfvars` non commité)
- `terraform fmt` avant chaque commit

### Git
- Branches : `feature/`, `fix/`, `infra/`
- Commits en français, format conventionnel : `feat:`, `fix:`, `chore:`, `infra:`
- PR obligatoire pour merger sur `main`
- GitHub Actions valide lint + tests avant merge

---

## Sources de données — détail

### Mapping endpoints AN par page

| Page            | Endpoints AN utilisés                         |
|-----------------|-----------------------------------------------|
| `/`             | Acteurs (députés en cours), Organes (groupes) |
| `/deputes`      | Acteurs, Organes                              |
| `/depute/:id`   | Acteur, Scrutins, Amendements, Comptes rendus |
| `/votes`        | Scrutins (liste)                              |
| `/votes/:id`    | Scrutin (détail), Acteurs (colorisation)      |

### Pattern d'ingestion (Serverless Functions)

```
CRON trigger Scaleway
  → Serverless Function Python
    → Requête API open data AN ou data.gouv.fr
    → Validation / normalisation (Pydantic)
    → Upsert PostgreSQL (jamais d'insert brut)
```

Fréquences CRON indicatives :
- Scrutins / votes : quotidien (les jours de séance)
- Amendements : quotidien
- Données député (groupe, circonscription) : hebdomadaire
- Données statiques (positions sièges hémicycle) : à la demande uniquement

### Regards Citoyens — attribution obligatoire
Toute page affichant des données issues de NosDéputés.fr doit afficher dans le footer :
"NosDéputés.fr par Regards Citoyens à partir de l'Assemblée nationale"

---

## Variables d'environnement requises

```env
# Back-end
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
API_HOST=0.0.0.0
API_PORT=8000

# Ingestion
ASSEMBLEE_API_BASE_URL=https://data.assemblee-nationale.fr/api
GOUV_API_BASE_URL=https://www.data.gouv.fr/api/1
NOSDEPUTES_API_BASE_URL=https://www.nosdeputes.fr

# Scaleway (via tfvars ou env CI/CD)
SCW_ACCESS_KEY=
SCW_SECRET_KEY=
SCW_DEFAULT_PROJECT_ID=
SCW_DEFAULT_REGION=fr-par
```

---

## Gotchas — Points d'attention

- **APIs open data lentes ou indisponibles** : implémenter un retry avec backoff exponentiel dans toutes les fonctions d'ingestion. Ne jamais échouer silencieusement.
- **Scaleway Serverless Functions** : le handler Python est `handle(event, context)` — différent du format AWS Lambda. Ne pas copier des exemples AWS.
- **Svelte 5 runes** : syntaxe `$state`, `$derived`, `$effect` incompatible avec Svelte 4. Ne pas mélanger les deux styles dans un même composant.
- **SQLAlchemy 2.0 async** : utiliser `AsyncSession` et `async with session.begin()`. Le pattern synchrone `session.commit()` ne fonctionne pas en mode async.
- **Terraform Scaleway** : le provider s'appelle `scaleway/scaleway` sur le registry. Ne pas utiliser d'anciens providers communautaires.
- **Positions des sièges hémicycle** : `hemicycle-seats.json` doit être extrait du SVG Regards Citoyens avant de démarrer `Hemicycle.svelte`. C'est un prérequis bloquant pour la page d'accueil et `/votes/:id`.
- **Terraform HCL** : ne jamais utiliser de `;` comme séparateur dans 
  les blocs — toujours des retours à la ligne. Un bloc variable correct :
  variable "nom" {
    type      = string
    sensitive = true
  }
---
- **Terraform provider Scaleway** : le source est `scaleway/scaleway`, jamais `hashicorp/scaleway`. À déclarer dans chaque module qui utilise le provider.
- **Terraform variables** : les noms dans terraform.tfvars doivent correspondre exactement (casse incluse) aux déclarations dans variables.tf. Utiliser snake_case minuscules partout.
- **-backend-config** : uniquement avec `terraform init`, jamais avec `plan` ou `apply`.
- **Nom de la base de données** : `les577` partout dans .env, docker, et Scaleway Managed PostgreSQL.
- **API Assemblée Nationale** : pas d'API REST paginée — les données sont des archives ZIP à télécharger et décompresser.
  Format des URLs : https://data.assemblee-nationale.fr/static/openData/repository/17/[type]/[jeu]/json/
  Ne jamais inventer un endpoint /api/v2/...
- **asyncpg + paramètre NULL** : asyncpg ne peut pas inférer le type d'un paramètre utilisé dans `CASE WHEN $n IS NULL` ou dans un `EXISTS` subquery avec le même `$n` qu'une colonne `VARCHAR` → `AmbiguousParameterError`. Solution : filtrer les valeurs nullables en Python avant l'insert et garder le SQL simple (pas de logique conditionnelle sur les paramètres). Ne jamais écrire `CASE WHEN :x IS NULL THEN NULL WHEN EXISTS(...id = :x)` avec SQLAlchemy text().
- **Svelte 5 CSS** : pas de css() helper ni de CSS-in-JS. Tout le CSS dans des blocs <style> standard. Styles dynamiques via attribut style= ou classes conditionnelles.

## Workflow recommandé avec Claude Code

1. **Avant toute feature complexe** : Plan Mode (`Shift+Tab`) pour valider l'approche avant toute modification de fichier
2. **Changer de sujet** : `/clear` entre des tâches non liées
3. **Infra** : toujours `terraform plan` avant `terraform apply`
4. **Migrations DB** : relire le fichier Alembic généré avant d'appliquer
5. **Enrichir ce fichier** : ajouter une ligne dans les Gotchas à chaque erreur liée à la stack
