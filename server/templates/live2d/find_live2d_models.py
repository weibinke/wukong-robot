# 执行这个脚本，会遍历读取directory目录，找出所有live2d模型列表，输出到all_models.json，用于网页预览

import os
import json

def find_live2d_models(directory):
    models = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith("model.json") or file.endswith("model3.json"):
                model = {}
                relative_path = os.path.relpath(root, directory)
                model['name'] = relative_path.replace(os.sep, '_')
                model['model_file_path'] = os.path.join(root, file)
                model['model_directory'] = root
                model['relative_path'] = os.path.join(relative_path, file)
                print(model)
                models.append(model)
    return models

# 替换为你要遍历的文件夹路径
directory = "/Users/weibinke/ChatGPT/wukong-robot/server/templates/live2d/packages"
output_path = os.path.join(directory, 'all_models.json')

models = find_live2d_models(directory)
print(f"Find models,count={len(models)},output={output_path}")

# 将结果输出到指定的JSON文件中，如果旧的JSON文件存在，则删除
if os.path.exists(output_path):
    os.remove(output_path)
with open(output_path, 'w') as f:
    json.dump(models, f, indent=4)
