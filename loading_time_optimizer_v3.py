"""
装货时间优化算法 V3
每辆车只能在一个装货点装货
为每辆车选择最优装货点，最小化最长装货时间
"""
import pandas as pd
from typing import List, Dict, Tuple, Set


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
        
        # 第一步：迭代为每辆车选择最优装货点（考虑预期排队影响）
        for vehicle_id, goods_ids in sorted_vehicles:
            if not goods_ids:
                continue

            vehicle_speed = self.vehicle_speeds.get(vehicle_id, 60.0)

            best_option = None

            for point in self.loading_points:
                # 检查车辆装货点限制
                restricted_points = self.vehicle_point_restrictions.get(vehicle_id, set())
                if point.id in restricted_points:
                    continue

                candidate_schedule = self._create_schedule(
                    vehicle_id,
                    goods_ids,
                    point,
                    vehicle_speed
                )

                queue_time, total_time = self._simulate_point_assignment(
                    candidate_schedule,
                    vehicle_schedules
                )

                if best_option is None or total_time < best_option['total_time']:
                    best_option = {
                        'schedule': candidate_schedule,
                        'queue_time': queue_time,
                        'total_time': total_time
                    }

            if best_option is None:
                print(f"警告: 车辆 {vehicle_id} 无可用装货点")
                continue

            schedule = best_option['schedule']
            schedule.set_queue_time(best_option['queue_time'])
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
    
    def _clone_schedule(self, schedule: VehicleSchedule) -> VehicleSchedule:
        """创建车辆计划的深拷贝"""
        cloned = VehicleSchedule(
            schedule.vehicle_id,
            schedule.loading_point_id,
            schedule.loading_point_name,
            schedule.vehicle_speed
        )
        cloned.set_distance_and_prep(schedule.distance, schedule.prep_time)
        for good in schedule.goods:
            cloned.add_good(good["货物ID"], good["货物名称"], good["装货时间"])
        cloned.set_queue_time(schedule.queue_time)
        return cloned

    def _create_schedule(self, vehicle_id: str, goods_ids: List[str],
                         point: LoadingPoint, vehicle_speed: float) -> VehicleSchedule:
        """构建指定车辆在某装货点的计划（不含排队）"""
        schedule = VehicleSchedule(vehicle_id, point.id, point.name, vehicle_speed)
        distance = self.distance_matrix.get(vehicle_id, {}).get(point.name, 0)
        prep_time = self.prep_time_matrix.get(vehicle_id, {}).get(point.name, 0)
        schedule.set_distance_and_prep(distance, prep_time)

        for good_id in goods_ids:
            good_info = self.goods_info.get(good_id, {})
            good_name = good_info.get("name", good_id)
            loading_time = self.goods_loading_time.get(good_id, 0)
            schedule.add_good(good_id, good_name, loading_time)

        return schedule

    def _simulate_point_assignment(self, candidate_schedule: VehicleSchedule,
                                   existing_schedules: List[VehicleSchedule]) -> Tuple[float, float]:
        """模拟候选计划加入装货点后的排队情况"""
        point_id = candidate_schedule.loading_point_id
        simulated_list = [
            self._clone_schedule(s)
            for s in existing_schedules
            if s.loading_point_id == point_id
        ]

        simulated_candidate = self._clone_schedule(candidate_schedule)
        simulated_list.append(simulated_candidate)

        simulated_list.sort(key=lambda s: s.travel_time)

        point_available_time = 0.0
        for schedule in simulated_list:
            arrival = schedule.travel_time
            start_time = max(arrival, point_available_time)
            queue_time = max(0.0, start_time - arrival)
            schedule.set_queue_time(queue_time)
            point_available_time = start_time + schedule.prep_time + schedule.loading_time

        return simulated_candidate.queue_time, simulated_candidate.total_time

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
            point_schedule_list.sort(key=lambda s: s.travel_time)

            point_available_time = 0.0
            for schedule in point_schedule_list:
                arrival = schedule.travel_time
                start_time = max(arrival, point_available_time)
                queue_time = max(0.0, start_time - arrival)
                schedule.set_queue_time(queue_time)
                point_available_time = start_time + schedule.prep_time + schedule.loading_time

        return schedules
    
    def _balance_load(self, schedules: List[VehicleSchedule]) -> List[VehicleSchedule]:
        """
        负载均衡优化
        尝试将时间最长的车辆调整到其他装货点
        """
        if not schedules:
            return schedules

        max_iterations = 10

        # 初始统一计算一次排队
        schedules = self._calculate_queue_times(schedules)

        for _ in range(max_iterations):
            current_max = max(s.total_time for s in schedules)
            improved = False

            # 优先尝试改善耗时最长的车辆
            for schedule in sorted(schedules, key=lambda s: s.total_time, reverse=True):
                goods_ids = [g["货物ID"] for g in schedule.goods]
                if not goods_ids:
                    continue

                restricted_points = self.vehicle_point_restrictions.get(schedule.vehicle_id, set())
                best_candidate = None

                for point in self.loading_points:
                    if point.id == schedule.loading_point_id or point.id in restricted_points:
                        continue

                    candidate_schedule = self._create_schedule(
                        schedule.vehicle_id,
                        goods_ids,
                        point,
                        schedule.vehicle_speed
                    )

                    simulated_schedules = [
                        self._clone_schedule(s) for s in schedules if s.vehicle_id != schedule.vehicle_id
                    ]
                    simulated_schedules.append(self._clone_schedule(candidate_schedule))
                    simulated_schedules = self._calculate_queue_times(simulated_schedules)

                    if not simulated_schedules:
                        continue

                    simulated_max = max(s.total_time for s in simulated_schedules)

                    if simulated_max + 1e-6 < current_max:
                        if (best_candidate is None or simulated_max < best_candidate['max_time']):
                            best_candidate = {
                                'schedule': candidate_schedule,
                                'max_time': simulated_max
                            }

                if best_candidate:
                    original_index = schedules.index(schedule)
                    schedules[original_index] = best_candidate['schedule']
                    schedules = self._calculate_queue_times(schedules)
                    improved = True
                    break

            if not improved:
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

