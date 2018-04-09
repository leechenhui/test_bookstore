# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Passport',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('is_delete', models.BooleanField(verbose_name='删除标记', default=False)),
                ('create_time', models.DateTimeField(verbose_name='创建时间', auto_now_add=True)),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('username', models.CharField(verbose_name='用户名称', max_length=20)),
                ('password', models.CharField(verbose_name='用户密码', max_length=40)),
                ('email', models.EmailField(verbose_name='用户邮箱', max_length=254)),
                ('is_active', models.BooleanField(verbose_name='激活状态', default=False)),
            ],
            options={
                'db_table': 's_user_account',
            },
        ),
    ]
