from django.conf import settings

BGO_URL = getattr(settings, 'BGO_URL', "http://build.gnome.org/continuous/buildmaster/")
