"""
第四课配套实战代码：基金基础分析工具
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
# 1. 基金费率对长期收益的影响
# ============================================================

def fee_impact_calculator(principal, annual_return, fee_rate, years):
    """计算费率对终值的影响"""
    net_return = annual_return - fee_rate
    gross_fv = principal * (1 + annual_return) ** years
    net_fv = principal * (1 + net_return) ** years
    fee_cost = gross_fv - net_fv
    return gross_fv, net_fv, fee_cost


def demo_fee_impact():
    """演示费率对长期收益的影响"""
    print("\n" + "=" * 60)
    print("  费率对长期收益的影响")
    print("=" * 60)

    principal = 100000  # 10万
    years = 30
    gross_return = 0.10  # 10%年化

    fees = [
        ('ETF (0.2%)', 0.002),
        ('指数基金 (0.5%)', 0.005),
        ('主动基金 (1.2%)', 0.012),
        ('高费率主动 (1.8%)', 0.018),
    ]

    print(f"\n  本金: {principal:,}元, 投资年限: {years}年, 市场年化: {gross_return*100:.0f}%")
    print(f"\n  {'基金类型':<20} {'费率':<10} {'净终值':<18} {'费用损失':<18} {'费后年化':<10}")
    print(f"  {'-'*76}")

    for name, fee in fees:
        gross_fv, net_fv, fee_cost = fee_impact_calculator(principal, gross_return, fee, years)
        net_annual = ((net_fv / principal) ** (1/years) - 1) * 100
        print(f"  {name:<20} {fee*100:<10.1f}% {net_fv:>14,.0f}元  "
              f"{fee_cost:>14,.0f}元  {net_annual:>6.2f}%")

    # 对比最低和最高费率
    _, lo_fv, _ = fee_impact_calculator(principal, gross_return, 0.002, years)
    _, hi_fv, _ = fee_impact_calculator(principal, gross_return, 0.018, years)
    print(f"\n  💡 ETF(0.2%) vs 高费率主动(1.8%):")
    print(f"     终值差距: {lo_fv - hi_fv:,.0f}元")
    print(f"     这{(lo_fv - hi_fv)/principal:.1f}倍于你的本金！")


# ============================================================
# 2. 资产配置组合模拟
# ============================================================

def simulate_portfolio(returns, weights, years=10, initial=100000):
    """
    模拟投资组合表现

    参数:
        returns: 各类资产的年化收益率
        weights: 各类资产的配置比例
    """
    portfolio_return = sum(r * w for r, w in zip(returns, weights))
    final_value = initial * (1 + portfolio_return) ** years
    return portfolio_return, final_value


def demo_portfolio_comparison():
    """对比不同基金组合"""
    print("\n" + "=" * 60)
    print("  三种入门基金组合对比")
    print("=" * 60)

    years = 20
    initial = 100000

    # 资产预期收益假设
    ret = {
        '沪深300': 0.09,
        '纳指100': 0.11,
        '债券': 0.04,
        '货币': 0.02,
    }

    portfolios = {
        '极简版': {'沪深300': 1.0},
        '标准版': {'沪深300': 0.7, '债券': 0.3},
        '全球化版': {'沪深300': 0.35, '纳指100': 0.35, '债券': 0.3},
        '保守版': {'债券': 0.6, '沪深300': 0.3, '货币': 0.1},
    }

    print(f"\n  初始投入: {initial:,}元, 投资年限: {years}年")
    print(f"\n  {'组合':<12} {'配置':<40} {'预期年化':<10} {'终值':<18}")
    print(f"  {'-'*80}")

    for name, alloc in portfolios.items():
        weights_list = list(alloc.values())
        returns_list = [ret[k] for k in alloc.keys()]
        p_return, fv = simulate_portfolio(returns_list, weights_list, years, initial)

        alloc_str = ' + '.join([f'{k}({v*100:.0f}%)' for k, v in alloc.items()])
        print(f"  {name:<12} {alloc_str:<40} {p_return*100:>6.2f}%    {fv:>14,.0f}元")

    print(f"\n  💡 这些是预期收益，实际会围绕预期大幅波动")
    print(f"  💡 极简版预期收益最高，但波动也最大")
    print(f"  💡 保守版波动最低，但长期收益显著更低")


# ============================================================
# 3. 定投模拟器
# ============================================================

def dollar_cost_averaging(monthly_amount, annual_return, years):
    """
    定投模拟器

    每月投入固定金额，模拟基金定投
    """
    monthly_rate = annual_return / 12
    total_months = years * 12
    balance = 0
    invested = 0
    balances = []

    for month in range(total_months):
        balance = balance * (1 + monthly_rate) + monthly_amount
        invested += monthly_amount
        if month % 12 == 0:
            balances.append(balance)

    return balance, invested, balances


def demo_dca():
    """定投演示"""
    print("\n" + "=" * 60)
    print("  基金定投模拟（每月固定金额投入）")
    print("=" * 60)

    monthly = 3000
    years_list = [5, 10, 15, 20, 25, 30]
    rates = [0.06, 0.08, 0.10]

    print(f"\n  每月定投: {monthly:,}元")
    print(f"\n  {'年限':<8}", end='')
    for r in rates:
        print(f"{'年化'+str(int(r*100))+'%':<20}", end='')
    print(f"{'总投入':<15}")
    print(f"  {'-'*80}")

    for yrs in years_list:
        print(f"  {yrs}年    ", end='')
        for r in rates:
            fv, invested, _ = dollar_cost_averaging(monthly, r, yrs)
            print(f"{fv:>12,.0f}元      ", end='')
        print(f"{invested:>12,.0f}元")

    # 定投 vs 一次性投入
    print(f"\n  💡 定投的魔力：每月{monthly}元，年化8%，30年:")
    fv, invested, balances = dollar_cost_averaging(monthly, 0.08, 30)
    print(f"     总投入: {invested:,}元")
    print(f"     终值: {fv:,.0f}元")
    print(f"     收益: {fv - invested:,.0f}元 ({(fv/invested-1)*100:.1f}%)")

    return balances


# ============================================================
# 4. 费率对比柱状图
# ============================================================

def plot_fee_comparison():
    """可视化费率对长期收益的影响"""
    principal = 100000
    years = 30
    gross_return = 0.10

    fees = np.arange(0.001, 0.021, 0.001)  # 0.1%到2.0%
    final_values = []

    for fee in fees:
        _, fv, _ = fee_impact_calculator(principal, gross_return, fee, years)
        final_values.append(fv / 10000)

    fig, ax = plt.subplots(figsize=(12, 5))

    ax.fill_between(fees * 100, final_values, max(final_values),
                    alpha=0.15, color='red')
    ax.plot(fees * 100, final_values, 'b-', linewidth=2.5)

    # 标注关键费率
    key_fees = {0.2: 'ETF(0.2%)', 0.5: '指数(0.5%)', 1.2: '主动(1.2%)', 1.8: '高费率(1.8%)'}
    for fee_pct, label in key_fees.items():
        _, fv, _ = fee_impact_calculator(principal, gross_return, fee_pct / 100, years)
        ax.annotate(f'{label}\n{fv/10000:.1f}万',
                     xy=(fee_pct, fv / 10000),
                     xytext=(fee_pct + 0.15, fv / 10000 + 20),
                     fontsize=9,
                     arrowprops=dict(arrowstyle='->', color='darkred'),
                     fontweight='bold')

    ax.set_xlabel('年费率 (%)', fontsize=12)
    ax.set_ylabel('30年后的终值（万元）', fontsize=12)
    ax.set_title(f'费率对{principal//10000}万元本金的影响（年化{gross_return*100:.0f}%，{years}年）',
                 fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 2.1)

    # 红色区域标注
    ax.text(1.6, max(final_values) * 0.85,
            '红色区域 = 费率吞噬的收益',
            fontsize=10, color='red', alpha=0.7)

    plt.tight_layout()
    plt.savefig(os.path.join(os.path.dirname(__file__), 'fee_impact.png'),
                dpi=150, bbox_inches='tight')
    plt.close()
    print("✅ 图表已生成: fee_impact.png")


# ============================================================
# 5. 基金类型风险收益散点图
# ============================================================

def plot_fund_risk_return():
    """各类基金风险收益分布"""
    np.random.seed(42)

    fund_types = [
        ('货币基金', 2.0, 0.3, 50, '#3498DB'),
        ('纯债基金', 4.5, 2.0, 50, '#2ECC71'),
        ('二级债基', 6.0, 5.0, 50, '#27AE60'),
        ('偏债混合', 7.5, 8.0, 50, '#F39C12'),
        ('平衡混合', 9.0, 15.0, 50, '#E67E22'),
        ('偏股混合', 10.5, 22.0, 50, '#E74C3C'),
        ('股票基金', 11.0, 25.0, 50, '#C0392B'),
        ('行业ETF', 12.0, 30.0, 50, '#8B0000'),
    ]

    fig, ax = plt.subplots(figsize=(12, 6))

    for name, mu_return, mu_risk, n, color in fund_types:
        returns = np.random.normal(mu_return, mu_risk * 0.3, n)
        risks = np.random.normal(mu_risk, mu_risk * 0.15, n)

        ax.scatter(risks, returns, c=color, label=name, alpha=0.6,
                   s=80, edgecolors='white', linewidth=0.5)

    # 效率前沿参考线
    x_ref = np.linspace(0, 35, 100)
    y_ref = 2 + 0.35 * x_ref
    ax.plot(x_ref, y_ref, 'k--', alpha=0.3, linewidth=1.5, label='大概的效率前沿')

    ax.set_xlabel('风险（年化波动率 %）', fontsize=12)
    ax.set_ylabel('预期年化收益 (%)', fontsize=12)
    ax.set_title('各类基金的风险-收益分布', fontsize=14, fontweight='bold')
    ax.legend(loc='lower right', frameon=True, ncol=2)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 40)
    ax.set_ylim(0, 20)

    plt.tight_layout()
    plt.savefig(os.path.join(os.path.dirname(__file__), 'fund_risk_return.png'),
                dpi=150, bbox_inches='tight')
    plt.close()
    print("✅ 图表已生成: fund_risk_return.png")


# ============================================================
# 6. 指数 vs 主动基金跑赢比例
# ============================================================

def plot_active_vs_passive():
    """主动基金跑赢指数的比例"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 美国市场数据
    periods_us = ['1年', '3年', '5年', '10年', '15年', '20年']
    underperform_us = [63, 78, 85, 92, 95, 97]  # 跑输比例
    outperform_us = [100 - x for x in underperform_us]

    # A股数据
    periods_cn = ['1年', '3年', '5年', '10年']
    underperform_cn = [45, 48, 52, 62]
    outperform_cn = [100 - x for x in underperform_cn]

    for ax, periods, outperform, title, color_out, color_under in [
        (axes[0], periods_us, outperform_us, '美国市场（标普500为基准）',
         '#2ECC71', '#E74C3C'),
        (axes[1], periods_cn, outperform_cn, 'A股市场（沪深300为基准）',
         '#3498DB', '#E74C3C'),
    ]:
        underperform = [100 - x for x in outperform]
        ax.bar(periods, outperform, color=color_out, alpha=0.85, label='跑赢的主动基金')
        ax.bar(periods, underperform, bottom=outperform, color=color_under,
               alpha=0.85, label='跑输的主动基金')

        # 标注比例
        for i, (out, under) in enumerate(zip(outperform, underperform)):
            ax.text(i, out / 2, f'{out}%', ha='center', fontweight='bold', fontsize=10)
            ax.text(i, out + under / 2, f'{under}%', ha='center', fontsize=10)

        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.set_ylabel('占比 (%)')
        ax.legend(loc='upper right', frameon=True)
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_ylim(0, 105)

    plt.suptitle('主动基金能跑赢指数吗？（数据来源：SPIVA / 晨星）',
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(os.path.dirname(__file__), 'active_vs_passive.png'),
                dpi=150, bbox_inches='tight')
    plt.close()
    print("✅ 图表已生成: active_vs_passive.png")


# ============================================================
# 7. 基金定投可视化
# ============================================================

def plot_dca_growth():
    """定投增长曲线"""
    monthly = 3000
    years = 30
    rates = [0.06, 0.08, 0.10]

    fig, ax = plt.subplots(figsize=(12, 6))
    years_range = range(years + 1)
    colors = ['#F39C12', '#3498DB', '#2ECC71']

    for rate, color in zip(rates, colors):
        _, invested, balances = dollar_cost_averaging(monthly, rate, years)
        balances_full = [0] + balances  # 加上第0年

        ax.plot(years_range, [b/10000 for b in balances_full],
                color=color, linewidth=2.5, label=f'年化{int(rate*100)}%')

        # 最终值标注
        ax.annotate(f'{balances_full[-1]/10000:.0f}万',
                     xy=(years, balances_full[-1]/10000),
                     xytext=(5, 5), textcoords='offset points',
                     fontsize=10, color=color, fontweight='bold')

    # 投入本金线
    invested_line = [monthly * 12 * y / 10000 for y in years_range]
    ax.fill_between(years_range, invested_line, 0,
                    alpha=0.08, color='gray')
    ax.plot(years_range, invested_line, 'k--', linewidth=1, alpha=0.5,
            label='累计投入本金')

    ax.annotate(f'总投入{monthly*12*years/10000:.0f}万',
                 xy=(years, invested_line[-1]),
                 xytext=(-80, -20), textcoords='offset points',
                 fontsize=9, color='gray')

    ax.set_xlabel('年数', fontsize=12)
    ax.set_ylabel('账户余额（万元）', fontsize=12)
    ax.set_title(f'基金定投：每月{monthly:,}元，不同收益率下的增长',
                 fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', frameon=True)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, years)

    plt.tight_layout()
    plt.savefig(os.path.join(os.path.dirname(__file__), 'dca_growth.png'),
                dpi=150, bbox_inches='tight')
    plt.close()
    print("✅ 图表已生成: dca_growth.png")


# ============================================================
# 8. 尝试获取真实基金数据
# ============================================================

def fetch_real_fund_data():
    """尝试使用 akshare 获取基金数据"""
    try:
        import akshare as ak
        print("\n✅ akshare 已安装，正在获取真实基金数据...")

        # 获取公募基金列表
        fund_df = ak.fund_name_em()
        print(f"  共获取 {len(fund_df)} 只基金")

        # 筛选指数基金
        idx_funds = fund_df[fund_df['基金类型'].str.contains('ETF|指数', na=False)]
        print(f"  其中ETF/指数基金: {len(idx_funds)} 只")

        # 展示一些例子
        if len(fund_df) > 0:
            print(f"\n  📊 公募基金类型分布:")
            type_counts = fund_df['基金类型'].value_counts().head(10)
            for t, c in type_counts.items():
                print(f"     {t}: {c}只")

        return fund_df
    except ImportError:
        print("\n⚠️  akshare 未安装，跳过了真实数据获取。")
        print("  如需获取基金数据，请运行: pip install akshare")
        return None
    except Exception as e:
        print(f"\n⚠️  获取数据时出错: {e}")
        return None


# ============================================================
# 9. 基金筛选器（用静态数据演示逻辑）
# ============================================================

def fund_screener_demo():
    """演示基金筛选逻辑"""
    print("\n" + "=" * 60)
    print("  基金筛选器（逻辑演示）")
    print("=" * 60)

    # 模拟基金数据
    sample_funds = [
        {'名称': '华泰柏瑞沪深300ETF', '代码': '510300', '类型': 'ETF',
         '规模(亿)': 1200, '成立年': 2012, '管理费': 0.15, '托管费': 0.05,
         '跟踪误差': 0.22, '经理年限': 8, '晨星评级': 5, '3年收益': 8.5},
        {'名称': '易方达沪深300ETF联接', '代码': '110020', '类型': '指数联接',
         '规模(亿)': 180, '成立年': 2015, '管理费': 0.15, '托管费': 0.05,
         '跟踪误差': 0.35, '经理年限': 6, '晨星评级': 4, '3年收益': 8.2},
        {'名称': '某明星主动基金A', '代码': 'xxxxxx', '类型': '偏股混合',
         '规模(亿)': 350, '成立年': 2014, '管理费': 1.50, '托管费': 0.25,
         '跟踪误差': None, '经理年限': 10, '晨星评级': 4, '3年收益': 12.0},
        {'名称': '某小型主动基金', '代码': 'xxxxxx', '类型': '普通股票',
         '规模(亿)': 0.3, '成立年': 2021, '管理费': 1.50, '托管费': 0.25,
         '跟踪误差': None, '经理年限': 2, '晨星评级': 2, '3年收益': 15.0},
        {'名称': '某行业ETF', '代码': 'xxxxxx', '类型': 'ETF',
         '规模(亿)': 8, '成立年': 2022, '管理费': 0.50, '托管费': 0.10,
         '跟踪误差': 0.80, '经理年限': 3, '晨星评级': 3, '3年收益': 20.0},
    ]

    print(f"\n  筛选条件:")
    print(f"  1. 规模 > 2亿")
    print(f"  2. 成立 > 3年")
    print(f"  3. 晨星评级 ≥ 3星")
    print(f"  4. 经理从业 > 5年（仅主动基金）")

    print(f"\n  {'名称':<25} {'通过?':<8} {'未通过原因'}")
    print(f"  {'-'*60}")

    for f in sample_funds:
        issues = []
        if f['规模(亿)'] < 2:
            issues.append(f"规模太小({f['规模(亿)']}亿)")
        if f['成立年'] > 2023:  # 假设当前2026
            issues.append(f"成立太短({f['成立年']}年)")
        if f['晨星评级'] < 3:
            issues.append(f"评级太低({f['晨星评级']}星)")
        if f['类型'] not in ['ETF', '指数联接'] and f['经理年限'] < 5:
            issues.append(f"经理经验不足({f['经理年限']}年)")

        if not issues:
            print(f"  {f['名称']:<25} {'✅ 通过':<8} -")
        else:
            print(f"  {f['名称']:<25} {'❌ 不通过':<8} {'; '.join(issues)}")

    print(f"\n  💡 这只是逻辑演示。实际筛选需要用真实数据。")
    print(f"  💡 筛出来的不一定好，筛掉的也不一定差。")
    print(f"  💡 筛选的目的是缩小范围，不是自动决策。")


if __name__ == '__main__':
    print("=" * 60)
    print("  第四课实战代码：基金基础")
    print("=" * 60)

    # 1. 费率影响分析
    demo_fee_impact()

    # 2. 投资组合对比
    demo_portfolio_comparison()

    # 3. 定投模拟
    demo_dca()

    # 4. 图表生成
    print("\n📊 生成图表...")
    plot_fee_comparison()
    plot_fund_risk_return()
    plot_active_vs_passive()
    plot_dca_growth()

    # 5. 基金筛选器
    fund_screener_demo()

    # 6. 尝试获取真实数据
    fetch_real_fund_data()

    print("\n" + "=" * 60)
    print("✅ 所有分析完成！")
    print("\n📝 课后练习提示：")
    print("  1. 打开支付宝/天天基金，搜索'510300'，看看一只ETF长什么样")
    print("  2. 对比3只跟踪沪深300的基金，算算出费率差在30年后的影响")
    print("  3. 用定投模拟器，算算你每月定投X元，Y年后大概有多少钱")
    print("  4. 根据你的年龄和风险偏好，从三种入门组合中选一个")
