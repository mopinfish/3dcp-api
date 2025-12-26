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
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from django.contrib.gis.geos import Point

from .models import Movie, CulturalProperty, Tag
from .serializers import (
    MovieSerializer, 
    CulturalPropertySerializer, 
    CulturalPropertyCreateSerializer,
    MovieCreateSerializer,
    TagSerializer
)
from .filters import CulturalPropertyFilter
from .permissions import IsOwnerOrReadOnly
from .services.thumbnail import generate_thumbnail_for_movie


class CulturalPropertyViewSet(viewsets.ModelViewSet):
    """
    文化財のCRUD操作を提供するViewSet
    
    - 一覧取得・詳細取得: 認証不要
    - 作成・更新・削除: 認証必須
    - 更新・削除: 作成者本人のみ
    """
    queryset = CulturalProperty.objects.all().prefetch_related(
        'movies', 'images', 'tags', 'created_by'
    ).select_related('created_by')
    filterset_class = CulturalPropertyFilter
    filterset_fields = ['name', 'name_en', 'movies']
    
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
    - regenerate_thumbnail: サムネイルを再生成
    """
    queryset = Movie.objects.all().select_related(
        'cultural_property', 'created_by'
    )
    filterset_fields = ['title', 'cultural_property']
    
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
