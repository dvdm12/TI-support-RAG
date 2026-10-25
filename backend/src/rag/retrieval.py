"""Query embedding and retrieval, without a universal similarity threshold."""
from .lexical import rank
from .timing import measure
from .applicability import applicable_candidates

RRF_CONSTANT = 60
SEMANTIC_WEIGHT = 1
LEXICAL_WEIGHT = 2
RETRIEVAL_VERSION = "technical_tokens_applicable_weighted_rrf_v2"


class Retriever:
    def __init__(self, repository, embedder, corpus_id, config, k=3):
        embedder.assert_compatible(config)
        self.repository, self.embedder = repository, embedder
        self.corpus_id, self.config, self.k = corpus_id, config, k

    def retrieve(self, query, category=None, *, timings=None):
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
                # Includes category boost, deterministic sorting and Top-k.
                scores, pool = {}, {}
                for ranked, weight in ((semantic, SEMANTIC_WEIGHT), (lexical, LEXICAL_WEIGHT)):
                    for position, candidate in enumerate(ranked, 1):
                        pool.setdefault(candidate.chunk_id, candidate)
                        scores[candidate.chunk_id] = scores.get(candidate.chunk_id, 0) + weight / (RRF_CONSTANT + position)
                if category:
                    for ident, candidate in pool.items():
                        if candidate.metadata.get('category') == category:
                            scores[ident] += .025
                # Filter the full union before Top-k so applicable alternatives
                # can fill positions discarded by the existing incident guard.
                applicable, _ = applicable_candidates(query, list(pool.values()))
                selected = sorted((c.chunk_id for c in applicable), key=lambda ident: (-scores[ident], ident))[:self.k]
            with measure(timings, 'candidate_scoring_seconds'):
                candidates = []
                for ident in selected:
                    candidate = pool[ident]
                    # Lexical-only results retain their actual cosine score.
                    if not any(c.chunk_id == ident for c in semantic):
                        passage_vector = self.embedder.encode([candidate.content])[0]
                        candidate = candidate.model_copy(update={'similitud': float(passage_vector @ vector)})
                    candidates.append(candidate)
        return candidates, timings
