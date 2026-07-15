import os, sys, yaml
r = yaml.safe_load(open('skills/roles/.registry.yaml'))
print(f'Total role cards: {len(r["cards"])}')
issues = 0
for c in r['cards']:
    p = 'skills/roles/' + c['path']
    if not os.path.exists(p):
        print(f'MISSING: {p}')
        issues += 1
sys.exit(issues)
