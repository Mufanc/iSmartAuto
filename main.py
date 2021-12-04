import asyncio
import sys
from argparse import ArgumentParser

from loguru import logger

from automaton import utils


async def main():
    parser = ArgumentParser('main.py')

    parser.add_argument('-v', dest='level', action='count', help='日志过滤等级，依次为 warning, info, debug')
    subparsers = parser.add_subparsers(dest='method', help='模式选择')

    method_list = subparsers.add_parser('list', help='列出所有课程和书籍')
    method_list.add_argument('-d', '--detail', action='store_true', help='显示详细信息')

    method_flash = subparsers.add_parser('flash', help='对选定的一个或几个课程执行刷课')
    target = method_flash.add_mutually_exclusive_group()
    target.add_argument('-i', '--id', help='直接指定书籍 id')
    target.add_argument('-c', '--current', action='store_true', help='限定当前课程或书籍')
    target.add_argument('-a', '--all', action='store_true', help='选择全部')
    method_flash.add_argument('-f', '--filter', help='任务过滤器，设置后只刷匹配的任务（尚未实现）')  # Todo: 实现这个

    args = parser.parse_args()

    logger.remove()
    logger.add(sys.stdout, level=['WARNING', 'INFO', 'DEBUG'][args.level or 0])

    if args.method == 'list':
        await utils.list_books(detail=args.detail)
    elif args.method == 'flash':
        if args.id:
            await utils.flash_by_id(args.id)
        elif args.current:
            await utils.flash_current()
        elif args.all:
            await utils.flash_all()
    else:
        parser.print_help()

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()

