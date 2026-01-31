import sqlite3

from flask import Flask, flash, redirect, render_template, request, session, g
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

DATABASE = "project.db"

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row  # Allow accessing columns by name
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    get_db().commit() # Commit by default for simplicity in this project scope
    return (rv[0] if rv else None) if one else rv


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

def login_required(f):
    """
    Decorate routes to require login.
    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
@login_required
def index():
    """Show dashboard"""
    user_id = session["user_id"]
    courses = query_db("SELECT * FROM courses WHERE user_id = ?", (user_id,))
    return render_template("dashboard.html", courses=courses)

@app.route("/create_class", methods=["GET", "POST"])
@login_required
def create_class():
    """Create a new class/course"""
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        weekdays = request.form.get("weekdays")
        time = request.form.get("time")
        mode = request.form.get("mode")
        platform = request.form.get("platform")

        if not name:
            return "Must provide class name", 400
        
        user_id = session["user_id"]
        query_db("""
            INSERT INTO courses (user_id, name, description, weekdays, time, mode, platform) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, name, description, weekdays, time, mode, platform))
        
        flash("Class created successfully!")
        return redirect("/")
    else:
        return render_template("create_class.html")

@app.route("/course/<int:course_id>")
@login_required
def course(course_id):
    """View a specific course and its lessons"""
    user_id = session["user_id"]
    
    # Ensure course exists and belongs to user
    course = query_db("SELECT * FROM courses WHERE id = ? AND user_id = ?", (course_id, user_id), one=True)
    if course is None:
        return "Course not found", 404
        
    lessons = query_db("SELECT * FROM lessons WHERE course_id = ? ORDER BY date", (course_id,))
    
    return render_template("course.html", course=course, lessons=lessons)

@app.route("/course/<int:course_id>/add_lesson", methods=["GET", "POST"])
@login_required
def add_lesson(course_id):
    """Add a lesson to a course"""
    user_id = session["user_id"]
    
    # Ensure course exists and belongs to user
    course = query_db("SELECT * FROM courses WHERE id = ? AND user_id = ?", (course_id, user_id), one=True)
    if course is None:
        return "Course not found", 404

    if request.method == "POST":
        title = request.form.get("title")
        topic = request.form.get("topic")
        date = request.form.get("date")
        private_notes = request.form.get("private_notes")

        if not title or not date:
            return "Must provide title and date", 400
            
        query_db("INSERT INTO lessons (course_id, title, topic, date, private_notes) VALUES (?, ?, ?, ?, ?)", 
                 (course_id, title, topic, date, private_notes))
                 
        flash("Lesson added successfully!")
        return redirect(f"/course/{course_id}")
    else:
        return render_template("add_lesson.html", course=course)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any user_id
    session.clear()

    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return "must provide username", 403

        # Ensure password was submitted
        elif not request.form.get("password"):
            return "must provide password", 403

        # Query database for username
        rows = query_db("SELECT * FROM users WHERE username = ?", (request.form.get("username"),))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return "invalid username and/or password", 403

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""
    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username:
             return "must provide username", 400
        if not password:
             return "must provide password", 400
        if not confirmation or password != confirmation:
             return "passwords must match", 400

        hash_password = generate_password_hash(password)

        try:
            query_db("INSERT INTO users (username, hash) VALUES(?, ?)", (username, hash_password))
        except ValueError:
             return "username taken", 400

        # Log in automatically
        rows = query_db("SELECT * FROM users WHERE username = ?", (username,))
        session["user_id"] = rows[0]["id"]

        return redirect("/")

    else:
        return render_template("register.html")
