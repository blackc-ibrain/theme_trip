# Theme Trip

> 一个真实场景约束的的LLM智能旅行助手。所有景点、酒店、餐厅、价格都来自外部 API,**不让 LLM 凭空编造**。

## 核心特性

- **真实数据驱动**:景点/酒店/餐厅从高德 API 检索,价格从静态票价表 + 规则估价,天气从高德实时 API
- **PlannerContext 协议**:把外部事实打包给 LLM,LLM 只在事实范围内编排
- **双轨防御**:prompt 软约束 + 12 项硬规则校验 + 重试循环
- **天气感知行程**:LLM 据天气调整景点(雨天改室内景点)
- **预算账本**:酒店估价、票价、规则餐饮,不在 prompt 里让 LLM 算钱
- **前端地图**:每天的景点/酒店/餐饮在地图上标点
- **规则评测**:20 条冻结样本,12 个规则指标,5 分钟跑完一次

## 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | FastAPI + Pydantic |
| LLM 集成 | OpenAI 兼容 SDK(支持 MiniMax M3 等) |
| 数据来源 | 高德地图 V3 API(POI / 天气) |
| 前端框架 | Vue 3 + TypeScript + Vite |
| UI 库 | Ant Design Vue |
| 前端地图 | 高德 Web JS API |
| 评估脚本 | Python(规则评测) |

## 项目结构

```
theme_trip/
├── backend/                    # 后端(FastAPI 应用)
│   ├── app/
│   │   ├── agents/             # Planner Agent (prompt + 重试 + feedback)
│   │   ├── api/                # FastAPI 路由
│   │   ├── models/             # Pydantic schema (TripRequest / TripPlan / POI)
│   │   ├── planner/            # 项目核心业务逻辑
│   │   │   ├── context.py      # PlannerContext 编译
│   │   │   ├── pois.py         # 景点召回
│   │   │   ├── hotels.py       # 酒店召回
│   │   │   ├── food.py         # 餐饮召回(多关键词)
│   │   │   ├── weather.py      # 天气快照
│   │   │   ├── dates.py        # 日期展开
│   │   │   ├── pricing.py      # 价格规则 + 静态票价表
│   │   │   └── validation.py  # 硬规则校验
│   │   └── services/           # 外部服务封装(高德、LLM、缓存)
│   ├── run.py                  # 启动入口
│   ├── requirements.txt
│   ├── .env.example            # 配置模板
│   └── .env                    # 真实配置(被 .gitignore 排除)
├── evaluation/                 # 规则评测(独立目录,与 backend 解耦)
│   ├── eval_set.jsonl          # 冻结核样本
│   └── eval_report.json        # 输出报告(被 .gitignore 排除)
├── frontend/                   # 前端(Vue 3)
│   ├── src/
│   │   ├── views/
│   │   │   └── Result.vue      # 行程结果 + 地图
│   │   ├── components/
│   │   │   └── DayMap.vue      # 单日地图组件
│   │   ├── services/
│   │   │   └── api.ts          # 后端 API 客户端
│   │   ├── types/
│   │   │   └── index.ts        # TypeScript 类型(镜像 Pydantic)
│   │   └── router/
│   │       └── index.ts
│   ├── package.json
│   ├── vite.config.ts
│   └── .env.example
└── .gitignore
```

## 快速开始

### 前置条件

- Python 3.11+
- Node.js 22+
- 高德地图 API Key
- OpenAI 兼容 LLM API Key(MiniMax / OpenAI / 智谱 等)

### 后端

```bash
cd backend

# 创建 conda 环境
conda create -n theme_trip python=3.11 -y
conda activate theme_trip

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env,填入 LLM_API_KEY、AMAP_API_KEY 等

# 启动服务(端口 7000)
python run.py
```

启动后访问:
- API 文档: http://localhost:7000/docs
- 健康检查: http://localhost:7000/health

### 前端

```bash
cd frontend

# 安装依赖
npm install

# 配置环境变量
cp .env.example .env.local
# 编辑 .env.local,填入 VITE_API_BASE_URL 和 AMAP_API_KEY

# 启动开发服务(端口 5173)
npm run dev
```

访问: http://localhost:5173

## 环境变量

### 后端 `backend/.env`

```bash
# LLM 配置(支持 MiniMax / OpenAI / 智谱 等 OpenAI 兼容服务)
LLM_API_KEY=your_llm_api_key_here
LLM_BASE_URL=https://api.minimaxi.com/v1
LLM_MODEL_ID=MiniMax-M3

# 高德地图 API Key
AMAP_API_KEY=your_amap_key_here
```

### 前端 `frontend/.env.local`

```bash
# 后端 API 地址
VITE_API_BASE_URL=http://localhost:7000

# 高德 Web 端 JS Key
AMAP_API_KEY=your_amap_key_here
```

## 核心架构:PlannerContext 协议

theme_trip 最重要的设计思想:**不让 LLM 凭空编造旅行事实**。

```
用户请求
  ↓
后端收集事实
  ├─ 高德 POI 搜索(景点/酒店/餐厅)
  ├─ 高德天气 API
  └─ 静态票价表
  ↓
编译 PlannerContext(把所有事实打包)
  ↓
LLM 接收 PlannerContext,在事实范围内编排
  ↓
硬规则校验
  ├─ 候选约束(景点/酒店/餐厅必须在候选中)
  ├─ 预算一致性
  └─ 多样性(同一餐厅不重复)
  ↓
失败 → 带错误反馈重试(最多 3 次)
  ↓
成功 → 返回 TripPlan
```

## 设计模式

### Planner Agent 设计模式:**Plan-and-Execute + 轻量 Reflexion**

**没有采用 ReAct、AutoGPT、LangGraph 等 agent 框架**。采用的是更朴素的模式:

| 模式 | 是否使用 | 原因 |
|---|---|---|
| **Plan-and-Execute** | ✅ **使用** | 旅行规划工具调用固定(POI / 天气 / 票价),程序决定调什么,LLM 决定怎么编排 |
| **Reflexion**(反思重试) | ✅ **使用** | validate_plan 失败时,把错误信息反馈给 LLM 让它重生成 |
| ReAct(思考-行动循环) | ❌ 不使用 | LLM 自己决定调工具,但旅行规划流程已知,不需要这种灵活性 |
| AutoGPT / LangGraph | ❌ 不使用 | 过度设计,会增加复杂度和成本 |

**为什么不用 LangChain / LlamaIndex 等框架**:

- **更可控**:LLM 调用细节自己写,出问题能直接定位
- **更轻量**:依赖少,部署简单
- **更易学**:不绑定框架,核心代码就是 plain Python
- **够用**:本项目逻辑用框架反而增加抽象成本

## 已知限制

- **中型城市 POI 候选不足**:部分城市的餐饮 POI 候选池较小
- **缓存是内存版**:重启后端会清空缓存,生产环境建议改用 Redis

## 后续优化方向

- [ ] Redis 持久化缓存
- [ ] OTA 酒店实时价格接入
- [ ] 路线时间真实计算(高德路线 API)
- [ ] DPO 后训练对齐偏好
- [ ] 景点开放时间/闭馆日增强

## 致谢

- 高德开放平台 - POI / 天气 / 地图数据
- MiniMax - LLM 服务

## 许可证

MIT
