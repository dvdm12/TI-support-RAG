"""Query embedding and retrieval, without a universal similarity threshold."""
from .lexical import rank
from .timing import measure
from .applicability import applicable_candidates

RRF_CONSTANT = 60
SEMANTIC_WEIGHT = 1
LEXICAL_WEIGHT = 2
RETRIEVAL_VERSION = "technical_tokens_applicable_weighted_rrf_v2"


def fuse_rankings(semantic, lexical, *, constant=RRF_CONSTANT,
                  semantic_weight=SEMANTIC_WEIGHT, lexical_weight=LEXICAL_WEIGHT):
    """One row per chunk; absent branches contribute zero, positions start at one."""
    if type(constant) is not int or constant < 0:
        raise ValueError('La constante RRF debe ser un entero no negativo.')
    positions = []
    for ranked in (semantic, lexical):
        ids = [c.chunk_id for c in ranked]
        if len(ids) != len(set(ids)):
            raise ValueError('Un ranking no puede repetir un chunk_id.')
        positions.append({ident: i for i, ident in enumerate(ids, 1)})
    sempos, lexpos = positions
    rows = []
    for ident in sempos.keys() | lexpos.keys():
        a = semantic_weight / (constant + sempos[ident]) if ident in sempos else 0.0
        b = lexical_weight / (constant + lexpos[ident]) if ident in lexpos else 0.0
        rows.append({'chunk_id': ident, 'semantic_rank': sempos.get(ident),
                     'bm25_rank': lexpos.get(ident), 'semantic_contribution': a,
                     'bm25_contribution': b, 'rrf_score': a + b})
    return sorted(rows, key=lambda row: (-row['rrf_score'], row['chunk_id']))


def select_ranked_candidates(query, semantic, lexical, *, k=3, category=None):
    """Shared production/offline selection with an auditable pre-filter union."""
    pool = {}
    for candidate in semantic + lexical:
        pool.setdefault(candidate.chunk_id, candidate)
    fused = fuse_rankings(semantic, lexical)
    applicable, omitted = applicable_candidates(query, list(pool.values()))
    included = {c.chunk_id for c in applicable}
    reasons = {row['chunk_id']: row['reason'] for row in omitted}
    for row in fused:
        ident = row['chunk_id']
        row['category_boost'] = .025 if category and pool[ident].metadata.get('category') == category else 0.0
        row['selection_score'] = row['rrf_score'] + row['category_boost']
        row['applicable'] = ident in included
        row['exclusion_reason'] = reasons.get(ident)
    fused.sort(key=lambda row: (-row['selection_score'], row['chunk_id']))
    selected = [r['chunk_id'] for r in fused if r['applicable']][:k]
    for row in fused:
        row['selected_rank'] = selected.index(row['chunk_id']) + 1 if row['chunk_id'] in selected else None
    trace = {
        'retrieval_version': RETRIEVAL_VERSION,
        'parameters': {'rrf_constant': RRF_CONSTANT, 'semantic_weight': SEMANTIC_WEIGHT,
                       'lexical_weight': LEXICAL_WEIGHT, 'k': k, 'category': category},
        'semantic_ranking': [{'chunk_id': c.chunk_id, 'cosine': c.similitud} for c in semantic],
        'bm25_ranking': [c.chunk_id for c in lexical],
        'rrf_union': fused, 'applicability_omitted': omitted, 'selected_ids': selected,
    }
    return [pool[ident] for ident in selected], trace


class Retriever:
    def __init__(self, repository, embedder, corpus_id, config, k=3):
        embedder.assert_compatible(config)
        self.repository, self.embedder = repository, embedder
        self.corpus_id, self.config, self.k = corpus_id, config, k

    def retrieve(self, query, category=None, *, timings=None, trace=None):
        # A caller-owned mapping preserves completed/failed stage measurements
        # if an exception prevents returning candidates.
        timings = {} if timings is None else timings
        with measure(timings, 'embedding_seconds'):
            vector = self.embedder.encode([query])[0]
        with measure(timings, 'retrieval_seconds'):
            with measure(timings, 'semantic_search_seconds'):
                semantic = self.repository.search(self.corpus_id, vector, self.config, 10)
            with measure(timings, 'lexical_fetch_seconds'):
                corpus = self.repository.lexical_candidates(self.corpus_id, self.config)
            with measure(timings, 'bm25_seconds'):
                lexical = rank(query, corpus, 10)
            with measure(timings, 'rrf_seconds'):
                selected, observed = select_ranked_candidates(query, semantic, lexical, k=self.k, category=category)
                if trace is not None:
                    trace.clear()
                    trace.update(observed)
            with measure(timings, 'candidate_scoring_seconds'):
                candidates = []
                for candidate in selected:
                    ident = candidate.chunk_id
                    # Lexical-only results retain their actual cosine score.
                    if not any(c.chunk_id == ident for c in semantic):
                        passage_vector = self.embedder.encode([candidate.content])[0]
                        candidate = candidate.model_copy(update={'similitud': float(passage_vector @ vector)})
                    candidates.append(candidate)
        return candidates, timings
