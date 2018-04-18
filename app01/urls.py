"""Monitor URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url,include
from django.contrib import admin
from app01 import views

urlpatterns = [
    url(r'^$',views.index ),
    url(r'^dashboard/$',views.dashboard ,name='dashboard' ),
    url(r'api/client/config/(\d+)/$',views.client_config),
    url(r'api/client/service/report/$',views.service_report),
    url(r'^triggers/$',views.triggers,name='triggers' ),
    url(r'hosts/$',views.hosts ,name='hosts'),
    url(r'host_groups/$',views.host_groups ,name='host_groups'),
    url(r'hosts/(\d+)/$',views.host_detail ,name='host_detail'),
    url(r'graphs/$', views.graphs_generator, name='get_graphs'),
    url(r'trigger_list/$',views.trigger_list ,name='trigger_list'),
    #url(r'client/service/report/$',views.service_data_report ),

    url(r'hosts/status/$',views.hosts_status,name='get_hosts_status' ),
    url(r'groups/status/$',views.hostgroups_status,name='get_hostgroups_status' ),
    #url(r'graphs/$',views.graphs_generator,name='get_graphs' )

]
