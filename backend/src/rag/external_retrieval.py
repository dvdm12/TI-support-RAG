"""Local parent-level retrieval over bounded multilingual embedding views."""
import re
import unicodedata
import numpy as np
from .lexical import rank, tokens
from .models import Candidate


def retrieve_units(query, vector, units, fragments, vectors, k=3, mode='semantic'):
    if mode not in {'semantic', 'hybrid', 'hybrid_literal'}:
        raise ValueError('Estrategia local desconocida.')
    by_id = {u['unit_id']: u for u in units}
    best = {}
    for position, score in enumerate(vectors @ np.asarray(vector)):
        fragment = fragments[position]
        uid = fragment['unit_id']
        if uid not in best or float(score) > best[uid]['cosine']:
            best[uid] = {'unit_id': uid, 'fragment_id': fragment['fragment_id'],
                         'cosine': float(score), 'search_view': fragment['text']}
    semantic = sorted(best, key=lambda uid: (-best[uid]['cosine'], uid))
    ordered = semantic
    if mode in {'hybrid', 'hybrid_literal'}:
        # Remove ubiquitous device terms without translating the query or
        # inserting test-specific synonyms. Shared model names carry no intent.
        terms = tokens(query)
        corpus_terms = [set(tokens(f['text'])) for f in fragments]
        meaningful = [t for t in terms if sum(t in d for d in corpus_terms) <= len(fragments) * .8]
        candidates = [Candidate(chunk_id=f['fragment_id'], content=f['text'],
                                metadata={'unit_id': f['unit_id']}, similitud=0)
                      for f in fragments]
        lexical = []
        for candidate in rank(' '.join(meaningful), candidates, len(candidates)):
            uid = candidate.metadata['unit_id']
            if uid not in lexical:
                lexical.append(uid)
        scores = {}
        for ranking in (semantic[:50], lexical[:50]):
            for position, uid in enumerate(ranking, 1):
                scores[uid] = scores.get(uid, 0) + 1 / (60 + position)
        ordered = sorted(scores, key=lambda uid: (-scores[uid], -best[uid]['cosine'], uid))
    if mode == 'hybrid_literal':
        # A quoted display message is source evidence, not a model prediction.
        # Match the complete primary message cell, never an arbitrary body hit.
        def canonical(text):
            return ' '.join(unicodedata.normalize('NFKC', text).casefold().split())
        quoted = {canonical(q) for q in re.findall(r'["“]([^"”]+)["”]', query) if len(q.strip()) >= 3}
        exact = []
        if quoted:
            for uid, unit in by_id.items():
                if unit['row'] and unit['row']['headers'][0].casefold() == 'message':
                    message = unit['row']['cells'][0]
                    primary = re.match(r'^"([^"]+)"', message)
                    primary = primary.group(1) if primary else message
                    if canonical(primary) in quoted:
                        exact.append(uid)
        exact.sort(key=lambda uid: (-best[uid]['cosine'], uid))
        ordered = exact + [uid for uid in ordered if uid not in exact]
        for uid in exact:
            best[uid]['match_basis'] = 'exact_quoted_source_message'
    # Return full source units. Callers must apply a separate generation-context
    # budget; they must never send just a short search view as a full procedure.
    return [{**best[uid], 'unit': by_id[uid]} for uid in ordered[:k]]


def evidence_text(unit):
    context = '\n\n'.join(b['text'] for b in unit['context_blocks'])
    return ('Context from ancestor/current section:\n' + context + '\n\n' if context else '') + unit['body']
