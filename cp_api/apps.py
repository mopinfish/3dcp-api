"""
cp_api/apps.py

アプリケーション設定
"""

from django.apps import AppConfig


class Open3DMapConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cp_api'

    def ready(self):
        """
        アプリケーション起動時にSignalを登録
        """
        # signalsモジュールをインポートしてSignalを登録
        import cp_api.signals  # noqa: F401
