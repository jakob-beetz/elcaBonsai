import ifcopenshell
import xml.etree.ElementTree as ET
import os
import uuid
import datetime

def create_guid():
    return ifcopenshell.guid.compress(uuid.uuid4().hex)

def create_ifc_library(xml_path, output_path):
    # Parse XML file
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    # Create a new IFC file
    ifc_file = ifcopenshell.file()
    
    # Create basic IFC entities
    # Create owner history
    person = ifc_file.create_entity("IfcPerson", 
                                   FamilyName="User", 
                                   GivenName="Default")
    organization = ifc_file.create_entity("IfcOrganization", 
                                         Name="BKI Material Library Creator")
    person_and_org = ifc_file.create_entity("IfcPersonAndOrganization", 
                                           ThePerson=person, 
                                           TheOrganization=organization)
    application = ifc_file.create_entity("IfcApplication", 
                                        ApplicationDeveloper=organization,
                                        Version="1.0",
                                        ApplicationFullName="BKI Material Library Creator",
                                        ApplicationIdentifier="BKI_Creator")
    owner_history = ifc_file.create_entity("IfcOwnerHistory", 
                                          OwningUser=person_and_org,
                                          OwningApplication=application,
                                          ChangeAction="ADDED",
                                          CreationDate=int(datetime.datetime.now().timestamp()))
    
    # Create units
    unit_assignment = ifc_file.create_entity("IfcUnitAssignment")
    
    # Length unit (meters)
    length_unit = ifc_file.create_entity("IfcSIUnit", 
                                        UnitType="LENGTHUNIT", 
                                        Name="METRE")
    unit_assignment.Units = (length_unit,)
    
    # Create project
    project = ifc_file.create_entity("IfcProject", 
                                    GlobalId=create_guid(),
                                    Name="BKI Material Library",
                                    OwnerHistory=owner_history,
                                    UnitsInContext=unit_assignment)
    
    # Create library information
    library = ifc_file.create_entity("IfcLibraryInformation",
                                    Name="BKI_Bauteilaufbauten_3_Ebene_DIN_276",
                                    Version="1.0",
                                    Publisher=organization)
    
    # Find all element nodes
    for element in root.findall(".//element"):
        element_id = element.get('id', 'Unknown')
        element_name = element.get('name', 'Unknown')
        
        # Create material layer set
        material_layer_set = ifc_file.create_entity("IfcMaterialLayerSet", Name=element_name)
        material_layers = []
        
        # Find all component siblings
        components = element.findall("./component")
        
        # Create material layers for each component
        for idx, component in enumerate(components):
            component_id = component.get('id', f'Component_{idx}')
            component_name = component.get('name', f'Component_{idx}')
            thickness_text = component.get('thickness', '0')
            
            # Convert thickness to float (in meters)
            try:
                # Assuming thickness is in mm, convert to meters
                thickness = float(thickness_text) / 1000.0
            except ValueError:
                thickness = 0.0
            
            # Create material
            material = ifc_file.create_entity("IfcMaterial", Name=component_name)
            
            # Create material layer
            material_layer = ifc_file.create_entity(
                "IfcMaterialLayer",
                Material=material,
                LayerThickness=thickness,
                Name=component_name
            )
            
            material_layers.append(material_layer)
        
        # Set the material layers
        material_layer_set.MaterialLayers = tuple(material_layers)
        
        # Create material layer set usage
        material_layer_set_usage = ifc_file.create_entity(
            "IfcMaterialLayerSetUsage",
            ForLayerSet=material_layer_set,
            LayerSetDirection="AXIS3",  # Typically for walls, floors, etc.
            DirectionSense="POSITIVE",
            OffsetFromReferenceLine=0.0
        )
        
        # Create a relation to the library
        ifc_file.create_entity(
            "IfcRelAssociatesLibrary",
            GlobalId=create_guid(),
            OwnerHistory=owner_history,
            Name=f"Association {element_name}",
            Description=f"Association to library for {element_name}",
            RelatedObjects=[material_layer_set],
            RelatingLibrary=library
        )
    
    # Save the IFC file
    ifc_file.write(output_path)
    print(f"IFC library file created at: {output_path}")
    return ifc_file

if __name__ == "__main__":
    xml_path = "elcaToIfcLibrary/BKI_Bauteilaufbauten_3_Ebene_DIN_276.xml"
    output_path = "elcaToIfcLibrary/BKI_Materials_Library.ifc"
    create_ifc_library(xml_path, output_path)