# 腾讯云部署说明（CVM + Docker + Nginx + HTTPS）

## 1. 服务器准备

1. 创建 CVM（建议 Ubuntu 22.04）。
2. 安全组放行：
   - `22`：仅你的管理 IP
   - `80`、`443`：公网访问
3. 安装 Docker：

```bash
sudo apt update
sudo apt install -y docker.io
sudo systemctl enable --now docker
```

## 2. 构建并运行服务

在项目根目录执行：

```bash
docker build -t weather-agent:latest .
```

准备生产环境变量文件（例如 `/opt/weather-agent/prod.env`）：

```bash
DEEPSEEK_API_KEY=your_deepseek_key
```

运行容器（仅监听本机 8000，由 Nginx 反代）：

```bash
docker run -d \
  --name weather-agent \
  --restart unless-stopped \
  -p 127.0.0.1:8000:8000 \
  --env-file /opt/weather-agent/prod.env \
  weather-agent:latest
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

## 3. 配置 Nginx 与 HTTPS

安装：

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

新增配置 `/etc/nginx/sites-available/weather-agent.conf`：

```nginx
server {
    listen 80;
    server_name weather-api.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用并重载：

```bash
sudo ln -s /etc/nginx/sites-available/weather-agent.conf /etc/nginx/sites-enabled/weather-agent.conf
sudo nginx -t
sudo systemctl reload nginx
```

签发证书：

```bash
sudo certbot --nginx -d weather-api.example.com
```

## 4. 小程序后台配置

1. 在微信小程序后台配置 `request` 合法域名：`https://weather-api.example.com`。
2. 小程序代码中将 `miniprogram/pages/index/index.js` 的 `BASE_URL` 改为该域名。
3. 重新上传并发布小程序版本。

## 5. 上线前检查清单

- 域名已解析到 CVM 公网 IP。
- 域名已备案（大陆服务器通常需要）。
- `https://weather-api.example.com/health` 可访问。
- 小程序已授权定位权限，且可正常调用 `/v1/chat`。
- 容器日志无异常：

```bash
docker logs -f weather-agent
```
