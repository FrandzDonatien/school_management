import os
import re
import subprocess
import sys
import webbrowser

from app.config import BULLETINS_DIR


def safe_name(name):
    return re.sub(r"[^\w\-]+", "_", name)


def open_in_browser(path):
    webbrowser.open("file://" + path)


def open_file(path):
    """Ouvre un fichier avec l'application par défaut du système (lecteur PDF, etc.)."""
    if sys.platform.startswith("win"):
        os.startfile(path)  # noqa: S606 (Windows uniquement)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def pdf_path(name, folder=BULLETINS_DIR):
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, safe_name(name) + ".pdf")


def write_and_open(doc, name, folder=BULLETINS_DIR):
    """Écrit un document HTML et l'ouvre dans le navigateur (conservé pour les autres usages)."""
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, safe_name(name) + ".html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)
    open_in_browser(path)
    return path