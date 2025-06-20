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
import ifcopenshell
import traceback
from typing import Optional, List, Dict, Any

def get_active_ifc_file():
    """Get the active IFC file from BlenderBIM"""
    try:
        import bonsai.tool as tool
        return tool.Ifc.get()
    except:
        try:
            # Fallback method
            if hasattr(bpy.context.scene, 'BIMProperties') and bpy.context.scene.BIMProperties.ifc_file:
                return ifcopenshell.open(bpy.context.scene.BIMProperties.ifc_file)
        except:
            pass
    return None

def add_material_sets_to_project(source_ifc_file=None) -> None:
    """Add IfcMaterialLayerSets and IfcMaterialConstituentsSets to the active project
    
    Args:
        source_ifc_file: Optional source IFC file to copy material sets from
    """
    
    # Get the active project's IFC file
    active_ifc = get_active_ifc_file()
    
    if not active_ifc:
        print("[eLCA] No active IFC file found in project")
        return
    
    # Use source file if provided, otherwise use active file
    ifc_file = source_ifc_file if source_ifc_file else active_ifc
    
    if not ifc_file:
        print("[eLCA] No IFC file available")
        return
    
    try:
        # Get material layer sets and constituent sets
        material_layer_sets = ifc_file.by_type("IfcMaterialLayerSet")
        material_constituent_sets = ifc_file.by_type("IfcMaterialConstituentSet")
        
        print(f"[eLCA] Found {len(material_layer_sets)} material layer sets")
        print(f"[eLCA] Found {len(material_constituent_sets)} material constituent sets")
        
        # If we're copying from a source file, we need to copy the entities
        if source_ifc_file and source_ifc_file != active_ifc:
            # Copy material layer sets
            for layer_set in material_layer_sets:
                copy_material_layer_set_to_project(layer_set, source_ifc_file, active_ifc)
            
            # Copy material constituent sets
            for constituent_set in material_constituent_sets:
                copy_material_constituent_set_to_project(constituent_set, source_ifc_file, active_ifc)
        else:
            # Add material layer sets to Blender materials
            for layer_set in material_layer_sets:
                add_material_layer_set_to_blender(layer_set)
            
            # Add material constituent sets to Blender materials
            for constituent_set in material_constituent_sets:
                add_material_constituent_set_to_blender(constituent_set)
        
        # Refresh the BlenderBIM interface
        refresh_bim_interface()
        
        print("[eLCA] Successfully added material sets to project")
        
    except Exception as e:
        print(f"[eLCA] Error adding material sets to project: {str(e)}")
        traceback.print_exc()

def copy_material_layer_set_to_project(layer_set, source_ifc, target_ifc):
    """Copy a material layer set from source IFC to target IFC"""
    try:
        # Check if it already exists
        existing_sets = [ls for ls in target_ifc.by_type("IfcMaterialLayerSet") 
                        if getattr(ls, 'LayerSetName', None) == getattr(layer_set, 'LayerSetName', None)]
        
        if existing_sets:
            print(f"[eLCA] Material layer set '{getattr(layer_set, 'LayerSetName', 'Unnamed')}' already exists")
            return existing_sets[0]
        
        # Copy materials first
        copied_materials = {}
        if hasattr(layer_set, 'MaterialLayers') and layer_set.MaterialLayers:
            for layer in layer_set.MaterialLayers:
                if layer.Material and layer.Material not in copied_materials:
                    copied_material = copy_material_to_project(layer.Material, source_ifc, target_ifc)
                    copied_materials[layer.Material] = copied_material
        
        # Create new material layer set in target IFC
        new_layer_set = target_ifc.create_entity("IfcMaterialLayerSet")
        
        # Copy basic properties
        if hasattr(layer_set, 'LayerSetName') and layer_set.LayerSetName:
            new_layer_set.LayerSetName = layer_set.LayerSetName
        if hasattr(layer_set, 'Description') and layer_set.Description:
            new_layer_set.Description = layer_set.Description
        
        # Copy layers
        if hasattr(layer_set, 'MaterialLayers') and layer_set.MaterialLayers:
            new_layers = []
            for layer in layer_set.MaterialLayers:
                new_layer = target_ifc.create_entity("IfcMaterialLayer")
                
                # Copy layer properties
                if hasattr(layer, 'LayerThickness'):
                    new_layer.LayerThickness = layer.LayerThickness
                if hasattr(layer, 'IsVentilated'):
                    new_layer.IsVentilated = layer.IsVentilated
                if hasattr(layer, 'Name') and layer.Name:
                    new_layer.Name = layer.Name
                if hasattr(layer, 'Description') and layer.Description:
                    new_layer.Description = layer.Description
                if hasattr(layer, 'Category') and layer.Category:
                    new_layer.Category = layer.Category
                if hasattr(layer, 'Priority'):
                    new_layer.Priority = layer.Priority
                
                # Assign copied material
                if layer.Material and layer.Material in copied_materials:
                    new_layer.Material = copied_materials[layer.Material]
                
                new_layers.append(new_layer)
            
            new_layer_set.MaterialLayers = new_layers
        
        # Create corresponding Blender material
        add_material_layer_set_to_blender(new_layer_set)
        
        print(f"[eLCA] Copied material layer set: {getattr(new_layer_set, 'LayerSetName', 'Unnamed')}")
        return new_layer_set
        
    except Exception as e:
        print(f"[eLCA] Error copying material layer set: {str(e)}")
        traceback.print_exc()
        return None

def copy_material_constituent_set_to_project(constituent_set, source_ifc, target_ifc):
    """Copy a material constituent set from source IFC to target IFC"""
    try:
        # Check if it already exists
        existing_sets = [cs for cs in target_ifc.by_type("IfcMaterialConstituentSet") 
                        if getattr(cs, 'Name', None) == getattr(constituent_set, 'Name', None)]
        
        if existing_sets:
            print(f"[eLCA] Material constituent set '{getattr(constituent_set, 'Name', 'Unnamed')}' already exists")
            return existing_sets[0]
        
        # Copy materials first
        copied_materials = {}
        if hasattr(constituent_set, 'MaterialConstituents') and constituent_set.MaterialConstituents:
            for constituent in constituent_set.MaterialConstituents:
                if constituent.Material and constituent.Material not in copied_materials:
                    copied_material = copy_material_to_project(constituent.Material, source_ifc, target_ifc)
                    copied_materials[constituent.Material] = copied_material
        
        # Create new material constituent set in target IFC
        new_constituent_set = target_ifc.create_entity("IfcMaterialConstituentSet")
        
        # Copy basic properties
        if hasattr(constituent_set, 'Name') and constituent_set.Name:
            new_constituent_set.Name = constituent_set.Name
        if hasattr(constituent_set, 'Description') and constituent_set.Description:
            new_constituent_set.Description = constituent_set.Description
        
        # Copy constituents
        if hasattr(constituent_set, 'MaterialConstituents') and constituent_set.MaterialConstituents:
            new_constituents = []
            for constituent in constituent_set.MaterialConstituents:
                new_constituent = target_ifc.create_entity("IfcMaterialConstituent")
                
                # Copy constituent properties
                if hasattr(constituent, 'Name') and constituent.Name:
                    new_constituent.Name = constituent.Name
                if hasattr(constituent, 'Description') and constituent.Description:
                    new_constituent.Description = constituent.Description
                if hasattr(constituent, 'Fraction'):
                    new_constituent.Fraction = constituent.Fraction
                if hasattr(constituent, 'Category') and constituent.Category:
                    new_constituent.Category = constituent.Category
                
                # Assign copied material
                if constituent.Material and constituent.Material in copied_materials:
                    new_constituent.Material = copied_materials[constituent.Material]
                
                new_constituents.append(new_constituent)
            
            new_constituent_set.MaterialConstituents = new_constituents
        
        # Create corresponding Blender material
        add_material_constituent_set_to_blender(new_constituent_set)
        
        print(f"[eLCA] Copied material constituent set: {getattr(new_constituent_set, 'Name', 'Unnamed')}")
        return new_constituent_set
        
    except Exception as e:
        print(f"[eLCA] Error copying material constituent set: {str(e)}")
        traceback.print_exc()
        return None

def copy_material_to_project(material, source_ifc, target_ifc):
    """Copy a material from source IFC to target IFC"""
    try:
        # Check if material already exists
        existing_materials = [m for m in target_ifc.by_type("IfcMaterial") 
                             if getattr(m, 'Name', None) == getattr(material, 'Name', None)]
        
        if existing_materials:
            return existing_materials[0]
        
        # Create new material
        new_material = target_ifc.create_entity("IfcMaterial")
        
        # Copy properties
        if hasattr(material, 'Name') and material.Name:
            new_material.Name = material.Name
        if hasattr(material, 'Description') and material.Description:
            new_material.Description = material.Description
        if hasattr(material, 'Category') and material.Category:
            new_material.Category = material.Category
        
        return new_material
        
    except Exception as e:
        print(f"[eLCA] Error copying material: {str(e)}")
        return None

def add_material_layer_set_to_blender(layer_set):
    """Add a material layer set to Blender materials"""
    try:
        # Get or create material set name
        set_name = getattr(layer_set, 'LayerSetName', None) or f"MaterialLayerSet_{layer_set.id()}"
        
        # Check if material set already exists
        if set_name in bpy.data.materials:
            print(f"[eLCA] Material layer set '{set_name}' already exists in Blender, skipping")
            return
        
        # Create a new material for the layer set
        mat = bpy.data.materials.new(name=set_name)
        mat.use_nodes = True
        
        # Add custom properties to store IFC data
        mat["ifc_type"] = "IfcMaterialLayerSet"
        mat["ifc_id"] = layer_set.id()
        
        # Process individual layers
        if hasattr(layer_set, 'MaterialLayers') and layer_set.MaterialLayers:
            layer_info = []
            total_thickness = 0.0
            
            for i, layer in enumerate(layer_set.MaterialLayers):
                layer_thickness = getattr(layer, 'LayerThickness', 0.0)
                total_thickness += layer_thickness
                
                layer_data = {
                    'name': getattr(layer.Material, 'Name', f'Layer_{i}') if layer.Material else f'Layer_{i}',
                    'thickness': layer_thickness,
                    'category': getattr(layer.Material, 'Category', '') if layer.Material else '',
                    'description': getattr(layer.Material, 'Description', '') if layer.Material else ''
                }
                layer_info.append(layer_data)
            
            # Store layer information as custom properties
            mat["layer_info"] = str(layer_info)
            mat["total_thickness"] = total_thickness
            mat["layer_count"] = len(layer_info)
            
        print(f"[eLCA] Added material layer set to Blender: {set_name}")
        
    except Exception as e:
        print(f"[eLCA] Error adding material layer set to Blender: {str(e)}")
        traceback.print_exc()

def add_material_constituent_set_to_blender(constituent_set):
    """Add a material constituent set to Blender materials"""
    try:
        # Get or create material set name
        set_name = getattr(constituent_set, 'Name', None) or f"MaterialConstituentSet_{constituent_set.id()}"
        
        # Check if material set already exists
        if set_name in bpy.data.materials:
            print(f"[eLCA] Material constituent set '{set_name}' already exists in Blender, skipping")
            return
        
        # Create a new material for the constituent set
        mat = bpy.data.materials.new(name=set_name)
        mat.use_nodes = True
        
        # Add custom properties to store IFC data
        mat["ifc_type"] = "IfcMaterialConstituentSet"
        mat["ifc_id"] = constituent_set.id()
        
        # Process individual constituents
        if hasattr(constituent_set, 'MaterialConstituents') and constituent_set.MaterialConstituents:
            constituent_info = []
            total_fraction = 0.0
            
            for i, constituent in enumerate(constituent_set.MaterialConstituents):
                fraction = getattr(constituent, 'Fraction', 0.0)
                total_fraction += fraction
                
                constituent_data = {
                    'name': getattr(constituent, 'Name', f'Constituent_{i}'),
                    'material_name': getattr(constituent.Material, 'Name', '') if constituent.Material else '',
                    'fraction': fraction,
                    'category': getattr(constituent.Material, 'Category', '') if constituent.Material else '',
                    'description': getattr(constituent.Material, 'Description', '') if constituent.Material else ''
                }
                constituent_info.append(constituent_data)
            
            # Store constituent information as custom properties
            mat["constituent_info"] = str(constituent_info)
            mat["total_fraction"] = total_fraction
            mat["constituent_count"] = len(constituent_info)
            
        print(f"[eLCA] Added material constituent set to Blender: {set_name}")
        
    except Exception as e:
        print(f"[eLCA] Error adding material constituent set to Blender: {str(e)}")
        traceback.print_exc()

def refresh_bim_interface():
    """Refresh the BlenderBIM interface to show new materials"""
    try:
        # Try to refresh BlenderBIM materials
        import bonsai.tool as tool
        if hasattr(tool, 'Material'):
            # Force refresh of material data
            for area in bpy.context.screen.areas:
                if area.type == 'PROPERTIES':
                    area.tag_redraw()
        
        # Also refresh the 3D viewport
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
                
        print("[eLCA] Refreshed BlenderBIM interface")
        
    except Exception as e:
        print(f"[eLCA] Could not refresh BlenderBIM interface: {str(e)}")

def add_material_sets_from_library_file(library_file_path: str) -> None:
    """Add material sets from an IFC library file to the active project
    
    Args:
        library_file_path: Path to the IFC library file
    """
    try:
        # Open the library file
        library_ifc = ifcopenshell.open(library_file_path)
        
        # Add material sets from the library to the active project
        add_material_sets_to_project(library_ifc)
        
        print(f"[eLCA] Added material sets from library: {library_file_path}")
        
    except Exception as e:
        print(f"[eLCA] Error adding material sets from library: {str(e)}")
        traceback.print_exc()

def update_material_sets_in_project(elca_data: Optional[Dict[str, Any]] = None) -> None:
    """Update existing material sets with new eLCA data
    
    Args:
        elca_data: Optional dictionary containing eLCA data for updates
    """
    try:
        # Get all materials with IFC material set types
        ifc_materials = [mat for mat in bpy.data.materials 
                        if "ifc_type" in mat and mat["ifc_type"] in ["IfcMaterialLayerSet", "IfcMaterialConstituentSet"]]
        
        print(f"[eLCA] Found {len(ifc_materials)} existing IFC material sets to update")
        
        # Update each material with new eLCA data if available
        for mat in ifc_materials:
            if elca_data:
                update_material_with_elca_data(mat, elca_data)
            
    except Exception as e:
        print(f"[eLCA] Error updating material sets: {str(e)}")
        traceback.print_exc()

def update_material_with_elca_data(material, elca_data: Dict[str, Any]) -> None:
    """Update a single material with eLCA data
    
    Args:
        material: The Blender material to update
        elca_data: Dictionary containing eLCA data
    """
    try:
        material_name = material.name
        ifc_id = material.get("ifc_id")
        
        # Look for matching eLCA data
        if material_name in elca_data or str(ifc_id) in elca_data:
            data_key = material_name if material_name in elca_data else str(ifc_id)
            material_elca_data = elca_data[data_key]
            
            # Add eLCA properties
            for key, value in material_elca_data.items():
                material[f"elca_{key}"] = value
            
            print(f"[eLCA] Updated material '{material_name}' with eLCA data")
            
    except Exception as e:
        print(f"[eLCA] Error updating material with eLCA data: {str(e)}")

def get_material_sets_summary() -> Dict[str, Any]:
    """Get a summary of all material sets in the project
    
    Returns:
        Dictionary containing summary information about material sets
    """
    try:
        layer_sets = []
        constituent_sets = []
        
        for mat in bpy.data.materials:
            if "ifc_type" not in mat:
                continue
                
            if mat["ifc_type"] == "IfcMaterialLayerSet":
                layer_sets.append({
                    'name': mat.name,
                    'ifc_id': mat.get("ifc_id"),
                    'layer_count': mat.get("layer_count", 0),
                    'total_thickness': mat.get("total_thickness", 0.0)
                })
            elif mat["ifc_type"] == "IfcMaterialConstituentSet":
                constituent_sets.append({
                    'name': mat.name,
                    'ifc_id': mat.get("ifc_id"),
                    'constituent_count': mat.get("constituent_count", 0),
                    'total_fraction': mat.get("total_fraction", 0.0)
                })
        
        return {
            'layer_sets': layer_sets,
            'constituent_sets': constituent_sets,
            'total_layer_sets': len(layer_sets),
            'total_constituent_sets': len(constituent_sets)
        }
        
    except Exception as e:
        print(f"[eLCA] Error getting material sets summary: {str(e)}")
        return {}

def remove_material_sets_from_project(material_type: Optional[str] = None) -> None:
    """Remove material sets from the project
    
    Args:
        material_type: Optional type filter ("IfcMaterialLayerSet" or "IfcMaterialConstituentSet")
                      If None, removes all material sets
    """
    try:
        materials_to_remove = []
        
        for mat in bpy.data.materials:
            if "ifc_type" not in mat:
                continue
                
            if material_type is None or mat["ifc_type"] == material_type:
                materials_to_remove.append(mat)
        
        for mat in materials_to_remove:
            print(f"[eLCA] Removing material set: {mat.name}")
            bpy.data.materials.remove(mat)
        
        print(f"[eLCA] Removed {len(materials_to_remove)} material sets")
        
        # Refresh interface after removal
        refresh_bim_interface()
        
    except Exception as e:
        print(f"[eLCA] Error removing material sets: {str(e)}")
        traceback.print_exc()

def validate_material_sets() -> List[Dict[str, Any]]:
    """Validate material sets and return any issues found
    
    Returns:
        List of dictionaries containing validation issues
    """
    issues = []
    
    try:
        for mat in bpy.data.materials:
            if "ifc_type" not in mat:
                continue
            
            material_issues = []
            
            # Check for required properties
            if "ifc_id" not in mat:
                material_issues.append("Missing IFC ID")
            
            if mat["ifc_type"] == "IfcMaterialLayerSet":
                if "layer_info" not in mat:
                    material_issues.append("Missing layer information")
                elif mat.get("layer_count", 0) == 0:
                    material_issues.append("No layers defined")
                    
            elif mat["ifc_type"] == "IfcMaterialConstituentSet":
                if "constituent_info" not in mat:
                    material_issues.append("Missing constituent information")
                elif mat.get("constituent_count", 0) == 0:
                    material_issues.append("No constituents defined")
            
            if material_issues:
                issues.append({
                    'material_name': mat.name,
                    'material_type': mat["ifc_type"],
                    'issues': material_issues
                })
        
        return issues
        
    except Exception as e:
        print(f"[eLCA] Error validating material sets: {str(e)}")
        return [{'error': str(e)}]

def sync_material_sets_with_ifc():
    """Synchronize Blender material sets with the active IFC file"""
    try:
        active_ifc = get_active_ifc_file()
        if not active_ifc:
            print("[eLCA] No active IFC file found")
            return False
        
        # Get existing material sets from IFC
        ifc_layer_sets = active_ifc.by_type("IfcMaterialLayerSet")
        ifc_constituent_sets = active_ifc.by_type("IfcMaterialConstituentSet")
        
        print(f"[eLCA] Found {len(ifc_layer_sets)} layer sets and {len(ifc_constituent_sets)} constituent sets in IFC")
        
        # Create Blender materials for any missing IFC material sets
        for layer_set in ifc_layer_sets:
            add_material_layer_set_to_blender(layer_set)
        
        for constituent_set in ifc_constituent_sets:
            add_material_constituent_set_to_blender(constituent_set)
        
        # Remove Blender materials that no longer exist in IFC
        cleanup_orphaned_material_sets(active_ifc)
        
        refresh_bim_interface()
        
        print("[eLCA] Synchronized material sets with IFC file")
        return True
        
    except Exception as e:
        print(f"[eLCA] Error synchronizing material sets: {str(e)}")
        traceback.print_exc()
        return False

def cleanup_orphaned_material_sets(active_ifc):
    """Remove Blender materials that don't exist in the IFC file"""
    try:
        # Get all IFC IDs from the active file
        ifc_ids = set()
        for entity in active_ifc.by_type("IfcMaterialLayerSet") + active_ifc.by_type("IfcMaterialConstituentSet"):
            ifc_ids.add(entity.id())
        
        # Check Blender materials
        materials_to_remove = []
        for mat in bpy.data.materials:
            if "ifc_type" in mat and "ifc_id" in mat:
                if mat["ifc_id"] not in ifc_ids:
                    materials_to_remove.append(mat)
        
        # Remove orphaned materials
        for mat in materials_to_remove:
            print(f"[eLCA] Removing orphaned material: {mat.name}")
            bpy.data.materials.remove(mat)
        
        if materials_to_remove:
            print(f"[eLCA] Cleaned up {len(materials_to_remove)} orphaned materials")
            
    except Exception as e:

        print(f"[eLCA] Error cleaning up orphaned materials: {str(e)}")

def create_material_from_elca_component(component_data: Dict[str, Any]) -> Optional[str]:
    """Create a Blender material from eLCA component data
    
    Args:
        component_data: Dictionary containing eLCA component information
        
    Returns:
        Name of the created material or None if creation failed
    """
    try:
        # Extract component information
        component_name = component_data.get('name', 'Unknown Component')
        component_type = component_data.get('type', 'Unknown')
        
        # Create unique material name
        material_name = f"eLCA_{component_name}_{component_type}"
        
        # Check if material already exists
        if material_name in bpy.data.materials:
            print(f"[eLCA] Material '{material_name}' already exists, updating")
            mat = bpy.data.materials[material_name]
        else:
            # Create new material
            mat = bpy.data.materials.new(name=material_name)
            mat.use_nodes = True
            print(f"[eLCA] Created new material: {material_name}")
        
        # Add eLCA properties
        mat["elca_component"] = True
        mat["elca_name"] = component_name
        mat["elca_type"] = component_type
        
        # Add environmental data if available
        if 'environmental_data' in component_data:
            env_data = component_data['environmental_data']
            for key, value in env_data.items():
                mat[f"elca_{key}"] = value
        
        # Add material properties if available
        if 'properties' in component_data:
            props = component_data['properties']
            for key, value in props.items():
                mat[f"prop_{key}"] = value
        
        return material_name
        
    except Exception as e:
        print(f"[eLCA] Error creating material from eLCA component: {str(e)}")
        traceback.print_exc()
        return None

def create_material_layer_set_from_elca_element(element_data: Dict[str, Any]) -> Optional[str]:
    """Create a material layer set from eLCA building element data
    
    Args:
        element_data: Dictionary containing eLCA building element information
        
    Returns:
        Name of the created material layer set or None if creation failed
    """
    try:
        element_name = element_data.get('name', 'Unknown Element')
        components = element_data.get('components', [])
        
        if not components:
            print(f"[eLCA] No components found for element: {element_name}")
            return None
        
        # Create material layer set name
        layer_set_name = f"eLCA_LayerSet_{element_name}"
        
        # Check if material already exists
        if layer_set_name in bpy.data.materials:
            print(f"[eLCA] Material layer set '{layer_set_name}' already exists, updating")
            mat = bpy.data.materials[layer_set_name]
        else:
            # Create new material
            mat = bpy.data.materials.new(name=layer_set_name)
            mat.use_nodes = True
            print(f"[eLCA] Created new material layer set: {layer_set_name}")
        
        # Add eLCA properties
        mat["elca_element"] = True
        mat["elca_element_name"] = element_name
        mat["ifc_type"] = "IfcMaterialLayerSet"
        
        # Process components as layers
        layer_info = []
        total_thickness = 0.0
        
        for i, component in enumerate(components):
            component_name = component.get('name', f'Layer_{i}')
            thickness = component.get('thickness', 0.0)
            total_thickness += thickness
            
            layer_data = {
                'name': component_name,
                'thickness': thickness,
                'category': component.get('category', ''),
                'description': component.get('description', ''),
                'elca_type': component.get('type', '')
            }
            layer_info.append(layer_data)
            
            # Add environmental data
            if 'environmental_data' in component:
                env_data = component['environmental_data']
                for key, value in env_data.items():
                    layer_data[f"elca_{key}"] = value
        
        # Store layer information as custom properties
        mat["layer_info"] = str(layer_info)
        mat["total_thickness"] = total_thickness
        mat["layer_count"] = len(layer_info)
        
        # Add element-level environmental data if available
        if 'environmental_data' in element_data:
            env_data = element_data['environmental_data']
            for key, value in env_data.items():
                mat[f"elca_total_{key}"] = value
        
        return layer_set_name
        
    except Exception as e:
        print(f"[eLCA] Error creating material layer set from eLCA element: {str(e)}")
        traceback.print_exc()
        return None

def export_material_sets_to_ifc(output_path: str) -> bool:
    """Export Blender material sets to an IFC file
    
    Args:
        output_path: Path where to save the IFC file
        
    Returns:
        True if export was successful, False otherwise
    """
    try:
        # Create a new IFC file
        ifc_file = ifcopenshell.file()
        
        # Add basic IFC structure
        create_basic_ifc_structure(ifc_file)
        
        # Get all material sets from Blender
        layer_sets = []
        constituent_sets = []
        
        for mat in bpy.data.materials:
            if "ifc_type" not in mat:
                continue
                
            if mat["ifc_type"] == "IfcMaterialLayerSet":
                layer_sets.append(mat)
            elif mat["ifc_type"] == "IfcMaterialConstituentSet":
                constituent_sets.append(mat)
        
        print(f"[eLCA] Exporting {len(layer_sets)} layer sets and {len(constituent_sets)} constituent sets")
        
        # Export material layer sets
        for mat in layer_sets:
            export_material_layer_set_to_ifc(mat, ifc_file)
        
        # Export material constituent sets
        for mat in constituent_sets:
            export_material_constituent_set_to_ifc(mat, ifc_file)
        
        # Write the IFC file
        ifc_file.write(output_path)
        print(f"[eLCA] Exported material sets to: {output_path}")
        
        return True
        
    except Exception as e:
        print(f"[eLCA] Error exporting material sets to IFC: {str(e)}")
        traceback.print_exc()
        return False

def create_basic_ifc_structure(ifc_file):
    """Create basic IFC file structure"""
    try:
        # Create basic entities required for IFC file
        person = ifc_file.create_entity("IfcPerson")
        person.FamilyName = "eLCA"
        person.GivenName = "Integration"
        
        organization = ifc_file.create_entity("IfcOrganization")
        organization.Name = "eLCA Bonsai Integration"
        
        person_and_organization = ifc_file.create_entity("IfcPersonAndOrganization")
        person_and_organization.ThePerson = person
        person_and_organization.TheOrganization = organization
        
        application = ifc_file.create_entity("IfcApplication")
        application.ApplicationDeveloper = organization
        application.Version = "1.0"
        application.ApplicationFullName = "eLCA Bonsai Integration"
        application.ApplicationIdentifier = "eLCA"
        
        # Create ownership history
        ownership_history = ifc_file.create_entity("IfcOwnerHistory")
        ownership_history.OwningUser = person_and_organization
        ownership_history.OwningApplication = application
        ownership_history.ChangeAction = "ADDED"
        
        # Create project
        project = ifc_file.create_entity("IfcProject")
        project.GlobalId = ifcopenshell.guid.new()
        project.OwnerHistory = ownership_history
        project.Name = "eLCA Material Library"
        project.Description = "Material library created from eLCA data"
        
        return project
        
    except Exception as e:
        print(f"[eLCA] Error creating basic IFC structure: {str(e)}")
        return None

def export_material_layer_set_to_ifc(blender_material, ifc_file):
    """Export a Blender material layer set to IFC"""
    try:
        # Create IfcMaterialLayerSet
        layer_set = ifc_file.create_entity("IfcMaterialLayerSet")
        layer_set.LayerSetName = blender_material.name
        
        # Get layer information
        layer_info_str = blender_material.get("layer_info", "[]")
        try:
            layer_info = eval(layer_info_str) if isinstance(layer_info_str, str) else layer_info_str
        except:
            layer_info = []
        
        # Create material layers
        material_layers = []
        created_materials = {}
        
        for layer_data in layer_info:
            # Create or get material
            material_name = layer_data.get('name', 'Unknown')
            if material_name not in created_materials:
                material = ifc_file.create_entity("IfcMaterial")
                material.Name = material_name
                material.Category = layer_data.get('Category', '')
                material.Description = layer_data.get('Description', '')
                created_materials[material_name] = material
            else:
                material = created_materials[material_name]
            
            # Create material layer
            layer = ifc_file.create_entity("IfcMaterialLayer")
            layer.Material = material
            layer.LayerThickness = layer_data.get('LayerThickness', 0.0)
            layer.Name = material_name
            
            material_layers.append(layer)
        
        layer_set.MaterialLayers = material_layers
        
        print(f"[eLCA] Exported material layer set: {blender_material.name}")
        return layer_set
        
    except Exception as e:
        print(f"[eLCA] Error exporting material layer set: {str(e)}")
        return None

def export_material_constituent_set_to_ifc(blender_material, ifc_file):
    """Export a Blender material constituent set to IFC"""
    try:
        # Create IfcMaterialConstituentSet
        constituent_set = ifc_file.create_entity("IfcMaterialConstituentSet")
        constituent_set.Name = blender_material.name
        
        # Get constituent information
        constituent_info_str = blender_material.get("constituent_info", "[]")
        try:
            constituent_info = eval(constituent_info_str) if isinstance(constituent_info_str, str) else constituent_info_str
        except:
            constituent_info = []
        
        # Create material constituents
        material_constituents = []
        created_materials = {}
        
        for constituent_data in constituent_info:
            # Create or get material
            material_name = constituent_data.get('material_name', 'Unknown')
            if material_name not in created_materials:
                material = ifc_file.create_entity("IfcMaterial")
                material.Name = material_name
                material.Category = constituent_data.get('category', '')
                material.Description = constituent_data.get('description', '')
                created_materials[material_name] = material
            else:
                material = created_materials[material_name]
            
            # Create material constituent
            constituent = ifc_file.create_entity("IfcMaterialConstituent")
            constituent.Material = material
            constituent.Fraction = constituent_data.get('fraction', 0.0)
            constituent.Name = constituent_data.get('name', material_name)
            
            material_constituents.append(constituent)
        
        constituent_set.MaterialConstituents = material_constituents
        
        print(f"[eLCA] Exported material constituent set: {blender_material.name}")
        return constituent_set
        
    except Exception as e:
        print(f"[eLCA] Error exporting material constituent set: {str(e)}")
        return None

def get_elca_materials_summary() -> Dict[str, Any]:
    """Get a summary of eLCA-specific materials in the project
    
    Returns:
        Dictionary containing summary information about eLCA materials
    """
    try:
        elca_components = []
        elca_elements = []
        
        for mat in bpy.data.materials:
            if mat.get("elca_component", False):
                elca_components.append({
                    'name': mat.name,
                    'elca_name': mat.get("elca_name", ""),
                    'elca_type': mat.get("elca_type", ""),
                    'has_environmental_data': any(key.startswith("elca_") for key in mat.keys())
                })
            
            if mat.get("elca_element", False):
                elca_elements.append({
                    'name': mat.name,
                    'element_name': mat.get("elca_element_name", ""),
                    'layer_count': mat.get("layer_count", 0),
                    'total_thickness': mat.get("total_thickness", 0.0),
                    'has_environmental_data': any(key.startswith("elca_total_") for key in mat.keys())
                })
        
        return {
            'elca_components': elca_components,
            'elca_elements': elca_elements,
            'total_components': len(elca_components),
            'total_elements': len(elca_elements)
        }
        
    except Exception as e:
        print(f"[eLCA] Error getting eLCA materials summary: {str(e)}")
        return {}

def cleanup_elca_materials() -> None:
    """Remove all eLCA-specific materials from the project"""
    try:
        materials_to_remove = []
        
        for mat in bpy.data.materials:
            if mat.get("elca_component", False) or mat.get("elca_element", False):
                materials_to_remove.append(mat)
        
        for mat in materials_to_remove:
            print(f"[eLCA] Removing eLCA material: {mat.name}")
            bpy.data.materials.remove(mat)
        
        print(f"[eLCA] Removed {len(materials_to_remove)} eLCA materials")
        
        # Refresh interface after removal
        refresh_bim_interface()
        
    except Exception as e:
        print(f"[eLCA] Error cleaning up eLCA materials: {str(e)}")
        traceback.print_exc()

def import_materials_from_ifc_library(library_path: str, filter_elca: bool = False) -> bool:
    """Import materials from an IFC library file
    
    Args:
        library_path: Path to the IFC library file
        filter_elca: If True, only import materials with eLCA data
        
    Returns:
        True if import was successful, False otherwise
    """
    try:
        if not os.path.exists(library_path):
            print(f"[eLCA] Library file not found: {library_path}")
            return False
        
        # Open the library file
        library_ifc = ifcopenshell.open(library_path)
        
        # Import material sets
        add_material_sets_to_project(library_ifc)
        
        # If filtering for eLCA materials, also look for materials with eLCA properties
        if filter_elca:
            materials = library_ifc.by_type("IfcMaterial")
            elca_materials = []
            
            for material in materials:
                # Check if material has eLCA-related properties
                if hasattr(material, 'HasProperties') and material.HasProperties:
                    for prop_set in material.HasProperties:
                        if hasattr(prop_set, 'Properties'):
                            for prop in prop_set.Properties:
                                if hasattr(prop, 'Name') and 'elca' in prop.Name.lower():
                                    elca_materials.append(material)
                                    break
            
            print(f"[eLCA] Found {len(elca_materials)} materials with eLCA properties")
        
        print(f"[eLCA] Successfully imported materials from library: {library_path}")
        return True
        
    except Exception as e:
        print(f"[eLCA] Error importing materials from library: {str(e)}")
        traceback.print_exc()
        return False