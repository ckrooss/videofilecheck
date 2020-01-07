#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import hashlib

log = logging.getLogger(__name__)


def checksum(file, bar=None, algorithm=hashlib.md5):
    file_hash = algorithm()
    log.debug("Calculating hash of %s using algorithm %s" % (file, file_hash.name))

    with open(file, "rb") as f:
        if bar is not None:
            f.seek(0, 2)
            filesize = f.tell()
            f.seek(0)
            bar.reset(filesize)

            if hasattr(bar, "desc"):
                bar.desc = bar.desc.replace("[____]", "[%s]" % file_hash.name)
            bar.unit = "b"
            bar.unit_scale = True

        while True:
            chunk = f.read(8192)
            if bar is not None:
                bar.update(len(chunk))

            if not chunk:
                break

            file_hash.update(chunk)

    if bar is not None and hasattr(bar, "desc"):
        bar.desc = bar.desc.replace("[%s]" % file_hash.name, "[____]")

    hexdigest = file_hash.hexdigest()
    log.debug("Hash of %s is %s" % (file, hexdigest))
    return hexdigest
