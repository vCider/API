"""
We provide a low-level client for the vCider API.

This client knows how to issue properly authenticated HTTP requests to the vCider API.
However, it does not know anything about the actual resources that it accesses, such
as nodes or networks.

The client should be used to build higher-level functionality on top of it.

Usage:

    from vcider.api_client import VciderApiClient

    vac = VciderApiClient(<server_uri>, <api_id>, <api_key>)

    vac.get("/api/root")
    ...
    vac.put("/api/nodes/bb3ef2c99fde53a4a6031f4e2cbc80fb/", json.dumps({"name":"foo"}))
    ...

The get(), put(), post() and delete() methods provided by the client class correspond
to the HTTP methods of the same name and return a response object as defined by the
'requests' HTTP library. This return object has attributes, such as 'status_code' and
'content'.

Prerequisites: The client uses the requests HTTP library: http://docs.python-requests.org

"""

import time, json
import requests
import hmac, hashlib

class VciderApiClient(object):
    _CALL_METHODS = {
        "GET"    : requests.get,
        "PUT"    : requests.put,
        "POST"   : requests.post,
        "DELETE" : requests.delete,
    }

    class MalformedRequest(Exception):
        pass

    def __init__(self, server_root, api_id, api_key, app_id=0):
        if server_root.endswith("/"):
            server_root = server_root[:-1]
        self.server_root = server_root
        self.api_id      = api_id
        self.api_key     = api_key
        self.app_id      = app_id
        self.time_diff   = 0

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
        hash_funcs = {
            "SHA1"   : hashlib.sha1,
            "SHA256" : hashlib.sha256,
            "SHA512" : hashlib.sha512,
            "MD5"    : hashlib.md5
        }

        if not uri.startswith("/"):
            raise VciderApiClient.MalformedRequest("URI should start with '/'")

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

        timestamp   = int(time.time()) - self.time_diff
        msg         = "%s:%s:%s:%d:%s:%s:%s" % \
                                            (http_method, path, query, timestamp,
                                             self.app_id, self.api_id, data if data else "")
        sig         = hmac.new(self.api_key, msg, hash_funcs[hash_type]).hexdigest()
        auth_hdr    = "VCIDER %s:%s:%d:%s:%s" % \
                                            (self.app_id, self.api_id, timestamp, hash_type, sig)
        return auth_hdr


    def _make_api_req(self, http_method, uri, data=None):
        """
        Make a request to the vCider API.

        @param  http_method:    The HTTP request method, which is used for this request.
                                Should be either "GET", "POST", "PUT" or "DELETE".
        @param  uri:            The URI to which the request should be sent. Not that this
                                is only the PATH component (and any query string). So, the
                                protocol ('http://', or 'https://') as well as the server
                                name (and optional port) are omitted. For example, if the
                                full URI is "http://localhost:8000/foo/bar?x=1&abc=test"
                                then the uri is: /foo/bar?x=1&abc=test
        @param  data:           Any data to be sent to the server. Only needed for PUt and POST
                                requests. For all other methods, this should be None.

        @return                 Returns a response object of the 'requests' library.

        """
        auth_hdr = self._construct_auth_hdr(http_method, uri, data=data)
        headers  = {
            "Authorization" : auth_hdr,
            "Content-type"  : "application/json",
            "Accept"        : "application/json"
        }
        return VciderApiClient._CALL_METHODS[http_method](self.server_root+uri,
                                                          headers=headers,
                                                          data=data)

    def get(self, uri):
        return self._make_api_req("GET", uri)

    def delete(self, uri):
        return self._make_api_req("DELETE", uri)

    def put(self, uri, data):
        return self._make_api_req("PUT", uri, data)

    def post(self, uri, data):
        return self._make_api_req("POST", uri, data)

    def time_sync(self):
        ret            = self.get("/api/server_info/")
        data           = json.loads(ret.content)
        server_time    = int(data['volatile']['server_time'])
        my_time        = int(time.time())
        self.time_diff = my_time - server_time


