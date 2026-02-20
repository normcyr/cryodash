Migration vers PostgreSQL
=========================

Ce document décrit les étapes pour migrer CryoDash de SQLite vers PostgreSQL,
et comment utiliser Alembic pour gérer les migrations.

Prérequis
---------

- Variable d'environnement `DATABASE_URL` configurée, ex :
  `postgresql+psycopg://user:password@host:5432/cryodash`
- Dépendances : `psycopg[binary]` et `alembic` (déclarées dans `pyproject.toml`)

Installation locale
-------------------

```bash
# Installer les dépendances (avec uv ou pip)
uv pip install -e .
uv pip install -e .[dev]
```

Initialiser et exécuter les migrations
-------------------------------------

1. Générer une migration initiale (si vous avez modifié des modèles):

```bash
alembic revision --autogenerate -m "init models"
```

1. Appliquer les migrations:

```bash
alembic upgrade head
```

Notes sur Alembic inclus dans le dépôt
-------------------------------------

- `alembic.ini` : configuration d'Alembic (le champ `sqlalchemy.url` peut être
  laissé vide; Alembic utilisera `DATABASE_URL` depuis `cryodash.config`).
- `alembic/env.py` : script d'environnement configuré pour utiliser
  `cryodash.database.Base.metadata`.
- `alembic/versions/` : dossier pour les versions générées par `alembic revision`.

Docker / Railway
----------------

- Docker Compose : ajoutez un service `postgres` et montez un volume pour la
  persistance des données. Exposez la base sur le réseau interne et passez
  `DATABASE_URL` au service `cryodash-app`.

- Railway : activez le plugin Postgres depuis le dashboard Railway et copiez
  la variable `DATABASE_URL` fournie dans les variables d'environnement du
  service.

Conseils
--------

- Testez les migrations localement avec une instance Postgres (via Docker)
  avant de les appliquer en production.
- Conservez SQLite pour les usages locaux rapides; utilisez Postgres pour la
  production et les environnements gérés (Railway, Render, etc.).

Exemples Docker Compose (bref)
-----------------------------

```yaml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: cryo
      POSTGRES_PASSWORD: cryo
      POSTGRES_DB: cryodash
    volumes:
      - ./data/postgres:/var/lib/postgresql/data

  cryodash-app:
    build: .
    environment:
      DATABASE_URL: postgresql+psycopg://cryo:cryo@postgres:5432/cryodash
    depends_on:
      - postgres
```

Support
-------

Pour toute question liée à la migration, ouvrir une issue sur GitHub ou me
contacter directement.
