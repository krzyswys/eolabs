# How to Complete Lab 5

## Simple Two-Step Workflow

### Step 1: Collect Spectral Signatures (15 minutes)

```bash
python viewer.py
```

**What you'll see:**
- Left side: RGB image of your hyperspectral data
- Right side: Empty (waiting for you to click)

**What to do:**

1. **Click on water** (looks dark/blue in the image)
   - Spectral signature appears on the right
   - Click "Export spectrum to CSV..."
   - Save as `water.csv`

2. **Click on vegetation** (looks green/bright)
   - Spectral signature appears
   - Export as `vegetation.csv`

3. **Click on soil** (looks brown/tan)
   - Spectral signature appears
   - Export as `soil.csv`

4. **Optional: Click on urban** (looks gray)
   - Export as `urban.csv`

**How many times?**
- **3-5 clicks total** (one per land cover type)
- Each click = 1 export

---

### Step 2: Run Jupyter Notebook (30 minutes)

```bash
jupyter notebook water_quality_analysis.ipynb
```

**Execute cells in order (press Shift+Enter for each):**

#### Cell 1: Import Libraries
```python
import numpy as np
import matplotlib.pyplot as plt
...
```
Just press Shift+Enter

#### Cell 2: Load Hyperspectral Data
```python
img = envi.open(...)
wavelengths = ...
```
Press Shift+Enter → Data loads

#### Cell 3: Display RGB and False-Color Composites
Press Shift+Enter → 3 images appear

#### Cell 4: Calculate Water Quality Indices
Press Shift+Enter → 6 water quality maps appear

#### Cell 5: Load Your Spectral Signatures

**IMPORTANT: Modify this cell to load YOUR files:**

Find this section:
```python
# Create example signatures
water_sig, veg_sig, soil_sig = create_example_signatures(wavelengths)
```

**Replace it with:**
```python
# Load YOUR collected signatures
spectral_lib.load_from_csv('water.csv', 'water')
spectral_lib.load_from_csv('vegetation.csv', 'vegetation')
spectral_lib.load_from_csv('soil.csv', 'soil')
# If you collected urban:
# spectral_lib.load_from_csv('urban.csv', 'urban')
```

Press Shift+Enter → Your signatures are plotted

#### Cell 6: Run SAM Classification

**Note:** This cell processes the full image and may take 5-10 minutes.

Press Shift+Enter → Classification map appears

---

### Step 3: Save Your Results

**To save any plot in the notebook:**

Right-click on the plot → "Save image as..." → save as PNG

**Or add this line after any plot:**
```python
plt.savefig('my_result.png', dpi=150, bbox_inches='tight')
```

---

## What to Submit

1. ✅ RGB and false-color composites (from Cell 3)
2. ✅ Water quality indices - 6 maps (from Cell 4)
3. ✅ Spectral library plot (from Cell 5)
4. ✅ SAM classification map (from Cell 6)

Save each as PNG file.

---

## Complete Checklist

- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Run `python viewer.py`
- [ ] Click on water → export as `water.csv`
- [ ] Click on vegetation → export as `vegetation.csv`
- [ ] Click on soil → export as `soil.csv`
- [ ] Run `jupyter notebook water_quality_analysis.ipynb`
- [ ] Execute Cell 1 (imports)
- [ ] Execute Cell 2 (load data)
- [ ] Execute Cell 3 (composites) → save plots
- [ ] Execute Cell 4 (water indices) → save plots
- [ ] Modify Cell 5 to load your CSV files
- [ ] Execute Cell 5 (spectral library) → save plot
- [ ] Execute Cell 6 (SAM classification) → save plot
- [ ] Submit all PNG files

---

## Tips

**Finding pixels in viewer:**
- **Water**: Dark areas, especially in NIR bands
- **Vegetation**: Green areas, bright in NIR
- **Soil**: Brown/tan areas
- **Urban**: Gray areas, roads, buildings

**In the notebook:**
- Execute cells in order (don't skip)
- Wait for each cell to finish before moving to next
- Cell 6 (SAM) takes longest - be patient

**Saving plots:**
- Right-click on any plot → "Save image as..."
- Or add `plt.savefig('name.png', dpi=150)` after plot

---

## Time Estimate

- Install dependencies: 2 min
- Collect signatures (viewer): 15 min
- Run notebook: 30 min
- Save plots: 5 min
- **Total: ~50 minutes**

---

## Troubleshooting

**Q: "No .hdr files found" in viewer**
- A: Make sure data is in `Obrazy lotnicze/` folder

**Q: "Import error" in notebook**
- A: Run `pip install -r requirements.txt`

**Q: SAM takes too long**
- A: It's normal, processing full image takes 5-10 minutes

**Q: How do I know which pixel is water/vegetation?**
- A: Look at the RGB image - water is dark/blue, vegetation is green

---

## That's It!

**Two simple steps:**
1. `python viewer.py` → collect 3-5 signatures
2. `jupyter notebook water_quality_analysis.ipynb` → execute all cells

**Submit the PNG plots from the notebook.**