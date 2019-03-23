# Battleship client


import socket
import selectors
import types
import sys
import signal
import fcntl
import os

from functools import partial
from time import sleep

import models

import kivy
kivy.require('1.10.1')
from kivy.app import App
from kivy.properties import NumericProperty, ListProperty, ObjectProperty, StringProperty
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.widget import Widget


def send_message(socket, input):

	socket.send(input.encode())
	# msgType = input[:4]

	# if msgType == "JOIN":
		# players = input("Number of players:")


	# elif msgType == "NAME":


	# elif msgType == "SETB":


	# elif msgType == "SHOT":


	# elif msgType == "QUIT":



class FbBoard(BoxLayout):
	pass



class ConnectScreen(Screen):
	address = StringProperty("localhost")
	port = StringProperty("2136")
	manager = ObjectProperty(None)

	def __init__(self, **kwargs):
		super(ConnectScreen, self).__init__(**kwargs)
		self.fboatApp = App.get_running_app()

	def create_connection(self, *args):
		self.fboatApp.client = self.fboatApp.start_connection(self.address, int(self.port))
		self.manager.to_join_scr()
		Clock.schedule_interval(self.fboatApp.service_connection, .5)


class PlacementScreen(Screen):
	pass



class JoinScreen(Screen):
	opps = NumericProperty()
	join_button_1 = ObjectProperty(None)
	join_button_2 = ObjectProperty(None)
	join_button_3 = ObjectProperty(None)
	join_button_4 = ObjectProperty(None)
	wait_text = ObjectProperty(None)
	wait_player = NumericProperty(0)
	# client = ObjectProperty(None)

	def __init__(self, **kwargs):
		super(JoinScreen, self).__init__(**kwargs)
		self.fboatApp = App.get_running_app()
		# self.client = self.fboatApp.client

	def send_join_msg(self, opps):
		self.fboatApp.client.send_join_msg(opps)
		self.join_button_1.disabled = True
		self.join_button_2.disabled = True
		self.join_button_3.disabled = True
		self.join_button_4.disabled = True
		self.wait_text.color = self.fboatApp.color_dark_gray + [1]
		# self.fboatApp.client.bind(player_count = self.on_wait_player)

	def set_wait_text(self, have, want):
		self.wait_text.text = "Your game currently has {0} of {1} players. Please wait...".format(have, want)

	def on_wait_player(self):
		self.wait_text(self.fboatApp.client.player_count, self.fboatApp.client.player_goal)


class Manager(ScreenManager):
	def __init__(self, **kwargs):
		super(Manager, self).__init__(**kwargs)
		self.fboatApp = App.get_running_app()

	def to_conn_scr(self, *args):
		self.current = "connect_scr"

	def to_join_scr(self, *args):
		self.current = "join_scr"

	def to_placement_scr(self, *args):
		self.current = "placement_scr"



class FboatApp(App):

	# Colors for Kivy Lang File
	color_main = ListProperty([0.13671875, 0.53515625, 0.93359375])
	color_accent_1 = ListProperty([1.0, 0.8313725490196079, 0.28627450980392155])
	color_accent_2 = ListProperty([1.0, 0.6745098039215687, 0.5176470588235295])
	color_white = ListProperty([1, 1, 1])
	color_dark_gray = ListProperty([0.3254901960784314, 0.41568627450980394, 0.5098039215686274])
	color_light_gray = ListProperty([0.87109375, 0.90625, 0.921875])
	color_black = ListProperty([0, 0, 0])

	client = ObjectProperty(None)


	def __init__(self, **kwargs):
		super(FboatApp, self).__init__(**kwargs)
		self.sel = selectors.DefaultSelector()


	def service_connection(self, *args):
		events = self.sel.select(timeout=0)
		for key, mask in events:
			if mask & selectors.EVENT_READ:
				self.process_server_msg(key)


	def start_connection(self, host, port):

		# Connection to server
		addr = (host, port)
		print('starting connection to', addr)
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.setblocking(False)
		sock.connect_ex(addr)

		# Create Client datatype
		events = selectors.EVENT_READ | selectors.EVENT_WRITE
		myHost, myPort = sock.getsockname()
		data = models.Client(sock, myPort)

		# Add socket to selectors
		self.sel.register(sock, events, data=data)

		return data


	def process_server_msg(self, key):
		conn = key.fileobj
		client = key.data

		msg = conn.recv(4).decode()
		print("msg:" + msg)

		if msg == "GAME":
			client.parse_game_msg()
			return

		gameId = conn.recv(3).decode()

		# Check for correct game number
		if client.get_game_id() != gameId:
			print("This is the game: {}".format(gameId))
			# IGNORE MESSAGE, ERROR HAS OCCURED
			wrongMsg = conn.recv(1024).decode()
			print("THE WRONG GAME NUMBER WAS SENT TO {}, YOU HAVE SOME WORK TO DO".format(client.get_port()))
			print("Wrong Message: {}".format(wrongMsg))
			return None

		if msg == "WAIT":
			have, want = client.parse_wait_msg()
			self.root.ids.join_scr.set_wait_text(have, want)

		elif msg == "PLAY":
			client.parse_play_msg()

		elif msg == "SAIL":
			client.parse_sail_msg()


	def on_stop(self):
		map = self.sel.get_map()
		keys = list(map.keys())
		for conn in keys:
			socket = self.sel.get_key(conn).fileobj
			socket.close()
			self.sel.unregister(conn)
		self.sel.close()


if __name__ == '__main__':
	FboatApp().run()
