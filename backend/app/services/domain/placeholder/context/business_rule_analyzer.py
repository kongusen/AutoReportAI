"""
业务规则分析器
分析业务规则、约束条件和领域特定的上下文信息
"""
import re
import logging
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
from enum import Enum
from ..models import PlaceholderSpec, DocumentContext, BusinessContext

logger = logging.getLogger(__name__)

class RuleType(Enum):
    """规则类型枚举"""
    VALIDATION = "validation"
    CALCULATION = "calculation"
    CONDITIONAL = "conditional"
    TEMPORAL = "temporal"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    BUSINESS_LOGIC = "business_logic"
    DATA_QUALITY = "data_quality"

class RulePriority(Enum):
    """规则优先级"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class BusinessRule:
    """业务规则定义"""
    rule_id: str
    rule_type: RuleType
    priority: RulePriority
    condition: str
    action: str
    description: str
    applicable_domains: List[str]
    dependencies: List[str]
    constraints: Dict[str, Any]

@dataclass
class DomainKnowledge:
    """领域知识库"""
    domain: str
    key_metrics: List[str]
    calculation_rules: Dict[str, str]
    validation_rules: Dict[str, Any]
    business_constraints: List[str]
    reporting_standards: List[str]
    glossary: Dict[str, str]

@dataclass
class ComplianceRequirement:
    """合规要求"""
    regulation_name: str
    requirement_type: str
    mandatory_fields: List[str]
    calculation_standards: Dict[str, str]
    reporting_frequency: str
    audit_trails: List[str]

@dataclass
class BusinessRuleContext:
    """业务规则上下文"""
    applicable_rules: List[BusinessRule]
    domain_knowledge: List[DomainKnowledge]
    compliance_requirements: List[ComplianceRequirement]
    constraint_conflicts: List[Dict[str, Any]]
    rule_hierarchy: Dict[str, List[str]]
    context_specific_weights: Dict[str, float]

class BusinessRuleAnalyzer:
    """业务规则分析器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.rule_repository = self._initialize_rule_repository()
        self.domain_knowledge_base = self._initialize_domain_knowledge()
        self.compliance_registry = self._initialize_compliance_registry()
        
    def _initialize_rule_repository(self) -> Dict[str, List[BusinessRule]]:
        """初始化业务规则库"""
        return {
            "financial": [
                BusinessRule(
                    rule_id="FIN001",
                    rule_type=RuleType.VALIDATION,
                    priority=RulePriority.CRITICAL,
                    condition="revenue > 0",
                    action="validate_positive_revenue",
                    description="收入必须为正数",
                    applicable_domains=["finance", "sales"],
                    dependencies=[],
                    constraints={"min_value": 0}
                ),
                BusinessRule(
                    rule_id="FIN002",
                    rule_type=RuleType.CALCULATION,
                    priority=RulePriority.HIGH,
                    condition="profit_calculation",
                    action="revenue - cost - tax",
                    description="利润计算公式",
                    applicable_domains=["finance"],
                    dependencies=["revenue", "cost", "tax"],
                    constraints={}
                ),
                BusinessRule(
                    rule_id="FIN003",
                    rule_type=RuleType.TEMPORAL,
                    priority=RulePriority.MEDIUM,
                    condition="quarterly_report",
                    action="aggregate_by_quarter",
                    description="季度报告时间聚合规则",
                    applicable_domains=["finance", "reporting"],
                    dependencies=["date_range"],
                    constraints={"frequency": "quarterly"}
                )
            ],
            "sales": [
                BusinessRule(
                    rule_id="SAL001",
                    rule_type=RuleType.BUSINESS_LOGIC,
                    priority=RulePriority.HIGH,
                    condition="conversion_rate_calculation",
                    action="leads_converted / total_leads",
                    description="转化率计算规则",
                    applicable_domains=["sales", "marketing"],
                    dependencies=["leads_converted", "total_leads"],
                    constraints={"range": [0, 1]}
                ),
                BusinessRule(
                    rule_id="SAL002",
                    rule_type=RuleType.CONDITIONAL,
                    priority=RulePriority.MEDIUM,
                    condition="high_value_customer",
                    action="annual_revenue > 100000",
                    description="大客户识别规则",
                    applicable_domains=["sales", "customer"],
                    dependencies=["annual_revenue"],
                    constraints={"threshold": 100000}
                )
            ],
            "operations": [
                BusinessRule(
                    rule_id="OPS001",
                    rule_type=RuleType.DATA_QUALITY,
                    priority=RulePriority.HIGH,
                    condition="data_completeness",
                    action="check_required_fields",
                    description="数据完整性检查",
                    applicable_domains=["operations", "quality"],
                    dependencies=[],
                    constraints={"completeness_threshold": 0.95}
                ),
                BusinessRule(
                    rule_id="OPS002",
                    rule_type=RuleType.VALIDATION,
                    priority=RulePriority.CRITICAL,
                    condition="inventory_levels",
                    action="validate_stock_levels",
                    description="库存水平验证",
                    applicable_domains=["operations", "inventory"],
                    dependencies=["current_stock", "minimum_stock"],
                    constraints={"alert_threshold": "minimum_stock"}
                )
            ]
        }
    
    def _initialize_domain_knowledge(self) -> Dict[str, DomainKnowledge]:
        """初始化领域知识库"""
        return {
            "finance": DomainKnowledge(
                domain="finance",
                key_metrics=["revenue", "profit", "cost", "margin", "ROI", "EBITDA"],
                calculation_rules={
                    "gross_profit": "revenue - cogs",
                    "net_profit": "gross_profit - operating_expenses - tax",
                    "profit_margin": "net_profit / revenue * 100",
                    "roi": "(gain - investment) / investment * 100"
                },
                validation_rules={
                    "revenue": {"type": "positive", "currency": True},
                    "cost": {"type": "positive", "currency": True},
                    "margin": {"type": "percentage", "range": [0, 100]}
                },
                business_constraints=[
                    "财务数据必须按会计准则计算",
                    "季度报告必须在季度结束后30天内完成",
                    "年度报告需要审计师确认"
                ],
                reporting_standards=["GAAP", "IFRS", "中国企业会计准则"],
                glossary={
                    "EBITDA": "息税折旧摊销前利润",
                    "ROI": "投资回报率",
                    "COGS": "销货成本"
                }
            ),
            "sales": DomainKnowledge(
                domain="sales",
                key_metrics=["revenue", "leads", "conversion_rate", "customer_acquisition_cost", "lifetime_value"],
                calculation_rules={
                    "conversion_rate": "converted_leads / total_leads * 100",
                    "customer_acquisition_cost": "marketing_spend / new_customers",
                    "average_deal_size": "total_revenue / number_of_deals"
                },
                validation_rules={
                    "leads": {"type": "integer", "min": 0},
                    "conversion_rate": {"type": "percentage", "range": [0, 100]},
                    "deal_size": {"type": "positive", "currency": True}
                },
                business_constraints=[
                    "销售数据必须每日更新",
                    "转化率计算基于有效商机",
                    "客户分级按年度营收确定"
                ],
                reporting_standards=["销售漏斗标准", "CRM数据标准"],
                glossary={
                    "MQL": "市场认可线索",
                    "SQL": "销售认可线索",
                    "CAC": "客户获取成本"
                }
            ),
            "operations": DomainKnowledge(
                domain="operations",
                key_metrics=["efficiency", "quality", "capacity_utilization", "downtime", "throughput"],
                calculation_rules={
                    "efficiency": "output / input * 100",
                    "capacity_utilization": "actual_output / max_capacity * 100",
                    "quality_rate": "passed_units / total_units * 100"
                },
                validation_rules={
                    "efficiency": {"type": "percentage", "range": [0, 200]},
                    "downtime": {"type": "duration", "unit": "hours"},
                    "throughput": {"type": "rate", "unit": "units/hour"}
                },
                business_constraints=[
                    "生产数据实时采集",
                    "质量指标符合ISO标准",
                    "设备维护按计划执行"
                ],
                reporting_standards=["ISO 9001", "精益生产标准"],
                glossary={
                    "OEE": "设备综合效率",
                    "MTBF": "平均故障间隔时间",
                    "MTTR": "平均修复时间"
                }
            )
        }
    
    def _initialize_compliance_registry(self) -> Dict[str, List[ComplianceRequirement]]:
        """初始化合规注册表"""
        return {
            "finance": [
                ComplianceRequirement(
                    regulation_name="企业会计准则",
                    requirement_type="accounting_standard",
                    mandatory_fields=["revenue", "expenses", "assets", "liabilities"],
                    calculation_standards={
                        "depreciation": "straight_line_or_accelerated",
                        "revenue_recognition": "accrual_basis"
                    },
                    reporting_frequency="quarterly",
                    audit_trails=["transaction_records", "approval_workflows"]
                ),
                ComplianceRequirement(
                    regulation_name="税务法规",
                    requirement_type="tax_compliance",
                    mandatory_fields=["taxable_income", "tax_rate", "tax_paid"],
                    calculation_standards={
                        "corporate_tax": "taxable_income * tax_rate",
                        "vat": "output_vat - input_vat"
                    },
                    reporting_frequency="monthly",
                    audit_trails=["tax_calculations", "payment_records"]
                )
            ],
            "data_protection": [
                ComplianceRequirement(
                    regulation_name="个人信息保护法",
                    requirement_type="privacy_protection",
                    mandatory_fields=["consent_status", "data_category", "retention_period"],
                    calculation_standards={},
                    reporting_frequency="annual",
                    audit_trails=["consent_records", "data_access_logs"]
                )
            ]
        }
    
    def analyze_business_rules(self, 
                              content: str,
                              business_context: BusinessContext,
                              placeholder_specs: List[PlaceholderSpec]) -> BusinessRuleContext:
        """分析业务规则上下文"""
        try:
            # 识别适用的业务规则
            applicable_rules = self._identify_applicable_rules(content, business_context)
            
            # 提取领域知识
            relevant_domains = self._identify_relevant_domains(content, placeholder_specs)
            domain_knowledge = [self.domain_knowledge_base[domain] 
                              for domain in relevant_domains 
                              if domain in self.domain_knowledge_base]
            
            # 识别合规要求
            compliance_requirements = self._identify_compliance_requirements(
                content, business_context, relevant_domains
            )
            
            # 检测约束冲突
            constraint_conflicts = self._detect_constraint_conflicts(
                applicable_rules, compliance_requirements
            )
            
            # 构建规则层次结构
            rule_hierarchy = self._build_rule_hierarchy(applicable_rules)
            
            # 计算上下文特定权重
            context_weights = self._calculate_context_weights(
                applicable_rules, business_context, placeholder_specs
            )
            
            return BusinessRuleContext(
                applicable_rules=applicable_rules,
                domain_knowledge=domain_knowledge,
                compliance_requirements=compliance_requirements,
                constraint_conflicts=constraint_conflicts,
                rule_hierarchy=rule_hierarchy,
                context_specific_weights=context_weights
            )
            
        except Exception as e:
            logger.error(f"业务规则分析失败: {e}")
            return self._create_fallback_business_context()
    
    def _identify_applicable_rules(self, 
                                  content: str, 
                                  business_context: BusinessContext) -> List[BusinessRule]:
        """识别适用的业务规则"""
        applicable_rules = []
        content_lower = content.lower()
        
        # 基于内容关键词匹配规则
        for domain, rules in self.rule_repository.items():
            for rule in rules:
                # 检查领域匹配
                if any(domain_keyword in content_lower 
                       for domain_keyword in rule.applicable_domains):
                    applicable_rules.append(rule)
                    continue
                
                # 检查依赖字段匹配
                if any(dep in content_lower for dep in rule.dependencies):
                    applicable_rules.append(rule)
                    continue
                
                # 检查规则描述关键词匹配
                rule_keywords = self._extract_rule_keywords(rule)
                if any(keyword in content_lower for keyword in rule_keywords):
                    applicable_rules.append(rule)
        
        # 基于业务上下文筛选
        context_filtered_rules = []
        for rule in applicable_rules:
            if self._is_rule_contextually_relevant(rule, business_context):
                context_filtered_rules.append(rule)
        
        return context_filtered_rules
    
    def _identify_relevant_domains(self, 
                                  content: str, 
                                  placeholder_specs: List[PlaceholderSpec]) -> List[str]:
        """识别相关领域"""
        domains = set()
        content_lower = content.lower()
        
        # 基于内容识别
        domain_keywords = {
            "finance": ["财务", "资金", "收入", "利润", "成本", "预算", "投资", "会计"],
            "sales": ["销售", "营销", "客户", "商机", "转化", "业绩", "渠道"],
            "operations": ["运营", "生产", "效率", "质量", "流程", "库存", "供应链"],
            "hr": ["人力资源", "员工", "招聘", "培训", "绩效", "薪酬"],
            "marketing": ["市场", "品牌", "推广", "活动", "用户", "流量"],
            "customer": ["客户", "服务", "满意度", "体验", "支持", "投诉"]
        }
        
        for domain, keywords in domain_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                domains.add(domain)
        
        # 基于占位符识别
        for spec in placeholder_specs:
            if hasattr(spec, 'parameters') and spec.parameters:
                for param_value in spec.parameters.values():
                    param_str = str(param_value).lower()
                    for domain, keywords in domain_keywords.items():
                        if any(keyword in param_str for keyword in keywords):
                            domains.add(domain)
        
        return list(domains)
    
    def _identify_compliance_requirements(self, 
                                        content: str,
                                        business_context: BusinessContext,
                                        domains: List[str]) -> List[ComplianceRequirement]:
        """识别合规要求"""
        requirements = []
        content_lower = content.lower()
        
        # 基于领域匹配合规要求
        for domain in domains:
            if domain in self.compliance_registry:
                requirements.extend(self.compliance_registry[domain])
        
        # 基于内容关键词匹配
        compliance_keywords = {
            "audit": ["审计", "合规", "监管", "检查"],
            "privacy": ["隐私", "个人信息", "数据保护"],
            "financial": ["会计准则", "财务报告", "税务"],
            "security": ["安全", "权限", "访问控制"]
        }
        
        for category, keywords in compliance_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                for req_list in self.compliance_registry.values():
                    for req in req_list:
                        if category in req.requirement_type:
                            requirements.append(req)
        
        return list(set(requirements))  # 去重
    
    def _detect_constraint_conflicts(self, 
                                   rules: List[BusinessRule], 
                                   compliance_reqs: List[ComplianceRequirement]) -> List[Dict[str, Any]]:
        """检测约束冲突"""
        conflicts = []
        
        # 检查规则间冲突
        for i, rule1 in enumerate(rules):
            for j, rule2 in enumerate(rules[i+1:], i+1):
                conflict = self._check_rule_conflict(rule1, rule2)
                if conflict:
                    conflicts.append({
                        "type": "rule_conflict",
                        "rule1": rule1.rule_id,
                        "rule2": rule2.rule_id,
                        "description": conflict,
                        "severity": "medium"
                    })
        
        # 检查规则与合规要求冲突
        for rule in rules:
            for req in compliance_reqs:
                conflict = self._check_rule_compliance_conflict(rule, req)
                if conflict:
                    conflicts.append({
                        "type": "compliance_conflict",
                        "rule": rule.rule_id,
                        "requirement": req.regulation_name,
                        "description": conflict,
                        "severity": "high"
                    })
        
        return conflicts
    
    def _build_rule_hierarchy(self, rules: List[BusinessRule]) -> Dict[str, List[str]]:
        """构建规则层次结构"""
        hierarchy = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": []
        }
        
        for rule in rules:
            priority_level = rule.priority.value
            hierarchy[priority_level].append(rule.rule_id)
        
        return hierarchy
    
    def _calculate_context_weights(self, 
                                  rules: List[BusinessRule],
                                  business_context: BusinessContext,
                                  placeholder_specs: List[PlaceholderSpec]) -> Dict[str, float]:
        """计算上下文特定权重"""
        weights = {}
        
        for rule in rules:
            weight = 0.0
            
            # 优先级权重
            priority_weights = {
                RulePriority.CRITICAL: 1.0,
                RulePriority.HIGH: 0.8,
                RulePriority.MEDIUM: 0.6,
                RulePriority.LOW: 0.4
            }
            weight += priority_weights.get(rule.priority, 0.5) * 0.4
            
            # 规则类型权重
            type_weights = {
                RuleType.VALIDATION: 0.9,
                RuleType.CALCULATION: 0.8,
                RuleType.BUSINESS_LOGIC: 0.7,
                RuleType.COMPLIANCE: 0.9,
                RuleType.SECURITY: 0.8
            }
            weight += type_weights.get(rule.rule_type, 0.5) * 0.3
            
            # 上下文相关性权重
            context_relevance = self._calculate_context_relevance(rule, business_context)
            weight += context_relevance * 0.2
            
            # 占位符相关性权重
            placeholder_relevance = self._calculate_placeholder_relevance(rule, placeholder_specs)
            weight += placeholder_relevance * 0.1
            
            weights[rule.rule_id] = min(1.0, weight)
        
        return weights
    
    def _extract_rule_keywords(self, rule: BusinessRule) -> List[str]:
        """提取规则关键词"""
        keywords = []
        
        # 从描述中提取
        description_words = re.findall(r'[\u4e00-\u9fff]+', rule.description)
        keywords.extend([word for word in description_words if len(word) >= 2])
        
        # 从依赖中提取
        keywords.extend(rule.dependencies)
        
        # 从约束中提取
        for key, value in rule.constraints.items():
            if isinstance(value, str):
                keywords.append(value)
        
        return list(set(keywords))
    
    def _is_rule_contextually_relevant(self, 
                                     rule: BusinessRule, 
                                     business_context: BusinessContext) -> bool:
        """判断规则是否在当前上下文中相关"""
        # 检查时间上下文相关性
        if rule.rule_type == RuleType.TEMPORAL:
            if hasattr(business_context, 'time_range') and business_context.time_range:
                return True
        
        # 检查业务类型相关性
        if hasattr(business_context, 'business_type'):
            business_type = business_context.business_type.lower()
            return any(domain in business_type for domain in rule.applicable_domains)
        
        return True  # 默认相关
    
    def _check_rule_conflict(self, rule1: BusinessRule, rule2: BusinessRule) -> Optional[str]:
        """检查两个规则是否冲突"""
        # 检查计算规则冲突
        if (rule1.rule_type == RuleType.CALCULATION and 
            rule2.rule_type == RuleType.CALCULATION):
            if (set(rule1.dependencies) & set(rule2.dependencies) and 
                rule1.action != rule2.action):
                return f"计算规则冲突：{rule1.action} vs {rule2.action}"
        
        # 检查验证规则冲突
        if (rule1.rule_type == RuleType.VALIDATION and 
            rule2.rule_type == RuleType.VALIDATION):
            common_deps = set(rule1.dependencies) & set(rule2.dependencies)
            if common_deps:
                if rule1.constraints != rule2.constraints:
                    return f"验证约束冲突：{common_deps}"
        
        return None
    
    def _check_rule_compliance_conflict(self, 
                                      rule: BusinessRule, 
                                      requirement: ComplianceRequirement) -> Optional[str]:
        """检查规则与合规要求冲突"""
        # 检查计算标准冲突
        if rule.rule_type == RuleType.CALCULATION:
            for field, standard in requirement.calculation_standards.items():
                if field in rule.dependencies and standard not in rule.action:
                    return f"计算标准冲突：规则要求 {rule.action}，合规要求 {standard}"
        
        return None
    
    def _calculate_context_relevance(self, 
                                   rule: BusinessRule, 
                                   business_context: BusinessContext) -> float:
        """计算上下文相关性"""
        relevance = 0.0
        
        # 时间相关性
        if rule.rule_type == RuleType.TEMPORAL:
            if hasattr(business_context, 'reporting_period'):
                relevance += 0.5
        
        # 业务领域相关性
        if hasattr(business_context, 'primary_domain'):
            if business_context.primary_domain in rule.applicable_domains:
                relevance += 0.5
        
        return min(1.0, relevance)
    
    def _calculate_placeholder_relevance(self, 
                                       rule: BusinessRule, 
                                       placeholder_specs: List[PlaceholderSpec]) -> float:
        """计算占位符相关性"""
        relevance = 0.0
        total_specs = len(placeholder_specs) if placeholder_specs else 1
        
        for spec in placeholder_specs:
            spec_relevance = 0.0
            
            # 依赖字段匹配
            if rule.dependencies:
                matches = sum(1 for dep in rule.dependencies if dep in spec.content)
                spec_relevance += (matches / len(rule.dependencies)) * 0.6
            
            # 领域匹配
            if hasattr(spec, 'parameters') and spec.parameters:
                for param_key, param_value in spec.parameters.items():
                    if any(domain in str(param_value).lower() 
                           for domain in rule.applicable_domains):
                        spec_relevance += 0.4
                        break
            
            relevance += spec_relevance
        
        return relevance / total_specs
    
    def _create_fallback_business_context(self) -> BusinessRuleContext:
        """创建回退业务规则上下文"""
        return BusinessRuleContext(
            applicable_rules=[],
            domain_knowledge=[],
            compliance_requirements=[],
            constraint_conflicts=[],
            rule_hierarchy={"critical": [], "high": [], "medium": [], "low": []},
            context_specific_weights={}
        )
    
    def calculate_business_rule_weight(self, 
                                     rule_context: BusinessRuleContext,
                                     placeholder_spec: PlaceholderSpec) -> float:
        """计算业务规则权重"""
        weight = 0.0
        
        # 适用规则权重
        if rule_context.applicable_rules:
            rule_weight = 0.0
            for rule in rule_context.applicable_rules:
                rule_relevance = rule_context.context_specific_weights.get(rule.rule_id, 0.0)
                
                # 检查占位符与规则的匹配度
                placeholder_match = 0.0
                if rule.dependencies:
                    matches = sum(1 for dep in rule.dependencies 
                                if dep in placeholder_spec.content)
                    placeholder_match = matches / len(rule.dependencies)
                
                rule_weight += rule_relevance * placeholder_match
            
            weight += (rule_weight / len(rule_context.applicable_rules)) * 0.4
        
        # 领域知识权重
        if rule_context.domain_knowledge:
            domain_weight = 0.0
            for domain_kb in rule_context.domain_knowledge:
                # 关键指标匹配
                metric_matches = sum(1 for metric in domain_kb.key_metrics
                                   if metric in placeholder_spec.content.lower())
                if domain_kb.key_metrics:
                    domain_weight += metric_matches / len(domain_kb.key_metrics)
            
            weight += (domain_weight / len(rule_context.domain_knowledge)) * 0.3
        
        # 合规要求权重
        if rule_context.compliance_requirements:
            compliance_weight = 0.0
            for req in rule_context.compliance_requirements:
                # 必需字段匹配
                field_matches = sum(1 for field in req.mandatory_fields
                                  if field in placeholder_spec.content.lower())
                if req.mandatory_fields:
                    compliance_weight += field_matches / len(req.mandatory_fields)
            
            weight += (compliance_weight / len(rule_context.compliance_requirements)) * 0.2
        
        # 冲突惩罚
        if rule_context.constraint_conflicts:
            conflict_penalty = len(rule_context.constraint_conflicts) * 0.1
            weight = max(0, weight - conflict_penalty)
        
        # 规则层次结构加成
        critical_rules = len(rule_context.rule_hierarchy.get("critical", []))
        high_rules = len(rule_context.rule_hierarchy.get("high", []))
        
        if critical_rules > 0:
            weight += 0.05
        if high_rules > 0:
            weight += 0.05
        
        return min(1.0, weight)