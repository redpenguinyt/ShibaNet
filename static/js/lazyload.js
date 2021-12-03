var scroller = document.querySelector("#scroller");
var template = document.querySelector('#post_template');
var sentinel = document.querySelector('#sentinel');

// Set a counter to count the items loaded
var counter = 0;

function ratioButtons() {
	$(function() {
		$('a#like').bind('click', function() {
			$.getJSON(`/${$(this).parent().attr('id')}/like`,
				function(data) {}
			);
			if (this.classList.contains("ratio-clicked")) {
				$(this).removeClass("ratio-clicked");
			} else {
				$(this).addClass("ratio-clicked");
				$(this).parent().children("a#dislike").removeClass("ratio-clicked");
			};
			return false;
		});
		$('a#dislike').bind('click', function() {
			$.getJSON(`/${$(this).parent().attr('id')}/dislike`,
				function(data) {}
			);
			if (this.classList.contains("ratio-clicked")) {
				$(this).removeClass("ratio-clicked");
			} else {
				$(this).addClass("ratio-clicked");
				$(this).parent().children("a#like").removeClass("ratio-clicked");
			};
			return false;
		});
	});
};
// Run for post view
ratioButtons();

// Function to request new items and render to the dom
function loadItems() {
	let url = `/load?c=${counter}&sort=${sortBy}`
	
	if (typeof user !== 'undefined') {
		url += `&user=${user}`  
	};
	if (typeof search !== 'undefined') {
		url += `&search=${search}`
	};
	// Use fetch to request data and pass the counter value in the QS
	fetch( url ).then((response) => {
		// Convert the response data to JSON
		response.json().then((data) => {
		console.log("Loading more posts");
		// If empty JSON, exit the function
		if (!data.posts.length) {
			sentinel.innerHTML = "No more posts";
			return;
		}

		// Iterate over the items in the response
		for (var i = 0; i < data.posts.length; i++) {

			// Clone the HTML template
			let template_clone = template.content.cloneNode(true);
			const post = data["posts"][i]

			// Query & update the template content
			template_clone.querySelector("#title").innerHTML = post.title;
			template_clone.querySelector("#title").href = `/${post._id}`;
			template_clone.querySelector("#author").innerHTML = post.author;
			template_clone.querySelector("#author").href = `/u/${post.author}`;
			template_clone.querySelector("#category").innerHTML = post.category;
			template_clone.querySelector("#category").href = `/c/${post.category}`;
			template_clone.querySelector("#body").innerHTML = post.body;
			template_clone.querySelector("#body").classList.add(`${post.type}_post`);

			if (data.username) {
				template_clone.querySelector("#postID").id = `${post._id}`;
				template_clone.querySelector("#ratio").innerHTML = `${post.ratio}%`;
				template_clone.querySelector("#comment").href = `/post/${post._id}/comment`;
				template_clone.querySelector("#edit").href = `/post/${post._id}/edit`;
				template_clone.querySelector("#delete").href = `/post/${post._id}/delete`;

				if (data.username != post.author) { 
					template_clone.querySelector("#modOptions").innerHTML = "";
				};
				if (!post.category) {
					template_clone.querySelector("#isCategory").innerHTML = "";
				};

				if (post.myRatio == 1) {
					template_clone.querySelector("#like").classList.add("ratio-clicked");
				} else if (post.myRatio == -1) {
					template_clone.querySelector("#dislike").classList.add("ratio-clicked");
				};
				
			};
			
			// Append template to dom
			scroller.appendChild(template_clone);

			// Increment the counter
			counter += 1;
		}
		});

		// Bind Like and dislike buttons
		$('a#like').unbind("click");
		$('a#dislike').unbind("click");
		ratioButtons();
	})
};

// Create a new IntersectionObserver instance
var intersectionObserver = new IntersectionObserver(entries => {
	if (entries[0].intersectionRatio <= 0) {
		return;
	}

	loadItems();
});

// Instruct the IntersectionObserver to watch the sentinel
if (sentinel) {
	intersectionObserver.observe(sentinel);
};