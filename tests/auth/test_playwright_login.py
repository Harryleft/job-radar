"""测试 playwright_login 模块 — CDP 自动登录、手动登录、Cookie 解析与凭据持久化"""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.auth.playwright_login import (
    REQUIRED_COOKIES,
    ChromeNotFoundError,
    CookieParseError,
    LoginTimeoutError,
    MissingCookiesError,
    _find_chrome,
    _parse_cookie_input,
    _wait_for_login,
    cdp_login,
    check_status,
    load_credential,
    manual_login,
    save_credential,
)

# ── Chrome 查找测试 ──────────────────────────────────────────────────


class TestFindChrome:
    """测试 Chrome 路径查找"""

    def test_found(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        fake_chrome = tmp_path / "chrome.exe"
        fake_chrome.write_text("")
        monkeypatch.setattr(
            "src.auth.playwright_login._CHROME_SEARCH_PATHS", [fake_chrome]
        )
        assert _find_chrome() == fake_chrome

    def test_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "src.auth.playwright_login._CHROME_SEARCH_PATHS",
            [Path("/nonexistent/chrome.exe")],
        )
        assert _find_chrome() is None


# ── 自动登录检测测试 ──────────────────────────────────────────────────


class TestWaitForLogin:
    """测试自动登录检测轮询"""

    def test_detects_redirect(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # 模拟页面已跳转到主页
        fake_response = MagicMock()
        fake_response.read.return_value = json.dumps(
            [{"url": "https://www.zhipin.com/web/geek/job"}]
        ).encode()
        fake_response.__enter__ = MagicMock(return_value=fake_response)
        fake_response.__exit__ = MagicMock(return_value=False)
        monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: fake_response)

        _wait_for_login(9222, timeout=5)  # 应立即返回

    def test_timeout_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # 模拟页面一直在登录页
        fake_response = MagicMock()
        fake_response.read.return_value = json.dumps(
            [{"url": "https://www.zhipin.com/web/user/?ka=header-login"}]
        ).encode()
        fake_response.__enter__ = MagicMock(return_value=fake_response)
        fake_response.__exit__ = MagicMock(return_value=False)
        monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: fake_response)
        monkeypatch.setattr("time.sleep", lambda *a: None)  # 跳过 sleep 加速测试

        with pytest.raises(LoginTimeoutError, match="登录超时"):
            _wait_for_login(9222, timeout=1)

    def test_connection_error_retries(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # 第一次连接失败，第二次返回已登录页面
        call_count = 0
        fake_response = MagicMock()
        fake_response.read.return_value = json.dumps(
            [{"url": "https://www.zhipin.com/"}]
        ).encode()
        fake_response.__enter__ = MagicMock(return_value=fake_response)
        fake_response.__exit__ = MagicMock(return_value=False)

        def mock_urlopen(*a, **kw):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionRefusedError
            return fake_response

        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)
        monkeypatch.setattr("time.sleep", lambda *a: None)

        _wait_for_login(9222, timeout=5)
        assert call_count == 2


# ── CDP 登录测试 ──────────────────────────────────────────────────────


class TestCdpLogin:
    """测试 CDP 登录流程（mock 外部依赖）"""

    def test_no_chrome_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("src.auth.playwright_login._find_chrome", lambda: None)
        with pytest.raises(ChromeNotFoundError, match="未找到 Chrome"):
            cdp_login()

    def test_successful_cdp_login(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "src.auth.playwright_login._find_chrome",
            lambda: Path("/fake/chrome.exe"),
        )

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: mock_proc)
        monkeypatch.setattr("tempfile.mkdtemp", lambda **kw: "/tmp/test-chrome")
        monkeypatch.setattr("shutil.rmtree", lambda *a, **kw: None)
        monkeypatch.setattr("time.sleep", lambda *a: None)

        # Mock CDP 就绪和登录检测
        monkeypatch.setattr(
            "src.auth.playwright_login._wait_for_cdp_ready", lambda *a, **kw: None
        )
        monkeypatch.setattr(
            "src.auth.playwright_login._wait_for_login", lambda *a, **kw: None
        )

        fake_cookies = {
            "__zp_stoken__": "st_val",
            "wt2": "wt_val",
            "wbg": "0",
            "zp_at": "at_val",
        }
        monkeypatch.setattr(
            "src.auth.playwright_login._extract_cookies_via_cdp",
            lambda pw_factory: fake_cookies,
        )

        cookies = cdp_login()
        assert set(cookies.keys()) >= REQUIRED_COOKIES

    def test_missing_cookies_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "src.auth.playwright_login._find_chrome",
            lambda: Path("/fake/chrome.exe"),
        )
        mock_proc = MagicMock()
        monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: mock_proc)
        monkeypatch.setattr("tempfile.mkdtemp", lambda **kw: "/tmp/test-chrome")
        monkeypatch.setattr("shutil.rmtree", lambda *a, **kw: None)
        monkeypatch.setattr("time.sleep", lambda *a: None)
        monkeypatch.setattr(
            "src.auth.playwright_login._wait_for_cdp_ready", lambda *a, **kw: None
        )
        monkeypatch.setattr(
            "src.auth.playwright_login._wait_for_login", lambda *a, **kw: None
        )

        monkeypatch.setattr(
            "src.auth.playwright_login._extract_cookies_via_cdp",
            lambda pw_factory: {"wt2": "only"},
        )

        with pytest.raises(MissingCookiesError):
            cdp_login()


# ── Cookie 解析测试 ──────────────────────────────────────────────────


class TestParseCookieInput:
    """测试用户粘贴内容的解析"""

    def test_parse_json(self) -> None:
        raw = '{"__zp_stoken__": "abc123", "wt2": "def456"}'
        result = _parse_cookie_input(raw)
        assert result == {"__zp_stoken__": "abc123", "wt2": "def456"}

    def test_parse_cookie_string(self) -> None:
        raw = "__zp_stoken__=abc123; wt2=def456; wbg=0"
        result = _parse_cookie_input(raw)
        assert result == {"__zp_stoken__": "abc123", "wt2": "def456", "wbg": "0"}

    def test_parse_value_with_equals(self) -> None:
        raw = "token=abc=def=ghi"
        result = _parse_cookie_input(raw)
        assert result == {"token": "abc=def=ghi"}

    def test_parse_empty_raises(self) -> None:
        with pytest.raises(CookieParseError):
            _parse_cookie_input("")

    def test_parse_garbage_raises(self) -> None:
        with pytest.raises(CookieParseError):
            _parse_cookie_input("not valid cookie data at all")

    def test_parse_cookie_js_output(self) -> None:
        raw = '{"__zp_stoken__":"s%3Aabc","wt2":"val123","wbg":"0","zp_at":"at456"}'
        result = _parse_cookie_input(raw)
        assert set(result.keys()) >= {"__zp_stoken__", "wt2", "wbg", "zp_at"}


# ── 凭据持久化测试 ──────────────────────────────────────────────────


class TestSaveCredential:
    """测试凭据保存（兼容 boss-cli 格式）"""

    def test_saves_correct_format(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cred_file = tmp_path / "credential.json"
        monkeypatch.setattr("src.auth.playwright_login.CREDENTIAL_FILE", cred_file)

        cookies = {"__zp_stoken__": "abc", "wt2": "def", "wbg": "0", "zp_at": "xyz"}
        path = save_credential(cookies)

        assert path == cred_file
        data = json.loads(cred_file.read_text(encoding="utf-8"))
        assert set(data.keys()) == {"cookies", "saved_at"}
        assert data["cookies"] == cookies
        assert isinstance(data["saved_at"], float)

    def test_creates_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cred_file = tmp_path / "subdir" / "credential.json"
        monkeypatch.setattr("src.auth.playwright_login.CREDENTIAL_FILE", cred_file)

        save_credential({"wt2": "test"})
        assert cred_file.exists()


class TestLoadCredential:
    """测试凭据加载"""

    def test_loads_existing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cred_file = tmp_path / "credential.json"
        monkeypatch.setattr("src.auth.playwright_login.CREDENTIAL_FILE", cred_file)

        data = {"cookies": {"wt2": "abc"}, "saved_at": time.time()}
        cred_file.write_text(json.dumps(data), encoding="utf-8")

        cookies = load_credential()
        assert cookies == {"wt2": "abc"}

    def test_returns_none_when_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cred_file = tmp_path / "nonexistent.json"
        monkeypatch.setattr("src.auth.playwright_login.CREDENTIAL_FILE", cred_file)
        assert load_credential() is None

    def test_returns_none_on_invalid_json(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cred_file = tmp_path / "credential.json"
        monkeypatch.setattr("src.auth.playwright_login.CREDENTIAL_FILE", cred_file)
        cred_file.write_text("not json", encoding="utf-8")
        assert load_credential() is None


# ── manual_login 集成测试（mock input）──────────────────────────────


class TestManualLogin:
    """测试手动登录流程（降级方案）"""

    def test_successful_login(self, monkeypatch: pytest.MonkeyPatch) -> None:
        inputs = iter(["", "val_stoken", "val_wt2", "0", "val_zp_at"])
        monkeypatch.setattr("builtins.input", lambda *a: next(inputs))
        monkeypatch.setattr("webbrowser.open", lambda *a: None)

        cookies = manual_login()
        assert set(cookies.keys()) >= REQUIRED_COOKIES

    def test_partial_skip_then_raise(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        inputs = iter(["", "val_stoken", "", "", ""])
        monkeypatch.setattr("builtins.input", lambda *a: next(inputs))
        monkeypatch.setattr("webbrowser.open", lambda *a: None)

        with pytest.raises(MissingCookiesError) as exc_info:
            manual_login()
        assert "wt2" in exc_info.value.missing

    def test_all_missing_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        inputs = iter(["", "", "", "", ""])
        monkeypatch.setattr("builtins.input", lambda *a: next(inputs))
        monkeypatch.setattr("webbrowser.open", lambda *a: None)

        with pytest.raises(MissingCookiesError):
            manual_login()


# ── check_status 测试 ────────────────────────────────────────────────


class TestCheckStatus:
    """测试状态检查输出"""

    def test_not_logged_in(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        cred_file = tmp_path / "nonexistent.json"
        monkeypatch.setattr("src.auth.playwright_login.CREDENTIAL_FILE", cred_file)

        check_status()
        assert "未登录" in capsys.readouterr().out

    def test_logged_in(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        cred_file = tmp_path / "credential.json"
        monkeypatch.setattr("src.auth.playwright_login.CREDENTIAL_FILE", cred_file)

        cookies = {k: f"val_{k}" for k in REQUIRED_COOKIES}
        data = json.dumps({"cookies": cookies, "saved_at": time.time()})
        cred_file.write_text(data, encoding="utf-8")

        check_status()
        output = capsys.readouterr().out
        assert "已登录" in output
        assert "4 个 cookie" in output

    def test_incomplete_cookies(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        cred_file = tmp_path / "credential.json"
        monkeypatch.setattr("src.auth.playwright_login.CREDENTIAL_FILE", cred_file)

        cookies = {"wt2": "abc"}
        data = json.dumps({"cookies": cookies, "saved_at": time.time()})
        cred_file.write_text(data, encoding="utf-8")

        check_status()
        output = capsys.readouterr().out
        assert "凭证不完整" in output
