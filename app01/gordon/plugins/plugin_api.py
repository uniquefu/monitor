#!/usr/bin/env python
# -*- coding:utf-8 -*-
#Author:Jeff Lee

from plugins.linuxs import sysinfo,cpu_mac,memory,network,host_alive

def GetLinuxCpuStatus():
    return cpu_mac.monitor()

def GetLinuxMemoryStatus():
    return memory.monitor()

def GetLinuxNetworkStatus():
    return network.monitor()