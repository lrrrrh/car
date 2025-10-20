"""
车辆装载优化算法
使用最少最快的车辆装载所有货物
"""
import pandas as pd
from typing import List, Dict, Tuple, Set
import copy


class Vehicle:
    """车辆类"""
    def __init__(self, vehicle_id: str, name: str, speed: float, capacity: float, max_load: float):
        self.id = vehicle_id
        self.name = name
        self.speed = speed  # km/h
        self.capacity = capacity  # m³
        self.max_load = max_load  # kg
        self.loaded_goods = []  # 已装载的货物
        self.used_capacity = 0.0  # 已使用容量
        self.used_load = 0.0  # 已使用载重
    
    def can_load(self, good: 'Good') -> bool:
        """检查是否可以装载该货物"""
        return (self.used_capacity + good.volume <= self.capacity and 
                self.used_load + good.weight <= self.max_load)
    
    def load_good(self, good: 'Good'):
        """装载货物"""
        self.loaded_goods.append(good)
        self.used_capacity += good.volume
        self.used_load += good.weight
    
    def unload_good(self, good: 'Good'):
        """卸载货物"""
        if good in self.loaded_goods:
            self.loaded_goods.remove(good)
            self.used_capacity -= good.volume
            self.used_load -= good.weight
    
    def get_capacity_utilization(self) -> float:
        """获取容量使用率"""
        return (self.used_capacity / self.capacity * 100) if self.capacity > 0 else 0
    
    def get_load_utilization(self) -> float:
        """获取载重使用率"""
        return (self.used_load / self.max_load * 100) if self.max_load > 0 else 0
    
    def is_empty(self) -> bool:
        """检查是否为空"""
        return len(self.loaded_goods) == 0
    
    def reset(self):
        """重置车辆"""
        self.loaded_goods = []
        self.used_capacity = 0.0
        self.used_load = 0.0


class Good:
    """货物类"""
    def __init__(self, good_id: str, name: str, volume: float, weight: float):
        self.id = good_id
        self.name = name
        self.volume = volume  # m³
        self.weight = weight  # kg
    
    def get_density(self) -> float:
        """获取密度（重量/体积）"""
        return self.weight / self.volume if self.volume > 0 else 0


class LoadingOptimizer:
    """装载优化器"""
    
    def __init__(self, vehicles: List[Vehicle], goods: List[Good], restrictions: Dict[str, Set[str]]):
        """
        初始化优化器
        :param vehicles: 车辆列表
        :param goods: 货物列表
        :param restrictions: 限制关系字典 {货物ID: {不能装载的车辆ID集合}}
        """
        self.vehicles = vehicles
        self.goods = goods
        self.restrictions = restrictions
        self.min_capacity_utilization = 0.85  # 最小容量使用率85%
    
    def can_load_good_to_vehicle(self, good: Good, vehicle: Vehicle) -> bool:
        """检查货物是否可以装载到车辆"""
        # 检查限制关系
        if good.id in self.restrictions and vehicle.id in self.restrictions[good.id]:
            return False
        # 检查容量和载重
        return vehicle.can_load(good)
    
    def optimize(self) -> Tuple[List[Vehicle], List[Good]]:
        """
        优化装载方案
        返回: (使用的车辆列表, 未装载的货物列表)
        """
        # 按容量降序、速度降序排序车辆（优先选择装载能力大且速度快的车辆）
        sorted_vehicles = sorted(self.vehicles, key=lambda v: (-v.capacity, -v.speed))

        # 按体积降序排序货物（先装大件）
        sorted_goods = sorted(self.goods, key=lambda g: -g.volume)
        
        # 重置所有车辆
        for vehicle in sorted_vehicles:
            vehicle.reset()
        
        # 尝试装载所有货物
        unloaded_goods = []
        used_vehicles = []
        
        for good in sorted_goods:
            loaded = False
            
            # 首先尝试装到已使用的车辆中
            for vehicle in used_vehicles:
                if self.can_load_good_to_vehicle(good, vehicle):
                    vehicle.load_good(good)
                    loaded = True
                    break
            
            # 如果已使用的车辆装不下，尝试使用新车辆
            if not loaded:
                for vehicle in sorted_vehicles:
                    if vehicle not in used_vehicles and self.can_load_good_to_vehicle(good, vehicle):
                        vehicle.load_good(good)
                        used_vehicles.append(vehicle)
                        loaded = True
                        break
            
            if not loaded:
                unloaded_goods.append(good)
        
        # 检查容量使用率，调整不满足85%的车辆
        used_vehicles = self._adjust_capacity_utilization(used_vehicles, sorted_vehicles)
        
        return used_vehicles, unloaded_goods
    
    def _adjust_capacity_utilization(self, used_vehicles: List[Vehicle], all_vehicles: List[Vehicle]) -> List[Vehicle]:
        """调整容量使用率，确保除最后一辆车外，其他车至少85%"""
        if not used_vehicles:
            return []

        # 按容量使用率排序，使用率高的在前
        sorted_vehicles = sorted(used_vehicles, key=lambda v: -v.get_capacity_utilization())

        adjusted_vehicles = []
        goods_to_redistribute = []

        # 检查每辆车（除了最后一辆）
        for i, vehicle in enumerate(sorted_vehicles):
            is_last = (i == len(sorted_vehicles) - 1)
            utilization = vehicle.get_capacity_utilization()

            if is_last:
                # 最后一辆车，无论使用率多少都保留
                adjusted_vehicles.append(vehicle)
            elif utilization >= self.min_capacity_utilization * 100:
                # 使用率达标，保留
                adjusted_vehicles.append(vehicle)
            else:
                # 使用率不达标，将货物重新分配
                goods_to_redistribute.extend(vehicle.loaded_goods)
                vehicle.reset()

        # 如果有需要重新分配的货物
        if goods_to_redistribute:
            # 按体积降序排序
            goods_to_redistribute.sort(key=lambda g: -g.volume)

            for good in goods_to_redistribute:
                loaded = False

                # 尝试装到已调整的车辆中
                for vehicle in adjusted_vehicles:
                    if self.can_load_good_to_vehicle(good, vehicle):
                        vehicle.load_good(good)
                        loaded = True
                        break

                # 尝试使用新车辆
                if not loaded:
                    for vehicle in all_vehicles:
                        if vehicle not in adjusted_vehicles and self.can_load_good_to_vehicle(good, vehicle):
                            vehicle.load_good(good)
                            adjusted_vehicles.append(vehicle)
                            loaded = True
                            break

        # 移除空车辆
        final_vehicles = [v for v in adjusted_vehicles if not v.is_empty()]

        return final_vehicles
    
    def get_statistics(self, used_vehicles: List[Vehicle]) -> Dict:
        """获取统计信息"""
        if not used_vehicles:
            return {
                "车辆数量": 0,
                "平均速度": 0,
                "总容量": 0,
                "已用容量": 0,
                "平均容量使用率": 0,
                "总载重": 0,
                "已用载重": 0,
                "平均载重使用率": 0,
                "装载货物数": 0
            }
        
        total_capacity = sum(v.capacity for v in used_vehicles)
        used_capacity = sum(v.used_capacity for v in used_vehicles)
        total_load = sum(v.max_load for v in used_vehicles)
        used_load = sum(v.used_load for v in used_vehicles)
        avg_speed = sum(v.speed for v in used_vehicles) / len(used_vehicles)
        total_goods = sum(len(v.loaded_goods) for v in used_vehicles)
        
        return {
            "车辆数量": len(used_vehicles),
            "平均速度": round(avg_speed, 2),
            "总容量": round(total_capacity, 2),
            "已用容量": round(used_capacity, 2),
            "平均容量使用率": round(used_capacity / total_capacity * 100, 2) if total_capacity > 0 else 0,
            "总载重": round(total_load, 2),
            "已用载重": round(used_load, 2),
            "平均载重使用率": round(used_load / total_load * 100, 2) if total_load > 0 else 0,
            "装载货物数": total_goods
        }

