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
from api_client import VciderApiClient

#
# Provide these values that are specific to your server and your account.
#
APP_ID  = "0"                                   # Currently is always zero.
API_ID  = "59a7b4173e3254c0b4e222bf60b31136"    # Your public API-ID.
API_KEY = "a775b5a5c19856a1acff88da7db72cc2"    # Your secret API access key. Please keep secret!
ROOT    = "http://localhost:8000"               # The vCider API server's root URI.

#
# Create an instance of the client. The 'autosync' flag indicates that we should automatically
# try to handle any time sync issues with the server.
#
vac = VciderApiClient(ROOT, API_ID, API_KEY, autosync=True)

#
# Access the root of the API to get information about the basic links into the system.
# Check that the result is 200 (HTTP OK status code). Convert the result buffer into
# via JSON into a dictionary: The low-level client does not perform this conversion itself.
#
r = vac.get("/api/root/")
d = json.loads(r.content)
print json.dumps(d, sort_keys=True, indent=4)  # We use JSON for nicely formatted printing

#
# The following would add a node to a network: We post the node-ID to the node-list
# resource of a network.
#
#r = vac.post("/api/nets/195a591a936b50219ab9ba90ee944097/nodes/",
#            json.dumps({ "node_id" : "fb89514e9f5c5594bbbb660acbba4f2f" }))

