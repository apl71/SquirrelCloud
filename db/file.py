from datetime import datetime
import utils
import requests
import uuid
import os
import shutil
from db import auth, notification

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
        return directory_or_file_exists_with_link(conn, user_uuid, path, type)
    else:
        return True

## given a path with link in it, convert it to the target path
## return [target_user_uuid, target_path, link_path] if succeed, otherwise return [None, None, None]
def convert_path_with_link(conn, user_uuid: str, path: str) -> str:
    nodes = path.split("/")[1:]
    nodes[0] = "/" + nodes[0]
    for i in range(1, len(nodes) + 1):
        sql = "SELECT path FROM File WHERE path = %s AND owner_uuid = %s AND type = 'TYPE_LINK'"
        cursor = conn.cursor()
        subpath = "/".join(nodes[0:i])
        cursor.execute(sql, (subpath, user_uuid))
        result = cursor.fetchall()
        if len(result) > 0:
            ## this indicates that the `subpath` is a link
            ## get the target path
            target_user_uuid, target_path = get_link_target_path(conn, user_uuid, subpath)
            if target_user_uuid is None:
                return [None, None, None]
            path = target_path + "/" + "/".join(nodes[i:])
            if path.endswith("/"):
                path = path[:-1]
            ## embedded link is not allowed, so there is no infinite loop
            return [target_user_uuid, path, subpath]
    return [None, None, None]

def directory_or_file_exists_with_link(conn, user_uuid: str, path: str, type: str) -> bool:
    if path == "/":
        return False
    target_user_uuid, target_path, _ = convert_path_with_link(conn, user_uuid, path)
    if target_user_uuid == None:
        return False
    ## embedded link is not allowed, so there is no infinite loop
    return directory_or_file_exists(conn, target_user_uuid, target_path, type)

## insert a new file
def insert_file(conn, user_uuid: str, path: str, hash: str, size: int):
    sql = "INSERT INTO File (owner_uuid, type, hash, size, path) VALUES (%s, %s, %s, %s, %s)"
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (user_uuid, "TYPE_FILE", hash, size, path))
        conn.commit()
    except Exception as e:
        utils.log(utils.LEVEL_WARNING, "Fail to execute SQL statement in `insert_file()`: {}".format(e))
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
        return get_hash_and_size_with_link(conn, user_uuid, path)
    return result[0][0], result[0][1]

def get_hash_and_size_with_link(conn, user_uuid: str, path: str) -> tuple[str, int]:
    target_user_uuid, target_path, _ = convert_path_with_link(conn, user_uuid, path)
    if target_user_uuid is None:
        return (None, None)
    return get_hash_and_size(conn, target_user_uuid, target_path)

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
        utils.log(utils.LEVEL_WARNING, "Fail to execute SQL statement in `remove_file()`: {}".format(e))
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
        utils.log(utils.LEVEL_WARNING, "Fail to execute SQL statement in `remove_dir()`: {}".format(e))
        conn.rollback()
        return False
    cursor.close()
    return True

## get file infomation under specific path
def list_file(conn, user_uuid: str, path: str, link: bool = True) -> list:
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
    if len(file_infos) == 0 and link:
        return list_file_with_link(conn, user_uuid, path)
    else:
        return file_infos

def list_file_with_link(conn, user_uuid: str, path: str) -> list:
    if path == "/":
        return []
    target_user_uuid, target_path, subpath = convert_path_with_link(conn, user_uuid, path)
    files = list_file(conn, target_user_uuid, target_path, False)
    for file in files:
        file["path"] = utils.replace_prefix(file["path"], target_path, subpath)
    return files

def get_directory_size(conn, user_uuid: str, path: str) -> int:
    if not path.endswith("/"):
        path += "/"
    sql = "SELECT SUM(size) FROM File WHERE owner_uuid = %s AND path LIKE %s AND type = 'TYPE_FILE'"
    cursor = conn.cursor()
    cursor.execute(sql, (user_uuid, "{}%".format(path)))
    result = cursor.fetchall()
    if len(result) == 0:
        return 0
    return result[0][0]

def create_directory(conn, user_uuid: str, newdir: str, recursive: bool = False) -> tuple[bool, str]:
    ## end of recursion
    if directory_exists(conn, user_uuid, newdir) and recursive:
        return True, "OK"
    ## check if the name is used or not
    if directory_exists(conn, user_uuid, newdir) or file_exists(conn, user_uuid, newdir):
        return False, "File or directory is already exists."
    ## check if the parent path exists
    parent_path = str(os.path.dirname(newdir))
    if not directory_exists(conn, user_uuid, parent_path):
        if not recursive:
            return False, "Parent directory '{}' does not exists.".format(parent_path)
        else:
            result, message = create_directory(conn, user_uuid, parent_path, recursive)
            if not result:
                return result, message
    sql = "INSERT INTO File (owner_uuid, type, path) VALUES (%s, 'TYPE_DIR', %s)"
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (user_uuid, newdir))
        conn.commit()
    except Exception as e:
        message = "Fail to execute SQL statement in `create_directory()`: {}".format(e)
        utils.log(utils.LEVEL_WARNING, message)
        conn.rollback()
        return False, message
    cursor.close()
    return True, "OK"

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
        utils.log(utils.LEVEL_WARNING, "Fail to execute SQL statement in `update_remark()`: {}".format(e))
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
        utils.log(utils.LEVEL_WARNING, "Fail to execute SQL statement in `pin_or_unpin_file()`: {}".format(e))
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
        utils.log(utils.LEVEL_WARNING, "Fail to execute SQL statement in `create_tag()`: {}".format(e))
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
        utils.log(utils.LEVEL_WARNING, "Fail to execute SQL statement in `remove_tag()`: {}".format(e))
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
        utils.log(utils.LEVEL_WARNING, "Fail to execute SQL statement in `rename_file_or_directory()`: {}".format(e))
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
        utils.log(utils.LEVEL_WARNING, "Fail to execute SQL statement in `attach_tag_to_file()`: {}".format(e))
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
        utils.log(utils.LEVEL_WARNING, "Fail to execute SQL statement in `remove_tag_from_file()`: {}".format(e))
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
        utils.log(utils.LEVEL_WARNING, "Fail to execute SQL statement in `create_external_link()`: {}".format(e))
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
    ## remove expired links
    remove_expired_external_links(conn)
    sql = "SELECT user_uuid, file_path FROM ExternalLink WHERE share_key = %s"
    cursor = conn.cursor()
    cursor.execute(sql, (key,))
    result = cursor.fetchall()
    if len(result) == 0:
        return None
    else:
        return (result[0][0], result[0][1])

def get_all_external_links(conn, user_uuid: str) -> list:
    ## remove expired links
    remove_expired_external_links(conn)
    sql = "SELECT file_path, expire, share_key FROM ExternalLink WHERE user_uuid = %s"
    cursor = conn.cursor()
    cursor.execute(sql, (user_uuid,))
    result = cursor.fetchall()
    links = []
    for info in result:
        links.append({
            "path": info[0],
            "expire": info[1],
            "key": info[2]
        })
    return links

def remove_expired_external_links(conn):
    sql = "DELETE FROM ExternalLink WHERE expire < NOW()"
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        conn.commit()
    except Exception as e:
        utils.log(utils.LEVEL_WARNING, "Fail to execute SQL statement in `remove_expired_external_links()`: {}".format(e))
        conn.rollback()
        return False
    cursor.close()
    return True

def remove_external_link(conn, user_uuid: str, key: str):
    sql = "DELETE FROM ExternalLink WHERE user_uuid = %s AND share_key = %s"
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (user_uuid, key))
        conn.commit()
    except Exception as e:
        utils.log(utils.LEVEL_WARNING, "Fail to execute SQL statement in `remove_external_link()`: {}".format(e))
        conn.rollback()
        return False
    cursor.close()
    return True

## find all replicas
def find_replicas(conn, user_uuid: str) -> list:
    sql = "SELECT ARRAY_AGG(path), hash, size FROM File WHERE owner_uuid = %s AND type = 'TYPE_FILE' GROUP BY hash, size HAVING COUNT(*) > 1"
    cursor = conn.cursor()
    cursor.execute(sql, (user_uuid, ))
    result = cursor.fetchall()
    result_list = []
    for info in result:
        result_list.append({
            "paths": info[0],
            "hash":  info[1],
            "size":  info[2]
        })
    return result_list

## download a file from http
## save progress in global variable
## return file path when succeed
progress_data = {}
## progress_data = {
##     "task_id": [url, downloaded, total_size, stop]
## }
def download_file_http(conn, user_uuid: str, url: str, task_id: str, root: str) -> str:
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    downloaded = 0
    tmp = "/tmp/{}".format(task_id)
    filename = url.split("/")[-1]
    global progress_data
    progress_data[task_id] = [url, downloaded, total_size, False]
    with open(tmp, "wb") as f:
        for data in response.iter_content(chunk_size=1024):
            downloaded += len(data)
            f.write(data)
            progress_data[task_id][1] = downloaded
            if progress_data[task_id][3]:
                os.remove(tmp)
                progress_data.pop(task_id)
                break
    if progress_data[task_id][1] == progress_data[task_id][2]:
        ## move file to destination
        hash = utils.hash_file(tmp)
        size = os.path.getsize(tmp)
        ## create subdirectory if not exists
        if not os.path.exists("{}/{}".format(root, hash[0:2])):
            os.makedirs("{}/{}".format(root, hash[0:2]))
        shutil.move(tmp, "{}/{}/{}_{}".format(root, hash[0:2], hash, size))
        insert_file(conn, user_uuid, "/{}".format(filename), hash, size)
        progress_data.pop(task_id)
    return task_id

def stop_download(task_id: str):
    global progress_data
    ## if download finished, remove task_id in progress_data
    if progress_data[task_id][1] == progress_data[task_id][2]:
        progress_data.pop(task_id)
        return True
    ## if download not finished, set stop flag
    if task_id in progress_data:
        progress_data[task_id][3] = True
        return True
    else:
        return False

## check if a file is shared with a user
def check_share(conn, user_uuid: str, path: str, target_uuid: str) -> bool:
    sql = "SELECT share_uuid FROM File WHERE owner_uuid = %s AND path = %s"
    cursor = conn.cursor()
    cursor.execute(sql, (user_uuid, path))
    result = cursor.fetchall()
    if len(result) == 0:
        return None
    return target_uuid in result[0][0]

def create_share_request(conn, user_uuid: str, path: str, target_uuid: str):
    title = "Share Request"
    username = auth.get_username_by_uuid(conn, user_uuid)
    content = "User [{}] wants to share directory [{}] with you.".format(username, path.split("/")[-1])
    if notification.create_notification(conn, user_uuid, target_uuid, title, content, "TYPE_SHARE_REQUEST", path):
        return True
    else:
        return False

def share_directory(conn, owner_uuid: str, path: str, share_user_uuid: str):
    sql = "UPDATE File SET share_uuid = array_append(share_uuid, %s) WHERE owner_uuid = %s AND path = %s"
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (share_user_uuid, owner_uuid, path))
        conn.commit()
    except Exception as e:
        utils.log(utils.LEVEL_WARNING, "Fail to execute SQL statement in `share_directory()`: {}".format(e))
        conn.rollback()
        return False
    cursor.close()
    utils.log(utils.LEVEL_INFO, "User [{}] shared directory [{}] with user [{}]".format(owner_uuid, path, share_user_uuid))
    return True

def create_link(conn, owner_uuid: str, path: str, target_uuid: str, target_path: str):
    ## disallow link to link
    if check_shared(conn, target_uuid, target_path):
        return False
    sql_link = "INSERT INTO Link (owner_uuid, path, target_uuid, target_path) VALUES (%s, %s, %s, %s)"
    sql_file = "INSERT INTO File (owner_uuid, type, path) VALUES (%s, 'TYPE_LINK', %s)"
    cursor = conn.cursor()
    try:
        cursor.execute(sql_link, (owner_uuid, path, target_uuid, target_path))
        cursor.execute(sql_file, (owner_uuid, path))
        conn.commit()
    except Exception as e:
        utils.log(utils.LEVEL_WARNING, "Fail to execute SQL statement in `create_link()`: {}".format(e))
        conn.rollback()
        return False
    cursor.close()
    return True

## if `link_path` is a link, return the target path, otherwise return None
def get_link_target_path(conn, user_uuid: str, link_path: str):
    sql = "SELECT target_uuid, target_path FROM Link WHERE owner_uuid = %s AND path = %s"
    cursor = conn.cursor()
    cursor.execute(sql, (user_uuid, link_path))
    result = cursor.fetchall()
    if len(result) == 0:
        return None, None
    else:
        return result[0][0], result[0][1]

## check if a file or directory is shared with a user
def check_shared(conn, user_uuid: str, path: str) -> bool:
    target_user_uuid, _, _ = convert_path_with_link(conn, user_uuid, path)
    if target_user_uuid == None:
        return True
    else:
        return False

## check if a directory is shared with a user
## if so, return the target user uuid, otherwise return empty list
def get_shared_users(conn, user_uuid: str, path: str) -> str:
    sql = "SELECT share_uuid FROM File WHERE owner_uuid = %s AND path = %s"
    cursor = conn.cursor()
    cursor.execute(sql, (user_uuid, path))
    result = cursor.fetchall()
    if len(result) == 0:
        return []
    return result[0][0]

def update_link(conn, owner_uuid: str, path: str, new_path: str):
    sql = "UPDATE Link SET path = %s WHERE owner_uuid = %s AND path = %s"
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (new_path, owner_uuid, path))
        conn.commit()
    except Exception as e:
        utils.log(utils.LEVEL_WARNING, "Fail to execute SQL statement in `update_link()`: {}".format(e))
        conn.rollback()
        return False
    cursor.close()
    return True

def update_link_target(conn, owner_uuid: str, path: str, new_target_path):
    sql = "UPDATE Link SET target_path = %s WHERE owner_uuid = %s AND path = %s"
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (new_target_path, owner_uuid, path))
        conn.commit()
    except Exception as e:
        utils.log(utils.LEVEL_WARNING, "Fail to execute SQL statement in `update_link_target()`: {}".format(e))
        conn.rollback()
        return False
    cursor.close()
    return True

## save a file and register it in database
## `file_storage` is a FileStorage object, obtained from ``request.files['file']``
## `user_uuid` is the uuid of the user who owns the file
## `vpath` is the path to save the file, it should be a directory
## `storage_path` is the app configuration for the storage path
## `replica` is a boolean value, if True, check if the file is already exists
## if so, remove the file and return the path of the first replica
## if not, save the file and return the path of the new file
def save_and_register_file(conn, user_uuid: str, vpath: str, file_storage, storage_path: str, replica: bool) -> dict:
    result = {
        "result": "FAIL",
        "message": "File saved."
    }
    pname = str(uuid.uuid4())
    ppath = os.path.join(storage_path, pname)
    ## check if the path contains a link
    target_user_uuid, target_path, _ = convert_path_with_link(conn, user_uuid, vpath)
    if target_user_uuid and target_path:
        ## do contain a link
        vpath = target_path
        user_uuid = target_user_uuid
        ## actually, if the path contains a link, then the file should be saved for target user's file system
    ## check if path is available, i.e. is a folder in which no same file name
    if not directory_exists(conn, user_uuid, vpath):
        result["message"] = "Directory not exists."
        return result
    vpath = os.path.join(vpath, file_storage.filename)
    if file_exists(conn, user_uuid, vpath):
        result["message"] = "File already exists."
        return result
    if file_storage:
        file_storage.save(ppath)
        ## compute hash value
        hash = utils.hash_file(ppath)
        ## get file size
        size = os.path.getsize(ppath)
        ## check redundent if there is params 'replica=true'
        if replica:
            replicas = search_by_id(conn, user_uuid, hash, size)
            if len(replicas) > 0:
                replica_path = search_by_uuid(conn, user_uuid, replicas[0])
                ## remove temp file
                os.remove(ppath)
                result["message"] = "First replica [{}].".format(replica_path)
                return result
        ## create folder for file according to the first two chars of hash
        newfolder = os.path.join(storage_path, hash[0:2])
        if not os.path.exists(newfolder):
            os.makedirs(newfolder)
        ## move file into according folder and rename to [HASH]_[SIZE]
        newpath = os.path.join(newfolder, "{}_{}".format(hash, size))
        ## check if the file is already exists
        if not os.path.exists(newpath):
            shutil.move(ppath, newpath)
        else:
            if os.path.exists(ppath):
                os.remove(ppath)
        ## insert new file item into database
        insert_file(conn, user_uuid, vpath, hash, size)
        result["result"] = "OK"
        return result
    
def get_all_upload_filters(conn, user_uuid: str) -> list:
    sql = "SELECT uuid, filter, type, value, active FROM UploadFilter WHERE user_uuid = %s"
    cursor = conn.cursor()
    cursor.execute(sql, (user_uuid,))
    result = cursor.fetchall()
    filters = []
    for info in result:
        filters.append({
            "uuid": info[0],
            "filter": info[1],
            "type": info[2],
            "value": info[3],
            "active": info[4]
        })
    return filters

filter_list = ["file_name", "file_size", "extension"]
type_list = ["IS", "IS_NOT", "CONTAINS", "NOT_CONTAINS", "GREATER", "LESS"]

def add_upload_filter(conn, user_uuid: str, filter: str, type: str, value: str):
    if filter not in filter_list:
        utils.log(utils.LEVEL_WARNING, "Invalid filter type: {}".format(type))
        return False
    if type not in type_list:
        utils.log(utils.LEVEL_WARNING, "Invalid filter type: {}".format(type))
        return False
    sql = "INSERT INTO UploadFilter (user_uuid, filter, type, value) VALUES (%s, %s, %s, %s)"
    cursor = conn.cursor()
    ## create a new filter
    try:
        cursor.execute(sql, (user_uuid, filter, type, value))
        conn.commit()
    except Exception as e:
        utils.log(utils.LEVEL_WARNING, "Fail to execute SQL statement in `add_upload_filter()`: {}".format(e))
        conn.rollback()
        return False
    cursor.close()
    return True

def update_upload_filter(conn, user_uuid: str, filter_uuid: str, filter: str, type: str, value: str, active: bool):
    sql = """
        UPDATE UploadFilter
        SET
            filter = COALESCE(%s, filter),
            type   = COALESCE(%s, type),
            value  = COALESCE(%s, value),
            active = COALESCE(%s, active)
        WHERE uuid = %s AND user_uuid = %s;
    """
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (filter, type, value, active, filter_uuid, user_uuid))
        conn.commit()
    except Exception as e:
        utils.log(utils.LEVEL_WARNING, "Fail to execute SQL statement in `update_upload_filter()`: {}".format(e))
        conn.rollback()
        return False
    cursor.close()
    return True

def remove_upload_filter(conn, user_uuid: str, filter_uuid: str):
    sql = "DELETE FROM UploadFilter WHERE uuid = %s AND user_uuid = %s"
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (filter_uuid, user_uuid))
        conn.commit()
    except Exception as e:
        utils.log(utils.LEVEL_WARNING, "Fail to execute SQL statement in `remove_upload_filter()`: {}".format(e))
        conn.rollback()
        return False
    cursor.close()
    return True