# Certbot DNS Aliyun ESA Plugin

这是一个 Certbot 插件，用于通过阿里云 ESA（Edge Security Acceleration）API 自动完成 DNS-01 验证。

> ESA 的 CNAME 接入站点不允许创建 TXT 记录，因此本插件只适用于 **NS 接入**的 ESA 站点。

## 安装

本仓库不发布 PyPI 包，推荐使用 uv 从源码创建独立环境：

```bash
git clone https://github.com/kyangconn/certbot-dns-aliyun-esa.git
cd certbot-dns-aliyun-esa
uv sync --locked --no-dev
uv run --locked --no-dev certbot plugins
```

最后一个命令的输出中应出现 `dns-aliyun-esa`。

## 依赖

- Python 3.10+
- Certbot 5.8.0+
- alibabacloud-esa20240910 3.15.1+
- uv

依赖版本由 `uv.lock` 锁定，运行环境不会与系统 Python 或系统安装的 Certbot 混用。

## 配置

### 1. 创建凭证文件

```bash
mkdir -p ~/.certbot
install -m 600 credentials.ini.example ~/.certbot/aliyun-esa-credentials.ini
editor ~/.certbot/aliyun-esa-credentials.ini
```

凭证文件内容如下：

```ini
dns_aliyun_esa_access_key_id = your_access_key_id
dns_aliyun_esa_access_key_secret = your_access_key_secret

# 可选；省略后自动查找 ESA 站点
# dns_aliyun_esa_site_id = your_site_id
```

早期版本使用过 `dns_aliyun_esa_access_id` 和 `dns_aliyun_esa_access_secret`，插件仍兼容这两个旧字段。

### 2. 获取阿里云 AccessKey

1. 登录阿里云控制台。
2. 进入“访问控制”并创建或选择专用 RAM 用户。
3. 创建 AccessKey 并保存 ID 和 Secret。
4. 为 RAM 用户授予 `esa:ListSites`、`esa:GetSite`、`esa:ListRecords`、
   `esa:CreateRecord` 和 `esa:DeleteRecord`。建议按这五项操作配置自定义策略，
   不要长期使用 `AliyunESAFullAccess`。

## 使用方法

首次测试建议增加 `--test-cert`，确认成功后再申请生产证书：

```bash
uv run --locked --no-dev certbot certonly \
  --test-cert \
  --authenticator dns-aliyun-esa \
  --dns-aliyun-esa-credentials ~/.certbot/aliyun-esa-credentials.ini \
  --dns-aliyun-esa-propagation-seconds 60 \
  -d example.com \
  -d '*.example.com'
```

### 参数说明

- `--dns-aliyun-esa-credentials`：凭证文件路径，必需。
- `--dns-aliyun-esa-site-id`：ESA 站点 ID，可选；未提供时自动查找，命令行参数优先于凭证文件。
- `--dns-aliyun-esa-ttl`：临时 TXT 记录 TTL，可选，默认 `600`；可设置为 `1` 或 `30`–`86400`。
- `--dns-aliyun-esa-propagation-seconds`：DNS 传播等待时间，可选，默认 `30` 秒。

Certbot 会在首次签发后保存插件参数，之后可以直接检查续期：

```bash
uv run --locked --no-dev certbot renew --dry-run
```

## 自部署

下面是一种简单的 Linux 部署方式：把仓库和虚拟环境放在 `/opt/certbot-dns-aliyun-esa`，
凭证放在 `/etc/letsencrypt`。先安装 [uv](https://docs.astral.sh/uv/getting-started/installation/)：

```bash
sudo git clone https://github.com/kyangconn/certbot-dns-aliyun-esa.git \
  /opt/certbot-dns-aliyun-esa
cd /opt/certbot-dns-aliyun-esa
sudo uv sync --locked --no-dev
sudo install -d -m 700 /etc/letsencrypt
sudo install -m 600 credentials.ini.example /etc/letsencrypt/aliyun-esa.ini
sudo editor /etc/letsencrypt/aliyun-esa.ini
sudo .venv/bin/certbot plugins
```

如果 `sudo` 找不到 `uv`，请把上面的 `uv` 换成 `command -v uv` 输出的绝对路径。

先用 Let's Encrypt 测试环境完成一次签发：

```bash
sudo .venv/bin/certbot certonly \
  --test-cert \
  --authenticator dns-aliyun-esa \
  --dns-aliyun-esa-credentials /etc/letsencrypt/aliyun-esa.ini \
  --dns-aliyun-esa-propagation-seconds 60 \
  -d example.com \
  -d '*.example.com'
```

成功后去掉 `--test-cert` 申请生产证书，再验证自动续期：

```bash
sudo .venv/bin/certbot renew --dry-run
```

仓库提供了每天运行两次的 systemd 定时器，确认 dry-run 成功后安装：

```bash
sudo install -m 644 deploy/systemd/certbot-aliyun-esa-renew.service \
  /etc/systemd/system/certbot-aliyun-esa-renew.service
sudo install -m 644 deploy/systemd/certbot-aliyun-esa-renew.timer \
  /etc/systemd/system/certbot-aliyun-esa-renew.timer
sudo systemctl daemon-reload
sudo systemctl enable --now certbot-aliyun-esa-renew.timer
systemctl list-timers certbot-aliyun-esa-renew.timer
```

更新时重新同步锁定依赖，并再次测试续期：

```bash
cd /opt/certbot-dns-aliyun-esa
sudo git pull --ff-only
sudo uv sync --locked --no-dev
sudo .venv/bin/certbot renew --dry-run
```

## 工作原理

1. Certbot 调用插件开始 DNS-01 验证。
2. 插件根据域名查找 ESA 站点（先试完整域名，再逐级尝试上级域名），或使用手动指定的站点 ID。
3. 插件通过阿里云 ESA API 添加 TXT 记录；如果相同记录已存在则直接复用，不会重复创建。
4. Certbot 等待 DNS 传播并请求 Let's Encrypt 验证。
5. 插件清理本次创建的 TXT 记录；本就不属于本次验证的记录会被保留。
6. Certbot 颁发证书。

## 故障排除

- **权限不足**：确认 AccessKey 属于正确的阿里云账号，并且 RAM 策略包含前面列出的 ESA 操作。
- **找不到站点**：确认域名已在 ESA 中以 NS 方式接入，或通过 `--dns-aliyun-esa-site-id` 手动指定。
- **DNS 验证超时**：增大 `--dns-aliyun-esa-propagation-seconds`，并用公共 DNS 解析器检查
  `_acme-challenge` TXT 记录是否已生效。
- **查看日志**：`uv run --locked --no-dev certbot certonly ... -vv`，或
  `tail -f /var/log/letsencrypt/letsencrypt.log`。

## 开发

```text
certbot-dns-aliyun-esa/
├── certbot_dns_aliyun_esa/  # Certbot 插件和 ESA API 客户端
├── tests/                   # 单元测试
├── deploy/systemd/          # systemd 自动续期示例
├── pyproject.toml           # 项目和工具配置
└── uv.lock                  # 锁定依赖
```

本地检查：

```bash
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest -q
uv run --locked pip-audit --local
uv build --no-sources
uv run --locked twine check dist/*
```

单元测试使用模拟 ESA 客户端，不会读取真实 AccessKey 或修改线上 DNS。
GitHub Actions 会在 Python 3.10–3.14 上运行测试，并检查构建产物和依赖漏洞。

## 支持

- [阿里云 ESA API 概览](https://help.aliyun.com/zh/edge-security-acceleration/esa/api-reference-1-1/)
- [Certbot 文档](https://eff-certbot.readthedocs.io/en/stable/)
- [问题反馈](https://github.com/kyangconn/certbot-dns-aliyun-esa/issues)

## 许可证

[MIT](LICENSE) © 2026 Kangyang Ji
