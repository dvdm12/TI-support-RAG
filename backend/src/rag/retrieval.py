"""Query embedding and retrieval, without a universal similarity threshold."""
import time


class Retriever:
    def __init__(self, repository, embedder, corpus_id, config, k=3):
        embedder.assert_compatible(config)
        self.repository, self.embedder = repository, embedder
        self.corpus_id, self.config, self.k = corpus_id, config, k

    def retrieve(self, query, category=None):
        start = time.perf_counter()
        vector = self.embedder.encode([query])[0]
        embedding_seconds = time.perf_counter() - start
        start = time.perf_counter()
        semantic = self.repository.search(self.corpus_id, vector, self.config, 10)
        lexical = self.repository.lexical_search(self.corpus_id, query, self.config, 10)
        # Reciprocal rank fusion: ranking scores are never model confidence.
        scores, pool = {}, {}
        for ranked in (semantic, lexical):
            for position, candidate in enumerate(ranked, 1):
                pool.setdefault(candidate.chunk_id, candidate)
                scores[candidate.chunk_id] = scores.get(candidate.chunk_id, 0) + 1 / (60 + position)
        if category:
            for ident, candidate in pool.items():
                if candidate.metadata.get('category') == category:
                    scores[ident] += .025
        selected = sorted(pool, key=lambda ident: (-scores[ident], ident))[:self.k]
        candidates = []
        for ident in selected:
            candidate = pool[ident]
            # Lexical-only candidates need their actual cosine score too.
            if not any(c.chunk_id == ident for c in semantic):
                passage_vector = self.embedder.encode([candidate.content])[0]
                candidate = candidate.model_copy(update={'similitud': float(passage_vector @ vector)})
            candidates.append(candidate)
        return candidates, {'embedding_seconds': embedding_seconds,
                            'retrieval_seconds': time.perf_counter() - start}
