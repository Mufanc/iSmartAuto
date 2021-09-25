import asyncio
import ctypes
import json
import re

import httpx
import websockets
from loguru import logger

from configs import configs

_default_port = configs['browser']['port']
_executable = configs['browser']['executable']
_args = configs['browser']['args']


class Browser(object):
    @classmethod
    def connect(cls):
        return cls(_default_port)

    @classmethod
    def launch(cls):
        ctypes.windll.shell32.ShellExecuteW(
            None, 'runas', _executable,
            ' '.join([f'--remote-debugging-port={_default_port}', *_args]),
            None, 1
        )
        return cls(_default_port)

    def __init__(self, dev_port):
        self.port = dev_port

    async def wait_for_book(self):  # 等待「教材学习」页面
        async with httpx.AsyncClient() as client:
            while True:
                logger.info('等待「教材学习」页面...')
                try:
                    pages = (await client.get(f'http://127.0.0.1:{self.port}/json')).json()
                    for page in pages:
                        if re.match(r'.*me.ismartlearning.cn/center/student/course/bookLearn\.html.*', page['url']):
                            return Page(page['url'], page['webSocketDebuggerUrl'])
                    await asyncio.sleep(2)  # 这样写跟套 finally 有区别
                except httpx.ConnectError:
                    await asyncio.sleep(2)


class Page(object):
    def __init__(self, url, dev_url):
        self.id = 0
        self.url, self.dev_url = url, dev_url

    async def send(self, command, params):
        async with websockets.connect(self.dev_url) as devtools:
            await devtools.send(json.dumps({
                'id': self.id,
                'method': command,
                'params': params
            }))
            self.id += 1
            return json.loads(await devtools.recv())

    async def eval(self, script):
        result = await self.send(
            'Runtime.evaluate', {
                'expression': script,
                'awaitPromise': True
            }
        )
        return result['result']

    async def submit(self, book_id, chapter_id, task_id, score, seconds, percent, user_id):
        model = 'NetBrowser.submitTask("%s", "%s", "%s", 0, "%d", %d, %d, "%s");'
        result = f'%7B%22studentid%22:{user_id},%22testInfo%22:%7B%22answerdata%22:%22%22,%22markdatao%22:%22%22%7D%7D'
        return await self.eval(
            model % (book_id, chapter_id, task_id, score, seconds, percent, result)
        )
