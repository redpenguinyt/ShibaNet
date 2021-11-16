import secrets

def generate_id(length, collection=None):
	new_id = secrets.token_hex(length)
	if collection:
		if collection.find_one({"_id":new_id}):
			new_id = generate_id(collection)
	return new_id