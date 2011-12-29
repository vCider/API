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

import json, urllib

from api_client import VciderApiClient

_RESOURCE_NODE  = "Node"
_RESOURCE_NET   = "Network"
_RESOURCE_PORT  = "Port"

class VciderResource(object):
    """
    High-level representation of a vCider resource.

    This is the base class for nodes, networks and ports.

    """
    _KEY_TRANSLATE = dict()

    def __init__(self, vcider_client, resource_id, resource_uri, resource_data = None):
        """
        Initialize the resource reprsentation.

        If no 'resource_data' is specified then we instead try to access
        the relevant data from the server.

        @param resource_id:     The ID of the resource.
        @param resource_uri:    The URI of the resource.
        @param resource_data:   The data for the resource. Optional.

        This can raise StaleResource if no resource_data was provided and
        the server cannot

        """
        self._resource_id   = resource_id
        self._resource_uri  = resource_uri
        self._resource_data = resource_data
        self._vcider_client = vcider_client
        self._deleted       = False
        if self._resource_data:
            self._is_updated         = False
            self._update_status_msg  = "Not updated yet"
        else:
            self.update()
        if not self._resource_id:
            # If no resource-ID was provided to us directly then we 
            # try to take it from the resource data instead
            self._resource_id = self._get_data('id', 'meta/id')

    def _get_data(self, name, key):
        """
        Access a particular item from the resource data.

        Since the resource data is always a dicionary, the 'key' is defined
        as a search string, which can traverse multiple levels. Each level
        is separated from the next by a '/'. So, "links/networks_list/uri"
        gets the URI of for the networks list of a node, for example.

        If the specified key does not exist, we raise an AttributeError.

        @param name:            The name of the attribute, which we only need in
                                case we need to raise an AttributeError exception.
                                The 'name' here is the high-level item that we
                                define as a property.
        @param key:             The complete search path to the element within the
                                resource data dictionary.

        @return:                The element that was referenced by the key.

        """
        path_elems = key.split("/")
        d = self._resource_data
        for i, e in enumerate(path_elems):
            if e not in d:
                if not self._is_updated:
                    # If we can't find the item, we do a refresh to see if we can get
                    # it that way. This is often needed when the resource was instantiated
                    # from 'related' info.
                    self.update()
                    # Now we try to get the element once more (from this refreshed data).
                    # The update() will have set the is_updated flag, so we won't fall
                    # into an endless loop.
                    return self._get_data(name, key)

                raise AttributeError("'%s' object has no attribute '%s'" % \
                                     (type(self).__name__, name))
            if i == len(path_elems)-1:
                return d[e]
            else:
                d = d[e]

    def _set_data(self, name, key, value):
        """
        Set a particular item in the resource data.

        Keys are specified in the same way as for _get_data().

        If the specified key does not exist, we raise an AttributeError.

        @param name:            The name of the attribute, which we only need in
                                case we need to raise an AttributeError exception.
                                The 'name' here is the high-level item that we
                                define as a property.
        @param key:             The complete search path to the element within the
                                resource data dictionary.
        @param value:           The new value for the specified item.

        """
        path_elems = key.split("/")
        d = self._resource_data
        for i, e in enumerate(path_elems):
            if e not in d:
                if not self._is_updated:
                    # If we can't find the item, we do a refresh to see if we can get
                    # it that way. This is often needed when the resource was instantiated
                    # from 'related' info.
                    self.update()
                    # Now we try to get the element once more (from this refreshed data).
                    # The update() will have set the is_updated flag, so we won't fall
                    # into an endless loop.
                    return self._set_dat(name, key, value)

                raise AttributeError("'%s' object has no attribute '%s'" % \
                                     (type(self).__name__, name))
            if i == len(path_elems)-1:
                d[e] = value
            else:
                d = d[e]

    def __repr__(self):
        return "%s: id: %s" % (self._RESOURCE_TYPE, self.id)

    def __str__(self):
        """
        Return a more user friendly and verbose output.

        We return a formatted string, which contains all attributes of the
        resource.

        """
        out_lines = [ "%s: %s" % (self._RESOURCE_TYPE, self.id) ]
        # All attributes that don't start with a '_' are public ones, which makes it easy
        # for us. We also don't print any bound methods (those methods have the 'im_self'
        # attribute on which we can filter).
        is_bound_method = lambda x: getattr(x, 'im_self', False)
        attr_names = [ key for key in dir(self)  \
                          if not key.startswith("_") and not is_bound_method(getattr(self, key)) ]
        for attr in attr_names:
            out_lines.append( "    %18s: %s" % (attr, getattr(self, attr)) )
        return "\n".join(out_lines)

    def _get_template(self, name, uri):
        """
        Return a template.

        This implements a small cache, which prevents the client from having
        to query for the template every time we want to issue a PUT or POST.

        @param name:            Name under which the template should be stored in the cache.
        @param uri:             URI from where to load the template if we don't have it in the cache.

        @return:                A template dictionary.

        """
        template = self._vcider_client.template_cache.get(name)
        if not template:
            template = self._vcider_client._make_get_req(uri)
            self._vcider_client.template_cache[name] = template
        return template

    def is_deleted(self):
        """
        Return True if the resource represented through this object was deleted.

        Note that this only works if the delete operation took place through this
        object here. If someone else went and deleted the resource then this object
        here is not automatically updated.

        @return:                True if the object is deleted, False otherwise.

        """
        return self._deleted

    def update(self):
        """
        Refresh the data from the server.

        If the resource cannot be accessed on the server then the status message
        is updated and the is_valid flag is set.

        """
        existing_resource = self._resource_data is not None
        try:
            path, qs = urllib.splitquery(self._resource_uri)
            if not qs:
                qs = ""
            # When we get a resource, we always request it with linkinfo (to get template
            # links) and IDs (to have the IDs of referenced resources available)
            new_qs_list = list()
            if self._vcider_client.linkinfo_qs not in qs:
                new_qs_list.append(self._vcider_client.linkinfo_qs)
            if self._vcider_client.id_qs not in qs:
                new_qs_list.append(self._vcider_client.id_qs)
            new_qs = "&".join(new_qs_list)
            if not qs:
                qs = new_qs
            else:
                qs += new_qs

            self._resource_data      = self._vcider_client._make_get_req("%s?%s" % (path, qs))
            self._is_updated         = True
            self._update_status_msg  = "Ok"
        except VciderClient.ApiException, e:
            self._is_updated        = False
            self._update_status_msg = e.args[2]
            if e.args[1] == 404  or  not existing_resource:
                raise VciderClient.UnavailableResource("Cannot find resource: " + \
                                                                       self._update_status_msg)
            else:
                raise VciderClient.StaleResource("Cannot update resource: " + self._update_status_msg)

    def save(self):
        """
        Store the modified version of this resource back to the server.

        We use the template URI to retrieve the template, then transcribe
        appropriate values from our in-memory representation to the dictionary
        that will be posted to the server.

        """
        # Retrive the template for this resource type
        template = self._get_template(self._RESOURCE_TYPE, 
                                  self._vcider_client.templ_uri_pattern[self._RESOURCE_TYPE] % self.id)

        # Now search for the data we need to supply in our current resource data. As we are
        # finding those items, we are creating a temporary copy of the template, since we
        # don't want to modify the copy that's in the cache. The name of the attribute in
        # the object representation MAY be different than in the resource data dictionary.
        # Therefore, if a _KEY_TRANSLATE dictionary is defined, we use that to translate
        # the template key name into the name of the object attribute. The _KEY_TRANSLATE
        # dictionary doesn't have to be complete. It only needs to specify those cases
        # where the object attribute name is different than the resource-data key.
        tmp_template = dict()
        for key in template.keys():
            attr_key = self._KEY_TRANSLATE.get(key, key)  # Either resource-data key or translation
            if hasattr(self, attr_key):
                val = getattr(self, attr_key, None)
                tmp_template[key] = val

        # The temporary template dictionary has now been created and we can submit it
        # to the server in order to save the update.
        self._vcider_client._make_put_req( \
                                  self._resource_uri,
                                  tmp_template)

    def delete(self):
        """
        Delete this resource from the server.

        """
        self._vcider_client._make_delete_req(self._resource_uri)
        self._deleted = True

class VciderNode(VciderResource):
    """
    An object representing a node resource.

    """
    _RESOURCE_TYPE = _RESOURCE_NODE
    
    id            = property(lambda self: self._resource_id,
                             doc="The ID of the node")
    uri           = property(lambda self: urllib.splitquery(self._get_data("uri", "links/self/uri"))[0],
                             doc="The URI of the node")
    name          = property(lambda self:       self._get_data("name", "name"),
                             lambda self, val : self._set_data("name", "name", val),
                             doc="The name of the node")
    os            = property(lambda self: self._get_data("os", "info/os"),
                             doc="The operating system of the node")
    tags          = property(lambda self: self._get_data("tags", "info/tags"),
                             doc="Any tags defined for this node")
    sw_version    = property(lambda self: self._get_data("sw_version", "info/sw_version"),
                             doc="Version of the vCider software running on this node")
    phys_addrs    = property(lambda self: self._get_data("phys_addrs", "info/phys_addrs_set"),
                             doc="The list of physical addresses of the node")
    creation_time = property(lambda self: self._get_data("creation_time", "meta/creation_time"),
                             doc="The time when this node first connected to the vCider controller")
    cur_packets   = property(lambda self: self._get_data("cur_packets", "volatile/cur_packets"),
                             doc="The current packets per second seen by this node on vCider interfaces")
    cur_traffic   = property(lambda self: self._get_data("cur_traffic", "volatile/cur_traffic"),
                             doc="The current traffic (bytes/s) seen by this node on vCider interfaces")
    last_seen     = property(lambda self: self._get_data("last_seen", "volatile/last_seen"),
                             doc="The time when this node last reported to the vCider controller")
    num_gateways  = property(lambda self: self._get_data("num_gateways", "volatile/num_gateways"),
                             doc="How many gateway routes are configured for this node")
    num_networks  = property(lambda self: self._get_data("num_networks", "volatile/num_networks"),
                             doc="In how many networks is this node a member")
    status_level  = property(lambda self: self._get_data("status_level", "volatile/status_level"),
                             doc="The current status level of the node")
    status_msg    = property(lambda self: self._get_data("status_msg", "volatile/status_msg"),
                             doc="The current status message of the node")

    def __repr__(self):
        ret = super(VciderNode, self).__repr__()
        ret += ", name: %s, status: %s (%s), update-status: %s" % \
                   ( self.name, self.status_level, self.status_msg, self._update_status_msg )
        return ret

    def get_list_of_networks(self, info=False):
        """
        Return the list of all networks that this node is a member of.

        @param info:            If this flag is set then some additional
                                information about each network is returned,
                                not just the network IDs.

        @return:                List of network IDs. If 'info' is set then a
                                dictionary is returned with the network IDs
                                as keys and the additional network information
                                (also as dictionary) as value.

        """
        net_list_uri = self._get_data("networks_list", "links/networks_list/uri")
        uri          = self._vcider_client._make_qs_uri_for_list(net_list_uri, info)
        return self._vcider_client._list_process(self._vcider_client._make_get_req(uri),
                                                 VciderNetwork if info else None)

    def get_list_of_ports(self, info=False):
        """
        Return the list of all the ports of this node.

        @param info:            If this flag is set then some additional
                                information about each port is returned,
                                not just the port IDs.

        @return:                List of port IDs. If 'info' is set then a
                                dictionary is returned with the port IDs
                                as keys and the additional port information
                                (also as dictionary) as value.

        """
        port_list_uri = self._get_data("port_list", "links/ports_list/uri")
        uri           = self._vcider_client._make_qs_uri_for_list(port_list_uri, info)
        return self._vcider_client._list_process(self._vcider_client._make_get_req(uri),
                                                 VciderPort if info else None)

class VciderNetwork(VciderResource):
    """
    An object representing a network resource.

    """
    _RESOURCE_TYPE = _RESOURCE_NET
    _KEY_TRANSLATE = {
        "opt_auto_addr"         : "auto_addr",
        "opt_encrypted"         : "encrypted",
        "opt_may_use_pub_addr"  : "may_use_pub_addr",
    }
    
    id            = property(lambda self: self._resource_id,
                             doc="The ID of the network")
    uri           = property(lambda self: urllib.splitquery(self._get_data("uri", "links/self/uri"))[0],
                             doc="The URI of the network")
    name          = property(lambda self:       self._get_data("name", "name"),
                             lambda self, val : self._set_data("name", "name", val),
                             doc="The name of the node")
    net_addresses = property(lambda self:       self._get_data("net_addresses", "net_addresses"),
                             lambda self, val : self._set_data("net_addresses", "net_addresses", val),
                             doc="The CIDR address space of the network")
    auto_addr     = property(lambda self:       self._get_data("opt_auto_addr", "opt_auto_addr"),
                             lambda self, val : self._set_data("opt_auto_addr", "opt_auto_addr", val),
                             doc="If True then IP addresses are automatically assigned to new nodes")
    encrypted     = property(lambda self:       self._get_data("opt_encrypted", "opt_encrypted"),
                             lambda self, val : self._set_data("opt_encrypted", "opt_encrypted", val),
                             doc="If True all address within the network is encrypted")
    may_use_pub_addr = property( \
        lambda self:       self._get_data("opt_may_use_pub_addr", "opt_may_use_pub_addr"),
        lambda self, val : self._set_data("opt_may_use_pub_addr", "opt_may_use_pub_addr", val),
        doc="If True then nodes may try to use public (even NAT) addresses to connect with each other")
    tags          = property(lambda self:      self._get_data("tags", "tags"),
                             lambda self, val: self._set_data("tags", "tags", val),
                             doc="Any tags defined for this network")
    creation_time = property(lambda self: self._get_data("creation_time", "meta/creation_time"),
                             doc="The time when this network was created")
    cur_packets   = property(lambda self: self._get_data("cur_packets", "volatile/cur_packets"),
                             doc="The current packets per second within this vCider network")
    cur_traffic   = property(lambda self: self._get_data("cur_traffic", "volatile/cur_traffic"),
                             doc="The current traffic (bytes/s) within this vCider network")
    num_gateways  = property(lambda self: self._get_data("num_gateways", "volatile/num_gateways"),
                             doc="How many gateway routes are configured for this network")
    num_nodes     = property(lambda self: self._get_data("num_nodes", "volatile/num_nodes"),
                             doc="In how many nodes are members of this network")
    status_level  = property(lambda self: self._get_data("status_level", "volatile/status_level"),
                             doc="The current status level of the network")
    status_msg    = property(lambda self: self._get_data("status_msg", "volatile/status_msg"),
                             doc="The current status message of the network")

    def __repr__(self):
        ret = super(VciderNetwork, self).__repr__()
        ret += ", name: %s, status: %s (%s), update-status: %s" % \
                   ( self.name, self.status_level, self.status_msg, self._update_status_msg )
        return ret

    def get_list_of_nodes(self, info=False):
        """
        Return the list of all nodes that are part of this network.

        @param info:            If this flag is set then some additional
                                information about each node is returned,
                                not just the node IDs.

        @return:                List of node IDs. If 'info' is set then a
                                dictionary is returned with the node IDs
                                as keys and the additional node information
                                (also as dictionary) as value.

        """
        node_list_uri = self._get_data("nodes_list", "links/nodes_list/uri")
        uri           = self._vcider_client._make_qs_uri_for_list(node_list_uri, info)
        return self._vcider_client._list_process(self._vcider_client._make_get_req(uri),
                                                 VciderNode if info else None)

    def get_list_of_ports(self, info=False):
        """
        Return the list of all the ports of this node.

        @param info:            If this flag is set then some additional
                                information about each port is returned,
                                not just the port IDs.

        @return:                List of port IDs. If 'info' is set then a
                                dictionary is returned with the port IDs
                                as keys and the additional port information
                                (also as dictionary) as value.

        """
        port_list_uri = self._get_data("port_list", "links/ports_list/uri")
        uri           = self._vcider_client._make_qs_uri_for_list(port_list_uri, info)
        return self._vcider_client._list_process(self._vcider_client._make_get_req(uri),
                                                 VciderPort if info else None)

    def add_node(self, node):
        """
        Add a node to the network.

        @param node:            Either the ID of a node, or the node's object representation.

        @return:                A port object for the new connection.

        """
        # First we need to get the template to add a node to the network
        template_uri = self._get_data("template_uri", "links/nodes_list/%s" % \
                                                              self._vcider_client.template_link_attr)
        template     = self._get_template(self._RESOURCE_TYPE+"_add_node", template_uri)

        if "node_id" not in template:
            raise VciderClient.ApiException( \
                         "Template for adding node to network does not contain 'node_id'")

        if isinstance(node, VciderNode):
            # Someone passed us a full node object
            node_id = node.id
        else:
            # This is just the ID of a node
            node_id = node

        # We don't modify the real template, which is stored in the cache. Instead,
        # we make a disposable copy.
        tmp_template = dict(node_id=node_id)

        # Now we can POST this filled out template to the node list of the network
        list_uri = self._get_data("list_uri", "links/nodes_list/uri")
        loc      = self._vcider_client._make_post_req(list_uri, tmp_template)
        return VciderPort(self._vcider_client, None, loc)


class VciderPort(VciderResource):
    """
    An object representing a port resource.

    """
    _RESOURCE_TYPE = _RESOURCE_PORT
    
    id            = property(lambda self: self._resource_id,
                             doc="The ID of the port")
    uri           = property(lambda self: urllib.splitquery(self._get_data("uri", "links/self/uri"))[0],
                             doc="The URI of the port")
    vcider_vaddr  = property(lambda self:       self._get_data("vcider_vaddr", "vcider_vaddr"),
                             lambda self, val : self._set_data("vcider_vaddr", "vcider_vaddr", val),
                             doc="The one IP address that is under vCider control")
    mac_addr      = property(lambda self: self._get_data("mac_addr", "interface/mac_address"),
                             doc="The MAC address of the vCider interface")
    virt_ip_addrs = property(lambda self: self._get_data("virt_ip_addrs", "interface/virt_ip_addrs_set"),
                             doc="All IP addresses that are configured on the vCider interface")
    node_id       = property(lambda self: self._get_data("node_id", "links/node/%s" % \
                                                                   self._vcider_client.id_link_attr),
                             doc="All IP addresses that are configured on the vCider interface")
    network_id    = property(lambda self: self._get_data("network_id", "links/network/%s" % \
                                                                   self._vcider_client.id_link_attr),
                             doc="All IP addresses that are configured on the vCider interface")
    creation_time = property(lambda self: self._get_data("creation_time", "meta/creation_time"),
                             doc="The time when this port was created")

    def __repr__(self):
        ret = super(VciderPort, self).__repr__()
        ret += ", node: %s, network: %s, vcider-addr: %s (%s)" % \
                   ( self.node_id, self.network_id, self.vcider_vaddr, self.mac_addr )
        return ret

class VciderClient(VciderApiClient):

    class ApiException(Exception):
        """
        An exception to indicate that something went wrong with the API access.

        Has three arguments: The request URI, the HTTP status code and the response
        message.

        """
        pass

    class StaleResource(ApiException):
        """
        This exception is raised if the found out that the server cannot serve
        a particular resource anymore: In that case, the existing data we have
        for this resource may be out of date.

        """
        pass

    class UnavailableResource(ApiException):
        """
        This exception is raised if the found out that the server cannot serve
        a particular resource (anymore).

        """
        pass

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
            raise VciderClient.ApiException(uri, r.status_code, buf)
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
            raise VciderClient.ApiException(uri, r.status_code, buf)

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
            raise VciderClient.ApiException(uri, r.status_code, buf)
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
            raise VciderClient.ApiException(uri, r.status_code, buf)

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
        self.template_cache = dict()

        server_info         = self._make_get_req(self.server)

        # Learn about the available query string modifiers
        uri_mods           = server_info['uri_modifiers']
        self.id_qs         = uri_mods['id']['param']
        self.linkinfo_qs   = uri_mods['link_info']['param']
        self.related_qs    = uri_mods['related_info']['param']
        self.list_end_qs   = uri_mods['list_end_index']['param']
        self.list_start_qs = uri_mods['list_start_index']['param']

        # Learn about the additional link attributes, which may be returned if
        # a particular query string parameter is provided.
        link_info_add_link_attrs       = uri_mods['link_info']['add_link_attrs']
        self.allowed_methods_link_attr = link_info_add_link_attrs['allowed_methods']['name']
        self.template_link_attr        = link_info_add_link_attrs['template_uri']['name']

        id_add_link_attrs              = uri_mods['id']['add_link_attrs']
        self.id_link_attr              = id_add_link_attrs['resource_ids']['name']

        related_add_link_attrs         = uri_mods['related_info']['add_link_attrs']
        self.related_link_attr         = related_add_link_attrs['related_info']['name']

        # Learn about the URI patterns. We don't want to hard code those
        # in our client code, which is why the client gets the information
        # about those patterns from the server
        uri_patterns          = server_info['uri_patterns']
        self.uri_pattern      = dict()
        self.uri_pattern[_RESOURCE_NODE] = uri_patterns['node']['uri'].replace("#node_id#", "%s")
        self.uri_pattern[_RESOURCE_NET]  = uri_patterns['network']['uri'].replace("#net_id#", "%s")
        self.uri_pattern[_RESOURCE_PORT] = uri_patterns['port']['uri'].replace("#port_id#", "%s")
        self.templ_uri_pattern                 = dict()
        self.templ_uri_pattern[_RESOURCE_NODE] = \
                                   uri_patterns['node_template']['uri'].replace("#node_id#", "%s")
        self.templ_uri_pattern[_RESOURCE_NET]  = \
                                   uri_patterns['network_template']['uri'].replace("#net_id#", "%s")
        self.templ_uri_pattern[_RESOURCE_PORT] = \
                                   uri_patterns['port_template']['uri'].replace("#port_id#", "%s")

    def get_num_nodes_and_nets(self):
        """
        Return the current number of nodes and networks.

        @return:                A tuple of node and net counts.

        """
        d = self._get_root()
        return ( d['volatile']['num_nodes'], d['volatile']['num_nets'] )

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
        uri = self._make_qs_uri_for_list(self.nodes_list, info)
        return self._list_process(self._make_get_req(uri), VciderNode if info else None)

    def get_node(self, node_id):
        """
        Return an object representing a node resource.

        @param node_id:         The ID of a vCider node as a string.

        @return:                A node object, representing a node resource on the server.

        """
        return VciderNode(self, node_id, self.uri_pattern[_RESOURCE_NODE] % node_id)

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
        uri = self._make_qs_uri_for_list(self.networks_list, info)
        return self._list_process(self._make_get_req(uri), VciderNetwork if info else None)

    def get_network(self, net_id):
        """
        Return an object representing a network resource.

        @param node_id:         The ID of a vCider network as a string.

        @return:                A network object, representing a network resource on the server.

        """
        return VciderNetwork(self, net_id, self.uri_pattern[_RESOURCE_NET] % net_id)


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
        net_list_uri = self._make_qs_uri_for_list(d['links']['networks_list']['uri'], info)
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
        node_list_uri = self._make_qs_uri_for_list(d['links']['nodes_list']['uri'], info)
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
        port_list_uri = self._make_qs_uri_for_list(d['links']['ports_list']['uri'], info)
        return self._list_process(port_list_uri, info)

    def get_ports_of_network(self, net_id, info=False):
        """
        Return list of ports that are configured for a network.

        @param net_id:          The ID of a vCider network as a string.
        @param info:            If this flag is set then some additional
                                information about each port is returned,
                                not just the port IDs.

        @return:                List of port IDs. If 'info' is set then a
                                dictionary is returned with the port IDs
                                as keys and the additional port information
                                (also as dictionary) as value.

        """
        d             = self._make_get_req("%s%s/" % (self.networks_list, net_id))
        port_list_uri = self._make_qs_uri_for_list(d['links']['ports_list']['uri'], info)
        return self._list_process(port_list_uri, info)


