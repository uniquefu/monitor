#!/usr/bin/env python
# -*- coding:utf-8 -*-
#Author:Jeff Lee
import  subprocess

def monitor(frist_invoke=1):
    shell_command ='cat /proc/cpuinfo'
    result =subprocess.Popen(shell_command,shell=True,stdout=subprocess.PIPE).stdout.readlines()

    print(result)
    value_dic ={'status':0,'data':{}}

    for line in result:
        line =line.split()
        nic_name,t_in,t_out =line[1].decode(),line[4].decode(),line[5].decode()
        value_dic['data'][nic_name]={'t_in':line[4],'t_out':line[5]}

    return value_dic