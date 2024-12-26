from flask import Blueprint

class plugin_base:

    plugin_info = {
        "name": "",
        "author": "",
        "description": "",
        "version": "",
    }

    def __init__(self):
        self.plugin_info["root"] = "/plugin/" + self.plugin_info["name"].rsplit("_", 1)[0]
        self.bp = Blueprint(self.plugin_info["name"], __name__, url_prefix=self.plugin_info["root"]) ## is there an injection risk here?

    def register(self, app):
        result = {
            "result": "OK",
            "message": "Plugin registered successfully."
        }
        if self.plugin_info["name"] == "":
            result["result"] = "FAIL"
            result["message"] = "Plugin name is not set."
            return result
        if self.plugin_info["author"] == "":
            result["result"] = "FAIL"
            result["message"] = "Plugin author is not set."
            return result
        if self.plugin_info["description"] == "":
            result["result"] = "FAIL"
            result["message"] = "Plugin description is not set."
            return result
        if self.plugin_info["version"] == "":
            result["result"] = "FAIL"
            result["message"] = "Plugin version is not set."
            return result
        app.register_blueprint(self.bp)
        return result

    def info(self):
        return self.plugin_info