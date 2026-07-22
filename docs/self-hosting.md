# 源码自托管指南

本指南把仓库固定部署到 `/opt/certbot-dns-aliyun-esa`，使用项目自己的虚拟环境，
并由 systemd 每天触发两次续期。命令以 Debian/Ubuntu 风格的 Linux 为例。

## 1. 准备主机

安装 Git、受支持的 Python，以及
[uv](https://docs.astral.sh/uv/getting-started/installation/)。确认 root 执行 systemd
任务时也能找到 `uv`：

```bash
git --version
uv --version
python3 --version
```

Certbot 需要写入 `/etc/letsencrypt`，以下示例由 root 管理部署目录和续期任务。

## 2. 安装固定源码

```bash
sudo git clone https://github.com/kyangconn/certbot-dns-aliyun-esa.git \
  /opt/certbot-dns-aliyun-esa
cd /opt/certbot-dns-aliyun-esa
sudo uv sync --locked --no-dev
sudo .venv/bin/certbot plugins
```

如果 `sudo` 的安全路径里没有 `uv`，请把上面的 `uv` 换成 `command -v uv` 返回的绝对路径。
不要用系统 `pip` 把插件装进另一套 Certbot 环境。

## 3. 保存凭证

```bash
sudo install -m 600 credentials.ini.example \
  /etc/letsencrypt/aliyun-esa.ini
sudo editor /etc/letsencrypt/aliyun-esa.ini
sudo stat -c '%a %U:%G %n' /etc/letsencrypt/aliyun-esa.ini
```

期望权限为 `600 root:root`。AccessKey 应属于专用 RAM 用户，并只授予 README 中列出的
ESA 站点查询和 DNS 记录操作权限。

## 4. staging 演练和生产签发

```bash
cd /opt/certbot-dns-aliyun-esa
sudo .venv/bin/certbot certonly \
  --test-cert \
  --authenticator dns-aliyun-esa \
  --dns-aliyun-esa-credentials /etc/letsencrypt/aliyun-esa.ini \
  --dns-aliyun-esa-propagation-seconds 60 \
  -d example.com \
  -d '*.example.com'
```

成功后删除 `--test-cert` 再运行一次。需要在续期成功后重载服务时，可在生产签发命令加上
部署钩子，例如：

```bash
--deploy-hook 'systemctl reload nginx'
```

Certbot 会把认证器参数和部署钩子保存到 `/etc/letsencrypt/renewal/` 的证书续期配置中。

## 5. 验证自动续期

```bash
cd /opt/certbot-dns-aliyun-esa
sudo .venv/bin/certbot renew --dry-run
```

只有 dry-run 成功后再启用定时器。

## 6. 安装 systemd 定时器

仓库提供的 unit 假设部署路径与本指南一致：

```bash
cd /opt/certbot-dns-aliyun-esa
sudo install -m 644 deploy/systemd/certbot-aliyun-esa-renew.service \
  /etc/systemd/system/certbot-aliyun-esa-renew.service
sudo install -m 644 deploy/systemd/certbot-aliyun-esa-renew.timer \
  /etc/systemd/system/certbot-aliyun-esa-renew.timer
sudo systemctl daemon-reload
sudo systemctl enable --now certbot-aliyun-esa-renew.timer
```

检查下次触发时间并手动测试一次：

```bash
systemctl list-timers certbot-aliyun-esa-renew.timer
sudo systemctl start certbot-aliyun-esa-renew.service
sudo journalctl -u certbot-aliyun-esa-renew.service --since today
```

## 7. 安全更新

先备份 `/etc/letsencrypt`，然后只接受可以快进的默认分支更新：

```bash
cd /opt/certbot-dns-aliyun-esa
sudo git fetch origin
sudo git pull --ff-only
sudo uv sync --locked --no-dev
sudo .venv/bin/certbot plugins
sudo .venv/bin/certbot renew --dry-run
```

如需最严格的可重复部署，可记录当前提交并在多台主机上检出同一提交：

```bash
git rev-parse HEAD
```

不要删除仍被现有证书续期配置引用的旧凭证文件或部署路径。

## 8. 回退

更新前记录提交 ID。出现问题时，检出已验证的旧提交并重新同步锁文件：

```bash
cd /opt/certbot-dns-aliyun-esa
sudo git switch --detach PREVIOUS_COMMIT_ID
sudo uv sync --locked --no-dev
sudo .venv/bin/certbot renew --dry-run
```

确认上游修复后，再切回 `main` 并执行安全更新流程。
