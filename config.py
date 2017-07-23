#!/bin/env python
# -*- coding: utf-8 -*-

# Get the local path
import os
localpath = os.path.dirname(os.path.realpath(__file__))

# Set configuration
PULLREQUESTS   = '%s/data/pullrequests.json'   % localpath
RELEASETICKETS = '%s/data/releasetickets.json' % localpath
REVIEWERS      = '%s/data/reviewers.json'      % localpath
REPOSITORY     = 'opencast-community/opencast'
