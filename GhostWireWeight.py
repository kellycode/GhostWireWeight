bl_info = {
    "name": "Ghost Wire Weight",
    "author": "Pon Pon Games",
    "version": (1, 2),
    "blender": (4, 1, 1),
    "location": "3D Viewport > Right side of Header",
    "description": "This shows wireframe with X-Ray on Wight Pain Mode.",
    "warning": "Not enough debugging. This addon can cause crashes.",
    "doc_url": "",
    "tracker_url": "",
    "category": "3D View"
}

import bpy
import gpu
import gpu_extras.batch
import bmesh

g_draw_handle = None
g_shader = gpu.shader.from_builtin('UNIFORM_COLOR')

g_batch = None

g_last_mode = ""
g_last_frame = -99999
g_does_draw = False

# Log
# 0: Warn and Error
# 1: Debug
# 2: Debug (Noisy)
def print_log(text, level):
    level_max = 0
    if level <= level_max:
        print(text)

# This is called only the first time the add-on is enabled after starting Blender.print_log("Ghost Wire Weight is called", 1)

# Control operator
# Toggles the running state of the drawing routine. Called from a button added to the UI。
class GhostWireWeight_OT_ModeController(bpy.types.Operator):
    bl_idname = "ghostwireweight.modecontroller"
    bl_label = "Ghost Wire Weight"

    def __init__(self):
        print_log("ModeController.init is called", 1)

    def __del__(self):
        print_log("ModeController.del is called", 1)

    def execute(self, context):
        print_log("ModeController.execute is called", 1)

        if bpy.app.timers.is_registered(update_ghost) == False:
            start_draw()
        else:
            stop_draw()
            # 再描画
            for area in bpy.context.window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()

        return {'FINISHED'}

    def invoke(self, context, event):
        print_log("ModeController.invoke is called", 1)
        return self.execute(context)

# Add button
# Called by Blender when redrawing the 3DView header.
def add_toggle_button(self, context):
    if context.active_object != None:
        if context.active_object.mode == "WEIGHT_PAINT":
            row = self.layout.row()
            row.active = False
            if bpy.app.timers.is_registered(update_ghost) == True:
                row.active = True
            label = "Ghost Wire"            
            row.operator(GhostWireWeight_OT_ModeController.bl_idname, text=label)

# Monitor modes and frames and update batches
# Called periodically by a timer.
def update_ghost():
    print_log("update_ghost is called", 2)
    
    global g_last_mode
    global g_last_frame
    global g_does_draw
    
    does_recreate = False
    
    # Check for mode change
    mode = bpy.context.active_object.mode
    if mode == "WEIGHT_PAINT":
        g_does_draw = True
        if g_last_mode != "WEIGHT_PAINT":
            does_recreate = True
    else:
        g_does_draw = False
    g_last_mode = mode

    # Check for frame changes
    frame = bpy.context.scene.frame_current
    if mode == "WEIGHT_PAINT":
        if frame != g_last_frame:
            does_recreate = True
    g_last_frame = frame    
    
    # Recreate the batch
    if does_recreate == True:
        recreate_batch()

        # 再描画
        for area in bpy.context.window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()    
    
    return 0.1

# Drawing
# Called when the 3DView is redrawn.
def draw_wire(dummy):
    print_log("draw_wire is called", 2)

    global g_does_draw
    global g_batch
    global g_shader
    if g_does_draw == True:
        if g_batch != None and g_shader != None:
            last_blend = gpu.state.blend_get()
            last_depth_test = gpu.state.depth_test_get()
            gpu.state.blend_set("ALPHA")
            gpu.state.depth_test_set("ALWAYS")
            g_shader.bind()
            g_shader.uniform_float("color", (1.0, 1.0, 1.0, 0.1))
            #g_shader.uniform_float("lineWidth", 5)
            g_batch.draw(g_shader)
            gpu.state.blend_set(last_blend)
            gpu.state.depth_test_set(last_depth_test)
            
# Batch update
# Get the mesh edges of the active object.
def recreate_batch():
    print_log("recreate_batch is called.", 1)

    # Tuple in Tuple
    # ((x, y, z), (x, y, z), (x, y, z), ...)
    coords = ()
    # ((i0, i1), (i0, i1), (i0, i1), ...)
    indices = ()

    if bpy.context.active_object != None:
        mesh = bpy.context.active_object.data # bpy_types.mesh
        if mesh != None:
                
            # Get the mesh with modifier applied
            depsgraph = bpy.context.evaluated_depsgraph_get()
            evaluated_object = bpy.context.active_object.evaluated_get(depsgraph)
            evaluated_mesh = evaluated_object.to_mesh()
                
            # Convert to world
            evaluated_mesh.transform(bpy.context.active_object.matrix_world)
                
            # Vertex
            for vertex in evaluated_mesh.vertices: # bpy.types.MeshVertex

                # co is class Vector
                coTuple = (vertex.co[0], vertex.co[1], vertex.co[2])
                coords = coords + (coTuple, )
            
            # Side
            for edge in evaluated_mesh.edges: # bpy_types.MeshEdge

                index0 = edge.vertices[0]
                index1 = edge.vertices[1]

                indexTuple = (index0, index1)
                indices = indices + (indexTuple, )

            evaluated_object.to_mesh_clear()

    global g_batch
    global g_shader
    g_batch = gpu_extras.batch.batch_for_shader(
        g_shader, "LINES", {"pos": coords}, indices=indices
    )

# Start drawing
# Register the timer (update_ghost) and add the drawing handler (draw_wire)
def start_draw():
    print_log("add_update_timer is called.", 1)

    global g_batch
    if g_batch != None:
        del g_batch
    g_batch = None

    global g_last_mode
    global g_last_frame
    global g_does_draw
    g_last_mode = ""
    g_last_frame = -9999
    g_does_draw = False
    
    if bpy.app.timers.is_registered(update_ghost) == False:
        bpy.app.timers.register(update_ghost, first_interval=0.1, persistent=False)

    global g_draw_handle
    if g_draw_handle == None:
        g_draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            draw_wire, (None, ), "WINDOW", "POST_VIEW"
        )

# End of drawing
# Cancel the timer (update_ghost) and remove the drawing handler (draw_wire)
def stop_draw():
    print_log("unregister_update_timer is called.", 1)

    if bpy.app.timers.is_registered(update_ghost) == True:
        bpy.app.timers.unregister(update_ghost)

    global g_draw_handle
    if g_draw_handle != None:
        bpy.types.SpaceView3D.draw_handler_remove(g_draw_handle, "WINDOW")
    g_draw_handle = None

# When loading a file, make sure to reset it to its initial state.
# If draw_handler is left as is, it will exist across blend files,
# so we will force delete it.
@bpy.app.handlers.persistent
def reset_status_on_load_post(scene):
    print_log("reset_status_on_load_post is called.", 1)
    stop_draw()

# Called by Blender when the add-on is enabled.
# At this time, bpy.data and bpy.context are not accessible.
def register():
    print_log("register is called.", 1)
    bpy.utils.register_class(GhostWireWeight_OT_ModeController)
    bpy.types.VIEW3D_HT_tool_header.append(add_toggle_button)
    bpy.app.handlers.load_post.append(reset_status_on_load_post)

# Called by Blender when the addon is disabled.
# In this case, bpy.data and bpy.context are inaccessible.。
def unregister():
    print_log("unregister is called", 1)
    bpy.app.handlers.load_post.remove(reset_status_on_load_post)
    bpy.types.VIEW3D_HT_tool_header.remove(add_toggle_button)
    bpy.utils.unregister_class(GhostWireWeight_OT_ModeController)
    stop_draw()

# Processing when called from Blender's text editor (for debugging)
if __name__ == "__main__":
    print_log("Ghost Wire Weight is called from main", 1)
    register()
    #unregister()

