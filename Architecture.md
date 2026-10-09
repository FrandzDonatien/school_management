# EduManager

**EduManager** est une application de bureau de gestion scolaire développée en **Python** avec **CustomTkinter** et **SQLite**. Elle permet de centraliser la gestion des élèves, enseignants, classes, matières, notes, bulletins, emplois du temps et années scolaires au sein d'une interface graphique moderne.

## Fonctionnalités

### Authentification

* Connexion utilisateur sécurisée
* Gestion des utilisateurs
* Gestion des mots de passe
* Contrôle de l'accès à l'application

### Gestion des élèves

* Ajouter, modifier et supprimer des élèves
* Consulter les informations des élèves
* Gestion de la discipline
* Association des élèves aux classes
* Recherche et filtrage

### Gestion des enseignants

* Ajouter, modifier et supprimer des enseignants
* Gestion des informations des enseignants
* Association des enseignants aux matières
* Gestion des affectations

### Gestion des classes

* Création et modification des classes
* Association des élèves aux classes
* Gestion des titulaires
* Consultation des effectifs

### Gestion des matières

* Création et modification des matières
* Gestion des coefficients
* Association des matières aux classes
* Association des matières aux enseignants

### Gestion des notes

* Saisie des notes
* Modification des notes
* Calcul automatique des moyennes
* Calcul des moyennes par matière
* Calcul des moyennes générales
* Classement des élèves
* Statistiques scolaires

### Bulletins scolaires

* Génération des bulletins
* Calcul automatique des résultats
* Génération au format HTML
* Mise en forme personnalisée
* Export des bulletins

### Emplois du temps

* Création des emplois du temps
* Gestion des jours et périodes
* Affectation des enseignants
* Affectation des matières et classes
* Vérification des heures et conflits

### Années scolaires

* Création d'une année scolaire
* Activation d'une année scolaire
* Consultation des années précédentes
* Modification des informations
* Gestion des données par année scolaire

### Paramètres

* Configuration de l'établissement
* Gestion des paramètres de l'application
* Personnalisation des informations utilisées dans les documents

### Export et sauvegarde

* Export des données
* Génération de documents
* Gestion des fichiers générés
* Sauvegarde de la base de données

---

## Technologies utilisées

| Technologie       | Utilisation                          |
| ----------------- | ------------------------------------ |
| **Python**        | Langage principal                    |
| **CustomTkinter** | Interface graphique                  |
| **Tkinter**       | Composants graphiques natifs         |
| **SQLite**        | Base de données locale               |
| **Pillow**        | Gestion des images                   |
| **HTML/CSS**      | Génération des bulletins et rapports |
| **Matplotlib**    | Graphiques et statistiques           |

---

## Architecture

Le projet suit une architecture modulaire afin de séparer l'interface utilisateur, la logique métier et l'accès aux données.

```text
EduManager/
│
├── main.py
├── requirements.txt
├── README.md
│
├── assets/
│   ├── logo.png
│   ├── icons/
│   └── images/
│
├── data/
│   ├── ecole.db
│   └── backups/
│
├── exports/
│   ├── bulletins/
│   ├── emplois_du_temps/
│   └── excel/
│
├── app/
│   ├── config.py
│   ├── constants.py
│   │
│   ├── database/
│   │   ├── connection.py
│   │   ├── schema.py
│   │   ├── migrations.py
│   │   ├── queries.py
│   │   └── seed.py
│   │
│   ├── models/
│   │   ├── student.py
│   │   ├── teacher.py
│   │   ├── subject.py
│   │   ├── class_room.py
│   │   ├── grade.py
│   │   ├── schedule.py
│   │   ├── school_year.py
│   │   └── discipline.py
│   │
│   ├── repositories/
│   │   ├── student_repository.py
│   │   ├── teacher_repository.py
│   │   ├── subject_repository.py
│   │   ├── class_repository.py
│   │   ├── grade_repository.py
│   │   ├── schedule_repository.py
│   │   ├── year_repository.py
│   │   └── user_repository.py
│   │
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── student_service.py
│   │   ├── teacher_service.py
│   │   ├── grade_service.py
│   │   ├── bulletin_service.py
│   │   ├── schedule_service.py
│   │   ├── school_year_service.py
│   │   ├── settings_service.py
│   │   ├── export_service.py
│   │   └── backup_service.py
│   │
│   ├── calculations/
│   │   ├── grades.py
│   │   ├── rankings.py
│   │   ├── statistics.py
│   │   └── schedule.py
│   │
│   ├── reports/
│   │   ├── bulletin.py
│   │   ├── schedule_report.py
│   │   └── templates/
│   │       └── bulletin.html
│   │
│   ├── ui/
│   │   ├── app.py
│   │   ├── login.py
│   │   ├── main_window.py
│   │   │
│   │   ├── components/
│   │   │   ├── card.py
│   │   │   ├── buttons.py
│   │   │   ├── inputs.py
│   │   │   ├── data_table.py
│   │   │   ├── charts.py
│   │   │   ├── dialogs.py
│   │   │   └── icons.py
│   │   │
│   │   └── pages/
│   │       ├── dashboard.py
│   │       ├── students.py
│   │       ├── teachers.py
│   │       ├── classes.py
│   │       ├── subjects.py
│   │       ├── grades.py
│   │       ├── bulletins.py
│   │       ├── schedule.py
│   │       ├── school_years.py
│   │       └── settings.py
│   │
│   └── utils/
│       ├── dates.py
│       ├── formatting.py
│       ├── validation.py
│       ├── files.py
│       └── security.py
│
└── tests/
    ├── test_students.py
    ├── test_grades.py
    ├── test_bulletins.py
    ├── test_schedule.py
    └── test_database.py
```

### Flux de l'application

```text
Interface utilisateur
        │
        ▼
      Pages
        │
        ▼
    Services
        │
        ▼
  Repositories
        │
        ▼
     SQLite
```

Les calculs métier et la génération des rapports sont isolés afin de faciliter la maintenance et les tests.

---

## Installation

### 1. Cloner le projet

```bash
git clone <URL_DU_REPOSITORY>
cd EduManager
```

### 2. Créer un environnement virtuel

Sous Windows :

```cmd
python -m venv .venv
```

Activer l'environnement :

```cmd
.venv\Scripts\activate
```

### 3. Installer les dépendances

```cmd
pip install -r requirements.txt
```

### 4. Build

```cmd
pyinstaller --noconfirm --clean --onefile --windowed --name EduManager --icon "assets\EduManager.ico" --collect-data customtkinter --collect-submodules app --paths . --add-data "assets;assets" --add-data "app/reports/templates;app/reports/templates" main.py
```


---

## Lancement

Depuis la racine du projet :

```cmd
python main.py
```

L'application initialise automatiquement la base de données SQLite au démarrage.

---

## Base de données

EduManager utilise **SQLite**, ce qui permet de faire fonctionner l'application localement sans serveur de base de données supplémentaire.

La base de données est stockée dans :

```text
data/ecole.db
```

Les sauvegardes peuvent être conservées dans :

```text
data/backups/
```

### Principales tables

```text
users
settings
years
students
teachers
discipline
subjects
classes
schedule
assignments
teacher_subjects
grades
```

La création et les évolutions du schéma sont gérées séparément dans :

```text
app/database/schema.py
app/database/migrations.py
```

---

## Configuration

Les paramètres généraux de l'application sont centralisés dans :

```text
app/config.py
```

Les constantes utilisées par l'application sont regroupées dans :

```text
app/constants.py
```

Cela permet notamment de centraliser :

* les chemins de fichiers ;
* le chemin de la base SQLite ;
* les dossiers d'export ;
* les couleurs de l'interface ;
* les polices ;
* les jours de la semaine ;
* les périodes scolaires ;
* les valeurs par défaut.

---

## Développement

### Ajouter une nouvelle fonctionnalité

Pour une nouvelle fonctionnalité, il est recommandé de respecter le flux suivant :

```text
UI
 ↓
Service
 ↓
Repository
 ↓
Database
```

Par exemple, pour la gestion des élèves :

```text
ui/pages/students.py
        ↓
services/student_service.py
        ↓
repositories/student_repository.py
        ↓
database/connection.py
        ↓
data/ecole.db
```

Les calculs spécifiques doivent être placés dans :

```text
app/calculations/
```

Les documents et rapports dans :

```text
app/reports/
```

Les composants graphiques réutilisables dans :

```text
app/ui/components/
```

---

## Tests

Les tests sont regroupés dans le dossier :

```text
tests/
```

Pour exécuter les tests :

```cmd
python -m unittest discover -s tests
```

---

## Sauvegarde

Les données de l'établissement étant stockées dans SQLite, il est recommandé d'effectuer régulièrement une sauvegarde du fichier :

```text
data/ecole.db
```

Les sauvegardes peuvent être organisées dans :

```text
data/backups/
```

---

## Export des documents

Les fichiers générés par l'application sont regroupés dans :

```text
exports/
```

Organisation :

```text
exports/
├── bulletins/
├── emplois_du_temps/
└── excel/
```

Cette organisation évite de mélanger les fichiers générés avec le code source de l'application.

---

## Sécurité

L'application dispose d'un système d'authentification et de gestion des mots de passe.

Les fonctions liées à la sécurité doivent être regroupées dans :

```text
app/utils/security.py
```

La logique d'authentification est centralisée dans :

```text
app/services/auth_service.py
```

Les informations sensibles ne doivent pas être stockées directement dans le code source.

---

## Principes de développement

Le projet suit plusieurs principes :

* séparation de l'interface et de la logique métier ;
* séparation de la logique métier et des requêtes SQL ;
* réutilisation des composants graphiques ;
* centralisation de la configuration ;
* limitation du code dupliqué ;
* validation des données avant enregistrement ;
* utilisation de services pour les traitements métier ;
* utilisation de repositories pour les accès à la base ;
* tests des fonctionnalités importantes.

L'objectif est de conserver une application simple à maintenir tout en permettant son évolution.

---

## Évolutions possibles

Les évolutions futures peuvent notamment inclure :

* gestion avancée des utilisateurs et permissions ;
* génération PDF des bulletins ;
* export Excel complet ;
* système de sauvegarde automatique ;
* restauration de sauvegardes ;
* statistiques scolaires avancées ;
* recherche globale ;
* notifications ;
* historique des modifications ;
* gestion des paiements et frais scolaires ;
* synchronisation avec une base de données distante ;
* version réseau/client-serveur.

---

## Auteur

**EduManager**

Application de gestion scolaire développée en Python.

---

## Licence

Projet privé / propriétaire.

Toute reproduction, modification ou redistribution du projet doit être effectuée avec l'autorisation du propriétaire du projet.
