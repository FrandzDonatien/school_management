from app.repositories import year_repository
from app.services.settings_service import set_setting


def create_year(libelle, src, base, cls, asg, stu):
    """Crée une année et copie éventuellement des données de src.
    Lève sqlite3.IntegrityError si l'année existe déjà."""
    if asg:
        base = cls = True
    if stu:
        cls = True
    if src is None:
        base = cls = asg = stu = False
    yid = year_repository.create(libelle)
    year_repository.copy_data(src, yid, base, cls, asg, stu)
    return yid


def activate(year_id):
    set_setting("annee_id", str(year_id))


def delete_year(year_id):
    year_repository.delete(year_id)
