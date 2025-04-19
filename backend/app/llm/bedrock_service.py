"""
AWS Bedrock LLM 서비스 구현
"""
import os
import json
import boto3
from typing import List, Dict, Any, Optional

from app.llm.base import LLMService


class BedrockService(LLMService):
    """AWS Bedrock API를 사용하는 LLM 서비스 구현"""
    
    def __init__(self, 
                 aws_access_key_id: Optional[str] = None,
                 aws_secret_access_key: Optional[str] = None,
                 region_name: Optional[str] = None,
                 model_id: str = "anthropic.claude-3-opus-20240229-v1:0"):
        """
        AWS Bedrock 서비스 초기화
        
        Args:
            aws_access_key_id: AWS 액세스 키 ID (없으면 환경 변수에서 가져옴)
            aws_secret_access_key: AWS 시크릿 액세스 키 (없으면 환경 변수에서 가져옴)
            region_name: AWS 리전 (없으면 환경 변수에서 가져옴)
            model_id: 사용할 모델 ID (기본값: Claude 3 Opus)
        """
        self.aws_access_key_id = aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        self.region_name = region_name or os.getenv("AWS_REGION", "us-east-1")
        
        if not self.aws_access_key_id or not self.aws_secret_access_key:
            raise ValueError("AWS 인증 정보가 필요합니다. 환경 변수를 설정하거나 초기화 시 제공하세요.")
        
        self.model_id = model_id
        self.provider = model_id.split('.')[0]  # anthropic, amazon, ai21 등
        
        self.client = boto3.client(
            service_name='bedrock-runtime',
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.region_name
        )
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """
        주어진 프롬프트를 기반으로 텍스트를 생성합니다.
        
        Args:
            prompt: 텍스트 생성을 위한 프롬프트
            **kwargs: 추가 매개변수 (temperature, max_tokens 등)
            
        Returns:
            생성된 텍스트
        """
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 1000)
        
        # 모델 제공자에 따라 요청 형식 조정
        if self.provider == "anthropic":
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
        else:
            # 다른 모델에 대한 요청 형식 추가 가능
            raise ValueError(f"지원되지 않는 모델 제공자: {self.provider}")
        
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response.get('body').read())
        
        if self.provider == "anthropic":
            return response_body['content'][0]['text']
        else:
            # 다른 모델의 응답 처리 추가 가능
            return str(response_body)
    
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
        
        # 모델 제공자에 따라 요청 형식 조정
        if self.provider == "anthropic":
            # Anthropic 모델은 messages 형식 지원
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages
            }
        else:
            # 다른 모델에 대한 요청 형식 추가 가능
            raise ValueError(f"지원되지 않는 모델 제공자: {self.provider}")
        
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response.get('body').read())
        
        if self.provider == "anthropic":
            return response_body['content'][0]['text']
        else:
            # 다른 모델의 응답 처리 추가 가능
            return str(response_body)
    
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
        
        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": text + "\n\n결과를 JSON 형식으로 반환해주세요."}
        ]
        
        if self.provider == "anthropic":
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "temperature": 0.2,
                "messages": messages
            }
        else:
            # 다른 모델에 대한 요청 형식 추가 가능
            raise ValueError(f"지원되지 않는 모델 제공자: {self.provider}")
        
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response.get('body').read())
        
        if self.provider == "anthropic":
            result = response_body['content'][0]['text']
        else:
            # 다른 모델의 응답 처리 추가 가능
            result = str(response_body)
            
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
            'bedrock'
        """
        return "bedrock"
