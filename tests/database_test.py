#!/usr/bin/env python
# -*- coding: utf-8 -*-
from videofilecheck.lib.database import Database
import tempfile
import json
from os.path import exists
from os import unlink
import pytest


@pytest.fixture(scope="module")
def dbpath():
    p = tempfile.mktemp()
    assert not exists(p)
    yield p
    assert exists(p)
    unlink(p)


def test_db_default_created(dbpath):
    Database(dbpath)


def test_db_default_content(dbpath):
    Database(dbpath)

    with open(dbpath, "rt", encoding="utf-8") as f:
        content = json.load(f)

    assert "files" in content
    assert len(content["files"]) == 0


def test_db_set_get(dbpath):
    db = Database(dbpath)
    db.set(dict(videofile="a/b", hash="hashsum", filesize=1, status=False))
    db.set(dict(videofile="a/c", hash="hashsum2", filesize=2, status=True))
    assert len(db.get_all()) == 2

    assert db.get("a/b", "hashsum") is False
    assert db.get("a/c", "hashsum2") is True

    assert db.get("a/b", "hashsum", 1) is False
    assert db.get("a/c", "hashsum2", 2) is True

    assert db.get("a/b", None, 1) is False
    assert db.get("a/c", None, 2) is True

    assert db.get("a/b", "wronghash", 1) is None
    assert db.get("a/c", "wronghash", 2) is None

    assert db.get("wrongfile", "hashsum", 1) is None
    assert db.get("wrongfile", "hashsum2", 2) is None

    assert db.get("a/b", "hashsum", 99) is None
    assert db.get("a/c", "hashsum2", 99) is None
