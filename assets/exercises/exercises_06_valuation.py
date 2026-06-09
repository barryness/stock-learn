"""
第六课配套实战代码：估值方法大全
包含：PE/PB/PEG/PS/EV-EBITDA/DDM/DCF 七种估值方法的Python实现
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


class ValuationEngine:
    """估值引擎：7种估值方法的统一实现"""

    def __init__(self, name, data):
        self.name = name
        self.data = data
        self.results = {}

    # ================================================================
    # 方法1：PE估值
    # ================================================================
    def pe_valuation(self):
        eps = self.data['eps']
        pe_low = self.data.get('pe_low', 0)
        pe_median = self.data.get('pe_median', 0)
        pe_high = self.data.get('pe_high', 0)

        result = {
            'method': 'PE估值',
            'enterprise_value_low': eps * pe_low,
            'enterprise_value_mid': eps * pe_median,
            'enterprise_value_high': eps * pe_high,
        }
        self.results['PE'] = result
        return result

    # ================================================================
    # 方法2：PB估值
    # ================================================================
    def pb_valuation(self):
        bvps = self.data.get('bvps', 0)  # 每股净资产
        pb_low = self.data.get('pb_low', 0)
        pb_median = self.data.get('pb_median', 0)
        pb_high = self.data.get('pb_high', 0)

        result = {
            'method': 'PB估值',
            'low': bvps * pb_low,
            'mid': bvps * pb_median,
            'high': bvps * pb_high,
        }
        self.results['PB'] = result
        return result

    # ================================================================
    # 方法3：PEG估值
    # ================================================================
    def peg_valuation(self):
        eps = self.data['eps']
        growth_rate = self.data.get('growth_rate', 0.10)  # 盈利增长率
        peg_ratio = self.data.get('peg_target', 1.0)  # 目标PEG

        # PEG=1 → 合理PE = 增长率×100
        fair_pe = growth_rate * 100 * peg_ratio
        fair_value = eps * fair_pe

        result = {
            'method': 'PEG估值',
            'growth_rate': growth_rate * 100,  # 转为百分比
            'target_peg': peg_ratio,
            'fair_pe': fair_pe,
            'fair_value': fair_value,
            'low': eps * growth_rate * 100 * 0.7,   # PEG=0.7
            'high': eps * growth_rate * 100 * 1.3,  # PEG=1.3
        }
        self.results['PEG'] = result
        return result

    # ================================================================
    # 方法4：PS估值
    # ================================================================
    def ps_valuation(self):
        sps = self.data.get('sps', 0)  # 每股营收
        ps_ratio = self.data.get('ps_ratio', 2.0)

        result = {
            'method': 'PS估值',
            'sps': sps,
            'ps_ratio': ps_ratio,
            'fair_value': sps * ps_ratio,
            'low': sps * ps_ratio * 0.7,
            'high': sps * ps_ratio * 1.5,
        }
        self.results['PS'] = result
        return result

    # ================================================================
    # 方法5：EV/EBITDA估值
    # ================================================================
    def ev_ebitda_valuation(self):
        ebitda = self.data.get('ebitda', 0)  # 亿元
        total_shares = self.data.get('total_shares', 0)  # 亿股
        net_debt = self.data.get('net_debt', 0)  # 净债务=有息负债-现金（亿元）
        ev_ebitda_ratio = self.data.get('ev_ebitda_ratio', 10)

        fair_ev = ebitda * ev_ebitda_ratio
        fair_market_cap = fair_ev - net_debt  # 市值 = EV - 净债务
        fair_price = fair_market_cap / total_shares if total_shares > 0 else 0

        result = {
            'method': 'EV/EBITDA估值',
            'ebitda': ebitda,
            'target_ratio': ev_ebitda_ratio,
            'fair_ev': fair_ev,
            'fair_price': fair_price,
            'low': (ebitda * ev_ebitda_ratio * 0.7 - net_debt) / total_shares,
            'high': (ebitda * ev_ebitda_ratio * 1.3 - net_debt) / total_shares,
        }
        self.results['EV_EBITDA'] = result
        return result

    # ================================================================
    # 方法6：股息估值(DDM)
    # ================================================================
    def ddm_valuation(self):
        dividend = self.data.get('dividend_per_share', 0)
        growth = self.data.get('dividend_growth', 0.03)
        required_return = self.data.get('required_return', 0.08)

        if required_return <= growth:
            fair_value = dividend / (required_return - growth + 0.01)  # 加保护
        else:
            fair_value = dividend * (1 + growth) / (required_return - growth)

        result = {
            'method': '股息折现(DDM)',
            'dividend': dividend,
            'growth': growth * 100,
            'required_return': required_return * 100,
            'fair_value': fair_value,
            'low': dividend * (1 + growth) / (required_return - growth + 0.02),
            'high': dividend * (1 + growth) / (required_return - growth - 0.01),
        }
        self.results['DDM'] = result
        return result

    # ================================================================
    # 方法7：DCF估值（简化版）
    # ================================================================
    def dcf_valuation(self):
        base_fcf = self.data.get('base_fcf', 0)        # 基准年FCF（亿元）
        total_shares = self.data.get('total_shares', 1)  # 总股本（亿股）
        net_debt = self.data.get('net_debt', 0)           # 净债务（亿元）
        growth_1_5 = self.data.get('dcf_growth_1_5', 0.12)   # 前5年增长率
        growth_6_10 = self.data.get('dcf_growth_6_10', 0.08)  # 第6-10年增长率
        terminal_growth = self.data.get('dcf_terminal_growth', 0.03)  # 永续增长率
        discount_rate = self.data.get('dcf_discount', 0.09)  # 折现率

        # 预测10年FCF
        fcf_projections = []
        current_fcf = base_fcf
        for year in range(1, 11):
            if year <= 5:
                current_fcf *= (1 + growth_1_5)
            else:
                current_fcf *= (1 + growth_6_10)
            fcf_projections.append(current_fcf)

        # 折现
        pv_fcfs = []
        for i, fcf in enumerate(fcf_projections):
            pv = fcf / ((1 + discount_rate) ** (i + 1))
            pv_fcfs.append(pv)

        # 终值
        final_fcf = fcf_projections[-1]
        terminal_value = final_fcf * (1 + terminal_growth) / (discount_rate - terminal_growth)
        pv_terminal = terminal_value / ((1 + discount_rate) ** 10)

        # 企业价值
        enterprise_value = sum(pv_fcfs) + pv_terminal

        # 每股价值
        equity_value = enterprise_value - net_debt
        per_share_value = equity_value / total_shares if total_shares > 0 else 0

        # 敏感性分析
        sensitivity = {}
        disc_range = [discount_rate - 0.02, discount_rate - 0.01, discount_rate,
                      discount_rate + 0.01, discount_rate + 0.02]
        term_range = [terminal_growth - 0.01, terminal_growth, terminal_growth + 0.01]

        for dr in disc_range:
            for tg in term_range:
                if dr <= tg:
                    continue
                # 重算
                pvs = []
                cf = base_fcf
                for yr in range(1, 11):
                    cf *= (1 + growth_1_5) if yr <= 5 else (1 + growth_6_10)
                    pvs.append(cf / ((1 + dr) ** yr))

                tv = cf * (1 + tg) / (dr - tg)
                pv_tv = tv / ((1 + dr) ** 10)
                ev = sum(pvs) + pv_tv
                eq = ev - net_debt
                pv = eq / total_shares
                sensitivity[(f'dr={dr*100:.0f}%', f'g={tg*100:.0f}%')] = pv

        result = {
            'method': 'DCF估值',
            'base_fcf': base_fcf,
            'discount_rate': discount_rate * 100,
            'terminal_growth': terminal_growth * 100,
            'enterprise_value': enterprise_value,
            'equity_value': equity_value,
            'per_share_value': per_share_value,
            'pv_fcfs': sum(pv_fcfs),
            'pv_terminal': pv_terminal,
            'pv_terminal_pct': pv_terminal / enterprise_value * 100,
            'sensitivity': sensitivity,
        }
        self.results['DCF'] = result
        return result

    def print_summary(self, current_price=None):
        """打印估值汇总"""
        print(f"\n{'='*60}")
        print(f"  {self.name} 估值汇总")
        print(f"{'='*60}")

        if current_price:
            print(f"  当前股价: {current_price:.2f}元")

        all_prices = []

        for key, r in self.results.items():
            if key == 'PE':
                print(f"\n  📊 {r['method']}:")
                print(f"     低估: {r['enterprise_value_low']:.1f}元")
                print(f"     合理: {r['enterprise_value_mid']:.1f}元")
                print(f"     高估: {r['enterprise_value_high']:.1f}元")
                all_prices.extend([r['enterprise_value_low'],
                                   r['enterprise_value_mid'],
                                   r['enterprise_value_high']])

            elif key == 'PB':
                print(f"\n  📊 {r['method']}:")
                print(f"     低估: {r['low']:.1f}元")
                print(f"     合理: {r['mid']:.1f}元")
                print(f"     高估: {r['high']:.1f}元")
                all_prices.extend([r['low'], r['mid'], r['high']])

            elif key == 'PEG':
                print(f"\n  📊 {r['method']}:")
                print(f"     增长率: {r['growth_rate']:.1f}%, 目标PEG: {r['target_peg']}")
                print(f"     公允PE: {r['fair_pe']:.1f}倍")
                print(f"     公允股价: {r['fair_value']:.1f}元")
                print(f"     低估-高估: {r['low']:.1f} - {r['high']:.1f}元")
                all_prices.extend([r['low'], r['fair_value'], r['high']])

            elif key == 'PS':
                print(f"\n  📊 {r['method']}:")
                print(f"     每股营收: {r['sps']:.1f}元, PS: {r['ps_ratio']}倍")
                print(f"     公允股价: {r['fair_value']:.1f}元")
                print(f"     低估-高估: {r['low']:.1f} - {r['high']:.1f}元")
                all_prices.extend([r['low'], r['fair_value'], r['high']])

            elif key == 'EV_EBITDA':
                print(f"\n  📊 {r['method']}:")
                print(f"     目标比率: {r['target_ratio']}倍")
                print(f"     公允股价: {r['fair_price']:.1f}元")
                print(f"     低估-高估: {r['low']:.1f} - {r['high']:.1f}元")
                all_prices.extend([r['low'], r['fair_price'], r['high']])

            elif key == 'DDM':
                print(f"\n  📊 {r['method']}:")
                print(f"     分红: {r['dividend']:.2f}元, 要求回报: {r['required_return']:.1f}%")
                print(f"     公允股价: {r['fair_value']:.1f}元")
                all_prices.append(r['fair_value'])

            elif key == 'DCF':
                print(f"\n  📊 {r['method']}:")
                print(f"     折现率: {r['discount_rate']:.1f}%, 永续增长: {r['terminal_growth']:.1f}%")
                print(f"     企业价值: {r['enterprise_value']:,.0f}亿")
                print(f"     每股价值: {r['per_share_value']:.1f}元")
                print(f"     终值占比: {r['pv_terminal_pct']:.1f}%")
                all_prices.append(r['per_share_value'])

                # 显示敏感性矩阵
                g_keys = sorted(set(k[1] for k in r['sensitivity']))
                dr_keys_sorted = sorted(set(k[0] for k in r['sensitivity']))
                if len(g_keys) >= 2 and len(dr_keys_sorted) >= 2:
                    print(f"\n     ┌──────────┬──────────┬──────────┐")
                    header = f"     │ 折现率\\永续│"
                    for gk in g_keys[:3]:
                        header += f" {gk:>8} │"
                    print(header)
                    print(f"     ├──────────┼──────────┼──────────┤")
                    for dr_label in dr_keys_sorted[:5]:
                        row = f"     │ {dr_label:>8} │"
                        for g_key in g_keys[:3]:
                            val = r['sensitivity'].get((dr_label, g_key))
                            if val:
                                row += f" {val:>8.0f} │"
                            else:
                                row += f" {'N/A':>8} │"
                        print(row)
                    print(f"     └──────────┴──────────┴──────────┘")

        # 综合判断
        if current_price and all_prices:
            # 过滤负值（DDM可能在增长率>回报率时产生负值）
            valid_prices = [p for p in all_prices if p > 0]
            if not valid_prices:
                return
            avg_fair = np.mean(valid_prices)
            upside = (avg_fair / current_price - 1) * 100
            low_est = np.min(valid_prices)
            high_est = np.max(valid_prices)

            print(f"\n  {'─'*50}")
            print(f"  🎯 综合判断:")
            print(f"     估值区间: {low_est:.0f} - {high_est:.0f}元")
            print(f"     平均公允价: {avg_fair:.0f}元")
            print(f"     当前价格: {current_price:.0f}元")
            print(f"     潜在空间: {upside:+.1f}%")

            if current_price < low_est:
                print(f"     结论: ✅ 明显低估，有较大安全边际")
            elif current_price < avg_fair * 0.85:
                print(f"     结论: ✅ 合理偏低，有一定安全边际")
            elif current_price < avg_fair * 1.15:
                print(f"     结论: ⚡ 估值合理，取决于你对增长的判断")
            else:
                print(f"     结论: ⚠️  估值偏高，安全边际不足")


# ============================================================
# 案例1：茅台估值
# ============================================================
def value_maotai():
    print(f"\n{'█'*60}")
    print(f"  案例1：贵州茅台 (600519) 估值分析")
    print(f"{'█'*60}")

    data = {
        # PE估值所需
        'eps': 59.5,
        'pe_low': 25,
        'pe_median': 35,
        'pe_high': 45,
        # PB估值所需
        'bvps': 189,
        'pb_low': 6.0,
        'pb_median': 9.0,
        'pb_high': 12.0,
        # PEG估值所需
        'growth_rate': 0.15,
        'peg_target': 1.5,
        # PS估值所需
        'sps': 119.9,
        'ps_ratio': 12,
        # EV/EBITDA所需
        'ebitda': 800,
        'total_shares': 12.56,
        'net_debt': -691,
        'ev_ebitda_ratio': 25,
        # DDM所需
        'dividend_per_share': 25.9,
        'dividend_growth': 0.05,
        'required_return': 0.08,
        # DCF所需
        'base_fcf': 640,
        'dcf_growth_1_5': 0.10,
        'dcf_growth_6_10': 0.07,
        'dcf_terminal_growth': 0.03,
        'dcf_discount': 0.09,
    }

    engine = ValuationEngine('贵州茅台', data)
    engine.pe_valuation()
    engine.pb_valuation()
    engine.peg_valuation()
    engine.ps_valuation()
    engine.ev_ebitda_valuation()
    engine.ddm_valuation()
    engine.dcf_valuation()
    engine.print_summary(current_price=1800)

    return engine


# ============================================================
# 案例2：美的集团估值
# ============================================================
def value_midea():
    print(f"\n{'█'*60}")
    print(f"  案例2：美的集团 (000333) 估值分析")
    print(f"{'█'*60}")

    data = {
        'eps': 4.7,
        'pe_low': 10,
        'pe_median': 15,
        'pe_high': 20,
        'bvps': 25.5,
        'pb_low': 2.0,
        'pb_median': 3.0,
        'pb_high': 4.5,
        'growth_rate': 0.10,
        'peg_target': 1.0,
        'sps': 52.0,
        'ps_ratio': 1.0,
        'ebitda': 500,
        'total_shares': 70.0,
        'net_debt': -300,
        'ev_ebitda_ratio': 10,
        'dividend_per_share': 2.7,
        'dividend_growth': 0.05,
        'required_return': 0.08,
        'base_fcf': 340,
        'dcf_growth_1_5': 0.08,
        'dcf_growth_6_10': 0.05,
        'dcf_terminal_growth': 0.025,
        'dcf_discount': 0.10,
    }

    engine = ValuationEngine('美的集团', data)
    engine.pe_valuation()
    engine.pb_valuation()
    engine.peg_valuation()
    engine.ps_valuation()
    engine.ev_ebitda_valuation()
    engine.ddm_valuation()
    engine.dcf_valuation()
    engine.print_summary(current_price=72)

    return engine


# ============================================================
# 案例3：比亚迪估值
# ============================================================
def value_byd():
    print(f"\n{'█'*60}")
    print(f"  案例3：比亚迪 (002594) 估值分析")
    print(f"{'█'*60}")

    data = {
        'eps': 10.2,
        'pe_low': 15,
        'pe_median': 25,
        'pe_high': 40,
        'bvps': 65.0,
        'pb_low': 2.5,
        'pb_median': 4.0,
        'pb_high': 6.0,
        'growth_rate': 0.25,
        'peg_target': 0.8,
        'sps': 207.0,
        'ps_ratio': 1.2,
        'ebitda': 650,
        'total_shares': 29.0,
        'net_debt': 100,
        'ev_ebitda_ratio': 12,
        'dividend_per_share': 0.3,
        'dividend_growth': 0.20,
        'required_return': 0.10,
        'base_fcf': 130,
        'dcf_growth_1_5': 0.20,
        'dcf_growth_6_10': 0.10,
        'dcf_terminal_growth': 0.03,
        'dcf_discount': 0.11,
    }

    engine = ValuationEngine('比亚迪', data)
    engine.pe_valuation()
    engine.pb_valuation()
    engine.peg_valuation()
    engine.ps_valuation()
    engine.ev_ebitda_valuation()
    engine.ddm_valuation()
    engine.dcf_valuation()
    engine.print_summary(current_price=265)

    return engine


# ============================================================
# 可视化
# ============================================================

def plot_valuation_summary(engines, current_prices):
    """三家公司的估值区间对比"""
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    colors = ['#E74C3C', '#3498DB', '#2ECC71']

    for i, (engine, price) in enumerate(zip(engines, current_prices)):
        ax = axes[i]

        # 收集各方法的估值
        pairs = []  # (label, value)
        for key, r in engine.results.items():
            if key == 'PE':
                pairs.append(('PE', r['enterprise_value_mid']))
                ax.errorbar(0, r['enterprise_value_mid'],
                           yerr=[[r['enterprise_value_mid']-r['enterprise_value_low']],
                                 [r['enterprise_value_high']-r['enterprise_value_mid']]],
                           fmt='o', color=colors[i], capsize=5, markersize=8)
            elif key == 'PB':
                pairs.append(('PB', r['mid']))
            elif key == 'PEG':
                pairs.append(('PEG', r['fair_value']))
            elif key == 'DCF':
                pairs.append(('DCF', r['per_share_value']))
            elif key == 'DDM':
                pairs.append(('DDM', r['fair_value']))
            elif key == 'EV_EBITDA':
                pairs.append(('EV/EBITDA', r['fair_price']))

        # 柱状图
        labels = [p[0] for p in pairs]
        values = [p[1] for p in pairs]

        bars = ax.bar(range(len(labels)), values, color=colors[i], alpha=0.7)
        ax.axhline(y=price, color='black', linewidth=2, linestyle='--',
                   label=f'当前股价 {price:.0f}元')

        # 标注
        for bar, val in zip(bars, values):
            diff = (val / price - 1) * 100
            color_diff = '#2ECC71' if diff > 0 else '#E74C3C'
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values)*0.02,
                   f'{val:.0f}\n({diff:+.0f}%)',
                   ha='center', fontsize=8, color=color_diff, fontweight='bold')

        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, fontsize=9)
        ax.set_title(f'{engine.name}\n(当前{price}元)', fontsize=12, fontweight='bold')
        ax.legend(loc='lower right', fontsize=8)
        ax.grid(True, alpha=0.3, axis='y')

    plt.suptitle('三种估值方法对比：茅台 vs 美的 vs 比亚迪',
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(os.path.dirname(__file__), 'valuation_summary.png'),
                dpi=150, bbox_inches='tight')
    plt.close()
    print("✅ 图表已生成: valuation_summary.png")


def plot_dcf_sensitivity(engine, name):
    """DCF敏感性热力图"""
    if 'DCF' not in engine.results:
        return

    sens = engine.results['DCF']['sensitivity']

    # 提取网格
    dr_keys = sorted(set(k[0] for k in sens))
    g_keys = sorted(set(k[1] for k in sens))

    # 构建矩阵
    matrix = np.zeros((len(dr_keys), len(g_keys)))
    for i, dr in enumerate(dr_keys):
        for j, g in enumerate(g_keys):
            matrix[i, j] = sens.get((dr, g), np.nan)

    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(matrix, cmap='RdYlGn', aspect='auto')

    ax.set_xticks(range(len(g_keys)))
    ax.set_xticklabels(g_keys, fontsize=10)
    ax.set_yticks(range(len(dr_keys)))
    ax.set_yticklabels(dr_keys, fontsize=10)
    ax.set_xlabel('永续增长率', fontsize=12)
    ax.set_ylabel('折现率', fontsize=12)
    ax.set_title(f'{name} DCF敏感性分析（每股价值，元）', fontsize=13, fontweight='bold')

    # 标注数值
    for i in range(len(dr_keys)):
        for j in range(len(g_keys)):
            text = ax.text(j, i, f'{matrix[i, j]:.0f}',
                          ha='center', va='center',
                          fontsize=11, fontweight='bold',
                          color='black' if 0.3 < matrix[i, j]/np.nanmax(matrix) < 0.7 else 'white')

    plt.colorbar(im, ax=ax, label='每股价值（元）')
    plt.tight_layout()
    plt.savefig(os.path.join(os.path.dirname(__file__), 'dcf_sensitivity.png'),
                dpi=150, bbox_inches='tight')
    plt.close()
    print("✅ 图表已生成: dcf_sensitivity.png")


def plot_valuation_methods_comparison():
    """7种估值方法对比 """
    methods = ['PE', 'PB', 'PEG', 'PS', 'EV/EBITDA', 'DDM', 'DCF']
    applicability = {
        '盈利稳定公司': [5, 3, 4, 3, 4, 4, 5],
        '银行/保险':     [2, 5, 2, 1, 3, 4, 4],
        '成长型公司':     [3, 2, 5, 4, 3, 1, 4],
        '亏损公司':       [0, 2, 0, 4, 3, 0, 4],
        '重资产公司':     [3, 5, 2, 2, 5, 3, 4],
        '高分红的公司':    [3, 3, 2, 2, 3, 5, 3],
    }

    fig, ax = plt.subplots(figsize=(14, 6))
    x = np.arange(len(methods))
    width = 0.12
    colors = ['#E74C3C', '#3498DB', '#2ECC71', '#F39C12', '#9B59B6', '#1ABC9C']

    for i, (label, scores) in enumerate(applicability.items()):
        bars = ax.bar(x + i * width - 0.3, scores, width, label=label, alpha=0.8, color=colors[i])
        for bar, score in zip(bars, scores):
            if score > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                       str(score), ha='center', fontsize=7)

    ax.set_xticks(x)
    ax.set_xticklabels(methods, fontsize=11)
    ax.set_ylabel('适用性评分 (0=不适用, 5=最适用)', fontsize=11)
    ax.set_title('估值方法适用范围矩阵', fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', frameon=True, fontsize=9, ncol=2)
    ax.set_ylim(0, 6)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(os.path.join(os.path.dirname(__file__), 'valuation_methods_matrix.png'),
                dpi=150, bbox_inches='tight')
    plt.close()
    print("✅ 图表已生成: valuation_methods_matrix.png")


if __name__ == '__main__':
    print("=" * 60)
    print("  第六课实战代码：估值方法大全")
    print("=" * 60)

    # 三家公司的估值分析
    e1 = value_maotai()
    e2 = value_midea()
    e3 = value_byd()

    # 可视化
    print(f"\n📊 生成图表...")
    engines = [e1, e2, e3]
    prices = [1800, 72, 265]
    plot_valuation_summary(engines, prices)
    plot_dcf_sensitivity(e1, '茅台')
    plot_valuation_methods_comparison()

    # 自定义估值练习
    print(f"\n{'='*60}")
    print(f"  💡 自定义估值练习")
    print(f"{'='*60}")
    print(f"")
    print(f"  使用方法：")
    print(f"  1. 复制上面的任意一个案例（如 value_maotai）")
    print(f"  2. 把数据替换成你想估值的公司")
    print(f"  3. 运行，观察结果")
    print(f"")
    print(f"  关键数据获取渠道：")
    print(f"  · EPS/PB/分红 → 同花顺/东方财富F10 → 财务分析")
    print(f"  · 历史PE/PB分位 → 雪球/理杏仁")
    print(f"  · 增长率预测 → 券商研报（注意是参考，不是事实）")

    print(f"\n{'='*60}")
    print("✅ 所有估值分析完成！")
    print("\n📝 课后练习提示：")
    print("  1. 选一家你关注池里的公司，用PE估值法估算合理价格")
    print("  2. 用DCF敏感性分析，看估值对假设的敏感程度")
    print("  3. 对比至少3种估值方法的结果，如果差异很大→思考为什么")
    print("  4. 问问自己：如果估值需要20%的安全边际，我应该以什么价格买入？")
