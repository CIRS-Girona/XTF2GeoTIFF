import os, subprocess

from src.utils import get_bounds


def run_mbsystem_processing(xtf_pings, xtf_path, output_dir, resolution, clip=10, epsg_code=25831, colormap='gray'):
    """
    Run MBSystem commands to generate .tif from XTF file

    Args:
        xtf_pings: XTF ping data for bounds calculation (required if bounds=None)
        xtf_path: Path to the XTF file
        output_dir: Directory to save outputs
        resolution: Grid resolution in meters
        clip: Clipping value for spline interpolation (default: 10)
        epsg_code: EPSG code for coordinate system (default: 25831)
        colormap: Color map to use for the output .tif (options: https://docs.generic-mapping-tools.org/6.2/cookbook/cpts.html)

    Returns:
        Path to generated .tif file or None if failed
    """
    label = '.'.join(xtf_path.split("/")[-1].split(".")[:-1])

    bounds = get_bounds(xtf_pings, epsg_code=epsg_code)

    # Create datalist file
    datalist_path = os.path.join(output_dir, f"{label}_datalist.txt")
    with open(datalist_path, 'w') as f:
        f.write(f"{label}.xtf 211\n")

    # Prepare bounds string
    lon_min, lon_max, lat_min, lat_max = bounds
    bounds_str = f"-R{lon_min}/{lon_max}/{lat_min}/{lat_max}"

    # Output grid name
    grid_name = os.path.join(output_dir, f"{label}")
    try:
        # Run mbmosaic
        subprocess.run([
            "./mbs.sh",
            "mbmosaic",
            "-A4",                              # Algorithm 4
            f"-I{datalist_path}",               # Input datalist
            bounds_str,                          # Bounds (if specified)
            f"-C{clip}",                              # No clip
            "-N",                               # Use SRTM30 topography
            f"-E{resolution}/{resolution}/meters",  # Resolution
            f"-O{grid_name}"                    # Output prefix
        ], capture_output=True, text=True, check=True)

        grd_file = f"{grid_name}.grd"
        if not os.path.exists(grd_file):
            raise FileNotFoundError(f"Grid file not found: {grd_file}")

        cpt_file = f"{grid_name}.cpt"
        with open(cpt_file, 'w') as f:
            subprocess.run([
                "./mbs.sh",
                "gmt",
                "grd2cpt",
                grd_file,
                f"-C{colormap}"
            ], stdout=f, check=True)

        if not os.path.exists(cpt_file):
            raise FileNotFoundError(f"CPT file not found: {cpt_file}")

        tif_file = f"{grd_file}.tif"

        setlib_cmd = "gmt gmtset GMT_CUSTOM_LIBS /usr/local/lib/mbsystem.so"
        mbgrdtiff_cmd = f"gmt mbgrdtiff -I{grd_file} -O{tif_file} -C{cpt_file}"
        subprocess.run([
            "./mbs.sh",
            "bash",
            "-c",
            f"{setlib_cmd} && {mbgrdtiff_cmd}"
        ], capture_output=True, text=True, check=True)

        if not os.path.exists(tif_file):
            raise FileNotFoundError(f"TIF file not found: {tif_file}")

        # subprocess.run([
        #     "./mbs.sh",
        #     "mbm_grdtiff",
        #     f"-I{grd_file}",
        #     "-G1",                              # GeoTIFF format
        #     "-W1/4"                             # Color map 1, intensity 4
        # ], capture_output=True, text=True, check=True)

        # Run the generated command script
        # cmd_script = f"{grd_file}_tiff.cmd"
        # if os.path.exists(cmd_script):
        #     os.chmod(cmd_script, 0o755)  # Make script executable

        #     subprocess.run([
        #         cmd_script, "-N"
        #     ], capture_output=True, text=True, check=True)

        #     # Find the generated .tif file
        #     tif_file = f"{grd_file}.tif"
        #     if os.path.exists(tif_file):
        #         return tif_file
        #     else:
        #         raise FileNotFoundError(f"TIF file not found: {tif_file}")
        # else:
        #     raise FileNotFoundError(f"Command script not found: {cmd_script}")

    except subprocess.CalledProcessError as e:
        print(f"MBSystem command failed: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")

    except Exception as e:
        print(f"Error running MBSystem: {e}")
        return None