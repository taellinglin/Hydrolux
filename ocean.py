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
    sync-video false
""")


class AudioEmitter:
    """Audio emitter attached to each letter that plays sounds at its position"""
    def __init__(self, audio3d, base_freq, scale_frequencies, node, char, index):
        self.audio3d = audio3d
        self.base_freq = base_freq
        self.scale_frequencies = scale_frequencies
        self.node = node
        self.char = char
        self.index = index
        
        # Audio properties
        self.sound_cooldown = 0.0
        self.last_played = 0.0
        self.base_volume = random.uniform(0.1, 1)
        self.pitch_variation = random.uniform(0.0, 0.0)
        
        # Character to note mapping
        self.char_to_note = {
            'a': 0, 'b': 1, 'c': 2, 'd': 3, 'e': 4, 'f': 5, 'g': 6,
            'h': 7, 'i': 8, 'j': 9, 'k': 10, 'l': 11, 'm': 12,
            'n': 13, 'o': 14, 'p': 15, 'q': 16, 'r': 17, 's': 18,
            't': 19, 'u': 20, 'v': 21, 'w': 22, 'x': 23, 'y': 24, 'z': 25
        }
        
        # Get note for this character
        self.note_index = self.char_to_note.get(char, 0) % len(self.scale_frequencies)
        self.base_pitch = self.scale_frequencies[self.note_index] / self.base_freq
        
    def update(self, current_time, velocity, trigger_distance, camera_pos):
        """Update audio emitter and trigger sounds based on distance"""
        # Calculate distance to camera
        emitter_pos = self.node.getPos()
        distance = (emitter_pos - camera_pos).length()
        
        # Trigger sound based on distance and cooldown
        if (distance < trigger_distance and 
            current_time - self.last_played > self.sound_cooldown):
            self.play_sound(velocity)
            self.last_played = current_time
            
        # Continuous sound that changes with distance
        self.update_continuous_sound(distance)
    
    def play_sound(self, velocity):
        """Play a sound at the emitter's position"""
        try:
            # Add some random variation to pitch
            pitch_variation = random.uniform(0.9, 1.1)
            pitch = self.base_pitch * pitch_variation * self.pitch_variation
            
            # Volume based on base volume with slight variation
            volume = self.base_volume * random.uniform(0.8, 1.2)
            
            # Play the sound at the emitter's position with its velocity
            sound_id = f"{self.char}_{self.index}"
            self.audio3d.playSfx(self.char, self.node, True, random.choice(self.scale_frequencies)/(self.base_freq), volume, velocity)
            
        except Exception as e:
            print(f"Error playing sound for emitter {self.index}: {e}")
    
    def update_continuous_sound(self, distance):
        """Update continuous ambient sound based on distance"""
        # This could be used for continuous tones that change with proximity
        pass


class OceanOfLetters(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
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
        # Ocean parameters
        self.ocean_size = 64
        self.num_letters = 64  # Good number for performance with audio
        self.letter_swim_speed = 10.0
        
        # Audio parameters
        self.base_freq = 110.0

        self.audio_trigger_distance = 25.0  # Distance to trigger sounds
        
        # Flight control parameters
        self.flight_speed = 25.0
        self.max_speed = 40.0
        
        # Camera state
        self.camera_velocity = Vec3(0, 0, 0)
        
        # Flight control state
        self.move_forward = False
        self.move_backward = False
        self.move_left = False
        self.move_right = False
        self.move_up = False
        self.move_down = False
        self.boost = False
        
        # Mouse look
        self.mouse_look = True
        self.last_mouse_pos = None
        
        # Visual parameters
        self.flicker_time = 0.0
        
        # Colors
        self.red_color = Vec4(1.0, 0.2, 0.1, 1.0)
        self.blue_color = Vec4(0.1, 0.3, 1.0, 1.0)
        self.pink_color = Vec4(1.0, 0.4, 0.6, 1.0)
        self.cyan_color = Vec4(0.2, 0.8, 1.0, 1.0)
        
        # Setup fog
        fog = Fog("SceneFog")
        fog.setColor(0.0, 0.0, 0.0)
        fog.setLinearRange(10, 200)
        self.render.setFog(fog)
        
        # Set background
        self.setBackgroundColor(0.0, 0.0, 0.0, 1)
        
        # Storage for particles and audio emitters
        self.particles = []
        self.particle_nodes = []
        self.audio_emitters = []  # NEW: Store audio emitters
        
        # Setup
        self.setup_emissive_rendering()
        self.load_bam_meshes()
        self.setup_camera()
        
        # Motion blur
        self.mb = MotionBlur()
        
        # Audio system
        self.audio3d = Audio3d(self.sfxManagerList, self.camera)
        self.audio3d.setAudioRange(60.0)
        self.audio3d.audio3d.setDopplerFactor(100.0)  # Higher for more dramatic effect
        #self.setup_drum_loop()
        
        # Setup controls
        self.setup_controls()
        
        # Initialize particles WITH audio emitters
        self.initialize_particles()
        
        # Start tasks
        self.taskMgr.add(self.update_particles, "update_particles")
        self.taskMgr.add(self.update_camera, "update_camera")
        self.taskMgr.add(self.update_audio, "update_audio")
        
        # Simple exit control
        self.accept('escape', self.quit)
        
        print("Ocean of Letters with Audio Emitters Initialized!")
        print(f"Letters: {self.num_letters}")
        print("Each letter has its own audio emitter that plays sounds at its position!")
        print("Controls: WASD + Mouse to fly, Shift to boost")
        
    def initialize_particles(self):
        """Initialize all particles with random properties and audio emitters"""
        available_chars = list(self.char_meshes.keys())
        if not available_chars:
            available_chars = ['a']  # Fallback
            
        for i in range(self.num_letters):
            # Create particle data
            char = random.choice(available_chars)
            particle = {
                'position': [
                    random.uniform(-self.ocean_size, self.ocean_size),
                    random.uniform(-self.ocean_size, self.ocean_size),
                    random.uniform(-self.ocean_size/3, self.ocean_size/3)
                ],
                'velocity': [
                    random.uniform(-1, 1) * self.letter_swim_speed,
                    random.uniform(-1, 1) * self.letter_swim_speed,
                    random.uniform(-0.3, 0.3) * self.letter_swim_speed
                ],
                'color_type': random.choice([0, 1, 0, 1, 2, 3]),
                'scale': random.uniform(0.4, 20),  # 5x larger: 0.08-0.15 -> 0.4-0.75
                'rotation': random.uniform(0, 360),
                'rotation_speed': random.uniform(-2.0, 2.0),
                'brightness': random.uniform(0.8, 1.6),
                'flicker_speed': random.uniform(1.0, 4.0),
                'flicker_phase': random.uniform(0, 2 * math.pi),
                'twinkle_speed': random.uniform(0.5, 2.0),
                'twinkle_phase': random.uniform(0, 2 * math.pi),
                'pulse_speed': random.uniform(0.3, 1.5),
                'pulse_phase': random.uniform(0, 2 * math.pi),
                'char': char
            }
            
            self.particles.append(particle)
            
            # Create visual node
            node = self.create_particle_node(i, particle)
            
            # NEW: Create audio emitter for this particle
            if node:
                emitter = AudioEmitter(
                    self.audio3d, 
                    self.base_freq, 
                    self.scale_frequencies,
                    node,
                    char,
                    i
                )
                self.audio_emitters.append(emitter)
            else:
                self.audio_emitters.append(None)
        
        print(f"Created {len(self.particles)} particles with {len(self.audio_emitters)} audio emitters")
    
    def create_particle_node(self, index, particle):
        """Create a visual node for a particle"""
        char = particle['char']
        if char not in self.char_meshes:
            char = list(self.char_meshes.keys())[0] if self.char_meshes else 'a'
        
        try:
            # Create the mesh node
            node = self.char_meshes[char].copyTo(self.render)
            node.setPos(*particle['position'])
            node.setScale(particle['scale'])
            node.setR(particle['rotation'])
            
            # Set initial color
            color = self.get_color_by_type(particle['color_type'])
            node.setColor(color)
            
            # Setup material
            material = Material()
            material.setShininess(1.0)
            material.setEmission(color)
            material.setLocal(True)
            node.setMaterial(material, 1)
            node.setLightOff()
            node.setTwoSided(True)
            
            self.particle_nodes.append(node)
            return node
            
        except Exception as e:
            print(f"Error creating particle node {index}: {e}")
            self.particle_nodes.append(None)
            return None
    
    def get_color_by_type(self, color_type):
        """Get color based on type"""
        colors = [self.red_color, self.blue_color, self.pink_color, self.cyan_color]
        return colors[color_type % len(colors)]
    
    def update_particles(self, task):
        """Update all particles and their audio emitters"""
        dt = ClockObject.getGlobalClock().getDt()
        self.flicker_time += dt
        
        camera_pos = self.camera.getPos()
        current_time = globalClock.getFrameTime()
        
        for i, (particle, node, emitter) in enumerate(zip(
            self.particles, self.particle_nodes, self.audio_emitters)):
            
            if node is None or node.is_empty():
                continue
            
            # Update position
            particle['position'][0] += particle['velocity'][0] * dt
            particle['position'][1] += particle['velocity'][1] * dt
            particle['position'][2] += particle['velocity'][2] * dt
            
            # Star Fox-style looping boundaries
            # X-axis looping (left-right)
            if particle['position'][0] > self.ocean_size:
                particle['position'][0] = -self.ocean_size
            elif particle['position'][0] < -self.ocean_size:
                particle['position'][0] = self.ocean_size
                
            # Y-axis looping (forward-backward)  
            if particle['position'][1] > self.ocean_size:
                particle['position'][1] = -self.ocean_size
            elif particle['position'][1] < -self.ocean_size:
                particle['position'][1] = self.ocean_size
                
            # Z-axis looping (up-down) - using ocean_size/3 as vertical bounds
            if particle['position'][2] > self.ocean_size/3:
                particle['position'][2] = -self.ocean_size/3
            elif particle['position'][2] < -self.ocean_size/3:
                particle['position'][2] = self.ocean_size/3
            
            # Update rotation
            particle['rotation'] += particle['rotation_speed'] * dt
            
            # Random velocity variation
            if random.random() < 0.02:
                particle['velocity'][0] += random.uniform(-1, 1) * 3
                particle['velocity'][1] += random.uniform(-1, 1) * 3
                particle['velocity'][2] += random.uniform(-0.3, 0.3) * 3
                
                # Normalize to maintain speed
                speed = math.sqrt(particle['velocity'][0]**2 + particle['velocity'][1]**2 + particle['velocity'][2]**2)
                if speed > 0:
                    factor = self.letter_swim_speed / speed
                    particle['velocity'][0] *= factor
                    particle['velocity'][1] *= factor
                    particle['velocity'][2] *= factor
            
            # Update visual properties
            self.update_particle_visual(i, particle, node)
            
            # NEW: Update audio emitter
            if emitter:
                velocity_vec = Vec3(*particle['velocity'])
                emitter.update(current_time, velocity_vec, self.audio_trigger_distance, camera_pos)
        
        return Task.cont
    
    def update_particle_visual(self, index, particle, node):
        """Update particle visual appearance"""
        # Calculate dynamic brightness
        flicker = math.sin(self.flicker_time * particle['flicker_speed'] + particle['flicker_phase']) * 0.3 + 1.0
        pulse = math.sin(self.flicker_time * particle['pulse_speed'] + particle['pulse_phase']) * 0.2 + 1.0
        twinkle = math.sin(self.flicker_time * particle['twinkle_speed'] + particle['twinkle_phase']) * 0.4 + 1.0
        
        brightness = particle['brightness'] * flicker * pulse * twinkle
        brightness = max(0.5, min(2.0, brightness))
        
        # Update position and rotation
        node.setPos(*particle['position'])
        node.setR(particle['rotation'])
        
        # Update scale with brightness
        scale = particle['scale'] * (0.8 + 0.4 * (brightness - 0.5) / 1.5)
        node.setScale(scale)
        
        # Update color with brightness
        base_color = self.get_color_by_type(particle['color_type'])
        color = Vec4(
            min(1.0, base_color.x * brightness),
            min(1.0, base_color.y * brightness),
            min(1.0, base_color.z * brightness),
            1.0
        )
        node.setColor(color)
        
        # Update material
        material = Material()
        material.setShininess(0.8)
        material.setEmission(color)
        material.setLocal(True)
        node.setMaterial(material, 1)
        
        # Billboarding - make particle face camera
        node.lookAt(self.camera)
    
    def setup_controls(self):
        """Setup keyboard and mouse controls"""
        # Movement keys
        self.accept('w', self.set_move_forward, [True])
        self.accept('w-up', self.set_move_forward, [False])
        self.accept('s', self.set_move_backward, [True])
        self.accept('s-up', self.set_move_backward, [False])
        self.accept('a', self.set_move_left, [True])
        self.accept('a-up', self.set_move_left, [False])
        self.accept('d', self.set_move_right, [True])
        self.accept('d-up', self.set_move_right, [False])
        self.accept('q', self.set_move_up, [True])
        self.accept('q-up', self.set_move_up, [False])
        self.accept('e', self.set_move_down, [True])
        self.accept('e-up', self.set_move_down, [False])
        self.accept('shift', self.set_boost, [True])
        self.accept('shift-up', self.set_boost, [False])
        
        self.disableMouse()
        
    def set_move_forward(self, state):
        self.move_forward = state
    def set_move_backward(self, state):
        self.move_backward = state
    def set_move_left(self, state):
        self.move_left = state
    def set_move_right(self, state):
        self.move_right = state
    def set_move_up(self, state):
        self.move_up = state
    def set_move_down(self, state):
        self.move_down = state
    def set_boost(self, state):
        self.boost = state
        
    def setup_drum_loop(self):
        """Setup ambient drum loop"""
        try:
            self.drum_sound = self.loader.loadSfx('drum.wav')
            self.drum_sound.setLoop(True)
            self.drum_sound.setVolume(0.02)  # Lower volume to hear the letters
            self.audio3d.audio3d.attachSoundToObject(self.drum_sound, self.camera)
            self.drum_sound.setPlayRate(1.0)
            self.drum_sound.play()
            print("Drum loop started")
        except Exception as e:
            print(f"Error setting up drum loop: {e}")

    def update_drum_speed(self):
        """Update drum speed based on camera velocity"""
        if hasattr(self, 'drum_sound') and self.drum_sound:
            camera_speed = self.camera_velocity.length()
            min_speed, max_speed = 0.2, self.max_speed
            min_rate, max_rate = 0.3, 2.0
            
            normalized_speed = (camera_speed - min_speed) / (max_speed - min_speed)
            normalized_speed = max(0.0, min(1.0, normalized_speed))
            
            play_rate = min_rate + (max_rate - min_rate) * normalized_speed
            current_rate = self.drum_sound.getPlayRate()
            smoothed_rate = current_rate * 0.9 + play_rate * 0.1
            self.drum_sound.setPlayRate(smoothed_rate)
        
    def setup_emissive_rendering(self):
        """Setup emissive rendering"""
        self.render.clearLight()
        self.render.setLightOff()
        
        # Add some ambient light so we can see the letters
        ambient_light = AmbientLight('ambient')
        ambient_light.setColor((0.05, 0.05, 0.08, 1))
        ambient_node = self.render.attachNewNode(ambient_light)
        self.render.setLight(ambient_node)
    
    def load_bam_meshes(self):
        """Load character meshes"""
        self.char_meshes = {}
        bam_dir = "./bam"
        
        # Try to load characters
        chars_to_load = list(string.ascii_lowercase)  # Try all letters
        
        for char in chars_to_load:
            bam_path = os.path.join(bam_dir, f"{char}.bam")
            if os.path.exists(bam_path):
                try:
                    model = self.loader.loadModel(bam_path)
                    if model:
                        model.setLightOff()
                        model.setTwoSided(True)
                        # Scale up the loaded models by 5x
                        model.setScale(2.0)
                        self.char_meshes[char] = model
                except Exception as e:
                    self.create_fallback_mesh(char)
            else:
                self.create_fallback_mesh(char)
        
        # If no meshes loaded, create fallbacks
        if not self.char_meshes:
            for char in ['a', 'b', 'c']:
                self.create_fallback_mesh(char)
        
        print(f"Loaded {len(self.char_meshes)} character meshes")
    
    def create_fallback_mesh(self, char):
        """Create simple quad mesh - 5x larger"""
        try:
            format = GeomVertexFormat.getV3n3c4()
            vdata = GeomVertexData('fallback', format, Geom.UHStatic)
            
            vertex = GeomVertexWriter(vdata, 'vertex')
            normal = GeomVertexWriter(vdata, 'normal')
            color = GeomVertexWriter(vdata, 'color')
            
            size = 1.0  # 5x larger: 0.2 -> 1.0
            vertices = [
                (-size, 0, -size), (size, 0, -size), 
                (size, 0, size), (-size, 0, size)
            ]
            
            for v in vertices:
                vertex.addData3f(v[0], v[1], v[2])
                normal.addData3f(0, 1, 0)
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
            material.setEmission((1, 1, 1, 1))
            material.setShininess(1.0)
            mesh_node.setMaterial(material, 1)
            mesh_node.setLightOff()
            mesh_node.setTwoSided(True)
            
            self.char_meshes[char] = mesh_node
            
        except Exception as e:
            print(f"Error creating fallback mesh: {e}")
    
    def setup_camera(self):
        """Setup camera for flight view"""
        self.camLens.setFov(135)
        self.camLens.setNear(0.001)
        self.camLens.setFar(10000)
        
        # Start in a position where we should see particles
        #self.camera.setPos(0, -40, 15)
        #self.camera.setH(90)
        #self.camera.setP(-5)
        
        print(f"Camera position: {self.camera.getPos()}")
    
    def update_camera(self, task):
        """Update camera movement"""
        dt = ClockObject.getGlobalClock().getDt()
        
        self.camera_prev_pos = self.camera.getPos()
        
        # Flight controls
        current_speed = self.flight_speed * (2.0 if self.boost else 1.0)
        
        move_vector = Vec3(0, 0, 0)
        
        if self.move_forward:
            move_vector += self.camera.getQuat().getForward()
        if self.move_backward:
            move_vector -= self.camera.getQuat().getForward()
        if self.move_left:
            move_vector -= self.camera.getQuat().getRight()
        if self.move_right:
            move_vector += self.camera.getQuat().getRight()
        if self.move_up:
            move_vector += Vec3(0, 0, 1)
        if self.move_down:
            move_vector -= Vec3(0, 0, 1)
        
        if move_vector.length() > 0:
            move_vector.normalize()
        
        # Apply movement
        target_velocity = move_vector * current_speed
        self.camera_velocity = self.camera_velocity * 0.8 + target_velocity * 0.2
        
        # Limit speed
        current_speed_mag = self.camera_velocity.length()
        if current_speed_mag > self.max_speed:
            self.camera_velocity = self.camera_velocity * (self.max_speed / current_speed_mag)
        
        # Move camera
        new_pos = self.camera.getPos() + self.camera_velocity * dt
        self.camera.setPos(new_pos)
        
        # Mouse look
        if self.mouse_look and self.mouseWatcherNode.hasMouse():
            mouse_pos = self.mouseWatcherNode.getMouse()
            if self.last_mouse_pos:
                delta = mouse_pos - self.last_mouse_pos
                self.camera.setH(self.camera.getH() - delta.x * 100)
                self.camera.setP(self.camera.getP() + delta.y * 100)
                self.camera.setP(max(-89, min(89, self.camera.getP())))
            self.last_mouse_pos = mouse_pos
        else:
            self.last_mouse_pos = None
        
        # Update velocity for audio
        current_pos = self.camera.getPos()
        self.camera_velocity = (current_pos - self.camera_prev_pos) / dt
        
        return Task.cont
    
    def update_audio(self, task):
        """Update audio system"""
        dt = globalClock.getDt()
        
        self.audio3d.update(task)
        
        if hasattr(self, 'camera_velocity'):
            self.audio3d.setCameraVelocity(self.camera_velocity)
        
        #self.update_drum_speed()
        self.audio3d.update_sound_velocities()
        
        return Task.cont
        
    def quit(self):
        if hasattr(self, 'audio3d'):
            self.audio3d.stopLoopingAudio()
        if hasattr(self, 'mb'):
            self.mb.cleanup()
        self.destroy()
        sys.exit(0)

if __name__ == "__main__":
    app = OceanOfLetters()
    app.run()