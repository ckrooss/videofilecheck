#!/usr/bin/env python
# -*- coding: utf-8 -*-
from time import sleep
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

def ffmpeg_scan(videofile: str, bar=None) -> Result:
    log.debug('Running ffmpeg for "%s"' % videofile)
    ffmpeg_call = ["ffmpeg", "-loglevel", "error", "-i", "-", "-max_muxing_queue_size", "400", "-f", "null", "-"]

    with open(videofile, "rb") as f:
        if bar is not None:
            f.seek(0, 2)
            filesize = f.tell()
            f.seek(0)
            bar.reset(filesize)

            if hasattr(bar, "desc"):
                bar.desc = bar.desc.replace("[____]",  "[ffmpeg]")
            bar.unit = "b"
            bar.unit_scale = True

        proc = subprocess.Popen(ffmpeg_call, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        while True:
            chunk = f.read(32 * 1024)

            if not chunk:
                break

            proc.stdin.write(chunk)

            if bar is not None:
                bar.update(len(chunk))
                bar.refresh()

    output, _ = proc.communicate()
    output = output.decode("utf-8")
    output = remove_ignored_stuff(output)
    output = output.strip()

    if bar is not None:
        if hasattr(bar, "desc"):
            bar.desc = bar.desc.replace("[ffmpeg]", "[____]")

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
