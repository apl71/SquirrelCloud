import hashlib
import os
from datetime import datetime
from flask import current_app
import requests, re
import subprocess, sys

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

def replace_prefix(text, prefix, new_prefix):
    if text.startswith(prefix):
        return new_prefix + text[len(prefix):]
    else:
        return text

LEVEL_DEBUG = 0
LEVEL_INFO = 1
LEVEL_WARNING = 2
LEVEL_CRITICAL = 3

def log_level_to_str(level: int) -> str:
    if level == LEVEL_DEBUG:
        return " DEBUG  "
    elif level == LEVEL_INFO:
        return "  INFO  "
    elif level == LEVEL_WARNING:
        return "WARNING "
    elif level == LEVEL_CRITICAL:
        return "CRITICAL"
    else:
        return "UNKNOWN"

def log(level: int, data: str):
    ## get log level
    sys_log_level = current_app.config["LOG_LEVEL"]
    if level < 1 and sys_log_level == "INFO":
        return
    elif level < 2 and sys_log_level == "WARNING":
        return
    elif level < 3 and sys_log_level == "CRITICAL":
        return
    
    now = datetime.now()
    log_file_time = now.strftime("%Y-%m-%d")
    log_time = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    log_file = "{}/LOG_{}.log".format(current_app.config["LOG_PATH"], log_file_time)

    try:
        # 尝试打开文件
        with open(log_file, 'a') as f:
            f.write("[{}][{}] {}\n".format(log_time, log_level_to_str(level), data))
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

def install_requirements(requirements_file: str) -> list[bool, str]:
    if not os.path.isfile(requirements_file):
        return False, "Requirements file not found."
    ## install requirements
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", requirements_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            return True, None
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)
