import sqlite3
from flask import Flask, render_template, request, redirect, session
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "minde_secret_key_123" 

DB_NAME = "salon.db"
ADMIN_PASSWORD = "123" 

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # جدول الحجوزات الشامل مع عمود الحالة status
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            client_phone TEXT NOT NULL,
            service_id INTEGER NOT NULL,
            booking_date TEXT NOT NULL,
            booking_time TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'قيد الانتظار'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price INTEGER NOT NULL
        )
    ''')
    
    cursor.execute('SELECT COUNT(*) FROM services')
    if cursor.fetchone()[0] == 0:
        default_services = [
            ("تدليك استرخائي كامل (60 دقيقة)", 3000),
            ("تدليك علاجي للظهر (45 دقيقة)", 2500),
            ("العناية بالوجه والجسد (90 دقيقة)", 5000)
        ]
        cursor.executemany('INSERT INTO services (name, price) VALUES (?, ?)', default_services)
    
    # تحديثات أمان لقواعد البيانات القديمة (إضافة الأعمدة إن لم تكن موجودة)
    try:
        cursor.execute("ALTER TABLE bookings ADD COLUMN created_at TEXT")
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute("ALTER TABLE bookings ADD COLUMN status TEXT DEFAULT 'قيد الانتظار'")
    except sqlite3.OperationalError:
        pass
        
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    services = cursor.execute('SELECT * FROM services').fetchall()
    conn.close()
    return render_template('index.html', services=services)

@app.route('/book', methods=['POST'])
def book():
    name = request.form['name']
    phone = request.form['phone']
    service_id = request.form['service_id']
    date = request.form['date']
    time = request.form['time']
    
    current_now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM bookings WHERE client_name = ? AND booking_date = ? AND booking_time = ?', (name, date, time))
    if cursor.fetchone():
        conn.close()
        return "<h1>⚠️ عذرًا، هذا الحجز مسجل بالفعل مسبقاً!</h1><a href='/'>العودة ومحاولة وقت آخر</a>"
    
    cursor.execute('''
        INSERT INTO bookings (client_name, client_phone, service_id, booking_date, booking_time, created_at, status) 
        VALUES (?, ?, ?, ?, ?, ?, 'قيد الانتظار')
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
    
    bookings = cursor.execute('''
        SELECT bookings.*, services.name AS service_name, services.price AS service_price 
        FROM bookings 
        LEFT JOIN services ON bookings.service_id = services.id 
        ORDER BY bookings.id DESC
    ''').fetchall()
    
    services = cursor.execute('SELECT * FROM services').fetchall()
    
    # حساب الإحصائيات
    total_bookings = cursor.execute('SELECT COUNT(*) FROM bookings').fetchone()[0]
    
    # الأرباح المتوقعة المحسوبة فقط من المواعيد (المؤكدة أو المكتملة)
    total_revenue = cursor.execute('''
        SELECT SUM(services.price) 
        FROM bookings 
        JOIN services ON bookings.service_id = services.id
        WHERE bookings.status IN ('مؤكد', 'مكتمل')
    ''').fetchone()[0]
    if total_revenue is None: total_revenue = 0
    
    most_popular_query = '''
        SELECT services.name, COUNT(bookings.id) as count 
        FROM bookings 
        JOIN services ON bookings.service_id = services.id 
        GROUP BY bookings.service_id 
        ORDER BY count DESC LIMIT 1
    '''
    popular_result = cursor.execute(most_popular_query).fetchone()
    most_popular_service = popular_result[0] if popular_result else "لا توجد حجوزات بعد"
    
    conn.close()
    return render_template('dashboard.html', 
                           bookings=bookings, 
                           services=services,
                           total_bookings=total_bookings,
                           total_revenue=total_revenue,
                           most_popular_service=most_popular_service)

# 🔄 مسار جديد لتحديث حالة الحجز
@app.route('/update_status/<int:booking_id>/<string:new_status>')
def update_status(booking_id, new_status):
    if not session.get('logged_in'):
        return redirect('/login')
        
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE bookings SET status = ? WHERE id = ?', (new_status, booking_id))
    conn.commit()
    conn.close()
    return redirect('/admin')

@app.route('/add_service', methods=['POST'])
def add_service():
    if not session.get('logged_in'):
        return redirect('/login')
    name = request.form['service_name']
    price = request.form['service_price']
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO services (name, price) VALUES (?, ?)', (name, price))
    conn.commit()
    conn.close()
    return redirect('/admin')

@app.route('/delete_service/<int:service_id>')
def delete_service(service_id):
    if not session.get('logged_in'):
        return redirect('/login')
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM services WHERE id = ?', (service_id,))
    conn.commit()
    conn.close()
    return redirect('/admin')

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