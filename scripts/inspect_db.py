import sqlite3
import pprint

conn = sqlite3.connect('db.sqlite3')
rows = conn.execute("PRAGMA table_info('products_product')").fetchall()
pprint.pprint(rows)
conn.close()
