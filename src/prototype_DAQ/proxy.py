import logging
import requests
import time
from odin.util import decode_request_body
from odin.adapters.adapter import (
    ApiAdapter, ApiAdapterResponse,
    request_types, response_types, wants_metadata
)
from odin.adapters.base_proxy import BaseProxyTarget, BaseProxyAdapter

class TargetDecodeError(Exception):
    """Simple error class for raising target decode error exceptions."""
    pass


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

        This method requests data from the remote target by issuing a GET request to the target
        URL, and then updates the local proxy target data and status information according to the
        response. The request is sent to the target by the implementation-specific _send_request
        method.

        :param path: path to data on remote target
        :param get_metadata: flag indicating if metadata is to be requested
        """
        # Create a GET request to send to the target
        headers = self.request_headers.copy()

        # If metadata is requested, modify the Accept header accordingly
        if get_metadata:
            headers["Accept"] += ";metadata=True"

        request = {
            'url': self.url + path,
            'headers': headers,
            'timeout': self.request_timeout
        }

        # Send the request to the remote target
        logging.debug(f'Calling _send_request with: {request}')
        
        return self._send_request('GET', request, path, get_metadata)

    # def remote_get(self, path='', get_metadata=False):
    #     """
    #     Get data from the remote target.

    #     This method updates the local proxy target with new data by issuing a GET request to the
    #     target URL, and then updates the local proxy target data and status information according to
    #     the response. The detailed handling of this is implemented by the base class.

    #     :param path: path to data on remote target
    #     :param get_metadata: flag indicating if metadata is to be requested
    #     """
    #     super(ProxyTarget, self).remote_get(path, get_metadata)

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

    def _send_request(self, method, request, path, get_metadata=False):
        """
        Send a request to the remote target and update data.
        """
        logging.debug("Calling _send_request")
        # 'fixing' UnboundLocalError: local variable 'response' referenced before assignment
        response = None
        try:
            if method == 'GET':
                logging.debug(f'Calling GET methods')
                response = requests.get(request['url'], headers=request['headers'], timeout=request['timeout'])
                logging.debug(f'response from _send_request: {response}')
                logging.debug(f'Response body: {response.text}')
            elif method == 'PUT':
                logging.debug(f'Calling PUT methods')
                response = requests.put(request['url'], headers=request['headers'], timeout=request['timeout'], data=request['data'])
                logging.debug(f'response from _send_request: {response}')
        except Exception as fetch_exception:
            response = fetch_exception

        self._process_response(response, path, get_metadata)

    def _process_response(self, response, path, get_metadata):
        """
        Process a response from the remote target.
        """
        # Update the timestamp of the last request in standard format
        self.last_update = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())

        # If an HTTP response was received, handle accordingly
        if isinstance(response, requests.Response):
            # Decode the reponse body, handling errors by re-processing the repsonse as an
            # exception. Otherwise, update the target data and status based on the response.
            try:
                response_body = response.json()
            except ValueError as decode_error:
                error_string = "Failed to decode response body: {}".format(str(decode_error))
                self._process_response(TargetDecodeError(error_string), path, get_metadata)
            else:
                # Update status code, errror string and data accordingly
                self.status_code = response.status_code
                self.error_string = 'OK'
                # Set a reference to the data or metadata to update as necessary
                data_ref = self.metadata if get_metadata else self.data
                # If a path was specified, parse it and descend to the appropriate location in the
                # data struture
                if path:
                    path_elems = path.split('/')
                    # Remove empty string caused by trailing slashes
                    if path_elems[-1] == '':
                        del path_elems[-1]
                    # Traverse down the data tree for each element
                    for elem in path_elems[:-1]:
                        data_ref = data_ref.setdefault(elem, {})
                # Update the data or metadata with the body of the response
                for key in response_body:
                    data_ref[key] = response_body[key]

        # Otherwise, handle the exception, updating status information and reporting the error
        elif isinstance(response, Exception):
            if isinstance(response, requests.RequestException):
                self.status_code = 408 if isinstance(response, requests.Timeout) else 502
                self.error_string = str(response)
            else:
                self.status_code = 500
                self.error_string = str(response)

            logging.error(
                "Error: proxy target %s request failed (%d): %s ",
                self.name,
                self.status_code,
                self.error_string,
            )

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
