"""
ZhipuAI GLM client for multi-agent system.
Provides a simple interface to interact with GLM models.
"""
from zhipuai import ZhipuAI
from functools import lru_cache
from config import get_settings
from typing import List, Dict, Any


@lru_cache()
def get_glm_client() -> ZhipuAI:
    """Get cached ZhipuAI client instance."""
    settings = get_settings()
    if not settings.zhipuai_api_key:
        raise ValueError("ZHIPUAI_API_KEY not set in .env file")
    return ZhipuAI(api_key=settings.zhipuai_api_key)


class GLMClient:
    """
    Wrapper for ZhipuAI GLM API.
    Provides simple methods for agent interactions.
    """
    
    def __init__(self, model: str = None, temperature: float = None):
        """
        Initialize GLM client.
        
        Args:
            model: GLM model to use (default: from settings)
            temperature: Sampling temperature (default: from settings)
        """
        self.settings = get_settings()
        self.client = get_glm_client()
        self.model = model or self.settings.glm_model
        self.temperature = temperature or self.settings.glm_temperature
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Send chat completion request to GLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
        
        Returns:
            Response content as string
        
        Example:
            messages = [
                {"role": "system", "content": "You are an HR specialist."},
                {"role": "user", "content": "Analyze this performance review..."}
            ]
            response = client.chat(messages)
        """
        response = self.client.chat.completions.create(
            model=kwargs.get('model', self.model),
            messages=messages,
            temperature=kwargs.get('temperature', self.temperature),
            max_tokens=kwargs.get('max_tokens', 2000),
            top_p=kwargs.get('top_p', 0.7),
            stream=False
        )
        return response.choices[0].message.content
    
    def chat_stream(self, messages: List[Dict[str, str]], **kwargs):
        """
        Send streaming chat completion request to GLM.
        
        Args:
            messages: List of message dicts
            **kwargs: Additional parameters
        
        Yields:
            Chunks of response content
        """
        response = self.client.chat.completions.create(
            model=kwargs.get('model', self.model),
            messages=messages,
            temperature=kwargs.get('temperature', self.temperature),
            max_tokens=kwargs.get('max_tokens', 2000),
            stream=True
        )
        
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    def structured_chat(
        self, 
        system_prompt: str, 
        user_input: str, 
        context: Dict[str, Any] = None,
        **kwargs
    ) -> str:
        """
        Simplified chat with system prompt + user input + optional context.
        
        Args:
            system_prompt: System instruction (agent persona)
            user_input: User query or task
            context: Optional dict of context data to inject
            **kwargs: Additional parameters
        
        Returns:
            Response content as string
        
        Example:
            response = client.structured_chat(
                system_prompt="You are an HR specialist analyzing performance data.",
                user_input="Should we terminate employee 1023?",
                context={"hr_records": [...], "sales_records": [...]}
            )
        """
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add context if provided
        if context:
            context_text = "\n\n**Context Data:**\n"
            for key, value in context.items():
                context_text += f"\n### {key}:\n{value}\n"
            messages.append({"role": "user", "content": context_text})
        
        # Add main user input
        messages.append({"role": "user", "content": user_input})
        
        return self.chat(messages, **kwargs)


# Example usage for agents
def example_hr_agent_usage():
    """Example of how HR agent would use GLM client."""
    client = GLMClient(model="glm-4-plus")
    
    # Prepare HR data
    hr_records = [
        {"period": "2025-Q3", "score": 2.8, "summary": "Below expectations"},
        {"period": "2025-Q4", "score": 2.1, "summary": "Declining performance"},
        {"period": "2026-Q1", "score": 2.0, "summary": "No improvement, PIP recommended"}
    ]
    
    # System prompt for HR agent
    system_prompt = """You are an HR specialist agent analyzing employee performance data.

Your task is to:
1. Analyze performance trends
2. Identify risks (legal, morale, replacement cost)
3. Provide a clear recommendation

Output format:
**Findings:**
- [Key finding 1]
- [Key finding 2]

**Risks:**
- [Risk 1]
- [Risk 2]

**Recommendation:**
[Clear, actionable recommendation]
"""
    
    # User query
    user_query = f"""Analyze this employee's performance:

Performance Reviews:
{hr_records}

Question: Should we terminate this employee for performance reasons?
"""
    
    # Get response
    response = client.structured_chat(
        system_prompt=system_prompt,
        user_input=user_query
    )
    
    return response


# Example usage for vision model (OCR)
def example_ocr_usage(image_path: str):
    """Example of how to use GLM-4V for OCR (Kai Haung's task)."""
    client = GLMClient(model="glm-4v-plus")
    
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Extract all text from this image and structure it as a performance review with: employee name, period, score, summary."
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_path  # Can be URL or base64
                    }
                }
            ]
        }
    ]
    
    response = client.chat(messages)
    return response
