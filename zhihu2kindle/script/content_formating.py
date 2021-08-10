# !/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Vincent<vincent8280@outlook.com>
#         http://wax8280.github.io
# Created on 18-7-29 下午11:41
import re
from urllib.parse import urlparse, unquote

from zhihu2kindle.libs.utils import md5string

"知乎"


def convert_zhihu_equation_link(x):
    if 'www.zhihu.com/equation' not in x.group(1):
        return 'src="./static/{}"'.format(urlparse(x.group(1)).path[1:])
    # svg等式的保存
    else:
        url = x.group(1)
        if not url.startswith('http'):
            if url.startswith('//'):
                url = 'http:' + url
            else:
                url = 'http://' + url
        a = 'src="./static/{}.svg"'.format(md5string(url))
        return a


def format_zhihu_content(content):
    """去除空行-删除无用img标签-img居中-清除gif-移除html和body标签-获取静态资源下载地址-将静态资源的地址转换为本地路径-超链接的转换-noscript标签移除"""
    download_img_list = []
    # 换行格式化
    content = content.replace('</p><br/><p>', '<br/>').replace('</p><p><br/>', '').replace('</p><p><br>', '')
    content = re.sub('(<br>)+', '<br/>', content)
    content = re.sub('(<br/>)+', '<br/>', content)

    # 需要下载的静态资源
    download_img_list.extend(re.findall('src="(.*?)"', content))
    # 更换为本地相对路径
    content = re.sub('src="(.*?)"', convert_zhihu_equation_link, content)

    # 超链接的转换
    content = re.sub('//link.zhihu.com/\?target=(.*?)"', lambda x: unquote(x.group(1)), content)

    # 去除<noscript>
    content = re.sub('<noscript>(.*?)</noscript>', lambda x: x.group(1), content, flags=re.S)
    return download_img_list, content
