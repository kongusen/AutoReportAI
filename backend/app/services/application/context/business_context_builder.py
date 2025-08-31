"""
业务上下文构建器
将业务需求和组织信息转换为标准的BusinessContext对象
"""
import logging
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from app.services.domain.placeholder.models import BusinessContext

logger = logging.getLogger(__name__)

class BusinessType(Enum):
    """业务类型枚举"""
    RETAIL = "retail"
    E_COMMERCE = "e-commerce"
    MANUFACTURING = "manufacturing"
    FINANCIAL_SERVICES = "financial_services"
    TECHNOLOGY = "technology"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    GOVERNMENT = "government"
    NON_PROFIT = "non_profit"
    CONSULTING = "consulting"
    REAL_ESTATE = "real_estate"
    LOGISTICS = "logistics"

class CompanySize(Enum):
    """公司规模枚举"""
    STARTUP = "startup"        # < 10人
    SMALL = "small"           # 10-50人
    MEDIUM = "medium"         # 50-500人
    LARGE = "large"           # 500-5000人
    ENTERPRISE = "enterprise" # > 5000人

class IndustryDomain(Enum):
    """行业领域枚举"""
    FINANCE = "finance"
    SALES = "sales"
    MARKETING = "marketing"
    OPERATIONS = "operations"
    HR = "hr"
    IT = "it"
    CUSTOMER_SERVICE = "customer_service"
    SUPPLY_CHAIN = "supply_chain"
    PRODUCT = "product"
    STRATEGY = "strategy"

class DataMaturity(Enum):
    """数据成熟度枚举"""
    BASIC = "basic"           # 基础数据收集
    INTERMEDIATE = "intermediate"  # 有一定数据分析能力
    ADVANCED = "advanced"     # 高级数据分析和洞察
    EXPERT = "expert"         # 数据驱动决策文化

@dataclass
class OrganizationalProfile:
    """组织概况"""
    company_name: Optional[str] = None
    business_type: BusinessType = BusinessType.TECHNOLOGY
    company_size: CompanySize = CompanySize.MEDIUM
    industry_domains: List[IndustryDomain] = None
    primary_domain: IndustryDomain = IndustryDomain.OPERATIONS
    data_maturity: DataMaturity = DataMaturity.INTERMEDIATE
    regions: List[str] = None
    languages: List[str] = None
    
    def __post_init__(self):
        if self.industry_domains is None:
            self.industry_domains = [self.primary_domain]
        if self.regions is None:
            self.regions = ["china"]
        if self.languages is None:
            self.languages = ["chinese"]

@dataclass
class ComplianceProfile:
    """合规配置"""
    regulations: List[str] = None
    data_governance: bool = True
    audit_requirements: List[str] = None
    privacy_level: str = "medium"
    retention_policies: Dict[str, str] = None
    
    def __post_init__(self):
        if self.regulations is None:
            self.regulations = []
        if self.audit_requirements is None:
            self.audit_requirements = []
        if self.retention_policies is None:
            self.retention_policies = {}

@dataclass
class PerformanceProfile:
    """绩效配置"""
    kpi_framework: str = "balanced_scorecard"
    target_metrics: Dict[str, Union[int, float]] = None
    benchmark_sources: List[str] = None
    measurement_frequency: str = "monthly"
    
    def __post_init__(self):
        if self.target_metrics is None:
            self.target_metrics = {}
        if self.benchmark_sources is None:
            self.benchmark_sources = ["internal_historical", "industry_average"]

class BusinessContextBuilder:
    """业务上下文构建器"""
    
    def __init__(self, 
                 default_profile: Optional[OrganizationalProfile] = None):
        self.default_profile = default_profile or OrganizationalProfile()
        self._domain_templates = self._initialize_domain_templates()
        self._compliance_templates = self._initialize_compliance_templates()
        self._performance_templates = self._initialize_performance_templates()
    
    def _initialize_domain_templates(self) -> Dict[IndustryDomain, Dict[str, Any]]:
        """初始化领域模板"""
        return {
            IndustryDomain.FINANCE: {
                "key_metrics": ["revenue", "profit_margin", "cash_flow", "roi", "budget_variance"],
                "reporting_standards": ["GAAP", "IFRS"],
                "regulatory_focus": ["financial_reporting", "risk_management"],
                "typical_periods": ["monthly", "quarterly", "yearly"],
                "stakeholders": ["investors", "auditors", "management", "regulators"]
            },
            IndustryDomain.SALES: {
                "key_metrics": ["revenue", "leads", "conversion_rate", "deal_size", "customer_acquisition_cost"],
                "reporting_standards": ["CRM_standards", "sales_methodology"],
                "regulatory_focus": ["customer_privacy", "contract_compliance"],
                "typical_periods": ["daily", "weekly", "monthly"],
                "stakeholders": ["sales_team", "management", "marketing", "customers"]
            },
            IndustryDomain.MARKETING: {
                "key_metrics": ["traffic", "engagement", "conversion_rate", "cost_per_acquisition", "brand_awareness"],
                "reporting_standards": ["digital_marketing", "brand_guidelines"],
                "regulatory_focus": ["data_privacy", "advertising_compliance"],
                "typical_periods": ["daily", "weekly", "monthly"],
                "stakeholders": ["marketing_team", "management", "sales", "customers"]
            },
            IndustryDomain.OPERATIONS: {
                "key_metrics": ["efficiency", "quality", "capacity_utilization", "downtime", "cost_per_unit"],
                "reporting_standards": ["ISO_9001", "lean_manufacturing"],
                "regulatory_focus": ["safety_compliance", "environmental_compliance"],
                "typical_periods": ["hourly", "daily", "weekly"],
                "stakeholders": ["operations_team", "management", "quality_assurance", "suppliers"]
            },
            IndustryDomain.HR: {
                "key_metrics": ["headcount", "turnover_rate", "satisfaction_score", "training_hours", "recruitment_cost"],
                "reporting_standards": ["HR_best_practices", "employment_law"],
                "regulatory_focus": ["employment_compliance", "diversity_reporting"],
                "typical_periods": ["weekly", "monthly", "quarterly"],
                "stakeholders": ["hr_team", "management", "employees", "unions"]
            }
        }
    
    def _initialize_compliance_templates(self) -> Dict[str, ComplianceProfile]:
        """初始化合规模板"""
        return {
            "financial_services": ComplianceProfile(
                regulations=["Basel_III", "GDPR", "SOX", "PCI_DSS"],
                audit_requirements=["external_audit", "internal_audit", "risk_assessment"],
                privacy_level="high",
                retention_policies={"financial_records": "7_years", "customer_data": "5_years"}
            ),
            "healthcare": ComplianceProfile(
                regulations=["HIPAA", "FDA", "GDPR"],
                audit_requirements=["compliance_audit", "security_audit"],
                privacy_level="high",
                retention_policies={"patient_data": "permanent", "clinical_trial": "25_years"}
            ),
            "government": ComplianceProfile(
                regulations=["FISMA", "FOIA", "privacy_act"],
                audit_requirements=["security_audit", "transparency_audit"],
                privacy_level="high",
                retention_policies={"public_records": "permanent", "personal_data": "lifecycle"}
            ),
            "general": ComplianceProfile(
                regulations=["GDPR", "local_privacy_laws"],
                audit_requirements=["annual_audit"],
                privacy_level="medium",
                retention_policies={"business_records": "5_years", "customer_data": "3_years"}
            )
        }
    
    def _initialize_performance_templates(self) -> Dict[CompanySize, PerformanceProfile]:
        """初始化绩效模板"""
        return {
            CompanySize.STARTUP: PerformanceProfile(
                kpi_framework="growth_metrics",
                target_metrics={"growth_rate": 200, "burn_rate": -50000, "user_acquisition": 1000},
                benchmark_sources=["startup_benchmarks"],
                measurement_frequency="weekly"
            ),
            CompanySize.SMALL: PerformanceProfile(
                kpi_framework="simple_kpi",
                target_metrics={"revenue_growth": 50, "customer_satisfaction": 85, "profit_margin": 15},
                benchmark_sources=["industry_average", "internal_historical"],
                measurement_frequency="monthly"
            ),
            CompanySize.MEDIUM: PerformanceProfile(
                kpi_framework="balanced_scorecard",
                target_metrics={"revenue_growth": 25, "customer_satisfaction": 90, "employee_satisfaction": 80},
                benchmark_sources=["industry_average", "best_practices", "internal_historical"],
                measurement_frequency="monthly"
            ),
            CompanySize.LARGE: PerformanceProfile(
                kpi_framework="okr",
                target_metrics={"revenue_growth": 15, "market_share": 25, "innovation_index": 75},
                benchmark_sources=["industry_leaders", "market_research", "internal_historical"],
                measurement_frequency="quarterly"
            ),
            CompanySize.ENTERPRISE: PerformanceProfile(
                kpi_framework="enterprise_scorecard",
                target_metrics={"revenue_growth": 10, "operational_excellence": 95, "stakeholder_value": 85},
                benchmark_sources=["market_leaders", "analyst_reports", "peer_comparison"],
                measurement_frequency="quarterly"
            )
        }
    
    def build_from_user_context(self, 
                               user_role: Optional[str] = None,
                               department: Optional[str] = None,
                               company_info: Optional[Dict[str, Any]] = None,
                               project_context: Optional[Dict[str, Any]] = None) -> BusinessContext:
        """
        从用户上下文构建业务上下文
        
        Args:
            user_role: 用户角色
            department: 部门
            company_info: 公司信息
            project_context: 项目上下文
        """
        try:
            # 确定主要业务领域
            primary_domain = self._determine_primary_domain(user_role, department)
            
            # 构建组织配置
            org_context = self._build_organizational_context(company_info, primary_domain)
            
            # 构建合规要求
            compliance_requirements = self._build_compliance_requirements(
                org_context, company_info
            )
            
            # 构建绩效目标
            performance_targets = self._build_performance_targets(
                org_context, primary_domain, project_context
            )
            
            return BusinessContext(
                business_type=org_context.get("business_type", "technology"),
                primary_domain=primary_domain.value if isinstance(primary_domain, IndustryDomain) else primary_domain,
                compliance_requirements=compliance_requirements,
                performance_targets=performance_targets,
                organizational_context=org_context,
                metadata=self._build_metadata(user_role, department, project_context)
            )
            
        except Exception as e:
            logger.error(f"业务上下文构建失败: {e}")
            return self._create_default_business_context()
    
    def build_for_domain(self, 
                        domain: Union[IndustryDomain, str],
                        company_size: Optional[CompanySize] = None,
                        business_type: Optional[BusinessType] = None,
                        custom_config: Optional[Dict[str, Any]] = None) -> BusinessContext:
        """
        为特定业务领域构建上下文
        
        Args:
            domain: 业务领域
            company_size: 公司规模
            business_type: 业务类型
            custom_config: 自定义配置
        """
        if isinstance(domain, str):
            try:
                domain = IndustryDomain(domain)
            except ValueError:
                logger.warning(f"未知业务领域: {domain}, 使用默认配置")
                domain = IndustryDomain.OPERATIONS
        
        # 获取领域模板
        domain_template = self._domain_templates.get(domain, {})
        
        # 构建组织上下文
        org_context = {
            "company_size": (company_size or self.default_profile.company_size).value,
            "business_type": (business_type or self.default_profile.business_type).value,
            "primary_domain": domain.value,
            "data_maturity": self.default_profile.data_maturity.value,
            "key_metrics": domain_template.get("key_metrics", []),
            "stakeholders": domain_template.get("stakeholders", []),
            "reporting_standards": domain_template.get("reporting_standards", [])
        }
        
        # 合并自定义配置
        if custom_config:
            org_context.update(custom_config)
        
        # 构建合规要求
        compliance_requirements = domain_template.get("regulatory_focus", [])
        
        # 构建绩效目标
        size_profile = self._performance_templates.get(
            company_size or self.default_profile.company_size, 
            PerformanceProfile()
        )
        performance_targets = size_profile.target_metrics.copy()
        
        return BusinessContext(
            business_type=org_context["business_type"],
            primary_domain=domain.value,
            compliance_requirements=compliance_requirements,
            performance_targets=performance_targets,
            organizational_context=org_context,
            metadata={
                "template_based": True,
                "domain": domain.value,
                "created_at": datetime.now().isoformat()
            }
        )
    
    def build_multi_domain(self, 
                          domains: List[Union[IndustryDomain, str]],
                          primary_domain: Union[IndustryDomain, str],
                          weights: Optional[Dict[str, float]] = None) -> BusinessContext:
        """
        构建多领域业务上下文
        
        Args:
            domains: 涉及的业务领域列表
            primary_domain: 主要业务领域
            weights: 各领域权重
        """
        # 标准化领域
        normalized_domains = []
        for domain in domains:
            if isinstance(domain, str):
                try:
                    domain = IndustryDomain(domain)
                except ValueError:
                    logger.warning(f"跳过未知业务领域: {domain}")
                    continue
            normalized_domains.append(domain)
        
        if isinstance(primary_domain, str):
            try:
                primary_domain = IndustryDomain(primary_domain)
            except ValueError:
                primary_domain = normalized_domains[0] if normalized_domains else IndustryDomain.OPERATIONS
        
        # 合并所有领域的配置
        merged_config = self._merge_domain_configs(normalized_domains, primary_domain, weights)
        
        return BusinessContext(
            business_type=self.default_profile.business_type.value,
            primary_domain=primary_domain.value,
            compliance_requirements=merged_config["compliance_requirements"],
            performance_targets=merged_config["performance_targets"],
            organizational_context=merged_config["organizational_context"],
            metadata={
                "multi_domain": True,
                "domains": [d.value for d in normalized_domains],
                "primary_domain": primary_domain.value,
                "weights": weights or {},
                "created_at": datetime.now().isoformat()
            }
        )
    
    def build_from_template(self, 
                           template_name: str,
                           customizations: Optional[Dict[str, Any]] = None) -> BusinessContext:
        """
        从预定义模板构建业务上下文
        
        Args:
            template_name: 模板名称
            customizations: 自定义修改
        """
        templates = {
            "startup_saas": {
                "business_type": "technology",
                "primary_domain": "product",
                "company_size": "startup",
                "key_focus": ["user_growth", "product_metrics", "funding_metrics"]
            },
            "enterprise_finance": {
                "business_type": "financial_services",
                "primary_domain": "finance", 
                "company_size": "enterprise",
                "key_focus": ["compliance", "risk_management", "profitability"]
            },
            "retail_operations": {
                "business_type": "retail",
                "primary_domain": "operations",
                "company_size": "large",
                "key_focus": ["inventory_management", "customer_satisfaction", "supply_chain"]
            },
            "manufacturing_quality": {
                "business_type": "manufacturing",
                "primary_domain": "operations",
                "company_size": "medium",
                "key_focus": ["quality_control", "efficiency", "safety"]
            }
        }
        
        template = templates.get(template_name)
        if not template:
            logger.warning(f"未找到模板: {template_name}, 使用默认配置")
            return self._create_default_business_context()
        
        # 应用自定义修改
        if customizations:
            template.update(customizations)
        
        # 构建业务上下文
        try:
            business_type = BusinessType(template["business_type"])
            primary_domain = IndustryDomain(template["primary_domain"])
            company_size = CompanySize(template["company_size"])
        except ValueError as e:
            logger.error(f"模板配置错误: {e}")
            return self._create_default_business_context()
        
        return self.build_for_domain(
            domain=primary_domain,
            company_size=company_size,
            business_type=business_type,
            custom_config={
                "template_name": template_name,
                "key_focus": template.get("key_focus", [])
            }
        )
    
    def _determine_primary_domain(self, 
                                 user_role: Optional[str], 
                                 department: Optional[str]) -> IndustryDomain:
        """确定主要业务领域"""
        # 基于用户角色推断
        if user_role:
            role_lower = user_role.lower()
            if any(keyword in role_lower for keyword in ["cfo", "finance", "财务", "会计"]):
                return IndustryDomain.FINANCE
            elif any(keyword in role_lower for keyword in ["sales", "销售", "商务"]):
                return IndustryDomain.SALES
            elif any(keyword in role_lower for keyword in ["marketing", "市场", "营销"]):
                return IndustryDomain.MARKETING
            elif any(keyword in role_lower for keyword in ["hr", "人事", "人力"]):
                return IndustryDomain.HR
            elif any(keyword in role_lower for keyword in ["cto", "技术", "开发", "it"]):
                return IndustryDomain.IT
            elif any(keyword in role_lower for keyword in ["operations", "运营", "生产"]):
                return IndustryDomain.OPERATIONS
        
        # 基于部门推断
        if department:
            dept_lower = department.lower()
            if any(keyword in dept_lower for keyword in ["finance", "财务", "会计"]):
                return IndustryDomain.FINANCE
            elif any(keyword in dept_lower for keyword in ["sales", "销售"]):
                return IndustryDomain.SALES
            elif any(keyword in dept_lower for keyword in ["marketing", "市场"]):
                return IndustryDomain.MARKETING
            elif any(keyword in dept_lower for keyword in ["hr", "人力"]):
                return IndustryDomain.HR
            elif any(keyword in dept_lower for keyword in ["it", "技术"]):
                return IndustryDomain.IT
            elif any(keyword in dept_lower for keyword in ["operations", "运营"]):
                return IndustryDomain.OPERATIONS
        
        return self.default_profile.primary_domain
    
    def _build_organizational_context(self, 
                                    company_info: Optional[Dict[str, Any]], 
                                    primary_domain: IndustryDomain) -> Dict[str, Any]:
        """构建组织上下文"""
        org_context = {
            "business_type": self.default_profile.business_type.value,
            "company_size": self.default_profile.company_size.value,
            "primary_domain": primary_domain.value,
            "data_maturity": self.default_profile.data_maturity.value,
            "regions": self.default_profile.regions,
            "languages": self.default_profile.languages
        }
        
        if company_info:
            # 映射公司信息到标准字段
            if "industry" in company_info:
                try:
                    org_context["business_type"] = BusinessType(company_info["industry"]).value
                except ValueError:
                    pass
            
            if "size" in company_info:
                try:
                    org_context["company_size"] = CompanySize(company_info["size"]).value
                except ValueError:
                    pass
            
            # 直接添加其他字段
            for key in ["company_name", "headquarters", "founded_year", "employee_count"]:
                if key in company_info:
                    org_context[key] = company_info[key]
        
        # 添加领域特定配置
        domain_template = self._domain_templates.get(primary_domain, {})
        org_context.update({
            "key_metrics": domain_template.get("key_metrics", []),
            "stakeholders": domain_template.get("stakeholders", []),
            "reporting_standards": domain_template.get("reporting_standards", []),
            "typical_periods": domain_template.get("typical_periods", ["monthly"])
        })
        
        return org_context
    
    def _build_compliance_requirements(self, 
                                     org_context: Dict[str, Any],
                                     company_info: Optional[Dict[str, Any]]) -> List[str]:
        """构建合规要求"""
        requirements = []
        
        # 基于业务类型的合规要求
        business_type = org_context.get("business_type", "general")
        compliance_template = self._compliance_templates.get(business_type, 
                                                           self._compliance_templates["general"])
        requirements.extend(compliance_template.regulations)
        
        # 基于公司规模的合规要求
        company_size = org_context.get("company_size", "medium")
        if company_size in ["large", "enterprise"]:
            requirements.extend(["sox_compliance", "external_audit"])
        
        # 基于地区的合规要求
        regions = org_context.get("regions", ["china"])
        if "eu" in regions or "europe" in regions:
            requirements.append("gdpr")
        if "us" in regions or "usa" in regions:
            requirements.append("ccpa")
        if "china" in regions:
            requirements.extend(["cybersecurity_law", "data_security_law"])
        
        # 自定义合规要求
        if company_info and "compliance" in company_info:
            requirements.extend(company_info["compliance"])
        
        return list(set(requirements))  # 去重
    
    def _build_performance_targets(self, 
                                 org_context: Dict[str, Any],
                                 primary_domain: IndustryDomain,
                                 project_context: Optional[Dict[str, Any]]) -> Dict[str, Union[int, float]]:
        """构建绩效目标"""
        company_size = CompanySize(org_context.get("company_size", "medium"))
        size_profile = self._performance_templates.get(company_size, PerformanceProfile())
        
        targets = size_profile.target_metrics.copy()
        
        # 添加领域特定目标
        domain_template = self._domain_templates.get(primary_domain, {})
        key_metrics = domain_template.get("key_metrics", [])
        
        for metric in key_metrics:
            if metric not in targets:
                # 为每个关键指标设置默认目标
                targets[metric] = self._get_default_target_for_metric(metric)
        
        # 项目特定目标
        if project_context and "targets" in project_context:
            targets.update(project_context["targets"])
        
        return targets
    
    def _get_default_target_for_metric(self, metric: str) -> Union[int, float]:
        """为指标获取默认目标值"""
        default_targets = {
            "revenue": 1000000,
            "profit_margin": 15.0,
            "customer_satisfaction": 85.0,
            "employee_satisfaction": 80.0,
            "conversion_rate": 5.0,
            "quality_score": 95.0,
            "efficiency": 85.0,
            "growth_rate": 20.0
        }
        
        return default_targets.get(metric, 100.0)
    
    def _merge_domain_configs(self, 
                            domains: List[IndustryDomain],
                            primary_domain: IndustryDomain,
                            weights: Optional[Dict[str, float]]) -> Dict[str, Any]:
        """合并多个领域的配置"""
        if not weights:
            # 主要领域权重50%，其他平均分配
            primary_weight = 0.5
            other_weight = 0.5 / (len(domains) - 1) if len(domains) > 1 else 0.0
            weights = {primary_domain.value: primary_weight}
            for domain in domains:
                if domain != primary_domain:
                    weights[domain.value] = other_weight
        
        merged = {
            "compliance_requirements": [],
            "performance_targets": {},
            "organizational_context": {
                "domains": [d.value for d in domains],
                "primary_domain": primary_domain.value,
                "domain_weights": weights
            }
        }
        
        # 合并合规要求
        for domain in domains:
            domain_template = self._domain_templates.get(domain, {})
            regulatory_focus = domain_template.get("regulatory_focus", [])
            merged["compliance_requirements"].extend(regulatory_focus)
        
        merged["compliance_requirements"] = list(set(merged["compliance_requirements"]))
        
        # 加权合并绩效目标
        for domain in domains:
            domain_template = self._domain_templates.get(domain, {})
            key_metrics = domain_template.get("key_metrics", [])
            domain_weight = weights.get(domain.value, 0.0)
            
            for metric in key_metrics:
                default_target = self._get_default_target_for_metric(metric)
                if metric in merged["performance_targets"]:
                    # 加权平均
                    current_target = merged["performance_targets"][metric]
                    merged["performance_targets"][metric] = (
                        current_target * (1 - domain_weight) + default_target * domain_weight
                    )
                else:
                    merged["performance_targets"][metric] = default_target * domain_weight
        
        return merged
    
    def _build_metadata(self, 
                       user_role: Optional[str],
                       department: Optional[str],
                       project_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """构建元数据"""
        metadata = {
            "builder_version": "1.0",
            "created_at": datetime.now().isoformat(),
            "profile_used": {
                "company_size": self.default_profile.company_size.value,
                "business_type": self.default_profile.business_type.value,
                "data_maturity": self.default_profile.data_maturity.value
            }
        }
        
        if user_role:
            metadata["user_role"] = user_role
        if department:
            metadata["department"] = department
        if project_context:
            metadata["project_context"] = project_context
        
        return metadata
    
    def _create_default_business_context(self) -> BusinessContext:
        """创建默认业务上下文"""
        return BusinessContext(
            business_type=self.default_profile.business_type.value,
            primary_domain=self.default_profile.primary_domain.value,
            compliance_requirements=["general_compliance"],
            performance_targets={"general_performance": 100.0},
            organizational_context={
                "company_size": self.default_profile.company_size.value,
                "data_maturity": self.default_profile.data_maturity.value,
                "is_default": True
            },
            metadata={
                "default_context": True,
                "created_at": datetime.now().isoformat()
            }
        )