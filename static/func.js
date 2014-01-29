$(document).ready(function() {
	options = {
		valueNames: [ 'id', 'author', 'title', 'source_repo', 'source_branch', 'dest_branch', 'reviewer' ]
	};
	var list = new List('pull-requests', options);

	$('#search-id').keyup(function() {
		var id = $('#search-id').val();
		list.filter(function(item) {
			return item.values().id.indexOf(id) >= 0;
		});
		return false;
	});

	$('#search-author').keyup(function() {
		var author = $('#search-author').val().toLowerCase();
		list.filter(function(item) {
			return item.values().author.toLowerCase().indexOf(author) >= 0;
		});
		return false;
	});

	$('#search-title').keyup(function() {
		var title = $('#search-title').val().toLowerCase();
		list.filter(function(item) {
			return item.values().title.toLowerCase().indexOf(title) >= 0;
		});
		return false;
	});

	$('#search-source_repo').keyup(function() {
		var source_repo = $('#search-source_repo').val().toLowerCase();
		list.filter(function(item) {
			return item.values().source_repo.toLowerCase().indexOf(source_repo) >= 0;
		});
		return false;
	});

	$('#search-source_branch').keyup(function() {
		var source_branch = $('#search-source_branch').val().toLowerCase();
		list.filter(function(item) {
			return item.values().source_branch.toLowerCase().indexOf(source_branch) >= 0;
		});
		return false;
	});

	$('#search-dest_branch').keyup(function() {
		var dest_branch = $('#search-dest_branch').val().toLowerCase();
		list.filter(function(item) {
			return item.values().dest_branch.toLowerCase().indexOf(dest_branch) >= 0;
		});
		return false;
	});

	$('#search-reviewer').keyup(function() {
		var reviewer = $('#search-reviewer').val().toLowerCase();
		list.filter(function(item) {
			return item.values().reviewer.toLowerCase().indexOf(reviewer) >= 0;
		});
		return false;
	});
})

function branchfilter(branch) {
	$('#search-dest_branch').val( branch );
	$('#search-dest_branch').keyup();
}
