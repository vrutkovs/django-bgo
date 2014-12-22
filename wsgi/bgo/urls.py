from django.conf.urls import patterns, include, url
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^sync/builds/$', 'bgo.views.sync_buildlist', name='sync_buildlist'),
    url(r'^sync/builds/(\d{4})(\d{2})(\d{2}).(\d+)/$', 'bgo.views.sync_build', name='sync_build'),
    url(r'^sync/builds/(\d{4})(\d{2})(\d{2}).(\d+)/(\w+)/$', 'bgo.views.sync_test', name='sync_test'),
    url(r'^admin/', include(admin.site.urls)),
)
