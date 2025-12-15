class SoundLibrary:
    def __init__(self):
        self.sounds = {}

        
        self.sounds["explosion"] = Sound("mp3")

    def play(self, sound_id):
        if sound_id in self.sounds:
            self.sounds[sound_id].play()
        else:
            print(f"Sound '{sound_id}' not found")
