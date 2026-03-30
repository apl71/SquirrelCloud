"""Basic file API tests for mkdir, list, and file_exist."""

from test import client, app
from test_utils import (
    ADMIN_USERNAME,
    ADMIN_PASSWORD,
    ALICE_USERNAME,
    ALICE_PASSWORD,
    BOB_USERNAME,
    BOB_PASSWORD,
    login_and_assert_ok,
)


def test_list_requires_valid_session(app):
    """Listing files without a valid session should fail."""
    fresh_client = app.test_client()
    response = fresh_client.get("/api/list?path=/")
    assert response.status_code == 200
    body = response.get_json()
    assert body["result"] == "FAIL"
    assert body["message"] == "Your session is not valid."


def test_list_root_directory_for_alice(client):
    """Alice should be able to list her root directory and see seeded folders/files."""
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    response = client.get("/api/list?path=/")
    assert response.status_code == 200
    body = response.get_json()
    assert body["result"] == "OK"

    returned_paths = {item["path"] for item in body["files"]}
    assert "/Documents" in returned_paths
    assert "/Pictures" in returned_paths
    assert "/Downloads" in returned_paths
    assert "/Music" in returned_paths
    assert "/recycle" in returned_paths


def test_list_rejects_nonexistent_directory(client):
    """Listing a non-existent directory should fail cleanly."""
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    response = client.get("/api/list?path=/DoesNotExist")
    assert response.status_code == 200
    body = response.get_json()
    assert body["result"] == "FAIL"
    assert body["message"] == "Directory does not exist."


def test_file_exist_requires_valid_session(app):
    """file_exist without a valid session should fail."""
    fresh_client = app.test_client()
    response = fresh_client.get("/api/file_exist?path=/Documents&type=TYPE_DIR")
    assert response.status_code == 200
    body = response.get_json()
    assert body["result"] == "FAIL"
    assert body["message"] == "Your session is not valid."


def test_file_exist_detects_directory(client):
    """file_exist should report true for an existing directory."""
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    response = client.get("/api/file_exist?path=/Documents&type=TYPE_DIR")
    assert response.status_code == 200
    body = response.get_json()
    assert body["result"] == "OK"
    assert body["exist"] is True


def test_file_exist_detects_file(client):
    """file_exist should report true for an existing file."""
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    response = client.get("/api/file_exist?path=/Documents/Work/project-plan.md&type=TYPE_FILE")
    assert response.status_code == 200
    body = response.get_json()
    assert body["result"] == "OK"
    assert body["exist"] is True


def test_file_exist_type_any_works_for_file_and_directory(client):
    """TYPE_ANY should succeed for both files and directories."""
    login_and_assert_ok(client, BOB_USERNAME, BOB_PASSWORD)

    dir_response = client.get("/api/file_exist?path=/Projects&type=TYPE_ANY")
    assert dir_response.status_code == 200
    dir_body = dir_response.get_json()
    assert dir_body["result"] == "OK"
    assert dir_body["exist"] is True

    file_response = client.get("/api/file_exist?path=/Projects/demo-app/README.md&type=TYPE_ANY")
    assert file_response.status_code == 200
    file_body = file_response.get_json()
    assert file_body["result"] == "OK"
    assert file_body["exist"] is True


def test_file_exist_rejects_invalid_type(client):
    """Invalid type values should fail cleanly."""
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    response = client.get("/api/file_exist?path=/Documents&type=NOT_A_REAL_TYPE")
    assert response.status_code == 200
    body = response.get_json()
    assert body["result"] == "FAIL"
    assert body["message"] == "Type is not valid."


def test_mkdir_requires_valid_session(app):
    """mkdir without a valid session should fail."""
    fresh_client = app.test_client()
    response = fresh_client.post("/api/mkdir?path=/NewFolder")
    assert response.status_code == 200
    body = response.get_json()
    assert body["result"] == "FAIL"
    assert body["message"] == "Your session is not valid."


def test_mkdir_creates_directory_successfully(client):
    """mkdir should create a new directory for a valid logged-in user."""
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    create_response = client.post("/api/mkdir?path=/Documents/NewFolder")
    assert create_response.status_code == 200
    create_body = create_response.get_json()
    assert create_body["result"] == "OK"

    exist_response = client.get("/api/file_exist?path=/Documents/NewFolder&type=TYPE_DIR")
    assert exist_response.status_code == 200
    exist_body = exist_response.get_json()
    assert exist_body["result"] == "OK"
    assert exist_body["exist"] is True


def test_mkdir_rejects_duplicate_directory(client):
    """mkdir should fail when the target directory already exists."""
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    first_response = client.post("/api/mkdir?path=/Documents/AlreadyThere")
    assert first_response.status_code == 200
    assert first_response.get_json()["result"] == "OK"

    second_response = client.post("/api/mkdir?path=/Documents/AlreadyThere")
    assert second_response.status_code == 200
    second_body = second_response.get_json()
    assert second_body["result"] == "FAIL"


def test_mkdir_rejects_missing_parent_directory(client):
    """mkdir should fail when the parent directory does not exist."""
    login_and_assert_ok(client, ALICE_USERNAME, ALICE_PASSWORD)

    response = client.post("/api/mkdir?path=/NoSuchParent/Child")
    assert response.status_code == 200
    body = response.get_json()
    assert body["result"] == "FAIL"


def test_mkdir_result_is_visible_in_list(client):
    """A newly created directory should appear in the parent directory listing."""
    login_and_assert_ok(client, BOB_USERNAME, BOB_PASSWORD)

    create_response = client.post("/api/mkdir?path=/Projects/NewModule")
    assert create_response.status_code == 200
    assert create_response.get_json()["result"] == "OK"

    list_response = client.get("/api/list?path=/Projects")
    assert list_response.status_code == 200
    list_body = list_response.get_json()
    assert list_body["result"] == "OK"

    returned_paths = {item["path"] for item in list_body["files"]}
    assert "/Projects/NewModule" in returned_paths