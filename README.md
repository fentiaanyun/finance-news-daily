# 每日财经新闻自动推送

这是一个基于GitHub Actions的自动化财经新闻推送系统，每天早上8点自动抓取过去24小时的重要财经新闻，并通过Server酱推送到微信，同时发送邮件通知。

## 🆘 遇到问题？

如果看到 **"24小时没有重要新闻"** 或其他问题，请查看：
- 📖 **[诊断与重新配置指南](诊断与重新配置指南.md)** - 详细的问题排查和解决方案
- ✅ **[快速配置清单](快速配置清单.md)** - 快速检查配置是否正确

## 功能特点

- 📰 自动抓取过去24小时的财经新闻（智能降级策略确保有内容）
- 🔍 重点关注：美联储、美国总统、央行政策等重大财经新闻
- 📱 通过Server酱推送到微信
- 📧 自动发送邮件通知
- ⏰ 每天早上8点（北京时间）自动运行
- 🆓 完全免费，使用GitHub Actions免费额度
- ✨ 增强的错误诊断信息帮助快速定位问题

## 新闻来源

- 新浪财经RSS（上交、深交、股票）
- 东方财富RSS
- NewsAPI（可选，需要API密钥）
- 智能兜底机制确保无网络中断时仍有内容

## 部署步骤

### 第一步：准备必要的账号和密钥

#### 1. Server酱（微信推送）

1. 访问 [Server酱官网](https://sctapi.ftqq.com/)
2. 使用微信扫码登录
3. 在"发送消息"页面获取你的 `SendKey`
4. 记录下这个 `SendKey`，后续会用到

#### 2. 邮箱配置（邮件推送）

**QQ邮箱配置：**
- SMTP服务器：`smtp.qq.com`
- SMTP端口：`587`
- 需要开启SMTP服务并获取授权码（不是QQ密码）

**Gmail配置：**
- SMTP服务器：`smtp.gmail.com`
- SMTP端口：`587`
- 需要开启"应用专用密码"

**163邮箱配置：**
- SMTP服务器：`smtp.163.com`
- SMTP端口：`587`
- 需要开启SMTP服务并获取授权码

#### 3. NewsAPI（可选，用于获取国际新闻）

1. 访问 [NewsAPI官网](https://newsapi.org/)
2. 注册免费账号
3. 获取API密钥（免费版每天有请求限制）

### 第二步：创建GitHub仓库

1. 登录GitHub账号
2. 点击右上角的 `+` 图标，选择 `New repository`
3. 填写仓库信息：
   - Repository name: `finance-news-daily`（或你喜欢的名字）
   - Description: `每日财经新闻自动推送`
   - 选择 `Public` 或 `Private`（Private需要GitHub Pro）
   - **不要**勾选 "Initialize this repository with a README"
4. 点击 `Create repository`

### 第三步：上传代码文件

#### 方法1：使用Git命令行（推荐）

```bash
# 1. 克隆仓库（将YOUR_USERNAME替换为你的GitHub用户名）
git clone https://github.com/YOUR_USERNAME/finance-news-daily.git
cd finance-news-daily

# 2. 创建必要的目录
mkdir -p .github/workflows

# 3. 将以下文件复制到仓库目录：
#    - fetch_news.py
#    - requirements.txt
#    - .github/workflows/daily-news.yml
#    - README.md

# 4. 提交并推送
git add .
git commit -m "初始化财经新闻推送工作流"
git push -u origin main
```

#### 方法2：使用GitHub网页界面

1. 在仓库页面点击 `Add file` → `Upload files`
2. 将以下文件拖拽上传：
   - `fetch_news.py`
   - `requirements.txt`
   - `README.md`
3. 创建 `.github/workflows/` 目录：
   - 点击 `Add file` → `Create new file`
   - 输入路径：`.github/workflows/daily-news.yml`
   - 复制工作流文件内容并粘贴
   - 点击 `Commit new file`

### 第四步：配置GitHub Secrets

1. 进入你的GitHub仓库
2. 点击 `Settings`（设置）
3. 在左侧菜单找到 `Secrets and variables` → `Actions`
4. 点击 `New repository secret`，依次添加以下密钥：

#### 必需配置：

- **SERVERCHAN_SEND_KEY**
  - Name: `SERVERCHAN_SEND_KEY`
  - Value: 你的Server酱SendKey

- **EMAIL_SENDER**
  - Name: `EMAIL_SENDER`
  - Value: 你的发件邮箱地址（如：`your_email@qq.com`）

- **EMAIL_PASSWORD**
  - Name: `EMAIL_PASSWORD`
  - Value: 你的邮箱授权码（不是邮箱密码）

- **EMAIL_RECIPIENT**
  - Name: `EMAIL_RECIPIENT`
  - Value: 收件邮箱地址（可以是你自己的邮箱）

- **SMTP_SERVER**
  - Name: `SMTP_SERVER`
  - Value: 根据你的邮箱选择：
    - QQ邮箱：`smtp.qq.com`
    - Gmail：`smtp.gmail.com`
    - 163邮箱：`smtp.163.com`

- **SMTP_PORT**
  - Name: `SMTP_PORT`
  - Value: `587`

#### 可选配置：

- **NEWS_API_KEY**
  - Name: `NEWS_API_KEY`
  - Value: 你的NewsAPI密钥（如果使用）

### 第五步：启用GitHub Actions

1. 进入仓库的 `Actions` 标签页
2. 如果看到提示 "I understand my workflows, go ahead and enable them"，点击它
3. 如果没有提示，说明Actions已经启用

### 第六步：测试工作流

1. 在 `Actions` 标签页，找到 "每日财经新闻推送" 工作流
2. 点击工作流名称
3. 点击右侧的 `Run workflow` 按钮
4. 选择分支（通常是 `main` 或 `master`）
5. 点击绿色的 `Run workflow` 按钮
6. 等待工作流执行完成（通常需要1-2分钟）
7. 点击运行记录查看详细日志
8. 检查你的微信和邮箱是否收到推送

### 第七步：验证定时任务

工作流配置为每天早上8点（北京时间）自动运行。你可以：

1. 等待第二天早上8点自动运行
2. 或者修改 `.github/workflows/daily-news.yml` 中的cron表达式来测试

**Cron表达式说明：**
- `0 0 * * *` = 每天UTC 0点 = 北京时间早上8点
- `0 1 * * *` = 每天UTC 1点 = 北京时间早上9点
- `0 12 * * *` = 每天UTC 12点 = 北京时间晚上8点

## 常见问题

### 1. 工作流没有自动运行？

- 检查仓库是否为Public（Private仓库需要GitHub Pro才能使用Actions）
- 确认工作流文件路径正确：`.github/workflows/daily-news.yml`
- 检查cron表达式是否正确

### 2. 微信推送失败？

- 确认 `SERVERCHAN_SEND_KEY` 配置正确
- 检查Server酱账号是否正常
- 查看Actions运行日志中的错误信息

### 3. 邮件发送失败？

- 确认邮箱授权码正确（不是邮箱密码）
- 检查SMTP服务器和端口配置
- 确认邮箱已开启SMTP服务
- 对于Gmail，需要开启"应用专用密码"

### 4. 没有抓取到新闻？

- RSS源可能暂时不可用
- 检查网络连接
- 查看运行日志了解详细错误

### 5. 如何修改运行时间？

编辑 `.github/workflows/daily-news.yml` 文件中的cron表达式：
```yaml
- cron: '0 0 * * *'  # 修改这里的值
```

## 注意事项

1. GitHub Actions免费账户每月有2000分钟的运行时间限制
2. 每次运行大约需要1-2分钟，每天运行一次，一个月大约需要60分钟
3. 如果使用NewsAPI，注意免费版的请求限制
4. Server酱免费版每天有推送次数限制

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！
