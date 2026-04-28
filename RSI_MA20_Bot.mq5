//+------------------------------------------------------------------+
//| RSI_MA20_Bot.mq5 — FTMO Demo Challenge                          |
//| אסטרטגיה: RSI(14) + MA20 על M15                                 |
//| LONG: RSI<30 | SHORT: RSI>70 | ריסק: 1% לעסקה                  |
//+------------------------------------------------------------------+
#property copyright "RSI Bot"
#property version   "1.00"
#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>

//--- פרמטרים
input double InpRisk         = 1.0;    // ריסק לעסקה (%)
input int    InpRSIPeriod    = 14;     // RSI Period
input int    InpMAPeriod     = 20;     // MA Period
input int    InpSLPips       = 30;     // Stop Loss (pips)
input double InpMaxDailyLoss = 4.5;   // מקסימום הפסד יומי (%) — FTMO
input double InpMaxDrawdown  = 9.0;   // מקסימום drawdown (%) — FTMO
input int    InpMagic        = 202600; // Magic Number

CTrade        trade;
CPositionInfo pos;

double g_InitialBalance  = 0;
double g_DailyBalance    = 0;
datetime g_LastDay       = 0;

//+------------------------------------------------------------------+
int OnInit()
{
    trade.SetExpertMagicNumber(InpMagic);
    trade.SetDeviationInPoints(20);
    trade.SetTypeFilling(ORDER_FILLING_IOC);

    g_InitialBalance = AccountInfoDouble(ACCOUNT_BALANCE);
    g_DailyBalance   = g_InitialBalance;
    g_LastDay        = TimeCurrent();

    Print("=== RSI+MA20 Bot מופעל ===");
    Print("בלנס: ", g_InitialBalance, " | ריסק: ", InpRisk, "% | FTMO guard: ", InpMaxDailyLoss, "%/", InpMaxDrawdown, "%");
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| בדיקת חוקי FTMO                                                  |
//+------------------------------------------------------------------+
bool FTMOGuard()
{
    double balance = AccountInfoDouble(ACCOUNT_BALANCE);
    double equity  = AccountInfoDouble(ACCOUNT_EQUITY);

    // איפוס יומי
    MqlDateTime now, last;
    TimeToStruct(TimeCurrent(), now);
    TimeToStruct(g_LastDay, last);
    if(now.day != last.day)
    {
        g_DailyBalance = balance;
        g_LastDay      = TimeCurrent();
        Print("יום חדש — בלנס יומי מאופס: ", g_DailyBalance);
    }

    // הפסד יומי
    double dailyLoss = (g_DailyBalance - equity) / g_InitialBalance * 100.0;
    if(dailyLoss >= InpMaxDailyLoss)
    {
        Print("FTMO STOP: הפסד יומי ", DoubleToString(dailyLoss,2), "% — לא סוחרים היום!");
        return false;
    }

    // מקסימום drawdown
    double dd = (g_InitialBalance - equity) / g_InitialBalance * 100.0;
    if(dd >= InpMaxDrawdown)
    {
        Print("FTMO STOP: Drawdown ", DoubleToString(dd,2), "% — עוצר הבוט!");
        return false;
    }

    return true;
}

//+------------------------------------------------------------------+
//| חישוב lot size לפי % ריסק                                        |
//+------------------------------------------------------------------+
double CalcLot(string sym, int slPips)
{
    double balance    = AccountInfoDouble(ACCOUNT_BALANCE);
    double riskMoney  = balance * InpRisk / 100.0;
    double point      = SymbolInfoDouble(sym, SYMBOL_POINT);
    double tickVal    = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
    double tickSz     = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
    int    digits     = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);

    double slDist = slPips * point * (digits == 3 || digits == 5 ? 10 : 1);
    if(tickSz == 0 || tickVal == 0) return SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);

    double lot = riskMoney / (slDist / tickSz * tickVal);

    double minL = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
    double maxL = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
    double step = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
    lot = MathRound(lot / step) * step;
    return MathMax(minL, MathMin(maxL, lot));
}

//+------------------------------------------------------------------+
//| בדיקה אם יש פוזיציה פתוחה                                        |
//+------------------------------------------------------------------+
bool HasPosition(string sym)
{
    for(int i = PositionsTotal()-1; i >= 0; i--)
        if(pos.SelectByIndex(i) && pos.Symbol() == sym && pos.Magic() == InpMagic)
            return true;
    return false;
}

//+------------------------------------------------------------------+
//| לוגיקת כניסה                                                     |
//+------------------------------------------------------------------+
void CheckSignal(string sym)
{
    if(HasPosition(sym)) return;

    int hRSI = iRSI(sym, PERIOD_M15, InpRSIPeriod, PRICE_CLOSE);
    int hMA  = iMA (sym, PERIOD_M15, InpMAPeriod,  0, MODE_SMA, PRICE_CLOSE);
    if(hRSI == INVALID_HANDLE || hMA == INVALID_HANDLE) return;

    double rsi[], ma[];
    ArraySetAsSeries(rsi, true);
    ArraySetAsSeries(ma,  true);
    if(CopyBuffer(hRSI, 0, 0, 3, rsi) < 3) { IndicatorRelease(hRSI); IndicatorRelease(hMA); return; }
    if(CopyBuffer(hMA,  0, 0, 3, ma)  < 3) { IndicatorRelease(hRSI); IndicatorRelease(hMA); return; }

    int    digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
    double point  = SymbolInfoDouble(sym, SYMBOL_POINT);
    double mult   = (digits == 3 || digits == 5) ? 10.0 : 1.0;
    double slDist = InpSLPips * point * mult;
    double tpDist = slDist * 2.0;   // R:R 1:2
    double lot    = CalcLot(sym, InpSLPips);

    double rsiVal = rsi[1];
    double price  = SymbolInfoDouble(sym, SYMBOL_BID);

    // ── LONG ─────────────────────────────────────────────
    if(rsiVal < 30)
    {
        double ask = SymbolInfoDouble(sym, SYMBOL_ASK);
        double sl  = NormalizeDouble(ask - slDist, digits);
        double tp  = NormalizeDouble(ask + tpDist, digits);
        if(trade.Buy(lot, sym, ask, sl, tp, "RSI-Bot LONG"))
            Print("LONG  ", sym, " | RSI:", DoubleToString(rsiVal,1), " | lot:", lot, " | SL:", sl, " | TP:", tp);
        else
            Print("FAIL LONG  ", sym, " | error:", trade.ResultRetcode(), " - ", trade.ResultRetcodeDescription());
    }
    // ── SHORT ────────────────────────────────────────────
    else if(rsiVal > 70)
    {
        double bid = SymbolInfoDouble(sym, SYMBOL_BID);
        double sl  = NormalizeDouble(bid + slDist, digits);
        double tp  = NormalizeDouble(bid - tpDist, digits);
        if(trade.Sell(lot, sym, bid, sl, tp, "RSI-Bot SHORT"))
            Print("SHORT ", sym, " | RSI:", DoubleToString(rsiVal,1), " | lot:", lot, " | SL:", sl, " | TP:", tp);
        else
            Print("FAIL SHORT ", sym, " | error:", trade.ResultRetcode(), " - ", trade.ResultRetcodeDescription());
    }

    IndicatorRelease(hRSI);
    IndicatorRelease(hMA);
}

//+------------------------------------------------------------------+
//| OnTick — רץ על כל תנועת מחיר, מבדיק נר חדש בלבד                |
//+------------------------------------------------------------------+
void OnTick()
{
    static datetime lastBar = 0;
    datetime curBar = iTime(_Symbol, PERIOD_M15, 0);
    if(curBar == lastBar) return;
    lastBar = curBar;

    if(!FTMOGuard()) return;
    CheckSignal(_Symbol);
}
//+------------------------------------------------------------------+
