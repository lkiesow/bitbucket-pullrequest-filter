#!/bin/env python
# -*- coding: utf-8 -*-

# Set default encoding to UTF-8
import sys
reload(sys)
sys.setdefaultencoding('utf8')

import config
import json


def main():
	r = {}
	try:
		with open(config.REVIEWERS, 'r') as f:
			r = json.loads(f.read())
	except:
		return

	stats = {}
	for k,v in r.iteritems():
		if not v.get('user'):
			continue
		if not stats.get(v.get('user')):
			stats[v['user']] = []
		stats[v['user']].append(k)

	stats = [ (k,len(v),[int(x) for x in v]) for k,v in stats.iteritems() ]

	# Sort by number of reviews
	stats.sort(key=lambda r: r[1])

	for s in stats:
		print('%12s, %5s, %120s' % s)


if __name__ == "__main__":
	main()
