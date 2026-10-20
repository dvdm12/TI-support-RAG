"""Non-secret configuration for documentary retrieval."""
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


@dataclass(frozen=True)
class RAGConfig:
    model: str = EMBEDDING_MODEL
    revision: str | None = None
    dimension: int = 384
    strategy: str = "sections"
    chunk_chars: int = 420
    overlap_chars: int = 80
    max_tokens: int = 80
    k: int = 3
    context_chars: int = 6000
    corpus_base: str = "ti-manuals-v2"
    manifest: Path = ROOT / "data/corpus/v2/manifest.json"
    prompt: Path = ROOT / "prompts/rag_v4.md"
