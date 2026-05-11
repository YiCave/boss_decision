"""
Zhipu AI Client - OpenAI-compatible wrapper for Zhipu API
"""
import os
from typing import List, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class ZhipuClient:
    """Client for Zhipu AI API (OpenAI-compatible)"""
    
    def __init__(self):
        self.api_key = os.getenv("ZHIPU_API_KEY")
        self.base_url = os.getenv("ZHIPU_BASE_URL", "https://api.ilmu.ai/v1")
        self.model = os.getenv("ZHIPU_MODEL", "nemo-super")
        
        if not self.api_key:
            raise ValueError("ZHIPU_API_KEY not found in environment variables")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Send chat completion request to Zhipu API
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            response_format: Optional format specification (e.g., {"type": "json_object"})
        
        Returns:
            Response content as string
        """
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            }
            
            if max_tokens:
                kwargs["max_tokens"] = max_tokens
            
            if response_format:
                kwargs["response_format"] = response_format
            
            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        
        except Exception as e:
            raise Exception(f"Zhipu API error: {str(e)}")
    
    def generate_sql(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3
    ) -> str:
        """
        Generate SQL commands using Zhipu AI
        Lower temperature for more deterministic SQL generation
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        return self.chat(messages, temperature=temperature)


# Singleton instance
_client = None

def get_zhipu_client() -> ZhipuClient:
    """Get or create Zhipu client instance"""
    global _client
    if _client is None:
        _client = ZhipuClient()
    return _client
