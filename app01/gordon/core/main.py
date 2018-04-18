#!/usr/bin/env python
# -*- coding:utf-8 -*-
#Author:Jeff Lee
from core.client import ClientHandle

class command_handler(object):

    def __init__(self,args):
        self.sys_args =args
        if len(self.sys_args)<2:
            exit(self.help_msg)

        self.command_allowcator()


    def help_msg(self):
        valid_commands ='''
        start   start monitor client
        stop    stop monitor client
        '''
        exit(valid_commands)

    def command_allowcator(self):
        '''分析用户输入的不同命令'''

        print(self.sys_args[1])

        if hasattr(self,self.sys_args[1]):
            func = getattr(self,self.sys_args[1])
            return  func()
        else:
            print("命令不存在")
            self.help_msg()

    def start(self):
        print('开始启动客户端')

        client =ClientHandle()
        client.forever_run()

    def stop(self):
        print('停止客户端')
