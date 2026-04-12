from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "accounts"

    def ready(self):
        # Register HEIC/HEIF support so Pillow can open iPhone photos
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
        except ImportError:
            pass
