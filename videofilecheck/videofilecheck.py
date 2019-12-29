#!/usr/bin/env python
# -*- coding: utf-8 -*-
import subprocess
from os import walk, chdir
from os.path import join, expanduser, relpath, abspath
from concurrent.futures import ThreadPoolExecutor as Executor
from hashlib import md5
import argparse

from .lib.database import Database

import logging
FORMAT = '%(asctime)-15s [%(name)s] [%(levelname)s] %(message)s'
logging.basicConfig(format=FORMAT)
log = logging.getLogger(__name__)


class App:
    def __init__(self, config):
        self.nthreads = config.nthreads if config.nthreads is not None else 2
        self.dbpath = abspath(expanduser(config.dbpath) if config.dbpath is not None else expanduser("~/.vcheck.json"))
        self.db = Database(self.dbpath)
        self.output = abspath(config.output if config.output is not None else "results.txt")
        self.force_rescan = config.force_rescan if config.force_rescan is not None else False
        self.path_only = config.path_only if config.path_only is not None else False

        log.info("Settings: nthreads=%s dbpath=%s output=%s force_rescan=%s path_only=%s"
                 % (self.nthreads, self.dbpath, self.output, self.force_rescan, self.path_only))

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
        videofiles = [relpath(p, rootdir) for p in videofiles]
        return videofiles

    def store_result_to_db(self, videofile, md5sum, status):
        self.db.set(videofile, md5sum, status)
        self.db.flush()

    def calculate_md5(self, file):
        log.info("Calculating md5 of %s" % file)
        with open(file, "rb") as f:
            return md5(f.read()).hexdigest()

    def run_ffmpeg(self, file):
        log.info("Processing \"%s\"" % file)
        ffmpeg_call = ["ffmpeg", "-loglevel", "error", "-i", file, "-f", "null", "-"]
        output = subprocess.check_output(ffmpeg_call, stderr=subprocess.STDOUT)
        return output

    def worker(self, videofile):
        if self.path_only:
            md5sum = None
        else:
            md5sum = self.calculate_md5(videofile)

        db_result = self.db.get(videofile, md5sum)

        if self.force_rescan:
            log.info("Forcing a rescan for \"%s\"" % videofile)
            db_result = None

        if db_result is None:
            log.info("Running ffmpeg for \"%s\"" % videofile)
            output = self.run_ffmpeg(videofile)
            sucess = len(output) == 0
            if md5sum is None:
                md5sum = self.calculate_md5(videofile)
            self.store_result_to_db(videofile, md5sum, sucess)
            return (videofile, sucess)
        else:
            log.info("Found \"%s\" in db, hash matches, using old status %s" % (videofile, db_result))
            return (videofile, db_result)

    def scan(self, videodir, force=False):
        chdir(videodir)
        vfiles = self.find_video_files(".")
        log.info("Found %s videofiles in total" % len(vfiles))

        with Executor(max_workers=self.nthreads) as exe:
            futures = exe.map(self.worker, vfiles)

            with open(self.output, "wt") as f:
                for videofile, success in futures:
                    if not success:
                        log.warning("%s: %s" % ("FAILED", videofile))

                    f.write("%s %s\n" % ("  OK  " if success else "FAILED", videofile))
                    f.flush()

    def show(self):
        for _, entry in self.db.get_all():
            if(entry["status"] is False):
                print("%s: %s" % (entry["path"], entry["status"]))


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', help='Subcommand to run: scan, show')
    parser.add_argument('videodir', help='Directory that will be recursively scanned')
    parser.add_argument('-n', "--nthreads", help='Number of threads to run in parallel (Default: 2)')
    parser.add_argument('-d', "--dbpath", help='Database path to use to store results (Default: ~/.vcheck.json)')
    parser.add_argument('-o', "--output", help='Output textfile to store the human readable results (Default: ./results.txt)')
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
        app.scan(args.videodir)
    elif args.command == "show":
        app.show()
    else:
        parser.print_usage()
        exit(1)
