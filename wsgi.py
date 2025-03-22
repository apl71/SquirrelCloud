## python wsgi.py
from app import create_app

app = create_app()

@app.after_request
def after_request(response):
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    return response

if __name__ == "__main__":
    ssl_context = ("cert/cert.pem", "cert/key.pem")
    debug = False
    ssl = True
    if app.config["DEBUG"] == "ON":
        debug = True
    if app.config["SSL"] == "OFF":
        ssl = False
    port = int(app.config["PORT"])
    if ssl:
        app.run(debug=debug, host="0.0.0.0", port=port, ssl_context=ssl_context)
    else:
        app.run(debug=debug, host="0.0.0.0", port=port)