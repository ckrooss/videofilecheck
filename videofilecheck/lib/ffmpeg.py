#!/usr/bin/env python
# -*- coding: utf-8 -*-
from time import sleep
import subprocess
import logging
import os.path
from os import unlink
import shutil
from videofilecheck.lib.util import SubBar
from threading import Thread, Event

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


def watchdog(f, proc, done):
    try:
        stuck_counter = 0
        previous_progress = 0
        while not done.is_set():
            sleep(1)
            if f.tell() == previous_progress:
                stuck_counter += 1

            if stuck_counter > 5:
                log.error("Killing stuck process")
                proc.terminate()

            previous_progress = f.tell()
    except ValueError:
        return


def ffmpeg_scan(videofile: str, bar=None) -> Result:
    try:
        log.debug('Running ffmpeg for "%s"' % videofile)
        ffmpeg_call = ["ffmpeg", "-loglevel", "error", "-i", "-", "-max_muxing_queue_size", "1800", "-f", "null", "-"]

        with open(videofile, "rb") as f, SubBar(f, bar, "ffmpeg", "b") as _bar:
            proc = subprocess.Popen(ffmpeg_call, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            done = Event()
            t = Thread(target=watchdog, args=(f, proc, done))
            t.start()

            while True:
                chunk = f.read(32 * 1024)

                if not chunk:
                    break

                proc.stdin.write(chunk)

                _bar.update(len(chunk))
                _bar.refresh()

            done.set()
            t.join()

        output, _ = proc.communicate()
        output = output.decode("utf-8")
        output = remove_ignored_stuff(output)
        output = output.strip()
    except Exception as e:
        output = str(e)

    if t and t.is_alive():
        t.join()

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
