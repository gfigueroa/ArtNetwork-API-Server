import base64
import json
from urllib import urlencode
from tornado import httpclient
from tornado import gen
from tornado import escape
import tornado.web
import logging

logger = logging.getLogger('artmego.' + __name__)

# Handler result error codes
RESULT_ERROR_CODES = {
	'0001': "internal server error",
	'0002': "inexistent resource",
	'0003': "missing arguments",
	'0004': "not implemented",
    '0005': "authentication error",
    '0006': "wrong argument value",
    '0007': "user inexistent",
    '0008': "user already exists",
    '0009': "unauthorized",
	'0010': "insufficient funds",
}

def construct_error_json(error_code):
	"""
	Constructs a Json object representing an error, given the error code, in the following format:
	{"error_code":"0001","message":"server_error"}
	:param error_code: the code number as a string, e.g. "0001"
	:return: a Json object with the error code and reason
	"""
	reason = RESULT_ERROR_CODES[error_code]
	json_object = {'response': "fail",'error_code': error_code, 'reason': reason}
	return json_object


class BaseHandler(tornado.web.RequestHandler):
	"""
	A class to collect common handler methods - all other handlers should
    subclass this one.
    """

	def data_received(self, chunk):
		pass

	def load_json(self):
		"""
	        Load JSON from the request body and store them in
	        self.request.arguments, like Tornado does by default for POSTed form
	        parameters.

	        If JSON cannot be decoded, raises an HTTPError with status 400.
	        """
		try:
			self.request.arguments = json.loads(self.request.body)
		except ValueError:
			msg = "Could not decode JSON: %s" % self.request.body
			logger.debug(msg)
			raise tornado.web.HTTPError(400, msg)


	def get_json_argument(self, name, default=None):
		"""
	        Find and return the argument with key 'name' from JSON request data.
	        Similar to Tornado's get_argument() method.
	        """
		if default is None:
			default = self._ARG_DEFAULT
		if not self.request.arguments:
			self.load_json()
		if name not in self.request.arguments:
			if default is self._ARG_DEFAULT:
				msg = "Missing argument '%s'" % name
				logger.debug(msg)
				raise tornado.web.HTTPError(400, msg)
			logger.debug("Returning default argument %s, as we couldn't find "
			             "'%s' in %s" % (default, name, self.request.arguments))
			return default
		arg = self.request.arguments[name]
		logger.debug("Found '%s': %s in JSON arguments" % (name, arg))
		return arg


	def async_request(self, callback, server_url, method=u'GET', headers=None, body=None, **kwargs):
		"""
	        Make async request to server
	        :param callback: callback to pass results
	        :param server_url: path to required API
	        :param method: HTTP method to use, default - GET
	        :param body: HTTP request body for POST request, default - None
	        :param headers: HTTP request headers, default - None
	        :return: None
	        """
		args = {}

		logger.info("async_request test...")

		if kwargs:
			args.update(kwargs)

		url = '%s?%s' % (server_url, urlencode(args))
		request = tornado.httpclient.HTTPRequest(url, method, headers=headers, body=body)

		http = tornado.httpclient.AsyncHTTPClient()
		response = yield tornado.gen.Task(http.fetch, request)

		if response.error:
			logging.warning("Error response %s fetching %s", response.error, response.request.url)
			callback(None)
			return
		data = tornado.escape.json_decode(response.body) if response else None
		callback(data)


def require_basic_auth(handler_class):
	"""
    Decorator for requiring basic authentication.
    :param handler_class: the decorated class
    :return:
    """
	# Should return the new _execute function, one which enforces
	# authentication and only calls the inner handler's _execute() if
	# it's present.
	def wrap_execute(handler_execute):
		# I've pulled this out just for clarity, but you could stick
		# it in _execute if you wanted.  It returns True iff
		# credentials were provided.  (The end of this function might
		# be a good place to see if you like their username and
		# password.)
		def require_basic_auth(handler, kwargs):
			auth_header = handler.request.headers.get('Authorization')
			if auth_header is None or not auth_header.startswith('Basic '):
				# If the browser didn't send us authorization headers,
				# send back a response letting it know that we'd like
				# a username and password (the "Basic" authentication
				# method).  Without this, even if you visit put a
				# username and password in the URL, the browser won't
				# send it.  The "realm" option in the header is the
				# name that appears in the dialog that pops up in your
				# browser.
				handler.set_status(401)
				handler.set_header('WWW-Authenticate', 'Basic realm=Restricted')
				handler._transforms = []
				handler.finish()
				return False
			# The information that the browser sends us is
			# base64-encoded, and in the format "username:password".
			# Keep in mind that either username or password could
			# still be unset, and that you should check to make sure
			# they reflect valid credentials!
			auth_decoded = base64.decodestring(auth_header[6:])
			username, password = auth_decoded.split(':', 2)
			kwargs['basicauth_user'], kwargs['basicauth_pass'] = username, password
			return True

		# Since we're going to attach this to a RequestHandler class,
		# the first argument will wind up being a reference to an
		# instance of that class.
		def _execute(self, transforms, *args, **kwargs):
			if not require_basic_auth(self, kwargs):
				return False
			return handler_execute(self, transforms, *args, **kwargs)

		return _execute

	handler_class._execute = wrap_execute(handler_class._execute)
	return handler_class


def callback(write):
	"""
	A decorator function to wrap a callback function around the original JSON object for JSONP.
	This decorator must be used on the write() function in a RequestHandler.
	:param write: the original write() function
	:return: a decorated write() function with a callback function wrapping
	"""
	def new_write(self, chunk):
		callback = self.get_argument('callback', None)
		if callback is not None:
			chunk = "{0}({1})".format(callback, chunk)  # Wrap Json result around callback function
			self.set_header('content-type', "application/javascript; charset=utf-8")  # Change content type

		write(self, chunk)

	return new_write