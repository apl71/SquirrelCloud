import pytest
from http.cookies import SimpleCookie
from test import client, app, get_connection

@pytest.mark.parametrize("username,password,expected_result", [
    ("admin", "admin", "OK"),
    ("admin", "Admin@123", "FAIL"),
    ("admin' or '1'='1", "root' or 1=1 -- # ", "FAIL"),      ## simple sql injection
    ("", "", "FAIL"),                                        ## empty username or password
    ("admin", "", "FAIL"),
    ("", "admin", "FAIL")
])
def test_login(client, username, password, expected_result):
    response = client.post("/api/login", json={
        "username": username,
        "password": password
    })
    assert response.status_code == 200
    # Parse result
    result = response.json["result"]
    assert result == expected_result
    if result == "OK":
        # Parse the Set-Cookie header
        cookie = SimpleCookie()
        cookie.load(response.headers["Set-Cookie"])
        # Check that the session value is not empty
        assert cookie["session"].value != ""
    else:
        assert "Set-Cookie" not in response.headers
