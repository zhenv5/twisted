# -*- test-case-name: twisted.test.test_paths -*-
# Copyright (c) 2001-2004 Twisted Matrix Laboratories.
# See LICENSE for details.

#

import urlparse
import urllib

class URLPath:
    def __init__(self, scheme='', netloc='localhost', path='',
                 query='', fragment=''):
        self.scheme = scheme or 'http'
        self.netloc = netloc
        self.path = path or '/'
        self.query = query
        self.fragment = fragment

    _qpathlist = None
    _uqpathlist = None
    
    def pathList(self, unquote=0, copy=1):
        if self._qpathlist is None:
            self._qpathlist = self.path.split('/')
            self._uqpathlist = map(urllib.unquote, self._qpathlist)
        if unquote:
            result = self._uqpathlist
        else:
            result = self._qpathlist
        if copy:
            return result[:]
        else:
            return result

    def fromString(klass, st):
        t = urlparse.urlsplit(st)
        u = klass(*t)
        return u

    fromString = classmethod(fromString)

    def fromRequest(klass, request):
        return klass.fromString(request.prePathURL())

    fromRequest = classmethod(fromRequest)

    def _pathMod(self, newpathsegs, keepQuery):
        if keepQuery:
            query = self.query
        else:
            query = ''
        return URLPath(self.scheme,
                        self.netloc,
                        '/'.join(newpathsegs),
                        query)

    def sibling(self, path, keepQuery=False):
        l = self.pathList()
        l[-1] = path
        return self._pathMod(l, keepQuery)

    def child(self, path, keepQuery=False):
        """
        Add a child segment to URL path part. 
        
        @param path: path segment to add. The path argument should not be quoted.
        @type path: C{str}
        @param keepQuery: if set to True, will keep the query part of URL, 
                          else (and by default) will strip query part.
        @type keepQuery: C{bool}
        @return: A new L{URLPath} object with path appended to current object
        @rtype: L{URLPath}
        """
        #Clean up path with urlescaped version
        fixedPath = urllib.quote(path,'')
        l = self.pathList()
        if l[-1] == '':
            l[-1] = fixedPath
        else:
            l.append(fixedPath)
        return self._pathMod(l, keepQuery)

    def parent(self, keepQuery=False):
        l = self.pathList()
        if l[-1] == '':
            del l[-2]
        else:
            # We are a file, such as http://example.com/foo/bar
            # our parent directory is http://example.com/
            l.pop()
            l[-1] = ''
        return self._pathMod(l, keepQuery)

    def here(self, keepQuery=False):
        l = self.pathList()
        if l[-1] != '':
            l[-1] = ''
        return self._pathMod(l, keepQuery)

    def click(self, st):
        """Return a path which is the URL where a browser would presumably take
        you if you clicked on a link with an HREF as given.
        """
        scheme, netloc, path, query, fragment = urlparse.urlsplit(st)
        if not scheme:
            scheme = self.scheme
        if not netloc:
            netloc = self.netloc
            if not path:
                path = self.path
                if not query:
                    query = self.query
            elif path[0] != '/':
                l = self.pathList()
                l[-1] = path
                path = '/'.join(l)
        
        return URLPath(scheme,
                        netloc,
                        path,
                        query,
                        fragment)


    
    def __str__(self):
        x = urlparse.urlunsplit((
            self.scheme, self.netloc, self.path,
            self.query, self.fragment))
        return x

    def __repr__(self):
        return ('URLPath(scheme=%r, netloc=%r, path=%r, query=%r, fragment=%r)'
                % (self.scheme, self.netloc, self.path, self.query, self.fragment))

