from flask import render_template, url_for, session, redirect, request
import os, logging, datetime, flask_pymongo
from flask_misaka import Misaka
from utils.authutils import app, mongo
from utils.utils import generate_id

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
Misaka(app)

@app.route("/")
def index():
	if not "username" in session:
		return redirect(url_for("all"))

	following = mongo.db.users.find_one({"name": session["username"]})["following"]
	following.append(session["username"])

	recent_posts = mongo.db.posts.find(
		{"author": {"$in": following}}
	).sort('timestamp', flask_pymongo.DESCENDING)

	return render_template("home.html", posts=recent_posts)

@app.route("/all")
def all():
	all_posts = mongo.db.posts.find().sort('timestamp', flask_pymongo.DESCENDING)

	return render_template("home.html", posts=all_posts)

# Posts

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

@app.route("/post/<post_id>/delete")
def delete_post(post_id):
	if not "username" in session:
		return redirect(url_for("login"))
	
	post = mongo.db.posts.find_one({"_id": post_id})

	if not post:
		return render_template("message.html",title="404",body="Coudn't find what you were looking for!")

	if post["author"] == session["username"]:
		mongo.db.posts.delete_one({"_id": post_id})
	else:
		return render_template("message.html",title="Cannot delete",body="You can't delete that!")
	
	return redirect(url_for("view_user",username=post["author"]))

@app.route("/post/<post_id>/edit", methods=["POST","GET"])
def edit_post(post_id):
	if not "username" in session:
		return redirect(url_for("login"))

	post = mongo.db.posts.find_one({"_id": post_id})

	if post["author"] != session["username"]:
		return render_template("message.html",title="Cannot edit",body="You can't edit that!")

	if request.method == "GET":
		return render_template("post/submit.html", edit_post=post)
	
	mongo.db.posts.find_one_and_update(
		{'_id': post_id},
		{'$set': {
			'title': request.form["title"],
			"body": request.form["body"]
			}
		}
	)

	return redirect(url_for("view_post", post_id=post_id))

# User

@app.route("/user/<username>", methods=["POST","GET"])
def view_user(username):
	users = mongo.db.users
	user = users.find_one({"name": username})
	if not user:
		return render_template("message.html",title="404",body="Coudn't find what you were looking for!")

	following = False

	if "username" in session:
		following = username in users.find_one({"name": session["username"]})["following"]

	user_posts = mongo.db.posts.find({"author":user["name"]}).sort('timestamp', flask_pymongo.DESCENDING)

	return render_template(
		"user/view.html",
		user = user,
		user_posts = user_posts,
		following = following
	)

@app.route("/user/<username>/follow")
def follow(username):
	if not "username" in session:
		return redirect(url_for("login"))

	if username != session["username"]:
		following_users = mongo.db.users.find_one({"name": session["username"]})["following"]

		if username in following_users:
			mongo.db.users.find_one_and_update(
				{ "name": session["username"] }, 
				{"$pull": {"following": username}}
			)
		else:
			mongo.db.users.find_one_and_update(
				{ "name": session["username"] }, 
				{"$push": {"following": username}}
			)
	
	return redirect(url_for("view_user", username=username))

@app.route("/settings", methods=["POST","GET"])
def user_settings():
	if not "username" in session:
		return redirect(url_for("login"))
	
	user = mongo.db.users.find_one({"name": session["username"]})

	if request.method == "GET":
		return render_template("user/settings.html", user=user)
	
	mongo.db.users.find_one_and_update(
		{'name': session["username"]},
		{'$set': {
			"bio": request.form["bio"]
			}
		}
	)

	return redirect(url_for("view_user", username=session["username"]))

app.secret_key = os.environ["secret_key"]
app.run(host='0.0.0.0', port=8080, debug=True)