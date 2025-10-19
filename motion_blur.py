from panda3d.core import CardMaker


class MotionBlur():
    def __init__(self, cam=None):
        base.win.set_clear_color_active(False)
        self.cardmaker = CardMaker('background')
        self.cardmaker.set_frame(-1,1,-1,1)
        if hasattr(self, 'cam'):
            self.bg = cam.attach_new_node(self.cardmaker.generate())
        else:
            self.bg = base.cam.attach_new_node(self.cardmaker.generate())
        self.bg.set_y(2048)
        self.bg.set_transparency(True)
        self.bg.set_color((0,0,0,0.25))
        self.bg.set_scale(20000)
    def cleanup(self):
        self.cardmaker = None
        self.bg = None
        return