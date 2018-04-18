#!/usr/bin/env python
# -*- coding:utf-8 -*-
#Author:Jeff Lee
from  Monitor import  settings
import json,time,copy

class DataStore(object):

    def __init__(self,client_id,service_name,data,redis_obj):
        self.client_id =client_id
        self.servicename =service_name
        self.data =data
        self.redis_conn_obj =redis_obj
        self.process_and_save()

    def get_data_slice(self,lastest_data_key,interval):
        '''
        取数据
        :param lastest_data_key:
        :param interval:
        :return:
        '''

        all_real_data = self.redis_conn_obj.lrange(lastest_data_key,1,-1) #第一个为空

        data_set = []
        for item in all_real_data:
            data =json.loads(item.decode())

            if len(data)==2:
                service_data,last_save_time =data

                if time.time() -last_save_time > interval:
                    data_set.append(data)

                else:
                    pass

        return data_set

    def get_avg(self,v_list):
        if len(v_list)>0:
            return sum(v_list)/len(v_list)
        else:
            return 0

    def get_max(self,v_list):
        if len(v_list) > 0:
            return max(v_list)
        else:
            return 0

    def get_min(self,v_list):
        if len(v_list) > 0:
            return min(v_list)
        else:
            return 0

    def get_mid(self,v_list):
        if len(v_list) > 0:
            v_list.sort()
            return v_list[len(v_list)//2]
        else:
            return 0

    def get_optimized_data(self,data_set_key,raw_service_data):

        #print("get_optimized_data:",raw_service_data[0])
        service_data_keys = raw_service_data[0][0].keys()
        first_service_data_point = raw_service_data[0][0]
        #print("keys@@@@@",service_data_keys,)
        #print("data@@@@@", first_service_data_point, )

        optimized_dict ={}

        if 'data' not in service_data_keys:
            print('not network!!!!!!!')
            for key in service_data_keys:
                optimized_dict[key] =[]

            tmp_data_dic =copy.deepcopy(optimized_dict)
            for service_data_item,last_save_time in raw_service_data:
                for service_index,v in service_data_item.items():
                    try:
                        tmp_data_dic[service_index].append(round(float(v),2))

                    except ValueError as e:
                        print(e)

            for service_k,v_list in tmp_data_dic.items():
                #print (service_k,v_list)
                avg_res =self.get_avg(v_list)
                max_res = self.get_max(v_list)
                min_res = self.get_min(v_list)
                mid_res = self.get_mid(v_list)

                optimized_dict[service_k] =[avg_res,max_res,min_res,mid_res]

                #print(service_k,optimized_dict[service_k])
        else:
            print('network@@@@@@@@@')
            #print(first_service_data_point)
            #print(first_service_data_point['data'])
            for service_item_key,v_dic in first_service_data_point['data'].items():
                #service_item_key相当于网卡名ETH0，v_dic={'t_in': '2098.41', 't_out': '1056.77'}
                #print(service_item_key,v_dic)
                optimized_dict[service_item_key] ={}

                for k2,v2 in v_dic.items():
                    optimized_dict[service_item_key][k2]=[]

            tmp_data_dic =copy.deepcopy(optimized_dict)

            if tmp_data_dic:
                #print('raw_service_data:',raw_service_data)

                for service_data_item,last_save_time in raw_service_data:
                    for service_index,v_dic in service_data_item['data'].items():
                        #service_index相当于eth0
                        #print('@@@@@@@@',service_index,v_dic)
                        for service_item_sub_key,val in v_dic.items():
                            #service_item_sub_key相当于t_in,t_out
                            tmp_data_dic[service_index][service_item_sub_key].append(round(float(val),2))

                for service_k,v_dic in tmp_data_dic.items():
                    for service_sub_k,v_list in v_dic.items():
                        avg_res = self.get_avg(v_list)
                        max_res = self.get_max(v_list)
                        min_res = self.get_min(v_list)
                        mid_res = self.get_mid(v_list)

                        optimized_dict[service_k][service_sub_k] =[avg_res,max_res,min_res,mid_res]

                        #print('&&&&&',service_k,service_sub_k,optimized_dict[service_k][service_sub_k])

            else:
                print("Must be sth wrong with client report")

        #print("优化后数据：",optimized_dict)

        return  optimized_dict

    def save_optimized_data(self,data_service_key_in_redis, optimized_data):
        print("%%%%",data_service_key_in_redis)
        self.redis_conn_obj.rpush(data_service_key_in_redis,json.dumps([optimized_data,time.time()]))
        print("%%%%")

    def process_and_save(self):
        #print ("保存1min 服务器")
        if self.data['status'] ==0: #服务数据有效
            for key,data_service_val in settings.STATUS_DATA_OPTIMIZATION.items():
                data_service_key_in_redis = "Status_%s_%s_%s" %(self.client_id,self.servicename,key)

                print("=========%s====%s===========" %(key ,data_service_val),data_service_key_in_redis)
                #print(key ,data_service_val,data_service_key_in_redis)
                last_point_from_redis =self.redis_conn_obj.lrange(data_service_key_in_redis,-1,-1)
                if not last_point_from_redis:
                    self.redis_conn_obj.rpush(data_service_key_in_redis,json.dumps([None,time.time()]))

                if data_service_val[0] ==0:

                    self.redis_conn_obj.rpush(data_service_key_in_redis,json.dumps([self.data, time.time()]))

                else:
                    redis_data= self.redis_conn_obj.lrange(data_service_key_in_redis,-1,-1)[0]

                    last_point_data,last_point_save_time =json.loads(redis_data.decode())


                    if time.time() - last_point_save_time > data_service_val[0]:
                        lastest_data_key_in_redis = "Status_%s_%s_latest" %(self.client_id,self.servicename)
                        #取出最近N分钟数据，并保存在data_set
                        #print('######',data_service_val[0])
                        data_set = self.get_data_slice(lastest_data_key_in_redis,data_service_val[0])

                        #print('数据需要优化,最近N分钟数据:',len(data_set))

                        if len(data_set)>0:
                            # 开始优化数据
                            optimized_data = self.get_optimized_data(data_service_key_in_redis,data_set)

                            print("优化后数据：", optimized_data)
                            if optimized_data:
                                self.save_optimized_data(data_service_key_in_redis,optimized_data)

                if self.redis_conn_obj.llen(data_service_key_in_redis) >= data_service_val[1]:
                    self.redis_conn_obj.lpop(data_service_key_in_redis) #删除最后一个数据
            print('数据结束')


        else:
            print("report data is invalid::", self.data)
            raise ValueError

