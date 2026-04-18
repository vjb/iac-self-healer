import json, os
run_dir = r'c:\Users\vjbel\hacks\inverse-prompt-gen\results\optimization\run_1776473889'
telemetry = os.path.join(run_dir, 'live_telemetry.jsonl')
data = []
with open(telemetry, 'r', encoding='utf-8') as f:
    for line in f:
        try: data.append(json.loads(line))
        except: pass

data.sort(key=lambda x: x.get('avg_score', 0), reverse=True)
print('\n=== OVERALL TOP SCORES ===')
for d in data[:3]:
    print(f"Avg: {d.get('avg_score',0):.2f} | Intent: {d.get('intent','')[:80]}...")

print('\nTotal Traces:', len(data))
print('Optimized Factory JSON exists:', os.path.exists(os.path.join(run_dir, 'optimized_factory.json')))
