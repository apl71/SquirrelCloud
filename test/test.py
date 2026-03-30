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
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(open("test/drop.sql").read())
    conn.commit()
    cursor.close()
    conn.close()

    app = create_app()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(open("test/test_data.sql").read())
    conn.commit()
    cursor.close()
    conn.close()

    yield app

@pytest.fixture
def client(app):
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        with app.test_client() as client:
            yield client