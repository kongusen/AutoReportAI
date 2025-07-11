# AutoReportAI - 系统架构与功能方案 (v2)

## 1. 概览 (Overview)

本项目旨在构建一个名为“AutoReportAI”的自动化报告生成系统。系统以用户上传的Word文档为模板，通过连接外部业务数据库获取实时数据，并利用数据分析和AI能力，自动填充模板生成分析报告，最终通过邮件分发并归档。

整个系统采用现代化、容器化的微服务思想进行设计，确保各模块的高内聚、低耦合，方便独立开发、测试、部署和扩展。所有核心功能都将通过“MCP（Machine-Callable Platform）接口”（即RESTful API）暴露，便于AI模块或任何其他系统集成调用。

### 1.1. 技术栈

*   **后端框架**: Python 3.9 + FastAPI (高性能、异步Web框架)
*   **数据库**: PostgreSQL (稳定、强大的开源关系型数据库)
*   **数据持久化/ORM**: SQLAlchemy
*   **数据分析与处理**: Pandas, NumPy
*   **图表生成**: Matplotlib
*   **Word文档处理**: python-docx
*   **前端框架**: Next.js (React框架，支持服务端渲染)
*   **部署与运维**: Docker, Docker Compose
*   **任务调度**: APScheduler (或Celery Beat)

## 2. 系统架构图 (System Architecture Diagram)

```mermaid
graph TD
    subgraph "用户/管理员"
        A[浏览器]
    end

    subgraph "前端 (Next.js)"
        B[Web界面]
    end

    subgraph "后端 (FastAPI on Docker)"
        C{API网关}
        C -- "/templates" --> D[模板管理 (CRUD & Parse)]
        C -- "/mappings" --> E[数据映射管理]
        C -- "/reports" --> F[报告生成流程]
        C -- "/tasks" --> G[任务管理]
        C -- "/ai" --> H[AI服务 (文本 & 图表)]
        C -- "/files" --> I[文件服务]
    end

    subgraph "持久化与存储 (Docker Volumes)"
        J[(PostgreSQL DB)]
        K[/templates]
        L[/generated_reports]
    end

    subgraph "外部依赖"
        M[(业务数据库)]
        N((SMTP邮件服务))
    end
    
    subgraph "调度器 (Scheduler)"
        O[任务调度进程]
    end

    A -- "访问" --> B
    B -- "调用MCP接口" --> C
    
    D -- "读/写模板文件" --> K
    D -- "读/写模板元数据/JSON" --> J
    
    E -- "定义占位符与SQL的映射" --> J
    
    F -- "调用" --> H
    F -- "读取映射" --> E
    F -- "连接/查询" --> M
    F -- "读取模板JSON" --> D
    F -- "生成Word" --> L
    F -- "发送邮件" --> N

    G -- "读/写" --> J
    I -- "读/写" --> L
    
    O -- "定时触发" --> F
    O -- "读取任务" --> G
```

## 3. 核心数据库模型 (Core DB Models)

为支持新功能，数据库将包含以下核心模型：

*   `Template`: 存储模板信息，包括文件名、描述以及**首次解析后缓存的JSON结构**。
*   `PlaceholderMapping`: 存储每个占位符的详细映射规则。
    *   `template_id`: 关联到具体的模板。
    *   `placeholder_name`: 占位符名称（如 `total_sales`）。
    *   `placeholder_type`: 占位符类型（`query`, `computed`, `chart`, `table`）。
    *   `source_logic`: 数据源逻辑。如果类型是`query`，这里就存SQL语句；如果是`chart`，这里存用于获取图表数据的SQL。
    *   `description`: 占位符的自然语言描述（特别是对于图表）。

## 4. 模块功能详解 (Detailed Module Functions)

### 4.1. 模板管理 (Template Management) - 已升级
*   **核心能力**: 提供模板的完整CRUD能力。上传新模板时解析其结构并存入数据库，避免后续重复解析。
*   **开发思路**:
    1.  **接口**:
        *   `POST /api/v1/templates`: 上传`.docx`文件。服务会将文件存入`/templates`目录，然后**立即解析**，并将文件名和解析出的JSON结构存入`Template`表。
        *   `GET /api/v1/templates`: 列出所有数据库中已记录的模板。
        *   `GET /api/v1/templates/{id}`: 获取单个模板的详细信息（包括其缓存的JSON结构）。
        *   `PUT /api/v1/templates/{id}`: 更新模板元数据（如描述）。
        *   `DELETE /api/v1/templates/{id}`: 从数据库和文件系统中删除模板。
    2.  **解析逻辑增强**: 解析函数需要能识别更丰富的、统一带有描述的占位符格式。我们将使用正则表达式来捕获括号或引号内的描述。
        *   查询/计算占位: `{{total_sales "返回公司本年度的总销售额"}}`
        *   图表占位: `[chart:sales_by_region "生成一张柱状图，展示按区域划分的销售额排名前五的地区"]`
        *   表格占位: `[table:detailed_sales "列出所有销售记录的详细信息，包括区域、产品和金额"]`
    3.  **输出**: 解析后的JSON将包含占位符名称、类型和从模板中提取的自然语言描述。
        ```json
        {
          "placeholders": [
            {"name": "total_sales", "type": "scalar", "description": "返回公司本年度的总销售额"},
            {"name": "sales_by_region", "type": "chart", "description": "生成一张柱状图，展示按区域划分的销售额排名前五的地区"},
            {"name": "detailed_sales", "type": "table", "description": "列出所有销售记录的详细信息，包括区域、产品和金额"}
          ]
        }
        ```

### 4.2. 数据映射管理 (Data Mapping Management) - 新增
*   **核心能力**: 为模板中的每个占位符配置其数据来源。
*   **开发思路**:
    1.  **接口**: `POST /api/v1/templates/{template_id}/mappings`
    2.  **输入**: 一个映射配置列表。
        ```json
        [
          {
            "placeholder_name": "total_sales",
            "placeholder_type": "query",
            "source_logic": "SELECT SUM(amount) FROM sales WHERE sale_date > '2023-01-01';"
          },
          {
            "placeholder_name": "sales_by_region",
            "placeholder_type": "chart",
            "source_logic": "SELECT region, SUM(amount) FROM sales GROUP BY region ORDER BY SUM(amount) DESC LIMIT 5;"
          }
        ]
        ```
    3.  **处理**: 服务将这些配置存入`PlaceholderMapping`表，与`template_id`关联。

### 4.3. AI服务 (AI Service) - 已升级
*   **核心能力**:
    *   **(已有)** 接收结构化数据，撰写分析性文本。
    *   **(新增)** 接收**图表数据的查询结果**和**自然语言描述**，调用`matplotlib`生成图表。
*   **开发思路**:
    1.  **接口**: `POST /api/v1/ai/generate-chart`
    2.  **输入**:
        ```json
        {
          "description": "近半年各区域销售额对比柱状图",
          "data": [{"region": "昆明", "total": 500}, {"region": "大理", "total": 400}]
        }
        ```
    3.  **处理**:
        *   使用`pandas`将输入数据转换为DataFrame。
        *   **解析描述**: 通过关键词（如 "柱状图", "饼图", "折线图"）判断要生成的图表类型。
        *   **动态绘图**: 调用`matplotlib`的相应函数进行绘图。可以根据描述中的其他关键词调整样式（如“对比”可能意味着使用不同颜色）。
        *   **中文支持**: 确保在绘图时指定了已安装的中文字体。
    4.  **输出**: Base64编码的图表图片字符串。

### 4.4. 报告生成与分发 (Report Generation & Distribution) - 已升级
*   **核心能力**: 升级版的流程编排，能处理模板、映射、数据、AI的全流程调用。
*   **开发思路**:
    1.  **接口**: `POST /api/v1/reports/generate`
    2.  **输入**: `{ "template_id": 1, "recipients": ["test@example.com"], "report_name": "2023年10月销售报告" }`
    3.  **处理 (新流程)**:
        1.  根据`template_id`从数据库获取模板的缓存JSON结构和所有关联的`PlaceholderMapping`。
        2.  遍历`mappings`，执行SQL查询获取所有占位符所需的数据，形成一个**原始数据集**。
        3.  遍历原始数据集，找到所有图表类型的数据。
        4.  对每一个图表数据，调用**AI图表生成服务 (4.3)**，传入数据和描述，获取Base64图片。将返回的图片字符串**更新/替换**到数据集中。
        5.  (可选) 调用AI文本生成服务，丰富报告内容。
        6.  调用`WordGeneratorService`，传入模板文件和**最终处理完成的数据集**（其中图表占位符的值现在是Base64图片），生成报告。
        7.  调用`EmailService`，在后台任务中发送邮件。

### 3.5. 任务管理与调度 (Task Management & Scheduling)
*   **核心能力**: 提供一个管理界面和API，用于创建、配置和管理周期性的报告生成任务。
*   **开发思路**:
    1.  **数据模型**: `Task`表已在PostgreSQL中定义，包含任务名称、CRON表达式格式的调度周期、关联的模板、收件人等信息。
    2.  **接口 (MCP)**:
        *   `GET /api/v1/tasks`: 列出所有任务。
        *   `POST /api/v1/tasks`: 创建新任务。
        *   `PUT /api/v1/tasks/{task_id}`: 更新任务。
        *   `DELETE /api/v1/tasks/{task_id}`: 删除任务。
    3.  **调度器 (Scheduler)**:
        *   这将是一个**独立的Python进程**，与FastAPI应用一同通过`docker-compose`启动。
        *   使用`APScheduler`库，配置其使用我们的PostgreSQL作为任务存储后端。
        *   调度器启动后，会从`Task`表中加载所有启用的任务。
        *   当任务到达预定时间时，调度器会组装一个请求（包含模板、收件人等信息），并**通过HTTP调用报告生成的API接口** (`POST /api/v1/reports/generate`) 来触发报告生成流程。这种通过API解耦的方式比在调度器进程内执行业务逻辑更加健壮和可扩展。

### 3.6. 文件系统与前端 (File System & Frontend)
*   **核心能力**: 提供一个用户友好的Web界面，用于管理模板、任务、查看和下载已生成的报告。
*   **开发思路**:
    1.  **后端支持**: 提供API接口用于文件操作。
        *   `GET /api/v1/files`: 列出`/generated_reports`目录下的所有报告。
        *   `GET /api/v1/files/{filename}`: 下载指定的报告文件。
    2.  **前端实现 (Next.js)**:
        *   创建一个仪表盘（Dashboard）布局。
        *   **模板管理页**: 展示已上传的模板，允许上传新模板，点击模板可以触发分析并查看其JSON结构。
        *   **任务管理页**: 调用任务管理API，通过表单实现对定时任务的增删改查。
        *   **报告库**: 调用文件服务API，展示所有已生成的报告，并提供下载按钮。

## 5. 下一步开发计划 (Next Steps) - 已更新

1.  **数据库模型更新**:
    *   在`backend/app/models`中创建`template.py`和`placeholder_mapping.py`。
    *   在`backend/app/schemas`中为新模型创建对应的Pydantic Schema。
    *   更新`backend/app/initial_data.py`以在启动时创建新表。
2.  **实现模板管理 (CRUD)**:
    *   创建`crud_template.py`。
    *   重构`template_analysis.py`端点，实现文件的上传、解析、存储和管理功能。
3.  **实现数据映射管理**:
    *   创建`crud_placeholder_mapping.py`。
    *   创建`mapping_management.py` API端点。
4.  **升级AI和报告生成服务**:
    *   实现`ai/generate-chart`接口的逻辑。
    *   重构`report_generation.py`端点以遵循新的、更复杂的编排流程。
5.  **构建和测试**:
    *   在完成上述模块后，通过`docker-compose`重新构建和测试端到端的报告生成流程。
6.  **前端开发**:
    *   前端需要新增**模板管理**和**数据映射配置**界面。 