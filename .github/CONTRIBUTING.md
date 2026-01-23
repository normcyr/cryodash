# Guide de Contribution - CryoDash

Merci de contribuer à CryoDash! Ce guide vous aidera à mettre en place votre environnement de développement et à comprendre nos processus de qualité.

## 🚀 Configuration initiale

### 1. Cloner et installer

```bash
git clone https://github.com/yourusername/cryodash.git
cd cryodash
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

### 2. Installer les hooks pre-commit

```bash
pre-commit install
```

Cela active les vérifications automatiques avant chaque commit.

## 📋 Avant de committer

### Vérifications locales

```bash
# Option 1 : Utiliser le script fourni
./scripts/lint-and-check.sh

# Option 2 : Commandes individuelles
ruff check cryodash
ruff format cryodash --check
mypy cryodash --config-file mypy.ini
pytest tests/ --cov=cryodash
```

### Avec pre-commit (automatique)

Pre-commit s'exécute automatiquement avant `git commit`. Si une vérification échoue:

1. **Corrections automatiques** : Les outils auto-fixent ce qu'ils peuvent
2. **Stage les changements** : `git add .`
3. **Recommmit** : `git commit -m "message"`

Ou forcez le commit:

```bash
git commit --no-verify  # À éviter!
```

## 🧪 Tests

Avant de pousser, assurez-vous que les tests passent:

```bash
pytest tests/ -v
pytest tests/ --cov=cryodash --cov-report=html
```

Ouvrez `htmlcov/index.html` pour voir la couverture détaillée.

## 📝 Conventions de code

### Python

- **Type hints** : Toutes les fonctions doivent avoir des annotations de type
- **Docstrings** : Format Google pour chaque fonction/classe
- **Imports** : Groupés et triés (stdlib, third-party, local)
- **Ligne max** : 100 caractères
- **Nommage** : `snake_case` pour fonctions/variables, `PascalCase` pour classes

### Exemple

```python
"""Module documentation."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String
from pydantic import BaseModel


class MyModel(BaseModel):
    """Documentation de la classe."""

    id: int
    name: str
    created_at: datetime

    def process(self, value: str) -> Optional[str]:
        """Traiter une valeur.

        Args:
            value: La valeur à traiter.

        Returns:
            La valeur traitée ou None.
        """
        if value:
            return value.upper()
        return None
```

## 🔄 Processus CI/CD

Nos workflows GitHub Actions exécutent automatiquement:

1. **Lint** : ruff check
2. **Format** : ruff format
3. **Type checking** : mypy
4. **Tests** : pytest avec coverage

Les PR doivent passer **tous les checks** avant fusion.

## 📊 Outils utilisés

| Outil | Rôle | Config |
|-------|------|--------|
| **ruff** | Lint + format | `pyproject.toml` |
| **mypy** | Type checking | `mypy.ini` |
| **pytest** | Tests + coverage | `pyproject.toml` |
| **pre-commit** | Hooks git | `.pre-commit-config.yaml` |
| **GitHub Actions** | CI/CD | `.github/workflows/` |

## 🐛 Debugger

### Logs du serveur

```bash
python -m cryodash.main
# Ou avec logs plus verbeux
DEBUG=1 python -m cryodash.main
```

### Vérifier les types en temps réel

```bash
mypy cryodash --watch  # Si disponible
```

### Tests en mode watch

```bash
pytest tests/ --looponfail
```

## 📚 Documentation

Pour tous les changements majeurs:

- Mettre à jour [README.md](../README.md)
- Mettre à jour [AGENT_INSTRUCTIONS.md](../AGENT_INSTRUCTIONS.md)
- Ajouter des docstrings aux nouvelles fonctions
- Commenter le code complexe

## 🎯 Checklist avant PR

- [ ] Tests passent : `pytest tests/`
- [ ] Coverage acceptable : `pytest --cov=cryodash`
- [ ] Lint passe : `ruff check cryodash`
- [ ] Format valide : `ruff format --check cryodash`
- [ ] Type checking passe : `mypy cryodash`
- [ ] Pre-commit passe : `pre-commit run --all-files`
- [ ] Docstrings ajoutées/mises à jour
- [ ] README/AGENT_INSTRUCTIONS mises à jour

## 🆘 Besoin d'aide?

- **Docs CI/CD** : Voir [docs/CI_CD.md](../docs/CI_CD.md)
- **Architecture** : Voir [AGENT_INSTRUCTIONS.md](../AGENT_INSTRUCTIONS.md)
- **Erreurs pre-commit** : Lancer `pre-commit run --all-files -v` pour les détails

---

**Merci de contribuer! 🙏**
