import asyncio
import json
import os
import pickle
from hashlib import md5
from random import random

import httpx
from loguru import logger

from .captcha import recognize


class Tree:
    def __init__(self, task):
        self.task = task
        self.children = []


class Spider(httpx.AsyncClient):
    def __init__(self):
        super().__init__()

    async def login(self, username, password):  # 账号密码登录
        logger.info('正在获取验证码...')
        result = await self.get(f'http://sso.ismartlearning.cn/captcha.html?{random()}')
        code = recognize(result.content)
        token = md5(password.encode()).hexdigest()
        info = (await self.post(
            'http://sso.ismartlearning.cn/v2/tickets-v2',
            data={
                'username': username,
                'password': md5(token.encode() + b'fa&s*l%$k!fq$k!ld@fjlk').hexdigest(),
                'captcha': code
            },
            headers={
                'X-Requested-With': 'XMLHttpRequest',
                'Origin': 'http://me.ismartlearning.cn',
                'Referer': 'http://me.ismartlearning.cn/'
            }
        )).json()
        logger.debug(info['result'])

        if info['result']['code'] != -26:
            raise AssertionError(f'[!] 登录失败: {info["result"]["msg"]}')
        return info['result']

    async def get_courses(self):  # 获取用户课程列表
        logger.info('正在获取课程列表...')
        courses = (await self.post(
            'https://school.ismartlearning.cn/client/course/list-of-student?status=1',
            data={
                'pager.currentPage': 1,
                'pager.pageSize': 32767
            }
        )).json()['data']
        return courses['list']

    async def get_books(self, course):  # 获取某课程的书籍列表
        logger.info('正在获取书籍列表...')
        await self.get_courses()  # 必须有这个请求，否则后面会报错
        books = (await self.post(
            'http://school.ismartlearning.cn/client/course/textbook/list-of-student',
            data={
                'courseId': course['courseId']
            }
        )).json()['data']
        return books

    @staticmethod
    def _merge_tasks(tasks):  # 将任务列表重组成树形结构
        id_record = {task['id']: Tree(task) for task in tasks}
        root = Tree({
            'book_id': tasks[0]['book_id'],
            'unitStudyPercent': 0
        })

        for task_id in id_record:
            node = id_record[task_id]
            node_name = (f'{node.task["name"]} ' if 'name' in node.task else '') + f'[id:{node.task["id"]}]'
            if 'parent_id' in node.task:
                if (parent_id := node.task['parent_id']) in id_record:
                    id_record[parent_id].children.append(node)
                else:
                    logger.warning(f'任务已忽略（父节点不存在）：{node_name}')
            else:
                root.children.append(node)

        return root

    async def get_tasks(self, book, tree=False):  # 获取某书籍的任务列表
        logger.info('正在获取任务列表...')
        await self.post('http://school.ismartlearning.cn/client/course/textbook/chapters')
        tasks = (await self.post(
            'http://school.ismartlearning.cn/client/course/textbook/chapters',
            data={key: book[key] for key in ('bookId', 'bookType', 'courseId')}
        )).json()['data']
        if tree:
            return self._merge_tasks(tasks)
        else:
            return tasks

    async def get_paper(self, paper_id):  # 获取任务点信息（包括题目和答案）
        ticket = (await self.post(
            'http://sso.ismartlearning.cn/v1/serviceTicket',
            data={
                'service': 'http://xot-api.ismartlearning.cn/client/textbook/paperinfo'
            }
        )).json()['data']['serverTicket']
        logger.debug(f'Ticket: {ticket}')
        paper_info = (await self.post(
            'http://xot-api.ismartlearning.cn/client/textbook/paperinfo',
            data={
                'paperId': paper_id
            },
            headers={
                'Origin': 'http://me.ismartlearning.cn',
                'Referer': 'http://me.ismartlearning.cn/',
                'X-Requested-With': 'XMLHttpRequest',
                'Accept-Encoding': 'gzip, deflate'
            },
            params={
                'ticket': ticket
            }
        )).json()['data']
        return paper_info

    async def download_tree(self, root):
        async def download(task):
            paper_id = task['paperId']
            filepath = f'.cache/books/{root.task["book_id"]}/{paper_id}.json'
            if os.path.exists(filepath):
                return
            async with limit:  # 防止并发过高
                result = await self.get_paper(paper_id)
            result['task'] = task  # 继续存入 Task
            with open(filepath, 'w') as file:
                json.dump(result, file)

        def dfs(src):
            if 'paperId' in (task := src.task):
                logger.info(f'添加任务：{task["name"]}')
                tasks.append(download(task))
            for child in src.children:
                dfs(child)

        logger.info('开始下载试题及答案...')
        os.makedirs(f'.cache/books/{root.task["book_id"]}', exist_ok=True)
        with open(f'.cache/books/{root.task["book_id"]}/Tree.pck', 'wb') as fp:
            pickle.dump(root, fp)
        tasks, limit = [], asyncio.Semaphore(4)
        dfs(root)
        await asyncio.gather(*tasks)
        logger.info('下载完成.')

    async def get_user(self):
        return (await self.post(
            'https://school.ismartlearning.cn/client/user/student-info')
        ).json()

    async def book_info(self, book_id):
        ticket = (await self.post(
            'http://sso.ismartlearning.cn/v1/serviceTicket',
            data={
                'service': 'http://book-api.ismartlearning.cn/client/v2/book/info'
            }
        )).json()['data']['serverTicket']
        book_info = (await self.post(
            'http://book-api.ismartlearning.cn/client/v2/book/info',
            headers={
                'Origin': 'http://me.ismartlearning.cn',
                'Referer': 'http://me.ismartlearning.cn/',
                'X-Requested-With': 'XMLHttpRequest',
                'Accept-Encoding': 'gzip, deflate'
            },
            params={
                'ticket': ticket
            },
            data={
                'bookId': book_id,
                'bookType': 0
            }
        )).json()
        return book_info['data']
