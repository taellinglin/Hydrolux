from direct.showbase import Audio3DManager
from random import choice, shuffle
from panda3d.core import Vec3

class Audio3d():
    def __init__(self, sml, cam):
        self.audio3d = Audio3DManager.Audio3DManager(sml[0], cam)
        self.sfx3d = {
            'circle': [
                self.audio3d.loadSfx('tones/Circle.wav')
            ],
            'square': [
                self.audio3d.loadSfx('tones/Square.wav')
            ],
            'triangle': [
                self.audio3d.loadSfx('tones/Triangle.wav')
            ],
        }
        self.audio3d.setDistanceFactor(100)
        self.audio3d.setDopplerFactor(30)
        self.playing_loops = []
        self.audio_range = 100.0  # Increased range
        self.active_sounds = {}
        self.camera_node = cam
        print(f"Audio3D Manager initialized with range: {self.audio_range}")
                
    def enter(self):
        base.task_mgr.add(self.update, 'update')
        
    def playSfx(self, sfx=None, obj=None, loop=True):
        if sfx is None or obj is None:
            return
            
        if self.sfx3d.get(sfx):
            list_copy = self.sfx3d.get(sfx)[:]
            shuffle(list_copy)
            sfx3d = list_copy.pop()
            
            print(f"Setting up {sfx} sound for object at {obj.getPos()}")
            
            sfx3d.setLoop(loop)
            sfx3d.setVolume(1.0)
            
            # Configure 3D audio properties
            self.audio3d.attachSoundToObject(sfx3d, obj)
            self.audio3d.setSoundMinDistance(sfx3d, 0.5)  # Increased min distance
            self.audio3d.setSoundMaxDistance(sfx3d, self.audio_range)
            self.audio3d.setDropOffFactor(5)  # Reduced dropoff
            self.audio3d.setSoundVelocityAuto(sfx3d)
            
            # DON'T start playing yet - wait for audio system to be ready
            # Just store the sound for now
            sound_data = {
                'sound': sfx3d,
                'object': obj,
                'type': sfx,
                'loop': loop,
                'started': False
            }
            
            if loop:
                self.playing_loops.append(sfx3d)
            
            self.active_sounds[obj] = sound_data
            
    def update(self, task):
        # Update the audio system
        self.audio3d.update()
        
        # Get listener position
        listener_pos = self.camera_node.getPos()
        
        # Start sounds that are within range and haven't been started yet
        for obj, sound_data in list(self.active_sounds.items()):
            if not sound_data['started']:
                obj_pos = obj.getPos()
                distance = (obj_pos - listener_pos).length()
                
                if distance <= self.audio_range:
                    print(f"Starting {sound_data['type']} sound at distance {distance}")
                    sound_data['sound'].play()
                    sound_data['started'] = True
    
    def setAudioRange(self, range):
        """Set the maximum distance for audio playback"""
        self.audio_range = range
        print(f"Audio range set to {range} units")
    
    def stopLoopingAudio(self):
        for sound in self.playing_loops:
            if sound.status() == sound.PLAYING:
                sound.stop()
        self.playing_loops.clear()
        self.active_sounds.clear()