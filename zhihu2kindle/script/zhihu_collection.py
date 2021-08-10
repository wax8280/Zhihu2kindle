# !/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Vincent<vincent8280@outlook.com>
#         http://wax8280.github.io
# Created on 2017/10/9 19:07
import json
import os
from copy import deepcopy
from queue import Queue, PriorityQueue
from urllib.parse import urlparse
import time

from zhihu2kindle import MAIN_CONFIG, CONFIG_ZHIHU_COLLECTION, INF, DEFAULT_WINDOW, DEFAULT_RETRY, DEFAULT_RETRY_DELAY
from zhihu2kindle.script.content_formating import format_zhihu_content
from zhihu2kindle.libs.crawler import Crawler, md5string, RetryDownload, Task
from zhihu2kindle.libs.db import ArticleDB
from zhihu2kindle.libs.utils import write, load_config, check_config, make_crawler_meta, read_file_to_list
from zhihu2kindle.libs.html2kindle import HTML2Kindle
from zhihu2kindle.libs.log import Log
from zhihu2kindle.libs.send_email import SendEmail2Kindle

__all__ = ["main"]

# 读取脚本配置
SCRIPT_CONFIG = load_config(CONFIG_ZHIHU_COLLECTION)

LOG = Log('zhihu_collection')

DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/'
                  '61.0.3163.100 Safari/537.36'
}

ARTICLE_ID_SET = set()

META = make_crawler_meta(SCRIPT_CONFIG.get('HEADER', {}),
                         ['referer', 'connection', 'accept-encoding', 'If-None-Match', 'host', ':authority', ':method',
                          ':path', ':scheme'])

HTML_PARSER_NAME = 'lxml'

# 脚本全局变量
# 获取收藏夹名字，将其插入meta表
URL_ZHIHU_ITEM = 'https://www.zhihu.com/api/v4/collections/{}/items?offset={}&limit={}'
URL_ZHIHU_COLLECTINO = 'https://www.zhihu.com/collection/{}'


def main(collection_num, email=False, start=0, end=INF, img=True, gif=True, book_name='zhi2kindle',
         window=DEFAULT_WINDOW):

    # 检查配置
    check_config(MAIN_CONFIG, SCRIPT_CONFIG, 'SAVE_PATH', LOG)
    save_path = os.path.join(SCRIPT_CONFIG['SAVE_PATH'], str(collection_num))

    # 队列
    iq, oq, result_q = PriorityQueue(), PriorityQueue(), Queue()
    crawler = Crawler(iq, oq, result_q,
                      MAIN_CONFIG.get('PARSER_WORKER', 1),
                      MAIN_CONFIG.get('DOWNLOADER_WORKER', 1),
                      MAIN_CONFIG.get('RESULTER_WORKER', 1))

    if not META:
        new_header = deepcopy(DEFAULT_HEADERS)
        m_meta = {'headers': new_header}
    else:
        m_meta = deepcopy(META)
    m_meta['verify'] = False

    task = Task.make_task({
        'url': URL_ZHIHU_ITEM.format(collection_num, start, 20),
        'method': 'GET',
        'meta': m_meta,
        'parser': parser_collection,
        'resulter': resulter_collection,
        'priority': 0,
        'retry': DEFAULT_RETRY,
        'save': {'start': start,
                 'end': end,
                 'now': start,
                 'kw': {'img': img, 'gif': gif},
                 'book_name': book_name,
                 'save_path': save_path,
                 'collection_num': collection_num, },
        'retry_delay': DEFAULT_RETRY_DELAY
    })
    iq.put(task)

    # Init DB
    with ArticleDB(save_path, VERSION=0) as db:
        _ = db.select_all_article_id()

    # 集合去重
    if _:
        for each in _:
            ARTICLE_ID_SET.add(each[0])

    crawler.start()

    # 爬虫完毕
    # 批量新建
    items = []
    save_path = os.path.join(SCRIPT_CONFIG['SAVE_PATH'], str(collection_num))
    with ArticleDB(save_path) as db:
        items.extend(db.select_article())
        db.increase_version()
        db.reset()

    if items:
        with HTML2Kindle(items, save_path, book_name,MAIN_CONFIG.get('KINDLEGEN_PATH')) as html2kindle:
            html2kindle.make_metadata(window=window)
            html2kindle.make_book_multi(save_path)

        if email:
            save_path = os.path.join(SCRIPT_CONFIG['SAVE_PATH'], str(collection_num))
            with SendEmail2Kindle(kindle_addr=email) as s:
                s.send_all_mobi(save_path)
    else:
        LOG.logi('无新项目')


def parser_collection(task):
    to_next = True
    response = task['response']

    if not response:
        raise RetryDownload

    try:
        json_data = json.loads(response.text)
    except:
        LOG.loge("无法获取收藏列表（如一直出现，而且浏览器能正常访问知乎，可能是知乎代码升级，请通知开发者。）")
        raise RetryDownload

    download_img_list = []
    new_tasks = []
    items = []

    for item in json_data['data']:
        content = item['content']
        article_url = content['url']
        article_id = md5string(article_url)

        # 如果在数据库里面已经存在的项目，就不继续爬了
        if article_id not in ARTICLE_ID_SET:
            author_name = content['author']['name']
            title = content['question']['title'] if content.get('question') else content['title']

            voteup_count = content['voteup_count']
            created_time = item['created']
            content = content['content']

            img_list, content = format_zhihu_content(content)
            download_img_list.extend(img_list)

            items.append(
                [article_id, title, content, created_time, voteup_count, author_name, int(time.time() * 100000)])
        else:
            to_next = False

    # 获取下一页
    if to_next and task['save']['now'] < task['save']['end'] and task['save']['now'] <= json_data['paging']['totals']:
        next_url = json_data['paging']['next']
        task['save']['now'] = task['save']['now'] + 20

        new_tasks.append(Task.make_task({
            'url': next_url,
            'method': 'GET',
            'priority': 0,
            'save': task['save'],
            'meta': task['meta'],
            'parser': parser_collection,
            'resulter': resulter_collection,
        }))

    # 获取图片
    if task['save']['kw'].get('img', True):
        img_header = deepcopy(DEFAULT_HEADERS)
        img_header.update({'Referer': URL_ZHIHU_COLLECTINO.format(task['save']['collection_num'])})
        for img_url in download_img_list:
            new_tasks.append(Task.make_task({
                'url': img_url,
                'method': 'GET',
                'meta': {'headers': img_header, 'verify': False},
                'parser': parser_downloader_img,
                'resulter': resulter_downloader_img,
                'priority': 5,
                'save': task['save']
            }))

    if items:
        task.update({'parsed_data': items})
        return task, new_tasks
    else:
        return None, new_tasks


def resulter_collection(task):
    with ArticleDB(task['save']['save_path']) as article_db:
        article_db.insert_article(task['parsed_data'])


def parser_downloader_img(task):
    return task, None


"""
在convert_link函数里面md5(url)，然后转换成本地链接
在resulter_downloader_img函数里面，将下载回来的公式，根据md5(url)保存为文件名
"""


def resulter_downloader_img(task):
    if 'www.zhihu.com/equation' not in task['url']:
        write(os.path.join(task['save']['save_path'], 'static'), urlparse(task['response'].url).path[1:],
              task['response'].content, mode='wb')
    else:
        write(os.path.join(task['save']['save_path'], 'static'), md5string(task['url']) + '.svg',
              task['response'].content,
              mode='wb')
