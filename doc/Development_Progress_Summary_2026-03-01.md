# FloodScout 开发进展总结（2026-03-01）

## 1. 本次开发目标
围绕《Weibo_Flood_Crawling_Framework_Development_Plan.md》落地首版可运行系统，重点完成：
- 微博历史洪涝信息批量采集框架
- 数据清洗、抽取、聚合的基础流水线
- 真实微博 Cookie 接入与在线抓取能力
- 关键词评估、人工复核抽样、事件查询服务

## 2. 已完成任务

### 2.1 工程基础与可运行骨架
- 完成 Python 工程结构、CLI 入口、配置管理、测试框架。
- 新增 `pyproject.toml`、`README.md`、`src/`、`tests/` 等核心目录与文件。

### 2.2 批量历史采集任务系统
- 实现“城市 + 关键词 + 时间分片（周/月）”任务生成。
- 实现 SQLite 任务状态管理（`pending/running/done/failed`）。
- 支持断点续跑和失败重试（任务幂等去重）。

### 2.3 数据处理流水线（MVP）
- 已实现链路：
  - 文本清洗
  - 去重
  - 相关性分类
  - 结构化事实抽取
  - 事件聚合
- 已实现 JSONL 结果输出（posts/facts/events）。

### 2.4 真实微博爬虫适配（重点）
- 已实现 `RealWeiboCrawler`：
  - 对接 `m.weibo.cn` 搜索接口
  - 请求重试与退避
  - 时间字段解析增强（刚刚/分钟前/昨天/中文月日等）
  - 媒体 URL 提取
- CLI 已改为真实抓取优先（`run-batch` 默认 `weibo`）。
- 新增 `check-weibo-cookie` 命令用于在线验证登录态。
- 新增 `crawl-history` 一键命令（建任务 + 执行抓取）。

### 2.5 质量评估与服务能力
- 新增关键词质量评估：输出 `keyword_metrics.csv`。
- 新增人工复核抽样：输出 `review_samples.csv`。
- 新增事件查询 API（`/health`、`/events`）。

### 2.6 运行验证结果
- 自动化测试通过：`19 passed`。
- Cookie 校验通过：
  - `Cookie check passed: login=true nick=unknown`
- 说明：`nick=unknown` 不影响登录态判定，`login=true` 即可用于抓取。

## 3. 当前可直接使用的核心命令

### 3.1 Cookie 校验
```bash
PYTHONPATH=src python -m floodscout.cli check-weibo-cookie --weibo-cookie-file data/input/weibo_cookie.txt
```

### 3.2 一键历史抓取（按城市与时间范围）
```bash
PYTHONPATH=src python -m floodscout.cli crawl-history \
  --cities 广州 \
  --start-date 2020-06-01 \
  --end-date 2020-09-30 \
  --slice-unit month \
  --weibo-cookie-file data/input/weibo_cookie.txt \
  --limit 200 \
  --max-pages 5
```

## 4. 尚需完成的任务（下一阶段）

### 4.1 地理编码与空间融合增强（高优先级）
- 尚未接入高德/百度地理编码 API Key。
- 需要实现地点解析、坐标落点、坐标系统一与空间聚合细化。

### 4.2 模型能力升级（中优先级）
- 当前相关性分类与抽取为规则/MVP 版本。
- 需替换或补充 LLM 结构化抽取（Pydantic/Instructor 强约束）与更强分类器。

### 4.3 图像验证模块（中优先级）
- 目前未完成少样本图像二分类（洪涝/非洪涝）正式接入。
- 需补标注集、训练脚本、模型评估与融合策略。

### 4.4 可观测性与运维完善（中优先级）
- 需补充更完整监控指标（任务时延、抓取成功率、数据漂移）。
- 需完善运行告警与故障恢复脚本。

### 4.5 合规与风控增强（持续任务）
- 需明确更细粒度请求频率、代理策略和异常封禁恢复机制。
- 需完善日志脱敏与审计留痕策略。

## 5. 建议的下一步实施顺序
1. 接入地理编码 API（高德/百度）并打通事件空间落点。
2. 将文本抽取升级为 LLM 结构化输出，提升事实抽取精度。
3. 接入图像二分类模型并纳入事件置信度评分。
4. 完善监控与运维策略，进入稳定批处理运行阶段。

## 6. 结论
当前项目已完成“真实微博在线抓取 + 基础处理 + 评估与查询服务”的可运行版本，具备按城市和时间范围执行历史洪涝信息采集与结构化输出的能力。下一阶段重点是空间融合与模型能力升级，以支撑科研分析和业务应用的精度与稳定性要求。
