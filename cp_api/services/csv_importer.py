"""
cp_api/services/csv_importer.py

文化財CSVインポートサービス

機能:
- 自治体標準データセット形式のCSV解析
- バリデーション（座標、必須項目、重複チェック）
- データベースへの一括登録
- エンコーディング自動判定（UTF-8, UTF-16, Shift-JIS等）
"""

import io
import csv
import uuid
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum

from django.db import transaction
from django.contrib.gis.geos import Point
from django.core.cache import cache

logger = logging.getLogger(__name__)


class ImportStatus(Enum):
    """インポート行のステータス"""
    VALID = "valid"           # 有効（インポート可能）
    ERROR = "error"           # エラー（インポート不可）
    DUPLICATE = "duplicate"   # 重複（既存データと重複）
    WARNING = "warning"       # 警告（インポート可能だが注意が必要）


@dataclass
class ImportRow:
    """インポート対象の1行を表すデータクラス"""
    row_number: int                      # 行番号（1始まり、ヘッダー除く）
    status: ImportStatus = ImportStatus.VALID
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    # マッピング後のフィールド
    name: Optional[str] = None
    name_kana: Optional[str] = None
    name_en: Optional[str] = None
    category: Optional[str] = None
    type: Optional[str] = None
    place_name: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    url: Optional[str] = None
    note: Optional[str] = None
    
    # 重複チェック用
    duplicate_id: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'row_number': self.row_number,
            'status': self.status.value,
            'errors': self.errors,
            'warnings': self.warnings,
            'name': self.name,
            'name_kana': self.name_kana,
            'name_en': self.name_en,
            'category': self.category,
            'type': self.type,
            'place_name': self.place_name,
            'address': self.address,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'url': self.url,
            'note': self.note,
            'duplicate_id': self.duplicate_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ImportRow':
        """辞書からインスタンスを生成"""
        row = cls(row_number=data['row_number'])
        row.status = ImportStatus(data['status'])
        row.errors = data.get('errors', [])
        row.warnings = data.get('warnings', [])
        row.name = data.get('name')
        row.name_kana = data.get('name_kana')
        row.name_en = data.get('name_en')
        row.category = data.get('category')
        row.type = data.get('type')
        row.place_name = data.get('place_name')
        row.address = data.get('address')
        row.latitude = data.get('latitude')
        row.longitude = data.get('longitude')
        row.url = data.get('url')
        row.note = data.get('note')
        row.duplicate_id = data.get('duplicate_id')
        return row


@dataclass
class ImportPreviewResult:
    """プレビュー結果を表すデータクラス"""
    filename: str
    total_rows: int
    valid_rows: int
    error_rows: int
    duplicate_rows: int
    warning_rows: int
    columns_detected: List[str]
    rows: List[ImportRow]
    detected_encoding: Optional[str] = None  # 検出されたエンコーディング
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'filename': self.filename,
            'total_rows': self.total_rows,
            'valid_rows': self.valid_rows,
            'error_rows': self.error_rows,
            'duplicate_rows': self.duplicate_rows,
            'warning_rows': self.warning_rows,
            'columns_detected': self.columns_detected,
            'rows': [row.to_dict() for row in self.rows],
            'detected_encoding': self.detected_encoding,
        }


@dataclass
class ImportExecuteResult:
    """インポート実行結果を表すデータクラス"""
    success: bool
    imported_count: int
    skipped_count: int
    error_count: int
    duplicate_count: int
    errors: List[Dict[str, Any]] = field(default_factory=list)
    created_ids: List[int] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'success': self.success,
            'imported_count': self.imported_count,
            'skipped_count': self.skipped_count,
            'error_count': self.error_count,
            'duplicate_count': self.duplicate_count,
            'errors': self.errors,
            'created_ids': self.created_ids,
        }


class CulturalPropertyCSVImporter:
    """文化財CSVインポーター"""
    
    # 自治体標準データセットのカラム名マッピング
    # 複数のカラム名に対応（優先順位順）
    COLUMN_MAPPING = {
        'name': ['名称', 'name'],
        'name_kana': ['名称_カナ', 'name_kana', 'ふりがな'],
        'name_en': ['名称_英語', 'name_en', '英語名'],
        'category': ['文化財分類', 'category', 'カテゴリ'],
        'type': ['種類', 'type', '種別'],
        'place_name': ['場所名称', 'place_name', '場所名'],
        'address': ['所在地_連結表記', 'address', '住所', '所在地'],
        'latitude': ['緯度', 'latitude', 'lat'],
        'longitude': ['経度', 'longitude', 'lng', 'lon'],
        'url': ['URL', 'url', '参考URL'],
        'note': ['備考', 'note', '説明'],
    }
    
    # 必須フィールド（typeは必須から外し、デフォルト値を設定）
    REQUIRED_FIELDS = ['name', 'address', 'latitude', 'longitude']
    
    # デフォルト値
    DEFAULT_TYPE = '不明'
    
    # 緯度の有効範囲（日本国内）
    LATITUDE_RANGE = (20.0, 46.0)
    
    # 経度の有効範囲（日本国内）
    LONGITUDE_RANGE = (122.0, 154.0)
    
    # セッションキャッシュの有効期限（秒）
    SESSION_TIMEOUT = 1800  # 30分
    
    # エンコーディング判定の候補（優先順位順）
    ENCODING_CANDIDATES = [
        'utf-8',
        'utf-8-sig',      # UTF-8 with BOM
        'utf-16',
        'utf-16-le',
        'utf-16-be',
        'cp932',          # Windows Shift-JIS
        'shift-jis',
        'euc-jp',
        'iso-2022-jp',
    ]
    
    def __init__(self, check_duplicates: bool = True):
        """
        初期化
        
        Args:
            check_duplicates: 重複チェックを行うかどうか
        """
        self.check_duplicates = check_duplicates
    
    def detect_encoding(self, file_content: bytes) -> str:
        """
        ファイルのエンコーディングを自動判定
        
        Args:
            file_content: ファイルのバイト列
            
        Returns:
            検出されたエンコーディング名
        """
        # BOMによる判定
        if file_content.startswith(b'\xff\xfe'):
            logger.info("🔍 BOM検出: UTF-16 LE")
            return 'utf-16-le'
        if file_content.startswith(b'\xfe\xff'):
            logger.info("🔍 BOM検出: UTF-16 BE")
            return 'utf-16-be'
        if file_content.startswith(b'\xef\xbb\xbf'):
            logger.info("🔍 BOM検出: UTF-8 with BOM")
            return 'utf-8-sig'
        
        # 各エンコーディングで試す
        for encoding in self.ENCODING_CANDIDATES:
            try:
                decoded = file_content.decode(encoding)
                # 日本語の文字が含まれているかチェック
                # ヘッダーに「名称」「緯度」「経度」などが含まれていれば正しい
                if any(keyword in decoded for keyword in ['名称', '緯度', '経度', '住所', '所在地']):
                    logger.info(f"🔍 エンコーディング検出: {encoding}")
                    return encoding
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        # デフォルトはUTF-8
        logger.warning("⚠️ エンコーディング自動判定失敗、UTF-8をデフォルトとして使用")
        return 'utf-8'
    
    def preview(
        self, 
        file_path: str = None, 
        file_content: bytes = None,
        filename: str = None,
        encoding: str = None  # Noneの場合は自動判定
    ) -> Tuple[ImportPreviewResult, str]:
        """
        CSVファイルを解析してプレビュー結果を返す
        
        Args:
            file_path: ファイルパス（CLI用）
            file_content: ファイル内容（Web API用）
            filename: ファイル名
            encoding: ファイルエンコーディング（Noneの場合は自動判定）
            
        Returns:
            (ImportPreviewResult, session_id): プレビュー結果とセッションID
        """
        logger.info(f"📂 CSVプレビュー開始: {filename or file_path}")
        
        # ファイル内容を取得（エンコーディング判定用）
        if file_path and not file_content:
            with open(file_path, 'rb') as f:
                file_content = f.read()
        
        # エンコーディング自動判定
        detected_encoding = encoding
        if not encoding or encoding == 'auto':
            detected_encoding = self.detect_encoding(file_content)
            logger.info(f"📋 自動検出エンコーディング: {detected_encoding}")
        
        # CSVを読み込み
        rows_data, columns = self._parse_csv(
            file_content=file_content,
            encoding=detected_encoding
        )
        
        # カラムマッピングを検出
        column_map = self._detect_column_mapping(columns)
        logger.info(f"📋 検出されたカラムマッピング: {column_map}")
        
        # 各行をバリデーション
        import_rows: List[ImportRow] = []
        for idx, row_data in enumerate(rows_data, start=1):
            import_row = self._process_row(row_data, idx, column_map)
            import_rows.append(import_row)
        
        # 統計を計算
        valid_rows = sum(1 for r in import_rows if r.status == ImportStatus.VALID)
        error_rows = sum(1 for r in import_rows if r.status == ImportStatus.ERROR)
        duplicate_rows = sum(1 for r in import_rows if r.status == ImportStatus.DUPLICATE)
        warning_rows = sum(1 for r in import_rows if r.status == ImportStatus.WARNING)
        
        result = ImportPreviewResult(
            filename=filename or (file_path.split('/')[-1] if file_path else 'unknown.csv'),
            total_rows=len(import_rows),
            valid_rows=valid_rows,
            error_rows=error_rows,
            duplicate_rows=duplicate_rows,
            warning_rows=warning_rows,
            columns_detected=columns,
            rows=import_rows,
            detected_encoding=detected_encoding
        )
        
        # セッションに保存
        session_id = str(uuid.uuid4())
        self._save_session(session_id, result)
        
        logger.info(f"✅ CSVプレビュー完了: 総数={len(import_rows)}, 有効={valid_rows}, エラー={error_rows}, 重複={duplicate_rows}")
        
        return result, session_id
    
    def execute(
        self,
        session_id: str = None,
        rows: List[ImportRow] = None,
        created_by: 'User' = None,
        skip_errors: bool = True,
        skip_duplicates: bool = True,
        selected_row_numbers: List[int] = None
    ) -> ImportExecuteResult:
        """
        インポートを実行する
        
        Args:
            session_id: プレビュー時のセッションID
            rows: インポート対象の行リスト（session_idがない場合）
            created_by: 作成者ユーザー
            skip_errors: エラー行をスキップするかどうか
            skip_duplicates: 重複行をスキップするかどうか
            selected_row_numbers: 特定の行番号のみインポート（Noneの場合は全て）
            
        Returns:
            ImportExecuteResult: 実行結果
        """
        from cp_api.models import CulturalProperty
        
        logger.info(f"🚀 CSVインポート実行開始")
        
        # セッションから行データを取得
        if session_id:
            session_data = self._get_session(session_id)
            if not session_data:
                logger.error("❌ セッションが見つかりません")
                return ImportExecuteResult(
                    success=False,
                    imported_count=0,
                    skipped_count=0,
                    error_count=0,
                    duplicate_count=0,
                    errors=[{'message': 'セッションが期限切れか見つかりません'}]
                )
            rows = [ImportRow.from_dict(r) for r in session_data['rows']]
        
        if not rows:
            logger.error("❌ インポート対象の行がありません")
            return ImportExecuteResult(
                success=False,
                imported_count=0,
                skipped_count=0,
                error_count=0,
                duplicate_count=0,
                errors=[{'message': 'インポート対象の行がありません'}]
            )
        
        # 特定行のみ選択
        if selected_row_numbers:
            rows = [r for r in rows if r.row_number in selected_row_numbers]
        
        # インポート対象をフィルタリング
        rows_to_import = []
        skipped_count = 0
        error_count = 0
        duplicate_count = 0
        
        for row in rows:
            if row.status == ImportStatus.ERROR:
                if skip_errors:
                    skipped_count += 1
                    error_count += 1
                    continue
                else:
                    # エラー行を含めない場合は失敗
                    return ImportExecuteResult(
                        success=False,
                        imported_count=0,
                        skipped_count=skipped_count,
                        error_count=error_count,
                        duplicate_count=duplicate_count,
                        errors=[{'row': row.row_number, 'errors': row.errors}]
                    )
            
            if row.status == ImportStatus.DUPLICATE:
                if skip_duplicates:
                    skipped_count += 1
                    duplicate_count += 1
                    continue
                else:
                    rows_to_import.append(row)
            
            if row.status in [ImportStatus.VALID, ImportStatus.WARNING]:
                rows_to_import.append(row)
        
        # 一括インポート
        created_ids = []
        errors = []
        
        try:
            with transaction.atomic():
                for row in rows_to_import:
                    try:
                        # ジオメトリを生成
                        geom = Point(row.longitude, row.latitude, srid=6668)
                        
                        # CulturalPropertyを作成
                        cp = CulturalProperty(
                            name=row.name,
                            name_kana=row.name_kana or '',
                            name_en=row.name_en or '',
                            category=row.category or '',
                            type=row.type or self.DEFAULT_TYPE,
                            place_name=row.place_name or '',
                            address=row.address,
                            latitude=row.latitude,
                            longitude=row.longitude,
                            url=row.url or '',
                            note=row.note or '',
                            geom=geom,
                            created_by=created_by
                        )
                        cp.save()
                        created_ids.append(cp.id)
                        
                    except Exception as e:
                        logger.error(f"❌ 行{row.row_number}のインポートに失敗: {e}")
                        errors.append({
                            'row': row.row_number,
                            'name': row.name,
                            'error': str(e)
                        })
                        error_count += 1
        
        except Exception as e:
            logger.error(f"❌ トランザクションエラー: {e}")
            return ImportExecuteResult(
                success=False,
                imported_count=0,
                skipped_count=skipped_count,
                error_count=error_count,
                duplicate_count=duplicate_count,
                errors=[{'message': f'データベースエラー: {str(e)}'}]
            )
        
        # セッションを削除
        if session_id:
            self._delete_session(session_id)
        
        logger.info(f"✅ CSVインポート完了: インポート={len(created_ids)}, スキップ={skipped_count}")
        
        return ImportExecuteResult(
            success=True,
            imported_count=len(created_ids),
            skipped_count=skipped_count,
            error_count=error_count,
            duplicate_count=duplicate_count,
            errors=errors,
            created_ids=created_ids
        )
    
    def _parse_csv(
        self,
        file_path: str = None,
        file_content: bytes = None,
        encoding: str = 'utf-8'
    ) -> Tuple[List[Dict[str, str]], List[str]]:
        """
        CSVファイルを読み込んで行データとカラム名を返す
        
        Returns:
            (rows, columns): 行データのリストとカラム名のリスト
        """
        if file_path and not file_content:
            with open(file_path, 'rb') as f:
                file_content = f.read()
        
        if not file_content:
            raise ValueError("file_path または file_content が必要です")
        
        # デコード
        content = file_content.decode(encoding, errors='replace')
        
        # BOMを除去（UTF-8-sigの場合は自動で除去されるが念のため）
        if content.startswith('\ufeff'):
            content = content[1:]
        
        # 改行コードを統一
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # CSVを解析
        reader = csv.DictReader(io.StringIO(content))
        columns = reader.fieldnames or []
        rows = list(reader)
        
        return rows, columns
    
    def _detect_column_mapping(self, columns: List[str]) -> Dict[str, str]:
        """
        CSVのカラム名から内部フィールドへのマッピングを検出
        
        Returns:
            {内部フィールド名: CSVカラム名} の辞書
        """
        mapping = {}
        
        for field_name, possible_columns in self.COLUMN_MAPPING.items():
            for col_name in possible_columns:
                if col_name in columns:
                    mapping[field_name] = col_name
                    break
        
        return mapping
    
    def _process_row(
        self,
        row_data: Dict[str, str],
        row_number: int,
        column_map: Dict[str, str]
    ) -> ImportRow:
        """
        1行を処理してImportRowを生成
        """
        from cp_api.models import CulturalProperty
        
        import_row = ImportRow(row_number=row_number)
        import_row.raw_data = row_data
        
        # カラムマッピングに従ってデータを抽出
        for field_name, csv_column in column_map.items():
            value = row_data.get(csv_column, '').strip()
            
            # 空文字列はNoneに変換
            if value == '':
                value = None
            
            # 数値フィールドの変換
            if field_name in ['latitude', 'longitude'] and value:
                try:
                    value = float(value)
                except ValueError:
                    import_row.errors.append(f'{field_name}が数値ではありません: {value}')
                    import_row.status = ImportStatus.ERROR
                    value = None
            
            setattr(import_row, field_name, value)
        
        # typeが空の場合はデフォルト値を設定し、警告を追加
        if not import_row.type:
            import_row.type = self.DEFAULT_TYPE
            import_row.warnings.append(f'種類が空のため、デフォルト値「{self.DEFAULT_TYPE}」を設定しました')
            if import_row.status == ImportStatus.VALID:
                import_row.status = ImportStatus.WARNING
        
        # 必須フィールドチェック
        for field in self.REQUIRED_FIELDS:
            value = getattr(import_row, field, None)
            if value is None or value == '':
                import_row.errors.append(f'{field}は必須項目です')
                import_row.status = ImportStatus.ERROR
        
        # エラーがなければバリデーション続行
        if import_row.status != ImportStatus.ERROR:
            self._validate_row(import_row)
        
        # 重複チェック
        if import_row.status != ImportStatus.ERROR and self.check_duplicates:
            if import_row.name and import_row.latitude and import_row.longitude:
                duplicate = self._check_duplicate(
                    import_row.name,
                    import_row.latitude,
                    import_row.longitude
                )
                if duplicate:
                    import_row.status = ImportStatus.DUPLICATE
                    import_row.duplicate_id = duplicate.id
                    import_row.warnings.append(f'既存データと重複しています (ID: {duplicate.id})')
        
        return import_row
    
    def _validate_row(self, row: ImportRow) -> None:
        """
        1行のバリデーションを行う（必須チェック以外）
        """
        # 緯度の範囲チェック
        if row.latitude is not None:
            if not (self.LATITUDE_RANGE[0] <= row.latitude <= self.LATITUDE_RANGE[1]):
                row.errors.append(
                    f'緯度が日本国内の範囲外です: {row.latitude} '
                    f'(有効範囲: {self.LATITUDE_RANGE[0]}〜{self.LATITUDE_RANGE[1]})'
                )
                row.status = ImportStatus.ERROR
        
        # 経度の範囲チェック
        if row.longitude is not None:
            if not (self.LONGITUDE_RANGE[0] <= row.longitude <= self.LONGITUDE_RANGE[1]):
                row.errors.append(
                    f'経度が日本国内の範囲外です: {row.longitude} '
                    f'(有効範囲: {self.LONGITUDE_RANGE[0]}〜{self.LONGITUDE_RANGE[1]})'
                )
                row.status = ImportStatus.ERROR
        
        # URL形式チェック（警告のみ）
        if row.url and not (row.url.startswith('http://') or row.url.startswith('https://')):
            row.warnings.append(f'URLの形式が不正です: {row.url}')
            if row.status == ImportStatus.VALID:
                row.status = ImportStatus.WARNING
        
        # 文字列長チェック
        if row.name and len(row.name) > 254:
            row.errors.append(f'名称が長すぎます (最大254文字)')
            row.status = ImportStatus.ERROR
        
        if row.address and len(row.address) > 254:
            row.errors.append(f'住所が長すぎます (最大254文字)')
            row.status = ImportStatus.ERROR
    
    def _check_duplicate(
        self,
        name: str,
        latitude: float,
        longitude: float,
        tolerance: float = 0.0001  # 約10m
    ) -> Optional['CulturalProperty']:
        """
        重複チェックを行う
        
        同一名称かつ座標が近い（toleranceの範囲内）データを検索
        """
        from cp_api.models import CulturalProperty
        
        # 名称が完全一致し、座標が近いものを検索
        duplicates = CulturalProperty.objects.filter(
            name=name,
            latitude__gte=latitude - tolerance,
            latitude__lte=latitude + tolerance,
            longitude__gte=longitude - tolerance,
            longitude__lte=longitude + tolerance
        )
        
        return duplicates.first()
    
    def _save_session(self, session_id: str, result: ImportPreviewResult) -> None:
        """プレビュー結果をセッションに保存"""
        cache.set(
            f"csv_import_session:{session_id}",
            result.to_dict(),
            timeout=self.SESSION_TIMEOUT
        )
        logger.info(f"📝 セッション保存: {session_id}")
    
    def _get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """セッションからプレビュー結果を取得"""
        data = cache.get(f"csv_import_session:{session_id}")
        if data:
            logger.info(f"📖 セッション取得: {session_id}")
        else:
            logger.warning(f"⚠️ セッションが見つかりません: {session_id}")
        return data
    
    def _delete_session(self, session_id: str) -> None:
        """セッションを削除"""
        cache.delete(f"csv_import_session:{session_id}")
        logger.info(f"🗑️ セッション削除: {session_id}")
