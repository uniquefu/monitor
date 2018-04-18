#!/usr/bin/env python
# -*- coding:utf-8 -*-
#Author:Jeff Lee

configs ={
    "HostID":2,
    "Server":"169.0.199.17",
    "ServerPort":8000,
    "urls":{
        "get_configs":['monitor/api/client/config','get'],
        "service_report":['monitor/api/client/service/report/','post']
    },
    "RequsetTimeout":30,
    "ConfigUpdateInterval":300,

}