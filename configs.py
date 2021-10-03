import yaml


with open('configs.yml', 'r', encoding='utf-8') as _fp:
    configs = yaml.safe_load(_fp)


if __name__ == '__main__':
    import json
    print(json.dumps(configs, indent=4))
