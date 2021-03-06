from flask import url_for, session, redirect, request, make_response, jsonify
import os, flask_pymongo
from datetime import datetime
from utils.flask import app, getratio, render_template, mongo
from utils.authutils import login_required
from utils import imgur, utils, notifs
from utils import shortlinks

# Main

@app.route("/")
def index():
	if "sort" in request.args:
		if request.args["sort"] == "All" or not "username" in session:
			return render_template("home.html")
		elif request.args["sort"] == "Following":
			return render_template("home.html")
			
	return redirect(url_for("index", sort="Following"))

@app.route("/search")
def search():
	query = request.args["q"] if "q" in request.args else ""
	found_users = mongo.db.users.find({"$or": [{"name": {"$regex": query, "$options": 'i'}},{"bio": {"$regex": query, "$options": 'i'}}]}, projection = {"password": False,"_id": False, "email": False})

	found_categories = mongo.db.categories.find({"$text": {"$search": query}})
	
	return render_template(
		"search.html",
		users = found_users,
		categories = found_categories
	)

# Posts

@app.route("/submit", methods=["POST", "GET"])
@login_required
def submit():
	mins_since_post = utils.isCoolDown(session["username"], mongo.db.posts)
	if mins_since_post > 0:
		return render_template(
			"post/submit.html",
			error=f"You can only make a post every 5 minutes, please wait {5 - mins_since_post} minutes first"
		), 403

	if request.method == "GET":
		return render_template("post/submit.html")
	
	if "type" in request.args:
		posts = mongo.db.posts
		post_id = utils.generate_id(3, posts)

		if request.args["type"] == "text":
			if request.form["title"] == "" or request.form["body"] == "":
				return render_template("post/submit.html", error="All fields must be filled")
			
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
		elif request.args["type"] == "link":
			content = f"[link-post]({request.form['link']})"
		else:
			return render_template("post/submit.html", error="Error creating post of that type, if this message appears then you broke the website")
		
		posts.insert_one({
			"_id": post_id,
			"title": request.form["title"],
			"body": content,
			"author": session["username"],
			"timestamp": datetime.now(),
			"comments": [],
			"type": request.args["type"],
			"score": {session["username"]: 1},
			"category": ""
		})
		mentions = []
		for word in f"{request.form['title']} {content}".split(" "):
			if word.startswith("@"):
				username = word.replace("@","")
				if mongo.db.users.find_one({"name": username}) and username not in mentions:
						mentions.append(username)
		for username in mentions:
			notifs.call(username, f"[{session['username']}](/u/{session['username']}) mentioned you in a post!", request.form["title"], url_for("view_post", post_id=post_id))
		
		return redirect(url_for("view_post", post_id=post_id))

	return render_template("post/submit.html", error="Something went wrong :(")

@app.route("/post/<post_id>", methods=["GET"])
def view_post(post_id):
	post = mongo.db.posts.find_one({"_id": post_id.lower()})
	
	if not post:
		return render_template("message.html",title="404",body="Coudn't find what you were looking for!"), 404

	comments = utils.getcomments(post["comments"])

	return render_template("post/view.html", post=post, comments=comments)

@app.route("/post/<post_id>/edit", methods=["POST","GET"])
@login_required
def edit_post(post_id):

	post = mongo.db.posts.find_one({"_id": post_id})

	if not post:
		return render_template("message.html",title="404",body="Coudn't find what you were looking for!"), 404

	if post["author"] != session["username"]:
		return render_template("message.html",title="Cannot edit",body="You don't have permissions to edit that!"), 403

	if post["type"] == "image":
		return render_template("message.html", title="Cannot edit",body="You cannot edit images :/"), 403

	if request.method == "GET":
		return render_template("post/submit.html", ex_post=post)
	
	if request.form["title"] == "" or request.form["body"] == "":
		return render_template("post/submit.html", error="All fields must be filled", ex_post=post)

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
	
	post = mongo.db.posts.find_one({"_id": post_id})

	if not post:
		return render_template("message.html",title="404",body="Coudn't find what you were looking for!"), 404

	if post["author"] == session["username"]:
		mongo.db.posts.delete_one({"_id": post_id})
	else:
		return render_template("message.html",title="Cannot delete",body="You can't delete that!"), 403
	
	return redirect(url_for("view_user",username=post["author"]))

@app.route("/post/<post_id>/comment", methods=["POST","GET"])
@login_required
def comment(post_id):
	post = mongo.db.posts.find_one({"_id": post_id})

	if not post:
		return render_template("message.html",title="404",body="Coudn't find what you were looking for!"), 404

	if request.method == "GET":
		return render_template("post/cmt_submit.html", prnt=post)
	
	if request.form["body"] == "":
		return render_template("post/cmt_submit.html",
			error="All fields must be filled",
			prnt=post
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
		},
		"timestamp": datetime.now()
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
	mentions = []
	for word in request.form['body'].split(" "):
		if word.startswith("@"):
			username = word.replace("@","")
			if mongo.db.users.find_one({"name": username}) and username not in mentions:
					mentions.append(username)
	for username in mentions:
		notifs.call(username, f"[{session['username']}](/u/{session['username']}) mentioned you in a comment!", request.form["body"], url_for("view_post", post_id=post_id))
	
	return redirect(url_for("view_post", post_id=post_id))

@app.route("/post/<post_id>/comment/<parent_cmt_id>", methods=["POST","GET"])
@login_required
def subcomment(post_id, parent_cmt_id):
	parent = mongo.db.comments.find_one({"_id": parent_cmt_id})

	if not parent or parent["author"] == "<deleted>":
		return render_template("message.html",title="404",body="Coudn't find what you were looking for!"), 404

	if request.method == "GET":
		return render_template("post/cmt_submit.html", prnt=parent, pst_id=post_id)
	
	if request.form["body"] == "":
		return render_template("post/cmt_submit.html", error="All fields must be filled", prnt=parent)
	
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
		"timestamp": datetime.now()
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
	mentions = []
	for word in request.form['body'].split(" "):
		if word.startswith("@"):
			username = word.replace("@","")
			if mongo.db.users.find_one({"name": username}) and username not in mentions:
					mentions.append(username)
	for username in mentions:
		notifs.call(username, f"[{session['username']}](/u/{session['username']}) mentioned you in a comment!", request.form["body"], url_for("view_post", post_id=post_id))
		
	return redirect(url_for("view_post", post_id=post_id))

@app.route("/comment/<cmt_id>/edit", methods=["POST","GET"])
@login_required
def edit_comment(cmt_id):
	comment = mongo.db.comments.find_one({"_id": cmt_id})

	if not comment:
		return render_template("message.html",title="404",body="Coudn't find what you were looking for!"), 404

	if comment["author"] != session["username"]:
		return render_template("message.html",title="Cannot edit",body="You don't have permissions to edit that!"), 403
	
	if request.method == "GET":
		return render_template("post/cmt_submit.html", ex_cmt=comment)
	
	if request.form["body"] == "":
		return render_template("post/cmt_submit.html", error="All fields must be filled", ex_cmt=comment)

	mongo.db.comments.find_one_and_update(
		{'_id': cmt_id},
		{'$set': {
			"body": request.form["body"]
			}
		}
	)

	return redirect(url_for("view_post", post_id=utils.getparent(cmt_id)["_id"]))

@app.route("/comment/<cmt_id>/delete")
@login_required
def delete_comment(cmt_id):
	comment = mongo.db.comments.find_one({"_id": cmt_id})

	if not comment:
		return render_template("message.html",title="404",body="Coudn't find what you were looking for!"), 404

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
		return render_template("message.html",title="Cannot delete",body="You can't delete that!"), 403
	
	return redirect(url_for("view_post",post_id=utils.getparent(cmt_id)["_id"]))

@app.route('/<post_id>/like')
@login_required
def like(post_id):
	username = session["username"]
	score = mongo.db.posts.find_one({"_id": post_id})["score"]

	if username in score and score[username] == 1:
		mongo.db.posts.find_one_and_update(
			{ "_id": post_id }, 
			{"$unset": {f"score.{username}": 1}}
		)
	else:
		mongo.db.posts.find_one_and_update(
				{ "_id": post_id },
				{"$set": {f"score.{username}": 1}}
			)
	res = getratio(mongo.db.posts.find_one({"_id": post_id})["score"])
	return make_response(jsonify(res), 200)

@app.route('/<post_id>/dislike')
@login_required
def dislike(post_id):
	username = session["username"]
	score = mongo.db.posts.find_one({"_id": post_id})["score"]

	if username in score and score[username] == -1:
		mongo.db.posts.find_one_and_update(
			{ "_id": post_id }, 
			{"$unset": {f"score.{username}": -1}}
		)
	else:
		mongo.db.posts.find_one_and_update(
				{ "_id": post_id },
				{"$set": {f"score.{username}": -1}}
			)
	res = getratio(mongo.db.posts.find_one({"_id": post_id})["score"])
	return make_response(jsonify(res), 200)

# Categories/Communities

@app.route("/c/<category>")
def view_category(category):
	category = mongo.db.categories.find_one({"_name": category})
	return render_template("category/view.html", category=category)

# User

@app.route("/user/<username>", methods=["POST","GET"])
def view_user(username):
	if "username" in session:
		if username == "me":
			return redirect(url_for("view_user", username=session["username"]))

	users = mongo.db.users
	user = users.find_one({"name": username}, projection={"password": False,"_id": False, "email": False})
	if not user:
		return render_template("message.html",title="404",body="That user doesn't exist"), 404

	following = False
	friends = False

	if "username" in session:
		following = username in users.find_one({"name": session["username"]})["following"]

		friends = following and session["username"] in users.find_one({"name": username})["following"]
	
	if "follow" in request.args: 
		if "username" in session:
			if session["username"] != username:
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
		else:
			return redirect(url_for("login", back="view_user"))

	user_comments = mongo.db.comments.find({"author":user["name"]}).sort('timestamp', flask_pymongo.DESCENDING)

	return render_template(
		"user/view.html",
		user = user,
		user_comments = user_comments,
		following = following,
		friends = friends
	)

@app.route("/settings", methods=["POST","GET"])
@login_required
def user_settings():
	user = mongo.db.users.find_one({"name": session["username"]})

	if request.method == "GET":
		return render_template("user/settings.html", user=user)
	
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
	return "success", 200

@app.route("/notification")
@login_required
def view_notif():
	if not "notif" in request.args:
		return redirect(url_for("index"))

	notif = notifs.mark_read(session["username"], request.args["notif"])

	if "link" in notif:
		if notif["link"]:
			return redirect(notif["link"])

	return render_template("notif/view.html",notif=notif)

# Help

@app.route("/help",methods=["POST","GET"])
@login_required
def help():
	if request.method == "GET":
		return render_template("help.html")

	mongo.db.feedback.insert_one({
		"title": request.form["title"],
		"body": request.form["body"],
		"author": session["username"],
		"timestamp": datetime.now(),
		"approved": False
	})
	notifs.call("RedPenguin", f"{session['username']} needs help!", request.form["body"])

	return render_template("message.html", title="Message recieved")

app.run(host='0.0.0.0', port=8080, debug=True)