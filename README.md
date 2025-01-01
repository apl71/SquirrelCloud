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

`docker build -t squirrelcloud:latest .`

`cd ..`

### Preparing for running docker

`
mkdir file
mkdir logs
mkdir backup
mkdir src
mkdir db
`

Mount your disk to `file` directory and your backup disk to `backup`.

`cp SquirrelCloud/docker-compose.yaml .`

Modify the docker compose file. Remember to change `POSTGRES_PASSWORD`. Modify port if you need.

Copy sources to docker volume.

`cp -r SquirrelCloud/* src`

### Running docker

`docker compose up -d`

## Squirrel Cloud Syncer

## External Resources