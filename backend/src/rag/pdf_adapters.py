"""Library boundaries for PDF structure and page geometry.

Only this module understands pypdf destinations and pdfplumber objects.
The interfaces use Python data; layout policy belongs to the extractor.
Libraries are imported only when their document context is opened.
"""
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol, runtime_checkable

PDFObject = dict[str, Any]


@dataclass(frozen=True)
class OutlineEntry:
    title: str
    pdf_page: int
    top: float
    ancestors: tuple[str, ...]


@dataclass(frozen=True)
class TableSnapshot:
    bbox: tuple[float, ...]
    column_count: int
    row_boxes: list[tuple[float, ...]]
    grid: list[list[str | None]]


@runtime_checkable
class StructureDocument(Protocol):
    @property
    def encrypted(self) -> bool: ...
    @property
    def page_count(self) -> int: ...
    def outline_entries(self) -> list[OutlineEntry]: ...


@runtime_checkable
class LayoutPage(Protocol):
    @property
    def number(self) -> int: ...
    @property
    def height(self) -> float: ...
    @property
    def characters(self) -> list[PDFObject]: ...
    @property
    def image_count(self) -> int: ...
    def lines(self, **options) -> list[PDFObject]: ...
    def select(self, predicate: Callable[[PDFObject], bool]) -> 'LayoutPage': ...
    def region(self, box: tuple) -> 'LayoutPage': ...
    def tables(self, settings: dict | None = None) -> list[TableSnapshot]: ...
    def close(self) -> None: ...


class LayoutDocument(Protocol):
    @property
    def pages(self) -> Iterable[LayoutPage]: ...


class PypdfStructureAdapter:
    def __init__(self, reader):
        self._reader = reader

    @property
    def encrypted(self):
        return self._reader.is_encrypted

    @property
    def page_count(self):
        return len(self._reader.pages)

    def outline_entries(self):
        entries = []

        def visit(items, ancestors=()):
            previous = None
            for item in items:
                if isinstance(item, list):
                    if previous is None:
                        raise ValueError('Marcadores sin padre; revisar el índice del PDF.')
                    visit(item, ancestors + (previous,))
                    continue
                previous = item.title
                page = self._reader.get_destination_page_number(item) + 1
                height = float(self._reader.pages[page - 1].mediabox.height)
                top = max(0, height - float(item.get('/Top') or height))
                entries.append(OutlineEntry(item.title, page, top, ancestors))

        visit(self._reader.outline)
        return entries


def table_snapshot(table):
    """Compatibility boundary for callers of the existing table_block helper."""
    if isinstance(table, TableSnapshot):
        return table
    return TableSnapshot(tuple(table.bbox), len(table.columns),
                         [tuple(row.bbox) for row in table.rows],
                         table.extract(x_tolerance=2, y_tolerance=3))


class PdfplumberPageAdapter:
    def __init__(self, page):
        self._page = page

    @property
    def number(self):
        return self._page.page_number

    @property
    def height(self):
        return self._page.height

    @property
    def characters(self):
        # Preserve dictionary identity across filtered views for exact exclusion
        # accounting. No native page/table object crosses this interface.
        return self._page.chars

    @property
    def image_count(self):
        return len(self._page.images)

    def lines(self, **options):
        return self._page.extract_text_lines(**options)

    def select(self, predicate):
        return PdfplumberPageAdapter(self._page.filter(predicate))

    def region(self, box):
        return PdfplumberPageAdapter(self._page.crop(box))

    def tables(self, settings=None):
        tables = self._page.find_tables() if settings is None else self._page.find_tables(settings)
        return [table_snapshot(table) for table in tables]

    def close(self):
        self._page.close()


class PdfplumberDocumentAdapter:
    def __init__(self, document):
        self._document = document

    @property
    def pages(self):
        return (PdfplumberPageAdapter(page) for page in self._document.pages)


def structure_document(reader):
    """Accept legacy raw readers only at the public helper boundary."""
    return reader if isinstance(reader, StructureDocument) else PypdfStructureAdapter(reader)


def layout_page(page):
    """Accept legacy raw pages only at the public helper boundary."""
    return page if isinstance(page, LayoutPage) else PdfplumberPageAdapter(page)


@contextmanager
def open_structure_document(path):
    from pypdf import PdfReader

    with Path(path).open('rb') as stream:
        yield PypdfStructureAdapter(PdfReader(stream))


@contextmanager
def open_layout_document(path):
    import pdfplumber

    with pdfplumber.open(path, unicode_norm='NFC') as document:
        yield PdfplumberDocumentAdapter(document)


@dataclass(frozen=True)
class PDFBackends:
    open_structure: Callable[[Path], AbstractContextManager[StructureDocument]] = open_structure_document
    open_layout: Callable[[Path], AbstractContextManager[LayoutDocument]] = open_layout_document


DEFAULT_BACKENDS = PDFBackends()


def render_ocr_page(path, number, dpi, output_prefix):
    """Optional local Poppler boundary; no shell, downloads or source mutation."""
    import shutil
    import subprocess

    executable = shutil.which('pdftoppm')
    if executable is None:
        raise RuntimeError('OCR de PDF requiere pdftoppm (Poppler) instalado localmente.')
    subprocess.run([executable, '-f', str(number), '-l', str(number), '-r', str(dpi),
                    '-singlefile', '-png', str(Path(path).resolve()), str(output_prefix)],
                   check=True, capture_output=True, timeout=60)
    return Path(str(output_prefix) + '.png')
