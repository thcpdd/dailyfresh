from django.urls import path
from .views import IndexView, DetailView, ListView, SearchView

app_name = 'goods'
urlpatterns = [
    path('', IndexView.as_view(), name='index'),  # 网站首页
    path('goods/detail/<int:good_id>', DetailView.as_view(), name='detail'),  # 商品详情页
    path('goods/list/<str:sort>/<int:page>', ListView.as_view(), name='list'),  # 商品列表页
    path('goods/search/<int:page>', SearchView.as_view(), name='search')  # 搜索
]
