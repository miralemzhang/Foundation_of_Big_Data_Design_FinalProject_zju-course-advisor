# 浙大小先生：通识选课评价与多功能推荐智能体

《设计大数据基础》（Foundation of Big Data Design）期末项目。面向通识课选课时的信息整理需求，将历史GPA、教师评分、评论依据和个人偏好放在同一个界面中，辅助整理、比较与管理候选课程。

**公开仓库默认使用虚构结构样例。** 样例课程、教师、评分及评论均为构造数据，供软件复现和测试；完整历史数据另随课程材料提交。真实实验结果与样例测试分别记录，不用样例数据冒充真实选课资料。

## 功能

- 自然语言查课、多轮调整条件、普通问候与知识解释。
- 按历史GPA、教师评分、两类人数、通识类别和教师学院筛选。
- 查看原始依据、教师级评论、来源文件和逻辑行号；比较2–3条课程—教师记录。
- 使用中文分词、TF-IDF与余弦相似度扩展候选，排除原课程名称。
- 保存显式偏好，结合兴趣与浏览类别做规则推荐。
- 自选清单去重、拖拽或上下调整顺序，保存后刷新恢复。
- 热门参考、学院分布、历史GPA图表和教师分页。

评价总结支持承接上一轮教师对象，自动补充该教师的本地评论。工具查询后的自然语言及附带引用信息可以直接展示；数量措辞和失效正文引用在后台处理，不因此要求用户重述。

## 架构与核心代码

React 18 / Ant Design 5 / Axios / Recharts → Flask API → Qwen单智能体 → 本地只读工具与百炼知识检索 → 条件和引用核验。

| 文件 | 职责 |
|---|---|
| `backend/app.py` | API、推荐、参数校验、错误处理、前端托管 |
| `backend/catalog.py` | 筛选、取证、相似、比较、统计的共用数据服务 |
| `backend/pipeline.py` | Qwen原生工具编排、状态保留、引用核验与有限修复 |
| `backend/tools.py`、`backend/skills/` | 四个工具契约与实际加载的查询、比较步骤 |
| `backend/providers.py` | Qwen兼容接口、百炼知识库检索、超时处理 |
| `backend/memory.py` | SQLite会话、偏好、浏览记录、有序清单与更新版本号 |
| `scripts/build_catalog.py` | 从指定输入目录构建带来源的数据目录 |
| `frontend/src/` | 页面、共享状态、交互组件和前端测试 |

详细接口见[架构文档](docs/architecture.md)，字段与关联口径见[数据说明](docs/data_dictionary.md)。

## 环境

已在Apple Silicon macOS上验证的开发环境：Python **3.11.18**、Node **22.23.4**、npm **10.9.9**。保留Flask 2.3.3、NumPy 1.24.3、scikit-learn 1.3.0；依赖分别锁在 `backend/requirements.lock.txt` 和 `frontend/package-lock.json`。

需要Python 3.11、Node 22及npm。macOS / Linux使用下列Bash命令；Windows原生环境未验收，可使用相应Linux环境自行复现。安装脚本不会安装系统Python或Node，也不会自动占用或关闭其他服务。

## 快速开始

```bash
git clone https://github.com/miralemzhang/Foundation_of_Big_Data_Design_FinalProject_zju-course-advisor.git
cd Foundation_of_Big_Data_Design_FinalProject_zju-course-advisor
cp .env.example .env
./setup-mac.sh
./scripts/run-demo.sh
```

打开 <http://127.0.0.1:5000>。Flask托管构建后的React页面；按Ctrl+C停止。

不填写任何云端凭证，也能使用结构化筛选、详情、本地证据、比较、相似接口、偏好、清单和统计。**聊天需要真实模型接口**；未配置时会返回明确错误，不自动生成假回答。

开发模式运行 `./scripts/dev.sh`，前端端口3000代理至后端5000。默认端口5000；如更改开发后端端口，需要同步修改前端代理。生产构建模式可在 `.env` 设置 `BACKEND_PORT`。

### 模型与知识库

仅在本地根目录 `.env` 填写：

```dotenv
DASHSCOPE_API_KEY=
BAILIAN_WORKSPACE_ID=
BAILIAN_KNOWLEDGE_IDS=
QWEN_MODEL=qwen-plus
```

`qwen-plus`是服务别名。当前接口适配北京地域百炼业务空间；模型自定义兼容地址可用 `QWEN_BASE_URL`。不要把服务Key写入前端或提交Git。

知识库需使用读者自己的可访问空间和知识库ID。本项目不会自动创建、上传或覆盖云端知识库。运行 `backend/venv/bin/python scripts/build_knowledge.py` 可导出当前数据；如需RAG，应自行导入相应资料并验证。只有与对应教师本地评论逐字匹配的检索片段才作为回答证据。知识库缺失或失败时，已核验的本地证据可保留，检索失败独立记录。

## 样例与完整数据切换

默认 `DATA_SOURCE_DIR=data/sample`，17条虚构记录，包含同名教师、缺失关联、同课多教师和500+人数等边界。公开离线测试始终使用独立样例夹具，不读取个人数据库。

老师取得完整数据后，将原始文件置于被忽略的 `data/private/`，在 `.env` 修改：

```dotenv
DATA_SOURCE_DIR=data/private
```

然后重新构建、核验，并重启后端：

```bash
backend/venv/bin/python scripts/build_catalog.py
backend/venv/bin/python scripts/audit_data.py
```

文件格式和完整清单规则见[data/README.md](data/README.md)。不要将原始评论、知识文本或生成数据库推送到公开仓库。

## 测试与结果

```bash
backend/venv/bin/python -m pytest backend/tests -q
CI=true ./scripts/npm.sh test -- --watchAll=false --runInBand
./scripts/npm.sh run build
backend/venv/bin/python scripts/doctor.py
```

公开版验收结果见[测试说明](docs/testing.md)。离线模型测试使用显式 `FakeCloud`，用于故障、状态和协议检查，不代表真实Qwen表现。

完整数据的固定真实任务定义在 `evaluation/cases.jsonl`。配置完整数据、模型及相应知识库后才可执行：

```bash
backend/venv/bin/python backend/eval.py --live
```

这会产生真实API请求和费用。样例目录会拒绝该固定真实评测，避免错误报告。2026-11-02完整历史数据的一次固定回归为 **10/13通过**，对应12个案例实际调用模型、29次生成调用、平均8.89秒/完整案例，1案例使用经核验的结果恢复。摘要在 `evaluation/summaries/`；这是开发回归，未证明泛化成功率，也不是本公开版重新完成的云端评测。

## 演示建议

1. 样例可查询“策略博弈入门（示例）”，或筛选GPA至少4.3的文艺审美类候选。
2. 在模型可用时继续“改成生命探索方向，GPA要求不变，再给出3门课程”，检查有效条件与实际结果。
3. 打开详情、比较与自选清单，调整顺序并刷新验证恢复。
4. 保存兴趣，查看推荐理由，再检查热门排序与统计口径。

模型可能过度追问，条件取消也有已知边界，见[已知问题](docs/known_issues.md)。数字筛选由程序执行；教师评论是个人观点，属于教师级资料；同课不同教师是多条记录，不一定是多门不同课程；500+不是精确人数。历史资料没有实时余量、课表冲突或选课资格信息。匿名浏览器ID只用于本地状态隔离，服务默认监听127.0.0.1，尚未实现公网账号认证。

开发中AI辅助的实际检查与纠错记录见[AI协作说明](docs/ai_collaboration.md)。
