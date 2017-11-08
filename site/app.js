"use strict";

const keys = ['id', 'created_date', 'author_name', 'title', 'destination',
              'reviewer_name']

Vue.component('pull-requests', {
  props: ['requests', 'filter', 'keys'],
  template: `
  <div class=table>
	  <div class=row>
		 <span class=cell v-for="key in keys">{{ key.replace(/_.*$/, '') }}</span>
	  </div>
	  <div class=row>
		 <div class=cell v-for="key in keys">
			<input type=text v-model="filter[key]"
			  :placeholder="key.replace('_', ' ')" />
		 </div>
	  </div>
	  <div class="row" v-if="filter_row(pr)" v-for="pr in requests">
		  <a class=cell :href=pr.url :title=pr.id>#{{ pr.id }}</a>
		  <a class=cell :href=pr.url :title=pr.created_date>{{ pr.created_date }}</a>
		  <span class=cell :title=pr.author_name
        v-on:click="filter['author_name'] = pr.author_name">{{ pr.author_name }}</span>
		  <a class=cell :href=pr.url :title=pr.title>{{ pr.title }}</a>
		  <span class=cell :title=pr.destination
        v-on:click="filter['destination'] = pr.destination">{{ pr.destination }}</span>
		  <span class=cell :title=pr.reviewer_name
        v-on:click="filter['reviewer_name'] = pr.reviewer_name">{{ pr.reviewer_name }}</span>
	  </div>
  </div>
  `,
methods: {
  contains(a, b) {
    b = (b || '').toLowerCase();
    return (a || '').toString().toLowerCase().indexOf(b) >= 0;
  },
  filter_row(row) {
    for (let i = 0; i < keys.length; i++) {
      let filterval = this.filter[keys[i]];
      if (filterval && !this.contains(row[keys[i]], filterval)) {
        return false;
      }
    }
    return true;
  }
}
})


Vue.component('release-tickets', {
  props: ['tickets'],
  template: `
  <div class=table style="max-width: 300px;">
  <div class=row>
    <span class=cell>Version</span>
    <span class=cell>Assignee</span>
  </div>
  <a class="row" v-for="ticket in tickets" :href=ticket.url>
    <span class=cell>{{ ticket.version }}</span>
    <span class=cell>{{ ticket.assignee }}</span>
  </a>
  </div>
  `
})


let app = new Vue({
  el: '#app',
  data: {
    filter: {
      'author_name': '',
      'destination': '',
      'reviewer_name': ''},
    all: false,
    reverse: false,
    loading: true,
    tickets: {},
    prLoading: true,
    requests: {},
    keys: keys
  },
  methods: {
    getTickets() {
      this.loading = true;
      axios.get('/release.json').then(response => {
        this.loading = false;
        this.tickets = response.data;
      }).catch((error) => { console.log(error) });
    },
    getPullRequests() {
      this.prLoading = true;

      let args = [];
      if (this.all) {
        args.push('all=true');
      }
      if (this.reverse) {
        args.push('reverse=true');
      }
        
      let url = '/pr.json?' + args.join('&');
      axios.get(url).then(response => {
        this.prLoading = false;
        this.requests = response.data;
      }).catch((error) => { console.log(error) });
    }
  },
  watch: {
    reverse: function() {
      this.getPullRequests();
    },
    all: function() {
      this.getPullRequests();
    }
  },
  mounted() {
    this.getTickets();
    this.getPullRequests();
  }
});
