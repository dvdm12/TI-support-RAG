"""Reference existence and coherence; semantic support remains a review task."""
import re
from schemas.rag_response_v1 import RespuestaRAG


def validate_response(raw, catalog) -> RespuestaRAG:
    result = (RespuestaRAG.model_validate_json(raw) if isinstance(raw, str)
              else RespuestaRAG.model_validate(raw))
    labels = set(result.citas)
    mentions = set(re.findall(r'\[(F\d+)\]', result.respuesta))
    if any(not re.fullmatch(r'F[1-9]\d*', label) for label in labels):
        raise ValueError('Formato de etiqueta inválido.')
    if not labels.issubset(catalog) or labels != mentions:
        raise ValueError('Las citas no coinciden con el catálogo y la respuesta.')
    return result
