"""뉴스 수집 모듈.

- 네이버: 검색 결과 페이지 스크래핑 (API 키 불필요, 최신순)
- 구글: 구글 뉴스 RSS (한국어/한국 지역)

두 소스 모두 실패해도 예외를 던지지 않고 빈 리스트를 돌려줘서
전체 실행이 멈추지 않도록 한다. (요구사항: 오류 발생 시 계속 진행)
"""
import logging
import urllib.parse

import requests
import feedparser
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
TIMEOUT = 10


def search_naver_news(keyword: str, limit: int = 10) -> list:
    """네이버 뉴스 검색 결과 스크래핑. sort=1은 최신순."""
    results = []
    try:
        q = urllib.parse.quote(keyword)
        url = f"https://search.naver.com/search.naver?where=news&query={q}&sort=1"
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        anchors = soup.select("a.news_tit")
        if not anchors:
            anchors = soup.select(
                ".news_area a.news_tit, "
                "a[class*='headline'], "
                ".sds-comps-vertical-layout a[href^='http']"
            )

        seen = set()
        for a in anchors:
            title = (a.get("title") or a.get_text(strip=True) or "").strip()
            link = (a.get("href") or "").strip()
            if not title or not link or link in seen:
                continue
            seen.add(link)
            results.append({
                "title": title,
                "url": link,
                "source": "네이버",
                "keyword": keyword,
            })
            if len(results) >= limit:
                break
        logger.info("naver: '%s' -> %d건", keyword, len(results))
    except Exception as e:
        logger.warning("naver: '%s' 검색 실패 (%s)", keyword, e)
    return results


def search_google_news(keyword: str, limit: int = 10) -> list:
    """구글 뉴스 RSS 검색."""
    results = []
    try:
        q = urllib.parse.quote(keyword)
        url = f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
        feed = feedparser.parse(url, request_headers=HEADERS)
        for entry in feed.entries[:limit]:
            title = (getattr(entry, "title", "") or "").strip()
            link = (getattr(entry, "link", "") or "").strip()
            if title and link:
                results.append({
                    "title": title,
                    "url": link,
                    "source": "구글뉴스",
                    "keyword": keyword,
                })
        logger.info("google: '%s' -> %d건", keyword, len(results))
    except Exception as e:
        logger.warning("google: '%s' 검색 실패 (%s)", keyword, e)
    return results


def search_all(keyword: str) -> list:
    """두 소스를 합치고 같은 실행 내 URL 중복을 제거한다."""
    items = []
    items.extend(search_naver_news(keyword))
    items.extend(search_google_news(keyword))

    seen = set()
    deduped = []
    for it in items:
        if it["url"] in seen:
            continue
        seen.add(it["url"])
        deduped.append(it)
    return deduped
