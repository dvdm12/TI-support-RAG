"""Verify an uploaded construction from two authenticated clients, without reindexing."""
import argparse
import json
from pathlib import Path
import numpy as np
from src.rag.index import load_index
from src.rag.repository import SupabaseRepository, RepositoryError


def inventory(repository, corpus_id):
    try:
        response = (repository.client.table('clase08_fragmentos')
                    .select('chunk_id,content', count='exact')
                    .eq('owner_id', repository.owner_id).eq('corpus_id', corpus_id)
                    .range(0, 999).execute())
    except Exception:
        raise RepositoryError('No se pudo verificar la tabla; revisa la migración y los permisos.') from None
    if response.count != len(response.data):
        raise RepositoryError('La comprobación admite hasta 1000 filas; ajusta la paginación para corpus mayores.')
    return {row['chunk_id']: row['content'] for row in response.data}


def verify(index_directory, *, connect=SupabaseRepository.connect):
    corpus_id, chunks, vectors, config = load_index(index_directory)
    first = connect()
    expected = {chunk.chunk_id: chunk.text for chunk in chunks}
    if inventory(first, corpus_id) != expected:
        raise RepositoryError('Las filas visibles no coinciden con el índice: carga la construcción correcta.')
    candidates = first.search(corpus_id, vectors[0], config, 3)
    second = connect()
    if second.owner_id != first.owner_id:
        raise RepositoryError('La prueba de persistencia requiere el mismo usuario.')
    if inventory(second, corpus_id) != expected:
        raise RepositoryError('El cliente nuevo no conserva la misma construcción.')
    repeated = second.search(corpus_id, vectors[0], config, 3)
    if ([c.chunk_id for c in candidates] != [c.chunk_id for c in repeated]
            or [c.content for c in candidates] != [c.content for c in repeated]
            or not np.allclose([c.similitud for c in candidates], [c.similitud for c in repeated])):
        raise RepositoryError('La recuperación difiere entre los dos clientes.')
    return {'corpus_id': corpus_id, 'rows_verified': len(expected),
            'authenticated': True, 'persistence_new_client': True,
            'rpc_verified': True, 'probe': 'embedding_of_first_stored_chunk',
            'owner_isolation': 'PENDIENTE: requiere un segundo usuario de Auth.',
            'upsert_performed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index', type=Path, default=Path('data/indexes/sections'))
    parser.add_argument('--output', type=Path, default=Path('docs/rag_runs/supabase_check.json'))
    args = parser.parse_args()
    try:
        result = verify(args.index)
    except Exception as error:
        print(f'No se completó la verificación: {type(error).__name__}. Revisa configuración, carga y migración.')
        raise SystemExit(1) from None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
