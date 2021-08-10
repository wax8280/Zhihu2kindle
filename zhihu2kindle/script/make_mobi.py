# !/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Vincent<vincent8280@outlook.com>
#         http://wax8280.github.io
# Created on 18-7-30 上午11:52
import os


def make_mobi(path, window=50, multi=True):
    from zhihu2kindle.libs.db import ArticleDB
    from zhihu2kindle import MAIN_CONFIG
    from zhihu2kindle.libs.html2kindle import HTML2Kindle

    if not path:
        path = os.getcwd()

    items = []
    with ArticleDB(path) as db:
        db.decrease_version()
        items.extend(db.select_article())
        book_name = db.select_meta('BOOK_NAME')

    if items:
        with HTML2Kindle(items, path, book_name, MAIN_CONFIG.get('KINDLEGEN_PATH')) as html2kindle:
            html2kindle.make_metadata(window)
            if multi:
                html2kindle.make_book_multi(path)
            else:
                html2kindle.make_book(path)
