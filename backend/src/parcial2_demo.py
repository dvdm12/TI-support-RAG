"""Notebook interaction using project components; no credentials or startup calls."""
import json
from copy import deepcopy
from pathlib import Path

import numpy as np

from src.rag.config import ROOT
from src.rag.index import load_index
from src.rag.repository import LocalRepository, SupabaseRepository
from src.rag.lexical import rank
from src.rag.retrieval import Retriever
from src.rag.context import build_context
from src.rag.pipeline import run_rag_case
from src.rag.embeddings import SentenceEmbedder


class ProfessorDemo:
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.corpus_id, self.chunks, vectors, self.config = load_index(self.root / 'data/indexes/sections')
        self.local = LocalRepository()
        self.local.upsert(self.corpus_id, self.chunks, vectors, self.config)
        self.inventory = self.local.lexical_candidates(self.corpus_id, self.config)
        review = json.loads((self.root / 'docs/human_review/class09_review_v1.json').read_text())
        self.saved = {r['case_id']: r for r in review['rows'] if r['variant'] == 'API_system_v8'}
        self.embedder = None
        self.remote = None
        self.supabase_receipt = None

    @staticmethod
    def validate_question(question):
        if not isinstance(question, str) or not question.strip() or len(question) > 4000:
            raise ValueError('Escribe una pregunta de 1 a 4000 caracteres.')
        return question.strip()

    def saved_case(self, ident):
        if ident not in self.saved:
            raise ValueError('Selecciona uno de los trece casos de desarrollo.')
        row = self.saved[ident]
        return deepcopy({'mode': 'saved_observation', 'case_id': ident, 'question': row['question'],
                         'response': row['response'], 'sources': row['cited_passages'],
                         'expected_units': row['expected_information_units'], 'provider_calls': 0})

    def load_embedder(self):
        if self.embedder is None:
            self.embedder = SentenceEmbedder(self.config.revision)
            self.embedder.assert_compatible(self.config)
        return self.embedder

    def search(self, question, *, hybrid=False):
        question = self.validate_question(question)
        trace = {}
        if hybrid:
            retriever = Retriever(self.local, self.load_embedder(), self.corpus_id, self.config)
            candidates, _ = retriever.retrieve(question, trace=trace)
        else:
            candidates = rank(question, self.inventory, 3)
        context = build_context(question, candidates)
        return {'mode': 'local_search', 'method': 'semantic_bm25_rrf' if hybrid else 'bm25',
                'question': question, 'candidates': [c.model_dump() for c in candidates],
                'context': context['user_content'], 'ranking_trace': trace,
                'answer_generated': False, 'provider_calls': 0}

    def prepare_supabase(self, question, *, upload=False):
        """Explicit professor-owned session, optional upload, second-client check."""
        question = self.validate_question(question)
        self.remote = None
        self.supabase_receipt = None
        embedder = self.load_embedder()
        first = SupabaseRepository.connect()
        if upload:
            # Use the same immutable index, never infer embeddings from metadata.
            _, chunks, vectors, config = load_index(self.root / 'data/indexes/sections', embedder)
            first.upsert(self.corpus_id, chunks, vectors, config)
        visible = first.lexical_candidates(self.corpus_id, self.config)
        expected = {c.chunk_id: c.text for c in self.chunks}
        if len(visible) != len(expected) or {c.chunk_id: c.content for c in visible} != expected:
            raise ValueError('El usuario de Auth no tiene el corpus compatible. Prepara SQL y carga el índice en su proyecto.')
        vector = embedder.encode([question])[0]
        original = first.search(self.corpus_id, vector, self.config, 3)
        second = SupabaseRepository.connect()
        repeated = second.search(self.corpus_id, vector, self.config, 3)
        if (first.owner_id != second.owner_id
                or [c.chunk_id for c in original] != [c.chunk_id for c in repeated]
                or [c.content for c in original] != [c.content for c in repeated]
                or not np.allclose([c.similitud for c in original], [c.similitud for c in repeated])):
            raise ValueError('La recuperación desde el segundo cliente no coincide.')
        self.remote = first
        self.supabase_receipt = {'rows_verified': len(visible), 'upsert_performed': bool(upload),
                                'persistence_new_client': True, 'second_client_upsert': False,
                                'owner_isolation': 'No probado: ambos clientes usan el mismo usuario.'}
        return deepcopy(self.supabase_receipt)

    def query(self, question, *, use_supabase=False):
        question = self.validate_question(question)
        if use_supabase and self.remote is None:
            raise ValueError('Comprueba primero Supabase con tus secretos de Colab.')
        repository = self.remote if use_supabase else self.local
        retriever = Retriever(repository, self.load_embedder(), self.corpus_id, self.config)
        result = run_rag_case({'id': 'PROFESOR', 'tipo': 'usuario', 'input': question}, retriever)
        # Keep an explicit export surface; provider headers/credentials are excluded.
        return {'mode': 'live_query', 'backend': 'supabase' if use_supabase else 'local',
                'question': question, 'state': result['state'], 'classification': result['classification'],
                'response': result['documentary_output'], 'failure_stage': result['failure_stage'],
                'candidates': result['rag']['candidates'], 'sources': result['rag']['catalog'],
                'context': result['user_content_sent'], 'timings': result['rag']['timings'],
                'generation_usage': result.get('usage'), 'supabase_check': self.supabase_receipt if use_supabase else None}
