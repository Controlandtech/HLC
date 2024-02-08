from flask import Flask, redirect, url_for, render_template, request
import socket, select, time, threading, pickle, vlc, os, random, yaml


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((socket.gethostname(), 1234))
s.listen(5)
s.settimeout(5)	
app = Flask(__name__)

#get configuration data
with open("server_conf.yml", "r") as f:
	config_data = yaml.safe_load(f)

#set server ip and port
server_ip = config_data['server_ip']
server_port = config_data['port']

#make some holders for data handling
servers = []
write_data = []
current_server = ""
clients_data = {}
client_cc_setting = {}
client_screen_mode = {}
channel_index = {}
channel_listings = []

#set vlc player attributes and set allowed files
accepted_exts = config_data['accepted_extentions']
play_order = [0, 1]
play_files = ["None", "None"]
fullscreen = config_data['fullscreen']
CC = config_data['CC']
play_location = ""
index = 0
media_play_command = 0


run = True
gui_run = False
send_data = False
player_running = False


def save_data(l1,l2,l3,l4,b1,b2):
	with open("data_state_server.txt", 'wb') as tmp:
		pickle.dump([l1,l2,l3,l4,b1,b2],tmp)
	print("Data Saved")

def player_handler():
	global play_order
	global play_files
	global play_location
	global index
	global media_play_command
	global player_running
	global fullscreen
	global CC
	media_player = vlc.MediaPlayer()
	media_player.set_fullscreen(fullscreen)
	while run:
		if not media_player.is_playing():
			if player_running:
				index +=1
			else:
				player_running = True
			if index >= len(play_files):
				index = 0
			print(media_player.is_playing())
			media = vlc.Media(os.path.join(play_location,play_files[play_order[index]]))
			media_player.set_media(media)
			media_player.set_fullscreen(fullscreen)
			if CC == False:
				media_player.video_set_spu(0)
			media_player.play()
			print(f"Subtitles Available: {media_player.video_get_spu_count()}")
			time.sleep(1)
		if media_play_command > 0:
			#skip forward
			if media_play_command == 1:
				media_player.stop()
				index +=1
				if index >= len(play_files):
					index = 0
				media = vlc.Media(os.path.join(play_location,play_files[play_order[index]]))
				media_player.set_media(media)
				media_player.set_fullscreen(fullscreen)
				if CC == False:
					media_player.video_set_spu(0)
				media_player.play()
				time.sleep(1)
				media_play_command = 0
			
			#skip backwards
			elif media_play_command == 2:
				media_player.stop()
				if index > 0:
					index -= 1
				media = vlc.Media(os.path.join(play_location,play_files[play_order[index]]))
				media_player.set_media(media)
				media_player.set_fullscreen(fullscreen)
				if CC == False:
					media_player.video_set_spu(0)
				media_player.play()
				time.sleep(1)
				media_play_command = 0


			#reload player (if their is new data)
			elif media_play_command == 3:
				media_player.stop()
				index = 0
				media = vlc.Media(os.path.join(play_location,play_files[play_order[index]]))
				media_player.set_media(media)
				media_player.set_fullscreen(fullscreen)
				if CC == False:
					media_player.video_set_spu(0)
				media_player.play()
				time.sleep(1)
				media_play_command = 0
	time.sleep(1)

def load_data():
	global play_order
	global play_files
	global play_location
	global index
	global player_running
	global media_play_command
	global fullscreen
	global CC
	with open("data_state_server.txt", 'rb') as data:
		tmp = pickle.load(data)
		play_order = tmp[0]
		play_files = tmp[1]
		play_location = tmp[2]
		index = tmp[3]
		fullscreen = tmp[4]
		CC = tmp[5]
	if not player_running:
		threading._start_new_thread(player_handler())
	else:
		media_play_command = 3

def server_video_play(location):
	global play_order
	global play_files
	global play_location
	global index
	global player_running
	global media_play_command
	if os.path.exists(location):
		files = []
		files = os.listdir(location)
		large_files = 0
		play_files = []
		play_order = []
		for f in files:
			names = os.path.splitext(location +"\\"+f) 
			if names[1].lower() in accepted_exts:
				play_files.append(f)
				large_files += 1
		if large_files > 0:
			play_order = random.sample(range(large_files), large_files)
			#print(f"Location Found! Total files and Total Large Files: {len(files)} {large_files}")
			#print(play_order, play_files)
			play_location = location
			print(play_order, play_files)
			if not player_running:
				print("i ran it")
				threading._start_new_thread(player_handler())
			else:
				media_play_command = 3
		else:
			play_order = [0, 1]
			play_files = ["None", "None"]
			print("Error No Files")
	else:
		print('directory not found')


def write_client(c,adr):
	global write_data
	global run
	global current_server
	global send_data
	global clients_data
	global servers
	my_address = adr[0]
	counter = 0
	refresh = False

	#start loop to handle channel servers
	while run:
		if counter >= 50:
			write_data = ["?"]
			counter = 0
			refresh = True
		else:
			counter +=1
		#only execute if server matches current server
		if len(write_data) > 0 and my_address == current_server or refresh:
			#send command or directory data to server and read back response
			try:
				c.sendall(pickle.dumps(write_data))
				msg = pickle.loads(c.recv(1024))
			except:
				break
			if msg:
				print(msg)
				clients_data[my_address] = msg
			write_data.clear()
			send_data = False
			refresh = False		
		elif send_data == True:
			print(f"failed client ip, current server and data was:\n{repr(my_address)} {repr(current_server)} {write_data}")
			send_data = False
			refresh = False
		time.sleep(0.1)

	del clients_data[my_address]
	servers.remove(my_address)
	c.close()




#Main start page
@app.route("/")
def home():
	global servers
	global server_ip
	global clients_data
	global play_files
	global play_order
	global index
	global servers
	global player_running
	if not player_running and os.path.exists("data_state_server.txt"):
		load_data()

	return render_template("index.html", servers=servers, server_ip=server_ip, len_server=len(servers), data=clients_data, server_side=[play_files[play_order[index]],play_files[play_order[index+1]]])

@app.route("/forward/", methods=["POST"])
def update_servers():
	global servers
	global server_ip
	global clients_data
	global play_files
	global play_order
	global index
	global channel_index
	try:
		conn, addr = s.accept()
		conn.send(b'hello')
		msg = pickle.loads(conn.recv(1024))
		print(msg)
		if msg:
			clients_data[addr[0]] = msg
		print(f"connected by {addr}")
		if addr not in servers:
			client_screen_mode[addr[0]] = ""
			client_cc_setting[addr[0]] = ""
			threading._start_new_thread(write_client,(conn,addr))
			servers.append(addr[0])
			print(connected_servers)
			channel_index[addr[0]] = ""
		return render_template("index.html",servers=servers, server_ip=server_ip, len_server=len(servers), data=clients_data, server_side=[play_files[play_order[index]],play_files[play_order[index+1]]])
	
	except:
		return render_template("index.html", servers=servers, server_ip=server_ip, len_server=len(servers), data=clients_data, server_side=[play_files[play_order[index]],play_files[play_order[index+1]]])

@app.route("/settings/", methods=["POST"])
def load_settings_page():
	global current_server
	current_server = request.form['settings_field']
	return render_template("setting.html", FYes="checked", CCNo="checked", FNo="", CCYes="")


@app.route("/server_settings/", methods=["POST"])
def load_server_settings_page():
	global current_server
	current_server = request.form['settings_field']
	return render_template("server_setting.html", FYes="checked", CCNo="checked", FNo="", CCYes="", DirYes="", DirNo="checked")

@app.route("/server_save/", methods=["POST"])
def save_server_settings():
	global run
	global fullscreen
	global CC
	global servers
	global server_ip
	global clients_data
	global play_files
	global play_order
	global index
	global channel_index
	global channel_listings
	global gui_run
	if request.form['directory'] != 'True':
		if request.form['Fullscreen'] == 'True':
			fullscreen = True
		if request.form['Fullscreen'] == 'False':
			fullscreen = False
		if request.form['CC'] == 'True':
			CC = True
		if request.form['CC'] == 'False':
			CC = False
		gui_run = False

		server_video_play(request.form['location'])
	time.sleep(1.5)
	return render_template("index.html", servers=servers, server_ip=server_ip, len_server=len(servers), data=clients_data, server_side=[play_files[play_order[index]],play_files[play_order[index+1]]])


@app.route("/save/", methods=["POST"])
def save_settings():
	global write_data
	global send_data
	global client_cc_setting
	global client_screen_mode
	global servers
	global server_ip
	global clients_data
	global play_files
	global play_order
	global index
	save_location = request.form['location']
	if len(save_location) > 0:
		print("Sent Data")
		send_data = True
		fullscreen = request.form['Fullscreen']
		cc = request.form['CC']
		write_data.clear()
		write_data.append(save_location)
		write_data.append(fullscreen)
		write_data.append(cc)
		time.sleep(1)
		print(cc, fullscreen)
		if fullscreen == True:
			client_screen_mode[current_server] = "checked"
		if fullscreen == False:
			client_screen_mode[current_server] = ""
		if cc == True:
			client_cc_setting[current_server] = "checked"
		if cc == False:
			client_cc_setting[current_server] = ""
		if len(write_data) == 0:
			print(f"Saving to and data is: {write_data} and servers are {servers} and data is {clients_data} aswell modes are: {client_cc_setting} {client_screen_mode}")
		if len(write_data) > 0:
			print("Server Not Found")
		write_data.clear()
	return render_template("index.html", servers=servers, server_ip=server_ip, len_server=len(servers), data=clients_data, server_side=[play_files[play_order[index]],play_files[play_order[index+1]]])


@app.route("/home/", methods=["POST"])
def go_home():
	global servers
	global server_ip
	global clients_data
	global play_files
	global play_order
	global index
	return render_template("index.html", servers=servers, server_ip=server_ip, len_server=len(servers), data=clients_data, server_side=[play_files[play_order[index]],play_files[play_order[index+1]]])

@app.route("/skip_forward/", methods=['POST'])
def skip_forward():
	global write_data
	global send_data
	global current_server
	global servers
	global server_ip
	global clients_data
	global play_files
	global play_order
	global index
	print("Skipping Forward")
	current_server = request.form['next']
	send_data = True
	write_data = [">", client_screen_mode, client_cc_setting]
	time.sleep(0.3)
	return render_template("index.html", servers=servers, server_ip=server_ip, len_server=len(servers), data=clients_data, server_side=[play_files[play_order[index]],play_files[play_order[index+1]]])

@app.route("/skip_back/", methods=['POST'])
def skip_back():
	global write_data
	global send_data
	global current_server
	global servers
	global server_ip
	global clients_data
	global play_files
	global play_order
	global index
	print("Skipping Forward")
	current_server = request.form['previous']
	send_data = True
	write_data = ["<", client_screen_mode, client_cc_setting]
	time.sleep(0.5)
	return render_template("index.html", servers=servers, server_ip=server_ip, len_server=len(servers), data=clients_data, server_side=[play_files[play_order[index]],play_files[play_order[index+1]]])


@app.route("/server_skip_forward/", methods=['POST'])
def server_skip_forward():
	global play_order
	global play_files
	global play_location
	global index
	global player_running
	global media_play_command
	global servers
	global server_ip
	global clients_data
	global fullscreen
	global CC
	
	if player_running:
		media_play_command = 1
	save_data(play_order, play_files, play_location, index, fullscreen, CC)
	time.sleep(0.5)
	return render_template("index.html", servers=servers, server_ip=server_ip, len_server=len(servers), data=clients_data, server_side=[play_files[play_order[index]],play_files[play_order[index+1]]])

@app.route("/server_skip_back/", methods=['POST'])
def server_skip_back():
	global play_order
	global play_files
	global play_location
	global index
	global player_running
	global media_play_command
	global servers
	global server_ip
	global clients_data
	global fullscreen
	global CC
	
	if player_running:
		media_play_command = 2
	save_data(play_order, play_files, play_location, index, fullscreen, CC)
	time.sleep(0.5)
	return render_template("index.html", servers=servers, server_ip=server_ip, len_server=len(servers), data=clients_data, server_side=[play_files[play_order[index]],play_files[play_order[index+1]]])

@app.route("/refresh/", methods=['POST'])
def client_refresh():
	global write_data
	global current_server
	global servers
	global server_ip
	global clients_data
	global play_files
	global play_order
	global index
	global client_screen_mode
	current_server = request.form['client_ip']
	write_data = ["?", client_screen_mode[current_server], client_cc_setting[current_server]]
	time.sleep(0.5)
	return render_template("index.html", servers=servers, server_ip=server_ip, len_server=len(servers), data=clients_data, server_side=[play_files[play_order[index]],play_files[play_order[index+1]]])


if __name__ == "__main__":
	#app.run(host=server_ip)
	app.run()
	if not player_running and os.path.exists("data_state_server.txt"):
		load_data()
