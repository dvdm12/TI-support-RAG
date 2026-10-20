"""Authenticated Supabase operations and explicit local exact-search adapter."""
import re
from urllib.parse import urlparse
from uuid import UUID
import numpy as np
from src.config import get_secret
from .models import Candidate
from .embeddings import validate_vectors


class RepositoryError(RuntimeError):
    pass


class SupabaseRepository:
    def __init__(self, client, owner_id: str):
        self.client = client
        self.owner_id = str(UUID(owner_id))

    @classmethod
    def connect(cls):
        from supabase import create_client, ClientOptions

        url, key = get_secret('SUPABASE_URL'), get_secret('SUPABASE_PUBLISHABLE_KEY')
        parsed = urlparse(url)
        if parsed.scheme != 'https' or not (parsed.hostname or '').endswith('.supabase.co'):
            raise ValueError('Usa la Project URL HTTPS de Supabase.')
        if not key.startswith('sb_publishable_'):
            raise ValueError('Se requiere clave publicable, nunca service_role o clave secreta.')
        client = create_client(url, key, options=ClientOptions(persist_session=False))
        try:
            session = client.auth.sign_in_with_password({'email': get_secret('SUPABASE_EMAIL'),
                                                        'password': get_secret('SUPABASE_PASSWORD')})
            if not session.user or not session.session:
                raise RepositoryError('Sesión de usuario requerida.')
        except Exception:
            raise RepositoryError('No se pudo autenticar el usuario de Supabase.') from None
        return cls(client, session.user.id)

    def upsert(self, corpus_id, chunks, vectors, config):
        validate_corpus_id(corpus_id)
        matrix = validate_vectors(vectors, len(chunks))
        rows = [{'owner_id': self.owner_id, 'corpus_id': corpus_id,
                 'chunk_id': c.chunk_id, 'content': c.text,
                 'metadata': c.model_dump(exclude={'chunk_id', 'text'}),
                 'configuracion': config.model_dump(), 'embedding': matrix[i].tolist()}
                for i, c in enumerate(chunks)]
        try:
            for start in range(0, len(rows), 50):
                self.client.table('clase08_fragmentos').upsert(
                    rows[start:start+50], on_conflict='owner_id,corpus_id,chunk_id').execute()
        except Exception:
            raise RepositoryError('Fallo de carga en Supabase; puede haber lotes parciales. Repite la misma construcción.') from None

    def search(self, corpus_id, vector, config, k=3):
        params = rpc_params(corpus_id, vector, config, k)
        try:
            rows = self.client.rpc('clase08_buscar_fragmentos', params).execute().data
            if not rows:
                raise RepositoryError('No hay filas visibles: revisa carga, sesión, corpus y permisos.')
            return [Candidate.model_validate(r) for r in rows]
        except RepositoryError:
            raise
        except Exception:
            raise RepositoryError('Fallo de recuperación en Supabase.') from None

    def lexical_search(self, corpus_id, query, config, k=10):
        """Fetch only this user's compatible passages; RLS still applies.

        Intended for the small teaching corpus. Paginate rather than trusting
        the server's row limit; never use the local index as a remote fallback.
        """
        from .lexical import rank
        validate_corpus_id(corpus_id)
        candidates, start = [], 0
        try:
            while True:
                rows = (self.client.table('clase08_fragmentos')
                        .select('chunk_id,content,metadata')
                        .eq('owner_id', self.owner_id).eq('corpus_id', corpus_id)
                        .eq('configuracion->>modelo', config.modelo)
                        .eq('configuracion->>revision', config.revision)
                        .order('chunk_id').range(start, start + 499).execute().data)
                candidates.extend(Candidate(**row, similitud=0) for row in rows)
                if len(rows) < 500:
                    break
                start += 500
        except Exception:
            raise RepositoryError('Fallo de recuperación léxica en Supabase.') from None
        return rank(query, candidates, k)


def validate_corpus_id(corpus_id):
    if not isinstance(corpus_id, str) or not 1 <= len(corpus_id.strip()) <= 100:
        raise ValueError('corpus_id inválido.')


def rpc_params(corpus_id, vector, config, k=3):
    validate_corpus_id(corpus_id)
    if type(k) is not int or not 1 <= k <= 10:
        raise ValueError('k debe estar entre 1 y 10.')
    matrix = validate_vectors(np.asarray(vector, dtype=float).reshape(1, -1), 1)
    return {'query_embedding': matrix[0].tolist(), 'p_corpus_id': corpus_id,
            'p_modelo': config.modelo, 'p_revision': config.revision, 'match_count': k}


class LocalRepository:
    """Offline exact search; this adapter does not claim to implement SQL RLS."""
    def __init__(self):
        self.rows = {}

    def upsert(self, corpus_id, chunks, vectors, config):
        validate_corpus_id(corpus_id)
        matrix = validate_vectors(vectors, len(chunks))
        for c, v in zip(chunks, matrix):
            self.rows[corpus_id, c.chunk_id] = (c, v.copy(), config)

    def search(self, corpus_id, vector, config, k=3):
        rpc_params(corpus_id, vector, config, k)
        matches = [Candidate(chunk_id=c.chunk_id, content=c.text,
                             metadata=c.model_dump(exclude={'chunk_id', 'text'}),
                             similitud=float(v @ vector))
                   for (corpus, _), (c, v, cfg) in self.rows.items()
                   if corpus == corpus_id and cfg == config]
        if not matches:
            raise RepositoryError('La construcción no está cargada o es incompatible.')
        return sorted(matches, key=lambda r: (-r.similitud, r.chunk_id))[:k]

    def lexical_search(self, corpus_id, query, config, k=10):
        from .lexical import rank
        candidates = [Candidate(chunk_id=c.chunk_id, content=c.text,
                                metadata=c.model_dump(exclude={'chunk_id', 'text'}), similitud=0)
                      for (corpus, _), (c, _, cfg) in self.rows.items()
                      if corpus == corpus_id and cfg == config]
        return rank(query, candidates, k)
