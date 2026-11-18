import sqlite3

connection = sqlite3.connect("gwcdbbot.db")

with open("gwcdbbot.sql", "r") as file:
    sql_script = file.read()

connection.executescript(sql_script)

connection.close()

print("Database created successfully.")