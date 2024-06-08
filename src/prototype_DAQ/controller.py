import asyncio
import logging
from functools import partial
from odin.adapters.parameter_tree import ParameterTree, ParameterTreeError
from odin.adapters.adapter import ApiAdapterRequest, ApiAdapterResponse

class PrototypeDAQController:
    """Class to manage the other adapters in the system."""

    def __init__(self):
        """Initialize the controller object."""
        self.test_value = "This is a test value :):):):)"
        self.adapters = {}

        # Initialize the parameter tree after adapters are loaded
        self.param_tree = None

    def initialize_adapters(self, adapters):
        """Get access to all of the other adapters."""
        self.adapters = adapters
        logging.debug(f"Adapters loaded: {self.adapters}")
        #assign adapters to self and check for loaded adpaters

        self.param_tree = ParameterTree({
            'test_value': (lambda: self.test_value, None),
            'dummy_enable': (lambda: self.iac_get('dummy', 'enable'), partial(self.iac_set, 'dummy', 'enable')),
            'test_proxy': (self.async_wrapper(self.async_iac_get, 'test_proxy', 'node_1'), partial(self.async_iac_set, 'test_proxy', 'node_1'))
        })

    def get(self, path):
        """Get the parameter tree from the controller."""
        return self.param_tree.get(path)

    def set(self, path, data):
        """Set parameters in the parameter tree of the controller."""
        self.param_tree.set(path, data)

    def iac_get(self, adapter_name, path):
        """Generic IAC get method for synchronous adapters."""
        request = ApiAdapterRequest(None, accept="application/json")
        response = self.adapters[adapter_name].get(path, request)
        if response.status_code != 200:
            logging.debug(f"IAC GET failed for adapter {adapter_name}, path {path}: {response.data}")
        logging.debug(f'Raw response: {response.data}')
        return response.data[path]

    def iac_set(self, adapter_name, path, data):
        """Generic IAC set method for synchronous adapters."""
        request = ApiAdapterRequest(data)
        response = self.adapters[adapter_name].put(path, request)
        if response.status_code != 200:
            logging.debug(f"IAC SET failed for adapter {adapter_name}, path {path}: {response.data}")

    async def async_iac_get(self, adapter_name, path):
        """Generic IAC get method for asynchronous adapters."""
        request = ApiAdapterRequest(None, accept="application/json")
        response = await self.adapters[adapter_name].get(path, request)
        if response.status_code != 200:
            logging.debug(f"IAC GET failed for adapter {adapter_name}, path {path}: {response.data}")
        logging.debug(f'Raw response: {response.data}')
        return response.data[path]

    async def async_iac_set(self, adapter_name, path, data):
        """Generic IAC set method for asynchronous adapters."""
        request = ApiAdapterRequest(data)
        response = await self.adapters[adapter_name].put(path, request)
        if response.status_code != 200:
            logging.debug(f"IAC SET failed for adapter {adapter_name}, path {path}: {response.data}")

    def async_wrapper(self, func, *args, **kwargs):
        """Wrap an async function to make it callable in a synchronous context."""
        async def async_func():
            return await func(*args, **kwargs)
        
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(async_func())

class PrototypeDAQControllerError(Exception):
    """Simple exception class to wrap lower-level exceptions."""
    pass