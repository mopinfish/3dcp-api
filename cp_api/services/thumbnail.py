"""
cp_api/services/thumbnail.py

ムービー（3D映像）のサムネイル生成サービス

機能:
- Luma AIのURLからキャプチャIDを抽出
- Luma CDNからサムネイル画像をダウンロード
- 画像のリサイズと最適化
- Movieモデルへの保存
"""

import re
import logging
from io import BytesIO

import requests
from PIL import Image
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


def extract_capture_id(luma_url: str) -> str | None:
    """
    Luma URLからキャプチャIDを抽出
    
    Args:
        luma_url: Luma AIのURL (例: https://lumalabs.ai/capture/abc123-def456)
    
    Returns:
        キャプチャID または None
    """
    if not luma_url:
        return None
    
    match = re.search(r'lumalabs\.ai/capture/([a-zA-Z0-9-]+)', luma_url)
    return match.group(1) if match else None


def download_luma_thumbnail(capture_id: str, timeout: int = 30) -> bytes | None:
    """
    Luma CDNからサムネイル画像をダウンロード
    
    Args:
        capture_id: Luma AIのキャプチャID
        timeout: リクエストのタイムアウト秒数
    
    Returns:
        画像のバイナリデータ または None
    """
    cdn_url = f"https://cdn.lumalabs.ai/captures/{capture_id}/thumbnail.jpg"
    
    try:
        logger.info(f"📥 Downloading thumbnail from: {cdn_url}")
        response = requests.get(cdn_url, timeout=timeout)
        
        if response.status_code == 200:
            logger.info(f"✅ Successfully downloaded thumbnail ({len(response.content)} bytes)")
            return response.content
        else:
            logger.warning(f"⚠️ Failed to download thumbnail: HTTP {response.status_code}")
            return None
            
    except requests.Timeout:
        logger.error(f"❌ Timeout downloading thumbnail from: {cdn_url}")
        return None
    except requests.RequestException as e:
        logger.error(f"❌ Error downloading thumbnail: {e}")
        return None


def resize_thumbnail(image_data: bytes, width: int = 400, height: int = 300, quality: int = 90) -> bytes:
    """
    サムネイル画像をリサイズ
    
    Args:
        image_data: 元画像のバイナリデータ
        width: リサイズ後の幅
        height: リサイズ後の高さ
        quality: JPEG品質 (1-100)
    
    Returns:
        リサイズ後の画像バイナリデータ
    """
    try:
        img = Image.open(BytesIO(image_data))
        
        # RGBに変換（PNGなどの場合）
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # リサイズ（アスペクト比を維持してクロップ）
        img_ratio = img.width / img.height
        target_ratio = width / height
        
        if img_ratio > target_ratio:
            # 画像が横長の場合、幅を基準にリサイズ
            new_height = height
            new_width = int(height * img_ratio)
        else:
            # 画像が縦長の場合、高さを基準にリサイズ
            new_width = width
            new_height = int(width / img_ratio)
        
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 中央からクロップ
        left = (new_width - width) // 2
        top = (new_height - height) // 2
        img = img.crop((left, top, left + width, top + height))
        
        # JPEG形式で出力
        output = BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"❌ Error resizing thumbnail: {e}")
        # リサイズに失敗した場合は元のデータを返す
        return image_data


def generate_thumbnail_for_movie(movie, force: bool = False) -> bool:
    """
    Movieのサムネイルを生成して保存
    
    Args:
        movie: Movieモデルのインスタンス
        force: 既存のサムネイルがあっても再生成するかどうか
    
    Returns:
        成功した場合はTrue、失敗した場合はFalse
    """
    # 既にサムネイルがある場合はスキップ（forceがTrueでない限り）
    if movie.thumbnail and not force:
        logger.info(f"ℹ️ Movie #{movie.id} already has a thumbnail, skipping")
        return True
    
    # Luma AIのURL以外はスキップ
    if not movie.url or 'lumalabs.ai' not in movie.url:
        logger.info(f"ℹ️ Movie #{movie.id} is not a Luma AI URL, skipping")
        return False
    
    # キャプチャIDを抽出
    capture_id = extract_capture_id(movie.url)
    if not capture_id:
        logger.warning(f"⚠️ Could not extract capture ID from URL: {movie.url}")
        return False
    
    logger.info(f"🎬 Generating thumbnail for Movie #{movie.id} (capture_id: {capture_id})")
    
    # サムネイルをダウンロード
    image_data = download_luma_thumbnail(capture_id)
    if not image_data:
        logger.error(f"❌ Failed to download thumbnail for Movie #{movie.id}")
        return False
    
    # リサイズ
    try:
        resized_data = resize_thumbnail(image_data)
    except Exception as e:
        logger.error(f"❌ Failed to resize thumbnail for Movie #{movie.id}: {e}")
        return False
    
    # 保存
    try:
        filename = f"movie-{movie.id}.jpg"
        
        # 既存のサムネイルを削除
        if movie.thumbnail:
            try:
                movie.thumbnail.delete(save=False)
            except Exception:
                pass
        
        # 新しいサムネイルを保存
        movie.thumbnail.save(filename, ContentFile(resized_data), save=True)
        
        logger.info(f"✅ Successfully saved thumbnail for Movie #{movie.id}: {movie.thumbnail.url}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to save thumbnail for Movie #{movie.id}: {e}")
        return False


def delete_thumbnail_for_movie(movie) -> bool:
    """
    Movieのサムネイルを削除
    
    Args:
        movie: Movieモデルのインスタンス
    
    Returns:
        成功した場合はTrue、失敗した場合はFalse
    """
    if not movie.thumbnail:
        return True
    
    try:
        movie.thumbnail.delete(save=True)
        logger.info(f"🗑️ Deleted thumbnail for Movie #{movie.id}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to delete thumbnail for Movie #{movie.id}: {e}")
        return False
