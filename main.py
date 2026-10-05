"""
EduManager v5 - Gestion scolaire (CustomTkinter)

Installation :  pip install -r requirements.txt
Lancement    :  python main.py
Connexion    :  admin / admin123
"""
from app.config import ensure_dirs


def main():
    ensure_dirs()
    from app.database.migrations import init_db
    from app.services import backup_service
    from app.ui.app import App

    init_db()
    backup_service.create_backup()
    App().mainloop()


if __name__ == "__main__":
    main()
