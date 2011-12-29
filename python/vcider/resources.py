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
The client-side resource representations.

"""

import urllib
from   exceptions import VciderApiException, VciderApiStaleResource, VciderApiUnavailableResource

RESOURCE_NODE  = "Node"
RESOURCE_NET   = "Network"
RESOURCE_PORT  = "Port"

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
        except VciderApiException, e:
            self._is_updated        = False
            self._update_status_msg = e.args[2]
            if e.args[1] == 404  or  not existing_resource:
                raise VciderApiUnavailableResource("Cannot find resource: " + self._update_status_msg)
            else:
                raise VciderApiStaleResource("Cannot update resource: " + self._update_status_msg)

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

    Only settable property is 'name'. Everything else is determined by the
    node itself and cannot be changed via the API or even the vCider UI.

    Please note that the delete() method can only be executed successfully
    if contact to the node was lost for some reason. If the node is still
    actively connected to the vCider controller then the delete operation
    will fail (an exception will be thrown).

    """
    _RESOURCE_TYPE = RESOURCE_NODE

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

    def get_all_networks(self, info=True):
        """
        Return all networks that this node is a member of.

        @param info:            If this flag is unset then only a list of network
                                IDs is returned. If it is set then a dictionary
                                of full objects representing the resources is
                                returned.

        @return:                Dictionary keyed by the network ID, containing
                                the object representations of the resource as
                                value. If 'info' is set to False then only a list
                                of network IDs is returned.

        """
        net_list_uri = self._get_data("networks_list", "links/networks_list/uri")
        uri          = self._vcider_client._make_qs_uri_for_list(net_list_uri, info)
        return self._vcider_client._list_process(self._vcider_client._make_get_req(uri),
                                                 VciderNetwork if info else None)

    def get_all_ports(self, info=True):
        """
        Return all the ports (network connections) of this node.

        @param info:            If this flag is unset then only a list of port
                                IDs is returned. If it is set then a dictionary
                                of full objects representing the resources is
                                returned.

        @return:                Dictionary keyed by the port ID, containing
                                the object representations of the resource as
                                value. If 'info' is set to False then only a list
                                of port IDs is returned.

        """
        port_list_uri = self._get_data("port_list", "links/ports_list/uri")
        uri           = self._vcider_client._make_qs_uri_for_list(port_list_uri, info)
        return self._vcider_client._list_process(self._vcider_client._make_get_req(uri),
                                                 VciderPort if info else None)

class VciderNetwork(VciderResource):
    """
    An object representing a network resource.

    Settable attributes are:

        - name
        - net_addresses    (address space of the network defined in CIDR format)
        - auto_addr        (flag indicating whether new nodes should receive an automatic IP address assignment)
        - encrypted        (flag indicating whether all inter-node traffic on the network should be encrypted)
        - may_use_pub_addr (flag indicating whether nodes may attempt to contact each other on public addresses)
        - tags             (the tags for this network, which may be used for automatic node assignment)

    """
    _RESOURCE_TYPE = RESOURCE_NET
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
    may_use_pub_addr = property(lambda self:      self._get_data("opt_may_use_pub_addr","opt_may_use_pub_addr"),
                                lambda self, val: self._set_data("opt_may_use_pub_addr","opt_may_use_pub_addr",val),
                                doc="If True, nodes may try to use public addresses to connect with each other")
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

    def get_all_nodes(self, info=True):
        """
        Return all nodes that are part of this network.

        @param info:            If this flag is unset then only a list of nodes
                                IDs is returned. If it is set then a dictionary
                                of full objects representing the resources is
                                returned.

        @return:                Dictionary keyed by the port ID, containing
                                the object representations of the resource as
                                value. If 'info' is set to False then only a list
                                of node IDs is returned.

        """
        node_list_uri = self._get_data("nodes_list", "links/nodes_list/uri")
        uri           = self._vcider_client._make_qs_uri_for_list(node_list_uri, info)
        return self._vcider_client._list_process(self._vcider_client._make_get_req(uri),
                                                 VciderNode if info else None)

    def get_all_ports(self, info=True):
        """
        Return all the ports (node connections) of this network.

        @param info:            If this flag is unset then only a list of port
                                IDs is returned. If it is set then a dictionary
                                of full objects representing the resources is
                                returned.

        @return:                Dictionary keyed by the port ID, containing
                                the object representations of the resource as
                                value. If 'info' is set to False then only a list
                                of port IDs is returned.

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
            raise VciderApiException("Template for adding node to network does not contain 'node_id'")

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

    The only settable property is 'vcider_vaddr', which is the virtual IP address under vCider
    control. The virtual vCider interface that was created on the node for this port can have
    any number of IP addresses assigned to it (for example as aliases), but only one of those
    addresses is under vCider's control.

    """
    _RESOURCE_TYPE = RESOURCE_PORT

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

