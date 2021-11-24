$(function() {
	$('a#markread').bind('click', function() {
		$.getJSON('/mark_all_read',
			function(data) {}
		);
		return false;
	});
});

$(function() {
	$('a#like').bind('click', function(post_id) {
		$.getJSON("/post/{0}/like".format(post_id),
			function(data) {}
		);
		return false;
	});
});