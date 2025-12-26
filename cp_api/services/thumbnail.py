"""
cp_api/services/thumbnail.py

ムービー（3D映像）のサムネイル生成サービス

機能:
- Luma AIのページからOGP画像URLを抽出
- cdn-luma.comからサムネイル画像をダウンロード
- 画像のリサイズと最適化
- Movieモデルへの保存
"""

import re
import logging
from io import BytesIO
from urllib.parse import unquote

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


def fetch_og_image_url(luma_url: str, timeout: int = 30) -> str | None:
    """
    LumaページのHTMLからOGP画像URLを抽出
    
    Args:
        luma_url: Luma AIのキャプチャページURL
        timeout: リクエストのタイムアウト秒数
    
    Returns:
        OGP画像URL（cdn-luma.comの直接URL） または None
    """
    try:
        logger.info(f"📄 Fetching OGP image from: {luma_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(luma_url, headers=headers, timeout=timeout)
        
        if response.status_code != 200:
            logger.warning(f"⚠️ Failed to fetch page: HTTP {response.status_code}")
            return None
        
        html = response.text
        
        # og:image メタタグからURLを抽出
        # パターン1: content属性内のcdn-luma.com URL
        og_match = re.search(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html)
        if not og_match:
            # パターン2: content属性が先に来る場合
            og_match = re.search(r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']', html)
        
        if not og_match:
            logger.warning("⚠️ og:image meta tag not found")
            return None
        
        og_url = og_match.group(1)
        logger.info(f"📍 Found og:image URL: {og_url}")
        
        # og:image URLからcdn-luma.comの直接URLを抽出
        # 形式: https://lumalabs.ai/api/og/image/capture?src=https%3A%2F%2Fcdn-luma.com%2F...%2F_thumb.jpg&type=captures
        src_match = re.search(r'src=([^&]+)', og_url)
        if src_match:
            encoded_url = src_match.group(1)
            cdn_url = unquote(encoded_url)
            logger.info(f"✅ Extracted CDN URL: {cdn_url}")
            return cdn_url
        
        # srcパラメータがない場合はog:image URLをそのまま返す
        return og_url
        
    except requests.Timeout:
        logger.error(f"❌ Timeout fetching page: {luma_url}")
        return None
    except requests.RequestException as e:
        logger.error(f"❌ Error fetching page: {e}")
        return None


def download_thumbnail(image_url: str, timeout: int = 30) -> bytes | None:
    """
    画像URLからサムネイル画像をダウンロード
    
    Args:
        image_url: 画像のURL（cdn-luma.comまたはその他）
        timeout: リクエストのタイムアウト秒数
    
    Returns:
        画像のバイナリデータ または None
    """
    try:
        logger.info(f"📥 Downloading thumbnail from: {image_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(image_url, headers=headers, timeout=timeout)
        
        if response.status_code == 200:
            logger.info(f"✅ Successfully downloaded thumbnail ({len(response.content)} bytes)")
            return response.content
        else:
            logger.warning(f"⚠️ Failed to download thumbnail: HTTP {response.status_code}")
            return None
            
    except requests.Timeout:
        logger.error(f"❌ Timeout downloading thumbnail from: {image_url}")
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
    
    logger.info(f"🎬 Generating thumbnail for Movie #{movie.id}")
    
    # Step 1: LumaページからOGP画像URLを取得
    og_image_url = fetch_og_image_url(movie.url)
    if not og_image_url:
        logger.error(f"❌ Failed to get OGP image URL for Movie #{movie.id}")
        return False
    
    # Step 2: サムネイル画像をダウンロード
    image_data = download_thumbnail(og_image_url)
    if not image_data:
        logger.error(f"❌ Failed to download thumbnail for Movie #{movie.id}")
        return False
    
    # Step 3: リサイズ
    try:
        resized_data = resize_thumbnail(image_data)
    except Exception as e:
        logger.error(f"❌ Failed to resize thumbnail for Movie #{movie.id}: {e}")
        return False
    
    # Step 4: 保存
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
