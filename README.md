# ShortReport 量化交易助手

ShortReport 是一个免费数据优先的半自动美股波段交易助手。系统通过 GitHub Actions 定时运行，扫描少量股票池，输出每日简报、机会提醒和明确交易计划，但不连接券商 API、不自动下单。

## 核心功能

- 股票池扫描：使用 `SYMBOLS` 配置 5-20 个美股或 ETF，默认 `NVDA`。
- 市场过滤：用 `SPY`、`QQQ`、`SMH`、`^VIX` 判断大盘、科技、半导体和波动率背景。
- 分项评分：趋势、动量、相对强弱、成交量、期权/波动率、新闻情绪、事件风险、市场环境。
- 信号类型：突破入场、趋势回踩加仓、持有观察、减仓/风险升高、禁止交易/等待。
- 交易计划：入场区、失效位、止损、目标价、R 倍数、仓位比例、最大亏损占比、触发条件和取消条件。
- 风控预算：单笔风险、单标的最大仓位、组合总风险暴露。
- 数据降级：Yahoo Finance、RSS 或期权数据失败时优先使用缓存或降级输出，不让整次任务直接崩溃。
- 状态管理：按 symbol 和 alert kind 记录提醒冷却、信号 hash 和交易计划摘要。

## 环境变量

必需邮件配置：

- `SMTP_USER`
- `SMTP_APP_PASSWORD`
- `FROM_EMAIL`
- `TO_EMAIL`

股票池与调度：

- `SYMBOLS`: 默认 `NVDA`，示例 `NVDA,MSFT,AMD,SMH,QQQ`
- `MARKET_SYMBOLS`: 默认 `SPY,QQQ,SMH,^VIX`
- `SEND_HOUR`: 默认 `7`
- `SEND_MINUTE`: 默认 `30`
- `SEND_WINDOW_MINUTES`: 默认 `10`
- `ENABLE_ENTRY_ALERTS`: 默认 `true`
- `ALERT_COOLDOWN_HOURS`: 默认 `12`
- `ALERT_SCORE_THRESHOLD`: 默认 `65`
- `INTRADAY_INTERVAL`: 默认 `30m`
- `SUBJECT_PREFIX`: 邮件标题前缀
- `DRY_RUN`: 默认 `false`

风控：

- `ACCOUNT_EQUITY`: 可选账户规模；未设置时只输出百分比仓位
- `RISK_PER_TRADE_PCT`: 默认 `0.5`
- `MAX_POSITION_PCT`: 默认 `10`
- `PORTFOLIO_HEAT_MAX_PCT`: 默认 `3`
- `ATR_STOP_MULTIPLIER`: 默认 `2.0`
- `MIN_RR`: 默认 `1.5`

## 本地运行

```powershell
python -m pip install -r requirements.txt
$env:DRY_RUN="true"
python report.py
```

## Frontend 宣传页

静态宣传页位于 `frontend/index.html`，默认英文显示，并支持 English / 中文切换。

```powershell
Start-Process .\frontend\index.html
```

该页面用于对外展示 ShortReport 的系统能力、工作流、交易计划样例、风控参数和版本状态。页面不依赖前端构建工具，可直接部署到 GitHub Pages 或任意静态托管服务。

## 测试

```powershell
python -m compileall report.py shortreport tests
pytest
```

## 数据源

- Yahoo Finance: 行情、基本面、期权链
- NVIDIA RSS、Google News RSS: 新闻与公开标题情绪
- 本地缓存目录: `.cache/shortreport`

提示：免费数据源可能延迟、缺失或被限流。系统会降级输出，但交易决策仍应人工复核。

## 免责声明

本项目仅用于信息分析和交易辅助，不构成投资建议，不代表任何自动交易指令。
