# coding=utf-8
"""
This module contains the ORM (Object Relational Mapping) tables to map Python classes with MySQL tables.
The ORM used is the SQLAlchemy package.
"""

import logging

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Text, SmallInteger, Float, Boolean
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship


logger = logging.getLogger('artmego.' + __name__)

BaseTable = declarative_base()  # The base table class


################################### TABLES ###################################


class Address(BaseTable):
	__tablename__ = "Address"

	address_id = Column(BigInteger, primary_key=True)
	address_line1 = Column(String(50))
	address_line2 = Column(String(50))
	address_postal_code = Column(Integer)
	city_id = Column(BigInteger, ForeignKey('City.city_id'))
	geolocation = Column(String(40))
	phone_number = Column(String(20))
	mobile_phone_number = Column(String(20))
	address_website = Column(String(50))
	address_comments = Column(String(50))
	address_creation_time = Column(DateTime)
	address_modification_time = Column(DateTime)

	# One-to-one relationships
	artist= relationship("Artist", uselist=False, backref="address")
	auction_house = relationship("Auction_House", uselist=False, backref="address")
	buyer = relationship("Buyer", uselist=False, backref="address")
	critic = relationship("Critic", uselist=False, backref="address")
	gallery = relationship("Gallery", uselist=False, backref="address")


class Administrator(BaseTable):
	__tablename__ = "Administrator"

	user_id = Column(BigInteger, ForeignKey('User.user_id'), primary_key=True)
	administrator_name = Column(String(50))
	administrator_comments = Column(String(50))
	administrator_modification_time = Column(DateTime)


class Artist(BaseTable):
	__tablename__ = "Artist"

	user_id = Column(BigInteger, ForeignKey('User.user_id'), primary_key=True)
	artist_first_name = Column(String(50))
	artist_last_name = Column(String(50))
	artist_nickname = Column(String(50))
	address_id = Column(BigInteger, ForeignKey('Address.address_id'))
	artist_description = Column(Text)
	image_id = Column(BigInteger, ForeignKey('Image.image_id'))
	artist_followed_count = Column(Integer)
	artist_comments = Column(String(50))
	artist_modification_time = Column(DateTime)

	# One-to-many relationship
	artworks = relationship("Artwork", backref="artist", foreign_keys="Artwork.artist_user_id")
	owned_artworks = relationship("Artwork", backref="owner_artist", foreign_keys="Artwork.owner_artist_user_id")
	followers = relationship("Follow_Artist")

class Artwork(BaseTable):
	__tablename__ = "Artwork"

	artwork_id = Column(BigInteger, primary_key=True)
	artist_user_id = Column(BigInteger, ForeignKey('Artist.user_id'))
	artwork_name = Column(String(50))
	artwork_description = Column(Text)
	artwork_size = Column(String(30))
	artwork_medium = Column(String(20))
	artwork_date = Column(String(30))
	artwork_followed_count = Column(Integer)
	artwork_critique_count = Column(Integer)
	artwork_status = Column(String(20))
	artwork_blog_url = Column(String(100))
	owner_buyer_user_id = Column(BigInteger, ForeignKey('Buyer.user_id'))
	owner_gallery_user_id = Column(BigInteger, ForeignKey('Gallery.user_id'))
	owner_auction_house_user_id = Column(BigInteger, ForeignKey('Auction_House.user_id'))
	owner_artist_user_id = Column(BigInteger, ForeignKey('Artist.user_id'))
	artwork_display_weight = Column(Integer)
	artwork_creation_time = Column(DateTime)
	artwork_modification_time = Column(DateTime)

	# One-to-Many relationship
	artwork_images = relationship("Artwork_Image")
	critiques = relationship("Critique")


class Artwork_Auction(BaseTable):
	__tablename__ = "Artwork_Auction"

	artwork_auction_id = Column(BigInteger, primary_key=True)
	artwork_id = Column(BigInteger, ForeignKey('Artwork.artwork_id'))
	artwork_auction_current_bid = Column(BigInteger, ForeignKey('Artwork_Auction_Bid.artwork_auction_bid_id'))
	artwork_auction_minimum_bid = Column(Float(12, False, 2))
	artwork_auction_bid_increment = Column(Float(12, False, 2))
	artwork_auction_start_time = Column(DateTime)
	artwork_auction_end_time = Column(DateTime)
	artwork_auction_fixed_price = Column(Float(12, False, 2))
	artwork_auction_creation_time = Column(DateTime)
	artwork_auction_modification_time = Column(DateTime)

	# Many-to-One relationship
	artwork = relationship("Artwork", backref="artwork_auctions")
	current_bid = relationship("Artwork_Auction_Bid", foreign_keys=[artwork_auction_current_bid])


class Artwork_Auction_Bid(BaseTable):
	__tablename__ = "Artwork_Auction_Bid"

	artwork_auction_bid_id = Column(BigInteger, primary_key=True)
	artwork_auction_id = Column(BigInteger, ForeignKey('Artwork_Auction.artwork_auction_id'))
	buyer_user_id = Column(BigInteger, ForeignKey('Buyer.user_id'))
	artwork_auction_bid_amount = Column(Float(12, False, 2))
	artwork_auction_bid_creation_time = Column(DateTime)

	# Many-to-One relationship
	artwork_auction = relationship("Artwork_Auction", backref="artwork_auction_bids", foreign_keys=[artwork_auction_id])
	buyer = relationship("Buyer", backref="artwork_auction_bids")


class Artwork_Image(BaseTable):
	__tablename__ = "Artwork_Image"

	artwork_id = Column(BigInteger, ForeignKey('Artwork.artwork_id'), primary_key=True)
	image_id = Column(BigInteger, ForeignKey('Image.image_id'), primary_key=True)
	artwork_image_creation_time = Column(DateTime)
	artwork_image_modification_time = Column(DateTime)

	# Many-to-One relationship
	image = relationship("Image")


class Artwork_Label(BaseTable):
	__tablename__ = "Artwork_Label"

	artwork_id = Column(BigInteger, ForeignKey('Artwork.artwork_id'), primary_key=True)
	label_id = Column(BigInteger, ForeignKey('Label.label_id'), primary_key=True)
	artwork_label_weight = Column(Float(12, False, 2))
	artwork_label_creation_time = Column(DateTime)
	artwork_label_modification_time = Column(DateTime)

	# Many-to-One relationship
	artwork = relationship("Artwork", backref="artwork_labels")
	label = relationship("Label", backref="artwork_labels")


class Auction_House(BaseTable):
	__tablename__ = "Auction_House"

	user_id = Column(BigInteger, ForeignKey('User.user_id'), primary_key=True)
	auction_house_name = Column(String(50))
	auction_house_description = Column(Text)
	address_id = Column(BigInteger, ForeignKey('Address.address_id'))
	banner_image_id = Column(BigInteger, ForeignKey('Image.image_id'))
	auction_house_followed_count = Column(Integer)
	auction_house_comments = Column(String(50))
	auction_house_modification_time = Column(DateTime)

	# One-to-many relationship
	owned_artworks = relationship("Artwork", backref="owner_auction_house")
	events = relationship("Auction_House_Event", backref="auction_house")


class Auction_House_Event(BaseTable):
	__tablename__ = "Auction_House_Event"

	auction_house_event_id = Column(BigInteger, primary_key=True)
	auction_house_user_id = Column(BigInteger, ForeignKey('Auction_House.user_id'))
	auction_house_event_name = Column(String(50))
	auction_house_event_description = Column(Text)
	image_id = Column(BigInteger, ForeignKey('Image.image_id'))
	auction_house_event_starting_time = Column(DateTime)
	auction_house_event_ending_time = Column(DateTime)
	auction_house_event_creation_time = Column(DateTime)
	auction_house_event_modification_time = Column(DateTime)

	# Many to one relationship
	image = relationship("Image")


class Banner(BaseTable):
	__tablename__ = "Banner"

	banner_id = Column(BigInteger, primary_key=True)
	banner_name = Column(String(50))
	banner_text = Column(String(50))
	image_id = Column(BigInteger, ForeignKey('Image.image_id'))
	banner_start_time = Column(DateTime)
	banner_end_time = Column(DateTime)
	banner_comments = Column(String(50))
	banner_creation_time = Column(DateTime)
	banner_modification_time = Column(DateTime)


class Buyer(BaseTable):
	__tablename__ = "Buyer"

	user_id = Column(BigInteger, ForeignKey('User.user_id'), primary_key=True)
	facebook_id = Column(BigInteger)
	buyer_type = Column(String(10))
	buyer_first_name = Column(String(50))
	buyer_last_name = Column(String(50))
	buyer_nickname = Column(String(50))
	buyer_gender = Column(String(1))
	buyer_birthday = Column(DateTime)
	buyer_occupation = Column(String(20))
	address_id = Column(BigInteger, ForeignKey('Address.address_id'))
	image_id = Column(BigInteger, ForeignKey('Image.image_id'))
	buyer_points = Column(Integer)
	buyer_cash = Column(Float(12, False, 2))
	buyer_comments = Column(String(50))
	buyer_modification_time = Column(DateTime)

	# One-to-many relationship
	owned_artworks = relationship("Artwork", backref="owner_buyer")
	followed_artists = relationship("Follow_Artist")


class City(BaseTable):
	__tablename__ = "City"

	city_id = Column(BigInteger, primary_key=True)
	country_id = Column(BigInteger, ForeignKey('Country.country_id'))
	city_name = Column(String(50))
	city_creation_time = Column(DateTime)
	city_modification_time = Column(DateTime)

	# One-to-many relationship
	addresses = relationship("Address", backref="city")


class Country(BaseTable):
	__tablename__ = "Country"

	country_id = Column(BigInteger, primary_key=True)
	country_code = Column(Integer)
	country_name = Column(String(50))
	country_creation_time = Column(DateTime)
	country_modification_time = Column(DateTime)

	# One-to-many relationship
	cities = relationship("City", backref="country")


class Critic(BaseTable):
	__tablename__ = "Critic"

	user_id = Column(BigInteger, ForeignKey('User.user_id'), primary_key=True)
	critic_first_name = Column(String(50))
	critic_last_name = Column(String(50))
	critic_nickname = Column(String(50))
	address_id = Column(BigInteger, ForeignKey('Address.address_id'))
	critic_level = Column(SmallInteger)
	critic_followed_count = Column(Integer)
	critic_comments = Column(String(50))
	critic_modification_time = Column(DateTime)

	# One-to-Many relationship
	critiques = relationship("Critique")


class Critique(BaseTable):
	__tablename__ = "Critique"

	artwork_id = Column(BigInteger, ForeignKey('Artwork.artwork_id'), primary_key=True)
	critic_user_id = Column(BigInteger, ForeignKey('Critic.user_id'), primary_key=True)
	critique_text = Column(Text)
	critique_point_price = Column(Integer)
	critique_upvote_count = Column(Integer)
	critique_downvote_count = Column(Integer)
	critique_status = Column(String(20))
	critique_comments = Column(String(50))
	critique_creation_time = Column(DateTime)
	critique_modification_time = Column(DateTime)

	# Many-to-One relationship
	artwork = relationship("Artwork")
	critic = relationship("Critic")


class Critique_Purchase(BaseTable):
	__tablename__ = "Critique_Purchase"

	critique_purchase_id = Column(BigInteger, primary_key=True)
	artwork_id = Column(BigInteger, ForeignKey('Critique.artwork_id'))
	critic_user_id = Column(BigInteger, ForeignKey('Critique.critic_user_id'))
	buyer_user_id = Column(BigInteger, ForeignKey('Buyer.user_id'))
	critique_purchase_creation_time = Column(DateTime)

	# Many-to-One relationship
	critique = relationship("Critique", primaryjoin="and_(Critique_Purchase.artwork_id==Critique.artwork_id, "
	                                                "Critique_Purchase.critic_user_id==Critique.critic_user_id)")
	buyer = relationship("Buyer")


class Critique_Vote(BaseTable):
	__tablename__ = "Critique_Vote"

	artwork_id = Column(BigInteger, ForeignKey('Critique.artwork_id'), primary_key=True)
	critic_user_id = Column(BigInteger, ForeignKey('Critique.critic_user_id'), primary_key=True)
	buyer_user_id = Column(BigInteger, ForeignKey('Buyer.user_id'), primary_key=True)
	critique_vote_type = Column(String)
	critique_vote_creation_time = Column(DateTime)
	critique_vote_modification_time = Column(DateTime)

	# Many-to-One relationship
	critique = relationship("Critique", primaryjoin="and_(Critique_Vote.artwork_id==Critique.artwork_id, "
	                                                "Critique_Vote.critic_user_id==Critique.critic_user_id)")
	buyer = relationship("Buyer")


class Follow_Artist(BaseTable):
	__tablename__ = "Follow_Artist"

	buyer_user_id = Column(BigInteger, ForeignKey('Buyer.user_id'), primary_key=True)
	artist_user_id = Column(BigInteger, ForeignKey('Artist.user_id'), primary_key=True)
	follow_artist_status = Column(String(20))
	follow_artist_creation_time = Column(DateTime)
	follow_artist_modification_time = Column(DateTime)

	# Many-to-one relationship
	buyer = relationship("Buyer")
	artist = relationship("Artist")


class Follow_Artwork(BaseTable):
	__tablename__ = "Follow_Artwork"

	buyer_user_id = Column(BigInteger, ForeignKey('Buyer.user_id'), primary_key=True)
	artwork_id = Column(BigInteger, ForeignKey('Artwork.artwork_id'), primary_key=True)
	follow_artwork_status = Column(String(20))
	is_favorite = Column(Boolean)
	follow_artwork_creation_time = Column(DateTime)
	follow_artwork_modification_time = Column(DateTime)

	# Many-to-one relationship
	buyer = relationship("Buyer")
	artwork = relationship("Artwork")


class Follow_Auction(BaseTable):
	__tablename__ = "Follow_Auction"

	buyer_user_id = Column(BigInteger, ForeignKey('Buyer.user_id'), primary_key=True)
	auction_house_user_id = Column(BigInteger, ForeignKey('Auction_House.user_id'), primary_key=True)
	follow_auction_status = Column(String(20))
	follow_auction_creation_time = Column(DateTime)
	follow_auction_modification_time = Column(DateTime)

	# Many-to-one relationship
	buyer = relationship("Buyer")
	auction_house = relationship("Auction_House")


class Follow_Critic(BaseTable):
	__tablename__ = "Follow_Critic"

	buyer_user_id = Column(BigInteger, ForeignKey('Buyer.user_id'), primary_key=True)
	critic_user_id = Column(BigInteger, ForeignKey('Critic.user_id'), primary_key=True)
	follow_critic_status = Column(String(20))
	follow_critic_creation_time = Column(DateTime)
	follow_critic_modification_time = Column(DateTime)

	# Many-to-one relationship
	buyer = relationship("Buyer")
	critic = relationship("Critic")


class Follow_Gallery(BaseTable):
	__tablename__ = "Follow_Gallery"

	buyer_user_id = Column(BigInteger, ForeignKey('Buyer.user_id'), primary_key=True)
	gallery_user_id = Column(BigInteger, ForeignKey('Gallery.user_id'), primary_key=True)
	follow_gallery_status = Column(String(20))
	follow_gallery_creation_time = Column(DateTime)
	follow_gallery_modification_time = Column(DateTime)

	# Many-to-one relationship
	buyer = relationship("Buyer")
	gallery = relationship("Gallery")


class Gallery(BaseTable):
	__tablename__ = "Gallery"

	user_id = Column(BigInteger, ForeignKey('User.user_id'), primary_key=True)
	gallery_name = Column(String(50))
	gallery_description = Column(Text)
	address_id = Column(BigInteger, ForeignKey('Address.address_id'))
	banner_image_id = Column(BigInteger, ForeignKey('Image.image_id'))
	gallery_followed_count = Column(Integer)
	gallery_comments = Column(String(50))
	gallery_modification_time = Column(DateTime)

	# One-to-many relationship
	owned_artworks = relationship("Artwork", backref="owner_gallery")
	events = relationship("Gallery_Event", backref="gallery")


class Gallery_Event(BaseTable):
	__tablename__ = "Gallery_Event"

	gallery_event_id = Column(BigInteger, primary_key=True)
	gallery_user_id = Column(BigInteger, ForeignKey('Gallery.user_id'))
	gallery_event_name = Column(String(50))
	gallery_event_description = Column(Text)
	image_id = Column(BigInteger, ForeignKey('Image.image_id'))
	gallery_event_starting_time = Column(DateTime)
	gallery_event_ending_time = Column(DateTime)
	gallery_event_creation_time = Column(DateTime)
	gallery_event_modification_time = Column(DateTime)

	# Many to one relationship
	image = relationship("Image")


class Image(BaseTable):
	__tablename__ = "Image"

	image_id = Column(BigInteger, primary_key=True)
	image_name = Column(String(50))
	image_path = Column(String(50))
	image_comments = Column(String(50))
	image_creation_time = Column(DateTime)
	image_modification_time = Column(DateTime)

	# One-to-one relationships
	artist = relationship("Artist", uselist=False, backref="image")
	auction_house = relationship("Auction_House", uselist=False, backref="banner_image")
	buyer = relationship("Buyer", uselist=False, backref="image")
	banner = relationship("Banner", uselist=False, backref="image")
	gallery = relationship("Gallery", uselist=False, backref="banner_image")


class Label(BaseTable):
	__tablename__ = "Label"

	label_id = Column(BigInteger, primary_key=True)
	label_name = Column(String(20))
	label_description = Column(Text)
	label_comments = Column(String(50))
	label_creation_time = Column(DateTime)
	label_modification_time = Column(DateTime)


class User(BaseTable):
	__tablename__ = "User"

	user_id = Column(BigInteger, primary_key=True)
	user_email = Column(String(50))
	user_hashed_email = Column(String(64))
	user_type = Column(String(20))  # ADMINISTRATOR, ARTIST, BUYER, CRITIC, GALLERY
	user_password = Column(String(64))
	user_status = Column(String(20))
	user_creation_time = Column(DateTime)
	user_modification_time = Column(DateTime)

	# One-to-one relationships
	administrator = relationship("Administrator", uselist=False, backref="user", lazy="joined")
	artist = relationship("Artist", uselist=False, backref="user", lazy="joined")
	auction_house = relationship("Auction_House", uselist=False, backref="user", lazy="joined")
	buyer = relationship("Buyer", uselist=False, backref="user", lazy="joined")
	critic = relationship("Critic", uselist=False, backref="user", lazy="joined")
	gallery = relationship("Gallery", uselist=False, backref="user", lazy="joined")

	def __repr__(self):
		return "<User(id='%s', email='%s', password='%s')>" % (self.user_id, self.user_email, self.user_password)