"""Export des emplois du temps (Excel / page imprimable)."""
import re

from app.reports import schedule_report as report
from app.services.settings_service import get_settings
from app.utils.files import open_in_browser, safe_name


def build_tables(scope, cid, tid, cls_map, teachers):
    """-> (liste de tableaux, nom de base du fichier)."""
    if scope == "general":
        tables, base = [report.tbl_general(cls_map)], "Emploi_du_temps_general"
    elif scope == "classe":
        tables, base = [report.tbl_class(cid, cls_map)], "Emploi_du_temps_" + {i: n for n, i in cls_map.items()}.get(cid, "classe")
    elif scope == "enseignant":
        tables, base = [report.tbl_teacher(tid, teachers)], "Emploi_du_temps_" + {i: n for n, i in teachers.items()}.get(tid, "enseignant")
    elif scope == "enseignants":
        tables, base = [report.tbl_teacher(i, teachers) for i in teachers.values()], "Emplois_du_temps_enseignants"
    else:
        tables, base = [report.tbl_class(i, cls_map) for i in cls_map.values()], "Emplois_du_temps_classes"
    return tables, safe_name(base) + "_" + get_settings()["annee"]


def write_xlsx(path, tables):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.worksheet.properties import PageSetupProperties
    wb = Workbook()
    wb.remove(wb.active)
    used = set()
    thin = Side(style="thin", color="999999")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    for t in tables:
        title = re.sub(r"[\[\]:*?/\\]", "-", t["sheet"])[:28] or "Feuille"
        base, n = title, 2
        while title in used:
            title, n = f"{base[:25]}_{n}", n + 1
        used.add(title)
        ws = wb.create_sheet(title)
        ncol = len(t["header"])
        ws.append([t["title"]])
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncol)
        ws["A1"].font = Font(bold=True, size=14)
        ws.append([t.get("caption", "")])
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ncol)
        ws["A2"].font = Font(italic=True, color="64748B")
        ws.append(t["header"])
        hr = ws.max_row
        ws.row_dimensions[hr].height = 32
        for c in ws[hr]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="3C50E0")
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            c.border = border
        for row in t["rows"]:
            ws.append(row)
            r = ws.max_row
            multi = any("\n" in str(x) for x in row)
            ws.row_dimensions[r].height = 34 if multi else 20
            for c in ws[r]:
                c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                c.border = border
            ws.cell(r, 1).font = Font(bold=True)
        for a, b in t.get("groups", []):
            ws.merge_cells(start_row=hr + 1 + a, start_column=1, end_row=hr + 1 + b, end_column=1)
        ws.column_dimensions["A"].width = 14
        for k in range(2, ncol + 1):
            ws.column_dimensions[ws.cell(hr, k).column_letter].width = 13 if t.get("groups") else 16
        if t.get("legend"):
            ws.append([])
            ws.append([t["legend"]])
            ws.merge_cells(start_row=ws.max_row, start_column=1, end_row=ws.max_row, end_column=ncol)
            ws.cell(ws.max_row, 1).alignment = Alignment(wrap_text=True, vertical="top")
            ws.row_dimensions[ws.max_row].height = 48
        ws.page_setup.orientation = "landscape"
        ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
        ws.page_setup.fitToHeight = 0
    wb.save(path)


def write_html(path, tables):
    with open(path, "w", encoding="utf-8") as f:
        f.write(report.render_html_tables(tables))
    open_in_browser(path)


def write_file(path, tables, fmt):
    """fmt : 'xlsx' ou 'html'. Lève ImportError si openpyxl est absent (xlsx)."""
    if fmt == "xlsx":
        write_xlsx(path, tables)
    else:
        write_html(path, tables)
