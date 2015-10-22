# TODO1: need to process ctrl+k and ctrl+d
# TODO2: delete previous chars lead to mis-colored

import sublime, sublime_plugin
import os
import threading
import time
import re
import codecs

plugin_name = "Color Tail"
setting_name = "ColorTail.sublime-settings"


pattern_char = re.compile(r'\S')

pre_colors = [
	"FF0000", #red
	"DC143C", #crimson
	"FF4500", #orangered
	"FF8C00", #darkorange
	"FFA500", #orange
	"FFFF00", #yellow
	"ADFF2F", #greenyellow
	"98FB98", #palegreen
	"9ACD32", #yellowgreen
    "7FFFD4", #aquamarine
]

colorViews = {}
gen_color_id = 1

def GetColor(i):
	col_new = pre_colors[i]
	return "mcol_"+col_new+"FF"

class ColorTailCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		setting = sublime.load_settings(setting_name)
		enable = setting.get("enabled")
		setting.set("enabled", not enable)
		return

class ColorThread(threading.Thread):
	def __init__(self, region, color_view):
		print("ColorThread init")
		threading.Thread.__init__(self)
		self.region = region
		self.text = color_view.view.substr(self.region)
		self.view = color_view.view
#		self.style = sublime.DRAW_NO_FILL|sublime.DRAW_NO_OUTLINE|sublime.DRAW_SOLID_UNDERLINE
		self.style = sublime.DRAW_NO_OUTLINE
		global gen_color_id
		self.id = gen_color_id
		gen_color_id += 1

		self.color_view = color_view
		color_view.color_thread_dict[self.id] = self
		self.need_destory = False

	def run(self):
		self.change_color(0)

	def change_color(self, i):
		if self.need_destory:
			return
		if i >= 10:
			self.destory()
			return
		self.view.add_regions(str(self.id)+"Color", [self.region], GetColor(i), "cross", self.style)
		time.sleep(.1)
		self.change_color(i+1)

	def destory(self):
		self.need_destory = True
		self.view.erase_regions(str(self.id)+"Color")
		del(self.color_view.color_thread_dict[self.id])
		return

	def on_delete_region(self, pos):
		if self.region.begin() == pos:
			self.destory()
		elif self.text != self.view.substr(self.region):
			self.destory()
		return

class ColorTailView:
	def __init__(self, view):
		self.view = view
		self.whole_size = 0
		self.color_thread_dict = {}

	def on_activated(self):
		self.whole_size = self.view.size()
		self.CreateColorScheme()		
		return

	def on_deactivated(self):
		keys = {}
		for k in self.color_thread_dict.keys():
			keys[k] = 0
		for k in keys:
			self.color_thread_dict[k].destory()
		self.color_thread_dict.clear()		
		return

	def on_modified(self):		
		view = self.view
		new_size = view.size()
#		print("new:"+str(new_size)+" old:"+str(self.whole_size))
		if new_size > self.whole_size:
			letter = sublime.Region(view.sel()[0].a-1, view.sel()[0].b)
#			print("letter:"+view.substr(letter))
			match = pattern_char.match(view.substr(letter))
			if match:
				setting = sublime.load_settings(setting_name)
				enable = setting.get("enabled")
				if enable:
					t = ColorThread(letter, self)
					t.start()

		self.whole_size = new_size
		return

	def delete_regions(self, from_pos, to_pos):
		for i in range(from_pos, to_pos):
			keys = {}
			for k in self.color_thread_dict.keys():
				keys[k] = 0
			for k in keys:
				self.color_thread_dict[k].on_delete_region(i)
		return

	def CreateColorScheme(self):
		# check prevous color scheme if contains color scope
		# cs = view.settings().get("color_scheme")
		# print("cs:"+cs)
		# data = sublime.load_resource(cs)
		# n = data.find(pre_colors[2])
		# if n < 0:
		# 	return

		# create color tail path
		path = sublime.packages_path()+"/User/"+plugin_name+"/"
		if not os.path.exists(path):
			os.mkdir(path)
		#print("path:"+path)
		# load now used color_scheme
		src_cs = self.view.settings().get("color_scheme")
		base_name = os.path.basename(src_cs)
		print("src_cs:"+src_cs)
		#print("name:"+base_name)		

		# create color tail scheme
		if not os.path.isfile(path+base_name):
			data = sublime.load_resource(src_cs)
			n = data.find("<array>") + len("<array>")

			#print("tail: write file:"+path+base_name)
			with codecs.open(path+base_name, "w", "utf-8") as f:
				f.write(data[:n])
				f.write(color_scopes)
				f.write(data[n:])

		new_cs = "Packages/User/"+plugin_name+"/"+base_name
		#print("new_cs:"+new_cs)
		# set color tail scheme
		if new_cs != src_cs:
			self.view.settings().set("color_scheme", new_cs)

class ColorTailListener(sublime_plugin.EventListener):

	def __init__(self):
		self.lastCmd = ""
		self.lastArgs = {}
		for wnd in sublime.windows():
			for v in wnd.views():
				colorViews[v.id()] = ColorTailView(v)				
		return

	def on_new(self, view):
		colorViews[view.id()] = ColorTailView(view)
		return
 
	def on_load(self, view):
		colorViews[view.id()] = ColorTailView(view)
		return

	def on_clone(self, view):
		colorViews[view.id()] = ColorTailView(view)
		return		

	def on_close(self, view):
		del(colorViews[view.id()])
		return

	def on_activated(self, view):
		if colorViews.get(view.id(), False):
			colorViews[view.id()].on_activated()
		return

	def on_deactivated(self, view):
		if colorViews.get(view.id(), False):
			colorViews[view.id()].on_deactivated()
		return

	def on_pre_save(self, view):
		return

	def on_post_save(self, view):
		return 

	def on_modified(self, view):
		if self.lastCmd == "undo" or self.lastCmd == "redo":
			""
		# TODO: this codes are not a good work, so comment these
		# elif self.lastCmd == "left_delete" or self.lastCmd == "delete_word":
		# 	now = view.sel()[0].begin()
		# 	pre = self.lastArgs["cursor_pos"]
		# 	print("from-to:"+str(now)+"-"+str(pre))
		# 	colorViews[view.id()].delete_regions(now, pre)
		elif colorViews.get(view.id(), False):
			colorViews[view.id()].on_modified()

		self.lastCmd = ""
		return

	def on_selection_modified_async(self, view):
		#print("hello")
		return

	def on_query_context(self, view, key, op, operand, match_all):
		return

	def on_text_command(self, window, name, args):
		self.lastCmd = name
		view = window
		# TODO: ctrl+k and ctrl+d
		if name == "left_delete" or name == "delete_word":
			self.lastArgs["cursor_pos"] = view.sel()[0].begin()
		#print("The text command name is: " + name)
		#print("The args are: " + str(args))
		return

color_scopes = '''

<dict>
<key>name</key>
<string>mon_color</string>
<key>scope</key>
<string>mcol_FF0000FF</string>
<key>settings</key>
<dict>
<key>background</key>
<string>#B3FFD9FF</string>
<key>foreground</key>
<string>#004C26FF</string>
<key>caret</key>
<string>#004C26FF</string>
</dict>
</dict>

<dict>
<key>name</key>
<string>mon_color</string>
<key>scope</key>
<string>mcol_DC143CFF</string>
<key>settings</key>
<dict>
<key>background</key>
<string>#DC143CFF</string>
<key>foreground</key>
<string>#460613FF</string>
<key>caret</key>
<string>#460613FF</string>
</dict>
</dict>

<dict>
<key>name</key>
<string>mon_color</string>
<key>scope</key>
<string>mcol_FF4500FF</string>
<key>settings</key>
<dict>
<key>background</key>
<string>#FF4500FF</string>
<key>foreground</key>
<string>#4C1400FF</string>
<key>caret</key>
<string>#4C1400FF</string>
</dict>
</dict>

<dict>
<key>name</key>
<string>mon_color</string>
<key>scope</key>
<string>mcol_FF8C00FF</string>
<key>settings</key>
<dict>
<key>background</key>
<string>#FF8C00FF</string>
<key>foreground</key>
<string>#4C2A00FF</string>
<key>caret</key>
<string>#4C2A00FF</string>
</dict>
</dict>

<dict>
<key>name</key>
<string>mon_color</string>
<key>scope</key>
<string>mcol_FFA500FF</string>
<key>settings</key>
<dict>
<key>background</key>
<string>#FFA500FF</string>
<key>foreground</key>
<string>#4C3100FF</string>
<key>caret</key>
<string>#4C3100FF</string>
</dict>
</dict>

<dict>
<key>name</key>
<string>mon_color</string>
<key>scope</key>
<string>mcol_FFFF00FF</string>
<key>settings</key>
<dict>
<key>background</key>
<string>#FFFF00FF</string>
<key>foreground</key>
<string>#4C4C00FF</string>
<key>caret</key>
<string>#4C4C00FF</string>
</dict>
</dict>

<dict>
<key>name</key>
<string>mon_color</string>
<key>scope</key>
<string>mcol_ADFF2FFF</string>
<key>settings</key>
<dict>
<key>background</key>
<string>#ADFF2FFF</string>
<key>foreground</key>
<string>#7DD000FF</string>
<key>caret</key>
<string>#7DD000FF</string>
</dict>
</dict>

<dict>
<key>name</key>
<string>mon_color</string>
<key>scope</key>
<string>mcol_98FB98FF</string>
<key>settings</key>
<dict>
<key>background</key>
<string>#98FB98FF</string>
<key>foreground</key>
<string>#046704FF</string>
<key>caret</key>
<string>#046704FF</string>
</dict>
</dict>

<dict>
<key>name</key>
<string>mon_color</string>
<key>scope</key>
<string>mcol_9ACD32FF</string>
<key>settings</key>
<dict>
<key>background</key>
<string>#9ACD32FF</string>
<key>foreground</key>
<string>#2E3D0EFF</string>
<key>caret</key>
<string>#2E3D0EFF</string>
</dict>
</dict>

<dict>
<key>name</key>
<string>mon_color</string>
<key>scope</key>
<string>mcol_7FFFD4FF</string>
<key>settings</key>
<dict>
<key>background</key>
<string>#7FFFD4FF</string>
<key>foreground</key>
<string>#008055FF</string>
<key>caret</key>
<string>#008055FF</string>
</dict>
</dict>

'''
