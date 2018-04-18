#!/usr/bin/env python
# -*- coding:utf-8 -*-
#Author:Jeff Lee
import  os,sys


if __name__ =="__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(base_dir)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE','Monitor.settings')

    from app01.backends.management import execute_from_command_line

    execute_from_command_line(sys.argv)