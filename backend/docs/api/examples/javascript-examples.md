# JavaScript API使用示例

## 概述

本文档提供了使用JavaScript/TypeScript调用AutoReportAI API的完整示例，包括Node.js环境和浏览器环境的使用方法。

## 环境准备

### Node.js环境

```bash
npm install axios dotenv
# 或者使用yarn
yarn add axios dotenv
```

### 浏览器环境

```html
<script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
```

### 环境配置

创建 `.env` 文件：

```bash
# .env
AUTOREPORT_API_URL=http://localhost:8000
AUTOREPORT_USERNAME=your_username
AUTOREPORT_PASSWORD=your_password
```

## 基础客户端类

```javascript
// Node.js环境
require('dotenv').config();
const axios = require('axios');

class AutoReportAPIClient {
    constructor() {
        this.baseURL = process.env.AUTOREPORT_API_URL || 'http://localhost:8000';
        this.username = process.env.AUTOREPORT_USERNAME;
        this.password = process.env.AUTOREPORT_PASSWORD;
        this.token = null;
        this.tokenExpires = null;
        
        // 创建axios实例
        this.client = axios.create({
            baseURL: this.baseURL,
            timeout: 30000,
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        // 请求拦截器
        this.client.interceptors.request.use(
            async (config) => {
                const token = await this.getToken();
                if (token) {
                    config.headers.Authorization = `Bearer ${token}`;
                }
                return config;
            },
            (error) => Promise.reject(error)
        );
        
        // 响应拦截器
        this.client.interceptors.response.use(
            (response) => response,
            async (error) => {
                if (error.response?.status === 401) {
                    // 令牌过期，重新获取
                    this.token = null;
                    const token = await this.getToken();
                    if (token) {
                        error.config.headers.Authorization = `Bearer ${token}`;
                        return this.client.request(error.config);
                    }
                }
                return Promise.reject(error);
            }
        );
    }
    
    async authenticate() {
        try {
            const response = await axios.post(`${this.baseURL}/api/v1/auth/login`, {
                username: this.username,
                password: this.password
            });
            
            const data = response.data.data;
            this.token = data.access_token;
            this.tokenExpires = new Date(Date.now() + data.expires_in * 1000);
            
            return this.token;
        } catch (error) {
            throw new Error(`认证失败: ${error.response?.data?.message || error.message}`);
        }
    }
    
    async getToken() {
        if (this.token && this.tokenExpires > new Date()) {
            return this.token;
        }
        return await this.authenticate();
    }
}
```

## TypeScript版本

```typescript
// types.ts
export interface User {
    id: string;
    username: string;
    email: string;
    full_name: string;
    is_active: boolean;
}

export interface Template {
    id: string;
    name: string;
    description: string;
    content: string;
    template_type: string;
    is_public: boolean;
    created_at: string;
    updated_at: string;
    user_id: string;
    file_size: number;
    placeholder_count: number;
}

export interface APIResponse<T> {
    success: boolean;
    message: string;
    data: T;
    timestamp: string;
}

// client.ts
import axios, { AxiosInstance } from 'axios';
import dotenv from 'dotenv';

dotenv.config();

export class AutoReportAPIClient {
    private baseURL: string;
    private username: string;
    private password: string;
    private token: string | null = null;
    private tokenExpires: Date | null = null;
    private client: AxiosInstance;
    
    constructor() {
        this.baseURL = process.env.AUTOREPORT_API_URL || 'http://localhost:8000';
        this.username = process.env.AUTOREPORT_USERNAME!;
        this.password = process.env.AUTOREPORT_PASSWORD!;
        
        this.client = axios.create({
            baseURL: this.baseURL,
            timeout: 30000,
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        this.setupInterceptors();
    }
    
    private setupInterceptors(): void {
        this.client.interceptors.request.use(
            async (config) => {
                const token = await this.getToken();
                if (token) {
                    config.headers.Authorization = `Bearer ${token}`;
                }
                return config;
            },
            (error) => Promise.reject(error)
        );
    }
    
    async authenticate(): Promise<string> {
        try {
            const response = await axios.post(`${this.baseURL}/api/v1/auth/login`, {
                username: this.username,
                password: this.password
            });
            
            const data = response.data.data;
            this.token = data.access_token;
            this.tokenExpires = new Date(Date.now() + data.expires_in * 1000);
            
            return this.token;
        } catch (error: any) {
            throw new Error(`认证失败: ${error.response?.data?.message || error.message}`);
        }
    }
    
    async getToken(): Promise<string> {
        if (this.token && this.tokenExpires && this.tokenExpires > new Date()) {
            return this.token;
        }
        return await this.authenticate();
    }
    
    // API方法
    async getCurrentUser(): Promise<User> {
        const response = await this.client.get<APIResponse<User>>('/api/v1/users/me');
        return response.data.data;
    }
    
    async getTemplates(skip: number = 0, limit: number = 10): Promise<Template[]> {
        const response = await this.client.get<APIResponse<Template[]>>(
            `/api/v1/templates?skip=${skip}&limit=${limit}`
        );
        return response.data.data;
    }
}
```

## 1. 用户认证示例

```javascript
async function authenticationExample() {
    const client = new AutoReportAPIClient();
    
    try {
        // 获取当前用户信息
        const response = await client.client.get('/api/v1/users/me');
        const userInfo = response.data.data;
        
        console.log(`登录成功！用户: ${userInfo.username}`);
        console.log(`邮箱: ${userInfo.email}`);
        
        return userInfo;
    } catch (error) {
        console.error('认证失败:', error.response?.data?.message || error.message);
        throw error;
    }
}

// 使用示例
authenticationExample()
    .then(user => console.log('用户信息:', user))
    .catch(error => console.error('错误:', error));
```

## 2. 模板管理示例

```javascript
class TemplateManager {
    constructor(client) {
        this.client = client;
    }
    
    async listTemplates(skip = 0, limit = 10) {
        try {
            const response = await this.client.client.get(
                `/api/v1/templates?skip=${skip}&limit=${limit}`
            );
            return response.data.data;
        } catch (error) {
            throw new Error(`获取模板列表失败: ${error.response?.data?.message || error.message}`);
        }
    }
    
    async createTemplate(templateData) {
        try {
            const response = await this.client.client.post('/api/v1/templates', templateData);
            return response.data.data;
        } catch (error) {
            throw new Error(`创建模板失败: ${error.response?.data?.message || error.message}`);
        }
    }
}

async function templateManagementExample() {
    const client = new AutoReportAPIClient();
    const templateManager = new TemplateManager(client);
    
    try {
        // 1. 获取模板列表
        console.log('=== 获取模板列表 ===');
        const templates = await templateManager.listTemplates();
        console.log(`找到 ${templates.length} 个模板`);
        
        templates.forEach(template => {
            console.log(`- ${template.name}: ${template.description}`);
        });
        
        // 2. 创建新模板
        console.log('\n=== 创建新模板 ===');
        const newTemplateData = {
            name: 'JavaScript示例模板',
            description: '通过JavaScript API创建的示例模板',
            content: '本月共收到{{统计:投诉总数}}件投诉，主要来自{{区域:主要投诉地区}}。',
            template_type: 'txt',
            is_public: false
        };
        
        const newTemplate = await templateManager.createTemplate(newTemplateData);
        console.log(`模板创建成功: ${newTemplate.id}`);
        
        return newTemplate;
    } catch (error) {
        console.error('模板管理失败:', error.message);
        throw error;
    }
}
```

## 3. 智能占位符处理示例

```javascript
class PlaceholderProcessor {
    constructor(client) {
        this.client = client;
    }
    
    async analyzePlaceholders(templateContent, templateId = null) {
        try {
            const requestData = {
                template_content: templateContent,
                analysis_options: {
                    include_context: true,
                    confidence_threshold: 0.7
                }
            };
            
            if (templateId) {
                requestData.template_id = templateId;
            }
            
            const response = await this.client.client.post(
                '/api/v1/intelligent-placeholders/analyze',
                requestData
            );
            
            return response.data;
        } catch (error) {
            throw new Error(`占位符分析失败: ${error.response?.data?.message || error.message}`);
        }
    }
    
    async generateIntelligentReport(templateId, dataSourceId, emailRecipients = null) {
        try {
            const requestData = {
                template_id: templateId,
                data_source_id: dataSourceId,
                processing_config: {
                    llm_provider: 'openai',
                    llm_model: 'gpt-4',
                    enable_caching: true,
                    quality_check: true
                },
                output_config: {
                    format: 'docx',
                    include_charts: true,
                    quality_report: true
                }
            };
            
            if (emailRecipients) {
                requestData.email_config = {
                    recipients: emailRecipients,
                    subject: '智能生成报告',
                    include_summary: true
                };
            }
            
            const response = await this.client.client.post(
                '/api/v1/intelligent-placeholders/generate-report',
                requestData
            );
            
            return response.data;
        } catch (error) {
            throw new Error(`报告生成失败: ${error.response?.data?.message || error.message}`);
        }
    }
}

async function placeholderProcessingExample() {
    const client = new AutoReportAPIClient();
    const processor = new PlaceholderProcessor(client);
    
    try {
        const templateContent = `
        # 月度投诉分析报告
        
        ## 数据概览
        本月共收到{{统计:投诉总数}}件投诉，比上月{{统计:环比变化}}。
        
        ## 地区分布
        投诉主要集中在{{区域:主要投诉地区}}，占总投诉量的{{统计:主要地区占比}}。
        `;
        
        const analysisResult = await processor.analyzePlaceholders(templateContent);
        console.log(`识别到 ${analysisResult.total_count} 个占位符`);
        
        analysisResult.placeholders.forEach(placeholder => {
            console.log(`- ${placeholder.placeholder_text}`);
            console.log(`  类型: ${placeholder.placeholder_type}`);
            console.log(`  置信度: ${placeholder.confidence.toFixed(2)}`);
        });
        
        return analysisResult;
    } catch (error) {
        console.error('占位符分析失败:', error.message);
        throw error;
    }
}
```

## 4. 浏览器环境示例

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AutoReportAI API 浏览器示例</title>
    <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
</head>
<body>
    <div id="app">
        <h1>AutoReportAI API 浏览器示例</h1>
        
        <div id="login-section">
            <h2>用户登录</h2>
            <input type="text" id="username" placeholder="用户名">
            <input type="password" id="password" placeholder="密码">
            <button onclick="login()">登录</button>
        </div>
        
        <div id="templates-section" style="display: none;">
            <h2>模板管理</h2>
            <button onclick="loadTemplates()">加载模板</button>
            <div id="templates-list"></div>
            
            <h3>创建新模板</h3>
            <input type="text" id="template-name" placeholder="模板名称">
            <textarea id="template-content" placeholder="模板内容"></textarea>
            <button onclick="createTemplate()">创建模板</button>
        </div>
    </div>

    <script>
        class BrowserAPIClient {
            constructor() {
                this.baseURL = 'http://localhost:8000';
                this.token = localStorage.getItem('autoreport_token');
                this.tokenExpires = localStorage.getItem('autoreport_token_expires');
                
                this.client = axios.create({
                    baseURL: this.baseURL,
                    timeout: 30000,
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                this.client.interceptors.request.use(
                    (config) => {
                        if (this.token && this.isTokenValid()) {
                            config.headers.Authorization = `Bearer ${this.token}`;
                        }
                        return config;
                    },
                    (error) => Promise.reject(error)
                );
            }
            
            isTokenValid() {
                if (!this.tokenExpires) return false;
                return new Date(this.tokenExpires) > new Date();
            }
            
            async authenticate(username, password) {
                try {
                    const response = await axios.post(`${this.baseURL}/api/v1/auth/login`, {
                        username: username,
                        password: password
                    });
                    
                    const data = response.data.data;
                    this.token = data.access_token;
                    this.tokenExpires = new Date(Date.now() + data.expires_in * 1000).toISOString();
                    
                    localStorage.setItem('autoreport_token', this.token);
                    localStorage.setItem('autoreport_token_expires', this.tokenExpires);
                    
                    return data;
                } catch (error) {
                    throw new Error(`认证失败: ${error.response?.data?.message || error.message}`);
                }
            }
        }
        
        const apiClient = new BrowserAPIClient();
        
        async function login() {
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            if (!username || !password) {
                alert('请输入用户名和密码');
                return;
            }
            
            try {
                await apiClient.authenticate(username, password);
                alert('登录成功！');
                
                document.getElementById('login-section').style.display = 'none';
                document.getElementById('templates-section').style.display = 'block';
                
            } catch (error) {
                alert(`登录失败: ${error.message}`);
            }
        }
        
        async function loadTemplates() {
            try {
                const response = await apiClient.client.get('/api/v1/templates?limit=10');
                const templates = response.data.data;
                
                const listElement = document.getElementById('templates-list');
                listElement.innerHTML = '<h3>模板列表</h3>';
                
                templates.forEach(template => {
                    const templateDiv = document.createElement('div');
                    templateDiv.innerHTML = `
                        <p><strong>${template.name}</strong></p>
                        <p>${template.description}</p>
                        <p>占位符数量: ${template.placeholder_count || 0}</p>
                        <hr>
                    `;
                    listElement.appendChild(templateDiv);
                });
                
            } catch (error) {
                alert(`加载模板失败: ${error.response?.data?.message || error.message}`);
            }
        }
        
        async function createTemplate() {
            const name = document.getElementById('template-name').value;
            const content = document.getElementById('template-content').value;
            
            if (!name || !content) {
                alert('请输入模板名称和内容');
                return;
            }
            
            try {
                const templateData = {
                    name: name,
                    description: '通过浏览器创建的模板',
                    content: content,
                    template_type: 'txt',
                    is_public: false
                };
                
                const response = await apiClient.client.post('/api/v1/templates', templateData);
                const newTemplate = response.data.data;
                
                alert(`模板创建成功！ID: ${newTemplate.id}`);
                
                document.getElementById('template-name').value = '';
                document.getElementById('template-content').value = '';
                
                loadTemplates();
                
            } catch (error) {
                alert(`创建模板失败: ${error.response?.data?.message || error.message}`);
            }
        }
    </script>
</body>
</html>
```

## 总结

本文档提供了使用JavaScript/TypeScript调用AutoReportAI API的完整示例，包括：

1. **Node.js环境的基础客户端**
2. **TypeScript类型定义和类型安全**
3. **浏览器环境的使用方法**
4. **完整的HTML页面示例**

这些示例涵盖了从基础认证到复杂业务逻辑的各种使用场景，可以作为集成AutoReportAI API到您的JavaScript应用程序的参考。

## 相关资源

- [API参考文档](http://localhost:8000/api/v1/docs)
- [Python示例](./python-examples.md)
- [最佳实践指南](../best-practices.md)
- [常见问题解答](../faq.md)