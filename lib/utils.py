import Queue
import time
import urlparse
import os
import hashlib
from threading import Lock
from urllib2 import Request
import re


class TimedQueue(Queue.Queue):
    '''This queue enforces that subsequent get operations are at least DELAY
       seconds apart
    '''

    def __init__(self, delay=0, maxsize=0):
        #print "initializing timedqueue"
        Queue.Queue.__init__(self, maxsize=maxsize)
        self.delay = delay
        self.lock = Lock()

    def get(self, block=True, timeout=None):
        item = Queue.Queue.get(self, block, timeout)
        self.lock.acquire()
        now = time.time()
        try:
            diff = now - self.last
            if diff < self.delay:
                time.sleep(self.delay - diff)
        except AttributeError:
            pass
        finally:
            self.last = time.time()
        self.lock.release()
        return item

    def get_nowait(self):
        return self.get(block=False)

    def join(self, timeout=None):
        """Override of the original Queue.join() method.
           https://bitbucket.org/mirror/python-trunk/src/f2b7abc5e425/Lib/Queue.py#cl-70
        """
        self.all_tasks_done.acquire()
        try:
            while self.unfinished_tasks:
                self.all_tasks_done.wait(timeout)  # changed here
        finally:
            self.all_tasks_done.release()


class BotRequest(Request):
    '''Convenience class to specify number of extra headers to send'''

    def __init__(self, url, data='', headers={}):
        Request.__init__(self, url, data, headers)
        Request.add_header(self, 'User-Agent',
                     'NilanjanBot(nilanjan-basu.appspot.com/bot/testbot.html)')


class HostURLParse:
    '''Representative of URLs with convenience functions'''

    def __init__(self, url, baseurl):
    #Compulsory to include baseurl, make user acknowledge each time

        self.HTTP = 1
        self.RELATIVE = 2
        self.OTHER = 3

        u = urlparse.urlparse(urlparse.urljoin(baseurl.strip(), url.strip()))
        #print u
        self.scheme = u.scheme
        self.scheme_num = self._get_scheme_num(self.scheme)

        res = self.is_ip_or_localhost(u.netloc)
        if not res and u.netloc and not u.netloc[:4] == 'www.':
            self.netloc = 'www.' + u.netloc
        else:
            self.netloc = u.netloc
        self.path = u.path if u.path else '/'

        self.dirname, f = os.path.split(u.path)

        if not f:
            self.filename = 'index.html'
        else:
            self.filename = f

        # throw away param and query for now

    def is_ip_or_localhost(self,netloc):
        st = re.match("^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])",netloc)
        lc = re.match("^localhost", netloc)
        if st or lc:
            return True
        else:
            return False

    def get_url(self):
        return urlparse.urlunparse((self.scheme, self.netloc, self.path, '', '',''))

    def get_filename(self):
        return self.filename

    def get_robots_url(self):
        return urlparse.urlunparse((self.scheme, self.netloc, 'robots.txt', '', '', ''))

    def get_diskrelpath(self):
        '''returns a relative path for this url
           do a os.path.join() with the project workspace
        '''
        return os.path.join(self.netloc, self.dirname[1:], self.filename)

    def is_scheme_http(self):
        return self.scheme_num == self.HTTP

    def is_scheme(self, val):
        if val == self.scheme_num:
            return True

    def get_url_hash(self):
        c = hashlib.md5()
        c.update(self.get_url())
        return c.hexdigest()

    def __str__(self):
        return '( "' + self.scheme + '" , "' + self.netloc +'" , "' + self.dirname + '" ), ' + str(self.filename)  #tuple objects

    def _get_scheme_num(self, name):
        if name == 'http':
            return self.HTTP
        elif name == '':
            return self.RELATIVE
        else:
            return self.OTHER


class SafeDict:
    '''
    Thread safe dictionary
    '''
    def __init__(self):
        self._dict = {}
        self.lock = Lock()

    def get(self, key):
        self.lock.acquire()
        val = None
        if key in self._dict:
            val = self._dict[key]
        self.lock.release()
        return val

    def put(self, key, value):
        self.lock.acquire()
        self._dict[key] = value
        self.lock.release()

    def __str__(self):
        return str(self._dict)


class SafeSet:
    '''
    Thread safe set
    '''
    def __init__(self):
        self._set = set()
        self.lock = Lock()

    def in_set(self, key):
        self.lock.acquire()
        val = key in self._set
        self.lock.release()
        return val

    def add(self, item):
        self.lock.acquire()
        self._set.add(item)
        self.lock.release()

    def __str__(self):
        return str(self._set)







