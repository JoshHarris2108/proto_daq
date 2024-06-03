import logging
from odin.adapters.parameter_tree import ParameterTreeError
from odin.adapters.adapter import ApiAdapter, ApiAdapterRequest, ApiAdapterResponse, request_types, response_types

class PrototypeDAQController():
    """Class to manage the other adapters in the system."""

    def __init__(self):
        """Initialize the controller object."""
        self.adapters = {}

    def initialize_adapters(self, adapters):
        """Get access to all of the other adapters."""
        self.adapters = adapters
        logging.debug(f"Adapters loaded: {self.adapters}")

    def get(self, path):
        """Get the parameter tree from the appropriate adapter."""
        adapter_name, param_path = self._parse_path(path)
        if adapter_name in self.adapters:
            # Create an ApiAdapterRequest object to pass to the adapter's get method
            request = ApiAdapterRequest(None, accept="application/json")
            # Call the get method on the target adapter
            return self.adapters[adapter_name].get(param_path, request).data
        else:
            # Error handkling if adapter is not found
            raise ParameterTreeError(f"Adapter {adapter_name} not found")

    def set(self, path, data):
        """Set parameters in the parameter tree of the appropriate adapter."""
        adapter_name, param_path = self._parse_path(path)
        if adapter_name in self.adapters:
            # create and pass the ApiAdapterRequest object to the correct adapter
            request = ApiAdapterRequest(data)
            self.adapters[adapter_name].put(param_path, request)
        else:
            raise ParameterTreeError(f"Adapter {adapter_name} not found")

    def _parse_path(self, path):
        """Private method to parse the adapter name and parameter path from the URI path, 
        to route the requests to the correct adapter and path"""
        parts = path.strip('/').split('/')
        if len(parts) < 1:
            raise ParameterTreeError(f"Invalid path format. Expected /<adapter>/<param_path>. Got: {path}")
        adapter_name = parts[0]
        param_path = '/'.join(parts[1:]) if len(parts) > 1 else ""
        return adapter_name, param_path


class PrototypeDAQControllerError(Exception):
    """Simple exception class to wrap lower-level exceptions."""
    pass
