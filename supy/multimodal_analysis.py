"""Multimodal AI analysis using GPT-5 vision capabilities."""

from __future__ import annotations

import os
import base64
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# Load environment variables from .env file
load_dotenv()

_llm_multimodal = None


def _get_multimodal_ai():
    """Lazy-load multimodal ChatOpenAI instance."""
    global _llm_multimodal
    if _llm_multimodal is None:
        try:
            # Get API key from environment
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY not found in environment variables. "
                    "Please set it in your .env file or environment."
                )
            
            # Get model from environment (default to gpt-5 for multimodal)
            model = os.getenv("OPENAI_MODEL", "gpt-5")
            
            # Create multimodal LLM instance
            is_reasoning_model = model and ('o1' in model.lower() or 'o3' in model.lower() or 'gpt-5' in model.lower())
            
            llm_kwargs = {
                'api_key': api_key,
                'model': model,
                'max_tokens': 4000,
            }
            
            # Only add temperature for non-reasoning models
            if not is_reasoning_model:
                llm_kwargs['temperature'] = 0.1
            
            # For reasoning models, add reasoning_effort
            if is_reasoning_model:
                llm_kwargs['model_kwargs'] = {
                    'reasoning_effort': 'high'
                }
            
            print(f"[supy] Initializing multimodal ChatOpenAI with model={model}")
            _llm_multimodal = ChatOpenAI(**llm_kwargs)
            
        except ImportError as e:
            raise RuntimeError(
                "LangChain OpenAI not available. Install with:\n"
                "  pip install langchain-openai"
            ) from e
    
    return _llm_multimodal


def analyze_image_with_ai(image_path: Path) -> Path:
    """
    Send image directly to GPT-5 for multimodal analysis and save response.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Path to the saved AI response file (.response.txt)
    """
    image_path = Path(image_path)
    
    # Read and encode the image
    try:
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
        
        # Encode to base64
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        # Determine image format
        suffix = image_path.suffix.lower()
        if suffix in ['.jpg', '.jpeg']:
            mime_type = 'image/jpeg'
        elif suffix == '.png':
            mime_type = 'image/png'
        elif suffix == '.gif':
            mime_type = 'image/gif'
        else:
            mime_type = 'image/jpeg'  # Default fallback
            
    except Exception as e:
        raise RuntimeError(f"Failed to read image from {image_path}: {e}")
    
    # Get the prompt template from environment
    prompt_template = os.getenv(
        "AI_PROMPT", 
        "You will be given a single question (either multiple-choice or numeric). Follow these rules exactly.\n\n"
        "1) Multiple-choice (single-correct):\n"
        "   - Options may or may not be labeled A/B/C/D. If unlabeled, assume order A, B, C, D, ...\n"
        "   - Provide concise reasoning.\n"
        "   - Output exactly one line: <answer>X</answer> where X is the chosen option letter.\n\n"
        "2) Numeric questions:\n"
        "   - Show brief step-by-step arithmetic.\n"
        "   - Output exactly one line: <answer>final numeric value</answer>.\n\n"
        "3) Type tag (must output exactly one line):\n"
        "   - Output <type>X</type> where X is MCQ for single-correct MCQs, NUM for numeric, and OTHER for any other type (e.g., multiple-correct, programming, matching).\n"
        "   - Ensure the <answer> tag format matches the determined type.\n\n"
        "4) General:\n"
        "   - Do not ask clarifying questions; if info is missing, state a one-line assumption and proceed.\n"
        "   - Keep reasoning succinct.\n"
        "   - Do not include any extra text before or after the reasoning, <type>, and <answer> lines.\n"
        "   - Use plain text only (no Markdown or emojis)."
    )
    
    # Create multimodal message with image and text
    message_content = [
        {
            "type": "text",
            "text": prompt_template
        },
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{base64_image}",
                "detail": "high"  # Use high detail for better accuracy
            }
        }
    ]
    
    # Save the prompt for debugging
    prompt_path = image_path.with_suffix('.prompt.txt')
    try:
        prompt_content = f"{prompt_template}\n\n[IMAGE: {image_path.name}]"
        prompt_path.write_text(prompt_content, encoding='utf-8')
    except Exception:
        pass  # Non-fatal
    
    print(f"[supy] Sending image to multimodal AI: {image_path.name}")
    print("[supy] ---- Multimodal prompt (begin) ----")
    print(prompt_template)
    print(f"[IMAGE: {image_path.name} - {mime_type}]")
    print("[supy] ---- Multimodal prompt (end) ----")
    
    # Send to multimodal AI with retries
    llm = _get_multimodal_ai()
    last_error = None
    response_text = ""
    
    for attempt in range(3):
        try:
            print(f"[supy] Multimodal attempt {attempt + 1}/3...")
            
            # Create HumanMessage with multimodal content
            message = HumanMessage(content=message_content)
            response = llm.invoke([message])
            
            response_text = response.content if hasattr(response, 'content') else str(response)
            print(f"[supy] Received multimodal response length: {len(response_text)} chars")
            
            if response_text and response_text.strip():
                print(f"[supy] ✓ Got valid multimodal response on attempt {attempt + 1}")
                break
            else:
                print(f"[supy] ✗ Empty multimodal response on attempt {attempt + 1}")
                
        except Exception as e:
            last_error = e
            print(f"[supy] ✗ Multimodal error on attempt {attempt + 1}: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
        
        # Backoff before retrying (skip sleep after last attempt)
        if attempt < 2:
            import time
            sleep_time = 0.6 * (2 ** attempt)
            print(f"[supy] Waiting {sleep_time}s before retry...")
            time.sleep(sleep_time)
    
    if not response_text or not response_text.strip():
        # Provide a diagnostic message rather than an empty file
        diag = "No response returned by the multimodal model after retries."
        if last_error is not None:
            diag += f" Last error: {last_error}"
        response_text = (
            "Reasoning\n" + diag + "\n"
            "<type>OTHER</type>\n"
            "<answer>Could not determine</answer>"
        )
    
    # Print raw response for debugging
    print("[supy] ---- Multimodal AI raw response (begin) ----")
    try:
        print(response_text)
    except Exception:
        print("[supy] (Could not print multimodal response)")
    print("[supy] ---- Multimodal AI raw response (end) ----")
    
    # Save response with same timestamp as original image
    response_path = image_path.with_suffix('.response.txt')
    
    try:
        response_path.write_text(response_text.strip(), encoding='utf-8')
    except Exception as e:
        raise RuntimeError(f"Failed to save multimodal AI response to {response_path}: {e}")
    
    return response_path
