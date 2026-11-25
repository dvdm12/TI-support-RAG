-- Clase 12: historial de conversaciones por usuario.
-- Ejecutar en el SQL Editor del mismo proyecto de Supabase que ya tiene
-- clase08_fragmentos. No modifica tablas existentes.
-- Idempotente: se puede volver a ejecutar sin error.
begin;

-- ─── Tabla: conversaciones ────────────────────────────────────────────────────
-- Una fila por conversación. El usuario_id es siempre el uid autenticado.

create table if not exists public.conversaciones (
  id          uuid        primary key default gen_random_uuid(),
  usuario_id  uuid        not null default auth.uid() references auth.users(id) on delete cascade,
  titulo      text        not null default 'Nueva conversación'
                            check (length(btrim(titulo)) between 1 and 200),
  creada_en   timestamptz not null default now(),
  actualizada_en timestamptz not null default now()
);

alter table public.conversaciones enable row level security;
revoke all on public.conversaciones from public, anon, authenticated;
grant select, insert, update, delete on public.conversaciones to authenticated;

drop policy if exists conv_select_own on public.conversaciones;
create policy conv_select_own on public.conversaciones
  for select to authenticated
  using ((select auth.uid()) = usuario_id);

drop policy if exists conv_insert_own on public.conversaciones;
create policy conv_insert_own on public.conversaciones
  for insert to authenticated
  with check ((select auth.uid()) = usuario_id);

drop policy if exists conv_update_own on public.conversaciones;
create policy conv_update_own on public.conversaciones
  for update to authenticated
  using ((select auth.uid()) = usuario_id)
  with check ((select auth.uid()) = usuario_id);

drop policy if exists conv_delete_own on public.conversaciones;
create policy conv_delete_own on public.conversaciones
  for delete to authenticated
  using ((select auth.uid()) = usuario_id);

create index if not exists conv_usuario_creada
  on public.conversaciones (usuario_id, creada_en desc);

-- ─── Tabla: mensajes ─────────────────────────────────────────────────────────
-- Una fila por turno (usuario o asistente). El orden viene de creado_en.
-- fuentes guarda la lista de fragmentos documentales que la respuesta citó.

create table if not exists public.mensajes (
  id              uuid        primary key default gen_random_uuid(),
  conversacion_id uuid        not null
                    references public.conversaciones(id) on delete cascade,
  rol             text        not null check (rol in ('usuario', 'asistente')),
  contenido       text        not null check (length(btrim(contenido)) between 1 and 20000),
  fuentes         jsonb       not null default '[]'::jsonb,
  creado_en       timestamptz not null default now()
);

alter table public.mensajes enable row level security;
revoke all on public.mensajes from public, anon, authenticated;
grant select, insert on public.mensajes to authenticated;

-- Un mensaje es accesible solo si la conversación pertenece al usuario.
-- La subconsulta usa (select auth.uid()) para que el planificador la evalúe
-- una vez por sentencia, no una vez por fila.

drop policy if exists msg_select_own on public.mensajes;
create policy msg_select_own on public.mensajes
  for select to authenticated
  using (
    exists (
      select 1 from public.conversaciones c
      where c.id = conversacion_id
        and c.usuario_id = (select auth.uid())
    )
  );

drop policy if exists msg_insert_own on public.mensajes;
create policy msg_insert_own on public.mensajes
  for insert to authenticated
  with check (
    exists (
      select 1 from public.conversaciones c
      where c.id = conversacion_id
        and c.usuario_id = (select auth.uid())
    )
  );

create index if not exists msg_conv_creado
  on public.mensajes (conversacion_id, creado_en asc);

-- ─── Función auxiliar: actualizar actualizada_en al insertar mensajes ─────────

create or replace function public.refrescar_conversacion()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  update public.conversaciones
  set actualizada_en = now()
  where id = new.conversacion_id;
  return new;
end;
$$;

drop trigger if exists trg_refrescar_conv on public.mensajes;
create trigger trg_refrescar_conv
  after insert on public.mensajes
  for each row execute function public.refrescar_conversacion();

notify pgrst, 'reload schema';
commit;

-- ─── Comprobaciones de instalación ───────────────────────────────────────────
select relname, relrowsecurity
from pg_class
where oid in (
  'public.conversaciones'::regclass,
  'public.mensajes'::regclass
);

select count(*) as conversaciones_total from public.conversaciones;
select count(*) as mensajes_total       from public.mensajes;
