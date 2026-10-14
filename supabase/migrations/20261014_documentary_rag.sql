-- Clase 08: ejecutar en el SQL Editor de un proyecto de práctica.
-- No elimina documentos ni modifica otras tablas del proyecto.
begin;

create schema if not exists extensions;
create extension if not exists vector with schema extensions;

create table if not exists public.clase08_fragmentos (
  owner_id uuid not null default auth.uid() references auth.users(id),
  corpus_id text not null check (length(btrim(corpus_id)) between 1 and 100),
  chunk_id text not null,
  content text not null check (length(btrim(content)) between 1 and 10000),
  metadata jsonb not null,
  configuracion jsonb not null,
  embedding extensions.vector(384) not null,
  primary key (owner_id, corpus_id, chunk_id)
);

alter table public.clase08_fragmentos enable row level security;
revoke all on public.clase08_fragmentos from public, anon, authenticated;
grant usage on schema public, extensions to authenticated;
grant select, insert, update on public.clase08_fragmentos to authenticated;

-- Solo reemplazamos las tres políticas de este ejercicio al repetir el script.
drop policy if exists clase08_select_own on public.clase08_fragmentos;
create policy clase08_select_own on public.clase08_fragmentos
  for select to authenticated
  using ((select auth.uid()) = owner_id);

drop policy if exists clase08_insert_own on public.clase08_fragmentos;
create policy clase08_insert_own on public.clase08_fragmentos
  for insert to authenticated
  with check ((select auth.uid()) = owner_id);

drop policy if exists clase08_update_own on public.clase08_fragmentos;
create policy clase08_update_own on public.clase08_fragmentos
  for update to authenticated
  using ((select auth.uid()) = owner_id)
  with check ((select auth.uid()) = owner_id);

-- Búsqueda exacta para el corpus pequeño de la práctica.
-- El índice de la clave primaria ayuda a delimitar propietario y corpus.
-- No necesitamos todavía un índice vectorial aproximado HNSW o IVFFlat.
create or replace function public.clase08_buscar_fragmentos(
  query_embedding extensions.vector(384),
  p_corpus_id text,
  p_modelo text,
  p_revision text,
  match_count integer default 3
)
returns table (
  chunk_id text,
  content text,
  metadata jsonb,
  similitud double precision
)
language sql stable
security invoker
set search_path = ''
as $$
  select d.chunk_id, d.content, d.metadata,
         1 - (d.embedding operator(extensions.<=>) query_embedding) as similitud
  from public.clase08_fragmentos as d
  where d.owner_id = (select auth.uid())
    and d.corpus_id = p_corpus_id
    and d.configuracion ->> 'modelo' = p_modelo
    and d.configuracion ->> 'revision' = p_revision
  order by d.embedding operator(extensions.<=>) query_embedding, d.chunk_id
  limit least(greatest(coalesce(match_count, 3), 1), 10);
$$;

revoke all on function public.clase08_buscar_fragmentos(extensions.vector, text, text, text, integer)
  from public, anon;
grant execute on function public.clase08_buscar_fragmentos(extensions.vector, text, text, text, integer)
  to authenticated;

notify pgrst, 'reload schema';
commit;

-- Comprobaciones de instalación. Al principio es normal tener cero filas.
select extname, extnamespace::regnamespace as esquema
from pg_extension where extname = 'vector';

select relname, relrowsecurity
from pg_class where oid = 'public.clase08_fragmentos'::regclass;

select count(*) as fragmentos_totales from public.clase08_fragmentos;
