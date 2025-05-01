import bpy
import os

# Configuration
mat_dir = r"D:\Unity\Packages\CSXfil assets"


def find_mat_file(base_name):
    """Recursively search mat_dir for base_name + '.mat'."""
    target = f"{base_name}.mat"
    for root, _, files in os.walk(mat_dir):
        if target in files:
            return os.path.join(root, target)
    return None


def find_texture_file(base_name):
    """
    Recursively search mat_dir for base_name + .png or .dds.
    Returns first hit it finds, or None.
    """
    for root, _, files in os.walk(mat_dir):
        for ext in ('.png', '.dds'):
            fname = base_name + ext
            if fname in files:
                return os.path.join(root, fname)
    return None


def ensure_nodes(mat):
    if not mat.use_nodes:
        mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    return nt


def assign_textures(mat):
    nt = ensure_nodes(mat)
    nodes = nt.nodes
    links = nt.links

    shader = nodes.new('ShaderNodeBsdfPrincipled')
    out = nodes.get("Material Output") or nodes.new("ShaderNodeOutputMaterial")

    base = mat.name.split('.')[0]
    mat_file = find_mat_file(base)
    if not mat_file:
        print(f".mat not found for '{mat.name}'")
        return

    diff_name = norm_name = None
    with open(mat_file, 'r') as f:
        for line in f:
            if line.startswith('Diffuse'):
                diff_name = line.split('=',1)[1].strip()
            elif line.startswith('Normal'):
                norm_name = line.split('=',1)[1].strip()

    # now use the NEW find_texture_file:
    if diff_name:
        p = find_texture_file(diff_name)
        if p:
            img = bpy.data.images.load(p)
            tn = nodes.new('ShaderNodeTexImage'); tn.image = img
            links.new(tn.outputs['Color'], shader.inputs['Base Color'])
        else:
            print(f"Diffuse '{diff_name}' not found anywhere under mat_dir.")

    if norm_name:
        p = find_texture_file(norm_name)
        if p:
            img = bpy.data.images.load(p)
            tn = nodes.new('ShaderNodeTexImage'); tn.image = img
            nm = nodes.new('ShaderNodeNormalMap')
            links.new(tn.outputs['Color'], nm.inputs['Color'])
            links.new(nm.outputs['Normal'], shader.inputs['Normal'])
        else:
            print(f"Normal '{norm_name}' not found anywhere under mat_dir.")

    links.new(shader.outputs['BSDF'], out.inputs['Surface'])


def dedup_materials(old_name, base_name):
    """
    Replace any slots using old_name with a single base_name material.
    Auto-creates base_name (with textures) if missing.
    """
    mats = bpy.data.materials
    rep = mats.get(base_name)
    if not rep:
        print(f"Creating base material '{base_name}'")
        rep = mats.new(name=base_name)
        rep.use_nodes = True
        assign_textures(rep)

    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH':
            continue
        for idx, slot in enumerate(obj.material_slots):
            if slot.material and slot.material.name == old_name:
                slot.material = rep
                print(f"Replaced '{old_name}' → '{base_name}' on {obj.name}[{idx}]")


def clean_objects_without_materials():
    for obj in list(bpy.context.scene.objects):
        if obj.type == 'MESH' and (not obj.material_slots or not any(s.material for s in obj.material_slots)):
            print(f"Removing {obj.name} (no materials)")
            bpy.data.objects.remove(obj, do_unlink=True)


# --- MAIN PROCESS ---
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH':
        continue
    for slot in obj.material_slots:
        mat = slot.material
        if not mat:
            continue
        # kill any grid materials
        if 'WorldGridMaterial' in mat.name:
            bpy.data.materials.remove(mat, do_unlink=True)
            continue

        parts = mat.name.split('.')
        if len(parts) > 1:
            dedup_materials(mat.name, parts[0])
            bpy.data.materials.remove(mat, do_unlink=True)
        else:
            assign_textures(mat)

clean_objects_without_materials()
print("Done.")
