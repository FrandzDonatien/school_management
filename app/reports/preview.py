"""Rendu à l'écran des pages d'un PDF (aperçu du bulletin) avec PyMuPDF : pip install pymupdf"""


class PdfPreview:
    def __init__(self, data):
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz                                   # anciennes versions de PyMuPDF
        self._fitz = fitz
        self._doc = fitz.open(stream=data, filetype="pdf")
        self.count = self._doc.page_count
        self._cache = {}

    def render(self, index, zoom):
        """Image PIL de la page `index` (0 = première) ; zoom 1.0 = 72 dpi."""
        key = (index, round(zoom, 2))
        if key not in self._cache:
            from PIL import Image
            pix = self._doc[index].get_pixmap(matrix=self._fitz.Matrix(zoom, zoom), alpha=False)
            if len(self._cache) >= 6:                     # petit cache : évite de re-rendre en changeant de zoom
                self._cache.pop(next(iter(self._cache)))
            self._cache[key] = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        return self._cache[key]

    def close(self):
        self._doc.close()