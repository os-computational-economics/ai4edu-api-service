/*
    Pre-Migration Check Script
    --------------------------
    Due to a very legacy design history issue, there is a possibility that some user workspace relationships
    stored in the "workspace_role" JSON column in the ai_users table do not have corresponding records in the
    ai_workspaces and ai_user_workspace tables. This script is designed as a pre-migration check to ensure that 
    every workspace present in the JSON is properly recorded in the ai_workspaces table, and that the corresponding 
    user-workspace relationship exists in the ai_user_workspace table.

    For each user, the script:
      - Extracts each workspace and associated role from the workspace_role JSON.
      - Checks if the workspace exists in ai_workspaces; if not, it inserts a new record with default values.
      - Checks if the user-workspace relationship exists in ai_user_workspace; if not, it inserts the relationship.
      - Logs each insert action using RAISE NOTICE for tracking purposes.

    This operation is performed within a single transaction to maintain atomicity. This pre-migration script 
    clears out any inconsistencies before the actual migration process.
*/

BEGIN;

DO $$
DECLARE
    r RECORD;
    ws_item RECORD;
BEGIN
    -- Loop over each user in ai_users
    FOR r IN SELECT user_id, student_id, workspace_role FROM ai_users LOOP
        -- For each workspace in the JSON, iterate over its key/value pairs.
        FOR ws_item IN SELECT key, value FROM json_each_text(r.workspace_role) LOOP

            -- If the workspace does not exist in ai_workspaces, insert it.
            IF NOT EXISTS (
                SELECT 1
                FROM ai_workspaces
                WHERE workspace_id = ws_item.key
            ) THEN
                INSERT INTO ai_workspaces(workspace_id, workspace_name, workspace_password)
                VALUES (ws_item.key, ws_item.key, ws_item.key);
                RAISE NOTICE 'Inserted workspace % into ai_workspaces', ws_item.key;
            END IF;

            -- If the relationship does not exist in ai_user_workspace, insert it.
            IF NOT EXISTS (
                SELECT 1
                FROM ai_user_workspace
                WHERE workspace_id = ws_item.key
                  AND student_id = r.student_id
            ) THEN
                INSERT INTO ai_user_workspace(user_id, workspace_id, role, student_id)
                VALUES (r.user_id, ws_item.key, ws_item.value, r.student_id);
                RAISE NOTICE 'Inserted user_workspace relationship for user_id %, student_id %, workspace %', r.user_id, r.student_id, ws_item.key;
            END IF;
        END LOOP;
    END LOOP;
END
$$;

COMMIT;

-- actual migration starts
-- Script used for updating database for workspace redesign
BEGIN;

-- convert workspace_id to a UUID for all tables
    -- a lot of steps are required, will go through them one by one

-- create a temporary 'new_workspace_id' column in ai_workspaces to generate new UUIDs
ALTER TABLE ai_workspaces ADD COLUMN new_workspace_id UUID DEFAULT gen_random_uuid();

-- propogate new uuids to all other relevant tables
ALTER TABLE ai_user_workspace ADD COLUMN new_workspace_id UUID;
UPDATE ai_user_workspace AS uw
    SET new_workspace_id=(
        SELECT w.new_workspace_id FROM ai_workspaces AS w 
        WHERE w.workspace_id=uw.workspace_id);

ALTER TABLE ai_threads ADD COLUMN new_workspace_id UUID;
UPDATE ai_threads AS t
    SET new_workspace_id=(
        SELECT w.new_workspace_id FROM ai_workspaces AS w 
        WHERE w.workspace_id=t.workspace_id);

ALTER TABLE ai_agents ADD COLUMN new_workspace_id UUID;
UPDATE ai_agents AS a
    SET new_workspace_id=(
        SELECT w.new_workspace_id FROM ai_workspaces AS w 
        WHERE w.workspace_id=a.workspace_id);

-- update workspace_id references inside ai_users.workspace_role JSON field
UPDATE ai_users
    SET workspace_role = COALESCE((
        SELECT json_object_agg(w.new_workspace_id::TEXT, old_role.value)
        FROM ai_users u,
            json_each_text(u.workspace_role) AS old_role
        JOIN ai_workspaces w ON w.workspace_id::TEXT = old_role.key
        WHERE u.user_id = ai_users.user_id
    ), '{}'::json);

-- swap columns in all relevant tables
ALTER TABLE ai_workspaces DROP CONSTRAINT ai_workspaces_pk;
ALTER TABLE ai_workspaces RENAME COLUMN workspace_id TO old_workspace_id;
ALTER TABLE ai_workspaces RENAME COLUMN new_workspace_id TO workspace_id;
ALTER TABLE ai_workspaces ADD CONSTRAINT ai_workspaces_pk PRIMARY KEY (workspace_id);

ALTER TABLE ai_user_workspace DROP CONSTRAINT ai_user_workspace_pk;
ALTER TABLE ai_user_workspace RENAME COLUMN workspace_id TO old_workspace_id;
ALTER TABLE ai_user_workspace RENAME COLUMN new_workspace_id TO workspace_id;
-- note: the user_id is being replaced with the student_id in the pk as student_id is being phased out
-- It's true that we should phase out student ID. However, updating primary key here to 
-- user id will make the current way of adding students via CSV upload stop working.
ALTER TABLE ai_user_workspace ADD CONSTRAINT ai_user_workspace_pk PRIMARY KEY (workspace_id, student_id);

ALTER TABLE ai_threads RENAME COLUMN workspace_id TO old_workspace_id;
ALTER TABLE ai_threads RENAME COLUMN new_workspace_id TO workspace_id;

ALTER TABLE ai_agents RENAME COLUMN workspace_id TO old_workspace_id;
ALTER TABLE ai_agents RENAME COLUMN new_workspace_id TO workspace_id;

-- remove old workspace_id columns
ALTER TABLE ai_workspaces DROP COLUMN old_workspace_id;
ALTER TABLE ai_user_workspace DROP COLUMN old_workspace_id;
ALTER TABLE ai_threads DROP COLUMN old_workspace_id;
ALTER TABLE ai_agents DROP COLUMN old_workspace_id;

-- assign a workspace_join_code to all existing workspaces
-- ensure correct constraint is applied to workspace_join_code
ALTER TABLE ai_workspaces 
    ADD COLUMN workspace_join_code VARCHAR(8);

ALTER TABLE ai_workspaces
    ADD CONSTRAINT valid_join_code
        CHECK (workspace_join_code similar to '[0-9]{8}');

UPDATE ai_workspaces SET workspace_join_code=LPAD((floor(random() * 100000000)::TEXT), 8, '0') 
    WHERE workspace_join_code IS NULL;

-- add and remove required fields to ai_workspaces table
ALTER TABLE ai_workspaces 
    ADD COLUMN workspace_prompt TEXT;

ALTER TABLE ai_workspaces
    ADD COLUMN workspace_comment TEXT;

ALTER TABLE ai_workspaces
    ADD COLUMN created_by INTEGER;

ALTER TABLE ai_workspaces
    ADD FOREIGN KEY(created_by) REFERENCES ai_users(user_id);

ALTER TABLE ai_workspaces
    DROP COLUMN workspace_password;

-- add required field to ai_users table
-- as of now, I am assuming that these will just be set manually
ALTER TABLE ai_users
    ADD COLUMN workspace_admin BOOLEAN DEFAULT false;

-- fetch teachers for all workspaces
WITH teachers AS (
    SELECT
        uw.workspace_id,
        uw.user_id,
        uw.created_at,
        ROW_NUMBER() OVER (PARTITION BY uw.workspace_id ORDER BY uw.created_at ASC) AS row_num
    FROM ai_user_workspace AS uw
    JOIN ai_workspaces AS w ON uw.workspace_id=w.workspace_id
    WHERE uw.role='teacher'
)

-- update created_by based on the following criteria:
    -- no teacher -> set created_by to 3
    -- one teacher -> set created_by to teacher user_id
    -- multiple teachers -> set created_by to the first teacher added to the workspace
UPDATE ai_workspaces AS w
    SET created_by = COALESCE(
        (SELECT user_id FROM teachers AS t WHERE t.workspace_id=w.workspace_id AND t.row_num=1),
        3
    );

-- Remove uniqueness constraint on workspace name
ALTER TABLE ai_workspaces DROP CONSTRAINT ai_workspaces_pk_2;

-- set workspace_admin to true for users who are creators
UPDATE ai_users
    SET workspace_admin=true
        WHERE user_id IN (SELECT DISTINCT created_by FROM ai_workspaces WHERE created_by IS NOT NULL);

-- commit the changes
COMMIT;
