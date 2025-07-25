# Gemini検索エージェント (Self-Correcting Research Agent)

## 概要

これは、単なる検索ツールではありません。Googleの最新AIであるGeminiを搭載し、**自ら思考戦略を立て、自己評価と反復検索を繰り返す**ことで、ユーザーの要求に対して粘り強く、質の高い回答を生成することを目指す高度な検索エージェントです。

このプロジェクトは、AIロジックを担う「専門エージェント」 (`gemini_agent.py`) と、ユーザーとの窓口となる「司令塔」 (`main_app.py`) に役割を完全に分離した、クリーンなアーキテクチャを採用しています。

## 主な特徴

-   **🧠 自律的な戦略プランニング**:
    ユーザーの質問を分析し、「思考言語（英語/日本語）」と「難易度（高/中/低）」をAIが自ら判断。最適なアプローチで調査を開始します。

-   **🔄 自己評価と反復検索**:
    一度の検索で得られた情報が不十分な場合、エージェントは「何が足りないか」を自己評価し、より具体的なクエリで**追加のWeb検索を自動的に実行**します。これにより、情報の網羅性と精度を極限まで高めます。

-   **🏢 関心の分離アーキテクチャ**:
    AIの複雑なロジックはすべて`gemini_agent.py`にカプセル化。司令塔である`main_app.py`は、エージェントに仕事を依頼し、報告書を受け取るだけなので、コードの見通しが良く、メンテナンスや機能拡張が容易です。

-   **🔍 透明性の確保**:
    最終的な回答だけでなく、AIがどのように考え、調査を進めたかの「思考の要約」と、回答の根拠となった「情報源のURL」を明示。AIの判断プロセスを追跡できます。

## 技術スタック

-   Python 3.8以上
-   **Google AI Python SDK (`google-genai`)**
-   Requests (情報源URLの解決用)
-   Python-Dotenv (APIキー管理用)

---

## 🚀 セットアップ手順

### 1. リポジトリをクローン

```bash
git clone <リポジトリのURL>
cd <リポジトリ名>
```

### 2. Python仮想環境の作成と有効化

クリーンな環境で実行するために、仮想環境を作成することを強く推奨します。

```bash
# 仮想環境を作成
python -m venv venv

# 仮想環境を有効化
# Windowsの場合
.\venv\Scripts\activate
# macOS / Linuxの場合
source venv/bin/activate
```

### 3. APIキーの設定

1.  [Google AI Studio](https://aistudio.google.com/app/apikey)にアクセスし、APIキーを取得します。
2.  プロジェクトのルートディレクトリに `.env` という名前のファイルを作成します。
3.  作成した`.env`ファイルに、取得したAPIキーを以下のように記述します。

    **.env**
    ```
    GOOGLE_API_KEY="ここにあなたのAPIキーを貼り付けてください"
    ```

### 4. 依存パッケージのインストール

`requirements.txt`ファイルに必要なライブラリがすべて記載されています。以下のコマンドで一度にインストールします。

```bash
pip install -r requirements.txt
```*(もし`uv`をお使いの場合は `uv pip install -r requirements.txt` でも同様にインストールできます)*


## 実行方法

セットアップが完了したら、ターミナルから`main_app.py`を実行します。引数として、エージェントに尋ねたい質問を文字列で渡してください。

### 実行例

**単純な質問:**
```bash
python main_app.py "日本の現在の首相は誰ですか？"
```

**専門的な調査:**
```bash
python main_app.py "米国株で、配当利回りが4%以上の銘柄を5つ、その利回りデータと共に教えて"
```

**複雑な分析:**
```bash
python main_app.py "Pythonの非同期処理について、async/awaitの基本的な使い方とメリット・デメリットをまとめて"
```

---

## 🏛️ アーキテクチャとコード解説

### `main_app.py` (司令塔)
-   **役割**: ユーザーからの指令（コマンドライン引数）を受け取り、エージェントに渡し、返ってきた報告書（結果）を見やすく表示することに特化しています。
-   AIの内部ロジックについては一切関知しません。
-   受け取った情報源のURL（リダイレクトされている場合がある）を解決し、最終的なURLを表示する機能も持ちます。

### `gemini_agent.py` (専門エージェント)
-   **役割**: このアプリケーションの頭脳です。指令を達成するための全てのAIロジックを内包します。
-   **`_decide_strategy(query)`**:【内部関数】第一エージェント。指令の性質を分析し、最適な「思考言語」と「難易度」からなる戦略を立案します。
-   **`ask_agent(query)`**:【公開関数】第二エージェントであり、唯一の公開窓口。立案された戦略に基づき、システムプロンプト（自己評価と反復検索のルール）を設定し、Google検索ツールを使って調査を実行。最終的な回答、思考の要約、情報源を生成して司令塔に報告します。

## ライセンス

このプロジェクトは [MITライセンス](LICENSE) の下で公開されています。

承知いたしました。これまでの対話と、一連のバッチ処理から得られたすべての知見、ノウハウ、そして完成したスクリプトの使い方を、一つの完璧な`README.md`ファイルにまとめます。

このファイルをプロジェクトのルートディレクトリに保存すれば、誰でもこの強力なAIエージェントを最大限に活用できるようになります。

---

# Gemini AI 並列実行エージェント

## 概要

このプロジェクトは、GoogleのGeminiモデルを搭載したAIエージェントを活用し、Web検索やURLコンテンツの読み取りを伴う反復的な情報収集タスクを、**並列処理によって高速に自動化する**ためのツールです。

テキストファイルに複数の質問（クエリ）を記述するだけで、各クエリを独立したタスクとして同時に実行し、結果を構造化されたJSONログと、人間が読みやすいMarkdownレポートとして出力します。

## 主な機能

-   **バッチ処理:** テキストファイルから複数のクエリを読み込み、一括で実行します。
-   **並列実行:** `asyncio`を活用し、複数のタスクを同時に処理することで、全体の実行時間を大幅に短縮します。
-   **動的な戦略決定:** 各クエリの言語や難易度をAIが自動で分析し、思考予算（`thinking_budget`）などを最適化します。
-   **デュアル出力:**
    -   **JSONログ:** 全ての実行結果を、再利用や分析に適した構造化データとして保存します。
    -   **Markdownレポート:** 人間が結果を確認しやすいように、整形されたレポートを自動生成します。
-   **高度なプロンプト制御:** クエリに特定のフラグ（`#url_context`）を含めることで、AIの行動様式を動的に変更できます。

## 構成ファイル

-   `gemini_agent.py`: 中核となるAIエージェント。戦略決定とGemini APIとの通信を担います。
-   `main_app.py`: バッチ処理と並列実行を管理する実行スクリプト。
-   `requirements.txt`: 必要なPythonライブラリのリスト。
-   `.env`: APIキーなどの環境変数を格納するファイル。

## セットアップ

1.  **リポジトリのクローンまたはダウンロード**
    プロジェクトファイルをローカル環境に配置します。

2.  **.envファイルの作成**
    プロジェクトのルートに`.env`という名前のファイルを作成し、お使いのGoogle AI APIキーを以下のように記述します。
    ```
    GOOGLE_API_KEY="ここにあなたのAPIキーを貼り付け"
    ```

3.  **必要なライブラリのインストール**
    ターミナルで以下のコマンドを実行し、必要なライブラリをインストールします。
    ```bash
    pip install -r requirements.txt
    ```

## 使い方

1.  **クエリファイルの準備**
    処理したい質問を1行ずつ記述したテキストファイルを作成します。（例: `queries.txt`）

2.  **スクリプトの実行**
    ターミナルで`main_app.py`を実行します。引数として、準備したクエリファイルのパスを指定します。

    ```bash
    python main_app.py queries.txt
    ```
    -   `-w`または`--max-workers`オプションで、並列実行するタスクの最大数を指定できます。（デフォルトは10）
        ```bash
        python main_app.py queries.txt -w 5
        ```

3.  **結果の確認**
    実行が完了すると、`log`ディレクトリ内にタイムスタンプ付きのファイルが2つ生成されます。
    -   `YYYYMMDD_HHMMSS.json`: 全ての詳細情報が含まれたJSONログ。
    -   `YYYYMMDD_HHMMSS.md`: 整形されたMarkdownレポート。

---

## ⭐ AIエージェントを使いこなすための黄金律（最重要） ⭐

一連の実験を通じて、このAIエージェントの性能を最大限に引き出すための、最も効果的な利用方法が確立されました。

### 基本原則：人間が「戦略家」、AIが「実行部隊」

AIは、曖昧で複雑な「発見」タスクよりも、明確で単純な「作業」タスクの方が圧倒的に得意です。
したがって、最も良い結果を得るためには、人間が賢い監督として振る舞い、タスクをAIが実行しやすい形に設計する必要があります。

> **複雑な問題を、人間がAIの解きやすい単純なタスクに分解して与えること。**
> これが、このシステムを使いこなすための鍵です。

### 黄金律：「30件バッチ」という最適戦略

大量のデータ（例: 100件以上の企業リスト）を一度に処理させようとすると、AIは思考プロセスの途中で時間やトークンの上限に達し、最終的な答えを出力できずに失敗します。

実験の結果、以下の**「スイートスポット（最適値）」**が判明しました。

> **一度にAIに処理させる件数は「30件」程度に分割するのが、最も安定的かつ効率的に完璧な結果を得られる方法です。**

タスクが単純な場合は40件程度まで成功しますが、安定性を最優先するなら30件が黄金律です。

### 実践的なワークフロー：2ステップ戦略

#### ステップ1：発見フェーズ（大まかなリストアップ）

まず、AIに「検証」や「確認」を求めず、**とにかく名前をリストアップさせる**ことだけに集中させます。

-   **クエリの例 (`step1.txt`): １行づつの質問を記述してください。**
    ```
    大阪市天王寺区のお寺の名前を、できるだけ多くリストアップしてください。
    大阪市天王寺区のお寺の名前を、できるだけ多くリストアップしてください。
    大阪市天王寺区のお寺の名前を、できるだけ多くリストアップしてください。
    ```
-   **実行:**
    ```bash
    python main_app.py step1.txt
    ```    これにより、AIはウェブサイトの有無などを気にせず、高速で大量の候補リストを生成します。

#### ステップ2：情報収集フェーズ（個別撃破）

ステップ1で得られた.jsonファイルのリストに注目します。
answerで検索してください。
"answer": "大阪市天王寺区にあるお寺の名前を以下にリストアップします。\n\n*   妙光寺\n*   堂閣寺\n*   道善寺\n*   妙覚寺\n*   "
上記のような感じで、たくさん出力されます。
\nは改行コードこれを活かします。
**エディタで、\nを検索して、1行に30件ある状態を作ります**
そして、それぞれのファイルに対して、具体的な情報収集を依頼します。

-   **クエリの例 (`step2_part1.txt`):**
    ```
    以下の大阪市天王寺区の以下のお寺について、名前,電話番号,住所のcsvにして、リストアップしてください。妙光寺\n*   堂閣寺\n*   道善寺\n*   妙覚寺\n*    ... (30件分)
    ```
-   **実行:**
    ```bash
    python main_app.py step2_part1.txt
    ```
    この方法であれば、AIは一つ一つのタスクが単純なため、迷うことなく最高のパフォーマンスを発揮し、完璧なCSVを生成します。

---

## 高度なプロンプト技術

### `#url_context` フラグの活用

ユーザーが特定のURLの内容を深く調査してほしい場合、クエリの末尾に`#url_context`と記述します。これにより、AIは`url_context`ツールの使用を最優先する専用モードで動作します。

-   **使用例:**
    `米国ETFの高利回り銘柄について、この記事（https://example.com/etf-ranking）を参考にしてリストアップして。 #url_context`

### 制約の緩和

AIに「絶対に50件」のような厳格な制約を与えると、達成不可能な場合に処理を諦めてしまうことがあります。

-   **悪い例:** `企業名を50件リストアップして。`
-   **良い例:** `企業名を可能な限り多くリストアップしてください。**見つけられただけで構いません。**`

「〜だけで構いません」「可能な範囲で」といった言葉は、AIに不完全な結果でも報告する許可を与え、結果を出力させる上で非常に有効です。

## AIの限界とトラブルシューティング

-   **ログインの壁:** 会員登録やログインが必要なサイトの情報は取得できません。
-   **複雑なナビゲーション:** サイト内のリンクを複数回クリックして情報を探すような、複雑な操作は苦手です。
-   **`FAILURE: Agent returned an empty result.`:**
    タスクが複雑すぎるか、制約が厳しすぎます。上記の「黄金律」に従い、タスクを分割・単純化してください。
-   **`SUCCESS`なのに`Answer`が出力されない:**
    タスク量が多すぎて、AIが途中で力尽きています。一度に処理させる件数を減らしてください。（30件が推奨）


---

### プロンプト設計の神髄：速度とコストのトレードオフ

驚くべきことに、AIに求める出力形式をどう指示するかで、処理の**「速度」**と**「コスト（消費トークン）」**が大きく変わることが判明しました。これは、AIの内部的な思考プロセスと、仕事の「丁寧さ」が変化するためです。

あなたの目的に応じて、プロンプトの表現を戦略的に使い分けることで、このエージェントの性能を最大限に引き出すことができます。

| | 速度優先モード | コスト優先モード |
| :--- | :--- | :--- |
| **プロンプトの例** | `...名前,電話番号,住所を**CSVで**取得して` | `...名前,電話番号,住所を**取得して**` |
| **実行速度** | **速い** | 遅い |
| **消費トークン（コスト）** | 高い | **安い** |
| **AIの内部的な挙動<br>（なぜそうなるか）** | 出力形式が「CSV」という強力な制約によってAIの「迷い」がなくなり、処理が一直線の「作業」になるため**高速化**します。

一方で、機械的可読性の高いデータを保証しようと、より多くの情報源を照合（ツールを多用）するため、「隠れトークン」が増加し**コストは高くなる**傾向があります。 | 出力形式が自由なため、AIは「どう報告するのが親切か」というプレゼンテーションについて**思考する時間が必要**です。その分、実行時間は長くなります。

一方で、人間向けの報告が目的なので、一つの信頼できる情報源が見つかれば満足し、過剰な裏取り（ツールの使用）を控えるため、総消費トークンは**安くなる**傾向があります。 |

---

### 結論：あなたの目的に合わせて使い分ける

-   **最速の結果が欲しい場合:**
    プロンプトで`CSVで取得して`のように、**出力形式を厳密に指定**してください。AIの思考をショートカットさせ、最速で処理を完了させます。

-   **コストを最小限に抑えたい場合:**
    プロンプトを`取得して`のように、**出力形式を曖昧に**してください。AIの過剰なツール使用を抑制し、最も安価にタスクを実行します。