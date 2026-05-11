from flask import Flask, render_template, request, redirect, session
import pyodbc

app = Flask(__name__)
app.secret_key = "salamtak_secret"


# ================= DATABASE =================
def get_db():
    return pyodbc.connect(
        r"Driver={ODBC Driver 17 for SQL Server};"
        r"Server=DESKTOP-8MI2AQC\SQLEXPRESS;"
        r"Database=Salamtak;"
        r"Trusted_Connection=yes;"
        r"TrustServerCertificate=yes;"
    )


# ================= LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        )

        user = cursor.fetchone()
        conn.close()

        if user:
            session["user"] = user[1]
            session["role"] = user[11]

            if session["role"] == "admin":
                return redirect("/admin")
            elif session["role"] == "pharmacist":
                return redirect("/pharmacist")
            elif session["role"] == "doctor":
                return redirect("/doctor")
            else:
                return redirect("/dashboard")
        else:
            error = "Invalid login"

    return render_template("login.html", error=error)

@app.route("/add_user", methods=["GET", "POST"])
def add_user():

    if session.get("role") != "admin":
        return redirect("/login")

    if request.method == "POST":

        first_name = request.form["first_name"]
        middle_name = request.form["middle_name"]
        last_name = request.form["last_name"]
        email = request.form["email"]
        phone = request.form["phone"]
        password = request.form["password"]
        role = request.form["role"]

        full_name = f"{first_name} {middle_name} {last_name}"

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO users (username, first_name, middle_name, last_name, email, phone, password, role, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            full_name,
            first_name,
            middle_name,
            last_name,
            email,
            phone,
            password,
            role,
            "approved"
        ))

        conn.commit()
        conn.close()

        return redirect("/admin")

    return render_template("add_user.html")

# ================= ADMIN =================
@app.route("/admin")
def admin():
    if session.get("role") != "admin":
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    conn.close()

    return render_template("admin.html", users=users)


# ================= DOCTORS =================
@app.route("/doctors")
def doctors():
    if session.get("role") != "admin":
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT d.doctor_id, u.username, d.specialization
        FROM Doctors d
        JOIN users u ON d.user_id = u.id
    """)

    data = cursor.fetchall()
    conn.close()

    return render_template("doctors.html", doctors=data)


# ================= DEPARTMENTS =================
@app.route("/departments")
def departments():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Departments")
    data = cursor.fetchall()

    conn.close()
    return render_template("departments.html", departments=data)


# ================= APPOINTMENTS =================
@app.route("/appointments")
def appointments():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Appointments")
    data = cursor.fetchall()

    conn.close()
    return render_template("appointments.html", appointments=data)


# ================= MEDICINES STOCK (SEARCH WORKS) =================
@app.route("/medicines_stock")
def medicines_stock():

    if session.get("role") not in ["admin", "pharmacist"]:
        return redirect("/login")

    search = request.args.get("search", "").strip()

    conn = get_db()
    cursor = conn.cursor()

    if search:
        cursor.execute("""
            SELECT * FROM Medicines
            WHERE name LIKE ?
               OR description LIKE ?
               OR CAST(price AS VARCHAR) LIKE ?
        """, (f"%{search}%", f"%{search}%", f"%{search}%"))
    else:
        cursor.execute("SELECT * FROM Medicines")

    medicines = cursor.fetchall()
    conn.close()

    return render_template(
        "medicines_stock.html",
        medicines=medicines,
        search=search
    )

@app.route("/pharmacy_stock")
def pharmacy_stock():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Medicines")
    meds = cursor.fetchall()

    conn.close()

    return render_template("pharmacy_stock.html", meds=meds)

# ================= PHARMACY PRESCRIPTIONS (SEARCH WORKS) =================
@app.route("/pharmacy_prescriptions")
def pharmacy_prescriptions():

    if session.get("role") not in ["admin", "pharmacist"]:
        return redirect("/login")

    search = request.args.get("search", "").strip()

    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT 
            p.prescription_id,
            p.appointment_id,
            du.username,
            pu.username,
            p.issue_date
        FROM Prescription p
        JOIN Doctors d ON p.doctor_id = d.doctor_id
        JOIN users du ON d.user_id = du.id
        JOIN Patients pa ON p.patient_id = pa.patient_id
        JOIN users pu ON pa.user_id = pu.id
    """

    if search:
        query += """
        WHERE 
            CAST(p.prescription_id AS VARCHAR) LIKE ?
            OR CAST(p.appointment_id AS VARCHAR) LIKE ?
            OR du.username LIKE ?
            OR pu.username LIKE ?
            OR CAST(p.issue_date AS VARCHAR) LIKE ?
        """

        cursor.execute(query, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        ))
    else:
        cursor.execute(query)

    data = cursor.fetchall()
    conn.close()

    return render_template(
        "pharmacy_prescriptions.html",
        prescriptions=data,
        search=search
    )


# ================= PRESCRIPTIONS =================
@app.route("/prescriptions")
def prescriptions():

    search = request.args.get("search", "").strip()

    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT 
            p.prescription_id,
            du.username,
            pu.username,
            p.issue_date
        FROM Prescription p
        JOIN Doctors d ON p.doctor_id = d.doctor_id
        JOIN users du ON d.user_id = du.id
        JOIN Patients pa ON p.patient_id = pa.patient_id
        JOIN users pu ON pa.user_id = pu.id
    """

    if search:
        query += """
        WHERE 
            CAST(p.prescription_id AS VARCHAR) LIKE ?
            OR du.username LIKE ?
            OR pu.username LIKE ?
            OR CAST(p.issue_date AS VARCHAR) LIKE ?
        """

        cursor.execute(query, (f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"))
    else:
        cursor.execute(query)

    data = cursor.fetchall()
    conn.close()

    return render_template("prescriptions.html", prescriptions=data, search=search)


# ================= PHARMACIST =================
@app.route("/pharmacist")
def pharmacist():
    if session.get("role") != "pharmacist":
        return redirect("/login")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Medicines")
    medicines = cursor.fetchall()

    cursor.execute("""
        SELECT p.prescription_id, p.appointment_id,
               du.username, pu.username, p.issue_date
        FROM Prescription p
        JOIN Doctors d ON p.doctor_id = d.doctor_id
        JOIN users du ON d.user_id = du.id
        JOIN Patients pa ON p.patient_id = pa.patient_id
        JOIN users pu ON pa.user_id = pu.id
    """)

    prescriptions = cursor.fetchall()
    conn.close()

    return render_template(
        "pharmacist.html",
        medicines=medicines,
        prescriptions=prescriptions
    )


# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    return f"Welcome {session['user']}"


# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)