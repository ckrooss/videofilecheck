#!/usr/bin/env python
# -*- coding: utf-8 -*-
import subprocess
import logging
import os.path
from os import unlink
import shutil

log = logging.getLogger(__name__)


IGNORE_THESE_ERRORS = ["Application provided invalid, non monotonically increasing dts to muxer"]


class Result:
    def __init__(self, output: str):
        self.output = output
        self.success = len(output) == 0

    def __str__(self):
        return "Result(success=%s, output=%s)" % (self.success, self.output)

    def __repr__(self):
        return str(self)


def ignore_line(data: str) -> bool:
    for poison in IGNORE_THESE_ERRORS:
        if poison in data:
            return True
    else:
        return False


def remove_ignored_stuff(data: str) -> str:
    wanted_output = []
    lines = data.splitlines()

    for l in lines:
        if ignore_line(l):
            continue
        else:
            wanted_output.append(l)

    return "\n".join(wanted_output)


def ffmpeg_scan(file: str) -> Result:
    log.debug('Running ffmpeg for "%s"' % file)
    ffmpeg_call = ["ffmpeg", "-loglevel", "error", "-i", file, "-max_muxing_queue_size", "400", "-f", "null", "-"]
    output = subprocess.check_output(ffmpeg_call, stderr=subprocess.STDOUT)
    output = output.decode("utf-8")
    output = remove_ignored_stuff(output)
    output = output.strip()

    # If the error-string length is 0, there are no errors
    return Result(output)


def ffmpeg_remux(file: str):
    """use ffmpeg to remux a (avi,mkv,mp4, whatever) file in-place, copying all audio/video/subtitle streams as-is"""

    if not os.path.isfile(file):
        log.error("Can only remux files, got %s" % file)
        raise Exception("Can only remux files, got %s" % file)

    extension = os.path.splitext(file)[1]
    tmpfile = os.path.dirname(file) + "_temp_" + extension
    try:
        ffmpeg_call = ["ffmpeg", "-loglevel", "error", "-i", file, "-c", "copy", "-map", "0", tmpfile]
        output = subprocess.check_output(ffmpeg_call, stderr=subprocess.STDOUT)
        output = output.decode("utf-8")
        output = remove_ignored_stuff(output)
        output = output.strip()
        if output:
            log.warning(output)

        shutil.move(tmpfile, file)
    except Exception as e:
        log.error(e)
        unlink(tmpfile)

    return
