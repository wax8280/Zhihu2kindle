# !/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Vincent<vincent8280@outlook.com>
#         http://wax8280.github.io
# Created on 2017/10/10 9:52
import datetime
import time
import heapq
import os
import random
import re
import yaml
import hashlib
import platform
import base64

from functools import wraps


def md5string(x):
    return hashlib.md5(x.encode()).hexdigest()


def singleton(cls):
    instances = {}

    @wraps(cls)
    def getinstance(*args, **kw):
        if cls not in instances:
            the_instances = cls(*args, **kw)
            instances[cls] = the_instances
            return the_instances
        else:
            return instances[cls]

    return getinstance


def load_config(path):
    try:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.load(f, Loader=yaml.Loader)
        except UnicodeDecodeError:
            with open(path, 'r') as f:
                return yaml.load(f, Loader=yaml.Loader)
    except FileNotFoundError:
        return {}


def write_config(path, d):
    # path所在的目录
    if not os.path.exists(os.path.split(path)[0]):
        os.makedirs((os.path.split(path)[0]))

    dump_string = yaml.dump(d)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(dump_string)


def get_system():
    return platform.system()


def get_all_files_from_path(path, mfilter="", no_include=None):
    """
    返回path下面所有符合mfilter正则的文件.
    get_all_files_from_path('./zhihu2kindle/script', '.py$', ['__init__.py'])
    :param path:            str         路径
    :param mfilter:         str         正则过滤pattern
    :param no_include:      list        过滤列表
    :return:
    """
    result = []

    for root, dirs, files in os.walk(path):
        for each_file_name in files:
            file_path = os.path.join(root, each_file_name)

            if mfilter:
                if not re.search(mfilter, file_path):
                    continue

            if no_include:
                if each_file_name in no_include:
                    continue

            result.append(file_path)
    return result


def find_file(rootdir, pattern):
    finded = []
    for i in os.listdir(rootdir):
        if not os.path.isdir(os.path.join(rootdir, i)):
            if re.search(pattern, i):
                finded.append(os.path.join(rootdir, i))
    return finded


def write(folder_path, file_path, content, mode='wb'):
    path = os.path.join(folder_path, file_path)
    if not os.path.exists(os.path.split(path)[0]):
        try:
            os.makedirs((os.path.split(path)[0]))
        except FileExistsError:
            pass
    with open(path, mode) as f:
        f.write(content)


def codes_write(folder_path, file_path, content, mode='wb'):
    path = os.path.join(folder_path, file_path)
    if not os.path.exists(os.path.split(path)[0]):
        os.makedirs((os.path.split(path)[0]))
    with open(path, mode) as f:
        f.write(content)


def format_file_name(file_name, a=''):
    file_name = re.sub(r'[ \\/:*?"<>→|+\r\n]', '', file_name)

    if a:
        # 文件名太长无法保存mobi
        if len(file_name) + len(a) + 2 > 55:
            _ = 55 - len(a) - 2 - 3
            file_name = file_name[:_] + '...（{}）'.format(a)
        else:
            file_name = file_name + '（{}）'.format(a)
    else:
        if len(file_name) > 55:
            _ = 55 - 3
            file_name = file_name[:_] + '...'
        else:
            file_name = file_name
    return file_name


def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    return str(text)


def read_file_to_list(path):
    try:
        with open(path, 'r') as f:
            return [i.strip() for i in list(f.readlines())]
    except FileNotFoundError as e:
        return str(e)
    except Exception as e:
        return str(e)


def check_config(main_config, script_config, config_name, logger):
    if config_name not in script_config:
        if config_name in main_config:
            script_config.update({config_name: main_config.get(config_name)})
        else:
            logger.log_it("在配置文件中没有发现'{}'项，请确认主配置文件中或脚本配置文件中存在该项。".format(config_name), 'ERROR')
            os._exit(0)


def split_list(the_list, window):
    return [the_list[i:i + window] for i in range(0, len(the_list), window)]


def random_char(c):
    return [chr(random.choice(list(set(range(65, 123)) - set(range(91, 97))))) for i in range(c)]


def get_next_datetime_string(data_string: str, format_string: str, days: int, prev=False) -> str:
    now_datatime = datetime.datetime.strptime(data_string, format_string)
    if prev:
        return (now_datatime - datetime.timedelta(days=days)).strftime(format_string)
    else:
        return (now_datatime + datetime.timedelta(days=days)).strftime(format_string)


def compare_datetime_string(data_stringA: str, data_stringB: str, format_string: str) -> bool:
    """return true if data_stringA is bigger or equal"""
    return datetime.datetime.strptime(data_stringA, format_string) >= datetime.datetime.strptime(data_stringB,
                                                                                                 format_string)


def get_datetime_string(format_string: str) -> str:
    return datetime.datetime.fromtimestamp(time.time()).strftime(format_string)


class PriorityList(list):
    """
    >>> a = PriorityList()
    >>> a.priority_push([150, ['t5', 't6']])
    >>> print(a)
    [[150, ['t5', 't6']]]
    >>> a.priority_push([50, ['t1', 't2']])
    >>> print(a)
    [[50, ['t1', 't2']], [150, ['t5', 't6']]]
    >>> a.priority_push([100, ['t3', 't4']])
    >>> print(a)
    [[50, ['t1', 't2']], [150, ['t5', 't6']], [100, ['t3', 't4']]]
    >>> print(a.priority_pop())
    [50, ['t1', 't2']]
    >>> print(a)
    [[100, ['t3', 't4']], [150, ['t5', 't6']]]
    """

    def priority_pop(self):
        # lowest is first
        try:
            return heapq.heappop(self)
        except IndexError:
            return None

    def priority_push(self, item):
        heapq.heappush(self, item)


def make_string_to_dict(base64_headers: str) -> dict:
    """分割: """
    d = {}
    s = base64.decodebytes(base64_headers.encode('utf-8')).decode('utf-8')
    string_list_by_line = s.strip().split('\n')

    for each in string_list_by_line:
        each = each.strip()
        # 去除:开头的
        if each.startswith(':'):
            continue

        re_group = re.search("(.*?):[ ]*(.*?)$", each)
        d[re_group[1]] = re_group[2].strip()

    return d


def split_cookies(s: str) -> dict:
    """分割cookie"""
    d = {}
    for each in s.split(';'):
        a = re.search("(.*?)=[\"\']?(.*?)[\"\']?$", each)

        k = a.group(1).strip()
        v = a.group(2).strip()
        d[k] = v

    return d


def make_crawler_meta(s: str, filter_k=None) -> dict:
    """
    解析Chrome导出的请求头部
    base64.encodebytes(raw_headers.encode('utf-8')).decode('utf-8')
    base64.decodebytes(base64_headers.encode('utf-8')).decode('utf-8')
    """

    if not s:
        return {}

    if filter_k is None:
        filter_k = []

    d = make_string_to_dict(s)
    meta_d = {'headers': {}}

    for k, v in d.items():
        if k.lower() == "cookie":
            meta_d['cookies'] = split_cookies(v)
        elif k.lower() in filter_k:
            pass
        else:
            meta_d['headers'].update({k: v})
    return meta_d
