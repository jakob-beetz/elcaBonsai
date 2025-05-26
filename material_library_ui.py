import bpy
import os
import ifcopenshell
from . import ifc_library_creator

class ELCA_OT_LoadMaterialLibrary(bpy.types.Operator):
    bl_idname = "elca.load_material_library"
    bl_label = "Load Material Library"
    bl_description = "Load material layer sets from an IFC library file"
    
    filepath: bpy.props.StringProperty(
        name="Library File",
        description="Path to the IFC library file",
        default="",
        subtype='FILE_PATH'
    )
    
    def execute(self, context):
        if not self.filepath:
            self.report({'ERROR'}, "No file selected")
            return {'CANCELLED'}
        
        # Store the library path in scene properties
        context.scene.elca_library_path = self.filepath
        
        # Load material sets from the library
        material_sets = ifc_library_creator.get_library_material_sets(self.filepath)
        
        # Clear existing items
        context.scene.elca_material_sets.clear()
        
        # Add items to the collection
        for mset in material_sets:
            item = context.scene.elca_material_sets.add()
            item.id = str(mset["id"])
            item.name = mset["name"]
            item.wall_type = mset["wall_type"] if mset["wall_type"] else ""
            
            # Add layer information
            layers_info = []
            for layer in mset["layers"]:
                thickness_mm = round(layer["thickness"] * 1000, 1)
                layers_info.append(f"{layer['material']} ({thickness_mm} mm)")
            
            item.layers = ", ".join(layers_info)
        
        self.report({'INFO'}, f"Loaded {len(material_sets)} material sets from library")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class ELCA_OT_ApplyMaterialSet(bpy.types.Operator):
    bl_idname = "elca.apply_material_set"
    bl_label = "Apply Material Set"
    bl_description = "Apply the selected material set to selected objects"
    
    def execute(self, context):
        # Get the selected material set
        if not context.scene.elca_material_sets or context.scene.elca_material_set_index < 0:
            self.report({'ERROR'}, "No material set selected")
            return {'CANCELLED'}
        
        # Get the selected material set
        material_set = context.scene.elca_material_sets[context.scene.elca_material_set_index]
        
        # Get selected objects
        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({'ERROR'}, "No objects selected")
            return {'CANCELLED'}
        
        # Apply the material set
        success = ifc_library_creator.apply_material_set_to_blender_objects(
            context.scene.elca_library_path,
            int(material_set.id),
            selected_objects
        )
        
        if success:
            self.report({'INFO'}, f"Applied material set '{material_set.name}' to {len(selected_objects)} objects")
            # Update the BlenderBIM display
            bpy.ops.bim.update_representation()
        else:
            self.report({'ERROR'}, "Failed to apply material set")
        
        return {'FINISHED'}
class ELCA_MaterialSetItem(bpy.types.PropertyGroup):
    id: bpy.props.StringProperty(name="ID")
    name: bpy.props.StringProperty(name="Name")
    wall_type: bpy.props.StringProperty(name="Wall Type")
    layers: bpy.props.StringProperty(name="Layers")

class ELCA_PT_MaterialLibraryPanel(bpy.types.Panel):
    bl_idname = "ELCA_PT_MaterialLibraryPanel"
    bl_label = "eLCA Material Library"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"
    
    def draw(self, context):
        layout = self.layout
        
        # Library file selection
        row = layout.row()
        row.prop(context.scene, "elca_library_path", text="Library")
        row.operator("elca.load_material_library", text="", icon='FILE_FOLDER')
        
        # Material sets list
        layout.label(text="Material Sets:")
        row = layout.row()
        row.template_list("UI_UL_list", "elca_material_sets", context.scene, 
                         "elca_material_sets", context.scene, "elca_material_set_index")
        
        # Show details of selected material set
        if context.scene.elca_material_sets and context.scene.elca_material_set_index >= 0:
            material_set = context.scene.elca_material_sets[context.scene.elca_material_set_index]
            
            box = layout.box()
            box.label(text=f"Name: {material_set.name}")
            if material_set.wall_type:
                box.label(text=f"Wall Type: {material_set.wall_type}")
            box.label(text="Layers:")
            box.label(text=material_set.layers)
            
            # Apply button
            layout.operator("elca.apply_material_set", icon='MATERIAL')

def register():
    bpy.utils.