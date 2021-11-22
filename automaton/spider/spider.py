import json
from hashlib import md5
from random import random

import httpx
from loguru import logger

from .captcha import recognize


class Tree:  # 任务树
    def __init__(self, task):
        self.task = task
        self.child = []

    def sort(self):
        self.child.sort(
            key=lambda node: node.task['displayOrder']
        )
        for ch in self.child:
            ch.sort()


class Spider(httpx.AsyncClient):
    def __init__(self):
        super().__init__()
        self.is_login = False

    async def login(self, username, password):
        if self.is_login:
            return {}

        self.cookies.clear()  # 重置 cookies
        logger.info('正在获取验证码...')
        result = await self.get(f'http://sso.ismartlearning.cn/captcha.html?{random()}')
        code = recognize(result.content)
        token = md5(password.encode()).hexdigest()
        info = (await self.post(
            'http://sso.ismartlearning.cn/v2/tickets-v2',
            data={
                'username': username,
                'password': md5(token.encode() + b'fa&s*l%$k!fq$k!ld@fjlk').hexdigest(),  # 啥时候炸了就写成动态获取的
                'captcha': code
            },
            headers={
                'X-Requested-With': 'XMLHttpRequest',
                'Origin': 'http://me.ismartlearning.cn',
                'Referer': 'http://me.ismartlearning.cn/'
            }
        )).json()
        logger.debug(info['result'])

        assert info['result']['code'] == -26  # 断言登录结果
        self.is_login = True
        return info['result']

    async def get_courses(self):  # 获取课程列表
        logger.info('正在获取课程列表...')
        courses = (await self.post(
            'https://school.ismartlearning.cn/client/course/list-of-student?status=1',
            data={
                'pager.currentPage': 1,
                'pager.pageSize': 32767
            }
        )).json()['data']
        return courses['list']

    async def get_books(self, course_id):  # 获取某课程的书籍列表
        logger.info('正在获取书籍列表...')
        await self.post(  # 必须有这个请求，否则后面会报错
            'http://school.ismartlearning.cn/client/course/list-of-student?status=1',
            data={
                'pager.currentPage': 1,
                'pager.pageSize': 32767
            }
        )
        books = (await self.post(
            'http://school.ismartlearning.cn/client/course/textbook/list-of-student',
            data={
                'courseId': course_id
            }
        )).json()['data']
        return books

    async def get_tasks(self, book_id, book_type, course_id):  # 获取某书籍的任务树
        logger.info('正在获取任务列表...')
        await self.post('http://school.ismartlearning.cn/client/course/textbook/chapters')
        tasks = (await self.post(
            'http://school.ismartlearning.cn/client/course/textbook/chapters',
            data={
                'bookId': book_id,
                'bookType': book_type,
                'courseId': course_id
            }
        )).json()['data']
        id_record = {task['id']: Tree(task) for task in tasks}
        book_name = (await self.book_info(book_id))['bookName']
        root = Tree({
            'book_id': tasks[0]['book_id'],
            'unitStudyPercent': 0,
            'name': book_name
        })
        for task_id in id_record:
            node = id_record[task_id]
            node_name = (f'{node.task["name"]} ' if 'name' in node.task else '') + f'[id:{node.task["id"]}]'
            if 'parent_id' in node.task:
                if (parent_id := node.task['parent_id']) in id_record:
                    id_record[parent_id].child.append(node)
                else:
                    logger.warning(f'父节点不存在：{node_name}')
            else:
                root.child.append(node)
        root.sort()
        return root

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
        )).json()
        logger.debug(f'paper_info: {json.dumps(paper_info, indent=4)}')
        return paper_info['data']

    async def user_info(self):
        logger.info('正在获取用户信息...')
        return (await self.post(
            'https://school.ismartlearning.cn/client/user/student-info')
        ).json()

    async def book_info(self, book_id):
        logger.info('正在获取书籍信息...')
        ticket = (await self.post(
            'http://sso.ismartlearning.cn/v1/serviceTicket',
            data={
                'service': 'http://book-api.ismartlearning.cn/client/v2/book/info'
            }
        )).json()['data']['serverTicket']
        logger.debug(f'Ticket: {ticket}')
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
        logger.debug(f'book_info: {json.dumps(book_info, indent=4)}')
        return book_info['data']
