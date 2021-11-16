import yagmail, os

yag = yagmail.SMTP(os.environ["email"], os.environ["email_key"])
contents = """
<div style="padding-left: 15px;padding-top: 15px;">
	<div class="centercontainer"><div class="center">
		<h1 style="text-align: center;">Confirm your email</h1>
		<h2 style="text-align: center;">
			<a href="%s">Click here to confirm your email</a>
		</h2>
	</div></div>
</div>
</body>
"""

def confirmemail(user, key):
	link = f"https://shibanet.repl.co/confirm/{user['email']}/{key}"

	yag.send(user["email"], "Confirm your email - ShibaNet", contents % link)