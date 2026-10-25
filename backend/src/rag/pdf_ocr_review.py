"""Explicit OCR candidates for image-only pages, kept outside native v1/indexes."""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

from .pdf_adapters import open_layout_document, open_structure_document, render_ocr_page


def review_scan_page(path, pdf_page, *, source_sha256, language='spa+eng', dpi=200, engine=None):
    path = Path(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != source_sha256:
        raise ValueError('La fuente OCR cambió; revisar el hash registrado.')
    if type(pdf_page) is not int or pdf_page < 1 or type(dpi) is not int or not 100 <= dpi <= 400:
        raise ValueError('Página o resolución OCR fuera de los límites permitidos.')
    with open_structure_document(path) as structure:
        if structure.encrypted or pdf_page > structure.page_count:
            raise ValueError('Página OCR inexistente o PDF cifrado.')
    with open_layout_document(path) as document:
        for page in document.pages:
            try:
                if page.number == pdf_page and (page.characters or not page.image_count):
                    raise ValueError('OCR de revisión requiere una página de imagen sin texto nativo.')
            finally:
                page.close()
    if engine is None:
        from src.ocr.tesseract_strategy import TesseractStrategy
        engine = TesseractStrategy(language=language, scale=1.0)
    if getattr(engine, 'scale', 1.0) != 1.0:
        raise ValueError('El adaptador OCR de revisión requiere escala 1 para conservar coordenadas.')
    with TemporaryDirectory(prefix='ti-pdf-ocr-') as folder:
        image = render_ocr_page(path, pdf_page, dpi, Path(folder)/'page')
        raster_hash = hashlib.sha256(image.read_bytes()).hexdigest()
        result = engine.extract(image)
    # Original image coordinates, not native PDF characters or table cells.
    # An injected engine must use scale=1; larger preprocessing coordinates
    # cannot be represented faithfully by this candidate contract.
    words = []
    for block in result.blocks:
        box = block.bounding_box
        bbox = [box.left, box.top, box.left+box.width, box.top+box.height]
        if (min(bbox) < 0 or bbox[2] > result.image_size[0] or bbox[3] > result.image_size[1]
                or bbox[0] >= bbox[2] or bbox[1] >= bbox[3]):
            raise ValueError('Palabra OCR fuera de la imagen rasterizada.')
        words.append({'text': block.text, 'confidence': block.confidence, 'bbox': bbox})
    return {'schema_version': 'pdf-ocr-review-v1', 'source_sha256': source_sha256,
            'pdf_page': pdf_page, 'engine': result.engine, 'language': result.language,
            'dpi': dpi, 'raster_sha256': raster_hash, 'image_size': list(result.image_size),
            'coordinate_space': 'rendered_page_pixels', 'text': result.text, 'words': words,
            'mean_word_confidence': result.ocr_confidence, 'status': 'review',
            'text_index_eligible': False, 'human_review_performed': False,
            'limitations': ['OCR confidence is not semantic accuracy.',
                           'No reading-order, table-cell or figure interpretation is certified.',
                           'Raster coordinates are not native PDF point coordinates.']}
