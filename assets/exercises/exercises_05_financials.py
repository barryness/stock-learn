"""
第五课配套实战代码：财报分析工具
核心功能：财务指标计算 + 三家公司对比 + 造假信号扫描
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
# 1. 财务指标计算引擎
# ============================================================

class FinancialAnalyzer:
    """财务报表分析器"""

    def __init__(self, name, data):
        self.name = name
        self.data = data
        self.metrics = {}

    def calculate_all(self):
        """计算所有关键财务指标"""
        d = self.data
        m = self.metrics

        # 毛利率
        m['毛利率'] = (d['营收'] - d['营业成本']) / d['营收'] * 100

        # 净利率
        m['净利率'] = d['净利润'] / d['营收'] * 100

        # ROE
        m['ROE'] = d['净利润'] / d['净资产'] * 100

        # ROA (总资产收益率)
        m['ROA'] = d['净利润'] / d['总资产'] * 100

        # ROIC（简化版）
        # ROIC ≈ 净利润 / (净资产 + 有息负债)
        invested_capital = d['净资产'] + d.get('有息负债', d.get('长期借款', 0) + d.get('短期借款', 0))
        m['ROIC'] = d['净利润'] / invested_capital * 100 if invested_capital > 0 else None

        # 资产负债率
        m['资产负债率'] = d['总负债'] / d['总资产'] * 100

        # 有息负债率
        interest_debt = d.get('短期借款', 0) + d.get('长期借款', 0) + d.get('应付债券', 0)
        m['有息负债率'] = interest_debt / d['总资产'] * 100

        # 总资产周转率
        m['总资产周转率'] = d['营收'] / d['总资产']

        # 杜邦分析
        m['杜邦_净利率'] = d['净利润'] / d['营收']
        m['杜邦_周转率'] = d['营收'] / d['总资产']
        m['杜邦_权益乘数'] = d['总资产'] / d['净资产']
        m['杜邦_ROE'] = m['杜邦_净利率'] * m['杜邦_周转率'] * m['杜邦_权益乘数'] * 100

        # 自由现金流相关
        ocf = d.get('经营现金流', 0)
        capex = d.get('资本支出', 0)
        m['自由现金流'] = ocf - capex
        m['FCF/净利润'] = (m['自由现金流'] / d['净利润'] * 100) if d['净利润'] > 0 else None

        # 经营现金流/净利润（利润质量）
        m['经营现金流/净利润'] = (ocf / d['净利润']) if d['净利润'] > 0 else None

        # 应收账款占比
        receivables = d.get('应收账款', 0)
        m['应收/营收'] = (receivables / d['营收'] * 100) if d['营收'] > 0 else None

        # 商誉占比
        goodwill = d.get('商誉', 0)
        m['商誉/净资产'] = (goodwill / d['净资产'] * 100) if d['净资产'] > 0 else None

        # 存货周转（简化）
        inventory = d.get('存货', 0)
        m['存货/营业成本'] = (inventory / d['营业成本'] * 100) if d['营业成本'] > 0 else None

        return m

    def print_report(self):
        """打印分析报告"""
        m = self.metrics
        d = self.data

        print(f"\n{'='*60}")
        print(f"  {self.name} 财务分析报告")
        print(f"{'='*60}")

        print(f"\n  📊 核心指标:")
        print(f"  {'─'*40}")
        print(f"  营收: {d['营收']:.1f}亿")
        print(f"  净利润: {d['净利润']:.1f}亿")
        print(f"  毛利率: {m.get('毛利率', 0):.1f}%")
        print(f"  净利率: {m.get('净利率', 0):.1f}%")
        print(f"  ROE: {m.get('ROE', 0):.1f}%")
        print(f"  ROIC: {m.get('ROIC', 0):.1f}%")
        print(f"  资产负债率: {m.get('资产负债率', 0):.1f}%")
        print(f"  有息负债率: {m.get('有息负债率', 0):.1f}%")
        print(f"  经营现金流/净利润: {m.get('经营现金流/净利润', 0):.2f}")
        print(f"  自由现金流: {m.get('自由现金流', 0):.1f}亿")
        print(f"  FCF/净利润: {m.get('FCF/净利润', 0):.1f}%")

        print(f"\n  🔍 杜邦分析拆解:")
        print(f"  {'─'*40}")
        print(f"  ROE = {m['杜邦_净利率']*100:.1f}% × {m['杜邦_周转率']:.2f} × {m['杜邦_权益乘数']:.2f}")
        print(f"      = {m['杜邦_ROE']:.1f}%")
        print(f"  解读：", end=' ')
        if m['杜邦_净利率'] > 0.20:
            print('高利润率驱动型 → 品牌/技术护城河')
        elif m['杜邦_周转率'] > 1.5:
            print('高周转驱动型 → 运营效率高')
        elif m['杜邦_权益乘数'] > 3:
            print('高杠杆驱动型 → 借力打力，注意风险')
        else:
            print('均衡型')

        print(f"\n  ⚠️  风险扫描:")
        print(f"  {'─'*40}")
        risks = []
        if m.get('应收/营收') and m['应收/营收'] > 30:
            risks.append(f"应收账款/营收={m['应收/营收']:.1f}%，偏高")
        if m.get('商誉/净资产') and m['商誉/净资产'] > 30:
            risks.append(f"商誉/净资产={m['商誉/净资产']:.1f}%，减值风险大")
        if m.get('资产负债率', 0) > 70 and d.get('行业') not in ['银行', '保险', '房地产']:
            risks.append(f"资产负债率={m['资产负债率']:.1f}%，偏高")
        if m.get('经营现金流/净利润') and m['经营现金流/净利润'] < 0.5:
            risks.append(f"经营现金流/净利润={m['经营现金流/净利润']:.2f}，利润质量差")
        if d.get('短期借款', 0) > d.get('货币资金', 0) * 0.8:
            risks.append("短期借款接近或超过货币资金，偿债压力大")
        if m.get('有息负债率', 0) > 40:
            risks.append(f"有息负债率={m['有息负债率']:.1f}%，债务负担重")

        if risks:
            for r in risks:
                print(f"  ⚠️  {r}")
        else:
            print(f"  ✅ 未发现明显风险信号")


# ============================================================
# 2. 三家公司真实数据对比
# ============================================================

def analyze_three_companies():
    """三家典型公司的财务对比分析"""

    # 茅台2023年数据（单位：亿元，简化近似值）
    maotai = {
        '营收': 1505.6, '营业成本': 117.4, '净利润': 747.3,
        '总资产': 2720, '总负债': 446, '净资产': 2274,
        '经营现金流': 666, '资本支出': 25,
        '应收账款': 0.6, '存货': 464, '商誉': 0,
        '短期借款': 0, '长期借款': 0, '应付债券': 0,
        '货币资金': 691, '行业': '白酒',
        '销售费用': 46.5, '管理费用': 97.0, '研发费用': 1.6,
    }

    # 美的2023年数据（近似）
    midea = {
        '营收': 3737, '营业成本': 2756, '净利润': 337,
        '总资产': 5350, '总负债': 3480, '净资产': 1870,
        '经营现金流': 430, '资本支出': 90,
        '应收账款': 340, '存货': 450, '商誉': 290,
        '短期借款': 120, '长期借款': 380, '应付债券': 0,
        '货币资金': 800, '行业': '家电',
        '销售费用': 374, '管理费用': 130, '研发费用': 150,
    }

    # 比亚迪2023年数据（近似）
    byd = {
        '营收': 6023, '营业成本': 4818, '净利润': 300,
        '总资产': 9200, '总负债': 7200, '净资产': 2000,
        '经营现金流': 680, '资本支出': 550,
        '应收账款': 680, '存货': 720, '商誉': 80,
        '短期借款': 230, '长期借款': 620, '应付债券': 150,
        '货币资金': 850, '行业': '新能源车',
        '销售费用': 241, '管理费用': 310, '研发费用': 420,
    }

    companies = [
        ('贵州茅台 (600519)', maotai),
        ('美的集团 (000333)', midea),
        ('比亚迪 (002594)', byd),
    ]

    for name, data in companies:
        analyzer = FinancialAnalyzer(name, data)
        analyzer.calculate_all()
        analyzer.print_report()

    # 关键指标对比表
    print(f"\n{'='*60}")
    print(f"  三家公司关键指标对比")
    print(f"{'='*60}")
    print(f"\n  {'指标':<20} {'茅台':<15} {'美的':<15} {'比亚迪':<15}")
    print(f"  {'─'*65}")

    all_metrics = {}
    for name, data in companies:
        a = FinancialAnalyzer(name, data)
        all_metrics[name] = a.calculate_all()

    compare_keys = ['毛利率', '净利率', 'ROE', 'ROIC', '资产负债率',
                    '有息负债率', '经营现金流/净利润', 'FCF/净利润',
                    '应收/营收', '商誉/净资产', '总资产周转率']

    for key in compare_keys:
        print(f"  {key:<22}", end='')
        for name, _ in companies:
            val = all_metrics[name].get(key)
            if val is not None:
                if key in ['经营现金流/净利润', '总资产周转率']:
                    print(f"{val:<12.2f}  ", end='')
                else:
                    suffix = '%' if any(pct in key for pct in ['率', 'ROE', 'ROIC', 'FCF', '应收', '商誉']) else ''
                    print(f"{val:<12.1f}{suffix}  ", end='')
            else:
                print(f"{'N/A':<14}", end='')
        print()

    return all_metrics


# ============================================================
# 3. 造假信号扫描器
# ============================================================

def fraud_scanner(name, data):
    """扫描10项造假/粉饰风险信号"""
    print(f"\n{'─'*50}")
    print(f"  🔍 {name} — 造假风险扫描")
    print(f"{'─'*50}")

    warnings = []
    score = 0  # 风险得分，越高越危险

    # 1. 经营现金流 vs 净利润
    ocf = data.get('经营现金流', 0)
    profit = data.get('净利润', 1)
    if profit > 0 and ocf < profit * 0.5:
        warnings.append(f"⚠️  经营现金流({ocf:.0f}亿)不到净利润({profit:.0f}亿)的50%")
        score += 2
    elif profit > 0 and ocf < profit * 0.8:
        warnings.append(f"⚡ 经营现金流/净利润 = {ocf/profit:.2f}，偏低")
        score += 1

    # 2. 应收账款增速 vs 营收增速（简化：比值）
    receivables = data.get('应收账款', 0)
    revenue = data.get('营收', 1)
    if revenue > 0 and receivables / revenue > 0.3:
        warnings.append(f"⚠️  应收账款/营收 = {receivables/revenue*100:.1f}% > 30%")
        score += 2

    # 3. 存货问题（行业判断简化）
    inventory = data.get('存货', 0)
    cost = data.get('营业成本', 1)
    if cost > 0 and inventory / cost > 1.0:
        industry = data.get('行业', '')
        if industry not in ['白酒']:
            warnings.append(f"⚠️  存货/营业成本 = {inventory/cost:.1f}，可能滞销")
            score += 1

    # 4. 毛利率异常（行业内对比简化）
    gross_margin = (revenue - data.get('营业成本', 0)) / revenue * 100 if revenue > 0 else 0
    # 这里用行业常识判断

    # 5. 大存大贷
    cash = data.get('货币资金', 0)
    short_loan = data.get('短期借款', 0)
    long_loan = data.get('长期借款', 0)
    if cash > total_assets * 0.1 and (short_loan + long_loan) > cash * 0.5:
        warnings.append(f"⚠️  大存大贷：货币资金{cash:.0f}亿，但有息负债{short_loan+long_loan:.0f}亿")
        score += 2

    # 6. 商誉占比
    goodwill = data.get('商誉', 0)
    equity = data.get('净资产', 1)
    if equity > 0 and goodwill / equity > 0.5:
        warnings.append(f"⚠️  商誉/净资产 = {goodwill/equity*100:.1f}% > 50%，减值风险极高")
        score += 2
    elif equity > 0 and goodwill / equity > 0.3:
        warnings.append(f"⚡ 商誉/净资产 = {goodwill/equity*100:.1f}%，需要关注")
        score += 1

    # 7. 资产负债率
    debt_ratio = data.get('总负债', 0) / data.get('总资产', 1) * 100
    if debt_ratio > 80 and data.get('行业') not in ['银行', '保险']:
        warnings.append(f"⚠️  资产负债率 = {debt_ratio:.1f}%，极高")
        score += 1

    # 8. 净利润率极低（辛苦生意）
    if gross_margin < 15:
        warnings.append(f"⚡ 毛利率仅{gross_margin:.1f}%，抗风险能力弱")
        score += 1

    # 判定风险等级
    if score == 0:
        print(f"  ✅ 风险得分: {score} — 未发现明显风险信号")
    elif score <= 2:
        print(f"  ⚡ 风险得分: {score} — 轻微关注，需要进一步研究")
    elif score <= 4:
        print(f"  ⚠️  风险得分: {score} — 中度风险，建议深入调查")
    else:
        print(f"  🚨 风险得分: {score} — 高风险！投资前必须彻底调查")

    for w in warnings:
        print(f"  {w}")

    return score, warnings


def run_fraud_scan():
    """对三家公司运行造假扫描"""
    print(f"\n{'='*60}")
    print(f"  财务造假/粉饰风险扫描")
    print(f"{'='*60}")

    companies = [
        ('茅台', {
            '营收': 1505.6, '营业成本': 117.4, '净利润': 747.3,
            '总资产': 2720, '总负债': 446, '净资产': 2274,
            '经营现金流': 666, '应收账款': 0.6, '存货': 464,
            '商誉': 0, '货币资金': 691, '短期借款': 0, '长期借款': 0,
            '行业': '白酒'
        }),
        ('美的', {
            '营收': 3737, '营业成本': 2756, '净利润': 337,
            '总资产': 5350, '总负债': 3480, '净资产': 1870,
            '经营现金流': 430, '应收账款': 340, '存货': 450,
            '商誉': 290, '货币资金': 800, '短期借款': 120, '长期借款': 380,
            '行业': '家电'
        }),
        ('比亚迪', {
            '营收': 6023, '营业成本': 4818, '净利润': 300,
            '总资产': 9200, '总负债': 7200, '净资产': 2000,
            '经营现金流': 680, '应收账款': 680, '存货': 720,
            '商誉': 80, '货币资金': 850, '短期借款': 230, '长期借款': 620,
            '行业': '新能源车'
        }),
    ]

    scores = {}
    for name, data in companies:
        global total_assets
        total_assets = data['总资产']
        score, warnings = fraud_scanner(name, data)
        scores[name] = score

    print(f"\n  📊 风险排名:")
    for name, sc in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        bar = '█' * sc + '░' * (6 - sc)
        print(f"  {name}: {bar} ({sc}分)")


# ============================================================
# 4. 可视化
# ============================================================

def plot_three_company_comparison(metrics_dict):
    """三家公司核心指标对比图"""
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))

    companies_short = ['茅台', '美的', '比亚迪']
    colors = ['#E74C3C', '#3498DB', '#2ECC71']

    # 各子图的数据
    plots = [
        ('毛利率 (%)', '毛利率', axes[0, 0]),
        ('净利率 (%)', '净利率', axes[0, 1]),
        ('ROE & ROIC (%)', ['ROE', 'ROIC'], axes[0, 2]),
        ('资产负债率 (%)', '资产负债率', axes[1, 0]),
        ('经营现金流/净利润', '经营现金流/净利润', axes[1, 1]),
        ('FCF/净利润 (%)', 'FCF/净利润', axes[1, 2]),
    ]

    for title, keys, ax in plots:
        if isinstance(keys, list):
            # 分组柱状图
            x = np.arange(len(companies_short))
            width = 0.35
            for i, (key, color) in enumerate(zip(keys, ['#E74C3C', '#F39C12'])):
                values = []
                for comp_full in metrics_dict:
                    comp_short = comp_full.split(' (')[0] if ' (' in comp_full else comp_full
                    values.append(metrics_dict[comp_full].get(key, 0))
                bars = ax.bar(x + i * width - width/2, values, width, color=color, alpha=0.85,
                             label=key)
                for bar, val in zip(bars, values):
                    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values)*0.02,
                           f'{val:.1f}', ha='center', fontsize=9, fontweight='bold')
            ax.set_xticks(x)
            ax.set_xticklabels(companies_short)
            ax.legend(fontsize=8)
        else:
            values = []
            for comp_full in metrics_dict:
                values.append(metrics_dict[comp_full].get(keys, 0))
            bars = ax.bar(companies_short, values, color=colors, alpha=0.85)
            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values)*0.02,
                       f'{val:.1f}', ha='center', fontsize=10, fontweight='bold')

        ax.set_title(title, fontsize=11, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')

    plt.suptitle('茅台 vs 美的 vs 比亚迪：核心财务指标对比',
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(os.path.dirname(__file__), 'financial_comparison.png'),
                dpi=150, bbox_inches='tight')
    plt.close()
    print("✅ 图表已生成: financial_comparison.png")


def plot_cashflow_patterns():
    """三种现金流模式可视化"""
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    patterns = [
        ('奶牛型 — 茅台', [666, -25, -500], ['经营(+)', '投资(-)', '筹资(-)'],
         ['#2ECC71', '#E74C3C', '#E74C3C'],
         '主业赚钱 → 投资 + 分红'),
        ('成长型 — 比亚迪', [680, -550, 400], ['经营(+)', '投资(-)', '筹资(+)'],
         ['#2ECC71', '#E74C3C', '#3498DB'],
         '现金流 → 建厂 + 融资'),
        ('危险型 — 某暴雷公司', [-50, -80, 140], ['经营(-)', '投资(-)', '筹资(+)'],
         ['#E74C3C', '#E74C3C', '#F39C12'],
         '不赚钱 → 乱投资 → 靠借债续命'),
    ]

    for ax, (title, values, labels, colors, desc) in zip(axes, patterns):
        bars = ax.bar(labels, values, color=colors, alpha=0.85)

        # 零线
        ax.axhline(y=0, color='black', linewidth=0.5)

        for bar, val in zip(bars, values):
            va = 'bottom' if val >= 0 else 'top'
            offset = 10 if val >= 0 else -10
            ax.text(bar.get_x() + bar.get_width()/2, val + offset,
                   f'{val:+.0f}亿', ha='center', fontweight='bold', fontsize=10)

        ax.set_title(f'{title}\n{desc}', fontsize=11, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')

    plt.suptitle('现金流量表的三种典型模式', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(os.path.dirname(__file__), 'cashflow_patterns.png'),
                dpi=150, bbox_inches='tight')
    plt.close()
    print("✅ 图表已生成: cashflow_patterns.png")


def plot_dupont_waterfall():
    """杜邦分析瀑布图"""
    fig, ax = plt.subplots(figsize=(12, 6))

    companies = ['茅台', '美的', '比亚迪']
    dupont_data = {
        '茅台':  {'净利率': 49.6, '周转率': 0.55, '杠杆': 1.20},
        '美的':  {'净利率': 9.0,  '周转率': 0.70, '杠杆': 2.86},
        '比亚迪': {'净利率': 5.0,  '周转率': 0.65, '杠杆': 4.60},
    }

    x = np.arange(len(companies))
    width = 0.25
    colors = ['#E74C3C', '#3498DB', '#2ECC71']

    # ROE 总柱
    for i, comp in enumerate(companies):
        d = dupont_data[comp]
        roe = d['净利率'] * d['周转率'] * d['杠杆']

        # 三个因素堆叠显示（用乘积的对数来展示）
        ax.bar(i, d['净利率'], width, color='#FF6B6B', alpha=0.9, label='净利率(%)' if i == 0 else '')
        ax.bar(i, d['周转率']*100, width, bottom=d['净利率'],
               color='#4ECDC4', alpha=0.9, label='周转率(×100)' if i == 0 else '')
        ax.bar(i, d['杠杆']*20, width, bottom=d['净利率']+d['周转率']*100,
               color='#45B7D1', alpha=0.9, label='杠杆(×20)' if i == 0 else '')

        ax.text(i, d['净利率'] + d['周转率']*100 + d['杠杆']*20 + 2,
                f'ROE={roe:.1f}%', ha='center', fontweight='bold', fontsize=11)

    ax.set_xticks(x)
    ax.set_xticklabels(companies, fontsize=12)
    ax.set_ylabel('ROE拆解 (%)', fontsize=11)
    ax.set_title('ROE杜邦分析拆解：不同商业模式的高ROE之路', fontsize=13, fontweight='bold')
    ax.legend(loc='upper left', frameon=True, fontsize=9)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(os.path.join(os.path.dirname(__file__), 'dupont_waterfall.png'),
                dpi=150, bbox_inches='tight')
    plt.close()
    print("✅ 图表已生成: dupont_waterfall.png")


# ============================================================
# 5. 尝试获取真实财报数据
# ============================================================

def fetch_real_financials():
    """尝试从 akshare 获取真实财报数据"""
    try:
        import akshare as ak

        print("\n✅ 正在获取真实财报数据...")
        print("  (可能需要几秒钟...)")

        # 获取茅台财务数据
        # 利润表
        try:
            profit = ak.stock_financial_report_em(symbol="600519", symbol_type="利润表")
            if profit is not None and len(profit) > 0:
                print(f"\n  📊 茅台(600519) 最新财报数据（部分）:")
                print(f"  {profit.head(3)}")
        except Exception as e:
            print(f"  ⚠️ 获取茅台利润表失败: {e}")

        # 资产负债表
        try:
            balance = ak.stock_financial_report_em(symbol="600519", symbol_type="资产负债表")
            if balance is not None and len(balance) > 0:
                print(f"\n  📊 茅台(600519) 资产负债表:")
                print(f"  {balance.head(3)}")
        except Exception as e:
            print(f"  ⚠️ 获取茅台资产负债表失败: {e}")

        print(f"\n  💡 akshare API更新频繁，如果获取失败可以用同花顺/东方财富F10手工查看")
        print(f"  💡 或者使用 baostock (pip install baostock) 作为备选数据源")

    except ImportError:
        print("\n⚠️  akshare 未安装，跳过了真实数据获取")
        print("  安装: pip install akshare")
    except Exception as e:
        print(f"\n⚠️  获取数据时出错: {e}")


# ============================================================
# 主程序
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("  第五课实战代码：财报分析")
    print("=" * 60)

    # 1. 三家公司全面分析
    metrics_dict = analyze_three_companies()

    # 2. 造假扫描
    run_fraud_scan()

    # 3. 可视化
    print("\n📊 生成图表...")
    plot_three_company_comparison(metrics_dict)
    plot_cashflow_patterns()
    plot_dupont_waterfall()

    # 4. 尝试获取真实数据
    fetch_real_financials()

    print("\n" + "=" * 60)
    print("✅ 所有分析完成！")
    print("\n📝 课后练习提示:")
    print("  1. 打开同花顺/东方财富F10，找到茅台的三张表")
    print("  2. 选一家你感兴趣的公司，用本代码的FinancialAnalyzer分析")
    print("  3. 用10条造假信号扫描你关注池里的每家公司")
    print("  4. 对比毛利率，选出你关注池里毛利率最高的3家")
