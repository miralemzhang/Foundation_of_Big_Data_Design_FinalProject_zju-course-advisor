# 架构与接口

前端React / Ant Design通过Axios访问Flask；四个只读工具共享Catalog，Qwen使用原生Function Calling规划；SQLite保存会话、偏好、浏览和带revision的有序清单。运行时实际加载两份Skill。没有引入多Agent或额外Agent框架。

## 工作流

1. 读取本地会话条件和显式偏好。
2. 普通交流由模型自然回答；具体课程请求使用工具。
3. 验证工具名、参数、硬条件和实体ID；程序执行查询。
4. 需要评价时检索本地证据及配置的百炼知识库，云端片段必须与本地教师评论匹配。
5. 核验课程ID、引用及数量口径，输出卡片、依据和状态。
6. 记录模型调用、工具参数与结果、检索和用量。最终核验失败时有限修复；满足适用条件才使用独立标注的事实恢复。

最多6轮模型调用、8次工具调用；任务预算120秒，在步骤边界检查，生成与检索分别设置网络超时。日志不包含隐藏思维过程。服务凭证仅从后端环境读取。

## 接口

| 方法 | 路径 | 功能 |
|---|---|---|
| GET | `/api/health`、`/api/meta` | 数据与配置存在性、类别、统计、是否为样例 |
| POST | `/api/search` | query、filters、sort、page、page_size、semantic |
| GET | `/api/courses/{id}` | 详情并记录浏览 |
| GET | `/api/courses/{id}/evidence` | query、limit、page |
| POST | `/api/compare` | offering_ids，2–3条不同记录 |
| POST | `/api/similar-courses` | offering_id、filters、limit |
| GET | `/api/hot-courses` | 按教师评分人数排序 |
| GET | `/api/college-stats`、`/api/teachers` | 统计、教师筛选与分页 |
| GET/PUT | `/api/profile` | interests、filters |
| POST | `/api/personalized-recommendations` | 硬过滤后结合兴趣、浏览做规则排序 |
| GET/PUT | `/api/shortlist` | items、revision；更新冲突409 |
| POST | `/api/user-behavior`、`/api/user-insights` | 行为及统计 |
| POST | `/api/sessions` | 创建会话 |
| GET/DELETE | `/api/sessions/{id}` | 恢复或清除会话 |
| POST | `/api/chat` | prompt、session_id；状态、课程、证据、有效条件、用量 |

错误输入400、未知记录404、更新冲突409、云端失败502或超时504；配置缺失可返回503。前端相对路径`/api`，开发代理默认5000。

数据来源改为显式 `DATA_SOURCE_DIR`；公开版仅增加数据源适配、样例标识和独立测试夹具，保留原智能体与界面主体。匿名X-User-ID不是身份认证，不应直接公网部署。
