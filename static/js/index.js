$(function() {
	$('a#markread').bind('click', function() {
		$.getJSON('/mark_all_read',
			function(data) {}
		);
		this.innerHTML = "Success!";
		$(this).addClass('disabled btn-success')
			.removeClass('btn-primary');
		$("#all_notifs").empty();
		$("#notif_badge").empty();
		return false;
	});
});

$(function() {
	$('a#like').bind('click', function() {
		$.getJSON('/like',
			function(data) {}
		);
		this.innerHTML = "Success!";
		$(this).addClass('disabled');
		$("#all_notifs").empty();
		return false;
	});
});

