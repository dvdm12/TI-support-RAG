-- Tickets de demostración editables desde la vista "Tickets" del frontend.
-- Ejecutar en el SQL Editor del mismo proyecto de Supabase. No modifica tablas
-- existentes. Idempotente: se puede volver a ejecutar sin error.
--
-- Reglas:
--   - Cualquiera (también el backend y el servidor MCP con la clave publishable)
--     puede LEER los tickets: son datos ficticios de demostración.
--   - Cualquier usuario con sesión iniciada puede cambiar estado y detalle
--     (acceso libre a la vista). Sin sesión no se puede modificar nada.
--   - Nadie puede crear ni borrar tickets desde la API.
begin;

-- ─── Tabla: tickets ──────────────────────────────────────────────────────────
create table if not exists public.tickets (
  codigo          text        primary key check (codigo ~ '^TI-[0-9]{4}$'),
  estado          text        not null check (estado in (
                    'Abierto', 'Asignado', 'En revisión', 'Pendiente de información',
                    'Pendiente de aprobación', 'Escalado', 'Resuelto', 'Cerrado')),
  detalle         text        not null check (length(btrim(detalle)) between 1 and 500),
  actualizado_en  timestamptz not null default now(),
  actualizado_por uuid        references auth.users(id) on delete set null
);

alter table public.tickets enable row level security;
revoke all on public.tickets from public, anon, authenticated;
grant select on public.tickets to anon, authenticated;
-- Solo estas dos columnas son editables; el resto lo fija el trigger.
grant update (estado, detalle) on public.tickets to authenticated;

drop policy if exists tickets_select_todos on public.tickets;
create policy tickets_select_todos on public.tickets
  for select to anon, authenticated
  using (true);

drop policy if exists tickets_update_soporte on public.tickets;
drop policy if exists tickets_update_autenticados on public.tickets;
create policy tickets_update_autenticados on public.tickets
  for update to authenticated
  using (true)
  with check (true);

-- Quién y cuándo se registra en el servidor, no lo decide el cliente.
create or replace function public.tickets_auditar()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.actualizado_en  := now();
  new.actualizado_por := auth.uid();
  return new;
end;
$$;

drop trigger if exists trg_tickets_auditar on public.tickets;
create trigger trg_tickets_auditar
  before update on public.tickets
  for each row execute function public.tickets_auditar();

-- ─── Datos iniciales (los mismos que backend/api/tickets_demo.json) ──────────
insert into public.tickets (codigo, estado, detalle) values
  ('TI-1001', 'En revisión', 'Soporte está revisando la conexión del equipo.'),
  ('TI-1002', 'Pendiente de información', 'Soporte necesita el mensaje de error de la aplicación.'),
  ('TI-1003', 'Resuelto', 'Se restableció el acceso al portal de pruebas.'),
  ('TI-1004', 'Abierto', 'Se registró el reporte de la impresora del segundo piso; pendiente de asignación.'),
  ('TI-1005', 'Asignado', 'Un técnico revisará el equipo que no enciende en el puesto de recepción.'),
  ('TI-1006', 'En revisión', 'Seguridad está analizando el correo sospechoso reportado por el usuario.'),
  ('TI-1007', 'Pendiente de aprobación', 'El acceso a la carpeta compartida requiere la autorización del responsable del área.'),
  ('TI-1008', 'Escalado', 'La falla de la aplicación de nómina se escaló al proveedor del software.'),
  ('TI-1009', 'Resuelto', 'Se restableció la contraseña del correo corporativo tras verificar la identidad.'),
  ('TI-1010', 'Cerrado', 'El usuario confirmó que la conexión Wi-Fi funciona correctamente.')
on conflict (codigo) do nothing;

commit;
