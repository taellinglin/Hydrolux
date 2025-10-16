from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import *
import numpy as np
import random
import string
import os
import math
import sys
import uuid
from motion_blur import MotionBlur
from panda3d.core import Fog
from panda3d.core import loadPrcFileData
from audio3d import Audio3d
from panda3d.core import ClockObject
# Configure before ShowBase initializes
loadPrcFileData("", """
    fullscreen true
    win-size 1920 1080
    show-frame-rate-meter false
    audio-volume 1.0
    audio-library-name p3openal_audio
    notify-level-audio debug
""")


class StarfieldTunnel(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        fog = Fog("SceneFog")

        # Set the fog color (R, G, B)
        fog.setColor(0.0, 0.0, 0.0)

        # Choose the fog mode
        fog.setLinearRange(1, 20)
        fog.setExpDensity(0.02)

        # Attach fog to the render tree
        self.render.setFog(fog)
        
        # Sound parameters
        self.sound_trigger_distance = 50
        self.sound_cooldown = 0  # seconds between sounds for same cell
        
        # Optional: Match fog color to background color for smooth fade
        self.setBackgroundColor(fog.getColor())
        
        # Tunnel parameters
        self.tunnel_layers = 1
        self.grid_size = 16
        self.layer_spacing = 3
        self.camera_speed = 0.25
        
        # Camera motion
        self.camera_position = 3.5
        self.camera_rotation = 1.35
        self.camera_spiral_radius = 2.5
        self.camera_spiral_speed = 0.125
        
        # Slice rotation
        self.slice_rotation = 0
        self.rotation_direction = 1
        self.rotation_speed = 0.125
        self.max_rotation = math.pi * 360
        
        # Visual parameters
        self.flicker_time = 0.0
        
        # Colors
        self.red_color = Vec4(1.0, 0.2, 0.1, 1.0)
        self.blue_color = Vec4(0.1, 0.3, 1.0, 1.0)
        
        # Storage
        self.cells = {}
        self.mesh_nodes = {}
        self.char_meshes = {}
        self.slice_rotations = {}
        self.cell_sounds = {}  # Track sounds per cell
        
        # Setup
        self.setBackgroundColor(0, 0, 0, 0)
        self.setup_emissive_rendering()
        self.load_bam_meshes()
        self.setup_camera()
        self.audio3d = Audio3d(self.sfxManagerList, self.camera)
        # Initialize tunnel
        #self.initialize_tunnel()
        self.audio3d.setAudioRange(100.0)  # Increase range
        # Enable motion blur
        self.mb = MotionBlur()
        
        # Start tasks
        self.taskMgr.add(self.update_tunnel, "update_tunnel")
        self.taskMgr.add(self.update_flicker, "update_flicker")
        self.taskMgr.add(self.update_camera, "update_camera")
        self.taskMgr.add(self.update_rotation, "update_rotation")
        self.taskMgr.add(self.update_audio, "update_audio")  # ADD THIS!
        # Simple exit control
        self.accept('escape', self.quit)
        
        print("Starfield Tunnel initialized - Environmental 3D Audio enabled!")
        print(f"Loaded {len(self.audio3d.sfx3d)} environmental sounds")
            # WAIT A FRAME BEFORE PLAYING SOUNDS
        self.taskMgr.doMethodLater(0.1, self.delayed_audio_start, "delayed_audio")
        

    def update_audio(self, task):
        """Update audio system every frame"""
        dt = globalClock.getDt()
        self.audio3d.update(task)
        return task.cont
    def delayed_audio_start(self, task):
        # Now it's safe to create cells with audio
        self.initialize_tunnel()
        return task.done

        
    def setup_emissive_rendering(self):
        """Setup emissive rendering"""
        self.render.clearLight()
        self.render.setLightOff()
        
        ambient_light = AmbientLight('ambient')
        ambient_light.setColor((0.01, 0.01, 0.01, 1))
        ambient_node = self.render.attachNewNode(ambient_light)
        self.render.setLight(ambient_node)
    
    def load_bam_meshes(self):
        """Load character meshes"""
        bam_dir = "./bam"
        
        for char in string.ascii_lowercase:
            bam_path = os.path.join(bam_dir, f"{char}.bam")
            if os.path.exists(bam_path):
                try:
                    model = self.loader.loadModel(bam_path)
                    if model:
                        model.setLightOff()
                        model.setTwoSided(True)
                        self.char_meshes[char] = model
                except:
                    self.create_fallback_mesh(char)
            else:
                self.create_fallback_mesh(char)
        
        if not self.char_meshes:
            self.create_fallback_mesh('a')
    
    def create_fallback_mesh(self, char):
        """Create simple quad mesh"""
        format = GeomVertexFormat.getV3n3c4()
        vdata = GeomVertexData('fallback', format, Geom.UHDynamic)
        vertex = GeomVertexWriter(vdata, 'vertex')
        normal = GeomVertexWriter(vdata, 'normal')
        color = GeomVertexWriter(vdata, 'color')
        
        vertices = [(-0.2, 0, -0.2), (0.2, 0, -0.2), (0.2, 0, 0.2), (-0.2, 0, 0.2)]
        normals = [(0, 1, 0)] * 4
        
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
        
        mesh_node = NodePath(node)
        material = Material()
        material.setShininess(0.5)
        material.setEmission((1, 1, 1, 1))
        material.setLocal(True)
        
        mesh_node.setMaterial(material, 1)
        mesh_node.setLightOff()
        mesh_node.setTwoSided(True)
        
        self.char_meshes[char] = mesh_node
    
    def setup_camera(self):
        """Setup camera for tunnel view"""
        self.disableMouse()
        self.camLens.setFov(135)
        self.camLens.setNear(0.001)
        self.camLens.setFar(10000)
    
    def random_char(self):
        return random.choice(string.ascii_lowercase)
    
    def random_color_type(self):
        return random.random() > 0.5
    
    def get_slice_rotation(self, layer_y):
        """Calculate rotation for a specific slice layer"""
        slice_index = int(layer_y / self.layer_spacing)
        
        if slice_index not in self.slice_rotations:
            base_rotation = (slice_index % 4) * (math.pi / 2)
            self.slice_rotations[slice_index] = base_rotation
        
        return self.slice_rotations[slice_index]
    
    def initialize_tunnel(self):
        """Initialize the tunnel with rotating slices"""
        half_size = self.grid_size // 2
        
        for layer in range(self.tunnel_layers):
            layer_y = layer * self.layer_spacing
            slice_rotation = self.get_slice_rotation(layer_y)
            
            for x in range(-half_size, half_size + 1):
                for z in range(-half_size, half_size + 1):
                    distance = math.sqrt(x*x + z*z)
                    if distance <= half_size and random.random() > 0.6:
                        self.create_cell(x, z, layer_y, slice_rotation)
    
    def create_cell(self, x, z, y, slice_rotation):
        """Create a cell at specific 3D position with slice rotation"""
        cell_key = (x, z, y)
        
        # Apply slice rotation to position
        cos_rot = math.cos(slice_rotation)
        sin_rot = math.sin(slice_rotation)
        
        # Rotate around Y axis
        rotated_x = x * cos_rot - z * sin_rot
        rotated_z = x * sin_rot + z * cos_rot
        
        world_x = rotated_x * 1.0
        world_z = rotated_z * 1.0
        world_y = y
        
        char = self.random_char()
        self.cells[cell_key] = {
            'char': char,
            'is_red': self.random_color_type(),
            'brightness': random.uniform(0.8, 1.5),
            'flicker_speed': random.uniform(3.0, 8.0),
            'flicker_phase': random.uniform(0, 2 * math.pi),
            'hue_shift': random.uniform(-0.2, 0.2),
            'pulse_speed': random.uniform(1.0, 4.0),
            'pulse_phase': random.uniform(0, 2 * math.pi),
            'world_pos': (world_x, world_y, world_z),
            'slice_rotation': slice_rotation,
            'base_pos': (x, z),
            'last_played': 0.0
        }
        
        self.create_cell_node(cell_key, world_x, world_y, world_z)
    
    def create_cell_node(self, cell_key, x, y, z):
        """Create visual representation of a cell"""
        cell_data = self.cells[cell_key]
        char = cell_data['char']
        
        if char not in self.char_meshes:
            char = 'a'
            
        node = self.char_meshes[char].copyTo(self.render)
        node.setPos(x, y, z)
        node.setScale(1)
        
        # Make them face the camera
        node.lookAt(self.camera)
        
        # Set initial color
        if cell_data['is_red']:
            base_color = self.red_color
        else:
            base_color = self.blue_color
            
        color = Vec4(
            base_color.x * cell_data['brightness'],
            base_color.y * cell_data['brightness'],
            base_color.z * cell_data['brightness'],
            1.0
        )
        
        material = Material()
        material.setShininess(1.0)
        material.setEmission(color)
        material.setLocal(True)
        
        node.setColor(color)
        node.setMaterial(material, 1)
        node.setLightOff()
        node.setTwoSided(True)

        self.mesh_nodes[cell_key] = node
        
        # Store the sound reference in the cell data so it persists
        try:
            self.audio3d.playSfx('circle', node, True)
            print(f"Playing circle for cell {cell_key}...")
        except Exception as e:
            print(f"Error playing sound for cell {cell_key}: {e}")
    
    def update_cell_visual(self, cell_key):
        """Update cell visual appearance"""
        cell_data = self.cells[cell_key]
        node = self.mesh_nodes[cell_key]
        
        # Calculate flicker
        flicker = math.sin(self.flicker_time * cell_data['flicker_speed'] + cell_data['flicker_phase']) * 0.3 + 1.0
        pulse = math.sin(self.flicker_time * cell_data['pulse_speed'] + cell_data['pulse_phase']) * 0.2 + 1.0
        
        brightness = cell_data['brightness'] * flicker * pulse
        brightness = max(0.3, min(2.0, brightness))
        
        # Get base color
        if cell_data['is_red']:
            base_color = self.red_color
        else:
            base_color = self.blue_color
        
        # Apply hue shift and brightness
        r = min(1.0, base_color.x * brightness + cell_data['hue_shift'])
        g = min(1.0, base_color.y * brightness)
        b = min(1.0, base_color.z * brightness - cell_data['hue_shift'])
        
        color = Vec4(r, g, b, 1.0)
        
        # Update material
        material = Material()
        material.setShininess(0.5)
        material.setEmission(color)
        material.setLocal(True)
        
        node.setColor(color)
        node.setMaterial(material, 1)
        
        # Scale variation
        scale = 0.86 + 0.04 * (brightness - 0.3) / 1.7
        node.setScale(scale)
        
        # Make sure it faces the camera
        node.lookAt(self.camera)
    
    def update_camera(self, task):
        """Move camera forward with corkscrew motion - NO RESET"""
        dt = ClockObject.getGlobalClock().getDt()
        
        # Move camera forward along Y axis - continuous, no reset
        self.camera_position += self.camera_speed * dt
        
        # Update camera rotation for corkscrew effect
        self.camera_rotation += self.camera_spiral_speed * dt
        
        # Calculate corkscrew position
        spiral_x = math.sin(self.camera_rotation) * self.camera_spiral_radius
        spiral_z = math.cos(self.camera_rotation) * self.camera_spiral_radius
        
        # Update camera position with corkscrew motion
        self.camera.setPos(spiral_x, self.camera_position, spiral_z + 1.5)
        
        # Look slightly ahead in the spiral
        look_ahead_x = math.sin(self.camera_rotation + 0.3) * self.camera_spiral_radius
        look_ahead_z = math.cos(self.camera_rotation + 0.3) * self.camera_spiral_radius
        self.camera.lookAt(look_ahead_x, self.camera_position + 10, look_ahead_z + 1.5)
        
        return Task.cont
    def update_rotation(self, task):
        """Update slice rotations for DNA-like effect"""
        dt = ClockObject.getGlobalClock().getDt()
        
        # Update global slice rotation
        self.slice_rotation += self.rotation_speed * dt * self.rotation_direction
        
        # Reverse direction when reaching max rotation
        if abs(self.slice_rotation) > self.max_rotation:
            self.rotation_direction *= -1
            self.slice_rotation = self.max_rotation * self.rotation_direction
        
        # Update all cells with new rotations
        for cell_key, cell_data in list(self.cells.items()):
            x, z = cell_data['base_pos']
            y = cell_key[2]
            
            # Get slice-specific rotation
            slice_index = int(y / self.layer_spacing)
            slice_base_rotation = (slice_index % 4) * (math.pi / 2)
            
            # Add the animated rotation
            total_rotation = slice_base_rotation + self.slice_rotation
            
            # Apply rotation
            cos_rot = math.cos(total_rotation)
            sin_rot = math.sin(total_rotation)
            
            rotated_x = x * cos_rot - z * sin_rot
            rotated_z = x * sin_rot + z * cos_rot
            
            world_x = rotated_x * 1.0
            world_z = rotated_z * 1.0
            
            # Update cell position
            cell_data['world_pos'] = (world_x, y, world_z)
            cell_data['slice_rotation'] = total_rotation
            
            # Update visual node
            if cell_key in self.mesh_nodes:
                self.mesh_nodes[cell_key].setPos(world_x, y, world_z)
        
        return Task.cont
    
    def update_tunnel(self, task):
        """Manage tunnel cells - seamless creation and destruction"""        
        cells_to_remove = []
        half_size = self.grid_size // 2
        
        # Define visible range around camera
        visible_range_ahead = 30  # How far ahead to generate cells
        visible_range_behind = 10  # How far behind to keep cells
        
        # Remove cells that are too far behind camera
        for cell_key, cell_data in list(self.cells.items()):
            world_y = cell_data['world_pos'][1]
            
            if world_y < self.camera_position - visible_range_behind:
                cells_to_remove.append(cell_key)
        
        # Remove old cells
        for cell_key in cells_to_remove:
            if cell_key in self.mesh_nodes:
                self.mesh_nodes[cell_key].removeNode()
                del self.mesh_nodes[cell_key]
            if cell_key in self.cells:
                del self.cells[cell_key]
        
        # Find the farthest Y position we have cells for
        farthest_y = max([cell_data['world_pos'][1] for cell_data in self.cells.values()]) if self.cells else self.camera_position
        
        # Keep generating new cells ahead of camera until we reach visible range
        while farthest_y < self.camera_position + visible_range_ahead:
            new_y = farthest_y + self.layer_spacing
            
            # Get rotation for this new slice
            slice_rotation = self.get_slice_rotation(new_y) + self.slice_rotation
            
            # Fill the new layer with cells
            for x in range(-half_size, half_size + 1):
                for z in range(-half_size, half_size + 1):
                    distance = math.sqrt(x*x + z*z)
                    if distance <= half_size and random.random() > 0.6:
                        self.create_cell(x, z, new_y, slice_rotation)
            
            farthest_y = new_y
        
        return Task.cont
    
    def update_flicker(self, task):
        """Update flickering effects"""
        dt = ClockObject.getGlobalClock().getDt()
        self.flicker_time += dt
        
        for cell_key in list(self.mesh_nodes.keys()):
            if cell_key in self.cells:
                self.update_cell_visual(cell_key)
        
        return Task.cont
    
    
    def quit(self):
        # Clean up audio
        if hasattr(self, 'audio3d'):
            self.audio3d.stopLoopingAudio()
            
        if hasattr(self, 'mb'):
            self.mb.cleanup()
        self.destroy()
        sys.exit(0)

if __name__ == "__main__":
    app = StarfieldTunnel()
    app.run()