from .flaskutils import app
from .mongoutils import getparent
from flask import redirect, url_for

@app.route("/u/<username>")
def view_user_short(username):
	return redirect(url_for("view_user",username=username))

@app.route("/<post_id>")
def view_post_short(post_id):
	return redirect(url_for("view_post",post_id=post_id))

@app.route("/comment/<cmt_id>")
def view_comment(cmt_id):
	return redirect(url_for("view_post", post_id=getparent(cmt_id)["_id"]))