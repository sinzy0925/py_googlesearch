# gemini_agent.py (URLコンテキストツールを搭載した、最終進化版)

from google import genai
from google.genai import types
import os
import json
from dotenv import load_dotenv

load_dotenv() 

try:
    client = genai.Client()
except Exception as e:
    client = None
    print(f"エージェント初期化エラー: APIキーの設定に失敗しました。: {e}")

def _decide_strategy(query: str) -> dict:
    """
    【内部専用】第一エージェント：思考戦略プランナー。
    """
    if not client:
        return {'language': 'japanese', 'difficulty': 'medium'}

    prompt = f"""
    You are a highly intelligent and meticulous strategic query analyzer. Your role is to determine the optimal strategy for a subordinate AI agent. You must follow the rules and examples provided below with extreme precision. Your final output must be a single, valid JSON object and nothing else.

    **## Instructions ##**
    1.  **Analyze the User Query:** Carefully read and understand the user's query.
    2.  **Chain of Thought (CoT):** Internally, reason step-by-step to determine the optimal strategy. First, determine the 'language'. Second, determine the 'difficulty'. Your reasoning process itself should not be in the final output.
    3.  **Determine 'language':**
        *   **Rule:** The thinking language must be 'english' for all topics that are universal, abstract, technical, or international (e.g., finance, science, programming, business, art).
        *   **Exception:** Only choose 'japanese' if the query is **unambiguously and exclusively Japan-specific**, meaning that searching in Japanese would yield significantly better results. This includes specific Japanese locations (e.g., "渋谷の天気"), domestic laws, or purely local cultural events. "Japanese anime" is considered an international topic.
    4.  **Determine 'difficulty':**
        *   **'simple':** For fact-checking or simple retrieval questions. `thinking_budget` will be `0`.
        *   **'medium':** For queries that require explanation, comparison, or summarization. `thinking_budget` will be `-1` (dynamic).
        *   **'hard':** For queries that demand deep reasoning, multi-step logic, creative synthesis, or complex analysis. `thinking_budget` will be high.
    5.  **Output JSON:** Based on your reasoning, construct the final JSON object.

    **## Examples (Few-Shot Learning) ##**
    **Example 1:**
    *   **User Query:** "日本の現在の首相は誰ですか？"
    *   **Your JSON Output:** {{"language": "japanese", "difficulty": "simple"}}
    **Example 2:**
    *   **User Query:** "Pythonの非同期処理について"
    *   **Your JSON Output:** {{"language": "english", "difficulty": "medium"}}
    **Example 3:**
    *   **User Query:** "米国ETFについて、利回りが良い順番に30個教えて"
    *   **Your JSON Output:** {{"language": "english", "difficulty": "hard"}}

    **## Your Task ##**
    **User Query:** "{query}"
    **Your JSON Output:**
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        json_text = response.text.strip().replace('```json', '').replace('```', '').strip()
        strategy = json.loads(json_text)
        if 'language' not in strategy or 'difficulty' not in strategy:
            raise ValueError("Invalid JSON structure")
        return strategy
    except Exception as e:
        print(f"戦略プランニングでエラーが発生したため、デフォルト戦略を適用します: {e}")
        return {'language': 'japanese', 'difficulty': 'medium'}

def ask_agent(query: str) -> dict | None:
    """
    【唯一の公開窓口】ユーザーの質問を受け取り、戦略決定から回答生成までを一貫して行う。
    """
    if not client:
        print("エージェントが初期化されていません。")
        return None

    print("\nエージェント (戦略プランニング中...):")
    strategy = _decide_strategy(query)
    
    thinking_language = strategy['language']
    difficulty = strategy['difficulty']
    
    system_instruction = None
    thinking_config = {'include_thoughts': True}

    if thinking_language == 'english':
        system_instruction = (
            "You are a meticulous and tenacious research agent. Your primary goal is to fully satisfy the user's request with the highest possible quality. Follow this multi-step process rigorously:\n"
            "1.  **Initial Search & Compilation (Internal Thought):** First, think step-by-step in English to find as much information as possible. If the user asks for a list of a specific number of items (e.g., 30 stocks) with specific data points (e.g., dividend yields), your initial goal is to compile a raw list that meets the criteria.\n"
            "2.  **Self-Correction and Refinement (Internal Thought):** Second, critically review your compiled list against the user's original request. Ask yourself: 'Does every single item in my list have the required data (e.g., a specific dividend yield)?' and 'Have I met the required number of items?'\n"
            "3.  **Iterative Search (Internal Thought):** If your list is incomplete (missing data points or not enough items), YOU MUST GO BACK and perform additional, more specific search queries to fill in the gaps. For example, search for '[Stock Ticker] dividend yield'. Do not give up easily. Repeat this until your list is as complete as humanly possible.\n"
            "4.  **Final Answer Generation:** Finally, based on your complete and refined list, generate the final answer in Japanese. If, and only if, after multiple exhaustive search iterations, you still cannot fully complete the list, you must explicitly state how many you found and explain the rigorous steps you took to try to find the rest."
        )
    
    if difficulty == 'simple':
        thinking_config['thinking_budget'] = 0
        print(f"エージェント (戦略決定: [{thinking_language.upper()}] 思考不要タスク：低予算で実行)")
    elif difficulty == 'hard':
        thinking_config['thinking_budget'] = 8192
        print(f"エージェント (戦略決定: [{thinking_language.upper()}] 思考タスク：高予算で実行)")
    else: # medium
        thinking_config['thinking_budget'] = -1
        print(f"エージェント (戦略決定: [{thinking_language.upper()}] 思考タスク：動的予算で実行)")
    
    print("思考を開始します...")
    
    # --- ここからが修正箇所 ---
    # エージェントに渡す道具箱に、2つのツールを入れる
    tools_to_use = [
        types.Tool(google_search=types.GoogleSearch()),
        types.Tool(url_context=types.UrlContext()) # URLコンテキストツールを追加
    ]
    
    config_dict = {'tools': tools_to_use, 'thinking_config': types.ThinkingConfig(**thinking_config)}
    if system_instruction:
        config_dict['system_instruction'] = system_instruction
    
    config = types.GenerateContentConfig(**config_dict)
    model_name = 'gemini-2.5-flash' 

    try:
        response = client.models.generate_content(model=model_name, contents=query, config=config)
        
        answer, thought_summary = "", ""
        for part in response.candidates[0].content.parts:
            if not part.text: continue
            if hasattr(part, 'thought') and part.thought: thought_summary += part.text
            else: answer += part.text
        
        sources = []
        if hasattr(response.candidates[0], 'grounding_metadata') and response.candidates[0].grounding_metadata.grounding_supports:
            for support in response.candidates[0].grounding_metadata.grounding_supports:
                for index in support.grounding_chunk_indices:
                    try:
                        chunk = response.candidates[0].grounding_metadata.grounding_chunks[index]
                        sources.append({'title': chunk.web.title, 'url': chunk.web.uri})
                    except (IndexError, AttributeError): continue
        
        return {'answer': answer, 'sources': sources, 'thought_summary': thought_summary}

    except Exception as e:
        print(f"APIとの通信中にエラーが発生しました: {e}")
        return None