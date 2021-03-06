#!/usr/bin/env python

import sys
sys.path.append("..")
import unittest

import cherrypy
import maroon
from maroon import MockDB

import api
from etc.settings import settings


class TestAPI(unittest.TestCase):
    def setUp(self):
        maroon.Model.database = MockDB("infolabbers",api.models)

    def test_user_id(self):
        jeff = api.user.id('106582358')
        self.failUnlessEqual(jeff['sn'],'JeffAMcGee')
        self.failUnlessRaises(cherrypy.HTTPError, api.user.id, '12')
        #FIXME: check date format
    
    def test_user_tweets(self):
        #tweets(uid,start_date=None,end_date=None,limit=100):
        jan5 = '1294185600'
        jan16 = '1295136000'
        before = api.user.tweets('106582358',max_date=jan5)
        self.failUnlessEqual(len(before),3)
        after = api.user.tweets('106582358',min_date=jan16)
        self.failUnlessEqual(len(after),4)
        mid = api.user.tweets('106582358',min_date=jan5,max_date=jan16)
        self.failUnlessEqual(len(mid),12)
        lim = api.user.tweets('106582358',limit=5)
        self.failUnlessEqual(len(lim),5)

    def test_crowd_simple(self):
        crowd = api.crowd.simple('test1')
        self.failUnlessEqual(crowd['size'],2)
        self.failUnlessEqual(crowd['users'][0],106582358)

    def test_crowd_users(self):
        users = api.crowd.users('test1')
        names = sorted(u['sn'].lower() for u in users)
        self.failUnlessEqual(['jeffamcgee','nod'],names)

    def test_crowd_tweets(self):
        tweets = api.crowd.tweets('test1')
        self.failUnlessEqual(len(tweets),6)

    def _assert_search_res(self, expected,**kwargs):
        res = api.search.crowd(**kwargs)
        res = ''.join(sorted(d['_id'].strip('test') for d in res))
        self.failUnlessEqual(res,expected)
        
    def test_search_crowd(self):
        self._assert_search_res("123")
        self._assert_search_res("12",min_start='1294185600')
        self._assert_search_res("13",max_size='3')
    
    def test_crowd_star(self):
        api.crowd.star('test1','f')
        crowd = api.crowd.id('test1')
        self.failUnlessEqual(crowd['star'],False)
        api.crowd.star('test1')
        crowd = api.crowd.id('test1')
        self.failUnlessEqual(crowd['star'],True)


if __name__ == '__main__':
    unittest.main()
