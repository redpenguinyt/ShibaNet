import requests, base64, os

client_id = os.environ["imgur_id"]
headers = {'Authorization': 'Client-ID ' + client_id}

def upload(filename, title="untitled"):
	image = open(filename, "rb").read()
	b64_image = base64.standard_b64encode(image)
	data = {'image': b64_image, 'title': title}

	response = requests.post(
		url="https://api.imgur.com/3/upload.json", 
		data=data,
		headers=headers
	)

	parse = response.json()
	if not "link" in parse["data"]:
		return None
	return parse['data']['link']