"""
装货时间优化算法 V3
每辆车只能在一个装货点装货
为每辆车选择最优装货点，最小化最长装货时间
"""
import pandas as pd
from typing import List, Dict, Tuple, Set
import copy


class LoadingPoint:
    """装货点类"""
    def __init__(self, point_id: str, name: str, address: str = ""):
        self.id = point_id
        self.name = name
        self.address = address


class VehicleSchedule:
    """车辆装货计划"""
    def __init__(self, vehicle_id: str, loading_point_id: str, loading_point_name: str,
                 vehicle_speed: float = 60.0):
        self.vehicle_id = vehicle_id
        self.loading_point_id = loading_point_id
        self.loading_point_name = loading_point_name
        self.vehicle_speed = vehicle_speed
        self.goods = []  # 在该装货点装载的货物
        
        # 时间组成
        self.distance = 0.0  # 到装货点的距离
        self.travel_time = 0.0  # 行驶时间
        self.prep_time = 0.0  # 准备时长
        self.loading_time = 0.0  # 装货时长
        self.queue_time = 0.0  # 排队时长
        self.total_time = 0.0  # 总时长
    
    def set_distance_and_prep(self, distance: float, prep_time: float):
        """设置距离和准备时长"""
        self.distance = distance
        self.prep_time = prep_time
        # 计算行驶时间
        if self.vehicle_speed > 0:
            self.travel_time = (distance / self.vehicle_speed) * 60
        else:
            self.travel_time = 0
        self._update_total_time()
    
    def add_good(self, good_id: str, good_name: str, loading_time: float):
        """添加货物"""
        self.goods.append({
            "货物ID": good_id,
            "货物名称": good_name,
            "装货时间": loading_time
        })
        self.loading_time += loading_time
        self._update_total_time()
    
    def set_queue_time(self, queue_time: float):
        """设置排队时长"""
        self.queue_time = queue_time
        self._update_total_time()
    
    def _update_total_time(self):
        """更新总时长"""
        self.total_time = self.travel_time + self.prep_time + self.queue_time + self.loading_time


class LoadingTimeOptimizerV3:
    """装货时间优化器 V3 - 每辆车只能在一个装货点装货"""

    def __init__(self,
                 vehicle_goods_map: Dict[str, List[str]],  # {车辆ID: [货物ID列表]}
                 loading_points: List[LoadingPoint],
                 distance_matrix: Dict[str, Dict[str, float]],  # {车辆ID: {装货点名称: 距离}}
                 prep_time_matrix: Dict[str, Dict[str, float]],  # {车辆ID: {装货点名称: 准备时长}}
                 goods_loading_time: Dict[str, float],  # {货物ID: 装货时间}
                 goods_info: Dict[str, Dict],  # {货物ID: {货物信息}}
                 vehicle_speeds: Dict[str, float],  # {车辆ID: 速度}
                 vehicle_point_restrictions: Dict[str, Set[str]] = None):  # {车辆ID: {不能停的装货点ID集合}}
        """
        初始化优化器
        """
        self.vehicle_goods_map = vehicle_goods_map
        self.loading_points = loading_points
        self.distance_matrix = distance_matrix
        self.prep_time_matrix = prep_time_matrix
        self.goods_loading_time = goods_loading_time
        self.goods_info = goods_info
        self.vehicle_speeds = vehicle_speeds
        self.vehicle_point_restrictions = vehicle_point_restrictions or {}
    
    def optimize(self) -> Tuple[List[VehicleSchedule], Dict]:
        """
        优化装货方案，每辆车只选择一个装货点
        策略：迭代分配，考虑已分配车辆的排队影响
        
        返回: (车辆装货计划列表, 统计信息)
        """
        print("\n正在优化装货点分配（考虑排队影响）...")
        
        vehicle_schedules = []
        
        # 按车辆速度排序，速度快的优先分配（先到先得）
        sorted_vehicles = sorted(
            self.vehicle_goods_map.items(),
            key=lambda x: -self.vehicle_speeds.get(x[0], 60.0)
        )
        
        # 第一步：迭代为每辆车选择最优装货点（考虑已分配车辆的影响）
        for vehicle_id, goods_ids in sorted_vehicles:
            if not goods_ids:
                continue
            
            vehicle_speed = self.vehicle_speeds.get(vehicle_id, 60.0)
            
            # 计算该车的总装货时间
            total_loading_time = sum(self.goods_loading_time.get(gid, 0) for gid in goods_ids)
            
            # 评估每个装货点（考虑预期排队时间）
            best_point = None
            best_time = float('inf')
            
            for point in self.loading_points:
                # 检查车辆装货点限制
                restricted_points = self.vehicle_point_restrictions.get(vehicle_id, set())
                if point.id in restricted_points:
                    continue
                
                # 计算基础时间
                distance = self.distance_matrix.get(vehicle_id, {}).get(point.name, 0)
                prep_time = self.prep_time_matrix.get(vehicle_id, {}).get(point.name, 0)
                travel_time = (distance / vehicle_speed) * 60 if vehicle_speed > 0 else 0
                
                # 计算预期排队时间（基于已分配到该点的车辆）
                expected_queue_time = self._estimate_queue_time(
                    point.id, travel_time, vehicle_schedules
                )
                
                # 总时间 = 行驶 + 准备 + 预期排队 + 装货
                total_time = travel_time + prep_time + expected_queue_time + total_loading_time
                
                if total_time < best_time:
                    best_time = total_time
                    best_point = {
                        'point': point,
                        'distance': distance,
                        'prep_time': prep_time,
                        'expected_queue': expected_queue_time
                    }
            
            if best_point is None:
                print(f"警告: 车辆 {vehicle_id} 无可用装货点")
                continue
            
            # 创建车辆装货计划
            schedule = VehicleSchedule(
                vehicle_id, 
                best_point['point'].id,
                best_point['point'].name,
                vehicle_speed
            )
            schedule.set_distance_and_prep(best_point['distance'], best_point['prep_time'])
            
            # 添加货物
            for good_id in goods_ids:
                good_info = self.goods_info.get(good_id, {})
                good_name = good_info.get("name", good_id)
                loading_time = self.goods_loading_time.get(good_id, 0)
                schedule.add_good(good_id, good_name, loading_time)
            
            vehicle_schedules.append(schedule)
        
        print(f"✓ 装货点分配完成")
        print(f"  - 车辆数: {len(vehicle_schedules)} 辆")
        
        # 统计装货点使用情况
        point_usage = {}
        for schedule in vehicle_schedules:
            point_id = schedule.loading_point_id
            point_usage[point_id] = point_usage.get(point_id, 0) + 1
        
        print(f"  - 使用装货点: {len(point_usage)} 个")
        print(f"  - 平均每个装货点服务: {len(vehicle_schedules) / len(point_usage):.1f} 辆车")
        
        # 第二步：计算排队时长
        print("\n正在计算排队时长...")
        vehicle_schedules = self._calculate_queue_times(vehicle_schedules)
        print(f"✓ 排队时长计算完成")
        
        # 第三步：尝试负载均衡优化
        print("\n正在进行负载均衡优化...")
        vehicle_schedules = self._balance_load(vehicle_schedules)
        print(f"✓ 负载均衡完成")
        
        # 生成统计信息
        statistics = self._generate_statistics(vehicle_schedules)
        
        return vehicle_schedules, statistics
    
    def _estimate_queue_time(self, point_id: str, arrival_time: float, 
                            existing_schedules: List[VehicleSchedule]) -> float:
        """
        估算在某个装货点的预期排队时间
        基于已分配到该点的车辆
        """
        # 找出已分配到该装货点的车辆
        point_vehicles = [s for s in existing_schedules if s.loading_point_id == point_id]
        
        if not point_vehicles:
            return 0.0  # 没有其他车，无需排队
        
        # 按到达时间排序
        point_vehicles.sort(key=lambda s: s.travel_time)
        
        # 计算装货点何时可用
        point_available_time = 0.0
        for pv in point_vehicles:
            if pv.travel_time >= point_available_time:
                # 该车到达时装货点已空闲
                point_available_time = pv.travel_time + pv.prep_time + pv.loading_time
            else:
                # 该车需要排队
                point_available_time = point_available_time + pv.prep_time + pv.loading_time
        
        # 当前车到达时的排队情况
        if arrival_time >= point_available_time:
            return 0.0  # 到达时已空闲
        else:
            return point_available_time - arrival_time  # 需要等待
    
    def _calculate_queue_times(self, schedules: List[VehicleSchedule]) -> List[VehicleSchedule]:
        """
        计算排队时长
        同一个装货点的多辆车需要排队
        """
        # 按装货点分组
        point_schedules = {}
        for schedule in schedules:
            point_id = schedule.loading_point_id
            if point_id not in point_schedules:
                point_schedules[point_id] = []
            point_schedules[point_id].append(schedule)
        
        # 为每个装货点计算排队时长
        for point_id, point_schedule_list in point_schedules.items():
            if len(point_schedule_list) <= 1:
                # 只有一辆车，无需排队
                continue
            
            # 按到达时间（行驶时间）排序
            point_schedule_list.sort(key=lambda s: s.travel_time)
            
            # 第一辆车无需排队
            point_schedule_list[0].set_queue_time(0)
            
            # 计算后续车辆的排队时间
            cumulative_time = point_schedule_list[0].travel_time + point_schedule_list[0].prep_time + point_schedule_list[0].loading_time
            
            for i in range(1, len(point_schedule_list)):
                current = point_schedule_list[i]
                arrival_time = current.travel_time
                
                if arrival_time < cumulative_time:
                    # 需要排队
                    queue_time = cumulative_time - arrival_time
                    current.set_queue_time(queue_time)
                    cumulative_time = cumulative_time + current.prep_time + current.loading_time
                else:
                    # 无需排队
                    current.set_queue_time(0)
                    cumulative_time = arrival_time + current.prep_time + current.loading_time
        
        return schedules
    
    def _balance_load(self, schedules: List[VehicleSchedule]) -> List[VehicleSchedule]:
        """
        负载均衡优化
        尝试将时间最长的车辆调整到其他装货点
        """
        max_iterations = 10
        
        for iteration in range(max_iterations):
            # 找到耗时最长的车辆
            max_schedule = max(schedules, key=lambda s: s.total_time)
            max_time_before = max_schedule.total_time
            
            # 尝试为该车选择其他装货点
            best_alternative = None
            best_alternative_time = max_time_before
            
            for point in self.loading_points:
                # 跳过当前装货点
                if point.id == max_schedule.loading_point_id:
                    continue
                
                # 检查限制
                restricted_points = self.vehicle_point_restrictions.get(max_schedule.vehicle_id, set())
                if point.id in restricted_points:
                    continue
                
                # 计算在新装货点的时间
                distance = self.distance_matrix.get(max_schedule.vehicle_id, {}).get(point.name, 0)
                prep_time = self.prep_time_matrix.get(max_schedule.vehicle_id, {}).get(point.name, 0)
                travel_time = (distance / max_schedule.vehicle_speed) * 60 if max_schedule.vehicle_speed > 0 else 0
                
                # 估算排队时间（假设该点当前的车辆都先到）
                estimated_queue = 0
                for other in schedules:
                    if other.loading_point_id == point.id and other.vehicle_id != max_schedule.vehicle_id:
                        if other.travel_time <= travel_time:
                            estimated_queue += other.prep_time + other.loading_time
                
                total_time = travel_time + prep_time + estimated_queue + max_schedule.loading_time
                
                if total_time < best_alternative_time:
                    best_alternative_time = total_time
                    best_alternative = {
                        'point': point,
                        'distance': distance,
                        'prep_time': prep_time
                    }
            
            # 如果找到更好的装货点，则切换
            if best_alternative and best_alternative_time < max_time_before * 0.95:  # 至少改善5%
                max_schedule.loading_point_id = best_alternative['point'].id
                max_schedule.loading_point_name = best_alternative['point'].name
                max_schedule.set_distance_and_prep(best_alternative['distance'], best_alternative['prep_time'])
                
                # 重新计算排队时间
                schedules = self._calculate_queue_times(schedules)
            else:
                # 无法改善，退出
                break
        
        return schedules
    
    def _generate_statistics(self, schedules: List[VehicleSchedule]) -> Dict:
        """生成统计信息"""
        if not schedules:
            return {
                "车辆数量": 0,
                "装货点数量": 0,
                "总货物数": 0,
                "最长装货时间(分钟)": 0,
                "最短装货时间(分钟)": 0,
                "平均装货时间(分钟)": 0,
                "总装货时间(分钟)": 0
            }
        
        total_times = [s.total_time for s in schedules]
        total_goods = sum(len(s.goods) for s in schedules)
        used_points = len(set(s.loading_point_id for s in schedules))
        
        return {
            "车辆数量": len(schedules),
            "装货点数量": used_points,
            "总货物数": total_goods,
            "最长装货时间(分钟)": round(max(total_times), 2),
            "最短装货时间(分钟)": round(min(total_times), 2),
            "平均装货时间(分钟)": round(sum(total_times) / len(total_times), 2),
            "总装货时间(分钟)": round(sum(total_times), 2)
        }
    
    def get_point_name(self, point_id: str) -> str:
        """根据装货点ID获取名称"""
        for point in self.loading_points:
            if point.id == point_id:
                return point.name
        return point_id

