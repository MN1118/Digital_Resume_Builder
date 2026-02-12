from flask import Flask, render_template, request, redirect, send_file, session
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from fpdf import FPDF
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "super-secret-key")


# ================= DATABASE CONNECTION =================

def get_connection():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

# ================= ROUTES =================


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/auth")
def auth():
    return render_template("auth.html")


@app.route("/builder")
def builder():
    if "user_id" not in session:
        return redirect("/auth")
    return render_template("builder.html")


# ================= REGISTER =================

@app.route("/register", methods=["POST"])
def register():
    name = request.form["name"]
    email = request.form["email"]
    password = request.form["password"]

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE email=%s", (email,))
    existing = cur.fetchone()

    if existing:
        cur.close()
        conn.close()
        return "Email already registered."

    hashed_password = generate_password_hash(password)

    cur.execute(
        "INSERT INTO users(name,email,password) VALUES(%s,%s,%s)",
        (name, email, hashed_password)
    )

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/auth")


# ================= LOGIN =================

@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"]
    password = request.form["password"]

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = cur.fetchone()

    cur.close()
    conn.close()

    if user and check_password_hash(user["password"], password):
        session["user_id"] = user["user_id"]   # FIXED
        session["user_name"] = user["name"]
        return redirect("/builder")

    return "Invalid credentials."


# ================= LOGOUT =================

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ================= SAVE RESUME =================

@app.route("/save_resume", methods=["POST"])
def save():
    if "user_id" not in session:
        return redirect("/auth")

    # 🔥 FIXED — DEFINE VARIABLES
    full_name = request.form.get("full_name")
    email = request.form.get("email")
    phone = request.form.get("phone")
    summary = request.form.get("summary")
    skills = request.form.get("skills")
    experience = request.form.get("experience")
    education = request.form.get("education")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO resume 
        (user_id, full_name, email, phone, summary, skills, experience, education)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        session["user_id"],
        full_name,
        email,
        phone,
        summary,
        skills,
        experience,
        education
    ))

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/generate")


# ================= GENERATE PDF =================

@app.route("/generate")
def generate():
    if "user_id" not in session:
        return redirect("/auth")

    conn = get_connection()
    cur = conn.cursor()

    # 🔥 FIXED COLUMN NAME
    cur.execute(
        "SELECT * FROM resume WHERE user_id=%s ORDER BY resume_id DESC LIMIT 1",
        (session["user_id"],)
    )

    r = cur.fetchone()

    if not r:
        return "No resume found."

    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, r[2], ln=True)

    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, r[3], ln=True)
    pdf.cell(0, 8, r[4], ln=True)
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Professional Summary", ln=True)
    pdf.set_font("Helvetica", "", 12)
    pdf.multi_cell(0, 8, r[5])
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Skills", ln=True)
    pdf.set_font("Helvetica", "", 12)
    pdf.multi_cell(0, 8, r[6])
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Experience", ln=True)
    pdf.set_font("Helvetica", "", 12)
    pdf.multi_cell(0, 8, r[7])
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Education", ln=True)
    pdf.set_font("Helvetica", "", 12)
    pdf.multi_cell(0, 8, r[8])

    filename = "resume.pdf"
    pdf.output(filename)

    cur.close()
    conn.close()

    return send_file(filename, as_attachment=True)


# ================= RUN =================

if __name__ == "__main__":
    app.run()
