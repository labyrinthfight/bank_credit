import psycopg2

DB_CONFIG = {
    'host': 'localhost',
    'database': 'postgres',
    'user': 'postgres',
    'password': '123456',
    'port': '5432'
}

try:
    conn = psycopg2.connect(**DB_CONFIG)
    print("✅ Подключение успешно!")
    
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()
    print(f"Версия PostgreSQL: {version[0]}")
    
    conn.close()
except Exception as e:
    print(f"❌ Ошибка: {e}")