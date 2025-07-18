# api_key_manager.py (APIキーの管理に関する全てを司る、独立したモジュール)

import os
import json
import asyncio
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# セッションファイル（最後に使ったキーのインデックスを保存する場所）
SESSION_FILE = os.path.join(os.getcwd(), '.session_data.json')

class ApiKeyManager:
    """
    複数のAPIキーを管理し、安全なローテーション、セッションの永続化、
    および高負荷な並列処理下でのレースコンディションを回避するシステム。
    """
    def __init__(self):
        self._api_keys: list[str] = []
        self._current_index: int = -1
        self._last_access_time: float = 0.0
        # APIコール間のクールダウン時間（秒）。レート制限に対する安全マージン。
        self._COOLDOWN_SECONDS = 0.1 # 0.1秒

        # キー選択処理をアトミック（不可分）にするためのロック
        self._key_selection_lock = asyncio.Lock()
        
        self._load_api_keys_from_env()
        self._load_session()
        
        # シングルトンとして振る舞うためのクラス変数
        ApiKeyManager._instance = self

    def _load_api_keys_from_env(self):
        """ .envファイルから全てのAPIキーを読み込む """
        keys = set() # 重複を自動的に排除するためにセットを使用
        # GOOGLE_API_KEY も読み込む
        if os.getenv('GOOGLE_API_KEY'):
            keys.add(os.getenv('GOOGLE_API_KEY'))
        
        # GOOGLE_API_KEY_1, _2, ... を読み込む
        i = 1
        while True:
            key = os.getenv(f'GOOGLE_API_KEY_{i}')
            if key:
                keys.add(key)
                i += 1
            else:
                break
        
        self._api_keys = list(keys)
        if not self._api_keys:
            print("警告: APIキーが.envファイルに設定されていません。")
        else:
            print(f"[{self.__class__.__name__}] {len(self._api_keys)}個のユニークなAPIキーをロードしました。")

    def _load_session(self):
        """ セッションファイルから、最後に使ったキーのインデックスを読み込む """
        try:
            if os.path.exists(SESSION_FILE):
                with open(SESSION_FILE, 'r') as f:
                    data = json.load(f)
                    last_index = data.get('lastKeyIndex', -1)
                    if 0 <= last_index < len(self._api_keys):
                        self._current_index = last_index
        except (IOError, json.JSONDecodeError) as e:
            print(f"セッションファイルの読み込みに失敗しました: {e}")
            self._current_index = -1

    def save_session(self):
        """ 最後に使ったキーのインデックスをセッションファイルに保存する """
        try:
            with open(SESSION_FILE, 'w') as f:
                json.dump({'lastKeyIndex': self._current_index}, f)
        except IOError as e:
            print(f"セッションファイルの保存に失敗しました: {e}")

    async def get_next_key(self) -> str | None:
        """
        次の利用可能なAPIキーを、安全な排他制御とクールダウン付きで取得する。
        """
        if not self._api_keys:
            return None

        # asyncio.Lockを使い、キーの選択とインデックス更新処理が同時に実行されないようにする
        async with self._key_selection_lock:
            now = asyncio.get_event_loop().time()
            elapsed_time = now - self._last_access_time

            # 前回の呼び出しからクールダウン時間内に再度呼び出された場合、待機する
            if self._last_access_time > 0 and elapsed_time < self._COOLDOWN_SECONDS:
                wait_time = self._COOLDOWN_SECONDS - elapsed_time
                await asyncio.sleep(wait_time)
            
            # ラウンドロビン方式で次のインデックスを計算
            self._current_index = (self._current_index + 1) % len(self._api_keys)
            self._last_access_time = asyncio.get_event_loop().time() # キーを払い出した時刻を更新
            
            return self._api_keys[self._current_index]

# シングルトンインスタンスとしてエクスポート（プログラム全体で一つのインスタンスを共有する）
api_key_manager = ApiKeyManager()