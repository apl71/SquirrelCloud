from flask import Blueprint, request, jsonify, send_file, current_app
from app import get_db
from db import file, auth, notification
import os
import pathlib
import utils
import secrets
from threading import Thread
import tempfile
import queue
import shutil

file_api = Blueprint("file_api", __name__)

def get_valid_session_user(conn):
    """Return the current user UUID if the session is valid, otherwise None."""
    session = request.cookies.get("session")
    return auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])

def get_and_validate_path_arg(arg_name: str = "path") -> tuple[bool, str | None, str]:
    """Read a path from query args and validate it."""
    path = request.args.get(arg_name)
    if path is None:
        return False, None, "Path is not specified."

    ok, message = utils.validate_virtual_path(path)
    if not ok:
        return False, None, message

    return True, path, "OK"

@file_api.route("/api/upload", methods=["POST"])
def upload():
    conn = get_db()
    ## check session
    user_uuid = get_valid_session_user(conn)
    if not user_uuid:
        return jsonify(utils.make_result(False, "Your session is not valid."))
    ## check if there is a file part in post request
    if "file" not in request.files:
        return jsonify(utils.make_result(False, "No file is uploaded."))
    file_storage = request.files["file"]
    ## check if the file is empty
    if file_storage.filename == "":
        return jsonify(utils.make_result(False, "Empty file is not allowed."))
    ## get input path
    if "path" not in request.form:
        return jsonify(utils.make_result(False, "No path is specified."))
    vpath = request.form["path"]
    result = file.save_and_register_file(conn, user_uuid, vpath, file_storage, current_app.config["STORAGE_PATH"], "replica" in request.form and request.form["replica"])
    return jsonify(result)
    
@file_api.route("/api/upload_directory", methods=["POST"])
def upload_directory():
    conn = get_db()
    ## check session
    user_uuid = get_valid_session_user(conn)
    if not user_uuid:
        return jsonify(utils.make_result(False, "Your session is not valid."))
    ## get input path
    if "path" not in request.form:
        return jsonify(utils.make_result(False, "No path is specified."))
    vpath = request.form["path"]
    file_num = request.form["file_num"]
    if int(file_num) < 1:
        return jsonify(utils.make_result(False, "No file is uploaded."))
    ## upload files
    i = 0
    while i < int(file_num):
        result = utils.make_result(True, "Files saved.")
        file_storage = request.files["file{}".format(i)]
        if not file_storage:
            break
        ## create sub-directory
        sub_path = os.path.join(os.path.join(vpath, os.path.dirname(file_storage.filename)))
        file.create_directory(conn, user_uuid, sub_path, True)
        if not file.directory_exists(conn, user_uuid, sub_path):
            return jsonify(utils.make_result(False, "Fail to create directory."))
        ## check if the file is empty
        if file_storage.filename == "":
            return jsonify(utils.make_result(False, "Empty file is not allowed."))
        result = file.save_and_register_file(conn, user_uuid, vpath, file_storage, current_app.config["STORAGE_PATH"], "replica" in request.form and request.form["replica"])
        if result["result"] == "FAIL":
            return jsonify(result)
        i += 1
    return jsonify(result)

@file_api.route("/api/download", methods=["GET"])
def download():
    conn = get_db()
    ## check if session is valid
    user_uuid = get_valid_session_user(conn)
    if not user_uuid:
        return jsonify(utils.make_result(False, "Your session is not valid."))
    ## get requested path
    filepath = request.args.get("file")
    if file.file_exists(conn, user_uuid, filepath):
        ## send a file
        ## get file hash and size
        hash, size = file.get_hash_and_size(conn, user_uuid, filepath)
        if not hash or not size:
            return jsonify(utils.make_result(False, "File not exists."))
        spath = os.path.join(current_app.config["STORAGE_PATH"], hash[0:2], "{}_{}".format(hash, size))
        if not os.path.exists(spath):
            return jsonify(utils.make_result(False, "File accidentally lost."))
        return send_file(spath, as_attachment=True, download_name=os.path.basename(filepath))
    elif file.directory_exists(conn, user_uuid, filepath):
        ## send a directory
        ## create a temporary directory for holding files
        with tempfile.TemporaryDirectory() as temp_dir:
            ## list all item in `filepath`
            directory_queue = queue.Queue()
            directory_queue.put(filepath)
            while not directory_queue.empty():
                current_vpath = directory_queue.get()
                current_ppath = os.path.join(temp_dir, os.path.relpath(current_vpath, filepath))
                print("Traversing: {}".format(current_vpath))
                print("Go to target: {}".format(current_ppath))
                files = file.list_file(conn, user_uuid, current_vpath)
                for f in files:
                    if f["type"] == "TYPE_FILE":
                        ## copy the file into folder
                        hash, size = file.get_hash_and_size(conn, user_uuid, f["path"])
                        spath = os.path.join(current_app.config["STORAGE_PATH"], hash[0:2], "{}_{}".format(hash, size))
                        shutil.copy(spath, current_ppath)
                        shutil.move(os.path.join(current_ppath, "{}_{}".format(hash, size)), os.path.join(current_ppath, os.path.basename(f["path"])))
                    else:
                        ## create directory and push to queue
                        os.mkdir(os.path.join(current_ppath, os.path.basename(f["path"])))
                        directory_queue.put(f["path"])
            shutil.make_archive(temp_dir, "zip", temp_dir)
            return send_file(temp_dir + ".zip", as_attachment=True, download_name=os.path.basename(filepath) + ".zip")
    else:
        return jsonify(utils.make_result(False, "No such file or directory."))

@file_api.route("/api/delete", methods=["DELETE"])
def delete():
    conn = get_db()
    ## get and check session
    user_uuid = get_valid_session_user(conn)
    if not user_uuid:
        return jsonify(utils.make_result(False, "Your session is not valid."))
    ## get requested path to delete
    filepath = request.args.get("file")
    ## remove '/' is not allowed
    if filepath == "/":
        return jsonify(utils.make_result(False, "Removing root is not allowed."))
    if filepath == "/recycle":
        return jsonify(utils.make_result(False, "Removing recycle bin is not allowed."))
    ## check if there is a link in the path
    target_user_uuid, target_path, _ = file.convert_path_with_link(conn, user_uuid, filepath)
    if target_user_uuid and target_path:
        ## do contain a link
        filepath = target_path
        user_uuid = target_user_uuid
        ## actually, if the path contains a link, then the file should be removed for target user's file system
    ## check the type of the file, dir or file?
    type = file.get_file_type(conn, user_uuid, filepath)
    if not type:
        return jsonify(utils.make_result(False, "File or directory not exists."))
    ## remove it
    if type == "TYPE_DIR":
        file.remove_dir(conn, user_uuid, filepath)
    elif type == "TYPE_FILE":
        file.remove_file(conn, user_uuid, filepath)
    else:
        return jsonify(utils.make_result(False, "Unknown error."))
    return jsonify(utils.make_result(True, "File Deleted."))

@file_api.route("/api/list", methods=["GET"])
def list():
    conn = get_db()
    ## get and check session
    user_uuid = get_valid_session_user(conn)
    if not user_uuid:
        return jsonify(utils.make_result(False, "Your session is not valid."))

    ## get requested path
    ok, filepath, message = get_and_validate_path_arg("path")
    if not ok:
        return jsonify(utils.make_result(False, message, files=[]))

    sort_by = request.args.get("sort_by")
    sort_order = request.args.get("sort")

    ## check if the path exists
    if not file.directory_exists(conn, user_uuid, filepath):
        return jsonify(utils.make_result(False, "Directory does not exist.", files=[]))

    ## get file infomations
    files = file.list_file(conn, user_uuid, filepath, sort_by=sort_by, sort=sort_order)
    return jsonify(utils.make_result(True, "Success.", files=files))

@file_api.route("/api/directory_size", methods=["GET"])
def directory_size():
    conn = get_db()
    ## get and check session
    user_uuid = get_valid_session_user(conn)
    if not user_uuid:
        return jsonify(utils.make_result(False, "Your session is not valid."))

    ## get requested path to delete
    filepath = request.args.get("path")

    ## check if the path exists
    if not file.directory_exists(conn, user_uuid, filepath):
        return jsonify(utils.make_result(False, "Directory does not exist.", size=0))

    ## get directory size
    size = file.get_directory_size(conn, user_uuid, filepath)
    return jsonify(utils.make_result(True, "Success.", size=size))

@file_api.route("/api/mkdir", methods=["POST"])
def mkdir():
    conn = get_db()
    ## get and check session
    user_uuid = get_valid_session_user(conn)
    if not user_uuid:
        return jsonify(utils.make_result(False, "Your session is not valid."))

    ## get requested path
    ok, newdir, message = get_and_validate_path_arg("path")
    if not ok:
        return jsonify(utils.make_result(False, message))

    ## check if there is a link in the path
    target_user_uuid, target_path, _ = file.convert_path_with_link(conn, user_uuid, newdir)
    if target_user_uuid and target_path:
        ## do contain a link
        newdir = target_path
        user_uuid = target_user_uuid
        ## actually, if the path contains a link, then the file should be saved for target user's file system

    r, m = file.create_directory(conn, user_uuid, newdir)
    if not r:
        return jsonify(utils.make_result(False, m))

    return jsonify(utils.make_result(True, "Success."))

@file_api.route("/api/fileid", methods=["GET"])
def fileid():
    conn = get_db()
    ## get and check session
    user_uuid = get_valid_session_user(conn)
    if not user_uuid:
        return jsonify(utils.make_result(False, "Your session is not valid."))

    ## get requested path
    filename = request.args.get("path")

    ## check if it is a file
    if not file.file_exists(conn, user_uuid, filename):
        return jsonify(utils.make_result(False, "File does not exist."))

    ## get id
    hash, size = file.get_hash_and_size(conn, user_uuid, filename)
    return jsonify(utils.make_result(True, "{}_{}".format(hash, size)))

@file_api.route("/api/search", methods=["GET"])
def search():
    conn = get_db()
    ## get and check session
    user_uuid = get_valid_session_user(conn)
    if not user_uuid:
        return jsonify(utils.make_result(False, "Your session is not valid."))

    ## get query string
    query = request.args.get("query")
    files = file.search(conn, user_uuid, query)
    return jsonify(utils.make_result(True, "Success.", files=files))

@file_api.route("/api/remark", methods=["POST"])
def update_remark():
    conn = get_db()
    ## get and check session
    user_uuid = get_valid_session_user(conn)
    if not user_uuid:
        return jsonify(utils.make_result(False, "Your session is not valid."))
    ## get request data in body
    request_data = request.get_json()
    filename = request_data["file"]
    remark = request_data["remark"]
    ## check if file or directory exists
    if not file.file_exists(conn, user_uuid, filename) and not file.directory_exists(conn, user_uuid, filename):
        return jsonify(utils.make_result(False, "File or directory does not exists."))
    ## update remark
    file.update_remark(conn, user_uuid, filename, remark)
    return jsonify(utils.make_result(True, "Success."))

@file_api.route("/api/rename", methods=["POST"])
def rename():
    conn = get_db()
    ## get and check session
    user_uuid = get_valid_session_user(conn)
    if not user_uuid:
        return jsonify(utils.make_result(False, "Your session is not valid."))
    ## get request data in body
    request_data = request.get_json()
    path = request_data["path"]
    new_path = request_data["new_path"]
    rename_type = ""
    ## check if path exists
    if file.file_exists(conn, user_uuid, path):
        rename_type = "FILE"
    elif file.directory_exists(conn, user_uuid, path):
        rename_type = "DIR"
    else:
        return jsonify(utils.make_result(False, "Directory or file does not exists."))
    ## check if parent path of new_path exists
    parent_path = str(pathlib.Path(new_path).parent)
    if not file.directory_exists(conn, user_uuid, parent_path):
        return jsonify(utils.make_result(False, "Parent of new name does not exists."))
    ## check if new_path exists already
    if file.file_exists(conn, user_uuid, new_path) or file.directory_exists(conn, user_uuid, new_path):
        return jsonify(utils.make_result(False, "New name is not valid."))
    ## check if the original path is shared from or to another user
    ## check if there is a link in the path
    target_user_uuid, _, _ = file.convert_path_with_link(conn, user_uuid, path)
    if not target_user_uuid == None:
        ## update table `LINK`
        file.update_link(conn, user_uuid, path, new_path)
    ## check if shared to another user
    shared_to = file.get_shared_users(conn, user_uuid, path)
    if len(shared_to) > 0:
        file.update_link_target(conn, user_uuid, path, new_path)
    if not file.rename_file_or_directory(conn, user_uuid, path, new_path, rename_type):
        return jsonify(utils.make_result(False, "Fail to rename."))
    return jsonify(utils.make_result(True, "Success."))


@file_api.route("/api/pin", methods=["POST"])
def pin_file():
    conn = get_db()
    ## get and check session
    user_uuid = get_valid_session_user(conn)
    if not user_uuid:
        return jsonify(utils.make_result(False, "Your session is not valid."))
    ## get query string
    path = request.args.get("path")
    pin = request.args.get("pin")
    ## check if path exists
    if not file.directory_exists(conn, user_uuid, path) and not file.file_exists(conn, user_uuid, path):
        return jsonify(utils.make_result(False, "File or directory does not exists."))
    file.pin_or_unpin_file(conn, user_uuid, path, pin)
    return jsonify(utils.make_result(True, "Success."))

@file_api.route("/api/tag", methods=["PUT", "GET", "DELETE"])
def new_tag():
    conn = get_db()
    ## get and check session
    user_uuid = get_valid_session_user(conn)
    if not user_uuid:
        return jsonify(utils.make_result(False, "Your session is not valid."))
    if request.method == "PUT":     ## create new tag
        ## get query string
        tag = request.args.get("tag")
        file.create_tag(conn, user_uuid, tag)
        return jsonify(utils.make_result(True, "Success."))
    elif request.method == "GET":   ## get all tag
        tags = file.get_tags(conn, user_uuid)
        return jsonify(utils.make_result(True, "Success.", tags=tags))
    elif request.method == "DELETE":
        tag = request.args.get("tag")
        tag_uuid = file.check_user_own_tag(conn, user_uuid, tag)
        if not tag_uuid:
            return jsonify(utils.make_result(False, "Tag does not exist."))
        file.remove_tag(conn, user_uuid, tag_uuid)
        return jsonify(utils.make_result(True, "Success."))
    
@file_api.route("/api/file_tag", methods=["PUT", "DELETE"])
def attach_tag():
    conn = get_db()
    ## get and check session
    user_uuid = get_valid_session_user(conn)
    if not user_uuid:
        return jsonify(utils.make_result(False, "Your session is not valid."))
    ## get vpath and tag
    tag = request.args.get("tag")
    path = request.args.get("path")
    if request.method == "PUT":
        ## check if path exists
        if not file.file_exists(conn, user_uuid, path) and not file.directory_exists(conn, user_uuid, path):
            return jsonify(utils.make_result(False, "File or directory does not exist."))
        ## check if tag exists
        tag_uuid = file.check_user_own_tag(conn, user_uuid, tag)
        if not tag_uuid:
            return jsonify(utils.make_result(False, "Tag does not exist."))
        ## check if the same tag is attached already
        if file.check_file_tag_exists(conn, user_uuid, tag_uuid, path):
            return jsonify(utils.make_result(False, "File is already tagged with the tag."))
        ## attach it to file
        file.attach_tag_to_file(conn, user_uuid, tag_uuid, path)
        return jsonify(utils.make_result(True, "Success."))
    elif request.method == "DELETE":
        ## check if tag exists
        tag_uuid = file.check_user_own_tag(conn, user_uuid, tag)
        if not tag_uuid:
            return jsonify(utils.make_result(False, "Tag does not exist."))
        file.remove_tag_from_file(conn, user_uuid, tag_uuid, path)
        return jsonify(utils.make_result(True, "Success."))
    
@file_api.route("/api/file_exist", methods=["GET"])
def file_exist():
    conn = get_db()
    ## get and check session
    user_uuid = get_valid_session_user(conn)
    if not user_uuid:
        return jsonify(utils.make_result(False, "Your session is not valid."))

    ## check if it exists
    ok, path, message = get_and_validate_path_arg("path")
    if not ok:
        return jsonify(utils.make_result(False, message, exist=False))

    type = request.args.get("type")
    file_exist_flag = file.file_exists(conn, user_uuid, path)
    dir_exist_flag = file.directory_exists(conn, user_uuid, path)

    if type == "TYPE_ANY":
        exist = file_exist_flag or dir_exist_flag
    elif type == "TYPE_FILE":
        exist = file_exist_flag
    elif type == "TYPE_DIR":
        exist = dir_exist_flag
    else:
        return jsonify(utils.make_result(False, "Type is not valid.", exist=False))

    return jsonify(utils.make_result(True, "Success.", exist=exist))

@file_api.route("/api/external_link", methods=["POST", "GET"])
def external_link():
    conn = get_db()
    ## create external link
    if request.method == "POST":
        ## get and check session
        user_uuid = get_valid_session_user(conn)
        if not user_uuid:
            return jsonify(utils.make_result(False, "Your session is not valid."))
        ## get params
        request_data = request.get_json()
        path = request_data["path"]
        expire = request_data["expire"] # in unix timestamps
        ## check if the file exists
        if not file.file_exists(conn, user_uuid, path):
            return jsonify(utils.make_result(False, "File does not exist.", link="Not valid"))
        ## generate an external link and insert it into database
        key = file.create_external_link(conn, user_uuid, path, expire)
        if key is None:
            return jsonify(utils.make_result(False, "Fail to create external link.", link="Not valid"))
        link = "https://{}/api/external_link?key={}".format(current_app.config["HOST"], key)
        return jsonify(utils.make_result(True, "Success.", link=link))
    ## download from external link
    elif request.method == "GET":
        key = request.args.get("key")
        ## get file information
        user_uuid, filepath = file.query_external_link(conn, key)
        ## check if file exists
        if not file.file_exists(conn, user_uuid, filepath):
            return jsonify(utils.make_result(False, "File not exists."))
        ## get file hash and size
        hash, size = file.get_hash_and_size(conn, user_uuid, filepath)
        if not hash or not size:
            return jsonify(utils.make_result(False, "File not exists."))
        spath = os.path.join(current_app.config["STORAGE_PATH"], hash[0:2], "{}_{}".format(hash, size))
        if not os.path.exists(spath):
            return jsonify(utils.make_result(False, "File accidentally lost."))
        return send_file(spath, as_attachment=True, download_name=os.path.basename(filepath))
    

@file_api.route("/api/all_external_links", methods=["GET"])
def all_external_link():
    conn = get_db()
    ## get and check session
    user_uuid = get_valid_session_user(conn)
    if not user_uuid:
        return jsonify(utils.make_result(False, "Your session is not valid."))
    links = file.get_all_external_links(conn, user_uuid)
    return jsonify(utils.make_result(True, "Success.", links=links))

@file_api.route("/api/remove_external_link", methods=["DELETE"])
def remove_external_link():
    conn = get_db()
    ## get and check session
    user_uuid = get_valid_session_user(conn)
    if not user_uuid:
        return jsonify(utils.make_result(False, "Your session is not valid."))
    key = request.args.get("key")
    if file.remove_external_link(conn, user_uuid, key):
        return jsonify(utils.make_result(True, "Success."))
    else:
        return jsonify(utils.make_result(False, "Fail to remove external link."))

@file_api.route("/api/replica", methods=["GET"])
def replica():
    conn = get_db()
    ## return if user owns the same file 
    ## get and check session
    user_uuid = get_valid_session_user(conn)
    if not user_uuid:
        return jsonify(utils.make_result(False, "Your session is not valid."))
    ## check if it exists
    hash = request.args.get("hash")
    size = request.args.get("size")
    files = file.search_by_id(conn, user_uuid, hash, size)
    exist = len(files) > 0
    return jsonify(utils.make_result(True, "Success.", exist=exist))

@file_api.route("/api/replica_list", methods=["GET"])
def replica_list():
    conn = get_db()
    ## get and check session
    user_uuid = get_valid_session_user(conn)
    if not user_uuid:
        return jsonify(utils.make_result(False, "Your session is not valid."))
    files = file.find_replicas(conn, user_uuid)
    return jsonify(utils.make_result(True, "Success.", files=files))

@file_api.route("/api/http_download", methods=["POST"])
def http_download():
    conn = get_db()
    ## get and check session
    user_uuid = get_valid_session_user(conn)
    if not user_uuid:
        return jsonify(utils.make_result(False, "Your session is not valid."))
    url = request.args.get("url")
    ## generate a task id
    task_id = secrets.token_hex(32)
    ## async download file
    thread = Thread(target=file.download_file_http, args=(conn, user_uuid, url, task_id, current_app.config["STORAGE_PATH"]))
    thread.start()
    return jsonify(utils.make_result(True, "Success.", task_id=task_id))

@file_api.route("/api/http_download_tasks", methods=["GET"])
def http_download_tasks():
    conn = get_db()
    ## get and check session
    user_uuid = get_valid_session_user(conn)
    if not user_uuid:
        return jsonify(utils.make_result(False, "Your session is not valid."))
    ## WARNING: No authentication here
    ## get all tasks
    tasks = []
    for task_id in file.progress_data:
        url, downloaded, total_size, _ = file.progress_data[task_id]
        tasks.append({
            "task_id": task_id,
            "url": url,
            "downloaded": downloaded,
            "total": total_size
        })
    return jsonify(utils.make_result(True, "Success.", tasks=tasks))

@file_api.route("/api/http_download_stop", methods=["DELETE"])
def http_download_stop():
    conn = get_db()
    ## get and check session
    user_uuid = get_valid_session_user(conn)
    if not user_uuid:
        return jsonify(utils.make_result(False, "Your session is not valid."))
    ## WARNING: No authentication here
    ## get task id and stop it
    task_id = request.args.get("task_id")
    if file.stop_download(task_id):
        return jsonify(utils.make_result(True, "Success."))
    else:
        return jsonify(utils.make_result(False, "Task not found."))


## POST: send a share request to another user
## PUT:  accept a share request from another user
@file_api.route("/api/share_request", methods=["POST", "PUT"])
def share_request():
    conn = get_db()
    ## get and check session
    if request.method == "POST":
        from_user_uuid = get_valid_session_user(conn)
        if not from_user_uuid:
            return jsonify(utils.make_result(False, "Your session is not valid."))
        ## get data
        request_data = request.get_json()
        target_user = request_data["target_user"]
        target_user_uuid = auth.get_uuid_by_username(conn, target_user)
        if not target_user_uuid:
            return jsonify(utils.make_result(False, "Target user does not exist."))
        share_path = request_data["share_path"]
        ## check if share path is valid
        if not file.directory_exists(conn, from_user_uuid, share_path):
            return jsonify(utils.make_result(False, "Share path does not exist."))
        ## check if share path is already shared to target user
        if file.check_share(conn, from_user_uuid, share_path, target_user_uuid):
            return jsonify(utils.make_result(False, "Share path is already shared to target user."))
        ## create share request
        if file.create_share_request(conn, from_user_uuid, share_path, target_user_uuid):
            utils.log(utils.LEVEL_INFO, "User [{}] send a share request to [{}] for [{}]".format(from_user_uuid, target_user_uuid, share_path))
            return jsonify(utils.make_result(True, "Success."))
        else:
            utils.log(utils.LEVEL_INFO, "User [{}] send a share request to [{}] for [{}]".format(from_user_uuid, target_user_uuid, share_path))
            return jsonify(utils.make_result(False, "Fail to create share request."))
    elif request.method == "PUT":
        to_user_uuid = get_valid_session_user(conn)
        if not to_user_uuid:
            return jsonify(utils.make_result(False, "Your session is not valid."))
        ## get data
        request_data = request.get_json()
        notification_uuid = request_data["notification_uuid"]
        path = request_data["path"] # link directory
        ## create the path
        if file.directory_exists(conn, to_user_uuid, path):
            return jsonify(utils.make_result(False, "The Path already exists."))
        ## chenk if there is the share request from another user
        if not notification.check_notification(conn, notification_uuid):
            return jsonify(utils.make_result(False, "Share request does not exist."))
        ## get share request info
        info = notification.get_notification(conn, notification_uuid)
        if not info:
            return jsonify(utils.make_result(False, "Share request does not exist."))
        if file.create_link(conn, info["to_user_uuid"], path, info["from_user_uuid"], info["meta"]):
            ## remove notification
            notification.remove_notification(conn, notification_uuid)
            return jsonify(utils.make_result(True, "Success."))
        else:
            return jsonify(utils.make_result(False, "Fail to create link."))
    
@file_api.route("/api/upload_filter", methods=["GET", "PUT", "POST", "DELETE"])
def upload_filter():
    conn = get_db()
    ## get and check session
    user_uuid = get_valid_session_user(conn)
    if not user_uuid:
        return jsonify(utils.make_result(False, "Your session is not valid."))
    if request.method == "GET":
        ## get file list
        filters = file.get_all_upload_filters(conn, user_uuid)
        return jsonify(utils.make_result(True, "Success.", filters=filters))
    elif request.method == "PUT":
        ## get data
        request_data = request.get_json()
        filter = request_data["filter"]
        type = request_data["type"]
        value = request_data["value"]
        ## add the filter
        if file.add_upload_filter(conn, user_uuid, filter, type, value):
            return jsonify(utils.make_result(True, "Success."))
        else:
            return jsonify(utils.make_result(False, "Fail to add upload filter."))
    elif request.method == "POST":
        ## get data
        request_data = request.get_json()
        filter_uuid = request_data["uuid"]
        filter = request_data.get("filter")
        type = request_data.get("type")
        value = request_data.get("value")
        active = request_data.get("active")
        ## remove the filter
        if file.update_upload_filter(conn, user_uuid, filter_uuid, filter, type, value, active):
            return jsonify(utils.make_result(True, "Success."))
        else:
            return jsonify(utils.make_result(False, "Fail to update upload filter."))
    elif request.method == "DELETE":
        ## get data
        request_data = request.get_json()
        filter_uuid = request_data["uuid"]
        ## remove the filter
        if file.remove_upload_filter(conn, user_uuid, filter_uuid):
            return jsonify(utils.make_result(True, "Success."))
        else:
            return jsonify(utils.make_result(False, "Fail to remove upload filter."))