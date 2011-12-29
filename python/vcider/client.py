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
This module implements a high-level client for the vCider API.

Todo
====
It could be useful to add some caching in this client, so that if we ask
the same question multiple times, we don't always end up sending out HTTP
requests. The _make_get_req() function would be a good place to insert
a caching layer.

Gateway-related operations are currently not implemented in the client.

"""

import json, urllib

from api_client import VciderApiClient
from exceptions import VciderApiException
from resources  import VciderNode, VciderNetwork, RESOURCE_NODE, RESOURCE_NET, RESOURCE_PORT

class VciderClient(VciderApiClient):
    """
    A high level client for the vCider API, which uses objects to represent
    server resources to the client. It extends the low-level VciderApiClient
    class.

    Concepts
    ========
    The client provides special classes to represent server-side resources:

        VciderNode:     Representing a node resource.
        VciderNetwork:  Representing a vCider network resource.
        VciderPort:     Representing a port, the connection of a node to
                        a network.

    Each of these resources expose a number of properies, which are filled
    after a resource has been received. Most properties are read-only, but
    some can be set. Once a change has been made, the save() method of the
    object can be called to write the changes back to the resource on the
    server. Furthermore, the delete() method of the objects can be used to
    remove the resource from the server.

    Exceptions are raised if any of the operations does not proceed as
    expected.

    Example
    =======

        from vcider.client import VciderClient

        vc = VciderClient(API_BASE_URI, API_ID, API_KEY)

        nodes     = vc.get_all_nodes()                              # Dictionary of all my nodes
        nets      = vc.get_all_networks()                           # Dictionary of all networks

        node      = vc.get_node("b23825f6a2cf54b5b645c07e83fc2311") # Get node based on its ID
        node.name = "test_node"                                     # Change name and save
        node.save()

        net       = vc.get_network("9337c6e1b8455978a318ce03e76626b7")  # Get network based on its ID
        nnodes    = net.get_all_nodes()                             # All nodes in this network
        nports    = net.get_all_ports()                             # All ports of this network
        port      = net.add_node(node)                              # Port represents new connection

        print port                                                  # Prints interface information

        port.delete()                                               # Remove node from network


    """

    # -----------------------------
    # Some private helper functions
    # -----------------------------

    def _make_qs_uri_for_list(self, uri, info):
        """
        Add the query string for an access to a list.

        If the 'info' flag is set then the _related query string modifier
        is specified. In all cases, the _id modifier is set.

        @param uri:             The URI to which the necessary query string
                                should be added.
        @param info:            A flag indicating whether the caller wishes to
                                receive related information about referenced
                                resources.

        @return:                A ready-formatted URI, with the required query
                                string attached.

        """
        path, qs = urllib.splitquery(uri)
        qs_list = [ self.id_qs ]
        if info:
            qs_list.append(self.related_qs)
        more_qs = "&".join(qs_list)
        if not qs:
            qs = ""
        else:
            qs += "&"
        qs += more_qs
        uri = "%s?%s" % (path, qs)
        return uri

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
        try:
            buf = json.loads(r.content)
        except ValueError:
            buf = r.content
        if r.status_code != expect:
            raise VciderApiException(uri, r.status_code, buf)
        return buf

    def _make_put_req(self, uri, data, expect=204):
        """
        Issue a PUT request and ensure the response status code is as expected.

        If not then it raises an exception.

        @param uri:             The URI (without server component, just the path
                                and query string).
        @param data:            The data (a dictionary) that should be posted to
                                the server.
        @param expect:          The expected HTTP status code in the response.
                                If a different status code is seen, an exception
                                is raised.

        """
        r = self.put(uri, json.dumps(data))
        if r.status_code != expect:
            try:
                buf = json.loads(r.content)
            except ValueError:
                buf = r.content
            raise VciderApiException(uri, r.status_code, buf)

    def _make_post_req(self, uri, data, expect=201):
        """
        Issue a POST request and ensure the response status code is as expected.

        If not then it raises an exception.

        @param uri:             The URI (without server component, just the path
                                and query string).
        @param data:            The data (a dictionary) that should be posted to
                                the server.
        @param expect:          The expected HTTP status code in the response.
                                If a different status code is seen, an exception
                                is raised.

        @return:                The location of the newly created resource.

        """
        r = self.post(uri, json.dumps(data))
        if r.status_code != expect:
            try:
                buf = json.loads(r.content)
            except ValueError:
                buf = r.content
            raise VciderApiException(uri, r.status_code, buf)
        loc = r.headers.get('location')
        if loc:
            loc = urllib.splithost(urllib.splittype(loc)[1])[1]
        return loc

    def _make_delete_req(self, uri, expect=204):
        """
        Issue a DELETE request and ensure the response status code is as expected.

        If not then it raises an exception.

        @param uri:             The URI (without server component, just the path
                                and query string).
        @param expect:          The expected HTTP status code in the response.
                                If a different status code is seen, an exception
                                is raised.

        """
        r = self.delete(uri)
        if r.status_code != expect:
            try:
                buf = json.loads(r.content)
            except ValueError:
                buf = r.content
            raise VciderApiException(uri, r.status_code, buf)

    def _get_root(self):
        """
        Return the root dictionary of the API.

        @return:                A dictionary containg the root resource of the
                                vCider API. This normally contains links to the
                                more interesting parts of the API, such as node
                                or network lists.

        """
        return self._make_get_req("/")

    def _list_process(self, api_list, resource_class=None):
        """
        Return either a list of IDs or a dictionary with instantiated
        resource objects.

        Lists in the vCider API always have the same format: You can either
        get a list of URIs of each element, or you can request some additional
        information (add '_related' to the query string or add '_id' to the
        the resource IDs).
        
        This convenience function performs some post-processing on the list as
        it was returned by the API:

        Depending on the value of 'info', this either just returns a list of
        all IDs, or it returns a dictionary with IDs as key and the related
        information as value (also in a dictionary).

        We assume that the list contains '_id' elements.

        @param api_list:        A list as returned by the API.
        @param resource_class:  If set then return a dictionary where the key
                                is the resource ID and the value is an initialized
                                resource object, such as VciderNode or VciderNetwork.
                                Otherwise, just return a list of IDs.

        @return:                A list of IDs or a dictionary with IDs as key
                                and per-item information as values.

        """
        if resource_class:
            dd = dict(
                [
                    (e[self.id_link_attr],
                     resource_class(self, e[self.id_link_attr], e['uri'], e[self.related_link_attr]))
                    for e in api_list
                ]
            )
        else:
            dd = [ e[self.id_link_attr] for e in api_list ]

        return dd


    # ----------------
    # Public functions
    # ----------------

    def __init__(self, *args, **kwargs):
        """
        Initialize by accessing the API root and learning the important links.

        We avoid hard-coding any URIs or knowledge about specific URI query
        string modifiers. Therefore, we start by accessing the server's root
        resource, which allows us to learn (and cache) the URIs and also to
        find out about the supported query string modifiers.

        """
        super(VciderClient, self).__init__(*args, **kwargs)

        # We are a higher level client: Always attempt auto sync in case of time drift
        self.autosync                         = True

        # We don't want to hard-code URIs. Instead, we learn them
        # as we go along. Here we store the links to the main lists
        # in the system: Nodes, networks, etc.
        self.links                            = self._get_root()['links']
        self.nodes_list                       = self.links['nodes_list']['uri']
        self.networks_list                    = self.links['networks_list']['uri']
        self.credentials                      = self.links['credentials']['uri']
        self.server                           = self.links['server']['uri']
        self.template_cache                   = dict()

        server_info                           = self._make_get_req(self.server)

        # Learn about the available query string modifiers
        uri_mods                              = server_info['uri_modifiers']
        self.id_qs                            = uri_mods['id']['param']
        self.linkinfo_qs                      = uri_mods['link_info']['param']
        self.related_qs                       = uri_mods['related_info']['param']
        self.list_end_qs                      = uri_mods['list_end_index']['param']
        self.list_start_qs                    = uri_mods['list_start_index']['param']

        # Learn about the additional link attributes, which may be returned if
        # a particular query string parameter is provided.
        link_info_add_link_attrs              = uri_mods['link_info']['add_link_attrs']
        self.allowed_methods_link_attr        = link_info_add_link_attrs['allowed_methods']['name']
        self.template_link_attr               = link_info_add_link_attrs['template_uri']['name']

        id_add_link_attrs                     = uri_mods['id']['add_link_attrs']
        self.id_link_attr                     = id_add_link_attrs['resource_ids']['name']

        related_add_link_attrs                = uri_mods['related_info']['add_link_attrs']
        self.related_link_attr                = related_add_link_attrs['related_info']['name']

        # Learn about the URI patterns. We don't want to hard code those
        # in our client code, which is why the client gets the information
        # about those patterns from the server
        uri_patterns                          = server_info['uri_patterns']
        self.uri_pattern                      = dict()
        self.uri_pattern[RESOURCE_NODE]       = uri_patterns['node']['uri'].replace("#node_id#", "%s")
        self.uri_pattern[RESOURCE_NET]        = uri_patterns['network']['uri'].replace("#net_id#", "%s")
        self.uri_pattern[RESOURCE_PORT]       = uri_patterns['port']['uri'].replace("#port_id#", "%s")
        self.templ_uri_pattern                = dict()
        self.templ_uri_pattern[RESOURCE_NODE] = uri_patterns['node_template']['uri'].replace("#node_id#", "%s")
        self.templ_uri_pattern[RESOURCE_NET]  = uri_patterns['network_template']['uri'].replace("#net_id#", "%s")
        self.templ_uri_pattern[RESOURCE_PORT] = uri_patterns['port_template']['uri'].replace("#port_id#", "%s")

        # Prepare a cache for the new network template (which is loaded on demand by create_network())
        self.new_net_template                 = None

    def get_num_nodes_and_nets(self):
        """
        Return the current number of nodes and networks.

        @return:                A tuple of node and net counts.

        """
        d = self._get_root()
        return ( d['volatile']['num_nodes'], d['volatile']['num_nets'] )

    def get_all_nodes(self, info=True):
        """
        Return all the nodes.

        @param info:            If this flag is unset then only a list of nodes
                                IDs is returned. If it is set then a dictionary
                                of full objects representing the resources is
                                returned.

        @return:                Dictionary keyed by the port ID, containing
                                the object representations of the resource as
                                value. If 'info' is set to False then only a list
                                of node IDs is returned.

        """
        uri = self._make_qs_uri_for_list(self.nodes_list, info)
        return self._list_process(self._make_get_req(uri), VciderNode if info else None)

    def get_node(self, node_id):
        """
        Return an object representing a node resource.

        @param node_id:         The ID of a vCider node as a string.

        @return:                A node object, representing a node resource on the server.

        """
        return VciderNode(self, node_id, self.uri_pattern[RESOURCE_NODE] % node_id)

    def get_all_networks(self, info=True):
        """
        Return all networks.

        @param info:            If this flag is unset then only a list of network
                                IDs is returned. If it is set then a dictionary
                                of full objects representing the resources is
                                returned.

        @return:                Dictionary keyed by the port ID, containing
                                the object representations of the resource as
                                value. If 'info' is set to False then only a list
                                of network IDs is returned.

        """
        uri = self._make_qs_uri_for_list(self.networks_list, info)
        return self._list_process(self._make_get_req(uri), VciderNetwork if info else None)

    def get_network(self, net_id):
        """
        Return an object representing a network resource.

        @param node_id:         The ID of a vCider network as a string.

        @return:                A network object, representing a network resource on the server.

        """
        return VciderNetwork(self, net_id, self.uri_pattern[RESOURCE_NET] % net_id)

    def create_network(self, name, net_addresses, auto_addr=True, encrypted=True, may_use_pub_addr=True, tags=""):
        """
        Create a new network.

        All the parameters specified for the network during creation may be changed
        at a later time.

        @param name:             A user defined name for the new network.
        @param net_addresses:    The address space of the network in CIDR notation, or None if no automatic
                                 address assignment should be performed. Specify an empty string as value
                                 if you don't want to set it (in that case you also need to set auto_addr to False).
        @param auto_addr:        If True then perform automatic address assignment for new nodes, otherwise
                                 do not do so.
        @param encrypted:        If True then all traffic amongst nodes of this network is encrypted.
        @param may_use_pub_addr: If True then the nodes of the network are allowed to establish contact with each
                                 other via their public address. Since this may be a NATed address, this will
                                 not work in some data centers. However, Amazon EC2 users should leave this
                                 set to True. If it is false then the public address of the node (as it shows
                                 itself to the vCider controller) will never be used for inter-node communication.
                                 Node that the setting of this flag does not impact the route optimization that
                                 is automatically performed by vCider: Even if the initial contact between nodes
                                 may happen via the public addresses, vCider always tries to optimize traffic and
                                 at least attempts to use private addresses later on if possible.
        @param tags:             Tags for this network (comma separated list of words and phrases). If a node
                                 presents tags to the vCider controller on first contact, those node tags will
                                 be matched against the network tags. If a match is found then the node is
                                 automatically assigned to one or more networks.

        @return:                 A network resource object.

        """
        if not self.new_net_template:
            # Get and cache the template for a new network, if we don't have it already
            new_net_templ_uri = self.links['networks_list']['uri'] + "?" + self.template_link_attr
            self.new_net_template = self._make_get_req(new_net_templ_uri)

        tmp_template = dict(
            name                 = name,
            net_addresses        = net_addresses,
            opt_auto_addr        = auto_addr,
            opt_encrypted        = encrypted,
            opt_may_use_pub_addr = may_use_pub_addr,
            tags                 = tags
        )

        # Make sure the keys in the template match the ones we have assembled here.
        tmpl_keys = self.new_net_template.keys()
        for k in tmp_template.keys():
            if k not in tmpl_keys:
                raise VciderApiException("Template key mismatch '%s'. Server/client mismatch?" % k)

        # The POST of this data returns the location of the new network. We then initialize
        # a new network object with this location data.
        loc = self._make_post_req(self.networks_list, tmp_template)
        return VciderNetwork(self, None, loc)

