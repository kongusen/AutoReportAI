# API 常见问题解答 (FAQ)

## 🔐 认证和安全

### Q: 如何获取API访问令牌？
**A**: 通过登录端点获取访问令牌：

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'
```

成功后会返回包含`access_token`的响应。

### Q: 访问令牌多长时间过期？
**A**: 默认访问令牌有效期为30分钟（1800秒）。过期后需要重新登录获取新令牌。

### Q: 如何在请求中使用访问令牌？
**A**: 在请求头中添加Authorization字段：

```bash
curl -X GET "http://localhost:8000/api/v1/templates" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Q: 如何检查令牌是否过期？
**A**: JWT令牌包含过期时间信息，可以解析令牌payload检查：

```javascript
function isTokenExpired(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return Date.now() >= payload.exp * 1000;
  } catch {
    return true;
  }
}
```

### Q: API支持哪些安全措施？
**A**: 
- JWT令牌认证
- HTTPS加密传输
- 请求速率限制
- 输入验证和清理
- SQL注入防护
- CORS安全配置

## 📄 模板管理

### Q: 支持哪些模板文件格式？
**A**: 目前支持以下格式：
- Microsoft Word (.docx)
- PDF (.pdf)
- HTML (.html)
- 纯文本 (.txt)

### Q: 模板文件大小有限制吗？
**A**: 是的，单个模板文件最大支持10MB。如果需要上传更大的文件，请联系技术支持。

### Q: 如何在模板中使用占位符？
**A**: 使用双花括号语法，格式为`{{类型:描述}}`：

```
本月{{统计:投诉总数}}件投诉中，{{区域:主要投诉地区}}占比最高。
{{周期:上月同期}}相比{{统计:同比增长率}}。
```

### Q: 支持哪些占位符类型？
**A**: 目前支持以下类型：
- **统计**: 数值统计和计算
- **区域**: 地理位置相关
- **周期**: 时间周期相关
- **图表**: 数据可视化

### Q: 可以创建私有模板吗？
**A**: 是的，创建模板时设置`is_public: false`即可创建私有模板，只有创建者可以访问。

### Q: 如何批量管理模板？
**A**: 目前需要逐个操作模板。批量操作功能计划在v1.1.0版本中添加。

## 🧠 智能占位符

### Q: 占位符分析需要多长时间？
**A**: 通常在几秒内完成，具体时间取决于：
- 模板内容长度
- 占位符数量和复杂度
- 是否需要数据源验证

### Q: 字段匹配的置信度如何计算？
**A**: 置信度基于以下因素：
- 语义相似度
- 字段名匹配度
- 数据类型兼容性
- 上下文相关性

### Q: 如何提高字段匹配准确性？
**A**: 
- 提供清晰的占位符描述
- 包含充分的上下文信息
- 使用标准的字段命名
- 确保数据源字段文档完整

### Q: 智能报告生成失败怎么办？
**A**: 
1. 检查任务状态获取详细错误信息
2. 验证模板和数据源配置
3. 确认占位符格式正确
4. 检查数据源连接状态
5. 如问题持续，联系技术支持

### Q: 可以自定义占位符类型吗？
**A**: 目前不支持自定义类型，但这个功能在我们的开发计划中。

### Q: 支持哪些LLM提供商？
**A**: 目前支持：
- OpenAI (GPT-3.5, GPT-4)
- Anthropic Claude
- 计划支持更多提供商

## 🗄️ 数据源

### Q: 支持哪些数据源类型？
**A**: 目前支持：
- PostgreSQL
- MySQL
- SQL Server
- Oracle
- SQLite
- MongoDB (计划中)
- REST API (计划中)

### Q: 如何测试数据源连接？
**A**: 创建数据源时设置`test_connection: true`，或使用连接测试端点：

```bash
curl -X POST "http://localhost:8000/api/v1/data-sources/{id}/test" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Q: 数据源连接信息如何保护？
**A**: 
- 连接密码使用AES加密存储
- 传输过程使用HTTPS加密
- 数据库连接使用SSL/TLS
- 访问日志记录和监控

### Q: 可以连接云数据库吗？
**A**: 是的，支持连接各种云数据库服务，如AWS RDS、Azure SQL、Google Cloud SQL等。

### Q: 数据源查询有性能限制吗？
**A**: 
- 单次查询最多返回10,000条记录
- 查询超时时间为30秒
- 支持分页查询处理大数据集

## 📊 报告生成

### Q: 报告生成需要多长时间？
**A**: 时间取决于：
- 模板复杂度
- 占位符数量
- 数据源查询复杂度
- 选择的输出格式

通常在1-5分钟内完成。

### Q: 支持哪些输出格式？
**A**: 
- Microsoft Word (.docx)
- PDF (.pdf)
- HTML (.html)
- 计划支持Excel (.xlsx)

### Q: 可以自动发送报告邮件吗？
**A**: 是的，在报告生成请求中配置`email_config`：

```json
{
  "email_config": {
    "recipients": ["user@example.com"],
    "subject": "智能生成报告",
    "include_summary": true
  }
}
```

### Q: 如何监控报告生成进度？
**A**: 使用任务状态查询端点：

```bash
curl -X GET "http://localhost:8000/api/v1/intelligent-placeholders/task/{task_id}/status" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Q: 生成的报告存储在哪里？
**A**: 报告文件存储在服务器的安全目录中，只有授权用户可以访问。文件会定期清理。

### Q: 可以下载生成的报告吗？
**A**: 是的，通过报告详情接口获取下载链接，或使用专门的下载端点。

## 🔧 技术问题

### Q: API请求频率有限制吗？
**A**: 是的，默认限制为每分钟60个请求。如需更高频率，请联系我们。

### Q: 如何处理API错误？
**A**: 所有错误都返回统一格式：

```json
{
  "success": false,
  "message": "错误描述",
  "error": {
    "code": "ERROR_CODE",
    "details": {}
  }
}
```

参考[错误代码文档](./error-codes.md)了解详细信息。

### Q: 支持批量操作吗？
**A**: 目前大部分操作需要逐个进行。批量操作支持计划在v1.1.0版本中添加。

### Q: 如何优化API性能？
**A**: 
- 使用分页查询大数据集
- 启用客户端缓存
- 合理设置查询参数
- 避免频繁的重复请求
- 使用WebSocket接收实时通知

### Q: API支持HTTPS吗？
**A**: 是的，生产环境强制使用HTTPS。开发环境可以使用HTTP。

### Q: 如何处理超时问题？
**A**: 
- 检查网络连接
- 简化复杂查询
- 使用异步处理长时间任务
- 实现客户端重试机制

## 📱 集成和开发

### Q: 有官方SDK吗？
**A**: 
- Python SDK: `pip install autoreportai-sdk`
- JavaScript SDK: `npm install autoreportai-js`
- 其他语言SDK正在开发中

### Q: 如何在前端应用中集成？
**A**: 参考我们的[最佳实践指南](./best-practices.md)，包含详细的集成示例。

### Q: 支持Webhook通知吗？
**A**: Webhook支持计划在v1.2.0版本中添加。目前可以使用WebSocket接收实时通知。

### Q: 如何进行API测试？
**A**: 
- 使用Swagger UI进行交互式测试
- 导入Postman集合进行测试
- 使用我们提供的测试环境

### Q: 有测试环境吗？
**A**: 是的，测试环境地址：`http://test.autoreportai.com/api/v1`

### Q: 如何获取API使用统计？
**A**: 使用统计端点获取使用情况：

```bash
curl -X GET "http://localhost:8000/api/v1/intelligent-placeholders/statistics" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 💰 计费和限制

### Q: API使用是否收费？
**A**: 基础功能免费使用，高级功能和大量使用可能需要付费。详情请联系销售团队。

### Q: 有使用量限制吗？
**A**: 
- 免费用户：每月1000次API调用
- 付费用户：根据套餐不同有不同限制
- 企业用户：可定制限制

### Q: 如何查看使用量？
**A**: 通过用户面板或API统计端点查看当前使用量。

## 🆘 支持和帮助

### Q: 如何获得技术支持？
**A**: 
- 邮箱：support@autoreportai.com
- 技术支持：tech@autoreportai.com
- GitHub Issues：https://github.com/autoreportai/issues
- 在线文档：查看详细文档和示例

### Q: 支持哪些语言？
**A**: 
- 中文（简体）
- 英文
- 计划支持更多语言

### Q: 如何报告Bug？
**A**: 
1. 通过GitHub Issues报告
2. 发送邮件到bugs@autoreportai.com
3. 提供详细的重现步骤和错误信息

### Q: 如何提出功能建议？
**A**: 
- GitHub Discussions：https://github.com/autoreportai/discussions
- 功能建议邮箱：features@autoreportai.com
- 用户反馈表单

### Q: 有用户社区吗？
**A**: 
- GitHub Discussions
- 官方QQ群：123456789
- 微信群：联系客服获取邀请

### Q: 文档更新频率如何？
**A**: 文档与API版本同步更新，重大更新会及时通知用户。

### Q: 如何获取最新消息？
**A**: 
- 关注GitHub仓库
- 订阅邮件通知
- 关注官方社交媒体账号

---

## 📞 联系我们

如果您的问题没有在FAQ中找到答案，请通过以下方式联系我们：

- **技术支持**: tech@autoreportai.com
- **一般咨询**: support@autoreportai.com
- **商务合作**: business@autoreportai.com
- **GitHub**: https://github.com/autoreportai
- **官网**: https://autoreportai.com

我们会尽快回复您的问题！

---

**最后更新**: 2024-01-01  
**文档版本**: v1.0.0