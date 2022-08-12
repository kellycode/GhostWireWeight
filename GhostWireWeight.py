import bpy
import gpu
import gpu_extras.batch
import bgl
import bmesh

# アドオン情報（名前やバージョンなど）
bl_info = {
    "name": "Ghost Wire Weight",
    "author": "Pon Pon Games",
    "version": (1, 1),
    "blender": (3, 2, 1),
    "location": "3D Viewport > Right side of Header",
    "description": "This shows wireframe with X-Ray on Wight Pain Mode.",
    "warning": "Not enough debugging. This addon can cause crashes.",
    "support": "TESTING",
    "doc_url": "",
    "tracker_url": "",
    "category": "3D View"
}

g_draw_handle = None
g_shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')

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

# Blender起動後の初回のアドオン有効時だけ呼ばれます。
print_log("Ghost Wire Weight is called", 1)

# 制御オペレータ
# 描画ルーチンの起動状態をトグルします。UIに追加したボタンから呼ばれます。
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

# ボタンの追加
# 3DViewのヘッダの再描画時にBlenderから呼ばれます。
def add_toggle_button(self, context):
    if context.active_object != None:
        if context.active_object.mode == "WEIGHT_PAINT":
            row = self.layout.row()
            row.active = False
            if bpy.app.timers.is_registered(update_ghost) == True:
                row.active = True
            label = "Ghost Wire"            
            row.operator(GhostWireWeight_OT_ModeController.bl_idname, text=label)

# モードとフレームの監視とバッチの更新
# タイマーにより定期的に呼ばれます。
def update_ghost():
    print_log("update_ghost is called", 2)
    
    global g_last_mode
    global g_last_frame
    global g_does_draw
    
    does_recreate = False
    
    # モード変更をチェック
    mode = bpy.context.active_object.mode
    if mode == "WEIGHT_PAINT":
        g_does_draw = True
        if g_last_mode != "WEIGHT_PAINT":
            does_recreate = True
    else:
        g_does_draw = False
    g_last_mode = mode

    # フレーム変更をチェック
    frame = bpy.context.scene.frame_current
    if mode == "WEIGHT_PAINT":
        if frame != g_last_frame:
            does_recreate = True
    g_last_frame = frame    
    
    # バッチの作り直し
    if does_recreate == True:
        recreate_batch()

        # 再描画
        for area in bpy.context.window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()    
    
    return 0.1

# 描画
# 3DViewの再描画時に呼ばれます。
def draw_wire(dummy):
    print_log("draw_wire is called", 2)

    global g_does_draw
    global g_batch
    global g_shader
    if g_does_draw == True:
        if g_batch != None and g_shader != None:
            bgl.glEnable(bgl.GL_BLEND)
            bgl.glDisable(bgl.GL_DEPTH_TEST)
            g_shader.bind()
            g_shader.uniform_float("color", (1.0, 1.0, 1.0, 0.1))
            g_batch.draw(g_shader)
            bgl.glDisable(bgl.GL_BLEND)
            bgl.glEnable(bgl.GL_DEPTH_TEST)
            
# バッチの更新
# アクティブオブジェクトのメッシュの辺を取得します。
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
                
            # モディファイア適用済みのメッシュを取得
            depsgraph = bpy.context.evaluated_depsgraph_get()
            evaluated_object = bpy.context.active_object.evaluated_get(depsgraph)
            evaluated_mesh = evaluated_object.to_mesh()
                
            # ワールドに変換
            evaluated_mesh.transform(bpy.context.active_object.matrix_world)
                
            # 頂点
            for vertex in evaluated_mesh.vertices: # bpy.types.MeshVertex

                # co is class Vector
                coTuple = (vertex.co[0], vertex.co[1], vertex.co[2])
                coords = coords + (coTuple, )
            
            # 辺
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

# 描画開始
# タイマーの登録(update_ghost)と、描画ハンドラの追加(draw_wire)
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

# 描画終了
# タイマーの解除(update_ghost)と、描画ハンドラの削除(draw_wire)
def stop_draw():
    print_log("unregister_update_timer is called.", 1)

    if bpy.app.timers.is_registered(update_ghost) == True:
        bpy.app.timers.unregister(update_ghost)

    global g_draw_handle
    if g_draw_handle != None:
        bpy.types.SpaceView3D.draw_handler_remove(g_draw_handle, "WINDOW")
    g_draw_handle = None

# ファイル読み込み時に、確実に初期状態にします。
# draw_handlerはそのままだとblendファイルをまたいで存在してしまうので、
# 強制的に削除します。
@bpy.app.handlers.persistent
def reset_status_on_load_post(scene):
    print_log("reset_status_on_load_post is called.", 1)
    stop_draw()

# アドオンを有効にしたときにBlenderから呼ばれます。
# このとき、bpy.dataとbpy.contextにアクセス不可。
def register():
    print_log("register is called.", 1)
    bpy.utils.register_class(GhostWireWeight_OT_ModeController)
    bpy.types.VIEW3D_HT_tool_header.append(add_toggle_button)
    bpy.app.handlers.load_post.append(reset_status_on_load_post)

# アドオンを無効にしたときにBlenderから呼ばれます。
# このとき、bpy.dataとbpy.contextにアクセス不可。
def unregister():
    print_log("unregister is called", 1)
    bpy.app.handlers.load_post.remove(reset_status_on_load_post)
    bpy.types.VIEW3D_HT_tool_header.remove(add_toggle_button)
    bpy.utils.unregister_class(GhostWireWeight_OT_ModeController)
    stop_draw()

# Blenderのテキストエディタで呼んだときの処理（デバッグ用）
if __name__ == "__main__":
    print_log("Ghost Wire Weight is called from main", 1)
    register()
    #unregister()

