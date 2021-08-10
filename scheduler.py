from zhihu2kindle import Log
from zhihu2kindle.libs.db import SchedulerDB
import traceback
import subprocess
import time

day_sec = 60 * 60 * 24

if __name__ == '__main__':
    logger = Log('Scheduler')

    while True:
        try:
            with SchedulerDB() as s:
                task_list = s.select_task()
                task_count = len(task_list)
                logger.logi('用户信息:{}'.format(task_list))

                if not task_list:
                    logger.logi('等待{}秒'.format(day_sec))
                    time.sleep(day_sec)

                for task in task_list:
                    subprocess.run(
                        'python zhihu2kindle_cli.py zhihu_collection --i="{}" --email="{}" --book_name="{}"'.format(
                            task['collection_id'],
                            task['email'],
                            task['book_name']
                        ))
                    # 一天时间平分，比如有24个用户，则每个任务结束后sleep 1小时
                    logger.logi('等待{}秒'.format(day_sec / task_count))
                    time.sleep(day_sec / task_count)

        except:
            logger.loge(traceback.format_exc())
            time.sleep(60 * 5)
