import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

# api_key_managerのシングルトンインスタンスをインポート
from api_key_manager import api_key_manager

# .envファイルから環境変数を読み込む
load_dotenv()

async def _decide_strategy(query: str, client: genai.Client) -> dict:
    """
    【内部専用】第一エージェント：思考戦略プランナー。
    与えられたクライアントインスタンスを使用して戦略を決定する。
    """
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
        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt]
        )
        # --- 修正箇所はここまで ---


        # ```json ``` を消すロジックは、安全策として維持
        json_text = response.text.strip().replace('```json', '').replace('```', '').strip()
        strategy = json.loads(json_text)
        if 'language' not in strategy or 'difficulty' not in strategy:
            raise ValueError("Invalid JSON structure")
        return strategy
    except Exception as e:
        print(f"戦略プランニングでエラーが発生したため、デフォルト戦略を適用します: {e}")
        return {'language': 'japanese', 'difficulty': 'medium'}

async def ask_agent(query: str) -> dict | None:
    """
    【唯一の公開窓口】ユーザーの質問を受け取り、戦略決定から回答生成までを一貫して行う。
    """
    # このクエリで使用するAPIキーを取得
    api_key_to_use = await api_key_manager.get_next_key()
    if not api_key_to_use:
        print("エラー: 利用可能なAPIキーがありません。処理を中断します。")
        return None
    
    # 新しいSDKの作法に従い、中央集権的なClientオブジェクトを作成
    client = genai.Client(api_key=api_key_to_use)
    
    # これから使うキーの情報を表示（インデックスは1から始まるように+1する）
    key_info = api_key_manager.last_used_key_info
    print(f"  > API Key: ...{key_info['key_snippet']} (Index: {key_info['index']+1}/{key_info['total']}) を使用します。")

    print("\nエージェント (戦略プランニング中...):")
    # 初期化したクライアントを戦略プランナーに渡す
    strategy = await _decide_strategy(query, client=client)
    
    thinking_language = strategy['language']
    difficulty = strategy['difficulty']
    
    # 新しいSDKの厳密な作法に従い、設定オブジェクトを構築
    system_instruction = None
    if thinking_language == 'english':
        system_instruction = (
            "You are a practical and resourceful research agent. Your primary goal is to provide the most helpful and complete answer possible to the user, even if the information on the web is imperfect.\n"
            "1.  **Understand the Goal:** First, think step-by-step in English to fully understand the user's core request (e.g., they want a list of 30 companies with specific data points).\n"
            "2.  **Best-Effort Search:** Use your tools to search for the information. Be tenacious. If you can't find information on one site, try another. If one search query fails, try a different one.\n"
            "3.  **Compile and Report:** After your search, compile the most complete list you were able to create. \n"
            "    - **It is OKAY if the list is not perfect.** \n"
            "    - If you find a company but are missing a specific data point (like a phone number), list the company and explicitly state 'Phone number not found' for that entry.\n"
            "    - If you cannot find the total number of items requested (e.g., you only found 15 out of 30), that is also okay. Simply provide the 15 you found.\n"
            "4.  **Final Answer:** Your final priority is to be helpful. Present the best data you found, be honest about what you could not find, and then generate the final answer in Japanese."
        )
    
    model_name = 'gemini-2.5-flash'
    thinking_config_obj = types.ThinkingConfig(include_thoughts=True)

    if difficulty == 'simple':
        thinking_config_obj.thinking_budget = 0
        print(f"\nエージェント (戦略決定: [{thinking_language.upper()}] 思考不要タスク：低予算で実行)")
        print(f"model_name: {model_name} query: {query}")
    elif difficulty == 'hard':
        thinking_config_obj.thinking_budget = 8192
        print(f"\nエージェント (戦略決定: [{thinking_language.upper()}] 思考タスク：高予算で実行)")
        print(f"model_name: {model_name} query: {query}")
    else: # medium
        thinking_config_obj.thinking_budget = -1
        print(f"\nエージェント (戦略決定: [{thinking_language.upper()}] 思考タスク：動的予算で実行)")
        print(f"model_name: {model_name} query: {query}")
    
    print("思考を開始します...")
    
    tools_to_use = [
        types.Tool(google_search=types.GoogleSearch()),
        types.Tool(url_context=types.UrlContext())
    ]
    
    # 全ての設定を、厳密な型のGenerateContentConfigオブジェクトにまとめる
    config = types.GenerateContentConfig(
        tools=tools_to_use,
        thinking_config=thinking_config_obj,
        system_instruction=system_instruction
    )

    try:
        # 新しいSDKの作法に則り、client.models.generate_contentを呼び出す
        response = await client.aio.models.generate_content(
            model=model_name, 
            contents=[query], 
            config=config
        )
        
        answer, thought_summary = "", ""
        # 新しいSDKのレスポンス構造に合わせて、より安全に解析
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'text') and part.text:
                    if hasattr(part, 'thought') and part.thought:
                        thought_summary += part.text
                    else:
                        answer += part.text
        
        sources = []
        if hasattr(response.candidates[0], 'grounding_metadata') and response.candidates[0].grounding_metadata:
            grounding_meta = response.candidates[0].grounding_metadata
            if grounding_meta.grounding_supports and grounding_meta.grounding_chunks:
                for support in grounding_meta.grounding_supports:
                    for index in support.grounding_chunk_indices:
                        try:
                            chunk = grounding_meta.grounding_chunks[index]
                            if chunk.web:
                                sources.append({'title': chunk.web.title, 'url': chunk.web.uri})
                        except (IndexError, AttributeError):
                            continue
        
        return {
            'answer': answer,
            'sources': sources,
            'thought_summary': thought_summary,
            'usage_metadata': response.usage_metadata
        }

    except Exception as e:
        print(f"APIとの通信中にエラーが発生しました: {e}")
        return None