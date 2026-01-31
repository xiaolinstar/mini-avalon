# -*- coding: utf-8 -*-
import logging


# *************************************************
# @Time         : 2026/1/31 14:05
# @Author       : xingxiaolin
# @Site         : 
# @File         : exce.py
# @Software:    : PyCharm
# Description   : Some descriptions about the file.
# *************************************************

class AppException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


try:
    1 / 0
except ZeroDivisionError as e:
    e.add_note("除数不能为0")
    logging.exception("除法发生错误")

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, AppException):
        logging.error(exc_value)
    else:
        logging.error("未处理异常", exc_info=(exc_type, exc_value, exc_traceback))
try:
    int("abc")
except ValueError as e1:
    raise RuntimeError("处理失败")  # ← e1自动存入__context__

print("进程结束")