"""Rendu des pages d'un PDF en images, pour l'aperçu dans l'application.

Utilise pypdfium2 (pip install pypdfium2) ou, à défaut, PyMuPDF (pip install pymupdf).
Les pages sont rendues à la demande : l'aperçu d'une classe entière reste rapide.
"""


class PdfPages:
    def __init__(self, data):
        self._data = data  # conservé : la bibliothèque lit ce tampon à la demande
        try:
            import pypdfium2 as pdfium
            self._pdf, self._kind = pdfium.PdfDocument(data), "pdfium"
            self._n = len(self._pdf)
        except ImportError:
            try:
                import fitz
                self._pdf, self._kind = fitz.open(stream=data, filetype="pdf"), "fitz"
                self._n = self._pdf.page_count
            except ImportError:
                raise ImportError("pypdfium2 est requis pour l'aperçu", name="pypdfium2") from None

    def __len__(self):
        return self._n

    def render(self, index, width_px):
        """Page `index` (à partir de 0) sous forme d'image PIL de largeur `width_px`."""
        if self._kind == "pdfium":
            page = self._pdf[index]
            return page.render(scale=width_px / page.get_width()).to_pil().convert("RGB")
        from PIL import Image
        import fitz
        page = self._pdf[index]
        k = width_px / page.rect.width
        pix = page.get_pixmap(matrix=fitz.Matrix(k, k), alpha=False)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    def close(self):
        try:
            self._pdf.close()
        except Exception:
            pass