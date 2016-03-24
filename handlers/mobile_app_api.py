# coding=utf-8
"""
Module to handle access to the Mobile APP web services.
"""

import json
import logging
from random import randint

from tornado import httpclient
from tornado.httputil import HTTPHeaders

import lib.db_crud

from handlers.base import BaseHandler, callback
from handlers.base import construct_error_json
from lib import security
from lib.exceptions import InexistentResourceError, MissingArgumentsError, UnauthorizedError, UserExistsError, \
	UserInexistentError, WrongArgumentValueError, AuthenticationError, InsufficientFundsError
from settings import settings

from lib.utils import DecimalEncoder, deprecated

# Global variables

logger = logging.getLogger('artmego.' + __name__)
db_crud = lib.db_crud


# @require_basic_auth
class MobileAppAPIHandler(BaseHandler):
	"""
	A class to handle all calls to web services related to Power Metering (電量報表).
	"""

	# Private attributes
	_static_headers = HTTPHeaders({"content-type": "application/json; charset=utf-8"})

	def initialize(self, require_token=False):
		"""
		:param require_token: whether the requested web service required a JWT token or not, default=False
		:return:
		"""
		self.require_token = require_token
		for header in self._static_headers:
			self.set_header(header, self._static_headers[header])

	def data_received(self, chunk):
		pass

	@callback
	def write(self, chunk):
		super(MobileAppAPIHandler, self).write(chunk)

	def get(self, **kwargs):
		"""
		Fetches the required web service (a dictionary) using the GET method and displays it as a Json object
		:param **kwargs: this includes the basicauth_user and basicauth_pass
		:return: the result of a web service in Json format
		"""

		# Basic user authentication (override)
		basicauth_user = kwargs.get('basicauth_user')
		basicauth_pass = kwargs.get('basicauth_pass')

		ws_name = self.request.path[1:]  # original path is like "/banner"
		arguments = self.request.arguments

		try:
			# First, check if it requires a JWT token
			if self.require_token:
				token_header = self.request.headers['Authorization']  # Produces KeyError if missing
				token = token_header.split(' ')[1]
				user_id = security.authenticate_user_token(token)
			else:
				user_id = None

			result = get_ws(ws_name, arguments, user_id)
		except httpclient.HTTPError, e:
			if e.code == 401:  # Authentication error
				result = construct_error_json("0005")
			else:
				result = construct_error_json("0001")
		except KeyError:
			result = construct_error_json("0009")  # No Authorization header
		except InexistentResourceError:
			result = construct_error_json("0002")
		except MissingArgumentsError:
			result = construct_error_json("0003")
		except NotImplementedError:
			result = construct_error_json("0004")
		except AuthenticationError:
			result = construct_error_json("0005")
		except WrongArgumentValueError:
			result = construct_error_json("0006")
		except UserInexistentError:
			result = construct_error_json("0007")
		except UserExistsError:
			result = construct_error_json("0008")
		except UnauthorizedError:
			result = construct_error_json("0009")
		except Exception, e:
			logger.log(logging.ERROR, "Error in mobile_app_api post(): {0}".format(e.message))
			result = construct_error_json("0001")

		# Convert result to JSON
		result = json.dumps(result, cls=DecimalEncoder)

		self.write(result)

	def post(self, **kwargs):
		"""
		Fetches the required web service (a dictionary) using the POST method and displays it as a Json object
		:param **kwargs: this includes the basicauth_user and basicauth_pass
		:return: the result of a web service in Json format
		"""

		# Basic user authentication (override)
		basicauth_user = kwargs.get('basicauth_user')
		basicauth_pass = kwargs.get('basicauth_pass')

		ws_name = self.request.path[1:]  # original path is like "/login"
		arguments = self.request.arguments
		request_body = self.request.body

		try:
			# First, check if it requires a JWT token
			if self.require_token:
				try:
					token_header = self.request.headers['Authorization']  # Produce KeyError if not provided
					token = token_header.split(' ')[1]
					user_id = security.authenticate_user_token(token)
				except KeyError, e:
					# JWT token is optional for some web services (i.e. login)
					if ws_name != "login":
						raise e
					else:
						user_id = None
			else:
				user_id = None

			result = post_ws(ws_name, arguments, request_body, user_id)
		except httpclient.HTTPError, e:
			if e.code == 401:  # Authentication error
				result = construct_error_json("0005")
			else:
				result = construct_error_json("0001")
		except KeyError:
			result = construct_error_json("0009")  # No Authorization header
		except InexistentResourceError:
			result = construct_error_json("0002")
		except MissingArgumentsError:
			result = construct_error_json("0003")
		except NotImplementedError:
			result = construct_error_json("0004")
		except AuthenticationError:
			result = construct_error_json("0005")
		except WrongArgumentValueError:
			result = construct_error_json("0006")
		except UserInexistentError:
			result = construct_error_json("0007")
		except UserExistsError:
			result = construct_error_json("0008")
		except UnauthorizedError:
			result = construct_error_json("0009")
		except InsufficientFundsError:
			result = construct_error_json("0010")
		except Exception, e:
			logger.log(logging.ERROR, "Error in mobile_app_api post(): {0}".format(e.message))
			result = construct_error_json("0001")

		# Convert result to JSON
		result = json.dumps(result, cls=DecimalEncoder)

		self.write(result)


################################### GET REQUESTS ###################################


def get_ws(ws_name, arguments, user_id=None):
	"""
	Get a GET web service given its name and arguments and return it as a dictionary
	:param ws_name: the name of the web service to access
	:param arguments: the URL arguments for the web service
	:param user_id: the user_id of the requesting User (when applicable)
	:return: a dictionary with the requested web service information
	"""

	try:
		# Common arguments

		if ws_name == "banner_list":
			return home_banner_list()
		elif ws_name == "home_artwork":
			sorting_rule = int(arguments['sorting_rule'][0])
			limit = int(arguments['limit'][0])
			offset = int(arguments['offset'][0])
			if sorting_rule == 5:
				location = arguments['location'][0]
			else:
				location = None
			return home_artwork(sorting_rule, limit, offset, user_id, location)
		elif ws_name == "artwork_page":
			artwork_id = long(arguments['artwork_id'][0])
			return artwork_page(artwork_id, user_id)
		elif ws_name == "artwork_auction":
			artwork_id = long(arguments['artwork_id'][0])
			return artwork_auction(artwork_id, user_id)
		elif ws_name == "artist_page":
			artist_id = long(arguments['artist_id'][0])
			sorting_rule = int(arguments['sorting_rule'][0])
			limit = int(arguments['limit'][0])
			offset = int(arguments['offset'][0])
			return artist_page(artist_id, sorting_rule, limit, offset, user_id)
		elif ws_name == "gallery_auction_page":
			id = long(arguments['id'][0])
			type = arguments['type'][0]
			return gallery_auction_page(id, type, user_id)
		elif ws_name == "artist_list":
			limit = int(arguments['limit'][0])
			offset = int(arguments['offset'][0])
			return artist_list(limit, offset)
		elif ws_name == "gallery_list":
			limit = int(arguments['limit'][0])
			offset = int(arguments['offset'][0])
			return gallery_list(limit, offset)
		elif ws_name == "auction_house_list":
			limit = int(arguments['limit'][0])
			offset = int(arguments['offset'][0])
			return auction_house_list(limit, offset)
		elif ws_name == "label_list":
			limit = int(arguments['limit'][0])
			offset = int(arguments['offset'][0])
			return label_list(limit, offset)
		elif ws_name == "about_me":
			top_n_labels = int(arguments['top_n_labels'][0])
			top_n_artists = int(arguments['top_n_artists'][0])
			return about_me(user_id, top_n_labels, top_n_artists)
		elif ws_name == "following_lists":
			limit = int(arguments['limit'][0])
			offset = int(arguments['offset'][0])
			return following_lists(user_id, limit, offset)
		elif ws_name == "user_auction_list":
			sorting_rule = int(arguments['sorting_rule'][0])
			return user_auction_list(user_id, sorting_rule)
		else:
			raise InexistentResourceError()
	except KeyError, e:
		raise MissingArgumentsError()
	except ValueError, e:
		raise WrongArgumentValueError('')
	except Exception, e:
		raise e


def home_banner_list():
	"""
	2A - Home Banner list (GET)
	Obtain list of Banners to display in Home screen based on the banners' start_time and end_time.
	URL: http://host:port/banner_list
	:return: {
			  "response":"success",
			  "banner_list":[
			  {
			    "banner_name":"name",
			    "banner_text":"text",
			    "banner_image_path":"path/to/image"
			  },
			  ...
			  ],
			  "count":12
			}
	"""

	banner_list = db_crud.get_banner_list()

	banner_dictionary_list = []
	for banner in banner_list:
		banner_dictionary = dict(banner_name=banner.banner_name,
		                         banner_text=banner.banner_text,
		                         banner_image_path=banner.image.image_path if banner.image is not None else None)
		banner_dictionary_list.append(banner_dictionary)

	result = dict(reponse="success",
				  banner_list=banner_dictionary_list,
				  count=len(banner_dictionary_list))

	return result


def home_artwork(sorting_rule, limit, offset, user_id, location=None):
	"""
	2B - Home Artwork list (GET)
	List of Artwork to display in Home screen, sorted by one of several rules.
	URL: http://host:port/home_artwork?sorting_rule=1&limit=10&offset=10[&location=long,lat]
	:param sorting_rule:
		1: most popular Artwork
		2: my watched Critics
		3: my watched Artists
		4: my watched Artwork
		5: nearby Galleries (requires location)
	:param limit: the max number of rows to return (0 for no limit)
	:param offset: the offset (starting point) for the list. E.g. if offset=10, the list will begin at row 11
	:param user_id: the user_id of the requesting User
	:param location: "lat,long" (optional) e.g. 24.971059,121.241765
	:return: {
			  "response":"success",
			  "artwork_list":[
			  {
				"display_order": 0,
				"artwork_id":"abc123",
				"artwork_name":"name",
				"artwork_date":"2015-2016",
				"artwork_image_path":"path/to/image",
				"artist_id":1203,
				"artist_name":"name",
				"artist_image_path":"path/to/image",
				"following":false,
				"owner_id":1243,
				"owner_type":"GALLERY",
				"owner_name":"name",
				"owner_image_path":"path/to/image",
				"follower_count":135,
				"critique_count":25
			  },
			  ...
			  ],
			  "count":12
			}
	"""

	# Get Artwork list and Images
	artwork_list, artwork_image_dictionary = \
		db_crud.get_artwork_list(sorting_rule, None, limit, offset, user_id, location)

	# Build dictionaries
	artwork_dictionary_list = []
	for i in range(0, len(artwork_list)):
		artwork = artwork_list[i]
		artwork_images = artwork_image_dictionary[artwork]

		if len(artwork_images) > 0:
			rand_image_index = randint(0, len(artwork_images) - 1)
			rand_image = artwork_images[rand_image_index]
		else:
			rand_image = None

		artist, artist_image = db_crud.get_artist(artwork.artist_user_id)

		# Owner
		owner, owner_type, owner_image = db_crud.get_artwork_owner(artwork)

		if owner is None:
			owner_id = None
			owner_type = None
			owner_name = None
		else:
			owner_id = owner.user_id

			if owner_type.lower() == "buyer":
				owner_name = owner.buyer_nickname
			elif owner_type.lower() == "artist":
				owner_name = owner.artist_nickname
			elif owner_type.lower() == "auction_house":
				owner_name = owner.auction_house_name
			else:
				owner_name = owner.gallery_name

		# Following or not
		following = db_crud.artwork_is_followed(user_id, artwork.artwork_id)

		artwork_dictionary = dict(display_order=i,
								  artwork_id=artwork.artwork_id,
								  artwork_name=artwork.artwork_name,
								  artwork_date=artwork.artwork_date,
								  artwork_image_path=rand_image.image_path if rand_image is not None else None,
								  artist_id=artist.user_id,
								  artist_name=artist.artist_nickname,
								  artist_image_path=artist_image.image_path if artist_image is not None else None,
								  following=following,
								  owner_id=owner_id,
								  owner_type=owner_type,
								  owner_name=owner_name,
								  owner_image_path=owner_image.image_path if owner_image is not None else None,
								  follower_count=artwork.artwork_followed_count,
								  critique_count=artwork.artwork_critique_count)
		artwork_dictionary_list.append(artwork_dictionary)

	result = dict(response="success",
				  artwork_list=artwork_dictionary_list,
				  count=len(artwork_list))

	return result


def artwork_page(artwork_id, user_id):
	"""
	3A - Artwork page and Critique list (GET)
	A particular Artwork's main page.
	Contains additional information as well as a list of Critiques that have been made to this Artwork.
	URL: http://host:port/artwork_page?artwork_id=1203
	:param artwork_id: the id of the Artwork
	:param user_id: the user_id of the requesting User
	:return: {
			  "response":"success",
			  "artwork":
			  {
			    "artwork_id":123,
			    "artwork_name":"name",
			    "artwork_date":"1870-1871,
			    "artwork_image_path":"path/to/image",
			    "artwork_blog_url":"http://www.page.com",
			    "artist_id":1203,
			    "artist_name":"name",
			    "following":false,
			    "owner_id":1243,
			    "owner_type":"GALLERY",
			    "owner_name":"name",
			    "owner_image_path":"path/to/image",
			    "follower_count":135,
			    "critique_count":25
			  },
			  "critique_list":[
			  {
			    "critique_date":"2015-04-23",
			    "critique_point_price":500,
			    "critique_text":"text",
			    "critique_upvote_count":51,
			    "critique_downvote_count":4,
			    "critique_vote_type":"L",
			    "critique_purchased":true,
			    "critic_id":4324,
			    "critic_name":"name",
			    "critic_follower_count":1025
			  },
			  ...
			  ],
			  "count":1
			}
	"""

	# Get Artwork and Images
	artwork, artwork_images = db_crud.get_artwork(artwork_id)

	# Check that the Artwork exists
	if artwork is None:
		raise InexistentResourceError()

	# Check that the Artwork is available
	if artwork.artwork_status.lower() != "available":
		raise UnauthorizedError()

	if len(artwork_images) > 0:
		rand_image_index = randint(0, len(artwork_images) - 1)
		rand_image = artwork_images[rand_image_index]
	else:
		rand_image = None

	# Get Critiques
	critiques = db_crud.get_critique_list(artwork.artwork_id)

	# Owner
	owner, owner_type, owner_image = db_crud.get_artwork_owner(artwork)

	if owner is None:
		owner_id = None
		owner_type = None
		owner_name = None
	else:
		owner_id = owner.user_id

		if owner_type.lower() == "buyer":
			owner_name = owner.buyer_nickname
		elif owner_type.lower() == "artist":
			owner_name = owner.artist_nickname
		elif owner_type.lower() == "auction_house":
			owner_name = owner.auction_house_name
		else:
			owner_name = owner.gallery_name

	# Following or not
	following = db_crud.artwork_is_followed(user_id, artwork.artwork_id)

	# Build dictionaries
	artwork_dictionary = dict(artwork_id=artwork.artwork_id,
	                          artwork_name=artwork.artwork_name,
	                          artwork_date=artwork.artwork_date,
	                          artwork_image_path=rand_image.image_path if rand_image is not None else None,
	                          artwork_blog_url=artwork.artwork_blog_url,
	                          artist_id=artwork.artist.user_id,
	                          artist_name=artwork.artist.artist_nickname,
	                          following=following,
	                          owner_id=owner_id,
	                          owner_type=owner_type,
	                          owner_name=owner_name,
	                          owner_image_path=owner_image.image_path if owner_image is not None else None,
	                          follower_count=artwork.artwork_followed_count,
	                          critique_count=artwork.artwork_critique_count
	                          )

	critique_dictionary_list = []
	for critique in critiques:

		# Check if Critique is purchased
		critique_purchased = db_crud.critique_purchased(user_id, artwork_id, critique.critic_user_id)
		if critique_purchased:
			critique_text = critique.critique_text
		else:
			critique_text = ""

		# Check Critique vote type
		critique_liked = db_crud.get_critique_vote_type(user_id, artwork_id, critique.critic_user_id)

		critique_dictionary = \
			dict(critique_date=critique.critique_creation_time.strftime(settings['DATE_DISPLAY_FORMAT']),
			     critique_point_price=critique.critique_point_price,
			     critique_text=critique_text,
			     critique_upvote_count=critique.critique_upvote_count,
			     critique_downvote_count=critique.critique_downvote_count,
			     critique_vote_type=critique_liked,
			     critique_purchased=critique_purchased,
			     critic_id=critique.critic.user_id,
			     critic_name=critique.critic.critic_nickname,
			     critic_follower_count=critique.critic.critic_followed_count
			     )
		critique_dictionary_list.append(critique_dictionary)

	result = dict(response="success",
	              artwork=artwork_dictionary,
	              critique_list=critique_dictionary_list,
	              count=1)

	return result


def artwork_auction(artwork_id, user_id):
	"""
	4A - Artwork Auction page (GET)
	Current Auction page for a given Artwork. Displays current Auction information and time left for Auction.
	If the given Artwork has no current Auction, then an empty result is returned.
	URL: http://host:port/artwork_auction?artwork_id=123
	:param artwork_id: the id of the Artwork
	:param user_id: the user_id of the requesting User
	:return: {
			  "response":"success",
			  "artwork_auction":
			  {
			    "artwork_auction_id":123,
			    "minimum_bid":800.0,
			    "current_bid":1000.0,
			    "bid_increment":100.0,
			    "high_bidder_name":"pa****",
			    "bid_count":3,
			    "auction_starting_time":"2015-08-21 13:10:00",
			    "auction_ending_time":"2015-08-21 13:10:00",
			  },
			  "count":1
			}
	"""

	# Get Artwork Auction
	artwork_auction = db_crud.get_artwork_auction(artwork_id)

	if artwork_auction is None:
		raise InexistentResourceError()

	# Build Artwork Auction dictionary
	current_bid = artwork_auction.current_bid
	current_bid_amount = current_bid.artwork_auction_bid_amount if current_bid is not None else 0
	high_bidder = current_bid.buyer if current_bid is not None else None
	high_bidder_name = high_bidder.buyer_nickname if high_bidder is not None else None
	if high_bidder is not None:
		if high_bidder.user.user_id == user_id:
			user_is_high_bidder = True
		else:
			user_is_high_bidder = False
	else:
		user_is_high_bidder = False
	bid_count = len(artwork_auction.artwork_auction_bids)

	artwork_auction_dictionary = dict(artwork_auction_id=artwork_auction.artwork_auction_id,
	                                  minimum_bid=artwork_auction.artwork_auction_minimum_bid,
	                                  current_bid=current_bid_amount,
	                                  bid_increment=artwork_auction.artwork_auction_bid_increment,
	                                  high_bidder_name=high_bidder_name,
	                                  user_is_high_bidder = user_is_high_bidder,
	                                  bid_count=bid_count,
	                                  auction_starting_time=artwork_auction.artwork_auction_start_time.strftime(
		                                  settings['DATETIME_DISPLAY_FORMAT']),
	                                  auction_ending_time=artwork_auction.artwork_auction_end_time.strftime(
		                                  settings['DATETIME_DISPLAY_FORMAT'])
	                                  )

	result = dict(response="success",
	              artwork_auction=artwork_auction_dictionary,
	              count=1)

	return result


def artist_page(artist_id, sorting_rule, limit, offset, user_id):
	"""
	5A - Artist fan page (GET)
	Fan page for Artist. Includes an image, description and a list of Artwork.
	URL: http://host:port/artist_page?artist_id=1203&sorting_rule=1&limit=0&offset=0
	:param artist_id: the id of the Artist
	:param sorting_rule:
		1: most popular Artwork
		2: latest Artwork (uploaded)
		3: most Critiques
		4: highest to lowest price
		5: lowest to highest price
		6: most popular critique
	:param limit: the max number of rows to return for the artwork_list (0 for no limit)
	:param offset: the offset (starting point) for the artwork_list. E.g. if offset=10, the list will begin at row 11
	:param user_id: the user_id of the requesting User
	:return: {
			  "response":"success",
			  "artist":
			  {
				"artist_name":"name",
				"artist_description":"text",
				"artist_image_path":"path/to/image",
				"following":false,
				"follower_count":158,
				"followers":[
				{
				  "follower_image_path":"path/to/image"
				},
				...
				]
			  },
			  "artwork_list":[
			  {
				"artwork_id":"abc123",
				"artwork_name":"name",
				"artwork_date":"1870-1871",
				"artwork_image_path":"path/to/image",
				"following":false,
				"owner_id":1243,
				"owner_type":"GALLERY",
				"owner_name":"name",
				"owner_image_path":"path/to/image",
				"follower_count":135,
				"critique_count":25
			  },
			  ...
			  ],
			  "count":1
			}
	"""

	# Get Artist and Image
	artist, artist_image = db_crud.get_artist(artist_id)

	if artist is None:
		raise InexistentResourceError()

	# Get followers (list of Buyer)
	followers = db_crud.get_artist_followers(artist_id, 5, 0)

	# Get Artwork list
	# First, map the sorting rule for db_crud.get_artwork_list
	sorting_rule_map = {
		1: 1,
		2: 6,
		3: 7,
		4: 8,
		5: 9,
		6: 10
	}
	sorting_rule = sorting_rule_map[sorting_rule]

	artwork_list, artwork_image_dictionary = db_crud.get_artwork_list(sorting_rule, artist_id, limit, offset, user_id)

	# Build dictionaries
	artwork_dictionary_list = []
	for i in range(0, len(artwork_list)):
		artwork = artwork_list[i]
		artwork_images = artwork_image_dictionary[artwork]

		if len(artwork_images) > 0:
			rand_image_index = randint(0, len(artwork_images) - 1)
			rand_image = artwork_images[rand_image_index]
		else:
			rand_image = None

		# Owner
		owner, owner_type, owner_image = db_crud.get_artwork_owner(artwork)

		if owner is None:
			owner_id = None
			owner_type = None
			owner_name = None
		else:
			owner_id = owner.user_id

			if owner_type.lower() == "buyer":
				owner_name = owner.buyer_nickname
			elif owner_type.lower() == "artist":
				owner_name = owner.artist_nickname
			elif owner_type.lower() == "auction_house":
				owner_name = owner.auction_house_name
			else:
				owner_name = owner.gallery_name

		# Following or not
		following = db_crud.artwork_is_followed(user_id, artwork.artwork_id)

		artwork_dictionary = dict(display_order=i,
						  artwork_id=artwork.artwork_id,
						  artwork_name=artwork.artwork_name,
						  artwork_date=artwork.artwork_date,
						  artwork_image_path=rand_image.image_path if rand_image is not None else None,
						  following=following,
						  owner_id=owner_id,
						  owner_type=owner_type,
						  owner_name=owner_name,
						  owner_image_path=owner_image.image_path if owner_image is not None else None,
						  follower_count=artwork.artwork_followed_count,
						  critique_count=artwork.artwork_critique_count)

		artwork_dictionary_list.append(artwork_dictionary)

	follower_dictionary_list = []
	for follower in followers:
		image = follower.image
		follower_dictionary = dict(follower_image_path=image.image_path if image is not None else None)
		follower_dictionary_list.append(follower_dictionary)

	# Following or not
	following = db_crud.artist_is_followed(user_id, artist.user_id)

	artist_dictionary = dict(artist_name=artist.artist_nickname,
	                         artist_description=artist.artist_description,
	                         artist_image_path=artist_image.image_path if artist_image is not None else None,
	                         following=following,
	                         follower_count=artist.artist_followed_count,
	                         followers=follower_dictionary_list
	                         )

	result = dict(response="success",
	              artist=artist_dictionary,
	              artwork_list=artwork_dictionary_list,
	              count=1)

	return result


def gallery_auction_page(id, type, user_id):
	"""
	5B - Gallery and Auction House fan page (GET)
	Fan page for Gallery and Auction House, which follow the same format. The page has 3 parts: About, Events and Contact.
	URL: http://host:port/gallery_auction_page?id=1203&type=GALLERY
	:param id: the id of the Gallery or Auction House
	:param type:
		"GALLERY": if the fan page is for a Gallery
		"AUCTION_HOUSE": if the fan page is for an Auction House
	:param user_id: the user_id of the requesting User
	:return: {
			  "response":"success",
			  "place":
			  {
				"place_name":"name",
				"place_description":"text",
				"place_image_path":"path/to/image",
				"following":false,
				"place_address_line1":"address1",
				"place_address_line2":"address2",
				"place_postal_code":30033,
				"place_city":"city_name",
				"place_country":"country_name",
				"place_phone_number":"888-88-88-88",
				"place_website":"http://www.site.com",
				"place_email":"place@email.com",
				"place_geolocation":"lat,long"
			  },
			  "event_list":[
			  {
				"event_name":"name",
				"event_description":"text",
				"event_starting_date":"2015-01-15",
				"event_ending_date":"2015-06-31",
				"event_image_path":"path/to/image"
			  },
			  ...
			  ],
			  "count":1
			}
	"""

	# Check type and get place
	if type.lower() == "gallery":
		place = db_crud.get_gallery(id)
	elif type.lower() == "auction_house":
		place = db_crud.get_auction_house(id)
	else:
		raise WrongArgumentValueError("")
	if place is None:
		raise InexistentResourceError()

	# Get events
	if type.lower() == "gallery":
		event_list = db_crud.get_gallery_events(id, True)
	else:
		event_list = db_crud.get_auction_house_events(id, True)

	# Build dictionaries
	if type.lower() == "gallery":
		place_name = place.gallery_name
		place_description = place.gallery_description
		following = db_crud.gallery_is_followed(user_id, place.user_id)
	else:
		place_name = place.auction_house_name
		place_description = place.auction_house_description
		following = db_crud.auction_house_is_followed(user_id, place.user_id)

	address = place.address
	place_address_line1 = address.address_line1 if address is not None else None
	place_address_line2 = address.address_line2 if address is not None else None
	place_postal_code = address.address_postal_code if address is not None else None
	place_city = address.city.city_name if address is not None else None
	place_country = address.city.country.country_name if address is not None else None
	place_phone_number = address.phone_number if address is not None else None
	place_website = address.address_website if address is not None else None
	place_geolocation = address.geolocation if address is not None else None

	place_dictionary = dict(place_name=place_name,
	                        place_description=place_description,
							place_image_path=place.banner_image.image_path if place.banner_image is not None else None,
	                        following=following,
	                        place_address_line1=place_address_line1,
	                        place_address_line2=place_address_line2,
	                        place_postal_code=place_postal_code,
	                        place_city=place_city,
	                        place_country=place_country,
	                        place_phone_number=place_phone_number,
	                        place_website=place_website,
	                        place_email=place.user.user_email,
	                        place_geolocation=place_geolocation)

	event_dictionary_list = []
	for event in event_list:
		if type.lower() == "gallery":
			event_name = event.gallery_event_name
			event_description = event.gallery_event_description
			event_starting_date = event.gallery_event_starting_time.strftime(settings['DATE_DISPLAY_FORMAT'])
			event_ending_date = event.gallery_event_ending_time.strftime(settings['DATE_DISPLAY_FORMAT'])
		else:
			event_name = event.auction_house_event_name
			event_description = event.auction_house_event_description
			event_starting_date = event.auction_house_event_starting_time.strftime(settings['DATE_DISPLAY_FORMAT'])
			event_ending_date = event.auction_house_event_ending_time.strftime(settings['DATE_DISPLAY_FORMAT'])

		event_dictionary = dict(event_name=event_name,
		                        event_description=event_description,
		                        event_starting_date=event_starting_date,
		                        event_ending_date=event_ending_date,
		                        event_image_path=event.image.image_path if event.image is not None else None)

		event_dictionary_list.append(event_dictionary)

	result = dict(response="success",
	              place=place_dictionary,
	              event_list=event_dictionary_list,
	              count=1)

	return result


def artist_list(limit, offset):
	"""
	7A - Artist list (GET)
	Get a list of Artists in alphabetical order.
	URL: http://host:port/artist_list?limit=0&offset=0
	:param limit: the max number of rows to return for the list (0 for no limit)
	:param offset: the offset (starting point) for the list. E.g. if offset=10, the list will begin at row 11
	:return: {
			  "response":"success",
			  "artist_list":[
			  {
			    "artist_id":123,
			    "artist_name":"name",
			    "image_path":"path/to/image"
			  },
			  ...
			  ],
			  "count":12
			}
	"""

	artist_list = db_crud.get_artist_list(limit, offset)
	artist_dictionary_list = []
	for artist in artist_list:
		artist_dictionary = dict(artist_id=artist.user_id,
		                         artist_name=artist.artist_nickname,
		                         image_path=artist.image.image_path if artist.image is not None else None)
		artist_dictionary_list.append(artist_dictionary)

	result = dict(response="success",
	              artist_list=artist_dictionary_list,
	              count=len(artist_dictionary_list))

	return result


def gallery_list(limit, offset):
	"""
	7B - Gallery list (GET)
	Get a list of Galleries in alphabetical order.
	URL: http://host:port/gallery_list?limit=0&offset=0
	:param limit: the max number of rows to return for the list (0 for no limit)
	:param offset: the offset (starting point) for the list. E.g. if offset=10, the list will begin at row 11
	:return: {
			  "response":"success",
			  "gallery_list":[
			  {
			    "gallery_id":123,
			    "gallery_name":"name",
			    "image_path":"path/to/image"
			  },
			  ...
			  ],
			  "count":12
			}
	"""

	gallery_list = db_crud.get_gallery_list(limit, offset)
	gallery_dictionary_list = []
	for gallery in gallery_list:
		gallery_dictionary = dict(gallery_id=gallery.user_id,
		                         gallery_name=gallery.gallery_name,
		                         image_path=gallery.banner_image.image_path if gallery.banner_image is not None else None)
		gallery_dictionary_list.append(gallery_dictionary)

	result = dict(response="success",
	              gallery_list=gallery_dictionary_list,
	              count=len(gallery_dictionary_list))

	return result


def auction_house_list(limit, offset):
	"""
	7C - Auction House list (GET)
	Get a list of Auction Houses in alphabetical order.
	URL: http://host:port/auction_house_list?limit=0&offset=0
	:param limit: the max number of rows to return for the list (0 for no limit)
	:param offset: the offset (starting point) for the list. E.g. if offset=10, the list will begin at row 11
	:return: {
			  "response":"success",
			  "auction_house_list":[
			  {
			    "auction_house_id":123,
			    "auction_house_name":"name",
			    "image_path":"path/to/image"
			  },
			  ...
			  ],
			  "count":12
			}
	"""

	auction_house_list = db_crud.get_auction_house_list(limit, offset)
	auction_house_dictionary_list = []
	for auction_house in auction_house_list:
		auction_house_dictionary = dict(auction_house_id=auction_house.user_id,
		                         auction_house_name=auction_house.auction_house_name,
		                         image_path=auction_house.banner_image.image_path
		                         if auction_house.banner_image is not None else None)
		auction_house_dictionary_list.append(auction_house_dictionary)

	result = dict(response="success",
	              auction_house_list=auction_house_dictionary_list,
	              count=len(auction_house_dictionary_list))

	return result


def label_list(limit, offset):
	"""
	7D - Label list (GET)
	Get a list of Labels in alphabetical order.
	URL: http://host:port/label_list?limit=0&offset=0
	:param limit: the max number of rows to return for the list (0 for no limit)
	:param offset: the offset (starting point) for the list. E.g. if offset=10, the list will begin at row 11
	:return: {
			  "response":"success",
			  "label_list":[
			  {
			    "label_id":123,
			    "label_name":"name"
			  },
			  ...
			  ],
			  "count":12
			}
	"""

	label_list = db_crud.get_label_list(limit, offset)
	label_dictionary_list = []
	for label in label_list:
		label_dictionary = dict(label_id=label.label_id,
		                        label_name=label.label_name)
		label_dictionary_list.append(label_dictionary)

	result = dict(response="success",
	              label_list=label_dictionary_list,
	              count=len(label_dictionary_list))

	return result


def about_me(user_id, top_n_labels, top_n_artists):
	"""
	11A - About me (GET)
	General information about user, including: membership level, points, personal preferences.
	URL: http://host:port/about_me?top_n_labels=10&top_n_artists=10
	:param user_id: the user_id of the requesting User
	:param top_n_labels: the top n preferred Labels to retrieve, 0 for no limit
	:param top_n_artists: the top n recommended Artists to retrieve, 0 for no limit
	:return: {
			  "response":"success",
			  "user":
			  {
			    "buyer_name":"name",
			    "buyer_level":"SILVER",
			    "buyer_points":1000
			  },
			  "preferred_labels":[
			  {
			    "label_name":"name",
			    "artwork_list":[
			    {
			      "artwork_id":123,
			      "artwork_image":"path/to/image"
			    },
			    ...
			    ]
			  },
			  ...
			  ]
			  "recommended_artists":[
			  {
			    "artist_id":123,
			    "artist_image":"path/to/image"
			  },
			  ...
			  ]
			  },
			  "count":1
			}
	"""

	# Get Buyer info
	buyer = db_crud.get_buyer(user_id)
	user_dictionary = dict(buyer_name=buyer.buyer_nickname,
	                       buyer_level=buyer.buyer_type,
	                       buyer_points=buyer.buyer_points)

	# Get preferred Labels
	preferred_labels = db_crud.get_preferred_labels(user_id, top_n_labels)
	preferred_labels_dictionary_list = []
	for label in preferred_labels:
		label_artworks = db_crud.get_artwork_list_from_label(label.label_id)  # TODO: Improve Artwork selection method
		label_artworks_dictionary_list = []
		for artwork in label_artworks:
			random_artwork_image_index = randint(0, len(artwork.artwork_images) - 1)
			random_artwork_image = \
				artwork.artwork_images[random_artwork_image_index].image if len(artwork.artwork_images) > 0 else None
			artwork_dictionary = dict(artwork_id=artwork.artwork_id,
			                          artwork_image=random_artwork_image.image_path)
			label_artworks_dictionary_list.append(artwork_dictionary)

		preferred_labels_dictionary = dict(label_name=label.label_name,
		                                   artwork_list=label_artworks_dictionary_list)
		preferred_labels_dictionary_list.append(preferred_labels_dictionary)

	# Get recommended Artists
	recommended_artists = db_crud.get_artist_list(top_n_artists, 0, True)  # TODO: Get recommended Artists for this Buyer
	recommended_artist_dictionary_list = []
	for artist in recommended_artists:
		recommended_artist_dictionary = dict(artist_id=artist.user_id,
		                                     artist_image=artist.image.image_path if artist.image is not None else None)
		recommended_artist_dictionary_list.append(recommended_artist_dictionary)

	result = dict(response="success",
	              user=user_dictionary,
	              preferred_labels=preferred_labels_dictionary_list,
	              recommended_artists=recommended_artist_dictionary_list,
	              count=1)

	return result


def following_lists(user_id, limit, offset):
	"""
	11B - Following lists (GET)
	List of people and objects being followed, including My Favorites and owned Artwork.
	URL: http://host:port/following_lists?limit=0&offset=0
	:param user_id: the user_id of the requesting User
	:param limit: the max number of rows to return (0 for no limit)
	:param offset: the offset (starting point) for the list. E.g. if offset=10, the list will begin at row 11
	:return: {
			  "response":"success",
			  "followed_artwork":[
			  {
			    "artwork_id":123,
			    "artwork_name":"name",
			    "artwork_image":"path/to/image"
			  },
			  ...
			  ],
			  "followed_artists":[
			  {
			    "artist_id":123,
			    "artist_name":"name",
			    "artist_image":"path/to/image"
			  },
			  ...
			  ],
			  "followed_galleries":[
			  {
			    "gallery_id":123,
			    "gallery_name":"name",
			    "gallery_image":"path/to/image"
			  },
			  ...
			  ],
			  "followed_auction_houses":[
			  {
			    "auction_house_id":123,
			    "auction_house_name":"name",
			    "auction_house_image":"path/to/image"
			  },
			  ...
			  ],
			  "followed_critics":[
			  {
			    "critic_id":123,
			    "critic_name":"name"
			  },
			  ...
			  ],
			  "favorite_artwork":[
			  {
			    "artwork_id":123,
			    "artwork_name":"name",
			    "artwork_image":"path/to/image"
			  },
			  ...
			  ],
			  "owned_artwork":[
			  {
			    "artwork_id":123,
			    "artwork_name":"name",
			    "artwork_image":"path/to/image"
			  },
			  ...
			  ]
			}
	"""

	followed_artwork = db_crud.get_followed_artwork(user_id, limit, offset)
	followed_artwork_dictionary_list = []
	for artwork in followed_artwork:
		random_artwork_image_index = \
			randint(0, len(artwork.artwork_images) - 1) if len(artwork.artwork_images) > 0 else None
		random_artwork_image = \
			artwork.artwork_images[random_artwork_image_index].image if len(artwork.artwork_images) > 0 else None
		followed_artwork_dictionary = dict(artwork_id=artwork.artwork_id,
		                                   artwork_name=artwork.artwork_name,
		                                   artwork_image=random_artwork_image.image_path
		                                        if random_artwork_image is not None else None)
		followed_artwork_dictionary_list.append(followed_artwork_dictionary)

	followed_artists = db_crud.get_followed_artists(user_id, limit, offset)
	followed_artist_dictionary_list = []
	for artist in followed_artists:
		followed_artist_dictionary = dict(artist_id=artist.user_id,
		                                  artist_name=artist.artist_nickname,
		                                  artist_image=artist.image.image_path if artist.image is not None else None)
		followed_artist_dictionary_list.append(followed_artist_dictionary)

	followed_galleries = db_crud.get_followed_galleries(user_id, limit, offset)
	followed_gallery_dictionary_list = []
	for gallery in followed_galleries:
		followed_gallery_dictionary = dict(gallery_id=gallery.user_id,
		                                   gallery_name=gallery.gallery_name,
		                                   gallery_image=gallery.banner_image.image_path if gallery.banner_image is not None else None)
		followed_gallery_dictionary_list.append(followed_gallery_dictionary)

	followed_auction_houses = db_crud.get_followed_auction_houses(user_id, limit, offset)
	followed_auction_house_dictionary_list = []
	for auction_house in followed_auction_houses:
		followed_auction_house_dictionary = dict(auction_house_id=auction_house.user_id,
		                                         auction_house_name=auction_house.auction_house_name,
		                                         auction_house_image=auction_house.banner_image.image_path
		                                            if auction_house.banner_image is not None else None)
		followed_auction_house_dictionary_list.append(followed_auction_house_dictionary)

	followed_critics = db_crud.get_followed_critics(user_id, limit, offset)
	followed_critic_dictionary_list = []
	for critic in followed_critics:
		followed_critic_dictionary = dict(critic_id=critic.user_id,
		                                  critic_name=critic.critic_nickname)
		followed_critic_dictionary_list.append(followed_critic_dictionary)

	favorite_artwork = db_crud.get_followed_artwork(user_id, limit, offset, True)
	favorite_artwork_dictionary_list = []
	for artwork in favorite_artwork:
		random_artwork_image_index = \
			randint(0, len(artwork.artwork_images) - 1) if len(artwork.artwork_images) > 0 else None
		random_artwork_image = \
			artwork.artwork_images[random_artwork_image_index].image if len(artwork.artwork_images) > 0 else None
		favorite_artwork_dictionary = dict(artwork_id=artwork.artwork_id,
		                                   artwork_name=artwork.artwork_name,
		                                   artwork_image=random_artwork_image.image_path
		                                        if random_artwork_image is not None else None)
		favorite_artwork_dictionary_list.append(favorite_artwork_dictionary)

	owned_artwork = db_crud.get_buyer_artwork(user_id, limit, offset)
	owned_artwork_dictionary_list = []
	for artwork in owned_artwork:
		random_artwork_image_index = \
			randint(0, len(artwork.artwork_images) - 1) if len(artwork.artwork_images) > 0 else None
		random_artwork_image = \
			artwork.artwork_images[random_artwork_image_index].image if len(artwork.artwork_images) > 0 else None
		owned_artwork_dictionary = dict(artwork_id=artwork.artwork_id,
		                                artwork_name=artwork.artwork_name,
		                                artwork_image=random_artwork_image.image_path
		                                    if random_artwork_image is not None else None)
		owned_artwork_dictionary_list.append(owned_artwork_dictionary)

	result = dict(response="success",
	              followed_artwork=followed_artwork_dictionary_list,
	              followed_artists=followed_artist_dictionary_list,
	              followed_galleries=followed_gallery_dictionary_list,
	              followed_auction_houses=followed_auction_house_dictionary_list,
	              followed_critics=followed_critic_dictionary_list,
	              favorite_artwork=favorite_artwork_dictionary_list,
	              owned_artwork=owned_artwork_dictionary_list)

	return result


def user_auction_list(user_id, sorting_rule):
	"""
	11C - User Auction list (GET)
	List of Auctions in which the user is participating.
	URL: http://host:port/user_auction_list?sorting_rule=1
	:param user_id: the user_id of the requesting User
	:param sorting_rule:
		1: bidding time
		2: price
	:return: {
			  "response":"success",
			  "artwork_auctions":[
			  {
			    "artwork_auction_id":123,
			    "artist_name":"name",
			    "artwork_name":"name",
			    "artwork_image":"path/to/image",
			    "artwork_follower_count":135,
			    "artwork_critique_count":25,
			    "minimum_bid":800.0,
			    "current_bid":1000.0,
			    "bid_increment":100.0,
			    "high_bidder_name":"pa****",
			    "user_is_high_bidder":false,
			    "bid_count":3,
			    "auction_starting_time":"2015-08-21 13:10:00",
			    "auction_ending_time":"2015-08-21 13:10:00",
			    "top_three_critiques":[
			    {
			      "critique_date":"2015-04-23",
			      "critique_point_price":500,
			      "critique_text":"text",
			      "critique_upvote_count":51,
			      "critique_downvote_count":4,
			      "critique_vote_type":"L",
			      "critique_purchased":true,
			      "critic_id":4324,
			      "critic_name":"name",
			      "critic_follower_count":1025
			    },
			    ...
			    ]
			  },
			  ...
			  ]
			  "count":5
			}
	"""

	artwork_auction_list = db_crud.get_artwork_auction_list(user_id, sorting_rule)

	artwork_auction_dictionary_list = []
	for artwork_auction in artwork_auction_list:
		critique_list = db_crud.get_critique_list(artwork_auction.artwork.artwork_id, limit=3)
		critique_dictionary_list = []
		for critique in critique_list:

			# Check if Critique is purchased
			critique_purchased = db_crud.critique_purchased(user_id, critique.artwork_id, critique.critic_user_id)
			if critique_purchased:
				critique_text = critique.critique_text
			else:
				critique_text = ""

			# Check Critique vote type
			critique_liked = db_crud.get_critique_vote_type(user_id, critique.artwork_id, critique.critic.user_id)

			critique_dictionary = \
				dict(critique_date=critique.critique_creation_time.strftime(settings['DATE_DISPLAY_FORMAT']),
				     critique_point_price=critique.critique_point_price,
				     critique_text=critique_text,
				     critique_upvote_count=critique.critique_upvote_count,
				     critique_downvote_count=critique.critique_downvote_count,
				     critique_vote_type=critique_liked,
				     critique_purchased=critique_purchased,
				     critic_id=critique.critic.user_id,
				     critic_name=critique.critic.critic_nickname,
				     critic_follower_count=critique.critic.critic_followed_count
				     )
			critique_dictionary_list.append(critique_dictionary)

		# Build Artwork Auction dictionary
		current_bid = artwork_auction.current_bid
		current_bid_amount = current_bid.artwork_auction_bid_amount if current_bid is not None else 0
		high_bidder = current_bid.buyer if current_bid is not None else None
		high_bidder_name = high_bidder.buyer_nickname if high_bidder is not None else None
		if high_bidder is not None:
			if high_bidder.user.user_id == user_id:
				user_is_high_bidder = True
			else:
				user_is_high_bidder = False
		else:
			user_is_high_bidder = False
		bid_count = len(artwork_auction.artwork_auction_bids)

		# Artwork and Artist
		artwork = artwork_auction.artwork
		artist = artwork.artist
		artwork_images = artwork.artwork_images

		if len(artwork_images) > 0:
			rand_image_index = randint(0, len(artwork_images) - 1)
			rand_artwork_image = artwork_images[rand_image_index]
			rand_image = rand_artwork_image.image
		else:
			rand_image = None

		artwork_auction_dictionary = dict(artwork_auction_id=artwork_auction.artwork_auction_id,
		                                  artist_name=artwork_auction.artwork.artist.artist_nickname,
		                                  artwork_name=artwork.artwork_name,
		                                  artwork_image=rand_image.image_path if rand_image is not None else None,
		                                  artwork_follower_count=artwork.artwork_followed_count,
		                                  artwork_critique_count=artwork.artwork_critique_count,
		                                  minimum_bid=artwork_auction.artwork_auction_minimum_bid,
		                                  current_bid=current_bid_amount,
		                                  bid_increment=artwork_auction.artwork_auction_bid_increment,
		                                  high_bidder_name=high_bidder_name,
		                                  user_is_high_bidder = user_is_high_bidder,
		                                  bid_count=bid_count,
		                                  auction_starting_time=artwork_auction.artwork_auction_start_time.strftime(
		                                      settings['DATETIME_DISPLAY_FORMAT']),
		                                  auction_ending_time=artwork_auction.artwork_auction_end_time.strftime(
		                                    settings['DATETIME_DISPLAY_FORMAT']),
		                                  top_three_critiques=critique_dictionary_list)

		artwork_auction_dictionary_list.append(artwork_auction_dictionary)

	result = dict(response="success",
	              artwork_auctions=artwork_auction_dictionary_list,
	              count=len(artwork_auction_dictionary_list))

	return result


################################### POST REQUESTS ###################################


def post_ws(ws_name, arguments, request_body, user_id=None):
	"""
	Get a POST web service given its name and arguments and return it as a dictionary
	:param ws_name: the name of the web service to access
	:param arguments: the URL arguments for the web service
	:param request_body: the raw body of the request (usually expecting a JSON object as text)
	:param user_id: the id of the requesting User (when applicable)
	:return: a dictionary with the requested web service information
	"""

	try:
		# Common arguments
		request_body_dict = json.loads(request_body)

		if ws_name == "login":
			user_email = request_body_dict['user_email']  # Hash-encrypted using SHA256
			user_password = request_body_dict['user_password']  # Hash-encrypted using SHA256
			return login_buyer(user_email, user_password, user_id)
		if ws_name == "logout":
			return logout_buyer(user_id)
		elif ws_name == "signup":
			user_email = request_body_dict['user_email']
			user_password = request_body_dict['user_password']  # Hash-encrypted using SHA256
			return signup_buyer(user_email, user_password)
		elif ws_name == "signup_facebook":
			fb_id = request_body_dict['fb_id']
			user_name = request_body_dict['user_name']
			user_email = request_body_dict['user_email']
			user_image = request_body_dict['user_image']
			return signup_buyer_facebook(fb_id, user_name, user_email, user_image)
		elif ws_name == "like_dislike_critique":
			artwork_id = request_body_dict['artwork_id']
			critic_id = request_body_dict['critic_id']
			vote_type = request_body_dict['vote_type']
			return like_dislike_critique(user_id, artwork_id, critic_id, vote_type)
		elif ws_name == "make_bid":
			artwork_auction_id = request_body_dict['artwork_auction_id']
			bid_amount = request_body_dict['bid_amount']
			return make_bid(user_id, artwork_auction_id, bid_amount)
		elif ws_name == "buy_critique":
			artwork_id = request_body_dict['artwork_id']
			critic_id = request_body_dict['critic_id']
			return buy_critique(user_id, artwork_id, critic_id)
		elif ws_name == "buy_coins":
			coin_amount = request_body_dict['coin_amount']
			return buy_coins(user_id, coin_amount)
		elif ws_name == "follow_artwork":
			artwork_id = request_body_dict['artwork_id']
			follow = request_body_dict['follow']
			return follow_something(user_id, 'ARTWORK', artwork_id, follow)
		elif ws_name == "follow_artist":
			artist_id = request_body_dict['artist_id']
			follow = request_body_dict['follow']
			return follow_something(user_id, 'ARTIST', artist_id, follow)
		elif ws_name == "follow_gallery":
			gallery_id = request_body_dict['gallery_id']
			follow = request_body_dict['follow']
			return follow_something(user_id, 'GALLERY', gallery_id, follow)
		elif ws_name == "follow_auction_house":
			auction_house_id = request_body_dict['auction_house_id']
			follow = request_body_dict['follow']
			return follow_something(user_id, 'AUCTION_HOUSE', auction_house_id, follow)
		elif ws_name == "follow_critic":
			critic_id = request_body_dict['critic_id']
			follow = request_body_dict['follow']
			return follow_something(user_id, 'CRITIC', critic_id, follow)
		elif ws_name == "add_favorite_artwork":
			artwork_id = request_body_dict['artwork_id']
			is_favorite = request_body_dict['is_favorite']
			return add_favorite_artwork(user_id, artwork_id, is_favorite)
		else:
			raise InexistentResourceError()
	except KeyError, e:
		raise MissingArgumentsError()
	except ValueError, e:
		raise MissingArgumentsError()
	except Exception, e:
		raise e


def login_buyer(user_email, user_password, user_id=None):
	"""
	1A - Log in (POST)
	Log in to the ArtMeGo system using the given user email and password (hash-encrypted using SHA-256).
	The JWT token must be sent when this web service is used for confirming user purchases.
	If user id in JWT token does not match the user id of the user logging in, then an "authentication error"
	will be returned.
	URL: http://host:port/login
	:param user_email: The user email (hash-encrypted using SHA-256)
	:param user_password: The user password (hash-encrypted using SHA-256)
	:param user_id: The user if of the requesting Buyer. It will be used only when logging in to confirm user purchases.
	:return: if success: {
						  "response":"success",
						  "jwt_token":"xxxxx.yyyy.zzzz"
						 }
			 else:  {
					  "response":"fail",
					  "error_code":"0005",
					  "reason":"authentication error"
					}
					{
					  "response":"fail",
					  "error_code":"0007",
					  "reason":"user inexistent"
					}
					{
					  "response":"fail",
					  "error_code":"0009",
					  "reason":"unauthorized"
					}
	"""

	user = db_crud.login(user_email, user_password)

	# Check user type
	if user.user_type.lower() != "buyer":
		raise UnauthorizedError()

	if user_id is not None:
		if user.user_id != user_id:
			raise AuthenticationError()

	jwt_token = security.generate_jwt(user)

	result = dict(response="success", jwt_token=jwt_token)

	return result


def logout_buyer(user_id=None):
	"""
	1B - Log out (POST)
	Log out of the ArtMeGo API.
	URL: http://host:port/logout
	:param user_id: The user if of the requesting Buyer.
	:return: if success: {
						  "response":"success"
						 }
	"""

	# TODO: Perform necessary log out (e.g. make JWT token invalid, etc.)

	result = dict(response="success")

	return result


def signup_buyer(user_email, user_password):
	"""
	1C - Sign up (POST)
	Register to ArtMeGo as a Buyer
	URL: http://host:port/signup
	:param user_email: The user email
	:param user_password: The user password (hash-encrypted using SHA-256)
	:return: if success: {
						  "response":"success",
						  "jwt_token":"xxxxx.yyyy.zzzz"
						 }
			 else: {"response":"fail",
					"error_code":"0008",
					"reason":"user already exists"}
				   {"response":"fail",
					"error_code":"0006",
					"reason":"wrong argument value"}
	"""

	buyer, user = db_crud.create_buyer_user(user_email, user_password)

	jwt_token = security.generate_jwt(user)

	result = dict(response="success", jwt_token=jwt_token)

	return result


def signup_buyer_facebook(fb_id, user_name, user_email, user_image):
	"""
	1D - Facebook signup (POST)
	Register to ArtMeGo as a Buyer using Facebook login
	URL: http://host:port/signup_facebook
	:param fb_id: the Facebook id to check
	:param user_name: the user name
	:param user_email: the user email
	:param user_image: the path to the user's image on Facebook (profile pic)
	:return: if success: {
						  "response":"success",
						  "jwt_token":"xxxxx.yyyy.zzzz"
						 }
			 else:  {
					  "response":"fail",
					  "error_code":"0005",
					  "reason":"authentication error"
					}
	"""

	# Check if user exists
	try:
		user = db_crud.login_facebook(fb_id, user_email)
	# If doesn't exist, create it
	except UserInexistentError, e:
		buyer= db_crud.create_buyer_user_facebook(fb_id, user_name, user_email, user_image)
		user = buyer.user
	except Exception, e:
		raise e

	# Check user type
	if user.user_type.lower() != "buyer":
		raise UnauthorizedError()

	jwt_token = security.generate_jwt(user)

	result = dict(response="success", jwt_token=jwt_token)

	return result


def like_dislike_critique(user_id, artwork_id, critic_user_id, vote_type):
	"""
	3B - Like/dislike Critique
	Like or dislike a given Critique.
	URL: http://host:port/like_dislike_critique
	:param user_id: the user_id of the requesting Buyer
	:param artwork_id: the id of the Artwork whose Critique is to be bought
	:param critic_user_id: the user id of the Critic who made the Critique
	:param vote_type: the vote type made by the user: "L" (like), "D" (dislike), "N" (none)
	:return: if success: {
						  "response":"success"
						 }
			 else:  {
					  "response":"fail",
					  "error_code":"0009",
					  "reason":"unauthorized"
					}
	"""

	critique = db_crud.like_dislike_critique(user_id, artwork_id, critic_user_id, vote_type)

	result = dict(response="success")

	return result


def make_bid(user_id, artwork_auction_id, bid_amount):
	"""
	4B - Artwork Auction page
	User makes a bid on an Artwork Auction. The bid amount is the total bid offered by the user.
	URL: http://host:port/make_bid
	:param user_id: the user_id of the requesting Buyer
	:param artwork_auction_id: the id of the Artwork Auction
	:param bid_amount: the total amount to bid for the artwork
	:return: if success: {
						  "response":"success"
						 }
			 else:  {
					  "response":"fail",
					  "error_code":"0002",
					  "reason":"inexistent resource"
					}
					{
					  "response":"fail",
					  "error_code":"0010",
					  "reason":"insufficient funds"
					}
					{
					  "response":"fail",
					  "error_code":"0009",
					  "reason":"unauthorized"
					}
	"""

	current_bid_amount = db_crud.make_bid(user_id, artwork_auction_id, bid_amount)

	result = dict(response="success")

	return result


def buy_critique(user_id, artwork_id, critic_user_id):
	"""
	4C - Buy Critique
	User purchases a Critique using his/her points.
	URL: http://host:port/buy_critique
	:param user_id: the user_id of the requesting Buyer
	:param artwork_id: the id of the Artwork whose Critique is to be bought
	:param critic_user_id: the user id of the Critic who made the Critique
	:return: if success: {
						  "response":"success"
						 }
			 else:  {
					  "response":"fail",
					  "error_code":"0010",
					  "reason":"insufficient funds"
					}
					{
					  "response":"fail",
					  "error_code":"0009",
					  "reason":"unauthorized"
					}
	"""

	critique = db_crud.purchase_critique(user_id, artwork_id, critic_user_id)

	result = dict(response="success")

	return result


def buy_coins(user_id, coin_amount):
	"""
	4D - Buy coins
	Buyer makes a purchase of a certain amount of coins for his/her account.
	Requires username and password confirmation (use Login web service 1A).
	URL: http://host:port/buy_coins
	:param user_id: the user_id of the requesting Buyer
	:param coin_amount: the amount of coins to buy. Possible values are:
		5 ($250), 20 ($1000), 100 ($4500), 200 ($8000), 150 ($5000), 300 ($9000)
	:return: if success: {
						  "response":"success"
						 }
			 else:  {
					  "response":"fail",
					  "error_code":"0010",
					  "reason":"insufficient funds"
					}
					{
					  "response":"fail",
					  "error_code":"0005",
					  "reason":"authentication error"
					}
					{
					  "response":"fail",
					  "error_code":"0006",
					  "reason":"wrong argument value"
					}
	"""

	coins = db_crud.buy_coins(user_id, coin_amount)

	result = dict(response="success")

	return result


def follow_something(user_id, type, thing_id, follow):
	"""
	6A - 6E - Follow Artwork, Artist, Gallery, Auction House or Critic
	Follow or unfollow something.
	URL: http://host:port/follow_artwork (example)
	:param user_id: the user_id of the requesting Buyer
	:param type: the type of thing to follow: ARTWORK, ARTIST, GALLERY, AUCTION_HOUSE, CRITIC
	:param thing_id: the id of the thing to follow
	:param follow: true if the user is to follow this thing, false otherwise
	:return: if success: {
						  "response":"success"
						 }
	"""

	thing = db_crud.follow_something(user_id, type, thing_id, follow)

	result = dict(response="success")

	return result


def add_favorite_artwork(user_id, artwork_id, is_favorite):
	"""
	6F - Add Artwork to My Favorites
	Add/remove an Artwork to User favorites.
	URL: http://host:port/add_favorite_artwork
	:param user_id: the user_id of the requesting Buyer
	:param artwork_id: the id of the Artwork to make a favorite
	:param is_favorite: true if the user is to make this Artwork a favorite, false otherwise
	:return: if success: {
						  "response":"success"
						 }
	"""

	# First, follow this Artwork if is_favorite is true
	if is_favorite:
		artwork = db_crud.follow_something(user_id, 'ARTWORK', artwork_id, True)

	# Then, make the Artwork a favorite
	db_crud.add_favorite_artwork(user_id, artwork_id, is_favorite)

	result = dict(response="success")

	return result