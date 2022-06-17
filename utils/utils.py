import datetime, secrets
from .flask import mongo

def generate_id(length, collection=None, col_key="_id"):
	new_id = secrets.token_hex(length)
	if collection:
		if collection.find_one({col_key: new_id}):
			new_id = generate_id(length, collection, col_key)
	return new_id

def isCoolDown(username, posts):
	if posts.count_documents({"author": username}) >= 1:
		last_post = posts.find({"author": username}).sort('timestamp', -1)[0]
		time_since_last_post = datetime.datetime.now() - last_post["timestamp"]
		mins_since_post = (time_since_last_post.seconds//60)%60

		if mins_since_post > 5:
			return 0
		
		return mins_since_post
	return 0

def cursor_to_json(cursor):
	result = []

	for doc in cursor:
		result.append(doc)

	return result

def getcomments(comment_ids):
	result = mongo.db.comments.find({"_id": {"$in": comment_ids}})

	comments = cursor_to_json(result)

	for comment in comments:
		if comment["children"]:
			comment["children"] = getcomments(comment["children"])
	
	return comments

def like(post, username, likeType=1):
	if username in post["score"]:
		mongo.db.posts.find_one_and_update({"_id": post["_id"]},{"score":{"$unset":{username: likeType}}})
	else:
		mongo.db.posts.find_one_and_update({"_id": post["_id"]},{"score":{"$set":{username: likeType}}})

def getparent(cmt_id):
	comments = mongo.db.comments

	parent = {}

	while True:
		parent = comments.find_one({"_id":cmt_id})
		parent_type = parent["parent"]["type"]
		if parent_type == "post":
			break
		cmt_id = parent["parent"]["id"]
	
	post = mongo.db.posts.find_one({"_id": parent["parent"]["id"]})
	return post