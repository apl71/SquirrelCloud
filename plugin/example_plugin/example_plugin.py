from plugin.plugin import plugin_base
from flask import send_from_directory, jsonify, request

## import function from squirrelcloud app
import db.auth as auth

class example_plugin(plugin_base):
    def __init__(self):
        self.plugin_info = {
            "name": "example_plugin",
            "author": "apl-71",
            "description": "An example plugin. Providing a gallery app for user.",
            "version": "0.1"
        }
        super().__init__()

    def register(self, app):
        self.routes(app)
        result = super().register(app)
        return result

    ## now plugin can access any thing from app
    ## should we restrict it?
    def routes(self, app):
        ## create you own static file route
        @self.bp.route("/<path:filename>", methods=["GET"])
        def example_view(filename):
            return send_from_directory("plugin/{}/static".format(self.plugin_info["name"]), filename)

        ## create any route you want
        @self.bp.route("/info", methods=["GET"])
        def example_info():
            return jsonify(self.plugin_info)
        
        ## get next `n` image from `s`, start from 0
        ## if n is not provided, then return next 5 images
        ## if s is not provided, then start from 0
        @self.bp.route("/get_images", methods=["GET"])
        def get_images():
            n = request.args.get("num", 5)
            s = request.args.get("start", 0)
            ## check session
            result = {
                "result": "FAIL"
            }
            ## check session
            session = request.cookies.get("session")
            user_uuid = auth.check_session(app.conn, session, app.config["SESSION_LIFESPAN"])
            if not user_uuid:
                result["message"] = "Your session is not valid."
                return jsonify(result)
            ## get url of images from database
            sql = "SELECT path FROM File WHERE owner_uuid = %s AND path ~ '\\.(jpg|jpeg|png|gif|bmp|webp)$' ORDER BY create_at DESC LIMIT %s OFFSET %s"
            cursor = app.conn.cursor()
            cursor.execute(sql, (user_uuid, n, s))
            data = cursor.fetchall()
            cursor.close()
            result["result"] = "OK"
            result["images"] = [row[0] for row in data]
            return jsonify(result)