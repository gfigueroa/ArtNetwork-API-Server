"""
Module to maintain all scheduled tasks in the ArtMeGo web server.
"""
import logging
from settings import settings
import tornado.ioloop
import time
import glob
import os

logger = logging.getLogger('artmego.' + __name__)

FILE_DELETE_INTERVAL_HOURS = settings['FILE_DELETE_INTERVAL_HOURS']
FILE_EXPORT_LIFETIME_HOURS = settings['FILE_EXPORT_LIFETIME_HOURS']
FILE_EXPORT_PATH = settings['FILE_EXPORT_PATH']

class Scheduler(object):
	"""
	Class to handle the execution of all scheduled tasks in the server
	"""

	def __init__(self, main_loop):
		"""
		:param main_loop: the main loop of the Tornado application instance
		:return:
		"""
		self.main_loop = main_loop

	def run_scheduled_tasks(self):
		"""
		Run all scheduled tasks
		:return:
		"""
		# Delete export files
		self.run_delete_export_files()

	def run_delete_export_files(self):
		interval_ms = FILE_DELETE_INTERVAL_HOURS * 60 * 60 * 1000
		scheduler = tornado.ioloop.PeriodicCallback(delete_export_files, interval_ms, io_loop=self.main_loop)
		scheduler.start()


def delete_export_files():
	"""
	Delete expired export files found in the FILE_EXPORT_PATH
	Expiration time is defined in the settings for FILE_EXPORT_LIFETIME_HOURS
	:return:
	"""
	logger.debug("Deleting export files...")
	files = glob.glob(FILE_EXPORT_PATH + "/*.csv") if glob.glob(FILE_EXPORT_PATH + "/*.csv") is not None else []
	for file in files:
		now = time.time()
		creation_time = os.path.getctime(file)
		delta_seconds = now - creation_time
		delta_hours = (delta_seconds) / (60 * 60)
		if delta_hours > FILE_EXPORT_LIFETIME_HOURS:
			os.remove(file)