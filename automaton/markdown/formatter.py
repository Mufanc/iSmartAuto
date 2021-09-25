import re


class Formatter:
    @staticmethod
    def fix_img(text):  # 处理 <img/> 标签
        return re.sub('<img.+?>', '「暂不支持图片显示澳」', text)

    @staticmethod
    def rm_lgt(text):  # 处理括号对
        return re.sub('<.+?>', '', text)

    @staticmethod
    def fix_uline(text):  # 处理下划线
        return re.sub('_{3,}', lambda mch: '\\_' * len(mch.group()), text)

    @staticmethod
    def rm_head(text):  # 处理数字标号
        return re.sub(r'^(?:\d+(?:\.| +\b))+\d+ ', '', text)

    @staticmethod
    def fix_lf(text):  # 处理换行
        text = re.sub('<br/?>', '\n\n', text)
        return re.sub('<p>(.+?)</p>', lambda mch: mch.group(1) + '\n\n', text)

    @staticmethod
    def fix_space(text):
        return re.sub('(?:&nbsp;)+', ' ', text)


def fix(text, func_ptrs):
    for func in func_ptrs:
        text = getattr(Formatter, func)(text)
    return text
