# !/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Vincent<vincent8280@outlook.com>
#         http://wax8280.github.io
# Created on 18-7-30 上午11:52


def send_mobi(path):
    if not path:
        import os
        path = os.getcwd()

    from zhihu2kindle.libs.send_email import SendEmail2Kindle
    with SendEmail2Kindle() as s:
        s.send_all_mobi(path)
