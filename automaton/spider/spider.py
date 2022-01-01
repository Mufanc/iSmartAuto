import sys
import json
import httpx
from hashlib import md5
from loguru import logger
from .captcha import recognize


class Tree:  # 任务树
    def __init__(self, task):
        self.task = task
        self.child = []

    def sort(self):
        try:
            self.child.sort(
                key=lambda node: node.task['displayOrder']
            )
            for ch in self.child:
                ch.sort()
        except Exception:
            exceptionInformation = sys.exc_info()
            logger.warning(f'[构建任务树] | 排序出错：{exceptionInformation}')


class Spider(httpx.AsyncClient):
    def __init__(self):
        super().__init__()
        self.is_login = False

    async def login(self, username, password):
        try:
            if self.is_login:
                return {}

            self.cookies.clear()  # 重置 cookies
            logger.info('[登录] | 正在获取验证码...')
            result = await self.get('http://sso.ismartlearning.cn/captcha.html')
            code = recognize(result.content)
            password = md5(md5(password.encode()).hexdigest().encode() + b'fa&s*l%$k!fq$k!ld@fjlk').hexdigest()
            logger.info('[登录] | 正在登录...')
            info = (await self.post(
                'http://sso.ismartlearning.cn/v2/tickets-v2',
                data={
                    'username': username,
                    'password': password,
                    'captcha': code
                },
                headers={
                    'X-Requested-With': 'XMLHttpRequest',
                    'Origin': 'http://me.ismartlearning.cn',
                    'Referer': 'http://me.ismartlearning.cn/'
                }
            )).json()['result']
            logger.debug(f"[登录] | {info}")
            assert info['code'] == -26  # 断言登录结果
            self.is_login = True
            logger.success('[登录] | 登录成功')
            return info
        except Exception:
            exceptionInformation = sys.exc_info()
            logger.warning(f'[登录] | 登录出错：{exceptionInformation}')

    async def get_courses(self):  # 获取课程列表
        try:
            logger.info('[获取课程列表] | 正在获取课程列表...')
            courses = (await self.post(
                'https://school.ismartlearning.cn/client/course/list-of-student?status=1',
                data={
                    'pager.currentPage': 1,
                    'pager.pageSize': 100
                }
            )).json()['data']['list']
            logger.debug(f"[获取课程列表] | {courses}")
            logger.success('[获取课程列表] | 获取课程列表成功')
            return courses
        except Exception:
            exceptionInformation = sys.exc_info()
            logger.warning(f'[获取课程列表] | 获取课程列表出错：{exceptionInformation}')

    async def get_books(self, course_id):  # 获取某课程的书籍列表
        try:
            await self.post(  # 必须有这个请求，否则后面会报错
                'http://school.ismartlearning.cn/client/course/list-of-student?status=1',
                data={
                    'pager.currentPage': 1,
                    'pager.pageSize': 100
                }
            )
            books = (await self.post(
                'http://school.ismartlearning.cn/client/course/textbook/list-of-student',
                data={
                    'courseId': course_id
                }
            )).json()['data']
            return books
        except Exception:
            exceptionInformation = sys.exc_info()
            logger.warning(f'[获取书籍列表] | 获取书籍列表出错：{exceptionInformation}')

    async def get_tasks(self, book_id, book_type, course_id):  # 获取某书籍的任务树
        try:
            logger.info('[获取任务列表] | 正在获取任务列表...')
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
            logger.info('[构建任务树] | 正在构建任务树...')
            for task_id in id_record:
                node = id_record[task_id]
                node_name = f'{node.task.get("name","")}[id:{node.task["id"]}]'
                if 'parent_id' in node.task:
                    if node.task['parent_id'] in id_record:
                        id_record[node.task['parent_id']].child.append(node)
                    else:
                        logger.warning(f'[构建任务树] | {node_name} 父节点不存在')
                else:
                    root.child.append(node)
            root.sort()
            logger.success('[构建任务树] | 构建任务树完成')
            logger.success('[获取任务列表] | 获取任务列表完成')
            return root
        except Exception:
            exceptionInformation = sys.exc_info()
            logger.warning(f'[获取任务列表] | 获取任务列表出错：{exceptionInformation}')

    async def get_paper(self, paper_id):  # 获取任务点信息（包括题目和答案）
        try:
            logger.info('[获取任务点] | 正在获取任务点信息...')
            ticket = (await self.post(
                'http://sso.ismartlearning.cn/v1/serviceTicket',
                data={
                    'service': 'http://xot-api.ismartlearning.cn/client/textbook/paperinfo'
                }
            )).json()['data']['serverTicket']
            logger.debug(f'[获取任务点] | {ticket}')
            paper_info = (await self.post(
                'http://xot-api.ismartlearning.cn/client/textbook/paperinfo',
                params={
                    'ticket': ticket
                },
                data={
                    'paperId': paper_id
                },
                headers={
                    'Origin': 'http://me.ismartlearning.cn',
                    'Referer': 'http://me.ismartlearning.cn/',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept-Encoding': 'gzip, deflate'
                }
            )).json()['data']
            # logger.debug(f'[获取任务点] | {json.dumps(paper_info, indent=4)}')
            logger.success('[获取任务点] | 获取任务点信息完成')
            return paper_info
        except Exception:
            exceptionInformation = sys.exc_info()
            logger.warning(f'[获取任务点] | 获取任务点出错：{exceptionInformation}')

    async def user_info(self):
        try:
            logger.info('[获取用户信息] | 正在获取用户信息...')
            info = (await self.post('https://school.ismartlearning.cn/client/user/student-info')).json()
            logger.success('[获取用户信息] | 获取用户信息完成')
            return info
        except Exception:
            exceptionInformation = sys.exc_info()
            logger.warning(f'[获取用户信息] | 获取用户信息出错：{exceptionInformation}')

    async def book_info(self, book_id):
        try:
            logger.info('[获取书籍信息] | 正在获取书籍信息...')
            ticket = (await self.post(
                'http://sso.ismartlearning.cn/v1/serviceTicket',
                data={
                    'service': 'http://book-api.ismartlearning.cn/client/v2/book/info'
                }
            )).json()['data']['serverTicket']
            logger.debug(f'[获取书籍信息] | {ticket}')
            book_info = (await self.post(
                'http://book-api.ismartlearning.cn/client/v2/book/info',
                params={
                    'ticket': ticket
                },
                data={
                    'bookId': book_id,
                    'bookType': 0
                },
                headers={
                    'Origin': 'http://me.ismartlearning.cn',
                    'Referer': 'http://me.ismartlearning.cn/',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept-Encoding': 'gzip, deflate'
                }
            )).json()['data']
            logger.debug(f'[获取书籍信息] |  {json.dumps(book_info, indent=4)}')
            logger.success('[获取书籍信息] | 获取书籍信息完成')
            return book_info
        except Exception:
            exceptionInformation = sys.exc_info()
            logger.warning(f'[获取书籍信息] | 获取书籍信息出错：{exceptionInformation}')
