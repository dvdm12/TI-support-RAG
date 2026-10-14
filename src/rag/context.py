"""Whole passages under an explicit serialized-character context budget."""
import json


def build_context(question, candidates, *, classification=None, max_chars=6000, request_fits=None):
    if max_chars < 1:
        raise ValueError('Presupuesto de contexto inválido.')
    compact_classification = {'categoria':classification['categoria']} if request_fits and classification else classification
    payload = {'pregunta': question, 'clasificacion': compact_classification,
               'corpus_simulado': True, 'evidencia': []}
    catalog, omitted, seen = {}, [], set()
    encode = lambda: json.dumps(payload, ensure_ascii=False,separators=(',',':')) if request_fits else json.dumps(payload, ensure_ascii=False)
    if len(encode()) > max_chars:
        raise ValueError('La pregunta y clasificación exceden el presupuesto de contexto.')
    if request_fits and not request_fits(encode()):
        raise ValueError('La pregunta e instrucciones exceden el presupuesto de tokens.')
    for candidate in candidates:
        if candidate.content in seen:
            omitted.append({'chunk_id': candidate.chunk_id, 'reason': 'duplicate_content'})
            continue
        seen.add(candidate.content)
        label = f'F{len(catalog)+1}'
        meta = candidate.metadata
        required = ('source', 'section', 'version', 'document_id', 'category', 'source_hash', 'pages')
        if any(key not in meta for key in required):
            raise ValueError('Un candidato perdió procedencia requerida.')
        passage = {'etiqueta': label, 'chunk_id': candidate.chunk_id,
                   **{key: meta[key] for key in required}, 'texto': candidate.content}
        if request_fits:
            # All provenance stays in catalog/trace; generation only needs the
            # label and complete passage (already headed with title/section).
            passage = {'etiqueta':label,'texto':candidate.content}
        payload['evidencia'].append(passage)
        if len(encode()) > max_chars or (request_fits and not request_fits(encode())):
            payload['evidencia'].pop()
            omitted.append({'chunk_id': candidate.chunk_id, 'reason': 'token_budget' if request_fits else 'context_budget'})
        else:
            catalog[label] = candidate
    return {'user_content': encode(), 'catalog': catalog, 'omitted': omitted,
            'chars': len(encode()), 'budget_chars': max_chars,
            'budget_unit': 'serialized_characters_not_tokens'}
