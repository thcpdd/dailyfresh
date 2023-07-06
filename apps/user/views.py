import re
from random import choice
from apps.user.models import User, Address
from django.shortcuts import render, redirect, HttpResponse, reverse
from django.core.exceptions import ObjectDoesNotExist
from django.views.generic import View
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.goods.models import GoodsSKU
from django.contrib.auth.hashers import make_password
from django.core import signing
# from celery_tasks.tasks import send_register_active_email, send_forgot_password_email  异步发送邮件


class BaseUserView:
    @staticmethod
    def send(email, username, token=None, code=None, mode=None):
        message = ''
        sender = settings.EMAIL_FROM
        receiver = [email]

        if mode == 'register':
            # 发送激活信息
            subject = '天天生鲜-欢迎信息'
            html_msg = f'<h1>{username},欢迎您成为天天生鲜会员</h1>请点击下面链接激活您的账号</br><a href="http://127.0.0.1:8000/' \
                       f'user/active/{token}">点此激活账号</a>'
            send_mail(subject, message, sender, receiver, html_message=html_msg)
        else:
            # 发送重置密码验证码
            subject = '天天生鲜-找回密码'
            html_msg = f'<h1>{username},系统检测到您申请了找回密码功能。</h1>' \
                       f'</br>现在，我们将提供给您一个找回密码的凭证，请妥善保管好该凭证：<u><h3>{code}</h3></u>' \
                       f'<p>该凭证将在两分钟后过期，请抓紧时间处理。</p>'
            send_mail(subject, message, sender, receiver, html_message=html_msg)

    @staticmethod
    def is_chinese(string):
        """判断用户名是否包含中文"""
        for content in string:
            if u'\u4e00' <= content <= u'\u9fff':
                return True
        return False

    @staticmethod
    def rand_code():
        """生成随机验证码"""
        chars = 'abcdefghijklmnopqrstuvwsyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        code = ''
        for _ in range(6):
            code += choice(chars)
        return code

    def __str__(self):
        return "用户视图基类"


class RegisterView(View, BaseUserView):
    @staticmethod
    def get(request):
        return render(request, 'user/register.html')

    def post(self, request):
        # 接收用户输入的数据
        username = request.POST.get('username')  # 用户名
        password = request.POST.get('pwd')  # 密码
        email = request.POST.get('email')  # 邮箱
        allow = request.POST.get('allow')  # 勾选框
        context = {
            'errmsg': '',
            'username': username,
            'email': email,
            'allow': allow,
            'password': password
        }
        # 判断用户名是否存在中文
        if self.is_chinese(username):
            context['errmsg'] = '用户名不能包含中文'
            return render(request, 'user/register.html', context)

        # 进行表单数据校验
        if not all([username, password, email]):
            context['errmsg'] = '数据不完整'
            return render(request, 'user/register.html', context)

        # 检验邮箱格式是否正确
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            context['errmsg'] = '邮箱格式不正确'
            return render(request, 'user/register.html', context)

        # 检验用户是否勾选用户协议
        if allow != 'on':
            context['errmsg'] = '请先勾选用户协议'
            return render(request, 'user/register.html', context)

        # 创建新用户
        # 判断用户名是否存在
        try:
            user = User.objects.get(username=username)  # 从数据库中尝试获取这个用户名
        except ObjectDoesNotExist:
            user = None

        if user:  # 用户名存在则返回错误信息
            context['errmsg'] = '用户名已存在'
            return render(request, 'user/register.html', context)

        user_info = User.objects.create_user(username, email, password)
        user_info.is_active = 0
        user_info.save()

        # 加密用户信息
        token = signing.dumps(user_info.id)
        request.session['token'] = token
        request.session.set_expiry(60*60*24)  # 设置缓存为24小时

        # 发送邮箱
        self.send(email=email, username=username, token=token, mode='register')
        # send_register_active_email.delay(email, username, token)  异步发送邮件

        # 注册完成后跳转至注册成功页面
        return render(request, 'user/register_success.html')

    def __str__(self):
        return "注册视图"


class ActiveView(View):
    @staticmethod
    def get(request, token):
        """激活用户"""
        try:  # 获取缓存中的token
            request.session['token']
        except KeyError:
            return HttpResponse('错误，检测不到该用户的激活信息或激活信息已过期')

        try:
            uid = signing.loads(token)
            user = User.objects.get(id=uid)
            user.is_active = 1
            user.save()
            request.session.flush()  # 清除激活信息
            return render(request, 'user/active_success.html')
        except ValueError:
            return HttpResponse('激活失败，请勿随机访问该页面')

    def __str__(self):
        return "激活用户视图"


class LoginView(View):
    @staticmethod
    def get(request):
        # 判断是否记住用户名
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            username = ''
            checked = ''
        return render(request, 'user/login.html', {'username': username, 'checked': checked})

    @staticmethod
    def post(request):
        username = request.POST.get('username')
        password = request.POST.get('pwd')

        if not all([username, password]):
            return render(request, 'user/login.html', {'errmsg': '请输入用户名或密码'})

        # 接收用户信息
        userinfo = authenticate(request, username=username, password=password)  # 返回用户对象

        # 判断用户是否存在
        if userinfo:
            # 判断是否激活
            if userinfo.is_active:  # 用户激活
                login(request, userinfo)
                next_url = request.GET.get('next', reverse('user:user'))
                response = redirect(next_url)  # 返回一个HttpResponse对象

                # 判断用户是否勾选“记住用户名”
                remember = request.POST.get('remember')  # 勾选返回’on‘，不勾选返回None
                if remember == 'on':
                    response.set_cookie('username', username, max_age=7*24*3600)  # 设置缓存为一个星期
                else:
                    response.delete_cookie('username')

                return response

            else:  # 用户未激活
                return render(request, 'user/login.html', {'errmsg': '用户未激活'})

        else:  # 用户不存在或者密码错误
            return render(request, 'user/login.html', {'errmsg': '用户名或密码错误', 'username': username})

    def __str__(self):
        return "登录视图"


class LogoutView(View):
    @staticmethod
    def get(request):
        logout(request)  # 退出登录并清除cookie信息
        return redirect(reverse('goods:index'))  # 重定向至首页

    def __str__(self):
        return "退出登录视图"


class UserInfoView(LoginRequiredMixin, View):
    @staticmethod
    def get(request):
        # request.user.is_authenticated()
        # 验证登录情况，用户未登录，返回AnonymousUser，即False
        # 登录成功返回User，即True

        user = request.user  # 获取当前登录的用户名
        default_address = Address.objects.get_default_address(user)  # 获取默认地址

        # 访问用户浏览历史记录
        from django_redis import get_redis_connection
        connect = get_redis_connection('default')
        history_id = f'history_{user.id}'

        sku_ids = connect.lrange(history_id, 0, 4)  # 获取前5条浏览记录

        # 从数据库获取用户最近浏览的商品信息
        GoodsSKU.objects.filter(id__in=sku_ids)  # 过滤信息
        goods_li = []  # 储存商品信息
        for _id in sku_ids:
            goods = GoodsSKU.objects.get(id=_id)
            goods_li.append(goods)

        context = {
            'page': 'user',
            'default_address': default_address,
            'goods_li': goods_li
        }
        return render(request, 'user/user_center_info.html', context)

    def __str__(self):
        return "处理用户信息视图"


class UserOrderView(LoginRequiredMixin, View):
    @staticmethod
    def get(request, page):
        from apps.order.models import OrderGoods, OrderInfo
        user_id = request.user.id
        orders = OrderInfo.objects.filter(user_id=user_id)  # 查询该用户的所有订单
        user_orders = []  # 用户所有订单
        order_status = OrderInfo.ORDER_STATUS
        for order in orders:
            goods_orders = OrderGoods.objects.filter(order_info_id=order.order_id)
            for goods_order in goods_orders:
                # 动态的为对象增加属性
                goods_order.status = order_status[goods_order.order_info.status]
                goods_order.amount = goods_order.price * goods_order.count
            user_orders.append(goods_orders)
        from db.base_model import MyPaginator
        paginator = MyPaginator(user_orders, 2)  # 一页两个订单
        pages = paginator.page(page)
        context = {
            'page': 'order',
            'user_orders': user_orders,
            'pages': pages
        }
        return render(request, 'user/user_center_order.html', context)


class AddressView(LoginRequiredMixin, View):
    @staticmethod
    def get(request):
        """进入网页时获取用户默认收获地址"""
        user = request.user  # 获取用户名
        # 尝试获取默认地址
        default_address = Address.objects.get_default_address(user)
        context = {
            'page': 'address',
            'address': default_address
        }
        return render(request, 'user/user_center_site.html', context)

    @staticmethod
    def post(request):
        """用户提交收货地址"""
        receiver = request.POST.get('receiver')  # 获取收件人
        address = request.POST.get('address')  # 获取收货地址
        zip_code = request.POST.get('zip_code')  # 获取邮编
        phone = request.POST.get('phone')  # 获取手机号
        context = {
            "errmsg": '',
            'address': address,
            'zip_code': zip_code,
            'phone': phone,
            'receiver': receiver
        }
        # 检验数据是否完整
        if not all([receiver, address, phone]):
            context['errmsg'] = '数据不完整'
            return render(request, 'user/user_center_site.html', context)

        # 检验邮编是否正确
        if len(zip_code) != 6:
            context['errmsg'] = '邮编格式不正确'
            return render(request, 'user/user_center_site.html', context)

        # 检验手机号格式是否正确
        if not re.match(r'^1[3-9][0-9]{9}', phone):
            context['errmsg'] = '手机号格式不正确'
            return render(request, 'user/user_center_site.html', context)

        user = request.user  # 获取用户名

        # 尝试获取默认地址
        default_address = Address.objects.get_default_address(user)

        if default_address:  # 如果存在默认地址，那么当前地址设置为非默认地址
            is_default = False
        else:
            is_default = True

        # 添加地址
        Address.objects.create(user=user, receiver=receiver, addr=address, zip_code=zip_code, phone=phone,
                               is_default=is_default)

        return redirect(reverse('user:address'))

    def __str__(self):
        return "处理收货地址视图"


class ForgotPasswordView(View, BaseUserView):
    @staticmethod
    def get(request):
        return render(request, 'user/forgot.html')

    def post(self, request):
        username = request.POST.get('username')
        email = request.POST.get('email')

        # 校验数据是否完整
        if not all([username, email]):
            return render(request, 'user/forgot.html', {'errmsg': '数据不完整'})

        # 判断用户名是否存在
        try:
            user = User.objects.get(username=username)
            if user.is_superuser:
                return render(request, 'user/forgot.html', {'errmsg': '您没有权限修改超级管理员的信息'})
        except ObjectDoesNotExist:
            return render(request, 'user/forgot.html', {'errmsg': '用户名不存在'})

        if email != user.email:
            return render(request, 'user/forgot.html', {'errmsg': '当前输入的邮箱与该用户注册时的邮箱不匹配'})

        code = self.rand_code()  # 产生随机验证码

        # 记录缓存信息
        request.session['code'] = code
        request.session['username'] = username
        request.session.set_expiry(120)  # 设置缓存将在120秒后过期

        self.send(email, username, code=code, mode='reset')  # 将验证码发送给指定邮箱
        # send_forgot_password_email.delay(email, username, code)  异步发送邮件
        return redirect(reverse('user:check'))  # 重定向至校验验证码页面

    def __str__(self):
        return '找回密码发送邮箱验证码'


class CheckCodeView(View):
    @staticmethod
    def get(request):
        try:
            request.session['code']
        except KeyError:  # 若未能从会话中获取验证码，那么返回错误页面
            return HttpResponse('错误，您当前没有访问该网页的权限')

        return render(request, 'user/check.html')

    @staticmethod
    def post(request):
        try:  # 获取系统发送的验证码
            code = request.session['code']
        except KeyError:
            return render(request, 'user/check.html', {'errmsg': '校验码已超过有效期，请重试'})

        yz_code = request.POST.get('yz_code')  # 获取用户输入的验证码

        if not yz_code:
            return render(request, 'user/check.html', {'errmsg': '请输入校验码'})

        if yz_code == code:
            request.session['check'] = True  # 验证码正确则通过校验
            return redirect(reverse('user:reset'))  # 验证码正确则跳转到重置密码页面
        else:
            return render(request, 'user/check.html', {'errmsg': '校验码不正确'})

    def __str__(self):
        return "校验验证码视图"


class ResetPasswordView(View):
    @staticmethod
    def get(request):
        try:
            request.session['check']
        except KeyError:  # 若未能从会话中获取检验信息，即用户未填写验证码或验证码错误，那么将不能提前访问该网站
            return HttpResponse('错误，请先通过验证码校验页面再访问此网站')

        return render(request, 'user/reset_password.html')

    @staticmethod
    def post(request):
        try:
            request.session['check']
        except KeyError:  # 若未能从会话中获取检验信息，则代表缓存已过期，用户需重新操作
            return render(request, 'user/reset_password.html', {'errmsg': '用户信息已过期，请重试'})

        username = request.session['username']  # 获取缓存中的用户名
        user_info = User.objects.get(username=username)  # 从数据库中访问该用户名对应的用户信息

        new_password = request.POST.get('pwd')  # 获取用户输入的新密码
        c_new_password = request.POST.get('cpwd')  # 获取用户第二次输入的新密码

        if new_password != c_new_password:
            return render(request, 'user/reset_password.html', {'errmsg': '两次输入的密码不一致'})

        user_info.password = make_password(new_password)  # 加密密码并替换数据库原有的值
        user_info.save()

        request.session.flush()  # 清除会话保存的验证码和用户信息

        return render(request, 'user/reset_success.html')

    def __str__(self):
        return '重置密码'
