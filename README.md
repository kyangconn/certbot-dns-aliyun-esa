# certbot-dns-aliyun-esa

通过阿里云 ESA（Edge Security Acceleration）DNS API 自动完成 Certbot
DNS-01 验证。插件会为挑战创建 TXT 记录，并在验证结束后清理对应记录。

> [!IMPORTANT]
> 本仓库目前**不发布官方 PyPI 包**。PyPI 上的同名发行物由第三方 fork
> 独立维护，不属于本仓库的发布流程。本文档只保证从
> `kyangconn/certbot-dns-aliyun-esa` 源码安装和运行。

## 功能

- 自动创建、查询和删除 ESA TXT 记录
- 可按证书域名自动发现 ESA 站点，支持 `example.co.uk` 等多级后缀
- 可通过命令行或凭证文件固定 `site_id`
- 支持同一记录名下的多个并行 DNS-01 challenge
- 使用 `uv.lock` 提供可重复安装，并通过单元测试、构建检查和依赖审计

## 要求

- Linux（生产自托管推荐）
- Python 3.10 或更高版本
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- 已接入阿里云 ESA 的域名
- 一个可调用 ESA DNS API 的阿里云 RAM AccessKey

Certbot 和插件会安装在仓库自己的 `.venv` 中，不会与系统 Python 或系统安装的
Certbot 混用。

## 从源码安装

```bash
git clone https://github.com/kyangconn/certbot-dns-aliyun-esa.git
cd certbot-dns-aliyun-esa
uv sync --locked --no-dev
uv run --locked --no-dev certbot plugins
```

最后一个命令的输出中应出现 `dns-aliyun-esa`。如需先构建 wheel：

```bash
uv build --no-sources
uv run --no-dev --with twine twine check dist/*
```

完整的 `/opt` 部署、更新和 systemd 定时续期流程见
[自托管指南](docs/self-hosting.md)。

## 阿里云权限

先用测试 RAM 用户验证策略，再按实际账号和资源范围收紧。插件只调用以下操作：

- `esa:ListSites`
- `esa:GetSite`
- `esa:ListRecords`
- `esa:CreateRecord`
- `esa:DeleteRecord`

最小功能策略示例：

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "esa:ListSites",
        "esa:GetSite",
        "esa:ListRecords",
        "esa:CreateRecord",
        "esa:DeleteRecord"
      ],
      "Resource": "*"
    }
  ]
}
```

不建议长期给自动续期使用的 AccessKey 授予 `AliyunESAFullAccess`。

## 配置凭证

创建只允许当前用户读取的文件：

```bash
mkdir -p ~/.config/certbot
install -m 600 credentials.ini.example ~/.config/certbot/aliyun-esa.ini
editor ~/.config/certbot/aliyun-esa.ini
```

填写：

```ini
dns_aliyun_esa_access_key_id = your_access_key_id
dns_aliyun_esa_access_key_secret = your_access_key_secret

# 可选；省略后按证书域名自动查找 ESA 站点
# dns_aliyun_esa_site_id = 1234567890
```

早期 README 使用过 `dns_aliyun_esa_access_id` 和
`dns_aliyun_esa_access_secret`。插件仍兼容这两个旧字段，但新部署应使用上面的规范字段。

## 首次签发

先使用 Let's Encrypt staging 环境，避免调试时触发生产限额：

```bash
uv run --locked --no-dev certbot certonly \
  --test-cert \
  --authenticator dns-aliyun-esa \
  --dns-aliyun-esa-credentials ~/.config/certbot/aliyun-esa.ini \
  --dns-aliyun-esa-propagation-seconds 60 \
  -d example.com \
  -d '*.example.com'
```

确认成功后删除 `--test-cert` 再签发生产证书。若自动发现不到站点，可显式传入：

```bash
--dns-aliyun-esa-site-id 1234567890
```

### 参数

| 参数 | 必需 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `--dns-aliyun-esa-credentials` | 是 | 无 | 凭证 INI 文件路径 |
| `--dns-aliyun-esa-site-id` | 否 | 自动发现 | 优先于凭证文件中的 `site_id` |
| `--dns-aliyun-esa-ttl` | 否 | `600` | TXT TTL；ESA 接受 `1` 或 `30`–`86400` |
| `--dns-aliyun-esa-propagation-seconds` | 否 | `30` | 创建记录后由 Certbot 统一等待的秒数 |

## 续期与更新

验证现有证书的自动续期配置：

```bash
uv run --locked --no-dev certbot renew --dry-run
```

源码部署更新时只做快进拉取，并严格使用锁文件：

```bash
git pull --ff-only
uv sync --locked --no-dev
uv run --locked --no-dev certbot renew --dry-run
```

## 故障排查

查看插件是否已加载：

```bash
uv run --locked --no-dev certbot plugins --debug
```

提高日志详细度：

```bash
uv run --locked --no-dev certbot certonly ... -vv
tail -f /var/log/letsencrypt/letsencrypt.log
```

常见问题：

- **凭证字段缺失**：以示例文件中的 `access_key_id` / `access_key_secret` 为准。
- **找不到站点**：确认域名已接入 ESA，或传入 `--dns-aliyun-esa-site-id`。
- **验证超时**：增大 `--dns-aliyun-esa-propagation-seconds`，并从公共 DNS
  解析器检查 `_acme-challenge` TXT 记录。
- **权限不足**：检查 RAM 策略是否包含上面列出的五个 ESA 操作。
- **插件未出现**：确认运行的是仓库内的 `uv run --no-dev certbot` 或
  `.venv/bin/certbot`。

## 开发与验证

```bash
uv sync --locked
uv run ruff check .
uv run pytest -q
uv run pip-audit -r requirements.txt
uv build --no-sources
uv run twine check dist/*
```

单元测试使用假 ESA 客户端，不会读取真实 AccessKey，也不会修改线上 DNS。真实账号的
staging 签发仍是发布前最高价值的端到端检查。

## 许可证

[MIT](LICENSE) © 2026 Kangyang Ji
