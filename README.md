# 车辆装载优化工具

本项目用于根据车辆、货物以及装货点的属性，优化车辆与货物的匹配方案，并计算每辆车的装货总时长。

## 环境准备
1. 安装 Python 3.9+。
2. 安装依赖库：
   ```bash
   pip install pandas openpyxl
   ```

## 准备 Excel 数据
1. 将包含各类信息的 Excel 文件放在任意可访问的位置。
2. 打开 `main_with_loading_time_v3.py`，在文件顶部找到 `INPUT_EXCEL_PATH` 常量，将其设置为 Excel 文件的绝对路径，例如：
   ```python
   INPUT_EXCEL_PATH = r"D:\\data\\车辆货物数据.xlsx"
   ```
   如果保留为空字符串，程序会在脚本所在目录下自动查找 `DEFAULT_INPUT_FILENAMES` 列表中的文件名。
3. 若您没有现成的数据，可先运行示例数据生成脚本：
   ```bash
   python generate_sample_data.py
   ```
   该脚本会在项目根目录创建 `车辆货物数据.xlsx`，可直接用于测试。

## 运行主程序
在终端执行以下命令：
```bash
python main_with_loading_time_v3.py
```
程序会读取 Excel 数据，执行装载优化，并在控制台输出结果；若脚本内设置了结果导出逻辑，还会生成相应的输出文件。

## 常见问题
- **找不到 Excel 文件**：请确认 `INPUT_EXCEL_PATH` 设置正确，或将文件命名为默认名称并放在脚本目录下。
- **缺少装货时间列**：确保 “货物装货时间” 工作表的 A/B/C 列标题分别为 “货物ID”、“货物名称”、“装货时间(分钟)”。

如需进一步扩展或自定义规则，可编辑 `vehicle_loading_optimizer.py` 与 `loading_time_optimizer_v3.py` 中的逻辑。
