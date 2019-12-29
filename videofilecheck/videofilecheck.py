#!/usr/bin/env python
# -*- coding: utf-8 -*-
import subprocess
from time import time, sleep
from os import walk, chdir
from os.path import join, expanduser, relpath, abspath, getsize
from concurrent.futures import ThreadPoolExecutor as Executor, as_completed
from hashlib import md5
import argparse
from tqdm import tqdm

from .lib.database import Database

import logging
FORMAT = '%(asctime)-15s [%(name)s] [%(levelname)s] %(message)s'
logging.basicConfig(format=FORMAT)
log = logging.getLogger(__name__)


class App:
    def __init__(self, config):
        self.nthreads = int(config.nthreads) if config.nthreads is not None else 2
        self.dbpath = abspath(expanduser(config.dbpath) if config.dbpath is not None else expanduser("~/.vcheck.json"))
        self.db = Database(self.dbpath)
        self.force_rescan = config.force_rescan if config.force_rescan is not None else False
        self.path_only = config.path_only if config.path_only is not None else False
        self.verbose = True if config.verbose else False

        log.debug("Settings: nthreads=%s dbpath=%s force_rescan=%s path_only=%s"
                  % (self.nthreads, self.dbpath, self.force_rescan, self.path_only))

    def find_video_files(self, rootdir):
        videofiles = []

        for root, subdirs, files in walk(rootdir):

            for file in files:
                if any([file.endswith(".mkv"),
                        file.endswith(".mp4"),
                        file.endswith(".avi")]):
                    videofiles.append(join(root, file))
                else:
                    continue

            idx = 0
            while idx < len(subdirs):
                if subdirs[idx].startswith("@"):
                    subdirs.remove(subdirs[idx])
                    idx = 0
                else:
                    idx += 1

        # make path relative to rootdir so e.g. the mountpoint does not invalidate the cache
        videofiles = sorted([relpath(p, rootdir) for p in videofiles])
        return videofiles

    def store_result_to_db(self, videofile, md5sum, status):
        entry = dict(videofile=videofile,
                     hash=md5sum,
                     status=status,
                     timestamp=int(time()),
                     filesize=getsize(videofile))

        self.db.set(entry)
        self.db.flush()

    def calculate_md5(self, file):
        log.debug("Calculating md5 of %s" % file)
        with open(file, "rb") as f:
            file_hash = md5()

            while True:
                chunk = f.read(8192)
                if not chunk:
                    break

                file_hash.update(chunk)

        hexdigest = file_hash.hexdigest()
        log.debug("Hash of %s is %s" % (file, hexdigest))
        return hexdigest

    def run_ffmpeg(self, file):
        log.debug("Running ffmpeg for \"%s\"" % file)
        ffmpeg_call = ["ffmpeg", "-loglevel", "error", "-i", file, "-f", "null", "-"]
        output = subprocess.check_output(ffmpeg_call, stderr=subprocess.STDOUT)
        return output

    def worker(self, videofile):
        try:
            if self.path_only:
                md5sum = None
            else:
                md5sum = self.calculate_md5(videofile)

            db_result = self.db.get(videofile, md5sum, getsize(videofile))

            if self.force_rescan:
                log.debug("Forcing a rescan for \"%s\"" % videofile)
                db_result = None

            if db_result is None:
                output = self.run_ffmpeg(videofile)
                sucess = len(output) == 0
                if md5sum is None:
                    md5sum = self.calculate_md5(videofile)
                self.store_result_to_db(videofile, md5sum, sucess)
                return (videofile, sucess)
            else:
                log.debug("Found \"%s\" in db, using old status %s" % (videofile, db_result))
                return (videofile, db_result)
        except Exception as e:
            import traceback
            traceback.print_exception(e)

    def scan(self, videodir, force=False):
        """Scan videofiles in videodir recursively. Ignore existing results if force is set"""

        chdir(videodir)
        vfiles = self.find_video_files(".")
        log.debug("Found %s videofiles in total" % len(vfiles))

        with Executor(max_workers=self.nthreads) as exe:
            futures = [exe.submit(self.worker, vfile) for vfile in vfiles]

            failed = []

            # Use an empty lambda as a progress-bar in verbose mode to prevent ugly console output
            def passthrough(iterable, total):
                return iterable

            progress = passthrough if self.verbose else tqdm
            for future in progress(as_completed(futures), total=len(vfiles)):
                sleep(0.01)  # TQDM doesnt update without a very short sleep :/
                if future.exception() is not None:
                    log.error(future.exception())
                    continue

                vfile, success = future.result()
                if not success:
                    failed.append(vfile)

            for vfile in failed:
                log.warning("FAILED: %s" % vfile)

            self.db.flush()

    def rescan(self, videodir):
        """Rescan all files in videodir that have a previous status of FAILED"""
        chdir(videodir)
        vfiles = self.find_video_files(".")

        for vfile in vfiles:
            db_result = self.db.get(vfile)

            if db_result is not None and db_result is False:
                log.debug("Rescanning previously failed file %s" % vfile)
                self.db.delete(vfile)

        self.scan(videodir)

    def show(self):
        for _, entry in self.db.get_all():
            if(entry["status"] is False):
                print("%s: %s" % (entry["videofile"], entry["status"]))


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', help='Subcommand to run: scan, rescan, show')
    parser.add_argument('videodir', help='Directory that will be recursively scanned')
    parser.add_argument('-n', "--nthreads", help='Number of threads to run in parallel (Default: 2)')
    parser.add_argument('-d', "--dbpath", help='Database path to use to store results (Default: ~/.vcheck.json)')
    parser.add_argument('-f', "--force-rescan", help='Rescan every file, even if it has been scanned before (Default: No)', action='store_true')
    parser.add_argument('-p', "--path-only", help='Only scan files using their path, skip hashing file content (Default: No)', action='store_true')
    verb = parser.add_mutually_exclusive_group()
    verb.add_argument("-v", "--verbose", help="log more", action='store_true')
    verb.add_argument("-q", "--quiet", help="log less", action='store_true')
    args = parser.parse_args()

    baselogger = logging.getLogger("videofilecheck")
    if args.verbose:
        baselogger.setLevel(logging.DEBUG)
    elif args.quiet:
        baselogger.setLevel(logging.WARN)
    else:
        baselogger.setLevel(logging.INFO)

    app = App(args)

    if args.command == "scan":
        log.info("Running scan on video directory %s" % args.videodir)
        app.scan(args.videodir)
    elif args.command == "rescan":
        log.info("Running rescan on video directory %s" % args.videodir)
        app.rescan(args.videodir)
    elif args.command == "show":
        log.info("Showing results for video directory %s" % args.videodir)
        app.show()
    else:
        parser.print_usage()
        exit(1)
