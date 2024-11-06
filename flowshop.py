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
    def __init__(self, machine_id: str, allowed_jobs: List[str]):
        self.machine_id = machine_id
        self.allowed_jobs = allowed_jobs
        self.jobs: List[Job] = []
        self.cumulative_time = 0

class Operation:
    def __init__(self, operation_id: str, allowed_machines: Dict[str, List[str]]):
        self.operation_id = operation_id
        self.machines: List[Machine] = []
        for machine_id, allowed_jobs in allowed_machines.items():
            self.machines.append(Machine(machine_id, allowed_jobs))

def create_operations(allowed_machines: Dict[str, Dict[str, List[str]]]) -> List[Operation]:
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

def calculate_total_processing_time(job_type: str, processing_time: Dict[str, Dict[str, List[int]]]) -> int:
    total_time = 0
    for operation, machines in processing_time.items():
        min_time = float('inf')
        for machine_times in machines.values():
            if len(machine_times) == 1:  # 단일 시간값
                time = machine_times[0]
            else:  # 작업 타입별 다른 시간값
                time = machine_times[0] if job_type == 'A' else machine_times[1]
            min_time = min(min_time, time)
        total_time += min_time
    return total_time

def apply_SPT_rule(jobs: List[Job], processing_time: Dict[str, Dict[str, List[int]]]) -> List[Job]:
    job_processing_times = []
    for job in jobs:
        total_time = calculate_total_processing_time(job.type, processing_time)
        job_processing_times.append((job, total_time))
    
    sorted_jobs = [job for job, _ in sorted(job_processing_times, key=lambda x: x[1])]
    
    for job in sorted_jobs:
        total_time = calculate_total_processing_time(job.type, processing_time)
        print(f"Job {job.id} (Type: {job.type}, Total Processing Time: {total_time})")
    
    return sorted_jobs

def apply_LPT_rule(jobs: List[Job], processing_time: Dict[str, Dict[str, List[int]]]) -> List[Job]:
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

def assign_job_to_machine(job: Job, operation: Operation, processing_time: Dict[str, Dict[str, List[int]]], 
                         setup_time: Dict[str, Dict[str, int]], prev_operation_end: int = 0) -> Optional[Machine]:
    available_machines = get_available_machines_for_job(job, operation)
    
    if not available_machines:
        print(f"No available machines for Job {job.id} (Type: {job.type}) in {operation.operation_id}")
        return None
    
    selected_machine, start_time = find_machine_with_min_time(available_machines, prev_operation_end)
    
    if not selected_machine:
        return None
    
    setup_duration = 0
    if selected_machine.jobs:
        prev_job_type = selected_machine.jobs[-1].type
        setup_duration = setup_time[prev_job_type][job.type]
    
    start_time = max(selected_machine.cumulative_time + setup_duration, prev_operation_end)

    machine_times = processing_time[operation.operation_id][selected_machine.machine_id]
    if len(machine_times) == 1:  # 단일 시간값
        job_processing_time = machine_times[0]
    else:  # 작업 타입별 다른 시간값
        job_processing_time = machine_times[0] if job.type == 'A' else machine_times[1]
    
    end_time = start_time + job_processing_time
    selected_machine.jobs.append(job)
    selected_machine.cumulative_time = end_time
    
    job.operation_times[operation.operation_id] = {
        'start': start_time,
        'end': end_time,
        'setup_time': setup_duration
    }
    
    return selected_machine

def schedule_all_jobs(jobs: List[Job], operations: List[Operation], processing_time: Dict[str, Dict[str, List[int]]], 
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
    colors = {'A': '#FF9999', 'B': '#66B2FF'}
    setup_color = 'black'
    
    makespan = max(machine.cumulative_time for operation in operations 
                  for machine in operation.machines)

    fig, axes = plt.subplots(len(operations), 1, figsize=(15, 9))
    
    for op_idx, operation in enumerate(operations):
        ax = axes[op_idx]

        y_labels = []
        machine_positions = {}
        current_pos = 0
        
        for machine in operation.machines:
            y_labels.append(machine.machine_id)
            machine_positions[machine.machine_id] = current_pos
            current_pos += 1

        for machine in operation.machines:
            y_pos = machine_positions[machine.machine_id]
            
            for job in machine.jobs:
                times = job.operation_times[operation.operation_id]
                start_time = times['start']
                end_time = times['end']
                setup_time = times['setup_time']

                if setup_time > 0:
                    ax.barh(y_pos, setup_time, 
                           left=start_time - setup_time, 
                           color=setup_color,
                           alpha=0.9,
                           edgecolor='none')

                ax.barh(y_pos, end_time - start_time, 
                       left=start_time, 
                       color=colors[job.type],
                       edgecolor='black',
                       linewidth=1)
                
                ax.text(start_time + (end_time - start_time)/2, y_pos, 
                       f'Job {job.id}', 
                       ha='center', va='center',
                       fontsize=10)

        ax.set_title(f'{operation.operation_id}', pad=5)
        if op_idx == len(operations)-1:
            ax.set_xlabel('Time')
        ax.set_ylabel('Machine')
        ax.grid(True, axis='x', alpha=0.3)
        
        ax.set_yticks(range(len(operation.machines)))
        ax.set_yticklabels(y_labels)
        
        ax.set_xlim(-1, makespan + 3)
        
        ax.axvline(x=makespan, color='red', linestyle='--', alpha=0.5)
        if op_idx == 0:
            ax.text(makespan + 0.2, len(operation.machines) - 1, 
                    f'Makespan: {makespan}', 
                    color='red', va='top', ha='left')
        
        if op_idx == 0:
            legend_elements = [
                plt.Rectangle((0, 0), 1, 1, facecolor=colors['A'], 
                            label='Type A', edgecolor='black'),
                plt.Rectangle((0, 0), 1, 1, facecolor=colors['B'],
                            label='Type B', edgecolor='black'),
                plt.Rectangle((0, 0), 1, 1, facecolor=setup_color,
                            label='Setup Time', edgecolor='none')
            ]
            ax.legend(handles=legend_elements, 
                     loc='upper right', 
                     bbox_to_anchor=(1.13, 1))
    
    plt.suptitle(f'Gantt Chart ({rule} Rule)   (Makespan: {makespan})', y=0.95, fontsize=12)
    
    plt.tight_layout()
    plt.subplots_adjust(top=0.85)
    
    plt.show()

# 테스트
if __name__ == "__main__":
    demand = {
        'A': 4,
        'B': 6
    }

    allowed_machines = {
        'OP_1': {
            'M_1': ['A', 'B'], 
            'M_2': ['A', 'B'], 
            'M_3': ['A', 'B'], 
            'M_4': ['A', 'B']
        },
        'OP_2': {
            'M_1': ['A'], 
            'M_2': ['A'], 
            'M_3': ['A', 'B'], 
            'M_4': ['A', 'B']
        }
    }

    processing_time = {
        'OP_1': {
            'M_1': [3, 6], 
            'M_2': [3, 6], 
            'M_3': [3, 6], 
            'M_4': [3, 6]
        },
        'OP_2': {
            'M_1': [3], 
            'M_2': [3], 
            'M_3': [3, 6], 
            'M_4': [3, 6]
        }
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
    create_gantt_chart(operations_spt, jobs_spt, 'SPT')

    # LPT 규칙 테스트 및 간트 차트 생성
    print("\n=== LPT Rule Results ===")
    operations_lpt = create_operations(allowed_machines)
    jobs_lpt = create_job_list(demand)
    schedule_all_jobs(jobs_lpt, operations_lpt, processing_time, setup_time, 'LPT')
    create_gantt_chart(operations_lpt, jobs_lpt, 'LPT')
