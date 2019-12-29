#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
from os.path import exists
import tempfile
from shutil import move
import logging
log = logging.getLogger(__name__)

DEFAULT_CONTENT = {"files": {}}


class Database:
    def __init__(self, dbpath):
        log.info("dbpath is %s" % dbpath)
        self.dbpath = dbpath

        if exists(self.dbpath):
            with open(self.dbpath, "rt", encoding="utf-8") as f:
                self.data = json.load(f)
                log.info("Loading existing database with %s entries" % len(self.data["files"].keys()))
        else:
            log.info("Creating new database")
            self.data = DEFAULT_CONTENT
            self.flush()

    def flush(self):
        tmp = tempfile.mktemp()

        with open(tmp, "wt", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)
            f.flush()

        move(tmp, self.dbpath)

    def set(self, videofile, md5sum, status):
        self.data["files"][videofile] = dict(videofile=videofile, hash=md5sum, status=status)

    def get(self, videofile, md5sum=None):
        if videofile in self.data["files"]:
            vfile = self.data["files"][videofile]

            if md5sum is None or vfile["hash"] == md5sum:
                return vfile["status"]
            else:
                log.warning("Hash of file: %s has changed!" % videofile)

        return None

    def get_all(self):
        return self.data["files"].items()

    def to_json(self):
        return json.dumps(self.data)

    def from_json(self, data):
        self.data = json.loads(data)
