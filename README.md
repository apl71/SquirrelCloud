# Squirrel Cloud

## Introduction

## Installation

### Docker(Recommanded)

Before installing, make sure you have docker and docker compose available.

### 1. Cloning

`git clone https://github.com/apl71/SquirrelCloud`

`cd SquirrelCloud`

### 2. Building image

Modify `app.conf` to make correct configuration.
For docker installation, set `DB_HOST="db"`.
Sample configuration file:
```
DB_HOST = "db"
DB_PORT = "5432"
DB_NAME = "squirrelcloud"
DB_USER = "squirrelcloud"
DB_PWD = "{PASSWORD}"
SESSION_LIFESPAN = 1000
STORAGE_PATH = "/file"
LOG_PATH = "/logs"
HOST = "{HOST_NAME}"
IMPORT_PATH = "/import"
CODE_PATH = "/app"
UPDATE_SERVER = "https://update.squirrelcloud.net"
PLUGIN_SERVER = "https://plugin.squirrelcloud.net"
DEBUG = "OFF"
SSL = "OFF"
PORT = "5000"
```

`docker build -t squirrelcloud:latest .`

`cd ..`

### Preparing for running docker

```
mkdir file
mkdir logs
mkdir backup
mkdir src
mkdir db
```

Mount your disk to `file` directory and your backup disk to `backup`.

`cp SquirrelCloud/docker-compose.yaml .`

Modify the docker compose file. Remember to change `POSTGRES_PASSWORD`. Modify port if you need.

Copy sources to docker volume.

`cp -r SquirrelCloud/* src`

### Running docker

`docker compose up -d`

## Squirrel Cloud Syncer

## External Resources