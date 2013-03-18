# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tests for L{twisted.words.protocols.jabber.sasl_mechanisms}.
"""

import binascii

from twisted.trial import unittest

from twisted.words.protocols.jabber import sasl_mechanisms
from twisted.python.hashlib import md5

class PlainTest(unittest.TestCase):
    def test_getInitialResponse(self):
        """
        Test the initial response.
        """
        m = sasl_mechanisms.Plain(None, 'test', 'secret')
        self.assertEqual(m.getInitialResponse(), '\x00test\x00secret')



class AnonymousTest(unittest.TestCase):
    """
    Tests for L{twisted.words.protocols.jabber.sasl_mechanisms.Anonymous}.
    """
    def test_getInitialResponse(self):
        """
        Test the initial response to be empty.
        """
        m = sasl_mechanisms.Anonymous()
        self.assertEqual(m.getInitialResponse(), None)



class DigestMD5Test(unittest.TestCase):
    def setUp(self):
        self.mechanism = sasl_mechanisms.DigestMD5('xmpp', 'example.org', None,
                                                   'test', 'secret')


    def test_getInitialResponse(self):
        """
        Test that no initial response is generated.
        """
        self.assertIdentical(self.mechanism.getInitialResponse(), None)

    def test_getResponse(self):
        """
        Partially test challenge response.

        Does not actually test the response-value, yet.
        """

        challenge = 'realm="localhost",nonce="1234",qop="auth",charset=utf-8,algorithm=md5-sess'
        directives = self.mechanism._parse(self.mechanism.getResponse(challenge))
        self.assertEqual(directives['username'], 'test')
        self.assertEqual(directives['nonce'], '1234')
        self.assertEqual(directives['nc'], '00000001')
        self.assertEqual(directives['qop'], ['auth'])
        self.assertEqual(directives['charset'], 'utf-8')
        self.assertEqual(directives['digest-uri'], 'xmpp/example.org')
        self.assertEqual(directives['realm'], 'localhost')

    def test_getResponseNoRealm(self):
        """
        Test that we accept challenges without realm.

        The realm should default to the host part of the JID.
        """

        challenge = 'nonce="1234",qop="auth",charset=utf-8,algorithm=md5-sess'
        directives = self.mechanism._parse(self.mechanism.getResponse(challenge))
        self.assertEqual(directives['realm'], 'example.org')

    def test__calculate_response(self):
        """
        Tests the response calculation.

        Values were taken from RFC-2831 with additional unicode characters.
        """

        charset = 'utf-8'
        nonce = 'OA6MG9tEQGm2hh'
        nc = '%08x' % 1
        cnonce = 'OA6MHXh6VqTrRk'

        username = u'\u0418chris'.encode(charset)
        password = u'\u0418secret'.encode(charset)
        realm = u'\u0418elwood.innosoft.com'.encode(charset)
        digest_uri = u'imap/\u0418elwood.innosoft.com'.encode(charset)
        
        mechanism = sasl_mechanisms.DigestMD5('imap', realm, None, 
                                            username, password) 
        response = mechanism._calculate_response(cnonce, nc, nonce,
                                                 username, password,
                                                 realm, digest_uri)
        self.assertEqual(response, '7928f233258be88392424d094453c5e3')

    def test__parse(self):
        """
        Test challenge decoding.

        Specifically, check for multiple values for the C{qop} and C{cipher}
        directives.
        """
        challenge = 'nonce="1234",qop="auth,auth-conf",charset=utf-8,' \
                    'algorithm=md5-sess,cipher="des,3des"'
        directives = self.mechanism._parse(challenge)
        self.assertEqual('1234', directives['nonce'])
        self.assertEqual('utf-8', directives['charset'])
        self.assertIn('auth', directives['qop'])
        self.assertIn('auth-conf', directives['qop'])
        self.assertIn('des', directives['cipher'])
        self.assertIn('3des', directives['cipher'])
