from direct.showbase import Audio3DManager
from random import choice, shuffle
from panda3d.core import Vec3
import random
class Audio3d():
    def __init__(self, sml, cam):
        self.audio3d = Audio3DManager.Audio3DManager(sml[0], cam)
        
        # Load multiple instances of each sound for layering
        self.sfx3d = {
            'a': [
                self.audio3d.loadSfx('tones/vowel_ - a.wav') for _ in range(8)
            ],
            'b': [
                self.audio3d.loadSfx('tones/consonant_ - b.wav') for _ in range(8)
            ],
            'c': [
                self.audio3d.loadSfx('tones/vowel_ - c.wav') for _ in range(8)
            ],
            'd': [
                self.audio3d.loadSfx('tones/consonant_ - d.wav') for _ in range(8)
            ],
            'e': [
                self.audio3d.loadSfx('tones/vowel_ - e.wav') for _ in range(8)
            ],
            'f': [
                self.audio3d.loadSfx('tones/consonant_ - f.wav') for _ in range(8)
            ],
            'g': [
                self.audio3d.loadSfx('tones/consonant_ - g.wav') for _ in range(8)
            ],
            'h': [
                self.audio3d.loadSfx('tones/consonant_ - h.wav') for _ in range(8)
            ],
            'i': [
                self.audio3d.loadSfx('tones/vowel_ - i.wav') for _ in range(8)
            ],
            'j': [
                self.audio3d.loadSfx('tones/consonant_ - j.wav') for _ in range(8)
            ],
            'k': [
                self.audio3d.loadSfx('tones/consonant_ - k.wav') for _ in range(8)
            ],
            'l': [
                self.audio3d.loadSfx('tones/vowel_ - l.wav') for _ in range(8)
            ],
            'm': [
                self.audio3d.loadSfx('tones/vowel_ - m.wav') for _ in range(8)
            ],
            'n': [
                self.audio3d.loadSfx('tones/vowel_ - n.wav') for _ in range(8)
            ],
            'o': [
                self.audio3d.loadSfx('tones/vowel_ - o.wav') for _ in range(8)
            ],
            'p': [
                self.audio3d.loadSfx('tones/consonant_ - p.wav') for _ in range(8)
            ],
            'q': [
                self.audio3d.loadSfx('tones/consonant_ - q.wav') for _ in range(8)
            ],
            'r': [
                self.audio3d.loadSfx('tones/vowel_ - r.wav') for _ in range(8)
            ],
            's': [
                self.audio3d.loadSfx('tones/vowel_ - s.wav') for _ in range(8)
            ],
            't': [
                self.audio3d.loadSfx('tones/consonant_ - t.wav') for _ in range(8)
            ],
            'u': [
                self.audio3d.loadSfx('tones/vowel_ - u.wav') for _ in range(8)
            ],
            'v': [
                self.audio3d.loadSfx('tones/consonant_ - v.wav') for _ in range(8)
            ],
            'w': [
                self.audio3d.loadSfx('tones/consonant_ - w.wav') for _ in range(8)
            ],
            'x': [
                self.audio3d.loadSfx('tones/consonant_ - x.wav') for _ in range(8)
            ],
            'y': [
                self.audio3d.loadSfx('tones/consonant_ - y.wav') for _ in range(8)
            ],
            'z': [
                self.audio3d.loadSfx('tones/vowel_ - z.wav') for _ in range(8)
            ],
        }
        
        # Track which sounds are currently in use
        self.available_sounds = {}
        for sfx_type, sounds_list in self.sfx3d.items():
            self.available_sounds[sfx_type] = sounds_list.copy()
        
        self.audio3d.setDistanceFactor(1)
        self.audio3d.setDopplerFactor(5.0)
        self.playing_loops = []
        self.audio_range = 50.0  # Increased range
        self.active_sounds = {}  # key: (obj, sound_type, sound_id)
        self.camera_node = cam
        self.camera_velocity = Vec3(0, 0, 0)
        print(f"Audio3D Manager initialized with {len(self.sfx3d)} sound types")
        print(f"Total sound instances: {sum(len(sounds) for sounds in self.sfx3d.values())}")
                
    def enter(self):
        base.task_mgr.add(self.update, 'update_audio')
        
    def setCameraVelocity(self, velocity):
        """Update the camera/listener velocity for Doppler effect"""
        self.camera_velocity = velocity
        # Panda3D should automatically use this for the listener
    def debug_sound(self, sound_key):
        """Debug sound properties"""
        if sound_key in self.active_sounds:
            sound_data = self.active_sounds[sound_key]
            sfx3d = sound_data['sound']
            print(f"Sound debug - Pitch: {sound_data['pitch']}, Actual rate: {sfx3d.getPlayRate()}, Volume: {sfx3d.getVolume()}")
    def playSfx(self, sfx=None, obj=None, loop=True, pitch=None, volume=None, obj_velocity=None):
        if sfx is None or obj is None:
            return
            
        # Check distance to camera - don't play distant sounds
        camera_pos = self.camera_node.getPos()
        obj_pos = obj.getPos()
        distance = (obj_pos - camera_pos).length()
        
        if distance > self.audio_range * 0.8:  # Don't play if too far
            return None
            
        if sfx in self.available_sounds and self.available_sounds[sfx]:
            sfx3d = self.available_sounds[sfx].pop(0)
            
            # Configure basic sound properties FIRST
            sfx3d.setLoop(loop)
            
            if volume is not None:
                sfx3d.setVolume(max(0.0, min(1.0, volume)))
            else:
                sfx3d.setVolume(0.5)
                
            if pitch is not None:
                sfx3d.setPlayRate(max(0.1, min(10.0, pitch)))
            
            # Configure 3D audio properties
            self.audio3d.attachSoundToObject(sfx3d, obj)
            self.audio3d.setSoundMinDistance(sfx3d, 0.5)
            self.audio3d.setSoundMaxDistance(sfx3d, self.audio_range)
            self.audio3d.setDropOffFactor(1.0)
            
            # USE ACTUAL VELOCITY for Doppler effect
            if obj_velocity is not None:
                self.audio3d.setSoundVelocity(sfx3d, obj_velocity)
            else:
                self.audio3d.setSoundVelocity(sfx3d, Vec3(0, 0, 0))
            
            # Create unique key for this sound instance
            sound_key = (id(obj), sfx, id(sfx3d))
            
            sound_data = {
                'sound': sfx3d,
                'object': obj,
                'type': sfx,
                'loop': loop,
                'pitch': pitch,
                'started': False
            }
            
            if loop:
                self.playing_loops.append(sfx3d)
            
            self.active_sounds[sound_key] = sound_data
            
            # Start the sound AFTER all properties are set
            sfx3d.play()
            sound_data['started'] = True
            
            return sound_key
            
        else:
            # Don't spam console - only log occasionally
            if random.random() < 0.01:
                print(f"No available {sfx} sounds")
            return None
    def update_sound_velocities(self):
        """Update velocities for all active sounds based on object movement"""
        for sound_key, sound_data in list(self.active_sounds.items()):
            obj = sound_data['object']
            # For now, we'll assume objects are stationary
            # In a more complex system, you'd track object velocities here
            pass
    def stopSfxDeferred(self, node):
        """Queue a node for deferred audio cleanup to spread workload"""
        if not hasattr(self, '_deferred_cleanup_queue'):
            self._deferred_cleanup_queue = []
        self._deferred_cleanup_queue.append(node)
    def stopSfx(self, node):
        """Stop all sounds associated with a specific node - optimized version"""
        node_id = id(node)
        keys_to_remove = []
        
        # Quick pre-check to avoid unnecessary work
        has_sounds = any(obj_id == node_id for obj_id, _, _ in self.active_sounds.keys())
        if not has_sounds:
            return
        
        # Batch process sounds for this node
        for sound_key, sound_data in list(self.active_sounds.items()):
            obj_id, sfx_type, sound_id = sound_key
            
            if obj_id == node_id:
                sound = sound_data['sound']
                
                # Stop the sound immediately
                if sound.status() == sound.PLAYING:
                    sound.stop()
                
                # Return to available pool
                if sfx_type in self.available_sounds:
                    self.available_sounds[sfx_type].append(sound)
                
                # Remove from playing loops
                if sound in self.playing_loops:
                    self.playing_loops.remove(sound)
                
                keys_to_remove.append(sound_key)
        
        # Batch remove from active sounds
        for key in keys_to_remove:
            del self.active_sounds[key]
    
    def update(self, task):
        # Update the audio system
        self.audio3d.update()
        # Process deferred cleanup (limited per frame)
        if hasattr(self, '_deferred_cleanup_queue') and self._deferred_cleanup_queue:
            max_audio_cleanup_per_frame = 16
            cleanup_count = 0
            
            while self._deferred_cleanup_queue and cleanup_count < max_audio_cleanup_per_frame:
                node = self._deferred_cleanup_queue.pop(0)
                self.stopSfx(node)
                cleanup_count += 1
        # Clean up finished non-looping sounds
        keys_to_remove = []
        for sound_key, sound_data in list(self.active_sounds.items()):
            if not sound_data['loop'] and sound_data['started']:
                sound = sound_data['sound']
                if sound.status() != sound.PLAYING:
                    # Return to available pool
                    sfx_type = sound_data['type']
                    if sfx_type in self.available_sounds:
                        self.available_sounds[sfx_type].append(sound)
                    keys_to_remove.append(sound_key)
        
        # Remove finished sounds
        for key in keys_to_remove:
            if key in self.active_sounds:
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
            
            # Find the sound type and return to available pool
            for sfx_type, sounds_list in self.sfx3d.items():
                if sound in sounds_list and sound not in self.available_sounds[sfx_type]:
                    self.available_sounds[sfx_type].append(sound)
        
        self.playing_loops.clear()
        
        # Also clear active_sounds
        for sound_data in list(self.active_sounds.values()):
            sfx_type = sound_data['type']
            sound = sound_data['sound']
            if sfx_type in self.available_sounds and sound not in self.available_sounds[sfx_type]:
                self.available_sounds[sfx_type].append(sound)
        
        self.active_sounds.clear()
        
    def getAvailableSoundCount(self):
        """Debug method to see how many sounds are available"""
        return {sfx_type: len(sounds) for sfx_type, sounds in self.available_sounds.items()}
    
    def debug_audio_status(self):
        """Print debug information about audio status"""
        total_available = sum(len(sounds) for sounds in self.available_sounds.values())
        total_active = len(self.active_sounds)
        
        print(f"Audio Status - Available: {total_available}, Active: {total_active}")
        
        # Show top 5 most used sound types
        usage = {}
        for key in self.active_sounds.keys():
            sfx_type = key[1]
            usage[sfx_type] = usage.get(sfx_type, 0) + 1
        
        for sfx_type, count in sorted(usage.items(), key=lambda x: x[1], reverse=True)[:5]:
            available = len(self.available_sounds.get(sfx_type, []))
            print(f"  {sfx_type}: Available={available}, Active={count}")