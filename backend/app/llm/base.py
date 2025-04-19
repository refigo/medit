"""
LLM 서비스의 기본 클래스를 정의합니다.
다양한 LLM 서비스 제공자(OpenAI, AWS Bedrock 등)는 이 기본 클래스를 상속받아 구현됩니다.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class LLMService(ABC):
    """LLM 서비스의 기본 추상 클래스"""
    
    @abstractmethod
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """
        주어진 프롬프트를 기반으로 텍스트를 생성합니다.
        
        Args:
            prompt: 텍스트 생성을 위한 프롬프트
            **kwargs: 추가 매개변수
            
        Returns:
            생성된 텍스트
        """
        pass
    
    @abstractmethod
    async def generate_chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        채팅 형식의 메시지를 기반으로 응답을 생성합니다.
        
        Args:
            messages: 채팅 메시지 목록 (역할과 내용 포함)
            **kwargs: 추가 매개변수
            
        Returns:
            생성된 응답 텍스트
        """
        pass
    
    @abstractmethod
    async def analyze_text(self, text: str, task: str, **kwargs) -> Dict[str, Any]:
        """
        텍스트를 분석하고 결과를 반환합니다.
        
        Args:
            text: 분석할 텍스트
            task: 분석 작업 유형 (예: 'sentiment', 'entities', 'classification')
            **kwargs: 추가 매개변수
            
        Returns:
            분석 결과를 담은 사전
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """
        사용 중인 LLM 서비스 제공자의 이름을 반환합니다.
        
        Returns:
            서비스 제공자 이름 (예: 'openai', 'bedrock')
        """
        pass
