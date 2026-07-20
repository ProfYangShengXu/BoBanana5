@tool
extends Reference
# G2 · Input Relay
#
# UDP socket listener that receives Agent key events and injects them
# into the running game via Input.parse_input_event().
#
# Protocol: JSON packets over UDP 127.0.0.1:42069
#
# Request format:
#   {"event": "key_press",  "key": "Space"}           # tap (press + release)
#   {"event": "key_down",   "key": "W"}                # hold down
#   {"event": "key_up",     "key": "W"}                # release
#   {"event": "key_sequence", "keys": ["W","W","Space"], "delay_ms": 200}
#
# Response format:
#   {"status": "ok", "event": "key_press", "key": "Space"}
#   {"status": "error", "message": "Unknown key: INVALID"}

var plugin: EditorPlugin = null

var _udp: PacketPeerUDP = null
var _running := false
var _thread: Thread = null
var _port: int = 42069

# Key name → KeyCode mapping (Godot 4.x)
const KEY_MAP: Dictionary = {
	"Space": KEY_SPACE,
	"Enter": KEY_ENTER,
	"Escape": KEY_ESCAPE,
	"Tab": KEY_TAB,
	"Backspace": KEY_BACKSPACE,
	"Up": KEY_UP,
	"Down": KEY_DOWN,
	"Left": KEY_LEFT,
	"Right": KEY_RIGHT,
	"Shift": KEY_SHIFT,
	"Control": KEY_CTRL,
	"Alt": KEY_ALT,
	"W": KEY_W,
	"A": KEY_A,
	"S": KEY_S,
	"D": KEY_D,
	"Q": KEY_Q,
	"E": KEY_E,
	"R": KEY_R,
	"F": KEY_F,
	"X": KEY_X,
	"Y": KEY_Y,
	"Z": KEY_Z,
	"1": KEY_1,
	"2": KEY_2,
	"3": KEY_3,
	"4": KEY_4,
	"5": KEY_5,
	"MouseLeft": MOUSE_BUTTON_LEFT,
	"MouseRight": MOUSE_BUTTON_RIGHT,
}

# Physical key mapping for reliable input
const PHYSICAL_KEY_MAP: Dictionary = {
	"W": KEY_W,
	"A": KEY_A,
	"S": KEY_S,
	"D": KEY_D,
	"Space": KEY_SPACE,
}


func start(port: int = 42069) -> bool:
	if _running:
		return true

	_port = port
	_udp = PacketPeerUDP.new()

	var err := _udp.bind(_port, "127.0.0.1")
	if err != OK:
		print("[godox] Input Relay: Failed to bind UDP :" + str(_port) + " error=" + str(err))
		return false

	_running = true
	_thread = Thread.new()
	_thread.start(_listen_loop)

	print("[godox] Input Relay: Listening on UDP 127.0.0.1:" + str(_port))
	return true


func stop() -> void:
	_running = false
	if _thread != null:
		_thread.wait_to_finish()
		_thread = null
	if _udp != null:
		_udp.close()
		_udp = null
	print("[godox] Input Relay: Stopped")


# Background thread: listen for UDP packets
func _listen_loop() -> void:
	while _running:
		if _udp.get_available_packet_count() > 0:
			var packet := _udp.get_packet()
			if packet.size() > 0:
				var json_str := packet.get_string_from_utf8()
				var response := _handle_packet(json_str)
				var resp_bytes := response.to_utf8()
				_udp.set_dest_address("127.0.0.1", _udp.get_packet_port())
				_udp.put_packet(resp_bytes)
		OS.delay_msec(10)


func _handle_packet(json_str: String) -> String:
	var json := JSON.new()
	var err := json.parse(json_str)
	if err != OK:
		return '{"status":"error","message":"Parse error"}'

	var data = json.get_data()
	if typeof(data) != TYPE_DICTIONARY:
		return '{"status":"error","message":"Invalid JSON"}'

	var event_type: String = data.get("event", "")

	match event_type:
		"key_press":
			return _do_key_tap(data.get("key", ""))
		"key_down":
			return _do_key_down(data.get("key", ""))
		"key_up":
			return _do_key_up(data.get("key", ""))
		"key_sequence":
			return _do_key_sequence(data.get("keys", []), data.get("delay_ms", 100))
		_:
			return '{"status":"error","message":"Unknown event type: ' + event_type + '"}'


func _do_key_tap(key_name: String) -> String:
	var code := _get_keycode(key_name)
	if code == null:
		return '{"status":"error","message":"Unknown key: ' + key_name + '"}'

	# Press
	var ev_press := InputEventKey.new()
	ev_press.keycode = code
	ev_press.pressed = true
	Input.parse_input_event(ev_press)

	# Release (after small delay to simulate real tap)
	var ev_release := InputEventKey.new()
	ev_release.keycode = code
	ev_release.pressed = false
	Input.parse_input_event(ev_release)

	return '{"status":"ok","event":"key_press","key":"' + key_name + '"}'


func _do_key_down(key_name: String) -> String:
	var code := _get_keycode(key_name)
	if code == null:
		return '{"status":"error","message":"Unknown key: ' + key_name + '"}'

	var ev := InputEventKey.new()
	ev.keycode = code
	ev.pressed = true
	Input.parse_input_event(ev)

	return '{"status":"ok","event":"key_down","key":"' + key_name + '"}'


func _do_key_up(key_name: String) -> String:
	var code := _get_keycode(key_name)
	if code == null:
		return '{"status":"error","message":"Unknown key: ' + key_name + '"}'

	var ev := InputEventKey.new()
	ev.keycode = code
	ev.pressed = false
	Input.parse_input_event(ev)

	return '{"status":"ok","event":"key_up","key":"' + key_name + '"}'


func _do_key_sequence(keys: Array, delay_ms: int) -> String:
	var results := []
	for key_name in keys:
		var result := _do_key_tap(str(key_name))
		results.append(result)
		OS.delay_msec(delay_ms)
	return '{"status":"ok","event":"key_sequence","count":' + str(keys.size()) + '}'


func _get_keycode(key_name: String):
	# Try exact match
	if KEY_MAP.has(key_name):
		return KEY_MAP[key_name]

	# Try uppercase
	var upper := key_name.to_upper()
	if KEY_MAP.has(upper):
		return KEY_MAP[upper]

	# Try capitalizing first letter
	if key_name.length() > 0:
		var capitalized := key_name[0].to_upper() + key_name.substr(1).to_lower()
		if KEY_MAP.has(capitalized):
			return KEY_MAP[capitalized]

	return null
