# !/usr/bin/env python
# coding: utf-8

import logging
import sys
import os
from logging.handlers import WatchedFileHandler
from functools import partial

from zhihu2kindle import load_config

MAIN_CONFIG = load_config(os.path.join(os.path.join(os.getcwd(), 'zhihu2kindle/config'), 'config.yml'))


class BaseLog(object):
    logger_dict = {}
    log_level = 'DEBUG'
    write_log: bool = MAIN_CONFIG.get('WRITE_LOG', False)
    log_path: str = './log'

    def log(self, logger_name: str, message: str, level: str) -> None:
        if level == 'INFO':
            self.get_logger(logger_name).info(message)
        elif level == 'DEBUG':
            self.get_logger(logger_name).debug(message)
        elif level == 'ERROR':
            self.get_logger(logger_name).error(message)
        elif level == 'WARN':
            self.get_logger(logger_name).warning(message)

    def get_logger(self, logger_name: str) -> logging.Logger:
        if logger_name not in BaseLog.logger_dict:
            logger = logging.getLogger(logger_name)
            formatter = logging.Formatter(
                '[%(asctime)s][' + logger_name + '] %(message)s')

            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setFormatter(formatter)
            logger.addHandler(stream_handler)

            if self.write_log:
                failed_path = os.path.join(self.log_path, logger_name)
                if not os.path.exists(failed_path):
                    os.makedirs(failed_path)
                file_handler = WatchedFileHandler(
                    os.path.join(failed_path, logger_name + '.log'))
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)

            logger.setLevel(self.log_level)
            BaseLog.logger_dict[logger_name] = logger
        return BaseLog.logger_dict[logger_name]


class Log(BaseLog):
    def __init__(self, logger_name: str):
        super().__init__()

        self.logger_name = logger_name
        self._logger_info = partial(BaseLog.log, self=self, logger_name=self.logger_name, level='INFO')
        self._logger_debug = partial(BaseLog.log, self=self, logger_name=self.logger_name, level='DEBUG')
        self._logger_warn = partial(BaseLog.log, self=self, logger_name=self.logger_name, level='WARN')
        self._logger_error = partial(BaseLog.log, self=self, logger_name=self.logger_name, level='ERROR')

    def log_it(self, message: str, level: str = 'DEBUG') -> None:
        if level == 'INFO':
            self._logger_info(message=message)
        elif level == 'DEBUG':
            self._logger_debug(message=message)
        elif level == 'ERROR':
            self._logger_error(message=message)
        elif level == 'WARN' or level == 'WARNING':
            self._logger_warn(message=message)

    def logi(self, message: str):
        self.log_it(message, 'INFO')

    def logd(self, message: str):
        self.log_it(message, 'DEBUG')

    def loge(self, message: str):
        # TODO:trigger to send email
        self.log_it(message, 'ERROR')

    def logw(self, message: str):
        self.log_it(message, 'WARN')
