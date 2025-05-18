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
from bpy.props import StringProperty, BoolProperty
from bpy.app.handlers import persistent
import traceback
import os
import tempfile
from pathlib import Path

print("\n[eLCA] Initializing eLCA Bonsai integration...")

# First, ensure dependencies are installed
from . import dependencies
dependencies_installed = dependencies.ensure_dependencies()

# Only import our modules if dependencies are installed
if dependencies_installed:
    # Import our modules
    from . import elca_parser
    from . import ifc_library_creator
else:
    # Create dummy modules for graceful failure
    class DummyModule:
        pass
    
    elca_parser = DummyModule()
    elca_parser.ELCAComponentExtractor = lambda *args, **kwargs: None
    
    ifc_library_creator = DummyModule()
    ifc_library_creator.create_ifc_library_from_bauteil_elements = lambda *args, **kwargs: None
    ifc_library_creator.attach_library_to_project = lambda *args, **kwargs: None

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
    """Load eLCA results from HTML file and create IFC material library"""
    bl_idname = "elca.load_results"
    bl_label = "Load eLCA Results"
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: StringProperty(
        name="File Path",
        description="Path to eLCA results HTML file",
        default="",
        subtype='FILE_PATH'
    )
    
    create_library: BoolProperty(
        name="Create IFC Library",
        description="Create an IFC material library from the results",
        default=True
    )
    
    attach_to_project: BoolProperty(
        name="Attach to Project",
        description="Attach the created library to the current IFC project",
        default=False
    )
    
    def execute(self, context):
        if not dependencies_installed:
            self.report({'ERROR'}, "Required dependencies are not installed. Check the console for details.")
            return {'CANCELLED'}
            
        try:
            print(f"[eLCA] Loading eLCA results from: {self.filepath}")
            
            # Extract components from HTML file
            extractor = elca_parser.ELCAComponentExtractor(self.filepath)
            bauteil_elements = extractor.extract_bauteil_elements()
            
            # Report the number of elements found
            num_elements = len(bauteil_elements)
            num_components = sum(len(element.components) for element in bauteil_elements)
            
            self.report({'INFO'}, f"Extracted {num_elements} building elements with {num_components} components")
            print(f"[eLCA] Extracted {num_elements} building elements with {num_components} components")
            
            # Create IFC library if requested
            if self.create_library and num_elements > 0:
                # Create output path in same directory as input file
                input_path = Path(self.filepath)
                output_path = input_path.with_suffix('.ifc')
                
                # Create the IFC library
                ifc_file = ifc_library_creator.create_ifc_library_from_bauteil_elements(
                    bauteil_elements, str(output_path))
                
                self.report({'INFO'}, f"Created IFC material library at {output_path}")
                print(f"[eLCA] Created IFC material library at {output_path}")
                
                # Attach to project if requested
                if self.attach_to_project:
                    # TODO: Get the current IFC project path
                    # For now, we'll just use a dummy path
                    project_path = context.scene.BIMProperties.ifc_file
                    
                    # Attach the library to the project
                    ifc_library_creator.attach_library_to_project(project_path, str(output_path))
                    
                    self.report({'INFO'}, f"Attached library to project at {project_path}")
                    print(f"[eLCA] Attached library to project at {project_path}")
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Error processing eLCA results: {str(e)}")
            print(f"[eLCA] Error processing eLCA results: {str(e)}")
            print(traceback.format_exc())
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        print("[eLCA] Opening file browser for eLCA results selection")
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class ELCA_OT_InstallDependencies(Operator):
    """Install required dependencies for eLCA integration"""
    bl_idname = "elca.install_dependencies"
    bl_label = "Install Dependencies"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        try:
            success = dependencies.ensure_dependencies()
            if success:
                self.report({'INFO'}, "All dependencies successfully installed")
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "Failed to install some dependencies. Check the console for details.")
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error installing dependencies: {str(e)}")
            print(f"[eLCA] Error installing dependencies: {str(e)}")
            print(traceback.format_exc())
            return {'CANCELLED'}

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
        
        # Show dependency status
        if not dependencies_installed:
            box.label(text="Dependencies not installed", icon='ERROR')
            box.operator("elca.install_dependencies", icon='PACKAGE')
        else:
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
        # print(f"[eLCA] Drawing eLCA UI in {self.__class__.__name__}")
        layout = self.layout
        
        box = layout.box()
        box.label(text="eLCA Integration", icon='FILE_REFRESH')
        
        # Show dependency status
        if not dependencies_installed:
            box.label(text="Dependencies not installed", icon='ERROR')
            box.operator("elca.install_dependencies", icon='PACKAGE')
        else:
            box.label(text="Load eLCA project and results files:")
            
            row = box.row()
            row.operator("elca.load_project", text="Load Project", icon='IMPORT')
            
            row = box.row()
            row.operator("elca.load_results", text="Load Results", icon='SPREADSHEET')
        
        # print(f"[eLCA] Successfully drew UI in {self.__class__.__name__}")
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
    # for i, cls in enumerate(bpy.types.Panel.__subclasses__()):
    #     if hasattr(cls, '__module__'):
    #         print(f"  {i+1}. {cls.__module__}.{cls.__name__}")
    
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