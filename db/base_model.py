from django.db import models
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


class BaseModel(models.Model):
    """模型抽象基类"""
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记')

    class Meta:
        # 说明是一个抽象模型类
        abstract = True


# 封装分页功能
class MyPaginator:
    def __init__(self, object_list, per_page):
        self.paginator = Paginator(object_list, per_page)

    def page(self, _page):
        try:
            pages = self.paginator.page(_page)
        except EmptyPage:  # 用户访问的页数超出范围
            pages = self.paginator.page(self.paginator.num_pages)  # 返回最大页码数
        except PageNotAnInteger:  # 用户输入的页码不是一个整型
            pages = self.paginator.page(1)  # 返回第一页
        return pages
