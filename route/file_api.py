from flask import Blueprint, request, jsonify, send_file, current_app
from app import conn
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

@file_api.route("/api/upload", methods=["POST"])
def upload():
    result = {
        "result": "FAIL",
        "message": "File saved."
    }
    ## check session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["message"] = "Your session is not valid."
        return jsonify(result)
    ## check if there is a file part in post request
    if "file" not in request.files:
        result["message"] = "No file is uploaded."
        return jsonify(result)
    file_storage = request.files["file"]
    ## check if the file is empty
    if file_storage.filename == "":
        result["message"] = "Empty file is not allowed."
        return jsonify(result)
    ## get input path
    if "path" not in request.form:
        result["message"] = "No path is specified."
        return jsonify(result)
    vpath = request.form["path"]
    result = file.save_and_register_file(conn, user_uuid, vpath, file_storage, current_app.config["STORAGE_PATH"], "replica" in request.form and request.form["replica"])
    return jsonify(result)
    
@file_api.route("/api/upload_directory", methods=["POST"])
def upload_directory():
    result = {
        "result": "FAIL",
        "message": "Files saved."
    }
    ## check session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["message"] = "Your session is not valid."
        return jsonify(result)
    ## get input path
    if "path" not in request.form:
        result["message"] = "No path is specified."
        return jsonify(result)
    vpath = request.form["path"]
    file_num = request.form["file_num"]
    ## upload files
    i = 0
    while i < int(file_num):
        result["result"] = "OK"
        file_storage = request.files["file{}".format(i)]
        if not file_storage:
            break
        ## create sub-directory
        sub_path = os.path.join(os.path.join(vpath, os.path.dirname(file_storage.filename)))
        file.create_directory(conn, user_uuid, sub_path, True)
        if not file.directory_exists(conn, user_uuid, sub_path):
            result["message"] = "Fail to create directory."
            return jsonify(result)
        ## check if the file is empty
        if file_storage.filename == "":
            result["message"] = "Empty file is not allowed."
            return jsonify(result)
        result = file.save_and_register_file(conn, user_uuid, vpath, file_storage, current_app.config["STORAGE_PATH"], "replica" in request.form and request.form["replica"])
        if result["result"] == "FAIL":
            return jsonify(result)
        i += 1
    return jsonify(result)

@file_api.route("/api/download", methods=["GET"])
def download():
    result = {
        "result": "FAIL",
        "message": ""
    }
    ## check if session is valid
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["message"] = "Your session is not valid."
        return jsonify(result)
    ## get requested path
    filepath = request.args.get("file")
    if file.file_exists(conn, user_uuid, filepath):
        ## send a file
        ## get file hash and size
        hash, size = file.get_hash_and_size(conn, user_uuid, filepath)
        if not hash or not size:
            result["message"] = "File not exists."
            return jsonify(result)
        spath = os.path.join(current_app.config["STORAGE_PATH"], hash[0:2], "{}_{}".format(hash, size))
        if not os.path.exists(spath):
            result["message"] = "File accidentally lost."
            return jsonify(result)
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
        result["message"] = "No such file or directory."
        return jsonify(result)

@file_api.route("/api/delete", methods=["DELETE"])
def delete():
    result = {
        "result": "FAIL",
        "message": ""
    }
    ## get and check session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["message"] = "Your session is not valid."
        return jsonify(result)
    ## get requested path to delete
    filepath = request.args.get("file")
    ## remove '/' is not allowed
    if filepath == "/":
        result["message"] = "Removing root is not allowed."
        return jsonify(result)
    if filepath == "/recycle":
        result["message"] = "Removing recycle bin is not allowed."
        return jsonify(result)
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
        result["message"] = "File or directory not exists."
        return jsonify(result)
    ## remove it
    if type == "TYPE_DIR":
        file.remove_dir(conn, user_uuid, filepath)
    elif type == "TYPE_FILE":
        file.remove_file(conn, user_uuid, filepath)
    else:
        result["message"] = "Unknown error."
        return jsonify(result)
    result["result"] = "OK"
    result["message"] = "File Deleted."
    return jsonify(result)

@file_api.route("/api/list", methods=["GET"])
def list():
    result = {
        "result": "FAIL",
        "message": "",
        "files": []
    }
    ## get and check session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["message"] = "Your session is not valid."
        return jsonify(result)
    ## get requested path to delete
    filepath = request.args.get("path")
    ## check if the path exists
    if not file.directory_exists(conn, user_uuid, filepath):
        result["message"] = "Directory does not exist."
        return jsonify(result)
    ## get file infomations
    file_infos = file.list_file(conn, user_uuid, filepath)
    result["files"] = file_infos
    result["result"] = "OK"
    result["message"] = "Success."
    return jsonify(result)

@file_api.route("/api/directory_size", methods=["GET"])
def directory_size():
    result = {
        "result": "FAIL",
        "message": "",
        "size": 0
    }
    ## get and check session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["message"] = "Your session is not valid."
        return jsonify(result)
    ## get requested path to delete
    filepath = request.args.get("path")
    ## check if the path exists
    if not file.directory_exists(conn, user_uuid, filepath):
        result["message"] = "Directory does not exist."
        return jsonify(result)
    ## get directory size
    result["size"] = file.get_directory_size(conn, user_uuid, filepath)
    result["result"] = "OK"
    result["message"] = "Success."
    return jsonify(result)

@file_api.route("/api/mkdir", methods=["POST"])
def mkdir():
    result = {
        "result": "FAIL",
        "message": ""
    }
    ## get and check session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["message"] = "Your session is not valid."
        return jsonify(result)
    ## get requested path
    newdir = request.args.get("path")
    ## check if there is a link in the path
    target_user_uuid, target_path, _ = file.convert_path_with_link(conn, user_uuid, newdir)
    if target_user_uuid and target_path:
        ## do contain a link
        newdir = target_path
        user_uuid = target_user_uuid
        ## actually, if the path contains a link, then the file should be saved for target user's file system
    r, m = file.create_directory(conn, user_uuid, newdir)
    if not r:
        result["message"] = m
        return jsonify(result)
    result["result"] = "OK"
    result["message"] = "Success."
    return jsonify(result)

@file_api.route("/api/fileid", methods=["GET"])
def fileid():
    result = {
        "result": "FAIL",
        "message": ""
    }
    ## get and check session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["message"] = "Your session is not valid."
        return jsonify(result)
    ## get requested path
    filename = request.args.get("path")
    ## check if it is a file
    if not file.file_exists(conn, user_uuid, filename):
        result["message"] = "File does not exist."
        return jsonify(result)
    ## get id
    hash, size = file.get_hash_and_size(conn, user_uuid, filename)
    result["message"] = "{}_{}".format(hash, size)
    result["result"] = "OK"
    return jsonify(result)

@file_api.route("/api/search", methods=["GET"])
def search():
    result = {
        "result": "FAIL",
        "message": "",
        "files": []
    }
    ## get and check session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["message"] = "Your session is not valid."
        return jsonify(result)
    ## get query string
    query = request.args.get("query")
    result["files"] = file.search(conn, user_uuid, query)
    result["result"] = "OK"
    result["message"] = "Success."
    return jsonify(result)

@file_api.route("/api/remark", methods=["POST"])
def update_remark():
    result = {
        "result": "FAIL",
        "message": "Success."
    }
    ## get and check session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["message"] = "Your session is not valid."
        return jsonify(result)
    ## get request data in body
    request_data = request.get_json()
    filename = request_data["file"]
    remark = request_data["remark"]
    ## check if file or directory exists
    if not file.file_exists(conn, user_uuid, filename) and not file.directory_exists(conn, user_uuid, filename):
        result["message"] = "File or directory does not exists."
        return jsonify(result)
    ## update remark
    file.update_remark(conn, user_uuid, filename, remark)
    result["result"] = "OK"
    return jsonify(result)

@file_api.route("/api/rename", methods=["POST"])
def rename():
    result = {
        "result": "FAIL",
        "message": "Success."
    }
    ## get and check session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["message"] = "Your session is not valid."
        return jsonify(result)
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
        result["message"] = "Directory or file does not exists."
        return jsonify(result)
    ## check if parent path of new_path exists
    parent_path = str(pathlib.Path(new_path).parent)
    if not file.directory_exists(conn, user_uuid, parent_path):
        result["message"] = "Parent of new name does not exists."
        return jsonify(result)
    ## check if new_path exists already
    if file.file_exists(conn, user_uuid, new_path) or file.directory_exists(conn, user_uuid, new_path):
        result["message"] = "New name is not valid."
        return jsonify(result)
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
        result["message"] = "Fail to rename."
        return jsonify(result)
    result["result"] = "OK"
    return jsonify(result)


@file_api.route("/api/pin", methods=["POST"])
def pin_file():
    result = {
        "result": "FAIL",
        "message": "Success."
    }
    ## get and check session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["message"] = "Your session is not valid."
        return jsonify(result)
    ## get query string
    path = request.args.get("path")
    pin = request.args.get("pin")
    ## check if path exists
    if not file.directory_exists(conn, user_uuid, path) and not file.file_exists(conn, user_uuid, path):
        result["message"] = "File or directory does not exists."
        return jsonify(result)
    file.pin_or_unpin_file(conn, user_uuid, path, pin)
    result["result"] = "OK"
    return jsonify(result)

@file_api.route("/api/tag", methods=["PUT", "GET", "DELETE"])
def new_tag():
    result = {
        "result": "FAIL",
        "message": "Success."
    }
    ## get and check session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["message"] = "Your session is not valid."
        return jsonify(result)
    if request.method == "PUT":     ## create new tag
        ## get query string
        tag = request.args.get("tag")
        file.create_tag(conn, user_uuid, tag)
        result["result"] = "OK"
        return jsonify(result)
    elif request.method == "GET":   ## get all tag
        tags = file.get_tags(conn, user_uuid)
        result["tags"] = tags
        result["result"] = "OK"
        return jsonify(result)
    elif request.method == "DELETE":
        tag = request.args.get("tag")
        tag_uuid = file.check_user_own_tag(conn, user_uuid, tag)
        if not tag_uuid:
            result["message"] = "Tag does not exist."
            return jsonify(result)
        file.remove_tag(conn, user_uuid, tag_uuid)
        result["result"] = "OK"
        return jsonify(result)
    
@file_api.route("/api/file_tag", methods=["PUT", "DELETE"])
def attach_tag():
    result = {
        "result": "FAIL",
        "message": "Success."
    }
    ## get and check session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["message"] = "Your session is not valid."
        return jsonify(result)
    ## get vpath and tag
    tag = request.args.get("tag")
    path = request.args.get("path")
    if request.method == "PUT":
        ## check if path exists
        if not file.file_exists(conn, user_uuid, path) and not file.directory_exists(conn, user_uuid, path):
            result["message"] = "File or directory does not exist."
            return jsonify(result)
        ## check if tag exists
        tag_uuid = file.check_user_own_tag(conn, user_uuid, tag)
        if not tag_uuid:
            result["message"] = "Tag does not exist."
            return jsonify(result)
        ## check if the same tag is attached already
        if file.check_file_tag_exists(conn, user_uuid, tag_uuid, path):
            result["message"] = "File is already tagged with the tag."
            return jsonify(result)
        ## attach it to file
        file.attach_tag_to_file(conn, user_uuid, tag_uuid, path)
        result["result"] = "OK"
        return jsonify(result)
    elif request.method == "DELETE":
        ## check if tag exists
        tag_uuid = file.check_user_own_tag(conn, user_uuid, tag)
        if not tag_uuid:
            result["message"] = "Tag does not exist."
            return jsonify(result)
        file.remove_tag_from_file(conn, user_uuid, tag_uuid, path)
        result["result"] = "OK"
        return jsonify(result)
    
@file_api.route("/api/file_exist", methods=["GET"])
def file_exist():
    result = {
        "result": "FAIL",
        "exist": False,
        "message": "Success."
    }
    ## get and check session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["message"] = "Your session is not valid."
        return jsonify(result)
    ## check if it exists
    path = request.args.get("path")
    type = request.args.get("type")
    file_exist = file.file_exists(conn, user_uuid, path)
    dir_exist = file.directory_exists(conn, user_uuid, path)
    if type == "TYPE_ANY":
        result["exist"] = file_exist or dir_exist
    elif type == "TYPE_FILE":
        result["exist"] = file_exist
    elif type == "TYPE_DIR":
        result["exist"] = dir_exist
    else:
        result["message"] = "Type is not valid."
        return jsonify(result)
    result["result"] = "OK"
    return jsonify(result)

@file_api.route("/api/external_link", methods=["POST", "GET"])
def external_link():
    ## create external link
    if request.method == "POST":
        result = {
            "result": "FAIL",
            "link": "Not valid",
            "message": "Success."
        }
        ## get and check session
        session = request.cookies.get("session")
        user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
        if not user_uuid:
            result["message"] = "Your session is not valid."
            return jsonify(result)
        ## get params
        request_data = request.get_json()
        path = request_data["path"]
        expire = request_data["expire"] # in unix timestamps
        ## check if the file exists
        if not file.file_exists(conn, user_uuid, path):
            result["message"] = "File does not exist."
            return jsonify(result)
        ## generate an external link and insert it into database
        key = file.create_external_link(conn, user_uuid, path, expire)
        if key == None:
            result["message"] = "Fail to create external link."
            return jsonify(result)
        result["result"] = "OK"
        result["link"] = "https://{}/api/external_link?key={}".format(current_app.config["HOST"], key)
        return jsonify(result)
    ## download from external link
    elif request.method == "GET":
        key = request.args.get("key")
        ## get file information
        user_uuid, filepath = file.query_external_link(conn, key)
        ## check if file exists
        if not file.file_exists(conn, user_uuid, filepath):
            result["message"] = "File not exists."
            return jsonify(result)
        ## get file hash and size
        hash, size = file.get_hash_and_size(conn, user_uuid, filepath)
        if not hash or not size:
            result["message"] = "File not exists."
            return jsonify(result)
        spath = os.path.join(current_app.config["STORAGE_PATH"], hash[0:2], "{}_{}".format(hash, size))
        if not os.path.exists(spath):
            result["message"] = "File accidentally lost."
            return jsonify(result)
        return send_file(spath, as_attachment=True, download_name=os.path.basename(filepath))
    

@file_api.route("/api/all_external_links", methods=["GET"])
def all_external_link():
    result = {
        "result": "FAIL",
        "message": "Success.",
        "links": []
    }
    ## get and check session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["message"] = "Your session is not valid."
        return jsonify(result)
    result["links"] = file.get_all_external_links(conn, user_uuid)
    result["result"] = "OK"
    return jsonify(result)

@file_api.route("/api/remove_external_link", methods=["DELETE"])
def remove_external_link():
    result = {
        "result": "FAIL",
        "message": "Success."
    }
    ## get and check session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["message"] = "Your session is not valid."
        return jsonify(result)
    key = request.args.get("key")
    if file.remove_external_link(conn, user_uuid, key):
        result["result"] = "OK"
    else:
        result["message"] = "Fail to remove external link."
    return jsonify(result)

@file_api.route("/api/replica", methods=["GET"])
def replica():
    ## return if user owns the same file 
    result = {
        "result": "FAIL",
        "exist": False,
        "message": "Success."
    }
    ## get and check session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["message"] = "Your session is not valid."
        return jsonify(result)
    ## check if it exists
    hash = request.args.get("hash")
    size = request.args.get("size")
    files = file.search_by_id(conn, user_uuid, hash, size)
    result["result"] = "OK"
    if len(files) > 0:
        result["exist"] = True
    else:
        result["exist"] = False
    return jsonify(result)

@file_api.route("/api/replica_list", methods=["GET"])
def replica_list():
    result = {
        "result": "FAIL",
        "message": "",
        "files": []
    }
    ## get and check session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["message"] = "Your session is not valid."
        return jsonify(result)
    result["files"] = file.find_replicas(conn, user_uuid)
    result["result"] = "OK"
    result["message"] = "Success."
    return jsonify(result)

@file_api.route("/api/http_download", methods=["POST"])
def http_download():
    result = {
        "result": "FAIL",
        "message": "Success."
    }
    ## get and check session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["message"] = "Your session is not valid."
        return jsonify(result)
    url = request.args.get("url")
    ## generate a task id
    task_id = secrets.token_hex(32)
    ## async download file
    thread = Thread(target=file.download_file_http, args=(conn, user_uuid, url, task_id, current_app.config["STORAGE_PATH"]))
    thread.start()
    result["result"] = "OK"
    result["message"] = "Success."
    result["task_id"] = task_id
    return jsonify(result)

@file_api.route("/api/http_download_tasks", methods=["GET"])
def http_download_tasks():
    result = {
        "result": "FAIL",
        "message": "Success.",
        "tasks": []
    }
    ## get and check session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["message"] = "Your session is not valid."
        return jsonify(result)
    ## get all tasks
    for task_id in file.progress_data:
        url, downloaded, total_size, _ = file.progress_data[task_id]
        result["tasks"].append({
            "task_id": task_id,
            "url": url,
            "downloaded": downloaded,
            "total": total_size
        })
    result["result"] = "OK"
    return jsonify(result)

@file_api.route("/api/http_download_stop", methods=["DELETE"])
def http_download_stop():
    result = {
        "result": "FAIL",
        "message": "Success."
    }
    ## get and check session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["message"] = "Your session is not valid."
        return jsonify(result)
    ## get task id and stop it
    task_id = request.args.get("task_id")
    if file.stop_download(task_id):
        result["result"] = "OK"
    else:
        result["message"] = "Task not found."
    return jsonify(result)


## POST: send a share request to another user
## PUT:  accept a share request from another user
@file_api.route("/api/share_request", methods=["POST", "PUT"])
def share_request():
    result = {
        "result": "FAIL",
        "message": "Success."
    }
    ## get and check session
    session = request.cookies.get("session")
    if request.method == "POST":
        from_user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
        if not from_user_uuid:
            result["message"] = "Your session is not valid."
            return jsonify(result)
        ## get data
        request_data = request.get_json()
        target_user = request_data["target_user"]
        target_user_uuid = auth.get_uuid_by_username(conn, target_user)
        if not target_user_uuid:
            result["message"] = "Target user does not exist."
            return jsonify(result)
        share_path = request_data["share_path"]
        ## check if share path is valid
        if not file.directory_exists(conn, from_user_uuid, share_path):
            result["message"] = "Share path does not exist."
            return jsonify(result)
        ## check if share path is already shared to target user
        if file.check_share(conn, from_user_uuid, share_path, target_user_uuid):
            result["message"] = "Share path is already shared to target user."
            return jsonify(result)
        ## create share request
        if file.create_share_request(conn, from_user_uuid, share_path, target_user_uuid):
            result["result"] = "OK"
        else:
            result["message"] = "Fail to create share request."
        utils.log(utils.LEVEL_INFO, "User [{}] send a share request to [{}] for [{}]".format(from_user_uuid, target_user_uuid, share_path))
        return jsonify(result)
    elif request.method == "PUT":
        to_user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
        if not to_user_uuid:
            result["message"] = "Your session is not valid."
            return jsonify(result)
        ## get data
        request_data = request.get_json()
        notification_uuid = request_data["notification_uuid"]
        path = request_data["path"] # link directory
        ## create the path
        if file.directory_exists(conn, to_user_uuid, path):
            result["message"] = "The Path already exists."
            return jsonify(result)
        ## chenk if there is the share request from another user
        if not notification.check_notification(conn, notification_uuid):
            result["message"] = "Share request does not exist."
            return jsonify(result)
        ## get share request info
        info = notification.get_notification(conn, notification_uuid)
        if not info:
            result["message"] = "Share request does not exist."
            return jsonify(result)
        if file.create_link(conn, info["to_user_uuid"], path, info["from_user_uuid"], info["meta"]):
            result["result"] = "OK"
            ## remove notification
            notification.remove_notification(conn, notification_uuid)
        else:
            result["message"] = "Fail to create link."
        return jsonify(result)