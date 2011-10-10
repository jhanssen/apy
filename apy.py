#!/usr/local/bin/python

import urllib2, json, getopt, sys, os, re
from pprint import pprint

def createRequest(method, args = None):
    if not args is None:
        req = json.dumps({'jsonrpc': '2.0', 'id': 'qwer', 'method': method, 'params': args})
        return req
    req = json.dumps({'jsonrpc': '2.0', 'id': 'qwer', 'method': method})
    return req

def sendRequest(req):
    try:
        c = urllib2.urlopen('http://localhost:6800/jsonrpc', req)
    except urllib2.HTTPError, err:
        if err.code != 500:
            print str(err)
        return None
    data = json.loads(c.read())
    if not type(data) is dict:
        return None
    return data['result']

def applyConfig(uri, cfg):
    args = []
    args.append([uri])
    for c in cfg:
        if not type(c) is dict:
            print "Type is not dict in applyConfig!"
            return [[uri]]
        if c['type'] == 'match':
            p = re.compile(c['match'])
            r = p.search(uri)
            if not r is None:
                args.append(c['options'])
    return args

def addUri(uri, cfg):
    args = applyConfig(uri, cfg)
    req = createRequest('aria2.addUri', args)
    resp = sendRequest(req)
    if resp is None:
        print 'Failure.'
    else:
        print 'Added as gid', resp

def removeUri(gid):
    req = createRequest('aria2.remove', [gid])
    sendRequest(req)
    req = createRequest('aria2.removeDownloadResult', [gid])
    resp = sendRequest(req)
    if isinstance(resp, basestring):
        if resp == 'OK':
            print 'Ok.'
        else:
            print 'Failure.'
    else:
        print 'Failure.'

def printTell(resp):
    if len(resp) > 0:
        for entry in resp:
            if not type(entry) is dict:
                print 'entry is not dict!'
                return
            print '  GID', entry['gid']
            files = entry['files']
            running = 'completedLength' in entry
            for f in files:
                uris = f['uris']
                if running:
                    print '    PATH', f['path']
                for u in uris:
                    print '    URI', u['uri'], 'STATUS', u['status']
            if running:
                tot = float(entry['totalLength'])
                cur = float(entry['completedLength'])
                perc = int(cur / tot * 100)
                speed = float(entry['downloadSpeed']) / 1024
                print '    SPEED', round(speed, 1), 'KiB/s'
                print '    COMPLETED', str(perc) + '%'
                print '      DOWNLOADED', round(cur / 1048576, 1), 'MiB'
                print '      TOTAL', round(tot / 1048576, 1), 'MiB'


def status():
    req = createRequest('aria2.getGlobalStat')
    resp = sendRequest(req)
    if not type(resp) is dict:
        return
    numActive = int(resp['numActive'])
    numStopped = int(resp['numStopped'])
    numWaiting = int(resp['numWaiting'])
    req = createRequest('aria2.tellActive', ['gid', 'status', 'totalLength', 'uploadLength', 'downloadSpeed', 'files'])
    resp = sendRequest(req)
    if not type(resp) is list:
        return
    print 'ACTIVE'
    printTell(resp)
    req = createRequest('aria2.tellWaiting', [0, numWaiting, ['gid', 'status', 'totalLength', 'uploadLength', 'downloadSpeed', 'files']])
    resp = sendRequest(req)
    if not type(resp) is list:
        return
    print 'WAITING'
    printTell(resp)
    req = createRequest('aria2.tellStopped', [0, numStopped, ['gid', 'status', 'totalLength', 'uploadLength', 'downloadSpeed', 'files']])
    resp = sendRequest(req)
    if not type(resp) is list:
        return
    print 'STOPPED'
    printTell(resp)

def syntax():
    print 'Syntax: apy.py [-a uri] [-r gid] [-s]'

def parseConfig():
    try:
        f = open(os.path.expanduser('~/.apy.cfg'), 'r')
    except IOError:
        return []
    j = json.load(f)
    return j

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'a:r:s')
    except getopt.GetoptError, err:
        print str(err)
        syntax()
        sys.exit(1)
    if len(opts) == 0:
        syntax()
        sys.exit(0)
    cfg = parseConfig()
    for k, v in opts:
        if k == '-a':
            addUri(v, cfg)
        elif k == '-r':
            removeUri(v)
        elif k == '-s':
            status()
        else:
            syntax()
            sys.exit(1)

if __name__ == '__main__':
    main()
