#!/usr/bin/env python
# -*- coding:utf-8 -*-
#Author:Jeff Lee
from  app01.backends import  redis_conn
import pickle,time
from app01 import  models
from django.core.mail import send_mail
from  Monitor import  settings


class TriggerHandler(object):

    def __init__(self,django_settings):
        self.django_settings = django_settings
        self.redis = redis_conn.redis_conn(self.django_settings)
        self.alert_counters ={}#记录每个action的触发报警次数
        alert_counters ={
            1:{
                2: {'counter': 0, 'last_alert ':None},
                4: {'counter': 1, 'last_alert': None}, #K是action id，
            }
        }

    def start_watching(self):
        '''
        :return:
        '''
        radio =self.redis.pubsub()
        radio.subscribe(self.django_settings.TRIGGER_CHAN)
        radio.parse_response() #ready to watch
        print("\033[43;1m*****开始监听new trigger******\033[0m")
        self.trigger_count = 0
        while True:
            print("########")
            msg =radio.parse_response()
            print("########")
            self.trigger_consume(msg)

    def trigger_consume(self,msg):
        self.trigger_count += 1
        print ('\033[41;******获取trigger msg [%s]******\033[0m'% self.trigger_count)
        trigger_msg = pickle.loads(msg[2])

        action =ActionHandler(trigger_msg,self.alert_counters)
        action.trigger_process()

class ActionHandler(object):
    '''
    负责把达到报警条件的trigger进行分析，并根据action表中的配置进行报警
    '''

    def __init__(self,trigger_data,alert_counters_dict):
        self.trigger_data = trigger_data
        self.alert_counters_dict = alert_counters_dict

    def record_log(self, action_obj, action_operation, host_id, trigger_data):
        """record alert log into DB"""
        models.EventLog.objects.create(
            event_type=0,
            host_id=host_id,
            trigger_id=trigger_data.get('trigger_id'),
            log=trigger_data
        )

    def action_email(self, action_obj, action_operation_obj, host_id, trigger_data):
        '''
        sending alert email to who concerns.
        :param action_obj: 触发这个报警的action对象
        :param action_operation_obj: 要报警的动作对象
        :param host_id: 要报警的目标主机
        :param trigger_data: 要报警的数据
        :return:
        '''

        print("要发报警的数据:", self.alert_counter_dic[action_obj.id][host_id])
        print("action email:", action_operation_obj.action_type, action_operation_obj.notifiers, trigger_data)
        notifier_mail_list = [obj.email for obj in action_operation_obj.notifiers.all()]
        subject = '级别:%s -- 主机:%s -- 服务:%s' % (trigger_data.get('trigger_id'),
                                               trigger_data.get('host_id'),
                                               trigger_data.get('service_item'))

        send_mail(
            subject,
            action_operation_obj.msg_format,
            settings.DEFAULT_FROM_EMAIL,
            notifier_mail_list,
        )

    def trigger_process(self):
        '''
        分析trigger并报警
        :return:
        '''
        print('分析开始'.center(50,'*'))
        #print(self.trigger_data)

        if self.trigger_data.get('trigger_id') == None:
            if self.trigger_data.get('msg'):
                print(self.trigger_data.get('msg'))

            else:
                print('非法数据[%s]' % self.trigger_data)

        else: #合法数据，报警触发
            print("\033[33;1m%s\033[0m" % self.trigger_data)

            trigger_id = self.trigger_data.get('trigger_id')
            host_id = self.trigger_data.get('host_id')
            trigger_obj =models.Trigger.objects.get(id =trigger_id)
            action_set =trigger_obj.action_set.select.related()
            matched_action_list = set()
            for action in action_set:
                # 每个action 都 可以直接 包含多个主机或主机组,
                # 为什么tigger里关联了template,template里又关联了主机，那action还要直接关联主机呢？
                # 那是因为一个trigger可以被多个template关联，这个trigger触发了，不一定是哪个tempalte里的主机导致的
                for hg in action.host_groups.select_related():
                    for h in hg.host_set.select_related():
                        if h.id ==host_id:#这个action适用于此主机
                            matched_action_list.add(action)
                            if action.id not in self.alert_counters_dict:#第一次被触发
                                self.alert_counters_dict[action] = {
                                    h.id:{'counter': 0, 'last_alert ':time.time()}
                                }
                for host in action.hosts.select_related():
                    if host.id == host_id:#这个action适用于此主机
                        matched_action_list.add(action)
                        self.alert_counters_dict.setdefault(action,{host.id:{'counter': 0, 'last_alert ':time.time()}})

            for action_obj in matched_action_list:
                if time.time() - self.alert_counters_dict[action_obj.id][host_id]['last_alert'] >= action_obj.interval:
                    #该报警了
                    print("该报警了.......", time.time() - self.alert_counter_dic[action_obj.id][host_id]['last_alert'],
                          action_obj.interval)
                    for action_operation in action_obj.operations.select_related().order_by('-step'):
                        if action_operation.step >self.alert_counters_dict[action_obj.id][host_id]['counter']:
                            print('alert action:%s' %action.action_type,action.notifiers)

                            action_func = getattr(self, 'action_%s' % action_operation.action_type)
                            action_func(action_obj, action_operation, host_id, self.trigger_data)

                            # 报完警后更新一下报警时间 ，这样就又重新计算alert interval了
                            self.alert_counter_dic[action_obj.id][host_id]['last_alert'] = time.time()
                            self.record_log(action_obj, action_operation, host_id, self.trigger_data)







