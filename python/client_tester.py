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

Still TODO:

- Functions regarding gateways
- Functions to modify anything (currently only read-only)

"""

import json

#
# Import the high-level client class
#
from vcider.client import VciderClient

#
# Provide these values that are specific to your server and your account.
#
APP_ID       = "0"                                # Currently is always zero.
"""
API_ID       = "091ca03fa801527abbd76109d439efe8" # Your public API-ID.
API_KEY      = "afe380c143965e289fcc70c9e1ed3f2d" # Your secret API access key. Please keep secret!
API_BASE_URI = "https://beta.vcider.com/api/"     # The vCider API base address
"""
API_ID       = "59a7b4173e3254c0b4e222bf60b31136" # Your public API-ID.
API_KEY      = "a775b5a5c19856a1acff88da7db72cc2" # Your secret API access key. Please keep secret!
API_BASE_URI = "http://localhost:8000/api/"     # The vCider API base address

#
# Create an instance of the client.
#

vc = VciderClient(API_BASE_URI, API_ID, API_KEY)


api_root = vc._get_root()
print "\n======== The root API resource:\n", json.dumps(api_root, indent=4)

nums = vc.get_num_nodes_and_nets()
print "\n======== Current number of nodes and networks:\n", json.dumps(nums, indent=4)

nodes = vc.get_all_nodes()
"""
for id, node in nodes.items():
    print "\n" + str(node)
"""

print "====================================="
node = vc.get_node("b23825f6a2cf54b5b645c07e83fc2311")
print "--------------------- 1"
print node
print "--------------------- 2"
node.name = "foobar_blah"
print node
node.save()
nnets = node.get_all_networks()
print nnets

nets = vc.get_all_networks()
for id, net in nets.items():
    print "\n" + str(net)

net = vc.get_network("9337c6e1b8455978a318ce03e76626b7")
print "--------------------- 3"
print net
net.auto_addr = True
net.net_addresses = "11.2/16"
net.save()
print net.get_all_ports()


nnodes = net.get_all_nodes()
print "--------------------------------------------------------- 4"
print nnodes
port = net.add_node(node)
print port
port.delete()

nports = node.get_all_ports()
print nports




"""
nets_of_node = vc.get_networks_of_node(node_id, info=True)
print "\n======== Networks of that node with details:\n", json.dumps(nets_of_node, indent=4)

net_id = nets_of_node.keys()[0]  # Take one of the network IDs and use it for further requests

nodes_of_net = vc.get_nodes_of_network(net_id, info=True)
print "\n======== Nodes of that network with details:\n", json.dumps(nodes_of_net, indent=4)

ports_of_node = vc.get_ports_of_node(node_id, info=False)
print "\n======== Port list of the node:\n", json.dumps(ports_of_node, indent=4)

ports_of_net = vc.get_ports_of_network(net_id, info=False)
print "\n======== Port list of the network:\n", json.dumps(ports_of_net, indent=4)

print node_detail
node = VciderNode(vc, node_id, node_detail['links']['self']['uri'])
dir(node)
print node.id
print node.name
print node.bar
"""


