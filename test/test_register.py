"""Register endpoint tests for authentication/authorization and basic user bootstrap behavior."""

import pytest
from uuid import uuid4

from test import client, app, get_connection
from test_utils import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    ALICE_PASSWORD,
    ALICE_USERNAME,
    BOB_PASSWORD,
    BOB_USERNAME,
    login_and_assert_ok,
    parse_session_cookie
)


def make_register_payload(is_admin="false"):
    """Create a unique register payload so tests do not conflict with each other."""
    suffix = uuid4().hex[:8]
    return {
        "username": f"testuser_{suffix}",
        "password": f"pw_{suffix}",
        "admin": is_admin,
        "email": f"testuser_{suffix}@example.com",
    }

def get_user_uuid(username):
    """Return the user UUID for a username, or None if it does not exist."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT uuid FROM AppUser WHERE username = %s", (username,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else None

def get_user_uuid_by_email(email):
    """Return the user UUID for an email, or None if it does not exist."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT uuid FROM AppUser WHERE email = %s", (email,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else None

def user_path_exists(username, path):
    """Check whether a path exists in the File table for the given user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 1
        FROM File
        WHERE owner_uuid = (SELECT uuid FROM AppUser WHERE username = %s)
          AND path = %s
        LIMIT 1
        """,
        (username, path),
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row is not None

def test_register_requires_valid_session(client):
    """Unauthenticated users should not be able to create new users."""
    payload = make_register_payload()
    response = client.put("/api/register", json=payload)
    assert response.status_code == 200
    body = response.get_json()
    assert body["result"] == "FAIL"
    assert body["message"] == "Your session is not valid."
    assert get_user_uuid(payload["username"]) is None


def test_register_requires_admin_privileges(client):
    """A normal logged-in user should not be able to create new users."""
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)
    payload = make_register_payload()
    response = client.put("/api/register", json=payload)
    assert response.status_code == 200
    body = response.get_json()
    assert body["result"] == "FAIL"
    assert body["message"] == "You are not administrator."
    assert get_user_uuid(payload["username"]) is None

@pytest.mark.parametrize("missing_key", ["username", "password", "admin", "email"])
def test_register_rejects_missing_required_fields(client, missing_key):
    """Admin register requests should fail cleanly when required JSON fields are missing."""
    login_and_assert_ok(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    payload = make_register_payload()
    removed_username = payload["username"]
    payload.pop(missing_key)

    response = client.put("/api/register", json=payload)
    assert response.status_code in (200, 400, 415, 500)
    assert get_user_uuid(removed_username) is None
    if response.is_json:
        assert response.get_json()["result"] == "FAIL"


@pytest.mark.parametrize("content_type,data", [
    ("application/x-www-form-urlencoded", "username=a&password=b&admin=false&email=a@example.com"),
    ("text/plain", "username=a,password=b,admin=false,email=a@example.com"),
    (None, None),
])
def test_register_rejects_non_json_body(client, content_type, data):
    """Admin register requests should not succeed when the body is not valid JSON."""
    login_and_assert_ok(client, ADMIN_USERNAME, ADMIN_PASSWORD)

    kwargs = {}
    if content_type is not None:
        kwargs["content_type"] = content_type
    if data is not None:
        kwargs["data"] = data

    response = client.put("/api/register", **kwargs)
    assert response.status_code in (200, 400, 415, 500)
    if response.is_json:
        assert response.get_json()["result"] == "FAIL"


@pytest.mark.parametrize("payload", [
    {"username": 123, "password": "pw", "admin": "false", "email": "bad1@example.com"},
    {"username": "badtype_user", "password": ["pw"], "admin": "false", "email": "bad2@example.com"},
    {"username": "badtype_user2", "password": "pw", "admin": True, "email": "bad3@example.com"},
    {"username": "badtype_user3", "password": "pw", "admin": "false", "email": None},
])
def test_register_rejects_wrong_field_types(client, payload):
    """Admin register requests should not succeed when field types are invalid."""
    login_and_assert_ok(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    username = payload.get("username") if isinstance(payload.get("username"), str) else None

    response = client.put("/api/register", json=payload)
    assert response.status_code in (200, 400, 415, 500)
    if username is not None:
        assert get_user_uuid(username) is None
    if response.is_json:
        assert response.get_json()["result"] == "FAIL"

def test_admin_can_register_normal_user_and_create_default_directories(client):
    """An admin should be able to create a normal user, root directory, and recycle directory."""
    login_and_assert_ok(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    payload = make_register_payload(is_admin="false")
    response = client.put("/api/register", json=payload)
    assert response.status_code == 200
    body = response.get_json()
    assert body["result"] == "OK"

    assert get_user_uuid(payload["username"]) is not None
    assert user_path_exists(payload["username"], "/")
    assert user_path_exists(payload["username"], "/recycle")


def test_admin_can_register_admin_user(client):
    """An admin should be able to create another admin account when admin='true'."""
    login_and_assert_ok(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    payload = make_register_payload(is_admin="true")
    response = client.put("/api/register", json=payload)
    assert response.status_code == 200
    body = response.get_json()
    assert body["result"] == "OK"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM AppUser WHERE username = %s", (payload["username"],))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    assert row is not None
    assert row[0] == "ROLE_ADMIN"

def test_register_admin_field_semantics_non_true_values_create_normal_user(client):
    """Only admin='true' should create an admin; other string values should create a normal user."""
    login_and_assert_ok(client, ADMIN_USERNAME, ADMIN_PASSWORD)

    for admin_value in ("false", "TRUE", "yes"):
        payload = make_register_payload(is_admin=admin_value)
        response = client.put("/api/register", json=payload)
        assert response.status_code == 200
        body = response.get_json()
        assert body["result"] == "OK"

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM AppUser WHERE username = %s", (payload["username"],))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        assert row is not None
        assert row[0] == "ROLE_USER"


def test_newly_registered_admin_can_login_and_register_another_user(client, app):
    """A newly registered admin should be able to log in and use the register endpoint."""
    login_and_assert_ok(client, ADMIN_USERNAME, ADMIN_PASSWORD)

    new_admin_payload = make_register_payload(is_admin="true")
    register_admin_response = client.put("/api/register", json=new_admin_payload)
    assert register_admin_response.status_code == 200
    assert register_admin_response.get_json()["result"] == "OK"

    fresh_client = app.test_client()
    login_and_assert_ok(fresh_client, new_admin_payload["username"], new_admin_payload["password"])

    child_payload = make_register_payload(is_admin="false")
    register_child_response = fresh_client.put("/api/register", json=child_payload)
    assert register_child_response.status_code == 200
    assert register_child_response.get_json()["result"] == "OK"
    assert get_user_uuid(child_payload["username"]) is not None

def test_failed_register_does_not_leave_directory_residue(client):
    """A failed register attempt should not leave root/recycle directory records behind."""
    login_and_assert_ok(client, ADMIN_USERNAME, ADMIN_PASSWORD)

    first_payload = make_register_payload()
    first_response = client.put("/api/register", json=first_payload)
    assert first_response.status_code == 200
    assert first_response.get_json()["result"] == "OK"

    second_payload = make_register_payload()
    second_payload["email"] = first_payload["email"]
    second_response = client.put("/api/register", json=second_payload)
    assert second_response.status_code == 200
    if second_response.is_json:
        assert second_response.get_json()["result"] == "FAIL"

    assert get_user_uuid(second_payload["username"]) is None
    assert not user_path_exists(second_payload["username"], "/")
    assert not user_path_exists(second_payload["username"], "/recycle")

def test_register_rejects_duplicate_email(client):
    """Registering a second user with an existing email should fail."""
    login_and_assert_ok(client, ADMIN_USERNAME, ADMIN_PASSWORD)

    first_payload = make_register_payload()
    first_response = client.put("/api/register", json=first_payload)
    assert first_response.status_code == 200
    assert first_response.get_json()["result"] == "OK"

    second_payload = make_register_payload()
    second_payload["email"] = first_payload["email"]
    second_response = client.put("/api/register", json=second_payload)
    assert second_response.status_code == 200
    if second_response.is_json:
        assert second_response.get_json()["result"] == "FAIL"

    assert get_user_uuid(second_payload["username"]) is None
    assert get_user_uuid_by_email(first_payload["email"]) is not None

def test_registered_user_can_login(client, app):
    """A newly registered user should be able to log in with the provided credentials."""
    login_and_assert_ok(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    payload = make_register_payload(is_admin="false")

    register_response = client.put("/api/register", json=payload)
    assert register_response.status_code == 200
    assert register_response.get_json()["result"] == "OK"

    fresh_client = app.test_client()
    login_response = fresh_client.post(
        "/api/login",
        json={
            "username": payload["username"],
            "password": payload["password"],
        },
    )
    assert login_response.status_code == 200
    assert login_response.get_json()["result"] == "OK"
    parse_session_cookie(login_response)

def test_register_rejects_duplicate_username(client):
    """Creating the same username twice should fail on the second attempt."""
    login_and_assert_ok(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    payload = make_register_payload()

    first_response = client.put("/api/register", json=payload)
    assert first_response.status_code == 200
    assert first_response.get_json()["result"] == "OK"

    second_response = client.put("/api/register", json=payload)
    assert second_response.status_code == 200
    body = second_response.get_json()
    assert body["result"] == "FAIL"
    assert body["message"] == "Username is occupied. Try another!"