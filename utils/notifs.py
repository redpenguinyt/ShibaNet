from .authutils import mongo
from .utils import generate_id
import datetime

def get_notif(user, notif_id):
	all_notifs = mongo.db.notifications.find_one(
		{"user": user}
	)["notifs"]

	return next(item for item in all_notifs if item["_id"] == notif_id)

def mark_read(user, notif_id):
	mongo.db.notifications.find_one_and_update({
    	"user" : user,
    	"notifs._id" : notif_id
    },
    {
    	"$set" :
    	{
    		"notifs.$.read": True
    	}
    })

	return get_notif(user, notif_id)

def mark_read_all(user):
	for notif in mongo.db.notifications.find_one({"user":user})["notifs"]:
		mark_read(user, notif["_id"])

def call(user, title, body=None):
	if not body:
		body = title
	
	notif_id = generate_id(2)

	mongo.db.notifications.find_one_and_update(
		{ "user": user }, 
		{"$push": {"notifs": {
			"_id": notif_id,
			"title": title,
			"body": body,
			"timestamp": datetime.datetime.now(),
			"read": False
		}}}
	)

	return get_notif(user, notif_id)

def call_all(title, body=None):
	if not body:
		body = title
	
	for user in mongo.db.users.find():
		call(user["name"], title, body)

def get_notifs(username):
	user = mongo.db.notifications.find_one({"user": username})
	
	unread = list(filter(lambda d: d['read'] in [False], user["notifs"]))

	sorted_notifs = sorted(unread, key=lambda d: d['timestamp'], reverse=True)

	return sorted_notifs

def clean_notifs():
	pass