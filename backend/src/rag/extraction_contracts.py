"""Structural contracts for the existing external PDF extraction format v1.

Validation does not rewrite the payload. Source metadata and document-specific
profile settings remain extensible; extraction records reject unknown fields.
Figure references and diagnostics are separate contracts, not invented v1 blocks.
"""
from collections import Counter
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Text = Annotated[str, Field(min_length=1, pattern=r'\S')]
PositiveInt = Annotated[int, Field(gt=0)]
Count = Annotated[int, Field(ge=0)]
Coordinate = Annotated[float, Field(allow_inf_nan=False)]
Box = Annotated[list[Coordinate], Field(min_length=4, max_length=4)]
SHA256 = Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]


class Record(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


def ordered_box(box):
    if box[0] > box[2] or box[1] > box[3]:
        raise ValueError('Coordenadas invertidas: se espera x0, top, x1, bottom.')
    return box


class TableOverride(Record):
    pdf_page: PositiveInt
    bbox: Box
    settings: dict[str, Any]
    reason: Text

    @model_validator(mode='after')
    def geometry(self):
        ordered_box(self.bbox)
        return self


class ExcludedPageRange(Record):
    first: PositiveInt
    last: PositiveInt
    reason: Text

    @model_validator(mode='after')
    def order(self):
        if self.first > self.last:
            raise ValueError('Rango de exclusión invertido.')
        return self


class ExtractionProfile(Record):
    # Future strategies may add settings without altering stored source metadata.
    model_config = ConfigDict(extra='allow', strict=True)
    parser: Text
    content_pdf_page_range: Annotated[list[PositiveInt], Field(min_length=2, max_length=2)]
    excluded_pdf_page_ranges: list[ExcludedPageRange]
    running_header_bottom: Coordinate
    running_header_max_font_size: Coordinate
    footer_height: Coordinate
    right_sidebar_x0: Coordinate
    table_overrides: list[TableOverride] = Field(default_factory=list)

    @model_validator(mode='after')
    def order(self):
        if self.content_pdf_page_range[0] > self.content_pdf_page_range[1]:
            raise ValueError('Rango de contenido invertido.')
        return self


class DocumentSource(Record):
    model_config = ConfigDict(extra='allow', strict=True)
    document_id: Text
    path: Text
    sha256: SHA256
    version: Text
    language: Text
    simulated: bool
    pages: PositiveInt
    size_bytes: PositiveInt
    extraction_profile: ExtractionProfile

    @model_validator(mode='after')
    def external_source(self):
        if self.simulated:
            raise ValueError('El contrato externo requiere simulated=false.')
        return self


class ExtractedPage(Record):
    status: Literal['extracted']
    pdf_page: PositiveInt
    printed_page: PositiveInt
    source_characters: PositiveInt
    body_characters: Count
    table_count: Count
    non_table_lines: Count


class ExcludedPage(Record):
    status: Literal['excluded']
    pdf_page: PositiveInt
    printed_page: PositiveInt | None
    source_characters: Count
    table_count: Annotated[int, Field(ge=0, le=0)]
    reason: Text


Page = Annotated[ExtractedPage | ExcludedPage, Field(discriminator='status')]


class LocatedBlock(Record):
    id: Text
    pdf_page: PositiveInt
    printed_page: PositiveInt
    bbox: Box

    @model_validator(mode='after')
    def geometry(self):
        ordered_box(self.bbox)
        return self


class Paragraph(LocatedBlock):
    type: Literal['paragraph']
    text: Text


class TableRow(Record):
    id: Text
    row_number: PositiveInt
    cells: list[str | None]
    bbox: Box

    @model_validator(mode='after')
    def geometry(self):
        ordered_box(self.bbox)
        return self


class Table(LocatedBlock):
    type: Literal['table']
    headers: Annotated[list[str], Field(min_length=2)]
    raw_header: list[str | None]
    rows: Annotated[list[TableRow], Field(min_length=1)]
    review_flags: list[Text]
    text_index_eligible: bool
    continuation_candidate_of: Text | None = None

    @model_validator(mode='after')
    def grid(self):
        columns = len(self.headers)
        if len(self.raw_header) != columns or any(len(r.cells) != columns for r in self.rows):
            raise ValueError('Fila o encabezado con número de columnas inconsistente.')
        if [r.row_number for r in self.rows] != list(range(1, len(self.rows) + 1)):
            raise ValueError('Numeración de filas incompleta o duplicada.')
        if self.text_index_eligible != (not self.review_flags):
            raise ValueError('Elegibilidad textual incompatible con indicadores de revisión.')
        if self.text_index_eligible and (any(not h.strip() for h in self.headers)
                or any(c is None or not c.strip() for r in self.rows for c in r.cells)):
            raise ValueError('Tabla con celdas ambiguas marcada como evidencia textual completa.')
        for row in self.rows:
            if (row.bbox[0] < self.bbox[0] - .01 or row.bbox[1] < self.bbox[1] - .01
                    or row.bbox[2] > self.bbox[2] + .01 or row.bbox[3] > self.bbox[3] + .01):
                raise ValueError('Fila fuera de las coordenadas de su tabla.')
        return self


Block = Annotated[Paragraph | Table, Field(discriminator='type')]


class ExtractionSection(Record):
    id: Text
    title: Text
    heading_path: Annotated[list[Text], Field(min_length=1)]
    level: Count
    start_pdf_page: PositiveInt
    start_top: Coordinate
    blocks: list[Block]
    ancestor_section_ids: list[Text]
    pages: list[PositiveInt]
    text: str  # Structural bookmarks can legitimately contain no own blocks.

    @model_validator(mode='after')
    def hierarchy(self):
        if self.heading_path[-1] != self.title or self.level != len(self.heading_path) - 1:
            raise ValueError('Título, nivel y jerarquía de sección inconsistentes.')
        if self.pages != sorted({b.pdf_page for b in self.blocks}):
            raise ValueError('Páginas de sección distintas de sus bloques.')
        return self


class ExcludedLayoutText(Record):
    pdf_page: PositiveInt
    text: Text
    reason: Text


class ExtractionResult(Record):
    schema_version: int
    parser_version: Text
    document: DocumentSource
    profile: ExtractionProfile
    pages: list[Page]
    excluded_layout_text: list[ExcludedLayoutText]
    sections: list[ExtractionSection]
    limitations: list[Text]

    @model_validator(mode='after')
    def references(self):
        if self.schema_version != 1:
            raise ValueError('Versión de extracción no admitida; se requiere v1.')
        if self.parser_version != self.profile.parser or self.profile != self.document.extraction_profile:
            raise ValueError('Perfil o parser difiere de la fuente registrada.')
        if [p.pdf_page for p in self.pages] != list(range(1, self.document.pages + 1)):
            raise ValueError('Páginas ausentes, duplicadas o fuera de orden.')
        first, last = self.profile.content_pdf_page_range
        if last > self.document.pages:
            raise ValueError('Contenido fuera del PDF registrado.')
        for page in self.pages:
            if (first <= page.pdf_page <= last) != (page.status == 'extracted'):
                raise ValueError('Estado de página incompatible con rango de contenido.')
            if page.status == 'excluded':
                reasons = [r.reason for r in self.profile.excluded_pdf_page_ranges
                           if r.first <= page.pdf_page <= r.last]
                if reasons != [page.reason]:
                    raise ValueError('Página excluida sin motivo único del perfil.')
        sections = {s.id: s for s in self.sections}
        if not sections or len(sections) != len(self.sections):
            raise ValueError('Secciones vacías o identificadores repetidos.')
        pages = {p.pdf_page: p for p in self.pages}
        identifiers = set(sections)
        table_counts = Counter()
        for section in self.sections:
            if not first <= section.start_pdf_page <= last:
                raise ValueError('Sección fuera de las páginas de contenido.')
            expected = [s.id for s in self.sections if len(s.heading_path) < len(section.heading_path)
                        and section.heading_path[:len(s.heading_path)] == s.heading_path]
            if section.ancestor_section_ids != expected:
                raise ValueError('Referencias de antecesores incompletas o incorrectas.')
            preceding_tables = {}
            for block in section.blocks:
                ids = [block.id] + ([r.id for r in block.rows] if isinstance(block, Table) else [])
                for ident in ids:
                    if ident in identifiers:
                        raise ValueError('Identificador de bloque o fila duplicado.')
                    identifiers.add(ident)
                page = pages.get(block.pdf_page)
                if page is None or page.status != 'extracted' or page.printed_page != block.printed_page:
                    raise ValueError('Procedencia de bloque incompatible con auditoría de página.')
                if (block.pdf_page, block.bbox[1] + 1) < (section.start_pdf_page, section.start_top):
                    raise ValueError('Bloque situado antes del comienzo de su sección.')
                if isinstance(block, Table):
                    table_counts[block.pdf_page] += 1
                    if block.continuation_candidate_of is not None:
                        previous = preceding_tables.get(block.continuation_candidate_of)
                        if previous is None or previous.pdf_page != block.pdf_page - 1 or previous.headers != block.headers:
                            raise ValueError('Continuación de tabla sin referencia anterior compatible.')
                    preceding_tables[block.id] = block
        if any(table_counts[p.pdf_page] != p.table_count for p in self.pages):
            raise ValueError('Cantidad de tablas distinta de la auditoría de página.')
        if any(t.pdf_page not in pages or pages[t.pdf_page].status != 'extracted' for t in self.excluded_layout_text):
            raise ValueError('Texto excluido sin página de contenido válida.')
        return self


class FigureReference(LocatedBlock):
    """Separate future-facing reference; v1 does not extract or interpret figures."""
    type: Literal['figure_reference']
    document_id: Text
    caption: Text | None = None
    interpretation_status: Literal['not_performed']


class ExtractionDiagnostic(Record):
    code: Text
    severity: Literal['info', 'review', 'error']
    message: Text
    document_id: Text
    pdf_page: PositiveInt | None = None
    section_id: Text | None = None
    block_id: Text | None = None


def validate_extraction(payload: dict) -> ExtractionResult:
    """Return a validated view; callers retain the original dict for serialization."""
    return ExtractionResult.model_validate(payload)
