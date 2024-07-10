"""
Proxy adapter for use in odin-control.

This module implements a simple proxy adapter, allowing requests to be proxied to
one or more remote HTTP resources, typically further odin-control instances.

Tim Nicholls, Ashley Neaves STFC Detector Systems Software Group.
"""
import requests
from odin.util import decode_request_body
from odin.adapters.adapter import (
    ApiAdapter, ApiAdapterResponse,
    request_types, response_types, wants_metadata
)
#from odin.adapters.base_proxy import BaseProxyTarget, BaseProxyAdapter
from prototype_DAQ.base_proxy import BaseProxyTarget, BaseProxyAdapter


class ProxyTarget(BaseProxyTarget):
    """
    Proxy adapter target class.

    This class implements a proxy target, its parameter tree and associated
    status information for use in the ProxyAdapter.
    """

    def __init__(self, name, url, request_timeout):
        """
        Initialise the ProxyTarget object.

        This constructor initialises the ProxyTarget, creating a HTTP client and delegating
        the full initialisation to the base class.

        :param name: name of the proxy target
        :param url: URL of the remote target
        :param request_timeout: request timeout in seconds
        """
        # Initialise the base class
        super(ProxyTarget, self).__init__(name, url, request_timeout)

        # Initialise the data and metadata trees from the remote target
        self.remote_get()
        self.remote_get(get_metadata=True)

    def remote_get(self, path='', get_metadata=False):
        """
        Get data from the remote target.

        This method updates the local proxy target with new data by issuing a GET request to the
        target URL, and then updates the local proxy target data and status information according to
        the response. The detailed handling of this is implemented by the base class.

        :param path: path to data on remote target
        :param get_metadata: flag indicating if metadata is to be requested
        """
        super(ProxyTarget, self).remote_get(path, get_metadata)

    def remote_set(self, path, data):
        """
        Set data on the remote target.

        This method sends data to the remote target by issuing a PUT request to the target
        URL, and then updates the local proxy target data and status information according to the
        response. The detailed handling of this is implemented by the base class.

        :param path: path to data on remote target
        :param data: data to set on remote target
        """
        super(ProxyTarget, self).remote_set(path, data)

    def _send_request(self, request, path, get_metadata=False):
        """
        Send a request to the remote target using the Requests library, handling the response
        and updating target data accordingly

        :param request: HTTP request dict to transmit to target
        :param path: path of data being updated
        :param get_metadata: flag indicating if metadata is to be requested
        """
        # Send the request to the remote target, handling any exceptions that occur
        try:
            # Use the requests.request method to send the request
            response = requests.request(
                method=request['method'], 
                url=request['url'],
                headers=request.get('headers'),# Safely get access to optional params
                timeout=request.get('timeout'), 
                data=request.get('data') 
            )
        except Exception as fetch_exception:
            # Set the response to the exception so it can be handled during response resolution 
            response = fetch_exception

        # Process the response from the target, updating data as appropriate
        self._process_response(response, path, get_metadata)

    # def _send_request(self, method, request, path, get_metadata=False):
    #         """
    #         Send a request to the remote target and update data.
        
    #         This internal method sends a request to the remote target using the HTTP client
    #         and handles the response, updating target data accordingly.

    #         :param request: HTTP request to transmit to target
    #         :param path: path of data being updated
    #         :param get_metadata: flag indicating if metadata is to be requested
    #         """
    #         # Send the request to the remote target, handling any exceptions that occur
    #         try:
    #             # Build the get/put request, using the requests library to send them
    #             if method == 'GET':
    #                 response = requests.get(url=request['url'], headers=request['headers'], timeout=request['timeout'])
    #             elif method == 'PUT':
    #                 response = requests.put(url=request['url'], headers=request['headers'], timeout=request['timeout'], data=request['data'])
    #         except Exception as fetch_exception:
    #             # Set the response to the exception so it can be handled during response resolution 
    #             response = fetch_exception

    #         # Process the response from the target, updating data as appropriate
    #         self._process_response(response, path, get_metadata)


class ProxyAdapter(ApiAdapter, BaseProxyAdapter):
    """
    Proxy adapter class for odin-control.

    This class implements a proxy adapter, allowing odin-control to forward requests to
    other HTTP services.
    """

    def __init__(self, **kwargs):
        """
        Initialise the ProxyAdapter.

        This constructor initialises the adapter instance. The base class adapter is initialised
        with the keyword arguments and then the proxy targets and paramter tree initialised by the
        proxy adapter mixin.

        :param kwargs: keyword arguments specifying options
        """
        # Initialise the base class
        super(ProxyAdapter, self).__init__(**kwargs)

        # Initialise the proxy targets and parameter trees
        self.initialise_proxy(ProxyTarget)

    @response_types('application/json', default='application/json')
    def get(self, path, request):
        """
        Handle an HTTP GET request.

        This method handles an HTTP GET request, returning a JSON response. The request is
        passed to the adapter proxy and resolved into responses from the requested proxy targets.

        :param path: URI path of request
        :param request: HTTP request object
        :return: an ApiAdapterResponse object containing the appropriate response
        """
        get_metadata = wants_metadata(request)

        self.proxy_get(path, get_metadata)
        (response, status_code) = self._resolve_response(path, get_metadata)

        return ApiAdapterResponse(response, status_code=status_code)

    @request_types("application/json", "application/vnd.odin-native")
    @response_types('application/json', default='application/json')
    def put(self, path, request):
        """
        Handle an HTTP PUT request.

        This method handles an HTTP PUT request, returning a JSON response. The request is
        passed to the adapter proxy to set data on the remote targets and resolved into responses
        from those targets.

        :param path: URI path of request
        :param request: HTTP request object
        :return: an ApiAdapterResponse object containing the appropriate response
        """
        # Decode the request body from JSON, handling and returning any errors that occur. Otherwise
        # send the PUT request to the remote target
        try:
            body = decode_request_body(request)
        except (TypeError, ValueError) as type_val_err:
            response = {'error': 'Failed to decode PUT request body: {}'.format(str(type_val_err))}
            status_code = 415
        else:
            self.proxy_set(path, body)
            (response, status_code) = self._resolve_response(path)

        return ApiAdapterResponse(response, status_code=status_code)
