from django.shortcuts import render, redirect, reverse
from django.views.generic import View
from .models import GoodsType, IndexGoodsBanner, IndexPromotion, GoodsSKU
from django.db.models import Q
from db.base_model import MyPaginator  # 自定义分页类


class IndexView(View):
    @staticmethod
    def get(request):
        # 获取商品种类信息
        types = GoodsType.objects.all()
        for _type in types:
            hots = GoodsSKU.objects.filter(Q(type=_type.id) & Q(is_delete=0)).order_by('-sales')[:4]
            abundant = GoodsSKU.objects.filter(Q(type=_type.id) & Q(is_delete=0)).order_by('sales')[:3]
            # 动态的为_type添加属性
            _type.hots = hots
            _type.abundant = abundant
        # 获取首页轮播图信息
        goods_banners = IndexGoodsBanner.objects.all().order_by('index')
        # 获取首页促销活动信息
        promotion_banners = IndexPromotion.objects.all().order_by('index')
        context = {
            'types': types,
            'goods_banners': goods_banners,
            'promotion_banners': promotion_banners,
        }
        return render(request, 'goods/index.html', context)


class DetailView(View):
    @staticmethod
    def get(request, good_id):
        # 通过id查找该该商品
        goods = GoodsSKU.objects.get(id=good_id)
        # 按照商品上架的时间降序排序
        new_products = GoodsSKU.objects.filter(type_id=goods.type_id).order_by('-create_time')[:2]
        # 添加用户浏览记录
        from django_redis import get_redis_connection
        connect = get_redis_connection('default')
        user_id = request.user.id
        history_id = f'history_{user_id}'
        connect.lpush(history_id, good_id)
        context = {
            'goods': goods,
            "new_products": new_products,
        }
        return render(request, 'goods/detail.html', context)


class ListView(View):
    @staticmethod
    def get(request, sort, page):
        new_products = GoodsSKU.objects.all().order_by('-create_time')[:3]  # 最新商品
        # 判断分类信息
        if sort == 'default':
            goods = GoodsSKU.objects.filter(is_delete=0).all()
        elif sort == 'price':
            goods = GoodsSKU.objects.filter(is_delete=0).order_by('-price')
        else:
            goods = GoodsSKU.objects.filter(is_delete=0).order_by('-sales')
        paginator = MyPaginator(goods, 15)  # 一页15条数据
        pages = paginator.page(page)
        context = {
            'new_products': new_products,
            'pages': pages,
            'sort': sort
        }
        return render(request, 'goods/list.html', context)


class SearchView(View):
    @staticmethod
    def get(request, page):
        content = request.session.get('content', '')  # 从缓存中获取搜索内容
        goods = GoodsSKU.objects.filter(is_delete=0).filter(Q(name__icontains=content) | Q(price__icontains=content))
        paginator = MyPaginator(goods, 15)
        pages = paginator.page(page)
        context = {
            'content': content,
            'pages': pages
        }
        return render(request, 'goods/search.html', context)

    @staticmethod
    def post(request, page):
        content = request.POST.get('content')  # 获取用户输入的内容
        request.session['content'] = content  # 将该内容存入缓存
        return redirect(reverse('goods:search', kwargs={'page': page}))
