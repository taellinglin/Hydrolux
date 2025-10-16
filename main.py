from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import *
import numpy as np
import random
import string
import os
import math
import sys

# Try to import PyCUDA, fall back to CPU if not available
try:
    import pycuda.autoinit
    import pycuda.driver as cuda
    from pycuda.compiler import SourceModule
    import pycuda.gpuarray as gpuarray
    PYCUDA_AVAILABLE = True
    print("PyCUDA available - using GPU acceleration!")
except ImportError:
    PYCUDA_AVAILABLE = False
    print("PyCUDA not available - falling back to CPU computation")

class SymmetricGameOfLife3D(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.update_interval = 16
        self.last_update_time = 0
        self.running = True
        
        # Camera movement
        self.camera_pos = Vec3(0, 0, 0)
        self.camera_hpr = Vec3(0, 0, 0)
        self.movement_speed = 0.0001
        self.rotation_speed = 00.0
        
        # FOV oscillation
        self.base_fov = 35.0
        self.fov_amplitude = 00.0
        self.fov_frequency = 0.00
        self.fov_time = 0.0
        
        # Rotation around origin
        self.auto_rotate = True
        self.rotation_speeds = Vec3(1.0, 1.0, 0.0)
        self.rotation_time = 0.0
        
        # Flame flicker effects
        self.flicker_time = 0.0
        self.base_brightness = 1.0
        self.flicker_intensity = 0.8
        
        # Grid setup
        self.grid_size = 32
        self.voxel_size = 0.25
        self.generation = 0
        
        # Game state
        self.current_grid = np.zeros((self.grid_size, self.grid_size, self.grid_size), dtype=np.int32)
        self.next_grid = np.zeros_like(self.current_grid)
        
        # Store cell data - simplified color type as boolean flag
        self.cell_data = np.empty((self.grid_size, self.grid_size, self.grid_size), dtype=object)
        for x in range(self.grid_size):
            for y in range(self.grid_size):
                for z in range(self.grid_size):
                    self.cell_data[x, y, z] = {
                        'char': 'a', 
                        'is_red': True,  # Simple boolean flag for color type
                        'alive': False,
                        'brightness': 1.0,
                        'base_hue_shift': random.uniform(-0.001, 0.001),
                        'hue_oscillation_speed': random.uniform(0.5, 3.0),
                        'hue_oscillation_phase': random.uniform(0, 2 * math.pi),
                        'brightness_phase': random.uniform(0, 2 * math.pi),
                        'brightness_speed': random.uniform(5.0, 20.0),
                        'saturation': random.uniform(0.7, 1.0),
                        'pulse_phase': random.uniform(0, 2 * math.pi),
                        'pulse_speed': random.uniform(2.0, 8.0),
                        'flicker_intensity': random.uniform(0.5, 1.5),
                        'hue_variation': random.uniform(-0.001, 0.001),
                        'last_flicker_update': 0.0,
                        'flicker_interval': random.uniform(0.05, 0.2)
                    }
        
        # Color palettes - we'll use these to generate colors based on the flag
        self.red_base_colors = [
            (1.0, 0.9, 0.3),
            (1.0, 0.6, 0.2),
            (1.0, 0.3, 0.1),
            (0.9, 0.2, 0.4),
            (0.8, 0.1, 0.3)
        ]
        
        self.blue_base_colors = [
            (0.3, 0.9, 1.0),
            (0.2, 0.7, 1.0),
            (0.3, 0.5, 1.0),
            (0.5, 0.3, 0.9),
            (0.4, 0.2, 0.8)
        ]
        
        # Mesh nodes storage
        self.mesh_nodes = {}
        self.char_meshes = {}
        self.load_bam_meshes()
        
        # Set black background
        self.setBackgroundColor(0, 0, 0, 1)
        
        # Setup
        self.setup_camera_controls()
        self.setup_emissive_rendering()
        
        if PYCUDA_AVAILABLE:
            self.setup_cuda_simple()
        
        # Initialize with random symmetric pattern
        self.initialize_random_pattern()
        self.setup_controls()
        
        # Start simulation
        self.taskMgr.add(self.update_simulation, "update_simulation")
        self.taskMgr.add(self.update_camera_movement, "update_camera_movement")
        self.taskMgr.add(self.update_flame_flicker, "update_flame_flicker")
    
    def load_bam_meshes(self):
        """Load character meshes from .bam files in ./bam directory"""
        bam_dir = "./bam"
        
        for char in string.ascii_lowercase:
            bam_path = os.path.join(bam_dir, f"{char}.bam")
            if os.path.exists(bam_path):
                try:
                    # Load the BAM file
                    model = self.loader.loadModel(bam_path)
                    if model:
                        model.setLightOff()
                        model.setTwoSided(True)
                        
                        self.char_meshes[char] = model
                        print(f"Loaded {char}.bam")
                    else:
                        print(f"Failed to load {bam_path}")
                        self.create_fallback_mesh(char)
                except Exception as e:
                    print(f"Error loading {bam_path}: {e}")
                    self.create_fallback_mesh(char)
            else:
                print(f"BAM file not found: {bam_path}")
                self.create_fallback_mesh(char)
        
        # Ensure at least one fallback mesh exists
        if not self.char_meshes:
            self.create_fallback_mesh('a')
    
    def create_fallback_mesh(self, char):
        """Create a simple geometric mesh as fallback for missing BAM files"""
        format = GeomVertexFormat.getV3n3c4()
        vdata = GeomVertexData('fallback', format, Geom.UHDynamic)
        vertex = GeomVertexWriter(vdata, 'vertex')
        normal = GeomVertexWriter(vdata, 'normal')
        color = GeomVertexWriter(vdata, 'color')
        
        # Simple flat quad geometry
        vertices = [
            (-0.3, -0.3, 0), (0.3, -0.3, 0), (0.3, 0.3, 0), (-0.3, 0.3, 0)
        ]
        
        normals = [(0, 0, 1)] * 4
        
        for v, n in zip(vertices, normals):
            vertex.addData3f(v[0], v[1], v[2])
            normal.addData3f(n[0], n[1], n[2])
            color.addData4f(1, 1, 1, 1)
        
        tris = GeomTriangles(Geom.UHStatic)
        tris.addVertices(0, 1, 2)
        tris.addVertices(0, 2, 3)
        
        geom = Geom(vdata)
        geom.addPrimitive(tris)
        node = GeomNode(f'mesh_{char}')
        node.addGeom(geom)
        
        # Create the NodePath and apply emissive material
        mesh_node = NodePath(node)
        
        material = Material()
        material.setShininess(1.0)
        material.setEmission((1.0, 0.0, .0, 1.0))
        material.setLocal(True)
        
        mesh_node.setMaterial(material, 1)
        mesh_node.setLightOff()
        mesh_node.setTwoSided(True)
        
        self.char_meshes[char] = mesh_node
        print(f"Created fallback mesh for {char}")
    
    def setup_emissive_rendering(self):
        """Setup emissive rendering by removing all lights"""
        self.render.clearLight()
        self.render.setLightOff()
        
        # Add a very dim ambient light so we can see non-emissive parts if any
        ambient_light = AmbientLight('ambient')
        ambient_light.setColor((0.01, 0.01, 0.01, 1))
        ambient_node = self.render.attachNewNode(ambient_light)
        self.render.setLight(ambient_node)
    
    def get_base_color_for_cell(self, cell_info, brightness):
        """Get base color based on the is_red flag and brightness"""
        if cell_info['is_red']:
            base_colors = self.red_base_colors
        else:
            base_colors = self.blue_base_colors
            
        if brightness > 1.8:
            return base_colors[0]
        elif brightness > 1.4:
            return self.blend_colors(base_colors[1], base_colors[0], (brightness - 1.4) * 2.5)
        elif brightness > 1.0:
            return self.blend_colors(base_colors[2], base_colors[1], (brightness - 1.0) * 2.5)
        elif brightness > 0.6:
            return self.blend_colors(base_colors[3], base_colors[2], (brightness - 0.6) * 2.5)
        else:
            return self.blend_colors(base_colors[4], base_colors[3], brightness * 1.7)

    def create_color_variation(self, base_color, hue_range=0.000, brightness_range=0.00, opacity_range=0.5):
        """
        Create a color variation with hue, brightness, and opacity adjustments.
        
        Args:
            base_color: Tuple of (r, g, b) or (r, g, b, a) values (0.0-1.0)
            hue_range: Maximum hue shift (0.0-1.0)
            brightness_range: Maximum brightness variation (0.0-1.0)
            opacity_range: Maximum opacity variation (0.0-1.0)
        
        Returns:
            Tuple of (r, g, b, a) with variations
        """
        # Extract RGB components
        if len(base_color) == 4:
            r, g, b, original_a = base_color
        else:
            r, g, b = base_color
            original_a = 1.0
        
        # Convert RGB to HSV
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        h, s, v = 0.0, 0.0, max_val
        
        if max_val != 0:
            s = (max_val - min_val) / max_val
        
        if s != 0:
            if max_val == r:
                h = (g - b) / (max_val - min_val)
            elif max_val == g:
                h = 2.0 + (b - r) / (max_val - min_val)
            else:
                h = 4.0 + (r - g) / (max_val - min_val)
            h /= 6.0
            if h < 0:
                h += 1.0
        
        # Apply hue variation
        hue_shift = random.uniform(-hue_range, hue_range)
        h = (h + hue_shift) % 1.0
        
        # Apply brightness variation
        brightness_shift = random.uniform(-brightness_range, brightness_range)
        v = max(0.0, min(1.0, v + brightness_shift))
        
        # Convert back to RGB
        if s == 0:
            r, g, b = v, v, v
        else:
            h *= 6.0
            i = int(h)
            f = h - i
            p = v * (1 - s)
            q = v * (1 - s * f)
            t = v * (1 - s * (1 - f))
            
            if i == 0:
                r, g, b = v, t, p
            elif i == 1:
                r, g, b = q, v, p
            elif i == 2:
                r, g, b = p, v, t
            elif i == 3:
                r, g, b = p, q, v
            elif i == 4:
                r, g, b = t, p, v
            else:
                r, g, b = v, p, q
        
        # Apply opacity variation
        a = max(0.0, min(1.0, original_a + random.uniform(-opacity_range, opacity_range)))
        
        return (r, g, b, a)
        
    def create_mesh_node(self, char, is_red, position):
        """Create a mesh instance for a character"""
        if char not in self.char_meshes:
            char = 'a'
            
        node = self.char_meshes[char].copyTo(self.render)
        node.setPos(position)
        node.setScale(1)
        # Make it a billboard that always faces the camera
        node.setBillboardPointEye()
        # Set initial color based on the flag
        if is_red:
            base_color = self.red_base_colors[2]
        else:
            base_color = self.blue_base_colors[2]
            
        initial_color = Vec4(base_color[0], base_color[1], base_color[2], 1.0)
        
        # Create new material for this instance
        material = Material()
        
        # Set base color (diffuse/ambient)
        node.setColor(initial_color)
        material.setAmbient(initial_color)
        material.setDiffuse(initial_color)
        
        # Set emission color (what makes it glow)
        material.setEmission(initial_color)
        
        # Make it fully emissive (no lighting calculations)
        material.setShininess(1.0)
        material.setLocal(True)
        
        node.setMaterial(material, 1)
        node.setLightOff()
        node.setTwoSided(True)
        
        return node
        
    def rgb_to_hsv(self, r, g, b):
        """Convert RGB to HSV color space"""
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        h, s, v = 0.0, 0.0, max_val
        
        if max_val != 0:
            s = (max_val - min_val) / max_val
        
        if s != 0:
            if max_val == r:
                h = (g - b) / (max_val - min_val)
            elif max_val == g:
                h = 2.0 + (b - r) / (max_val - min_val)
            else:
                h = 4.0 + (r - g) / (max_val - min_val)
            h /= 6.0
            if h < 0:
                h += 1.0
        
        return h, s, v
    
    def hsv_to_rgb(self, h, s, v):
        """Convert HSV to RGB color space"""
        if s == 0:
            return v, v, v
        
        h *= 6.0
        i = int(h)
        f = h - i
        p = v * (1 - s)
        q = v * (1 - s * f)
        t = v * (1 - s * (1 - f))
        
        if i == 0:
            return v, t, p
        elif i == 1:
            return q, v, p
        elif i == 2:
            return p, v, t
        elif i == 3:
            return p, q, v
        elif i == 4:
            return t, p, v
        else:
            return v, p, q
    
    def apply_hue_shift(self, r, g, b, hue_shift):
        """Apply hue shift to RGB color"""
        h, s, v = self.rgb_to_hsv(r, g, b)
        h = (h + hue_shift) % 1.0
        return self.hsv_to_rgb(h, s, v)
    
    def blend_colors(self, color1, color2, factor):
        """Blend between two colors"""
        factor = max(0.0, min(1.0, factor))
        return (
            color1[0] * (1 - factor) + color2[0] * factor,
            color1[1] * (1 - factor) + color2[1] * factor,
            color1[2] * (1 - factor) + color2[2] * factor
        )
    
    def update_flame_flicker(self, task):
        """Update flame flicker effects for all alive cells - every frame"""
        dt = globalClock.getDt()
        self.flicker_time += dt
        
        for x in range(self.grid_size):
            for y in range(self.grid_size):
                for z in range(self.grid_size):
                    if self.current_grid[x, y, z]:
                        cell_info = self.cell_data[x, y, z]
                        
                        # Update flicker at random intervals for more natural effect
                        current_time = globalClock.getFrameTime()
                        if current_time - cell_info['last_flicker_update'] > cell_info['flicker_interval']:
                            # Randomize flicker intensity
                            cell_info['flicker_intensity'] = random.uniform(0.5, 1.5)
                            # Randomize hue variation
                            cell_info['hue_variation'] = random.uniform(-0.001, 0.001)
                            # Randomize next update interval
                            cell_info['flicker_interval'] = random.uniform(0.05, 0.2)
                            cell_info['last_flicker_update'] = current_time
                        
                        brightness_flicker1 = math.sin(self.flicker_time * cell_info['brightness_speed'] + cell_info['brightness_phase'])
                        brightness_flicker2 = math.sin(self.flicker_time * cell_info['brightness_speed'] * 1.7 + cell_info['brightness_phase'] * 2.3)
                        brightness_flicker3 = math.sin(self.flicker_time * cell_info['brightness_speed'] * 2.5 + cell_info['brightness_phase'] * 1.4)
                        
                        combined_brightness_flicker = (brightness_flicker1 + brightness_flicker2 * 0.7 + brightness_flicker3 * 0.3) / 2.0
                        
                        brightness_random = 0.3 + 0.7 * random.random()
                        cell_info['brightness'] = (self.base_brightness + 
                                                 combined_brightness_flicker * self.flicker_intensity * brightness_random * cell_info['flicker_intensity'])
                        
                        cell_info['brightness'] = max(0.2, min(2.5, cell_info['brightness']))
                        
                        if (x, y, z) in self.mesh_nodes:
                            self.update_cell_visualization(x, y, z)
        
        return Task.cont
    
    def update_cell_visualization(self, x, y, z):
        """Update the visual appearance of a single cell with flame effect - every frame"""
        cell_info = self.cell_data[x, y, z]
        brightness = cell_info['brightness']
        
        # Get base color based on the is_red flag
        base_color = self.get_base_color_for_cell(cell_info, brightness)
        
        # Apply hue oscillation based on color type
        if cell_info['is_red']:
            hue_oscillation = math.sin(self.flicker_time * cell_info['hue_oscillation_speed'] + cell_info['hue_oscillation_phase']) * 0.15
        else:
            hue_oscillation = math.sin(self.flicker_time * cell_info['hue_oscillation_speed'] + cell_info['hue_oscillation_phase']) * 0.2
        
        # Apply random hue variation for flicker effect
        total_hue_shift = cell_info['base_hue_shift'] + hue_oscillation + cell_info['hue_variation']
        
        r, g, b = self.apply_hue_shift(base_color[0], base_color[1], base_color[2], total_hue_shift)
        
        h, s, v = self.rgb_to_hsv(r, g, b)
        s *= cell_info['saturation']
        r, g, b = self.hsv_to_rgb(h, s, v)
        
        r = min(1.0, r * brightness)
        g = min(1.0, g * brightness)
        b = min(1.0, b * brightness)
        
        pulse = math.sin(self.flicker_time * cell_info['pulse_speed'] + cell_info['pulse_phase']) * 0.1 + 1.0
        r = min(1.0, r * pulse)
        g = min(1.0, g * pulse)
        b = min(1.0, b * pulse)
        
        final_color = Vec4(r, g, b, 1.0)
        
        mesh_node = self.mesh_nodes[(x, y, z)]
        
        # Update material with new emissive color
        material = Material()
        material.setShininess(5.0)
        mesh_node.setColor(final_color)
        material.setEmission(final_color)
        material.setLocal(True)
        
        mesh_node.setMaterial(material, 1)
        
        scale_variation = 0.6 + 0.8 * (brightness - 0.2) / 2.3
        mesh_node.setScale(0.1 * scale_variation * pulse)
    
    def setup_camera_controls(self):
        self.disableMouse()
        self.update_camera_transform()
    
    def setup_cuda_simple(self):
        try:
            cuda_kernel = """
            __global__ void game_of_life_3d_simple(int *current_grid, int *next_grid, int grid_size) {
                int x = blockIdx.x * blockDim.x + threadIdx.x;
                int y = blockIdx.y * blockDim.y + threadIdx.y;
                int z = blockIdx.z * blockDim.z + threadIdx.z;
                
                if (x >= grid_size || y >= grid_size || z >= grid_size) return;
                
                int idx = x * grid_size * grid_size + y * grid_size + z;
                int neighbors = 0;
                
                for (int dx = -1; dx <= 1; dx++) {
                    for (int dy = -1; dy <= 1; dy++) {
                        for (int dz = -1; dz <= 1; dz++) {
                            if (dx == 0 && dy == 0 && dz == 0) continue;
                            int nx = (x + dx + grid_size) % grid_size;
                            int ny = (y + dy + grid_size) % grid_size;
                            int nz = (z + dz + grid_size) % grid_size;
                            int nidx = nx * grid_size * grid_size + ny * grid_size + nz;
                            if (current_grid[nidx] == 1) neighbors++;
                        }
                    }
                }
                
                int current_state = current_grid[idx];
                int new_state = current_state;
                
                if (current_state == 1) {
                    if (neighbors < 2 || neighbors > 3) new_state = 0;
                } else {
                    if (neighbors == 3) new_state = 1;
                }
                
                next_grid[idx] = new_state;
            }
            """
            
            self.mod = SourceModule(cuda_kernel, options=['-arch=sm_52'])
            self.game_of_life_kernel = self.mod.get_function("game_of_life_3d_simple")
            self.current_grid_gpu = gpuarray.to_gpu(self.current_grid.astype(np.int32))
            self.next_grid_gpu = gpuarray.to_gpu(self.next_grid.astype(np.int32))
            print(f"CUDA initialized for {self.grid_size}^3 grid")
            
        except Exception as e:
            print(f"CUDA setup failed: {e}")
            global PYCUDA_AVAILABLE
            PYCUDA_AVAILABLE = False
    
    def update_camera_transform(self):
        self.camera.setPos(self.camera_pos)
        self.camera.setHpr(self.camera_hpr)
    
    def update_camera_movement(self, task):
        dt = globalClock.getDt()
    
        self.fov_time += dt
        fov_offset = self.fov_amplitude * math.sin(2 * math.pi * self.fov_frequency * self.fov_time)
        self.camLens.setFov(self.base_fov + fov_offset)
        
        if self.auto_rotate:
            self.rotation_time += dt
            
            # Celtic knot path parameters
            t = self.rotation_time * 0.005  # Speed control
            scale = 5.0  # Size of the knot
            
            # 3D Celtic knot equations (more complex 3D path)
            x = scale * (math.sin(t) + 2 * math.sin(2 * t))
            y = scale * (math.cos(t) - 2 * math.cos(2 * t))
            z = scale * (-math.sin(3 * t))
            
            # Position camera on the knot path
            self.camera_pos = Vec3(x, y, z)
            
            # Calculate forward direction (tangent to the path)
            # Sample nearby points to compute derivative
            t_future = t + 0.00001
            x_future = scale * (math.sin(t_future) + 2 * math.sin(2 * t_future))
            y_future = scale * (math.cos(t_future) - 2 * math.cos(2 * t_future))
            z_future = scale * (-math.sin(3 * t_future))
            
            # Forward vector is tangent to the path
            forward = Vec3(x_future - x, y_future - y, z_future - z)
            forward.normalize()
            
            # Calculate up vector (try to maintain world up with some variation)
            world_up = Vec3(0, 1, 1)
            
            # Right vector is cross product of forward and world up
            right = forward.cross(world_up)
            right.normalize()
            
            # Recalculate proper up vector
            up = right.cross(forward)
            up.normalize()
            
            # Set camera orientation using lookAt
            look_at_point = Vec3(x, y, z) + forward
            self.camera.lookAt(look_at_point)
            
            # Apply some roll oscillation for more dynamic movement
            roll = math.sin(t * 0.07) * 0.1  # Gentle rolling motion
            self.camera.setR(roll)
        
        # Keep manual controls for when auto-rotate is off
        heading_rad = np.radians(self.camera_hpr.x)
        pitch_rad = np.radians(self.camera_hpr.y)
        
        manual_forward = Vec3(
            -np.sin(heading_rad) * np.cos(pitch_rad),
            np.cos(heading_rad) * np.cos(pitch_rad),
            math.sin(pitch_rad)
        )
        
        manual_right = Vec3(math.cos(heading_rad), math.sin(heading_rad), 0)
        manual_up = Vec3(0, 1, 1)
        
        move_vector = Vec3(0, 0, 0)
        
        if self.keyMap['w']: move_vector += manual_forward * self.movement_speed * dt
        if self.keyMap['s']: move_vector -= manual_forward * self.movement_speed * dt
        if self.keyMap['a']: move_vector -= manual_right * self.movement_speed * dt
        if self.keyMap['d']: move_vector += manual_right * self.movement_speed * dt
        if self.keyMap['q']: move_vector += manual_up * self.movement_speed * dt
        if self.keyMap['e']: move_vector -= manual_up * self.movement_speed * dt
        
        self.camera_pos += move_vector
        
        if self.keyMap['arrow_up']: self.camera_hpr.y += self.rotation_speed * dt
        if self.keyMap['arrow_down']: self.camera_hpr.y -= self.rotation_speed * dt
        if self.keyMap['arrow_left']: self.camera_hpr.x += self.rotation_speed * dt
        if self.keyMap['arrow_right']: self.camera_hpr.x -= self.rotation_speed * dt
        
        if self.keyMap['shift']:
            if self.keyMap['a']: self.camera_hpr.z += self.rotation_speed * dt
            if self.keyMap['d']: self.camera_hpr.z -= self.rotation_speed * dt
        
        self.camera_hpr.y = max(-90, min(90, self.camera_hpr.y))
        
        # Only update camera transform if not auto-rotating
        if not self.auto_rotate:
            self.update_camera_transform()
        
        return Task.cont
        
    def random_char(self):
        return random.choice(string.ascii_lowercase)

    def random_color_type(self):
        return random.random() > 0.5  # True for red, False for blue

    def initialize_random_pattern(self):
        print("Initializing random symmetric pattern...")
        
        self.current_grid.fill(0)
        self.generation = 0
        
        half_size = self.grid_size // 2
        
        for x in range(half_size):
            for y in range(half_size):
                for z in range(half_size):
                    if random.random() > 0.7:
                        self.current_grid[x, y, z] = 1
                        self.cell_data[x, y, z] = {
                            'char': self.random_char(),
                            'is_red': self.random_color_type(),  # Use boolean flag
                            'alive': True,
                            'brightness': 1.0,
                            'base_hue_shift': random.uniform(-0.001, 0.001),
                            'hue_oscillation_speed': random.uniform(0.5, 3.0),
                            'hue_oscillation_phase': random.uniform(0, 2 * math.pi),
                            'brightness_phase': random.uniform(0, 2 * math.pi),
                            'brightness_speed': random.uniform(5.0, 20.0),
                            'saturation': random.uniform(0.7, 1.0),
                            'pulse_phase': random.uniform(0, 2 * math.pi),
                            'pulse_speed': random.uniform(2.0, 8.0),
                            'flicker_intensity': random.uniform(0.5, 1.5),
                            'hue_variation': random.uniform(-0.001, 0.001),
                            'last_flicker_update': 0.0,
                            'flicker_interval': random.uniform(0.05, 0.2)
                        }
        
        self.apply_3d_symmetry()
        
        if PYCUDA_AVAILABLE:
            self.current_grid_gpu.set(self.current_grid.astype(np.int32))
        
        live_count = np.sum(self.current_grid)
        print(f"Initialized with {live_count} live cells")
        self.update_visualization()

    def apply_3d_symmetry(self):
        half_size = self.grid_size // 2
        
        for x in range(half_size):
            for y in range(half_size):
                for z in range(half_size):
                    source_data = self.cell_data[x, y, z]
                    source_alive = self.current_grid[x, y, z]
                    
                    symmetric_positions = [
                        (x, y, z), (self.grid_size - x - 1, y, z),
                        (x, self.grid_size - y - 1, z), (x, y, self.grid_size - z - 1),
                        (self.grid_size - x - 1, self.grid_size - y - 1, z),
                        (self.grid_size - x - 1, y, self.grid_size - z - 1),
                        (x, self.grid_size - y - 1, self.grid_size - z - 1),
                        (self.grid_size - x - 1, self.grid_size - y - 1, self.grid_size - z - 1)
                    ]
                    
                    for pos_x, pos_y, pos_z in symmetric_positions:
                        self.current_grid[pos_x, pos_y, pos_z] = source_alive
                        self.cell_data[pos_x, pos_y, pos_z] = {
                            'char': source_data['char'],
                            'is_red': source_data['is_red'],  # Copy the boolean flag
                            'alive': bool(source_alive),
                            'brightness': source_data['brightness'],
                            'base_hue_shift': random.uniform(-0.01, 0.01),
                            'hue_oscillation_speed': random.uniform(0.5, 3.0),
                            'hue_oscillation_phase': random.uniform(0, 2 * math.pi),
                            'brightness_phase': random.uniform(0, 2 * math.pi),
                            'brightness_speed': random.uniform(5.0, 20.0),
                            'saturation': random.uniform(0.7, 1.0),
                            'pulse_phase': random.uniform(0, 2 * math.pi),
                            'pulse_speed': random.uniform(2.0, 8.0),
                            'flicker_intensity': random.uniform(0.5, 1.5),
                            'hue_variation': random.uniform(-0.001, 0.001),
                            'last_flicker_update': 0.0,
                            'flicker_interval': random.uniform(0.05, 0.2)
                        }

    def setup_controls(self):
        self.keyMap = {
            'w': False, 'a': False, 's': False, 'd': False,
            'q': False, 'e': False, 'shift': False,
            'arrow_up': False, 'arrow_down': False, 
            'arrow_left': False, 'arrow_right': False
        }
        
        self.accept('w', self.update_key, ['w', True])
        self.accept('w-up', self.update_key, ['w', False])
        self.accept('a', self.update_key, ['a', True])
        self.accept('a-up', self.update_key, ['a', False])
        self.accept('s', self.update_key, ['s', True])
        self.accept('s-up', self.update_key, ['s', False])
        self.accept('d', self.update_key, ['d', True])
        self.accept('d-up', self.update_key, ['d', False])
        self.accept('q', self.update_key, ['q', True])
        self.accept('q-up', self.update_key, ['q', False])
        self.accept('e', self.update_key, ['e', True])
        self.accept('e-up', self.update_key, ['e', False])
        self.accept('arrow_up', self.update_key, ['arrow_up', True])
        self.accept('arrow_up-up', self.update_key, ['arrow_up', False])
        self.accept('arrow_down', self.update_key, ['arrow_down', True])
        self.accept('arrow_down-up', self.update_key, ['arrow_down', False])
        self.accept('arrow_left', self.update_key, ['arrow_left', True])
        self.accept('arrow_left-up', self.update_key, ['arrow_left', False])
        self.accept('arrow_right', self.update_key, ['arrow_right', True])
        self.accept('arrow_right-up', self.update_key, ['arrow_right', False])
        self.accept('shift', self.update_key, ['shift', True])
        self.accept('shift-up', self.update_key, ['shift', False])
        
        self.accept('escape', self.quit)
        self.accept('space', self.toggle_simulation)
        self.accept('r', self.initialize_random_pattern)
        self.accept('c', self.clear_grid)
        self.accept('n', self.next_generation)
        self.accept('t', self.toggle_auto_rotate)

    def update_key(self, key, value):
        self.keyMap[key] = value

    def toggle_auto_rotate(self):
        self.auto_rotate = not self.auto_rotate
        state = "ON" if self.auto_rotate else "OFF"
        print(f"Auto-rotation {state}")

    def count_alive_neighbors_cpu(self, x, y, z):
        count = 0
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    if dx == 0 and dy == 0 and dz == 0:
                        continue
                    nx = (x + dx) % self.grid_size
                    ny = (y + dy) % self.grid_size
                    nz = (z + dz) % self.grid_size
                    if self.current_grid[nx, ny, nz]:
                        count += 1
        return count

    def update_visualization(self):
        for node in self.mesh_nodes.values():
            node.removeNode()
        self.mesh_nodes.clear()
        
        for x in range(self.grid_size):
            for y in range(self.grid_size):
                for z in range(self.grid_size):
                    if self.current_grid[x, y, z]:
                        cell_info = self.cell_data[x, y, z]
                        world_x = (x - self.grid_size/2) * self.voxel_size
                        world_y = (y - self.grid_size/2) * self.voxel_size  
                        world_z = (z - self.grid_size/2) * self.voxel_size
                        
                        mesh_node = self.create_mesh_node(
                            cell_info['char'], 
                            cell_info['is_red'],  # Pass the boolean flag
                            Point3(world_x, world_y, world_z)
                        )
                        self.mesh_nodes[(x, y, z)] = mesh_node

    def next_generation_gpu(self):
        threads_per_block = (4, 4, 4)
        blocks_per_grid = (
            (self.grid_size + threads_per_block[0] - 1) // threads_per_block[0],
            (self.grid_size + threads_per_block[1] - 1) // threads_per_block[1],
            (self.grid_size + threads_per_block[2] - 1) // threads_per_block[2]
        )
        
        self.game_of_life_kernel(
            self.current_grid_gpu, 
            self.next_grid_gpu, 
            np.int32(self.grid_size),
            block=threads_per_block,
            grid=blocks_per_grid
        )
        
        self.current_grid_gpu, self.next_grid_gpu = self.next_grid_gpu, self.current_grid_gpu
        self.current_grid = self.current_grid_gpu.get()

    def next_generation_cpu(self):
        temp_grid = np.zeros_like(self.current_grid)
        
        for x in range(self.grid_size):
            for y in range(self.grid_size):
                for z in range(self.grid_size):
                    neighbors = self.count_alive_neighbors_cpu(x, y, z)
                    current_state = self.current_grid[x, y, z]
                    new_state = current_state
                    
                    if current_state:
                        if neighbors < 2 or neighbors > 3:
                            new_state = 0
                    else:
                        if neighbors == 3:
                            new_state = 1
                            self.cell_data[x, y, z] = {
                                'char': self.random_char(),
                                'is_red': self.random_color_type(),  # Use boolean flag
                                'alive': True,
                                'brightness': 1.0,
                                'base_hue_shift': random.uniform(-0.01, 0.01),
                                'hue_oscillation_speed': random.uniform(0.5, 3.0),
                                'hue_oscillation_phase': random.uniform(0, 2 * math.pi),
                                'brightness_phase': random.uniform(0, 2 * math.pi),
                                'brightness_speed': random.uniform(5.0, 20.0),
                                'saturation': random.uniform(0.7, 1.0),
                                'pulse_phase': random.uniform(0, 2 * math.pi),
                                'pulse_speed': random.uniform(2.0, 8.0),
                                'flicker_intensity': random.uniform(0.5, 1.5),
                                'hue_variation': random.uniform(-0.01, 0.01),
                                'last_flicker_update': 0.0,
                                'flicker_interval': random.uniform(0.05, 0.2)
                            }
                    
                    if random.random() < 0.002:
                        new_state = 1 - new_state
                        if new_state:
                            self.cell_data[x, y, z] = {
                                'char': self.random_char(),
                                'is_red': self.random_color_type(),  # Use boolean flag
                                'alive': True,
                                'brightness': 1.0,
                                'base_hue_shift': random.uniform(-0.01, 0.01),
                                'hue_oscillation_speed': random.uniform(0.5, 3.0),
                                'hue_oscillation_phase': random.uniform(0, 2 * math.pi),
                                'brightness_phase': random.uniform(0, 2 * math.pi),
                                'brightness_speed': random.uniform(5.0, 20.0),
                                'saturation': random.uniform(0.7, 1.0),
                                'pulse_phase': random.uniform(0, 2 * math.pi),
                                'pulse_speed': random.uniform(2.0, 8.0),
                                'flicker_intensity': random.uniform(0.5, 1.5),
                                'hue_variation': random.uniform(-0.01, 0.01),
                                'last_flicker_update': 0.0,
                                'flicker_interval': random.uniform(0.05, 0.2)
                            }
                    
                    temp_grid[x, y, z] = new_state
        
        self.current_grid = temp_grid

    def update_simulation(self, task):
        current_time = globalClock.getFrameTime()
        if self.running and (current_time - self.last_update_time) >= self.update_interval:
            self.next_generation()
            self.last_update_time = current_time
        return Task.cont

    def next_generation(self):
        self.generation += 1
        
        if PYCUDA_AVAILABLE:
            self.next_generation_gpu()
        else:
            self.next_generation_cpu()
        
        half_size = self.grid_size // 2
        for x in range(half_size):
            for y in range(half_size):
                for z in range(half_size):
                    if self.current_grid[x, y, z]:
                        source_data = self.cell_data[x, y, z]
                        symmetric_positions = [
                            (self.grid_size - x - 1, y, z),
                            (x, self.grid_size - y - 1, z),
                            (x, y, self.grid_size - z - 1),
                            (self.grid_size - x - 1, self.grid_size - y - 1, z),
                            (self.grid_size - x - 1, y, self.grid_size - z - 1),
                            (x, self.grid_size - y - 1, self.grid_size - z - 1),
                            (self.grid_size - x - 1, self.grid_size - y - 1, self.grid_size - z - 1)
                        ]
                        for pos_x, pos_y, pos_z in symmetric_positions:
                            self.current_grid[pos_x, pos_y, pos_z] = 1
                            self.cell_data[pos_x, pos_y, pos_z] = {
                                'char': source_data['char'],
                                'is_red': source_data['is_red'],  # Copy the boolean flag
                                'alive': True,
                                'brightness': source_data['brightness'],
                                'base_hue_shift': random.uniform(-0.01, 0.01),
                                'hue_oscillation_speed': random.uniform(0.5, 3.0),
                                'hue_oscillation_phase': random.uniform(0, 2 * math.pi),
                                'brightness_phase': random.uniform(0, 2 * math.pi),
                                'brightness_speed': random.uniform(5.0, 20.0),
                                'saturation': random.uniform(0.7, 1.0),
                                'pulse_phase': random.uniform(0, 2 * math.pi),
                                'pulse_speed': random.uniform(2.0, 8.0),
                                'flicker_intensity': random.uniform(0.5, 1.5),
                                'hue_variation': random.uniform(-0.01, 0.01),
                                'last_flicker_update': 0.0,
                                'flicker_interval': random.uniform(0.05, 0.2)
                            }
        
        live_count = np.sum(self.current_grid)
        print(f"Generation {self.generation}: {live_count} live cells")
        self.update_visualization()

    def clear_grid(self):
        self.current_grid.fill(0)
        self.generation = 0
        
        for x in range(self.grid_size):
            for y in range(self.grid_size):
                for z in range(self.grid_size):
                    self.cell_data[x, y, z] = {
                        'char': 'a', 
                        'is_red': True,  # Use boolean flag
                        'alive': False,
                        'brightness': 1.0,
                        'base_hue_shift': random.uniform(-0.01, 0.01),
                        'hue_oscillation_speed': random.uniform(0.5, 3.0),
                        'hue_oscillation_phase': random.uniform(0, 2 * math.pi),
                        'brightness_phase': random.uniform(0, 2 * math.pi),
                        'brightness_speed': random.uniform(5.0, 20.0),
                        'saturation': random.uniform(0.7, 1.0),
                        'pulse_phase': random.uniform(0, 2 * math.pi),
                        'pulse_speed': random.uniform(2.0, 8.0),
                        'flicker_intensity': random.uniform(0.5, 1.5),
                        'hue_variation': random.uniform(-0.01, 0.01),
                        'last_flicker_update': 0.0,
                        'flicker_interval': random.uniform(0.05, 0.2)
                    }
        
        if PYCUDA_AVAILABLE:
            self.current_grid_gpu.set(self.current_grid.astype(np.int32))
        
        self.update_visualization()
        print("Grid cleared")

    def toggle_simulation(self):
        self.running = not self.running
        state = "RUNNING" if self.running else "PAUSED"
        print(f"Simulation {state}")

    def quit(self):
        self.destroy()
        sys.exit(0)

if __name__ == "__main__":
    app = SymmetricGameOfLife3D()
    app.run()