# !/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Vincent<vincent8280@outlook.com>
#         http://wax8280.github.io
# Created on 2017/10/11 7:48
from zhihu2kindle.libs.utils import load_config
import os
from zhihu2kindle.libs.log import Log

INF = 99999999999999999999

CURRENT_PATH = os.getcwd()
CONFIG_PATH = os.path.join(CURRENT_PATH, 'zhihu2kindle/config')
BIN_PATH = os.path.join(CURRENT_PATH, 'zhihu2kindle/bin')
TEMPLATES_PATH = os.path.join(CURRENT_PATH, 'zhihu2kindle/templates')
MAIN_CONFIG_PATH = os.path.join(CONFIG_PATH, 'config.yml')
EMAIL_CONFIG = os.path.join(CONFIG_PATH, 'email.yml')

TEMPLATES_KINDLE_CONTENT = os.path.join(TEMPLATES_PATH, 'kindle_content.html')
TEMPLATES_KINDLE_OPF = os.path.join(TEMPLATES_PATH, 'kindle_opf.html')
TEMPLATES_KINDLE_TABLE = os.path.join(TEMPLATES_PATH, 'kindle_table.html')
TEMPLATES_KINDLE_NCX = os.path.join(TEMPLATES_PATH, 'kindle_ncx.ncx')

CONFIG_ZHIHU_ANSWERS = os.path.join(CONFIG_PATH, 'zhihu_answers.yml')
CONFIG_ZHIHU_COLLECTION = os.path.join(CONFIG_PATH, 'zhihu_collection.yml')
CONFIG_ZHIHU_ZHUANLAN = os.path.join(CONFIG_PATH, 'zhihu_zhuanlan.yml')
CONFIG_ZHIHU_DAILY = os.path.join(CONFIG_PATH, 'zhihu_daily.yml')

MAIN_CONFIG = load_config(MAIN_CONFIG_PATH)
EMAIL_CONFIG = load_config(EMAIL_CONFIG)

DEFAULT_WINDOW = 20
DEFAULT_RETRY = 10
DEFAULT_RETRY_DELAY = 10

KINDLE_GEN_PATH = MAIN_CONFIG['KINDLEGEN_PATH']