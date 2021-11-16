from flask import render_template, url_for, session, redirect, request
import os, logging, datetime, flask_pymongo
from utils.authutils import app, mongo
from utils.utils import generate_id

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# The basic website, includes login/logout, shows username on login

@app.route("/")
def index():
	recent_posts = mongo.db.posts.find().sort('timestamp', flask_pymongo.DESCENDING)

	return render_template("home.html", posts=recent_posts)

@app.route("/submit", methods=["POST","GET"])
def submit():
	if not "username" in session:
		return redirect(url_for("login"))
	
	if request.method == "GET":
		return render_template("post/submit.html")
	
	if request.form["title"] == "" or request.form["body"] == "":
		return render_template("post/submit.html", error="All fields must be filled")

	posts = mongo.db.posts
	post_id = generate_id(3, posts)
	posts.insert_one({
		"_id": post_id,
		"title": request.form["title"],
		"body": request.form["body"],
		"author": session["username"],
		"timestamp": datetime.datetime.now()
	})
	return redirect(url_for("view_post", post_id=post_id))

@app.route("/post/<post_id>")
def view_post(post_id):
	post = mongo.db.posts.find_one({"_id": post_id})
	if not post:
		return render_template("message.html",title="404",body="Coudn't find what you were looking for!")
	
	clean_time = post["timestamp"].strftime("%A %-dth %B %Y at %H:%M")
	return render_template("post/view.html", post=post, timestamp=clean_time)

@app.route("/user/<username>")
def view_user(username):
	user = mongo.db.users.find_one({"name": username})
	if not user:
		return render_template("message.html",title="404",body="Coudn't find what you were looking for!")
	
	user_posts = mongo.db.posts.find({"author":user["name"]}).sort('timestamp', flask_pymongo.DESCENDING)

	return render_template(
		"user/view.html",
		username = user["name"],
		user_posts = user_posts
	)

app.secret_key = os.environ["secret_key"]
app.run(host='0.0.0.0', port=8080, debug=True)