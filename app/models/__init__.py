"""Modèles de données (dataclasses) construits à partir des lignes SQLite."""


def row_to(cls, row):
    """Construit un modèle à partir d'une sqlite3.Row en ignorant les colonnes inconnues."""
    from dataclasses import fields
    keys = row.keys()
    return cls(**{f.name: row[f.name] for f in fields(cls) if f.name in keys})
