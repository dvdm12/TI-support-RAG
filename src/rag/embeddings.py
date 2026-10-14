"""Pinned representation and explicit rejection of silent token truncation."""
import re
import numpy as np
from .config import EMBEDDING_MODEL


def validate_vectors(vectors, count: int) -> np.ndarray:
    matrix = np.asarray(vectors)
    if matrix.shape != (count, 384) or not np.issubdtype(matrix.dtype, np.floating):
        raise ValueError('Se necesita una matriz flotante N × 384.')
    if not np.isfinite(matrix).all() or not np.allclose(np.linalg.norm(matrix, axis=1), 1, atol=1e-3):
        raise ValueError('Los vectores deben ser finitos, no nulos y normalizados.')
    return matrix


class SentenceEmbedder:
    def __init__(self, revision: str | None = None, *, model: str = EMBEDDING_MODEL):
        from huggingface_hub import model_info
        from sentence_transformers import SentenceTransformer

        if model != EMBEDDING_MODEL:
            raise ValueError('Modelo incompatible con esta implementación.')
        self.revision = revision or model_info(model).sha
        if not re.fullmatch(r'[0-9a-f]{40}', self.revision):
            raise ValueError('Registra una revisión exacta del modelo.')
        self.model_name = model
        self.model = SentenceTransformer(model, revision=self.revision, device='cpu')
        self.max_seq_length = self.model.max_seq_length
        if self.model.get_sentence_embedding_dimension() != 384:
            raise ValueError('La dimensión del modelo no es 384.')

    def count_tokens(self, text: str) -> int:
        return len(self.model.tokenizer.encode(text, add_special_tokens=True, truncation=False))

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts or any(not t.strip() for t in texts):
            raise ValueError('No se admiten textos vacíos.')
        if any(self.count_tokens(t) > self.max_seq_length for t in texts):
            raise ValueError('Entrada superior al límite efectivo del modelo de embeddings.')
        return validate_vectors(self.model.encode(texts, normalize_embeddings=True,
                                convert_to_numpy=True, show_progress_bar=False), len(texts))

    def assert_compatible(self, config) -> None:
        if (config.modelo != self.model_name or config.revision != self.revision
                or config.max_seq_length != self.max_seq_length):
            raise ValueError('La representación no coincide con el índice.')
