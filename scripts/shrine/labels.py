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
    "torii_total": {"jp": "今年の貢献", "en": "contributions this year"},
    "torii_peak": {"jp": "最多の週", "en": "busiest week"},
    "torii_now": {"jp": "今週", "en": "this week"},
    # month names, comma separated, January first
    "months": {
        "jp": "1月,2月,3月,4月,5月,6月,7月,8月,9月,10月,11月,12月",
        "en": "Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec",
    },
    # ---- feed (今日の参拝): omikuji slips
    "feed_title": {"jp": "今日の参拝 · 最近の活動", "en": "Recent activity · 今日の参拝"},
    "verb_push": {"jp": "プッシュ", "en": "Pushed to"},
    "verb_create": {"jp": "作成", "en": "Created"},
    "verb_release": {"jp": "リリース", "en": "Released"},
    "verb_star": {"jp": "スター", "en": "Starred"},
    "verb_fork": {"jp": "フォーク", "en": "Forked"},
    "verb_updated": {"jp": "更新", "en": "Updated"},
    "feed_empty": {"jp": "今宵の参道は静かです", "en": "A quiet night at the shrine"},
    "ago_now": {"jp": "たった今", "en": "just now"},
    "ago_hours": {"jp": "{n}時間前", "en": "{n}h ago"},
    "ago_days": {"jp": "{n}日前", "en": "{n}d ago"},
    # decorative fortune stamps on the slips (おみくじ)
    "fortunes": {"jp": "大吉,吉,中吉,小吉,末吉", "en": "大吉,吉,中吉,小吉,末吉"},
    "ellipsis": {"jp": "…", "en": "…"},
    # ---- stat plaques
    "stat_contrib": {"jp": "今年の貢献", "en": "Contributions"},
    "stat_contrib_sub": {"jp": "非公開の仕事も含む", "en": "this year · incl. private"},
    "stat_streak": {"jp": "連続の日数", "en": "Current streak"},
    "stat_streak_unit": {"jp": "日", "en": "days"},
    "stat_streak_unit_one": {"jp": "日", "en": "day"},
    "stat_streak_sub": {"jp": "最長 {n}日", "en": "longest {n} days"},
    "stat_stars": {"jp": "獲得スター", "en": "Stars earned"},
    "stat_stars_sub": {"jp": "公開リポジトリ {n}件", "en": "across {n} public repos"},
    "stat_followers": {"jp": "フォロワー", "en": "Followers"},
    "stat_followers_sub": {"jp": "GitHubでのご縁", "en": "connections on GitHub"},
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
