from TimedQueue import HostURLParse, BotRequest
from urllib2 import Request


def run_test_on_HostURLParse(u, base=''):
    m = HostURLParse(u, base)
    print u , base + '--->' + str(m) + ' full path--> ' + m.get_diskrelpath() +' ;URL:"'+m.get_url()+ '" '+ str(m.scheme_num)


def test_HostURLParse():

    run_test_on_HostURLParse('http://facebook.com ')
    run_test_on_HostURLParse('http://facebook.com/')
    run_test_on_HostURLParse('http://fb.com/abc/index.html')
    run_test_on_HostURLParse('http://fb.com/abc/other.html?answer=1')
    run_test_on_HostURLParse('http://fb.com/abc/other.html?answer=1%20hello=3')
    run_test_on_HostURLParse('http://www.fb.com/abc/other.html?answer=1')
    run_test_on_HostURLParse('mailto:neelpulse@gmail.com')
    run_test_on_HostURLParse('http://buildbot.net/trac')
    run_test_on_HostURLParse('/about/website')
    run_test_on_HostURLParse('../about/', 'http://fb.com/abc/')


def test_BotRequest():
    from BeautifulSoup import BeautifulSoup
    import urllib2

    req = BotRequest('http://python.org')
    response = urllib2.urlopen(req)
    soup = BeautifulSoup(response.read())
    links = [x.get('href') for x in soup.findAll('a')]
    for link in links:
        print link





if __name__=='__main__':
    test_HostURLParse()
    #test_BotRequest()
