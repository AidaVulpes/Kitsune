from flask import g, current_app
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from os import getenv
import config

pool = None

def init():
    global pool
    try:
        pool = psycopg2.pool.ThreadedConnectionPool(1, 2000,
            host = config.database_host,
            dbname = config.database_dbname,
            user = config.database_user,
            password = config.database_password,
            port = 5432,
            cursor_factory = RealDictCursor
        )
    except Exception as e:
        print(f'Failed to connect to the database: {e}')
    return pool

def get_pool():
    global pool
    return pool

def get_cursor():
    if 'cursor' not in g:
        g.connection = get_conn()
        g.cursor = g.connection.cursor()
    return g.cursor

def get_raw_conn():
    return pool.getconn()

def get_conn():
    if 'connection' not in g:
        g.connection = pool.getconn()
    return g.connection

def return_conn(conn):
    if conn is not None:
        pool.putconn(conn)
