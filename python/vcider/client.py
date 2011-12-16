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
A client for the vCider API, which extends the low-level VciderApiClient
class.

This VciderClient is implemented as a class, which provides higher-level constructs,
such as retrieving node or network lists, adding nodes to networks, and so on.

"""

import json

from api_client import VciderApiClient


class VciderClient(VciderApiClient):

    class ApiException(Exception):
        """
        An exception to indicate that something went wrong with the API access.

        Has two arguments: The HTTP status code and the response message.

        """
        pass

    # -----------------------------
    # Some private helper functions
    # -----------------------------

    def _make_get_req(self, uri, expect=200):
        """
        Issue a GET request and ensure the response status code is as expected.

        If not then it raises an exception.

        In case of success, the response is JSON decoded.

        """
        r = self.get(uri)
        if r.status_code != expect:
            raise VciderClient.ApiException(r.status_code, r.content)
        return json.loads(r.content)

    def _get_root(self):
        """
        Return the root dictionary of the API.

        """
        return self._make_get_req("/api/root")


    # ----------------
    # Public functions
    # ----------------

    def __init__(self, *args, **kwargs):
        """
        Initialize by accessing the API root and learning the important links.

        """
        super(VciderClient, self).__init__(*args, **kwargs)

        # We are a higher level client: Always attempt auto sync
        self.autosync = True

        # We don't want to hard-code URIs. Instead, we learn them
        # as we go along. Here we store the links to the main lists
        # in the system: Nodes, networks, etc.
        self.links          = self._get_root()['links']
        self.nodes_list     = self.links['nodes_list']
        self.networks_list  = self.links['networks_list']
        self.credentials    = self.links['credentials']
        self.server         = self.links['server']

        print "@@@: ", self.links



