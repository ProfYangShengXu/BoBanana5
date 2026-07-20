@tool
extends EditorPlugin

# Godox MCP Bridge — Main EditorPlugin entry point
# Godot 4.7+
# Protocols: JSON-RPC 2.0 over stdio (classic) + WebSocket (enhanced)

var mcp_server: Reference = null
var ws_server: Node = null
var scene_bridge: Reference = null
var input_relay: Reference = null
var log_channel: Reference = null
var validator: Reference = null
var dock: Control = null
var _ws_port: int = 9800

const MCP_SERVER_SCRIPT := preload("res://addons/godox/mcp_server.gd")
const WS_SERVER_SCRIPT := preload("res://addons/godox/mcp_ws_server.gd")
const SCENE_BRIDGE_SCRIPT := preload("res://addons/godox/scene_bridge.gd")
const INPUT_RELAY_SCRIPT := preload("res://addons/godox/input_relay.gd")
const LOG_CHANNEL_SCRIPT := preload("res://addons/godox/log_channel.gd")
const VALIDATOR_SCRIPT := preload("res://addons/godox/validator.gd")


func _enter_tree() -> void:
	print("[godox] Plugin loading...")
	_start_mcp_server()
	_start_ws_server()
	_setup_dock()
	print("[godox] Plugin ready — stdio MCP + WebSocket :", _ws_port)


func _exit_tree() -> void:
	_stop_ws_server()
	_stop_mcp_server()
	_remove_dock()


# ── Stdio MCP Server (original) ──

func _start_mcp_server() -> void:
	mcp_server = MCP_SERVER_SCRIPT.new()
	mcp_server.plugin = self
	mcp_server.start()


func _stop_mcp_server() -> void:
	if mcp_server:
		mcp_server.stop()
		mcp_server = null


# ── WebSocket Server (enhanced) ──

func _start_ws_server() -> void:
	ws_server = WS_SERVER_SCRIPT.new()
	add_child(ws_server)
	ws_server.connect("request_received", _on_ws_request)
	ws_server.start(_ws_port)

	scene_bridge = SCENE_BRIDGE_SCRIPT.new(self)


func _stop_ws_server() -> void:
	if ws_server:
		ws_server.stop()
		remove_child(ws_server)
		ws_server.free()
		ws_server = null


# ── WebSocket Request Handler ──

func _on_ws_request(client_id: int, request: Dictionary) -> void:
	var req_id = request.get("id")
	var method: String = request.get("method", "")
	var params: Dictionary = request.get("params", {})

	var result = _dispatch_method(method, params)
	if result == null:
		result = _dispatch_to_stdio(method, params)

	if result != null:
		var response := {
			"jsonrpc": "2.0",
			"id": req_id,
			"result": result,
		}
		ws_server.send_response(client_id, response)


func _dispatch_method(method: String, params: Dictionary):
	match method:
		"get_scene_tree":
			if scene_bridge:
				return scene_bridge.get_scene_tree()
		"add_node":
			if scene_bridge:
				return scene_bridge.add_node(
					params.get("parent_path", "."),
					params.get("node_type", "Node2D"),
					params.get("name", "NewNode")
				)
		"remove_node":
			if scene_bridge:
				return scene_bridge.remove_node(params.get("path", ""))
		"set_property":
			if scene_bridge:
				return scene_bridge.set_property(
					params.get("path", ""),
					params.get("property", ""),
					params.get("value")
				)
		"get_scene_path":
			if scene_bridge:
				return {"path": scene_bridge.get_scene_path()}
		"get_version":
			return {
				"godox_version": "1.0.0",
				"godot_version": Engine.get_version_info(),
			}
		"get_editor_state":
			return _get_editor_state()
		_:
			return null
	return null


func _dispatch_to_stdio(method: String, params: Dictionary):
	# Fallback to stdio MCP server if WebSocket handler doesn't know the method
	if mcp_server and mcp_server.has_method("_handle_method"):
		return mcp_server._handle_method(method, params)
	return null


func _get_editor_state() -> Dictionary:
	var iface := get_editor_interface()
	return {
		"has_scene_open": iface.get_edited_scene_root() != null,
		"scene_count": iface.get_open_scenes().size(),
		"is_playing": iface.is_playing_scene(),
	}


# ── Editor Methods (compatibility with stdio MCP) ──

func add_node(parent_path: String, node_type: String, node_name: String, script_path: String = "") -> Dictionary:
	if scene_bridge:
		return scene_bridge.add_node(parent_path, node_type, node_name)
	return {"error": "scene_bridge not initialized"}


func remove_node(path: String) -> Dictionary:
	if scene_bridge:
		return scene_bridge.remove_node(path)
	return {"error": "scene_bridge not initialized"}


func set_node_property(path: String, property: String, value) -> Dictionary:
	if scene_bridge:
		return scene_bridge.set_property(path, property, value)
	return {"error": "scene_bridge not initialized"}


func get_scene_tree() -> Dictionary:
	if scene_bridge:
		return scene_bridge.get_scene_tree()
	return {"error": "scene_bridge not initialized"}


func query_version() -> Dictionary:
	return _dispatch_method("get_version", {})


# ── Dock UI ──

func _setup_dock() -> void:
	dock = preload("res://addons/godox/dock.tscn").instantiate() if ResourceLoader.exists("res://addons/godox/dock.tscn") else _create_default_dock()
	add_control_to_dock(DOCK_SLOT_LEFT_UL, dock)
	dock.visible = true


func _create_default_dock() -> Control:
	var panel := PanelContainer.new()
	var vbox := VBoxContainer.new()
	panel.add_child(vbox)

	var title := Label.new()
	title.text = "Godox MCP Bridge"
	title.add_theme_font_size_override("font_size", 14)
	vbox.add_child(title)

	var status := Label.new()
	status.name = "StatusLabel"
	status.text = "Status: Running (ws://:" + str(_ws_port) + ")"
	vbox.add_child(status)

	var btn := Button.new()
	btn.text = "Get Scene Tree"
	btn.connect("pressed", _on_get_scene_tree_pressed)
	vbox.add_child(btn)

	var tree_preview := RichTextLabel.new()
	tree_preview.name = "TreePreview"
	tree_preview.bbcode_enabled = true
	tree_preview.minimum_size = Vector2(200, 200)
	vbox.add_child(tree_preview)

	return panel


func _remove_dock() -> void:
	if dock:
		remove_control_from_docks(dock)
		dock.free()
		dock = null


func _on_get_scene_tree_pressed() -> void:
	var tree = get_scene_tree()
	var preview = dock.get_node("TreePreview") if dock else null
	if preview:
		var text = "[b]Scene Tree[/b]\n"
		if tree.has("nodes"):
			text += _tree_to_text(tree["nodes"], 0, 20)
		preview.bbcode_text = text


func _tree_to_text(nodes: Array, depth: int, max_items: int) -> String:
	if max_items <= 0:
		return ""
	var text := ""
	var indent := "  ".repeat(depth)
	for node in nodes:
		if max_items <= 0:
			break
		text += indent + "- " + node.get("name", "?") + " (" + node.get("type", "?") + ")\n"
		max_items -= 1
		if node.has("children"):
			var child_text = _tree_to_text(node["children"], depth + 1, max_items)
			text += child_text
			max_items -= child_text.count("\n")
	return text


# ── Input Simulation (delegate to input_relay.gd) ──

func get_input_relay():
	if not input_relay:
		input_relay = INPUT_RELAY_SCRIPT.new()
	return input_relay


# ── Log Channel (delegate to log_channel.gd) ──

func get_log_channel():
	if not log_channel:
		log_channel = LOG_CHANNEL_SCRIPT.new()
	return log_channel


# ── Validator (delegate to validator.gd) ──

func get_validator():
	if not validator:
		validator = VALIDATOR_SCRIPT.new()
	return validator
