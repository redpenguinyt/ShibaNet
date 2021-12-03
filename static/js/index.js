// Mark all read button
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