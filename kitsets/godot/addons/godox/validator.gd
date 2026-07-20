@tool
extends Reference
# G4 · Scene Validator
#
# Validates .tscn files by loading them with ResourceLoader.load()
# and reporting errors/warnings.
#
# Much faster than launching godot --headless --check because it runs
# inside the already-running editor process.

var plugin: EditorPlugin = null


# Validate a scene file at the given res:// path
# Returns: { valid: bool, errors: [], warnings: [] }
func validate(scene_path: String) -> Dictionary:
	var result := {
		"valid": true,
		"errors": [],
		"warnings": []
	}

	if scene_path.is_empty():
		result.valid = false
		result.errors.append({"code": "EMPTY_PATH", "message": "Scene path is empty"})
		return result

	# Check file exists
	if not ResourceLoader.exists(scene_path):
		result.valid = false
		result.errors.append({
			"code": "FILE_NOT_FOUND",
			"message": "Scene file not found: " + scene_path
		})
		return result

	# Try loading the scene
	var scene := ResourceLoader.load(scene_path, "PackedScene", ResourceLoader.CACHE_MODE_REUSE)
	if scene == null:
		result.valid = false
		result.errors.append({
			"code": "LOAD_FAILED",
			"message": "ResourceLoader.load() returned null for: " + scene_path
		})
		return result

	# Verify it's a valid PackedScene
	if not scene is PackedScene:
		result.valid = false
		result.errors.append({
			"code": "WRONG_TYPE",
			"message": "Resource is not a PackedScene, got: " + str(scene.get_class())
		})
		return result

	# Try instantiating the scene to check for runtime errors
	var instance := scene.instantiate()
	if instance == null:
		result.valid = false
		result.errors.append({
			"code": "INSTANTIATE_FAILED",
			"message": "Failed to instantiate scene: " + scene_path
		})
		return result

	instance.queue_free()

	return result
