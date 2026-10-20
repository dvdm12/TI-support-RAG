"""Compare real constructions under fixed queries, model, revision and k."""
from collections import Counter
from .chunking import fragment_sections
from .models import EmbeddingConfig
from .index import save_index
from .repository import LocalRepository


def compare_strategies(sections, embedder, questions, output_dir, *, k=3,
                       chunk_chars=420, overlap_chars=80, max_tokens=80):
    from pathlib import Path
    result = {'model': embedder.model_name, 'revision': embedder.revision, 'k': k,
              'winner': None, 'semantic_review': 'PENDIENTE', 'strategies': {}}
    query_vectors = embedder.encode([q['question'] for q in questions])
    for strategy in ('characters', 'overlap', 'sections'):
        config = EmbeddingConfig(modelo=embedder.model_name, revision=embedder.revision,
                                 max_seq_length=embedder.max_seq_length, estrategia=strategy,
                                 chunk_chars=chunk_chars, overlap_chars=overlap_chars if strategy == 'overlap' else 0,
                                 max_tokens=max_tokens)
        chunks = fragment_sections(sections, embedder, config)
        vectors = embedder.encode([c.text for c in chunks])
        corpus_id = save_index(Path(output_dir) / strategy, chunks, vectors, config)
        repository = LocalRepository()
        repository.upsert(corpus_id, chunks, vectors, config)
        trials = []
        for question, vector in zip(questions, query_vectors):
            candidates = repository.search(corpus_id, vector, config, k)
            expected = question.get('expected_section')
            condition = question.get('condition')
            trials.append({**question, 'retrieved': [c.model_dump() for c in candidates],
                           'expected_section_in_top_k': any(expected in c.metadata['section'] for c in candidates) if expected else None,
                           'condition_in_single_chunk': any(condition in c.text for c in chunks) if condition else None,
                           'condition_in_retrieved_context': any(condition in c.content for c in candidates) if condition else None,
                           'retrieved_duplicate_content': len(candidates) - len({c.content for c in candidates}),
                           'semantic_review': 'PENDIENTE'})
        counts = [c.tokens for c in chunks]
        result['strategies'][strategy] = {'corpus_id': corpus_id, 'config': config.model_dump(),
                                          'count': len(chunks), 'tokens_min': min(counts),
                                          'tokens_max': max(counts), 'tokens_mean': sum(counts)/len(counts),
                                          'exact_duplicate_chunks': sum(n-1 for n in Counter(c.text for c in chunks).values()),
                                          'chunks': [c.model_dump() for c in chunks], 'trials': trials}
    return result
