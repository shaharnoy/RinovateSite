from pyomo.environ import *
from coopr.pyomo import *
# Define the Pyomo model
model = ConcreteModel()

# SETS
model.RELATION_TYPES = Set(initialize=['FREE', 'SAME', 'PROTECTED', 'MUTEX', 'PARALLEL'])
model.S_tasksites = Set(initialize=['1','2']) # replace with the actual set of task sites
model.S_sourcelocation = Set(initialize=['3','4']) # replace with the actual set of Crafter source locations

model.K = Set(initialize=['1','2']) # replace with the actual set of task sites
model.S = model.S_tasksites | model.S_sourcelocation
model.M = Set(initialize=['1','2']) # replace with the actual set of task sites
model.R_materials = Set(initialize=['1','2']) # replace with the actual set of task sites
model.R_tool = Set(initialize=['1','2']) # replace with the actual set of task sites
model.R = model.R_materials | model.R_tool


# CONSTRAINTS
def no_empty_s(model):
    return ConstraintList(rule=(len(s) > 0 for s in model.S))
model.check_empty_s = no_empty_s

def no_empty_k(model):
    return ConstraintList(rule=(len(s) > 0 for s in model.K))
model.check_empty_k = no_empty_k

def no_empty_r(model):
    return ConstraintList(rule=(len(s) > 0 for s in model.R))
model.check_empty_r = no_empty_r
"""
def site_and_source_different(m):
    return len(m.S_tasksites.intersection(m.S_sourcelocation)) == 0
model.check_site_source_different = Constraint(rule=site_and_source_different)

def resource_material_or_tool(m):
    return len(m.R_materials & m.R_tool) == 0
model.check_resource_material_or_tool = Constraint(rule=resource_material_or_tool)

def all_different(m):
    return len(m.S | m.K | m.M | m.R) == len(m.S) + len(m.K) + len(m.M) + len(m.R)
model.check_all_different = Constraint(rule=all_different)
"""

##### PARAMETERS #####
## Time and Dates ##
model.T_day_start = Param(within=NonNegativeReals,default={'8'}) # Start Time for a given day
model.T_day_end = Param(within=NonNegativeReals, default={'14'},validate=lambda model, value: value > model.T_day_start) # End Time for a given day
model.U_WORKDAY = Param(initialize=model.T_day_end - model.T_day_start) # Workday times

## Todo: Add parameter for available days, currently the model assumes it all works in 1 day and all crafters have the same availability
## End - Time and Dates ##

## Location ##
model.lat_SITE = Param(model.S, within=Reals) # Latitude coordinates of site s
model.lng_SITE = Param(model.S, within=Reals) # Longitude coordinate of site s

model.D_DEFAULT_GoogleDirections = Param(model.S, model.S, within=NonNegativeReals) # Todo: Populate with data from Google API
model.D = Param(model.S, model.S, within=NonNegativeReals, default=lambda model, i, j: model.D_DEFAULT_GoogleDirections[i, j]) # Distance using Google API and type of commute

model.S_start_DEFAULT = Param(within=model.S_sourcelocation, mutable=True) # Default starting position of crafter m is its home base
model.S_start = Param(model.M, within=model.S_sourcelocation, default=lambda model, m: model.S_start_DEFAULT) # Starting position of crafter m

model.S_end_DEFAULT = Param(within=model.S_sourcelocation, mutable=True) # Default ending position of crafter m (assuming commute back to start location)
model.S_end = Param(model.M, within=model.S_sourcelocation, initialize=lambda model, m: model.S_end_DEFAULT if value(model.S_start[m]) == value(model.S_start_DEFAULT) else value(model.S_sourcelocation - model.S_start[m] + 1)) # Ending position of crafter m
## End - Location ##

# Time and Dates
model.T_day_start = Param(within=NonNegativeReals)
model.T_day_end = Param(within=NonNegativeReals, bounds=(model.T_day_start, None))
model.U_WORKDAY = Param(initialize=lambda model: model.T_day_end - model.T_day_start)

# Location
model.lat_SITE = Param(model.S)
model.lng_SITE = Param(model.S)
model.D_DEFAULT_GoogleDirections = Param(model.S, model.S, within=NonNegativeReals)
def D_default_rule(model, s1, s2):
    return model.D_DEFAULT_GoogleDirections[s1, s2] if (s1, s2) in model.D_DEFAULT_GoogleDirections else model.D_DEFAULT_GoogleDirections[s2, s1]
model.D = Param(model.S, model.S, within=NonNegativeReals, default=D_default_rule)
model.S_start_DEFAULT = Param(within=model.S_sourcelocation, mutable=True)
model.S_start = Param(model.M, within=model.S_sourcelocation, default=model.S_start_DEFAULT, mutable=True)
model.S_end_DEFAULT = Param(within=model.S_sourcelocation, mutable=True)
model.S_end = Param(model.M, within=model.S_sourcelocation, default=lambda model, m: model.S_start[m], mutable=True)

# Task Execution
model.S_task_DEFAULT = Param(within=model.S_tasksites, mutable=True)
model.S_task = Param(model.K, within=model.S_tasksites, default=model.S_task_DEFAULT, mutable=True)
model.U_exec_DEFAULT = Param(within=NonNegativeReals, mutable=True)
model.U_exec_DEFAULT_M = Param(model.M, within=NonNegativeReals, default=model.U_exec_DEFAULT, mutable=True)
model.U_exec = Param(model.K, model.M, within=NonNegativeReals, default=lambda model, k, m: model.U_exec_DEFAULT_M[m], mutable=True)

# Materials and tools
model.Q_task_DEFAULT = Param(within=NonNegativeReals, mutable=True)
model.Q_task_DEFAULT_R = Param(model.R, within=NonNegativeReals, default=model.Q_task_DEFAULT, mutable=True)
model.Q_task_DEFAULT_R_M = Param(model.R, model.M, within=NonNegativeReals, default=lambda model, r, m: model.Q_task_DEFAULT_R[r], mutable=True)
model.Q_task = Param(model.R, model.K, model.M, within=NonNegativeReals, default=lambda model, r, k, m: model.Q_task_DEFAULT_R_M[r, m], mutable=True)
model.Q_available_DEFAULT = Param(within=NonNegativeReals, mutable=True)
model.Q_available = Param(model.R, within=NonNegativeReals, default=model.Q_available_DEFAULT, mutable=True)


#Task Relations
P_UNIVERSE = Set(initialize=set((k1,k2) for k1 in K for k2 in K if k1 != k2)) # (auxiliary) set of all possible relations
P_ALL = Set(initialize=set((k1,k2,r) for k1,k2 in P_UNIVERSE for r in model.RELATION_TYPES)) # (auxiliary) set of all relations
P_free = Set(initialize=set((k1,k2,r) for k1,k2,r in P_ALL if r=='FREE')) # set of free precedence relations
P_same = Set(initialize=set((k1,k2,r) for k1,k2,r in P_ALL if r=='SAME')) # set of same-crafter precedence relations
P_prot = Set(initialize=set((k1,k2,r) for k1,k2,r in P_ALL if r=='PROTECTED')) # set of protected precedence relations
P_mutex = Set(initialize=set((k1,k2,r) for k1,k2,r in P_ALL if r=='MUTEX')) # set of mutual exclusion relations
P_parallel = Set(initialize=set((k1,k2,r) for k1,k2,r in P_ALL if r=='PARALLEL')) # set of parallel execution relations
P_prec = P_same | P_prot | P_free # set of all precedence relations

#Auxiliary sets
model.N_crafter = Param(model.M, within=NonNegativeIntegers, default=1)
N_crafter_max = Param(model.M, initialize=lambda model, m: model.ALG_N[m] if model.ALG_USE == 1 else model.N_crafter[m])
J_slots = Set(initialize=set((m,i) for m in model.M for i in range(1,N_crafter_max[m]+1))) # (auxiliary) set of all job slots in the model
T_slots = Set(initialize=set((m,i) for m in model.M for i in range(N_crafter_max[m]+1))) # (auxiliary) set of all travelling slots in the model
S_slots = Set(initialize=set((m,i) for m in model.M for i in range(N_crafter_max[m]+2))) # (auxiliary) set of all moments where position of a crafter is observed

##### Preamble for iterative algorithm
# this must be set to 1 by a data file to apply the algorithm
model.ALG_USE = Param(within=Binary, default=0)

# this is the only data imported from files
model.ALG_decisions = Set(within=model.K*model.M*model.S, dimen=3, filter=lambda model: {(0,0,0)} - {(0,0,0)})

# check constraints
model.check = ConstraintList()
model.check.add((k,m,i) in model.ALG_decisions for k in model.K for m in model.M for i in range(1, model.U_exec[k,m]+1))
model.check.add((k,m,i) in model.ALG_decisions for m in model.M for k in model.K for i in model.ALG_indices[m])
model.check.add(pyomo.cardinality(model.ALG_decisions_task_list) == pyomo.cardinality(model.ALG_decisions))
model.check.add(pyomo.cardinality(model.ALG_decisions_job_slot_list) == pyomo.cardinality(model.ALG_decisions))
model.check.add((k,m,i) in model.ALG_decisions for i in model.ALG_indices[m] for m in model.M for k in model.K)

model.ALG_indices = pyomo.Set(model.M, initialize=lambda model, m: set((k,m,i) for k in model.K for i in range(1, model.U_exec[k,m]+1) if (k,m) in model.ALG_decisions))
model.ALG_N = pyomo.Param(model.M, initialize=lambda model, m: len(model.ALG_indices[m]) + 1)
model.ALG_ITERATION_COUNT = pyomo.Param(initialize=lambda model: len(model.ALG_decisions) + 1)
##### Preamble - END 


# VARIABLES
model.al = Var(model.K, model.J_slots, within=Binary)
model.al_task = Var(model.K, model.M, bounds=(0,1))
model.b_present = Var(model.S_slots, model.S, bounds=(0,1))
model.b_sch = Var(model.T_slots, model.S, model.S, bounds=(0,1))
model.b_travel_move = Var(model.T_slots, within=Binary)
model.p_close = Var(model.K, bounds=(0,1))
model.p_open = Var(model.K, bounds=(0,1))
model.p_prot = Var(model.P_prot, within=Binary)
model.p_mutex = Var(model.P_mutex, within=Binary)

model.q_req = Var(model.R, model.J_slots, within=NonNegativeReals)
model.q_carry = Var(model.R, model.M, within=NonNegativeReals)
model.d = Var(model.T_slots, within=NonNegativeReals)
model.t_travel_start = Var(model.T_slots, bounds=(model.T_day_start, model.T_day_end))
model.t_travel_end = Var(model.T_slots, bounds=(model.T_day_start, model.T_day_end))
model.u_idle = Var(model.T_slots, within=NonNegativeReals)

model.t_task_presence_start = Var(model.K, bounds=(model.T_day_start, model.T_day_end))
model.t_task_presence_end = Var(model.K, bounds=(model.T_day_start, model.T_day_end))
model.t_task_start = Var(model.K, bounds=(model.T_day_start, model.T_day_end))
model.t_task_end = Var(model.K, bounds=(model.T_day_start, model.T_day_end))
model.t_wait_before = Var(model.K, within=NonNegativeReals)
model.t_wait_after = Var(model.K, within=NonNegativeReals)
model.t_slack = Var(model.K, within=NonNegativeReals)

model.time_total = Var()

# defining parameter PRESET_al
model.PRESET_al = Param(model.K, model.J_slots, within=Binary, default=-1)

# defining set ALG_tasks_done and ALG_tasks_remaining
model.ALG_tasks_done = Set(within=model.K, initialize=lambda m: {k for (k, m, i) in m.ALG_decisions})
model.ALG_tasks_remaining = Set(within=model.K, initialize=lambda m: m.K - m.ALG_tasks_done)

# defining variables
model.alg_select_crafter = Var(model.M, within=Binary, bounds=(0,1), initialize=lambda m, i: 1 if m.ALG_USE == 1 else 0)
model.alg_select_task = Var(model.ALG_tasks_remaining, within=Binary, bounds=(0,1), initialize=lambda m, k: 1 if m.ALG_USE == 1 else 0)
model.alg_select_task_slot = Var(model.J_slots, within=Binary, bounds=(0,1), initialize=lambda m, i: 1 if m.ALG_USE == 1 else 0)
model.alg_inselect = Var(model.T_slots, within=Binary, bounds=(0,1), initialize=lambda m, i: 1 if m.ALG_USE == 1 else 0)
model.alg_task = Var(model.ALG_tasks_remaining, model.J_slots, within=Binary, bounds=(0,1), initialize=lambda m, k, i: 1 if m.ALG_USE == 1 else 0)


# Define Constraints
def CALG_1_01_rule(model, m):
    if model.ALG_USE == 1:
        return model.alg_inselect[m,0] == 0
    else:
        return Constraint.Skip
model.CALG_1_01 = Constraint(M, rule=CALG_1_01_rule)

def CALG_1_02_rule(model, m, i):
    if model.ALG_USE == 1:
        if i == 0:
            return Constraint.Skip
        else:
            return model.alg_inselect[m,i] >= model.alg_inselect[m,i-1]
    else:
        return Constraint.Skip
model.CALG_1_02 = Constraint(J_slots, rule=CALG_1_02_rule)

def CALG_1_03_rule(model, m, i):
    if model.ALG_USE == 1:
        return model.alg_inselect[m,i] >= model.alg_select_task_slot[m,i]
    else:
        return Constraint.Skip
model.CALG_1_03 = Constraint(J_slots, rule=CALG_1_03_rule)

def CALG_1_04_rule(model, m, i):
    if model.ALG_USE == 1:
        if i == 0:
            return Constraint.Skip
        else:
            return model.alg_inselect[m,i] <= model.alg_inselect[m,i-1] + model.alg_select_task_slot[m,i]
    else:
        return Constraint.Skip
model.CALG_1_04 = Constraint(J_slots, rule=CALG_1_04_rule)

def CALG_2_01_rule(model, m, i):
    if model.ALG_USE == 1:
        return model.alg_select_crafter[m] >= model.alg_inselect[m,i]
    else:
        return Constraint.Skip
model.CALG_2_01 = Constraint(J_slots, rule=CALG_2_01_rule)

def CALG_3_01_rule(model, k, m, i):
    if model.ALG_USE == 1:
        return model.alg_task[k,m,i] <= model.alg_select_task[k]
    else:
        return Constraint.Skip
model.CALG_3_01 = Constraint(model.ALG_tasks_remaining, J_slots, rule=CALG_3_01_rule)

def CALG_3_02_rule(model, k, m, i):
    if model.ALG_USE == 1:
        return model.alg_task[k,m,i] <= model.alg_select_task_slot[m,i]
    else:
        return Constraint.Skip
model.CALG_3_02 = Constraint(model.ALG_tasks_remaining, J_slots, rule=CALG_3_02_rule)

def CALG_3_03_rule(model, k, m, i):
    if model.ALG_USE == 1:
        return model.alg_task
    

# Constraints
def C_PRESETS_rule(model, k, m, i):
    if model.PRESET_al[k, m, i] != -1:
        return model.al[k, m, i] == model.PRESET_al[k, m, i]
    else:
        return Constraint.Skip
model.C_PRESETS = Constraint(model.K, model.J_slots, rule=C_PRESETS_rule)

def C01_rule(model, k, m):
    return model.al_task[k, m] == sum(model.al[k, m, i] for (m_, i) in model.J_slots if m_ == m)
model.C01 = Constraint(model.K, model.M, rule=C01_rule)

def C02_rule(model, k):
    if model.ALG_USE == 0:
        return sum(model.al_task[k, m] for m in model.M) == 1
    else:
        return Constraint.Skip
model.C02 = Constraint(model.K, rule=C02_rule)

def C03_rule(model, m, i):
    if i > 1:
        return sum(model.al[k, m, i-1] for k in model.K) >= sum(model.al[k, m, i] for k in model.K)
    else:
        return Constraint.Skip
model.C03 = Constraint(model.J_slots, rule=C03_rule)

def C04_rule(model, m, i, s):
    if s == model.S_start[m] and i == 0:
        return model.b_present[m, i, s] == 1
    else:
        return Constraint.Skip
model.C04 = Constraint(model.S_slots, model.S_sourcelocation, rule=C04_rule)
