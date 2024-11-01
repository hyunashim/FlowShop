from typing import Dict, List, Union, Optional, Tuple
import matplotlib.pyplot as plt
import numpy as np


class Job:
    def __init__(self, job_type: str, job_id: int):
        self.type = job_type
        self.id = job_id
        self.start_time = 0
        self.completion_time = 0
        self.operation_times: Dict[str, Dict[str, int]] = {}

class Machine:
    def __init__(self, machine_id: str, allowed_jobs: Union[str, List[str]]):
        self.machine_id = machine_id
        self.allowed_jobs = allowed_jobs
        self.jobs: List[Job] = []
        self.cumulative_time = 0

class Operation:
    def __init__(self, operation_id: str, allowed_machines: Dict[str, Union[str, List[str]]]):
        self.operation_id = operation_id
        self.machines: List[Machine] = []
        for machine_id, allowed_jobs in allowed_machines.items():
            self.machines.append(Machine(machine_id, allowed_jobs))

def create_operations(allowed_machines: Dict[str, Dict[str, Union[str, List[str]]]]) -> List[Operation]:
    operations = []
    for operation_id, machines in allowed_machines.items():
        operations.append(Operation(operation_id, machines))
    return operations

def create_job_list(demand: Dict[str, int]) -> List[Job]:
    jobs = []
    job_id = 1
    for job_type, count in demand.items():
        for _ in range(count):
            jobs.append(Job(job_type, job_id))
            job_id += 1
    return jobs

def calculate_total_processing_time(job_type: str, processing_time: Dict[str, List[int]]) -> int:
    return sum(processing_time[job_type])

def apply_SPT_rule(jobs: List[Job], processing_time: Dict[str, List[int]]) -> List[Job]:
    job_processing_times = []
    for job in jobs:
        total_time = calculate_total_processing_time(job.type, processing_time)
        job_processing_times.append((job, total_time))
    
    sorted_jobs = [job for job, _ in sorted(job_processing_times, key=lambda x: x[1])]
    
    for job in sorted_jobs:
        total_time = calculate_total_processing_time(job.type, processing_time)
        print(f"Job {job.id} (Type: {job.type}, Total Processing Time: {total_time})")
    
    return sorted_jobs

def apply_LPT_rule(jobs: List[Job], processing_time: Dict[str, List[int]]) -> List[Job]:
    job_processing_times = []
    for job in jobs:
        total_time = calculate_total_processing_time(job.type, processing_time)
        job_processing_times.append((job, total_time))
    
    sorted_jobs = [job for job, _ in sorted(job_processing_times, key=lambda x: -x[1])]
    
    for job in sorted_jobs:
        total_time = calculate_total_processing_time(job.type, processing_time)
        print(f"Job {job.id} (Type: {job.type}, Total Processing Time: {total_time})")
    
    return sorted_jobs

def get_available_machines_for_job(job: Job, operation: Operation) -> List[Machine]:
    available_machines = []
    for machine in operation.machines:
        if isinstance(machine.allowed_jobs, str):
            if machine.allowed_jobs == job.type:
                available_machines.append(machine)
        else:
            if job.type in machine.allowed_jobs:
                available_machines.append(machine)
    return available_machines

def find_machine_with_min_time(available_machines: List[Machine], prev_operation_end: int = 0) -> Tuple[Machine, int]:
    selected_machine = None
    earliest_start_time = float('inf')
    
    for machine in available_machines:
        possible_start_time = max(machine.cumulative_time, prev_operation_end)
        if possible_start_time < earliest_start_time:
            earliest_start_time = possible_start_time
            selected_machine = machine
            
    return selected_machine, earliest_start_time

def assign_job_to_machine(job: Job, operation: Operation, processing_time: Dict[str, List[int]], 
                         setup_time: Dict[str, Dict[str, int]], prev_operation_end: int = 0) -> Optional[Machine]:
    available_machines = get_available_machines_for_job(job, operation)
    
    if not available_machines:
        print(f"No available machines for Job {job.id} (Type: {job.type}) in {operation.operation_id}")
        return None
    
    selected_machine, start_time = find_machine_with_min_time(available_machines, prev_operation_end)
    
    if not selected_machine:
        return None
    
    # 셋업 시간 계산
    setup_duration = 0
    if selected_machine.jobs:  # 이전 작업이 있는 경우
        prev_job_type = selected_machine.jobs[-1].type
        setup_duration = setup_time[prev_job_type][job.type]  # 딕셔너리에서 셋업 시간 가져오기
        if setup_duration > 0:
            print(f"Setup time added: {setup_duration} (Type change from {prev_job_type} to {job.type})")
    
    # 시작 시간 갱신 (셋업 시간 포함)
    start_time = max(selected_machine.cumulative_time + setup_duration, prev_operation_end)
        
    op_index = int(operation.operation_id.split('_')[-1]) - 1
    job_processing_time = processing_time[job.type][op_index]
    
    end_time = start_time + job_processing_time
    selected_machine.jobs.append(job)
    selected_machine.cumulative_time = end_time
    
    job.operation_times[operation.operation_id] = {
        'start': start_time,
        'end': end_time,
        'setup_time': setup_duration
    }
    
    return selected_machine

def schedule_all_jobs(jobs: List[Job], operations: List[Operation], processing_time: Dict[str, List[int]], 
                     setup_time: Dict[str, Dict[str, int]], rule: str = 'SPT'):
    if rule == 'SPT':
        sorted_jobs = apply_SPT_rule(jobs, processing_time)
    elif rule == 'LPT':
        sorted_jobs = apply_LPT_rule(jobs, processing_time)
    else:
        raise ValueError("Invalid rule. Choose either 'SPT' or 'LPT'.")
    
    operations_order = sorted(operations, key=lambda x: x.operation_id)
    
    for job in sorted_jobs:
        prev_end_time = 0
        for operation in operations_order:
            assigned_machine = assign_job_to_machine(job, operation, processing_time, setup_time, prev_end_time)
            if assigned_machine:
                prev_end_time = job.operation_times[operation.operation_id]['end']
            else:
                print(f"Failed to schedule Job {job.id} in {operation.operation_id}")
def create_gantt_chart(operations: List[Operation], jobs: List[Job], rule: str):
    """
    Operation별 Machine의 작업 일정을 간트 차트로 시각화
    
    Args:
        operations: Operation 객체 리스트
        jobs: Job 객체 리스트
        rule: 사용된 스케줄링 규칙 (SPT/LPT)
    """
    # 전체 machine 수 계산
    total_machines = sum(len(operation.machines) for operation in operations)
    
    # 색상 설정
    colors = {'A': 'skyblue', 'B': 'lightgreen'}
    setup_color = 'red'
    
    # 그래프 크기 설정
    plt.figure(figsize=(15, 8))
    
    # y축 레이블 생성
    y_labels = []
    machine_positions = {}
    current_pos = 0
    
    for op_idx, operation in enumerate(operations):
        for machine in operation.machines:
            y_labels.append(f"{operation.operation_id}-{machine.machine_id}")
            machine_positions[(operation.operation_id, machine.machine_id)] = current_pos
            current_pos += 1
    
    # makespan 계산
    makespan = max(machine.cumulative_time for operation in operations 
                  for machine in operation.machines)
    
    # 각 작업 블록 그리기
    for operation in operations:
        for machine in operation.machines:
            y_pos = machine_positions[(operation.operation_id, machine.machine_id)]
            
            prev_end_time = 0
            for job in machine.jobs:
                times = job.operation_times[operation.operation_id]
                start_time = times['start']
                end_time = times['end']
                setup_time = times['setup_time']
                
                # 셋업 시간이 있는 경우 표시
                if setup_time > 0:
                    plt.barh(y_pos, setup_time, 
                            left=start_time - setup_time, 
                            color=setup_color, alpha=0.3,
                            edgecolor='black')
                
                # 작업 시간 표시
                plt.barh(y_pos, end_time - start_time, 
                        left=start_time, 
                        color=colors[job.type],
                        edgecolor='black',
                        label=f'Job {job.id} ({job.type})')
                
                # 작업 ID 표시
                plt.text(start_time + (end_time - start_time)/2, y_pos, 
                        f'J{job.id}', 
                        ha='center', va='center')
    
    # 그래프 설정
    plt.title(f'Gantt Chart ({rule} Rule)', pad=20)
    plt.xlabel('Time')
    plt.ylabel('Machine')
    plt.grid(True, axis='x')
    
    # y축 설정
    plt.yticks(range(total_machines), y_labels)
    
    # x축 범위 설정
    plt.xlim(-1, makespan + 1)
    
    # 범례 설정 (중복 제거)
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys(), 
              loc='upper right', bbox_to_anchor=(1.15, 1))
    
    plt.tight_layout()
    plt.show()




# 테스트
if __name__ == "__main__":
    demand = {
        'A': 4,
        'B': 6
    }

    allowed_machines = {
        'OP_1': {'M_1': 'A', 'M_2': 'A', 'M_3': 'B', 'M_4': 'B'},
        'OP_2': {'M_1': 'A', 'M_2': 'A', 'M_3': ['A', 'B'], 'M_4': ['A','B']}
    }

    processing_time = {
        'A': [3, 3],  # OP_1, OP_2 소요시간
        'B': [6, 6]   # OP_1, OP_2 소요시간
    }

    setup_time = {
        'A': {'A': 0, 'B': 6},
        'B': {'A': 6, 'B': 0}
    }

    # SPT 규칙 테스트 및 간트 차트 생성
    print("\n=== SPT Rule Results ===")
    operations_spt = create_operations(allowed_machines)
    jobs_spt = create_job_list(demand)
    schedule_all_jobs(jobs_spt, operations_spt, processing_time, setup_time, 'SPT')
   # print_schedule_results(operations_spt, jobs_spt, 'SPT')
    create_gantt_chart(operations_spt, jobs_spt, 'SPT')

    # LPT 규칙 테스트 및 간트 차트 생성
    print("\n=== LPT Rule Results ===")
    operations_lpt = create_operations(allowed_machines)
    jobs_lpt = create_job_list(demand)
    schedule_all_jobs(jobs_lpt, operations_lpt, processing_time, setup_time, 'LPT')
    #print_schedule_results(operations_lpt, jobs_lpt, 'LPT')
    create_gantt_chart(operations_lpt, jobs_lpt, 'LPT')
