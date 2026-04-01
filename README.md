# Certbot DNS Aliyun ESA Plugin

这是一个Certbot插件，用于通过阿里云ESA（Edge Security Acceleration）API进行DNS-01验证。

## 功能

- 通过阿里云ESA API自动添加和删除TXT记录
- 支持自动查找ESA站点
- 支持手动指定站点ID
- 完整的错误处理和日志记录

## 安装

### 从源码安装

```bash
git clone https://github.com/yourusername/certbot-dns-aliyun-esa.git
cd certbot-dns-aliyun-esa
pip install -e .
```

## 依赖

- Python 3.10+ 
- certbot >= 3.1.0
- alibabacloud_esa20240910 >= 2.30.0

## 配置

### 1. 创建凭证文件

创建凭证文件 ~/.certbot/aliyun-esa-credentials.ini：

```INI
dns_aliyun_esa_access_id=your_access_key_id
dns_aliyun_esa_access_secret=your_access_key_secret
dns_aliyun_esa_site_id=your_site_id
```

确保文件权限安全：

```BASH
chmod 600 ~/.certbot/aliyun-esa-credentials.ini
```

### 2. 获取阿里云AccessKey

1. 登录阿里云控制台
2. 进入"访问控制" -> "用户" -> 创建或选择用户
3. 为用户添加"AliyunESAFullAccess"权限
4. 创建AccessKey并保存ID和Secret

# 使用方法

## 基本用法

```BASH
# 自动查找站点
certbot certonly \
  --authenticator dns-aliyun-esa \
  --dns-aliyun-esa-credentials ~/.certbot/aliyun-esa-credentials.ini \
  -d example.com \
  -d *.example.com
```

## 参数说明

--dns-aliyun-esa-credentials: 凭证文件路径（必需）
--dns-aliyun-esa-site-id: ESA站点ID（可选，如果不提供会自动查找）
--dns-aliyun-esa-propagation-seconds: DNS传播等待时间（可选，默认30秒）

# 工作原理

1. Certbot调用插件进行DNS-01验证
2. 插件通过阿里云ESA API添加TXT记录
3. 等待DNS记录传播
4. Let's Encrypt验证TXT记录
5. 插件清理TXT记录
6. Certbot颁发证书

# 故障排除

## 常见问题

1. 权限不足

- 确保AccessKey有足够的权限
- 需要"AliyunESAFullAccess"或相关权限

2. 找不到站点

- 确保域名已在ESA中配置
- 可以手动指定站点ID：--dns-aliyun-esa-site-id

3. API调用失败

- 检查AccessKey是否正确
- 检查地域ID是否正确
- 查看详细日志：certbot ... --verbose

## 查看日志

```BASH
# 启用详细日志
certbot ... --verbose

# 查看Certbot日志
tail -f /var/log/letsencrypt/letsencrypt.log
```

# 开发

## 项目结构

```TEXT
certbot-dns-aliyun-esa/
├── certbot_dns_aliyun_esa/
│   ├── __init__.py
│   ├── __main__.py
│   ├── esa_client.py          # ESA API客户端
│   └── certbot_dns_aliyun_esa.py  # Certbot插件
├── setup.py
├── README.md
└── requirements.txt
```

# 支持

查看[阿里云ESA文档](https://help.aliyun.com/zh/edge-security-acceleration/esa/esa-sdk-reference?spm=5176.29099518.console-base_help.dexternal.5e8b4a9bOXtFzJ)

查看[Certbot文档](https://eff-certbot.readthedocs.io/en/stable/)
