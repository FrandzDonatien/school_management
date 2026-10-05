from app.repositories import teacher_repository
from app.services.settings_service import default_hours


def teacher_target(tid):
    """Objectif horaire d'un enseignant : valeur de sa fiche, sinon valeur par défaut."""
    h = teacher_repository.target_hours(tid)
    return int(round(h)) if h else default_hours()
