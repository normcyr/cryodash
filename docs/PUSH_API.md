# Push API Documentation - POST /api/data

## Overview

Le nouvel endpoint **POST /api/data** permet aux instruments d'envoyer des mesures flexibles directement à CryoDash sans dépendre de la synchronisation horaire des logs distants.

Cet endpoint supporte:

- ✅ Mesures associées à des instruments (device)
- ✅ Mesures localisées (location-based)
- ✅ Mesures indépendantes (aucune association)
- ✅ Types de mesures flexibles (cryogène, température, humidité, pression, état, etc.)
- ✅ Métadonnées additionnelles

## Authentification

Tous les requêtes doivent inclure une clé API valide via le header `X-API-Key`:

```bash
curl -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -X POST http://localhost:8000/api/data \
  -d '{...}'
```

## Format de la Requête

### Structure de base

```json
{
  "device": "neo600",
  "location": "magnet_room",
  "timestamp": "2026-02-17T10:30:00Z",
  "readings": [
    {
      "type": "cryogen_level",
      "cryogen": "N2",
      "value": 85.5,
      "unit": "%",
      "metadata": {}
    }
  ]
}
```

### Champs

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| `device` | string | ❌ | Nom de l'instrument (ex: "neo600", "neo700") |
| `location` | string | ❌ | Localisation (ex: "magnet_room", "control_room") |
| `timestamp` | ISO 8601 | ✅ | Horodatage de la mesure en UTC |
| `readings` | array | ✅ | Array de lectures (min. 1 élément) |

### Objet Reading

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| `type` | string | ✅ | Type de mesure (ex: "cryogen_level", "temperature", "humidity") |
| `cryogen` | string | ❌ | Type de cryogène (ex: "N2", "He") - pour cryogen_level |
| `location` | string | ❌ | Localisation spécifique (ex: "sample_room") |
| `value` | float | ❌ | Valeur numérique |
| `status` | string | ❌ | État (ex: "ok", "warning", "critical") |
| `unit` | string | ❌ | Unité (ex: "%", "°C", "psi") |
| `metadata` | object | ❌ | Données additionnelles en JSON |

## Exemples d'Utilisation

### 1. Mesure de niveau de cryogène

```bash
curl -X POST http://localhost:8000/api/data \
  -H "X-API-Key: dev-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "device": "neo600",
    "timestamp": "2026-02-17T10:30:00Z",
    "readings": [
      {
        "type": "cryogen_level",
        "cryogen": "N2",
        "value": 85.5,
        "unit": "%"
      }
    ]
  }'
```

### 2. Mesures multiples avec localisation

```bash
curl -X POST http://localhost:8000/api/data \
  -H "X-API-Key: dev-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "device": "neo600",
    "location": "magnet_room",
    "timestamp": "2026-02-17T10:30:00Z",
    "readings": [
      {
        "type": "cryogen_level",
        "cryogen": "N2",
        "value": 85.5,
        "unit": "%"
      },
      {
        "type": "temperature",
        "location": "sample_room",
        "value": 22.3,
        "unit": "°C"
      },
      {
        "type": "humidity",
        "value": 45.0,
        "unit": "%"
      }
    ]
  }'
```

### 3. Mesures indépendantes (aucun instrument)

```bash
curl -X POST http://localhost:8000/api/data \
  -H "X-API-Key: dev-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "location": "lab_A",
    "timestamp": "2026-02-17T10:30:00Z",
    "readings": [
      {
        "type": "pressure",
        "value": 101.325,
        "unit": "kPa",
        "metadata": {
          "sensor": "barometric_001",
          "calibration_date": "2026-01-15"
        }
      }
    ]
  }'
```

### 4. Mesure uniquement basée sur le temps (sans device ni location)

```bash
curl -X POST http://localhost:8000/api/data \
  -H "X-API-Key: dev-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2026-02-17T10:30:00Z",
    "readings": [
      {
        "type": "system_status",
        "status": "operational",
        "metadata": {
          "uptime_hours": 240,
          "last_maintenance": "2026-02-10"
        }
      }
    ]
  }'
```

## Format de la Réponse

Succès (200 OK):

```json
[
  {
    "id": 1,
    "device": "neo600",
    "location": "magnet_room",
    "measurement_type": "cryogen_level",
    "value": 85.5,
    "unit": "%",
    "timestamp": "2026-02-17T10:30:00",
    "data": {
      "cryogen": "N2"
    },
    "created_at": "2026-02-17T14:45:23"
  },
  {
    "id": 2,
    "device": "neo600",
    "location": "sample_room",
    "measurement_type": "temperature",
    "value": 22.3,
    "unit": "°C",
    "timestamp": "2026-02-17T10:30:00",
    "data": null,
    "created_at": "2026-02-17T14:45:23"
  }
]
```

Erreur (400 Bad Request):

```json
{
  "detail": "Failed to submit measurements: <error message>"
}
```

## Code Types Supportés

| Type | Description | Champs typiques |
|------|-------------|-----------------|
| `cryogen_level` | Niveau de cryogène | cryogen, value, unit |
| `temperature` | Température | value, unit, location |
| `humidity` | Humidité relative | value, unit |
| `pressure` | Pression | value, unit |
| `status` | État du système | status, metadata |
| Tous les autres | Types personnalisés | Flexible |

## Python Client Example

```python
import requests
from datetime import datetime, timezone

API_KEY = "dev-key-change-in-production"
BASE_URL = "http://localhost:8000"

def submit_measurements(device: str, readings: list):
    """Submit measurements to CryoDash."""
    url = f"{BASE_URL}/api/data"

    data = {
        "device": device,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "readings": readings
    }

    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()

    return response.json()

# Exemple d'utilisation
readings = [
    {
        "type": "cryogen_level",
        "cryogen": "N2",
        "value": 85.5,
        "unit": "%"
    },
    {
        "type": "temperature",
        "value": 22.3,
        "unit": "°C",
        "location": "sample_room"
    }
]

results = submit_measurements("neo600", readings)
for m in results:
    print(f"Created measurement {m['id']}: {m['measurement_type']} = {m['value']} {m['unit']}")
```

## Notes Importantes

1. **Timestamps**: Utiliser le format ISO 8601 avec timezone (ex: `2026-02-17T10:30:00Z`)
2. **Métadonnées**: Le champ `metadata` peut contenir n'importe quel objet JSON
3. **Types flexibles**: Vous pouvez utiliser n'importe quel type de mesure, pas seulement ceux listés
4. **Pas de duplicata**: Assurez-vous que les timestamps sont corrects pour éviter les détections de refill
5. **Location optionnelle**: Une lecture peut avoir sa propre location qui override celle du niveau parent

## Intégration avec les Instruments

Pour intégrer cet endpoint dans vos instruments:

1. **Configurer l'API key** dans les paramètres de l'instrument
2. **Envoyer les lectures** via HTTP POST chaque fois qu'une mesure est disponible
3. **Gérer les erreurs** (retry, logging)
4. **Batching** (facultatif): Grouper plusieurs lectures dans une seule requête

## Migration depuis Pull API

Si vous utilisez actuellement l'endpoint `/api/readings` (pull-based):

**Ancien (Pull):**

```bash
POST /api/readings
{
  "device": "neo600",
  "cryogen": "N2",
  "level": 85.5,
  "timestamp": "2026-02-17T10:30:00Z"
}
```

**Nouveau (Push):**

```bash
POST /api/data
{
  "device": "neo600",
  "timestamp": "2026-02-17T10:30:00Z",
  "readings": [
    {
      "type": "cryogen_level",
      "cryogen": "N2",
      "value": 85.5,
      "unit": "%"
    }
  ]
}
```

Les deux endpoints coexistent et fonctionnent ensemble! ✅
