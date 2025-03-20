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
    ## fetch new version number
    latest = utils.check_update()
    if latest == None:
        result["message"] = "Fail to fetch new version number."
        return jsonify(result)
    ## fetch metadata
    mata_path = "{}/api/package?version={}".format(current_app.config["UPDATE_SERVER"], latest)
    metadata = requests.get(mata_path).json()
    if metadata["result"] != "OK":
        result["message"] = "Fail to fetch metadata."
        return jsonify(result)
    ## fetch new sources
    http_path = "{}/api/download?version={}".format(current_app.config["UPDATE_SERVER"], latest)
    new_source_zip = requests.get(http_path)
    if new_source_zip.status_code != 200:
        result["message"] = "Fail to fetch new source."
        return jsonify(result)
    else:
        zip_file = open("temp_source.zip", "wb")
        zip_file.write(new_source_zip.content)
        ## compute checksum
        hash = utils.hash_file("temp_source.zip")
        if hash != metadata["hash"]:
            result["message"] = "Checksum failed. Expected: {}, Got: {}".format(metadata["hash"], hash)
            return jsonify(result)
        zip_file.close()
    ## zip old sources
    zip_cmd = 'zip -q -r squirrelcloud-{}.zip {} -x "__pycache__/" "*/__pycache__/" "*.pyc" "*.zip" ".venv/" "venv" ".venv/*" "*/.pytest_cache/" ".pytest_cache/*" ".pytest_cache/" "*/.git/" ".git/" ".git/*" "*/.gitignore" ".gitignore" "*/.DS_Store" ".DS_Store" "*/.vscode/" ".vscode/" "*/.idea/" ".idea/" "*/.gitlab-ci.yml" '.format(current_app.config["VERSION"], current_app.config["CODE_PATH"])
    os.system(zip_cmd)
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

@system_api.route("/api/get_theme", methods=["GET"])
def get_theme():
    result = {
        "result": "OK",
        "theme": [file for file in os.listdir("{}/static/css".format(current_app.config["CODE_PATH"])) if file.endswith("-theme.css")]
    }
    return jsonify(result)

@system_api.route("/api/get_plugins", methods=["GET"])
def get_plugins():
    result = {}
    ## get and check session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["plugins"] = None
        result["result"] = "FAIL"
        result["message"] = "Your session is not valid."
    else:
        result["plugins"] = current_app.plugin_list
        result["result"] = "OK"
    return jsonify(result)

## TODO: get logs
@system_api.route("/api/get_logs", methods=["GET"])
def get_logs():
    result = {
        "result": "OK",
        "logs": []
    }
    return jsonify(result)

@system_api.route("/api/get_remote_plugins", methods=["GET"])
def get_remote_plugins():
    result = {
        "result": "OK",
        "plugins": []
    }
    http_path = "{}/list.html".format(current_app.config["PLUGIN_SERVER"])
    plugin_list = requests.get(http_path)
    if plugin_list.status_code != 200:
        result["result"] = "FAIL"
        result["message"] = "Fail to fetch plugin list."
        return jsonify(result)
    plugin_names = [item for item in plugin_list.text.split("\n") if item.strip() != ""]
    for plugin_name in plugin_names:
        http_path = "{}/{}/latest.html".format(current_app.config["PLUGIN_SERVER"], plugin_name)
        plugin_version = requests.get(http_path)
        if plugin_version.status_code != 200:
            continue
        plugin_version = plugin_version.text.strip()
        result["plugins"].append({
            "name": plugin_name,
            "version": plugin_version
        })
    return jsonify(result)

@system_api.route("/api/install_plugin", methods=["POST"])
def install_plugin():
    result = {
        "result": "FAIL",
        "message": "Success. Restart server to take effect."
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
    ## get plugin name
    plugin_name = request.args.get("name")
    plugin_version = request.args.get("version")
    reinstall = request.args.get("reinstall")
    ## check if plugin is already installed
    if reinstall == "false" and any(plugin["name"] == "{}_plugin".format(plugin_name) and plugin["version"] == plugin_version for plugin in current_app.plugin_list):
        result["message"] = "Latest plugin is already installed."
        return jsonify(result)
    ## formulate url
    http_path = "{}/{}/{}_plugin-{}.zip".format(current_app.config["PLUGIN_SERVER"], plugin_name, plugin_name, plugin_version)
    ## fetch plugin
    plugin_zip = requests.get(http_path)
    if plugin_zip.status_code != 200:
        result["message"] = "Fail to fetch plugin."
        return jsonify(result)
    else:
        zip_file = open("temp_plugin.zip", "wb")
        zip_file.write(plugin_zip.content)
        zip_file.close()
    ## unzip plugin
    os.system('unzip -o temp_plugin.zip -d {}/plugin'.format(current_app.config["CODE_PATH"]))
    ## remove temp sources
    os.system('rm temp_plugin.zip')
    result["result"] = "OK"
    return jsonify(result)

@system_api.route("/api/host", methods=["GET"])
def host():
    result = {
        "result": "OK",
        "host": current_app.config["HOST"]
    }
    return jsonify(result)