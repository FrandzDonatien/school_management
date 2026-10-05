from app.database.connection import execute, query


def find(username, hashed_password):
    return query("SELECT 1 FROM users WHERE username=? AND password=?", (username, hashed_password))


def count():
    return query("SELECT COUNT(*) FROM users")[0][0]


def create(username, hashed_password):
    return execute("INSERT INTO users(username,password) VALUES(?,?)", (username, hashed_password))
