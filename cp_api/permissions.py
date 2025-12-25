"""
cp_api/permissions.py

カスタム権限クラス

✅ 内容:
- IsOwnerOrReadOnly: 作成者本人のみ編集・削除可能
"""

from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    オブジェクトの作成者のみが編集・削除を許可する権限クラス
    
    - GET, HEAD, OPTIONS: 誰でもアクセス可能
    - PUT, PATCH, DELETE: created_byフィールドがリクエストユーザーと一致する場合のみ許可
    """

    def has_object_permission(self, request, view, obj):
        # 読み取り権限は誰でも許可
        if request.method in permissions.SAFE_METHODS:
            return True

        # created_byフィールドが存在しない場合は許可（後方互換性）
        if not hasattr(obj, 'created_by'):
            return True

        # created_byがNullの場合は許可（既存データの互換性）
        if obj.created_by is None:
            return True

        # 作成者本人かどうかをチェック
        return obj.created_by == request.user
