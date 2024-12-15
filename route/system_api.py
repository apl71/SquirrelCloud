from flask import Blueprint, current_app, request, jsonify, redirect, url_for
from app import conn
from db import auth
import shutil
import utils
import requests, os
import toml

system_api = Blueprint("system_api", __name__)

@system_api.route("/", methods=["GET"])
def index():
    return redirect(url_for("static", filename="app.html"))

@system_api.route("/api/version", methods=["GET"])
def version():
    result = {
        "result": "OK",
        "message": current_app.config["VERSION"]
    }
    return jsonify(result)

@system_api.route("/api/check_update", methods=["GET"])
def check_update():
    result = {
        "result": "FAIL",
        "message": ""
    }
    ## check for admin session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["message"] = "Your session is not valid."
        return jsonify(result)
    if not auth.check_admin_user(conn, user_uuid):
        result["message"] = "You are not administrator."
        return jsonify(result)
    ## get latest version
    latest = utils.check_update()
    if latest == None:
        result["message"] = "Fail to get latest version number."
    else:
        result["result"] = "OK"
        result["message"] = latest
    return jsonify(result)

@system_api.route("/api/update", methods=["GET"])
def update_system():
    result = {
        "result": "FAIL",
        "message": "Success."
    }
    ## check for admin session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["message"] = "Your session is not valid."
        return jsonify(result)
    if not auth.check_admin_user(conn, user_uuid):
        result["message"] = "You are not administrator."
        return jsonify(result)
    ## save configuration file to dict
    conf = open("{}/app.conf".format(current_app.config["CODE_PATH"]), "r")
    original_conf = toml.load(conf)
    ## fetch new sources
    latest = utils.check_update()
    if latest == None:
        result["message"] = "Fail to fetch new version number."
        return jsonify(result)
    http_path = "http://{}/download/squirrelcloud-{}.zip".format(current_app.config["UPDATE_SERVER"], latest)
    new_source_zip = requests.get(http_path)
    if new_source_zip.status_code != 200:
        result["message"] = "Fail to fetch new source."
        return jsonify(result)
    else:
        zip_file = open("temp_source.zip", "wb")
        zip_file.write(new_source_zip.content)
    ## zip old sources
    os.system('zip -q -r squirrelcloud-{}.zip {} -x "__pycache__/" "*/__pycache__/" "*.pyc" "*.zip"'.format(current_app.config["VERSION"], current_app.config["CODE_PATH"]))
    ## unzip new sources
    os.system('unzip -o temp_source.zip -d {}'.format(current_app.config["CODE_PATH"]))
    ## read new config
    conf = open("{}/app.conf".format(current_app.config["CODE_PATH"]), "r")
    new_conf = toml.load(conf)
    for key, value in new_conf.items():
        if not key in original_conf.keys():
            original_conf[key] = value
    ## write new config
    conf = open("{}/app.conf".format(current_app.config["CODE_PATH"]), "w")
    toml.dump(original_conf, conf)
    ## remove temp sources
    os.system('rm temp_source.zip')
    ## restart server
    utils.kill_program()

@system_api.route("/api/disk_usage", methods=["GET"])
def disk_usage():
    result = {
        "result": "FAIL",
        "message": "Success.",
        "total_space": 0,
        "used_space": 0,
        "app_used_space": 0
    }
    ## get and check session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["message"] = "Your session is not valid."
        return jsonify(result)
    if not auth.check_admin_user(conn, user_uuid):
        result["message"] = "You are not administrator."
        return jsonify(result)
    ## get data
    root = current_app.config["STORAGE_PATH"]
    result["total_space"], result["used_space"], _ = shutil.disk_usage(root)
    result["app_used_space"] = utils.get_directory_size(root)
    ## return
    result["result"] = "OK"
    return jsonify(result)

## get all users, only for admin
@system_api.route("/api/all_users", methods=["GET"])
def all_users():
    result = {
        "result": "FAIL",
        "message": "Success.",
        "users": []
    }
    ## get and check session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["message"] = "Your session is not valid."
        return jsonify(result)
    if not auth.check_admin_user(conn, user_uuid):
        result["message"] = "You are not administrator."
        return jsonify(result)
    ## get all users
    result["users"] = auth.get_all_users(conn)
    ## return
    result["result"] = "OK"
    return jsonify(result)