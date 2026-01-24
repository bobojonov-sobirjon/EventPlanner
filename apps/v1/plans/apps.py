from django.apps import AppConfig


class PlansConfig(AppConfig):
    name = 'apps.v1.plans'
    verbose_name = 'Планы'
    
    def ready(self):
        import apps.v1.plans.signals  # noqa
