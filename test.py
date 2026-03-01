import sqlite3

db_local = "DB.db"

connect = sqlite3.connect(db_local)
cursor = connect.cursor()
cursor.execute("insert into users (username,password) values ('admin','admin')")

connect.commit()
connect.close()