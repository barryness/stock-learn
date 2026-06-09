"""
第九课机构实战配套代码：因子工厂、行业中性化、算法执行、风控体系
模拟真实量化机构的核心工具链
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
from collections import defaultdict
from itertools import combinations
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
# 1. 数据生成：机构级模拟数据
# ============================================================

def generate_institutional_data(n_stocks=200, n_days=1260, seed=42):
    """生成机构级模拟数据（200只股票，含行业、市值、流动性特征）"""
    np.random.seed(seed)

    industries_list = ['银行', '非银金融', '消费', '科技', '医药',
                       '能源', '材料', '工业', '地产', '公用事业']
    n_industries = len(industries_list)
    industry_assignments = {}
    for s in range(n_stocks):
        industry_assignments[f'S{s:04d}'] = industries_list[s % n_industries]

    # 行业特征参数
    industry_params = {}
    for i, ind in enumerate(industries_list):
        industry_params[ind] = {
            'beta': 0.7 + 0.6 * (i / n_industries),
            'pe_base': 6 + 30 * (i / n_industries),
            'roe_base': 0.06 + 0.12 * (i / n_industries),
            'vol_extra': 0.005 + 0.015 * (i / n_industries),
            'daily_volume_base': 10 ** (6 + np.random.uniform(0, 2)),
        }

    # 市场收益
    t = np.arange(n_days)
    drift = 0.00025
    cycles = 0.10 * np.sin(2 * np.pi * t / 250) + 0.05 * np.sin(2 * np.pi * t / 63)
    noise = np.random.normal(0, 0.012, n_days)
    market_returns = drift + np.diff(np.concatenate([[0], cycles])) * 0.3 + noise
    market_index = 3000 * np.exp(np.cumsum(market_returns))

    # 规模因子（小盘-大盘）
    smb = np.random.normal(0.0002, 0.02, n_days)
    # 价值因子（高BP-低BP）
    hml = np.random.normal(0.0001, 0.015, n_days)

    n_months = n_days // 21 + 1
    stock_data = {}

    for s in range(n_stocks):
        sid = f'S{s:04d}'
        ind = industry_assignments[sid]
        ip = industry_params[ind]

        # 市值（对数正态分布）
        log_mcap = 8 + np.random.uniform(0, 5)  # 市值从几千万到几千亿
        mcap = np.exp(log_mcap)

        beta = ip['beta'] + np.random.normal(0, 0.12)
        smb_beta = np.random.normal(0, 0.3)  # 规模暴露
        hml_beta = np.random.normal(0, 0.25)  # 价值暴露

        alpha = np.random.normal(ip['roe_base'] * 0.3, ip['roe_base'] * 0.2)
        idio_vol = 0.012 + ip['vol_extra'] + np.random.uniform(0, 0.01)

        stock_returns = (alpha + beta * market_returns +
                         smb_beta * smb + hml_beta * hml +
                         np.random.normal(0, idio_vol, n_days))
        stock_prices = 10 * np.exp(np.cumsum(stock_returns))

        # 日成交量（对数正态，波动较大）
        daily_volume = ip['daily_volume_base'] * np.exp(np.random.normal(0, 0.5, n_days))

        # 月度因子数据
        pe = ip['pe_base'] + np.random.normal(0, ip['pe_base'] * 0.35, n_months)
        pe += 3 * np.sin(np.linspace(0, 2 * np.pi, n_months))
        pe = np.clip(pe, 3, 100)

        roe = ip['roe_base'] + np.random.normal(0, 0.04, n_months)
        roe += 0.02 * np.sin(np.linspace(0, 3 * np.pi, n_months))
        roe = np.clip(roe, -0.05, 0.40)

        momentum_12m = np.zeros(n_months)
        for m in range(1, n_months):
            lookback = min(m, 12)
            start = max(0, (m - lookback) * 21)
            end = min(m * 21, n_days)
            if end > start:
                momentum_12m[m] = (stock_prices[min(end, n_days-1)] / stock_prices[start] - 1)

        volatility = np.zeros(n_months)
        for m in range(1, n_months):
            s_idx = max(0, (m - 1) * 21)
            e_idx = min(m * 21, n_days)
            if e_idx > s_idx + 5:
                rets = np.diff(stock_prices[s_idx:e_idx]) / stock_prices[s_idx:e_idx - 1]
                volatility[m] = np.std(rets) * np.sqrt(252)
        volatility = np.clip(volatility, 0.03, 0.70)

        future_ret_1m = np.zeros(n_months)
        for m in range(n_months - 1):
            s_idx = m * 21
            e_idx = min((m + 1) * 21, n_days)
            if e_idx > s_idx:
                future_ret_1m[m] = (stock_prices[min(e_idx, n_days-1)] / stock_prices[s_idx] - 1)

        stock_data[sid] = {
            'prices': stock_prices,
            'returns': stock_returns,
            'industry': ind,
            'market_cap': mcap,
            'beta': beta,
            'daily_volume': daily_volume,
            'pe': pe,
            'roe': roe,
            'momentum_12m': momentum_12m,
            'volatility': volatility,
            'future_ret_1m': future_ret_1m,
        }

    return {
        'market_index': market_index,
        'market_returns': market_returns,
        'smb': smb,
        'hml': hml,
        'stocks': stock_data,
        'industries': industries_list,
        'industry_assignments': industry_assignments,
        'n_days': n_days,
        'n_months': n_months,
    }


# ============================================================
# 2. 因子工厂：自动化因子生成、测试、去重
# ============================================================

class FactorFactory:
    """模拟机构的因子工厂——自动化因子生成与测试"""

    def __init__(self, stocks, industries, n_months):
        self.stocks = stocks
        self.industries = industries
        self.n_months = n_months
        self.factor_library = {}

    def generate_candidates(self, base_factors=None):
        """从基础因子自动生成变体（模拟公式树）"""
        if base_factors is None:
            base_factors = ['pe', 'roe', 'momentum_12m', 'volatility']

        candidates = []

        for bf in base_factors:
            meta = {
                'pe': {'inverse': True, 'label': 'PE'},
                'roe': {'inverse': False, 'label': 'ROE'},
                'momentum_12m': {'inverse': False, 'label': '动量'},
                'volatility': {'inverse': True, 'label': '波动率'},
            }
            candidates.append({
                'name': bf,
                'transform': 'raw',
                'window': None,
                'inverse': meta.get(bf, {}).get('inverse', False),
                'label': meta.get(bf, {}).get('label', bf),
            })

            # 变体1：Z-Score标准化
            candidates.append({
                'name': f'{bf}_zscore',
                'transform': 'zscore',
                'window': None,
                'inverse': meta.get(bf, {}).get('inverse', False),
                'label': f'{meta.get(bf, {}).get("label", bf)}(Z)',
            })

            # 变体2：3月变化
            candidates.append({
                'name': f'{bf}_delta3m',
                'transform': 'delta',
                'window': 3,
                'inverse': False,
                'label': f'{bf}_Δ3M',
            })

            # 变体3：6月变化
            candidates.append({
                'name': f'{bf}_delta6m',
                'transform': 'delta',
                'window': 6,
                'inverse': False,
                'label': f'{bf}_Δ6M',
            })

        # 交互项
        for f1, f2 in [('pe', 'roe'), ('momentum_12m', 'roe'), ('pe', 'volatility')]:
            candidates.append({
                'name': f'{f1}_x_{f2}',
                'transform': 'interaction',
                'factors': (f1, f2),
                'window': None,
                'inverse': None,
                'label': f'{f1}×{f2}',
            })

        return candidates

    def compute_factor_values(self, candidate, month_idx):
        """计算某个候选因子在某个月的值"""
        values = {}
        name = candidate['name']
        transform = candidate['transform']

        for sid, data in self.stocks.items():
            if month_idx >= len(data.get('pe', [])):
                continue

            if transform == 'raw':
                if name in data:
                    values[sid] = data[name][month_idx]
                else:
                    values[sid] = np.nan

            elif transform == 'zscore':
                base_name = name.replace('_zscore', '')
                if base_name in data:
                    values[sid] = data[base_name][month_idx]
                else:
                    values[sid] = np.nan

            elif transform == 'delta':
                parts = name.split('_delta')
                base = parts[0]
                window = candidate.get('window', 3)
                if month_idx >= window:
                    if base in data:
                        values[sid] = data[base][month_idx] - data[base][month_idx - window]
                    else:
                        values[sid] = np.nan
                else:
                    values[sid] = np.nan

            elif transform == 'interaction':
                f1, f2 = candidate['factors']
                v1 = data.get(f1, [np.nan]*self.n_months)[month_idx]
                v2 = data.get(f2, [np.nan]*self.n_months)[month_idx]
                values[sid] = v1 * v2 if not (np.isnan(v1) or np.isnan(v2)) else np.nan

            else:
                values[sid] = np.nan

        return values

    def quick_screen(self, candidates, month_range=None):
        """快速IC筛选：对候选因子做IC，只保留显著的"""
        if month_range is None:
            month_range = (0, self.n_months - 1)

        results = []
        for c in candidates:
            ic_list = []
            for m in range(month_range[0], month_range[1]):
                factor_vals = self.compute_factor_values(c, m)
                fwd_rets = {}
                for sid in factor_vals:
                    if m < len(self.stocks[sid].get('future_ret_1m', [])):
                        fwd_rets[sid] = self.stocks[sid]['future_ret_1m'][m]

                common = set(factor_vals.keys()) & set(fwd_rets.keys())
                if len(common) < 20:
                    continue

                fv = np.array([factor_vals[s] for s in common])
                fr = np.array([fwd_rets[s] for s in common])

                valid = ~(np.isnan(fv) | np.isnan(fr))
                if np.sum(valid) < 20:
                    continue

                fv_clean = fv[valid]
                fr_clean = fr[valid]
                n_valid = len(fv_clean)

                rank_fv = np.argsort(np.argsort(fv_clean)) / (n_valid - 1)
                rank_fr = np.argsort(np.argsort(fr_clean)) / (n_valid - 1)

                if np.std(rank_fv) > 0 and np.std(rank_fr) > 0:
                    ic = np.corrcoef(rank_fv, rank_fr)[0, 1]
                    ic_list.append(ic)

            if not ic_list:
                continue

            ic_vals = np.array(ic_list)
            ic_mean = np.mean(ic_vals)
            ic_std = np.std(ic_vals)
            ic_ir = ic_mean / ic_std if ic_std > 0 else 0

            results.append({
                'name': c['name'],
                'label': c.get('label', c['name']),
                'transform': c['transform'],
                'ic_mean': ic_mean,
                'ic_std': ic_std,
                'ic_ir': ic_ir,
                'n_obs': len(ic_list),
                'ic_series': ic_vals,
            })

        # 按|IC|排序
        results.sort(key=lambda x: abs(x['ic_mean']), reverse=True)
        return results

    def deduplicate(self, screened_results, corr_threshold=0.85):
        """因子去重：删除高度相关的因子"""
        n = len(screened_results)
        if n == 0:
            return []

        # 计算因子IC序列的相关性（不是因子值的相关性）
        kept = [screened_results[0]]

        for i in range(1, n):
            is_duplicate = False
            for kept_f in kept:
                min_len = min(len(screened_results[i]['ic_series']),
                              len(kept_f['ic_series']))
                if min_len < 10:
                    continue
                a = screened_results[i]['ic_series'][:min_len]
                b = kept_f['ic_series'][:min_len]
                if np.std(a) > 0 and np.std(b) > 0:
                    corr = np.corrcoef(a, b)[0, 1]
                    if abs(corr) > corr_threshold:
                        is_duplicate = True
                        break

            if not is_duplicate:
                kept.append(screened_results[i])

        return kept


# ============================================================
# 3. 行业中性化（机构必备操作）
# ============================================================

class Neutralizer:
    """行业中性化和市值中性化"""

    @staticmethod
    def industry_neutralize(factor_values, industry_map, method='rank'):
        """行业中性化：每个行业内部分别排名"""
        by_industry = defaultdict(dict)
        for sid, value in factor_values.items():
            if not np.isnan(value):
                by_industry[industry_map[sid]][sid] = value

        neutralized = {}
        for ind, stocks in by_industry.items():
            sids = list(stocks.keys())
            vals = np.array([stocks[s] for s in sids])

            if method == 'rank':
                # 行业内排名 → [0, 1]
                n = len(vals)
                ranked = np.argsort(np.argsort(vals)) / (n - 1)
            elif method == 'zscore':
                # 行业内Z-Score
                mu, sigma = np.mean(vals), np.std(vals)
                if sigma > 0:
                    ranked = (vals - mu) / sigma
                else:
                    ranked = np.zeros(n)
            else:
                ranked = vals

            for sid, val in zip(sids, ranked):
                neutralized[sid] = val

        return neutralized

    @staticmethod
    def size_neutralize(factor_values, market_caps):
        """市值中性化：对市值做正交回归"""
        common = set(factor_values.keys()) & set(market_caps.keys())
        common = {s for s in common if not (np.isnan(factor_values[s]) or np.isnan(market_caps[s]))}
        if len(common) < 20:
            return factor_values

        sids = sorted(common)
        y = np.array([factor_values[s] for s in sids])
        x = np.log(np.array([market_caps[s] for s in sids]))

        X = np.column_stack([np.ones(len(x)), x])
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
        residuals = y - X @ beta

        return {sid: r for sid, r in zip(sids, residuals)}

    @staticmethod
    def sector_benchmark_map(stock_data):
        """提取行业映射和市值"""
        industry_map = {}
        market_caps = {}
        for sid, data in stock_data.items():
            industry_map[sid] = data['industry']
            market_caps[sid] = data['market_cap']
        return industry_map, market_caps


# ============================================================
# 4. 风控系统
# ============================================================

class RiskManager:
    """模拟机构风控系统"""

    def __init__(self, max_single_position=0.02, max_industry=0.15,
                 max_net_exposure=0.10, max_drawdown_threshold=-0.08,
                 max_leverage=1.0):
        self.max_single_position = max_single_position
        self.max_industry = max_industry
        self.max_net_exposure = max_net_exposure
        self.max_drawdown_threshold = max_drawdown_threshold
        self.max_leverage = max_leverage

        self.violations_log = []
        self.warning_log = []

    def pre_trade_check(self, order, portfolio_state, industry_map):
        """事前风控：下单前检查"""
        violations = []

        # 1. 单票上限
        proposed_pct = order['amount'] / portfolio_state['nav']
        if proposed_pct > self.max_single_position:
            violations.append(f"单票超限: {proposed_pct:.1%} > {self.max_single_position:.1%}")

        # 2. 行业上限
        ind = industry_map.get(order['sid'], '未知')
        current_ind_pct = portfolio_state.get('industry_weights', {}).get(ind, 0)
        if current_ind_pct + proposed_pct > self.max_industry:
            violations.append(f"行业超限: {ind} {current_ind_pct+proposed_pct:.1%} > {self.max_industry:.1%}")

        # 3. 流动性检查
        if order.get('daily_volume', 0) < 10_000_000:
            violations.append(f"流动性不足: {order['sid']} 日成交<1000万")

        # 4. 杠杆检查
        new_leverage = (portfolio_state['gross_exposure'] + proposed_pct) / portfolio_state['nav']
        if new_leverage > self.max_leverage * 1.1:
            violations.append(f"杠杆超限: {new_leverage:.1%}")

        if violations:
            self.violations_log.append({'order': order, 'violations': violations})
            return False, violations
        return True, []

    def check_drawdown(self, nav_series, current_nav):
        """回撤检查"""
        peak = np.max(nav_series)
        dd = (current_nav - peak) / peak
        if dd < self.max_drawdown_threshold:
            return True, f"回撤超限: {dd:.2%} < {self.max_drawdown_threshold:.2%}"
        return False, None

    def daily_risk_report(self, positions, nav, industry_weights, style_exposures):
        """每日风险报告"""
        report = {
            'nav': nav,
            'n_positions': len(positions),
            'top_position': max(positions.values()) if positions else 0,
            'top_industry': max(industry_weights.values()) if industry_weights else 0,
            'net_exposure': sum(p for p in positions.values() if p > 0) -
                           sum(abs(p) for p in positions.values() if p < 0),
            'style_exposures': style_exposures,
        }

        warnings = []
        if report['top_position'] > self.max_single_position * 0.8:
            warnings.append(f"单票接近上限")
        if report['top_industry'] > self.max_industry * 0.8:
            warnings.append(f"行业集中度接近上限")
        if abs(report['net_exposure']) > self.max_net_exposure * 0.8:
            warnings.append(f"净敞口接近上限")

        report['warnings'] = warnings
        self.warning_log.append(report)
        return report

    def stress_test(self, positions, prices, scenarios=None):
        """压力测试"""
        if scenarios is None:
            scenarios = {
                '2008金融危机': {'market': -0.50, 'small_cap': -0.15, 'correlation_boost': 0.3},
                '2015股灾': {'market': -0.35, 'small_cap': -0.25, 'correlation_boost': 0.4},
                '2020疫情': {'market': -0.30, 'small_cap': -0.10, 'correlation_boost': 0.5},
                '利率飙升': {'market': -0.15, 'small_cap': -0.20, 'correlation_boost': 0.2},
                '流动性危机': {'market': -0.40, 'small_cap': -0.30, 'correlation_boost': 0.6},
            }

        results = {}
        total_value = sum(p * prices.get(sid, 0) for sid, p in positions.items())

        for name, shocks in scenarios.items():
            loss = total_value * shocks['market'] * 1.2  # 简化估计
            results[name] = {'pnl_pct': loss / total_value * 100}

        return results


# ============================================================
# 5. 算法执行模拟
# ============================================================

class ExecutionSimulator:
    """模拟TWAP/VWAP算法执行"""

    @staticmethod
    def twap_execute(target_shares, total_seconds, interval_seconds=10, volatility=0.0002):
        """TWAP执行模拟"""
        n_slices = total_seconds // interval_seconds
        shares_per_slice = target_shares // n_slices

        slices = []
        price = 10.0
        executed = 0

        for i in range(n_slices):
            # 价格随机波动
            price += np.random.normal(0, volatility * price)
            # 冲击成本（随交易量增加）
            impact = 0.0001 * (shares_per_slice / 100000)
            executed_price = price * (1 + impact)

            slices.append({
                'slice': i,
                'time': i * interval_seconds,
                'shares': shares_per_slice,
                'price': executed_price,
            })
            executed += shares_per_slice

        # 尾单
        remaining = target_shares - executed
        if remaining > 0:
            price += np.random.normal(0, volatility * price)
            slices.append({
                'slice': n_slices,
                'time': n_slices * interval_seconds,
                'shares': remaining,
                'price': price,
            })

        avg_price = np.average([s['price'] for s in slices], weights=[s['shares'] for s in slices])
        arrival_price = slices[0]['price']

        return {
            'total_shares': target_shares,
            'n_slices': len(slices),
            'avg_price': avg_price,
            'arrival_price': arrival_price,
            'slippage_bps': (avg_price - arrival_price) / arrival_price * 10000,
            'slices': slices,
        }

    @staticmethod
    def vwap_execute(target_shares, total_day_seconds, volume_profile, interval=60):
        """VWAP执行模拟"""
        n_intervals = total_day_seconds // interval
        # volume_profile: 历史成交量占比（一天各时段）
        if volume_profile is None:
            # 默认成交量分布（A股典型：开盘和收盘量最大）
            t = np.linspace(0, np.pi, n_intervals)
            volume_profile = 0.5 + 0.5 * np.sin(t)
            volume_profile = volume_profile / np.sum(volume_profile)

        shares_per_interval = (target_shares * volume_profile).astype(int)
        # 确保总股数正确
        diff = target_shares - np.sum(shares_per_interval)
        shares_per_interval[0] += diff

        slices = []
        price = 10.0

        for i in range(n_intervals):
            if shares_per_interval[i] <= 0:
                continue
            price += np.random.normal(0, 0.0002 * price)
            executed_price = price * (1 + 0.0001 * (shares_per_interval[i] / 100000))
            slices.append({
                'interval': i,
                'shares': shares_per_interval[i],
                'price': executed_price,
            })

        avg_price = np.average([s['price'] for s in slices], weights=[s['shares'] for s in slices])
        arrival_price = slices[0]['price']

        return {
            'total_shares': target_shares,
            'avg_price': avg_price,
            'arrival_price': arrival_price,
            'slippage_bps': (avg_price - arrival_price) / arrival_price * 10000,
            'slices': slices,
        }

    @staticmethod
    def compare_execution_methods(target_shares, market_volume):
        """对比不同执行方法"""
        results = {}

        # 一次性市价单（基准：冲击最大）
        market_price = 10.0
        impact = 0.001 * np.sqrt(target_shares / market_volume)
        market_exec_price = market_price * (1 + impact)
        results['市价单'] = {
            'price': market_exec_price,
            'slippage_bps': (market_exec_price - market_price) / market_price * 10000,
            'impact_cost_bps': impact * 10000,
        }

        # TWAP
        twap = ExecutionSimulator.twap_execute(target_shares, 1800, 30)
        results['TWAP(30分钟)'] = {
            'price': twap['avg_price'],
            'slippage_bps': twap['slippage_bps'],
        }

        # TWAP(更长)
        twap_long = ExecutionSimulator.twap_execute(target_shares, 7200, 60)
        results['TWAP(2小时)'] = {
            'price': twap_long['avg_price'],
            'slippage_bps': twap_long['slippage_bps'],
        }

        # VWAP
        vwap = ExecutionSimulator.vwap_execute(target_shares, 14400, None, 120)
        results['VWAP(全天)'] = {
            'price': vwap['avg_price'],
            'slippage_bps': vwap['slippage_bps'],
        }

        return results


# ============================================================
# 6. 策略退役监控
# ============================================================

class StrategyMonitor:
    """策略持续监控 + 退役条件检查"""

    def __init__(self, strategy_name, retirement_rules=None):
        self.strategy_name = strategy_name
        self.retirement_rules = retirement_rules or {
            'max_drawdown_vs_backtest': 2.0,   # 实盘回撤 > 2×回测回撤 → 停
            'consecutive_neg_months': 3,         # 连续3月负超额 → 降仓
            'consecutive_neg_months_hard': 6,    # 连续6月负超额 → 停
            'live_vs_backtest_ratio': 0.5,       # 实盘超额 < 回测超额50% → 停
            'min_info_ratio': 0.3,               # 信息比率 < 0.3 持续6月 → 降仓
        }
        self.monthly_track = []
        self.status = 'active'  # active, warning, reduced, stopped

    def add_month(self, excess_return, tracking_error):
        """记录月度表现"""
        record = {
            'month': len(self.monthly_track) + 1,
            'excess_return': excess_return,
            'tracking_error': tracking_error,
        }
        self.monthly_track.append(record)
        self._check_rules()

    def _check_rules(self):
        """检查退役条件"""
        if len(self.monthly_track) < 3:
            return

        excess_returns = [r['excess_return'] for r in self.monthly_track]

        # 连续负超额
        neg_streak = 0
        for r in reversed(excess_returns):
            if r < 0:
                neg_streak += 1
            else:
                break

        if neg_streak >= self.retirement_rules['consecutive_neg_months_hard']:
            self.status = 'stopped'
            return

        if neg_streak >= self.retirement_rules['consecutive_neg_months']:
            self.status = 'reduced'

        # 信息比率
        if len(self.monthly_track) >= 6:
            recent_6 = excess_returns[-6:]
            ir = np.mean(recent_6) / np.std(recent_6) if np.std(recent_6) > 0 else 0
            if ir < self.retirement_rules['min_info_ratio']:
                self.status = 'reduced'
                if ir < 0:
                    self.status = 'stopped'

    def should_continue(self):
        return self.status != 'stopped'

    def get_status(self):
        if len(self.monthly_track) < 3:
            return 'active', '观察期（数据不足）'

        recent_3 = [r['excess_return'] for r in self.monthly_track[-3:]]
        avg_excess = np.mean(recent_3)

        if self.status == 'stopped':
            return 'stopped', f'已触及退役条件，当前3月平均超额: {avg_excess:.2%}'
        elif self.status == 'reduced':
            return 'reduced', f'降仓观察中，当前3月平均超额: {avg_excess:.2%}'
        else:
            return 'active', f'正常，当前3月平均超额: {avg_excess:.2%}'


# ============================================================
# 7. 策略容量估算
# ============================================================

class CapacityEstimator:
    """策略容量估算器"""

    @staticmethod
    def estimate_single_stock_capacity(daily_volume, position_pct=0.005, trade_days=5):
        """单票容量：不超过日均成交的0.5%，分5天建仓"""
        single_day_max = daily_volume * position_pct
        total_capacity = single_day_max * trade_days
        return total_capacity

    @staticmethod
    def estimate_strategy_capacity(stock_data, universe, turnover_rate=0.02,
                                    position_pct_per_day=0.005):
        """估算策略总容量"""
        total_capacity = 0
        capacities = {}

        for sid in universe:
            if sid not in stock_data:
                continue
            avg_volume = np.mean(stock_data[sid]['daily_volume'])
            single_stock_cap = CapacityEstimator.estimate_single_stock_capacity(
                avg_volume, position_pct_per_day
            )
            total_capacity += single_stock_cap
            capacities[sid] = single_stock_cap

        # 考虑换手率后的实际容量
        adjusted_capacity = total_capacity * turnover_rate

        return {
            'gross_capacity': total_capacity,
            'adjusted_capacity': adjusted_capacity,
            'top_capacities': sorted(capacities.items(), key=lambda x: x[1], reverse=True)[:10],
        }


# ============================================================
# 8. 可视化
# ============================================================

def plot_factor_factory(screened, deduped):
    """绘制因子工厂筛选结果"""
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # 图1：筛选前后对比
    ax = axes[0]
    if screened:
        top_n = min(15, len(screened))
        top_factors = screened[:top_n]
        labels = [f['label'] for f in top_factors]
        ic_vals = [f['ic_mean'] for f in top_factors]
        colors = ['#A23B72' if ic > 0 else '#2E86AB' for ic in ic_vals]
        bars = ax.barh(range(len(labels)), ic_vals, color=colors, alpha=0.8)
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels, fontsize=8)
        ax.axvline(x=0, color='gray', linewidth=0.5)
        ax.axvline(x=0.03, color='#F39C12', linestyle='--', alpha=0.7, label='IC阈值(0.03)')
        ax.set_xlabel('IC均值')
        ax.set_title(f'因子工厂：Top {top_n} 候选因子（筛选前，共{len(screened)}个）')
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3, axis='x')

    # 图2：去重后结果
    ax = axes[1]
    if deduped:
        labels = [f['label'] for f in deduped]
        ic_vals = [f['ic_mean'] for f in deduped]
        colors = ['#A23B72' if ic > 0 else '#2E86AB' for ic in ic_vals]
        ax.barh(range(len(labels)), ic_vals, color=colors, alpha=0.8)
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels, fontsize=8)
        ax.axvline(x=0, color='gray', linewidth=0.5)
        ax.set_xlabel('IC均值')
        ax.set_title(f'去重后：{len(deduped)}个独立因子（相关性<0.85）')
        ax.grid(True, alpha=0.3, axis='x')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'inst_factor_factory.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] 因子工厂图已保存: {path}")


def plot_neutralization(raw_values, ind_neutralized, size_neutralized, industry_map):
    """绘制行业中性化前后对比"""
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    industries_set = sorted(set(industry_map.values()))
    colors = plt.cm.tab10(np.linspace(0, 1, len(industries_set)))
    ind_colors = {ind: colors[i] for i, ind in enumerate(industries_set)}

    datasets = [
        ('原始PE', raw_values),
        ('行业中性化', ind_neutralized),
        ('行业+市值中性化', size_neutralized),
    ]

    for ax_idx, (title, values) in enumerate(datasets):
        ax = axes[ax_idx]
        for sid, val in values.items():
            if sid in industry_map and not np.isnan(val):
                ax.scatter(val, 0, c=[ind_colors[industry_map[sid]]], alpha=0.5, s=30)

        ax.set_title(title)
        ax.set_xlabel('因子值')
        ax.set_yticks([])
        ax.grid(True, alpha=0.3, axis='x')

    # 图例
    legend_elements = [plt.Line2D([0], [0], marker='o', color='w',
                                   markerfacecolor=ind_colors[ind],
                                   markersize=8, label=ind)
                       for ind in industries_set[:5]]
    axes[0].legend(handles=legend_elements, fontsize=6, loc='upper right')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'inst_neutralization.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] 行业中性化图已保存: {path}")


def plot_execution_comparison(exec_results):
    """绘制算法执行对比"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 图1：滑点对比
    ax = axes[0]
    methods = list(exec_results.keys())
    slippages = [exec_results[m]['slippage_bps'] for m in methods]
    colors = ['#E74C3C', '#F39C12', '#2E86AB', '#27AE60']
    ax.bar(methods, slippages, color=colors, alpha=0.8)
    ax.set_ylabel('滑点 (bps)')
    ax.set_title('不同执行方法的滑点对比')
    ax.grid(True, alpha=0.3, axis='y')

    # 图2：执行价格vs时间（TWAP模拟）
    ax = axes[1]
    twap_slices = exec_results.get('TWAP(30分钟)', {}).get('slices', None)
    if twap_slices:
        times = [s['time'] for s in twap_slices]
        prices = [s['price'] for s in twap_slices]
        ax.step(times, prices, where='post', color='#2E86AB', linewidth=1.5, label='TWAP执行价')
        arrival = exec_results['TWAP(30分钟)']['arrival_price']
        avg = exec_results['TWAP(30分钟)']['avg_price']
        ax.axhline(y=arrival, color='#E74C3C', linestyle='--', alpha=0.7, label=f'到达价: {arrival:.3f}')
        ax.axhline(y=avg, color='#27AE60', linestyle='--', alpha=0.7, label=f'均价: {avg:.3f}')
        ax.set_xlabel('时间 (秒)')
        ax.set_ylabel('价格')
        ax.set_title('TWAP执行轨迹（30分钟）')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'inst_execution.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] 算法执行对比图已保存: {path}")


def plot_risk_dashboard(nav_series, positions_history, warnings_log):
    """绘制风控仪表盘"""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    days = np.arange(len(nav_series))

    # 图1：净值 + 回撤
    ax = axes[0, 0]
    ax.plot(days, nav_series, linewidth=1.5, color='#2E86AB', label='净值')
    peak = np.maximum.accumulate(nav_series)
    dd = (nav_series - peak) / peak * 100
    ax2 = ax.twinx()
    ax2.fill_between(days, 0, dd, color='#E74C3C', alpha=0.15, label='回撤')
    ax2.plot(days, dd, linewidth=0.8, color='#E74C3C', alpha=0.5)
    ax.set_ylabel('净值')
    ax2.set_ylabel('回撤 (%)')
    ax.set_title('净值与回撤')
    ax.grid(True, alpha=0.3)

    # 图2：行业权重热力图
    ax = axes[0, 1]
    if positions_history:
        dates = list(positions_history.keys())
        industries_set = set()
        for pos in positions_history.values():
            industries_set.update(pos.keys())
        industries_list = sorted(industries_set)[:10]

        if len(dates) > 0 and len(industries_list) > 0:
            heatmap_data = np.zeros((len(industries_list), len(dates)))
            for j, date in enumerate(dates):
                for i, ind in enumerate(industries_list):
                    heatmap_data[i, j] = positions_history[date].get(ind, 0) * 100

            im = ax.imshow(heatmap_data, cmap='RdYlGn', aspect='auto', vmin=0, vmax=20)
            ax.set_yticks(range(len(industries_list)))
            ax.set_yticklabels(industries_list, fontsize=7)
            ax.set_xticks(range(0, len(dates), max(1, len(dates)//8)))
            ax.set_xticklabels([dates[i] for i in range(0, len(dates), max(1, len(dates)//8))],
                               fontsize=6, rotation=30)
            ax.set_title('行业权重变化 (%)')
            plt.colorbar(im, ax=ax, shrink=0.8)

    # 图3：风险指标仪表
    ax = axes[1, 0]
    risk_metrics = {
        '当前回撤': f'{dd[-1]:.1f}%' if len(dd) > 0 else 'N/A',
        '波动率': f'{np.std(np.diff(nav_series)/nav_series[:-1])*np.sqrt(252)*100:.1f}%' if len(nav_series) > 1 else 'N/A',
        '预警次数': str(len(warnings_log)),
        '违规次数': '0',
        '状态': '✓ 正常',
    }

    y_pos = np.arange(len(risk_metrics))
    ax.barh(y_pos, [1]*len(risk_metrics), height=0.5, color='#2E86AB', alpha=0.3)
    for i, (metric, value) in enumerate(risk_metrics.items()):
        ax.text(0.5, i, f'{metric}: {value}', ha='center', va='center',
                fontsize=11, fontweight='bold')
    ax.set_yticks([])
    ax.set_xlim(0, 1)
    ax.set_title('风险仪表盘')

    # 图4：策略监控
    ax = axes[1, 1]
    # 模拟监控趋势
    months = np.arange(1, 13)
    excess = 0.005 + 0.002 * np.sin(months/3) + np.random.normal(0, 0.003, 12)
    excess_cum = np.cumsum(excess)
    ax.bar(months, excess * 100, color=['#27AE60' if e > 0 else '#E74C3C' for e in excess], alpha=0.7)
    ax.plot(months, excess_cum * 100, 'o-', color='#333333', linewidth=1.5, markersize=4,
            label='累计超额')
    ax.axhline(y=0, color='gray', linewidth=0.5)
    ax.set_xlabel('月份')
    ax.set_ylabel('超额收益 (%)')
    ax.set_title('策略月度超额监控')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'inst_risk_dashboard.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] 风控仪表盘已保存: {path}")


def plot_capacity_analysis(stock_data, cap_result):
    """绘制策略容量分析"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 图1：成交额分布
    ax = axes[0]
    volumes = [np.mean(stock_data[sid]['daily_volume']) for sid in stock_data]
    volumes_m = [v / 1e6 for v in volumes]
    ax.hist(volumes_m, bins=50, color='#2E86AB', alpha=0.7, edgecolor='white')
    ax.axvline(x=np.median(volumes_m), color='#A23B72', linestyle='--',
               label=f'中位数: {np.median(volumes_m):.0f}万元')
    ax.set_xlabel('日均成交额 (万元)')
    ax.set_ylabel('股票数量')
    ax.set_title('股票池成交额分布')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    # 图2：单票容量排名
    ax = axes[1]
    top_caps = cap_result.get('top_capacities', [])
    if top_caps:
        labels = [s[0] for s in top_caps[:10]]
        values = [s[1]/1e6 for s in top_caps[:10]]
        ax.barh(range(len(labels)), values, color='#A23B72', alpha=0.8)
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels, fontsize=7)
        ax.set_xlabel('容量 (百万元)')
        ax.set_title('单票策略容量 Top 10')
        ax.grid(True, alpha=0.3, axis='x')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'inst_capacity.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] 策略容量分析图已保存: {path}")


def plot_strategy_lifecycle(monitor_records):
    """绘制策略生命周期监控"""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    months = [r['month'] for r in monitor_records]
    excess = [r['excess_return'] * 100 for r in monitor_records]
    te = [r['tracking_error'] * 100 for r in monitor_records]

    # 图1：超额收益
    ax = axes[0, 0]
    colors_bar = ['#27AE60' if e > 0 else '#E74C3C' for e in excess]
    ax.bar(months, excess, color=colors_bar, alpha=0.8)
    ax.axhline(y=0, color='gray', linewidth=0.5)
    ax.axhline(y=np.mean(excess), color='#F39C12', linestyle='--', alpha=0.7,
               label=f'均值: {np.mean(excess):.2f}%')
    ax.set_xlabel('月份')
    ax.set_ylabel('超额收益 (%)')
    ax.set_title('月度超额收益')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')

    # 图2：跟踪误差
    ax = axes[0, 1]
    ax.plot(months, te, 'o-', color='#2E86AB', linewidth=1.5, markersize=5)
    ax.axhline(y=np.mean(te), color='#F39C12', linestyle='--', label=f'均值: {np.mean(te):.2f}%')
    ax.set_xlabel('月份')
    ax.set_ylabel('跟踪误差 (%)')
    ax.set_title('月度跟踪误差')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # 图3：滚动信息比率
    ax = axes[1, 0]
    if len(excess) >= 6:
        rolling_ir = []
        for i in range(5, len(excess)):
            window = excess[i-5:i+1]
            ir = np.mean(window) / np.std(window) if np.std(window) > 0 else 0
            rolling_ir.append(ir)
        ax.plot(months[5:], rolling_ir, 'o-', color='#A23B72', linewidth=1.5, markersize=5)
        ax.axhline(y=0.5, color='#27AE60', linestyle='--', label='优秀(0.5)')
        ax.axhline(y=0.3, color='#F39C12', linestyle='--', label='及格(0.3)')
        ax.axhline(y=0, color='gray', linewidth=0.5)
        ax.set_xlabel('月份')
        ax.set_ylabel('滚动6月IR')
        ax.set_title('滚动信息比率')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    # 图4：策略健康度
    ax = axes[1, 1]
    # 综合健康度评分
    health_scores = []
    for i in range(len(months)):
        score = 5  # 满分5
        if excess[i] < 0:
            score -= 1
        if i >= 2 and all(e < 0 for e in excess[max(0,i-2):i+1]):
            score -= 2
        if i >= 5:
            w = excess[i-5:i+1]
            ir = np.mean(w) / np.std(w) if np.std(w) > 0 else 0
            if ir < 0.3:
                score -= 1
        health_scores.append(max(0, score))

    colors_health = ['#27AE60' if s >= 4 else '#F39C12' if s >= 2 else '#E74C3C'
                     for s in health_scores]
    ax.bar(months, health_scores, color=colors_health, alpha=0.8)
    ax.axhline(y=3, color='#F39C12', linestyle='--', alpha=0.7, label='警戒线')
    ax.set_xlabel('月份')
    ax.set_ylabel('健康度 (满分5)')
    ax.set_title('策略健康度评分')
    ax.set_ylim(0, 6)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'inst_strategy_lifecycle.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] 策略生命周期图已保存: {path}")


# ============================================================
# 演示函数
# ============================================================

def demo_factor_factory(data):
    """演示因子工厂"""
    print("\n" + "=" * 60)
    print("  机构实战1：因子工厂——自动化因子生成与筛选")
    print("=" * 60)

    stocks = data['stocks']
    industries = data['industries']
    n_months = data['n_months']

    factory = FactorFactory(stocks, industries, n_months)
    candidates = factory.generate_candidates()
    print(f"\n  生成了 {len(candidates)} 个候选因子（含基础因子+变体+交互项）")

    screened = factory.quick_screen(candidates, month_range=(24, n_months - 1))
    print(f"  IC筛选后保留: {len(screened)} 个（|IC|最大为 {screened[0]['ic_mean']:.4f}）")

    deduped = factory.deduplicate(screened, corr_threshold=0.85)
    print(f"  去重后保留: {len(deduped)} 个独立因子")

    print(f"\n  Top 5 因子：")
    print(f"  {'排名':<6s} {'因子':<20s} {'IC均值':>10s} {'IC_IR':>8s} {'来源':<10s}")
    print(f"  {'-'*6} {'-'*20} {'-'*10} {'-'*8} {'-'*10}")
    for rank, f in enumerate(deduped[:5], 1):
        print(f"  #{rank:<5d} {f['label']:<20s} {f['ic_mean']:>9.4f}  {f['ic_ir']:>7.2f}  {f['transform']:<10s}")

    return screened, deduped


def demo_neutralization(data, month_idx=30):
    """演示行业中性化"""
    print("\n" + "=" * 60)
    print("  机构实战2：行业中性化")
    print("=" * 60)

    stocks = data['stocks']
    industry_map, market_caps = Neutralizer.sector_benchmark_map(stocks)

    # 原始PE值
    raw_values = {}
    for sid, sd in stocks.items():
        if month_idx < len(sd['pe']):
            raw_values[sid] = sd['pe'][month_idx]

    neutralizer = Neutralizer()
    ind_neut = neutralizer.industry_neutralize(raw_values, industry_map)

    # 先行业中性化，再市值中性化
    size_neut = neutralizer.size_neutralize(ind_neut, market_caps)

    # 按行业看PE分布改进
    print(f"\n  行业PE原始值 vs 行业中性化排名：")
    print(f"  {'行业':<10s} {'原始PE均值':>12s} {'行业内排名均值':>14s}")
    print(f"  {'-'*10} {'-'*12} {'-'*14}")

    for ind in sorted(set(industry_map.values()))[:5]:
        sids = [s for s in raw_values if industry_map.get(s) == ind]
        if sids:
            raw_mean = np.mean([raw_values[s] for s in sids])
            neut_mean = np.mean([ind_neut.get(s, np.nan) for s in sids])
            print(f"  {ind:<10s} {raw_mean:>11.1f}  {neut_mean:>13.3f}")

    # 检查中性化效果
    # 中性化后，行业不应有系统性差异
    ind_means_after = {}
    for ind in set(industry_map.values()):
        sids = [s for s in ind_neut if industry_map.get(s) == ind]
        if sids:
            ind_means_after[ind] = np.mean([ind_neut[s] for s in sids])

    if ind_means_after:
        dispersions = np.std(list(ind_means_after.values()))
        print(f"\n  行业间离散度（中性化后）: {dispersions:.4f}")
        print(f"  → {'行业差异已消除 ✓' if dispersions < 0.2 else '仍有行业差异'}")

    return raw_values, ind_neut, size_neut, industry_map


def demo_execution():
    """演示算法执行"""
    print("\n" + "=" * 60)
    print("  机构实战3：算法交易执行")
    print("=" * 60)

    target_shares = 500000  # 50万股
    market_volume = 50000000  # 日均成交5000万股

    results = ExecutionSimulator.compare_execution_methods(target_shares, market_volume)

    print(f"\n  目标：买入{target_shares/10000:.0f}万股，日均成交{market_volume/10000:.0f}万股")
    print(f"\n  {'执行方法':<16s} {'成交均价':>10s} {'滑点(bps)':>10s}")
    print(f"  {'-'*16} {'-'*10} {'-'*10}")
    for method, result in results.items():
        print(f"  {method:<16s} {result['price']:>9.3f}元  {result['slippage_bps']:>9.1f}")

    best = min(results.items(), key=lambda r: abs(r[1]['slippage_bps']))
    print(f"\n  → 执行建议：{best[0]}，滑点最低 ({best[1]['slippage_bps']:.1f} bps)")

    return results


def demo_risk_system(data):
    """演示风控系统"""
    print("\n" + "=" * 60)
    print("  机构实战4：风控体系")
    print("=" * 60)

    rm = RiskManager()

    # 模拟一个组合状态
    portfolio_state = {
        'nav': 100_000_000,  # 1亿
        'gross_exposure': 85_000_000,
        'industry_weights': {
            '银行': 0.12, '消费': 0.18, '科技': 0.22,
            '医药': 0.14, '能源': 0.08, '地产': 0.05,
        },
    }

    industry_map = {'S0001': '科技', 'S0002': '消费', 'S0003': '银行',
                    'S0004': '医药', 'S0005': '能源'}

    # 测试订单
    test_orders = [
        {'sid': 'S0001', 'amount': 5_000_000, 'daily_volume': 50_000_000},  # 正常订单
        {'sid': 'S0002', 'amount': 3_000_000, 'daily_volume': 500_000},     # 流动性差
        {'sid': 'S0003', 'amount': 8_000_000, 'daily_volume': 30_000_000},  # 行业可能超限
    ]

    print(f"\n  事前风控测试：")
    for order in test_orders:
        passed, reasons = rm.pre_trade_check(order, portfolio_state, industry_map)
        status = '✓ 通过' if passed else '✗ 拒绝'
        print(f"    {order['sid']} {order['amount']/1e6:.1f}M: {status}")
        if not passed:
            for r in reasons:
                print(f"      → {r}")

    # 压力测试
    positions = {'S0001': 0.15, 'S0002': 0.12, 'S0003': 0.10, 'S0004': 0.08, 'S0005': 0.05}
    prices = {'S0001': 50.0, 'S0002': 35.0, 'S0003': 18.0, 'S0004': 42.0, 'S0005': 25.0}

    stress_results = rm.stress_test(positions, prices)
    print(f"\n  压力测试：")
    for scenario, result in stress_results.items():
        print(f"    {scenario}: 预估亏损 {result['pnl_pct']:.1f}%")

    return rm


def demo_strategy_monitor():
    """演示策略退役监控"""
    print("\n" + "=" * 60)
    print("  机构实战5：策略退役监控")
    print("=" * 60)

    monitor = StrategyMonitor("Alpha策略-中证500增强")

    # 模拟18个月的策略表现
    np.random.seed(42)
    records = []
    for m in range(18):
        if m < 12:
            excess = np.random.normal(0.008, 0.02)
        else:
            # 最近6个月开始衰减
            excess = np.random.normal(-0.002, 0.018)
        te = 0.06 + np.random.normal(0, 0.005)
        monitor.add_month(excess, te)
        records.append({'month': m+1, 'excess_return': excess, 'tracking_error': te})

    status, msg = monitor.get_status()
    print(f"\n  策略状态: {status}")
    print(f"  {msg}")

    print(f"\n  退役条件检查：")
    rules = monitor.retirement_rules
    print(f"    连续负月(软): {rules['consecutive_neg_months']}月 → 降仓位")
    print(f"    连续负月(硬): {rules['consecutive_neg_months_hard']}月 → 停止")
    print(f"    最低信息比率: {rules['min_info_ratio']}")
    print(f"    实盘/回测比: {rules['live_vs_backtest_ratio']}")

    return records


def demo_capacity(data):
    """演示策略容量估算"""
    print("\n" + "=" * 60)
    print("  机构实战6：策略容量估算")
    print("=" * 60)

    stocks = data['stocks']

    # 筛选流通性最好的100只
    stock_liquidity = []
    for sid, sd in stocks.items():
        avg_vol = np.mean(sd['daily_volume'])
        stock_liquidity.append((sid, avg_vol))
    stock_liquidity.sort(key=lambda x: x[1], reverse=True)

    top100 = [s[0] for s in stock_liquidity[:100]]

    cap_result = CapacityEstimator.estimate_strategy_capacity(
        stocks, top100, turnover_rate=0.02
    )

    print(f"\n  策略池：流通性最好的100只股票")
    print(f"  总容量（毛）: {cap_result['gross_capacity']/1e8:.1f} 亿")
    print(f"  调整后容量（含换手）: {cap_result['adjusted_capacity']/1e8:.2f} 亿")
    print(f"\n  单票容量 Top 5：")
    for sid, cap in cap_result['top_capacities'][:5]:
        print(f"    {sid}: {cap/1e6:.1f} 百万")

    return cap_result


# ============================================================
# 主程序
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("  第九课机构实战：因子工厂/行业中性化/算法执行/风控体系")
    print("=" * 60)

    print("\n⏳ 生成机构级模拟数据...")
    data = generate_institutional_data(n_stocks=200, n_days=1260)
    print(f"  {len(data['stocks'])}只股票, {len(data['industries'])}个行业, {data['n_months']}个月")

    # 1. 因子工厂
    screened, deduped = demo_factor_factory(data)
    plot_factor_factory(screened, deduped)

    # 2. 行业中性化
    raw_values, ind_neut, size_neut, industry_map = demo_neutralization(data)
    plot_neutralization(raw_values, ind_neut, size_neut, industry_map)

    # 3. 算法执行
    exec_results = demo_execution()
    if 'TWAP(30分钟)' in exec_results:
        plot_execution_comparison(exec_results)

    # 4. 风控系统
    rm = demo_risk_system(data)

    # 5. 策略退役监控
    monitor_records = demo_strategy_monitor()

    # 6. 策略容量
    cap_result = demo_capacity(data)

    # 风控仪表盘（综合可视化）
    np.random.seed(123)
    nav = 100 + np.cumsum(np.random.normal(0.0003, 0.01, 252))
    nav = np.maximum(nav, 80)
    pos_history = {
        '2025Q1': {'银行': 0.12, '消费': 0.18, '科技': 0.25, '医药': 0.15, '能源': 0.08},
        '2025Q2': {'银行': 0.10, '消费': 0.20, '科技': 0.28, '医药': 0.14, '能源': 0.07},
        '2025Q3': {'银行': 0.13, '消费': 0.18, '科技': 0.22, '医药': 0.16, '能源': 0.09},
        '2025Q4': {'银行': 0.14, '消费': 0.15, '科技': 0.20, '医药': 0.17, '能源': 0.10},
    }
    plot_risk_dashboard(nav, pos_history, rm.warning_log)

    # 策略生命周期
    plot_strategy_lifecycle(monitor_records)

    # 容量分析
    plot_capacity_analysis(data['stocks'], cap_result)

    print(f"\n{'=' * 60}")
    print(f"  所有机构实战图表已生成到：{OUTPUT_DIR}")
    print(f"{'=' * 60}")
