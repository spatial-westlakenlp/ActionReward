import bpy
import glob
import os
import imageio
from PIL import Image
import math
import mathutils
import shutil
import sys
import argparse


VIEW_OFFSETS = [
    {'cam': (-1, -3, 0.6), 'light': (-4, -6, 6)},
    {'cam': (1, 3, 0.6), 'light': (4, 6, 6)},
]


def add_chessboard_floor(size=10, divisions=10, z=0, transparency=0.5):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0,0,z))
    floor = bpy.context.object
    floor.name = 'ChessboardFloor'

    mat = bpy.data.materials.new(name="ChessboardMaterial")
    mat.use_nodes = True

    mat.blend_method = 'BLEND'
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    for node in nodes:
        nodes.remove(node)

    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    principled_node = nodes.new(type='ShaderNodeBsdfPrincipled')
    checker_node = nodes.new(type='ShaderNodeTexChecker')
    texture_coord = nodes.new(type='ShaderNodeTexCoord')
    mapping_node = nodes.new(type='ShaderNodeMapping')

    alpha_node = nodes.new(type='ShaderNodeValue')
    alpha_node.outputs[0].default_value = transparency 

    checker_node.inputs['Scale'].default_value = divisions

    links.new(texture_coord.outputs['UV'], mapping_node.inputs['Vector'])
    links.new(mapping_node.outputs['Vector'], checker_node.inputs['Vector'])
    links.new(checker_node.outputs['Color'], principled_node.inputs['Base Color'])
    links.new(alpha_node.outputs[0], principled_node.inputs['Alpha']) 
    links.new(principled_node.outputs['BSDF'], output_node.inputs['Surface'])

    floor.data.materials.append(mat)

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.uv.smart_project()
    bpy.ops.object.mode_set(mode='OBJECT')

    floor.hide_select = True
    return floor

def create_skin_material():
    mat = bpy.data.materials.new(name="DarkBronzeSkinMaterial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    principled_bsdf = nodes.get("Principled BSDF")
    principled_bsdf.inputs['Base Color'].default_value = (0.3, 0.15, 0.07, 1) 
    principled_bsdf.inputs['Metallic'].default_value = 0.4 
    principled_bsdf.inputs['Roughness'].default_value = 0.6 
    

    return mat

def assign_material_to_obj(obj, mat):
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

def get_obj_world_center(obj):
    coords = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
    center = sum(coords, mathutils.Vector()) / 8
    result = mathutils.Vector((center.x, center.y, center.z))
    return result


def convert_objs_to_images(obj_folder, out_dir, view_idx):
    files = sorted(glob.glob(os.path.join(obj_folder, "frame*.obj")))

    scene = bpy.context.scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


    world = bpy.data.worlds["World"]
    world.use_nodes = True
    bg_node = world.node_tree.nodes["Background"]
    bg_node.inputs[0].default_value = (1.0, 1.0, 1.0, 1) 
    bg_node.inputs[1].default_value = 0.6

    floor_flag=False


    scene.render.image_settings.file_format = 'PNG' 
    scene.render.resolution_x = 1088
    scene.render.resolution_y = 1088

    light_data = bpy.data.lights.new(name="Sun", type='SUN')
    light = bpy.data.objects.new(name="Sun", object_data=light_data)
    light.data.energy = 4.5
    bpy.context.collection.objects.link(light)
    light.location = mathutils.Vector(VIEW_OFFSETS[view_idx]['light'])
    light.rotation_euler = (mathutils.Vector((0, 0, 0)) - light.location).to_track_quat('-Z', 'Y').to_euler()



    skin_mat = create_skin_material()
    for fp in files:
        name = os.path.splitext(os.path.basename(fp))[0]
        bpy.ops.wm.obj_import(filepath=fp)
        obj = bpy.data.objects[name]
        assign_material_to_obj(obj, skin_mat)

        if not floor_flag:
            add_chessboard_floor(z=min([v[1] for v in obj.bound_box]))
            floor_flag=True


        bpy.ops.object.select_by_type(type='CAMERA')
        bpy.ops.object.delete()
        bpy.ops.object.camera_add()
        camera = bpy.context.object
        center = get_obj_world_center(obj)
        camera.location = center + mathutils.Vector(VIEW_OFFSETS[view_idx]['cam'])
        direction = center - camera.location 
        camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        scene.camera = camera

        bpy.context.view_layer.update()
        
        scene.render.filepath = os.path.join(out_dir, f"{name}.png")
        bpy.ops.render.render(write_still=True)  
        bpy.data.objects.remove(obj, do_unlink=True)


def convert_images_to_video(image_dir,output_video,fps=30):
    
    image_paths = sorted(glob.glob(os.path.join(image_dir, "*.png")))
    if not image_paths:
        raise ValueError("Not PNG founded")
    
    writer = imageio.get_writer(output_video, fps=fps, codec='libx264', quality=9)
    for image_path in image_paths:
        writer.append_data(imageio.v3.imread(image_path))
    writer.close()

    print(f"Video saved to: {output_video}")

if __name__=='__main__':
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        raise "no valid argument"
    
    obj_folder = argv[0]
    
    view_idx = int(argv[1]) if len(argv)>1 else 0
    fps = 20
    print('obj_folder:',obj_folder)


    parent_name = os.path.dirname(obj_folder)
    assert os.path.basename(obj_folder).endswith('_obj')
    new_base_name = os.path.basename(obj_folder).replace('_obj',f'_viz#{view_idx}')
    image_dir = os.path.join(parent_name,new_base_name)
    output_video = f'{image_dir}.mp4'


    if not os.path.exists(output_video):
        shutil.rmtree(image_dir,ignore_errors=True)
        convert_objs_to_images(obj_folder,image_dir,view_idx)
        convert_images_to_video(image_dir,output_video,fps=fps)
    else:
        print(f'Skip existed video: {output_video}')

    shutil.rmtree(image_dir,ignore_errors=True)
    # shutil.rmtree(obj_folder)