current_filter = '';

filter = {};
keys = [ 'id', 'created_on', 'author', 'title', 'source_repo', 'source_branch', 'dest_branch', 'reviewer' ];

function filterTable() {
	// prepare filter settings
	for (var k in keys) {
		var v = keys[k];
		filter[v] = $('#search-' + v).val().toLowerCase();
	}
	filter['global'] = $('#search').val().toLowerCase();

	// filter table
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

		$('#pr-count').html($('.list tr:visible').length);
	})
}

$(document).ready(function() {

	// Add events to input fields
	$('input').change(filterTable).keyup(filterTable);

	// Add clean input field icons
	$('input').parent().append('<a onclick="cleanup(this);" class=clean>×</a>');

	// Expand hidden elements
	$('.ellipsis').click(function() {
		$('.ellipsis').hide();
		$('.hide').show();
	});

	// Do an initial filtering
	filterTable();

	// Add sorting functionality
	$('th.sort').click(function() {
		var field = this.getAttribute('data-sort');
		var order = this.getAttribute('data-order') ? 1 : -1;
		this.setAttribute('data-order', (order < 1) ? '1' : '');
		var rows = $('tbody.list tr');
		$('tbody.list').empty().append(rows.sort(function(a, b) {
			return order * ($(a).find('td.' + field).text() > $(b).find('td.' + field).text() ? 1 : -1);
		}));
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
	var current_filter = '';
	for (var k in filter) {
		if (filter[k]) {
			current_filter += '/' + k + '/' + filter[k].replace('/', '//');
		}
	}
	window.location.href = current_filter;
}
