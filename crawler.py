#!/usr/bin/python

import threading
import BeautifulSoup
import urllib2
import urlparse
import logging
import socket
from lib.TimedQueue import TimedQueue, BotRequest, HostURLParse, SafeDict, SafeSet
from robotparser import RobotFileParser
import os

hosts = ["http://yahoo.com", "http://google.com", "http://amazon.com",
        "http://ibm.com", "http://apple.com"]



class Worker(threading.Thread):

    def __init__(self, queue, shutdown_event, hash_set, workspace, robotdict):
        threading.Thread.__init__(self)
        self.queue = queue
        self.shutdown_event = shutdown_event
        self.hash_set = hash_set
        self.workspace = workspace
        self.robotdict = robotdict

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

        #if robo_url in self.robotdict:
            #logging.info("Found in Cache: " + robo_url)
            #robo_parser = self.robotdict[robo_url]
        #else:
            #logging.info("Fetching: " + robo_url)
            #robo_parser = self.robotdict[robo_url] = RobotFileParser()
            #robo_parser.set_url(robo_url)
            #robo_parser.read()

        if cached_parser.can_fetch('*', host. get_url()):
            print 'Going to fetch:', host.get_url()
            bot_req = BotRequest(host.get_url())
            try:
                url = urllib2.urlopen(bot_req)
            except urllib2.HTTPError as e:
                logging.info("HttpError: Response:%d Host: %s" % (e. code, host))
                return None
            except urllib2.URLError as e:
                logging.info("Server Unreachable: Reason %s" % (e.reason, ))
                return None
            else:
                return url.read()  # return the HTML
        else:
            logging.info("Forbidden by Robots.txt")
            return None

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
        return str(soup)

    def save_file(self, host, html):
        filepath = os.path.join(self.workspace, host.get_diskrelpath())
        if not os.path.exists(os.path.dirname(filepath)):
            os.makedirs(os.path.dirname(filepath))
        try:
            f = open(filepath, 'w')
        except IOError:
            logging.error('Unable to create file: ' + filepath)
        f.write(html)


class Controller:

    def __init__(self, sock_timeout, req_delay, workspace, url_obj, max_conn=5):
        ## Set up all configurations
        logging.basicConfig(level=logging.DEBUG)
        socket.setdefaulttimeout(sock_timeout)
        self.queue = TimedQueue(delay=req_delay)
        self.shutdown_event = threading.Event()
        self.downloaded_hash_set = SafeSet()
        self.max_conn = max_conn
        self.project_directory = workspace  # take this argument from command line
        self.url_obj = url_obj
        self.robots_dict = SafeDict()

    def start(self):
        self.workers = []
        for i in range(self.max_conn):
            t = Worker(self.queue, self.shutdown_event, self.downloaded_hash_set, self.project_directory, self.robots_dict)
            t.setDaemon(True)
            t.start()
            self.workers.append(t)

        #for i in hosts:
            #print i
            #self.queue.put(i)
        self.queue.put(self.url_obj)

        try:
            self.queue.join(.1)
        except (KeyboardInterrupt, SystemExit):
            self.shutdown_event.set()
            #Other clean up codes

        #for w in self.workers:
            #w.join()
        #while(True):
            #br = True
            #for w in self.workers:
                #if w.is_alive():
                    #br = False
            #if br:
                #break

if __name__ == '__main__':
    #host = HostURLParse('http://python.org/', '')

    host = HostURLParse('http://127.0.0.1:8080/index.html', '')
    p = os.path.join(os.getcwd(), 'workspace/')
    ctrl = Controller(60, 2, p, host, 5)
    ctrl.start()

