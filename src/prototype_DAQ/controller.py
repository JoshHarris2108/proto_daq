import asyncio
import logging
from functools import partial
import os
import signal
import sys
from odin.adapters.parameter_tree import ParameterTree, ParameterTreeError
from odin.adapters.adapter import ApiAdapterRequest, ApiAdapterResponse
from dataclasses import dataclass

@dataclass
class Adapters:
    system_info: object
    dummy: object
   #loki_proxy: object

class PrototypeDAQController:
    """Class to manage the other adapters in the system."""

    def __init__(self):
        """Initialize the controller object."""
        # Adjusting logging level of the requests library, to prevent connectionpool debugging on every proxy request
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        self.test_value = "Test String from main IAC Adapter"
        # Initialize the parameter tree and adpater dataclass after adapters are loaded
        self.adapters = None 
        self.param_tree = None

    def initialize_adapters(self, adapters):
        """Get access to all of the other adapters."""
        self.adapters = Adapters(**adapters)
        logging.debug(f"Adapters loaded: {self.adapters}")      

        logging.debug(f"retrieveing dummy enable: {self.iac_get(self.adapters.dummy, 'enable', param='enable')}")

        self.param_tree = ParameterTree({
            'test_value': (lambda: self.test_value, None),
            'dummy_enable': (lambda: self.iac_get(self.adapters.dummy, 'enable', param='enable'), self.set_dummy_bgt)
        })
        self.sync_toggle_iac()

    def get(self, path):
        """Get the parameter tree from the controller."""
        return self.param_tree.get(path)

    def set(self, path, data):
        """Set parameters in the parameter tree of the controller."""
        self.param_tree.set(path, data)

    def iac_get(self, adapter, path, **kwargs):
        """Generic IAC get method for synchronous adapters."""
        request = ApiAdapterRequest(None, accept="application/json")
        response = adapter.get(path, request)
        if response.status_code != 200:
            logging.debug(f"IAC GET failed for adapter {adapter}, path {path}: {response.data}")
        return response.data.get(kwargs['param']) if 'param' in kwargs else response.data

    def iac_set(self, adapter, path, param, data):
        """Generic IAC set method for synchronous adapters."""
        request = ApiAdapterRequest({param: data}, content_type="application/vnd.odin-native")
        response = adapter.put(path, request)
        if response.status_code != 200:
            logging.debug(f"IAC SET failed for adapter {adapter}, path {path}: {response.data}")

    # def sync_toggle_iac(self):
    #     """
    #     Example function to demonstrate a very basic use case of the iac methods and proxy adapter.

    #     This function uses the iac get method to target a proxied adapter, to retrieve and store the value of its SYNC 
    #     attribute, the iac set method is then used to set the SYNC value to the inverse of its current value.
    #     """
    #     sync = (self.iac_get(self.adapters.loki_proxy, 'node_1/acquisition/SYNC', param='SYNC'))
    #     logging.debug(f'SYNC value: {sync}')
    #     self.iac_set(self.adapters.loki_proxy, 'node_1/acquisition', 'SYNC', not(sync))
    #     logging.debug(f"SYNC value: {(self.iac_get(self.adapters.loki_proxy, 'node_1/acquisition/SYNC', param='SYNC'))}")

    def set_dummy_bgt(self, enable):
        """
        Example function to demonstrate using the parameter tree to call a function that will use iac methods to
        adjust attributes on another loaded adapter.

        This function uses the iac set method to target the dummy adapter, and pass the enable value that is provided from the 
        paramater tre call into the enable attribute on the dummy adapter, stoping/starting the background task.
        """
        self.iac_set(self.adapters.dummy, '', 'enable', enable)

class PrototypeDAQControllerError(Exception):
    """Simple exception class to wrap lower-level exceptions."""
    pass