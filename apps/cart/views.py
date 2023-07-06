"""
JsonResponse：
    用户点击了js函数绑定的标签，会先经过js发送一个ajax请求，这个请求会被响应的视图捕获，
视图经过业务处理后会返回一个JsonResponse，此时js代码会捕获这个响应并进行业务处理

购物车数据的存储：
    因为购物车需要频繁的访问数据库，因此使用redis来保存用户的购物车信息，这就需要用Python
来操作redis了

用到的redis方法：
    hset(name, key, value)  添加数据或者更新数据到redis中
    hvals(name)  获取所有值
    hdel(name, *keys)  删除数据
"""
from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from ..goods.models import GoodsSKU
from django.contrib.auth.mixins import LoginRequiredMixin
from django_redis import get_redis_connection


class CartAddView(View):
    @staticmethod
    def post(request):
        if not request.user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '请先登录再加入购物车'})
        goods_id = request.POST.get('goods_id')  # 商品id
        goods_count = request.POST.get('goods_count')  # 商品总数
        if not all([goods_id, goods_count]):
            return JsonResponse({'res': 0, 'errmsg': '数据不完整'})
        # 检验商品是否存在
        try:
            goods = GoodsSKU.objects.get(id=goods_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 0, 'errmsg': '商品不存在'})
        # 检验数量是否合法
        try:
            goods_count = int(goods_count)
        except ValueError:
            JsonResponse({'res': 0, 'errmsg': '非法数量'})
        # 核心业务处理
        connect = get_redis_connection("default")
        cart_key = f'cart_{request.user.id}'
        cart_count = connect.hget(cart_key, goods_id)  # 存在返回数量（字符串），不存在返回None
        if cart_count:
            goods_count += int(cart_count)
        # 检验商品库存
        if goods_count > goods.stock:
            return JsonResponse({'res': 0, 'errmsg': '商品库存不足'})
        # 更新或添加数据到redis中
        connect.hset(cart_key, goods_id, goods_count)
        # 计算购物车条目数（不是商品总数）
        cart_len = connect.hlen(cart_key)
        return JsonResponse({'res': 1, 'msg': '购物车添加成功', 'cart_len': cart_len})


class CartInfoView(LoginRequiredMixin, View):
    @staticmethod
    def get(request):
        cart_key = f'cart_{request.user.id}'
        connect = get_redis_connection('default')
        cart_dict = connect.hgetall(cart_key)  # 相当于一个字典
        goods = []  # 购物车中的所有商品
        total_count = 0  # 商品总数
        total_price = 0  # 总价钱
        for good_id, good_count in cart_dict.items():
            good = GoodsSKU.objects.get(id=int(good_id))
            good.count = int(good_count)  # 动态的给对象增加属性
            good.amount = good.price * int(good_count)  # 动态的给对象增加属性
            total_count += int(good_count)
            total_price += good.price
            goods.append(good)
        context = {
            'goods': goods,
            'total_count': total_count,
            'total_price': total_price,
        }

        return render(request, 'cart.html', context)


class UpdateCartView(View):
    @staticmethod
    def post(request):
        goods_id = request.POST.get('good_id')
        goods_count = request.POST.get('good_count')
        if not all([goods_id, goods_count]):
            return JsonResponse({'res': 0, 'errmsg': '数据不完整'})
        # 检验商品是否存在
        try:
            goods = GoodsSKU.objects.get(id=int(goods_id))
        except GoodsSKU.DoesNotExist:
            return JsonResponse({"res": 0, 'errmsg': '商品不存在'})
        # 检验数量是否合法
        try:
            goods_count = int(goods_count)
        except KeyError:
            return JsonResponse({'res': 0, 'errmsg': '非法数量'})
        # 判断库存是否足够
        if goods_count > goods.stock:
            return JsonResponse({'res': 0, 'errmsg': '商品库存不足'})
        # 核心业务处理
        cart_key = f'cart_{request.user.id}'
        connect = get_redis_connection('default')
        connect.hset(cart_key, goods.id, goods_count)  # 更新用户购物车
        # 计算商品总数
        values = connect.hvals(cart_key)  # 获取字典中的值，值就是每一件商品数量
        values = map(lambda x: int(x), values)
        cart_total = sum(values)

        return JsonResponse({'res': 1, 'msg': '数量修改成功', 'cart_total': cart_total})


class CartDeleteView(View):
    @staticmethod
    def post(request):
        goods_id = request.POST.get('good_id')
        if not goods_id:
            return JsonResponse({'res': 0, 'errmsg': '数据不完整'})
        try:
            GoodsSKU.objects.get(id=int(goods_id))
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 0, 'errmsg': '商品不存在'})
        # 核心业务处理
        connect = get_redis_connection('default')
        cart_key = f'cart_{request.user.id}'
        connect.hdel(cart_key, int(goods_id))
        # 计算删除后的商品总数
        values = connect.hvals(cart_key)  # 获取字典中的值，值就是每一件商品数量
        values = map(lambda x: int(x), values)
        cart_total = sum(values)

        return JsonResponse({'res': 1, 'msg': '商品删除成功', 'cart_total': cart_total})
