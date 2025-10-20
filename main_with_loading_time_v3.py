"""
车辆装载优化主程序 V3（每辆车只能在一个装货点装货）
从Excel读取数据，进行装载优化和装货时间优化，输出结果到Excel
"""
import pandas as pd
from vehicle_loading_optimizer import Vehicle, Good, LoadingOptimizer
from loading_time_optimizer_v3 import LoadingPoint, LoadingTimeOptimizerV3, VehicleSchedule
from datetime import datetime
import os
import sys

# 设置输出编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def load_data_from_excel(filename: str):
    """从Excel文件加载数据"""
    print(f"\n正在读取数据文件: {filename}")
    
    # 读取Excel文件
    df_vehicles = pd.read_excel(filename, sheet_name='车辆信息')
    df_goods = pd.read_excel(filename, sheet_name='货物信息')
    df_restrictions = pd.read_excel(filename, sheet_name='装载限制')
    df_loading_points = pd.read_excel(filename, sheet_name='装货点信息')
    df_distance = pd.read_excel(filename, sheet_name='车辆到装货点距离')
    df_prep_time = pd.read_excel(filename, sheet_name='车辆准备时长')
    df_loading_time = pd.read_excel(filename, sheet_name='货物装货时间')
    
    # 创建车辆对象
    vehicles = []
    for _, row in df_vehicles.iterrows():
        vehicle = Vehicle(
            vehicle_id=row['车辆ID'],
            name=row['车辆名称'],
            speed=row['速度(km/h)'],
            capacity=row['容量(m³)'],
            max_load=row['最大载重(kg)']
        )
        vehicles.append(vehicle)
    
    # 创建货物对象
    goods = []
    goods_info = {}
    for _, row in df_goods.iterrows():
        good = Good(
            good_id=row['货物ID'],
            name=row['货物名称'],
            volume=row['体积(m³)'],
            weight=row['重量(kg)']
        )
        goods.append(good)
        goods_info[good.id] = {
            "name": good.name,
            "volume": good.volume,
            "weight": good.weight
        }
    
    # 创建限制关系字典
    restrictions = {}
    for _, row in df_restrictions.iterrows():
        good_id = row['货物ID']
        vehicle_id = row['车辆ID']
        if good_id not in restrictions:
            restrictions[good_id] = set()
        restrictions[good_id].add(vehicle_id)
    
    # 创建装货点对象
    loading_points = []
    for _, row in df_loading_points.iterrows():
        point = LoadingPoint(
            point_id=row['装货点ID'],
            name=row['装货点名称'],
            address=row.get('地址', '')
        )
        loading_points.append(point)
    
    # 创建距离矩阵
    distance_matrix = {}
    for _, row in df_distance.iterrows():
        vehicle_id = row['车辆ID']
        distance_matrix[vehicle_id] = {}
        for point in loading_points:
            distance_matrix[vehicle_id][point.name] = row[point.name]
    
    # 创建准备时长矩阵
    prep_time_matrix = {}
    for _, row in df_prep_time.iterrows():
        vehicle_id = row['车辆ID']
        prep_time_matrix[vehicle_id] = {}
        for point in loading_points:
            prep_time_matrix[vehicle_id][point.name] = row[point.name]
    
    # 创建货物装货时间字典
    goods_loading_time = {}
    for _, row in df_loading_time.iterrows():
        goods_loading_time[row['货物ID']] = row['装货时间(分钟)']

    # 读取车辆装货点限制（如果存在）
    vehicle_point_restrictions = {}
    has_restrictions = False
    try:
        df_vehicle_point_restrictions = pd.read_excel(filename, sheet_name='车辆装货点限制')
        for _, row in df_vehicle_point_restrictions.iterrows():
            vehicle_id = row['车辆ID']
            point_id = row['装货点ID']
            if vehicle_id not in vehicle_point_restrictions:
                vehicle_point_restrictions[vehicle_id] = set()
            vehicle_point_restrictions[vehicle_id].add(point_id)
        has_restrictions = True
        restriction_count = len(df_vehicle_point_restrictions)
    except Exception as e:
        has_restrictions = False
        restriction_count = 0
    
    print(f"数据加载完成:")
    print(f"  - 车辆: {len(vehicles)} 辆")
    print(f"  - 货物: {len(goods)} 件")
    print(f"  - 限制: {len(df_restrictions)} 条")
    print(f"  - 装货点: {len(loading_points)} 个")
    if has_restrictions:
        print(f"  - 车辆装货点限制: {restriction_count} 条")
    else:
        print(f"  - 车辆装货点限制: 0 条（未设置）")

    return (vehicles, goods, restrictions, loading_points,
            distance_matrix, prep_time_matrix, goods_loading_time, goods_info,
            vehicle_point_restrictions)


def save_results_to_excel(used_vehicles, unloaded_goods, vehicle_statistics, 
                          vehicle_schedules, loading_statistics, 
                          loading_time_optimizer, output_filename):
    """保存结果到Excel文件"""
    print(f"\n正在保存结果到: {output_filename}")
    
    # 1. 装载方案数据（包含装货点信息）
    loading_plan = []
    # 创建车辆到装货点的映射
    vehicle_to_point = {}
    for schedule in vehicle_schedules:
        vehicle_to_point[schedule.vehicle_id] = {
            'point_id': schedule.loading_point_id,
            'point_name': schedule.loading_point_name
        }
    
    for vehicle in used_vehicles:
        point_info = vehicle_to_point.get(vehicle.id, {'point_id': '未分配', 'point_name': '未分配'})
        for good in vehicle.loaded_goods:
            loading_plan.append({
                "车辆ID": vehicle.id,
                "车辆名称": vehicle.name,
                "车辆速度(km/h)": vehicle.speed,
                "车辆容量(m³)": vehicle.capacity,
                "车辆最大载重(kg)": vehicle.max_load,
                "货物ID": good.id,
                "货物名称": good.name,
                "货物体积(m³)": good.volume,
                "货物重量(kg)": good.weight,
                "装货点ID": point_info['point_id'],
                "装货点名称": point_info['point_name']
            })
    
    # 2. 车辆使用情况数据
    vehicle_usage = []
    for vehicle in used_vehicles:
        point_info = vehicle_to_point.get(vehicle.id, {'point_id': '未分配', 'point_name': '未分配'})
        vehicle_usage.append({
            "车辆ID": vehicle.id,
            "车辆名称": vehicle.name,
            "装货点ID": point_info['point_id'],
            "装货点名称": point_info['point_name'],
            "速度(km/h)": vehicle.speed,
            "容量(m³)": vehicle.capacity,
            "已用容量(m³)": round(vehicle.used_capacity, 2),
            "容量使用率(%)": round(vehicle.get_capacity_utilization(), 2),
            "最大载重(kg)": vehicle.max_load,
            "已用载重(kg)": round(vehicle.used_load, 2),
            "载重使用率(%)": round(vehicle.get_load_utilization(), 2),
            "装载货物数": len(vehicle.loaded_goods)
        })
    
    # 3. 未装载货物数据
    unloaded_data = []
    for good in unloaded_goods:
        unloaded_data.append({
            "货物ID": good.id,
            "货物名称": good.name,
            "体积(m³)": good.volume,
            "重量(kg)": good.weight
        })
    
    # 4. 装载统计信息
    vehicle_stats_data = [{"指标": k, "数值": v} for k, v in vehicle_statistics.items()]
    
    # 5. 装货方案（每辆车的装货详情）
    loading_schedule_data = []
    for schedule in vehicle_schedules:
        for good in schedule.goods:
            loading_schedule_data.append({
                "车辆ID": schedule.vehicle_id,
                "装货点ID": schedule.loading_point_id,
                "装货点名称": schedule.loading_point_name,
                "距离(km)": schedule.distance,
                "行驶时间(分钟)": round(schedule.travel_time, 2),
                "准备时长(分钟)": round(schedule.prep_time, 2),
                "排队时长(分钟)": round(schedule.queue_time, 2),
                "装货时长(分钟)": round(schedule.loading_time, 2),
                "总时长(分钟)": round(schedule.total_time, 2),
                "货物ID": good["货物ID"],
                "货物名称": good["货物名称"],
                "装货时间(分钟)": good["装货时间"]
            })
    
    # 6. 车辆装货时间汇总
    vehicle_loading_summary = []
    for schedule in vehicle_schedules:
        vehicle_loading_summary.append({
            "车辆ID": schedule.vehicle_id,
            "装货点ID": schedule.loading_point_id,
            "装货点名称": schedule.loading_point_name,
            "距离(km)": round(schedule.distance, 2),
            "行驶时间(分钟)": round(schedule.travel_time, 2),
            "准备时长(分钟)": round(schedule.prep_time, 2),
            "排队时长(分钟)": round(schedule.queue_time, 2),
            "装货时长(分钟)": round(schedule.loading_time, 2),
            "总时长(分钟)": round(schedule.total_time, 2),
            "装载货物数": len(schedule.goods)
        })
    
    # 7. 装货时间统计
    loading_stats_data = [{"指标": k, "数值": v} for k, v in loading_statistics.items()]
    
    # 8. 装货点使用情况
    point_usage = {}
    for schedule in vehicle_schedules:
        point_id = schedule.loading_point_id
        point_name = schedule.loading_point_name
        if point_id not in point_usage:
            point_usage[point_id] = {
                "装货点ID": point_id,
                "装货点名称": point_name,
                "服务车辆数": 0,
                "装载货物数": 0,
                "总装货时长(分钟)": 0
            }
        point_usage[point_id]["服务车辆数"] += 1
        point_usage[point_id]["装载货物数"] += len(schedule.goods)
        point_usage[point_id]["总装货时长(分钟)"] += schedule.loading_time
    
    point_usage_data = list(point_usage.values())
    for item in point_usage_data:
        item["总装货时长(分钟)"] = round(item["总装货时长(分钟)"], 2)
    
    # 创建DataFrame
    df_loading_plan = pd.DataFrame(loading_plan)
    df_vehicle_usage = pd.DataFrame(vehicle_usage)
    df_unloaded = pd.DataFrame(unloaded_data)
    df_vehicle_stats = pd.DataFrame(vehicle_stats_data)
    df_loading_schedule = pd.DataFrame(loading_schedule_data)
    df_vehicle_loading_summary = pd.DataFrame(vehicle_loading_summary)
    df_loading_stats = pd.DataFrame(loading_stats_data)
    df_point_usage = pd.DataFrame(point_usage_data)
    
    # 保存到Excel
    with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
        df_loading_plan.to_excel(writer, sheet_name='装载方案', index=False)
        df_vehicle_usage.to_excel(writer, sheet_name='车辆使用情况', index=False)
        df_unloaded.to_excel(writer, sheet_name='未装载货物', index=False)
        df_vehicle_stats.to_excel(writer, sheet_name='装载统计', index=False)
        df_loading_schedule.to_excel(writer, sheet_name='装货方案', index=False)
        df_vehicle_loading_summary.to_excel(writer, sheet_name='车辆装货时间汇总', index=False)
        df_loading_stats.to_excel(writer, sheet_name='装货时间统计', index=False)
        df_point_usage.to_excel(writer, sheet_name='装货点使用情况', index=False)
    
    print(f"✓ 结果已保存")


def print_summary(used_vehicles, unloaded_goods, vehicle_statistics, 
                 vehicle_schedules, loading_statistics, loading_time_optimizer):
    """打印摘要信息"""
    print("\n" + "="*60)
    print("装载优化结果摘要")
    print("="*60)
    
    print(f"\n使用车辆数: {vehicle_statistics['车辆数量']} 辆")
    print(f"平均速度: {vehicle_statistics['平均速度']} km/h")
    print(f"装载货物数: {vehicle_statistics['装载货物数']} 件")
    print(f"未装载货物数: {len(unloaded_goods)} 件")
    print(f"\n容量统计:")
    print(f"  总容量: {vehicle_statistics['总容量']} m³")
    print(f"  已用容量: {vehicle_statistics['已用容量']} m³")
    print(f"  平均容量使用率: {vehicle_statistics['平均容量使用率']}%")
    
    print("\n" + "="*60)
    print("装货时间优化结果摘要")
    print("="*60)
    
    print(f"\n装货点数量: {loading_statistics['装货点数量']} 个（共 {len(loading_time_optimizer.loading_points)} 个可用）")
    print(f"最长装货时间: {loading_statistics['最长装货时间(分钟)']} 分钟")
    print(f"最短装货时间: {loading_statistics['最短装货时间(分钟)']} 分钟")
    print(f"平均装货时间: {loading_statistics['平均装货时间(分钟)']} 分钟")
    
    print(f"\n各车辆装货详情:")
    print("-" * 80)
    
    # 按总时长降序排序
    sorted_schedules = sorted(vehicle_schedules, key=lambda s: s.total_time, reverse=True)
    
    for schedule in sorted_schedules:
        print(f"\n【{schedule.vehicle_id}】 → {schedule.loading_point_name}")
        print(f"  距离: {schedule.distance} km")
        print(f"  行驶时间: {schedule.travel_time:.2f} 分钟")
        print(f"  准备时长: {schedule.prep_time:.2f} 分钟")
        print(f"  排队时长: {schedule.queue_time:.2f} 分钟")
        print(f"  装货时长: {schedule.loading_time:.2f} 分钟")
        print(f"  总时长: {schedule.total_time:.2f} 分钟")
        print(f"  装载货物 ({len(schedule.goods)}件):", end=" ")
        good_names = [g['货物名称'] for g in schedule.goods[:5]]
        if len(schedule.goods) > 5:
            print(f"{', '.join(good_names)}... (还有{len(schedule.goods)-5}件)")
        else:
            print(', '.join(good_names))
    
    print("\n" + "="*60)


def main():
    """主函数"""
    print("="*60)
    print("车辆装载优化系统 V3（每辆车只在一个装货点装货）")
    print("="*60)
    
    # 输入文件名
    input_file = "车辆货物数据1.xlsx"
    
    # 检查文件是否存在
    if not os.path.exists(input_file):
        print(f"\n错误: 找不到输入文件 '{input_file}'")
        print("请先运行 generate_sample_data.py 生成模拟数据")
        return
    
    # 加载数据
    (vehicles, goods, restrictions, loading_points,
     distance_matrix, prep_time_matrix, goods_loading_time, goods_info,
     vehicle_point_restrictions) = load_data_from_excel(input_file)
    
    # ========== 第一步: 车辆装载优化 ==========
    print("\n" + "="*60)
    print("第一步: 车辆装载优化")
    print("="*60)
    
    vehicle_optimizer = LoadingOptimizer(vehicles, goods, restrictions)
    used_vehicles, unloaded_goods = vehicle_optimizer.optimize()
    vehicle_statistics = vehicle_optimizer.get_statistics(used_vehicles)
    
    print(f"\n✓ 装载优化完成")
    print(f"  - 使用车辆: {len(used_vehicles)} 辆")
    print(f"  - 装载货物: {vehicle_statistics['装载货物数']} 件")
    print(f"  - 未装载货物: {len(unloaded_goods)} 件")
    
    # ========== 第二步: 装货时间优化（V3版本 - 每辆车只在一个点）==========
    print("\n" + "="*60)
    print("第二步: 装货时间优化（每辆车只在一个装货点）")
    print("="*60)
    
    # 构建车辆-货物映射
    vehicle_goods_map = {}
    vehicle_speeds = {}
    for vehicle in used_vehicles:
        vehicle_goods_map[vehicle.id] = [g.id for g in vehicle.loaded_goods]
        vehicle_speeds[vehicle.id] = vehicle.speed

    # 创建装货时间优化器 V3
    loading_optimizer = LoadingTimeOptimizerV3(
        vehicle_goods_map=vehicle_goods_map,
        loading_points=loading_points,
        distance_matrix=distance_matrix,
        prep_time_matrix=prep_time_matrix,
        goods_loading_time=goods_loading_time,
        goods_info=goods_info,
        vehicle_speeds=vehicle_speeds,
        vehicle_point_restrictions=vehicle_point_restrictions
    )
    
    # 执行优化
    vehicle_schedules, loading_statistics = loading_optimizer.optimize()
    
    print(f"\n✓ 装货时间优化完成")
    print(f"  - 使用装货点: {loading_statistics['装货点数量']} 个")
    print(f"  - 最长装货时间: {loading_statistics['最长装货时间(分钟)']} 分钟")
    print(f"  - 平均装货时间: {loading_statistics['平均装货时间(分钟)']} 分钟")
    
    # 打印摘要
    print_summary(used_vehicles, unloaded_goods, vehicle_statistics, 
                 vehicle_schedules, loading_statistics, loading_optimizer)
    
    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"装载装货方案_V3_{timestamp}.xlsx"
    save_results_to_excel(used_vehicles, unloaded_goods, vehicle_statistics,
                         vehicle_schedules, loading_statistics, 
                         loading_optimizer, output_file)
    
    print(f"\n✓ 优化完成！结果已保存到: {output_file}")


if __name__ == "__main__":
    main()

