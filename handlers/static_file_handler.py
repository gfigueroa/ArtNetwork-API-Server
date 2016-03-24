from handlers.base import BaseHandler
import logging
from settings import settings
import urls

logger = logging.getLogger('artmego.' + __name__)

# Global variables
FILE_EXPORT_PATH = settings['FILE_EXPORT_PATH']

class StaticFileHandlers(BaseHandler):

	"""
	Handler to serve static files from the server
	"""

	def data_received(self, chunk):
		pass

	def get(self, file_name):
		"""
		Fetches the required file from the static path and serves it as a downloadable file
		:param file_name: the name of the file that is going to be served
		"""
		pass