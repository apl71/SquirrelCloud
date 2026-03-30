"""Path validation and edge-case tests for basic file APIs."""

from test import app
from test_utils import ALICE_PASSWORD, ALICE_USERNAME, login_and_assert_ok


def assert_fail(response, expected_message=None):
    """Assert a JSON FAIL response, optionally checking the message."""
    assert response.status_code == 200
    body = response.get_json()
    assert body["result"] == "FAIL"
    if expected_message is not None:
        assert body["message"] == expected_message
    return body


def test_mkdir_rejects_missing_path_parameter(app):
    """mkdir should fail when path is missing."""
    client = app.test_client()
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    response = client.post("/api/mkdir")
    assert_fail(response)


def test_mkdir_rejects_empty_path(app):
    """mkdir should fail when path is an empty string."""
    client = app.test_client()
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    response = client.post("/api/mkdir?path=")
    assert_fail(response)


def test_mkdir_rejects_relative_path(app):
    """mkdir should fail for a relative virtual path."""
    client = app.test_client()
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    response = client.post("/api/mkdir?path=Documents/NewFolder")
    assert_fail(response)


def test_mkdir_rejects_parent_traversal_path(app):
    """mkdir should fail for a path containing '..' traversal segments."""
    client = app.test_client()
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    response = client.post("/api/mkdir?path=/Documents/../Escape")
    assert_fail(response)


def test_mkdir_rejects_double_slash_path(app):
    """mkdir should fail for a path containing repeated slashes."""
    client = app.test_client()
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    response = client.post("/api/mkdir?path=/Documents//DoubleSlash")
    assert_fail(response)


def test_mkdir_rejects_trailing_slash_path(app):
    """mkdir should fail for a non-normalized path ending with '/'."""
    client = app.test_client()
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    response = client.post("/api/mkdir?path=/Documents/TrailingSlash/")
    assert_fail(response)


def test_mkdir_current_api_is_not_recursive(app):
    """mkdir currently should fail when parent directories do not already exist."""
    client = app.test_client()
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    response = client.post("/api/mkdir?path=/NoSuchParent/Child/Grandchild")
    assert_fail(response)


def test_mkdir_behavior_for_dollar_sign_path(app):
    """Record current behavior for a path containing '$' in the final segment."""
    client = app.test_client()
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    response = client.post("/api/mkdir?path=/Documents/haha$123")
    assert response.status_code == 200
    body = response.get_json()
    assert body["result"] in ("OK", "FAIL")


def test_list_rejects_empty_path(app):
    """list should fail when path is empty."""
    client = app.test_client()
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    response = client.get("/api/list?path=")
    assert_fail(response)


def test_list_rejects_relative_path(app):
    """list should fail for a relative virtual path."""
    client = app.test_client()
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    response = client.get("/api/list?path=Documents")
    assert_fail(response)


def test_list_rejects_parent_traversal_path(app):
    """list should fail for a path containing '..' traversal segments."""
    client = app.test_client()
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    response = client.get("/api/list?path=/Documents/../Work")
    assert_fail(response)


def test_list_rejects_trailing_slash_path(app):
    """list should fail for a non-normalized path ending with '/'."""
    client = app.test_client()
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    response = client.get("/api/list?path=/Documents/")
    assert_fail(response)


def test_file_exist_rejects_empty_path(app):
    """file_exist should fail when path is empty."""
    client = app.test_client()
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    response = client.get("/api/file_exist?path=&type=TYPE_ANY")
    assert_fail(response)


def test_file_exist_rejects_double_slash_path(app):
    """file_exist should fail for a path with repeated slashes."""
    client = app.test_client()
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    response = client.get("/api/file_exist?path=/Documents//Work&type=TYPE_DIR")
    assert_fail(response)


def test_file_exist_rejects_parent_traversal_path(app):
    """file_exist should fail for a path containing '..' traversal segments."""
    client = app.test_client()
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    response = client.get("/api/file_exist?path=/Documents/../Work&type=TYPE_DIR")
    assert_fail(response)


def test_file_exist_rejects_trailing_slash_path(app):
    """file_exist should fail for a non-normalized path ending with '/'."""
    client = app.test_client()
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    response = client.get("/api/file_exist?path=/Documents/Work/&type=TYPE_DIR")
    assert_fail(response)

def test_mkdir_allows_dot_prefixed_name(app):
    client = app.test_client()
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    response = client.post("/api/mkdir?path=/Documents/.ab")
    assert response.status_code == 200
    assert response.get_json()["result"] == "OK"


def test_mkdir_allows_dot_inside_name(app):
    client = app.test_client()
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    response = client.post("/api/mkdir?path=/Documents/a.b")
    assert response.status_code == 200
    assert response.get_json()["result"] == "OK"

def test_mkdir_ignores_json_body_and_still_requires_query_path(app):
    """mkdir should still require query-string path even if JSON body is provided."""
    client = app.test_client()
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    response = client.post("/api/mkdir", json={"path": "/Documents/BodyOnly"})
    assert response.status_code == 200
    body = response.get_json()
    assert body["result"] == "FAIL"
    assert body["message"] == "Path is not specified."


def test_list_ignores_json_body_and_still_requires_query_path(app):
    """list should still require query-string path even if JSON body is provided."""
    client = app.test_client()
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    response = client.get("/api/list", json={"path": "/"})
    assert response.status_code == 200
    body = response.get_json()
    assert body["result"] == "FAIL"
    assert body["message"] == "Path is not specified."


def test_file_exist_ignores_json_body_and_still_requires_query_path(app):
    """file_exist should still require query-string path even if JSON body is provided."""
    client = app.test_client()
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    response = client.get("/api/file_exist?type=TYPE_DIR", json={"path": "/Documents"})
    assert response.status_code == 200
    body = response.get_json()
    assert body["result"] == "FAIL"
    assert body["message"] == "Path is not specified."

def test_file_exist_requires_type_parameter(app):
    """file_exist should fail when type is missing."""
    client = app.test_client()
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    response = client.get("/api/file_exist?path=/Documents")
    assert response.status_code == 200
    body = response.get_json()
    assert body["result"] == "FAIL"
    assert body["message"] == "Type is not valid."