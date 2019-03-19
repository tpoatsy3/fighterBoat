"""
Ted Poatsy, March 2018

This is the python side of the kivy GUI interface

TODO: Add logic and tie in gameClient.py for logic
"""



import kivy

kivy.require('1.10.1')

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, Screen



class ConnectScreen(Screen):
	pass

class FbBoard(BoxLayout):
	pass

class PlacementScreen(Screen):
	pass

class JoinScreen(Screen):
	pass

class FboatApp(App):
	pass


if __name__ == '__main__':
    FboatApp().run()
