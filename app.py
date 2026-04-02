from flask import Flask, g, current_app, has_app_context
import tomllib
import db.init
import psycopg2
import utils
import os, importlib

def create_connection(user, password, host, port, database):
    dsn = "postgresql://{}:{}@{}:{}/{}".format(user, password, host, port, database)
    try:
        conn = psycopg2.connect(dsn)
        if has_app_context():
            utils.log(utils.LEVEL_INFO, "Connect to database successfully.")
    except Exception as e:
        print("Fail to connect to database.")
        print("Reason: {}".format(e))
        if has_app_context():
            utils.log(utils.LEVEL_CRITICAL, "Fail to connect to database.")
        return None
    return conn

plugin_list = []


def get_db():
    """Get a per-request database connection stored in Flask `g`."""
    if "db_conn" not in g:
        g.db_conn = create_connection(
            current_app.config["DB_USER"],
            current_app.config["DB_PWD"],
            current_app.config["DB_HOST"],
            current_app.config["DB_PORT"],
            current_app.config["DB_NAME"],
        )
    return g.db_conn



def close_db(e=None):
    """Close the request-scoped database connection if it exists."""
    conn = g.pop("db_conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception as exc:
            utils.log(utils.LEVEL_WARNING, "Fail to close database connection: {}".format(exc))

def load_plugin(app):
    plugin_dir = "./plugin"
    loaded_num = 0
    for plugin_name in os.listdir(plugin_dir):
        if not plugin_name.endswith("_plugin"):
            continue
        plugin_path = os.path.join(plugin_dir, plugin_name)
        ## install requirements of plugin
        result, message = utils.install_requirements("{}/requirements.txt".format(plugin_path))
        if not result:
            print("Fail to install requirements of plugin: {}".format(plugin_name))
            print("Reason: {}".format(message))
            with app.app_context():
                utils.log(utils.LEVEL_WARNING, "Fail to install requirements of plugin: {}".format(plugin_name))
            continue
        if os.path.isdir(plugin_path):
            plugin_module = importlib.import_module("plugin.{}.{}".format(plugin_name, plugin_name))
            plugin_class = getattr(plugin_module, plugin_name)
            plugin = plugin_class()
            with app.app_context():
                result = plugin.register(app)
                if result["result"] == "OK":
                    plugin_list.append(plugin.info())
            if result["result"] == "OK":
                print("Register plugin: {}".format(plugin_name))
                loaded_num += 1
                with app.app_context():
                    utils.log(utils.LEVEL_INFO, "Register plugin: {}".format(plugin_name))
            else:
                print("Fail to register plugin: {}".format(plugin_name))
                print("Reason: {}".format(result["message"]))
                with app.app_context():
                    utils.log(utils.LEVEL_WARNING, "Fail to register plugin: {}".format(plugin_name))
    print("Load {} plugin(s).".format(loaded_num))
    with app.app_context():
        utils.log(utils.LEVEL_INFO, "Load {} plugin(s).".format(loaded_num))
    app.plugin_list = plugin_list
            

def create_app():
    app = Flask(__name__, static_url_path='', static_folder='static')
    if not app.config.from_file("app.conf", load=tomllib.load, text=False):
        print("Fail to read configuration file.")
        utils.log(utils.LEVEL_CRITICAL, "Fail to read configuration file.")
        return None

    ## initialize database schema
    conn = create_connection(
        app.config["DB_USER"],
        app.config["DB_PWD"],
        app.config["DB_HOST"],
        app.config["DB_PORT"],
        app.config["DB_NAME"],
    )
    if conn is None:
        return None
    cursor = conn.cursor()
    cursor.execute(open("db/init.sql").read())
    conn.commit()
    cursor.close()
    conn.close()

    ## register request-scoped database lifecycle
    app.teardown_appcontext(close_db)

    ## setting version
    app.config["VERSION"] = "0.9.0"
    with app.app_context():
        utils.log(utils.LEVEL_INFO, "Starting Squirrel Cloud Version: {}".format(app.config["VERSION"]))

    ## register api for app
    from route.auth_api import auth_api
    app.register_blueprint(auth_api)

    from route.file_api import file_api
    app.register_blueprint(file_api)

    from route.system_api import system_api
    app.register_blueprint(system_api)

    from route.function_api import function_api
    app.register_blueprint(function_api)

    with app.app_context():
        utils.log(utils.LEVEL_INFO, "Register APIs successfully.")

    load_plugin(app)

    app.config["MAX_CONTENT_LENGTH"] = None

    ## expose db accessor for plugins and other modules
    app.get_db = get_db

    return app
