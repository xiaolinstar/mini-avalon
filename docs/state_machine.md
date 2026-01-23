# 阿瓦隆 - 游戏状态机 (FSM)

本项目采用严格的有限状态机 (Finite State Machine) 管理游戏流程。阿瓦隆的游戏逻辑较为复杂，涉及嵌套的投票循环、多角色视角判定以及多分支的结果结算。

## 状态定义 (States)

| 状态枚举         | 描述       | 允许动作                       |
| :--------------- | :--------- | :----------------------------- |
| `WAITING`        | 等待开始   | 加入, 退出, 设置昵称, 开始游戏 |
| `TEAM_SELECTION` | 队长组队   | 队长提名 (`/pick`)             |
| `TEAM_VOTE`      | 对队伍投票 | 全员投票 (`/vote`)             |
| `QUEST_PERFORM`  | 执行任务   | 队内成员执行 (`/quest`)        |
| `ASSASSINATION`  | 刺杀时刻   | 刺客刺杀 (`/shoot`)            |
| `GAME_OVER`      | 游戏结束   | 查看战绩, 重开                 |

## 事件与流转 (Transitions)

### 1. 游戏初始化

- `WAITING` --(start game)--> `TEAM_SELECTION` (分配角色, 随机队长)

### 2. 回合循环 (Round Loop)

每个任务 (Quest 1-5) 包含多个组队尝试。

- **组队分支**:
  - `TEAM_SELECTION` --(leader picks team)--> `TEAM_VOTE`
- **组队投票分支**:
  - `TEAM_VOTE` --(majority yes)--> `QUEST_PERFORM` (投票通过)
  - `TEAM_VOTE` --(majority no / tie)--> check `vote_track`
    - if `vote_track < 5`: --> `TEAM_SELECTION` (换下一位队长, track+1)
    - if `vote_track == 5`: --> `GAME_OVER` (坏人直接胜利)

- **任务执行分支**:
  - `QUEST_PERFORM` --(all performed)--> Calculate Result
    - Result recorded.
    - Check Game End Condition:
      - if `fails >= 3`: --> `GAME_OVER` (坏人胜)
      - if `successes >= 3`: --> `ASSASSINATION` (好人暂胜, 进刺杀)
      - else: --> `TEAM_SELECTION` (进入下一轮 Quest, track重置0)

### 3. 终局分支

- `ASSASSINATION` --(assassin shoots merlin)--> `GAME_OVER` (坏人反败为胜)
- `ASSASSINATION` --(assassin misses)--> `GAME_OVER` (好人胜利)

## 关键数据流

- **Vote Track**: 在 `TEAM_VOTE` 失败时 +1，在 `TEAM_VOTE` 成功时重置为 0。
- **Quest History**: 记录每一轮的红/蓝结果。

## 实现位置

- 核心逻辑: `src/fsm/avalon_fsm.py`
- 状态存储: Redis Hash `room:{id}:state`
