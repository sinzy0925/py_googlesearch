import json
import os
import sys
import re
def format_temple_list(input_filename, items_per_line=30):
    """
    寺院リストが書かれたテキストファイルを読み込み、
    全寺院を一度連結した後、指定された数ごとに改行して整形する。

    Args:
        input_filename (str): 入力するテキストファイル名。
        items_per_line (int): 1行あたりに並べる寺院の数。
    """
    # 元のファイル名に "_formatted" を付けて出力ファイル名を生成
    base_name, ext = os.path.splitext(input_filename)
    output_filename = f"{base_name}.txt_formatted.txt"

    try:
        # ファイルを読み込む
        with open(input_filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        all_temples = []
        # 各行を処理して、全寺院名を一つのリストにまとめる
        for line in lines:
            line = line.strip()
            if not line:  # 空行は無視
                continue

            # 行末に '.' があれば取り除く
            if line.endswith('.'):
                line = line[:-1]

            # カンマ「,」と読点「、」の両方で分割する
            # これにより、どちらの記号が使われていても対応可能
            temples_in_line = re.split(r'[、,]', line)

            # 分割した各要素の前後の空白を削除し、中身が空でなければリストに追加
            all_temples.extend([temple.strip() for temple in temples_in_line if temple.strip()])

        # 整形後の各行を格納するリスト
        formatted_lines = []
        
        # 固定の接頭辞（先頭につける文章）を定義
        prefix_string = '大阪市天王寺区に以下のお寺があります。それぞれの寺の名前,電話番号,住所\\nをCSVで抽出して　解説は不要　# google_search '
        
        # 全寺院リストを、指定された数（items_per_line）ずつのまとまりに分割
        for i in range(0, len(all_temples), items_per_line):
            chunk = all_temples[i:i + items_per_line]
            
            # チャンク（寺院のまとまり）をカンマで連結して寺院リスト部分の文字列を作成
            temple_list_string = ",".join(chunk)
            
            # 接頭辞と寺院リストを「+」で連結して、1行分の完全な文字列を作成する
            full_line = prefix_string + temple_list_string
            
            # 完成した1行をリストに追加する
            formatted_lines.append(full_line)
            
        # 整形されたすべての行を、改行文字で連結して最終的な出力データを作成
        output_data = "\n".join(formatted_lines)

        # 新しいファイルに書き出す
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(output_data)

        print(f"'{output_filename}' に整形後のリストを正常に書き出しました。")
        print(f"合計 {len(all_temples)} 件のデータを、1行あたり最大 {items_per_line} 件で整形しました。")

    except FileNotFoundError:
        print(f"エラー: ファイル '{input_filename}' が見つかりません。")
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")

def extract_temple_lists(input_filename):
    """
    JSONファイルから寺院名のリストのみを抽出し、テキストファイルに書き出す。
    - カンマ区切りのリスト形式を優先して抽出する。
    - 上記が見つからない場合、箇条書きからリストを生成する。

    Args:
        input_filename (str): 入力するJSONファイル名。
    """
    # 出力ファイル名を生成 (例: AAA.json -> AAA.txt)
    base_name = os.path.splitext(input_filename)[0]
    output_filename = f"{base_name}.txt"

    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        extracted_lists = []

        # 'results' のリストをループ処理
        if 'results' in data and isinstance(data['results'], list):
            for result in data['results']:
                if 'data' in result and 'answer' in result['data']:
                    answer_text = result['data']['answer']
                    lines = answer_text.splitlines()
                    
                    found_list = False

                    # --- 戦略1: まずカンマ区切りのリスト形式の行を探す ---
                    for line in lines:
                        line = line.strip()
                        # 条件: カンマが2つ以上含まれる行をリスト候補とする
                        if line.count(',') + line.count('、') >= 2:
                            # ただし、明らかに文章であるものは除外する
                            if not any(prose in line for prose in ['です', 'ます', 'Here', ' a list of', ' as follows:']):
                                extracted_lists.append(line)
                                found_list = True
                                break # このanswerの処理は完了
                    
                    if found_list:
                        continue # 次のresultへ

                    # --- 戦略2: カンマ区切りのリストが見つからない場合、箇条書きを解析 ---
                    temple_names = []
                    # 「* 名前」「1. 名前」のような形式にマッチする正規表現
                    # 名前の後のカッコ書き「（）」やブラケット「[]」は除外する
                    list_item_pattern = re.compile(r"^\s*[*1-9]+\.?\s*([^(\[（]+)")
                    
                    for line in lines:
                        match = list_item_pattern.match(line)
                        if match:
                            # マッチした部分（寺院名）の前後の空白を削除してリストに追加
                            name = match.group(1).strip()
                            temple_names.append(name)
                    
                    # 箇条書きから名前が一つでも取れたら、カンマで連結してリストに追加
                    if temple_names:
                        extracted_lists.append(",".join(temple_names))

        # 抽出したすべてのリストをテキストファイルに書き出す
        if extracted_lists:
            # 各リストの間には空行を1行いれる
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write("\n".join(extracted_lists))
            print(f"'{output_filename}' に寺院リストを正常に書き出しました。")
        else:
            print("抽出対象のリストが見つかりませんでした。")

    except FileNotFoundError:
        print(f"エラー: ファイル '{input_filename}' が見つかりません。")
    except json.JSONDecodeError:
        print(f"エラー: ファイル '{input_filename}' は有効なJSON形式ではありません。")
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")

# スクリプトを実行
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("エラー: 入力ファイル名を指定してください。")
        print(f"使用法: python {sys.argv[0]} <入力JSONファイル名>")
        sys.exit(1)

    input_file  = sys.argv[1]
    extract_temple_lists(input_file)
    input_file2 = input_file.split('.')[0] + '.txt'
    format_temple_list(input_file2, items_per_line=30)
    print('処理が完了しました。')
