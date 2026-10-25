from __future__ import annotations

import json
from dataclasses import dataclass
from functools import partial
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

    def __init__(self, *args: Any, header_label: str = "EVIDENCIA TÉCNICA · PARCIAL 1", **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.header_label = header_label
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

        header_label = self.header_label
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
            text = json.dumps(value, ensure_ascii=False, indent=2)
        else:
            text = str(value)
        # Standard PDF fonts lack several Unicode hyphen glyphs. This changes
        # presentation only; original JSON evidence retains its exact text.
        return text.translate(dict.fromkeys(range(0x2010, 0x2016), '-'))

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
                    Paragraph("RAG DOCUMENTAL · PARCIAL 2" if any(c.result.get("rag") for c in self._cases) else "PARCIAL 1", styles["label"]),
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
        if result.get("rag"):
            story.extend([
                Paragraph("Respuesta documental RAG", styles["section"]),
                self._paragraph(result.get("documentary_output") or "Sin respuesta documental aceptada.", styles["code"]),
                Paragraph("Fuentes y revisión de respaldo", styles["section"]),
                self._paragraph({"catalog": result["rag"].get("catalog"),
                                 "citations_valid": result["rag"].get("citations_valid"),
                                 "semantic_support_review": result["rag"].get("semantic_support_review"),
                                 "omitted": result["rag"].get("omitted"),
                                 "timings": result["rag"].get("timings")}, styles["code"]),
            ])
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

    def generate_timing_comparison(self, report: dict[str, Any], *, source_json: str | Path | None = None) -> Path:
        """Descriptive time matrix, using the same tables/styles/page chrome."""
        from hashlib import sha256
        if report.get("schema_version") != "timing-comparison-v1":
            raise ValueError("No es una matriz de comparación de tiempos compatible.")
        styles=self._styles()
        p=lambda text, small=False: self._paragraph(text, styles["small" if small else "body"])
        h=lambda text: self._paragraph(text,styles["section"])
        def ms(value):
            return "N/E" if value is None else f"{value*1000:.3f}".replace(".",",")
        def pct(value):
            return "N/E" if value is None else f"{value:.2f}%".replace(".",",")
        def table(rows,widths):
            return self._table([[p(c,True) for c in row] for row in rows],[w*mm for w in widths])
        names=("A_semantic","B_hybrid_rrf")
        all_group=report["groups"]["all"]
        variants=all_group["variants"]
        story=[self._paragraph("Comparación de tiempos",styles["title"]),
               self._paragraph("Recuperación semántica frente a híbrida BM25 + RRF",styles["subtitle"]),
               Spacer(1,4*mm),p("OBSERVACIONES DE DESARROLLO - " + ("COMPLETA" if report["status"]=="complete" else "INCOMPLETA")),
               Spacer(1,3*mm)]
        story.append(table([["Dato","Observación"],
            ["Medición original UTC",report["measurement_timestamp_utc"]],
            ["Origen / corpus",report["backend"] + " / " + report["corpus_id"]],
            ["Casos previstos / registrados",f"{report.get('source_planned_cases','N/D')} / {report.get('source_recorded_cases','N/D')}"],
            ["Muestra",f"{all_group['recorded_pairs']} pares registrados; {all_group['valid_pairs']} válidos; {all_group['excluded_pairs']} excluidos"],
            ["Unidad de presentación","Milisegundos (ms). JSON y CSV conservan segundos."],
            ["Diseño","Una observación por pregunta; embedding y búsqueda semántica compartidos entre A y B."]],[35,151]))
        story += [Spacer(1,4*mm),h("1. Tiempo total de recuperación")]
        rows=[["Estadístico (ms)","A: Semántica","B: Híbrida"]]
        for label,key in (("Media","mean"),("Mediana","median"),("Percentil 95 (*)","p95"),("Mínimo","min"),("Máximo","max")):
            rows.append([label,*[ms(variants[name]["total_seconds"][key]) for name in names]])
        story.append(table(rows,[80,53,53]))
        delta=all_group["paired_difference_seconds"];relative=all_group["paired_relative_change_percent"]
        story += [Spacer(1,3*mm),p("Coste incremental B - A: mediana " + ms(delta["median"]) + " ms; cambio relativo mediano por par " + pct(relative["median"]) + ".",True),
                  p("El cambio relativo es (B - A) / A por caso. No equivale al cociente de las medianas. Los pares con A=0 quedan fuera del porcentaje, conservando su diferencia absoluta.",True),
                  Spacer(1,4*mm),h("2. Mediana por etapa (ms)")]
        labels={"embedding_seconds":"Embedding de pregunta (compartido)","semantic_search_seconds":"Búsqueda semántica/RPC (compartida)",
                "lexical_fetch_seconds":"Lectura del corpus léxico","bm25_seconds":"Tokenización y cálculo BM25",
                "rrf_seconds":"Fusión RRF y selección","candidate_scoring_seconds":"Puntuación de candidatos adicionales",
                "coordination_seconds":"Resto de coordinación (derivado)"}
        stages=[["Etapa","A","B"]]
        for key,label in labels.items():
            stages.append([label,*[ms(variants[name]["stage_seconds"][key]["median"]) for name in names]])
        story.append(table(stages,[100,43,43]))
        story += [Spacer(1,3*mm),p("N/E: etapa que no aplica o no tiene observaciones válidas. No es cero. Las medianas y percentiles de etapas no se suman para obtener la mediana o percentil del total.",True),
                  p("(*) P95: interpolación lineal en (n - 1) x 0,95. Es una descripción de una muestra pequeña, no una garantía de latencia ni un intervalo de confianza.",True),
                  PageBreak(),h("3. Comparación por pregunta")]
        rows=[["Caso / grupo","A (ms)","B (ms)","B - A (ms)","Cambio relativo"]]
        for case in report["cases"]:
            valid=case["status"]=="valid"
            row=[case["id"] + " / " + ("documental" if case["group"]=="documentary" else "comportamiento")]
            row += [ms(case["variants"][name]["total_seconds"]) if valid else "ERROR" for name in names]
            row += [ms(case["difference_seconds"]),pct(case["relative_change_percent"])]
            rows.append(row)
        story.append(table(rows,[50,32,32,35,37]))
        story += [Spacer(1,4*mm),h("4. Grupos comparables")]
        rows=[["Grupo","Pares válidos","Mediana A (ms)","Mediana B (ms)","Mediana B - A (ms)"]]
        for key,label in (("all","Todos"),("documentary","Documentales"),("behavior","Comportamiento")):
            group=report["groups"][key]
            rows.append([label,str(group["valid_pairs"]),*[ms(group["variants"][name]["total_seconds"]["median"]) for name in names],ms(group["paired_difference_seconds"]["median"])])
        story.append(table(rows,[42,27,38,38,41]))
        story += [Spacer(1,4*mm),h("Cómo interpretar la comparación"),
                  p("Los casos de comportamiento se incluyen para medir trabajo computacional, aunque no tengan métricas documentales. El grupo documental permite comparar los mismos casos que la matriz de calidad."),
                  p("A = embedding + búsqueda semántica. B = embedding + subtotal híbrido. El subtotal híbrido incluye búsqueda semántica, lectura léxica, BM25, RRF, puntuación y coordinación. No se suma otra vez con sus subetapas."),
                  p("Ambas alternativas comparten componentes medidos. B - A describe el trabajo adicional en estas observaciones; no es el resultado de dos servicios HTTP independientes. Carga de modelos, autenticación y calentamiento quedan fuera del intervalo original."),
                  p("La rapidez no acredita calidad de recuperación. La configuración elegida requiere contrastar evidencias, fallos, revisión humana y una reserva independiente."),
                  PageBreak(),h("5. Preguntas y procedencia")]
        rows=[["Caso","Pregunta de la medición original"]]
        rows += [[case["id"],case["question"]] for case in report["cases"]]
        story.append(table(rows,[15,171]))
        story += [Spacer(1,4*mm),h("Integridad y límites")]
        source=report.get("source",{})
        story += [p("Mediciones: " + source.get("filename","No disponible"),True),
                  p("SHA-256 de las mediciones: " + source.get("sha256","No disponible"),True)]
        if source_json is not None:
            source_path=Path(source_json)
            story += [p("Matriz de tiempos: " + source_path.name,True),p("SHA-256: " + sha256(source_path.read_bytes()).hexdigest(),True)]
        story += [Spacer(1,2*mm),p("La comparación se calcula desde el JSON guardado, sin llamadas nuevas a proveedores. Se conservan fallos y datos inválidos; se excluye el par completo de los agregados. Las celdas ausentes permanecen vacías en CSV.",True),
                  p("Una observación por pregunta conocida de desarrollo. No se midió una distribución de ejecuciones repetidas ni una muestra independiente de producción.",True)]
        self.output_path.parent.mkdir(parents=True,exist_ok=True)
        doc=SimpleDocTemplate(str(self.output_path),pagesize=A4,leftMargin=12*mm,rightMargin=12*mm,
            topMargin=20*mm,bottomMargin=17*mm,title="Comparación de tiempos RAG",author="TI-support-RAG")
        doc.build(story,canvasmaker=partial(NumberedCanvas,header_label="TIEMPOS RAG - DESARROLLO"))
        return self.output_path

    def generate_token_comparison(self, report, *, source_json=None):
        """Actual generation usage, paired populations and incomplete checkpoints."""
        if report.get('schema_version')!='generation-token-comparison-v1':
            raise ValueError('No es una comparación de tokens compatible.')
        from hashlib import sha256
        styles=self._styles()
        p=lambda value,small=False:self._paragraph(value,styles['small' if small else 'body'])
        h=lambda value:self._paragraph(value,styles['section'])
        table=lambda rows,widths:self._table([[p(c,True) for c in row] for row in rows],[w*mm for w in widths])
        names={'A_semantic':'A: Semántica','B_hybrid_rrf':'B: Híbrida v2'}
        variants=list(names);summary=report['summary'];protocol=report['protocol']
        number=lambda value:'N/E' if value is None else f'{value:,.2f}'.replace(',','_').replace('.',',').replace('_','.')
        status='MEDICIÓN COMPLETA' if report['status']=='complete' else 'MEDICIÓN INCOMPLETA'
        story=[self._paragraph('Consumo de tokens',styles['title']),
            self._paragraph('Generación comparable: semántica frente a híbrida',styles['subtitle']),
            Spacer(1,4*mm),p(status+' | Desarrollo | Revisión humana pendiente'),Spacer(1,3*mm),
            table([['Dato','Condición'],['Modelo',protocol['model']],
                ['Prompt / parámetros',f"{protocol['prompt_version']} / temperatura 0 / reasoning low / salida máxima 800 tokens"],
                ['Muestra',f"{len(report['cases'])} preguntas documentales; dos variantes; {summary['paired_measured_cases']} pares con usage válido"],
                ['Alcance','Generación directa únicamente; excluye clasificación, revisión y corrección. Reserva sin ejecutar.']], [37,149]),
            Spacer(1,4*mm),h('1. Tokens informados por Groq')]
        rows=[['Medida',names[variants[0]],names[variants[1]],'Diferencia B-A']]
        for key,label in [('prompt_tokens','Entrada: media'),('completion_tokens','Salida: media'),('total_tokens','Total: media')]:
            rows.append([label,*[number(summary['variants'][v]['paired_usage'][key]['mean']) for v in variants],number(summary['paired_difference'][key]['mean'])])
        for key,label in [('prompt_tokens','Entrada: suma emparejada'),('completion_tokens','Salida: suma emparejada'),('total_tokens','Total: suma emparejada')]:
            rows.append([label,*[number(summary['variants'][v]['paired_usage'][key]['sum']) for v in variants],number(summary['paired_difference'][key]['sum'])])
        story += [table(rows,[67,40,40,39]),Spacer(1,3*mm),
            p('Usage real del proveedor; no son estimaciones del tokenizer. Salida puede incluir razonamiento interno. Menos tokens no acredita mayor fidelidad o utilidad. No se calcula costo monetario.',True),
            Spacer(1,4*mm),h('2. Integridad de la medición')]
        rows=[['Registro',*[names[v] for v in variants]]]
        for key,label in [('observations','Observaciones, incluidos reintentos explícitos'),('http_responses','Respuestas HTTP recibidas'),
                          ('observations_without_valid_usage','Observaciones sin usage válido'),('contract_valid_outputs','Salidas con contrato y citas válidos')]:
            rows.append([label,*[str(summary['variants'][v][key]) for v in variants]])
        story += [table(rows,[100,43,43]),Spacer(1,3*mm),
            p('La comparación utiliza exactamente los mismos casos con usage válido en ambas variantes. Un error o usage ausente no se convierte en cero. El JSON conserva todas las observaciones; su contabilidad global incluye tokens conocidos aunque la salida no cumpla el contrato.',True),
            PageBreak(),h('3. Registro por pregunta y variante')]
        rows=[['Caso','Variante','Entrada','Salida','Total','Contrato / estado']]
        for case in report['cases']:
            for name in variants:
                observations=case['variants'][name]['observations']
                for o in observations or [None]:
                    usage=(o.get('usage') or {}) if o else {}
                    rows.append([case['id'],names[name],*[str(usage.get(k)) if usage.get(k) is not None else 'N/E' for k in ('prompt_tokens','completion_tokens','total_tokens')],o['status'] if o else 'not_run'])
        story += [table(rows,[15,35,24,24,24,64]),Spacer(1,4*mm),
            p('contract_valid solo comprueba JSON, contrato y coherencia de etiquetas con el catálogo. No prueba respaldo semántico, corrección, conservación de condiciones ni utilidad. Las respuestas y contextos quedan en JSON para la siguiente revisión humana.'),
            PageBreak(),h('4. Preguntas y protocolo')]
        story.append(table([['Caso','Pregunta']]+[[c['id'],c['question']] for c in report['cases']],[15,171]))
        story += [Spacer(1,4*mm),p('Mismo modelo, prompt, esquema, temperatura, límite de salida y presupuesto de contexto para ambas estrategias. A usa los Top-10 semánticos guardados; ambas aplican la política de pertinencia antes de Top-3. B usa la selección híbrida mejorada. No se alimentan categorías esperadas al generador.'),
            p('Orden alternado A/B y B/A entre preguntas. Una observación por combinación; no acredita estabilidad estadística ni generalización. Son preguntas conocidas de desarrollo, con anotaciones pendientes de revisión humana.'),
            p('La estimación local de entrada se conserva separada del usage real. Sin clasificación, revisor ni corrección, esta medición no equivale al consumo total de la API query. Los reintentos explícitos permanecen en el historial; uso desconocido permanece desconocido.'),
            Spacer(1,3*mm),h('Trazabilidad'),p('Creación UTC: '+report['created_at_utc'],True),
            p('SHA-256 fuente de recuperación: '+report['source_sha256'],True),
            p('SHA-256 prompt: '+protocol['prompt_sha256'],True)]
        if source_json:
            source=Path(source_json)
            story += [p('JSON: '+source.name,True),p('SHA-256 JSON: '+sha256(source.read_bytes()).hexdigest(),True)]
        self.output_path.parent.mkdir(parents=True,exist_ok=True)
        document=SimpleDocTemplate(str(self.output_path),pagesize=A4,leftMargin=12*mm,rightMargin=12*mm,
            topMargin=20*mm,bottomMargin=17*mm,title='Consumo de tokens: comparación generativa',author='TI-support-RAG')
        document.build(story,canvasmaker=partial(NumberedCanvas,header_label='TOKENS REALES - DESARROLLO'))
        return self.output_path

    def generate_retrieval_metrics(self, report: dict[str, Any], *, source_json: str | Path | None = None) -> Path:
        """Render the annotated A/B retrieval matrix with the existing PDF engine.

        Reads saved observations only: no provider calls, rescoring or changes to
        the source JSON. Missing/error measurements are never converted to zero.
        """
        if not report.get("aggregate") or "cases" not in report:
            raise ValueError("El reporte no contiene una matriz de recuperación.")
        from hashlib import sha256

        styles = self._styles()
        p = lambda value, small=False: self._paragraph(value, styles["small" if small else "body"])
        heading = lambda value: self._paragraph(value, styles["section"])
        variants = list(report["aggregate"])
        names = {"A_semantic": "A: Semántica", "B_hybrid_rrf": "B: Híbrida BM25 + RRF"}
        def number(value, *, percent=False, digits=4):
            if value is None:
                return "N/E"
            return ((f"{value * 100:.2f}%") if percent else f"{value:.{digits}f}").replace(".", ",")
        def table(rows, widths, *, small=True):
            return self._table([[p(cell, small) for cell in row] for row in rows], [w * mm for w in widths])
        case_rows = report["cases"]
        paired = [row for row in case_rows if row.get("retrieval_evaluable") and not row.get("error")]
        errors = sum(bool(row.get("error")) for row in case_rows)
        annotation = report.get("annotation_validation", {})
        review = "Revisión humana pendiente" if not annotation.get("human_review_completed") else "Revisión humana registrada"
        status = "INCOMPLETO: hay errores técnicos" if errors or report.get("status") != "complete" else "EJECUCIÓN COMPLETA"
        story = [self._paragraph("Evaluación de recuperación", styles["title"]),
                 self._paragraph("Matriz comparativa de métricas RAG", styles["subtitle"]), Spacer(1, 5 * mm),
                 p(status + " | Desarrollo | " + review), Spacer(1, 3 * mm)]
        story.append(table([
            ["Dato", "Observación"],
            ["Ejecución UTC", report.get("timestamp_utc", "No disponible")],
            ["Origen / corpus", f"{report.get('backend', 'No disponible')} / {report.get('corpus_id', 'No disponible')}"],
            ["Casos", f"{report.get('planned_cases', len(case_rows))} previstos; {len(case_rows)} registrados; {len(paired)} documentales válidos emparejados"],
            ["Exclusiones", f"{sum(not r.get('retrieval_evaluable') for r in case_rows)} de comportamiento; {errors} errores técnicos"],
        ], [36, 150]))
        story += [Spacer(1, 4 * mm), heading("1. Matriz agregada")]
        metric_rows = [["Métrica", *[names.get(v, v) for v in variants]]]
        for label, key, percent in [("Precision@3", "precision", True), ("Recall@3", "recall", True),
                                    ("Hit@3", "hit", True), ("MRR@3", "rr", False),
                                    ("Cobertura de información Top-3", "coverage", True)]:
            metric_rows.append([label, *[number(report["aggregate"][v]["metrics_at_3"].get(key), percent=percent) for v in variants]])
        for label, key, percent in [("Cobertura del contexto tras presupuesto", "context_coverage_mean", True),
                                    ("Cobertura de candidatos (*)", "candidate_coverage_mean", True),
                                    ("Mediana de recuperación observada (s)", "retrieval_seconds_median", False)]:
            metric_rows.append([label, *[number(report["aggregate"][v].get(key), percent=percent) for v in variants]])
        widths = [90] + [96 / len(variants)] * len(variants)
        story.append(table(metric_rows, widths))
        replay = report.get("backend") == "offline_replay"
        story += [Spacer(1, 3 * mm), p("Promedios macro: cada pregunta documental válida tiene el mismo peso. MRR es el promedio del inverso del primer rango relevante; no es una confianza del modelo.", True),
                  Spacer(1, 2 * mm), p("(*) Cobertura de candidatos no reevaluada. Antes/después reutiliza rankings semánticos guardados y recalcula léxico/contexto. No mide latencia ni respuestas generadas." if replay else "(*) A mide hasta diez candidatos semánticos; B mide la unión completa, hasta veinte. Los conjuntos candidatos tienen tamaños distintos.", True)]
        if paired:
            unit_count = sum(row.get("units_count", 0) for row in paired)
            if unit_count:
                values=[]
                for name in variants:
                    covered=sum(round(row["variants"][name]["metrics_at_3"]["coverage"] * row.get("units_count", 0)) for row in paired)
                    values.append(f"{names.get(name, name)}: {covered}/{unit_count} ({number(covered / unit_count, percent=True)})")
                story += [Spacer(1, 3 * mm), p("Cobertura ponderada por unidades: " + "; ".join(values) + ". Puede empatar aunque cambie el promedio macro.", True)]
        story += [Spacer(1, 4 * mm), heading("Alcance de esta evaluación"),
                  p("Casos conocidos de desarrollo, sin reserva independiente. Las anotaciones del agente requieren revisión humana. La métrica de recuperación no acredita la calidad de respuestas generadas. Los casos de comportamiento quedan fuera del denominador documental."),
                  PageBreak(), heading("2. Matriz por caso")]
        labels = [names.get(v, v).split(":")[0] for v in variants]
        story += [p("Cada celda sigue el orden " + " / ".join(labels) + ". P y R: precisión y recall. RR: rango recíproco. Cobertura: unidades necesarias presentes. N/E significa no evaluable, nunca cero."), Spacer(1, 4 * mm)]
        matrix = [["Caso", "P@3", "R@3", "RR@3", "Cobertura Top-3", "Cobertura contexto"]]
        for row in case_rows:
            cells=[row["id"] + (" / ERROR" if row.get("error") else "")]
            for key in ("precision", "recall", "rr", "coverage", "context"):
                values=[]
                for name in variants:
                    v=row.get("variants", {}).get(name, {})
                    value=v.get("context_coverage") if key=="context" else v.get("metrics_at_3", {}).get(key)
                    values.append("ERROR" if row.get("error") else number(value, percent=key in ("coverage", "context"), digits=3))
                cells.append(" / ".join(values))
            matrix.append(cells)
        story.append(table(matrix, [14, 30, 30, 30, 41, 41]))
        story += [Spacer(1, 4 * mm), heading("Lectura de resultados")]
        if len(variants)==2:
            a,b=variants
            for row in paired:
                av,bv=(row["variants"][v]["metrics_at_3"] for v in (a,b))
                changes=[]
                for label,key in (("Recall", "recall"), ("cobertura", "coverage")):
                    if av[key]!=bv[key]:
                        changes.append(f"{label}: {number(av[key], percent=True)} a {number(bv[key], percent=True)}")
                if changes:
                    story.append(p(row["id"] + ": " + "; ".join(changes) + ".", True))
                if all(row["variants"][v]["metrics_at_3"]["hit"]==0 for v in variants):
                    story.append(p(row["id"] + ": ninguna alternativa seleccionó evidencia pertinente en Top-3.", True))
        story += [Spacer(1, 4 * mm), heading("3. Condiciones y tiempos"),
                  p(f"K={report.get('protocol', {}).get('k', 'N/D')}; profundidad semántica/léxica={report.get('protocol', {}).get('search_depth_per_branch', 'N/D')}; constante RRF={report.get('protocol', {}).get('rrf_constant', 'N/D')}. Ajuste por categoría: {'activado' if report.get('protocol', {}).get('category_boost') else 'desactivado'}."),
                  p("No se comparan latencias: se reutilizan los Top-10 semánticos históricos y se recalculan el ranking léxico y los contextos localmente. Parámetros ajustados con desarrollo conocido; no es una verificación independiente. Tokens de entrada son estimaciones locales, sin generación." if replay else "Los tiempos son observaciones emparejadas de componentes compartidos. Excluyen inicialización y autenticación previas; no son un benchmark de latencia HTTP. Se conserva la duración de fallos, pero no se les asigna calidad cero."),
                  p(f"Contexto: límite de entrada {report.get('protocol', {}).get('context_budget_input_tokens', 'N/D')} tokens; clasificación y filtros según el protocolo del JSON. Groq: {report.get('groq_calls', 'N/D')} llamadas; escrituras Supabase: {report.get('supabase_writes', 'N/D')}.", True),
                  PageBreak(), heading("4. Preguntas y trazabilidad")]
        questions = [["Caso / uso", "Pregunta evaluada"]]
        for row in case_rows:
            usage = "Documental" if row.get("retrieval_evaluable") else "Comportamiento"
            questions.append([row["id"] + " / " + usage, row.get("question", "No disponible")])
        story.append(table(questions, [32, 154]))
        story += [Spacer(1, 5 * mm), heading("Fuentes del informe"),
                  p("Las anotaciones enlazan unidades de información con IDs, citas literales, páginas y archivos del corpus. El JSON de esta ejecución conserva catálogo, rankings, contribuciones RRF, contexto, omisiones, parámetros y tiempos. El CSV permite revisar la matriz sin redondear.", True)]
        if source_json is not None:
            source = Path(source_json)
            story += [Spacer(1, 2 * mm), p("JSON de origen: " + source.name, True),
                      p("SHA-256: " + sha256(source.read_bytes()).hexdigest(), True)]
        story += [Spacer(1, 2 * mm), p("PDF generado a partir de observaciones guardadas. No recalcula búsquedas ni modifica la matriz; no declara una configuración ganadora ni completa revisión humana pendiente.", True)]
        if any("coverage_completeness" in value for value in report["aggregate"].values()):
            story += [PageBreak(), heading("5. Cobertura completa por pregunta"),
                      p("Completa: todas las unidades necesarias tienen evidencia en la etapa. Incompleta: falta al menos una. N/E: caso de comportamiento o sin medición; ERROR: fallo técnico. No equivale a exactitud de la respuesta generada."), Spacer(1, 3*mm)]
            summary = [["Variante / etapa", "Completas", "Incompletas", "Evaluadas", "Proporción"]]
            for name in variants:
                for stage, label in (("top_3", "Top-3"), ("context", "Contexto")):
                    value = report["aggregate"][name].get("coverage_completeness", {}).get(stage, {})
                    summary.append([names.get(name, name)+" / "+label,
                        value.get("complete_cases", "N/E"), value.get("incomplete_cases", "N/E"),
                        value.get("evaluated_cases", "N/E"), number(value.get("complete_rate"), percent=True)])
            story += [table(summary, [70, 29, 29, 29, 29]), Spacer(1, 3*mm),
                      p("Denominador: casos documentales válidos con medición. Comportamiento y errores quedan fuera; los contadores e IDs excluidos permanecen en el JSON. Las unidades faltantes se detallan por caso en JSON y CSV.", True), Spacer(1, 3*mm)]
            matrix = [["Caso", *["Top-3 "+label for label in labels], *["Contexto "+label for label in labels]]]
            for row in case_rows:
                cells = [row["id"]]
                for stage in ("top_3", "context"):
                    for name in variants:
                        detail = row.get("variants", {}).get(name, {}).get("coverage_completeness", {}).get(stage, {})
                        value = detail.get("complete")
                        cell = "ERROR" if row.get("error") else "N/E"
                        if not row.get("error") and row.get("retrieval_evaluable") and value is not None:
                            cell = ("Completa" if value else "Incompleta")+f" ({detail['covered_units']}/{detail['total_units']})"
                        cells.append(cell)
                matrix.append(cells)
            story.append(table(matrix, [14, 43, 43, 43, 43]))
            derivation = report.get("complete_coverage_derivation")
            if derivation:
                story += [Spacer(1, 3*mm), p("Derivación local: "+derivation["derived_at_utc"]+
                    ". Sin búsquedas nuevas ni llamadas a proveedores; conserva fecha y mediciones originales.", True),
                    p("SHA-256 de la matriz histórica: "+derivation["source_sha256"], True)]
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        document=SimpleDocTemplate(str(self.output_path),pagesize=A4,leftMargin=12*mm,rightMargin=12*mm,
            topMargin=20*mm,bottomMargin=17*mm,title="Métricas de recuperación RAG",author="TI-support-RAG")
        document.build(story,canvasmaker=partial(NumberedCanvas,header_label="MÉTRICAS RAG - DESARROLLO"))
        return self.output_path

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

        header_label = "EVIDENCIA RAG · PARCIAL 2" if any(c.result.get("rag") for c in self._cases) else "EVIDENCIA TÉCNICA · PARCIAL 1"
        document.build(story, canvasmaker=partial(NumberedCanvas, header_label=header_label))
        return self.output_path


__all__ = [
    "PDFReport",
    "ReportCase",
]
