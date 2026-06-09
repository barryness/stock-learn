"""
第三课配套实战代码：三大市场分析 + 股票分类
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


# ============================================================
# 1. A股四大板块对比
# ============================================================

def plot_a_share_markets():
    """A股四大板块可视化对比"""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    boards = ['主板', '创业板', '科创板', '北交所']
    companies_count = [3200, 1300, 570, 240]
    avg_market_cap = [350, 120, 80, 8]  # 平均市值（亿）
    daily_volatility = [2.5, 4.5, 5.0, 6.5]  # 日均波动率(%)
    threshold = [0, 10, 50, 50]  # 投资门槛（万）
    colors = ['#3498DB', '#E74C3C', '#2ECC71', '#F39C12']

    # 图1：公司数量
    ax = axes[0, 0]
    bars = ax.bar(boards, companies_count, color=colors, alpha=0.85)
    ax.set_title('各板块上市公司数量', fontsize=12, fontweight='bold')
    ax.set_ylabel('公司数量（家）')
    for bar, val in zip(bars, companies_count):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 30,
                f'{val}家', ha='center', fontweight='bold')

    # 图2：平均市值
    ax = axes[0, 1]
    bars = ax.bar(boards, avg_market_cap, color=colors, alpha=0.85)
    ax.set_title('各板块公司平均市值', fontsize=12, fontweight='bold')
    ax.set_ylabel('平均市值（亿元）')
    for bar, val in zip(bars, avg_market_cap):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                f'{val}亿', ha='center', fontweight='bold')

    # 图3：日均波动率
    ax = axes[1, 0]
    bars = ax.bar(boards, daily_volatility, color=colors, alpha=0.85)
    ax.set_title('各板块日均波动率', fontsize=12, fontweight='bold')
    ax.set_ylabel('日均波动率（%）')
    ax.axhline(y=3, color='gray', linestyle='--', alpha=0.5, label='主板波动参考线')
    for bar, val in zip(bars, daily_volatility):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                f'{val}%', ha='center', fontweight='bold')
    ax.legend()

    # 图4：投资门槛
    ax = axes[1, 1]
    bars = ax.bar(boards, threshold, color=colors, alpha=0.85)
    ax.set_title('各板块投资门槛', fontsize=12, fontweight='bold')
    ax.set_ylabel('最低资产要求（万元）')
    for bar, val in zip(bars, threshold):
        label = '无门槛' if val == 0 else f'{val}万'
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                label, ha='center', fontweight='bold')

    plt.suptitle('A股四大板块全面对比', fontsize=14, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.savefig(os.path.join(os.path.dirname(__file__), 'a_share_markets.png'),
                dpi=150, bbox_inches='tight')
    plt.close()
    print("✅ 图表已生成: a_share_markets.png")


# ============================================================
# 2. 三大市场估值对比
# ============================================================

def plot_global_markets_comparison():
    """三大市场对比"""
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    # 数据
    markets = ['A股\n(沪深300)', '港股\n(恒生指数)', '美股\n(标普500)']
    pe_values = [12.5, 9.0, 22.0]
    pb_values = [1.35, 0.95, 4.5]
    dividend_yield = [2.8, 4.2, 1.4]

    colors_market = ['#E74C3C', '#3498DB', '#2ECC71']

    metrics = [
        ('PE (市盈率)', pe_values, '倍'),
        ('PB (市净率)', pb_values, '倍'),
        ('股息率', dividend_yield, '%'),
    ]

    for idx, (title, values, unit) in enumerate(metrics):
        ax = axes[idx]
        bars = ax.bar(markets, values, color=colors_market, alpha=0.85)

        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values)*0.03,
                    f'{val}{unit}', ha='center', fontsize=12, fontweight='bold')

        ax.set_title(title, fontsize=13, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')

        # 高亮港股的低估值
        if title == 'PE (市盈率)':
            ax.annotate('全球最低估值\n主要市场之一',
                       xy=(1, pe_values[1]), fontsize=9,
                       ha='center', color='#3498DB',
                       xytext=(1, pe_values[1] + 2))
        elif title == '股息率':
            ax.annotate('高股息机会多',
                       xy=(1, dividend_yield[1]), fontsize=9,
                       ha='center', color='#3498DB')

    plt.suptitle('A股 / 港股 / 美股 核心指标对比', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(os.path.dirname(__file__), 'global_markets.png'),
                dpi=150, bbox_inches='tight')
    plt.close()
    print("✅ 图表已生成: global_markets.png")


# ============================================================
# 3. AH股溢价演示
# ============================================================

def demo_ah_premium():
    """演示AH股溢价"""
    print("\n" + "=" * 60)
    print("  AH股溢价演示（同一家公司，A股和H股价差）")
    print("=" * 60)

    # 示例数据（近似，实际数据会变化）
    ah_stocks = [
        {'name': '工商银行', 'a_code': '601398', 'h_code': '01398',
         'a_price': 5.50, 'h_price_hkd': 5.20},
        {'name': '中国平安', 'a_code': '601318', 'h_code': '02318',
         'a_price': 45.00, 'h_price_hkd': 38.00},
        {'name': '比亚迪', 'a_code': '002594', 'h_code': '01211',
         'a_price': 265.00, 'h_price_hkd': 220.00},
        {'name': '招商银行', 'a_code': '600036', 'h_code': '03968',
         'a_price': 38.00, 'h_price_hkd': 35.50},
        {'name': '中国神华', 'a_code': '601088', 'h_code': '01088',
         'a_price': 42.00, 'h_price_hkd': 30.00},
        {'name': '中芯国际', 'a_code': '688981', 'h_code': '00981',
         'a_price': 55.00, 'h_price_hkd': 18.00},
    ]

    # 假设港币汇率
    hkd_cny_rate = 0.915

    print(f"\n  {'名称':<10} {'A股价':<10} {'H股(港币)':<12} "
          f"{'H股(人民币)':<14} {'AH溢价率':<12} {'评价'}")
    print(f"  {'-'*70}")

    for s in ah_stocks:
        h_price_cny = s['h_price_hkd'] * hkd_cny_rate
        premium = (s['a_price'] / h_price_cny - 1) * 100  # AH溢价率

        if premium < 10:
            comment = '基本平价'
        elif premium < 30:
            comment = 'A股略贵'
        elif premium < 60:
            comment = 'A股明显更贵'
        else:
            comment = 'A股贵很多！'

        print(f"  {s['name']:<10} {s['a_price']:<10.2f} {s['h_price_hkd']:<12.2f} "
              f"{h_price_cny:<14.2f} {premium:<12.1f}% {comment}")

    print(f"\n  💡 AH溢价率 = (A股价 ÷ H股折算人民币价 - 1) × 100%")
    print(f"  💡 港币汇率假设: 1港币 = {hkd_cny_rate}人民币")
    print(f"  💡 当AH溢价率 > 130% + 时，H股相对便宜很多")
    print(f"  💡 但也意味着：不能简单因为H股便宜就买入")
    print(f"     （港股有流动性、汇率等额外风险）")

    return ah_stocks


# ============================================================
# 4. 股票类型分类器
# ============================================================

def classify_stock(pe, roe, dividend_yield, revenue_growth, industry):
    """
    根据指标对股票进行分类

    参数:
        pe: 市盈率
        roe: 净资产收益率(%)
        dividend_yield: 股息率(%)
        revenue_growth: 营收增长率(%)
        industry: 所属行业
    """
    types = []

    # 龙头股：高ROE + 行业头部公司（简化条件）
    if roe > 18:
        types.append('龙头')

    # 成长股：高增长
    if revenue_growth > 15:
        types.append('成长')

    # 价值股：低PE
    if pe > 0 and pe < 12:
        types.append('价值')

    # 红利股：高股息
    if dividend_yield > 4:
        types.append('红利')

    # 周期股行业
    cyclical_industries = ['有色', '煤炭', '钢铁', '化工', '航运', '券商', '猪肉']
    if any(c in industry for c in cyclical_industries):
        types.append('周期')

    if not types:
        types.append('一般')

    return types


def demo_stock_classification():
    """演示股票分类"""
    print("\n" + "=" * 60)
    print("  股票分类器：根据指标判断股票类型")
    print("=" * 60)

    stocks_to_classify = [
        {'name': '贵州茅台', 'pe': 28, 'roe': 31, 'div': 1.5, 'growth': 16, 'ind': '白酒'},
        {'name': '工商银行', 'pe': 5.5, 'roe': 11, 'div': 6.0, 'growth': 2, 'ind': '银行'},
        {'name': '宁德时代', 'pe': 35, 'roe': 22, 'div': 0.5, 'growth': 35, 'ind': '新能源'},
        {'name': '中国神华', 'pe': 10, 'roe': 15, 'div': 6.5, 'growth': -5, 'ind': '煤炭'},
        {'name': '某AI概念股', 'pe': 150, 'roe': 5, 'div': 0, 'growth': 60, 'ind': '软件'},
        {'name': '某航运公司', 'pe': 4, 'roe': 25, 'div': 2.0, 'growth': -40, 'ind': '航运'},
        {'name': '长江电力', 'pe': 20, 'roe': 16, 'div': 3.2, 'growth': 8, 'ind': '电力'},
        {'name': '宝钢股份', 'pe': 8, 'roe': 7, 'div': 4.5, 'growth': -3, 'ind': '钢铁'},
    ]

    print(f"\n  {'名称':<10} {'PE':<8} {'ROE':<8} {'股息率':<8} {'增长':<8} {'行业':<8} → {'分类结果'}")
    print(f"  {'-'*75}")

    for s in stocks_to_classify:
        types = classify_stock(s['pe'], s['roe'], s['div'], s['growth'], s['ind'])
        type_str = ' + '.join(types)
        print(f"  {s['name']:<10} {s['pe']:<8.1f} {s['roe']:<8.1f}% "
              f"{s['div']:<8.1f}% {s['growth']:<8.1f}% {s['ind']:<8} → {type_str}")

    print(f"\n  📊 分类逻辑说明:")
    print(f"  ┌──────────┬────────────────────────────┐")
    print(f"  │ 龙头      │ ROE > 18%                   │")
    print(f"  │ 成长      │ 营收增长 > 15%              │")
    print(f"  │ 价值      │ PE在0-12之间                │")
    print(f"  │ 红利      │ 股息率 > 4%                 │")
    print(f"  │ 周期      │ 行业属周期类               │")
    print(f"  └──────────┴────────────────────────────┘")
    print(f"  💡 一只股票可以同时属于多个类型")
    print(f"     例：中国神华 = 价值 + 红利 + 周期")
    print(f"     例：宁德时代 = 龙头 + 成长")


# ============================================================
# 5. 公司行为时间线模拟
# ============================================================

def demo_corporate_actions():
    """演示公司资本行为对股东的影响"""
    print("\n" + "=" * 60)
    print("  公司行为对股东权益的影响模拟")
    print("=" * 60)

    # 模拟一家公司
    initial_price = 20.0
    initial_shares = 1000  # 你持有的股数
    total_shares = 10_000_000_000  # 总股本100亿股

    print(f"\n  初始状态:")
    print(f"  股价: {initial_price}元, 你持有: {initial_shares}股")
    print(f"  你的持仓市值: {initial_price * initial_shares:,.0f}元")
    print(f"  总股本: {total_shares/1e8:.0f}亿股")
    print(f"  你的持股比例: {initial_shares/total_shares*100:.8f}%")

    # 场景1：分红
    print(f"\n  ┌─ 场景1：每股分红0.5元 ─────────────────────┐")
    dividend = 0.5
    cash_received = dividend * initial_shares
    price_after_div = initial_price - dividend
    print(f"  │ 除权后股价: {initial_price} → {price_after_div}元")
    print(f"  │ 你收到现金: {cash_received:,.0f}元")
    print(f"  │ 你的总资产: 股票{price_after_div*initial_shares:,.0f} + 现金{cash_received:,.0f}")
    print(f"  │            = {price_after_div*initial_shares + cash_received:,.0f}元 (和分红前一样)")
    print(f"  │ 💡 分红只是把一部分股票价值变成了现金")
    print(f"  └──────────────────────────────────────────────┘")

    # 场景2：回购
    print(f"\n  ┌─ 场景2：公司回购注销1亿股 ───────────────┐")
    buyback_shares = 100_000_000  # 回购1亿股
    new_total_shares = total_shares - buyback_shares
    ownership_change = (initial_shares / new_total_shares - initial_shares / total_shares) * 100
    print(f"  │ 总股本: {total_shares/1e8:.0f}亿 → {new_total_shares/1e8:.1f}亿")
    print(f"  │ 你的持股比例: {initial_shares/total_shares*100:.8f}%")
    print(f"  │             → {initial_shares/new_total_shares*100:.8f}%")
    print(f"  │ 每股收益自动提高 (同样的利润 ÷ 更少的股本)")
    print(f"  │ 💡 回购提升每股价值，且不用交红利税")
    print(f"  └──────────────────────────────────────────────┘")

    # 场景3：增发
    print(f"\n  ┌─ 场景3：公司增发2亿股 ───────────────────┐")
    issuance = 200_000_000
    new_total = total_shares + issuance
    dilution = (initial_shares / total_shares - initial_shares / new_total) * 100
    print(f"  │ 总股本: {total_shares/1e8:.0f}亿 → {new_total/1e8:.0f}亿")
    print(f"  │ 你的持股比例: {initial_shares/total_shares*100:.8f}%")
    print(f"  │             → {initial_shares/new_total*100:.8f}%")
    print(f"  │ 被稀释了: {dilution*100:.6f}个百分点")
    print(f"  │ ⚠️  增发稀释现有股东的权益")
    print(f"  │ ✅ 但如果募资用于好项目，长期可能增值")
    print(f"  └──────────────────────────────────────────────┘")

    # 场景4：解禁
    print(f"\n  ┌─ 场景4：大股东限售股解禁1亿股 ───────────┐")
    unlock_shares = 100_000_000
    unlock_pct = unlock_shares / total_shares * 100
    print(f"  │ 解禁数量: {unlock_shares/1e8:.1f}亿股")
    print(f"  │ 占总股本: {unlock_pct:.2f}%")
    print(f"  │ 大股东成本: 可能只有当前股价的10-20%")
    print(f"  │ ⚠️  如果大股东抛售 → 股价承压")
    print(f"  │ ✅ 如果大股东不卖且承诺不减持 → 利好信号")
    print(f"  │ 💡 关键不是解禁本身，而是大股东是否真的减持")
    print(f"  └──────────────────────────────────────────────┘")


# ============================================================
# 6. 投资者市场选择决策树
# ============================================================

def investment_decision_tree():
    """根据投资者画像推荐市场配置"""
    print("\n" + "=" * 60)
    print("  投资市场选择决策")
    print("=" * 60)

    profiles = [
        {
            'name': '小明（25岁，激进型）',
            'monthly': 3000, 'risk': '高', 'goal': '长期增值',
            'knowledge': '初级', 'time_horizon': '30年+'
        },
        {
            'name': '老张（40岁，稳健型）',
            'monthly': 10000, 'risk': '中', 'goal': '稳健增长+分红',
            'knowledge': '中级', 'time_horizon': '15年+'
        },
        {
            'name': '李阿姨（55岁，保守型）',
            'monthly': 5000, 'risk': '低', 'goal': '保值+稳定现金流',
            'knowledge': '初级', 'time_horizon': '10年+'
        },
    ]

    for p in profiles:
        print(f"\n  {'─'*50}")
        print(f"  {p['name']}")
        print(f"  {'─'*50}")

        if p['risk'] == '高' and p['time_horizon'] == '30年+':
            print(f"  推荐配置:")
            print(f"    美股(纳指100 ETF):  40%  — 全球最强科技公司，长期增长")
            print(f"    A股(沪深300 ETF):   30%  — 中国核心资产")
            print(f"    港股(恒生科技 ETF): 20%  — 互联网巨头，估值修复机会")
            print(f"    A股(科创50 ETF):    10%  — 高成长硬科技")
            print(f"  理由: 年轻+时间长 → 可以承受高波动 → 重仓权益类")

        elif p['risk'] == '中':
            print(f"  推荐配置:")
            print(f"    A股(沪深300 ETF):     35%  — 中国核心资产")
            print(f"    美股(标普500 ETF):    30%  — 全球配置")
            print(f"    A股(红利低波 ETF):    20%  — 稳定分红")
            print(f"    港股(恒生高股息 ETF): 15%  — 高股息补充")
            print(f"  理由: 中年稳健 → 增长+分红并重 → 攻守兼备")

        else:
            print(f"  推荐配置:")
            print(f"    A股(红利低波 ETF):    40%  — 稳定分红现金流")
            print(f"    债券基金:              30%  — 降低波动")
            print(f"    美股(标普500 ETF):    15%  — 少量全球化配置")
            print(f"    货币基金:              15%  — 流动性储备")
            print(f"  理由: 临近退休 → 保值+现金流为王 → 防御为主")


if __name__ == '__main__':
    print("=" * 60)
    print("  第三课实战代码：三大市场 + 股票分类")
    print("=" * 60)

    # 1. A股板块对比图
    print("\n📊 生成A股板块对比图...")
    plot_a_share_markets()

    # 2. 三大市场估值对比图
    print("\n📊 生成三大市场对比图...")
    plot_global_markets_comparison()

    # 3. AH股溢价演示
    demo_ah_premium()

    # 4. 股票分类器
    demo_stock_classification()

    # 5. 公司行为模拟
    demo_corporate_actions()

    # 6. 投资决策树
    investment_decision_tree()

    print("\n" + "=" * 60)
    print("✅ 所有分析完成！")
    print("\n📝 课后练习提示：")
    print("  1. 在App中找3家A+H两地上市的公司，计算AH溢价率")
    print("  2. 对你关注池的10只股票进行分类（龙头/成长/价值/红利/周期）")
    print("  3. 找一只你持有的/想买的股票，查看它的解禁日程")
    print("  4. 根据你的年龄和风险偏好，用决策树给自己设计配置方案")
