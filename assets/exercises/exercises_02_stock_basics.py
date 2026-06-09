"""
第二课配套实战代码：股票基础指标计算 + 数据获取
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import os

# 尝试设置中文字体
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


# ============================================================
# 1. 股票基础指标计算器
# ============================================================

def calculate_stock_metrics(price, eps, book_value_per_share, dividend_per_share,
                             total_shares, net_profit, revenue, total_assets,
                             total_equity):
    """
    计算股票核心指标

    参数:
        price: 当前股价（元）
        eps: 每股收益 TTM（元）
        book_value_per_share: 每股净资产（元）
        dividend_per_share: 每股年度分红（元）
        total_shares: 总股本（亿股）
        net_profit: 净利润（亿元）
        revenue: 营业收入（亿元）
        total_assets: 总资产（亿元）
        total_equity: 净资产（亿元）
    """
    metrics = {}

    # PE (市盈率)
    metrics['PE'] = price / eps if eps > 0 else None

    # PB (市净率)
    metrics['PB'] = price / book_value_per_share if book_value_per_share > 0 else None

    # ROE (净资产收益率)
    metrics['ROE'] = (net_profit / total_equity) * 100

    # 股息率
    metrics['dividend_yield'] = (dividend_per_share / price) * 100

    # 市值
    metrics['market_cap'] = price * total_shares  # 亿元

    # 净利率
    metrics['net_margin'] = (net_profit / revenue) * 100

    # 杜邦分析
    metrics['dupont_net_margin'] = net_profit / revenue  # 净利率
    metrics['dupont_asset_turnover'] = revenue / total_assets  # 总资产周转率
    metrics['dupont_equity_multiplier'] = total_assets / total_equity  # 权益乘数
    metrics['dupont_roe'] = (metrics['dupont_net_margin'] *
                              metrics['dupont_asset_turnover'] *
                              metrics['dupont_equity_multiplier'] * 100)

    return metrics


def demo_metric_calculation():
    """
    演示：用真实案例计算股票指标
    """
    print("\n" + "=" * 60)
    print("  股票核心指标计算演练")
    print("=" * 60)

    # 模拟三个典型公司
    companies = {
        '白酒龙头（类茅台）': {
            'price': 1800, 'eps': 59.5, 'book_value_per_share': 189,
            'dividend_per_share': 25.9, 'total_shares': 12.56,
            'net_profit': 747, 'revenue': 1477, 'total_assets': 2720,
            'total_equity': 2374
        },
        '大型银行（类工行）': {
            'price': 5.0, 'eps': 0.95, 'book_value_per_share': 8.5,
            'dividend_per_share': 0.30, 'total_shares': 3564,
            'net_profit': 3600, 'revenue': 8400, 'total_assets': 420000,
            'total_equity': 32000
        },
        '成长科技（类某消费电子）': {
            'price': 35, 'eps': 1.2, 'book_value_per_share': 5.8,
            'dividend_per_share': 0.15, 'total_shares': 20,
            'net_profit': 24, 'revenue': 400, 'total_assets': 280,
            'total_equity': 116
        }
    }

    for name, data in companies.items():
        m = calculate_stock_metrics(**data)
        print(f"\n{'─' * 50}")
        print(f"  {name}")
        print(f"{'─' * 50}")
        print(f"  股价: {data['price']}元")
        print(f"  市值: {m['market_cap']:.0f}亿元")
        print(f"  PE: {m['PE']:.1f}倍")
        print(f"  PB: {m['PB']:.2f}倍")
        print(f"  ROE: {m['ROE']:.1f}%")
        print(f"  股息率: {m['dividend_yield']:.2f}%")
        print(f"  净利率: {m['net_margin']:.1f}%")

        print(f"\n  杜邦分析拆解:")
        print(f"    净利率: {m['dupont_net_margin']*100:.1f}%")
        print(f"    总资产周转率: {m['dupont_asset_turnover']:.2f}次")
        print(f"    权益乘数: {m['dupont_equity_multiplier']:.2f}倍")
        print(f"    验证ROE = {m['dupont_net_margin']*100:.1f}% × "
              f"{m['dupont_asset_turnover']:.2f} × "
              f"{m['dupont_equity_multiplier']:.2f} = {m['dupont_roe']:.1f}%")

    print(f"\n{'─' * 50}")
    print("  三家公司对比分析:")
    print(f"{'─' * 50}")
    print(f"""
  ┌──────────────┬──────────┬──────────┬──────────┐
  │              │ 白酒龙头  │ 大型银行  │ 成长科技  │
  ├──────────────┼──────────┼──────────┼──────────┤
  │ PE (估值)     │  ~30倍   │  ~5倍    │  ~29倍   │
  │ ROE (赚钱能力)│  ~31%    │  ~11%    │  ~21%    │
  │ 净利率        │  ~50%+   │  ~43%    │  ~6%     │
  │ 股息率        │  ~1.4%   │  ~6%     │  ~0.4%   │
  ├──────────────┼──────────┼──────────┼──────────┤
  │ 为什么PE不同？│           │          │          │
  │ 白酒：高ROE+稳定增长 → 市场给高估值          │
  │ 银行：低增长+高杠杆+监管风险 → 市场给低估值  │
  │ 科技：中高ROE+增长预期 → 中等偏高估值        │
  └──────────────┴──────────┴──────────┴──────────┘
  """)


# ============================================================
# 2. 股价涨跌模型可视化
# ============================================================

def plot_price_drivers():
    """
    可视化：股价 = EPS × PE 的四种变化模式
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 模式A：盈利驱动
    ax = axes[0, 0]
    years = list(range(1, 11))
    eps = [1.0 * (1.15 ** (y - 1)) for y in years]  # 每年增长15%
    pe = [15] * 10  # PE不变
    price = [e * p for e, p in zip(eps, pe)]

    ax.plot(years, eps, 'b-', linewidth=2, label='EPS (每股收益)')
    ax.plot(years, pe, 'g--', linewidth=2, label='PE (市盈率)')
    ax.plot(years, price, 'r-', linewidth=3, label='股价')

    # 标注
    ax.annotate(f'EPS: {eps[-1]:.1f}', xy=(10, eps[-1]), fontsize=10, color='blue')
    ax.annotate(f'PE: {pe[-1]}', xy=(10, pe[-1]), fontsize=10, color='green')
    ax.annotate(f'股价: {price[-1]:.1f}', xy=(10, price[-1]), fontsize=10, color='red')

    ax.set_title('模式A：盈利驱动（EPS↑ PE→）✅ 健康的上涨', fontsize=12, fontweight='bold')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    ax.set_xlabel('年数')

    # 模式B：估值驱动
    ax = axes[0, 1]
    eps = [1.0] * 10  # EPS不变
    pe = [10 + 2 * (y - 1) for y in years]  # PE从10到28
    price = [e * p for e, p in zip(eps, pe)]

    ax.plot(years, eps, 'b-', linewidth=2, label='EPS (每股收益)')
    ax.plot(years, pe, 'g--', linewidth=2, label='PE (市盈率)')
    ax.plot(years, price, 'orange', linewidth=3, label='股价')

    ax.fill_between(years, price, eps, alpha=0.1, color='orange')
    ax.text(5, 17, '泡沫区域？\n盈利没变，全靠情绪', fontsize=10, color='orange', alpha=0.8,
            ha='center')

    ax.annotate(f'EPS: {eps[-1]:.1f}', xy=(10, eps[-1]), fontsize=10, color='blue')
    ax.annotate(f'PE: {pe[-1]}', xy=(10, pe[-1]), fontsize=10, color='green')
    ax.annotate(f'股价: {price[-1]:.1f}', xy=(10, price[-1]), fontsize=10, color='orange')

    ax.set_title('模式B：估值驱动（EPS→ PE↑）⚠️ 情绪驱动的上涨', fontsize=12, fontweight='bold')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    ax.set_xlabel('年数')

    # 模式C：戴维斯双击
    ax = axes[1, 0]
    eps = [1.0 * (1.2 ** (y - 1)) for y in years]  # 每年增长20%
    pe = [10 + 1 * (y - 1) for y in years]  # PE从10到19
    price = [e * p for e, p in zip(eps, pe)]

    ax.plot(years, eps, 'b-', linewidth=2, label='EPS (每股收益)')
    ax.plot(years, pe, 'g--', linewidth=2, label='PE (市盈率)')
    ax.plot(years, price, 'r-', linewidth=3, label='股价')

    ax.fill_between(years, price, [e * 10 for e in eps], alpha=0.08, color='green')
    ax.text(3, price[-1] / 2,
            '深色区域 = 估值提升贡献\n下方 = 盈利增长贡献',
            fontsize=9, color='green', alpha=0.8)

    ax.annotate(f'EPS: {eps[-1]:.2f}', xy=(10, eps[-1]), fontsize=10, color='blue')
    ax.annotate(f'PE: {pe[-1]}', xy=(10, pe[-1]), fontsize=10, color='green')
    ax.annotate(f'股价: {price[-1]:.1f}', xy=(10, price[-1]), fontsize=10, color='red')

    ax.set_title('模式C：戴维斯双击（EPS↑ PE↑）🚀 最好的情况', fontsize=12, fontweight='bold')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    ax.set_xlabel('年数')

    # 模式D：戴维斯双杀
    ax = axes[1, 1]
    eps_vals = [2.0, 1.8, 1.6, 1.3, 1.0, 0.8, 0.7, 0.6, 0.5, 0.5]
    pe_vals = [20, 18, 16, 14, 12, 10, 9, 8, 7, 6]
    price = [e * p for e, p in zip(eps_vals, pe_vals)]

    ax.plot(years, eps_vals, 'b-', linewidth=2, label='EPS (每股收益)')
    ax.plot(years, pe_vals, 'g--', linewidth=2, label='PE (市盈率)')
    ax.plot(years, price, linewidth=3, label='股价', color='darkred')

    ax.annotate(f'EPS: {eps_vals[-1]:.1f}', xy=(10, eps_vals[-1]), fontsize=10, color='blue')
    ax.annotate(f'PE: {pe_vals[-1]}', xy=(10, pe_vals[-1]), fontsize=10, color='green')
    ax.annotate(f'股价: {price[-1]:.1f}', xy=(10, price[-1]), fontsize=10, color='darkred')

    ax.set_title('模式D：戴维斯双杀（EPS↓ PE↓）💀 最惨的情况', fontsize=12, fontweight='bold')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    ax.set_xlabel('年数')

    plt.suptitle('股价 = EPS × PE：四种变化模式', fontsize=14, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.savefig(os.path.join(os.path.dirname(__file__), 'stock_price_drivers.png'),
                dpi=150, bbox_inches='tight')
    plt.close()
    print("✅ 图表已生成: stock_price_drivers.png")


# ============================================================
# 3. PE vs ROE 散点图：理解估值与盈利能力的关系
# ============================================================

def plot_pe_vs_roe():
    """
    展示PE和ROE的关系
    """
    np.random.seed(42)

    # 模拟不同行业的PE和ROE
    n = 50

    # 消费龙头：高ROE，高PE
    consumer_roe = np.random.normal(22, 5, n)
    consumer_pe = consumer_roe * 1.2 + np.random.normal(5, 5, n)

    # 银行：中低ROE，低PE
    bank_roe = np.random.normal(11, 2, n)
    bank_pe = np.random.normal(6, 2, n)

    # 科技：中ROE，高PE
    tech_roe = np.random.normal(15, 6, n)
    tech_pe = tech_roe * 1.5 + np.random.normal(10, 10, n)

    # 周期股：ROE波动大，PE波动大
    cycle_roe = np.random.normal(10, 8, n)
    cycle_pe = np.random.normal(12, 8, n)

    fig, ax = plt.subplots(figsize=(12, 7))

    ax.scatter(consumer_roe, consumer_pe, c='#E74C3C', label='消费龙头', alpha=0.6, s=60)
    ax.scatter(bank_roe, bank_pe, c='#3498DB', label='银行', alpha=0.6, s=60)
    ax.scatter(tech_roe, tech_pe, c='#2ECC71', label='科技', alpha=0.6, s=60)
    ax.scatter(cycle_roe, cycle_pe, c='#95A5A6', label='周期股', alpha=0.6, s=60)

    # 添加趋势参考线
    x_ref = np.linspace(0, 35, 100)
    ax.plot(x_ref, x_ref, 'k--', alpha=0.3, linewidth=1, label='PE=ROE (参考线)')
    ax.plot(x_ref, x_ref * 2, 'gray', alpha=0.2, linewidth=1, label='PE=2×ROE')

    ax.set_xlabel('ROE (%)', fontsize=12)
    ax.set_ylabel('PE (倍)', fontsize=12)
    ax.set_title('PE vs ROE：估值与盈利能力的行业差异', fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', frameon=True)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 40)
    ax.set_ylim(0, 60)

    # 标注
    ax.annotate('高ROE+高PE\n优质消费公司', xy=(25, 35), fontsize=9, color='#E74C3C')
    ax.annotate('低ROE+低PE\n银行', xy=(10, 6), fontsize=9, color='#3498DB')
    ax.annotate('中ROE+高PE\n科技成长', xy=(18, 35), fontsize=9, color='#2ECC71')

    plt.tight_layout()
    plt.savefig(os.path.join(os.path.dirname(__file__), 'pe_vs_roe.png'),
                dpi=150, bbox_inches='tight')
    plt.close()
    print("✅ 图表已生成: pe_vs_roe.png")


# ============================================================
# 4. 杜邦分析可视化
# ============================================================

def plot_dupont_analysis():
    """
    杜邦分析：不同公司ROE的驱动力分解
    """
    companies = ['A公司\n高端白酒', 'B公司\n大型银行', 'C公司\n零售超市',
                 'D公司\n科技硬件', 'E公司\n地产开发']
    net_margin = [50.6, 42.9, 2.5, 6.0, 8.0]  # %
    asset_turnover = [0.54, 0.02, 2.50, 1.44, 0.25]  # 次
    equity_multiplier = [1.15, 13.13, 2.50, 2.41, 5.00]  # 倍

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    colors = ['#E74C3C', '#3498DB', '#F39C12', '#2ECC71', '#9B59B6']

    metrics = [
        ('净利率 (%)', net_margin, axes[0]),
        ('总资产周转率 (次)', asset_turnover, axes[1]),
        ('权益乘数 (倍)', equity_multiplier, axes[2]),
    ]

    for title, values, ax in metrics:
        bars = ax.bar(range(len(companies)), values, color=colors, alpha=0.85)
        ax.set_title(title, fontsize=13, fontweight='bold')
        ax.set_xticks(range(len(companies)))
        ax.set_xticklabels(companies, fontsize=9)
        ax.grid(True, alpha=0.3, axis='y')

        # 在柱子上标注数值
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(values) * 0.02,
                    f'{val:.1f}', ha='center', fontsize=9, fontweight='bold')

    plt.suptitle('杜邦分析：ROE的三个驱动因素', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(os.path.dirname(__file__), 'dupont_analysis.png'),
                dpi=150, bbox_inches='tight')
    plt.close()
    print("✅ 图表已生成: dupont_analysis.png")


# ============================================================
# 5. 市值梯队可视化
# ============================================================

def plot_market_cap_tiers():
    """
    展示A股市值分布
    """
    fig, ax = plt.subplots(figsize=(12, 6))

    tiers = ['万亿俱乐部\n(>1万亿)', '千亿级\n(1000亿-1万亿)',
             '百亿级\n(100亿-1000亿)', '几十亿级\n(<100亿)']
    count = [10, 120, 1500, 3500]
    total_market_cap = [15, 25, 35, 10]  # 万亿元
    colors = ['#8E44AD', '#E74C3C', '#F39C12', '#95A5A6']

    # 双轴图
    ax1 = ax
    ax2 = ax.twinx()

    bars = ax1.bar(tiers, count, color=colors, alpha=0.7, width=0.6)
    ax2.plot(tiers, total_market_cap, 'ko-', linewidth=2, markersize=10, label='总市值(万亿)')

    ax1.set_ylabel('公司数量（家）', fontsize=12)
    ax2.set_ylabel('总市值（万亿元）', fontsize=12)
    ax1.set_title('A股市值分布（约5000家上市公司）', fontsize=14, fontweight='bold')

    for bar, c in zip(bars, count):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 50,
                 f'{c}家\n{bar.get_height()/sum(count)*100:.1f}%',
                 ha='center', fontsize=10)

    for i, (tier, cap) in enumerate(zip(tiers, total_market_cap)):
        ax2.annotate(f'{cap}万亿', xy=(i, cap), fontsize=9, fontweight='bold',
                     ha='center', va='bottom')

    ax1.grid(True, alpha=0.3, axis='y')
    ax2.legend(loc='upper right')

    plt.tight_layout()
    plt.savefig(os.path.join(os.path.dirname(__file__), 'market_cap_tiers.png'),
                dpi=150, bbox_inches='tight')
    plt.close()
    print("✅ 图表已生成: market_cap_tiers.png")


# ============================================================
# 6. 尝试获取真实数据（需要 akshare）
# ============================================================

def fetch_real_stock_data():
    """
    尝试使用 akshare 获取真实A股数据
    如果没有安装 akshare，跳过
    """
    try:
        import akshare as ak
        print("\n✅ akshare 已安装，正在获取真实数据...")

        # 获取A股实时行情
        spot_df = ak.stock_zh_a_spot_em()
        print(f"\n  A股实时行情：共获取 {len(spot_df)} 只股票数据")

        # 市值TOP10
        top10 = spot_df.nlargest(10, '总市值')
        print(f"\n  📊 A股市值TOP10:")
        print(f"  {'代码':<10} {'名称':<10} {'股价':<10} {'总市值(亿)':<15} {'PE':<10}")
        print(f"  {'-'*55}")
        for _, row in top10.iterrows():
            code = row.get('代码', 'N/A')
            name = row.get('名称', 'N/A')
            price = row.get('最新价', 'N/A')
            mcap = row.get('总市值', 0) / 1e8 if row.get('总市值') else 'N/A'
            pe = row.get('市盈率-动态', 'N/A')
            print(f"  {code:<10} {name:<10} {str(price):<10} "
                  f"{f'{mcap:.0f}亿' if isinstance(mcap, (int, float)) else str(mcap):<15} "
                  f"{str(pe):<10}")

        # 高ROE筛选（用PE作为代理，需要财务数据会更准）
        # 筛选正PE的公司中PE最低的（可能是价值股）
        positive_pe = spot_df[spot_df['市盈率-动态'].apply(
            lambda x: isinstance(x, (int, float)) and 0 < x < 15
        )]
        print(f"\n  📊 PE在0-15倍的公司数量: {len(positive_pe)}")
        print(f"  (通常代表价值股/低估值公司)")

        return spot_df

    except ImportError:
        print("\n⚠️  akshare 未安装。跳过了真实数据获取。")
        print("  如需使用，请运行: pip install akshare")
        return None
    except Exception as e:
        print(f"\n⚠️  获取数据时出错: {e}")
        return None


# ============================================================
# 7. 固定数据演示（不需要网络也能跑）
# ============================================================

def demo_with_static_data():
    """
    使用静态示例数据演示，不需要网络
    """
    print("\n" + "=" * 60)
    print("  示例公司数据演示（静态数据）")
    print("=" * 60)

    sample_stocks = [
        {'名称': '贵州茅台', '代码': '600519', '行业': '白酒',
         '股价': 1680, '市值': 21100, 'PE': 28.3, 'PB': 8.9, 'ROE': 31.2, '股息率': 1.5},
        {'名称': '招商银行', '代码': '600036', '行业': '银行',
         '股价': 38, '市值': 9600, 'PE': 6.2, 'PB': 0.95, 'ROE': 14.8, '股息率': 5.2},
        {'名称': '比亚迪', '代码': '002594', '行业': '新能源车',
         '股价': 265, '市值': 7200, 'PE': 35.8, 'PB': 5.6, 'ROE': 18.5, '股息率': 0.3},
        {'名称': '美的集团', '代码': '000333', '行业': '家电',
         '股价': 72, '市值': 5100, 'PE': 14.5, 'PB': 3.2, 'ROE': 22.1, '股息率': 3.8},
        {'名称': '海康威视', '代码': '002415', '行业': '安防',
         '股价': 35, '市值': 3300, 'PE': 22.0, 'PB': 4.5, 'ROE': 19.8, '股息率': 2.1},
        {'名称': '恒瑞医药', '代码': '600276', '行业': '医药',
         '股价': 48, '市值': 3100, 'PE': 55.0, 'PB': 6.8, 'ROE': 12.5, '股息率': 0.4},
        {'名称': '中国神华', '代码': '601088', '行业': '煤炭',
         '股价': 42, '市值': 8300, 'PE': 10.5, 'PB': 1.6, 'ROE': 15.2, '股息率': 6.5},
        {'名称': '长江电力', '代码': '600900', '行业': '电力',
         '股价': 29, '市值': 7100, 'PE': 20.0, 'PB': 3.2, 'ROE': 16.0, '股息率': 3.2},
    ]

    print(f"\n  {'名称':<10} {'代码':<8} {'PE':<8} {'PB':<8} {'ROE':<8} {'股息率':<8}  {'特征'}")
    print(f"  {'-'*70}")

    for s in sample_stocks:
        # 判断特征
        features = []
        if s['PE'] < 10:
            features.append('低PE')
        elif s['PE'] > 40:
            features.append('高PE')

        if s['ROE'] > 25:
            features.append('高ROE')
        elif s['ROE'] > 15:
            features.append('中高ROE')

        if s['股息率'] > 4:
            features.append('高股息')
        elif s['股息率'] > 2:
            features.append('中股息')

        feature_str = ' | '.join(features) if features else '一般'
        print(f"  {s['名称']:<10} {s['代码']:<8} {s['PE']:<8.1f} {s['PB']:<8.2f} "
              f"{s['ROE']:<8.1f} {s['股息率']:<8.1f} {feature_str}")

    # 分类讨论
    print(f"\n  📊 分类分析:")
    print(f"  {'─'*50}")
    print(f"  低PE(价值型): 招商银行(6.2)、中国神华(10.5)、美的(14.5)")
    print(f"    → 市场对这些公司的增长预期较低")
    print(f"    → 但它们的ROE并不差（都在14%+）")
    print(f"    → 适合追求稳定+分红的价值投资者")
    print()
    print(f"  高PE(成长型): 恒瑞医药(55)、比亚迪(35.8)")
    print(f"    → 市场预期它们未来增长很高")
    print(f"    → 但一旦增长不达预期，股价可能大跌")
    print(f"    → 需要深入研究才能判断高PE是否合理")
    print()
    print(f"  高ROE(优质): 茅台(31.2%)、美的(22.1%)、海康(19.8%)")
    print(f"    → 巴菲特最看重的指标")
    print(f"    → 长期高ROE意味着持久的竞争优势")
    print()
    print(f"  高股息(分红型): 中国神华(6.5%)、招商银行(5.2%)、美的(3.8%)")
    print(f"    → 适合需要现金流收入的投资者")
    print(f"    → 需要判断分红是否可持续")

    return sample_stocks


if __name__ == '__main__':
    print("=" * 60)
    print("  第二课实战代码：股票基础")
    print("=" * 60)

    # 1. 股票指标计算
    demo_metric_calculation()

    # 2. 股价涨跌模型图
    print("\n📊 生成股价涨跌模型图...")
    plot_price_drivers()

    # 3. PE vs ROE 散点图
    print("\n📊 生成PE vs ROE图...")
    plot_pe_vs_roe()

    # 4. 杜邦分析图
    print("\n📊 生成杜邦分析图...")
    plot_dupont_analysis()

    # 5. 市值梯队图
    print("\n📊 生成市值梯队图...")
    plot_market_cap_tiers()

    # 6. 静态数据演示（不需要网络）
    sample_data = demo_with_static_data()

    # 7. 尝试获取真实数据
    print("\n" + "=" * 60)
    real_data = fetch_real_stock_data()

    print("\n✅ 所有计算完成！请查看生成的PNG图表文件。")
    print("\n📝 动手练习：")
    print("  1. 打开交易软件/App，查看茅台(600519)的真实数据")
    print("  2. 和本代码中的示例数据对比")
    print("  3. 找3家你感兴趣的公司，记录它们的PE/PB/ROE")
    print("  4. 用股价=EPS×PE的框架，分析它们的上涨驱动力")
    print("  5. 如果安装了akshare，运行 fetch_real_stock_data() 获取实时数据")
