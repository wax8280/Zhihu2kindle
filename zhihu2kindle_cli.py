# !/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Vincent<vincent8280@outlook.com>
#         http://wax8280.github.io
# Created on 2017/10/11 12:30
import click
import multiprocessing

import zhihu2kindle.script.zhihu_collection
from zhihu2kindle import DEFAULT_WINDOW
from zhihu2kindle.script.make_mobi import make_mobi
from zhihu2kindle.script.send_mobi import send_mobi

INF = 999999999


@click.group()
def cli():
    pass


@cli.command('zhihu_collection')
@click.option('--i')
@click.option('--email')
@click.option('--book_name')
@click.option('--start', default=0)
@click.option('--end', default=INF)
@click.option('--img/--no-img', default=True)
@click.option('--gif/--no-gif', default=False)
@click.option('--window', default=DEFAULT_WINDOW)
def zhihu_collection_main_cli(i, email, book_name, start, end, img, gif, window):
    zhihu2kindle.script.zhihu_collection.main(i, email, start, end, img, gif, book_name, window=window)


@cli.command('make_mobi')
@click.option('--multi/--single', default=True)
@click.option('--path')
@click.option('--window', default=50)
def make_mobi_cli(path, window, multi):
    make_mobi(path, window, multi)


@cli.command('send_mobi')
@click.option('--path')
def send_mobi_cli(path):
    send_mobi(path)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    cli()
