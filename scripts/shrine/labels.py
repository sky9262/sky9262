"""Every fixed string the live cards (千本鳥居 · 活動) can render, in both languages.

`python -m scripts.build` subsets the runtime fonts from these values (plus
printable ASCII), so any glyph a live card draws must appear here. Rebuild the
runtime fonts after editing this file.
"""
from __future__ import annotations

LABELS: dict[str, dict[str, str]] = {
    # ---- torii path (千本鳥居)
    "torii_title": {"jp": "千本鳥居", "en": "Torii Path"},
    "torii_caption": {"jp": "鳥居一基＝一週間の貢献", "en": "one gate for each week · 千本鳥居"},
    # the calendar covers the last 365 days, not the calendar year
    "torii_total": {"jp": "過去1年の貢献", "en": "contributions in the last year"},
    "torii_peak": {"jp": "最多の週", "en": "busiest week"},
    "torii_now": {"jp": "今週", "en": "this week"},
    # month names, comma separated, January first
    "months": {
        "jp": "1月,2月,3月,4月,5月,6月,7月,8月,9月,10月,11月,12月",
        "en": "Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec",
    },
    # ---- this week (今週の参拝): one omikuji per day
    "week_title": {"jp": "今週の参拝", "en": "This week"},
    "week_caption": {"jp": "おみくじ一枚＝一日の貢献", "en": "one omikuji for each day"},
    "week_total": {"jp": "今週の貢献", "en": "contributions"},
    "week_today": {"jp": "今日", "en": "today"},
    "weekdays": {"jp": "月,火,水,木,金,土,日", "en": "Mon,Tue,Wed,Thu,Fri,Sat,Sun"},
    # fortune seals by tier, lowest first (0, 1-9, 10-29, 30-49, 50+); kind: 休 = rest
    "fortune_tiers": {"jp": "休,小吉,中吉,吉,大吉", "en": "休,小吉,中吉,吉,大吉"},
    # never looked up by key: it is here so "…" lands in the runtime font subset
    # (live.fit / _fit_w cut long language names on the ensō and hours cards with it)
    "ellipsis": {"jp": "…", "en": "…"},
    # ---- stat plaques
    "stat_contrib": {"jp": "過去1年の貢献", "en": "Contributions"},
    "stat_contrib_sub": {"jp": "非公開の仕事も含む", "en": "in the last year · incl. private"},
    "stat_month": {"jp": "直近30日の貢献", "en": "Last 30 days"},
    "stat_month_sub": {"jp": "1日平均 {avg}", "en": "avg {avg} a day"},
    "stat_peak": {"jp": "最も熱い一日", "en": "Busiest day"},
    "stat_peak_sub": {"jp": "{y}年{m}月{d}日", "en": "{mon} {d}, {y}"},
    "stat_peak_none": {"jp": "これからの一日", "en": "still to come"},
    "stat_stars": {"jp": "獲得スター", "en": "Stars earned"},
    "stat_stars_sub": {"jp": "公開リポジトリ {n}件", "en": "across {n} public repos"},
    # ---- language ensō (円相)
    "enso_title": {"jp": "円相 · 使用言語", "en": "Languages · 円相"},
    "enso_note": {"jp": "公開リポジトリのコード量", "en": "by code size, public repos"},
    "enso_empty": {"jp": "まだ言語の記録がありません", "en": "No languages yet"},
    "other": {"jp": "その他", "en": "Other"},
    # ---- shrine hours (朝・昼・夕・夜)
    "hours_title": {"jp": "参拝の刻 · 時間帯", "en": "Shrine hours · 刻"},
    "public_commits": {"jp": "公開コミット", "en": "public commits"},
    "hours_note": {"jp": "日本時間", "en": "JST"},
    "hour_asa": {"jp": "朝", "en": "Morning"},
    "hour_hiru": {"jp": "昼", "en": "Day"},
    "hour_yu": {"jp": "夕", "en": "Evening"},
    "hour_yoru": {"jp": "夜", "en": "Night"},
    # JST ranges of the buckets above, in the order asa, hiru, yu, yoru
    "hour_ranges": {"jp": "5–11時,11–17時,17–21時,21–5時", "en": "5–11,11–17,17–21,21–5"},
    # the kanji shown as a seal beside every bucket, both languages
    "hour_kanji": {"jp": "朝昼夕夜", "en": "朝昼夕夜"},
}
