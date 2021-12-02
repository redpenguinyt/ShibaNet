from flask import Flask, render_template, session, redirect, url_for, request, make_response, jsonify, escape
from flask_misaka import Misaka, markdown
from flask_pymongo import PyMongo, DESCENDING
import datetime, os

app = Flask('ShibaNet')
app.config["MONGO_URI"] = os.environ["MONGO_URI"]
app.secret_key = os.environ["secret_key"]

Misaka(app)
mongo = PyMongo(app)

def truncate(data, amount):
	return (data[:amount] + '...') if len(data) > amount else data

@app.errorhandler(404)
def page_not_found(e):
    return render_template('message.html',title="404",body="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('message.html',title="Bruh",body="You broke the website >:("), 500

@app.errorhandler(403)
def forbidden(e):
    return render_template('message.html',title="Forbidden",body="You can't do that"), 403

@app.template_filter()
def getratio(score):
	ratio = 0
	for key, item in score.items():
		if int(item) > 0: ratio += 1
	
	return (ratio/len(score))*100 if len(score) > 0 else 100

@app.template_filter()
def pretty_time(time_delta):
	result = time_delta.strftime("%A %-d{0} %B %Y at %H:%M")
	
	prefix = {"1":"st","2":"nd","3":"rd","4":"","5":"","6":"","7":"","8":"","9":"","0":"",}

	day = time_delta.strftime("%-d")
	day_suffix = prefix[day[-1]]
	if not day_suffix: day_suffix = "th"

	return result.format(day_suffix)

@app.template_filter()
def is_mod(username):
	user = mongo.db.users.find_one({"author": username})
	if not user:
		return False
	return user["is_mod"]

@app.template_filter()
def getparenttitle(comment):
	if comment["parent"]["type"] == "post":
		post = mongo.db.posts.find_one({"_id": comment["parent"]["id"]})
		return post["title"]
	else:
		parent_cmt = mongo.db.comments.find_one({"_id": comment["parent"]["id"]})
		return parent_cmt["body"]

@app.route("/test")
def test():
	if not "username" in session:
		return redirect(url_for("login"))
	elif session["username"] != "RedPenguin":
		return redirect(url_for("index"))
	
	# Test code goes here
	# notifs.call_all("Welcome to ShibaNet!", "We hope you enjoy using the app :)")

	return "Done"

@app.route("/load")
def load():
	""" Route to return the posts """

	quantity = 5

	if "c" in request.args and "sort" in request.args:
		counter = int(request.args.get("c"))

		mongo_result = []

		if request.args["sort"] == "Following" and "username" in session:
			following = mongo.db.users.find_one({"name": session["username"]})["following"]
			following.append(session["username"])

			mongo_result = mongo.db.posts.find({"timestamp":{"$lte": datetime.datetime.now()}, "author": {"$in": following}}, skip=counter, limit=quantity).sort('timestamp', DESCENDING)
		elif request.args["sort"] == "User" and "user" in request.args:
			user = request.args["user"]

			mongo_result = mongo.db.posts.find({"author":user}, skip=counter, limit=quantity).sort('timestamp', DESCENDING)
		else: # sort by All
			mongo_result = mongo.db.posts.find({"timestamp":{"$lte": datetime.datetime.now()}}, skip=counter, limit=quantity).sort('timestamp', DESCENDING)

		posts = []

		for post in mongo_result:
			post["title"] = markdown(escape(post["title"]))
			post["ratio"] = getratio(post["score"])
			post["body"] = markdown(truncate(escape(post["body"]), 200))
			
			posts.append(post)

		username = session["username"] if "username" in session else ""
		res = {"username":username, "posts":posts}
	else:
		return redirect(url_for("load",c=0,sort="All"))

	return make_response(jsonify(res), 200)