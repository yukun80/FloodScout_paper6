# FloodScout

FloodScout 是一个面向“历史城市洪水内涝微博信息”的批量采集与结构化处理框架。

## 已实现能力（阶段 2）
- 关键词组合生成（城市词 + 灾情词 + 场景词）
- 历史时间窗分片（按周/按月）
- 批处理任务规划（城市-关键词-时间片）
- 断点续跑（SQLite 状态存储）
- 真实微博爬虫适配：`weibo`（在线接口 + Cookie 校验 + 请求重试）
- 基础流水线：清洗 -> 去重 -> 相关性分类 -> 结构化抽取 -> 事件聚合
- 关键词质量评估（CSV）
- 人工复核抽样导出（CSV）
- 事件查询 HTTP API（`/health`、`/events`）
- CLI 命令行执行

## 快速开始

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

准备 Cookie（单行）：

```bash
cp data/input/weibo_cookie.example.txt data/input/weibo_cookie.txt
# 编辑 data/input/weibo_cookie.txt，填入真实 cookie
```

检查 Cookie 是否可用：

```bash
floodscout check-weibo-cookie --weibo-cookie-file data/input/weibo_cookie.txt
```

一键按城市+时间在线抓取（推荐）：

```bash
floodscout crawl-history \
  --cities-file data/input/cities.txt \
  --flood-terms-file data/input/flood_terms.txt \
  --scene-terms-file data/input/scene_terms.txt \
  --start-date 2020-01-01 \
  --end-date 2020-12-31 \
  --slice-unit month \
  --weibo-cookie-file data/input/weibo_cookie.txt \
  --limit 100 \
  --max-pages 3
```

分步执行（可选）：

```bash
floodscout build-tasks \
  --cities-file data/input/cities.txt \
  --flood-terms-file data/input/flood_terms.txt \
  --scene-terms-file data/input/scene_terms.txt \
  --start-date 2020-01-01 \
  --end-date 2020-12-31 \
  --slice-unit month

floodscout run-batch \
  --crawler weibo \
  --weibo-cookie-file data/input/weibo_cookie.txt \
  --limit 100
```

关键词评估：

```bash
floodscout evaluate-keywords \
  --posts-file data/output/posts.jsonl \
  --facts-file data/output/facts.jsonl \
  --output-file data/output/keyword_metrics.csv
```

人工复核抽样：

```bash
floodscout sample-review \
  --posts-file data/output/posts.jsonl \
  --facts-file data/output/facts.jsonl \
  --output-file data/output/review_samples.csv \
  --sample-size 200
```

启动事件查询 API：

```bash
floodscout serve-events --host 127.0.0.1 --port 8000
```

运行测试：

```bash
pytest
```

## 目录说明
- `src/floodscout/`：核心代码
- `data/input/`：城市与关键词输入模板
- `data/state/`：任务状态和断点信息
- `data/output/`：结构化输出结果
- `doc/`：方案与白皮书文档

## 注意
- 真实平台采集需严格遵守平台协议与法律法规。
- `data/input/weibo_cookie.txt` 建议本地保管且不要提交到仓库。
- 也可用环境变量传 cookie：`export WEIBO_COOKIE='SUB=...; SUBP=...;'`。
