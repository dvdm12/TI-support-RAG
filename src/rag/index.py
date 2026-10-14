"""Persist an immutable construction and check row/text/representation compatibility."""
import hashlib
import json
import re
from pathlib import Path
import numpy as np
from .models import Chunk, EmbeddingConfig
from .embeddings import validate_vectors


def construction_id(base, chunks, vectors, config):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,60}', base):
        raise ValueError('Nombre base inválido.')
    payload = json.dumps({'chunks': [c.model_dump() for c in chunks],
                          'config': config.model_dump()}, sort_keys=True, ensure_ascii=False).encode()
    digest = hashlib.sha256(payload + np.asarray(vectors, dtype='<f4').tobytes()).hexdigest()[:20]
    return f'{base}-{digest}'


def save_index(directory, chunks, vectors, config, base='ti-manuals-v2'):
    vectors = validate_vectors(vectors, len(chunks))
    if not chunks:
        raise ValueError('No se puede guardar un índice vacío.')
    corpus_id = construction_id(base, chunks, vectors, config)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'records.json').write_text(json.dumps([c.model_dump() for c in chunks], ensure_ascii=False, indent=2))
    np.save(directory / 'vectors.npy', vectors)
    (directory / 'config.json').write_text(json.dumps({'corpus_id': corpus_id, 'base': base,
                                                     'config': config.model_dump()}, indent=2))
    return corpus_id


def load_index(directory, embedder=None):
    directory = Path(directory)
    info = json.loads((directory / 'config.json').read_text())
    config = EmbeddingConfig.model_validate(info['config'])
    chunks = [Chunk.model_validate(c) for c in json.loads((directory / 'records.json').read_text())]
    if not chunks or len({c.chunk_id for c in chunks}) != len(chunks):
        raise ValueError('Índice vacío o duplicado.')
    vectors = validate_vectors(np.load(directory / 'vectors.npy', allow_pickle=False), len(chunks))
    if construction_id(info['base'], chunks, vectors, config) != info['corpus_id']:
        raise ValueError('La construcción almacenada fue alterada.')
    if embedder:
        embedder.assert_compatible(config)
        if any(embedder.count_tokens(c.text) != c.tokens or c.tokens > min(config.max_tokens, config.max_seq_length) for c in chunks):
            raise ValueError('Fragmentos truncados o conteo incompatible.')
        samples = sorted({0, len(chunks) - 1})
        recalculated = embedder.encode([chunks[i].text for i in samples])
        if not np.allclose(np.sum(recalculated * vectors[samples], axis=1), 1, atol=1e-3):
            raise ValueError('Las muestras de texto y vectores no coinciden.')
    return info['corpus_id'], chunks, vectors, config
