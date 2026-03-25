import os
from tqdm import tqdm

from src.utils import load_xtf, inspect_xtf
from src.modify_pings import modify_pings_with_correction
from src.mb_system import run_mbsystem_processing


# Example usage
if __name__ == "__main__":
    # Base directories
    input_path = "data/"
    output_path = "output/"

    inspect_xtfs = True
    run_mbsystem = True  # Set to True to run MBSystem processing
    auto_calculate_bounds = True  # Set to True to auto-calculate bounds from XTF data
    grid_resolution = 0.45  # meters
    epsg_code = 25831  # Coordinate system EPSG code

    # Create output directory
    os.makedirs(output_path, exist_ok=True)
    
    # Find XTF files in session directory
    xtf_files = [f for f in os.listdir(input_path) if f.endswith('.xtf')]
    
    if len(xtf_files) == 0:
        print(f"No XTF files found in the specified directory")
        exit()

    xtf_files.sort()  # Sort files alphabetically
    xtf_data = []
    for xtf_file in xtf_files:
        xtf_path = os.path.join(input_path, xtf_file)

        fh, packet, xtfpings = load_xtf(xtf_path)
        xtf_data.append((fh, packet, xtfpings))

        if inspect_xtfs:
            print(f"Inspecting {xtf_file}")
            inspect_xtf(xtf_file, fh, packet, output_path)

    print(f"Processing {len(xtf_files)} XTF file(s)")
    for i, (fh, packet, xtfpings) in enumerate(tqdm(xtf_data)):
        output_xtf_path = os.path.join(output_path, xtf_files[i])

        try:
            print(f"\nProcessing: {xtf_files[i]}")

            # Process with trajectory update and intensity correction
            pings = modify_pings_with_correction(
                xtfpings,
                yaw_offset=0.0,          # Adjust if needed
                install_angle=30.0,      # Adjust based on your sonar
                tvg_k=2.0,
                tvg_alpha=0.1,
                use_tvg=False,           # Set to True if you want TVG correction
                apply_water_mask=True,
                normalize_gain=True
            )

            # Write to file
            with open(output_xtf_path, 'wb') as f:
                f.write(fh.to_bytes())
                for p in pings:
                    f.write(p.to_bytes())

            print(f"Saved corrected XTF file to {output_xtf_path}")

            # Run MBSystem processing if enabled
            if run_mbsystem:
                print(f"Running MBSystem")

                tif_path = run_mbsystem_processing(
                    xtf_pings=pings,
                    xtf_path=output_xtf_path,
                    output_dir=output_path,
                    resolution=grid_resolution,
                    epsg_code=epsg_code
                )
        except Exception as e:
            print(f"Error processing {xtf_file}: {e}")
            import traceback
            traceback.print_exc()