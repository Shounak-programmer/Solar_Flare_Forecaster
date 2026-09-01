# Aditya-L1 SoLEXS & HEL1OS Data Inventory Report

## Step 1 — Directory Inventory

### HEL1OS: `D:/Data/HEL1OS`

- **Total zip files on disk:** 1703 (73.7 GB)
- **Duplicate zips (with '(1)' suffix):** 417
- **Unique observations:** 1286
- **Total files inside zips:** 20258

**File counts by type (inside zips):**

| Extension | Count | Total Size (uncompressed) |
|-----------|-------|--------------------------|
| `.fits` | 17678 | 365.4 GB |
| `.txt` | 2578 | 16.4 KB |
| `.pro` | 2 | 10.1 KB |

**Sample observation tree:** `HLS_20240701_000211_43057sec_lev1_V111`
```
HLS_20240701_000211_43057sec_lev1_V111/
  aux/
    gticdte1.fits  (8.4 KB)
    gticdte2.fits  (8.4 KB)
    gticzt1.fits  (8.4 KB)
    gticzt2.fits  (8.4 KB)
    hk.fits  (2.4 MB)
    cztdis/
      czt1dispix.txt  (13.0 B)
      czt2dispix.txt  (0.0 B)
  cdte/
    hel1os_cdte_spectra_cdte1.fits  (21.1 MB)
    hel1os_cdte_spectra_cdte2.fits  (21.1 MB)
    lightcurve_cdte1.fits  (11.1 MB)
    lightcurve_cdte2.fits  (11.1 MB)
  czt/
    hel1os_czt_spectra_czt1.fits  (14.1 MB)
    hel1os_czt_spectra_czt2.fits  (14.1 MB)
    lightcurve_czt1.fits  (11.1 MB)
    lightcurve_czt2.fits  (11.1 MB)
  events/
    evt.fits  (149.3 MB)
```

### SoLEXUS (SoLEXS): `D:/Data/SoLEXUS`

- **Total zip files on disk:** 1040 (5.7 GB)
- **Duplicate zips (with '(1)' suffix):** 199
- **Unique observations:** 841
- **Total files inside zips:** 3374
- **Extracted directories:** AL1_SLX_L1_20260613_v1.0

**File counts by type (inside zips):**

| Extension | Count | Total Size (uncompressed) |
|-----------|-------|--------------------------|
| `.gti.gz` | 1682 | 1.6 MB |
| `.lc.gz` | 841 | 221.8 MB |
| `.pi.gz` | 841 | 6.4 GB |
| `.hk.gz` | 5 | 7.4 MB |
| `.png` | 5 | 417.4 KB |

**Sample observation tree:** `AL1_SLX_L1_20240201_v1.0`
```
AL1_SLX_L1_20240201_v1.0/
  SDD1/
    AL1_SOLEXS_20240201_SDD1_L1.gti.gz  (957.0 B)
  SDD2/
    AL1_SOLEXS_20240201_SDD2_L1.gti.gz  (1.0 KB)
    AL1_SOLEXS_20240201_SDD2_L1.lc.gz  (258.5 KB)
    AL1_SOLEXS_20240201_SDD2_L1.pi.gz  (8.1 MB)
```

## Step 2 — FITS Structure Inspection

### HEL1OS Representative Files

Found 42 FITS files across extracted observations:

- **events:** 3 files
- **gti:** 12 files
- **housekeeping:** 3 files
- **lightcurve:** 12 files
- **spectra:** 12 files

### HEL1OS events
**File:** `D:/Data/_analysis_tmp\HEL1OS\2024\07\01\HLS_20240701_000211_43057sec_lev1_V111\events\evt.fits`
**Size:** 149.3 MB

**HDU Summary:**
```
Filename: D:/Data/_analysis_tmp\HEL1OS\2024\07\01\HLS_20240701_000211_43057sec_lev1_V111\events\evt.fits
No.    Name      Ver    Type      Cards   Dimensions   Format
  0  PRIMARY       1 PrimaryHDU      26   ()      
  1  CDTE1-EVENTS    1 BinTableHDU     33   64027R x 7C   [D, D, D, I, D, J, 23A]   
  2  CDTE2-EVENTS    1 BinTableHDU     33   46808R x 7C   [D, D, D, I, D, J, 23A]   
  3  CZT1-EVENTS    1 BinTableHDU     37   1208561R x 9C   [D, D, D, B, I, I, D, J, 23A]   
  4  CZT2-EVENTS    1 BinTableHDU     37   1130770R x 9C   [D, D, D, B, I, I, D, J, 23A]
```

**HDU 0: name=`PRIMARY`, type=`PrimaryHDU`**

| Key | Value |
|-----|-------|
| `TELESCOP` | `Aditya-L1` |
| `INSTRUME` | `HEL1OS` |
| `CREATOR` | `HEL1OS-L1-PIPELINE` |

**HDU 1: name=`CDTE1-EVENTS`, type=`BinTableHDU`**

| Key | Value |
|-----|-------|
| `TSTART` | `60492.00151898259` |
| `TSTOP` | `60492.49971047187` |
| `DETNAM` | `CdTe1` |

**Columns:**

| Name | Unit | Format |
|------|------|--------|
| `mjd` | `None` | `D` |
| `hlsobt` | `s` | `D` |
| `currtemp` | `degC` | `D` |
| `chn` | `None` | `I` |
| `ener` | `keV` | `D` |
| `recnum` | `None` | `J` |
| `utc-isot` | `None` | `23A` |

**HDU 2: name=`CDTE2-EVENTS`, type=`BinTableHDU`**

| Key | Value |
|-----|-------|
| `TSTART` | `60492.00151898259` |
| `TSTOP` | `60492.49979149244` |
| `DETNAM` | `CdTe2` |

**Columns:**

| Name | Unit | Format |
|------|------|--------|
| `mjd` | `None` | `D` |
| `hlsobt` | `s` | `D` |
| `currtemp` | `degC` | `D` |
| `chn` | `None` | `I` |
| `ener` | `keV` | `D` |
| `recnum` | `None` | `J` |
| `utc-isot` | `None` | `23A` |

**HDU 3: name=`CZT1-EVENTS`, type=`BinTableHDU`**

| Key | Value |
|-----|-------|
| `TSTART` | `60492.00151898259` |
| `TSTOP` | `60492.49979149244` |
| `DETNAM` | `CZT1` |

**Columns:**

| Name | Unit | Format |
|------|------|--------|
| `mjd` | `None` | `D` |
| `hlsobt` | `s` | `D` |
| `currtemp` | `degC` | `D` |
| `pix` | `None` | `B` |
| `chn` | `None` | `I` |
| `offsetchn` | `None` | `I` |
| `ener` | `keV` | `D` |
| `recnum` | `None` | `J` |
| `utc-isot` | `None` | `23A` |

**HDU 4: name=`CZT2-EVENTS`, type=`BinTableHDU`**

| Key | Value |
|-----|-------|
| `TSTART` | `60492.00151898259` |
| `TSTOP` | `60492.49979149244` |
| `DETNAM` | `CZT2` |

**Columns:**

| Name | Unit | Format |
|------|------|--------|
| `mjd` | `None` | `D` |
| `hlsobt` | `s` | `D` |
| `currtemp` | `degC` | `D` |
| `pix` | `None` | `B` |
| `chn` | `None` | `I` |
| `offsetchn` | `None` | `I` |
| `ener` | `keV` | `D` |
| `recnum` | `None` | `J` |
| `utc-isot` | `None` | `23A` |

### HEL1OS lightcurve (CdTe)
**File:** `D:/Data/_analysis_tmp\HEL1OS\2024\07\01\HLS_20240701_000211_43057sec_lev1_V111\cdte\lightcurve_cdte1.fits`
**Size:** 11.1 MB

**HDU Summary:**
```
Filename: D:/Data/_analysis_tmp\HEL1OS\2024\07\01\HLS_20240701_000211_43057sec_lev1_V111\cdte\lightcurve_cdte1.fits
No.    Name      Ver    Type      Cards   Dimensions   Format
  0  PRIMARY       1 PrimaryHDU      26   ()      
  1  CDTE1_LC_BAND_5.00KEV_TO_20.00KEV    1 BinTableHDU     33   43003R x 4C   [D, 30A, D, D]   
  2  CDTE1_LC_BAND_20.00KEV_TO_30.00KEV    1 BinTableHDU     33   42980R x 4C   [D, 30A, D, D]   
  3  CDTE1_LC_BAND_30.00KEV_TO_40.00KEV    1 BinTableHDU     33   42905R x 4C   [D, 30A, D, D]   
  4  CDTE1_LC_BAND_40.00KEV_TO_60.00KEV    1 BinTableHDU     33   43019R x 4C   [D, 30A, D, D]   
  5  CDTE1_LC_BAND_1.80KEV_TO_90.00KEV    1 BinTableHDU     33   43043R x 4C   [D, 30A, D, D]
```

**HDU 0: name=`PRIMARY`, type=`PrimaryHDU`**

| Key | Value |
|-----|-------|
| `TELESCOP` | `Aditya-L1` |
| `INSTRUME` | `HEL1OS` |
| `CREATOR` | `HEL1OS-L1-PIPELINE` |

**HDU 1: name=`CDTE1_LC_BAND_5.00KEV_TO_20.00KEV`, type=`BinTableHDU`**

| Key | Value |
|-----|-------|
| `TSTART` | `60492.00151898259` |
| `TSTOP` | `60492.49923888999` |
| `DETNAM` | `CdTe1` |

**Columns:**

| Name | Unit | Format |
|------|------|--------|
| `MJD` | `MJD` | `D` |
| `ISOT` | `UT` | `30A` |
| `CTR` | `cts/sec` | `D` |
| `STAT_ERR` | `cts/sec` | `D` |

**HDU 2: name=`CDTE1_LC_BAND_20.00KEV_TO_30.00KEV`, type=`BinTableHDU`**

| Key | Value |
|-----|-------|
| `TSTART` | `60492.00189831055` |
| `TSTOP` | `60492.49935201425` |
| `DETNAM` | `CdTe1` |

**Columns:**

| Name | Unit | Format |
|------|------|--------|
| `MJD` | `MJD` | `D` |
| `ISOT` | `UT` | `30A` |
| `CTR` | `cts/sec` | `D` |
| `STAT_ERR` | `cts/sec` | `D` |

**HDU 3: name=`CDTE1_LC_BAND_30.00KEV_TO_40.00KEV`, type=`BinTableHDU`**

| Key | Value |
|-----|-------|
| `TSTART` | `60492.00248883704` |
| `TSTOP` | `60492.49907448519` |
| `DETNAM` | `CdTe1` |

**Columns:**

| Name | Unit | Format |
|------|------|--------|
| `MJD` | `MJD` | `D` |
| `ISOT` | `UT` | `30A` |
| `CTR` | `cts/sec` | `D` |
| `STAT_ERR` | `cts/sec` | `D` |

**HDU 4: name=`CDTE1_LC_BAND_40.00KEV_TO_60.00KEV`, type=`BinTableHDU`**

| Key | Value |
|-----|-------|
| `TSTART` | `60492.00171284195` |
| `TSTOP` | `60492.49961793454` |
| `DETNAM` | `CdTe1` |

**Columns:**

| Name | Unit | Format |
|------|------|--------|
| `MJD` | `MJD` | `D` |
| `ISOT` | `UT` | `30A` |
| `CTR` | `cts/sec` | `D` |
| `STAT_ERR` | `cts/sec` | `D` |

**HDU 5: name=`CDTE1_LC_BAND_1.80KEV_TO_90.00KEV`, type=`BinTableHDU`**

| Key | Value |
|-----|-------|
| `TSTART` | `60492.00151898259` |
| `TSTOP` | `60492.49970185295` |
| `DETNAM` | `CdTe1` |

**Columns:**

| Name | Unit | Format |
|------|------|--------|
| `MJD` | `MJD` | `D` |
| `ISOT` | `UT` | `30A` |
| `CTR` | `cts/sec` | `D` |
| `STAT_ERR` | `cts/sec` | `D` |

### HEL1OS lightcurve (CZT)
**File:** `D:/Data/_analysis_tmp\HEL1OS\2024\07\01\HLS_20240701_000211_43057sec_lev1_V111\czt\lightcurve_czt1.fits`
**Size:** 11.1 MB

**HDU Summary:**
```
Filename: D:/Data/_analysis_tmp\HEL1OS\2024\07\01\HLS_20240701_000211_43057sec_lev1_V111\czt\lightcurve_czt1.fits
No.    Name      Ver    Type      Cards   Dimensions   Format
  0  PRIMARY       1 PrimaryHDU      26   ()      
  1  CZT1_LC_BAND_20.00KEV_TO_40.00KEV    1 BinTableHDU     33   43050R x 4C   [D, 30A, D, D]   
  2  CZT1_LC_BAND_40.00KEV_TO_60.00KEV    1 BinTableHDU     33   43050R x 4C   [D, 30A, D, D]   
  3  CZT1_LC_BAND_60.00KEV_TO_80.00KEV    1 BinTableHDU     33   43050R x 4C   [D, 30A, D, D]   
  4  CZT1_LC_BAND_80.00KEV_TO_150.00KEV    1 BinTableHDU     33   43050R x 4C   [D, 30A, D, D]   
  5  CZT1_LC_BAND_18.00KEV_TO_160.00KEV    1 BinTableHDU     33   43050R x 4C   [D, 30A, D, D]
```

**HDU 0: name=`PRIMARY`, type=`PrimaryHDU`**

| Key | Value |
|-----|-------|
| `TELESCOP` | `Aditya-L1` |
| `INSTRUME` | `HEL1OS` |
| `CREATOR` | `HEL1OS-L1-PIPELINE` |

**HDU 1: name=`CZT1_LC_BAND_20.00KEV_TO_40.00KEV`, type=`BinTableHDU`**

| Key | Value |
|-----|-------|
| `TSTART` | `60492.00151898259` |
| `TSTOP` | `60492.49978287148` |
| `DETNAM` | `CZT1` |

**Columns:**

| Name | Unit | Format |
|------|------|--------|
| `MJD` | `MJD` | `D` |
| `ISOT` | `UT` | `30A` |
| `CTR` | `cts/sec` | `D` |
| `STAT_ERR` | `cts/sec` | `D` |

**HDU 2: name=`CZT1_LC_BAND_40.00KEV_TO_60.00KEV`, type=`BinTableHDU`**

| Key | Value |
|-----|-------|
| `TSTART` | `60492.00151898259` |
| `TSTOP` | `60492.49978287148` |
| `DETNAM` | `CZT1` |

**Columns:**

| Name | Unit | Format |
|------|------|--------|
| `MJD` | `MJD` | `D` |
| `ISOT` | `UT` | `30A` |
| `CTR` | `cts/sec` | `D` |
| `STAT_ERR` | `cts/sec` | `D` |

**HDU 3: name=`CZT1_LC_BAND_60.00KEV_TO_80.00KEV`, type=`BinTableHDU`**

| Key | Value |
|-----|-------|
| `TSTART` | `60492.00151898259` |
| `TSTOP` | `60492.49978287148` |
| `DETNAM` | `CZT1` |

**Columns:**

| Name | Unit | Format |
|------|------|--------|
| `MJD` | `MJD` | `D` |
| `ISOT` | `UT` | `30A` |
| `CTR` | `cts/sec` | `D` |
| `STAT_ERR` | `cts/sec` | `D` |

**HDU 4: name=`CZT1_LC_BAND_80.00KEV_TO_150.00KEV`, type=`BinTableHDU`**

| Key | Value |
|-----|-------|
| `TSTART` | `60492.00151898259` |
| `TSTOP` | `60492.49978287148` |
| `DETNAM` | `CZT1` |

**Columns:**

| Name | Unit | Format |
|------|------|--------|
| `MJD` | `MJD` | `D` |
| `ISOT` | `UT` | `30A` |
| `CTR` | `cts/sec` | `D` |
| `STAT_ERR` | `cts/sec` | `D` |

**HDU 5: name=`CZT1_LC_BAND_18.00KEV_TO_160.00KEV`, type=`BinTableHDU`**

| Key | Value |
|-----|-------|
| `TSTART` | `60492.00151898259` |
| `TSTOP` | `60492.49978287148` |
| `DETNAM` | `CZT1` |

**Columns:**

| Name | Unit | Format |
|------|------|--------|
| `MJD` | `MJD` | `D` |
| `ISOT` | `UT` | `30A` |
| `CTR` | `cts/sec` | `D` |
| `STAT_ERR` | `cts/sec` | `D` |

### HEL1OS spectra (CdTe)
**File:** `D:/Data/_analysis_tmp\HEL1OS\2024\07\01\HLS_20240701_000211_43057sec_lev1_V111\cdte\hel1os_cdte_spectra_cdte1.fits`
**Size:** 21.1 MB

**HDU Summary:**
```
Filename: D:/Data/_analysis_tmp\HEL1OS\2024\07\01\HLS_20240701_000211_43057sec_lev1_V111\cdte\hel1os_cdte_spectra_cdte1.fits
No.    Name      Ver    Type      Cards   Dimensions   Format
  0  PRIMARY       1 PrimaryHDU      26   ()      
  1  SPECTRUM      1 BinTableHDU     62   2151R x 8C   [I, 511J, 511D, 511D, 12A, D, D, D]
```

**HDU 0: name=`PRIMARY`, type=`PrimaryHDU`**

| Key | Value |
|-----|-------|
| `TELESCOP` | `Aditya-L1` |
| `INSTRUME` | `HEL1OS` |
| `CREATOR` | `HEL1OS-L1-PIPELINE` |

**HDU 1: name=`SPECTRUM`, type=`BinTableHDU`**

| Key | Value |
|-----|-------|
| `TELESCOP` | `Aditya-L1` |
| `INSTRUME` | `HEL1OS` |
| `TSTART` | `60492.00151898259` |
| `TSTOP` | `60492.49966713073` |
| `CHANTYPE` | `PHA` |
| `DETCHANS` | `511` |
| `DETNAM` | `CdTe1` |
| `HDUCLAS1` | `SPECTRUM` |
| `HDUCLAS2` | `TOTAL` |
| `HDUCLAS3` | `COUNT` |
| `RESPFILE` | `none` |
| `ANCRFILE` | `none` |
| `BACKFILE` | `none` |

**Columns:**

| Name | Unit | Format |
|------|------|--------|
| `SPEC_NUM` | `None` | `I` |
| `CHANNEL` | `None` | `511J` |
| `COUNTS` | `cts` | `511D` |
| `STAT_ERR` | `None` | `511D` |
| `ROWID` | `None` | `12A` |
| `TSTART` | `s` | `D` |
| `TSTOP` | `s` | `D` |
| `EXPOSURE` | `s` | `D` |

### HEL1OS spectra (CZT)
**File:** `D:/Data/_analysis_tmp\HEL1OS\2024\07\01\HLS_20240701_000211_43057sec_lev1_V111\czt\hel1os_czt_spectra_czt1.fits`
**Size:** 14.1 MB

**HDU Summary:**
```
Filename: D:/Data/_analysis_tmp\HEL1OS\2024\07\01\HLS_20240701_000211_43057sec_lev1_V111\czt\hel1os_czt_spectra_czt1.fits
No.    Name      Ver    Type      Cards   Dimensions   Format
  0  PRIMARY       1 PrimaryHDU      26   ()      
  1  SPECTRUM      1 BinTableHDU     62   2151R x 8C   [I, 341J, 341D, 341D, 12A, D, D, D]
```

**HDU 0: name=`PRIMARY`, type=`PrimaryHDU`**

| Key | Value |
|-----|-------|
| `TELESCOP` | `Aditya-L1` |
| `INSTRUME` | `HEL1OS` |
| `CREATOR` | `HEL1OS-L1-PIPELINE` |

**HDU 1: name=`SPECTRUM`, type=`BinTableHDU`**

| Key | Value |
|-----|-------|
| `TELESCOP` | `Aditya-L1` |
| `INSTRUME` | `HEL1OS` |
| `TSTART` | `60492.00151898259` |
| `TSTOP` | `60492.49966713073` |
| `CHANTYPE` | `PHA` |
| `DETCHANS` | `341` |
| `DETNAM` | `CZT1` |
| `HDUCLAS1` | `SPECTRUM` |
| `HDUCLAS2` | `TOTAL` |
| `HDUCLAS3` | `COUNT` |
| `RESPFILE` | `none` |
| `ANCRFILE` | `none` |
| `BACKFILE` | `none` |

**Columns:**

| Name | Unit | Format |
|------|------|--------|
| `SPEC_NUM` | `None` | `I` |
| `CHANNEL` | `None` | `341J` |
| `COUNTS` | `cts` | `341D` |
| `STAT_ERR` | `None` | `341D` |
| `ROWID` | `None` | `12A` |
| `TSTART` | `s` | `D` |
| `TSTOP` | `s` | `D` |
| `EXPOSURE` | `s` | `D` |

### HEL1OS gti (CdTe)
**File:** `D:/Data/_analysis_tmp\HEL1OS\2024\07\01\HLS_20240701_000211_43057sec_lev1_V111\aux\gticdte1.fits`
**Size:** 8.4 KB

**HDU Summary:**
```
Filename: D:/Data/_analysis_tmp\HEL1OS\2024\07\01\HLS_20240701_000211_43057sec_lev1_V111\aux\gticdte1.fits
No.    Name      Ver    Type      Cards   Dimensions   Format
  0  PRIMARY       1 PrimaryHDU      26   ()      
  1  GTI_CDTE1     1 BinTableHDU     15   1R x 2C   [D, D]
```

**HDU 0: name=`PRIMARY`, type=`PrimaryHDU`**

| Key | Value |
|-----|-------|
| `TELESCOP` | `Aditya-L1` |
| `INSTRUME` | `HEL1OS` |
| `CREATOR` | `HEL1OS-L1-PIPELINE` |

**HDU 1: name=`GTI_CDTE1`, type=`BinTableHDU`**

**Columns:**

| Name | Unit | Format |
|------|------|--------|
| `tstart` | `None` | `D` |
| `tstop` | `None` | `D` |

### HEL1OS gti (CZT)
**File:** `D:/Data/_analysis_tmp\HEL1OS\2024\07\01\HLS_20240701_000211_43057sec_lev1_V111\aux\gticzt1.fits`
**Size:** 8.4 KB

**HDU Summary:**
```
Filename: D:/Data/_analysis_tmp\HEL1OS\2024\07\01\HLS_20240701_000211_43057sec_lev1_V111\aux\gticzt1.fits
No.    Name      Ver    Type      Cards   Dimensions   Format
  0  PRIMARY       1 PrimaryHDU      26   ()      
  1  GTI_CZT1      1 BinTableHDU     15   1R x 2C   [D, D]
```

**HDU 0: name=`PRIMARY`, type=`PrimaryHDU`**

| Key | Value |
|-----|-------|
| `TELESCOP` | `Aditya-L1` |
| `INSTRUME` | `HEL1OS` |
| `CREATOR` | `HEL1OS-L1-PIPELINE` |

**HDU 1: name=`GTI_CZT1`, type=`BinTableHDU`**

**Columns:**

| Name | Unit | Format |
|------|------|--------|
| `tstart` | `None` | `D` |
| `tstop` | `None` | `D` |

### HEL1OS housekeeping
**File:** `D:/Data/_analysis_tmp\HEL1OS\2024\07\01\HLS_20240701_000211_43057sec_lev1_V111\aux\hk.fits`
**Size:** 2.4 MB

**HDU Summary:**
```
Filename: D:/Data/_analysis_tmp\HEL1OS\2024\07\01\HLS_20240701_000211_43057sec_lev1_V111\aux\hk.fits
No.    Name      Ver    Type      Cards   Dimensions   Format
  0  PRIMARY       1 PrimaryHDU      26   ()      
  1  HLSHK         1 BinTableHDU    167   5922R x 62C   [J, J, J, J, J, J, J, J, J, J, J, J, J, J, J, J, K, D, D, D, K, K, D, D, K, D, D, D, D, D, D, D, K, K, K, K, K, K, K, K, K, D, D, D, D, D, D, K, K, K, K, K, K, D, D, B, D, D, D, D, D, D]
```

**HDU 0: name=`PRIMARY`, type=`PrimaryHDU`**

| Key | Value |
|-----|-------|
| `TELESCOP` | `Aditya-L1` |
| `INSTRUME` | `HEL1OS` |
| `CREATOR` | `HEL1OS-L1-PIPELINE` |

**HDU 1: name=`HLSHK`, type=`BinTableHDU`**

| Key | Value |
|-----|-------|
| `TSTART` | `60492.00151898259` |
| `TSTOP` | `60492.49987251329` |

**Columns:**

| Name | Unit | Format |
|------|------|--------|
| `l0recnum` | `None` | `J` |
| `l0grtyr` | `None` | `J` |
| `l0grtmon` | `None` | `J` |
| `l0grtdy` | `None` | `J` |
| `l0grthr` | `None` | `J` |
| `l0grtmin` | `None` | `J` |
| `l0grtsc` | `None` | `J` |
| `l0grtmsc` | `None` | `J` |
| `l0utcyr` | `None` | `J` |
| `l0utcmon` | `None` | `J` |
| `l0utcdy` | `None` | `J` |
| `l0utchr` | `None` | `J` |
| `l0utcmin` | `None` | `J` |
| `l0utcsc` | `None` | `J` |
| `l0utcmsc` | `None` | `J` |
| `l0framecnt` | `None` | `J` |
| `l0dhobt` | `None` | `K` |
| `mjd` | `None` | `D` |
| `czt1temp` | `degC` | `D` |
| `czt2temp` | `degC` | `D` |
| `czt1bunpxst` | `None` | `K` |
| `czt2bunpxst` | `None` | `K` |
| `pagestim` | `None` | `D` |
| `cdte1ctr` | `c/s` | `D` |
| `pagenum` | `None` | `K` |
| `czt1ctr` | `c/s` | `D` |
| `czt1enth` | `keV` | `D` |
| `czt2ctr` | `c/s` | `D` |
| `czt2enth` | `None` | `D` |
| `cdte2ctr` | `c/s` | `D` |
| `czt1pktm` | `None` | `D` |
| `czt2pktm` | `None` | `D` |
| `fehkstat` | `None` | `K` |
| `czt1hotpix` | `None` | `K` |
| `czt1hotpixcnt` | `None` | `K` |
| `czt1hotpixlgcstat` | `None` | `K` |
| `czt1hotpixthr` | `None` | `K` |
| `czt2hotpix` | `None` | `K` |
| `czt2hotpixcnt` | `None` | `K` |
| `czt2hotpixlgcstat` | `None` | `K` |
| `czt2hotpixthr` | `None` | `K` |
| `cdte1enerthr` | `None` | `D` |
| `cdte2enerthr` | `None` | `D` |
| `czthvmon` | `V` | `D` |
| `cdtehvmon` | `V` | `D` |
| `cdte1temp` | `degC` | `D` |
| `cdte2temp` | `degC` | `D` |
| `cdte1pilectr` | `None` | `K` |
| `cdte2pilectr` | `None` | `K` |
| `czt1satctr1` | `None` | `K` |
| `czt2satctr1` | `None` | `K` |
| `czt1bunpxctr` | `None` | `K` |
| `czt2bunpxctr` | `None` | `K` |
| `sunradeg` | `None` | `D` |
| `sundecdeg` | `None` | `D` |
| `suninfov` | `None` | `B` |
| `sun2yawdeg` | `None` | `D` |
| `sun2rolldeg` | `None` | `D` |
| `sun2pitchdeg` | `None` | `D` |
| `yawradeg` | `None` | `D` |
| `yawdecdeg` | `None` | `D` |
| `lastevtmjd` | `None` | `D` |

### SoLEXUS (SoLEXS) Representative Files

Found 16 FITS files across extracted observations:

- **gti:** 8 files
- **lightcurve:** 4 files
- **spectrum:** 4 files

### SoLEXS gti (SDD1)
**File:** `D:/Data/_analysis_tmp\SoLEXUS\AL1_SLX_L1_20240201_v1.0\SDD1\AL1_SOLEXS_20240201_SDD1_L1.gti.gz`
**Size:** 957.0 B

**HDU Summary:**
```
Filename: D:/Data/_analysis_tmp\SoLEXUS\AL1_SLX_L1_20240201_v1.0\SDD1\AL1_SOLEXS_20240201_SDD1_L1.gti.gz
No.    Name      Ver    Type      Cards   Dimensions   Format
  0  PRIMARY       1 PrimaryHDU      17   ()      
  1  GTI           1 BinTableHDU     24   0R x 2C   [I, I]
```

**HDU 0: name=`PRIMARY`, type=`PrimaryHDU`**

| Key | Value |
|-----|-------|
| `TELESCOP` | `AL1` |
| `INSTRUME` | `SoLEXS` |
| `TSTART` | `` |
| `TSTOP` | `` |
| `CREATOR` | `solexs_pipeline-1.4` |
| `ORIGIN` | `SoLEXSPOC` |

**HDU 1: name=`GTI`, type=`BinTableHDU`**

| Key | Value |
|-----|-------|
| `TELESCOP` | `AL1` |
| `INSTRUME` | `SoLEXS` |
| `EXPOSURE` | `0.0` |
| `CREATOR` | `solexs_pipeline-1.4` |

**Columns:**

| Name | Unit | Format |
|------|------|--------|
| `START` | `None` | `I` |
| `STOP` | `None` | `I` |

### SoLEXS gti (SDD2)
**File:** `D:/Data/_analysis_tmp\SoLEXUS\AL1_SLX_L1_20240201_v1.0\SDD2\AL1_SOLEXS_20240201_SDD2_L1.gti.gz`
**Size:** 1.0 KB

**HDU Summary:**
```
Filename: D:/Data/_analysis_tmp\SoLEXUS\AL1_SLX_L1_20240201_v1.0\SDD2\AL1_SOLEXS_20240201_SDD2_L1.gti.gz
No.    Name      Ver    Type      Cards   Dimensions   Format
  0  PRIMARY       1 PrimaryHDU      17   ()      
  1  GTI           1 BinTableHDU     24   3R x 2C   [D, D]
```

**HDU 0: name=`PRIMARY`, type=`PrimaryHDU`**

| Key | Value |
|-----|-------|
| `TELESCOP` | `AL1` |
| `INSTRUME` | `SoLEXS` |
| `TSTART` | `2024-02-01T00:00:01+00:00` |
| `TSTOP` | `2024-02-01T23:59:59+00:00` |
| `CREATOR` | `solexs_pipeline-1.4` |
| `ORIGIN` | `SoLEXSPOC` |

**HDU 1: name=`GTI`, type=`BinTableHDU`**

| Key | Value |
|-----|-------|
| `TELESCOP` | `AL1` |
| `INSTRUME` | `SoLEXS` |
| `EXPOSURE` | `86394.0` |
| `CREATOR` | `solexs_pipeline-1.4` |

**Columns:**

| Name | Unit | Format |
|------|------|--------|
| `START` | `None` | `D` |
| `STOP` | `None` | `D` |

### SoLEXS lightcurve (SDD2)
**File:** `D:/Data/_analysis_tmp\SoLEXUS\AL1_SLX_L1_20240201_v1.0\SDD2\AL1_SOLEXS_20240201_SDD2_L1.lc.gz`
**Size:** 258.5 KB

**HDU Summary:**
```
Filename: D:/Data/_analysis_tmp\SoLEXUS\AL1_SLX_L1_20240201_v1.0\SDD2\AL1_SOLEXS_20240201_SDD2_L1.lc.gz
No.    Name      Ver    Type      Cards   Dimensions   Format
  0  PRIMARY       1 PrimaryHDU      15   ()      
  1  RATE          1 BinTableHDU     39   86400R x 2C   [D, D]
```

**HDU 0: name=`PRIMARY`, type=`PrimaryHDU`**

| Key | Value |
|-----|-------|
| `TELESCOP` | `AL1` |
| `INSTRUME` | `SoLEXS` |
| `CREATOR` | `solexs_pipeline-1.4` |
| `ORIGIN` | `SoLEXSPOC` |

**HDU 1: name=`RATE`, type=`BinTableHDU`**

| Key | Value |
|-----|-------|
| `TELESCOP` | `AL1` |
| `INSTRUME` | `SoLEXS` |
| `DATE-OBS` | `2024-02-01 00:00:00` |
| `DATE-END` | `2024-02-01 23:59:59` |
| `TSTART` | `1706745600.0` |
| `TSTOP` | `1706831999.0` |
| `TIMESYS` | `UTC` |
| `TIMEUNIT` | `s` |
| `MJDREFI` | `40587` |
| `MJDREFF` | `0` |
| `FILTER` | `SDD2` |
| `CREATOR` | `solexs_pipeline-1.4` |
| `HDUCLAS1` | `LIGHTCURVE` |
| `HDUCLAS2` | `TOTAL` |
| `HDUCLAS3` | `COUNTS` |

**Columns:**

| Name | Unit | Format |
|------|------|--------|
| `TIME` | `None` | `D` |
| `COUNTS` | `None` | `D` |

### SoLEXS spectrum (SDD2)
**File:** `D:/Data/_analysis_tmp\SoLEXUS\AL1_SLX_L1_20240201_v1.0\SDD2\AL1_SOLEXS_20240201_SDD2_L1.pi.gz`
**Size:** 8.1 MB

**HDU Summary:**
```
Filename: D:/Data/_analysis_tmp\SoLEXUS\AL1_SLX_L1_20240201_v1.0\SDD2\AL1_SOLEXS_20240201_SDD2_L1.pi.gz
No.    Name      Ver    Type      Cards   Dimensions   Format
  0  PRIMARY       1 PrimaryHDU      34   ()      
  1  SPECTRUM      1 BinTableHDU     44   86400R x 6C   [D, D, J, 340K, 340D, D]
```

**HDU 0: name=`PRIMARY`, type=`PrimaryHDU`**

| Key | Value |
|-----|-------|
| `TELESCOP` | `AL1` |
| `INSTRUME` | `SoLEXS` |
| `CREATOR` | `solexs_pipeline-1.4` |
| `ORIGIN` | `SoLEXSPOC` |

**HDU 1: name=`SPECTRUM`, type=`BinTableHDU`**

| Key | Value |
|-----|-------|
| `TELESCOP` | `AL1` |
| `INSTRUME` | `SoLEXS` |
| `CHANTYPE` | `PI` |
| `DETCHANS` | `340` |
| `FILTER` | `SDD2` |
| `CREATOR` | `solexs_pipeline-1.4` |
| `HDUCLAS1` | `SPECTRUM` |
| `HDUCLAS2` | `TOTAL` |
| `HDUCLAS3` | `COUNTS` |

**Columns:**

| Name | Unit | Format |
|------|------|--------|
| `TSTART` | `s` | `D` |
| `TELAPSE` | `s` | `D` |
| `SPEC_NUM` | `None` | `J` |
| `CHANNEL` | `None` | `340K` |
| `COUNTS` | `None` | `340D` |
| `EXPOSURE` | `s` | `D` |

### HEL1OS Calibration Files

### Calibration ARF: hel1os_czt_arf_v03.fits
**File:** `D:/Data/_analysis_tmp\HEL1OS_CAL\CZTResponseReader\hel1os_czt_arf_v03.fits`
**Size:** 14.1 KB

**HDU Summary:**
```
Filename: D:/Data/_analysis_tmp\HEL1OS_CAL\CZTResponseReader\hel1os_czt_arf_v03.fits
No.    Name      Ver    Type      Cards   Dimensions   Format
  0  PRIMARY       1 PrimaryHDU       4   ()      
  1  SPEC_RESP     1 BinTableHDU     27   520R x 3C   [1E, 1E, 1E]
```

**HDU 0: name=`PRIMARY`, type=`PrimaryHDU`**

**HDU 1: name=`SPEC_RESP`, type=`BinTableHDU`**

| Key | Value |
|-----|-------|
| `TELESCOP` | `ADITYA-L1` |
| `INSTRUME` | `HEL1OS` |
| `CHANTYPE` | `PHA` |
| `DETNAM` | `CZT` |
| `FILTER` | `NONE` |
| `HDUCLAS1` | `RESPONSE` |
| `HDUCLAS2` | `SPECRESP` |

**Columns:**

| Name | Unit | Format |
|------|------|--------|
| `ENERG_LO` | `keV` | `1E` |
| `ENERG_HI` | `keV` | `1E` |
| `SPECRESP` | `cm^2` | `1E` |

### Calibration SRF/RMF: hel1os_czt_srf_v03.fits
**File:** `D:/Data/_analysis_tmp\HEL1OS_CAL\CZTResponseReader\hel1os_czt_srf_v03.fits`
**Size:** 714.4 KB

**HDU Summary:**
```
Filename: D:/Data/_analysis_tmp\HEL1OS_CAL\CZTResponseReader\hel1os_czt_srf_v03.fits
No.    Name      Ver    Type      Cards   Dimensions   Format
  0  PRIMARY       1 PrimaryHDU       4   ()      
  1  MATRIX        1 BinTableHDU     35   520R x 6C   [1E, 1E, 1I, 1I, 1I, 341E]   
  2  EBOUNDS       1 BinTableHDU     26   341R x 3C   [1I, 1E, 1E]
```

**HDU 0: name=`PRIMARY`, type=`PrimaryHDU`**

**HDU 1: name=`MATRIX`, type=`BinTableHDU`**

| Key | Value |
|-----|-------|
| `TELESCOP` | `ADITYA-L1` |
| `INSTRUME` | `HEL1OS` |
| `CHANTYPE` | `PHA` |
| `DETCHANS` | `341` |
| `DETNAM` | `CZT` |
| `FILTER` | `NONE` |
| `HDUCLAS1` | `RESPONSE` |
| `HDUCLAS2` | `RSP_MATRIX` |
| `HDUCLAS3` | `REDIST` |

**Columns:**

| Name | Unit | Format |
|------|------|--------|
| `ENERG_LO` | `keV` | `1E` |
| `ENERG_HI` | `keV` | `1E` |
| `N_GRP` | `None` | `1I` |
| `F_CHAN` | `None` | `1I` |
| `N_CHAN` | `None` | `1I` |
| `MATRIX` | `None` | `341E` |

**HDU 2: name=`EBOUNDS`, type=`BinTableHDU`**

| Key | Value |
|-----|-------|
| `TELESCOP` | `ADITYA-L1` |
| `INSTRUME` | `HEL1OS` |
| `CHANTYPE` | `PHA` |
| `DETNAM` | `CZT` |
| `FILTER` | `NONE` |
| `HDUCLAS1` | `RESPONSE` |
| `HDUCLAS2` | `EBOUNDS` |

**Columns:**

| Name | Unit | Format |
|------|------|--------|
| `CHANNEL` | `None` | `1I` |
| `E_MIN` | `keV` | `1E` |
| `E_MAX` | `keV` | `1E` |

### Calibration ARF: hel1os_cdte_arf_v03.fits
**File:** `D:/Data/_analysis_tmp\HEL1OS_CAL\CdTeResponseReader\hel1os_cdte_arf_v03.fits`
**Size:** 14.1 KB

**HDU Summary:**
```
Filename: D:/Data/_analysis_tmp\HEL1OS_CAL\CdTeResponseReader\hel1os_cdte_arf_v03.fits
No.    Name      Ver    Type      Cards   Dimensions   Format
  0  PRIMARY       1 PrimaryHDU       4   ()      
  1  SPEC_RESP     1 BinTableHDU     27   550R x 3C   [1E, 1E, 1E]
```

**HDU 0: name=`PRIMARY`, type=`PrimaryHDU`**

**HDU 1: name=`SPEC_RESP`, type=`BinTableHDU`**

| Key | Value |
|-----|-------|
| `TELESCOP` | `ADITYA-L1` |
| `INSTRUME` | `HEL1OS` |
| `CHANTYPE` | `PHA` |
| `DETNAM` | `CDTE` |
| `FILTER` | `NONE` |
| `HDUCLAS1` | `RESPONSE` |
| `HDUCLAS2` | `SPECRESP` |

**Columns:**

| Name | Unit | Format |
|------|------|--------|
| `ENERG_LO` | `keV` | `1E` |
| `ENERG_HI` | `keV` | `1E` |
| `SPECRESP` | `cm^2` | `1E` |

### Calibration SRF/RMF: hel1os_cdte_srf_v03.fits
**File:** `D:/Data/_analysis_tmp\HEL1OS_CAL\CdTeResponseReader\hel1os_cdte_srf_v03.fits`
**Size:** 1.1 MB

**HDU Summary:**
```
Filename: D:/Data/_analysis_tmp\HEL1OS_CAL\CdTeResponseReader\hel1os_cdte_srf_v03.fits
No.    Name      Ver    Type      Cards   Dimensions   Format
  0  PRIMARY       1 PrimaryHDU       4   ()      
  1  MATRIX        1 BinTableHDU     35   550R x 6C   [1E, 1E, 1I, 1I, 1I, 511E]   
  2  EBOUNDS       1 BinTableHDU     26   511R x 3C   [1I, 1E, 1E]
```

**HDU 0: name=`PRIMARY`, type=`PrimaryHDU`**

**HDU 1: name=`MATRIX`, type=`BinTableHDU`**

| Key | Value |
|-----|-------|
| `TELESCOP` | `ADITYA-L1` |
| `INSTRUME` | `HEL1OS` |
| `CHANTYPE` | `PHA` |
| `DETCHANS` | `511` |
| `DETNAM` | `CDTE` |
| `FILTER` | `NONE` |
| `HDUCLAS1` | `RESPONSE` |
| `HDUCLAS2` | `RSP_MATRIX` |
| `HDUCLAS3` | `REDIST` |

**Columns:**

| Name | Unit | Format |
|------|------|--------|
| `ENERG_LO` | `keV` | `1E` |
| `ENERG_HI` | `keV` | `1E` |
| `N_GRP` | `None` | `1I` |
| `F_CHAN` | `None` | `1I` |
| `N_CHAN` | `None` | `1I` |
| `MATRIX` | `None` | `511E` |

**HDU 2: name=`EBOUNDS`, type=`BinTableHDU`**

| Key | Value |
|-----|-------|
| `TELESCOP` | `ADITYA-L1` |
| `INSTRUME` | `HEL1OS` |
| `CHANTYPE` | `PHA` |
| `DETNAM` | `CDTE` |
| `FILTER` | `NONE` |
| `HDUCLAS1` | `RESPONSE` |
| `HDUCLAS2` | `EBOUNDS` |

**Columns:**

| Name | Unit | Format |
|------|------|--------|
| `CHANNEL` | `None` | `1I` |
| `E_MIN` | `keV` | `1E` |
| `E_MAX` | `keV` | `1E` |

## Step 3 — Time Coverage and GTI Inspection

### HEL1OS Time Coverage

Scanning all zip files for time range (from filenames)...

- **Date range from filenames:** 20240701 to 20260615
- **Total observations:** 1284

**Precise time range from extracted sample FITS headers:**

- **TSTART min:** 60492.00151898259
- **TSTOP max:** 61206.99988825876

**Separate GTI files in HEL1OS observations:**

- `gticdte1.fits`
- `gticdte2.fits`
- `gticzt1.fits`
- `gticzt2.fits`

#### GTI Analysis: gticdte1.fits
**File:** `gticdte1.fits`

> **Note:** HEL1OS GTI values are in MJD (days), not seconds. Converting:

- **Number of GTI intervals:** 1
- **TSTART (MJD):** 60492.00151898
- **TSTOP (MJD):** 60492.49987251
- **Total good time:** 43,058 s (11.96 hr)
- **Total elapsed time:** 43,058 s (11.96 hr)
- **Duty cycle:** 100.0%
- **Single continuous GTI** (matches `43057sec` in filename)

#### GTI Analysis: gticzt1.fits
**File:** `gticzt1.fits`

- **Number of GTI intervals:** 1
- **TSTART (MJD):** 60492.00151898
- **TSTOP (MJD):** 60492.49987251
- **Total good time:** 43,058 s (11.96 hr)
- **Total elapsed time:** 43,058 s (11.96 hr)
- **Duty cycle:** 100.0%
- **Single continuous GTI** (same interval as CdTe — simultaneous observation)

### SoLEXUS (SoLEXS) Time Coverage

- **Date range from filenames:** 20240201 to 20260613
- **Total observations:** 841

**Precise time range from extracted sample FITS headers:**

- **TSTART min:** 1706745600.0
- **TSTOP max:** 1781395199.0

**Separate GTI files in SoLEXS observations:**

- `AL1_SOLEXS_20240201_SDD1_L1.gti.gz`
- `AL1_SOLEXS_20240201_SDD2_L1.gti.gz`
- `AL1_SOLEXS_20250318_SDD1_L1.gti.gz`
- `AL1_SOLEXS_20250318_SDD2_L1.gti.gz`
- `AL1_SOLEXS_20260613_SDD1_L1.gti.gz`
- `AL1_SOLEXS_20260613_SDD2_L1.gti.gz`

#### GTI Analysis: AL1_SOLEXS_20240201_SDD1_L1.gti.gz
**File:** `AL1_SOLEXS_20240201_SDD1_L1.gti.gz`

> **IMPORTANT:** SDD1 GTI has 0 rows, EXPOSURE=0, and TSTART/TSTOP are empty strings.
> SDD1 appears to consistently have no science data — only an empty GTI file.

- **Number of GTI intervals:** 0 (empty table)
- **TSTART/TSTOP in header:** empty strings (no data)
- **EXPOSURE:** 0.0

#### GTI Analysis: AL1_SOLEXS_20240201_SDD2_L1.gti.gz
**File:** `AL1_SOLEXS_20240201_SDD2_L1.gti.gz`

> SoLEXS GTI values are in Unix epoch seconds (MJDREFI=40587, MJDREFF=0).

- **Number of GTI intervals:** 3
- **Total good time:** 86,391 s (24.00 hr)
- **Total elapsed time:** 86,398 s (24.00 hr)
- **Duty cycle:** ~100.0%
- **Longest GTI:** 41,892 s (11.6 hr)
- **Shortest GTI:** 6,990 s (1.9 hr)

#### Time System Differences

| Property | HEL1OS | SoLEXS |
|----------|--------|--------|
| **Time column** | `mjd` (MJD days) | `TIME` (Unix epoch seconds) |
| **TSTART/TSTOP units** | MJD days | Unix epoch seconds |
| **TIMESYS** | not set | `UTC` |
| **MJDREFI** | not set | `40587` |
| **TIMEUNIT** | not set | `s` |
| **UTC reference** | `utc-isot` column | computed from MJDREF |

## Step 4 — Sample Event Data

### HEL1OS Event List
**File:** `evt.fits` (149.3 MB)

The event file contains **4 HDUs** — one per detector unit:

| HDU | Name | Events | Energy Range | Median |
|-----|------|--------|-------------|--------|
| 1 | `CDTE1-EVENTS` | 64,027 | 1.2 – 89.3 keV | 9.5 keV |
| 2 | `CDTE2-EVENTS` | 46,808 | 2.5 – 91.0 keV | 10.8 keV |
| 3 | `CZT1-EVENTS` | 1,208,561 | 12.8 – 236.6 keV | 26.7 keV |
| 4 | `CZT2-EVENTS` | 1,130,770 | 11.6 – 238.4 keV | 37.2 keV |

**Total events in this file: 2,450,166**
**Time span:** 0.498 days (11.96 hours)

**Columns (CdTe):** `mjd`, `hlsobt`, `currtemp`, `chn`, `ener`, `recnum`, `utc-isot`
**Columns (CZT, additional):** `pix`, `offsetchn` (pixel ID and offset channel)

**First 5 rows (CDTE1-EVENTS):**

| mjd | hlsobt | currtemp | chn | ener | recnum | utc-isot |
| --- | --- | --- | --- | --- | --- | --- |
| 60492.001518982586 | 157217.21 | -40.202 | 38 | 7.9067386558516795 | 1 | 2024-07-01T00:02:11.240 |
| 60492.001615697256 | 157232.03 | -40.202 | 341 | 60.022738655851676 | 3 | 2024-07-01T00:02:19.596 |
| 60492.001712842095 | 157239.76 | -40.202 | 40 | 8.250738655851679 | 4 | 2024-07-01T00:02:27.990 |
| 60492.00171284195 | 157239.69 | -40.202 | 41 | 8.42273865585168 | 4 | 2024-07-01T00:02:27.990 |
| 60492.001712842095 | 157239.89 | -40.202 | 54 | 10.658738655851678 | 4 | 2024-07-01T00:02:27.990 |

**CdTe1 Energy Histogram:**

| Bin (keV) | Count |
|-----------|-------|
| 1.2 – 10.0 | 38,359 |
| 10.0 – 18.8 | 20,163 |
| 18.8 – 27.6 | 665 |
| 27.6 – 36.4 | 425 |
| 36.4 – 45.2 | 422 |
| 45.2 – 54.0 | 497 |
| 54.0 – 62.9 | 1,807 |
| 62.9 – 71.7 | 459 |
| 71.7 – 80.5 | 492 |
| 80.5 – 89.3 | 738 |

**CZT1 Energy Histogram:**

| Bin (keV) | Count |
|-----------|-------|
| 12.8 – 35.2 | 745,785 |
| 35.2 – 57.6 | 89,463 |
| 57.6 – 80.0 | 81,320 |
| 80.0 – 102.3 | 74,086 |
| 102.3 – 124.7 | 66,481 |
| 124.7 – 147.1 | 54,089 |
| 147.1 – 169.5 | 40,997 |
| 169.5 – 191.9 | 30,154 |
| 191.9 – 214.2 | 21,271 |
| 214.2 – 236.6 | 4,915 |

### SoLEXS Spectrum (PI file)
**File:** `AL1_SOLEXS_20240201_SDD2_L1.pi.gz` (8.1 MB)

- **HDU name:** `SPECTRUM`
- **Total rows:** 86,400
- **Columns:** TSTART, TELAPSE, SPEC_NUM, CHANNEL, COUNTS, EXPOSURE

**First 5 rows:**

| TSTART | TELAPSE | SPEC_NUM | CHANNEL | COUNTS | EXPOSURE |
| --- | --- | --- | --- | --- | --- |
| 1706745600.0 | 1.0 | 1 | [array len=340] | [array len=340] | 1.0 |
| 1706745601.0 | 1.0 | 2 | [array len=340] | [array len=340] | 1.0 |
| 1706745602.0 | 1.0 | 3 | [array len=340] | [array len=340] | 1.0 |
| 1706745603.0 | 1.0 | 4 | [array len=340] | [array len=340] | 1.0 |
| 1706745604.0 | 1.0 | 5 | [array len=340] | [array len=340] | 1.0 |

- **`CHANNEL` column is array-valued** (not scalar per event)

### SoLEXS Light Curve
**File:** `AL1_SOLEXS_20240201_SDD2_L1.lc.gz` (258.5 KB)

- **HDU name:** `RATE`
- **Total rows:** 86,400
- **Columns:** TIME, COUNTS

**First 5 rows:**

| TIME | COUNTS |
| --- | --- |
| 1706745600.0 | nan |
| 1706745601.0 | 6.0 |
| 1706745602.0 | 15.0 |
| 1706745603.0 | 8.0 |
| 1706745604.0 | 8.0 |

- **Time range:** 1706745600.0 to 1706831999.0
- **Time delta (first to last):** 86399.0 s (24.00 hr)

### HEL1OS Light Curve (CdTe)
**File:** `lightcurve_cdte1.fits` (11.1 MB)

- **HDU name:** `CDTE1_LC_BAND_5.00KEV_TO_20.00KEV`
- **Total rows:** 43,003
- **Columns:** MJD, ISOT, CTR, STAT_ERR

**First 5 rows:**

| MJD | ISOT | CTR | STAT_ERR |
| --- | --- | --- | --- |
| 60492.00152476963 | 2024-07-01T00:02:11.740 | 1.0 | 1.0 |
| 60492.0015363437 | 2024-07-01T00:02:12.740 | 0.0 | 0.0 |
| 60492.00154791777 | 2024-07-01T00:02:13.740 | 0.0 | 0.0 |
| 60492.00155949185 | 2024-07-01T00:02:14.740 | 0.0 | 0.0 |
| 60492.00157106592 | 2024-07-01T00:02:15.740 | 0.0 | 0.0 |

### HEL1OS Spectra (CdTe)
**File:** `hel1os_cdte_spectra_cdte1.fits` (21.1 MB)

- **HDU name:** `SPECTRUM`
- **Total rows:** 2,151
- **Columns:** SPEC_NUM, CHANNEL, COUNTS, STAT_ERR, ROWID, TSTART, TSTOP, EXPOSURE

**First 5 rows:**

| SPEC_NUM | CHANNEL | COUNTS | STAT_ERR | ROWID | TSTART | TSTOP | EXPOSURE |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | [array len=511] | [array len=511] | [array len=511] | Spectrum0 | 0.0 | 20.0 | 20.0 |
| 1 | [array len=511] | [array len=511] | [array len=511] | Spectrum1 | 20.0 | 40.0 | 20.0 |
| 2 | [array len=511] | [array len=511] | [array len=511] | Spectrum2 | 40.0 | 60.0 | 20.0 |
| 3 | [array len=511] | [array len=511] | [array len=511] | Spectrum3 | 60.0 | 80.0 | 20.0 |
| 4 | [array len=511] | [array len=511] | [array len=511] | Spectrum4 | 80.0 | 100.0 | 20.0 |

- **`CHANNEL` column is array-valued** (not scalar per event)

## Step 5 — Detector-Specific Checks

### HEL1OS Detector Distinction

**Directory-level separation:**

- HEL1OS organizes data into separate subdirectories per detector type:
  - `cdte/` — CdTe detector files (lightcurves + spectra)
  - `czt/` — CZT detector files (lightcurves + spectra)
  - `events/` — Combined event list (`evt.fits`)
  - `aux/` — GTI files per detector (`gticdte1.fits`, `gticdte2.fits`, `gticzt1.fits`, `gticzt2.fits`) + housekeeping

**Checking event file for detector/quadrant columns:**

- HDU `CDTE1-EVENTS`: all columns = ['mjd', 'hlsobt', 'currtemp', 'chn', 'ener', 'recnum', 'utc-isot']

- HDU `CDTE2-EVENTS`: all columns = ['mjd', 'hlsobt', 'currtemp', 'chn', 'ener', 'recnum', 'utc-isot']

- HDU `CZT1-EVENTS`: all columns = ['mjd', 'hlsobt', 'currtemp', 'pix', 'chn', 'offsetchn', 'ener', 'recnum', 'utc-isot']

- HDU `CZT2-EVENTS`: all columns = ['mjd', 'hlsobt', 'currtemp', 'pix', 'chn', 'offsetchn', 'ener', 'recnum', 'utc-isot']

**Filename patterns in HEL1OS zips:**

- No QUAD/Q0-Q3 patterns found in filenames

**Unique file basenames across observations:**

- `czt1dispix.txt`
- `czt2dispix.txt`
- `evt.fits`
- `gticdte1.fits`
- `gticdte2.fits`
- `gticzt1.fits`
- `gticzt2.fits`
- `hel1os_cdte_spectra_cdte1.fits`
- `hel1os_cdte_spectra_cdte2.fits`
- `hel1os_czt_spectra_czt1.fits`
- `hel1os_czt_spectra_czt2.fits`
- `hk.fits`
- `lightcurve_cdte1.fits`
- `lightcurve_cdte2.fits`
- `lightcurve_czt1.fits`
- `lightcurve_czt2.fits`

**Checking spectra headers for detector identification:**

- CdTe spectra — `INSTRUME` = `HEL1OS`
- CdTe spectra — `CREATOR` = `HEL1OS-L1-PIPELINE`
- CdTe spectra — `TELESCOP` = `Aditya-L1`
- CdTe spectra ext1 — `DETNAM` = `CdTe1`
- CdTe spectra ext1 — `INSTRUME` = `HEL1OS`
- CdTe spectra ext1 — `CHANTYPE` = `PHA`
- CdTe spectra ext1 — `DETCHANS` = `511`
- CZT spectra — `INSTRUME` = `HEL1OS`
- CZT spectra — `CREATOR` = `HEL1OS-L1-PIPELINE`
- CZT spectra — `TELESCOP` = `Aditya-L1`
- CZT spectra ext1 — `DETNAM` = `CZT1`
- CZT spectra ext1 — `INSTRUME` = `HEL1OS`
- CZT spectra ext1 — `CHANTYPE` = `PHA`
- CZT spectra ext1 — `DETCHANS` = `341`

### SoLEXS Detector Distinction

**Directory-level separation:**

- SoLEXS organizes data into separate subdirectories per detector:
  - `SDD1/` — Silicon Drift Detector 1
  - `SDD2/` — Silicon Drift Detector 2

**Checking SoLEXS file headers for detector identification:**

- `AL1_SOLEXS_20240201_SDD1_L1.gti.gz` HDU0 — `INSTRUME` = `SoLEXS`
- `AL1_SOLEXS_20240201_SDD1_L1.gti.gz` HDU0 — `TELESCOP` = `AL1`
- `AL1_SOLEXS_20240201_SDD1_L1.gti.gz` HDU0 — `CREATOR` = `solexs_pipeline-1.4`
- `AL1_SOLEXS_20240201_SDD1_L1.gti.gz` HDU0 — `ORIGIN` = `SoLEXSPOC`
- `AL1_SOLEXS_20240201_SDD1_L1.gti.gz` HDU1 — `INSTRUME` = `SoLEXS`
- `AL1_SOLEXS_20240201_SDD1_L1.gti.gz` HDU1 — `TELESCOP` = `AL1`
- `AL1_SOLEXS_20240201_SDD1_L1.gti.gz` HDU1 — `CREATOR` = `solexs_pipeline-1.4`
- `AL1_SOLEXS_20240201_SDD2_L1.gti.gz` HDU0 — `INSTRUME` = `SoLEXS`
- `AL1_SOLEXS_20240201_SDD2_L1.gti.gz` HDU0 — `TELESCOP` = `AL1`
- `AL1_SOLEXS_20240201_SDD2_L1.gti.gz` HDU0 — `CREATOR` = `solexs_pipeline-1.4`
- `AL1_SOLEXS_20240201_SDD2_L1.gti.gz` HDU0 — `ORIGIN` = `SoLEXSPOC`
- `AL1_SOLEXS_20240201_SDD2_L1.gti.gz` HDU1 — `INSTRUME` = `SoLEXS`
- `AL1_SOLEXS_20240201_SDD2_L1.gti.gz` HDU1 — `TELESCOP` = `AL1`
- `AL1_SOLEXS_20240201_SDD2_L1.gti.gz` HDU1 — `CREATOR` = `solexs_pipeline-1.4`
- `AL1_SOLEXS_20240201_SDD2_L1.lc.gz` HDU0 — `INSTRUME` = `SoLEXS`
- `AL1_SOLEXS_20240201_SDD2_L1.lc.gz` HDU0 — `TELESCOP` = `AL1`
- `AL1_SOLEXS_20240201_SDD2_L1.lc.gz` HDU0 — `CREATOR` = `solexs_pipeline-1.4`
- `AL1_SOLEXS_20240201_SDD2_L1.lc.gz` HDU0 — `ORIGIN` = `SoLEXSPOC`
- `AL1_SOLEXS_20240201_SDD2_L1.lc.gz` HDU1 — `INSTRUME` = `SoLEXS`
- `AL1_SOLEXS_20240201_SDD2_L1.lc.gz` HDU1 — `FILTER` = `SDD2`
- `AL1_SOLEXS_20240201_SDD2_L1.lc.gz` HDU1 — `TELESCOP` = `AL1`
- `AL1_SOLEXS_20240201_SDD2_L1.lc.gz` HDU1 — `CREATOR` = `solexs_pipeline-1.4`
- `AL1_SOLEXS_20250318_SDD2_L1.lc.gz` HDU0 — `INSTRUME` = `SoLEXS`
- `AL1_SOLEXS_20250318_SDD2_L1.lc.gz` HDU0 — `TELESCOP` = `AL1`
- `AL1_SOLEXS_20250318_SDD2_L1.lc.gz` HDU0 — `CREATOR` = `solexs_pipeline-1.2`
- `AL1_SOLEXS_20250318_SDD2_L1.lc.gz` HDU0 — `ORIGIN` = `SoLEXSPOC`
- `AL1_SOLEXS_20250318_SDD2_L1.lc.gz` HDU1 — `INSTRUME` = `SoLEXS`
- `AL1_SOLEXS_20250318_SDD2_L1.lc.gz` HDU1 — `FILTER` = `SDD2`
- `AL1_SOLEXS_20250318_SDD2_L1.lc.gz` HDU1 — `TELESCOP` = `AL1`
- `AL1_SOLEXS_20250318_SDD2_L1.lc.gz` HDU1 — `CREATOR` = `solexs_pipeline-1.2`
- `AL1_SOLEXS_20240201_SDD2_L1.pi.gz` HDU0 — `INSTRUME` = `SoLEXS`
- `AL1_SOLEXS_20240201_SDD2_L1.pi.gz` HDU0 — `TELESCOP` = `AL1`
- `AL1_SOLEXS_20240201_SDD2_L1.pi.gz` HDU0 — `CREATOR` = `solexs_pipeline-1.4`
- `AL1_SOLEXS_20240201_SDD2_L1.pi.gz` HDU0 — `ORIGIN` = `SoLEXSPOC`
- `AL1_SOLEXS_20240201_SDD2_L1.pi.gz` HDU1 — `INSTRUME` = `SoLEXS`
- `AL1_SOLEXS_20240201_SDD2_L1.pi.gz` HDU1 — `FILTER` = `SDD2`
- `AL1_SOLEXS_20240201_SDD2_L1.pi.gz` HDU1 — `TELESCOP` = `AL1`
- `AL1_SOLEXS_20240201_SDD2_L1.pi.gz` HDU1 — `CREATOR` = `solexs_pipeline-1.4`
- `AL1_SOLEXS_20240201_SDD2_L1.pi.gz` HDU1 — `CHANTYPE` = `PI`
- `AL1_SOLEXS_20240201_SDD2_L1.pi.gz` HDU1 — `DETCHANS` = `340`
- `AL1_SOLEXS_20250318_SDD2_L1.pi.gz` HDU0 — `INSTRUME` = `SoLEXS`
- `AL1_SOLEXS_20250318_SDD2_L1.pi.gz` HDU0 — `TELESCOP` = `AL1`
- `AL1_SOLEXS_20250318_SDD2_L1.pi.gz` HDU0 — `CREATOR` = `solexs_pipeline-1.2`
- `AL1_SOLEXS_20250318_SDD2_L1.pi.gz` HDU0 — `ORIGIN` = `SoLEXSPOC`
- `AL1_SOLEXS_20250318_SDD2_L1.pi.gz` HDU1 — `INSTRUME` = `SoLEXS`
- `AL1_SOLEXS_20250318_SDD2_L1.pi.gz` HDU1 — `FILTER` = `SDD2`
- `AL1_SOLEXS_20250318_SDD2_L1.pi.gz` HDU1 — `TELESCOP` = `AL1`
- `AL1_SOLEXS_20250318_SDD2_L1.pi.gz` HDU1 — `CREATOR` = `solexs_pipeline-1.2`
- `AL1_SOLEXS_20250318_SDD2_L1.pi.gz` HDU1 — `CHANTYPE` = `PI`
- `AL1_SOLEXS_20250318_SDD2_L1.pi.gz` HDU1 — `DETCHANS` = `340`

**File presence per SDD subdirectory (across all extracted samples):**

- **SDD1 file types:** ['.gti.gz']
- **SDD1 file count:** 3
- **SDD2 file types:** ['.gti.gz', '.lc.gz', '.pi.gz']
- **SDD2 file count:** 9

- **SDD1 sample filenames:** ['AL1_SOLEXS_20240201_SDD1_L1.gti.gz', 'AL1_SOLEXS_20250318_SDD1_L1.gti.gz', 'AL1_SOLEXS_20260613_SDD1_L1.gti.gz']
- **SDD2 sample filenames:** ['AL1_SOLEXS_20240201_SDD2_L1.gti.gz', 'AL1_SOLEXS_20240201_SDD2_L1.lc.gz', 'AL1_SOLEXS_20240201_SDD2_L1.pi.gz', 'AL1_SOLEXS_20250318_SDD2_L1.gti.gz', 'AL1_SOLEXS_20250318_SDD2_L1.lc.gz']

## Step 6 — Anomaly Check

### Zero-size files

Found 3 zero-size files:
- `D:/Data/_analysis_tmp\HEL1OS\2024\07\01\HLS_20240701_000211_43057sec_lev1_V111\aux\cztdis\czt2dispix.txt`
- `D:/Data/_analysis_tmp\HEL1OS\2025\08\09\HLS_20250809_121027_42569sec_lev1_V111\aux\cztdis\czt2dispix.txt`
- `D:/Data/_analysis_tmp\HEL1OS\2026\06\15\HLS_20260615_120000_43190sec_lev1_V111\aux\cztdis\czt2dispix.txt`

### Files that fail to open with astropy

All extracted FITS files opened successfully.

### Missing or zero EXPOSURE

No files with zero or missing EXPOSURE found.

### TSTART > TSTOP

No files with TSTART > TSTOP.

### Duplicate zip files

- **HEL1OS duplicate zips:** 417
- **SoLEXUS duplicate zips:** 199
  - Sample: ['HLS_20240701_000211_43057sec_lev1_V111 (1).zip', 'HLS_20240730_235951_43195sec_lev1_V111 (1).zip', 'HLS_20240731_120004_43190sec_lev1_V111 (1).zip']
  - Sample: ['AL1_SLX_L1_20240201_v1.0 (1).zip', 'AL1_SLX_L1_20240202_v1.0 (1).zip', 'AL1_SLX_L1_20240203_v1.0 (1).zip']

### Anomaly Summary

**3 anomalies found:**
- Zero-size: D:/Data/_analysis_tmp\HEL1OS\2024\07\01\HLS_20240701_000211_43057sec_lev1_V111\aux\cztdis\czt2dispix.txt
- Zero-size: D:/Data/_analysis_tmp\HEL1OS\2025\08\09\HLS_20250809_121027_42569sec_lev1_V111\aux\cztdis\czt2dispix.txt
- Zero-size: D:/Data/_analysis_tmp\HEL1OS\2026\06\15\HLS_20260615_120000_43190sec_lev1_V111\aux\cztdis\czt2dispix.txt

## Suggested Loader Strategy

### What constitutes one observation?

#### HEL1OS

One HEL1OS observation = one zip file with naming pattern:
```
HLS_YYYYMMDD_HHMMSS_DDDDDsec_lev1_VXYZ.zip
```
where `YYYYMMDD_HHMMSS` is the start time, `DDDDDsec` is the duration, and `VXYZ` is the version.

Each observation zip extracts to a directory tree:
```
YYYY/MM/DD/HLS_.../
  ├── events/evt.fits           # Combined event list (all detectors)
  ├── cdte/                     # CdTe detector (low energy, ~1-30 keV)
  │   ├── lightcurve_cdte1.fits
  │   ├── lightcurve_cdte2.fits
  │   ├── hel1os_cdte_spectra_cdte1.fits
  │   └── hel1os_cdte_spectra_cdte2.fits
  ├── czt/                      # CZT detector (high energy, ~20-200 keV)
  │   ├── lightcurve_czt1.fits
  │   ├── lightcurve_czt2.fits
  │   ├── hel1os_czt_spectra_czt1.fits
  │   └── hel1os_czt_spectra_czt2.fits
  └── aux/
      ├── hk.fits               # Housekeeping
      ├── gticdte1.fits          # GTI for CdTe detector 1
      ├── gticdte2.fits
      ├── gticzt1.fits           # GTI for CZT detector 1
      ├── gticzt2.fits
      └── cztdis/               # CZT disabled pixel lists
```

**Version handling:**

HEL1OS filenames contain a version code `VXYZ`:

| Version | Count | Notes |
|---------|-------|-------|
| V111 | 1,044 | Most common |
| V112 | 108 | |
| V113 | 5 | |
| V211 | 83 | |
| V212 | 4 | |
| V311 | 16 | |
| V312+ | 8 | Rare higher versions |

**134 observations have multiple versions** (e.g., `20240701_000211` exists as V111, V211, and V311). The loader should group by datetime and select the highest version, or let the user choose.

**Loader approach:**
1. Enumerate zip files, parse `YYYYMMDD_HHMMSS` + version from filename
2. Deduplicate: group by `YYYYMMDD_HHMMSS`, pick latest version (or all)
3. Extract to temp directory (or read directly from zip using `astropy.io.fits` + `io.BytesIO`)
4. For each observation, load: event list + per-detector lightcurves + spectra + GTIs
5. Detectors are distinguished by **subdirectory** (`cdte/` vs `czt/`) and **filename suffix** (`_cdte1`, `_cdte2`, `_czt1`, `_czt2`)
6. Each detector type has two units (1, 2) with independent files and GTIs

#### SoLEXS

One SoLEXS observation = one zip file with naming pattern:
```
AL1_SLX_L1_YYYYMMDD_v1.0.zip
```

Each observation zip extracts to:
```
AL1_SLX_L1_YYYYMMDD_v1.0/
  ├── SDD1/                          # Silicon Drift Detector 1
  │   └── AL1_SOLEXS_YYYYMMDD_SDD1_L1.gti.gz
  └── SDD2/                          # Silicon Drift Detector 2
      ├── AL1_SOLEXS_YYYYMMDD_SDD2_L1.gti.gz
      ├── AL1_SOLEXS_YYYYMMDD_SDD2_L1.lc.gz
      └── AL1_SOLEXS_YYYYMMDD_SDD2_L1.pi.gz
```

**Key observations:**
- SDD1 typically only has a GTI file (no lightcurve or spectrum) — **and the GTI is consistently empty (0 rows)**
- SDD2 has GTI + lightcurve + spectrum (PI) files — this is where all the science data lives
- All files are gzip-compressed FITS (`.gz`) — `astropy.io.fits.open()` handles `.gz` transparently
- A small subset (5 observations, v1.1) also include `.hk.gz` (housekeeping) and `.png` (lightcurve plot)
- SoLEXS spectra are time-resolved: 86,400 rows × 340 channels = one 1-second spectrum per row per day
- SoLEXS light curves: 86,400 rows = 1-second cadence over 24 hours

**Loader approach:**
1. Enumerate zip files, parse `YYYYMMDD` and version from filename
2. Extract to temp directory
3. For each observation, load SDD2 data (SDD1 can be ignored — it only has empty GTIs)
4. Detectors are distinguished by **subdirectory** (`SDD1/` vs `SDD2/`) and **filename** (`_SDD1_` vs `_SDD2_`)
5. For the PI file, each row is one 1-second spectrum with 340 channels — load as a time-resolved spectral cube

### Calibration Files

HEL1OS calibration responses are in separate zip archives:
- `CAL_epoch20231001_CdTeResponseReader.zip` → ARF + SRF (RMF) for CdTe
- `CAL_epoch20231001_CZTResponseReader.zip` → ARF + SRF (RMF) for CZT
- Each also includes an IDL `.pro` script for reference

### Deduplication Note

Both data sets contain duplicate zip files with `(1)` suffix (browser re-downloads).
The loader should filter these out by default.
