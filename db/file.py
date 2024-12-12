from datetime import datetime
import utils

## check if a user owns a directory
def directory_exists(conn, user_uuid: str, path: str) -> bool:
    return directory_or_file_exists(conn, user_uuid, path, "TYPE_DIR")

## check if a user owns a file
def file_exists(conn, user_uuid: str, path: str) -> bool:
    return directory_or_file_exists(conn, user_uuid, path, "TYPE_FILE")

def directory_or_file_exists(conn, user_uuid: str, path: str, type: str) -> bool:
    sql = "SELECT uuid FROM File WHERE path = %s AND owner_uuid = %s AND type = %s"
    cursor = conn.cursor()
    cursor.execute(sql, (path, user_uuid, type))
    result = cursor.fetchall()
    if len(result) == 0:
        return False
    else:
        return True
    
## insert a new file
def insert_file(conn, user_uuid: str, path: str, hash: str, size: int):
    sql = "INSERT INTO File (owner_uuid, type, hash, size, path) VALUES (%s, %s, %s, %s, %s)"
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (user_uuid, "TYPE_FILE", hash, size, path))
        conn.commit()
    except Exception as e:
        utils.log("Fail to execute SQL statement in `insert_file()`: {}".format(e))
        conn.rollback()
        return False
    cursor.close()
    return True

def get_hash_and_size(conn, user_uuid: str, path: str) -> tuple[str, int]:
    sql = "SELECT hash, size FROM File WHERE owner_uuid = %s AND path = %s AND type = 'TYPE_FILE'"
    cursor = conn.cursor()
    cursor.execute(sql, (user_uuid, path))
    result = cursor.fetchall()
    if len(result) == 0:
        return (None, None)
    return result[0][0], result[0][1]

## return the type of file:
## Regular file : TYPE_FILE
## Directory    : TYPE_DIR
## Not exists   : None
def get_file_type(conn, user_uuid: str, path: str) -> str:
    sql = "SELECT type FROM File WHERE owner_uuid = %s AND path = %s"
    cursor = conn.cursor()
    cursor.execute(sql, (user_uuid, path))
    result = cursor.fetchall()
    if len(result) == 0:
        return None
    return result[0][0]

## before calling, make sure `path` is a file by calling `get_file_type()`
def remove_file(conn, user_uuid: str, path: str):
    sql = "DELETE FROM File WHERE owner_uuid = %s AND path = %s AND type = 'TYPE_FILE'"
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (user_uuid, path))
        conn.commit()
    except Exception as e:
        utils.log("Fail to execute SQL statement in `remove_file()`: {}".format(e))
        conn.rollback()
        return False
    cursor.close()
    return True

def remove_dir(conn, user_uuid: str, path: str):
    sql = "DELETE FROM File WHERE owner_uuid = %s AND path LIKE %s OR path = %s"
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (user_uuid, "{}/%".format(path), path))
        conn.commit()
    except Exception as e:
        utils.log("Fail to execute SQL statement in `remove_dir()`: {}".format(e))
        conn.rollback()
        return False
    cursor.close()
    return True

## get file infomation under specific path
def list_file(conn, user_uuid: str, path: str) -> list:
    query = "{}%".format(path)
    sql = "SELECT path, size, type, remark, create_at, pinned, tag_uuid FROM File WHERE owner_uuid = %s AND path LIKE %s AND path NOT LIKE %s AND path != %s"
    cursor = conn.cursor()
    cursor.execute(sql, (user_uuid, query, "{}_%/%".format(path), path))
    result = cursor.fetchall()
    file_infos = []
    for info in result:
        file_infos.append({
            "path": info[0],
            "size": info[1],
            "type": info[2],
            "remark": info[3],
            "create_at": info[4],
            "pinned": info[5],
            "tags": [get_tag_by_uuid(conn, uuid) for uuid in info[6]]
        })
    return file_infos

def create_directory(conn, user_uuid: str, newdir: str):
    sql = "INSERT INTO File (owner_uuid, type, path) VALUES (%s, 'TYPE_DIR', %s)"
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (user_uuid, newdir))
        conn.commit()
    except Exception as e:
        utils.log("Fail to execute SQL statement in `create_directory()`: {}".format(e))
        conn.rollback()
        return False
    cursor.close()
    return True

## search file or directory containing certain substring
def search(conn, user_uuid: str, query: str) -> list:
    sql = "SELECT path, size, type, remark, create_at, pinned, tag_uuid FROM File WHERE owner_uuid = %s AND path LIKE %s"
    cursor = conn.cursor()
    cursor.execute(sql, (user_uuid, "%{}%".format(query)))
    result = cursor.fetchall()
    file_infos = []
    for info in result:
        file_infos.append({
            "path": info[0],
            "size": info[1],
            "type": info[2],
            "remark": info[3],
            "create_at": info[4],
            "pinned": info[5],
            "tags": [get_tag_by_uuid(conn, uuid) for uuid in info[6]]
        })
    return file_infos

## search file by hash and size(fileid)
## return the list of uuids of files if exist, otherwise return empty list
def search_by_id(conn, user_uuid: str, hash: str, size: int) -> list:
    sql = "SELECT uuid FROM File WHERE owner_uuid = %s AND hash = %s AND size = %s"
    cursor = conn.cursor()
    cursor.execute(sql, (user_uuid, hash, str(size)))
    result = cursor.fetchall()
    return [uuid[0] for uuid in result]

## search path by uuid, return None if not exists
def search_by_uuid(conn, user_uuid: str, file_uuid: str):
    sql = "SELECT path FROM File WHERE owner_uuid = %s AND uuid = %s"
    cursor = conn.cursor()
    cursor.execute(sql, (user_uuid, file_uuid))
    result = cursor.fetchall()
    if len(result) > 0:
        return result[0][0]
    else:
        return None

## update remark of a file or directory
def update_remark(conn, user_uuid: str, path: str, remark: str):
    sql = "UPDATE File SET remark = %s WHERE owner_uuid = %s AND path = %s"
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (remark, user_uuid, path))
        conn.commit()
    except Exception as e:
        utils.log("Fail to execute SQL statement in `update_remark()`: {}".format(e))
        conn.rollback()
        return False
    cursor.close()
    return True

## pin or unpin a file or directory
## `pin` = True  -> pin a file, if it is already pinned, do nothing
## `pin` = False -> unpin a file, if it is not pinned, do nothing
def pin_or_unpin_file(conn, user_uuid: str, path: str, pin: bool):
    sql = "UPDATE File SET pinned = %s WHERE owner_uuid = %s and path = %s"
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (pin, user_uuid, path))
        conn.commit()
    except Exception as e:
        utils.log("Fail to execute SQL statement in `pin_or_unpin_file()`: {}".format(e))
        conn.rollback()
        return False
    cursor.close()
    return True

def create_tag(conn, user_uuid: str, tag: str):
    sql = "INSERT INTO Tag (text, owner_uuid) VALUES (%s, %s)"
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (tag, user_uuid))
        conn.commit()
    except Exception as e:
        utils.log("Fail to execute SQL statement in `create_tag()`: {}".format(e))
        conn.rollback()
        return False
    cursor.close()
    return True

def get_tags(conn, user_uuid: str):
    sql = "SELECT text FROM Tag WHERE owner_uuid = %s"
    cursor = conn.cursor()
    cursor.execute(sql, (user_uuid,))
    result = cursor.fetchall()
    tags = []
    for info in result:
        tags.append(info[0])
    return tags

def remove_tag(conn, user_uuid: str, tag_uuid: str):
    sql = "DELETE FROM Tag WHERE uuid = %s AND owner_uuid = %s"
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (tag_uuid, user_uuid))
        conn.commit()
    except Exception as e:
        utils.log("Fail to execute SQL statement in `remove_tag()`: {}".format(e))
        conn.rollback()
        return False
    cursor.close()
    return True

def get_tag_by_uuid(conn, tag_uuid: str) -> str:
    sql = "SELECT text FROM Tag WHERE uuid = %s"
    cursor = conn.cursor()
    cursor.execute(sql, (tag_uuid,))
    result = cursor.fetchall()
    if len(result) == 0:
        return None
    else:
        return result[0][0]

def rename_file_or_directory(conn, user_uuid: str, path: str, new_path: str, type: str):
    cursor = conn.cursor()
    if type == "DIR":
        sql = "UPDATE File SET path = REGEXP_REPLACE(path, %s, %s) WHERE owner_uuid = %s"
        params = ('^{}/'.format(path), '{}/'.format(new_path), user_uuid)
        cursor.execute(sql, params)
    sql = "UPDATE File SET path = %s WHERE path = %s AND owner_uuid = %s"
    try:
        cursor.execute(sql, (new_path, path, user_uuid))
        conn.commit()
    except Exception as e:
        utils.log("Fail to execute SQL statement in `rename_file_or_directory()`: {}".format(e))
        conn.rollback()
        return False
    cursor.close()
    return True

## check if the user owns the tag, if so, return the uuid of the tag, otherwise return None
def check_user_own_tag(conn, user_uuid: str, tag: str) -> str:
    sql = "SELECT uuid FROM Tag WHERE text = %s AND owner_uuid = %s"
    cursor = conn.cursor()
    cursor.execute(sql, (tag, user_uuid))
    result = cursor.fetchall()
    if len(result) == 0:
        return None
    else:
        return result[0][0]

## attach a tag to a file, this function will not check if the tag is owned by the user
def attach_tag_to_file(conn, user_uuid: str, tag_uuid: str, path: str):
    sql = "UPDATE File SET tag_uuid = array_append(tag_uuid, %s) WHERE path = %s AND owner_uuid = %s"
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (tag_uuid, path, user_uuid))
        conn.commit()
    except Exception as e:
        utils.log("Fail to execute SQL statement in `attach_tag_to_file()`: {}".format(e))
        conn.rollback()
        return False
    cursor.close()
    return True

## check if the file is already tagged with the tag
def check_file_tag_exists(conn, user_uuid: str, tag_uuid: str, path: str) -> bool:
    sql = "SELECT tag_uuid FROM File WHERE path = %s AND owner_uuid = %s"
    cursor = conn.cursor()
    cursor.execute(sql, (path, user_uuid))
    result = cursor.fetchall()
    if len(result) == 0:
        return False
    elif tag_uuid in result[0][0]:
        return True
    return False

def remove_tag_from_file(conn, user_uuid: str, tag_uuid: str, path: str):
    sql = "UPDATE File SET tag_uuid = array_remove(tag_uuid, %s) WHERE path = %s AND owner_uuid = %s"
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (tag_uuid, path, user_uuid))
        conn.commit()
    except Exception as e:
        utils.log("Fail to execute SQL statement in `remove_tag_from_file()`: {}".format(e))
        conn.rollback()
        return False
    cursor.close()
    return True

## return a 64-length sharing key if succeed
def create_external_link(conn, user_uuid: str, path: str, expire: int) -> str:
    expire = datetime.fromtimestamp(expire)
    sql = "INSERT INTO ExternalLink (user_uuid, file_path, expire) VALUES (%s, %s, %s)"
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (user_uuid, path, expire))
        conn.commit()
    except Exception as e:
        utils.log("Fail to execute SQL statement in `create_external_link()`: {}".format(e))
        conn.rollback()
        return None
    ## query the key
    sql = "SELECT share_key FROM ExternalLink WHERE user_uuid = %s AND file_path = %s"
    cursor.execute(sql, (user_uuid, path))
    result = cursor.fetchall()
    cursor.close()
    if len(result) == 0:
        return None
    else:
        return result[0][0]

## return (user_uuid, file_path)
def query_external_link(conn, key: str) -> tuple[str, str]:
    sql = "SELECT user_uuid, file_path FROM ExternalLink WHERE share_key = %s"
    cursor = conn.cursor()
    cursor.execute(sql, (key,))
    result = cursor.fetchall()
    if len(result) == 0:
        return None
    else:
        return (result[0][0], result[0][1])

## find all replicas
def find_replicas(conn, user_uuid: str) -> list:
    sql = "SELECT ARRAY_AGG(path), hash, size FROM File WHERE owner_uuid = %s AND type = 'TYPE_FILE' GROUP BY hash, size HAVING COUNT(*) > 1"
    cursor = conn.cursor()
    cursor.execute(sql, (user_uuid, ))
    result = cursor.fetchall()
    print(result)
    result_list = []
    for info in result:
        result_list.append({
            "paths": info[0],
            "hash":  info[1],
            "size":  info[2]
        })
    return result_list