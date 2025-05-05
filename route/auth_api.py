from flask import Blueprint, current_app, request, jsonify, redirect
from app import conn
from db import auth
from db import file
import utils

auth_api = Blueprint("auth_api", __name__)

@auth_api.route("/api/login", methods=["POST"])
def login():
    request_data = request.get_json()
    username = request_data["username"]
    password = request_data["password"]
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
    request_data = request.get_json()
    old_password = request_data["old_password"]
    new_password = request_data["new_password"]
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
    request_data = request.get_json()
    username = request_data["username"]
    password = request_data["password"]
    admin = True if request_data["admin"] == "true" else False
    email = request_data["email"]
    ## check if username already exists
    if auth.check_user_exist(conn, username):
        result["message"] = "Username is occupied. Try another!"
        return jsonify(result)
    new_uuid = auth.create_user(conn, username, password, admin, email)
    if new_uuid == None:
        result["message"] = "Fail to create new user."
        return jsonify(result)
    ## create root for new user
    if not file.create_directory(conn, new_uuid, "/"):
        result["message"] = "Fail to create root for new user."
        return jsonify(result)
    ## create recycle bin for new user
    if not file.create_directory(conn, new_uuid, "/recycle"):
        result["message"] = "Fail to create recycle bin for new user."
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