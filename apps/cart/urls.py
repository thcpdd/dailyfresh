from django.urls import path
from .views import CartInfoView, CartAddView, UpdateCartView, CartDeleteView

app_name = 'cart'
urlpatterns = [
    path('mycart', CartInfoView.as_view(), name='cart'),  # 用户购物车页面
    path('add', CartAddView.as_view(), name='add'),  # 添加到购物车
    path('update', UpdateCartView.as_view(), name='update'),  # 在购物车页面添加或减少数据
    path('delete', CartDeleteView.as_view(), name='delete')  # 在购物车页面删除数据
]
