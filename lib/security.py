# coding=utf-8
"""
This module contains class and methods for maintaining security in the API server (e.g. user authentication,
token generation, etc.)
"""

import logging
import jwt
from lib.exceptions import AuthenticationError
from settings import settings
from jwt import DecodeError
from db_tables import User
import json

logger = logging.getLogger('artmego.' + __name__)

JWT_OPTIONS = {
   'verify_signature': True,
   'verify_exp': True,
   'verify_nbf': True,
   'verify_iat': True,
   'verify_aud': True,
   'require_exp': False,
   'require_iat': False,
   'require_nbf': False
}


# TODO: Generate expiring and changeable JWT
def generate_jwt(user):
	"""
	Generate a JWT token for a user who has successfully logged in.
	:param user: The user whose authentication token will be generated
	:return: The JWT token with the necessary payload
	"""
	payload = dict(user_id=user.user_id, user_type=user.user_type)
	token = jwt.encode(payload, settings['JWT_SECRET'], algorithm=settings['JWT_ALGORITHM'])

	return token


# TODO: Generate expiring and changeable JWT
def authenticate_user_token(token):
	"""
	Check that this user has sent the correct JWT token. If it is valid, then the user_id will be returned.
	:param token: the JWT token to verify
	example - Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxOSwidXNlcl90eXBlIjoiQlVZRVIifQ.TE3S-UihiPIe5mj9RQP208aUCYiAoyVc7WWdY64aMCM
	:return: the user_id of the sender of the token
	"""
	try:

		decoded = jwt.decode(token, settings['JWT_SECRET'], algorithms=[settings['JWT_ALGORITHM']])
		user_id = decoded['user_id']
		return user_id
	except DecodeError, e:
		raise AuthenticationError


# For testing
if __name__ == "__main__":
	encoded = jwt.encode({'some': 'payload'}, 'secret', algorithm='HS256')
	print encoded
	decoded = jwt.decode(encoded, 'secret', algorithms=['HS256'])
	print decoded
