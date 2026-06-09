"""
第一课配套实战代码：复利计算器 + 案例分析
"""

import matplotlib
matplotlib.use('Agg')  # 非交互式后端
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import os

# ============================================================
# 尝试设置中文字体
# ============================================================
try:
    # macOS 常见中文字体
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


def compound_interest(principal, annual_rate, years, monthly_contribution=0):
    """
    复利计算器

    参数:
        principal: 初始本金
        annual_rate: 年化收益率（如0.08表示8%）
        years: 投资年限
        monthly_contribution: 每月定投金额（默认0）

    返回:
        final_value: 最终总价值
        yearly_values: 每年末的账户余额列表
    """
    monthly_rate = annual_rate / 12
    total_months = years * 12
    balance = principal
    yearly_values = [principal]

    for month in range(1, total_months + 1):
        balance = balance * (1 + monthly_rate) + monthly_contribution
        if month % 12 == 0:
            yearly_values.append(balance)

    return balance, yearly_values


def calculate_purchasing_power(amount, inflation_rate, years):
    """计算实际购买力"""
    return amount / ((1 + inflation_rate) ** years)


def plot_compound_growth_scenarios():
    """
    场景对比图：不同收益率下的复利增长
    """
    principal = 100000  # 10万本金
    years = 30
    rates = [0.02, 0.03, 0.05, 0.08, 0.10, 0.12]
    colors = ['#8B4513', '#CD853F', '#DAA520', '#228B22', '#1E90FF', '#FF4500']

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # 图1：不同收益率对比
    ax1 = axes[0]
    for rate, color in zip(rates, colors):
        _, yearly_values = compound_interest(principal, rate, years)
        x = list(range(years + 1))
        ax1.plot(x, [v / 10000 for v in yearly_values], color=color, linewidth=2,
                label=f'{rate*100:.0f}%')

    ax1.set_title('10万元在不同收益率下的复利增长', fontsize=14, fontweight='bold')
    ax1.set_xlabel('年数')
    ax1.set_ylabel('账户余额（万元）')
    ax1.legend(loc='upper left', frameon=True)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(0, years)

    # 标注关键数据
    for rate, color in zip(rates, colors):
        _, vals = compound_interest(principal, rate, years)
        final = vals[-1] / 10000
        ax1.annotate(f'{final:.1f}万',
                     xy=(years, final),
                     xytext=(5, 0), textcoords='offset points',
                     fontsize=8, color=color)

    # 图2：三种典型场景柱状图
    ax2 = axes[1]
    scenarios = {
        '银行存款\n(2%)': 0.02,
        '债券/理财\n(5%)': 0.05,
        '指数基金\n(8%)': 0.08,
        '优秀主动基金\n(12%)': 0.12,
    }

    periods = [10, 20, 30]
    x_positions = np.arange(len(periods))
    bar_width = 0.2
    colors_bar = ['#CD853F', '#DAA520', '#228B22', '#1E90FF']

    for i, (label, rate) in enumerate(scenarios.items()):
        values = []
        for yr in periods:
            fv, _ = compound_interest(principal, rate, yr)
            values.append(fv / 10000)
        ax2.bar(x_positions + i * bar_width, values, bar_width,
                label=label, color=colors_bar[i], alpha=0.85)

    ax2.set_title('10万元本金：不同收益率 × 不同时间 终值对比', fontsize=14, fontweight='bold')
    ax2.set_xlabel('投资年限')
    ax2.set_ylabel('终值（万元）')
    ax2.set_xticks(x_positions + bar_width * 1.5)
    ax2.set_xticklabels([f'{p}年' for p in periods])
    ax2.legend(loc='upper left', frameon=True)
    ax2.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(os.path.join(os.path.dirname(__file__), 'compound_growth.png'),
                dpi=150, bbox_inches='tight')
    plt.close()
    print("✅ 图表已生成: compound_growth.png")


def plot_inflation_impact():
    """
    通货膨胀购买力衰减图
    """
    amount = 1000000  # 100万
    years = 30
    inflation_rates = [0.02, 0.03, 0.05, 0.07]
    colors = ['#228B22', '#DAA520', '#FF4500', '#8B0000']

    fig, ax = plt.subplots(figsize=(12, 5))

    x = list(range(years + 1))
    for rate, color in zip(inflation_rates, colors):
        y = [calculate_purchasing_power(amount, rate, yr) / 10000 for yr in x]
        ax.plot(x, y, color=color, linewidth=2.5,
                label=f'{rate*100:.0f}% 年通胀率')

    ax.axhline(y=50, color='gray', linestyle='--', alpha=0.5)
    ax.annotate('购买力减半线',
                xy=(0, 50), xytext=(15, 55),
                arrowprops=dict(arrowstyle='->', color='gray'),
                fontsize=10, color='gray')

    ax.set_title('100万元在不同通胀率下的购买力衰减', fontsize=14, fontweight='bold')
    ax.set_xlabel('年数')
    ax.set_ylabel('实际购买力（万元）')
    ax.legend(loc='upper right', frameon=True)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, years)
    ax.set_ylim(0, 105)

    # 填充通胀损失区域（3%通胀）
    y_3pct = [calculate_purchasing_power(amount, 0.03, yr) / 10000 for yr in x]
    ax.fill_between(x, y_3pct, 100, alpha=0.08, color='red')
    ax.text(20, 80, '通胀侵蚀的区域', fontsize=10, color='red', alpha=0.6)

    plt.tight_layout()
    plt.savefig(os.path.join(os.path.dirname(__file__), 'inflation_impact.png'),
                dpi=150, bbox_inches='tight')
    plt.close()
    print("✅ 图表已生成: inflation_impact.png")


def case_study_zhang_vs_li():
    """
    案例研究：张三 vs 李四
    """
    print("\n" + "=" * 60)
    print("  案例分析：张三 vs 李四的25年财富对比")
    print("=" * 60)

    monthly_income = 10000
    monthly_living = 5000
    years = 25
    inflation = 0.03

    # 张三：全部存银行（2%）
    zhang_monthly_save = monthly_income - monthly_living
    zhang_total, zhang_yearly = compound_interest(0, 0.02, years, zhang_monthly_save)
    zhang_real = calculate_purchasing_power(zhang_total, inflation, years)
    zhang_invested = zhang_monthly_save * 12 * years

    # 李四：每月定投3000指数基金（8%），剩余存银行（2%）
    li_monthly_invest = 3000
    li_monthly_save = monthly_income - monthly_living - li_monthly_invest
    li_invest_total, li_invest_yearly = compound_interest(0, 0.08, years, li_monthly_invest)
    li_save_total, _ = compound_interest(0, 0.02, years, li_monthly_save)
    li_total = li_invest_total + li_save_total
    li_real = calculate_purchasing_power(li_total, inflation, years)
    li_invested = li_monthly_invest * 12 * years + li_monthly_save * 12 * years

    print(f"\n{'项目':<25} {'张三（存款派）':<20} {'李四（投资派）':<20}")
    print("-" * 65)
    print(f"{'每月投资金额':<25} {'0元':<20} {'3,000元':<20}")
    print(f"{'每月储蓄金额':<25} {f'{zhang_monthly_save:,}元':<20} {f'{li_monthly_save:,}元':<20}")
    print(f"{'总投资本金':<25} {f'{zhang_invested:,.0f}元':<20} {f'{li_invested:,.0f}元':<20}")
    print(f"{'25年后总财富':<25} {f'{zhang_total:,.0f}元':<20} {f'{li_total:,.0f}元':<20}")
    print(f"{'实际购买力(25年后)':<25} {f'{zhang_real:,.0f}元':<20} {f'{li_real:,.0f}元':<20}")
    print(f"{'投资收益部分':<25} {'0元':<20} {f'{li_invest_total:,.0f}元':<20}")
    print(f"{'其中投资收益':<25} {'0元':<20} {f'{li_invest_total - li_monthly_invest*12*years:,.0f}元':<20}")
    print(f"{'财富差距':<25} {'':<20} {f'+{li_total - zhang_total:,.0f}元':<20}")
    print()

    # 额外分析：如果李四每月定投增加到5000
    li2_monthly_invest = 5000
    li2_monthly_save = monthly_income - monthly_living - li2_monthly_invest
    li2_invest_total, _ = compound_interest(0, 0.08, years, li2_monthly_invest)
    li2_save_total, _ = compound_interest(0, 0.02, years, li2_monthly_save)
    li2_total = li2_invest_total + li2_save_total

    print(f"💡 如果李四每月定投5,000元（更努力省钱）:")
    print(f"   25年后总财富: {li2_total:,.0f}元")
    print(f"   比张三多: +{li2_total - zhang_total:,.0f}元")
    print()

    return zhang_total, li_total, li2_total


def plot_early_vs_late():
    """
    早开始 vs 晚开始对比图
    """
    annual_contribution = 50000  # 每年投5万
    rate = 0.10

    # 小明：25-35岁投入（10年），然后到60岁
    xiaoming_balance = 0
    xiaoming_values = []
    for age in range(25, 61):
        if age <= 35:
            xiaoming_balance = xiaoming_balance * (1 + rate) + annual_contribution
        else:
            xiaoming_balance = xiaoming_balance * (1 + rate)
        xiaoming_values.append(xiaoming_balance)

    # 小红：35-60岁投入（25年）
    xiaohong_balance = 0
    xiaohong_values = []
    for age in range(25, 61):
        if age >= 35:
            xiaohong_balance = xiaohong_balance * (1 + rate) + annual_contribution
        xiaohong_values.append(xiaohong_balance)

    ages = list(range(25, 61))

    fig, ax = plt.subplots(figsize=(14, 6))

    ax.fill_between([25, 35], 0, max(xiaoming_values) * 1.05,
                    alpha=0.08, color='blue', label='小明投入期 (10年)')
    ax.fill_between([35, 60], 0, max(xiaoming_values) * 1.05,
                    alpha=0.05, color='orange', label='小红投入期 (25年)')

    ax.plot(ages, [v / 10000 for v in xiaoming_values],
            color='#1E90FF', linewidth=3, label='小明: 25-35岁投入50万 → 60岁')
    ax.plot(ages, [v / 10000 for v in xiaohong_values],
            color='#FF4500', linewidth=3, label='小红: 35-60岁投入125万 → 60岁')

    # 标注最终结果
    ax.annotate(f'小明: {xiaoming_values[-1]/10000:.0f}万\n(投入50万)',
                xy=(60, xiaoming_values[-1] / 10000),
                xytext=(-120, -40), textcoords='offset points',
                fontsize=11, color='#1E90FF', fontweight='bold',
                arrowprops=dict(arrowstyle='->', color='#1E90FF'))

    ax.annotate(f'小红: {xiaohong_values[-1]/10000:.0f}万\n(投入125万)',
                xy=(60, xiaohong_values[-1] / 10000),
                xytext=(-120, 30), textcoords='offset points',
                fontsize=11, color='#FF4500', fontweight='bold',
                arrowprops=dict(arrowstyle='->', color='#FF4500'))

    ax.axvline(x=35, color='gray', linestyle='--', alpha=0.5)
    ax.text(35.5, max(xiaoming_values) / 10000 * 0.9,
            '← 35岁分界线',
            fontsize=9, color='gray')

    ax.set_title('早点开始 vs 晚点开始：时间的魔力', fontsize=14, fontweight='bold')
    ax.set_xlabel('年龄')
    ax.set_ylabel('账户余额（万元）')
    ax.legend(loc='upper left', frameon=True)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(25, 60)

    plt.tight_layout()
    plt.savefig(os.path.join(os.path.dirname(__file__), 'early_vs_late.png'),
                dpi=150, bbox_inches='tight')
    plt.close()
    print("✅ 图表已生成: early_vs_late.png")


def financial_freedom_calculator(annual_expense, safe_withdrawal_rate=0.04):
    """
    财务自由计算器

    参数:
        annual_expense: 年度生活支出
        safe_withdrawal_rate: 安全提取率（4%法则）
    """
    target = annual_expense / safe_withdrawal_rate
    print(f"\n{'='*60}")
    print(f"  财务自由计算器")
    print(f"{'='*60}")
    print(f"  年度生活支出: {annual_expense:,.0f} 元/年")
    print(f"  安全提取率: {safe_withdrawal_rate*100:.0f}%")
    print(f"  ─────────────────────────────")
    print(f"  财务自由目标: {target:,.0f} 元 ({target/10000:.0f} 万元)")
    print(f"  每年可提取: {target * safe_withdrawal_rate:,.0f} 元")
    print(f"  每月可提取: {target * safe_withdrawal_rate / 12:,.0f} 元")
    print(f"{'='*60}")

    # 计算到达目标需要的时间
    print(f"\n  定投达成目标的路径:")
    print(f"  {'每月定投':<15} {'年化收益':<10} {'需要年数':<10} {'总投入':<20} {'终值':<20}")
    print(f"  {'-'*75}")

    for monthly in [2000, 3000, 5000, 8000, 10000]:
        for rate in [0.06, 0.08, 0.10]:
            years_needed = 0
            balance = 0
            while balance < target and years_needed < 50:
                balance, _ = compound_interest(0, rate, 1, monthly)
                years_needed += 1
                # 简化计算：直接用近似
                if years_needed == 1:
                    balance = monthly * 12 * (1 + rate)
                else:
                    balance = balance * (1 + rate) + monthly * 12

            # 用更精确的公式
            from math import log
            if monthly * 12 * rate > 0:
                years_needed = log(1 + target * rate / (monthly * 12)) / log(1 + rate)
            else:
                years_needed = 99

            if years_needed <= 40:
                total_invested = monthly * 12 * years_needed
                fv, _ = compound_interest(0, rate, int(years_needed) + 1, monthly)
                print(f"  {monthly:>8,}元/月  {rate*100:>6.0f}%     {years_needed:>6.1f}年    "
                      f"{total_invested:>12,.0f}元    {fv:>12,.0f}元")

    return target


if __name__ == '__main__':
    print("=" * 60)
    print("  第一课实战代码：复利与投资认知")
    print("=" * 60)

    # 1. 基础复利计算演示
    print("\n📊 基础复利计算演示")
    print("-" * 40)
    principal = 100000
    for rate in [0.03, 0.05, 0.08, 0.10, 0.15, 0.20]:
        for years in [10, 20, 30, 40]:
            fv, _ = compound_interest(principal, rate, years)
            times = fv / principal
            print(f"  10万 × {rate*100:.0f}% × {years}年 = {fv:>12,.0f}元 ({times:.1f}倍)")

    # 2. 通胀购买力演示
    print("\n📊 通胀购买力衰减演示")
    print("-" * 40)
    amount = 1000000
    for inflation in [0.02, 0.03, 0.05]:
        for yrs in [10, 20, 30]:
            pv = calculate_purchasing_power(amount, inflation, yrs)
            print(f"  100万 × {inflation*100:.0f}%通胀 × {yrs}年后 = 实际购买力 {pv:>10,.0f}元")

    # 3. 生成图表
    print("\n📊 生成分析图表...")
    plot_compound_growth_scenarios()
    plot_inflation_impact()
    plot_early_vs_late()

    # 4. 案例研究
    case_study_zhang_vs_li()

    # 5. 财务自由计算器
    print("\n" + "=" * 60)
    print("  💰 输入你的年度支出，计算财务自由目标")
    print("=" * 60)

    # 示例：假设年度支出12万
    financial_freedom_calculator(120000)

    # 也可以让用户输入
    # expense = float(input("请输入你的年度生活支出（元）: "))
    # financial_freedom_calculator(expense)

    print("\n✅ 所有计算完成！请查看生成的PNG图表文件。")
    print("\n📝 思考题：")
    print("  1. 观察复利增长曲线，前10年为什么看起来'没什么变化'？")
    print("  2. 如果年化收益从8%提高到10%，30年后差距有多大？")
    print("  3. 你现在的年龄和收入情况，每月该定投多少？")
    print("  4. 通货膨胀3%和5%，对退休生活的影响差多少？")
