#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
from os.path import exists
import tempfile
from shutil import move
from threading import Lock
import logging
log = logging.getLogger(__name__)

DEFAULT_CONTENT = {"files": {}}


def locked(func):
    def _synchronized(self, *args, **kw):
        with self.lock:
            return func(self, *args, **kw)

    return _synchronized


class Database:
    def __init__(self, dbpath):
        log.debug("dbpath is %s" % dbpath)
        self.dbpath = dbpath
        self.lock = Lock()

        if exists(self.dbpath):
            with open(self.dbpath, "rt", encoding="utf-8") as f:
                self.data = json.load(f)
                log.debug("Loading existing database with %s entries" % len(self.data["files"].keys()))
        else:
            log.info("Creating new database")
            self.data = DEFAULT_CONTENT
            self.flush()

    @locked
    def flush(self):
        tmp = tempfile.mktemp()

        with open(tmp, "wt", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)
            f.flush()

        move(tmp, self.dbpath)

    @locked
    def set(self, entry):
        self.data["files"][entry["videofile"]] = entry

    @locked
    def get(self, videofile, filehash=None, filesize=None):
        if videofile not in self.data["files"]:
            return None

        vfile = self.data["files"][videofile]

        if filehash is None and filesize is None:
            return vfile["status"]

        if "filesize" not in vfile and filesize is not None:
            log.warn("Migration: setting filesize of %s to %s" % (videofile, filesize))
            vfile["filesize"] = filesize

        size_match = (filesize is None or vfile["filesize"] == filesize)
        hash_match = (filehash is None or vfile["hash"] == filehash)

        if filesize is not None and vfile["filesize"] != filesize:
            log.debug("Size mismatch for %s - old \"%s\" vs. new \"%s\"" % (videofile, vfile["filesize"], filesize))

        if filehash is not None and vfile["hash"] != filehash:
            log.debug("Hash mismatch for %s - old \"%s\" vs. new \"%s\"" % (videofile, vfile["hash"], filehash))

        if size_match and hash_match:
            return vfile["status"]

        return None

    @locked
    def delete(self, videofile):
        del self.data["files"][videofile]

    @locked
    def get_all(self):
        return self.data["files"].items()
