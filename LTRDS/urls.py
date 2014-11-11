from django.conf.urls import patterns, include, url
from serverstatus.views import *

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'LTRDS.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^importrds/', importRDSlog, name='importRDSlog'),
    #url(r'^importrdmpinfo/', importRDMPinfo, name='importRDMPinfo'),
    
)
