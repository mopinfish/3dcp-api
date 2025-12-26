"""
cp_api/management/commands/generate_all_thumbnails.py

既存ムービーのサムネイルを一括生成するmanagementコマンド

使用方法:
    # 新規のみ（サムネイルがないムービーのみ）
    python manage.py generate_all_thumbnails
    
    # 全て強制再生成
    python manage.py generate_all_thumbnails --force
    
    # 特定のムービーIDのみ
    python manage.py generate_all_thumbnails --movie-id 123
"""

import time
from django.core.management.base import BaseCommand
from cp_api.models import Movie
from cp_api.services.thumbnail import generate_thumbnail_for_movie


class Command(BaseCommand):
    help = '全ムービーのサムネイルを生成'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='既存サムネイルも再生成',
        )
        parser.add_argument(
            '--movie-id',
            type=int,
            help='特定のムービーIDのみ処理',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には処理せず、対象となるムービーを表示',
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=1.0,
            help='各ダウンロード間の待機秒数（デフォルト: 1.0秒）',
        )

    def handle(self, *args, **options):
        force = options['force']
        movie_id = options['movie_id']
        dry_run = options['dry_run']
        delay = options['delay']
        
        self.stdout.write(self.style.NOTICE('🎬 サムネイル一括生成を開始します'))
        self.stdout.write(f'   オプション: force={force}, dry_run={dry_run}, delay={delay}s')
        
        # クエリセットを構築
        if movie_id:
            movies = Movie.objects.filter(id=movie_id)
        else:
            movies = Movie.objects.all()
        
        # Luma AI URLのみにフィルタリング
        movies = movies.filter(url__contains='lumalabs.ai')
        
        # forceでない場合はサムネイルがないものだけ
        if not force:
            movies = movies.filter(thumbnail='') | movies.filter(thumbnail__isnull=True)
        
        total = movies.count()
        
        if total == 0:
            self.stdout.write(self.style.WARNING('⚠️ 処理対象のムービーがありません'))
            return
        
        self.stdout.write(f'📊 処理対象: {total}件のムービー')
        
        if dry_run:
            self.stdout.write(self.style.NOTICE('🔍 Dry-run モード: 対象ムービーを表示します'))
            for movie in movies:
                self.stdout.write(f'   - Movie #{movie.id}: {movie.title or "(無題)"}')
                self.stdout.write(f'     URL: {movie.url}')
            return
        
        success = 0
        failed = 0
        skipped = 0
        
        for i, movie in enumerate(movies, 1):
            self.stdout.write(f'\n[{i}/{total}] Processing Movie #{movie.id}: {movie.title or "(無題)"}')
            self.stdout.write(f'   URL: {movie.url}')
            
            try:
                result = generate_thumbnail_for_movie(movie, force=force)
                
                if result:
                    success += 1
                    self.stdout.write(self.style.SUCCESS('   ✅ 生成成功'))
                    if movie.thumbnail:
                        self.stdout.write(f'   📁 保存先: {movie.thumbnail.name}')
                else:
                    failed += 1
                    self.stdout.write(self.style.ERROR('   ❌ 生成失敗'))
                    
            except Exception as e:
                failed += 1
                self.stdout.write(self.style.ERROR(f'   ❌ エラー: {e}'))
            
            # レート制限対策として待機
            if i < total:
                time.sleep(delay)
        
        # サマリー
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS(f'🎉 処理完了!'))
        self.stdout.write(f'   ✅ 成功: {success}件')
        self.stdout.write(f'   ❌ 失敗: {failed}件')
        self.stdout.write(f'   📊 合計: {total}件')
