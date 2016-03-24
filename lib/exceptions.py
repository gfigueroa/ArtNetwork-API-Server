# coding=utf-8
"""
This module contains user-defined Exceptions created for the ArtMeGo API Web Server.
The exceptions in this module more or less follow the errors in the base.py file:
	'0002': "inexistent resource",
	'0003': "missing arguments",
	'0004': "not implemented",
    '0005': "authentication error",
    '0006': "wrong argument value",
    '0007': "user inexistent",
    '0008': "user already exists",
    '0009': "unauthorized"
    ...
"""

import logging


logger = logging.getLogger('artmego.' + __name__)


class Error(Exception):
	def __init__(self, value, msg):
		self.value = value
		self.msg = msg

	def __str__(self):
		return repr("Error {0}: {1}".format(self.value, self.msg))


class InexistentResourceError(Error):
	def __init__(self):
		value = "0002"
		msg = "inexistent resource"
		super(InexistentResourceError, self).__init__(value, msg)


class MissingArgumentsError(Error):
	def __init__(self):
		value = "0003"
		msg = "missing arguments"
		super(MissingArgumentsError, self).__init__(value, msg)


class NotImplementedError(Error):
	def __init__(self):
		value = "0004"
		msg = "not implemented"
		super(NotImplementedError, self).__init__(value, msg)


class AuthenticationError(Error):
	def __init__(self):
		value = "0005"
		msg = "authentication error"
		super(AuthenticationError, self).__init__(value, msg)


class WrongArgumentValueError(Error):
	def __init__(self, argument):
		value = "0006"
		msg = "wrong argument value"
		self.argument = argument
		super(WrongArgumentValueError, self).__init__(value, msg)

	def __str__(self):
		return repr("Error {0}: {1} on argument '{2}'".format(self.value, self.msg, self.argument))


class UserInexistentError(Error):
	def __init__(self):
		value = "0007"
		msg = "user inexistent"
		super(UserInexistentError, self).__init__(value, msg)


class UserExistsError(Error):
	def __init__(self):
		value = "0008"
		msg = "user already exists"
		super(UserExistsError, self).__init__(value, msg)


class UnauthorizedError(Error):
	def __init__(self):
		value = "0009"
		msg = "unauthorized"
		super(UnauthorizedError, self).__init__(value, msg)


class InsufficientFundsError(Error):
	def __init__(self):
		value = "0010"
		msg = "insufficient funds"
		super(InsufficientFundsError, self).__init__(value, msg)