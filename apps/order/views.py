"""
订单的业务逻辑：
    1、事务：当一个订单异常的时候，应该选择用事务来回滚，而不是将异常的数据存入数据库中，
在Django中，使用transaction来启动事务。

    2、下单并发：在处理订单并发的时候，通常有两种解决方案，第一种是悲观锁，第二种是乐观锁

        悲观锁：悲观锁指的就是当一个用户查询了一个商品时，对这个操作加上一把锁，那么在Mysql中，
    加锁的对应语句是：select * from table where id=id (for update)，此时只有当用户拿到了这把锁，
    该用户才能对这个数据进行操作，否则都需要等到前面一个用户完成订单（锁被释放）之后，才能进行操作数据。
    上述sql语句翻译成Django语句就是：模型类名.objects.select_for_update().get(id=id)

        乐观锁：乐观锁指的是在查询的时候不加锁，但是等到我要修改数据的时候，对数据进行判断，判断的依据是：
    先获取商品原来的库存，再对数据进行查询，若能够查询到数据，则说明没有人和抢这个资源；若不能查询到数据，就说明
    同时有另一个人在跟我竞争这个资源，则下单失败。
        对应的Mysql语句为：select * from table set stock=new_stock sales=new_sales where id=id stock=origin_stock
        翻译成Django语句：模型类名.objects.filter(id=id, stock=origin_stock).update(stock=new_stock, sales=new_sales)
        这样会返回受影响的行数，也就是说，要么返回1，要么返回0。
        在乐观锁中，我们通常会给用户三次机会来尝试下单，若3次都不能下单成功，则最后判定为下单失败

    综上所述：
        1、不管是乐观锁还是悲观锁，都存在一个运气的成分在里面
        2、乐观锁适用于冲突较少的情景（冲突较多则存在大量的循环，浪费资源）
        3、悲观锁适用于冲突较多的情景

"""
from django.shortcuts import render, redirect, reverse
from django.views import View
from ..user.models import Address
from ..goods.models import GoodsSKU
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from .models import OrderInfo, OrderGoods
from django_redis import get_redis_connection
from django.db import transaction  # 绑定事务


class OrderPlaceView(LoginRequiredMixin, View):
    @staticmethod
    def post(request):
        # 接受参数
        sku_ids = request.POST.getlist('sku_id')
        # 没有接受到数据什么都不做
        if not sku_ids:
            return redirect(reverse('cart:cart'))
        user_id = request.user.id
        # 获取用户所有收货地址
        address = Address.objects.filter(user_id=user_id).all()
        # 核心业务处理
        skus = []  # 所有已勾选的商品
        total_count = 0  # 商品总数
        total_price = 0  # 商品总价格
        cart_id = f'cart_{request.user.id}'  # 购物车id
        connect = get_redis_connection('default')
        for sku_id in sku_ids:
            sku = GoodsSKU.objects.get(id=int(sku_id))
            price = sku.price
            count = int(connect.hget(cart_id, sku_id))
            amount = price * count
            # 动态的为对象增加属性
            sku.count = count
            sku.amount = amount
            total_price += amount
            total_count += count
            skus.append(sku)

        transport_fare = 10  # 没有写运费这个子系统，所以运费写死
        total_pay = transport_fare + total_price  # 实际付款

        context = {
            'address': address,
            'skus': skus,
            'total_price': total_price,
            'total_count': total_count,
            'transport_fare': transport_fare,
            'total_pay': total_pay,
            'sku_ids': sku_ids
        }
        return render(request, 'place_order.html', context)


class OrderCommitView(View):
    @staticmethod
    @transaction.atomic  # 绑定该函数中的事务
    def post(request):
        if not request.user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})
        sku_ids = eval(request.POST.get('sku_ids'))  # 获取当前页面的所有商品id
        addr_id = request.POST.get('addr_id')  # 获取收货地址id
        pay_method = request.POST.get('pay_method')
        # 校验数据是否完整
        if not all([sku_ids, addr_id, pay_method]):
            return JsonResponse({'res': 0, 'errmsg': '数据不完整'})
        # 校验支付方式
        if pay_method not in OrderInfo.PAY_METHOD.keys():
            return JsonResponse({'res': 0, 'errmsg': '非法的支付方式'})
        # 校验地址是否存在
        try:
            Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res': 0, 'errmsg': '地址不存在'})
        # 核心业务处理
        total_count = 0
        total_price = 0
        user = request.user
        cart_id = f'cart_{user.id}'
        from time import time
        from datetime import datetime
        order_id = str(int(time())) + str(user.id)  # 订单id
        trade_no = datetime.now().strftime('%Y%m%d%H%M%S') + str(user.id)  # 交易编号
        save_id = transaction.savepoint()  # 事务保存点
        try:
            # 更新订单信息表
            order = OrderInfo.objects.create(
                order_id=order_id,
                addr_id=addr_id,
                user_id=user.id,
                pay_methods=pay_method,
                total_count=total_count,
                total_price=total_price,
                transit_price=10,
                trade_no=trade_no
            )
            connect = get_redis_connection('default')
            # 更新商品订单表
            for sku_id in sku_ids:
                try:
                    goods = GoodsSKU.objects.select_for_update().get(id=sku_id)  # 悲观锁
                except GoodsSKU.DoesNotExist:
                    transaction.rollback(save_id)  # 回滚到保存点的位置
                    return JsonResponse({'res': 0, 'errmsg': '商品不存在'})

                count = int(connect.hget(cart_id, sku_id))
                # 商品库存不足
                if count > goods.stock:
                    transaction.rollback(save_id)  # 回滚到保存点的位置
                    return JsonResponse({'res': 0, 'errmsg': '商品库存不足'})

                OrderGoods.objects.create(
                    order_info=order,
                    goods_sku=goods,
                    count=count,
                    price=goods.price
                ).save()
                goods.stock -= count  # 更新库存
                goods.sales += count  # 更新销量
                goods.save()
                total_count += count
                total_price += count * goods.price
            # 修改订单中的商品总数、商品总价并保存
            order.total_count = total_count
            order.total_price = total_price
            order.save()
        except (Exception, ):
            transaction.rollback(save_id)  # 回滚到保存点的位置
            return JsonResponse({'res': 0, 'errmsg': '订单异常'})
        # 提交事务
        transaction.savepoint_commit(save_id)
        # 删除购物车中的数据
        connect.hdel(cart_id, *sku_ids)
        return JsonResponse({'res': 1, 'msg': '订单提交成功'})
