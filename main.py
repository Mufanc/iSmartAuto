import asyncio
from argparse import ArgumentParser


async def main():
    parser = ArgumentParser('main.py')
    parser.add_argument('-v', dest='LEVEL', default='warning', help='日志过滤等级，默认为 warning')
    subparsers = parser.add_subparsers(help='模式选择')

    method_list = subparsers.add_parser('list', help='列出所有课程和书籍')

    method_flash = subparsers.add_parser('flash', help='对选定的一个或几个课程执行刷课')
    target = method_flash.add_mutually_exclusive_group()
    target.add_argument('-b', '--book', action='store_true', help='对当前打开的书籍执行刷课')
    target.add_argument('-c', '--course', action='store_true', help='对当前打开的课程执行刷课')
    target.add_argument('-a', '--all', action='store_true', help='对所有课程和书籍执行刷课')
    method_flash.add_argument('-f', '--filter', help='')
    method_flash.add_argument('-i', '--invert', help='过滤器反向')

    parser.parse_args()

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()

