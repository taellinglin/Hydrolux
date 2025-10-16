class FractalGrowthRules:
    def __init__(self, turtle):
        self.turtle = turtle
        self.step_count = 0
        
    def rule_sierpinski_3d(self, depth, size):
        """3D Sierpinski tetrahedron pattern"""
        if depth == 0:
            for _ in range(size):
                self.turtle.move_forward()
            return
            
        self.rule_sierpinski_3d(depth-1, size//2)
        
        self.turtle.push_state()
        self.turtle.turn_up()
        self.rule_sierpinski_3d(depth-1, size//2)
        self.turtle.pop_state()
        
        self.turtle.push_state()
        self.turtle.turn_left()
        self.turtle.turn_up()
        self.rule_sierpinski_3d(depth-1, size//2)
        self.turtle.pop_state()
        
        self.turtle.push_state()
        self.turtle.turn_right()
        self.turtle.turn_up()
        self.rule_sierpinski_3d(depth-1, size//2)
        self.turtle.pop_state()
    
    def rule_menger_sponge(self, depth, size):
        """Menger sponge fractal"""
        if depth == 0:
            # Fill the cube
            for x in range(size):
                for y in range(size):
                    for z in range(size):
                        if (x % 3 == 1 and y % 3 == 1) or \
                           (x % 3 == 1 and z % 3 == 1) or \
                           (y % 3 == 1 and z % 3 == 1):
                            continue
                        pos = [
                            (self.turtle.position[0] + x) % self.turtle.grid_size,
                            (self.turtle.position[1] + y) % self.turtle.grid_size, 
                            (self.turtle.position[2] + z) % self.turtle.grid_size
                        ]
                        self.turtle.grid[tuple(pos)] = self.turtle.color
            return
            
        smaller = size // 3
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    # Skip the center cubes
                    if (i == 1 and j == 1) or (i == 1 and k == 1) or (j == 1 and k == 1):
                        continue
                        
                    # Move to sub-cube position
                    self.turtle.push_state()
                    for _ in range(i * smaller):
                        self.turtle.move_forward()
                    self.turtle.turn_left()
                    for _ in range(j * smaller):
                        self.turtle.move_forward()  
                    self.turtle.turn_up()
                    for _ in range(k * smaller):
                        self.turtle.move_forward()
                    
                    self.rule_menger_sponge(depth-1, smaller)
                    self.turtle.pop_state()
    
    def rule_psychedelic_spiral(self, iterations, step_size=2):
        """Creates colorful spiral patterns"""
        for i in range(iterations):
            self.turtle.next_color()
            for _ in range(step_size):
                self.turtle.move_forward()
            
            # Complex turning pattern
            if i % 7 == 0:
                self.turtle.turn_up()
            elif i % 5 == 0:
                self.turtle.turn_left()
            elif i % 3 == 0:
                self.turtle.turn_right()
            
            # Occasionally branch
            if i % 13 == 0:
                self.turtle.push_state()
                self.turtle.turn_right()
                self.turtle.turn_up()
                self.rule_psychedelic_spiral(iterations//2, step_size//2)
                self.turtle.pop_state()
    
    def rule_crystal_growth(self, depth, angle_variation=30):
        """Crystal-like branching growth"""
        if depth == 0:
            return
            
        branch_length = depth * 2
        
        # Main stem
        self.turtle.change_color(5)  # Blue
        for _ in range(branch_length):
            self.turtle.move_forward()
        
        # Create branches
        branches = 3 + (depth % 3)
        for i in range(branches):
            self.turtle.push_state()
            
            # Color variation
            self.turtle.change_color((5 + i) % 7 + 1)
            
            # Turn at varied angles
            for _ in range(i):
                self.turtle.turn_left()
            self.turtle.turn_up()
            
            # Recursive branch
            self.rule_crystal_growth(depth-1, angle_variation)
            self.turtle.pop_state()
            
            # Turn the other way for next branch
            for _ in range(i):
                self.turtle.turn_right()