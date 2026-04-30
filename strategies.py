"""
STRATEGY DEFINITIONS — כל שורה = חשבון נפרד + אסטרטגיה שונה
"""

STRATEGIES = {

    # ── אסטרטגיה 1: RSI קלאסי + anti-trend (המקורית, שמרנית)
    "s1_classic": {
        "rsi_oversold":    30,
        "rsi_overbought":  70,
        "require_trend":   True,    # חייב price > MA50
        "anti_trend":      True,    # חוסם last3_bearish/bullish
        "rsi_direction":   True,    # חייב rsi_rising/rsi_falling
        "news_block":      True,
        "description":     "RSI Classic + Anti-trend (conservative)",
    },

    # ── אסטרטגיה 2: RSI רגיש יותר, בלי anti-trend
    "s2_aggressive": {
        "rsi_oversold":    35,
        "rsi_overbought":  65,
        "require_trend":   True,
        "anti_trend":      False,   # מאפשר כניסה נגד מומנטום קצר
        "rsi_direction":   True,
        "news_block":      True,
        "description":     "RSI Sensitive 35/65, no anti-trend",
    },

    # ── אסטרטגיה 3: Momentum בלבד — RSI בין 50-65 (bull) / 35-50 (bear)
    "s3_momentum": {
        "rsi_oversold":    50,      # לא oversold — momentum בלבד
        "rsi_overbought":  50,
        "rsi_bull_min":    52,      # LONG רק אם RSI > 52
        "rsi_bear_max":    48,      # SHORT רק אם RSI < 48
        "require_trend":   True,
        "anti_trend":      False,
        "rsi_direction":   True,
        "news_block":      True,
        "description":     "Momentum only — RSI 52-68 / 32-48",
    },

    # ── אסטרטגיה 4: בלי סינון RSI direction — כל signal תקין נכנס
    "s4_no_rsi_dir": {
        "rsi_oversold":    30,
        "rsi_overbought":  70,
        "require_trend":   True,
        "anti_trend":      True,
        "rsi_direction":   False,   # לא בודק כיוון RSI
        "news_block":      True,
        "description":     "Classic RSI no direction filter",
    },

    # ── אסטרטגיה 5: Trend-following אגרסיבי — RSI 40-75
    "s5_trend_follow": {
        "rsi_oversold":    40,
        "rsi_overbought":  60,
        "require_trend":   True,
        "anti_trend":      False,
        "rsi_direction":   False,
        "news_block":      False,   # גם בחדשות
        "description":     "Trend-following, wide RSI, no news block",
    },
}
