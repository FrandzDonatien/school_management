"""Catégories de matières (Littéraire, Scientifique, Optionnelle...) — paramétrables."""
from app.database.connection import conn, query


def list_all():
    return query("""SELECT c.id, c.nom, c.titre, c.ordre,
                    (SELECT COUNT(*) FROM subjects s WHERE s.categorie_id=c.id) AS n
                    FROM categories c ORDER BY c.ordre, c.id""")


def get(cid):
    r = query("SELECT * FROM categories WHERE id=?", (cid,))
    return r[0] if r else None


def options():
    return {r["nom"]: r["id"] for r in list_all()}


def create(nom, titre=""):
    """Lève sqlite3.IntegrityError si le nom existe déjà."""
    ordre = query("SELECT COALESCE(MAX(ordre),0)+1 FROM categories")[0][0]
    cid = conn.execute("INSERT INTO categories(nom,titre,ordre) VALUES(?,?,?)", (nom, titre, ordre)).lastrowid
    conn.commit()
    return cid


def update(cid, nom, titre=""):
    conn.execute("UPDATE categories SET nom=?, titre=? WHERE id=?", (nom, titre, cid))
    conn.commit()


def delete(cid):
    conn.execute("UPDATE subjects SET categorie_id=NULL WHERE categorie_id=?", (cid,))
    conn.execute("DELETE FROM categories WHERE id=?", (cid,))
    conn.commit()


def move(cid, delta):
    """Monte (delta=-1) ou descend (delta=+1) une catégorie dans l'ordre d'affichage."""
    ids = [r["id"] for r in list_all()]
    if cid not in ids:
        return
    i, j = ids.index(cid), ids.index(cid) + delta
    if 0 <= j < len(ids):
        ids[i], ids[j] = ids[j], ids[i]
        for n, k in enumerate(ids, 1):
            conn.execute("UPDATE categories SET ordre=? WHERE id=?", (n, k))
        conn.commit()