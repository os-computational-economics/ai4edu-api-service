-- CREATE DATABASE ai4edu_local
--     WITH
--     OWNER = postgres
--     ENCODING = 'UTF8'
--     LC_COLLATE = 'en_US.utf8'
--     LC_CTYPE = 'en_US.utf8'
--     LOCALE_PROVIDER = 'libc'
--     TABLESPACE = pg_default
--     CONNECTION LIMIT = -1
--     IS_TEMPLATE = False;

create table db_version
(
version varchar(5) not null
constraint db_version_pk
primary key
);
  
create table ai_agents
(
agent_id uuid not null
constraint ai_agents_pk
primary key,
created_at timestamp default now() not null,
agent_name varchar(255) not null,
course_id varchar(31),
creator varchar(16),
updated_at timestamp default now() not null,
voice boolean default false not null,
status integer default 1 not null,
allow_model_choice boolean default true not null,
model varchar(16)
);