# 定时清理任务配置指南

## 概述

项目支持两种定时清理过期房间的方式：
1. **K8s CronJob** - 推荐：在Kubernetes集群中运行，自动调度
2. **Linux Cron** - 传统方式：在服务器上使用cron调度

## 清理策略

清理服务根据房间状态和活跃度采用不同的清理策略：

| 房间状态 | 清理策略 | 说明 |
|---------|---------|------|
| ENDED | 7天后清理 | 已结束的游戏保留7天用于回放 |
| WAITING (无玩家) | 1小时后清理 | 无人加入的空房间快速清理 |
| WAITING (有玩家) | 24小时后清理 | 有玩家但长时间未开始游戏 |
| PLAYING (异常) | 3天后清理 | 游戏进行中但超过3天无更新（异常卡住） |
| ORPHANED | 立即清理 | 无玩家关联的孤儿房间 |

## 方式1: K8s CronJob (推荐)

### 生产环境配置

每天凌晨2点执行清理（UTC时间）：

```bash
# 应用K8s配置（包含CronJob）
kubectl apply -k k8s/overlays/prod

# 验证CronJob已创建
kubectl get cronjobs

# 查看CronJob详细信息
kubectl describe cronjob room-cleanup

# 查看历史执行记录
kubectl get jobs --sort-by=.metadata.creationTimestamp
```

### 开发/测试环境配置

每小时执行一次，方便观察清理效果：

```bash
# 应用开发环境配置（包含频繁清理的CronJob）
kubectl apply -f k8s/base/cleanup-cronjob-dev.yaml

# 查看最近一次执行日志
kubectl logs -l job-name=<job-name>
```

### CronJob 配置说明

**生产环境** (`k8s/base/cleanup-cronjob.yaml`):
- 调度时间: `0 2 * * *` (每天凌晨2点 UTC)
- 并发策略: `Forbid` (不允许并发)
- 超时时间: 1小时
- 资源限制: 500m CPU, 256Mi 内存

**开发环境** (`k8s/base/cleanup-cronjob-dev.yaml`):
- 调度时间: `0 * * * *` (每小时)
- 超时时间: 30分钟
- 资源限制: 200m CPU, 128Mi 内存

## 方式2: Linux Cron

### 配置步骤

1. **赋予脚本执行权限**
```bash
chmod +x scripts/cleanup_rooms.py
```

2. **编辑crontab**
```bash
crontab -e
```

3. **添加定时任务**

生产环境（每天凌晨2点）:
```cron
0 2 * * * cd /path/to/mini-avalon && /usr/bin/python3 scripts/cleanup_rooms.py >> /var/log/avalon-cleanup.log 2>&1
```

开发环境（每小时）:
```cron
0 * * * * cd /path/to/mini-avalon && /usr/bin/python3 scripts/cleanup_rooms.py >> /var/log/avalon-cleanup.log 2>&1
```

4. **验证定时任务**
```bash
# 查看当前用户的crontab
crontab -l

# 查看cron执行日志
tail -f /var/log/avalon-cleanup.log
```

### Cron 时间格式说明

```
* * * * *
│ │ │ │ │
│ │ │ │ └─ 星期几 (0-7, 0和7都代表星期日)
│ │ │ └─── 月份 (1-12)
│ │ └───── 日期 (1-31)
│ └─────── 小时 (0-23)
└───────── 分钟 (0-59)
```

常用示例:
- `0 2 * * *` - 每天凌晨2点
- `*/5 * * * *` - 每5分钟
- `0 */2 * * *` - 每2小时
- `0 0 * * 0` - 每周日凌晨

## 手动执行清理

### 使用Flask CLI命令

```bash
# 生产环境执行清理
flask cleanup-rooms

# 开发环境
flask --app main.py cleanup-rooms
```

### 使用清理脚本

```bash
# 执行清理
python scripts/cleanup_rooms.py

# 只查看统计
python scripts/cleanup_rooms.py --stats

# 模拟运行（不删除）
python scripts/cleanup_rooms.py --dry-run
```

### 使用Docker执行

```bash
# 进入容器
docker exec -it <container_id> bash

# 执行清理
python scripts/cleanup_rooms.py
```

### 使用K8s执行

```bash
# 创建临时Job执行清理
kubectl create job manual-cleanup --from=cronjob/room-cleanup

# 查看执行日志
kubectl logs -l job-name=manual-cleanup

# 清理临时Job
kubectl delete job manual-cleanup
```

## 监控和日志

### 查看清理日志

**应用日志**:
```bash
# 查看最近的清理日志
kubectl logs -l app=app-server --tail=100 | grep cleanup

# 查看所有清理相关日志
kubectl logs -l app=app-server --tail=500 | grep -i "cleanup\|cleaned"
```

**CronJob日志**:
```bash
# 查看最近一次清理Job的日志
kubectl logs -l job-name=<job-name>

# 查看所有清理Job的历史
kubectl get jobs --sort-by=.metadata.creationTimestamp
```

**Linux Cron日志**:
```bash
# 查看cron日志文件
tail -f /var/log/avalon-cleanup.log

# 查看系统cron日志
tail -f /var/log/syslog | grep CRON
```

### 监控指标

建议监控以下指标：
- 清理执行次数
- 清理房间数量（按状态分类）
- 执行时长
- 失败次数

### 告警配置

建议配置以下告警：
- 清理任务连续失败3次
- 单次清理房间数量异常（>1000）
- 清理执行时间超过阈值（>30分钟）

## 故障排查

### CronJob未执行

1. 检查CronJob状态:
```bash
kubectl describe cronjob room-cleanup
```

2. 检查调度时间是否正确（注意时区）

3. 检查Job状态:
```bash
kubectl get jobs
```

4. 查看Pod日志:
```bash
kubectl logs <pod-name>
```

### 清理失败

1. 检查数据库连接:
```bash
kubectl logs <pod-name> | grep "database\|connection"
```

2. 检查Redis连接:
```bash
kubectl logs <pod-name> | grep "redis"
```

3. 检查权限问题:
```bash
kubectl logs <pod-name> | grep "permission\|access"
```

### 清理数量异常

1. 查看房间统计:
```bash
flask cleanup-rooms --stats
```

2. 检查清理策略配置:
```python
# src/services/cleanup_service.py
CLEANUP_POLICIES = {...}
```

3. 检查房间状态分布

## 清理策略调整

如需调整清理策略，编辑 `src/services/cleanup_service.py`:

```python
CLEANUP_POLICIES = {
    'ENDED': 168,           # 已结束房间：7天
    'WAITING_EMPTY': 1,     # 等待中无玩家：1小时
    'WAITING_STALLED': 24,  # 等待中有玩家：24小时
    'PLAYING_STALLED': 72,  # 游戏中异常：3天
    'ORPHANED': 0,          # 孤儿房间：立即
}
```

修改后需要重新部署:
```bash
kubectl rollout restart deployment app-server
```

## 最佳实践

1. **测试环境先验证**: 在开发环境测试清理逻辑，确保不会误删活跃房间
2. **备份数据**: 执行清理前确保数据库有备份
3. **监控执行**: 配置监控和告警，及时发现清理异常
4. **日志保留**: 保留清理日志至少30天，便于问题排查
5. **定期检查**: 每周检查清理效果，调整策略参数
6. **分阶段清理**: 初期可以使用较长的保留时间，逐步缩短

## 相关文件

- 清理服务: `src/services/cleanup_service.py`
- 清理脚本: `scripts/cleanup_rooms.py`
- K8s配置: `k8s/base/cleanup-cronjob.yaml`
- Flask命令: `main.py` (cleanup-rooms命令)
