# coding=utf-8
"""
This module contains CRUD (Create, Read, Update, Delete) functions for database manipulation using ORM mapping.
The ORM used is the SQLAlchemy package.
"""

import logging
from datetime import datetime
from datetime import timedelta
import re
import hashlib

from sqlalchemy import create_engine, and_, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
import sys

from lib.db_tables import Country, City, Address, Image, Banner, Buyer, Administrator, User, Artist, Auction_House, \
	Gallery, Critic, Artwork, Artwork_Image, Critique, Follow_Artist, Gallery_Event, Auction_House_Event, \
	Critique_Purchase, Artwork_Auction, Artwork_Auction_Bid, Follow_Artwork, Follow_Gallery, Follow_Auction, \
	Follow_Critic, Critique_Vote, Artwork_Label, Label
from lib.exceptions import WrongArgumentValueError, UserExistsError, UserInexistentError, AuthenticationError, \
	InexistentResourceError, InsufficientFundsError, UnauthorizedError
from lib.utils import deprecated
from settings import settings


logger = logging.getLogger('artmego.' + __name__)

DB_CONNECTION_STRING = "{0}://{1}:{2}@{3}:{4}/{5}?charset=utf8".format(settings['DB_ENGINE_ORM_MAP'][settings['DB_ENGINE']],
                                                                       settings['DB_USER'], settings['DB_PASSWORD'],
                                                                       settings['DB_HOST'], settings['DB_PORT'],
                                                                       settings['DB_SCHEMA'])
engine = create_engine(DB_CONNECTION_STRING)
Session = sessionmaker(bind=engine)
COIN_PRICES = settings['COIN_PRICES']

################################### CREATE ###################################


def add_favorite_artwork(user_id, artwork_id, is_favorite):
	"""
	Add/remove an Artwork to User favorites.
	:param user_id: the user_id of the requesting Buyer
	:param artwork_id: the id of the Artwork to make a favorite
	:param is_favorite: true if the user is to make this Artwork a favorite, false otherwise
	"""

	now = datetime.now()
	curr_session = Session()

	try:
		# Get Buyer
		buyer = curr_session.query(Buyer). \
			filter_by(user_id=user_id). \
			one()

		# Check if Buyer is already following this Artwork
		follow_artwork = curr_session.query(Follow_Artwork). \
				filter_by(buyer_user_id=user_id). \
				filter_by(artwork_id=artwork_id). \
				first()

		if follow_artwork is None and is_favorite:
			follow_artwork(buyer_user_id=user_id, artwork_id=artwork_id, follow_artwork_status="FOLLOWING",
			               is_favorite=True, follow_artwork_creation_time=now, follow_artwork_modification_time=now)
			curr_session.add(follow_artwork)
			curr_session.flush()
			artwork = follow_artwork.artwork
			artwork.artwork_followed_count += 1
		elif follow_artwork is not None and follow_artwork.is_favorite != is_favorite:
			follow_artwork.is_favorite = is_favorite
			curr_session.add(follow_artwork)
		else:
			return None

		curr_session.commit()
	except NoResultFound, e:
		curr_session.rollback()
		raise InexistentResourceError()
	except Exception, e:
		curr_session.rollback()
		raise e
	finally:
		curr_session.close()


def buy_coins(user_id, coin_amount):
	"""
	Buyer makes a purchase of a certain amount of coins for his/her account.
	Raises an InsufficientFundsError if Buyer does not have enough cash.
	:param user_id: the user_id of the Buyer making the bid
	:param coin_amount: the amount of coins to buy. Possible values are:
		5 ($250), 20 ($1000), 100 ($4500), 200 ($8000), 150 ($5000), 300 ($9000)
	:return: the amount of coins bought (0 for error)
	"""

	now = datetime.now()
	curr_session = Session()

	try:
		# Get Buyer
		buyer = curr_session.query(Buyer). \
			filter_by(user_id=user_id). \
			one()

		# Check that the Buyer has enough cash to buy the coins
		price = COIN_PRICES[coin_amount]
		if buyer.buyer_cash < price:
			raise InsufficientFundsError()

		# Make purchase
		buyer.buyer_points = buyer.buyer_points + coin_amount
		buyer.buyer_cash = buyer.buyer_cash - price

		curr_session.add(buyer)
		curr_session.commit()

		return coin_amount
	except NoResultFound, e:
		curr_session.rollback()
		raise InexistentResourceError()
	except KeyError, e:
		curr_session.rollback()
		raise WrongArgumentValueError('coin_amount')
	except Exception, e:
		curr_session.rollback()
		raise e
	finally:
		curr_session.close()


def create_buyer_user(user_email, user_password):
	"""
	Create a new Buyer user. This method creates a row for the User and Buyer tables in a single transaction.
	:param user_email: the user email
	:param user_password: the hash-encrypted (SHA256) password
	:return: an instance of the Buyer class, an instance of the User class
	"""

	now = datetime.now()
	curr_session = Session(expire_on_commit=False)

	try:
		# Check e-mail address format
		email_regex = r"[^@^\s-]+@[^@^\s-]+\.[^@^\s-]+"
		if not re.match(email_regex, user_email):
			raise WrongArgumentValueError("user_email")

		# Check that the e-mail doesn't exist
		user = curr_session.query(User).filter_by(user_email=user_email).first()
		if user is not None:
			raise UserExistsError()

		# Hash-encrypt email
		hasher = hashlib.sha256(user_email)
		user_hashed_email = hasher.hexdigest()

		user = User(user_email=user_email, user_hashed_email=user_hashed_email, user_type="BUYER",
		            user_password=user_password, user_status="UNCONFIRMED", user_creation_time=now,
		            user_modification_time=now)
		curr_session.add(user)
		curr_session.flush()

		buyer = Buyer(user_id=user.user_id, buyer_type="SILVER", buyer_first_name=user_email,
		              buyer_last_name="", buyer_nickname=user_email, buyer_gender="", buyer_birthday=now,
		              buyer_occupation="", address_id=None, image_id=None, buyer_points=0, buyer_cash=0,
		              buyer_modification_time=now)
		curr_session.add(buyer)

		curr_session.commit()

		return buyer, user
	except Exception, e:
		curr_session.rollback()
		raise e
	finally:
		curr_session.close()


def create_buyer_user_facebook(fb_id, user_name, user_email, user_image):
	"""
	Create a new Buyer user from Facebook.
	This method creates a row for the User and Buyer tables in a single transaction.
	:param fb_id: the Facebook id of the user
	:param user_name: the user name
	:param user_email: the user email
	:param user_image: the path to the user's image on Facebook (profile pic)
	:return: an instance of the Buyer class
	"""

	now = datetime.now()
	curr_session = Session(expire_on_commit=False)

	try:
		# Check e-mail address format
		email_regex = r"[^@^\s-]+@[^@^\s-]+\.[^@^\s-]+"
		if not re.match(email_regex, user_email):
			raise WrongArgumentValueError("user_email")

		# Check that the e-mail doesn't exist
		user = curr_session.query(User).filter_by(user_email=user_email).first()
		if user is not None:
			raise UserExistsError()

		# Check that the facebook id doesn't exist
		buyer = curr_session.query(Buyer).filter_by(facebook_id=fb_id).first()
		if buyer is not None:
			raise UserExistsError()

		# Hash-encrypt email
		hasher = hashlib.sha256(user_email)
		user_hashed_email = hasher.hexdigest()

		user = User(user_email=user_email, user_hashed_email=user_hashed_email, user_type="BUYER",
		            user_password="", user_status="UNCONFIRMED", user_creation_time=now,
		            user_modification_time=now)
		curr_session.add(user)
		curr_session.flush()

		# Create Image
		if user_image is not None:
			image = Image(image_name=user_name, image_path=user_image,
			              image_creation_time=now, image_modification_time=now)
			curr_session.add(image)
			curr_session.flush()
			image_id = image.image_id
		else:
			image_id = None

		buyer = Buyer(user_id=user.user_id, facebook_id=fb_id, buyer_type="SILVER", buyer_first_name=user_name,
		              buyer_last_name="", buyer_nickname=user_email, buyer_gender="", buyer_birthday=now,
		              buyer_occupation="", address_id=None, image_id=image_id, buyer_points=0, buyer_cash=0,
		              buyer_modification_time=now)
		curr_session.add(buyer)

		curr_session.commit()

		# touch User
		user = buyer.user

		return buyer
	except Exception, e:
		curr_session.rollback()
		raise e
	finally:
		curr_session.close()


def follow_something(user_id, type, object_id, follow):
	"""
	Follow or unfollow something, depending on the type
	:param user_id: the user_id of the requesting Buyer
	:param type: the type of thing to follow: ARTWORK, ARTIST, GALLERY, AUCTION_HOUSE, CRITIC
	:param object_id: the id of the object_to_follow to follow
	:param follow: true whether the user is to follow this thing, false otherwise
	:return: the object_to_follow to follow
	"""

	now = datetime.now()
	curr_session = Session()

	try:
		# Get Buyer
		buyer = curr_session.query(Buyer). \
			filter_by(user_id=user_id). \
			one()

		# Get object_to_follow to follow
		if type.lower() == 'artwork':
			table_to_follow = Artwork
			table_to_follow_id = Artwork.artwork_id
			follow_table = Follow_Artwork
			follow_table_id = Follow_Artwork.artwork_id
		elif type.lower() == 'artist':
			table_to_follow = Artist
			table_to_follow_id = Artist.user_id
			follow_table = Follow_Artist
			follow_table_id = Follow_Artist.artist_user_id
		elif type.lower() == 'gallery':
			table_to_follow = Gallery
			table_to_follow_id = Gallery.user_id
			follow_table = Follow_Gallery
			follow_table_id = Follow_Gallery.gallery_user_id
		elif type.lower() == 'auction_house':
			table_to_follow = Auction_House
			table_to_follow_id = Auction_House.user_id
			follow_table = Follow_Auction
			follow_table_id = Follow_Auction.auction_house_user_id
		elif type.lower() == 'critic':
			table_to_follow = Critic
			table_to_follow_id = Critic.user_id
			follow_table = Follow_Critic
			follow_table_id = Follow_Critic.critic_user_id
		else:
			raise WrongArgumentValueError("")

		# Get object to follow
		object_to_follow = curr_session.query(table_to_follow). \
					filter(table_to_follow_id == object_id). \
					one()

		# Check if it is following or unfollowing
		if follow:
			status = "FOLLOWING"
			followed_count_sum = 1
		else:
			status = "UNFOLLOWING"
			followed_count_sum = -1

		# Check if Buyer already followed this object
		follow_object = curr_session.query(follow_table). \
				filter_by(buyer_user_id=user_id). \
				filter(follow_table_id == object_id). \
				first()

		if follow_object is not None:
			if  type.lower() == 'artwork' and status.lower() != follow_object.follow_artwork_status.lower():
				follow_object.follow_artwork_status = status
				object_to_follow.artwork_followed_count += followed_count_sum
			elif type.lower() == 'artist' and status.lower() != follow_object.follow_artist_status.lower():
				follow_object.follow_artist_status = status
				object_to_follow.artist_followed_count += followed_count_sum
			elif type.lower() == 'gallery' and status.lower() != follow_object.follow_gallery_status.lower():
				follow_object.follow_gallery_status = status
				object_to_follow.gallery_followed_count += followed_count_sum
			elif type.lower() == 'auction_house' and status.lower() != follow_object.follow_auction_status.lower():
				follow_object.follow_auction_status = status
				object_to_follow.auction_house_followed_count += followed_count_sum
			elif type.lower() == 'critic' and status.lower() != follow_object.follow_critic_status.lower():
				follow_object.follow_critic_status = status
				object_to_follow.critic_followed_count += followed_count_sum
			else:
				return None

		elif follow_object is None and follow:
			if  type.lower() == 'artwork':
				follow_object = follow_table(buyer_user_id=user_id, artwork_id=object_id, follow_artwork_status=status,
				                             is_favorite=False, follow_artwork_creation_time=now,
				                             follow_artwork_modification_time=now)
				object_to_follow.artwork_followed_count += followed_count_sum
			elif type.lower() == 'artist':
				follow_object = follow_table(buyer_user_id=user_id, artist_user_id=object_id, follow_artist_status=status,
				                             follow_artist_creation_time=now, follow_artist_modification_time=now)
				object_to_follow.artist_followed_count += followed_count_sum
			elif type.lower() == 'gallery':
				follow_object = follow_table(buyer_user_id=user_id, gallery_user_id=object_id, follow_gallery_status=status,
				                             follow_gallery_creation_time=now, follow_gallery_modification_time=now)
				object_to_follow.gallery_followed_count += followed_count_sum
			elif type.lower() == 'auction_house':
				follow_object = follow_table(buyer_user_id=user_id, auction_house_user_id=object_id,
				                             follow_auction_status=status, follow_auction_creation_time=now,
				                             follow_auction_modification_time=now)
				object_to_follow.auction_house_followed_count += followed_count_sum
			elif type.lower() == 'critic':
				follow_object = follow_table(buyer_user_id=user_id, critic_user_id=object_id, follow_critic_status=status,
				                             follow_critic_creation_time=now, follow_critic_modification_time=now)
				object_to_follow.critic_followed_count += followed_count_sum

		else:
			return None

		curr_session.add(follow_object)
		curr_session.add(object_to_follow)

		curr_session.commit()

		return object_to_follow
	except NoResultFound, e:
		curr_session.rollback()
		raise InexistentResourceError()
	except Exception, e:
		curr_session.rollback()
		raise e
	finally:
		curr_session.close()


def like_dislike_critique(user_id, artwork_id, critic_user_id, vote_type):
	"""
	A specific Buyer likes or dislikes a Critique
	:param user_id: the user_id of the Buyer
	:param artwork_id: the id of the Artwork whose Critique is liked/disliked
	:param critic_user_id: the user id of the Critic who made the Critique
	:param vote_type: the vote type made by the user: "L" (like), "D" (dislike), "N" (none)
	:return: the Critique that was liked or disliked
	"""

	now = datetime.now()
	curr_session = Session()

	try:
		# Get Buyer
		buyer = curr_session.query(Buyer). \
			filter_by(user_id=user_id). \
			one()

		# Get Critique
		critique = curr_session.query(Critique). \
				filter_by(artwork_id=artwork_id). \
				filter_by(critic_user_id=critic_user_id). \
				one()

		# Check that Critique is APPROVED
		if critique.critique_status.lower() != "approved":
			raise UnauthorizedError()

		# Check if Buyer already liked/disliked this Critique
		critique_vote = curr_session.query(Critique_Vote). \
				filter_by(artwork_id=artwork_id). \
				filter_by(critic_user_id=critic_user_id). \
				filter_by(buyer_user_id=user_id). \
				first()
		if critique_vote is not None and vote_type != critique_vote.critique_vote_type:
			# Check vote type
			if vote_type.lower() == "l" and critique_vote.critique_vote_type.lower() == "d":
				upvote_increment = 1
				downvote_increment = -1
			elif vote_type.lower() == "l" and critique_vote.critique_vote_type.lower() == "n":
				upvote_increment = 1
				downvote_increment = 0
			elif vote_type.lower() == "d" and critique_vote.critique_vote_type.lower() == "l":
				upvote_increment = -1
				downvote_increment = 1
			elif vote_type.lower() == "d" and critique_vote.critique_vote_type.lower() == "n":
				upvote_increment = 0
				downvote_increment = 1
			elif vote_type.lower() == "n" and critique_vote.critique_vote_type.lower() == "l":
				upvote_increment = -1
				downvote_increment = 0
			elif vote_type.lower() == "n" and critique_vote.critique_vote_type.lower() == "d":
				upvote_increment = 0
				downvote_increment = -1
			else:
				raise WrongArgumentValueError()

			critique_vote.critique_vote_type = vote_type
		elif critique_vote is None:
			# Make Critique Vote
			critique_vote = Critique_Vote(artwork_id=artwork_id, critic_user_id=critic_user_id, buyer_user_id=user_id,
			                              critique_vote_type=vote_type, critique_vote_creation_time=now,
			                              critique_vote_modification_time=now)
			# Check vote type
			if vote_type.lower() == "l":
				upvote_increment = 1
				downvote_increment = 0
			elif vote_type.lower() == "d":
				upvote_increment = 0
				downvote_increment = 1
			elif vote_type.lower() == "n":
				return critique
			else:
				raise WrongArgumentValueError()
		else:
			return critique

		curr_session.add(critique_vote)

		# Increase upvote/downvote count
		critique.critique_upvote_count += upvote_increment
		critique.critique_downvote_count += downvote_increment

		curr_session.add(critique)

		curr_session.commit()

		return critique
	except NoResultFound, e:
		curr_session.rollback()
		raise InexistentResourceError()
	except Exception, e:
		curr_session.rollback()
		raise e
	finally:
		curr_session.close()


def make_bid(user_id, artwork_auction_id, bid_amount):
	"""
	A specific Buyer makes a bid on an Artwork Auction. Buyer's cash is checked, as well as starting and ending
	time of the Artwork Auction.
	Returns the current bid after making the bid (if successful)
	Raises an InsufficientFundsError if Buyer does not have enough cash.
	Raises an InexistentResourceError if Artwork Auction hasn't started or is already finished.
	Raises an UnauthorizedError if bid_amount is lower than minimum bid or lower than previous bid.
	Raises an UnauthorizedError if bid_amount is not a multiple of bid increment.
	:param user_id: the user_id of the Buyer making the bid
	:param artwork_auction_id: the id of the Artwork Auction
	:param bid_amount: the total bid amount made by the user
	:return: the current bid value after making the bid (if successful)
	"""

	now = datetime.now()

	curr_session = Session()

	try:
		# Get Buyer
		buyer = curr_session.query(Buyer). \
			filter_by(user_id=user_id). \
			one()

		# Get Artwork Auction
		artwork_auction = curr_session.query(Artwork_Auction). \
				filter_by(artwork_auction_id=artwork_auction_id). \
				one()

		# Check that the Artwork Auction is still available
		if artwork_auction.artwork_auction_start_time > now or artwork_auction.artwork_auction_end_time < now:
			raise InexistentResourceError()

		# Check that the Buyer has enough cash to make a bid
		if buyer.buyer_cash < bid_amount:
			raise InsufficientFundsError()

		# Check that the Buyer's bid_amount is higher than minimum_bid and higher than previous bid
		if artwork_auction.current_bid is None:
			current_bid_amount = 0
		else:
			current_bid_amount = artwork_auction.current_bid.artwork_auction_bid_amount

		if bid_amount <= current_bid_amount:
			raise UnauthorizedError()

		if bid_amount < artwork_auction.artwork_auction_minimum_bid:
			raise UnauthorizedError()

		# Check that bid_amount is a multiple of bid increment
		if bid_amount % artwork_auction.artwork_auction_bid_increment != 0:
			raise UnauthorizedError()

		# Make bid
		artwork_auction_bid = Artwork_Auction_Bid(artwork_auction_id=artwork_auction.artwork_auction_id,
		                                          buyer_user_id=user_id, artwork_auction_bid_amount=bid_amount,
		                                          artwork_auction_bid_creation_time = now)
		curr_session.add(artwork_auction_bid)
		curr_session.flush()

		# Update current bid in Artwork Auction
		artwork_auction.artwork_auction_current_bid = artwork_auction_bid.artwork_auction_bid_id
		curr_session.add(artwork_auction)

		curr_session.commit()

		return current_bid_amount
	except NoResultFound, e:
		curr_session.rollback()
		raise InexistentResourceError()
	except Exception, e:
		curr_session.rollback()
		raise e
	finally:
		curr_session.close()


def purchase_critique(user_id, artwork_id, critic_user_id):
	"""
	A specific Buyer buys a Critique using his/her points.
	Raises an InsufficientFundsError if Buyer does not have enough points.
	:param user_id: the user_id of the Buyer making the bid
	:param artwork_id: the id of the Artwork whose Critique is to be bought
	:param critic_user_id: the user id of the Critic who made the Critique
	:return: the Critique that was purchased
	"""

	now = datetime.now()
	curr_session = Session()

	try:
		# Get Buyer
		buyer = curr_session.query(Buyer). \
			filter_by(user_id=user_id). \
			one()

		# Get Critique
		critique = curr_session.query(Critique). \
				filter_by(artwork_id=artwork_id). \
				filter_by(critic_user_id=critic_user_id). \
				one()

		# Check that Critique is APPROVED
		if critique.critique_status.lower() != "approved":
			raise UnauthorizedError()

		# Check if Buyer already bought this Critique
		critique_purchase = curr_session.query(Critique_Purchase). \
				filter_by(artwork_id=artwork_id). \
				filter_by(critic_user_id=critic_user_id). \
				filter_by(buyer_user_id=user_id). \
				first()
		if critique_purchase is not None:
			return critique

		# Check that the Buyer has enough points to buy the Critique
		if buyer.buyer_points < critique.critique_point_price:
			raise InsufficientFundsError()

		# Make Critique Purchase
		critique_purchase = Critique_Purchase(artwork_id=artwork_id, critic_user_id=critic_user_id,
		                                      buyer_user_id=user_id, critique_purchase_creation_time=now)
		curr_session.add(critique_purchase)
		curr_session.flush()

		# Subtract user points
		buyer.buyer_points = buyer.buyer_points - critique.critique_point_price
		curr_session.add(buyer)

		curr_session.commit()

		return critique
	except NoResultFound, e:
		curr_session.rollback()
		raise InexistentResourceError()
	except Exception, e:
		curr_session.rollback()
		raise e
	finally:
		curr_session.close()


################################### READ ###################################

def artist_is_followed(user_id, artist_id):
	"""
	Whether a given Artist is being followed by a particular Buyer
	:param user_id: the user id of the Buyer
	:param artist_id: the id of the Artist
	:return True if the Artist is being followed by this Buyer, False otherwise
	"""

	curr_session = Session()
	try:

		follow_artist = curr_session.query(Follow_Artist). \
			filter_by(buyer_user_id=user_id). \
			filter_by(artist_user_id=artist_id). \
			first()

		if follow_artist is None:
			return False
		else:
			if follow_artist.follow_artist_status.lower() == "following":
				return True
			else:
				return False

	except Exception, e:
		raise e
	finally:
		curr_session.close()


def artwork_is_followed(user_id, artwork_id):
	"""
	Whether a given Artwork is being followed by a particular Buyer
	:param user_id: the user id of the Buyer
	:param artwork_id: the id of the Artwork
	:return True if the Artwork is being followed by this Buyer, False otherwise
	"""

	curr_session = Session()
	try:

		follow_artwork = curr_session.query(Follow_Artwork). \
			filter_by(buyer_user_id=user_id). \
			filter_by(artwork_id=artwork_id). \
			first()

		if follow_artwork is None:
			return False
		else:
			if follow_artwork.follow_artwork_status.lower() == "following":
				return True
			else:
				return False

	except Exception, e:
		raise e
	finally:
		curr_session.close()


def auction_house_is_followed(user_id, auction_house_id):
	"""
	Whether a given Auction House is being followed by a particular Buyer
	:param user_id: the user id of the Buyer
	:param auction_house_id: the id of the Auction House
	:return True if the Auction House is being followed by this Buyer, False otherwise
	"""

	curr_session = Session()
	try:

		follow_auction_house = curr_session.query(Follow_Auction). \
			filter_by(buyer_user_id=user_id). \
			filter_by(auction_house_user_id=auction_house_id). \
			first()

		if follow_auction_house is None:
			return False
		else:
			if follow_auction_house.follow_artist_status.lower() == "following":
				return True
			else:
				return False

	except Exception, e:
		raise e
	finally:
		curr_session.close()


def gallery_is_followed(user_id, gallery_id):
	"""
	Whether a given Gallery is being followed by a particular Buyer
	:param user_id: the user id of the Buyer
	:param gallery_id: the id of the Gallery
	:return True if the Gallery is being followed by this Buyer, False otherwise
	"""

	curr_session = Session()
	try:

		follow_gallery = curr_session.query(Follow_Gallery). \
			filter_by(buyer_user_id=user_id). \
			filter_by(gallery_user_id=gallery_id). \
			first()

		if follow_gallery is None:
			return False
		else:
			if follow_gallery.follow_gallery_status.lower() == "following":
				return True
			else:
				return False

	except Exception, e:
		raise e
	finally:
		curr_session.close()


def critique_purchased(buyer_user_id, artwork_id, critic_user_id):
	"""
	Check whether a Critique has been purchased by this Buyer or not.
	:param buyer_user_id: the id of the Buyer
	:param artwork_id: the id of the Artwork (PK for Critique)
	:param critic_user_id: the id of the Critic (PK for Critique)
	:return: True if the Critique has been bought, False otherwise
	"""

	curr_session = Session()
	try:

		critique_purchase = curr_session.query(Critique_Purchase). \
			filter_by(buyer_user_id=buyer_user_id). \
			filter_by(artwork_id=artwork_id). \
			filter_by(critic_user_id=critic_user_id). \
			one()

		curr_session.close()

		return True
	except NoResultFound, e:
		return False
	except Exception, e:
		raise e
	finally:
		curr_session.close()


def get_artist(user_id):
	"""
	Get an instance of an Artist given his/her user_id, together with his/her Image
	:param user_id: the Artist's user_id
	:return an instance of Artist, an instance of Image
	"""

	curr_session = Session()
	try:

		artist = curr_session.query(Artist). \
			filter_by(user_id=user_id). \
			first()

		# Load Image
		if artist is not None:
			image = curr_session.query(Image).filter_by(image_id=artist.image_id).first()
		else:
			image = None

		curr_session.close()

		return artist, image
	except Exception, e:
		raise e
	finally:
		curr_session.close()


def get_artist_followers(artist_id, limit=0, offset=0):
	"""
	Get the followers (list of Buyer) of this Artist.
	:param artist_id: the id of the Artist whose followers will be retrieved
	:param limit: the max number of rows to return, 0 for no limit
	:param offset: the offset (starting point) for the list. E.g. if offset=10, the list will begin at row 11
	:return: a list of Buyer
	"""

	curr_session = Session()

	try:
		# Check limit
		if limit == 0:
			limit = sys.maxint

		buyer_list = []
		follow_artist_list = curr_session.query(Follow_Artist). \
			filter_by(artist_user_id=artist_id). \
			filter_by(follow_artist_status="following"). \
			order_by(Follow_Artist.follow_artist_creation_time.desc()). \
			limit(limit). \
			offset(offset). \
			all()

		# Create list
		for follow_artist in follow_artist_list:
			buyer = follow_artist.buyer
			buyer_list.append(buyer)

			# Touch image
			image = buyer.image

		curr_session.close()

		return buyer_list
	except Exception, e:
		raise e
	finally:
		curr_session.close()


def get_artist_list(limit=0, offset=0, randomize=False):
	"""
	A list of all Artists in alphabetical order.
	:param limit: the max number of rows to return, 0 for no limit
	:param offset: the offset (starting point) for the list. E.g. if offset=10, the list will begin at row 11
	:param randomize: whether to randomize the list or not
	return: a list of Artists
	"""

	curr_session = Session()

	try:

		# Check limit
		if limit == 0:
			limit = sys.maxint

		# Check randomize
		if randomize:
			order_by = func.rand()
		else:
			order_by = Artist.artist_nickname.asc()

		artist_list = curr_session.query(Artist). \
			order_by(order_by). \
			limit(limit). \
			offset(offset). \
			all()

		# Check that Artists are ACTIVE
		artist_list[:] = [artist for artist in artist_list if artist.user.user_status.lower() == "active"]

		# Touch Images
		for artist in artist_list:
			image = artist.image

		curr_session.close()

		return artist_list
	except Exception, e:
		raise e
	finally:
		curr_session.close()


def get_artwork(artwork_id):
	"""
	Get an instance of an Artwork given its artwork_id, together with its Images
	:param artwork_id: the Artwork's artwork_id
	:return an instance of Artwork, a list of Images
	"""

	curr_session = Session()
	try:

		artwork = curr_session.query(Artwork). \
			filter_by(artwork_id=artwork_id). \
			first()

		# Touch Artist
		if artwork is not None:
			artist = artwork.artist

		# Load Images
		if artwork is not None:
			images = []
			for image, artwork_images in curr_session.query(Image, Artwork_Image). \
					filter(and_(Image.image_id == Artwork_Image.image_id,
			               Artwork_Image.artwork_id == artwork.artwork_id)). \
					all():
				images.append(image)
		else:
			images = None

		curr_session.close()

		return artwork, images
	except Exception, e:
		raise e
	finally:
		curr_session.close()


def get_artwork_auction(artwork_id, artwork_auction_id=None):
	"""
	Get an instance of an Artwork_Auction given its artwork_id or artwork_auction_id
	:param artwork_id: the Artwork's artwork_id
	:param artwork_auction_id: the Artwork Auction's id
	:return an instance of Artwork_Auction
	"""

	now = datetime.now()
	curr_session = Session()
	try:

		if artwork_auction_id is None:
			artwork_auction = curr_session.query(Artwork_Auction). \
				filter_by(artwork_id=artwork_id). \
				filter(Artwork_Auction.artwork_auction_end_time >= now). \
				filter(Artwork_Auction.artwork_auction_start_time <= now). \
				order_by(Artwork_Auction.artwork_auction_start_time.desc()). \
				first()
		else:
			artwork_auction = curr_session.query(Artwork_Auction). \
				filter_by(artwork_auction_id=artwork_auction_id). \
				one()

		# Touch related objects
		if artwork_auction is not None:
			current_bid = artwork_auction.current_bid
			all_bids = artwork_auction.artwork_auction_bids
			if current_bid is not None:
				high_bidder = current_bid.buyer
				if high_bidder is not None:
					user = high_bidder.user

		curr_session.close()

		return artwork_auction
	except NoResultFound, e:
		raise InexistentResourceError()
	except Exception, e:
		raise e
	finally:
		curr_session.close()


def get_artwork_auction_list(user_id, sorting_rule):
	"""
	A list of Artwork Auction in which the given Buyer is participating
	Only the Artwork with artwork_status = "AVAILABLE" will be returned.
	:param label_id: the id of the Label
	:param limit: the max number of rows to return (0 for no limit), default=0
	:param offset: the offset (starting point) for the list. E.g. if offset=10, the list will begin at row 11, default=0
	return: a list of Artwork
	"""

	now = datetime.now()
	curr_session = Session()

	# TODO: Check sorting rule
	try:

		artwork_auction_list = []
		for artwork_auction, artwork_auction_bid in \
				curr_session.query(Artwork_Auction, Artwork_Auction_Bid). \
						filter(Artwork_Auction.artwork_auction_end_time >= now). \
						filter(Artwork_Auction.artwork_auction_start_time <= now). \
						filter(Artwork_Auction_Bid.artwork_auction_id == Artwork_Auction.artwork_auction_id). \
						filter(Artwork_Auction_Bid.buyer_user_id == user_id). \
						order_by(Artwork_Auction.artwork_auction_start_time.desc()). \
						all():

			if artwork_auction not in artwork_auction_list:
				artwork_auction_list.append(artwork_auction)

			# Touch related objects
			if artwork_auction is not None:
				# Artwork and Artist
				artwork = artwork_auction.artwork
				artwork_images = artwork.artwork_images
				for artwork_image in artwork_images:
					image = artwork_image.image
				artist = artwork.artist

				# Bids
				current_bid = artwork_auction.current_bid
				all_bids = artwork_auction.artwork_auction_bids
				if current_bid is not None:
					high_bidder = current_bid.buyer
					if high_bidder is not None:
						user = high_bidder.user

		curr_session.close()

		return artwork_auction_list
	except Exception, e:
		raise e
	finally:
		curr_session.close()


def get_artwork_list_from_label(label_id, limit=0, offset=0):
	"""
	A list of Artwork belonging to the given Label.
	Only the Artwork with artwork_status = "AVAILABLE" will be returned.
	:param label_id: the id of the Label
	:param limit: the max number of rows to return (0 for no limit), default=0
	:param offset: the offset (starting point) for the list. E.g. if offset=10, the list will begin at row 11, default=0
	return: a list of Artwork
	"""

	curr_session = Session()

	# Check limit
	if limit == 0:
		limit = sys.maxint

	try:

		artwork_list = []
		for artwork, artwork_label in curr_session.query(Artwork, Artwork_Label). \
			filter(Artwork.artwork_status == 'AVAILABLE'). \
			filter(and_(Artwork_Label.artwork_id == Artwork.artwork_id, Artwork_Label.label_id == label_id)). \
			limit(limit). \
			offset(offset). \
			all():

			artwork_list.append(artwork)

			# Touch images
			for artwork_image in artwork.artwork_images:
				image = artwork_image.image

		curr_session.close()

		return artwork_list
	except Exception, e:
		raise e
	finally:
		curr_session.close()


def get_artwork_list(sorting_rule, artist_id=None, limit=0, offset=0, user_id=None, location=None):
	"""
	A list of Artwork, together with each corresponding ArtworkImages in a dictionary, sorted by one of several rules.
	The artist_id can also be given to return the Artwork of a single Artist.
	Only the Artwork with artwork_status = "AVAILABLE" will be returned.
	:param sorting_rule: the rule to sort by, below are the possible rules:
		1: most popular Artwork
		2: my watched Critics
		3: my watched Artists
		4: my watched Artwork
		5: nearby Galleries (requires location)
		6: latest Artwork (uploaded)
		7: most Critiques
		8: highest to lowest price
		9: lowest to highest price
		10: most popular critique
	:param artist_id: the Artist whose artwork will be retrieved, default=None
	:param limit: the max number of rows to return (0 for no limit), default=0
	:param offset: the offset (starting point) for the list. E.g. if offset=10, the list will begin at row 11, default=0
	:param user_id: the user_id of the requesting User
	:param location: "lat,long" (optional) e.g. 24.971059,121.241765
	return: a list of sorted Artwork, a dictionary with ArtworkImages per Artwork
	"""

	curr_session = Session()

	try:
		# Check sorting_rule
		filter_by = None
		order_by2 = None
		if sorting_rule == 1:
			order_by1 = Artwork.artwork_followed_count.desc()
			order_by2 = Artwork.artwork_display_weight.desc()
		elif sorting_rule == 2:
			filter_by = None  # TODO: change to only show those followed by my watched Critics
			order_by1 = Artwork.artwork_display_weight.desc()
		elif sorting_rule == 3:
			filter_by = None  # TODO: change to only show those followed by my watched Artists
			order_by1 = Artwork.artwork_display_weight.desc()
		elif sorting_rule == 4:
			filter_by = None  # TODO: change to only show those followed by my watched Artwork
			order_by1 = Artwork.artwork_display_weight.desc()
		elif sorting_rule == 5:
			order_by1 = Artwork.artwork_display_weight.desc()  # TODO: Change for location proximity
		elif sorting_rule == 6:
			order_by1 = Artwork.artwork_creation_time.desc()
		elif sorting_rule == 7:
			order_by1 = Artwork.artwork_critique_count.desc()
			order_by2 = Artwork.artwork_display_weight.desc()
		elif sorting_rule == 8:
			order_by1 = Artwork.artwork_display_weight.desc()  # TODO: Change for highest to lowest price
		elif sorting_rule == 9:
			order_by1 = Artwork.artwork_display_weight.desc()  # TODO: Change for lowest to highest price
		elif sorting_rule == 10:
			order_by1 = Artwork.artwork_display_weight.desc()  # TODO: Change for most popular critique
		else:
			raise WrongArgumentValueError()

		# Check artist_id
		if artist_id is not None:
			artist_filter = Artwork.artist_user_id == artist_id
		else:
			artist_filter = True

		# Check limit
		if limit == 0:
			limit = sys.maxint

		if filter_by is None:
			artwork_list = curr_session.query(Artwork). \
				filter(artist_filter). \
				filter_by(artwork_status="AVAILABLE"). \
				order_by(order_by1, order_by2). \
				limit(limit). \
				offset(offset). \
				all()
		else:
			artwork_list = curr_session.query(Artwork). \
				filter(artist_filter). \
				filter_by(filter_by). \
				filter_by(artwork_status="AVAILABLE"). \
				order_by(order_by1, order_by2). \
				limit(limit). \
				offset(offset). \
				all()

		# If empty, just get all the Artwork, ordered by popularity (sorting_rule=1)
		if not artwork_list:
			artwork_list = curr_session.query(Artwork). \
				filter(artist_filter). \
				filter_by(artwork_status="AVAILABLE"). \
				order_by(Artwork.artwork_followed_count.desc(), Artwork.artwork_display_weight.desc()). \
				limit(limit). \
				offset(offset). \
				all()

		# Load Images per Artwork
		artwork_image_dictionary = {}
		for artwork in artwork_list:
			images = []
			for image, artwork_images in curr_session.query(Image, Artwork_Image). \
					filter(and_(Image.image_id == Artwork_Image.image_id,
			               Artwork_Image.artwork_id == artwork.artwork_id)). \
					all():
				images.append(image)
			artwork_image_dictionary[artwork] = images

		curr_session.close()

		return artwork_list, artwork_image_dictionary
	except Exception, e:
		raise e
	finally:
		curr_session.close()


def get_artwork_owner(artwork):
	"""
	Get an instance of a Buyer, Gallery, Auction_House or Artist, which owns this Artwork.
	:param artwork: the Artwork whose owner will be fetched
	:return an instance of Buyer, Gallery, Auction_House or Artist,
		a string with the owner type:
			"BUYER", "GALLERY", "AUCTION_HOUSE", "ARTIST",
		an instance of Image
	"""

	curr_session = Session()
	try:

		if artwork.owner_buyer_user_id is not None:
			table = Buyer
			owner_user_id = artwork.owner_buyer_user_id
			owner_type = "BUYER"
		elif artwork.owner_gallery_user_id is not None:
			table = Gallery
			owner_user_id = artwork.owner_gallery_user_id
			owner_type = "GALLERY"
		elif artwork.owner_auction_house_user_id is not None:
			table = Auction_House
			owner_user_id = artwork.owner_auction_house_user_id
			owner_type = "AUCTION_HOUSE"
		elif artwork.owner_artist_user_id is not None:
			table = Artist
			owner_user_id = artwork.owner_artist_user_id
			owner_type = "ARTIST"
		else:
			return None, None, None

		owner = curr_session.query(table). \
			filter_by(user_id=owner_user_id). \
			first()

		# Load Image
		if owner is not None:
			if owner_type.lower() == "buyer" or owner_type.lower() == "artist":
				owner_image = curr_session.query(Image).filter_by(image_id=owner.image_id).first()
			else:
				owner_image = curr_session.query(Image).filter_by(image_id=owner.banner_image_id).first()
		else:
			owner_image = None

		curr_session.close()

		return owner, owner_type, owner_image
	except Exception, e:
		raise e
	finally:
		curr_session.close()


def get_auction_house(user_id):
	"""
	Get an instance of an Auction_House given its user_id
	:param user_id: the Auction Houses's user id
	:return an instance of Auction_house
	"""

	curr_session = Session()
	try:

		auction_house = curr_session.query(Auction_House). \
			filter_by(user_id=user_id). \
			first()

		# Touch User, Image and Address
		if auction_house is not None:
			user = auction_house.user
			image = auction_house.banner_image
			address = auction_house.address
			city = address.city
			country = city.country

		curr_session.close()

		return auction_house
	except Exception, e:
		raise e
	finally:
		curr_session.close()


def get_auction_house_events(user_id, current=False):
	"""
	Get the Events from a given Auction House.
	:param user_id: the user_id of the Auction House
	:param current: whether only the current events will be displayed or not (all)
	:return: a list of Auction_House_Event
	"""

	now = datetime.now()
	curr_session = Session()

	try:
		# Check current
		if current:
			event_list = curr_session.query(Auction_House_Event). \
				filter_by(auction_house_user_id=user_id). \
				filter(Auction_House_Event.auction_house_event_ending_time >= now). \
				order_by(Auction_House_Event.auction_house_event_ending_time.desc()). \
				all()
		else:
			event_list = curr_session.query(Auction_House_Event). \
				filter_by(auction_house_user_id=user_id). \
				order_by(Auction_House_Event.auction_house_event_ending_time.desc()). \
				all()

		# Touch images
		for event in event_list:
			image = event.image

		curr_session.close()

		return event_list
	except Exception, e:
		raise e
	finally:
		curr_session.close()


def get_auction_house_list(limit=0, offset=0):
	"""
	A list of all Auction Houses in alphabetical order.
	:param limit: the max number of rows to return, 0 for no limit
	:param offset: the offset (starting point) for the list. E.g. if offset=10, the list will begin at row 11
	return: a list of Auction Houses
	"""

	curr_session = Session()

	try:

		# Check limit
		if limit == 0:
			limit = sys.maxint

		auction_house_list = curr_session.query(Auction_House). \
			order_by(Auction_House.auction_house_name.asc()). \
			limit(limit). \
			offset(offset). \
			all()

		# Check that Auction Houses are ACTIVE
		auction_house_list[:] = [auction_house for auction_house in auction_house_list
		                         if auction_house.user.user_status.lower() == "active"]

		# Touch Images
		for auction_house in auction_house_list:
			image = auction_house.banner_image

		curr_session.close()

		return auction_house_list
	except Exception, e:
		raise e
	finally:
		curr_session.close()


@deprecated
def get_banner():
	"""
	Obtain Banner to display in Home screen based on the banner's start_time and end_time.
	return: an instance of a Banner, an instance of an Image
	"""

	now = datetime.now()
	curr_session = Session()

	try:
		# Check available banner for current date
		banner = curr_session.query(Banner). \
			filter(Banner.banner_start_time <= now). \
			filter(Banner.banner_end_time >= now). \
			order_by(Banner.banner_end_time.desc()). \
			first()

		# If None, just get the banner with the latest end time
		if banner is None:
			banner = curr_session.query(Banner). \
				order_by(Banner.banner_end_time.desc()). \
				first()

		if banner is None:
			image = None
		else:
			# Load Image
			image = curr_session.query(Image).filter_by(image_id=banner.image_id).first()

		curr_session.close()

		return banner, image
	except Exception, e:
		raise e
	finally:
		curr_session.close()


def get_banner_list():
	"""
	Obtain a list of Banners to display in Home screen based on the banners' start_time and end_time.
	return: an list of Banners
	"""

	now = datetime.now()
	curr_session = Session()

	try:
		# Check available banners for current date
		banner_list = curr_session.query(Banner). \
			filter(Banner.banner_start_time <= now). \
			filter(Banner.banner_end_time >= now). \
			order_by(Banner.banner_end_time.desc()). \
			all()

		# If there are no Banners, just get the Banner with the latest end time
		if not banner_list:
			banner = curr_session.query(Banner). \
				order_by(Banner.banner_end_time.desc()). \
				first()
			banner_list = [banner]

		# Touch images
		for banner in banner_list:
			image = banner.image

		curr_session.close()

		return banner_list
	except Exception, e:
		raise e
	finally:
		curr_session.close()


def get_buyer(user_id):
	"""
	Get an instance of an Buyer given his/her user_id
	:param user_id: the Buyer's user_id
	:return an instance of Buyer
	"""

	curr_session = Session()
	try:

		buyer = curr_session.query(Buyer). \
			filter_by(user_id=user_id). \
			one()

		curr_session.close()

		return buyer
	except NoResultFound, e:
		raise UserInexistentError()
	except Exception, e:
		raise e
	finally:
		curr_session.close()


def get_buyer_artwork(user_id, limit=0, offset=0):
	"""
	Get the Artworks owned by the given Buyer
	:param user_id: the id of the Buyer
	:param limit: the max number of rows to return, 0 for no limit
	:param offset: the offset (starting point) for the list. E.g. if offset=10, the list will begin at row 11
	:return: a list of owned Artworks
	"""

	curr_session = Session()

	try:
		# Check limit
		if limit == 0:
			limit = sys.maxint

		artwork_list = curr_session.query(Artwork). \
			filter_by(owner_buyer_user_id=user_id). \
			order_by(Artwork.artwork_display_weight). \
			limit(limit). \
			offset(offset). \
			all()

		# Touch images
		for artwork in artwork_list:
			images = artwork.artwork_images
			for artwork_image in images:
				image = artwork_image.image

		curr_session.close()

		return artwork_list
	except Exception, e:
		raise e
	finally:
		curr_session.close()


def get_critique_list(artwork_id=None, critic_id=None, limit=0, offset=0, user_id=None):
	"""
	A list of Critique given an artwork_id or a critic_id.
	:param artwork_id: the id of the Artwork whose Critiques will be retrieved
	:param critic_id: the id of the Critic whose Critiques will be retrieved
	:param limit: the max number of rows to return, 0 for no limit
	:param offset: the offset (starting point) for the list. E.g. if offset=10, the list will begin at row 11
	:param user_id: the user_id of the requesting User
	return: a list of Critiques
	"""

	now = datetime.now()
	curr_session = Session()

	try:

		# Check limit
		if limit == 0:
			limit = sys.maxint

		# Check filter
		if artwork_id is not None:
			critique_list = curr_session.query(Critique). \
				filter_by(artwork_id=artwork_id). \
				filter_by(critique_status="APPROVED"). \
				order_by(Critique.critique_upvote_count.desc()). \
				limit(limit). \
				offset(offset). \
				all()
		elif critic_id is not None:
			critique_list = curr_session.query(Critique). \
				filter_by(critic_id=critic_id). \
				filter_by(critique_status="APPROVED"). \
				order_by(Critique.critique_upvote_count.desc()). \
				limit(limit). \
				offset(offset). \
				all()
		else:
			return None

		# Touch Critics
		for critique in critique_list:
			critic = critique.critic

		curr_session.close()

		return critique_list
	except Exception, e:
		raise e
	finally:
		curr_session.close()


def get_critique_vote_type(buyer_user_id, artwork_id, critic_user_id):
	"""
	Get type of Critique vote ("LIKED", "DISLIKED", "NONE")
	:param buyer_user_id: the id of the Buyer
	:param artwork_id: the id of the Artwork (PK for Critique)
	:param critic_user_id: the id of the Critic (PK for Critique)
	:return: "LIKED", "DISLIKED", or None if user hasn't voted
	"""

	curr_session = Session()
	try:

		critique_vote = curr_session.query(Critique_Vote). \
			filter_by(buyer_user_id=buyer_user_id). \
			filter_by(artwork_id=artwork_id). \
			filter_by(critic_user_id=critic_user_id). \
			first()

		if critique_vote is not None:
			return critique_vote.critique_vote_type
		else:
			return "N"

	except NoResultFound, e:
		return False
	except Exception, e:
		raise e
	finally:
		curr_session.close()


def get_followed_artists(user_id, limit=0, offset=0):
	"""
	Get the Artists followed by the given Buyer
	:param user_id: the id of the requesting Buyer
	:param limit: the max number of rows to return, 0 for no limit
	:param offset: the offset (starting point) for the list. E.g. if offset=10, the list will begin at row 11
	:return: a list of followed Artists sorted by name
	"""

	curr_session = Session()

	try:
		# Check limit
		if limit == 0:
			limit = sys.maxint

		artist_list = []
		for followed_artist, artist in curr_session.query(Follow_Artist, Artist). \
				filter_by(buyer_user_id=user_id). \
				filter_by(follow_artist_status="following"). \
				filter(Follow_Artist.artist_user_id == Artist.user_id). \
				order_by(Artist.artist_nickname). \
				limit(limit). \
				offset(offset). \
				all():

			artist_list.append(artist)

			# Touch image
			image = artist.image

		curr_session.close()

		return artist_list
	except Exception, e:
		raise e
	finally:
		curr_session.close()


def get_followed_artwork(user_id, limit=0, offset=0, get_favorite=False):
	"""
	Get the Artwork followed by the given Buyer
	:param user_id: the id of the requesting Buyer
	:param limit: the max number of rows to return, 0 for no limit
	:param offset: the offset (starting point) for the list. E.g. if offset=10, the list will begin at row 11
	:param get_favorite: whether to only retrieve the favorite Artwork of the Buyer or not
	:return: a list of followed Artwork sorted by name
	"""

	curr_session = Session()

	try:
		# Check limit
		if limit == 0:
			limit = sys.maxint

		favorite_filter = Follow_Artwork.is_favorite == True if get_favorite else True == True

		artwork_list = []
		for followed_artwork, artwork in curr_session.query(Follow_Artwork, Artwork). \
				filter_by(buyer_user_id=user_id). \
				filter_by(follow_artwork_status="following"). \
				filter(Follow_Artwork.artwork_id == Artwork.artwork_id). \
				filter(favorite_filter). \
				order_by(Artwork.artwork_name). \
				limit(limit). \
				offset(offset). \
				all():

			artwork_list.append(artwork)

			# Touch images
			images = artwork.artwork_images
			for artwork_image in images:
				image = artwork_image.image

		curr_session.close()

		return artwork_list
	except Exception, e:
		raise e
	finally:
		curr_session.close()


def get_followed_auction_houses(user_id, limit=0, offset=0):
	"""
	Get the Auction Houses followed by the given Buyer
	:param user_id: the id of the requesting Buyer
	:param limit: the max number of rows to return, 0 for no limit
	:param offset: the offset (starting point) for the list. E.g. if offset=10, the list will begin at row 11
	:return: a list of followed Auction Houses sorted by name
	"""

	curr_session = Session()

	try:
		# Check limit
		if limit == 0:
			limit = sys.maxint

		auction_house_list = []
		for followed_auction_house, auction_house in curr_session.query(Follow_Auction, Auction_House). \
				filter_by(buyer_user_id=user_id). \
				filter_by(follow_auction_status="following"). \
				filter(Follow_Auction.auction_house_user_id == Auction_House.user_id). \
				order_by(Auction_House.auction_house_name). \
				limit(limit). \
				offset(offset). \
				all():

			auction_house_list.append(auction_house)

			# Touch image
			image = auction_house.banner_image

		curr_session.close()

		return auction_house_list
	except Exception, e:
		raise e
	finally:
		curr_session.close()


def get_followed_critics(user_id, limit=0, offset=0):
	"""
	Get the Critics followed by the given Buyer
	:param user_id: the id of the requesting Buyer
	:param limit: the max number of rows to return, 0 for no limit
	:param offset: the offset (starting point) for the list. E.g. if offset=10, the list will begin at row 11
	:return: a list of followed Critics sorted by name
	"""

	curr_session = Session()

	try:
		# Check limit
		if limit == 0:
			limit = sys.maxint

		critic_list = []
		for followed_critic, critic in curr_session.query(Follow_Critic, Critic). \
				filter_by(buyer_user_id=user_id). \
				filter_by(follow_critic_status="following"). \
				filter(Follow_Critic.critic_user_id == Critic.user_id). \
				order_by(Critic.critic_nickname). \
				limit(limit). \
				offset(offset). \
				all():

			critic_list.append(critic)

		curr_session.close()

		return critic_list
	except Exception, e:
		raise e
	finally:
		curr_session.close()


def get_followed_galleries(user_id, limit=0, offset=0):
	"""
	Get the Galleries followed by the given Buyer
	:param user_id: the id of the requesting Buyer
	:param limit: the max number of rows to return, 0 for no limit
	:param offset: the offset (starting point) for the list. E.g. if offset=10, the list will begin at row 11
	:return: a list of followed Galleries sorted by name
	"""

	curr_session = Session()

	try:
		# Check limit
		if limit == 0:
			limit = sys.maxint

		gallery_list = []
		for followed_gallery, gallery in curr_session.query(Follow_Gallery, Gallery). \
				filter_by(buyer_user_id=user_id). \
				filter_by(follow_gallery_status="following"). \
				filter(Follow_Gallery.gallery_user_id == Gallery.user_id). \
				order_by(Gallery.gallery_name). \
				limit(limit). \
				offset(offset). \
				all():

			gallery_list.append(gallery)

			# Touch image
			image = gallery.banner_image

		curr_session.close()

		return gallery_list
	except Exception, e:
		raise e
	finally:
		curr_session.close()


def get_gallery(user_id):
	"""
	Get an instance of a Gallery given its user_id
	:param user_id: the Auction Houses's user id
	:return an instance of Auction_house
	"""

	curr_session = Session()
	try:

		gallery = curr_session.query(Gallery). \
			filter_by(user_id=user_id). \
			first()

		# Touch User, Image and Address
		if gallery is not None:
			user = gallery.user
			image = gallery.banner_image
			address = gallery.address
			city = address.city
			country = city.country

		curr_session.close()

		return gallery
	except Exception, e:
		raise e
	finally:
		curr_session.close()


def get_gallery_events(user_id, current=False):
	"""
	Get the Events from a given Gallery.
	:param user_id: the user_id of the Gallery
	:param current: whether only the current events will be displayed or not (all)
	:return: a list of Gallery_Event
	"""

	now = datetime.now()
	curr_session = Session()

	try:
		# Check current
		if current:
			event_list = curr_session.query(Gallery_Event). \
				filter_by(gallery_user_id=user_id). \
				filter(Gallery_Event.gallery_event_ending_time >= now). \
				order_by(Gallery_Event.gallery_event_ending_time.desc()). \
				all()
		else:
			event_list = curr_session.query(Gallery_Event). \
				filter_by(gallery_user_id=user_id). \
				order_by(Gallery_Event.gallery_event_ending_time.desc()). \
				all()

		# Touch images
		for event in event_list:
			image = event.image

		curr_session.close()

		return event_list
	except Exception, e:
		raise e
	finally:
		curr_session.close()


def get_gallery_list(limit=0, offset=0):
	"""
	A list of all Galleries in alphabetical order.
	:param limit: the max number of rows to return, 0 for no limit
	:param offset: the offset (starting point) for the list. E.g. if offset=10, the list will begin at row 11
	return: a list of Galleries
	"""

	curr_session = Session()

	try:

		# Check limit
		if limit == 0:
			limit = sys.maxint

		gallery_list = curr_session.query(Gallery). \
			order_by(Gallery.gallery_name.asc()). \
			limit(limit). \
			offset(offset). \
			all()

		# Check that Galleries are ACTIVE
		gallery_list[:] = [gallery for gallery in gallery_list if gallery.user.user_status.lower() == "active"]

		# Touch Images
		for gallery in gallery_list:
			image = gallery.banner_image

		curr_session.close()

		return gallery_list
	except Exception, e:
		raise e
	finally:
		curr_session.close()


def get_label_list(limit=0, offset=0):
	"""
	A list of all Labels in alphabetical order.
	:param limit: the max number of rows to return, 0 for no limit
	:param offset: the offset (starting point) for the list. E.g. if offset=10, the list will begin at row 11
	return: a list of Labels
	"""

	curr_session = Session()

	try:

		# Check limit
		if limit == 0:
			limit = sys.maxint

		label_list = curr_session.query(Label). \
			order_by(Label.label_name.asc()). \
			limit(limit). \
			offset(offset). \
			all()

		curr_session.close()

		return label_list
	except Exception, e:
		raise e
	finally:
		curr_session.close()


def get_preferred_labels(user_id, top_n=0):
	"""
	Get the top n Labels preferred by the given Buyer
	:param user_id: the id of the requesting Buyer
	:param top_n: the top n preferred Labels to retrieve, 0 for no limit
	:return: a list of top n preferred Labels
	"""

	curr_session = Session()

	try:
		# Check top_n
		if top_n == 0:
			top_n = sys.maxint


		label_list = []
		for followed_artwork, artwork, artwork_label in curr_session.query(Follow_Artwork, Artwork, Artwork_Label). \
				filter_by(buyer_user_id=user_id). \
				filter_by(follow_artwork_status="following"). \
				filter(and_(Follow_Artwork.artwork_id == Artwork.artwork_id,
		                    Artwork.artwork_id == Artwork_Label.artwork_id)). \
				group_by(Artwork_Label.label_id). \
				order_by(func.count(Artwork_Label.label_id).desc()). \
				all():

			label_list.append(artwork_label.label)

		curr_session.close()

		return label_list
	except Exception, e:
		raise e
	finally:
		curr_session.close()


def login(user_email, user_password):
	"""
	Log in to the ArtMeGo system using the given user email and password (hash-encrypted using SHA-256)
	:param user_email: The user email (hash-encrypted using SHA-256)
	:param user_password: The user password (hash-encrypted using SHA-256)
	:return: an instance of the User class
	"""

	curr_session = Session()
	try:
		user = curr_session.query(User).filter_by(user_hashed_email=user_email).one()

		# Check password
		if user.user_password != user_password:
			raise AuthenticationError()

		# Check status TODO: Add this later
		#if user.user_status.lower() != "active":
		#	raise UnauthorizedError()

		return user
	except NoResultFound, e:
		raise UserInexistentError()
	except Exception, e:
		raise e
	finally:
		curr_session.close()


def login_facebook(fb_id, user_email):
	"""
	Log in to the ArtMeGo system using the given user email and password (hash-encrypted using SHA-256)
	:param fb_id: the Facebook id to check
	:param user_email: the user's email to check
	:return: an instance of the User class
	"""

	curr_session = Session()
	try:
		buyer = curr_session.query(Buyer).filter_by(facebook_id=fb_id).one()

		# Check status TODO: Add this later
		#if user.user_status.lower() != "active":
		#	raise UnauthorizedError()

		user = buyer.user

		# Check that user_email matches
		if user_email != user.user_email:
			raise AuthenticationError()

		return user
	except NoResultFound, e:
		raise UserInexistentError()
	except Exception, e:
		raise e
	finally:
		curr_session.close()


################################### TESTING ###################################


def add_sample_data1():
	curr_session = Session()
	now = datetime.now()
	one_month = timedelta(days=30)
	later = now + one_month

	try:
		# Address
		country = Country(country_code=886, country_name="Taiwan", country_creation_time=now,
		                  country_modification_time=now)
		curr_session.add(country)
		curr_session.flush()

		city = City(country_id=country.country_id, city_name="Hsinchu", city_creation_time=now,
		            city_modification_time=now)
		curr_session.add(city)
		curr_session.flush()

		address = Address(address_line1="Guangfu Road, Sec. 2", address_line2="No. 101", address_postal_code=30013,
		                  city_id=city.city_id, geolocation=u"24°49′N 120°59′E", phone_number="",
		                  mobile_phone_number="0975314927", address_creation_time=now, address_modification_time=now)
		curr_session.add(address)
		curr_session.flush()

		# Image
		image = Image(image_name="Image1", image_path="path/to/image", image_creation_time=now,
		              image_modification_time=now)
		curr_session.add(image)
		curr_session.flush()

		# Banner
		banner = Banner(banner_name="Banner", banner_text="This is a test banner", image_id=image.image_id,
		                banner_start_time=now, banner_end_time=later, banner_creation_time=now,
		                banner_modification_time=now)
		curr_session.add(banner)
		curr_session.flush()

		# Users
		password = "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"  # SHA256 for "password"

		admin_user_hashed_email = "d68471ba4a66859cd38277a6bdb9ffe54f0ba87030a892efd456b6dc5c6f4328"  # SHA256
		admin_user = User(user_email="admin@artmego.com", user_hashed_email=admin_user_hashed_email,
		                  user_type="ADMINISTRATOR", user_password=password, user_status="UNCONFIRMED",
		                  user_creation_time=now, user_modification_time=now)
		curr_session.add(admin_user)
		curr_session.flush()

		administrator = Administrator(user_id=admin_user.user_id, administrator_name="Administrator",
		                              administrator_modification_time=now)
		curr_session.add(administrator)
		curr_session.flush()

		buyer_user_hashed_email = "bcd3d4a1d0fe347c8023ce6fdc8e5b4ab4de2f8f217867cc4f63d994a0dea4f1"  # SHA256
		buyer_user = User(user_email="gerardo_ofc@yahoo.com", user_hashed_email=buyer_user_hashed_email,
		                  user_type="BUYER", user_password=password, user_status="UNCONFIRMED", user_creation_time=now,
		                  user_modification_time=now)
		curr_session.add(buyer_user)
		curr_session.flush()

		buyer = Buyer(user_id=buyer_user.user_id, buyer_type="GOLD", buyer_first_name="Gerardo",
		              buyer_last_name="Figueroa", buyer_nickname="Gerardo", buyer_gender="m", buyer_birthday=now,
		              buyer_occupation="Student", address_id=address.address_id, image_id=image.image_id,
		              buyer_modification_time=now)
		curr_session.add(buyer)

		curr_session.commit()
	except Exception, e:
		curr_session.rollback()
		raise e

	our_user = curr_session.query(User).filter_by(user_email="gerardo_ofc@yahoo.com").first()
	our_buyer = curr_session.query(Buyer).filter_by(user=our_user).first()

	print our_user
	print our_buyer

	curr_session.close()


def add_sample_data2():
	curr_session = Session()
	now = datetime.now()
	one_month = timedelta(days=30)
	later = now + one_month

	try:
		'''
		# Address
		country = Country(country_code=504, country_name="Honduras", country_creation_time=now,
		                  country_modification_time=now)
		curr_session.add(country)
		curr_session.flush()

		city = City(country_id=country.country_id, city_name="Tegucigalpa", city_creation_time=now,
		            city_modification_time=now)
		curr_session.add(city)
		curr_session.flush()

		address = Address(address_line1="Col. Rio Grande", address_line2="No. 101", address_postal_code=504,
		                  city_id=city.city_id, geolocation=u"24°49′N 120°59′E", phone_number="",
		                  mobile_phone_number="0975314927", address_creation_time=now, address_modification_time=now)
		curr_session.add(address)
		curr_session.flush()

		# Image
		image = Image(image_name="Image2", image_path="path/to/image", image_creation_time=now,
		              image_modification_time=now)
		curr_session.add(image)
		curr_session.flush()
		'''
		# Users
		password = "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"  # SHA256 for "password"
		'''
		artist_user_hashed_email = "11c98297602d2cfc3e97ceb591c4a105ab536065a7e83c4719104162d556842e"  # SHA256
		artist_user = User(user_email="artist@artmego.com", user_hashed_email=artist_user_hashed_email,
		                   user_type="ARTIST", user_password=password, user_status="UNCONFIRMED", user_creation_time=now,
		                   user_modification_time=now)
		curr_session.add(artist_user)
		curr_session.flush()

		artist = Artist(user_id=artist_user.user_id, artist_first_name="Artist", artist_last_name="",
		                artist_nickname="Artist", address_id=address.address_id, artist_description="Cool artist",
		                image_id=image.image_id, artist_modification_time=now)
		curr_session.add(artist)
		curr_session.flush()
		'''
		auction_house_user_hashed_email = "61791f7bed1e39791337dbd267512bfcb158cc7cc2675ffbe5c310bde5b91589"  # SHA256
		auction_house_user = User(user_email="auction_house@artmego.com", user_hashed_email=auction_house_user_hashed_email,
		                          user_type="AUCTION_HOUSE", user_password=password, user_status="UNCONFIRMED",
		                          user_creation_time=now, user_modification_time=now)
		curr_session.add(auction_house_user)
		curr_session.flush()

		auction_house = Auction_House(user_id=auction_house_user.user_id, auction_house_name="Auction House",
		                              auction_house_description="Cool auction house",
		                              address_id=1, banner_image_id=None, auction_house_followed_count=0,
		                              auction_house_modification_time=now)
		curr_session.add(auction_house)
		curr_session.flush()
		'''
		critic_user_hashed_email = "c5ef914ceb8002854dc987c77b55c509b66dc98a58dc58039ceb83f2be335315"  # SHA256
		critic_user = User(user_email="critic@artmego.com", user_hashed_email=critic_user_hashed_email,
		                   user_type="CRITIC", user_password=password, user_status="UNCONFIRMED", user_creation_time=now,
		                   user_modification_time=now)
		curr_session.add(critic_user)
		curr_session.flush()

		critic = Critic(user_id=critic_user.user_id, critic_first_name="Critic", critic_last_name="",
		                critic_nickname="Critic", address_id=address.address_id, critic_level=2,
		                critic_modification_time=now)
		curr_session.add(critic)
		curr_session.flush()

		gallery_user_hashed_email = "e089c4c3aff73a92ff10e631865673c13a8089d841f9c28b68a991ae751f5d35"  # SHA256
		gallery_user = User(user_email="gallery@artmego.com", user_hashed_email=gallery_user_hashed_email,
		                    user_type="GALLERY", user_password=password, user_status="UNCONFIRMED",
		                    user_creation_time=now, user_modification_time=now)
		curr_session.add(gallery_user)
		curr_session.flush()

		gallery = Gallery(user_id=gallery_user.user_id, gallery_name="Gallery", gallery_description="Cool gallery",
		                  address_id=address.address_id, banner_image_id=image.image_id, gallery_modification_time=now)
		curr_session.add(gallery)
		curr_session.flush()

		# Artwork
		artwork = Artwork(artist_user_id=artist.user_id, artwork_name="Artwork", artwork_description="Nice art",
		                  artwork_date='', artwork_followed_count=0, artwork_critique_count=0,
		                  artwork_status="AVAILABLE", artwork_blog_url="", owner_gallery_user_id=gallery.user_id,
		                  artwork_display_weight=100, artwork_creation_time=now, artwork_modification_time=now)
		curr_session.add(artwork)
		curr_session.flush()

		artwork_image = Artwork_Image(artwork_id=artwork.artwork_id, image_id=image.image_id,
		                              artwork_image_creation_time=now, artwork_image_modification_time=now)
		curr_session.add(artwork_image)
		curr_session.flush()
		'''
		curr_session.commit()
	except Exception, e:
		curr_session.rollback()
		raise e

	curr_session.close()


def test_queries():
	curr_session = Session()

	for user in curr_session.query(User).order_by(User.user_id):
		print user

	# Banner test
	now = datetime.now()
	banner = curr_session.query(Banner).filter(Banner.banner_start_time <= now).\
		filter(Banner.banner_end_time >= now).first()
	print banner

	curr_session.close()


# For testing
if __name__ == "__main__":
	option = 0
	while option != 4:
		print "SQLAlchemy ORM Test"
		print "1. Add sample data 1"
		print "2. Add sample data 2"
		print "3. Test queries"
		print "4. Exit"
		option = int(raw_input("Enter an option: "))

		if option == 1:
			add_sample_data1()
		elif option == 2:
			add_sample_data2()
		elif option == 3:
			test_queries()
		else:
			print "Bye :)"