from handlers.base import BaseHandler
import logging
import urls

logger = logging.getLogger('artmego.' + __name__)


class IndexHandler(BaseHandler):
    """
    Root handler class with index to the various server functions
    """

    def data_received(self, chunk):
        pass

    def get(self, function=None):
        """
        Print main page
        """
        self.render("index.html")