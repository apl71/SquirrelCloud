from flask import Flask
import tomllib
import db.init, db.file, db.auth

def create_connection(user, password, host, port, database):
    dsn = "postgresql://{}:{}@{}:{}/{}".format(user, password, host, port, database)
    conn = db.init.initialize_database(dsn)
    return conn

conn = None

def create_app():
    app = Flask(__name__, static_url_path='', static_folder='static')
    if not app.config.from_file("app.conf", load=tomllib.load, text=False):
        print("Fail to read configuration file.")

    ## initialize database connection
    global conn
    conn = create_connection(
        app.config["DB_USER"],
        app.config["DB_PWD"],
        app.config["DB_HOST"],
        app.config["DB_PORT"],
        app.config["DB_NAME"]
    )

    ## setting version
    app.config["VERSION"] = "0.6.1"

    ## register api for app
    from route.auth_api import auth_api
    app.register_blueprint(auth_api)

    from route.file_api import file_api
    app.register_blueprint(file_api)

    from route.system_api import system_api
    app.register_blueprint(system_api)

    return app

