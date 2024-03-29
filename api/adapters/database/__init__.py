import os
import sys
import datetime

import duckdb
from drivers.creds import generate_password_hash
from exceptions import AccountLockedError
from exceptions import InvalidAuthenticationError
from exceptions import UserDoesntExistError

sys.path.insert(1, os.path.join(sys.path[0], "../../.."))


DATABASE: str = "hakatomi.duckdb"


def _get_user(username: str) -> dict:

    sql = f"""
SELECT *
  FROM user_table 
 WHERE username LIKE '{username}';
"""
    conn = duckdb.connect(database=DATABASE)
    cursor = conn.cursor()
    cursor.execute(sql)

    match = cursor.fetchone()
    if match is None:
        return None

    # Fetch column names
    columns = [description[0] for description in cursor.description]

    # Convert tuple to dictionary using column names
    user_dict = dict(zip(columns, match))

    return user_dict


def _update_user(user):

    def val(v):
        if isinstance(v, str):
            return f"'{v}'"
        if isinstance(v, datetime.datetime):
            return f"TIMESTAMP '{v.isoformat()}'"
        return str(v)

    # Create the SET part of the SQL statement, excluding 'username'
    set_part = ", ".join(
        [
            f"{key} = {val(value)}"
            for key, value in user.items()
            if key not in ("username", "id", "password") and value is not None
        ]
    )

    sql = f"""
UPDATE user_table 
   SET {set_part}
 WHERE username LIKE '{user['username']}';
"""

    conn = duckdb.connect(database=DATABASE)
    cursor = conn.cursor()
    cursor.execute(sql)
    cursor.commit()


def authenticate_user(username: str, password: str) -> bool:
    user = _get_user(username)
    if user is None:
        raise UserDoesntExistError(username)

    if user["failed_sign_in_attempts"] >= 3:
        raise AccountLockedError(username)

    # sign-in test
    password_hash = generate_password_hash(password, user["salt"])
    if password_hash != user["password"]:
        user["failed_sign_in_attempts"] += 1
        user["last_failed_sign_in"] = datetime.datetime.now()
        _update_user(user)
        raise InvalidAuthenticationError(username)

    user["failed_sign_in_attempts"] = 0
    user["last_sign_in"] = datetime.datetime.now()
    _update_user(user)


def reset_user(username: str, password: str) -> bool:
    user = _get_user(username)
    if user is None:
        raise UserDoesntExistError(username)

    # sign-in test
    password_hash = generate_password_hash(password, user["salt"])
    user["password"] = password_hash
    user["failed_sign_in_attempts"] = 0
    _update_user(user)

    return True


def get_signin_stats():
    sql = f"""
SELECT COUNT(*) AS count, failed_sign_in_attempts AS attempts
  FROM user_table 
 GROUP BY failed_sign_in_attempts
"""
    conn = duckdb.connect(database="hakatomi.duckdb")
    cursor = conn.cursor()
    cursor.execute(sql)

    match = cursor.arrow()
    return match.to_pydict()

def get_signin_fails_last_5_mins():
    sql = f"""
SELECT COUNT(*) AS count
  FROM user_table 
 WHERE last_failed_sign_in + INTERVAL '5 MINUTES' > CAST(CURRENT_TIMESTAMP AS TIMESTAMP)
"""
    conn = duckdb.connect(database="hakatomi.duckdb")
    cursor = conn.cursor()
    cursor.execute(sql)

    match = cursor.arrow()
    return match.to_pydict()
