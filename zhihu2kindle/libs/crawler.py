# !/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Vincent<vincent8280@outlook.com>
#         http://wax8280.github.io
# Created on 2017/10/10 9:53
import traceback
import time
from queue import PriorityQueue, Empty, Queue

import requests
from threading import Thread, Condition, Lock

from zhihu2kindle.libs.log import Log
from zhihu2kindle.libs.utils import md5string, PriorityList

# 禁用安全请求警告
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
COND = Condition()
LOCK = Lock()


class RetryDownload(Exception):
    pass


class RetryDownloadNodelay(Exception):
    pass


class RetryDownloadEnForce(Exception):
    """强制将task放入to_download队列"""
    pass


class RetryDownloadEnForceNodelay(Exception):
    pass


class RetryParse(Exception):
    pass


class RetryParseNodelay(Exception):
    pass


class RetryParseEnForce(Exception):
    """强制将task放入download_parser队列"""
    pass


class RetryParseEnForceNodelay(Exception):
    pass


class RetryResult(Exception):
    pass


class RetryResultNodelay(Exception):
    pass


class RetryResultEnForce(Exception):
    """强制将task放入parser_resulter队列"""
    pass


class RetryResultEnForceNodelay(Exception):
    pass


class Task(dict):
    """
    'task': {
        'tid': str,                         md5(request.url + request.data)
        'method':str                        HTTP method
        'url':str                           URL
        'parser': function
        'priority': int,                    Priority of task
        'retried': int,                     Retried count
        'retry': int,                       Retry time
        'meta':dict                         A dict to some config or something to save
        {
            'params':dict/bytes             (optional) Dictionary or bytes to be sent in the query string
            'data':dict/list                (optional) Dictionary or list of tuples [(key, value)]
                                            (will be form-encoded), bytes, or file-like object
            ‘json':str                      (optional) json data to send in the body
            'headers':dict                  (optional) Dictionary of HTTP Headers
            'cookies':dict/CookieJar        (optional) Dict or CookieJar object
            'files':dict                    (optional) Dictionary of 'name': file-like-objects (or {'name': file-tuple})
                                            for multipart encoding upload. can be a 2-tuple ('filename', fileobj),
                                            3-tuple ('filename', fileobj, 'content_type') a 4-tuple
                                            ('filename', fileobj, 'content_type', custom_headers), where 'content-type'
                                            is a string the content type of the given file and custom_headers a
                                            dict-like object containing additional headers add for the file.
            'timeout':float/tuple           (optional) a float, or (connect timeout, read timeout) tuple.
            'allow_redirects':bool          (optional) Boolean. Enable/disable GET/OPTIONS/POST/PUT/PATCH/DELETE/HEAD
                                            redirection. Defaults to True.
            'proxies':dict                  (optional) Dictionary mapping protocol to the URL of the proxy.
            'verify':bool/str               (optional) Either a boolean, in which case it controls whether we verify
                                            server's TLS certificate, or a string, in which case it must be a path
                                            a CA bundle to use. Defaults to True.
            'stream':bool                   (optional) if False, the response content will be immediately downloaded.
            'cert':str/tuple                (optional) if String, path to ssl client cert file (.pem).
                                            If Tuple, ('cert', 'key') pair.
        },

        'response': requests.models.Response,
        # for detail:http://docs.python-requests.org/en/master/api/#requests.Response
        {
            'status_code':int               HTTP status code
            'url':str                       url
            'history':list                  A list of Response objects from the history of the Request. Any redirect
                                            responses will end up here. The list is sorted from the oldest to the most
                                            recent request.
            'encoding':str
            'reason':str                    OK
            'elapsed':timedelta             The amount of time elapsed between sending the request and the arrival of
                                            the response
            'text':str/unicode              Content of the response, in unicode.
            json():
                Returns the json-encoded content of a response, if any.
                    Parameters:	**kwargs -- Optional arguments that json.loads takes.
                    Raises:	ValueError -- If the response body does not contain valid json.

        }
        parsed_data:                        Structured data from parser
        to_download_timestamp：int          Timestamp to put in download queue
        retry_delay: int                    Retry delay
    }
    """

    def __eq__(self, other):
        return self['priority'] == other['priority']

    def __lt__(self, other):
        return self['priority'] > other['priority']

    @staticmethod
    def make_task(params):
        if 'parser' not in params:
            # FIXME Can't raise Exception in there
            raise Exception("Need a parser")
        if 'method' not in params:
            raise Exception("Need a method")
        if 'url' not in params:
            raise Exception("Need a url")

        tid = md5string(params['url'] + str(params.get('data')) + str(params.get('params')))
        params.setdefault('meta', {})
        params.setdefault('priority', 0)
        params.setdefault('retry', 3)
        params.setdefault('tid', tid)

        if not params['url'].startswith('http'):
            if params['url'].startswith('//'):
                params['url'] = 'http:' + params['url']
            else:
                params['url'] = 'http://' + params['url']
        return Task(**params)


def retry(task: Task, queue: Queue or PriorityQueue):
    if task.get('retry', None):
        task.setdefault('retried', 0)
        if task.get('retried', 0) < task.get('retry'):
            task['retried'] += 1
            if task.get('retry_delay'):
                # TaskManager只认to_download_timestamp
                task['to_download_timestamp'] = time.time() + task.get('retry_delay')
                TaskManager.push_delay_queue(task)
            else:
                queue.put(task)
        else:
            TaskManager.unregister(task['tid'])
    else:
        # 不重试，直接取消注册
        TaskManager.unregister(task['tid'])


def retry_nodelay(task: Task, queue: Queue or PriorityQueue):
    if task.get('retry', None):
        task.setdefault('retried', 0)
        if task.get('retried', 0) < task.get('retry'):
            task['retried'] += 1
            queue.put(task)
        else:
            TaskManager.unregister(task['tid'])
    else:
        # 不重试，直接取消注册
        TaskManager.unregister(task['tid'])


class TaskManager:
    registered_task = set()
    ALLDONE = False
    delay_task_prioritylist = PriorityList()
    delay_task_time_section = set()
    start_timestamp = time.time()
    granularity = 0.1
    lock = LOCK

    def __init__(self, to_download_q: PriorityQueue, ):
        self.to_download_q = to_download_q
        self._exit = False

    @staticmethod
    def register(tid):
        TaskManager.lock.acquire()
        try:
            TaskManager.registered_task.add(tid)
        except:
            traceback.print_exc()
        finally:
            TaskManager.lock.release()

    @staticmethod
    def unregister(tid):
        TaskManager.lock.acquire()
        try:
            TaskManager.registered_task.remove(tid)
        except KeyError:
            pass
        finally:
            TaskManager.lock.release()

    @staticmethod
    def is_empty():
        TaskManager.lock.acquire()
        is_empty = (len(TaskManager.registered_task) == 0)
        TaskManager.lock.release()
        if is_empty:
            TaskManager.ALLDONE = True
        return is_empty

    @staticmethod
    def get_time_section(t: int or float) -> float:
        """
        取大
        >>> TaskManager.start_timestamp=1518490691.5014048
        >>> TaskManager.get_time_section(1518490691.5014048+1.6)
        1518490693.5014048
        >>> TaskManager.get_time_section(1518490691.5014048+1.9)
        1518490693.5014048

        :param t:
        :return:
        """
        time_section = TaskManager.start_timestamp
        while t > time_section:
            time_section += TaskManager.granularity
        return time_section

    @staticmethod
    def push_delay_queue(task: Task):
        to_dowload_timestamp = TaskManager.get_time_section(task['to_download_timestamp'])

        TaskManager.lock.acquire()
        try:
            # 如果已经在delay_task_time_section，说明已经存在delay_task_prioritylist里面
            if to_dowload_timestamp in TaskManager.delay_task_time_section:
                # 一直pop直到遇到to_download_timestamp的task为止
                flag = True
                old_tasks_list = []
                while flag:
                    tmp_tasks_list = TaskManager.delay_task_prioritylist.priority_pop()
                    # print(to_dowload_timestamp,tmp_tasks_list)
                    if tmp_tasks_list:
                        if tmp_tasks_list[0] != to_dowload_timestamp:
                            # 不相同的，重新入队
                            pass
                        else:
                            flag = False
                            tmp_tasks_list[1].append(task)

                        old_tasks_list.append(tmp_tasks_list)
                    else:
                        raise Exception("!BUG!")
                        # delay_task_prioritylist里面为空。正常情况下不会运行到这里。
                        # to_dowload_timestamp在delay_task_time_section，说明已经存在delay_task_prioritylist里面
                        pass
                for each_tasks_list in old_tasks_list:
                    TaskManager.delay_task_prioritylist.priority_push(each_tasks_list)
            else:
                # 全新的
                TaskManager.delay_task_prioritylist.priority_push([to_dowload_timestamp, [task]])
                TaskManager.delay_task_time_section.add(to_dowload_timestamp)
        except:
            traceback.print_exc()
        finally:
            TaskManager.lock.release()

    def pop_to_download_queue(self):
        now_time = time.time()
        to_next = True

        TaskManager.lock.acquire()
        try:
            while to_next:
                tasks_list = TaskManager.delay_task_prioritylist.priority_pop()
                if tasks_list:
                    if tasks_list[0] <= now_time:
                        # 放入downloader队列
                        for task in tasks_list[1]:
                            del task['to_download_timestamp']
                            self.to_download_q.put(task)
                            with COND:
                                COND.notify_all()
                        TaskManager.delay_task_time_section.remove(tasks_list[0])
                    else:
                        # 重新放入等待队列
                        TaskManager.delay_task_prioritylist.priority_push(tasks_list)
                        to_next = False
                else:
                    to_next = False
        except:
            traceback.print_exc()
        finally:
            TaskManager.lock.release()

    def run(self):
        while not self._exit:
            _ = time.time()

            self.pop_to_download_queue()
            time.sleep(self.granularity / 4)

    def exit(self):
        self._exit = True


class Downloader(Thread):
    def __init__(self,
                 to_download_q: PriorityQueue,
                 downloader_parser_q: PriorityQueue,
                 result_q: Queue,
                 name: str,
                 session=requests.session()):
        super().__init__(name=name)
        self.to_download_q = to_download_q
        self.downloader_parser_q = downloader_parser_q
        self.result_q = result_q
        self.session = session

        self._exit = False

        self.log = Log(self.name)

    def exit(self):
        self._exit = True

    def request(self):
        response = None

        try:
            task = self.to_download_q.get_nowait()
            TaskManager.register(task['tid'])
        except Empty:
            # self.log.log_it("Scheduler to Downloader队列为空，{}等待中。".format(self.name), 'DEBUG')
            with COND:
                COND.wait()
                # self.log.log_it("Downloader to Parser队列不为空。{}被唤醒。".format(self.name), 'DEBUG')
            return

        self.log.log_it("请求 {}".format(task['url']), 'INFO')
        try:
            response = self.session.request(task['method'], task['url'], **task.get('meta', {}))
        except Exception as e:
            traceback.print_exc()
            self.log.log_it("网络请求错误。错误信息:{} URL:{} Response:{}".format(str(e), task['url'], response), 'INFO')
            retry(task, self.to_download_q)
            return

        if response:
            task['response'] = response
        else:
            task['response'] = None

        self.downloader_parser_q.put(task)

    def run(self):
        while not self._exit:
            self.request()


class Parser(Thread):
    def __init__(
            self,
            to_download_q: PriorityQueue,
            downloader_parser_q: PriorityQueue,
            result_q: Queue,
            name: str):
        super().__init__(name=name)
        self.downloader_parser_q = downloader_parser_q
        self.to_download_q = to_download_q
        self.result_q = result_q

        self._exit = False
        self.log = Log(self.name)

    def exit(self):
        self._exit = True

    def parser(self):

        with COND:
            COND.notify_all()
        try:
            task = self.downloader_parser_q.get_nowait()
        except Empty:
            time.sleep(0.1)
            with COND:
                COND.notify_all()
            return

        try:
            task_with_parsed_data, tasks = task['parser'](task)
            if tasks:
                if not isinstance(tasks, list):
                    tasks = [tasks]
                self.log.log_it("获取新任务{}个。".format(len(tasks)), 'INFO')
                for each_task in tasks:
                    TaskManager.register(each_task['tid'])
                    self.to_download_q.put(each_task)
        except RetryDownload:
            self.log.log_it("RetryDownload Exception.Task{}".format(task), 'INFO')
            retry(task, self.to_download_q)
            return
        except RetryDownloadEnForce:
            self.log.log_it("RetryDownloadEnForce Exception.Task{}".format(task), 'INFO')
            self.to_download_q.put(task)
            return
        except RetryParse:
            self.log.log_it("RetryParse Exception.Task{}".format(task), 'INFO')
            retry(task, self.downloader_parser_q)
            return
        except RetryParseEnForce:
            self.log.log_it("RetryParse Exception.Task{}".format(task), 'INFO')
            self.downloader_parser_q.put(task)
            return
        except Exception as e:
            self.log.log_it("解析错误。错误信息：{}。Task：{}".format(str(e), task), 'WARN')
            traceback.print_exc()
            return
        TaskManager.unregister(task['tid'])
        return task_with_parsed_data

    def run(self):
        while not self._exit:
            task_with_parsed_data = self.parser()
            if task_with_parsed_data:
                self.result_q.put(task_with_parsed_data)


class Resulter(Thread):
    def __init__(
            self,
            to_download_q: PriorityQueue,
            downloader_parser_q: PriorityQueue,
            result_q: Queue,
            name: str):
        super().__init__(name=name)
        self.result_q = result_q
        self.downloader_parser_q = downloader_parser_q
        self.to_download_q = to_download_q

        self._exit = False
        self.log = Log(self.name)

    def exit(self):
        self._exit = True

    def result(self):
        with COND:
            COND.notify_all()

        try:
            task = self.result_q.get_nowait()
        except Empty:
            time.sleep(0.1)
            return

        try:
            self.log.log_it("正在处理{}".format(task['tid']))
            task['resulter'](task)
        except RetryDownload:
            self.log.log_it("RetryDownload Exception.Task{}".format(task), 'INFO')
            retry(task, self.to_download_q)
            return
        except RetryDownloadEnForceNodelay:
            self.log.log_it("RetryDownloadEnForce Exception.Task{}".format(task), 'INFO')
            self.to_download_q.put(task)
            return
        except RetryDownloadNodelay:
            self.log.log_it("RetryDownloadNodelay Exception.Task{}".format(task), 'INFO')
            retry_nodelay(task, self.to_download_q)
            return

        except RetryParse:
            self.log.log_it("RetryParse Exception.Task{}".format(task), 'INFO')
            retry(task, self.downloader_parser_q)
            return
        except RetryParseEnForceNodelay:
            self.log.log_it("RetryParse Exception.Task{}".format(task), 'INFO')
            self.downloader_parser_q.put(task)
            return
        except RetryParseNodelay:
            self.log.log_it("RetryParseNodelay Exception.Task{}".format(task), 'INFO')
            retry_nodelay(task, self.downloader_parser_q)
            return

        except RetryResult:
            self.log.log_it("RetryResult Exception.Task{}".format(task), 'INFO')
            retry(task, self.result_q)
            return
        except RetryResultEnForceNodelay:
            self.log.log_it("RetryResultEnForce Exception.Task{}".format(task), 'INFO')
            self.result_q.put(task)
            return
        except RetryResultNodelay:
            self.log.log_it("RetryResultNodelay Exception.Task{}".format(task), 'INFO')
            retry_nodelay(task, self.result_q)
            return

        except Exception as e:
            traceback.print_exc()
            self.log.log_it("Resulter函数错误。错误信息：{}。Task：{}".format(str(e), task), 'WARN')
            retry(task, self.result_q)
            return

    def run(self):
        while (not TaskManager.ALLDONE) or (not self.result_q.empty()):
            self.result()


class Crawler:
    def __init__(self,
                 to_download_q: PriorityQueue,
                 downloader_parser_q: PriorityQueue,
                 result_q: Queue,
                 parser_worker_count,
                 downloader_worker_count,
                 resulter_worker_count,
                 session=requests.session()):
        self.parser_worker_count = int(parser_worker_count)
        self.downloader_worker_count = int(downloader_worker_count)
        self.resulter_worker_count = int(resulter_worker_count)
        self.downloader_worker = []
        self.parser_worker = []
        self.resulter_worker = []
        self.log = Log("Crawler")

        self.to_download_q = to_download_q
        self.downloader_parser_q = downloader_parser_q
        self.result_q = result_q

        self.task_manager = TaskManager(self.to_download_q)
        self.session = session
        self.lock = LOCK

        self.task_manager_thread = Thread(target=self.task_manager.run)

    def start(self):
        self.task_manager_thread.start()

        for i in range(self.downloader_worker_count):
            _worker = Downloader(self.to_download_q, self.downloader_parser_q, self.result_q, "Downloader {}".format(i),
                                 self.session, )
            self.downloader_worker.append(_worker)
            self.log.log_it("启动 Downloader {}".format(i), 'INFO')
            _worker.start()

        for i in range(self.parser_worker_count):
            _worker = Parser(self.to_download_q, self.downloader_parser_q, self.result_q, "Parser {}".format(i))
            self.parser_worker.append(_worker)
            self.log.log_it("启动 Parser {}".format(i), 'INFO')
            _worker.start()

        for i in range(self.resulter_worker_count):
            _worker = Resulter(self.to_download_q, self.downloader_parser_q, self.result_q, "Resulter {}".format(i))
            self.resulter_worker.append(_worker)
            self.log.log_it("启动 Resulter {}".format(i), 'INFO')
            _worker.start()

        while True:
            time.sleep(1)
            if self.task_manager.is_empty():
                for worker in self.downloader_worker:
                    worker.exit()
                for worker in self.parser_worker:
                    worker.exit()

                resulter_not_alive = False
                while not resulter_not_alive:
                    resulter_not_alive = True
                    time.sleep(1)
                    for worker in self.resulter_worker:
                        resulter_not_alive &= not worker.is_alive()

                for worker in self.resulter_worker:
                    worker.exit()

                self.task_manager.exit()
                TaskManager.ALLDONE = False
                return
