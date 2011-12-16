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
A ttest program, which shows how to use the high-level VciderClient for
the vCider API.

"""

import json

#
# Import the high-level client class
#
from client import VciderClient

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
vc = VciderClient(ROOT, API_ID, API_KEY)

