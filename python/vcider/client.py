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

This VciderClient class adds higher-level constructs, such as retrieving
node or network lists, assigning nodes to networks, and so on.

It could be useful to add some caching in this client, so that if we ask
the same question multiple times, we don't always end up sending out HTTP
requests. The _make_get_req() function would be a good place to insert
a caching layer.

"""

import json

from api_client import VciderApiClient


class VciderClient(VciderApiClient):

    class ApiException(Exception):
        """
        An exception to indicate that something went wrong with the API access.

        Has three arguments: The request URI, the HTTP status code and the response
        message.

        """
        pass

    # -----------------------------
    # Some private helper functions
    # -----------------------------

    def _make_get_req(self, uri, expect=200):
        """
        Issue a GET request and ensure the response status code is as expected.

        If not then it raises an exception. In case of success, the response is
        JSON decoded.

        @param uri:             The URI (without server component, just the path
                                and query string).
        @param expect:          The expected HTTP status code in the response.
                                If a different status code is seen, an exception
                                is raised.

        @return:                The JSON decoded response object.

        """
        r = self.get(uri)
        if r.status_code != expect:
            raise VciderClient.ApiException(uri, r.status_code, r.content)
        return json.loads(r.content)

    def _get_root(self):
        """
        Return the root dictionary of the API.

        """
        return self._make_get_req("/api/root")

    def _list_process(self, api_list, info):
        """
        Return either a list of IDs or a dictionary with related info.

        Lists in the vCider API always have the same format: You can either
        get a list of URIs of each element, or you can request some additional
        information (add '_related' to the query string).

        Depending on the value of info, this either just returns a list of
        all IDs, or it returns a dictionary with IDs as key and the related
        information as value (also in a dictionary).

        @param api_list:        A list as returned by the API.
        @param info:            If True, return a dictionary with additional
                                information for each item, else return just
                                a list of IDs.

        @return:                A list of IDs or a dictionary with IDs as key
                                and per-item information as values.

        """
        # We assume that we can get the ID in the 'third' element of the item URI.
        # A URI may look like this: "/api/nodes/<node-id>/"
        if info:
            dd = dict( (e['uri'].split("/")[3], e['_related']) for e in api_list )
        else:
            dd = [ e['uri'].split("/")[3] for e in api_list ]

        return dd


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
        self.nodes_list     = self.links['nodes_list']['uri']
        self.networks_list  = self.links['networks_list']['uri']
        self.credentials    = self.links['credentials']['uri']
        self.server         = self.links['server']['uri']

    def get_num_nodes_and_nets(self):
        """
        Return the current number of nodes and networks.

        @return:                A tuple of node and net counts.

        """
        d = self._get_root()
        return ( d['volatile']['num_nodes'], d['volatile']['num_nets'])

    def get_list_of_nodes(self, info=False):
        """
        Return the list of all nodes.

        @param info:            If this flag is set then some additional
                                information about each node is returned,
                                not just the node IDs.

        @return:                List of node IDs. If 'info' is set then a
                                dictionary is returned with the node IDs
                                as keys and the additional node information
                                (also as dictionary) as value.

        """
        qs = "?_related" if info else ""
        return self._list_process(self._make_get_req(self.nodes_list+qs), info)

    def get_list_of_networks(self, info=False):
        """
        Return the list of all networks.

        @param info:            If this flag is set then some additional
                                information about each network is returned,
                                not just the network IDs.

        @return:                List of network IDs. If 'info' is set then a
                                dictionary is returned with the network IDs
                                as keys and the additional network information
                                (also as dictionary) as value.

        """
        qs = "?_related" if info else ""
        return self._list_process(self._make_get_req(self.networks_list+qs), info)

    def get_node_detail(self, node_id):
        """
        Return details about a given node.

        @param node_id:         The ID of a vCider node as a string.

        @return:                A dictionary with detailed information about the node.

        """
        d = self._make_get_req("%s%s/" % (self.nodes_list, node_id))
        del d['links'] # Users of the higher-level client don't need to know about the links
        return d

    def get_network_detail(self, net_id):
        """
        Return details about a given network.

        @param net_id:          The ID of a vCider network as a string.

        @return:                A dictionary with detailed information about the network.

        """
        d = self._make_get_req("%s%s/" % (self.networks_list, net_id))
        del d['links'] # Users of the higher-level client don't need to know about the links
        return d

    def get_networks_of_node(self, node_id, info=False):
        """
        Return list of networks that a node belongs to.

        @param node_id:         The ID of a vCider node as a string.
        @param info:            If this flag is set then some additional
                                information about each network is returned,
                                not just the network IDs.

        @return:                List of network IDs. If 'info' is set then a
                                dictionary is returned with the network IDs
                                as keys and the additional network information
                                (also as dictionary) as value.

        """
        # Avoid hard-coding URIs. Instead, we get the node info and follow a link
        d            = self._make_get_req("%s%s/" % (self.nodes_list, node_id))
        qs           = "?_related" if info else ""
        net_list_uri = self._make_get_req(d['links']['networks_list']['uri']+qs)
        return self._list_process(net_list_uri, info)

    def get_nodes_of_network(self, net_id, info=False):
        """
        Return list of nodes that belong to a network.

        @param net_id:          The ID of a vCider network as a string.
        @param info:            If this flag is set then some additional
                                information about each node is returned,
                                not just the node IDs.

        @return:                List of node IDs. If 'info' is set then a
                                dictionary is returned with the node IDs
                                as keys and the additional node information
                                (also as dictionary) as value.

        """
        # Avoid hard-coding URIs. Instead, we get the network info and follow a link
        d             = self._make_get_req("%s%s/" % (self.networks_list, net_id))
        qs            = "?_related" if info else ""
        node_list_uri = self._make_get_req(d['links']['nodes_list']['uri']+qs)
        return self._list_process(node_list_uri, info)

    def get_ports_of_node(self, node_id, info=False):
        """
        Return list of ports that are configured for a node.

        @param node_id:         The ID of a vCider node as a string.
        @param info:            If this flag is set then some additional
                                information about each port is returned,
                                not just the port IDs.

        @return:                List of port IDs. If 'info' is set then a
                                dictionary is returned with the port IDs
                                as keys and the additional port information
                                (also as dictionary) as value.

        """
        d             = self._make_get_req("%s%s/" % (self.nodes_list, node_id))
        qs            = "?_related" if info else ""
        port_list_uri = self._make_get_req(d['links']['ports_list']['uri']+qs)
        return self._list_process(port_list_uri, info)

    def get_ports_of_network(self, net_id, info=False):
        """
        Return list of ports that are configured for a network.

        @param node_id:         The ID of a vCider network as a string.
        @param info:            If this flag is set then some additional
                                information about each port is returned,
                                not just the port IDs.

        @return:                List of port IDs. If 'info' is set then a
                                dictionary is returned with the port IDs
                                as keys and the additional port information
                                (also as dictionary) as value.

        """
        d             = self._make_get_req("%s%s/" % (self.networks_list, net_id))
        qs            = "?_related" if info else ""
        port_list_uri = self._make_get_req(d['links']['ports_list']['uri']+qs)
        return self._list_process(port_list_uri, info)



