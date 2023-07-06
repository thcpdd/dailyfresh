from django.contrib import admin
from .models import GoodsType, Goods, GoodsSKU, GoodsImage, IndexGoodsBanner, IndexPromotion, IndexCreatoryGoods

# Register your models here.
admin.site.register(GoodsType)
admin.site.register(Goods)
admin.site.register(GoodsSKU)
admin.site.register(GoodsImage)
admin.site.register(IndexGoodsBanner)
admin.site.register(IndexPromotion)
admin.site.register(IndexCreatoryGoods)
