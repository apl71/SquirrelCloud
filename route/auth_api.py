from flask import Blueprint, current_app, request, jsonify, redirect
from app import conn
from db import auth
from db import file
import utils

auth_api = Blueprint("auth_api", __name__)

@auth_api.route("/api/login", methods=["POST"])
def login():
    request_data = request.get_json(silent=True)
    if not isinstance(request_data, dict):
        utils.log(utils.LEVEL_INFO, "Login fail: invalid or missing JSON body.")
        return jsonify({"result": "FAIL", "message": "Invalid request body."})

    required_keys = {"username", "password"}
    if not required_keys.issubset(request_data.keys()):
        utils.log(utils.LEVEL_INFO, "Login fail: missing username/password fields.")
        return jsonify({"result": "FAIL", "message": "Missing username or password."})

    username = request_data.get("username")
    password = request_data.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        utils.log(utils.LEVEL_INFO, "Login fail: username/password must be strings.")
        return jsonify({"result": "FAIL", "message": "Invalid username or password."})
    ## check password in database
    uuid, session = auth.check_user_login(conn, username, password)
    admin = auth.check_admin_user(conn, uuid)
    success = True if uuid else False
    result = {
        "result": "OK" if success else "FAIL"
    }
    response = current_app.make_response(jsonify(result))
    if success:
        response.set_cookie("session", value=session, httponly=True, secure=True)
        response.set_cookie("username", value=username, httponly=False, secure=True)
        response.set_cookie("admin", value="true" if admin else "false", httponly=False, secure=True)
        utils.log(utils.LEVEL_INFO, "User {} login, is admin: {}.".format(username, admin))
    else:
        utils.log(utils.LEVEL_INFO, "User {} login fail.".format(username))
    return response

@auth_api.route("/api/logout", methods=["DELETE"])
def logout():
    result = {
        "result": "OK"
    }
    session = request.cookies.get("session")
    auth.remove_session(conn, session)
    return jsonify(result)

@auth_api.route("/api/password", methods=["POST"])
def reset_password():
    result = {
        "result": "FAIL",
        "message": "Password changed."
    }
    ## check session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["message"] = "Your session is not valid."
        return jsonify(result)
    ## get new password from body
    request_data = request.get_json(silent=True)
    if not isinstance(request_data, dict):
        result["message"] = "Invalid request body."
        return jsonify(result)

    required_keys = {"old_password", "new_password"}
    if not required_keys.issubset(request_data.keys()):
        result["message"] = "Missing required fields."
        return jsonify(result)

    old_password = request_data.get("old_password")
    new_password = request_data.get("new_password")

    if not isinstance(old_password, str) or not isinstance(new_password, str):
        result["message"] = "Invalid field types."
        return jsonify(result)
    ## check if old_password is right
    username = auth.get_username_by_uuid(conn, user_uuid)
    user_uuid_2, _ = auth.check_user_login(conn, username, old_password)
    if user_uuid != user_uuid_2:
        result["message"] = "Old password does not work."
        return jsonify(result)
    ## change password
    if auth.update_password(conn, user_uuid, new_password):
        result["result"] = "OK"
        utils.log(utils.LEVEL_INFO, "User {} change password.".format(username))
    else:
        result["message"] = "Update fail. Check logs."
    return jsonify(result)

@auth_api.route("/api/register", methods=["PUT"])
def register():
    result = {
        "result": "FAIL",
        "message": "User created."
    }
    ## check session, admin session required
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["message"] = "Your session is not valid."
        return jsonify(result)
    if not auth.check_admin_user(conn, user_uuid):
        result["message"] = "You are not administrator."
        return jsonify(result)
    ## get information of new user
    request_data = request.get_json(silent=True)
    if not isinstance(request_data, dict):
        result["message"] = "Invalid request body."
        return jsonify(result)

    required_keys = {"username", "password", "admin", "email"}
    if not required_keys.issubset(request_data.keys()):
        result["message"] = "Missing required fields."
        return jsonify(result)

    username = request_data.get("username")
    password = request_data.get("password")
    admin_value = request_data.get("admin")
    email = request_data.get("email")

    if (
        not isinstance(username, str)
        or not isinstance(password, str)
        or not isinstance(admin_value, str)
        or not isinstance(email, str)
    ):
        result["message"] = "Invalid field types."
        return jsonify(result)

    admin = True if admin_value == "true" else False
    ## check if username already exists
    if auth.check_user_exist(conn, username):
        result["message"] = "Username is occupied. Try another!"
        return jsonify(result)
    new_uuid = auth.create_user(conn, username, password, admin, email)
    if new_uuid == None:
        result["message"] = "Fail to create new user."
        return jsonify(result)
    ok, message = file.create_directory(conn, new_uuid, "/")
    if not ok:
        result["message"] = message
        return jsonify(result)

    ok, message = file.create_directory(conn, new_uuid, "/recycle")
    if not ok:
        result["message"] = message
        return jsonify(result)
    result["result"] = "OK"
    utils.log(utils.LEVEL_INFO, "User {} created by admin.".format(username))
    return jsonify(result)

## check if session is valid
@auth_api.route("/api/session_status", methods=["GET"])
def session_status():
    ## check session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        return redirect("/login.html")
    else:
        return jsonify({"result": "OK"})