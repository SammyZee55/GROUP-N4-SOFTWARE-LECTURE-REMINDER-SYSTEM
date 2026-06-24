from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from email.mime.text import MIMEText
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import smtplib
import os

# ---------------- Flask Setup ---------------- #
app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------- Database Setup ---------------- #
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///lecture_reminders.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ---------------- Models ---------------- #
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    reminders = db.relationship("Reminder", backref="user", lazy=True)


class Reminder(db.Model):
    __tablename__ = "reminders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(20), nullable=False)

    sent = db.Column(db.Boolean, default=False)

# ---------------- Create Tables ---------------- #
with app.app_context():
    db.create_all()

# ---------------- EMAIL FUNCTION ---------------- #
def send_email(to_email, subject, body):
    sender_email = os.getenv("EMAIL_USER")
    sender_password = os.getenv("EMAIL_PASSSWORD")


    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to_email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()

        print(f"Email sent to {to_email}")

    except Exception as e:
        print("Email failed:", e)
        

# ---------------- SCHEDULER FUNCTION ---------------- #
def check_reminders():
    with app.app_context():

        now = datetime.now()
        today = now.strftime("%Y-%m-%d")

        reminders = Reminder.query.filter_by(date=today, sent=False).all()

        for reminder in reminders:
            try:
                reminder_time = datetime.strptime(reminder.time, "%H:%M")

                if reminder_time.hour == now.hour and reminder_time.minute == now.minute:

                    user = User.query.get(reminder.user_id)

                    if user:
                        send_email(
                            user.email,
                            f"Lecture Reminder: {reminder.title}",
                            f"""
Lecture Reminder

Title: {reminder.title}
Description: {reminder.description}
Date: {reminder.date}
Time: {reminder.time}

Prepare for your lecture.
                            """
                        )

                        reminder.sent = True
                        db.session.commit()

            except Exception as e:
                print("Reminder check error:", e)

# ---------------- SCHEDULER SETUP ---------------- #
scheduler = BackgroundScheduler()
scheduler.add_job(
    func=check_reminders,
    trigger="interval",
    minutes=1,
    id="reminder_job",
    replace_existing=True
)

# IMPORTANT: Start scheduler safely AFTER setup

# ---------------- ROUTES ---------------- #

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('home.html')


# ---------------- REGISTER ---------------- #
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        try:
            new_user = User(username=username, email=email, password=password)
            db.session.add(new_user)
            db.session.commit()

            flash("Registration successful! Please login.", "success")
            return redirect(url_for('login'))

        except Exception as e:
            db.session.rollback()
            flash("Username or email already exists!", "danger")
            return redirect(url_for('register'))

    return render_template('register.html')


# ---------------- LOGIN ---------------- #
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username

            flash(f"Welcome, {username}!", "success")
            return redirect(url_for('dashboard'))

        flash("Invalid username or password!", "danger")
        return redirect(url_for('login'))

    return render_template('login.html')


# ---------------- LOGOUT ---------------- #
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect(url_for('login'))


# ---------------- ADD REMINDER ---------------- #
@app.route('/add', methods=['GET', 'POST'])
def add_reminder():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_reminder = Reminder(
            user_id=session['user_id'],
            title=request.form['title'],
            description=request.form['description'],
            date=request.form['date'],
            time=request.form['time'],
            sent=False
        )

        db.session.add(new_reminder)
        db.session.commit()

        flash("Reminder added successfully!", "success")
        return redirect(url_for('dashboard'))

    return render_template('add_reminder.html')


# ---------------- VIEW ---------------- #
@app.route('/view/<int:id>')
def view_reminder(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    reminder = Reminder.query.filter_by(
        id=id,
        user_id=session['user_id']
    ).first()

    return render_template('view_reminder.html', reminder=reminder)


# ---------------- EDIT ---------------- #
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_reminder(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    reminder = Reminder.query.filter_by(
        id=id,
        user_id=session['user_id']
    ).first()

    if request.method == 'POST':
        reminder.title = request.form['title']
        reminder.description = request.form['description']
        reminder.date = request.form['date']
        reminder.time = request.form['time']
        reminder.sent = False

        db.session.commit()

        flash("Reminder updated successfully!", "success")
        return redirect(url_for('dashboard'))

    return render_template('edit_reminder.html', reminder=reminder)


# ---------------- DELETE ---------------- #
@app.route('/delete/<int:id>')
def delete_reminder(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    reminder = Reminder.query.filter_by(
        id=id,
        user_id=session['user_id']
    ).first()

    db.session.delete(reminder)
    db.session.commit()

    flash("Reminder deleted successfully!", "success")
    return redirect(url_for('dashboard'))


# ---------------- DASHBOARD ---------------- #
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    today = datetime.now().strftime("%Y-%m-%d")

    reminders = Reminder.query.filter_by(user_id=user_id).all()

    today_reminders = Reminder.query.filter_by(
        user_id=user_id,
        date=today
    ).all()

    return render_template(
        'dashboard.html',
        reminders=reminders,
        today_reminders=today_reminders
    )


# ---------------- RUN APP ---------------- #
if __name__ == "__main__":
    scheduler.start()
    app.run(debug=True, use_reloader=False)
