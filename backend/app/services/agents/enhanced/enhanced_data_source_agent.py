"""
Enhanced Data Source Agent

Advanced data source analysis and management through the agent system.
Provides intelligent schema analysis, query optimization, and data profiling.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from ..core_types import BaseAgent, AgentConfig, AgentResult, AgentType
from ..specialized.data_query_agent import DataQueryAgent


logger = logging.getLogger(__name__)


class DataSourceType(Enum):
    """Data source types"""
    DORIS = "doris"
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    CLICKHOUSE = "clickhouse"
    MONGODB = "mongodb"
    REDIS = "redis"
    ELASTICSEARCH = "elasticsearch"


class AnalysisMode(Enum):
    """Data source analysis modes"""
    QUICK = "quick"           # Basic schema and connection test
    STANDARD = "standard"     # Schema + sample data + basic profiling
    COMPREHENSIVE = "comprehensive"  # Full profiling + optimization recommendations
    DEEP = "deep"            # Advanced analysis + ML-based insights


@dataclass
class SchemaInfo:
    """Database schema information"""
    databases: List[str] = field(default_factory=list)
    tables: Dict[str, List[str]] = field(default_factory=dict)  # database -> tables
    columns: Dict[str, Dict[str, List[Dict]]] = field(default_factory=dict)  # db -> table -> columns
    indexes: Dict[str, Dict[str, List[str]]] = field(default_factory=dict)  # db -> table -> indexes
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    constraints: Dict[str, List[Dict]] = field(default_factory=dict)


@dataclass
class DataProfile:
    """Data profiling results"""
    table_name: str
    row_count: int = 0
    column_profiles: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    data_quality_score: float = 0.0
    data_distribution: Dict[str, Any] = field(default_factory=dict)
    anomalies: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class QueryOptimization:
    """Query optimization recommendations"""
    original_query: str
    optimized_query: str
    optimization_type: str
    expected_improvement: float
    rationale: str
    execution_plan_analysis: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataSourceAnalysisResult:
    """Comprehensive data source analysis result"""
    data_source_id: str
    data_source_type: DataSourceType
    analysis_mode: AnalysisMode
    connection_status: bool
    schema_info: Optional[SchemaInfo] = None
    data_profiles: List[DataProfile] = field(default_factory=list)
    query_optimizations: List[QueryOptimization] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    security_assessment: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    analysis_timestamp: datetime = field(default_factory=datetime.now)
    error_details: Optional[str] = None


class EnhancedDataSourceAgent(BaseAgent):
    """
    Enhanced agent for comprehensive data source analysis and optimization
    """
    
    def __init__(self, config: AgentConfig = None):
        if config is None:
            config = AgentConfig(
                agent_id="enhanced_data_source_agent",
                agent_type=AgentType.DATA_QUERY,
                name="Enhanced Data Source Agent",
                description="Advanced data source analysis, profiling, and optimization",
                timeout_seconds=300,  # 5 minutes for comprehensive analysis
                enable_caching=True,
                cache_ttl_seconds=3600  # 1 hour cache for schema info
            )
        
        super().__init__(config)
        self.data_query_agent = DataQueryAgent()
        
    async def execute(
        self,
        input_data: Any,
        context: Dict[str, Any] = None
    ) -> AgentResult:
        """
        Execute enhanced data source analysis
        
        Expected input_data format:
        {
            "data_source_id": str,
            "analysis_mode": str,  # quick, standard, comprehensive, deep
            "target_tables": List[str],  # optional, specific tables to analyze
            "query_samples": List[str],  # optional, queries to optimize
            "custom_config": Dict[str, Any]  # optional
        }
        """
        try:
            # Parse input
            data_source_id = input_data.get("data_source_id")
            analysis_mode = AnalysisMode(input_data.get("analysis_mode", "standard"))
            target_tables = input_data.get("target_tables", [])
            query_samples = input_data.get("query_samples", [])
            custom_config = input_data.get("custom_config", {})
            
            if not data_source_id:
                raise ValueError("data_source_id is required")
            
            self.logger.info(
                f"Starting enhanced data source analysis",
                agent_id=self.agent_id,
                data_source_id=data_source_id,
                analysis_mode=analysis_mode.value
            )
            
            # Get data source configuration
            data_source_config = await self._get_data_source_config(data_source_id)
            data_source_type = DataSourceType(data_source_config.get("source_type", "doris"))
            
            # Initialize analysis result
            analysis_result = DataSourceAnalysisResult(
                data_source_id=data_source_id,
                data_source_type=data_source_type,
                analysis_mode=analysis_mode,
                connection_status=False
            )
            
            # Step 1: Test connection
            connection_test = await self._test_connection(data_source_config)
            analysis_result.connection_status = connection_test.get("success", False)
            
            if not analysis_result.connection_status:
                analysis_result.error_details = connection_test.get("error", "Connection failed")
                return AgentResult(
                    success=False,
                    agent_id=self.agent_id,
                    agent_type=self.agent_type,
                    data=analysis_result,
                    error_message=f"Data source connection failed: {analysis_result.error_details}"
                )
            
            # Step 2: Analyze schema (all modes)
            schema_info = await self._analyze_schema(data_source_config, target_tables)
            analysis_result.schema_info = schema_info
            
            # Step 3: Additional analysis based on mode
            if analysis_mode in [AnalysisMode.STANDARD, AnalysisMode.COMPREHENSIVE, AnalysisMode.DEEP]:
                # Data profiling
                data_profiles = await self._profile_data(
                    data_source_config, 
                    schema_info, 
                    target_tables,
                    analysis_mode
                )
                analysis_result.data_profiles = data_profiles
            
            if analysis_mode in [AnalysisMode.COMPREHENSIVE, AnalysisMode.DEEP]:
                # Query optimization
                if query_samples:
                    optimizations = await self._optimize_queries(
                        data_source_config, 
                        query_samples
                    )
                    analysis_result.query_optimizations = optimizations
                
                # Performance analysis
                performance_metrics = await self._analyze_performance(
                    data_source_config,
                    schema_info
                )
                analysis_result.performance_metrics = performance_metrics
                
                # Security assessment
                security_assessment = await self._assess_security(
                    data_source_config,
                    schema_info
                )
                analysis_result.security_assessment = security_assessment
            
            if analysis_mode == AnalysisMode.DEEP:
                # Advanced ML-based insights
                advanced_insights = await self._generate_advanced_insights(
                    analysis_result,
                    custom_config
                )
                analysis_result.recommendations.extend(advanced_insights)
            
            # Generate general recommendations
            general_recommendations = self._generate_recommendations(analysis_result)
            analysis_result.recommendations.extend(general_recommendations)
            
            self.logger.info(
                f"Enhanced data source analysis completed",
                agent_id=self.agent_id,
                data_source_id=data_source_id,
                tables_analyzed=len(analysis_result.data_profiles),
                recommendations_count=len(analysis_result.recommendations)
            )
            
            return AgentResult(
                success=True,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                data=analysis_result,
                metadata={
                    "analysis_mode": analysis_mode.value,
                    "tables_analyzed": len(analysis_result.data_profiles),
                    "optimizations_generated": len(analysis_result.query_optimizations),
                    "recommendations_count": len(analysis_result.recommendations),
                    "data_quality_avg": sum(p.data_quality_score for p in analysis_result.data_profiles) / len(analysis_result.data_profiles) if analysis_result.data_profiles else 0
                }
            )
            
        except Exception as e:
            error_msg = f"Enhanced data source analysis failed: {str(e)}"
            self.logger.error(error_msg, agent_id=self.agent_id, exc_info=True)
            
            return AgentResult(
                success=False,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                error_message=error_msg
            )
    
    async def _get_data_source_config(self, data_source_id: str) -> Dict[str, Any]:
        """Get data source configuration from database"""
        try:
            from app.db.session import get_db_session
            from app.models.data_source import DataSource
            from uuid import UUID
            
            with get_db_session() as db:
                data_source = db.query(DataSource).filter(
                    DataSource.id == UUID(data_source_id)
                ).first()
                
                if not data_source:
                    raise ValueError(f"Data source {data_source_id} not found")
                
                return {
                    "source_type": data_source.source_type.value,
                    "doris_fe_hosts": data_source.doris_fe_hosts or [],
                    "doris_query_port": data_source.doris_query_port or 9030,
                    "doris_database": data_source.doris_database or "default",
                    "doris_username": data_source.doris_username,
                    "doris_password": data_source.doris_password,
                    "is_active": data_source.is_active
                }
        except Exception as e:
            self.logger.error(f"Failed to get data source config: {e}")
            raise
    
    async def _test_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test data source connection"""
        try:
            # Use the existing data query agent for connection test
            test_result = await self.data_query_agent.execute({
                "operation": "test_connection",
                "config": config
            })
            
            return {
                "success": test_result.success,
                "error": test_result.error_message
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _analyze_schema(
        self, 
        config: Dict[str, Any], 
        target_tables: List[str] = None
    ) -> SchemaInfo:
        """Analyze database schema structure"""
        try:
            schema_info = SchemaInfo()
            
            # Get databases
            db_query_result = await self.data_query_agent.execute({
                "operation": "execute_query",
                "query": "SHOW DATABASES",
                "config": config
            })
            
            if db_query_result.success and hasattr(db_query_result.data, 'data'):
                databases = [row[0] for row in db_query_result.data.data]
                schema_info.databases = databases
                
                # For each database, get tables and columns
                for db_name in databases:
                    if db_name in ['information_schema', 'mysql', 'performance_schema', 'sys']:
                        continue
                    
                    # Get tables
                    tables_query = f"SHOW TABLES FROM {db_name}"
                    tables_result = await self.data_query_agent.execute({
                        "operation": "execute_query",
                        "query": tables_query,
                        "config": config
                    })
                    
                    if tables_result.success and hasattr(tables_result.data, 'data'):
                        tables = [row[0] for row in tables_result.data.data]
                        
                        # Filter by target tables if specified
                        if target_tables:
                            tables = [t for t in tables if t in target_tables]
                        
                        schema_info.tables[db_name] = tables
                        schema_info.columns[db_name] = {}
                        schema_info.indexes[db_name] = {}
                        
                        # Get column info for each table
                        for table_name in tables:
                            columns_query = f"DESCRIBE {db_name}.{table_name}"
                            columns_result = await self.data_query_agent.execute({
                                "operation": "execute_query",
                                "query": columns_query,
                                "config": config
                            })
                            
                            if columns_result.success and hasattr(columns_result.data, 'data'):
                                columns_info = []
                                for row in columns_result.data.data:
                                    columns_info.append({
                                        "name": row[0],
                                        "type": row[1],
                                        "null": row[2] == "YES",
                                        "key": row[3],
                                        "default": row[4],
                                        "extra": row[5] if len(row) > 5 else None
                                    })
                                
                                schema_info.columns[db_name][table_name] = columns_info
            
            return schema_info
            
        except Exception as e:
            self.logger.error(f"Schema analysis failed: {e}")
            return SchemaInfo()
    
    async def _profile_data(
        self, 
        config: Dict[str, Any], 
        schema_info: SchemaInfo, 
        target_tables: List[str],
        analysis_mode: AnalysisMode
    ) -> List[DataProfile]:
        """Profile data in tables"""
        profiles = []
        
        try:
            for db_name, tables in schema_info.tables.items():
                for table_name in tables:
                    if target_tables and table_name not in target_tables:
                        continue
                    
                    profile = await self._profile_single_table(
                        config, db_name, table_name, 
                        schema_info.columns[db_name][table_name],
                        analysis_mode
                    )
                    profiles.append(profile)
                    
                    # Limit number of tables for quick analysis
                    if analysis_mode == AnalysisMode.QUICK and len(profiles) >= 5:
                        break
                        
        except Exception as e:
            self.logger.error(f"Data profiling failed: {e}")
        
        return profiles
    
    async def _profile_single_table(
        self, 
        config: Dict[str, Any], 
        db_name: str, 
        table_name: str, 
        columns: List[Dict],
        analysis_mode: AnalysisMode
    ) -> DataProfile:
        """Profile a single table"""
        profile = DataProfile(table_name=f"{db_name}.{table_name}")
        
        try:
            # Get row count
            count_query = f"SELECT COUNT(*) FROM {db_name}.{table_name}"
            count_result = await self.data_query_agent.execute({
                "operation": "execute_query",
                "query": count_query,
                "config": config
            })
            
            if count_result.success and hasattr(count_result.data, 'data'):
                profile.row_count = count_result.data.data[0][0]
            
            # Profile each column
            for column in columns:
                column_name = column["name"]
                column_type = column["type"]
                
                column_profile = await self._profile_column(
                    config, db_name, table_name, column_name, column_type, analysis_mode
                )
                profile.column_profiles[column_name] = column_profile
            
            # Calculate data quality score
            profile.data_quality_score = self._calculate_data_quality_score(profile)
            
            # Generate recommendations for this table
            profile.recommendations = self._generate_table_recommendations(profile, columns)
            
        except Exception as e:
            self.logger.error(f"Failed to profile table {db_name}.{table_name}: {e}")
        
        return profile
    
    async def _profile_column(
        self, 
        config: Dict[str, Any], 
        db_name: str, 
        table_name: str, 
        column_name: str, 
        column_type: str,
        analysis_mode: AnalysisMode
    ) -> Dict[str, Any]:
        """Profile a single column"""
        profile = {
            "type": column_type,
            "null_count": 0,
            "distinct_count": 0,
            "min_value": None,
            "max_value": None,
            "avg_value": None
        }
        
        try:
            full_table_name = f"{db_name}.{table_name}"
            
            # Basic stats for all modes
            if analysis_mode in [AnalysisMode.QUICK, AnalysisMode.STANDARD, AnalysisMode.COMPREHENSIVE, AnalysisMode.DEEP]:
                # Null count
                null_query = f"SELECT COUNT(*) FROM {full_table_name} WHERE {column_name} IS NULL"
                null_result = await self.data_query_agent.execute({
                    "operation": "execute_query",
                    "query": null_query,
                    "config": config
                })
                
                if null_result.success and hasattr(null_result.data, 'data'):
                    profile["null_count"] = null_result.data.data[0][0]
                
                # Distinct count
                distinct_query = f"SELECT COUNT(DISTINCT {column_name}) FROM {full_table_name}"
                distinct_result = await self.data_query_agent.execute({
                    "operation": "execute_query",
                    "query": distinct_query,
                    "config": config
                })
                
                if distinct_result.success and hasattr(distinct_result.data, 'data'):
                    profile["distinct_count"] = distinct_result.data.data[0][0]
            
            # Extended stats for standard and above
            if analysis_mode in [AnalysisMode.STANDARD, AnalysisMode.COMPREHENSIVE, AnalysisMode.DEEP]:
                # Min, Max, Avg for numeric columns
                if "int" in column_type.lower() or "float" in column_type.lower() or "double" in column_type.lower() or "decimal" in column_type.lower():
                    stats_query = f"SELECT MIN({column_name}), MAX({column_name}), AVG({column_name}) FROM {full_table_name}"
                    stats_result = await self.data_query_agent.execute({
                        "operation": "execute_query",
                        "query": stats_query,
                        "config": config
                    })
                    
                    if stats_result.success and hasattr(stats_result.data, 'data'):
                        row = stats_result.data.data[0]
                        profile["min_value"] = row[0]
                        profile["max_value"] = row[1]
                        profile["avg_value"] = row[2]
            
        except Exception as e:
            self.logger.error(f"Failed to profile column {column_name}: {e}")
        
        return profile
    
    async def _optimize_queries(
        self, 
        config: Dict[str, Any], 
        query_samples: List[str]
    ) -> List[QueryOptimization]:
        """Optimize query performance"""
        optimizations = []
        
        for query in query_samples:
            try:
                optimization = await self._optimize_single_query(config, query)
                if optimization:
                    optimizations.append(optimization)
            except Exception as e:
                self.logger.error(f"Failed to optimize query: {e}")
        
        return optimizations
    
    async def _optimize_single_query(
        self, 
        config: Dict[str, Any], 
        query: str
    ) -> Optional[QueryOptimization]:
        """Optimize a single query"""
        try:
            # Basic query optimization rules
            optimized_query = query
            optimization_type = "none"
            expected_improvement = 0.0
            rationale = ""
            
            # Rule 1: Add LIMIT if missing for SELECT queries
            if "SELECT" in query.upper() and "LIMIT" not in query.upper():
                optimized_query = query.strip()
                if not optimized_query.endswith(';'):
                    optimized_query += " LIMIT 1000"
                else:
                    optimized_query = optimized_query[:-1] + " LIMIT 1000;"
                
                optimization_type = "limit_addition"
                expected_improvement = 0.5
                rationale = "Added LIMIT to prevent large result sets"
            
            # Rule 2: Add WHERE clause suggestions for full table scans
            if "SELECT *" in query.upper() and "WHERE" not in query.upper():
                rationale += " Consider adding WHERE clause to filter results."
                expected_improvement += 0.3
            
            # Rule 3: Index usage suggestions
            if "WHERE" in query.upper():
                rationale += " Ensure indexes exist on WHERE clause columns."
                expected_improvement += 0.2
            
            if optimized_query != query or rationale:
                return QueryOptimization(
                    original_query=query,
                    optimized_query=optimized_query,
                    optimization_type=optimization_type,
                    expected_improvement=expected_improvement,
                    rationale=rationale
                )
            
        except Exception as e:
            self.logger.error(f"Query optimization failed: {e}")
        
        return None
    
    async def _analyze_performance(
        self, 
        config: Dict[str, Any], 
        schema_info: SchemaInfo
    ) -> Dict[str, Any]:
        """Analyze data source performance"""
        metrics = {
            "connection_latency_ms": 0,
            "query_execution_time_ms": 0,
            "table_sizes": {},
            "index_effectiveness": {},
            "bottlenecks": []
        }
        
        try:
            # Test query performance with a simple query
            import time
            start_time = time.time()
            
            test_result = await self.data_query_agent.execute({
                "operation": "execute_query",
                "query": "SELECT 1",
                "config": config
            })
            
            if test_result.success:
                metrics["query_execution_time_ms"] = (time.time() - start_time) * 1000
            
            # Analyze table sizes
            for db_name, tables in schema_info.tables.items():
                for table_name in tables[:5]:  # Limit to first 5 tables
                    try:
                        size_query = f"SELECT COUNT(*) FROM {db_name}.{table_name}"
                        size_result = await self.data_query_agent.execute({
                            "operation": "execute_query",
                            "query": size_query,
                            "config": config
                        })
                        
                        if size_result.success and hasattr(size_result.data, 'data'):
                            metrics["table_sizes"][f"{db_name}.{table_name}"] = size_result.data.data[0][0]
                    except:
                        pass
            
        except Exception as e:
            self.logger.error(f"Performance analysis failed: {e}")
        
        return metrics
    
    async def _assess_security(
        self, 
        config: Dict[str, Any], 
        schema_info: SchemaInfo
    ) -> Dict[str, Any]:
        """Assess data source security"""
        assessment = {
            "security_score": 0.7,  # Default moderate score
            "vulnerabilities": [],
            "recommendations": []
        }
        
        try:
            # Check for common security issues
            if not config.get("doris_password"):
                assessment["vulnerabilities"].append("No password authentication configured")
                assessment["security_score"] -= 0.2
                assessment["recommendations"].append("Configure password authentication")
            
            # Check for sensitive column names
            sensitive_patterns = ["password", "pwd", "secret", "key", "token", "ssn", "credit"]
            
            for db_name, tables in schema_info.columns.items():
                for table_name, columns in tables.items():
                    for column in columns:
                        column_name = column["name"].lower()
                        if any(pattern in column_name for pattern in sensitive_patterns):
                            assessment["vulnerabilities"].append(f"Potentially sensitive column: {db_name}.{table_name}.{column['name']}")
                            assessment["recommendations"].append(f"Review access controls for {db_name}.{table_name}.{column['name']}")
            
            # Adjust security score based on findings
            if len(assessment["vulnerabilities"]) > 0:
                assessment["security_score"] = max(0.1, assessment["security_score"] - (len(assessment["vulnerabilities"]) * 0.1))
            
        except Exception as e:
            self.logger.error(f"Security assessment failed: {e}")
        
        return assessment
    
    async def _generate_advanced_insights(
        self, 
        analysis_result: DataSourceAnalysisResult, 
        custom_config: Dict[str, Any]
    ) -> List[str]:
        """Generate advanced ML-based insights"""
        insights = []
        
        try:
            # Data distribution analysis
            for profile in analysis_result.data_profiles:
                if profile.row_count > 10000:
                    insights.append(f"Large table {profile.table_name} ({profile.row_count:,} rows) - consider partitioning")
                
                # Analyze column profiles for anomalies
                for column_name, column_profile in profile.column_profiles.items():
                    distinct_count = column_profile.get("distinct_count", 0)
                    null_count = column_profile.get("null_count", 0)
                    
                    # High cardinality detection
                    if distinct_count > profile.row_count * 0.9:
                        insights.append(f"High cardinality detected in {profile.table_name}.{column_name} - potential candidate for indexing")
                    
                    # Data quality issues
                    if null_count > profile.row_count * 0.5:
                        insights.append(f"High null rate in {profile.table_name}.{column_name} ({null_count/profile.row_count*100:.1f}%) - data quality concern")
            
            # Performance insights
            if analysis_result.performance_metrics:
                query_time = analysis_result.performance_metrics.get("query_execution_time_ms", 0)
                if query_time > 1000:
                    insights.append("High query latency detected - consider query optimization or hardware upgrades")
            
        except Exception as e:
            self.logger.error(f"Advanced insights generation failed: {e}")
        
        return insights
    
    def _calculate_data_quality_score(self, profile: DataProfile) -> float:
        """Calculate data quality score for a table"""
        try:
            if not profile.column_profiles:
                return 0.0
            
            quality_factors = []
            
            for column_name, column_profile in profile.column_profiles.items():
                null_count = column_profile.get("null_count", 0)
                distinct_count = column_profile.get("distinct_count", 0)
                
                # Null rate factor (lower is better)
                null_rate = null_count / profile.row_count if profile.row_count > 0 else 1
                null_factor = 1.0 - min(null_rate, 1.0)
                
                # Distinctness factor (higher is generally better, but depends on column type)
                distinct_factor = min(distinct_count / profile.row_count, 1.0) if profile.row_count > 0 else 0
                
                column_quality = (null_factor * 0.7) + (distinct_factor * 0.3)
                quality_factors.append(column_quality)
            
            return sum(quality_factors) / len(quality_factors) if quality_factors else 0.0
            
        except Exception as e:
            self.logger.error(f"Data quality calculation failed: {e}")
            return 0.0
    
    def _generate_table_recommendations(
        self, 
        profile: DataProfile, 
        columns: List[Dict]
    ) -> List[str]:
        """Generate recommendations for a specific table"""
        recommendations = []
        
        try:
            # Large table recommendations
            if profile.row_count > 1000000:
                recommendations.append("Consider table partitioning for better performance")
            
            # Column-specific recommendations
            for column in columns:
                column_name = column["name"]
                if column_name in profile.column_profiles:
                    column_profile = profile.column_profiles[column_name]
                    
                    # Index recommendations
                    if column_profile.get("distinct_count", 0) > profile.row_count * 0.1:
                        recommendations.append(f"Consider adding index on {column_name}")
                    
                    # Data type optimization
                    if column["type"].lower().startswith("varchar("):
                        max_length = int(column["type"].split("(")[1].split(")")[0])
                        if max_length > 1000:
                            recommendations.append(f"Review varchar length for {column_name} - consider using TEXT if needed")
            
        except Exception as e:
            self.logger.error(f"Table recommendations generation failed: {e}")
        
        return recommendations
    
    def _generate_recommendations(self, analysis_result: DataSourceAnalysisResult) -> List[str]:
        """Generate general recommendations based on analysis"""
        recommendations = []
        
        try:
            # Connection recommendations
            if not analysis_result.connection_status:
                recommendations.append("Fix connection issues before proceeding with data operations")
                return recommendations
            
            # Schema recommendations
            if analysis_result.schema_info:
                total_tables = sum(len(tables) for tables in analysis_result.schema_info.tables.values())
                if total_tables > 50:
                    recommendations.append("Large number of tables detected - consider database organization review")
            
            # Data quality recommendations
            if analysis_result.data_profiles:
                avg_quality = sum(p.data_quality_score for p in analysis_result.data_profiles) / len(analysis_result.data_profiles)
                if avg_quality < 0.6:
                    recommendations.append("Low overall data quality detected - implement data quality monitoring")
            
            # Performance recommendations
            if analysis_result.performance_metrics:
                if analysis_result.performance_metrics.get("query_execution_time_ms", 0) > 500:
                    recommendations.append("Consider query optimization and index tuning")
            
            # Security recommendations
            if analysis_result.security_assessment:
                if analysis_result.security_assessment.get("security_score", 0) < 0.7:
                    recommendations.append("Review security configuration and access controls")
            
        except Exception as e:
            self.logger.error(f"General recommendations generation failed: {e}")
        
        return recommendations


# Agent instance for use throughout the system
enhanced_data_source_agent = EnhancedDataSourceAgent()