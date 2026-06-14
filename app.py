import sqlite3
from flask import Flask, render_template, request, redirect, session
import os
from datetime import datetime # 📅 مكتبة التعامل مع الوقت والتاريخ لالتقاط لحظة الحجز

app = Flask(__name__)
app.secret_key = "minde_secret_key_123" 

DB_NAME = "salon.db"
ADMIN_PASSWORD = "123" 

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # أنشأنا الجدول وأضفنا عمود created_at لتسجيل وقت الحجز تلقائياً إذا لم يكن موجوداً
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            client_phone TEXT NOT NULL,
            service_id INTEGER NOT NULL,
            booking_date TEXT NOT NULL,
            booking_time TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP 
        )
    ''')
    
    # ⚠️ حركة ذكية: إذا كان الجدول قديم وموجود مسبقاً، نضيف العمود الجديد له لكي لا تضيع الحجوزات السابقة
    try:
        cursor.execute("ALTER TABLE bookings ADD COLUMN created_at TEXT")
    except sqlite3.OperationalError:
        pass # العمود موجود بالفعل، لا داعي لفعل شيء
        
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/book', methods=['POST'])
def book():
    name = request.form['name']
    phone = request.form['phone']
    service_id = request.form['service_id']
    date = request.form['date']
    time = request.form['time']
    
    # ⏱️ التقاط الوقت والتاريخ الحالي لحظة ضغط الزر بتنسيق أنيق (سنة-شهر-يوم ساعة:دقيقة)
    current_now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM bookings WHERE client_name = ? AND booking_date = ? AND booking_time = ?', (name, date, time))
    if cursor.fetchone():
        conn.close()
        return "<h1>⚠️ عذرًا، هذا الحجز مسجل بالفعل مسبقاً!</h1><a href='/'>العودة ومحاولة وقت آخر</a>"
    
    # حفظ الوقت المباشر في قاعدة البيانات في خانة created_at
    cursor.execute('''
        INSERT INTO bookings (client_name, client_phone, service_id, booking_date, booking_time, created_at) 
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, phone, service_id, date, time, current_now))
    conn.commit()
    conn.close()
    return redirect('/admin')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        input_password = request.form['password']
        if input_password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect('/admin')
        else:
            return render_template('login.html', error="كلمة السر خاطئة! حاول مجدداً.")
    return render_template('login.html')

@app.route('/admin')
def admin_dashboard():
    if not session.get('logged_in'):
        return redirect('/login')
        
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    bookings = cursor.execute('SELECT * FROM bookings ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('dashboard.html', bookings=bookings)

@app.route('/delete/<int:booking_id>')
def delete_booking(booking_id):
    if not session.get('logged_in'):
        return redirect('/login')
        
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM bookings WHERE id = ?', (booking_id,))
    conn.commit()
    conn.close()
    return redirect('/admin')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)