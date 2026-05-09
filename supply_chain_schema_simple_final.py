import json
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch

BASE_DIR = Path(__file__).resolve().parent
SPEC_PATH = BASE_DIR / 'model_spec.json'

with open(SPEC_PATH, 'r', encoding='utf-8') as f:
    spec = json.load(f)

pos = {
    'supplier': (0.08, 0.62),
    'warehouse': (0.33, 0.62),
    'hub': (0.58, 0.62),
    'client': (0.83, 0.62),
    'bank': (0.5, 0.24),
}

labels = {
    'supplier': 'Поставщик',
    'warehouse': 'Склад',
    'hub': 'Хаб',
    'client': 'Клиент',
    'bank': 'Банк',
}

colors = {
    'supplier': '#3A945B',
    'warehouse': '#5B86B8',
    'hub': '#F28C18',
    'client': '#58A84A',
    'bank': '#E85B5B',
}

fig, ax = plt.subplots(figsize=(14, 7))
fig.patch.set_facecolor('white')
ax.set_facecolor('white')

radius = 0.046
for node, (x, y) in pos.items():
    ax.add_patch(Circle((x, y), radius, facecolor=colors[node], edgecolor='black', linewidth=1.6))
    ax.text(x, y, labels[node], ha='center', va='center', fontsize=14, fontweight='bold')


def arrow(start, end, label, dashed=False, color='#666666', rad=0.0, text_shift=(0, 0)):
    a = FancyArrowPatch(
        start, end,
        arrowstyle='-|>',
        mutation_scale=20,
        linewidth=2.4,
        linestyle='--' if dashed else '-',
        color=color,
        connectionstyle=f'arc3,rad={rad}',
        shrinkA=22,
        shrinkB=22,
    )
    ax.add_patch(a)
    mx = (start[0] + end[0]) / 2 + text_shift[0]
    my = (start[1] + end[1]) / 2 + text_shift[1]
    if label:
        ax.text(mx, my, label, fontsize=12, ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.18', fc='white', ec='none', alpha=0.92))

# Материальный поток
arrow(pos['supplier'], pos['warehouse'], 'товар', color='#444444', text_shift=(0, 0.02))
arrow(pos['warehouse'], pos['hub'], 'товар', color='#444444', text_shift=(0, 0.02))
arrow(pos['hub'], pos['client'], 'товар', color='#444444', text_shift=(0, 0.02))

# Финансовый поток: одна основная стрелка оплаты
arrow(pos['client'], pos['bank'], 'оплата', dashed=True, color='#777777', text_shift=(0.02, -0.015))

# Распределение платежей через банк
arrow(pos['bank'], pos['supplier'], 'расчёты', dashed=True, color='#777777', rad=0.0, text_shift=(-0.06, 0.02))
arrow(pos['bank'], pos['warehouse'], 'расчёты', dashed=True, color='#777777', rad=0.0, text_shift=(-0.02, 0.03))
arrow(pos['bank'], pos['hub'], 'расчёты', dashed=True, color='#777777', rad=0.0, text_shift=(0.02, 0.03))

ax.text(0.5, 0.84, 'Материальный поток', ha='center', fontsize=18, fontweight='bold')
ax.text(0.5, 0.04, 'Финансовый контур', ha='center', fontsize=18, fontweight='bold')
ax.text(0.5, 0.74, 'Схема цепочки поставок и финансовых расчётов', ha='center', fontsize=22, fontweight='bold')

ax.set_xlim(0, 0.92)
ax.set_ylim(0.0, 0.9)
ax.axis('off')

out = BASE_DIR / 'supply_chain_schema_simple.png'
plt.tight_layout()
plt.savefig(out, dpi=240, bbox_inches='tight')
plt.close(fig)

with open(str(out) + '.meta.json', 'w', encoding='utf-8') as f:
    json.dump({
        'caption': 'Упрощенная схема цепочки поставок',
        'description': 'Рисунок показывает материальный поток от поставщика к клиенту и основной финансовый поток через банк в более простой форме.'
    }, f, ensure_ascii=False)

print(out.name)
