from flask import Blueprint, current_app, request, jsonify
import utils
from app import get_db
from db import notification, auth

function_api = Blueprint("notification_api", __name__)

@function_api.route("/api/notification", methods=["GET", "DELETE"])
def get_all_notifications():
    conn = get_db()

    ## check session
    session = request.cookies.get("session")
    user_uuid = auth.check_session(conn, session, current_app.config["SESSION_LIFESPAN"])
    if not user_uuid:
        return jsonify(utils.make_result(False, "Your session is not valid."))

    if request.method == "GET":
        ## get notifications
        notifications = notification.get_all_notifications(conn, user_uuid)
        return jsonify(utils.make_result(True, "Success.", notifications=notifications))
    elif request.method == "DELETE":
        ## delete notification
        request_data = request.get_json()
        notification_uuid = request_data["uuid"]
        if not notification_uuid:
            return jsonify(utils.make_result(False, "No notification uuid provided."))
        if notification.remove_notification(conn, notification_uuid):
            return jsonify(utils.make_result(True, "Success."))
        else:
            return jsonify(utils.make_result(False, "Fail to delete notification."))