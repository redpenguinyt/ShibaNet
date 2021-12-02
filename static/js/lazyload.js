var scroller = document.querySelector("#scroller");
var template = document.querySelector('#post_template');
var sentinel = document.querySelector('#sentinel');

// Set a counter to count the items loaded
var counter = 0;

// Function to request new items and render to the dom
function loadItems() {
  let url = `/load?c=${counter}&sort=${sortBy}`
  
  if (user) {
	url += `&user=${user}`  
  };
  // Use fetch to request data and pass the counter value in the QS
  fetch( url ).then((response) => {
    // Convert the response data to JSON
    response.json().then((data) => {
	  console.log(data);
      // If empty JSON, exit the function
      if (!data.posts.length) {

        // Replace the spinner with "No more posts"
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
        template_clone.querySelector("#body").innerHTML = post.body;
		template_clone.querySelector("#body").classList.add(`${post.type}_post`);

		if (data.username) {
			template_clone.querySelector("#ratio").innerHTML = `${post.ratio}%`;
			template_clone.querySelector("#comment").href = `/post/${post._id}/comment`;
			template_clone.querySelector("#edit").href = `/post/${post._id}/edit`;
			template_clone.querySelector("#delete").href = `/post/${post._id}/edit`;

			if (data.username != post.author) { 
				template_clone.querySelector("#modOptions").innerHTML = ""; 
			};
		};
		
        // Append template to dom
        scroller.appendChild(template_clone);

        // Increment the counter
        counter += 1;

      }
    })
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
intersectionObserver.observe(sentinel);