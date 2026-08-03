-- Nexo IA — esquema de Supabase.
--
-- Uso: pegar en el SQL Editor de un proyecto de Supabase (o correr con
-- `supabase db push` si usás la CLI). El backend funciona sin este esquema
-- (todo cae en el store en memoria), pero sin él no se puede listar corridas
-- anteriores ni conversaciones después de un reinicio del backend.

create table if not exists runs (
    id bigint generated always as identity primary key,
    run_id text not null unique,
    nombre_archivo text not null,
    creado_en timestamptz not null default now(),
    validacion jsonb not null,
    resumen jsonb not null,
    hallazgos jsonb not null
);

create index if not exists idx_runs_creado_en on runs (creado_en desc);

create table if not exists conversaciones (
    id bigint generated always as identity primary key,
    run_id text not null references runs (run_id) on delete cascade,
    pregunta text not null,
    respuesta jsonb not null,
    creado_en timestamptz not null default now()
);

create index if not exists idx_conversaciones_run_id on conversaciones (run_id);

create table if not exists anotaciones (
    id bigint generated always as identity primary key,
    run_id text not null references runs (run_id) on delete cascade,
    texto text not null,
    creado_en timestamptz not null default now()
);

create index if not exists idx_anotaciones_run_id on anotaciones (run_id);

-- Bucket de Storage para los CSV subidos (crear desde el dashboard de Supabase
-- Storage con este mismo nombre, o descomentar si tenés la extensión pg_net /
-- permisos para crearlo por SQL en tu plan):
-- insert into storage.buckets (id, name, public) values ('csv-uploads', 'csv-uploads', false)
-- on conflict (id) do nothing;

-- RLS: MVP académico sin autenticación — se deja todo abierto a la clave de
-- servicio (service_role) que usa el backend. Si en algún momento se agrega
-- autenticación de usuarios, hay que habilitar RLS acá y filtrar por usuario.
alter table runs enable row level security;
alter table conversaciones enable row level security;
alter table anotaciones enable row level security;

create policy "service_role_full_access_runs" on runs
    for all to service_role using (true) with check (true);
create policy "service_role_full_access_conversaciones" on conversaciones
    for all to service_role using (true) with check (true);
create policy "service_role_full_access_anotaciones" on anotaciones
    for all to service_role using (true) with check (true);
