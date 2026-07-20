@tool
extends Node
# MCP WebSocket Server — JSON-RPC 2.0 over WebSocket
#
# 在独立线程中运行 WebSocket 服务器，接收 Agent 的 JSON-RPC 请求。
# 端口: 9800 (默认)
#
# 请求格式:  {"jsonrpc": "2.0", "id": 1, "method": "get_scene_tree", "params": {}}
# 响应格式: {"jsonrpc": "2.0", "id": 1, "result": {"nodes": [...]}}
# 事件推送: {"jsonrpc": "2.0", "method": "scene.updated", "params": {...}}

signal connected(client_id: int)
signal disconnected(client_id: int)
signal request_received(client_id: int, request: Dictionary)

var port: int = 9800
var _server: WebSocketServer = null
var _clients: Dictionary = {}  # client_id -> WebSocketPeer
var _running := false


func start(p: int = 9800) -> void:
	if _running:
		return
	port = p
	_server = WebSocketServer.new()
	_server.bind(port)
	_server.connect("client_connected", _on_client_connected)
	_server.connect("client_disconnected", _on_client_disconnected)
	_server.start()
	_running = true
	print("[Godox MCP WS] WebSocket server started on ws://localhost:", port)


func stop() -> void:
	if not _running:
		return
	if _server:
		_server.stop()
		_server = null
	_running = false
	_clients.clear()
	print("[Godox MCP WS] WebSocket server stopped")


func _process(_delta: float) -> void:
	if not _running or not _server:
		return
	_server.poll()

	for id in _clients.keys():
		var peer: WebSocketPeer = _clients.get(id)
		if not peer:
			continue
		peer.poll()
		if peer.get_ready_state() != WebSocketPeer.STATE_OPEN:
			continue
		while peer.get_available_packet_count() > 0:
			var packet = peer.get_packet().get_string_from_utf8()
			_handle_packet(id, packet)


func _on_client_connected(id: int, protocol: String) -> void:
	var peer: WebSocketPeer = _server.get_client(id)
	_clients[id] = peer
	connected.emit(id)
	print("[Godox MCP WS] Client connected: ", id)


func _on_client_disconnected(id: int) -> void:
	_clients.erase(id)
	disconnected.emit(id)
	print("[Godox MCP WS] Client disconnected: ", id)


func _handle_packet(client_id: int, packet: String) -> void:
	var json := JSON.new()
	var err := json.parse(packet)
	if err != OK:
		_send_error(client_id, null, -32700, "Parse error: " + json.get_error_message())
		return

	var request = json.get_data()
	if typeof(request) != TYPE_DICTIONARY:
		_send_error(client_id, null, -32600, "Invalid Request")
		return

	request_received.emit(client_id, request)


func send_response(client_id: int, response: Dictionary) -> void:
	var peer: WebSocketPeer = _clients.get(client_id)
	if not peer:
		return
	var json_str = JSON.stringify(response)
	peer.send_text(json_str)


func send_event(method: String, params: Dictionary = {}) -> void:
	"""向所有客户端推送事件"""
	var event := {
		"jsonrpc": "2.0",
		"method": method,
		"params": params,
	}
	var json_str = JSON.stringify(event)
	for client_id in _clients.keys():
		var peer: WebSocketPeer = _clients.get(client_id)
		if peer and peer.get_ready_state() == WebSocketPeer.STATE_OPEN:
			peer.send_text(json_str)


func _send_error(client_id: int, req_id, code: int, message: String) -> void:
	var response := {
		"jsonrpc": "2.0",
		"id": req_id,
		"error": {"code": code, "message": message},
	}
	send_response(client_id, response)


func has_clients() -> bool:
	return _clients.size() > 0


func client_count() -> int:
	return _clients.size()
