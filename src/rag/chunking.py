"""Comparable character cuts and structural paragraphs, bounded by real tokens."""
import hashlib
import json
import re
from .models import Chunk, EmbeddingConfig


def fragment_sections(sections, embedder, config: EmbeddingConfig) -> list[Chunk]:
    embedder.assert_compatible(config)
    budget = min(config.max_tokens, embedder.max_seq_length)
    if config.estrategia == 'overlap' and config.overlap_chars >= config.chunk_chars:
        raise ValueError('El solapamiento debe ser menor que el corte.')
    chunks = []
    for section in sections:
        header = f'{section.title} / {section.section}\n'
        if embedder.count_tokens(header) >= budget:
            raise ValueError('El encabezado no deja presupuesto para el contenido.')
        parts = re.split(r'\n\s*\n', section.text) if config.estrategia == 'sections' else [section.text]
        for part_number, part in enumerate(parts):
            start = 0
            while start < len(part):
                end = min(start + config.chunk_chars, len(part))
                while end > start and embedder.count_tokens(header + part[start:end]) > budget:
                    end -= 1
                if end <= start:
                    raise ValueError('No se pudo producir un fragmento dentro del presupuesto.')
                text = header + part[start:end].strip()
                identity = json.dumps([section.document_id, section.source_hash, section.section,
                                       config.model_dump(), part_number, start, end, text], sort_keys=True)
                chunk_id = section.document_id + '-' + hashlib.sha256(identity.encode()).hexdigest()[:24]
                chunks.append(Chunk(**{**section.model_dump(), 'text': text},
                                    chunk_id=chunk_id, tokens=embedder.count_tokens(text)))
                if end == len(part):
                    break
                overlap = config.overlap_chars if config.estrategia == 'overlap' else 0
                # Token-bound cuts can be shorter than the configured overlap.
                start = end - min(overlap, max(0, (end - start) // 2))
    if len({c.chunk_id for c in chunks}) != len(chunks):
        raise ValueError('Identidades de fragmento duplicadas.')
    return chunks
