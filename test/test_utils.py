"""Shared test helpers and constants for API tests."""

from http.cookies import SimpleCookie


ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"

ALICE_USERNAME = "alice"
ALICE_PASSWORD = "alice123"

BOB_USERNAME = "bob"
BOB_PASSWORD = "bob123"

REDIRECT_STATUS_CODES = (301, 302, 303, 307, 308)


def parse_session_cookie(response):
    """Parse the session cookie from a login response and assert it is present."""
    cookie = SimpleCookie()
    cookie.load(response.headers["Set-Cookie"])
    assert "session" in cookie, "Session cookie is missing"
    assert cookie["session"].value != "", "Session cookie is empty"
    return cookie["session"].value


def assert_redirects_to_login(response):
    """Assert that a response redirects unauthenticated users to the login page."""
    assert response.status_code in REDIRECT_STATUS_CODES, "Expected redirect for missing/invalid session"
    assert response.headers["Location"].endswith("/login.html")


def login_and_assert_ok(client, username, password):
    """Log in with the provided credentials and assert the login succeeds."""
    response = client.post(
        "/api/login",
        json={
            "username": username,
            "password": password,
        },
    )
    assert response.status_code == 200
    assert response.get_json()["result"] == "OK"
    session_cookie = parse_session_cookie(response)
    return response, session_cookie