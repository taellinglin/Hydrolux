from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import *
import numpy as np
import random
import string
import os
import math
import sys
from motion_blur import MotionBlur
from panda3d.core import Fog
from panda3d.core import loadPrcFileData

# Configure before ShowBase initializes
loadPrcFileData("", """
    fullscreen true
    win-size 1920 1080
    show-frame-rate-meter false
""")

class FractalFireworks(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        
        # Enhanced fog
        self.fog = Fog("SceneFog")
        self.fog.setColor(0.0, 0.01, 0.02)
        self.fog.setLinearRange(50, 200)
        self.render.setFog(self.fog)
        
        # Load music
        self.bgm = self.loader.loadMusic("bgm.wav")
        if self.bgm:
            self.bgm.setLoop(True)
            self.bgm.setVolume(0.7)
            self.bgm.play()
        
        self.setBackgroundColor(0, 0.005, 0.01, 1)
        
        # SIMPLIFIED: Clear coordinate system
        self.ground_level = 0
        self.launch_area_center = Vec3(0, 50, 0)  # Center of where shells launch
        self.launch_spread = 20  # How wide the launch area is
        
        # Fireworks systems
        self.shells = []
        self.flares = []
        self.ignitions = []
        
        # Timing
        self.shell_spawn_timer = 0
        self.shell_spawn_interval = 2.0
        
        # Performance limits
        self.max_flares = 150
        
        # Visual parameters
        self.global_time = 0.0
        
        # Colors
        self.colors = {
            'red': Vec4(1.0, 0.1, 0.1, 1.0),
            'blue': Vec4(0.1, 0.3, 1.0, 1.0),
            'gold': Vec4(1.0, 0.8, 0.2, 1.0),
            'green': Vec4(0.1, 1.0, 0.3, 1.0),
            'purple': Vec4(0.8, 0.2, 1.0, 1.0),
        }
        
        # Setup
        self.setBackgroundColor(0, 0.005, 0.01, 1)
        self.setup_emissive_rendering()
        self.load_bam_meshes()
        self.setup_camera()
        self.setup_ground_plane()
        
        # Start tasks
        self.taskMgr.add(self.update_shells, "update_shells")
        self.taskMgr.add(self.update_flares, "update_flares")
        self.taskMgr.add(self.update_ignitions, "update_ignitions")
        self.taskMgr.add(self.update_cleanup, "update_cleanup")
        self.taskMgr.add(self.update_global_time, "update_time")
        
        # Controls
        self.setup_controls()
        
        print("Fireworks system initialized! Press SPACE to launch shells, 1-5 for colors")

    def setup_ground_plane(self):
        """Create a visible ground plane"""
        # Create a simple visible ground
        ground = self.loader.loadModel("plane.bam")
        if ground:
            ground.setScale(100, 100, 1)
            ground.setPos(0, 50, -2)  # Position below launch area
            ground.setColor(0.1, 0.1, 0.15, 1)
            ground.reparentTo(self.render)
        else:
            # Fallback: create a simple quad
            format = GeomVertexFormat.getV3n3c4()
            vdata = GeomVertexData('ground', format, Geom.UHStatic)
            vertex = GeomVertexWriter(vdata, 'vertex')
            color = GeomVertexWriter(vdata, 'color')
            
            size = 200
            vertex.addData3f(-size, -size, -5)
            vertex.addData3f(size, -size, -5)
            vertex.addData3f(size, size, -5)
            vertex.addData3f(-size, size, -5)
            
            for i in range(4):
                color.addData4f(0.1, 0.1, 0.15, 1)
            
            tris = GeomTriangles(Geom.UHStatic)
            tris.addVertices(0, 1, 2)
            tris.addVertices(0, 2, 3)
            
            geom = Geom(vdata)
            geom.addPrimitive(tris)
            node = GeomNode('ground_node')
            node.addGeom(geom)
            
            ground = self.render.attachNewNode(node)

    def setup_emissive_rendering(self):
        """Setup emissive rendering"""
        self.render.clearLight()
        self.render.setLightOff()
        
        # Brighter ambient so we can see the ground
        ambient_light = AmbientLight('ambient')
        ambient_light.setColor((0.1, 0.1, 0.15, 1))
        ambient_node = self.render.attachNewNode(ambient_light)
        self.render.setLight(ambient_node)

    def create_shell(self, position=None, color_type=None):
        """Create a shell that launches from ground"""
        if position is None:
            position = Vec3(
                random.uniform(-self.launch_spread, self.launch_spread),
                random.uniform(-self.launch_spread, self.launch_spread) + 50,
                self.ground_level
            )
        
        if color_type is None:
            color_type = random.choice(list(self.colors.keys()))
        
        shell = {
            'position': position,
            'velocity': Vec3(0, 0, random.uniform(15, 25)),  # Up in Z direction
            'color_type': color_type,
            'age': 0.0,
            'max_age': random.uniform(2.0, 3.0),
            'node': None,
            'state': 'rising',
            'brightness': 1.0
        }
        
        # Create visual node
        shell['node'] = self.create_letter_node('•', shell['position'], color_type, 2.0)
        self.shells.append(shell)
        print(f"Created shell at {position}")
        return shell

    def create_shell(self, position=None, color_type=None):
        """Create a shell that launches from ground"""
        if position is None:
            position = Vec3(
                random.uniform(-self.launch_spread, self.launch_spread),
                random.uniform(-self.launch_spread, self.launch_spread) + 50,
                self.ground_level
            )
        
        if color_type is None:
            color_type = random.choice(list(self.colors.keys()))
        
        shell = {
            'position': position,
            'velocity': Vec3(0, 0, random.uniform(20, 30)),  # Faster upward speed
            'color_type': color_type,
            'age': 0.0,
            'max_age': random.uniform(2.5, 4.0),  # Longer lifespan
            'node': None,
            'state': 'rising',
            'brightness': 1.0
        }
        
        # Create visual node
        shell['node'] = self.create_letter_node('•', shell['position'], color_type, 2.0)
        self.shells.append(shell)
        return shell

    def create_flare(self, ignition, index):
        """Create a single flare with better explosion patterns"""
        # More varied directions - spherical distribution but biased outward
        theta = random.uniform(0, 2 * math.pi)
        phi = random.uniform(0, math.pi)
        
        # Make most flares go more horizontal than vertical for better spread
        speed = random.uniform(8, 25)  # Wider speed range
        
        velocity = Vec3(
            math.sin(phi) * math.cos(theta) * speed,
            math.sin(phi) * math.sin(theta) * speed, 
            math.cos(phi) * speed * 0.7  # Reduced upward bias
        )
        
        # Add some randomness to make patterns more interesting
        velocity += Vec3(
            random.uniform(-3, 3),
            random.uniform(-3, 3),
            random.uniform(-2, 2)
        )
        
        flare = {
            'position': ignition['position'].copy(),
            'velocity': velocity,
            'color_type': ignition['color_type'],
            'base_color': self.colors[ignition['color_type']],
            'age': 0.0,
            'max_age': random.uniform(2.0, 4.0),  # Longer lifespan
            'node': None,
            'brightness': 1.0,
            'gravity': 4.0,  # MUCH LESS INTENSE GRAVITY
            'drag': 0.97,    # Less drag for longer travel
            'fade_start': random.uniform(1.5, 2.5)  # When to start fading
        }
        
        flare['node'] = self.create_letter_node('•', flare['position'], flare['color_type'], flare['brightness'])
        self.flares.append(flare)
        return flare

    def update_flares(self, task):
        """Update flare behavior with better physics"""
        dt = globalClock.getDt()
        
        flares_to_remove = []
        
        for flare in self.flares:
            flare['age'] += dt
            
            # Apply physics - MUCH GENTLER GRAVITY
            flare['velocity'].z -= flare['gravity'] * dt  # Gentle gravity
            flare['velocity'] *= flare['drag']  # Air resistance
            
            # Update position
            flare['position'] += flare['velocity'] * dt
            
            # Better brightness curve - bright then gradual fade
            if flare['age'] < flare['fade_start']:
                # Bright phase
                flare['brightness'] = 1.0
            else:
                # Gradual fade phase
                fade_factor = (flare['age'] - flare['fade_start']) / (flare['max_age'] - flare['fade_start'])
                flare['brightness'] = max(0, 1.0 - fade_factor)
            
            # Update visual
            if flare['node']:
                flare['node'].setPos(flare['position'])
                flare['node'].setScale(1.2 * flare['brightness'])  # Slightly larger
                
                base_color = flare['base_color']
                flare['node'].setColor(Vec4(
                    base_color.x * flare['brightness'],
                    base_color.y * flare['brightness'],
                    base_color.z * flare['brightness'],
                    flare['brightness']
                ))
            
            # Check for removal
            if flare['age'] >= flare['max_age'] or flare['brightness'] <= 0.01:
                flares_to_remove.append(flare)
        
        # Remove dead flares
        for flare in flares_to_remove:
            if flare['node']:
                flare['node'].removeNode()
            self.flares.remove(flare)
        
        return Task.cont

    def create_letter_node(self, letter, position, color_type, brightness=1.0):
        """Create a properly billboarded letter node"""
        if letter not in self.char_meshes:
            letter = '•'
            
        node = self.char_meshes[letter].copyTo(self.render)
        node.setPos(position)
        node.setScale(1.8 * brightness)  # Larger scale
        
        # PROPER BILLBOARDING - always face camera
        node.setBillboardPointEye()
        
        # Set color
        base_color = self.colors[color_type]
        color = Vec4(
            base_color.x * brightness,
            base_color.y * brightness,
            base_color.z * brightness,
            1.0
        )
        
        material = Material()
        material.setShininess(5.0)
        material.setEmission(color)
        material.setLocal(True)
        
        node.setColor(color)
        node.setMaterial(material, 1)
        node.setLightOff()
        node.setTwoSided(True)
        
        return node

    def create_ignition(self, shell):
        """Create an ignition with better visual impact"""
        ignition = {
            'position': shell['position'],
            'color_type': shell['color_type'],
            'age': 0.0,
            'max_age': 0.4,  # Slightly longer flash
            'brightness': 4.0,  # Brighter flash
            'node': None
        }
        
        # Create bright flash - make sure it's billboarded too
        ignition['node'] = self.create_letter_node('★', ignition['position'], ignition['color_type'], ignition['brightness'])
        self.ignitions.append(ignition)
        
        # Create MORE flares from ignition for better explosion effect
        self.create_flares_from_ignition(ignition)
        
        return ignition

    def create_flares_from_ignition(self, ignition):
        """Create multiple flares from an ignition - MORE VARIETY"""
        flare_count = random.randint(30, 80)  # More flares for better explosions
        
        for i in range(flare_count):
            if len(self.flares) >= self.max_flares:
                break
            self.create_flare(ignition, i)

    def update_ignitions(self, task):
        """Update ignition behavior with better visual effect"""
        dt = globalClock.getDt()
        
        ignitions_to_remove = []
        
        for ignition in self.ignitions:
            ignition['age'] += dt
            
            # Bright flash with pulsing effect
            pulse = math.sin(ignition['age'] * 20) * 0.5 + 1.0  # Pulsing effect
            ignition['brightness'] = max(0, (4.0 - (ignition['age'] / ignition['max_age']) * 5.0) * pulse)
            
            if ignition['node']:
                ignition['node'].setScale(2.5 * ignition['brightness'])  # Larger scale
                base_color = self.colors[ignition['color_type']]
                ignition['node'].setColor(Vec4(
                    base_color.x * ignition['brightness'],
                    base_color.y * ignition['brightness'],
                    base_color.z * ignition['brightness'],
                    ignition['brightness']
                ))
            
            if ignition['age'] >= ignition['max_age']:
                ignitions_to_remove.append(ignition)
        
        # Remove dead ignitions
        for ignition in ignitions_to_remove:
            if ignition['node']:
                ignition['node'].removeNode()
            self.ignitions.remove(ignition)
        
        return Task.cont

    def update_cleanup(self, task):
        """Clean up old elements"""
        # Additional cleanup if needed
        return Task.cont

    def setup_camera(self):
        """Simple camera setup that definitely works"""
        self.disableMouse()
        
        # Standard field of view
        self.camLens.setFov(60)
        self.camLens.setNear(1)
        self.camLens.setFar(500)
        
        # Position camera to see the action
        # In Panda3D: 
        # X = left/right, Y = forward/backward, Z = up/down
        self.camera.setPos(0, -80, 30)  # Back from scene, elevated
        
        # Look at the center of where action happens
        self.camera.lookAt(0, 50, 20)
        
        print(f"Camera positioned at {self.camera.getPos()}, looking at (0, 50, 20)")

    def update_global_time(self, task):
        """Update global time for effects"""
        dt = globalClock.getDt()
        self.global_time += dt
        return Task.cont

    def load_bam_meshes(self):
        """Load character meshes with fallbacks"""
        self.char_meshes = {}
        
        # Try to load some basic shapes
        for char in ['•', '★', 'o', '*']:
            try:
                # Try different possible locations
                bam_path = f"./bam/{char}.bam"
                if os.path.exists(bam_path):
                    model = self.loader.loadModel(bam_path)
                    if model:
                        model.setLightOff()
                        model.setTwoSided(True)
                        self.char_meshes[char] = model
                        print(f"Loaded mesh for '{char}'")
                else:
                    self.create_fallback_mesh(char)
            except:
                self.create_fallback_mesh(char)
        
        # If nothing loaded, create at least one fallback
        if not self.char_meshes:
            self.create_fallback_mesh('•')
            print("Using fallback meshes")

    def create_fallback_mesh(self, char):
        """Create simple visible quad mesh"""
        format = GeomVertexFormat.getV3n3c4()
        vdata = GeomVertexData('fallback', format, Geom.UHStatic)
        vertex = GeomVertexWriter(vdata, 'vertex')
        normal = GeomVertexWriter(vdata, 'normal')
        color = GeomVertexWriter(vdata, 'color')
        
        # Create a visible quad
        size = 0.3
        vertices = [
            (-size, -size, 0), (size, -size, 0), 
            (size, size, 0), (-size, size, 0)
        ]
        
        for v in vertices:
            vertex.addData3f(v[0], v[1], v[2])
            normal.addData3f(0, 0, 1)
            color.addData4f(1, 1, 1, 1)
        
        tris = GeomTriangles(Geom.UHStatic)
        tris.addVertices(0, 1, 2)
        tris.addVertices(0, 2, 3)
        
        geom = Geom(vdata)
        geom.addPrimitive(tris)
        node = GeomNode(f'mesh_{char}')
        node.addGeom(geom)
        
        mesh_node = NodePath(node)
        material = Material()
        material.setShininess(5.0)
        material.setEmission((1, 1, 1, 1))
        material.setLocal(True)
        
        mesh_node.setMaterial(material, 1)
        mesh_node.setLightOff()
        mesh_node.setTwoSided(True)
        
        self.char_meshes[char] = mesh_node

    def setup_controls(self):
        """Setup controls"""
        self.accept('escape', self.quit)
        self.accept('space', self.create_shell)
        self.accept('1', lambda: self.create_shell(color_type='red'))
        self.accept('2', lambda: self.create_shell(color_type='blue'))
        self.accept('3', lambda: self.create_shell(color_type='gold'))
        self.accept('4', lambda: self.create_shell(color_type='green'))
        self.accept('5', lambda: self.create_shell(color_type='purple'))
        
        print("Controls: SPACE=random shell, 1-5=colored shells, ESC=quit")

    def quit(self):
        """Clean shutdown"""
        if hasattr(self, 'mb'):
            self.mb.cleanup()
        if hasattr(self, 'bgm'):
            self.bgm.stop()
        self.destroy()
        sys.exit(0)

if __name__ == "__main__":
    app = FractalFireworks()
    app.run()