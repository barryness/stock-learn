"""
第九课配套实战代码：量化投资回测与因子分析
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
from collections import defaultdict
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
# 1. 数据生成
# ============================================================

def generate_market_data(days=1500, seed=42):
    """生成模拟市场和一组股票的日线数据"""
    np.random.seed(seed)

    # 市场指数
    t = np.arange(days)
    drift = 0.00025
    cycles = 0.12 * np.sin(2 * np.pi * t / 250) + 0.06 * np.sin(2 * np.pi * t / 63)
    noise = np.random.normal(0, 0.012, days)
    market_returns = drift + np.diff(np.concatenate([[0], cycles])) * 0.3 + noise
    market_index = 3000 * np.exp(np.cumsum(market_returns))

    # 生成30只个股
    n_stocks = 30
    stock_data = {}

    for s in range(n_stocks):
        beta = 0.5 + np.random.uniform(0, 1.0)
        alpha = np.random.normal(0.0001, 0.0003)  # 个股超额收益
        idio_noise = np.random.normal(0, 0.018, days)

        stock_returns = alpha + beta * market_returns + idio_noise
        stock_prices = 10 * np.exp(np.cumsum(stock_returns))

        # 生成财务因子数据（月度）
        months = days // 21 + 1
        pe = 15 + 10 * np.sin(np.linspace(0, 4 * np.pi, months)) + np.random.normal(0, 3, months)
        pe = np.clip(pe, 5, 60)
        roe = 0.12 + 0.04 * np.sin(np.linspace(0, 3 * np.pi, months)) + np.random.normal(0, 0.03, months)
        roe = np.clip(roe, 0.02, 0.30)
        momentum_12m = np.zeros(months)
        for m in range(1, months):
            lookback = min(m, 12)
            mom_start_idx = max(0, (m - lookback) * 21)
            mom_current_idx = m * 21
            if mom_current_idx > mom_start_idx and mom_start_idx < len(stock_prices):
                momentum_12m[m] = stock_prices[min(mom_current_idx, len(stock_prices)-1)] / \
                                  stock_prices[mom_start_idx] - 1
        volatility = np.zeros(months)
        for m in range(1, months):
            start_idx = max(0, (m - 1) * 21)
            end_idx = min(m * 21, days)
            if end_idx > start_idx + 5:
                rets = np.diff(stock_prices[start_idx:end_idx]) / stock_prices[start_idx:end_idx - 1]
                volatility[m] = np.std(rets) * np.sqrt(252)

        stock_data[f'stock_{s}'] = {
            'prices': stock_prices,
            'returns': stock_returns,
            'beta': beta,
            'pe': pe,
            'roe': roe,
            'momentum_12m': momentum_12m,
            'volatility': volatility,
        }

    return {
        'market_index': market_index,
        'market_returns': market_returns,
        'stocks': stock_data,
        'days': days,
    }


# ============================================================
# 2. 回测引擎
# ============================================================

class BacktestEngine:
    """通用回测框架"""

    def __init__(self, initial_capital=100000, commission_rate=0.00025,
                 stamp_tax=0.001, slippage=0.0005):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.stamp_tax = stamp_tax
        self.slippage = slippage

    def run(self, prices, signals, dates=None):
        """
        运行回测
        prices: array of daily prices
        signals: dict with 'action' (buy/sell/hold) and optional 'quantity'/'weight'
        """
        n = len(prices)
        cash = self.initial_capital
        shares = 0
        portfolio = np.zeros(n)
        trades = []

        for i in range(n):
            price = prices[i]
            action = signals[i] if isinstance(signals, np.ndarray) else signals.get(i, {})

            action_type = action if isinstance(action, str) else action.get('action', 'hold')

            if action_type == 'buy' and cash > 0:
                if isinstance(action, dict) and 'weight' in action:
                    buy_amount = (cash + shares * price) * action['weight']
                else:
                    buy_amount = cash

                buy_amount *= (1 - self.slippage)
                new_shares = buy_amount / price
                cost = new_shares * price * self.commission_rate
                shares += new_shares
                cash -= buy_amount + cost
                trades.append((i, 'BUY', price, new_shares))

            elif action_type == 'sell' and shares > 0:
                if isinstance(action, dict) and 'weight' in action:
                    sell_shares = shares * action['weight']
                else:
                    sell_shares = shares

                sell_value = sell_shares * price * (1 - self.slippage)
                cost = sell_value * (self.commission_rate + self.stamp_tax)
                cash += sell_value - cost
                shares -= sell_shares
                trades.append((i, 'SELL', price, sell_shares))

            portfolio[i] = cash + shares * price

        return {
            'portfolio': portfolio,
            'trades': trades,
            'final_cash': cash,
            'final_shares': shares,
        }


class RiskAnalyzer:
    """风险与绩效分析"""

    def __init__(self, portfolio_values, benchmark_values=None, risk_free_rate=0.03):
        self.pv = np.array(portfolio_values)
        self.bm = np.array(benchmark_values) if benchmark_values is not None else None
        self.rf = risk_free_rate
        self._calc_returns()

    def _calc_returns(self):
        self.returns = np.diff(self.pv) / self.pv[:-1]
        self.returns = self.returns[~np.isnan(self.returns)]
        if len(self.returns) == 0:
            self.returns = np.array([0])
            self.n_days = 1
        else:
            self.n_days = len(self.returns)

    def annual_return(self):
        days = max(self.n_days, 1)
        return (self.pv[-1] / self.pv[0]) ** (252 / days) - 1

    def annual_volatility(self):
        return np.std(self.returns) * np.sqrt(252)

    def max_drawdown(self):
        peak = np.maximum.accumulate(self.pv)
        dd = (self.pv - peak) / peak
        return dd.min()

    def max_drawdown_duration(self):
        """最大回撤持续天数"""
        peak = np.maximum.accumulate(self.pv)
        dd = (self.pv - peak) / peak
        in_dd = dd < 0
        max_dur = 0
        current_dur = 0
        for v in in_dd:
            if v:
                current_dur += 1
                max_dur = max(max_dur, current_dur)
            else:
                current_dur = 0
        return max_dur

    def sharpe_ratio(self):
        vol = self.annual_volatility()
        if vol == 0:
            return 0
        return (self.annual_return() - self.rf) / vol

    def calmar_ratio(self):
        mdd = abs(self.max_drawdown())
        if mdd == 0:
            return 0
        return self.annual_return() / mdd

    def sortino_ratio(self):
        downside = self.returns[self.returns < 0]
        if len(downside) == 0:
            return 0
        downside_vol = np.std(downside) * np.sqrt(252)
        if downside_vol == 0:
            return 0
        return (self.annual_return() - self.rf) / downside_vol

    def win_rate(self, trades):
        """计算胜率（基于交易记录）"""
        if not trades:
            return 0, 0
        profits = []
        losses = []
        # 配对买卖计算盈亏
        i = 0
        while i < len(trades) - 1:
            buy = trades[i]
            sell = trades[i + 1]
            if buy[1] == 'BUY' and sell[1] == 'SELL':
                pnl = (sell[2] - buy[2]) * buy[3]
                if pnl > 0:
                    profits.append(pnl)
                else:
                    losses.append(abs(pnl))
                i += 2
            else:
                i += 1

        win_count = len(profits)
        total_count = win_count + len(losses)
        win_rate = win_count / total_count if total_count > 0 else 0
        profit_factor = sum(profits) / sum(losses) if sum(losses) > 0 else float('inf')
        return win_rate, profit_factor

    def info_ratio(self):
        """信息比率 = 超额收益 / 跟踪误差"""
        if self.bm is None:
            return 0
        bm_returns = np.diff(self.bm) / self.bm[:-1]
        min_len = min(len(self.returns), len(bm_returns))
        excess = self.returns[:min_len] - bm_returns[:min_len]
        te = np.std(excess) * np.sqrt(252)
        if te == 0:
            return 0
        return (self.annual_return() - self._bm_return()) / te

    def _bm_return(self):
        if self.bm is None:
            return 0
        days = len(self.bm)
        return (self.bm[-1] / self.bm[0]) ** (252 / days) - 1

    def full_report(self, trades=None):
        report = {
            '年化收益率': f'{self.annual_return():.2%}',
            '年化波动率': f'{self.annual_volatility():.2%}',
            '最大回撤': f'{self.max_drawdown():.2%}',
            '最大回撤持续(天)': self.max_drawdown_duration(),
            '夏普比率': f'{self.sharpe_ratio():.2f}',
            '卡玛比率': f'{self.calmar_ratio():.2f}',
            '索提诺比率': f'{self.sortino_ratio():.2f}',
        }
        if self.bm is not None:
            report['信息比率'] = f'{self.info_ratio():.2f}'
        if trades:
            wr, pf = self.win_rate(trades)
            report['胜率'] = f'{wr:.2%}'
            report['盈亏比'] = f'{pf:.2f}'
        return report


# ============================================================
# 3. 双均线策略
# ============================================================

class DualMAStrategy:
    """双均线趋势跟踪策略"""

    def __init__(self, short=20, long=60, use_filter=False, filter_ma=200,
                 buffer_days=0, use_volume=False):
        self.short = short
        self.long = long
        self.use_filter = use_filter
        self.filter_ma = filter_ma
        self.buffer_days = buffer_days
        self.use_volume = use_volume

        self.ma_short = None
        self.ma_long = None
        self.ma_filter = None
        self.signals = None

    def calc_ma(self, prices, period):
        ma = np.full(len(prices), np.nan)
        for i in range(period - 1, len(prices)):
            ma[i] = np.mean(prices[i - period + 1:i + 1])
        return ma

    def generate_signals(self, prices, volumes=None):
        """生成交易信号: 1=买入, -1=卖出, 0=持有"""
        n = len(prices)
        self.ma_short = self.calc_ma(prices, self.short)
        self.ma_long = self.calc_ma(prices, self.long)
        if self.use_filter:
            self.ma_filter = self.calc_ma(prices, self.filter_ma)

        signals = np.zeros(n, dtype=int)

        for i in range(max(self.short, self.long), n):
            if np.isnan(self.ma_short[i]) or np.isnan(self.ma_long[i]):
                continue

            if self.buffer_days > 0:
                # 需要连续buffer_days天确认交叉
                cross_ok = True
                for d in range(self.buffer_days + 1):
                    idx = i - d
                    if idx < max(self.short, self.long):
                        cross_ok = False
                        break
                    if self.ma_short[idx] <= self.ma_long[idx]:
                        cross_ok = False
                        break
                if cross_ok:
                    signals[i] = 1
            else:
                prev_diff = self.ma_short[i - 1] - self.ma_long[i - 1]
                curr_diff = self.ma_short[i] - self.ma_long[i]

                if prev_diff <= 0 and curr_diff > 0:
                    signals[i] = 1
                elif prev_diff >= 0 and curr_diff < 0:
                    signals[i] = -1

            # 过滤器：只在MA200上方做多
            if self.use_filter and not np.isnan(self.ma_filter[i]):
                if signals[i] == 1 and prices[i] < self.ma_filter[i]:
                    signals[i] = 0

            # 成交量确认
            if self.use_volume and volumes is not None and signals[i] != 0:
                if i >= 20:
                    avg_vol = np.mean(volumes[i - 20:i])
                    if volumes[i] < avg_vol * 1.2:
                        signals[i] = 0

        self.signals = signals
        return signals

    def get_actions(self, prices, volumes=None):
        """转换为买卖动作序列"""
        signals = self.generate_signals(prices, volumes)
        actions = {}
        position = 0  # 0=空仓, 1=持仓

        for i, sig in enumerate(signals):
            if sig == 1 and position == 0:
                actions[i] = 'buy'
                position = 1
            elif sig == -1 and position == 1:
                actions[i] = 'sell'
                position = 0
            else:
                actions[i] = 'hold'

        return actions


# ============================================================
# 4. 因子打分系统
# ============================================================

class FactorEngine:
    """多因子打分系统"""

    def __init__(self, stock_universe):
        self.stocks = stock_universe

    def calculate_scores(self, month_idx):
        """计算某个月份所有股票的因子得分"""
        scores = {}
        for name, data in self.stocks.items():
            score = 0
            details = {}

            # 价值因子：PE越低越好
            if month_idx < len(data['pe']):
                pe = data['pe'][month_idx]
                details['pe'] = pe
                score += self._pe_score(pe) * 0.30

            # 质量因子：ROE越高越好
            if month_idx < len(data['roe']):
                roe = data['roe'][month_idx]
                details['roe'] = roe
                score += self._roe_score(roe) * 0.25

            # 动量因子：过去12个月收益越高越好
            if month_idx < len(data['momentum_12m']):
                mom = data['momentum_12m'][month_idx]
                details['momentum'] = mom
                score += self._momentum_score(mom) * 0.25

            # 低波因子：波动率越低越好
            if month_idx < len(data['volatility']):
                vol = data['volatility'][month_idx]
                details['volatility'] = vol
                score += self._lowvol_score(vol) * 0.20

            scores[name] = {'total': score, 'details': details}

        return scores

    def _pe_score(self, pe):
        if pe <= 0:
            return 0
        if pe < 10:
            return 1.0
        elif pe < 15:
            return 0.7
        elif pe < 20:
            return 0.4
        elif pe < 30:
            return 0.15
        else:
            return 0.0

    def _roe_score(self, roe):
        if roe > 0.20:
            return 1.0
        elif roe > 0.15:
            return 0.7
        elif roe > 0.10:
            return 0.4
        elif roe > 0.05:
            return 0.15
        else:
            return 0.0

    def _momentum_score(self, mom):
        if mom > 0.30:
            return 1.0
        elif mom > 0.15:
            return 0.7
        elif mom > 0.05:
            return 0.45
        elif mom > -0.10:
            return 0.2
        else:
            return 0.0

    def _lowvol_score(self, vol):
        if vol < 0.20:
            return 1.0
        elif vol < 0.28:
            return 0.7
        elif vol < 0.35:
            return 0.35
        elif vol < 0.45:
            return 0.1
        else:
            return 0.0

    def rank_stocks(self, month_idx, top_n=5):
        """按得分排名，返回前N只"""
        scores = self.calculate_scores(month_idx)
        ranked = sorted(scores.items(), key=lambda x: x[1]['total'], reverse=True)
        return ranked[:top_n]


# ============================================================
# 5. Walk-Forward分析
# ============================================================

def walk_forward_analysis(prices, strategy_class, param_ranges,
                           train_years=3, test_years=1, days_per_year=252):
    """Walk-Forward滚动优化"""
    total_days = len(prices)
    train_days = train_years * days_per_year
    test_days = test_years * days_per_year

    results = []
    start = 0

    while start + train_days + test_days <= total_days:
        train_prices = prices[start:start + train_days]
        test_prices = prices[start + train_days:start + train_days + test_days]

        # 在训练集上找最优参数
        best_sharpe = -np.inf
        best_params = None

        for short, long in param_ranges:
            if short >= long:
                continue
            strategy = strategy_class(short=short, long=long)
            actions = strategy.get_actions(train_prices)
            engine = BacktestEngine()
            bt_result = engine.run(train_prices, actions)
            analyzer = RiskAnalyzer(bt_result['portfolio'])
            sharpe = analyzer.sharpe_ratio()
            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_params = (short, long)

        # 用最优参数在测试集上运行
        strategy = strategy_class(short=best_params[0], long=best_params[1])
        actions = strategy.get_actions(test_prices)
        engine = BacktestEngine()
        bt_result = engine.run(test_prices, actions)
        analyzer = RiskAnalyzer(bt_result['portfolio'])

        results.append({
            'period': f'{start//252}-{(start+train_days)//252}→{(start+train_days+test_days)//252}',
            'best_params': best_params,
            'train_sharpe': best_sharpe,
            'test_return': analyzer.annual_return(),
            'test_sharpe': analyzer.sharpe_ratio(),
            'test_maxdd': analyzer.max_drawdown(),
        })

        start += test_days

    return results


# ============================================================
# 6. 演示函数
# ============================================================

def demo_dual_ma_strategy(prices):
    """演示双均线策略"""
    print("\n" + "=" * 60)
    print("  双均线策略回测")
    print("=" * 60)

    # 基础版
    strategy = DualMAStrategy(short=20, long=60)
    actions = strategy.get_actions(prices)
    engine = BacktestEngine()
    result = engine.run(prices, actions)
    analyzer = RiskAnalyzer(result['portfolio'])

    # 买入持有
    bh_result = prices[-1] / prices[0] - 1

    print(f"\n  策略参数：MA20 / MA60")
    print(f"  回测天数：{len(prices)} 天")
    print(f"  交易次数：{len(result['trades'])} 笔")

    print(f"\n  📊 绩效报告：")
    report = analyzer.full_report(result['trades'])
    for k, v in report.items():
        print(f"    {k}: {v}")

    print(f"\n  策略收益：{(result['portfolio'][-1]/100000 - 1)*100:+.2f}%")
    print(f"  买入持有：{bh_result*100:+.2f}%")
    print(f"  超额收益：{(result['portfolio'][-1]/100000 - 1 - bh_result)*100:+.2f}%")

    return result, analyzer, actions


def demo_strategy_comparison(prices):
    """对比不同参数的双均线策略"""
    print("\n" + "=" * 60)
    print("  双均线策略参数对比")
    print("=" * 60)

    param_sets = [(10, 50), (20, 60), (30, 90), (10, 90), (30, 50)]
    results = []

    print(f"\n  {'参数':<10s} {'年化收益':>10s} {'最大回撤':>10s} {'夏普':>8s} {'交易次数':>8s}")
    print(f"  {'-'*10} {'-'*10} {'-'*10} {'-'*8} {'-'*8}")

    for short, long in param_sets:
        strategy = DualMAStrategy(short=short, long=long)
        actions = strategy.get_actions(prices)
        engine = BacktestEngine()
        result = engine.run(prices, actions)
        analyzer = RiskAnalyzer(result['portfolio'])

        param_label = f'MA{short}/{long}'
        print(f"  {param_label:<10s} {analyzer.annual_return():>9.1%}  "
              f"{analyzer.max_drawdown():>9.1%}  {analyzer.sharpe_ratio():>7.2f}  "
              f"{len(result['trades']):>8d}")
        results.append((param_label, analyzer, result))

    return results


def demo_factors(data, month_idx=30):
    """演示因子打分系统"""
    print("\n" + "=" * 60)
    print("  多因子打分选股")
    print("=" * 60)

    engine = FactorEngine(data['stocks'])
    ranked = engine.rank_stocks(month_idx, top_n=10)

    print(f"\n  月份 {month_idx} 因子打分排名（前10）：")
    print(f"  {'排名':<6s} {'股票':<12s} {'总分':>6s} {'PE':>8s} {'ROE':>8s} {'动量':>8s} {'波动率':>8s}")
    print(f"  {'-'*6} {'-'*12} {'-'*6} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")

    for rank, (name, score_data) in enumerate(ranked, 1):
        d = score_data['details']
        pe_str = f"{d.get('pe', 0):.1f}"
        roe_str = f"{d.get('roe', 0):.1%}"
        mom_str = f"{d.get('momentum', 0):.1%}"
        vol_str = f"{d.get('volatility', 0):.1%}"
        print(f"  #{rank:<5d} {name:<12s} {score_data['total']:>6.3f} "
              f"{pe_str:>8s} {roe_str:>8s} {mom_str:>8s} {vol_str:>8s}")

    return ranked


def demo_walk_forward(prices):
    """演示Walk-Forward分析"""
    print("\n" + "=" * 60)
    print("  Walk-Forward 滚动优化")
    print("=" * 60)

    param_ranges = [(s, l) for s in [10, 20, 30] for l in [50, 60, 90] if s < l]
    results = walk_forward_analysis(prices, DualMAStrategy, param_ranges,
                                     train_years=3, test_years=1)

    print(f"\n  {'窗口':<16s} {'最优参数':<10s} {'训练夏普':>8s} {'测试夏普':>8s} {'测试收益':>10s}")
    print(f"  {'-'*16} {'-'*10} {'-'*8} {'-'*8} {'-'*10}")

    all_test_returns = []
    all_test_sharpes = []
    for r in results:
        params_str = f'MA{r["best_params"][0]}/{r["best_params"][1]}'
        print(f"  {r['period']:<16s} {params_str:<10s} {r['train_sharpe']:>7.2f}  "
              f"{r['test_sharpe']:>7.2f}  {r['test_return']:>9.1%}")
        all_test_returns.append(r['test_return'])
        all_test_sharpes.append(r['test_sharpe'])

    if all_test_returns:
        print(f"\n  Walk-Forward总结：")
        print(f"    样本外平均年化收益：{np.mean(all_test_returns):.2%}")
        print(f"    样本外平均夏普比率：{np.mean(all_test_sharpes):.2f}")
        print(f"    样本外最低年化收益：{np.min(all_test_returns):.2%}")
        print(f"    样本外最高年化收益：{np.max(all_test_returns):.2%}")

    return results


def demo_overfitting_demo(data):
    """演示过拟合：随机搜索找到'最佳'参数 vs Walk-Forward"""
    print("\n" + "=" * 60)
    print("  过拟合演示：静态回测 vs Walk-Forward")
    print("=" * 60)

    prices = data['market_index']

    # 静态回测：搜索所有参数组合
    all_params = [(s, l) for s in range(5, 55, 5) for l in range(25, 150, 5) if s < l]
    best_static_sharpe = -np.inf
    best_static_params = None
    best_static_return = 0

    for short, long in all_params:
        strategy = DualMAStrategy(short=short, long=long)
        actions = strategy.get_actions(prices)
        engine = BacktestEngine()
        bt = engine.run(prices, actions)
        analyzer = RiskAnalyzer(bt['portfolio'])
        sr = analyzer.sharpe_ratio()
        if sr > best_static_sharpe:
            best_static_sharpe = sr
            best_static_params = (short, long)
            best_static_return = analyzer.annual_return()

    print(f"\n  静态全样本回测（搜索{len(all_params)}组参数）：")
    print(f"    最优参数：MA{best_static_params[0]}/{best_static_params[1]}")
    print(f"    全样本夏普：{best_static_sharpe:.2f}")
    print(f"    全样本年化：{best_static_return:.2%}")

    # Walk-Forward（用更少参数提高速度）
    param_ranges = [(s, l) for s in [10, 20, 30] for l in [50, 60, 90] if s < l]
    wf_results = walk_forward_analysis(prices, DualMAStrategy, param_ranges,
                                        train_years=3, test_years=1)

    wf_returns = [r['test_return'] for r in wf_results]
    wf_sharpes = [r['test_sharpe'] for r in wf_results]

    print(f"\n  Walk-Forward（滚动样本外）：")
    print(f"    样本外平均夏普：{np.mean(wf_sharpes):.2f}")
    print(f"    样本外平均年化：{np.mean(wf_returns):.2%}")

    print(f"\n  ⚠️ 对比分析：")
    print(f"    静态回测年化：{best_static_return:.2%}  (高估！)")
    print(f"    Walk-Forward年化：{np.mean(wf_returns):.2%}  (更接近真实)")
    drop = (best_static_return - np.mean(wf_returns))
    print(f"    过拟合虚增：约{drop:.2%}")
    print(f"    这{drop:.2%}的'超额收益'在实盘中大概率不存在")

    return best_static_params, wf_results


def demo_risk_management():
    """演示仓位管理与止损"""
    print("\n" + "=" * 60)
    print("  风险管理工具演示")
    print("=" * 60)

    capital = 100000

    # 凯利公式
    print(f"\n  凯利公式仓位计算：")
    scenarios = [
        (0.55, 2.0, "趋势策略"),
        (0.60, 1.5, "均值回归策略"),
        (0.45, 3.0, "高盈亏比策略"),
    ]
    for win_rate, profit_factor, desc in scenarios:
        avg_win = 0.10
        avg_loss = avg_win / profit_factor
        kelly = (win_rate * profit_factor - (1 - win_rate)) / profit_factor
        half_kelly = kelly / 2
        print(f"    {desc}: 胜率{win_rate:.0%}, 盈亏比{profit_factor}")
        print(f"      凯利仓位={kelly:.1%}, 半凯利（推荐）={half_kelly:.1%}")

    # 波动率目标
    print(f"\n  波动率目标仓位：")
    for target_vol, actual_vol, desc in [(0.12, 0.20, '稳健型'), (0.15, 0.25, '平衡型'), (0.20, 0.30, '进取型')]:
        position = target_vol / actual_vol
        print(f"    {desc}: 目标{target_vol:.0%}, 实际{actual_vol:.0%} → 仓位={position:.0%}")

    # ATR止损
    print(f"\n  ATR止损计算示例：")
    print(f"    买入价：10.00元, ATR(14)=0.35元")
    for multiplier, desc in [(1.5, '紧止损'), (2.0, '标准'), (3.0, '宽松')]:
        stop_price = 10.00 - multiplier * 0.35
        risk_pct = (10.00 - stop_price) / 10.00
        print(f"    {desc} ({multiplier}x ATR): 止损价={stop_price:.2f}元, 风险={risk_pct:.1%}")


# ============================================================
# 7. 可视化
# ============================================================

def plot_strategy_backtest(prices, bt_result, actions):
    """绘制策略回测图"""
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [2, 1, 1]})

    days = np.arange(len(prices))
    portfolio = bt_result['portfolio']

    # 图1：价格 + 买卖点
    ax = axes[0]
    ax.plot(days, prices, linewidth=1, color='#333333', alpha=0.7, label='价格')
    ax.plot(days, portfolio / (100000 / prices[0]), linewidth=1.5, color='#2E86AB',
            alpha=0.8, label='策略净值（调整后）')

    for trade in bt_result['trades']:
        idx, action, price, _ = trade
        if action == 'BUY':
            ax.scatter(idx, price, color='#A23B72', marker='^', s=60, zorder=5)
        else:
            ax.scatter(idx, price, color='#2E86AB', marker='v', s=60, zorder=5)

    # 标注一次买卖作为图例
    ax.scatter([], [], color='#A23B72', marker='^', s=60, label='买入')
    ax.scatter([], [], color='#2E86AB', marker='v', s=60, label='卖出')
    ax.set_ylabel('价格')
    ax.set_title('双均线策略回测（MA20/MA60）')
    ax.legend(loc='upper left', fontsize=8)
    ax.grid(True, alpha=0.3)

    # 图2：持仓状态
    ax = axes[1]
    position = np.zeros(len(prices))
    in_position = False
    for trade in bt_result['trades']:
        idx, action, _, _ = trade
        if action == 'BUY':
            in_position = True
        elif action == 'SELL':
            in_position = False
        for j in range(idx, len(position)):
            position[j] = 1 if in_position else 0
    ax.fill_between(days, 0, position, color='#A23B72', alpha=0.3)
    ax.set_ylabel('持仓')
    ax.set_ylim(-0.1, 1.1)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(['空仓', '持仓'])
    ax.grid(True, alpha=0.3)

    # 图3：回撤
    ax = axes[2]
    peak = np.maximum.accumulate(portfolio)
    drawdown = (portfolio - peak) / peak * 100
    ax.fill_between(days, 0, drawdown, color='#A23B72', alpha=0.3)
    ax.plot(days, drawdown, linewidth=0.8, color='#A23B72')
    ax.set_xlabel('交易日')
    ax.set_ylabel('回撤 (%)')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'quant_backtest.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] 策略回测图已保存: {path}")


def plot_factor_analysis(data, month_idx=30):
    """绘制因子分析图"""
    stocks = data['stocks']

    # 提取因子数据
    names = []
    pe_vals = []
    roe_vals = []
    mom_vals = []
    vol_vals = []

    for name, sd in stocks.items():
        if month_idx < len(sd['pe']):
            names.append(name)
            pe_vals.append(sd['pe'][month_idx])
            roe_vals.append(sd['roe'][month_idx])
            mom_vals.append(sd['momentum_12m'][month_idx])
            vol_vals.append(sd['volatility'][month_idx])

    n = len(names)
    if n == 0:
        return

    # 百分位排名
    pe_rank = np.argsort(np.argsort(pe_vals)) / (n - 1)
    roe_rank = np.argsort(np.argsort(roe_vals)) / (n - 1)
    mom_rank = np.argsort(np.argsort(mom_vals)) / (n - 1)
    vol_rank = 1 - np.argsort(np.argsort(vol_vals)) / (n - 1)  # 低波排名高

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))

    # PE vs ROE
    ax = axes[0, 0]
    ax.scatter(pe_vals, roe_vals, c='#2E86AB', alpha=0.6, s=50)
    ax.set_xlabel('PE')
    ax.set_ylabel('ROE')
    ax.set_title('价值 vs 质量 (PE vs ROE)')
    ax.grid(True, alpha=0.3)
    for i in range(n):
        if pe_rank[i] > 0.7 or roe_rank[i] > 0.7:
            ax.annotate(names[i].split('_')[1], (pe_vals[i], roe_vals[i]),
                         fontsize=6, alpha=0.7)

    # 动量 vs 波动率
    ax = axes[0, 1]
    ax.scatter(mom_vals, vol_vals, c='#A23B72', alpha=0.6, s=50)
    ax.set_xlabel('12月动量')
    ax.set_ylabel('年化波动率')
    ax.set_title('动量 vs 低波')
    ax.grid(True, alpha=0.3)

    # 因子排名热力图（前10只）
    ax = axes[1, 0]
    top10 = np.argsort(pe_rank + roe_rank + mom_rank + vol_rank)[-10:]
    matrix = np.zeros((10, 4))
    labels = ['价值', '质量', '动量', '低波']
    for i, idx in enumerate(top10):
        matrix[i, 0] = pe_rank[idx]
        matrix[i, 1] = roe_rank[idx]
        matrix[i, 2] = mom_rank[idx]
        matrix[i, 3] = vol_rank[idx]
    im = ax.imshow(matrix.T, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)
    ax.set_xticks(range(10))
    ax.set_xticklabels([names[i].split('_')[1] for i in top10], fontsize=7)
    ax.set_yticks(range(4))
    ax.set_yticklabels(labels)
    ax.set_title('因子排名热力图 (绿=排名高)')

    # 综合得分柱状图
    ax = axes[1, 1]
    total_scores = pe_rank + roe_rank + mom_rank + vol_rank
    top5_idx = np.argsort(total_scores)[-5:]
    others_idx = np.argsort(total_scores)[:-5]
    ax.barh([names[i].split('_')[1] for i in top5_idx],
             total_scores[top5_idx], color='#A23B72', alpha=0.8, label='Top 5')
    ax.barh([names[i].split('_')[1] for i in others_idx],
             total_scores[others_idx], color='#2E86AB', alpha=0.4, label='Others')
    ax.set_xlabel('综合得分')
    ax.set_title('多因子综合得分排名')
    ax.legend(fontsize=7)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'factor_analysis.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] 因子分析图已保存: {path}")


def plot_walk_forward(wf_results, static_params, prices):
    """绘制Walk-Forward vs 静态回测对比"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 图1：参数稳定性
    ax = axes[0]
    periods = [r['period'] for r in wf_results]
    params = [r['best_params'] for r in wf_results]
    shorts = [p[0] for p in params]
    longs = [p[1] for p in params]
    x = range(len(periods))
    ax.plot(x, shorts, 'o-', color='#A23B72', linewidth=1.5, label='短周期', markersize=8)
    ax.plot(x, longs, 's-', color='#2E86AB', linewidth=1.5, label='长周期', markersize=8)
    ax.axhline(y=static_params[0], color='#A23B72', linestyle='--', alpha=0.4)
    ax.axhline(y=static_params[1], color='#2E86AB', linestyle='--', alpha=0.4)
    ax.set_xticks(x)
    ax.set_xticklabels(periods, fontsize=7, rotation=30)
    ax.set_ylabel('MA周期')
    ax.set_title('Walk-Forward：各窗口最优参数')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 图2：样本内 vs 样本外夏普
    ax = axes[1]
    x = range(len(periods))
    train_sharpes = [r['train_sharpe'] for r in wf_results]
    test_sharpes = [r['test_sharpe'] for r in wf_results]
    ax.bar(np.array(x) - 0.15, train_sharpes, 0.3, color='#F39C12', alpha=0.8, label='训练集夏普')
    ax.bar(np.array(x) + 0.15, test_sharpes, 0.3, color='#2E86AB', alpha=0.8, label='测试集夏普')
    ax.set_xticks(x)
    ax.set_xticklabels(periods, fontsize=7, rotation=30)
    ax.set_ylabel('夏普比率')
    ax.set_title('样本内 vs 样本外 夏普比率')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'walk_forward.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] Walk-Forward分析图已保存: {path}")


def plot_overfitting_demo(all_params_results, wf_results):
    """绘制过拟合演示图"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # all_params_results: list of ((short, long), sharpe)
    params = [p[0] for p in all_params_results]
    sharpes = [p[1] for p in all_params_results]
    shorts_list = [p[0] for p in params]
    longs_list = [p[1] for p in params]
    shorts = sorted(set(shorts_list))
    longs = sorted(set(longs_list))

    # 图1：参数热力图
    ax = axes[0]
    heatmap = np.full((len(shorts), len(longs)), np.nan)
    for (s, l), sharpe in all_params_results:
        si = shorts.index(s)
        li = longs.index(l)
        heatmap[si, li] = sharpe

    im = ax.imshow(heatmap, cmap='RdYlGn', aspect='auto', origin='lower',
                    extent=[longs[0], longs[-1], shorts[0], shorts[-1]])
    ax.set_xlabel('长周期')
    ax.set_ylabel('短周期')
    ax.set_title('全样本参数搜索（静态回测）')
    plt.colorbar(im, ax=ax, label='夏普比率')

    # 标注最优
    best_idx = np.unravel_index(np.nanargmax(heatmap), heatmap.shape)
    ax.scatter(longs[best_idx[1]], shorts[best_idx[0]], marker='*',
                color='black', s=200, zorder=5)

    # 图2：Walk-Forward各窗口收益对比
    ax = axes[1]
    if wf_results:
        periods = [r['period'] for r in wf_results]
        test_rets = [r['test_return'] * 100 for r in wf_results]
        colors = ['#A23B72' if r >= 0 else '#2E86AB' for r in test_rets]
        ax.bar(range(len(periods)), test_rets, color=colors, alpha=0.8)
        ax.axhline(y=0, color='gray', linewidth=0.5)
        mean_ret = np.mean(test_rets)
        ax.axhline(y=mean_ret, color='#F39C12', linewidth=1.5, linestyle='--',
                    label=f'平均样本外: {mean_ret:.1f}%')
        ax.set_xticks(range(len(periods)))
        ax.set_xticklabels(periods, fontsize=8, rotation=30)
        ax.set_ylabel('年化收益率 (%)')
        ax.set_title('Walk-Forward 各窗口样本外收益')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'overfitting_demo.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] 过拟合演示图已保存: {path}")


# ============================================================
# 主程序
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("  第九课实战代码：量化投资回测与因子分析")
    print("=" * 60)

    # 生成数据
    data = generate_market_data(days=1500)
    prices = data['market_index']

    # 1. 双均线策略
    bt_result, analyzer, actions = demo_dual_ma_strategy(prices)
    plot_strategy_backtest(prices, bt_result, actions)

    # 2. 参数对比
    demo_strategy_comparison(prices)

    # 3. 因子打分
    demo_factors(data, month_idx=40)
    plot_factor_analysis(data, month_idx=40)

    # 4. Walk-Forward
    wf_results = demo_walk_forward(prices)

    # 5. 过拟合演示
    # 生成完整参数扫描结果用于热力图
    all_params = [(s, l) for s in range(5, 55, 5) for l in range(25, 150, 5) if s < l]
    all_params_sharpes = []
    for short, long in all_params:
        strategy = DualMAStrategy(short=short, long=long)
        actions = strategy.get_actions(prices)
        engine = BacktestEngine()
        bt = engine.run(prices, actions)
        analyzer = RiskAnalyzer(bt['portfolio'])
        all_params_sharpes.append(((short, long), analyzer.sharpe_ratio()))

    best_params, wf_results2 = demo_overfitting_demo(data)
    plot_overfitting_demo(all_params_sharpes, wf_results2)
    if wf_results2:
        plot_walk_forward(wf_results2, best_params, prices)

    # 6. 风险管理
    demo_risk_management()

    print(f"\n{'=' * 60}")
    print(f"  所有图表已生成到：{OUTPUT_DIR}")
    print(f"{'=' * 60}")
