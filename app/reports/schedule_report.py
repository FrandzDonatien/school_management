"""Tableaux et rendu imprimable des emplois du temps."""
import html

from app.constants import DAYS, SLOTS
from app.services.schedule_service import cell_data
from app.services.settings_service import get_settings
from app.utils.formatting import ordinal


def slot_headers():
    return [f"{ordinal(i)}\n{s}-{e}" for i, (s, e) in enumerate(SLOTS)]


def tbl_general(cls_map):
    S = get_settings()
    header = ["CLASSE", "JOURS"] + slot_headers()
    rows, groups, used = [], [], {}
    for name, cid in cls_map.items():
        data = cell_data("c", cid)
        first = len(rows)
        for d, day in enumerate(DAYS):
            cells = []
            for s in range(len(SLOTS)):
                x = data.get((d, s))
                cells.append(x["code"] if x else "")
                if x:
                    used[x["code"]] = x["subj"]
            rows.append([name if d == 0 else "", day] + cells)
        groups.append((first, len(rows) - 1))
    legend = "Légende : " + " ; ".join(f"{k} = {v}" for k, v in sorted(used.items())) if used else ""
    return dict(sheet="Général", title=f"Emploi du temps général — {S['ecole_nom']}",
                caption=f"Année scolaire {S['annee']}", header=header, rows=rows, groups=groups, legend=legend)


def tbl_class(cid, cls_map):
    S = get_settings()
    name = {i: n for n, i in cls_map.items()}.get(cid, "")
    data = cell_data("c", cid)
    rows = []
    for d, day in enumerate(DAYS):
        cells = []
        for s in range(len(SLOTS)):
            x = data.get((d, s))
            cells.append("" if not x else x["code"] + ("\n" + x["teacher"] if x["teacher"] else ""))
        rows.append([day] + cells)
    return dict(sheet=name, title=f"Emploi du temps — {name}", caption=f"Année scolaire {S['annee']}",
                header=["JOURS"] + slot_headers(), rows=rows)


def tbl_teacher(tid, teachers):
    S = get_settings()
    name = {i: n for n, i in teachers.items()}.get(tid, "")
    data = cell_data("t", tid)
    rows = []
    for d, day in enumerate(DAYS):
        cells = []
        for s in range(len(SLOTS)):
            x = data.get((d, s))
            cells.append("" if not x else f"{x['cls']} {x['code']}")
        rows.append([day] + cells)
    return dict(sheet=name, title=f"{name} — {len(data)} heures/semaine", caption=f"Année scolaire {S['annee']}",
                header=["JOURS"] + slot_headers(), rows=rows)


def render_html_tables(tables):
    e = html.escape
    br = lambda s: e(str(s)).replace("\n", "<br>")
    sections = []
    for t in tables:
        starts = {a: b - a + 1 for a, b in t.get("groups", [])}
        inside = {i for a, b in t.get("groups", []) for i in range(a + 1, b + 1)}
        head = "".join("<th>" + br(h) + "</th>" for h in t["header"])
        rows = []
        for ri, row in enumerate(t["rows"]):
            cells = []
            for ci, v in enumerate(row):
                if ci == 0 and ri in inside:
                    continue
                if ci == 0 and ri in starts:
                    cells.append("<th rowspan='" + str(starts[ri]) + "'>" + br(v) + "</th>")
                elif ci == 0:
                    cells.append("<th>" + br(v) + "</th>")
                else:
                    cells.append("<td>" + br(v) + "</td>")
            rows.append("<tr>" + "".join(cells) + "</tr>")
        legend = "<p class='lg'>" + e(t["legend"]) + "</p>" if t.get("legend") else ""
        sections.append("<section><h2>" + e(t["title"]) + "</h2><p class='cp'>" + e(t.get("caption", "")) +
                        "</p><table><tr>" + head + "</tr>" + "".join(rows) + "</table>" + legend + "</section>")
    css = ("body{font-family:Arial,sans-serif;margin:20px;color:#1C2434}h2{margin:0 0 4px}.cp{color:#64748B;margin:0 0 10px;"
           "font-style:italic}table{border-collapse:collapse;width:100%}th,td{border:1px solid #888;padding:7px 4px;"
           "text-align:center;font-size:12px}tr:first-child th{background:#3C50E0;color:#fff}th{background:#EEF1FF}"
           "tr:first-child th{background:#3C50E0}.lg{font-size:11px;color:#475569;margin-top:10px}"
           "section{page-break-after:always;margin-bottom:30px}@page{size:A4 landscape;margin:10mm}"
           ".bar{background:#1C2434;color:#fff;padding:10px;margin:-20px -20px 16px}@media print{.bar{display:none}}")
    return ("<!DOCTYPE html><html lang='fr'><head><meta charset='utf-8'><title>Emplois du temps</title><style>" + css +
            "</style></head><body><div class='bar'>Emplois du temps "
            "<button onclick='window.print()'>Imprimer / Enregistrer en PDF</button></div>" + "".join(sections) +
            "</body></html>")
