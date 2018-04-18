#!/usr/bin/env python
# -*- coding:utf-8 -*-
#Author:Jeff Lee
import json, time
from conf import settings
import requests,threading
from plugins import plugin_api


class ClientHandle(object):
    def __init__(self):
        self.moniroted_services = {}

    def load_latest_configs(self):
        '''
        加载从服务器下发的最新配置
        return:
        '''
        request_type = settings.configs['urls']['get_configs'][1]
        url = "%s/%s" % (settings.configs['urls']['get_configs'][0], settings.configs['HostID'])
        latest_configs = self.url_request(request_type, url)
        latest_configs = json.loads(latest_configs)
        self.moniroted_services.update(latest_configs)

    def forever_run(self):
        '''
        '''
        exit_flag = False

        self.load_latest_configs()
        print('\033[31;1m第一次加载最新配置\033[0m')
        config_last_update_time = time.time()

        while not exit_flag:
            if time.time() - config_last_update_time > settings.configs['ConfigUpdateInterval']:
                self.load_latest_configs()
                print('\033[31;1m[%s]s 加载最新配置\033[0m' % self.moniroted_services)
                config_last_update_time = time.time()

            for service_name,val in self.moniroted_services['services'].items():
                if len(val) ==2:
                    self.moniroted_services['services'][service_name].append(0)
                monitor_interval =val[1]
                last_invoke_time =val[2]

                if time.time()-last_invoke_time >monitor_interval:
                    #print(last_invoke_time,time.time())
                    self.moniroted_services['services'][service_name][2]=time.time()

                    t =threading.Thread(target=self.invoke_plugin,args=(service_name,val))
                    t.start()
                    print("开始监控[%s]" %service_name)
                else:
                    print("\033[31;Going to monitor [%s] in [%s] secs\033[0m" % (service_name,
                                    monitor_interval - (time.time() - last_invoke_time)))

            time.sleep(1)

    def invoke_plugin(self,service_name,val):

        plugin_name =val[0]
        #print(plugin_name)
        if hasattr(plugin_api,plugin_name):
            func =getattr(plugin_api,plugin_name)
            plugin_callback =func()

            report_data ={
                'client_id':settings.configs['HostID'],
                'service_name':service_name,
                'data':json.dumps(plugin_callback)#返回byte

            }
            print('\033[31;1m#######把数据发给服务器########\033[0m',report_data)

            request_type = settings.configs['urls']['service_report'][1]
            request_url = settings.configs['urls']['service_report'][0]

            self.url_request(request_type, request_url,params = report_data)
            print('\033[33;1m#######服务器接收成功########\033[0m')

        else:
            print("\033[31;1mCannot find service [%s]'s plugin name [%s] in plugin_api\033[0m" % (
            service_name, plugin_name))




    def url_request(self,request_type, url,**kwargs):
        abs_url ="http://%s:%s/%s" %(settings.configs['Server'],
                                     settings.configs['ServerPort'],
                                     url)
        if request_type in ("get",'GET'):
            #url ="http://127.0.0.1:8000/" +url
            print(abs_url)
            try:
                response = requests.get(abs_url)
                print('\033[31;1m加载最新配置完成\033[0m')
                return  response.text
            except:
                print("请求超时")
        else: #post
            data = kwargs['params']
            print("#########",data)
            response = requests.post(abs_url, data)

            return response.text
