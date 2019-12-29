#!/usr/bin/env python
# -*- coding: utf-8 -*-
from subprocess import check_output
from os import walk
from shutil import move
from os.path import join, expanduser, exists
from concurrent.futures import ThreadPoolExecutor as Executor
import pickle
import tempfile
from hashlib import md5


class VFile:
    def __init__(self, p, h, s):
        self.path = p
        self.hash = h
        self.status = s


class App:
    def __init__(self):
        self.dbpath = expanduser("~/.check_files.pkl")
        self.db = self.get_database()

    def get_database(self):
        if exists(self.dbpath):
            with open(self.dbpath, "rb") as f:
                data = pickle.load(f)
                print("Loading existing database with %s entries" % len(data["files"].keys()))
        else:
            print("Creating new database")
            data = {"files": {}}
            with open(self.dbpath, "wb") as f:
                pickle.dump(data, f)

        return data

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
        return videofiles

    def get_result_from_db(self, videofile, md5sum):
        if videofile in self.db["files"]:
            if self.db["files"][videofile].hash == md5sum:
                return self.db["files"][videofile].status
            else:
                print("Hash of file: %s has changed!" % videofile)

        return None

    def store_result_to_db(self, videofile, md5sum, status):
        self.db["files"][videofile] = VFile(videofile, md5sum, status)
        tmp = tempfile.mktemp()

        with open(tmp, "wb") as f:
            pickle.dump(self.db, f)

        move(tmp, self.dbpath)

    def calculate_md5(self, file):
        print("Calculating md5 of %s" % file)
        with open(file, "rb") as f:
            return md5(f.read()).hexdigest()

    def run_ffmpeg(self, file):
        print("Processing %s" % file)
        ffmpeg_call = ["ffmpeg", "-loglevel", "error", "-i", file, "-f", "null", "-"]
        output = check_output(ffmpeg_call)
        return output

    def worker(self, videofile):
        md5sum = self.calculate_md5(videofile)
        db_result = self.get_result_from_db(videofile, md5sum)

        if db_result is None:
            print("Could not find %s in db, checking with ffmpeg" % videofile)
            output = self.run_ffmpeg(videofile)
            sucess = len(output) == 0
            self.store_result_to_db(videofile, md5sum, sucess)
            return (videofile, sucess)
        else:
            print("Found %s in db, hash matches, using old status %s" % (videofile, db_result))
            return db_result

    def check_files(self):
        vfiles = self.find_video_files(".")

        with Executor(max_workers=2) as exe:
            futures = exe.map(self.worker, vfiles)

            with open("results.txt", "wt") as f:
                for videofile, success in futures:
                    print("%s: %s" % (videofile, "OK" if success else "FAILED"))
                    f.write("%s %s" % (videofile, "OK" if success else "FAILED"))
                    f.flush()


app = App()
app.check_files()
