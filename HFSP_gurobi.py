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

# 제약식 (1): Makespan 정의
for j in J:
    for k in K:
        model.addConstr(tjk[j,k] + pjk[j,k] <= Cmax)

# 제약식 (2): stage 간 선행관계
for j in J:
    for k in range(1, s):
        model.addConstr(tjk[j,k] + pjk[j,k] <= tjk[j,k+1])

# 제약식 (3): 같은 기계에서의 작업 순서 관계 (셋업 시간 포함)
for g in J:
    for h in J:
        if g != h:  # 서로 다른 작업 간에
            for k in K:
                for m in range(1, Mk[k] + 1):
                    model.addConstr(
                        tjk[g,k] + pjk[g,k] + setup_time[g][h] <= tjk[h,k] + 
                        U * (3 - xjkm[g,k,m] - xjkm[h,k,m] - yghk[g,h,k])
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
    
    # 간트차트 생성
    fig, ax = plt.subplots(figsize=(12, 6))
    colors = ['#FF9999', '#99FF99', '#9999FF']
    
    y_positions = {
        (1,1): 4, (1,2): 3,  # Stage 1의 기계들
        (2,1): 2, (2,2): 1   # Stage 2의 기계들
    }
    
    for j in J:
        for k in K:
            for m in range(1, Mk[k] + 1):
                if xjkm[j,k,m].X > 0.5:
                    start_time = tjk[j,k].X
                    duration = pjk[j,k]
                    y_pos = y_positions[k,m]
                    
                    ax.barh(y_pos, duration, left=start_time, 
                           height=0.8, color=colors[j-1],
                           edgecolor='black')
                    ax.text(start_time + duration/2, y_pos, f'J{j}',
                          ha='center', va='center')
    
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
    plt.show()
    
    # 상세 스케줄 출력
    print("\n상세 스케줄:")
    for j in J:
        print(f'\nJob {j}:')
        for k in K:
            for m in range(1, Mk[k] + 1):
                if xjkm[j,k,m].X > 0.5:
                    print(f'Stage {k}, Machine {m}: 시작={tjk[j,k].X:.1f}, ' +
                          f'종료={tjk[j,k].X + pjk[j,k]:.1f}')

else:
    print('최적해를 찾을 수 없습니다.')
