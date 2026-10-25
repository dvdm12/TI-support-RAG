import argparse
import json
from pathlib import Path
from src.rag.config import RAGConfig, ROOT
from src.rag.ingestion import load_corpus
from src.rag.embeddings import SentenceEmbedder
from src.rag.comparison import compare_strategies


def main():
    parser = argparse.ArgumentParser(description='Comparar tres cortes; no asigna ganador automáticamente.')
    parser.add_argument('--revision')
    parser.add_argument('--output', type=Path, default=Path('docs/evaluacion/recuperacion/rag_comparison.json'))
    args = parser.parse_args()
    result = compare_strategies(load_corpus(RAGConfig().manifest), SentenceEmbedder(args.revision),
                               json.loads((ROOT / 'cases/rag_questions.json').read_text()),
                               ROOT / 'data/indexes')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(args.output)


if __name__ == '__main__':
    main()
