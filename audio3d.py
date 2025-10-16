from direct.showbase import Audio3DManager
from random import choice, shuffle
from panda3d.core import Vec3

class Audio3d():
    def __init__(self, sml, cam):
        self.audio3d = Audio3DManager.Audio3DManager(sml[0], cam)
        
        # Load multiple instances of each sound for layering
        self.sfx3d = {
            'circle': [
                self.audio3d.loadSfx('tones/Circle.wav') for _ in range(10)  # 10 instances for layering
            ],
            'square': [
                self.audio3d.loadSfx('tones/Square.wav') for _ in range(10)
            ],
            'triangle': [
                self.audio3d.loadSfx('tones/Triangle.wav') for _ in range(10)
            ],
            'noise': [
                self.audio3d.loadSfx('tones/Noise.wav') for _ in range(10)
            ],
            'click': [
                self.audio3d.loadSfx('tones/Click.wav') for _ in range(10)
            ],
        }
        
        # Track which sounds are currently in use
        self.available_sounds = {
            'circle': self.sfx3d['circle'][:],
            'square': self.sfx3d['square'][:],
            'triangle': self.sfx3d['triangle'][:],
            'noise': self.sfx3d['noise'][:],
            'click': self.sfx3d['click'][:]
        }
        
        self.audio3d.setDistanceFactor(50)
        self.audio3d.setDopplerFactor(300)
        self.playing_loops = []
        self.audio_range = 10.0
        self.active_sounds = {}  # key: (obj, sound_type) to handle multiple same-type sounds on same object
        self.camera_node = cam
        print(f"Audio3D Manager initialized with range: {self.audio_range}")
                
    def enter(self):
        base.task_mgr.add(self.update, 'update_audio')
        
    def playSfx(self, sfx=None, obj=None, loop=True, pitch=None):
        if sfx is None or obj is None:
            return
            
        # Get an available sound instance
        if sfx in self.available_sounds and self.available_sounds[sfx]:
            sfx3d = self.available_sounds[sfx].pop()
            
            print(f"Setting up {sfx} sound for object at {obj.getPos()}")
            
            sfx3d.setLoop(loop)
            sfx3d.setVolume(1.0)  # Reduced volume for better layering
            sfx3d.setPlayRate(pitch)
            print(f"Playing Note: {pitch}")
            
            # Configure 3D audio properties
            self.audio3d.attachSoundToObject(sfx3d, obj)
            self.audio3d.setSoundMinDistance(sfx3d, 0.1)
            self.audio3d.setSoundMaxDistance(sfx3d, self.audio_range)
            self.audio3d.setDropOffFactor(2)
            self.audio3d.setSoundVelocityAuto(sfx3d)
            
            # Create unique key for this sound instance
            sound_key = (obj, sfx, id(sfx3d))
            
            sound_data = {
                'sound': sfx3d,
                'object': obj,
                'type': sfx,
                'loop': loop,
                'note': pitch,
                'started': False
            }
            
            if loop:
                self.playing_loops.append(sfx3d)
            
            self.active_sounds[sound_key] = sound_data
            
        else:
            print(f"No available {sfx} sounds for layering!")
            
    def stopSound(self, obj, sfx_type=None):
        """Stop specific sounds on an object"""
        keys_to_remove = []
        for key, sound_data in self.active_sounds.items():
            obj_ref, sfx_type_ref, sound_id = key
            if obj_ref == obj and (sfx_type is None or sfx_type == sfx_type_ref):
                if sound_data['sound'].status() == sound_data['sound'].PLAYING:
                    sound_data['sound'].stop()
                
                # Return sound to available pool
                if sfx_type_ref in self.available_sounds:
                    self.available_sounds[sfx_type_ref].append(sound_data['sound'])
                
                keys_to_remove.append(key)
                if sound_data['sound'] in self.playing_loops:
                    self.playing_loops.remove(sound_data['sound'])
        
        for key in keys_to_remove:
            del self.active_sounds[key]
    
    def update(self, task):
        # Update the audio system
        self.audio3d.update()
        
        # Get listener position
        listener_pos = self.camera_node.getPos()
        
        # Start sounds that are within range and haven't been started yet
        # Also clean up finished sounds
        keys_to_remove = []
        
        for sound_key, sound_data in list(self.active_sounds.items()):
            obj, sfx_type, sound_id = sound_key
            
            if not sound_data['started']:
                # Start sounds within range
                obj_pos = obj.getPos()
                distance = (obj_pos - listener_pos).length()
                
                if distance <= self.audio_range:
                    print(f"Starting {sound_data['type']} sound at distance {distance}")
                    sound_data['sound'].play()
                    sound_data['started'] = True
            else:
                # Check if sound has finished (for non-looping sounds)
                if not sound_data['loop'] and sound_data['sound'].status() != sound_data['sound'].PLAYING:
                    # Return sound to available pool
                    if sfx_type in self.available_sounds:
                        self.available_sounds[sfx_type].append(sound_data['sound'])
                    keys_to_remove.append(sound_key)
                    if sound_data['sound'] in self.playing_loops:
                        self.playing_loops.remove(sound_data['sound'])
        
        # Remove finished sounds
        for key in keys_to_remove:
            del self.active_sounds[key]
            
        return task.cont
    
    def setAudioRange(self, range):
        """Set the maximum distance for audio playback"""
        self.audio_range = range
        print(f"Audio range set to {range} units")
    
    def stopLoopingAudio(self):
        """Stop all looping sounds and return them to available pool"""
        for sound in self.playing_loops:
            if sound.status() == sound.PLAYING:
                sound.stop()
            
            # Return sounds to available pool
            for sfx_type, sounds_list in self.sfx3d.items():
                if sound in sounds_list and sound not in self.available_sounds[sfx_type]:
                    self.available_sounds[sfx_type].append(sound)
        
        self.playing_loops.clear()
        self.active_sounds.clear()
        
    def getAvailableSoundCount(self):
        """Debug method to see how many sounds are available"""
        return {sfx_type: len(sounds) for sfx_type, sounds in self.available_sounds.items()}