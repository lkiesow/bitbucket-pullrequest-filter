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
      <input v-model="filter[key]" :placeholder="key.replace('_', ' ')" />
    </div>
  </div>
  <a class="row" v-if="filter_row(pr)" v-for="pr in requests" :href=pr.url>
    <span class=cell v-for="key in keys" :title="pr[key]">{{ pr[key] }}</span>
  </a>
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
    filter: {},
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
      axios.get('/pr.json').then(response => {
        this.prLoading = false;
        this.requests = response.data;
      }).catch((error) => { console.log(error) });
    }
  },
  mounted() {
    this.getTickets();
    this.getPullRequests();
  }
});
