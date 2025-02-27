import utils

def get_all_notifications(conn, user_uuid):
    sql = "SELECT uuid, title, content, type, create_at FROM Notification WHERE to_user_uuid = %s"
    cursor = conn.cursor()
    cursor.execute(sql, (user_uuid,))
    notifications = cursor.fetchall()
    cursor.close()
    result = []
    for notification in notifications:
        result.append({
            "uuid": notification[0],
            "title": notification[1],
            "content": notification[2],
            "type": notification[3],
            "create_at": notification[4]
        })
    return result

def create_notification(conn, from_user_uuid, to_user_uuid, title, content, type, meta):
    if type not in ["TYPE_INFO", "TYPE_SHARE_REQUEST"]:
        utils.log(utils.LEVEL_WARNING, "Invalid type in `create_notification()`: {}".format(type))
        return False
    sql = "INSERT INTO Notification (from_user_uuid, to_user_uuid, title, content, type, meta) VALUES (%s, %s, %s, %s, %s, %s)"
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (from_user_uuid, to_user_uuid, title, content, type, meta))
        conn.commit()
    except Exception as e:
        utils.log(utils.LEVEL_WARNING, "Fail to execute SQL statement in `create_notification()`: {}".format(e))
        conn.rollback()
        return False
    cursor.close()
    return True

def remove_notification(conn, notification_uuid):
    sql = "DELETE FROM Notification WHERE  uuid = %s"
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (notification_uuid,))
        conn.commit()
    except Exception as e:
        utils.log(utils.LEVEL_WARNING, "Fail to execute SQL statement in `remove_notification()`: {}".format(e))
        conn.rollback()
        return False
    cursor.close()
    return True

def check_notification(conn, uuid):
    sql = "SELECT COUNT(*) FROM Notification WHERE uuid = %s and create_at > now() - interval '3 day'"
    cursor = conn.cursor()
    cursor.execute(sql, (uuid,))
    count = cursor.fetchone()[0]
    cursor.close()
    return count > 0

def get_notification(conn, uuid):
    sql = "SELECT from_user_uuid, to_user_uuid, title, content, type, meta FROM Notification WHERE uuid = %s"
    cursor = conn.cursor()
    cursor.execute(sql, (uuid,))
    result = cursor.fetchone()
    cursor.close()
    return {
        "from_user_uuid": result[0],
        "to_user_uuid": result[1],
        "title": result[2],
        "content": result[3],
        "type": result[4],
        "meta": result[5]
    }