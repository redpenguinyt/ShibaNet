from flask import Flask, render_template, session, redirect, url_for
from flask_misaka import Misaka
import os

app = Flask('ShibaNet')
app.config["MONGO_URI"] = os.environ["MONGO_URI"]
app.secret_key = os.environ["secret_key"]

Misaka(app)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('message.html',title="404",body="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('message.html',title="Server error",body="The website broke :("), 500

@app.errorhandler(403)
def forbidden(e):
    return render_template('message.html',title="Forbidden",body="You can't do that"), 403

@app.template_filter()
def pretty_time(time_delta):
	result = time_delta.strftime("%A %-d{0} %B %Y at %H:%M")
	day_suffix = "th"


	return result.format(day_suffix)

@app.route("/test")
def test():
	if not "username" in session:
		return redirect(url_for("login"))
	elif session["username"] != "RedPenguin":
		return redirect(url_for("index"))
	
	# Test code goes here
	# notifs.call_all("Welcome to ShibaNet!", "We hope you enjoy using the app :)")

	return "Done"