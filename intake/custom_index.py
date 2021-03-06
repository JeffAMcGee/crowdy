import sys
sys.path.append('.')

import os
from collections import defaultdict
from datetime import datetime, timedelta
from bisect import bisect_right
from itertools import izip_longest
from operator import itemgetter

from bson.code import Code
import maroon

from api.models import Crowd, CrowdTime, CrowdTweets, CrowdSnapshot
from etc.settings import settings


def mr_crowds(db):
    map = Code("""
        function() {
            var seconds = 1000;
            var t = 3600*Math.floor(this.start/3600/seconds)-3600;
            var end = this.end/seconds|| 1288224000;
            while(t<=end) {
                emit( new Date(t*1000), {crowds:[this._id]} );
                t+=3600;
            }
        }
    """)
    #GRR. Mongodb demands that the values be objects, not arrays.
    reduce = Code("""
        function (key, values) {
            var res = {crowds:[]};
            values.forEach(function(val) {
                res.crowds.push.apply(res.crowds, val.crowds);
            });
            return res;
        }
    """)
    db.Crowd.map_reduce(map, reduce, "CrowdTime")


def _path_time(label, time):
    return os.path.join(label, *[str(n) for n in time.timetuple()[:4]])


def crowd_snapshots(year, month, startday, days=1):
    time = start = datetime(int(year), int(month), int(startday))
    end = start+timedelta(days=int(days))
    while time <end:
        print "crowds for %r"%time
        crowd_time = CrowdTime.get_id(time)
        crowd_ids = crowd_time.value['crowds']
        crowds = [
                dict(
                    cid = crowd._id,
                    co = crowd.clust_coeff,
                    u = len(crowd_members(crowd, time)),
                    t = sum(1
                        for dt in tweet.times
                        if time<=dt<time+timedelta(hours=1))
                    )
                for crowd,tweet in _crowd_and_tweets(crowd_ids)
            ]
        total_people = sum(c['u'] for c in crowds)
        _add_centile(crowds, 'co', total_people)
        _add_centile(crowds, 'u', total_people)
        cs = CrowdSnapshot(_id=time, crowds=crowds)
        cs.save()
        time = time+timedelta(hours=1)


def _add_centile(crowds, key, total_people):
    crowds.sort(key=itemgetter(key))
    people = 0
    for c in crowds:
        c[key+"_pc"] = 100 * (people+c['u']//2) // total_people
        people += c['u']


def _crowd_and_tweets(crowd_ids):
    crowds = Crowd.find(
            Crowd._id.is_in(crowd_ids),
            fields=['users','clco'],
            sort='_id')
    tweets = CrowdTweets.find(
            CrowdTweets._id.is_in(crowd_ids),
            fields=['dts'],
            sort='_id')
    for c,t in izip_longest(crowds, tweets):
        assert c._id==t._id
        yield (c,t)


def crowd_tweets(year, month, startday, days=1):
    time = start = datetime(int(year), int(month), int(startday))
    end = start+timedelta(days=int(days))
    keys = ['dts','tids','uids','aids']
    while time <end:
        at_path = _path_time("tri_ats",time)
        tweets = [
            [int(s) for s in line.split()]
            for line in open(at_path)
        ]
        crowd_time = CrowdTime.get_id(time)
        if crowd_time:
            print "crowds for %r"%time
            crowds = Crowd.find(Crowd._id.is_in(crowd_time.value['crowds']))
        else:
            print "no crowds at %r"%time
            crowds = []
        for crowd in crowds:
            #figure out who is in the crowd this hour
            members = crowd_members(crowd, time)
            if not members:
                print "an empty crowd?"
                import pdb; pdb.set_trace()
            #find tweets between crowd members
            d = defaultdict(list)
            for tweet in tweets:
                if tweet[2] in members and tweet[3] in members:
                    for k,v in zip(keys,tweet):
                        d[k].append(v)
            #save the new crowd
            if d:
                d['dts'] = [datetime.utcfromtimestamp(t) for t in d['dts']]
                CrowdTweets.coll().find_and_modify(
                    {'_id':crowd._id},
                    {'$pushAll':d},
                    upsert=True,
                    )
        time = time+timedelta(hours=1)


def crowd_members(crowd, time):
    return set(
        user['id']
        for user in crowd.users
        if user['history'][0][0]-timedelta(hours=2) <= time and
           time <= user['history'][-1][-1]
    )


if __name__ == '__main__':
    db = maroon.Model.database = maroon.MongoDB(
        name="hou",
        host=settings.mongo_host)
    cmd = sys.argv[1]
    if cmd=='hourly':
        mr_crowds(db)
    elif cmd=='snapshots':
        crowd_snapshots(*sys.argv[2:])
    elif cmd=='index':
        crowd_tweets(*sys.argv[2:])
    else:
        print "unknown command: %s"%cmd
