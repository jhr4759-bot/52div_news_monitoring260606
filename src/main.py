"""뉴스 키워드 모니터링 - 엔트리포인트."""
import os
import sys
import html
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yaml  # noqa: E402
import crawler  # noqa: E402
import storage  # noqa: E402
import telegram_sender  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("news-monitor")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEYWORDS_PATH = os.path.join(ROOT, "keywords.yml")
SENT_PATH = os.path.join(ROOT, "sent_news.json")


def load_keywords(path: str) -> list:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        kws = [str(k).strip() for k in data.get("keywords", []) if str(k).strip()]
        logger.info("키워드 %d개 로드: %s", len(kws), ", ".join(kws))
        return kws
    except Exception as e:
        logger.error("키워드 로드 실패 (%s)", e)
        return []


def build_message(new_items: list) -> str:
    by_kw = {}
    for it in new_items:
        by_kw.setdefault(it["keyword"], []).append(it)

    lines = ["\U0001F4F0 <b>뉴스 키워드 모니터링</b>"]
    for kw, items in by_kw.items():
        lines.append(f"\n\U0001F50E <b>{html.escape(kw)}</b> ({len(items)}건)")
        for it in items:
            title = html.escape(it["title"])
            lines.append(f"\u2022 [{it['source']}] <a href=\"{it['url']}\">{title}</a>")
    return "\n".join(lines)


def main() -> int:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        logger.error("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 가 설정되지 않았습니다.")
        return 1

    keywords = load_keywords(KEYWORDS_PATH)
    if not keywords:
        logger.warning("키워드가 없어 종료합니다.")
        return 0

    sent = storage.load_sent(SENT_PATH)
    new_items = []

    for kw in keywords:
        try:
            items = crawler.search_all(kw)
        except Exception as e:
            logger.warning("'%s' 검색 중 오류, 건너뜀 (%s)", kw, e)
            continue
        for it in items:
            if storage.is_sent(it["url"], sent):
                continue
            new_items.append(it)
            storage.mark_sent(it["url"], sent)

    logger.info("새 기사 총 %d건", len(new_items))

    if not new_items:
        logger.info("새 뉴스가 없어 알림을 전송하지 않습니다.")
        return 0

    message = build_message(new_items)
    if telegram_sender.send_message(token, chat_id, message):
        storage.save_sent(sent, SENT_PATH)
        logger.info("완료: sent_news.json 갱신됨")
        return 0

    logger.error("전송 실패 -> sent_news.json 갱신 안 함 (다음 실행 때 재시도)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
