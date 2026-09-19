from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# Palette sobria para documentación técnica.
INK = colors.HexColor("#172033")
MUTED = colors.HexColor("#667085")
LINE = colors.HexColor("#D9DEE8")
SURFACE = colors.HexColor("#F6F8FB")
SURFACE_DARK = colors.HexColor("#E9EDF4")
ACCENT = colors.HexColor("#2F5BEA")
ACCENT_SOFT = colors.HexColor("#EAF0FF")
SUCCESS = colors.HexColor("#18794E")
SUCCESS_SOFT = colors.HexColor("#E8F5EE")
DANGER = colors.HexColor("#B42318")
DANGER_SOFT = colors.HexColor("#FDECEC")
WARNING = colors.HexColor("#A15C00")
WARNING_SOFT = colors.HexColor("#FFF4E5")
WHITE = colors.white
NOT_AVAILABLE = "No disponible"


@dataclass
class ReportCase:
    """Representa una ejecución registrada en el reporte."""

    case_id: str
    case_type: str
    input_text: str
    result: dict[str, Any]
    source: str = "prueba"
    expected: dict[str, Any] | None = None
    evaluation: dict[str, Any] | None = None
    multimodal: dict[str, Any] | None = None
    image_path: Path | None = None
    notes: str | None = None


class NumberedCanvas(Canvas):
    """Canvas de dos pasadas para numerar páginas como X de Y."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_pages: list[dict[str, Any]] = []

    def showPage(self) -> None:
        self._saved_pages.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        total_pages = len(self._saved_pages)

        for page_state in self._saved_pages:
            self.__dict__.update(page_state)
            self._draw_page_chrome(total_pages)
            super().showPage()

        super().save()

    def _draw_page_chrome(self, total_pages: int) -> None:
        width, height = A4
        page_number = self._pageNumber

        self.saveState()

        # Encabezado.
        top_y = height - 10 * mm
        self.setStrokeColor(LINE)
        self.setLineWidth(0.5)
        self.line(12 * mm, top_y - 3.5 * mm, width - 12 * mm, top_y - 3.5 * mm)

        self.setFillColor(INK)
        self.setFont("Helvetica-Bold", 8.5)
        self.drawString(12 * mm, top_y, "TI-support-RAG")

        header_label = "EVIDENCIA TÉCNICA · PARCIAL 1"
        self.setFillColor(MUTED)
        self.setFont("Helvetica-Bold", 7.5)
        header_width = stringWidth(header_label, "Helvetica-Bold", 7.5)
        self.drawString(width - 12 * mm - header_width, top_y, header_label)

        # Pie de página.
        bottom_y = 8 * mm
        self.setStrokeColor(LINE)
        self.line(12 * mm, bottom_y + 5 * mm, width - 12 * mm, bottom_y + 5 * mm)

        self.setFillColor(MUTED)
        self.setFont("Helvetica", 7.2)
        self.drawString(
            12 * mm,
            bottom_y,
            "Registro de ejecución y evidencia del sistema",
        )

        page_label = f"Página {page_number} de {total_pages}"
        page_width = stringWidth(page_label, "Helvetica-Bold", 7.2)
        self.setFont("Helvetica-Bold", 7.2)
        self.drawString(width - 12 * mm - page_width, bottom_y, page_label)

        self.restoreState()


class PDFReport:
    """Registra ejecuciones y genera un único PDF de evidencia."""

    def __init__(
        self,
        output_path: str | Path,
        *,
        title: str = "Evidencia de TI-support-RAG",
        subtitle: str = "Evaluación y ejecución del modelo",
    ) -> None:
        self.output_path = Path(output_path)
        self.title = title
        self.subtitle = subtitle
        self._cases: list[ReportCase] = []

    @property
    def cases(self) -> tuple[ReportCase, ...]:
        """Devuelve los casos registrados sin exponer la lista interna."""
        return tuple(self._cases)

    def register_case(
        self,
        *,
        case_id: str,
        case_type: str,
        input_text: str,
        result: dict[str, Any],
        source: str = "prueba",
        expected: dict[str, Any] | None = None,
        evaluation: dict[str, Any] | None = None,
        multimodal: dict[str, Any] | None = None,
        image_path: str | Path | None = None,
        notes: str | None = None,
    ) -> None:
        """Registra una ejecución sin ejecutar ni modificar el pipeline."""
        self._cases.append(
            ReportCase(
                case_id=str(case_id),
                case_type=str(case_type),
                input_text=str(input_text),
                result=result,
                source=str(source),
                expected=expected,
                evaluation=evaluation,
                multimodal=multimodal,
                image_path=Path(image_path) if image_path else None,
                notes=notes,
            )
        )

    def register_test_case(
        self,
        *,
        case: dict[str, Any],
        result: dict[str, Any],
        evaluation: dict[str, Any] | None = None,
    ) -> None:
        """Registra un caso de prueba definido por expectativas."""
        self.register_case(
            case_id=case["id"],
            case_type=case["tipo"],
            input_text=case["input"],
            result=result,
            source="prueba",
            expected=case.get("expected"),
            evaluation=evaluation,
            multimodal=result.get("multimodal"),
            image_path=result.get("image_path"),
        )

    def register_ocr_case(
        self,
        *,
        case_id: str,
        case_type: str,
        input_text: str,
        result: dict[str, Any],
        multimodal: dict[str, Any],
        image_path: str | Path | None = None,
        source: str = "ocr",
        evaluation: dict[str, Any] | None = None,
        notes: str | None = None,
    ) -> None:
        """Registra una ejecución con evidencia OCR/multimodal."""
        self.register_case(
            case_id=case_id,
            case_type=case_type,
            input_text=input_text,
            result=result,
            source=source,
            evaluation=evaluation,
            multimodal=multimodal,
            image_path=image_path,
            notes=notes,
        )

    def register_defense_case(
        self,
        *,
        case_id: str,
        input_text: str,
        result: dict[str, Any],
        multimodal: dict[str, Any] | None = None,
        image_path: str | Path | None = None,
        notes: str | None = None,
    ) -> None:
        """Registra una consulta ejecutada directamente durante la defensa."""
        self.register_case(
            case_id=case_id,
            case_type="defensa",
            input_text=input_text,
            result=result,
            source="defensa",
            multimodal=multimodal,
            image_path=image_path,
            notes=notes,
        )

    def clear(self) -> None:
        """Elimina los casos registrados en memoria."""
        self._cases.clear()

    @staticmethod
    def _safe_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value, ensure_ascii=False, indent=2)
        return str(value)

    @classmethod
    def _paragraph(cls, value: Any, style: ParagraphStyle) -> Paragraph:
        text = escape(cls._safe_text(value)).replace("\n", "<br/>")
        return Paragraph(text, style)

    @staticmethod
    def _styles() -> dict[str, ParagraphStyle]:
        base = getSampleStyleSheet()

        return {
            "title": ParagraphStyle(
                "report_title",
                parent=base["Title"],
                fontName="Helvetica-Bold",
                fontSize=21,
                leading=24,
                textColor=INK,
                alignment=TA_LEFT,
                spaceAfter=2 * mm,
            ),
            "subtitle": ParagraphStyle(
                "report_subtitle",
                parent=base["BodyText"],
                fontName="Helvetica",
                fontSize=10,
                leading=13,
                textColor=MUTED,
            ),
            "section": ParagraphStyle(
                "report_section",
                parent=base["Heading2"],
                fontName="Helvetica-Bold",
                fontSize=12,
                leading=15,
                textColor=INK,
                spaceBefore=1 * mm,
                spaceAfter=3 * mm,
            ),
            "case_title": ParagraphStyle(
                "report_case_title",
                parent=base["Heading2"],
                fontName="Helvetica-Bold",
                fontSize=14,
                leading=17,
                textColor=INK,
                spaceAfter=2 * mm,
            ),
            "body": ParagraphStyle(
                "report_body",
                parent=base["BodyText"],
                fontName="Helvetica",
                fontSize=9,
                leading=12,
                textColor=INK,
            ),
            "small": ParagraphStyle(
                "report_small",
                parent=base["BodyText"],
                fontName="Helvetica",
                fontSize=7.5,
                leading=9.5,
                textColor=MUTED,
            ),
            "label": ParagraphStyle(
                "report_label",
                parent=base["BodyText"],
                fontName="Helvetica-Bold",
                fontSize=7,
                leading=8.5,
                textColor=MUTED,
            ),
            "code": ParagraphStyle(
                "report_code",
                parent=base["Code"],
                fontName="Courier",
                fontSize=6.5,
                leading=8,
                textColor=INK,
                backColor=SURFACE,
                borderWidth=0.5,
                borderColor=LINE,
                borderPadding=5,
            ),
            "center_small": ParagraphStyle(
                "report_center_small",
                parent=base["BodyText"],
                fontName="Helvetica-Bold",
                fontSize=7.5,
                leading=9,
                textColor=MUTED,
                alignment=TA_CENTER,
            ),
            "metric_value": ParagraphStyle(
                "report_metric_value",
                parent=base["BodyText"],
                fontName="Helvetica-Bold",
                fontSize=14,
                leading=16,
                textColor=INK,
                alignment=TA_CENTER,
            ),
        }

    @staticmethod
    def _table(rows: list[list[Any]], widths: list[float]) -> Table:
        table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), SURFACE_DARK),
                    ("TEXTCOLOR", (0, 0), (-1, 0), INK),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return table

    @staticmethod
    def _status_style(status: str) -> tuple[Any, Any]:
        normalized = status.upper()
        if normalized == "CUMPLE":
            return SUCCESS, SUCCESS_SOFT
        if normalized == "NO CUMPLE":
            return DANGER, DANGER_SOFT
        return WARNING, WARNING_SOFT

    def _summary(self) -> dict[str, Any]:
        evaluations = [
            case.evaluation
            for case in self._cases
            if isinstance(case.evaluation, dict)
        ]

        evaluated = sum(int(item.get("evaluated", 0)) for item in evaluations)
        passed = sum(int(item.get("passed", 0)) for item in evaluations)
        failed = sum(int(item.get("failed", 0)) for item in evaluations)
        not_evaluable = sum(
            int(item.get("not_evaluable", 0)) for item in evaluations
        )

        return {
            "cases": len(self._cases),
            "ocr_cases": sum(
                1
                for case in self._cases
                if case.multimodal is not None or case.image_path is not None
            ),
            "defense_cases": sum(
                1 for case in self._cases if case.source == "defensa"
            ),
            "evaluated_cases": len(evaluations),
            "criteria_evaluated": evaluated,
            "passed": passed,
            "failed": failed,
            "not_evaluable": not_evaluable,
            "coverage": round(100 * passed / evaluated, 2) if evaluated else 0.0,
        }

    def _document_metadata(self) -> tuple[str, str]:
        model = NOT_AVAILABLE
        prompt_version = NOT_AVAILABLE

        for case in self._cases:
            model = str(case.result.get("model") or model)
            prompt_version = str(case.result.get("prompt_version") or prompt_version)
            if model != NOT_AVAILABLE and prompt_version != NOT_AVAILABLE:
                break

        return model, prompt_version

    def _cover(self, styles: dict[str, ParagraphStyle]) -> list[Any]:
        model, prompt_version = self._document_metadata()
        generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        summary = self._summary()

        title_block = Table(
            [
                [
                    Paragraph("TI-support-RAG", styles["label"]),
                    Paragraph("PARCIAL 1", styles["label"]),
                ],
                [
                    Paragraph(self.title, styles["title"]),
                    Paragraph("EVIDENCIA TÉCNICA", styles["section"]),
                ],
                [
                    Paragraph(self.subtitle, styles["subtitle"]),
                    Paragraph(
                        "Registro consolidado de pruebas, OCR y defensa.",
                        styles["small"],
                    ),
                ],
            ],
            colWidths=[105 * mm, 70 * mm],
        )
        title_block.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), WHITE),
                    ("BOX", (0, 0), (-1, -1), 0.8, LINE),
                    ("INNERGRID", (0, 0), (-1, -1), 0, WHITE),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ]
            )
        )

        meta = self._table(
            [
                ["Modelo", model, "Prompt", prompt_version],
                ["Generado", generated, "Ejecuciones", str(summary["cases"])],
            ],
            [23 * mm, 63 * mm, 23 * mm, 66 * mm],
        )

        cards = self._metric_cards(styles, summary)

        return [
            Spacer(1, 6 * mm),
            title_block,
            Spacer(1, 7 * mm),
            meta,
            Spacer(1, 8 * mm),
            Paragraph("Resumen ejecutivo", styles["section"]),
            cards,
            Spacer(1, 7 * mm),
            Paragraph(
                "Este documento consolida la evidencia generada por el sistema durante las pruebas funcionales, las ejecuciones con OCR y las consultas realizadas directamente durante la defensa.",
                styles["body"],
            ),
            Spacer(1, 6 * mm),
            Paragraph("Registro general", styles["section"]),
            self._registry_section(styles)[0],
        ]

    def _metric_cards(
        self,
        styles: dict[str, ParagraphStyle],
        summary: dict[str, Any],
    ) -> Table:
        values = [
            (str(summary["cases"]), "CASOS"),
            (str(summary["ocr_cases"]), "OCR"),
            (str(summary["defense_cases"]), "DEFENSA"),
            (f"{summary['coverage']:.2f}%", "COBERTURA"),
        ]

        cells = []
        for value, label in values:
            cells.append(
                [
                    Paragraph(value, styles["metric_value"]),
                    Spacer(1, 1 * mm),
                    Paragraph(label, styles["center_small"]),
                ]
            )

        table = Table([cells], colWidths=[43.5 * mm] * 4, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), SURFACE),
                    ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        return table

    def _registry_section(self, styles: dict[str, ParagraphStyle]) -> list[Any]:
        rows = [["Caso", "Tipo", "Fuente", "OCR", "Evaluación"]]
        occurrence: dict[tuple[str, str], int] = {}

        for case in self._cases:
            key = (case.case_id, case.source)
            occurrence[key] = occurrence.get(key, 0) + 1
            run_number = occurrence[key]

            case_label = case.case_id
            if case.source == "defensa" or run_number > 1:
                case_label = f"{case.case_id} · ejecución {run_number}"

            evaluated = (
                "Sí"
                if isinstance(case.evaluation, dict)
                and case.evaluation.get("evaluated", 0) > 0
                else "No"
            )
            has_ocr = "Sí" if (
                case.multimodal is not None or case.image_path is not None
            ) else "No"

            rows.append(
                [
                    self._paragraph(case_label, styles["small"]),
                    self._paragraph(case.case_type, styles["small"]),
                    self._paragraph(case.source, styles["small"]),
                    has_ocr,
                    evaluated,
                ]
            )

        return [
            self._table(rows, [45 * mm, 32 * mm, 28 * mm, 18 * mm, 25 * mm]),
            Spacer(1, 4 * mm),
        ]

    def _metrics_section(self, result: dict[str, Any]) -> Table:
        usage = result.get("usage") or {}
        metrics = result.get("metrics") or {}
        http = result.get("http") or {}

        rows = [
            ["Métrica", "Valor", "Métrica", "Valor"],
            ["Estado", self._safe_text(result.get("state")), "HTTP", self._safe_text(http.get("status_code"))],
            ["Latencia (s)", self._safe_text(result.get("latency_seconds")), "Servidor (s)", self._safe_text(metrics.get("total_time"))],
            ["Prompt tokens", self._safe_text(usage.get("prompt_tokens")), "Completion tokens", self._safe_text(usage.get("completion_tokens"))],
            ["Total tokens", self._safe_text(usage.get("total_tokens")), "Modelo", self._safe_text(result.get("model"))],
            ["Fuente", self._safe_text(result.get("source")), "", ""],
        ]

        return self._table(rows, [35 * mm, 52.5 * mm, 35 * mm, 52.5 * mm])

    def _ocr_section(
        self,
        case: ReportCase,
        styles: dict[str, ParagraphStyle],
    ) -> list[Any]:
        if case.multimodal is None and case.image_path is None:
            return []

        extraction = {}
        if isinstance(case.multimodal, dict):
            extraction = case.multimodal.get("extraction") or {}

        text = extraction.get("text")
        if not text and isinstance(case.multimodal, dict):
            text = case.multimodal.get("extracted_text")

        metadata_rows = [
            ["Campo", "Valor"],
            ["Motor OCR", self._safe_text(extraction.get("engine"))],
            ["Idioma", self._safe_text(extraction.get("language"))],
            ["Palabras", self._safe_text(extraction.get("word_count"))],
            ["Confianza OCR", self._safe_text(extraction.get("ocr_confidence"))],
            ["Con texto", self._safe_text(extraction.get("has_text"))],
        ]

        story: list[Any] = [
            Paragraph("Evidencia OCR / multimodal", styles["section"]),
            self._table(metadata_rows, [55 * mm, 80 * mm]),
            Spacer(1, 3 * mm),
            Paragraph("Texto extraído", styles["label"]),
            self._paragraph(text, styles["code"]),
        ]

        image_path = case.image_path
        if image_path and image_path.exists():
            try:
                image = Image(str(image_path))
                image._restrictSize(165 * mm, 76 * mm)
                story.extend(
                    [
                        Spacer(1, 3 * mm),
                        Paragraph("Imagen de evidencia", styles["label"]),
                        image,
                    ]
                )
            except OSError:
                story.append(
                    Paragraph(
                        "No se pudo incrustar la imagen de evidencia.",
                        styles["small"],
                    )
                )

        return story

    def _result_section(
        self,
        result: dict[str, Any],
        styles: dict[str, ParagraphStyle],
    ) -> list[Any]:
        story: list[Any] = [
            Paragraph("Contenido enviado al modelo", styles["section"]),
            self._paragraph(result.get("user_content_sent"), styles["code"]),
            Spacer(1, 4 * mm),
            Paragraph("Salida del modelo", styles["section"]),
        ]

        validated = result.get("validated_output")
        raw_output = result.get("raw_output")

        if validated:
            story.append(self._paragraph(validated, styles["code"]))
        elif raw_output:
            story.append(self._paragraph(raw_output, styles["code"]))
        else:
            story.append(
                Paragraph(
                    "No se obtuvo una salida estructurada.",
                    styles["body"],
                )
            )

        execution_error = result.get("execution_error")
        if execution_error:
            story.extend(
                [
                    Spacer(1, 4 * mm),
                    Paragraph("Error de ejecución", styles["section"]),
                    self._paragraph(execution_error, styles["body"]),
                ]
            )

        story.extend(
            [
                Spacer(1, 4 * mm),
                Paragraph("Métricas de ejecución", styles["section"]),
                self._metrics_section(result),
            ]
        )

        return story

    def _evaluation_section(
        self,
        case: ReportCase,
        styles: dict[str, ParagraphStyle],
    ) -> list[Any]:
        if not case.evaluation:
            return [
                Paragraph("Evaluación", styles["section"]),
                Paragraph(
                    "Caso registrado sin evaluación automática. La entrada, respuesta y métricas quedan como evidencia de ejecución.",
                    styles["body"],
                ),
            ]

        evaluation = case.evaluation
        rows = [["Criterio", "Resultado", "Observado"]]

        for check in evaluation.get("checks", []):
            observed = self._safe_text(check.get("observed"))
            if len(observed) > 450:
                observed = observed[:450] + "..."

            rows.append(
                [
                    self._paragraph(check.get("criterion"), styles["small"]),
                    self._paragraph(check.get("status"), styles["small"]),
                    self._paragraph(observed, styles["small"]),
                ]
            )

        table = self._table(rows, [60 * mm, 32 * mm, 85 * mm])

        for index, check in enumerate(evaluation.get("checks", []), start=1):
            foreground, background = self._status_style(
                self._safe_text(check.get("status"))
            )
            table.setStyle(
                TableStyle(
                    [
                        ("TEXTCOLOR", (1, index), (1, index), foreground),
                        ("BACKGROUND", (1, index), (1, index), background),
                        ("FONTNAME", (1, index), (1, index), "Helvetica-Bold"),
                    ]
                )
            )

        return [
            Paragraph(
                f"Evaluación · cobertura {evaluation.get('coverage', 0.0):.2f}%",
                styles["section"],
            ),
            table,
        ]

    def _case_section(
        self,
        case: ReportCase,
        styles: dict[str, ParagraphStyle],
        run_number: int,
        total_runs_for_id: int,
    ) -> list[Any]:
        title = f"{case.case_id} - {case.case_type}"
        if total_runs_for_id > 1 or case.source == "defensa":
            title += f" · ejecución {run_number}"

        source_table = self._table(
            [
                ["Campo", "Valor"],
                ["Fuente", case.source],
                ["Tipo", case.case_type],
                ["Entrada", self._safe_text(case.input_text)],
            ],
            [35 * mm, 140 * mm],
        )

        story: list[Any] = [
            Paragraph(title, styles["case_title"]),
            source_table,
            Spacer(1, 3 * mm),
        ]

        if case.notes:
            note = Table(
                [[self._paragraph(case.notes, styles["body"])]],
                colWidths=[175 * mm],
            )
            note.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), ACCENT_SOFT),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#BFCBFF")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ]
                )
            )
            story.extend([note, Spacer(1, 4 * mm)])

        if case.expected is not None:
            story.extend(
                [
                    Paragraph("Expectativas del caso", styles["section"]),
                    self._paragraph(case.expected, styles["code"]),
                    Spacer(1, 4 * mm),
                ]
            )

        story.extend(self._ocr_section(case, styles))
        story.append(Spacer(1, 4 * mm))
        story.extend(self._result_section(case.result, styles))
        story.append(Spacer(1, 5 * mm))
        story.extend(self._evaluation_section(case, styles))

        return story

    def generate(self) -> Path:
        """Genera el PDF con todos los casos registrados."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        styles = self._styles()
        document = SimpleDocTemplate(
            str(self.output_path),
            pagesize=A4,
            rightMargin=12 * mm,
            leftMargin=12 * mm,
            topMargin=18 * mm,
            bottomMargin=16 * mm,
            title=self.title,
            author="TI-support-RAG",
        )

        story: list[Any] = []
        story.extend(self._cover(styles))

        if self._cases:
            story.append(PageBreak())

        occurrence: dict[tuple[str, str], int] = {}
        totals: dict[str, int] = {}
        for case in self._cases:
            totals[case.case_id] = totals.get(case.case_id, 0) + 1

        for index, case in enumerate(self._cases):
            key = (case.case_id, case.source)
            occurrence[key] = occurrence.get(key, 0) + 1
            story.extend(
                self._case_section(
                    case,
                    styles,
                    occurrence[key],
                    totals[case.case_id],
                )
            )

            if index < len(self._cases) - 1:
                story.append(PageBreak())

        document.build(story, canvasmaker=NumberedCanvas)
        return self.output_path


__all__ = [
    "PDFReport",
    "ReportCase",
]
