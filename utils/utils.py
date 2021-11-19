import flask_pymongo, datetime, secrets

def generate_id(length, collection=None):
	new_id = secrets.token_hex(length)
	if collection:
		if collection.find_one({"_id":new_id}):
			new_id = generate_id(collection)
	return new_id

def format_time(time_del):
	return time_del.strftime("%A %-dth %B %Y at %H:%M")

def isCoolDown(username, posts):
	if posts.count_documents({"author": username}) >= 1:
		last_post = posts.find({"author": username}).sort('timestamp', flask_pymongo.DESCENDING)[0]
		time_since_last_post = datetime.datetime.now() - last_post["timestamp"]
		mins_since_post = (time_since_last_post.seconds//60)%60

		if mins_since_post > 5:
			return 0
		
		return mins_since_post
	return 0