# Copyright (c) 2024.
# -*-coding:utf-8 -*-
"""
@file: endpoint_access_map.py
@author: Jerry(Ruihuang)Yang
@email: rxy216@case.edu
@time: 5/24/24 19:54
"""
endpoint_access_map = {
    "/agent/{agent_id}": {"student": True, "teacher": True, "admin": True},
    "/agent/get/{agent_id}": {"student": True, "teacher": True, "admin": True},  # student get agent by id
    "/agents/add_agent": {"student": False, "teacher": True, "admin": True},
    "/agents/delete_agent": {"student": False, "teacher": True, "admin": True},
    "/agents/update_agent": {"student": False, "teacher": True, "admin": True},
    "/agents/agents": {"student": False, "teacher": True, "admin": True},
    "/agents/agent/{agent_id}": {"student": False, "teacher": True, "admin": True},
    "/threads/get_thread/{thread_id}": {"student": False, "teacher": True, "admin": True},
    "/threads/get_thread_list": {"student": False, "teacher": True, "admin": True},
    "/sso": {"student": True, "teacher": True, "admin": True},
    "/stream_chat": {"student": True, "teacher": True, "admin": True},
    "/get_tts_file": {"student": True, "teacher": True, "admin": True},
    "/get_temp_stt_auth_code": {"student": True, "teacher": True, "admin": True},
    "/get_new_thread": {"student": True, "teacher": True, "admin": True},
    "/access/get_user_list": {"student": False, "teacher": True, "admin": True},
    # workspace endpoints
    "/workspace/create_workspace": {"student": False, "teacher": False, "admin": True},
    "/workspace/add_users_via_csv": {"student": False, "teacher": True, "admin": True},
    "/workspace/student_join_workspace": {"student": True, "teacher": True, "admin": True},
    "/workspace/delete_user_from_workspace": {"student": False, "teacher": True, "admin": True},
    "/workspace/set_user_role": {"student": False, "teacher": True, "admin": True},
    "/workspace/set_user_role_with_student_id": {"student": False, "teacher": True, "admin": True},
    "/workspace/get_workspace_list": {"student": False, "teacher": False, "admin": True},
    # testing endpoints
    "/test_query": {"student": True, "teacher": True, "admin": True},
    "/test_query/history": {"student": True, "teacher": True, "admin": True},
    "/test_query/clear_history": {"student": True, "teacher": True, "admin": True},
    "/upload_file": {"student": True, "teacher": True, "admin": True},
    "/get_presigned_url_for_file": {"student": True, "teacher": True, "admin": True},
    "/ping": {"student": True, "teacher": True, "admin": True},
}
