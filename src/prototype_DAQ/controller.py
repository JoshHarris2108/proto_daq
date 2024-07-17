import asyncio
import logging
from functools import partial
import os
import signal
import sys
from odin.adapters.parameter_tree import ParameterTree, ParameterTreeError
from odin.adapters.adapter import ApiAdapterRequest, ApiAdapterResponse

class PrototypeDAQController:
    """Class to manage the other adapters in the system."""

    def __init__(self):
        """Initialize the controller object."""
        self.test_value = "Test String from main IAC Adapter"
        self.expected_adapters = ["system_info", "dummy", "loki_proxy"]
        self.adapters = {}
        # Initialize the parameter tree after adapters are loaded
        self.param_tree = None

    def initialize_adapters(self, adapters):
        """Get access to all of the other adapters."""
        self.adapters = adapters
        logging.debug(f"Adapters loaded: {self.adapters}")      

        # for adapter in self.expected_adapters:
        #     if ["System_info"] not found:
        #         KeyboardInterrupt

        #assign adapters to self and check for loaded adpaters

        self.param_tree = ParameterTree({
            'test_value': (lambda: self.test_value, None),
            'dummy_enable': (lambda: self.iac_get('dummy', 'enable'), partial(self.iac_set, 'dummy', 'enable')),
            'loki_proxy': (lambda: self.iac_get('loki_proxy', 'node_1'), partial(self.iac_set, 'loki_proxy', 'node_1'))
        })

        self.sync_toggle_iac()
        logging.debug(f"testing iac_get: {self.iac_get('loki_proxy', 'node_1/acquisition/SYNC')}")
        logging.debug(f"testing kwargs iac_get: {self.iac_get('loki_proxy', 'node_1/acquisition/SYNC', param='SYNC')}")

    def get(self, path):
        """Get the parameter tree from the controller."""
        return self.param_tree.get(path)

    def set(self, path, data):
        """Set parameters in the parameter tree of the controller."""
        self.param_tree.set(path, data)

    def iac_get(self, adapter_name, path, **kwargs):
        """Generic IAC get method for synchronous adapters."""
        request = ApiAdapterRequest(None, accept="application/json")
        response = self.adapters[adapter_name].get(path, request)
        if response.status_code != 200:
            logging.debug(f"IAC GET failed for adapter {adapter_name}, path {path}: {response.data}")
        return response.data.get(kwargs['param']) if 'param' in kwargs else response.data

    def iac_set(self, adapter_name, path, param, data):
        """Generic IAC set method for synchronous adapters."""
        request = ApiAdapterRequest({param:data}, content_type="application/vnd.odin-native")
        response = self.adapters[adapter_name].put(path, request)
        if response.status_code != 200:
            logging.debug(f"IAC SET failed for adapter {adapter_name}, path {path}: {response.data}")

    def debugging_test_iac(self):
        logging.debug(f"Calling iac_get: {self.iac_get('loki_proxy', 'node_1/acquisition/SYNC')}")
        logging.debug(f'Calling Loki Proxy Directly: {(self.adapters["loki_proxy"].get("node_1", ApiAdapterRequest(None, accept="application/json"))).data}')
        #logging.debug(f'Calling iac_set: {self.iac_set("loki_proxy", "node_1", {"test_string":"string from controller function"})}')
        logging.debug(f'Calling iac_set: {self.iac_set("loki_proxy", "node_1/acquisition", "SYNC", True)}')
        # logging.debug(f'Calling iac_set: {self.iac_set("loki_proxy", "node_1/acquisition", {"SYNC":False})}')
        logging.debug(f"Calling iac_get: {self.iac_get('loki_proxy', 'node_1/acquisition/SYNC')}")

    def sync_toggle_iac(self):
        sync = (self.iac_get('loki_proxy', 'node_1/acquisition/SYNC'))['SYNC']
        logging.debug(f'SYNC value: {sync}')
        self.iac_set('loki_proxy', 'node_1/acquisition', 'SYNC', not(sync))
        logging.debug(f"SYNC value: {(self.iac_get('loki_proxy', 'node_1/acquisition/SYNC'))['SYNC']}")
        
class PrototypeDAQControllerError(Exception):
    """Simple exception class to wrap lower-level exceptions."""
    pass
