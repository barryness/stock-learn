"""
第十课配套实战代码：个人投资管理系统
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
from datetime import datetime, timedelta
import json
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
# 1. 投资组合管理
# ============================================================

class PortfolioManager:
    """个人投资组合管理器"""

    def __init__(self, name="我的投资组合", initial_cash=0):
        self.name = name
        self.cash = initial_cash
        self.holdings = {}  # {ticker: {'shares': x, 'avg_cost': y}}
        self.history = []   # [{date, total_value, holdings_value, cash, ...}]
        self.transactions = []

    def deposit(self, amount, date=None):
        self.cash += amount
        if date:
            self._record(date, 'deposit', amount)

    def buy(self, ticker, shares, price, date=None):
        cost = shares * price * 1.0003  # 手续费
        if cost > self.cash:
            print(f"  [警告] 现金不足！需要{cost:.2f}，可用{self.cash:.2f}")
            return False

        self.cash -= cost
        if ticker in self.holdings:
            old = self.holdings[ticker]
            total_shares = old['shares'] + shares
            old_cost = old['shares'] * old['avg_cost']
            new_cost = shares * price * 1.0003
            self.holdings[ticker] = {
                'shares': total_shares,
                'avg_cost': (old_cost + new_cost) / total_shares
            }
        else:
            self.holdings[ticker] = {
                'shares': shares,
                'avg_cost': price * 1.0003
            }

        self.transactions.append({
            'date': date or 'today', 'action': 'BUY', 'ticker': ticker,
            'shares': shares, 'price': price, 'total': cost
        })
        if date:
            self._record(date, 'buy', ticker)
        return True

    def sell(self, ticker, shares, price, date=None):
        if ticker not in self.holdings:
            print(f"  [错误] 未持有 {ticker}")
            return False
        if shares > self.holdings[ticker]['shares']:
            print(f"  [警告] 持仓不足！持有{self.holdings[ticker]['shares']}，卖出{shares}")
            return False

        value = shares * price * (1 - 0.0003 - 0.001)  # 手续费+印花税
        self.cash += value
        self.holdings[ticker]['shares'] -= shares
        if self.holdings[ticker]['shares'] <= 0.001:
            del self.holdings[ticker]

        self.transactions.append({
            'date': date or 'today', 'action': 'SELL', 'ticker': ticker,
            'shares': shares, 'price': price, 'total': value
        })
        if date:
            self._record(date, 'sell', ticker)
        return True

    def update_prices(self, prices, date):
        """更新当日的持仓市值"""
        holdings_value = 0
        details = {}
        for ticker, h in self.holdings.items():
            if ticker in prices:
                mv = h['shares'] * prices[ticker]
                cost = h['shares'] * h['avg_cost']
                pnl = mv - cost
                pnl_pct = (mv / cost - 1) * 100 if cost > 0 else 0
                holdings_value += mv
                details[ticker] = {
                    'shares': h['shares'],
                    'price': prices[ticker],
                    'market_value': mv,
                    'cost': cost,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'weight': 0
                }

        total = self.cash + holdings_value
        for t in details:
            details[t]['weight'] = details[t]['market_value'] / total * 100 if total > 0 else 0

        record = {
            'date': date,
            'total_value': total,
            'cash': self.cash,
            'holdings_value': holdings_value,
            'details': details,
        }
        self.history.append(record)
        return record

    def _record(self, date, event_type, ticker=None):
        """记录历史"""
        pass  # update_prices会记录完整信息

    def current_allocation(self):
        """返回当前配置比例"""
        if not self.history:
            return {}
        last = self.history[-1]
        alloc = {'现金': last['cash'] / last['total_value'] * 100 if last['total_value'] > 0 else 100}
        for t, d in last['details'].items():
            alloc[t] = d['weight']
        return alloc

    def get_total_value(self):
        if not self.history:
            return self.cash
        return self.history[-1]['total_value']

    def print_summary(self, prices):
        """打印组合摘要"""
        record = self.update_prices(prices, 'today')
        print(f"\n  {'='*50}")
        print(f"  {self.name} — 投资组合摘要")
        print(f"  {'='*50}")
        print(f"  总资产：{record['total_value']:>12,.0f} 元")
        print(f"  现金：  {record['cash']:>12,.0f} 元 ({record['cash']/record['total_value']*100:.1f}%)")
        print(f"  持仓市值：{record['holdings_value']:>10,.0f} 元")
        print(f"\n  {'标的':<14s} {'持仓(份)':>10s} {'现价':>8s} {'市值':>12s} {'盈亏':>12s} {'占比':>6s}")
        print(f"  {'-'*14} {'-'*10} {'-'*8} {'-'*12} {'-'*12} {'-'*6}")

        for ticker, d in sorted(record['details'].items(), key=lambda x: x[1]['weight'], reverse=True):
            print(f"  {ticker:<14s} {d['shares']:>10,.0f} {d['price']:>8.2f} "
                  f"{d['market_value']:>11,.0f}  {d['pnl']:>+11,.0f} {d['weight']:>5.1f}%")

        print(f"  {'现金':<14s} {'':>10s} {'':>8s} {record['cash']:>11,.0f}  {'':>12s} "
              f"{record['cash']/record['total_value']*100:>5.1f}%")

        return record


# ============================================================
# 2. 再平衡计算器
# ============================================================

class RebalancingCalculator:
    """再平衡计算器"""

    def __init__(self, current_values, target_weights):
        """
        current_values: {'asset_A': 60000, 'asset_B': 40000}
        target_weights: {'asset_A': 0.60, 'asset_B': 0.40}
        """
        self.current = current_values
        self.targets = target_weights
        self.total = sum(current_values.values())

    def analyze(self, threshold=0.05):
        """分析是否需要再平衡"""
        results = []
        for asset, target_w in self.targets.items():
            current_w = self.current.get(asset, 0) / self.total if self.total > 0 else 0
            deviation = current_w - target_w
            needs_action = abs(deviation) > threshold
            results.append({
                'asset': asset,
                'current_value': self.current.get(asset, 0),
                'current_weight': current_w,
                'target_weight': target_w,
                'target_value': self.total * target_w,
                'deviation': deviation,
                'adjustment': self.total * target_w - self.current.get(asset, 0),
                'needs_action': needs_action,
            })

        total_deviation = sum(abs(r['deviation']) for r in results) / 2
        return {
            'total_value': self.total,
            'total_deviation': total_deviation,
            'needs_rebalance': total_deviation > threshold,
            'details': results,
        }

    def print_plan(self, threshold=0.05):
        analysis = self.analyze(threshold)

        print(f"\n  {'='*50}")
        print(f"  再平衡分析 (阈值: {threshold:.0%})")
        print(f"  {'='*50}")
        print(f"  组合总值：{analysis['total_value']:,.0f} 元")
        print(f"  总偏离度：{analysis['total_deviation']:.2%}")

        if not analysis['needs_rebalance']:
            print(f"  结论：偏离在阈值内，无需再平衡")
            return analysis

        print(f"  结论：需要再平衡！")
        print(f"\n  {'资产':<14s} {'当前':>10s} {'目标':>8s} {'偏离':>8s} {'操作':>12s}")
        print(f"  {'-'*14} {'-'*10} {'-'*8} {'-'*8} {'-'*12}")

        for r in analysis['details']:
            adj = r['adjustment']
            if abs(adj) < 1:
                action = "— 不变"
            elif adj > 0:
                action = f"买入 {adj:.0f}元"
            else:
                action = f"卖出 {abs(adj):.0f}元"

            marker = " ⚠" if r['needs_action'] else ""
            print(f"  {r['asset']:<14s} {r['current_weight']:>9.1%} {r['target_weight']:>7.1%} "
                  f"{r['deviation']:>+7.1%}{marker:<2s} {action:>12s}")

        return analysis


# ============================================================
# 3. 投资清单工具
# ============================================================

class InvestmentChecklist:
    """投资决策清单"""

    def __init__(self):
        self.buy_checklist = [
            ('标的类型', '是指数基金/ETF吗？', 'type_check'),
            ('PE分位', 'PE在历史分位30%以下？', 'pe_check'),
            ('ROE检查', 'ROE > 12%？', 'roe_check'),
            ('现金流', '经营性现金流 > 净利润？', 'cashflow_check'),
            ('趋势检查', '价格在MA60以上？', 'trend_check'),
            ('RSI检查', 'RSI(14) < 70？', 'rsi_check'),
            ('仓位上限', '买入后单标的不超过总资产上限？', 'position_check'),
            ('心理检查1', '不是因为"怕踏空"而买入？', 'fomo_check'),
            ('心理检查2', '不是因为"听消息"而买入？', 'news_check'),
            ('心理检查3', '已想好跌20%的应对方案？', 'plan_check'),
        ]

        self.sell_checklist = [
            ('重大坏消息', '公司是否财务造假/被立案调查？', 'fraud_check'),
            ('逻辑破坏', '核心投资逻辑是否被破坏？', 'logic_check'),
            ('触发止损', '是否已触发止损线？', 'stop_check'),
            ('估值过高', 'PE是否超过历史分位80%？', 'overvalued_check'),
            ('技术恶化', '价格跌破MA60+MACD死叉？', 'tech_bad_check'),
            ('基本面恶化', 'ROE连续2季度大幅下降？', 'fundamentals_check'),
        ]

    def run_checklist(self, checklist_type='buy', context=None):
        """运行清单检查"""
        checklist = self.buy_checklist if checklist_type == 'buy' else self.sell_checklist
        title = "买入决策清单" if checklist_type == 'buy' else "卖出决策清单"

        print(f"\n  {'='*50}")
        print(f"  {title}")
        print(f"  {'='*50}")

        if context:
            for k, v in context.items():
                print(f"  {k}: {v}")

        print(f"\n  逐条检查：")

        passed = 0
        failed = []
        total = len(checklist)

        for category, question, key in checklist:
            # 模拟回答（实际使用中可交互）
            result = self._auto_check(key, context)
            status = '✅' if result else '❌'
            if result:
                passed += 1
            else:
                failed.append(question)
            print(f"  [{status}] ({category}) {question}")

        score = passed / total * 100
        print(f"\n  📊 结果：{passed}/{total} 通过 ({score:.0f}%)")

        if checklist_type == 'buy':
            if passed >= total - 1:
                print(f"  ✅ 可以买入（建议标准仓位）")
            elif passed >= total - 3:
                print(f"  ⚠️ 条件不完全满足，建议减半仓位或观望")
            else:
                print(f"  ❌ 不建议买入，等待更好时机")
        else:
            if passed >= total - 1:
                print(f"  ✅ 满足多项卖出条件，建议执行卖出")
            elif passed >= total - 3:
                print(f"  ⚠️ 谨慎考虑卖出")
            else:
                print(f"  ✅ 暂不需要卖出")

        return {'passed': passed, 'total': total, 'score': score, 'failed': failed}

    def _auto_check(self, key, context):
        """自动检查（基于context数据）"""
        if context is None:
            return True  # 无数据时默认通过
        checks = {
            'pe_check': lambda c: c.get('pe', 100) < c.get('pe_70th', 50),
            'roe_check': lambda c: c.get('roe', 0) > 0.12,
            'cashflow_check': lambda c: c.get('ocf', 0) > c.get('net_profit', 0),
            'position_check': lambda c: c.get('after_weight', 0) < c.get('max_weight', 20),
            'type_check': lambda c: True,  # 需主观判断
            'trend_check': lambda c: c.get('above_ma60', False),
            'rsi_check': lambda c: c.get('rsi', 50) < 70,
            'fomo_check': lambda c: True,
            'news_check': lambda c: True,
            'plan_check': lambda c: True,
            'fraud_check': lambda c: not c.get('fraud_risk', False),
            'logic_check': lambda c: not c.get('logic_broken', False),
            'stop_check': lambda c: c.get('hit_stop', False),
            'overvalued_check': lambda c: c.get('pe', 15) < c.get('pe_20th', 30) * 1.5,
            'tech_bad_check': lambda c: not (not c.get('above_ma60', True) and c.get('macd_death', False)),
            'fundamentals_check': lambda c: not c.get('roe_declining', False),
        }
        check_fn = checks.get(key, lambda c: True)
        return check_fn(context)


# ============================================================
# 4. 年度复盘报告生成器
# ============================================================

class AnnualReview:
    """年度投资复盘"""

    def __init__(self, portfolio_manager, year, benchmark_return=0):
        self.pm = portfolio_manager
        self.year = year
        self.benchmark_return = benchmark_return

    def generate_report(self, monthly_deposits=0):
        """生成年度复盘报告"""
        history = self.pm.history
        if not history:
            print("  暂无投资记录")
            return

        # 筛选年度数据
        year_start = None
        year_end = None
        for i, record in enumerate(history):
            date_str = record['date']
            if str(self.year) in str(date_str):
                if year_start is None:
                    year_start = i
                year_end = i

        if year_start is None:
            print(f"  {self.year}年暂无记录")
            return

        start_val = history[year_start]['total_value']
        end_val = history[year_end]['total_value'] if year_end is not None else start_val

        total_deposits = monthly_deposits * 12
        investment_return = end_val - start_val - total_deposits
        avg_capital = start_val + total_deposits / 2
        return_rate = (investment_return / avg_capital * 100) if avg_capital > 0 else 0

        print(f"\n  {'='*60}")
        print(f"  {self.year}年度投资复盘报告")
        print(f"  {'='*60}")

        print(f"\n  📊 收益回顾：")
        print(f"    年初总资产：{start_val:>12,.0f} 元")
        print(f"    年末总资产：{end_val:>12,.0f} 元")
        print(f"    年度新增投入：{total_deposits:>10,.0f} 元")
        print(f"    年度投资收益：{investment_return:>10,.0f} 元")
        print(f"    年度收益率：  {return_rate:>10.2f}%")
        print(f"    基准收益（沪深300）：{self.benchmark_return*100:>6.2f}%")
        excess = return_rate / 100 - self.benchmark_return
        print(f"    超额收益：    {excess*100:>+10.2f}%")

        # 分项收益
        if year_end is not None:
            print(f"\n  📈 持仓明细：")
            details = history[year_end].get('details', {})
            for ticker, d in details.items():
                pnl_pct = d.get('pnl_pct', 0)
                print(f"    {ticker:<14s} 市值{d['market_value']:>10,.0f}  盈亏{pnl_pct:>+6.1f}%  占比{d['weight']:>5.1f}%")

        # 交易统计
        year_trades = [t for t in self.pm.transactions if str(self.year) in str(t.get('date', ''))]
        buys = [t for t in year_trades if t['action'] == 'BUY']
        sells = [t for t in year_trades if t['action'] == 'SELL']
        print(f"\n  📋 交易统计：")
        print(f"    总交易次数：{len(year_trades)} 笔")
        print(f"    买入：{len(buys)} 笔    卖出：{len(sells)} 笔")

        if monthly_deposits > 0:
            print(f"\n  💰 定投执行：")
            print(f"    月定投金额：{monthly_deposits:,.0f} 元")
            print(f"    年度定投总额：{total_deposits:,.0f} 元")
            print(f"    定投占新增投入：100%")

        # 综合评分
        print(f"\n  🏆 年度综合评估：")
        ratings = []
        if return_rate > 8:
            ratings.append("收益达标（>8%）")
        if excess > 0:
            ratings.append("跑赢基准")
        if year_end is not None and history[year_end]['cash'] / end_val < 0.3:
            ratings.append("资金利用率高")
        if len(year_trades) < 20:
            ratings.append("交易频率合理")

        if ratings:
            for r in ratings:
                print(f"    ✅ {r}")
        else:
            print(f"    ⚠️ 有改进空间，请检查各项指标")

        return {
            'start_val': start_val,
            'end_val': end_val,
            'return_rate': return_rate,
            'excess': excess,
            'trade_count': len(year_trades),
        }


# ============================================================
# 5. 财务目标规划器
# ============================================================

class GoalPlanner:
    """财务目标规划器"""

    def __init__(self, age, current_savings, monthly_save, annual_return=0.08):
        self.age = age
        self.current = current_savings
        self.monthly = monthly_save
        self.annual_return = annual_return

    def project(self, years=30):
        """预测资产增长"""
        months = years * 12
        monthly_r = self.annual_return / 12
        values = []
        current = self.current

        for m in range(months + 1):
            values.append(current)
            current = current * (1 + monthly_r) + self.monthly

        return np.array(values)

    def time_to_goal(self, goal_amount):
        """计算达到目标需要的时间"""
        monthly_r = self.annual_return / 12
        current = self.current
        months = 0
        values = []

        while current < goal_amount and months < 1200:  # 最多100年
            values.append(current)
            current = current * (1 + monthly_r) + self.monthly
            months += 1

        return months, np.array(values)

    def required_monthly(self, goal_amount, years):
        """计算达成目标需要的月投入"""
        months = years * 12
        monthly_r = self.annual_return / 12
        # FV = PV*(1+r)^n + PMT*((1+r)^n-1)/r
        fv_pv = self.current * (1 + monthly_r) ** months
        remaining = goal_amount - fv_pv
        if remaining <= 0:
            return 0
        pmt = remaining * monthly_r / ((1 + monthly_r) ** months - 1)
        return pmt

    def print_plan(self):
        print(f"\n  {'='*50}")
        print(f"  财务自由路线图")
        print(f"  {'='*50}")
        print(f"  当前年龄：{self.age} 岁")
        print(f"  现有资产：{self.current:,.0f} 元")
        print(f"  月定投：  {self.monthly:,.0f} 元")
        print(f"  预期年化：{self.annual_return:.0%}")

        projection = self.project(30)
        print(f"\n  📈 资产增长预测：")
        for yr in [5, 10, 15, 20, 25, 30]:
            idx = yr * 12
            val = projection[idx] if idx < len(projection) else projection[-1]
            total_invested = self.current + self.monthly * yr * 12
            gain = val - total_invested
            print(f"    {self.age + yr:>2}岁 ({yr:>2}年后)：{val:>13,.0f} 元 "
                  f"(投入{total_invested:,.0f}, 收益{gain:,.0f})")

        # 目标倒推
        goals = [
            (1000000, "第一个100万"),
            (5000000, "500万（财务安全）"),
            (10000000, "1000万（财务自由）"),
        ]
        print(f"\n  🎯 目标倒推：")
        for goal, desc in goals:
            months, _ = self.time_to_goal(goal)
            yrs = months / 12
            reach_age = self.age + yrs
            print(f"    {desc:<20s} → {reach_age:.1f}岁达到 ({yrs:.1f}年)")

        return projection


# ============================================================
# 6. 演示函数
# ============================================================

def demo_portfolio_management():
    """演示组合管理"""
    print("\n" + "=" * 60)
    print("  个人投资组合管理演示")
    print("=" * 60)

    pm = PortfolioManager(name="演示组合", initial_cash=100000)

    # 建仓
    pm.buy('沪深300ETF', 8000, 3.80, '2025-01-15')
    pm.buy('中证500ETF', 5000, 5.50, '2025-01-15')
    pm.buy('纳指ETF', 3000, 4.20, '2025-02-01')
    pm.buy('债券基金', 10000, 1.05, '2025-03-01')

    # 更新价格并查看
    prices1 = {'沪深300ETF': 4.10, '中证500ETF': 6.00, '纳指ETF': 4.80, '债券基金': 1.08}
    pm.update_prices(prices1, '2025-06-30')
    pm.print_summary(prices1)

    # 再平衡分析
    current = {
        '沪深300ETF': 8000 * 4.10,
        '中证500ETF': 5000 * 6.00,
        '纳指ETF': 3000 * 4.80,
        '债券基金': 10000 * 1.08,
        '现金': pm.cash,
    }
    targets = {'沪深300ETF': 0.30, '中证500ETF': 0.20, '纳指ETF': 0.20, '债券基金': 0.20, '现金': 0.10}

    calc = RebalancingCalculator(current, targets)
    calc.print_plan(threshold=0.05)

    return pm


def demo_checklist():
    """演示投资清单"""
    print("\n" + "=" * 60)
    print("  投资决策清单演示")
    print("=" * 60)

    checklist = InvestmentChecklist()

    # 模拟买入检查
    context = {
        'pe': 18,
        'pe_70th': 30,
        'roe': 0.15,
        'ocf': 120,
        'net_profit': 100,
        'above_ma60': True,
        'rsi': 55,
        'after_weight': 12,
        'max_weight': 20,
    }
    print(f"\n  --- 场景1：一只基本面良好的ETF ---")
    checklist.run_checklist('buy', context)

    print(f"\n  --- 场景2：高估值热门股 ---")
    context2 = {
        'pe': 55,
        'pe_70th': 30,
        'roe': 0.08,
        'ocf': 30,
        'net_profit': 100,
        'above_ma60': True,
        'rsi': 82,
        'after_weight': 15,
        'max_weight': 20,
    }
    checklist.run_checklist('buy', context2)


def demo_annual_review():
    """演示年度复盘"""
    print("\n" + "=" * 60)
    print("  年度投资复盘演示")
    print("=" * 60)

    # 模拟全年数据
    pm = PortfolioManager(name="年度复盘演示", initial_cash=50000)

    months = ['2025-{:02d}-15'.format(m) for m in range(1, 13)]
    prices_seq = [
        {'沪深300ETF': 3.80, '纳指ETF': 4.00},
        {'沪深300ETF': 3.90, '纳指ETF': 4.10},
        {'沪深300ETF': 3.70, '纳指ETF': 3.90},
        {'沪深300ETF': 3.85, '纳指ETF': 4.20},
        {'沪深300ETF': 4.00, '纳指ETF': 4.40},
        {'沪深300ETF': 4.05, '纳指ETF': 4.50},
        {'沪深300ETF': 3.95, '纳指ETF': 4.60},
        {'沪深300ETF': 4.10, '纳指ETF': 4.55},
        {'沪深300ETF': 4.20, '纳指ETF': 4.70},
        {'沪深300ETF': 4.15, '纳指ETF': 4.90},
        {'沪深300ETF': 4.30, '纳指ETF': 5.00},
        {'沪深300ETF': 4.40, '纳指ETF': 5.20},
    ]

    for i, month in enumerate(months):
        pm.deposit(5000, month)
        pm.buy('沪深300ETF', 800, prices_seq[i]['沪深300ETF'], month)
        pm.buy('纳指ETF', 500, prices_seq[i]['纳指ETF'], month)
        pm.update_prices(prices_seq[i], month)

    # 沪深300全年收益约15.8%（3.80 → 4.40）
    review = AnnualReview(pm, 2025, benchmark_return=0.158)
    review.generate_report(monthly_deposits=5000)


def demo_goal_planner():
    """演示目标规划"""
    print("\n" + "=" * 60)
    print("  财务目标规划演示")
    print("=" * 60)

    planner = GoalPlanner(age=30, current_savings=200000, monthly_save=8000, annual_return=0.08)
    planner.print_plan()

    # 达到500万需要的月投入
    req = planner.required_monthly(5000000, 20)
    print(f"\n  💡 如果要在50岁前达到500万：")
    print(f"    需要月投入：{req:,.0f} 元")


# ============================================================
# 7. 可视化
# ============================================================

def plot_portfolio_dashboard(pm):
    """绘制组合仪表盘"""
    if not pm.history:
        print("  无数据可绘制")
        return

    history = pm.history
    dates = [h['date'] for h in history]
    total_values = [h['total_value'] for h in history]
    cash_values = [h['cash'] for h in history]
    holdings_values = [h['holdings_value'] for h in history]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 图1：总资产增长
    ax = axes[0, 0]
    x = range(len(dates))
    ax.fill_between(x, 0, total_values, alpha=0.15, color='#2E86AB')
    ax.plot(x, total_values, linewidth=2, color='#2E86AB', label='总资产')
    ax.plot(x, holdings_values, linewidth=1.5, color='#A23B72', label='持仓市值')
    ax.plot(x, cash_values, linewidth=1, color='#F39C12', alpha=0.7, label='现金')
    ax.set_xlabel('时间')
    ax.set_ylabel('金额 (元)')
    ax.set_title('资产增长曲线')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    if len(dates) > 10:
        tick_idx = np.linspace(0, len(dates) - 1, min(8, len(dates)), dtype=int)
        ax.set_xticks(tick_idx)
        ax.set_xticklabels([dates[i] for i in tick_idx], fontsize=7, rotation=30)

    # 图2：当前配置饼图
    ax = axes[0, 1]
    if history:
        last = history[-1]
        labels = []
        sizes = []
        colors_pie = []
        pie_colors = ['#2E86AB', '#A23B72', '#F18F01', '#3B1F2B', '#C73E1D',
                       '#6DA34D', '#8E44AD', '#F39C12', '#1ABC9C', '#E74C3C']
        for i, (ticker, d) in enumerate(sorted(last['details'].items(),
                                                key=lambda x: x[1]['weight'], reverse=True)):
            if d['weight'] > 0.5:
                labels.append(f"{ticker}\n({d['weight']:.1f}%)")
                sizes.append(d['weight'])
                colors_pie.append(pie_colors[i % len(pie_colors)])
        cash_w = last['cash'] / last['total_value'] * 100 if last['total_value'] > 0 else 0
        if cash_w > 0.5:
            labels.append(f"现金\n({cash_w:.1f}%)")
            sizes.append(cash_w)
            colors_pie.append('#BDC3C7')
        if sizes:
            ax.pie(sizes, labels=labels, colors=colors_pie, autopct='',
                    startangle=90, textprops={'fontsize': 8})
        ax.set_title('当前资产配置')

    # 图3：持仓盈亏柱状图
    ax = axes[1, 0]
    if history:
        last = history[-1]
        tickers = list(last['details'].keys())
        pnls = [last['details'][t]['pnl_pct'] for t in tickers]
        colors_bar = ['#A23B72' if p >= 0 else '#2E86AB' for p in pnls]
        bars = ax.barh(tickers, pnls, color=colors_bar, alpha=0.8)
        ax.axvline(x=0, color='gray', linewidth=0.5)
        ax.set_xlabel('盈亏 (%)')
        ax.set_title('持仓盈亏明细')
        ax.grid(True, alpha=0.3, axis='x')
        for bar, pnl in zip(bars, pnls):
            ax.text(bar.get_width() + (0.5 if pnl >= 0 else -2.5),
                     bar.get_y() + bar.get_height() / 2,
                     f'{pnl:+.1f}%', va='center', fontsize=9, fontweight='bold')

    # 图4：资产配置 vs 目标
    ax = axes[1, 1]
    # 模拟目标配置
    categories = ['权益', '债券', '黄金', '现金']
    current_alloc = [65, 15, 5, 15]
    target_alloc = [60, 25, 5, 10]
    x = np.arange(len(categories))
    width = 0.3
    ax.bar(x - width / 2, current_alloc, width, color='#2E86AB', alpha=0.8, label='当前')
    ax.bar(x + width / 2, target_alloc, width, color='#A23B72', alpha=0.5, label='目标')
    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    ax.set_ylabel('占比 (%)')
    ax.set_title('配置 vs 目标')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'portfolio_dashboard.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] 组合仪表盘已保存: {path}")


def plot_goal_projection(planner):
    """绘制目标规划图"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 图1：资产增长预测
    ax = axes[0]
    projection = planner.project(30)
    years = np.arange(0, 30.1, 1 / 12)
    if len(years) > len(projection):
        years = years[:len(projection)]
    elif len(projection) > len(years):
        projection = projection[:len(years)]

    ax.fill_between(years, 0, projection / 10000, alpha=0.15, color='#2E86AB')
    ax.plot(years, projection / 10000, linewidth=2, color='#2E86AB')

    # 标注总投入
    total_invested = [planner.current + planner.monthly * y * 12 for y in years]
    if len(total_invested) > len(years):
        total_invested = total_invested[:len(years)]
    elif len(years) > len(total_invested):
        years2 = years[:len(total_invested)]
    else:
        years2 = years
    ax.fill_between(years2[:len(total_invested)], 0, np.array(total_invested) / 10000,
                     alpha=0.1, color='#A23B72')
    ax.plot(years2[:len(total_invested)], np.array(total_invested) / 10000,
             linewidth=1, color='#A23B72', linestyle='--', alpha=0.7, label='总投入')

    ax.set_xlabel('年数')
    ax.set_ylabel('资产 (万元)')
    ax.set_title(f'资产增长预测 (年化{planner.annual_return:.0%})')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    # 图2：达到不同目标的时间
    ax = axes[1]
    goals = [1000000, 3000000, 5000000, 10000000]
    goal_labels = ['100万', '300万', '500万', '1000万']
    times = []
    for goal in goals:
        months, _ = planner.time_to_goal(goal)
        times.append(months / 12)

    colors = ['#2E86AB', '#F18F01', '#A23B72', '#3B1F2B']
    bars = ax.barh(goal_labels, times, color=colors, alpha=0.85)
    for bar, t in zip(bars, times):
        ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height() / 2,
                 f'{t:.1f}年 ({planner.age + t:.0f}岁)', va='center', fontsize=11, fontweight='bold')
    ax.set_xlabel('需要年数')
    ax.set_title('达到财务目标的时间')
    ax.grid(True, alpha=0.3, axis='x')

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'goal_projection.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] 目标规划图已保存: {path}")


def plot_system_summary():
    """绘制投资系统全景总结图"""
    fig, ax = plt.subplots(figsize=(16, 9))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')

    # 标题
    ax.text(5, 9.5, '个人投资系统全景图', ha='center', fontsize=20, fontweight='bold')
    ax.text(5, 9.0, '从知识到执行，从零到成熟投资者', ha='center', fontsize=12, color='gray')

    # 五个层次
    layers = [
        {'y': 7.5, 'title': '投资哲学 (Why)', 'items': ['长期主义', '复利思维', '全球配置', '风险意识'], 'color': '#2E86AB'},
        {'y': 5.8, 'title': '分析方法 (What)', 'items': ['基本面分析', '估值体系', '技术分析', '量化回测'], 'color': '#A23B72'},
        {'y': 4.1, 'title': '决策流程 (When & How)', 'items': ['买入清单', '卖出清单', '仓位规则', '极端预案'], 'color': '#F18F01'},
        {'y': 2.4, 'title': '执行纪律 (Do it)', 'items': ['自动定投', '年度再平衡', '净值跟踪', '降低交易频率'], 'color': '#3B1F2B'},
        {'y': 0.7, 'title': '复盘进化 (Improve)', 'items': ['月度检查', '年度复盘', '错误记录', '系统迭代'], 'color': '#6DA34D'},
    ]

    for layer in layers:
        y = layer['y']
        # 层标题
        ax.fill_between([0.2, 9.8], y - 0.3, y + 0.5, alpha=0.08, color=layer['color'])
        ax.text(0.5, y + 0.2, layer['title'], fontsize=14, fontweight='bold', color=layer['color'])

        # 项目
        for i, item in enumerate(layer['items']):
            x = 2.5 + i * 2.0
            ax.fill_between([x - 0.8, x + 0.8], y - 0.15, y + 0.15,
                             color=layer['color'], alpha=0.15)
            ax.text(x, y - 0.05, item, ha='center', fontsize=9, color=layer['color'])

        # 层间箭头
        if y > 0.7:
            ax.annotate('', xy=(0.8, y - 0.3), xytext=(0.8, y - 0.6),
                         arrowprops=dict(arrowstyle='->', color='gray', lw=2))

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, 'investment_system.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图表] 投资系统全景图已保存: {path}")


# ============================================================
# 主程序
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("  第十课实战代码：个人投资管理系统")
    print("=" * 60)

    # 1. 组合管理
    pm = demo_portfolio_management()

    # 2. 投资清单
    demo_checklist()

    # 3. 年度复盘
    demo_annual_review()

    # 4. 目标规划
    demo_goal_planner()

    # 5. 可视化
    plot_portfolio_dashboard(pm)
    planner = GoalPlanner(age=30, current_savings=200000, monthly_save=8000)
    plot_goal_projection(planner)
    plot_system_summary()

    print(f"\n{'=' * 60}")
    print(f"  所有图表已生成到：{OUTPUT_DIR}")
    print(f"{'=' * 60}")
    print(f"\n  🎉 恭喜完成「从零到成熟投资者」全部十课！")
    print(f"  现在，打开你的券商App，开始你的第一笔投资吧。")
    print(f"{'=' * 60}")
