# DevMind Token Tracking & Cost Monitoring

DevMind 提供实时的 token 使用统计和成本监控功能，帮助您跟踪 LLM API 的使用情况和费用。

## 🚀 功能概述

### 实时统计
- **自动跟踪**: 每次 LLM 请求时自动统计 token 使用量
- **实时显示**: 在命令执行过程中显示 token 消耗和成本
- **会话汇总**: 整个会话期间的累计统计信息

### 成本监控
- **精确计费**: 基于模型定价自动计算成本
- **多模型支持**: 支持不同 LLM 提供商的定价结构
- **成本分析**: 按模型分解的详细成本报告

## 📊 显示内容

### 实时 Token 统计
每次 LLM 调用后会显示：
```
📊 Tokens: 1,245 (prompt: 850, completion: 395) | Cost: $0.002340 | Model: deepseek-chat
```

### 会话统计
```
╭─ Session Summary ─────────────────────────────────────────────╮
│ Duration           │ 15.3 minutes                              │
│ Total Requests     │ 12                                        │
│ Total Tokens       │ 15,420                                    │
│ Total Cost         │ $0.028560                                 │
│ Cost per 1K tokens │ $0.001852                                 │
╰───────────────────────────────────────────────────────────────╯
```

## 🔧 可用命令

### `/tokens` - 显示当前统计
显示当前会话的 token 使用情况和成本信息。

```bash
devmind> /tokens
```

### `/usage` - 详细使用报告
显示详细的使用报告，包含最近请求的历史记录。

```bash
devmind> /usage
```

### `/usage --export <文件名>` - 导出报告
将详细使用报告导出到文件。

```bash
devmind> /usage --export token_report.txt
```

### `/cost` - 成本分析
显示按模型分解的成本分析和每请求的平均费用。

```bash
devmind> /cost
```

## 📈 使用示例

### 基本使用流程

1. **启动 DevMind**:
```bash
python main.py --model deepseek-chat
```

2. **进行对话** - token 统计会自动跟踪：
```
devmind> 帮我写一个 Python 函数来计算斐波那契数列

💭 Iteration 1
💭 我需要创建一个Python函数来计算斐波那契数列...
📊 Tokens: 245 (prompt: 120, completion: 125) | Cost: $0.000343 | Model: deepseek-chat
🔧 Executing file_write(filename="fibonacci.py", content="...")
✓ file_write completed
```

3. **查看统计**:
```
devmind> /tokens
╭─ Token Usage - deepseek-chat ─────────────────────────╮
│ ┌─────────────────┬─────────────────┬───────────────────┐ │
│ │ Metric          │ Current Request │ Session Total     │ │
│ │ Prompt Tokens   │ 120             │ 1,420             │ │
│ │ Completion      │ 125             │ 1,156             │ │
│ │ Tokens          │                 │                   │ │
│ │ Total Tokens    │ 245             │ 2,576             │ │
│ │ Cost (USD)      │ $0.000343       │ $0.003604         │ │
│ └─────────────────┴─────────────────┴───────────────────┘ │
╰───────────────────────────────────────────────────────────╯
```

4. **成本分析**:
```
devmind> /cost
💰 Cost Analysis

┌─────────────┬──────────┬─────────────────┬──────────────────┐
│ Model       │ Requests │ Avg Tokens/Req  │ Est. Cost/Req    │
│ deepseek-   │ 5        │ 315             │ $0.000441        │
│ chat        │          │                 │                  │
│ gpt-4-turbo │ 2        │ 856             │ $0.008560        │
└─────────────┴──────────┴─────────────────┴──────────────────┘

Session Total: $0.019301
Average cost per 1K tokens: $0.001952
```

### 导出详细报告

```bash
devmind> /usage --export daily_usage.txt
Usage report exported to: daily_usage.txt
```

导出的报告内容示例：
```
============================================================
DevMind Token Usage Report
============================================================
Session Duration: 23.7 minutes
Total Requests: 15
Total Tokens: 18,945
  - Prompt Tokens: 12,340
  - Completion Tokens: 6,605
Total Cost: $0.026523

Models Used:
  - deepseek-chat: 12 requests
  - gpt-4-turbo: 3 requests

Recent Requests:
  1. [14:23:15] deepseek-chat - 1,245 tokens ($0.001742)
  2. [14:25:42] deepseek-chat - 856 tokens ($0.001198)
  3. [14:28:09] gpt-4-turbo - 2,145 tokens ($0.021450)
  ...
```

## ⚙️ 技术实现

### 自动跟踪
- 集成到 `StreamingReActAgent` 中
- 每次 LLM 调用时自动记录 token 使用
- 基于模型配置自动计算成本

### 数据结构
```python
@dataclass
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_input: float
    cost_output: float
    total_cost: float
    timestamp: float
    model: str
```

### 会话统计
```python
@dataclass
class SessionStats:
    total_requests: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_cost: float
    models_used: Dict[str, int]
    request_history: List[TokenUsage]
```

## 🎯 支持的模型定价

### OpenAI
- GPT-4 Turbo: $0.01/1K prompt, $0.03/1K completion
- GPT-3.5 Turbo: $0.0005/1K prompt, $0.0015/1K completion

### Anthropic Claude
- Claude 3 Opus: $0.015/1K prompt, $0.075/1K completion
- Claude 3 Sonnet: $0.003/1K prompt, $0.015/1K completion
- Claude 3 Haiku: $0.00025/1K prompt, $0.00125/1K completion

### DeepSeek
- DeepSeek Chat: $0.0014/1K prompt, $0.0028/1K completion
- DeepSeek Coder V2: $0.0014/1K prompt, $0.0028/1K completion

## 🔧 配置选项

### 环境变量
```bash
# 启用/禁用token统计 (默认启用)
export DEVMIND_TRACK_TOKENS=true

# 自动显示token统计 (默认启用)
export DEVMIND_SHOW_TOKEN_STATS=true
```

### CLI 选项
```bash
# 启动时显示token统计
python main.py --model deepseek-chat --show-token-stats

# 静默模式 (不显示token统计)
python main.py --model deepseek-chat --silent-tokens
```

## 💡 使用建议

### 成本优化
1. **选择合适的模型**: DeepSeek 模型性价比高，适合大多数任务
2. **监控使用**: 定期查看 `/cost` 了解费用分布
3. **会话管理**: 及时保存重要会话，避免重复工作

### 使用模式
1. **开发阶段**: 使用较便宜的模型进行迭代开发
2. **生产代码**: 使用更强大的模型进行最终审查
3. **批量处理**: 监控 token 使用，避免意外高费用

### 报告导出
1. **日常跟踪**: 每日导出使用报告进行费用跟踪
2. **团队共享**: 导出详细报告与团队分享使用情况
3. **成本分析**: 定期分析使用模式优化成本

这个功能让您完全掌控 LLM 使用成本，做到心中有数！🎯