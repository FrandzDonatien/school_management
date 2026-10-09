import customtkinter as ctk

from app.ui.components.data_table import setup_style
from app.ui.login import LoginFrame
from app.ui.main_window import MainFrame
from app.constants import C
from pathlib import Path
import sys

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

def resource_path(relative_path):
    """Retourne le chemin d'une ressource, y compris après compilation PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative_path

    return Path(__file__).resolve().parent.parent.parent / relative_path

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("EduManager — Gestion scolaire")
        self.iconbitmap(str(resource_path("assets/EduManager_fixed.ico")))
        self.geometry("1380x820")
        self.minsize(1220, 740)
        self.configure(fg_color=C["bg"])
        setup_style()
        self.current = None
        self.show_login()

    def swap(self, frame):
        if self.current:
            self.current.destroy()
        self.current = frame
        frame.pack(fill="both", expand=True)

    def show_login(self):
        self.swap(LoginFrame(self, self.show_main))

    def show_main(self, username):
        self.swap(MainFrame(self, username, self.show_login))
