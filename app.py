import sqlite3
from flask import Flask, render_template, request, redirect, session
import os

app = Flask(__name__)

# مفتاح أمان ضروري لتشغيل الـ Session (يمكنك كتابة أي نص عشوائي هنا)
app.secret_key = "minde_secret_key_123" 

DB_NAME = "salon.db"
ADMIN_PASSWORD = "123" # 🔑 كلمة السر الخاصة بصاحب الصالون (يمكنك تغييرها لاحقاً)

def init_db():
    if not os.path.exists(DB_NAME):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL,
                client_phone TEXT NOT NULL,
                service_id INTEGER NOT NULL,
                booking_date TEXT NOT NULL,
                booking_time TEXT NOT NULL
            )
        ''')
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
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM bookings WHERE client_name = ? AND booking_date = ? AND booking_time = ?', (name, date, time))
    if cursor.fetchone():
        conn.close()
        return "<h1>⚠️ عذرًا، هذا الحجز مسجل بالفعل مسبقاً!</h1><a href='/'>العودة ومحاولة وقت آخر</a>"
    
    cursor.execute('INSERT INTO bookings (client_name, client_phone, service_id, booking_date, booking_time) VALUES (?, ?, ?, ?, ?)', (name, phone, service_id, date, time))
    conn.commit()
    conn.close()
    return redirect('/admin')

# 🔒 مسار صفحة تسجيل الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        input_password = request.form['password']
        if input_password == ADMIN_PASSWORD:
            session['logged_in'] = True # تسجيل أنه دخل بنجاح
            return redirect('/admin')
        else:
            return render_template('login.html', error="كلمة السر خاطئة! حاول مجدداً.")
    return render_template('login.html')

# 🛡️ لوحة التحكم المحمية
@app.route('/admin')
def admin_dashboard():
    # فحص أمني: إذا لم يكن مسجلاً للدخول، يتم طرده لصفحة الـ login
    if not session.get('logged_in'):
        return redirect('/login')
        
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    bookings = cursor.execute('SELECT * FROM bookings ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('dashboard.html', bookings=bookings)

# 🗑️ مسار الحذف المحمي أيضاً
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

# 🚪 مسار تسجيل الخروج (إغلاق اللوحة)
@app.route('/logout')
def logout():
    session.clear() # مسح بيانات الدخول
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)