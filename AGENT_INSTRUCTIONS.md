# CryoDash - Agent Code Instructions

Fichier de directives pour les agents de code travaillant sur le projet CryoDash.

## Vision du projet

CryoDash est un dashboard web pour le suivi en temps réel des niveaux de cryogènes (azote liquide et hélium liquide) dans des appareils RMN (Neo600 et Neo700). Le système comprend :

- **Backend** : API REST FastAPI avec SQLite
- **Frontend** : Interface web moderne avec JavaScript vanilla et Chart.js
- **Importer** : Script pour charger les données depuis les fichiers logs

## Architecture

```
cryodash/
├── cryodash/
│   ├── main.py              # Entrée FastAPI, création app, lifespan + scheduler
│   ├── config.py            # Configuration (chemins, seuils, etc.)
│   ├── database.py          # Setup SQLAlchemy et SQLite
│   ├── models.py            # Modèles SQLAlchemy + Schemas Pydantic
│   ├── api/
│   │   └── routes.py        # Endpoints API (/api/*)
│   ├── scripts/
│   │   ├── import_logs.py   # Parser logs et import DB
│   │   └── sync_remote_logs.py  # Télécharge logs du serveur HTTP
│   └── static/
│       ├── index.html       # UI (Dashboard | Graphiques | Admin)
│       ├── style.css        # Styles CSS (dark theme)
│       └── script.js        # Frontend JavaScript/Fetch
├── pyproject.toml           # Dépendances et metadata
├── README.md
├── LICENSE
└── .gitignore
```

## Patterns et conventions

### Base de données

**Modèles SQLAlchemy** (`models.py`):

- `CryogenReading` : Lecture de niveau (device, cryogen, level, timestamp)
- `Instrument` : Métadonnées appareil (neo600, neo700, frequencies, cryogens)
- `SyncHistory` : Historique des synchronisations (timestamps, status, counts)

**Schemas Pydantic** :

- Pour API responses et validations
- Nommage : `{Model}Schema` ou `{Model}CreateSchema`
- Nouveaux : `SyncHistorySchema`, `EvaporationRateSchema`

**Indices** :

- `device`, `cryogen`, `timestamp` pour requêtes fréquentes
- Utiliser `order_by(desc())` pour les lectures les plus récentes

### API REST

**Patterns d'endpoints** :

```
GET     /api/instruments                    # Liste appareils
GET     /api/instruments/{name}             # Détail appareil + lectures actuelles
GET     /api/instruments/{name}/current     # Lectures actuelles
GET     /api/instruments/{name}/history     # Historique avec filtres
POST    /api/readings                       # Créer une lecture
POST    /api/instruments                    # Créer un appareil
GET     /api/health                         # Health check
POST    /api/sync-logs                      # Déclencher sync manuelle
GET     /api/sync-status                    # Statut scheduler
GET     /api/sync-history?limit=50          # Historique des syncs
GET     /api/stats                          # Stats globales BD
GET     /api/evaporation-rate?hours=24      # Taux évaporation par cryogen
```

**Query parameters** :

- `cryogen` : Type de cryogène (N2, He)
- `hours` : Nombre d'heures d'historique (défaut: 24)
- `limit` : Max enregistrements (défaut: 1000)

**Statuts d'alerte** :

- `ok` : Au-dessus du seuil warning
- `warning` : Entre critical et warning
- `critical` : Sous le seuil critical

### Import des logs

**Format attendu** :

```
# timestamp ; cryogen level [%]
2017-11-22T17:26:00.000-0500;86.6
```

**Deux modes** :

1. **Import local** : `import_logs.py` - Parse fichiers logs locaux
2. **Sync remote** : `sync_remote_logs.py` - Télécharge depuis HTTP et importe

**Utilisation** :

```bash
# Import local
python -m cryodash.scripts.import_logs \
  --device neo600 \
  --file neo600_N2logcache.log \
  --cryogen N2 \
  --init-db

# Sync remote (manuel)
python -m cryodash.scripts.sync_remote_logs
```

**Logique** :

- Parser ISO 8601 timestamps (inclure timezones)
- Télécharger depuis `http://airen.bcm.umontreal.ca/biostruct/logs/`
- Vérifier les doublons avant insertion
- Clamps values à 0-100% (rejets évités)
- Créer automatiquement les appareils s'ils n'existent pas
- Enregistrer sync event en `SyncHistory`

### Frontend

**Pages/Onglets** :

1. **Dashboard** (📊) : Cards temps réel avec taux évaporation
2. **Graphiques** (📈) : Charts historiques, single/dual mode
3. **Admin** (⚙️) : Sync controls, stats, historique, taux évaporation avec détection refill

**Architecture JavaScript** :

- Event-driven avec listeners sur page load
- Fetch API pour appels HTTP (pas de jQuery)
- Rafraîchissement auto toutes les 60 secondes (dashboard seulement)
- Chart.js pour visualisations historiques
- Page navigation avec `switchPage()`

**Détection des refills** :

- Les "refills" (remplissages) sont détectés automatiquement
- Un refill = augmentation du niveau > 10% entre deux lectures consécutives
- Le taux d'évaporation est calculé **DEPUIS le dernier refill détecté**
- Cela évite de distordre les calculs avec les périodes de remplissage
- Frontend affiche le timestamp du dernier refill dans la section Admin

**Fonctions principales** :

- `loadInstruments()` : Charge la liste et appelle API détail
- `displayInstruments()` : Rend les cards + évaporation rates
- `loadCharts()` : Détermine single vs dual mode
- `loadEvaporationRates()` : Récupère taux %/jour pour admin
- `setupAdminControls()` : Event listeners admin page
- `triggerManualSync()` : POST /api/sync-logs

**Admin features** :

- Bouton sync manuel avec résultats
- Monitoring scheduler (status, intervalle)
- Stats BD (total lectures, appareils, timestamps)
- Historique des 50 derniers syncs
- Taux évaporation avec sélecteur heures (24/72/168h)

### CSS et Thème

**Palette** :

- Dark theme avec variables CSS (--primary-color, --secondary-color, etc.)
- Gradients pour accents (primary + secondary)
- Colores d'état : success (vert), warning (orange), critical (rouge)
- Classes admin : `.admin-card`, `.status-badge`, `.stat-grid`, `.evap-table`

**Responsive** :

- Grid CSS auto-fit pour instrument cards
- Dual charts avec grid 2 colonnes sur desktop
- Mobile-first avec media queries
- Min-width 200px pour stat items, 350px pour cards

### Configuration

**Variables d'environnement** (`config.py`) :

```python
DATABASE_URL         # SQLite par défaut
HOST, PORT          # Serveur (127.0.0.1:8000)
DEBUG               # Mode développement
ALERT_THRESHOLDS    # Dict seuils par device/cryogen
```

**Seuils d'alerte** (modifiables dans config.py) :

- Neo600 N2 : warning 25%, critical 10%
- Neo700 N2 : warning 25%, critical 10%
- Neo700 He : warning 20%, critical 5%

## Conventions de code

### Python

- Type hints partout (except `disallow_untyped_defs: false`)
- Docstrings : Format Google
- Imports : Groupes (stdlib, third-party, local)
- Ligne max : 100 caractères
- Formatage : black, ruff checks
- Nommage :
  - Fonctions/variables : `snake_case`
  - Classes : `PascalCase`
  - Constantes : `UPPER_CASE`
  - Privées : `_leading_underscore`

### JavaScript

- const/let (pas var)
- Fonctions : camelCase
- Classes : PascalCase (si nécessaire)
- Commentaires : JSDoc pour publiques
- Template literals pour interpolation
- Fetch async/await (pas promises)

### Base de données

- `device` toujours lowercase dans requêtes
- `cryogen` toujours uppercase (N2, He)
- Timestamps toujours en UTC
- Vérifier existence avant insertion

## Tâches courantes

### Ajouter un nouvel endpoint

1. Ajouter fonction dans `cryodash/api/routes.py`
2. Utiliser Depends(get_db) pour session
3. Retourner Pydantic schema (ajouter à models.py si nouveau)
4. Ajouter au router avec décorateur (@router.get, @router.post)
5. Enregistrer SyncHistory si c'est un import
6. Mettre à jour AGENT_INSTRUCTIONS.md

### Modifier le schéma DB

1. Éditer classes dans `cryodash/models.py`
2. Ajouter schemas Pydantic correspondants
3. Créer nouvelle table via init_db() si nécessaire
4. Migrer données existantes si structure change

### Ajouter section Admin

1. Créer div `.page-content` dans `index.html`
2. Ajouter onglet `.nav-tab` avec `data-page="admin"`
3. Implémenter fonctions JS pour charger data
4. Ajouter styles CSS `.admin-*` à `style.css`
5. Créer endpoints API correspondants

### Modifier le frontend

1. Éditer fichiers dans `cryodash/static/`
2. Pas de build step (vanilla JS)
3. CSS dark theme à respecter
4. Tester responsive avec DevTools
5. Rafraîchir page (F5) après modifs CSS

### Importer nouvelles données

1. Placer fichier log en workspace ou URL accessible
2. Exécuter `import_logs` avec bons arguments
3. Ou appeler POST /api/sync-logs pour sync remote
4. Vérifier pas de doublons en BD
5. Rafraîchir UI (F5 ou auto 60s)

## Erreurs courantes à éviter

- **Timestamps** : Ne pas oublier timezones, parser correctement ISO 8601
- **Doublons DB** : Vérifier avant INSERT, gérer timezone/microseconds
- **Cryogen case** : Stocker uppercase (N2, HE), normaliser en API avec `.upper()`
- **API responses** : Toujours valider avec Pydantic schema
- **Status 404** : Vérifier noms devices lowercase
- **CSS** : Respecter dark theme, vars CSS, pas de hardcoded colors
- **Fetch** : Toujours try/catch et vérifier `response.ok`
- **Chart** : Destroy instance avant créer nouvelle
- **Sync records** : Enregistrer même si partiellement échoué en SyncHistory
- **Evaporation calculation** : Clamps negative/positive values, hours_calculated peut être float
- **Admin page** : Charger data au switch seulement, pas au démarrage

## Testing

```bash
# Vérifier syntax Python
python -m py_compile cryodash/*.py cryodash/*/*.py

# Lancer serveur dev
python -m cryodash.main

# Tester endpoint
curl http://localhost:8000/api/health
curl http://localhost:8000/api/stats
curl -X POST http://localhost:8000/api/sync-logs

# Importer données test
python -m cryodash.scripts.import_logs \
  --device neo600 \
  --file neo600_N2logcache.log \
  --init-db

# Sync remote (télécharge depuis serveur)
python -m cryodash.scripts.sync_remote_logs
```

## Déploiement

- **Dev** : `python -m cryodash.main` (reload auto)
- **Prod** : `uvicorn cryodash.main:app --host 0.0.0.0 --port 80`
- Base de données : Fichier SQLite, backup régulier
- Reverse proxy : nginx recommandé pour prod
- Scheduler : APScheduler dans lifespan, sync logs toutes les heures
- Logs : Diriger stdout/stderr vers fichiers pour prod

## Ressources

- FastAPI docs : <https://fastapi.tiangolo.com/>
- SQLAlchemy : <https://docs.sqlalchemy.org/>
- Chart.js : <https://www.chartjs.org/>
- Pydantic : <https://docs.pydantic.dev/>

## Points d'extension futurs

- [x] Sync automatique des logs (APScheduler chaque heure)
- [x] Dashboard admin avec statut scheduler
- [x] Export historique syncs
- [x] Taux d'évaporation (%/jour)
- [ ] WebSockets pour live updates (pas polling)
- [ ] Notifications email/SMS alertes
- [ ] Multi-user avec auth
- [ ] Prédictions ML sur consommation
- [ ] Support PostgreSQL/MySQL
- [ ] Graphiques side-by-side comparison
- [ ] Alembic migrations pour schema changes

## Structure Pydantic et validation

**Important** :

- Tous les schemas utilisent `ConfigDict(from_attributes=True)`
- Les types float acceptent entiers ET décimales
- Types int : rejettent float (sauf conversion explicite)
- Les datetime doivent être ISO 8601
- Optional[] pour champs nullables

**Exemple correct** :

```python
class MySchema(BaseModel):
    hours: float  # Accepte 22.4
    count: int    # Rejette 5.0, accepte 5

    model_config = ConfigDict(from_attributes=True)
```
