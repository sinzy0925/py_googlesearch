from gemini_agent import ask_agent
import argparse
import time
import asyncio
import os
import json
import logging
from datetime import datetime
import aiohttp

def setup_logger(timestamp: str) -> tuple[logging.Logger, str]:
    """ログファイルを設定し、ロガーとベースファイル名を返す"""
    log_dir = "log"
    os.makedirs(log_dir, exist_ok=True)
    base_filename = os.path.join(log_dir, timestamp)
    json_log_filename = f"{base_filename}.json"

    logger = logging.getLogger('GeminiAgentLogger')
    logger.setLevel(logging.INFO)
    if logger.hasHandlers():
        logger.handlers.clear()

    file_handler = logging.FileHandler(json_log_filename, encoding='utf-8')
    file_formatter = logging.Formatter('%(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger, base_filename

def generate_markdown_report(log_summary: dict, base_filename: str):
    """
    実行結果のサマリーから、人間可読なMarkdownレポートを生成する。
    トークン使用量の詳細も含まれる。
    """
    md_filename = f"{base_filename}.md"
    
    try:
        with open(md_filename, 'w', encoding='utf-8') as f:
            summary = log_summary["execution_summary"]
            f.write(f"# Gemini Agent Batch Report\n\n")
            f.write(f"**Execution Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Total Queries:** {summary['total_queries']}\n")
            f.write(f"**Total Duration:** {summary['total_duration_seconds']:.2f} seconds\n\n")
            f.write("---\n\n")

            for result in log_summary["results"]:
                f.write(f"## Query {result['query_number']}: `{result['query']}`\n\n")
                f.write(f"**Status:** `{result['status']}`\n\n")

                if result['status'] == 'SUCCESS':
                    data = result['data']
                    if data.get('thought_summary'):
                        f.write(f"### Thought Summary\n\n")
                        thought_text = data['thought_summary'].strip()
                        f.write(f"> {thought_text.replace('\n', '\n> ')}\n\n")
                    
                    if data.get('answer'):
                        f.write(f"### Answer\n\n")
                        # CSVデータの場合、コードブロックとして整形する
                        answer_text = data['answer'].strip()
                        if "```csv" in answer_text or "会社名,電話番号,住所" in answer_text or "名前,電話番号,住所" in answer_text:
                            # 既存のコードブロックマーカーを削除してから囲む
                            cleaned_answer = answer_text.replace("```csv", "").replace("```", "").strip()
                            f.write(f"```csv\n{cleaned_answer}\n```\n\n")
                        else:
                            formatted_answer = answer_text.replace('\n', '  \n')
                            f.write(f"{formatted_answer}\n\n")

                    if data.get('sources'):
                        f.write(f"### Sources\n\n")
                        unique_sources_in_md = []
                        seen_urls_in_md = set()
                        for source in data.get('sources', []):
                             if source.get('url') not in seen_urls_in_md:
                                unique_sources_in_md.append(source)
                                seen_urls_in_md.add(source.get('url'))
                        
                        for source in unique_sources_in_md:
                            title = source.get('title', 'N/A')
                            url = source.get('url', '#')
                            f.write(f"- **{title}**: <{url}>\n")
                        f.write("\n")
                    
                    # トークン使用量のセクションを追加
                    if data.get('usage_metadata'):
                        usage = data['usage_metadata']
                        f.write(f"### Token Usage\n\n")
                        f.write(f"- **Input (Prompt):** {usage.get('prompt_token_count', 'N/A')} tokens\n")
                        f.write(f"- **Output (Thought + Answer):** {usage.get('candidates_token_count', 'N/A')} tokens\n")
                        f.write(f"- **Tool Response (Hidden):** {usage.get('tool_token_count', 'N/A')} tokens\n")
                        f.write(f"- **Total:** {usage.get('total_token_count', 'N/A')} tokens\n\n")

                elif 'error_message' in result:
                    f.write(f"**Error Details:**\n")
                    f.write(f"```\n{result['error_message']}\n```\n\n")
                
                f.write("---\n\n")
        print(f"Markdownレポートが保存されました: {md_filename}")
    except IOError as e:
        print(f"Markdownレポートの書き込みに失敗しました: {e}")

async def resolve_redirect_url(session: aiohttp.ClientSession, source: dict) -> dict:
    original_url = source.get('url')
    if not original_url: return source
    try:
        async with session.head(original_url, allow_redirects=True, timeout=5) as response:
            resolved_source = source.copy()
            resolved_source['url'] = str(response.url)
            return resolved_source
    except Exception:
        return source

async def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger, base_filename = setup_logger(timestamp)
    
    header = "--------------------------------------------------\n" \
             "Gemini検索エージェント (デュアル出力・最終完成版)\n" \
             "--------------------------------------------------"
    print(header)
    
    parser = argparse.ArgumentParser(description="ファイルから複数の質問を読み込み、Gemini検索エージェントに並列で実行させます。")
    parser.add_argument("query_file", type=str, help="処理したい質問が1行ずつ書かれたテキストファイルのパス。")
    parser.add_argument("-w", "--max-workers", type=int, default=10, help="同時に実行する並列タスクの最大数。")
    args = parser.parse_args()

    try:
        with open(args.query_file, 'r', encoding='utf-8') as f:
            queries = [line.strip() for line in f if line.strip()]
        if not queries:
            print("エラー: クエリファイルが空か、読み取り可能なクエリがありません。")
            return
    except FileNotFoundError:
        print(f"エラー: ファイルが見つかりません - {args.query_file}")
        return
    
    print(f"{len(queries)}件のクエリを、最大{args.max_workers}の並列度で実行します...")
    
    start_time = time.time()
    
    semaphore = asyncio.Semaphore(args.max_workers)
    async def run_with_semaphore(query):
        async with semaphore:
            return await ask_agent(query)

    tasks = [run_with_semaphore(query) for query in queries]
    results_list = await asyncio.gather(*tasks, return_exceptions=True)

    agent_processing_end_time = time.time()
    
    # URL解決とロギング処理
    print("\n情報源のURLを非同期・並列で解決中...")
    
    log_summary_results = []
    successful_tasks = 0
    
    async with aiohttp.ClientSession() as session:
        for i, results in enumerate(results_list):
            query_result = {"query_number": i + 1, "query": queries[i]}
            if isinstance(results, Exception):
                query_result["status"] = "ERROR"
                query_result["error_message"] = str(results)
            elif results:
                successful_tasks += 1
                query_result["status"] = "SUCCESS"

                # usage_metadataオブジェクトを、JSONに変換可能な「普通の辞書」に変換し、「隠れトークン」を計算する
                if 'usage_metadata' in results and results.get('usage_metadata'):
                    usage = results['usage_metadata']
                    
                    prompt_tokens = usage.prompt_token_count
                    candidate_tokens = usage.candidates_token_count
                    total_tokens = usage.total_token_count
                    
                    tool_tokens = max(0, total_tokens - prompt_tokens - candidate_tokens)
                    
                    results['usage_metadata'] = {
                        'prompt_token_count': prompt_tokens,
                        'candidates_token_count': candidate_tokens,
                        'tool_token_count': tool_tokens,
                        'total_token_count': total_tokens
                    }
                
                if results.get('sources'):
                    resolution_tasks = [resolve_redirect_url(session, source) for source in results['sources']]
                    resolved_sources = await asyncio.gather(*resolution_tasks, return_exceptions=True)
                    results['sources'] = [s for s in resolved_sources if not isinstance(s, Exception)]

                query_result["data"] = results
            else:
                query_result["status"] = "FAILURE"
                query_result["error_message"] = "Agent returned an empty result."
            log_summary_results.append(query_result)
            
    total_end_time = time.time()
    total_duration = total_end_time - start_time

    log_summary = {
        "execution_summary": {
            "total_queries": len(queries),
            "max_workers": args.max_workers,
            "total_duration_seconds": round(total_duration, 2),
        },
        "results": log_summary_results
    }
    
    # ログファイルにJSON形式で書き出す
    logger.info(json.dumps(log_summary, indent=2, ensure_ascii=False))
    
    # Markdownレポートを生成する
    generate_markdown_report(log_summary, base_filename)
    
    # コンソールへのサマリー表示
    print("\n==================================================")
    print("           バッチ処理 結果サマリー")
    print("==================================================")
    for result_log in log_summary["results"]:
        print(f"\n--- クエリ {result_log['query_number']:02d}: '{result_log['query']}' ---")
        print(f"  [ステータス]: {result_log['status']}")
        if result_log['status'] == 'SUCCESS':
            answer_snippet = result_log['data']['answer'].replace('\n', ' ').strip()
            print(f"  [回答の要約]: {answer_snippet[:100]}...")
            
            # トークン使用量の表示部分
            if result_log['data'].get('usage_metadata'):
                usage = result_log['data']['usage_metadata']
                print("  [トークン使用量]:")
                print(f"    - 入力 (プロンプト): {usage.get('prompt_token_count', 'N/A')} トークン")
                print(f"    - 出力 (思考+回答): {usage.get('candidates_token_count', 'N/A')} トークン")
                print(f"    - ツール応答 (隠れ): {usage.get('tool_token_count', 'N/A')} トークン")
                print(f"    - 合計: {usage.get('total_token_count', 'N/A')} トークン")

        elif 'error_message' in result_log:
            print(f"  [エラー内容]: {result_log['error_message']}")

    print("\n==================================================")
    print("                  処理完了")
    print("==================================================")
    print(f"成功したタスク: {successful_tasks} / {len(queries)} 件")
    print(f"合計処理時間: {total_duration:.2f}秒")
    print(f"1クエリあたりの平均時間: {total_duration / len(queries):.2f}秒")
    print(f"JSONログが保存されました: {base_filename}.json")
    print(f"Markdownレポートが保存されました: {base_filename}.md")
    print("--------------------------------------------------")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        # スクリプトの最後にセッションを保存する
        from api_key_manager import api_key_manager
        api_key_manager.save_session()
        print("\nAPIキーのセッションを保存しました。")