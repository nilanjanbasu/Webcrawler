#!/usr/bin/python

import Queue
import threading
import BeautifulSoup
import urllib2
import urlparse
import logging
import socket
from lib.utils import TimedQueue, BotRequest, HostURLParse, SafeDict, SafeSet
from robotparser import RobotFileParser
import sys
import re
import os


class Worker(threading.Thread):

    def __init__(self, queue, shutdown_event, hash_set, static_set, workspace, robotdict):
        '''
        queue : Shared Queue.Queue object containing the URLs (HostURLParse)
        shutdown_event: theading.Event to signal termination of the program
        hash_set: The threadsafe SafeSet to represent the visited links
        statis_set : The threadsafe SafeSet to represent the fetched static files
        workspace: The workspace to save files to
        robotdict : dictionary to contain RobotFileParser for a site
        '''

        threading.Thread.__init__(self)
        self.queue = queue
        self.shutdown_event = shutdown_event
        self.hash_set = hash_set
        self.workspace = workspace
        self.robotdict = robotdict
        self.static_set = static_set

    def run(self):
        while not self.shutdown_event.is_set():
        #while True:
            host = self.queue.get()
            html = self.urlopen(host)
            if html:
                self.hash_set.add(host.get_url_hash())
                html = self.parse_and_enque(host, html)
                self.save_file(host, html)
            else:
                if not html:
                    logging.info("No HTML found")

            self.queue.task_done()

    def urlopen(self, host):
        robo_url = host.get_robots_url()

        print self.robotdict

        cached_parser = self.robotdict.get(robo_url)
        if cached_parser:
            logging.info("Found in Cache: " + robo_url)
        else:
            logging.info("Fetching: " + robo_url)
            cached_parser = RobotFileParser()
            self.robotdict.put(robo_url, cached_parser)
            cached_parser.set_url(robo_url)
            cached_parser.read()

        if cached_parser.can_fetch('*', host. get_url()):
            print 'Going to fetch:', host.get_url()
            return self.fetch_file(host.get_url())
        else:
            logging.info("Forbidden by Robots.txt")
            return None

    def fetch_file(self, url):

        request = BotRequest(url)
        try:
            response = urllib2.urlopen(request)
        except urllib2.HTTPError as e:
            logging.info("HttpError: Response:%d Host: %s" % (e. code, url))
            return None
        except urllib2.URLError as e:
            logging.info("Server Unreachable: URL: %s  Reason %s" % (url, e.reason))
            return None
        else:
            return response.read()  # return the HTML


    def parse_and_enque(self, host, html):
        soup = BeautifulSoup.BeautifulSoup(html)
        links = [x for x in soup.findAll('a', href=True)]

        for a in links:
            #print a, host.get_url()
            urlhostp = HostURLParse(a['href'], host.get_url())
            h = urlhostp.get_url_hash()
            if not self.hash_set.in_set(h):
                print "Enquing", a['href'], host.get_url()
                self.queue.put(urlhostp)
                self.hash_set.add(h)
            a['href'] = os.path.join(self. workspace, urlhostp. get_diskrelpath())
        self.save_static_files(host,soup)
        return str(soup)

    def save_static_files(self,host,soup):
        css_files = soup.findAll('link', {'rel' : re.compile(r'stylesheet')}, href=True)
        img_files = soup.findAll('img', src=True)
        js_files = soup.findAll('script', src=True)

        self.save_static_by_type(host, soup, css_files, 'href')
        self.save_static_by_type(host, soup, img_files, 'src')
        self.save_static_by_type(host, soup, js_files, 'src')

    def save_static_by_type(self, host, soup, link_items, attr):
        q = Queue.Queue()
        for link in link_items:
            print host.get_url()
            static_url_obj = HostURLParse(link[attr], host.get_url())
            if not self.static_set.in_set(static_url_obj.get_url_hash()):
                #self.static_set.add(static_url_obj.get_url_hash())
                q.put(static_url_obj)
                link[attr] = os.path.join(self. workspace, static_url_obj. get_diskrelpath())
            else:
                logging.info('Found Static file in cache: ' + static_url_obj.get_url())

        stop_event = threading.Event()
        if not q.empty():
            for i in range(5):
                t = threading.Thread(target=self.static_worker, args=(q,stop_event))
                t.setDaemon(True)
                t.start()

            q.join()
            stop_event.set()

    def static_worker(self, static_queue, stop_event):

        while not stop_event.is_set():
            url_obj = static_queue.get()
            content = self.fetch_file(url_obj.get_url())
            if content:
                self.static_set.add(url_obj.get_url_hash())
                logging.info("Saved static file: " + url_obj.get_url())
                self.save_file(url_obj, content)
            static_queue.task_done()

    def save_file(self, host, content):
        filepath = os.path.join(self.workspace, host.get_diskrelpath())
        print filepath
        if not os.path.exists(os.path.dirname(filepath)):
            os.makedirs(os.path.dirname(filepath))
        try:
            f = open(filepath, 'w')
        except IOError:
            logging.error('Unable to create file: ' + filepath)
        f.write(content)


class Controller:

    def __init__(self, sock_timeout, req_delay, workspace, url_obj, max_conn=5):
        '''sock_timeout: time-out for terminating a socket connection without any reply
           req_delay   : Delay between successive requests to a website
           workspace   : Folder to which the mirror should be saved
           url_obj     : An HostURLParse object representing the base URL
           max_conn    : Maximum number of parallel threads to use'''


        ## Set up all configurations
        logging.basicConfig(level=logging.DEBUG)
        socket.setdefaulttimeout(sock_timeout)
        self.queue = TimedQueue(delay=req_delay)
        self.shutdown_event = threading.Event()
        self.downloaded_hash_set = SafeSet()
        self.static_set = SafeSet()
        self.max_conn = max_conn
        self.project_directory = workspace  # take this argument from command line
        self.url_obj = url_obj
        self.robots_dict = SafeDict()

    def start(self):
        self.workers = []
        for i in range(self.max_conn):
            t = Worker(self.queue, self.shutdown_event, self.downloaded_hash_set, self.static_set, self.project_directory, self.robots_dict)
            t.setDaemon(True)
            t.start()
            self.workers.append(t)

        self.queue.put(self.url_obj)

        try:
            self.queue.join(.1)
        except (KeyboardInterrupt, SystemExit):
            self.shutdown_event.set()
            #Other clean up codes

if __name__ == '__main__':
    #host = HostURLParse('http://python.org/', '')

    if len(sys.argv) < 2:
        print "Usage: ./crawler.py <Website URL>"
        sys.exit(0)

    host = HostURLParse(sys.argv[1], '')
    p = os.path.join(os.getcwd(), 'workspace/')
    ctrl = Controller(60, 25, p, host, 5)
    ctrl.start()

