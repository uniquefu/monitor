#!/usr/bin/env python
# -*- coding:utf-8 -*-
#Author:Jeff Lee
import time,json,operator,pickle
from Monitor import  settings
from  app01.backends import redis_conn
from app01 import  models
import  redis

class DataHandler(object):
    def __init__(self,django_settings,connect_redis =True):
        self.django_settings = django_settings
        self.poll_interval =0.5
        self.config_update_interval =120
        self.config_last_loading_time = time.time()
        self.global_monitor_dic ={}
        self.exit_flag = False
        if connect_redis:
            self.redis = redis_conn.redis_conn(django_settings=settings)

    def looping(self):

        self.update_or_load_configs()
        count =0
        while not self.exit_flag:
            print("looping %s".center(50,'-') %count)
            count +=1

            if time.time() - self.config_last_loading_time >= self.config_update_interval:
                print("\033[41;1mneed update configs ...\033[0m")
                self.update_or_load_configs()
                print("monitor dic",self.global_monitor_dic)
            if self.global_monitor_dic:
                for h,config_dic in self.global_monitor_dic.items():
                    print('handling host:\033[32;1m%s\033[0m' %h)
                    for service_id,val in config_dic['services'].items(): #循环所有要监控的服务
                        #print(service_id,val)
                        service_obj,last_monitor_time = val
                        if time.time() - last_monitor_time >= service_obj.interval: #reached the next monitor interval
                            print("\033[33;1mserivce [%s] has reached the monitor interval...\033[0m" % service_obj.name)
                            self.global_monitor_dic[h]['services'][service_obj.id][1] = time.time()
                            #self.load_service_data_and_calulating(h,service_obj)
                            #only do basic data validataion here, alert if the client didn't report data to server in \
                            #the configured time interval
                            self.data_point_validation(h,service_obj) #检测此服务最近的汇报数据
                        else:
                            next_monitor_time = time.time() - last_monitor_time - service_obj.interval
                            print("service [%s] next monitor time is %s" % (service_obj.name,next_monitor_time))

                    if time.time() - self.global_monitor_dic[h]['status_last_check'] >10:
                        #检测 有没有这个机器的trigger,如果没有,把机器状态改成ok
                        trigger_redis_key = "host_%s_trigger*" % (h.id)
                        trigger_keys = self.redis.keys(trigger_redis_key)
                        #print('len grigger keys....',trigger_keys)
                        if len(trigger_keys) ==0: #没有trigger被触发,可以把状态改为ok了
                            h.status = 1
                            h.save()
                    #looping triggers 这里是真正根据用户的配置来监控了
                    #for trigger_id,trigger_obj in config_dic['triggers'].items():
                    #    #print("triggers expressions:",trigger_obj.triggerexpression_set.select_related())
                    #    self.load_service_data_and_calulating(h,trigger_obj)

            time.sleep(self.poll_interval)

    def update_or_load_configs(self):
        '''

        :return:
        '''
        all_enabled_host = models.Host.objects.all()
        for h in all_enabled_host:
            if h not in self.global_monitor_dic:
                self.global_monitor_dic[h] = {
                    "services":{},
                    'trigger':{},
                }

            service_list = []
            trigger_list = []
            for group in h.host_groups.select_related():
                # print("grouptemplates:", group.templates.select_related())

                for template in group.templates.select_related():
                    # print("tempalte:",template.services.select_related())
                    # print("triigers:",template.triggers.select_related())
                    service_list.extend(template.services.select_related())
                    trigger_list.extend(template.triggers.select_related())
                for service in service_list:
                    if service.id not in self.global_monitor_dic[h]['services']:  # first loop
                        self.global_monitor_dic[h]['services'][service.id] = [service, 0]
                    else:
                        self.global_monitor_dic[h]['services'][service.id][0] = service
                for trigger in trigger_list:
                    # if not self.global_monitor_dic['triggers'][trigger.id]:
                    self.global_monitor_dic[h]['trigger'][trigger.id] = trigger

            # print(h.templates.select_related() )
            # print('service list:',service_list)

            for template in h.templates.select_related():
                service_list.extend(template.services.select_related())
                trigger_list.extend(template.triggers.select_related())
            for service in service_list:
                if service.id not in self.global_monitor_dic[h]['services']:  # first loop
                    self.global_monitor_dic[h]['services'][service.id] = [service, 0]
                else:
                    self.global_monitor_dic[h]['services'][service.id][0] = service
            for trigger in trigger_list:
                print('###',trigger.id)
                self.global_monitor_dic[h]['trigger'][trigger.id] = trigger
            print(self.global_monitor_dic[h])
            # 通过这个时间来确定是否需要更新主机状态
            self.global_monitor_dic[h].setdefault('status_last_check', time.time())

        self.config_last_loading_time = time.time()
        print('更新主机状态',self.global_monitor_dic)
        return True

    def data_point_validation(self, host_obj, service_obj):
        '''

        :param host_obj:
        :param service_obj:
        :return:
        '''
        service_redis_key = "Status_%s_%s_latest" % (host_obj.id, service_obj.name)  # 拼出此服务在redis中存储的对应key
        latest_data_point = self.redis.lrange(service_redis_key, -1, -1)
        if latest_data_point:
            latest_data_point = json.loads(latest_data_point[0].decode())
            latest_service_data, last_report_time = latest_data_point
            monitor_interval = service_obj.interval + self.django_settings.REPORT_LATE_TOLERANCE_TIME
            if time.time() - last_report_time > monitor_interval:#超过监控间隔但数据还没汇报过来,something wrong with cli
                no_data_secs = time.time() - last_report_time
                msg = '''Some thing must be wrong with client [%s],because haven't receive data of service [%s] \
    			for [%s]s (interval is [%s])''' % (host_obj.ip_addr, service_obj.name, no_data_secs, monitor_interval)

                self.trigger_notifier(host_obj=host_obj, trigger_id=None, positive_expression=None, msg=msg)

                if service_obj.name == 'uptime':
                    host_obj.status = 3
                    host_obj.save()

                else:
                    host_obj.status = 5
                    host_obj.save()

        else:  # no data at all
            print("\033[41;1m no data for serivce [%s] host[%s] at all..\033[0m" % (service_obj.name, host_obj.name))
            msg = '''no data for serivce [%s] host[%s] at all..''' % (service_obj.name, host_obj.name)
            self.trigger_notifier(host_obj=host_obj, trigger_id=None, positive_expression=None, msg=msg)
            host_obj.status = 5  # problem
            host_obj.save()

    def load_service_data_and_calulating(self,host_obj,trigger_obj,redis_obj):
        '''

        :param host_obj:
        :param trigger_obj:
        :param redis_obj:
        :return:
        '''
        self.redis =redis_obj
        calc_sub_res_list = [] #先把每个expression的结果算出来，放在列表里
        positive_expression =[]
        expression_res_string =''

        for expression in trigger_obj.triggerexpression_set.select_related().order_by('id'):
            print(expression,expression.logic_type)
            expression_process_obj = ExpressionProcess(self,host_obj,expression)
            single_expression_res = expression_process_obj.process()

            if single_expression_res:
                calc_sub_res_list.append(single_expression_res)
                if single_expression_res['expression_obj'].logic_type:
                    expression_res_string +=str(single_expression_res['calc_res'] )+' ' + \
                                                single_expression_res['expression_obj'].logic_type + ' '

                else:
                    expression_res_string += str(single_expression_res['calc_res'] )+' '

                #把所有结果为True的expression提取，报警时就可以知道谁的问题导致trigger
                if single_expression_res['calc_res'] ==True:
                    single_expression_res['expression_obj'] =single_expression_res['expression_obj'].id
                    # 要存到redis里,数据库对象转成id
                    positive_expression.append(single_expression_res)

        print("whole trigger res",trigger_obj.name,expression_res_string)

        if expression_res_string:
            trigger_res =eval(expression_res_string)

            if trigger_res: #触发报警
                print('####trigger alert',trigger_obj.severity,trigger_res)
                self.trigger_notifier(host_obj,trigger_obj.id,positive_expression,msg =trigger_obj.name)


    def trigger_notifier(self,host_obj,trigger_id,positive_expression,redis_obj=None,msg=None):
        '''

        :param self:
        :param host_obj:
        :param trigger_id:
        :param positive_expression:
        :param redis_obj:
        :return:
        '''
        if redis_obj:#从外部调用时才用的到，为了避免重复调用redis连接
            self.redis =redis_obj
        print("告警参数",host_obj,trigger_id,positive_expression)

        msg_dict ={
            'host_id':host_obj.id,
            'trigger_id':trigger_id,
            'positive_expression':positive_expression,
            'msg': msg,
            'time':time.strftime('%Y-%m-%d %H:%M:%S',time.localtime()),
            'start_time':time.time(),
            'duration':None
        }

        self.redis.publish(self.django_settings.TRIGGER_CHAN,pickle.dumps(msg_dict))

        #先把之前的trigger加载回来，获取上次报警的时间，以统计故障持续时间
        trigger_redis_key ='host_%s_trigger_%s' %(host_obj.id,trigger_id)
        old_trigger_data = self.redis.get(trigger_redis_key)
        if old_trigger_data:
            old_trigger_data = old_trigger_data.decode()
            trigger_starttime =json.loads(old_trigger_data)['start_time']
            msg_dict['start_time']=trigger_starttime
            msg_dict['duration'] =round(time.time()-trigger_starttime)

        # 同时在redis记录这个trigger，前端展示页面时统计trigger个数
        self.redis.set(trigger_redis_key,json.dumps(msg_dict),300)#一个trigger记录5分钟后自动清除

class ExpressionProcess(object):

    def __init__(self,main_ins,host_obj,expression_obj,specified_item =None):
        '''
        :param main_ins DataHandler 实例:
        :param host_obj:
        :param expression_obj:
        :param specified_item:
        计算单条表达式的结果
        '''
        self.host_obj =host_obj
        self.expression_obj=expression_obj
        self.main_ins=main_ins
        self.service_redis_key = "Status_%s_%s_latest" %(host_obj.id,expression_obj.service.name)

        #从redis中获取多长时间的数据，单位为分钟
        self.time_range =self.expression_obj.data_cal_args.split(',')[0]

    def load_data_from_redis(self):
        time_in_sec =int(self.time_range) *60
        #多取一分钟数据
        approximate_data_points =(time_in_sec+60)//self.expression_obj.service.interval #获取大概要取的值

        print('获取多少数据及间隔')
        try:
            data_range_raw = self.main_ins.redis.lrange(self.service_redis_key, -approximate_data_points,-1)

        except redis.exceptions.ResponseError as e:
            data_range_raw = self.main_ins.redis.lrange(self.service_redis_key, 0, -1)

        print('获取数据',data_range_raw)
        approximate_data_range =[json.loads(i.decode()) for i in data_range_raw]

        data_range =[] #精确的需要的数据列表

        for point in approximate_data_range:
            val,saving_time = point

            if time.time() - saving_time < time_in_sec: #代表数据有效
                data_range.append(point)

        print('有效数据',data_range)
        return data_range


    def process(self):
        #按照用户的配置把数据从reids获取
        data = self.load_data_from_redis()
        data_calc_func = getattr(self,'get_%s' %self.expression_obj.data_calc_func)

        single_expression_cal_res =data_calc_func(data) #[True,43,None]

        if single_expression_cal_res: #确保上面的条件，有正确的返回
            res_dic ={
                'cal_res': single_expression_cal_res[0],
                'cal_res_val': single_expression_cal_res[1],
                'expression_obj': self.expression_obj,
                'service_item': single_expression_cal_res[2],
            }

            return res_dic
        else:
            return  False

    def judge(self,calculated_val):
        '''

        :param calculated_val:
        :return:
        '''
        calc_func =getattr(operator,self.expression_obj.operator_type)

        return calc_func(calculated_val,self.expression_obj.threshold)

    def get_hit(self, data_set):
        '''
        return hit times  value of given data set
        :param data_set:
        :return:
        '''
        pass

    def get_avg(self,data_set):
        """

        :param data_set:
        :return:
        """
        clean_data_list =[] #非网卡数据
        clean_data_dic ={} #网卡数据

        for point in data_set:
            val,saving_time =point

            if val:
                if 'data' not in val:#没有dict
                    clean_data_list.append(val[self.expression_obj.service_index.key])

                else: #has sub dict
                    for k,v in val['data'].items():
                        if k not in clean_data_dic:
                            clean_data_dic[k]=[]

                        clean_data_dic[k].append(self.expression_obj.service_index.key)

        if clean_data_list:
            clean_data_list =[float(i) for i in clean_data_list]

            avg_res = sum(clean_data_list)/len(clean_data_list)

            print("\033[46;1m----avg res:%s\033[0m" % avg_res)
            return [self.judge(avg_res),avg_res,None]

        elif clean_data_dic:
            for k,v in clean_data_dic.items():
                clean_v_list = [float(i) for i in v]

                if sum(clean_v_list) ==0:
                    avg_res = 0
                else:
                    sum(clean_v_list)/len(clean_v_list)

                if self.expression_obj.specified_index_key:#监控了特定的指标,比如有多个网卡,但这里只特定监控eth0
                    if k ==self.expression_obj.specified_index_key:#就是监控这个特定指标,match上了
                        #在这里判断是否超阀值
                        print('test res [%s] [%s] [%s]' %(avg_res,
                                                          self.expression_obj.operator_type,
                                                          self.expression_obj.threshold,
                                                          self.judge(avg_res)
                                                          ))
                        calc_res = self.judge(avg_res)
                        if calc_res:
                            return [calc_res,avg_res,k]

                    else:#监控这个服务的所有项，比如一台机器的多个网卡, 任意一个超过了阈值,都 算是有问题的
                        calc_res = self.judge(avg_res)
                        if calc_res:
                            return [calc_res, avg_res, k]

                    print('specified monitor key:', self.expression_obj.specified_index_key)
                    print('clean data dic:', k, len(clean_v_list), clean_v_list)
                else:  # 能走到这一步,代表 上面的循环判段都未成立
                    return [False, avg_res, k]
            else:  # 可能是由于最近这个服务 没有数据 汇报 过来,取到的数据 为空,所以没办法 判断阈值
                return [False, None, None]










