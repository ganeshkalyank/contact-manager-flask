from flask import Flask, render_template, url_for, flash, request, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user, fresh_login_required
from os import environ, path
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
is_gunicorn = "gunicorn" in environ.get("SERVER_SOFTWARE", "")
if is_gunicorn:
    app.config["SQLALCHEMY_DATABASE_URI"] = environ.get("DATABASE_URL").replace("postgres://","postgresql://") # production database
    app.config["SECRET_KEY"] = environ.get("SESSION_KEY") # production session key
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db" # development database
    app.config["SECRET_KEY"] = "may the force be with you" # development session key
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(150))
    email = db.Column(db.String(150), unique = True)
    password = db.Column(db.String(150))
    contacts = db.relationship("Contacts")

class Contacts(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(150))
    email = db.Column(db.String(150))
    mobile = db.Column(db.String(15))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

if not is_gunicorn:
    if not path.exists("database.db"):
        db.create_all()

if is_gunicorn:
    @app.before_request
    def before_request():
        if not request.is_secure:
            url = request.url.replace('http://', 'https://', 1)
            code = 301
            return redirect(url, code=code)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message_category = "error"
login_manager.refresh_view = "login"
login_manager.needs_refresh_message = "Please logout and login again to access that page!"
login_manager.needs_refresh_message_category = "error"
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["POST","GET"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = Users.query.filter_by(email=email).first()
        if not user:
            flash("Email is not registered!", category="error")
        elif not check_password_hash(user.password, password=password):
            flash("Password is wrong!", category="error")
        else:
            login_user(user=user, remember=True)
            flash("Logged in successfully!", category="success")
            next = request.args.get("next")
            if next:
                url = next
            else:
                url = url_for("index")
            return redirect(url)
    return render_template("login.html")

@app.route("/signup", methods=["POST","GET"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")
        user = Users.query.filter_by(email=email).first()
        if user:
            flash("Email already exists!", category="error")
        elif len(name) < 3:
            flash("Name is too short!", category="error")
        elif len(email) < 5:
            flash("Email is not vaild!", category="error")
        elif len(password1) < 8:
            flash("Password is too short!", category="error")
        elif not password1 == password2:
            flash("Passwords do not match!", category="error")
        else:
            new_user = Users(name=name,email=email,password=generate_password_hash(password1))
            db.session.add(new_user)
            db.session.commit()
            flash("Account created successfully! Login to continue...", category="success")
            return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/dashboard", methods=["POST","GET"])
@login_required
def dashboard():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "new":
            name = request.form.get("name")
            email = request.form.get("email")
            mobile = request.form.get("mobile")
            new_contact = Contacts(name=name,email=email,mobile=mobile,user_id=current_user.id)
            db.session.add(new_contact)
            db.session.commit()
            return redirect(url_for("dashboard"))
        elif action == "edit":
            id = int(request.form.get("id"))
            name = request.form.get("name")
            email = request.form.get("email")
            mobile = request.form.get("mobile")
            contact_to_be_edited = Contacts.query.get(id)
            if contact_to_be_edited.user_id == current_user.id:
                contact_to_be_edited.name = name
                contact_to_be_edited.email = email
                contact_to_be_edited.mobile = mobile
                db.session.commit()
            return redirect(url_for("dashboard"))
        elif action == "delete":
            id = int(request.form.get("id"))
            contact_to_be_deleted = Contacts.query.get(id)
            if contact_to_be_deleted.user_id == current_user.id:
                db.session.delete(contact_to_be_deleted)
                db.session.commit()
            return redirect(url_for("dashboard"))
        else:
            return redirect(url_for("dashboard"))
    return render_template("dashboard.html")

@app.route("/profile", methods=["POST","GET"])
@fresh_login_required
def profile():
    if request.method == "POST":
        id = request.form.get("id")
        name = request.form.get("name")
        email = request.form.get("email")
        if email == current_user.email:
            user_check = None
        else:
            user_check = Users.query.filter_by(email=email).first()
        if len(name) < 3:
            flash("Name is too short!", category="error")
        elif user_check:
            flash("Email already exists!", category="error")
        elif len(email) < 5:
            flash("Email is invalid!", category="error")
        elif current_user.id == id:
            user_to_be_edited = Users.query.get(int(id))
            user_to_be_edited.name = name
            user_to_be_edited.email = email
            db.session.commit()
            flash("Profile details updated successfully!", category="success")
            return redirect(url_for("profile"))
        else:
            flash("Some error occurred!", category="error")
    return render_template("profile.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
