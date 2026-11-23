from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "accounts"
    verbose_name = "Customer accounts"

    def ready(self):
        from . import signals  # noqa: F401  (connects the post_save receiver)
