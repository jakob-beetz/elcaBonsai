def import_wall_type(project_file, library_file, wall_type, owner_history, new_library_info):
    """
    Import a wall type from the library file to the project file.
    
    Args:
        project_file: The target IFC file
        library_file: The source library file
        wall_type: The wall type to import
        owner_history: Owner history in the target file
        new_library_info: Library information in the target file
        
    Returns:
        The imported wall type, or None if import failed
    """
    # Find the material association for this wall type
    material_association = None
    for rel in library_file.by_type("IfcRelAssociatesMaterial"):
        if wall_type.id() in [obj.id() for obj in rel.RelatedObjects]:
            material_association = rel
            break
                
    if not material_association:
        print(f"No material association found for wall type: {wall_type.Name}")
        return None
            
    material_layer_set = material_association.RelatingMaterial
    if not material_layer_set.is_a("IfcMaterialLayerSet"):
        print(f"Material association is not a layer set for wall type: {wall_type.Name}")
        return None
            
    # Create a new material layer set in the project file
    new_mls = project_file.create_entity(
        "IfcMaterialLayerSet",
        LayerSetName=material_layer_set.LayerSetName
    )
        
    # Create new material layers
    new_layers = []
    for layer in material_layer_set.MaterialLayers:
        if not layer or not layer.Material:
            continue
                
        # Create a new material
        new_material = project_file.create_entity(
            "IfcMaterial",
            Name=layer.Material.Name
        )
            
        # Add classification references if any
        import_material_classifications(
            project_file, 
            library_file, 
            layer.Material, 
            new_material, 
            owner_history
        )
            
        # Create a new material layer
        new_layer = project_file.create_entity(
            "IfcMaterialLayer",
            Material=new_material,
            LayerThickness=layer.LayerThickness,
            Name=layer.Name
        )
            
        new_layers.append(new_layer)
        
    # Set the material layers
    if new_layers:
        new_mls.MaterialLayers = tuple(new_layers)
            
        # Create material layer set usage
        new_mls_usage = project_file.create_entity(
            "IfcMaterialLayerSetUsage",
            ForLayerSet=new_mls,
            LayerSetDirection="AXIS3",
            DirectionSense="POSITIVE",
            OffsetFromReferenceLine=0.0
        )
            
        # Create a new wall type in the project file
        new_wall_type = project_file.create_entity(
            "IfcWallType",
            GlobalId=ifc_utils.create_guid(),
            OwnerHistory=owner_history,
            Name=wall_type.Name,
            Description=wall_type.Description,
            ApplicableOccurrence="",
            HasPropertySets=(),
            RepresentationMaps=(),
            Tag="",
            ElementType=wall_type.ElementType,
            PredefinedType="STANDARD"
        )
            
        # Associate the material layer set with the wall type
        project_file.create_entity(
            "IfcRelAssociatesMaterial",
            GlobalId=ifc_utils.create_guid(),
            OwnerHistory=owner_history,
            RelatedObjects=[new_wall_type],
            RelatingMaterial=new_mls
        )
            
        # Associate with the library
        project_file.create_entity(
            "IfcRelAssociatesLibrary",
            GlobalId=ifc_utils.create_guid(),
            OwnerHistory=owner_history,
            Name=f"Association {new_wall_type.Name}",
            Description=f"Association to library for {new_wall_type.Name}",
            RelatedObjects=[new_wall_type, new_mls, new_mls_usage],
            RelatingLibrary=new_library_info
        )
        
        return new_wall_type
    
    return None