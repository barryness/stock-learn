"""
第七课配套实战代码：基金投资实战 —— 组合构建与策略回测
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
# 1. 定投 vs 一次性投入对比
# ============================================================

def dca_vs_lump_sum(monthly_invest, years, annual_return, volatility, seed=42):
    """定投 vs 一次性投入的回测对比"""
    np.random.seed(seed)
    months = years * 12
    monthly_r = annual_return / 12
    monthly_vol = volatility / np.sqrt(12)

    returns = np.random.normal(monthly_r, monthly_vol, months)
    prices = np.cumprod(1 + returns)

    # 定投
    dca_shares = 0
    dca_invested = 0
    dca_values = []
    for i, price in enumerate(prices):
        dca_shares += monthly_invest / price
        dca_invested += monthly_invest
        dca_values.append(dca_shares * price)

    # 一次性投入
    lump_total = monthly_invest * months
    lump_shares = lump_total / prices[0]
    lump_values = [lump_shares * p for p in prices]

    return {
        'prices': prices,
        'dca_values': np.array(dca_values),
        'lump_values': np.array(lump_values),
        'total_invested': lump_total,
        'months': months
    }


def demo_dca_vs_lump():
    """演示定投 vs 一次性投入"""
    print("\n" + "=" * 60)
    print("  定投（DCA）vs 一次性投入 回测对比")
    print("=" * 60)

    # 场景1：先跌后涨（微笑曲线）
    print("\n📊 场景1：先跌后涨（微笑曲线）")
    result1 = dca_vs_lump_sum(monthly_invest=1000, years=5, annual_return=0.08,
                               volatility=0.25, seed=42)
    dca_final = result1['dca_values'][-1]
    lump_final = result1['lump_values'][-1]
    invested = result1['total_invested']
    print(f"  总投入：{invested:,.0f} 元")
    print(f"  定投终值：{dca_final:,.0f} 元  |  收益率：{(dca_final/invested-1)*100:+.1f}%")
    print(f"  一次性终值：{lump_final:,.0f} 元  |  收益率：{(lump_final/invested-1)*100:+.1f}%")
    print(f"  定投超额收益：{dca_final - lump_final:,.0f} 元")

    # 场景2：单边上涨
    print("\n📊 场景2：单边上涨（牛市）")
    result2 = dca_vs_lump_sum(monthly_invest=1000, years=5, annual_return=0.18,
                               volatility=0.15, seed=123)
    dca_final2 = result2['dca_values'][-1]
    lump_final2 = result2['lump_values'][-1]
    print(f"  定投终值：{dca_final2:,.0f} 元  |  收益率：{(dca_final2/invested-1)*100:+.1f}%")
    print(f"  一次性终值：{lump_final2:,.0f} 元  |  收益率：{(lump_final2/invested-1)*100:+.1f}%")
    print(f"  注：单边上涨中一次性投入跑赢定投，但定投心理压力更小")

    # 场景3：长期定投（30年）
    print("\n📊 场景3：30年长期定投")
    for monthly in [1000, 3000, 5000]:
        r = dca_vs_lump_sum(monthly_invest=monthly, years=30, annual_return=0.08,
                             volatility=0.18, seed=99)
        fv = r['dca_values'][-1]
        total = r['total_invested']
        print(f"  月投{monthly:>5,}元 → 总投入{total:>10,.0f}元 → 终值{fv:>12,.0f}元 ({(fv/total-1)*100:+.0f}%)")

    return result1, result2


def plot_dca_comparison(result1, result2):
    """绘制定投对比图"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 图1：微笑曲线场景
    ax = axes[0]
    months = np.arange(result1['months'])
    years_label = months / 12
    ax.plot(years_label, result1['dca_values'], linewidth=2, label='定投', color='#2E86AB')
    ax.plot(years_label, result1['lump_values'], linewidth=2, label='一次性投入', color='#A23B72')
    ax.axhline(y=result1['total_invested'], color='gray', linestyle='--', alpha=0.5, label='总投入')
    ax.set_xlabel('年数')
    ax.set_ylabel('账户价值 (元)')
    ax.set_title('场景1：先跌后涨（微笑曲线）')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 图2：单边上涨场景
    ax = axes[1]
    ax.plot(years_label, result2['dca_values'], linewidth=2, label='定投', color='#2E86AB')
    ax.plot(years_label, result2['lump_values'], linewidth=2, label='一次性投入', color='#A23B72')
    ax.axhline(y=result2['total_invested'], color='gray', linestyle='--', alpha=0.5, label='总投入')
    ax.set_xlabel('年数')
    ax.set_ylabel('账户价值 (元)')
    ax.set_title('场景2：单边上涨（牛市）')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'dca_comparison.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] 定投对比图已保存: {path}")


# ============================================================
# 2. 网格交易模拟
# ============================================================

class GridTrader:
    """网格交易模拟器"""

    def __init__(self, base_price, lower_bound, upper_bound, grids, capital_per_grid, total_capital):
        self.base_price = base_price
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
        self.grids = grids
        self.capital_per_grid = capital_per_grid
        self.total_capital = total_capital

        self.cash = total_capital
        self.shares = 0
        self.trades = []
        self.portfolio_values = []

        step = (upper_bound - lower_bound) / (grids - 1)
        self.grid_levels = [lower_bound + i * step for i in range(grids)]
        self.base_idx = min(range(grids), key=lambda i: abs(self.grid_levels[i] - base_price))
        self.last_grid = self.base_idx

    def step(self, price):
        """处理一个价格点"""
        current_grid = min(range(self.grids),
                           key=lambda i: abs(self.grid_levels[i] - price))

        if current_grid < self.last_grid:
            for g in range(current_grid, self.last_grid):
                buy_price = self.grid_levels[g]
                if self.cash >= self.capital_per_grid:
                    shares_bought = self.capital_per_grid / buy_price
                    self.shares += shares_bought
                    self.cash -= self.capital_per_grid
                    self.trades.append(('买入', buy_price, self.capital_per_grid))
        elif current_grid > self.last_grid:
            for g in range(self.last_grid + 1, current_grid + 1):
                sell_price = self.grid_levels[g]
                if self.shares > 0:
                    sell_value = self.capital_per_grid
                    shares_to_sell = sell_value / sell_price
                    if shares_to_sell > self.shares:
                        shares_to_sell = self.shares
                        sell_value = shares_to_sell * sell_price
                    self.shares -= shares_to_sell
                    self.cash += sell_value
                    self.trades.append(('卖出', sell_price, sell_value))

        self.last_grid = current_grid
        self.portfolio_values.append(self.cash + self.shares * price)

    def run(self, price_series):
        for price in price_series:
            self.step(price)
        return self.portfolio_values


def demo_grid_trading():
    """演示网格交易"""
    print("\n" + "=" * 60)
    print("  网格交易模拟")
    print("=" * 60)

    np.random.seed(42)
    months = 24
    base_price = 4.0

    # 生成震荡价格路径
    t = np.arange(months)
    trend = 0.001 * t
    noise = 0.06 * np.sin(t * 0.5) + 0.04 * np.sin(t * 1.3) + np.random.normal(0, 0.02, months)
    prices = base_price * np.exp(trend + np.cumsum(noise) * 0.3)

    # 网格交易
    trader = GridTrader(base_price=base_price, lower_bound=3.2, upper_bound=4.8,
                         grids=9, capital_per_grid=10000, total_capital=100000)
    pv_grid = trader.run(prices)

    # 买入持有
    buy_hold_shares = 100000 / prices[0]
    pv_hold = buy_hold_shares * prices

    print(f"\n  网格设置：{trader.grids}档，区间{trader.lower_bound}-{trader.upper_bound}元")
    print(f"  每档资金：{trader.capital_per_grid:,.0f} 元，总资金：{trader.total_capital:,.0f} 元")
    print(f"  交易次数：{len(trader.trades)} 次")
    buy_count = sum(1 for t in trader.trades if t[0] == '买入')
    sell_count = sum(1 for t in trader.trades if t[0] == '卖出')
    print(f"  其中买入 {buy_count} 次，卖出 {sell_count} 次")

    grid_final = pv_grid[-1]
    hold_final = pv_hold[-1]
    print(f"\n  网格交易终值：{grid_final:,.0f} 元  |  收益率：{(grid_final/100000-1)*100:+.1f}%")
    print(f"  买入持有终值：{hold_final:,.0f} 元  |  收益率：{(hold_final/100000-1)*100:+.1f}%")
    print(f"  网格增厚收益：{grid_final - hold_final:,.0f} 元")

    return prices, pv_grid, pv_hold, trader


def plot_grid_trading(prices, pv_grid, pv_hold, trader):
    """绘制网格交易图"""
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))

    # 上图：价格走势 + 网格线
    ax = axes[0]
    months = np.arange(len(prices))
    ax.plot(months, prices, linewidth=2, color='#2E86AB', label='ETF价格')
    for level in trader.grid_levels:
        ax.axhline(y=level, color='gray', linestyle='--', alpha=0.3, linewidth=0.5)
    ax.axhline(y=trader.grid_levels[trader.base_idx], color='#A23B72',
               linestyle='-', alpha=0.6, linewidth=1, label='中枢')
    buys = [i for i, t in enumerate(trader.trades) if t[0] == '买入']
    sells = [i for i, t in enumerate(trader.trades) if t[0] == '卖出']
    if buys:
        ax.scatter([b for b in buys], [prices[min(b, len(prices)-1)] for b in buys],
                    color='green', marker='^', s=60, zorder=5, label='买入')
    if sells:
        ax.scatter([s for s in sells], [prices[min(s, len(prices)-1)] for s in sells],
                    color='red', marker='v', s=60, zorder=5, label='卖出')
    ax.set_xlabel('月份')
    ax.set_ylabel('价格 (元)')
    ax.set_title('网格交易：价格走势与网格触发')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)

    # 下图：账户价值对比
    ax = axes[1]
    ax.plot(months, pv_grid, linewidth=2, color='#2E86AB', label='网格交易')
    ax.plot(months, pv_hold, linewidth=2, color='#A23B72', label='买入持有')
    ax.axhline(y=100000, color='gray', linestyle='--', alpha=0.5, label='初始资金')
    ax.set_xlabel('月份')
    ax.set_ylabel('账户价值 (元)')
    ax.set_title('网格交易 vs 买入持有')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'grid_trading.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] 网格交易图已保存: {path}")


# ============================================================
# 3. 红利再投资 vs 不复投对比
# ============================================================

def dividend_reinvestment(principal, years, price_growth, dividend_yield, reinvest=True):
    """计算红利再投资 vs 不复投的终值差异"""
    shares = principal  # 假设初始价格=1，初始份额=本金
    price = 1.0
    total_dividends = 0
    history = []

    for year in range(years):
        price *= (1 + price_growth)
        dividend = shares * price * dividend_yield
        total_dividends += dividend

        if reinvest:
            shares += dividend / price

        history.append({
            'year': year + 1,
            'price': price,
            'shares': shares,
            'value': shares * price,
            'dividend': dividend,
            'total_dividends': total_dividends
        })

    return history


def demo_dividend_reinvestment():
    """演示红利再投资的力量"""
    print("\n" + "=" * 60)
    print("  红利再投资 vs 红利取出 对比")
    print("=" * 60)

    principal = 100000
    years = 20
    price_growth = 0.05
    dividend_yield = 0.05

    h_reinvest = dividend_reinvestment(principal, years, price_growth, dividend_yield, reinvest=True)
    h_no_reinvest = dividend_reinvestment(principal, years, price_growth, dividend_yield, reinvest=False)

    fv_reinvest = h_reinvest[-1]['value']
    fv_no = h_no_reinvest[-1]['value']
    total_div_reinvest = h_reinvest[-1]['total_dividends']

    print(f"\n  初始投入：{principal:,.0f} 元，年化价格增长：{price_growth:.0%}，股息率：{dividend_yield:.0%}")
    print(f"  红利再投资终值：{fv_reinvest:,.0f} 元  ({(fv_reinvest/principal-1)*100:+.1f}%)")
    print(f"  红利取出终值：  {fv_no:,.0f} 元  ({(fv_no/principal-1)*100:+.1f}%)")
    print(f"  再投资多赚：    {fv_reinvest - fv_no:,.0f} 元")
    print(f"  累计收到红利：  {total_div_reinvest:,.0f} 元 (再投资发挥了复利威力)")

    return h_reinvest, h_no_reinvest


def plot_dividend_reinvestment(h_reinvest, h_no_reinvest):
    """绘制红利对比图"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    years = [h['year'] for h in h_reinvest]

    # 图1：账户价值
    ax = axes[0]
    v_re = [h['value'] for h in h_reinvest]
    v_no = [h['value'] for h in h_no_reinvest]
    ax.plot(years, v_re, linewidth=2, color='#2E86AB', label='红利再投资')
    ax.plot(years, v_no, linewidth=2, color='#A23B72', label='红利取出')
    ax.fill_between(years, v_re, v_no, alpha=0.15, color='#2E86AB')
    ax.set_xlabel('年数')
    ax.set_ylabel('账户价值 (元)')
    ax.set_title('红利再投资 vs 红利取出')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 图2：每年红利
    ax = axes[1]
    d_re = [h['dividend'] for h in h_reinvest]
    d_no = [h['dividend'] for h in h_no_reinvest]
    ax.bar(np.array(years) - 0.15, d_re, 0.3, color='#2E86AB', label='再投资（份额增长）')
    ax.bar(np.array(years) + 0.15, d_no, 0.3, color='#A23B72', label='取出（份额不变）')
    ax.set_xlabel('年数')
    ax.set_ylabel('年红利 (元)')
    ax.set_title('每年红利金额对比')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'dividend_reinvestment.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] 红利对比图已保存: {path}")


# ============================================================
# 4. 再平衡模拟
# ============================================================

def rebalance_simulation(initial_allocation, years, annual_returns, annual_vols, rebalance_freq=1):
    """模拟再平衡 vs 不再平衡"""
    np.random.seed(42)
    months = years * 12
    monthly_returns = {}
    monthly_vols = {}

    for asset in initial_allocation:
        monthly_returns[asset] = annual_returns[asset] / 12
        monthly_vols[asset] = annual_vols[asset] / np.sqrt(12)

    # 不再平衡
    no_rebal_values = np.zeros((months, len(initial_allocation)))
    current_weights = {}
    for j, asset in enumerate(initial_allocation):
        rets = np.random.normal(monthly_returns[asset], monthly_vols[asset], months)
        no_rebal_values[:, j] = initial_allocation[asset] * np.cumprod(1 + rets)

    no_rebal_total = no_rebal_values.sum(axis=1)

    # 每年再平衡
    rebal_values = np.zeros((months, len(initial_allocation)))
    current_values = {asset: initial_allocation[asset] for asset in initial_allocation}
    target_weights = {asset: initial_allocation[asset] / sum(initial_allocation.values())
                      for asset in initial_allocation}

    for month in range(months):
        total = sum(current_values.values())
        for j, asset in enumerate(initial_allocation):
            ret = np.random.normal(monthly_returns[asset], monthly_vols[asset])
            current_values[asset] *= (1 + ret)
            rebal_values[month, j] = current_values[asset]

        if (month + 1) % (rebalance_freq * 12) == 0 and month > 0:
            total = sum(current_values.values())
            for asset in initial_allocation:
                current_values[asset] = total * target_weights[asset]

    rebal_total = rebal_values.sum(axis=1)

    return no_rebal_total, rebal_total


def demo_rebalance():
    """演示再平衡的价值"""
    print("\n" + "=" * 60)
    print("  再平衡 vs 不再平衡 长期对比")
    print("=" * 60)

    allocation = {
        '沪深300ETF': 60000,
        '债券基金': 40000
    }
    returns = {'沪深300ETF': 0.10, '债券基金': 0.04}
    vols = {'沪深300ETF': 0.22, '债券基金': 0.05}

    no_rebal, rebal = rebalance_simulation(allocation, years=20, annual_returns=returns,
                                            annual_vols=vols, rebalance_freq=1)

    print(f"\n  初始配置：沪深300 60% + 债券 40%，初始资金 100,000 元")
    print(f"  模拟20年...")
    print(f"  不进行再平衡终值：{no_rebal[-1]:,.0f} 元  |  年化：{(no_rebal[-1]/100000)**(1/20)-1:.2%}")
    print(f"  每年再平衡终值：  {rebal[-1]:,.0f} 元  |  年化：{(rebal[-1]/100000)**(1/20)-1:.2%}")
    print(f"  再平衡增厚：      {rebal[-1] - no_rebal[-1]:,.0f} 元")

    return no_rebal, rebal


def plot_rebalance(no_rebal, rebal):
    """绘制再平衡对比图"""
    fig, ax = plt.subplots(figsize=(12, 5))

    months = np.arange(len(no_rebal))
    years_label = months / 12

    ax.plot(years_label, no_rebal, linewidth=2, color='#A23B72', alpha=0.7, label='不再平衡')
    ax.plot(years_label, rebal, linewidth=2, color='#2E86AB', label='每年再平衡')
    ax.fill_between(years_label, rebal, no_rebal, alpha=0.1, color='#2E86AB')

    ax.set_xlabel('年数')
    ax.set_ylabel('账户价值 (元)')
    ax.set_title('再平衡 vs 不再平衡（股60%债40%，20年模拟）')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'rebalance_comparison.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] 再平衡对比图已保存: {path}")


# ============================================================
# 5. 投资组合构建与分析
# ============================================================

PORTFOLIO_TEMPLATES = {
    '极简版': {
        '沪深300ETF': 1.0,
    },
    '标准版': {
        '沪深300ETF': 0.50,
        '中证500ETF': 0.25,
        '纳指/标普ETF': 0.25,
    },
    '增强版': {
        '沪深300ETF': 0.40,
        '中证500ETF': 0.15,
        '纳指ETF': 0.15,
        '消费ETF': 0.15,
        '医药ETF': 0.15,
    },
    '全球化版': {
        '沪深300ETF': 0.30,
        '标普500ETF': 0.25,
        '纳指100ETF': 0.15,
        '恒生科技ETF': 0.10,
        '黄金ETF': 0.10,
        '债券ETF': 0.10,
    },
}

ALL_WEATHER = {
    '沪深300ETF': 0.20,
    '标普500ETF': 0.20,
    '黄金ETF': 0.10,
    '债券基金': 0.40,
    '红利低波ETF': 0.10,
}

ASSET_RETURNS = {
    '沪深300ETF': (0.09, 0.22),
    '中证500ETF': (0.10, 0.28),
    '纳指ETF': (0.12, 0.22),
    '纳指100ETF': (0.13, 0.23),
    '标普500ETF': (0.10, 0.18),
    '纳指/标普ETF': (0.11, 0.20),
    '消费ETF': (0.10, 0.24),
    '医药ETF': (0.09, 0.26),
    '恒生科技ETF': (0.11, 0.35),
    '黄金ETF': (0.06, 0.17),
    '债券ETF': (0.04, 0.06),
    '债券基金': (0.04, 0.05),
    '红利低波ETF': (0.10, 0.18),
}


def portfolio_stats(weights, annual_returns, annual_vols, corr_matrix=None):
    """计算组合的预期收益和风险"""
    assets = list(weights.keys())
    w = np.array([weights[a] for a in assets])
    r = np.array([annual_returns[a] for a in assets])
    vols = np.array([annual_vols[a] for a in assets])

    port_return = np.dot(w, r)

    if corr_matrix is None:
        n = len(assets)
        corr = np.eye(n)
        for i in range(n):
            for j in range(i + 1, n):
                if ('ETF' in assets[i] and 'ETF' in assets[j]) or \
                   ('基金' in assets[i] and '基金' in assets[j]):
                    corr[i, j] = corr[j, i] = 0.55
                elif ('黄金' in assets[i]) or ('债券' in assets[i]) or \
                     ('黄金' in assets[j]) or ('债券' in assets[j]):
                    corr[i, j] = corr[j, i] = 0.0
                else:
                    corr[i, j] = corr[j, i] = 0.3
        cov = np.outer(vols, vols) * corr
    else:
        cov = np.outer(vols, vols) * corr_matrix

    port_vol = np.sqrt(w @ cov @ w)
    sharpe = port_return / port_vol if port_vol > 0 else 0

    return port_return, port_vol, sharpe


def demo_portfolios():
    """演示各种组合模板"""
    print("\n" + "=" * 60)
    print("  投资组合模板对比")
    print("=" * 60)

    results = []

    # 提取资产预期
    all_assets = {}
    for w_dict in PORTFOLIO_TEMPLATES.values():
        all_assets.update(w_dict)
    all_assets.update(ALL_WEATHER)

    annual_ret = {}
    annual_vol = {}
    for asset in all_assets:
        if asset in ASSET_RETURNS:
            annual_ret[asset], annual_vol[asset] = ASSET_RETURNS[asset]
        else:
            annual_ret[asset], annual_vol[asset] = 0.07, 0.15

    print(f"\n  {'模板':<10s} {'预期年化':>8s} {'波动率':>8s} {'夏普比':>8s} {'成分'}")
    print(f"  {'-'*10} {'-'*8} {'-'*8} {'-'*8} {'-'*30}")

    for name, weights in {**PORTFOLIO_TEMPLATES, **{'全天候': ALL_WEATHER}}.items():
        port_ret, port_vol, sharpe = portfolio_stats(weights, annual_ret, annual_vol)
        results.append((name, port_ret, port_vol, sharpe, weights))
        assets_str = '+'.join([f"{a.split('ETF')[0] if 'ETF' in a else a[:4]}" for a in weights])
        print(f"  {name:<10s} {port_ret:>7.1%}   {port_vol:>7.1%}   {sharpe:>7.2f}   {assets_str}")

    return results


def plot_portfolio_compare(results):
    """绘制组合对比图"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    names = [r[0] for r in results]
    rets = [r[1] for r in results]
    vols = [r[2] for r in results]
    sharpes = [r[3] for r in results]
    colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#3B1F2B']

    # 图1：风险-收益散点图
    ax = axes[0]
    for i, (name, ret, vol, _, _) in enumerate(results):
        ax.scatter(vol, ret, s=200, color=colors[i], zorder=5)
        ax.annotate(name, (vol, ret), textcoords="offset points", xytext=(8, 0),
                     fontsize=10, fontweight='bold')
    for vol in np.linspace(0, 0.25, 50):
        ax.plot(vol, vol * 0.5, color='gray', alpha=0.15, linewidth=0.5)
        ax.plot(vol, vol * 0.7, color='gray', alpha=0.15, linewidth=0.5)
    ax.set_xlabel('波动率（风险）')
    ax.set_ylabel('预期年化收益率')
    ax.set_title('组合风险-收益图')
    ax.grid(True, alpha=0.3)

    # 图2：夏普比率柱状图
    ax = axes[1]
    bars = ax.bar(names, sharpes, color=colors, alpha=0.85)
    for bar, s in zip(bars, sharpes):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                f'{s:.2f}', ha='center', fontweight='bold', fontsize=11)
    ax.set_ylabel('夏普比率')
    ax.set_title('各组合夏普比率对比')
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'portfolio_comparison.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] 组合对比图已保存: {path}")


# ============================================================
# 6. 养老下滑路径（Glide Path）
# ============================================================

def glide_path_simulation(start_age, retirement_age, monthly_invest, annual_return, volatility):
    """模拟养老下滑路径"""
    np.random.seed(42)
    total_months = (retirement_age - start_age) * 12

    returns = np.random.normal(annual_return / 12, volatility / np.sqrt(12), total_months)
    prices = np.cumprod(1 + returns)

    equity_ratio = []
    bond_ratio = []
    portfolio_values = []

    equity_value = 0
    bond_value = 0
    total_invested = 0

    for month in range(total_months):
        age = start_age + month / 12
        eq_pct = max(0.20, (120 - age) / 100)

        eq_invest = monthly_invest * eq_pct
        bond_invest = monthly_invest * (1 - eq_pct)

        equity_value = equity_value * (1 + returns[month]) + eq_invest
        bond_value = bond_value * (1 + 0.035 / 12) + bond_invest
        total_invested += monthly_invest

        equity_ratio.append(eq_pct)
        bond_ratio.append(1 - eq_pct)
        portfolio_values.append(equity_value + bond_value)

    return {
        'ages': np.linspace(start_age, retirement_age, total_months),
        'equity_ratio': np.array(equity_ratio),
        'bond_ratio': np.array(bond_ratio),
        'portfolio_values': np.array(portfolio_values),
        'equity_value': equity_value,
        'bond_value': bond_value,
        'total_invested': total_invested,
        'final_value': portfolio_values[-1]
    }


def demo_glide_path():
    """演示养老下滑路径"""
    print("\n" + "=" * 60)
    print("  养老下滑路径（Glide Path）模拟")
    print("=" * 60)

    result = glide_path_simulation(start_age=30, retirement_age=60, monthly_invest=5000,
                                    annual_return=0.09, volatility=0.20)

    print(f"\n  计划：30岁开始 → 60岁退休，月投5,000元")
    print(f"  总投入：{result['total_invested']:,.0f} 元")
    print(f"  退休时总资产：{result['final_value']:,.0f} 元")
    print(f"  总收益：{result['final_value'] - result['total_invested']:,.0f} 元")
    print(f"  年化回报：{(result['final_value'] / result['total_invested']) ** (1/30) - 1:.2%}")

    print(f"\n  '120-年龄'下滑路径示意：")
    for age in [30, 35, 40, 45, 50, 55, 60]:
        eq = max(0.20, (120 - age) / 100)
        bond = 1 - eq
        print(f"    {age}岁：权益{eq:.0%} + 债券{bond:.0%}")

    return result


def plot_glide_path(result):
    """绘制下滑路径图"""
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))

    ages = result['ages']

    # 上图：权益/债券比例变化
    ax = axes[0]
    ax.fill_between(ages, result['equity_ratio'], alpha=0.5, color='#2E86AB', label='权益类')
    ax.fill_between(ages, 0, result['bond_ratio'], alpha=0.5, color='#A23B72', label='债券类')
    ax.plot(ages, result['equity_ratio'], linewidth=2, color='#2E86AB')
    ax.plot(ages, result['bond_ratio'], linewidth=2, color='#A23B72')
    ax.set_xlabel('年龄')
    ax.set_ylabel('配置比例')
    ax.set_title('"120-年龄"下滑路径：权益比例随年龄递减')
    ax.legend(loc='center right')
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1.05)

    # 下图：资产增长
    ax = axes[1]
    years = ages
    values = result['portfolio_values'] / 10000
    ax.plot(years, values, linewidth=2, color='#2E86AB')
    ax.fill_between(years, 0, values, alpha=0.15, color='#2E86AB')
    ax.set_xlabel('年龄')
    ax.set_ylabel('账户价值 (万元)')
    ax.set_title('养老资产增长曲线（月投5,000元，30年）')
    ax.grid(True, alpha=0.3)

    # 标注关键节点
    for age in [30, 40, 50, 60]:
        idx = int((age - 30) * 12)
        if idx < len(values):
            ax.annotate(f'{values[idx]:.0f}万', (age, values[idx]),
                         textcoords="offset points", xytext=(0, 10),
                         fontsize=9, ha='center')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'glide_path.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] 下滑路径图已保存: {path}")


# ============================================================
# 7. 全天候策略回测
# ============================================================

def all_weather_backtest(years, initial_capital):
    """全天候策略历史模拟"""
    np.random.seed(42)
    months = years * 12
    weights = ALL_WEATHER
    assets = list(weights.keys())

    monthly_ret = {}
    for asset in assets:
        ret, vol = ASSET_RETURNS.get(asset, (0.07, 0.15))
        monthly_ret[asset] = np.random.normal(ret / 12, vol / np.sqrt(12), months)

    values = np.zeros((months, len(assets)))
    current = {asset: initial_capital * weights[asset] for asset in assets}

    for month in range(months):
        for j, asset in enumerate(assets):
            current[asset] *= (1 + monthly_ret[asset][month])
            values[month, j] = current[asset]

    total = values.sum(axis=1)

    # 计算回撤
    peak = np.maximum.accumulate(total)
    drawdown = (total - peak) / peak

    return {
        'total_values': total,
        'max_drawdown': drawdown.min(),
        'final_value': total[-1],
        'annual_return': (total[-1] / initial_capital) ** (1 / years) - 1,
        'drawdown_series': drawdown,
    }


def demo_all_weather():
    """演示全天候策略"""
    print("\n" + "=" * 60)
    print("  全天候策略（达利欧简化版）回测")
    print("=" * 60)

    result = all_weather_backtest(years=20, initial_capital=1000000)

    print(f"\n  简化版全天候配置：")
    for asset, weight in ALL_WEATHER.items():
        print(f"    {asset:<15s} {weight:.0%}")

    print(f"\n  20年回测结果（模拟）：")
    print(f"  初始资金：{1000000:,.0f} 元")
    print(f"  终值：    {result['final_value']:,.0f} 元")
    print(f"  年化收益：{result['annual_return']:.2%}")
    print(f"  最大回撤：{result['max_drawdown']:.2%}")
    print(f"\n  全天候策略的特点：不大赚不大亏，每年都'过得去'")
    print(f"  适合：大资金、低风险偏好、不想焦虑的投资者")

    return result


def plot_all_weather(result):
    """绘制全天候策略图"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    months = np.arange(len(result['total_values']))
    years_label = months / 12

    # 图1：资产增长
    ax = axes[0]
    ax.plot(years_label, result['total_values'] / 10000, linewidth=2, color='#2E86AB')
    ax.fill_between(years_label, 0, result['total_values'] / 10000,
                     alpha=0.15, color='#2E86AB')
    ax.set_xlabel('年数')
    ax.set_ylabel('账户价值 (万元)')
    ax.set_title('全天候策略：20年资产增长')
    ax.grid(True, alpha=0.3)

    # 图2：回撤曲线
    ax = axes[1]
    ax.fill_between(years_label, 0, result['drawdown_series'] * 100,
                     color='#A23B72', alpha=0.3)
    ax.plot(years_label, result['drawdown_series'] * 100, linewidth=1.5, color='#A23B72')
    ax.set_xlabel('年数')
    ax.set_ylabel('回撤 (%)')
    ax.set_title('全天候策略：回撤曲线')
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color='gray', linewidth=0.5)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'all_weather.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] 全天候策略图已保存: {path}")


# ============================================================
# 8. 核心-卫星策略可视化
# ============================================================

def plot_core_satellite():
    """绘制核心-卫星策略结构图"""
    fig, ax = plt.subplots(figsize=(10, 8))

    # 使用同心圆饼图展示核心-卫星结构
    outer_sizes = [0.80, 0.20]
    inner_sizes = [0.375, 0.1875, 0.1875, 0.125, 0.125,  # 核心
                   0.25, 0.25, 0.25, 0.25]                 # 卫星

    outer_labels = ['核心仓位\n(80%)', '卫星仓位\n(20%)']
    outer_colors = ['#2E86AB', '#F18F01']

    inner_labels = [
        '沪深300ETF\n(30%)', '中证500ETF\n(15%)', '纳指ETF\n(15%)',
        '红利低波\n(10%)', '债券基金\n(10%)', '消费ETF\n(5%)',
        '医药ETF\n(5%)', '恒生科技\n(5%)', '网格交易\n(5%)'
    ]
    inner_colors = [
        '#1B6B93', '#267BA6', '#318CB9',
        '#4DA8CC', '#70C1DF', '#F29E2E',
        '#F5B041', '#F7C36D', '#F9D69A'
    ]

    # 外圈
    wedges1, texts1 = ax.pie(outer_sizes, radius=1, labels=outer_labels,
                              colors=outer_colors, startangle=90,
                              labeldistance=0.85,
                              wedgeprops=dict(width=0.25, edgecolor='white'))
    for t in texts1:
        t.set_fontsize(13)
        t.set_fontweight('bold')

    # 内圈
    wedges2, texts2, autotexts2 = ax.pie(inner_sizes, radius=0.75,
                                          labels=inner_labels,
                                          colors=inner_colors,
                                          startangle=90,
                                          labeldistance=0.62,
                                          autopct='',
                                          wedgeprops=dict(width=0.25, edgecolor='white'))
    for t in texts2:
        t.set_fontsize(8)

    ax.set_title('核心-卫星策略结构示意', fontsize=16, fontweight='bold', pad=20)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'core_satellite.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] 核心-卫星结构图已保存: {path}")


# ============================================================
# 9. 投资决策工具
# ============================================================

class InvestmentPlanner:
    """个人投资计划生成器"""

    def __init__(self, age, monthly_save, current_savings, goal, goal_amount, risk_tolerance='medium'):
        self.age = age
        self.monthly_save = monthly_save
        self.current_savings = current_savings
        self.goal = goal
        self.goal_amount = goal_amount
        self.risk_tolerance = risk_tolerance

    def generate_plan(self):
        equity_pct = max(0.20, (120 - self.age) / 100)
        if self.risk_tolerance == 'high':
            equity_pct = min(0.95, equity_pct + 0.10)
        elif self.risk_tolerance == 'low':
            equity_pct = max(0.20, equity_pct - 0.15)

        bond_pct = 1 - equity_pct

        # 权益内部配置
        equity_alloc = {
            '沪深300ETF': 0.50 * equity_pct,
            '中证500ETF': 0.20 * equity_pct,
            '纳指/标普ETF': 0.20 * equity_pct,
            '红利低波ETF': 0.10 * equity_pct,
        }
        bond_alloc = {'债券基金': bond_pct}
        full_alloc = {**equity_alloc, **bond_alloc}

        portfolio_return = 0.09 * equity_pct + 0.04 * bond_pct
        portfolio_vol = 0.20 * equity_pct + 0.05 * bond_pct

        return {
            'equity_pct': equity_pct,
            'bond_pct': bond_pct,
            'allocation': full_alloc,
            'expected_return': portfolio_return,
            'expected_vol': portfolio_vol,
            'monthly_invest': self.monthly_save,
        }

    def project_growth(self, plan, years=30):
        """预测资产增长"""
        monthly_r = plan['expected_return'] / 12
        months = years * 12
        values = []
        current = self.current_savings

        for month in range(months):
            current = current * (1 + monthly_r) + self.monthly_save
            values.append(current)

        return np.array(values)

    def print_report(self):
        plan = self.generate_plan()
        projection = self.project_growth(plan)

        print(f"\n{'='*60}")
        print(f"  个人投资计划")
        print(f"{'='*60}")
        print(f"\n  📋 基本信息：")
        print(f"    年龄：{self.age}岁")
        print(f"    风险偏好：{self.risk_tolerance}")
        print(f"    月定投金额：{self.monthly_save:,}元")
        print(f"    现有资金：{self.current_savings:,}元")
        print(f"    投资目标：{self.goal}（目标金额 {self.goal_amount:,}元）")

        print(f"\n  📊 资产配置：")
        print(f"    权益类：{plan['equity_pct']:.0%}  |  债券类：{plan['bond_pct']:.0%}")
        for asset, weight in plan['allocation'].items():
            print(f"    {asset:<15s} {weight:>6.1%}")

        print(f"\n  📈 预期指标：")
        print(f"    预期年化收益：{plan['expected_return']:.2%}")
        print(f"    预期波动率：  {plan['expected_vol']:.2%}")

        # 关键时间节点
        for yr in [5, 10, 20, 30]:
            idx = yr * 12 - 1
            if idx < len(projection):
                total_invested = self.current_savings + self.monthly_save * yr * 12
                gain = projection[idx] - total_invested
                print(f"    {yr:>2}年后：{projection[idx]:>13,.0f}元 (投入{total_invested:,.0f}, 收益{gain:,.0f})")

        return plan, projection


def demo_planner():
    """演示投资规划工具"""
    print("\n" + "=" * 60)
    print("  个人投资规划工具")
    print("=" * 60)

    # 示例1：30岁投资者
    planner = InvestmentPlanner(age=30, monthly_save=5000, current_savings=100000,
                                 goal='退休储备', goal_amount=5000000, risk_tolerance='medium')
    plan1, proj1 = planner.print_report()

    # 示例2：45岁投资者
    print("\n" + "-" * 40)
    planner2 = InvestmentPlanner(age=45, monthly_save=10000, current_savings=500000,
                                  goal='养老加固', goal_amount=3000000, risk_tolerance='medium')
    plan2, proj2 = planner2.print_report()

    return plan1, proj1, plan2, proj2


# ============================================================
# 主程序
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("  第七课实战代码：基金投资策略回测与组合构建")
    print("=" * 60)

    # 1. 定投 vs 一次性投入
    r1, r2 = demo_dca_vs_lump()
    plot_dca_comparison(r1, r2)

    # 2. 网格交易
    prices, pv_grid, pv_hold, trader = demo_grid_trading()
    plot_grid_trading(prices, pv_grid, pv_hold, trader)

    # 3. 红利再投资
    h_re, h_no = demo_dividend_reinvestment()
    plot_dividend_reinvestment(h_re, h_no)

    # 4. 再平衡
    no_rebal, rebal = demo_rebalance()
    plot_rebalance(no_rebal, rebal)

    # 5. 组合对比
    port_results = demo_portfolios()
    plot_portfolio_compare(port_results)

    # 6. 养老下滑路径
    glide_result = demo_glide_path()
    plot_glide_path(glide_result)

    # 7. 全天候策略
    aw_result = demo_all_weather()
    plot_all_weather(aw_result)

    # 8. 核心-卫星结构
    plot_core_satellite()

    # 9. 投资规划工具
    demo_planner()

    print(f"\n{'=' * 60}")
    print(f"  所有图表已生成到：{OUTPUT_DIR}")
    print(f"{'=' * 60}")
