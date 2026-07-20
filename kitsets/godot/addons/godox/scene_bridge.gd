@tool
extends Reference
# 场景桥接器 — 读取和修改 Godot 场景树
#
# 供 mcp_ws_server.gd 调用的核心场景操作接口。

var plugin: EditorPlugin = null


func _init(p: EditorPlugin) -> void:
	plugin = p


# 获取当前编辑场景的完整树结构
func get_scene_tree() -> Dictionary:
	var scene_root := plugin.get_editor_interface().get_edited_scene_root()
	if not scene_root:
		return {"nodes": [], "error": "No scene open"}
	return _node_to_dict(scene_root)


# 递归将节点转为字典
func _node_to_dict(node: Node) -> Dictionary:
	var data := {
		"name": node.name,
		"type": node.get_class(),
		"path": plugin.get_editor_interface().get_edited_scene_root().get_path_to(node) if node != plugin.get_editor_interface().get_edited_scene_root() else ".",
		"children": [],
		"properties": _get_node_properties(node),
	}
	for child in node.get_children():
		data["children"].append(_node_to_dict(child))
	return data


# 获取节点的主要属性
func _get_node_properties(node: Node) -> Dictionary:
	var props := {}
	var skip := ["name", "script", "filename", "owner", "unique_name_in_owner"]
	for prop in node.get_property_list():
		var name = prop.get("name", "")
		if name in skip or name.begins_with("__") or name.begins_with("_"):
			continue
		var usage = prop.get("usage", 0)
		if usage & PROPERTY_USAGE_EDITOR:
			var val = node.get(name)
			if typeof(val) in [TYPE_INT, TYPE_FLOAT, TYPE_BOOL, TYPE_STRING, TYPE_VECTOR2, TYPE_VECTOR3, TYPE_COLOR]:
				props[name] = val
	return props


# 按路径查找节点
func find_node(path: String) -> Node:
	var root := plugin.get_editor_interface().get_edited_scene_root()
	if not root:
		return null
	if path == ".":
		return root
	return root.get_node_or_null(path)


# 添加节点到场景
func add_node(parent_path: String, node_type: String, node_name: String) -> Dictionary:
	var parent := find_node(parent_path)
	if not parent:
		return {"error": "Parent node not found: " + parent_path}

	var new_node: Node = _create_node(node_type)
	if not new_node:
		return {"error": "Unknown node type: " + node_type}

	new_node.name = node_name
	parent.add_child(new_node, true)
	new_node.set_owner(plugin.get_editor_interface().get_edited_scene_root())
	return {"success": true, "node": _node_to_dict(new_node)}


# 删除节点
func remove_node(path: String) -> Dictionary:
	var node := find_node(path)
	if not node:
		return {"error": "Node not found: " + path}

	var parent = node.get_parent()
	if parent:
		parent.remove_child(node)
	node.free()
	return {"success": true}


# 设置节点属性
func set_property(path: String, property: String, value) -> Dictionary:
	var node := find_node(path)
	if not node:
		return {"error": "Node not found: " + path}

	node.set(property, value)
	return {"success": true, "new_value": node.get(property)}


# 创建节点实例
func _create_node(type_name: String) -> Node:
	var class_map := {
		"Node2D": Node2D,
		"Node3D": Node3D,
		"Sprite2D": Sprite2D,
		"Label": Label,
		"Button": Button,
		"TextureRect": TextureRect,
		"CollisionShape2D": CollisionShape2D,
		"Area2D": Area2D,
		"RigidBody2D": RigidBody2D,
		"CharacterBody2D": CharacterBody2D,
		"Camera2D": Camera2D,
		"TileMap": TileMap,
		"Node": Node,
		"Control": Control,
		"Panel": Panel,
		"ColorRect": ColorRect,
		"AudioStreamPlayer2D": AudioStreamPlayer2D,
		"AnimationPlayer": AnimationPlayer,
		"Timer": Timer,
		"RichTextLabel": RichTextLabel,
	}
	var cls = class_map.get(type_name)
	if cls:
		return cls.new()
	return null


# 获取场景文件的完整路径
func get_scene_path() -> String:
	var root := plugin.get_editor_interface().get_edited_scene_root()
	if root and root.filename:
		return root.filename
	return ""
