from flask import Blueprint, current_app, request, jsonify
from app import conn
from db import notification, auth

function_api = Blueprint("notification_api", __name__)

@function_api.route("/api/notification", methods=["GET", "DELETE"])
def get_all_notifications():
    result = {
        "result": "FAIL",
        "message": "Success."
    }
    ## check session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        result["message"] = "Your session is not valid."
        return jsonify(result)
    if request.method == "GET":
        ## get notifications
        notifications = notification.get_all_notifications(conn, user_uuid)
        result["result"] = "OK"
        result["notifications"] = notifications
        return jsonify(result)
    elif request.method == "DELETE":
        ## delete notification
        request_data = request.get_json()
        notification_uuid = request_data["uuid"]
        if not notification_uuid:
            result["message"] = "No notification uuid provided."
            return jsonify(result)
        if notification.remove_notification(conn, notification_uuid):
            result["result"] = "OK"
        else:
            result["message"] = "Fail to delete notification."
        return jsonify(result)