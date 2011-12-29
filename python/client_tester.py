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
A test program, which shows how to use the high-level VciderClient for
the vCider API.

"""

import json

#
# Import the high-level client class
#
from vcider.client     import VciderClient
from vcider.exceptions import VciderApiException

#
# Provide these values that are specific to your server and your account.
#
APP_ID       = "0"                                # Currently is always zero.
API_ID       = "091ca03fa801527abbd76109d439efe8" # Your public API-ID.
API_KEY      = "afe380c143965e289fcc70c9e1ed3f2d" # Your secret API access key. Please keep secret!
API_BASE_URI = "https://beta.vcider.com/api/"     # The vCider API base address

#
# Create an instance of the client.
#

vc = VciderClient(API_BASE_URI, API_ID, API_KEY)

nums = vc.get_num_nodes_and_nets()
print "======== Current number of nodes: %d  Current number of networks: %d" % (nums[0], nums[1])

print "======== List of all nodes:"
nodes = vc.get_all_nodes()
for node in nodes.values():
    print node


print "======== List of networks of one node (%s):" % node.id
nnets = node.get_all_networks()
for net in nnets.values():
    print net

print "======== List of all networks:"
nets = vc.get_all_networks()
for net in nets.values():
    print net

print "======== List of the ports of a network:"
nports = net.get_all_ports()
for port in nports.values():
    print port

"""

# The following examples involve changes or specific resource IDs.
# Therefore, they don't apply to the testuser account.
# If you have your own account with vCider, you can substitute
# real IDs and perform the write operations.

#
# If we want to retrieve a specific node based on ID:
#
node = vc.get_node("b23825f6a2cf54b5b645c07e83fc2311")

#
# If we want to change something about a node:
#
node.name = "foobar_blah"
node.save()

#
# If we want to retrieve a specific network based on ID:
#
net = vc.get_network("9337c6e1b8455978a318ce03e76626b7")

#
# If we want to change something about a network:
#
net.auto_addr     = True
net.net_addresses = "11.2/16"
net.save()

#
# If you want to add a node to a network:
#
port = net.add_node(node)

#
# If you want to remove a node from a network:
#
port.delete()

#
# If you want to create a new network:
#
newnet = vc.create_network("some_test_network_name", "", False)

# 
# Making invalid changes to the network:
#
newnet.net_addresses = "foo"      # Malformed address range
try:
    newnet.save()
except VciderApiException, e:
    # Will raise exception because of malformed address range
    print "could not create network: ", e

"""


