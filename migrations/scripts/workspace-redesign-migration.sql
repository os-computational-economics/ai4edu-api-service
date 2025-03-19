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
ALTER TABLE ai_user_workspace ADD CONSTRAINT ai_user_workspace_pk PRIMARY KEY (workspace_id, user_id);

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

-- set workspace_admin to true for users who are creators
UPDATE ai_users
    SET workspace_admin=true
        WHERE user_id IN (SELECT DISTINCT created_by FROM ai_workspaces WHERE created_by IS NOT NULL);

-- commit the changes
COMMIT;