@tool
extends Reference
# G3 · Structured Log Channel
#
# Intercepts Godot log messages via Engine.add_log_message_hook()
# and streams them as JSON over TCP socket to Agent.
#
# Protocol: TCP 127.0.0.1:42070
# Each message is a single JSON line terminated by \n:
#   {"level":"info","message":"hello","file":"res://player.gd","line":42,"ts":1234}
#
# Levels: error, warning, info, debug (maps from Godot's MSG_FLAG_*)

var plugin: EditorPlugin = null

var _tcp: TCPServer = null
var _client: StreamPeerTCP = null
var _running := false
var _thread: Thread = null
var _port: int = 42070
var _hook_id := 0
var _log_count := 0
var _max_logs := 10000  # Rate limit: max logs per session

# Godot log message flags
const MSG_FLAG_ERROR := 1
const MSG_FLAG_WARNING := 2
const MSG_FLAG_INFO := 4


func start(port: int = 42070) -> bool:
	if _running:
		return true

	_port = port
	_tcp = TCPServer.new()

	var err := _tcp.listen(_port, "127.0.0.1")
	if err != OK:
		print("[godox] Log Channel: Failed to listen TCP :" + str(_port) + " error=" + str(err))
		return false

	# Register log message hook
	_add_log_hook()

	_running = true
	_thread = Thread.new()
	_thread.start(_accept_loop)

	print("[godox] Log Channel: Listening on TCP 127.0.0.1:" + str(_port))
	return true


func stop() -> void:
	_running = false
	_remove_log_hook()
	if _thread != null:
		_thread.wait_to_finish()
		_thread = null
	if _tcp != null:
		_tcp.stop()
		_tcp = null
	if _client != null:
		_client = null
	_log_count = 0
	print("[godox] Log Channel: Stopped")


# Accept TCP connections in background thread
func _accept_loop() -> void:
	while _running:
		if _client == null or _client.get_status() != StreamPeerTCP.STATUS_CONNECTED:
			_client = null
			if _tcp.is_connection_available():
				_client = _tcp.take_connection()
				if _client != null:
					print("[godox] Log Channel: Client connected")
		OS.delay_msec(50)


# Hook: called by Godot engine for every log message
func _log_hook(msg: String, flags: int, file: String, line: int) -> void:
	if not _running:
		return
	if _log_count >= _max_logs:
		return
	if _client == null or _client.get_status() != StreamPeerTCP.STATUS_CONNECTED:
		return

	_log_count += 1

	var level := "info"
	if flags & MSG_FLAG_ERROR:
		level = "error"
	elif flags & MSG_FLAG_WARNING:
		level = "warning"

	# Build JSON
	var json_line := JSON.stringify({
		"level": level,
		"message": msg,
		"file": file,
		"line": line,
		"ts": Time.get_ticks_msec()
	}) + "\n"

	var bytes := json_line.to_utf8()
	_client.put_data(bytes)


func _add_log_hook() -> void:
	# Engine.add_log_message_hook takes a Callable
	# The hook receives (message: String, flags: int, file: String, line: int)
	if Engine.has_method("add_log_message_hook"):
		Engine.add_log_message_hook(_log_hook)


func _remove_log_hook() -> void:
	if Engine.has_method("remove_log_message_hook"):
		Engine.remove_log_message_hook(_log_hook)
