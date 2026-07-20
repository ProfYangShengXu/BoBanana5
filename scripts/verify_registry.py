import os, sys, yaml
try:
    r = yaml.safe_load(open('skills/roles/.registry.yaml'))
except (FileNotFoundError, yaml.YAMLError) as e:
    print(f'ERROR: 加载 registry 失败: {e}')
    sys.exit(1)
print(f'Total role cards: {len(r["cards"])}')
issues = 0
for c in r['cards']:
    p = 'skills/roles/' + c['path']
    if not os.path.exists(p):
        print(f'MISSING: {p}')
        issues += 1
sys.exit(issues)
