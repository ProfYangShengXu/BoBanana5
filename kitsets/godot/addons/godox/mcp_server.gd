@tool
extends Reference
# G1 · MCP stdio Server
#
# JSON-RPC 2.0 over stdin/stdout protocol handler.
# Runs in a separate thread reading stdin, dispatching to plugin.gd methods.
#
# Request format:  {"id": 1, "method": "get_scene_tree", "params": {}}
# Response format: {"id": 1, "result": {"nodes": [...]}}
# Error format:    {"id": 1, "error": {"code": -32601, "message": "Method not found"}}

var plugin: EditorPlugin = null

var _running := false
var _thread: Thread = null
var _line_buffer := ""


func start() -> void:
	if _running:
		return
	_running = true
	_thread = Thread.new()
	_thread.start(_read_loop)


func stop() -> void:
	_running = false
	if _thread != null:
		_thread.wait_to_finish()
		_thread = null


# Main loop: read lines from stdin, dispatch, write response to stdout
func _read_loop() -> void:
	while _running:
		var line := _read_line()
		if line.is_empty():
			OS.delay_msec(10)
			continue

		var response := _dispatch(line)
		if not response.is_empty():
			# Write to stdout — flock to avoid interleaving
			printt(response)
			OS.delay_msec(5)


func _read_line() -> String:
	var result := ""
	while _running:
		if OS.has_feature("editor"):
			# Use FileAccess to read stdin non-blocking
			var fa := FileAccess.open("stdin://", FileAccess.READ)
			if fa != null and fa.get_length() > 0:
				var content := fa.get_as_text()
				fa.close()
				_line_buffer += content
				# Extract first complete line
				var nl := _line_buffer.find("\n")
				if nl >= 0:
					result = _line_buffer.substr(0, nl).strip_edges()
					_line_buffer = _line_buffer.substr(nl + 1)
					return result
		OS.delay_msec(20)
	return ""


# Parse JSON-RPC and dispatch to plugin method
func _dispatch(raw_json: String) -> String:
	var json := JSON.new()
	var parse_err := json.parse(raw_json)
	if parse_err != OK:
		return _error_resp(null, -32700, "Parse error: " + json.get_error_message())

	var msg := json.get_data()
	if typeof(msg) != TYPE_DICTIONARY:
		return _error_resp(null, -32600, "Invalid Request: not an object")

	var req_id = msg.get("id")
	var method: String = msg.get("method", "")
	var params: Dictionary = msg.get("params", {})

	if method.is_empty():
		return _error_resp(req_id, -32601, "Method not found")

	match method:
		"query_version":
			return _ok_resp(req_id, {"version": "1.0", "godot": Engine.get_version_info()})
		"get_scene_tree":
			return _call_plugin(req_id, "get_scene_tree", [])
		"add_node":
			return _call_plugin(req_id, "add_node", [
				params.get("parent_path", ""),
				params.get("node_type", "Node2D"),
				params.get("node_name", "NewNode"),
				params.get("properties", {})
			])
		"remove_node":
			return _call_plugin(req_id, "remove_node", [
				params.get("node_path", "")
			])
		"set_node_property":
			return _call_plugin(req_id, "set_node_property", [
				params.get("node_path", ""),
				params.get("properties", {})
			])
		"attach_script":
			return _call_plugin(req_id, "attach_script", [
				params.get("node_path", ""),
				params.get("script_path", "")
			])
		"start_input_relay":
			return _call_plugin(req_id, "start_input_relay", [
				params.get("port", 42069)
			])
		"stop_input_relay":
			return _call_plugin(req_id, "stop_input_relay", [])
		"start_log_channel":
			return _call_plugin(req_id, "start_log_channel", [
				params.get("port", 42070)
			])
		"stop_log_channel":
			return _call_plugin(req_id, "stop_log_channel", [])
		"validate_scene":
			return _call_plugin(req_id, "validate_scene", [
				params.get("scene_path", "")
			])
		_:
			return _error_resp(req_id, -32601, "Method not found: " + method)


# Call a method on plugin.gd and return JSON-RPC result
func _call_plugin(req_id, method: String, args: Array) -> String:
	if plugin == null:
		return _error_resp(req_id, -32000, "Plugin reference not set")

	if not plugin.has_method(method):
		return _error_resp(req_id, -32601, "Handler not implemented: " + method)

	var result = plugin.callv(method, args)
	if typeof(result) == TYPE_DICTIONARY and result.has("error"):
		return _error_resp(req_id, -32000, result["error"])
	return _ok_resp(req_id, result)


func _ok_resp(req_id, result) -> String:
	var resp := {"jsonrpc": "2.0", "id": req_id, "result": result}
	return JSON.stringify(resp)


func _error_resp(req_id, code: int, message: String) -> String:
	var resp := {
		"jsonrpc": "2.0",
		"id": req_id,
		"error": {"code": code, "message": message}
	}
	return JSON.stringify(resp)
