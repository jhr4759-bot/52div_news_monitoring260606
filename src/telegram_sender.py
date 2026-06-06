"""Telegram Bot 전송 모듈.

메시지가 길면 텔레그램 한도(4096자) 안쪽으로 나눠 보낸다.
하나라도 실패하면 False를 반환해 호출 측에서 저장을 보류할 수 있게 한다.
"""
import logging

import requests

logger = logging.getLogger(__name__)

API = "https://api.telegram.org/bot{token}/sendMessage"
MAX_LEN = 3500  # 4096 한도보다 여유 있게


def _chunks(text: str, size: int = MAX_LEN):
    buf = ""
    for line in text.split("\n"):
        if len(buf) + len(line) + 1 > size:
            if buf:
                yield buf
            buf = line
        else:
            buf = f"{buf}\n{line}" if buf else line
    if buf:
        yield buf


def send_message(token: str, chat_id: str, text: str) -> bool:
    ok = True
    for chunk in _chunks(text):
        try:
            resp = requests.post(
                API.format(token=token),
                data={
                    "chat_id": chat_id,
                    "text": chunk,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=15,
            )
            if resp.status_code != 200:
                logger.error("telegram: 전송 실패 %s %s", resp.status_code, resp.text)
                ok = False
            else:
                logger.info("telegram: 전송 성공 (%d자)", len(chunk))
        except Exception as e:
            logger.error("telegram: 예외 (%s)", e)
            ok = False
    return ok
