# Generated migration for adding created_by, created_at, updated_at fields

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    文化財（CulturalProperty）とムービー（Movie）モデルに
    created_by, created_at, updated_atフィールドを追加するマイグレーション
    """

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cp_api', '0001_initial'),
    ]

    operations = [
        # CulturalPropertyに created_by フィールドを追加
        migrations.AddField(
            model_name='culturalproperty',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='cultural_properties',
                to=settings.AUTH_USER_MODEL,
                verbose_name='作成者'
            ),
        ),
        # CulturalPropertyに created_at フィールドを追加
        migrations.AddField(
            model_name='culturalproperty',
            name='created_at',
            field=models.DateTimeField(
                auto_now_add=True,
                null=True,
                verbose_name='作成日時'
            ),
        ),
        # CulturalPropertyに updated_at フィールドを追加
        migrations.AddField(
            model_name='culturalproperty',
            name='updated_at',
            field=models.DateTimeField(
                auto_now=True,
                null=True,
                verbose_name='更新日時'
            ),
        ),
        
        # Movieに created_by フィールドを追加
        migrations.AddField(
            model_name='movie',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='movies',
                to=settings.AUTH_USER_MODEL,
                verbose_name='作成者'
            ),
        ),
        # Movieに created_at フィールドを追加
        migrations.AddField(
            model_name='movie',
            name='created_at',
            field=models.DateTimeField(
                auto_now_add=True,
                null=True,
                verbose_name='作成日時'
            ),
        ),
        # Movieに updated_at フィールドを追加
        migrations.AddField(
            model_name='movie',
            name='updated_at',
            field=models.DateTimeField(
                auto_now=True,
                null=True,
                verbose_name='更新日時'
            ),
        ),
        
        # MovieのForeignKeyをDO_NOTHINGからSET_NULLに変更
        migrations.AlterField(
            model_name='movie',
            name='cultural_property',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='movies',
                to='cp_api.culturalproperty',
                verbose_name='文化財'
            ),
        ),
        
        # CulturalPropertyの並び順を変更
        migrations.AlterModelOptions(
            name='culturalproperty',
            options={
                'ordering': ['-created_at', '-id'],
                'verbose_name': '文化財',
                'verbose_name_plural': '文化財'
            },
        ),
        # Movieの並び順を変更
        migrations.AlterModelOptions(
            name='movie',
            options={
                'ordering': ['-created_at', '-id'],
                'verbose_name': 'ムービー',
                'verbose_name_plural': 'ムービー'
            },
        ),
    ]
