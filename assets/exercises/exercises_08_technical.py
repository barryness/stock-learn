"""
第八课配套实战代码：技术分析工具集
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import os

try:
    for font_name in ['PingFang SC', 'Heiti SC', 'STHeiti', 'Arial Unicode MS', 'SimHei']:
        try:
            fm.findfont(font_name, fallback_to_default=False)
            plt.rcParams['font.sans-serif'] = [font_name]
            break
        except Exception:
            continue
    plt.rcParams['axes.unicode_minus'] = False
except Exception:
    pass

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


# ============================================================
# 1. 生成模拟行情数据
# ============================================================

def generate_price_data(days=250, seed=42):
    """生成模拟的OHLCV数据 —— 模拟真实股票走势"""
    np.random.seed(seed)

    # 构建真实走势：趋势 + 周期 + 噪声
    t = np.arange(days)
    daily_drift = 0.0002  # 微弱的日常上涨漂移（年化~5%）
    cycle1 = 0.10 * np.sin(2 * np.pi * t / 63)   # 季度周期
    cycle2 = 0.05 * np.sin(2 * np.pi * t / 21)   # 月度周期
    trend_break = np.where(t > 180, -0.0003 * (t - 180), 0)  # 后期回调
    noise = np.random.normal(0, 0.012, days)

    log_returns = daily_drift + noise
    # 周期通过影响收益率而非累加产生真实起伏
    cycle_effect = np.diff(np.concatenate([[0], cycle1 + cycle2 + trend_break]))
    log_returns = log_returns + cycle_effect * 0.3
    prices = 10 * np.exp(np.cumsum(log_returns))

    daily_vol = 0.018
    opens = np.zeros(days)
    highs = np.zeros(days)
    lows = np.zeros(days)
    closes = prices.copy()
    volumes = np.zeros(days)

    for i in range(days):
        if i == 0:
            opens[i] = closes[i] * (1 + np.random.normal(0, daily_vol * 0.3))
        else:
            opens[i] = closes[i - 1] * (1 + np.random.normal(0, daily_vol * 0.3))
        daily_range = closes[i] * daily_vol * np.random.uniform(0.5, 1.5)
        highs[i] = max(opens[i], closes[i]) + abs(np.random.normal(0, daily_range * 0.3))
        lows[i] = min(opens[i], closes[i]) - abs(np.random.normal(0, daily_range * 0.3))
        base_vol = 8_000_000
        vol_factor = 1 + 3 * abs(log_returns[i]) + np.random.uniform(0, 0.4)
        volumes[i] = base_vol * vol_factor

    highs = np.maximum(highs, np.maximum(opens, closes))
    lows = np.minimum(lows, np.minimum(opens, closes))

    return {
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes,
        'days': days
    }


# ============================================================
# 2. 技术分析引擎
# ============================================================

class TechnicalAnalyzer:
    """技术指标计算与信号检测"""

    def __init__(self, data):
        self.data = data
        self.close = data['close']
        self.high = data['high']
        self.low = data['low']
        self.volume = data['volume']
        self.open = data['open']

        self.ma = {}
        self.signals = {}

    # ---- 均线 ----
    def calc_ma(self, periods=(5, 10, 20, 60, 120, 250)):
        for p in periods:
            self.ma[p] = np.full(len(self.close), np.nan)
            for i in range(p - 1, len(self.close)):
                self.ma[p][i] = np.mean(self.close[i - p + 1:i + 1])
        return self.ma

    def find_crossovers(self, fast=5, slow=20):
        """检测金叉死叉"""
        crosses = []
        for i in range(1, len(self.close)):
            if np.isnan(self.ma[fast][i]) or np.isnan(self.ma[slow][i]):
                continue
            if np.isnan(self.ma[fast][i - 1]) or np.isnan(self.ma[slow][i - 1]):
                continue

            prev_diff = self.ma[fast][i - 1] - self.ma[slow][i - 1]
            curr_diff = self.ma[fast][i] - self.ma[slow][i]

            if prev_diff <= 0 and curr_diff > 0:
                crosses.append((i, 'golden', self.close[i]))
            elif prev_diff >= 0 and curr_diff < 0:
                crosses.append((i, 'death', self.close[i]))

        self.signals[f'ma_{fast}_{slow}_cross'] = crosses
        return crosses

    def ma_arrangement(self):
        """判断均线排列状态"""
        n = len(self.close)
        arrangements = np.zeros(n, dtype=int)  # -1=空头, 0=交织, 1=多头

        for i in range(n):
            values = []
            for p in [5, 10, 20, 60]:
                if not np.isnan(self.ma[p][i]):
                    values.append(self.ma[p][i])
            if len(values) < 4:
                continue
            if values[0] > values[1] > values[2] > values[3]:
                arrangements[i] = 1
            elif values[0] < values[1] < values[2] < values[3]:
                arrangements[i] = -1

        self.signals['arrangement'] = arrangements
        return arrangements

    # ---- MACD ----
    def calc_macd(self, fast=12, slow=26, signal=9):
        """计算MACD指标"""
        ema_fast = self._ema(self.close, fast)
        ema_slow = self._ema(self.close, slow)
        dif = ema_fast - ema_slow
        dea = self._ema(dif, signal)
        macd_bar = 2 * (dif - dea)

        self.signals['macd_dif'] = dif
        self.signals['macd_dea'] = dea
        self.signals['macd_bar'] = macd_bar
        return dif, dea, macd_bar

    def find_macd_cross(self):
        """检测MACD金叉死叉"""
        dif = self.signals.get('macd_dif')
        dea = self.signals.get('macd_dea')
        if dif is None:
            self.calc_macd()
            dif = self.signals['macd_dif']
            dea = self.signals['macd_dea']

        crosses = []
        for i in range(1, len(dif)):
            prev = dif[i - 1] - dea[i - 1]
            curr = dif[i] - dea[i]
            if prev <= 0 and curr > 0:
                crosses.append((i, 'golden', self.close[i]))
            elif prev >= 0 and curr < 0:
                crosses.append((i, 'death', self.close[i]))

        self.signals['macd_cross'] = crosses
        return crosses

    def find_macd_divergence(self, window=30):
        """检测MACD背离"""
        dif = self.signals.get('macd_dif')
        if dif is None:
            self.calc_macd()
            dif = self.signals['macd_dif']

        divergences = []

        for i in range(window, len(self.close) - 1):
            # 顶背离：价格新高，DIF没新高
            recent_high_idx = np.argmax(self.close[i - window:i + 1]) + (i - window)
            prev_window = self.close[max(0, recent_high_idx - window * 2):recent_high_idx - window]
            if len(prev_window) < window:
                continue
            prev_high_idx = np.argmax(prev_window) + max(0, recent_high_idx - window * 2)

            if self.close[recent_high_idx] > self.close[prev_high_idx] and \
               dif[recent_high_idx] < dif[prev_high_idx] and \
               recent_high_idx == i:
                divergences.append((i, 'bearish', self.close[i]))

            # 底背离：价格新低，DIF没新低
            recent_low_idx = np.argmin(self.close[i - window:i + 1]) + (i - window)
            prev_window_low = self.close[max(0, recent_low_idx - window * 2):recent_low_idx - window]
            if len(prev_window_low) < window:
                continue
            prev_low_idx = np.argmin(prev_window_low) + max(0, recent_low_idx - window * 2)

            if self.close[recent_low_idx] < self.close[prev_low_idx] and \
               dif[recent_low_idx] > dif[prev_low_idx] and \
               recent_low_idx == i:
                divergences.append((i, 'bullish', self.close[i]))

        self.signals['macd_divergence'] = divergences
        return divergences

    # ---- RSI ----
    def calc_rsi(self, period=14):
        """计算RSI"""
        deltas = np.diff(self.close, prepend=self.close[0])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.full(len(self.close), np.nan)
        avg_loss = np.full(len(self.close), np.nan)

        # 第一个平均值用简单平均
        if period < len(gains):
            avg_gain[period] = np.mean(gains[1:period + 1])
            avg_loss[period] = np.mean(losses[1:period + 1])

        # 后续用平滑平均
        for i in range(period + 1, len(gains)):
            avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gains[i]) / period
            avg_loss[i] = (avg_loss[i - 1] * (period - 1) + losses[i]) / period

        rsi = np.full(len(self.close), np.nan)
        for i in range(len(rsi)):
            if not np.isnan(avg_gain[i]) and not np.isnan(avg_loss[i]):
                if avg_loss[i] == 0:
                    rsi[i] = 100
                else:
                    rs = avg_gain[i] / avg_loss[i]
                    rsi[i] = 100 - 100 / (1 + rs)

        self.signals[f'rsi_{period}'] = rsi
        return rsi

    # ---- KDJ ----
    def calc_kdj(self, n=9, m1=3, m2=3):
        """计算KDJ指标"""
        k = np.full(len(self.close), np.nan)
        d = np.full(len(self.close), np.nan)
        j = np.full(len(self.close), np.nan)

        for i in range(n - 1, len(self.close)):
            high_n = np.max(self.high[i - n + 1:i + 1])
            low_n = np.min(self.low[i - n + 1:i + 1])
            rsv = (self.close[i] - low_n) / (high_n - low_n) * 100 if high_n != low_n else 50

            if i == n - 1:
                k[i] = 50
                d[i] = 50
            else:
                k[i] = (m1 - 1) / m1 * k[i - 1] + 1 / m1 * rsv
                d[i] = (m2 - 1) / m2 * d[i - 1] + 1 / m2 * k[i]
            j[i] = 3 * k[i] - 2 * d[i]

        self.signals['kdj_k'] = k
        self.signals['kdj_d'] = d
        self.signals['kdj_j'] = j
        return k, d, j

    def find_kdj_cross(self):
        """检测KDJ金叉死叉"""
        k = self.signals.get('kdj_k')
        d = self.signals.get('kdj_d')
        if k is None:
            self.calc_kdj()
            k = self.signals['kdj_k']
            d = self.signals['kdj_d']

        crosses = []
        for i in range(1, len(k)):
            if np.isnan(k[i]) or np.isnan(d[i]):
                continue
            prev = k[i - 1] - d[i - 1]
            curr = k[i] - d[i]
            if prev <= 0 and curr > 0:
                crosses.append((i, 'golden', self.close[i]))
            elif prev >= 0 and curr < 0:
                crosses.append((i, 'death', self.close[i]))

        self.signals['kdj_cross'] = crosses
        return crosses

    # ---- 成交量分析 ----
    def calc_volume_ma(self, period=20):
        vm = np.full(len(self.volume), np.nan)
        for i in range(period - 1, len(self.volume)):
            vm[i] = np.mean(self.volume[i - period + 1:i + 1])
        self.signals[f'volume_ma_{period}'] = vm
        return vm

    def volume_analysis(self):
        """量价关系分析"""
        n = len(self.close)
        vm20 = self.calc_volume_ma(20)
        analysis = np.zeros(n, dtype=int)  # -1=缩量, 0=正常, 1=放量

        for i in range(20, n):
            if self.volume[i] > vm20[i] * 1.5:
                if self.close[i] > self.close[i - 1]:
                    analysis[i] = 2  # 放量上涨
                else:
                    analysis[i] = -2  # 放量下跌
            elif self.volume[i] < vm20[i] * 0.5:
                analysis[i] = -1  # 缩量

        self.signals['volume_analysis'] = analysis
        return analysis

    def calc_obv(self):
        """计算OBV能量潮"""
        obv = np.zeros(len(self.close))
        obv[0] = self.volume[0]
        for i in range(1, len(self.close)):
            if self.close[i] > self.close[i - 1]:
                obv[i] = obv[i - 1] + self.volume[i]
            elif self.close[i] < self.close[i - 1]:
                obv[i] = obv[i - 1] - self.volume[i]
            else:
                obv[i] = obv[i - 1]
        self.signals['obv'] = obv
        return obv

    # ---- 支撑/压力位 ----
    def find_support_resistance(self, window=20, threshold=0.03):
        """检测支撑和压力位"""
        supports = []
        resistances = []

        for i in range(window, len(self.close) - window):
            # 局部低点 → 支撑
            if self.low[i] == np.min(self.low[i - window:i + window + 1]):
                # 合并相近的支撑位
                price = self.low[i]
                if not supports or min(abs(price - s) / s for s in supports) > threshold:
                    supports.append(price)

            # 局部高点 → 压力
            if self.high[i] == np.max(self.high[i - window:i + window + 1]):
                price = self.high[i]
                if not resistances or min(abs(price - r) / r for r in resistances) > threshold:
                    resistances.append(price)

        return {'supports': sorted(supports), 'resistances': sorted(resistances)}

    # ---- 综合信号系统 ----
    def composite_signal(self):
        """四级共振信号系统"""
        n = len(self.close)
        self.calc_ma()
        self.calc_macd()
        rsi14 = self.calc_rsi(14)
        kdj_k, kdj_d, kdj_j = self.calc_kdj()
        vol_analysis = self.volume_analysis()
        arrangement = self.ma_arrangement()

        signals = np.zeros(n, dtype=int)  # -2=强卖, -1=弱卖, 0=观望, 1=弱买, 2=强买
        scores = np.zeros(n)

        for i in range(60, n):
            score = 0
            # 一级：趋势
            if arrangement[i] == 1:
                score += 2
            elif arrangement[i] == -1:
                score -= 2
            # 价格与MA60关系
            if not np.isnan(self.ma[60][i]):
                if self.close[i] > self.ma[60][i]:
                    score += 1
                else:
                    score -= 1

            # 二级：位置
            if not np.isnan(rsi14[i]):
                if rsi14[i] < 30:
                    score += 1.5
                elif rsi14[i] > 70:
                    score -= 1.5
                elif 40 < rsi14[i] < 60:
                    score += 0

            if not np.isnan(kdj_k[i]) and not np.isnan(kdj_d[i]):
                if kdj_k[i] < 20 and kdj_d[i] < 20:
                    score += 1
                elif kdj_k[i] > 80 and kdj_d[i] > 80:
                    score -= 1

            # 三级：信号
            if i >= 1:
                dif = self.signals['macd_dif']
                dea = self.signals['macd_dea']
                prev_m = dif[i - 1] - dea[i - 1]
                curr_m = dif[i] - dea[i]
                if prev_m <= 0 and curr_m > 0:
                    score += 1
                elif prev_m >= 0 and curr_m < 0:
                    score -= 1

                prev_k = kdj_k[i - 1] - kdj_d[i - 1]
                curr_k = kdj_k[i] - kdj_d[i]
                if not np.isnan(prev_k) and not np.isnan(curr_k):
                    if prev_k <= 0 and curr_k > 0:
                        score += 0.5
                    elif prev_k >= 0 and curr_k < 0:
                        score -= 0.5

            # 四级：量能
            if vol_analysis[i] == 2:
                score += 1
            elif vol_analysis[i] == -2:
                score -= 1

            scores[i] = score
            if score >= 3:
                signals[i] = 2
            elif score >= 1.5:
                signals[i] = 1
            elif score <= -3:
                signals[i] = -2
            elif score <= -1.5:
                signals[i] = -1

        self.signals['composite'] = signals
        self.signals['composite_score'] = scores
        return signals, scores

    # ---- 工具方法 ----
    def _ema(self, data, period):
        ema = np.full(len(data), np.nan)
        # 找到第一个可用的非NaN起始位置
        valid_from = period - 1
        while valid_from < len(data) and np.isnan(data[valid_from]):
            valid_from += 1
        if valid_from >= len(data):
            return ema
        # 用第一个有效位置前period个非NaN值的均值初始化
        valid_data = data[:valid_from + 1]
        valid_vals = valid_data[~np.isnan(valid_data)]
        if len(valid_vals) >= period:
            ema[valid_from] = np.mean(valid_vals[-period:])
        elif len(valid_vals) > 0:
            ema[valid_from] = np.mean(valid_vals)
        multiplier = 2 / (period + 1)
        for i in range(valid_from + 1, len(data)):
            if np.isnan(data[i]):
                ema[i] = ema[i - 1]
            else:
                ema[i] = (data[i] - ema[i - 1]) * multiplier + ema[i - 1]
        return ema


# ============================================================
# 3. 演示函数
# ============================================================

def demo_ma_system(analyzer):
    """演示均线系统"""
    print("\n" + "=" * 60)
    print("  均线系统分析")
    print("=" * 60)

    analyzer.calc_ma()
    golden_death = analyzer.find_crossovers(5, 20)
    arrangement = analyzer.ma_arrangement()

    recent_arr = arrangement[-60:]
    bull_days = np.sum(recent_arr == 1)
    bear_days = np.sum(recent_arr == -1)
    neutral_days = np.sum(recent_arr == 0)

    print(f"\n  近60个交易日:")
    print(f"    多头排列：{bull_days} 天")
    print(f"    空头排列：{bear_days} 天")
    print(f"    均线交织：{neutral_days} 天")

    print(f"\n  最近10个交叉信号:")
    for cross in golden_death[-10:]:
        idx, ctype, price = cross
        label = '金叉 ✨' if ctype == 'golden' else '死叉 ⚠️'
        print(f"    第{idx:>3}天  MA5{'>MA20' if ctype == 'golden' else '<MA20'}  {label}  价格:{price:.2f}")

    # 当前状态
    last = len(analyzer.close) - 1
    print(f"\n  当前状态 (第{last}天, 收盘{analyzer.close[last]:.2f}):")
    for p in [5, 10, 20, 60, 120]:
        if not np.isnan(analyzer.ma[p][last]):
            above = "↑ 在均线上方" if analyzer.close[last] > analyzer.ma[p][last] else "↓ 在均线下方"
            print(f"    MA{p:<3}: {analyzer.ma[p][last]:.2f}  {above}")


def demo_macd(analyzer):
    """演示MACD指标"""
    print("\n" + "=" * 60)
    print("  MACD指标分析")
    print("=" * 60)

    dif, dea, bar = analyzer.calc_macd()
    crosses = analyzer.find_macd_cross()
    divergences = analyzer.find_macd_divergence()

    last = len(analyzer.close) - 1
    print(f"\n  最新MACD值 (第{last}天):")
    print(f"    DIF: {dif[last]:.4f}")
    print(f"    DEA: {dea[last]:.4f}")
    print(f"    MACD柱: {bar[last]:.4f}")
    zero_status = "零轴上方（多头区域）" if dif[last] > 0 else "零轴下方（空头区域）"
    print(f"    状态：{zero_status}")
    bar_status = "红柱（动能↑）" if bar[last] > 0 else "绿柱（动能↓）"
    print(f"          {bar_status}")

    print(f"\n  最近MACD交叉:")
    for cross in crosses[-5:]:
        idx, ctype, price = cross
        zone = "零轴上" if dif[idx] > 0 else "零轴下"
        label = '金叉' if ctype == 'golden' else '死叉'
        print(f"    第{idx:>3}天  {label} (强度: {zone})  价格:{price:.2f}")

    if divergences:
        print(f"\n  检测到背离信号:")
        for div in divergences:
            idx, dtype, price = div
            label = '顶背离（看跌）⚠️' if dtype == 'bearish' else '底背离（看涨）✨'
            print(f"    第{idx:>3}天  {label}  价格:{price:.2f}")
    else:
        print(f"\n  近期未检测到明显背离信号")


def demo_rsi_kdj(analyzer):
    """演示RSI和KDJ"""
    print("\n" + "=" * 60)
    print("  RSI & KDJ 摆动指标分析")
    print("=" * 60)

    rsi14 = analyzer.calc_rsi(14)
    k, d, j = analyzer.calc_kdj()
    kdj_crosses = analyzer.find_kdj_cross()

    last = len(analyzer.close) - 1

    print(f"\n  RSI(14)最新值: {rsi14[last]:.1f}")
    if rsi14[last] > 70:
        print(f"    → 超买区域（>70），短期过热，不宜追高")
    elif rsi14[last] < 30:
        print(f"    → 超卖区域（<30），短期过冷，不宜杀跌")
    elif 40 <= rsi14[last] <= 60:
        print(f"    → 中性区域（40-60），无明确信号")
    else:
        print(f"    → 中间区域，需结合趋势判断")

    print(f"\n  KDJ最新值:")
    print(f"    K: {k[last]:.1f}  |  D: {d[last]:.1f}  |  J: {j[last]:.1f}")
    k_status = "超买" if k[last] > 80 else ("超卖" if k[last] < 20 else "正常")
    d_status = "超买" if d[last] > 80 else ("超卖" if d[last] < 20 else "正常")
    j_status = "极度超买" if j[last] > 100 else ("极度超卖" if j[last] < 0 else "正常")
    print(f"    K状态: {k_status}  |  D状态: {d_status}  |  J状态: {j_status}")

    print(f"\n  最近KDJ交叉:")
    for cross in kdj_crosses[-5:]:
        idx, ctype, price = cross
        zone_label = ''
        if k[idx] < 20 and d[idx] < 20:
            zone_label = '(超卖区→强信号)'
        elif k[idx] > 80 and d[idx] > 80:
            zone_label = '(超买区→强信号)'
        label = '金叉' if ctype == 'golden' else '死叉'
        print(f"    第{idx:>3}天  {label} {zone_label}  价格:{price:.2f}")


def demo_volume(analyzer):
    """演示成交量分析"""
    print("\n" + "=" * 60)
    print("  成交量与量价分析")
    print("=" * 60)

    vol_analysis = analyzer.volume_analysis()
    obv = analyzer.calc_obv()

    last = len(analyzer.close) - 1
    vm20 = analyzer.signals['volume_ma_20']

    # 统计近期量价关系
    recent = vol_analysis[-30:]
    vol_up = np.sum(recent == 2)
    vol_down = np.sum(recent == -2)
    vol_shrink = np.sum(recent == -1)

    print(f"\n  近30个交易日量价统计:")
    print(f"    放量上涨：{vol_up} 天  (健康的上涨)")
    print(f"    放量下跌：{vol_down} 天  (需要警惕)")
    print(f"    缩量：    {vol_shrink} 天")

    print(f"\n  最新量价状态 (第{last}天):")
    if vol_analysis[last] == 2:
        print(f"    放量上涨 → 买方积极，上涨有支撑")
    elif vol_analysis[last] == -2:
        print(f"    放量下跌 → 恐慌出逃，不要接飞刀")
    elif vol_analysis[last] == -1:
        print(f"    缩量 → 交投清淡，等待变盘")
    else:
        print(f"    正常量能")

    print(f"\n  成交量对比:")
    print(f"    今日成交量: {analyzer.volume[last]:,.0f}")
    print(f"    20日均量:   {vm20[last]:,.0f}")
    ratio = analyzer.volume[last] / vm20[last] * 100
    print(f"    量比:       {ratio:.0f}%")

    # OBV趋势
    obv_recent = obv[-20:]
    obv_trend = "上升" if obv_recent[-1] > obv_recent[0] else "下降"
    print(f"    OBV趋势:    {obv_trend}")


def demo_support_resistance(analyzer):
    """演示支撑压力位"""
    print("\n" + "=" * 60)
    print("  支撑位与压力位分析")
    print("=" * 60)

    sr = analyzer.find_support_resistance(window=20, threshold=0.03)
    current_price = analyzer.close[-1]

    print(f"\n  当前价格: {current_price:.2f}")
    print(f"\n  支撑位（下方）:")
    supports_below = [s for s in sr['supports'] if s < current_price]
    for s in sorted(supports_below, reverse=True)[:5]:
        distance = (current_price - s) / current_price * 100
        print(f"    {s:.2f}  (距离 {distance:.1f}%)")

    print(f"\n  压力位（上方）:")
    resistances_above = [r for r in sr['resistances'] if r > current_price]
    for r in sorted(resistances_above)[:5]:
        distance = (r - current_price) / current_price * 100
        print(f"    {r:.2f}  (距离 {distance:.1f}%)")


def demo_composite_signals(analyzer):
    """演示综合信号"""
    print("\n" + "=" * 60)
    print("  四级共振综合信号")
    print("=" * 60)

    signals, scores = analyzer.composite_signal()
    last = len(analyzer.close) - 1

    # 统计近期信号
    recent_sig = signals[-30:]
    strong_buy = np.sum(recent_sig == 2)
    weak_buy = np.sum(recent_sig == 1)
    neutral = np.sum(recent_sig == 0)
    weak_sell = np.sum(recent_sig == -1)
    strong_sell = np.sum(recent_sig == -2)

    print(f"\n  近30个交易日信号统计:")
    print(f"    强买入:  {strong_buy:>2} 天")
    print(f"    弱买入:  {weak_buy:>2} 天")
    print(f"    观望:    {neutral:>2} 天")
    print(f"    弱卖出:  {weak_sell:>2} 天")
    print(f"    强卖出:  {strong_sell:>2} 天")

    print(f"\n  当前综合评分: {scores[last]:.1f}")
    signal_map = {2: '★★ 强买入', 1: '★ 弱买入', 0: '— 观望', -1: '☆ 弱卖出', -2: '☆☆ 强卖出'}
    print(f"  当前综合信号: {signal_map.get(signals[last], '未知')}")

    # 打印最近的非观望信号
    print(f"\n  最近交易信号:")
    count = 0
    for i in range(last, max(0, last - 100), -1):
        if signals[i] != 0 and count < 8:
            print(f"    第{i:>3}天  {signal_map[signals[i]]:<10s}  评分:{scores[i]:.1f}  价格:{analyzer.close[i]:.2f}")
            count += 1
        if count >= 8:
            break


# ============================================================
# 4. 可视化
# ============================================================

def plot_technical_dashboard(analyzer):
    """绘制技术分析总览图"""
    analyzer.calc_ma([5, 20, 60, 120])
    analyzer.calc_macd()
    analyzer.calc_rsi(14)
    analyzer.calc_kdj()
    analyzer.calc_volume_ma(20)
    analyzer.composite_signal()

    days = np.arange(analyzer.data['days'])
    close = analyzer.close

    fig = plt.figure(figsize=(16, 14))

    # 图1：K线（用OHLC模拟）+ 均线
    ax1 = fig.add_subplot(5, 1, 1)
    colors_price = ['#A23B72' if close[i] >= analyzer.open[i] else '#2E86AB'
                    for i in range(len(close))]
    ax1.plot(days, close, linewidth=1.2, color='#333333', alpha=0.7)
    ax1.fill_between(days, close, analyzer.open, color=colors_price, alpha=0.3)
    for p, color, alpha_val in [(5, '#E74C3C', 0.7), (20, '#F39C12', 0.8),
                                  (60, '#2E86AB', 0.7), (120, '#8E44AD', 0.5)]:
        ax1.plot(days, analyzer.ma[p], linewidth=0.8, color=color, alpha=alpha_val,
                 label=f'MA{p}')
    ax1.set_ylabel('价格')
    ax1.set_title('技术分析综合面板')
    ax1.legend(loc='upper left', fontsize=7, ncol=4)
    ax1.grid(True, alpha=0.3)

    # 图2：成交量
    ax2 = fig.add_subplot(5, 1, 2)
    colors_vol = ['#A23B72' if close[i] >= analyzer.open[i] else '#2E86AB'
                  for i in range(len(close))]
    ax2.bar(days, analyzer.volume, color=colors_vol, alpha=0.6, width=1)
    ax2.plot(days, analyzer.signals['volume_ma_20'], linewidth=1, color='#F39C12',
             alpha=0.8, label='MA20')
    ax2.set_ylabel('成交量')
    ax2.legend(loc='upper left', fontsize=7)
    ax2.grid(True, alpha=0.3)

    # 图3：MACD
    ax3 = fig.add_subplot(5, 1, 3)
    dif = analyzer.signals['macd_dif']
    dea = analyzer.signals['macd_dea']
    bar = analyzer.signals['macd_bar']
    bar_colors = ['#A23B72' if b >= 0 else '#2E86AB' for b in bar]
    ax3.bar(days, bar, color=bar_colors, alpha=0.5, width=1)
    ax3.plot(days, dif, linewidth=1, color='#E74C3C', label='DIF')
    ax3.plot(days, dea, linewidth=1, color='#2E86AB', label='DEA')
    ax3.axhline(y=0, color='gray', linewidth=0.5, linestyle='--')
    ax3.set_ylabel('MACD')
    ax3.legend(loc='upper left', fontsize=7)
    ax3.grid(True, alpha=0.3)

    # 图4：RSI
    ax4 = fig.add_subplot(5, 1, 4)
    rsi14 = analyzer.signals['rsi_14']
    ax4.plot(days, rsi14, linewidth=1, color='#8E44AD', label='RSI(14)')
    ax4.axhline(y=70, color='#E74C3C', linewidth=0.8, linestyle='--', alpha=0.5)
    ax4.axhline(y=30, color='#2E86AB', linewidth=0.8, linestyle='--', alpha=0.5)
    ax4.fill_between(days, 30, 70, alpha=0.05, color='gray')
    ax4.set_ylabel('RSI')
    ax4.set_ylim(0, 100)
    ax4.legend(loc='upper left', fontsize=7)
    ax4.grid(True, alpha=0.3)

    # 图5：综合信号
    ax5 = fig.add_subplot(5, 1, 5)
    scores = analyzer.signals['composite_score']
    sig = analyzer.signals['composite']
    ax5.fill_between(days, 0, scores, color='gray', alpha=0.2)
    ax5.plot(days, scores, linewidth=1, color='#333333', alpha=0.7)
    ax5.axhline(y=3, color='#A23B72', linewidth=0.8, linestyle='--', alpha=0.4, label='强买线')
    ax5.axhline(y=-3, color='#2E86AB', linewidth=0.8, linestyle='--', alpha=0.4, label='强卖线')
    ax5.axhline(y=0, color='gray', linewidth=0.5, linestyle='-')
    ax5.set_xlabel('交易日')
    ax5.set_ylabel('综合评分')
    ax5.legend(loc='upper left', fontsize=7)
    ax5.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'technical_dashboard.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] 技术分析总览图已保存: {path}")


def plot_candlestick_with_indicators(analyzer):
    """绘制K线+关键信号标注图"""
    analyzer.calc_ma([5, 20, 60])
    analyzer.calc_macd()
    analyzer.calc_rsi(14)

    # 取最近120天
    start = max(0, len(analyzer.close) - 120)
    days = np.arange(start, len(analyzer.close))
    close_seg = analyzer.close[start:]
    ma5_seg = analyzer.ma[5][start:]
    ma20_seg = analyzer.ma[20][start:]
    ma60_seg = analyzer.ma[60][start:]

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={'height_ratios': [2, 1]})

    # 上图：K线模拟+均线
    ax = axes[0]
    for i in range(len(days)):
        idx = days[i]
        color = '#A23B72' if analyzer.close[idx] >= analyzer.open[idx] else '#2E86AB'
        body_bottom = min(analyzer.open[idx], analyzer.close[idx])
        body_height = abs(analyzer.close[idx] - analyzer.open[idx])
        ax.bar(i, body_height, bottom=body_bottom, color=color, width=0.6, alpha=0.85)
        ax.plot([i, i], [analyzer.low[idx], analyzer.high[idx]], color=color, linewidth=0.8)

    ax.plot(range(len(days)), ma5_seg, linewidth=1, color='#E74C3C', label='MA5', alpha=0.8)
    ax.plot(range(len(days)), ma20_seg, linewidth=1.2, color='#F39C12', label='MA20', alpha=0.9)
    ax.plot(range(len(days)), ma60_seg, linewidth=1, color='#2E86AB', label='MA60', alpha=0.7)

    # 标注金叉死叉
    crosses = analyzer.signals.get('macd_cross', [])
    for idx, ctype, price in crosses:
        if idx >= start:
            rel_idx = idx - start
            if ctype == 'golden':
                ax.annotate('金叉', (rel_idx, analyzer.low[idx]),
                            textcoords="offset points", xytext=(0, -18),
                            fontsize=7, color='#A23B72', ha='center',
                            arrowprops=dict(arrowstyle='->', color='#A23B72', lw=0.5))
            else:
                ax.annotate('死叉', (rel_idx, analyzer.high[idx]),
                            textcoords="offset points", xytext=(0, 8),
                            fontsize=7, color='#2E86AB', ha='center',
                            arrowprops=dict(arrowstyle='->', color='#2E86AB', lw=0.5))

    ax.set_ylabel('价格')
    ax.set_title('K线图 + 均线 + MACD交叉信号（最近120天）')
    ax.legend(loc='upper left', fontsize=8)
    ax.grid(True, alpha=0.3)

    # 下图：MACD柱状图
    ax = axes[1]
    bar_seg = analyzer.signals['macd_bar'][start:]
    dif_seg = analyzer.signals['macd_dif'][start:]
    dea_seg = analyzer.signals['macd_dea'][start:]
    x_range = range(len(days))
    bar_colors = ['#A23B72' if b >= 0 else '#2E86AB' for b in bar_seg]
    ax.bar(x_range, bar_seg, color=bar_colors, alpha=0.5, width=1)
    ax.plot(x_range, dif_seg, linewidth=1, color='#E74C3C', label='DIF')
    ax.plot(x_range, dea_seg, linewidth=1, color='#2E86AB', label='DEA')
    ax.axhline(y=0, color='gray', linewidth=0.5, linestyle='--')
    ax.set_ylabel('MACD')
    ax.legend(loc='upper left', fontsize=8)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'candlestick_signals.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] K线+信号标注图已保存: {path}")


def plot_indicator_detail(analyzer):
    """绘制RSI/KDJ/OBV综合对比图"""
    analyzer.calc_rsi(14)
    analyzer.calc_kdj()
    analyzer.calc_obv()

    start = max(0, len(analyzer.close) - 120)
    days = np.arange(start, len(analyzer.close))
    x_range = range(len(days))

    fig, axes = plt.subplots(3, 1, figsize=(14, 10))

    # RSI
    ax = axes[0]
    rsi = analyzer.signals['rsi_14'][start:]
    ax.plot(x_range, rsi, linewidth=1.2, color='#8E44AD')
    ax.fill_between(x_range, 70, 100, alpha=0.1, color='#E74C3C')
    ax.fill_between(x_range, 0, 30, alpha=0.1, color='#2E86AB')
    ax.axhline(y=70, color='#E74C3C', linewidth=0.8, linestyle='--', alpha=0.4)
    ax.axhline(y=30, color='#2E86AB', linewidth=0.8, linestyle='--', alpha=0.4)
    ax.axhline(y=50, color='gray', linewidth=0.5, alpha=0.3)
    ax.set_ylabel('RSI(14)')
    ax.set_ylim(0, 100)
    ax.set_title('RSI / KDJ / OBV 指标对比（最近120天）')
    ax.grid(True, alpha=0.3)

    # KDJ
    ax = axes[1]
    k_seg = analyzer.signals['kdj_k'][start:]
    d_seg = analyzer.signals['kdj_d'][start:]
    j_seg = analyzer.signals['kdj_j'][start:]
    ax.plot(x_range, k_seg, linewidth=0.8, color='#E74C3C', label='K', alpha=0.9)
    ax.plot(x_range, d_seg, linewidth=0.8, color='#2E86AB', label='D', alpha=0.9)
    ax.plot(x_range, j_seg, linewidth=0.6, color='#F39C12', label='J', alpha=0.6)
    ax.axhline(y=80, color='#E74C3C', linewidth=0.8, linestyle='--', alpha=0.3)
    ax.axhline(y=20, color='#2E86AB', linewidth=0.8, linestyle='--', alpha=0.3)
    ax.set_ylabel('KDJ')
    ax.set_ylim(-20, 120)
    ax.legend(loc='upper left', fontsize=8)
    ax.grid(True, alpha=0.3)

    # OBV
    ax = axes[2]
    obv_seg = analyzer.signals['obv'][start:]
    ax.fill_between(x_range, obv_seg, obv_seg[0], color='gray', alpha=0.2)
    ax.plot(x_range, obv_seg, linewidth=1.2, color='#333333')
    ax.set_xlabel('交易日')
    ax.set_ylabel('OBV')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'indicators_detail.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] RSI/KDJ/OBV对比图已保存: {path}")


def plot_signal_heatmap(analyzer):
    """绘制信号热力图"""
    analyzer.calc_ma([5, 20, 60])
    analyzer.calc_macd()
    analyzer.calc_rsi(14)
    analyzer.calc_kdj()
    analyzer.volume_analysis()
    analyzer.composite_signal()

    start = max(0, len(analyzer.close) - 100)
    n = len(analyzer.close) - start

    # 构建信号矩阵: [价格趋势, MA排列, MACD, RSI, KDJ, 成交量, 综合]
    matrix = np.zeros((7, n))

    close_seg = analyzer.close[start:]
    ema12 = analyzer._ema(analyzer.close, 12)
    ema26 = analyzer._ema(analyzer.close, 26)

    for i in range(n):
        idx = start + i
        # 价格趋势
        if i >= 5:
            matrix[0, i] = 1 if close_seg[i] > close_seg[i - 5] else -1
        # MA排列
        if not np.isnan(analyzer.ma[5][idx]) and not np.isnan(analyzer.ma[60][idx]):
            matrix[1, i] = 1 if analyzer.ma[5][idx] > analyzer.ma[60][idx] else -1
        # MACD信号
        dif = analyzer.signals['macd_dif']
        dea = analyzer.signals['macd_dea']
        if idx > 0:
            matrix[2, i] = 1 if dif[idx] > dea[idx] else -1
        # RSI信号
        rsi_val = analyzer.signals['rsi_14'][idx]
        if not np.isnan(rsi_val):
            if rsi_val < 30:
                matrix[3, i] = 1
            elif rsi_val > 70:
                matrix[3, i] = -1
        # KDJ信号
        k_val = analyzer.signals['kdj_k'][idx]
        d_val = analyzer.signals['kdj_d'][idx]
        if not np.isnan(k_val) and not np.isnan(d_val):
            matrix[4, i] = 1 if k_val > d_val else -1
        # 成交量信号
        va = analyzer.signals['volume_analysis'][idx]
        matrix[5, i] = 1 if va == 2 else (-1 if va == -2 else 0)
        # 综合
        matrix[6, i] = analyzer.signals['composite'][idx] / 2

    fig, ax = plt.subplots(figsize=(16, 4))
    im = ax.imshow(matrix, cmap='RdYlGn', aspect='auto', vmin=-1, vmax=1)

    ax.set_yticks(range(7))
    ax.set_yticklabels(['价格趋势', 'MA排列', 'MACD', 'RSI', 'KDJ', '成交量', '综合'])
    ax.set_xlabel('交易日（最近100天）')
    ax.set_title('多指标信号热力图（绿=看多，红=看空）')

    # 添加颜色条
    cbar = plt.colorbar(im, ax=ax, ticks=[-1, 0, 1])
    cbar.set_ticklabels(['看空', '中性', '看多'])

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'signal_heatmap.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] 信号热力图已保存: {path}")


# ============================================================
# 5. 简易回测
# ============================================================

def simple_backtest(analyzer, initial_capital=100000):
    """基于综合信号的回测"""
    analyzer.calc_macd()
    analyzer.calc_rsi(14)
    analyzer.calc_kdj()
    analyzer.calc_ma([5, 20, 60])
    analyzer.volume_analysis()
    signals, scores = analyzer.composite_signal()

    cash = initial_capital
    shares = 0
    portfolio_values = []
    trades = []
    position = 0  # 0=空仓, 0.5=半仓, 1=满仓

    for i in range(60, len(analyzer.close)):
        price = analyzer.close[i]
        signal = signals[i]

        if signal >= 2 and position < 1:
            # 强买入
            buy_amount = cash * (1 - position)
            new_shares = buy_amount / price
            shares += new_shares
            cash -= buy_amount
            position = 1
            trades.append((i, 'BUY', price, '强买入'))
        elif signal >= 1 and position < 0.5:
            # 弱买入 → 半仓
            buy_amount = cash * 0.5
            new_shares = buy_amount / price
            shares += new_shares
            cash -= buy_amount
            position = 0.5
            trades.append((i, 'BUY', price, '弱买入'))
        elif signal <= -2 and position > 0:
            # 强卖出 → 全清
            cash += shares * price
            shares = 0
            position = 0
            trades.append((i, 'SELL', price, '强卖出'))
        elif signal <= -1 and position > 0.5:
            # 弱卖出 → 减半仓
            sell_shares = shares * 0.5
            cash += sell_shares * price
            shares -= sell_shares
            position = 0.5
            trades.append((i, 'SELL', price, '弱卖出'))

        portfolio_values.append(cash + shares * price)

    final_value = portfolio_values[-1] if portfolio_values else initial_capital
    total_return = (final_value - initial_capital) / initial_capital
    years = len(portfolio_values) / 250
    annual_return = (final_value / initial_capital) ** (1 / max(years, 0.1)) - 1

    # 买入持有
    buy_hold_shares = initial_capital / analyzer.close[60]
    buy_hold_final = buy_hold_shares * analyzer.close[-1]
    bh_return = (buy_hold_final - initial_capital) / initial_capital

    print(f"\n  {'='*60}")
    print(f"  简易策略回测")
    print(f"  {'='*60}")
    print(f"\n  初始资金：{initial_capital:,}元")
    print(f"  回测区间：第60天 → 第{len(analyzer.close)-1}天 (约{years:.1f}年)")
    print(f"\n  策略收益：{final_value:,.0f}元  |  收益率：{total_return:+.2%}  |  年化：{annual_return:+.2%}")
    print(f"  买入持有：{buy_hold_final:,.0f}元  |  收益率：{bh_return:+.2%}")
    print(f"  超额收益：{final_value - buy_hold_final:,.0f}元")
    print(f"\n  交易记录（共{len(trades)}笔）:")
    for t in trades[-10:]:
        idx, action, price, reason = t
        print(f"    第{idx:>3}天  {action:<4s}  {price:.2f}  {reason}")

    return portfolio_values, trades


# ============================================================
# 主程序
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("  第八课实战代码：技术分析工具集")
    print("=" * 60)

    # 生成数据
    data = generate_price_data(days=250, seed=42)
    analyzer = TechnicalAnalyzer(data)

    # 1. 均线系统
    demo_ma_system(analyzer)

    # 2. MACD
    demo_macd(analyzer)

    # 3. RSI + KDJ
    demo_rsi_kdj(analyzer)

    # 4. 成交量
    demo_volume(analyzer)

    # 5. 支撑压力
    demo_support_resistance(analyzer)

    # 6. 综合信号
    demo_composite_signals(analyzer)

    # 7. 回测
    simple_backtest(analyzer)

    # 8. 图表
    plot_technical_dashboard(analyzer)
    plot_candlestick_with_indicators(analyzer)
    plot_indicator_detail(analyzer)
    plot_signal_heatmap(analyzer)

    print(f"\n{'=' * 60}")
    print(f"  所有图表已生成到：{OUTPUT_DIR}")
    print(f"{'=' * 60}")
