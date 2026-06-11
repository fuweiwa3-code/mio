# Mio 云服务器 PostgreSQL 部署文档

## 1. 部署结果

Mio 的 PostgreSQL 已部署到腾讯云 Ubuntu 24.04 服务器。

当前状态：

- PostgreSQL：`16.14`
- Cluster：`16/main`
- 数据库：`mio`
- 应用角色：`mio_app`
- 服务管理：systemd
- 开机启动：已启用
- 监听地址：仅 `127.0.0.1:5432`
- 密码加密：`scram-sha-256`
- Alembic revision：`20260609_0001`
- 每日备份：已启用
- 备份保留：7 天

最近一次无损重部署验证：`2026-06-10 22:24 CST`。

- 重启前已生成即时备份 `mio-20260610-222409.dump`。
- PostgreSQL 重启后状态为 `active`，Cluster `16/main` 为 `online`。
- `mio_app` 使用应用连接串连接成功。
- Alembic revision 仍为 `20260609_0001`。
- 现有数据表和数据目录未重建、未清空。

数据库没有直接暴露给公网或 Tailscale 网络。后端部署在同一服务器时使用 localhost；本地调试通过 SSH 隧道访问。

截至 `2026-06-10 22:30 CST`，本机 `backend/.env` 已切换到隧道端口
`127.0.0.1:15432`，FastAPI 已重启并通过 `/api/health/ready` 验证。

## 2. 为什么采用系统 PostgreSQL

服务器在部署前没有 Docker，但 Ubuntu 24.04 官方源直接提供 PostgreSQL 16。

本次使用系统包而不是 Docker，原因是：

- 少安装一层容器运行时。
- systemd 可以直接管理启动、日志和恢复。
- 数据目录和配置位置符合 Ubuntu 标准。
- 当前只有一个 Mio 应用数据库，不需要容器隔离。

本地开发仍然可以使用项目根目录的 `docker-compose.yml`。本地和云端运行方式不同，但数据库 Schema 都由同一套 Alembic migration 管理。

## 3. 连接方式

### 3.1 SSH

本机 `~/.ssh/config` 已配置：

```sshconfig
Host mio-cloud
  HostName 100.93.97.96
  User ubuntu
  IdentityFile ~/.ssh/finalshell_tx_111.pem
  IdentitiesOnly yes
```

连接：

```bash
ssh mio-cloud
```

这里使用 Tailscale 私网地址，避免公网 SSH 当前存在的握手关闭问题。

### 3.2 云端后端连接

凭据保存在服务器：

```text
/etc/mio/postgresql.env
```

权限：

```text
640 root:ubuntu
```

目录权限：

```text
750 root:ubuntu
```

后续 FastAPI 以 `ubuntu` 用户运行时，可以通过 systemd：

```ini
EnvironmentFile=/etc/mio/postgresql.env
```

读取 `MIO_DATABASE_URL`。不要把该文件内容写入仓库、聊天记录或公开日志。

### 3.3 本机通过 SSH 隧道连接

终端一：

```bash
ssh -N -L 127.0.0.1:15432:127.0.0.1:5432 mio-cloud
```

终端二可以临时取得云端配置并把端口改为隧道端口：

```bash
REMOTE_URL=$(
  ssh mio-cloud \
    "sudo sed -n 's/^MIO_DATABASE_URL=//p' /etc/mio/postgresql.env"
)
export MIO_DATABASE_URL="${REMOTE_URL/127.0.0.1:5432/127.0.0.1:15432}"
```

该变量只存在当前 shell。不要执行 `echo "$MIO_DATABASE_URL"`，因为 URL 中包含密码。

## 4. 服务器文件

| 路径 | 用途 |
|---|---|
| `/etc/postgresql/16/main/postgresql.conf` | PostgreSQL 主配置 |
| `/etc/postgresql/16/main/pg_hba.conf` | 客户端认证规则 |
| `/var/lib/postgresql/16/main` | 数据目录 |
| `/etc/mio/postgresql.env` | Mio 数据库连接配置 |
| `/usr/local/sbin/mio-postgres-backup` | 备份脚本 |
| `/var/backups/mio-postgresql` | 备份目录 |
| `/etc/systemd/system/mio-postgres-backup.service` | 备份任务 |
| `/etc/systemd/system/mio-postgres-backup.timer` | 每日调度 |

## 5. 数据库角色与权限

`mio_app` 是普通登录角色：

```text
superuser: false
createdb: false
createrole: false
login: true
```

数据库 `mio` 的 owner 是 `mio_app`。应用可以在该数据库执行 Alembic migration，但不能创建其他数据库、角色或获得系统超级权限。

验证：

```bash
ssh mio-cloud \
  "sudo -u postgres psql -Atqc \
  \"select rolname, rolsuper, rolcreatedb, rolcreaterole, rolcanlogin
    from pg_roles where rolname='mio_app';\""
```

预期：

```text
mio_app|f|f|f|t
```

## 6. 网络安全

PostgreSQL 配置：

```text
listen_addresses = 'localhost'
password_encryption = 'scram-sha-256'
```

验证：

```bash
ssh mio-cloud \
  "sudo ss -ltnp | grep :5432"
```

预期只出现：

```text
127.0.0.1:5432
```

不要修改为：

```text
listen_addresses = '*'
```

也不要在腾讯云安全组开放公网 `5432`。远程管理统一使用 SSH 隧道。

## 7. Migration

本次已在真实云端 PostgreSQL 上执行：

```bash
cd backend
uv run alembic upgrade head
```

当前 revision：

```text
20260609_0001 (head)
```

当前表：

```text
agent_traces
alembic_version
companion_profiles
conversations
messages
users
```

以后每次部署后端时：

1. 先备份数据库。
2. 上传或拉取新代码。
3. 执行 `uv run alembic upgrade head`。
4. 确认 `uv run alembic current`。
5. 再重启 FastAPI。

## 8. 服务管理

查看状态：

```bash
ssh mio-cloud "systemctl status postgresql --no-pager"
```

重启：

```bash
ssh mio-cloud "sudo systemctl restart postgresql"
```

查看最近日志：

```bash
ssh mio-cloud \
  "sudo journalctl -u postgresql -n 100 --no-pager"
```

检查数据库：

```bash
ssh mio-cloud \
  "sudo -u postgres psql -d mio -c '\\dt'"
```

## 9. 自动备份

systemd timer：

```text
mio-postgres-backup.timer
```

计划：

```text
每天 03:30
随机延迟最多 10 分钟
```

`Persistent=true` 表示服务器在计划时间关机时，恢复后会补执行任务。

备份格式：

```text
/var/backups/mio-postgresql/mio-YYYYMMDD-HHMMSS.dump
```

使用 PostgreSQL custom format，便于选择性恢复。文件权限由 `umask 077` 限制。

查看 timer：

```bash
ssh mio-cloud \
  "systemctl list-timers mio-postgres-backup.timer --no-pager"
```

手动备份：

```bash
ssh mio-cloud \
  "sudo systemctl start mio-postgres-backup.service"
```

查看备份：

```bash
ssh mio-cloud \
  "sudo ls -lh /var/backups/mio-postgresql"
```

查看备份清单而不恢复：

```bash
ssh mio-cloud \
  "sudo -u postgres pg_restore --list \
  /var/backups/mio-postgresql/<backup>.dump | head"
```

## 10. 恢复流程

恢复是破坏性操作，不要直接覆盖生产库。先恢复到临时数据库检查：

```bash
ssh mio-cloud

sudo -u postgres createdb mio_restore_check
sudo -u postgres pg_restore \
  --dbname=mio_restore_check \
  /var/backups/mio-postgresql/<backup>.dump

sudo -u postgres psql \
  --dbname=mio_restore_check \
  -c '\dt'
```

检查完成后：

```bash
sudo -u postgres dropdb mio_restore_check
```

正式恢复前必须：

1. 停止 FastAPI。
2. 再做一次当前数据库备份。
3. 明确选择目标备份。
4. 在临时数据库验证。
5. 才执行生产恢复。

## 11. 实际验证结果

本次已经验证：

- PostgreSQL systemd 服务 enabled/active。
- 只监听 `127.0.0.1:5432`。
- `scram-sha-256` 密码认证成功。
- `mio_app` 不是超级用户。
- 数据库 owner 为 `mio_app`。
- Alembic migration 在 PostgreSQL 16.14 上成功。
- FastAPI 通过 SSH 隧道连接真实云数据库。
- Ready API 返回 database reachable。
- 默认「澪」种子数据创建成功。
- 创建 Conversation 成功。
- SSE 完整产生 started、delta、completed。
- 用户与助手消息写入云数据库。
- 自动备份成功。
- `pg_restore --list` 可以读取备份清单。

## 12. 已知限制

- 当前只部署了 PostgreSQL，FastAPI 尚未常驻部署到云服务器。
- 数据库备份仍在同一块云盘；后续应增加对象存储或异地备份。
- 当前没有监控磁盘空间、连接数和慢查询。
- 尚未安装 pgvector；进入 RAG 阶段时再安装并通过 Alembic 创建扩展。
- 腾讯云安全组仍应人工确认没有放行 5432，即使 PostgreSQL 自身只监听 localhost。
