"""
ollama_client.py

QThread-based streaming client for local Ollama API.
未來可擴充支援 OpenAI / Anthropic 等雲端 API。

Signals:
    chunk_received(str)   — 每收到一段回應文字就 emit
    finished_signal()     — 串流完成（含正常結束與錯誤後）
    error_occurred(str)   — 連線失敗或 API 錯誤
"""
from __future__ import annotations
import json
import urllib.request
import urllib.error

from PyQt6.QtCore import QThread, pyqtSignal


class OllamaThread(QThread):
    chunk_received  = pyqtSignal(str)
    finished_signal = pyqtSignal()
    error_occurred  = pyqtSignal(str)

    def __init__(
        self,
        base_url: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        parent=None,
    ):
        super().__init__(parent)
        self._base_url = base_url.rstrip("/")
        self._model    = model
        self._system   = system_prompt
        self._user     = user_prompt
        self._abort    = False

    def abort(self):
        """呼叫後下一個 chunk 讀取前中止。"""
        self._abort = True

    def run(self):
        url = f"{self._base_url}/api/generate"
        payload = json.dumps({
            "model":  self._model,
            "system": self._system,
            "prompt": self._user,
            "stream": True,
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                for raw_line in resp:
                    if self._abort:
                        break
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    try:
                        obj   = json.loads(line)
                        chunk = obj.get("response", "")
                        if chunk:
                            self.chunk_received.emit(chunk)
                        if obj.get("done", False):
                            break
                    except json.JSONDecodeError:
                        pass

        except urllib.error.URLError as e:
            reason = getattr(e, "reason", str(e))
            self.error_occurred.emit(f"連線失敗：{reason}")
        except TimeoutError:
            self.error_occurred.emit("連線逾時，請確認 Ollama 服務是否啟動")
        except Exception as e:
            self.error_occurred.emit(f"錯誤：{e}")
        finally:
            self.finished_signal.emit()


# ── 同步工具函式 ───────────────────────────────────────────────────────────────

def fetch_models(base_url: str) -> list[str]:
    """
    同步取得 Ollama 已安裝的模型清單。
    成功回傳 name list；失敗回傳空 list。
    """
    url = f"{base_url.rstrip('/')}/api/tags"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []
