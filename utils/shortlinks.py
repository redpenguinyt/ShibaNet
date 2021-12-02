from .flaskutils import app
from .mongoutils import getparent
from flask import redirect, url_for, render_template

@app.route("/u/<username>")
def view_user_short(username):
	return redirect(url_for("view_user",username=username))

@app.route("/<post_id>")
def view_post_short(post_id):
	return redirect(url_for("view_post",post_id=post_id))

@app.route("/comment/<cmt_id>")
def view_comment(cmt_id):
	parent = getparent(cmt_id)
	if not parent:
		return render_template("message.html", title="Post not found",body="It may have been deleted")
	return redirect(url_for("view_post", post_id=parent["_id"]))