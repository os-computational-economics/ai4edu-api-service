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

insert into db_version (version) values ('dev');

create table ai_agents
(
    agent_id           uuid                         not null
        constraint ai_agents_pk
            primary key,
    created_at         timestamp default now()      not null,
    agent_name         varchar(255)                 not null,
    workspace_id       uuid                         not null,
    creator            varchar(16),
    updated_at         timestamp default now()      not null,
    voice              boolean   default false      not null,
    status             integer   default 1          not null,
    allow_model_choice boolean   default true       not null,
    model              varchar(16),
    agent_files        json      default '{}'::json not null
);

comment on column ai_agents.status is '1-active, 0-inactive, 2-deleted';

comment on column ai_agents.agent_files is '{"file_id":"file_name"}';

create table ai_files
(
    file_id            uuid                    not null,
    file_name          varchar                 not null,
    file_desc          varchar,
    file_type          varchar(63)             not null,
    file_ext           varchar(15),
    file_status        integer   default 1,
    chunking_separator varchar(15),
    created_at         timestamp default now() not null
);

comment on column ai_files.file_type is 'mime type of the file';

comment on column ai_files.file_ext is 'extension of file, without dot';

comment on column ai_files.file_status is ' 0 is deleted';

create table ai_users
(
    user_id         serial
        constraint ai_users_pk
            unique,
    first_name      varchar(60)           not null,
    last_name       varchar(60)           not null,
    email           varchar(150)          not null
        unique,
    student_id      varchar(20)           not null,
    workspace_role  json                  not null,
    school_id       integer               not null,
    last_login      timestamp,
    create_at       timestamp,
    system_admin    boolean default false not null,
    workspace_admin boolean default false not null,
    primary key (user_id, email)
);

create table ai_refresh_tokens
(
    token_id           uuid                    not null
        primary key,
    user_id            integer                 not null
        constraint ai_refresh_tokens_ai_users_user_id_fk
            references ai_users (user_id),
    token              uuid                    not null
        unique,
    created_at         timestamp default now() not null,
    expire_at          timestamp               not null,
    issued_token_count integer   default 0     not null
);

create table ai_threads
(
    thread_id    uuid                                          not null
        constraint ai_threads_pk
            primary key,
    student_id   varchar(16),
    created_at   timestamp   default now()                     not null,
    agent_id     uuid                                          not null
        constraint ai_threads_ai_agents_agent_id_fk
            references ai_agents,
    user_id      integer     default 1                         not null,
    workspace_id uuid                                          not null,
    agent_name   varchar(256)
);

create table ai_user_workspace
(
    user_id      integer,
    workspace_id uuid                                             not null,
    role         varchar(16) default 'pending'::character varying not null,
    created_at   timestamp   default now()                        not null,
    updated_at   timestamp,
    student_id   varchar(16)                                      not null,
    constraint ai_user_workspace_pk
        primary key (workspace_id, student_id)
);

create table ai_workspaces
(
    workspace_id        uuid                 not null
        constraint ai_workspaces_pk
            primary key,
    workspace_name      varchar(64)          not null,
    workspace_prompt    text,
    workspace_comment   text,
    created_by integer                       not null
        references ai_users(user_id),
    workspace_join_code varchar(8)           not null
        unique
            constraint valid_join_code
                check (workspace_join_code similar to '[0-9]{8}'),
    status             integer default 1     not null,
    school_id          integer default 0     not null
);

create table ai_feedback
(
    feedback_id        serial
        constraint ai_feedback_pk
            primary key,
    user_id            integer               not null
        constraint ai_feedback_ai_users_user_id_fk
            references ai_users (user_id),
    thread_id          uuid                  not null
        constraint ai_feedback_ai_threads_thread_id_fk
            references ai_threads (thread_id),
    message_id         varchar(256),
    feedback_time      timestamp             default now(),
    rating_format      integer               not null,
    rating             integer               not null,
    comments           text,
    constraint chk_rating_validity check (
        (rating_format = 2 and rating in (0, 1)) or
        (rating_format = 5 and rating between 1 and 5) or
        (rating_format = 10 and rating between 1 and 10)
    )
)
