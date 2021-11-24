from flask import render_template, url_for, session, redirect, request
import os, logging, datetime, flask_pymongo
from utils.mongoutils import mongo
from utils.flaskutils import app
from utils import imgur, utils, notifs
from utils import shortlinks, authutils

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Home

@app.route("/")
def index():
	user_notifs = []
	if "username" in session:
		user_notifs = notifs.get_notifs(session["username"])

	if "sort" in request.args:
		if request.args["sort"] == "All" or not "username" in session:
			all_posts = mongo.db.posts.find().sort('timestamp', flask_pymongo.DESCENDING)

			return render_template("home.html", posts=all_posts, notifs=user_notifs)
		elif request.args["sort"] == "Following":
			following = mongo.db.users.find_one({"name": session["username"]})["following"]
			following.append(session["username"])

			recent_posts = mongo.db.posts.find({"author": {"$in": following}}).sort('timestamp', flask_pymongo.DESCENDING)

			return render_template("home.html", posts=recent_posts, notifs=user_notifs)
			
	return redirect(url_for("index", sort="Following"))

# Posts

@app.route("/submit", methods=["POST", "GET"])
def submit():
	if not "username" in session:
		return redirect(url_for("login"))
	user_notifs = notifs.get_notifs(session["username"])

	mins_since_post = utils.isCoolDown(session["username"], mongo.db.posts)
	if mins_since_post > 0:
		return render_template(
			"post/submit.html",
			error=f"You can only make a post every 5 minutes, please wait {5 - mins_since_post} minutes first",
			notifs=user_notifs
		), 403

	if request.method == "GET":
		return render_template("post/submit.html", notifs=user_notifs)
	
	if "type" in request.args:
		posts = mongo.db.posts
		post_id = utils.generate_id(3, posts)

		if request.args["type"] == "text":
			if request.form["title"] == "" or request.form["body"] == "":
				return render_template("post/submit.html", error="All fields must be filled", notifs=user_notifs)
			
		elif request.args["type"] == "image":
			f = request.files['image']

			if request.form["title"] == "" or f.filename == "":
				return render_template("post/submit.html", error="All fields must be filled")
			
			imgur_url = None
			if f.filename:
				f.save("tmp/"+f.filename)
				imgur_url = imgur.upload(f"tmp/{f.filename}")
				os.remove("tmp/"+f.filename)
			
			if not imgur_url:
				imgur_url = ""

			content = f"![{request.form['title']}]({imgur_url})"
		
		posts.insert_one({
			"_id": post_id,
			"title": request.form["title"],
			"body": content,
			"author": session["username"],
			"timestamp": datetime.datetime.now(),
			"comments": [],
			"type": "image"
		})
		
		return redirect(url_for("view_post", post_id=post_id))
	return render_template("post/submit.html", error="Something went wrong :(")

@app.route("/post/<post_id>", methods=["GET"])
def view_post(post_id):
	post = mongo.db.posts.find_one({"_id": post_id})

	user_notifs = []
	if "username" in session:
		user_notifs = notifs.get_notifs(session["username"])
		if "like" in request.args:
			utils.like(post, session["username"])
	
	if not post:
		return render_template("message.html",title="404",body="Coudn't find what you were looking for!", notifs=user_notifs), 404

	authorpfp = mongo.db.users.find_one(
		{"name": post["author"]}
	)["pfp"]
	return render_template("post/view.html", post=post, authorpfp=authorpfp, notifs=user_notifs)

@app.route("/post/<post_id>/delete")
def delete_post(post_id):
	if not "username" in session:
		return redirect(url_for("login"))
	user_notifs = notifs.get_notifs(session["username"])
	
	post = mongo.db.posts.find_one({"_id": post_id})

	if not post:
		return render_template("message.html",title="404",body="Coudn't find what you were looking for!", notifs=user_notifs), 404

	if post["author"] == session["username"]:
		mongo.db.posts.delete_one({"_id": post_id})
	else:
		return render_template("message.html",title="Cannot delete",body="You can't delete that!", notifs=user_notifs), 403
	
	return redirect(url_for("view_user",username=post["author"]))

@app.route("/post/<post_id>/edit", methods=["POST","GET"])
def edit_post(post_id):
	if not "username" in session:
		return redirect(url_for("login"))
	user_notifs = notifs.get_notifs(session["username"])

	post = mongo.db.posts.find_one({"_id": post_id})

	if not post:
		return render_template("message.html",title="404",body="Coudn't find what you were looking for!", notifs=user_notifs), 404

	if post["author"] != session["username"]:
		return render_template("message.html",title="Cannot edit",body="You don't have permissions to edit that!", notifs=user_notifs), 403

	if post["type"] == "image":
		return render_template("message.html", title="Cannot edit",body="You cannot edit images :/", notifs=user_notifs), 403

	if request.method == "GET":
		return render_template("post/submit.html", edit_post=post, notifs=user_notifs)
	
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
	user_notifs = []
	if "username" in session:
		user_notifs = notifs.get_notifs(session["username"])

		if username == "me":
			return redirect(url_for("view_user", username=session["username"]))

	users = mongo.db.users
	user = users.find_one({"name": username})
	if not user:
		return render_template("message.html",title="404",body="That user doesn't exist", notifs=user_notifs), 404

	following = False
	friends = False

	if "username" in session:
		following = username in users.find_one({"name": session["username"]})["following"]

		friends = following and session["username"] in users.find_one({"name": username})["following"]
	
	if "follow" in request.args:
		if following:
			mongo.db.users.find_one_and_update(
				{ "name": session["username"] }, 
				{"$pull": {"following": username}}
			)
		else:
			notifs.call(username, f"{session['username']} started following you!", f"[{session['username']}]({url_for('view_user',username=session['username'])}) started following you! If you haven't already, [follow them back!]({url_for('view_user',username=session['username'])})")
			
			mongo.db.users.find_one_and_update(
				{ "name": session["username"] }, 
				{"$push": {"following": username}}
			)
		
		return redirect(url_for("view_user", username=username))

	user_posts = mongo.db.posts.find({"author":user["name"]}).sort('timestamp', flask_pymongo.DESCENDING)

	return render_template(
		"user/view.html",
		user = user,
		user_posts = user_posts,
		following = following,
		friends=friends,
		notifs=user_notifs
	)

@app.route("/settings", methods=["POST","GET"])
def user_settings():
	if not "username" in session:
		return redirect(url_for("login"))
	user_notifs = notifs.get_notifs(session["username"])
	
	user = mongo.db.users.find_one({"name": session["username"]})

	if request.method == "GET":
		return render_template("user/settings.html", user=user, notifs=user_notifs)
	
	# Pfp save

	f = request.files['pfp']

	imgur_url = None
	if f.filename:
		f.save("tmp/"+f.filename)
		imgur_url = imgur.upload(f"tmp/{f.filename}")
		os.remove("tmp/"+f.filename)
	
	if not imgur_url:
		imgur_url = user["pfp"]

	mongo.db.users.find_one_and_update(
		{'name': session["username"]},
		{'$set': {
			"pfp": imgur_url,
			"bio": request.form["bio"],
			"theme": request.form["themes"]
			}
		}
	)
	session["theme"] = request.form["themes"]

	return redirect(url_for("view_user", username=session["username"]))

# Notifications

@app.route('/mark_all_read')
def mark_all_read():
	if not "username" in session:
		return redirect(url_for("login"))
	
	notifs.mark_read_all(session["username"])
	return "success"

@app.route("/notification")
def view_notif():
	if not "username" in session:
		return redirect(url_for("login"))
	
	if not "notif" in request.args:
		return redirect(url_for("index"))

	notif = notifs.mark_read(session["username"], request.args["notif"])

	user_notifs = notifs.get_notifs(session["username"])

	timestamp = utils.format_time(notif["timestamp"])

	return render_template("notif/view.html",notif=notif, notifs=user_notifs, timestamp=timestamp)

app.run(host='0.0.0.0', port=8080, debug=True)