# coding=utf-8
"""
Module to maintain all URL patterns used in this Tornado web server.
These URLs must be imported into the main program and used in the tornado.web.Application initializer.
"""

from tornado.web import url, StaticFileHandler
from handlers.index_handler import IndexHandler
from handlers.mobile_app_api import MobileAppAPIHandler
from settings import settings

# File export path
FILE_EXPORT_PATH = settings['FILE_EXPORT_PATH']

# Reusable regex expressions
alphanumeric_regex = "[a-zA-Z0-9._-]+"
slash_param_list = "(\/{0})*".format(alphanumeric_regex)
json_or_xml = "[jJ][sS][oO][nN]|[xX][mM][lL]"

url_patterns = [
    # **** Main index ****
    url(r"/", IndexHandler),

	# **** 1. Login and Register ****
    # 1A - Log in
    # Example: http://localhost:8888/login
    url(r"/login", MobileAppAPIHandler, dict(require_token=True)),
	# 1B - Log out
    # Example: http://localhost:8888/logout
    url(r"/logout", MobileAppAPIHandler, dict(require_token=True)),
    # 1C - Sign up
    # Example: http://localhost:8888/signup
    url(r"/signup", MobileAppAPIHandler, dict(require_token=False)),
	# 1D - Facebook signup
    # Example: http://localhost:8888/signup_facebook
    url(r"/signup_facebook", MobileAppAPIHandler, dict(require_token=False)),
    # 1E - Facebook login
    # Example: http://localhost:8888/login_facebook
   #  url(r"/login_facebook", MobileAppAPIHandler, dict(require_token=False)),

    # **** 2. Home Screen ****
	# 2A - Home Banner list
    # Example: http://localhost:8888/banner_list
    url(r"/banner_list", MobileAppAPIHandler, dict(require_token=False)),
    # 2B - Home Artwork list
    # Example: http://localhost:8888/home_artwork?sorting_rule=1&limit=10&offset=10[&location=long,lat]
    url(r"/home_artwork", MobileAppAPIHandler, dict(require_token=True)),

    # **** 3. Artwork ****
    # 3A - Artwork page and Critique list
    # Example: http://localhost:8888/artwork_page?artwork_id=1203
	url(r"/artwork_page", MobileAppAPIHandler, dict(require_token=True)),
	# 3B - Like/dislike Critique
	# Example: http://host:port/like_dislike_critique
	url(r"/like_dislike_critique", MobileAppAPIHandler, dict(require_token=True)),

	# **** 4. Purchases ****
    # 4A - Artwork Auction page
    # Example: http://host:port/artwork_auction?artwork_id=123
	url(r"/artwork_auction", MobileAppAPIHandler, dict(require_token=True)),
    # 4B - Make bid
    # Example: http://host:port/make_bid
	url(r"/make_bid", MobileAppAPIHandler, dict(require_token=True)),
	# 4C - Buy Critique
	# Example: http://host:port/buy_critique
	url(r"/buy_critique", MobileAppAPIHandler, dict(require_token=True)),
    # 4D - Buy coins
	# Example: http://host:port/buy_coins
	url(r"/buy_coins", MobileAppAPIHandler, dict(require_token=True)),

    # **** 5. Fan Pages ****
    # 5A - Artist fan page
    # Example: http://localhost:8888/artist_page?artist_id=1203&sorting_rule=1
    url(r"/artist_page", MobileAppAPIHandler, dict(require_token=True)),
    # 5B - Gallery and Auction House fan page
    # Example: http://localhost:8888/gallery_auction_page?id=1203&type=GALLERY
    url(r"/gallery_auction_page", MobileAppAPIHandler, dict(require_token=True)),

	# **** 6. Follow ****
	# 6A - Follow Artwork
    # Example: http://host:port/follow_artwork
    url(r"/follow_artwork", MobileAppAPIHandler, dict(require_token=True)),
	# 6B - Follow Artist
    # Example: http://host:port/follow_artist
    url(r"/follow_artist", MobileAppAPIHandler, dict(require_token=True)),
	# 6C - Follow Gallery
    # Example: http://host:port/follow_gallery
    url(r"/follow_gallery", MobileAppAPIHandler, dict(require_token=True)),
	# 6D - Follow Auction House
    # Example: http://host:port/follow_auction_house
    url(r"/follow_auction_house", MobileAppAPIHandler, dict(require_token=True)),
	# 6E - Follow Critic
    # Example: http://host:port/follow_critic
    url(r"/follow_critic", MobileAppAPIHandler, dict(require_token=True)),
	# 6F - Add Artwork to My Favorites
	# Example: http://host:port/add_favorite_artwork
    url(r"/add_favorite_artwork", MobileAppAPIHandler, dict(require_token=True)),

    # **** 7. Explore ****
	# 7A - Artist list
	# Example: http://host:port/artist_list?limit=0&offset=0
	url(r"/artist_list", MobileAppAPIHandler, dict(require_token=False)),
	# 7B - Gallery list
	# Example: http://host:port/gallery_list?limit=0&offset=0
	url(r"/gallery_list", MobileAppAPIHandler, dict(require_token=False)),
	# 7C - Auction House list
	# Example: http://host:port/auction_house_list?limit=0&offset=0
	url(r"/auction_house_list", MobileAppAPIHandler, dict(require_token=False)),
	# 7D - Label list
	# Example: http://host:port/kabek_list?limit=0&offset=0
	url(r"/label_list", MobileAppAPIHandler, dict(require_token=False)),

	# **** 11. Profile ****
	# 11A - About me
	# Example: http://host:port/about_me?top_n_labels=10&top_n_artists=10
	url(r"/about_me", MobileAppAPIHandler, dict(require_token=True)),
	# 11B - Following lists
	# Example: http://host:port/following_lists?limit=0&offset=0
	url(r"/following_lists", MobileAppAPIHandler, dict(require_token=True)),
	# 11C - Auction list
	# Example: http://host:port/user_auction_list?sorting_rule=1
	url(r"/user_auction_list", MobileAppAPIHandler, dict(require_token=True)),

    # *** Serve static files ***
	# Export files:
    # Example: http://localhost:8888/static/exportfiles/1260.csv
    url(r"/static/exportfiles/(.*)", StaticFileHandler, {'path': FILE_EXPORT_PATH})
]