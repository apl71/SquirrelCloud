## run pytest from the root directory

import pytest, sys, os

# 将父目录路径添加到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
import psycopg2
import warnings

def get_connection():
    dsn = "postgresql://squirrelcloud:squirrelcloud@localhost:5432/squirrelcloud"
    conn = psycopg2.connect(dsn)
    return conn

@pytest.fixture(scope="session")
def app():
    ## drop all table in database and recreate for testing
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(open("testing/drop.sql").read())
    conn.commit()
    cursor.close()
    conn.close()

    ## start app
    app = create_app()
    return app

@pytest.fixture(scope="session")
def client(app):
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', category=DeprecationWarning)
        return app.test_client()

