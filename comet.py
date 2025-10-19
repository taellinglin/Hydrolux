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
import threading
from queue import Queue

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
        fog.setLinearRange(2, 8)
        fog.setExpDensity(0.05)
        self.cell_creation_queue = Queue()
        self.creation_thread = None
        self.should_stop_creation = False
        self.pending_cells = {}  # Track cells being created
        self.pending_cells_lock = threading.Lock()  # Thread safety
        
        # Start the background thread after everything else is initialized
        self.start_creation_thread()
        # Base frequency: 220Hz (A3) with playRate 1.0
        self.base_freq = 220.0
        # Camera velocity tracking
        self.camera_prev_pos = Vec3(0, 0, 0)
        self.camera_velocity = Vec3(0, 0, 0)
        
        # Set Doppler factor (but it won't work without velocities)
        # 26-note scale frequencies in Hz (calculated from the cent values)
        self.scale_frequencies = [
            # Pentatonic Scale - Multiple Octaves
            # C Major Pentatonic: C, D, E, G, A
            
            # Octave 1 (Low)
            65.41,    # [0] C2
            73.42,    # [1] D2
            82.41,    # [2] E2
            98.00,    # [3] G2
            110.00,   # [4] A2
            
            # Octave 2
            130.81,   # [5] C3
            146.83,   # [6] D3
            164.81,   # [7] E3
            196.00,   # [8] G3
            220.00,   # [9] A3
            
            # Octave 3
            261.63,   # [10] C4 (Middle C)
            293.66,   # [11] D4
            329.63,   # [12] E4
            392.00,   # [13] G4
            440.00,   # [14] A4
            
            # Octave 4
            523.25,   # [15] C5
            587.33,   # [16] D5
            659.25,   # [17] E5
            783.99,   # [18] G5
            880.00,   # [19] A5
            
            # Octave 5 (High)
            1046.50,  # [20] C6
            1174.66,  # [21] D6
            1318.51,  # [22] E6
            1567.98,  # [23] G6
            1760.00,  # [24] A6
            
            # Extended for more range
            2093.00,  # [25] C7
            2349.32,  # [26] D7
            2637.02,  # [27] E7
            3135.96,  # [28] G7
            3520.00,  # [29] A7
            
            # Bonus: Minor Pentatonic (A minor: A, C, D, E, G)
            110.00,   # [30] A2 (minor root)
            130.81,   # [31] C3
            146.83,   # [32] D3
            164.81,   # [33] E3
            196.00,   # [34] G3
            
            220.00,   # [35] A3
            261.63,   # [36] C4
            293.66,   # [37] D4
            329.63,   # [38] E4
            392.00,   # [39] G4
            
            # Microtonal variations for texture
            277.18,   # [40] C♯/D♭
            311.13,   # [41] D♯/E♭
            369.99,   # [42] F♯/G♭
            415.30,   # [43] G♯/A♭
            466.16,   # [44] A♯/B♭
            
            # Harmonic series partials for metallic tones
            55.00,    # [45] A1 (sub)
            82.50,    # [46] E2 (5th)
            110.00,   # [47] A2
            137.50,   # [48] C♯3
            165.00,   # [49] E3
            192.50,   # [50] G3
            220.00,   # [51] A3
        ]
        # Attach fog to the render tree
        self.render.setFog(fog)
        
        # Sound parameters
        self.sound_trigger_distance = 50
        self.sound_cooldown = 16  # seconds between sounds for same cell
        
        # Optional: Match fog color to background color for smooth fade
        self.setBackgroundColor(fog.getColor())
        
        # Tunnel parameters
        self.tunnel_layers = 1
        self.grid_size = 12
        self.layer_spacing = 8
        self.camera_speed = 6.25
        
        # Camera motion
        self.camera_position = 0
        self.camera_rotation = 0.35
        self.camera_spiral_radius = -1
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
        self.audio3d.setAudioRange(50.0)  # Increase range
        # Enable motion blur
        self.mb = MotionBlur(self.camera)
        self.audio3d.audio3d.setDopplerFactor(50.0)  # Start with a more reasonable value
        self.setup_drum_loop()
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
        
    def start_creation_thread(self):
        """Start background thread for cell creation"""
        self.creation_thread = threading.Thread(target=self._cell_creation_worker, daemon=True)
        self.creation_thread.start()
        print("Background cell creation thread started")
    def setup_drum_loop(self):
        """Setup looping drum beat that changes speed with camera velocity"""
        try:
            # Load the drum sound
            self.drum_sound = self.loader.loadSfx('drum.wav')
            self.drum_sound.setLoop(True)
            self.drum_sound.setVolume(0.1)  # Adjust volume as needed
            
            # Attach to camera for 3D positioning (or use a fixed position)
            self.audio3d.audio3d.attachSoundToObject(self.drum_sound, self.camera)
            
            # Set initial play rate
            self.drum_sound.setPlayRate(1.0)
            
            # Start playing
            self.drum_sound.play()
            
            print("Drum loop started")
            
        except Exception as e:
            print(f"Error setting up drum loop: {e}")

    def update_drum_speed(self):
        """Update drum speed based on camera velocity"""
        if hasattr(self, 'drum_sound') and self.drum_sound:
            # Calculate camera speed magnitude
            camera_speed = self.camera_velocity.length()
            
            # Map camera speed to drum play rate
            # Adjust these values to taste:
            min_speed = 0.2    # Minimum camera speed for slowest drum
            max_speed = 10.0   # Maximum camera speed for fastest drum
            min_rate = 0.5     # Slowest drum speed
            max_rate = 3.5     # Fastest drum speed
            
            # Calculate normalized speed (0 to 1)
            normalized_speed = (camera_speed - min_speed) / (max_speed - min_speed)
            normalized_speed = max(0.0, min(1.0, normalized_speed))  # Clamp to 0-1
            
            # Map to play rate range
            play_rate = min_rate + (max_rate - min_rate) * normalized_speed
            
            # Apply with some smoothing to avoid jarring changes
            current_rate = self.drum_sound.getPlayRate()
            smoothed_rate = current_rate * 0.8 + play_rate * 0.1
            
            self.drum_sound.setPlayRate(smoothed_rate)
            
            # Optional: Debug output
            if random.random() < 0.02:
                print(f"Drum speed: {smoothed_rate:.2f} (camera speed: {camera_speed:.2f})")
    def _cell_creation_worker(self):
        """Background worker for creating cells"""
        while not self.should_stop_creation:
            try:
                # Get creation task from queue
                task_data = self.cell_creation_queue.get(timeout=0.1)
                if task_data is None:  # Stop signal
                    break
                    
                cell_key, x, z, y, slice_rotation = task_data
                self._create_cell_in_background(cell_key, x, z, y, slice_rotation)
                
                self.cell_creation_queue.task_done()
            except:
                pass  # Timeout, continue

    def _create_cell_in_background(self, cell_key, x, z, y, slice_rotation):
        """Create a cell in the background thread (mesh creation only)"""
        try:
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
            
            # Create cell data structure
            cell_data = {
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
            
            # Create the mesh node in the background
            if char not in self.char_meshes:
                char = 'a'
                
            # This is the expensive part - creating the mesh
            node = self.char_meshes[char].copyTo(NodePath())  # Don't attach to render yet
            node.setPos(world_x, world_y, world_z)
            node.setScale(0.08)
            
            # Set up visual properties
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
            
            # Store the prepared cell for main thread to finalize
            with self.pending_cells_lock:
                self.pending_cells[cell_key] = {
                    'cell_data': cell_data,
                    'node': node,
                    'world_pos': (world_x, world_y, world_z)
                }
                
        except Exception as e:
            print(f"Error creating cell in background: {e}")

    def queue_cell_creation(self, cell_key, x, z, y, slice_rotation):
        """Queue a cell for creation in background thread"""
        self.cell_creation_queue.put((cell_key, x, z, y, slice_rotation))
        
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
                        self.create_cell_background(x, z, layer_y, slice_rotation)
    def setup_cell_audio(self, cell_key, node, cell_data):
        """Set up audio for a cell (must be called in main thread)"""
        try:
            char = cell_data['char']
            
            char_to_note = {
                'a': 0, 'b': 1, 'c': 2, 'd': 3, 'e': 4, 'f': 5, 'g': 6,
                'h': 7, 'i': 8, 'j': 9, 'k': 10, 'l': 11, 'm': 12,
                'n': 13, 'o': 14, 'p': 15, 'q': 16, 'r': 17, 's': 18,
                't': 19, 'u': 20, 'v': 21, 'w': 22, 'x': 23, 'y': 24, 'z': 25
            }
            
            note_index = char_to_note.get(char, 0)
            volume = random.uniform(0.0, 1.0)
            
            # FIX: Use the same pitch calculation as in create_cell_node
            pitch = self.scale_frequencies[note_index] / self.base_freq
            
            current_time = globalClock.getFrameTime()
            if current_time - cell_data.get('last_played', 0) > 1.0:
                # PASS THE VELOCITY for Doppler effect
                obj_velocity = cell_data.get('velocity', Vec3(0, 0, 0))
                self.audio3d.playSfx(char, node, True, random.choice(self.scale_frequencies)/self.base_freq, volume, obj_velocity)
                cell_data['last_played'] = current_time
                
        except Exception as e:
            print(f"Error setting up audio for cell {cell_key}: {e}")
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
        node.setScale(0.08)
        
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
            # Map character to scale index (0-25)
            char_to_note = {
                'a': 0, 'b': 1, 'c': 2, 'd': 3, 'e': 4, 'f': 5, 'g': 6,
                'h': 7, 'i': 8, 'j': 9, 'k': 10, 'l': 11, 'm': 12,
                'n': 13, 'o': 14, 'p': 15, 'q': 16, 'r': 17, 's': 18,
                't': 19, 'u': 20, 'v': 21, 'w': 22, 'x': 23, 'y': 24, 'z': 25
            }
            
            # Default to note 0 if character not found
            note_index = char_to_note.get(char, 0)
            
            # TRACK CHARACTER APPEARANCE COUNT
            if not hasattr(self, 'char_appearance_count'):
                self.char_appearance_count = {}
            
            # Increment appearance count for this character
            self.char_appearance_count[char] = self.char_appearance_count.get(char, 0) + 1
            
            # Calculate note index based on appearance count (wrap around scale)
            appearance_count = self.char_appearance_count[char]
            scale_length = len(self.scale_frequencies)
            dynamic_note_index = (note_index + appearance_count - 1) % scale_length
            
            # FIX: Use proper volume range (0.0 to 1.0)
            volume = random.uniform(0.3, 0.8)  # More reasonable volume range
            
            # Calculate pitch based on character appearance
            pitch = self.scale_frequencies[dynamic_note_index] / self.base_freq
            
            print(f"Character '{char}' -> appearance {appearance_count} -> note {dynamic_note_index} -> pitch {pitch:.4f} -> volume {volume:.2f}")
            
            # FIX: Add a small delay to prevent audio overload
            current_time = globalClock.getFrameTime()
            if current_time - cell_data.get('last_played', 0) > 1.0:  # 100ms cooldown
                self.audio3d.playSfx(char, node, True, random.choice(self.scale_frequencies)/self.base_freq, volume)
                cell_data['last_played'] = current_time
                
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
        """Smooth rollercoaster camera with continuous, fluid motion"""
        dt = ClockObject.getGlobalClock().getDt()
        
        time_elapsed = globalClock.getFrameTime()
        
        # Store previous position for velocity calculation
        self.camera_prev_pos = self.camera.getPos()
        
        # Smooth speed variation with multiple frequencies
        speed_variation = (math.sin(time_elapsed * 0.3) * 0.4 + 
                        math.sin(time_elapsed * 0.7) * 0.2 + 
                        math.sin(time_elapsed * 0.1) * 0.1)
        coaster_speed = 1.0 + speed_variation
        
        # Move camera forward with smooth acceleration
        self.camera_position += self.camera_speed * coaster_speed * dt
        
        # SMOOTH ROLLERCOASTER TRACK with multiple frequencies for organic motion
        # Primary track motion
        track_x = math.sin(time_elapsed * 0.5) * 2.5  # Gentle left/right turns
        track_z = math.cos(time_elapsed * 0.3) * 1.5  # Gentle forward/back motion
        track_y = math.sin(time_elapsed * 0.2) * 1.0  # Gentle hills and drops
        
        # Secondary subtle motions for more organic feel
        subtle_x = math.sin(time_elapsed * 1.2) * 0.8
        subtle_z = math.cos(time_elapsed * 0.9) * 0.6
        subtle_y = math.sin(time_elapsed * 0.5) * 0.4
        
        # Very slow drifting motion
        drift_x = math.sin(time_elapsed * 0.08) * 1.2
        drift_z = math.cos(time_elapsed * 0.06) * 0.8
        
        # Smooth corkscrew motion
        corkscrew = time_elapsed * 0.8
        corkscrew_x = math.sin(corkscrew) * 0.6
        corkscrew_z = math.cos(corkscrew) * 0.6
        
        # Combine all motions with smooth blending
        final_x = track_x + subtle_x + drift_x + corkscrew_x
        final_z = track_z + subtle_z + drift_z + corkscrew_z + 2.0
        final_y = self.camera_position + track_y + subtle_y
        
        # Set camera position
        self.camera.setPos(final_x, final_y, final_z)
        
        # SMOOTH BANKING with derivative-based calculation
        # Calculate smooth turn direction (derivative of track motion)
        turn_strength = (math.cos(time_elapsed * 0.5) * 2.5 +  # Primary turn
                        math.cos(time_elapsed * 1.2) * 0.8 +   # Secondary
                        math.cos(time_elapsed * 0.08) * 0.3)   # Very slow drift
        
        # Apply smooth banking with limits
        bank_angle = turn_strength * 15  # Reduced from 30 to 15 for smoother banking
        self.camera.setR(bank_angle)
        
        # SMOOTH LOOK-AHEAD with anticipation
        look_ahead = 5.0  # Slightly further look-ahead for smoother transitions
        
        # Calculate future position with same smooth motion
        future_time = time_elapsed + look_ahead
        future_track_x = math.sin(future_time * 0.5) * 2.5
        future_track_z = math.cos(future_time * 0.3) * 1.5
        future_track_y = math.sin(future_time * 0.2) * 1.0
        
        future_subtle_x = math.sin(future_time * 1.2) * 0.8
        future_subtle_z = math.cos(future_time * 0.9) * 0.6
        future_subtle_y = math.sin(future_time * 0.5) * 0.4
        
        future_drift_x = math.sin(future_time * 0.08) * 1.2
        future_drift_z = math.cos(future_time * 0.06) * 0.8
        
        future_corkscrew = future_time * 0.8
        future_corkscrew_x = math.sin(future_corkscrew) * 0.6
        future_corkscrew_z = math.cos(future_corkscrew) * 0.6
        
        # Combined future look-at target
        future_x = (future_track_x + future_subtle_x + future_drift_x + 
                future_corkscrew_x)
        future_z = (future_track_z + future_subtle_z + future_drift_z + 
                future_corkscrew_z + 2.0)
        future_y = (self.camera_position + look_ahead * self.camera_speed + 
                future_track_y + future_subtle_y)
        
        # Add slight vertical anticipation (look up before hills, down before drops)
        vertical_anticipation = math.cos(future_time * 0.2) * 3.0
        future_y += vertical_anticipation
        
        # Smooth look-at
        self.camera.lookAt(future_x, future_y, future_z)
        
        # CONTINUOUS SPECIAL MOVES (no abrupt triggers)
        # Continuous gentle looping motion
        continuous_loop = math.sin(time_elapsed * 0.15) * 8  # Very slow, gentle loops
        self.camera.setR(self.camera.getR() + continuous_loop * dt)
        
        # Continuous gentle pitching
        continuous_pitch = math.sin(time_elapsed * 0.25) * 5  # Gentle up/down nodding
        self.camera.setP(continuous_pitch)
        
        # Calculate smooth camera velocity
        current_pos = self.camera.getPos()
        self.camera_velocity = (current_pos - self.camera_prev_pos) / dt
        
        return Task.cont
    def update_rotation(self, task):
        """Update slice rotations for DNA-like effect"""
        dt = ClockObject.getGlobalClock().getDt()
        
        # Store previous positions for velocity calculation
        prev_positions = {}
        for cell_key, cell_data in self.cells.items():
            if cell_key in self.mesh_nodes:
                prev_positions[cell_key] = self.mesh_nodes[cell_key].getPos()
        
        # Update global slice rotation
        self.slice_rotation += self.rotation_speed * dt * self.rotation_direction
        
        # Update all cells with new rotations
        for cell_key, cell_data in list(self.cells.items()):
            x, z = cell_data['base_pos']
            y = cell_key[2]
            
            slice_index = int(y / self.layer_spacing)
            slice_base_rotation = (slice_index % 4) * (math.pi / 2)
            total_rotation = slice_base_rotation + self.slice_rotation
            
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
                
                # Calculate velocity for Doppler effect
                current_pos = self.mesh_nodes[cell_key].getPos()
                if cell_key in prev_positions:
                    prev_pos = prev_positions[cell_key]
                    velocity = (current_pos - prev_pos) / dt
                    cell_data['velocity'] = velocity
        
        return Task.cont
    
    def update_tunnel(self, task):
        """Manage tunnel cells with background creation"""
        cells_to_remove = []
        half_size = self.grid_size // 2
        # Debug background thread occasionally
        if random.random() < 0.1:
            self.debug_background_thread()
        # Define visible range around camera
        visible_range_ahead = 32
        visible_range_behind = 6
        
        # First, finalize any cells created in background
        cells_finalized = self.finalize_pending_cells()
        
        # Remove cells that are too far behind camera
        for cell_key, cell_data in list(self.cells.items()):
            world_y = cell_data['world_pos'][1]
            if world_y < self.camera_position - visible_range_behind:
                cells_to_remove.append(cell_key)
        
        # Remove old cells (including audio)
        max_deletions_per_frame = 8
        deletions_this_frame = 0
        
        for cell_key in cells_to_remove:
            if deletions_this_frame >= max_deletions_per_frame:
                break
                
            if cell_key in self.mesh_nodes:
                node = self.mesh_nodes[cell_key]
                self.audio3d.stopSfx(node)
                node.removeNode()
                del self.mesh_nodes[cell_key]
            if cell_key in self.cells:
                del self.cells[cell_key]
            
            deletions_this_frame += 1
        
        # Find the farthest Y position we have cells for
        farthest_y = max([cell_data['world_pos'][1] for cell_data in self.cells.values()]) if self.cells else self.camera_position
        
        # Queue new cells for background creation
        max_creations_per_frame = 25
        creations_this_frame = 0
        
        # Calculate how many layers we need to create
        layers_needed = math.ceil((self.camera_position + visible_range_ahead - farthest_y) / self.layer_spacing)
        
        for layer_offset in range(layers_needed):
            if creations_this_frame >= max_creations_per_frame:
                break
                
            new_y = farthest_y + (layer_offset * self.layer_spacing)
            slice_rotation = self.get_slice_rotation(new_y) + self.slice_rotation
            
            # Queue cells for background creation
            for x in range(-half_size, half_size + 1):
                for z in range(-half_size, half_size + 1):
                    if creations_this_frame >= max_creations_per_frame:
                        break
                        
                    distance = math.sqrt(x*x + z*z)
                    if distance <= half_size and random.random() > 0.6:
                        cell_key = (x, z, new_y)
                        # Check if not already existing or pending
                        if cell_key not in self.cells and cell_key not in self.pending_cells:
                            self.create_cell_background(x, z, new_y, slice_rotation)
                            creations_this_frame += 1
        
        # Debug output
        if random.random() < 0.05:
            pending_count = len(self.pending_cells)
            queue_size = self.cell_creation_queue.qsize()
            active_cells = len(self.cells)
            print(f"Cells: {active_cells}, Pending: {pending_count}, Queue: {queue_size}, Finalized: {cells_finalized}, Created: {creations_this_frame}")
            print(f"Camera Y: {self.camera_position:.1f}, Farthest Y: {farthest_y:.1f}")
        
        return Task.cont
    def debug_background_thread(self):
        """Debug the background thread status"""
        if not hasattr(self, 'creation_thread'):
            print("Background thread not created!")
            return
            
        if not self.creation_thread.is_alive():
            print("Background thread is dead!")
            return
            
        print(f"Background thread alive: {self.creation_thread.is_alive()}")
        print(f"Queue size: {self.cell_creation_queue.qsize()}")
        print(f"Pending cells: {len(self.pending_cells)}")
    def finalize_pending_cells(self):
        """Finalize cells created in background thread (call this in main thread)"""
        with self.pending_cells_lock:
            if not self.pending_cells:
                return 0
                
            finalized_count = 0
            # DRAMATICALLY INCREASE finalization rate to match creation rate
            max_finalize_per_frame = 25  # Increased from 8 to 25
            
            # Process pending cells in order of creation (oldest first)
            pending_keys = sorted(self.pending_cells.keys(), key=lambda k: k[2])  # Sort by Y position
            
            for cell_key in pending_keys:
                if finalized_count >= max_finalize_per_frame:
                    break
                    
                if cell_key in self.pending_cells:
                    pending_data = self.pending_cells[cell_key]
                    cell_data = pending_data['cell_data']
                    node = pending_data['node']
                    world_x, world_y, world_z = pending_data['world_pos']
                    
                    # Only finalize cells that are near the camera (within audio range)
                    camera_pos = self.camera.getPos()
                    cell_pos = Vec3(world_x, world_y, world_z)
                    distance = (cell_pos - camera_pos).length()
                    
                    if distance < self.audio3d.audio_range * 1.5:  # Only finalize if within range
                        # Finalize the cell in main thread
                        node.reparentTo(self.render)
                        node.lookAt(self.camera)
                        
                        # Store in main data structures
                        self.cells[cell_key] = cell_data
                        self.mesh_nodes[cell_key] = node
                        
                        # Set up audio
                        self.setup_cell_audio(cell_key, node, cell_data)
                        
                        # Remove from pending
                        del self.pending_cells[cell_key]
                        finalized_count += 1
            
            return finalized_count
    def update_flicker(self, task):
        """Update flickering effects"""
        dt = ClockObject.getGlobalClock().getDt()
        self.flicker_time += dt
        
        for cell_key in list(self.mesh_nodes.keys()):
            if cell_key in self.cells:
                self.update_cell_visual(cell_key)
        
        return Task.cont
    def delayed_audio_start(self, task):
        """Wait a frame before starting audio to ensure everything is initialized"""
        print("Starting audio system and initializing tunnel...")
        
        # Pre-warm a few layers to avoid initial creation spike
        self.pre_warm_tunnel(layers=5)
        
        # Now it's safe to create cells with audio
        self.initialize_tunnel()
        
        print("Audio system started - tunnel initialized with audio")
        print(f"Total cells: {len(self.cells)}")
        
        return task.done

    def pre_warm_tunnel(self, layers=5):
        """Pre-create some tunnel sections to avoid initial creation spikes"""
        half_size = self.grid_size // 2
        
        for layer in range(layers):
            layer_y = layer * self.layer_spacing
            slice_rotation = self.get_slice_rotation(layer_y)
            
            # Create fewer cells for pre-warming (lower density)
            for x in range(-half_size, half_size + 1):
                for z in range(-half_size, half_size + 1):
                    distance = math.sqrt(x*x + z*z)
                    if distance <= half_size and random.random() > 0.8:  # Lower density
                        cell_key = (x, z, layer_y)
                        # Use the background creation method
                        self.create_cell_background(x, z, layer_y, slice_rotation)
        
        print(f"Pre-warmed {layers} tunnel layers")
            
    def create_cell_background(self, x, z, y, slice_rotation):
        """Queue cell creation in background thread"""
        cell_key = (x, z, y)
        
        # Check if cell already exists or is being created
        if cell_key in self.cells or cell_key in self.pending_cells:
            return
        
        # Queue for background creation
        self.queue_cell_creation(cell_key, x, z, y, slice_rotation)
    def update_audio(self, task):
        """Update audio system every frame"""
        dt = globalClock.getDt()
        
        # Update the audio3d system
        self.audio3d.update(task)
        
        # Update camera velocity for Doppler effect
        if hasattr(self, 'camera_velocity'):
            self.audio3d.setCameraVelocity(self.camera_velocity)
        
        # Update drum speed based on camera velocity
        self.update_drum_speed()
        # Update sound velocities for moving letters
        self.audio3d.update_sound_velocities()
        
        return Task.cont
    def quit(self):
        # Stop background thread
        self.should_stop_creation = True
        self.cell_creation_queue.put(None)  # Signal to stop
        if self.creation_thread:
            self.creation_thread.join(timeout=6.0)
        
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