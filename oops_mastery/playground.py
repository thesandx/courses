class Counter:
    count = 0                 # class variable (shared)
    def __init__(self):
        Counter.count += 1   
        self.count+=1
        print(self.count) # modify via CLASS name to affect all

a, b = Counter(), Counter()
print(Counter.count)          # 2

# Gotcha: assigning self.x creates an INSTANCE var that SHADOWS class var