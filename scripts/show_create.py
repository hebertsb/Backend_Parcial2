import sqlite3
conn=sqlite3.connect('db.sqlite3')
cur=conn.cursor()
cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='products_product'")
row=cur.fetchone()
print(row[0])
conn.close()
