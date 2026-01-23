#!/bin/bash

# Script pour exécuter les vérifications localement
# Usage: ./scripts/lint-and-check.sh

set -e

echo "🔍 Linting avec ruff..."
ruff check cryodash

echo "✨ Vérification du format avec ruff..."
ruff format cryodash --check

echo "🔬 Type checking avec mypy..."
mypy cryodash --config-file mypy.ini

echo "✅ Toutes les vérifications sont passées!"
