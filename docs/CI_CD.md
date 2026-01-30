# Guide CI/CD pour CryoDash

## Vue d'ensemble

CryoDash utilise GitHub Actions pour l'intégration continue (CI) avec deux workflows principaux :

- **ci.yml** : Tests et vérifications sur tous les push/PR
- **build.yml** : Build de distribution sur les tags et main

## Configuration locale

### Installation des outils de développement

```bash
# Installer uv (recommandé)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Installer les dépendances
uv pip install -e .
uv pip install -e .[dev]

# Installer prek pour les hooks
pip install prek  # ou uv pip install prek
prek install
prek install-hooks
```

### Exécuter les vérifications localement

#### Option 1 : Script fourni

```bash
chmod +x scripts/lint-and-check.sh
./scripts/lint-and-check.sh
```

#### Option 2 : Commandes individuelles

```bash
# Lint avec ruff
ruff check cryodash

# Format check
ruff format cryodash --check

# Type checking avec mypy
mypy cryodash --config-file mypy.ini

# Tests avec pytest
pytest tests/ --cov=cryodash --cov-report=term-missing
```

## Workflows GitHub Actions

### 1. CI Workflow (ci.yml)

**Déclenché par :**

- Push sur `main` ou `develop`
- Pull requests vers `main` ou `develop`

**Étapes :**

1. Checkout du code
2. Installation de Python (3.9, 3.10, 3.11, 3.12)
3. Installation des dépendances
4. Lint avec ruff (`ruff check`)
5. Format check avec ruff (`ruff format --check`)
6. Type checking avec mypy
7. Tests avec pytest et coverage
8. Upload de coverage sur Codecov

**Matrice de test :** Les tests s'exécutent sur Python 3.9 à 3.12 pour assurer la compatibilité.

### 2. Build Workflow (build.yml)

**Déclenché par :**

- Push sur `main`
- Tags `v*`
- Dispatch manuel

**Étapes :**

1. Checkout du code
2. Installation de Python 3.11
3. Exécution de toutes les vérifications
4. Build de la distribution (wheel + sdist)
5. Upload des artifacts

## Configuration des outils

### Ruff (`.ruff.toml`)

Configuration :

- **line-length** : 100 caractères
- **Règles activées** : E, W, F, I, UP, B, A, C4, PIE, RUF
- **Règles désactivées** : E501 (longueur de ligne, gérée par black)

**Commandes :**

```bash
# Vérifier le code
ruff check cryodash

# Appliquer les corrections automatiques
ruff check cryodash --fix

# Vérifier le formatage
ruff format cryodash --check

# Appliquer le formatage
ruff format cryodash
```

### MyPy (mypy.ini)

Configuration :

- **python_version** : 3.9
- **warn_return_any** : True
- **ignore_missing_imports** : True (pour les dépendances tierces)

**Commande :**

```bash
mypy cryodash --config-file mypy.ini
```

## Bonnes pratiques

### Avant de faire un commit

```bash
# 1. Formater le code
ruff format cryodash

# 2. Vérifier le code
ruff check cryodash

# 3. Vérifier les types
mypy cryodash

# 4. Exécuter les tests
pytest tests/
```

### Ou utilisez le hook pre-commit

Installez `pre-commit` :

```bash
pip install pre-commit
pre-commit install
```

### Ajouter des tests

Les tests vont dans le dossier `tests/` :

- `test_api.py` : Tests des endpoints API
- `test_models.py` : Tests des modèles
- `conftest.py` : Fixtures pytest

**Exécuter les tests :**

```bash
# Tous les tests
pytest tests/

# Avec coverage
pytest tests/ --cov=cryodash --cov-report=html

# Test spécifique
pytest tests/test_api.py::test_get_instruments
```

## Dépannage

### Erreur : "mypy: command not found"

```bash
pip install mypy>=1.5.0
```

### Erreur : "ruff: command not found"

```bash
pip install ruff>=0.1.0
```

### Erreur : "pytest not found"

```bash
pip install -e ".[dev]"
```

### Workflow échoue sur GitHub Actions

1. Vérifier les logs du workflow (Actions tab)
2. Exécuter les commandes localement
3. Pousser après avoir corrigé les erreurs

## Intégration avec l'éditeur

### VS Code

Ajouter à `.vscode/settings.json` :

```json
{
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.fixAll": true
        }
    },
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "mypy-type-checker.enabled": true
}
```

## Ressources

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [MyPy Documentation](https://mypy.readthedocs.io/)
- [pytest Documentation](https://docs.pytest.org/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
