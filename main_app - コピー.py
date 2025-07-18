# main_app.py (Geminiの存在を一切知らない、究極に純化された司令塔)

# エージェントの「窓口」関数だけをインポートする。'client'はもう不要。
from gemini_agent import ask_agent
import argparse
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

def resolve_redirect_url(redirect_url: str) -> tuple[str, str]:
    """
    リダイレクトURLを解決して、最終的な本物のURLと、元のURLをタプルで返す。
    """
    try:
        response = requests.head(redirect_url, allow_redirects=True, timeout=5)
        return redirect_url, response.url
    except requests.RequestException:
        return redirect_url, redirect_url

def main():
    """
    この関数の責務はただ一つ：ユーザーからの指令を受け取り、エージェントに渡し、
    返ってきた報告書を見やすく表示すること。
    """
    print("--------------------------------------------------")
    print("Gemini検索エージェント (アーキテクチャ最終完成版)")
    print("--------------------------------------------------")
    
    parser = argparse.ArgumentParser(description="Gemini検索エージェントにコマンドラインから質問します。")
    parser.add_argument("query", type=str, help="エージェントに尋ねたい質問を文字列で指定します。")
    args = parser.parse_args()
    query = args.query

    start_time = time.time()
    
    # 司令塔の仕事は、これだけ。エージェントが裏で何をしているかは知る必要がない。
    results = ask_agent(query)
    
    agent_end_time = time.time()
    
    if results:
        if results['thought_summary']:
            print("\n■ 思考の要約:")
            print("---")
            print(results['thought_summary'])
            print("---")

        print("\n■ モデルの回答:")
        print(results['answer'])
        if results['sources']:
            print("\n--- 回答の根拠となった情報 ---")
            
            unique_sources_before_resolution = []
            seen_urls = set()
            for source in results['sources']:
                if source['url'] not in seen_urls:
                    unique_sources_before_resolution.append(source)
                    seen_urls.add(source['url'])
            
            print("\n情報源のURLを並列で解決中...")
            final_sources = {}
            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_url = {executor.submit(resolve_redirect_url, source['url']): source['url'] for source in unique_sources_before_resolution}
                for future in as_completed(future_to_url):
                    original_url, final_url = future.result()
                    final_sources[original_url] = final_url
            
            for i, source in enumerate(unique_sources_before_resolution):
                resolved_url = final_sources.get(source['url'], source['url'])
                print(f"\n[{i+1}] 情報源:")
                print(f"    - タイトル: {source['title']}")
                print(f"    - URL: {resolved_url}")

    total_end_time = time.time()
    agent_time = agent_end_time - start_time
    total_time = total_end_time - start_time
    
    print(f"\n>> エージェントの処理時間: {agent_time:.2f}秒")
    print(f">> URL解決を含む合計処理時間: {total_time:.2f}秒")
    print("\n--------------------------------------------------")

if __name__ == "__main__":
    main()