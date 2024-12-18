import hashlib
import os
from datetime import datetime
from flask import current_app
import requests, re

def hash_file(path: str) -> str:
    f = open(path, "rb")
    digest = hashlib.file_digest(f, "sha3-512")
    return digest.hexdigest()

def get_directory_size(path):
    total_size = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size

def log(data: str):
    now = datetime.now()
    log_file_time = now.strftime("%Y-%m-%d")
    log_time = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    log_file = "{}/LOG_{}.log".format(current_app.config["LOG_PATH"], log_file_time)

    try:
        # 尝试打开文件
        with open(log_file, 'a') as f:
            f.write("[{}] {}\n".format(log_time, data))
    except FileNotFoundError:
        print("Warning: Cannot open log file: {} does not exist.".format(log_file))
    except PermissionError:
        print("Warning: Cannot open log file: {} permission denied.".format(log_file))
    except Exception as e:
        print("Warning: Cannot open log file: {} unknown error.".format(log_file))

def kill_program():
    ## use docker to restart programe
    ## so --restart=always is necessary
    if current_app.config["DEBUG"] == "ON":
        os.system("pkill python")
    else:
        os.system("pkill gunicorn")

def check_update() -> str:
    ## get latest version
    url = "{}/latest.html".format(current_app.config["UPDATE_SERVER"])
    latest = requests.get(url).text.strip()
    if bool(re.match(r'^.+\..+\..+$', latest)):
        return latest
    else:
        return None