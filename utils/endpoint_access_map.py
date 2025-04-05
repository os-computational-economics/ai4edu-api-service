# Copyright (c) 2024.
"""Access endpoint map"""

from typing import Literal

PersonType = Literal["student", "teacher", "system_admin", "workspace_admin"]
AccessMap = dict[str, dict[PersonType, bool]]

endpoint_access_map: AccessMap = {
    "/ai4edu_testing": {
        "student": False,
        "teacher": False,
        "system_admin": True,
        "workspace_admin": False,
    },
    "/agent/{agent_id}": {
        "student": True,
        "teacher": True,
        "system_admin": True,
        "workspace_admin": False,
    },
    "/agent/get/{agent_id}": {
        "student": True,
        "teacher": True,
        "system_admin": True,
        "workspace_admin": False,
    },  # student get agent by id
    "/agents/add_agent": {
        "student": False,
        "teacher": True,
        "system_admin": True,
        "workspace_admin": False,
    },
    "/agents/delete_agent": {
        "student": False,
        "teacher": True,
        "system_admin": True,
        "workspace_admin": False,
    },
    "/agents/update_agent": {
        "student": False,
        "teacher": True,
        "system_admin": True,
        "workspace_admin": False,
    },
    "/agents/agents": {
        "student": True,
        "teacher": True,
        "system_admin": True,
        "workspace_admin": False,
    },
    "/agents/agent/{agent_id}": {
        "student": True,
        "teacher": True,
        "system_admin": True,
        "workspace_admin": False,
    },
    "/feedback/rating": {
        "student": True,
        "teacher": True,
        "system_admin": True,
        "workspace_admin": False,
    },
    "/threads/get_thread/{thread_id}": {
        "student": True,
        "teacher": True,
        "system_admin": True,
        "workspace_admin": False,
    },
    "/threads/get_thread_list": {
        "student": True,
        "teacher": True,
        "system_admin": True,
        "workspace_admin": False,
    },
    "/sso": {
        "student": True,
        "teacher": True,
        "system_admin": True,
        "workspace_admin": False,
    },
    "/stream_chat": {
        "student": True,
        "teacher": True,
        "system_admin": True,
        "workspace_admin": False,
    },
    "/get_tts_file": {
        "student": True,
        "teacher": True,
        "system_admin": True,
        "workspace_admin": False,
    },
    "/get_temp_stt_auth_code": {
        "student": True,
        "teacher": True,
        "system_admin": True,
        "workspace_admin": False,
    },
    "/get_new_thread": {
        "student": True,
        "teacher": True,
        "system_admin": True,
        "workspace_admin": False,
    },
    "/access/get_user_list": {
        "student": False,
        "teacher": True,
        "system_admin": True,
        "workspace_admin": False,
    },
    # workspace endpoints
    "/workspace/create_workspace": {
        "student": False,
        "teacher": True,  # Assumedly, this endpoint should be available to teachers
        "system_admin": True,
        "workspace_admin": True,
    },
    "/workspace/set_workspace_status": {
        "student": False,
        "teacher": True,
        "system_admin": True,
        "workspace_admin": True,
    },
    "/workspace/add_users_via_csv": {
        "student": False,
        "teacher": True,
        "system_admin": True,
        "workspace_admin": True,
    },
    "/workspace/add_users_json": {
        "student": False,
        "teacher": True,
        "system_admin": True,
        "workspace_admin": True,
    },
    "/workspace/student_join_workspace": {
        "student": True,
        "teacher": True,
        "system_admin": True,
        "workspace_admin": True,
    },
    "/workspace/delete_user_from_workspace": {
        "student": False,
        "teacher": True,
        "system_admin": True,
        "workspace_admin": True,
    },
    "/workspace/set_user_role_with_user_id": {
        "student": False,
        "teacher": False,
        "system_admin": True,
        "workspace_admin": True,
    },
    "/workspace/get_workspace_list": {
        "student": False,
        "teacher": False,
        "system_admin": True,
        "workspace_admin": True,
    },
    "/workspace/set_workspace_admin_role": {
        "student": False,
        "teacher": False,
        "system_admin": False,
        "workspace_admin": True,
    },
    "/workspace/delete_workspace/{workspace}": {
        "student": False,
        "teacher": False,
        "system_admin": True,
        "workspace_admin": True,
    },
    "/workspace/get_user_workspace_details": {
        "student": False,
        "teacher": False,
        "system_admin": True,
        "workspace_admin": True,
    },
    "/workspace/edit_workspace": {
        "student": False,
        "teacher": False,
        "system_admin": True,
        "workspace_admin": True,
    },
    # testing endpoints
    "/test_query": {
        "student": True,
        "teacher": True,
        "system_admin": True,
        "workspace_admin": False,
    },
    "/test_query/history": {
        "student": True,
        "teacher": True,
        "system_admin": True,
        "workspace_admin": False,
    },
    "/test_query/clear_history": {
        "student": True,
        "teacher": True,
        "system_admin": True,
        "workspace_admin": False,
    },
    "/upload_file": {
        "student": True,
        "teacher": True,
        "system_admin": True,
        "workspace_admin": False,
    },
    "/get_presigned_url_for_file": {
        "student": True,
        "teacher": True,
        "system_admin": True,
        "workspace_admin": False,
    },
    "/ping": {
        "student": True,
        "teacher": True,
        "system_admin": True,
        "workspace_admin": False,
    },
    "/openapi.json": {
        "student": False,
        "teacher": False,
        "system_admin": True,
        "workspace_admin": False,
    },
}
