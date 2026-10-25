"""Explicit page/region strategies; no automatic OCR or unreviewed fallback.

The legacy Ricoh profile selects native text and ruled tables by default.
Selection traces are sidecars, never additions to the extraction v1 payload.
"""
from collections import Counter
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import Field, model_validator

from .extraction_contracts import Box, ExtractionDiagnostic, PositiveInt, Record, Text, ordered_box
from .pdf_adapters import LayoutPage, TableSnapshot

TextMode = Literal['native_text', 'column_text']
TableMode = Literal['ruled_tables', 'text_only', 'borderless_tables']


def validate_borderless_settings(settings, box):
    """Reviewed cell boundaries, not guessed rows from aligned prose."""
    if not isinstance(settings, dict) or set(settings) != {
            'vertical_strategy', 'horizontal_strategy', 'explicit_vertical_lines', 'explicit_horizontal_lines'}:
        raise ValueError('borderless_tables requiere límites explícitos de filas y columnas.')
    for axis, start, end in [('vertical', box[0], box[2]), ('horizontal', box[1], box[3])]:
        values = settings.get(f'explicit_{axis}_lines')
        if (settings.get(f'{axis}_strategy') != 'explicit' or not isinstance(values, list)
                or len(values) < 3 or any(type(v) not in (int, float) for v in values)
                or any(not start <= v <= end for v in values)
                or any(a >= b for a, b in zip(values, values[1:]))):
            raise ValueError('Límites de celdas inválidos o fuera de la región revisada.')


class RegionRule(Record):
    bbox: Box
    tables: TableMode
    reason: Text
    settings: dict | None = None

    @model_validator(mode='after')
    def geometry(self):
        ordered_box(self.bbox)
        if min(self.bbox) < 0 or self.bbox[0] == self.bbox[2] or self.bbox[1] == self.bbox[3]:
            raise ValueError('La región debe tener área positiva y coordenadas no negativas.')
        if self.tables == 'text_only' and self.settings is not None:
            raise ValueError('text_only no admite parámetros de detección de tablas.')
        if self.tables == 'borderless_tables':
            validate_borderless_settings(self.settings, self.bbox)
        return self


def overlap(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


class PageRule(Record):
    first: PositiveInt
    last: PositiveInt
    text: TextMode = 'native_text'
    tables: TableMode = 'ruled_tables'
    reason: Text
    regions: list[RegionRule] = Field(default_factory=list)
    columns: list[Box] = Field(default_factory=list)

    @model_validator(mode='after')
    def bounds(self):
        if self.first > self.last:
            raise ValueError('Rango de estrategia invertido.')
        if self.tables == 'borderless_tables':
            raise ValueError('borderless_tables solo se selecciona en una región con límites revisados.')
        if self.text == 'column_text' and len(self.columns) < 2:
            raise ValueError('column_text requiere dos o más columnas explícitas en orden de lectura.')
        if self.text != 'column_text' and self.columns:
            raise ValueError('Las columnas requieren seleccionar column_text.')
        for i, column in enumerate(self.columns):
            ordered_box(column)
            if min(column) < 0 or column[0] == column[2] or column[1] == column[3]:
                raise ValueError('Columna sin área o con coordenadas negativas.')
            if any(overlap(column, other) for other in self.columns[:i]):
                raise ValueError('Columnas superpuestas; no inferir orden de lectura.')
        for i, region in enumerate(self.regions):
            if any(overlap(region.bbox, other.bbox) for other in self.regions[:i]):
                raise ValueError('Regiones de estrategia superpuestas; no inferir precedencia.')
        return self


class StrategyPolicy(Record):
    default_text: TextMode = 'native_text'
    default_tables: TableMode = 'ruled_tables'
    default_reason: Text = 'Perfil revisado existente: texto nativo y tablas con bordes.'
    pages: list[PageRule] = Field(default_factory=list)

    @model_validator(mode='after')
    def unambiguous(self):
        if self.default_text != 'native_text' or self.default_tables == 'borderless_tables':
            raise ValueError('Columnas y tablas sin bordes requieren reglas de página/región explícitas.')
        if self.default_tables != 'ruled_tables' and 'default_reason' not in self.model_fields_set:
            raise ValueError('Una estrategia predeterminada diferente requiere justificación explícita.')
        for i, rule in enumerate(self.pages):
            if any(rule.first <= other.last and other.first <= rule.last for other in self.pages[:i]):
                raise ValueError('Rangos de estrategia superpuestos; no inferir precedencia.')
        return self


def validate_policy(profile, page_count):
    policy = StrategyPolicy.model_validate(profile.get('strategies', {}))
    if any(rule.last > page_count for rule in policy.pages):
        raise ValueError('Estrategia configurada fuera del PDF registrado.')
    return policy


class TextStrategy(Protocol):
    def extract(self, page: LayoutPage, *, columns: tuple | None = None) -> list[dict]: ...


class TableStrategy(Protocol):
    def extract(self, page: LayoutPage, profile: dict, *, settings: dict | None = None) -> list[TableSnapshot]: ...


class NativeTextStrategy:
    def extract(self, page, *, columns=None):
        return page.lines(x_tolerance=2, y_tolerance=3)


def containing_column(box, columns):
    matches = [i for i, c in enumerate(columns) if c[0] <= box[0] and c[1] <= box[1]
               and c[2] >= box[2] and c[3] >= box[3]]
    if len(matches) != 1:
        raise ValueError('Contenido fuera de una columna única; revisar regiones antes de extraer.')
    return matches[0]


def validate_column_sections(sections, number, selection):
    if selection.text != 'column_text':
        return
    if len(selection.columns) < 2:
        raise ValueError('column_text requiere columnas explícitas.')
    starts = [s for s in sections if s['start_pdf_page'] == number]
    if len(starts) > 1 or (starts and starts[0]['start_top'] > min(c[1] for c in selection.columns)):
        raise ValueError('Marcadores dentro de columnas requieren un contrato de secciones con eje horizontal.')


class ColumnTextStrategy:
    def extract(self, page, *, columns=None):
        if columns is None or len(columns) < 2:
            raise ValueError('column_text requiere columnas explícitas.')
        grouped = [[] for _ in columns]
        for char in page.characters:
            index = containing_column([char['x0'], char['top'], char['x1'], char['bottom']], columns)
            grouped[index].append(char)
        lines = []
        for index, chars in enumerate(grouped):
            identifiers = {id(char) for char in chars}
            view = page.select(lambda char: char.get('object_type') != 'char' or id(char) in identifiers)
            lines.extend({**line, '_column_order': index}
                         for line in view.lines(x_tolerance=2, y_tolerance=3))
        return lines


class BorderlessTableStrategy:
    def extract(self, page, profile, *, settings=None):
        if settings is None:
            raise ValueError('borderless_tables requiere geometría explícita por región.')
        tables = page.tables(settings)
        if (len(tables) != 1 or tables[0].column_count != len(settings['explicit_vertical_lines']) - 1
                or len(tables[0].grid) != len(settings['explicit_horizontal_lines']) - 1):
            raise ValueError('La tabla sin bordes no coincide con las celdas revisadas.')
        table = tables[0]
        # Every native character in the reviewed grid must survive in a cell.
        box = table.bbox
        expected = Counter(c['text'] for c in page.characters
                           if box[0] <= c['x0'] and box[1] <= c['top'] and c['x1'] <= box[2]
                           and c['bottom'] <= box[3] and not c['text'].isspace())
        actual = Counter(ch for row in table.grid for cell in row if cell for ch in cell if not ch.isspace())
        if expected != actual:
            raise ValueError('Límites de tabla sin bordes cortan o pierden caracteres; revisar geometría.')
        return tables


class RuledTableStrategy:
    def extract(self, page, profile, *, settings=None):
        tables = page.tables() if settings is None else page.tables(settings)
        for override in profile.get('table_overrides', []):
            if override['pdf_page'] != page.number:
                continue
            box = override['bbox']
            replaced = [t for t in tables if all(abs(a-b) < 1 for a, b in zip(t.bbox, box))]
            if len(replaced) != 1:
                raise ValueError('La tabla no coincide con la corrección de geometría revisada.')
            repaired = page.region(tuple(box)).tables(override['settings'])
            if len(repaired) != 1:
                raise ValueError('La corrección de geometría no produjo una tabla única.')
            tables.remove(replaced[0])
            tables.extend(repaired)
        return sorted(tables, key=lambda t: (t.bbox[1], t.bbox[0]))


class TextOnlyTableStrategy:
    def extract(self, page, profile, *, settings=None):
        if settings is not None:
            raise ValueError('text_only no admite parámetros de detección de tablas.')
        if any(o['pdf_page'] == page.number for o in profile.get('table_overrides', [])):
            raise ValueError('text_only entra en conflicto con una corrección de tabla revisada.')
        return []


@dataclass(frozen=True)
class StrategySelection:
    text: str
    tables: str
    reason: str
    regions: tuple[RegionRule, ...] = ()
    columns: tuple = ()


def select_strategy(policy, number):
    rule = next((r for r in policy.pages if r.first <= number <= r.last), None)
    if rule:
        return StrategySelection(rule.text, rule.tables, rule.reason, tuple(rule.regions), tuple(rule.columns))
    return StrategySelection(policy.default_text, policy.default_tables, policy.default_reason)


class ExtractionStrategies:
    def __init__(self, *, text=None, tables=None):
        self.text = {'native_text': NativeTextStrategy(), 'column_text': ColumnTextStrategy()} if text is None else dict(text)
        self.tables = {'ruled_tables': RuledTableStrategy(), 'text_only': TextOnlyTableStrategy(),
                       'borderless_tables': BorderlessTableStrategy()} if tables is None else dict(tables)

    def require(self, selection):
        table_modes = [selection.tables, *[r.tables for r in selection.regions]]
        if selection.text not in self.text or any(name not in self.tables for name in table_modes):
            raise ValueError('Estrategia no implementada; no se aplica una sustitución automática.')

    def text_lines(self, page, selection):
        self.require(selection)
        if selection.text == 'column_text':
            return self.text[selection.text].extract(page, columns=selection.columns)
        return self.text[selection.text].extract(page)

    def table_snapshots(self, page, profile, selection):
        self.require(selection)
        tables = list(self.tables[selection.tables].extract(page, profile))
        for region in selection.regions:
            box = region.bbox
            if box[3] > page.height:
                raise ValueError('Región fuera de la altura de la página.')
            # A region may replace complete tables, never slice rows of one.
            affected = [t for t in tables if overlap(t.bbox, box)]
            if any(t.bbox[0] < box[0]-.01 or t.bbox[1] < box[1]-.01
                   or t.bbox[2] > box[2]+.01 or t.bbox[3] > box[3]+.01 for t in affected):
                raise ValueError('La región corta una tabla; revisar límites antes de extraer.')
            replacement = []
            if region.tables != 'text_only':
                if region.tables == 'borderless_tables':
                    xs, ys = region.settings['explicit_vertical_lines'], region.settings['explicit_horizontal_lines']
                    cells = [[x0, y0, x1, y1] for x0, x1 in zip(xs, xs[1:]) for y0, y1 in zip(ys, ys[1:])]
                    grid_box = [xs[0], ys[0], xs[-1], ys[-1]]
                    for char in page.characters:
                        char_box = [char['x0'], char['top'], char['x1'], char['bottom']]
                        if overlap(char_box, grid_box) and not char['text'].isspace():
                            containing_column(char_box, cells)
                # Exact cropping can drop a boundary/cell in pdfplumber. Keep
                # already recognized complete grids if no settings change.
                replacement = affected if affected and region.settings is None else self.tables[region.tables].extract(
                    page.region(tuple(box)), {}, settings=region.settings)
                if not replacement:
                    raise ValueError('Región de tabla sin tabla detectable; requiere revisión, no fallback silencioso.')
                tokens = lambda group: Counter(word for t in group for row in t.grid
                                               for cell in row if cell for word in cell.split())
                if tokens(affected) - tokens(replacement):
                    raise ValueError('La redetección regional pierde texto de una tabla existente; requiere revisión.')
            tables = [t for t in tables if t not in affected] + replacement
        return sorted(tables, key=lambda t: (t.bbox[1], t.bbox[0]))


def trace_selection(document_id, number, selection):
    records = [{'kind': 'strategy_selection', 'document_id': document_id, 'pdf_page': number,
                'text': selection.text, 'tables': selection.tables, 'reason': selection.reason}]
    if selection.columns:
        records[0]['columns'] = list(selection.columns)
    for region in selection.regions:
        records.append({'kind': 'region_strategy', 'document_id': document_id, 'pdf_page': number,
                        'bbox': region.bbox, 'tables': region.tables, 'settings': region.settings, 'reason': region.reason})
    if selection.tables == 'text_only' or any(r.tables == 'text_only' for r in selection.regions):
        diagnostic = ExtractionDiagnostic(code='table_structure_disabled', severity='review',
            message='Se conserva texto nativo; la estructura de tablas se desactiva por perfil explícito.',
            document_id=document_id, pdf_page=number)
        records.append({'kind': 'diagnostic', **diagnostic.model_dump(exclude_none=True)})
    return records


DEFAULT_STRATEGIES = ExtractionStrategies()
