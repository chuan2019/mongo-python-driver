# Copyright 2009-2011 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test the pymongo uri_parser module."""

import copy
import unittest

from pymongo.uri_parser import (_partition,
                                        _rpartition,
                                        parse_userinfo,
                                        split_hosts,
                                        split_options,
                                        parse_uri)
from pymongo.errors import (ConfigurationError,
                            InvalidURI,
                            UnsupportedOption)


class TestURI(unittest.TestCase):

    def test_partition(self):
        self.assertEqual(('foo', ':', 'bar'), _partition('foo:bar', ':'))
        self.assertEqual(('foobar', '', ''), _partition('foobar', ':'))

    def test_rpartition(self):
        self.assertEqual(('fo:o:', ':', 'bar'), _rpartition('fo:o::bar', ':'))
        self.assertEqual(('', '', 'foobar'), _rpartition('foobar', ':'))

    def test_validate_userinfo(self):
        self.assertRaises(InvalidURI, parse_userinfo,
                          'foo@')
        self.assertRaises(InvalidURI, parse_userinfo,
                          ':password')
        self.assertRaises(InvalidURI, parse_userinfo,
                          'user:')
        self.assertRaises(InvalidURI, parse_userinfo,
                          'fo::o:p@ssword')
        self.assertRaises(InvalidURI, parse_userinfo, ':')
        self.assert_(parse_userinfo('user:password'))
        self.assertEqual(('us:r', 'p@ssword'),
                         parse_userinfo('us%3Ar:p%40ssword'))

    def test_split_hosts(self):
        self.assertRaises(ConfigurationError, split_hosts,
                          'localhost:27017,')
        self.assertRaises(ConfigurationError, split_hosts,
                          ',localhost:27017')
        self.assertRaises(ConfigurationError, split_hosts,
                          'localhost:27017,,localhost:27018')
        self.assertEqual([('localhost', 27017), ('example.com', 27017)],
                         split_hosts('localhost,example.com'))
        self.assertEqual([('localhost', 27018), ('example.com', 27019)],
                         split_hosts('localhost:27018,example.com:27019'))
        self.assertRaises(ConfigurationError, split_hosts, '::1', 27017)
        self.assertRaises(ConfigurationError, split_hosts, '[::1:27017')
        self.assertRaises(ConfigurationError, split_hosts, '::1')
        self.assertRaises(ConfigurationError, split_hosts, '::1]:27017')
        self.assertEqual([('::1', 27017)], split_hosts('[::1]:27017'))
        self.assertEqual([('::1', 27017)], split_hosts('[::1]'))

    def test_split_options(self):
        # This should remind us to write tests for these if
        # they are ever supported.
        self.assertRaises(UnsupportedOption, split_options,
                          'minPoolSize=5')
        self.assertRaises(UnsupportedOption, split_options,
                          'waitQueueTimeoutMS=500')
        self.assertRaises(UnsupportedOption, split_options,
                          'waitQueueMultiple=5')
        self.assertRaises(UnsupportedOption, split_options,
                          'connectTimeoutMS=500')
        self.assertRaises(UnsupportedOption, split_options,
                          'socketTimeoutMS=500')

        self.assertRaises(InvalidURI, split_options, 'foo')
        self.assertRaises(InvalidURI, split_options, 'foo=bar')
        self.assertRaises(InvalidURI, split_options, 'foo=bar;foo')
        self.assertRaises(InvalidURI, split_options, 'connect=foo')
        self.assert_(split_options('connect=direct'))
        self.assert_(split_options('connect=replicaSet'))
        self.assert_(split_options('connect=Replicaset'))
        self.assertRaises(InvalidURI, split_options, 'w=foo')
        self.assertRaises(InvalidURI, split_options, 'w=5.5')
        self.assert_(split_options, 'w=5')
        self.assertRaises(InvalidURI, split_options, 'wtimeoutms=foo')
        self.assertRaises(InvalidURI, split_options, 'wtimeoutms=5.5')
        self.assert_(split_options, 'wtimeoutms=500')
        self.assertRaises(InvalidURI, split_options, 'fsync=foo')
        self.assertRaises(InvalidURI, split_options, 'fsync=5.5')
        self.assertEqual({'fsync': True}, split_options('fsync=true'))
        self.assertEqual({'fsync': False}, split_options('fsync=false'))
        self.assertRaises(InvalidURI, split_options, 'maxpoolsize=foo')
        self.assertRaises(InvalidURI, split_options, 'maxpoolsize=5.5')
        self.assert_(split_options, 'maxpoolsize=50')

    def test_parse_uri(self):
        self.assertRaises(InvalidURI, parse_uri, "http://foobar.com")
        self.assertRaises(InvalidURI, parse_uri, "http://foo@foobar.com")
        self.assertRaises(InvalidURI, parse_uri, "mongodb://::1", 27017)

        orig = {
            'nodelist': [("localhost", 27017)],
            'username': None,
            'password': None,
            'database': None,
            'collection': None,
            'options': {}
        }

        res = copy.deepcopy(orig)
        self.assertEqual(res, parse_uri("mongodb://localhost"))

        res.update({'username': 'fred', 'password': 'foobar'})
        self.assertEqual(res, parse_uri("mongodb://fred:foobar@localhost"))

        res.update({'database': 'baz'})
        self.assertEqual(res, parse_uri("mongodb://fred:foobar@localhost/baz"))

        res = copy.deepcopy(orig)
        res['nodelist'] = [("example1.com", 27017), ("example2.com", 27017)]
        self.assertEqual(res,
                         parse_uri("mongodb://example1.com:27017,"
                                   "example2.com:27017"))

        res = copy.deepcopy(orig)
        res['nodelist'] = [("localhost", 27017),
                           ("localhost", 27018),
                           ("localhost", 27019)]
        self.assertEqual(res,
                         parse_uri("mongodb://localhost,"
                                   "localhost:27018,localhost:27019"))

        res = copy.deepcopy(orig)
        res['database'] = 'foo'
        self.assertEqual(res, parse_uri("mongodb://localhost/foo"))

        res = copy.deepcopy(orig)
        self.assertEqual(res, parse_uri("mongodb://localhost/"))

        res.update({'database': 'test', 'collection': 'yield_historical.in'})
        self.assertEqual(res, parse_uri("mongodb://"
                                        "localhost/test.yield_historical.in"))

        res.update({'username': 'fred', 'password': 'foobar'})
        self.assertEqual(res,
                         parse_uri("mongodb://fred:foobar@localhost/"
                                   "test.yield_historical.in"))

        res = copy.deepcopy(orig)
        res['nodelist'] = [("example1.com", 27017), ("example2.com", 27017)]
        res.update({'database': 'test', 'collection': 'yield_historical.in'})
        self.assertEqual(res,
                         parse_uri("mongodb://example1.com:27017,example2.com"
                                   ":27017/test.yield_historical.in"))

        res = copy.deepcopy(orig)
        res['nodelist'] = [("::1", 27017)]
        res['options'] = {'slaveok': True}
        self.assertEqual(res, parse_uri("mongodb://[::1]:27017/?slaveOk=true"))

        res = copy.deepcopy(orig)
        res['nodelist'] = [("2001:0db8:85a3:0000:0000:8a2e:0370:7334", 27017)]
        res['options'] = {'slaveok': True}
        self.assertEqual(res, parse_uri(
                              "mongodb://[2001:0db8:85a3:0000:0000"
                              ":8a2e:0370:7334]:27017/?slaveOk=true"))

        res = copy.deepcopy(orig)
        res['nodelist'] = [("::1", 27017),
                           ("2001:0db8:85a3:0000:0000:8a2e:0370:7334", 27018),
                           ("192.168.0.212", 27019),
                           ("localhost", 27018)]
        self.assertEqual(res, parse_uri("mongodb://[::1]:27017,[2001:0db8:"
                                        "85a3:0000:0000:8a2e:0370:7334],"
                                        "192.168.0.212:27019,localhost",
                                        27018))

        res = copy.deepcopy(orig)
        res.update({'username': 'fred', 'password': 'foobar'})
        res.update({'database': 'test', 'collection': 'yield_historical.in'})
        res['options'] = {'slaveok': True}
        self.assertEqual(res,
                         parse_uri("mongodb://fred:foobar@localhost/"
                                   "test.yield_historical.in?slaveok=true"))

if __name__ == "__main__":
    unittest.main()
