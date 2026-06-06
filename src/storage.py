"""중복 전송 방지를 위한 저장소 모듈.

전송한 기사 URL을 SHA-1 해시로 저장해 다음 실행 때 새 기사만 골라낸다.
파일이 없거나 깨져 있어도 빈 집합으로 시작해 실행이 멈추지 않도록 한다.
"""
import json
import os
import hashlib
import logging

logger = logging.getLogger(__name__)

# 무한 증가 방지: 가장 최근 N개만 보관
MAX_STORED = 5000


def _hash_url(url: str) -> str:
    return hashlib.sha1(url.strip().encode("utf-8")).hexdigest()


def load_sent(path: str = "sent_news.json") -> set:
    """이미 전송한 URL 해시 집합을 반환한다."""
    if not os.path.exists(path):
        logger.info("storage: %s 없음 -> 빈 상태로 시작", path)
        return set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        urls = data.get("urls", [])
        logger.info("storage: 기존 전송 기록 %d건 로드", len(urls))
        return set(urls)
    except Exception as e:
        logger.warning("storage: %s 로드 실패(%s) -> 빈 상태로 시작", path, e)
        return set()


def is_sent(url: str, sent: set) -> bool:
    return _hash_url(url) in sent


def mark_sent(url: str, sent: set) -> None:
    sent.add(_hash_url(url))


def save_sent(sent: set, path: str = "sent_news.json") -> None:
    try:
        urls = list(sent)
        if len(urls) > MAX_STORED:
            urls = urls[-MAX_STORED:]
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"urls": urls}, f, ensure_ascii=False, indent=2)
        logger.info("storage: 전송 기록 %d건 저장", len(urls))
    except Exception as e:
        logger.error("storage: %s 저장 실패(%s)", path, e)
