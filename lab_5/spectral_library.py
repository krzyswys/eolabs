#!/usr/bin/env python3
"""
Spectral Library Management
----------------------------
Manage spectral signatures for different land cover types.
Load signatures from CSV files exported by viewer.py.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


class SpectralLibrary:
    """Manage spectral signatures for different land cover types."""
    
    def __init__(self):
        self.signatures = {}
        self.wavelengths = None
    
    def add_signature(self, name, spectrum, wavelengths=None):
        """
        Add a spectral signature to the library.
        
        Parameters:
        -----------
        name : str
            Name of the land cover type
        spectrum : array-like
            Spectral reflectance values
        wavelengths : array-like, optional
            Wavelengths corresponding to spectrum values
        """
        self.signatures[name] = np.array(spectrum)
        if wavelengths is not None:
            self.wavelengths = np.array(wavelengths)
    
    def load_from_csv(self, filepath, name):
        """
        Load signature from CSV file exported by viewer.py.
        
        Parameters:
        -----------
        filepath : str or Path
            Path to CSV file
        name : str
            Name to assign to this signature
        """
        df = pd.read_csv(filepath)
        
        # Handle both 'wavelength_nm' and 'band' column names
        wl_col = 'wavelength_nm' if 'wavelength_nm' in df.columns else 'band'
        
        self.add_signature(name, df['value'].values, df[wl_col].values)
        print(f"Loaded signature '{name}' from {filepath}")
    
    def get_signature(self, name):
        """Get a signature by name."""
        return self.signatures.get(name)
    
    def list_signatures(self):
        """List all signatures in the library."""
        return list(self.signatures.keys())
    
    def plot_signatures(self, names=None, figsize=(12, 6)):
        """
        Plot spectral signatures.
        
        Parameters:
        -----------
        names : list of str, optional
            Names of signatures to plot. If None, plots all.
        figsize : tuple
            Figure size
        """
        if names is None:
            names = list(self.signatures.keys())
        
        if not names:
            print("No signatures to plot")
            return
        
        plt.figure(figsize=figsize)
        
        for name in names:
            if name in self.signatures:
                plt.plot(self.wavelengths, self.signatures[name], 
                        label=name, linewidth=2)
        
        plt.xlabel('Wavelength (nm)', fontsize=12)
        plt.ylabel('Reflectance (× 10⁻⁴)', fontsize=12)
        plt.title('Spectral Library', fontsize=14)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()
    
    def save_library(self, filepath):
        """
        Save library to CSV file.
        
        Parameters:
        -----------
        filepath : str or Path
            Output CSV file path
        """
        if self.wavelengths is None:
            print("Error: No wavelengths defined")
            return
        
        df = pd.DataFrame({'wavelength_nm': self.wavelengths})
        
        for name, spectrum in self.signatures.items():
            df[name] = spectrum
        
        df.to_csv(filepath, index=False)
        print(f"Library saved to {filepath}")
    
    def load_library(self, filepath):
        """
        Load library from CSV file.
        
        Parameters:
        -----------
        filepath : str or Path
            Input CSV file path
        """
        df = pd.read_csv(filepath)
        
        self.wavelengths = df['wavelength_nm'].values
        
        for col in df.columns:
            if col != 'wavelength_nm':
                self.signatures[col] = df[col].values
        
        print(f"Loaded {len(self.signatures)} signatures from {filepath}")
    
    def compare_signatures(self, name1, name2):
        """
        Compare two signatures and compute spectral angle.
        
        Parameters:
        -----------
        name1, name2 : str
            Names of signatures to compare
        
        Returns:
        --------
        angle : float
            Spectral angle in radians
        """
        if name1 not in self.signatures or name2 not in self.signatures:
            print("Error: One or both signatures not found")
            return None
        
        spec1 = self.signatures[name1]
        spec2 = self.signatures[name2]
        
        # Remove NaN values
        valid = ~(np.isnan(spec1) | np.isnan(spec2))
        spec1 = spec1[valid]
        spec2 = spec2[valid]
        
        # Compute spectral angle
        dot_product = np.dot(spec1, spec2)
        norm_product = np.linalg.norm(spec1) * np.linalg.norm(spec2)
        
        if norm_product == 0:
            return None
        
        cos_angle = dot_product / norm_product
        angle = np.arccos(np.clip(cos_angle, -1, 1))
        
        print(f"Spectral angle between '{name1}' and '{name2}': {angle:.4f} radians ({np.degrees(angle):.2f}°)")
        return angle


def create_example_library(wavelengths, output_path=None):
    """
    Create an example spectral library with synthetic signatures.
    
    Parameters:
    -----------
    wavelengths : array-like
        Wavelength array
    output_path : str or Path, optional
        If provided, saves library to this path
    
    Returns:
    --------
    library : SpectralLibrary
        Library with example signatures
    """
    library = SpectralLibrary()
    library.wavelengths = np.array(wavelengths)
    
    # Water signature (low reflectance, strong NIR absorption)
    water = np.ones_like(wavelengths) * 200.0
    water[wavelengths > 700] = 50
    water[wavelengths < 500] = 300
    library.add_signature('water', water)
    
    # Vegetation signature (chlorophyll absorption, red edge, high NIR)
    vegetation = np.ones_like(wavelengths) * 300.0
    vegetation[(wavelengths > 600) & (wavelengths < 680)] = 150
    vegetation[wavelengths > 750] = 3000
    # Red edge transition
    red_edge_mask = (wavelengths > 680) & (wavelengths < 750)
    if red_edge_mask.sum() > 0:
        vegetation[red_edge_mask] = np.linspace(150, 3000, red_edge_mask.sum())
    library.add_signature('vegetation', vegetation)
    
    # Soil signature (gradual increase with wavelength)
    soil = 500 + (wavelengths - wavelengths[0]) * 2
    library.add_signature('soil', soil)
    
    # Urban/built-up (relatively flat, moderate reflectance)
    urban = np.ones_like(wavelengths) * 1500.0
    urban[wavelengths < 500] = 1200
    library.add_signature('urban', urban)
    
    print("Created example library with 4 signatures: water, vegetation, soil, urban")
    
    if output_path:
        library.save_library(output_path)
    
    return library


if __name__ == "__main__":
    # Example usage
    print("Spectral Library Management Tool")
    print("=" * 50)
    
    # Create example library
    wavelengths = np.linspace(400, 2500, 456)
    lib = create_example_library(wavelengths, "example_library.csv")
    
    # Plot signatures
    lib.plot_signatures()
    
    # Compare signatures
    lib.compare_signatures('water', 'vegetation')
    lib.compare_signatures('soil', 'urban')

# Made with Bob
