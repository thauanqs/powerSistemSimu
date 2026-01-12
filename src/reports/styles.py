V_MIN = 0.0
V_MAX = 1.05

def voltage_color(v):
    if v < V_MIN:
        #return "red"
        return "green"
    elif v > V_MAX:
        #return "orange"
        return "green"
    else:
        return "green"
