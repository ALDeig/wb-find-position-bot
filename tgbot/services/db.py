import sqlite3


conn = sqlite3.connect("db/users.db", check_same_thread=False)
cursor = conn.cursor()


def insert(table: str, column_values: dict):
    columns = ', '.join(column_values.keys())
    values = [tuple(column_values.values())]
    placeholders = ", ".join("?" * len(column_values.keys()))
    cursor.executemany(
        f"INSERT INTO {table} "
        f"({columns}) "
        f"VALUES ({placeholders})",
        values)
    conn.commit()


def fetchall(columns: list[str], table: str) -> list[dict]:
    columns_joined = ", ".join(columns)
    cursor.execute(f"SELECT {columns_joined} FROM {table}")
    rows = cursor.fetchall()
    result = []
    for row in rows:
        dict_row = {}
        for index, column in enumerate(columns):
            dict_row[column] = row[index]
        result.append(dict_row)
    return result


def fetchall_by_filter(table: str, columns: str, filters: dict):
    cols = []
    for key in filters.keys():
        cols.append(f'{key}=?')
    value = ' AND '.join(cols)
    request = f'SELECT {columns} FROM {table} WHERE {value}'
    cursor.execute(request, tuple(filters.values()))
    rows = cursor.fetchall()
    if not rows:
        return
    result = []
    for row in rows:
        dict_row = {}
        for index, col in enumerate(columns.split(',')):
            dict_row[col.strip()] = row[index]
        result.append(dict_row)
    return result


def fetchone(table: str, columns: str, filters: dict) -> dict | None:
    cols = []
    for key in filters.keys():
        cols.append(f'{key}=?')
    value = ' AND '.join(cols)
    request = f'SELECT {columns} FROM {table} WHERE {value}'
    cursor.execute(request, tuple(filters.values()))
    result = cursor.fetchone()
    if not result:
        return
    result_dict = {}
    for index, col in enumerate(columns.split(',')):
        result_dict[col.strip()] = result[index]
    return result_dict


def insert_user(user_id: str):
    cursor.execute(f"SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    if rows:
        return
    cursor.execute(f"INSERT INTO users (user_id) VALUES (?)", (user_id, ))
    conn.commit()


def delete(table: str, column: str, value: str):
    cursor.execute(f"DELETE FROM {table} WHERE {column} = ?", (value,))
    conn.commit()


def delete_subscribe(subscribe_id: str):
    cursor.execute(f"DELETE FROM subscribe WHERE subscribe_id = ?", (subscribe_id, ))
    conn.commit()


def update(table: str, new_data: dict, filters: dict):
    cols = []
    for key in new_data.keys():
        cols.append(f'{key}=?')
    new_data_str = ', '.join(cols)
    cols = []
    for key in filters.keys():
        cols.append(f'{key}=?')
    filters_str = ' AND '.join(cols)
    values = tuple(new_data.values()) + tuple(filters.values())
    cursor.execute(f'UPDATE {table} SET {new_data_str} WHERE {filters_str}', values)
    conn.commit()


def delete_tmp_subscribes():
    cursor.execute("DELETE FROM tmp_subscribe")
    conn.commit()


def _init_db():
    """Инициализирует БД"""
    with open("db/createdb.sql", "r") as f:
        sql = f.read()
    cursor.executescript(sql)
    conn.commit()


def check_db_exists():
    """Проверяет, инициализирована ли БД, если нет — инициализирует"""
    cursor.execute("SELECT name FROM sqlite_master "
                   "WHERE type='table' AND name='users'")
    table_exists = cursor.fetchall()
    if table_exists:
        return
    _init_db()


check_db_exists()

