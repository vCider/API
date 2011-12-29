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
Exceptions for the vCider API.

"""

class VciderApiException(Exception):
    """
    An exception to indicate that something went wrong with the API access.

    Has three arguments: The request URI, the HTTP status code and the response
    message.

    """
    pass

class VciderApiStaleResource(VciderApiException):
    """
    This exception is raised if we find out that the server cannot serve
    a particular resource anymore: In that case, the existing data we have
    for this resource may be out of date.

    """
    pass

class VciderApiUnavailableResource(VciderApiException):
    """
    This exception is raised if we find out that the server cannot serve
    a particular resource.

    """
    pass

