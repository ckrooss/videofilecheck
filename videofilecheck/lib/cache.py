#!/usr/bin/env python
# -*- coding: utf-8 -*-
from shutil import copyfile
from os.path import join, basename
from os import unlink
import logging
log = logging.getLogger(__name__)

SHM = "/dev/shm"


class CachedFile:
    def __enter__(self):
        return self

    def __init__(self, src: str, bar=None):
        self.original = src
        self._cached = None
        self.bar = bar

    def __exit__(self, *exc):
        if self._cached is not None:
            assert self._cached.startswith(SHM)
            unlink(self._cached)

    @property
    def cached(self):
        if self._cached is not None:
            return self._cached

        dst = join(SHM, basename(self.original))
        log.debug("Caching %s to %s" % (self.original, dst))
        with open(self.original, "rb") as fsrc, open(dst, "wb") as fdst:
            if self.bar is not None:
                fsrc.seek(0, 2)
                filesize = fsrc.tell()
                fsrc.seek(0)
                self.bar.total = filesize
                self.bar.unit = "b"
                self.bar.unit_scale = True

            while True:
                chunk = fsrc.read(8192)
                if self.bar is not None:
                    self.bar.update(len(chunk))

                if not chunk:
                    break

                fdst.write(chunk)

        self._cached = dst
        return self._cached
