current_filter = '';
$(document).ready(function() {
	options = {
		valueNames: [ 'id', 'created_on', 'author', 'title', 'source_repo', 'source_branch', 'dest_branch', 'reviewer' ]
	};
	var list = new List('pull-requests', options);

	for (var k in options['valueNames']) {
		var v = options['valueNames'][k];
		$('#search-' + v).keyup(function(e) {
			var v = e.target.id.replace(/^search-/, '');
			var s = $(e.target).val().toLowerCase();
			current_filter = s ? v + '/' + s : '';
			list.filter(function(item) {
				return item.values()[v].toLowerCase().indexOf(s) >= 0;
			});
			return false;
		});
	}

	$('input').each(function() {
		$(this).parent().append('<a onclick="cleanup(this);" class=clean>×</a>');
	});

	$('.ellipsis').each(function() {
		$(this).click(function() {
			$('.ellipsis').hide();
			$('.hide').show();
		});
	});

})

function cleanup(e) {
	var inp = $(e).parent().find('input');
	inp.val('');
	inp.keyup();
}

function branchfilter(branch) {
	$('#search-dest_branch').val( branch );
	$('#search-dest_branch').keyup();
}

function bookmark() {
	window.location.href = "/" + current_filter;
}
