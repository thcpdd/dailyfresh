from django.urls import path
from .views import OrderPlaceView, OrderCommitView

app_name = 'order'
urlpatterns = [
    path('myorder', OrderPlaceView.as_view(), name='order'),  # 从购物车——>订单页面
    path('commit', OrderCommitView.as_view(), name='commit'),  # 提交订单
]
