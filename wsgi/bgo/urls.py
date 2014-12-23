from django.conf.urls import patterns, include, url
from django.contrib import admin
from bgo import views

admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^sync/builds/$', 'bgo.views.sync_buildlist', name='sync_buildlist'),
    url(r'^sync/builds/(\d{4})(\d{2})(\d{2}).(\d+)/$', 'bgo.views.sync_build', name='sync_build'),
    url(r'^sync/builds/(\d{4})(\d{2})(\d{2}).(\d+)/(\w+)/$', 'bgo.views.sync_test', name='sync_test'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^$', views.BuildsListView.as_view(), name='build_list'),
    url(r'^([\d\.]+?)/$', views.BuildDetailView.as_view(), name='build_detail'),
    url(r'^([\d\.]+?)/(\w+)/$', views.TestDetailView.as_view(), name='test_detail'),
    url(r'^test/(\d+)/$', views.TestHistoryView.as_view(), name='test_history'),
)
