"""Build independently; --upload is the explicit authenticated persistence step."""
import argparse
import json
from pathlib import Path
from src.rag.config import RAGConfig
from src.rag.ingestion import load_corpus
from src.rag.embeddings import SentenceEmbedder
from src.rag.models import EmbeddingConfig
from src.rag.chunking import fragment_sections
from src.rag.index import save_index, load_index
from src.rag.repository import SupabaseRepository


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=RAGConfig().manifest)
    parser.add_argument('--output', type=Path, default=Path('data/indexes/sections'))
    parser.add_argument('--strategy', choices=['characters', 'overlap', 'sections'], default='sections')
    parser.add_argument('--revision')
    parser.add_argument('--chunk-chars', type=int, default=420)
    parser.add_argument('--overlap-chars', type=int, default=80)
    parser.add_argument('--max-tokens', type=int, default=80)
    parser.add_argument('--upload', action='store_true')
    parser.add_argument('--existing', action='store_true', help='Load an existing construction; do not reindex.')
    args = parser.parse_args()
    if args.existing:
        corpus_id, chunks, vectors, config = load_index(args.output)
        embedder = SentenceEmbedder(config.revision)
        load_index(args.output, embedder)
    else:
        sections = load_corpus(args.manifest)
        embedder = SentenceEmbedder(args.revision)
        config = EmbeddingConfig(modelo=embedder.model_name, revision=embedder.revision,
                                 max_seq_length=embedder.max_seq_length, estrategia=args.strategy,
                                 chunk_chars=args.chunk_chars, max_tokens=args.max_tokens,
                                 overlap_chars=args.overlap_chars if args.strategy == 'overlap' else 0)
        chunks = fragment_sections(sections, embedder, config)
        vectors = embedder.encode([c.text for c in chunks])
        corpus_id = save_index(args.output, chunks, vectors, config)
        load_index(args.output, embedder)
    if args.upload:
        SupabaseRepository.connect().upsert(corpus_id, chunks, vectors, config)
    print(json.dumps({'corpus_id': corpus_id, 'chunks': len(chunks),
                      'revision': config.revision, 'uploaded': args.upload}, indent=2))


if __name__ == '__main__':
    main()
