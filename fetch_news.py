#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财经新闻抓取和推送脚本
抓取过去24小时的财经新闻，通过Server酱推送到微信，并发送邮件
"""

import requests
import json
from datetime import datetime, timedelta
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import feedparser
import re
import time

# 请求头，避免被部分站点拒绝
REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/rss+xml, application/xml, text/xml, */*',
}

def fetch_news_from_rss():
    """从RSS源抓取财经新闻（财经源直接取最新条目，不依赖关键词过滤）"""
    news_list = []
    
    # 财经新闻RSS源列表（多源保证有内容）
    rss_sources = [
        {'url': 'https://feed.finance.sina.com.cn/realstock/newsuniverse_sh.xml', 'source': '新浪财经'},
        {'url': 'https://feed.finance.sina.com.cn/realstock/newsuniverse_sz.xml', 'source': '新浪财经'},
        {'url': 'https://www.eastmoney.com/rss/news.html', 'source': '东方财富'},
        {'url': 'https://rss.sina.com.cn/finance/stock.xml', 'source': '新浪股票'},
    ]
    
    # 关键词用于优先展示（不满足也保留，保证有内容）
    keywords = ['美联储', '美国总统', '央行', '利率', '通胀', '股市', '汇率', '经济', 
                '财政', '政策', 'GDP', '就业', 'CPI', 'PPI', '加息', '降息', '量化宽松', 'A股', '港股', '美股']
    
    for rss_info in rss_sources:
        try:
            # 用 requests 拉取，带 User-Agent，再交给 feedparser 解析
            resp = requests.get(rss_info['url'], headers=REQUEST_HEADERS, timeout=15)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or 'utf-8'
            feed = feedparser.parse(resp.content)
            
            if not feed.entries:
                continue
                
            current_time = datetime.now()
            taken = 0
            max_per_source = 12
            
            for entry in feed.entries:
                if taken >= max_per_source:
                    break
                title = entry.get('title', '').strip()
                if not title:
                    continue
                try:
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_time = datetime(*entry.published_parsed[:6])
                        if current_time - pub_time > timedelta(hours=48):
                            continue  # 超过48小时的不要，放宽到48h
                except Exception:
                    pass
                summary = entry.get('summary', '') or entry.get('description', '')
                if summary and hasattr(summary, 'replace'):
                    summary = re.sub(r'<[^>]+>', '', summary)
                else:
                    summary = ''
                content = (title + ' ' + summary)
                is_highlight = any(kw in content for kw in keywords)
                news_list.append({
                    'title': title,
                    'description': (summary[:200] if summary else ''),
                    'url': entry.get('link', ''),
                    'source': rss_info['source'],
                    'publishedAt': entry.get('published', ''),
                    'highlight': is_highlight,
                })
                taken += 1
        except Exception as e:
            print(f"抓取 {rss_info.get('source', rss_info['url'])} 失败: {e}")
            continue
    
    # 若一条都没有，做兜底：不限制时间，从第一个能用的源取最新几条
    if not news_list:
        for rss_info in rss_sources:
            try:
                resp = requests.get(rss_info['url'], headers=REQUEST_HEADERS, timeout=15)
                resp.raise_for_status()
                resp.encoding = resp.apparent_encoding or 'utf-8'
                feed = feedparser.parse(resp.content)
                for entry in (feed.entries or [])[:10]:
                    title = entry.get('title', '').strip()
                    if not title:
                        continue
                    summary = entry.get('summary', '') or entry.get('description', '')
                    if summary and hasattr(summary, 'replace'):
                        summary = re.sub(r'<[^>]+>', '', summary)
                    else:
                        summary = ''
                    news_list.append({
                        'title': title,
                        'description': (summary[:200] if summary else ''),
                        'url': entry.get('link', ''),
                        'source': rss_info['source'],
                        'publishedAt': entry.get('published', ''),
                        'highlight': False,
                    })
                if news_list:
                    break
            except Exception:
                continue
    
    # 优先展示含关键词的
    news_list.sort(key=lambda x: (not x.get('highlight', False), x.get('publishedAt', '')), reverse=False)
    return news_list

def fetch_news_from_api():
    """从NewsAPI抓取新闻（需要API密钥）"""
    news_list = []
    api_key = os.getenv('NEWS_API_KEY', '')
    
    if not api_key:
        print("未配置NEWS_API_KEY，跳过API新闻源")
        return news_list
    
    keywords = [
        'Federal Reserve',  # 美联储
        'US President',     # 美国总统
        'interest rate',     # 利率
        'inflation',         # 通胀
        'stock market',      # 股市
        'exchange rate',     # 汇率
        'central bank',      # 央行
        'monetary policy'    # 货币政策
    ]
    
    try:
        for keyword in keywords:
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': keyword,
                'sortBy': 'publishedAt',
                'language': 'en',
                'apiKey': api_key,
                'from': (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%S'),
                'pageSize': 5
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                articles = response.json().get('articles', [])
                for article in articles:
                    news_list.append({
                        'title': article.get('title', ''),
                        'description': article.get('description', '')[:200] if article.get('description') else '',
                        'url': article.get('url', ''),
                        'source': article.get('source', {}).get('name', 'NewsAPI'),
                        'publishedAt': article.get('publishedAt', '')
                    })
            
            time.sleep(1)  # 避免请求过快
    except Exception as e:
        print(f"API抓取失败: {e}")
    
    return news_list

def format_news_content(news_list):
    """格式化新闻内容为推送格式"""
    if not news_list:
        return "📰 过去24小时未发现重要财经新闻"
    
    # 去重（基于标题）
    seen_titles = set()
    unique_news = []
    for news in news_list:
        title = news.get('title', '')
        if title and title not in seen_titles:
            seen_titles.add(title)
            unique_news.append(news)
    
    # 按来源分组
    content = f"📊 财经早报 - {datetime.now().strftime('%Y年%m月%d日')}\n"
    content += "=" * 50 + "\n\n"
    content += f"共抓取到 {len(unique_news)} 条重要新闻\n\n"
    
    # 显示前15条
    for idx, news in enumerate(unique_news[:15], 1):
        title = news.get('title', '无标题')
        description = news.get('description', '')
        url = news.get('url', '')
        source = news.get('source', '未知来源')
        
        content += f"{idx}. 【{source}】{title}\n"
        if description:
            content += f"   {description}...\n"
        if url:
            content += f"   链接: {url}\n"
        content += "\n"
    
    return content

def send_via_serverchan(content):
    """通过Server酱API推送到微信"""
    send_key = os.getenv('SERVERCHAN_SEND_KEY', '')
    
    if not send_key:
        print("未配置SERVERCHAN_SEND_KEY，跳过微信推送")
        return False
    
    # Server酱最新API地址
    url = f"https://sctapi.ftqq.com/{send_key}.send"
    
    title = f"📊 财经早报 - {datetime.now().strftime('%m月%d日')}"
    
    data = {
        'title': title,
        'desp': content
    }
    
    try:
        response = requests.post(url, data=data, timeout=10)
        result = response.json()
        
        if response.status_code == 200 and result.get('code') == 0:
            print("✅ 微信推送成功")
            return True
        else:
            print(f"❌ 微信推送失败: {result.get('message', '未知错误')}")
            return False
    except Exception as e:
        print(f"❌ 微信推送异常: {e}")
        return False

def send_email(content, recipient_email):
    """发送邮件（QQ邮箱优先使用465端口SSL，失败则尝试587 TLS）"""
    sender_email = os.getenv('EMAIL_SENDER', '')
    email_password = os.getenv('EMAIL_PASSWORD', '')
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.qq.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    
    if not sender_email or not email_password:
        print("未配置邮箱信息，跳过邮件发送")
        return False
    
    if not recipient_email:
        recipient_email = sender_email  # 默认发送给自己
    
    subject = f"财经早报 - {datetime.now().strftime('%Y年%m月%d日')}"
    html_content = content.replace('\n', '<br>')
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = Header(subject, 'utf-8')
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))
    
    # 先尝试 465 端口 SSL（QQ邮箱更稳定）
    if smtp_server == 'smtp.qq.com':
        try:
            server = smtplib.SMTP_SSL(smtp_server, 465, timeout=15)
            server.login(sender_email, email_password)
            server.sendmail(sender_email, [recipient_email], msg.as_string())
            server.quit()
            print("✅ 邮件发送成功（465 SSL）")
            return True
        except Exception as e465:
            print(f"465 SSL 失败，尝试 587 TLS: {e465}")
    
    # 587 TLS 或 其他邮箱
    try:
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=15)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(sender_email, email_password)
        server.sendmail(sender_email, [recipient_email], msg.as_string())
        server.quit()
        print("✅ 邮件发送成功（587 TLS）")
        return True
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False

def main():
    print("=" * 50)
    print("开始抓取财经新闻...")
    print("=" * 50)
    
    # 抓取新闻
    all_news = []
    
    print("\n1. 从RSS源抓取新闻...")
    rss_news = fetch_news_from_rss()
    all_news.extend(rss_news)
    print(f"   从RSS源获取 {len(rss_news)} 条新闻")
    
    print("\n2. 从NewsAPI抓取新闻...")
    api_news = fetch_news_from_api()
    all_news.extend(api_news)
    print(f"   从API获取 {len(api_news)} 条新闻")
    
    print(f"\n总共获取 {len(all_news)} 条新闻")
    
    # 格式化内容
    content = format_news_content(all_news)
    
    # 推送
    print("\n3. 推送到微信...")
    send_via_serverchan(content)
    
    print("\n4. 发送邮件...")
    recipient_email = os.getenv('EMAIL_RECIPIENT', '')
    send_email(content, recipient_email)
    
    print("\n" + "=" * 50)
    print("任务完成！")
    print("=" * 50)

if __name__ == '__main__':
    main()
