# Mini-Avalon: 微信公众号阿瓦隆桌游后端

![Game Stage](https://img.shields.io/badge/Stage-Development-orange)
![Python](https://img.shields.io/badge/Python-3.12+-blue)
![Architecture](https://img.shields.io/badge/Architecture-DDD--Layered-green)

## 🌟 项目简介

**Mini-Avalon** 是一个专为微信公众号设计的“阿瓦隆”多人桌面游戏后端。它支持全文本指令交互，完美适配个人订阅号（无自定义菜单环境）。

本项目采用 **MySQL 作为单一事实来源**，并配合 **Redis 缓存异步优化**，确保在微信 5 秒内被动回复的严格限制下，依然能提供稳定、高性能、且具有强数据一致性的游戏体验。

---

## 🚀 快速启动

### 1. 启动基础设施 (MySQL & Redis)
推荐使用 Docker Compose 一键启动本地开发所需的数据库和缓存：
```bash
docker-compose up -d
```

### 2. 配置环境
根据不同环境设置 `APP_ENV`（默认为 `dev`）。系统会自动加载对应的 `.env.{APP_ENV}` 文件：
- **开发**: `export APP_ENV=dev` (使用本地 MySQL/Redis)
- **测试**: `export APP_ENV=test` (使用内存 SQLite，运行测试会自动切换)

### 3. 安装依赖并运行
```bash
# 安装依赖
./.venv/bin/pip install -r requirements.txt

# 启动应用
./.venv/bin/python main.py
```

---

## 🛠 技术深度

- **MySQL-First 架构**: 所有游戏状态和用户信息持久化存储在 MySQL 中。
- **Cache-Aside 策略**: 基于 Redis 的热点数据（房间、活跃游戏状态）自动缓存，提升读写响应速度。
- **并发保护**: 引入 Version 乐观锁机制，防止多人同时投票导致的数据冲突。
- **正则指令引擎**: 提供极简的指令解析，支持 `/join 1234` 或 `加入 1234` 等多种输入格式。

---

## 🎮 指令交互指南

| 指令类 | 示例 | 说明 |
| :--- | :--- | :--- |
| **房间管理** | `建房` | 创建 4 位数字唯一房间号 |
| **加入游戏** | `加入 1024` | 进入指定房间 |
| **状态查询** | `状态` | 查看当前房间人数、局次及角色阶段 |
| **游戏开始** | `/start` | 房主启动游戏（需满足 5-10 人） |
| **队长提议** | `/pick 1 3 5` | 队长提名本轮任务执行者 |
| **全员投票** | `投票 赞成` | 对当前提议进行公开投票 |
| **秘密任务** | `任务 成功` | 任务执行者决定任务结果 |
| **刺客刺杀** | `刺杀 1` | 坏人阵营反败为胜的最后一击 |

---

## 📈 开发进度与路线图

### 🟢 已完成 (Done)
- [x] 基于 Application Factory 的 Flask 后端框架。
- [x] 微信消息签名验证及 XML 协议处理。
- [x] 支持多参数的正则表达式指令解析器。
- [x] MySQL 核心模型定义（User, Room, State, History）。
- [x] 集成 Redis 缓存一致性 Repository 层。
- [x] 标准阿瓦隆 FSM 状态机框架（人数分配、阶段校验）。
- [x] 核心游戏流程实现（组队、投票、任务执行、刺杀阶段）。
- [x] **高阶角色支持**: 莫甘娜 (Morgana)、莫德雷德 (Mordred)、奥伯伦 (Oberon) 的视野逻辑与分配。
- [x] **Quest 4 特殊规则**: 7 人及以上局第 4 轮需 2 张失败。
- [x] **个人战绩中心**: 实现 `/profile` 指令，统计胜率及阵营分布。
- [x] 单元测试与集成测试（覆盖率 > 50%）。
- [x] 战绩历史统计与归档流程。
- [x] 房间清理机制（命令行指令：`flask cleanup-rooms`）。

### 🟡 进行中 (In Progress)
- [ ] 工程健壮性建设：接入 Sentry 监控与 Flask-Migrate 数据库迁移。
- [ ] 可观测性：引入 TraceID 处理微信 5s 回复限制下的日志追踪。

### 🔴 待办 (Todo)
- [ ] 异步超时处理：当玩家长时间不投票时自动随机执行。
- [ ] Kubernetes (Kustomize) 部署清单与 HPA 配置。

---

## 🧪 测试
```bash
# 运行单元测试
pytest
```
目前指令解析器测试覆盖率已达 100%。

---

## 📄 开源协议
MIT License
