"""
第九课进阶配套实战代码：因子研究、统计检验、均值回归、组合优化、绩效归因
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
from collections import defaultdict
import os
import warnings
warnings.filterwarnings('ignore')

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
# 1. 数据生成（更真实的模拟市场数据）
# ============================================================

def generate_realistic_data(n_stocks=50, n_days=1260, seed=42):
    """生成更真实的股票数据，包含行业分类和因子特征"""
    np.random.seed(seed)

    # 5个行业
    industries = ['银行', '消费', '科技', '医药', '能源']
    industry_assignments = {}
    for s in range(n_stocks):
        industry_assignments[f'stock_{s}'] = industries[s % 5]

    # 行业基准收益（不同行业有不同的Alpha）
    industry_factors = {
        '银行': {'drift': 0.00015, 'beta': 0.85, 'vol': 0.015},
        '消费': {'drift': 0.00030, 'beta': 0.90, 'vol': 0.016},
        '科技': {'drift': 0.00035, 'beta': 1.25, 'vol': 0.022},
        '医药': {'drift': 0.00025, 'beta': 0.80, 'vol': 0.019},
        '能源': {'drift': 0.00010, 'beta': 1.10, 'vol': 0.021},
    }

    # 市场收益
    t = np.arange(n_days)
    drift = 0.00025
    cycles = 0.10 * np.sin(2 * np.pi * t / 250) + 0.05 * np.sin(2 * np.pi * t / 63)
    noise = np.random.normal(0, 0.012, n_days)
    market_returns = drift + np.diff(np.concatenate([[0], cycles])) * 0.3 + noise
    market_index = 3000 * np.exp(np.cumsum(market_returns))

    # 生成个股
    stock_data = {}
    for s in range(n_stocks):
        ind = industry_assignments[f'stock_{s}']
        ind_f = industry_factors[ind]

        beta = ind_f['beta'] + np.random.normal(0, 0.15)
        alpha = np.random.normal(ind_f['drift'] * 0.5, ind_f['drift'] * 0.3)
        idio_noise = np.random.normal(0, ind_f['vol'], n_days)

        stock_returns = alpha + beta * market_returns + idio_noise
        stock_prices = 10 * np.exp(np.cumsum(stock_returns))

        # 月度因子数据
        n_months = n_days // 21 + 1

        # PE：行业有系统性差异
        pe_base = {'银行': 8, '消费': 25, '科技': 35, '医药': 30, '能源': 12}[ind]
        pe = pe_base + np.random.normal(0, pe_base * 0.3, n_months)
        pe += 5 * np.sin(np.linspace(0, 3 * np.pi, n_months))
        pe = np.clip(pe, 3, 80)

        # ROE
        roe_base = {'银行': 0.12, '消费': 0.18, '科技': 0.14, '医药': 0.15, '能源': 0.09}[ind]
        roe = roe_base + np.random.normal(0, 0.03, n_months)
        roe = np.clip(roe, 0.01, 0.35)

        # 12月动量
        momentum_12m = np.zeros(n_months)
        for m in range(1, n_months):
            lookback = min(m, 12)
            mom_start = max(0, (m - lookback) * 21)
            mom_end = min(m * 21, n_days)
            if mom_end > mom_start and mom_start < len(stock_prices):
                momentum_12m[m] = (stock_prices[min(mom_end, len(stock_prices)-1)] /
                                   stock_prices[mom_start] - 1)
        momentum_12m += np.random.normal(0, 0.05, n_months)

        # 波动率
        volatility = np.zeros(n_months)
        for m in range(1, n_months):
            start_idx = max(0, (m - 1) * 21)
            end_idx = min(m * 21, n_days)
            if end_idx > start_idx + 5:
                rets = np.diff(stock_prices[start_idx:end_idx]) / stock_prices[start_idx:end_idx - 1]
                volatility[m] = np.std(rets) * np.sqrt(252)
        volatility += np.random.normal(0, 0.02, n_months)
        volatility = np.clip(volatility, 0.05, 0.60)

        # 未来1月收益（用于IC计算）
        future_ret_1m = np.zeros(n_months)
        for m in range(n_months - 1):
            start_idx = m * 21
            end_idx = min((m + 1) * 21, n_days)
            if end_idx > start_idx and start_idx < len(stock_prices):
                future_ret_1m[m] = (stock_prices[min(end_idx, len(stock_prices)-1)] /
                                    stock_prices[start_idx] - 1)

        stock_data[f'stock_{s}'] = {
            'prices': stock_prices,
            'returns': stock_returns,
            'industry': ind,
            'beta': beta,
            'pe': pe,
            'roe': roe,
            'momentum_12m': momentum_12m,
            'volatility': volatility,
            'future_ret_1m': future_ret_1m,
        }

    return {
        'market_index': market_index,
        'market_returns': market_returns,
        'stocks': stock_data,
        'industries': industries,
        'industry_assignments': industry_assignments,
        'n_days': n_days,
        'n_months': n_days // 21 + 1,
    }


# ============================================================
# 2. 因子IC分析
# ============================================================

class FactorICAnalyzer:
    """因子IC（信息系数）分析器"""

    @staticmethod
    def rank_ic(factor_values, forward_returns):
        """计算Rank IC (Spearman相关系数)"""
        valid_mask = ~(np.isnan(factor_values) | np.isnan(forward_returns))
        if np.sum(valid_mask) < 10:
            return np.nan

        fv = factor_values[valid_mask]
        fr = forward_returns[valid_mask]

        # Spearman = Pearson on ranks
        n = len(fv)
        rank_fv = np.argsort(np.argsort(fv)) / (n - 1)
        rank_fr = np.argsort(np.argsort(fr)) / (n - 1)

        if np.std(rank_fv) == 0 or np.std(rank_fr) == 0:
            return np.nan

        return np.corrcoef(rank_fv, rank_fr)[0, 1]

    @staticmethod
    def pearson_ic(factor_values, forward_returns):
        """计算Pearson IC"""
        valid_mask = ~(np.isnan(factor_values) | np.isnan(forward_returns))
        if np.sum(valid_mask) < 10:
            return np.nan

        fv = factor_values[valid_mask]
        fr = forward_returns[valid_mask]

        if np.std(fv) == 0 or np.std(fr) == 0:
            return np.nan

        return np.corrcoef(fv, fr)[0, 1]

    def analyze_factor(self, stocks, factor_name, n_months, ic_method='rank'):
        """对某个因子做完整的IC分析"""
        ic_func = self.rank_ic if ic_method == 'rank' else self.pearson_ic

        ic_series = []
        for m in range(n_months - 1):
            factor_vals = []
            fwd_rets = []
            for name, data in stocks.items():
                if m < len(data.get(factor_name, [])) and m < len(data.get('future_ret_1m', [])):
                    fv = data[factor_name][m]
                    fr = data['future_ret_1m'][m]
                    if not np.isnan(fv) and not np.isnan(fr):
                        factor_vals.append(fv)
                        fwd_rets.append(fr)

            if len(factor_vals) >= 10:
                ic = ic_func(np.array(factor_vals), np.array(fwd_rets))
                ic_series.append(ic)

        ic_series = np.array([x for x in ic_series if not np.isnan(x)])

        if len(ic_series) == 0:
            return {'error': 'No valid IC data'}

        ic_mean = np.mean(ic_series)
        ic_std = np.std(ic_series)
        ic_ir = ic_mean / ic_std if ic_std > 0 else 0
        ic_positive_ratio = np.mean(ic_series > 0)
        t_stat = ic_mean / (ic_std / np.sqrt(len(ic_series))) if ic_std > 0 else 0

        return {
            'factor': factor_name,
            'method': ic_method,
            'n_periods': len(ic_series),
            'ic_mean': ic_mean,
            'ic_std': ic_std,
            'ic_ir': ic_ir,
            'ic_positive_ratio': ic_positive_ratio,
            't_statistic': t_stat,
            'ic_series': ic_series,
        }

    def ic_decay(self, stocks, factor_name, n_months, max_lag=12):
        """IC衰减分析：因子对未来1/2/3/.../12月收益的预测能力"""
        decays = []

        for lag in range(1, max_lag + 1):
            ic_vals = []
            for m in range(n_months - lag):
                factor_vals = []
                fwd_rets = []
                for name, data in stocks.items():
                    fv_key = factor_name
                    if m < len(data.get(fv_key, [])):
                        fv = data[fv_key][m]
                        # 计算从m到m+lag的收益
                        start_idx = m * 21
                        end_idx = min((m + lag) * 21, data['prices'].shape[0])
                        if end_idx > start_idx and start_idx < len(data['prices']):
                            fr = (data['prices'][min(end_idx, len(data['prices'])-1)] /
                                  data['prices'][start_idx] - 1)
                            if not np.isnan(fv) and not np.isnan(fr):
                                factor_vals.append(fv)
                                fwd_rets.append(fr)

                if len(factor_vals) >= 10:
                    ic = self.rank_ic(np.array(factor_vals), np.array(fwd_rets))
                    if not np.isnan(ic):
                        ic_vals.append(ic)

            if ic_vals:
                decays.append(np.mean(ic_vals))
            else:
                decays.append(np.nan)

        return decays


# ============================================================
# 3. 分层回测（Quantile Analysis）
# ============================================================

def quantile_backtest(stocks, factor_name, n_months, n_quantiles=5):
    """分层回测：按因子值分组，看各组未来表现"""
    quantile_returns = [[] for _ in range(n_quantiles)]
    long_short_returns = []

    for m in range(n_months - 1):
        stock_scores = []
        for name, data in stocks.items():
            if m < len(data.get(factor_name, [])):
                fv = data[factor_name][m]
                fr = data['future_ret_1m'][m]
                if not np.isnan(fv) and not np.isnan(fr):
                    stock_scores.append((fv, fr))

        if len(stock_scores) < n_quantiles * 3:
            continue

        stock_scores.sort(key=lambda x: x[0])
        n = len(stock_scores)
        group_size = n // n_quantiles

        for q in range(n_quantiles):
            start = q * group_size
            end = start + group_size if q < n_quantiles - 1 else n
            group_ret = np.mean([s[1] for s in stock_scores[start:end]])
            quantile_returns[q].append(group_ret)

        # 做多Q1（因子最好），做空Q5（因子最差）
        top_ret = np.mean([s[1] for s in stock_scores[:group_size]])
        bottom_ret = np.mean([s[1] for s in stock_scores[-group_size:]])
        long_short_returns.append(top_ret - bottom_ret)

    return {
        'quantile_returns': quantile_returns,
        'long_short_returns': long_short_returns,
    }


# ============================================================
# 4. Bootstrap统计显著性检验
# ============================================================

def bootstrap_significance_test(returns, n_bootstrap=10000, seed=42):
    """Bootstrap检验：策略收益是否统计显著"""
    np.random.seed(seed)
    returns = np.array(returns)
    observed_mean = np.mean(returns)
    n = len(returns)

    # H0: 收益均值为0
    # 将收益中心化（减去均值），使其均值为0
    centered = returns - observed_mean

    # Bootstrap：从中心化数据中重复抽样
    bootstrap_means = np.zeros(n_bootstrap)
    for i in range(n_bootstrap):
        sample = np.random.choice(centered, size=n, replace=True)
        bootstrap_means[i] = np.mean(sample)

    # 双边p值
    p_value = np.mean(np.abs(bootstrap_means) >= np.abs(observed_mean))

    # 置信区间
    ci_lower = np.percentile(bootstrap_means, 2.5)
    ci_upper = np.percentile(bootstrap_means, 97.5)

    # 实际收益率在bootstrap分布中的分位数
    percentile = np.mean(bootstrap_means < observed_mean)

    return {
        'observed_mean': observed_mean,
        'bootstrap_mean': np.mean(bootstrap_means),
        'bootstrap_std': np.std(bootstrap_means),
        'p_value': p_value,
        'ci_95': (ci_lower, ci_upper),
        'percentile': percentile,
        'significant_95': p_value < 0.05,
        'significant_99': p_value < 0.01,
        'bootstrap_means': bootstrap_means,
    }


def multiple_testing_correction(p_values, method='bonferroni'):
    """多重检验修正"""
    p_values = np.array(p_values)
    n = len(p_values)

    if method == 'bonferroni':
        corrected = np.minimum(p_values * n, 1.0)
    elif method == 'holm':
        sorted_idx = np.argsort(p_values)
        corrected = np.zeros(n)
        for rank, idx in enumerate(sorted_idx):
            corrected[idx] = min(p_values[idx] * (n - rank), 1.0)
    elif method == 'bh':
        sorted_idx = np.argsort(p_values)
        corrected = np.zeros(n)
        for rank, idx in enumerate(sorted_idx):
            corrected[idx] = min(p_values[idx] * n / (rank + 1), 1.0)
    else:
        corrected = p_values

    return corrected


# ============================================================
# 5. 布林带均值回归策略
# ============================================================

class BollingerBandStrategy:
    """布林带均值回归策略（含多种改进）"""

    def __init__(self, ma_period=20, std_mult=2.0, use_trend_filter=True,
                 trend_ma=200, use_rsi_confirm=True, rsi_threshold=30,
                 use_volume_confirm=True, require_confirmation_candle=True):
        self.ma_period = ma_period
        self.std_mult = std_mult
        self.use_trend_filter = use_trend_filter
        self.trend_ma = trend_ma
        self.use_rsi_confirm = use_rsi_confirm
        self.rsi_threshold = rsi_threshold
        self.use_volume_confirm = use_volume_confirm
        self.require_confirmation_candle = require_confirmation_candle

    def calc_ma(self, prices, period):
        ma = np.full(len(prices), np.nan)
        for i in range(period - 1, len(prices)):
            ma[i] = np.mean(prices[i - period + 1:i + 1])
        return ma

    def calc_rolling_std(self, prices, period):
        std = np.full(len(prices), np.nan)
        for i in range(period - 1, len(prices)):
            std[i] = np.std(prices[i - period + 1:i + 1])
        return std

    def calc_rsi(self, prices, period=14):
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        rsi = np.full(len(prices), np.nan)

        for i in range(period, len(prices)):
            avg_gain = np.mean(gains[i - period:i])
            avg_loss = np.mean(losses[i - period:i])
            if avg_loss == 0:
                rsi[i] = 100
            else:
                rs = avg_gain / avg_loss
                rsi[i] = 100 - 100 / (1 + rs)
        return rsi

    def generate_signals(self, prices, volumes=None):
        n = len(prices)
        ma = self.calc_ma(prices, self.ma_period)
        std = self.calc_rolling_std(prices, self.ma_period)

        upper = ma + self.std_mult * std
        lower = ma - self.std_mult * std

        trend_ma = self.calc_ma(prices, self.trend_ma) if self.use_trend_filter else None
        rsi = self.calc_rsi(prices) if self.use_rsi_confirm else None

        signals = np.zeros(n, dtype=int)
        # 1=buy, -1=sell, 0=hold

        position = 0  # 0=空仓, 1=持仓
        entry_price = 0

        for i in range(max(self.ma_period, self.trend_ma), n):
            if np.isnan(ma[i]) or np.isnan(lower[i]) or np.isnan(upper[i]):
                continue

            # 卖出条件：回到中轨或有盈利
            if position == 1:
                if prices[i] >= ma[i] or prices[i] >= entry_price * 1.03:
                    signals[i] = -1
                    position = 0
                continue

            # 买入条件检查
            if position == 0:
                # 基本条件：价格低于下轨
                if prices[i] >= lower[i]:
                    continue

                buy_signal = True

                # 改进1：趋势过滤器（价格必须在长期均线上方）
                if self.use_trend_filter and trend_ma is not None:
                    if not np.isnan(trend_ma[i]) and prices[i] < trend_ma[i]:
                        buy_signal = False

                # 改进2：RSI确认（RSI必须低于阈值）
                if self.use_rsi_confirm and rsi is not None:
                    if not np.isnan(rsi[i]) and rsi[i] > self.rsi_threshold:
                        buy_signal = False

                # 改进3：成交量确认（缩量表明抛压衰竭）
                if self.use_volume_confirm and volumes is not None:
                    if i >= 20:
                        avg_vol = np.mean(volumes[i - 20:i])
                        if volumes[i] > avg_vol * 0.8:
                            buy_signal = False

                # 改进4：确认K线（等待阳线确认）
                if self.require_confirmation_candle and i > 0:
                    if prices[i] <= prices[i - 1]:
                        buy_signal = False

                if buy_signal:
                    signals[i] = 1
                    position = 1
                    entry_price = prices[i]

        return signals, {'ma': ma, 'upper': upper, 'lower': lower, 'rsi': rsi, 'trend_ma': trend_ma}


# ============================================================
# 6. 简单回测引擎（支持布林带策略）
# ============================================================

class SimpleBacktest:
    def __init__(self, initial_capital=100000, commission=0.00025, stamp_tax=0.001, slippage=0.0005):
        self.capital = initial_capital
        self.commission = commission
        self.stamp_tax = stamp_tax
        self.slippage = slippage

    def run(self, prices, signals):
        n = len(prices)
        cash = self.capital
        shares = 0
        portfolio = np.zeros(n)
        trades = []

        for i in range(n):
            sig = signals[i] if i < len(signals) else 0
            price = prices[i]

            if sig == 1 and cash > 0:  # Buy
                buy_price = price * (1 + self.slippage)
                new_shares = cash / buy_price
                cost = new_shares * buy_price * self.commission
                shares += new_shares
                cash -= (new_shares * buy_price + cost)
                trades.append((i, 'BUY', price, new_shares))

            elif sig == -1 and shares > 0:  # Sell
                sell_price = price * (1 - self.slippage)
                sell_value = shares * sell_price
                cost = sell_value * (self.commission + self.stamp_tax)
                cash += sell_value - cost
                trades.append((i, 'SELL', price, shares))
                shares = 0

            portfolio[i] = cash + shares * price

        return {'portfolio': portfolio, 'trades': trades, 'final_value': portfolio[-1]}


# ============================================================
# 7. 风险平价组合优化
# ============================================================

def risk_parity_weights(returns, target_risk_contrib=None):
    """计算风险平价权重"""
    n_assets = returns.shape[1]
    cov = np.cov(returns, rowvar=False)

    if target_risk_contrib is None:
        target_risk_contrib = np.ones(n_assets) / n_assets

    # 初始权重：等权
    w = np.ones(n_assets) / n_assets

    # 迭代求解（简单梯度下降）
    learning_rate = 0.01
    for iteration in range(5000):
        # 组合波动率
        port_vol = np.sqrt(w @ cov @ w)

        if port_vol < 1e-10:
            break

        # 边际风险贡献
        mrc = cov @ w / port_vol

        # 风险贡献
        rc = w * mrc

        # 风险贡献比例
        rc_pct = rc / np.sum(rc)

        # 梯度：使风险贡献接近目标
        grad = rc_pct - target_risk_contrib
        w = w - learning_rate * grad

        # 投影回合法空间
        w = np.maximum(w, 1e-8)
        w = w / np.sum(w)

        if np.max(np.abs(grad)) < 1e-8:
            break

    return w


def markowitz_optimization(returns, target_return=None, risk_aversion=1.0):
    """简化的Markowitz均值-方差优化"""
    n_assets = returns.shape[1]
    mean_ret = np.mean(returns, axis=0) * 12  # 年化
    cov = np.cov(returns, rowvar=False) * 12  # 年化

    # 目标：max(w'r - λ·w'Σw)，约束：Σw=1, w≥0
    # 使用简单的网格搜索 + 梯度下降
    if target_return is not None:
        # 在给定收益目标下最小化风险
        best_w = None
        best_risk = np.inf

        for _ in range(2000):
            w = np.random.dirichlet(np.ones(n_assets))
            port_ret = w @ mean_ret
            port_risk = np.sqrt(w @ cov @ w)
            if port_ret >= target_return and port_risk < best_risk:
                best_risk = port_risk
                best_w = w.copy()

        if best_w is None:
            best_w = np.ones(n_assets) / n_assets
    else:
        # 最大化效用函数
        best_w = np.ones(n_assets) / n_assets
        best_utility = -np.inf

        for _ in range(3000):
            w = np.random.dirichlet(np.ones(n_assets))
            port_ret = w @ mean_ret
            port_risk = np.sqrt(w @ cov @ w)
            utility = port_ret - risk_aversion * port_risk ** 2
            if utility > best_utility:
                best_utility = utility
                best_w = w.copy()

    return best_w


def efficient_frontier(returns, n_points=50):
    """计算有效前沿"""
    n_assets = returns.shape[1]
    mean_ret = np.mean(returns, axis=0) * 12
    cov = np.cov(returns, rowvar=False) * 12

    # 先找出最小风险和最大收益组合
    min_ret = np.min(mean_ret)
    max_ret = np.max(mean_ret)

    target_returns = np.linspace(min_ret * 1.1, max_ret * 0.9, n_points)
    frontier_risks = []
    frontier_weights = []

    for tr in target_returns:
        w = markowitz_optimization(returns, target_return=tr)
        port_risk = np.sqrt(w @ cov @ w)
        frontier_risks.append(port_risk)
        frontier_weights.append(w)

    return target_returns, frontier_risks, frontier_weights


# ============================================================
# 8. Brinson绩效归因
# ============================================================

def brinson_attribution(portfolio_weights, portfolio_returns,
                        benchmark_weights, benchmark_returns,
                        industry_labels=None):
    """Brinson归因分析"""
    n_sectors = len(portfolio_weights)

    # 基准收益
    bench_total = np.sum(benchmark_weights * benchmark_returns)

    # 配置贡献：超配/低配行业带来的收益
    allocation_effect = np.sum((portfolio_weights - benchmark_weights) * benchmark_returns)

    # 选股贡献：在行业内选股带来的收益
    selection_effect = np.sum(benchmark_weights * (portfolio_returns - benchmark_returns))

    # 交互项
    interaction = np.sum((portfolio_weights - benchmark_weights) *
                         (portfolio_returns - benchmark_returns))

    # 组合总收益
    portfolio_total = np.sum(portfolio_weights * portfolio_returns)

    # 超额收益
    excess_return = portfolio_total - bench_total

    return {
        'portfolio_return': portfolio_total,
        'benchmark_return': bench_total,
        'excess_return': excess_return,
        'allocation_effect': allocation_effect,
        'selection_effect': selection_effect,
        'interaction': interaction,
        # 分行业明细
        'sector_allocation': (portfolio_weights - benchmark_weights) * benchmark_returns,
        'sector_selection': benchmark_weights * (portfolio_returns - benchmark_returns),
        'sector_interaction': (portfolio_weights - benchmark_weights) *
                              (portfolio_returns - benchmark_returns),
    }


def fama_french_attribution(portfolio_returns, market_returns, smb=None, hml=None, mom=None):
    """Fama-French因子归因（简化版）"""
    import numpy as np

    n = min(len(portfolio_returns), len(market_returns))

    y = portfolio_returns[:n]
    X_cols = [market_returns[:n]]

    if smb is not None:
        X_cols.append(smb[:n])
    if hml is not None:
        X_cols.append(hml[:n])
    if mom is not None:
        X_cols.append(mom[:n])

    X = np.column_stack(X_cols)
    # OLS回归：y = α + β₁X₁ + β₂X₂ + ...
    X_with_const = np.column_stack([np.ones(n), X])

    try:
        coeffs = np.linalg.lstsq(X_with_const, y, rcond=None)[0]
        alpha = coeffs[0]
        betas = coeffs[1:]

        residuals = y - X_with_const @ coeffs
        alpha_se = np.std(residuals) / np.sqrt(n)
        t_stat = alpha / alpha_se if alpha_se > 0 else 0

        return {
            'alpha': alpha,
            'alpha_t_stat': t_stat,
            'betas': betas,
            'r_squared': 1 - np.var(residuals) / np.var(y) if np.var(y) > 0 else 0,
        }
    except np.linalg.LinAlgError:
        return {'alpha': np.nan, 'alpha_t_stat': np.nan, 'betas': [], 'r_squared': 0}


# ============================================================
# 9. 交易成本影响分析
# ============================================================

def transaction_cost_impact(strategy_returns, turnover_rate, frequency_per_year,
                             commission=0.00025, stamp_tax=0.001,
                             spread=0.001, impact_factor=0.0005):
    """计算交易成本对策略收益的影响"""
    returns = np.array(strategy_returns)
    n = len(returns)

    # 单次交易成本
    buy_cost = commission + spread * 0.5 + impact_factor
    sell_cost = commission + stamp_tax + spread * 0.5 + impact_factor
    round_trip_cost = buy_cost + sell_cost

    # 年度换手总成本
    annual_turnover = turnover_rate * frequency_per_year
    annual_cost_pct = round_trip_cost * annual_turnover

    # 策略年化收益
    total_return = np.prod(1 + returns) - 1
    years = n / frequency_per_year
    annual_return = (1 + total_return) ** (1 / years) - 1

    # 扣除成本后
    net_annual_return = annual_return - annual_cost_pct

    # 成本对夏普比率的影响
    excess = returns - np.mean(returns)
    annual_vol = np.std(returns) * np.sqrt(frequency_per_year)

    sharpe_gross = annual_return / annual_vol if annual_vol > 0 else 0
    sharpe_net = net_annual_return / annual_vol if annual_vol > 0 else 0

    return {
        'round_trip_cost_pct': round_trip_cost * 100,
        'annual_turnover': annual_turnover,
        'annual_cost_pct': annual_cost_pct * 100,
        'gross_annual_return': annual_return * 100,
        'net_annual_return': net_annual_return * 100,
        'cost_drag': annual_cost_pct * 100,
        'sharpe_gross': sharpe_gross,
        'sharpe_net': sharpe_net,
        'is_profitable': net_annual_return > 0,
    }


def simulate_turnover_impact(strategy_returns, frequency=12):
    """模拟不同换手率对策略的影响"""
    returns = np.array(strategy_returns)
    total_return = np.prod(1 + returns) - 1
    years = len(returns) / frequency
    annual_return = (1 + total_return) ** (1 / years) - 1

    turnovers = np.linspace(0.1, 2.0, 20)  # 年换手率从10%到200%
    net_returns = []

    for turnover in turnovers:
        annual_cost = (0.00025 + 0.001 + 0.001 + 0.0005) * turnover * frequency
        net_ret = annual_return - annual_cost
        net_returns.append(net_ret)

    return turnovers, net_returns


# ============================================================
# 10. 时间序列交叉验证
# ============================================================

def timeseries_cv_demo(stocks, factor_name, n_months, train_months=36, test_months=12):
    """时间序列交叉验证（滚动窗口）"""
    total_months = n_months - 1

    if total_months < train_months + test_months:
        return {'error': f'数据不足: {total_months} < {train_months + test_months}'}

    results = []
    start_month = 0

    while start_month + train_months + test_months <= total_months:
        train_start = start_month
        train_end = start_month + train_months
        test_start = train_end
        test_end = test_start + test_months

        # 训练集IC
        train_ics = []
        for m in range(train_start, train_end):
            factor_vals = []
            fwd_rets = []
            for name, data in stocks.items():
                if m < len(data.get(factor_name, [])) and m < len(data.get('future_ret_1m', [])):
                    fv = data[factor_name][m]
                    fr = data['future_ret_1m'][m]
                    factor_vals.append(fv)
                    fwd_rets.append(fr)

            if len(factor_vals) >= 10:
                ic = FactorICAnalyzer.rank_ic(np.array(factor_vals), np.array(fwd_rets))
                if not np.isnan(ic):
                    train_ics.append(ic)

        # 测试集IC
        test_ics = []
        for m in range(test_start, test_end):
            factor_vals = []
            fwd_rets = []
            for name, data in stocks.items():
                if m < len(data.get(factor_name, [])) and m < len(data.get('future_ret_1m', [])):
                    fv = data[factor_name][m]
                    fr = data['future_ret_1m'][m]
                    factor_vals.append(fv)
                    fwd_rets.append(fr)

            if len(factor_vals) >= 10:
                ic = FactorICAnalyzer.rank_ic(np.array(factor_vals), np.array(fwd_rets))
                if not np.isnan(ic):
                    test_ics.append(ic)

        results.append({
            'window': f'{train_start}-{train_end}→{test_end}',
            'train_ic_mean': np.mean(train_ics) if train_ics else np.nan,
            'test_ic_mean': np.mean(test_ics) if test_ics else np.nan,
            'train_ic_ir': np.mean(train_ics) / np.std(train_ics) if train_ics and np.std(train_ics) > 0 else np.nan,
            'test_ic_ir': np.mean(test_ics) / np.std(test_ics) if test_ics and np.std(test_ics) > 0 else np.nan,
            'train_ics': train_ics,
            'test_ics': test_ics,
        })

        start_month += test_months

    return results


# ============================================================
# 11. 可视化
# ============================================================

def plot_ic_analysis(ic_results, data):
    """绘制IC分析综合图"""
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    stocks = data['stocks']
    n_months = data['n_months']

    # 图1：各因子IC均值对比
    ax = axes[0, 0]
    factors = []
    ic_means = []
    ic_stds = []
    for name, res in ic_results.items():
        if 'error' not in res:
            factors.append(res['factor'])
            ic_means.append(res['ic_mean'])
            ic_stds.append(res['ic_std'])

    colors_bar = ['#A23B72' if m > 0 else '#2E86AB' for m in ic_means]
    bars = ax.bar(range(len(factors)), ic_means, color=colors_bar, alpha=0.8)
    ax.errorbar(range(len(factors)), ic_means, yerr=ic_stds, fmt='none',
                ecolor='#333333', capsize=5, capthick=1)
    ax.axhline(y=0, color='gray', linewidth=0.5)
    ax.axhline(y=0.03, color='#F39C12', linestyle='--', alpha=0.7, label='中等因子阈值(0.03)')
    ax.set_xticks(range(len(factors)))
    ax.set_xticklabels(factors)
    ax.set_ylabel('Rank IC均值')
    ax.set_title('各因子IC均值 ± 1标准差')
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3, axis='y')

    # 图2：IC时间序列
    ax = axes[0, 1]
    for name, res in ic_results.items():
        if 'ic_series' in res:
            ax.plot(res['ic_series'], alpha=0.7, linewidth=0.8, label=res['factor'])
    ax.axhline(y=0, color='gray', linewidth=0.5)
    ax.set_xlabel('月份')
    ax.set_ylabel('Rank IC')
    ax.set_title('IC时间序列')
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)

    # 图3：IC衰减曲线
    ax = axes[0, 2]
    analyzer = FactorICAnalyzer()
    for factor_name in ['pe', 'roe', 'momentum_12m', 'volatility']:
        decays = analyzer.ic_decay(stocks, factor_name, n_months, max_lag=12)
        ax.plot(range(1, len(decays)+1), decays, 'o-', linewidth=1.5, markersize=5,
                label=factor_name)
    ax.axhline(y=0, color='gray', linewidth=0.5)
    ax.set_xlabel('预测期（月）')
    ax.set_ylabel('IC均值')
    ax.set_title('IC衰减曲线')
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)

    # 图4：分层回测各组收益
    ax = axes[1, 0]
    qb = quantile_backtest(stocks, 'pe', n_months, n_quantiles=5)
    if qb['quantile_returns']:
        group_cumrets = []
        for q in range(5):
            cumret = np.cumprod(1 + np.array(qb['quantile_returns'][q])) - 1
            group_cumrets.append(cumret)
            ax.plot(cumret * 100, linewidth=1.2, label=f'Q{q+1}')
        ax.set_xlabel('月份')
        ax.set_ylabel('累计收益 (%)')
        ax.set_title('PE因子分层回测（Q1=低PE, Q5=高PE）')
        ax.legend(fontsize=7, ncol=5, loc='upper left')
        ax.grid(True, alpha=0.3)

    # 图5：多空组合收益
    ax = axes[1, 1]
    if qb['long_short_returns']:
        ls_cum = np.cumprod(1 + np.array(qb['long_short_returns'])) - 1
        ax.fill_between(range(len(ls_cum)), 0, ls_cum * 100,
                         color='#A23B72' if ls_cum[-1] > 0 else '#2E86AB', alpha=0.3)
        ax.plot(ls_cum * 100, color='#A23B72', linewidth=1.5)
        ax.axhline(y=0, color='gray', linewidth=0.5)
        ax.set_xlabel('月份')
        ax.set_ylabel('累计收益 (%)')
        ax.set_title('PE因子多空组合（Q1买入 - Q5卖出）')
        ax.grid(True, alpha=0.3)

    # 图6：IC_IR对比
    ax = axes[1, 2]
    ic_irs = []
    for name, res in ic_results.items():
        if 'ic_ir' in res:
            ic_irs.append((res['factor'], res['ic_ir']))
    ic_irs.sort(key=lambda x: x[1], reverse=True)
    labels = [x[0] for x in ic_irs]
    values = [x[1] for x in ic_irs]
    colors_ir = ['#A23B72' if v > 0.3 else '#2E86AB' for v in values]
    ax.barh(labels, values, color=colors_ir, alpha=0.8)
    ax.axvline(x=0.3, color='#F39C12', linestyle='--', alpha=0.7, label='优秀阈值(0.3)')
    ax.set_xlabel('IC_IR')
    ax.set_title('各因子信息比率（IC_IR）')
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3, axis='x')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'adv_ic_analysis.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] IC分析综合图已保存: {path}")


def plot_bootstrap_test(bootstrap_result):
    """绘制Bootstrap检验结果"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 图1：Bootstrap分布
    ax = axes[0]
    means = bootstrap_result['bootstrap_means']
    ax.hist(means, bins=80, color='#2E86AB', alpha=0.7, edgecolor='white', density=True)
    ax.axvline(x=bootstrap_result['observed_mean'], color='#A23B72', linewidth=2,
               label=f'实际均值: {bootstrap_result["observed_mean"]:.4f}')
    ax.axvline(x=0, color='gray', linewidth=0.5, linestyle='--')
    ci_low, ci_high = bootstrap_result['ci_95']
    ax.axvline(x=ci_low, color='#F39C12', linewidth=1, linestyle='--', alpha=0.7)
    ax.axvline(x=ci_high, color='#F39C12', linewidth=1, linestyle='--', alpha=0.7)

    sig_text = '显著!' if bootstrap_result['significant_95'] else '不显著'
    color = '#A23B72' if bootstrap_result['significant_95'] else '#2E86AB'
    ax.set_title(f'Bootstrap检验：策略超额收益（{sig_text}）', color=color, fontsize=13)
    ax.set_xlabel('平均收益（H0假设下）')
    ax.set_ylabel('密度')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    # 图2：p值和分位数可视化
    ax = axes[1]
    pct = bootstrap_result['percentile'] * 100
    ax.barh(['超额收益分位数'], [pct], color='#2E86AB' if pct < 95 else '#A23B72', alpha=0.8)
    ax.axvline(x=95, color='#F39C12', linewidth=1.5, linestyle='--', label='95%分位线')
    ax.set_xlim(0, 100)
    ax.set_xlabel('分位数 (%)')
    ax.set_title(f'实际收益在随机分布中的位置: {pct:.1f}%')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3, axis='x')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'adv_bootstrap_test.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] Bootstrap检验图已保存: {path}")


def plot_bollinger_strategy(prices, signals, indicators):
    """绘制布林带策略回测"""
    bt = SimpleBacktest()
    result = bt.run(prices, signals)

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [2.5, 1, 1]})

    n = len(prices)
    days = np.arange(n)

    # 图1：价格 + 布林带 + 买卖点
    ax = axes[0]
    ax.plot(days, prices, linewidth=1, color='#333333', alpha=0.8, label='价格')
    ax.plot(days, indicators['ma'], linewidth=1, color='#2E86AB', alpha=0.7, label=f'MA{len(prices)}')
    ax.fill_between(days, indicators['lower'], indicators['upper'],
                     color='#2E86AB', alpha=0.1, label='布林带(±2σ)')
    ax.plot(days, indicators['upper'], linewidth=0.8, color='#2E86AB', alpha=0.4, linestyle='--')
    ax.plot(days, indicators['lower'], linewidth=0.8, color='#2E86AB', alpha=0.4, linestyle='--')

    if indicators['trend_ma'] is not None:
        ax.plot(days, indicators['trend_ma'], linewidth=1, color='#F39C12', alpha=0.6,
                linestyle='--', label='趋势MA')

    for trade in result['trades']:
        idx, action, price, _ = trade
        if action == 'BUY':
            ax.scatter(idx, price, color='#A23B72', marker='^', s=80, zorder=5)
        else:
            ax.scatter(idx, price, color='#2E86AB', marker='v', s=80, zorder=5)

    ax.scatter([], [], color='#A23B72', marker='^', s=80, label='买入')
    ax.scatter([], [], color='#2E86AB', marker='v', s=80, label='卖出')
    ax.set_ylabel('价格')
    ax.set_title('布林带均值回归策略')
    ax.legend(fontsize=7, loc='upper left', ncol=2)
    ax.grid(True, alpha=0.3)

    # 图2：RSI
    ax = axes[1]
    if indicators['rsi'] is not None:
        ax.plot(days, indicators['rsi'], linewidth=1, color='#A23B72', alpha=0.7)
        ax.axhline(y=70, color='#E74C3C', linestyle='--', alpha=0.5, linewidth=0.8)
        ax.axhline(y=30, color='#27AE60', linestyle='--', alpha=0.5, linewidth=0.8)
    ax.set_ylabel('RSI')
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3)

    # 图3：净值曲线
    ax = axes[2]
    portfolio = result['portfolio']
    ax.plot(days, portfolio / 100000, linewidth=1.2, color='#A23B72', label='策略净值')
    bh = prices / prices[0]
    ax.plot(days, bh, linewidth=1, color='gray', alpha=0.5, label='买入持有')
    ax.set_xlabel('交易日')
    ax.set_ylabel('净值')
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'adv_bollinger_strategy.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] 布林带策略图已保存: {path}")


def plot_risk_parity(asset_returns, labels, rp_weights, ew_weights, mvo_weights):
    """绘制风险平价组合对比"""
    n_assets = len(labels)

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    weight_sets = [
        ('等权', ew_weights, '#2E86AB'),
        ('风险平价', rp_weights, '#A23B72'),
        ('最大夏普', mvo_weights, '#F39C12'),
    ]

    for ax_idx, (title, weights, color) in enumerate(weight_sets):
        ax = axes[ax_idx]
        wedges, texts, autotexts = ax.pie(
            weights, labels=labels, autopct='%1.1f%%',
            colors=plt.cm.Set3(np.linspace(0, 1, n_assets)),
            startangle=90, pctdistance=0.85
        )
        for at in autotexts:
            at.set_fontsize(8)
        ax.set_title(title, fontsize=12)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'adv_risk_parity.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] 风险平价组合图已保存: {path}")


def plot_efficient_frontier(target_returns, frontier_risks, asset_returns, labels,
                            rp_weights, mvo_weights, ew_weights):
    """绘制有效前沿"""
    fig, ax = plt.subplots(1, 1, figsize=(10, 7))

    mean_ret = np.mean(asset_returns, axis=0) * 12
    vols = np.std(asset_returns, axis=0) * np.sqrt(12)

    # 有效前沿
    ax.plot(frontier_risks, target_returns * 100, linewidth=2, color='#2E86AB', label='有效前沿')

    # 单个资产
    ax.scatter(vols * 100, mean_ret * 100, c='#333333', s=80, alpha=0.7, zorder=5)
    for i, label in enumerate(labels):
        ax.annotate(label, (vols[i] * 100, mean_ret[i] * 100),
                     fontsize=8, xytext=(5, 5), textcoords='offset points')

    # 各组合
    for w, name, color, marker in [
        (rp_weights, '风险平价', '#A23B72', 'D'),
        (mvo_weights, '最大夏普', '#F39C12', 's'),
        (ew_weights, '等权', '#27AE60', 'o'),
    ]:
        port_ret = w @ mean_ret * 100
        port_risk = np.sqrt(w @ np.cov(asset_returns, rowvar=False) * 12 @ w) * 100
        ax.scatter(port_risk, port_ret, c=color, s=200, marker=marker,
                    zorder=10, edgecolors='white', linewidths=1.5, label=name)

    ax.set_xlabel('年化波动率 (%)')
    ax.set_ylabel('年化收益率 (%)')
    ax.set_title('有效前沿与最优组合')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'adv_efficient_frontier.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] 有效前沿图已保存: {path}")


def plot_attribution(attrib_result):
    """绘制Brinson归因图"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 图1：归因贡献瀑布图
    ax = axes[0]
    effects = [
        ('基准收益', attrib_result['benchmark_return'] * 100),
        ('配置贡献', attrib_result['allocation_effect'] * 100),
        ('选股贡献', attrib_result['selection_effect'] * 100),
        ('交互项', attrib_result['interaction'] * 100),
        ('组合收益', attrib_result['portfolio_return'] * 100),
    ]
    labels = [e[0] for e in effects]
    values = [e[1] for e in effects]
    colors = ['#7F8C8D', '#2E86AB', '#A23B72', '#F39C12', '#27AE60']

    cum = attrib_result['benchmark_return'] * 100
    ax.bar(0, cum, color=colors[0], alpha=0.8, label='基准')
    ax.bar(1, values[1], bottom=cum, color=colors[1], alpha=0.8, label='配置')
    cum += values[1]
    ax.bar(2, values[2], bottom=cum, color=colors[2], alpha=0.8, label='选股')
    cum += values[2]
    ax.bar(3, values[3], bottom=cum, color=colors[3], alpha=0.8, label='交互')
    ax.set_xticks(range(4))
    ax.set_xticklabels(['基准', '+配置', '+选股', '+交互'])
    ax.axhline(y=attrib_result['portfolio_return'] * 100, color='#27AE60',
               linewidth=1.5, linestyle='--', label='组合总收益')
    ax.set_ylabel('收益率 (%)')
    ax.set_title('Brinson绩效归因')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')

    # 图2：贡献占比饼图
    ax = axes[1]
    pos_contrib = max(0, attrib_result['allocation_effect'])
    pos_contrib += max(0, attrib_result['selection_effect'])
    pos_contrib += max(0, attrib_result['interaction'])
    neg_contrib = abs(min(0, attrib_result['allocation_effect']))
    neg_contrib += abs(min(0, attrib_result['selection_effect']))
    neg_contrib += abs(min(0, attrib_result['interaction']))
    residual = attrib_result['excess_return'] - (pos_contrib - neg_contrib)

    labels_pie = ['配置(+)', '选股(+)', '交互(+)', '配置贡献(-)', '选股(-)', '交互(-)']
    sizes_pie = [
        max(0, attrib_result['allocation_effect'] * 100),
        max(0, attrib_result['selection_effect'] * 100),
        max(0, attrib_result['interaction'] * 100),
        abs(min(0, attrib_result['allocation_effect'] * 100)),
        abs(min(0, attrib_result['selection_effect'] * 100)),
        abs(min(0, attrib_result['interaction'] * 100)),
    ]
    sizes_pie = [s for s in sizes_pie if s > 0.001]
    labels_pie = [l for l, s in zip(labels_pie, sizes_pie) if s > 0.001]

    if sizes_pie:
        ax.pie(sizes_pie, labels=labels_pie, autopct='%1.1f%%',
               colors=plt.cm.RdYlGn(np.linspace(0.2, 0.8, len(sizes_pie))),
               startangle=90)
    ax.set_title(f'超额收益归因分解\n(总超额: {attrib_result["excess_return"]*100:.2f}%)')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'adv_attribution.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] 绩效归因图已保存: {path}")


def plot_cost_impact(turnovers, net_returns, cost_result):
    """绘制交易成本影响"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    turnovers = np.array(turnovers).flatten()
    net_returns = np.array(net_returns).flatten()

    # 图1：换手率vs净收益
    ax = axes[0]
    gross = cost_result['gross_annual_return']
    colors = ['#27AE60' if r > 0 else '#E74C3C' for r in net_returns]
    ax.bar(range(len(turnovers)), net_returns * 100, color=colors, alpha=0.7)
    ax.axhline(y=0, color='gray', linewidth=0.5)
    ax.axhline(y=gross, color='#A23B72', linewidth=1.5, linestyle='--',
               label=f'无成本收益: {gross:.1f}%')
    ax.set_xticks(range(0, len(turnovers), 4))
    ax.set_xticklabels([f'{t:.0%}' for t in turnovers[::4]])
    ax.set_xlabel('年换手率')
    ax.set_ylabel('年化净收益 (%)')
    ax.set_title('交易成本对策略收益的影响')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3, axis='y')

    # 图2：成本分解
    ax = axes[1]
    cost_items = {
        '佣金(双边)': 0.00025 * 2,
        '印花税(卖出)': 0.001,
        '买卖价差': 0.001,
        '冲击成本(估)': 0.001,
    }
    item_labels = list(cost_items.keys())
    item_values = [v * 100 for v in cost_items.values()]
    colors_bp = ['#3498DB', '#E74C3C', '#F39C12', '#9B59B6']
    ax.barh(item_labels, item_values, color=colors_bp, alpha=0.8)
    ax.set_xlabel('成本 (%)')
    ax.set_title('单次完整交易成本分解')
    ax.grid(True, alpha=0.3, axis='x')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'adv_cost_impact.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] 交易成本影响图已保存: {path}")


def plot_timeseries_cv(cv_results):
    """绘制时间序列交叉验证结果"""
    n_windows = len(cv_results)
    if n_windows == 0:
        return

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 图1：训练IC vs 测试IC
    ax = axes[0]
    x = np.arange(n_windows)
    w = 0.35
    train_ics = [r['train_ic_mean'] for r in cv_results]
    test_ics = [r['test_ic_mean'] for r in cv_results]

    ax.bar(x - w/2, train_ics, w, color='#F39C12', alpha=0.8, label='训练集IC')
    ax.bar(x + w/2, test_ics, w, color='#2E86AB', alpha=0.8, label='测试集IC')
    ax.axhline(y=0, color='gray', linewidth=0.5)
    ax.axhline(y=np.mean(train_ics), color='#F39C12', linestyle='--', alpha=0.5)
    ax.axhline(y=np.mean(test_ics), color='#2E86AB', linestyle='--', alpha=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels([r['window'] for r in cv_results], fontsize=7, rotation=30)
    ax.set_ylabel('Rank IC均值')
    ax.set_title('时间序列交叉验证：训练 vs 测试 IC')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3, axis='y')

    # 图2：IC_IR对比
    ax = axes[1]
    train_irs = [r['train_ic_ir'] for r in cv_results]
    test_irs = [r['test_ic_ir'] for r in cv_results]

    ax.bar(x - w/2, train_irs, w, color='#F39C12', alpha=0.8, label='训练集IC_IR')
    ax.bar(x + w/2, test_irs, w, color='#2E86AB', alpha=0.8, label='测试集IC_IR')
    ax.axhline(y=0.3, color='#27AE60', linestyle='--', alpha=0.7, label='优秀阈值(0.3)')
    ax.set_xticks(x)
    ax.set_xticklabels([r['window'] for r in cv_results], fontsize=7, rotation=30)
    ax.set_ylabel('IC_IR')
    ax.set_title('时间序列交叉验证：训练 vs 测试 IC_IR')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'adv_timeseries_cv.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] 时间序列交叉验证图已保存: {path}")


# ============================================================
# 演示函数
# ============================================================

def demo_ic_analysis(data):
    """演示因子IC分析"""
    print("\n" + "=" * 60)
    print("  进阶1：因子IC分析")
    print("=" * 60)

    analyzer = FactorICAnalyzer()
    stocks = data['stocks']
    n_months = data['n_months']

    ic_results = {}
    for factor_name in ['pe', 'roe', 'momentum_12m', 'volatility']:
        result = analyzer.analyze_factor(stocks, factor_name, n_months, ic_method='rank')
        ic_results[factor_name] = result

        if 'error' not in result:
            print(f"\n  📊 {factor_name}因子分析：")
            print(f"    IC均值:     {result['ic_mean']:.4f}")
            print(f"    IC标准差:   {result['ic_std']:.4f}")
            print(f"    IC_IR:      {result['ic_ir']:.2f}")
            print(f"    IC>0比例:   {result['ic_positive_ratio']:.1%}")
            print(f"    t统计量:    {result['t_statistic']:.2f}")

            # 判断因子质量
            if abs(result['ic_mean']) >= 0.05 and result['ic_ir'] >= 0.5:
                quality = "强因子 ✓"
            elif abs(result['ic_mean']) >= 0.03 and result['ic_ir'] >= 0.3:
                quality = "中等因子"
            elif abs(result['ic_mean']) >= 0.02:
                quality = "弱因子（注意交易成本）"
            else:
                quality = "可能无预测能力"
            print(f"    因子质量:   {quality}")

    # IC衰减
    print(f"\n  📉 IC衰减分析（PE因子）：")
    decays = analyzer.ic_decay(stocks, 'pe', n_months, max_lag=6)
    for lag, ic in enumerate(decays, 1):
        if not np.isnan(ic):
            print(f"    滞后{lag}月: IC = {ic:.4f}")

    return ic_results


def demo_quantile_backtest(data):
    """演示分层回测"""
    print("\n" + "=" * 60)
    print("  进阶2：分层回测（Quantile Analysis）")
    print("=" * 60)

    n_months = data['n_months']
    qb = quantile_backtest(data['stocks'], 'pe', n_months, n_quantiles=5)

    if qb['quantile_returns']:
        print(f"\n  PE因子5分组回测：")
        print(f"  {'分组':<8s} {'平均月收益':>12s} {'年化收益':>12s} {'累计收益':>12s}")
        print(f"  {'-'*8} {'-'*12} {'-'*12} {'-'*12}")

        for q in range(5):
            monthly = np.mean(qb['quantile_returns'][q])
            annual = (1 + monthly) ** 12 - 1
            cumulative = np.prod(1 + np.array(qb['quantile_returns'][q])) - 1
            print(f"  Q{q+1} (第{q+1}组)   {monthly:>10.2%}   {annual:>10.2%}   {cumulative:>10.2%}")

        if qb['long_short_returns']:
            ls_monthly = np.mean(qb['long_short_returns'])
            ls_annual = (1 + ls_monthly) ** 12 - 1
            ls_cum = np.prod(1 + np.array(qb['long_short_returns'])) - 1
            print(f"  {'-'*8} {'-'*12} {'-'*12} {'-'*12}")
            print(f"  多空(Q1-Q5) {ls_monthly:>10.2%}   {ls_annual:>10.2%}   {ls_cum:>10.2%}")

            # 单调性检查
            q_means = [np.mean(qb['quantile_returns'][q]) for q in range(5)]
            is_monotonic = all(q_means[i] >= q_means[i+1] for i in range(4))
            print(f"\n  因子单调性: {'✓ 单调递减' if is_monotonic else '✗ 不够单调'}")

    return qb


def demo_bootstrap_test(data):
    """演示Bootstrap检验"""
    print("\n" + "=" * 60)
    print("  进阶3：Bootstrap统计显著性检验")
    print("=" * 60)

    # 构造一个策略的超额收益序列（多空组合月收益）
    n_months = data['n_months']
    qb = quantile_backtest(data['stocks'], 'pe', n_months, n_quantiles=5)

    if not qb['long_short_returns']:
        print("  数据不足")
        return None

    ls_returns = np.array(qb['long_short_returns'])
    result = bootstrap_significance_test(ls_returns, n_bootstrap=10000)

    print(f"\n  Bootstrap检验结果（PE因子多空策略）：")
    print(f"    观测月均超额:     {result['observed_mean']:.4%}")
    print(f"    Bootstrap SE:     {result['bootstrap_std']:.4%}")
    print(f"    95% CI:           [{result['ci_95'][0]:.4%}, {result['ci_95'][1]:.4%}]")
    print(f"    p值:              {result['p_value']:.4f}")
    print(f"    分位数:           {result['percentile']:.1%}")
    print(f"    95%显著:          {'✓ 是' if result['significant_95'] else '✗ 否'}")
    print(f"    99%显著:          {'✓ 是' if result['significant_99'] else '✗ 否'}")

    # 多重检验修正演示
    print(f"\n  多重检验修正演示：")
    p_values = np.array([0.001, 0.01, 0.03, 0.05, 0.08, 0.15, 0.30, 0.50])
    print(f"    原始p值:     {p_values}")
    print(f"    Bonferroni:  {multiple_testing_correction(p_values, 'bonferroni')}")
    print(f"    Holm:        {multiple_testing_correction(p_values, 'holm')}")
    print(f"    B-H(FDR):    {multiple_testing_correction(p_values, 'bh')}")

    return result


def demo_bollinger_strategy(data):
    """演示布林带均值回归策略"""
    print("\n" + "=" * 60)
    print("  进阶4：布林带均值回归策略")
    print("=" * 60)

    prices = data['market_index']
    volumes = np.random.lognormal(mean=14, sigma=0.4, size=len(prices))

    # 基础版
    bb_basic = BollingerBandStrategy(ma_period=20, std_mult=2.0,
                                      use_trend_filter=False, use_rsi_confirm=False,
                                      use_volume_confirm=False, require_confirmation_candle=False)
    signals_basic, ind_basic = bb_basic.generate_signals(prices, volumes)
    bt_basic = SimpleBacktest()
    result_basic = bt_basic.run(prices, signals_basic)

    # 改进版
    bb_improved = BollingerBandStrategy(ma_period=20, std_mult=2.0,
                                         use_trend_filter=True, use_rsi_confirm=True,
                                         use_volume_confirm=True, require_confirmation_candle=True)
    signals_improved, ind_improved = bb_improved.generate_signals(prices, volumes)
    bt_improved = SimpleBacktest()
    result_improved = bt_improved.run(prices, signals_improved)

    bh_return = prices[-1] / prices[0] - 1

    print(f"\n  策略对比：")
    print(f"  {'指标':<20s} {'基础布林带':>12s} {'改进布林带':>12s} {'买入持有':>12s}")
    print(f"  {'-'*20} {'-'*12} {'-'*12} {'-'*12}")

    for name, basic_val, improved_val, bh_val in [
        ('最终收益', f'{(result_basic["final_value"]/100000-1)*100:.2f}%',
         f'{(result_improved["final_value"]/100000-1)*100:.2f}%', f'{bh_return*100:.2f}%'),
        ('交易次数', f'{len(result_basic["trades"])}笔', f'{len(result_improved["trades"])}笔', '-'),
    ]:
        print(f"  {name:<20s} {basic_val:>12s} {improved_val:>12s} {bh_val:>12s}")

    return signals_improved, ind_improved


def demo_risk_parity(data):
    """演示风险平价组合优化"""
    print("\n" + "=" * 60)
    print("  进阶5：风险平价组合优化")
    print("=" * 60)

    # 构造5类资产的模拟收益
    np.random.seed(123)
    n_periods = 120  # 10年月度
    n_assets = 5
    labels = ['沪深300', '中证500', '纳斯达克', '黄金', '债券']

    # 各资产的年化收益和波动率
    asset_mean = np.array([0.08, 0.10, 0.12, 0.05, 0.03]) / 12
    asset_vol = np.array([0.22, 0.26, 0.20, 0.16, 0.04])

    # 协方差矩阵（含相关性）
    corr = np.array([
        [1.0, 0.7, 0.4, 0.0, -0.1],
        [0.7, 1.0, 0.3, 0.1, -0.1],
        [0.4, 0.3, 1.0, 0.0, -0.05],
        [0.0, 0.1, 0.0, 1.0, 0.1],
        [-0.1, -0.1, -0.05, 0.1, 1.0],
    ])
    D = np.diag(asset_vol)
    cov = D @ corr @ D

    # 生成服从多元正态的收益
    asset_returns = np.random.multivariate_normal(asset_mean, cov / 12, n_periods)

    # 风险平价权重
    rp_w = risk_parity_weights(asset_returns)

    # Markowitz最大夏普
    mvo_w = markowitz_optimization(asset_returns, risk_aversion=0.5)

    # 等权
    ew_w = np.ones(n_assets) / n_assets

    # 计算各组合的风险贡献
    cov_sample = np.cov(asset_returns, rowvar=False) * 12
    port_vol = lambda w: np.sqrt(w @ cov_sample @ w)
    rc_pct = lambda w: w * (cov_sample @ w) / (w @ cov_sample @ w)

    print(f"\n  组合权重与风险贡献对比：")
    print(f"  {'资产':<12s} {'风险平价权重':>12s} {'风险贡献':>10s} | {'等权权重':>10s} {'风险贡献':>10s}")
    print(f"  {'-'*12} {'-'*12} {'-'*10} | {'-'*10} {'-'*10}")

    rp_rc = rc_pct(rp_w)
    ew_rc = rc_pct(ew_w)

    for i, label in enumerate(labels):
        print(f"  {label:<12s} {rp_w[i]:>11.1%}  {rp_rc[i]:>9.1%}  | {ew_w[i]:>10.1%}  {ew_rc[i]:>10.1%}")

    print(f"\n  {'组合统计':<12s} {'风险平价':>12s} {'等权':>12s} {'最大夏普':>12s}")
    print(f"  {'-'*12} {'-'*12} {'-'*12} {'-'*12}")

    for name, rp_val, ew_val, mvo_val in [
        ('年化收益', f'{rp_w @ np.mean(asset_returns, axis=0) * 12 * 100:.2f}%',
         f'{ew_w @ np.mean(asset_returns, axis=0) * 12 * 100:.2f}%',
         f'{mvo_w @ np.mean(asset_returns, axis=0) * 12 * 100:.2f}%'),
        ('年化波动', f'{port_vol(rp_w)*100:.2f}%', f'{port_vol(ew_w)*100:.2f}%',
         f'{port_vol(mvo_w)*100:.2f}%'),
        ('夏普比率', f'{(rp_w @ np.mean(asset_returns, axis=0) * 12 / port_vol(rp_w)):.2f}',
         f'{(ew_w @ np.mean(asset_returns, axis=0) * 12 / port_vol(ew_w)):.2f}',
         f'{(mvo_w @ np.mean(asset_returns, axis=0) * 12 / port_vol(mvo_w)):.2f}'),
    ]:
        print(f"  {name:<12s} {rp_val:>12s} {ew_val:>12s} {mvo_val:>12s}")

    # 有效前沿
    ef_rets, ef_risks, ef_weights = efficient_frontier(asset_returns)

    return {
        'asset_returns': asset_returns,
        'labels': labels,
        'rp_weights': rp_w,
        'ew_weights': ew_w,
        'mvo_weights': mvo_w,
        'ef_rets': ef_rets,
        'ef_risks': ef_risks,
    }


def demo_attribution():
    """演示绩效归因"""
    print("\n" + "=" * 60)
    print("  进阶6：Brinson绩效归因")
    print("=" * 60)

    # 模拟数据：5个行业
    industries = ['银行', '消费', '科技', '医药', '能源']
    np.random.seed(456)

    # 组合权重（超配科技和消费）
    port_weights = np.array([0.10, 0.30, 0.30, 0.20, 0.10])
    # 基准权重（沪深300近似）
    bench_weights = np.array([0.20, 0.25, 0.20, 0.20, 0.15])

    # 各行业实际收益
    bench_returns = np.array([0.05, 0.15, 0.25, 0.10, 0.08])
    port_returns = np.array([0.06, 0.18, 0.28, 0.09, 0.07])

    result = brinson_attribution(port_weights, port_returns,
                                  bench_weights, bench_returns, industries)

    print(f"\n  归因结果：")
    print(f"    组合收益：    {result['portfolio_return']*100:+.2f}%")
    print(f"    基准收益：    {result['benchmark_return']*100:+.2f}%")
    print(f"    超额收益：    {result['excess_return']*100:+.2f}%")
    print(f"    ─────────────────────────")
    print(f"    配置贡献：    {result['allocation_effect']*100:+.2f}%")
    print(f"    选股贡献：    {result['selection_effect']*100:+.2f}%")
    print(f"    交互项：      {result['interaction']*100:+.2f}%")

    print(f"\n  分行业明细：")
    print(f"  {'行业':<8s} {'配置贡献':>10s} {'选股贡献':>10s} {'交互项':>10s}")
    print(f"  {'-'*8} {'-'*10} {'-'*10} {'-'*10}")
    for i, ind in enumerate(industries):
        print(f"  {ind:<8s} {result['sector_allocation'][i]*100:>+9.2f}% "
              f"{result['sector_selection'][i]*100:>+9.2f}% "
              f"{result['sector_interaction'][i]*100:>+9.2f}%")

    # Fama-French归因
    print(f"\n  Fama-French因子归因（简化）：")
    np.random.seed(789)
    n = 60
    market_rets = np.random.normal(0.006, 0.045, n)
    smb = np.random.normal(0.002, 0.03, n)   # 规模因子
    hml = np.random.normal(0.001, 0.03, n)   # 价值因子
    mom = np.random.normal(0.003, 0.04, n)   # 动量因子

    port_rets = 0.003 + 0.95 * market_rets + 0.2 * smb - 0.1 * hml + \
                np.random.normal(0, 0.02, n)

    ff_result = fama_french_attribution(port_rets, market_rets, smb, hml, mom)
    print(f"    Alpha (月):       {ff_result['alpha']*100:.2f}%")
    print(f"    Alpha t值:        {ff_result['alpha_t_stat']:.2f}")
    beta_names = ['市场', '规模(SMB)', '价值(HML)', '动量(MOM)']
    for i, (name, beta) in enumerate(zip(beta_names, ff_result['betas'])):
        print(f"    β_{name}:        {beta:.2f}")
    print(f"    R²:              {ff_result['r_squared']:.3f}")
    alpha_significant = abs(ff_result['alpha_t_stat']) > 2
    print(f"    Alpha显著:       {'✓ 是（真正的选股能力）' if alpha_significant else '✗ 否（收益可用因子解释）'}")

    return result


def demo_cost_impact(data):
    """演示交易成本影响"""
    print("\n" + "=" * 60)
    print("  进阶7：交易成本影响分析")
    print("=" * 60)

    # 构造一个策略的月收益序列
    n_months = data['n_months']
    qb = quantile_backtest(data['stocks'], 'pe', n_months, n_quantiles=5)

    if not qb['long_short_returns']:
        print("  数据不足")
        return None

    ls_returns = np.array(qb['long_short_returns'])
    ls_returns = ls_returns[~np.isnan(ls_returns)]

    result = transaction_cost_impact(ls_returns, turnover_rate=0.5, frequency_per_year=12)

    print(f"\n  交易成本对策略的影响：")
    print(f"    单次完整交易成本:  {result['round_trip_cost_pct']:.2f}%")
    print(f"    年化换手率:        {result['annual_turnover']:.0f}x")
    print(f"    年化成本:          {result['annual_cost_pct']:.2f}%")
    print(f"    毛年化收益:        {result['gross_annual_return']:.2f}%")
    print(f"    净年化收益:        {result['net_annual_return']:.2f}%")
    print(f"    成本吞噬:          {result['cost_drag']:.2f}%")
    print(f"    毛夏普:            {result['sharpe_gross']:.2f}")
    print(f"    净夏普:            {result['sharpe_net']:.2f}")
    print(f"    策略是否盈利:      {'✓ 是' if result['is_profitable'] else '✗ 否（成本吃掉了所有Alpha）'}")

    # 换手率影响模拟
    turnovers, net_rets = simulate_turnover_impact(ls_returns)
    breakeven_turnover = None
    for t, r in zip(turnovers, net_rets):
        if r < 0:
            breakeven_turnover = t
            break

    print(f"\n  换手率盈亏平衡点:   约{breakeven_turnover:.0%}年换手率")
    print(f"  → 如果换手率超过{breakeven_turnover:.0%}，策略从盈利变亏损")

    return {'cost_result': result, 'turnovers': turnovers, 'net_returns': net_rets}


def demo_timeseries_cv(data):
    """演示时间序列交叉验证"""
    print("\n" + "=" * 60)
    print("  进阶8：时间序列交叉验证")
    print("=" * 60)

    stocks = data['stocks']
    n_months = data['n_months']

    cv_results = timeseries_cv_demo(stocks, 'pe', n_months,
                                      train_months=24, test_months=12)

    if isinstance(cv_results, dict) and 'error' in cv_results:
        print(f"  {cv_results['error']}")
        return None

    print(f"\n  时间序列交叉验证（PE因子）：")
    print(f"  {'窗口':<18s} {'训练IC':>10s} {'测试IC':>10s} {'训练IC_IR':>10s} {'测试IC_IR':>10s}")
    print(f"  {'-'*18} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")

    for r in cv_results:
        print(f"  {r['window']:<18s} {r['train_ic_mean']:>9.4f}  {r['test_ic_mean']:>9.4f}  "
              f"{r['train_ic_ir']:>9.2f}  {r['test_ic_ir']:>9.2f}")

    # 汇总
    train_ics_all = [r['train_ic_mean'] for r in cv_results]
    test_ics_all = [r['test_ic_mean'] for r in cv_results]

    print(f"\n  汇总统计：")
    print(f"    训练集平均IC:    {np.mean(train_ics_all):.4f}")
    print(f"    测试集平均IC:    {np.mean(test_ics_all):.4f}")
    print(f"    IC衰减:          {(np.mean(train_ics_all) - np.mean(test_ics_all)):.4f}")
    print(f"    → 样本外衰减约{(1 - np.mean(test_ics_all)/np.mean(train_ics_all))*100:.0f}%，在可接受范围" if
          np.mean(test_ics_all) > np.mean(train_ics_all) * 0.5 else
          "    → 样本外衰减严重，因子稳定性存疑")

    return cv_results


# ============================================================
# 主程序
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("  第九课进阶实战代码：因子研究、统计检验与组合优化")
    print("=" * 60)

    # 生成数据
    print("\n⏳ 生成模拟数据...")
    data = generate_realistic_data(n_stocks=50, n_days=1260)
    print(f"  {len(data['stocks'])}只股票, {data['n_days']}个交易日, {data['n_months']}个月")

    # 1. 因子IC分析
    ic_results = demo_ic_analysis(data)
    plot_ic_analysis(ic_results, data)

    # 2. 分层回测
    qb_result = demo_quantile_backtest(data)

    # 3. Bootstrap检验
    bs_result = demo_bootstrap_test(data)
    if bs_result:
        plot_bootstrap_test(bs_result)

    # 4. 布林带策略
    bb_signals, bb_indicators = demo_bollinger_strategy(data)
    plot_bollinger_strategy(data['market_index'], bb_signals, bb_indicators)

    # 5. 风险平价
    rp_data = demo_risk_parity(data)
    plot_risk_parity(rp_data['asset_returns'], rp_data['labels'],
                      rp_data['rp_weights'], rp_data['ew_weights'], rp_data['mvo_weights'])
    plot_efficient_frontier(rp_data['ef_rets'], rp_data['ef_risks'],
                             rp_data['asset_returns'], rp_data['labels'],
                             rp_data['rp_weights'], rp_data['mvo_weights'], rp_data['ew_weights'])

    # 6. 绩效归因
    attrib_result = demo_attribution()
    plot_attribution(attrib_result)

    # 7. 交易成本
    cost_data = demo_cost_impact(data)
    if cost_data:
        plot_cost_impact(cost_data['turnovers'], cost_data['net_returns'],
                          cost_data['cost_result'])

    # 8. 时间序列交叉验证
    cv_results = demo_timeseries_cv(data)
    if cv_results:
        plot_timeseries_cv(cv_results)

    print(f"\n{'=' * 60}")
    print(f"  所有进阶图表已生成到：{OUTPUT_DIR}")
    print(f"{'=' * 60}")
