"""
cp_api/signals.py

Django Signals - モデル保存時のフック処理

機能:
- Movie保存後にサムネイルを自動生成
- Movie削除時にサムネイルファイルも削除
"""

import logging
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='cp_api.Movie')
def movie_post_save(sender, instance, created, **kwargs):
    """
    Movie保存後にサムネイルを生成
    
    トリガー条件:
    - 新規作成時
    - URLが変更された時（update_fieldsにurlが含まれる場合）
    
    Note:
    - 循環インポートを避けるため、関数内でインポート
    - 非同期実行が望ましいが、シンプルさを優先して同期実行
    """
    from .services.thumbnail import generate_thumbnail_for_movie
    
    # サムネイル生成をスキップするフラグ（無限ループ防止）
    if getattr(instance, '_skip_thumbnail_generation', False):
        return
    
    # update_fieldsが指定されている場合、urlの変更をチェック
    update_fields = kwargs.get('update_fields')
    
    should_generate = False
    
    if created:
        # 新規作成時は常に生成
        should_generate = True
        logger.info(f"🆕 New Movie #{instance.id} created, will generate thumbnail")
    elif update_fields is not None:
        # update_fieldsが指定されている場合、urlが含まれていれば生成
        if 'url' in update_fields:
            should_generate = True
            logger.info(f"🔄 Movie #{instance.id} URL updated, will regenerate thumbnail")
    else:
        # update_fieldsが指定されていない場合（通常のsave）
        # サムネイルがなければ生成
        if not instance.thumbnail:
            should_generate = True
            logger.info(f"📷 Movie #{instance.id} has no thumbnail, will generate")
    
    if should_generate and instance.url:
        try:
            # 無限ループ防止フラグを設定
            instance._skip_thumbnail_generation = True
            
            # サムネイル生成（強制再生成）
            force = not created  # 更新時は強制再生成
            generate_thumbnail_for_movie(instance, force=force)
            
        except Exception as e:
            logger.error(f"❌ Error generating thumbnail for Movie #{instance.id}: {e}")
        finally:
            # フラグをリセット
            instance._skip_thumbnail_generation = False


@receiver(pre_delete, sender='cp_api.Movie')
def movie_pre_delete(sender, instance, **kwargs):
    """
    Movie削除前にサムネイルファイルを削除
    """
    if instance.thumbnail:
        try:
            instance.thumbnail.delete(save=False)
            logger.info(f"🗑️ Deleted thumbnail file for Movie #{instance.id}")
        except Exception as e:
            logger.error(f"❌ Error deleting thumbnail file for Movie #{instance.id}: {e}")
