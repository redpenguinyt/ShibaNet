from flask import request, render_template, redirect, url_for, session
from functools import wraps
from .email import confirm_email, iforgor_email
from .utils import generate_id
from .flask import app, mongo
import bcrypt, datetime

# Auth

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'username' in session:
            return f(*args, **kwargs)
        else:
            return redirect(url_for('login',next=f.__name__))
    return wrap

@app.route("/login", methods=["POST", "GET"])
def login():
	if request.method == "GET":
		if "username" in session:
			return render_template("home.html")
		return render_template("auth/login.html", hidenav=True)
	
	users = mongo.db.users
	login_user = None
	try:
		if "@" in request.form["username"]:
			login_user = users.find_one({"email": request.form["username"]})
		else:
			login_user = users.find_one({"name": request.form["username"]})
	except:
		login_user = users.find_one({"name": request.form["username"]})

	if login_user:
		if bcrypt.hashpw(request.form["password"].encode("utf-8"), login_user["password"]) == login_user["password"]:
			session["username"] = login_user["name"]
			session["theme"] = login_user["theme"]
			if "next" in request.args:
				return redirect(url_for(request.args["next"]))
			return redirect(url_for("index"))
	elif mongo.db.tmp_users.find_one({"name": request.form["username"]}):
		return render_template("auth/login.html", hidenav=True, error="Please confirm your email first")
	
	return render_template("auth/login.html", hidenav=True, error="Incorrect username or password")

@app.route("/logout")
@login_required
def logout():
	session.clear()
	return redirect(url_for('index'))

# Register

@app.route("/register", methods=["POST","GET"])
def register():
	if request.method == "POST":
		users = mongo.db.users
		existing_user = users.find_one({"name": request.form["username"]})
		existing_email = users.find_one({"email": request.form["email"]})
		if not existing_user:
			if not existing_email:
				tmp_users = mongo.db.tmp_users
				hashpass = bcrypt.hashpw(request.form["password"].encode("utf-8"), bcrypt.gensalt())

				confirm_key = generate_id(10, tmp_users, "key")

				new_tmp_user = {
					"name": request.form["username"],
					"email": request.form["email"],
					"password": hashpass,
					"key": confirm_key,
					"timestamp": datetime.datetime.now(),
					"type": "new"
				}

				# Confirm email
				e_result = confirm_email(new_tmp_user)

				if e_result == "error":
					return render_template("auth/register.html", error="That email could not be used")

				tmp_users.delete_many({'email': request.form["email"]})
				tmp_users.insert_one(new_tmp_user)

				# Email not working, temporary fix
				return render_template("tmp_confirm.html", key=confirm_key)
				
				return render_template("message.html",title="Confirm email address", body=f"Check your email ({request.form['email']})", btnurl=url_for("resend_email",email=request.form['email']), btntag="Resend email")
			else:
				return render_template("auth/register.html", hidenav=True, error="Email is already in use")
		else:
			return render_template("auth/register.html", hidenav=True, error="Username is already in use")

	return render_template("auth/register.html", hidenav=True)

@app.route("/resend/<email>/")
def resend_email(email):
	user = mongo.db.tmp_users.find_one({"email": email})
	e_result = confirm_email(user)

	if e_result == "error":
		return render_template("auth/register.html", hidenav=True, error="That email could not be used")
	
	return render_template("message.html",
		title="Resent email address",
		body=f"Check your email ({user['email']})",
		btnurl=url_for("resend_email",email=user['email']),
		btntag="Resend email"
	)

@app.route("/confirm/new/")
def confirm():
	if not "key" in request.args:
		return render_template("message.html", title="Couldn't confirm email", body="Try again")
	key = request.args["key"]
	tmp_users = mongo.db.tmp_users
	tmp_user = tmp_users.find_one({"key": key,"type":"new"})
	if tmp_user:
		mongo.db.users.insert_one(
			{
				"name": tmp_user["name"],
				"email": tmp_user["email"],
				"password": tmp_user["password"],
				"following": ["ShibaNet_Official"],
				"bio": "",
				"pfp": "",
				"theme":"amethyst"
			}
		)
		mongo.db.notifications.insert_one({
			"user": tmp_user["name"],
			"notifs": [
				{
					"_id": "0001",
					"title": "Welcome to ShibaNet!",
					"body": "We hope you enjoy using the app :)",
					"timestamp": datetime.datetime.now(),
					"read": False
				}
			]
		})
		tmp_users.delete_many({'email': tmp_user["email"]})
		session["username"] = tmp_user["name"]
		session["theme"] = "amethyst"
		return redirect(url_for("index"))
	
	return render_template("message.html", title="Couldn't confirm email", body="Try again")

# Forgot password

@app.route("/iforgor", methods=["POST","GET"])
def forgot_password():
	if request.method == "GET":
		return render_template("auth/forgot.html", hidenav=True)
	
	lost_user = mongo.db.users.find_one({"email": request.form["email"]})

	if not lost_user:
		return render_template("auth/forgot.html", hidenav=True, error="Could not find a user with that email")
	
	confirm_key = generate_id(10)

	new_tmp_user = {
		"email": request.form["email"],
		"key": confirm_key,
		"type": "forgot"
	}

	iforgor_email(new_tmp_user)

	tmp_users = mongo.db.tmp_users
	tmp_users.delete_many({'email': request.form["email"]})
	tmp_users.insert_one(new_tmp_user)

	return render_template("message.html",title="Confirm email address", body=f"Check your email ({request.form['email']})")

@app.route("/confirm/forgot/<key>", methods=["POST","GET"])
def confirm_forgot(key):
	tmp_users = mongo.db.tmp_users
	tmp_user = tmp_users.find_one({"key": key, "type":"forgot"})
	
	if request.method == "GET":
		if tmp_user:
				return render_template("auth/forgot.html",
					user=tmp_user
				)
	elif tmp_user:
		password = bcrypt.hashpw(request.form["password"].encode("utf-8"), bcrypt.gensalt())
			
		mongo.db.users.find_one_and_update(
			{"email": tmp_user["email"]},
			{"$set": {
				"password": password
			}}
		)
		tmp_users.delete_many({'email': tmp_user["email"]})
		return redirect(url_for("login"))
	
	return render_template("message.html", title="Couldn't change password", body="Try again")

@app.route("/admin")
def admin():
	return redirect("https://replit.com/@shibanet/shibanet")