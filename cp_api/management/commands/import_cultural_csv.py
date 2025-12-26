"""
cp_api/management/commands/import_cultural_csv.py

文化財CSVインポート管理コマンド

使用方法:
    # プレビューのみ（ドライラン）- エンコーディング自動判定
    python manage.py import_cultural_csv /path/to/file.csv --dry-run
    
    # インポート実行
    python manage.py import_cultural_csv /path/to/file.csv
    
    # 重複チェックをスキップ
    python manage.py import_cultural_csv /path/to/file.csv --no-duplicate-check
    
    # エンコーディング手動指定（autoで自動判定）
    python manage.py import_cultural_csv /path/to/file.csv --encoding=auto
    python manage.py import_cultural_csv /path/to/file.csv --encoding=utf-16-le
    
    # 詳細表示
    python manage.py import_cultural_csv /path/to/file.csv --verbose
"""

import os
from django.core.management.base import BaseCommand, CommandError
from cp_api.services.csv_importer import (
    CulturalPropertyCSVImporter,
    ImportStatus
)


class Command(BaseCommand):
    help = '文化財CSVファイルをインポートします'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='インポートするCSVファイルのパス'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際にはインポートせず、プレビューのみ表示'
        )
        parser.add_argument(
            '--no-duplicate-check',
            action='store_true',
            help='重複チェックをスキップする'
        )
        parser.add_argument(
            '--skip-errors',
            action='store_true',
            default=True,
            help='エラー行をスキップしてインポート（デフォルト: True）'
        )
        parser.add_argument(
            '--skip-duplicates',
            action='store_true',
            default=True,
            help='重複行をスキップしてインポート（デフォルト: True）'
        )
        parser.add_argument(
            '--encoding',
            type=str,
            default='auto',
            help='CSVファイルのエンコーディング（デフォルト: auto=自動判定）'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='詳細な情報を表示'
        )
    
    def handle(self, *args, **options):
        csv_file = options['csv_file']
        dry_run = options['dry_run']
        no_duplicate_check = options['no_duplicate_check']
        skip_errors = options['skip_errors']
        skip_duplicates = options['skip_duplicates']
        encoding = options['encoding']
        verbose = options['verbose']
        
        # ファイル存在チェック
        if not os.path.exists(csv_file):
            raise CommandError(f'ファイルが見つかりません: {csv_file}')
        
        self.stdout.write(self.style.NOTICE(f'📂 CSVファイル: {csv_file}'))
        if encoding == 'auto':
            self.stdout.write(self.style.NOTICE(f'📋 エンコーディング: 自動判定'))
        else:
            self.stdout.write(self.style.NOTICE(f'📋 エンコーディング: {encoding}'))
        self.stdout.write('')
        
        # インポーターを初期化
        importer = CulturalPropertyCSVImporter(
            check_duplicates=not no_duplicate_check
        )
        
        # プレビュー実行
        self.stdout.write(self.style.NOTICE('🔍 CSVファイルを解析中...'))
        try:
            # encoding='auto'またはNoneの場合は自動判定
            enc = None if encoding == 'auto' else encoding
            result, session_id = importer.preview(
                file_path=csv_file,
                filename=os.path.basename(csv_file),
                encoding=enc
            )
        except Exception as e:
            raise CommandError(f'CSVの解析に失敗しました: {e}')
        
        # 検出されたエンコーディングを表示
        if result.detected_encoding:
            self.stdout.write(self.style.SUCCESS(f'🔍 検出されたエンコーディング: {result.detected_encoding}'))
        
        # プレビュー結果を表示
        self._display_preview(result, verbose)
        
        # ドライランの場合はここで終了
        if dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('🔸 ドライランモードのため、インポートはスキップされました'))
            return
        
        # 有効な行がない場合は終了
        importable_count = result.valid_rows + result.warning_rows
        if importable_count == 0:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR('❌ インポート可能なデータがありません'))
            return
        
        # インポート確認
        self.stdout.write('')
        confirm = input(f'📥 {importable_count}件のデータをインポートしますか？ (y/N): ')
        if confirm.lower() != 'y':
            self.stdout.write(self.style.WARNING('インポートをキャンセルしました'))
            return
        
        # インポート実行
        self.stdout.write('')
        self.stdout.write(self.style.NOTICE('🚀 インポートを実行中...'))
        
        exec_result = importer.execute(
            session_id=session_id,
            skip_errors=skip_errors,
            skip_duplicates=skip_duplicates
        )
        
        # 結果を表示
        self._display_result(exec_result)
    
    def _display_preview(self, result, verbose=False):
        """プレビュー結果を表示"""
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('📊 プレビュー結果'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        self.stdout.write(f'  ファイル名:   {result.filename}')
        self.stdout.write(f'  総件数:       {result.total_rows}')
        self.stdout.write(f'  ✅ 有効:      {result.valid_rows}')
        self.stdout.write(f'  ⚠️  警告:     {result.warning_rows}')
        self.stdout.write(f'  🔄 重複:      {result.duplicate_rows}')
        self.stdout.write(f'  ❌ エラー:    {result.error_rows}')
        self.stdout.write('')
        
        # インポート可能件数
        importable_count = result.valid_rows + result.warning_rows
        self.stdout.write(f'  📥 インポート可能: {importable_count}件')
        self.stdout.write('')
        
        # 検出されたカラム
        if verbose:
            self.stdout.write(self.style.NOTICE('検出されたカラム:'))
            for col in result.columns_detected:
                self.stdout.write(f'  - {col}')
            self.stdout.write('')
        
        # エラー・警告の詳細
        error_rows = [r for r in result.rows if r.status == ImportStatus.ERROR]
        warning_rows = [r for r in result.rows if r.status == ImportStatus.WARNING]
        duplicate_rows = [r for r in result.rows if r.status == ImportStatus.DUPLICATE]
        
        if error_rows:
            self.stdout.write(self.style.ERROR('❌ エラー詳細:'))
            for row in error_rows[:10]:  # 最大10件表示
                self.stdout.write(f'  行{row.row_number}: {row.name or "(名称なし)"}')
                for error in row.errors:
                    self.stdout.write(f'    └─ {error}')
            if len(error_rows) > 10:
                self.stdout.write(f'  ... 他 {len(error_rows) - 10}件')
            self.stdout.write('')
        
        if warning_rows:
            self.stdout.write(self.style.WARNING('⚠️ 警告詳細:'))
            for row in warning_rows[:10]:
                self.stdout.write(f'  行{row.row_number}: {row.name}')
                for warning in row.warnings:
                    self.stdout.write(f'    └─ {warning}')
            if len(warning_rows) > 10:
                self.stdout.write(f'  ... 他 {len(warning_rows) - 10}件')
            self.stdout.write('')
        
        if duplicate_rows and verbose:
            self.stdout.write(self.style.WARNING('🔄 重複詳細:'))
            for row in duplicate_rows[:10]:
                self.stdout.write(f'  行{row.row_number}: {row.name} (既存ID: {row.duplicate_id})')
            if len(duplicate_rows) > 10:
                self.stdout.write(f'  ... 他 {len(duplicate_rows) - 10}件')
            self.stdout.write('')
        
        # 有効データのサンプル表示
        if verbose:
            valid_rows = [r for r in result.rows if r.status in [ImportStatus.VALID, ImportStatus.WARNING]]
            if valid_rows:
                self.stdout.write(self.style.SUCCESS('✅ 有効データサンプル (先頭5件):'))
                for row in valid_rows[:5]:
                    self.stdout.write(f'  行{row.row_number}: {row.name}')
                    self.stdout.write(f'    └─ {row.category} / {row.type}')
                    self.stdout.write(f'    └─ {row.address}')
                    self.stdout.write(f'    └─ ({row.latitude}, {row.longitude})')
                self.stdout.write('')
    
    def _display_result(self, result):
        """インポート結果を表示"""
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        if result.success:
            self.stdout.write(self.style.SUCCESS('✅ インポート完了'))
        else:
            self.stdout.write(self.style.ERROR('❌ インポート失敗'))
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        self.stdout.write(f'  📥 インポート: {result.imported_count}件')
        self.stdout.write(f'  ⏭️  スキップ:   {result.skipped_count}件')
        self.stdout.write(f'    └─ エラー:   {result.error_count}件')
        self.stdout.write(f'    └─ 重複:     {result.duplicate_count}件')
        self.stdout.write('')
        
        if result.errors:
            self.stdout.write(self.style.ERROR('エラー詳細:'))
            for error in result.errors[:10]:
                if 'row' in error:
                    self.stdout.write(f"  行{error['row']}: {error.get('error', error.get('message', ''))}")
                else:
                    self.stdout.write(f"  {error.get('message', str(error))}")
            if len(result.errors) > 10:
                self.stdout.write(f'  ... 他 {len(result.errors) - 10}件')
            self.stdout.write('')
        
        if result.success and result.created_ids:
            self.stdout.write(self.style.SUCCESS(f'作成されたID: {result.created_ids[:10]}'))
            if len(result.created_ids) > 10:
                self.stdout.write(f'  ... 他 {len(result.created_ids) - 10}件')
