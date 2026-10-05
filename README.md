# EduManager v5 — Gestion scolaire

Application de bureau (CustomTkinter + SQLite) pour gérer élèves, enseignants, classes, matières,
notes, bulletins (format togolais) et emplois du temps.

## Installation et lancement
```bash
pip install -r requirements.txt
python main.py          # connexion par défaut : admin / admin123
python -m pytest        # tests (logique métier, sans interface)
```

## Architecture
Les dépendances vont toujours dans un seul sens : `ui → services → repositories → database`.

| Dossier | Rôle |
|---|---|
| `app/config.py`, `constants.py` | Chemins, couleurs, jours, périodes, listes d'horaires (`PLAN`, `SLOTS`) |
| `app/database/` | `connection` (SQLite), `schema` (DDL), `migrations` (+ `init_db`), `queries` (année active/consultée), `seed` (données initiales et exemple) |
| `app/models/` | Dataclasses (`Student`, `Teacher`, `ClassRoom`…) |
| `app/repositories/` | Tout le SQL, par entité |
| `app/calculations/` | Fonctions pures : notes, rangs, statistiques, horaires + solveur d'emploi du temps |
| `app/services/` | Cas d'usage : authentification, import élèves, bulletins, génération/export d'emploi du temps, années, paramètres, sauvegardes |
| `app/reports/` | Rendu HTML : bulletin (`templates/bulletin.html`) et emplois du temps |
| `app/ui/` | Fenêtres, composants réutilisables (`components/`) et pages (`pages/`) |
| `app/utils/` | Dates, formatage, validation, fichiers, sécurité |
| `data/` | Base `ecole.db` et `backups/` (sauvegarde automatique à chaque lancement, 10 conservées) |
| `exports/` | Bulletins, emplois du temps, fichiers Excel générés |

## Points à connaître
- **Ancienne base** : si un `ecole.db` existe à la racine (version monofichier), il est déplacé automatiquement dans `data/`.
- **PLAN / SLOTS** sont des listes partagées modifiées *en place* (`settings_service.load_plan()`). Ne jamais les réaffecter.
- **Mise en page du bulletin** : modifiez `app/reports/templates/bulletin.html` (placeholders `${...}`) ; le CSS est dans `app/reports/bulletin.py`.
- `CrudPage` (liste + formulaire générique) est dans `ui/components/data_table.py`.
