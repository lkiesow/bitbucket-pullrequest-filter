current_filter = '';

filter = {};
keys = [ 'id', 'created_on', 'author', 'title', 'source_repo', 'source_branch', 'dest_branch', 'reviewer' ];

function filterTable() {
	for (var k in keys) {
		var v = keys[k];
		filter[v] = $('#search-' + v).val().toLowerCase();
	}
	filter['global'] = $('#search').val().toLowerCase();
	$('.list tr').each(function(i, row) {
		for (var k in keys) {
			var v = keys[k];
			if (!filter[v]) {
				$(row).show();
				continue;
			}
			var cell = $(row).find('td.' + v).text().toLowerCase();
			if (cell.indexOf(filter[v]) < 0) {
				$(row).hide();
				break;
			} else {
				$(row).show();
			}
		}
		if ($(row).text().toLowerCase().indexOf(filter['global']) < 0) {
			$(row).hide();
		}
	})
}

$(document).ready(function() {

		$('#search').change(filterTable);
		$('#search').keyup(filterTable);
	for (var k in keys) {
		var v = keys[k];
		$('#search-' + v).change(filterTable);
		$('#search-' + v).keyup(filterTable);
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

	filterTable();

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
	var current_filter = '';
	for (var k in filter) {
		if (filter[k]) {
			current_filter += '/' + k + '/' + filter[k].replace('/', '//');
		}
	}
	window.location.href = current_filter;
}
