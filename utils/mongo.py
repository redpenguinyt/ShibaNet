from .flask import mongo

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