from flask import Flask, render_template, url_for, request, redirect, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3
import io
from flask import send_file
import random
from flask import session, request, redirect, url_for, render_template, flash
from flask import request, jsonify



db_local = "DB.db"

app = Flask(__name__)
app.secret_key = "secret123"   # ต้องมีสำหรับ session
# ==============================
# สร้างตาราง images
# ==============================
def create_image_table():
    connect = sqlite3.connect(db_local)
    cursor = connect.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        image BLOB
    )
    """)

    connect.commit()
    connect.close()

create_image_table()

@app.route("/upload_qr", methods=["GET", "POST"])
@login_required
def upload_qr():

    if request.method == "POST":

        selected_price = request.form.get("price")

        if "image" not in request.files:
            return "No file selected"

        file = request.files["image"]

        if file.filename == "":
            return "No file chosen"

        if not selected_price:
            return "Please select price"

        # 🔥 สร้างชื่อ qr จากราคาที่เลือก
        qr_name = "qr" + selected_price

        img_data = file.read()

        connect = sqlite3.connect(db_local)
        cursor = connect.cursor()

        # ==========================
        # เช็คก่อนว่ามี qr นี้ไหม
        # ==========================
        cursor.execute(
            "SELECT id FROM images WHERE name = ?",
            (qr_name,)
        )
        existing = cursor.fetchone()

        if existing:
            # 🔥 ถ้ามีแล้ว → UPDATE
            cursor.execute(
                "UPDATE images SET image = ? WHERE name = ?",
                (img_data, qr_name)
            )
            connect.commit()
            message = f"{qr_name} updated successfully"

        else:
            # 🔥 ถ้ายังไม่มี → INSERT
            cursor.execute(
                "INSERT INTO images (name, image) VALUES (?, ?)",
                (qr_name, img_data)
            )
            connect.commit()
            message = f"{qr_name} uploaded successfully"

        connect.close()
        return message

    return '''
    <h2>Upload QR Code</h2>
    <form method="POST" enctype="multipart/form-data">
        
        <label>เลือกราคา:</label><br><br>
        <select name="price">
            <option value="">-- Select Price --</option>
            <option value="20">20 บาท</option>
            <option value="40">40 บาท</option>
            <option value="60">60 บาท</option>
            <option value="80">80 บาท</option>
            <option value="100">100 บาท</option>
            <option value="120">120 บาท</option>
        </select>
        <br><br>

        <input type="file" name="image"><br><br>

        <input type="submit" value="Upload">
    </form>
    '''
    
# ==============================
# View QR
# ==============================
@app.route("/view_qr/<qr_name>")
@login_required
def view_qr(qr_name):

    connect = sqlite3.connect(db_local)
    cursor = connect.cursor()

    cursor.execute(
        "SELECT image FROM images WHERE name = ?",
        (qr_name,)
    )

    data = cursor.fetchone()
    connect.close()

    if data is None:
        return "No QR found"

    else:
        return send_file(
            io.BytesIO(data[0]),
            mimetype="image/png"
        )
        


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# ==============================
# User Class
# ==============================
class User(UserMixin):
    def __init__(self, username):
        self.id = username


# ==============================
# โหลด user จาก database
# ==============================
@login_manager.user_loader
def load_user(user_id):
    connect = sqlite3.connect(db_local)
    cursor = connect.cursor()
    cursor.execute("SELECT username FROM users WHERE username = ?", (user_id,))
    user = cursor.fetchone()
    connect.close()

    if user:
        return User(user[0])
    else:
        return None


# ==============================
# หน้า Home
# ==============================
@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", username=current_user.id)


# ==============================
# หน้า Login
# ==============================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        connect = sqlite3.connect(db_local)
        cursor = connect.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password)
        )

        user = cursor.fetchone()
        connect.close()

        # ========================
        # ใช้ if - else ชัด ๆ
        # ========================
        if user:
            user_obj = User(username)
            login_user(user_obj)
            return redirect(url_for("dashboard"))
        else:
            flash("Username or Password incorrect")

    return render_template("login.html")


# ==============================
# Logout
# ==============================
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():

    if request.method == "POST":
        old_password = request.form.get("old_password")
        new_password = request.form.get("new_password")

        connect = sqlite3.connect(db_local)
        cursor = connect.cursor()

        # ตรวจสอบรหัสเดิมก่อน
        cursor.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (current_user.id, old_password)
        )

        user = cursor.fetchone()

        if user:
            cursor.execute(
                "UPDATE users SET password = ? WHERE username = ?",
                (new_password, current_user.id)
            )
            connect.commit()
            connect.close()

            flash("เปลี่ยนรหัสผ่านสำเร็จ")
            return redirect(url_for("profile"))

        else:
            connect.close()
            flash("รหัสผ่านเดิมไม่ถูกต้อง")

    return render_template("change_password.html")


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():

    if request.method == 'POST':

        # กรณีกดส่งเบอร์
        if "phone" in request.form:
            phone = request.form['phone']

            # สร้าง OTP 6 หลัก
            otp = random.randint(100000, 999999)

            # เก็บ OTP ไว้ใน session
            session['otp'] = str(otp)
            session['phone'] = phone

            print("OTP คือ:", otp)  # ตอนนี้ยังไม่ส่ง SMS จริง แค่โชว์ใน console

            flash("OTP ถูกส่งไปยังเบอร์ของคุณแล้ว")
            return redirect(url_for('forgot_password'))

        # กรณีกดตรวจสอบ OTP
        elif "otp_input" in request.form:
            otp_input = request.form['otp_input']

            if otp_input == session.get('otp'):
                return redirect(url_for('reset_password'))
            else:
                flash("OTP ไม่ถูกต้อง กรุณาลองใหม่")
                return redirect(url_for('forgot_password'))

    return render_template('forgot_password.html')

@app.route('/reset_password')
def reset_password():
    return "<h1>เปลี่ยนรหัสผ่านได้ตรงนี้ (ทำต่อได้เลย)</h1>"

# ==============================
# เพิ่ม user (ของเดิม ปรับให้ปลอดภัย)
# ==============================
@app.route("/addusers", methods=["POST", "GET"])
def addusers():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        connect = sqlite3.connect(db_local)
        cursor = connect.cursor()

        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password)
        )

        connect.commit()
        connect.close()

    return render_template("addusers.html")

    
@app.route("/credit", methods=["GET", "POST"])
@login_required
def credit():

    if request.method == "POST":
        selected_time = request.form.get("package")

        if selected_time == "30min":
            hour_text = "30 นาที"
            price = 20

        elif selected_time == "1hour":
            hour_text = "1 ชั่วโมง"
            price = 40

        elif selected_time == "1_30":
            hour_text = "1 ชั่วโมง 30 นาที"
            price = 60

        elif selected_time == "2hour":
            hour_text = "2 ชั่วโมง"
            price = 80

        elif selected_time == "2_30":
            hour_text = "2 ชั่วโมง 30 นาที"
            price = 100

        elif selected_time == "3hour":
            hour_text = "3 ชั่วโมง"
            price = 120

        else:
            flash("กรุณาเลือกแพ็คเกจ")
            return redirect(url_for("credit"))

        # 🔥 สร้างชื่อ qr จากราคา
        qr_name = "qr" + str(price)

        return render_template(
            "payment.html",
            hour_text=hour_text,
            price=price,
            qr_name=qr_name
        )

    return render_template("credit.html")

# ==============================
# หน้า Contact
# ==============================
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':

        data = request.get_json()
        message = data.get('message')

        # บันทึกลง database ตรงนี้

        return jsonify({"status": "success"})

    return render_template("contact.html")


# ==============================
# สร้างตาราง messages
# ==============================
def create_message_table():
    connect = sqlite3.connect(db_local)
    cursor = connect.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    connect.commit()
    connect.close()

create_message_table()


# ==============================
# หน้า Profile
# ==============================
@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html", username=current_user.id)


#==================================   ส่วนของ admin ฟังก์ชัน ดูข้อความจาก users.   ===============================================
# ==============================
# หน้า Admin ดูข้อความลูกค้า
# ==============================
@app.route("/admin_messages")
def admin_messages():

    connect = sqlite3.connect(db_local)
    cursor = connect.cursor()

    cursor.execute("""
    SELECT id, username, message, created_at
    FROM messages
    ORDER BY created_at DESC
""")

    all_messages = cursor.fetchall()
    connect.close()

    return render_template(
        "admin_messages.html",
        messages=all_messages
    )
    
    
# ==============================
# ลบข้อความ
# ==============================
@app.route("/delete_message/<int:msg_id>")
def delete_message(msg_id):

    connect = sqlite3.connect(db_local)
    cursor = connect.cursor()

    # เช็คก่อนว่ามีข้อความนี้จริงไหม
    cursor.execute("SELECT id FROM messages WHERE id = ?", (msg_id,))
    message = cursor.fetchone()

    if message:
        cursor.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
        connect.commit()
        connect.close()
        flash("ลบข้อความเรียบร้อยแล้ว")
    else:
        connect.close()
        flash("ไม่พบข้อความนี้")

    return redirect(url_for("admin_messages"))

# ===============================================.  ของ addmin จบตรงนี้   ================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)  