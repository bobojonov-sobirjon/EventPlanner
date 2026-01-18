from django.apps import AppConfig


class ConfigConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'config'

    def ready(self):
        from django.contrib import admin
        from django.contrib.auth.models import Group
        from django.contrib.sites.models import Site
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

        try:
            admin.site.unregister(Group)
        except admin.sites.NotRegistered:
            pass

        try:
            admin.site.unregister(Site)
        except admin.sites.NotRegistered:
            pass

        try:
            admin.site.unregister(BlacklistedToken)
        except admin.sites.NotRegistered:
            pass

        try:
            admin.site.unregister(OutstandingToken)
        except admin.sites.NotRegistered:
            pass
