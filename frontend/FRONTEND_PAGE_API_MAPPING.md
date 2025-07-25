# AutoReportAI 前端页面与接口映射文档

> 本文档详细梳理了 AutoReportAI 前端各页面（含子页面）结构、功能说明、所需后端接口、接口用途、请求方式、主要参数、返回数据要点。适用于前后端开发、联调、接口对接参考。

---

## 目录

1. [页面总览](#页面总览)
2. [各页面详细说明](#各页面详细说明)
   - 仪表盘（Dashboard）
   - 数据源管理
   - 数据源宽表预览
   - 任务管理
   - 任务详情
   - 创建任务
   - 历史记录
   - 用户认证与设置
3. [接口汇总表](#接口汇总表)

---

## 页面总览

| 页面路径                                   | 主要功能         |
|-------------------------------------------|----------------|
| /[locale]/dashboard                      | 仪表盘         |
| /[locale]/data-sources                   | 数据源管理     |
| /[locale]/data-sources/[id]/wide-table   | 宽表预览       |
| /[locale]/tasks                          | 任务管理       |
| /[locale]/tasks/[id]                     | 任务详情       |
| /[locale]/tasks/create                   | 创建任务       |
| /[locale]/history                        | 报告历史       |
| /[locale]/login                          | 登录           |
| /[locale]/register                       | 注册           |
| /[locale]/forgot-password                | 忘记密码       |
| /[locale]/reset-password                 | 重置密码       |
| /[locale]/verify-email                   | 邮箱验证       |

---

## 各页面详细说明

### 1. 仪表盘（Dashboard）
- **路径**：`/[locale]/dashboard`
- **功能**：展示统计卡片（报告数、数据源数、模板数、任务数、活跃任务数、成功率）、近期报告列表。
- **所需接口**：
  - `GET /api/v1/data-sources`：获取数据源列表
  - `GET /api/v1/templates`：获取模板列表
  - `GET /api/v1/tasks`：获取任务列表
  - `GET /api/v1/report-history`：获取报告历史
  - `GET /api/v1/users/me`：获取当前用户信息
- **接口参数与返回要点**：
  - `/data-sources`、`/templates`、`/tasks` 返回 `items` 数组，含各自实体的基本信息。
  - `/report-history` 支持分页参数（如 `page`、`size`），返回报告历史列表。
  - `/users/me` 返回当前用户基本信息（如 id、用户名、角色等）。

---

### 2. 数据源管理
- **路径**：`/[locale]/data-sources`
- **功能**：增删改查数据源、测试连接、预览宽表。
- **所需接口**：
  - `GET /api/v1/data-sources`：获取数据源列表
  - `DELETE /api/v1/data-sources/{id}`：删除数据源
  - `POST /api/v1/data-sources`：新建数据源
  - `PUT /api/v1/data-sources/{id}`：编辑数据源
  - `POST /api/v1/data-sources/{id}/test`：测试数据源连接
  - `GET /api/v1/data-sources/{id}/wide-table`：获取宽表数据
- **接口参数与返回要点**：
  - 新建/编辑需提交数据源名称、类型、连接配置等。
  - 测试连接返回连接状态、错误信息。
  - 宽表接口返回表头、数据行。

#### 2.1 数据源宽表预览
- **路径**：`/[locale]/data-sources/[id]/wide-table`
- **功能**：展示指定数据源的宽表数据。
- **所需接口**：
  - `GET /api/v1/data-sources/{id}/wide-table`
- **接口参数与返回要点**：
  - 参数：数据源 id
  - 返回：表头（字段名）、数据行（数组）

---

### 3. 任务管理
- **路径**：`/[locale]/tasks`
- **功能**：任务列表展示、增删改查。
- **所需接口**：
  - `GET /api/v1/tasks`：获取任务列表
  - `DELETE /api/v1/tasks/{id}`：删除任务
  - `PUT /api/v1/tasks/{id}`：编辑任务

#### 3.1 任务详情
- **路径**：`/[locale]/tasks/[id]`
- **功能**：展示任务详情、运行任务。
- **所需接口**：
  - `GET /api/v1/tasks/{id}`：获取任务详情
  - `POST /api/v1/tasks/{id}/run`：运行任务
- **接口参数与返回要点**：
  - 任务详情返回任务基本信息、模板、数据源、调度配置、状态等。
  - 运行任务接口返回执行结果、提示信息。

#### 3.2 创建任务
- **路径**：`/[locale]/tasks/create`
- **功能**：新建任务表单，选择模板、数据源、调度配置。
- **所需接口**：
  - `GET /api/v1/templates`：获取模板列表
  - `GET /api/v1/data-sources`：获取数据源列表
  - `POST /api/v1/tasks`：新建任务
- **接口参数与返回要点**：
  - 新建任务需提交任务名、模板 id、数据源 id、调度类型、配置等。
  - 返回新建任务 id、状态。

---

### 4. 历史记录
- **路径**：`/[locale]/history`
- **功能**：展示报告生成历史。
- **所需接口**：
  - `GET /api/v1/report-history`：获取报告历史
- **接口参数与返回要点**：
  - 支持分页参数，返回报告生成记录列表。

---

### 5. 用户认证与设置
- **登录**：`/[locale]/login`，接口：`POST /api/v1/auth/login`，`GET /api/v1/users/me`
- **注册**：`/[locale]/register`，接口：`POST /api/v1/auth/register`
- **忘记密码**：`/[locale]/forgot-password`，接口：`POST /api/v1/auth/forgot-password`
- **重置密码**：`/[locale]/reset-password`，接口：`POST /api/v1/auth/reset-password`
- **邮箱验证**：`/[locale]/verify-email`，接口：`POST /api/v1/auth/verify-email`
- **退出登录**：`POST /api/v1/auth/logout`
- **接口参数与返回要点**：
  - 登录/注册/重置密码等接口需提交用户名、密码、邮箱、验证码等。
  - 返回 token、用户信息、操作结果。

---

## 接口汇总表

| 接口路径                                 | 方法   | 说明               | 主要参数           | 返回要点           |
|------------------------------------------|--------|--------------------|--------------------|--------------------|
| /api/v1/data-sources                     | GET    | 获取数据源列表     | -                  | items[]            |
| /api/v1/data-sources                     | POST   | 新建数据源         | name, type, config | id, name, type     |
| /api/v1/data-sources/{id}                | PUT    | 编辑数据源         | id, name, config   | id, name, type     |
| /api/v1/data-sources/{id}                | DELETE | 删除数据源         | id                 | success            |
| /api/v1/data-sources/{id}/test           | POST   | 测试数据源连接     | id                 | status, message    |
| /api/v1/data-sources/{id}/wide-table     | GET    | 获取宽表数据       | id                 | fields[], rows[]   |
| /api/v1/templates                        | GET    | 获取模板列表       | -                  | items[]            |
| /api/v1/tasks                            | GET    | 获取任务列表       | -                  | items[]            |
| /api/v1/tasks                            | POST   | 新建任务           | name, template_id, data_source_id, schedule | id, status |
| /api/v1/tasks/{id}                       | GET    | 获取任务详情       | id                 | 任务详情           |
| /api/v1/tasks/{id}                       | PUT    | 编辑任务           | id, ...            | 任务详情           |
| /api/v1/tasks/{id}                       | DELETE | 删除任务           | id                 | success            |
| /api/v1/tasks/{id}/run                   | POST   | 运行任务           | id                 | result, message    |
| /api/v1/report-history                   | GET    | 获取报告历史       | page, size         | items[]            |
| /api/v1/users/me                         | GET    | 获取当前用户信息   | -                  | 用户信息           |
| /api/v1/auth/login                       | POST   | 登录               | username, password | token, user        |
| /api/v1/auth/register                    | POST   | 注册               | username, password, email | user      |
| /api/v1/auth/forgot-password             | POST   | 忘记密码           | email              | success            |
| /api/v1/auth/reset-password              | POST   | 重置密码           | token, password    | success            |
| /api/v1/auth/verify-email                | POST   | 邮箱验证           | token              | success            |
| /api/v1/auth/logout                      | POST   | 退出登录           | -                  | success            |

---

> 如需补充某页面或接口的详细参数、交互流程、示例数据等，请告知！ 