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
We provide a low-level client for the vCider API.

The client should be used to build higher-level functionality on top of it. An example
of a higher level client can be found in client.py.

"""

import time, json
import hmac, hashlib
import requests, urllib

class VciderApiClient(object):
    """
    A low-level client for the vCider API.

    This client knows how to issue properly authenticated HTTP requests to the vCider API.
    However, it does not know anything about the actual resources that it accesses, such
    as nodes or networks.

    Usage:

        from vcider.api_client import VciderApiClient

        vac = VciderApiClient(<api_base_uri>, <api_id>, <api_key>)

        vac.get("/")   # For the API root resource
        ...
        vac.put("/api/nodes/bb3ef2c99fde53a4a6031f4e2cbc80fb/", json.dumps({"name":"foo"}))

    or

        vac.put("nodes/bb3ef2c99fde53a4a6031f4e2cbc80fb/", json.dumps({"name":"foo"}))
        ...

    However, the better approach is to learn the relevant links from the root resource,
    rather than having to hard-code specific URI patterns in your code. Let the 'root'
    resource be the only URI of the API you will ever need to remember:

        root = vac.get("root/")

        nodes_list = root['links']['nodes_list']['uri']

        vac.put(nodes_list + "bb3ef2c99fde53a4a6031f4e2cbc80fb/", json.dumps({"name":"foo"}))


    The get(), put(), post() and delete() methods provided by the client class correspond
    to the HTTP methods of the same name and return a response object as defined by the
    'requests' HTTP library. This return object has attributes, such as 'status_code' and
    'content'.

    Prerequisites: The client uses the requests HTTP library: http://docs.python-requests.org

    """
    # Quickly translate HTTP method names into the actual request methods we can call
    _CALL_METHODS = {
        "GET"    : requests.get,
        "PUT"    : requests.put,
        "POST"   : requests.post,
        "DELETE" : requests.delete,
    }

    # Some exceptions, which users of this class may have to look out for.
    class MalformedRequest(Exception):
        """
        Thrown when the request (usually the URI) is malformed.

        """
        pass

    class ExcessiveTimeDrift(Exception):
        """
        Thrown when client and server time stamps disagree and we cannot sync the drift.

        """
        pass

    def __init__(self, api_base_uri, api_id, api_key, app_id=0, autosync=False):
        """
        Initialize the client.

        @param api_base:        The base URI of the API. For example: https://my.vcider.com/api
        @param api_id:          The public part of the API credentials. This is similar
                                to a username for your client software.
        @param api_key:         The secret part of the API crendetials. This is similar
                                to a password for your client software.
        @param app_id:          The ID of the application to which you wish to connect.
                                This is currently just '0'.
        @param autosync:        If True, the client attempts to automatically sync the
                                time stamps between client and server in case a request
                                to the server was rejected because of excessive time drift.

        """
        if not api_base_uri.endswith("/"):
            api_base_uri += "/"
        self.api_base_uri      = api_base_uri
        self.api_id            = api_id
        self.api_key           = api_key
        self.app_id            = app_id
        self.autosync          = autosync
        self.time_diff         = 300
        self.server_info_uri   = "server_info/"
        uri_type, base_path                 = urllib.splittype(self.api_base_uri)
        server_name, self.api_base_uri_path = urllib.splithost(base_path)
        self.api_server_root   = "%s://%s" % (uri_type, server_name)

    def _construct_auth_hdr(self, http_method, uri, data=None, hash_type="SHA256"):
        """
        Construct the auth-header for a vCider API request.

        @param  http_method:    The HTTP request method, which is used for this request.
                                Should be either "GET", "POST", "PUT" or "DELETE".
        @param  uri:            The URI to which the request should be sent. Not that this
                                is only the PATH component (and any query string).
        @param  data:           Any data to be sent to the server. Only needed for PUt and POST
                                requests. For all other methods, this should be None.
        @param  hash_type:      Either "SHA1", "SHA256", "SHA512" or "MD5". Those are indicated as
                                plain strings in the 'hash-type' part of the Authorization header.
                                If this client code should be re-implemented in a different
                                language or environment, you have the choice between those 4 hash
                                functions, depending on what's available to you.

        @return                 A fully constructed value (string) for the Authorization
                                HTTP header.

        """
        # These are the hash functions we are supporting. The client lets the server know which
        # hash function was used (part of the Auth-header).
        hash_funcs = {
            "SHA1"   : hashlib.sha1,
            "SHA256" : hashlib.sha256,
            "SHA512" : hashlib.sha512,
            "MD5"    : hashlib.md5
        }

        # See if the request has any parameters, we split it into path and query-string component
        elems = uri.split("?")
        if len(elems) > 2:
            raise VciderApiClient.MalformedRequest("Malformed query string")
        elif len(elems) == 2:
            path, query_raw = elems
            query_pairs = query_raw.split("&")    # Sort query parameter pairs alphabetically
            query_pairs.sort()
            query       = '&'.join(query_pairs)   # Assemble sorted elements back into correct qs
        else:
            path  = elems[0]
            query = "-"                           # Not passed to client, just used for HMAC
            
        if not path.endswith("/"):                # For HMACcalculation, ensure path ends with '/'
            path += "/"

        # The time stamp we use for the signature calculation. Apply any time differential
        # we may have detected when performing a time-sync with the server.
        timestamp   = int(time.time()) - self.time_diff

        # Assemble the message over which the signature is calculated. This message contains
        # elements of the HTTP request, the time stamp, IDs, message body, etc.
        msg         = "%s:%s:%s:%d:%s:%s:%s" % \
                                            (http_method, path, query, timestamp,
                                             self.app_id, self.api_id, data if data else "")
        sig         = hmac.new(self.api_key, msg, hash_funcs[hash_type]).hexdigest()
        auth_hdr    = "VCIDER %s:%s:%d:%s:%s" % \
                                            (self.app_id, self.api_id, timestamp, hash_type, sig)
        return auth_hdr


    def _make_api_req(self, http_method, uri, data=None, nosync=False):
        """
        Make a request to the vCider API.

        @param  http_method:    The HTTP request method, which is used for this request.
                                Should be either "GET", "POST", "PUT" or "DELETE".
        @param  uri:            The URI to which the request should be sent. Not that this
                                is only the PATH component (and any query string) that is
                                in addition to the stored API base URI.
                                full URI is "http://localhost:8000/api/foo/bar?x=1&abc=test"
                                then the uri is: foo/bar?x=1&abc=test
        @param  data:           Any data to be sent to the server. Only needed for PUt and POST
                                requests. For all other methods, this should be None.
        @param  nosync:         If set, we never attemtp to synchronize the time stamps
                                between client and server, even if an error for excessive
                                drift comes back. We use this when we repeat the request after
                                a first time-drift error and we have attempted a time-sync.
                                We then call this function again with that flag to avoid endless
                                loops in case something goes wrong.

        @return                 Returns a response object of the 'requests' library.

        """
        if uri.startswith("/") and len(uri) > 1:
            # This is an absolute URI, so we can take it as is...
            pass
        else:
            # This is a relative URI, so we prepend the full path of the
            # API base (or it is just a request to the API root, which is
            # also done with just "/", in which case we make that one
            # slash disappear)
            if uri == "/":
                uri = ""
            uri = self.api_base_uri_path + uri

        auth_hdr = self._construct_auth_hdr(http_method, uri, data=data)
        headers  = {
            "Authorization" : auth_hdr,
            "Content-type"  : "application/json",
            "Accept"        : "application/json"
        }
        ret = VciderApiClient._CALL_METHODS[http_method](self.api_server_root + uri,
                                                         headers=headers,
                                                         data=data)
        if ret.status_code == 403 and "Excessive time drift" in ret.content:
            # Special handling of time drift errors: If we were initialized
            # with the autosync flag then we will attempt to sync the time
            # and will retry the request.
            if self.autosync and not nosync:
                self.time_sync()
                ret = self._make_api_req(http_method, uri, data, nosync=True)
            else:
                raise VciderApiClient.ExcessiveTimeDrift(ret.content)

        return ret

    def get(self, uri):
        """
        Perform a GET request to the server.

        Normal response code should be 200.

        @param uri:             The API URI (path and query string only).

        @return                 Returns a response object of the 'requests' library.

        """
        return self._make_api_req("GET", uri)

    def delete(self, uri):
        """
        Perform a DELETE request to the server.

        Normal response code should be 200.

        @param uri:             The API URI (path and query string only).

        @return                 Returns a response object of the 'requests' library.

        """
        return self._make_api_req("DELETE", uri)

    def put(self, uri, data):
        """
        Perform a DELETE request to the server.

        Normal response code should be 204.

        @param uri:             The API URI (path and query string only).
        @param data:            The data to be sent to the server as a string.

        @return                 Returns a response object of the 'requests' library.

        """
        return self._make_api_req("PUT", uri, data)

    def post(self, uri, data):
        """
        Perform a DELETE request to the server.

        Normal response code should be 201. The location of the newly created
        entity can be found in the 'Location' HTTP response header.

        @param uri:             The API URI (path and query string only).
        @param data:            The data to be sent to the server as a string.

        @return                 Returns a response object of the 'requests' library.

        """
        return self._make_api_req("POST", uri, data)

    def time_sync(self):
        """
        Sycnhronize the time between client and server.

        Compares the times and calculates a delta-time, which is then applied
        to all future requests.

        """
        ret            = self.get(self.server_info_uri)
        data           = json.loads(ret.content)
        server_time    = int(data['volatile']['server_time'])
        my_time        = int(time.time())
        self.time_diff = my_time - server_time




