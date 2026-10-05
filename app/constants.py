"""Constantes globales (couleurs, jours, périodes, listes mutables d'horaires)."""

FONT = "Segoe UI"
C = dict(
    primary="#3C50E0", primary_dark="#2F40B8", primary_light="#EEF1FF", sidebar="#1C2434",
    sidebar_hover="#333A48", sidebar_text="#C5CEDC", bg="#F1F5F9", card="#FFFFFF", border="#E8EDF3",
    text="#1C2434", muted="#64748B", success="#10B981", success_light="#DCFCE7",
    danger="#D34053", danger_hover="#B82E40", warning="#FFA70B", warning_light="#FFF4DB",
    info="#13C296", info_light="#D9F7EE", soft="#F8FAFC",
)
CHART_COLORS = ["#3C50E0", "#10B981", "#FFA70B", "#D34053", "#8B5CF6", "#0EA5E9", "#F97316", "#64748B"]
R = 12  # rayon des coins

DAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]
PERIODES = ["Trimestre 1", "Trimestre 2", "Trimestre 3"]
PALETTE = [("#E0E7FF", "#3730A3"), ("#DCFCE7", "#166534"), ("#FEF3C7", "#92400E"), ("#FCE7F3", "#9D174D"),
           ("#CFFAFE", "#155E75"), ("#FFEDD5", "#9A3412"), ("#EDE9FE", "#5B21B6"), ("#E2E8F0", "#334155")]
JOURS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre",
           "octobre", "novembre", "décembre"]

# Horaires calculés à partir des paramètres : listes MODIFIÉES EN PLACE par
# settings_service.load_plan() (ne jamais les réaffecter, sinon les imports deviennent obsolètes).
PLAN, SLOTS = [], []
TIME_KEYS = ["matin_debut", "matin_fin", "apres_debut", "apres_fin", "pause_debut", "pause_fin"]

DEFAULT_CODES = {"mathématiques": "MATHS", "français": "FR", "anglais": "ANG", "physique-chimie": "PCT",
                 "svt": "SVT", "histoire-géographie": "HG", "eps": "EPS", "éducation civique et morale": "ECM",
                 "ecm": "ECM"}

DEFAULT_ADMIN = ("admin", "admin123")
