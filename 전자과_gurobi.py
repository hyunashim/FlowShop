import gurobipy as gp
from gurobipy import GRB
import matplotlib.pyplot as plt

# 데이터 정의
demand = {'A': 4, 'B': 6}
job_types = list(demand.keys())  # ['A', 'B']
J = range(1, sum(demand.values()) + 1)  # range(1, 11) - 총 10개 작업
K = range(1, 3)  # stage 집합: {1, 2}
s = 2  # 전체 stage 수

# 기계 정보
allowed_machines = {
    'OP_1': {'M_1': 'A', 'M_2': 'A', 'M_3': 'B', 'M_4': 'B'},
    'OP_2': {'M_1': 'A', 'M_2': 'A', 'M_3': ['A', 'B'], 'M_4': ['A','B']}
}
Mk = {1: 4, 2: 4}  # 각 stage별 기계 수

# 작업별 처리시간
processing_time = {
    'A': [4, 6],  # OP_1, OP_2 소요시간
    'B': [3, 1]   # OP_1, OP_2 소요시간
}

# 셋업 시간
setup_time = {
    'A': {'A': 0, 'B': 6},
    'B': {'A': 6, 'B': 0}
}

# job number를 type으로 매핑
job_to_type = {}
current_idx = 1
for jtype in job_types:
    for i in range(demand[jtype]):
        job_to_type[current_idx] = jtype
        current_idx += 1

# 작업별 처리시간 데이터 변환
pjk = {}
for j in J:
    job_type = job_to_type[j]
    pjk[j,1] = processing_time[job_type][0]  # OP_1 시간
    pjk[j,2] = processing_time[job_type][1]  # OP_2 시간

U = 10000  # Big M

# 모델 생성
model = gp.Model()

# 결정변수 생성
tjk = model.addVars(J, K, vtype=GRB.CONTINUOUS, name='t')
Cmax = model.addVar(vtype=GRB.CONTINUOUS, name='Cmax')

# 기계 할당 변수
xjkm = model.addVars(
    ((j, k, m) for j in J for k in K for m in range(1, Mk[k] + 1)),
    vtype=GRB.BINARY,
    name='x'
)

# 작업 순서 변수
yghk = model.addVars(
    ((g, h, k) for g in J for h in J for k in K if g != h),
    vtype=GRB.BINARY,
    name='y'
)

# 목적함수: makespan 최소화
model.setObjective(Cmax, GRB.MINIMIZE)

# 제약식 (1): Makespan 정의
for j in J:
    model.addConstr(tjk[j,s] + pjk[j,s] <= Cmax)

# 제약식 (2): stage 간 선행관계
for j in J:
    for k in range(1, s):
        model.addConstr(tjk[j,k] + pjk[j,k] <= tjk[j,k+1])

# 제약식 (3): 같은 기계에서의 작업 순서 관계 (셋업 포함)
# 제약식 (3) 수정
for g in J:
    for h in J:
        if g != h:
            for k in K:
                for m in range(1, Mk[k] + 1):
                    setup = setup_time[job_to_type[g]][job_to_type[h]]
                    # g가 h보다 먼저 처리되는 경우
                    model.addConstr(
                        tjk[h,k] >= tjk[g,k] + pjk[g,k] + setup - 
                        U * (3 - xjkm[g,k,m] - xjkm[h,k,m] - yghk[g,h,k])
                    )
                    # h가 g보다 먼저 처리되는 경우
                    model.addConstr(
                        tjk[g,k] >= tjk[h,k] + pjk[h,k] + setup - 
                        U * (3 - xjkm[g,k,m] - xjkm[h,k,m] - (1 - yghk[g,h,k]))
                    )
# 제약식 (4): 작업 순서의 상호배타성
for g in J:
    for h in J:
        if g != h:
            for k in K:
                model.addConstr(yghk[g,h,k] + yghk[h,g,k] <= 1)

# 제약식 (5): 각 작업은 각 stage에서 정확히 하나의 기계에 할당
for j in J:
    for k in K:
        model.addConstr(gp.quicksum(xjkm[j,k,m] for m in range(1, Mk[k] + 1)) == 1)

# 제약식 (6): 시작시간 비음수
for j in J:
    for k in K:
        model.addConstr(tjk[j,k] >= 0)

# 제약식 (7): 기계별 작업 타입 제약
for j in J:
    job_type = job_to_type[j]
    # Stage 1 (OP_1)
    for m in range(1, Mk[1] + 1):
        machine = f'M_{m}'
        if allowed_machines['OP_1'][machine] != job_type:
            model.addConstr(xjkm[j,1,m] == 0)
    
    # Stage 2 (OP_2)
    for m in range(1, Mk[2] + 1):
        machine = f'M_{m}'
        allowed_types = allowed_machines['OP_2'][machine]
        if isinstance(allowed_types, str):
            allowed_types = [allowed_types]
        if job_type not in allowed_types:
            model.addConstr(xjkm[j,2,m] == 0)

# 모델 최적화
model.optimize()
# 결과 출력 부분만 수정
if model.status == GRB.OPTIMAL:
    print(f'\nMakespan: {Cmax.X:.2f}')
    
    fig, ax = plt.subplots(figsize=(15, 8))
    colors = {'A': '#87CEEB', 'B': '#90EE90', 'setup': 'white'}
    
    y_positions = {
        (1,1): 8, (1,2): 7, (1,3): 6, (1,4): 5,
        (2,1): 4, (2,2): 3, (2,3): 2, (2,4): 1
    }
    
    # job number를 순차적으로 부여하기 위한 매핑
    job_mapping = {}
    current_id = 1
    # A 타입 작업 먼저 번호 부여
    for j in J:
        if job_to_type[j] == 'A':
            job_mapping[j] = current_id
            current_id += 1
    # B 타입 작업 번호 부여
    for j in J:
        if job_to_type[j] == 'B':
            job_mapping[j] = current_id
            current_id += 1
    
    # 각 기계별로 작업 순서 정렬
    machine_jobs = {(k,m): [] for k in K for m in range(1, Mk[k] + 1)}
    
    for j in J:
        for k in K:
            for m in range(1, Mk[k] + 1):
                if xjkm[j,k,m].X > 0.5:
                    machine_jobs[k,m].append((j, tjk[j,k].X))
    
    # 각 기계별로 시작 시간 순으로 정렬
    for k,m in machine_jobs:
        machine_jobs[k,m].sort(key=lambda x: x[1])
        jobs = machine_jobs[k,m]
        
        for i in range(len(jobs)):
            j = jobs[i][0]
            start_time = jobs[i][1]
            y_pos = y_positions[k,m]
            job_type = job_to_type[j]
            
            # 작업 블록
            ax.barh(y_pos, pjk[j,k], left=start_time,
                   height=0.8, color=colors[job_type],
                   edgecolor='black')
            
            # 작업 레이블 (순차적 번호로 표시)
            ax.text(start_time + pjk[j,k]/2, y_pos,
                   f'J{job_mapping[j]}', ha='center', va='center')
            
            # 셋업 시간 블록 (다음 작업이 있는 경우)
            if i < len(jobs) - 1:
                next_j = jobs[i+1][0]
                next_type = job_to_type[next_j]
                setup_start = start_time + pjk[j,k]
                setup_time_val = setup_time[job_type][next_type]
                
                if setup_time_val > 0:
                    ax.barh(y_pos, setup_time_val, left=setup_start,
                           height=0.8, color='white',
                           edgecolor='black', hatch='//')
                    ax.text(setup_start + setup_time_val/2, y_pos,
                           'S', ha='center', va='center')
    
    ax.set_ylim(0.5, 8.5)
    ax.set_xlabel('Time')
    ax.set_ylabel('Machines')
    
    y_labels = {
        8: 'OP_1-M_1',
        7: 'OP_1-M_2',
        6: 'OP_1-M_3',
        5: 'OP_1-M_4',
        4: 'OP_2-M_1',
        3: 'OP_2-M_2',
        2: 'OP_2-M_3',
        1: 'OP_2-M_4'
    }
    
    ax.set_yticks(list(y_labels.keys()))
    ax.set_yticklabels(list(y_labels.values()))
    
    ax.grid(True, axis='x', linestyle='--', alpha=0.7)
    plt.title('Gantt Chart ')
    
    # 범례
    legend_elements = [
        plt.Rectangle((0,0), 1, 1, facecolor=colors['A'], edgecolor='black', label='Job Type A'),
        plt.Rectangle((0,0), 1, 1, facecolor=colors['B'], edgecolor='black', label='Job Type B'),
        plt.Rectangle((0,0), 1, 1, facecolor='white', edgecolor='black', hatch='//', label='Setup')
    ]
    ax.legend(handles=legend_elements, bbox_to_anchor=(1.05, 1), loc='upper left')
    
    plt.tight_layout()
    plt.show()
