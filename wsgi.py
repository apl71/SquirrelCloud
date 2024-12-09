## python wsgi.py
from app import create_app

app = create_app()

if __name__ == "__main__":
    ssl_context = ("cert/cert.pem", "cert/key.pem")
    app.run(debug=True, host="0.0.0.0", port=5000, ssl_context=ssl_context)