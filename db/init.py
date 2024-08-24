import psycopg2

## initialize database, return connection
def initialize_database(dsn: str):
    conn = psycopg2.connect(dsn)
    cursor = conn.cursor()
    cursor.execute(open("db/init.sql", "r").read())
    conn.commit()
    cursor.close()
    return conn