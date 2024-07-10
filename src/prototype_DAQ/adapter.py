import logging
from odin.adapters.adapter import ApiAdapter, ApiAdapterRequest, ApiAdapterResponse, request_types, response_types
from tornado.escape import json_decode
from odin.adapters.parameter_tree import ParameterTreeError

from prototype_DAQ.controller import PrototypeDAQController, PrototypeDAQControllerError

class PrototypeDAQAdapter(ApiAdapter):
    """Prototype DAQ adapter class for inter-adapter communication."""

    def __init__(self, **kwargs):
        """Initialise the PrototypeDAQ object."""
        super(PrototypeDAQAdapter, self).__init__(**kwargs)
        self.protoDAQController = PrototypeDAQController()
        logging.debug("PrototypeDAQ Adapter Loaded")

    def initialize(self, adapters):
        """Initialize the adapter after it has been loaded."""
        self.adapters = dict((k, v) for k, v in adapters.items() if v is not self)
        self.protoDAQController.initialize_adapters(self.adapters)
        logging.debug("Received following dict of Adapters: %s", self.adapters)

    @response_types('application/json', default='application/json')
    def get(self, path, request):
        try:
            response = self.protoDAQController.get(path)
            status_code = 200
        except ParameterTreeError as e:
            response = {'error': str(e)}
            status_code = 400

        content_type = 'application/json'
        return ApiAdapterResponse(response, content_type=content_type, status_code=status_code)

    @request_types('application/json')
    @response_types('application/json', default='application/json')
    def put(self, path, request):
        content_type = 'application/json'
        try:
            data = json_decode(request.body)
            logging.debug(f"PUT request data: {data}")
            self.protoDAQController.set(path, data)
            response = self.protoDAQController.get(path)
            status_code = 200
        except PrototypeDAQControllerError as e:
            response = {'error': str(e)}
            status_code = 400
        except (TypeError, ValueError) as e:
            response = {'error': 'Failed to decode PUT request body: {}'.format(str(e))}
            status_code = 400

        logging.debug(f"PUT response: {response}")
        return ApiAdapterResponse(response, content_type=content_type, status_code=status_code)