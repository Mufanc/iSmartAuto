from random import uniform, randint

from bs4 import BeautifulSoup
from loguru import logger

from configs import configs
from .devtools import Browser
from .spider import Spider

PLACEHOLDER = '.   '
_paper_config = configs['paper']


async def list_books(detail):
    async with Spider() as spider:
        await spider.login(**configs['user'])
        courses = await spider.get_courses()

        for cr in courses:
            if detail:
                hint = f'{cr["courseName"]} ({cr["teacherName"]})'
            else:
                hint = cr['courseName']
            print(hint)

            books = await spider.get_books(cr["courseId"])
            for book in books:
                if detail:
                    hint = f'> [{cr["courseId"]}#{book["bookId"]}] {book["bookName"]} ({book["percent"]}%)'
                else:
                    hint = f'> {book["bookName"]}'
                print(PLACEHOLDER + hint)


async def _random(spider, paper_id):  # 随机的分数和学习时长
    paper = BeautifulSoup((await spider.get_paper(paper_id))['paperData'], 'lxml-xml')
    questions = paper.select('element[knowledge]:has(> question_type)')
    if not questions:
        return 100, 5

    total = 0
    score, time = 0, 0
    for q in questions:
        q_type = int(q.select_one('question_type').text)
        q_score = float(q.select_one('question_score').text)
        total += q_score

        ranges = _paper_config['random-score']
        if q_type <= len(ranges) and (r := ranges[q_type-1]) is not None:
            if not isinstance(ranges[q_type-1], list):
                r = [r, r]
            score += q_score * uniform(*r)
        else:
            q_no = q.select_one('question_no').text
            logger.warning(f'T{q_no}：未知的题型！')
            if (r := _paper_config['defaults']) == 'pause':
                score += float(input('请手动输入该题得分 [0-1]：'))
            else:  # defaults
                score += q_score * uniform(*r)

        time += randint(*_paper_config['random-time'])

    return int(100 * score / total), time


async def _flash(course_id, book_id, spider):
    async def dfs(node, depth=0):
        task = node.task
        print(PLACEHOLDER * depth + task['name'])
        if _paper_config['skip-finished'] and task['unitStudyPercent'] == 100:
            print(PLACEHOLDER * depth + '# Skipped')
            return
        if 'paperId' in task:  # 如果有任务则提交
            chapter_id = task['chapterId']
            task_id = task['id']
            score, time = await _random(spider, task['paperId'])
            result = await page.submit(book_id, chapter_id, task_id, score, time, 100, user_id)
            if result['wasThrown'] or not result['result']['value']:
                logger.warning(f'任务 {task["name"]} 可能提交失败，请留意最终结果！')
        for ch in node.child:
            await dfs(ch, depth + 1)

    browser = await Browser.connect()
    page = await browser.wait_for_page(r'https?://pc\.ismartin\.com.*')

    # With Spider
    await spider.login(**configs['user'])
    user_id = (await spider.user_info())['data']['uid']

    book_type = (await spider.book_info(book_id))['bookType']
    root = await spider.get_tasks(book_id, book_type, course_id)
    await dfs(root)


async def flash_by_id(identity):
    async with Spider() as spider:
        await _flash(*identity.split('#'), spider)


async def flash_current():  # 对当前课程或书籍执行刷课
    browser = await Browser.connect()
    course_id, book_id = await browser.get_current()
    async with Spider() as spider:
        if book_id:
            await _flash(course_id, book_id, spider)
        else:
            await spider.login(**configs['user'])
            books = await spider.get_books(course_id)
            for book in books:
                await _flash(course_id, book['bookId'], spider)


async def flash_all():
    async with Spider() as spider:
        await spider.login(**configs['user'])
        courses = await spider.get_courses()
        for course in courses:
            course_id = course['courseId']
            books = await spider.get_books(course_id)
            for book in books:
                await _flash(course_id, book['bookId'], spider)
