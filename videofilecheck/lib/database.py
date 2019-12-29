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
        log.debug("dbpath is %s" % dbpath)
        self.dbpath = dbpath

        if exists(self.dbpath):
            with open(self.dbpath, "rt", encoding="utf-8") as f:
                self.data = json.load(f)
                log.debug("Loading existing database with %s entries" % len(self.data["files"].keys()))
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

    def set(self, entry):
        self.data["files"][entry["videofile"]] = entry

    def get(self, videofile, md5sum=None, filesize=None):
        if md5sum is None and filesize is None:
            log.error("Database.get needs either a hash or a filesize to identify files!")
            raise Exception("Database.get needs either a hash or a filesize to identify files!")

        if videofile in self.data["files"]:
            vfile = self.data["files"][videofile]

            if "filesize" not in vfile and filesize is not None:
                log.warn("Migration: setting filesize of %s to %s" % (videofile, filesize))
                vfile["filesize"] = filesize

            if filesize is None and vfile["hash"] == md5sum:
                return vfile["status"]
            elif md5sum is None and vfile["filesize"] == filesize:
                return vfile["status"]

        return None

    def delete(self, videofile):
        del self.data["files"][videofile]

    def get_all(self):
        return self.data["files"].items()

    def to_json(self):
        return json.dumps(self.data)

    def from_json(self, data):
        self.data = json.loads(data)
