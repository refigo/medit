"""
OpenAI LLM 서비스 구현
"""
import os
from typing import List, Dict, Any, Optional
import json
from openai import AsyncOpenAI

from app.llm.base import LLMService


class OpenAIService(LLMService):
    """OpenAI API를 사용하는 LLM 서비스 구현"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        """
        OpenAI 서비스 초기화
        
        Args:
            api_key: OpenAI API 키 (없으면 환경 변수에서 가져옴)
            model: 사용할 OpenAI 모델 (기본값: gpt-4o)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API 키가 필요합니다. 'OPENAI_API_KEY' 환경 변수를 설정하거나 초기화 시 제공하세요.")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = model
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """
        주어진 프롬프트를 기반으로 텍스트를 생성합니다.
        
        Args:
            prompt: 텍스트 생성을 위한 프롬프트
            **kwargs: 추가 매개변수 (temperature, max_tokens 등)
            
        Returns:
            생성된 텍스트
        """
        # OpenAI API의 채팅 엔드포인트를 사용하여 텍스트 생성
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 1000)
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content.strip()
    
    async def generate_chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        채팅 형식의 메시지를 기반으로 응답을 생성합니다.
        
        Args:
            messages: 채팅 메시지 목록 (역할과 내용 포함)
            **kwargs: 추가 매개변수 (temperature, max_tokens 등)
            
        Returns:
            생성된 응답 텍스트
        """
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 1000)
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        print(f"OpenAI 응답: {response}")
        
        return response.choices[0].message.content.strip()
    
    async def analyze_text(self, text: str, task: str, **kwargs) -> Dict[str, Any]:
        """
        텍스트를 분석하고 결과를 반환합니다.
        
        Args:
            text: 분석할 텍스트
            task: 분석 작업 유형 (예: 'medical_analysis', 'symptoms_detection')
            **kwargs: 추가 매개변수
            
        Returns:
            분석 결과를 담은 사전
        """
        system_instruction = ""
        if task == "medical_analysis":
            system_instruction = """
            당신은 의료 텍스트 분석 전문가입니다. 제공된 대화에서 언급된 증상, 
            가능성 있는 질병, 그리고 적절한 건강 제안을 JSON 형식으로 반환하세요.
            반환 형식:
            {
                "symptoms": ["증상1", "증상2", ...],
                "possible_diseases": [{"name": "질병명", "probability": 확률}, ...],
                "health_suggestions": ["제안1", "제안2", ...]
            }
            """
        elif task == "symptoms_detection":
            system_instruction = """
            당신은 의료 증상 감지 전문가입니다. 제공된 텍스트에서 언급된 모든 건강 관련 증상을 
            찾아 JSON 형식의 배열로 반환하세요.
            반환 형식:
            ["증상1", "증상2", ...]
            """
        else:
            system_instruction = f"당신은 텍스트 분석 전문가입니다. '{task}' 유형의 분석을 수행하세요."
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        
        result = response.choices[0].message.content.strip()
        
        try:
            # JSON 문자열을 Python 객체로 변환
            return json.loads(result)
        except json.JSONDecodeError:
            # JSON 파싱 오류 발생 시 원본 텍스트 반환
            return {"error": "JSON 파싱 오류", "raw_response": result}
    
    def get_provider_name(self) -> str:
        """
        사용 중인 LLM 서비스 제공자의 이름을 반환합니다.
        
        Returns:
            'openai'
        """
        return "openai"
