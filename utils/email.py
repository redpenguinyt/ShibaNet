import yagmail, os

yag = yagmail.SMTP(os.environ["email"], os.environ["email_key"])
contents = """
<div style="padding-left: 15px;padding-top: 15px;">
	<div class="centercontainer"><div class="center">
		<h1 style="text-align: center;">{0}</h1>
		<h2 style="text-align: center;">
			<a href="{1}">Click here to {0}</a>
		</h2>
	</div></div>
</div>
</body>
"""

def confirmemail(user, key):
	try:
		link = f"https://shibanet.repl.co/confirm/new?email={user['email']}&key={key}"

		yag.send(user["email"], "Confirm email - ShibaNet", contents.format("Confirm your email",link))
	except:
		return "error"

def iforgor(email, key):
	try:
		link = f"https://shibanet.repl.co/confirm/forgot?email={email}&key={key}"

		yag.send(email, "Forgot password - ShibaNet", contents.format("Forgot password",link))
	except:
		return "error"