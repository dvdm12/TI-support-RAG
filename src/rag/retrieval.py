"""Query embedding and retrieval, without a universal similarity threshold."""
import time


class Retriever:
    def __init__(self, repository, embedder, corpus_id, config, k=3):
        embedder.assert_compatible(config)
        self.repository, self.embedder = repository, embedder
        self.corpus_id, self.config, self.k = corpus_id, config, k

    def retrieve(self, query):
        start = time.perf_counter()
        vector = self.embedder.encode([query])[0]
        embedding_seconds = time.perf_counter() - start
        start = time.perf_counter()
        candidates = self.repository.search(self.corpus_id, vector, self.config, self.k)
        return candidates, {'embedding_seconds': embedding_seconds,
                            'retrieval_seconds': time.perf_counter() - start}
