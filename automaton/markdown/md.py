import json
from collections import deque

from bs4 import BeautifulSoup
from loguru import logger

from .formatter import fix
from .generator import Generators

_output = deque()


# 解码题目与答案 xml
def decode(que, ans, qt_type):
    getattr(Generators, f'type_{qt_type}')(que, ans, _output)


# 生成每个 paper 的答案
def unescape(node, book_id):
    paper_id = node.task['paperId']
    with open(f'.cache/books/{book_id}/{paper_id}.json', 'r') as fp:
        task = json.load(fp)
    paper = BeautifulSoup(task['paperData'], 'lxml-xml')
    answer = BeautifulSoup(task['answerData'], 'lxml-xml')
    questions = paper.select('element[knowledge]:has(> question_type)')
    if questions:
        for que in questions:
            qt_type = int(que.select_one('question_type').text)
            decode(que, answer, qt_type)
        return True
    return False


# 深搜创建目录树
def dfs(node, book_id, depth=2):
    if title := node.task['name']:
        logger.info(f'{".    " * (depth - 1)}{title}')
        title = fix(title, ('rm_head',))
        _output.append(f'{"#" * depth} {title}\n')
    flag = False
    if 'paperId' in node.task:
        flag = unescape(node, book_id)
    for ch in node.children:
        if dfs(ch, book_id, depth + 1):
            flag = True
    if not flag:
        _output.pop()
    return flag


def generate_md(root):  # 生成答案
    book_id = root.task['book_id']
    for ch in root.children:
        dfs(ch, book_id)
    with open('.cache/answer.md', 'w', encoding='utf-8') as file:
        while len(_output):
            line = _output.popleft()
            file.write(line + '\n')
    logger.info('Done.')
