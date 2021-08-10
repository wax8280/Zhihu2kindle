# !/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Vincent<vincent8280@outlook.com>
#         http://wax8280.github.io
# Created on 17-12-14 下午8:23
import codecs
import os
from multiprocessing import cpu_count
from jinja2 import Template
from functools import partial

from zhihu2kindle.libs.log import Log
from zhihu2kindle.libs.utils import read_file, format_file_name, split_list, random_char
from zhihu2kindle import KINDLE_GEN_PATH, TEMPLATES_KINDLE_CONTENT, TEMPLATES_KINDLE_NCX, TEMPLATES_KINDLE_OPF, \
    TEMPLATES_KINDLE_TABLE

Html2KindleLog = Log('HTML2Kindle')


class HTML2Kindle:
    content_template = Template(read_file(TEMPLATES_KINDLE_CONTENT))
    opf_template = Template(read_file(TEMPLATES_KINDLE_OPF))
    index_template = Template(read_file(TEMPLATES_KINDLE_TABLE))
    ncx_template = Template(read_file(TEMPLATES_KINDLE_NCX))

    def __init__(self, items: list, path: str, book_name: str, kindlegen_path: str = KINDLE_GEN_PATH) -> None:
        self.kindlegen_path = kindlegen_path if kindlegen_path is not None else KINDLE_GEN_PATH
        self.items = items
        self.book_name = str(book_name)
        self.path = path
        self.to_remove = set()
        self.log = Log('HTML2Kindle')

        if not os.path.exists(path):
            os.makedirs(path)

    def __exit__(self, exc_type: None, exc_val: None, exc_tb: None) -> None:
        self.remove()

    def __enter__(self):
        return self

    def remove(self) -> None:
        for i in self.to_remove:
            try:
                os.remove(i)
            except FileNotFoundError:
                pass

    def make_metadata(self, window: str or int = 20) -> None:
        window = int(window)
        spilt_items = split_list(self.items, window)

        # 根据window分割电子书
        for index, items in enumerate(spilt_items):
            self.log.log_it("制作 {}_{} 的元数据".format(self.book_name, str(index)), 'INFO')
            opf = []
            table = []
            table_name = '{}_{}.html'.format(self.book_name, str(index))
            opf_name = '{}_{}.opf'.format(self.book_name, str(index))
            ncx_name = '{}_{}.ncx'.format(self.book_name, str(index))
            table_path = os.path.join(self.path, table_name)
            opf_path = os.path.join(self.path, opf_name)
            ncx_path = os.path.join(self.path, ncx_name)

            # 标记，以便删除
            self.to_remove.add(table_path)
            self.to_remove.add(opf_path)
            self.to_remove.add(ncx_path)

            for item in items:
                kw = {'author_name': item[5], 'voteup_count': item[4], 'created_time': item[3]}
                # 文件名=title+author
                article_path = os.path.join(self.path, format_file_name(item[1], item[5]) + '.html')
                if os.path.exists(article_path):
                    # 防止文件名重复
                    article_path = article_path.replace('.html', '') + ''.join(random_char(3)) + '.html'

                self.make_content(item[1], item[2], article_path, kw)
                # 标记，以便删除
                self.to_remove.add(article_path)
                opf.append({'id': article_path, 'href': article_path, 'title': item[1]})
                table.append({'href': article_path, 'name': item[1]})

            self.make_table(table, table_path)
            self.make_opf(self.book_name + '_' + str(index), opf, table_path, opf_path, ncx_path)
            self.make_ncx(self.book_name + '_' + str(index), opf, table_path, ncx_path)

    def make_opf(self, title: str, navigation: list, table_path: str, opf_path: str, ncx_path: str) -> None:
        rendered_content = self.opf_template.render(title=title, navigation=navigation, table_href=table_path,
                                                    ncx_href=ncx_path)
        with codecs.open(opf_path, 'w', 'utf_8_sig') as f:
            f.write(rendered_content)

    def make_ncx(self, title: str, navigation: list, table_path: str, opf_path: str) -> None:
        rendered_content = self.ncx_template.render(title=title, navigation=navigation, table_href=table_path)
        with codecs.open(opf_path, 'w', 'utf_8_sig') as f:
            f.write(rendered_content)

    def make_content(self, title: str, content: str, path: str, kw: dict = None) -> None:
        rendered_content = self.content_template.render(title=title, content=content, kw=kw)
        with codecs.open(path, 'w', 'utf_8_sig') as f:
            f.write(rendered_content)

    def make_table(self, navigation: list, path: str) -> None:
        rendered_content = self.index_template.render(navigation=navigation)
        with codecs.open(path, 'w', 'utf_8_sig') as f:
            f.write(rendered_content)

    @staticmethod
    def _make_book(kindlegen_path: str, log_path: str, path: str) -> None:
        print("{} -dont_append_source {}".format(kindlegen_path, path))
        os.system("{} -dont_append_source {}".format(kindlegen_path, path))

    def make_book_multi(self, rootdir: str, overwrite: bool = True) -> None:
        from multiprocessing import Pool
        self.log.log_it("新建 {} 个线程制作mobi文件.正在制作中，请稍后".format(str(cpu_count())), 'INFO')
        pool = Pool(cpu_count())
        opf_list = self.get_opf(rootdir, overwrite)
        pool.map(partial(self._make_book, self.kindlegen_path, os.path.join(self.path, 'kindlegen.log')), opf_list)

    def make_book(self, rootdir: str, overwrite: bool = True) -> None:
        opf_list = self.get_opf(rootdir, overwrite)
        self.log.log_it("正在制作中，请稍后", 'INFO')
        for i in opf_list:
            os.system("{} -dont_append_source {} > {}".format(self.kindlegen_path, os.path.join(rootdir, i),
                                                              os.path.join(self.path, 'kindlegen.log')))

    def get_opf(self, rootdir: str, overwrite: bool) -> list:
        result = []
        mobi = []
        for i in os.listdir(rootdir):
            if not os.path.isdir(os.path.join(rootdir, i)):
                if i.lower().endswith('mobi'):
                    mobi.append(i)

        for i in os.listdir(rootdir):
            if not os.path.isdir(os.path.join(rootdir, i)):
                if i.lower().endswith('opf'):
                    if overwrite:
                        result.append(os.path.join(rootdir, i))
                    else:
                        if i.replace('opf', 'mobi') not in mobi:
                            result.append(os.path.join(rootdir, i))
        return result
