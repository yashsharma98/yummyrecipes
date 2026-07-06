from django.apps import AppConfig


class YummyrecipesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'yummyrecipes'

    def ready(self):
        import yummyrecipes.signals