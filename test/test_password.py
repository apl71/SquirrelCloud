"""Password endpoint tests for session validation, password change flow, and input validation."""

import pytest
from uuid import uuid4

from test import client, app
from test_utils import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    login_and_assert_ok,
    parse_session_cookie,
)


def make_register_payload():
    """Create a unique user payload for password-change tests."""
    suffix = uuid4().hex[:8]
    return {
        "username": f"pw_user_{suffix}",
        "password": f"oldpw_{suffix}",
        "admin": "false",
        "email": f"pw_user_{suffix}@example.com",
    }


def register_user_as_admin(client, payload):
    """Register a fresh normal user through the admin API."""
    login_and_assert_ok(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    response = client.put("/api/register", json=payload)
    assert response.status_code == 200
    body = response.get_json()
    assert body["result"] == "OK"
    return response


def test_password_requires_valid_session(app):
    """Changing password without a valid session should fail."""
    fresh_client = app.test_client()
    response = fresh_client.post(
        "/api/password",
        json={
            "old_password": "anything",
            "new_password": "newpass123",
        },
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["result"] == "FAIL"
    assert body["message"] == "Your session is not valid."


def test_password_changes_successfully_with_correct_old_password(client, app):
    """A logged-in user should be able to change password with the correct old password."""
    payload = make_register_payload()
    register_user_as_admin(client, payload)

    user_client = app.test_client()
    login_and_assert_ok(user_client, payload["username"], payload["password"])

    new_password = payload["password"] + "_new"
    response = user_client.post(
        "/api/password",
        json={
            "old_password": payload["password"],
            "new_password": new_password,
        },
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["result"] == "OK"

    old_login_client = app.test_client()
    old_login_response = old_login_client.post(
        "/api/login",
        json={
            "username": payload["username"],
            "password": payload["password"],
        },
    )
    assert old_login_response.status_code == 200
    assert old_login_response.get_json()["result"] == "FAIL"

    new_login_client = app.test_client()
    new_login_response = new_login_client.post(
        "/api/login",
        json={
            "username": payload["username"],
            "password": new_password,
        },
    )
    assert new_login_response.status_code == 200
    assert new_login_response.get_json()["result"] == "OK"
    parse_session_cookie(new_login_response)


def test_password_rejects_wrong_old_password(client, app):
    """Changing password with a wrong old password should fail and leave the original password valid."""
    payload = make_register_payload()
    register_user_as_admin(client, payload)

    user_client = app.test_client()
    login_and_assert_ok(user_client, payload["username"], payload["password"])

    new_password = payload["password"] + "_new"
    response = user_client.post(
        "/api/password",
        json={
            "old_password": "definitely-wrong-old-password",
            "new_password": new_password,
        },
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["result"] == "FAIL"
    assert body["message"] == "Old password does not work."

    old_login_client = app.test_client()
    old_login_response = old_login_client.post(
        "/api/login",
        json={
            "username": payload["username"],
            "password": payload["password"],
        },
    )
    assert old_login_response.status_code == 200
    assert old_login_response.get_json()["result"] == "OK"
    parse_session_cookie(old_login_response)

    new_login_client = app.test_client()
    new_login_response = new_login_client.post(
        "/api/login",
        json={
            "username": payload["username"],
            "password": new_password,
        },
    )
    assert new_login_response.status_code == 200
    assert new_login_response.get_json()["result"] == "FAIL"


@pytest.mark.parametrize("missing_key", ["old_password", "new_password"])
def test_password_rejects_missing_required_fields(client, app, missing_key):
    """Password change should fail cleanly when required JSON fields are missing."""
    payload = make_register_payload()
    register_user_as_admin(client, payload)

    user_client = app.test_client()
    login_and_assert_ok(user_client, payload["username"], payload["password"])

    body = {
        "old_password": payload["password"],
        "new_password": payload["password"] + "_new",
    }
    body.pop(missing_key)

    response = user_client.post("/api/password", json=body)
    assert response.status_code in (200, 400, 415, 500)
    if response.is_json:
        assert response.get_json()["result"] == "FAIL"


@pytest.mark.parametrize(
    "content_type,data",
    [
        ("application/x-www-form-urlencoded", "old_password=a&new_password=b"),
        ("text/plain", "old_password=a,new_password=b"),
        (None, None),
    ],
)
def test_password_rejects_non_json_body(client, app, content_type, data):
    """Password change should not succeed when the body is not valid JSON."""
    payload = make_register_payload()
    register_user_as_admin(client, payload)

    user_client = app.test_client()
    login_and_assert_ok(user_client, payload["username"], payload["password"])

    kwargs = {}
    if content_type is not None:
        kwargs["content_type"] = content_type
    if data is not None:
        kwargs["data"] = data

    response = user_client.post("/api/password", **kwargs)
    assert response.status_code in (200, 400, 415, 500)
    if response.is_json:
        assert response.get_json()["result"] == "FAIL"


@pytest.mark.parametrize(
    "payload_builder",
    [
        lambda oldpw, newpw: {"old_password": 123, "new_password": newpw},
        lambda oldpw, newpw: {"old_password": oldpw, "new_password": ["x"]},
        lambda oldpw, newpw: {"old_password": {}, "new_password": None},
    ],
)
def test_password_rejects_wrong_field_types(client, app, payload_builder):
    """Password change should not succeed when old_password/new_password are not strings."""
    payload = make_register_payload()
    register_user_as_admin(client, payload)

    user_client = app.test_client()
    login_and_assert_ok(user_client, payload["username"], payload["password"])

    response = user_client.post(
        "/api/password",
        json=payload_builder(payload["password"], payload["password"] + "_new"),
    )
    assert response.status_code in (200, 400, 415, 500)
    if response.is_json:
        assert response.get_json()["result"] == "FAIL"


def test_password_rejects_json_null_body(client, app):
    """Password change should not succeed when JSON body is null."""
    payload = make_register_payload()
    register_user_as_admin(client, payload)

    user_client = app.test_client()
    login_and_assert_ok(user_client, payload["username"], payload["password"])

    response = user_client.post("/api/password", data="null", content_type="application/json")
    assert response.status_code in (200, 400, 415, 500)
    if response.is_json:
        assert response.get_json()["result"] == "FAIL"