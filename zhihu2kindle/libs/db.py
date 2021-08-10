# !/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Vincent<vincent8280@outlook.com>
#         http://wax8280.github.io
# Created on 17-12-13 下午9:56
# FIXME:sqlite3.OperationalError: database is locked

import sqlite3
import os
from threading import current_thread

DB_NAME = 'article.db'

ARTICLE_ARTICLE_SQL = """
CREATE TABLE ARTICLE(
  ARTICLE_ID              CHAR(32) PRIMARY KEY ,
  TITLE                   TEXT ,
  CONTENT                 TEXT ,
  CONTENT_PUBLISH_TIME    TEXT ,
  VOTE_UP_COUNT           TEXT ,
  AUTHOR                  TEXT ,
  CONTENT_INSERT_TIME     INTEGER ,
  VERSION                 INTEGER,
  CONSTRAINT uc_PersonID UNIQUE (ARTICLE_ID,TITLE)
);
"""
ARTICLE_META_SQL = """
CREATE TABLE META(
  META                  TEXT  PRIMARY KEY ,
  DATA                  TEXT
);
"""
ARTICLE_SQL = [ARTICLE_ARTICLE_SQL, ARTICLE_META_SQL]

INSERT_META_DATA_SQL = "INSERT INTO META VALUES (?,?)"
UPDATE_META_DATA_SQL = "UPDATE META SET DATA = ? WHERE META = ?"

INSERT_ARTICLE_SQL = "INSERT INTO ARTICLE VALUES (?,?,?,?,?,?,?,?);"
SELECT_ARTICLE_SQL = "SELECT * FROM ARTICLE WHERE VERSION = ?"
SELECT_LAST_VERION_FROM_ARTICLE_SQL = "SELECT MAX(VERSION) FROM ARTICLE;"
SELECT_METADATA_SQL = "SELECT DATA FROM META WHERE META = ?"
SELECT_ALL_ARTICLE_ID_SQL = "SELECT ARTICLE_ID FROM ARTICLE"


class ArticleDB:
    INSTANCES_FOR_THREAD = {}
    DB_INIT = False

    def __new__(cls, *args, **kwargs):
        # 每一个线程公用一个实例
        thread_name = current_thread().getName()
        if thread_name not in cls.INSTANCES_FOR_THREAD:
            instance = super(ArticleDB, cls).__new__(cls)
            cls.INSTANCES_FOR_THREAD[thread_name] = instance
            return instance
        else:
            return cls.INSTANCES_FOR_THREAD[thread_name]

    def __init__(self, script_save_path, **kwargs):
        if not ArticleDB.DB_INIT:
            if not os.path.exists(script_save_path):
                try:
                    os.makedirs(script_save_path)
                except FileExistsError:
                    pass

            conn = sqlite3.connect(os.path.join(script_save_path, DB_NAME))
            cursor = conn.cursor()
            for table in ARTICLE_SQL:
                try:
                    cursor.execute(table)
                    conn.commit()
                except sqlite3.OperationalError as e:
                    if 'table ARTICLE already exists' in str(e):
                        pass
            ArticleDB.DB_INIT = True

        self.conn = sqlite3.connect(os.path.join(script_save_path, DB_NAME))
        self.cursor = self.conn.cursor()

        for k, v in kwargs.items():
            self.insert_meta_data([k, v], update=False)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()

    @staticmethod
    def reset():
        ArticleDB.DB_INIT = False
        ArticleDB.INSTANCES_FOR_THREAD.clear()

    def create_table(self) -> None:
        for table in ARTICLE_SQL:
            try:
                self.cursor.execute(table)
                self.conn.commit()
            except sqlite3.OperationalError as e:
                if 'table ARTICLE already exists' in str(e):
                    pass

    def select_version(self) -> int:
        """返回当前VERSION"""
        return int(self.select_meta('VERSION'))

    def insert_meta_data(self, meta_data: list, update=True) -> None:
        """插入meta"""
        try:
            self.cursor.execute(INSERT_META_DATA_SQL, meta_data)
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e) and update:
                meta_data.reverse()
                self.cursor.execute(UPDATE_META_DATA_SQL, meta_data)
        finally:
            self.conn.commit()

    def insert_article(self, items: list) -> None:
        """插入文章"""
        if not len(items):
            return

        # 这次插入的VERSION比上次大
        last_version = self.select_version()
        if not isinstance(items[0], list):
            items = [items]
        if last_version is None:
            new_version = 1
        else:
            new_version = last_version + 1

        for item in items:
            item.append(new_version)
            try:
                # 忽略ARTICLE_ID(由url得到的md5)重复的
                self.cursor.execute(INSERT_ARTICLE_SQL, item)
            except sqlite3.IntegrityError as e:
                if "UNIQUE constraint failed" in str(e):
                    pass
        self.conn.commit()

    def select_article(self) -> list:
        """返回前一VERSION的所有文章"""
        return self.cursor.execute(SELECT_ARTICLE_SQL, (self.select_version() + 1,)).fetchall()

    def select_all_article_id(self) -> list:
        """返回所有文章"""
        return self.cursor.execute(SELECT_ALL_ARTICLE_ID_SQL).fetchall()

    def select_meta(self, meta) -> str:
        """返回指定meta"""
        return self.cursor.execute(SELECT_METADATA_SQL, (meta,)).fetchone()[0]

    def decrease_version(self) -> None:
        """VERSION - 1"""
        self.insert_meta_data(
            ['VERSION', int(self.cursor.execute(SELECT_LAST_VERION_FROM_ARTICLE_SQL).fetchone()[0]) - 1])

    def increase_version(self):
        """VERSION +1"""
        version = self.select_version()
        self.insert_meta_data(['VERSION', version + 1])


Scheduler_SQL = [
    """
    CREATE TABLE TASK(
      COLLECTION_ID           TEXT ,
      USERNAME                TEXT ,
      EMAIL                   TEXT,
      BOOKNAME                TEXT
    );
    """
]


class SchedulerDB:
    INSTANCES_FOR_THREAD = {}
    DB_INIT = False

    def __new__(cls, *args, **kwargs):
        # 每一个线程公用一个实例
        thread_name = current_thread().getName()
        if thread_name not in cls.INSTANCES_FOR_THREAD:
            instance = super(SchedulerDB, cls).__new__(cls)
            cls.INSTANCES_FOR_THREAD[thread_name] = instance
            return instance
        else:
            return cls.INSTANCES_FOR_THREAD[thread_name]

    def __init__(self):
        scheduler_db_path = './scheduler.db'
        if not ArticleDB.DB_INIT:
            conn = sqlite3.connect(scheduler_db_path)
            cursor = conn.cursor()
            for table in Scheduler_SQL:
                try:
                    cursor.execute(table)
                    conn.commit()
                except sqlite3.OperationalError as e:
                    if 'table ARTICLE already exists' in str(e):
                        pass
            ArticleDB.DB_INIT = True

        self.conn = sqlite3.connect(scheduler_db_path)
        self.cursor = self.conn.cursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()

    def select_task(self):
        r = self.conn.execute('SELECT * FROM TASK').fetchall()
        return [{'collection_id': each[0], 'username': each[1], 'email': each[2],'book_name':each[3]} for each in r]
