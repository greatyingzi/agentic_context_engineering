## Openspec 无感注入（ACE）

- 目标：用户每条提示自动注入与任务相关的 spec 片段，无需命令；缺 spec 时可零操作生成草稿，失败静默降级为仅 KPTs。
- 优先级：Spec 约束 > KPT 经验；冲突时以 spec 为准。

### 配置键（`~/.claude/settings.json`，env 覆盖）
- `enable_spec_injection`：开启/关闭注入（env: `ACE_OPENSPEC_ENABLE=0/1`）。
- `enable_spec_auto_generate`：缺文件时自动生成草稿（env: `ACE_OPENSPEC_AUTOGEN=0/1`）。
- `spec_paths`：文件或 URL 列表，默认 `openspec.yaml`（env: `ACE_OPENSPEC_PATHS=path1,path2`）。
- `default_profile`：默认使用的 profile（env: `ACE_OPENSPEC_PROFILE`）。
- `global_fallback_profile`：无默认命中时的回退。
- `spec_max_items`：每次注入的最大条目数（env: `ACE_OPENSPEC_MAX_ITEMS`）。

### Spec vs KPTs
- Spec：外部/先验规范（需求、接口、约束、NFR、验收），结构化、约束性强，更新低频。
- KPTs：对话中学习的经验/偏好，碎片化，带评分与标签，持续演化。
- 冲突：Spec > KPTs；无 Spec 时仅用 KPTs。

### 最小 openspec 结构（多 profile 示例）
```yaml
version: "1.0"
profiles:
  - name: webapp
    description: 主站前端
    goals:
      - 支持用户登录、注册、重置密码
    requirements:
      - 登录失败提示需本地化
    apis:
      - name: login
        method: POST
        path: /api/login
        constraints: 429 时展示重试等待
    non_functional:
      - P95 首屏 < 2.5s
    constraints:
      - 必须使用现有设计系统组件库
    acceptance:
      - 注册失败应记录安全日志
```

### 自动生成草稿（零操作）
- 触发：缺少 `openspec.yaml` 时首次提示；或检测到项目关键文件变更（package.json/pyproject/go.mod/openapi*/README/docs/** 等）。
- 收集：README/docs 提炼目标与 NFR；OpenAPI/Swagger 路由提取接口；package/pyproject/go.mod 识别语言栈；tests 提炼验收线索。
- 存储：默认缓存到 `~/.claude/openspec-cache/{repo}/openspec.yaml`（不进 git）；可通过设置禁用或改路径。
- 可信度：低置信条目标记 draft，不参与默认注入；诊断模式记录命中与截断。

### 注入流程（每条提示）
1. 解析设置/env，确定 spec 路径与 profile；无文件则尝试自动生成草稿并从缓存读取。
2. 载入 profiles 并选择 profile（显式 > default > global fallback）。
3. 对当前 prompt 做关键词/语义过滤，挑选 3-6 条 goals/requirements/apis/constraints/NFR，控制长度。
4. 生成 “Spec Context” 段落，与 KPT 上下文合并输出；过长截断；失败静默降级。

### 诊断
- 打开：`touch .claude/diagnostic_mode`（项目根）。
- 内容：记录 spec 路径、命中 profile、条目数、截断信息，存于 `.claude/diagnostics/*openspec*`。
