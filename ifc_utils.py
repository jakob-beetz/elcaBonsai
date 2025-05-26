# IFC Utilities Module
import ifcopenshell
import uuid
import datetime
from typing import Optional, List, Dict, Any, Union, Tuple
from pathlib import Path

def create_guid():
    """Create a compressed IFC GUID"""
    return ifcopenshell.guid.compress(uuid.uuid4().hex)

def create_owner_history(ifc_file):
    """
    Create basic owner history and related entities.
    
    Args:
        ifc_file: An IFC file object
        
    Returns:
        IfcOwnerHistory entity
    """
    # Create basic IFC entities
    person = ifc_file.create_entity("IfcPerson", 
                                   FamilyName="User", 
                                   GivenName="Default")
    organization = ifc_file.create_entity("IfcOrganization", 
                                         Name="eLCA Material Library Creator")
    person_and_org = ifc_file.create_entity("IfcPersonAndOrganization", 
                                           ThePerson=person, 
                                           TheOrganization=organization)
    application = ifc_file.create_entity("IfcApplication", 
                                        ApplicationDeveloper=organization,
                                        Version="1.0",
                                        ApplicationFullName="eLCA Material Library Creator",
                                        ApplicationIdentifier="eLCA_Creator")
    owner_history = ifc_file.create_entity("IfcOwnerHistory", 
                                          OwningUser=person_and_org,
                                          OwningApplication=application,
                                          ChangeAction="ADDED",
                                          CreationDate=int(datetime.datetime.now().timestamp()))
    return owner_history

def get_or_create_owner_history(ifc_file):
    """
    Get existing owner history or create a new one if none exists.
    
    Args:
        ifc_file: An IFC file object
        
    Returns:
        IfcOwnerHistory entity
    """
    if ifc_file.by_type("IfcOwnerHistory"):
        return ifc_file.by_type("IfcOwnerHistory")[0]
    else:
        return create_owner_history(ifc_file)

def create_units(ifc_file):
    """
    Create standard units for an IFC file.
    
    Args:
        ifc_file: An IFC file object
        
    Returns:
        IfcUnitAssignment entity
    """
    # Create units
    unit_assignment = ifc_file.create_entity("IfcUnitAssignment")
    
    # Length unit (meters)
    length_unit = ifc_file.create_entity("IfcSIUnit", 
                                        UnitType="LENGTHUNIT", 
                                        Name="METRE")
    unit_assignment.Units = (length_unit,)
    
    return unit_assignment

def parse_thickness(quantity_text: str) -> float:
    """
    Parse thickness from a quantity text (like "200,00 mm").
    
    Args:
        quantity_text: Text representation of quantity
        
    Returns:
        Thickness in meters
    """
    if not quantity_text:
        return 0.01  # Default thickness
    
    try:
        # Extract numeric part and convert to float
        parts = quantity_text.split()
        numeric_part = parts[0].replace(',', '.')
        unit_part = parts[1] if len(parts) > 1 else 'mm'
        
        thickness_value = float(numeric_part)
        
        # Convert to meters based on unit
        if unit_part.lower() == 'mm':
            return thickness_value / 1000.0
        elif unit_part.lower() == 'cm':
            return thickness_value / 100.0
        elif unit_part.lower() == 'm':
            return thickness_value
        else:
            # Default to mm if unit is unknown
            return thickness_value / 1000.0
    except (ValueError, IndexError):
        return 0.01  # Default thickness if parsing fails