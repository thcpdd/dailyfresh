import os
from celery import Celery
from django import setup
from django.conf import settings
from django.core.mail import send_mail

# 为worker调用项目配置信息
app = Celery('celery_tasks.tasks', broker='redis://127.0.0.1:6379/8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FreshEveryday.settings')
setup()


@app.task
def send_register_active_email(email, username, token):
    """注册邮件"""
    message = ''
    sender = settings.EMAIL_FROM
    receiver = [email]
    subject = '天天生鲜欢迎信息'
    html_msg = f'<h1>{username},欢迎您成为天天生鲜会员</h1>请点击下面链接激活您的账号</br><a href="http://127.0.0.1:8000/' \
               f'user/active/{token}">http://127.0.0.1:8000/user/active/{token}</a>'
    send_mail(subject, message, sender, receiver, html_message=html_msg)


@app.task
def send_forgot_password_email(email, username, code):
    """找回密码邮件"""
    message = ''
    sender = settings.EMAIL_FROM
    receiver = [email]
    subject = '天天生鲜-找回密码'
    html_msg = f'<h1>{username},系统检测到您申请了找回密码功能。</h1>' \
               f'</br>现在，我们将提供给您一个找回密码的凭证，请妥善保管好该凭证：<u><h3>{code}</h3></u>' \
               f'<p>该凭证将在一分钟后过期，请抓紧时间处理。</p>'
    send_mail(subject, message, sender, receiver, html_message=html_msg)
