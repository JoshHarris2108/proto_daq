from functools import partial
import logging
from odin.adapters.parameter_tree import ParameterTree, ParameterTreeError
from odin.adapters.adapter import ApiAdapter, ApiAdapterRequest, ApiAdapterResponse, request_types, response_types

class PrototypeDAQController():
    """Class to manage the other adapters in the system."""

    def __init__(self):
        """Initialize the controller object."""
        self.test_value = "This is a test value :):):):)"
        self.adapters = {}

        self.param_tree = ParameterTree({
            'test_value': (lambda: self.test_value, None),
            'dummy_state': (partial(self.get_dummy_state), partial(self.set_dummy_state))
        })

    def initialize_adapters(self, adapters):
        """Get access to all of the other adapters."""
        self.adapters = adapters
        logging.debug(f"Adapters loaded: {self.adapters}")
  
    def get(self, path):
        """Get the parameter tree from the appropriate adapter or the controller."""
        adapter_name, param_path = self._parse_path(path)
        
        if adapter_name == 'self':
            # Access the controller's own parameter tree
            return self.param_tree.get(param_path)
        elif adapter_name in self.adapters:
            # Create an ApiAdapterRequest object to pass to the adapter's get method
            request = ApiAdapterRequest(None, accept="application/json")
            # Call the get method on the target adapter
            return self.adapters[adapter_name].get(param_path, request).data
        else:
            # Error handkling if adapter is not found
            raise ParameterTreeError(f"Adapter {adapter_name} not found")

    def set(self, path, data):
        """Set parameters in the parameter tree of the appropriate adapter or the controller."""
        adapter_name, param_path = self._parse_path(path)
        
        if adapter_name == 'self':
            # Access the controller's own parameter tree
            self.param_tree.set(param_path, data)
        elif adapter_name in self.adapters:
            # create and pass the ApiAdapterRequest object to the correct adapter
            request = ApiAdapterRequest(data)
            self.adapters[adapter_name].put(param_path, request)
        else:
            raise ParameterTreeError(f"Adapter {adapter_name} not found")

    def _parse_path(self, path):
        """Private method to parse the adapter name and parameter path from the URI path, 
        to route the requests to the correct adapter and path"""
        parts = path.strip('/').split('/')
        
        # If the path is empty, it's a request to the root of the controller
        if len(parts) == 0:
            raise ParameterTreeError("Invalid path format. Path is empty")
        
        adapter_name = parts[0] if parts[0] else 'self'
        param_path = '/'.join(parts[1:]) if len(parts) > 1 else ""
        
        return adapter_name, param_path

    def get_dummy_state(self):
        """Get the enable state from the dummy adapter."""
        if 'dummy' in self.adapters:
            # Call the dummy adapter's get method and return the appropriate part of the response
            response = self.adapters['dummy'].dummyController.get('enable', False)
            if isinstance(response, dict) and 'enable' in response:
                return response['enable']
            else:
                return response
        else:
            return {"state": "Adapter not initialized"}

    def set_dummy_state(self, data):
        """Set the state on the dummy adapter."""
        if 'dummy' in self.adapters:
            # Ensure data is in the correct format before sending it to the dummy adapter
            if isinstance(data, dict) and 'dummy_state' in data:
                value = data['dummy_state']
            else:
                value = data
            self.adapters['dummy'].dummyController.set('enable', value)
        else:
            raise ParameterTreeError("Dummy adapter is not initialized")

class PrototypeDAQControllerError(Exception):
    """Simple exception class to wrap lower-level exceptions."""
    pass
