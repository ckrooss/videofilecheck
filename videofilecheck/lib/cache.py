#!/usr/bin/env python
# -*- coding: utf-8 -*-
from shutil import copyfile
from os.path import join, basename, expanduser, exists
from os import unlink, makedirs, statvfs, stat
from threading import Lock
import logging
from videofilecheck.lib.util import SubBar
log = logging.getLogger(__name__)


class CacheException(Exception):
    pass


class CacheLocation():
    """
    Handle the available space for a given cache-location
    As multiple threads use the same cache, space is immediately "reserved" so that a 1GB cache
    cannot be used by 3x500MB threads at the same time
    """

    def __init__(self, path):
        self.usage = 0
        self.lock = Lock()
        self.path = expanduser(path)

    def reserve(self, size):
        with self.lock:
            if 1.1 * size > self.__available():
                return False

            self.usage += size
            return True

    def free(self, size):
        with self.lock:
            self.usage -= size
            assert self.usage >= 0

    def __available(self):
        if not exists(self.path):
            log.warn("%s path does not exist" % self)
            return 0
        else:
            vfs_stat = statvfs(self.path)
            fs_available = vfs_stat.f_frsize * vfs_stat.f_bavail
            log.debug("%s path total size %d, usage %d" % (self, fs_available, self.usage))

            return fs_available - self.usage

    def __str__(self):
        return "Cache(path=%s)" % self.path

    def __repr__(self):
        return str(self)


CACHEDIRS = [
    CacheLocation("/dev/shm"),
    CacheLocation("~/vcheck_cache/")
]


class UnCachedFile:
    """Same interface as CachedFile without actually doing the caching"""

    def __enter__(self):
        return self

    def __init__(self, src: str, bar=None):
        self.original = src
        self._cached = src
        self.bar = bar

    def __exit__(self, *exc):
        pass

    @property
    def cached(self):
        return self._cached


class CachedFile:
    """
    Context manager to access a file that needs to be read multiple times
    Upon entering, the file is copied to a fast location, e.g. RAM
    On exit, the cache is deleted

    When not enough space is available in RAM, other locations  (SSD) are used
    """

    def __enter__(self):
        return self

    def __init__(self, src: str, bar=None):

        # File path of the original file, or example in the library
        self.original = src

        # File path of the cached file, for example in /tmp. If this is None, no cached file exists
        self._cached = None
        self.bar = bar
        self.cachedir = None
        self.do_delete = False
        self.size = stat(self.original).st_size

    def __exit__(self, *exc):
        if self._cached is not None and self.do_delete:
            assert any(self._cached.startswith(cachedir.path) for cachedir in CACHEDIRS)
            unlink(self._cached)
            log.debug("Deleting %s" % self._cached)

            self.cachedir.free(self.size)

    @property
    def cached(self):
        if self._cached is not None:
            return self._cached

        for cachedir in CACHEDIRS:
            if not cachedir.reserve(self.size):
                log.debug("Not enough space on %s for %s" % (cachedir, self.original))
                continue

            self.cachedir = cachedir
            break

        if self.cachedir is None:
            return self.original

        dst = join(self.cachedir.path, basename(self.original))
        log.debug("Caching %s to %s" % (self.original, dst))
        with open(self.original, "rb") as fsrc, open(dst, "wb") as fdst, SubBar(fsrc, self.bar, "cache", "b") as _bar:
            while True:
                chunk = fsrc.read(8192)

                if not chunk:
                    break

                _bar.update(len(chunk))
                fdst.write(chunk)

        self.do_delete = True
        self._cached = dst
        return self._cached
