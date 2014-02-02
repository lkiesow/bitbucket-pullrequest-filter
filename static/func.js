$(document).ready(function() {
	options = {
		valueNames: [ 'id', 'author', 'title', 'source_repo', 'source_branch', 'dest_branch', 'reviewer' ]
	};
	var list = new List('pull-requests', options);

	for (var k in options['valueNames']) {
		var v = options['valueNames'][k];
		$('#search-' + v).keyup(function(e) {
			var v = e.target.id.replace(/^search-/, '');
			var s = $(e.target).val().toLowerCase();
			list.filter(function(item) {
				return item.values()[v].toLowerCase().indexOf(s) >= 0;
			});
			return false;
		});
	}
})

function branchfilter(branch) {
	$('#search-dest_branch').val( branch );
	$('#search-dest_branch').keyup();
}
