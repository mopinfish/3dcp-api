"""
cp_api/views.py

文化財（CulturalProperty）とムービー（Movie）のViewSet

✅ 変更内容:
- 認証・権限設定を追加（IsAuthenticatedOrReadOnly）
- perform_createをオーバーライドしてcreated_byを自動設定
- perform_updateをオーバーライドして権限チェック
- /my/エンドポイントを追加（自分が作成したデータを取得）
- geomフィールドの自動生成処理を追加
- regenerate_thumbnailアクションを追加（サムネイル再生成）
- CSVインポートAPIを追加（プレビュー・実行）
- ✅ NEW: ordering_fieldsを追加（ソート機能）
- ✅ NEW: search_fieldsを追加（検索機能）
"""

import logging
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes as drf_permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.views import APIView
from django.contrib.gis.geos import Point
from django_filters.rest_framework import DjangoFilterBackend

from .models import Movie, CulturalProperty, Tag
from .serializers import (
    MovieSerializer, 
    CulturalPropertySerializer, 
    CulturalPropertyCreateSerializer,
    MovieCreateSerializer,
    TagSerializer
)
from .filters import CulturalPropertyFilter, MovieFilter
from .permissions import IsOwnerOrReadOnly
from .services.thumbnail import generate_thumbnail_for_movie
from .services.csv_importer import CulturalPropertyCSVImporter

logger = logging.getLogger(__name__)


class CulturalPropertyViewSet(viewsets.ModelViewSet):
    """
    文化財のCRUD操作を提供するViewSet
    
    - 一覧取得・詳細取得: 認証不要
    - 作成・更新・削除: 認証必須
    - 更新・削除: 作成者本人のみ
    
    ✅ 追加機能:
    - ordering: ソート（created_at, updated_at, name）
    - search: 検索（name, name_en, address）
    """
    queryset = CulturalProperty.objects.all().prefetch_related(
        'movies', 'images', 'tags', 'created_by'
    ).select_related('created_by')
    
    # フィルタリング・ソート・検索設定
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_class = CulturalPropertyFilter
    
    # ✅ ソート可能フィールド
    ordering_fields = ['created_at', 'updated_at', 'name', 'id']
    ordering = ['-updated_at']  # デフォルトのソート順
    
    # ✅ 検索可能フィールド
    search_fields = ['name', 'name_en', 'address', 'note']
    
    # 認証・権限設定
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_serializer_class(self):
        """
        アクションに応じてシリアライザーを切り替え
        """
        if self.action in ['create', 'update', 'partial_update']:
            return CulturalPropertyCreateSerializer
        return CulturalPropertySerializer

    def get_serializer_context(self):
        """
        シリアライザーにリクエストコンテキストを渡す
        """
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):
        """
        文化財作成時にcreated_byとgeomを自動設定
        """
        # リクエストデータから緯度・経度を取得
        latitude = self.request.data.get('latitude')
        longitude = self.request.data.get('longitude')
        
        # geomフィールドを生成
        geom = None
        if latitude and longitude:
            try:
                geom = Point(float(longitude), float(latitude), srid=6668)
            except (ValueError, TypeError):
                pass
        
        # geomが指定されていない場合はリクエストのgeomを使用
        if geom:
            serializer.save(created_by=self.request.user, geom=geom)
        else:
            serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        """
        文化財更新時にgeomを自動更新
        """
        latitude = self.request.data.get('latitude')
        longitude = self.request.data.get('longitude')
        
        if latitude and longitude:
            try:
                geom = Point(float(longitude), float(latitude), srid=6668)
                serializer.save(geom=geom)
            except (ValueError, TypeError):
                serializer.save()
        else:
            serializer.save()

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my(self, request):
        """
        自分が作成した文化財一覧を取得
        
        GET /api/cultural_property/my/
        """
        queryset = self.queryset.filter(created_by=request.user)
        
        # フィルタリングを適用
        queryset = self.filter_queryset(queryset)
        
        # ページネーション
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = CulturalPropertySerializer(
                page, many=True, context={'request': request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = CulturalPropertySerializer(
            queryset, many=True, context={'request': request}
        )
        return Response(serializer.data)


class MovieViewSet(viewsets.ModelViewSet):
    """
    ムービーのCRUD操作を提供するViewSet
    
    - 一覧取得・詳細取得: 認証不要
    - 作成・更新・削除: 認証必須
    - 更新・削除: 作成者本人のみ
    
    ✅ 追加機能:
    - ordering: ソート（created_at, updated_at, title）
    - search: 検索（title, note）
    - regenerate_thumbnail: サムネイルを再生成
    """
    queryset = Movie.objects.all().select_related(
        'cultural_property', 'created_by'
    )
    
    # フィルタリング・ソート・検索設定
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_class = MovieFilter
    
    # ✅ ソート可能フィールド
    ordering_fields = ['created_at', 'updated_at', 'title', 'id']
    ordering = ['-updated_at']  # デフォルトのソート順
    
    # ✅ 検索可能フィールド
    search_fields = ['title', 'note']
    
    # 認証・権限設定
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_serializer_class(self):
        """
        アクションに応じてシリアライザーを切り替え
        """
        if self.action in ['create', 'update', 'partial_update']:
            return MovieCreateSerializer
        return MovieSerializer

    def get_serializer_context(self):
        """
        シリアライザーにリクエストコンテキストを渡す
        """
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):
        """
        ムービー作成時にcreated_byを自動設定
        """
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my(self, request):
        """
        自分が作成したムービー一覧を取得
        
        GET /api/movie/my/
        """
        queryset = self.queryset.filter(created_by=request.user)
        
        # フィルタリングを適用
        queryset = self.filter_queryset(queryset)
        
        # ページネーション
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = MovieSerializer(
                page, many=True, context={'request': request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = MovieSerializer(
            queryset, many=True, context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def regenerate_thumbnail(self, request, pk=None):
        """
        サムネイルを再生成
        
        POST /api/movie/{id}/regenerate_thumbnail/
        
        権限: 作成者本人のみ
        """
        movie = self.get_object()
        
        # 権限チェック
        if movie.created_by and movie.created_by != request.user:
            return Response(
                {'error': '権限がありません'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # サムネイル生成
        success = generate_thumbnail_for_movie(movie, force=True)
        
        if success:
            # 最新のデータを取得
            movie.refresh_from_db()
            serializer = MovieSerializer(movie, context={'request': request})
            return Response({
                'message': 'サムネイルを再生成しました',
                'movie': serializer.data
            })
        else:
            return Response(
                {'error': 'サムネイル生成に失敗しました。Luma AIのURLを確認してください。'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TagViewSet(viewsets.ModelViewSet):
    """
    タグのCRUD操作を提供するViewSet
    """
    queryset = Tag.objects.all().prefetch_related('cultural_properties')
    serializer_class = TagSerializer
    filterset_fields = ['name']
    
    # タグは誰でも閲覧可能、作成・更新・削除は認証必須
    permission_classes = [IsAuthenticatedOrReadOnly]


# =============================================================================
# CSVインポートAPI
# =============================================================================

class CSVImportPreviewView(APIView):
    """
    CSVファイルをアップロードしてプレビューを取得
    
    POST /api/import/preview/
    
    リクエスト:
        - file: CSVファイル (multipart/form-data)
        - encoding: エンコーディング (オプション、デフォルト: utf-8)
        - check_duplicates: 重複チェック (オプション、デフォルト: true)
    
    レスポンス:
        - success: 成功フラグ
        - preview: プレビュー結果
        - session_id: セッションID（インポート実行時に使用）
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        logger.info(f"📥 CSVインポートプレビューリクエスト: user={request.user}")
        
        # ファイルを取得
        file = request.FILES.get('file')
        if not file:
            return Response(
                {'success': False, 'error': 'CSVファイルが指定されていません'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # ファイルサイズチェック（10MB制限）
        if file.size > 10 * 1024 * 1024:
            return Response(
                {'success': False, 'error': 'ファイルサイズが10MBを超えています'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # ファイル拡張子チェック
        if not file.name.lower().endswith('.csv'):
            return Response(
                {'success': False, 'error': 'CSVファイルのみアップロード可能です'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # パラメータを取得
        encoding = request.data.get('encoding', 'utf-8')
        check_duplicates = request.data.get('check_duplicates', 'true').lower() == 'true'
        
        try:
            # ファイル内容を読み込み
            file_content = file.read()
            
            # インポーターでプレビュー
            importer = CulturalPropertyCSVImporter(check_duplicates=check_duplicates)
            result, session_id = importer.preview(
                file_content=file_content,
                filename=file.name,
                encoding=encoding
            )
            
            return Response({
                'success': True,
                'preview': result.to_dict(),
                'session_id': session_id
            })
            
        except UnicodeDecodeError as e:
            logger.error(f"❌ エンコーディングエラー: {e}")
            return Response(
                {'success': False, 'error': f'ファイルのエンコーディングが不正です。{encoding}以外のエンコーディングを試してください。'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"❌ プレビューエラー: {e}")
            return Response(
                {'success': False, 'error': f'CSVの解析に失敗しました: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CSVImportExecuteView(APIView):
    """
    CSVインポートを実行
    
    POST /api/import/execute/
    
    リクエスト (JSON):
        - session_id: プレビュー時のセッションID (必須)
        - skip_errors: エラー行をスキップするか (オプション、デフォルト: true)
        - skip_duplicates: 重複行をスキップするか (オプション、デフォルト: true)
        - selected_rows: インポートする行番号のリスト (オプション)
    
    レスポンス:
        - success: 成功フラグ
        - result: インポート結果
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]
    
    def post(self, request):
        logger.info(f"🚀 CSVインポート実行リクエスト: user={request.user}")
        
        # パラメータを取得
        session_id = request.data.get('session_id')
        if not session_id:
            return Response(
                {'success': False, 'error': 'session_idが指定されていません'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        skip_errors = request.data.get('skip_errors', True)
        skip_duplicates = request.data.get('skip_duplicates', True)
        selected_rows = request.data.get('selected_rows')
        
        try:
            # インポーターでインポート実行
            importer = CulturalPropertyCSVImporter()
            result = importer.execute(
                session_id=session_id,
                user=request.user,
                skip_errors=skip_errors,
                skip_duplicates=skip_duplicates,
                selected_rows=selected_rows
            )
            
            return Response({
                'success': True,
                'result': result.to_dict()
            })
            
        except ValueError as e:
            logger.error(f"❌ インポートエラー: {e}")
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"❌ インポートエラー: {e}")
            return Response(
                {'success': False, 'error': f'インポートに失敗しました: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
