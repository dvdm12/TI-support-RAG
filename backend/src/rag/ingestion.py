"""Extract only manifest-listed PDFs, preserving sections and original hashes."""
import hashlib
import json
import re
from pathlib import Path
from .models import Section


def clean_text(text: str) -> str:
    paragraphs = re.split(r"\n\s*\n", text.strip())
    return "\n\n".join(" ".join(p.split()) for p in paragraphs if p.strip())


def extract_sections(path: Path, document: dict) -> list[Section]:
    from pypdf import PdfReader

    reader = PdfReader(path)
    if reader.is_encrypted:
        raise ValueError("El corpus no admite PDF cifrados.")
    sections = []
    current = None
    for page_number, page in enumerate(reader.pages, 1):
        text = page.extract_text(extraction_mode="layout") or ""
        if not text.strip():
            raise ValueError(f"Página {page_number} sin texto: requiere extracción OCR revisada.")
        for line in text.splitlines():
            line = line.strip()
            match = re.match(r"^([A-Z]+-\d{2})\s*\|\s*(.+)$", line)
            if match:
                current = {"section": f"{match[1]} | {match[2]}", "lines": [], "pages": []}
                sections.append(current)
                current['pages'].append(page_number)
            elif current is not None:
                # Known recurring layout elements, never arbitrary body keywords.
                if (line == document['title'] or line.startswith('Continuación ·')
                        or line.startswith('TI-support-RAG | Corpus simulado')):
                    continue
                current['lines'].append(line)
                if line and page_number not in current['pages']:
                    current['pages'].append(page_number)
    if not sections:
        raise ValueError(f"No se encontraron secciones identificables en {path.name}.")
    if len({s['section'] for s in sections}) != len(sections):
        raise ValueError('Identificadores de sección duplicados: revisar extracción.')
    return [Section(
        document_id=document['document_id'], source=document['path'],
        title=document['title'], section=s['section'], category=document['category'],
        version=document['version'], source_hash=document['sha256'],
        pages=s['pages'], text=clean_text('\n'.join(s['lines'])),
        simulated=document['simulated'],
    ) for s in sections]


def load_corpus(manifest_path: str | Path) -> list[Section]:
    manifest_path = Path(manifest_path).resolve()
    records = json.loads(manifest_path.read_text(encoding='utf-8'))['documents']
    if not records or len({d['document_id'] for d in records}) != len(records):
        raise ValueError('Corpus vacío o identidades documentales duplicadas.')
    result = []
    for record in records:
        path = (manifest_path.parent / record['path']).resolve()
        if not path.is_relative_to(manifest_path.parent) or path.suffix.lower() != '.pdf':
            raise ValueError('Solo se admiten PDF dentro del corpus.')
        if hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError(f"La fuente cambió: {record['document_id']}.")
        if record['simulated'] is not True:
            raise ValueError('Este corpus debe conservar su condición simulada.')
        result.extend(extract_sections(path, record))
    return result
