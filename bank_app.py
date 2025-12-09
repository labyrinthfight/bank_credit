from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import psycopg2
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Настройки подключения к PostgreSQL
DB_CONFIG = {
    'host': 'localhost',
    'database': 'postgres',  # или 'bank_db' если создашь отдельную базу
    'user': 'postgres',
    'password': '123456',
    'port': '5432'
}

def get_db_connection():
    """Создает подключение к базе данных"""
    conn = psycopg2.connect(**DB_CONFIG)
    return conn

# Главная страница - панель управления
@app.route('/')
def home():
    return render_template('bank_index.html')

# API для клиентов
@app.route('/api/clients', methods=['GET'])
def get_clients():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM clients ORDER BY id')
    clients = cur.fetchall()
    
    result = []
    for client in clients:
        result.append({
            'id': client[0],
            'name': client[1],
            'ownership_type': client[2],
            'address': client[3],
            'phone': client[4],
            'contact_person': client[5],
            'created_at': client[6].isoformat() if client[6] else None
        })
    
    cur.close()
    conn.close()
    return jsonify(result)

@app.route('/api/clients', methods=['POST'])
def add_client():
    data = request.json
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute(
        'INSERT INTO clients (name, ownership_type, address, phone, contact_person) VALUES (%s, %s, %s, %s, %s) RETURNING id',
        (data['name'], data['ownership_type'], data['address'], data['phone'], data['contact_person'])
    )
    
    new_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    
    return jsonify({'id': new_id, 'message': 'Клиент добавлен'})

# API для типов кредитов
@app.route('/api/loan_types', methods=['GET'])
def get_loan_types():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM loan_types ORDER BY id')
    types = cur.fetchall()
    
    result = []
    for type_item in types:
        result.append({
            'id': type_item[0],
            'name': type_item[1],
            'conditions': type_item[2],
            'interest_rate': float(type_item[3]) if type_item[3] else None,
            'term_months': type_item[4]
        })
    
    cur.close()
    conn.close()
    return jsonify(result)

# API для кредитов
@app.route('/api/loans', methods=['GET'])
def get_loans():
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        SELECT l.id, c.name as client_name, lt.name as loan_type_name, 
               l.amount, l.issue_date, l.return_date, l.status
        FROM loans l
        JOIN clients c ON l.client_id = c.id
        JOIN loan_types lt ON l.loan_type_id = lt.id
        ORDER BY l.issue_date DESC
    ''')
    
    loans = cur.fetchall()
    
    result = []
    for loan in loans:
        result.append({
            'id': loan[0],
            'client_name': loan[1],
            'loan_type_name': loan[2],
            'amount': float(loan[3]) if loan[3] else None,
            'issue_date': loan[4].isoformat() if loan[4] else None,
            'return_date': loan[5].isoformat() if loan[5] else None,
            'status': loan[6]
        })
    
    cur.close()
    conn.close()
    return jsonify(result)

@app.route('/api/loans', methods=['POST'])
def add_loan():
    data = request.json
    
    # Проверяем обязательные поля
    if not all(k in data for k in ['client_id', 'loan_type_id', 'amount', 'issue_date']):
        return jsonify({'error': 'Не все обязательные поля заполнены'}), 400
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute(
            '''INSERT INTO loans (client_id, loan_type_id, amount, issue_date, return_date, status) 
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id''',
            (data['client_id'], data['loan_type_id'], data['amount'], 
             data['issue_date'], data.get('return_date'), data.get('status', 'в обработке'))
        )
        
        new_id = cur.fetchone()[0]
        conn.commit()
        
        # Генерируем SMS сообщение (в реальной системе здесь был бы вызов SMS сервиса)
        cur.execute('SELECT name FROM clients WHERE id = %s', (data['client_id'],))
        client_name = cur.fetchone()[0]
        
        sms_message = f"Уважаемый клиент, {client_name}. Ваш кредит на сумму {data['amount']} руб. был одобрен."
        
        cur.close()
        conn.close()
        
        return jsonify({
            'id': new_id, 
            'message': 'Кредит добавлен',
            'sms': sms_message
        })
        
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({'error': str(e)}), 500

# Статистика
@app.route('/api/stats', methods=['GET'])
def get_stats():
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('SELECT COUNT(*) FROM clients')
    clients_count = cur.fetchone()[0]
    
    cur.execute('SELECT COUNT(*) FROM loans')
    loans_count = cur.fetchone()[0]
    
    cur.execute('SELECT SUM(amount) FROM loans WHERE status = %s', ('активен',))
    total_active_loans = cur.fetchone()[0] or 0
    
    cur.close()
    conn.close()
    
    return jsonify({
        'clients_count': clients_count,
        'loans_count': loans_count,
        'total_active_loans': float(total_active_loans)
    })

if __name__ == '__main__':
    app.run(debug=True, port=5001)  # Используем другой порт