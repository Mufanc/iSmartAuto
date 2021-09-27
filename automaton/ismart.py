import json
import os
import pickle
import urllib.parse as parser

from bs4 import BeautifulSoup
from loguru import logger
from random import random, randint

from configs import configs
from .devtools import Browser
from .markdown import generate_md
from .spider import Spider

random_args = {  # 不同题型对应的随机时长和分数范围
    '1': {  # 单选题
        'time': (20, 60),  # 完成时长 / 秒
        'score': 1  # 得分 (归一化, 向上随机取至满分)
    },
    '2': {  # 多选题
        'time': (40, 120),
        'score': 0.9
    },
    '3': {  # 判断题
        'time': (20, 50),
        'score': 1
    },
    '4': {  # 填空题
        'time': (60, 180),
        'score': 1
    },
    '6': {  # 连线题
        'time': (60, 180),
        'score': 0.8
    },
    '8': {  # 匹配题
        'time': (30, 90),
        'score': 1
    },
    '9': {  # 口语跟读
        'time': (15, 30),
        'score': 0.8
    },
    '10': {  # 短文改错
        'time': (120, 180),
        'score': 0.7
    },
    '11': {  # 选词填空
        'time': (30, 90),
        'score': 0.9
    }
}


def _random_progress(paper):
    paper = BeautifulSoup(paper, 'lxml-xml')
    questions = paper.select('element[knowledge]:has(> question_type)')
    if questions:
        total_score = 0
        my_score, my_time = 0, 0
        for que in questions:
            qt_type = que.select_one('question_type').text
            qt_score = int(que.select_one('question_score').text)
            total_score += qt_score

            rate = 1 - (1 - random_args[qt_type]['score']) * random()
            my_score += qt_score * rate
            my_time += randint(*random_args[qt_type]['time'])
        return int(100 * my_score / total_score), my_time
    return 100, 5


async def export():  # 导出某书籍的答案
    browser = Browser.connect()
    page = await browser.wait_for_book()
    params = dict(parser.parse_qsl(parser.urlsplit(page.url).query))
    # noinspection PyTypeChecker
    book_id, course_id = params['bookId'], params['courseId']
    if not os.path.exists(f'.cache/books/{book_id}'):
        async with Spider() as spider:
            await spider.login(**configs['user'])
            book = await spider.book_info(book_id)
            book['courseId'] = course_id
            tasks = await spider.get_tasks(book, tree=True)
            await spider.download_tree(tasks)
    with open(f'.cache/books/{book_id}/Tree.pck', 'rb') as fp:
        generate_md(pickle.load(fp))


async def finish():  # 直接完成某书籍的任务
    browser = Browser.connect()
    page = await browser.wait_for_book()
    params = dict(parser.parse_qsl(parser.urlsplit(page.url).query))
    # noinspection PyTypeChecker
    book_id, course_id = params['bookId'], params['courseId']
    async with Spider() as spider:
        await spider.login(**configs['user'])
        if not os.path.exists(f'.cache/books/{book_id}'):
            book = await spider.book_info(book_id)
            book['courseId'] = course_id
            tasks = await spider.get_tasks(book, tree=True)
            await spider.download_tree(tasks)
        user_id = (await spider.get_user())['data']['uid']
    logger.info('正在提交任务...')
    for file in os.listdir(f'.cache/books/{book_id}'):
        paper_id, ext = os.path.splitext(file)
        if ext != '.json':
            continue

        with open(f'.cache/books/{book_id}/{file}') as fp:
            data = json.load(fp)
            task = data['task']
            paper = data['paperData']
        score, time = _random_progress(paper)
        result = await page.submit(book_id, task['chapterId'], task['id'], score, time, 100, user_id)
        if result['wasThrown'] or not result['result']['value']:
            logger.warning(f'任务 {task["name"]} [paperId: {paper_id}] 可能提交失败，请留意最终结果！')
    logger.info('全部提交完成！')


async def finish_all():  # Todo: 全刷了？
    pass
