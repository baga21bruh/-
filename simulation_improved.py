import json
from pathlib import Path

import networkx as nx
import pandas as pd
import simpy
import matplotlib.pyplot as plt
import numpy as np

BASE_DIR = Path(__file__).resolve().parent
SPEC_PATH = BASE_DIR / 'model_spec.json'


def load_spec(path=SPEC_PATH):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_graph(spec):
    G = nx.DiGraph()
    for node in spec['nodes']:
        G.add_node(node['id'], **node)
    for edge in spec['edges']:
        G.add_edge(edge['from'], edge['to'], **edge)
    return G


def route_metrics(spec, scenario_name):
    scenario = spec['scenarios'][scenario_name]
    material_edges = [e for e in spec['edges'] if e['flow'] == 'material']

    base_time = sum(e['transit_time_days'] for e in material_edges)
    base_transport_cost = sum(e['transport_cost_per_unit'] for e in material_edges)

    delivery_time = base_time + scenario['hub_delay_days']
    effective_orders_per_day = max(1, int(round(spec['base_parameters']['orders_per_day'] * scenario['hub_capacity_factor'])))

    return {
        'delivery_time': delivery_time,
        'transport_cost_per_unit': base_transport_cost,
        'effective_orders_per_day': effective_orders_per_day,
        'extra_recovery_cost': scenario['extra_recovery_cost'],
    }


def simulate_scenario(spec, scenario_name):
    params = spec['base_parameters']
    metrics = route_metrics(spec, scenario_name)
    env = simpy.Environment()

    stats = {
        'scenario': scenario_name,
        'total_orders': 0,
        'delivered_orders': 0,
        'on_time_orders': 0,
        'revenue': 0.0,
        'transport_costs': 0.0,
        'warehouse_costs': 0.0,
        'purchase_costs': 0.0,
        'penalty_costs': 0.0,
        'recovery_costs': float(metrics['extra_recovery_cost']),
        'delivery_times': [],
    }

    def order_process(order_id, created_day):
        stats['total_orders'] += 1
        units = params['units_per_order']

        yield env.timeout(metrics['delivery_time'])

        stats['delivered_orders'] += 1
        stats['delivery_times'].append(metrics['delivery_time'])

        if metrics['delivery_time'] <= params['late_threshold_days']:
            stats['on_time_orders'] += 1
        else:
            stats['penalty_costs'] += params['penalty_rate_per_late_order']

        stats['revenue'] += units * params['sales_price_per_unit']
        stats['transport_costs'] += units * metrics['transport_cost_per_unit']
        stats['warehouse_costs'] += units * params['warehouse_cost_per_unit']
        stats['purchase_costs'] += units * params['purchase_cost_per_unit']

    def generator(env):
        order_id = 0
        for day in range(params['simulation_days']):
            for _ in range(metrics['effective_orders_per_day']):
                order_id += 1
                env.process(order_process(order_id, day))
            yield env.timeout(1)

    env.process(generator(env))
    env.run(until=params['simulation_days'] + metrics['delivery_time'] + 1)

    on_time_rate = 0 if stats['delivered_orders'] == 0 else stats['on_time_orders'] / stats['delivered_orders']
    avg_delivery_time = 0 if not stats['delivery_times'] else sum(stats['delivery_times']) / len(stats['delivery_times'])
    total_costs = (
        stats['transport_costs']
        + stats['warehouse_costs']
        + stats['purchase_costs']
        + stats['penalty_costs']
        + stats['recovery_costs']
    )
    profit = stats['revenue'] - total_costs

    return {
        'scenario': stats['scenario'],
        'total_orders': stats['total_orders'],
        'delivered_orders': stats['delivered_orders'],
        'on_time_rate': round(on_time_rate, 4),
        'revenue': round(stats['revenue'], 2),
        'transport_costs': round(stats['transport_costs'], 2),
        'warehouse_costs': round(stats['warehouse_costs'], 2),
        'purchase_costs': round(stats['purchase_costs'], 2),
        'penalty_costs': round(stats['penalty_costs'], 2),
        'recovery_costs': round(stats['recovery_costs'], 2),
        'total_costs': round(total_costs, 2),
        'profit': round(profit, 2),
        'average_delivery_time_days': round(avg_delivery_time, 2),
    }


def plot_results(df, output_path):
    scenarios = df['scenario']
    colors = ['#2E8B57', '#B22222', '#1E90FF']

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    axes[0, 0].bar(scenarios, df['profit'], color=colors)
    axes[0, 0].set_title('Прибыль по сценариям')
    axes[0, 0].set_ylabel('руб.')
    axes[0, 0].axhline(0, color='black', linewidth=0.8)

    x = np.arange(len(scenarios))
    width = 0.35
    axes[0, 1].bar(x - width/2, df['revenue'], width, label='Выручка', color='#4CAF50')
    axes[0, 1].bar(x + width/2, df['total_costs'], width, label='Совокупные затраты', color='#FF7043')
    axes[0, 1].set_title('Выручка и затраты')
    axes[0, 1].set_xticks(x)
    axes[0, 1].set_xticklabels(scenarios)
    axes[0, 1].legend()

    axes[1, 0].bar(scenarios, df['on_time_rate'] * 100, color=colors)
    axes[1, 0].set_title('Доля своевременных поставок')
    axes[1, 0].set_ylabel('%')
    axes[1, 0].set_ylim(0, 105)

    axes[1, 1].bar(scenarios, df['average_delivery_time_days'], color=colors)
    axes[1, 1].set_title('Среднее время доставки')
    axes[1, 1].set_ylabel('дней')

    plt.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close(fig)


def main():
    spec = load_spec()

    # Корректировка параметров для более наглядной модели ВКР
    spec['base_parameters']['sales_price_per_unit'] = 145
    spec['base_parameters']['warehouse_cost_per_unit'] = 6
    spec['base_parameters']['penalty_rate_per_late_order'] = 2500

    graph = build_graph(spec)

    print('Узлы сети:', list(graph.nodes))
    print('Связи сети:', list(graph.edges))

    results = []
    for scenario_name in spec['scenarios'].keys():
        result = simulate_scenario(spec, scenario_name)
        results.append(result)

    df = pd.DataFrame(results)
    df['on_time_rate_percent'] = (df['on_time_rate'] * 100).round(2)

    print('\nРезультаты моделирования:')
    print(df.to_string(index=False))

    csv_path = BASE_DIR / 'results_improved.csv'
    png_path = BASE_DIR / 'results_improved.png'

    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    plot_results(df, png_path)

    print(f'\nCSV сохранён: {csv_path.name}')
    print(f'График сохранён: {png_path.name}')


if __name__ == '__main__':
    main()