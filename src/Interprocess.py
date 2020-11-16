from abc import abstractmethod, ABC
import base64
import json
import sys
from sys import argv
from threading import Thread

"""
*
* Interprocess handling with bidirectional communication for child modules.
* Handles all parsing of all structured data into a consistent format for 
* transmission between client and parent processes. 
*
* All data is parsed as strings and encoded with base64 encoding to ensure 
* consistency between different processes and programming languages.
*
* All requests and responses are sent and received as JSON for simpler
* structuring of data.
*
"""

class InterprocessHandler(ABC):
    @abstractmethod
    def result_function(self, message: str) -> str:
        pass

    """ Starts the main loop thread """
    def loop(self) -> None:
        self.__flush_results("event.onreadyevent")
        while True:
            encodedRequest = sys.stdin.readline().strip()
            loop_thraed = Thread(target=self.__loop_function, args=[encodedRequest])
            loop_thraed.start()

    """ Actual function that is looped - Handles and parses all I/O """
    def __loop_function(self, encodedRequest) -> None:
        if encodedRequest == "": return

        request: str = base64.b64decode(encodedRequest).decode('utf-8')

        try:
            request: dict = json.loads(request)

        except json.decoder.JSONDecodeError:
            response: str = self.__parse_error(400, "Invalid request")
            self.__flush_results(response)
            return

        try:
            response: str = self.__parse_result(request)

        except AssertionError:
            response: str = self.__parse_error(500, "Unexpected type returned by result function", request = request)

        except Exception as e:
            response: str = self.__parse_result(500, f"Unexpected error occured: {e}", request = request)

        self.__flush_results(response)
            

    """ Passes the input into the result function and parses the response as a JSON string """
    def __parse_result(self, request: dict) -> str:
        result = self.result_function(request["message"])

        assert type(result) == str

        message = base64.b64encode(bytearray(result, 'utf-8')).decode('utf-8')

        response = dict()
        response["requestid"] = request["requestid"]
        response["status"] = 200
        response["message"] = message

        return json.dumps(response)
    
    """ Parses error message into a response as a JSON string """
    def __parse_error(self, error_code: int, error_message: str, request = None) -> str:
        message = base64.b64encode(bytearray(error_message, 'utf-8')).decode('utf-8')
        
        response = dict()
        response["requestid"] = request['requestid'] if request is not None else "-1"
        response["status"] = error_code
        response["message"] = message

        return json.dumps(response)

    """ Write results to output stream and flush """
    def __flush_results(self, response: str) -> None:
        sys.stdout.write(response + "\n")
        sys.stdout.flush()