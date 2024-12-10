import secrets
import datetime
import utils

## create n-bit cryptographical random string for session value
def create_session(n: int) -> str:
    return secrets.token_hex(n // 4)

## check user login, if success, return the uuid of the user and the session
## otherwise, return (None, None)
def check_user_login(conn, username: str, password: str) -> tuple[str, str]:
    sql = "SELECT (pswhash = crypt(%s, pswhash))::boolean as psw, uuid FROM AppUser WHERE username = %s"
    cursor = conn.cursor()
    cursor.execute(sql, (password, username))
    result = cursor.fetchall()
    if result == [] or not result[0][0]:
        cursor.close()
        return (None, None)
    else:
        uuid = result[0][1]
        session = create_session(128)
        sql = "INSERT INTO Session (user_uuid, session) VALUES (%s, %s)"
        try:
            cursor.execute(sql, (uuid, session))
            conn.commit()
        except Exception as e:
            utils.log("Fail to execute SQL statement in `check_user_login()`: {}".format(e))
            conn.rollback()
            return (None, None)
        cursor.close()
        return (uuid, session)

## get username by uuid, return None if the uuid does not exist
def get_username_by_uuid(conn, user_uuid: str) -> str:
    sql = "SELECT username FROM AppUser WHERE uuid = %s"
    cursor = conn.cursor()
    cursor.execute(sql, (user_uuid,))
    result = cursor.fetchall()
    if result == []:
        return None
    else:
        return result[0][0]

def get_uuid_by_username(conn, username: str) -> str:
    sql = "SELECT uuid FROM AppUser WHERE username = %s"
    cursor = conn.cursor()
    cursor.execute(sql, (username,))
    result = cursor.fetchall()
    if result == []:
        return None
    else:
        return result[0][0]

## update password
def update_password(conn, user_uuid: str, new_password: str):
    sql = "UPDATE AppUser SET pswhash = crypt(%s, gen_salt('md5')) WHERE uuid = %s"
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (new_password, user_uuid))
        conn.commit()
    except Exception as e:
        utils.log("Fail to execute SQL statement in `update_password()`: {}".format(e))
        conn.rollback()
        return False
    cursor.close()
    return True

## check if a session is valid, if so, return the uuid of the user
## otherwise, return None
def check_session(conn, session: str, lifespan: int) -> str:
    remove_expired_session(conn, lifespan)
    sql = "SELECT user_uuid, create_at FROM Session WHERE session = %s"
    cursor = conn.cursor()
    cursor.execute(sql, (session,))
    result = cursor.fetchall()
    if len(result) == 0:
        return None
    else:
        return result[0][0]

def remove_expired_session(conn, lifespan: int):
    sql = "DELETE FROM Session WHERE create_at < %s"
    current_time = datetime.datetime.now()
    delta = datetime.timedelta(minutes=lifespan)
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (current_time - delta,))
        conn.commit()
    except Exception as e:
        utils.log("Fail to execute SQL statement in `remove_expired_session()`: {}".format(e))
        conn.rollback()
        return False
    cursor.close()
    return True

## remove specific session
def remove_session(conn, session: str):
    sql = "DELETE FROM Session WHERE session = %s"
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (session,))
        conn.commit()
    except Exception as e:
        utils.log("Fail to execute SQL statement in `remove_session()`: {}".format(e))
        conn.rollback()
        return False
    cursor.close()
    return True

## check if an user exists, if so, return uuid
## else return None
def check_user_exist(conn, username: str) -> str:
    sql = "SELECT uuid FROM AppUser WHERE username = %s"
    cursor = conn.cursor()
    cursor.execute(sql, (username,))
    result = cursor.fetchall()
    if len(result) == 0:
        return None
    else:
        return result[0][0]

## check if an user is admin or not
## if a uuid does not exist, return false
def check_admin_user(conn, user_uuid: str) -> bool:
    if user_uuid == None:
        return False
    sql = "SELECT role FROM AppUser WHERE uuid = %s"
    cursor = conn.cursor()
    cursor.execute(sql, (user_uuid,))
    result = cursor.fetchall()
    if len(result) == 0 or result[0][0] != "ROLE_ADMIN":
        return False
    else:
        return True
    
## create new user, and return his/her uuid
def create_user(conn, username: str, password: str, admin: bool, email: str) -> str:
    role = "ROLE_ADMIN" if admin else "ROLE_USER"
    sql = """
        INSERT INTO AppUser 
        (username, email, pswhash, role) VALUES 
        (%s, %s, crypt(%s, gen_salt('md5')), %s)
        """
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (username, email, password, role))
        conn.commit()
    except Exception as e:
        utils.log("Fail to execute SQL statement in `create_user()`: {}".format(e))
        conn.rollback()
        return None
    cursor.close()
    return get_uuid_by_username(conn, username)