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
    
    # RSS源列表 - 使用全球可访问的、稳定的源
    rss_sources = [
        # CNBC (美国财经网络电视)
        {'url': 'https://www.cnbc.com/id/100003114/device/rss/rss.html', 'source': 'CNBC', 'priority': 1},
        
        # Yahoo Finance
        {'url': 'https://feeds.finance.yahoo.com/rss/2.0/headline', 'source': 'Yahoo Finance', 'priority': 1},
        
        # Investor's Business Daily
        {'url': 'https://feeds.investors.com/feeds/ibd-top-10.xml', 'source': 'IBD', 'priority': 1},
        
        # Financial Express (印度财经)
        {'url': 'https://www.financialexpress.com/feed/', 'source': 'Financial Express', 'priority': 2},
        
        # Business Insider
        {'url': 'https://feeds.businessinsider.com/markets/news', 'source': 'Business Insider', 'priority': 2},
        
        # The Motley Fool
        {'url': 'https://feeds.fool.com/foolscoop/index.xml', 'source': 'The Motley Fool', 'priority': 2},
    ]
    
    # 强化关键词（中英文混合，适应国际财经新闻）
    keywords = [
        # 央行相关
        '美联储', 'Federal Reserve', 'Fed', 'interest rate', '央行', 'central bank', 'monetary policy', '降息', '加息',
        
        # 政治经济
        'Trump', '特朗普', 'President', '总统', '政府', 'government', 'policy', '政策',
        
        # 股市
        'stock', '股票', 'stock market', '股市', 'index', '指数', 'Nasdaq', 'NYSE', 'Dow Jones',
        'S&P 500', '上证', '深证', '创业板', 'Shanghai', 'Shenzhen',
        
        # 经济指标
        'inflation', '通胀', 'GDP', 'unemployment', '就业', 'CPI', 'PPI', '经济',
        'earnings', '盈利', 'revenue', '收入', 'profit', '利润',
        
        # 行业与公司
        'Tesla', 'Apple', 'Microsoft', 'Amazon', 'Google',
        'Bitcoin', '比特币', 'crypto', '加密', 'technology', '科技',
        'energy', '能源', 'oil', '油价', 'banking', '银行',
        
        # 汇率外汇
        'exchange rate', '汇率', 'yuan', '人民币', 'dollar', 'euro', '欧元',
        
        # 债券市场
        'bond', '债券', 'Treasury', '国债', 'yield', '收益率',
        
        # 贸易与关税
        'trade', '贸易', 'tariff', '关税', 'commerce', '商业',
        
        # 房地产
        'real estate', '房地产', 'property', '房产', 'housing', '住房',
        
        # 其他常见词
        'market', '市场', 'price', '价格', 'rise', '上升', 'fall', '下降',
        'gain', 'loss', '涨', '跌', 'surge', '飙升', 'crash', '崩盘'
    ]
    
    
    for rss_info in rss_sources:
        try:
            print(f"尝试抓取 {rss_info['source']} (优先级{rss_info['priority']})...")
            # 用 requests 拉取，带 User-Agent，再交给 feedparser 解析
            try:
                resp = requests.get(
                    rss_info['url'], 
                    headers=REQUEST_HEADERS, 
                    timeout=20,  # 增加超时时间
                    verify=False  # 忽略SSL验证
                )
                resp.raise_for_status()
                resp.encoding = resp.apparent_encoding or 'utf-8'
                feed = feedparser.parse(resp.content)
            except requests.exceptions.Timeout:
                print(f"  {rss_info['source']} 连接超时，跳过")
                continue
            except requests.exceptions.ConnectionError as e:
                print(f"  {rss_info['source']} 网络错误: {str(e)[:50]}...")
                continue
            except Exception as e:
                print(f"  {rss_info['source']} 获取失败: {str(e)[:50]}...")
                continue
            
            if not feed.entries:
                print(f"  {rss_info['source']} 无条目")
                continue
                
            current_time = datetime.now()
            taken = 0
            max_per_source = 15  # 扩大单源获取数量
            
            for entry in feed.entries:
                if taken >= max_per_source:
                    break
                title = entry.get('title', '').strip()
                if not title:
                    continue
                
                # 获取发布时间（可选，但不强制过滤）
                pub_time = None
                try:
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_time = datetime(*entry.published_parsed[:6])
                        # 放宽到72小时，但优先显示24小时内的
                        if current_time - pub_time > timedelta(hours=72):
                            continue
                except Exception:
                    pass  # 如果无法解析时间，仍然保留
                
                summary = entry.get('summary', '') or entry.get('description', '')
                if summary and hasattr(summary, 'replace'):
                    summary = re.sub(r'<[^>]+>', '', summary)
                else:
                    summary = ''
                
                content = (title + ' ' + summary)
                # 改进关键词检测：任意匹配都算"重要"
                is_highlight = any(kw in content for kw in keywords)
                # 如果没有关键词但有内容，仍然保留（重要性稍低）
                
                news_item = {
                    'title': title,
                    'description': (summary[:200] if summary else ''),
                    'url': entry.get('link', ''),
                    'source': rss_info['source'],
                    'publishedAt': entry.get('published', ''),
                    'highlight': is_highlight,
                    'time_diff': (current_time - pub_time).total_seconds() / 3600 if pub_time else None,
                }
                news_list.append(news_item)
                taken += 1
            
            print(f"  获取 {taken} 条新闻")
        except Exception as e:
            print(f"  {rss_info['source']} 处理异常: {str(e)[:50]}...")
            continue
    
    # 若一条都没有，做兜底：不限制时间，从能用的源取最新几条
    if not news_list:
        print("\n⚠️ 主列表为空，执行兜底策略...")
        for rss_info in rss_sources:
            try:
                print(f"  兜底尝试: {rss_info['source']}")
                resp = requests.get(
                    rss_info['url'], 
                    headers=REQUEST_HEADERS, 
                    timeout=20,
                    verify=False
                )
                resp.raise_for_status()
                resp.encoding = resp.apparent_encoding or 'utf-8'
                feed = feedparser.parse(resp.content)
                
                for entry in (feed.entries or [])[:20]:  # 兜底增加到20条
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
                        'time_diff': None,
                    })
                
                if news_list:
                    print(f"  ✓ 兜底获取 {len(news_list)} 条新闻")
                    break
            except Exception as e:
                print(f"  ✗ 兜底失败 {rss_info['source']}: {str(e)[:30]}...")
                continue
    
    # 优先展示含关键词的，再按时间排序
    news_list.sort(key=lambda x: (
        not x.get('highlight', False),  # 优先显示有关键词的
        -(x.get('time_diff', 999) or 999)  # 再按时间新旧排序
    ))
    
    return news_list

def fetch_news_from_web_scraping():
    """备用方案：直接从网页爬取财经新闻"""
    news_list = []
    
    # 爬取的网站列表 - 全球可访问的财经网站
    scrape_sources = [
        {
            'url': 'https://news.google.com/topics/CAAqKggKEhAP-nZ_GqJEFQryfS9NqMEsqAEwkqKBBigBKkAP-nZ_GqJEFQryfS9NqMEsqAEwkqKBBg',
            'name': 'Google News - Business',
            'parser': 'simple'
        },
        {
            'url': 'https://www.cnbc.com/markets/',
            'name': 'CNBC Markets',
            'parser': 'simple'
        },
        {
            'url': 'https://www.bloomberg.com/markets',
            'name': 'Bloomberg Markets',
            'parser': 'simple'
        }
    ]
    
    from bs4 import BeautifulSoup
    
    for source in scrape_sources:
        try:
            print(f"  尝试爬取 {source['name']}...")
            response = requests.get(
                source['url'],
                headers=REQUEST_HEADERS,
                timeout=15,
                verify=False
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 通用新闻项提取
            articles = soup.find_all('article')[:10] or soup.find_all('a', {'data-article-id': True})[:10]
            
            for article in articles[:10]:
                try:
                    title = None
                    link = None
                    
                    # 尝试多种选择器
                    title_elem = article.find('h2') or article.find('h3') or article.find('a')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                    
                    if not title:
                        continue
                    
                    link_elem = article.find('a', href=True)
                    if link_elem:
                        link = link_elem['href']
                        if not link.startswith('http'):
                            link = 'https://' + source['url'].split('/')[2] + link
                    
                    if title and len(title) > 5:
                        news_list.append({
                            'title': title[:200],
                            'description': '',
                            'url': link or '',
                            'source': source['name'],
                            'publishedAt': '',
                            'highlight': True,
                            'time_diff': 0,
                        })
                except Exception:
                    continue
            
            if len(news_list) >= 5:
                print(f"  ✓ 爬取到 {len(news_list)} 条新闻")
                break
        except Exception as e:
            print(f"  ✗ 爬取失败: {str(e)[:30]}...")
            continue
    
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
        return "📰 过去24小时未发现重要财经新闻，但系统正常运行。如果持续无新闻，请检查RSS源是否可访问。"
    
    # 去重（基于标题）
    seen_titles = set()
    unique_news = []
    for news in news_list:
        title = news.get('title', '')
        if title and title not in seen_titles:
            seen_titles.add(title)
            unique_news.append(news)
    
    # 统计信息
    highlight_count = sum(1 for n in unique_news if n.get('highlight'))
    
    # 按来源分组
    content = f"📊 财经早报 - {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n"
    content += "=" * 50 + "\n\n"
    content += f"📈 统计信息\n"
    content += f"  • 总新闻数：{len(unique_news)} 条\n"
    content += f"  • 重要新闻：{highlight_count} 条\n"
    content += f"  • 更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    if len(unique_news) == 0:
        content += "⚠️ 暂无新闻数据\n"
        return content
    
    # 按重要性和来源分类显示
    highlight_news = [n for n in unique_news if n.get('highlight')]
    normal_news = [n for n in unique_news if not n.get('highlight')]
    
    # 先显示重要新闻
    if highlight_news:
        content += "⭐ 【重要新闻】\n"
        content += "-" * 50 + "\n"
        for idx, news in enumerate(highlight_news[:10], 1):  # 显示前10条重要新闻
            title = news.get('title', '无标题')
            description = news.get('description', '')
            url = news.get('url', '')
            source = news.get('source', '未知来源')
            time_info = ""
            if news.get('time_diff') is not None:
                hours = int(news.get('time_diff', 0))
                if hours < 1:
                    time_info = " (刚刚)"
                elif hours < 24:
                    time_info = f" ({hours}小时前)"
                else:
                    time_info = f" ({hours//24}天前)"
            
            content += f"{idx}. 【{source}】{title}{time_info}\n"
            if description:
                content += f"   {description}...\n"
            if url:
                content += f"   🔗 {url}\n"
            content += "\n"
    
    # 再显示普通新闻
    if normal_news:
        remaining = min(10, len(normal_news))  # 最多再显示10条
        content += f"\n📰 【其他新闻】(显示前{remaining}条)\n"
        content += "-" * 50 + "\n"
        for idx, news in enumerate(normal_news[:remaining], 1):
            title = news.get('title', '无标题')
            source = news.get('source', '未知来源')
            time_info = ""
            if news.get('time_diff') is not None:
                hours = int(news.get('time_diff', 0))
                if hours < 1:
                    time_info = " (刚刚)"
                elif hours < 24:
                    time_info = f" ({hours}小时前)"
            
            content += f"{idx}. 【{source}】{title}{time_info}\n"
        
        if len(normal_news) > remaining:
            content += f"\n...还有 {len(normal_news) - remaining} 条新闻未显示\n"
    
    content += "\n" + "=" * 50 + "\n"
    content += "✨ 更多财经资讯请访问：新浪财经、东方财富\n"
    
    return content

def send_via_serverchan(content):
    """通过Server酱API推送到微信"""
    send_key = os.getenv('SERVERCHAN_SEND_KEY', '')
    
    if not send_key:
        print("⚠️ 未配置SERVERCHAN_SEND_KEY，跳过微信推送")
        print("   请在GitHub Secrets中添加 SERVERCHAN_SEND_KEY")
        print("   获取方式：访问 https://sctapi.ftqq.com/ 微信扫码登录获取")
        return False
    
    # Server酱最新API地址
    url = f"https://sctapi.ftqq.com/{send_key}.send"
    
    title = f"📊 财经早报 - {datetime.now().strftime('%m月%d日')}"
    
    data = {
        'title': title,
        'desp': content
    }
    
    try:
        print(f"正在推送到Server酱: {url[:50]}...")
        response = requests.post(url, data=data, timeout=10)
        result = response.json()
        
        if response.status_code == 200 and result.get('code') == 0:
            print("✅ 微信推送成功 - 已发送到微信")
            return True
        else:
            error_msg = result.get('message', '未知错误')
            error_code = result.get('code', 'N/A')
            print(f"❌ 微信推送失败")
            print(f"   错误代码: {error_code}")
            print(f"   错误信息: {error_msg}")
            
            # 常见错误诊断
            if error_code == 40001:
                print("   💡 提示：SendKey可能已过期，请重新获取")
            elif error_code == 40002:
                print("   💡 提示：SendKey格式错误")
            
            return False
    except Exception as e:
        print(f"❌ 微信推送异常: {e}")
        print(f"   请检查网络连接或Server酱服务是否可用")
        return False

def send_email(content, recipient_email):
    """发送邮件（QQ邮箱优先使用465端口SSL，失败则尝试587 TLS）"""
    sender_email = os.getenv('EMAIL_SENDER', '')
    email_password = os.getenv('EMAIL_PASSWORD', '')
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.qq.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    
    if not sender_email or not email_password:
        print("⚠️ 未配置邮箱信息")
        print("   需要配置的环境变量:")
        print("   • EMAIL_SENDER: 发送者邮箱地址")
        print("   • EMAIL_PASSWORD: 邮箱密码或授权码")
        print("   • EMAIL_RECIPIENT: 接收者邮箱地址")
        print("   • SMTP_SERVER: SMTP服务器地址 (默认: smtp.qq.com)")
        print("   • SMTP_PORT: SMTP服务器端口 (默认: 587)")
        return False
    
    if not recipient_email:
        recipient_email = sender_email  # 默认发送给自己
        print(f"📧 发送给: {recipient_email} (默认发送给自己)")
    else:
        print(f"📧 发送给: {recipient_email}")
    
    subject = f"财经早报 - {datetime.now().strftime('%Y年%m月%d日')}"
    html_content = content.replace('\n', '<br>')
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = Header(subject, 'utf-8')
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))
    
    print(f"   SMTP服务器: {smtp_server}:{smtp_port}")
    
    # 先尝试 465 端口 SSL（QQ邮箱更稳定）
    if smtp_server == 'smtp.qq.com':
        try:
            print("   尝试使用 465 端口 SSL 连接...")
            server = smtplib.SMTP_SSL(smtp_server, 465, timeout=15)
            server.login(sender_email, email_password)
            server.sendmail(sender_email, [recipient_email], msg.as_string())
            server.quit()
            print("   ✅ 邮件发送成功 (465 SSL)")
            return True
        except smtplib.SMTPAuthenticationError:
            print("   ❌ 465 端口认证失败（可能是授权码错误）")
        except Exception as e465:
            print(f"   ❌ 465 SSL 连接失败: {e465}")
    
    # 587 TLS 或其他邮箱
    try:
        print(f"   尝试使用 {smtp_port} 端口 TLS 连接...")
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=15)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(sender_email, email_password)
        server.sendmail(sender_email, [recipient_email], msg.as_string())
        server.quit()
        print(f"   ✅ 邮件发送成功 ({smtp_port} TLS)")
        return True
    except smtplib.SMTPAuthenticationError:
        print(f"   ❌ {smtp_port} 端口认证失败")
        print("   💡 请检查:")
        print("      1. EMAIL_PASSWORD 是否为正确的授权码（非QQ密码）")
        print("      2. SMTP服务是否已在邮箱设置中开启")
        return False
    except Exception as e:
        print(f"   ❌ 邮件发送失败: {e}")
        print("   💡 请检查:")
        print("      1. 网络连接是否正常")
        print("      2. SMTP_SERVER 和 SMTP_PORT 是否正确")
        print("      3. 邮箱SMTP服务是否已开启")
        return False

def main():
    print("=" * 60)
    print("🚀 开始财经新闻抓取和推送")
    print(f"   执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 抓取新闻
    all_news = []
    
    print("\n[1/5] 从RSS源抓取新闻...")
    print("-" * 60)
    rss_news = fetch_news_from_rss()
    all_news.extend(rss_news)
    print(f"✓ RSS源获取 {len(rss_news)} 条新闻")
    print(f"  其中重要新闻 {sum(1 for n in rss_news if n.get('highlight'))} 条")
    
    print("\n[2/5] 从NewsAPI抓取新闻...")
    print("-" * 60)
    api_news = fetch_news_from_api()
    all_news.extend(api_news)
    print(f"✓ API获取 {len(api_news)} 条新闻")
    print(f"  其中重要新闻 {sum(1 for n in api_news if n.get('highlight'))} 条")
    
    # 备用方案：如果RSS和API都没有获取到足够的新闻，尝试web爬虫
    if len(all_news) < 5:
        print("\n[3/5] 备用方案：网页爬虫...")
        print("-" * 60)
        web_news = fetch_news_from_web_scraping()
        all_news.extend(web_news)
        print(f"✓ 网页爬虫获取 {len(web_news)} 条新闻")
    else:
        print("\n[3/5] 备用方案：网页爬虫 (跳过，已有足够新闻)")
    
    print("\n[4/5] 格式化新闻内容...")
    print("-" * 60)
    print(f"✓ 总共获取 {len(all_news)} 条新闻")
    highlight_sum = sum(1 for n in all_news if n.get('highlight'))
    print(f"  其中重要新闻 {highlight_sum} 条")
    
    # 格式化内容
    content = format_news_content(all_news)
    
    # 推送
    print("\n[5/5] 执行推送...")
    print("-" * 60)
    
    print("\n📱 微信推送:")
    send_via_serverchan(content)
    
    print("\n📧 邮件推送:")
    recipient_email = os.getenv('EMAIL_RECIPIENT', '')
    send_email(content, recipient_email)
    
    print("\n" + "=" * 60)
    print("✅ 任务完成！")
    print("=" * 60)

if __name__ == '__main__':
    main()
