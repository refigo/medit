"""
LLM 서비스 팩토리 클래스
환경 설정에 따라 적절한 LLM 서비스 구현체를 제공합니다.
"""
from typing import Dict, Any, Optional, Type

from app.llm.base import LLMService
from app.llm.openai_service import OpenAIService
from app.llm.bedrock_service import BedrockService


class LLMServiceFactory:
    """LLM 서비스 팩토리 클래스"""
    
    # 지원하는 LLM 서비스 매핑
    _services = {
        "openai": OpenAIService,
        "bedrock": BedrockService,
    }
    
    @classmethod
    def create(cls, provider: str, config: Optional[Dict[str, Any]] = None) -> LLMService:
        """
        지정된 제공자 및 구성으로 LLM 서비스 인스턴스를 생성합니다.
        
        Args:
            provider: 사용할 LLM 서비스 제공자 ('openai', 'bedrock' 등)
            config: 서비스 구성 매개변수
            
        Returns:
            LLMService 구현체 인스턴스
            
        Raises:
            ValueError: 지원되지 않는 LLM 서비스 제공자가 지정된 경우
        """
        config = config or {}
        
        # 제공자 이름 정규화 (소문자로 변환)
        provider = provider.lower()
        
        if provider not in cls._services:
            raise ValueError(f"지원되지 않는 LLM 서비스 제공자: {provider}")
        
        # 해당 서비스 클래스 가져오기
        service_class = cls._services[provider]
        
        # 서비스 인스턴스 생성 및 반환
        return service_class(**config)
