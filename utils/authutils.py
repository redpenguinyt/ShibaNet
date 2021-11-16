from flask import Flask, request, render_template, redirect, url_for, session
from flask_pymongo import PyMongo
from .email import confirmemail
from .utils import generate_id
import bcrypt, os

app = Flask('ShibaNet')
app.config["MONGO_URI"] = os.environ["MONGO_URI"]
mongo = PyMongo(app)

@app.route("/login", methods=["POST", "GET"])
def login():
	if request.method == "GET":
		if "username" in session:
			return render_template("home.html")
		return render_template("auth/login.html", hidenav=True)
	
	users = mongo.db.users
	login_user = users.find_one({"name": request.form["username"]})

	if login_user:
		if bcrypt.hashpw(request.form["password"].encode("utf-8"), login_user["password"]) == login_user["password"]:
			session["username"] = request.form["username"]
			return redirect(url_for("index"))
	
	return render_template("auth/login.html", hidenav=True, error="Incorrect username or password")

@app.route("/logout")
def logout():
	session.clear()
	return redirect(url_for('index'))

@app.route("/register", methods=["POST","GET"])
def register():
	if request.method == "POST":
		users = mongo.db.users
		existing_user = users.find_one({"name": request.form["username"]})
		existing_email = users.find_one({"email": request.form["email"]})
		if existing_user is None:
			if existing_email is None:
				hashpass = bcrypt.hashpw(request.form["password"].encode("utf-8"), bcrypt.gensalt())

				confirm_key = generate_id(10)

				new_user = {
					"name": request.form["username"],
					"email": request.form["email"],
					"password": hashpass,
					"key": confirm_key
				}

				# Confirm email
				confirmemail(new_user, confirm_key)

				tmp_users = mongo.db.tmp_users
				tmp_users.delete_many({'email': request.form["email"]})
				tmp_users.insert_one(new_user)

				return render_template("message.html",title="Confirm email address",body="Check your email")
			else:
				return render_template("auth/register.html", hidenav=True, error="Email is already in use")
		else:
			return render_template("auth/register.html", hidenav=True, error="Username already exists")

	return render_template("auth/register.html", hidenav=True)

@app.route("/confirm/<email>/<key>")
def confirm(email, key):
	tmp_users = mongo.db.tmp_users
	tmp_user = tmp_users.find_one({"email": email})
	if tmp_user:
		if tmp_user["key"] == key:
			mongo.db.users.insert_one(
				{
					"name": tmp_user["name"],
					"email": tmp_user["email"],
					"password": tmp_user["password"]
				}
			)
			tmp_users.delete_one({'email': email})
			session["username"] = tmp_user["name"]
			return redirect(url_for("index"))
	
	return render_template("message.html", title="Couldn't confirm email", body="Try again")