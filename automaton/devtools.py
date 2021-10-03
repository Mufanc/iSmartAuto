import asyncio
import ctypes
import json
import re

import httpx
import websockets
from loguru import logger

from configs import configs
from .utils import ainput

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

    async def verify(self):  # 校验客户端和配置文件中的用户是否相同
        logger.info('正在校验账号...')
        page = await self._any_http_page()
        user_info = json.loads((await page.eval('''
            (function () {
                var xhr = new XMLHttpRequest()
                xhr.open('POST', 'https://school.ismartlearning.cn/client/user/student-info', false)
                xhr.withCredentials = true
                xhr.send(null)
                return xhr.responseText
            })()
        '''))['result']['value'])['data']
        spider_user = configs['user']['username']
        if spider_user != user_info['mobile'] and spider_user != user_info['username']:
            logger.warning('检测到 iSmart 客户端中登录的账号与配置文件中账号不符！')
            choice = await ainput('继续使用可能会出现意料之外的问题，是否继续？[y/N]')
            if choice.lower() != 'y':
                return False
        else:
            logger.info('校验通过！')
        return True

    async def wait_for_book(self):  # 等待「教材学习」页面
        async with httpx.AsyncClient() as client:
            while True:
                logger.info('等待「教材学习」页面...')
                try:
                    pages = (await client.get(f'http://127.0.0.1:{self.port}/json')).json()
                    for page in pages:
                        if re.match(r'.*me.ismartlearning.cn/center/student/course/bookLearn.html.*', page['url']) and \
                                'webSocketDebuggerUrl' in page:
                            return Page(page['url'], page['webSocketDebuggerUrl'])
                except httpx.ConnectError:
                    pass
                await asyncio.sleep(2)

    async def _any_http_page(self):
        async with httpx.AsyncClient() as client:
            while True:
                logger.info('等待可用页面...')
                try:
                    pages = (await client.get(f'http://127.0.0.1:{self.port}/json')).json()
                    for page in pages:
                        if re.match(r'https?://.*', page['url']) and 'webSocketDebuggerUrl' in page:
                            return Page(page['url'], page['webSocketDebuggerUrl'])
                except httpx.ConnectError:
                    pass
                await asyncio.sleep(2)

    async def submit(self, book_id, chapter_id, task_id, score, seconds, percent, user_id):  # 提交任务点的得分
        page = await self._any_http_page()
        model = 'NetBrowser.submitTask("%s", "%s", "%s", 0, "%d", %d, %d, "%s");'
        result = f'%7B%22studentid%22:{user_id},%22testInfo%22:%7B%22answerdata%22:%22%22,%22markdatao%22:%22%22%7D%7D'
        return await page.eval(
            model % (book_id, chapter_id, task_id, score, seconds, percent, result)
        )


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
