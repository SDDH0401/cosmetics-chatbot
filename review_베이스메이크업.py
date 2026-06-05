"""
출력: reviews_베이스메이크업.csv
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import re
import time
import pandas as pd

CATEGORY_NAME = "베이스메이크업"
CATEGORY_URL = "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do?dispCatNo=100000100020001"
PRODUCT_LIMIT = 20
REVIEW_LIMIT = 10


def collect_product_ids(driver, limit=20):
    print(f"\n[1단계] {CATEGORY_NAME} TOP {limit} 수집")
    driver.get(CATEGORY_URL)
    time.sleep(10)

    driver.execute_script("window.scrollTo(0, 1500);")
    time.sleep(2)
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    product_ids = []
    for a in soup.find_all("a", href=True):
        m = re.search(r"goodsNo=(\w+)", a["href"])
        if m and m.group(1) not in product_ids:
            product_ids.append(m.group(1))

    print(f"  → {len(product_ids)}개 발견, 상위 {limit}개 사용")
    return product_ids[:limit]


def crawl_reviews(driver, goods_no, rank, limit=10):
    url = f"https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo={goods_no}&tab=review"
    print(f"  [{rank}위 / {goods_no}]", end=" ")
    driver.get(url)
    time.sleep(8)

    for _ in range(5):
        driver.execute_script("window.scrollBy(0, 1500);")
        time.sleep(2)

    product_name = driver.execute_script("""
        const el = document.querySelector('title');
        return el ? el.textContent.replace('| 올리브영', '').trim() : '';
    """)

    result = driver.execute_script("""
        function deepQuerySelectorAll(selector, root) {
            const results = [];
            function recurse(node) {
                if (node.querySelectorAll) {
                    for (let m of node.querySelectorAll(selector)) results.push(m);
                }
                const all = node.querySelectorAll ? node.querySelectorAll('*') : [];
                for (let el of all) {
                    if (el.shadowRoot) recurse(el.shadowRoot);
                }
            }
            recurse(root);
            return results;
        }

        const items = deepQuerySelectorAll('oy-review-review-item', document);
        const data = [];
        const maxCount = Math.min(items.length, arguments[0]);

        for (let i = 0; i < maxCount; i++) {
            const item = items[i];
            const innerShadow = item.shadowRoot;
            if (!innerShadow) continue;
            const inner = innerShadow.querySelector('div.inner');
            if (!inner) continue;

            const stars = inner.querySelectorAll('div.rating oy-review-star-icon');
            const rating = stars.length;

            const contentHost = inner.querySelector('oy-review-review-content');
            let content = '';
            if (contentHost && contentHost.shadowRoot) {
                const candidates = ['div.content', 'div.text', 'div.review-text', 'p', 'div.inner'];
                for (let sel of candidates) {
                    const el = contentHost.shadowRoot.querySelector(sel);
                    if (el && el.textContent.trim()) {
                        content = el.textContent.trim();
                        break;
                    }
                }
            }
            content = content.replace(/\\s+/g, ' ').trim();
            data.push({rating: rating, content: content});
        }
        return {total: items.length, data: data};
    """, limit)

    print(f"리뷰 {len(result['data'])}개")

    for r in result['data']:
        r["category"] = CATEGORY_NAME
        r["product_name"] = product_name

    return result['data']


def main():
    options = Options()
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(options=options)

    try:
        start = time.time()
        product_ids = collect_product_ids(driver, limit=PRODUCT_LIMIT)
        if not product_ids:
            print("❌ 제품 ID 없음")
            return

        all_reviews = []
        for idx, goods_no in enumerate(product_ids, start=1):
            try:
                reviews = crawl_reviews(driver, goods_no, rank=idx, limit=REVIEW_LIMIT)
                all_reviews.extend(reviews)
                if idx % 5 == 0 and all_reviews:
                    df_temp = pd.DataFrame(all_reviews)
                    df_temp = df_temp[df_temp["content"].str.len() > 0]
                    df_temp = df_temp[["category", "product_name", "rating", "content"]]
                    df_temp.to_csv(f"reviews_{CATEGORY_NAME}.csv", index=False, encoding="utf-8-sig")
                    print(f"    💾 중간 저장: {len(df_temp)}개 누적")
            except Exception as e:
                print(f"    ❌ 에러: {e}")
                continue

        if all_reviews:
            df = pd.DataFrame(all_reviews)
            df = df[df["content"].str.len() > 0]
            df = df[["category", "product_name", "rating", "content"]]
            save_path = f"reviews_{CATEGORY_NAME}.csv"
            df.to_csv(save_path, index=False, encoding="utf-8-sig")
            elapsed = time.time() - start
            print(f"\n{'='*60}")
            print(f"✅ 완료!")
            print(f"   파일: {save_path}")
            print(f"   리뷰 수: {len(df)}개")
            print(f"   소요 시간: {elapsed:.0f}초 ({elapsed/60:.1f}분)")
        else:
            print("\n❌ 리뷰 0개")

    finally:
        input("\n엔터 누르면 종료...")
        driver.quit()


if __name__ == "__main__":
    main()
    