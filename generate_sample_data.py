"""
模拟数据生成器
生成车辆、货物和限制关系的Excel文件
"""
import pandas as pd
import random
import os


def generate_sample_data():
    """生成模拟数据并保存到Excel文件"""
    
    # 设置随机种子以便复现
    random.seed(42)
    
    # 生成车辆数据
    vehicles = []
    vehicle_types = [
        {"name": "小型货车", "speed_range": (60, 80), "capacity_range": (10, 15), "max_load_range": (1000, 1500), "count": 8},
        {"name": "中型货车", "speed_range": (50, 70), "capacity_range": (20, 30), "max_load_range": (3000, 5000), "count": 6},
        {"name": "大型货车", "speed_range": (40, 60), "capacity_range": (40, 60), "max_load_range": (8000, 12000), "count": 3},
        {"name": "超大货车", "speed_range": (30, 50), "capacity_range": (70, 100), "max_load_range": (15000, 20000), "count": 2},
    ]

    vehicle_id = 1
    for vtype in vehicle_types:
        for i in range(vtype["count"]):  # 根据count生成不同数量的车辆
            vehicles.append({
                "车辆ID": f"V{vehicle_id:03d}",
                "车辆名称": f"{vtype['name']}{i+1}",
                "速度(km/h)": random.randint(*vtype['speed_range']),
                "容量(m³)": random.randint(*vtype['capacity_range']),
                "最大载重(kg)": random.randint(*vtype['max_load_range'])
            })
            vehicle_id += 1
    
    # 生成货物数据
    goods = []
    cargo_types = [
        {"name": "电子产品", "volume_range": (0.5, 2), "weight_range": (10, 50)},
        {"name": "服装", "volume_range": (1, 3), "weight_range": (5, 30)},
        {"name": "食品", "volume_range": (0.8, 2.5), "weight_range": (20, 80)},
        {"name": "建材", "volume_range": (2, 5), "weight_range": (100, 500)},
        {"name": "家具", "volume_range": (3, 8), "weight_range": (50, 200)},
        {"name": "机械零件", "volume_range": (1, 4), "weight_range": (80, 300)},
    ]
    
    goods_id = 1
    for ctype in cargo_types:
        for i in range(8):  # 每种类型生成8个货物
            goods.append({
                "货物ID": f"G{goods_id:03d}",
                "货物名称": f"{ctype['name']}{i+1}",
                "体积(m³)": round(random.uniform(*ctype['volume_range']), 2),
                "重量(kg)": round(random.uniform(*ctype['weight_range']), 2)
            })
            goods_id += 1
    
    # 生成限制关系（某些货物不能装在某些车上）
    restrictions = []
    
    # 规则1: 电子产品不能装在超大货车上（防震要求）
    for g in goods:
        if "电子产品" in g["货物名称"]:
            for v in vehicles:
                if "超大货车" in v["车辆名称"]:
                    restrictions.append({
                        "货物ID": g["货物ID"],
                        "车辆ID": v["车辆ID"],
                        "限制原因": "电子产品不适合超大货车运输"
                    })
    
    # 规则2: 建材不能装在小型货车上（重量限制）
    for g in goods:
        if "建材" in g["货物名称"]:
            for v in vehicles:
                if "小型货车" in v["车辆名称"]:
                    restrictions.append({
                        "货物ID": g["货物ID"],
                        "车辆ID": v["车辆ID"],
                        "限制原因": "建材过重，小型货车无法承载"
                    })
    
    # 规则3: 家具不能装在小型货车上（体积限制）
    for g in goods:
        if "家具" in g["货物名称"]:
            for v in vehicles:
                if "小型货车" in v["车辆名称"]:
                    restrictions.append({
                        "货物ID": g["货物ID"],
                        "车辆ID": v["车辆ID"],
                        "限制原因": "家具体积过大，小型货车无法装载"
                    })
    
    # 规则4: 随机添加一些其他限制
    for _ in range(10):
        g = random.choice(goods)
        v = random.choice(vehicles)
        # 避免重复
        if not any(r["货物ID"] == g["货物ID"] and r["车辆ID"] == v["车辆ID"] for r in restrictions):
            restrictions.append({
                "货物ID": g["货物ID"],
                "车辆ID": v["车辆ID"],
                "限制原因": "特殊运输要求"
            })
    
    # 创建DataFrame
    df_vehicles = pd.DataFrame(vehicles)
    df_goods = pd.DataFrame(goods)
    df_restrictions = pd.DataFrame(restrictions)
    
    # 生成装货点数据
    loading_points = []
    point_names = ["北京仓库", "上海仓库", "广州仓库", "深圳仓库", "成都仓库"]

    for i, name in enumerate(point_names):
        loading_points.append({
            "装货点ID": f"P{i+1:02d}",
            "装货点名称": name,
            "地址": f"{name}地址"
        })

    # 生成车辆到装货点的距离表（横轴为装货点，纵轴为车辆）
    # 创建一个矩阵：行=车辆，列=装货点
    distance_data = []
    for vehicle in vehicles:
        row = {"车辆ID": vehicle["车辆ID"]}
        for point in loading_points:
            # 随机生成距离（10-200公里）
            distance = random.randint(10, 200)
            row[point["装货点名称"]] = distance
        distance_data.append(row)

    # 生成车辆在装货点的准备时长表（横轴为装货点，纵轴为车辆）
    prep_time_data = []
    for vehicle in vehicles:
        row = {"车辆ID": vehicle["车辆ID"]}
        for point in loading_points:
            # 随机生成准备时长（10-60分钟）
            prep_time = random.randint(10, 60)
            row[point["装货点名称"]] = prep_time
        prep_time_data.append(row)

    # 生成货物装货时间表
    loading_time_data = []
    for good in goods:
        # 装货时间与体积和重量相关（5-30分钟）
        base_time = good["体积(m³)"] * 2 + good["重量(kg)"] * 0.01
        loading_time = max(5, min(30, base_time + random.uniform(-5, 5)))
        loading_time_data.append({
            "货物ID": good["货物ID"],
            "货物名称": good["货物名称"],
            "装货时间(分钟)": round(loading_time, 2)
        })

    # 创建DataFrame
    df_vehicles = pd.DataFrame(vehicles)
    df_goods = pd.DataFrame(goods)
    df_restrictions = pd.DataFrame(restrictions)
    df_loading_points = pd.DataFrame(loading_points)
    df_distance = pd.DataFrame(distance_data)
    df_prep_time = pd.DataFrame(prep_time_data)
    df_loading_time = pd.DataFrame(loading_time_data)

    # 生成车辆装货点限制（某些车不能停在某些装货点）
    vehicle_point_restrictions = []

    # 规则1: 超大货车不能停在小型装货点（空间限制）
    # 假设装货点1和装货点5是小型装货点
    small_points = [loading_points[0], loading_points[4]]  # 第1个和第5个装货点
    for v in vehicles:
        if "超大货车" in v["车辆名称"]:
            for point in small_points:
                vehicle_point_restrictions.append({
                    "车辆ID": v["车辆ID"],
                    "装货点ID": point["装货点ID"],
                    "装货点名称": point["装货点名称"],
                    "限制原因": "超大货车无法停靠小型装货点"
                })

    # 规则2: 小型货车不能停在某些远程装货点（距离限制）
    # 假设装货点3是远程装货点
    remote_point = loading_points[2]  # 第3个装货点
    for v in vehicles:
        if "小型货车" in v["车辆名称"]:
            vehicle_point_restrictions.append({
                "车辆ID": v["车辆ID"],
                "装货点ID": remote_point["装货点ID"],
                "装货点名称": remote_point["装货点名称"],
                "限制原因": "小型货车不适合长途运输"
            })

    # 规则3: 随机添加一些其他限制
    for _ in range(5):
        v = random.choice(vehicles)
        point = random.choice(loading_points)
        # 避免重复
        exists = any(r["车辆ID"] == v["车辆ID"] and r["装货点ID"] == point["装货点ID"]
                    for r in vehicle_point_restrictions)
        if not exists:
            vehicle_point_restrictions.append({
                "车辆ID": v["车辆ID"],
                "装货点ID": point["装货点ID"],
                "装货点名称": point["装货点名称"],
                "限制原因": "其他限制原因"
            })

    df_vehicle_point_restrictions = pd.DataFrame(vehicle_point_restrictions)

    # 保存到Excel文件
    output_file = "车辆货物数据.xlsx"
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df_vehicles.to_excel(writer, sheet_name='车辆信息', index=False)
        df_goods.to_excel(writer, sheet_name='货物信息', index=False)
        df_restrictions.to_excel(writer, sheet_name='装载限制', index=False)
        df_loading_points.to_excel(writer, sheet_name='装货点信息', index=False)
        df_distance.to_excel(writer, sheet_name='车辆到装货点距离', index=False)
        df_prep_time.to_excel(writer, sheet_name='车辆准备时长', index=False)
        df_loading_time.to_excel(writer, sheet_name='货物装货时间', index=False)
        df_vehicle_point_restrictions.to_excel(writer, sheet_name='车辆装货点限制', index=False)

    print(f"✓ 模拟数据已生成: {output_file}")
    print(f"  - 车辆数量: {len(vehicles)}")
    print(f"  - 货物数量: {len(goods)}")
    print(f"  - 限制关系: {len(restrictions)}")
    print(f"  - 装货点数量: {len(loading_points)}")
    print("\n车辆统计:")
    print(df_vehicles.groupby(df_vehicles['车辆名称'].str.extract(r'(.*)\d+')[0])['车辆ID'].count())
    print("\n货物统计:")
    print(df_goods.groupby(df_goods['货物名称'].str.extract(r'(.*)\d+')[0])['货物ID'].count())

    return output_file


if __name__ == "__main__":
    generate_sample_data()

