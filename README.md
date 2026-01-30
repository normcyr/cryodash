# CryoDash - Cryogenic Level Monitoring Dashboard

[![CI](https://github.com/normcyr/cryodash/actions/workflows/ci.yml/badge.svg)](https://github.com/normcyr/cryodash/actions/workflows/ci.yml)
[![Build](https://github.com/normcyr/cryodash/actions/workflows/build.yml/badge.svg)](https://github.com/normcyr/cryodash/actions/workflows/build.yml)
[![codecov](https://codecov.io/gh/normcyr/cryodash/branch/main/graph/badge.svg)](https://codecov.io/gh/normcyr/cryodash)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checking: mypy](https://img.shields.io/badge/type%20checking-mypy-blue.svg)](http://mypy-lang.org/)

Dashboard pour le suivi en temps réel des niveaux de cryogènes (azote liquide et hélium liquide) dans vos appareils RMN.

## Caractéristiques

- 📊 Dashboard web en temps réel avec taux d'évaporation
- 📈 Historique avec graphiques single/dual
- 🔄 Synchronisation **automatique toutes les heures** depuis serveur HTTP
- ⚙️ **Section Admin** : contrôle sync, statistiques BD, historique
- 📱 API REST complète pour accès aux données
- � **Sécurité avancée** : Authentification API, rate limiting, headers HTTPS, analyse sécurité
- 💾 Base de données SQLite intégrée
- 🎨 Interface modern dark theme responsive
- 🛠️ **Outils modernes** : uv pour gestion paquets, prek pour hooks pre-commit, bandit pour sécurité

## Appareils supportés

- **Neo600** : Imageur 600 MHz (Azote Liquide uniquement)
- **Neo700** : Imageur 700 MHz (Azote Liquide + Hélium Liquide)

## Installation

### Option 1: Docker (recommandé)

Prérequis: [Docker & Docker Compose](https://www.docker.com/products/docker-desktop)

```bash
git clone https://github.com/normcyr/cryodash.git
cd cryodash
cp .env.example .env
docker-compose up
```

Accessible sur: `http://localhost:8000`

### Option 2: Local (Python)

#### Prérequis

- Python 3.9 ou plus récent
- uv (recommandé) ou pip

#### Étapes d'installation

1. Cloner le repository :

```bash
git clone https://github.com/normcyr/cryodash.git
cd cryodash
```

1. Installer uv (optionnel mais recommandé) :

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

1. Installer les dépendances :

```bash
# Avec uv (recommandé)
uv pip install -e .
uv pip install -e .[dev]

# Ou avec pip
pip install -e .
pip install -e ".[dev]"
```

1. Installer les hooks pre-commit pour la sécurité :

```bash
# Installer prek
pip install prek  # ou uv pip install prek

# Configurer hooks
prek install
prek install-hooks
```

## Utilisation

### Démarrer le serveur

```bash
python -m cryodash.main
```

Le dashboard sera accessible à `http://localhost:8000`

Fonctionnalités incluses :

- **Dashboard** : Suivi temps réel des niveaux + taux d'évaporation
- **Graphiques** : Historique avec charts (24h/3j/7j/30j)
- **Admin** : Sync manuel, statistiques, historique des syncs

### Synchronisation automatique

La synchronisation des logs distants s'exécute **automatiquement toutes les heures**.

Pour déclencher une synchronisation manuelle :

```bash
# Appel API
curl -X POST http://localhost:8000/api/sync-logs

# Ou via le bouton Admin du dashboard
```

## Sécurité & Authentification

CryoDash protège les endpoints de mutation (POST) avec une **authentification par clé API** via en-tête HTTP.

### Configuration

Les variables d'environnement contrôlent l'authentification :

```bash
# Activer/désactiver l'authentification (défaut: true en production)
REQUIRE_API_KEY=true

# Clé API secrète (en production: variable d'environnement sécurisée)
API_KEY=your-secure-api-key-here
```

**Développement local :** Dans un environnement de dev, vous pouvez désactiver l'authentification :

```bash
REQUIRE_API_KEY=false
```

### Endpoints protégés

Les endpoints suivants **nécessitent une authentification** :

- `POST /api/readings` - Créer une lecture
- `POST /api/instruments` - Créer un appareil
- `POST /api/sync-logs` - Déclencher une synchronisation manuelle

### Utilisation de l'API avec authentification

Fournissez votre clé API dans l'en-tête `X-API-Key` :

```bash
# Créer une lecture avec authentification
curl -X POST http://localhost:8000/api/readings \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secure-api-key-here" \
  -d '{
    "instrument_name": "neo600",
    "level": 75.5,
    "cryogen": "N2",
    "timestamp": "2024-12-19T14:30:00Z"
  }'

# Créer un appareil
curl -X POST http://localhost:8000/api/instruments \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secure-api-key-here" \
  -d '{
    "name": "neo600",
    "description": "Imageur 600 MHz"
  }'

# Déclencher une synchronisation manuelle
curl -X POST http://localhost:8000/api/sync-logs \
  -H "X-API-Key: your-secure-api-key-here"
```

### Validation des données

L'API valide les valeurs soumises :

- **Level (niveau)** : Doit être entre 0 et 100% inclus
  - ❌ `level: -5` → Erreur 422
  - ❌ `level: 105` → Erreur 422
  - ✅ `level: 75.5` → Accepté

### Production (Render)

Sur Render, la clé API est stockée dans un **groupe d'environnement sécurisé** :

1. Créer le groupe `cryodash-env` dans Render Dashboard
2. Ajouter `API_KEY` avec votre clé secrète
3. La variable `REQUIRE_API_KEY=true` activera automatiquement la validation

**Note :** Ne jamais commiter la clé API dans le repository. Toujours utiliser les variables d'environnement de production.

### Importer les données des logs (mode local)

```bash
python -m cryodash.scripts.import_logs --device neo600 --file neo600_N2logcache.log
python -m cryodash.scripts.import_logs --device neo700 --file neo700_N2logcache.log
python -m cryodash.scripts.import_logs --device neo700 --file neo700_Helogcache.log --cryogen He
```

## Structure du Projet

```
cryodash/
├── cryodash/
│   ├── __init__.py
│   ├── main.py              # Application principale (FastAPI + APScheduler)
│   ├── config.py            # Configuration seuils/paths
│   ├── models.py            # Modèles DB + Schemas Pydantic
│   ├── database.py          # Setup SQLAlchemy/SQLite
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py        # Tous les endpoints API
│   ├── scripts/
│   │   ├── __init__.py
│   │   ├── import_logs.py   # Parser logs locaux
│   │   └── sync_remote_logs.py   # Télécharge depuis HTTP
│   └── static/
│       ├── index.html       # UI (3 pages : Dashboard/Graphiques/Admin)
│       ├── style.css        # Dark theme avec variables CSS
│       └── script.js        # Frontend vanilla JS + Fetch
├── pyproject.toml
├── AGENT_INSTRUCTIONS.md    # Directives pour agents
├── README.md
├── LICENSE
└── .gitignore
```

## API Endpoints

### Instruments & Lectures

- `GET /api/instruments` - Liste tous les appareils
- `GET /api/instruments/{name}` - Détail appareil + lectures actuelles
- `GET /api/instruments/{name}/current` - Niveau actuel
- `GET /api/instruments/{name}/history?cryogen=N2&hours=24` - Historique
- `POST /api/readings` - Créer une lecture
- `POST /api/instruments` - Créer un appareil

### Synchronisation & Admin

- `GET /api/health` - Health check
- `POST /api/sync-logs` - **Déclencher sync manuelle**
- `GET /api/sync-status` - Statut du scheduler
- `GET /api/sync-history?limit=50` - **Historique des syncs**
- `GET /api/stats` - **Statistiques BD**
- `GET /api/evaporation-rate?hours=24` - **Taux d'évaporation (%/jour)**

### Paramètres de query courants

- `hours`: Nombre d'heures (défaut: 24)
- `cryogen`: Type (N2, He)
- `limit`: Max enregistrements (défaut: 50-1000 selon endpoint)

### Exemples

```bash
# Appareils disponibles
curl http://localhost:8000/api/instruments

# Niveau actuel du Neo600
curl http://localhost:8000/api/instruments/neo600/current

# Historique des 7 derniers jours
curl http://localhost:8000/api/instruments/neo700/history?hours=168

# Statistiques BD
curl http://localhost:8000/api/stats

# Taux d'évaporation (24h)
curl http://localhost:8000/api/evaporation-rate?hours=24

# Déclencher sync manuelle
curl -X POST http://localhost:8000/api/sync-logs

# Historique des syncs
curl http://localhost:8000/api/sync-history?limit=20
```

## Configuration

Modifier le fichier `cryodash/config.py` pour :

- Changer le port du serveur
- Ajuster le chemin de la base de données
- Configurer les seuils d'alerte

## Développement

### Tests

CryoDash inclut une suite de tests complète avec couverture de code:

```bash
# Exécuter les tests principaux
pytest tests/test_api_integration.py tests/test_unit.py -v

# Avec rapport de couverture
pytest tests/test_api_integration.py tests/test_unit.py --cov=cryodash --cov-report=term-missing

# Tous les tests (incluant les anciens fichiers)
pytest --cov=cryodash
```

**Couverture actuelle :** 55% (25 tests passants)

- ✅ API Integration tests : 13/13 passants (100%)
- ✅ Unit tests : 12/12 passants (100%)
- Couverture par module :
  - `models.py`: 100% ✅
  - `api/routes.py`: 91%
  - `config.py`: 100% ✅
  - `database.py`: 62%
  - `main.py`: 57%
  - `scripts/`: 12-17% (À améliorer)

### Docker

CryoDash peut être exécuté dans un conteneur:

```bash
# Build l'image
docker build -t cryodash:latest .

# Ou utiliser Docker Compose (recommandé)
docker-compose up -d

# Accéder à l'application
# http://localhost:8000
```

**docker-compose.yml :**

- Service `cryodash-app` sur le port 8000
- Volumes persistants pour `cryodash_data/` et `cryodash.db`
- Variables d'environnement configurables (HOST, PORT, DATABASE_URL, DEBUG)

### Formatage et vérifications du code

```bash
# Format et lint avec ruff
ruff format cryodash/
ruff check cryodash/ --fix

# Type checking
mypy cryodash/

# Ou utiliser le script fourni
./scripts/lint-and-check.sh
```

### CI/CD avec GitHub Actions

CryoDash inclut des workflows GitHub Actions pour :

- ✅ Lint avec Ruff (vérification de style)
- ✅ Type checking avec mypy (vérification de types)
- ✅ Tests avec pytest (y compris coverage)
- ✅ Build de distribution (wheel + sdist)

**Workflows :**

- `ci.yml` : S'exécute sur push/PR vers main/develop
- `build.yml` : S'exécute sur push vers main et tags v*

Pour plus de détails, voir [docs/CI_CD.md](docs/CI_CD.md)

## Licence

MIT - Voir le fichier [LICENSE](LICENSE)

## Auteur

Norm

## Support

Pour les problèmes, ouvrir une issue sur GitHub.
