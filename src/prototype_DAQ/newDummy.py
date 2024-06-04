import logging
from concurrent import futures
import time
from odin.adapters.parameter_tree import ParameterTree, ParameterTreeError
from odin.adapters.adapter import ApiAdapter, ApiAdapterRequest, ApiAdapterResponse, request_types, response_types
from odin.util import decode_request_body
from tornado.concurrent import run_on_executor

class DummyAdapter(ApiAdapter):
    def __init__(self, **kwargs):
        self.test_value = 123
        super(DummyAdapter, self).__init__(**kwargs)
        self.dummyController = Dummy()
        logging.debug('DummyAdapter loaded')

    @response_types('application/json', default='application/json')
    def get(self, path, request):
        """Handle an HTTP GET request."""
        try:
            response = self.dummyController.get(path, False)
            status_code = 200
        except ParameterTreeError as param_error:
            response = {'error': str(param_error)}
            status_code = 400

        logging.debug(f'Sending {response} from DummyAdapter.get()')
        content_type = 'application/json'
        return ApiAdapterResponse(response, content_type=content_type, status_code=status_code)

    @request_types("application/json", "application/vnd.odin-native")
    @response_types("application/json", default="application/json")
    def put(self, path, request):
        try:
            body = decode_request_body(request)
            logging.debug(f"PUT request body: {body}")
            self.dummyController.set(path, body)
            response = self.dummyController.get(path, False)
            status_code = 200
        except ParameterTreeError as e:
            response = {'error': str(e)}
            status_code = 400

        logging.debug(f"PUT response: {response}")
        return ApiAdapterResponse(response, content_type='application/json', status_code=status_code)

    def cleanup(self):
        self.dummyController.cleanup()

class Dummy():
    executor = futures.ThreadPoolExecutor(max_workers=1)

    def __init__(self):
        self.background_task_enable = True
        self.background_task_interval = 1
        self.background_thread_counter = 0

        self.param_tree = ParameterTree({
            'background_task_counter': (lambda: self.background_thread_counter, None),
            'enable': (lambda: self.background_task_enable, self.set_task_enable),
            'interval': (lambda: self.background_task_interval, self.set_task_interval)
        })

        if self.background_task_enable:
            self.start_background_tasks()

    def set_task_interval(self, interval):
        """Set the background task interval."""
        logging.debug("Setting background task interval to %f", interval)
        self.background_task_interval = float(interval)
        
    def set_task_enable(self, enable):
        """Set the background task enable."""
        enable = bool(enable)
        if enable != self.background_task_enable:
            if enable:
                self.start_background_tasks()
            else:
                self.stop_background_tasks()

    def start_background_tasks(self):
        """Start the background tasks."""
        self.background_task_enable = True
        self.background_thread_task()

    def stop_background_tasks(self):
        """Stop the background tasks."""
        self.background_task_enable = False
    
    def get(self, path, with_metadata=False):
        """Get the parameter tree."""
        return self.param_tree.get(path, with_metadata)
    
    def set(self, path, value):
        """Set a parameter in the parameter tree."""
        return self.param_tree.set(path, value)
    
    def cleanup(self):
        """Clean up the Dummy instance."""
        logging.debug("Starting cleanup of Dummy adapter.")
        self.stop_background_tasks()

    @run_on_executor
    def background_thread_task(self):
        while self.background_task_enable:
            time.sleep(self.background_task_interval)
            if self.background_thread_counter < 10 or self.background_thread_counter % 20 == 0:
                logging.debug(
                    "Background thread task running, count = %d", self.background_thread_counter
                )
            self.background_thread_counter += 1

        logging.debug("Background thread task stopping")
