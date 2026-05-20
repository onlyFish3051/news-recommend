from datetime import timezone, date

from decimal import Decimal, ROUND_HALF_UP

from django import forms
from django.db.models import Max, F, ExpressionWrapper, Count
from django.db.models.functions import Coalesce
from django.forms import FloatField
from django.http import JsonResponse
from django.shortcuts import render, redirect
from datetime import datetime, timedelta
from django.utils import timezone
from appnewsre import models
from appnewsre.models import News, Newstype, Newsrecommend, Newscomment, Userread, User, Newssee, Collection, Like, Img, \
    Userclouds, Uservisit, Province
from django.utils.safestring import mark_safe

from djangoProject01 import settings


# 定义一个函数来处理新闻内容，每隔三个句号插入换行符
# 在视图中处理 selectnews.newscontent，每隔五个中文句号插入换行符并缩进每个小段的第一行
def insert_line_breaks(news_content):  # 每隔4个中文句号分一段
    # 每隔4个中文句号分一段
    segments = []
    segment = ""
    count = 0
    for char in news_content:
        if char in ['。', '！', '？', '”']:  # 假设中文句号、叹号和问号表示句子结束
            count += 1
            segment += char
            if count % 6 == 0:
                segments.append(segment)
                segment = ""
                count = 0  # 重置计数器
        else:
            segment += char
    if segment:
        segments.append(segment)

        # 添加首行缩进（每段第一行缩进两个空格）
    indented_segments = []
    for segment in segments:
        lines = segment.split('\n')
        indented_lines = ['  ' + line if i == 0 else line for i, line in enumerate(lines)]  # 首行缩进两个空格
        indented_segment = '\n'.join(indented_lines)
        indented_segments.append(indented_segment)

        # 返回处理后的新闻内容
    formatted_content = '\n\n'.join(indented_segments)
    return formatted_content


class LoginForm(forms.Form):
    username = forms.CharField(
        label='用户账号',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '账号'}),
        required=True
    )
    password = forms.CharField(
        label='密码',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '密码'}, render_value=True),
        required=True
    )


# def clean_password(self):
#     self.cleaned_data("password")
#     return md5(passwd)
# Create your views here.(View):
# 登录模块
def login(request):
    if request.method == "GET":
        form = LoginForm()
        return render(request, 'login.html', {'form': form})
    # 获取请求
    form = LoginForm(data=request.POST)
    if form.is_valid():
        # print(form.cleaned_data)
        # 来验证账号密码
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        user_obj = models.User.objects.filter(uid=username, passwd=password).first()
        if (not user_obj):
            # 不正确情况
            form.add_error('password', "用户名或密码错误")
            return render(request, 'login.html', {'form': form})
        # 用户名和密码正确
        request.session['info'] = {'uid': user_obj.uid, 'uname': user_obj.uname}
        # 在session中存储登录时间戳
        request.session['login_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if (user_obj.usertype == 1) or (user_obj.usertype == 2):
            today = datetime.today()
            all_news = News.objects.all()
            for news in all_news:
                # news_date = datetime.strptime(news.newsdate, '%Y-%m-%d')  # Assuming the date format is 'YYYY-MM-DD'
                days_difference = (today - news.newsdate).days
                timeliness = 100 - days_difference
                news.timeliness = timeliness
                news.save()
            info_dict = request.session["info"]
            nowdate = datetime.now().strftime('%Y-%m-%d')
            # 判断数据库表中是否有今天的访问记录
            uservisit_exists = Uservisit.objects.filter(datetime=nowdate).exists()
            if not uservisit_exists:
                createuservisit = Uservisit.objects.create(datetime=nowdate, count=1)
            else:
                updateuservisit = Uservisit.objects.filter(datetime=nowdate).update(count=F('count') + 1)

            # 判断数据库中是否包含
            userreadobj_exists = Userread.objects.filter(uid=info_dict['uid'], datetime=nowdate).exists()
            if not userreadobj_exists:
                createuserread = Userread.objects.create(uid=info_dict['uid'], datetime=nowdate)
                # 每一次进入系统就重新计算一遍该用户的basefire值
            info_dict = request.session["info"]
            news_recommends = Newsrecommend.objects.filter(uid=info_dict['uid'])
            for news_recommend in news_recommends:
                # 2.1 获取与之关联的appnewsre_news对象
                news = news_recommend.news  # 假设news是AppnewsreNewsrecommend到AppnewsreNews的外键字段

                # 2.2 计算新的basefire值(推荐指数调节)
                new_basefire = news.timeliness * 0.3 + news.seetimes * 0.10 + news.likenumbers * 0.15 + news.commentnumbers * 0.3 + news.collectionnumbers * 0.15

                # 3. 更新appnewsre_newsrecommend对象的refire字段
                news_recommend.basefire = new_basefire
                news_recommend.save()
            # 给每一类下面的新闻的addfire字段值统一
            # 定义cid的范围
            cid_range = range(1, 9)  # 包含1到8的整数
            # 遍历cid范围，为每个cid设置addfire的最大值
            for cid in cid_range:
                # 找到当前cid下addfire的最高值
                max_addfire = \
                    Newsrecommend.objects.filter(cid=cid, uid=info_dict['uid']).aggregate(max_addfire=Max('addfire'))[
                        'max_addfire']

                # 如果找到了addfire的最大值（即存在相关记录），则更新所有该cid下的新闻的addfire值
                if max_addfire is not None:
                    Newsrecommend.objects.filter(cid=cid, uid=info_dict['uid']).update(addfire=max_addfire)
                else:
                    # 如果没有找到addfire的最大值（即该cid下没有相关记录），可以选择打印一条消息或进行其他处理
                    print(f"No Newsrecommend records found for cid: {cid}")
            return redirect("/mainpage/0")
        else:
            # 计算一周前的日期
            one_week_ago = timezone.now() - timedelta(days=7)
            # 删除超过一周的记录
            Uservisit.objects.filter(datetime__lt=one_week_ago).delete()
            return redirect("/manage_base/")
    return render(request, 'login.html', {'form': form})


def logout(request):
    info_dict = request.session["info"]
    uid = info_dict['uid']
    login_time_str = request.session.get('login_time')
    if login_time_str:
        login_time = datetime.strptime(login_time_str, '%Y-%m-%d %H:%M:%S')
        logout_time = datetime.now()
        duration = (logout_time - login_time).total_seconds() / 60  # 转换为分钟
        duration = int(duration)
        # 更新阅读的时间
        current_time = datetime.now().strftime('%Y-%m-%d')
        updateuserread = Userread.objects.filter(uid=uid, datetime=current_time).update(
            readtime=F('readtime') + duration)
        # 更新session中login_time的值
        current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # 将当前时间戳字符串保存到session中
        request.session['login_time'] = current_time_str
        print(f"User stayed for {duration:.2f} minutes today.")
    request.session.clear()
    return redirect("/login/")


# 主界面
def mainpage(request, cid=0):
    # 检查用户是否登录，如果已登陆就继续接下来的操作
    # 用户发来的请求，获取cookie随机字符串，拿着随机字符串看看session中有没有
    # info = request.session.get('info')
    # if not info:
    #     return redirect("/login/")
    #
    info_dict = request.session["info"]
    # info_dict['uid'] info_dict['uname'] info_dict['uimg']
    # 获取用户感兴趣的新闻类型
    if request.method == 'POST':
        selected_img_url = request.POST.get('selectedImgUrl', '')
        selected_cid_list = selected_img_url.split(',')
        selected_cid_list = [int(cid) for cid in selected_cid_list if cid.isdigit()]  # 确保列表中的元素都是整数

        max_basefire = Newsrecommend.objects.aggregate(Max('basefire'))['basefire__max']-5
        # 使用Django ORM的F表达式来在数据库层面实现addfire字段的递增
        Newsrecommend.objects.filter(uid=info_dict['uid'], cid__in=selected_cid_list).update(addfire=F('addfire') + max_basefire)
        # 更新该用户类型
        Userupdate = User.objects.filter(uid=info_dict['uid']).update(usertype=1)

    # 搜索
    value = request.GET.get('q')
    if value:
        return redirect("/search/?q={}".format(value))

    # 计算并更新新闻推荐列表中的推荐指数refire字段

    # 现在来获取该名用户的推荐新闻
    # 定义页码
    page = int(request.GET.get('page', 1))
    page_size = 8
    start = (page - 1) * page_size
    end = page * page_size
    # 记录总数
    renews_count = Newsrecommend.objects.filter(uid=info_dict['uid']).select_related('news').all().count()
    # 计算refire
    # 使用Django ORM的F表达式来计算refire的新值，并更新所有匹配uid的记录

    max_basefire_value = Newsrecommend.objects.filter(uid=info_dict['uid']).aggregate(Max('basefire'))[
                             'basefire__max'] or 0
    # max_basefire = max_basefire_value * 1.10
    max_basefire=max_basefire_value*1.12
    # 更新所有记录的cos字段：
    for news_recommend in Newsrecommend.objects.filter(uid=info_dict['uid']):
        original_cos = Decimal(news_recommend.basefire) / Decimal(str(max_basefire)).quantize(Decimal('0.01'),
                                                                                              rounding=ROUND_HALF_UP)
        # 应用线性变换将cos值映射到-1到1的范围
        new_cos = original_cos * 2 - 1
        news_recommend.cos = new_cos.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)  # 保持两位小数
        news_recommend.save()
    Newsrecommend.objects.filter(uid=info_dict['uid']).update(refire=F('basefire')+ F('addfire')*0.3 + F('cos') * 10)
    # 获取登录uid的NewsRecommend对象所推荐的所有Newsrecommend对象，并按refire字段降序排序
    renews = Newsrecommend.objects.filter(uid=info_dict['uid']).select_related('news').all().order_by('-refire')[
             start:end]
    renews_page_count, div = divmod(renews_count, page_size)
    # 计算页码
    if div:
        renews_page_count += 1
    plus = 2
    if renews_page_count <= 2 * plus + 1:
        start_page = 1
        end_page = renews_page_count
    else:
        if page <= plus:
            start_page = 1
            end_page = 2 * plus + 1
        else:
            start_page = page - plus
            end_page = page + plus
    page_str_list_1 = []

    # 上一页
    if page > 1:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">上一页</a></li>'.format(page - 1)
    else:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">上一页</a></li>'.format(1)
    page_str_list_1.append(prev)
    # 页面
    for i in range(start_page, end_page + 1):
        if i == page:
            ele = '<li class="page-item active" ><a class="page-link" href="?page={}">{}</a></li>'.format(i, i)
        else:
            ele = '<li class="page-item " ><a class="page-link" href="?page={}">{}</a></li>'.format(i, i)
        page_str_list_1.append(ele)
    # 下一页
    if page < renews_page_count:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">下一页</a></li>'.format(page + 1)
    else:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">下一页</a></li>'.format(renews_page_count)
    page_str_list_1.append(prev)

    page_str_re = mark_safe(''.join(page_str_list_1))
    cid = int(cid)
    # 获取全部类别信息
    typelist = Newstype.objects.all()
    # 获取某个类别下的所有新闻
    # 1.根据用户想要访问的页码
    # 1.1分页
    page = int(request.GET.get('page', 1))
    page_size = 8
    start = (page - 1) * page_size
    end = page * page_size
    # 更新fire的值
    class_firenews = News.objects.all().update(
        class_fire=ExpressionWrapper(
            F('timeliness') * 0.8 +
            F('seetimes') * 0.05 +
            F('likenumbers') * 0.05 +
            F('collectionnumbers') * 0.1 +
            F('commentnumbers') * 0.1,
            output_field=FloatField()))
    newslist = News.objects.filter(cid=cid).order_by('-class_fire')[start:end]
    # 记录总数
    newslist_count = News.objects.filter(cid=cid).order_by('seetimes').count()
    firenews = News.objects.all().update(
        fire=ExpressionWrapper(
            F('timeliness') * 0.99 + F('seetimes') * 0.01,
            output_field=FloatField()))
    toplist = News.objects.filter(timeliness__gte=80).order_by('-fire')
    newslist_page_count, div = divmod(newslist_count, page_size)
    # 计算页码
    # 计算页码
    if div:
        newslist_page_count += 1
    # 计算前后两页的页码
    # 计算页码
    plus = 2
    if newslist_page_count <= 2 * plus + 1:
        start_page = 1
        end_page = newslist_page_count
    else:
        if page <= plus:
            start_page = 1
            end_page = 2 * plus + 1
        else:
            # 当前页>2
            if (page + plus) > newslist_page_count:
                start_page = newslist_page_count - 2 * plus
                end_page = newslist_page_count
            else:
                start_page = page - plus
                end_page = page + plus
    # 将页面的组件嵌入到html中

    page_str_list = []
    # 上一页
    if page > 1:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">上一页</a></li>'.format(page - 1)
    else:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">上一页</a></li>'.format(1)
    page_str_list.append(prev)
    # 中间页码
    for i in range(start_page, end_page + 1):
        if i == page:
            ele = '<li class="page-item active" ><a class="page-link" href="?page={}">{}</a></li>'.format(i, i)
        else:
            ele = '<li class="page-item " ><a class="page-link" href="?page={}">{}</a></li>'.format(i, i)
        page_str_list.append(ele)
    # 下一页
    if page < newslist_page_count:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">下一页</a></li>'.format(page + 1)
    else:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">下一页</a></li>'.format(newslist_page_count)
    page_str_list.append(prev)
    page_str_commom = mark_safe(''.join(page_str_list))

    userinfoobj = User.objects.filter(uid=info_dict['uid']).first()

    return render(request, 'mainpage.html',
                  {'toplist': toplist, 'typelist': typelist, 'newslist': newslist, 'currentcid': cid, 'renews': renews,
                   'page_str_commom': page_str_commom, 'page_str_re': page_str_re, 'userinfoobj': userinfoobj})


# 这是一个简单的函数，用于判断用户是否已收藏了某条新闻
def is_user_collected(uid, newsid):
    try:
        Collection.objects.get(news_id=newsid, uid=uid)
        return True
    except Collection.DoesNotExist:
        return False


# 这是一个简单的函数，用于判断用户是否已喜欢了某条新闻
def is_user_liked(uid, newsid):
    try:
        Like.objects.get(news_id=newsid, uid=uid)
        return True
    except Like.DoesNotExist:
        return False


# 某一个页面
def newsdetails(request, newsid):
    info_dict = request.session["info"]
    userinfoobj = User.objects.filter(uid=info_dict['uid']).first()
    # 跳转到搜索页面
    value = request.GET.get('q')
    # uid = info_dict['uid']  # 已经进行了用户认证
    if value:
        return redirect("/search/?q={}".format(value))

    newsid = int(newsid)
    # 更新fire的值
    firenews = News.objects.all().update(
        fire=ExpressionWrapper(
            F('timeliness') * 0.99 + F('seetimes') * 0.01,
            output_field=FloatField()))
    # 根据topfire排序获取新闻
    toplist = News.objects.filter(timeliness__gte=80).order_by('-fire')
    selectnews = News.objects.filter(newsid=newsid).first()
    selectnews.newscontent = insert_line_breaks(selectnews.newscontent)
    # 通过newsid查找News对象，并获取其cid字段的值
    selectid_query = News.objects.filter(newsid=newsid).values_list('cid', flat=True).first()

    # 检查selectid_query是否为None，避免在None上进行查询
    if selectid_query is not None:
        # 使用获取到的cid值来查找相关的News对象

        relatednews = News.objects.filter(cid=selectid_query).order_by('-fire').distinct()
    else:
        # 如果没有找到对应的cid，可以处理这种情况，比如返回一个空的查询集
        relatednews = News.objects.none()
    typelist = Newstype.objects.all()

    # 评论信息
    # 1全部评论的信息
    # 1.1初始化 chatlist，用来存储需要返回给前端的数据
    chatlist = []
    # 1.2从 Newscomment 中获取所有与 newsid 相关的评论
    comments = Newscomment.objects.filter(news_id=newsid)
    # 1.3遍历评论，获取每个评论的信息和关联的用户信息
    for comment in comments:
        # 从 User 模型中获取用户信息
        try:
            user = User.objects.get(uid=comment.uid)
        except User.DoesNotExist:
            # 如果用户不存在，可以跳过该评论或记录日志
            continue

            # 将评论和用户信息添加到 chatlist
        chatlist.append({
            'uid': user.uid,
            'uname': user.uname,
            'img': user.img,
            'commentid': comment.commentid,
            'comment': comment.comment,
            'commenttime': comment.commenttime,
        })
    # 评论总数
    commentnumbers = 0
    likenumbers = 0
    collectionnumbers = 0
    seetimes = 0
    try:
        commentnumbers = News.objects.filter(newsid=newsid).values_list('commentnumbers', flat=True).first()
        likenumbers = News.objects.filter(newsid=newsid).values_list('likenumbers', flat=True).first()
        collectionnumbers = News.objects.filter(newsid=newsid).values_list('collectionnumbers', flat=True).first()
        seetimes = News.objects.filter(newsid=newsid).values_list('seetimes', flat=True).first()
    except News.DoesNotExist:
        # 如果newsid不存在，设置commentnumbers为0或None或其他默认值
        commentnumbers = 0
        likenumbers = 0
        collectionnumbers = 0
        seetimes = 0
    #

    # 2我的评论的信息
    info_dict = request.session["info"]
    uid = info_dict['uid']  # 已经进行了用户认证
    # 初始化一个列表，用于存放我对该新闻的评论
    mychatlist = []
    # 从comment中查到所有满足newsid和uid这两个条件下的评论
    mycomments = Newscomment.objects.filter(news_id=newsid, uid=uid)
    # 遍历评论，获取每个评论的信息和关联的用户信息
    for mycomment in mycomments:
        user = User.objects.get(uid=uid)  # 这里假设mycomment.uid是有效的
        mychatlist.append({
            'uid': user.uid,
            'uname': user.uname,
            'img': user.img,
            'commentid': mycomment.commentid,
            'comment': mycomment.comment,
            'commenttime': mycomment.commenttime
        })

    return render(request, 'newsdetails.html',
                  {'toplist': toplist, 'selectnews': selectnews, 'currentnid': newsid, 'relatednews': relatednews,
                   'typelist': typelist, 'is_collection': is_user_collected(request.session['info']['uid'], newsid),
                   'is_like': is_user_liked(request.session['info']['uid'], newsid), 'chatlist': chatlist,
                   'commentnumbers': commentnumbers, 'mychatlist': mychatlist, 'userinfoobj': userinfoobj,
                   'likenumbers': likenumbers, 'collectionnumbers': collectionnumbers, 'seetimes': seetimes})


# 退出登录

# 搜索功能模块
def search(request):
    # 从前端获取搜索的字段
    value = request.GET.get('q')
    data_dict = {}
    info_dict = request.session["info"]
    uid = uid = info_dict['uid']
    userinfoobj = User.objects.filter(uid=info_dict['uid']).first()
    if value:
        data_dict['newscontent__contains'] = value
        searchresult = models.News.objects.filter(**data_dict)
    else:
        searchresult = models.News.objects.none()
    # 更新fire的值
    firenews = News.objects.all().update(
        fire=ExpressionWrapper(
            F('timeliness') * 0.99 + F('seetimes') * 0.01,
            output_field=FloatField()))
    # 根据fire排序获取新闻
    toplist = News.objects.filter(timeliness__gte=80).order_by('-fire')
    typelist = Newstype.objects.all()
    # 添加和更新词云图
    # 首先查询是否有这个词条对象
    cloudobj = Userclouds.objects.filter(uid=uid, cloudword=value).first()
    if cloudobj:
        updatecloudobj = Userclouds.objects.filter(uid=uid, cloudword=value).update(cloudtime=F('cloudtime') + 1)
    else:
        creatcloudobj = Userclouds.objects.create(uid=uid, cloudword=value, cloudtime=1)
    return render(request, 'search.html',
                  {"userinfoobj": userinfoobj, "typelist": typelist, 'toplist': toplist, 'searchresult': searchresult})


# 收藏功能的视图函数
def togglecollection(request, newsid):
    if request.method == 'POST':
        # 收藏功能
        info_dict = request.session["info"]
        uid = info_dict['uid']  # 已经进行了用户认证
        try:
            collection = Collection.objects.get(news_id=newsid, uid=uid)
            collection.delete()  # 如果已经收藏，则删除记录
            # 使用F表达式来更新collectionnumber字段，使其自减1
            News.objects.filter(newsid=newsid).update(collectionnumbers=F('collectionnumbers') - 1)
            # 对已收藏的该名新闻同属类别的新闻的推荐指数进行调整
            # 先找到同属类别的类别id
            collectednewscid = News.objects.filter(newsid=newsid).values_list('cid', flat=True).first()
            # 然后去推荐表里调整该名用户下同属类别新闻的推荐指数
            renewsupdate = Newsrecommend.objects.filter(cid=collectednewscid, uid=uid).update(addfire=F('addfire') - 3)
            is_collection = False
        except Collection.DoesNotExist:
            Collection.objects.create(news_id=newsid, uid=uid)  # 如果未收藏，则添加记录
            # 使用F表达式来更新collectionnumber字段，使其自加1
            News.objects.filter(newsid=newsid).update(
                collectionnumbers=F('collectionnumbers') + 1)  # 对已收藏的该名新闻同属类别的新闻的推荐指数进行调整
            # 先找到同属类别的类别id
            collectednewscid = News.objects.filter(newsid=newsid).values_list('cid', flat=True).first()
            # # 然后去推荐表里调整该名用户下同属类别新闻的推荐指数
            renewsupdate = Newsrecommend.objects.filter(cid=collectednewscid, uid=uid).update(addfire=F('addfire') + 3)
            is_collection = True
        return JsonResponse({'is_collection': is_collection})


# 喜欢按钮功能
def togglelike(request, newsid):
    if request.method == 'POST':
        # 收藏功能
        info_dict = request.session["info"]
        uid = info_dict['uid']  # 已经进行了用户认证

        try:
            like = Like.objects.get(news_id=newsid, uid=uid)
            like.delete()  # 如果已经收藏，则删除记录
            # 使用F表达式来更新collectionnumber字段，使其自减1
            News.objects.filter(newsid=newsid).update(likenumbers=F('likenumbers') - 1)
            # 对已喜欢的该名新闻同属类别的新闻的推荐指数进行调整
            # 先找到同属类别的类别id
            likednewscid = News.objects.filter(newsid=newsid).values_list('cid', flat=True).first()
            # 然后去推荐表里调整该名用户下同属类别新闻的推荐指数
            renewsupdate = Newsrecommend.objects.filter(cid=likednewscid, uid=uid).update(addfire=F('addfire') - 3)
            is_like = False
        except Like.DoesNotExist:
            Like.objects.create(news_id=newsid, uid=uid)  # 如果未收藏，则添加记录
            # 使用F表达式来更新collectionnumber字段，使其自加1
            News.objects.filter(newsid=newsid).update(likenumbers=F('likenumbers') + 1)
            # 对已喜欢的该名新闻同属类别的新闻的推荐指数进行调整
            # 先找到同属类别的类别id
            likednewscid = News.objects.filter(newsid=newsid).values_list('cid', flat=True).first()
            # 然后去推荐表里调整该名用户下同属类别新闻的推荐指数
            renewsupdate = Newsrecommend.objects.filter(cid=likednewscid, uid=uid).update(addfire=F('addfire') + 3)
            is_like = True
        return JsonResponse({'is_like': is_like})


# 浏览新闻
def seenews(request, newsid):
    if request.method == 'POST':
        info_dict = request.session["info"]
        uid = info_dict['uid']  # 已经进行了用户认证
        # 更新当天的浏览次数
        info_dict = request.session["info"]
        nowdate = datetime.now().strftime('%Y-%m-%d')
        # 判断数据库中是否包含
        userreadobj_exists = Userread.objects.filter(uid=info_dict['uid'], datetime=nowdate).exists()
        # 如果存在该对象就对该条对象进行更新
        if userreadobj_exists:
            updateuserread = Userread.objects.filter(uid=info_dict['uid'], datetime=nowdate).update(
                readnumbers=F('readnumbers') + 1)
        # 更新浏览次数
        # 更新该新闻的总浏览次数
        seetimesupdate = News.objects.filter(newsid=newsid).update(seetimes=F('seetimes') + 1)
        # 添加该条浏览记录
        # 获取当前时间（确保服务器设置为北京时间）
        current_time = datetime.now()
        # 格式化当前时间为年月日时分
        current_beijing_time_formatted = current_time.strftime('%Y-%m-%d %H:%M')
        current_beijing_time = current_time.replace(second=0, microsecond=0)  # 移除秒和微秒部分
        seecreate = Newssee.objects.create(news_id=newsid, uid=uid, seetime=current_beijing_time)

        # 找到该新闻的cid
        seenewscid = News.objects.filter(newsid=newsid).values_list('cid', flat=True).first()
        # 对该名用户该类别下的新闻推荐指数进行调整
        seenewsupdate = Newsrecommend.objects.filter(cid=seenewscid, uid=uid).update(addfire=F('addfire') + 1.5)
        return JsonResponse({'status': 'success'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)


def chat(request, newsid):
    if request.method == 'POST':
        info_dict = request.session["info"]
        uid = info_dict['uid']  # 已经进行了用户认证
        # 获取当前时间（确保服务器设置为北京时间）
        current_time = datetime.now()
        current_beijing_time = current_time.replace(second=0, microsecond=0)  # 移除秒和微秒部分
        # seecreate = Newssee.objects.create(news_id=newsid, uid=uid, seetime=current_beijing_time)

        createnews = Newscomment.objects.create(news_id=newsid, uid=uid, comment=request.POST['comment'],
                                                commenttime=current_beijing_time)
        commentupdate = News.objects.filter(newsid=newsid).update(commentnumbers=F('commentnumbers') + 1)
        # 找到该新闻的cid
        commentnewscid = News.objects.filter(newsid=newsid).values_list('cid', flat=True).first()
        # 对该名用户该类别下的新闻推荐指数进行调整
        seenewsupdate = Newsrecommend.objects.filter(cid=commentnewscid, uid=uid).update(addfire=F('addfire') + 2.5)
        return JsonResponse({'status': 'success'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)


def user_info(request):
    info_dict = request.session["info"]
    uid = info_dict['uid']  # 已经进行了用户认证
    # 跳转到搜索页面
    value = request.GET.get('q')
    # uid = info_dict['uid']  # 已经进行了用户认证

    if value:
        return redirect("/search/?q={}".format(value))
    userinfoobj = User.objects.filter(uid=uid).first()
    typelist = models.Newstype.objects.all()
    if request.method == 'POST':
        if 'uname' in request.POST:
            # 更新基本信息
            uname = request.POST['uname']
            sex = request.POST['sex']
            word = request.POST['word']
            email = request.POST['email']
            province = request.POST['province']
            birthdate = request.POST['birthdate']
            # 将字符串转换为日期对象
            birthdate = date.fromisoformat(birthdate)

            # 计算年龄
            today = timezone.now().date()
            age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
            updated_count = User.objects.filter(uid=uid).update(uname=uname, sex=sex, word=word, email=email,
                                                                province=province, birthdate=birthdate, age=age)
            if updated_count > 0:
                # 设置session变量表示成功
                request.session['update_success'] = True
                # 重定向到相同页面以刷新
                return redirect('/user_info/')  # 假设'user_info'是对应的视图名称或URL
            else:
                # 更新失败的处理逻辑
                pass
        elif 'selectedImgUrl' in request.POST:
            # 获取到的当前已选择的url
            selected_img_url = request.POST.get('selectedImgUrl')
            # 根据需要处理图片URL，比如保存到服务器或更新数据库中的URL
            userimgupadte = User.objects.filter(uid=uid).update(img=selected_img_url)
            print(selected_img_url)
            if userimgupadte > 0:
                # 设置session变量表示成功
                request.session['updateimg_success'] = True
                return redirect('/user_info/')  # 重定向到成功页面
            else:
                pass

    updateimg_success = request.session.pop('updateimg_success', False)
    update_success = request.session.pop('update_success', False)
    # 获取头像表中所有头像的url
    imgurllist = Img.objects.all()
    # 获取全部省份信息
    provincelist = Province.objects.all()
    return render(request, "user_info.html",
                  {"typelist": typelist, "userinfoobj": userinfoobj,
                   "update_success": update_success, 'imgurllist': imgurllist, 'updateimg_success': updateimg_success,
                   'provincelist': provincelist})


def user_like(request):
    info_dict = request.session["info"]
    uid = info_dict['uid']  # 已经进行了用户认证
    # 跳转到搜索页面
    value = request.GET.get('q')
    # uid = info_dict['uid']  # 已经进行了用户认证
    if value:
        return redirect("/search/?q={}".format(value))
    # 该用户所浏览的全部新闻信息
    like_dict = []
    # 需要获取到排序后以news_id去重的结果
    # 首先获取所有符合条件的Newssee对象，并按seeid降序排序
    newslike_entries = models.Like.objects.filter(uid=uid).order_by('-likeid')

    # 遍历Newssee记录，并获取关联的News对象的详细信息
    for newslike in newslike_entries:
        news = newslike.news  # 通过关联字段访问News对象
        # 将新闻的详细信息作为字典添加到see_dict列表中
        like_dict.append({
            'newsid': news.newsid,
            'newstitle': news.newstitle,
            'newscontent': news.newscontent,
            'newsdate': news.newsdate,  # 假设newsdate是合适的字段类型
            'newsauthor': news.newsauthor,
            'newsimg': news.newsimg,
            'cname': news.cname,  # 假设cname是News模型的一个字段
        })
    page = int(request.GET.get('page', 1))
    page_size = 5
    start = (page - 1) * page_size
    end = page * page_size
    # 记录总数
    renews_count = len(like_dict)
    #
    like_dict = like_dict[start:end]
    renews_page_count, div = divmod(renews_count, page_size)
    # 分页功能
    # 计算页码
    if div:
        renews_page_count += 1
    plus = 2
    if renews_page_count <= 2 * plus + 1:
        start_page = 1
        end_page = renews_page_count
    else:
        if page <= plus:
            start_page = 1
            end_page = 2 * plus + 1
        else:
            start_page = page - plus
            end_page = page + plus
    page_str_list_like = []

    # 上一页
    if page > 1:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">上一页</a></li>'.format(page - 1)
    else:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">上一页</a></li>'.format(1)
    page_str_list_like.append(prev)
    # 页面
    for i in range(start_page, end_page + 1):
        if i == page:
            ele = '<li class="page-item active" ><a class="page-link" href="?page={}">{}</a></li>'.format(i, i)
        else:
            ele = '<li class="page-item " ><a class="page-link" href="?page={}">{}</a></li>'.format(i, i)
        page_str_list_like.append(ele)
    # 下一页
    if page < renews_page_count:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">下一页</a></li>'.format(page + 1)
    else:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">下一页</a></li>'.format(renews_page_count)
    page_str_list_like.append(prev)
    page_str_like = mark_safe(''.join(page_str_list_like))

    # 收藏新闻搜索
    value2 = request.GET.get('likq')
    data_dict = {}
    search_none = False
    blank_success = True
    if value2:
        blank_success = False
        data_dict['newscontent__contains'] = value2
        searchresult = [item for item in like_dict if value2 in item['newscontent']]
        if searchresult is None or len(searchresult) == 0:
            search_none = True
    else:
        blank_success = True
        searchresult = models.News.objects.none()

    typelist = models.Newstype.objects.all()
    return render(request, "user_like.html", {"typelist": typelist, 'like_dict': like_dict,
                                              'page_str_like': page_str_like,
                                              'search_none': search_none, 'blank_success': blank_success,
                                              'searchresult': searchresult})


def user_collection(request):
    info_dict = request.session["info"]
    uid = info_dict['uid']  # 已经进行了用户认证
    # 跳转到搜索页面
    value = request.GET.get('q')
    # uid = info_dict['uid']  # 已经进行了用户认证
    if value:
        return redirect("/search/?q={}".format(value))
    # 该用户所浏览的全部新闻信息
    collection_dict = []
    # 需要获取到排序后以news_id去重的结果
    # 首先获取所有符合条件的Newssee对象，并按seeid降序排序
    newscollection_entries = models.Collection.objects.filter(uid=uid).order_by('-collectionid')

    # 遍历Newssee记录，并获取关联的News对象的详细信息
    for newscollection in newscollection_entries:
        news = newscollection.news  # 通过关联字段访问News对象
        # 将新闻的详细信息作为字典添加到see_dict列表中
        collection_dict.append({
            'newsid': news.newsid,
            'newstitle': news.newstitle,
            'newscontent': news.newscontent,
            'newsdate': news.newsdate,  # 假设newsdate是合适的字段类型
            'newsauthor': news.newsauthor,
            'newsimg': news.newsimg,
            'cname': news.cname,  # 假设cname是News模型的一个字段
        })
    page = int(request.GET.get('page', 1))
    page_size = 5
    start = (page - 1) * page_size
    end = page * page_size
    # 记录总数
    renews_count = len(collection_dict)
    #
    collection_dict = collection_dict[start:end]
    renews_page_count, div = divmod(renews_count, page_size)
    # 分页功能
    # 计算页码
    if div:
        renews_page_count += 1
    plus = 2
    if renews_page_count <= 2 * plus + 1:
        start_page = 1
        end_page = renews_page_count
    else:
        if page <= plus:
            start_page = 1
            end_page = 2 * plus + 1
        else:
            start_page = page - plus
            end_page = page + plus
    page_str_list_collection = []

    # 上一页
    if page > 1:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">上一页</a></li>'.format(page - 1)
    else:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">上一页</a></li>'.format(1)
    page_str_list_collection.append(prev)
    # 页面
    for i in range(start_page, end_page + 1):
        if i == page:
            ele = '<li class="page-item active" ><a class="page-link" href="?page={}">{}</a></li>'.format(i, i)
        else:
            ele = '<li class="page-item " ><a class="page-link" href="?page={}">{}</a></li>'.format(i, i)
        page_str_list_collection.append(ele)
    # 下一页
    if page < renews_page_count:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">下一页</a></li>'.format(page + 1)
    else:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">下一页</a></li>'.format(renews_page_count)
    page_str_list_collection.append(prev)
    page_str_collection = mark_safe(''.join(page_str_list_collection))

    # 收藏新闻搜索
    value2 = request.GET.get('colq')
    data_dict = {}
    search_none = False
    blank_success = True
    if value2:
        blank_success = False
        data_dict['newscontent__contains'] = value2
        searchresult = [item for item in collection_dict if value2 in item['newscontent']]
        if searchresult is None or len(searchresult) == 0:
            search_none = True
    else:
        blank_success = True
        searchresult = models.News.objects.none()

    typelist = models.Newstype.objects.all()
    return render(request, "user_collection.html", {"typelist": typelist, 'collection_dict': collection_dict,
                                                    'page_str_collection': page_str_collection,
                                                    'search_none': search_none, 'blank_success': blank_success,
                                                    'searchresult': searchresult})


def user_history(request):
    info_dict = request.session["info"]
    uid = info_dict['uid']  # 已经进行了用户认证
    # 跳转到搜索页面
    value = request.GET.get('q')
    # uid = info_dict['uid']  # 已经进行了用户认证
    if value:
        return redirect("/search/?q={}".format(value))
    # 该用户所浏览的全部新闻信息
    see_dict = []
    # 需要获取到排序后以news_id去重的结果
    # 首先获取所有符合条件的Newssee对象，并按seeid降序排序
    newssee_queryset = models.Newssee.objects.filter(uid=uid).order_by('-seeid')

    # 使用一个集合来存储已经出现过的news_id
    seen_news_ids = set()

    # 遍历查询集，构建一个新的列表，同时跳过重复的news_id
    newssee_entries = []
    for newssee_obj in newssee_queryset:
        if newssee_obj.news_id not in seen_news_ids:
            seen_news_ids.add(newssee_obj.news_id)
            newssee_entries.append(newssee_obj)
            # unique_newssee_objects现在包含去重后的Newssee对象列表
    # 遍历Newssee记录，并获取关联的News对象的详细信息
    for newssee in newssee_entries:
        news = newssee.news  # 通过关联字段访问News对象
        # 将新闻的详细信息作为字典添加到see_dict列表中
        see_dict.append({
            'newsid': news.newsid,
            'newstitle': news.newstitle,
            'newscontent': news.newscontent,
            'newsdate': news.newsdate,  # 假设newsdate是合适的字段类型
            'newsauthor': news.newsauthor,
            'newsimg': news.newsimg,
            'cname': news.cname,  # 假设cname是News模型的一个字段
            'seetime': newssee.seetime
        })
        # 现在see_dict列表包含了所有与给定uid相关的新闻信息
        # 定义页码
    page = int(request.GET.get('page', 1))
    page_size = 5
    start = (page - 1) * page_size
    end = page * page_size
    # 记录总数
    renews_count = len(see_dict)
    #
    see_dict = see_dict[start:end]
    renews_page_count, div = divmod(renews_count, page_size)
    # 分页功能
    # 计算页码
    if div:
        renews_page_count += 1
    plus = 2
    if renews_page_count <= 2 * plus + 1:
        start_page = 1
        end_page = renews_page_count
    else:
        if page <= plus:
            start_page = 1
            end_page = 2 * plus + 1
        else:
            start_page = page - plus
            end_page = page + plus
    page_str_list_history = []

    # 上一页
    if page > 1:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">上一页</a></li>'.format(page - 1)
    else:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">上一页</a></li>'.format(1)
    page_str_list_history.append(prev)
    # 页面
    for i in range(start_page, end_page + 1):
        if i == page:
            ele = '<li class="page-item active" ><a class="page-link" href="?page={}">{}</a></li>'.format(i, i)
        else:
            ele = '<li class="page-item " ><a class="page-link" href="?page={}">{}</a></li>'.format(i, i)
        page_str_list_history.append(ele)
    # 下一页
    if page < renews_page_count:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">下一页</a></li>'.format(page + 1)
    else:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">下一页</a></li>'.format(renews_page_count)
    page_str_list_history.append(prev)

    page_str_history = mark_safe(''.join(page_str_list_history))

    # 浏览历史搜索
    value1 = request.GET.get('hisq')
    data_dict = {}
    search_none = False
    blank_success = True
    if value1:
        blank_success = False
        data_dict['newscontent__contains'] = value1
        searchresult = [item for item in see_dict if value1 in item['newscontent']]
        if searchresult is None or len(searchresult) == 0:
            search_none = True
    else:
        blank_success = True
        searchresult = models.News.objects.none()
    typelist = models.Newstype.objects.all()
    return render(request, "user_history.html",
                  {"typelist": typelist, "see_dict": see_dict, "page_str_history": page_str_history,
                   "search_none": search_none, 'blank_success': blank_success, 'searchresult': searchresult})


def user_comment(request):
    info_dict = request.session["info"]
    uid = info_dict['uid']  # 已经进行了用户认证
    value = request.GET.get('q')
    # uid = info_dict['uid']  # 已经进行了用户认证
    if value:
        return redirect("/search/?q={}".format(value))
    userinfoobj = User.objects.filter(uid=info_dict['uid']).first()
    comment_dict = Newscomment.objects.filter(uid=uid).all()
    # 收藏搜索
    value3 = request.GET.get('comq')
    data_dict = {}
    search_none = False
    blank_success = True
    if value3:
        blank_success = False
        data_dict['comment__contains'] = value3
        searchresult = models.Newscomment.objects.filter(**data_dict)
        if searchresult is None or len(searchresult) == 0:
            search_none = True
    else:
        blank_success = True
        searchresult = models.Newscomment.objects.none()

    # 定义页码
    page = int(request.GET.get('page', 1))
    page_size = 5
    start = (page - 1) * page_size
    end = page * page_size
    # 记录总数
    renews_count = Newscomment.objects.filter(uid=uid).count()
    #
    comment_dict = Newscomment.objects.filter(uid=uid).order_by('-commentid')[start:end]
    renews_page_count, div = divmod(renews_count, page_size)
    # 分页功能
    # 计算页码
    if div:
        renews_page_count += 1
    plus = 2
    if renews_page_count <= 2 * plus + 1:
        start_page = 1
        end_page = renews_page_count
    else:
        if page <= plus:
            start_page = 1
            end_page = 2 * plus + 1
        else:
            start_page = page - plus
            end_page = page + plus
    page_str_list_comment = []

    # 上一页
    if page > 1:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">上一页</a></li>'.format(page - 1)
    else:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">上一页</a></li>'.format(1)
    page_str_list_comment.append(prev)
    # 页面
    for i in range(start_page, end_page + 1):
        if i == page:
            ele = '<li class="page-item active" ><a class="page-link" href="?page={}">{}</a></li>'.format(i, i)
        else:
            ele = '<li class="page-item " ><a class="page-link" href="?page={}">{}</a></li>'.format(i, i)
        page_str_list_comment.append(ele)
    # 下一页
    if page < renews_page_count:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">下一页</a></li>'.format(page + 1)
    else:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">下一页</a></li>'.format(renews_page_count)
    page_str_list_comment.append(prev)

    page_str_comment = mark_safe(''.join(page_str_list_comment))
    typelist = models.Newstype.objects.all()
    return render(request,
                  "user_comment.html",
                  {"typelist": typelist,
                   'comment_dict': comment_dict, 'search_none': search_none, 'blank_success': blank_success,
                   'userinfoobj': userinfoobj, 'searchresult': searchresult, 'page_str_comment': page_str_comment})


def user_bar(request):
    typelist = models.Newstype.objects.all()
    info_dict = request.session["info"]
    uid = info_dict['uid']  # 已经进行了用户认证
    # 搜索功能
    value = request.GET.get('q')
    # uid = info_dict['uid']  # 已经进行了用户认证
    if value:
        return redirect("/search/?q={}".format(value))
    # 计算用户浏览时长
    # 当第一次访问个人主页时，登陆时间设置成真正的登录时间
    login_time_str = request.session.get('login_time')
    if login_time_str:
        login_time = datetime.strptime(login_time_str, '%Y-%m-%d %H:%M:%S')
        logout_time = datetime.now()
        duration = (logout_time - login_time).total_seconds() / 60  # 转换为分钟
        duration = int(duration)
        # 更新阅读的时间
        current_time = datetime.now().strftime('%Y-%m-%d')
        updateuserread = Userread.objects.filter(uid=info_dict['uid'], datetime=current_time).update(
            readtime=F('readtime') + duration)
        # 更新session中login_time的值
        current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # 将当前时间戳字符串保存到session中
        request.session['login_time'] = current_time_str
        print(f"User stayed for {duration:.2f} minutes today.")
    date_time_list = Userread.objects.filter(uid=uid).order_by('id')
    # 最后一个数据对象
    last_date = Userread.objects.filter(uid=uid).order_by('id').last()
    return render(request, "user_bar.html",
                  {"typelist": typelist, "date_time_list": date_time_list, "last_date": last_date})


def user_pie(request):
    typelist = models.Newstype.objects.all()
    info_dict = request.session["info"]
    uid = info_dict['uid']  # 已经进行了用户认证
    # 搜索功能
    value = request.GET.get('q')
    # uid = info_dict['uid']  # 已经进行了用户认证
    if value:
        return redirect("/search/?q={}".format(value))
    # 首先，获取用户看过的所有新闻的总数
    total_news_count = Newssee.objects.filter(uid=uid).distinct().count()
    # 首先，我们需要一个字典来映射cid到cname
    cid_to_cname = News.objects.values('cid', 'cname').distinct()
    cname_dict = {item['cid']: item['cname'] for item in cid_to_cname}

    # 使用子查询来获取每个cid对应的新闻数量
    news_counts = Newssee.objects.filter(uid=uid).values('news__cid').annotate(
        news_count=Coalesce(Count('news'), 0)
    ).order_by('-news_count')

    # 构造cid_news_numbers列表，其中包含cid, cname和次数
    cid_news_numbers = []
    for count in news_counts:
        cid = count['news__cid']
        cname = cname_dict.get(cid, 'Unknown')  # 如果cid没有找到对应的cname，则使用'Unknown'
        news_count = count['news_count']
        # 计算百分比，注意要防止除数为0的情况
        account = (news_count / total_news_count) * 100 if total_news_count > 0 else 0
        cid_news_numbers.append({
            'cid': cid,
            'cname': cname,
            'count': count['news_count'],
            'account': round(account, 2)  # 保留两位小数
        })
        print(cid_news_numbers)
    return render(request, "user_pie.html",
                  {"cid_news_numbers": cid_news_numbers, 'typelist': typelist})


def user_line(request):
    typelist = models.Newstype.objects.all()
    info_dict = request.session["info"]
    uid = info_dict['uid']  # 已经进行了用户认证
    # 搜索功能
    value = request.GET.get('q')
    # uid = info_dict['uid']  # 已经进行了用户认证
    if value:
        return redirect("/search/?q={}".format(value))
    return render(request, "user_line.html", {'typelist': typelist})


def user_table(request):
    info_dict = request.session["info"]
    uid = info_dict['uid']  # 已经进行了用户认证
    # 这里是折柱图需要的数据
    # 我们只需要显示一周内的数据
    # 计算一周前的日期
    one_week_ago = timezone.now() - timedelta(days=7)
    # 删除超过一周的记录
    Userread.objects.filter(datetime__lt=one_week_ago).delete()
    # 获取日期数组
    date_tuples = Userread.objects.filter(uid=uid).values_list('datetime', flat=True).order_by('id')
    # 将元组列表转换成datetime对象列表
    date_list = list(date_tuples)
    # 格式化一下
    formatted_dates = [date.strftime('%Y-%m-%d') for date in date_list]
    # 获取近七天浏览时间
    readtimelist = Userread.objects.filter(uid=uid).values_list('readtime', flat=True).order_by('id')
    readtimelist = list(readtimelist)
    # 获取近七天的浏览篇数
    readnumberslist = Userread.objects.filter(uid=uid).values_list('readnumbers', flat=True).order_by('id')
    readnumberslist = list(readnumberslist)
    # 用户浏览偏好数据查询
    # 首先，从News模型中获取所有独特的cid
    all_cids = News.objects.values_list('cid', flat=True).distinct().order_by('cid')
    # 初始化一个字典来存储每个cid的新闻数量
    cid_news_numbers = {cid: 0 for cid in all_cids}
    # 然后，从Newssee模型中筛选出当前用户看过的新闻，并按cid分组计数
    seen_news_counts = Newssee.objects.filter(uid=uid).values('news__cid').annotate(count=Count('news'))
    # 更新cid_news_numbers字典中已查看过的cid的新闻数量
    for seen in seen_news_counts:
        cid = seen['news__cid']
        cid_news_numbers[cid] = seen['count']
    # 现在cid_news_numbers包含了所有cid以及对应被当前用户查看过的新闻数量（默认为0）
    news_counts_only = list(cid_news_numbers.values())  # 将新闻数量提取成列表

    # 用户喜欢数据查询
    # 初始化一个字典来存储每个cid的新闻数量
    cid_like_numbers = {cid: 0 for cid in all_cids}
    # 然后，从Newssee模型中筛选出当前用户看过的新闻，并按cid分组计数
    like_news_counts = Like.objects.filter(uid=uid).values('news__cid').annotate(count=Count('news'))
    # 更新cid_news_numbers字典中已查看过的cid的新闻数量
    for like in like_news_counts:
        cid = like['news__cid']
        cid_like_numbers[cid] = like['count']
    # 现在cid_news_numbers包含了所有cid以及对应被当前用户查看过的新闻数量（默认为0）
    news_like_only = list(cid_like_numbers.values())  # 将新闻数量提取成列表

    # 用户收藏查询
    # 初始化一个字典来存储每个cid的新闻数量
    cid_collection_numbers = {cid: 0 for cid in all_cids}
    # 然后，从Newssee模型中筛选出当前用户看过的新闻，并按cid分组计数
    collection_news_counts = Collection.objects.filter(uid=uid).values('news__cid').annotate(count=Count('news'))
    # 更新cid_news_numbers字典中已查看过的cid的新闻数量
    for collection in collection_news_counts:
        cid = collection['news__cid']
        cid_collection_numbers[cid] = collection['count']
    # 现在cid_news_numbers包含了所有cid以及对应被当前用户查看过的新闻数量（默认为0）
    news_collection_only = list(cid_collection_numbers.values())  # 将新闻数量提取成列表

    # 用户评论查询
    # 初始化一个字典来存储每个cid的新闻数量
    cid_comment_numbers = {cid: 0 for cid in all_cids}
    # 然后，从Newssee模型中筛选出当前用户看过的新闻，并按cid分组计数
    comment_news_counts = Newscomment.objects.filter(uid=uid).values('news__cid').annotate(count=Count('news'))
    # 更新cid_news_numbers字典中已查看过的cid的新闻数量
    for comment in comment_news_counts:
        cid = comment['news__cid']
        cid_comment_numbers[cid] = comment['count']
    # 现在cid_news_numbers包含了所有cid以及对应被当前用户查看过的新闻数量（默认为0）
    news_comment_only = list(cid_comment_numbers.values())  # 将新闻数量提取成列表
    # 词云图
    cloudslist = Userclouds.objects.filter(uid=uid).values_list('cloudword', 'cloudtime')
    cloudslist = list(cloudslist)
    # 来获取所有新闻类别
    typelist = Newstype.objects.values_list('cname', flat=True)
    typelist = list(typelist)

    # 返回的数据结果
    result = {
        "status": True,
        "data": {
            'formatted_dates': formatted_dates,
            'readtimelist': readtimelist,
            'readnumberslist': readnumberslist,
            'news_counts_only': news_counts_only,
            'typelist': typelist,
            'news_like_only': news_like_only,
            'news_collection_only': news_collection_only,
            'news_comment_only': news_comment_only,
            'cloudslist': cloudslist

        }
    }
    print(result)
    return JsonResponse(result)


def register(request):
    registerexist = False
    # 将新建用户添加到新闻推荐表
    uid = request.POST['uid']
    # 第一步：从 News 模型中获取所有 newsid 和 cid
    news_items = News.objects.values('newsid', 'cid')

    # 第二步：遍历新闻，并创建 Newsrecommend 对象
    for news_item in news_items:
        # 创建 Newsrecommend 对象
        newsrecommend = Newsrecommend(
            uid=uid,
            news_id=news_item['newsid'],  # 使用news_id字段代替直接使用外键
            cid=news_item['cid'],
            refire=0
        )
        # 保存 Newsrecommend 对象到数据库
        newsrecommend.save()
    if request.method == 'POST':
        print("POST数据：", request.POST)
        uid = request.POST['uid']
        uname = request.POST['uname']
        sex = request.POST['sex']
        passwd = request.POST['passwd']
        birthdate = request.POST['birthdate']
        province = request.POST['province']
        uobj = User.objects.filter(uid=uid).first()
        # 将字符串转换为日期对象
        birthdate = date.fromisoformat(birthdate)

        # 计算年龄
        today = timezone.now().date()
        age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
        if uobj:
            registerexist = True
        else:
            uobjcreate = User.objects.create(uid=uid, uname=uname, sex=sex, passwd=passwd, birthdate=birthdate, age=age,
                                             province=province)
            registerexist = False
    return JsonResponse({'registerexist': registerexist})


def user_register(request):
    provincelist = Province.objects.all()
    return render(request, "user_register.html", {'provincelist': provincelist})


def manage_info(request):
    info_dict = request.session["info"]
    uid = info_dict['uid']  # 已经进行了用户认证
    userinfoobj = User.objects.filter(uid=uid).first()
    typelist = models.Newstype.objects.all()
    if request.method == 'POST':
        if 'uname' in request.POST:
            # 更新基本信息
            uname = request.POST['uname']
            sex = request.POST['sex']
            word = request.POST['word']
            email = request.POST['email']
            updated_count = User.objects.filter(uid=uid).update(uname=uname, sex=sex, word=word, email=email)
            if updated_count > 0:
                # 设置session变量表示成功
                request.session['update_success'] = True
                # 重定向到相同页面以刷新
                return redirect('/manage_info/')  # 假设'user_info'是对应的视图名称或URL
            else:
                # 更新失败的处理逻辑
                pass
        elif 'selectedImgUrl' in request.POST:
            # 获取到的当前已选择的url
            selected_img_url = request.POST.get('selectedImgUrl')
            # 根据需要处理图片URL，比如保存到服务器或更新数据库中的URL
            userimgupadte = User.objects.filter(uid=uid).update(img=selected_img_url)
            print(selected_img_url)
            if userimgupadte > 0:
                # 设置session变量表示成功
                request.session['updateimg_success'] = True
                return redirect('/manage_info/')  # 重定向到成功页面
            else:
                pass

    updateimg_success = request.session.pop('updateimg_success', False)
    update_success = request.session.pop('update_success', False)
    # 获取头像表中所有头像的url
    imgurllist = Img.objects.all()
    return render(request, "manage_info.html",
                  {"typelist": typelist, "userinfoobj": userinfoobj,
                   "update_success": update_success, 'imgurllist': imgurllist, 'updateimg_success': updateimg_success
                   })


def manage_base(request):
    info_dict = request.session["info"]
    uid = info_dict['uid']  # 已经进行了用户认证
    # 我们只需要显示一周内的数据
    # 计算一周前的日期
    one_week_ago = timezone.now() - timedelta(days=7)
    # 删除超过一周的记录
    Uservisit.objects.filter(datetime__lt=one_week_ago).delete()
    # 查找总用户个数
    usernumber = User.objects.count()
    usernumber = int(usernumber)
    # 查找总浏览次数
    seenumber = Newssee.objects.count()
    seenumber = int(seenumber)
    # 查找总喜欢次数
    likenumber = Like.objects.count()
    likenumber = int(likenumber)
    # 查找总收藏次数
    collectionnumber = Collection.objects.count()
    collectionnumber = int(collectionnumber)
    # 查找总评论次数
    commentnumber = Newscomment.objects.count()
    commentnumber = int(commentnumber)
    # 查找总新闻个数
    newsnumber = News.objects.count()
    newsnumber = int(newsnumber)
    userinfoobj = User.objects.filter(uid=uid).first()
    # 删除时效性已过的推荐新闻
    # 第一步：获取timeliness小于等于93的News的newsid列表
    news_ids_to_delete = News.objects.filter(timeliness__lte=93).values_list('newsid', flat=True)
    # 第二步：在Newsrecommend中删除与这些newsid对应的记录
    Newsrecommend.objects.filter(news_id__in=news_ids_to_delete).delete()
    #删除时效性已过的新闻
    newsdelete=News.objects.filter(timeliness__lte=70).delete()
    #删除相应的浏览、点赞、收藏和评论
    newsoption_ids_to_delete = News.objects.filter(timeliness__lte=70).values_list('newsid', flat=True)
    # 删除收藏
    collection_delete=Collection.objects.filter(news_id__in=newsoption_ids_to_delete).delete()
    like_delete=Like.objects.filter(news_id__in=newsoption_ids_to_delete).delete()
    comment_delete=Newscomment.objects.filter(news_id__in=newsoption_ids_to_delete).delete()
    see_delete=Newssee.objects.filter(news_id__in=newsoption_ids_to_delete).delete()
    return render(request, "manage_base.html", {"userinfoobj": userinfoobj,
                                                'usernumber': usernumber, 'seenumber': seenumber,
                                                'likenumber': likenumber, 'collectionnumber': collectionnumber,
                                                'commentnumber': commentnumber, 'newsnumber': newsnumber})


def manage_table(request):
    info_dict = request.session["info"]
    uid = info_dict['uid']  # 已经进行了用户认证

    # 获取日期数组
    date_tuples = Uservisit.objects.values_list('datetime', flat=True).order_by('id')
    # 将元组列表转换成datetime对象列表
    date_list = list(date_tuples)
    # 格式化一下
    formatted_dates = [date.strftime('%Y-%m-%d') for date in date_list]
    # 获取近七天浏览时间
    visitlist = Uservisit.objects.values_list('count', flat=True).order_by('id')
    visitlist = list(visitlist)
    # 获取各个省份的人数
    province_counts = User.objects.values('province') \
        .annotate(count=Count('uid')) \
        .order_by('province')

    # 将查询结果转换为列表
    provincepeople = list(province_counts)
    # 统计各个年龄段的人数
    agelist = {'0~20': 0, '20~30': 0, '30~40': 0, '40~50': 0, '50~70': 0, '70~100': 0}

    # 定义年龄范围
    age_ranges = [(0, 20), (20, 30), (30, 40), (40, 50), (50, 70), (70, 100)]

    # 循环获取各个年龄段的人数
    for agerange in age_ranges:
        agelist[f"{agerange[0]}~{agerange[1]}"] = User.objects.filter(
            age__gte=agerange[0], age__lt=agerange[1]
        ).count()

    # 存入元组中
    agelist = [(key, value) for key, value in agelist.items()]

    result = {
        "status": True,
        "data": {
            'formatted_dates': formatted_dates,
            'visitlist': visitlist,
            'provincepeople': provincepeople,
            'agelist': agelist

        }
    }
    return JsonResponse(result)


def manage_user(request):
    info_dict = request.session["info"]
    uid = info_dict['uid']  # 已经进行了用户认证
    userlist = []
    userlist = User.objects.filter(usertype=1).all()
    # 该用户所浏览的全部新闻信息
    page = int(request.GET.get('page', 1))
    page_size = 10
    start = (page - 1) * page_size
    end = page * page_size
    # 记录总数
    renews_count = len(userlist)
    #
    userlist = userlist[start:end]
    renews_page_count, div = divmod(renews_count, page_size)
    # 分页功能
    # 计算页码
    if div:
        renews_page_count += 1
    plus = 2
    if renews_page_count <= 2 * plus + 1:
        start_page = 1
        end_page = renews_page_count
    else:
        if page <= plus:
            start_page = 1
            end_page = 2 * plus + 1
        else:
            start_page = page - plus
            end_page = page + plus
    page_str_list_user = []

    # 上一页
    if page > 1:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">上一页</a></li>'.format(page - 1)
    else:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">上一页</a></li>'.format(1)
    page_str_list_user.append(prev)
    # 页面
    for i in range(start_page, end_page + 1):
        if i == page:
            ele = '<li class="page-item active" ><a class="page-link" href="?page={}">{}</a></li>'.format(i, i)
        else:
            ele = '<li class="page-item " ><a class="page-link" href="?page={}">{}</a></li>'.format(i, i)
        page_str_list_user.append(ele)
    # 下一页
    if page < renews_page_count:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">下一页</a></li>'.format(page + 1)
    else:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">下一页</a></li>'.format(renews_page_count)
    page_str_list_user.append(prev)
    page_str_user = mark_safe(''.join(page_str_list_user))
    # 查找
    value = request.GET.get('userq')
    data_dict = {}
    search_none = False
    blank_success = True
    if value:
        blank_success = False
        data_dict['uid__contains'] = value
        searchresult = models.User.objects.filter(**data_dict)
        if searchresult is None or len(searchresult) == 0:
            search_none = True
    else:
        blank_success = True
        searchresult = models.User.objects.none()

    userinfoobj = User.objects.filter(uid=uid).first()
    provincelist = Province.objects.all()
    return render(request, "manage_user.html", {
        "userlist": userlist, 'provincelist': provincelist,
        'searchresult': searchresult, 'blank_success': blank_success, 'search_none': search_none,
        'page_str_user': page_str_user})


def manage_updateuser(request):
    if request.method == "POST":
        uid = request.POST.get('uid')
        uname = request.POST.get('uname')
        sex = request.POST.get('sex')
        province = request.POST.get('province')

        # 根据 uid 获取用户对象
        user = User.objects.get(uid=uid)
        # 更新用户信息
        user.uname = uname
        user.sex = sex
        user.province = province
        # 保存更新
        user.save()

        return JsonResponse({'success': True})  # 返回成功响应

    return JsonResponse({'success': False, 'message': '仅接受 POST 请求'})


def manage_deleteuser(request):
    if request.method == "POST":
        uid = request.POST.get('uid')

        try:
            # 尝试从数据库中获取要删除的用户对象
            user = User.objects.get(uid=uid)
            user.delete()  # 删除用户
            Newsrecommend.objects.filter(uid=uid).delete()
            Newssee.objects.filter(uid=uid).delete()
            Newscomment.objects.filter(uid=uid).delete()
            Like.objects.filter(uid=uid).delete()
            Collection.objects.filter(uid=uid).delete()
            return JsonResponse({'success': True})  # 返回成功响应
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': '用户不存在'})  # 返回用户不存在的错误响应

    return JsonResponse({'success': False, 'message': '仅接受 POST 请求'})  # 返回错误响应


def manage_news(request):
    info_dict = request.session["info"]
    uid = info_dict['uid']  # 已经进行了用户认证
    # 该用户所浏览的全部新闻信息
    newslist = []
    newslist = News.objects.all().order_by('-timeliness')
    page = int(request.GET.get('page', 1))
    page_size = 10
    start = (page - 1) * page_size
    end = page * page_size
    # 记录总数
    renews_count = len(newslist)
    #
    newslist = newslist[start:end]
    renews_page_count, div = divmod(renews_count, page_size)
    # 分页功能
    # 计算页码
    if div:
        renews_page_count += 1
    plus = 2
    if renews_page_count <= 2 * plus + 1:
        start_page = 1
        end_page = renews_page_count
    else:
        if page <= plus:
            start_page = 1
            end_page = 2 * plus + 1
        else:
            start_page = page - plus
            end_page = page + plus
    page_str_list_news = []

    # 上一页
    if page > 1:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">上一页</a></li>'.format(page - 1)
    else:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">上一页</a></li>'.format(1)
    page_str_list_news.append(prev)
    # 页面
    for i in range(start_page, end_page + 1):
        if i == page:
            ele = '<li class="page-item active" ><a class="page-link" href="?page={}">{}</a></li>'.format(i, i)
        else:
            ele = '<li class="page-item " ><a class="page-link" href="?page={}">{}</a></li>'.format(i, i)
        page_str_list_news.append(ele)
    # 下一页
    if page < renews_page_count:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">下一页</a></li>'.format(page + 1)
    else:
        prev = '<li class="page-item"><a class="page-link" href="?page={}">下一页</a></li>'.format(renews_page_count)
    page_str_list_news.append(prev)
    page_str_news = mark_safe(''.join(page_str_list_news))

    # 查找
    value = request.GET.get('newsq')
    data_dict = {}
    search_none = False
    blank_success = True
    if value:
        blank_success = False
        data_dict['newstitle__contains'] = value
        searchresult = models.News.objects.filter(**data_dict)
        if searchresult is None or len(searchresult) == 0:
            search_none = True
    else:
        blank_success = True
        searchresult = models.News.objects.none()

    userinfoobj = User.objects.filter(uid=uid).first()
    return render(request, "manage_news.html", {
        "newslist": newslist, 'page_str_news': page_str_news,
        'blank_success': blank_success, 'search_none': search_none,
        'searchresult': searchresult})


def manage_deletenews(request):
    if request.method == "POST":
        newsid = request.POST.get('newsid')

        try:
            # 尝试从数据库中获取要删除的新闻对象
            news = News.objects.get(newsid=newsid)
            news.delete()  # 删除新闻
            Newsrecommend.objects.filter(news_id=newsid).delete()
            Like.objects.filter(news_id=newsid).delete()
            Newscomment.objects.filter(news_id=newsid).delete()
            Collection.objects.filter(news_id=newsid).delete()
            Newssee.objects.filter(news_id=newsid).delete()
            return JsonResponse({'success': True})  # 返回成功响应
        except News.DoesNotExist:
            return JsonResponse({'success': False, 'message': '新闻不存在'})  # 返回用户不存在的错误响应

    return JsonResponse({'success': False, 'message': '仅接受 POST 请求'})  # 返回错误响应


def manage_spider(request):
    info_dict = request.session["info"]
    uid = info_dict['uid']  # 已经进行了用户认证
    typelist = Newstype.objects.all()
    userinfoobj = User.objects.filter(uid=uid).first()
    return render(request, "manage_spider.html", {'typelist': typelist})

def moredetails(request):
    return render(request, "moredetails.html")