# mysite/celery.py

from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# 设置Django的环境变量
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

app = Celery('mysite')

# 从Django的设置文件中加载CELERY配置
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现各个app下的tasks.py
app.autodiscover_tasks()
