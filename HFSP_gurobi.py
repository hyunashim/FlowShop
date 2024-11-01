import gurobipy as gp
from gurobipy import GRB
import matplotlib.pyplot as plt

# 데이터 정의
J = range(1, 4)  # job 집합: {1, 2, 3}
K = range(1, 3)  # stage 집합: {1, 2}
s = 2  # 전체 stage 수
Mk = {1: 2, 2: 2}  # 각 stage별 기계 수
U = 10000  # Big M

# 작업별 처리시간 데이터
pjk = {
    (1, 1): 4, (1, 2): 3,  # Job 1
    (2, 1): 5, (2, 2): 4,  # Job 2
    (3, 1): 3, (3, 2): 6   # Job 3
}

# 작업 간 셋업 시간 데이터
setup_time = {
    1: {2: 6, 3: 6},  # Job 1에서 Job 2나 3으로 변경 시 셋업시간
    2: {1: 6, 3: 6},  # Job 2에서 Job 1이나 3으로 변경 시 셋업시간
    3: {1: 6, 2: 6}   # Job 3에서 Job 1이나 2로 변경 시 셋업시간
}

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


# 제약식 (1): Makespan 정의 - 수정
for j in J:
    model.addConstr(tjk[j,s] + pjk[j,s] <= Cmax)  # 마지막 stage의 완료시간만 고려
# 제약식 (2): stage 간 선행관계
for j in J:
    for k in range(1, s):
        model.addConstr(tjk[j,k] + pjk[j,k] <= tjk[j,k+1])


# 제약식 (3) 수정
for g in J:
    for h in J:
        if g != h:
            for k in K:
                for m in range(1, Mk[k] + 1):
                    # g가 h보다 먼저 처리되는 경우
                    model.addConstr(
                        tjk[h,k] >= tjk[g,k] + pjk[g,k] + setup_time[g][h] - 
                        U * (3 - xjkm[g,k,m] - xjkm[h,k,m] - yghk[g,h,k])
                    )
                    # h가 g보다 먼저 처리되는 경우
                    model.addConstr(
                        tjk[h,k] + pjk[h,k] + setup_time[h][g] <= tjk[g,k] + 
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

# 모델 최적화
model.optimize()

# 결과 출력
if model.status == GRB.OPTIMAL:
    print(f'\nMakespan: {Cmax.X:.2f}')
    
    fig, ax = plt.subplots(figsize=(12, 6))
    colors = {'job': ['#FF9999', '#99FF99', '#9999FF'], 'setup': 'white'}
    
    y_positions = {
        (1,1): 4, (1,2): 3,
        (2,1): 2, (2,2): 1
    }
    
    # 각 기계별로 작업 순서 정렬
    machine_jobs = {(k,m): [] for k in K for m in range(1, Mk[k] + 1)}
    
    # 작업 할당 및 시작 시간 수집
    for j in J:
        for k in K:
            for m in range(1, Mk[k] + 1):
                if xjkm[j,k,m].X > 0.5:
                    machine_jobs[k,m].append((j, tjk[j,k].X))
    
    # 각 기계별로 시작 시간 순으로 정렬
    for k,m in machine_jobs:
        machine_jobs[k,m].sort(key=lambda x: x[1])
        jobs = machine_jobs[k,m]
        
        # 각 작업 그리기
        for i in range(len(jobs)):
            j = jobs[i][0]
            start_time = jobs[i][1]
            y_pos = y_positions[k,m]
            
            # 작업 블록
            ax.barh(y_pos, pjk[j,k], left=start_time,
                   height=0.8, color=colors['job'][j-1],
                   edgecolor='black')
            
            # 작업 레이블
            ax.text(start_time + pjk[j,k]/2, y_pos,
                   f'J{j}', ha='center', va='center')
            
            # 셋업 시간 블록 (다음 작업이 있는 경우)
            if i < len(jobs) - 1:
                next_j = jobs[i+1][0]
                setup_start = start_time + pjk[j,k]
                setup_time_val = setup_time[j][next_j]
                
                ax.barh(y_pos, setup_time_val, left=setup_start,
                       height=0.8, color='white',
                       edgecolor='black', hatch='//')
                ax.text(setup_start + setup_time_val/2, y_pos,
                       'S', ha='center', va='center')
    
    ax.set_ylim(0.5, 4.5)
    ax.set_xlabel('Time')
    ax.set_ylabel('Machines')
    
    y_labels = {
        4: 'Stage1-M1',
        3: 'Stage1-M2',
        2: 'Stage2-M1',
        1: 'Stage2-M2'
    }
    ax.set_yticks(list(y_labels.keys()))
    ax.set_yticklabels(list(y_labels.values()))
    
    ax.grid(True, axis='x', linestyle='--', alpha=0.7)
    plt.title('Hybrid Flowshop Schedule Gantt Chart')
    
    # 범례
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=colors['job'][i-1], edgecolor='black', label=f'Job {i}')
        for i in J
    ]
    legend_elements.append(
        Patch(facecolor='white', edgecolor='black', hatch='//', label='Setup')
    )
    ax.legend(handles=legend_elements, bbox_to_anchor=(1.05, 1), loc='upper left')
    
    plt.tight_layout()
    plt.show()
    
    # 상세 스케줄 출력
    print("\n상세 스케줄:")
    for k,m in sorted(machine_jobs.keys()):
        print(f"\nStage {k}, Machine {m}:")
        for j, start_time in sorted(machine_jobs[k,m], key=lambda x: x[1]):
            print(f"Job {j}: 시작={start_time:.1f}, 종료={start_time + pjk[j,k]:.1f}")
