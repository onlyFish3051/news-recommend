from datetime import datetime
from selenium.webdriver.support import expected_conditions as EC
from django.http import JsonResponse
from django.shortcuts import redirect, render
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service  # 导入 Service 类
from bs4 import BeautifulSoup
import os
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
import urllib.parse

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangoProject01.settings')
import django
django.setup()
from appnewsre.models import News, User, Newsrecommend


def clean_string(value):
    """
    移除无法存储的字符（非 UTF-8 兼容字符）
    """
    if not value:
        return value
    try:
        # 编码为 UTF-8 并忽略无法编码的字符，然后解码回字符串
        return value.encode('utf-8', 'ignore').decode('utf-8')
    except Exception as e:
        print(f"Error cleaning string: {value}. Error: {e}")
        return ""


def is_valid_utf8mb4(value):
    """
    检查字符串是否完全兼容 utf8mb4 字符集
    """
    if not value:
        return False
    try:
        # 尝试编码为 utf8mb4，并确保没有无效字符
        value.encode('utf-8').decode('utf-8')
        return True
    except UnicodeEncodeError:
        return False


def fetch_news_from_toutiao(request):
    if request.method == 'POST':
        # 从前端获取的其他值
        urllist = [
            'https://www.toutiao.com/?channel=finance&source=tuwen_detail',
            'https://www.toutiao.com/?channel=tech&source=tuwen_detail',
            'https://www.toutiao.com/?channel=sports&source=tuwen_detail',
            'https://www.toutiao.com/?channel=history&source=tuwen_detail',
            'https://www.toutiao.com/?channel=world&source=tuwen_detail',
            'https://www.toutiao.com/?channel=entertainment&source=tuwen_detail',
            'https://www.toutiao.com/?channel=food&source=tuwen_detail',
            'https://www.toutiao.com/?channel=military&source=tuwen_detail'
        ]
        cname = request.POST.get('cname')
        cid = request.POST.get('cid')  # 获取 data-cid 的值
        print(f'类别id:{cid}')
        print(f'类别名称:{cname}')
        url = urllist[int(cid) - 1]
        # 创建 Chrome WebDriver 实例
        options = Options()
        options.add_argument("--headless")  # 以无头模式运行浏览器
        service = Service()  # 创建 Service 实例
        driver = webdriver.Chrome(service=service, options=options)

        try:
            valid_news_count = 0
            base_url = 'https://www.toutiao.com'

            # 打开页面
            driver.get(url)
            time.sleep(3)  # 等待页面加载完成

            while valid_news_count < 10:  # 循环直到爬取到 10 条有效新闻
                # 使用显式等待等待页面元素加载
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a.title'))
                )

                # 获取页面内容
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                # 查找符合条件的新闻链接
                news_links = soup.find_all('a', class_='title')

                for link in news_links:
                    try:
                        href = link['href'].strip()
                        if not href.startswith('/article/'):  # 只处理文章链接
                            continue

                        full_url = urllib.parse.urljoin(base_url, href)  # 转换为完整 URL
                        driver.get(full_url)
                        # 使用显式等待等待页面元素加载
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, '.article-content h1'))
                        )
                        # 获取页面内容
                        soup = BeautifulSoup(driver.page_source, 'html.parser')
                        # 提取新闻标题
                        newstitle_element = soup.select_one('.article-content h1')
                        newstitle = clean_string(newstitle_element.text.strip()) if newstitle_element else ''

                        # 检查标题是否符合 utf8mb4 字符集
                        if not is_valid_utf8mb4(newstitle):
                            print(f"Skipping invalid title (not utf8mb4): {newstitle} at URL: {full_url}")
                            continue  # 直接跳过该 URL

                        # 检查新闻标题是否已存在，如果存在则跳过当前新闻
                        if News.objects.filter(newstitle=newstitle).exists():
                            print(f"Skipping duplicate title: {newstitle}")
                            continue

                        # 提取新闻日期
                        newsdate_element1 = soup.select_one('.article-content .article-meta span:nth-of-type(1)')
                        if newsdate_element1 and (newsdate_element1.text.strip() == '首发' or newsdate_element1.text.strip() == '原创'):
                            newsdate_element2 = soup.select_one('.article-content .article-meta span:nth-of-type(2)')
                            newsdate = clean_string(newsdate_element2.text.strip()) if newsdate_element2 else ''
                        else:
                            newsdate = clean_string(newsdate_element1.text.strip()) if newsdate_element1 else ''

                        # 提取新闻作者
                        newsauthor_element = soup.select_one('.article-content .article-meta a')
                        newsauthor = clean_string(newsauthor_element.text.strip()) if newsauthor_element else ''

                        # 提取新闻内容
                        newscontent_elements = soup.select('.article-content .syl-article-base p')
                        newscontent = '\n'.join([clean_string(p.text.strip()) for p in newscontent_elements])
                        if not newscontent:
                            print(f"Skipping empty content at URL: {full_url}")
                            continue

                        # 提取新闻图片链接
                        newsimg_element = soup.select_one('.article-content .syl-article-base img')
                        newsimg = newsimg_element['src'] if newsimg_element else ''

                        try:
                            last_news_item = News.objects.latest('newsid')
                            last_newsid_value = last_news_item.newsid if last_news_item else 0
                            print(f"The last news ID is: {last_newsid_value}")
                        except News.DoesNotExist:
                            print("No News items found.")
                            last_newsid_value = 0

                        # 创建 News 对象并保存到数据库
                        news_obj = News(
                            newsid=last_newsid_value + 1,
                            newstitle=newstitle,
                            newscontent=newscontent,
                            newsdate=newsdate,
                            newsauthor=newsauthor,
                            cid=cid,
                            seetimes=0,
                            newsimg=newsimg,
                            cname=cname,
                            fire=0
                        )
                        news_obj.save()
                        print("News saved successfully:", newstitle, newsauthor)

                        # 更新推荐表
                        userlist = User.objects.filter(usertype=1).values_list('uid', flat=True)
                        for uid in userlist:
                            renewsobj = Newsrecommend(
                                uid=uid,
                                cid=cid,
                                news_id=last_newsid_value + 1,
                            )
                            renewsobj.save()

                        # 更新计数器
                        valid_news_count += 1
                        if valid_news_count >= 15:  # 如果已经爬取到 10 条有效新闻，则停止
                            break

                    except (TimeoutException, WebDriverException) as e:
                        print(f"Failed to load page: {full_url}. Error: {e}")
                        continue

                # 如果仍未达到 10 条有效新闻，尝试滚动加载更多内容
                if valid_news_count < 10:
                    try:
                        # 模拟滚动到底部以加载更多新闻
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(3)  # 等待新内容加载
                    except Exception as e:
                        print(f"Failed to load more content. Error: {e}")
                        break

            # 返回成功提示，只显示成功爬取的数量
            return JsonResponse({'success': True, 'message': f'成功爬取 {valid_news_count} 条新闻'})

        except Exception as e:
            print(f"An error occurred: {e}")
            return JsonResponse({'success': False, 'message': '新闻爬取失败'})
        finally:
            # 关闭 WebDriver
            driver.quit()
    else:
        # 如果不是 POST 请求，则直接渲染页面
        return render(request, 'manage_spider.html')