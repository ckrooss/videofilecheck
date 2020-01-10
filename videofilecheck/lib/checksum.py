#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import hashlib
from videofilecheck.lib.util import SubBar
log = logging.getLogger(__name__)


def checksum(file, bar, algorithm=hashlib.md5):
    file_hash = algorithm()
    log.debug("Calculating hash of %s using algorithm %s" % (file, file_hash.name))

    with open(file, "rb") as f, SubBar(f, bar, file_hash.name, "b") as _bar:
        while True:
            chunk = f.read(8192)

            if not chunk:
                break

            _bar.update(len(chunk))
            file_hash.update(chunk)

    hexdigest = file_hash.hexdigest()
    log.debug("Hash of %s is %s" % (file, hexdigest))
    return hexdigest
