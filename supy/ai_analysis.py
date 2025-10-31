"""AI analysis module using LangChain + OpenAI to process OCR text."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
import time

# Load environment variables from .env file
load_dotenv()

_llm_chain = None


def _get_ai_chain():
    """Lazy-load LangChain + OpenAI chain."""
    global _llm_chain
    if _llm_chain is None:
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import HumanMessage
            
            # Get API key from environment
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY not found in environment variables. "
                    "Please set it in your .env file or environment."
                )
            
            # Get model and prompt from environment (with defaults)
            model = os.getenv("OPENAI_MODEL", "gpt-5")
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
            
            # Create LLM instance with proper parameters for gpt-5/reasoning models
            # GPT-5 and o1/o3 models don't support temperature parameter
            is_reasoning_model = model and ('o1' in model.lower() or 'o3' in model.lower() or 'gpt-5' in model.lower())
            
            llm_kwargs = {
                'api_key': api_key,
                'model': model,
                'max_tokens': 4000,  # Higher for reasoning models
            }
            
            # Only add temperature for non-reasoning models
            if not is_reasoning_model:
                llm_kwargs['temperature'] = 0.9
            
            # For reasoning models, pass reasoning_effort directly in model_kwargs
            if is_reasoning_model:
                llm_kwargs['model_kwargs'] = {
                    'reasoning_effort': 'high'  # high for best accuracy
                }
            
            print(f"[supy] Initializing ChatOpenAI with model={model}, is_reasoning_model={is_reasoning_model}")
            llm = ChatOpenAI(**llm_kwargs)
            
            # Store both LLM and prompt template
            _llm_chain = {
                'llm': llm,
                'prompt_template': prompt_template,
                'model': model
            }
            
        except ImportError as e:
            raise RuntimeError(
                "LangChain or OpenAI not available. Install with:\n"
                "  pip install langchain openai python-dotenv"
            ) from e
    
    return _llm_chain


def analyze_text_with_ai(text_path: Path) -> Path:
    """
    Send OCR text to OpenAI via LangChain and save response.
    
    Args:
        text_path: Path to the .txt file containing OCR results
        
    Returns:
        Path to the saved AI response file (.response.txt)
    """
    text_path = Path(text_path)
    
    # Read the OCR text
    try:
        ocr_text = text_path.read_text(encoding='utf-8').strip()
    except Exception as e:
        raise RuntimeError(f"Failed to read OCR text from {text_path}: {e}")
    
    if not ocr_text:
        # Handle empty OCR results
        response_text = "No text was detected in the image."
    else:
        # Get AI chain and process text
        try:
            chain_data = _get_ai_chain()
            llm = chain_data['llm']
            prompt_template = chain_data['prompt_template']
            model = chain_data.get('model', 'unknown-model')
            
            # Create the full prompt (also saved to file for debugging)
            # We'll send messages as [SystemMessage(prompt rules), HumanMessage(OCR text)]
            # but still keep a concatenated copy for file logging.
            # Cap OCR text length to avoid overly long prompts.
            max_ocr_chars = 12000
            ocr_text_capped = ocr_text[:max_ocr_chars]
            full_prompt = f"{prompt_template}\n\n{ocr_text_capped}"
            
            # Save prompt alongside and print to console for debugging
            prompt_path = text_path.with_suffix('.prompt.txt')
            try:
                prompt_path.write_text(full_prompt, encoding='utf-8')
            except Exception:
                # Non-fatal if prompt can't be written
                pass
            print(f"[supy] AI model: {model}")
            print("[supy] ---- Full prompt sent to OpenAI (begin) ----")
            try:
                # Avoid flooding terminal with extremely long text
                preview = full_prompt if len(full_prompt) < 20000 else full_prompt[:20000] + "\n...[truncated]"
                print(preview)
            except Exception:
                print("[supy] (Could not print prompt preview)")
            print("[supy] ---- Full prompt sent to OpenAI (end) ----")
            
            # Send to ChatOpenAI with retries and proper chat roles
            messages = [
                SystemMessage(content=prompt_template),
                HumanMessage(content=ocr_text_capped),
            ]

            last_error = None
            response_text = ""
            for attempt in range(3):
                try:
                    print(f"[supy] Attempt {attempt + 1}/3 calling OpenAI API...")
                    response = llm.invoke(messages)
                    response_text = response.content if hasattr(response, 'content') else str(response)
                    print(f"[supy] Received response length: {len(response_text)} chars")
                    if response_text and response_text.strip():
                        print(f"[supy] ✓ Got valid response on attempt {attempt + 1}")
                        break
                    else:
                        print(f"[supy] ✗ Empty response on attempt {attempt + 1}")
                except Exception as e:
                    last_error = e
                    print(f"[supy] ✗ Error on attempt {attempt + 1}: {type(e).__name__}: {e}")
                    import traceback
                    traceback.print_exc()
                # Backoff before retrying (skip sleep after last attempt)
                if attempt < 2:
                    sleep_time = 0.6 * (2 ** attempt)
                    print(f"[supy] Waiting {sleep_time}s before retry...")
                    time.sleep(sleep_time)
            
            if not response_text or not response_text.strip():
                # Provide a diagnostic message rather than an empty file
                diag = "No response returned by the model after retries."
                if last_error is not None:
                    diag += f" Last error: {last_error}"
                response_text = (
                    "Reasoning\n" + diag + "\n"
                    "<type>OTHER</type>\n"
                    "<answer>Could not determine</answer>"
                )
            
            # Print raw response for debugging
            print("[supy] ---- AI raw response (begin) ----")
            try:
                print(response_text)
            except Exception:
                print("[supy] (Could not print response)")
            print("[supy] ---- AI raw response (end) ----")
        except Exception as e:
            raise RuntimeError(f"AI analysis failed: {e}")
    
    # Save response with same timestamp as original files
    # Convert from .txt to .response.txt
    response_path = text_path.with_suffix('.response.txt')
    
    try:
        response_path.write_text(response_text.strip(), encoding='utf-8')
    except Exception as e:
        raise RuntimeError(f"Failed to save AI response to {response_path}: {e}")
    
    return response_path
