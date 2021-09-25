"""
不同 question type 对应的解析方法
传入两个参数 ( question, answer, output ), 将输出行依次 append 到 output 队列中
"""

import re

from .formatter import fix


class Generators:
    @staticmethod
    def type_1(que, ans, output):  # 单选题
        # 提取题目内容
        question = que.select_one("question_text").text
        question = fix(question, ('rm_lgt', 'fix_uline', 'fix_space'))
        output.append(f'* **{question}**\n')
        # 提取答案
        ans_id = que.attrs['id']
        corrects = set(ans.select_one(f'[id="{ans_id}"] > answers').text)
        # 生成对应 Markdown
        options = que.select('options > *')
        for opt in options:
            opt_id = opt.attrs['id']
            answer_text = fix(opt.text, ('rm_lgt', 'fix_space'))
            if opt_id in corrects:  # 高亮正确答案
                output.append(f'<p><font color="#2ed573">&emsp;&emsp;<b>{opt_id}.</b> {answer_text}</font></p>\n')
            else:
                output.append(f'&emsp;&emsp;<b>{opt_id}.</b> {answer_text}\n')

    @staticmethod
    def type_2(*args):  # 多选题
        return Generators.type_1(*args)

    @staticmethod
    def type_3(que, ans, output):  # 判断题
        question = que.select_one("question_text").text
        question = fix(question, ('rm_lgt', 'fix_uline', 'fix_space'))
        output.append(f'* **{question}**\n')
        # 提取答案
        ans_id = que.attrs['id']
        correct = ans.select_one(f'[id="{ans_id}"] > answers').text
        # 生成对应 Markdown
        output.append(f'* 答案：「**{correct}**」\n')

    @staticmethod
    def type_4(que, ans, output):  # 填空题
        # 提取题目内容
        question = que.select_one('question_text').text
        question = re.sub('<br/?>', '\n', question)
        question = fix(question, ('rm_lgt', 'fix_uline', 'fix_space'))
        # 提取答案
        ans_id = que.attrs['id']
        corrects = ans.select(f'[id="{ans_id}"] answers > answer')
        # 执行替换
        for ans in corrects:
            question = question.replace(
                '{{' + ans.attrs['id'] + '}}',
                f' <font color="#2ed573"><b>[{ans.text}]</b></font> '
            )
        output.append(question + '\n')
    
    @staticmethod
    def type_6(que, ans, output):  # 连线题
        # 提取题目内容
        question = que.select_one('question_text').text
        question = fix(question, ('rm_lgt', 'fix_uline', 'fix_space'))
        output.append(f'* **{question}**\n')
        # 提取答案
        options = que.select('options > *')
        pairs = {}
        for opt in options:
            opt_id = opt.attrs['id']
            if opt_id not in pairs:
                pairs[opt_id] = [0, 0]
            flag = int(opt.attrs['flag'])
            pairs[opt_id][flag - 1] = opt.text
        output.append('| Part-A | Part-B |')
        output.append('| :- | :- |')
        for gp_id in pairs:
            left = fix(pairs[gp_id][0], ('fix_img', 'rm_lgt', 'fix_uline', 'fix_space')).replace('|', '\\|')
            right = fix(pairs[gp_id][1], ('fix_img', 'rm_lgt', 'fix_uline', 'fix_space')).replace('|', '\\|')
            output.append(f'| {left} | {right} |')
        output.append('')
    
    @staticmethod
    def type_8(que, ans, output):  # 匹配题
        # 提取题目内容
        question = que.select_one('question_text').text
        question = fix(question, ('rm_lgt', 'fix_uline'))
        # 提取答案
        ans_id = que.attrs['id']
        corrects = ans.select(f'[id="{ans_id}"] answers > answer')
        # 执行替换
        question = fix(question, ('fix_lf', 'rm_lgt', 'fix_space'))
        for ans in corrects:
            question = question.replace(
                '{{' + ans.attrs['id'] + '}}',
                f' <font color="#2ed573"><b>{ans.text}</b></font> '
            )
        output.append(question + '\n')

    @staticmethod
    def type_9(que, ans, output):  # 口语跟读
        output.append('「口语跟读」\n')
    
    @staticmethod
    def type_10(que, ans, output):  # 短文改错
        output.append('* **短文改错**')
        ans_id = que.attrs['id']
        corrects = ans.select(f'[id="{ans_id}"] answers > answer')
        for i, ans in enumerate(corrects):
            desc = re.sub('(?<=[A-Za-z0-9])(?=[\u4e00-\u9fa5])', ' ', ans.attrs['desc'])
            desc = re.sub('(?<=[\u4e00-\u9fa5])(?=[A-Za-z0-9])', ' ', desc)
            output.append(f'{i + 1}. {desc}\n')
        output.append('')

    @staticmethod
    def type_11(que, ans, output):  # 选词填空
        # 提取题目内容
        question = que.select_one('question_text').text
        question = fix(question, ('fix_uline', 'fix_lf', 'rm_lgt', 'fix_space'))
        options = {opt.attrs['id']: opt.text for opt in que.select('options > option[flag="2"]')}
        # 提取答案
        ans_id = que.attrs['id']
        corrects = ans.select(f'[id="{ans_id}"] answers > answer')
        # 执行替换
        for ans in corrects:
            question = question.replace(
                '{{' + ans.attrs['id'] + '}}',
                f' <font color="#2ed573"><b>{options[ans.text]}</b></font> '
            )
        output.append(question + '\n')
