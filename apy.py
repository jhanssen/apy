#!/usr/local/bin/python

import urllib2, json, getopt, sys, os, re
from pprint import pprint

def createRequest(method, args = None):
    obj = {'jsonrpc': '2.0', 'id': 'qwer', 'method': method}
    if not args is None:
        obj['params'] = args
    return json.dumps(obj)

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
    args = [[uri]]
    for c in cfg:
        if not type(c) is dict:
            print 'type is not dict in applyConfig!'
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
    resp1 = sendRequest(req)
    req = createRequest('aria2.removeDownloadResult', [gid])
    resp2 = sendRequest(req)
    if resp1 == gid or (isinstance(resp2, basestring) and resp2 == "OK"):
        print 'Ok.'
    else:
        print 'Failure.'

def formatTime(days, hrs, mins, secs):
    fmt = ''
    if days > 0:
        fmt = str(days) + 'd '
    if hrs > 0:
        fmt = fmt + str(hrs) + 'h '
    fmt = fmt + str(mins) + 'm ' + str(secs) + 's'
    return fmt

def printTell(header, resp):
    if len(resp) > 0:
        print header
        for entry in resp:
            if not type(entry) is dict:
                print 'entry is not dict in printTell!'
                return
            print '  GID', entry['gid']
            files = entry['files']
            running = 'completedLength' in entry
            for f in files:
                uris = f['uris']
                if running:
                    print '    PATH', f['path']
                if len(uris) > 0:
                    print '    URI', uris[0]['uri']
            if running:
                tot = float(entry['totalLength'])
                cur = float(entry['completedLength'])
                perc = int(cur / tot * 100)
                speed = float(entry['downloadSpeed']) / 1024
                time = int(((tot - cur) / 1024) / speed)
                tmin = time / 60
                tsec = time % 60
                thr = tmin / 60
                tmin = tmin % 60
                tdy = thr / 24
                thr = thr % 24
                print '    CONNECTIONS', entry['connections']
                print '    SPEED', round(speed, 1), 'KiB/s'
                print '    TIME', formatTime(tdy, thr, tmin, tsec)
                print '    COMPLETED', str(perc) + '%'
                print '      DOWNLOADED', round(cur / 1048576, 1), 'MiB'
                print '      TOTAL', round(tot / 1048576, 1), 'MiB'
            if 'errorCode' in entry:
                error = entry['errorCode']
                if len(error) > 0:
                    print '    ERROR', entry['errorCode']

def filterStatus(resp, status):
    if not type(resp) is list:
        return []
    return filter(lambda entry: 'status' in entry and status == entry['status'], resp)

def removeStopped():
    req = createRequest('aria2.getGlobalStat')
    resp = sendRequest(req)
    if not type(resp) is dict:
        print 'type is not dict in removeStopped'
        return

    numStopped = int(resp['numStopped'])
    req = createRequest('aria2.tellStopped', [0, numStopped, ['gid', 'files']])
    resp = sendRequest(req)
    if not type(resp) is list:
        print 'type is not list in removeStopped'
        return

    for entry in resp:
        if not type(entry) is dict:
            print 'type is not dict (2) in removeStopped'
            return
        files = entry['files']
        gid = entry['gid']
        for f in files:
            if 'path' in f:
                print 'Clearing', f['path'], 'with GID', gid
        req = createRequest('aria2.removeDownloadResult', [gid])
        resp = sendRequest(req)
        if not isinstance(resp, basestring) or not resp == 'OK':
            print 'Failed to remove GID', gid

def status():
    req = createRequest('aria2.getGlobalStat')
    resp = sendRequest(req)
    if not type(resp) is dict:
        return

    numWaiting = int(resp['numWaiting'])
    numStopped = int(resp['numStopped'])

    req = createRequest('aria2.tellActive', ['gid', 'status', 'totalLength', 'completedLength', 'downloadSpeed', 'files', 'connections'])
    resp = sendRequest(req)
    if not type(resp) is list:
        return
    printTell('ACTIVE', resp)

    req = createRequest('aria2.tellWaiting', [0, numWaiting, ['gid', 'status', 'files']])
    resp = sendRequest(req)
    if not type(resp) is list:
        return
    printTell('WAITING', resp)

    req = createRequest('aria2.tellStopped', [0, numStopped, ['gid', 'status', 'files', 'errorCode']])
    resp = sendRequest(req)
    if not type(resp) is list:
        return
    complete = filterStatus(resp, 'complete')
    printTell('COMPLETE', complete)
    error = filterStatus(resp, 'error')
    printTell('ERROR', error)

def runCommand(cmd):
    req = createRequest(cmd)
    resp = sendRequest(req)
    if isinstance(resp, basestring):
        if resp == 'OK':
            print 'Ok.'
        else:
            print 'Failure.'
    else:
        print 'Failure.'

def syntax():
    print 'Syntax: apy.py [-a uri] [-r gid] [-s] [-p] [-u] [-c]'

def parseConfig():
    try:
        f = open(os.path.expanduser('~/.apy.cfg'), 'r')
    except IOError:
        return []
    j = json.load(f)
    return j

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'a:r:spuc')
    except getopt.GetoptError, err:
        print str(err)
        syntax()
        sys.exit(1)
    if len(opts) == 0 or len(args) != 0:
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
        elif k == '-p':
            runCommand('aria2.pauseAll')
        elif k == '-u':
            runCommand('aria2.unpauseAll')
        elif k == '-c':
            removeStopped()
        else:
            syntax()
            sys.exit(1)

if __name__ == '__main__':
    main()
