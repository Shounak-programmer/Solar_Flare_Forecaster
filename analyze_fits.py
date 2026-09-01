"""
Comprehensive FITS data inventory for Aditya-L1 SoLEXS and HEL1OS data.
Produces data_inventory.md report.
"""
import os
import sys
import glob
import gzip
import zipfile
import traceback
from collections import defaultdict
import numpy as np
from astropy.io import fits

EXTRACT = "D:/Data/_analysis_tmp"
HEL_ROOT = "D:/Data/HEL1OS"
SLX_ROOT = "D:/Data/SoLEXUS"
HEL_EXTRACT = os.path.join(EXTRACT, "HEL1OS")
SLX_EXTRACT = os.path.join(EXTRACT, "SoLEXUS")
CAL_EXTRACT = os.path.join(EXTRACT, "HEL1OS_CAL")

report = []
def R(line=""):
    report.append(line)

def format_size(nbytes):
    for unit in ['B','KB','MB','GB','TB']:
        if nbytes < 1024:
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} PB"

# ─────────────────────────────────────────────
# STEP 1: Directory Inventory
# ─────────────────────────────────────────────
R("# Aditya-L1 SoLEXS & HEL1OS Data Inventory Report")
R()
R("## Step 1 — Directory Inventory")
R()

for label, root in [("HEL1OS", HEL_ROOT), ("SoLEXUS (SoLEXS)", SLX_ROOT)]:
    R(f"### {label}: `{root}`")
    R()

    # File counts by extension (from zip listing, not extracted)
    ext_counts = defaultdict(int)
    ext_sizes = defaultdict(int)
    total_zip_size = 0
    total_files_in_zips = 0
    zip_count = 0
    dup_count = 0

    zips = [f for f in os.listdir(root) if f.endswith('.zip')]
    for zf_name in zips:
        zf_path = os.path.join(root, zf_name)
        total_zip_size += os.path.getsize(zf_path)
        zip_count += 1
        if '(1)' in zf_name:
            dup_count += 1
            continue
        try:
            with zipfile.ZipFile(zf_path) as z:
                for info in z.infolist():
                    if info.is_dir():
                        continue
                    total_files_in_zips += 1
                    _, ext = os.path.splitext(info.filename)
                    if ext == '.gz':
                        base, inner_ext = os.path.splitext(info.filename[:-3])
                        ext = inner_ext + '.gz'
                    ext_counts[ext] += 1
                    ext_sizes[ext] += info.file_size
        except Exception as e:
            R(f"  - Error reading {zf_name}: {e}")

    # Also check for extracted dirs
    extracted_dirs = [d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))]

    R(f"- **Total zip files on disk:** {zip_count} ({format_size(total_zip_size)})")
    R(f"- **Duplicate zips (with '(1)' suffix):** {dup_count}")
    R(f"- **Unique observations:** {zip_count - dup_count}")
    R(f"- **Total files inside zips:** {total_files_in_zips}")
    if extracted_dirs:
        R(f"- **Extracted directories:** {', '.join(extracted_dirs)}")
    R()
    R("**File counts by type (inside zips):**")
    R()
    R("| Extension | Count | Total Size (uncompressed) |")
    R("|-----------|-------|--------------------------|")
    for ext, count in sorted(ext_counts.items(), key=lambda x: -x[1]):
        R(f"| `{ext}` | {count} | {format_size(ext_sizes[ext])} |")
    R()

    # Show directory tree of one extracted observation
    if label == "HEL1OS":
        sample_obs = glob.glob(os.path.join(HEL_EXTRACT, "**", "HLS_*"), recursive=True)
        sample_obs = [d for d in sample_obs if os.path.isdir(d)]
    else:
        sample_obs = glob.glob(os.path.join(SLX_EXTRACT, "AL1_SLX_*"))
        sample_obs = [d for d in sample_obs if os.path.isdir(d)]

    if sample_obs:
        obs = sample_obs[0]
        R(f"**Sample observation tree:** `{os.path.basename(obs)}`")
        R("```")
        for dirpath, dirnames, filenames in os.walk(obs):
            level = dirpath.replace(obs, '').count(os.sep)
            indent = '  ' * level
            R(f"{indent}{os.path.basename(dirpath)}/")
            subindent = '  ' * (level + 1)
            for f in sorted(filenames):
                fpath = os.path.join(dirpath, f)
                sz = os.path.getsize(fpath)
                R(f"{subindent}{f}  ({format_size(sz)})")
        R("```")
        R()

# ─────────────────────────────────────────────
# STEP 2: FITS Structure Inspection
# ─────────────────────────────────────────────
R("## Step 2 — FITS Structure Inspection")
R()

HEADER_KEYS = [
    'TELESCOP','INSTRUME','OBJECT','DATE-OBS','DATE-END',
    'TSTART','TSTOP','TIMESYS','TIMEUNIT','MJDREF','MJDREFI','MJDREFF',
    'TIMEZERO','EXPOSURE','ONTIME','LIVETIME','DEADC',
    'CHANTYPE','DETCHANS','GAIN','OFFSET','BACKAPP','DEADAPP',
    'DETNAM','DET_ID','FILTER','CREATOR','ORIGIN','HDUCLAS1','HDUCLAS2',
    'HDUCLAS3','RESPFILE','ANCRFILE','BACKFILE'
]

def inspect_fits(filepath, label):
    R(f"### {label}")
    R(f"**File:** `{filepath}`")
    R(f"**Size:** {format_size(os.path.getsize(filepath))}")
    R()
    try:
        with fits.open(filepath) as hdul:
            R("**HDU Summary:**")
            R("```")
            from io import StringIO
            buf = StringIO()
            hdul.info(output=buf)
            R(buf.getvalue().strip())
            R("```")
            R()
            for i, hdu in enumerate(hdul):
                R(f"**HDU {i}: name=`{hdu.name}`, type=`{type(hdu).__name__}`**")
                R()
                # Key headers
                found_keys = []
                for key in HEADER_KEYS:
                    if key in hdu.header:
                        found_keys.append((key, hdu.header[key]))
                if found_keys:
                    R("| Key | Value |")
                    R("|-----|-------|")
                    for k, v in found_keys:
                        R(f"| `{k}` | `{v}` |")
                    R()
                # Columns
                if hasattr(hdu, 'columns') and hdu.columns is not None:
                    R("**Columns:**")
                    R()
                    R("| Name | Unit | Format |")
                    R("|------|------|--------|")
                    for c in hdu.columns:
                        R(f"| `{c.name}` | `{c.unit}` | `{c.format}` |")
                    R()
    except Exception as e:
        R(f"**ERROR opening file:** {e}")
        R()

# Find representative FITS files from extracted samples
def find_fits_files(base_dir):
    """Find all FITS files (including .gz) recursively."""
    results = []
    for dirpath, dirnames, filenames in os.walk(base_dir):
        for f in filenames:
            fpath = os.path.join(dirpath, f)
            if f.endswith('.fits') or f.endswith('.fits.gz') or \
               f.endswith('.gti.gz') or f.endswith('.lc.gz') or f.endswith('.pi.gz'):
                results.append(fpath)
    return sorted(results)

# HEL1OS files
R("### HEL1OS Representative Files")
R()

hel_fits = find_fits_files(HEL_EXTRACT)
# Group by type
hel_by_type = defaultdict(list)
for f in hel_fits:
    bname = os.path.basename(f)
    if 'evt' in bname:
        hel_by_type['events'].append(f)
    elif 'lightcurve' in bname:
        hel_by_type['lightcurve'].append(f)
    elif 'spectra' in bname:
        hel_by_type['spectra'].append(f)
    elif 'gti' in bname:
        hel_by_type['gti'].append(f)
    elif 'hk' in bname:
        hel_by_type['housekeeping'].append(f)
    else:
        hel_by_type['other'].append(f)

R(f"Found {len(hel_fits)} FITS files across extracted observations:")
R()
for ftype, files in sorted(hel_by_type.items()):
    R(f"- **{ftype}:** {len(files)} files")
R()

# Inspect 2-3 representative files
inspect_samples = []
for ftype in ['events', 'lightcurve', 'spectra', 'gti', 'housekeeping']:
    if ftype in hel_by_type:
        # Pick first, and if cdt vs czt variants exist, pick one of each
        files = hel_by_type[ftype]
        cdte_files = [f for f in files if 'cdte' in f.lower()]
        czt_files = [f for f in files if 'czt' in f.lower()]
        if cdte_files:
            inspect_samples.append((f"HEL1OS {ftype} (CdTe)", cdte_files[0]))
        if czt_files:
            inspect_samples.append((f"HEL1OS {ftype} (CZT)", czt_files[0]))
        if not cdte_files and not czt_files:
            inspect_samples.append((f"HEL1OS {ftype}", files[0]))

for label, fpath in inspect_samples:
    inspect_fits(fpath, label)

# SoLEXUS files
R("### SoLEXUS (SoLEXS) Representative Files")
R()

slx_fits = find_fits_files(SLX_EXTRACT)
# Also check the pre-extracted folder
slx_preextracted = find_fits_files(os.path.join(SLX_ROOT, "AL1_SLX_L1_20260613_v1.0"))
slx_all = slx_fits + slx_preextracted

slx_by_type = defaultdict(list)
for f in slx_all:
    bname = os.path.basename(f)
    if '.gti' in bname:
        slx_by_type['gti'].append(f)
    elif '.lc' in bname:
        slx_by_type['lightcurve'].append(f)
    elif '.pi' in bname:
        slx_by_type['spectrum'].append(f)
    else:
        slx_by_type['other'].append(f)

R(f"Found {len(slx_all)} FITS files across extracted observations:")
R()
for ftype, files in sorted(slx_by_type.items()):
    R(f"- **{ftype}:** {len(files)} files")
R()

# Inspect representative SoLEXS files
slx_inspect = []
for ftype in ['gti', 'lightcurve', 'spectrum']:
    if ftype in slx_by_type:
        files = slx_by_type[ftype]
        sdd1 = [f for f in files if 'SDD1' in f]
        sdd2 = [f for f in files if 'SDD2' in f]
        if sdd1:
            slx_inspect.append((f"SoLEXS {ftype} (SDD1)", sdd1[0]))
        if sdd2:
            slx_inspect.append((f"SoLEXS {ftype} (SDD2)", sdd2[0]))
        if not sdd1 and not sdd2:
            slx_inspect.append((f"SoLEXS {ftype}", files[0]))

for label, fpath in slx_inspect:
    inspect_fits(fpath, label)

# Also inspect calibration files
R("### HEL1OS Calibration Files")
R()
cal_fits = find_fits_files(CAL_EXTRACT)
for f in cal_fits:
    bname = os.path.basename(f)
    if 'arf' in bname:
        inspect_fits(f, f"Calibration ARF: {bname}")
    elif 'srf' in bname or 'rmf' in bname:
        inspect_fits(f, f"Calibration SRF/RMF: {bname}")

# ─────────────────────────────────────────────
# STEP 3: Time Coverage and GTI Inspection
# ─────────────────────────────────────────────
R("## Step 3 — Time Coverage and GTI Inspection")
R()

def get_time_range(fits_path):
    """Extract TSTART, TSTOP from a FITS file."""
    try:
        with fits.open(fits_path) as hdul:
            for hdu in hdul:
                h = hdu.header
                tstart = h.get('TSTART')
                tstop = h.get('TSTOP')
                if tstart is not None and tstop is not None:
                    return float(tstart), float(tstop)
    except:
        pass
    return None, None

def analyze_gti(fits_path, label):
    """Load GTI HDU and compute stats."""
    R(f"#### GTI Analysis: {label}")
    R(f"**File:** `{os.path.basename(fits_path)}`")
    R()
    try:
        with fits.open(fits_path) as hdul:
            gti_hdu = None
            for hdu in hdul:
                if hdu.name in ('GTI', 'STDGTI', 'GTI1', 'RATE') or \
                   (hasattr(hdu, 'columns') and hdu.columns is not None):
                    if hasattr(hdu, 'data') and hdu.data is not None:
                        cols = [c.name.upper() for c in hdu.columns]
                        if 'START' in cols and 'STOP' in cols:
                            gti_hdu = hdu
                            break
                        elif 'TSTART' in cols and 'TSTOP' in cols:
                            gti_hdu = hdu
                            break
            if gti_hdu is None:
                R("No GTI table found in this file.")
                R()
                return

            data = gti_hdu.data
            if 'START' in [c.name.upper() for c in gti_hdu.columns]:
                starts = data['START']
                stops = data['STOP']
            else:
                starts = data['TSTART']
                stops = data['TSTOP']

            n_intervals = len(starts)
            durations = stops - starts
            total_good = np.sum(durations)
            total_elapsed = stops[-1] - starts[0] if n_intervals > 0 else 0
            longest = np.max(durations) if n_intervals > 0 else 0
            shortest = np.min(durations) if n_intervals > 0 else 0

            R(f"- **Number of GTI intervals:** {n_intervals}")
            R(f"- **Total good time:** {total_good:.1f} s ({total_good/3600:.2f} hr)")
            R(f"- **Total elapsed time:** {total_elapsed:.1f} s ({total_elapsed/3600:.2f} hr)")
            if total_elapsed > 0:
                R(f"- **Duty cycle:** {total_good/total_elapsed*100:.1f}%")
            R(f"- **Longest GTI:** {longest:.1f} s")
            R(f"- **Shortest GTI:** {shortest:.1f} s")
            R()
    except Exception as e:
        R(f"**Error:** {e}")
        R()

# HEL1OS time coverage
R("### HEL1OS Time Coverage")
R()
R("Scanning all zip files for time range (from filenames)...")
R()

# Parse time info from filenames for overall coverage
hel_zip_names = sorted(set(f for f in os.listdir(HEL_ROOT) if f.startswith('HLS_') and f.endswith('.zip') and '(1)' not in f))
# Filename format: HLS_YYYYMMDD_HHMMSS_DURATIONsec_lev1_VXXX.zip
hel_dates = []
for zn in hel_zip_names:
    parts = zn.replace('.zip','').split('_')
    if len(parts) >= 2:
        hel_dates.append(parts[1])
if hel_dates:
    R(f"- **Date range from filenames:** {min(hel_dates)} to {max(hel_dates)}")
    R(f"- **Total observations:** {len(hel_dates)}")
R()

# Precise time range from extracted sample files
R("**Precise time range from extracted sample FITS headers:**")
R()
all_tstarts = []
all_tstops = []
for f in hel_fits:
    ts, te = get_time_range(f)
    if ts is not None:
        all_tstarts.append(ts)
        all_tstops.append(te)
if all_tstarts:
    R(f"- **TSTART min:** {min(all_tstarts)}")
    R(f"- **TSTOP max:** {max(all_tstops)}")
R()

# GTI analysis for HEL1OS
hel_gti_files = hel_by_type.get('gti', [])
R("**Separate GTI files in HEL1OS observations:**")
R()
if hel_gti_files:
    for f in hel_gti_files[:4]:
        R(f"- `{os.path.basename(f)}`")
    R()
    # Analyze 2 sample GTIs
    for f in hel_gti_files[:2]:
        analyze_gti(f, os.path.basename(f))
else:
    R("No separate GTI files found.")
    R()

# SoLEXS time coverage
R("### SoLEXUS (SoLEXS) Time Coverage")
R()

slx_zip_names = sorted(set(f for f in os.listdir(SLX_ROOT) if f.endswith('.zip') and '(1)' not in f))
slx_dates = []
for zn in slx_zip_names:
    # AL1_SLX_L1_YYYYMMDD_v1.0.zip
    parts = zn.replace('.zip','').split('_')
    for p in parts:
        if len(p) == 8 and p.isdigit():
            slx_dates.append(p)
            break
if slx_dates:
    R(f"- **Date range from filenames:** {min(slx_dates)} to {max(slx_dates)}")
    R(f"- **Total observations:** {len(slx_dates)}")
R()

# Precise time from extracted samples
R("**Precise time range from extracted sample FITS headers:**")
R()
slx_tstarts = []
slx_tstops = []
for f in slx_all:
    ts, te = get_time_range(f)
    if ts is not None:
        slx_tstarts.append(ts)
        slx_tstops.append(te)
if slx_tstarts:
    R(f"- **TSTART min:** {min(slx_tstarts)}")
    R(f"- **TSTOP max:** {max(slx_tstops)}")
R()

slx_gti_files = slx_by_type.get('gti', [])
if slx_gti_files:
    R("**Separate GTI files in SoLEXS observations:**")
    R()
    for f in slx_gti_files[:6]:
        R(f"- `{os.path.basename(f)}`")
    R()
    for f in slx_gti_files[:2]:
        analyze_gti(f, os.path.basename(f))

# ─────────────────────────────────────────────
# STEP 4: Sample Event Data
# ─────────────────────────────────────────────
R("## Step 4 — Sample Event Data")
R()

def analyze_events(fits_path, label):
    R(f"### {label}")
    R(f"**File:** `{os.path.basename(fits_path)}` ({format_size(os.path.getsize(fits_path))})")
    R()
    try:
        with fits.open(fits_path) as hdul:
            evt_hdu = None
            for hdu in hdul:
                if hdu.name in ('EVENTS', 'EVENT', 'RATE'):
                    evt_hdu = hdu
                    break
                if hasattr(hdu, 'columns') and hdu.columns is not None:
                    cols = [c.name.upper() for c in hdu.columns]
                    if 'TIME' in cols and ('CHANNEL' in cols or 'PI' in cols or 'PHA' in cols or 'ENERGY' in cols):
                        evt_hdu = hdu
                        break

            if evt_hdu is None:
                # If no events HDU, just show first binary table
                for hdu in hdul:
                    if hasattr(hdu, 'columns') and hdu.columns is not None and hdu.data is not None:
                        evt_hdu = hdu
                        break

            if evt_hdu is None:
                R("No event/data table found.")
                R()
                return

            data = evt_hdu.data
            ncols = [c.name for c in evt_hdu.columns]
            R(f"- **HDU name:** `{evt_hdu.name}`")
            R(f"- **Total rows:** {len(data):,}")
            R(f"- **Columns:** {', '.join(ncols)}")
            R()

            # First 5 rows
            R("**First 5 rows:**")
            R()
            R("| " + " | ".join(ncols) + " |")
            R("| " + " | ".join(["---"]*len(ncols)) + " |")
            for row_idx in range(min(5, len(data))):
                vals = []
                for col in ncols:
                    v = data[col][row_idx]
                    if hasattr(v, '__len__') and not isinstance(v, str):
                        if len(v) <= 5:
                            vals.append(str(v))
                        else:
                            vals.append(f"[array len={len(v)}]")
                    else:
                        vals.append(str(v))
                R("| " + " | ".join(vals) + " |")
            R()

            # Time info
            if 'TIME' in ncols:
                times = data['TIME']
                R(f"- **Time range:** {times[0]} to {times[-1]}")
                R(f"- **Time delta (first to last):** {times[-1] - times[0]:.1f} s ({(times[-1]-times[0])/3600:.2f} hr)")
                R()

            # Energy/channel histogram
            energy_col = None
            for candidate in ['ENERGY', 'PI', 'PHA', 'CHANNEL']:
                if candidate in ncols:
                    energy_col = candidate
                    break

            if energy_col is not None:
                edata = data[energy_col]
                if hasattr(edata[0], '__len__'):
                    R(f"- **`{energy_col}` column is array-valued** (not scalar per event)")
                    R()
                else:
                    edata = edata.astype(float)
                    valid = edata[np.isfinite(edata)]
                    if len(valid) > 0:
                        hist, edges = np.histogram(valid, bins=10)
                        R(f"**{energy_col} histogram (10 bins):**")
                        R()
                        R("| Bin Range | Count |")
                        R("|-----------|-------|")
                        for j in range(len(hist)):
                            R(f"| {edges[j]:.1f} – {edges[j+1]:.1f} | {hist[j]:,} |")
                        R()
                        R(f"- **{energy_col} range:** {valid.min():.1f} to {valid.max():.1f}")
                        R(f"- **{energy_col} median:** {np.median(valid):.1f}")
                        R()
    except Exception as e:
        R(f"**Error:** {e}")
        R(f"```\n{traceback.format_exc()}\n```")
        R()

# HEL1OS events
hel_evt_files = hel_by_type.get('events', [])
if hel_evt_files:
    analyze_events(hel_evt_files[0], "HEL1OS Event List")

# SoLEXS — check if there are event lists or if .pi files serve as spectra
# SoLEXS likely uses .pi (pulse-height spectra) rather than event lists
slx_pi_files = slx_by_type.get('spectrum', [])
if slx_pi_files:
    analyze_events(slx_pi_files[0], "SoLEXS Spectrum (PI file)")

slx_lc_files = slx_by_type.get('lightcurve', [])
if slx_lc_files:
    analyze_events(slx_lc_files[0], "SoLEXS Light Curve")

# Also show a HEL1OS lightcurve and spectra sample
hel_lc_files = hel_by_type.get('lightcurve', [])
if hel_lc_files:
    analyze_events(hel_lc_files[0], "HEL1OS Light Curve (CdTe)")

hel_spec_files = hel_by_type.get('spectra', [])
if hel_spec_files:
    analyze_events(hel_spec_files[0], "HEL1OS Spectra (CdTe)")

# ─────────────────────────────────────────────
# STEP 5: Detector-Specific Checks
# ─────────────────────────────────────────────
R("## Step 5 — Detector-Specific Checks")
R()

R("### HEL1OS Detector Distinction")
R()

# Check HEL1OS: CdTe vs CZT separation
R("**Directory-level separation:**")
R()
R("- HEL1OS organizes data into separate subdirectories per detector type:")
R("  - `cdte/` — CdTe detector files (lightcurves + spectra)")
R("  - `czt/` — CZT detector files (lightcurves + spectra)")
R("  - `events/` — Combined event list (`evt.fits`)")
R("  - `aux/` — GTI files per detector (`gticdte1.fits`, `gticdte2.fits`, `gticzt1.fits`, `gticzt2.fits`) + housekeeping")
R()

# Check event file for DET_ID, QUADRANT columns
R("**Checking event file for detector/quadrant columns:**")
R()
if hel_evt_files:
    try:
        with fits.open(hel_evt_files[0]) as hdul:
            for hdu in hdul:
                if hasattr(hdu, 'columns') and hdu.columns is not None:
                    cols = [c.name for c in hdu.columns]
                    det_cols = [c for c in cols if any(k in c.upper() for k in
                               ['DET', 'QUAD', 'MODULE', 'PIXEL', 'DETECTOR'])]
                    R(f"- HDU `{hdu.name}`: all columns = {cols}")
                    if det_cols:
                        R(f"  - **Detector-related columns found:** {det_cols}")
                        for dc in det_cols:
                            vals = hdu.data[dc]
                            unique = np.unique(vals)
                            if len(unique) <= 20:
                                R(f"    - `{dc}` unique values: {list(unique)}")
                            else:
                                R(f"    - `{dc}` has {len(unique)} unique values (range: {vals.min()} to {vals.max()})")
                    R()
    except Exception as e:
        R(f"Error: {e}")
        R()

# Check filenames for QUAD patterns
R("**Filename patterns in HEL1OS zips:**")
R()
hel_all_names = set()
for zf_name in hel_zip_names[:20]:
    try:
        with zipfile.ZipFile(os.path.join(HEL_ROOT, zf_name)) as z:
            for info in z.infolist():
                hel_all_names.add(os.path.basename(info.filename))
    except:
        pass
quad_names = [n for n in hel_all_names if any(q in n.upper() for q in ['QUAD', 'Q0', 'Q1', 'Q2', 'Q3'])]
if quad_names:
    R(f"- Files with QUAD/Q0-Q3 in name: {sorted(quad_names)}")
else:
    R("- No QUAD/Q0-Q3 patterns found in filenames")
R()

det_names = sorted(set(n for n in hel_all_names if n.endswith('.fits') or n.endswith('.txt')))
R("**Unique file basenames across observations:**")
R()
for n in det_names:
    R(f"- `{n}`")
R()

# Check spectra header for detector info
R("**Checking spectra headers for detector identification:**")
R()
for ftype_label, flist in [("CdTe spectra", [f for f in hel_by_type.get('spectra',[]) if 'cdte' in f.lower()]),
                            ("CZT spectra", [f for f in hel_by_type.get('spectra',[]) if 'czt' in f.lower()])]:
    if flist:
        try:
            with fits.open(flist[0]) as hdul:
                h = hdul[0].header if len(hdul) > 0 else None
                if h:
                    for key in ['DETNAM','DET_ID','INSTRUME','FILTER','OBJECT','ORIGIN',
                                'CREATOR','TELESCOP']:
                        if key in h:
                            R(f"- {ftype_label} — `{key}` = `{h[key]}`")
                # Also check extension headers
                if len(hdul) > 1:
                    h1 = hdul[1].header
                    for key in ['DETNAM','DET_ID','INSTRUME','FILTER','CHANTYPE','DETCHANS']:
                        if key in h1:
                            R(f"- {ftype_label} ext1 — `{key}` = `{h1[key]}`")
        except Exception as e:
            R(f"- Error reading {ftype_label}: {e}")
R()

R("### SoLEXS Detector Distinction")
R()
R("**Directory-level separation:**")
R()
R("- SoLEXS organizes data into separate subdirectories per detector:")
R("  - `SDD1/` — Silicon Drift Detector 1")
R("  - `SDD2/` — Silicon Drift Detector 2")
R()

# Check SoLEXS headers for detector info
R("**Checking SoLEXS file headers for detector identification:**")
R()
for ftype, flist in slx_by_type.items():
    for f in flist[:2]:
        try:
            with fits.open(f) as hdul:
                for i, hdu in enumerate(hdul):
                    h = hdu.header
                    for key in ['DETNAM','DET_ID','INSTRUME','FILTER','OBJECT','APERTURE',
                                'TELESCOP','CREATOR','ORIGIN','CHANTYPE','DETCHANS']:
                        if key in h:
                            R(f"- `{os.path.basename(f)}` HDU{i} — `{key}` = `{h[key]}`")
        except Exception as e:
            R(f"- Error reading {os.path.basename(f)}: {e}")
R()

# Check what files exist per SDD
R("**File presence per SDD subdirectory (across all extracted samples):**")
R()
sdd1_files_all = []
sdd2_files_all = []
for obs_dir in glob.glob(os.path.join(SLX_EXTRACT, "AL1_SLX_*")):
    sdd1 = os.path.join(obs_dir, "SDD1")
    sdd2 = os.path.join(obs_dir, "SDD2")
    if os.path.isdir(sdd1):
        sdd1_files_all.extend(os.listdir(sdd1))
    if os.path.isdir(sdd2):
        sdd2_files_all.extend(os.listdir(sdd2))

R(f"- **SDD1 file types:** {sorted(set(os.path.splitext(f)[-1] if not f.endswith('.gz') else os.path.splitext(f[:-3])[-1]+'.gz' for f in sdd1_files_all))}")
R(f"- **SDD1 file count:** {len(sdd1_files_all)}")
R(f"- **SDD2 file types:** {sorted(set(os.path.splitext(f)[-1] if not f.endswith('.gz') else os.path.splitext(f[:-3])[-1]+'.gz' for f in sdd2_files_all))}")
R(f"- **SDD2 file count:** {len(sdd2_files_all)}")
R()
if sdd1_files_all:
    R(f"- **SDD1 sample filenames:** {sorted(set(sdd1_files_all))[:5]}")
if sdd2_files_all:
    R(f"- **SDD2 sample filenames:** {sorted(set(sdd2_files_all))[:5]}")
R()

# ─────────────────────────────────────────────
# STEP 6: Anomaly Check
# ─────────────────────────────────────────────
R("## Step 6 — Anomaly Check")
R()

anomalies = []

# Check for zero-size files in extracted samples
R("### Zero-size files")
R()
zero_files = []
for base in [HEL_EXTRACT, SLX_EXTRACT]:
    for dirpath, dirnames, filenames in os.walk(base):
        for f in filenames:
            fpath = os.path.join(dirpath, f)
            if os.path.getsize(fpath) == 0:
                zero_files.append(fpath)
if zero_files:
    R(f"Found {len(zero_files)} zero-size files:")
    for f in zero_files:
        R(f"- `{f}`")
        anomalies.append(f"Zero-size: {f}")
else:
    R("No zero-size files found in extracted samples.")
R()

# Check for files that fail to open
R("### Files that fail to open with astropy")
R()
fail_files = []
all_extracted_fits = find_fits_files(HEL_EXTRACT) + find_fits_files(SLX_EXTRACT)
for f in all_extracted_fits:
    try:
        with fits.open(f) as hdul:
            _ = len(hdul)
    except Exception as e:
        fail_files.append((f, str(e)))
if fail_files:
    R(f"Found {len(fail_files)} files that fail to open:")
    for f, err in fail_files:
        R(f"- `{os.path.basename(f)}`: {err}")
        anomalies.append(f"Failed to open: {os.path.basename(f)}")
else:
    R("All extracted FITS files opened successfully.")
R()

# Check for missing/zero EXPOSURE
R("### Missing or zero EXPOSURE")
R()
zero_exp = []
for f in all_extracted_fits:
    try:
        with fits.open(f) as hdul:
            for hdu in hdul:
                if 'EXPOSURE' in hdu.header:
                    exp = hdu.header['EXPOSURE']
                    if exp == 0 or exp is None:
                        zero_exp.append((f, exp))
                    break
    except:
        pass
if zero_exp:
    R(f"Found {len(zero_exp)} files with zero/missing EXPOSURE:")
    for f, exp in zero_exp:
        R(f"- `{os.path.basename(f)}`: EXPOSURE={exp}")
        anomalies.append(f"Zero EXPOSURE: {os.path.basename(f)}")
else:
    R("No files with zero or missing EXPOSURE found.")
R()

# Check TSTART > TSTOP
R("### TSTART > TSTOP")
R()
bad_time = []
for f in all_extracted_fits:
    ts, te = get_time_range(f)
    if ts is not None and te is not None and ts > te:
        bad_time.append((f, ts, te))
if bad_time:
    R(f"Found {len(bad_time)} files where TSTART > TSTOP:")
    for f, ts, te in bad_time:
        R(f"- `{os.path.basename(f)}`: TSTART={ts}, TSTOP={te}")
        anomalies.append(f"TSTART > TSTOP: {os.path.basename(f)}")
else:
    R("No files with TSTART > TSTOP.")
R()

# Check for duplicate zip files
R("### Duplicate zip files")
R()
hel_dups = [f for f in os.listdir(HEL_ROOT) if '(1)' in f and f.endswith('.zip')]
slx_dups = [f for f in os.listdir(SLX_ROOT) if '(1)' in f and f.endswith('.zip')]
R(f"- **HEL1OS duplicate zips:** {len(hel_dups)}")
R(f"- **SoLEXUS duplicate zips:** {len(slx_dups)}")
if hel_dups:
    R(f"  - Sample: {hel_dups[:3]}")
if slx_dups:
    R(f"  - Sample: {slx_dups[:3]}")
R()

# Summary
R("### Anomaly Summary")
R()
if anomalies:
    R(f"**{len(anomalies)} anomalies found:**")
    for a in anomalies:
        R(f"- {a}")
else:
    R("**No anomalies found** in the extracted sample files.")
R()

# ─────────────────────────────────────────────
# STEP 7: Suggested Loader Strategy
# ─────────────────────────────────────────────
R("## Suggested Loader Strategy")
R()
R("### What constitutes one observation?")
R()
R("#### HEL1OS")
R()
R("One HEL1OS observation = one zip file with naming pattern:")
R("```")
R("HLS_YYYYMMDD_HHMMSS_DDDDDsec_lev1_VXYZ.zip")
R("```")
R("where `YYYYMMDD_HHMMSS` is the start time, `DDDDDsec` is the duration, and `VXYZ` is the version.")
R()
R("Each observation zip extracts to a directory tree:")
R("```")
R("YYYY/MM/DD/HLS_.../")
R("  ├── events/evt.fits           # Combined event list (all detectors)")
R("  ├── cdte/                     # CdTe detector (low energy, ~1-30 keV)")
R("  │   ├── lightcurve_cdte1.fits")
R("  │   ├── lightcurve_cdte2.fits")
R("  │   ├── hel1os_cdte_spectra_cdte1.fits")
R("  │   └── hel1os_cdte_spectra_cdte2.fits")
R("  ├── czt/                      # CZT detector (high energy, ~20-200 keV)")
R("  │   ├── lightcurve_czt1.fits")
R("  │   ├── lightcurve_czt2.fits")
R("  │   ├── hel1os_czt_spectra_czt1.fits")
R("  │   └── hel1os_czt_spectra_czt2.fits")
R("  └── aux/")
R("      ├── hk.fits               # Housekeeping")
R("      ├── gticdte1.fits          # GTI for CdTe detector 1")
R("      ├── gticdte2.fits")
R("      ├── gticzt1.fits           # GTI for CZT detector 1")
R("      ├── gticzt2.fits")
R("      └── cztdis/               # CZT disabled pixel lists")
R("```")
R()
R("**Loader approach:**")
R("1. Enumerate zip files, parse `YYYYMMDD_HHMMSS` + version from filename")
R("2. Extract to temp directory (or read directly from zip using `astropy.io.fits` + `io.BytesIO`)")
R("3. For each observation, load: event list + per-detector lightcurves + spectra + GTIs")
R("4. Detectors are distinguished by **subdirectory** (`cdte/` vs `czt/`) and **filename suffix** (`_cdte1`, `_cdte2`, `_czt1`, `_czt2`)")
R("5. Each detector type has two units (1, 2) with independent files and GTIs")
R()
R("#### SoLEXS")
R()
R("One SoLEXS observation = one zip file with naming pattern:")
R("```")
R("AL1_SLX_L1_YYYYMMDD_v1.0.zip")
R("```")
R()
R("Each observation zip extracts to:")
R("```")
R("AL1_SLX_L1_YYYYMMDD_v1.0/")
R("  ├── SDD1/                          # Silicon Drift Detector 1")
R("  │   └── AL1_SOLEXS_YYYYMMDD_SDD1_L1.gti.gz")
R("  └── SDD2/                          # Silicon Drift Detector 2")
R("      ├── AL1_SOLEXS_YYYYMMDD_SDD2_L1.gti.gz")
R("      ├── AL1_SOLEXS_YYYYMMDD_SDD2_L1.lc.gz")
R("      └── AL1_SOLEXS_YYYYMMDD_SDD2_L1.pi.gz")
R("```")
R()
R("**Key observations:**")
R("- SDD1 typically only has a GTI file (no lightcurve or spectrum)")
R("- SDD2 has GTI + lightcurve + spectrum (PI) files")
R("- All files are gzip-compressed FITS (`.gz`)")
R("- `astropy.io.fits.open()` handles `.gz` transparently")
R()
R("**Loader approach:**")
R("1. Enumerate zip files, parse `YYYYMMDD` from filename")
R("2. Extract to temp directory")
R("3. For each observation, load SDD1 and SDD2 data separately")
R("4. Detectors are distinguished by **subdirectory** (`SDD1/` vs `SDD2/`) and **filename** (`_SDD1_` vs `_SDD2_`)")
R("5. Handle the asymmetry: SDD1 may only have GTI, while SDD2 has the science data")
R()
R("### Calibration Files")
R()
R("HEL1OS calibration responses are in separate zip archives:")
R("- `CAL_epoch20231001_CdTeResponseReader.zip` → ARF + SRF (RMF) for CdTe")
R("- `CAL_epoch20231001_CZTResponseReader.zip` → ARF + SRF (RMF) for CZT")
R("- Each also includes an IDL `.pro` script for reference")
R()
R("### Deduplication Note")
R()
R("Both data sets contain duplicate zip files with `(1)` suffix (browser re-downloads).")
R("The loader should filter these out by default.")
R()

# Write report
output_path = "D:/Data/data_inventory.md"
with open(output_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(report))

print(f"Report written to {output_path}")
print(f"Total lines: {len(report)}")
