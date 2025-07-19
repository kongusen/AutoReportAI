from app.services.ai_integration import AIService
from app.services.data_retrieval_service import DataRetrievalService
from app.services.statistics_service import StatisticsService

ai_service = AIService()
data_retrieval_service = DataRetrievalService()
statistics_service = StatisticsService()


def get_ai_service() -> AIService:
    return ai_service


def get_data_retrieval_service() -> DataRetrievalService:
    return data_retrieval_service


def get_statistics_service() -> StatisticsService:
    return statistics_service
