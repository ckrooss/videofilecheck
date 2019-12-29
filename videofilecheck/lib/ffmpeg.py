#!/usr/bin/env python
# -*- coding: utf-8 -*-
import subprocess
import logging
log = logging.getLogger(__name__)


IGNORE_THESE_ERRORS = [
    "Application provided invalid, non monotonically increasing dts to muxer"
]


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


def ffmpeg_no_errors(file):
    log.debug("Running ffmpeg for \"%s\"" % file)
    ffmpeg_call = ["ffmpeg", "-loglevel", "error", "-i", file, "-f", "null", "-"]
    output = subprocess.check_output(ffmpeg_call, stderr=subprocess.STDOUT)
    output = output.decode("utf-8")
    output = remove_ignored_stuff(output)
    output = output.strip()

    # If the error-string length is 0, there are no errors
    return len(output) == 0
