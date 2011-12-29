#!/usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2011 vCider Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""
A tiny test program, which doesn't do anyting meaningful, but shows you
how to use the low-level VciderApiClient.

"""

import json

#
# Import the low-level client class
#
from vcider.api_client import VciderApiClient

#
# Provide these values that are specific to your server and your account.
#
APP_ID       = "0"                                # Currently is always zero.
API_ID       = "091ca03fa801527abbd76109d439efe8" # Your public API-ID.
API_KEY      = "afe380c143965e289fcc70c9e1ed3f2d" # Your secret API access key. Please keep secret!
API_BASE_URI = "https://beta.vcider.com/api/"     # The vCider API base address

#
# Create an instance of the client. The 'autosync' flag indicates that we should automatically
# try to handle any time sync issues with the server.
#
print "Connecting to vCider API..."
vac = VciderApiClient(API_BASE_URI, API_ID, API_KEY, autosync=True)

#
# Access the root of the API to get information about the basic links into the system.
# Check that the result is 200 (HTTP OK status code). Convert the result buffer into
# via JSON into a dictionary: The low-level client does not perform this conversion itself.
#
print "Retrieving root resource..."
r = vac.get("/")
d = json.loads(r.content)
print json.dumps(d, sort_keys=True, indent=4)  # We use JSON for nicely formatted printing

#
# After learning the link to the node list from the root resource,
# we now issue the request to get this list.
#
print "Retrieving list of node IDs..."
node_list_link = d['links']['nodes_list']['uri']
r = vac.get(node_list_link)
d = json.loads(r.content)
print json.dumps(d, sort_keys=True, indent=4)  # We use JSON for nicely formatted printing

#
# The following would add a node to a network: We post the node-ID to the node-list
# resource of a network.
#
#r = vac.post("/api/nets/195a591a936b50219ab9ba90ee944097/nodes/",
#            json.dumps({ "node_id" : "fb89514e9f5c5594bbbb660acbba4f2f" }))

