# eLCA HTML Parser Module
from bs4 import BeautifulSoup
import pandas as pd
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union
from pathlib import Path

@dataclass
class BauteilElement:
    """Represents a building element (Bauteil) with its properties."""
    category_code: str  # e.g., "331"
    category_name: str  # e.g., "Tragende Außenwände"
    subcategory: Optional[str] = None  # e.g., "Außenwände"
    name: str = ""  # e.g., "Strohballen - Holz"
    url: str = ""  # e.g., "https://www.bauteileditor.de/project-elements/5400248/"
    properties: Dict[str, str] = field(default_factory=dict)  # e.g., {"Menge im Gebäude": "200,00 m²"}
    components: List[Dict[str, Any]] = field(default_factory=list)
    
    def __str__(self):
        return f"{self.category_code} {self.category_name} - {self.name}"

class ELCAComponentExtractor:
    """Extracts components and their UUIDs from ELCA HTML reports."""
    
    def __init__(self, html_path: Optional[Union[str, Path]], xml_path: Optional[Union[str, Path]] = None):
        """
        Initialize the extractor with the path to the HTML file and optional XML file.
        
        Args:
            html_path: Path to the HTML file containing ELCA data (can be None for XML-only parsing)
            xml_path: Optional path to the XML project file containing layer thickness data
        """
        self.html_path = Path(html_path) if html_path else None
        self.xml_path = Path(xml_path) if xml_path else None
        self.soup = None
        self.xml_root = None
        self.xml_layer_data = {}  # Store layer thickness data from XML
        
        # Load HTML file if path is provided
        if self.html_path:
            print('[eLCA-parser] Loading HTML file...')
            self._load_html()
        else:
            print('[eLCA-parser] No HTML file provided - XML-only mode')
        
        # Load XML file if path is provided
        if self.xml_path and self.xml_path.exists():
            print('[eLCA-parser] Loading XML project file...')
            self._load_xml()
            self._extract_layer_data_from_xml()
        elif self.xml_path:
            print(f'[eLCA-parser] Warning: XML file not found: {self.xml_path}')
        else:
            print('[eLCA-parser] No XML project file provided - layer thickness data will not be available')
        
    def _load_html(self) -> None:
        """Load and parse the HTML file."""
        if not self.html_path.exists():
            raise FileNotFoundError(f"HTML file not found: {self.html_path}")
        
        with open(self.html_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
        
        self.soup = BeautifulSoup(html_content, 'html.parser')
    
    def extract_bauteil_elements(self) -> List[BauteilElement]:
        """
        Extract all building elements (Bauteile) with their properties.
        
        Returns:
            List of BauteilElement objects
        """
        bauteil_elements = []
        
        # Find all main category sections
        category_sections = self.soup.select("ul.category > li.section")
        
        for category_section in category_sections:
            # Extract category header from h1
            h1_elem = category_section.select_one("h1")
            if not h1_elem:
                continue
                
            # Extract category text (may contain both code and name)
            category_text = h1_elem.get_text(strip=True)
            
            # Extract subcategory from span if present
            span_elem = h1_elem.select_one("span")
            subcategory = None
            if span_elem:
                subcategory = span_elem.get_text(strip=True)
                # Remove subcategory from main category text
                category_text = category_text.replace(subcategory, "").strip()
            
            # Try to split category into code and name
            category_parts = category_text.split(" ", 1)
            category_code = category_parts[0] if len(category_parts) > 0 else ""
            category_name = category_parts[1] if len(category_parts) > 1 else category_text
            
            # Find all building elements in this category
            element_sections = category_section.select("ul.report-elements > li.section")
            
            for element_section in element_sections:
                # Extract element name and URL
                h2_elem = element_section.select_one("h2")
                if not h2_elem:
                    continue
                
                a_elem = h2_elem.select_one("a.page")
                if not a_elem:
                    continue
                
                element_name = a_elem.get_text(strip=True)
                element_url = a_elem.get("href", "")
                
                # Create new bauteil element
                bauteil = BauteilElement(
                    category_code=category_code,
                    category_name=category_name,
                    subcategory=subcategory,
                    name=element_name,
                    url=element_url
                )
                
                # Extract properties from definition list
                dl_elem = element_section.select_one("dl.clearfix")
                if dl_elem:
                    dt_elems = dl_elem.select("dt")
                    for dt in dt_elems:
                        property_name = dt.get_text(strip=True).rstrip(":")
                        dd = dt.find_next("dd")
                        if dd:
                            property_value = dd.get_text(strip=True)
                            bauteil.properties[property_name] = property_value
                
                # Extract components
                component_sections = element_section.select("div.element-assets")
                for component_section in component_sections:
                    # Get component category
                    component_category_elem = component_section.select_one("h3")
                    component_category = component_category_elem.get_text(strip=True) if component_category_elem else "Unknown"
                    
                    # Find all component rows
                    component_rows = component_section.select("tr.component")
                    
                    for component_row in component_rows:
                        component_data = {
                            "component_category": component_category
                        }
                        
                        # Extract component number
                        number_cell = component_row.select_one("td.firstColumn")
                        if number_cell:
                            component_data["number"] = number_cell.get_text(strip=True)
                        
                        # Extract component details
                        details_cell = component_row.select_one("td.lastColumn")
                        if details_cell:
                            # Extract component name
                            name_elem = details_cell.select_one("span.process-config-name")
                            if name_elem:
                                component_data["name"] = name_elem.get_text(strip=True)
                            
                            # Extract additional component info
                            status_elem = details_cell.select_one("span.info-is-extant")
                            if status_elem:
                                component_data["status"] = status_elem.get_text(strip=True)
                                
                            quantity_elem = details_cell.select_one("span.info-quantity span")
                            if quantity_elem:
                                component_data["quantity"] = quantity_elem.get_text(strip=True)
                                
                            lifetime_elem = details_cell.select_one("span.info-life-time")
                            if lifetime_elem:
                                component_data["lifetime"] = lifetime_elem.get_text(strip=True)
                        
                        # Find the details row that follows this component row
                        details_row = component_row.find_next("tr", class_="details")
                        if details_row:
                            # Extract lifecycle processes
                            process_rows = details_row.select("table.report-assets-details tbody tr:not(.table-headlines)")
                            
                            lifecycle_processes = []
                            for process_row in process_rows:
                                cells = process_row.select("td")
                                if len(cells) >= 5:
                                    process_data = {
                                        "lifecycle_phase": cells[0].get_text(strip=True),
                                        "ratio": cells[1].get_text(strip=True),
                                        "process_name": cells[2].get_text(strip=True),
                                        "reference_value": cells[3].get_text(strip=True),
                                        "uuid": cells[4].get_text(strip=True)
                                    }
                                    lifecycle_processes.append(process_data)
                            
                            if lifecycle_processes:
                                component_data["lifecycle_processes"] = lifecycle_processes
                        
                        bauteil.components.append(component_data)
                
                bauteil_elements.append(bauteil)
        
        return bauteil_elements
    
    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert extracted bauteil elements to a pandas DataFrame.
        
        Returns:
            DataFrame containing the bauteil elements and their components
        """
        bauteil_elements = self.extract_bauteil_elements()
        
        # Create a list of dictionaries for DataFrame creation
        data = []
        for bauteil in bauteil_elements:
            for component in bauteil.components:
                # Create base row with bauteil information
                row = {
                    'Category Code': bauteil.category_code,
                    'Category Name': bauteil.category_name,
                    'Subcategory': bauteil.subcategory,
                    'Bauteil Name': bauteil.name,
                    'Bauteil URL': bauteil.url
                }
                
                # Add bauteil properties
                for prop_name, prop_value in bauteil.properties.items():
                    row[f'Property: {prop_name}'] = prop_value
                
                # Add component information
                row['Component Category'] = component.get('component_category', '')
                row['Component Number'] = component.get('number', '')
                row['Component Name'] = component.get('name', '')
                row['Component Status'] = component.get('status', '')
                row['Component Quantity'] = component.get('quantity', '')
                row['Component Lifetime'] = component.get('lifetime', '')
                
                # Add lifecycle processes if available
                lifecycle_processes = component.get('lifecycle_processes', [])
                if lifecycle_processes:
                    for process in lifecycle_processes:
                        process_row = row.copy()
                        process_row['Lifecycle Phase'] = process.get('lifecycle_phase', '')
                        process_row['Ratio'] = process.get('ratio', '')
                        process_row['Process Name'] = process.get('process_name', '')
                        process_row['Reference Value'] = process.get('reference_value', '')
                        process_row['UUID'] = process.get('uuid', '')
                        data.append(process_row)
                else:
                    # Add row even if no lifecycle processes
                    data.append(row)
        
        return pd.DataFrame(data)
    
    def get_bauteil_summary_dataframe(self) -> pd.DataFrame:
        """
        Get a simplified DataFrame with just the bauteil IDs and basic info.
        
        Returns:
            DataFrame containing basic bauteil information
        """
        bauteil_elements = self.extract_bauteil_elements()
        
        # Create a list of dictionaries for DataFrame creation
        data = []
        for bauteil in bauteil_elements:
            row = {
                'Category Code': bauteil.category_code,
                'Category Name': bauteil.category_name,
                'Subcategory': bauteil.subcategory,
                'Bauteil Name': bauteil.name,
                'Bauteil URL': bauteil.url
            }
            
            # Add bauteil properties
            for prop_name, prop_value in bauteil.properties.items():
                row[prop_name] = prop_value
            
            # Count components and processes
            component_count = len(bauteil.components)
            process_count = sum(len(comp.get('lifecycle_processes', [])) for comp in bauteil.components)
            
            row['Component Count'] = component_count
            row['Process Count'] = process_count
            
            data.append(row)
        
        return pd.DataFrame(data)
    
    def save_to_csv(self, output_path: Union[str, Path]) -> None:
        """
        Save the extracted data to a CSV file.
        
        Args:
            output_path: Path where the CSV file will be saved
        """
        df = self.to_dataframe()
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"Data saved to {output_path}")
    
    def save_bauteil_summary_to_csv(self, output_path: Union[str, Path]) -> None:
        """
        Save a simplified version with just the bauteil IDs and basic info.
        
        Args:
            output_path: Path where the CSV file will be saved
        """
        df = self.get_bauteil_summary_dataframe()
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"Bauteil summary saved to {output_path}")
    
    def _load_xml(self) -> None:
        """Load and parse the XML project file."""
        if not self.xml_path or not self.xml_path.exists():
            raise FileNotFoundError(f"XML file not found: {self.xml_path}")
        
        try:
            tree = ET.parse(self.xml_path)
            self.xml_root = tree.getroot()
            print(f'[eLCA-parser] Successfully loaded XML project file: {self.xml_path}')
            
        except ET.ParseError as e:
            print(f'[eLCA-parser] Error parsing XML file: {e}')
            self.xml_root = None
            raise Exception(f"XML parsing error: {e}")
        
        except Exception as e:
            print(f'[eLCA-parser] Error loading XML file: {e}')
            self.xml_root = None
            raise Exception(f"Error loading XML file: {e}")

    def _extract_layer_data_from_xml(self) -> None:
        """Extract layer thickness data from XML file."""
        # if not self.xml_root:
        #     return
        ELCA_NS = 'https://www.bauteileditor.de'
        print(f'[eLCA-parser] inspecting DOM {self.xml_root}')
        try:
            # Find all elements in the XML at any depth using iter()
            el = self.xml_root.iter(f'{{{ELCA_NS}}}element')
            print(f'[eLCA-parser] Found{list(el)} element tags in XML')
            elements_found = list(self.xml_root.iter(f'{{{ELCA_NS}}}element'))
            if not elements_found:
                print('[eLCA-parser] No element tags found in XML')
                return
            print(f'[eLCA-parser] Found {len(elements_found)} element tags in XML')
            
            for element in elements_found:
                element_uuid = element.get('uuid')
                din276_code = element.get('din276Code')
                quantity = element.get('quantity')
                ref_unit = element.get('refUnit')
                
                if not element_uuid:
                    continue  # Skip elements without UUID
                
                print(f'[eLCA-parser] Processing element UUID: {element_uuid}')
                
                # Extract element name from CDATA in elementInfo/name
                element_name = ""
                element_info = element.find(f'{{{ELCA_NS}}}elementInfo')
                if element_info is not None:
                    name_elem = element_info.find(f'{{{ELCA_NS}}}name')
                    if name_elem is not None and name_elem.text:
                        element_name = name_elem.text.strip()
                        print(f'[eLCA-parser] Found element: {element_name}')
                
                # Extract element description from CDATA in elementInfo/description
                element_description = ""
                if element_info is not None:
                    desc_elem = element_info.find(f'{{{ELCA_NS}}}description')
                    if desc_elem is not None and desc_elem.text:
                        element_description = desc_elem.text.strip()
                
                # Find all components within this element at any depth
                components_found = list(element.iter(f'{{{ELCA_NS}}}component'))
                print(f'[eLCA-parser] Found {len(components_found)} components in element {element_uuid}')
                
                for component in components_found:
                    component_uuid = component.get('uuid')
                    is_layer = component.get('isLayer')
                    layer_size = component.get('layerSize')
                    layer_position = component.get('layerPosition')
                    layer_ratio = component.get('layerAreaRatio')
                    
                    # Extract additional attributes from the component tag
                    process_config_uuid = component.get('processConfigUuid')
                    process_config_name = component.get('processConfigName')
                    life_time = component.get('lifeTime')
                    life_time_delay = component.get('lifeTimeDelay')
                    calc_lca = component.get('calcLca')
                    is_extant = component.get('isExtant')
                    layer_length = component.get('layerLength')
                    layer_width = component.get('layerWidth')
                    component_name = process_config_name
                    print(f'[eLCA-parser] Processing component UUID: {component_uuid}, isLayer: {is_layer}, layerSize: {layer_size}, processConfigName: {process_config_name}')
                    
                    # Only process components marked as layers with a size
                    try:
                        thickness = float(layer_size) if layer_size else 0.0
                        
                        # Extract component name from CDATA in componentInfo/name
                        
                        # Store layer data
                        layer_key = f"{element_uuid}_{component_uuid}" if component_uuid else f"{element_uuid}_{component_name}"
                        
                        self.xml_layer_data[layer_key] = {
                            'element_uuid': element_uuid,
                            'element_name': element_name,
                            'element_description': element_description,
                            'element_din276': din276_code,
                            'element_quantity': quantity,
                            'element_ref_unit': ref_unit,
                            'component_name': component_name,
                            'layer_thickness': thickness, # This is layer_size converted to float
                            'component_uuid': component_uuid, # This is the component's uuid
                            'is_layer': is_layer,
                            # Add newly extracted attributes
                            'process_config_uuid': process_config_uuid,
                            'process_config_name': process_config_name,
                            'life_time': life_time,
                            'life_time_delay': life_time_delay,
                            'calc_lca': calc_lca,
                            'is_extant': is_extant,
                            'layer_position': layer_position,
                            'layer_ratio': layer_ratio,
                            'layer_length': layer_length,
                            'layer_width': layer_width
                        }
                        
                        # Also store by component name for easier matching (if name exists)
                        # Note: This might overwrite if component names are not unique across elements
                        if component_name:
                            self.xml_layer_data[component_name] = self.xml_layer_data[layer_key]
                        
                        print(f'[eLCA-parser] Found layer: {component_name} with thickness {thickness} mm in element: {element_name}')
                        
                    except ValueError:
                        print(f'[eLCA-parser] Invalid layer size value: {layer_size} for component {component_uuid}')
            
            print(f'[eLCA-parser] Extracted {len(self.xml_layer_data)} entries from XML')
            
        except Exception as e:
            print(f'[eLCA-parser] Error extracting layer data from XML: {e}')
            import traceback
            traceback.print_exc()

    def get_layer_thickness_summary(self) -> Dict[str, Any]:
        """Get a summary of layer thickness data from XML."""
        if not self.xml_layer_data:
            return {'total_elements': 0, 'total_layers': 0, 'total_components': 0}
        
        # Count unique elements and layers
        unique_elements = set()
        layer_count = 0
        component_count = 0
        
        for key, data in self.xml_layer_data.items():
            if isinstance(data, dict):
                if data.get('element_uuid'):
                    unique_elements.add(data['element_uuid'])
                if data.get('is_layer', False):
                    layer_count += 1
                else:
                    component_count += 1
        
        return {
            'total_elements': len(unique_elements),
            'total_layers': layer_count,
            'total_components': component_count,
            'total_entries': len(self.xml_layer_data)
        }