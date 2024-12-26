from flask import Flask
import tomllib
import db.init, db.file, db.auth
import utils
import os, importlib

def create_connection(user, password, host, port, database):
    dsn = "postgresql://{}:{}@{}:{}/{}".format(user, password, host, port, database)
    conn = db.init.initialize_database(dsn)
    return conn

conn = None

plugin_list = []

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
            continue
        if os.path.isdir(plugin_path):
            plugin_module = importlib.import_module("plugin.{}.{}".format(plugin_name, plugin_name))
            plugin_class = getattr(plugin_module, plugin_name)
            plugin = plugin_class()
            result = plugin.register(app)
            if result["result"] == "OK":
                plugin_list.append(plugin.info())
                print("Register plugin: {}".format(plugin_name))
                loaded_num += 1
            else:
                print("Fail to register plugin: {}".format(plugin_name))
                print("Reason: {}".format(result["message"]))
    print("Load {} plugin(s).".format(loaded_num))
    app.plugin_list = plugin_list
            

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
    ## pass connection to app, for plugin to use
    app.conn = conn

    ## setting version
    app.config["VERSION"] = "0.8.0"

    ## register api for app
    from route.auth_api import auth_api
    app.register_blueprint(auth_api)

    from route.file_api import file_api
    app.register_blueprint(file_api)

    from route.system_api import system_api
    app.register_blueprint(system_api)

    load_plugin(app)

    return app

