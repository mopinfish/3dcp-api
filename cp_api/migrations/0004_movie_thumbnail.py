# Generated migration for adding thumbnail field to Movie model

from django.db import migrations, models
import cp_api.models


class Migration(migrations.Migration):

    dependencies = [
        ('cp_api', '0003_alter_imageupload_options_alter_tag_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='movie',
            name='thumbnail',
            field=models.ImageField(
                blank=True, 
                null=True, 
                upload_to=cp_api.models.thumbnail_upload_to, 
                verbose_name='サムネイル'
            ),
        ),
    ]
