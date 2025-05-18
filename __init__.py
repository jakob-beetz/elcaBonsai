# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import bpy
from bpy.types import Operator, Panel
from bpy.props import StringProperty
from bpy.app.handlers import persistent
import traceback

bl_info = {
    "name": "Elca Bonsai",
    "author": "Jakob Beetz",
    "description": "Integration of eLCA data into Blender Bonsai",
    "blender": (2, 80, 0),
    "version": (0, 0, 1),
    "location": "Bonsai > GEOMETRY tab > eLCA",
    "warning": "",
    "category": "Generic",
}

print("\n[eLCA] Initializing eLCA Bonsai integration...")

class ELCA_OT_LoadProject(Operator):
    """Load eLCA project file"""
    bl_idname = "elca.load_project"
    bl_label = "Load eLCA Project"
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: StringProperty(
        name="File Path",
        description="Path to eLCA project file",
        default="",
        subtype='FILE_PATH'
    )
    
    def execute(self, context):
        print(f"[eLCA] Loading eLCA project from: {self.filepath}")
        self.report({'INFO'}, f"Loading eLCA project from: {self.filepath}")
        # TODO: Implement actual loading functionality
        return {'FINISHED'}
    
    def invoke(self, context, event):
        print("[eLCA] Opening file browser for eLCA project selection")
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class ELCA_OT_LoadResults(Operator):
    """Load eLCA results"""
    bl_idname = "elca.load_results"
    bl_label = "Load eLCA Results"
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: StringProperty(
        name="File Path",
        description="Path to eLCA results file",
        default="",
        subtype='FILE_PATH'
    )
    
    def execute(self, context):
        print(f"[eLCA] Loading eLCA results from: {self.filepath}")
        self.report({'INFO'}, f"Loading eLCA results from: {self.filepath}")
        # TODO: Implement actual loading functionality
        return {'FINISHED'}
    
    def invoke(self, context, event):
        print("[eLCA] Opening file browser for eLCA results selection")
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

# Create our own panel as a fallback
class ELCA_PT_Panel(Panel):
    """eLCA Panel"""
    bl_label = "eLCA Integration"
    bl_idname = "ELCA_PT_Panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"
    
    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        box.label(text="eLCA Integration", icon='FILE_REFRESH')
        
        box.label(text="Load eLCA project and results files:")
        
        row = box.row()
        row.operator("elca.load_project", text="Load Project", icon='IMPORT')
        
        row = box.row()
        row.operator("elca.load_results", text="Load Results", icon='SPREADSHEET')

# Store original draw functions
_original_draw_functions = {}

# Draw function for the BIM panel
def draw_elca_ui(self, context):
    try:
        print(f"[eLCA] Drawing eLCA UI in {self.__class__.__name__}")
        layout = self.layout
        
        box = layout.box()
        box.label(text="eLCA Integration", icon='FILE_REFRESH')
        
        box.label(text="Load eLCA project and results files:")
        
        row = box.row()
        row.operator("elca.load_project", text="Load Project", icon='IMPORT')
        
        row = box.row()
        row.operator("elca.load_results", text="Load Results", icon='SPREADSHEET')
        
        print(f"[eLCA] Successfully drew UI in {self.__class__.__name__}")
    except Exception as e:
        print(f"[eLCA] Error in draw_elca_ui: {e}")
        print(traceback.format_exc())

# Function to monkey patch a panel's draw method
def monkey_patch_panel(panel_class, panel_name):
    if panel_name not in _original_draw_functions:
        print(f"[eLCA] Storing original draw function for {panel_name}")
        _original_draw_functions[panel_name] = panel_class.draw
    
    def new_draw(self, context):
        try:
            # Draw our UI first
            draw_elca_ui(self, context)
            # Then call the original draw function
            if panel_name in _original_draw_functions:
                _original_draw_functions[panel_name](self, context)
        except Exception as e:
            print(f"[eLCA] Error in monkey-patched draw function for {panel_name}: {e}")
            print(traceback.format_exc())
            # Fallback to original draw if our addition fails
            if panel_name in _original_draw_functions:
                _original_draw_functions[panel_name](self, context)
    
    print(f"[eLCA] Setting new draw function for {panel_name}")
    panel_class.draw = new_draw

# Persistent handler to add our UI elements after file load
@persistent
def load_handler(dummy):
    print("\n[eLCA] Load handler triggered")
    
    # List all panel classes for debugging
    print("[eLCA] Available Panel classes:")
    for i, cls in enumerate(bpy.types.Panel.__subclasses__()):
        if hasattr(cls, '__module__'):
            print(f"  {i+1}. {cls.__module__}.{cls.__name__}")
    
    # Target panel classes to try
    target_panel_classes = [
        "bonsai.bim.module.material.ui.BIM_PT_materials",
        "bonsai.bim.module.material.ui.BIM_PT_object_material",
    ]
    
    found_panel = False
    
    for target_panel_name in target_panel_classes:
        try:
            panel_class = None
            for cls in bpy.types.Panel.__subclasses__():
                if hasattr(cls, '__module__') and f"{cls.__module__}.{cls.__name__}" == target_panel_name:
                    panel_class = cls
                    break
            
            if panel_class:
                print(f"[eLCA] Found panel: {target_panel_name}")
                monkey_patch_panel(panel_class, target_panel_name)
                print(f"[eLCA] Added eLCA UI to {target_panel_name} panel")
                found_panel = True
                break  # Stop after finding one panel
            else:
                print(f"[eLCA] Panel not found: {target_panel_name}")
        
        except Exception as e:
            print(f"[eLCA] Error processing panel {target_panel_name}: {e}")
            print(traceback.format_exc())
    
    if not found_panel:
        print("[eLCA] Could not find any target panels. Using fallback panel.")

def register():
    print("\n[eLCA] Registering eLCA Bonsai integration...")
    
    try:
        bpy.utils.register_class(ELCA_OT_LoadProject)
        print("[eLCA] Registered ELCA_OT_LoadProject")
    except Exception as e:
        print(f"[eLCA] Error registering ELCA_OT_LoadProject: {e}")
    
    try:
        bpy.utils.register_class(ELCA_OT_LoadResults)
        print("[eLCA] Registered ELCA_OT_LoadResults")
    except Exception as e:
        print(f"[eLCA] Error registering ELCA_OT_LoadResults: {e}")
    
    try:
        bpy.utils.register_class(ELCA_PT_Panel)
        print("[eLCA] Registered ELCA_PT_Panel (fallback panel)")
    except Exception as e:
        print(f"[eLCA] Error registering ELCA_PT_Panel: {e}")
    
    # Add our load handler
    if load_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(load_handler)
        print("[eLCA] Added load_handler to load_post")
    
    # Run the load handler immediately
    load_handler(None)
    
    print("[eLCA] Registration complete")

def unregister():
    print("\n[eLCA] Unregistering eLCA Bonsai integration...")
    
    # Restore original draw functions
    for panel_name, original_draw in _original_draw_functions.items():
        try:
            panel_class = None
            for cls in bpy.types.Panel.__subclasses__():
                if hasattr(cls, '__module__') and f"{cls.__module__}.{cls.__name__}" == panel_name:
                    panel_class = cls
                    break
            
            if panel_class:
                panel_class.draw = original_draw
                print(f"[eLCA] Restored original draw function for {panel_name}")
        except Exception as e:
            print(f"[eLCA] Error restoring draw function for {panel_name}: {e}")
    
    # Remove load handler
    if load_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_handler)
        print("[eLCA] Removed load_handler from load_post")
    
    try:
        bpy.utils.unregister_class(ELCA_PT_Panel)
        print("[eLCA] Unregistered ELCA_PT_Panel")
    except Exception as e:
        print(f"[eLCA] Error unregistering ELCA_PT_Panel: {e}")
    
    try:
        bpy.utils.unregister_class(ELCA_OT_LoadResults)
        print("[eLCA] Unregistered ELCA_OT_LoadResults")
    except Exception as e:
        print(f"[eLCA] Error unregistering ELCA_OT_LoadResults: {e}")
    
    try:
        bpy.utils.unregister_class(ELCA_OT_LoadProject)
        print("[eLCA] Unregistered ELCA_OT_LoadProject")
    except Exception as e:
        print(f"[eLCA] Error unregistering ELCA_OT_LoadProject: {e}")
    
    print("[eLCA] Unregistration complete")

if __name__ == "__main__":
    print("[eLCA] Running as main script")
    register()