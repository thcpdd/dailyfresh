from django.urls import path
from apps.user import views

app_name = 'user'
urlpatterns = [
    path('', views.UserInfoView.as_view(), name='user'),  # 用户中心
    path('register/', views.RegisterView.as_view(), name='register'),  # 注册
    path('login/', views.LoginView.as_view(), name='login'),  # 登录
    path('active/<str:token>', views.ActiveView.as_view(), name='active'),  # 激活
    path('order/<int:page>', views.UserOrderView.as_view(), name='order'),  # 订单
    path('address/', views.AddressView.as_view(), name='address'),  # 收货地址
    path('logout/', views.LogoutView.as_view(), name='logout'),  # 退出登录
    path('forgot/', views.ForgotPasswordView.as_view(), name='forgot'),  # 忘记密码
    path('check/', views.CheckCodeView.as_view(), name='check'),  # 检验验证码
    path('reset/', views.ResetPasswordView.as_view(), name='reset')  # 重置密码
]
