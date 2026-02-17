# Configuration des Instruments pour Push API

Guide pour configurer tes instruments NMR (neo600, neo700) à envoyer les mesures directement via POST API au lieu de télécharger des fichiers log.

## Vue d'ensemble

**Ancien système (PULL):**

- CryoDash télécharge les fichiers log toutes les heures
- Parsing local des données historiques
- Latence: jusqu'à 1 heure

**Nouveau système (PUSH):**

- Instruments envoient les mesures directement via POST
- Temps réel (ex: toutes les 5 minutes)
- Moins de charge serveur

## URL de l'API

```
POST https://cryodash-dev.up.railway.app/api/data
```

## Authentification

Chaque requête doit inclure la clé API dans le header:

```
X-API-Key: YOUR_API_KEY
```

⚠️ **IMPORTANT**: Remplacez `YOUR_API_KEY` par la clé réelle du fichier `.env` (`API_KEY=...`)

## Format des données

```json
{
  "device": "neo600",
  "location": "magnet_room",
  "timestamp": "2026-02-17T15:30:00Z",
  "readings": [
    {
      "type": "cryogen_level",
      "cryogen": "N2",
      "value": 87.5,
      "unit": "%"
    },
    {
      "type": "temperature",
      "location": "probe_head",
      "value": 22.3,
      "unit": "°C"
    }
  ]
}
```

### Champs disponibles

**Requête principale:**

- `device` (string, optionnel): Nom de l'instrument (ex: "neo600", "neo700")
- `location` (string, optionnel): Localisation générale (ex: "magnet_room")
- `timestamp` (ISO 8601, requis): Horodatage en UTC
- `readings` (array, requis): Liste des mesures

**Pour chaque reading:**

- `type` (string, requis): Type de mesure
  - `cryogen_level` - Niveau de cryogène
  - `temperature` - Température
  - `humidity` - Humidité
  - `pressure` - Pression
  - `status` - État du système
  - Ou tout type personnalisé
- `value` (float, optionnel): Valeur numérique
- `unit` (string, optionnel): Unité (%, °C, psi, etc.)
- `location` (string, optionnel): Localisation spécifique
- `cryogen` (string, optionnel): Type de cryogène (N2, He) pour cryogen_level
- `metadata` (object, optionnel): Données additionnelles (dict/JSON)

## Exemples par instrument

### neo600 (N2 uniquement)

```bash
curl -X POST https://cryodash-dev.up.railway.app/api/data \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "device": "neo600",
    "location": "magnet_room",
    "timestamp": "2026-02-17T15:30:00Z",
    "readings": [
      {
        "type": "cryogen_level",
        "cryogen": "N2",
        "value": 87.5,
        "unit": "%"
      }
    ]
  }'
```

### neo700 (N2 + He)

```bash
curl -X POST https://cryodash-dev.up.railway.app/api/data \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "device": "neo700",
    "location": "magnet_room",
    "timestamp": "2026-02-17T15:30:00Z",
    "readings": [
      {
        "type": "cryogen_level",
        "cryogen": "N2",
        "value": 85.2,
        "unit": "%"
      },
      {
        "type": "cryogen_level",
        "cryogen": "He",
        "value": 78.9,
        "unit": "%"
      }
    ]
  }'
```

### Avec plusieurs types de mesures

```bash
curl -X POST https://cryodash-dev.up.railway.app/api/data \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "device": "neo600",
    "location": "magnet_room",
    "timestamp": "2026-02-17T15:30:00Z",
    "readings": [
      {
        "type": "cryogen_level",
        "cryogen": "N2",
        "value": 87.5,
        "unit": "%"
      },
      {
        "type": "temperature",
        "location": "sample_head",
        "value": 22.3,
        "unit": "°C"
      },
      {
        "type": "humidity",
        "location": "control_room",
        "value": 45.2,
        "unit": "%"
      }
    ]
  }'
```

## Configuration des instruments

### Option 1: Cron job sur l'instrument

Si tu as accès shell sur les instruments:

```bash
# Ajouter dans crontab (toutes les 5 minutes)
*/5 * * * * /path/to/push_measurement.sh

# Fichier push_measurement.sh
#!/bin/bash

DEVICE="neo600"
API_KEY="YOUR_API_KEY"  # Remplacez par la clé du .env
ENDPOINT="https://cryodash-dev.up.railway.app/api/data"

# Lire le niveau du log file
LEVEL=$(tail -1 /path/to/neo600_N2logcache.log | cut -d';' -f2)
TIMESTAMP=$(date -u +'%Y-%m-%dT%H:%M:%SZ')

curl -X POST "$ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d "{
    \"device\": \"$DEVICE\",
    \"location\": \"magnet_room\",
    \"timestamp\": \"$TIMESTAMP\",
    \"readings\": [
      {
        \"type\": \"cryogen_level\",
        \"cryogen\": \"N2\",
        \"value\": $LEVEL,
        \"unit\": \"%\"
      }
    ]
  }"
```

### Option 2: Python script

Si vous utilisez Python sur les instruments:

```python
import requests
import json
from datetime import datetime, timezone
from pathlib import Path

API_KEY = "YOUR_API_KEY"  # Remplacez par la clé du .env
ENDPOINT = "https://cryodash-dev.up.railway.app/api/data"

def push_measurement():
    """Push the latest measurement to CryoDash"""

    # Read latest value from log file
    log_file = Path("/path/to/neo600_N2logcache.log")
    last_line = log_file.read_text().strip().split('\n')[-1]
    timestamp_str, level_str = last_line.split(';')
    level = float(level_str)

    # Prepare payload
    payload = {
        "device": "neo600",
        "location": "magnet_room",
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "readings": [
            {
                "type": "cryogen_level",
                "cryogen": "N2",
                "value": level,
                "unit": "%"
            }
        ]
    }

    # Send request
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }

    response = requests.post(ENDPOINT, json=payload, headers=headers)

    if response.status_code == 200:
        print(f"✓ Measurement sent successfully: {level}%")
    else:
        print(f"✗ Error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    push_measurement()
```

### Option 3: Scheduled task Windows

Si l'instrument tourne sur Windows avec un système d'acquisition:

```python
# script: cryodash_push.py
# Exécuté via Task Scheduler toutes les 5 minutes

import requests
import json
from datetime import datetime, timezone
import sys

API_KEY = "YOUR_API_KEY"  # Remplacez par la clé du .env
ENDPOINT = "https://cryodash-dev.up.railway.app/api/data"
LOG_FILE = r"C:\path\to\neo600_N2logcache.log"

def get_latest_level():
    """Read the latest value from log file"""
    try:
        with open(LOG_FILE, 'r') as f:
            lines = f.readlines()
        last_line = lines[-1].strip()
        if ';' in last_line:
            _, level = last_line.split(';')
            return float(level)
    except Exception as e:
        print(f"Error reading log: {e}")
        return None

def push_data():
    level = get_latest_level()
    if level is None:
        sys.exit(1)

    payload = {
        "device": "neo600",
        "location": "magnet_room",
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "readings": [
            {
                "type": "cryogen_level",
                "cryogen": "N2",
                "value": level,
                "unit": "%"
            }
        ]
    }

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }

    try:
        response = requests.post(ENDPOINT, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        print(f"✓ Sent: {level}% at {payload['timestamp']}")
    except requests.RequestException as e:
        print(f"✗ Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    push_data()
```

## Fréquence recommandée

- **Toutes les 5-10 minutes** : Bon équilibre entre temps réel et charge serveur
- **Toutes les 1-2 minutes** : Si tu veux du temps réel
- **Toutes les 30 minutes** : Si tu veux minimiser la charge

## Vérification

### Via dashboard

Va dans l'onglet **"📋 Measurements"** et filtre par ton device. Les données devraient apparaître immédiatement après l'envoi.

### Via API directement

```bash
curl "https://cryodash-dev.up.railway.app/api/measurements?device=neo600&limit=10" \
  -H "X-API-Key: YOUR_API_KEY"
```

## Migration progressive

1. **Phase 1** : Configurer push API en parallèle (gardez le sync des logs)
2. **Phase 2** : Laissez tourner les deux pendant 1-2 semaines
3. **Phase 3** : Désactiver le sync des logs une fois confiant dans le système push

## Dépannage

**"Clé API invalide"**

- Vérifier la clé complète dans `.env`
- S'assurer qu'elle ne contient pas d'espaces

**"Timeout"**

- Vérifier la connectivité réseau depuis l'instrument
- Augmenter le timeout à 15-30 secondes

**"Données ne s'affichent pas"**

- Vérifier l'onglet Measurements
- Vérifier les logs du serveur Railway

## Support

Pour des questions sur l'implémentation, voir la documentation complète:

- README.md - Vue d'ensemble
- PUSH_API.md - Spécification technique détaillée
- docs/ - Documentation supplémentaire
