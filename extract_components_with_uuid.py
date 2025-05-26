#!/usr/bin/env python3
"""
Extract building components and their UUIDs from ELCA HTML reports.
"""

import os
import sys
import argparse
from pathlib import Path
from bs4 import BeautifulSoup
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union


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
    
    def __init__(self, html_path: Union[str, Path]):
        """
        Initialize the extractor with the path to the HTML file.
        
        Args:
            html_path: Path to the HTML file containing ELCA data
        """
        self.html_path = Path(html_path)
        self.soup = None
        self._load_html()
        
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


def extract_components(html_path: Union[str, Path]) -> pd.DataFrame:
    """
    Extract components from an HTML file and return as DataFrame.
    
    Args:
        html_path: Path to the HTML file
        
    Returns:
        DataFrame containing the extracted components
    """
    extractor = ELCAComponentExtractor(html_path)
    return extractor.to_dataframe()


def extract_bauteil_summary(html_path: Union[str, Path]) -> pd.DataFrame:
    """
    Extract bauteil summary from an HTML file and return as DataFrame.
    
    Args:
        html_path: Path to the HTML file
        
    Returns:
        DataFrame containing the bauteil summary
    """
    extractor = ELCAComponentExtractor(html_path)
    return extractor.get_bauteil_summary_dataframe()


def main():
    print("starting to ingest ")
    """Main function to handle command line arguments and execute extraction."""
    parser = argparse.ArgumentParser(
        description='Extract building components and their UUIDs from ELCA HTML reports.'
    )
    parser.add_argument('input', help='Input HTML file or directory containing HTML files')
    parser.add_argument('-o', '--output', help='Output CSV file or directory (default: derived from input)')
    parser.add_argument('-s', '--summary', action='store_true', 
                        help='Generate summary output instead of detailed component data')
    parser.add_argument('-r', '--recursive', action='store_true',
                        help='Process directories recursively')
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    # Handle single file
    if input_path.is_file():
        if not args.output:
            # Default output name based on input file
            output_path = input_path.with_suffix('.csv')
        else:
            output_path = Path(args.output)
            
            # If output is a directory, create a file inside it
            if output_path.is_dir():
                output_path = output_path / (input_path.stem + '.csv')
        
        try:
            extractor = ELCAComponentExtractor(input_path)
            if args.summary:
                extractor.save_bauteil_summary_to_csv(output_path)
            else:
                extractor.save_to_csv(output_path)
            print(f"Successfully processed {input_path}")
        except Exception as e:
            print(f"Error processing {input_path}: {e}", file=sys.stderr)
            return 1
    
    # Handle directory
    elif input_path.is_dir():
        if not args.output:
            # Default output directory is same as input
            output_dir = input_path
        else:
            output_dir = Path(args.output)
            os.makedirs(output_dir, exist_ok=True)
        
        # Get list of HTML files
        if args.recursive:
            html_files = list(input_path.glob('**/*.htm')) + list(input_path.glob('**/*.html'))
        else:
            html_files = list(input_path.glob('*.htm')) + list(input_path.glob('*.html'))
        
        if not html_files:
            print(f"No HTML files found in {input_path}", file=sys.stderr)
            return 1
        
        success_count = 0
        error_count = 0
        
        for html_file in html_files:
            # Determine relative path from input directory
            rel_path = html_file.relative_to(input_path)
            
            # Create corresponding output path
            if args.summary:
                output_file = output_dir / rel_path.with_suffix('.summary.csv')
            else:
                output_file = output_dir / rel_path.with_suffix('.csv')
            
            # Create parent directories if needed
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                extractor = ELCAComponentExtractor(html_file)
                if args.summary:
                    extractor.save_bauteil_summary_to_csv(output_file)
                else:
                    extractor.save_to_csv(output_file)
                print(f"Successfully processed {html_file} -> {output_file}")
                success_count += 1
            except Exception as e:
                print(f"Error processing {html_file}: {e}", file=sys.stderr)
                error_count += 1
        
        print(f"Processed {success_count} files successfully, {error_count} with errors")
    
    else:
        print(f"Input path does not exist: {input_path}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == "__main__":
    main()