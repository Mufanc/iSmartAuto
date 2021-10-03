import asyncio
from concurrent.futures import ThreadPoolExecutor
import urllib.parse as parser

from configs import configs
from .devtools import Browser
from .spider import Spider


class Tree:  # 任务树
    def __init__(self, task):
        self.task = task
        self.child = []


async def ainput(prompt: str = ''):
    with ThreadPoolExecutor(1, 'ainput') as executor:
        return (
            await asyncio.get_event_loop().run_in_executor(executor, input, prompt)
        ).rstrip()


async def flash_recent():  # 对当前书籍执行刷课
    if configs['browser']['mode'] == 'launch':
        browser = Browser.launch()
    else:
        browser = Browser.connect()
    page = await browser.wait_for_book()
    params = dict(parser.parse_qsl(parser.urlsplit(page.url).query))
    # noinspection PyTypeChecker
    book_id, course_id = params['bookId'], params['courseId']
    async with Spider() as spider:
        await spider.login(**configs['user'])
