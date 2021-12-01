from flask import render_template, url_for, session, redirect, request
import os, logging, datetime, flask_pymongo
from utils.mongoutils import mongo, getparent
from utils.flaskutils import app
from utils.authutils import login_required
from utils import imgur, utils, notifs
from utils import shortlinks

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
@login_required
def submit():
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
			
			content = request.form["body"]
			
		elif request.args["type"] == "image":
			f = request.files['image']

			if request.form["title"] == "" or f.filename == "":
				return render_template("post/submit.html", error="All fields must be filled")
			
			imgur_url = None
			if f.filename:
				f.save("tmp/"+f.filename)
				imgur_url = imgur.upload(f"tmp/{f.filename}", request.form['title'])
				os.remove("tmp/"+f.filename)
			
			if not imgur_url:
				imgur_url = ""

			content = f"![{request.form['title']}]({imgur_url})"
		else:
			return render_template("post/submit.html", notifs=user_notifs, error="Error creating post of that type, if this message appears then you broke the website")
		
		posts.insert_one({
			"_id": post_id,
			"title": request.form["title"],
			"body": content,
			"author": session["username"],
			"timestamp": datetime.datetime.now(),
			"comments": [],
			"type": request.args["type"]
		})
		
		return redirect(url_for("view_post", post_id=post_id))
	return render_template("post/submit.html", error="Something went wrong :(")

@app.route("/post/<post_id>", methods=["GET"])
def view_post(post_id):
	post = mongo.db.posts.find_one({"_id": post_id.lower()})

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

	comments = utils.getcomments(post["comments"])

	return render_template("post/view.html", post=post, authorpfp=authorpfp, comments=comments, notifs=user_notifs)

@app.route("/post/<post_id>/edit", methods=["POST","GET"])
@login_required
def edit_post(post_id):
	user_notifs = notifs.get_notifs(session["username"])

	post = mongo.db.posts.find_one({"_id": post_id})

	if not post:
		return render_template("message.html",title="404",body="Coudn't find what you were looking for!", notifs=user_notifs), 404

	if post["author"] != session["username"]:
		return render_template("message.html",title="Cannot edit",body="You don't have permissions to edit that!", notifs=user_notifs), 403

	if post["type"] == "image":
		return render_template("message.html", title="Cannot edit",body="You cannot edit images :/", notifs=user_notifs), 403

	if request.method == "GET":
		return render_template("post/submit.html", ex_post=post, notifs=user_notifs)
	
	if request.form["title"] == "" or request.form["body"] == "":
		return render_template("post/submit.html", error="All fields must be filled", ex_post=post, notifs=user_notifs)

	mongo.db.posts.find_one_and_update(
		{'_id': post_id},
		{'$set': {
			'title': request.form["title"],
			"body": request.form["body"]
			}
		}
	)

	return redirect(url_for("view_post", post_id=post_id))

@app.route("/post/<post_id>/delete")
@login_required
def delete_post(post_id):
	user_notifs = notifs.get_notifs(session["username"])
	
	post = mongo.db.posts.find_one({"_id": post_id})

	if not post:
		return render_template("message.html",title="404",body="Coudn't find what you were looking for!", notifs=user_notifs), 404

	if post["author"] == session["username"]:
		mongo.db.posts.delete_one({"_id": post_id})
	else:
		return render_template("message.html",title="Cannot delete",body="You can't delete that!", notifs=user_notifs), 403
	
	return redirect(url_for("view_user",username=post["author"]))

@app.route("/post/<post_id>/comment", methods=["POST","GET"])
@login_required
def comment(post_id):
	user_notifs = notifs.get_notifs(session["username"])

	post = mongo.db.posts.find_one({"_id": post_id})

	if not post:
		return render_template("message.html",title="404",body="Coudn't find what you were looking for!", notifs=user_notifs), 404

	if request.method == "GET":
		return render_template("post/cmt_submit.html", prnt=post, notifs=user_notifs)
	
	if request.form["body"] == "":
		return render_template("post/cmt_submit.html",
			error="All fields must be filled",
			prnt=post,
			notifs=user_notifs
		)
	
	comments = mongo.db.comments
	cmt_id = utils.generate_id(3, comments)
	
	comments.insert_one({
		"_id": cmt_id,
		"body": request.form["body"],
		"author": session["username"],
		"children": [],
		"parent": {
			"type": "post",
			"id": post_id
		}
	})
	mongo.db.posts.find_one_and_update(
		{ "_id": post_id }, 
		{"$push": {"comments": cmt_id}}
	)
	if session["username"] != post["author"]:
		notifs.call(
			post["author"],
			f"{session['username']} commented on your post!",
			request.form["body"],
			url_for("view_post", post_id=post_id)
		)
	return redirect(url_for("view_post", post_id=post_id))

@app.route("/post/<post_id>/comment/<parent_cmt_id>", methods=["POST","GET"])
@login_required
def subcomment(post_id, parent_cmt_id):
	user_notifs = notifs.get_notifs(session["username"])

	parent = mongo.db.comments.find_one({"_id": parent_cmt_id})

	if not parent or parent["author"] == "<deleted>":
		return render_template("message.html",title="404",body="Coudn't find what you were looking for!", notifs=user_notifs), 404

	if request.method == "GET":
		return render_template("post/cmt_submit.html", prnt=parent, pst_id=post_id, notifs=user_notifs)
	
	if request.form["body"] == "":
		return render_template("post/cmt_submit.html", error="All fields must be filled", prnt=parent, notifs=user_notifs)
	
	comments = mongo.db.comments
	cmt_id = utils.generate_id(3, comments)
	
	comments.insert_one({
		"_id": cmt_id,
		"body": request.form["body"],
		"author": session["username"],
		"children": [],
		"parent": {
			"type": "comment",
			"id": parent_cmt_id
		},
		"timestamp": datetime.datetime.now()
	})
	mongo.db.comments.find_one_and_update(
		{"_id": parent_cmt_id}, 
		{"$push": {"children": cmt_id}}
	)
	if session["username"] != parent["author"]:
		notifs.call(
			parent["author"],
			f"{session['username']} replied to your comment!",
			request.form["body"],
			url_for("view_post", post_id=post_id)
		)
	return redirect(url_for("view_post", post_id=post_id))

@app.route("/comment/<cmt_id>/edit", methods=["POST","GET"])
@login_required
def edit_comment(cmt_id):
	user_notifs = notifs.get_notifs(session["username"])

	comment = mongo.db.comments.find_one({"_id": cmt_id})

	if not comment:
		return render_template("message.html",title="404",body="Coudn't find what you were looking for!", notifs=user_notifs), 404

	if comment["author"] != session["username"]:
		return render_template("message.html",title="Cannot edit",body="You don't have permissions to edit that!", notifs=user_notifs), 403
	
	if request.method == "GET":
		return render_template("post/cmt_submit.html", ex_cmt=comment, notifs=user_notifs)
	
	if request.form["body"] == "":
		return render_template("post/cmt_submit.html", error="All fields must be filled", ex_cmt=comment, notifs=user_notifs)

	mongo.db.comments.find_one_and_update(
		{'_id': cmt_id},
		{'$set': {
			"body": request.form["body"]
			}
		}
	)

	return redirect(url_for("view_post", post_id=getparent(cmt_id)["_id"]))

@app.route("/comment/<cmt_id>/delete")
@login_required
def delete_comment(cmt_id):
	user_notifs = notifs.get_notifs(session["username"])
	
	comment = mongo.db.comments.find_one({"_id": cmt_id})

	if not comment:
		return render_template("message.html",title="404",body="Coudn't find what you were looking for!", notifs=user_notifs), 404

	if comment["author"] == session["username"]:
		mongo.db.comments.find_one_and_update(
			{'_id': cmt_id},
			{'$set': {
				"body": "<deleted>",
				"author": "<deleted>"
				}
			}
		)
	else:
		return render_template("message.html",title="Cannot delete",body="You can't delete that!", notifs=user_notifs), 403
	
	return redirect(url_for("view_post",post_id=getparent(cmt_id)["_id"]))

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
	
	if "follow" in request.args and session["username"] != username:
		if following:
			mongo.db.users.find_one_and_update(
				{ "name": session["username"] }, 
				{"$pull": {"following": username}}
			)
		else:
			notifs.call(username, f"{session['username']} started following you!", f"If you haven't already, [follow them back!]({url_for('view_user',username=session['username'])})")
			
			mongo.db.users.find_one_and_update(
				{ "name": session["username"] }, 
				{"$push": {"following": username}}
			)
		
		return redirect(url_for("view_user", username=username))

	user_posts = mongo.db.posts.find({"author":user["name"]}).sort('timestamp', flask_pymongo.DESCENDING)

	user_comments = mongo.db.comments.find({"author":user["name"]}).sort('timestamp', flask_pymongo.DESCENDING)

	return render_template(
		"user/view.html",
		user = user,
		user_posts = user_posts,
		user_comments = user_comments,
		following = following,
		friends = friends,
		notifs = user_notifs
	)

@app.route("/settings", methods=["POST","GET"])
@login_required
def user_settings():
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
@login_required
def mark_all_read():
	notifs.mark_read_all(session["username"])
	return "success"

@app.route("/notification")
@login_required
def view_notif():
	if not "notif" in request.args:
		return redirect(url_for("index"))

	notif = notifs.mark_read(session["username"], request.args["notif"])

	user_notifs = notifs.get_notifs(session["username"])

	if "link" in notif:
		if notif["link"]:
			return redirect(notif["link"])

	return render_template("notif/view.html",notif=notif, notifs=user_notifs)

app.run(host='0.0.0.0', port=8080, debug=True)