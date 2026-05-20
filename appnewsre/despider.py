from datetime import datetime
from telnetlib import EC

from django.http import JsonResponse
from django.shortcuts import redirect, render
from selenium import webdriver
from selenium.webdriver.chrome.service import Service  # 导入 ChromeService
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

import os
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangoProject01.settings')
import django

django.setup()
from appnewsre.models import News, User, Newsrecommend


def fetch_news(request):
    if request.method == 'POST':
        # url从前端获取
        furl = request.POST.get('url')
        url = furl
        # 从前端获取的其他值
        cname = request.POST.get('cname')
        cid = request.POST.get('cid')  # 获取data-cid的值
        print(f'类别id:{cid}')
        print(f'类别名称:{cname}')
        # 创建 Chrome WebDriver 实例
        options = Options()
        options.add_argument("--headless")  # 以无头模式运行浏览器

        # 使用 ChromeService
        service = Service()
        driver = webdriver.Chrome(service=service, options=options)

        try:
            spidersuccess = False
            # 打开页面
            driver.get(url)

            # 等待页面动态加载完成
            time.sleep(2)  # 等待 2 秒

            # 获取页面内容
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            # 提取新闻标题
            newstitle_element = soup.select_one('.article-content h1')
            newstitle = newstitle_element.text.strip() if newstitle_element else ''

            # 提取新闻日期
            newsdate_element1 = soup.select_one('.article-content .article-meta span:nth-of-type(1)')
            if newsdate_element1.text.strip() == '首发' or newsdate_element1.text.strip() == '原创':
                newsdate_element2 = soup.select_one('.article-content .article-meta span:nth-of-type(2)')
                newsdate = newsdate_element2.text.strip()
            else:
                newsdate = newsdate_element1.text.strip() if newsdate_element1 else ''
            # 提取新闻作者
            newsauthor_element = soup.select_one('.article-content .article-meta a')
            newsauthor = newsauthor_element.text.strip() if newsauthor_element else ''

            # 提取新闻内容
            newscontent_elements = soup.select('.article-content .syl-article-base p')
            newscontent = '\n'.join([p.text.strip() for p in newscontent_elements])

            # 提取新闻图片链接
            newsimg_element = soup.select_one('.article-content .syl-article-base img')
            newsimg = newsimg_element['src'] if newsimg_element else ''
            try:
                last_news_item = News.objects.latest('newsid')
                if last_news_item is None:
                    last_newsid_value = 0
                last_newsid_value = last_news_item.newsid  # 这是一个整数
                print(f"The last news ID is: {last_newsid_value}")
            except News.DoesNotExist:
                print("No News items found.")
            # 判断一下有没有该新闻
            existnews = News.objects.filter(newstitle=newstitle, newsauthor=newsauthor).first()
            if existnews:
                spidersuccess = False
            else:
                spidersuccess = True
            # 创建 News 对象并保存到数据库
            news_obj = News(
                newsid=last_newsid_value + 1,
                newstitle=newstitle,
                newscontent=newscontent,
                newsdate=newsdate,
                newsauthor=newsauthor,
                # 类别需要换
                cid=cid,
                seetimes=0,
                newsimg=newsimg,
                # 这里也要换
                cname=cname,
                fire=0
            )
            news_obj.save()
            print("News saved successfully:", newstitle, newsauthor)
            userlist = User.objects.filter(usertype=1).values_list('uid', flat=True)
            for uid in userlist:
                renewsobj = Newsrecommend(
                    uid=uid,
                    cid=cid,
                    news_id=last_newsid_value + 1,
                )
                renewsobj.save()
            # 重定向到 /manage_spider/ 并返回成功提示
            return JsonResponse({'success': True, 'message': '新闻爬取成功'})
        finally:
            # 关闭 WebDriver
            driver.quit()
    else:
        # 如果不是 POST 请求，则直接渲染页面
        return render(request, 'manage_spider.html')