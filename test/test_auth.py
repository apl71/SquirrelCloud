"""Authentication/session tests for login, logout, and multi-session behavior."""

import pytest
from test import client, app
from test_utils import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    ALICE_PASSWORD,
    ALICE_USERNAME,
    BOB_PASSWORD,
    BOB_USERNAME,
    assert_redirects_to_login,
    login_and_assert_ok,
    parse_session_cookie,
)

# --- Basic login tests -----------------------------------------------------

TEST_VEC = [
    (ADMIN_USERNAME, ADMIN_PASSWORD, "OK"),
    (ALICE_USERNAME, ALICE_PASSWORD, "OK"),
    (BOB_USERNAME, BOB_PASSWORD, "OK"),
    (ADMIN_USERNAME, "Admin@123", "FAIL"),
    (ALICE_USERNAME, "wrong-password", "FAIL"),
    ("admin' or '1'='1", "root' or 1=1 -- # ", "FAIL"),              # simple sql injection
    ("", "", "FAIL"),                                                # empty username or password
    (ADMIN_USERNAME, "", "FAIL"),
    ("", ADMIN_PASSWORD, "FAIL"),
    (ADMIN_USERNAME * 999999, ADMIN_PASSWORD * 999999, "FAIL"),      # overflow/extreme input
]


@pytest.mark.parametrize("username,password,expected_result", TEST_VEC)
def test_login(client, username, password, expected_result):
    """Login should succeed for valid credentials and fail without setting a session cookie otherwise."""
    response = client.post(
        "/api/login",
        json={
            "username": username,
            "password": password,
        },
    )
    assert response.status_code == 200, "Response is not 200 OK"

    result = response.get_json()["result"]
    assert result == expected_result, f"Expected {expected_result}, but got {result}"

    if result == "OK":
        parse_session_cookie(response)
    else:
        assert "Set-Cookie" not in response.headers, "Session cookie is set"


# --- Login input-validation tests -----------------------------------------

def test_login_rejects_missing_json_fields(client):
    """Login should fail cleanly when required JSON fields are missing."""
    test_bodies = [
        {},
        {"username": ADMIN_USERNAME},
        {"password": ADMIN_PASSWORD},
    ]

    for body in test_bodies:
        response = client.post("/api/login", json=body)
        assert "Set-Cookie" not in response.headers
        assert response.status_code in (200, 400, 415, 500)
        if response.is_json:
            assert response.get_json()["result"] == "FAIL"


def test_login_allows_extra_json_fields_if_required_fields_are_valid(client):
    """Login should still succeed when extra JSON fields are present but required fields are valid."""
    response = client.post(
        "/api/login",
        json={
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD,
            "extra": "ignored",
        },
    )
    assert response.status_code == 200
    assert response.get_json()["result"] == "OK"
    parse_session_cookie(response)


@pytest.mark.parametrize(
    "content_type,data",
    [
        ("application/x-www-form-urlencoded", "username=admin&password=admin"),
        ("text/plain", "username=admin,password=admin"),
        (None, None),
    ],
)
def test_login_rejects_non_json_body(client, content_type, data):
    """Login should not succeed when the request body is not valid JSON."""
    kwargs = {}
    if content_type is not None:
        kwargs["content_type"] = content_type
    if data is not None:
        kwargs["data"] = data

    response = client.post("/api/login", **kwargs)
    assert "Set-Cookie" not in response.headers
    assert response.status_code in (200, 400, 415, 500)
    if response.is_json:
        assert response.get_json()["result"] == "FAIL"


@pytest.mark.parametrize(
    "payload",
    [
        {"username": 123, "password": ADMIN_PASSWORD},
        {"username": ADMIN_USERNAME, "password": ["x"]},
        {"username": {}, "password": None},
    ],
)
def test_login_rejects_wrong_field_types(client, payload):
    """Login should not succeed when username/password are not strings."""
    response = client.post("/api/login", json=payload)
    assert "Set-Cookie" not in response.headers
    assert response.status_code in (200, 400, 415, 500)
    if response.is_json:
        assert response.get_json()["result"] == "FAIL"


def test_login_rejects_json_null_body(client):
    """Login should not succeed when JSON body is null."""
    response = client.post("/api/login", data="null", content_type="application/json")
    assert "Set-Cookie" not in response.headers
    assert response.status_code in (200, 400, 415, 500)
    if response.is_json:
        assert response.get_json()["result"] == "FAIL"


# --- Session-status tests --------------------------------------------------

def test_session_status_redirects_without_session(app):
    """Unauthenticated requests to session_status should redirect to the login page."""
    fresh_client = app.test_client()
    response = fresh_client.get("/api/session_status", follow_redirects=False)
    assert_redirects_to_login(response)


def test_session_status_ok_after_login(client):
    """A valid login session should make /api/session_status return OK."""
    login_and_assert_ok(client, ADMIN_USERNAME, ADMIN_PASSWORD)

    status_response = client.get("/api/session_status")
    assert status_response.status_code == 200
    assert status_response.get_json()["result"] == "OK"


# --- Logout tests ----------------------------------------------------------

def test_logout_invalidates_current_session(client):
    """Logging out should invalidate the current client's session."""
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    status_response = client.get("/api/session_status")
    assert status_response.status_code == 200
    assert status_response.get_json()["result"] == "OK"

    logout_response = client.delete("/api/logout")
    assert logout_response.status_code == 200
    assert logout_response.get_json()["result"] == "OK"

    status_after_logout = client.get("/api/session_status", follow_redirects=False)
    assert_redirects_to_login(status_after_logout)

def test_logout_without_session_is_handled_gracefully(app):
    """Calling logout without a session cookie should not crash the endpoint."""
    fresh_client = app.test_client()
    response = fresh_client.delete("/api/logout")
    assert response.status_code == 200
    assert response.get_json()["result"] == "OK"


def test_logout_with_fake_session_is_handled_gracefully(app):
    """Calling logout with a fake session cookie should not crash the endpoint."""
    fresh_client = app.test_client()
    fresh_client.set_cookie("session", "fake-session-token")
    response = fresh_client.delete("/api/logout")
    assert response.status_code == 200
    assert response.get_json()["result"] == "OK"

# --- Multi-session behavior tests -----------------------------------------

def test_repeated_login_creates_distinct_sessions_and_both_remain_valid(app):
    """Repeated login for the same user should create distinct valid sessions."""
    client_a = app.test_client()
    client_b = app.test_client()

    _, session_a = login_and_assert_ok(client_a, BOB_USERNAME, BOB_PASSWORD)
    _, session_b = login_and_assert_ok(client_b, BOB_USERNAME, BOB_PASSWORD)

    assert session_a != session_b, "Repeated login should generate a new session token"

    status_a = client_a.get("/api/session_status")
    assert status_a.status_code == 200
    assert status_a.get_json()["result"] == "OK"

    status_b = client_b.get("/api/session_status")
    assert status_b.status_code == 200
    assert status_b.get_json()["result"] == "OK"


def test_logout_only_removes_current_session(app):
    """Logging out one session should not invalidate another concurrent session of the same user."""
    client_a = app.test_client()
    client_b = app.test_client()

    login_and_assert_ok(client_a, ADMIN_USERNAME, ADMIN_PASSWORD)
    login_and_assert_ok(client_b, ADMIN_USERNAME, ADMIN_PASSWORD)

    logout_a = client_a.delete("/api/logout")
    assert logout_a.status_code == 200
    assert logout_a.get_json()["result"] == "OK"

    status_a = client_a.get("/api/session_status", follow_redirects=False)
    assert_redirects_to_login(status_a)

    status_b = client_b.get("/api/session_status")
    assert status_b.status_code == 200
    assert status_b.get_json()["result"] == "OK"