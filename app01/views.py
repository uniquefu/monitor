from django.shortcuts import render,HttpResponse
import json
from Monitor import  settings
from  app01.backends import redis_conn,data_optimization,data_processing
from app01.serialize import ClientHandler,get_host_triggers,StatusSerializer,GroupStatusSerializer
from  django.views.decorators.csrf import csrf_exempt
from app01 import  models
from app01 import graphs

REDIS_OBJ = redis_conn.redis_conn(settings)

# Create your views here.
def index(request):
    return render(request, 'monitor/index.html')

def dashboard(request):

    return render(request,'monitor/dashboard.html')

def triggers(request):

    return render(request,'monitor/triggers.html')


def hosts(request):
    host_list = models.Host.objects.all()
    print("hosts:",host_list)
    return render(request,'monitor/hosts.html',{'host_list':host_list})

def host_detail(request,host_id):
    host_obj = models.Host.objects.get(id=host_id)
    return render(request,'monitor/host_detail.html',{'host_obj':host_obj})

def host_detail_old(request,host_id):
    host_obj = models.Host.objects.get(id=host_id)

    config_obj = ClientHandler(host_obj.id)
    monitored_services = {
            "services":{},
            "sub_services": {} #存储一个服务有好几个独立子服务 的监控,比如网卡服务 有好几个网卡
        }

    template_list= list(host_obj.templates.select_related())

    for host_group in host_obj.host_groups.select_related():
        template_list.extend( host_group.templates.select_related() )
    print(template_list)
    for template in template_list:
        #print(template.services.select_related())

        for service in template.services.select_related(): #loop each service
            print(service)
            if not service.has_sub_service:
                monitored_services['services'][service.name] = [service.plugin_name,service.interval]
            else:
                monitored_services['sub_services'][service.name] = []

                #get last point from redis in order to acquire the sub-service-key
                last_data_point_key = "Status_%s_%s_latest" %(host_obj.id,service.name)
                last_point_from_redis = REDIS_OBJ.lrange(last_data_point_key,-1,-1)[0]
                if last_point_from_redis:
                    data,data_save_time = json.loads(last_point_from_redis)
                    if data:
                        service_data_dic = data.get('data')
                        for serivce_key,val in service_data_dic.items():
                            monitored_services['sub_services'][service.name].append(serivce_key)


    return render(request,'host_detail.html', {'host_obj':host_obj,'monitored_services':monitored_services})


def hosts_status(request):

    hosts_data_serializer = StatusSerializer(request,REDIS_OBJ)
    hosts_data = hosts_data_serializer.by_hosts()

    return HttpResponse(json.dumps(hosts_data))


def hostgroups_status(request):
    group_serializer = GroupStatusSerializer(request,REDIS_OBJ)
    group_serializer.get_all_groups_status()

    return HttpResponse('ss')

def graphs_generator(request):

    graphs_generator = graphs.GraphGenerator2(request,REDIS_OBJ)
    graphs_data = graphs_generator.get_host_graph()
    print("graphs_data",graphs_data)
    return HttpResponse(json.dumps(graphs_data))

def graph_bak(request):


    #host_id = request.GET.get('host_id')
    #service_key = request.GET.get('service_key')

    #print("graph:", host_id,service_key)

    graph_generator = graphs.GraphGenerator(request,REDIS_OBJ)
    graph_data = graph_generator.get_graph_data()
    if graph_data:
        return HttpResponse(json.dumps(graph_data))


def trigger_list(request):

    print ('取trigger')

    host_id = request.GET.get("by_host_id")

    host_obj = models.Host.objects.get(id=host_id)

    alert_list = host_obj.eventlog_set.all().order_by('-date')
    return render(request,'monitor/trigger_list.html',locals())


def host_groups(request):

    host_groups = models.HostGroup.objects.all()
    return render(request,'monitor/host_groups.html',locals())

def client_config(request,client_id):
    print("客户端ID",client_id)
    config_obj = ClientHandler(client_id)
    config = config_obj.fetch_configs()

    if config:
        return  HttpResponse(json.dumps(config))

@csrf_exempt
def service_report(request):
    if request.method =="POST":
        print('----->', request.POST)
        try:
            data =json.loads(request.POST.get('data'))
            client_id =request.POST.get('client_id')
            service_name = request.POST.get('service_name')

            print("##########存储数据##########")
            data_saving_obj =data_optimization.DataStore(client_id,service_name,data,REDIS_OBJ)

            print("##########存储数据完成##########")
            #同时触发监控
            host_obj = models.Host.objects.get(id = client_id)
            service_triggers = get_host_triggers(host_obj)

            triggers_handler = data_processing.DataHandler(settings,connect_redis =False)


            for trigger in service_triggers:
                print("########获取触发器###########", service_triggers)
                triggers_handler.load_service_data_and_calulating(host_obj,trigger,REDIS_OBJ)

            print("服务器trigger:",service_triggers)



        except Exception as e:
            pass

    return HttpResponse(json.dumps("---report success---"))