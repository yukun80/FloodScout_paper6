# FloodScout 开发进展总结（2026-03-01）

## 1. 本次开发目标
围绕《Weibo_Flood_Crawling_Framework_Development_Plan.md》推进“爬虫能力增强 + 地理信息转化落地”，重点完成：
- Crawl4AI 接入与混合抓取架构（API 主通道 + 浏览器补充通道）
- 地点抽取 + 高德地理编码 + 坐标归一（GCJ02 -> WGS84）
- 事件聚合升级（城市 + 网格 + 30 分钟窗口 + 事件类型）
- 服务与导出能力增强（事件查询扩展 + GeoJSON 导出）

## 2. 已完成任务

### 2.1 工程基础与可运行骨架
- 完成 Python 工程结构、CLI 入口、配置管理、测试框架。
- 新增 `pyproject.toml`、`README.md`、`src/`、`tests/` 等核心目录与文件。

### 2.2 批量任务系统升级
- 任务模型扩展为多源抓取：`keyword_api`、`topic_browser`、`detail_browser`。
- SQLite 任务状态库支持字段迁移与兼容升级（新增 `source_type`、`entry_url`、`cursor`、`priority`、`last_cursor`）。
- `fetch_pending` 增加优先级排序，支持混合任务调度。
- 断点续跑与失败重试机制保持可用，并可记录游标更新。

### 2.3 爬虫能力升级（核心）
- 保留 `RealWeiboCrawler` 作为关键词历史抓取主通道（API 高吞吐）。
- 新增 `Crawl4AIWeiboCrawler` 作为浏览器抓取补充通道（用于话题/详情/回补场景）。
- 新增 `CrawlBackendRouter`，支持三种运行模式：
  - `api`：仅 API
  - `hybrid`：API 优先 + 失败/特定任务回退浏览器
  - `crawl4ai`：仅浏览器
- `RawPost` 新增来源与证据字段：`crawl_source`、`text_markdown`、`source_entry_url` 等。

### 2.4 流水线与融合升级
- 保持主链路：清洗 -> 去重 -> 分类 -> 抽取 -> 融合。
- 去重策略增强：`post_id` 去重 + 文本指纹双轨。
- 事实抽取新增地点短语字段：`location_text`。
- 新增地理编码模块：
  - 地点候选提取（路口/地铁站/小区等模式）
  - 高德地理编码
  - GCJ02 转 WGS84
  - SQLite geocode cache（避免重复请求）
- 事件聚合从“按日期”升级为“30 分钟时间桶 + 约 1km 网格”。
- `AggregatedEvent` 新增：
  - `start_time`、`end_time`
  - `grid_id`
  - `center_lng`、`center_lat`
  - `help_request_count`
  - `top_evidence_posts`

### 2.5 服务与导出增强
- `/events` 查询能力扩展，新增过滤参数：
  - `start_time`、`end_time`
  - `grid_id`
  - `bbox=min_lng,min_lat,max_lng,max_lat`
- 新增 `export-geojson` 命令，用于事件点位导出。

### 2.6 配置与依赖升级
- `AppConfig` 增加：
  - `crawl4ai` 配置段
  - `geo` 配置段
  - `source_weights` 配置段（为后续评分模型预留）
- `pyproject.toml` 增加可选依赖组：`crawl`（`crawl4ai>=0.7.4,<0.8`）。

### 2.7 运行验证结果
- 自动化测试通过：`26 passed`（`python -m pytest -q`）。
- CLI 帮助验证通过，新增命令/参数可正常显示：
  - `run-batch --crawler-mode {api,hybrid,crawl4ai}`
  - `--enable-geocode --geocode-provider gaode --gaode-key-env ...`
  - `export-geojson`

## 3. 当前可直接使用的核心命令

### 3.1 Cookie 校验
```bash
PYTHONPATH=src python -m floodscout.cli check-weibo-cookie --weibo-cookie-file data/input/weibo_cookie.txt
```

### 3.2 一键历史抓取（Hybrid 模式，按城市与时间范围）
```bash
PYTHONPATH=src python -m floodscout.cli crawl-history \
  --cities 广州 \
  --start-date 2020-06-01 \
  --end-date 2020-09-30 \
  --slice-unit month \
  --weibo-cookie-file data/input/weibo_cookie.txt \
  --crawler-mode hybrid \
  --limit 200 \
  --max-pages 5
```

### 3.3 启用地理编码运行批处理（需先设置高德 Key）
```bash
export GAODE_API_KEY="your_key_here"
PYTHONPATH=src python -m floodscout.cli run-batch \
  --crawler weibo \
  --crawler-mode hybrid \
  --weibo-cookie-file data/input/weibo_cookie.txt \
  --enable-geocode \
  --geocode-provider gaode \
  --gaode-key-env GAODE_API_KEY \
  --limit 100
```

### 3.4 导出 GeoJSON
```bash
PYTHONPATH=src python -m floodscout.cli export-geojson \
  --events-file data/output/events.jsonl \
  --output-file data/output/events.geojson
```

## 4. 尚需完成的任务（下一阶段）

### 4.1 模型能力升级（高优先级）
- 当前相关性分类与抽取为规则/MVP 版本。
- 需替换或补充 LLM 结构化抽取（Pydantic/Instructor 强约束）与更强分类器。

### 4.3 可观测性与运维完善（中优先级）
- 需补充更完整监控指标（任务时延、抓取成功率、数据漂移）。
- 需完善运行告警与故障恢复脚本。
- 需补充批次级质量报告（召回提升、地理命中率、失败原因分布）。

### 4.4 存储与编排升级（中优先级）
- 当前仍以 JSONL + SQLite 为主。
- 下一阶段需按方案推进 PostgreSQL/ES 与任务编排（Airflow/Celery）。

### 4.5 合规与风控增强（持续任务）
- 需明确更细粒度请求频率、代理策略和异常封禁恢复机制。
- 需完善日志脱敏与审计留痕策略。

## 5. 建议的下一步实施顺序
1. 引入 LLM 分类与结构化抽取替换规则链路，提升事实精度。
2. 为 Hybrid 爬虫补充更稳定的页面提取规则与回放样本集。
3. 建立批次级观测指标与故障恢复脚本，形成稳定运行规范。
4. 推进 PostgreSQL/ES 存储升级与编排系统接入。
5. 接入图像二分类并并入事件可信度评分。

## 6. 结论
当前项目已从“基础可运行 MVP”升级为“多后端混合抓取 + 地理信息转化 + 时空事件聚合”的增强版本。项目现已具备：
- API 与 Crawl4AI 协同的抓取能力
- 地点解析、地理编码与坐标归一能力
- 网格化、时间桶化事件产出与空间导出能力

下一阶段重点将转向模型智能化升级（LLM 抽取/分类）与生产级运维能力建设（监控、存储、编排、风控）。
